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
    """ROUGES-7 — aligné sur le comportement LIVRÉ. REMISE-1 a restreint la source TCSP aux STATIONS en
    site propre (`tcsp_station`, plus les simples arrêts de bus) ; FAISA-REGLES-1 (E-056) a porté le rayon
    à 800 m (loi 2025-1129). Les témoins DL0247/0248 sont à ~1068 m du plus proche TCSP → la réduction 0,5
    NE s'applique pas : le plafond L151-35 reste à 1 place/logement, « sous condition d'éligibilité »,
    jamais pré-rempli comme règle du PLU. La clé servie à l'écran est `condition_tcsp_sous_500m`
    (historique, conservée) ; le ratio 0,5 par distance est couvert base-free par test_remise1."""
    from labuse.implantation.service import stationnement_payload
    out = stationnement_payload(session_reelle, _SD, "senior")
    g = out["regimes"]["general"]
    # règle générale OPPOSABLE du PLU : 1 place/logt, article + millésime, appliquée
    assert g["applique"] is True and g["ratio_par_logement"] == 1.0
    assert g["article"] and g["millesime"]
    # plafond national L151-35 : SOUS CONDITION — éligibilité à confirmer, jamais la règle du PLU
    pf = out["regimes"]["plafond_national"]
    assert pf is not None
    assert pf["reference"] == "L151-35"
    assert pf["statut"] == "À confirmer" and pf["eligibilite_categorie"] == "À confirmer"
    # le ratio suit la RÈGLE (0,5 SEULEMENT à moins de 800 m d'un TCSP, sinon 1,0) — pas un 0,5 codé en dur
    sous = pf["condition_tcsp_sous_500m"]          # clé historique lue par l'écran ; seuil 800 m (loi 2025-1129)
    assert pf["rayon_tcsp_m"] == 800
    assert pf["ratio_plafond"] == (0.5 if sous else 1.0)
    # témoins DL : TCSP au-delà de 800 m → condition non remplie, pas de réduction
    assert sous is False and pf["distance_tcsp_m"] >= 800 and pf["ratio_plafond"] == 1.0
    # le ratio affiché est le plafond LÉGAL, jamais présenté comme la règle du PLU de la commune
    assert "plafond LÉGAL" in pf["note"] and "pas une règle du PLU" in pf["note"]


@pytest.mark.reel
def test_collectif_pas_de_plafond_reduit(session_reelle):
    from labuse.implantation.service import stationnement_payload
    out = stationnement_payload(session_reelle, _SD, "collectif")
    assert out["regimes"]["plafond_national"] is None   # pas de catégorie L151-34


@pytest.mark.reel
def test_senior_capacite_reduite_sans_objet_hors_rayon(session_reelle):
    """ROUGES-7 — DL0247/0248 sont à ~1068 m d'un TCSP : le plafond réduit (0,5) de L151-35 n'est PAS
    applicable (loi 2025-1129, 800 m). La « capacité réduite » est donc SANS OBJET — on ne sert jamais une
    capacité gonflée par une réduction qui ne s'applique pas ici. Le verdict reste « À compléter » (PPR +
    prospect à confirmer), jamais « Exploitable ». (La capacité réduite « À confirmer » quand la réduction
    s'applique est couverte base-free par test_remise1 — ratios appliqué == affiché.)"""
    from labuse.implantation.service import etudier_payload
    p = etudier_payload(session_reelle, {
        "idus": _SD, "type_projet": "senior",
        "programme": {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 10, "surface_m2": 56}]}})
    cr = p["capacite_reduite"]
    # réduction non applicable (TCSP > 800 m) → pas de capacité réduite servie (None, ou « sans effet »)
    assert cr is None or cr.get("statut") == "sans effet"
    assert p["verdict"] == "À compléter"       # PPR + prospect À confirmer → jamais « Exploitable »
