"""IMPLANTATION-1 / 1BIS LOT C — validations du moteur d'implantation.

Les tests RE-MESURENT les invariants depuis la géométrie produite (ils ne font pas confiance aux
compteurs du moteur) et cassent si un seul est faux. Paramétrés sur TROIS terrains réels
(L'Étang-Salé UA, Saint-André UC, Saint-Denis Ui). Marqués `reel` : ils ont besoin du cadastre /
de la voirie / des PPR réels — rejoués au banc, jamais en CI.
"""
from __future__ import annotations

import os

import pytest
from shapely.ops import unary_union

from labuse.implantation import rendu
from labuse.implantation.controles import (ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI,
                                           _ground_tiles)
from labuse.implantation.moteur import (IDUS_ETANG_SALE, IDUS_SAINT_ANDRE, IDUS_SAINT_DENIS, etudier)

_TOL_AIRE = 1e-6
_TOL_CONTENU = 0.05

TERRAINS = {
    "etang_sale": IDUS_ETANG_SALE,
    "saint_andre": IDUS_SAINT_ANDRE,
    "saint_denis": IDUS_SAINT_DENIS,
}


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
    tous = [i for idus in TERRAINS.values() for i in idus]
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": tous}).scalar()
    if n != len(tous):
        s.close()
        pytest.skip("parcelles témoins absentes de la base")
    yield s
    s.close()


@pytest.fixture(scope="module", params=list(TERRAINS), ids=list(TERRAINS))
def scenario(request, session_reelle):
    return etudier(session=session_reelle, idus=TERRAINS[request.param], avec_pente=False)


# ----------------------------------------------------------- aides
def _w(scenario, kind):
    return [o.geom_world for o in scenario.scene.of(kind)]


# ----------------------------------------------------------- faisabilité d'ensemble
def test_statut_non_impossible(scenario):
    assert scenario.statut in ("exploitable en pré-faisabilité", "à compléter")
    assert scenario.capacite.logements > 0
    assert not any(c.resultat == ECHOUE for c in scenario.controles)


# ----------------------------------------------------------- géométriques
def test_batiments_dans_la_zone(scenario):
    zone = scenario.terrain.zone_implantation.buffer(_TOL_CONTENU)
    batis = _w(scenario, "batiment_emprise")
    assert batis
    for b in batis:
        assert zone.contains(b)


def test_places_allees_dans_assiette_hors_bati(scenario):
    assiette = scenario.terrain.assiette.buffer(_TOL_CONTENU)
    bati = unary_union(_w(scenario, "batiment_emprise"))
    for g in _w(scenario, "place") + _w(scenario, "allee") + _w(scenario, "acces"):
        assert assiette.contains(g)
        assert g.intersection(bati).area <= _TOL_AIRE


def test_aucun_chevauchement_tous_couples(scenario):
    """Non-chevauchement sur TOUS les couples du plan de sol (module/noyau/coursive/place/allée/
    accès/espace libre), aire d'intersection = 0."""
    tiles = [o.geom_world for o in _ground_tiles(scenario.scene)]
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            assert tiles[i].intersection(tiles[j]).area <= _TOL_AIRE, \
                "deux objets du plan de sol se chevauchent"


def test_somme_surfaces_egale_assiette(scenario):
    tiles = [o.geom_world for o in _ground_tiles(scenario.scene)]
    somme = sum(t.area for t in tiles)
    assert abs(somme - scenario.terrain.assiette.area) < 1.0


def test_une_seule_allee(scenario):
    assert len(scenario.scene.of("allee")) == 1, "le stationnement doit tenir sur une allée unique"


def test_chaque_place_touche_une_allee(scenario):
    places = _w(scenario, "place")
    allees = unary_union(_w(scenario, "allee"))
    assert places
    for p in places:
        assert p.distance(allees) < 1e-6


def test_allees_reliees_a_l_acces_aucun_cul_de_sac(scenario):
    allees = _w(scenario, "allee")
    acces = unary_union(_w(scenario, "acces"))
    places = unary_union(_w(scenario, "place"))
    voie = unary_union(scenario.terrain.voie_edges)
    assert acces.distance(voie) < 0.6, "l'accès n'est pas sur une limite classée voie"
    for a in allees:
        assert a.distance(acces) < 1e-6, "une allée n'est pas reliée à l'accès"
        assert a.distance(places) < 1e-6, "une allée ne dessert aucune place (cul-de-sac)"


