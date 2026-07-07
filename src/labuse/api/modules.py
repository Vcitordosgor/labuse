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
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/modules", tags=["modules"])

RUN = "q_v2"


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


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
    rows = db.execute(text("""
        SELECT m.idu, m.surface_m2, m.bati_count, m.emprise_pct, m.zone, m.mic_radius_m,
               m.lot_area_m2, m.acces_voirie, m.score, ST_AsGeoJSON(m.lot_geom) AS lot,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM module_division m JOIN parcels p ON p.id = m.parcel_id
        WHERE m.score >= :s AND (CAST(:c AS text) IS NULL OR p.commune = :c)
        ORDER BY m.score DESC LIMIT :lim"""),
        {"s": min_score, "lim": limit, "c": commune}).mappings().all()
    total = db.execute(text(
        "SELECT count(*) FROM module_division m JOIN parcels p ON p.id = m.parcel_id"
        " WHERE m.score >= :s AND (CAST(:c AS text) IS NULL OR p.commune = :c)"),
        {"s": min_score, "c": commune}).scalar()
    return {"total": int(total or 0), "items": [{
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
    rows = db.execute(text("""
        SELECT p.idu, p.commune, p.surface_m2, d.matrice_statut AS statut, d.q_score, d.a_score,
               d.completeness_score, r.sdp_residuelle_m2,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE pm.siren = :s ORDER BY d.q_score DESC NULLS LAST"""),
        {"s": siren, "run": RUN}).mappings().all()
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
                   "surface_m2": round(r["surface_m2"] or 0), "sdp": r["sdp_residuelle_m2"],
                   "geom": json.loads(r["g"])} for r in rows],
    }


# ───────────────────────── M03 — RADAR PERMIS ─────────────────────────

@router.get("/permis")
def permis(commune: str | None = None, months: int = 24, db: Session = Depends(get_db)) -> dict:
    # fenêtre ancrée sur la FIN DES DONNÉES (le flux Sitadel s'arrête avant aujourd'hui) — honnêteté
    dmax = db.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()
    rows = db.execute(text("""
        SELECT permit_id, type, date::date::text AS date, commune,
               raw->>'etat' AS etat, raw->>'nb_lgt' AS nb_lgt, raw->>'surf_hab' AS surf_hab,
               CASE WHEN geom IS NOT NULL THEN ST_AsGeoJSON(geom) END AS g
        FROM sitadel_permits
        WHERE (CAST(:c AS text) IS NULL OR commune = :c) AND date >= :dmax - (:m || ' months')::interval
        ORDER BY date DESC LIMIT 2000"""), {"c": commune, "m": months, "dmax": dmax}).mappings().all()
    geo = [r for r in rows if r["g"]]
    return {
        "commune": commune or "Toute l'île", "months": months, "total": len(rows),
        "donnees_jusqu_au": dmax.date().isoformat() if dmax else None,
        "geocodes": len(geo), "pct_geocode": round(100 * len(geo) / len(rows)) if rows else 0,
        "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "etat", "nb_lgt", "surf_hab")},
                   "geom": json.loads(r["g"]) if r["g"] else None} for r in rows],
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
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
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
        ORDER BY s.date ASC LIMIT 500"""),
        {"c": commune, "m": months, "run": RUN}).mappings().all()
    return {"commune": commune or "Toute l'île", "months": months, "total": len(rows),
            "items": [{**{k: r[k] for k in ("permit_id", "type", "date", "etat", "nb_lgt", "idu",
                                            "surface_m2", "statut", "q_score")},
                       "geom": json.loads(r["g"])} for r in rows]}


# ───────────────────────── M05 — VÉLOCITÉ ADMIN ─────────────────────────
# LIMITE HONNÊTE : la base ne porte NI date de dépôt NI date de décision (une seule `date` +
# `daact`). Le délai médian dépôt→décision est IMPOSSIBLE ici → on livre ce qui est mesurable :
# volumes, part achevée (daact), délai médian date→achèvement. Consigné.

@router.get("/velocite")
def velocite(fmt: str = "json", db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT commune, count(*) AS permis,
               count(*) FILTER (WHERE raw->>'daact' IS NOT NULL) AS acheves,
               round(100.0 * count(*) FILTER (WHERE raw->>'daact' IS NOT NULL) / count(*)) AS pct_acheves,
               round(percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY ((raw->>'daact')::date - date::date))
                 FILTER (WHERE raw->>'daact' IS NOT NULL) / 30.44) AS delai_median_mois,
               count(*) FILTER (WHERE date >= now() - interval '24 months') AS depuis_24m
        FROM sitadel_permits GROUP BY commune ORDER BY permis DESC"""),
    ).mappings().all()
    data = [dict(r) for r in rows]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="velocite_admin.csv"'})
    return {"note": "délai = date permis → déclaration d'achèvement (dépôt→décision non porté par la source)",
            "communes": data}


