"""SOURCES-3 lot 4 — le garde-fou 974 commun à toute ingestion à maille adresse/parcelle/bâtiment.

Invariant DUR : le code postal SEUL ne suffit pas. Le garde croise CP + commune + coordonnées et
rejette dès que les critères présents ne confirment pas TOUS La Réunion. Cas d'école : les 75 DPE
de Saint-Leu-la-Forêt (Val-d'Oise) portant un CP réunionnais (97436) DOIVENT être rejetés — sinon
un bien de métropole s'épingle sur une parcelle réunionnaise.
"""
from __future__ import annotations

from labuse.ingestion.garde_974 import COMMUNES_24_FOLD, _fold, verifier_974


def test_saint_leu_la_foret_est_rejete():
    """Le cas qui a fuité : CP 974 ✓ + commune « ST LEU » ✓ MAIS coordonnées Val-d'Oise ✗.
    Les coordonnées contredisent → rejet, quoi qu'en disent le CP et la commune."""
    v = verifier_974(cp="97436", commune="ST LEU", lon=2.253, lat=49.017)
    assert v.ok is False
    assert v.coords_ok is False and v.cp_ok is True and v.commune_ok is True
    assert "hors emprise" in v.raison


def test_reunion_legitime_passe():
    v = verifier_974(cp="97436", commune="Saint-Leu", lon=55.29, lat=-21.17)
    assert v.ok is True


def test_metropole_coordonnees_rabattues_est_rejete():
    """Les 900 DPE métropolitains : CP + commune métropolitains, mais BAN a rabattu les coordonnées
    sur l'île. CP et commune contredisent → rejet (les coordonnées seules ne sauvent pas)."""
    v = verifier_974(cp="62200", commune="Boulogne-sur-Mer", lon=55.45, lat=-20.9)
    assert v.ok is False
    assert v.cp_ok is False and v.commune_ok is False


def test_cedex_reunionnais_977_passe():
    """La mairie de Saint-Denis porte le CEDEX 97717 (977xx) : réunionnais, jamais rejeté."""
    v = verifier_974(cp="97717", commune="Saint-Denis")
    assert v.ok is True and v.cp_ok is True


def test_cp_et_commune_seuls_coherents_passent():
    """Sans coordonnées, CP 974 + commune des 24 cohérents → passe (la maille adresse n'a pas
    toujours de point ; deux critères concordants suffisent)."""
    v = verifier_974(cp="97430", commune="Le Tampon")
    assert v.ok is True


def test_deux_criteres_sur_trois_contredisent_rejet():
    """CP 974 mais commune hors des 24 ET coordonnées hors emprise : deux critères contredisent."""
    v = verifier_974(cp="97400", commune="Paris", lon=2.35, lat=48.85)
    assert v.ok is False


def test_normalisation_commune():
    assert _fold("ST LEU") == "saint leu"
    assert _fold("Ste-Marie") == "sainte marie"
    assert _fold("L'Étang-Salé") == "l etang sale"
    assert _fold("Saint-Leu") in COMMUNES_24_FOLD
    assert _fold("Saint-Leu-la-Forêt") not in COMMUNES_24_FOLD   # l'homonyme de métropole n'y est pas


def test_verdict_porte_les_trois_valeurs():
    """La ligne rejetée est journalisable avec ses trois valeurs (CP, commune, coordonnées)."""
    v = verifier_974(cp="97436", commune="ST LEU", lon=2.253, lat=49.017)
    assert v.cp == "97436" and v.commune == "ST LEU" and v.lon == 2.253 and v.lat == 49.017
