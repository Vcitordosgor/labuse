"""⚠ OBSOLÈTE (OUTIL-COMMUNES-FIX-5 §1) — ce script applique une borne `BETWEEN 50 AND 4000 €/m²` que la
fonction SERVIE (`ligne2_terrain_zone`) N'APPLIQUE PAS : ses colonnes « après » divergent de l'écran.
Utiliser `scripts/communes_fix5_terrain_preuve.py` (appelle la fonction servie, sans borne). Conservé
uniquement pour la preuve « 0 local / 0 multi-commune » (partie 1), qui reste valable.

OUTIL-COMMUNES-FIX-4 LOT 1 — PREUVES du terrain nu (script committé, sortie brute collée au CR).

1. PREUVE UNIQUE : 0 acte servi par la qualification unique (`ACTE_TERRAIN_NU_CTE`) ne porte de local
   déclaré ni ne touche plus d'une commune — donc 0 dans CHAQUE lecteur (tous embarquent ce CTE).
2. AVANT/APRÈS : médianes €/m² du terrain nu par zone U et AU, pour les 24 communes, avec effectifs —
   ancienne qualification (bâti=0 seul, surface = plus grande ligne) vs la nouvelle (bâti=0 + aucun
   local + une seule commune + surface = somme des subdivisions distinctes).

Usage : PYTHONPATH=src python scripts/communes_fix4_terrain_preuve.py
Lecture seule. Lit `labuse` (LABUSE_DATABASE_URL)."""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE

# Ancienne qualification (telle que servie par main add341ebb) : bâti=0 sur l'acte, surface = plus
# grande ligne par (mutation, parcelle), AUCUN filtre local ni multi-communes.
ACTE_NU_AVANT = """acte_nu AS (
  SELECT id_mutation, sum(terr_p) AS terr_tot, max(val) AS val, max(mill) AS mill,
         min(d0) AS d0, max(d1) AS d1
  FROM (SELECT id_mutation, id_parcelle,
               max(COALESCE(surface_reelle_bati, 0)) AS bati_p,
               max(COALESCE(surface_terrain, 0))     AS terr_p,
               max(valeur_fonciere) AS val, max(millesime) AS mill,
               min(date_mutation) AS d0, max(date_mutation) AS d1
        FROM dvf_mutations_parcelle
        WHERE nature_mutation IN ('Vente', 'Vente terrain à bâtir')
        GROUP BY id_mutation, id_parcelle) pp
  GROUP BY id_mutation HAVING sum(bati_p) = 0 AND sum(terr_p) > 0)"""

_ZONE_SQL = """
WITH {cte},
zm AS (SELECT m.id_mutation, bool_or(z.zone_fam='U') has_u, bool_or(z.zone_fam='AU') has_au
       FROM dvf_mutations_parcelle m JOIN parcel_zone_plu z ON z.idu=m.id_parcelle AND z.zone_fam IN ('U','AU')
       WHERE m.code_commune=:insee AND m.nature_mutation IN ('Vente','Vente terrain à bâtir')
       GROUP BY m.id_mutation),
tot AS (SELECT a.val, a.terr_tot, zm.has_u, zm.has_au FROM acte_nu a JOIN zm USING(id_mutation))
SELECT
  round(percentile_cont(0.5) WITHIN GROUP (ORDER BY val/NULLIF(terr_tot,0))
        FILTER (WHERE has_u AND val/NULLIF(terr_tot,0) BETWEEN 50 AND 4000))::int AS med_u,
  count(*) FILTER (WHERE has_u AND val/NULLIF(terr_tot,0) BETWEEN 50 AND 4000) AS n_u,
  round(percentile_cont(0.5) WITHIN GROUP (ORDER BY val/NULLIF(terr_tot,0))
        FILTER (WHERE has_au AND val/NULLIF(terr_tot,0) BETWEEN 50 AND 4000))::int AS med_au,
  count(*) FILTER (WHERE has_au AND val/NULLIF(terr_tot,0) BETWEEN 50 AND 4000) AS n_au
FROM tot"""


def main() -> None:
    with session_scope() as db:
        # ── 1. PREUVE UNIQUE ────────────────────────────────────────────────────────────
        contamine = db.execute(text(
            "WITH " + ACTE_TERRAIN_NU_CTE + " "
            "SELECT "
            "  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM dvf_mutations_parcelle d "
            "     WHERE d.id_mutation=a.id_mutation AND d.type_local IS NOT NULL)) AS avec_local, "
            "  count(*) FILTER (WHERE (SELECT count(DISTINCT d.code_commune) FROM dvf_mutations_parcelle d "
            "     WHERE d.id_mutation=a.id_mutation) > 1) AS multi_communes, "
            "  count(*) AS total_actes "
            "FROM acte_nu a")).mappings().one()
        print("=== PREUVE UNIQUE (ACTE_TERRAIN_NU_CTE, lu par tous les lecteurs) ===")
        print(f"actes terrain nu qualifiés : {contamine['total_actes']}")
        print(f"  dont avec un local déclaré   : {contamine['avec_local']}   (attendu 0)")
        print(f"  dont multi-communes          : {contamine['multi_communes']}   (attendu 0)")
        print("Lecteurs embarquant ce CTE (donc 0 dans chacun) :")
        print("  P1 _median_terrain · P2 ligne2_terrain_zone (tableau/fiche/Comparer/Assemblage) ·")
        print("  P3 série baromètre · P4 comparateur_terrain (fiche parcelle/Estimer) · P5 Radar île ·")
        print("  zone.py prix_par_type_zone (Étude de zone) · _median_terrain_commune (bloc commune) ·")
        print("  banc_estimer · dvf_secteur_medianes terrain (fiche §8/Comparatif)")

        # ── 2. AVANT / APRÈS par commune ────────────────────────────────────────────────
        communes = [(r[0], r[1]) for r in db.execute(text(
            "SELECT insee, nom FROM communes_referentiel ORDER BY nom")).all()]
        print("\n=== AVANT / APRÈS — terrain nu U et AU, 24 communes (médiane €/m² · n) ===")
        print(f"{'Commune':24} | {'U avant':>12} | {'U après':>12} | {'AU avant':>12} | {'AU après':>12}")
        print("-" * 86)
        for insee, nom in communes:
            av = db.execute(text(_ZONE_SQL.format(cte=ACTE_NU_AVANT)), {"insee": insee}).mappings().one()
            ap = db.execute(text(_ZONE_SQL.format(cte=ACTE_TERRAIN_NU_CTE)), {"insee": insee}).mappings().one()

            def _c(m, n):
                return f"{m}·{n}" if m is not None else f"—·{n}"
            flag = ""
            if av["med_u"] != ap["med_u"] or av["n_u"] != ap["n_u"] \
                    or av["med_au"] != ap["med_au"] or av["n_au"] != ap["n_au"]:
                flag = "  ←bouge"
            print(f"{nom:24} | {_c(av['med_u'], av['n_u']):>12} | {_c(ap['med_u'], ap['n_u']):>12} | "
                  f"{_c(av['med_au'], av['n_au']):>12} | {_c(ap['med_au'], ap['n_au']):>12}{flag}")


if __name__ == "__main__":
    main()
