"""ÉTUDE DE ZONE · Z2 — le moteur de zone. On gèle les doctrines du mandat :

  · CACHE d'isochrone : une zone demandée deux fois ne rappelle PAS l'API.
  · Échec API → dégradé HONNÊTE et NOMMÉ (statut 'indisponible', geom None) — JAMAIS un cercle en silence.
  · UN SEUL point de calcul Filosofi (population_zone) : carreaux dont le centroïde est dans la zone.
  · Les « plus proches » portent leur TEMPS (plus petite bande d'isochrone), jamais des mètres.

Données de test créées puis PURGÉES (préfixes/valeurs dédiés).
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse import zone as Z
from labuse.db import session_scope

pytestmark = pytest.mark.db

# point d'ancrage (Saint-André, La Réunion) et deux carrés isochrones concentriques (4326).
_LON, _LAT = 55.6500, -20.9600


def _carre(demi: float) -> dict:
    """Polygone GeoJSON carré de demi-côté `demi` degrés, centré sur l'ancrage."""
    x0, x1, y0, y1 = _LON - demi, _LON + demi, _LAT - demi, _LAT + demi
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def _fake_fetch_factory(geom, compteur):
    def _fetch(lon, lat, minutes, mode, *, client):
        compteur.append((minutes, mode))
        return geom
    return _fetch


def test_isochrone_cache_ne_rappelle_pas_l_api():
    petit = _carre(0.01)
    calls: list = []
    with session_scope() as s:
        Z.ensure_tables(s)
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE lon = :lon"), {"lon": _LON})
        r1 = Z.isochrone(s, _LON, _LAT, 5, "voiture", fetch=_fake_fetch_factory(petit, calls))
        r2 = Z.isochrone(s, _LON, _LAT, 5, "voiture", fetch=_fake_fetch_factory(petit, calls))
    assert r1["statut"] == "ign" and r1["geom_geojson"]["type"] == "Polygon"
    assert r2["statut"] == "cache", "seconde demande servie par le CACHE"
    assert len(calls) == 1, "l'API n'est appelée qu'UNE fois (la 2ᵉ vient du cache)"
    with session_scope() as s:
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE lon = :lon"), {"lon": _LON})


def test_isochrone_echec_api_degrade_honnete_jamais_un_cercle():
    def _boom(lon, lat, minutes, mode, *, client):
        raise RuntimeError("503 Service Unavailable")
    with session_scope() as s:
        Z.ensure_tables(s)
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE lon = :lon"), {"lon": _LON})
        r = Z.isochrone(s, _LON, _LAT, 5, "voiture", fetch=_boom)
    assert r["statut"] == "indisponible", "échec NOMMÉ, pas silencieux"
    assert r["geom_geojson"] is None, "aucune géométrie substituée — JAMAIS un cercle inventé"
    assert "indisponible" in r["detail"]


def test_population_zone_point_unique_filosofi():
    zone = _carre(0.02)
    age_cols = ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17", "ind_18_24"]
    with session_scope() as s:
        for c in age_cols:
            s.execute(text(f"ALTER TABLE filosofi_carreaux_200m ADD COLUMN IF NOT EXISTS {c} double precision"))
        # deux carreaux DANS la zone (centroïde), un carreau LOIN (hors zone)
        for i, (lon, lat, ind) in enumerate([(_LON, _LAT, 100.0), (_LON + 0.001, _LAT, 60.0),
                                             (_LON + 5, _LAT, 999.0)]):
            s.execute(text(
                "INSERT INTO filosofi_carreaux_200m (geom, ind, men, men_pauv, men_prop, ind_snv, "
                " ind_0_3, ind_4_5, ind_6_10, ind_11_17, ind_18_24) VALUES ("
                " ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2975), :ind, :men, :mp, 5, "
                " :snv, :a, :a, :a, :a, :a)"),
                {"lon": lon, "lat": lat, "ind": ind, "men": ind / 2, "mp": ind / 20,
                 "snv": ind * 20000, "a": ind / 25})
        pop = Z.population_zone(s, zone)
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE men_prop = 5 AND ind IN (100, 60, 999)"))
    assert pop["inhabitee"] is False
    assert pop["habitants"] == 160, "seuls les 2 carreaux dont le centroïde est DANS la zone comptent (100+60)"
    assert pop["n_carreaux"] == 2
    assert pop["revenu_estime"] is True, "revenu toujours ESTIMÉ (INSEE lissé)"
    assert pop["revenu_median_eur"] == 20000
    # % < 25 = (5 tranches × ind/25) / ind = 5/25 = 20 %
    assert pop["pct_moins_25"] == 20


