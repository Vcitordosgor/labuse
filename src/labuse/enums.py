"""Vocabulaires contrôlés de LA BUSE.

Les valeurs de chaîne sont alignées sur le brief (§2, §5, §7, §9, §11) et
servent telles quelles en base et dans les payloads JSON. Ne pas renommer
sans migration : ce sont des contrats.
"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Enum sérialisable en str (compat 3.11 ; on n'importe pas enum.StrEnum)."""

    def __str__(self) -> str:  # pragma: no cover - cosmétique
        return self.value


class CascadeVerdict(StrEnum):
    """Verdict d'une couche de la cascade (brief §2)."""

    HARD_EXCLUDE = "HARD_EXCLUDE"   # élimination — faux positif quasi certain
    SOFT_FLAG = "SOFT_FLAG"         # contrainte non éliminatoire (avec sévérité)
    POSITIVE = "POSITIVE"           # signal favorable
    PASS = "PASS"                   # traversée sans remarque
    UNKNOWN = "UNKNOWN"             # donnée indisponible → impacte la complétude


class Severity(StrEnum):
    """Sévérité d'un SOFT_FLAG. Multiplicateurs : faible ×1, moyen ×2, fort ×3 ; info ×0."""

    INFO = "info"       # flag AFFICHÉ mais 0 point (ex. mvt : aléa déjà compté dans PPR)
    FAIBLE = "faible"
    MOYEN = "moyen"
    FORT = "fort"


class EvaluationStatus(StrEnum):
    """Statut d'une évaluation de parcelle (brief §5 / §7C)."""

    OPPORTUNITE = "opportunite"
    A_CREUSER = "a_creuser"
    FAUX_POSITIF_PROBABLE = "faux_positif_probable"
    EXCLUE = "exclue"


class SourceResultStatus(StrEnum):
    """État d'un appel source pour une parcelle (brief §4 — résultats partiels)."""

    REPONDU = "repondu"
    EN_COURS = "en_cours"
    ECHEC = "echec"
    NON_SOLLICITE = "non_sollicite"


class DataSourceStatus(StrEnum):
    """Statut d'un connecteur de source de données (brief §5/§6)."""

    CONNECTE = "connecte"     # branché auto (REST/WFS live)
    PARTIEL = "partiel"       # branché par import / couverture incomplète
    MOCK = "mock"             # fixture / réponse simulée
    MANUEL = "manuel"         # fallback champ manuel
    A_FAIRE = "a_faire"       # à connecter plus tard


class ReliabilityLevel(StrEnum):
    """Fiabilité d'une source (marqueurs du brief §6)."""

    VERIFIE = "verifie"             # [✓ vérifié]
    A_CONFIRMER = "a_confirmer"     # [~ à confirmer]
    SOUS_CONVENTION = "sous_convention"  # [~ accès sous convention]
    LEGAL_RESTREINT = "legal"       # [~ légal]


class ConfidenceLevel(StrEnum):
    """Niveau de confiance de l'agent IA (brief §9)."""

    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


class FeedbackVerdict(StrEnum):
    """Retour du promoteur sur une parcelle (brief §5/§10)."""

    FALSE_POSITIVE = "false_positive"
    GOOD_LEAD = "good_lead"
    NOT_INTERESTED = "not_interested"


class SignalType(StrEnum):
    """Type de signal de veille (offre C, brief §5 — post-MVP)."""

    NEW_PERMIT_NEARBY = "new_permit_nearby"
    MUTATION_DVF = "mutation_dvf"
    ZONAGE_CHANGE = "zonage_change"
