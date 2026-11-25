"""OUTIL-COMMUNES-FIX-7 LOT 1 — contrôle APRÈS reconstruction de `dvf_secteur_medianes` (effectif BÂTI).

LECTURE SEULE. Compare la sauvegarde `_bak__20261124_fix7` (bâti n_ventes = total) au cache reconstruit
(bâti n_ventes = ventes DANS les bornes). Prouve :
  · AT (Les Avirons) et AB (La Possession) maison : 8 → 7 ventes utilisées → sous le seuil 8 → via la
    fonction unique `prix_section`, aucun prix diffusé ;
  · n_ventes du cache == ventes dans les bornes pour maison/appartement (0 divergence) ;
  · liste des sections maison/appartement dont l'effectif change (et combien perdent leur prix servi) ;
  · CD terrain reste à 1 (inchangé par FIX-7, déjà corrigé au FIX-6).

Usage : PYTHONPATH=src python scripts/communes_fix7_cache_after.py"""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.dvf_secteur import prix_section, seuil_section

# Recalcul in-bornes de l'effectif BÂTI par (secteur, type) — ce que le builder corrigé doit produire.
_INBORNES = """
WITH mutations AS (
  SELECT id_mutation, max(valeur_fonciere) valeur, sum(COALESCE(surface_reelle_bati,0)) bati,
         bool_or(type_local='Maison') am, bool_or(type_local='Appartement') aa,
         bool_or(nature_mutation='Vente terrain à bâtir') vtb
  FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente','Vente terrain à bâtir') GROUP BY id_mutation),
-- MÊME filtre que le builder : VTB avec bâti exclu (NOT vtb OR bati=0 ; pour maison/appart bati>0 ⇒ NOT vtb).
typees AS (SELECT id_mutation, CASE WHEN am THEN 'maison' WHEN aa THEN 'appartement' END tb,
                  valeur/NULLIF(bati,0) r FROM mutations WHERE (am OR aa) AND valeur>1000 AND bati>0 AND NOT vtb),
sect AS (SELECT DISTINCT substring(d.id_parcelle FROM 1 FOR 10) secteur, t.* FROM typees t
         JOIN dvf_mutations_parcelle d ON d.id_mutation=t.id_mutation)
SELECT secteur, tb AS type_bien, count(*) FILTER (WHERE r BETWEEN 50 AND 20000) AS n_bornes
FROM sect GROUP BY secteur, tb"""


def main() -> None:
    with session_scope() as db:
        s = seuil_section()
        print(f"seuil de diffusion = {s}")
        for sec, nom in (("97401000AT", "Les Avirons"), ("97408000AB", "La Possession")):
            p = prix_section(db, sec, "maison")
            print(f"{nom} {sec} maison : n={p['n']} · prix_m2={p['prix_m2']} · assez={p['assez']} "
                  f"(attendu n=7, prix None)")
        cd = prix_section(db, "97415000CD", "terrain")
        print(f"CD terrain : n={cd['n']} · prix={cd['prix_m2']} (inchangé FIX-6 : n=1, pas de prix)")

        emp = db.execute(text(
            "SELECT count(*), sum(hashtext(secteur||'|'||type_bien||'|'||coalesce(n_ventes::text,'')||'|'||"
            "coalesce(mediane_valeur::text,'')||'|'||coalesce(mediane_prix_m2::text,'')||'|'||"
            "coalesce(fenetre,''))::bigint) FROM dvf_secteur_medianes")).one()
        print(f"empreinte APRÈS : lignes={emp[0]} checksum={emp[1]}")

        # cache bâti n_ventes == ventes dans les bornes ?
        propre = db.execute(text(f"""
            WITH inb AS ({_INBORNES}),
            cache AS (SELECT secteur, type_bien, n_ventes FROM dvf_secteur_medianes
                      WHERE type_bien IN ('maison','appartement'))
            SELECT count(*) FILTER (WHERE cache.n_ventes IS DISTINCT FROM inb.n_bornes) AS diff,
                   count(*) AS n FROM cache FULL JOIN inb USING (secteur, type_bien)""")).mappings().one()
        print(f"cache maison/appart n_ventes == ventes dans les bornes ? divergences={propre['diff']} "
              f"sur {propre['n']} lignes (0 attendu)")

        # ce qui change + combien perdent leur prix servi
        chg = db.execute(text(f"""
            WITH inb AS ({_INBORNES}),
            av AS (SELECT secteur, type_bien, n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes_bak__20261124_fix7
                   WHERE type_bien IN ('maison','appartement'))
            SELECT count(*) FILTER (WHERE av.n_ventes IS DISTINCT FROM inb.n_bornes) AS n_change,
                   count(*) FILTER (WHERE av.mediane_prix_m2 IS NOT NULL AND av.n_ventes >= {s}
                                      AND inb.n_bornes < {s}) AS perdent_prix
            FROM av JOIN inb USING (secteur, type_bien)""")).mappings().one()
        print(f"sections maison/appart dont l'effectif CHANGE : {chg['n_change']} ; "
              f"dont PERDENT leur prix servi (n≥{s}→<{s}) : {chg['perdent_prix']}")


if __name__ == "__main__":
    main()
