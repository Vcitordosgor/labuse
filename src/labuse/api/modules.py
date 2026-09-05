"""MODULES OUTILS (Vague 1) — les « filtres savants ». Lecture q_v2 + tables de base.

Doctrine : un module = requête savante + surfaces existantes. Compteurs SQL-exacts,
bandeaux de limites honnêtes (« estimation », « à instruire »). Aucun score modifié.

SPEC M01 : la spec officielle est ABSENTE du repo (consigné) — critères C1-C5 définis ici :
  C1 surface 600–5 000 m² · C2 bâti 1–3 corps, emprise 5–40 % · C3 zone U dominante ·
  C4 lot libre : plus grand CERCLE inscrit (ST_MaximumInscribedCircle) dans la parcelle
     érodée du bâti (recul 3 m) → carré inscrit côté r√2 ; aire ≥ 200 m² et r ≥ 6 m
     (approximation CONSERVATRICE : sous-estime les lots allongés — documentée) ·
  C5 accès voirie ≤ 5 m.
Score division = 30·min(lot/500,1) + 25·(1−emprise) + 20·min(r/12,1) + 15·voirie + 10.
"""
from __future__ import annotations

import csv
import io
import logging
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/modules", tags=["modules"])


def _check_idu(idu: str) -> str:
    """M-K (P2-31) : même garde de FORME d'IDU que le rail principal (alphanumérique ≤ 20,
    sinon 404 — jamais un 500 driver sur un octet nul). Le rail premium /modules ne l'avait
    pas. Délègue à app._check_idu (source unique, pas de copie qui diverge)."""
    from .app import _check_idu as _c
    return _c(idu)

from ..faisabilite.bilan import (  # défauts calculette dérivés de la source unique (mandat hypothèses bilan)
    CALCULETTE_COUT_DEFAUT_M2,
    CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
    CALCULETTE_VRD_DEFAUT_M2,
)
from .. import runs  # S3 : run servi relu à la requête (bascule à chaud)


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


def _v2run(db: Session) -> str | None:
    """Run scoring v2 servi (M5.1 lot 3.1) — import différé (cycle app ↔ modules)."""
    from .app import _score_v2_run_id
    return _score_v2_run_id(db)


DDL = """
CREATE TABLE IF NOT EXISTS module_division (
  parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,
  idu varchar(14) NOT NULL,
  surface_m2 double precision,
  bati_count integer,
  emprise_pct double precision,
  zone varchar(20),
  mic_radius_m double precision,
  lot_area_m2 double precision,
  lot_geom geometry(Polygon, 4326),
  acces_voirie boolean,
  score integer,
  computed_at timestamptz DEFAULT now()
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        from ..db import sql_statements  # FIX-GB-011 : plus de split(';') naif
        for stmt in sql_statements(DDL):
            if stmt.strip():
                c.execute(text(stmt))
    # FIX-C6 (GB-049) — table LUE par /modules/permis (LEFT JOIN), construite à l'ingestion
    # M10 seulement → créée VIDE ici pour qu'une base neuve ne renvoie plus 500.
    from ..ingestion.permit_delais_m10 import ensure_tables as _m10_ens
    _m10_ens(engine)


# ───────────────────────── M01 — DIVISION PARCELLAIRE ─────────────────────────

@router.post("/division/compute")
def division_compute(request: Request, commune: str = "Saint-Paul", db: Session = Depends(get_db)) -> dict:
    """Pré-calcule les candidats division (C1-C5) — idempotent PAR COMMUNE (extension île : les
    24 communes coexistent dans module_division, on ne repart propre que sur celle calculée).
    GATE ADMIN (M-K P2-43) : écrivain lourd (DELETE+INSERT PostGIS commune entière), aucun
    appelant front — c'est un recalcul d'ops, pas une action client."""
    from .auth import exiger_admin
    exiger_admin(request)
    db.execute(text("DELETE FROM module_division m USING parcels p"
                    " WHERE p.id = m.parcel_id AND p.commune = :c"), {"c": commune})
    db.execute(text("""
        INSERT INTO module_division (parcel_id, idu, surface_m2, bati_count, emprise_pct, zone,
                                     mic_radius_m, lot_area_m2, lot_geom, acces_voirie, score)
        SELECT * FROM (
          WITH cand AS (
            SELECT p.id, p.idu, p.surface_m2, p.geom_2975,
                   b.n AS bati_count, b.emprise, b.bati_geom,
                   z.zone
            FROM parcels p
            JOIN LATERAL (
              SELECT count(*) AS n,
                     COALESCE(sum(ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975))), 0)
                       / NULLIF(ST_Area(p.geom_2975), 0) AS emprise,
                     ST_Union(sl.geom_2975) AS bati_geom
              FROM spatial_layers sl
              WHERE sl.kind = 'batiment' AND ST_Intersects(sl.geom_2975, p.geom_2975)
            ) b ON true
            JOIN LATERAL (
              SELECT sl.subtype AS zone FROM spatial_layers sl
              WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975)
              ORDER BY ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975)) DESC LIMIT 1
            ) z ON true
            WHERE p.commune = :c
              AND p.surface_m2 BETWEEN 600 AND 5000                       -- C1
              AND b.n BETWEEN 1 AND 3 AND b.emprise BETWEEN 0.05 AND 0.40 -- C2
              AND upper(z.zone) LIKE 'U%'                                 -- C3
          ),
          libre AS (
            SELECT c.*,
                   ST_Difference(c.geom_2975, ST_Buffer(c.bati_geom, 3)) AS free_geom
            FROM cand c
          ),
          mic AS (
            SELECT l.*, (ST_MaximumInscribedCircle(l.free_geom)).center AS ctr,
                        (ST_MaximumInscribedCircle(l.free_geom)).radius AS r
            FROM libre l WHERE NOT ST_IsEmpty(l.free_geom)
          )
          SELECT m.id, m.idu, m.surface_m2, m.bati_count,
                 round(m.emprise::numeric * 100, 1)::float,
                 m.zone,
                 round(m.r::numeric, 1)::float,
                 round((2 * m.r * m.r)::numeric)::float AS lot_area,
                 -- lot candidat : carré inscrit dans le cercle (côté r√2), en 4326
                 ST_Transform(ST_Envelope(ST_Buffer(m.ctr, m.r / sqrt(2))), 4326),
                 EXISTS (SELECT 1 FROM spatial_layers v WHERE v.kind = 'voirie'
                         AND ST_DWithin(m.geom_2975, v.geom_2975, 5)) AS voirie,
                 LEAST(100, round(
                   30 * LEAST((2 * m.r * m.r) / 500, 1)
                   + 25 * (1 - m.emprise)
                   + 20 * LEAST(m.r / 12, 1)
                   + 15 * (EXISTS (SELECT 1 FROM spatial_layers v WHERE v.kind = 'voirie'
                                   AND ST_DWithin(m.geom_2975, v.geom_2975, 5)))::int
                   + 10))::int
          FROM mic m
          WHERE m.r >= 6 AND 2 * m.r * m.r >= 200                          -- C4
            AND EXISTS (SELECT 1 FROM spatial_layers v WHERE v.kind = 'voirie'
                        AND ST_DWithin(m.geom_2975, v.geom_2975, 5))       -- C5
        ) q
        ON CONFLICT (parcel_id) DO NOTHING
    """), {"c": commune})
    n = db.execute(text("SELECT count(*) FROM module_division")).scalar()
    return {"ok": True, "candidats": int(n or 0)}


@router.get("/division")
def division_list(min_score: int = 0, limit: int = Query(300, ge=1, le=2000),   # FIX-C5
                  commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    # M6 2a (ticket M6-INC-03) : l'étage 0 du run SERVI prime PARTOUT — une parcelle en
    # exclusion dure (PPR rouge, foncier public, zonage…) ne peut pas être servie comme
    # candidate à la division, quel que soit son score géométrique. Les exclues sont
    # retirées du gisement et comptées (`etage0_exclus`) pour la transparence.
    etage0 = ("EXISTS(SELECT 1 FROM dryrun_parcel_evaluations d WHERE d.parcel_id = m.parcel_id"
              " AND d.run_label = :run AND d.status IN ('exclue', 'faux_positif_probable'))")
    rows = db.execute(text(f"""
        SELECT m.idu, m.surface_m2, m.bati_count, m.emprise_pct, m.zone, m.mic_radius_m,
               m.lot_area_m2, m.acces_voirie, m.score, ST_AsGeoJSON(m.lot_geom) AS lot,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM module_division m JOIN parcels p ON p.id = m.parcel_id
        WHERE m.score >= :s AND (CAST(:c AS text) IS NULL OR p.commune = :c)
          AND NOT {etage0}
        ORDER BY m.score DESC LIMIT :lim"""),
        {"s": min_score, "lim": limit, "c": commune, "run": runs.current()}).mappings().all()
    counts = db.execute(text(
        f"SELECT count(*) FILTER (WHERE NOT {etage0}) AS total,"
        f"       count(*) FILTER (WHERE {etage0}) AS exclus"
        " FROM module_division m JOIN parcels p ON p.id = m.parcel_id"
        " WHERE m.score >= :s AND (CAST(:c AS text) IS NULL OR p.commune = :c)"),
        {"s": min_score, "c": commune, "run": runs.current()}).mappings().one()
    return {"total": int(counts["total"] or 0), "etage0_exclus": int(counts["exclus"] or 0),
            "items": [{
        "idu": r["idu"], "surface_m2": round(r["surface_m2"] or 0), "bati_count": r["bati_count"],
        "emprise_pct": r["emprise_pct"], "zone": r["zone"], "mic_radius_m": r["mic_radius_m"],
        "lot_area_m2": r["lot_area_m2"], "acces_voirie": r["acces_voirie"], "score": r["score"],
        "lot": json.loads(r["lot"]) if r["lot"] else None, "geom": json.loads(r["g"]),
    } for r in rows]}


# ───────────────────────── M02 — SCAN PATRIMOINE INVERSÉ ─────────────────────────

@router.get("/patrimoine/search")
def patrimoine_search(q: str, db: Session = Depends(get_db)) -> list[dict]:
    # M103 P2 (défaut M100 n°3) : la colonne MAJIC est 100 % désaccentuée (82 701 lignes) et
    # ILIKE ne plie pas les accents — « Société » rendait 0 en silence. LE MÊME pliage
    # (constants.sql_plie) s'applique au paramètre ET à la colonne (motif NDé M99-B, déjà en
    # place à l'autocomplétion d'adresses).
    from ..constants import params_pliage, sql_plie
    from ..patrimoine_alias import expand_sigle
    if len(q.strip()) < 2:
        return []
    # GB-006 : si la saisie EST un sigle foncier connu (« SHLMR »…), on cherche AUSSI son expansion en
    # raison sociale (les fichiers fonciers ne stockent que le nom légal complet). Table extensible.
    alias = expand_sigle(q)
    params = {"q": q, "qs": f"{q}%", **params_pliage()}
    alias_clause = ""
    if alias:
        params["a"] = alias
        alias_clause = " OR " + sql_plie("pm.denomination") + " LIKE " + sql_plie("'%' || :a || '%'")
    # GB-007 : le compteur `n` DOIT être le MÊME que le scan (qui fait JOIN parcels) — sinon
    # l'autocomplétion sur-comptait les lignes MAJIC dont l'IDU n'a pas de parcelle (2632 vs 2618).
    rows = db.execute(text(f"""
        SELECT pm.siren, max(pm.denomination) AS nom, count(*) AS n
        FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        WHERE pm.siren IS NOT NULL
          AND ({sql_plie('pm.denomination')} LIKE {sql_plie("'%' || :q || '%'")}
               OR pm.siren LIKE :qs{alias_clause})
        GROUP BY pm.siren ORDER BY n DESC LIMIT 12"""),
        params).mappings().all()
    return [dict(r) for r in rows]


_TIERS_ACTIONNABLES = ("brulante", "chaude", "reserve_fonciere", "a_creuser")


@router.get("/patrimoine")
def patrimoine(siren: str, fmt: str = "json",
               limit: int = Query(200, ge=1, le=2000), offset: int = Query(0, ge=0),
               request: Request = None, db: Session = Depends(get_db)):
    """Inventaire du foncier d'une PERSONNE MORALE (SIREN) : ses parcelles, le TIER v2 servi de
    chacune (étage 0 du run prime), le résiduel, les signaux d'approche (BODACC procédure + INPI
    dirigeants), la valorisation indicative du foncier nu, et — si des parcelles sont contiguës —
    l'assiette à étudier en assemblage. PM UNIQUEMENT (RGPD : jamais un particulier). Tri par rang P.
    M137 : plus de vestige de matrice (q_score/a_score/completeness_score MORTS retirés du fil).

    GB-018 — les agrégats couvrent TOUT le portefeuille ; la liste `items` est PAGINÉE (limit/offset,
    géométrie de la page seulement) et EXPORTABLE (`fmt=csv`, raison sociale entière, notice GB-016 si
    plafond). Un gros propriétaire (4000+ parcelles) ne fait plus 2,9 Mo/10 s d'un bloc. GB-017 :
    `fmt` est désormais un vrai paramètre (json|csv), plus un param fantôme ignoré."""
    from .app import _score_v2_run_id
    from ..assemblage import ADJ_BUFFER_M
    from ..faisabilite.marche_commune import ligne2_terrain_zone
    # ROBUSTESSE — cette fonction est aussi appelée EN DIRECT (copilote `parcelles_par_entreprise`,
    # tests) où les défauts `Query()` ne sont pas résolus : on retombe sur les valeurs par défaut.
    limit = limit if isinstance(limit, int) else 200
    offset = offset if isinstance(offset, int) else 0
    rows = db.execute(text("""
        SELECT p.id, p.idu, p.commune, p.surface_m2, z.zone_fam, r.sdp_residuelle_m2,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
        FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
        WHERE pm.siren = :s ORDER BY s2.rang ASC NULLS LAST"""),
        {"s": siren, "run": runs.current(), "v2run": _score_v2_run_id(db)}).mappings().all()
    bodacc = db.execute(text(
        "SELECT type_procedure, date_annonce FROM v_foncier_sous_pression WHERE siren = :s LIMIT 1"),
        {"s": siren}).mappings().first()
    nom = db.execute(text(
        "SELECT max(denomination) FROM parcelle_personne_morale WHERE siren = :s"), {"s": siren}).scalar()
    # #4 SIGNAL INPI (brique dormante de « Foncier fantôme ») : société ABSENTE du registre des
    # dirigeants = signal d'approche fort (succession / société en sommeil). Libellé FACTUEL.
    inpi_sans_dirigeant = bool(siren) and not db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pm_dirigeants WHERE siren = :s)"), {"s": siren}).scalar()
    # #2 l'agrégat dit l'ACTIONNABLE. « Écartées » de base = étage 0 cascade (exclues/faux positif).
    # CONNEXIONS-2 Lot 4 (KO-10) : si le COMPTE courant a explicitement ÉCARTÉ des parcelles dans un
    # de SES projets (projet_parcelles.statut='ecartee') ou archivé une piste (pipeline_entries), on
    # les retire AUSSI de l'actionnable — le libellé dit alors « hors écartées par vous ». Sans compte
    # ou sans décision, on ne retire rien et le libellé reste « N actionnables » (pas de faux ami).
    from .tenant import current_compte
    cid = current_compte(request) if request is not None else None
    ecartees_par_vous: set[str] = set()
    if cid is not None:
        idus_scan = [r["idu"] for r in rows]
        if idus_scan:
            ecartees_par_vous = {row[0] for row in db.execute(text(
                """SELECT DISTINCT par.idu
                   FROM projet_parcelles pp
                   JOIN parcels par ON par.id = pp.parcel_id
                   JOIN projets pj ON pj.id = pp.projet_id
                   WHERE pj.compte_id IS NOT DISTINCT FROM :cid
                     AND pp.statut = 'ecartee' AND par.idu = ANY(:idus)
                   UNION
                   SELECT DISTINCT par2.idu
                   FROM pipeline_entries pe
                   JOIN parcels par2 ON par2.id = pe.parcel_id
                   WHERE pe.compte_id IS NOT DISTINCT FROM :cid
                     AND pe.archived_at IS NOT NULL AND par2.idu = ANY(:idus)"""),
                {"cid": cid, "idus": idus_scan}).all()}
    n_actionnables = sum(1 for r in rows if r["tier_v2"] in _TIERS_ACTIONNABLES
                         and not r["etage0"] and r["idu"] not in ecartees_par_vous)
    sdp_residuelle = round(sum(r["sdp_residuelle_m2"] or 0 for r in rows))
    # #3 VALORISATION indicative du foncier nu (zones U/AU) au RÉFÉRENTIEL UNIQUE prix terrain de zone
    # (ligne2_terrain_zone, une fois par commune). Indicative — seules les zones U/AU ont un prix marché.
    prix_zone: dict[tuple[str, str], float] = {}
    for c in {r["commune"] for r in rows if r["commune"]}:
        try:
            cellules = (ligne2_terrain_zone(db, c).get("valeurs") or {}).get("par_zone") or {}
            for fam, cell in cellules.items():
                if cell.get("calculable"):
                    prix_zone[(c, fam)] = cell["median_eur_m2"]
        except Exception:  # noqa: BLE001 — la valorisation est un bonus, jamais un 500
            pass
    val_nu = 0.0
    n_valorisables = 0
    for r in rows:
        px = prix_zone.get((r["commune"], r["zone_fam"])) if r["zone_fam"] in ("U", "AU") else None
        if px and r["surface_m2"]:
            val_nu += r["surface_m2"] * px
            n_valorisables += 1
    # #5 ASSIETTE CONTIGUË : parcelles du portefeuille d'un seul tenant (contact cadastral ADJ_BUFFER_M)
    # → « Analyser en assiette ». Fréquent (79 % des portefeuilles multi-parcelles). Plus gros bloc ≥ 2.
    assiette_contigue: list[str] = []
    ids = [r["id"] for r in rows]
    if len(ids) >= 2:
        pairs = db.execute(text("""
            SELECT a.id AS a, b.id AS b FROM parcels a JOIN parcels b
              ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)
            WHERE a.id = ANY(:ids) AND b.id = ANY(:ids)"""), {"ids": ids, "buf": ADJ_BUFFER_M}).all()
        if pairs:
            adj: dict[int, set[int]] = {i: set() for i in ids}
            for a, b in pairs:
                adj[a].add(b)
                adj[b].add(a)
            vus: set[int] = set()
            best: list[int] = []
            for start in ids:
                if start in vus or not adj[start]:
                    continue
                comp, stack = {start}, [start]
                while stack:
                    for nb in adj[stack.pop()]:
                        if nb not in comp:
                            comp.add(nb)
                            stack.append(nb)
                vus |= comp
                if len(comp) > len(best):
                    best = list(comp)
            id2idu = {r["id"]: r["idu"] for r in rows}
            assiette_contigue = [id2idu[i] for i in best] if len(best) >= 2 else []
    # GB-017/018 — EXPORT CSV du portefeuille (raison sociale ENTIÈRE ; notice GB-016 si plafond).
    if fmt == "csv":
        import csv as _csv
        import io as _io
        CAP = 5000
        corpus = rows[:CAP]
        buf = _io.StringIO()
        w = _csv.writer(buf, delimiter=";")
        if len(rows) > CAP:
            w.writerow([f"Export limité aux {CAP} premières lignes sur {len(rows)} — "
                        "affinez ou paginez pour le reste."])
        w.writerow(["idu", "commune", "tier_v2", "rang_v2", "surface_m2", "sdp_residuelle_m2",
                    "siren", "raison_sociale"])
        for r in corpus:
            w.writerow([r["idu"], r["commune"], ("ecartee" if r["etage0"] else r["tier_v2"]) or "",
                        r["rang_v2"] if r["rang_v2"] is not None else "", round(r["surface_m2"] or 0),
                        round(r["sdp_residuelle_m2"]) if r["sdp_residuelle_m2"] is not None else "",
                        siren, nom or ""])
        return Response(buf.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="patrimoine-{siren}.csv"',
                                 "X-Rows": str(len(corpus)), "X-Total": str(len(rows))})
    # JSON — liste PAGINÉE ; la géométrie n'est calculée QUE pour la page servie (pas les 4000+ lignes).
    page = rows[offset:offset + limit]
    geoms = {r[0]: r[1] for r in db.execute(text(
        "SELECT idu, ST_AsGeoJSON(ST_Transform(geom_2975, 4326)) FROM parcels WHERE idu = ANY(:i)"),
        {"i": [r["idu"] for r in page]}).all()} if page else {}
    return {
        "siren": siren, "nom": nom, "n_parcelles": len(rows),
        "n_actionnables": n_actionnables,
        # KO-10 — le libellé front dit « hors écartées par vous » SI ce compte a écarté des parcelles.
        "hors_ecartees_par_vous": bool(ecartees_par_vous),
        "n_ecartees_par_vous": len(ecartees_par_vous),
        "sdp_residuelle_m2": sdp_residuelle,
        "valorisation_nu_eur": round(val_nu) if n_valorisables else None,
        "n_valorisables": n_valorisables,
        "bodacc": dict(bodacc) if bodacc else None,
        "inpi_sans_dirigeant": inpi_sans_dirigeant,
        "assiette_contigue": assiette_contigue,
        "total": len(rows), "affiches": len(page), "offset": offset, "limit": limit,
        "tronquee": offset + limit < len(rows),
        "items": [{"idu": r["idu"], "commune": r["commune"],
                   "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                   "surface_m2": round(r["surface_m2"] or 0), "sdp": r["sdp_residuelle_m2"],
                   "geom": json.loads(geoms[r["idu"]]) if geoms.get(r["idu"]) else None} for r in page],
    }


# ───────────────────────── M03 — RADAR PERMIS ─────────────────────────

def _permis_etat_pred(etat: str | None, a: str) -> str:
    """RETOURS-17 W2 — prédicat SQL de l'ÉTAT DE CYCLE d'un permis. La base se partitionne EXACTEMENT
    en quatre états dont la somme fait le total (constat Vic 05/09 : trois chips qui ne s'additionnaient
    pas) : Récent (autorisé ≤ 24 mois) · Dormant (PC ancien sans achèvement, non bâti) · Achevé (DAACT
    déclaré) · Autre (le reste). Le découpage « récent » (24 mois) est ancré sur :dmax = fin du flux
    Sitadel (honnêteté : le flux s'arrête avant aujourd'hui). « dormant » garde son endpoint dédié
    (/promesses : la jointure parcelle+run est coûteuse) ; ICI on sert récent/achevé/autre. `a` = préfixe
    d'alias table (`''` pour count/carte, `'s.'` pour la liste). Mesuré le 05/09 (base locale, q_v11_m137,
    dmax 2026-07-31) : récent 5 580 · dormant 15 466 · achevé 20 534 · autre 8 964 = 50 544 (= total base).
    Whitelist fermée (etat ∈ {recent, acheve, autre}) — aucune valeur libre n'entre dans le SQL."""
    rc = "(:dmax - interval '24 months')"
    if etat == "recent":
        return f" AND {a}date >= {rc}"
    if etat == "acheve":
        return f" AND {a}date < {rc} AND {a}raw->>'daact' IS NOT NULL"
    if etat == "autre":
        # non récent, sans DAACT, et surtout PAS un dormant : mêmes critères que /promesses
        # (PC ancien de plus de 36 mois, rattaché à une parcelle notée du run, toujours non bâtie).
        return (f" AND {a}date < {rc} AND {a}raw->>'daact' IS NULL"
                f" AND NOT ({a}type = 'PC' AND {a}date < now() - interval '36 months'"
                f" AND EXISTS (SELECT 1 FROM jsonb_array_elements_text({a}idu_codes) _c(idu)"
                f"   JOIN parcels _p ON _p.idu = _c.idu"
                f"   JOIN dryrun_parcel_evaluations _d ON _d.parcel_id = _p.id AND _d.run_label = :run"
                f"   WHERE NOT EXISTS (SELECT 1 FROM dryrun_cascade_results _cr"
                f"     WHERE _cr.run_label = :run AND _cr.parcel_id = _p.id"
                f"     AND _cr.layer_name = 'bati' AND _cr.result = 'HARD_EXCLUDE')))")
    return ""


