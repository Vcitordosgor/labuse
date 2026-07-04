"""Résolution commune CLI (LIVRABLE 3, refonte étage 0) — pur, sans DB.

Le bug historique : un INSEE non-pilote était renvoyé BRUT comme nom → 0 parcelle en silence.
`_resolve_commune` doit résoudre tout INSEE (pilote ou non) vers le NOM officiel des 24 communes.
Le garde-fou « 0 parcelle → échec bruyant » (evaluate/discover) est vérifié en revue (dépend DB).
"""
from labuse.cli import _resolve_commune


def test_none_donne_la_commune_pilote():
    assert _resolve_commune(None) == "Saint-Paul"


def test_insee_pilote_resolu_en_nom():
    assert _resolve_commune("97415") == "Saint-Paul"


def test_nom_passe_tel_quel():
    assert _resolve_commune("Saint-Paul") == "Saint-Paul"


def test_insee_non_pilote_resolu_en_nom():
    # Cœur du bug : un INSEE non-pilote ne doit PLUS être renvoyé brut, mais résolu.
    assert _resolve_commune("97408") == "La Possession"


def test_insee_inconnu_renvoye_brut_pour_echec_bruyant_en_aval():
    # INSEE hors référentiel : renvoyé tel quel → 0 parcelle → _fail_zero_parcel (échec bruyant).
    assert _resolve_commune("99999") == "99999"
