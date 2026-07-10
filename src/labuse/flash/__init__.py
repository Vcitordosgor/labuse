"""Module Flash — rapport de faisabilité PDF pour UNE parcelle, vendu à l'unité.

Règles anti-cannibalisation (mandat §2, NON NÉGOCIABLES) : Flash analyse UNE parcelle
que le client a déjà identifiée — aucune exploration, aucun classement, aucun
comparatif multi-parcelles (c'est la valeur de l'abonnement).
"""
from .report import TEMPLATE_VERSION, generate_flash_report

__all__ = ["generate_flash_report", "TEMPLATE_VERSION"]
