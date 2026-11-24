"""OUTIL-COMMUNES-FIX-7 LOT 3 — teste le LIEN DE SOURCE servi (carte Urbanisme) des 24 fiches communales.
Pour chaque commune, lit `plu_statut(...).source_url` (le lien affiché au promoteur) et vérifie qu'il
RÉPOND (DNS + HTTP). Liste ceux qui ne s'ouvrent pas. LECTURE SEULE (réseau sortant en HEAD).

Usage : PYTHONPATH=src python scripts/communes_fix7_liens.py"""
from __future__ import annotations

import subprocess

from sqlalchemy import text

from labuse.api.fiche_commune import plu_statut
from labuse.db import session_scope


def _http(url: str) -> str:
    try:
        out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-m", "10", "-w", "%{http_code}", "-IL", url],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "000"
    except Exception as exc:  # noqa: BLE001
        return f"ERR {exc}"


def main() -> None:
    with session_scope() as db:
        communes = [(r[0], r[1]) for r in db.execute(text(
            "SELECT insee, nom FROM communes_referentiel ORDER BY insee")).all()]
        casses = []
        for insee, nom in communes:
            s = plu_statut(db, insee, nom)
            url = s.get("source_url")
            if not url:   # RNU : pas de lien (normal)
                print(f"{insee} {nom:24} statut={s['statut']!r:34} lien=— (aucun)")
                continue
            code = _http(url)
            ok = code.startswith("2") or code.startswith("3")
            print(f"{insee} {nom:24} [{code}] {url}")
            if not ok:
                casses.append((insee, nom, url, code))
        print("\n=== LIENS QUI NE S'OUVRENT PAS ===")
        if not casses:
            print("aucun — les 24 liens répondent (ou RNU sans lien).")
        else:
            for insee, nom, url, code in casses:
                print(f"  {insee} {nom} [{code}] {url}")


if __name__ == "__main__":
    main()
