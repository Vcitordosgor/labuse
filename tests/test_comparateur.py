"""O6 — COMPARATEUR DE COMMUNES : normalisation directionnelle + composite à poids renormalisés.

Un axe manquant reste null (jamais 0 trompeur) et son poids est retiré du composite. Le composite est
une commodité, pas un score calibré — pondération réglable et documentée.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import comparateur as c


# OUTIL-PERMIS-FIX-8 (LOT 3) — l'axe vélocité (délai) est RETIRÉ du composite : cinq axes.
DEF = {"stock": 0.30, "permis": 0.15, "deficit_sru": 0.15,
       "pression_zan": 0.10, "prix_neuf": 0.15}


def _row(**kw):
    base = {k: None for k in c.INDICATEURS}
    base.update(kw)
    return base


# ───────────────────────── normalisation (pur) ─────────────────────────

def test_direction_stock_haut_mieux():
    rows = c._normalize([_row(stock=10), _row(stock=0)], DEF)
    hi = next(r for r in rows if r["stock"] == 10)
    lo = next(r for r in rows if r["stock"] == 0)
    assert hi["normalise"]["stock"] == 100.0 and lo["normalise"]["stock"] == 0.0


def test_direction_pression_zan_bas_mieux():
    # OUTIL-PERMIS-FIX-8 — l'axe vélocité est retiré ; on vérifie la direction « bas = mieux » sur
    # la pression ZAN (direction -1) : moins de consommation d'espace (bas) → mieux → normalisé plus haut.
    rows = c._normalize([_row(pression_zan=5), _row(pression_zan=50)], DEF)
    bas = next(r for r in rows if r["pression_zan"] == 5)
    haut = next(r for r in rows if r["pression_zan"] == 50)
    assert bas["normalise"]["pression_zan"] == 100.0 and haut["normalise"]["pression_zan"] == 0.0
    assert "velocite" not in bas["normalise"]       # l'axe délai n'existe plus


def test_axe_manquant_reste_null_et_renormalise():
    # une commune sans prix_neuf : l'axe est null, son poids est retiré du composite
    rows = c._normalize([_row(stock=10, prix_neuf=None), _row(stock=0, prix_neuf=3000)], DEF)
    sans = next(r for r in rows if r["prix_neuf"] is None)
    assert sans["normalise"]["prix_neuf"] is None
    assert sans["score_composite"] is not None      # composite calculé sur les axes présents


def test_composite_classe_rang():
    rows = c._normalize([_row(stock=0), _row(stock=100)], DEF)
    assert rows[0]["rang"] == 1 and rows[0]["stock"] == 100   # meilleur stock → rang 1


def test_borne_degeneree_neutre():
    # tous égaux sur un axe → normalisé neutre 50 (pas de division par zéro)
    rows = c._normalize([_row(stock=5), _row(stock=5)], DEF)
    assert all(r["normalise"]["stock"] == 50.0 for r in rows)


# ───────────────────────── flux DB ─────────────────────────

@pytest.mark.db
def test_compute_24_communes_et_composite(db_session):
    s = db_session
    # le comparateur lit des tables réelles ; s'il n'y a pas de communes en base de test, on skip proprement
    n = s.execute(text("SELECT count(DISTINCT left(idu,5)) FROM parcels")).scalar()
    if not n:
        pytest.skip("pas de parcelles en base de test")
    out = c._compute(s, DEF)
    assert "communes" in out and "indicateurs" in out
    assert out["indicateurs"]["stock"]["direction"] == "haut = mieux"
    assert out["indicateurs"]["pression_zan"]["direction"] == "bas = mieux"
    assert "velocite" not in out["indicateurs"]        # OUTIL-PERMIS-FIX-8 — axe délai retiré
    assert "COMMODITÉ" in out["methode"]
    assert out["poids_total"] == 1.0                    # cinq poids renormalisés (somme = 1)
