"""IMPLANTATION-1 LOT C — validations du moteur d'implantation.

Les tests RE-MESURENT les invariants depuis la géométrie produite (ils ne font pas confiance aux
compteurs du moteur) et cassent si un seul est faux. Marqués `reel` : ils ont besoin du cadastre /
de la voirie réels (base applicative), absents d'une base vierge — rejoués au banc, jamais en CI.
"""
from __future__ import annotations

import os

import pytest
from shapely.ops import unary_union

from labuse.implantation import rendu
from labuse.implantation.conventions import charger as charger_conventions
from labuse.implantation.controles import ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI
from labuse.implantation.moteur import IDUS_ETANG_SALE, etudier

_TOL_AIRE = 1e-6
_TOL_CONTENU = 0.05


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
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
        pytest.skip("parcelles AW 99/451/624/625 de L'Étang-Salé absentes de la base")
    yield s
    s.close()


@pytest.fixture(scope="module")
def scenario(session_reelle):
    return etudier(session=session_reelle)


# ----------------------------------------------------------- aides de mesure
def _w(scenario, kind):
    return [o.geom_world for o in scenario.scene.of(kind)]


def _plan(scenario):
    objs = []
    for kind in ("batiment_emprise", "place", "allee", "acces", "espace_libre"):
        objs += _w(scenario, kind)
    return objs


# ----------------------------------------------------------- faisabilité d'ensemble
def test_scenario_exploitable(scenario):
    assert scenario.statut == "exploitable en pré-faisabilité"
    assert scenario.capacite.logements > 0
    assert not any(c.resultat == ECHOUE for c in scenario.controles)


# ----------------------------------------------------------- géométriques
def test_batiments_dans_la_zone(scenario):
    zone = scenario.terrain.zone_implantation.buffer(_TOL_CONTENU)
    batis = _w(scenario, "batiment_emprise")
    assert batis, "aucun bâtiment dessiné"
    for b in batis:
        assert zone.contains(b), "un bâtiment déborde la zone d'implantation"


def test_places_allees_dans_assiette_hors_bati(scenario):
    assiette = scenario.terrain.assiette.buffer(_TOL_CONTENU)
    bati = unary_union(_w(scenario, "batiment_emprise"))
    for g in _w(scenario, "place") + _w(scenario, "allee") + _w(scenario, "acces"):
        assert assiette.contains(g), "place/allée/accès hors de l'assiette"
        assert g.intersection(bati).area <= _TOL_AIRE, "place/allée/accès recouvre le bâti"


def test_aucun_chevauchement(scenario):
    objs = _plan(scenario)
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            assert objs[i].intersection(objs[j]).area <= _TOL_AIRE, \
                "deux objets du plan se chevauchent (aire ∩ > 0)"


def test_chaque_place_touche_une_allee(scenario):
    places = _w(scenario, "place")
    allees = unary_union(_w(scenario, "allee"))
    assert places, "aucune place dessinée"
    for p in places:
        assert p.distance(allees) < 1e-6, "une place ne touche aucune allée"


def test_acces_relie_allees_et_sur_voie(scenario):
    acces = _w(scenario, "acces")
    allees = unary_union(_w(scenario, "allee"))
    voie = unary_union(scenario.terrain.voie_edges)
    assert acces, "aucun accès dessiné"
    acc = unary_union(acces)
    assert acc.distance(allees) < 1e-6, "l'accès ne rejoint pas le réseau d'allées"
    assert acc.distance(voie) < 0.5, "l'accès n'est pas sur une limite classée voie"


def test_largeur_allee(scenario):
    conv = scenario.conventions
    for o in scenario.scene.of("allee"):
        mnx, mny, mxx, mxy = o.geom_local.bounds
        assert min(mxx - mnx, mxy - mny) >= conv.allee_largeur_m - 0.05, "allée trop étroite"


def test_dimensions_modules(scenario):
    conv = scenario.conventions
    mods = scenario.scene.of("module")
    assert mods, "aucun module dessiné"
    for o in mods:
        mnx, mny, mxx, mxy = o.geom_local.bounds
        assert (mxx - mnx) >= conv.largeur_module(o.type_logement) - 0.05, "module trop étroit"
        assert (mxy - mny) >= conv.profondeur_logement_m() - 0.05, "module trop peu profond"


