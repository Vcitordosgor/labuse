"""JOHN-TAYLOR-1 — le PLAFOND MENSUEL de coût de John.

Le mandat : « Plafond mensuel configurable (50 € par défaut), coût affiché en temps réel ; au plafond,
John répond qu'il est en pause jusqu'au mois suivant. »

Le coût est lu du ledger `ia_log` (écrit par `ai.core._log_cost` à chaque appel modèle) sur les
surfaces `john-*` du MOIS COURANT en heure Réunion (le moteur DB force `Indian/Reunion`, donc `now()`
et `date_trunc('month', now())` sont déjà en heure locale). On ne compte que ce que John dépense :
`kind LIKE 'john-%'`.

Au plafond, `en_pause()` est vrai : l'orchestration NE lance AUCUN appel modèle et répond un message
honnête. C'est une COUPURE PROPRE (pas une erreur) : elle se lève d'elle-même au changement de mois.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


@dataclass
class EtatBudget:
    """L'état du plafond, lisible au dashboard et par l'orchestration."""
    plafond_eur: float
    depense_eur: float
    appels: int
    en_pause: bool

    @property
    def reste_eur(self) -> float:
        return round(max(0.0, self.plafond_eur - self.depense_eur), 5)

    def to_json(self) -> dict:
        return {"plafond_eur": round(self.plafond_eur, 2), "depense_eur": round(self.depense_eur, 4),
                "reste_eur": round(self.reste_eur, 4), "appels": self.appels, "en_pause": self.en_pause}


def _plafond(settings=None) -> float:
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    return float(getattr(settings, "john_plafond_eur", 50.0) or 0.0)


def cout_mois(db) -> tuple[float, int]:
    """(coût €, nb d'appels) de John sur le MOIS COURANT (Réunion). Lecture seule, best-effort :
    si le ledger n'existe pas encore (aucun appel jamais fait), renvoie (0, 0) sans lever."""
    try:
        row = db.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) AS c, COUNT(*) AS n FROM ia_log "
            "WHERE kind LIKE 'john-%' AND ts >= date_trunc('month', now())")).mappings().first()
    except Exception:  # noqa: BLE001 — table absente / base non prête : pas de dépense connue
        return 0.0, 0
    return float(row["c"] or 0.0), int(row["n"] or 0)


def etat(db, settings=None) -> EtatBudget:
    """L'état complet du plafond. `en_pause` dès que la dépense du mois atteint le plafond."""
    plafond = _plafond(settings)
    depense, appels = cout_mois(db)
    en_pause = plafond > 0 and depense >= plafond
    return EtatBudget(plafond_eur=plafond, depense_eur=depense, appels=appels, en_pause=en_pause)


def message_pause(e: EtatBudget) -> str:
    """Le message honnête que John rend au plafond (chat, résumé, veille, enquête)."""
    return (f"Je suis en pause jusqu'au mois prochain : le plafond de coût du mois "
            f"({e.plafond_eur:.0f} €) est atteint ({e.depense_eur:.2f} € dépensés). "
            f"Je reprends au changement de mois, ou dès que Vic relève le plafond.")
