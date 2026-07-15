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
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/modules", tags=["modules"])

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)


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
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


# ───────────────────────── M01 — DIVISION PARCELLAIRE ─────────────────────────

@router.post("/division/compute")
def division_compute(commune: str = "Saint-Paul", db: Session = Depends(get_db)) -> dict:
    """Pré-calcule les candidats division (C1-C5) — idempotent PAR COMMUNE (extension île : les
    24 communes coexistent dans module_division, on ne repart propre que sur celle calculée)."""
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
def division_list(min_score: int = 0, limit: int = 300, commune: str | None = None,
                  db: Session = Depends(get_db)) -> dict:
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
        {"s": min_score, "lim": limit, "c": commune, "run": RUN}).mappings().all()
    counts = db.execute(text(
        f"SELECT count(*) FILTER (WHERE NOT {etage0}) AS total,"
        f"       count(*) FILTER (WHERE {etage0}) AS exclus"
        " FROM module_division m JOIN parcels p ON p.id = m.parcel_id"
        " WHERE m.score >= :s AND (CAST(:c AS text) IS NULL OR p.commune = :c)"),
        {"s": min_score, "c": commune, "run": RUN}).mappings().one()
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
    if len(q.strip()) < 2:
        return []
    rows = db.execute(text("""
        SELECT siren, max(denomination) AS nom, count(*) AS n
        FROM parcelle_personne_morale
        WHERE siren IS NOT NULL AND (denomination ILIKE :q OR siren LIKE :qs)
        GROUP BY siren ORDER BY n DESC LIMIT 12"""),
        {"q": f"%{q}%", "qs": f"{q}%"}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/patrimoine")
def patrimoine(siren: str, db: Session = Depends(get_db)) -> dict:
    """M5.1 lot 3.1 : le TIER v2 effectif (étage 0 du run servi prime) est le label
    principal de chaque parcelle du patrimoine ; le statut matrice reste servi en
    secondaire (« (matrice : X) » côté UI). Tri par rang P."""
    from .app import _score_v2_run_id
    rows = db.execute(text("""
        SELECT p.idu, p.commune, p.surface_m2, d.matrice_statut AS statut, d.q_score, d.a_score,
               d.completeness_score, r.sdp_residuelle_m2,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE pm.siren = :s ORDER BY s2.rang ASC NULLS LAST, d.q_score DESC NULLS LAST"""),
        {"s": siren, "run": RUN, "v2run": _score_v2_run_id(db)}).mappings().all()
    bodacc = db.execute(text(
        "SELECT type_procedure, date_annonce FROM v_foncier_sous_pression WHERE siren = :s LIMIT 1"),
        {"s": siren}).mappings().first()
    nom = db.execute(text(
        "SELECT max(denomination) FROM parcelle_personne_morale WHERE siren = :s"), {"s": siren}).scalar()
    return {
        "siren": siren, "nom": nom, "n_parcelles": len(rows),
        "sdp_totale_m2": round(sum(r["sdp_residuelle_m2"] or 0 for r in rows)),
        "bodacc": dict(bodacc) if bodacc else None,
        "items": [{**{k: r[k] for k in ("idu", "commune", "statut", "q_score", "a_score", "completeness_score")},
                   "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                   "surface_m2": round(r["surface_m2"] or 0), "sdp": r["sdp_residuelle_m2"],
                   "geom": json.loads(r["g"])} for r in rows],
    }


# ───────────────────────── M03 — RADAR PERMIS ─────────────────────────

@router.get("/permis")
def permis(commune: str | None = None, months: int = 24, nature: str | None = None,
           db: Session = Depends(get_db)) -> dict:
    # fenêtre ancrée sur la FIN DES DONNÉES (le flux Sitadel s'arrête avant aujourd'hui) — honnêteté
    dmax = db.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()
    # M10 : jointure sur la date de dépôt + délai d'instruction rapatriés (m10_permit_delais)
    rows = db.execute(text("""
        SELECT s.permit_id, s.type, s.date::date::text AS date, s.commune,
               s.raw->>'etat' AS etat, s.raw->>'nb_lgt' AS nb_lgt, s.raw->>'surf_hab' AS surf_hab,
               d.date_depot::text AS depot, CASE WHEN d.valide THEN d.delai_mois END AS delai_mois,
               CASE WHEN s.geom IS NOT NULL THEN ST_AsGeoJSON(s.geom) END AS g
        FROM sitadel_permits s
        LEFT JOIN m10_permit_delais d ON d.permit_id = s.permit_id
        WHERE (CAST(:c AS text) IS NULL OR s.commune = :c)
          AND (CAST(:nat AS text) IS NULL OR s.type = :nat)
          AND s.date >= :dmax - (:m || ' months')::interval
        ORDER BY s.date DESC LIMIT 2000"""),
        {"c": commune, "m": months, "nat": nature, "dmax": dmax}).mappings().all()
    true_total = int(db.execute(text(
        """SELECT count(*) FROM sitadel_permits
           WHERE (CAST(:c AS text) IS NULL OR commune = :c)
             AND (CAST(:nat AS text) IS NULL OR type = :nat)
             AND date >= :dmax - (:m || ' months')::interval"""),
        {"c": commune, "m": months, "nat": nature, "dmax": dmax}).scalar() or 0)
    geo = [r for r in rows if r["g"]]
    return {
        "commune": commune or "Toute l'île", "months": months, "nature": nature,
        "total": true_total, "affiches": len(rows),
        "donnees_jusqu_au": dmax.date().isoformat() if dmax else None,
        "geocodes": len(geo), "pct_geocode": round(100 * len(geo) / len(rows)) if rows else 0,
        "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "depot", "delai_mois",
                                        "etat", "nb_lgt", "surf_hab")},
                   "geom": json.loads(r["g"]) if r["g"] else None} for r in rows],
    }


