"""COHERENCE-1 lot B — L'ÉCHANTILLON GELÉ.

120 parcelles, tirées UNE fois puis figées dans ECHANTILLON.csv : le banc rejoue toujours
les mêmes. Tirage déterministe (ORDER BY md5('coherence1'||%(strate)s||idu) — pas de random, pas de
date), stratifié selon le mandat :

  · les 7 témoins connus (EM0174, AB0134, AB1117, DE0231, BZ1065, AC0198, CK0678) —
    ⚠ AC0198 : le mandat dit « Sainte-Suzanne », la base dit commune=Sainte-Marie pour
    97418000AC0198 (le témoin historique de fiche-fix-4/5) — repris tel quel, noté ;
    « à cheval sur deux communes » : impossible par construction (l'idu porte la commune),
    remplacé par « au bord d'une limite communale » ;
  · 1 parcelle de base par commune (24) ;
  · zones U / AU ouverte (1AU) / AU fermée (2AU) / A / N, à cheval sur 2 zones ;
  · PPR interdiction (rouge) / prescription (bleue) / hors PPR ;
  · nue / bâtie / copropriété ; minuscule < 50 m² / géante > 10 ha ;
  · 50 pas géométriques ; ravine ; personne morale / physique ; filiation DFI récente.

Si une strate est vide en base, elle est dite (colonne strate absente du CSV final = 0
ligne), jamais remplacée en silence. Complément jusqu'à 120 par tirage md5 pur.

Usage : PYTHONPATH=src python scripts/coherence/echantillon.py [--regenerer]
Ne régénère PAS si ECHANTILLON.csv existe (gelé), sauf --regenerer explicite.
Lecture seule en base (statement_timeout 120 s).
"""
from __future__ import annotations

import csv
import pathlib
import sys

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-09" / "COHERENCE-1" / "ECHANTILLON.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"
RUN = "q_v11_m137"          # run servi au moment du gel (config/served_run.txt)

TEMOINS = [
    ("97411000EM0174", "temoin"), ("97415000AB0134", "temoin"),
    ("97402000AB1117", "temoin"), ("97411000DE0231", "temoin"),
    ("97411000BZ1065", "temoin"), ("97418000AC0198", "temoin"),
    ("97415000CK0678", "temoin"),
]

