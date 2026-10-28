"""REMISE-1 — plafonds de stationnement du Code de l'urbanisme (règle de Vic), UN TEST PAR CAS.

Règle (art. L151-35 / L151-36) :
  · **L151-35** — logement locatif aidé, résidence pour personnes âgées (senior), résidence universitaire
    (étudiante) : au plus **1 place/logement**, abaissé à **0,5** À MOINS DE 500 m d'un transport collectif
    en site propre bien desservi.
  · **L151-36** — TOUS LES AUTRES logements (« collectif » de droit commun) : au plus **1 place/logement**,
    et SEULEMENT à moins de 500 m d'un tel transport (au-delà, aucun plafond national).

Deux lecteurs doivent dire EXACTEMENT la même chose :
  · `moteur._plafond_l151` — la règle APPLIQUÉE (ce qui fixe le nombre de places dessinées) ;
  · `service._stationnement_regimes` — la règle AFFICHÉE (bloc « plafond national » de l'étude).

Tests unitaires (pas de base) : on monkeypatche la DISTANCE au TCSP (`moteur._tcsp_dist_m`, source unique
des deux lecteurs). La fiche réelle du témoin L'Étang-Salé (étudiante, 7 817 m → L151-35 à 1 place/logt) est
couverte par `test_etude_v6_8_pdf::test_item1` (reel).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labuse.implantation import moteur as M
from labuse.implantation import service as S


def _bareme(flat=2.0, validee=True, mode="par_logement"):
    """Barème PLU factice (volontairement PERMISSIF : 2 places/logt) pour que le plafond légal MORDE."""
    return SimpleNamespace(flat_places=flat, validee=validee, mode=mode, article="UA 2.7.3",
                           page_pdf=21, citation="PLU", lignes=[])


def _regles(bareme=None):
    return SimpleNamespace(stationnement=bareme or _bareme())


@pytest.fixture
def tcsp(monkeypatch):
    """Fixe la distance au TCSP vue par les DEUX lecteurs (moteur + service via _tcsp_sous_500m)."""
    def _set(d):
        monkeypatch.setattr(M, "_tcsp_dist_m", lambda *_a, **_k: d)
    return _set


# ── règle APPLIQUÉE (moteur._plafond_l151) ────────────────────────────────────────────────

@pytest.mark.parametrize("type_projet,dist,attendu_art,attendu_ratio", [
    ("etudiante", 7817, "L151-35", 1.0),   # témoin L'Étang-Salé : étudiante, loin d'un TCSP → 1/logt
    ("etudiante", 120,  "L151-35", 0.5),   # étudiante < 500 m → 0,5
    ("senior",    300,  "L151-35", 0.5),   # senior < 500 m → 0,5
    ("social",    900,  "L151-35", 1.0),   # social hors 500 m → 1/logt
    ("collectif", 300,  "L151-36", 1.0),   # autres logements < 500 m → L151-36, 1/logt
])
def test_plafond_applique_par_cas(tcsp, type_projet, dist, attendu_art, attendu_ratio):
    tcsp(dist)
    res = M._plafond_l151(None, ["x"], type_projet, _bareme())
    assert res is not None, f"{type_projet}@{dist}m : un plafond devait s'appliquer"
    cap, art, _cite = res
    assert art == attendu_art
    assert cap == attendu_ratio


def test_plafond_applique_collectif_hors_500m_aucun(tcsp):
    """L151-36 N'EXISTE PAS au-delà de 500 m → aucun plafond national pour un collectif éloigné."""
    tcsp(900)
    assert M._plafond_l151(None, ["x"], "collectif", _bareme()) is None


def test_plafond_ne_mord_pas_si_plu_deja_plus_favorable(tcsp):
    """La loi ne « mord » que si elle plafonne SOUS la règle PLU : PLU 0,5/logt ≤ L151-35 1 → None."""
    tcsp(7817)
    assert M._plafond_l151(None, ["x"], "etudiante", _bareme(flat=0.5)) is None


# ── règle AFFICHÉE (service._stationnement_regimes) — doit coller à l'appliquée ────────────

@pytest.mark.parametrize("type_projet,dist,ref,ratio,cond", [
    ("etudiante", 7817, "L151-35", 1.0, False),   # témoin : affiché 1/logt, condition 500 m NON remplie
    ("etudiante", 120,  "L151-35", 0.5, True),
    ("senior",    300,  "L151-35", 0.5, True),
    ("social",    900,  "L151-35", 1.0, False),
    ("collectif", 300,  "L151-36", 1.0, True),
])
def test_regime_affiche_par_cas(tcsp, type_projet, dist, ref, ratio, cond):
    tcsp(dist)
    pf = S._stationnement_regimes(None, ["x"], type_projet, _regles(), "97404")["plafond_national"]
    assert pf is not None, f"{type_projet}@{dist}m : un régime devait être affiché"
    assert pf["reference"] == ref
    assert pf["ratio_plafond"] == ratio
    assert pf["condition_tcsp_sous_500m"] is cond
    assert "condition_tcsp_sous_800m" not in pf          # l'ancien seuil 800 m a disparu
    assert ref in pf["citation"] and "500 m" in pf["citation"]


def test_regime_collectif_hors_500m_aucun_plafond(tcsp):
    """Au-delà de 500 m, un collectif n'a AUCUN plafond national affiché (seule la règle PLU s'applique)."""
    tcsp(900)
    assert S._stationnement_regimes(None, ["x"], "collectif", _regles(), "97404")["plafond_national"] is None


def test_regime_lotissement_aucun_plafond(tcsp):
    """Un lotissement n'est pas un programme de logements → aucun plafond L151-35/36."""
    tcsp(100)
    assert S._stationnement_regimes(None, ["x"], "lotissement", _regles(), "97404")["plafond_national"] is None


def test_affiche_egale_applique_sur_le_ratio(tcsp):
    """Garde-fou de cohérence : pour une étudiante < 500 m, le ratio AFFICHÉ == le ratio APPLIQUÉ (0,5)."""
    tcsp(120)
    pf = S._stationnement_regimes(None, ["x"], "etudiante", _regles(), "97404")["plafond_national"]
    cap, _art, _c = M._plafond_l151(None, ["x"], "etudiante", _bareme())
    assert pf["ratio_plafond"] == cap == 0.5