def test_population_zone_inhabitee_reste_digne():
    with session_scope() as s:
        pop = Z.population_zone(s, _carre(0.02))   # aucun carreau de test → zone inhabitée
    assert pop["inhabitee"] is True
    assert "millesime" in pop
    assert "habitants" not in pop, "zone sans population : aucun chiffre inventé"


def test_concurrents_portent_leur_temps_pas_des_metres():
    bandes = {2: _carre(0.005), 6: _carre(0.02)}   # bande 2 min (petit) ⊂ bande 6 min (grand)
    zone = _carre(0.05)
    with session_scope() as s:
        Z.ensure_tables(s)
        from labuse.ingestion.sirene_etablissements import ensure_tables as se_ens
        se_ens(s)
        # A : dans la bande 2 min · B : seulement dans 6 min · C : dans la zone mais hors bandes
        for siret, lon, lat, diff, denom in [
            ("91111111111111", _LON, _LAT, True, "PRIMEUR A"),
            ("92222222222222", _LON + 0.012, _LAT, True, "PRIMEUR B"),
            ("93333333333333", _LON + 0.04, _LAT, False, "MASQUE C"),
        ]:
            s.execute(text(
                "INSERT INTO sirene_etablissements (siret, siren, naf, denomination, diffusible, actif, geom) "
                "VALUES (:s, :siren, '4721Z', :d, :diff, true, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))"),
                {"s": siret, "siren": siret[:9], "d": (denom if diff else None), "diff": diff,
                 "lon": lon, "lat": lat})
        res = Z.concurrents_zone(s, zone, "4721Z", bandes=bandes)
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9%' AND naf = '4721Z'"))
    par_siret = {i["siret"]: i for i in res["items"]}
    assert res["n"] == 3
    assert par_siret["91111111111111"]["temps_min"] == 2, "le plus proche porte sa BANDE de temps (2 min)"
    assert par_siret["92222222222222"]["temps_min"] == 6
    assert par_siret["93333333333333"]["temps_min"] is None, "hors bandes : temps inconnu, pas une distance"
    assert par_siret["93333333333333"]["nom"] == "Établissement (nom non diffusé)", "non diffusible : masqué"
    # tri : les temps connus d'abord, croissants
    assert [i["temps_min"] for i in res["items"]] == [2, 6, None]


def _seed_parcel(s, idu, lon, lat):
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Saint-André','S','1', ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),0.0005), 1000, "
        " ST_SetSRID(ST_MakePoint(:lon,:lat),4326), "
        " ST_Envelope(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),0.0005)))"),
        {"i": idu, "lon": lon, "lat": lat})


def test_endpoint_parcelle_zone_revenu_source_unique(monkeypatch):
    from labuse.api.app import parcel_zone
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.03))
    idu = "ZONETEST000001"
    with session_scope() as s:
        for c in ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17", "ind_18_24"]:
            s.execute(text(f"ALTER TABLE filosofi_carreaux_200m ADD COLUMN IF NOT EXISTS {c} double precision"))
        s.execute(text("ALTER TABLE commune_insee_logement ADD COLUMN IF NOT EXISTS insee varchar"))
        _seed_parcel(s, idu, _LON, _LAT)
        # un carreau AU CENTROÏDE : sert la population de zone ET le revenu unique (nivvie = snv/ind)
        s.execute(text(
            "INSERT INTO filosofi_carreaux_200m (geom, ind, men, men_pauv, men_prop, ind_snv, "
            " ind_0_3, ind_4_5, ind_6_10, ind_11_17, ind_18_24) VALUES ("
            " ST_Transform(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),0.001),2975), "
            " 200, 80, 8, 40, 3800000, 10, 10, 10, 10, 10)"), {"lon": _LON, "lat": _LAT})
        out = parcel_zone(idu, mode="pied", minutes=15, db=s)
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE ind = 200 AND men_prop = 40"))
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE cache_key LIKE 'pied|%'"))
    assert out["disponible"] is True
    assert out["hors_trafic"] is True
    assert out["population"]["habitants"] == 200
    # REVENU = valeur au centroïde (snv/ind = 3 800 000 / 200 = 19 000), source unique dite
    assert out["population"]["revenu_median_eur"] == 19000
    assert "centroïde" in out["population"]["revenu_source"]
    assert out["population"]["revenu_estime"] is True