@router.get("/permis")
def permis(commune: str | None = None, months: int = 24, nature: str | None = None,
           limit: int = Query(300, ge=1, le=2000), offset: int = Query(0, ge=0),  # GB-029 : ge=0 → 422, plus de 500
           count_only: bool = False,   # RETOURS-16 V4 — compteur seul (ni lignes ni carte)
           etat: str | None = None,    # RETOURS-17 W2 — état de cycle : recent|acheve|autre (dormant = /promesses)
           db: Session = Depends(get_db)) -> dict:
    # fenêtre ancrée sur la FIN DES DONNÉES (le flux Sitadel s'arrête avant aujourd'hui) — honnêteté
    dmax = db.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()
    # FIX-C6 (GB-049) — base NEUVE / sans permis : dmax NULL rendrait `date >= NULL - interval`
    # (operator does not exist: timestamp >= interval) = 500. On répond un état VIDE honnête.
    if dmax is None:
        if count_only:   # RETOURS-16 V4 — même forme compteur, base vide comprise
            return {"total": 0, "geocodes": 0, "donnees_jusqu_au": None}
        return {"commune": commune or "Toute l'île", "months": months, "nature": nature,
                "total": 0, "affiches": 0, "has_more": False, "donnees_jusqu_au": None,
                "geocodes": 0, "sans_localisation": 0, "pct_geocode": 0, "carte": [], "items": []}
    limit = max(1, min(limit, 2000))  # garde-fou payload ; « voir plus » pagine par offset
    # RETOURS-17 W2 — prédicat d'état de cycle (récent/achevé/autre), whitelist fermée. `ep` sans alias
    # (count + carte), `eps` avec alias `s.` (liste). :run n'est lu que par l'état « autre ».
    if etat not in (None, "recent", "acheve", "autre"):
        etat = None
    ep, eps = _permis_etat_pred(etat, ""), _permis_etat_pred(etat, "s.")
    prun = runs.current() if etat == "autre" else None
    # RETOURS-16 V4 — chemin compteur : le chip « Tous » du segment doit dire le TOTAL EN BASE
    # (toute la profondeur), pas la somme de deux fenêtres. Un COUNT léger, jamais les 47k geoms.
    if count_only:
        c = db.execute(text(
            f"""SELECT count(*) AS n, count(*) FILTER (WHERE geom IS NOT NULL) AS geo
               FROM sitadel_permits
               WHERE (CAST(:c AS text) IS NULL OR commune = :c)
                 AND (CAST(:nat AS text) IS NULL OR type = :nat)
                 AND date >= :dmax - (:m || ' months')::interval{ep}"""),
            {"c": commune, "m": months, "nat": nature, "dmax": dmax, "run": prun}).mappings().first()
        return {"total": int(c["n"] or 0), "geocodes": int(c["geo"] or 0),
                "donnees_jusqu_au": dmax.date().isoformat()}
    # M10 : jointure sur la date de dépôt + délai d'instruction rapatriés (m10_permit_delais)
    # LISTE paginée (plafond levé côté client par « voir plus » — offset).
    rows = db.execute(text(f"""
        SELECT s.permit_id, s.type, s.date::date::text AS date, s.commune,
               s.raw->>'etat' AS etat, s.raw->>'nb_lgt' AS nb_lgt, s.raw->>'surf_hab' AS surf_hab,
               s.raw->>'geoloc' AS geoloc,   -- RETOURS-14 S5.1 : la liste DIT la localisation approximative
               d.date_depot::text AS depot, CASE WHEN d.valide THEN d.delai_mois END AS delai_mois,
               CASE WHEN s.geom IS NOT NULL THEN ST_AsGeoJSON(s.geom) END AS g
        FROM sitadel_permits s
        LEFT JOIN m10_permit_delais d ON d.permit_id = s.permit_id
        WHERE (CAST(:c AS text) IS NULL OR s.commune = :c)
          AND (CAST(:nat AS text) IS NULL OR s.type = :nat)
          AND s.date >= :dmax - (:m || ' months')::interval{eps}
        ORDER BY s.date DESC LIMIT :lim OFFSET :off"""),
        {"c": commune, "m": months, "nat": nature, "dmax": dmax, "run": prun, "lim": limit, "off": offset}).mappings().all()
    counts = db.execute(text(
        f"""SELECT count(*) AS n, count(*) FILTER (WHERE geom IS NOT NULL) AS geo
           FROM sitadel_permits
           WHERE (CAST(:c AS text) IS NULL OR commune = :c)
             AND (CAST(:nat AS text) IS NULL OR type = :nat)
             AND date >= :dmax - (:m || ' months')::interval{ep}"""),
        {"c": commune, "m": months, "nat": nature, "dmax": dmax, "run": prun}).mappings().first()
    true_total = int(counts["n"] or 0)
    geocodes_total = int(counts["geo"] or 0)
    # CARTE = TOUS les géocodés (décision Vic), chargée une seule fois (page 0), payload léger (geom seul).
    # RETOURS-15 U2 — le plafond LIMIT 8000 (tri date DESC) SAUTE : en « Tous » (240 mois), il
    # réduisait les 47 071 géocodés aux 8 000 plus récents → un PC 2016 rattaché par la géométrie
    # (S5) n'apparaissait JAMAIS sur la carte île entière (« je ne les vois pas », Vic 05/09).
    # Mesuré : 41 ms d'exécution pour la fenêtre pleine ; garde large 60 000 = borne de payload,
    # pas un filtre (la fenêtre Sitadel entière tient dessous).
    carte = []
    if offset == 0:
        crows = db.execute(text(f"""
            SELECT permit_id, type, date::date::text AS date, ST_AsGeoJSON(geom) AS g
            FROM sitadel_permits
            WHERE (CAST(:c AS text) IS NULL OR commune = :c)
              AND (CAST(:nat AS text) IS NULL OR type = :nat)
              AND date >= :dmax - (:m || ' months')::interval AND geom IS NOT NULL{ep}
            ORDER BY date DESC LIMIT 60000"""),
            {"c": commune, "m": months, "nat": nature, "dmax": dmax, "run": prun}).mappings().all()
        carte = [{"permit_id": r["permit_id"], "type": r["type"], "date": r["date"],
                  "geom": json.loads(r["g"])} for r in crows]
    return {
        "commune": commune or "Toute l'île", "months": months, "nature": nature,
        "total": true_total, "affiches": offset + len(rows), "has_more": offset + len(rows) < true_total,
        "donnees_jusqu_au": dmax.date().isoformat() if dmax else None,
        "geocodes": geocodes_total, "sans_localisation": max(0, true_total - geocodes_total),
        "pct_geocode": round(100 * geocodes_total / true_total) if true_total else 0,
        "carte": carte,
        # LOT11 (OUTILS-FINALE) — `etat_label` servi ici (source unique `_ETAT_LABELS`, comme la fiche) :
        # le front affichait le CODE Sitadel brut (« 2 ») orphelin en 2e ligne. Plus jamais un code nu.
        # RETOURS-16 V2 — l'état « 2 » (Autorisé) est MUET en liste : Sitadel 974 ne publie que des
        # permis autorisés, l'information est constante — elle vit dans la phrase d'explication de
        # l'outil ; la FICHE permis (permis_fiche) garde l'état complet. Les états 4/5/6 (chantier
        # ouvert, en cours, achevés), eux, varient : ils restent servis.
        "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "depot", "delai_mois",
                                        "etat", "nb_lgt", "surf_hab", "geoloc")},
                   "etat_label": (_ETAT_LABELS.get(r["etat"], f"état {r['etat']}")
                                  if r["etat"] and r["etat"] != "2" else None),
                   "geom": json.loads(r["g"]) if r["g"] else None} for r in rows],
    }


# Libellés lisibles (nature d'autorisation + état d'avancement, codes source non documentés)
# RETOURS-13 R30 — libellés OFFICIELS de DESTINATION_PRINCIPALE (dictionnaire Sitadel3, SDES —
# « dictionnaire_variables locaux_permis_construire.xls », vérifié le 05/09/2026) : la fiche
# permis dit désormais SA nature (un hôtel se lit « hôtels », plus un code muet).
_DESTINATION_LABELS = {"1": "habitation", "2": "hôtels", "3": "bureaux", "4": "commerce",
                       "6": "industrie", "7": "agriculture", "8": "entrepôt",
                       "9": "service public ou d'intérêt collectif"}
_NATURE_LABELS = {"PC": "Permis de construire", "DP": "Déclaration préalable",
                  "PA": "Permis d'aménager", "PD": "Permis de démolir"}
_ETAT_LABELS = {"2": "Autorisé", "4": "Chantier ouvert", "5": "En cours",
                "6": "Travaux achevés (DAACT)"}


@router.get("/permis/{permit_id}")
def permis_fiche(permit_id: str, db: Session = Depends(get_db)) -> dict:
    """Fiche permis cliquable (M10 lot 1.1) : référence, porteur (si PM), nature, lots,
    surfaces, dates clés (dépôt / autorisation / achèvement) + délai d'instruction, statut."""
    r = db.execute(text("""
        SELECT s.permit_id, s.type, s.commune, s.date::date::text AS date_autorisation,
               s.raw->>'etat' AS etat, s.raw->>'nb_lgt' AS nb_lgt, s.raw->>'surf_hab' AS surf_hab,
               s.raw->>'daact' AS daact, s.raw->>'destination' AS destination,
               s.raw->>'geoloc' AS geoloc,
               s.raw->>'petitioner_name' AS porteur, s.raw->>'petitioner_siren' AS porteur_siren,
               s.idu_codes,
               d.date_depot::text AS date_depot, d.valide AS delai_valide,
               d.delai_mois, d.date_achevement::text AS date_achevement,
               CASE WHEN s.geom IS NOT NULL THEN ST_AsGeoJSON(s.geom) END AS g
        FROM sitadel_permits s
        LEFT JOIN m10_permit_delais d ON d.permit_id = s.permit_id
        WHERE s.permit_id = :pid"""), {"pid": permit_id}).mappings().first()
    if not r:
        raise HTTPException(404, "Permis introuvable")
    delai = None
    if r["delai_valide"] and r["delai_mois"] is not None:
        delai = {"mois": r["delai_mois"],
                 "libelle": f"{r['delai_mois']} mois entre dépôt et autorisation"}
    return {
        "permit_id": r["permit_id"], "commune": r["commune"],
        "nature": r["type"], "nature_libelle": _NATURE_LABELS.get(r["type"], r["type"]),
        "porteur": r["porteur"], "porteur_siren": r["porteur_siren"],
        "porteur_note": None if r["porteur"] else "Pétitionnaire personne physique (anonymisé à la source)",
        "nb_lots": int(r["nb_lgt"]) if (r["nb_lgt"] or "").isdigit() else None,
        "surface_hab_m2": float(r["surf_hab"]) if r["surf_hab"] else None,
        "date_depot": r["date_depot"], "date_autorisation": r["date_autorisation"],
        "date_achevement": r["date_achevement"] or r["daact"],
        "delai_instruction": delai,
        "statut": _ETAT_LABELS.get(r["etat"], f"état {r['etat']}"), "etat_code": r["etat"],
        # R30 — la destination est SERVIE avec son libellé (hôtels, bureaux, commerce…) : le
        # filtre implicite « logements » n'existe plus, toutes les destinations sont dites.
        "destination": r["destination"],
        "destination_libelle": _DESTINATION_LABELS.get(r["destination"] or ""),
        "geoloc_note": r["geoloc"],
        "parcelles": list(r["idu_codes"]) if r["idu_codes"] else [],
        "geom": json.loads(r["g"]) if r["g"] else None,
        "source": "SITADEL (SDES/Dido) — autorisations d'urbanisme, dép. 974",
    }


