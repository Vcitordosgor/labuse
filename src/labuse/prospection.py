"""Module PROSPECTION (Niveau 1) — saisie MANUELLE, légale, sans donnée externe.

LA BUSE ne récupère AUCUNE donnée propriétaire nominative : tous les champs ci-dessous
sont saisis par l'utilisateur (ou marqués « à identifier »). Aucun nom n'est jamais
pré-rempli automatiquement. Stocké dans pipeline_entries.prospection (jsonb) — effaçable
d'un bloc (RGPD : droit à l'effacement). Cœur pur, sans DB.
"""
from __future__ import annotations

from datetime import date

# Statuts propriétaire (jamais « officiel »/« garanti » — toujours « probable » ou « manuel »).
STATUTS = {
    "inconnu", "a_identifier", "identifie_manuellement", "public_probable",
    "institutionnel_probable", "indivision_probable", "copropriete_probable",
}
SOURCES = {
    "non_renseignee", "saisi_utilisateur", "deduit_manuellement",
    "document_externe_utilisateur", "autre",
}
CONFIANCES = {"inconnu", "faible", "moyen", "eleve"}

# Champs de contact MANUELS (texte libre borné) — aucun pré-remplissage automatique.
TEXT_FIELDS = {"contact_nom", "contact_organisation", "contact_telephone",
               "contact_email", "contact_adresse", "prochaine_action",
               "responsable_interne", "notes_contact"}
DATE_FIELDS = {"date_prochaine_action", "date_derniere_verification"}

_DISCLAIMER = ("Informations de contact saisies MANUELLEMENT par l'utilisateur (ou issues "
               "d'une source autorisée qu'il a renseignée). LA BUSE ne récupère aucune donnée "
               "propriétaire automatiquement et ne garantit pas l'identité du propriétaire.")


def default_prospection() -> dict:
    """État initial : propriétaire NON identifié (aucun nom pré-rempli)."""
    return {"statut_proprietaire": "inconnu", "source_statut": "non_renseignee",
            "niveau_confiance": "inconnu"}


def merge_prospection(current: dict | None, patch: dict | None) -> dict:
    """Fusionne un patch utilisateur dans l'état courant, en VALIDANT chaque champ.

    - enums (statut/source/confiance) contraints ;
    - champs texte = libre borné 2000 car. ;
    - dates = ISO valide ou effacement ;
    - clés inconnues IGNORÉES (pas de stockage arbitraire) ;
    - lève ValueError sur valeur d'enum/date invalide.
    """
    out = dict(current or {})
    enums = {"statut_proprietaire": STATUTS, "source_statut": SOURCES, "niveau_confiance": CONFIANCES}
    for k, v in (patch or {}).items():
        if k in enums:
            if v not in enums[k]:
                raise ValueError(f"{k} invalide : {v!r}")
            out[k] = v
        elif k in TEXT_FIELDS:
            out[k] = ("" if v is None else str(v))[:2000]
        elif k in DATE_FIELDS:
            if v in (None, ""):
                out[k] = None
            else:
                date.fromisoformat(str(v))   # valide (lève ValueError sinon)
                out[k] = str(v)
        # toute autre clé est ignorée (anti-injection)
    return out


def statut_label(statut: str | None) -> str:
    return {
        "inconnu": "Propriétaire inconnu",
        "a_identifier": "Propriétaire à identifier",
        "identifie_manuellement": "Identifié manuellement",
        "public_probable": "Propriétaire public probable",
        "institutionnel_probable": "Propriétaire institutionnel probable",
        "indivision_probable": "Indivision probable",
        "copropriete_probable": "Copropriété probable",
    }.get(statut or "inconnu", "Propriétaire inconnu")


def has_manual_contact(prospection: dict | None) -> bool:
    p = prospection or {}
    return any((p.get(k) or "").strip() for k in
               ("contact_nom", "contact_organisation", "contact_telephone", "contact_email", "contact_adresse"))


def disclaimer() -> str:
    return _DISCLAIMER
