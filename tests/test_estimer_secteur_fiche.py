"""CHIRURGICAL-FIX-1 (LOT F, E8) — le PRIX DE SECTEUR affiché par Estimer est celui de la FICHE
(`prix_ancien`), et le chiffre propre à ESTIMER-3 est NOMMÉ « estimation du prix de ce bien », jamais
« le prix du secteur » (deux documents LABUSE ne montrent plus deux prix de secteur différents)."""
from labuse.exports.blocs.annonce import _estimation, _int


def _est(**extra):
    base = {"median": 2652, "q1": 1862, "q3": 4952, "n": 28, "radius_m": 500,
            "type_bien": "maison", "type_label_pluriel": "maisons", "periode": [2022, 2025],
            "precision_pct": 32,
            # le prix de secteur = celui de la fiche (ici 2 333, 43 ventes) — distinct de l'estimation 2 652.
            "secteur_fiche": {"median": 2333, "n": 43, "radius_m": 500, "type_prix": "maison",
                              "periode": [2022, 2026]}}
    base.update(extra)
    return base


def test_estimer_affiche_le_prix_de_secteur_de_la_fiche():
    html = _estimation(_est())
    # le prix de secteur montré = la médiane de la FICHE (2 333), pas l'estimation ESTIMER-3 (2 652)
    assert "Prix médian du secteur (fiche)" in html
    assert f"{_int(2333)} €/m²" in html and "43 vente" in html
    # l'estimation ESTIMER-3 est nommée « ce bien », jamais « le prix du secteur »
    assert "Prix estimé au m² — ce bien" in html
    assert "estimation du prix de ce bien" in html
    assert "ce n'est pas le prix médian du secteur" in html


def test_sans_secteur_fiche_pas_de_ligne_secteur():
    # robustesse : si la fiche ne sert pas de médiane de secteur, aucune ligne secteur n'est inventée.
    html = _estimation(_est(secteur_fiche=None))
    assert "Prix médian du secteur (fiche)" not in html
    assert "Prix estimé au m² — ce bien" in html   # l'estimation reste nommée
