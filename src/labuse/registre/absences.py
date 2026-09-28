"""COHERENCE-FIX-1 (lot D) — LE VOCABULAIRE UNIQUE DE L'ABSENCE : cinq formes, pas une de plus.

L'audit COHERENCE-1 recensait 178 phrases d'absence déclarées (ABSENCES.csv) et TROIS idiomes
à l'écran (« — », « n.c. », « non chiffré ») : trois manières de dire la même chose, et des
phrases libres qui dérivent. Ici, la règle du registre : TOUTE phrase d'absence déclarée
(`declarations/*.yaml`, champ `absence`) doit appartenir à l'une des CINQ formes ci-dessous —
V6 échoue sinon (test_coherencefix1_lot_d_absences). Le rendu compact d'un chiffre absent
reste « — » partout (format.ts) ; « n.c. » est réservé à la sentinelle SIRENE 1900 (dit).

Les cinq formes (chacune commence par « <Notion> : », sauf le tiret compact) :
  F1 non_disponible — la donnée devrait exister mais on ne l'a pas
      (« … : donnée non disponible / non renseignée / non déterminée / non évaluée /
      non mesurée / non résolue / non publiée / non estimable … »)
  F2 aucun — le vrai zéro d'inventaire : la source a répondu, il n'y a rien
      (« … : aucun(e) <objet> <périmètre>. »)
  F3 hors_perimetre — l'objet est hors du périmètre/de la couverture de la donnée
      (« … : parcelle/commune hors <périmètre> », « hors couverture <source> »)
  F4 sans_objet — la notion ne s'applique pas ici
      (« … : sans objet (<raison>). »)
  F5 non_calculable — un calcul dont une dépendance manque ou dont l'échantillon est
      trop petit (« … : non calculable / échantillon insuffisant / rien d'évaluable … »)
"""
from __future__ import annotations

import re

#: forme → regex (cherchée dans la phrase entière ; l'ORDRE fait foi : « sans objet (pas de
#: zone AU) » classe sans_objet même si sa parenthèse contient un « pas de »).
FORMES: dict[str, re.Pattern] = {
    "sans_objet": re.compile(r"sans objet"),
    "non_calculable": re.compile(
        r"non calculable|non calculé|pas calculé|échantillon .{0,40}insuffisant|"
        r"rien d'évaluable|insuffisant pour|non constructible ou"),
    "non_disponible": re.compile(
        r"non (disponible|renseign|détermin|évalu|mesur|résolu|publi|estimable|identifi|rattach|couvert|not)|indisponible"),
    "aucun": re.compile(r"\baucune? |\brien à |\bpas (encore )?d[e']|\bsans (?!objet)", re.IGNORECASE),
    "hors_perimetre": re.compile(r"\bhors ", re.IGNORECASE),
}


def classer(phrase: str) -> str | None:
    """La forme d'une phrase d'absence — None si elle n'appartient à AUCUNE des cinq
    (→ V6 échoue : on la reformule dans le vocabulaire, on n'ajoute pas une sixième forme)."""
    p = (phrase or "").strip()
    if not p or p == "—":
        return "tiret_compact"     # le rendu compact des tableaux (format.ts) — pas une 6e forme
    for nom, rx in FORMES.items():
        if rx.search(p):
            return nom
    return None


def hors_vocabulaire() -> list[tuple[str, str]]:
    """(surface, phrase) des déclarations dont la phrase d'absence n'entre dans aucune forme.
    Vide = le vocabulaire tient. Joué par V6 et par le banc (referentiel)."""
    from . import declarations as _d
    surfaces, _generiques = _d.charger()
    out: list[tuple[str, str]] = []
    for s in surfaces:
        for l in s.donnees:
            if l.absence and classer(l.absence) is None:
                out.append((f"{s.surface}:{l.quoi}", l.absence))
    return out