#: (nom de strate, nombre voulu, SQL rendant des idu triés md5) — déterministe.
STRATES: list[tuple[str, int, str]] = [
    ("commune_base", 24, """
        SELECT idu FROM (
          SELECT idu, commune, row_number() OVER (
            PARTITION BY commune ORDER BY md5('coherence1'||%(strate)s||idu)) rn
          FROM parcels) t WHERE rn=1 ORDER BY commune"""),
    ("zone_U", 5, """
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='U' ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 5"""),
    ("zone_AU_ouverte", 5, """
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='AU' AND z.zone_lib ~* '^1AU'
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 5"""),
    ("zone_AU_fermee", 5, """
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='AU' AND z.zone_lib ~* '^2AU'
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 5"""),
    ("zone_A", 5, """
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='A' ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 5"""),
    ("zone_N", 5, """
        SELECT p.idu FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
        WHERE z.zone_fam='N' ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 5"""),
    # à cheval sur 2 zones : la parcelle intersecte franchement (>5 % de sa surface)
    # 2 polygones GPU de familles différentes — échantillon restreint à 3 communes pour
    # tenir le coût, tirage md5 ensuite.
    # à cheval sur 2 zones : candidates = 4000 parcelles md5-premières de Saint-Denis
    # (coût borné), retenues si ≥ 2 familles GPU couvrent chacune > 5 % de la surface.
    ("a_cheval_2_zones", 6, """
        WITH cand AS MATERIALIZED (
          SELECT idu, geom_2975 FROM parcels WHERE commune='Saint-Denis'
          ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 4000)
        SELECT idu FROM (
          SELECT c.idu, count(DISTINCT sl.attrs->>'typezone') nz
          FROM cand c
          JOIN spatial_layers sl ON sl.kind='plu_gpu_zone'
               AND sl.geom_2975 && c.geom_2975
               AND ST_Area(ST_Intersection(sl.geom_2975, c.geom_2975))
                   > 0.05*ST_Area(c.geom_2975)
          GROUP BY c.idu HAVING count(DISTINCT sl.attrs->>'typezone') >= 2) t
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 6"""),
    ("bord_commune", 4, """
        SELECT p.idu FROM parcels p
        WHERE EXISTS (SELECT 1 FROM parcels v
                      WHERE v.commune <> p.commune
                        AND v.geom_2975 && ST_Expand(p.geom_2975, 20)
                        AND ST_DWithin(v.geom_2975, p.geom_2975, 20))
          AND p.commune IN ('Saint-Denis','Sainte-Marie','Saint-Paul','La Possession')
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 4"""),
    ("ppr_interdiction", 6, """
        SELECT p.idu FROM parcels p
        JOIN spatial_layers sl ON sl.kind='ppr' AND sl.subtype='INTERDICTION'
             AND sl.geom_2975 && p.geom_2975 AND ST_Intersects(sl.geom_2975, p.geom_2975)
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 6"""),
    ("ppr_prescription", 6, """
        SELECT p.idu FROM parcels p
        JOIN spatial_layers sl ON sl.kind='ppr' AND sl.subtype='PRESCRIPTION'
             AND sl.geom_2975 && p.geom_2975 AND ST_Intersects(sl.geom_2975, p.geom_2975)
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 6"""),
    ("copro", 6, """
        SELECT idu FROM p_model_ext_copro WHERE copro_rnic OR copro_dvf
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 6"""),
    ("batie", 6, """
        SELECT idu FROM p_model_bati WHERE emprise_bati_m2 > 20
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 6"""),
    ("nue", 6, """
        SELECT p.idu FROM parcels p
        LEFT JOIN p_model_bati b ON b.idu=p.idu
        WHERE coalesce(b.emprise_bati_m2,0)=0 AND p.surface_m2 BETWEEN 200 AND 5000
        ORDER BY md5('coherence1'||%(strate)s||p.idu) LIMIT 6"""),
    ("minuscule_50m2", 4, """
        SELECT idu FROM parcels WHERE surface_m2 < 50 AND surface_m2 > 1
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 4"""),
    ("geante_10ha", 4, """
        SELECT idu FROM parcels WHERE surface_m2 > 100000
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 4"""),
    ("cinquante_pas", 4, """
        SELECT idu FROM (
          SELECT DISTINCT p.idu FROM parcel_flags f
          JOIN parcels p ON p.id=f.parcel_id
          WHERE f.run_label=%(run)s AND f.layer_name='cinquante_pas') t
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 4"""),
    ("ravine", 4, """
        SELECT idu FROM (
          SELECT DISTINCT p.idu FROM parcel_flags f
          JOIN parcels p ON p.id=f.parcel_id
          WHERE f.run_label=%(run)s AND f.layer_name='ravine') t
        ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 4"""),
    ("personne_morale", 5, """
        SELECT idu FROM (SELECT DISTINCT idu FROM pm_proprietaires_millesimes
                         WHERE millesime=(SELECT max(millesime) FROM pm_proprietaires_millesimes)) t
        JOIN parcels USING (idu) ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 5"""),
    ("filiation_recente", 5, """
        SELECT idu_fille FROM (
          SELECT DISTINCT d.idu_fille FROM dfi_filiation d
          JOIN parcels p ON p.idu=d.idu_fille
          WHERE d.date_validation >= '2023-01-01') t
        ORDER BY md5('coherence1'||%(strate)s||idu_fille) LIMIT 5"""),
    ("complement_md5", 30, """
        SELECT idu FROM parcels ORDER BY md5('coherence1'||%(strate)s||idu) LIMIT 30"""),
]

CIBLE = 120


def tirer(conn) -> list[tuple[str, str]]:
    vus: dict[str, str] = {}
    strates_vides: list[str] = []
    for idu, s in TEMOINS:
        vus[idu] = s
    for nom, n, sql in STRATES:
        with conn.cursor() as cur:
            cur.execute(sql, {"run": RUN, "strate": nom})
            rows = [r[0] for r in cur.fetchall()]
        if not rows:
            strates_vides.append(nom)
            print(f"⚠ strate VIDE en base : {nom}")
        pris = 0
        for idu in rows:
            if len(vus) >= CIBLE:
                break
            if idu not in vus:
                vus[idu] = nom
                pris += 1
            if pris >= n and nom != "complement_md5":
                break
        print(f"strate {nom}: {pris} prises (candidates {len(rows)})")
    return list(vus.items())[:CIBLE]


def main() -> None:
    if SORTIE.exists() and "--regenerer" not in sys.argv:
        print(f"ECHANTILLON.csv existe déjà ({SORTIE}) — gelé, rien à faire "
              f"(--regenerer pour retirer).")
        return
    with psycopg.connect(DSN, options="-c statement_timeout=120000") as conn:
        ech = tirer(conn)
        # enrichissement descriptif (figé avec l'échantillon, sert de lisibilité)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.idu, p.commune, round(p.surface_m2::numeric,1),
                       z.zone_fam, z.zone_lib,
                       coalesce(b.emprise_bati_m2,0) > 20 AS batie
                FROM parcels p
                LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
                LEFT JOIN p_model_bati b ON b.idu=p.idu
                WHERE p.idu = ANY(%s)""", ([i for i, _ in ech],))
            infos = {r[0]: r[1:] for r in cur.fetchall()}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "strate", "commune", "surface_m2", "zone_fam", "zone_lib", "batie"])
        for idu, strate in sorted(ech, key=lambda x: (x[1] != "temoin", x[0])):
            i = infos.get(idu, ("?", "", "", "", ""))
            w.writerow([idu, strate, *i])
    print(f"→ {SORTIE} : {len(ech)} parcelles gelées (run {RUN})")


if __name__ == "__main__":
    main()
