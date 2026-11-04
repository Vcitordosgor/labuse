"""JOHN-TAYLOR-2 — l'accueil qui PARLE. Calculé à l'ouverture de la page (aucun appel modèle) : combien
de choses attendent une décision de Vic, une phrase d'accueil honnête, et trois suggestions utiles.

« Attend ta décision » = des signaux que John lit déjà (incidents ouverts, propositions de carnet, sources
de classe B avec une nouvelle version à valider). 100 % lecture, best-effort : une lecture qui rate ne
compte pour rien (jamais de fausse alerte, jamais de faux « tout tourne »).
"""
from __future__ import annotations

from . import carnet as _carnet
from . import contexte as _ctx

_MOTS = {1: "Une", 2: "Deux", 3: "Trois", 4: "Quatre", 5: "Cinq", 6: "Six", 7: "Sept", 8: "Huit"}

SUGGESTIONS = ["Tout est à jour ?", "Qu'est-ce qui a changé depuis hier ?", "Où en est q_v21 ?"]


def _attentes(db) -> list[dict]:
    """La liste honnête de ce qui attend un geste de Vic (dédoublonnée par type, bornée au raisonnable)."""
    items: list[dict] = []
    try:
        for i in (_ctx.incidents(db).get("ouverts") or []):
            titre = i.get("titre") or i.get("resume") or i.get("libelle") or i.get("cle") or "incident ouvert"
            items.append({"type": "incident", "titre": str(titre)})
    except Exception:  # noqa: BLE001
        pass
    try:
        for p in _carnet.proposees(db):
            items.append({"type": "carnet", "titre": p.get("titre") or "proposition de carnet"})
    except Exception:  # noqa: BLE001
        pass
    try:
        for s in (_ctx.sources(db).get("nouvelles_versions") or []):
            if str(s.get("classe") or "").upper().startswith("B"):
                items.append({"type": "source", "titre": f"{s.get('nom')} — nouvelle version à valider"})
    except Exception:  # noqa: BLE001
        pass
    return items


def etat(db) -> dict:
    """Rend {attentes, phrase, items, suggestions} pour la bannière d'accueil."""
    items = _attentes(db)
    n = len(items)
    if n == 0:
        phrase = "Bonjour Vic. Tout tourne : rien n'attend ta décision."
    elif n == 1:
        phrase = "Bonjour Vic. Une chose t'attend."
    else:
        mot = _MOTS.get(n, str(n))
        phrase = f"Bonjour Vic. {mot} choses t'attendent."
    return {"attentes": n, "phrase": phrase, "items": items[:8], "suggestions": list(SUGGESTIONS)}
