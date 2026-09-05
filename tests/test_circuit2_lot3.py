"""CIRCUIT-2 lot 3 — un concept, une source : jamais le même libellé pour deux origines,
le document des canoniques existe et couvre les concepts du mandat, les « i » des couches
équipements disent qui nourrit quoi (BPE → fiche, OSM → modèle)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from labuse.registre.donnees import DONNEES

RACINE = Path(__file__).resolve().parents[1]


def test_jamais_le_meme_libelle_pour_deux_origines():
    doubles = {k: v for k, v in Counter(d.libelle for d in DONNEES.values()).items() if v > 1}
    assert doubles == {}, doubles


def test_concepts_canoniques_couvre_le_mandat():
    doc = (RACINE / "docs/CIRCUIT/CONCEPTS-CANONIQUES.md").read_text()
    for concept in ("Zonage PLU", "Aléas & PPR", "50 pas", "Permis", "Prix", "SDP",
                    "Division", "DPE", "Propriétaire", "Transport", "Équipements",
                    "Population", "Réseaux", "Solaire", "Occupation du sol", "Friches"):
        assert concept in doc, concept
    assert "retiree" in doc and "rien n'est retiré sans Vic" in doc.lower() or \
        "aucune ligne ne l'est ici" in doc


def test_i_des_couches_equipements_coherents():
    """Le doublon d'affirmation corrigé au lot 3 : la fiche « À proximité » vient de la BPE
    (RETOURS-7 Z5) ; le « i » OSM ne prétend plus l'alimenter."""
    layers = (RACINE / "frontend/src/lib/layers.ts").read_text()
    assert "C’est cette couche OSM qui alimente les distances" not in layers
    assert "nourrissent le MODÈLE LABUSE" in layers
    assert "C’est la BPE qui nourrit la ligne « À proximité »" in layers
