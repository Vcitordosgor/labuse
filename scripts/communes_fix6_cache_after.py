"""OUTIL-COMMUNES-FIX-6 LOT 1 — contrôle APRÈS reconstruction de `dvf_secteur_medianes`.

LECTURE SEULE. Compare la sauvegarde `dvf_secteur_medianes_bak__20261124_fix6` (cache AVANT : n_ventes =
TOTAL des actes) au cache reconstruit (n_ventes = ventes DANS les bornes de prix, celles qui fondent la
médiane). Prouve :
  · 97411000IZ = 284 €/m² · 14 ventes (était 18) ; 97415000CD = 1 vente → sous le seuil → aucun prix ;
  · n_ventes du cache == ventes dans les bornes recalculées par la qualification unique (0 divergence) ;
  · nombre de sections qui PERDENT leur prix servi (med non nulle, n≥8 total → n_bornes<8) = 76 ;
  · liste des plus gros écarts d'effectif.

Usage : PYTHONPATH=src python scripts/communes_fix6_cache_after.py"""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.dvf_mediane import SEUIL_N
from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE

_CTE_NB = f"""
WITH {ACTE_TERRAIN_NU_CTE},
sect AS (SELECT DISTINCT substring(dm.id_parcelle FROM 1 FOR 10) AS secteur, dm.id_mutation
         FROM dvf_mutations_parcelle dm WHERE dm.nature_mutation IN ('Vente','Vente terrain à bâtir')),
nb AS (SELECT s.secteur,
         count(*) FILTER (WHERE a.val/NULLIF(a.terr_tot,0) BETWEEN 50 AND 20000) AS n_bornes
       FROM sect s JOIN acte_nu a USING (id_mutation)
       WHERE a.val>1000 AND a.terr_tot>0 GROUP BY s.secteur)"""


def main() -> None:
    with session_scope() as db:
        iz = db.execute(text("SELECT n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes "
                             "WHERE secteur='97411000IZ' AND type_bien='terrain'")).first()
        cd = db.execute(text("SELECT n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes "
                             "WHERE secteur='97415000CD' AND type_bien='terrain'")).first()
        print(f"=== 97411000IZ terrain : {iz[1]} €/m² · {iz[0]} ventes  (attendu 284 · 14) ===")
        print(f"=== 97415000CD terrain : n={cd[0]} · med={cd[1]} ; servi par Comparer ? "
              f"{'OUI' if cd[0] >= SEUIL_N else 'NON'} (seuil {SEUIL_N} → attendu NON, 1 vente) ===")

        # empreinte APRÈS
        emp = db.execute(text(
            "SELECT count(*), sum(hashtext(secteur||'|'||type_bien||'|'||coalesce(n_ventes::text,'')||'|'||"
            "coalesce(mediane_valeur::text,'')||'|'||coalesce(mediane_prix_m2::text,'')||'|'||"
            "coalesce(fenetre,''))::bigint) FROM dvf_secteur_medianes")).one()
        print(f"=== empreinte APRÈS : lignes={emp[0]} checksum={emp[1]} ===")

        # cache terrain n_ventes == ventes dans les bornes (qualification unique)
        propre = db.execute(text(f"""
            {_CTE_NB},
            cache AS (SELECT secteur, n_ventes FROM dvf_secteur_medianes WHERE type_bien='terrain')
            SELECT count(*) FILTER (WHERE cache.n_ventes IS DISTINCT FROM nb.n_bornes) AS diff,
                   count(*) AS n_sections
            FROM cache FULL JOIN nb USING (secteur)""")).mappings().one()
        print(f"=== cache n_ventes == ventes dans les bornes ? divergences={propre['diff']} "
              f"sur {propre['n_sections']} sections (0 = effectif = ventes utilisées) ===")

        # sections qui PERDENT leur prix servi (med non nulle & n>=8 avant → n_bornes<8)
        perdus = db.execute(text(f"""
            {_CTE_NB},
            av AS (SELECT secteur, n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes_bak__20261124_fix6
                   WHERE type_bien='terrain')
            SELECT count(*) AS n FROM av JOIN nb USING (secteur)
            WHERE av.mediane_prix_m2 IS NOT NULL AND av.n_ventes >= {SEUIL_N} AND nb.n_bornes < {SEUIL_N}
        """)).scalar()
        print(f"=== sections qui PERDENT leur prix servi (n≥{SEUIL_N} → <{SEUIL_N}) : {perdus} (attendu 76) ===")

        # top écarts d'effectif
        print("\n=== 20 plus gros écarts d'effectif (n_ventes avant → après) ===")
        rows = db.execute(text("""
            SELECT a.secteur, a.n_ventes AS n_av, b.n_ventes AS n_ap, b.mediane_prix_m2 AS med
            FROM dvf_secteur_medianes_bak__20261124_fix6 a
            JOIN dvf_secteur_medianes b ON b.secteur=a.secteur AND b.type_bien='terrain'
            WHERE a.type_bien='terrain' AND a.n_ventes <> b.n_ventes
            ORDER BY abs(a.n_ventes-b.n_ventes) DESC LIMIT 20""")).mappings().all()
        for r in rows:
            print(f"  {r['secteur']} : {r['n_av']} → {r['n_ap']}  (med {r['med']})")


if __name__ == "__main__":
    main()
