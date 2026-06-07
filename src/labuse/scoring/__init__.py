"""Scoring LA BUSE (brief §7) : complétude + opportunité + décision de statut.

Règle d'or : l'opportunité ne s'évalue/affiche JAMAIS sans la complétude.
"""
from .completeness import CompletenessResult, compute_completeness  # noqa: F401
from .feedback import apply_feedback  # noqa: F401
from .opportunity import OpportunityResult, compute_opportunity  # noqa: F401
from .status import decide_status  # noqa: F401
