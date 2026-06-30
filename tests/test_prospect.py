"""Hauteur prospect (Ud/Uu) — largeur de façade + plancher 10 m. Mock session, ZÉRO base/réseau."""
from __future__ import annotations

from labuse.faisabilite.db import _facade_largeur, _prospect_hauteur


class _FakeSession:
    """Session minimale : .execute(...).all() renvoie les lignes (largeur, nature) fournies."""
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *a, **k):
        rows = self._rows

        class _R:
            def all(self):
                return rows
        return _R()


def _largeur(rows):
    return _facade_largeur(_FakeSession(rows), 1, "Saint-Denis")


# ── _prospect_hauteur : plancher 10 m ─────────────────────────────────────────
def test_prospect_hauteur_plancher():
    assert _prospect_hauteur(4.0) == 10.0      # chaussée étroite → plancher
    assert _prospect_hauteur(14.0) == 14.0     # avenue large → largeur réelle
    assert _prospect_hauteur(None) == 10.0     # aucune voie → plancher
    assert _prospect_hauteur(0.0) == 10.0      # largeur dégénérée → plancher


# ── _facade_largeur : réel / classe / dégénéré / aucune / multi-façades ───────
def test_facade_largeur_reel():
    assert _largeur([(5.5, "Route à 1 chaussée")]) == (5.5, "reel")


def test_facade_largeur_fallback_classe():
    # largeur NULL → défaut par nature
    assert _largeur([(None, "Chemin")]) == (4.0, "classe")
    assert _largeur([(None, "Route à 2 chaussées")]) == (14.0, "classe")


def test_facade_largeur_zero_degenere_va_en_fallback():
    # largeur 0 = dégénérée → PAS 'reel', on retombe sur la classe.
    assert _largeur([(0.0, "Route à 1 chaussée")]) == (6.0, "classe")


def test_facade_largeur_aucune():
    assert _largeur([]) == (None, "aucune")                     # aucune voie ≤ 25 m
    assert _largeur([(None, "Sentier")]) == (None, "aucune")    # sentier = pas une desserte


def test_facade_largeur_multi_facades_prend_la_plus_large():
    rows = [(4.0, "Route à 1 chaussée"), (12.0, "Route à 2 chaussées")]
    assert _largeur(rows) == (12.0, "reel")                     # la plus large
    # mix réel/classe : on compare les largeurs effectives
    rows2 = [(None, "Chemin"), (None, "Route à 2 chaussées")]
    assert _largeur(rows2) == (14.0, "classe")


# ═══════════ A3 : le hook moteur (gating prospect + non-régression) ═══════════
from labuse.faisabilite import db as _fdb                           # noqa: E402
from labuse.faisabilite.engine import Contraintes, estimate_capacity  # noqa: E402
from labuse.faisabilite.plu_rules import ZoneRules, _has_usable_height  # noqa: E402


class _Row:
    full_area = 600.0
    uau_area = None
    er_area = 0.0


class _Res:
    def one(self):
        return _Row()

    def one_or_none(self):
        return _Row()

    def __iter__(self):
        return iter([])          # _ECO / _ER_DETAILS → vides


class _Sess:
    def execute(self, *a, **k):
        return _Res()


def _ctx():
    c = type("Ctx", (), {})()
    c.parcel_id, c.idu, c.commune = 1, "97411000AB0001", "Saint-Denis"
    c.surface_m2, c.zone = 1000.0, "Ud"
    c.contraintes, c.prescriptions_eco = Contraintes(), {}
    return c


def _run_hook(monkeypatch, hauteur_mode):
    """Exécute parcel_faisabilite avec ctx + règle mockés ; renvoie (Faisabilite, appels_facade)."""
    calls = []
    monkeypatch.setattr(_fdb, "parcel_context", lambda s, pid: _ctx())
    monkeypatch.setattr(_fdb, "resolve_zone", lambda z, c: ZoneRules(
        code="Ud", emprise_sol_pct=80.0, recul_limites_sep_m=4, hauteur_mode=hauteur_mode,
        he_m=("a_verifier" if hauteur_mode else 7), hf_m=("a_verifier" if hauteur_mode else 10)))
    monkeypatch.setattr(_fdb, "_facade_largeur", lambda s, pid, c: (calls.append(pid), (None, "aucune"))[1])
    res = _fdb.parcel_faisabilite(_Sess(), 1)
    return res, calls


def test_hook_prospect_appelle_facade_et_override(monkeypatch):
    res, calls = _run_hook(monkeypatch, "prospect")
    assert res is not None
    _ctx_out, f = res
    assert calls == [1]                       # _facade_largeur APPELÉ (zone prospect)
    assert f.constructible and f.calibree is True
    assert f.fourchette["niveaux_max"] == 2   # hf=10 (plancher, voie 'aucune') → 2 niveaux (R+1)


def test_hook_non_prospect_ne_declenche_pas(monkeypatch):
    res, calls = _run_hook(monkeypatch, None)
    assert res is not None
    assert calls == []                        # _facade_largeur PAS appelé (zone non-prospect)


def test_has_usable_height_prospect():
    # prospect = exploitable MÊME avec he/hf 'a_verifier'
    assert _has_usable_height(ZoneRules(code="Ud", hauteur_mode="prospect",
                                        he_m="a_verifier", hf_m="a_verifier")) is True
    # sans prospect ni hauteur chiffrée → non exploitable
    assert _has_usable_height(ZoneRules(code="X", he_m="a_verifier", hf_m="a_verifier")) is False


def test_estimate_capacity_hf10_emprise80():
    r = ZoneRules(code="Ud", emprise_sol_pct=80.0, hf_m=10.0, recul_limites_sep_m=4)
    f = estimate_capacity(r, 1000.0, emprise_geo=(600.0, 4.0))
    assert f.constructible and f.fourchette["niveaux_max"] == 2   # hf 10 m → R+1
