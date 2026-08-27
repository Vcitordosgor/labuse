"""Source de vérité UNIQUE des offres commerciales LABUSE (mandat parcours d'entrée · E1).

Il existe DEUX offres, aucune autre — ni « Illimité », ni 499 €, ni Indé/Pro, ni sièges
multiples, ni founding (décision Vic 27/08/2026) :

  · INTÉGRAL — abonnement mensuel récurrent (engagement 12 mois), 1 licence = 1 accès ;
  · FLASH    — paiement unique, un rapport PDF sur une parcelle (page publique /flash).

Les PRIX viennent de la config (`integral_prix_eur_mois`, `flash_price_eur`) : un seul
endroit à changer. Label, périodicité et engagement vivent ici. Tout écran (serveur ou
front, via l'endpoint /api/offres) lit CES valeurs — jamais un chiffre en dur dupliqué.
"""
from __future__ import annotations

from .config import get_settings

#: engagement ferme de l'offre Intégral, en mois (décision Vic).
INTEGRAL_ENGAGEMENT_MOIS = 12


def offre_integral() -> dict:
    """L'offre Intégral, prix lu en config. `eur_mois` int, `engagement_mois` 12."""
    s = get_settings()
    return {
        "cle": "integral",
        "label": "Intégral",
        "eur_mois": int(s.integral_prix_eur_mois),
        "engagement_mois": INTEGRAL_ENGAGEMENT_MOIS,
        "periodicite": "mois",
    }


def offre_flash() -> dict:
    """L'offre Flash, prix lu en config. `eur` int, paiement unique."""
    s = get_settings()
    return {
        "cle": "flash",
        "label": "Flash",
        "eur": int(s.flash_price_eur),
        "periodicite": "unique",
        "validite_lien_jours": int(s.flash_token_days),
    }


def offres_publiques() -> dict:
    """Les deux offres — payload servi tel quel au front par /api/offres."""
    return {"integral": offre_integral(), "flash": offre_flash()}
