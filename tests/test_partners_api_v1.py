"""M-T Volet 3 — clé API démo bridée en bac à sable.

`/api/v1` est derrière la garde d'auth globale (pas dans auth._PUBLIC) → on teste la FONCTION
d'endpoint directement (le bridage, pas le transport). Décisions Vic : commune unique Cilaos,
50 appels/jour, "demo": true dans chaque réponse ; les vraies clés ne changent pas.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from labuse.api.partners import _DEMO_COMMUNE, _DEMO_QUOTA, api_v1_parcels, ensure_tables
from labuse.db import engine, session_scope


def _seed_keys(s):
    for k, q, demo in (("demo-labuse-partner-key", 50, True), ("real-key-test", 500, False)):
        s.execute(text(
            "INSERT INTO api_keys (key, nom, quota_jour, demo, jour, utilise) "
            "VALUES (:k, 'test', :q, :d, current_date, 0) "
            "ON CONFLICT (key) DO UPDATE SET quota_jour=:q, demo=:d, jour=current_date, utilise=0"),
            {"k": k, "q": q, "d": demo})
    s.commit()


def test_demo_bridee_a_50_par_ensure_tables():
    # une clé démo héritée à 500 est rétro-corrigée à 50 par la migration d'ensure_tables.
    with session_scope() as s:
        s.execute(text("INSERT INTO api_keys (key, nom, quota_jour, demo) "
                       "VALUES ('demo-labuse-partner-key','x',500,true) "
                       "ON CONFLICT (key) DO UPDATE SET quota_jour=500, demo=true"))
        s.commit()
    ensure_tables(engine())
    with session_scope() as s:
        q = s.execute(text("SELECT quota_jour FROM api_keys WHERE key='demo-labuse-partner-key'")).scalar()
        assert q == _DEMO_QUOTA == 50


def test_demo_autre_commune_403():
    with session_scope() as s:
        _seed_keys(s)
        with pytest.raises(HTTPException) as e:
            api_v1_parcels(key="demo-labuse-partner-key", commune="Salazie", db=s, limit=5, offset=0)
        assert e.value.status_code == 403 and _DEMO_COMMUNE in e.value.detail


def test_demo_defaut_force_cilaos_et_flag_demo():
    with session_scope() as s:
        _seed_keys(s)
        out = api_v1_parcels(key="demo-labuse-partner-key", db=s, limit=5, offset=0)
        assert out["demo"] is True
        assert all(it["commune"] == _DEMO_COMMUNE for it in out["items"])   # jamais une autre commune


def test_vraie_cle_non_bridee_pas_de_flag_demo():
    with session_scope() as s:
        _seed_keys(s)
        out = api_v1_parcels(key="real-key-test", commune="Saint-Paul", db=s, limit=5, offset=0)
        assert out["demo"] is False


def test_demo_51e_appel_429():
    with session_scope() as s:
        _seed_keys(s)
        s.execute(text("UPDATE api_keys SET jour=current_date, utilise=:u WHERE key='demo-labuse-partner-key'"),
                  {"u": _DEMO_QUOTA})
        s.commit()
        with pytest.raises(HTTPException) as e:
            api_v1_parcels(key="demo-labuse-partner-key", db=s, limit=5, offset=0)
        assert e.value.status_code == 429


# ─────────────────── REVUE · R2 — porte quota partenaires & fuseau (bug consigné) ───────────────────
def test_r2_porte_quota_ne_reinitialise_pas_le_meme_jour_reunion():
    """Bug consigné : entre 20 h et minuit CEST, il est déjà « demain » à la Réunion — la porte
    comparait `date.today()` (CEST, J) au `jour` BD (SQL current_date, Réunion, J+1) → elle
    RÉINITIALISAIT le quota au lieu de le lever. Fix : la comparaison se fait en jour Réunion des
    DEUX côtés (today_reunion vs current_date en session PG Indian/Reunion). Non-régression :
    une clé au quota, marquée du jour Réunion courant, doit lever 429 (jamais se réinitialiser)."""
    from labuse.api.partners import _check_key
    from labuse.tz import today_reunion
    with session_scope() as s:
        # clé au PLAFOND, estampillée du jour Réunion courant (comme le ferait current_date SQL)
        s.execute(text(
            "INSERT INTO api_keys (key, nom, quota_jour, demo, jour, utilise) "
            "VALUES ('r2-quota-key', 'test R2', 5, false, :j, 5) "
            "ON CONFLICT (key) DO UPDATE SET quota_jour=5, jour=:j, utilise=5"),
            {"j": today_reunion()})
        s.commit()
        # même jour Réunion + quota atteint → 429, PAS un reset silencieux
        with pytest.raises(HTTPException) as exc:
            _check_key(s, "r2-quota-key")
        assert exc.value.status_code == 429
        # le compteur n'a PAS été remis à 0 (la porte a levé, elle n'a pas réinitialisé)
        u = s.execute(text("SELECT utilise FROM api_keys WHERE key='r2-quota-key'")).scalar()
        assert u == 5, f"la porte a réinitialisé à tort (utilise={u})"
        # en revanche, une clé estampillée d'HIER (Réunion) DOIT se réinitialiser
        s.execute(text("UPDATE api_keys SET jour = :h, utilise = 5 WHERE key='r2-quota-key'"),
                  {"h": today_reunion() - __import__("datetime").timedelta(days=1)})
        _check_key(s, "r2-quota-key")   # nouveau jour → reset + 1er appel du jour
        u2 = s.execute(text("SELECT utilise FROM api_keys WHERE key='r2-quota-key'")).scalar()
        assert u2 == 1, f"nouveau jour : la porte aurait dû réinitialiser puis compter 1 (utilise={u2})"
        s.execute(text("DELETE FROM api_keys WHERE key='r2-quota-key'")); s.commit()
