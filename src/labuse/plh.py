"""Orientations habitat du PLH du TCO (LOT 4.1).

Données EXTRAITES du 3e PLH du TCO (adopté en CC du 16/12/2019), jamais inventées. Expose,
pour la commune d'une parcelle : la cible de répartition (40 % libre / 60 % aidé), les
typologies aidées, le bilan communal et un indicateur d'alignement FACTUEL (la cible PLH
appliquée à la capacité estimée). Ce qui n'est pas chiffré par le PLH reste « non précisé ».
Commune-agnostique : une commune hors TCO renvoie None (on ne fabrique aucune orientation).
"""
from __future__ import annotations

from . import config


def orientations(commune: str, logements_estimes: int | None = None) -> dict | None:
    """Bloc « Orientations PLH » pour une commune (None si hors PLH/TCO ou config absente)."""
    try:
        cfg = config.plh() or {}
    except Exception:  # noqa: BLE001 - orientation optionnelle, jamais bloquante
        return None
    communes = cfg.get("communes") or {}
    if commune not in communes:
        return None
    cible = cfg.get("cible_repartition") or {}
    comm = communes.get(commune) or {}
    out = {
        "source": cfg.get("source"),
        "cible_repartition": cible,
        "besoin_tco_logements_an": cfg.get("besoin_tco_logements_an"),
        "typologies_aidees": cfg.get("typologies_aidees"),
        "commune": commune,
        "bilan": comm.get("bilan"),
        "note": comm.get("note"),
    }
    aide_pct = cible.get("aide_pct")
    if logements_estimes and aide_pct:   # alignement FACTUEL : cible PLH × capacité estimée
        aides = round(logements_estimes * aide_pct / 100)
        out["alignement"] = {
            "logements_estimes": logements_estimes,
            "aides_cibles": aides,
            "libres_cibles": logements_estimes - aides,
            "message": (f"Pour ~{logements_estimes} logements estimés, le PLH oriente vers "
                        f"~{aides} aidés ({aide_pct} %) et ~{logements_estimes - aides} libres. "
                        "Un programme aligné (LLTS / LLS / PLS) facilite l'instruction du permis."),
        }
    return out
