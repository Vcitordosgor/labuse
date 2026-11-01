#!/usr/bin/env python3
"""LOT P — Flash PDF via la fonction directe (hors paiement). Lecture seule."""
import csv, pathlib
from labuse.db import session_factory
SessionLocal = session_factory()
from labuse.flash.report import generate_flash_report
OUT = pathlib.Path("/Users/openclaw/Desktop/labuse-nu3-p/docs/audit-2026-11/nu-3/P/out")
PDFDIR = OUT / "pdf"
idus = [r["idu"] for r in csv.DictReader(open(OUT / "parcelles.csv"))]
for idu in idus:
    try:
        path = generate_flash_report(idu, order_ref="AUDIT-P", db=SessionLocal())
        data = pathlib.Path(path).read_bytes()
        (PDFDIR / f"{idu}__flash.pdf").write_bytes(data)
        print(f"  flash {idu} -> {len(data)}o  ({path})")
    except Exception as e:
        print(f"  flash {idu} -> ERR {type(e).__name__}: {str(e)[:120]}")
