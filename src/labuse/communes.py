"""Référentiel d'état & de FIABILITÉ des communes (LOT 6 — garde-fou produit).

Source unique : `config/communes_gold_standard.yaml`. Sert à la fois :
  - au script de généralisation (`scripts/import_commune_gold_standard.py`) ;
  - au garde-fou UI : empêcher qu'une commune NON refaite au standard Saint-Paul soit perçue comme
    fiable. `reliable = (etat == "gold")` — c'est de l'INFORMATION, jamais une modification de donnée,
    de verdict ou de cascade.

Lecture seule, pur (aucune écriture base). Validé contre la liste officielle `REUNION_COMMUNES`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from . import config
from .ingestion.run_all import REUNION_COMMUNES

# Seul l'état "gold" est commercialement fiable (refait au standard Saint-Paul, couches complètes).
RELIABLE_ETATS = frozenset({"gold"})

_ETAT_LABEL = {
    "gold": "Validée au standard Saint-Paul",
    "partiel_evalue": "Partielle — évaluée sur données incomplètes",
    "partiel_non_evalue": "Partielle — non évaluée",
    "absent": "Non importée",
}
# Référentiel officiel INSEE↔nom (24 communes) — pour valider qu'une commune existe vraiment.
_OFFICIAL_BY_INSEE = {insee: nom for insee, nom in REUNION_COMMUNES}
_OFFICIAL_BY_NAME = {nom: insee for insee, nom in REUNION_COMMUNES}


@lru_cache(maxsize=1)
def load_communes() -> dict[str, dict[str, Any]]:
    """{nom_commune: entrée}. Cache (la config ne change pas en cours d'exécution)."""
    data = config.load_yaml_config("communes_gold_standard")
    out: dict[str, dict[str, Any]] = {}
    for e in data.get("communes", []):
        nom = e.get("nom")
        if nom:
            out[nom] = dict(e)
    return out


@lru_cache(maxsize=1)
def meta() -> dict[str, Any]:
    return dict(config.load_yaml_config("communes_gold_standard").get("meta", {}))


def commune_known(insee: str | None = None, nom: str | None = None) -> bool:
    """Vrai si la commune existe dans le référentiel officiel La Réunion (anti-erreur de commune)."""
    if insee is not None and insee in _OFFICIAL_BY_INSEE:
        return nom is None or _OFFICIAL_BY_INSEE[insee] == nom
    if nom is not None and nom in _OFFICIAL_BY_NAME:
        return insee is None or _OFFICIAL_BY_NAME[nom] == insee
    return False


def get(nom: str) -> dict[str, Any] | None:
    return load_communes().get(nom)


def is_reliable(nom: str | None) -> bool:
    """Fiable = refaite au standard Saint-Paul (etat 'gold'). Inconnue/partielle/absente → False."""
    e = load_communes().get(nom or "")
    return bool(e and e.get("etat") in RELIABLE_ETATS)


def reliability(nom: str | None) -> dict[str, Any]:
    """Bloc de fiabilité d'une commune pour l'UI (information, jamais une donnée métier).

    Toujours défini : une commune absente du référentiel est traitée comme NON fiable + signalée.
    """
    e = load_communes().get(nom or "")
    if not e:
        return {
            "commune": nom, "etat": "inconnu", "reliable": False,
            "label": "Commune hors référentiel",
            "title": "Commune non validée au standard Saint-Paul",
            "warnings": ["Données partielles ou non vérifiées",
                         "Verdicts à ne pas utiliser commercialement",
                         "Recalcul au standard à venir"],
            "gold_reference": meta().get("gold_reference", "Saint-Paul"),
        }
    etat = e.get("etat")
    reliable = etat in RELIABLE_ETATS
    if reliable:
        return {
            "commune": nom, "etat": etat, "reliable": True,
            "label": _ETAT_LABEL.get(etat, etat),
            "title": None, "warnings": [],
            "gold_reference": meta().get("gold_reference", "Saint-Paul"),
        }
    return {
        "commune": nom, "etat": etat, "reliable": False,
        "label": _ETAT_LABEL.get(etat, etat),
        "title": "Commune non encore validée au standard Saint-Paul",
        "warnings": [
            "Données partielles (couches critiques incomplètes)",
            "Verdicts à ne pas utiliser commercialement",
            "Recalcul au standard à venir",
        ],
        "strategie": e.get("strategie"), "vague": e.get("vague"),
        "gold_reference": meta().get("gold_reference", "Saint-Paul"),
    }


def status_list() -> list[dict[str, Any]]:
    """Liste des 24 communes + fiabilité, triée par vague puis nom (pour /communes/status)."""
    out = []
    for nom, e in load_communes().items():
        out.append({
            "commune": nom, "insee": e.get("insee"), "etat": e.get("etat"),
            "reliable": e.get("etat") in RELIABLE_ETATS,
            "parcelles_en_base": e.get("parcelles_en_base"),
            "attendu": e.get("attendu"), "priorite": e.get("priorite"),
            "vague": e.get("vague"), "risque": e.get("risque"),
            "strategie": e.get("strategie"), "label": _ETAT_LABEL.get(e.get("etat"), e.get("etat")),
        })
    out.sort(key=lambda x: (x["vague"] if x["vague"] is not None else 99, x["commune"]))
    return out
