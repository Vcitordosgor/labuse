"""PLU-CALIBRAGE-10 — contrôle de la DISTANCE ENTRE CONSTRUCTIONS (ex-article 8).

Tests PURS (aucune base) : les règles de distance sont chargées depuis un YAML en mémoire et le
contrôle est mesuré sur une géométrie synthétique (deux emprises bâties à distance connue). On
vérifie les quatre formes servables (fixe / relative / conditionnelle / contiguïté), le silence
prouvé (→ Non applicable + convention) et le non-servi (→ Non effectué), ainsi que la bascule de
statut : plusieurs bâtiments ne forcent plus « à compléter » quand la règle est servie.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
import yaml

from labuse.implantation.conventions import charger as charger_conventions
from labuse.implantation.controles import (ECHOUE, NON_APPLICABLE, NON_EFFECTUE, REUSSI,
                                            controles_reglementaires, statut_etude)
from labuse.implantation.geometrie import Frame, Objet, Scene, rect
from labuse.implantation.regles import (BaremeStationnement, Mixite, Regle, ReglesZone,
                                        _distance_constructions)

CONV = charger_conventions()


def _dc(yaml_text: str):
    """DistanceConstructions depuis un bloc YAML `entre_constructions`, via le vrai loader."""
    leaf = yaml.safe_load(yaml_text)
    return _distance_constructions({"entre_constructions": leaf})


def _regles(dc):
    non = Regle(nom="x", valeur=None, unite="", validee=False)
    return ReglesZone(
        insee="97400", zone="UT", hauteur_egout=non, hauteur_faitage=non, emprise_ces=non,
        recul_voie=non, recul_separatives=non, pleine_terre=non,
        mixite=Mixite(False, None, None, None, None, None, None),
        stationnement=BaremeStationnement(False, "absent", None, "superieur", None, (), None, None, None),
        distance_constructions=dc, prospect=None)


def _scene(nb_bati: int, gap_m: float) -> Scene:
    """Scène synthétique : `nb_bati` emprises 10×10 alignées, séparées de `gap_m`."""
    frame = Frame(ox=0.0, oy=0.0, angle_deg=0.0)
    grand = rect(-5, -5, 200, 40)
    sc = Scene(frame=frame, assiette_local=grand, zone_local=grand, voie_bas=True, voie_local=[])
    x = 0.0
    for i in range(nb_bati):
        g = rect(x, 0, x + 10, 10)
        sc.ajouter(Objet("batiment_emprise", g, ref=f"B{i+1}", geom_world=g))
        x += 10 + gap_m
    return sc


def _terrain():
    grand = rect(-5, -5, 200, 40)
    return SimpleNamespace(zone_implantation=grand, contraintes={}, ppr_bleue=None,
                           ppr_rouge=None, contenance_totale_m2=4000.0, ppr_rouge_m2=0.0,
                           voie_edges=[])


def _cap(niveaux=3):
    # R+2 -> H = 3 niveaux × 3 m = 9 m ; H+h = 18 m
    return SimpleNamespace(niveaux=niveaux, emprise_sol_m2=200.0, places=0, places_imposees=None,
                           pleine_terre_m2=0.0)


def _ctrl_distance(dc, nb_bati=2, gap_m=7.0, niveaux=3):
    sc, ter = _scene(nb_bati, gap_m), _terrain()
    controles = controles_reglementaires(sc, ter, CONV, _cap(niveaux), _regles(dc))
    c = next(c for c in controles if c.nom == "Distance entre constructions")
    return c, controles, sc, ter


# --------------------------------------------------------------------- un seul bâtiment (pt 4)
# Non applicable est RÉSERVÉ au silence prouvé. En mono-bâtiment : règle chiffrable -> Réussi
# (respectée sans objet) ; silence -> Non applicable ; règle non servie -> Non effectué.
def test_mono_batiment_chiffrable_reussi():
    dc = _dc("{forme: fixe, min_m: 6, statut: valide, citation: 'd’au moins 6 m', article: y, page_pdf: 1}")
    c, *_ = _ctrl_distance(dc, nb_bati=1)
    assert c.resultat == REUSSI and c.citation and "seul bâtiment" in c.mesure


def test_mono_batiment_silence_non_applicable():
    dc = _dc("{absent: true, statut: valide, citation: 'Non réglementée.', article: a, page_pdf: 1}")
    c, *_ = _ctrl_distance(dc, nb_bati=1)
    assert c.resultat == NON_APPLICABLE


def test_mono_batiment_non_servi_non_effectue():
    # zone non calibrée + un seul bâtiment -> Non effectué, JAMAIS Non applicable (pt 4)
    dc = _dc("{forme: fixe, min_m: 6, statut: propose, citation: 'x', article: a, page_pdf: 1}")
    c, *_ = _ctrl_distance(dc, nb_bati=1)
    assert c.resultat == NON_EFFECTUE


# --------------------------------------------------------------------- FIXE
def test_fixe_reussi():
    dc = _dc("{forme: fixe, min_m: 6, statut: valide, citation: 'd’au moins 6 m', article: 'UA 8', page_pdf: 18}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0)            # 7 ≥ 6
    assert c.resultat == REUSSI and c.citation


def test_fixe_echoue():
    dc = _dc("{forme: fixe, min_m: 8, statut: valide, citation: 'd’au moins 8 m', article: 'UE 8', page_pdf: 70}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0)            # 7 < 8
    assert c.resultat == ECHOUE


# --------------------------------------------------------------------- RELATIVE
def test_relative_cumulee_echoue():
    # 0.5 × (H+h) = 0.5 × 18 = 9 m, min 4 → requis 9 ; mesuré 7 → Échoué
    dc = _dc("{forme: relative, base_hauteur: cumulee, fraction_hauteur: 0.5, min_m: 4, "
             "statut: valide, citation: '(H+h)/2 min 4', article: 'Ui.8', page_pdf: 55}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0, niveaux=3)
    assert c.resultat == ECHOUE
    assert "9.0 m" in c.regle


def test_relative_plus_haut_reussi():
    # 0.5 × H = 0.5 × 9 = 4.5 m, min 4 → requis 4.5 ; mesuré 7 → Réussi
    dc = _dc("{forme: relative, base_hauteur: plus_haut, fraction_hauteur: 0.5, min_m: 4, "
             "statut: valide, citation: 'D=H/2 min 4', article: 'Ua 8', page_pdf: 16}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0, niveaux=3)
    assert c.resultat == REUSSI


def test_relative_plancher_minimum_prime():
    # 0.5 × H = 0.5 × 3 = 1.5 m mais min 4 → requis 4 (le plancher prime)
    dc = _dc("{forme: relative, base_hauteur: plus_haut, fraction_hauteur: 0.5, min_m: 4, "
             "statut: valide, citation: 'min 4', article: a, page_pdf: 1}")
    c, *_ = _ctrl_distance(dc, gap_m=3.0, niveaux=1)   # H=3 ; requis 4 ; mesuré 3 → Échoué
    assert c.resultat == ECHOUE


# --------------------------------------------------------------------- CONDITIONNELLE (ouvertures)
def test_conditionnelle_applique_avec_ouvertures():
    # deux valeurs (6 avec baie / 3 sans) → le moteur retient 6 (cas le plus strict)
    dc = _dc("{forme: conditionnelle, avec_ouvertures_m: 6, sans_ouvertures_m: 3, "
             "statut: valide, citation: '6 m avec baie, 3 m sans', article: 'UA 8', page_pdf: 14}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0)             # 7 ≥ 6 → Réussi
    assert c.resultat == REUSSI
    assert "strict" in (c.detail or "")


def test_conditionnelle_relative_cumulee():
    # (H+h)/2 = 9 m, plancher avec ouvertures 6 → requis max(9,6)=9 ; mesuré 7 → Échoué
    dc = _dc("{forme: conditionnelle, base_hauteur: cumulee, fraction_hauteur: 0.5, "
             "avec_ouvertures_m: 6, sans_ouvertures_m: 3, statut: valide, "
             "citation: '(H+h)/2 min 6/3', article: 'UA 8', page_pdf: 14}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0, niveaux=3)
    assert c.resultat == ECHOUE


# --------------------------------------------------------------------- CONTIGUÏTÉ
def test_contiguite_autorisee_reussi():
    dc = _dc("{forme: contiguite, contiguite_autorisee: true, statut: valide, "
             "citation: 'contiguïté admise', article: a, page_pdf: 1}")
    c, *_ = _ctrl_distance(dc, gap_m=7.0)
    assert c.resultat == REUSSI


# --------------------------------------------------------------------- SILENCE prouvé
def test_silence_non_applicable_avec_convention():
    dc = _dc("{absent: true, statut: valide, citation: 'Non réglementée.', article: 'A 8', page_pdf: 91}")
    assert dc.est_silence
    c, *_ = _ctrl_distance(dc, gap_m=7.0)
    assert c.resultat == NON_APPLICABLE
    assert "convention" in c.mesure and f"{CONV.retrait_inter_barre_m:.0f} m" in c.mesure


# --------------------------------------------------------------------- non servi / forme hors schéma
def test_non_servi_non_effectue():
    dc = _dc("{forme: fixe, min_m: 6, statut: propose, citation: 'x', article: a, page_pdf: 1}")
    assert not dc.validee
    c, *_ = _ctrl_distance(dc)
    assert c.resultat == NON_EFFECTUE


def test_forme_hors_schema_non_servie():
    # une forme inconnue (seuil par nombre de logements) n'est PAS servie — on ne devine pas
    dc = _dc("{forme: par_nombre_logements, min_m: 6, statut: valide, citation: 'x', article: a, page_pdf: 1}")
    assert not dc.validee and dc.forme == "absente"


# --------------------------------------------------------------------- bascule de statut d'étude
def test_statut_plusieurs_batiments_plus_bloquant_si_servi():
    dc = _dc("{forme: fixe, min_m: 6, statut: valide, citation: 'x', article: a, page_pdf: 1}")
    c, controles, sc, ter = _ctrl_distance(dc, gap_m=7.0)
    assert c.resultat == REUSSI
    assert statut_etude(controles, True, scene=sc, terrain=ter, regles=_regles(dc)) \
        == "exploitable en pré-faisabilité"


def test_statut_plusieurs_batiments_bloquant_si_non_servi():
    dc = _dc("{forme: fixe, min_m: 6, statut: propose, citation: 'x', article: a, page_pdf: 1}")
    c, controles, sc, ter = _ctrl_distance(dc)
    assert c.resultat == NON_EFFECTUE
    assert statut_etude(controles, True, scene=sc, terrain=ter, regles=_regles(dc)) == "à compléter"


def test_statut_silence_non_bloquant():
    dc = _dc("{absent: true, statut: valide, citation: 'Non réglementée.', article: a, page_pdf: 1}")
    c, controles, sc, ter = _ctrl_distance(dc)
    assert c.resultat == NON_APPLICABLE
    assert statut_etude(controles, True, scene=sc, terrain=ter, regles=_regles(dc)) \
        == "exploitable en pré-faisabilité"