# ───────────────────────── M07 — FONCIER FANTÔME ─────────────────────────

@router.get("/fantome")
def fantome(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut, d.q_score,
               pm.siren, pm.denomination,
               NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren) AS inpi_introuvable,
               EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false) AS dirigeant_inactif,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND d.q_score >= 50 AND pm.groupe NOT IN (1, 2, 3, 4, 9)
          AND pm.siren IS NOT NULL
          AND (NOT EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren)
               OR EXISTS (SELECT 1 FROM pm_dirigeants dg WHERE dg.siren = pm.siren AND dg.actif = false))
        ORDER BY d.q_score DESC LIMIT 600"""),
        {"c": commune, "run": RUN}).mappings().all()
    return {"total": len(rows), "items": [{
        **{k: r[k] for k in ("idu", "surface_m2", "statut", "q_score", "siren", "denomination")},
        "verrou": "PM introuvable au RNE" if r["inpi_introuvable"] else "dirigeant inactif (RNE)",
        "levier": "notaire / recherche du représentant" if r["inpi_introuvable"] else "rachat de parts / contact liquidateur",
        "geom": json.loads(r["g"]),
    } for r in rows]}


# ───────────────────────── M06 — MODE BAILLEUR ─────────────────────────

@router.get("/bailleur")
def bailleur(commune: str | None = None, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(text("""
        SELECT p.idu, round(p.surface_m2) AS surface_m2, d.matrice_statut AS statut,
               d.q_score, d.a_score, r.sdp_residuelle_m2,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcels p
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        JOIN spatial_layers q ON q.kind = 'qpv' AND ST_Intersects(p.geom_2975, q.geom_2975)
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
        ORDER BY COALESCE(r.sdp_residuelle_m2, 0) DESC LIMIT 500"""),
        {"c": commune, "run": RUN}).mappings().all()
    return {"total": len(rows),
            "lecture_lls": ("QPV : TVA 2,1 % (au lieu de 8,5 % DOM), abattement TFPB 30 %, "
                            "éligibilité LLS/LLTS renforcée — bilan bailleur à instruire au cas par cas."),
            "items": [{**{k: r[k] for k in ("idu", "surface_m2", "statut", "q_score", "a_score")},
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
    items = []
    for t in tokens[:60]:
        row = db.execute(text("""
            SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2,
                   d.matrice_statut AS statut, d.q_score, d.a_score, d.completeness_score,
                   (SELECT count(*) FROM dryrun_cascade_results cr WHERE cr.run_label = :run
                     AND cr.parcel_id = p.id AND cr.result = 'SOFT_FLAG') AS flags,
                   (SELECT count(*) FROM dryrun_cascade_results cr WHERE cr.run_label = :run
                     AND cr.parcel_id = p.id AND cr.result = 'HARD_EXCLUDE') AS exclusions
            FROM parcels p
            LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            WHERE p.idu = :t OR (p.section || p.numero) = :t OR (p.section || lpad(p.numero, 4, '0')) = :t
            LIMIT 1"""), {"t": t, "run": RUN}).mappings().first()
        items.append(dict(row) | {"pdf": f"/parcels/{row['idu']}/export.pdf?source={RUN}"} if row
                     else {"ref": t, "erreur": "référence introuvable"})
    ok = [i for i in items if "idu" in i]
    return {"n_demandes": len(tokens), "n_trouvees": len(ok), "items": items}


# ───────────────── M22 + BILAN — ÉTUDE DE FAISABILITÉ BIDIRECTIONNELLE ─────────────────
# RÉUTILISE le moteur existant (faisabilite/engine + bilan) — rien de recalculé à la main.
# Ratios : étage 3 m, place 25 m² (config plu YAML) ; m²/logement = paramètre AFFICHÉ (défaut 60).

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
                           "bandeau": f.bandeau}
    else:
        out["capacite"] = None
    hyp = Hypotheses()
    prix = sector_price(db, row["id"], hyp)
    out["marche"] = {k: prix.get(k) for k in ("type_prix", "median", "q1", "q3", "n", "fiabilite",
                                              "tendance", "volatilite", "radius_m") if k in prix}
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
    rows = db.execute(text("""
        SELECT p.idu, p.commune, round(p.surface_m2) AS surface_m2, r.sdp_residuelle_m2,
               d.matrice_statut AS statut, d.q_score, cr.detail AS zonage,
               ST_AsGeoJSON(ST_Transform(p.geom_2975, 4326)) AS g
        FROM parcels p
        JOIN parcel_residuel r ON r.parcel_id = p.id AND r.sdp_residuelle_m2 >= :sdp
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
          AND d.matrice_statut IN ('chaude', 'a_surveiller', 'a_creuser')
        LEFT JOIN dryrun_cascade_results cr ON cr.run_label = :run AND cr.parcel_id = p.id
          AND cr.layer_name = 'zonage_plu_gpu' AND cr.detail LIKE 'Zone PLU%'
        WHERE (CAST(:c AS text) IS NULL OR p.commune = :c) AND p.surface_m2 >= :smin
        ORDER BY r.sdp_residuelle_m2 DESC LIMIT 300"""),
        {"sdp": sdp_min, "run": RUN, "c": body.commune,
         "smin": sdp_min * 0.4 + parking_m2}).mappings().all()
    import re as _re
    items = []
    for r in rows:
        m = _re.search(r"« ([^»]+) »", r["zonage"] or "")
        zone = (m.group(1) if m else "").strip()
        # la hauteur PLU se résout avec la commune DE LA PARCELLE (mode île : elles diffèrent)
        rules = resolve_zone(zone, r["commune"]) if zone else None
        h = getattr(rules, "hauteur_max_m", None) if rules else None
        if h is None and rules is not None:
            h = getattr(rules, "hf_m", None) or getattr(rules, "he_m", None)
        hauteur_ok = (h is None) or (float(h) >= hauteur_min)
        if not hauteur_ok:
            continue
        marge = round(float(r["sdp_residuelle_m2"]) / sdp_min, 2)
        items.append({"idu": r["idu"], "commune": r["commune"], "surface_m2": r["surface_m2"],
                      "sdp": round(r["sdp_residuelle_m2"]),
                      "statut": r["statut"], "q_score": r["q_score"], "zone": zone or None,
                      "hauteur_plu_m": float(h) if h is not None else None,
                      "hauteur_verifiee": h is not None, "marge_capacite": marge,
                      "geom": json.loads(r["g"])})
    items.sort(key=lambda x: -x["marge_capacite"])
    return {
        "criteres": {"unites": unites, "sdp_min_m2": sdp_min,
                     "calcul": f"{unites} unités × {body.surface_unite_m2} m² × 1,15 (circulations)",
                     "parking_m2": parking_m2, "hauteur_min_m": hauteur_min,
                     "hauteur_regle": f"R+{body.niveaux} → {hauteur_min:.0f} m ({body.niveaux + 1} niveaux × 3 m)"},
        "bandeau": ("Estimation capacitaire — hypothèses affichées (m²/unité, +15 % circulations, "
                    "25 m²/place) ; hauteur PLU vérifiée quand la zone est calibrée, sinon « à "
                    "instruire ». Étude d'architecte requise."),
        "n": len(items), "items": items[:200],
    }
