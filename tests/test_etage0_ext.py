"""PHASE 0 « Le Juge » — J1.a : caractérisation des couches ÉTAGE 0 à pouvoir d'exclusion.

Tests PURS (aucune base, pas de marqueur `db`) : chaque couche est appelée directement avec un
`EvalContext` FACTICE dont les getters sont stubés. On encode le comportement ACTUEL du code
(`cascade/layers/etage0_ext.py`) — seuils, kinds, bornes — pas ce qu'une doctrine dit qu'il devrait être.
"""
from __future__ import annotations

import pytest

from labuse.cascade.layers.etage0_ext import (
    GROUPES_PUBLICS,
    EmpriseLineaireLayer,
    EmpriseRoutiereLayer,
    FoncierPublicLayer,
    ResiduelSocleLayer,
)
from labuse.enums import CascadeVerdict


class _Parcel:
    def __init__(self, pid: int = 1):
        self.id = pid


class _Ctx:
    """EvalContext factice : chaque getter renvoie la valeur fixée par le test (ou None)."""

    def __init__(self, **vals):
        self._v = vals

    def owner_pm(self, pid):
        return self._v.get("owner_pm")

    def oriented_envelope_dims(self, pid):
        return self._v.get("dims")

    def emprise_routiere_signals(self, pid):
        return self._v.get("routiere")

    def residuel_sdp(self, pid):
        return self._v.get("sdp")


P = _Parcel()


# ───────────────── EmpriseLineaireLayer : largeur < 8 m ET allongement > 8× (les DEUX) ─────────────────

def test_emprise_lineaire_largeur7_allongement10_exclut():
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims={"largeur_m": 7.0, "allongement": 10.0}), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert v.exclude_kind == "faux_positif"


def test_emprise_lineaire_largeur9_ne_exclut_pas():
    # largeur 9 ≥ 8 → une seule condition manque → PASS (les DEUX sont requises).
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims={"largeur_m": 9.0, "allongement": 10.0}), {})
    assert v.result == CascadeVerdict.PASS


def test_emprise_lineaire_allongement5_ne_exclut_pas():
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims={"largeur_m": 7.0, "allongement": 5.0}), {})
    assert v.result == CascadeVerdict.PASS


def test_emprise_lineaire_frontiere_8_et_8_ne_exclut_pas():
    # FRONTIÈRE (comportement ACTUEL) : seuils STRICTS `w < 8` et `r > 8`. À l'égalité exacte
    # (largeur = 8, allongement = 8) AUCUNE n'est franchie → PASS. (À 7,99 / 8,01 → exclusion.)
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims={"largeur_m": 8.0, "allongement": 8.0}), {})
    assert v.result == CascadeVerdict.PASS


def test_emprise_lineaire_juste_au_dela_exclut():
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims={"largeur_m": 7.99, "allongement": 8.01}), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE


def test_emprise_lineaire_dims_absentes_pass():
    v = EmpriseLineaireLayer().evaluate(P, _Ctx(dims=None), {})
    assert v.result == CascadeVerdict.PASS


# ───────────────────── FoncierPublicLayer : groupe DGFiP public {1,2,3,4,9} ─────────────────────

