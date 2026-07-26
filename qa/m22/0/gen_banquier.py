#!/usr/bin/env python
"""M22-0 — génère le Dossier banquier d'un IDU pour la preuve avant/après refactoring.

La synthèse IA est DÉSACTIVÉE (clé vidée) pour que le PDF soit déterministe :
le repli déterministe (concaténation des faits) est identique d'un run à l'autre.
Les tuiles IGN sont servies du cache local après le premier run.

Usage : .venv/bin/python qa/m22/0/gen_banquier.py <IDU> <sortie.pdf>
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    idu, out_path = sys.argv[1], sys.argv[2]
    import labuse.config  # noqa: F401 — charge .env une fois pour toutes
    os.environ["ANTHROPIC_API_KEY"] = ""  # repli déterministe (has_key() → False)

    from labuse.db import session_scope
    from labuse.api.banquier import _build_pdf

    with session_scope() as s:
        pdf = _build_pdf(s, idu)
    with open(out_path, "wb") as f:
        f.write(pdf)
    print(f"{out_path} : {len(pdf) // 1024} ko")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
