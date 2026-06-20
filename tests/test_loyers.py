"""Carte des loyers DHUP (LOT 4-B) — marché locatif sur source ouverte, jamais inventé.

Vérifie l'extrait La Réunion (24 communes), les valeurs réelles Saint-Paul, la règle NA→None,
la fiabilité par granularité (commune vs maille) et le bloc fiche.
"""
from __future__ import annotations

from labuse import loyers


def test_extrait_reunion_24_communes():
    communes = loyers.load().get("communes")
    assert communes and len(communes) == 24
    assert all(c["insee"].startswith("974") for c in communes)


def test_source_sourcee_millesime():
    s = loyers.source()
    assert s["provenance"] == "sourcee"
    assert s["millesime"] == "2025"
    assert "DHUP" in s["producteur"]


def test_saint_paul_valeurs_reelles():
    """Valeurs réellement extraites de la carte des loyers 2025 (aucun chiffre fabriqué)."""
    rec = loyers.get_loyers(insee="97415")
    assert rec is not None and rec["commune"] == "Saint-Paul"
    assert rec["appartement"]["loyer_m2"] == 18.86
    assert rec["maison"]["loyer_m2"] == 15.57
    assert rec["appartement"]["type_prediction"] == "commune"


def test_lookup_par_insee_et_par_nom():
    a = loyers.get_loyers(insee="97415")
    b = loyers.get_loyers(commune="saint paul")          # tolérant accents/casse
    assert a and b and a["insee"] == b["insee"] == "97415"


def test_fiche_block_saint_paul():
    b = loyers.fiche_block(insee="97415", commune="Saint-Paul")
    assert b is not None
    assert b["appartement"]["loyer_m2"] == 18.86
    assert b["appartement"]["fiabilite"] == "bonne"       # estimation à l'échelle communale
    assert b["appartement"]["maille_elargie"] is False
    assert b["maison"]["loyer_m2"] == 15.57
    assert "Carte des loyers 2025" in b["source"]["mention"]


def test_fiabilite_maille_signalee():
    """Au moins une commune 974 est estimée sur une maille élargie → fiabilité « moyenne » signalée."""
    mailles = [
        c for c in loyers.load()["communes"]
        if (c.get("appartement") or {}).get("type_prediction") == "maille"
    ]
    assert mailles, "le dataset doit conserver l'info de granularité"
    seg = loyers._segment(mailles[0]["appartement"])
    assert seg["fiabilite"] == "moyenne" and seg["maille_elargie"] is True


def test_commune_hors_reunion_renvoie_none():
    assert loyers.get_loyers(insee="75056") is None       # Paris hors extrait 974
    assert loyers.fiche_block(insee="75056", commune="Paris") is None
