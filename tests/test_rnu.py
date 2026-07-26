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


# ───────────── PAU + plancher C (méthode VALIDÉE Vic 26/07/2026) ─────────────

def test_pau_params_depuis_config():
    p = rnu.pau_params()
    assert p == {"eps_m": 50.0, "min_batiments": 10, "buffer_m": 40.0, "critere": "centre"}


def test_pau_params_refus_si_invalide(monkeypatch):
    monkeypatch.setattr(rnu, "load_yaml_config", lambda _n: {"pau": {"eps_m": 50}})
    import pytest
    with pytest.raises(ValueError, match="incomplet"):
        rnu.pau_params()


def test_avertissement_pau_wording_exact():
    # wording VALIDÉ Vic — toute reformulation casse ce test volontairement
    assert rnu.AVERTISSEMENT_PAU == (
        "Enveloppe urbanisée estimée par LABUSE — la délimitation des parties "
        "actuellement urbanisées relève de l'appréciation du service instructeur.")
    assert rnu.NON_APPLICABLE_RNU == "non applicable — RNU"
    b = rnu.rnu_block("97417000AC0003")
    assert b["avertissement_pau"] == rnu.AVERTISSEMENT_PAU and b["dans_pau"] is None


def test_plancher_c_branche_rnu():
    import pandas as pd
    from labuse.scoring.p_v2.statuts import TierParams, plancher_c
    params = TierParams(n_entree=10, n_sortie=14)
    df = pd.DataFrame({
        "sdp_residuelle_m2": [0, 0, 0, 0, 500],
        "surface_m2":        [800, 800, 400, 800, 100],
        "zone_plu":          ["inconnu", "inconnu", "inconnu", "U", "N"],
        "dans_pau":          [True, False, True, False, False],
    })
    r = plancher_c(df, params)
    assert list(r) == [True,   # RNU : dans PAU ∧ ≥600 → éligible
                       False,  # RNU : hors PAU → non
                       False,  # RNU : dans PAU mais 400 < 600 → non (MÊME seuil que partout)
                       True,   # commune à PLU : comportement INCHANGÉ (U ∧ ≥600)
                       True]   # SDP > 0 : inchangé
    # colonne absente = comportement d'avant à l'identique (aucune régression possible)
    r2 = plancher_c(df.drop(columns=["dans_pau"]), params)
    assert list(r2) == [False, False, False, True, True]
