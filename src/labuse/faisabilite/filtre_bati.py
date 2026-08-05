"""FILTRE CLIENT BÂTI (M28, arbitrages Vic A1-A6) — cache `parcel_filtre_bati`.

Hiérarchie à 3 étages sur les parcelles portant un bâti (règle produit, jamais un poids) :
  étage 1 — ratio = emprise_max / surface (A1, seuils 15/40 %, UN point de calcul :
            `p_model_bati.emprise_bati_m2`, qui EST max(BD TOPO, CoSIA) depuis la bascule
            du 04/08 — dépendance documentée) ;
  étage 2 — année (A2) : DPE (annee_construction, point-in-parcel) → Sourcé ; BDNB absente
            des DOM ; année ABSENTE = traitée comme bâti récent (durcit — le doute ne
            profite jamais au classement) ;
  étage 3 — divisibilité (A3) : ÉCART SIGNALÉ AU RAPPORT — `coeff_recul` n'existe dans
            aucune fiche calibration. Substitution (à valider point d'arrêt 1) : divisible
            si commune CALIBRÉE (fiche calibration_<commune>.yaml présente) ET zone U/AU ET
            (surface − emprise_max) ≥ 600 m² (le plancher local déjà défini, statuts.py) —
            étiquette Sourcé ; commune non calibrée (les 14 du train 6) → Absent, badge
            non servi, jamais estimé.
Décisions (une par parcelle) : 'servie' (badge bâtie) · 'divisible' (servie + badge
division) · 'saturee' (badge + tier dédié, A4). Le chemin 'saturee' inclut AUSSI les
parcelles à SDP saturée par le bâti existant (pct_potentiel ≥ 100, cache parcel_residuel) —
MÊME mécanisme (A4). Kill-switch pipeline : LABUSE_DISABLE_FILTRE_BATI=1.
"""
from __future__ import annotations

import glob
import os

from sqlalchemy import text

RATIO_MARGINAL_PCT = 15.0     # A1 — en-dessous : bâti marginal, servie
RATIO_SATURE_PCT = 40.0       # A1 — au-dessus : bâtie saturée (tier), pas de repêchage (A4)
ANNEE_RECENTE_APRES = 2016    # étage 2 : bâti < 10 ans (2026) = récent → durcit
PLANCHER_LIBRE_M2 = 600.0     # étage 3 : plancher local existant (statuts.c_surface_min_m2)
SEUIL_BATI_M2 = 20.0          # en-dessous d'emprise : pas « bâtie » (cohérent règle E)


def _insee_calibres() -> list[str]:
    """Communes à fiche calibration présente (config/calibrage/calibration_<nom>.yaml) —
    point unique : le système de fichiers, croisé au référentiel communes."""
    from .. import communes as _c
    noms = {os.path.basename(f)[len("calibration_"):-len(".yaml")]
            for f in glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                            "config", "calibrage", "calibration_*.yaml"))}
    def slug(n: str) -> str:
        s = n.lower()
        for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("î", "i"), ("ï", "i"), ("ô", "o"),
                     ("û", "u"), ("'", "_"), ("-", "_"), (" ", "_")):
            s = s.replace(a, b)
        return s
    return [v.get('insee', k) for k, v in _c.load_communes().items()
            if slug(v['nom'] if isinstance(v, dict) else str(v)) in noms]


