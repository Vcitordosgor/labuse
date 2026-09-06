"""Témoin CIRCUIT-4 — composite du comparateur : min-max + moyenne pondérée recalculées
INDÉPENDAMMENT (formule MinMaxScaler citée), comparées à composite_communes."""
from __future__ import annotations

from labuse.registre.moteurs.commune import INDICATEURS, composite_communes


def test_composite_temoin():
    poids = {k: v[2] for k, v in INDICATEURS.items()}
    rows = [
        {"insee": "1", "commune": "A", "stock": 10, "velocite": 12.0, "permis": 100,
         "deficit_sru": 5.0, "pression_zan": 20.0, "prix_neuf": 4000.0},
        {"insee": "2", "commune": "B", "stock": 30, "velocite": 6.0, "permis": 300,
         "deficit_sru": 15.0, "pression_zan": 5.0, "prix_neuf": 5000.0},
        {"insee": "3", "commune": "C", "stock": 20, "velocite": 9.0, "permis": None,
         "deficit_sru": 10.0, "pression_zan": 10.0, "prix_neuf": 4500.0},
    ]
    out = composite_communes([dict(r) for r in rows], poids)

    # ── recalcul indépendant pour la commune B ──
    def norm(vals, v, direction):
        lo, hi = min(vals), max(vals)
        if hi == lo:
            return 50.0
        frac = (v - lo) / (hi - lo)
        return round((frac if direction > 0 else 1 - frac) * 100, 1)
    keys = list(INDICATEURS)
    b = next(r for r in out if r["commune"] == "B")
    wsum = wtot = 0.0
    for k in keys:
        vals = [r[k] for r in rows if r[k] is not None]
        v = rows[1][k]
        n = norm(vals, v, INDICATEURS[k][1]) if v is not None else None
        assert b["normalise"][k] == n
        if n is not None:
            wsum += poids[k] * n
            wtot += poids[k]
    assert b["score_composite"] == round(wsum / wtot, 1)
    # B domine tout (stock max, vélocité min, SRU max, ZAN min, prix max) → rang 1
    assert b["rang"] == 1
