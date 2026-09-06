"""Témoin CIRCUIT-4 — prix de secteur : trim 5 % et médiane recalculés INDÉPENDAMMENT
(médiane tronquée classique), comparés aux fonctions du moteur sur les mêmes entrées."""
from __future__ import annotations

import statistics

from labuse.faisabilite.bilan import TRIM_EXTREMES_FRAC, distribution_secteur, trim_extremes_5pct


def test_trim_et_mediane_independants():
    prices = [float(p) for p in
              [900, 1500, 1800, 2000, 2100, 2200, 2300, 2350, 2400, 2500,
               2600, 2700, 2800, 2900, 3000, 3100, 3200, 3400, 3600, 3800,
               4000, 4200, 4500, 5000, 6000, 7000, 8000, 9000, 11000, 15000]]
    kept, lo, hi = trim_extremes_5pct(prices)
    # ── recalcul indépendant : k = ⌊n × 2,5 %⌋ retiré à chaque queue du tri ──
    xs = sorted(prices)
    k = int(len(xs) * (TRIM_EXTREMES_FRAC / 2))
    attendu = xs[k:len(xs) - k] if k else xs
    assert sorted(kept) == attendu and k == 0 or sorted(kept) == attendu
    assert len(kept) == len(attendu)
    d = distribution_secteur(kept)
    assert d["median"] == round(statistics.median(kept))


def test_petit_echantillon_non_trime():
    prices = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]   # n=5 → k = ⌊5×0,025⌋ = 0
    kept, lo, hi = trim_extremes_5pct(prices)
    assert sorted(kept) == sorted(prices) and lo is None and hi is None
