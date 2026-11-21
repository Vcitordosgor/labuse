"""REMISE-1 / FAISA-REGLES-1 (E-056) — plafonds de stationnement du Code de l'urbanisme, UN TEST PAR CAS.

Règle (art. L151-35 / L151-36), rayon porté de 500 à **800 m** par la loi n° 2025-1129 du 26/11/2025 :
  · **L151-35** — logement locatif aidé, résidence pour personnes âgées (senior), résidence universitaire
    (étudiante) : au plus **1 place/logement**, abaissé à **0,5** À MOINS DE 800 m d'un transport collectif
    en site propre bien desservi.
  · **L151-36** — TOUS LES AUTRES logements (« collectif » de droit commun) : au plus **1 place/logement**,
    et SEULEMENT à moins de 800 m d'un tel transport (au-delà, aucun plafond national).

Deux lecteurs doivent dire EXACTEMENT la même chose :
  · `moteur._plafond_l151` — la règle APPLIQUÉE (ce qui fixe le nombre de places dessinées) ;
  · `service._stationnement_regimes` — la règle AFFICHÉE (bloc « plafond national » de l'étude).

Tests unitaires (pas de base) : on monkeypatche la DISTANCE au TCSP (`moteur._tcsp_dist_m`, source unique
des deux lecteurs). Le cas « 600 m » prouve le passage 500 → 800 m : hors plafond avant, plafonné désormais.
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
    """Fixe la distance au TCSP vue par les DEUX lecteurs (moteur + service via _tcsp_sous_rayon)."""
    def _set(d):
        monkeypatch.setattr(M, "_tcsp_dist_m", lambda *_a, **_k: d)
    return _set


# ── règle APPLIQUÉE (moteur._plafond_l151) ────────────────────────────────────────────────

# FIX-4 (LOT 2) — `_plafond_l151` renvoie (cap_appliqué, article, citation, cap_conditionnel). Le plafond
# fondé sur la DESSERTE (0,5 aidé < 800 m, 1 collectif < 800 m) n'est PLUS appliqué d'office (desserte non
# connue) : il est CONDITIONNEL. Appliqués d'office : 0,5 univ/âgées (usage) et 1 /logt aidé (base L151-35).
@pytest.mark.parametrize("type_projet,dist,attendu_art,cap_applique,cap_conditionnel", [
    ("etudiante", 7817, "L151-35", 0.5, None),   # résidence universitaire → 0,5 ferme (usage, pas desserte)
    ("etudiante", 120,  "L151-35", 0.5, None),
    ("senior",    300,  "L151-35", 0.5, None),
    ("social",    900,  "L151-35", 1.0, None),   # aidé hors 800 m → 1 /logt, aucun conditionnel
    ("social",    600,  "L151-35", 1.0, 0.5),    # aidé < 800 m → appliqué 1 /logt, 0,5 POSSIBLE si desserte établie
    ("collectif", 600,  "L151-36", None, 1.0),   # collectif < 800 m → plafond 1 CONDITIONNEL, PAS appliqué d'office
])
def test_plafond_applique_par_cas(tcsp, type_projet, dist, attendu_art, cap_applique, cap_conditionnel):
    tcsp(dist)
    res = M._plafond_l151(None, ["x"], type_projet, _bareme())
    assert res is not None, f"{type_projet}@{dist}m : un plafond (appliqué ou conditionnel) devait exister"
    cap, art, _cite, cond = res
    assert art == attendu_art
    assert cap == cap_applique, f"{type_projet}@{dist}m appliqué"
    assert cond == cap_conditionnel, f"{type_projet}@{dist}m conditionnel"


def test_plafond_applique_collectif_hors_800m_aucun(tcsp):
    """L151-36 N'EXISTE PAS au-delà de 800 m → aucun plafond national pour un collectif éloigné."""
    tcsp(900)
    assert M._plafond_l151(None, ["x"], "collectif", _bareme()) is None


