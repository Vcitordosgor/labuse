"""SCORING-6 lot D — Signal de mutation V2 (recette q_v15 + niveaux). Tests PURS (sans base)."""
import pytest

from labuse.scoring.p_v2 import qv14, qv15
from labuse.scoring.signal_mutation import (NIVEAU_FAIBLE, NIVEAU_FORT,
                                            NIVEAU_MOYEN, signal_niveau,
                                            signal_version)
from labuse.scoring.p_v2.statuts import PaliersConfig


def test_qv15_est_qv14_moins_piscine_pv():
    n14, _, _ = qv14.features_qv14()
    n15, s15, i15 = qv15.features_qv15()
    # sous-ensemble STRICT, exactement les deux features retirées, aucune variable nouvelle.
    assert set(n15) < set(n14)
    assert set(n14) - set(n15) == {"piscine", "pv_candidat"}
    assert set(n15) - set(n14) == set()
    assert all(s.name not in ("piscine", "pv_candidat") for s in s15)
    assert all("piscine" not in (a, b) and "pv_candidat" not in (a, b) for a, b in i15)


def test_qv15_respecte_le_flag_ventes_pm():
    with_pm, _, _ = qv15.features_qv15(avec_ventes_pm=True)
    sans_pm, _, _ = qv15.features_qv15(avec_ventes_pm=False)
    assert "ventes_pm_secteur_36m" in with_pm
    assert "ventes_pm_secteur_36m" not in sans_pm
    assert len(sans_pm) == len(with_pm) - 1


def test_niveaux_seuils_absolus_paliers1():
    cfg = PaliersConfig()          # entree_priorite=0.20, entree_a_suivre=0.10
    assert signal_niveau(0.25, cfg) == NIVEAU_FORT
    assert signal_niveau(0.20, cfg) == NIVEAU_FORT          # borne incluse
    assert signal_niveau(0.1999, cfg) == NIVEAU_MOYEN
    assert signal_niveau(0.10, cfg) == NIVEAU_MOYEN         # borne incluse
    assert signal_niveau(0.0999, cfg) == NIVEAU_FAIBLE
    assert signal_niveau(0.0, cfg) == NIVEAU_FAIBLE


def test_niveau_p_indefini():
    assert signal_niveau(None) is None
    assert signal_niveau(float("nan")) is None


def test_signal_version():
    assert signal_version() == "signal_v2+q_v15"
    assert signal_version("q_v15_20261015") == "signal_v2+q_v15_20261015"


def test_verify_artifacts_absent_echoue_proprement():
    # Le fit/gel est un geste de Vic : sans artefact, refus explicite (jamais un modèle deviné).
    with pytest.raises(RuntimeError, match="q_v15|arène|Vic"):
        qv15.verify_artifacts()
