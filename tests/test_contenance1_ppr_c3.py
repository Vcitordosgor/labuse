"""CONTENANCE-1 × PPR-PARTIEL-A — l'aire « hors zone rouge » passe par la règle C3.

L'emprise sur la partie hors rouge est déjà ramenée à l'échelle de la contenance (faisabilite/db.py
`emprise_brute *= k_cont`). Ce test verrouille les DEUX autres aires hors-rouge tirées du dessin :
  · le seuil servable 200 m² (`_hors_rouge_fragment_servable`) ;
  · la surface hors rouge AFFICHÉE au badge (`surface_hors_ppr_rouge`).
Les deux doivent être multipliées par contenance/dessin (k_cont), le `pct` restant invariant.
"""
from __future__ import annotations

import types

from labuse.faisabilite.db import (SEUIL_HORS_PPR_ROUGE_M2, _hors_rouge_fragment_servable,
                                    surface_hors_ppr_rouge)


class _Nested:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Sess:
    def __init__(self, row): self._row = row
    def begin_nested(self): return _Nested()
    def execute(self, *a, **k): return types.SimpleNamespace(first=lambda: self._row)


def test_seuil_servable_200_est_a_l_echelle_contenance(monkeypatch):
    # fragment de 250 m² DESSIN qui touche une voie.
    monkeypatch.setattr("labuse.gabarit.limites.classify_parcel_limits",
                        lambda *a, **k: types.SimpleNamespace(has_voie=True))
    s = _Sess(types.SimpleNamespace(wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))", m2=250.0))
    # sans contenance (k=1) : 250 ≥ 200 → servable
    assert _hors_rouge_fragment_servable(s, 1, 1.0) == (True, None)
    # contenance = 70 % du dessin (k=0.7) : 250×0.7 = 175 < 200 → NON servable, motif nommé
    assert _hors_rouge_fragment_servable(s, 1, 0.7) == (False, "hors_rouge_trop_petit")


def test_badge_hors_rouge_est_a_l_echelle_contenance():
    # parcelle 1000 m² dessin, 300 rouge → 700 hors rouge DESSIN. Contenance = moitié (k=0.5).
    row = types.SimpleNamespace(parcelle_m2=1000.0, rouge_m2=300.0)
    ctx = types.SimpleNamespace(terrain_sur_dessin=0.5)
    fa = types.SimpleNamespace(cause="terrain_exigu", exigu_raison="ppr_rouge")
    hp = surface_hors_ppr_rouge(_Sess(row), 1, faisa=(ctx, fa))
    # aire affichée ramenée à l'échelle contenance : 700 × 0,5 = 350 (≥ 200 → servie)
    assert hp == {"hors_rouge_m2": 350, "pct": 70}   # pct = 700/1000 inchangé (rapport de dessins)


def test_badge_sous_seuil_apres_rescale_rien():
    # 700 hors rouge dessin, mais k=0,25 → 175 < 200 : plus rien (le terrain redevient exigu).
    row = types.SimpleNamespace(parcelle_m2=1000.0, rouge_m2=300.0)
    ctx = types.SimpleNamespace(terrain_sur_dessin=0.25)
    fa = types.SimpleNamespace(cause="terrain_exigu", exigu_raison="ppr_rouge")
    assert surface_hors_ppr_rouge(_Sess(row), 1, faisa=(ctx, fa)) is None
    assert SEUIL_HORS_PPR_ROUGE_M2 == 200.0
