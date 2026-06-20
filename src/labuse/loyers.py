"""Carte des loyers (DHUP) — LOT 4-B : marché LOCATIF local sur source ouverte.

Dataset OFFICIEL « Carte des loyers » (DHUP / Ministère de la Transition écologique, publié sur
data.gouv.fr), millésime 2025 : loyer d'annonce médian estimé en €/m²/mois (charges comprises),
par commune. Extrait ici à La Réunion (département 974, 24 communes), pour l'appartement et la
maison, avec intervalle de prédiction, nombre d'observations et GRANULARITÉ d'estimation
(« commune » = estimée à l'échelle communale ; « maille » = empruntée à une maille plus large,
donc moins locale → fiabilité signalée).

Rien n'est inventé : une valeur absente (NA) reste None ; une commune hors dataset renvoie None.
Donnée vendue offline (l'app reste hors-ligne sûre) : l'extrait La Réunion est versionné, jamais
re-téléchargé au rendu. Commune-agnostique, exécution Saint-Paul (97415).
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "carte_loyers_reunion_2025.json"

# Granularité DHUP → fiabilité de l'estimation locale (l'indicateur de tête de la carte des loyers).
_FIABILITE = {"commune": "bonne", "maille": "moyenne"}


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """Charge l'extrait La Réunion (idempotent + caché). Dict vide si fichier manquant/illisible."""
    try:
        data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, Any]]:
    """Index commune par code INSEE ET par nom normalisé (tolérant accents/casse)."""
    idx: dict[str, dict[str, Any]] = {}
    for rec in load().get("communes", []):
        idx[rec["insee"]] = rec
        idx["nom:" + _norm(rec.get("commune"))] = rec
    return idx


def source() -> dict[str, Any]:
    """Bloc de provenance (producteur, millésime, nature, mention) — toujours sourcé."""
    return dict(load().get("source") or {})


def get_loyers(insee: str | None = None, commune: str | None = None) -> dict[str, Any] | None:
    """Enregistrement loyers d'une commune (par INSEE d'abord, puis par nom). None si hors dataset."""
    idx = _index()
    rec = None
    if insee:
        rec = idx.get(str(insee).strip())
    if not rec and commune:
        rec = idx.get("nom:" + _norm(commune))
    return dict(rec) if rec else None


def _segment(seg: dict[str, Any] | None) -> dict[str, Any] | None:
    """Enrichit un segment (appartement/maison) d'un libellé de fiabilité, sans rien fabriquer."""
    if not seg or seg.get("loyer_m2") is None:
        return None
    out = dict(seg)
    out["fiabilite"] = _FIABILITE.get(seg.get("type_prediction"), "faible")
    out["maille_elargie"] = seg.get("type_prediction") == "maille"
    return out


def fiche_block(insee: str | None = None, commune: str | None = None) -> dict[str, Any] | None:
    """Bloc fiche « Marché locatif » (carte des loyers) pour une parcelle. None si hors 974/dataset."""
    rec = get_loyers(insee=insee, commune=commune)
    if not rec:
        return None
    appart, maison = _segment(rec.get("appartement")), _segment(rec.get("maison"))
    if not appart and not maison:   # commune présente mais aucune valeur exploitable
        return None
    return {
        "insee": rec["insee"],
        "commune": rec["commune"],
        "appartement": appart,
        "maison": maison,
        "source": source(),
    }
