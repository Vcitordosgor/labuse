#!/usr/bin/env python
"""M22-B — génère les lettres de vérification de zonage de preuve (2 parcelles réelles :
une simple, une avec servitudes multiples). Usage :
    LABUSE_DATABASE_URL=... .venv/bin/python qa/m22/b/gen_lettres.py
"""
from __future__ import annotations

import labuse.config  # noqa: F401 — .env

from labuse.db import session_scope
from labuse.api.lettre_zonage import _build_pdf

CAS = [
    ("97415000BV1193", "qa/m22/b/lettre_BV1193_simple.pdf"),        # U6c 100 %, cas simple
    ("97415000DK1169", "qa/m22/b/lettre_DK1169_servitudes.pdf"),    # AU2h+N, 10 risques, ABF
]

with session_scope() as s:
    for idu, out in CAS:
        pdf = _build_pdf(s, idu)
        with open(out, "wb") as f:
            f.write(pdf)
        print(f"{out} : {len(pdf) // 1024} ko")