@router.get("/parcelle-permis")
def parcelle_permis(idu: str, db: Session = Depends(get_db)) -> dict:
    """M10 lot 1.2/1.3 — permis SUR ou À PROXIMITÉ d'une parcelle, cliquables.

    Lit EXACTEMENT `via_permits_geo` (permis géolocalisés autorisés, EPSG 2975) — la même
    table que le score de viabilisation M-VIA — pour que les permis affichés soient LA PREUVE
    derrière les compteurs c100/c200 de la fiche (cohérence garantie, rayons 100/200 m). Chaque
    entrée porte son `permit_id` → fiche permis (/modules/permis/{id})."""
    exists = db.execute(text(
        "SELECT to_regclass('public.via_permits_geo') IS NOT NULL")).scalar()
    if not exists:
        return {"idu": idu, "indisponible": "via_permits_geo non construit (relancer M-VIA)",
                "c100": 0, "c200": 0, "items": []}
    rows = db.execute(text("""
        WITH p AS (SELECT geom_2975 AS g FROM parcels WHERE idu = :idu)
        SELECT w.permit_id, s.type, s.date::date::text AS date, s.commune,
               s.raw->>'etat' AS etat, s.raw->>'nb_lgt' AS nb_lgt,
               s.raw->>'petitioner_name' AS porteur,
               round(ST_Distance(p.g, w.g))::int AS dist_m
        FROM p JOIN via_permits_geo w ON ST_DWithin(p.g, w.g, 200)
               JOIN sitadel_permits s ON s.permit_id = w.permit_id
        ORDER BY dist_m ASC LIMIT 100"""), {"idu": idu}).mappings().all()
    items = [{"permit_id": r["permit_id"], "nature": r["type"],
              "nature_libelle": _NATURE_LABELS.get(r["type"], r["type"]),
              "date": r["date"], "etat": r["etat"], "nb_lgt": r["nb_lgt"],
              "porteur": r["porteur"], "distance_m": r["dist_m"],
              "rayon": "100m" if r["dist_m"] <= 100 else "200m"} for r in rows]
    return {
        "idu": idu,
        "c100": sum(1 for i in items if i["distance_m"] <= 100),
        "c200": len(items),
        "note": "Permis autorisés géolocalisés < 200 m (source du signal viabilisation M-VIA).",
        "items": items,
    }


# ───────────────────────── M04 — PROMESSES MORTES ─────────────────────────
# Reco (états réels en base, codes raw.etat NON documentés par la source — interprétation
# prudente affichée telle quelle) : 6 = achevé (100 % ont une daact) ; 2/4/5 = sans daact.
# « Promesse morte » = PC daté > N mois, SANS daact, ET parcelle toujours sans bâti significatif.

@router.get("/promesses")
def promesses(commune: str | None = None, months: int = 24,
              limit: int = 1000, offset: int = Query(0, ge=0), count_only: bool = False,  # GB-029
              db: Session = Depends(get_db)) -> dict:
    limit = max(1, min(limit, 2000))  # 1re page légère (défaut 1000), le reste en « voir plus »
    # Le COUNT(DISTINCT) est coûteux (~4 s) : DÉCOUPLÉ du chemin des lignes (appel parallèle count_only)
    # pour que la liste s'affiche vite et s'étoffe — décision Vic « rapide qui s'étoffe > 10 s ».
    if count_only:
        return {"total": int(db.execute(text("""
            SELECT count(DISTINCT s.id) FROM sitadel_permits s
            JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS c(idu) ON true
            JOIN parcels p ON p.idu = c.idu
            JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            WHERE s.type = 'PC' AND (CAST(:c AS text) IS NULL OR s.commune = :c)
              AND s.date < now() - (:m || ' months')::interval AND s.raw->>'daact' IS NULL
              AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                              WHERE cr.run_label = :run AND cr.parcel_id = p.id
                                AND cr.layer_name = 'bati' AND cr.result = 'HARD_EXCLUDE')"""),
            {"c": commune, "m": months, "run": runs.current()}).scalar() or 0)}
    # CTE MATERIALIZED = parade au plan « fast-start » de LIMIT/OFFSET-0 (28 s → 5 s) : la jointure
    # latérale lourde est calculée en bloc (hash joins) AVANT le tri+plafond.
    # §3 (23/08/2026) — la GÉOM du permis est RÉ-AJOUTÉE (ST_AsGeoJSON) : depuis la fusion Radar+Point
    # mort, l'outil « Permis » rend le point mort en POINTS CLIQUABLES (comme le radar), plus en
    # surlignage de parcelle (module-hl). Payload = la géom du permis (centroïde) par ligne — mesuré
    # léger (une page 1000 ; les non-géocodés restent listés, geom NULL).
    rows = db.execute(text("""
        WITH cand AS MATERIALIZED (
            -- audit-promesses : `d.q_score` (matrice MORTE depuis M129-B) RETIRÉ — il était sélectionné
            -- et renvoyé mais aucun consommateur ne le lit (vestige). `d` reste utilisé pour `status`.
            SELECT s.permit_id, s.type, s.date, s.raw->>'etat' AS etat, s.raw->>'nb_lgt' AS nb_lgt,
                   p.idu, round(p.surface_m2) AS surface_m2,
                   CASE WHEN s.geom IS NOT NULL THEN ST_AsGeoJSON(s.geom) END AS g,
                   (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
            FROM sitadel_permits s
            JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS c(idu) ON true
            JOIN parcels p ON p.idu = c.idu
            JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            WHERE s.type = 'PC' AND (CAST(:c AS text) IS NULL OR s.commune = :c)
              AND s.date < now() - (:m || ' months')::interval
              AND s.raw->>'daact' IS NULL
              -- parcelle toujours non bâtie : pas d'exclusion « déjà bâti » au run q_v2
              AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                              WHERE cr.run_label = :run AND cr.parcel_id = p.id
                                AND cr.layer_name = 'bati' AND cr.result = 'HARD_EXCLUDE')
        )
        SELECT cand.permit_id, cand.type, cand.date::date::text AS date, cand.etat, cand.nb_lgt,
               cand.idu, cand.surface_m2, cand.g, s2.tier AS statut, cand.etage0,
               s2.tier AS tier_v2, s2.rang AS rang_v2
        FROM cand LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = cand.idu AND s2.run_id = :v2run
        ORDER BY cand.date ASC LIMIT :lim OFFSET :off"""),
        {"c": commune, "m": months, "run": runs.current(), "v2run": _v2run(db), "lim": limit, "off": offset}).mappings().all()
    # tri anciens d'abord (= les plus « morts »). total via l'appel count_only parallèle ; ici on déduit
    # has_more du remplissage de la page (une page pleine ⇒ il reste potentiellement des lignes).
    return {"commune": commune or "Toute l'île", "months": months, "total": None,
            "affiches": offset + len(rows), "has_more": len(rows) == limit,
            "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "etat", "nb_lgt", "idu",
                                            "surface_m2", "statut")},
                       "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                       "geom": json.loads(r["g"]) if r["g"] else None}
                      for r in rows]}


# ───────────────────────── PROSPECTION SOLAIRE (V1 restitution) ─────────────────────────
# Sert la donnée DÉJÀ en base, GELÉE au 11/07/2026 : parcel_solar (productible PVGIS/SARAH3 = Sourcé
# dérivé ; azimut du bâti = Estimé ; proba propriétaire-occupant = Estimé statistique ; flag ABF),
# parcel_terrain (pente = Sourcé RGE ALTI 5 m), p_model_bati (emprise bâtie = Estimé, proxy toiture),
# parcel_equipements (piscine = Estimé, ortho BD ORTHO 20 cm 2025, fiab. ~90,7 %).
# AUCUN recalcul, aucun appel externe, MASQUE SOLAIRE DU RELIEF NON CALCULÉ. RGPD : aucune donnée
# nominative — des parcelles et des caractéristiques, jamais des personnes (proba = probabilité).
def _prospection_solaire_cap() -> int:
    """Plafond de la liste EN CONFIG (config/prospection_solaire.yaml `liste_max`, défaut 500) —
    jamais un LIMIT muet ; l'écran DIT « les N premières sur M »."""
    try:
        from ..config import load_yaml_config
        return int(load_yaml_config("prospection_solaire").get("liste_max", 500))
    except Exception:  # noqa: BLE001
        return 500


def _classement_court(tier_v2: str | None, etage0: bool) -> str:
    """Le mot SERVI (M137, chip court) depuis le mapping canonique — même vocabulaire qu'à l'écran
    (verdictMeta). etage0 gagne (écartée) ; sinon le libellé court du tier ; sinon « — »."""
    if etage0:
        return "Écartée"
    from ..verdict_servi import TIER_LABELS
    return TIER_LABELS.get(tier_v2 or "", "—") if tier_v2 else "—"


@router.get("/prospection-solaire")
def prospection_solaire(commune: str | None = None,
                        potentiel_min: int = 0, proba_occ_min: int = 0,
                        piscine: str = "tous",   # tous | oui | non
                        piscine_surf_min: int = 0,   # surface piscine ≥ (m²) — mode Piscines
                        inclure_incertaines: bool = False,   # RETOURS-11F3 avenant — aligne le LISTING sur le filtre confiance de l'agg
                        sort: str = "potentiel",  # potentiel | toiture | proba
                        fmt: str = "json",
                        db: Session = Depends(get_db)):
    """Outil « Prospection solaire » V1 — liste de parcelles triée par potentiel solaire, servie
    depuis les données gelées au 11/07/2026 (cf. en-tête). Sert le démarchage (export CSV)."""
    if not db.execute(text("SELECT to_regclass('parcel_solar') IS NOT NULL")).scalar():
        raise HTTPException(503, "données solaires indisponibles (table absente).")
    cap = _prospection_solaire_cap()
    # OUTILS-2 (O2-2) — « Top parcelles » : potentiel DESC PUIS toiture DESC. À la maille PVGIS (~400 m),
    # des parcelles voisines partagent le MÊME potentiel : trier là-dessus seul ne classe rien — c'est la
    # toiture (emprise bâtie, proxy) qui départage et qui intéresse l'installateur. `ps.idu` reste en
    # dernier pour un ordre STABLE.
    # Le potentiel est trié à la MAILLE AFFICHÉE (round kWh/kWc) : à pleine précision, deux parcelles
    # voisines de la même maille PVGIS diffèrent d'un millième et la toiture ne départagerait jamais.
    # En arrondissant comme l'écran, les « 51 lignes à 1 597 » forment un vrai palier que la toiture classe.
    orders = {"potentiel": "round(ps.prod_spec_kwh_kwc) DESC NULLS LAST, b.emprise_bati_m2 DESC NULLS LAST, ps.idu",
              "toiture": "b.emprise_bati_m2 DESC NULLS LAST, round(ps.prod_spec_kwh_kwc) DESC NULLS LAST, ps.idu",
              "proba": "ps.proba_proprio_occupant DESC NULLS LAST, ps.idu"}
    order = orders.get(sort, orders["potentiel"])
    # piscine : « oui » = détectée ; « non » = non détectée (⚠ l'absence n'est pas VÉRIFIÉE hors des
    # zones scannées — dit au « i » ; pas un « zéro » affirmé).
    pisc_cond = " AND e.piscine IS TRUE" if piscine == "oui" \
        else " AND (e.piscine IS NOT TRUE)" if piscine == "non" else ""
    # surface piscine ≥ (mode Piscines) : implique une piscine détectée avec une surface mesurée.
    surf_cond = " AND e.piscine_surface_m2 >= :psmin" if piscine_surf_min else ""
    # RETOURS-11F3 avenant (note liée R11) — en mode PISCINES (piscine='oui'), le LISTING suit le MÊME
    # filtre que le compteur (agg) : confiance HAUTE par défaut (+ incertaines à la bascule) ET exclusion
    # des « pas une piscine ». Avant, la liste ignorait ces deux filtres → « 7 821 (agg) vs 8 299 (liste) »
    # sur le même écran. Point de calcul partagé `_piscine_conf_filtre`.
    conf_cond = corr_cond = ""
    if piscine == "oui":
        from ..ingestion.ortho_equipements import ensure_corrections
        ensure_corrections(db)   # idempotent — la table existe avant le NOT EXISTS
        conf_cond = _piscine_conf_filtre(inclure_incertaines)
        corr_cond = " AND NOT EXISTS (SELECT 1 FROM piscine_corrections pc WHERE pc.idu = e.idu)"
    where = ("WHERE ps.prod_spec_kwh_kwc IS NOT NULL AND ps.prod_spec_kwh_kwc >= :pmin"
             " AND ps.proba_proprio_occupant >= :prmin"
             + (" AND p.commune = :c" if commune else "") + pisc_cond + surf_cond + conf_cond + corr_cond)
    base = """
        FROM parcel_solar ps
        JOIN parcels p ON p.idu = ps.idu
        LEFT JOIN parcel_terrain t ON t.idu = ps.idu
        LEFT JOIN p_model_bati b ON b.idu = ps.idu
        LEFT JOIN parcel_equipements e ON e.idu = ps.idu"""
    params = {"c": commune, "pmin": potentiel_min, "prmin": proba_occ_min, "psmin": piscine_surf_min,
              "cmin": SEUIL_PISCINE_HAUTE}
    total = int(db.execute(text(f"SELECT count(*) {base} {where}"), params).scalar() or 0)
    # RETOURS-11F3 avenant R11 — en mode PISCINES, la limite de 500 est LEVÉE : le listing sert TOUTES
    # les piscines du filtre actif (le front pagine par 200). Ailleurs, le cap habituel tient.
    lim = total if piscine == "oui" else cap
    rows = db.execute(text(f"""
        SELECT ps.idu, p.commune AS commune,
               round(ps.prod_spec_kwh_kwc)::int AS productible,
               round(ps.azimut_bati_deg)::int AS azimut, ps.azimut_confiance,
               round(t.pente_moy_deg::numeric, 1) AS pente,
               round(b.emprise_bati_m2)::int AS toit_m2,
               (e.piscine IS TRUE) AS piscine, round(e.piscine_surface_m2)::int AS piscine_m2,
               ps.flag_abf AS abf,
               ps.proba_proprio_occupant AS proba_occ,
               s2.tier AS tier_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
        {base}
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = ps.idu AND s2.run_id = :v2run
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        {where}
        ORDER BY {order} LIMIT :lim"""),
        {**params, "v2run": _v2run(db), "run": runs.current(), "lim": lim}).mappings().all()
    items = []
    for r in rows:
        d = dict(r)
        d["etage0"] = bool(r["etage0"])
        d["classement"] = _classement_court(r["tier_v2"], d["etage0"])
        items.append(d)
    # SOLAIRE M1 — millésime LU en base (source_millesime, posé par le builder ingestion/solaire.py) :
    # le bandeau suit la donnée fraîche au lieu d'une date en dur. L'horizon topographique est intégré
    # par PVGIS (usehorizon=1) ; seul l'ombrage de PROXIMITÉ (bâti/arbres) reste non modélisé.
    meta = db.execute(text("SELECT max(source_millesime) AS mil, to_char(max(updated_at), 'YYYY-MM-DD') AS maj "
                           "FROM parcel_solar WHERE prod_spec_kwh_kwc IS NOT NULL")).mappings().first()
    maj = (meta and meta["maj"]) or "—"
    mil = (meta and meta["mil"]) or "PVGIS SARAH3"
    bandeau = (f"Données {mil} · horizon topographique intégré (PVGIS), ombrage de proximité "
               f"(bâti, arbres) non modélisé · potentiel théorique à confirmer sur site.")
    if fmt == "csv":
        # export démarchage : MÊMES colonnes que l'écran, mention Sourcé/Estimé en en-tête (mandat).
        cols = [("idu", "Parcelle (IDU)"),
                ("classement", "Classement [Analyse LABUSE]"),
                ("productible", "Productible kWh/kWc/an [Sourcé — PVGIS/SARAH3]"),
                ("azimut", "Azimut bâti ° [Estimé — élongation]"),
                ("pente", "Pente ° [Sourcé — RGE ALTI 5 m]"),
                ("toit_m2", "Toiture m² emprise [Estimé — proxy]"),
                ("piscine", "Piscine détectée [Estimé — ortho 2025]"),
                ("piscine_m2", "Piscine surface m² [Estimé — ortho 2025]"),
                ("abf", "Périmètre ABF [Sourcé]"),
                ("proba_occ", "Proba propriétaire-occupant % [Estimé — statistique]")]
        buf = io.StringIO()
        buf.write("﻿")  # BOM → accents corrects à l'ouverture Excel
        w = csv.writer(buf, delimiter=";")
        if total > len(items):   # GB-016 — notice EXPLICITE (le JSON portait déjà `tronquee`, pas le CSV)
            w.writerow([f"Export limité aux {len(items)} premières lignes sur {total} — "
                        "affinez les filtres pour un export complet."])
        w.writerow([h for _, h in cols])
        for it in items:
            def _cell(k: str):
                v = it.get(k)
                if k in ("piscine", "abf"):   # « oui » ou vide — jamais un « non/False » affirmé
                    return "oui" if v else ""
                return "" if v is None else v
            w.writerow([_cell(k) for k, _ in cols])
        return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="prospection_solaire.csv"'})
    return {"total": total, "n": len(items), "cap": cap, "tronquee": total > len(items),
            "items": items,
            "source": "PVGIS (Commission européenne) · RGE ALTI (IGN) · BD ORTHO 20 cm 2025 (IGN)",
            "maj": maj, "bandeau": bandeau}


