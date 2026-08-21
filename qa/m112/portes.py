"""M112 — capture des PORTES (preuve : chaque invisible → un objet cliquable, jamais une impasse).

Exerce le chemin complet `answer()` (routeur réel + aiguillage) pour chaque outil invisible, les
3 guidages (carte filtrée / Surveillance / document) et les 6 exemples d'accueil, puis dump l'objet
de porte servi (porte · carte_filtre · surveillance · document · clarification). Une porte = un
module/objet paramétré, jamais une section nue.

Usage : .venv/bin/python qa/m112/portes.py   (nécessite ANTHROPIC_API_KEY + base réelle)
"""
from __future__ import annotations

import json
import sys

from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

IDU = "97415000AC0016"

# (message, attendu) — attendu = clé de porte / carte / surveillance / doc / "clarif" / "web".
CAS: list[tuple[str, str]] = [
    # ── 11 outils invisibles → porte module ──
    ("Ouvre le baromètre du foncier", "barometre"),
    # M137-Z — « où investir » et « rareté du foncier » → outil « Communes » (fusion).
    ("Où investir à La Réunion ?", "communes"),
    ("Qui construit quoi à Saint-Paul ?", "permis"),
    ("Montre-moi les promesses mortes", "promesses"),
    ("Ouvre le simulateur ZAN", "zan"),
    ("Quelle est la rareté du foncier à Cilaos ?", "communes"),
    ("Le potentiel de renouvellement urbain à Saint-Denis", "renouvellement"),
    ("Et si cette zone passait constructible ?", "simulplu"),
    # 21/08/2026 — « Quoi de neuf » (o10-bascules) retiré du produit : plus de concept-route (cf.
    # test_quoi_de_neuf_retire_plus_de_concept). Le cas « Les bascules du mois » est donc retiré d'ici.
    ("Ouvre le suivi de secteur", "o7-carnet"),
    ("Je veux scorer une adresse", "scoreur-adresse"),
    # ── guidages ──
    ("Montre les friches à Saint-Paul", "carte_filtre"),
    ("Où sont les parcelles en procédure à Saint-Denis ?", "carte_filtre"),
    ("Préviens-moi de tout nouveau permis à Saint-Paul", "surveillance"),
    (f"Édite le dossier banquier de la parcelle {IDU}", "document:dossier-banquier"),
    (f"Génère l'argumentaire de {IDU}", "document:argumentaire"),
    # ── 6 exemples d'accueil (doivent aboutir) ──
    ("Quelles parcelles appartiennent à la SIDR ?", "reponse"),
    ("Combien de parcelles à Saint-Paul ?", "reponse"),
    ("Préviens-moi de tout nouveau permis à Saint-Paul", "surveillance"),
    ("Qui est le maire de Saint-Denis ?", "reponse"),
    ("Qui gère les dossiers de financement des bailleurs sociaux à la Région ?", "reponse"),
    ("Je veux écrire au propriétaire de cette parcelle", "clarif"),
]


def _porte_de(r: dict) -> str:
    if r.get("carte_filtre"):
        return "carte_filtre"
    if r.get("surveillance"):
        return "surveillance:" + r["surveillance"]["volet"]
    if r.get("document"):
        return "document:" + r["document"]["kind"]
    if r.get("porte"):
        return r["porte"]
    if r.get("clarification"):
        return "clarif"
    return "reponse"


def _ok(attendu: str, servi: str, r: dict) -> bool:
    if attendu == "reponse":
        return servi == "reponse" or bool(r.get("text"))     # aboutit (réponse ou porte)
    if attendu == "surveillance":
        return servi.startswith("surveillance")
    if attendu == "carte_filtre":
        return servi == "carte_filtre"
    if attendu.startswith("document:"):
        return servi == attendu
    if attendu == "clarif":
        return servi == "clarif"
    return servi == attendu


def main() -> int:
    n_ok = 0
    with session_scope() as db:
        for msg, attendu in CAS:
            r = answer(db, msg)
            servi = _porte_de(r)
            ok = _ok(attendu, servi, r)
            n_ok += ok
            extra = ""
            if r.get("carte_filtre"):
                extra = f"  → {r['carte_filtre']['libelle']} {json.dumps(r['carte_filtre']['filtres'], ensure_ascii=False)}"
            elif r.get("document"):
                extra = f"  → {r['document']['idu']}"
            print(f"{'OK ' if ok else 'FAIL'} [{servi:>18}] {msg[:52]:<54}{extra}")
    print(f"\n=== BILAN PORTES M112 : {n_ok}/{len(CAS)} ===")
    return 0 if n_ok == len(CAS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
