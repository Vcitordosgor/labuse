"""ETUDE-V6-2 (Lot 2) — CAPACITÉ STABLE (maximum calculé une fois, indépendant de la demande : deux
demandes différentes sur la même assiette → même maximum) et FACTEUR LIMITANT JUSTE (classé par impact,
le stationnement affirmé limitant/non limitant seulement après un contrefactuel « sans places »).
Rejoué sur Étang-Salé (collectif)."""
from __future__ import annotations

import os

import pytest

_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]


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
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": _ETANG}).scalar()
    if n != 4:
        s.close()
        pytest.skip("parcelles témoins absentes")
    yield s
    s.close()


def _cfg(lignes):
    return {"idus": _ETANG, "type_projet": "collectif", "programme": {"mode": "saisi", "lignes": lignes}}


@pytest.mark.reel
def test_capacite_maximale_stable_entre_deux_demandes(session_reelle):
    """Deux demandes de QUANTITÉS différentes (même type/surface) renvoient le MÊME maximum : la capacité
    est une propriété du terrain, pas de la demande. La demande est seulement CONFRONTÉE à ce maximum."""
    from labuse.implantation.service import etudier_payload
    a = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 10, "surface_m2": 56}]))
    b = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 40, "surface_m2": 56}]))
    ca, cb = a["capacite_maximale"], b["capacite_maximale"]
    assert ca is not None and cb is not None
    # le maximum est IDENTIQUE malgré deux demandes différentes
    assert ca["logements"] == cb["logements"]
    assert ca["par_type"] == cb["par_type"]
    assert ca["niveaux"] == cb["niveaux"]
    # mais la confrontation, elle, dépend de la demande
    assert a["confrontation"]["demande_logements"] == 10
    assert b["confrontation"]["demande_logements"] == 40
    assert a["confrontation"]["capacite_maximale_logements"] == ca["logements"]
    assert a["confrontation"]["tient"] is True          # 10 ≤ max
    assert b["confrontation"]["tient"] is False          # 40 > max
    assert b["confrontation"]["reserve_logements"] < 0


@pytest.mark.reel
def test_facteur_stationnement_prouve_par_contrefactuel(session_reelle):
    """Le stationnement n'est déclaré limitant qu'APRÈS un contrefactuel « sans places » : à Étang-Salé il
    l'est (retirer les places ajoute des logements). Les facteurs sont classés par impact décroissant."""
    from labuse.implantation.service import etudier_payload
    d = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 23, "surface_m2": 56},
                                              {"type": "T3", "nombre": 6, "surface_m2": 70}]))
    facteurs = d["facteurs_limitants"]
    assert facteurs, "au moins un facteur limitant attendu"
    # classement par impact décroissant
    impacts = [f["impact_logements"] for f in facteurs]
    assert impacts == sorted(impacts, reverse=True)
    stat = next(f for f in facteurs if f["facteur"].startswith("stationnement"))
    # à Étang-Salé le stationnement aérien EST limitant, prouvé par le contrefactuel
    assert stat["limitant"] is True
    assert stat["impact_logements"] > 0
    assert "contrefactuel" in stat["preuve"]
    assert "sans stationnement" in stat["detail"]
    # la mesure cite la surface occupée sur l'assiette (ex. « 612 m² occupés sur 1746 m² »)
    assert "m²" in stat["mesure"]
    # le stationnement, prouvé limitant, est en tête du classement (impact le plus fort)
    assert facteurs[0]["facteur"].startswith("stationnement")


@pytest.mark.reel
def test_facteur_non_limitant_jamais_affirme_sans_preuve(session_reelle):
    """Un facteur sans impact mesuré (ex. largeur de zone ici) n'est JAMAIS marqué « limitant »."""
    from labuse.implantation.service import etudier_payload
    d = etudier_payload(session_reelle, _cfg([{"type": "T2", "nombre": 10, "surface_m2": 56}]))
    for f in d["facteurs_limitants"]:
        if f["impact_logements"] == 0:
            assert f["limitant"] is False
