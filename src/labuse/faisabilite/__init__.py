"""Moteur de PRÉ-FAISABILITÉ (ÉTAPE B).

Calcule une enveloppe constructible et une fourchette de capacité (niveaux,
surface de plancher, logements) à partir des VRAIES règles du PLU de Saint-Paul
(config/plu_saint_paul.yaml) — jamais d'emprise inventée : la capacité est bornée
par les RECULS, la HAUTEUR et la PLEINE TERRE, puis modulée par les contraintes
réunionnaises (pente, PPR, littoral, agricole/SAR).

N'altère NI la cascade NI le scoring : module séparé, en lecture seule des règles.
Chaque résultat est tracé à sa règle source. Tout est en fourchette, jamais un faux
chiffre exact.
"""
from .engine import Faisabilite, Hypotheses, Step, estimate_capacity  # noqa: F401
from .plu_rules import ZoneRules, load_rules, resolve_zone  # noqa: F401

BANDEAU = (
    "Pré-faisabilité indicative sur règlement PLU public — ne remplace pas une "
    "étude de faisabilité réglementaire par un professionnel."
)
