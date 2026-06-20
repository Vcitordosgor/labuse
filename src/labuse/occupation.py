"""Statut d'occupation des résidences principales (INSEE RP 2022) — LOT 4-B, volet structure.

Part propriétaires / locataires (dont HLM) / logés gratuitement, par commune, extraite du
« Dossier complet » de l'INSEE (Recensement de la population 2022). Source ouverte officielle.

Prudence assumée (cf. arbitrage) : ces chiffres proviennent d'un tableau HTML du dossier complet,
parsé une seule fois et VENDU offline (l'app reste hors-ligne sûre, aucun scraping au rendu). Rien
n'est inventé : une commune absente de l'extrait renvoie None ; une valeur manquante reste None.
Commune-agnostique, exécution Saint-Paul (97415).
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "insee_occupation_reunion_2022.json"


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
    idx: dict[str, dict[str, Any]] = {}
    for rec in load().get("communes", []):
        idx[rec["insee"]] = rec
        idx["nom:" + _norm(rec.get("commune"))] = rec
    return idx


def source() -> dict[str, Any]:
    return dict(load().get("source") or {})


def get_occupation(insee: str | None = None, commune: str | None = None) -> dict[str, Any] | None:
    """Statut d'occupation d'une commune (par INSEE d'abord, puis par nom). None si hors extrait."""
    idx = _index()
    rec = None
    if insee:
        rec = idx.get(str(insee).strip())
    if not rec and commune:
        rec = idx.get("nom:" + _norm(commune))
    return dict(rec) if rec else None


def fiche_block(insee: str | None = None, commune: str | None = None) -> dict[str, Any] | None:
    """Bloc fiche « Statut d'occupation » (propriétaires / locataires / HLM). None si hors extrait."""
    rec = get_occupation(insee=insee, commune=commune)
    if not rec or not (rec.get("proprietaire") or {}).get("n"):
        return None
    return {
        "insee": rec["insee"],
        "commune": rec["commune"],
        "ensemble": rec.get("ensemble"),
        "proprietaire": rec.get("proprietaire"),
        "locataire": rec.get("locataire"),
        "dont_hlm": rec.get("dont_hlm"),
        "loge_gratuit": rec.get("loge_gratuit"),
        "source": source(),
    }