@router.get("/prospection-solaire/parcelle/{idu}")
def prospection_solaire_parcelle(idu: str, db: Session = Depends(get_db)):
    """Mode Ensoleillement — FICHE SOLEIL d'UNE parcelle (barre unique adresse/IDU). MÊMES données
    gelées au 11/07/2026, + le PROFIL MENSUEL (prod_mensuel) et le mois optimal, que la liste ne sert
    pas. Aucun recalcul : lecture seule d'une ligne parcel_solar (mandat SOLAIRE, garde-fou V1 gelée)."""
    if not db.execute(text("SELECT to_regclass('parcel_solar') IS NOT NULL")).scalar():
        raise HTTPException(503, "données solaires indisponibles (table absente).")
    r = db.execute(text("""
        SELECT ps.idu, p.commune AS commune,
               ST_X(ST_Centroid(p.geom)) AS lon, ST_Y(ST_Centroid(p.geom)) AS lat,  -- RETOURS-12 O7 : photo ortho du toit
               round(ps.prod_spec_kwh_kwc)::int AS productible,
               ps.prod_mensuel, ps.mois_optimal,
               round(ps.azimut_bati_deg)::int AS azimut, ps.azimut_confiance,
               round(t.pente_moy_deg::numeric, 1) AS pente,
               round(b.emprise_bati_m2)::int AS toit_m2,
               (e.piscine IS TRUE) AS piscine, round(e.piscine_surface_m2)::int AS piscine_m2,
               ps.flag_abf AS abf, ps.flag_topo_ombrage AS ombrage_topo,
               ps.flag_ombrage_vegetal AS ombrage_vegetal,
               ps.proba_proprio_occupant AS proba_occ,
               s2.tier AS tier_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
        FROM parcel_solar ps
        JOIN parcels p ON p.idu = ps.idu
        LEFT JOIN parcel_terrain t ON t.idu = ps.idu
        LEFT JOIN p_model_bati b ON b.idu = ps.idu
        LEFT JOIN parcel_equipements e ON e.idu = ps.idu
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = ps.idu AND s2.run_id = :v2run
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE ps.idu = :idu"""),
        {"idu": idu, "v2run": _v2run(db), "run": runs.current()}).mappings().first()
    if not r or r["productible"] is None:
        return {"ok": False, "idu": idu,
                "message": "Aucune donnée solaire pour cette parcelle (hors couverture V1 gelée)."}
    d = dict(r)
    d["ok"] = True
    d["etage0"] = bool(r["etage0"])
    d["classement"] = _classement_court(r["tier_v2"], d["etage0"])
    # prod_mensuel = JSONB (12 valeurs kWh/kWc/mois) → liste d'entiers arrondis pour l'affichage (12 barres).
    pm = r["prod_mensuel"]
    d["prod_mensuel"] = [round(float(x)) for x in pm] if isinstance(pm, (list, tuple)) else None
    d["ombrage"] = bool(r["ombrage_topo"]) or bool(r["ombrage_vegetal"])
    mil = db.execute(text("SELECT max(source_millesime) AS mil FROM parcel_solar "
                          "WHERE prod_spec_kwh_kwc IS NOT NULL")).scalar()
    d["millesime"] = mil or "PVGIS SARAH3"
    # RETOURS-13 R31 / RETOURS-15 U5 — NATURE DE LA TOITURE (LiDAR HD IGN, calcul à la demande +
    # cache, seuil de confiance S11). TROIS états servis, jamais confondus : verdict (servi) ·
    # non_determine (pans non nets) · indisponible (échec TECHNIQUE — WMS muet, dépendance
    # absente… cause au journal). `null` = pas de bâtiment sur la parcelle (pas de toit), seul cas
    # où l'écran peut montrer « — ». Un échec ne se déguise JAMAIS en absence de donnée.
    try:
        from ..solaire_toiture import analyse_toiture
        d["toiture"] = analyse_toiture(db, idu)
    except Exception as e:  # noqa: BLE001 — l'échec est DIT à l'écran, la cause au journal
        logging.getLogger("labuse").exception("solaire · toiture LiDAR indisponible (erreur technique)")
        from ..solaire_toiture import payload_indisponible
        d["toiture"] = payload_indisponible(f"{type(e).__name__}: {e}")
    return d


# RETOURS-11F M12 — bande de CONFIANCE par piscine. La détection retient déjà juge FLAIR ≥ 0,30 ×
# probe ≥ 0,50, mais `piscine_confiance` va de 0,44 à 1,0 (mesuré). On sert « haute » (≥ 0,80,
# 7 821 piscines) par défaut ; la bascule « inclure les incertaines » ajoute la bande « moyenne »
# (0,50–0,80, 476) et le reliquat (< 0,50, 2). Sous 0,80, on ne compte pas d'office : Vic a vu ~1 faux
# sur 4, mieux vaut sous-lister que sur-affirmer.
SEUIL_PISCINE_HAUTE = 0.80


def _piscine_conf_filtre(inclure_incertaines: bool) -> str:
    return "" if inclure_incertaines else " AND coalesce(e.piscine_confiance, 0) >= :cmin"


@router.get("/prospection-piscines")
def prospection_piscines(commune: str | None = None,
                         bati: str = "tous",   # tous | oui | non
                         piscine_surf_min: int = 0,   # surface piscine ≥ (m²) — même filtre que la liste
                         inclure_incertaines: bool = False,   # M12 — bascule confiance
                         db: Session = Depends(get_db)):
    """Mode Piscines (pisciniste) — AGRÉGATS de la détection piscines gelée (parcel_equipements) :
    compteur île + par commune (décroissant). Aucun recalcul : une requête d'agrégat (mandat SOLAIRE,
    garde-fou « requêtes d'agrégats uniquement »). Le « bâti » = présence d'emprise bâtie (p_model_bati).
    `piscine_surf_min` aligne le compteur sur le même filtre de surface que le listing.
    RETOURS-11F M12 : par défaut seule la CONFIANCE HAUTE (≥ 0,80) est comptée ; `inclure_incertaines`
    ajoute les bandes moyenne/basse. Les parcelles signalées « pas une piscine » sont TOUJOURS exclues."""
    if not db.execute(text("SELECT to_regclass('parcel_equipements') IS NOT NULL")).scalar():
        raise HTTPException(503, "détection équipements indisponible (table absente).")
    from ..ingestion.ortho_equipements import ensure_corrections
    ensure_corrections(db)   # idempotent — la table existe avant le NOT EXISTS
    join_bati = "LEFT JOIN p_model_bati b ON b.idu = e.idu"
    bati_cond = " AND coalesce(b.emprise_bati_m2, 0) > 0" if bati == "oui" \
        else " AND coalesce(b.emprise_bati_m2, 0) = 0" if bati == "non" else ""
    surf_cond = " AND e.piscine_surface_m2 >= :psmin" if piscine_surf_min else ""
    conf_cond = _piscine_conf_filtre(inclure_incertaines)
    corr_cond = " AND NOT EXISTS (SELECT 1 FROM piscine_corrections pc WHERE pc.idu = e.idu)"
    where = ("WHERE e.piscine IS TRUE" + bati_cond + surf_cond + conf_cond + corr_cond
             + (" AND p.commune = :c" if commune else ""))
    params = {"c": commune, "psmin": piscine_surf_min, "cmin": SEUIL_PISCINE_HAUTE}
    total = int(db.execute(text(
        f"SELECT count(*) FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu {join_bati} {where}"),
        params).scalar() or 0)
    communes = db.execute(text(f"""
        SELECT p.commune AS commune, count(*)::int AS n
        FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu {join_bati} {where}
        GROUP BY p.commune ORDER BY n DESC"""), params).mappings().all()
    maj = db.execute(text("SELECT to_char(max(updated_at), 'YYYY-MM-DD') AS maj "
                          "FROM parcel_equipements WHERE piscine IS TRUE")).scalar()
    # Bandes de confiance (informatif, hors filtres commune/bâti/surface) : pour DIRE à l'écran combien
    # de piscines « incertaines » la bascule ajouterait, et combien ont été retirées par un humain.
    bandes = db.execute(text(
        "SELECT count(*) FILTER (WHERE coalesce(piscine_confiance,0) >= :cmin) AS haute, "
        "count(*) FILTER (WHERE coalesce(piscine_confiance,0) < :cmin) AS incertaines "
        "FROM parcel_equipements e WHERE e.piscine IS TRUE "
        "AND NOT EXISTS (SELECT 1 FROM piscine_corrections pc WHERE pc.idu = e.idu)"),
        {"cmin": SEUIL_PISCINE_HAUTE}).mappings().first() or {}
    n_corrigees = int(db.execute(text("SELECT count(*) FROM piscine_corrections")).scalar() or 0)
    # LOT8a (OUTILS-FINALE) — le SEUIL de rétention est DIT : parcel_equipements.piscine ne retient que
    # les détections passant la porte de confiance (juge FLAIR ≥ 0,30 × probe ≥ 0,50, config
    # detection_ortho.yaml) — des détections plus incertaines sont donc EXCLUES du compte. Écrit à l'écran.
    return {"total": total, "communes": [dict(c) for c in communes],
            "confiance": {"haute": int(bandes.get("haute") or 0),
                          "incertaines": int(bandes.get("incertaines") or 0),
                          "seuil_haute": SEUIL_PISCINE_HAUTE, "inclure_incertaines": inclure_incertaines},
            "corrigees": n_corrigees,   # « pas une piscine » signalées par un humain, exclues du service
            "source": "Détection FLAIR sur BD ORTHO 20 cm 2025 (IGN) — précision mesurée ~90,7 % ; "
                      "confiance HAUTE (≥ 0,80) servie par défaut, « incertaines » sur bascule ; à confirmer sur site",
            "maj": maj or "—"}


@router.get("/prospection-piscines/points")
def prospection_piscines_points(commune: str | None = None, bati: str = "tous",
                                piscine_surf_min: int = 0, inclure_incertaines: bool = False,
                                db: Session = Depends(get_db)):
    """LOT8b (OUTILS-FINALE) — TOUTES les piscines de l'île (ou de la commune) en marqueurs, pour
    « 💧 Voir sur la carte » : centroïdes des parcelles à piscine (kind='piscine'), servis en GeoJSON.
    Aucun plafond de listing (l'écran cap à 500, la carte doit TOUT montrer). Agrégat lecture seule.
    RETOURS-11F M12 : chaque point porte sa bande de confiance (haute/moyenne/basse) ; défaut = haute
    seule ; corrigées « pas une piscine » toujours exclues."""
    if not db.execute(text("SELECT to_regclass('parcel_equipements') IS NOT NULL")).scalar():
        raise HTTPException(503, "détection équipements indisponible (table absente).")
    from ..ingestion.ortho_equipements import ensure_corrections
    ensure_corrections(db)
    join_bati = "LEFT JOIN p_model_bati b ON b.idu = e.idu"
    bati_cond = " AND coalesce(b.emprise_bati_m2, 0) > 0" if bati == "oui" \
        else " AND coalesce(b.emprise_bati_m2, 0) = 0" if bati == "non" else ""
    surf_cond = " AND e.piscine_surface_m2 >= :psmin" if piscine_surf_min else ""
    conf_cond = _piscine_conf_filtre(inclure_incertaines)
    corr_cond = " AND NOT EXISTS (SELECT 1 FROM piscine_corrections pc WHERE pc.idu = e.idu)"
    where = ("WHERE e.piscine IS TRUE" + bati_cond + surf_cond + conf_cond + corr_cond
             + (" AND p.commune = :c" if commune else ""))
    rows = db.execute(text(
        f"""SELECT e.idu, p.commune, round(e.piscine_surface_m2::numeric, 0) AS m2, e.piscine_confiance AS conf,
                   ST_X(ST_Transform(p.centroid, 4326)) AS lon, ST_Y(ST_Transform(p.centroid, 4326)) AS lat
            FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu {join_bati} {where}
            AND p.centroid IS NOT NULL"""),
        {"c": commune, "psmin": piscine_surf_min, "cmin": SEUIL_PISCINE_HAUTE}).mappings().all()

    def _bande(conf):
        if conf is None:
            return "moyenne"
        return "haute" if conf >= SEUIL_PISCINE_HAUTE else ("moyenne" if conf >= 0.5 else "basse")
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
         "properties": {"kind": "piscine", "idu": r["idu"], "commune": r["commune"],
                        "piscine_m2": float(r["m2"]) if r["m2"] is not None else None,
                        "confiance": round(float(r["conf"]), 2) if r["conf"] is not None else None,
                        "bande": _bande(r["conf"])}}
        for r in rows]}


class PasUnePiscineIn(BaseModel):
    idu: str
    motif: str | None = None


@router.post("/prospection-piscines/pas-une-piscine")
def piscine_pas_une(body: PasUnePiscineIn, request: Request, db: Session = Depends(get_db)):
    """RETOURS-11F M12 — « pas une piscine » : un signal HUMAIN qui retire la parcelle du service
    (compteur, carte) DÈS maintenant et sera repris au prochain calcul de détection. Idempotent
    (ON CONFLICT). Trace le compte émetteur (audit) ; l'exclusion est GLOBALE (qualité de donnée)."""
    from ..ingestion.ortho_equipements import ensure_corrections
    ensure_corrections(db)
    compte_id = getattr(getattr(request, "state", None), "compte_id", None)
    db.execute(text(
        "INSERT INTO piscine_corrections (idu, motif, compte_id) VALUES (:i, :m, :c) "
        "ON CONFLICT (idu) DO UPDATE SET motif = EXCLUDED.motif, created_at = now()"),
        {"i": body.idu, "m": body.motif, "c": compte_id})
    db.commit()
    n = int(db.execute(text("SELECT count(*) FROM piscine_corrections")).scalar() or 0)
    return {"ok": True, "idu": body.idu, "corrigees_total": n}


# ───────────────────────── M05 — VÉLOCITÉ ADMIN ─────────────────────────
# M10 : le VRAI délai d'instruction dépôt→autorisation, en MÉDIANE (robuste aux outliers).
# La date de dépôt (DR_DEPOT) manquait de `sitadel_permits` ; M10 l'a rapatriée de la source
# SDES/Dido dans la table additive `m10_permit_delais` (cf. ingestion.permit_delais_m10).
#
# HONNÊTETÉ (3 limites consignées, exposées telles quelles au client) :
#  1. CENSURE STRUCTURELLE : le fichier Sitadel ne contient QUE des dossiers ACCORDÉS
#     (0 dossier « déposé non tranché ») → le « taux de dossiers en cours » n'est PAS
#     observable ici. La médiane est conditionnelle à « a fini par être autorisé ».
#  2. SURVIE DES COHORTES RÉCENTES : un dépôt récent instruit lentement n'est pas encore
#     visible (biais à la baisse) → la médiane de tête EXCLUT les 12 derniers mois de dépôts
#     (cohortes non mûres), séparément comptés (`en_cours_estime` = non mesurable → null).
#  3. QUALITÉ SOURCE : DR_DEPOT est au MOIS (délai en mois, pas en jours) et ~15 % des lignes
#     ont dépôt > autorisation (erreur de saisie) → EXCLUES (`valide=false`), taux affiché.
# Indicateur HISTORIQUE, pas une promesse de délai futur (disclaimer).

_VELOCITE_MATURITE_MOIS = 12  # cohortes de dépôt < (dernier dépôt − 12 mois) = « mûres »


