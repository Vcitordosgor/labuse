"""M85-B — LE REGISTRE des notifications : l'inventaire UNIQUE.

Tout type d'envoi est déclaré ICI. Un type non déclaré est REFUSÉ (personne n'ajoute un envoi hors
registre) — c'est ce qui empêche l'empilement anarchique. Doctrine : chaque notification DÉPENSE la
tolérance du client (coût cumulatif et invisible) ; la discipline est la retenue. Ce qui a des
conséquences réelles (maintenance, compte) échappe aux préférences ; tout le reste est désactivable.

Les trois CHAÎNES du mandant :
  1 — une parcelle SUIVIE a changé ;
  2 — une ZONE de veille a bougé ;
  3 — LABUSE a quelque chose d'important à dire (annonce, maintenance).
Cadence : chaînes 1+2 → un mail/jour max (digest du matin, J-1) ; chaîne 3 → quand le mandant décide.
"""
from __future__ import annotations

# Chaque type : libellé client, chaîne, producteur, canaux autorisés, canal par défaut, cadence,
# désactivable (par mail), priorité (1 = la plus haute), gabarit, pilote_seulement.
REGISTRE: dict[str, dict] = {
    "parcelle_suivie": {
        "libelle": "Vos parcelles suivies",
        "chaine": 1, "producteur": "suivi_parcelle (SQL — à chaque ingestion + bascule de run)",
        "canaux": ("cloche", "mail"), "canal_defaut": ("cloche", "mail"),
        "cadence": "digest quotidien (J-1)", "desactivable": True, "priorite": 2, "gabarit": "digest",
    },
    "veille_zone": {
        "libelle": "Vos zones de veille",
        "chaine": 2, "producteur": "evaluer_toutes / saved_searches (SQL)",
        "canaux": ("cloche", "mail"), "canal_defaut": ("cloche", "mail"),
        "cadence": "digest quotidien (J-1)", "desactivable": True, "priorite": 2, "gabarit": "digest",
    },
    "annonce_produit": {
        "libelle": "Annonces LABUSE (nouveautés, sources)",
        "chaine": 3, "producteur": "pilote (CLI / écran)",
        "canaux": ("cloche", "mail"), "canal_defaut": ("cloche", "mail"),
        "cadence": "immédiat (décision du mandant)", "desactivable": True, "priorite": 3,
        "gabarit": "annonce",
    },
    "maintenance": {
        "libelle": "Maintenance & compte",
        "chaine": 3, "producteur": "pilote (CLI / écran)",
        "canaux": ("cloche", "mail"), "canal_defaut": ("cloche", "mail"),
        # NON désactivable par mail : conséquences réelles (coupure programmée, alerte de compte).
        "cadence": "immédiat", "desactivable": False, "priorite": 1, "gabarit": "maintenance",
    },
    "systeme_pilote": {
        "libelle": "Santé du système (pilote)",
        "chaine": 0, "producteur": "ingestion / fraîcheur (M84)",
        "canaux": ("cloche",), "canal_defaut": ("cloche",),   # cloche SEULE, jamais de mail
        "cadence": "à l'événement", "desactivable": True, "priorite": 1, "gabarit": None,
        "pilote_seulement": True,
    },
}

#: types réglables par le client dans ses préférences (maintenance : affiché mais VERROUILLÉ).
TYPES_CLIENT = ("parcelle_suivie", "veille_zone", "annonce_produit", "maintenance")

# Correspondance des `kind` historiques d'event_log → type de registre (les nouveaux producteurs
# écrivent DIRECTEMENT le type de registre comme kind). Le marché partagé (compte_id NULL) n'est PAS
# un type de mail : il reste un flux CLOCHE informatif, hors des 3 chaînes → jamais d'e-mail.
_KIND_VERS_TYPE = {
    "parcelle_suivie": "parcelle_suivie", "veille_zone": "veille_zone",
    "annonce_produit": "annonce_produit", "maintenance": "maintenance",
    "systeme": "systeme_pilote", "systeme_pilote": "systeme_pilote",
    "veille": "veille_zone",                                  # veilles Copilote + recherches
    "permis": "parcelle_suivie", "bascule": "parcelle_suivie", "bodacc": "parcelle_suivie",
    "match": "veille_zone",
}


def est_declare(type_: str) -> bool:
    """Un type non déclaré au registre est REFUSÉ (garde-fou anti-empilement)."""
    return type_ in REGISTRE


def meta(type_: str) -> dict:
    return REGISTRE.get(type_, {})


def canaux(type_: str) -> tuple:
    return REGISTRE.get(type_, {}).get("canaux", ())


def peut_mail(type_: str) -> bool:
    return "mail" in canaux(type_)


def desactivable(type_: str) -> bool:
    """False = échappe aux préférences (maintenance) : jamais coupable par le client."""
    return REGISTRE.get(type_, {}).get("desactivable", True)


def type_pour_kind(kind: str) -> str:
    """`kind` event_log → type de registre. Défaut prudent : systeme_pilote (jamais un mail à tort)."""
    return _KIND_VERS_TYPE.get(kind, "systeme_pilote")


# M87 P5 — les CHANGEMENTS détectés SUR une parcelle suivie (maille STRICTE, jamais « à proximité »),
# avec leur libellé court. L'en-tête de la cloche est DÉRIVÉ de cette liste, jamais écrit à la main —
# ainsi il ne redevient pas faux au prochain mandat. `producteur_reel` = le producteur DÉTECTE vraiment
# (code présent et exécutable, evaluer_suivis / detect_events) ; on n'annonce que le détectable.
CHANGEMENTS_SUIVI: list[dict] = [
    {"code": "mutation", "libelle_court": "vente", "producteur_reel": True},
    {"code": "permis", "libelle_court": "permis", "producteur_reel": True},
    {"code": "bodacc", "libelle_court": "procédure BODACC", "producteur_reel": True},
    {"code": "zonage", "libelle_court": "changement de zonage", "producteur_reel": True},
    {"code": "tier", "libelle_court": "évolution du classement", "producteur_reel": True},
]


def libelles_entete_cloche() -> list[str]:
    """Libellés courts des changements RÉELLEMENT détectés (producteur présent) — l'en-tête de la cloche
    les concatène, jamais écrit en dur. La maille est SUR la parcelle (jamais « à proximité »)."""
    return [c["libelle_court"] for c in CHANGEMENTS_SUIVI if c["producteur_reel"]]


def defaut_prefs() -> dict:
    """Défaut nouveau compte : TOUT activé (cloche + mail là où c'est permis). maintenance = verrouillé
    on. systeme_pilote exclu (pas une préférence client)."""
    out = {}
    for t in TYPES_CLIENT:
        c = canaux(t)
        out[t] = {"cloche": "cloche" in c, "mail": "mail" in c}
    return out
