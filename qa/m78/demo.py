"""M78 · STOP Phase 1 — DÉMO 10 messages en API brute (pas d'UI). 5 réponses · 5 refus.

Le ton d'un refus est plus difficile à réussir qu'une réponse (arbitrage Vic) — autant de refus que
de réponses. Chaque sortie montre : le texte servi au client, l'intention routée, l'outil appelé (ou
le motif de refus), la porte proposée. Modèle réel (Sonnet partout).

Usage : .venv/bin/python qa/m78/demo.py
"""
from __future__ import annotations

from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

IDU = "97414000CV0907"
IDU_PP = "97416000DE1763"

REPONSES = [
    "Combien de parcelles d'au moins 5000 m² à Saint-Paul ?",
    "Quelles parcelles possède la Société Immobilière du Département de la Réunion ?",
    "Combien de temps un dossier prend à être instruit par la mairie de Saint-Benoît ?",
    "Quel est le taux de logement social à Saint-Benoît ?",
    f"Je veux calculer la charge foncière que je peux supporter sur {IDU}.",
]
REFUS = [
    f"Qui est le propriétaire de la parcelle {IDU_PP} ?",
    f"Combien vaudra la parcelle {IDU} dans 10 ans ?",
    f"Cette parcelle {IDU} est-elle divisible ?",
    "Quelle est la météo demain à Saint-Denis ?",
    "Recommande-moi un bon restaurant créole à Saint-Pierre.",
]


def _show(db, titre, questions):
    print(f"\n{'='*78}\n{titre}\n{'='*78}")
    for q in questions:
        r = answer(db, q)
        meta = f"intent={r.get('intent')}"
        if r.get("tool"):
            meta += f" · outil={r['tool']}"
        if r.get("refus"):
            meta += f" · refus={r['refus']}"
        if r.get("porte"):
            meta += f" · porte={r['porte']}"
        if r.get("partiel"):
            meta += " · couverture PARTIELLE"
        print(f"\n▸ {q}")
        print(f"  « {r.get('text','')} »")
        print(f"  [{meta}]")


def main() -> int:
    with session_scope() as db:
        _show(db, "5 RÉPONSES", REPONSES)
        _show(db, "5 REFUS (le ton se gagne ici)", REFUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