# Libellés lisibles (nature d'autorisation + état d'avancement, codes source non documentés)
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
def promesses(commune: str | None = None, months: int = 24, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text("""
        SELECT s.permit_id, s.type, s.date::date::text AS date, s.raw->>'etat' AS etat,
               s.raw->>'nb_lgt' AS nb_lgt, p.idu, round(p.surface_m2) AS surface_m2,
               d.matrice_statut AS statut, d.q_score,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM sitadel_permits s
        JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS c(idu) ON true
        JOIN parcels p ON p.idu = c.idu
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        WHERE s.type = 'PC' AND (CAST(:c AS text) IS NULL OR s.commune = :c)
          AND s.date < now() - (:m || ' months')::interval
          AND s.raw->>'daact' IS NULL
          -- parcelle toujours non bâtie : pas d'exclusion « déjà bâti » au run q_v2
          AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                          WHERE cr.run_label = :run AND cr.parcel_id = p.id
                            AND cr.layer_name = 'bati' AND cr.result = 'HARD_EXCLUDE')
        ORDER BY s.date ASC LIMIT 500"""),
        {"c": commune, "m": months, "run": RUN, "v2run": _v2run(db)}).mappings().all()
    # affichage borné à 500 (tri anciens d'abord = les plus « morts ») ; le compte reste honnête
    true_total = len(rows) if len(rows) < 500 else int(db.execute(text("""
        SELECT count(DISTINCT s.id) FROM sitadel_permits s
        JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS c(idu) ON true
        JOIN parcels p ON p.idu = c.idu
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE s.type = 'PC' AND (CAST(:c AS text) IS NULL OR s.commune = :c)
          AND s.date < now() - (:m || ' months')::interval AND s.raw->>'daact' IS NULL
          AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                          WHERE cr.run_label = :run AND cr.parcel_id = p.id
                            AND cr.layer_name = 'bati' AND cr.result = 'HARD_EXCLUDE')"""),
        {"c": commune, "m": months, "run": RUN}).scalar() or 0)
    return {"commune": commune or "Toute l'île", "months": months, "total": true_total, "affiches": len(rows),
            "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "etat", "nb_lgt", "idu",
                                            "surface_m2", "statut", "q_score")},
                       "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                       "geom": json.loads(r["g"])} for r in rows]}


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
        "indicateur": "Délai médian d'instruction dépôt → autorisation",
        "unite": "mois", "nature": nature, "cohortes": f"{an['lo']}–{an['hi']}",
        "maturite_cutoff": cutoff.isoformat() if cutoff else None,
        "note": ("Médiane robuste (pas moyenne). Dépôts des 12 derniers mois exclus "
                 "(cohortes non mûres, biais de survie). Lignes dépôt>autorisation exclues."),
        "censure": ("Source Sitadel = dossiers ACCORDÉS uniquement : refusés et en cours "
                    "d'instruction non observables → taux de dossiers en cours non mesurable ici."),
        "disclaimer": "Indicateur HISTORIQUE (2013+), pas une promesse de délai futur.",
        "communes": data}


