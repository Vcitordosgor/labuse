"""Source de vérité UNIQUE des offres commerciales LABUSE (mandat parcours d'entrée · E1).

Il existe DEUX offres, aucune autre — ni « Illimité », ni 499 €, ni Indé/Pro, ni sièges
multiples, ni founding (décision Vic 27/08/2026) :

  · INTÉGRAL — abonnement mensuel SANS engagement, 1 licence = 1 accès ;
  · FLASH    — paiement unique, un rapport PDF sur une parcelle (page publique /flash).

Les PRIX viennent de la config (`integral_prix_eur_mois`, `flash_price_eur`) : un seul
endroit à changer. Label et périodicité vivent ici. Tout écran (serveur ou front, via
l'endpoint /api/offres) lit CES valeurs — jamais un chiffre en dur dupliqué.

Décision Vic 27/08/2026 : Intégral passe en mensuel SANS ENGAGEMENT (plus de durée ferme de
12 mois, plus de reconduction annuelle, plus de loi Chatel) — voir CGV art. 5.
"""
from __future__ import annotations

from .config import get_settings


def offre_integral() -> dict:
    """L'offre Intégral, prix lu en config. Mensuel, `engagement=False` (sans engagement)."""
    s = get_settings()
    return {
        "cle": "integral",
        "label": "Intégral",
        "eur_mois": int(s.integral_prix_eur_mois),
        "engagement": False,
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
