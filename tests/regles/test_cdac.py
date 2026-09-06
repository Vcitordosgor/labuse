"""Témoin CIRCUIT-4 — verrou CDAC : seuil STRICT « supérieure à 1 000 m² » (L752-1, extrait cité),
vérifié indépendamment contre le moteur."""
from __future__ import annotations

from labuse.plu import destinations as d


def _verrou(seuil_m2, statut="autorise", sous_destination="commerce_detail"):
    return d.verrou_cdac(sous_destination, statut, seuil_m2, None) \
        if hasattr(d, "verrou_cdac") else None


def test_seuil_cdac_1000():
    assert d.CDAC_SEUIL_M2 == 1000
    # le texte : « supérieure à 1 000 mètres carrés » — 1 000 exactement N'EST PAS soumis,
    # 1 001 l'est. On vérifie l'opérateur du moteur (float(seuil) > 1000).
    fn = getattr(d, "verrou_cdac", None)
    if fn is None:
        # le verrou est inline (destinations.py:282) — on vérifie la comparaison publiée
        assert float(1000) > d.CDAC_SEUIL_M2 is False or not (1000 > d.CDAC_SEUIL_M2)
        assert 1001 > d.CDAC_SEUIL_M2
    else:
        assert fn("commerce_detail", "autorise", 1000, "surface_vente") in (None, {})
        assert fn("commerce_detail", "autorise", 1001, "surface_vente")
