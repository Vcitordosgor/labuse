"""Couches ÉTAGE 2 (dry-run) — âge dirigeant (courbe + UNKNOWN si absent), BODACC (machine à états
sur libellés réels + bascule rouge), DPE passoire. Tests unitaires via ctx factice."""
from __future__ import annotations

from labuse.cascade.layers.etage2 import AgeDirigeantLayer, BodaccLayer, DpePassoireLayer
from labuse.enums import CascadeVerdict, Severity

AGE_P = {"bonus_key": "age_dirigeant", "courbe": {55: 4, 65: 8, 75: 12, 85: 14}, "age_min_valide": 18}
BODACC_P = {
    "etats": {
        "rouge": ["Jugement de conversion en liquidation judiciaire", "Autre jugement d'ouverture"],
        "orange": ["Jugement arrêtant le plan de sauvegarde"],
        "gris": ["Jugement de clôture pour insuffisance d'actif"]},
    "mojibake": {"Jugement arrÃªtant le plan de sauvegarde": "Jugement arrêtant le plan de sauvegarde"},
}


class _Ctx:
    def __init__(self, prop=None, bod=None, pas=None):
        self._p, self._b, self._pa = prop, bod, pas

    def propension(self, pid):
        return self._p

    def bodacc(self, pid):
        return self._b

    def passoire(self, pid):
        return self._pa


class _P:
    id = 1
    idu = "97415000AA0001"


# ── âge dirigeant ──

def test_age_courbe():
    for age, pts in [(60, 4), (70, 8), (80, 12), (90, 14)]:
        v = AgeDirigeantLayer().evaluate(_P(), _Ctx(prop={"age_max_dirigeant": age, "siren": "9"}), AGE_P)
        assert v.result == CascadeVerdict.POSITIVE
        assert abs(v.magnitude - pts / 14) < 1e-9        # points = round(14 × magnitude)
        assert v.extra["source_table"] == "v_foncier_propension_vendre" and v.extra["source_id"] == "9"


def test_age_jeune_pass():
    v = AgeDirigeantLayer().evaluate(_P(), _Ctx(prop={"age_max_dirigeant": 40, "siren": "9"}), AGE_P)
    assert v.result == CascadeVerdict.PASS               # <55 → pas de signal, mais pas d'inconnu


def test_age_absent_unknown():
    # absence (gigogne plafonnée, non-diffusible) → UNKNOWN, jamais un malus
    assert AgeDirigeantLayer().evaluate(_P(), _Ctx(prop=None), AGE_P).result == CascadeVerdict.UNKNOWN
    assert AgeDirigeantLayer().evaluate(_P(), _Ctx(prop={"age_max_dirigeant": None}), AGE_P).result == CascadeVerdict.UNKNOWN


def test_age_invalide_moins_18_unknown():
    v = AgeDirigeantLayer().evaluate(_P(), _Ctx(prop={"age_max_dirigeant": 5, "siren": "9"}), AGE_P)
    assert v.result == CascadeVerdict.UNKNOWN            # fiche RNE incohérente → invalide, pas de points


# ── BODACC machine à états ──

def test_bodacc_rouge_bascule():
    v = BodaccLayer().evaluate(_P(), _Ctx(bod={"type_procedure": "Jugement de conversion en liquidation judiciaire", "siren": "S1"}), BODACC_P)
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.INFO   # flag 0 point
    assert v.extra["evenement"] == "rouge"              # → bascule chaude
    assert v.extra["source_table"] == "v_foncier_sous_pression" and v.extra["source_id"] == "S1"


def test_bodacc_gris_pas_de_bascule():
    v = BodaccLayer().evaluate(_P(), _Ctx(bod={"type_procedure": "Jugement de clôture pour insuffisance d'actif", "siren": "S2"}), BODACC_P)
    assert "evenement" not in v.extra                    # clôture ≠ bascule


def test_bodacc_neutre_liste_creances_pas_de_bascule():
    v = BodaccLayer().evaluate(_P(), _Ctx(bod={"type_procedure": "Liste des créances nées après le jugement d'ouverture d'une procédure de liquidation judiciaire", "siren": "S3"}), BODACC_P)
    assert v.result == CascadeVerdict.SOFT_FLAG and "evenement" not in v.extra   # NEUTRE (Vic)


def test_bodacc_mojibake_normalise():
    # mojibake d'un libellé ORANGE → reconnu (sinon tomberait en neutre)
    v = BodaccLayer().evaluate(_P(), _Ctx(bod={"type_procedure": "Jugement arrÃªtant le plan de sauvegarde", "siren": "S4"}), BODACC_P)
    assert "sous plan" in v.detail and "evenement" not in v.extra


def test_bodacc_absent_pass():
    assert BodaccLayer().evaluate(_P(), _Ctx(bod=None), BODACC_P).result == CascadeVerdict.PASS


# ── DPE passoire ──

def test_dpe_passoire_flag():
    v = DpePassoireLayer().evaluate(_P(), _Ctx(pas={"etiquette_dpe": "G"}), {})
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.INFO
    assert "2028" in v.detail and v.extra["source_table"] == "v_passoire_thermique"


def test_dpe_absent_pass():
    assert DpePassoireLayer().evaluate(_P(), _Ctx(pas=None), {}).result == CascadeVerdict.PASS
