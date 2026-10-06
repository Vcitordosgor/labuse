"""Temps par BLOC du builder de fiche, sur UNE session chaude (= worker prod en régime).
Lecture seule."""
from __future__ import annotations
import time
from sqlalchemy import event, text
from labuse.db import engine, session_factory
from labuse import runs
from labuse.api import app as A

_SQL = {"t": 0.0, "n": 0}


@event.listens_for(engine(), "before_cursor_execute")
def _b(conn, cur, stmt, p, ctx, em):
    ctx._t0 = time.perf_counter()


@event.listens_for(engine(), "after_cursor_execute")
def _a(conn, cur, stmt, p, ctx, em):
    _SQL["t"] += time.perf_counter() - ctx._t0
    _SQL["n"] += 1


def main():
    run = runs.current()
    s = session_factory()()
    s.connection()
    cr = A._cascade_run(s, run)
    idus = s.execute(text(
        """SELECT p.idu FROM parcels p JOIN dryrun_parcel_evaluations d
           ON d.parcel_id=p.id AND d.run_label=:r WHERE p.commune IS NOT NULL
           ORDER BY md5(p.idu) LIMIT 11"""), {"r": cr}).scalars().all()
    # warm
    A.parcel_fiche(idus[0], source=run, db=s, request=None, trace=0)

    import statistics as st
    per = {}
    for idu in idus[1:11]:
        # chronométrer chaque appel coûteux individuellement, session chaude
        import labuse.api.fiche_blocs3 as B
        probes = [
            ("analyse_labuse(score_labuse)", lambda: s.execute(text(
                "SELECT bande, signal_niveau, contributions, cause, non_calculable, sdp_residuelle_m2 "
                "FROM score_labuse WHERE run_label=:r AND idu=:idu"), {"r": run, "idu": idu}).first()),
            ("_cascade_run", lambda: A._cascade_run(s, run)),
            ("pm_voisines", lambda: B.pm_voisines(s, idu)),
            ("trafic_rn", lambda: B.trafic_rn(s, idu)),
            ("_aleas_block", lambda: A._aleas_block(s, idu, [])),
            ("_proximites_block", lambda: A._proximites_block(s, idu)),
            ("_proximites_equip", lambda: A._proximites_equipements_block(s, idu)),
            ("_anc_block", lambda: A._anc_block(s, idu)),
            ("_secteur_opport", lambda: A._secteur_opportunites(s, idu)),
            ("_data_sources_fiche", lambda: A._data_sources_fiche(s, s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar(), cr)),
        ]
        for name, fn in probes:
            _SQL["t"] = 0.0; _SQL["n"] = 0
            t = time.perf_counter()
            fn()
            dt = time.perf_counter() - t
            per.setdefault(name, []).append((dt, _SQL["n"]))
    print(f"run={run} cascade={cr}")
    print(f"{'bloc':28} {'médiane ms':>10} {'max ms':>8} {'nq':>4}")
    for name, vals in per.items():
        meds = st.median(v[0] for v in vals) * 1e3
        mx = max(v[0] for v in vals) * 1e3
        nq = st.median(v[1] for v in vals)
        print(f"{name:28} {meds:10.1f} {mx:8.1f} {nq:4.0f}")
    s.close()


if __name__ == "__main__":
    main()
