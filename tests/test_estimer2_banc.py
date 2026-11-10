"""ESTIMER-2 (fix/estimer-2, D-6) — le banc de précision permanent + le job de nuit.

  · canary (UNITAIRE, pre-push) : le job est au registre, son implémentation existe, son horaire est
    cohérent (04:30 Réunion = 00:30 UTC) ;
  · banc (RÉEL) : le rétro-test no-leak tourne sur les 3 types, persiste la calibration, et le lecteur
    servi la relit."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as _Session


# ── Canary : le registre et l'implémentation (aucune base) ──────────────────────────────────────────
def test_banc_precision_canary():
    from labuse import jobs_impl
    from labuse.jobs import JOBS
    assert "estimer-banc-precision" in JOBS, "job absent du registre"
    j = JOBS["estimer-banc-precision"]
    assert callable(getattr(jobs_impl, "estimer_banc_precision", None)), "implémentation manquante"
    assert j.envoie_mail is True, "le banc doit alerter par mail en cas de régression"
    assert j.cron_utc == "30 0 * * *" and j.heure_reunion == "04:30"  # UTC+4 cohérent


def test_banc_module_importe_et_constantes():
    """Le lecteur unique s'importe et porte les constantes attendues (échantillon 200, 3 types)."""
    from labuse.pige import banc_estimer as be
    assert be.N_SAMPLE == 200 and be.RAYONS == (500.0, 1000.0, 1500.0)
    assert callable(be.calcule) and callable(be.persiste) and callable(be.charge_calibration)


# ── Banc réel : rétro-test no-leak + persistance + relecture ────────────────────────────────────────
@pytest.fixture(scope="module")
def engine():
    url = os.environ.get("LABUSE_REEL_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini")
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            if c.execute(text("SELECT to_regclass('dvf_mutations_parcelle')")).scalar() is None:
                pytest.skip("DVF absent")
        yield eng
    finally:
        eng.dispose()


@pytest.mark.reel
def test_banc_les_trois_types_mesures(engine):
    """Le banc juge bien 3 types ; chaque écart médian est fini et positif ; la part SANS PRIX du
    terrain est basse (objectif D-3 : rayon adaptatif + repli commune)."""
    from labuse.pige import banc_estimer as be
    rep = be.calcule(engine, n_sample=120)
    for t in ("maison", "appartement", "terrain"):
        q = rep["par_type"][t]
        assert q["n"] >= 50, f"{t} : échantillon jugé trop mince ({q['n']})"
        assert q["mediane"] is not None and q["mediane"] > 0
    assert rep["par_type"]["terrain"]["pct_sans_prix"] <= 5.0, "trop de terrains sans prix (D-3 raté)"


@pytest.mark.reel
def test_banc_persiste_et_relit_la_calibration(engine):
    """`persiste` écrit la table servie ; `charge_calibration` la relit (commune calibrée → perimetre
    'commune' ; commune inconnue → repli 'ile')."""
    from labuse.pige import banc_estimer as be
    rep = be.calcule(engine, n_sample=120)
    n = be.persiste(engine, rep)
    assert n >= 3  # au moins une ligne de repli '*' par type
    with _Session(engine) as db:
        repli = be.charge_calibration(db, "maison", "00000")
        assert repli and repli["perimetre"] == "ile" and repli["ecart_median"] > 0
