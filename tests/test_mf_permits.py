"""M-F (P1-6) — fraîcheur des permis dans rebuild_features : build_permits intégré + garde double
+ compteur au rapport. Tests PURS (fausse session) et source-level."""
from __future__ import annotations

import datetime
import inspect

import pytest

from labuse.scoring.p_v2 import pipeline as P


class _Res:
    def __init__(self, first=None, scalar=None):
        self._first, self._scalar = first, scalar

    def first(self):
        return self._first

    def scalar(self):
        return self._scalar


class _FakeSession:
    """execute() router : p_model_permits → (max, count) ; sitadel_permits → max source."""
    def __init__(self, feat_first, src_scalar):
        self.feat, self.src = feat_first, src_scalar

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "p_model_permits" in sql:
            return _Res(first=self.feat)
        if "sitadel_permits" in sql:
            return _Res(scalar=self.src)
        return _Res()


_D = datetime.date


def test_garde_passe_si_features_a_jour():
    """Features à jour avec la source (gap 0) → pas d'échec, compteur renvoyé."""
    st = P.check_permits_fraicheur(_FakeSession((_D(2026, 6, 30), 59262), _D(2026, 6, 30)))
    assert st["gap_jours"] == 0 and st["n_permits"] == 59262
    assert st["permits_max"] == "2026-06-30" and st["src_max"] == "2026-06-30"


def test_garde_echoue_si_permis_perimes():
    """Validation #3 : features en RETARD sur la source → échec BRUYANT (pas un warning muet)."""
    with pytest.raises(RuntimeError, match="FRAÎCHEUR PERMIS|RETARD"):
        P.check_permits_fraicheur(_FakeSession((_D(2026, 5, 1), 100), _D(2026, 6, 30)))


def test_garde_echoue_si_features_vides():
    """Aucun permis en features alors que la source en a → échec (build_permits n'a pas tourné)."""
    with pytest.raises(RuntimeError):
        P.check_permits_fraicheur(_FakeSession((None, 0), _D(2026, 6, 30)))


def test_garde_tolere_source_absente():
    """Pas de source (sitadel vide) → rien à garder, pas d'échec."""
    st = P.check_permits_fraicheur(_FakeSession((_D(2026, 6, 30), 100), None))
    assert st["gap_jours"] is None and st["src_max"] is None


def test_garde_respecte_le_seuil():
    """Un écart sous le seuil justifié ne bloque pas ; au-dessus, il bloque."""
    fs = _FakeSession((_D(2026, 6, 28), 100), _D(2026, 6, 30))   # 2 j de retard
    assert P.check_permits_fraicheur(fs, seuil_jours=3)["gap_jours"] == 2   # toléré
    with pytest.raises(RuntimeError):
        P.check_permits_fraicheur(fs, seuil_jours=1)                        # dépasse le seuil


# ── source-level : build_permits intégré AVANT le dataset, compteur au rapport ──
def test_rebuild_features_rafraichit_les_permis():
    src = inspect.getsource(P.rebuild_features)
    assert "build_permits" in src, "build_permits pas intégré à rebuild_features (P1-6)"
    assert "check_permits_fraicheur" in src, "garde de fraîcheur absente du rebuild"
    # build_permits AVANT build_ext_dataset (qui consomme p_model_permits en lecture seule)
    assert src.index("build_permits") < src.index("build_ext_dataset")


def test_run_score_v2_rapporte_le_compteur_permis():
    src = inspect.getsource(P.run_score_v2)
    assert '"permits"' in src or "'permits'" in src, "compteur permis absent du rapport de build"