def test_nb_annonce_egale_nb_dessine(scenario):
    cap = scenario.capacite
    assert cap.logements == len(scenario.scene.of("module"))
    assert cap.places == len(scenario.scene.of("place"))
    # distribution par niveau : somme = total
    somme = sum(sum(d["par_type"].values()) for d in cap.distribution_niveaux)
    assert somme == cap.logements


def test_surfaces_tableau_egalent_mesures(scenario):
    cap = scenario.capacite
    sdp_mes = sum(o.geom_world.area for o in scenario.scene.objets
                  if o.kind in ("module", "noyau", "coursive"))
    emp_mes = unary_union(_w(scenario, "batiment_emprise")).area
    pt_mes = sum(o.geom_world.area for o in scenario.scene.of("espace_libre"))
    assert abs(sdp_mes - cap.sdp_m2) < 0.5
    assert abs(emp_mes - cap.emprise_sol_m2) < 0.5
    assert abs(pt_mes - cap.pleine_terre_m2) < 0.5


def test_hauteur_sous_regle(scenario):
    cap = scenario.capacite
    conv = scenario.conventions
    r = scenario.regles.hauteur_egout
    assert r.validee and r.valeur is not None
    assert cap.niveaux * conv.hauteur_etage_m <= r.valeur + 1e-9


# ----------------------------------------------------------- réglementaires (4 états)
def test_reussi_seulement_avec_citation(scenario):
    """Aucun « Réussi » sans règle validée citée — exigence cardinale du mandat."""
    for c in scenario.controles:
        if c.resultat == REUSSI:
            assert c.citation, f"contrôle {c.nom!r} Réussi sans citation"


def test_regles_non_validees_sont_non_effectue(scenario):
    par_nom = {c.nom: c.resultat for c in scenario.controles}
    for nom in ("Espaces verts", "Destination", "Distance entre constructions", "Locaux vélos · déchets"):
        assert par_nom.get(nom) == NON_EFFECTUE, f"{nom} devrait être Non effectué"


def test_contraintes_absentes_sont_non_applicable(scenario):
    # aucune contrainte cartographiée sur ce terrain -> Non applicable (A0 l'a mesuré)
    assert not scenario.terrain.contraintes_presentes
    ppr = next(c for c in scenario.controles if c.nom == "PPR / ER / EBC / SUP")
    assert ppr.resultat == NON_APPLICABLE


def test_controles_durs_reussis(scenario):
    par_nom = {c.nom: c.resultat for c in scenario.controles}
    for nom in ("Emprise au sol", "Hauteur", "Reculs", "Perméabilité (pleine terre)", "Stationnement"):
        assert par_nom.get(nom) == REUSSI, f"{nom} devrait être Réussi"


def test_stationnement_suffisant(scenario):
    cap = scenario.capacite
    assert cap.places_imposees is not None
    assert cap.places >= cap.places_imposees


def test_quatre_etats_seulement(scenario):
    autorises = {REUSSI, ECHOUE, NON_EFFECTUE, NON_APPLICABLE}
    for c in scenario.controles:
        assert c.resultat in autorises


# ----------------------------------------------------------- déterminisme & archive
def test_deterministe(session_reelle):
    import hashlib
    import json

    def sig():
        s = etudier(session=session_reelle)
        blob = json.dumps(rendu.scenario_dict(s)["geometrie_objets"], sort_keys=True)
        return (s.forme, s.niveaux, s.capacite.logements, s.capacite.places,
                hashlib.md5(blob.encode()).hexdigest())
    assert sig() == sig(), "le moteur n'est pas déterministe"


def test_scenario_json_rejouable(scenario, tmp_path):
    p = tmp_path / "scenario.json"
    rendu.ecrire_scenario_json(scenario, p, genere_le="test")
    import json
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["crs"] == "EPSG:2975"
    for k in ("entrees", "version_regles", "conventions", "terrain", "tableau_capacite",
              "controles_reglementaires", "geometrie_objets"):
        assert k in d
    # le barème stationnement archivé est bien validé + cité
    bar = d["version_regles"]["stationnement_bareme"]
    assert bar["validee"] and bar["citation"] and bar["lignes"]


def test_conventions_toutes_estimees():
    conv = charger_conventions()
    assert conv.etiquette == "Estimé"
    assert conv.profondeur_m > 0 and conv.place_longueur_m == 5.0 and conv.place_largeur_m == 2.5
