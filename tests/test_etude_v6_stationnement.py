"""ETUDE-V6 (Lot C) — stationnement par destination : règle générale du PLU (appliquée, sourcée) +
plafond national L151-35 « sous condition d'éligibilité » (jamais le ratio 1/3 non sourcé). Rejoué sur
Saint-Denis Ui (DL0247-0248), proche d'un TCSP (< 800 m)."""
from __future__ import annotations

import os

import pytest

_SD = ["97411000DL0247", "97411000DL0248"]


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
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": _SD}).scalar()
    if n != len(_SD):
        s.close()
        pytest.skip("parcelles Saint-Denis absentes")
    yield s
    s.close()


@pytest.mark.reel
def test_senior_regle_generale_plus_plafond_a_confirmer(session_reelle):
    from labuse.implantation.service import stationnement_payload
    out = stationnement_payload(session_reelle, _SD, "senior")
    g = out["regimes"]["general"]
    # règle générale OPPOSABLE du PLU : 1 place/logt, article + millésime, appliquée
    assert g["applique"] is True and g["ratio_par_logement"] == 1.0
    assert g["article"] and g["millesime"]
    # plafond national L151-35 : SOUS CONDITION — 0,5 place/logt, TCSP < 800 m vérifié, éligibilité à confirmer
    pf = out["regimes"]["plafond_national"]
    assert pf is not None
    assert pf["ratio_plafond"] == 0.5 and pf["reference"] == "L151-35"
    assert pf["condition_tcsp_sous_800m"] is True and pf["distance_tcsp_m"] < 800
    assert pf["statut"] == "À confirmer" and pf["eligibilite_categorie"] == "À confirmer"
    # on ne présente JAMAIS le 1/3 comme une règle du PLU de cette commune
    assert "1 place / 3 logements" in pf["note"] and "PAS une règle du PLU" in pf["note"]


@pytest.mark.reel
def test_collectif_pas_de_plafond_reduit(session_reelle):
    from labuse.implantation.service import stationnement_payload
    out = stationnement_payload(session_reelle, _SD, "collectif")
    assert out["regimes"]["plafond_national"] is None   # pas de catégorie L151-34


@pytest.mark.reel
def test_senior_capacite_reduite_a_confirmer(session_reelle):
    """La capacité sous le plafond réduit (0,5) est servie « À confirmer » et dépasse la règle générale,
    quand le stationnement PLAFONNE la capacité (cas Saint-Denis)."""
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {
        "idus": _SD, "type_projet": "senior",
        "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 10, "surface_m2": 56}]}})
    cr = p["capacite_reduite"]
    assert cr is not None and cr["statut"] == "À confirmer"
    general = p["variantes"][0]["resume"]["logements"]
    assert cr["logements"] > general           # le régime réduit lèverait la contrainte stationnement
    assert p["verdict"] == "À compléter"       # PPR + prospect À confirmer → jamais « Exploitable »
