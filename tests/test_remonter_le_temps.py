"""3.B — Photos aériennes historiques : lien « Remonter le temps » (IGN).

Recette : le lien ouvre la BONNE localisation (lon/lat de la parcelle) et un millésime
historique COUVRANT La Réunion. Pur, sans I/O ni DB.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from labuse.api.enrichment import remonter_le_temps


def test_url_porte_la_bonne_localisation():
    """lon/lat de la parcelle se retrouvent (à 1e-6) dans l'URL, centrée et zoomée."""
    r = remonter_le_temps(55.270123, -21.009876)
    assert r["available"] is True
    u = urlparse(r["url"])
    assert u.netloc == "remonterletemps.ign.fr" and u.path == "/comparer"
    q = parse_qs(u.query)
    assert float(q["lon"][0]) == 55.270123
    assert float(q["lat"][0]) == -21.009876
    assert int(q["z"][0]) >= 15            # assez zoomé pour voir la parcelle


def test_millesime_historique_couvre_la_reunion():
    """layer2 = un millésime national qui COUVRE La Réunion (1950-1965, vérifié dispo)."""
    r = remonter_le_temps(55.27, -21.01)
    q = parse_qs(urlparse(r["url"]).query)
    assert q["layer1"][0] == "ORTHOIMAGERY.ORTHOPHOTOS"          # ortho actuelle
    assert q["layer2"][0] == "ORTHOIMAGERY.ORTHOPHOTOS.1950-1965"  # historique, couvre 974
    assert q["mode"][0] == "doubleMap"                          # comparateur côte à côte


def test_centroide_absent_pas_de_lien_invente():
    """Sans centroïde → available=False (on n'invente pas une localisation)."""
    assert remonter_le_temps(None, None)["available"] is False
    assert remonter_le_temps(55.0, None)["available"] is False