# ───────────────────────── M07 — FONCIER FANTÔME ─────────────────────────

@router.get("/fantome")
def fantome(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut, d.q_score,
               pm.siren, pm.denomination,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0,
               NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren) AS inpi_introuvable,
               EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false) AS dirigeant_inactif,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND d.q_score >= 50 AND pm.groupe NOT IN (1, 2, 3, 4, 9)
          AND pm.siren IS NOT NULL
          AND (NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren)
               OR EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false))
        ORDER BY d.q_score DESC LIMIT 600"""),
        {"c": commune, "run": RUN, "v2run": _v2run(db)}).mappings().all()
    true_total = len(rows) if len(rows) < 600 else int(db.execute(text(
        """SELECT count(*) FROM parcels p
           JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           JOIN parcelle_personne_morale pm ON pm.idu = p.idu
           WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND d.q_score >= 50
             AND pm.groupe NOT IN (1, 2, 3, 4, 9)"""), {"c": commune, "run": RUN}).scalar() or 0)
    return {"total": true_total, "affiches": len(rows), "items": [{
        **{k: r[k] for k in ("idu", "surface_m2", "statut", "q_score", "siren", "denomination")},
        "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
        "verrou": "PM introuvable au RNE" if r["inpi_introuvable"] else "dirigeant inactif (RNE)",
        "levier": "notaire / recherche du représentant" if r["inpi_introuvable"] else "rachat de parts / contact liquidateur",
        "geom": json.loads(r["g"]),
    } for r in rows]}


# ───────────────────────── M06 — MODE BAILLEUR ─────────────────────────

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
def bailleur(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut,
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
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
        ORDER BY (cs.statut = 'carencee') DESC NULLS LAST, COALESCE(r.sdp_residuelle_m2, 0) DESC LIMIT 500"""),
        {"c": commune, "run": RUN, "v2run": _v2run(db)}).mappings().all()
    true_total = len(rows) if len(rows) < 500 else int(db.execute(text(
        """SELECT count(*) FROM parcels p
           JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
           WHERE (CAST(:c AS text) IS NULL OR p.commune = :c)
             AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
             AND EXISTS (SELECT 1 FROM spatial_layers q WHERE q.kind = 'qpv'
                         AND ST_Intersects(p.geom_2975, q.geom_2975))"""),
        {"c": commune, "run": RUN}).scalar() or 0)
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


