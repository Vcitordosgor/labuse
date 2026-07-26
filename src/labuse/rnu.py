"""MANDAT RNU — communes sans document local d'urbanisme (règlement national d'urbanisme).

Flag COMMUNE-LEVEL, GÉNÉRAL (mandat C) : la liste vit dans config/rnu_communes.yaml
(déclaratif, vérifié à la main, sourcé — le flag GPU `is_rnu` est prouvé périmé).
Un PLU annulé/caduc fait retomber n'importe quelle commune au RNU : on AJOUTE une
entrée au yaml, aucun code à toucher.

Ce module ne porte QUE le flag et l'étiquetage produit (fiche + exports). La branche
RNU du moteur (parties actuellement urbanisées, plancher C adapté) attend la
VALIDATION de la méthode PAU — cf. docs/mandats/RNU_RAPPORT.md, proposition au STOP.

Doctrine wording : « commune au règlement national d'urbanisme — pas de PLU local ».
On n'affirme JAMAIS une constructibilité au RNU (parties urbanisées / continuité :
logique réglementaire subtile, non implémentée ici).
"""
from __future__ import annotations

from functools import lru_cache

from .config import load_yaml_config

#: Étiquette produit — wording DOCTRINAL (fiche + exports), exigé par le mandat B.
LIBELLE_RNU = "Commune au règlement national d'urbanisme — pas de PLU local"

#: Complément honnête affiché avec l'étiquette (fiche) : pourquoi les règles locales manquent.
DETAIL_RNU = ("Aucun document local approuvé : les règles nationales s'appliquent "
              "(constructibilité limitée aux parties actuellement urbanisées — "
              "analyse au cas par cas, non couverte par le zonage LABUSE).")


@lru_cache(maxsize=1)
def _entries() -> dict[str, dict]:
    """insee → entrée du yaml. Cache module (le yaml ne bouge pas en cours de run)."""
    try:
        cfg = load_yaml_config("rnu_communes") or {}
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for e in cfg.get("communes") or []:
        insee = str(e.get("insee") or "").strip()
        if insee:
            out[insee] = e
    return out


def is_rnu_insee(insee: str | None) -> bool:
    """La commune (code INSEE 5 chiffres) est-elle au RNU ?"""
    return bool(insee) and str(insee)[:5] in _entries()


def is_rnu_idu(idu: str | None) -> bool:
    """La parcelle (IDU) est-elle dans une commune au RNU ? (insee = left(idu, 5))"""
    return bool(idu) and str(idu)[:5] in _entries()


def rnu_block(idu: str | None) -> dict | None:
    """Bloc d'étiquetage produit pour la fiche/exports — None hors commune RNU."""
    if not is_rnu_idu(idu):
        return None
    e = _entries()[str(idu)[:5]]
    return {
        "libelle": LIBELLE_RNU,
        "detail": DETAIL_RNU,
        "commune_nom": e.get("nom"),
        "statut_detail": e.get("detail"),
        "verifie_le": e.get("verifie_le"),
    }


def clear_cache() -> None:
    """Tests : invalide le cache du yaml."""
    _entries.cache_clear()
