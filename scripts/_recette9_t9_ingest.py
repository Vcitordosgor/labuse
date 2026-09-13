"""RECETTE-9 T9 — ingestion BORNÉE du LiDAR HD (faîtage/égout) dans `batiment_hauteur_lidar`.
C'est la seule ingestion autorisée du mandat (T9). Idempotent par idu. Chaque parcelle = ~2 fetch
WMS (~1 s). PAS l'île en aveugle : on passe une LISTE d'idus (ou un échantillon d'une commune).
Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python scripts/_recette9_t9_ingest.py <idu|--commune Nom [n]>
"""
import sys
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.hauteur_lidar import ingest_hauteur_lidar


def main(argv):
    with session_scope() as db:
        if argv and argv[0] == "--commune":
            commune = argv[1]; n = int(argv[2]) if len(argv) > 2 else 20
            idus = [r[0] for r in db.execute(text(
                """SELECT DISTINCT p.idu FROM parcels p JOIN spatial_layers b
                     ON b.kind='batiment' AND ST_Intersects(b.geom_2975,p.geom_2975)
                   WHERE p.commune=:c AND NULLIF(b.attrs->>'hauteur','') IS NOT NULL
                     AND ST_Area(b.geom_2975) BETWEEN 60 AND 600
                   ORDER BY p.idu LIMIT :n"""), {"c": commune, "n": n})]
        else:
            idus = argv or ["97411000EL0157"]
        for idu in idus:
            m = ingest_hauteur_lidar(db, idu)
            ok = m and m.get("faitage_m") is not None
            print(f"{idu}: " + (f"faîtage={m['faitage_m']} égout={m.get('egout_m')} "
                  f"BDTOPO={m.get('hauteur_bdtopo_m')}" if ok else f"non mesuré ({m})"))
        db.commit()


if __name__ == "__main__":
    main(sys.argv[1:])
