"""OUTIL-COMMUNES-FIX-5 (3c) — contrôle APRÈS reconstruction de `dvf_secteur_medianes`.

LECTURE SEULE. Compare la sauvegarde `dvf_secteur_medianes_bak__20261124` (cache AVANT, contaminé) au
cache reconstruit, et PROUVE que le cache reconstruit est propre :
  · liste des secteurs TERRAIN qui changent, dont le sous-ensemble servi au Bilan mode B (n ≥ 3) = 60 ;
  · section IZ de Saint-Denis = 284 €/m² · 18 ventes (était 272 · 19) ;
  · 0 secteur TERRAIN du cache ne diffère de la qualification unique `ACTE_TERRAIN_NU_CTE` recalculée à
    la volée → le cache est bâti SANS acte avec local déclaré ni à cheval sur deux communes ;
  · secteurs qui perdent TOUTES leurs ventes (tous n ≤ 2 → sans effet Bilan, seuil n ≥ 3).

Usage : PYTHONPATH=src python scripts/communes_fix5_cache_after.py"""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE

# Recalcul TERRAIN par secteur depuis la qualification UNIQUE (identique au 2ᵉ INSERT du builder).
_CTE_SECTEUR = f"""
WITH {ACTE_TERRAIN_NU_CTE},
sect AS (SELECT DISTINCT substring(dm.id_parcelle FROM 1 FOR 10) AS secteur, dm.id_mutation
         FROM dvf_mutations_parcelle dm
         WHERE dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir'))
SELECT s.secteur, count(*) AS n,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY a.val / NULLIF(a.terr_tot, 0))
         FILTER (WHERE a.val / NULLIF(a.terr_tot, 0) BETWEEN 50 AND 20000)::int AS med
FROM sect s JOIN acte_nu a USING (id_mutation)
WHERE a.val > 1000 AND a.terr_tot > 0
GROUP BY s.secteur"""


def main() -> None:
    with session_scope() as db:
        # (c) section IZ Saint-Denis
        iz = db.execute(text("SELECT n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes "
                             "WHERE secteur='97411000IZ' AND type_bien='terrain'")).first()
        print(f"=== Section IZ Saint-Denis (terrain) : {iz[1]} €/m² · {iz[0]} ventes  (attendu 284 · 18) ===")

        # cache TERRAIN propre ? Comparaison cache reconstruit vs CTE recalculé à la volée.
        propre = db.execute(text(f"""
            WITH neu AS ({_CTE_SECTEUR}),
            cache AS (SELECT secteur, n_ventes AS n, mediane_prix_m2 AS med
                      FROM dvf_secteur_medianes WHERE type_bien='terrain')
            SELECT count(*) FILTER (WHERE neu.n IS DISTINCT FROM cache.n
                                       OR neu.med IS DISTINCT FROM cache.med) AS diff,
                   count(*) FILTER (WHERE cache.secteur IS NOT NULL) AS cache_terrain,
                   count(*) FILTER (WHERE neu.secteur IS NOT NULL)   AS cte_terrain
            FROM neu FULL JOIN cache USING (secteur)""")).mappings().one()
        print(f"=== Cache TERRAIN == qualification unique (ACTE_TERRAIN_NU_CTE) ? ===")
        print(f"secteurs cache terrain = {propre['cache_terrain']} · CTE = {propre['cte_terrain']} · "
              f"divergences = {propre['diff']}  (0 = cache bâti SANS local ni multi-communes)")

        # (c) 60 secteurs Bilan + per-secteur delta
        rows = db.execute(text("""
            WITH av AS (SELECT secteur, n_ventes AS n, mediane_prix_m2 AS med
                        FROM dvf_secteur_medianes_bak__20261124 WHERE type_bien='terrain'),
                 ap AS (SELECT secteur, n_ventes AS n, mediane_prix_m2 AS med
                        FROM dvf_secteur_medianes WHERE type_bien='terrain')
            SELECT secteur, av.med AS med_av, av.n AS n_av, ap.med AS med_ap, ap.n AS n_ap
            FROM av FULL JOIN ap USING (secteur)
            WHERE (COALESCE(av.n,0)>=3 OR COALESCE(ap.n,0)>=3) AND av.med IS DISTINCT FROM ap.med
            ORDER BY abs(COALESCE(ap.med,0)-COALESCE(av.med,0)) DESC""")).mappings().all()
        print(f"\n=== (c) {len(rows)} secteurs dont le PRIX servi au Bilan mode B (n≥3) bouge (attendu 60) ===")
        ecarts = sorted(abs((r['med_ap'] or 0) - (r['med_av'] or 0)) for r in rows)
        mediane_ecart = ecarts[len(ecarts)//2] if ecarts else 0
        print(f"écart médian {mediane_ecart} €/m² · écart max {ecarts[-1] if ecarts else 0} €/m²")
        print(f"{'secteur':12} | {'avant':>10} | {'après':>10} | {'Δ €/m²':>7}")
        print("-" * 48)
        for r in rows:
            av = f"{r['med_av']}·{r['n_av']}" if r['med_av'] is not None else f"—·{r['n_av'] or 0}"
            ap = f"{r['med_ap']}·{r['n_ap']}" if r['med_ap'] is not None else f"—·{r['n_ap'] or 0}"
            d = (r['med_ap'] or 0) - (r['med_av'] or 0)
            print(f"{r['secteur']:12} | {av:>10} | {ap:>10} | {d:>+7}")

        # secteurs qui perdent toutes leurs ventes terrain
        perdus = db.execute(text("""
            SELECT b.secteur, b.n_ventes AS n_av
            FROM dvf_secteur_medianes_bak__20261124 b
            LEFT JOIN dvf_secteur_medianes a ON a.secteur=b.secteur AND a.type_bien='terrain'
            WHERE b.type_bien='terrain' AND a.secteur IS NULL
            ORDER BY b.n_ventes DESC""")).mappings().all()
        print(f"\n=== secteurs TERRAIN qui perdent TOUTES leurs ventes : {len(perdus)} "
              f"(n max avant = {max([p['n_av'] for p in perdus], default=0)} ; <3 → sans effet Bilan) ===")
        for p in perdus:
            print(f"  {p['secteur']} (n_avant={p['n_av']})")


if __name__ == "__main__":
    main()
