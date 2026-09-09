"""RECETTE-8 W14 — la règle d'accord singulier/pluriel des équipements de proximité.

Le bug : « 1 bu » (le « s » de « bus », invariable, était mangé par un rstrip('s') naïf).
On teste chaque catégorie servie (api.app._PROX_EQUIP) à 0, 1 et 2.
"""
from __future__ import annotations

import pytest

from labuse.exports.blocs.autour import _EQUIP_ACCORD, _accord

CATS = ["École", "Commerces", "Santé", "Bus"]


@pytest.mark.parametrize("cat", CATS)
def test_categorie_connue_du_registre_daccord(cat):
    assert cat in _EQUIP_ACCORD, f"{cat} n'a pas de forme singulier/pluriel déclarée"


@pytest.mark.parametrize("cat", CATS)
@pytest.mark.parametrize("n", [0, 1, 2])
def test_accord_a_0_1_2(cat, n):
    sing, plur = _EQUIP_ACCORD[cat]
    attendu = f"{n} {sing if n <= 1 else plur}"
    assert _accord(cat, n) == attendu


def test_bus_ne_perd_jamais_son_s():
    # le bug historique : « 1 bu ». « bus » est invariable.
    assert _accord("Bus", 1) == "1 arrêt de bus"
    assert _accord("Bus", 2) == "2 arrêts de bus"
    assert "bu " not in _accord("Bus", 1) + " " and _accord("Bus", 1).split()[1].startswith("arrêt")


def test_commerces_singularise_bien():
    assert _accord("Commerces", 1) == "1 commerce"
    assert _accord("Commerces", 3) == "3 commerces"


# ── RECETTE-8 W13bis (C3) — le calcul de marge « Revente en l'état » ──────────────────────────

def test_calculer_revente_marge_et_taux():
    from labuse.exports.financier_bilan import calculer_revente
    r = calculer_revente({"prix_achat": 250000, "prix_revente": 340000, "frais_acq_pct": 8,
                          "travaux": 20000, "duree_portage": 12, "taux_apport": 4})
    # 250000 + 20000 (frais 8%) + 20000 (travaux) + 10000 (portage 4%×12/12) = 300000
    assert r["etablissable"] and r["cout_total"] == 300000.0
    assert r["marge"] == 40000.0 and r["taux_marge_pct"] == 11.8 and r["maximum"] is False


def test_calculer_revente_sans_portage_est_maximum():
    from labuse.exports.financier_bilan import calculer_revente
    r = calculer_revente({"prix_achat": 200000, "prix_revente": 250000, "frais_acq_pct": 7})
    assert r["etablissable"] and r["maximum"] is True   # pas de taux/durée → portage non chiffré
    assert r["marge"] == 250000 - 200000 - 14000  # 36000


def test_calculer_revente_non_etablissable_sans_prix():
    from labuse.exports.financier_bilan import calculer_revente
    assert calculer_revente({"prix_achat": 200000})["etablissable"] is False
    assert calculer_revente({"prix_revente": 300000})["etablissable"] is False


def test_usage_revente_obligatoires():
    from labuse import financier_questionnaire as qf
    assert qf.usage_choisi({"_usage": "revente"}) == "revente"
    assert qf.usage_choisi({}) == "construction"
    # complet en revente ssi achat + revente saisis
    assert not qf.est_complet({"_usage": "revente", "prix_achat_revente_saisi_eur": 200000})
    assert qf.est_complet({"_usage": "revente", "prix_achat_revente_saisi_eur": 200000,
                           "prix_revente_saisi_eur": 300000})