def test_plafond_ne_mord_pas_si_exigence_deja_plus_favorable():
    """FIX-3 (LOT 3) — le plafond ne « mord » que s'il est SOUS l'exigence du PROGRAMME : la comparaison se
    fait désormais au niveau de `exiger._cap_plafond` (exigence réelle, ligne aidée comprise), plus dans
    `_plafond_l151` (qui comparait au forfait général et sautait le plafond à tort). Un barème qui exige
    déjà ≤ 1 place/logt n'est pas relevé par un plafond de 1/logt."""
    from dataclasses import replace
    from labuse.implantation import regles as R
    from types import SimpleNamespace as NS
    b = R.charger("97405", "UB").stationnement        # 1 place/logt (≤ plafond 1)
    mods = [NS(pieces=3, surface_m2=70.0) for _ in range(20)]
    base = b.exiger(mods, destination="collectif").places
    capped = replace(b, plafond_national={"ratio": 1.0, "article": "L151-35"}).exiger(
        mods, destination="collectif").places
    assert capped == base, "un plafond de 1/logt ne doit pas relever une exigence déjà ≤ 1/logt"


# ── règle AFFICHÉE (service._stationnement_regimes) — doit coller à l'appliquée ────────────

@pytest.mark.parametrize("type_projet,dist,ref,ratio,ratio_cond,cond", [
    ("etudiante", 7817, "L151-35", 0.5, None, False),   # univ → 0,5 ferme ; condition 800 m NON remplie
    ("etudiante", 120,  "L151-35", 0.5, None, True),
    ("senior",    300,  "L151-35", 0.5, None, True),
    ("social",    900,  "L151-35", 1.0, None, False),   # aidé hors 800 m → 1 /logt, pas de 0,5 conditionnel
    ("social",    600,  "L151-35", 1.0, 0.5,  True),    # FIX-4 : aidé < 800 m → affiché 1, 0,5 CONDITIONNEL
    ("collectif", 600,  "L151-36", 1.0, None, True),    # collectif < 800 m → plafond possible affiché
])
def test_regime_affiche_par_cas(tcsp, type_projet, dist, ref, ratio, ratio_cond, cond):
    tcsp(dist)
    pf = S._stationnement_regimes(None, ["x"], type_projet, _regles(), "97404")["plafond_national"]
    assert pf is not None, f"{type_projet}@{dist}m : un régime devait être affiché"
    assert pf["reference"] == ref
    assert pf["ratio_plafond"] == ratio
    assert pf.get("ratio_conditionnel") == ratio_cond   # FIX-4 : 0,5 POSSIBLE (aidé < 800 m), non imposé
    assert pf["condition_tcsp_sous_500m"] is cond   # clé historique conservée (lue par l'écran)
    assert pf["rayon_tcsp_m"] == 800                # E-056 — seuil porté à 800 m (loi 2025-1129)
    assert ref in pf["citation"]
    if ratio_cond:
        assert "POSSIBLE" in pf["citation"] and "800 m" in pf["citation"] and "2025-1129" in pf["citation"]


def test_regime_collectif_hors_800m_aucun_plafond(tcsp):
    """Au-delà de 800 m, un collectif n'a AUCUN plafond national affiché (seule la règle PLU s'applique)."""
    tcsp(900)
    assert S._stationnement_regimes(None, ["x"], "collectif", _regles(), "97404")["plafond_national"] is None


def test_regime_lotissement_aucun_plafond(tcsp):
    """Un lotissement n'est pas un programme de logements → aucun plafond L151-35/36."""
    tcsp(100)
    assert S._stationnement_regimes(None, ["x"], "lotissement", _regles(), "97404")["plafond_national"] is None


def test_affiche_egale_applique_sur_le_ratio(tcsp):
    """Garde-fou de cohérence : pour une étudiante < 800 m, le ratio AFFICHÉ == le ratio APPLIQUÉ (0,5)."""
    tcsp(120)
    pf = S._stationnement_regimes(None, ["x"], "etudiante", _regles(), "97404")["plafond_national"]
    cap, _art, _c, _cond = M._plafond_l151(None, ["x"], "etudiante", _bareme())
    assert pf["ratio_plafond"] == cap == 0.5


def test_social_sous_800m_garde_exigence_locale(tcsp):
    """FIX-4 (LOT 2) — un logement AIDÉ à moins de 800 m : le 0,5 n'est PAS appliqué d'office (desserte non
    établie). Le plafond appliqué reste 1 /logt ; le 0,5 est affiché « possible »."""
    tcsp(600)
    cap, _art, _c, cond = M._plafond_l151(None, ["x"], "social", _bareme())
    assert cap == 1.0 and cond == 0.5
    pf = S._stationnement_regimes(None, ["x"], "social", _regles(), "97404")["plafond_national"]
    assert pf["ratio_plafond"] == 1.0 and pf["ratio_conditionnel"] == 0.5