def test_endpoint_parcelle_zone_degrade_honnete(monkeypatch):
    from labuse.api.app import parcel_zone
    def _boom(lon, lat, minutes, mode, *, client):
        raise RuntimeError("timeout IGN")
    monkeypatch.setattr(Z, "fetch_isochrone", _boom)
    idu = "ZONETEST000002"
    with session_scope() as s:
        _seed_parcel(s, idu, _LON, _LAT)
        out = parcel_zone(idu, mode="pied", minutes=15, db=s)
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    assert out["disponible"] is False
    assert out["statut"] == "indisponible"
    assert "geom" not in out, "aucune géométrie — jamais un cercle substitué"
    assert "population" not in out


def test_naf_recherche_par_libelle_francais():
    from labuse.naf_labels import chercher, label
    codes = {r["code"] for r in chercher("boulangerie")}
    assert "1071C" in codes, "« boulangerie » trouve le code 1071C"
    # accent-insensible : « patisserie » ≡ « pâtisserie »
    assert any(r["code"] == "1071D" for r in chercher("patisserie"))
    # recherche par code aussi
    assert any(r["code"] == "4773Z" for r in chercher("4773"))
    assert label("10.71C") == "Boulangerie et boulangerie-pâtisserie", "le point est normalisé"


def test_endpoint_etude_zone_concurrents_et_ratio(monkeypatch):
    from labuse.api.app import etude_zone, EtudeZoneIn
    from labuse.ingestion.sirene_etablissements import ensure_tables as se_ens
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.03))
    idu = "ZONETEST000004"
    with session_scope() as s:
        Z.ensure_tables(s); se_ens(s)
        for c in ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17", "ind_18_24"]:
            s.execute(text(f"ALTER TABLE filosofi_carreaux_200m ADD COLUMN IF NOT EXISTS {c} double precision"))
        _seed_parcel(s, idu, _LON, _LAT)
        s.execute(text(
            "INSERT INTO filosofi_carreaux_200m (geom, ind, men, men_pauv, men_prop, ind_snv, "
            " ind_0_3, ind_4_5, ind_6_10, ind_11_17, ind_18_24) VALUES ("
            " ST_Transform(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),0.001),2975), "
            " 600, 200, 20, 100, 12000000, 30, 30, 30, 30, 30)"), {"lon": _LON, "lat": _LAT})
        for siret, lon in [("94444444444444", _LON), ("95555555555555", _LON + 0.002)]:
            s.execute(text(
                "INSERT INTO sirene_etablissements (siret, siren, naf, denomination, diffusible, actif, geom) "
                "VALUES (:s, :si, '1071C', 'BOULANGERIE', true, true, ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"),
                {"s": siret, "si": siret[:9], "lon": lon, "lat": _LAT})
        out = etude_zone(EtudeZoneIn(idu=idu, naf="10.71C", minutes=10, mode="voiture"), db=s)
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE ind = 600 AND men_prop = 100"))
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9%' AND naf='1071C'"))
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM zone_isochrone_cache WHERE cache_key LIKE 'voiture|%'"))
    assert out["zone_disponible"] is True
    assert out["naf_label"] == "Boulangerie et boulangerie-pâtisserie"
    assert out["concurrents"]["n"] == 2, "les 2 boulangeries de la zone sont comptées"
    assert all(c["temps_min"] is not None for c in out["concurrents"]["items"]), "chaque concurrent porte son temps"
    # habitants / concurrents = 600 / 2 = 300
    assert out["habitants_par_concurrent"] == 300
    assert set(out["marche"]) == {"ventes_12m", "prix_m2_median_bati", "annonces_actives", "permis_36m"}
