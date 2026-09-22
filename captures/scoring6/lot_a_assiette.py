#!/usr/bin/env python3
"""SCORING-6 lot A — preuve BOUT-EN-BOUT sur la base `labuse` (lecture seule, jetable).

Montre que le moteur résiduel calcule une capacité > 0 sur la portion U/AU d'une parcelle
dont la zone DOMINANTE est A/N (assiette clippée), là où le tout-ou-rien renvoyait
`zone_non_constructible` (SDP nulle). N'écrit rien.

    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
    PYTHONPATH=src <venv>/python captures/scoring6/lot_a_assiette.py
"""
from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.residuel import compute_residuel

# Témoins A/N 90-99 % (SCORING-5 reports/scoring-5/TEMOINS.csv) + un témoin U de contrôle.
TEMOINS = ["97402000AL0088", "97402000AB1117", "97402000AH1389"]


def main() -> None:
    with session_scope() as s:
        for idu in TEMOINS:
            row = s.execute(text("SELECT id, commune FROM parcels WHERE idu=:i"),
                            {"i": idu}).one_or_none()
            if row is None:
                print(f"{idu}: absente de la base"); continue
            print(f"=== {idu} ({row.commune}) ===")
            for mode in (False, True):
                res = parcel_faisabilite(s, row.id, assiette_clippee=mode)
                if res is None:
                    print(f"  clippee={mode}: non constructible (tout-ou-rien)"); continue
                _, f = res
                r = compute_residuel(s, row.id, faisa=res, assiette_clippee=mode)
                sdp = r.get("sdp_residuelle_m2") if r.get("disponible") else r.get("sdp_ecrite")
                print(f"  clippee={mode}: zone={f.zone} constructible={f.constructible} "
                      f"sdp_max={f.fourchette.get('surface_plancher_m2')} "
                      f"sdp_residuelle={sdp} cause={r.get('cause')}")


if __name__ == "__main__":
    main()
