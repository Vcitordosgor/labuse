"""FRAICHEUR-FIX-1 (point 5) — les 3 couches OSM : sonde live Overpass RETIRÉE (aucun endpoint fiable
depuis le VPS), REMPLACÉE par un rappel de fraîcheur du snapshot ingéré (jamais 16-18 injoignable)."""
from labuse import sentinelle

_OSM = {"Parkings OSM (loi APER)",
        "OSM — transport (pôles d'échange & téléphérique)",
        "TCSP — voies bus en site propre (OSM)"}


def test_osm_plus_de_sonde_live_overpass():
    seed = {e["name"] for e in sentinelle.SEED}
    assert not (_OSM & seed), "aucune couche OSM ne doit garder une sonde live Overpass dans le SEED"
    # plus aucune URL overpass-api.de dans le SEED (fin des 16-18 injoignable)
    assert not any("overpass" in (e.get("url") or "").lower() for e in sentinelle.SEED)


def test_osm_surveillees_par_rappel_de_fraicheur():
    rappels = {r["name"]: r for r in sentinelle.RAPPELS_MANUELS}
    for nom in _OSM:
        assert nom in rappels, f"{nom} doit être surveillée par un rappel de fraîcheur"
        assert rappels[nom]["cadence_jours"] == 180
        assert nom in sentinelle.RAISONS_NON_SURVEILLEES  # la raison documente le remplacement
