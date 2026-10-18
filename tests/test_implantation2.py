"""IMPLANTATION-2 LOT A — le moteur SERVI par l'API (payload, contrôles, programme, hypothèses).

On exerce le vrai moteur sur des terrains réels (marqués `reel`, rejoués au banc, jamais en CI) :
le payload servi est ASSEMBLÉ par `service.etudier_payload` et la route `POST /modules/etude` est
appelée en direct (sans serveur : respecte « une seule API à la fois »). Les invariants sont
RE-MESURÉS depuis la géométrie servie (GeoJSON 4326), pas crus sur parole.
"""
from __future__ import annotations

import os

import pytest
from shapely.geometry import shape
from shapely.ops import unary_union

from labuse.implantation.controles import ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI
from labuse.implantation.moteur import IDUS_ETANG_SALE
from labuse.implantation.service import etudier_payload

pytestmark = pytest.mark.reel

_STATUTS = {"exploitable en pré-faisabilité", "à compléter", "simulation impossible", "ne tient pas"}


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                  {"i": IDUS_ETANG_SALE}).scalar()
    if n != len(IDUS_ETANG_SALE):
        s.close()
        pytest.skip("parcelles témoins absentes de la base")
    yield s
    s.close()


@pytest.fixture(scope="module")
def payload(session_reelle):
    return etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE, "objectif": "equilibre"})


# --------------------------------------------------------------- forme du payload
def test_payload_entetes(payload):
    assert payload["moteur"]["livrable"] == "IMPLANTATION-2"
    assert payload["moteur"]["crs_carte"] == "EPSG:4326"
    e = payload["entrees"]
    assert e["idus"] == IDUS_ETANG_SALE
    assert e["type_projet"] == "collectif" and e["objectif"] == "equilibre"
    assert e["zone"]
    assert payload["statut_global"] in _STATUTS
    assert payload["hypotheses"]["profondeur_m"] > 0
    assert set(payload["hypotheses"]["surfaces"]) >= {"T2", "T3", "T4"}


def test_etang_sale_servi(payload):
    # témoin collectif exploitable : au moins un scénario, statut cohérent avec le 1er scénario.
    assert payload["scenarios"], "L'Étang-Salé doit être servi"
    assert payload["statut_global"] == payload["scenarios"][0]["statut_etude"]
    assert payload["message"] is None


def test_trois_chiffres_cles(payload):
    for sc in payload["scenarios"]:
        r = sc["resume"]
        assert set(r) == {"logements", "places", "sdp_m2"}
        assert isinstance(r["logements"], int) and r["logements"] > 0
        assert isinstance(r["places"], int) and r["places"] >= 0
        assert r["sdp_m2"] > 0


def test_scenarios_distincts(payload):
    sigs = [(sc["forme"], sc["niveaux"]) for sc in payload["scenarios"]]
    assert len(sigs) <= 3
    assert len(sigs) == len(set(sigs)), "les scénarios doivent être géométriquement distincts"


def test_controles_quatre_etats(payload):
    for sc in payload["scenarios"]:
        c = sc["controles_compte"]
        assert set(c) == {"reussi", "echoue", "non_effectue", "non_applicable"}
        for ct in sc["controles"]:
            assert ct["resultat"] in (REUSSI, ECHOUE, NON_EFFECTUE, NON_APPLICABLE)
            # VERROU : un « Réussi » n'existe jamais sans règle citée.
            if ct["resultat"] == REUSSI:
                assert ct["citation"] and str(ct["citation"]).strip(), \
                    f"« Réussi » sans citation : {ct['nom']}"
        # un scénario servi ne porte aucun contrôle « Échoué ».
        assert c["echoue"] == 0


def test_versions_moteur_et_regles(payload):
    assert payload["moteur"]["version_conventions"]
    lignes = payload["regles"]["lignes"]
    assert lignes, "les règles citées doivent être servies"
    # au moins une règle validée porte une citation (verrou « validée + citation »).
    assert any(r["validee"] and r.get("citation") for r in lignes)