@router.post("/duediligence")
def duediligence(body: DueDiligenceIn, db: Session = Depends(get_db)) -> dict:
    import re
    tokens = [t.strip().upper().replace(" ", "") for t in re.split(r"[\n,;]+", body.refs) if t.strip()]
    v2run = _v2run(db)
    items = []
    for t in tokens[:60]:
        row = db.execute(text("""
            SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2,
                   d.matrice_statut AS statut, d.q_score, d.a_score, d.completeness_score,
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
            LIMIT 1"""), {"t": t, "run": RUN, "v2run": v2run}).mappings().first()
        items.append(dict(row) | {"etage0": bool(row["etage0"]),
                                  "pdf": f"/parcels/{row['idu']}/export.pdf?source={RUN}"} if row
                     else {"ref": t, "erreur": "référence introuvable"})
    ok = [i for i in items if "idu" in i]
    return {"n_demandes": len(tokens), "n_trouvees": len(ok), "items": items}


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
    from ..faisabilite.bilan import compute_bilan, sector_price
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses

    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, "Parcelle inconnue")
    out: dict = {"idu": idu}
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
    hyp = Hypotheses()
    prix = sector_price(db, row["id"], hyp)
    out["marche"] = {k: prix.get(k) for k in ("type_prix", "median", "q1", "q3", "n", "fiabilite",
                                              "tendance", "volatilite", "radius_m") if k in prix}
    # P14 (dernière passe) : fraîcheur DVF — période RÉELLE couverte (SQL), pour que l'utilisateur
    # sache de QUAND datent les prix (« fiabilité fragile » reste, c'est le n de ventes).
    out["marche"]["dvf_couverture"] = _dvf_couverture(db)
    shab = (f.fourchette or {}).get("shab_vendable_m2") if fz else None
    if shab and prix.get("median"):
        b = compute_bilan(float(shab), float(row["s"] or 0), prix, hyp)
        out["bilan"] = {k: v for k, v in b.__dict__.items() if not k.startswith("_")}
    else:
        out["bilan"] = None
    # fiscal / leviers (bilan promoteur — données en base + hypothèses ÉTIQUETÉES)
    qpv = bool(db.execute(text("""SELECT 1 FROM spatial_layers q JOIN parcels p ON p.idu = :i
        WHERE q.kind = 'qpv' AND ST_Intersects(p.geom_2975, q.geom_2975) LIMIT 1"""), {"i": idu}).scalar())
    vue = db.execute(text("SELECT vue FROM parcel_vue_mer vm JOIN parcels p ON p.id = vm.parcel_id WHERE p.idu = :i"),
                     {"i": idu}).scalar()
    out["fiscal"] = {
        "qpv": qpv,
        "tva": ("2,1 % (LLS en QPV — LODEOM) au lieu de 8,5 % DOM" if qpv
                else "8,5 % (taux DOM) — 2,1 % possible en LLS selon montage"),
        "ta_note": "Taxe d'aménagement : taux communal à confirmer en mairie (non ingéré) — "
                   "hypothèse indicative 5 % + part départementale.",
        "vue_mer": vue,
        "prime_vue_mer": "prime de prix de sortie (vue dégagée)" if vue == "oui" else None,
    }
    # RTAA DOM (mandat contexte-commune, 5bis) — rappel réglementaire de conception,
    # vérifié sur Légifrance (config/rtaa_dom.yaml), hors scoring
    from ..config import load_yaml_config
    rtaa = load_yaml_config("rtaa_dom")
    out["rtaa"] = {"meta": rtaa["meta"], "exigences": rtaa["exigences"]}
    return out


class ChargeIn(BaseModel):
    # hypothèses métier SAISIES (jamais estimées par LABUSE) — défauts « à ajuster »
    cout_construction_m2: float = Field(2500.0, ge=500, le=8000)   # €/m² de plancher
    marge_frais_pct: float = Field(21.0, ge=0, le=60)              # marge promoteur + frais (% du CA)
    prix_demande_eur: float | None = Field(None, ge=0, le=500_000_000)


