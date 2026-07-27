"""M26-A — planificateur 100 % DÉTERMINISTE (Factor 8) : une mission = une séquence
de moteurs codée en dur. Pas de LLM ici. Testé en golden (snapshot figé).

Le plan exécuté est figé dans l'événement `run_started` — le rejeu utilise le plan de
l'époque, jamais celui du code courant.

Décision Vic (GO M26-A Q1) : l'étape `mutation` appelle le CHAMPION P (lecture seule du
run servi épinglé, étiquette Sourcé) — jamais le Radar Mutation V1, gravé NON SERVI
(ALGO-1 §7-G, RR 0,51). `assemblage*` = assemblage du récapitulatif du dossier
(retenues/écartées + agrégats), pas le moteur multi-parcelles.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Etape:
    moteur: str
    bloquant: bool


PLAN_INSTRUIRE: tuple[Etape, ...] = (
    Etape("criblage", bloquant=True),
    Etape("faisabilite", bloquant=True),
    Etape("risques", bloquant=True),
    Etape("marche_dvf", bloquant=False),   # échec → « charge foncière non calculable »
    Etape("mutation", bloquant=False),     # lecture seule champion P (tier/rang/percentile)
    Etape("assemblage", bloquant=True),
)

PLAN_SHORTLIST: tuple[Etape, ...] = (
    Etape("criblage", bloquant=True),
    Etape("faisabilite", bloquant=True),
    Etape("risques", bloquant=True),
    Etape("mutation", bloquant=False),
    Etape("assemblage_court", bloquant=True),
)

PLAN_VERIFIER: tuple[Etape, ...] = (
    Etape("scoreur_unitaire", bloquant=True),
    Etape("assemblage_verdict", bloquant=True),
)

PLANS: dict[str, tuple[Etape, ...]] = {
    "instruire": PLAN_INSTRUIRE,
    "shortlist": PLAN_SHORTLIST,
    "verifier_adresse": PLAN_VERIFIER,
}


def plan_pour(mission: str) -> tuple[Etape, ...]:
    if mission not in PLANS:
        raise ValueError(f"mission inconnue : {mission!r}")
    return PLANS[mission]


def plan_serialise(mission: str) -> list[dict]:
    """Forme figée dans run_started (le rejeu lit CETTE liste, pas le code courant)."""
    return [{"moteur": e.moteur, "bloquant": e.bloquant} for e in plan_pour(mission)]
