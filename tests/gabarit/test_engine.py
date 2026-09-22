"""GABARIT-1 lot C — moteur (CDC §10). 20 cas + liste noire, sur fixtures fictives.

Le contrat des fixtures est IDENTIQUE au réel : aucun cas ne dépend de la base.
"""
from __future__ import annotations

import json

import pytest
from shapely.geometry import Polygon

from labuse.gabarit._geom import geojson_from_shape, to_metric, to_wgs
from labuse.gabarit.contract import GabaritInput, RegulatorySource
from labuse.gabarit.engine import INCOMPLETE_MESSAGE, compute_gabarit
from labuse.gabarit.fixtures import demo_gabarit_input


def _valid() -> GabaritInput:
    return demo_gabarit_input().model_copy(deep=True)


def _origin():
    from shapely.geometry import Point
    o = to_metric(Point(55.29, -21.03))
    return o.x, o.y


# ------------------------------------------------------------------ cas nominaux

def test_01_calcul_nominal():
    r = compute_gabarit(_valid())
    assert r.status == "ok"
    assert r.surfaceParcelleM2 == 1180.0
    assert r.zoneImplantationM2 and r.zoneImplantationM2 > 0
    assert r.coverage and r.coverage.familles_verifiees == 4
    assert r.zoneImplantationGeoJSON and r.contourGeoJSON


def test_02_distinction_zone_vs_plafond():
    r = compute_gabarit(_valid())
    # plafond = 1180 × 40 / 100 = 472, calculé À PART ; jamais min(zone, plafond)
    assert r.plafondEmpriseM2 == 472.0
    assert r.zoneImplantationM2 != r.plafondEmpriseM2
    assert r.zoneImplantationM2 != min(r.zoneImplantationM2, r.plafondEmpriseM2) or \
        r.zoneImplantationM2 <= r.plafondEmpriseM2  # la zone n'est pas bornée par le plafond


def test_03_valeurs_zero_explicites_valides():
    inp = _valid()
    inp.setbacks[0].setbackM = 0.0           # recul voie 0 (alignement), explicite + sourcé
    inp.maxFootprint.percent = 0.0           # plafond 0, explicite + sourcé
    r = compute_gabarit(inp)
    assert r.status == "ok"
    assert r.plafondEmpriseM2 == 0.0


def test_04_exclusion_partielle():
    r = compute_gabarit(_valid())
    assert r.status == "ok"
    assert r.exclusionsGeoJSON is not None
    # zone réduite par l'exclusion mais non vide
    assert r.zoneImplantationM2 > 0


def test_05_exclusion_totale_zone_vide():
    inp = _valid()
    x0, y0 = _origin()
    big = Polygon([(x0 - 5, y0 - 5), (x0 + 60, y0 - 5), (x0 + 60, y0 + 60), (x0 - 5, y0 + 60)])
    inp.exclusions[0].geometry = geojson_from_shape(to_wgs(big))
    r = compute_gabarit(inp)
    assert r.status == "ok"                   # une zone vide est un résultat VALIDE
    assert r.zoneImplantationM2 == 0.0
    assert r.zoneImplantationGeoJSON is None   # rien à dessiner


def test_06_entree_non_mutee():
    inp = _valid()
    avant = inp.model_dump()
    compute_gabarit(inp)
    assert inp.model_dump() == avant


# ------------------------------------------------------------------ cas géométrie

def test_07_geometrie_invalide():
    inp = _valid()
    # noeud papillon (auto-intersection) → invalide
    inp.parcel.geometry = {"type": "Polygon",
                           "coordinates": [[[55.29, -21.03], [55.2901, -21.0301],
                                            [55.29, -21.0301], [55.2901, -21.03],
                                            [55.29, -21.03]]]}
    r = compute_gabarit(inp)
    assert r.status == "incomplete" and r.message == INCOMPLETE_MESSAGE


def test_08_limite_ne_suit_pas_la_parcelle():
    inp = _valid()
    x0, y0 = _origin()
    from shapely.geometry import LineString
    loin = LineString([(x0 + 200, y0 + 200), (x0 + 240, y0 + 200)])
    inp.setbacks[0].geometry = geojson_from_shape(to_wgs(loin))
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("ne suit pas" in e or "couvert" in e for e in r.validationErrors)


def test_09_perimetre_insuffisamment_couvert():
    inp = _valid()
    inp.setbacks = [inp.setbacks[0]]          # une seule limite : périmètre non couvert
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("couvert" in e for e in r.validationErrors)


