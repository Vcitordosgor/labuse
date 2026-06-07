"""Agent IA LA BUSE (brief §9) : raisonne UNIQUEMENT sur le payload fourni.

Provider `stub` par défaut (déterministe, hors-ligne, n'invente jamais) ; provider
`anthropic` prêt à brancher (clé + réseau requis).
"""
from .agent import StubProvider, analyze, get_provider  # noqa: F401
from .prompt import SYSTEM_PROMPT, payload_from_outcome  # noqa: F401
from .schema import AI_OUTPUT_SCHEMA, validate_ai_output  # noqa: F401
