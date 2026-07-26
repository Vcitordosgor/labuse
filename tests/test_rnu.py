"""MANDAT RNU — tests du flag commune-level et de l'étiquetage produit.

Couvre : (1) config chargée + Saint-Philippe flaggée + généralité (le flag suit le yaml,
pas un INSEE codé en dur) ; (2) helpers insee/idu ; (3) bloc d'étiquetage (wording
doctrinal exact, jamais d'affirmation de constructibilité) ; (4) hors commune RNU → None.
"""
from __future__ import annotations

from labuse import rnu


def setup_function(_f):
    rnu.clear_cache()


def test_saint_philippe_flaggee_et_generalite():
    assert rnu.is_rnu_insee("97417") is True
    assert rnu.is_rnu_insee("97415") is False          # Saint-Paul a un PLU
    assert rnu.is_rnu_idu("97417000AC0003") is True
    assert rnu.is_rnu_idu("97415000DK1044") is False
    assert rnu.is_rnu_idu(None) is False and rnu.is_rnu_insee("") is False


def test_generalite_le_flag_suit_le_yaml(monkeypatch):
    # mandat C : ajouter une commune = une entrée yaml, AUCUN code — prouvé en simulant
    monkeypatch.setattr(rnu, "load_yaml_config", lambda _n: {
        "communes": [{"insee": "97413", "nom": "Saint-Leu", "verifie_le": "2027-01-01"}]})
    rnu.clear_cache()
    assert rnu.is_rnu_insee("97413") is True            # PLU annulé hypothétique → RNU
    assert rnu.is_rnu_insee("97417") is False           # plus au yaml → plus flaggée


def test_bloc_etiquetage_wording_doctrinal():
    b = rnu.rnu_block("97417000AC0003")
    assert b is not None
    assert b["libelle"] == "Commune au règlement national d'urbanisme — pas de PLU local"
    assert "parties actuellement urbanisées" in b["detail"]
    assert b["commune_nom"] == "Saint-Philippe" and b["verifie_le"] == "2026-07-26"
    # jamais une affirmation de constructibilité
    texte = (b["libelle"] + " " + b["detail"]).lower()
    assert "constructible" not in texte.replace("constructibilité limitée", "")
    assert rnu.rnu_block("97415000DK1044") is None
