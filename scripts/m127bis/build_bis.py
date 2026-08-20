"""M127-bis Phase 1 — les trois réparations : la donnée.

R1 (propriétaire historisé) — MESURÉ : `date_prise_fonction` couvre 2 % (458/23 095) → l'âge
dirigeant N'EST PAS historisable (dit, proposé : ingestion de l'historique RNE = mandat dédié) ;
`pm_millesimes` absente → PM nue / succession non historisables. SEUL BODACC concourt (événement
daté 2008+ ; le LIEN parcelle→SIREN reste l'instantané DGFiP 2025 — consigné).

R2 (causes M125 en catégories) — la colonne `residuel_cause` du dataset v2 devient une catégorie
FAMILLE (split ':', les codes de zone restent en fiche) : calculee / zone_non_constructible /
terrain_exigu / zone_non_resolue / habitat_interdit / hors_plu / redhibitoire / capacite_nulle.

R3 (features bâti) — BD TOPO ne porte AUCUNE date (attrs mesurés : hauteur, nature, nb_logements,
nombre_d_etages, usage, source) → pas d'âge du bâti (dit). Candidates CONSTRUITES (état physique
2026, statique consigné — bien moins anachronique qu'un état de propriétaire : le bâti bouge peu) :
  · taux_occupation  = emprise bâtie / surface parcelle (les 2 colonnes existent au dataset)
  · nb_batiments     — bâtiments intersectant ≥ 10 m² (même seuil que bati.stats_batch)
  · bati_max_m2      — plus grande emprise intersectée
  · hauteur_max_m / etages_max / nb_logements_bdtopo — attrs BD TOPO
  · usage_dominant   — usage BD TOPO du plus grand bâtiment
  · pct_potentiel_v2 — bâti vs droits (déjà au dataset : une case sur 2000 m² U ≠ immeuble saturé)
  · surelevation     — parcel_residuel_bati.surelevation_possible (existante)

Usage : python scripts/m127bis/build_bis.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope

REPORTS = Path("reports/m127bis")

SQL_BATI = """
DROP TABLE IF EXISTS p_model_bati_features;
CREATE TABLE p_model_bati_features AS
WITH inter AS (
  SELECT f.idu,
         ST_Area(ST_Intersection(b.geom_2975, p.geom_2975)) AS a,
         NULLIF(b.attrs->>'hauteur','')::float              AS hauteur,
         NULLIF(b.attrs->>'nombre_d_etages','')::int        AS etages,
         NULLIF(b.attrs->>'nb_logements','')::int           AS logts,
         COALESCE(b.attrs->>'usage', b.attrs->>'nature')    AS usage
  FROM p_model_frame f
  JOIN parcels p ON p.id = f.parcel_id
  JOIN spatial_layers b ON b.kind = 'batiment'
   AND b.geom_2975 && p.geom_2975 AND ST_Intersects(b.geom_2975, p.geom_2975)
)
SELECT idu,
       count(*) FILTER (WHERE a >= 10)                    AS nb_batiments,
       max(a)                                             AS bati_max_m2,
       max(hauteur)                                       AS hauteur_max_m,
       max(etages)                                        AS etages_max,
       sum(logts)                                         AS nb_logements_bdtopo,
       (array_agg(usage ORDER BY a DESC))[1]              AS usage_dominant
FROM inter GROUP BY idu;
ALTER TABLE p_model_bati_features ADD PRIMARY KEY (idu);
"""

SQL_V2BIS = """
DROP TABLE IF EXISTS p_model_dataset_v2bis;
CREATE TABLE p_model_dataset_v2bis AS
SELECT d.*,
       -- R2 · la cause M125 en catégorie FAMILLE (« 0 zone N » ≠ « 0 terrain exigu »)
       COALESCE(split_part(d.residuel_cause, ':', 1), 'calculee') AS residuel_cause_cat,
       -- R3 · features bâti (état physique, statique consigné)
       CASE WHEN d.surface_m2 > 0
            THEN LEAST(coalesce(d.emprise_bati_m2,0) / d.surface_m2, 2.0) END AS taux_occupation,
       COALESCE(bf.nb_batiments, 0)       AS nb_batiments,
       bf.bati_max_m2, bf.hauteur_max_m, bf.etages_max, bf.nb_logements_bdtopo,
       bf.usage_dominant,
       rb.surelevation_possible
FROM p_model_dataset_v2 d
LEFT JOIN p_model_bati_features bf ON bf.idu = d.idu
LEFT JOIN parcel_residuel_bati rb  ON rb.idu = d.idu;
CREATE UNIQUE INDEX ON p_model_dataset_v2bis (idu, annee);
CREATE INDEX ON p_model_dataset_v2bis (annee);
"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with session_scope() as s:
        s.execute(text(SQL_BATI))
    t1 = time.time()
    print(f"p_model_bati_features ✓ ({(t1-t0)/60:.1f} min)")
    with session_scope() as s:
        s.execute(text(SQL_V2BIS))
    print(f"p_model_dataset_v2bis ✓ ({(time.time()-t1)/60:.1f} min)")
    with session_scope() as s:
        cov = {}
        for col in ("taux_occupation", "nb_batiments", "bati_max_m2", "hauteur_max_m",
                    "etages_max", "nb_logements_bdtopo", "usage_dominant",
                    "surelevation_possible", "residuel_cause_cat"):
            cov[col] = float(s.execute(text(
                f"SELECT count({col})::float/count(*) FROM p_model_dataset_v2bis")).scalar())
        dist = [dict(r._mapping) for r in s.execute(text(
            "SELECT residuel_cause_cat, count(*) n FROM p_model_dataset_v2bis "
            "GROUP BY 1 ORDER BY n DESC"))]
    manifest = {"couvertures": {k: round(v, 4) for k, v in cov.items()},
                "cause_cat": dist,
                "r1_verdict": {"age_dirigeant": "NON historisable (prise_fonction 2 %) — fait affiché",
                               "succession": "NON historisable (snapshot) — fait affiché",
                               "pm_nue_dormante": "NON historisable (pm_millesimes absente) — fait affiché",
                               "proc_collective": "CONCOURT (événement daté 2008+ ; lien parcelle→SIREN = snapshot 2025 consigné)"}}
    (REPORTS / "manifest-bis.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