@router.post("/faisabilite/{idu}/charge")
def faisabilite_charge(idu: str, body: ChargeIn, db: Session = Depends(get_db)) -> dict:
    """CALCULETTE de charge foncière (déterministe, testable). RÉUTILISE le moteur : SDP vendable
    (capacité) + prix de sortie (DVF) sont SOURCÉS ; le coût de construction et la marge viennent
    du corps de requête (hypothèses du promoteur). Cas limites honnêtes : capacité non résolue ou
    prix DVF insuffisant → `calculable:false` + raison, jamais un faux chiffre."""
    from ..faisabilite.bilan import (
        CALCULETTE_COUT_DEFAUT_M2,
        CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
        compute_calculette,
        sector_price,
    )
    from ..faisabilite.db import parcel_faisabilite
    from ..faisabilite.engine import Hypotheses

    defaults = {"cout_construction_m2": CALCULETTE_COUT_DEFAUT_M2,
                "marge_frais_pct": CALCULETTE_MARGE_FRAIS_DEFAUT_PCT}
    row = db.execute(text("SELECT id, round(surface_m2) AS s FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, "Parcelle inconnue")
    fz = parcel_faisabilite(db, row["id"])
    shab = (fz[1].fourchette or {}).get("shab_vendable_m2") if fz else None
    if not shab:
        # capacité non résolue (zone PLU non calibrée / RNU) → on ne calcule pas de résultat creux
        return {"calculable": False, "raison": "capacite_non_resolue", "defaults": defaults,
                "message": "Capacité constructible non résolue pour cette parcelle (zone PLU "
                           "non résolue / non constructible) — charge foncière non calculable."}
    prix = sector_price(db, row["id"], Hypotheses())
    res = compute_calculette(float(shab), float(row["s"] or 0), prix,
                             body.cout_construction_m2, body.marge_frais_pct, body.prix_demande_eur)
    res["defaults"] = defaults
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
        compute_bilan,
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
    # bilan (si capacité vendable + prix) — hypothèses = celles de la calculette par défaut
    hyp = Hypotheses()
    prix = sector_price(db, row["id"], hyp)
    shab = fo.get("shab_vendable_m2")
    if shab and prix.get("median"):
        bp = {"cout_construction_m2_sdp": CALCULETTE_COUT_DEFAUT_M2,
              "marge_cible_pct": CALCULETTE_MARGE_FRAIS_DEFAUT_PCT,
              "honoraires_pct": 0.0, "frais_financiers_pct": 0.0}
        b = compute_bilan(float(shab), float(row["s"] or 0), prix, hyp, bilan_params=bp)
        for i, s in enumerate(b.steps, 1):
            facts[f"bilan_{i}"] = core_mod.Fact(f"{s.label} : {s.valeur}", _PROV_SOCLE.get(s.prov, "ESTIME"))
        cf = b.charge_fonciere or {}
        facts["charge_fonciere"] = core_mod.Fact(
            f"charge foncière médiane {cf.get('central')} € (~{cf.get('par_m2_terrain')} €/m² de terrain), "
            f"hypothèses par défaut coût {CALCULETTE_COUT_DEFAUT_M2:.0f} €/m² et marge+frais "
            f"{CALCULETTE_MARGE_FRAIS_DEFAUT_PCT:.0f} % (ajustables)", "ESTIME")
        facts["prix_dvf_fiabilite"] = core_mod.Fact(
            f"prix de sortie DVF — fiabilité {prix.get('fiabilite')}",
            "SOURCE" if prix.get("fiabilite") == "fiable" else "ESTIME")
    return facts


@router.get("/faisabilite/{idu}/explain")
def faisabilite_explain(idu: str, db: Session = Depends(get_db)) -> dict:
    """M11 Surface C : explication EN CLAIR de la dérivation du chiffrage, ancrée sur les STEPS du
    moteur (déterministes). L'IA narre, elle ne recalcule pas ; la couche 2 du socle rejette tout
    chiffre absent des étapes. Sur clic uniquement (coût) ; caché par (idu, run, question)."""
    from ..ai import core
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    QUESTION = "explication_faisabilite"

    hit = core.cache_get(db, idu, Q_A_RUN_LABEL, QUESTION)
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
    res = core.complete(db, kind="explain-faisa", model=core.MODEL_REASONING, max_tokens=800,
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
    core.cache_put(db, idu, Q_A_RUN_LABEL, QUESTION, out, kind="explain-faisa")
    return out


class ProgrammeIn(BaseModel):
    type: str = "logements"          # logements | etudiant | bureaux
    batiments: int = 1
    niveaux: int = 2                 # R+n → n
    logements_par_batiment: int = 8
    surface_unite_m2: float = 60     # hypothèse AFFICHÉE (m² SDP par unité)
    parking: bool = True
    commune: str | None = None       # None = île entière (extension île)


@router.post("/programme")
def faisabilite_sens2(body: ProgrammeIn, db: Session = Depends(get_db)) -> dict:
    """SENS 2 (programme → parcelles) : critères CALCULÉS et AFFICHÉS → candidates triées par
    marge de capacité. La hauteur PLU est vérifiée zone par zone (resolve_zone) quand calibrée."""
    from ..faisabilite.plu_rules import resolve_zone

    unites = max(1, body.batiments) * max(1, body.logements_par_batiment)
    sdp_min = round(unites * body.surface_unite_m2 * 1.15)       # +15 % circulations (hypothèse)
    parking_m2 = round(unites * 25) if body.parking else 0        # 25 m²/place (config PLU)
    hauteur_min = (body.niveaux + 1) * 3.0                        # R+n → (n+1) niveaux × 3 m
    # Fix LOT 3 : requête LÉGÈRE (sans la géométrie lourde) et SANS LIMIT prématuré — TOUTES les
    # parcelles satisfaisant les filtres SQL (SDP, surface, statut, run servi) sont ramenées, PUIS
    # le filtre HAUTEUR (résolu en Python via resolve_zone) s'applique, PUIS le tri marge, PUIS la
    # troncature d'AFFICHAGE. Avant, `LIMIT 300` sur SDP DESC coupait AVANT le filtre hauteur →
    # des parcelles valides (hors des 300 plus grosses SDP) étaient jetées sans être examinées.
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, r.sdp_residuelle_m2,
               d.matrice_statut AS statut, d.q_score, cr.detail AS zonage,
               s2.tier AS tier_v2, s2.rang AS rang_v2,
               (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
        FROM parcels p
        JOIN parcel_residuel r ON r.parcel_id = p.id AND r.sdp_residuelle_m2 >= :sdp
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
          AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
        LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
        LEFT JOIN dryrun_cascade_results cr ON cr.run_label = :run AND cr.parcel_id = p.id
          AND cr.layer_name = 'zonage_plu_gpu' AND cr.detail LIKE 'Zone PLU%'
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND p.surface_m2 >= :smin"""),
        {"sdp": sdp_min, "run": RUN, "c": body.commune, "v2run": _v2run(db),
         "smin": sdp_min * 0.4 + parking_m2}).mappings().all()
    import re as _re
    hcache: dict = {}   # (zone, commune) → hauteur — resolve_zone n'est appelé qu'une fois par couple
    items = []
    for r in rows:
        m = _re.search(r"« ([^»]+) »", r["zonage"] or "")
        zone = (m.group(1) if m else "").strip()
        key = (zone, r["commune"])
        if key not in hcache:
            # la hauteur PLU se résout avec la commune DE LA PARCELLE (mode île : elles diffèrent)
            rules = resolve_zone(zone, r["commune"]) if zone else None
            h = getattr(rules, "hauteur_max_m", None) if rules else None
            if h is None and rules is not None:
                h = getattr(rules, "hf_m", None) or getattr(rules, "he_m", None)
            hcache[key] = h
        h = hcache[key]
        hauteur_ok = (h is None) or (float(h) >= hauteur_min)
        if not hauteur_ok:                # filtre hauteur AVANT toute troncature (Fix A)
            continue
        marge = round(float(r["sdp_residuelle_m2"]) / sdp_min, 2)
        items.append({"idu": r["idu"], "commune": r["commune"], "surface_m2": r["surface_m2"],
                      "sdp": round(r["sdp_residuelle_m2"]),
                      "statut": r["statut"], "q_score": r["q_score"],
                      "tier_v2": r["tier_v2"], "rang_v2": r["rang_v2"], "etage0": bool(r["etage0"]),
                      "zone": zone or None,
                      "hauteur_plu_m": float(h) if h is not None else None,
                      "hauteur_verifiee": h is not None, "marge_capacite": marge})
    items.sort(key=lambda x: -x["marge_capacite"])
    top = items[:200]                     # troncature d'AFFICHAGE seulement — `n` reste le vrai total
    if top:                               # géométries ramenées UNIQUEMENT pour les 200 affichées
        geoms = {gr["idu"]: json.loads(gr["g"]) for gr in db.execute(text(
            "SELECT idu, ST_AsGeoJSON(ST_Transform(geom_2975, 4326)) AS g "
            "FROM parcels WHERE idu = ANY(:idus)"),
            {"idus": [i["idu"] for i in top]}).mappings()}
        for i in top:
            i["geom"] = geoms.get(i["idu"])
    return {
        "criteres": {"unites": unites, "sdp_min_m2": sdp_min,
                     "calcul": f"{unites} unités × {body.surface_unite_m2} m² × 1,15 (circulations)",
                     "parking_m2": parking_m2, "hauteur_min_m": hauteur_min,
                     "hauteur_regle": f"R+{body.niveaux} → {hauteur_min:.0f} m ({body.niveaux + 1} niveaux × 3 m)"},
        "bandeau": ("Estimation capacitaire — hypothèses affichées (m²/unité, +15 % circulations, "
                    "25 m²/place) ; hauteur PLU vérifiée quand la zone est calibrée, sinon « à "
                    "instruire ». Étude d'architecte requise."),
        "n": len(items), "items": top,   # n = VRAI nombre de correspondances ; items = top 200 affichées
    }