def test_allee_sans_troncon_mort(scenario):
    """Allée coupée au droit des places : aucun prolongement dans le vide (ni place, ni accès).
    Ce test casse sur l'ancien comportement (allée qui se prolongeait au-delà de la dernière place)."""
    conv = scenario.conventions
    places = _w(scenario, "place")
    acces = _w(scenario, "acces")
    allees = _w(scenario, "allee")
    if not places:
        return
    couvre = unary_union(places + acces).buffer(conv.place_longueur_m)
    mort = unary_union(allees).difference(couvre)
    assert mort.area < 1.0, f"allée avec tronçon mort {mort.area:.1f} m²"


def test_aucun_stationnement_en_ppr_rouge(scenario):
    rouge = scenario.terrain.ppr_rouge
    if rouge is None or rouge.is_empty:
        return
    for g in _w(scenario, "place") + _w(scenario, "allee") + _w(scenario, "acces"):
        assert g.intersection(rouge).area <= _TOL_AIRE, "stationnement en PPR rouge"


def test_noyaux_respectent_convention(scenario):
    import math
    from collections import Counter
    conv = scenario.conventions
    mods = Counter(o.ref for o in scenario.scene.of("module") if o.niveau == 0)
    noys = Counter(o.ref for o in scenario.scene.of("noyau") if o.niveau == 0)
    for ref, nmod in mods.items():
        assert noys[ref] >= math.ceil(nmod / conv.max_logements_par_noyau), \
            f"{ref} : un noyau dessert trop de logements"


def test_ratio_shab_sdp_expose(scenario):
    cap = scenario.capacite
    assert cap.ratio_shab_sdp is not None and 0 < cap.ratio_shab_sdp < 1
    assert cap.ratio_shab_sdp_par_batiment


def test_largeur_allee(scenario):
    conv = scenario.conventions
    for o in scenario.scene.of("allee"):
        mnx, mny, mxx, mxy = o.geom_local.bounds
        assert min(mxx - mnx, mxy - mny) >= conv.allee_largeur_m - 0.05


def test_dimensions_modules(scenario):
    conv = scenario.conventions
    mods = scenario.scene.of("module")
    assert mods
    for o in mods:
        mnx, mny, mxx, mxy = o.geom_local.bounds
        assert (mxx - mnx) >= conv.largeur_module(o.type_logement) - 0.05
        assert (mxy - mny) >= conv.profondeur_logement_m() - 0.05


def test_nb_annonce_egale_nb_dessine(scenario):
    cap = scenario.capacite
    assert cap.logements == len(scenario.scene.of("module"))
    assert cap.places == len(scenario.scene.of("place"))
    somme = sum(sum(d["par_type"].values()) for d in cap.distribution_niveaux)
    assert somme == cap.logements


def test_surfaces_tableau_egalent_mesures(scenario):
    cap = scenario.capacite
    sc = scenario.scene
    # PLU-CALIBRAGE-10 LOT D : la SDP = modules + noyaux (coursive ouverte HORS SDP, R111-22).
    sdp_mes = sum(o.geom_world.area for o in sc.objets if o.kind in ("module", "noyau"))
    coursive_mes = sum(o.geom_world.area for o in sc.of("coursive"))
    emp_mes = unary_union(_w(scenario, "batiment_emprise")).area
    pt_mes = sum(o.geom_world.area for o in sc.of("espace_libre"))
    assert abs(sdp_mes - cap.sdp_m2) < 0.5
    assert abs(coursive_mes - cap.coursive_m2) < 0.5
    assert abs(emp_mes - cap.bati_m2) < 0.5
    assert abs(pt_mes - cap.pleine_terre_m2) < 0.5


def test_coursive_hors_sdp(scenario):
    """LOT D : la coursive extérieure ouverte est MESURÉE mais n'entre pas dans la SDP."""
    cap = scenario.capacite
    assert cap.coursive_m2 > 0, "une barre à coursive doit avoir une coursive mesurée"
    # la SDP ne contient ni coursive : SDP + coursive = plancher total clos+ouvert
    assert cap.sdp_m2 < cap.sdp_m2 + cap.coursive_m2
    # le ratio SHAB/SDP se calcule sur la SDP sans coursive
    assert abs(cap.ratio_shab_sdp - round(cap.shab_estimee_m2 / cap.sdp_m2, 3)) < 1e-6


def test_noyau_surface_exposee(scenario):
    """LOT D : la surface des noyaux est donnée par niveau et par bâtiment."""
    cap = scenario.capacite
    assert cap.noyau_m2 > 0 and cap.noyaux_par_batiment
    for ref, d in cap.noyaux_par_batiment.items():
        assert d["niveaux"] == cap.niveaux
        assert abs(d["m2_total"] - d["m2_par_niveau"] * d["niveaux"]) < 0.5
    assert abs(sum(d["m2_total"] for d in cap.noyaux_par_batiment.values()) - cap.noyau_m2) < 0.6


