"""Lot 1 — matérialise p_model_* sur la base réelle puis imprime les stats de contrôle.

Usage : LABUSE_DATABASE_URL=… python scripts/m3-p-model/build_dataset.py
"""
from __future__ import annotations

import time

from sqlalchemy import text

from labuse.db import session_scope
from labuse.scoring.p_model import sql as psql


def main() -> None:
    steps = [
        ("frame", psql.build_frame),
        ("mutations", psql.build_mutations),
        ("permits", psql.build_permits),
        ("bati (BD TOPO × parcelles, long)", psql.build_bati),
        ("static", psql.build_static),
        ("dataset", psql.build_dataset),
    ]
    with session_scope() as session:
        for name, fn in steps:
            t0 = time.time()
            fn(session)
            session.commit()
            print(f"[{time.strftime('%H:%M:%S')}] {name} : {time.time() - t0:.0f}s", flush=True)

        print("\n=== Contrôles ===")
        for q, lbl in [
            ("SELECT count(*) FROM p_model_frame", "parcelles frame"),
            ("SELECT count(*) FROM p_model_dataset", "lignes dataset"),
            ("SELECT annee, count(*) n, sum(label) pos, avg(label::float) taux "
             "FROM p_model_dataset GROUP BY 1 ORDER BY 1", "par année"),
            ("SELECT annee, count(*) FILTER (WHERE label IS NULL) FROM p_model_dataset "
             "GROUP BY 1 ORDER BY 1", "labels NULL"),
            ("SELECT zone_plu, count(*) FROM p_model_dataset WHERE annee=2025 "
             "GROUP BY 1 ORDER BY 2 DESC", "zones PLU (2025)"),
            ("SELECT tenure_bin, count(*), avg(label::float) FROM p_model_dataset "
             "WHERE annee IN (2023,2024) GROUP BY 1 ORDER BY 1", "tenure (23-24)"),
            ("SELECT permis_bin, count(*), avg(label::float) FROM p_model_dataset "
             "WHERE annee IN (2023,2024) GROUP BY 1 ORDER BY 1", "permis (23-24)"),
            ("SELECT count(*) FROM p_model_dataset WHERE annee=2026", "lignes scoring 2026"),
        ]:
            with session.connection().engine.connect() as c:
                rows = c.execute(text(q)).all()
            print(f"-- {lbl}")
            for r in rows:
                print("   ", tuple(r))


if __name__ == "__main__":
    main()
