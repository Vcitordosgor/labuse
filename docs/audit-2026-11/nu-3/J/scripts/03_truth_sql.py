#!/usr/bin/env python3
"""AUDIT-NU-3-J — la vérité : chaque fait recalculé indépendamment depuis les tables
sources (requête à moi), sans passer par le code applicatif. Sortie truth.json par idu.
Lecture seule (SELECT only). SRID 2975 pour les aires."""
import json, os, sys
import psycopg
from psycopg.rows import dict_row
PG = "postgresql://openclaw@localhost:5432/labuse"
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")
RUN = "q_v20"

def main():
    sample = json.load(open(os.path.join(OUT, "sample120.json")))
    idus = [r["idu"] for r in sample]
    truth = {}
    with psycopg.connect(PG, row_factory=dict_row) as cx:
        for idu in idus:
            t = {"idu": idu}
            # surface : aire géométrique (dessin) vs contenance (acte)
            r = cx.execute("""select contenance_m2,
                       round(ST_Area(geom_2975)::numeric,1)::float as aire_dessin,
                       id from parcels where idu=%s""", (idu,)).fetchone()
            t["contenance_m2"] = r["contenance_m2"] if r else None
            t["aire_dessin_m2"] = r["aire_dessin"] if r else None
            pid = r["id"] if r else None
            # zone
            z = cx.execute("select zone_lib, zone_fam from parcel_zone_plu where idu=%s", (idu,)).fetchone()
            t["zone_lib"] = z["zone_lib"] if z else None
            t["zone_fam"] = z["zone_fam"] if z else None
            # pente
            p = cx.execute("select pente_moy_deg, pente_max_deg, flag_terrassement_lourd from parcel_terrain where idu=%s",(idu,)).fetchone()
            t["pente_moy_deg"] = round(p["pente_moy_deg"],1) if p and p["pente_moy_deg"] is not None else None
            t["pente_max_deg"] = round(p["pente_max_deg"],1) if p and p["pente_max_deg"] is not None else None
            # aléas Géorisques : décomposition complète par risque × niveau (vs "best only" servi)
            al = cx.execute("""
              with par as (select geom_2975 g, ST_Area(geom_2975) a from parcels where idu=%s)
              select sl.attrs->>'risque' as risque, sl.attrs->>'niveau' as niveau,
                     round((100*sum(ST_Area(ST_Intersection(par.g, sl.geom_2975)))
                            / nullif(min(par.a),0))::numeric,1)::float as pct
              from par
              join spatial_layers sl on sl.kind='georisque_alea' and sl.geom_2975 is not null
                   and par.g && sl.geom_2975 and ST_Intersects(par.g, sl.geom_2975)
              group by 1,2 order by 1,2""", (idu,)).fetchall()
            t["aleas_detail"] = [{"risque":a["risque"],"niveau":a["niveau"],"pct":a["pct"]} for a in al]
            # agrégats : par risque, total exposé et niveau max
            byr = {}
            for a in al:
                byr.setdefault(a["risque"], {"total":0.0,"niveaux":{}})
                byr[a["risque"]]["total"] += (a["pct"] or 0)
                byr[a["risque"]]["niveaux"][a["niveau"]] = a["pct"]
            t["aleas_par_risque"] = {k:{"total_pct":round(v["total"],1),"niveaux":v["niveaux"]} for k,v in byr.items()}
            t["n_risques"] = len(byr)
            # PPR rouge (interdiction) : part de la parcelle
            ppr = cx.execute("""
              with par as (select geom_2975 g, ST_Area(geom_2975) a from parcels where idu=%s)
              select coalesce(round((100*sum(ST_Area(ST_Intersection(par.g, sl.geom_2975)))
                            / nullif(min(par.a),0))::numeric,1),0)::float as pct_rouge
              from par
              join spatial_layers sl on sl.kind='ppr' and sl.subtype='INTERDICTION' and sl.geom_2975 is not null
                   and par.g && sl.geom_2975 and ST_Intersects(par.g, sl.geom_2975)""", (idu,)).fetchone()
            t["ppr_rouge_pct"] = ppr["pct_rouge"] if ppr else 0.0
            # dernière vente DVF (table parcelle brute) — la vraie dernière mutation
            dv = cx.execute("""select date_mutation::text as d, nature_mutation as nat, valeur_fonciere as val,
                       surface_reelle_bati as sb, surface_terrain as st, type_local
                       from dvf_mutations_parcelle where id_parcelle=%s
                       order by date_mutation desc, id desc limit 1""", (idu,)).fetchone()
            t["derniere_vente"] = (dict(dv) if dv else None)
            # palier / classement (run servi)
            sl2 = cx.execute("select bande, score, non_calculable, cause from score_labuse where idu=%s and run_label=%s",(idu,RUN)).fetchone()
            t["labuse_bande"] = sl2["bande"] if sl2 else None
            t["labuse_non_calculable"] = sl2["non_calculable"] if sl2 else None
            sv = cx.execute("select tier, copro, rang, percentile from parcel_p_score_v2 where parcelle_id=%s and run_id=%s",(idu,RUN)).fetchone()
            t["v2_tier"] = sv["tier"] if sv else None
            t["v2_copro"] = sv["copro"] if sv else None
            t["v2_rang"] = sv["rang"] if sv else None
            # copropriété RNIC : la parcelle est-elle rattachée à une copro RNIC ?
            rn = cx.execute("""select count(*) n from rnic_coproprietes
                       where parcelle_idu=%s or (idu_codes is not null and idu_codes ? %s)""",(idu,idu)).fetchone()
            t["rnic_present"] = (rn["n"] > 0) if rn else False
            # SDP : les deux tables servies
            sj = cx.execute("select sdp_residuelle_m2 from score_labuse where idu=%s and run_label=%s",(idu,RUN)).fetchone()
            t["sdp_labuse"] = (round(float(sj["sdp_residuelle_m2"]),1) if sj and sj["sdp_residuelle_m2"] is not None else None)
            pr = cx.execute("select sdp_residuelle_m2 from parcel_residuel where parcel_id=%s",(pid,)).fetchone() if pid else None
            t["sdp_residuel_live"] = (round(float(pr["sdp_residuelle_m2"]),1) if pr and pr["sdp_residuelle_m2"] is not None else None)
            # propriétaire personne morale
            pm = cx.execute("select denomination, siren, groupe, groupe_label from parcelle_personne_morale where idu=%s",(idu,)).fetchone()
            t["pm"] = (dict(pm) if pm else None)
            truth[idu] = t
    json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), ensure_ascii=False, indent=1)
    print(f"vérité recalculée pour {len(truth)} parcelles -> truth.json")
    # quelques invariants de synthèse
    masq = sum(1 for t in truth.values() if any(v["total_pct"]<99.5 and max(v["niveaux"].values() or [0]) < v["total_pct"]-0.5 for v in t["aleas_par_risque"].values()) )
    print("parcelles où un risque a plusieurs niveaux (le servi n'en garde qu'un) :", masq)

if __name__ == "__main__":
    main()