# --------------------------------------------------------------- GeoJSON (carte)
def test_geojson_valide_et_sans_chevauchement(payload):
    for sc in payload["scenarios"]:
        fc = sc["geojson"]
        assert fc["type"] == "FeatureCollection" and fc["features"]
        sol = {}
        for f in fc["features"]:
            assert "kind" in f["properties"]
            g = shape(f["geometry"])
            assert g.is_valid, f"feature {f['properties']['kind']} invalide"
            k = f["properties"]["kind"]
            if k in ("batiment_emprise", "place", "allee", "acces", "espace_libre"):
                sol.setdefault(k, []).append(g)
        unions = {k: unary_union(v) for k, v in sol.items()}
        ks = list(unions)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                inter = unions[ks[i]].intersection(unions[ks[j]]).area
                assert inter < 1e-9, f"chevauchement {ks[i]} ∩ {ks[j]}"


# --------------------------------------------------------------- programme saisi
def test_programme_saisi_qui_tient(session_reelle):
    # 4 T2 + 2 T3 : petit programme, doit tenir sur L'Étang-Salé (qui porte ~28 logts).
    prog = {"mode": "saisi", "lignes": [{"type": "T2", "nombre": 4, "surface_m2": 50},
                                        {"type": "T3", "nombre": 2, "surface_m2": 65}]}
    p = etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE, "programme": prog})
    assert p["scenarios"], "un petit programme doit tenir"
    assert p["entrees"]["programme_mode"] == "saisi"
    for sc in p["scenarios"]:
        assert sc["programme"]["par_type"].get("T2", 0) >= 4
        assert sc["programme"]["par_type"].get("T3", 0) >= 2


def test_programme_saisi_qui_ne_tient_pas(session_reelle):
    # 300 T4 : impossible sur ce terrain → « ne tient pas » + cause nommée, zéro scénario.
    prog = {"mode": "saisi", "lignes": [{"type": "T4", "nombre": 300, "surface_m2": 80}]}
    p = etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE, "programme": prog})
    assert p["scenarios"] == []
    assert p["statut_global"] == "ne tient pas"
    assert p["message"] and p["message"].startswith("ne tient pas")
    assert "plafonne" in p["message"]


# --------------------------------------------------------------- hypothèses modifiables
def test_hypotheses_surcharge_recalcule(session_reelle, payload):
    # T2 porté à 90 m² (modules plus larges) → moins de logements qu'au défaut (recalcul effectif).
    base = payload["scenarios"][0]["resume"]["logements"]
    p = etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE,
                                         "hypotheses": {"surfaces": {"T2": 90, "T3": 95}}})
    assert p["hypotheses"]["surfaces"]["T2"] == 90
    assert p["scenarios"]
    gros = p["scenarios"][0]["resume"]["logements"]
    assert gros < base, "des logements plus grands doivent réduire la capacité"


# --------------------------------------------------------------- objectif pilote le rang
def test_objectif_pilote_le_rang(session_reelle):
    simple = etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE, "objectif": "plus_simple"})
    logts = etudier_payload(session_reelle, {"idus": IDUS_ETANG_SALE, "objectif": "plus_logements"})
    assert simple["scenarios"] and logts["scenarios"]
    # « projet plus simple » ne monte pas plus haut que « plus de logements ».
    assert simple["scenarios"][0]["niveaux"] <= logts["scenarios"][0]["niveaux"]


# --------------------------------------------------------------- la route POST /modules/etude
def test_route_etude_sert_les_scenarios(session_reelle):
    from labuse.api.modules import EtudeIn, etude_implantation

    out = etude_implantation(EtudeIn(idus=IDUS_ETANG_SALE), db=session_reelle)
    assert out["moteur"]["livrable"] == "IMPLANTATION-2"
    assert out["scenarios"]


def test_route_etude_entrees_invalides(session_reelle):
    from fastapi import HTTPException

    from labuse.api.modules import EtudeIn, etude_implantation

    with pytest.raises(HTTPException) as e1:
        etude_implantation(EtudeIn(idus=[]), db=session_reelle)
    assert e1.value.status_code == 400

    with pytest.raises(HTTPException) as e2:
        etude_implantation(EtudeIn(idus=IDUS_ETANG_SALE * 3), db=session_reelle)  # > 8
    assert e2.value.status_code == 400

    with pytest.raises(HTTPException) as e3:
        etude_implantation(EtudeIn(idus=IDUS_ETANG_SALE, type_projet="lotissement"),
                           db=session_reelle)
    assert e3.value.status_code == 400
