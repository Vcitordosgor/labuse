"""M50 Lot A — RE-MESURE de la reconstructibilité des motifs (AUDIT5 rejoué sur l'état courant).

Pour CHAQUE tier servi (run q_v8_calibre), le motif exact d'écartement/déclassement se
reconstruit-il par requête depuis les tables persistées ? Compte total vs reconstructible.
Lecture seule. Sort qa/m50/reconstructibilite.csv.

Sources de motif (constaté sur pièces) :
  ecartee                    → dryrun_cascade_results HARD_EXCLUDE (étage 0)  OU  q_score (matrice Q<50)
  declasse_bati_sature       → parcel_filtre_bati.motif (idu)
  declasse_non_constructible → parcel_constructibilite.motif (parcel_id)
  declasse_zone_fermee       → parcel_constructibilite.motif (parcel_id)
  declasse_au_fermee/inconnu → parcel_au_statut.motif|classe (idu)
  declasse_bati_revele       → parcel_bati_revele.motif (idu)
  brulante/chaude/a_creuser/reserve_fonciere → PAR PARAMÈTRES (rang + contrib_d persistés +
      cutoffs p_score_v2_runs.params) ; registre = served_run_exceptions.motif
"""
from __future__ import annotations
import csv
from labuse.db import make_engine
from sqlalchemy import text

RUN = "q_v8_calibre"
eng = make_engine()

# tier -> (total_sql, reconstructible_sql) — chaque count filtré sur le run servi
Q = {
    "ecartee": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='ecartee'",
        """SELECT count(*) FROM parcel_p_score_v2 s WHERE s.run_id=:r AND s.tier='ecartee'
           AND (EXISTS (SELECT 1 FROM dryrun_cascade_results c JOIN parcels p ON p.id=c.parcel_id
                        WHERE p.idu=s.parcelle_id AND c.run_label=:r AND c.result='HARD_EXCLUDE')
                OR EXISTS (SELECT 1 FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
                           WHERE p.idu=s.parcelle_id AND d.run_label=:r AND d.q_score IS NOT NULL))"""),
    "declasse_bati_sature": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_bati_sature'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcel_filtre_bati fb ON fb.idu=s.parcelle_id
           WHERE s.run_id=:r AND s.tier='declasse_bati_sature' AND fb.motif IS NOT NULL"""),
    "declasse_non_constructible": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_non_constructible'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id
           JOIN parcel_constructibilite pc ON pc.parcel_id=p.id
           WHERE s.run_id=:r AND s.tier='declasse_non_constructible' AND pc.motif IS NOT NULL"""),
    "declasse_zone_fermee": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_zone_fermee'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id
           JOIN parcel_constructibilite pc ON pc.parcel_id=p.id
           WHERE s.run_id=:r AND s.tier='declasse_zone_fermee' AND pc.motif IS NOT NULL"""),
    "declasse_au_fermee": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_au_fermee'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcel_au_statut au ON au.idu=s.parcelle_id
           WHERE s.run_id=:r AND s.tier='declasse_au_fermee' AND (au.motif IS NOT NULL OR au.classe IS NOT NULL)"""),
    "declasse_au_statut_inconnu": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_au_statut_inconnu'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcel_au_statut au ON au.idu=s.parcelle_id
           WHERE s.run_id=:r AND s.tier='declasse_au_statut_inconnu' AND (au.motif IS NOT NULL OR au.classe IS NOT NULL)"""),
    "declasse_bati_revele": (
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='declasse_bati_revele'",
        """SELECT count(*) FROM parcel_p_score_v2 s JOIN parcel_bati_revele br ON br.idu=s.parcelle_id
           WHERE s.run_id=:r AND s.tier='declasse_bati_revele' AND br.motif IS NOT NULL"""),
}
# tiers servables : reconstructibles PAR PARAMÈTRES (rang + contrib_d non nuls + cutoffs persistés)
SERVABLES = ("brulante", "chaude", "a_creuser", "reserve_fonciere")

def scalar(c, sql):
    return int(c.execute(text(sql), {"r": RUN}).scalar() or 0)

def main():
    rows = []
    with eng.connect() as c:
        for tier, (tot_sql, rec_sql) in Q.items():
            tot, rec = scalar(c, tot_sql), scalar(c, rec_sql)
            rows.append({"tier": tier, "total": tot, "reconstructible": rec,
                         "manquants": tot - rec,
                         "pct": round(100 * rec / tot, 3) if tot else 100.0,
                         "source_motif": "table motif dédiée / cascade"})
        for tier in SERVABLES:
            tot = scalar(c, f"SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='{tier}'")
            # reconstructible = par PARAMÈTRES (rang+contrib_d présents) OU par le FLAG COPRO
            # (une copro n'est jamais classée en tête → rang NULL → tier par défaut ; motif = copro,
            # AUDIT5 « trou n°2 »). Les deux chemins couvrent 100 % de la famille.
            rec = scalar(c, f"""SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r AND tier='{tier}'
                                AND ((rang IS NOT NULL AND contrib_d IS NOT NULL) OR copro=true)""")
            rows.append({"tier": tier, "total": tot, "reconstructible": rec,
                         "manquants": tot - rec,
                         "pct": round(100 * rec / tot, 3) if tot else 100.0,
                         "source_motif": "paramètres du run (rang+contrib_d+cutoffs) OU flag copro"})
    tot_all = sum(r["total"] for r in rows)
    rec_all = sum(r["reconstructible"] for r in rows)
    with open("qa/m50/reconstructibilite.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "total", "reconstructible", "manquants", "pct", "source_motif"])
        w.writeheader(); w.writerows(rows)
        w.writerow({"tier": "TOTAL", "total": tot_all, "reconstructible": rec_all,
                    "manquants": tot_all - rec_all, "pct": round(100 * rec_all / tot_all, 3),
                    "source_motif": f"{len(rows)} familles"})
    print(f"=== RE-MESURE reconstructibilité (run {RUN}, {tot_all} parcelles) ===")
    for r in rows:
        flag = "" if r["manquants"] == 0 else f"  ⚠ {r['manquants']} MANQUANTS"
        print(f"  {r['tier']:28s} {r['reconstructible']:>7}/{r['total']:<7} = {r['pct']:6.2f} %{flag}")
    print(f"  {'TOTAL':28s} {rec_all:>7}/{tot_all:<7} = {100*rec_all/tot_all:.3f} %")

if __name__ == "__main__":
    main()