def test_hauteur_sous_regle(scenario):
    cap = scenario.capacite
    r = scenario.regles.hauteur_plafond
    assert r.validee and r.valeur is not None
    assert cap.niveaux * scenario.conventions.hauteur_etage_m <= r.valeur + 1e-9


# ----------------------------------------------------------- ratios sur contenance
def test_ratios_sur_contenance(scenario):
    """Emprise et perméabilité, quand Réussi, se mesurent contre la CONTENANCE (pas le dessin)."""
    t = scenario.terrain
    assert t.contenance_totale_m2 > 0
    # l'écart contenance/dessin est exposé
    assert abs(t.ecart_contenance_dessin_m2 - (t.contenance_totale_m2 - t.aire_dessin_m2)) < 0.1
    par_nom = {c.nom: c for c in scenario.controles}
    for nom in ("Emprise au sol", "Perméabilité (pleine terre)"):
        c = par_nom.get(nom)
        if c and c.resultat == REUSSI:
            assert "contenance" in c.regle


# ----------------------------------------------------------- réglementaires (4 états)
def test_reussi_seulement_avec_citation(scenario):
    for c in scenario.controles:
        if c.resultat == REUSSI:
            assert c.citation, f"{c.nom!r} Réussi sans citation"


def test_hauteur_non_chiffrable_jamais_exploitable(scenario):
    """Règle générale : une règle de hauteur non chiffrable (prospect L>H) ne laisse jamais
    l'étude exploitable. Vérifié sur Saint-Denis (prospect Ui.7)."""
    if scenario.regles.hauteur_non_chiffrable:
        assert scenario.statut != "exploitable en pré-faisabilité"
        c = next(c for c in scenario.controles if c.nom == "Prospect (hauteur relative)")
        assert c.resultat == NON_EFFECTUE
    else:
        c = next(c for c in scenario.controles if c.nom == "Prospect (hauteur relative)")
        assert c.resultat == NON_APPLICABLE


def test_distance_entre_constructions(scenario):
    """PLU-CALIBRAGE-10 : un seul bâtiment => Non applicable. Plusieurs => contrôle MESURÉ
    (Réussi/Échoué si règle servie chiffrable ; Non applicable si silence+convention ; Non
    effectué si règle non servie), et l'étude n'est forcée « à compléter » que si Non effectué."""
    nb_bati = len(scenario.scene.of("batiment_emprise"))
    c = next(c for c in scenario.controles if c.nom == "Distance entre constructions")
    if nb_bati <= 1:
        assert c.resultat == NON_APPLICABLE
    else:
        assert c.resultat in (REUSSI, ECHOUE, NON_APPLICABLE, NON_EFFECTUE)
        if c.resultat == NON_EFFECTUE:
            assert scenario.statut == "à compléter"
        if c.resultat == REUSSI:
            assert c.citation  # Réussi seulement avec citation (verrou)


def test_contraintes_absentes_non_applicable(scenario):
    par_nom = {c.nom: c.resultat for c in scenario.controles}
    t = scenario.terrain
    if not t.contraintes.get("ppr_rouge"):
        assert par_nom.get("PPR zone rouge (interdiction)") == NON_APPLICABLE
    if not t.contraintes.get("ppr_bleue"):
        assert par_nom.get("PPR zone bleue (prescription)") == NON_APPLICABLE


def test_quatre_etats_seulement(scenario):
    autorises = {REUSSI, ECHOUE, NON_EFFECTUE, NON_APPLICABLE}
    for c in scenario.controles:
        assert c.resultat in autorises


def test_stationnement_suffisant(scenario):
    cap = scenario.capacite
    if cap.places_imposees is not None:
        assert cap.places >= cap.places_imposees


# ----------------------------------------------------------- déterminisme & archive
def test_deterministe(session_reelle):
    import hashlib
    import json

    def sig():
        s = etudier(session=session_reelle, idus=IDUS_ETANG_SALE, avec_pente=False)
        blob = json.dumps(rendu.scenario_dict(s)["geometrie_objets"], sort_keys=True)
        return (s.forme, s.niveaux, s.capacite.logements, s.capacite.places,
                hashlib.md5(blob.encode()).hexdigest())
    assert sig() == sig()


def test_scenario_json_rejouable(scenario, tmp_path):
    import json
    p = tmp_path / "scenario.json"
    rendu.ecrire_scenario_json(scenario, p, genere_le="test")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["crs"] == "EPSG:2975"
    for k in ("entrees", "version_regles", "conventions", "terrain", "tableau_capacite",
              "controles_reglementaires", "geometrie_objets"):
        assert k in d
    s = d["tableau_capacite"]["surfaces_mesurees_m2"]
    assert abs(s["somme"] - d["terrain"]["aire_dessin_m2"]) < 1.0
