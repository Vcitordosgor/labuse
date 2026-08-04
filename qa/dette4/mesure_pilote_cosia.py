"""PILOTE CoSIA 2025 (arbitrage Vic 04/08) — mesures de validation, AUCUN branchement scoring.

Vérité terrain = qa/dette4/echantillon100_classement.tsv (100 têtes classées à la main sur
ortho : 38 bâties / 41 nues / 21 douteuses). Critère « CoSIA voit du bâti » : surface de la
classe Bâtiment intersectée avec la parcelle > 20 m² (même seuil que toutes les mesures).

Rapporte : rappel sur les 38 (seuil de déploiement ≥ 90 %) ; fausses détections sur les 41
nues ; lecture des 21 douteuses ; effet estimé sur les têtes servies de Saint-Paul.
"""
import csv, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from sqlalchemy import text
from labuse.db import session_scope

TSV = os.path.join(os.path.dirname(__file__), "echantillon100_classement.tsv")
SEUIL_M2 = 20.0

rows = list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))
t0 = time.time()
with session_scope() as s:
    s.execute(text("DROP TABLE IF EXISTS qa_verite_terrain"))
    s.execute(text("CREATE TABLE qa_verite_terrain (idu varchar(14) PRIMARY KEY, classement text)"))
    for r in rows:
        s.execute(text("INSERT INTO qa_verite_terrain VALUES (:i,:c)"),
                  {"i": r["idu"], "c": r["classement"]})
    s.commit()

    res = s.execute(text(f"""
        SELECT v.classement,
               count(*) n,
               count(*) FILTER (WHERE cos.m2 > {SEUIL_M2}) cosia_voit,
               round(avg(cos.m2) FILTER (WHERE cos.m2 > {SEUIL_M2})) m2_moyen
        FROM qa_verite_terrain v
        JOIN parcels p ON p.idu = v.idu
        LEFT JOIN LATERAL (
          SELECT COALESCE(sum(ST_Area(ST_Intersection(q.geom, p.geom_2975))),0) m2
          FROM qa_cosia_bati q WHERE ST_Intersects(q.geom, p.geom_2975)) cos ON true
        GROUP BY 1 ORDER BY 1""")).all()
    print("=== validation sur la vérité terrain (seuil > 20 m² CoSIA-Bâtiment) ===")
    for cl, n, voit, m2 in res:
        print(f"  {cl:8s} : {voit}/{n} vues bâties par CoSIA (surface moyenne {m2 or 0} m²)")

    # détail des ratés sur les 38 (chaque bâtie que CoSIA ne voit PAS)
    miss = s.execute(text(f"""
        SELECT v.idu, p.commune, ST_Area(p.geom_2975)::int surf,
               round(cos.m2)::int cosia_m2
        FROM qa_verite_terrain v JOIN parcels p ON p.idu=v.idu
        LEFT JOIN LATERAL (
          SELECT COALESCE(sum(ST_Area(ST_Intersection(q.geom, p.geom_2975))),0) m2
          FROM qa_cosia_bati q WHERE ST_Intersects(q.geom, p.geom_2975)) cos ON true
        WHERE v.classement='bati' AND cos.m2 <= {SEUIL_M2} ORDER BY 1""")).all()
    print(f"=== bâties RATÉES par CoSIA ({len(miss)}) ===")
    for i, c, sf, m2 in miss:
        print(f"  {i} {c} {sf} m² (CoSIA {m2} m²)")

    # fausses détections détaillées sur les 41 nues
    fp = s.execute(text(f"""
        SELECT v.idu, p.commune, ST_Area(p.geom_2975)::int surf, round(cos.m2)::int cosia_m2
        FROM qa_verite_terrain v JOIN parcels p ON p.idu=v.idu
        LEFT JOIN LATERAL (
          SELECT COALESCE(sum(ST_Area(ST_Intersection(q.geom, p.geom_2975))),0) m2
          FROM qa_cosia_bati q WHERE ST_Intersects(q.geom, p.geom_2975)) cos ON true
        WHERE v.classement='nu' AND cos.m2 > {SEUIL_M2} ORDER BY cos.m2 DESC""")).all()
    print(f"=== fausses détections sur les nues ({len(fp)}) ===")
    for i, c, sf, m2 in fp:
        print(f"  {i} {c} {sf} m² (CoSIA {m2} m²)")

    # effet Saint-Paul : têtes servies, couche <20, sans indice → que voit CoSIA ?
    eff = s.execute(text(f"""
        WITH ind AS (
          SELECT idu FROM ortho_detections WHERE validation IS DISTINCT FROM 'faux_positif' AND idu IS NOT NULL
          UNION SELECT id_parcelle FROM dvf_mutations_parcelle WHERE surface_reelle_bati>0)
        SELECT count(*) n,
               count(*) FILTER (WHERE cos.m2 > {SEUIL_M2}) cosia_bati,
               count(*) FILTER (WHERE cos.m2 > {SEUIL_M2} AND s.tier='brulante') dont_brulantes
        FROM parcel_p_score_v2 s
        JOIN parcels p ON p.idu=s.parcelle_id AND p.commune='Saint-Paul'
        LEFT JOIN p_model_bati b ON b.idu=s.parcelle_id
        LEFT JOIN LATERAL (
          SELECT COALESCE(sum(ST_Area(ST_Intersection(q.geom, p.geom_2975))),0) m2
          FROM qa_cosia_bati q WHERE ST_Intersects(q.geom, p.geom_2975)) cos ON true
        WHERE s.run_id='q_v8_calibre' AND s.tier IN ('brulante','chaude')
          AND COALESCE(b.emprise_bati_m2,0) < 20
          AND s.parcelle_id NOT IN (SELECT idu FROM ind)""")).one()
    print(f"=== effet Saint-Paul (têtes servies couche<20 sans indice) ===")
    print(f"  {eff.n} têtes → CoSIA voit du bâti sur {eff.cosia_bati} ({100.0*eff.cosia_bati/eff.n:.0f} %), "
          f"dont {eff.dont_brulantes} brûlante(s)")
    s.execute(text("DROP TABLE qa_verite_terrain")); s.commit()
print(f"durée des mesures : {time.time()-t0:.0f}s")
