"""EXPORTS-2 — le builder unique des cinq documents (Dossier · Résumé · Financier · Apporteur ·
Pré-dossier PC) + le Flash. Un seul rendu (WeasyPrint, theme.css = maquette.css), chaque chiffre
imprimé lu par son id du registre, sa nature dérivée du registre, le pied de section tiré des
réservoirs lus, le numéro de rapport unique et l'archive JSON reproductible.

Points d'entrée : `builder.construire` / `builder.generer_pdf`.
"""
from __future__ import annotations

from . import archive, builder, collecte, nature, numeros, pieds, rendu, verdicts  # noqa: F401

__all__ = ["archive", "builder", "collecte", "nature", "numeros", "pieds", "rendu", "verdicts"]
