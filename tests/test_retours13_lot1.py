"""RETOURS-13 Lot 1 — les tests qui auraient attrapé les défauts R4 / R6 / R9.

R6 : le repli d'ingestion envoyait ELEVE et TRES_ELEVE sur « moyen » — les 484 zones de
mouvement de terrain LES PLUS GRAVES étaient servies comme moyennes, jamais de rouge à l'écran.
R4 : la moyenne tension (ligne_mt, EDF open data) doit être servie par l'endpoint couches.
R9 : la bulle d'un arrêt a besoin des NOMS de lignes (lignes_noms), pas d'un route_id opaque.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.layers_ingest import _classe_alea, _normalise_alea

pytestmark = pytest.mark.db


# ── R6 — mapping des degrés réels (mesurés en base le 05/09/2026) ──────────────────────────

def test_r6_degres_graves_ne_sont_plus_ecrases():
    # AVANT : ELEVE/TRES_ELEVE → « moyen » (aucun mot-clé reconnu). APRÈS : classe grave.
    assert _normalise_alea("ELEVE") == ("fort", False)
    assert _normalise_alea("TRES_ELEVE") == ("fort", False)
    assert _classe_alea("ELEVE") == "eleve"
    assert _classe_alea("TRES_ELEVE") == "tres_eleve"


def test_r6_classes_affichage_couvrent_les_8_libelles_reels():
    attendus = {
        "FAIBLE": "faible", "FAIBLE_A_MODERE": "faible",
        "MODERE": "moyen", "MOYEN": "moyen", "MOYEN_B2U": "moyen", "MOYEN_SECURISABLE": "moyen",
        "ELEVE": "eleve", "TRES_ELEVE": "tres_eleve",
    }
    for degre, classe in attendus.items():
        assert _classe_alea(degre) == classe, degre
    # inondation : le triptyque officiel reste
    for degre, classe in {"FAIBLE": "faible", "MOYEN": "moyen", "FORT": "fort"}.items():
        assert _classe_alea(degre) == classe


