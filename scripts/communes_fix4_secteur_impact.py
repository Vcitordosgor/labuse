"""OUTIL-COMMUNES-FIX-4 LOT 1 — IMPACT sur le cache `dvf_secteur_medianes` (type_bien='terrain'),
lu par la fiche §8 / le Comparatif (`dvf_parcelle.secteur`) ET par le Bilan mode B
(`faisabilite/bilan.py::_prix_terrain_local`). LECTURE SEULE : compare la médiane TERRAIN par secteur
telle qu'elle SERA recalculée par le nouveau builder (qualification unique `ACTE_TERRAIN_NU_CTE` :
pas de local déclaré, une seule commune, surface = somme des subdivisions) à la valeur ACTUELLEMENT en
cache (ancien builder : bâti=0 seul, surface max/count). Aucun écrit : le recalcul du cache est un geste
de déploiement (comme toute ingestion DVF).

Usage : PYTHONPATH=src python scripts/communes_fix4_secteur_impact.py"""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE

_NEW = f"""
WITH {ACTE_TERRAIN_NU_CTE},
sect AS (SELECT DISTINCT substring(dm.id_parcelle FROM 1 FOR 10) AS secteur, dm.id_mutation
         FROM dvf_mutations_parcelle dm
         WHERE dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir')),
neu AS (
  SELECT s.secteur, count(*) AS n,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY a.val / NULLIF(a.terr_tot, 0))
           FILTER (WHERE a.val / NULLIF(a.terr_tot, 0) BETWEEN 50 AND 20000)::int AS med
  FROM sect s JOIN acte_nu a USING (id_mutation)
  WHERE a.val > 1000 AND a.terr_tot > 0
  GROUP BY s.secteur),
anc AS (SELECT secteur, n_ventes AS n, mediane_prix_m2 AS med
        FROM dvf_secteur_medianes WHERE type_bien = 'terrain')
SELECT
  count(*) FILTER (WHERE neu.med IS DISTINCT FROM anc.med OR neu.n IS DISTINCT FROM anc.n) AS secteurs_bouges,
  count(*) FILTER (WHERE anc.secteur IS NOT NULL) AS secteurs_anciens,
  count(*) FILTER (WHERE neu.secteur IS NOT NULL) AS secteurs_neufs,
  -- impact BILAN mode B (_prix_terrain_local) : secteurs dont le prix SERVI (n ≥ 3) change
  count(*) FILTER (WHERE (COALESCE(neu.n,0) >= 3 OR COALESCE(anc.n,0) >= 3)
                     AND neu.med IS DISTINCT FROM anc.med) AS bilan_secteurs_prix_bouge
FROM neu FULL JOIN anc USING (secteur)"""

_DETAIL = f"""
WITH {ACTE_TERRAIN_NU_CTE},
sect AS (SELECT DISTINCT substring(dm.id_parcelle FROM 1 FOR 10) AS secteur, dm.id_mutation
         FROM dvf_mutations_parcelle dm
         WHERE dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir')),
neu AS (SELECT s.secteur, count(*) AS n,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY a.val / NULLIF(a.terr_tot, 0))
           FILTER (WHERE a.val / NULLIF(a.terr_tot, 0) BETWEEN 50 AND 20000)::int AS med
        FROM sect s JOIN acte_nu a USING (id_mutation)
        WHERE a.val > 1000 AND a.terr_tot > 0 GROUP BY s.secteur),
anc AS (SELECT secteur, n_ventes AS n, mediane_prix_m2 AS med
        FROM dvf_secteur_medianes WHERE type_bien = 'terrain')
SELECT secteur, anc.med AS med_avant, anc.n AS n_avant, neu.med AS med_apres, neu.n AS n_apres
FROM neu FULL JOIN anc USING (secteur)
WHERE (COALESCE(neu.n,0) >= 3 OR COALESCE(anc.n,0) >= 3) AND neu.med IS DISTINCT FROM anc.med
ORDER BY abs(COALESCE(neu.med,0) - COALESCE(anc.med,0)) DESC LIMIT 25"""


def main() -> None:
    with session_scope() as db:
        if db.execute(text("SELECT to_regclass('dvf_secteur_medianes')")).scalar() is None:
            print("cache dvf_secteur_medianes absent — rien à comparer")
            return
        r = db.execute(text(_NEW)).mappings().one()
        print("=== IMPACT cache dvf_secteur_medianes (type_bien='terrain') — LECTURE SEULE ===")
        print(f"secteurs en cache (ancien builder) : {r['secteurs_anciens']}")
        print(f"secteurs au nouveau builder        : {r['secteurs_neufs']}")
        print(f"secteurs dont (médiane ou n) bouge  : {r['secteurs_bouges']}")
        print(f"→ dont PRIX servi au Bilan mode B (n≥3) qui bouge : {r['bilan_secteurs_prix_bouge']}")
        print("\n=== 25 plus gros écarts de PRIX de secteur (n≥3, €/m²) ===")
        print(f"{'secteur':12} | {'avant':>10} | {'après':>10}")
        print("-" * 40)
        for d in db.execute(text(_DETAIL)).mappings().all():
            av = f"{d['med_avant']}·{d['n_avant']}" if d['med_avant'] is not None else f"—·{d['n_avant'] or 0}"
            ap = f"{d['med_apres']}·{d['n_apres']}" if d['med_apres'] is not None else f"—·{d['n_apres'] or 0}"
            print(f"{d['secteur']:12} | {av:>10} | {ap:>10}")


if __name__ == "__main__":
    main()