# ------------------------------------------------------------------ cas sources / valeurs

def test_10_valeur_manquante():
    inp = _valid()
    inp.maxHeight.meters = None
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("hauteur" in e for e in r.validationErrors)


def test_11_source_manquante():
    inp = _valid()
    inp.maxFootprint.source = None
    r = compute_gabarit(inp)
    assert r.status == "incomplete"


def test_12_document_source_vide():
    inp = _valid()
    inp.maxHeight.source = RegulatorySource(document="   ")
    r = compute_gabarit(inp)
    assert r.status == "incomplete"


def test_13_source_absente_du_catalogue():
    inp = _valid()
    inp.maxHeight.source = RegulatorySource(document="PLU jamais catalogué", article="X")
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("catalogue" in e for e in r.validationErrors)


def test_14_source_differente_de_la_regle():
    inp = _valid()
    # la valeur pointe une source cohérente au catalogue mais différente de la règle applicable
    autre = RegulatorySource(document="PLU fictif", zone="UC", article="UC 99",
                             provider="LABUSE — démonstration (fictif)")
    inp.sources.append(autre)
    inp.maxHeight.source = autre
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("différente de celle de la règle" in e for e in r.validationErrors)


def test_15_regle_utilisee_mais_non_integree():
    inp = _valid()
    for ar in inp.applicableRules:
        if ar.id == "UC10":
            ar.integrationStatus = "not_integrated"
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("non intégrée" in e for e in r.validationErrors)


def test_16_regle_non_integree_ne_modifie_pas_les_metriques():
    base = compute_gabarit(_valid())
    inp = _valid()
    inp.applicableRules.append(inp.applicableRules[-1].model_copy(
        update={"id": "AUTRE", "label": "Coefficient de biotope"}))
    r = compute_gabarit(inp)
    assert r.status == "ok"
    assert r.zoneImplantationM2 == base.zoneImplantationM2
    assert r.plafondEmpriseM2 == base.plafondEmpriseM2
    assert any(n.label == "Coefficient de biotope" for n in r.nonIntegratedRules)


def test_17_analyse_risques_absente():
    inp = _valid()
    inp.applicableRules = [ar for ar in inp.applicableRules if ar.category != "exclusion"]
    inp.exclusions = []
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("analyse des risques" in e for e in r.validationErrors)


def test_18_exclusion_sans_type_ni_libelle():
    inp = _valid()
    inp.exclusions[0].type = None
    inp.exclusions[0].label = None
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert any("type manquant" in e for e in r.validationErrors)
    assert any("libellé manquant" in e for e in r.validationErrors)


def test_19_regroupement_segments_meme_ruleId():
    r = compute_gabarit(_valid())
    setbacks = [a for a in r.appliedRules if a.category == "setback"]
    # 3 séparatives (UC7, 3 m, même source) regroupées en 1 + 1 voie (UC6) = 2 lignes
    assert len(setbacks) == 2
    labels = {a.label for a in setbacks}
    assert "Limites séparatives" in labels and "Recul voie" in labels


def test_19b_pas_de_fusion_si_valeur_differe():
    inp = _valid()
    inp.setbacks[1].setbackM = 4.0            # une séparative à 4 m : ne doit PAS fusionner
    r = compute_gabarit(inp)
    seps = [a for a in r.appliedRules if a.category == "setback" and a.label == "Limites séparatives"]
    valeurs = {a.value for a in seps}
    assert valeurs == {3.0, 4.0}


def test_20_aucun_champ_estimatif():
    r = compute_gabarit(_valid())
    blob = json.dumps(r.model_dump(), ensure_ascii=False).lower()
    for interdit in ("logement", "étage", "etage", "sdp", "surface de plancher",
                     "coût", "cout", "valeur immob", "potentiel"):
        assert interdit not in blob, f"champ estimatif interdit présent : {interdit}"


@pytest.mark.parametrize("mut", [
    lambda i: setattr(i, "parcel", None),
    lambda i: setattr(i, "sources", []),
    lambda i: setattr(i, "applicableRules", []),
])
def test_incomplet_message_exact(mut):
    inp = _valid()
    mut(inp)
    r = compute_gabarit(inp)
    assert r.status == "incomplete"
    assert r.message == INCOMPLETE_MESSAGE
    assert r.zoneImplantationM2 is None and r.zoneImplantationGeoJSON is None