@router.get("/velocite")
def velocite(fmt: str = "json", nature: str | None = None, db: Session = Depends(get_db)):
    # borne de maturité : dernier mois de dépôt observé − 12 mois (au-delà = cohorte non mûre)
    cutoff = db.execute(text(
        "SELECT (max(date_depot) - make_interval(months => :m))::date "
        "FROM m10_permit_delais WHERE valide"), {"m": _VELOCITE_MATURITE_MOIS}).scalar()
    rows = db.execute(text("""
        SELECT commune,
          count(*) FILTER (WHERE valide) AS n_valide,
          count(*) FILTER (WHERE valide AND date_depot <= :cutoff) AS n_mur,
          count(*) FILTER (WHERE valide AND date_depot > :cutoff) AS n_recent_exclu,
          count(*) FILTER (WHERE NOT valide AND date_depot IS NOT NULL
                             AND date_autorisation IS NOT NULL) AS n_exclus_qualite,
          round(percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois)
                FILTER (WHERE valide AND date_depot <= :cutoff)) AS delai_median_mois,
          round(percentile_cont(0.25) WITHIN GROUP (ORDER BY delai_mois)
                FILTER (WHERE valide AND date_depot <= :cutoff)) AS delai_p25_mois,
          round(percentile_cont(0.75) WITHIN GROUP (ORDER BY delai_mois)
                FILTER (WHERE valide AND date_depot <= :cutoff)) AS delai_p75_mois
        FROM m10_permit_delais
        WHERE (CAST(:nat AS text) IS NULL OR nature = :nat)
        GROUP BY commune HAVING count(*) FILTER (WHERE valide) > 0
        ORDER BY n_valide DESC"""),
        {"cutoff": cutoff, "nat": nature}).mappings().all()
    data = [dict(r) for r in rows]
    # M137-Z — plus de CLASSEMENT par médiane (le `rang_delai` disparaît) : avec des médianes de 8-9
    # mois PARTOUT et un IQR ~6 mois, l'écart inter-communes est du BRUIT servi comme une info (audit
    # AUDIT_OUTILS_COMMUNE §2.2). On MESURE l'homogénéité et on la DIT ; on sert la TRANCHE p25-p75.
    meds = [c["delai_median_mois"] for c in data if c["delai_median_mois"] is not None]
    spread = (max(meds) - min(meds)) if meds else None
    homogene = spread is not None and spread <= 3   # écart des médianes ≤ 3 mois = communes semblables
    # Point 39 — TENDANCE : médiane des cohortes ANCIENNES vs RÉCENTES (coupe au milieu de la période).
    trend = {r["commune"]: r for r in db.execute(text("""
        WITH mid AS (SELECT (min(date_depot) + (max(date_depot) - min(date_depot)) / 2) AS m
                     FROM m10_permit_delais WHERE valide AND date_depot <= :cutoff)
        SELECT commune,
          round(percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois)
                FILTER (WHERE date_depot < (SELECT m FROM mid))) AS med_ancien,
          round(percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois)
                FILTER (WHERE date_depot >= (SELECT m FROM mid))) AS med_recent,
          count(*) FILTER (WHERE date_depot < (SELECT m FROM mid)) AS n_a,
          count(*) FILTER (WHERE date_depot >= (SELECT m FROM mid)) AS n_r
        FROM m10_permit_delais
        WHERE valide AND date_depot <= :cutoff AND (CAST(:nat AS text) IS NULL OR nature = :nat)
        GROUP BY commune"""), {"cutoff": cutoff, "nat": nature}).mappings()}
    for c in data:
        t = trend.get(c["commune"])
        tend = None
        if t and t["n_a"] and t["n_r"] and t["n_a"] >= 8 and t["n_r"] >= 8 \
                and t["med_ancien"] is not None and t["med_recent"] is not None:
            diff = float(t["med_recent"]) - float(t["med_ancien"])
            tend = "accelere" if diff <= -1 else "ralentit" if diff >= 1 else "stable"
        c["tendance"] = tend
    # période de couverture = années d'AUTORISATION (le fichier Sitadel des dossiers accordés)
    an = db.execute(text(
        "SELECT min(extract(year FROM date_autorisation))::int lo, "
        "max(extract(year FROM date_autorisation))::int hi "
        "FROM m10_permit_delais WHERE valide")).mappings().first()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="velocite_admin.csv"'})
    return {
        "indicateur": "Délai d'instruction dépôt → autorisation (tranche p25–p75)",
        "unite": "mois", "nature": nature, "cohortes": f"{an['lo']}–{an['hi']}",
        "maturite_cutoff": cutoff.isoformat() if cutoff else None,
        # M137-Z — l'homogénéité DITE : les communes se ressemblent, ne pas les classer sur la médiane.
        "communes_homogenes": homogene, "ecart_medianes_mois": spread,
        "note_homogeneite": ("Les délais se ressemblent d'une commune à l'autre (écart des médianes "
                             f"≈ {spread} mois) : pas de classement, la commune ne fait pas la différence."
                             if homogene else None),
        "note": ("Tranche p25–p75 (pas une médiane seule) : la moitié des dossiers y tombe. Dépôts des 12 "
                 "derniers mois exclus (cohortes non mûres, biais de survie). Lignes dépôt>autorisation exclues."),
        "censure": ("Source Sitadel = dossiers ACCORDÉS uniquement : refusés et en cours "
                    "d'instruction non observables → taux de dossiers en cours non mesurable ici."),
        "disclaimer": "Indicateur HISTORIQUE (2013+), pas une promesse de délai futur.",
        "communes": data}


# ───────────────────────── M07 — FONCIER FANTÔME ─────────────────────────
# ⚠️ DORMANT (M137-N, 20/08/2026) — l'outil « Foncier fantôme » (front M07) est RETIRÉ du produit :
# nom non fidèle au contenu (74 % successions et structures collectives, pas des sociétés fantômes),
# levier « dirigeant inactif » à 0. Cet endpoint RESTE servi (aucun autre consommateur mesuré : ni
# partners, ni PDF, ni Copilote — le concept-route a été retiré) + testé. Signal succession → facette.
@router.get("/fantome")
def fantome(commune: str | None = None, limit: int = 300, offset: int = Query(0, ge=0),  # GB-029
            db: Session = Depends(get_db)) -> dict:
    limit = max(1, min(limit, 600))  # « voir plus » pagine par offset
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, s2.tier AS statut,
               pm.siren, pm.denomination,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren) AS inpi_introuvable,
               EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false) AS dirigeant_inactif
        -- carte pilotée par IDU (module-hl), pas par géométrie : ST_AsGeoJSON retiré (payload/latence)
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        -- M137-L : « constructible » = la parcelle PASSE LA CASCADE (tier v2 hors étage 0), la
        -- définition qui fait foi depuis M129. Remplace le vestige matrice `d.q_score >= 50` (q_score
        -- NULL sur le run servi q_v10_m129 → l'outil renvoyait 0 — cf. PDF M136 / tuiles M137-D).
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
          AND s2.tier IS NOT NULL AND NOT (d.status IN ('exclue', 'faux_positif_probable'))
          AND pm.groupe NOT IN (1, 2, 3, 4, 9)
          AND pm.siren IS NOT NULL
          AND (NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren)
               OR EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false))
        ORDER BY s2.rang ASC NULLS LAST LIMIT :lim OFFSET :off"""),
        {"c": commune, "run": runs.current(), "v2run": _v2run(db), "lim": limit, "off": offset}).mappings().all()
    true_total = int(db.execute(text(
        """SELECT count(*) FROM parcels p
           JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
           JOIN parcelle_personne_morale pm ON pm.idu = p.idu
           WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
             AND s2.tier IS NOT NULL AND NOT (d.status IN ('exclue', 'faux_positif_probable'))
             AND pm.groupe NOT IN (1, 2, 3, 4, 9) AND pm.siren IS NOT NULL
             AND (NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren)
                  OR EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false))"""),
        {"c": commune, "run": runs.current(), "v2run": _v2run(db)}).scalar() or 0)
    return {"total": true_total, "affiches": offset + len(rows),
            "has_more": offset + len(rows) < true_total, "items": [{
        **{k: r[k] for k in ("idu", "surface_m2", "statut", "siren", "denomination")},
        "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
        "verrou": "société introuvable au registre" if r["inpi_introuvable"] else "dirigeant inactif (registre des entreprises)",
        "levier": "notaire / recherche du représentant" if r["inpi_introuvable"] else "rachat de parts / contact liquidateur",
    } for r in rows]}


# ───────────────────────── M06 — MODE BAILLEUR ─────────────────────────
# ⚠️ DORMANT (M137-N, 20/08/2026) — l'outil « Mode bailleur » (front M06) est RETIRÉ du produit.
# L'endpoint /modules/bailleur RESTE servi (aucun autre consommateur mesuré : ni partners, ni PDF, ni
# Copilote — le concept-route a été retiré) + testé.
def _sru_bloc(db: Session, commune: str) -> dict | None:
    """Contexte SRU d'une commune (données réelles commune_contexte_sru) : statut + déficit LLS
    DÉRIVÉ des chiffres sourcés (nb_lls, taux, objectif) — jamais inventé. None si pas de donnée."""
    r = db.execute(text(
        "SELECT statut, taux_lls, objectif_pct, prelevement_eur, millesime, "
        "(detail->>'nb_lls')::float AS nb_lls FROM commune_contexte_sru WHERE commune = :c"),
        {"c": commune}).mappings().first()
    if not r:
        return None
    nb_lls, taux, obj = r["nb_lls"], (float(r["taux_lls"]) if r["taux_lls"] is not None else None), \
        (float(r["objectif_pct"]) if r["objectif_pct"] is not None else None)
    deficit = None
    if nb_lls and taux and obj and obj > taux:
        # unités LLS manquantes pour atteindre l'objectif : nb_lls × (objectif − taux) / taux
        deficit = round(float(nb_lls) * (obj - taux) / taux)
    return {"statut": r["statut"], "taux_lls": taux, "objectif_pct": obj,
            "deficit_logements": deficit,
            "prelevement_eur": float(r["prelevement_eur"]) if r["prelevement_eur"] is not None else None,
            "millesime": r["millesime"]}


@router.get("/bailleur")
def bailleur(commune: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> dict:
    # GB-030 — l'endpoint (DORMANT) faisait un JOIN SPATIAL ÎLE-ENTIÈRE (`ST_Intersects` sur les 431k
    # parcelles × QPV) quand `commune` était absente → ~3 min de silence. `commune` devient OBLIGATOIRE
    # (422 si absente) : le scan est BORNÉ à une commune (1-8 s), plus jamais le balayage insulaire.
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, s2.tier AS statut,
               d.q_score, d.a_score, r.sdp_residuelle_m2,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0, cs.statut AS sru_statut,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        JOIN spatial_layers q ON q.kind = 'qpv' AND ST_Intersects(p.geom_2975, q.geom_2975)
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN commune_contexte_sru cs ON cs.commune = p.commune
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND s2.tier IN ('brulante', 'chaude', 'reserve_fonciere', 'a_creuser')
        ORDER BY (cs.statut = 'carencee') DESC NULLS LAST, COALESCE(r.sdp_residuelle_m2, 0) DESC LIMIT 500"""),
        {"c": commune, "run": runs.current(), "v2run": _v2run(db)}).mappings().all()
    true_total = len(rows) if len(rows) < 500 else int(db.execute(text(
        """SELECT count(*) FROM parcels p
           JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
           WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
             AND s2.tier IN ('brulante', 'chaude', 'reserve_fonciere', 'a_creuser')
             AND EXISTS (SELECT 1 FROM spatial_layers q WHERE q.kind = 'qpv'
                         AND ST_Intersects(p.geom_2975, q.geom_2975))"""),
        {"c": commune, "run": runs.current(), "v2run": _v2run(db)}).scalar() or 0)
    sru = _sru_bloc(db, commune) if commune else None
    n_carencees = len({r["commune"] for r in rows if r["sru_statut"] == "carencee"}) if not commune else None
    return {"total": true_total, "affiches": len(rows), "sru": sru, "n_communes_carencees": n_carencees,
            "lecture_lls": ("QPV : TVA 2,1 % (au lieu de 8,5 % DOM), abattement TFPB 30 %, "
                            "éligibilité LLS/LLTS renforcée — bilan bailleur à instruire au cas par cas."),
            "items": [{**{k: r[k] for k in ("idu", "commune", "surface_m2", "statut", "q_score", "a_score")},
                       "carencee": r["sru_statut"] == "carencee",
                       "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                       "sdp": r["sdp_residuelle_m2"], "geom": json.loads(r["g"])} for r in rows]}


# ───────────────────────── M09 — COURRIER PROPRIÉTAIRE ─────────────────────────

class CourriersIn(BaseModel):
    idus: list[str]
    contexte: str = "standard"   # standard | indivision | succession


_COURRIER = {
    "standard": ("Objet : votre parcelle cadastrée {ref} à {commune}\n\n"
                 "Madame, Monsieur,\n\n"
                 "Votre parcelle cadastrée {ref} ({surface} m²), située à {commune}, présente à notre "
                 "analyse un réel potentiel. Nous accompagnons des porteurs de projets locaux et serions "
                 "heureux d'échanger avec vous, sans aucun engagement, sur les possibilités qu'offre "
                 "votre bien — y compris si vous n'envisagez pas de vendre à court terme.\n\n"
                 "Nous nous tenons à votre disposition.\n\nCordialement,\n{signature}"),
    "indivision": ("Objet : votre parcelle cadastrée {ref} à {commune} — situation d'indivision\n\n"
                   "Madame, Monsieur,\n\n"
                   "Votre parcelle cadastrée {ref} ({surface} m²) à {commune} semble détenue en "
                   "indivision. Ces situations rendent souvent la gestion du bien complexe (entretien, "
                   "fiscalité, décisions partagées). Nous pouvons étudier avec vous et vos co-indivisaires "
                   "des solutions équitables — rachat de quote-part, sortie amiable d'indivision — avec "
                   "l'appui de notaires locaux.\n\nCordialement,\n{signature}"),
    "succession": ("Objet : votre parcelle cadastrée {ref} à {commune}\n\n"
                   "Madame, Monsieur,\n\n"
                   "Dans le cadre d'une succession, la parcelle cadastrée {ref} ({surface} m²) à {commune} "
                   "peut représenter une charge autant qu'un patrimoine. Si vous envisagez d'en céder tout "
                   "ou partie, nous pouvons vous proposer une étude sérieuse et confidentielle de sa "
                   "valeur, en lien avec votre notaire.\n\nCordialement,\n{signature}"),
}


@router.post("/courriers")
def courriers(body: CourriersIn, db: Session = Depends(get_db)) -> dict:
    if body.contexte not in _COURRIER:
        raise HTTPException(422, "contexte inconnu")
    out = []
    for idu in body.idus[:100]:
        r = db.execute(text("SELECT idu, commune, section, numero, round(surface_m2) s FROM parcels WHERE idu = :i"),
                       {"i": idu}).mappings().first()
        if not r:
            out.append({"idu": idu, "erreur": "parcelle inconnue"})
            continue
        ref = f"{r['section']} {r['numero']}"
        out.append({"idu": idu, "texte": _COURRIER[body.contexte].format(
            ref=ref, commune=r["commune"], surface=int(r["s"] or 0), signature="LABUSE — prospection foncière")})
    return {"contexte": body.contexte, "n": len(out), "courriers": out,
            "rappel_identite": ("Identité du propriétaire : workflow SPF/CERFA existant "
                                "(fiche → export SPF) — aucune donnée nominative automatisée.")}


# ───────────────────────── M10 — DUE DILIGENCE NOTAIRE ─────────────────────────

class DueDiligenceIn(BaseModel):
    refs: str   # texte libre : IDU complets ou « SECTION NUMERO » séparés par lignes/virgules


_SEV_RISK = {"fort": 70, "moyen": 50, "faible": 30, "info": 10}


def _diligence_dossier(db: Session, parcel_id: int, idu: str) -> dict:
    """Point 42 — dossier de diligence DÉTERMINISTE depuis les facteurs EXISTANTS (cascade + proprio) :
    checklist des points à vérifier avant d'acheter + score de risque consolidé. Aucun re-scoring.
    PRIVACY : personne morale nommée (public) ; particulier JAMAIS nommé."""
    concerns = db.execute(text(
        "SELECT cr.layer_name, cr.severity, cr.result, cr.detail FROM dryrun_cascade_results cr "
        "WHERE cr.run_label = :run AND cr.parcel_id = :pid "
        "  AND cr.result IN ('HARD_EXCLUDE', 'SOFT_FLAG', 'UNKNOWN') "
        "ORDER BY CASE cr.result WHEN 'HARD_EXCLUDE' THEN 0 WHEN 'SOFT_FLAG' THEN 1 ELSE 2 END, "
        "         CASE cr.severity WHEN 'fort' THEN 0 WHEN 'moyen' THEN 1 WHEN 'faible' THEN 2 ELSE 3 END"),
        {"run": runs.current(), "pid": parcel_id}).mappings().all()
    checklist = [{"layer": c["layer_name"], "severity": c["severity"], "result": c["result"],
                  "detail": c["detail"]} for c in concerns]
    # M137-U — ZNIEFF : contrainte HORS CASCADE (ne remonte pas dans dryrun_cascade_results) ; on la
    # lit géométriquement dans spatial_layers pour qu'elle apparaisse AUSSI dans l'entrée « lot »
    # (comme dans l'entrée « parcelle » / servitudes). Vigilance, jamais un blocage (severity faible).
    for z in db.execute(text(
            "SELECT sl.subtype, sl.name FROM spatial_layers sl JOIN parcels p ON p.id = :pid "
            "WHERE sl.kind = 'znieff' AND sl.geom_2975 IS NOT NULL "
            "  AND ST_Intersects(sl.geom_2975, p.geom_2975)"), {"pid": parcel_id}).mappings().all():
        checklist.append({"layer": "ZNIEFF", "severity": "faible", "result": "SOFT_FLAG",
                          "detail": f"{z['subtype'] or 'ZNIEFF'} — {z['name']} : contrainte "
                                    "environnementale (études d'impact, risque de recours), n'interdit pas de construire"})
    pm = db.execute(text("SELECT denomination, siren FROM parcelle_personne_morale WHERE idu = :i"),
                    {"i": idu}).mappings().first()
    proprio = ({"type": "personne_morale", "denomination": pm["denomination"], "siren": pm["siren"]}
               if pm and pm["denomination"] else {"type": "particulier"})
    if any(c["result"] == "HARD_EXCLUDE" for c in checklist):
        risque = 100
    else:
        risque = max([_SEV_RISK.get(c["severity"], 20) for c in checklist if c["result"] == "SOFT_FLAG"] or [0])
    if proprio["type"] == "particulier" and risque < 100:   # accès proprio via SPF (démarche +)
        risque = min(100, risque + 10)
    return {"checklist": checklist, "risque": risque, "proprio": proprio}


@router.post("/duediligence")
def duediligence(body: DueDiligenceIn, db: Session = Depends(get_db)) -> dict:
    import re
    tokens = [t.strip().upper().replace(" ", "") for t in re.split(r"[\n,;]+", body.refs) if t.strip()]
    v2run = _v2run(db)
    items = []
    for t in tokens[:60]:
        row = db.execute(text("""
            SELECT p.id AS parcel_id, p.idu, p.commune, round(p.surface_m2) AS surface_m2,
                   s2.tier AS statut, d.completeness_score,
                   s2.tier AS tier_v2, s2.rang AS rang_v2,
                   (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
                   (SELECT count(*) FROM dryrun_cascade_results cr WHERE cr.run_label = :run
                     AND cr.parcel_id = p.id AND cr.result = 'SOFT_FLAG') AS flags,
                   (SELECT count(*) FROM dryrun_cascade_results cr WHERE cr.run_label = :run
                     AND cr.parcel_id = p.id AND cr.result = 'HARD_EXCLUDE') AS exclusions
            FROM parcels p
            LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
            WHERE p.idu = :t OR (p.section || p.numero) = :t OR (p.section || lpad(p.numero, 4, '0')) = :t
            LIMIT 1"""), {"t": t, "run": runs.current(), "v2run": v2run}).mappings().first()
        if row:
            dossier = _diligence_dossier(db, row["parcel_id"], row["idu"])
            items.append({k: row[k] for k in row.keys() if k != "parcel_id"}
                         | {"etage0": bool(row["etage0"]), **dossier,
                            "pdf": f"/parcels/{row['idu']}/export.pdf?source={runs.current()}"})
        else:
            items.append({"ref": t, "erreur": "référence introuvable"})
    ok = [i for i in items if "idu" in i]
    # M137-T — le bloc NON COUVERT (source unique servitudes.NON_COUVERT) est REPORTÉ sur l'entrée
    # « un lot » : un lot sans flag cascade ne doit JAMAIS afficher un « RAS » muet — il dit ce que
    # la base ne couvre pas, à l'échelle des 60 parcelles comme sur une seule.
    from .servitudes import NON_COUVERT
    return {"n_demandes": len(tokens), "n_trouvees": len(ok), "items": items,
            "non_couvert": NON_COUVERT}


# ───────────────── M22 + BILAN — ÉTUDE DE FAISABILITÉ BIDIRECTIONNELLE ─────────────────
# RÉUTILISE le moteur existant (faisabilite/engine + bilan) — rien de recalculé à la main.
# Ratios : étage 3 m, place 25 m² (config plu YAML) ; m²/logement = paramètre AFFICHÉ (défaut 60).

_DVF_COUVERTURE_CACHE: dict = {}


def _dvf_couverture(db: Session) -> dict:
    """Période RÉELLE des transactions DVF en base (min/max date_mutation). Mise en cache
    process (la donnée ne bouge qu'à une ré-ingestion). Format prêt à afficher."""
    if "v" not in _DVF_COUVERTURE_CACHE:
        r = db.execute(text("SELECT to_char(min(date_mutation),'YYYY') AS d0, "
                            "to_char(max(date_mutation),'YYYY-MM') AS d1, count(*) AS n "
                            "FROM dvf_mutations")).mappings().first()
        MOIS = {"01": "janv.", "02": "févr.", "03": "mars", "04": "avr.", "05": "mai", "06": "juin",
                "07": "juil.", "08": "août", "09": "sept.", "10": "oct.", "11": "nov.", "12": "déc."}
        d1 = r["d1"] or ""
        libelle = None
        if d1 and "-" in d1:
            an, mo = d1.split("-")
            libelle = f"ventes jusqu'à {MOIS.get(mo, mo)} {an}"
        _DVF_COUVERTURE_CACHE["v"] = {"depuis": r["d0"], "jusqu_au": d1, "n": r["n"], "libelle": libelle}
    return _DVF_COUVERTURE_CACHE["v"]


_MOIS_FR = {"01": "janv.", "02": "févr.", "03": "mars", "04": "avr.", "05": "mai", "06": "juin",
            "07": "juil.", "08": "août", "09": "sept.", "10": "oct.", "11": "nov.", "12": "déc."}


def _fraicheur_couche(db: Session, source_name: str) -> dict:
    """M32 Phase B §2 — objet `fraicheur` STRUCTURÉ d'une couche, lu depuis le POINT DE CALCUL
    UNIQUE `data_sources` (renseigné par l'ingester via persist_millesime). L'API ne fabrique PAS
    de phrase : elle sert {horizon, horizon_libelle court, millesime, cadence, prochain} et le front
    formate. `horizon` NULL → « horizon inconnu » (spec §6 : jamais inventé)."""
    r = db.execute(text(
        "SELECT source_millesime, source_horizon_at, source_cadence, prochain_millesime_at "
        "FROM data_sources WHERE name ILIKE :n ORDER BY id LIMIT 1"), {"n": source_name}).mappings().first()
    if not r:
        return {"horizon": None, "horizon_libelle": "horizon inconnu", "millesime": None,
                "cadence": None, "prochain": None}
    h = r["source_horizon_at"]
    lib = "horizon inconnu"
    if h is not None:
        lib = f"jusqu'à {_MOIS_FR.get(f'{h.month:02d}', str(h.month))} {h.year}"
    return {"horizon": h.isoformat() if h else None, "horizon_libelle": lib,
            "millesime": r["source_millesime"], "cadence": r["source_cadence"],
            "prochain": r["prochain_millesime_at"].isoformat() if r["prochain_millesime_at"] else None}


def _faisa_step_prov(source: str, prov: str) -> str:
    """Provenance d'AFFICHAGE d'un step (transparence — n'altère AUCUN calcul). Si le moteur l'a
    posée (bilan), on la garde ; sinon (steps capacité, prov='') on la DÉRIVE du libellé de source :
    article PLU / géométrie réelle → « sourcee » ; hypothèse → « estimee » ; calcul dérivé → « derive »."""
    if prov:
        return prov
    s = (source or "").lower()
    if "hypoth" in s:
        return "estimee"
    if "dériv" in s or "deriv" in s:
        return "derive"
    if "art." in s or "zone" in s or "géomét" in s or "geomet" in s or "cadastr" in s or "règl" in s or "regl" in s:
        return "sourcee"
    return "estimee"   # défaut prudent : jamais présenter un chiffre non sourcé comme « sourcé »


@router.get("/faisabilite/{idu}")
def faisabilite_sens1(idu: str, db: Session = Depends(get_db)) -> dict:
    """SENS 1 (parcelle → programme) : « que peut accueillir ce terrain ? » + bilan économique."""
    _check_idu(idu)   # M-K (P2-31)
    from ..faisabilite.au_ouverture import DELAISSE_MAX_M2
    from ..faisabilite.bilan import sector_price, compute_bilan_servi
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses

    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, "Parcelle inconnue")
    out: dict = {"idu": idu}
    # M30 item 5 (anomalie AI1886, 9 m² servie avec un bilan R+6) : sous DELAISSE_MAX_M2
    # (50 m² — seuil UNIQUE, celui des délaissés de voisinage d'au_ouverture), un bilan
    # promoteur est un chiffre qui ment → il n'est PAS servi. LECTURE seulement : le moteur
    # de faisabilité et le scoring ne bougent pas ; la capacité reste servie (steps tracés).
    delaisse = row["s"] is not None and float(row["s"]) < DELAISSE_MAX_M2
    out["delaisse"] = ({"surface_m2": int(row["s"]), "seuil_m2": int(DELAISSE_MAX_M2),
                        "libelle": f"délaissé ({int(row['s'])} m²) — bilan non servi "
                                   f"sous {int(DELAISSE_MAX_M2)} m²"}
                       if delaisse else None)
    fz = parcel_faisabilite(db, row["id"])
    if fz:
        _ctx, f = fz
        out["capacite"] = {"zone": f.zone, "verdict": f.verdict, "calibree": f.calibree,
                           "fourchette": f.fourchette, "hypotheses": f.hypotheses,
                           "bandeau": f.bandeau,
                           # M11 Surface C : les 11 étapes TRACÉES du moteur, exposées telles quelles
                           # (aucune reformulation). `prov` d'affichage dérivé du `source` quand le
                           # moteur ne le pose pas (les steps capacité ont prov='' ; le sens reste exact).
                           "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur,
                                      "source": s.source, "prov": _faisa_step_prov(s.source, s.prov)}
                                     for s in f.steps],
                           "avertissements": f.avertissements, "modulation": f.modulation}
    else:
        out["capacite"] = None
    # Source unique (mandat hypothèses bilan, Vic 28/07/2026) : charger(), plus de défauts directs.
    hyp = Hypotheses.charger()
    prix = sector_price(db, row["id"], hyp)
    out["marche"] = {k: prix.get(k) for k in ("type_prix", "median", "q1", "q3", "n", "fiabilite",
                                              "tendance", "volatilite", "radius_m") if k in prix}
    # P14 (dernière passe) : fraîcheur DVF — période RÉELLE couverte (SQL), pour que l'utilisateur
    # sache de QUAND datent les prix (« fiabilité fragile » reste, c'est le n de ventes).
    out["marche"]["dvf_couverture"] = _dvf_couverture(db)
    # M32 Phase B §2 : objet `fraicheur` STRUCTURÉ (horizon/millesime/cadence) lu du point de vérité
    # data_sources — vocabulaire unique de la spec millésime, généralisable aux autres modules.
    out["marche"]["fraicheur"] = _fraicheur_couche(db, "DVF / valeurs foncières")
    # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — LE MÊME bilan que la fiche
    # (compute_bilan_servi : charge cohérente à l'euro, prix de sortie neuf, non calculable servi).
    # M30 item 5 : pas de bilan sur un délaissé (le libellé `delaisse` dit pourquoi)
    b, ps = compute_bilan_servi(db, row["id"], fz) if (fz and not delaisse) else (None, None)
    if b is None:
        out["bilan"] = None
    else:
        out["bilan"] = {k: v for k, v in b.__dict__.items() if not k.startswith("_")}
        out["bilan"]["non_calculable"] = bool(ps["non_calculable"])
        out["bilan"]["niveau_prix_neuf"] = None if ps["non_calculable"] else ps["niveau"]
        out["bilan"]["prix_neuf_label"] = ps["motif"] if ps["non_calculable"] else ps["label"]
        out["bilan"]["prix_neuf_repli_ile"] = ps["repli_ile"]
    # fiscal / leviers (bilan promoteur — données en base + hypothèses ÉTIQUETÉES)
    qpv = bool(db.execute(text("""SELECT 1 FROM spatial_layers q JOIN parcels p ON p.idu = :i
        WHERE q.kind = 'qpv' AND ST_Intersects(p.geom_2975, q.geom_2975) LIMIT 1"""), {"i": idu}).scalar())
    out["fiscal"] = {
        "qpv": qpv,
        "tva": ("2,1 % (LLS en QPV — LODEOM) au lieu de 8,5 % DOM" if qpv
                else "8,5 % (taux DOM) — 2,1 % possible en LLS selon montage"),
        # M58-P1 (f) : le taux communal n'est PAS ingéré — on ne l'INVENTE pas (l'ancien
        # « hypothèse indicative 5 % » était un taux fictif, non utilisé dans aucun calcul servi).
        "ta_note": "Taxe d'aménagement : taux communal non ingéré — à confirmer en mairie "
                   "(part communale + part départementale).",
    }
    # RTAA DOM (mandat contexte-commune, 5bis) — rappel réglementaire de conception,
    # vérifié sur Légifrance (config/rtaa_dom.yaml), hors scoring
    from ..config import load_yaml_config
    rtaa = load_yaml_config("rtaa_dom")
    out["rtaa"] = {"meta": rtaa["meta"], "exigences": rtaa["exigences"]}
    return out


