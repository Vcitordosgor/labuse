#!/usr/bin/env python3
"""G1 — sonde base pour `parcels-ile`.

Décode le protobuf MVT (sans dépendance : le format Tile est trivial) et rapporte,
pour chaque tuile île demandée : nom(s) de layer, extent, nb de features.
Appelle EXACTEMENT `tiles._parcel_tile_bytes` (le seul point qui construit les octets)
→ ce que la sonde lit est ce que l'API sert.

Le bug G1 : `ORDER BY` placé après le 1er argument de ST_AsMVT fait avaler
`'parcels', extent, 'geom'` comme clés de tri → la tuile sort nommée `default`,
extent 4096. La correction remet `ORDER BY` en fin d'arguments.

Usage : PYTHONPATH=src .venv/bin/python docs/audit-2026-10/G1/mvt_probe.py
"""
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _varint(buf, i):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, i
        shift += 7


def _skip(buf, i, wt):
    if wt == 0:
        _, i = _varint(buf, i)
    elif wt == 1:
        i += 8
    elif wt == 2:
        ln, i = _varint(buf, i)
        i += ln
    elif wt == 5:
        i += 4
    return i


def decode_layers(buf):
    """Retourne [{name, extent, features}] pour chaque layer du Tile MVT."""
    layers = []
    i, n = 0, len(buf)
    while i < n:
        key, i = _varint(buf, i)
        field, wt = key >> 3, key & 7
        if field == 3 and wt == 2:  # Tile.layers (repeated Layer)
            ln, i = _varint(buf, i)
            layers.append(_decode_layer(buf[i:i + ln]))
            i += ln
        else:
            i = _skip(buf, i, wt)
    return layers


def _decode_layer(buf):
    name, extent, feats = None, 4096, 0  # extent défaut MVT = 4096
    i, n = 0, len(buf)
    while i < n:
        key, i = _varint(buf, i)
        field, wt = key >> 3, key & 7
        if field == 1 and wt == 2:      # name
            ln, i = _varint(buf, i)
            name = buf[i:i + ln].decode("utf-8", "replace")
            i += ln
        elif field == 2 and wt == 2:    # feature
            ln, i = _varint(buf, i)
            feats += 1
            i += ln
        elif field == 5 and wt == 0:    # extent
            extent, i = _varint(buf, i)
        else:
            i = _skip(buf, i, wt)
    return {"name": name, "extent": extent, "features": feats}


# Tuiles île denses (features réelles), choisies par balayage de l'étendue de mvt_parcels.
# z≤11 : extent attendu 1024 (palier de simplification) ; z≥12 : extent 4096 (brut).
ILE_TILES = [(9, 335, 286), (10, 670, 572), (11, 1339, 1147),
             (12, 2679, 2295), (13, 5357, 4591)]


def main():
    url = os.environ.get(
        "LABUSE_DATABASE_URL",
        "postgresql+psycopg://openclaw@localhost:5432/labuse",
    )
    from labuse.api import tiles

    eng = create_engine(url)
    with Session(eng) as db:
        print(f"{'z/x/y':<14}{'layer':<10}{'extent':>8}{'features':>10}")
        print("-" * 42)
        for z, x, y in ILE_TILES:
            body = tiles._parcel_tile_bytes(db, z, x, y)
            layers = decode_layers(body) if body else []
            if not layers:
                print(f"{z}/{x}/{y:<10}  (tuile vide — {len(body)} o)")
                continue
            for lyr in layers:
                print(f"{z}/{x}/{y:<10}{lyr['name'] or '∅':<10}"
                      f"{lyr['extent']:>8}{lyr['features']:>10}  ({len(body)} o)")


if __name__ == "__main__":
    sys.exit(main())
