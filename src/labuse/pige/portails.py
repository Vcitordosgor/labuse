"""Identités des portails d'annonces — CONSTANTES D'AFFICHAGE UNIQUEMENT.

C'est le SEUL endroit du dépôt où un nom/URL de portail a le droit d'exister, et il n'y sert QUE :
  · à afficher le nom du portail (« Voir l'annonce sur Leboncoin ») ;
  · à valider/reconnaître le préfixe d'URL que Vic colle à la saisie (le bouton sortant réutilise
    l'URL EXACTE saisie, jamais une URL fabriquée).

DOCTRINE (mandat §2) : aucun code ne requête, ne fetch, ne parse, ne capture un portail. Ce module ne
contient donc AUCUN appel réseau — que des chaînes. Recette permanente : `tests/test_pige_socle.py`.
"""
from __future__ import annotations

# slug interne → { nom affiché, préfixe d'URL attendu (pour reconnaître/valider la saisie) }.
PORTAILS: dict[str, dict[str, str | None]] = {
    "leboncoin":  {"nom": "Leboncoin",     "prefixe_url": "https://www.leboncoin.fr/"},
    "seloger":    {"nom": "SeLoger",       "prefixe_url": "https://www.seloger.com/"},
    "pap":        {"nom": "PAP",           "prefixe_url": "https://www.pap.fr/"},
    "logic-immo": {"nom": "Logic-Immo",    "prefixe_url": "https://www.logic-immo.com/"},
    "bienici":    {"nom": "Bien’ici",      "prefixe_url": "https://www.bienici.com/"},
    "agence":     {"nom": "Site d’agence", "prefixe_url": None},   # URL d'agence saisie telle quelle
    "autre":      {"nom": "Autre",         "prefixe_url": None},
}


def est_portail(slug: str) -> bool:
    return slug in PORTAILS


def nom(slug: str) -> str:
    """Nom affichable du portail (« Autre » pour un slug inconnu — jamais une erreur d'affichage)."""
    return PORTAILS.get(slug, PORTAILS["autre"])["nom"]  # type: ignore[return-value]


def slug_pour_url(url: str) -> str:
    """Reconnaît le portail à partir de l'URL SAISIE (préfixe). Rien d'inventé : défaut « autre »."""
    u = (url or "").strip().lower()
    for slug, meta in PORTAILS.items():
        pref = meta["prefixe_url"]
        if pref and u.startswith(pref.lower()):
            return slug
    return "autre"
