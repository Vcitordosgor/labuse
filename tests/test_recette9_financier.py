"""RECETTE-9 T1 — le Dossier financier redevient accessible sur une parcelle SANS potentiel.

Le bug : sur une parcelle « faible / nul » (potentiel proche/atteint de la densité autorisée),
`capacite_estimee` est FAUX → le programme constructible n'est chiffrable QUE si le porteur
saisit un nombre de logements. Or ce champ n'était pas marqué indispensable, et le blocage
« Programme constructible » ne tombait qu'À L'ARRIVÉE du document (jamais au moment de la saisie).
On teste la logique qui décide quand ce champ devient indispensable, et la présence des manques.
"""
from __future__ import annotations

from labuse import financier_questionnaire as qf


# ── T1 défaut n°1/n°2 : le champ qui débloque le programme est marqué indispensable au bon moment ──

def test_programme_depuis_potentiel_vrai_si_capacite():
    assert qf.programme_depuis_potentiel({"capacite_estimee": True}) is True
    assert qf.programme_depuis_potentiel({"capacite_estimee": 8}) is True


def test_programme_depuis_potentiel_faux_sans_capacite():
    # parcelle à sa densité (recette : « Potentiel faible / Densité atteinte »)
    assert qf.programme_depuis_potentiel({"capacite_estimee": False}) is False
    assert qf.programme_depuis_potentiel({"capacite_estimee": None}) is False
    assert qf.programme_depuis_potentiel({}) is False
    assert qf.programme_depuis_potentiel(None) is False


def test_logements_indispensable_seulement_sans_potentiel():
    # avec potentiel : rien de plus à saisir (le potentiel chiffre le programme)
    assert qf.obligatoires_programme({"capacite_estimee": True}) == set()
    # sans potentiel : le nombre de logements DÉBLOQUE le programme → indispensable
    assert qf.obligatoires_programme({"capacite_estimee": False}) == {"logements_vises_saisi"}


def test_manques_programme_puis_debloque_par_logements():
    """Le constat de la recette, en test : sans surface vendable → « Programme constructible » ;
    dès que le programme a une surface (logements × typologie l'a produite) → plus de manque."""
    plein = {"prix_sortie_saisi_eur_m2": {"valeur": 4500}, "regime_tva_saisi": {"valeur": "x"}}
    bloque = qf.manques(plein, {"surface_vendable": None})
    assert any(m["libelle"] == "Programme constructible" for m in bloque)
    ok = qf.manques(plein, {"surface_vendable": 480})
    assert ok == []
