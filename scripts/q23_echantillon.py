"""DEPLOY-GROUPE-3 — échantillon des parcelles A–D (q_v20) → bande 0 (q_v23), vérifié contre la FICHE.

Lecture seule. `compute_residuel` LIVE = ce que montre la fiche (batch≡fiche, invariant RESIDUEL-1).
"""
from __future__ import annotations
from labuse.db import session_scope
from sqlalchemy import text
from labuse.faisabilite.residuel import compute_residuel

COHORT = """
SELECT p.id pid, s23.idu, p.commune, ST_Area(p.geom_2975) aire,
       s20.bande b20, s20.sdp_residuelle_m2 r20,
       r18.sdp_residuelle_m2 r18, r18.sdp_max_m2 c18, r18.sdp_existante_m2 e18,
       r18.cause cause18, r18.assiette_source a18
FROM score_labuse s23
JOIN score_labuse s20 ON s20.idu=s23.idu AND s20.run_label='q_v20'
JOIN parcels p ON p.idu=s23.idu
LEFT JOIN parcel_residuel_runs r18 ON r18.parcel_id=p.id AND r18.run_seq=18
WHERE s23.run_label='q_v23' AND s23.bande='0' AND s20.bande IN ('A','B','C','D')
{extra}
ORDER BY md5(s23.idu) LIMIT {lim}
"""


def _g(d, *ks):
    for k in ks:
        if isinstance(d, dict) and d.get(k) is not None:
            return d[k]
    return None


def show(session, extra, lim, titre):
    print(f"\n=== {titre} ===")
    rs = list(session.execute(text(COHORT.replace("{extra}", extra).replace("{lim}", str(lim)))))
    n_match = 0
    for r in rs:
        live = compute_residuel(session, r.pid) or {}
        lr = _g(live, "sdp_residuelle_m2"); lc = _g(live, "sdp_max_m2"); lcause = _g(live, "cause")
        match = round(lr or 0) == round(r.r18 or 0) and (lcause or None) == (r.cause18 or None)
        n_match += int(match)
        print(f"{r.idu} {(r.commune or '')[:11]:11} aire={round(r.aire):>6} | AVANT q20 {r.b20} R={round(r.r20 or 0):>6}"
              f" | APRÈS q23 R={round(r.r18 or 0):>5} C={round(r.c18 or 0):>6} E={round(r.e18 or 0):>6}"
              f" cause={r.cause18 or '-'} ass={r.a18 or '-'}"
              f" | FICHE R={round(lr or 0):>5} C={round(lc or 0):>6} cause={lcause or '-'} | batch==fiche:{match}")
    print(f"-- batch==fiche : {n_match}/{len(rs)}")


def main():
    with session_scope() as s:
        show(s, "", 20, "20 AU HASARD (cohorte A–D → bande 0)")
        show(s, "AND r18.cause='terrain_exigu' AND ST_Area(p.geom_2975)>1000", 8,
             "terrain_exigu >1000 m² (famille DISCUTABLE)")


if __name__ == "__main__":
    main()
