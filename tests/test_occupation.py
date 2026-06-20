"""Statut d'occupation INSEE RP 2022 (LOT 4-B) — données réellement extraites, jamais inventées."""
from __future__ import annotations

from labuse import occupation


def test_extrait_reunion_non_vide():
    communes = occupation.load().get("communes")
    assert communes, "l'extrait doit contenir au moins Saint-Paul"
    assert all(c["insee"].startswith("974") for c in communes)


def test_source_sourcee_insee_2022():
    s = occupation.source()
    assert s["provenance"] == "sourcee"
    assert s["millesime"] == "2022"
    assert "INSEE" in s["producteur"]


def test_saint_paul_valeurs_reelles():
    """Valeurs exactes du Dossier complet INSEE RP 2022 pour Saint-Paul (aucun chiffre fabriqué)."""
    r = occupation.get_occupation(insee="97415")
    assert r is not None and r["commune"] == "Saint-Paul"
    assert r["ensemble"]["n"] == 41610
    assert r["proprietaire"] == {"n": 25666, "pct": 61.7}
    assert r["locataire"] == {"n": 14364, "pct": 34.5}
    assert r["dont_hlm"] == {"n": 4670, "pct": 11.2}
    assert r["loge_gratuit"] == {"n": 1580, "pct": 3.8}


def test_coherence_somme():
    """Propriétaires + locataires + logés gratuits ≈ ensemble (cohérence du tableau source)."""
    r = occupation.get_occupation(insee="97415")
    total = r["proprietaire"]["n"] + r["locataire"]["n"] + r["loge_gratuit"]["n"]
    assert abs(total - r["ensemble"]["n"]) <= 2   # arrondis INSEE


def test_lookup_par_nom():
    a = occupation.get_occupation(insee="97415")
    b = occupation.get_occupation(commune="saint paul")
    assert a and b and a["insee"] == b["insee"] == "97415"


def test_fiche_block_saint_paul():
    b = occupation.fiche_block(insee="97415", commune="Saint-Paul")
    assert b is not None
    assert b["proprietaire"]["pct"] == 61.7
    assert b["locataire"]["pct"] == 34.5
    assert "Recensement de la population 2022" in b["source"]["mention"]


def test_commune_hors_extrait_none():
    assert occupation.get_occupation(insee="75056") is None
    assert occupation.fiche_block(insee="75056", commune="Paris") is None
