"""PPR-PARTIEL-FIX-1 (étape B) — verrou de `surface_hors_ppr_rouge` : la partie HORS zone rouge
d'une parcelle partiellement rouge servie à 0.

Tests PURS (sans base) : on injecte le résultat de faisabilité (`faisa`) et une fausse session
dont la requête géométrique rend des aires contrôlées. On vérifie la règle du mandat :
  · parcelle touchant du rouge, servie 0 pour ppr_rouge, 2 000 m² hors rouge → badge servi ;
  · même parcelle avec 150 m² hors rouge (< 200) → rien ;
  · parcelle sans rouge (motif ≠ ppr_rouge) → rien ;
  · découpage rouge-seul qui échoue (géométrie invalide) → rien (jamais un chiffre douteux).
"""
from __future__ import annotations

from types import SimpleNamespace

from labuse.faisabilite.db import SEUIL_HORS_PPR_ROUGE_M2, surface_hors_ppr_rouge


class _Row(SimpleNamespace):
    pass


class _FakeSession:
    """Session minimale : `begin_nested()` (SAVEPOINT) + `execute().first()` → une aire contrôlée.
    `raise_on_execute` simule une géométrie invalide (ST_* lève)."""

    def __init__(self, parcelle_m2, rouge_m2, raise_on_execute=False):
        self._row = _Row(parcelle_m2=parcelle_m2, rouge_m2=rouge_m2)
        self._raise = raise_on_execute

    def begin_nested(self):
        session = self

        class _Ctx:
            def __enter__(self):
                return session

            def __exit__(self, *a):
                return False
        return _Ctx()

    def execute(self, *a, **k):
        if self._raise:
            raise RuntimeError("TopologyException: side location conflict")
        return SimpleNamespace(first=lambda: self._row)


def _faisa(cause="terrain_exigu", exigu_raison="ppr_rouge"):
    return (None, SimpleNamespace(cause=cause, exigu_raison=exigu_raison))


def test_badge_servi_si_2000_m2_hors_rouge():
    # 2 500 m², 500 m² rouge → 2 000 m² hors rouge (80 % de la parcelle) → badge.
    s = _FakeSession(parcelle_m2=2500.0, rouge_m2=500.0)
    res = surface_hors_ppr_rouge(s, 1, faisa=_faisa())
    assert res == {"hors_rouge_m2": 2000, "pct": 80}


def test_rien_si_150_m2_hors_rouge():
    # même parcelle, 2 350 m² rouge → 150 m² hors rouge (< 200) → rien (terrain exigu correct).
    s = _FakeSession(parcelle_m2=2500.0, rouge_m2=2350.0)
    assert surface_hors_ppr_rouge(s, 1, faisa=_faisa()) is None


def test_seuil_200_exact():
    # bord : exactement 200 m² hors rouge → servi ; 199 → rien.
    assert SEUIL_HORS_PPR_ROUGE_M2 == 200.0
    s_ok = _FakeSession(parcelle_m2=1000.0, rouge_m2=800.0)        # 200 hors rouge
    assert surface_hors_ppr_rouge(s_ok, 1, faisa=_faisa()) == {"hors_rouge_m2": 200, "pct": 20}
    s_ko = _FakeSession(parcelle_m2=1000.0, rouge_m2=801.0)        # 199 hors rouge
    assert surface_hors_ppr_rouge(s_ko, 1, faisa=_faisa()) is None


def test_rien_sans_rouge():
    # parcelle servie 0 pour un AUTRE motif (ex. emplacement réservé) → pas le gisement → rien,
    # même si géométriquement il resterait du foncier.
    s = _FakeSession(parcelle_m2=2500.0, rouge_m2=100.0)
    assert surface_hors_ppr_rouge(s, 1, faisa=_faisa(exigu_raison="emplacement_reserve")) is None
    # parcelle calculée (constructible, pas de cause) → rien.
    assert surface_hors_ppr_rouge(s, 1, faisa=_faisa(cause=None, exigu_raison=None)) is None


def test_rien_si_decoupage_echoue():
    # géométrie invalide / PPR superposés pathologiques : on n'affiche rien (jamais un chiffre douteux).
    s = _FakeSession(parcelle_m2=2500.0, rouge_m2=500.0, raise_on_execute=True)
    assert surface_hors_ppr_rouge(s, 1, faisa=_faisa()) is None


def test_phrase_unique_chiffre():
    from labuse.faisabilite.db import phrase_hors_ppr_rouge
    p = phrase_hors_ppr_rouge({"hors_rouge_m2": 4732, "pct": 97})
    assert "4 732 m²" in p and "à étudier" in p and "constructible" not in p.lower()