class ChargeIn(BaseModel):
    # hypothèses métier SAISIES (jamais estimées par LABUSE) — défauts « à ajuster »,
    # DÉRIVÉS de la source unique (mandat hypothèses bilan : plus de 2500 gravé ici).
    cout_construction_m2: float = Field(CALCULETTE_COUT_DEFAUT_M2, ge=500, le=8000)   # €/m² de plancher
    marge_frais_pct: float = Field(CALCULETTE_MARGE_FRAIS_DEFAUT_PCT, ge=0, le=60)    # marge + frais (% du CA)
    vrd_m2: float = Field(CALCULETTE_VRD_DEFAUT_M2, ge=0, le=2000)                    # VRD/aménagements €/m² terrain (défaut DIT)
    prix_demande_eur: float | None = Field(None, ge=0, le=500_000_000)
    # M22-A : "charge" (sens historique) | "achat_max" (lecture inverse — prix d'achat max
    # admissible : même équation, dérivation ligne à ligne + écart de négociation demandé − max)
    mode: str = Field("charge", pattern="^(charge|achat_max)$")


@router.post("/faisabilite/{idu}/charge")
def faisabilite_charge(idu: str, body: ChargeIn, db: Session = Depends(get_db)) -> dict:
    """CALCULETTE de charge foncière (déterministe, testable). RÉUTILISE le moteur : SDP vendable
    (capacité) + prix de sortie (DVF) sont SOURCÉS ; le coût de construction et la marge viennent
    du corps de requête (hypothèses du promoteur). Cas limites honnêtes : capacité non résolue ou
    prix DVF insuffisant → `calculable:false` + raison, jamais un faux chiffre."""
    _check_idu(idu)   # M-K (P2-31)
    from ..faisabilite.bilan import (
        CALCULETTE_COUT_DEFAUT_M2,
        CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
        CALCULETTE_VRD_DEFAUT_M2,
        compute_calculette,
        resolve_prix_sortie_servi,
        sector_price,
    )
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses

    defaults = {"cout_construction_m2": CALCULETTE_COUT_DEFAUT_M2,
                "marge_frais_pct": CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
                "vrd_m2": CALCULETTE_VRD_DEFAUT_M2}
    row = db.execute(text("SELECT id, commune, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, "Parcelle inconnue")
    fz = parcel_faisabilite(db, row["id"])
    shab = (fz[1].fourchette or {}).get("shab_vendable_m2") if fz else None
    if not shab:
        # capacité non résolue (zone PLU non calibrée / RNU) → on ne calcule pas de résultat creux
        return {"calculable": False, "raison": "capacite_non_resolue", "defaults": defaults,
                "message": "Capacité constructible non résolue pour cette parcelle (zone PLU "
                           "non résolue / non constructible) — charge foncière non calculable."}
    # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — le prix de sortie de la calculette est un
    # prix NEUF (point de résolution partagé), plus jamais sector_price/existant. Non calculable
    # (social-dominant) → réponse honnête, jamais un faux chiffre.
    ps = resolve_prix_sortie_servi(db, row["id"])
    if ps["non_calculable"]:
        return {"calculable": False, "raison": "prix_sortie_non_calculable", "defaults": defaults,
                "message": ps["motif"]}
    prix = sector_price(db, row["id"], Hypotheses.charger())        # comparables/fiabilité (marché)
    prix = {**prix, "q1": ps["prix"], "median": ps["prix"], "q3": ps["prix"],   # prix de sortie NEUF
            "niveau_prix_neuf": ps["niveau"], "prix_neuf_label": ps["label"]}
    res = compute_calculette(float(shab), float(row["s"] or 0), prix,
                             body.cout_construction_m2, body.marge_frais_pct, body.prix_demande_eur,
                             mode=body.mode, vrd_m2=body.vrd_m2)
    res["prix_neuf_label"] = ps["label"]
    res["prix_neuf_repli_ile"] = ps["repli_ile"]
    res["defaults"] = defaults
    # LA CONFRONTATION (le geste du scoreur) : le prix TERRAIN NU observé de la ZONE, à côté de la
    # charge supportable. RÉFÉRENTIEL UNIQUE `prix_terrain_nu_zone` (M79) — le MÊME code que le constat
    # servi (Étudier un bien) et le comparateur. Absent (zone hors U/AU, ou pas de vente) → None.
    try:
        from ..faisabilite.marche_commune import prix_terrain_nu_zone
        tz = prix_terrain_nu_zone(db, row["commune"], (fz[0].zone if fz else None))
        if tz:
            res["terrain_zone_eur_m2"] = tz["eur_m2"]
            res["terrain_zone_fiabilite"] = tz["fiabilite"]
            res["terrain_zone_n"] = tz["n"]
    except Exception:  # noqa: BLE001 — la confrontation est un bonus, ne casse jamais la charge
        pass
    if not res.get("calculable"):
        # prix de sortie insuffisant → au mieux, on rend le prix secteur (déjà dans `marche`)
        res["raison"] = res.get("raison") or "prix_insuffisant"
        res["message"] = ("Prix de sortie insuffisant (échantillon DVF) — charge foncière non "
                          "chiffrée ; le prix de sortie secteur reste indiqué au mieux.")
    return res


# ── M11 · SURFACE C — l'IA EXPLIQUE le chiffrage (à partir des STEPS tracés, jamais elle ne recalcule) ──
_PROV_SOCLE = {"sourcee": "SOURCE", "estimee": "ESTIME", "derive": "ESTIME"}  # derive hérite d'estimé (prudence)

_EXPLAIN_FAISA_SYSTEM = (
    "Tu es l'assistant foncier de LA BUSE. On te donne les ÉTAPES DÉJÀ CALCULÉES d'un chiffrage de "
    "pré-faisabilité (capacité constructible + bilan promoteur) pour UNE parcelle. Explique en français "
    "clair et pédagogique COMMENT on arrive au résultat, en suivant le fil des étapes.\n"
    "RÈGLES ABSOLUES :\n"
    "- Tu n'inventes ni ne recalcules AUCUN chiffre. Chaque nombre que tu écris vient d'une étape du "
    "contexte et est suivi de sa source au format ⟨src:etape_N⟩ ou ⟨src:bilan_N⟩ (ex. « ~2 001 m² de "
    "surface de plancher ⟨src:etape_6⟩ »).\n"
    "- Distingue SOURCÉ (règle PLU, géométrie, prix de marché) et ESTIMÉ (hypothèses : coût de "
    "construction, marge, taux d'occupation, rendement) — dis explicitement quand un chiffre est une hypothèse.\n"
    "- HONNÊTETÉ SUR LE PRIX : si la fiabilité du prix DVF est « fragile », signale-le — la charge foncière "
    "est alors un ORDRE DE GRANDEUR à confirmer, jamais un chiffre certain. Ne survends jamais une estimation.\n"
    "- Ne conclus pas sur l'opportunité d'acheter (le promoteur décide).\n"
    "- FORME : phrases simples, un ou deux courts paragraphes. PAS de titres (##), PAS de séparateurs (---), "
    "PAS de listes. Gras (**…**) autorisé pour les chiffres clés uniquement. 4 à 8 phrases au total."
)


def _faisa_explain_facts(db: Session, row, core_mod) -> dict | None:
    """Construit le CONTEXTE AUTORISÉ (les steps étiquetés) pour l'explication IA. None si pas de capacité.

    Le bilan est calculé avec les MÊMES hypothèses PAR DÉFAUT que la calculette (coût/marge affichés
    au client) → l'explication porte sur les chiffres RÉELLEMENT vus, pas une variante. Ces hypothèses
    sont des ESTIMATIONS ajustables (jamais présentées comme certaines)."""
    from ..faisabilite.bilan import (
        CALCULETTE_COUT_DEFAUT_M2,
        CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
        compute_bilan_servi,
        sector_price,
    )
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses
    fz = parcel_faisabilite(db, row["id"])
    if not fz:
        return None
    _ctx, f = fz
    facts: dict = {}
    for i, s in enumerate(f.steps, 1):
        pv = _PROV_SOCLE.get(_faisa_step_prov(s.source, s.prov), "ESTIME")
        facts[f"etape_{i}"] = core_mod.Fact(f"{s.label} : {s.valeur} (source : {s.source})", pv)
    fo = f.fourchette or {}
    facts["resultat"] = core_mod.Fact(
        f"gabarit {fo.get('niveaux')}, SDP {fo.get('surface_plancher_m2')} m², "
        f"{fo.get('logements_au_sol')} logements, hauteur {fo.get('hauteur_m')} m", "ESTIME")
    # bilan (si capacité vendable) — MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) : l'explication
    # IA porte sur LE MÊME bilan que la fiche (compute_bilan_servi), pas une variante. Non calculable
    # (social-dominant) → dit honnêtement.
    b, ps = compute_bilan_servi(db, row["id"], fz)
    if b is not None and ps["non_calculable"]:
        facts["charge_fonciere"] = core_mod.Fact(ps["motif"], "SOURCE")
    elif b is not None:
        for i, s in enumerate(b.steps, 1):
            facts[f"bilan_{i}"] = core_mod.Fact(f"{s.label} : {s.valeur}", _PROV_SOCLE.get(s.prov, "ESTIME"))
        cf = b.charge_fonciere or {}
        facts["charge_fonciere"] = core_mod.Fact(
            f"charge foncière médiane {cf.get('central')} € (~{cf.get('par_m2_terrain')} €/m² de terrain), "
            f"prix de sortie neuf {ps['label']}", "ESTIME")
        facts["prix_sortie_neuf"] = core_mod.Fact(f"prix de sortie neuf — {ps['label']}", "ESTIME")
    return facts


@router.get("/faisabilite/{idu}/explain")
def faisabilite_explain(idu: str, db: Session = Depends(get_db)) -> dict:
    """M11 Surface C : explication EN CLAIR de la dérivation du chiffrage, ancrée sur les STEPS du
    moteur (déterministes). L'IA narre, elle ne recalcule pas ; la couche 2 du socle rejette tout
    chiffre absent des étapes. Sur clic uniquement (coût) ; caché par (idu, run, question)."""
    _check_idu(idu)   # M-K (P2-31)
    from ..ai import core
    QUESTION = "explication_faisabilite"

    hit = core.cache_get(db, idu, runs.current(), QUESTION)
    if hit is not None:
        return {**hit, "cached": True}
    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, "Parcelle inconnue")
    facts = _faisa_explain_facts(db, row, core)
    if not facts:
        return {"disponible": False,
                "message": "Capacité constructible non résolue pour cette parcelle — rien à expliquer."}
    ctx = core.build_context(facts, allowed_fields=set(facts))
    res = core.complete(db, kind="explain-faisa", model=core.model_for("explain-faisa"), max_tokens=800,
                        system=_EXPLAIN_FAISA_SYSTEM, context=ctx, validate=True, require_sources=True)
    if res.degraded:
        return {"disponible": True, "degraded": True,
                "texte": "Explication momentanément indisponible — réessayez.", "reason": res.reason}
    if res.rejected:
        out = {"disponible": True, "rejected": True,
               "texte": "Je ne peux pas expliquer ce calcul de façon sûrement sourcée.",
               "sources": [], "provenance": {}}
    else:
        out = {"disponible": True, "rejected": False, "texte": res.text, "sources": res.sources,
               "provenance": {k: facts[k].provenance for k in res.sources if k in facts}}
    core.cache_put(db, idu, runs.current(), QUESTION, out, kind="explain-faisa")
    return out


# M133 (B.1) — coefficient EXPLICITE surface utile/unité → SDP. Le champ « M²/UNITÉ » est une
# surface UTILE (habitable) ; la SDP ajoute circulations, murs et parties communes. +20 % est le bas
# de la fourchette 20-25 % du neuf collectif (M132 B.1 : l'ancien +15 % codé en dur sous-estimait le
# besoin, dans le sens du faux positif). Paramétré et affiché (cf. `criteres.calcul` / bandeau).
PROGRAMME_CIRCULATION_COEF = 1.20
_PROGRAMME_ETAGE_M = 3.0            # hauteur/niveau (cohérent hauteur_min ; défaut moteur engine.Hypotheses)


class ProgrammeIn(BaseModel):
    # M133 (contrôle 8) — le champ TYPE (logements/étudiant/bureaux) n'entrait dans AUCUN calcul :
    # champ décoratif, retiré du formulaire. Le réintroduire suppose des normes PAR TYPE calibrées
    # (surface/unité, coefficient circulations, stationnement) — consigné en dette, pas fabriqué ici.
    batiments: int = 1
    niveaux: int = 2                 # R+n → n
    logements_par_batiment: int = 8
    surface_unite_m2: float = 60     # M133 (B.1) : surface UTILE par unité (PAS de la SDP directe)
    # M133 (arbitrage Vic) — coefficient utile→SDP ÉDITABLE par le promoteur (défaut 1,20 = bas de la
    # fourchette 20-25 %). Laisser le défaut figé, c'est choisir à sa place le réglage le plus permissif.
    coef_circulation: float = Field(PROGRAMME_CIRCULATION_COEF, ge=1.0, le=1.6)
    commune: str | None = None       # None = île entière (extension île)
    offset: int = 0                  # FAISABILITE (pagination SOCLE) : fenêtre d'affichage (par page)
    # DESTINATIONS-1 (X4.3) — sous-destination du programme (slug R151-28). Contrairement à
    # l'ancien champ TYPE décoratif (M133), celui-ci AGIT : zone au verdict « interdit » écartée
    # (comptée), « sous condition »/« en cours de calibration » annotées — dit AVANT de calculer.
    destination: str | None = None


@router.post("/programme")
def faisabilite_sens2(body: ProgrammeIn, db: Session = Depends(get_db)) -> dict:
    """SENS 2 (programme → parcelles) : critères CALCULÉS et AFFICHÉS → candidates triées par
    marge de capacité. La hauteur PLU est vérifiée zone par zone (resolve_zone) quand calibrée."""
    from ..faisabilite.plu_rules import resolve_zone

    unites = max(1, body.batiments) * max(1, body.logements_par_batiment)
    # B.1 (+ arbitrage Vic) — besoin SDP = surface utile × coefficient utile→SDP ÉDITABLE (défaut 1,20),
    # affiché et étiqueté hypothèse : le promoteur choisit son taux, pas un réglage figé permissif.
    sdp_min = round(unites * body.surface_unite_m2 * body.coef_circulation)
    # B.4 — le champ PARKING est RETIRÉ (M133) : convertir des places en emprise/SDP consommée exige
    # un m²/place qui n'est SOURCÉ qu'à Cilaos (place_m2_source_ref) et MODÉLISÉ (25) ailleurs — une
    # valeur fabriquée. Un contrôle décoratif est un chiffre fabriqué : on ne le garde pas. Dette consignée.
    hauteur_min = (body.niveaux + 1) * _PROGRAMME_ETAGE_M        # R+n → (n+1) niveaux × 3 m
    # Fix LOT 3 : requête LÉGÈRE (sans la géométrie lourde) et SANS LIMIT prématuré — TOUTES les
    # parcelles satisfaisant les filtres SQL (SDP, surface, statut, run servi) sont ramenées, PUIS
    # le filtre HAUTEUR (résolu en Python via resolve_zone) s'applique, PUIS le tri marge, PUIS la
    # troncature d'AFFICHAGE. Avant, `LIMIT 300` sur SDP DESC coupait AVANT le filtre hauteur →
    # des parcelles valides (hors des 300 plus grosses SDP) étaient jetées sans être examinées.
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, r.sdp_residuelle_m2,
               s2.tier AS statut, zp.zone_lib AS zone,
               s2.tier AS tier_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
        FROM parcels p
        JOIN parcel_residuel r ON r.parcel_id = p.id AND r.sdp_residuelle_m2 >= :sdp
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        -- M133 : zone FINE (Ua/Uc/2AUc…) via parcel_zone_plu (mono-zone), PAS la famille grossière
        -- « U » de la sortie cascade — resolve_zone n'a de hauteur calibrée que sur la sous-zone fine.
        LEFT JOIN parcel_zone_plu zp ON zp.idu = p.idu
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND p.surface_m2 >= :smin
          AND s2.tier IN ('brulante', 'chaude', 'reserve_fonciere', 'a_creuser')"""),
        {"sdp": sdp_min, "run": runs.current(), "c": body.commune, "v2run": _v2run(db),
         "smin": sdp_min * 0.4}).mappings().all()
    hcache: dict = {}   # (zone, commune) → (hauteur éligibilité, niveaux_max, estimée, signature calcul)

    def _zinfo(zone: str, commune):
        key = (zone, commune)
        if key not in hcache:
            # la hauteur PLU se résout avec la commune DE LA PARCELLE (mode île : elles diffèrent)
            rules = resolve_zone(zone, commune) if zone else None
            he = getattr(rules, "he_m", None) if rules else None
            hf = getattr(rules, "hf_m", None) if rules else None
            # éligibilité hauteur : faîtage prioritaire (comportement conservé)
            h = (hf if isinstance(hf, (int, float)) else None) or (he if isinstance(he, (int, float)) else None)
            # niveaux_max FIDÈLE au moteur (engine.py:281-292) : hé prioritaire, sinon hf, sinon inconnu.
            if isinstance(he, (int, float)):
                nmax = int(float(he) // _PROGRAMME_ETAGE_M)
            elif isinstance(hf, (int, float)):
                nmax = max(1, int((float(hf) - _PROGRAMME_ETAGE_M) // _PROGRAMME_ETAGE_M))
            else:
                nmax = None
            # B.5 — capacité ESTIMÉE = zone non calibrée finement. MÊME source que le moteur
            # (engine.py:180 : `not rules.calibree`), lue en direct sur la sous-zone fine — pas le
            # flag du cache résiduel (antérieur à M131, incohérent). Zone non résolue → estimée.
            estimee = rules is None or not bool(getattr(rules, "calibree", False))
            # signature de CALCUL : ce qui distingue une zone d'une autre pour la capacité.
            cn = getattr(rules, "constructible_neuf", None) if rules else None
            hcache[key] = (float(h) if h is not None else None, nmax, estimee, (cn, he, hf))
        return hcache[key]

    # DESTINATIONS-1 (X4.3) — verdict destination par (commune, zone), lecture UNIQUE via
    # plu.destinations. Slug inconnu → 400 explicite (pas un filtre silencieux).
    dest = (body.destination or "").strip() or None
    dcache: dict = {}
    if dest:
        from ..plu.destinations import SOUS_DESTINATIONS as _SD, verdict as _dverdict
        if dest not in _SD:
            raise HTTPException(400, f"sous-destination inconnue : {dest}")

    def _dinfo(zone: str, commune):
        key = (zone, commune)
        if key not in dcache:
            v = _dverdict(commune or "", zone or "", dest)
            etat = v.get("statut_effectif")
            if v["etat_calibration"] == "non_calibree" or etat == "non_lu":
                etat = "en_cours_de_calibration"
            dcache[key] = {"etat": etat, "phrase": v.get("phrase")}
        return dcache[key]

    ecartees_destination = 0
    items = []
    for r in rows:
        zone = (r["zone"] or "").strip()   # étiquette FINE (parcel_zone_plu), pas la famille cascade
        h, niveaux_max, capacite_estimee, sig_label = _zinfo(zone, r["commune"])
        # CONFLIT DE SOURCE DE ZONE (vérif V2, dette §7) : le cache résiduel n'est POSITIF que si la
        # zone du CENTROÏDE (qui l'a produit, parcel_context db.py:32-36) est constructible. Si
        # l'ÉTIQUETTE (parcel_zone_plu) résout en NON constructible — ou ne résout pas —, la SDP servie
        # serait ÉTRANGÈRE à l'étiquette (la forme exacte du 4 m de M130-12 : chiffre juste, étiquette
        # fausse). On NE sert PAS de SDP : la parcelle sort « à instruire », même sort que les zones sans
        # étiquette — SANS trancher quelle source a raison (l'inconnu = dette §7). Les zones GELÉES
        # (Us/2AUc) ont un résiduel 0 : déjà écartées par le filtre SDP, le gel tient.
        if sig_label[0] is not True:
            continue
        # (1) grille d'ÉLIGIBILITÉ hauteur (rôle conservé) : la zone autorise-t-elle R+N ?
        if h is not None and float(h) < hauteur_min:
            continue                       # filtre hauteur AVANT toute troncature (Fix A)
        # (2) B.2 — SDP au GABARIT DEMANDÉ. Le résiduel est cumulé sur niveaux_max (plein gabarit) ;
        #     on le plafonne au R+N : sdp_dispo = résiduel × min(N+1, niveaux_max)/niveaux_max. Sans
        #     niveaux_max (zone sans hauteur calibrée), pas de plafond possible → résiduel brut, signalé.
        sdp_resid = float(r["sdp_residuelle_m2"])
        if niveaux_max:
            niveaux_dem = min(body.niveaux + 1, niveaux_max)
            sdp_dispo = sdp_resid * niveaux_dem / niveaux_max
        else:
            niveaux_dem, sdp_dispo = None, sdp_resid
        if sdp_dispo < sdp_min:
            continue
        # (3) B.3 — EMPRISE au sol : l'emprise du programme au gabarit demandé (sdp_min/niveaux_dem)
        #     tient-elle dans l'emprise bâtissable résiduelle (sdp_resid/niveaux_max) ? Contrôle explicite
        #     (algébriquement lié à (2) au même gabarit ; écrit à part pour être lisible — la contrainte
        #     géométrique de FORME/largeur, elle, exige le moteur → hors périmètre, consignée en dette).
        emprise_dispo = (sdp_resid / niveaux_max) if niveaux_max else None
        emprise_besoin = (sdp_min / niveaux_dem) if niveaux_dem else None
        if emprise_dispo is not None and emprise_besoin is not None and emprise_besoin > emprise_dispo + 0.5:
            continue
        # (4) DESTINATIONS-1 (X4.3) — la destination du programme doit être admise dans la zone :
        #     interdit → écartée (comptée) ; sous condition / en cours de calibration → annotée.
        dv = _dinfo(zone, r["commune"]) if dest else None
        if dv and dv["etat"] == "interdit":
            ecartees_destination += 1
            continue
        marge = round(sdp_dispo / sdp_min, 2)
        items.append({"idu": r["idu"], "commune": r["commune"], "surface_m2": r["surface_m2"],
                      **({"destination_verdict": dv} if dv else {}),
                      "sdp": round(sdp_dispo), "sdp_plein_gabarit_m2": round(sdp_resid),
                      "niveaux_demandes": niveaux_dem, "niveaux_max_zone": niveaux_max,
                      "emprise_besoin_m2": round(emprise_besoin) if emprise_besoin is not None else None,
                      "emprise_dispo_m2": round(emprise_dispo) if emprise_dispo is not None else None,
                      "capacite_estimee": capacite_estimee,
                      "statut": r["statut"], "tier_v2": r["tier_v2"], "etage0": bool(r["etage0"]),
                      "zone": zone or None,
                      "hauteur_plu_m": float(h) if h is not None else None,
                      "hauteur_verifiee": h is not None, "marge_capacite": marge})
    items.sort(key=lambda x: -x["marge_capacite"])
    # FAISABILITE (pagination SOCLE) : `offset` fenêtre l'affichage (page de `cap`) ; `n` reste le VRAI
    # total. Le tri (marge décroissante) est stable → paginer ne fait que faire glisser la fenêtre.
    # LOT2 (OUTILS-FINALE) P0 : `_moteurs_cap` vit dans .moteurs et n'était PAS importé ici → NameError
    # à CHAQUE recherche « Par critères » (500 → « Recherche indisponible »). Import local (pas de cycle).
    from .moteurs import _moteurs_cap
    cap = _moteurs_cap("programme_max", 200)
    off = max(0, body.offset)
    top = items[off:off + cap]            # troncature d'AFFICHAGE seulement — `n` reste le vrai total
    if top:                               # géométries ramenées UNIQUEMENT pour la page affichée
        geoms = {gr["idu"]: json.loads(gr["g"]) for gr in db.execute(text(
            "SELECT idu, ST_AsGeoJSON(ST_Transform(geom_2975, 4326)) AS g "
            "FROM parcels WHERE idu = ANY(:idus)"),
            {"idus": [i["idu"] for i in top]}).mappings()}
        for i in top:
            i["geom"] = geoms.get(i["idu"])
    _coef_pct = round((body.coef_circulation - 1) * 100)
    return {
        "criteres": {"unites": unites, "sdp_min_m2": sdp_min, "coef_circulation": body.coef_circulation,
                     "calcul": f"{unites} unités × {body.surface_unite_m2:g} m² utiles × "
                               f"{body.coef_circulation:g} (+{_coef_pct} % circulations/murs/communs, hypothèse)",
                     "hauteur_min_m": hauteur_min,
                     "hauteur_regle": f"R+{body.niveaux} → SDP plafonnée au gabarit demandé "
                                      f"({body.niveaux + 1} niveaux, {hauteur_min:.0f} m)",
                     **({"destination": dest,
                         "destination_ecartees": ecartees_destination,
                         "destination_regle": ("zones au verdict « interdit » écartées ; "
                                               "« sous condition » et « en cours de calibration » "
                                               "annotées par parcelle (source : calibration "
                                               "destinations, article/page/millésime)")}
                        if dest else {})},
        "bandeau": (f"Estimation capacitaire — hypothèses affichées (surface utile/unité, +{_coef_pct} % "
                    "SDP) ; SDP plafonnée au gabarit R+N demandé et emprise au sol vérifiée ; hauteur PLU "
                    "vérifiée quand la zone est calibrée, sinon « à instruire » ; capacité « estimée » "
                    "signalée hors PLU calibré. Étude d'architecte requise."),
        "n": len(items), "items": top,   # n = VRAI nombre de correspondances ; items = la page servie
        "cap": cap, "offset": off,        # pagination SOCLE (par page + offset)
    }


@router.get("/verif-procedure/{idu}")
def verif_procedure(idu: str, db: Session = Depends(get_db)) -> dict:
    """M41 Phase 2.6 — outil « Vérif procédure » : un IDU → la commune a-t-elle une procédure PLU
    en cours (OUI/NON), et les conséquences parcellaires applicables. L'outil LIT le radar
    (labuse.veille_plu, point de calcul UNIQUE) — il ne calcule rien, mêmes libellés que la fiche.
    L'absence est DATÉE elle aussi (« aucune procédure connue au JJ/MM — dernier constat le X »)."""
    # RETOURS-12 O4 — NORMALISER l'IDU avant tout (doctrine T1 : casse, espaces, retour-ligne). Le bug
    # « Parcelle inconnue » sur un IDU VALIDE venait d'un lookup `WHERE idu = :i` sur l'IDU BRUT : un IDU
    # collé avec un espace/retour en queue, ou saisi en minuscules (97413000cj0096), ne matchait pas.
    idu = (idu or "").strip().upper()
    _check_idu(idu)   # M-K (P2-31)
    import datetime

    from ..verdict_servi import verdict_servi
    from .. import veille_plu as V

    p = db.execute(text("SELECT idu, commune FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not p:
        raise HTTPException(404, "Parcelle inconnue")
    insee = idu[:5]
    try:
        tier = (verdict_servi(db, idu) or {}).get("tier")
    except Exception:  # noqa: BLE001 - l'outil ne doit jamais 500 sur le tier
        tier = None
    e = V.entry(insee)
    today = datetime.date.today().isoformat()
    out = {"idu": idu, "commune": p["commune"], "insee": insee, "tier_servi": tier,
           "consulte_le": today}
    if not e:
        out.update({"procedure_en_cours": None,
                    "message": "Commune hors registre radar — état de procédure inconnu."})
        return out
    radar = V.radar_parcelle(idu, tier)
    active = V.procedure_active(e)
    if active:
        syn = V.synthese_commune(insee) or {}
        out.update({
            "procedure_en_cours": True,
            "type": e["procedure"], "stade": e["stade"], "date_acte": e["date_acte"],
            "source": e["source"], "source_url": e.get("source_url"),
            "date_constat": e["date_constat"], "confiance": e["confiance"],
            "synthese": syn.get("etat"),
            "consequences": {
                "sursis": (radar or {}).get("sursis"),          # None tant que débat PADD non constaté
                "veille_au": (radar or {}).get("veille_au"),     # sur les déclassées zone-fermée/AU
            },
        })
    else:
        # aucune procédure active servie (aucune / clôturée / dormante) — l'absence est datée
        detail = {"aucune": "aucune procédure PLU lourde",
                  "cloturee": "procédure Sudocuh sans suite connue (clôture probable, non servie)",
                  }.get(e["procedure"], f"procédure « {e['procedure']} » non servie au radar")
        stade = e.get("stade")
        if stade == "prescrite_dormante":
            detail = f"élaboration prescrite le {e['date_acte']} — dormante, aucun acte postérieur connu"
        out.update({
            "procedure_en_cours": False, "confiance": e["confiance"],
            "message": (f"Aucune procédure PLU en cours servie au {today} — {detail}. "
                        f"Dernier constat le {e['date_constat']}."),
        })
    return out


# ── M51 — Annuaire PLU interrogeable (verbatim sourcé) ───────────────────────────────────────────
import functools as _ft  # noqa: E402


@_ft.lru_cache(maxsize=1)
def _plu_millesimes() -> dict:
    """Vérité idurba/statut par commune (M40) — chargée une fois."""
    import pathlib

    import yaml
    p = pathlib.Path(__file__).resolve().parents[3] / "config" / "plu_millesimes.yaml"
    return yaml.safe_load(p.read_text())["communes"]


@router.get("/plu-annuaire/communes")
def plu_annuaire_communes(db: Session = Depends(get_db)) -> dict:
    """M51 — état du corpus par commune : SERVABLE (n extraits), RNU, révision non réconciliée,
    ou non ingéré. Réponse HONNÊTE (pas de trou masqué)."""
    from ..ingestion.plu_ingest import corpus_status
    from .. import veille_plu as V   # RETOURS-12 O4 — source UNIQUE des procédures (radar Sudocuh + registre)
    ing = corpus_status(db)
    _TYPE_PROC = {"revision_plu": "révision générale", "elaboration_plu": "élaboration", "modification_plu": "modification"}
    out = []
    for insee, c in sorted(_plu_millesimes().items()):
        e = ing.get(insee)
        if e:
            out.append({"insee": insee, "commune": c["commune"], "statut": "servable",
                        "idurba": e["idurba"], "millesime": e["millesime"], "extraits": e["extraits"],
                        "doutes": e["doutes"], "pagination_ambigue": e["pagination_ambigue"],
                        # M137-P — le « PLU intégral » = le pack officiel GPU (.zip) à télécharger ;
                        # aucun PDF n'est stocké en base. document = nom du règlement PDF dans le pack.
                        "source_url": e.get("source_url"), "document": e.get("documents")})
        elif c["statut"] == "rnu":
            out.append({"insee": insee, "commune": c["commune"], "statut": "rnu", "extraits": 0,
                        "message": "RNU (règlement national d'urbanisme) — pas de règlement communal."})
        elif c["statut"] == "opposabilite_en_attente":
            out.append({"insee": insee, "commune": c["commune"], "statut": "revision", "extraits": 0,
                        "idurba": c.get("idurba"),
                        "message": "Révision en cours — règlement non servi par le GPU, vérifier en "
                                   "mairie. Complétion automatique à l'approbation (veille trimestrielle "
                                   "M41). On ne sert pas un règlement non réconcilié (garde idurba+sha)."})
        else:
            out.append({"insee": insee, "commune": c["commune"], "statut": "non_ingere",
                        "idurba": c.get("idurba"), "extraits": 0,
                        "message": "Règlement non ingéré pour cette commune."})
    # OUTILS-1 A5 — le décompte par statut est CALCULÉ ici (source unique = statut réel de l'annuaire),
    # jamais dérivé par soustraction ni figé au front : le RNU (ABSENCE de PLU) n'est pas une procédure et
    # ne doit jamais être compté « en révision ». Si une commune passe en révision demain, le bandeau suit
    # seul. `n_revision` = procédure de révision non réconciliée ; `n_rnu` = RNU ; `n_non_ingere` = corpus
    # manquant. Somme des quatre = n_communes (invariant vérifié par test).
    # RETOURS-12 O4 — RÉCONCILIATION : le compteur « en révision » de l'annuaire et le registre des
    # procédures lisaient DEUX sources différentes (statut d'opposabilité GPU vs radar Sudocuh) → l'annuaire
    # disait « 2 en révision » et ratait Les Trois-Bassins (révision prescrite le 02/06/2022, servie par le
    # radar). Désormais les DEUX lisent `veille_plu` (source unique). On attache à chaque commune sa
    # procédure ACTIVE (le fait), distincte de la disponibilité du règlement (statut GPU, conservé).
    for c in out:
        e_vp = V.entry(c["insee"])
        if e_vp and V.procedure_active(e_vp) and e_vp["procedure"] in _TYPE_PROC:
            c["procedure_active"] = _TYPE_PROC[e_vp["procedure"]]
            c["procedure_date"] = e_vp.get("date_acte")
        else:
            c["procedure_active"] = None
    servables = sum(1 for c in out if c["statut"] == "servable")
    # `n_revision`/`n_rnu` restent la disponibilité du RÈGLEMENT (statut GPU) — inchangés (invariant test).
    n_revision = sum(1 for c in out if c["statut"] == "revision")
    n_rnu = sum(1 for c in out if c["statut"] == "rnu")
    n_non_ingere = sum(1 for c in out if c["statut"] == "non_ingere")
    # `procedures` = la LISTE réconciliée des procédures PLU en cours (radar Sudocuh), par état — la MÊME
    # source que l'outil « Vérif procédure » et la fiche. C'est ce que le bandeau doit afficher.
    procedures = {}
    for c in out:
        if c["procedure_active"]:
            procedures[c["procedure_active"]] = procedures.get(c["procedure_active"], 0) + 1
    n_procedures = sum(1 for c in out if c["procedure_active"])
    # RETOURS-13 R22 — un PLU en RÉVISION reste EN VIGUEUR jusqu'à l'approbation du nouveau :
    # le compteur dit désormais les PLU EXISTANTS (24 communes − RNU), et NOMME les trous de
    # SOURCE (règlement en vigueur mais non servi par le GPU — Saint-André, Saint-Leu), au lieu
    # de les cacher dans un « 21 disponibles » faux.
    n_plu_vigueur = len(out) - n_rnu
    non_servis = sorted(c["commune"] for c in out if c["statut"] in ("revision", "non_ingere"))
    return {"n_communes": len(out), "servables": servables, "n_plu_vigueur": n_plu_vigueur,
            "non_servis": non_servis,
            "n_revision": n_revision, "n_rnu": n_rnu, "n_non_ingere": n_non_ingere,
            # RETOURS-12 O4 — compteur RÉCONCILIÉ des procédures (source unique veille_plu).
            "n_procedures": n_procedures, "procedures_par_etat": procedures,
            "communes": out}


@router.get("/plu-annuaire/pack/{insee}")
def plu_annuaire_pack(insee: str, db: Session = Depends(get_db)) -> dict:
    """RETOURS-15 U8 — le pack .zip du PLU EN VIGUEUR, résolu EN DIRECT sur le GPU (grid=insee) :
    une commune en révision doit quand même proposer sa dernière version en date. TROIS issues
    DISTINCTES, jamais confondues (même doctrine que U5) :
      · trouvé      → url du zip + millésime (document EN_VIGUEUR, sinon le plus récent) ;
      · GPU VIDE    → le GPU ne publie AUCUN document pour cette commune (vérifié à l'instant,
                      cas mesuré le 05/09/2026 : Saint-André ET Saint-Leu → `[]`) — on le DIT et
                      on donne la mairie (source K2) ;
      · injoignable → erreur réseau, dite comme telle (jamais déguisée en « rien au GPU »)."""
    import re as _re
    if not _re.fullmatch(r"974\d\d", insee):
        raise HTTPException(404, "Commune inconnue")
    mairie = db.execute(text(
        "SELECT nom, telephone, email, site_officiel FROM mairies WHERE insee = :i"),
        {"i": insee}).mappings().first()
    try:
        import requests as _rq
        r = _rq.get("https://www.geoportail-urbanisme.gouv.fr/api/document",
                    params={"grid": insee}, headers={"User-Agent": "labuse/1.0"}, timeout=12)
        r.raise_for_status()
        docs = [d for d in r.json() if (d.get("documentType") or d.get("type")) in ("PLU", "POS", "PLUI")]
    except Exception as e:  # noqa: BLE001 — l'échec réseau est DIT, jamais un faux « rien »
        logging.getLogger("labuse").warning("plu-annuaire pack %s : GPU injoignable (%s)", insee, e)
        return {"insee": insee, "disponible": False, "erreur": "gpu_injoignable",
                "message": "Géoportail de l'Urbanisme injoignable à l'instant — réessayez.",
                "mairie": dict(mairie) if mairie else None}
    if not docs:
        return {"insee": insee, "disponible": False, "erreur": None,
                "message": ("Le Géoportail de l'Urbanisme ne publie aucun document pour cette "
                            "commune (vérifié à l'instant). Le PLU en vigueur reste applicable — "
                            "demandez-le en mairie."),
                "mairie": dict(mairie) if mairie else None}
    # EN_VIGUEUR d'abord ; sinon le plus récent (les originalName portent la date AAAAMMJJ).
    docs.sort(key=lambda d: ((d.get("effectiveStatus") or d.get("status")) == "EN_VIGUEUR",
                             str(d.get("originalName") or "")), reverse=True)
    doc = docs[0]
    idurba = str(doc.get("originalName") or "")
    mdate = _re.search(r"(\d{4})(\d{2})(\d{2})$", idurba)
    return {"insee": insee, "disponible": True,
            "idurba": idurba,
            "millesime": f"{mdate.group(3)}/{mdate.group(2)}/{mdate.group(1)}" if mdate else None,
            "statut_gpu": doc.get("effectiveStatus") or doc.get("status"),
            "url": f"https://www.geoportail-urbanisme.gouv.fr/api/document/{doc.get('id')}/download/{idurba}.zip"}


@router.get("/plu-annuaire/search")
def plu_annuaire_search(q: str, insee: str | None = None, zone: str | None = None,
                        limit: int = Query(25, ge=1, le=200),   # FIX-C5
                        db: Session = Depends(get_db)) -> dict:
    """M51 — recherche full-text (french) qui SERT DU VERBATIM SOURCÉ : chaque résultat porte
    commune, document, article, PAGE PDF, millésime, lien. Aucun résumé, aucun reformulé. `doute` et
    `pagination_ambigue` sont RENDUS. `insee` absent = île entière. RNU / commune non ingérée =
    réponse honnête."""
    from ..ingestion.plu_ingest import corpus_status, search_reglement
    q = (q or "").strip()
    if not q:
        raise HTTPException(400, "Requête vide.")
    if insee:
        mil = _plu_millesimes().get(insee)
        if mil and mil["statut"] == "rnu":
            return {"query": q, "insee": insee, "commune": mil["commune"], "n": 0, "resultats": [],
                    "message": f"{mil['commune']} : RNU — pas de règlement communal à interroger."}
        if insee not in corpus_status(db):
            nm = mil["commune"] if mil else insee
            rev = mil and mil["statut"] == "opposabilite_en_attente"
            return {"query": q, "insee": insee, "commune": nm, "n": 0, "resultats": [],
                    "message": (f"{nm} : révision en cours — règlement non servi par le GPU, vérifier "
                                f"en mairie (complétion auto à l'approbation, veille M41).") if rev else
                               (f"{nm} : règlement non ingéré (hors corpus) — rien à servir. "
                                f"Voir /plu-annuaire/communes.")}
    res = search_reglement(db, q, insee, limit=limit, zone=zone)
    for r in res:
        r["gpu_consult"] = "https://www.geoportail-urbanisme.gouv.fr/"
        if r.get("pagination_ambigue"):
            r["pagination_note"] = ("pagination du document ambiguë (double numérotation) — la page "
                                    "citée est la PAGE PDF du fichier, pas la page imprimée.")
    return {"query": q, "insee": insee, "n": len(res), "resultats": res,
            "avis": "Verbatim du règlement opposable (source GPU). Vérifiez toujours au document "
                    "(lien) ; ceci n'est pas un conseil juridique."}
