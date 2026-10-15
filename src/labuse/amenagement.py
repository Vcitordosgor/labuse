"""CHASSE-INVARIANTS-FIX-1 Lot 7 (E-15) — le seuil « opération d'aménagement ».

Au-delà de 2 ha de surface de terrain, un bilan PROMOTEUR à rebours (marge, charge foncière
supportable) n'a plus de sens métier : c'est une opération d'AMÉNAGEMENT (lotissement / ZAC /
division foncière), pas une promotion sur une parcelle. Les chiffres restaient arithmétiquement
justes mais vides de sens (charge jusqu'à 183,9 M€, marge −115 M€…+85 M€). Un seul seuil, un seul
libellé, lus par score_e (source), la fiche, le Bilan et les exports.
"""
from __future__ import annotations

#: 2 ha — au-delà, pas d'estimation promoteur (opération d'aménagement).
SEUIL_AMENAGEMENT_M2 = 20_000

LIBELLE_AMENAGEMENT = "Opération d'aménagement : hors estimation promoteur"
DETAIL_AMENAGEMENT = (
    "Terrain supérieur à 2 ha : c'est une opération d'AMÉNAGEMENT (lotissement, ZAC, division "
    "foncière), pas une promotion sur une parcelle. Le bilan promoteur à rebours (marge, charge "
    "foncière supportable) n'a pas de sens métier à cette échelle — non estimé.")


def est_amenagement(surface_terrain_m2: float | int | None) -> bool:
    """True si la surface de terrain dépasse le seuil d'aménagement (2 ha)."""
    return bool(surface_terrain_m2 and surface_terrain_m2 > SEUIL_AMENAGEMENT_M2)
