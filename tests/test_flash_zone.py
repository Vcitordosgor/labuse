"""FLASH-ZONE F2/F3 — la section « Autour de cette parcelle » du rapport Flash.

On gèle : le builder consomme le moteur zone commun (aucune recopie) · il renvoie TOUJOURS un dict
rendable · le dégradé est honnête (raison client, pas de classe d'exception) · pas de NAF au parcours
Flash → pas de volet concurrence (FZ-001) · la section apparaît dans le HTML rendu, avec ses honnêtetés.
Données [ZONE-TEST] purgées.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import zone as Z
from labuse.db import session_scope
from labuse.flash import data as fdata

pytestmark = pytest.mark.db

_LON, _LAT = 55.6500, -20.9600


def _carre(demi: float) -> dict:
    x0, x1, y0, y1 = _LON - demi, _LON + demi, _LAT - demi, _LAT + demi
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def _seed_carreau(s):
    for c in ["ind_0_3", "ind_4_5", "ind_6_10", "ind_11_17", "ind_18_24"]:
        s.execute(text(f"ALTER TABLE filosofi_carreaux_200m ADD COLUMN IF NOT EXISTS {c} double precision"))
    s.execute(text(
        "INSERT INTO filosofi_carreaux_200m (geom, ind, men, men_pauv, men_prop, ind_snv, "
        " ind_0_3, ind_4_5, ind_6_10, ind_11_17, ind_18_24) VALUES ("
        " ST_Transform(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),0.001),2975), "
        " 400, 150, 15, 80, 8000000, 20, 20, 20, 20, 20)"), {"lon": _LON, "lat": _LAT})


def test_zone_builder_consomme_le_moteur_et_reste_rendable(monkeypatch):
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.03))
    with session_scope() as s:
        Z.ensure_tables(s)
        _seed_carreau(s)
        z = fdata._zone(s, {"lon": _LON, "lat": _LAT})
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE ind = 400 AND men_prop = 80"))
        s.execute(text("DELETE FROM zone_isochrone_cache"))
    assert z["disponible"] is True
    assert z["minutes"] == 10 and z["mode_lib"] == "en voiture"
    assert z["population"]["habitants"] == 400
    assert z["population"]["revenu_estime"] is True, "revenu toujours ESTIMÉ"
    assert z["concurrence_absente"] is True, "pas de NAF au parcours Flash (FZ-001)"
    assert set(z["marche"]) == {"ventes_12m", "prix_m2_median_bati", "annonces_actives",
                                "annonces_reserve", "permis_36m"}   # EXPORTS-1 (5.5) : réserve pige servie


def test_zone_builder_degrade_honnete_sans_classe_exception(monkeypatch):
    monkeypatch.setattr(Z, "fetch_isochrone",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom interne")))
    with session_scope() as s:
        Z.ensure_tables(s)
        s.execute(text("DELETE FROM zone_isochrone_cache"))
        z = fdata._zone(s, {"lon": _LON, "lat": _LAT})
    assert z["disponible"] is False
    assert "IGN" in z["raison"]
    assert "RuntimeError" not in z["raison"] and "boom" not in z["raison"], \
        "le PDF client ne montre pas la classe d'exception"
    assert "population" not in z, "aucune valeur approchée substituée"


def test_zone_builder_sans_centroide():
    z = fdata._zone(None, {"lon": None, "lat": None})   # ne touche pas la DB (garde en amont)
    assert z["disponible"] is False and "centroïde" in z["raison"]


def test_section_zone_dans_le_html_rendu(monkeypatch):
    """La section apparaît dans le HTML (WeasyPrint non requis) avec ses honnêtetés, et le rapport se
    rend sans lever. Parcelle réelle seedée pour que collect_report_data aboutisse."""
    from labuse.flash.report import render_report_html
    monkeypatch.setattr(Z, "fetch_isochrone", lambda lon, lat, minutes, mode, *, client: _carre(0.02))
    idu = "FLZONETEST0001"
    demi = 0.0008
    x0, x1, y0, y1 = _LON - demi, _LON + demi, _LAT - demi, _LAT + demi
    wkt = f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"
    with session_scope() as s:
        Z.ensure_tables(s)
        _seed_carreau(s)
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
            "(:i,'Saint-André','AC','1', ST_GeomFromText(:w,4326), 800, "
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "w": wkt})
        html = render_report_html(s, idu, order_ref="TEST-ZONE", with_map=False)
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE ind = 400 AND men_prop = 80"))
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM zone_isochrone_cache"))
    assert "Autour de cette parcelle" in html
    assert "hors trafic" in html
    assert "Revenu estimé" in html, "l'astérisque ESTIMÉ voyage avec le chiffre"
    assert "Marché immobilier de la zone" in html
    assert "chiffre d'affaires" in html, "la mention « aucune prévision de CA » est présente"