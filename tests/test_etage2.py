"""Couches ÉTAGE 2 (dry-run) — âge dirigeant (courbe + UNKNOWN si absent), BODACC (machine à états
sur libellés réels + bascule rouge). Tests unitaires via ctx factice.
M71 B1 : DpePassoireLayer retirée du scoring (audits M66/M66-B) — tests supprimés avec elle."""
from __future__ import annotations

from labuse.cascade.layers.etage2 import AgeDirigeantLayer, BodaccLayer
from labuse.enums import CascadeVerdict, Severity

# FIX-AGE-DIRIGEANT (décision Vic, I4) — courbe alignée sur la config servie : 0 point partout.
AGE_P = {"bonus_key": "age_dirigeant", "courbe": {55: 0, 65: 0, 75: 0, 85: 0}, "age_min_valide": 18}
BODACC_P = {
    "etats": {
        "rouge": ["Jugement de conversion en liquidation judiciaire", "Autre jugement d'ouverture"],
        "orange": ["Jugement arrêtant le plan de sauvegarde"],
        "gris": ["Jugement de clôture pour insuffisance d'actif"]},
    "mojibake": {"Jugement arrÃªtant le plan de sauvegarde": "Jugement arrêtant le plan de sauvegarde"},
}


class _Ctx:
    def __init__(self, prop=None, bod=None, pas=None, sondage=None):
        self._p, self._b, self._s = prop, bod, sondage

    def propension(self, pid):
        return self._p

    def bodacc(self, pid):
        return self._b

    def bodacc_sondage(self, pid):   # M70 déc. 3 — journal de sondage BODACC par propriétaire
        return self._s


class _P:
    id = 1
    idu = "97415000AA0001"


# ── âge dirigeant ──

def test_age_contexte_zero_point():
    # FIX-AGE-DIRIGEANT (décision Vic, I4) — l'âge du dirigeant NE SCORE PLUS : ligne de CONTEXTE
    # (flag INFO = ×0), jamais un POSITIVE. L'info reste visible + tracée (source), 0 point.
    for age in (60, 70, 80, 90):
        v = AgeDirigeantLayer().evaluate(_P(), _Ctx(prop={"age_max_dirigeant": age, "siren": "9"}), AGE_P)
        assert v.result == CascadeVerdict.SOFT_FLAG
        assert v.bonus_key is None                       # aucune clé de bonus → aucun point
        assert v.severity == Severity.INFO               # ×0
        assert "score" in v.detail.lower()               # dit qu'elle n'entre pas dans le score
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
    # M70 déc. 3 — pas de procédure ET pas de propriétaire PM → « sans objet » (PASS honnête).
    v = BodaccLayer().evaluate(_P(), _Ctx(bod=None, sondage=None), BODACC_P)
    assert v.result == CascadeVerdict.PASS and "sans objet" in v.detail


def test_bodacc_sonde_rien_pass_date():
    # M70 déc. 3 — propriétaire sondé, rien trouvé → PASS avec la date (jamais l'affirmation nue).
    from datetime import date
    v = BodaccLayer().evaluate(_P(), _Ctx(bod=None, sondage={"siren": "123456789", "resultat": "rien", "sonde_le": date(2026, 8, 6)}), BODACC_P)
    assert v.result == CascadeVerdict.PASS and "sondé le 06/08/2026" in v.detail


def test_bodacc_non_sondable_unknown():
    # M70 déc. 3 — siren non sondable / jamais sondé → UNKNOWN « non concluant », pas PASS.
    v = BodaccLayer().evaluate(_P(), _Ctx(bod=None, sondage={"siren": "U12345", "resultat": "non_sondable", "sonde_le": None}), BODACC_P)
    assert v.result == CascadeVerdict.UNKNOWN and "non concluant" in v.detail