def build_parcel_filtre_bati(session) -> dict:
    """(Re)peuple `parcel_filtre_bati`. Idempotent, transactionnel. Renvoie les effectifs
    par décision. Fraîcheurs amont portées par ligne (source_annee / source_divisibilite)."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_filtre_bati (
          parcel_id integer PRIMARY KEY REFERENCES parcels(id),
          idu varchar(14) NOT NULL,
          ratio_pct double precision NOT NULL,
          emprise_max_m2 double precision NOT NULL,
          etage smallint NOT NULL,
          annee_construction int,
          annee_etiquette varchar(8) NOT NULL,      -- 'Sourcé' (DPE) | 'Absent'
          passoire boolean NOT NULL DEFAULT false,
          divisible boolean,                         -- NULL = Absent (commune non calibrée)
          decision varchar(12) NOT NULL,             -- 'servie' | 'divisible' | 'saturee'
          motif text NOT NULL,
          computed_at timestamptz NOT NULL DEFAULT now())"""))
    session.execute(text("TRUNCATE parcel_filtre_bati"))
    # mapping DPE→parcelle pré-calculé en UNE passe indexée (914 points) — évite une LATERAL
    # quadratique (250 k parcelles × 914 points).
    session.execute(text("""
        CREATE TEMP TABLE IF NOT EXISTS tmp_dpe_parcel AS
        SELECT p.idu, max(d.annee_construction) annee,
               bool_or(d.etiquette_dpe IN ('F','G')) passoire
        FROM dpe_records d
        JOIN parcels p ON d.lon IS NOT NULL
          AND ST_Contains(p.geom_2975, ST_Transform(ST_SetSRID(ST_MakePoint(d.lon,d.lat),4326),2975))
        GROUP BY p.idu"""))
    insee_ok = _insee_calibres()
    session.execute(text(f"""
        INSERT INTO parcel_filtre_bati (parcel_id, idu, ratio_pct, emprise_max_m2, etage,
          annee_construction, annee_etiquette, passoire, divisible, decision, motif)
        SELECT p.id, p.idu, ratio, b.emprise_bati_m2, etage,
          dpe.annee, CASE WHEN dpe.annee IS NOT NULL THEN 'Sourcé' ELSE 'Absent' END,
          COALESCE(dpe.passoire, false), divisible,
          decision,
          CASE decision
            WHEN 'saturee' THEN
              CASE WHEN sat_sdp THEN 'SDP saturée par le bâti existant (pct_potentiel ≥ 100) — même chemin A4'
                   WHEN ratio > {RATIO_SATURE_PCT} THEN 'bâtie saturée — ratio ' || round(ratio) || ' % (emprise ' || round(b.emprise_bati_m2) || ' m², source max(BD TOPO éd. 2026-06-15, CoSIA PVA 2025))'
                   ELSE 'bâtie 15-40 % à bâti ' || CASE WHEN dpe.annee IS NULL THEN 'd''année Absente (traitée récente — le doute ne profite jamais au classement)' ELSE 'récent (' || dpe.annee || ', DPE Sourcé)' END || ', non divisible'
              END
            WHEN 'divisible' THEN 'bâtie ' || round(ratio) || ' % mais DIVISIBLE : partie libre ' || round(p_surf - b.emprise_bati_m2) || ' m² ≥ 600 en U/AU (commune calibrée — Sourcé)'
            ELSE 'bâtie ' || round(ratio) || ' % — servie (' ||
                 CASE WHEN ratio < {RATIO_MARGINAL_PCT} THEN 'bâti marginal'
                      ELSE 'bâti ancien/passoire, DPE Sourcé' END || ')'
          END
        FROM (
          SELECT p.id pid, p.idu pidu,
                 100.0 * b0.emprise_bati_m2 / NULLIF(ST_Area(p.geom_2975),0) AS ratio,
                 ST_Area(p.geom_2975) AS p_surf,
                 (r.pct_potentiel >= 100 AND r.sdp_residuelle_m2 = 0) AS sat_sdp,
                 (z.zone_fam IN ('U','AU')) AS en_uau,
                 substring(p.idu,1,5) = ANY(:insee_ok) AS calibree
          FROM parcels p
          JOIN p_model_bati b0 ON b0.idu = p.idu AND b0.emprise_bati_m2 >= {SEUIL_BATI_M2}
          LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
          LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
        ) base
        JOIN parcels p ON p.id = base.pid
        JOIN p_model_bati b ON b.idu = p.idu
        LEFT JOIN tmp_dpe_parcel dpe ON dpe.idu = p.idu
        CROSS JOIN LATERAL (
          SELECT CASE WHEN base.ratio < {RATIO_MARGINAL_PCT} AND NOT COALESCE(base.sat_sdp,false) THEN 1
                      WHEN base.ratio <= {RATIO_SATURE_PCT} AND NOT COALESCE(base.sat_sdp,false) THEN 2
                      ELSE 3 END AS etage,
                 CASE WHEN NOT base.calibree THEN NULL
                      ELSE (base.en_uau AND (base.p_surf - b.emprise_bati_m2) >= {PLANCHER_LIBRE_M2}) END AS divisible
        ) x
        CROSS JOIN LATERAL (
          SELECT CASE
            WHEN COALESCE(base.sat_sdp,false) THEN 'saturee'
            WHEN base.ratio > {RATIO_SATURE_PCT} THEN 'saturee'
            WHEN base.ratio < {RATIO_MARGINAL_PCT} THEN 'servie'
            -- étage 2 (15-40) :
            WHEN dpe.annee IS NOT NULL AND (dpe.annee < {ANNEE_RECENTE_APRES} OR COALESCE(dpe.passoire,false))
              THEN 'servie'
            -- récente ou Absente → étage 3 :
            WHEN x.divisible IS TRUE THEN 'divisible'
            ELSE 'saturee'
          END AS decision
        ) d"""), {"insee_ok": insee_ok})
    n = dict(session.execute(text(
        "SELECT decision, count(*) FROM parcel_filtre_bati GROUP BY decision")).all())
    return {"servie": n.get("servie", 0), "divisible": n.get("divisible", 0),
            "saturee": n.get("saturee", 0), "communes_calibrees": len(insee_ok)}
