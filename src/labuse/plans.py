"""Plans commerciaux (Essentiel / Intégral) — STUB assumé (Phase 0 du mandat wave-adresses).

Il n'existe AUCUN système de comptes/sièges en base (auth pilote = mot de passe unique).
Ce module fournit les constantes et les points de branchement pour que les features
« réservé Intégral » et les quotas par plan soient CÂBLÉS dès maintenant ; le « mandat
Auth & Plans » (prérequis à la commercialisation) remplacera `plan_courant()` par le plan
du compte connecté sans toucher les appelants.
"""
from __future__ import annotations

from .config import get_settings

ESSENTIEL = "essentiel"
INTEGRAL = "integral"
PLANS = (ESSENTIEL, INTEGRAL)

#: features gatées par plan — la liste est l'API des appelants (Lots 4/5/6).
FEATURES: dict[str, str] = {
    "dossier_parcelle": ESSENTIEL,     # accessible dès Essentiel (quota mensuel)
    "dossier_illimite": INTEGRAL,      # Intégral : pas de quota Dossier parcelle
    "pre_dossier_pc": INTEGRAL,        # pack pré-dossier PC (Lot 5)
    "recherche_nl": ESSENTIEL,         # barre NL (Lot 6) — quota commun
}


#: filtres du moteur de segments réservés au plan Intégral (Lot 6.6 — « même mécanique
#: que les presets » : résultat grisé + CTA upgrade). VIDE aujourd'hui : la classification
#: commerciale des filtres (Q×A, BODACC…) sera tranchée avec le mandat Auth & Plans —
#: le branchement (api/ia.py segments-search) est prêt.
FILTRES_INTEGRAL: frozenset[str] = frozenset()


def plan_courant() -> str:
    """Plan du « compte » courant. STUB : lit LABUSE_PLAN_DEFAUT (pilote = intégral).
    Auth & Plans branchera ici le plan réel du compte/siège connecté."""
    p = (get_settings().plan_defaut or INTEGRAL).lower()
    return p if p in PLANS else INTEGRAL


def acces(feature: str) -> bool:
    """Le plan courant donne-t-il accès à cette feature ?"""
    requis = FEATURES.get(feature, ESSENTIEL)
    return plan_courant() == INTEGRAL or requis == ESSENTIEL


def refus(feature: str) -> dict:
    """Payload de refus homogène (grisé + CTA upgrade — même mécanique que les presets)."""
    return {"disponible": False, "plan_requis": FEATURES.get(feature, INTEGRAL),
            "raison": "réservé au plan Intégral", "cta": "upgrade"}
