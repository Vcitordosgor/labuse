#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-10 LOT 3 — PREUVE : chaque pièce de la chronologie PLU de La Plaine-des-Palmistes
(97406) servie par le registre est OUVERTE (curl + pdftotext) et porte le jeton (date/numéro/id)
annoncé, avant d'être citée. Sortie brute : HTTP, type, jeton trouvé dans la pièce OU l'URL.

Les URL sont LUES du registre `config/veille_plu.yaml` (chronologie) via `veille_plu.entry`.

Usage :
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix10_plaine_liens.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from labuse import veille_plu

# date de la pièce → jetons attendus (dans le texte du PDF OU dans l'URL)
ATTENDU = {
    "2015-09-24": ["DCM40-240915", "20150924", "prescription"],
    "2020-02-05": ["2020AREU2", "5 février 2020", "24 septembre 2015"],
    "2022-07-13": ["13 juillet 2022", "2022ACREU2", "retir"],
    "2022-09-28": ["20220928-DCM3-28092022", "DCM3-28092022", "concertation"],  # FIX-11 LOT 2
    "2023-05-27": ["20230527-DCM04-270523", "DCM04-270523", "modification"],    # FIX-11 LOT 2 (procédure distincte)
    "2025-11-27": ["DCM32-271125", "271125", "27 novembre 2025"],
}


def _curl(url: str):
    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/"
    with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "30",
             "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
             "-e", origin, "-o", tmp.name,
             "-w", "%{http_code}\t%{url_effective}\t%{content_type}", url],
            capture_output=True, text=True)
        meta = (r.stdout or "").split("\t")
        code = meta[0] if meta else ""
        url_f = meta[1] if len(meta) > 1 else url
        ctype = meta[2] if len(meta) > 2 else ""
        head = open(tmp.name, "rb").read(5)
        if head.startswith(b"%PDF") or "pdf" in ctype.lower() or url_f.lower().endswith(".pdf"):
            txt = subprocess.run(["pdftotext", tmp.name, "-"], capture_output=True, text=True).stdout
        else:
            txt = open(tmp.name, "rb").read().decode("utf-8", "ignore")
    return code, url_f, ctype, txt


def main() -> int:
    e = veille_plu.entry("97406") or {}
    chrono = e.get("chronologie") or []
    print(f"La Plaine-des-Palmistes (97406) — {len(chrono)} pièces dans la chronologie\n")
    echecs = []
    for pc in chrono:
        d, nat, obj, url = pc.get("date"), pc.get("nature"), pc.get("objet"), pc.get("source_url", "")
        jetons = ATTENDU.get(d, [])
        print(f"{'='*86}\n{d}  [{nat}]  {obj}")
        print(f"  url : {url}")
        code, url_f, ctype, txt = _curl(url)
        hay = (txt + " " + url_f).lower()
        trouves = [j for j in jetons if j.lower() in hay]
        print(f"  HTTP {code}  [{ctype}]")
        print(f"  jetons trouvés : {trouves or '—'}")
        ok = code.startswith(("2", "3")) and bool(trouves)
        print("  → OK" if ok else "  → À VÉRIFIER")
        if not ok:
            echecs.append(d)
    print(f"\n{'='*86}")
    # DOCTRINE : des ACTES de procédure (2015/2020/2022-07/2022-09/2023 modif) + 1 MENTION d'avancement
    # (DCM32 2025). FIX-11 LOT 2 : la délib. du 28/09/2022 est le DERNIER ACTE de la révision générale.
    actes = [p for p in chrono if p.get("nature") == "acte"]
    avanc = [p for p in chrono if p.get("nature") == "avancement"]
    a2809 = any(p["date"] == "2022-09-28" and p.get("nature") == "acte" for p in chrono)
    print(f"actes : {len(actes)} · mentions d'avancement : {len(avanc)} · 28/09/2022 présent (acte) : {a2809}")
    if echecs or len(avanc) != 1 or not a2809:
        print(f"ÉCHEC : liens={echecs} actes={len(actes)} avancement={len(avanc)} 28/09/2022={a2809}")
        return 1
    print(f"SUCCÈS : {len(chrono)}/{len(chrono)} pièces ouvertes et vérifiées ; 28/09/2022 intégré ; "
          "actes distingués des mentions d'avancement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
