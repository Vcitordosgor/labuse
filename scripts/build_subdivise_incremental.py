"""COUCHES-TUYAU-1 retour §2 — build tuyau_subdivise UNE couche (kind stocké) à la fois.
statement_timeout 10 min POUR LE BUILD SEUL ; durée de chaque couche notée ; arrêt si > 10 min."""
import time
from sqlalchemy import text
from labuse.db import session_scope

with session_scope() as s:
    s.execute(text("DROP TABLE IF EXISTS tuyau_subdivise"))
    s.execute(text("""
        CREATE TABLE tuyau_subdivise (
            kind varchar, subtype varchar, name varchar, commune varchar,
            attrs jsonb, geom_2975 geometry)"""))
    s.commit()
    # retour §2 : SEULES les couches à GROSSES features (max sommets > 5000) sont découpées — les
    # méga-polygones (submersion, PPR, SUP, artificialisation, zonage…). Les couches à petites
    # features (bâti, voirie, points) restent sur spatial_layers (déjà < 2 s).
    kinds = [r[0] for r in s.execute(text(
        "SELECT kind, max(ST_NPoints(geom_2975)) mx FROM spatial_layers GROUP BY kind "
        "HAVING max(ST_NPoints(geom_2975)) > 5000 ORDER BY mx DESC")).all()]
    print(f"{len(kinds)} kinds à GROSSES features à découper", flush=True)
    for k in kinds:
        s.execute(text("SET statement_timeout='600s'")); s.commit()
        t0 = time.time()
        try:
            n = s.execute(text("""
                INSERT INTO tuyau_subdivise
                SELECT m.kind, m.subtype, m.name, m.commune, m.attrs, p.geom
                FROM spatial_layers m, LATERAL ST_Subdivide(m.geom_2975, 256) AS p(geom)
                WHERE m.kind = :k
                RETURNING 1"""), {"k": k}).rowcount
            s.commit()
            dt = time.time() - t0
            print(f"BUILD {k:26} {dt:7.1f}s  {n} morceaux", flush=True)
            if dt > 600:
                print(f"!! {k} a dépassé 10 min — ARRÊT", flush=True)
                break
        except Exception as e:  # noqa: BLE001
            s.rollback()
            print(f"!! {k} ÉCHEC/TIMEOUT ({type(e).__name__}) après {time.time()-t0:.1f}s — ARRÊT", flush=True)
            break
    else:
        # tous passés → index + analyse
        s.execute(text("SET statement_timeout='600s'"))
        s.execute(text("CREATE INDEX tuyau_subdivise_gix ON tuyau_subdivise USING GIST (geom_2975)"))
        s.execute(text("CREATE INDEX tuyau_subdivise_kind ON tuyau_subdivise (kind, subtype)"))
        s.execute(text("ANALYZE tuyau_subdivise"))
        s.commit()
        tot = s.execute(text("SELECT count(*) FROM tuyau_subdivise")).scalar()
        print(f"INDEX+ANALYZE ok — tuyau_subdivise : {tot} morceaux", flush=True)
    print("DONE", flush=True)
