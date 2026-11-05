#!/usr/bin/env python
"""NU5-A — sélection des 20 parcelles-pièges.

Lecture seule. Pour chaque critère-piège, on trouve des candidates par requête SQL
sur la base locale `labuse` (q_v20), on affiche l'idu + les attributs qui prouvent le
piège, puis on fige un choix (≥ 10 communes distinctes).

Usage : PYTHONPATH=src /Users/openclaw/Desktop/labuse/.venv/bin/python
        docs/audit-2026-11/nu-5/A/harnais/select_parcelles.py
"""
from __future__ import annotations
import json
from sqlalchemy import text
from labuse.db import engine

# Requêtes candidates : chaque entrée renvoie (idu, commune, + preuve). LIMIT court.
Q = {
 "nue_zone_U": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib, r.taux_emprise_pct, r.sdp_residuelle_m2
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   JOIN parcel_residuel r ON r.parcel_id=p.id
   WHERE z.zone_fam='U' AND COALESCE(r.taux_emprise_pct,0)=0
     AND p.surface_m2 BETWEEN 300 AND 3000 AND r.sdp_residuelle_m2>0
   ORDER BY p.surface_m2 DESC LIMIT 5""",

 "batie_saturee": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib, r.taux_emprise_pct, r.sdp_residuelle_m2, r.capacite_estimee
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   JOIN parcel_residuel r ON r.parcel_id=p.id
   WHERE z.zone_fam='U' AND r.taux_emprise_pct>=70 AND COALESCE(r.sdp_residuelle_m2,0)=0
   ORDER BY r.taux_emprise_pct DESC LIMIT 5""",

 "batie_reste_constructible": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib, r.taux_emprise_pct, r.sdp_residuelle_m2
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   JOIN parcel_residuel r ON r.parcel_id=p.id
   WHERE z.zone_fam='U' AND r.taux_emprise_pct BETWEEN 10 AND 55 AND r.sdp_residuelle_m2>150
   ORDER BY r.sdp_residuelle_m2 DESC LIMIT 5""",

 "pente_forte": """
   SELECT p.idu, p.commune, p.surface_m2, t.pente_moy_deg, t.pente_max_deg, t.flag_terrassement_lourd
   FROM parcels p JOIN parcel_terrain t ON t.idu=p.idu
   WHERE t.pente_moy_deg>=30 AND p.surface_m2 BETWEEN 400 AND 5000
   ORDER BY t.pente_moy_deg DESC LIMIT 5""",

 # 2 zones PLU : géométrie de la parcelle qui recoupe >=2 polygones plu_gpu_zone distincts (par libellé)
 "deux_zones_plu": """
   SELECT p.idu, p.commune, p.surface_m2, count(DISTINCT sl.name) nz,
          string_agg(DISTINCT sl.name, ' | ') zones
   FROM parcels p JOIN spatial_layers sl ON sl.kind='plu_gpu_zone'
        AND ST_Intersects(p.geom_2975, sl.geom_2975)
        AND ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975)) > 20
   WHERE p.surface_m2 BETWEEN 400 AND 8000
   GROUP BY p.idu, p.commune, p.surface_m2 HAVING count(DISTINCT sl.name)>=2
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 # 2 communes : aucune parcelle cadastrale ne CHEVAUCHE une limite communale (mono-commune par
 # construction). On retient donc la parcelle la plus COLLÉE à la limite d'une autre commune
 # (bord de territoire) — le piège teste l'attribution à la limite.
 "deux_communes": """
   WITH com AS (SELECT commune, ST_Transform(geom_3857,2975) g2975 FROM mvt_communes)
   SELECT p.idu, p.commune, p.surface_m2, com.commune autre,
          round(ST_Distance(p.geom_2975, com.g2975)::numeric,2) dist_m
   FROM com JOIN parcels p
     ON com.commune <> p.commune
    AND ST_DWithin(p.geom_2975, com.g2975, 0.5)
   WHERE p.surface_m2 BETWEEN 300 AND 10000
   ORDER BY dist_m ASC LIMIT 6""",

 "ppr_rouge_partielle": """
   WITH inter AS (
     SELECT p.id, p.idu, p.commune, p.surface_m2, ST_Area(p.geom_2975) pa,
            ST_Union(ST_Intersection(p.geom_2975, sl.geom_2975)) ug
     FROM parcels p JOIN spatial_layers sl
       ON sl.kind='ppr' AND labuse_ppr_couleur(sl.subtype, sl.attrs)='rouge'
      AND ST_Intersects(p.geom_2975, sl.geom_2975)
     WHERE p.surface_m2 BETWEEN 300 AND 10000
     GROUP BY p.id, p.idu, p.commune, p.surface_m2)
   SELECT idu, commune, surface_m2, round(100*ST_Area(ug)/pa)::int pct
   FROM inter WHERE round(100*ST_Area(ug)/pa)::int BETWEEN 10 AND 85
   ORDER BY surface_m2 DESC LIMIT 6""",

 "ppr_bleue": """
   WITH inter AS (
     SELECT p.id, p.idu, p.commune, p.surface_m2, ST_Area(p.geom_2975) pa,
            ST_Union(ST_Intersection(p.geom_2975, sl.geom_2975)) ug
     FROM parcels p JOIN spatial_layers sl
       ON sl.kind='ppr' AND labuse_ppr_couleur(sl.subtype, sl.attrs)='bleu'
      AND ST_Intersects(p.geom_2975, sl.geom_2975)
     WHERE p.surface_m2 BETWEEN 300 AND 10000
     GROUP BY p.id, p.idu, p.commune, p.surface_m2)
   SELECT idu, commune, surface_m2, round(100*ST_Area(ug)/pa)::int pct
   FROM inter WHERE round(100*ST_Area(ug)/pa)::int>=25
   ORDER BY round(100*ST_Area(ug)/pa)::int DESC LIMIT 6""",

 "minuscule": """
   SELECT p.idu, p.commune, p.surface_m2, p.contenance_m2, z.zone_fam
   FROM parcels p LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
   WHERE COALESCE(p.contenance_m2, p.surface_m2) < 100 AND COALESCE(p.contenance_m2,p.surface_m2) > 5
   ORDER BY COALESCE(p.contenance_m2,p.surface_m2) ASC LIMIT 6""",

 "geante": """
   SELECT p.idu, p.commune, p.surface_m2, p.contenance_m2, z.zone_fam
   FROM parcels p LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
   WHERE p.surface_m2 > 50000
   ORDER BY p.surface_m2 DESC LIMIT 8""",

 "copropriete": """
   SELECT p.idu, p.commune, p.surface_m2, co.nom_usage, co.nb_lots_total
   FROM rnic_coproprietes co JOIN parcels p ON p.idu=co.parcelle_idu
   WHERE co.parcelle_idu IS NOT NULL AND co.nb_lots_total>0
   ORDER BY co.nb_lots_total DESC LIMIT 8""",

 "littoral": """
   SELECT p.idu, p.commune, p.surface_m2
   FROM parcels p JOIN spatial_layers sl
     ON sl.kind='cinquante_pas' AND ST_Intersects(p.geom_2975, sl.geom_2975)
   WHERE p.surface_m2 BETWEEN 200 AND 20000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 # AU ouverte : zone AU non déclassée fermée, libellé 1AU/AUe
 "au_ouverte": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib, a.classe
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   LEFT JOIN parcel_au_statut a ON a.idu=p.idu
   WHERE z.zone_fam='AU' AND (z.zone_lib ILIKE '1AU%' OR z.zone_lib ILIKE 'AUe%' OR z.zone_lib ILIKE 'AU%')
     AND COALESCE(a.classe,'') NOT IN ('declasse_au_fermee','declasse_au_statut_inconnu','au_sous_plancher')
     AND p.surface_m2 BETWEEN 500 AND 20000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 "au_fermee": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib, a.classe
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   JOIN parcel_au_statut a ON a.idu=p.idu
   WHERE z.zone_fam='AU' AND a.classe='declasse_au_fermee'
     AND p.surface_m2 BETWEEN 500 AND 20000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 "zone_A": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   WHERE z.zone_fam='A' AND p.surface_m2 BETWEEN 1000 AND 30000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 "zone_N": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_lib
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   WHERE z.zone_fam='N' AND p.surface_m2 BETWEEN 1000 AND 30000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 "sans_adresse": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_fam
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   LEFT JOIN parcel_adresse a ON a.idu=p.idu
   WHERE a.idu IS NULL AND z.zone_fam='U' AND p.surface_m2 BETWEEN 300 AND 3000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 # sans propriétaire connu : aucun enregistrement personne morale (donc particulier/inconnu, non nominatif)
 "sans_proprio_connu": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_fam
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   LEFT JOIN parcelle_personne_morale pm ON pm.idu=p.idu
   WHERE pm.idu IS NULL AND z.zone_fam='U' AND p.surface_m2 BETWEEN 300 AND 2000
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 # sans aucune vente dans le voisinage : pas de mutation DVF rattachée + secteur rural
 "sans_vente_voisinage": """
   SELECT p.idu, p.commune, p.surface_m2, z.zone_fam
   FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
   LEFT JOIN dvf_mutations_parcelle dm ON dm.idu=p.idu
   WHERE dm.idu IS NULL AND z.zone_fam IN ('A','N')
     AND p.surface_m2 BETWEEN 1000 AND 20000
     AND p.commune IN ('Cilaos','Salazie','Sainte-Rose','Saint-Philippe')
   ORDER BY p.surface_m2 DESC LIMIT 6""",

 "monument_historique": """
   SELECT p.idu, p.commune, p.surface_m2, ci.subtype
   FROM parcels p JOIN parcel_couche_intersection ci ON ci.parcel_id=p.id
   WHERE ci.kind='sup' AND ci.subtype='ac1' AND p.surface_m2 BETWEEN 200 AND 10000
   ORDER BY p.surface_m2 DESC LIMIT 6""",
}

def main():
    out = {}
    eng = engine()
    for name, q in Q.items():
        with eng.connect() as c:          # une connexion/transaction par requête (isolation)
            try:
                c.execute(text("SET statement_timeout='120s'"))
                rows = [dict(r._mapping) for r in c.execute(text(q)).fetchall()]
            except Exception as e:
                rows = [{"ERREUR": str(e)[:200]}]
        out[name] = rows
        print(f"\n### {name} ({len(rows)} candidats)")
        for r in rows:
            print("   ", {k: (round(v,1) if isinstance(v,float) else v) for k,v in r.items()})
    with open("docs/audit-2026-11/nu-5/A/preuves/candidats.json","w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("\n-> preuves/candidats.json écrit")

if __name__ == "__main__":
    main()
