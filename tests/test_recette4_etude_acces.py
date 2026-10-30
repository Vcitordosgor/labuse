"""RECETTE-4 (point « Étude de faisabilité ») — VERROU : « aucune limite classée voie » ne bloque plus.
Quand aucune voie n'est classée, terrain.charger promeut une arête en accès hypothétique
(`voie_hypothese=True`). Le moteur ajoute alors un contrôle « Accès (voie) : À confirmer » et le verdict
devient « À compléter » (plus « Impossible ») : l'étude CONTINUE, l'accès est signalé « à confirmer ».
"""
from types import SimpleNamespace

from labuse.implantation.conventions import charger as charger_conventions
from labuse.implantation.controles import (A_CONFIRMER, VERDICT_A_COMPLETER, VERDICT_IMPOSSIBLE,
                                            controles_reglementaires, verdict_global)
from labuse.implantation.geometrie import Frame, Objet, Scene, rect
from labuse.implantation.regles import (BaremeStationnement, Mixite, Regle, ReglesZone,
                                         _distance_constructions)

CONV = charger_conventions()


def _scene():
    frame = Frame(ox=0.0, oy=0.0, angle_deg=0.0)
    grand = rect(-5, -5, 200, 40)
    sc = Scene(frame=frame, assiette_local=grand, zone_local=grand, voie_bas=True, voie_local=[])
    g = rect(0, 0, 10, 10)
    sc.ajouter(Objet("batiment_emprise", g, ref="B1", geom_world=g))
    return sc


def _terrain(*, has_voie, voie_hypothese):
    grand = rect(-5, -5, 200, 40)
    return SimpleNamespace(zone_implantation=grand, contraintes={}, ppr_bleue=None, ppr_rouge=None,
                           contenance_totale_m2=4000.0, ppr_rouge_m2=0.0, voie_edges=[rect(0, 0, 10, 0.1)],
                           has_voie=has_voie, voie_hypothese=voie_hypothese)


def _cap():
    return SimpleNamespace(niveaux=3, emprise_sol_m2=200.0, places=0, places_imposees=None,
                           pleine_terre_m2=0.0)


def _regles():
    non = Regle(nom="x", valeur=None, unite="", validee=False)
    return ReglesZone(
        insee="97400", zone="UT", hauteur_egout=non, hauteur_faitage=non, emprise_ces=non,
        recul_voie=non, recul_separatives=non, pleine_terre=non,
        mixite=Mixite(False, None, None, None, None, None, None),
        stationnement=BaremeStationnement(False, "absent", None, "superieur", None, (), None, None, None),
        distance_constructions=_distance_constructions({}), prospect=None)


def _acces(controles):
    return [c for c in controles if c.nom == "Accès (voie)"]


def test_accès_hypothétique_ajoute_un_contrôle_à_confirmer():
    controles = controles_reglementaires(_scene(), _terrain(has_voie=False, voie_hypothese=True),
                                         CONV, _cap(), _regles())
    acc = _acces(controles)
    assert len(acc) == 1 and acc[0].resultat == A_CONFIRMER
    assert "voie" in acc[0].regle.lower()


def test_voie_classée_n_ajoute_aucun_contrôle_accès():
    # comportement d'origine : une voie classée ne surface aucun contrôle « Accès (voie) ».
    controles = controles_reglementaires(_scene(), _terrain(has_voie=True, voie_hypothese=False),
                                         CONV, _cap(), _regles())
    assert _acces(controles) == []


def test_verdict_accès_à_confirmer_n_est_pas_impossible():
    controles = controles_reglementaires(_scene(), _terrain(has_voie=False, voie_hypothese=True),
                                         CONV, _cap(), _regles())
    ter = _terrain(has_voie=False, voie_hypothese=True)
    v = verdict_global(controles, statut_base="exploitable en pré-faisabilité", terrain=ter)
    assert v == VERDICT_A_COMPLETER
    assert v != VERDICT_IMPOSSIBLE
