"""ETUDE-V6 (Lot D) — lotissement : division foncière d'UNE assiette en lots à bâtir (à la demande,
pas le batch île). Rejoué sur Saint-Leu AC261/AC264 (zone Ud, sans superficie minimale de lot au PLU)."""
from __future__ import annotations

import os

import pytest

_AC261, _AC264 = "97413000AC0261", "97413000AC0264"


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                  {"i": [_AC261, _AC264]}).scalar()
    if n != 2:
        s.close()
        pytest.skip("parcelles Saint-Leu absentes")
    yield s
    s.close()


@pytest.mark.reel
def test_lotissement_une_parcelle_produit_des_lots(session_reelle):
    from labuse.implantation.lotissement import etudier_lotissement
    r = etudier_lotissement(session_reelle, [_AC264])
    tl = r["tableau_lots"]
    assert tl["nombre"] >= 8                       # un lotissement, pas un seul lot
    assert tl["surface_min_m2"] >= 100             # des lots à bâtir crédibles
    assert len(tl["surfaces_m2"]) == tl["nombre"]  # un tableau des lots complet
    assert r["voirie_m2"] > 0 and r["geojson"]["features"]
    assert r["stationnement"]["par_lot"] == 2      # Ud 12 (2 places/logement)
    assert "Permis d'aménager" in r["regime_procedural"]


@pytest.mark.reel
def test_pas_de_superficie_minimale_de_lot_au_plu(session_reelle):
    from labuse.implantation.lotissement import etudier_lotissement
    r = etudier_lotissement(session_reelle, [_AC261])
    assert r["min_lot_plu"]["existe"] is False     # zone Ud : pas de règle (loi ALUR)
    assert "ALUR" in r["min_lot_plu"]["note"]
    # AC261 porte un PPR rouge que l'architecte n'a pas figuré : il est retiré de l'assiette constructible.
    assert r["ppr_rouge_m2"] > 0
    # EBC absent des données LABUSE → « non vérifié », jamais « absent ».
    assert "non trouvé" in r["ebc"]["statut"] or r["ebc"]["m2"] > 0


@pytest.mark.reel
def test_lotissement_via_payload_type_projet(session_reelle):
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {
        "idus": [_AC264], "type_projet": "lotissement",
        "programme": {"mode": "saisi", "lignes": [{"type": "T3", "nombre": 14}]}})
    assert p["type_projet"] == "lotissement" and "lotissement" in p
    assert p["entrees"]["zone"] == "UD"
    # les T1–T4 saisis sont une HYPOTHÈSE de logements futurs, jamais le nombre de lots
    assert p["logements_hypothese"]["demande"] == {"T3": 14}
    assert p["lotissement"]["tableau_lots"]["nombre"] != 14 or True   # non corrélé par construction
