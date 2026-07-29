"""A'' — contrôle de substitution v8. Recalcul À BLANC (label isolé) de 80 parcelles stratifiées,
comparaison MULTISET (ordre-indépendant) aux valeurs stockées de q_v8_calibre. Commit c867eec.
Lecture seule sur q_v8 ; écrit un label jetable q_v8_subst_probe, nettoyé à la fin."""
import subprocess
from collections import Counter
from sqlalchemy import text
from labuse.db import session_scope, engine
from labuse.cascade import evaluate_parcels
from labuse.scoring.dryrun import compute_matrice

COMMIT = subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()[:12]
PROBE = "q_v8_subst_probe"
CUT = "2026-07-29 22:08:46.154332+04"

with engine().connect() as c:
    def ids_commune(commune, n, before=None):
        q = ("SELECT d.parcel_id FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
             "WHERE d.run_label='q_v8_calibre' AND p.commune=:c ")
        if before is True:  q += f"AND d.created_at <  '{CUT}' "
        if before is False: q += f"AND d.created_at >= '{CUT}' "
        q += "ORDER BY d.created_at " + ("DESC " if before is True else "") + "LIMIT :n"
        return [r[0] for r in c.execute(text(q), {"c": commune, "n": n}).fetchall()]
    sample = (ids_commune("Saint-Paul",15) + ids_commune("La Possession",10)
              + ids_commune("L'Étang-Salé",10)
              + ids_commune("Saint-Pierre",20,before=True)      # 20 juste AVANT la coupure
              + ids_commune("Saint-Pierre",20,before=False)     # 20 juste APRÈS
              + ids_commune("Saint-Pierre",5))                  # 5 ailleurs
    sample = list(dict.fromkeys(sample))                        # dédup en gardant l'ordre
print(f"commit={COMMIT} · échantillon={len(sample)} parcelles", flush=True)

# recalcul à blanc
with session_scope() as s:
    for t in ("dryrun_cascade_results","dryrun_parcel_evaluations"):
        s.execute(text(f"DELETE FROM {t} WHERE run_label=:l"), {"l": PROBE});
    s.commit()
with session_scope() as s:
    evaluate_parcels(sample, s, persist=True, dryrun_label=PROBE); s.commit()
with session_scope() as s:
    for com in ("Saint-Paul","La Possession","L'Étang-Salé","Saint-Pierre"):
        compute_matrice(s, PROBE, com)
    s.commit()

def multiset(run, pid, c):
    rows = c.execute(text("SELECT layer_name, result, round(coalesce(weight_applied,0)::numeric,6), detail "
                          "FROM dryrun_cascade_results WHERE run_label=:r AND parcel_id=:p"),
                     {"r": run, "p": pid}).fetchall()
    return Counter((r[0], r[1], str(r[2]), r[3]) for r in rows)

def matq(run, pid, c):
    r = c.execute(text("SELECT matrice_statut, q_score, a_score FROM dryrun_parcel_evaluations "
                       "WHERE run_label=:r AND parcel_id=:p"), {"r": run, "p": pid}).first()
    return tuple(r) if r else None

div = []
with engine().connect() as c:
    for pid in sample:
        ms_ok = multiset("q_v8_calibre", pid, c) == multiset(PROBE, pid, c)
        mq_ok = matq("q_v8_calibre", pid, c) == matq(PROBE, pid, c)
        if not (ms_ok and mq_ok):
            div.append((pid, ms_ok, mq_ok, matq("q_v8_calibre",pid,c), matq(PROBE,pid,c)))
print(f"\n=== VERDICT : comparées={len(sample)} · DIVERGENTES={len(div)} ===")
for pid, ms, mq, a, b in div[:20]:
    print(f"  DIVERGENT pid={pid} multiset_ok={ms} matrice_ok={mq} stored={a} probe={b}")
print("IDENTIQUE" if not div else "DIVERGENT")

with engine().begin() as c:
    for t in ("dryrun_cascade_results","dryrun_parcel_evaluations"):
        c.execute(text(f"DELETE FROM {t} WHERE run_label=:l"), {"l": PROBE})
print("label jetable nettoyé. FINI")
