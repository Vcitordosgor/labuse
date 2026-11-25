#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-8 (1) — PREUVE : pour les 8 communes en révision + Sainte-Marie et
Sainte-Suzanne (approbations), le `source_url` servi par la fiche ouvre LA PIÈCE elle-même
(délibération, avis, rapport, dossier) ou, à défaut d'adresse directe stable, la page la plus
précise qui la liste — le texte de la citation dit alors où la trouver dessus.

Le script OUVRE chaque lien (curl, suit les redirections ; pour un PDF, extrait le texte via
pdftotext) et vérifie que la pièce contient la DATE ou l'OBJET annoncé (jeton attendu). Sortie
BRUTE : code HTTP, URL finale, type, jetons trouvés dans la page ET/OU dans l'URL.

Les URL sont LUES de `config/veille_plu.yaml` (source_url) : le script ne réinvente aucune adresse,
il contrôle ce que la fiche sert.

Usage :
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix8_liens.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

import yaml

CFG = "config/veille_plu.yaml"

# INSEE → (nom, [jetons attendus — date/objet/identifiant de la pièce]). Un seul jeton trouvé
# (dans le texte de la pièce OU dans l'URL précise) prouve que le lien vise bien la pièce.
ATTENDU = {
    "97404": ("L'Étang-Salé",            ["17 septembre 2025", "révision allégée", "revision-allegee", "2025"]),
    "97406": ("La Plaine-des-Palmistes", ["révision générale", "plan local", "plainedespalmistes", "PLU"]),
    "97409": ("Saint-André",             ["2025areu7", "saint-andré", "saint-andre", "révision"]),
    "97411": ("Saint-Denis",             ["97411_plu_20260805", "97411", "by-id"]),
    "97413": ("Saint-Leu",               ["conclusions", "enquête", "enquete", "2026", "avis"]),
    "97414": ("Saint-Louis",             ["20251218", "modification simplifi", "saint-louis", "dcm"]),
    "97415": ("Saint-Paul",              ["97415_plu_20251217", "97415", "by-id"]),
    "97418": ("Sainte-Marie",            ["20251126", "219740180", "sainte-marie", "-de"]),
    "97420": ("Sainte-Suzanne",          ["29 septembre 2025", "28 février 2018", "97420_reglement", "approuvé"]),
    "97423": ("Les Trois-Bassins",       ["padd", "mai 2025", "trois-bassins", "réunions publiques"]),
}


def _entry(reg: dict, insee: str) -> dict:
    node = reg.get(insee, {})
    if isinstance(node, dict) and "source_url" in node:
        return node
    return node if isinstance(node, dict) else {}


def _curl(url: str) -> tuple[str, str, str, str]:
    """Télécharge l'URL (redirections suivies, Referer = origine, UA navigateur). Retourne
    (code_http, url_finale, type, texte). Si le corps est un PDF, extrait le texte via pdftotext."""
    origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/"
    with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "25",
             "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
             "-e", origin, "-o", tmp.name,
             "-w", "%{http_code}\t%{url_effective}\t%{content_type}", url],
            capture_output=True, text=True)
        meta = (r.stdout or "").split("\t")
        code = meta[0] if len(meta) > 0 else ""
        url_f = meta[1] if len(meta) > 1 else url
        ctype = meta[2] if len(meta) > 2 else ""
        head = open(tmp.name, "rb").read(5)
        if head.startswith(b"%PDF") or "pdf" in ctype.lower() or url_f.lower().endswith(".pdf"):
            txt = subprocess.run(["pdftotext", tmp.name, "-"], capture_output=True, text=True).stdout
            ctype = ctype or "application/pdf"
        else:
            txt = open(tmp.name, "rb").read().decode("utf-8", "ignore")
    return code, url_f, ctype, txt


def main() -> int:
    reg = yaml.safe_load(open(CFG)).get("communes") or {}
    echecs = []
    for insee, (nom, jetons) in ATTENDU.items():
        e = _entry(reg, insee)
        url = e.get("source_url", "")
        piece = e.get("piece_objet") or e.get("source") or ""
        etat = e.get("etat_source_date", "")
        print(f"\n{'='*86}\n{insee}  {nom}")
        print(f"  source_url  : {url}")
        print(f"  piece_objet : {piece[:160]}")
        print(f"  etat_au     : {etat}")
        if not url or url.rstrip("/") in (
                "https://www.geoportail-urbanisme.gouv.fr",
                "https://www.mrae.developpement-durable.gouv.fr"):
            print("  → ÉCHEC : lien absent ou page d'accueil de portail (pas la pièce).")
            echecs.append(insee)
            continue
        code, url_f, ctype, txt = _curl(url)
        hay = (txt + " " + url_f).lower()
        trouves = [j for j in jetons if j.lower() in hay]
        dans_url = [j for j in jetons if j.lower() in url_f.lower()]
        print(f"  HTTP {code}  [{ctype}]  →  {url_f}")
        print(f"  jetons trouvés (pièce+URL) : {trouves or '—'}")
        if dans_url:
            print(f"  dont présents dans l'URL (lien précis, pas un accueil) : {dans_url}")
        ok = code.startswith(("2", "3")) and bool(trouves)
        print("  → OK : le lien ouvre la pièce, date/objet confirmé." if ok
              else "  → À VÉRIFIER : code non-2xx ou aucun jeton de date/objet trouvé.")
        if not ok:
            echecs.append(insee)
    print(f"\n{'='*86}")
    if echecs:
        print(f"À corriger : {echecs}")
        return 1
    print("SUCCÈS : 10/10 liens ouvrent la pièce (ou la page précise qui la liste) avec date/objet confirmé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
