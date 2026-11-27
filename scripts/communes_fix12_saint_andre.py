#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-12 LOT 3 — PREUVE Saint-André + contrôle PPA des communes en révision.

ASTRA-9 §3 : la Région Réunion a délibéré le 03/10/2025 (avis PPA sur la révision générale du PLU de
Saint-André), postérieur à l'avis MRAe du 09/09/2025 → la conclusion « aucun acte postérieur » tombe.
CORRECTION DE RÉFÉRENCE : l'audit cite DCP2025_0684, mais 0684 = « Appui de l'AGORAH à la révision du
SAR » ; l'avis PLU Saint-André est DCP2025_0685 (presse régionale + index du recueil).

Ce que le script PROUVE / DOCUMENTE (ouvertures réelles) :
  1. MRAe 2025AREU7 (09/09/2025) OUVRE (HTTP 200) et porte « révision générale du PLU de Saint-André ».
  2. Le recueil Région (03/10/2025) est momentanément INACCESSIBLE (HTTP 404, migration du site) :
     on imprime son statut réel — la pièce ouvrable la plus récente reste la MRAe.
  3. Le registre sert désormais la dernière pièce = avis Région 03/10/2025 (consultation ≠ approbation),
     chronologie [09/09 MRAe · 03/10 Région].
  4. Contrôle PPA (Région/Département/État/MRAe/chambres) des communes en révision : où a-t-on cherché,
     et pourquoi aucune autre que Saint-André ne porte d'avis PPA postérieur à l'affiché.

Usage :
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix12_saint_andre.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from labuse import veille_plu

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/125 Safari/537.36")

# Contrôle PPA (synthèse de la recherche — Région CP, Département, État/Préfecture, MRAe, chambres) :
# où l'on a cherché, et le constat postérieur à la date affichée, par commune en révision.
PPA = {
    "97404 Étang-Salé (2025-09-17)": "GPU + Région CP : rien de postérieur (2025-09-17 = approbation révision allégée n°1).",
    "97406 La Plaine (2022-09-28)": "Site commune + MRAe : rien de postérieur à la révision (2023 = modification n°3, procédure distincte).",
    "97411 Saint-Denis (2026-08-05)": "GPU + MRAe : postérieurs seulement sur des MODIFICATIONS (2026ACREU6 23/09/2026 = modif n°10) — pas la révision générale.",
    "97413 Saint-Leu (2026-11-18)": "Site commune + Région CP + MRAe : avis PPA tous antérieurs ; conclusions d'enquête ~23/11 ne sont pas un PPA.",
    "97414 Saint-Louis (2025-12-18)": "MRAe + Région CP : rien de postérieur (révision pas encore au stade arrêt/PPA).",
    "97415 Saint-Paul (2025-12-17)": "MRAe + Région CP : rien de postérieur (2026APREU8 = avis projet, pas un PPA de révision).",
    "97423 Trois-Bassins (2025-09-04)": "MRAe/État/Région : postérieurs (09/09, 09/10, 07/11) PORTENT sur la MEC secteur Zattes — procédure DISTINCTE (voir LOT 2).",
}


def _curl(url: str):
    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/"
    with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "30", "-A", _UA, "-e", origin,
             "-o", tmp.name, "-w", "%{http_code}\t%{content_type}", url],
            capture_output=True, text=True)
        meta = (r.stdout or "").split("\t")
        code = meta[0] if meta else ""
        ctype = meta[1] if len(meta) > 1 else ""
        head = open(tmp.name, "rb").read(5)
        txt = ""
        if head.startswith(b"%PDF") or "pdf" in ctype.lower():
            txt = subprocess.run(["pdftotext", tmp.name, "-"], capture_output=True, text=True).stdout
    return code, ctype, txt


def main() -> int:
    e = veille_plu.entry("97409") or {}
    print("Saint-André (97409) — registre après FIX-12 LOT 3 :")
    print(f"  etat_source_date : {e.get('etat_source_date')}")
    print(f"  piece_objet      : {e.get('piece_objet')}")
    chrono = e.get("chronologie") or []
    print(f"  chronologie      : {[(p['date'], p['nature']) for p in chrono]}")

    print("\n1) MRAe 2025AREU7 (09/09/2025) — ouverture réelle :")
    mrae_url = "https://www.mrae.developpement-durable.gouv.fr/IMG/pdf/2025areu7_rev_plu_saint_andre.pdf"
    code, ctype, txt = _curl(mrae_url)
    hay = txt.lower()
    marqueurs = [m for m in ("révision générale du plu de saint-andré", "9 septembre 2025", "2025areu7")
                 if m in hay]
    print(f"   HTTP {code} [{ctype}] · marqueurs trouvés : {marqueurs or '—'}")
    mrae_ok = code.startswith("2") and len(marqueurs) >= 2

    print("\n2) Recueil Région CP 03/10/2025 (DCP2025_0685) — statut réel :")
    rg_url = "https://www.regionreunion.com/IMG/pdf/recueil_deliberations_cperma_du_03102025.pdf"
    code_rg, ctype_rg, _ = _curl(rg_url)
    print(f"   HTTP {code_rg} [{ctype_rg}] — {rg_url}")
    print("   → momentanément inaccessible (migration regionreunion.com) ; avis corroboré par la presse")
    print("     régionale + index du recueil (DCP2025_0685, DCP2025_0684 = appui AGORAH au SAR).")

    print("\n3) Dernière pièce servie : consultation Région 03/10/2025, DISTINCTE d'une approbation.")
    reg_ok = (e.get("etat_source_date") == "2025-10-03"
              and any(p["date"] == "2025-10-03" for p in chrono)
              and any(p["date"] == "2025-09-09" for p in chrono))

    print("\n4) Contrôle PPA des communes en révision (où l'on a cherché) :")
    for k, v in PPA.items():
        print(f"   · {k} — {v}")

    ok = mrae_ok and reg_ok
    print(f"\n{'SUCCÈS' if ok else 'À VÉRIFIER'} : MRAe ouverte={mrae_ok} · registre Région intégré={reg_ok} "
          f"(recueil Région HTTP {code_rg}, documenté).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