@pytest.mark.parametrize("groupe", sorted(GROUPES_PUBLICS))
def test_foncier_public_groupes_publics_excluent(groupe):
    v = FoncierPublicLayer().evaluate(
        P, _Ctx(owner_pm={"groupe": groupe, "denomination": "X", "groupe_label": GROUPES_PUBLICS[groupe]}), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert v.exclude_kind == "exclue"


def test_foncier_public_groupe_prive_ne_exclut_pas():
    # groupe 6 ∉ {1,2,3,4,9} → PM privée → PASS « acquérable ».
    v = FoncierPublicLayer().evaluate(
        P, _Ctx(owner_pm={"groupe": 6, "denomination": "SCI X", "groupe_label": "Sociétés"}), {})
    assert v.result == CascadeVerdict.PASS


def test_foncier_public_proprietaire_inconnu_pass():
    # owner_pm None (personne physique ou inconnue) → PASS (comportement ACTUEL : jamais UNKNOWN ici).
    v = FoncierPublicLayer().evaluate(P, _Ctx(owner_pm=None), {})
    assert v.result == CascadeVerdict.PASS


# ───────────────────── EmpriseRoutiereLayer : franche vs garde-fou « signal privé » ─────────────────────

def _routiere(**over):
    base = {"no_road": False, "surf": 100.0, "road_len": 40.0, "bati_m2": 0.0,
            "pm_privee": False, "mutation_dvf": False}
    base.update(over)
    return base


def test_emprise_routiere_franche_sans_signal_prive_exclut():
    # road_len 40 ≥ 30 ; densité 40×6/100 = 2.4 ≥ 0.5 ; bâti 0 % < 10 % ; aucun signal privé → exclusion.
    v = EmpriseRoutiereLayer().evaluate(P, _Ctx(routiere=_routiere()), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert v.exclude_kind == "faux_positif"


def test_emprise_routiere_avec_pm_privee_soft_flag_jamais_exclue():
    v = EmpriseRoutiereLayer().evaluate(P, _Ctx(routiere=_routiere(pm_privee=True)), {})
    assert v.result == CascadeVerdict.SOFT_FLAG  # garde-fou Vic : jamais exclu si signal privé


def test_emprise_routiere_avec_mutation_dvf_soft_flag():
    v = EmpriseRoutiereLayer().evaluate(P, _Ctx(routiere=_routiere(mutation_dvf=True)), {})
    assert v.result == CascadeVerdict.SOFT_FLAG


def test_emprise_routiere_bati_present_ne_exclut_pas():
    # bâti ≥ 10 % → pas une emprise routière (garde-fou bâti) → PASS.
    v = EmpriseRoutiereLayer().evaluate(P, _Ctx(routiere=_routiere(bati_m2=20.0)), {})
    assert v.result == CascadeVerdict.PASS


def test_emprise_routiere_no_road_pass():
    v = EmpriseRoutiereLayer().evaluate(P, _Ctx(routiere={"no_road": True}), {})
    assert v.result == CascadeVerdict.PASS


# ───────────────────── ResiduelSocleLayer : barème SOCLE_TIERS (-25…+30) ─────────────────────

@pytest.mark.parametrize("sdp,socle,phrase", [
    (5000, 30, "opération majeure"),
    (2000, 25, "belle opération"),
    (800, 15, "opération viable"),
    (300, 5, "petit collectif"),
    (100, -10, "une maison"),
    (0, -25, "rien à construire"),
])
def test_residuel_socle_paliers(sdp, socle, phrase):
    v = ResiduelSocleLayer().evaluate(P, _Ctx(sdp=float(sdp)), {})
    assert phrase in v.detail
    if socle > 0:
        assert v.result == CascadeVerdict.POSITIVE
        assert v.magnitude == pytest.approx(socle / 30.0)
    else:
        assert v.result == CascadeVerdict.SOFT_FLAG
        assert v.extra["weight_override"] == float(socle)


def test_residuel_socle_bornes_exactes():
    # juste SOUS un seuil → palier inférieur ; AU seuil (inclusif) → palier supérieur.
    assert "belle opération" in ResiduelSocleLayer().evaluate(P, _Ctx(sdp=4999.0), {}).detail
    assert "opération majeure" in ResiduelSocleLayer().evaluate(P, _Ctx(sdp=5000.0), {}).detail
    assert "une maison" in ResiduelSocleLayer().evaluate(P, _Ctx(sdp=299.0), {}).detail
    assert "petit collectif" in ResiduelSocleLayer().evaluate(P, _Ctx(sdp=300.0), {}).detail


def test_residuel_socle_monotone_croissant():
    def socle_of(sdp):
        v = ResiduelSocleLayer().evaluate(P, _Ctx(sdp=float(sdp)), {})
        return v.extra.get("weight_override", v.magnitude * 30.0) if v.result != CascadeVerdict.UNKNOWN else None
    socles = [socle_of(s) for s in (0, 100, 300, 800, 2000, 5000)]
    assert socles == sorted(socles)      # -25 → -10 → +5 → +15 → +25 → +30, strictement croissant
    assert socles[0] == -25.0 and socles[-1] == 30.0


def test_residuel_socle_none_unknown_jamais_exclusion():
    v = ResiduelSocleLayer().evaluate(P, _Ctx(sdp=None), {})
    assert v.result == CascadeVerdict.UNKNOWN
    assert v.result != CascadeVerdict.HARD_EXCLUDE
