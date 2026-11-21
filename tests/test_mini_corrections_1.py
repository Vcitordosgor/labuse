"""MANDAT MINI-CORRECTIONS-1 — tests des points 4 (recherche d'adresse) et 5 (fraîcheur des ventes).

Les points 1 à 3 sont VISUELS (captures dans docs/audit-2026-11/mini-corrections-1/) : point 1 déjà
réglé par RETOURS-25 (intro Gabarit retirée), point 2 déjà conforme (Pièges utilise EntreeParcelle),
point 3 corrigé (Étude de zone → EntreeParcelle). Rien à asserter en Python pour eux.

Ici :
  · pt 4 — « choisir une proposition de la liste doit TOUJOURS aboutir à une parcelle (la sienne, ou
    la plus proche avec la distance), jamais à "aucune adresse" » → le résolveur point→parcelle
    `/parcels/at` ne rend plus jamais `idu=None` tant que la base n'est pas vide (repli plus-proche).
  · pt 5 — l'horizon de fraîcheur DVF est lu sur les VENTES SERVIES (dvf_mutations), et la tâche
    hebdomadaire enchaîne la reconstruction de la table dérivée (dvf-marche).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest


# ─────────────────────────── pt 5 — fraîcheur des ventes (UNITAIRE, sans base) ───────────────────────────

def test_dvf_horizon_lu_sur_les_ventes_servies():
    """L'horizon DVF (data_sources.source_horizon_at) est CALCULÉ sur `dvf_mutations` — les mutations
    RÉELLEMENT SERVIES (celles que `refresh_dvf` recharge et que `_dvf_couverture` sert « ventes
    jusqu'à … ») — et non sur la table de détail par parcelle `dvf_mutations_parcelle`, qui pouvait
    retarder la mention (« ventes jusqu'au 31/12/2025 » vs mutations jusqu'au 30/06/2026)."""
    from labuse.ingestion.fraicheur import SOURCES

    date_sql = SOURCES["dvf"]["date_sql"]
    assert "dvf_mutations" in date_sql
    # c'est bien la table des mutations servies, pas la table de détail par parcelle
    assert "dvf_mutations_parcelle" not in date_sql
    assert "max(date_mutation)" in date_sql


def test_tache_hebdo_dvf_enchaine_la_reconstruction_du_derive(monkeypatch):
    """La tâche hebdomadaire des ventes (`ingest_dvf`) enchaîne D'ELLE-MÊME, dans la MÊME tâche :
    refresh-dvf (recharge + horizon) PUIS dvf-marche (reconstruction de la table dérivée des médianes
    de secteur = prix des terrains nus, dédup du couple (id_mutation, id_parcelle)). Plus de dépendance
    au job BODACC du lendemain."""
    from labuse import jobs_impl

    appels: list[str] = []
    monkeypatch.setattr(jobs_impl, "_ingest_via_cli",
                        lambda ctx, *args: appels.append(" ".join(args)))
    jobs_impl.ingest_dvf(MagicMock())
    assert appels == ["refresh-dvf", "dvf-marche"], appels


def test_refresh_dvf_rafraichit_lhorizon_meme_en_no_op(monkeypatch):
    """Même sans nouvelle livraison (no-op), `refresh_dvf` rejoue `persist_millesime(only='dvf')` :
    la mention ne doit pas rester figée en attendant un rechargement (cause du « 31/12/2025 » figé)."""
    from labuse.ingestion import fraicheur

    monkeypatch.setattr(fraicheur, "check_dvf_livraison",
                        lambda session, http_get=None: {"modifies": [], "ressources": [],
                                                        "dernier_millesime": "2025-s2"})
    appels: list[dict] = []
    monkeypatch.setattr(fraicheur, "persist_millesime",
                        lambda session, only=None, commit=True: appels.append({"only": only}))
    res = fraicheur.refresh_dvf(MagicMock(), http_get=lambda *_: b"", log_fn=lambda *_: None)
    assert res["no_op"] is True
    assert appels == [{"only": "dvf"}], "persist_millesime(only='dvf') doit être rejoué même en no-op"


# ─────────────────────────── pt 4 — recherche d'adresse (BASE RÉELLE, hors CI) ───────────────────────────

@pytest.fixture(scope="module")
def session_reelle():
    """Session sur la base APPLICATIVE réelle (`LABUSE_APP_DATABASE_URL`) — conftest redirige
    `session_scope()` vers `labuse_test` (vide) ; les tests `reel` lisent la vraie base servie."""
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


# Les 20 adresses à GRAINE FIXE (plusieurs communes) + l'adresse du mandat et ses variantes.
_MANDAT = [
    "47 Rue Emery Talvy, 97438 Sainte-Marie",
    "47 bis Rue Emery Talvy, 97438 Sainte-Marie",
    "47 ter Rue Emery Talvy, 97438 Sainte-Marie",
    "47 quater Rue Emery Talvy, 97438 Sainte-Marie",
]


def _adresses_graine_fixe(session, n: int = 20) -> list[str]:
    """20 adresses tirées à GRAINE FIXE (setseed déterministe), une par commune, plusieurs communes."""
    from sqlalchemy import text

    session.execute(text("SELECT setseed(0.4242)"))
    rows = session.execute(text(
        """SELECT DISTINCT ON (commune) trim(concat_ws(' ', nullif(numero,''), voie)) AS q,
                  code_postal, commune
           FROM adresses
           WHERE idu IS NOT NULL AND geom IS NOT NULL AND numero ~ '^[0-9]+$'
           ORDER BY commune, random() LIMIT :n""" ), {"n": n + 4}).mappings().all()
    return [f"{r['q']}, {r['code_postal']} {r['commune']}" for r in rows][:n]


def _premiere_proposition_cliquable(session, adresse: str) -> dict | None:
    """Reproduit la 1re proposition cliquable de la barre de recherche (hors ligne-note)."""
    from labuse.api.recherche import _sugg_adresse

    for it in _sugg_adresse(session, adresse, 8):
        if not it.get("note"):
            return it
    return None


def _parcelle_servable(session, idu: str) -> bool:
    """La parcelle a une fiche ouvrable (présente dans la trame `parcels`, même disparue du cadastre :
    la fiche la sert avec son historique — cf. /parcels/{idu})."""
    from sqlalchemy import text

    return session.execute(text("SELECT 1 FROM parcels WHERE idu = :i LIMIT 1"),
                           {"i": idu}).first() is not None


@pytest.mark.reel
def test_parcel_at_ne_rend_jamais_aucune_parcelle(session_reelle):
    """`/parcels/at` : un point DANS une parcelle → distance_m 0 ; un point HORS de toute parcelle
    (océan) → la parcelle la PLUS PROCHE avec distance_m > 0 — jamais `idu=None` (plus de « aucune
    adresse » quand le point BAN tombe sur la voirie / hors cadastre)."""
    from sqlalchemy import text
    from labuse.api.app import parcel_at

    s = session_reelle
    if not s.execute(text("SELECT 1 FROM parcels LIMIT 1")).first():
        pytest.skip("base réelle sans parcelles")

    # point au large (océan, sud-ouest) : aucune parcelle ne le contient
    au_large = parcel_at(54.5, -21.5, s)
    assert au_large["idu"] is not None, "le repli plus-proche doit rendre une parcelle"
    assert au_large["distance_m"] and au_large["distance_m"] > 0

    # un point DANS la parcelle de la plus proche doit, lui, être contenu (distance 0)
    lon, lat = s.execute(text(
        "SELECT ST_X(ST_PointOnSurface(geom)), ST_Y(ST_PointOnSurface(geom)) "
        "FROM parcels WHERE idu = :i"), {"i": au_large["idu"]}).one()
    dedans = parcel_at(float(lon), float(lat), s)
    assert dedans["idu"] == au_large["idu"]
    assert dedans["distance_m"] == 0.0


@pytest.mark.reel
def test_toute_proposition_aboutit_a_une_parcelle(session_reelle):
    """Pour l'adresse du mandat, ses variantes bis/ter/quater, et 20 adresses à graine fixe (plusieurs
    communes) : cliquer la 1re proposition aboutit TOUJOURS à une parcelle servable — jamais « aucune
    adresse ». Soit la parcelle rattachée à l'adresse (idu), soit — à défaut — la plus proche du point."""
    from sqlalchemy import text
    from labuse.api.app import parcel_at

    s = session_reelle
    if not s.execute(text("SELECT 1 FROM adresses WHERE idu IS NOT NULL LIMIT 1")).first():
        pytest.skip("base réelle sans adresses rattachées")

    adresses = _MANDAT + _adresses_graine_fixe(s, 20)
    echecs = []
    for a in adresses:
        sel = _premiere_proposition_cliquable(s, a)
        if sel is None:
            echecs.append((a, "aucune proposition"))
            continue
        # 1. la parcelle de l'adresse (idu rattaché), si elle est servable
        if sel.get("idu") and _parcelle_servable(s, sel["idu"]):
            continue
        # 2. sinon la parcelle au POINT (contenante, ou la plus proche + distance) : jamais None
        at = parcel_at(float(sel["lon"]), float(sel["lat"]), s)
        if at["idu"] and _parcelle_servable(s, at["idu"]):
            continue
        echecs.append((a, "aucune adresse"))
    assert not echecs, f"adresses sans parcelle : {echecs}"
