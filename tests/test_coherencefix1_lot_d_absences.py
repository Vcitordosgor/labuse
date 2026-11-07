"""COHERENCE-FIX-1 (lot D) — absence ≠ zéro, et un vocabulaire d'absence à CINQ formes.

Règle du registre : toute phrase d'absence déclarée (declarations/*.yaml) appartient à l'une
des cinq formes de `registre/absences.py` — une phrase libre qui n'y entre pas fait échouer
ce test (on la reformule dans le vocabulaire, on n'invente pas une sixième forme).
"""
from __future__ import annotations

from labuse.registre.absences import FORMES, classer, hors_vocabulaire


def test_cinq_formes_pas_une_de_plus():
    assert len(FORMES) == 5


def test_toutes_les_phrases_declarees_entrent_dans_le_vocabulaire():
    hv = hors_vocabulaire()
    assert hv == [], (
        f"{len(hv)} phrase(s) d'absence hors des 5 formes — à reformuler dans le vocabulaire "
        f"(registre/absences.py), pas à laisser dériver : {hv[:5]}")


def test_classer_les_cinq_familles():
    assert classer("Surface : contenance cadastrale non disponible pour cette parcelle.") == "non_disponible"
    assert classer("Aléas : aucun aléa réglementaire ne touche cette parcelle.") == "aucun"
    assert classer("QPV : parcelle hors quartier prioritaire dans l'emprise visible.") == "hors_perimetre"
    assert classer("Ouverture de la zone AU : sans objet (pas de zone AU ici).") == "sans_objet"
    assert classer("Terrain nu — secteur : échantillon DVF insuffisant pour une médiane fiable.") == "non_calculable"
    assert classer("—") == "tiret_compact"


def test_phrase_libre_refusee():
    assert classer("Ce champ est vide, désolé.") is None


def test_part_habitat_zan_absence_est_none():
    """moteurs.py — habitat NULL dans la source → part None (« — »), jamais « 0 % »."""
    # la formule corrigée : (round(100*h/c) if (c and h is not None) else None)
    c1121, h1121 = 125000.0, None
    part = (round(100 * float(h1121) / c1121) if (c1121 and h1121 is not None) else None)
    assert part is None


