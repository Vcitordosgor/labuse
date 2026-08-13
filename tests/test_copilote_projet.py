"""M78 · 3b — la fiche de cadrage construite par le Copilote depuis le brief (vocabulaire fermé
FICHE_SCHEMA). Pur + déterministe. Le roundtrip champ-à-champ complet (créer par Copilote → lire par
l'API projets → comparer) est dans qa/m78/demo_phase3.py (modèle réel)."""
from jsonschema import validate

from labuse.api.projet_schema import FICHE_SCHEMA
from labuse.copilote_v2.missions_lourdes import preparer_projet


def test_preparer_projet_construit_une_fiche_conforme():
    act = preparer_projet({"programme_logements": 12, "commune": "Bras-Panon",
                           "budget_eur": 600000, "idu": "97403000AB0001"},
                          "j'ai un projet : résidence 12 logements à Bras-Panon")
    fiche = act["fiche"]
    validate(fiche, FICHE_SCHEMA)                          # vocabulaire fermé respecté
    assert fiche["ampleur"]["logements"] == 12
    assert fiche["perimetre"] == {"mode": "communes", "communes": ["Bras-Panon"]}
    assert fiche["budget_foncier_eur"] == 600000.0
    assert act["idu"] == "97403000AB0001"                 # parcelle citée → à attacher au projet


def test_preparer_projet_minimal_reste_conforme():
    act = preparer_projet({"programme_logements": 30}, "projet 30 logements")
    validate(act["fiche"], FICHE_SCHEMA)
    assert act["fiche"]["ampleur"]["logements"] == 30
    assert "perimetre" not in act["fiche"]                # rien d'inventé (pas de commune → pas de périmètre)
