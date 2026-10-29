"""RADAR-FIX-3 — la passe de CONFIRMATION ne retire un bien que sur PREUVE POSITIVE, compte à part les
pages « non vérifiées » (bloquées/vides/illisibles), et n'écrit AUCUN retrait si une passe en veut plus
de 30 % (garde-fou anti fausses suppressions de masse — 60/60 le 28/10, 107/107 le 26/09).

Un test par cas, comme demandé au mandat.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.db import session_scope

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine, monkeypatch):
    from labuse.api.app import app
    # Même barrière que le reste du Radar : la garde admin ouvre aussi le jeton radar (_est_admin).
    monkeypatch.setattr("labuse.api.auth.exiger_admin", lambda request: None)
    return TestClient(app)


@pytest.fixture
def seed():
    """Crée des biens ACTIFS avec un list_id, et nettoie tout (biens, annonces, journal, passes) après."""
    crees: list[int] = []
    jours: set[str] = set()

    def _creer(n: int, base_list_id: int = 9_900_000_000, statut: str = "active") -> list[tuple[int, int]]:
        paires = []
        with session_scope() as db:
            for i in range(n):
                lid = base_list_id + len(crees)
                bid = db.execute(text(
                    "INSERT INTO pige_biens (commune, statut, last_seen_at, date_derniere_confirmation) "
                    "VALUES ('Saint-Denis', :s, now() - interval '20 days', now() - interval '20 days') "
                    "RETURNING bien_id"), {"s": statut}).scalar()
                db.execute(text(
                    "INSERT INTO pige_annonces (bien_id, list_id, portail, url_sortante) "
                    "VALUES (:b, :l, 'leboncoin', :u)"),
                    {"b": bid, "l": lid, "u": f"https://www.leboncoin.fr/ad/{lid}"})
                crees.append(bid)
                paires.append((bid, lid))
            db.commit()
        return paires

    yield _creer

    with session_scope() as db:
        if crees:
            db.execute(text("DELETE FROM pige_annonces WHERE bien_id = ANY(:b)"), {"b": crees})
            db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": crees})
        db.execute(text("DELETE FROM event_log WHERE kind LIKE 'pige.%'"))
        db.execute(text("DELETE FROM pige_passes WHERE passe = 'confirmation'"))
        db.commit()


def _statut(bid: int) -> str:
    with session_scope() as db:
        return db.execute(text("SELECT statut FROM pige_biens WHERE bien_id = :b"), {"b": bid}).scalar()


def _retiree_le(bid: int):
    with session_scope() as db:
        return db.execute(text("SELECT retiree_le FROM pige_biens WHERE bien_id = :b"), {"b": bid}).scalar()


def _passe(jour: str) -> dict:
    with session_scope() as db:
        return dict(db.execute(text(
            "SELECT n_pages, n_supprimees, n_non_verifiees FROM pige_passes "
            "WHERE passe = 'confirmation' AND captured_at = CAST(:j AS timestamptz)"),
            {"j": jour}).mappings().first() or {})


def _batch(client, jour, items):
    return client.post("/admin/radar/confirmation-batch",
                       json={"captured_at": jour, "items": items}).json()


# ── PREUVE POSITIVE : les deux seuls cas qui retirent ───────────────────────────────────────────────

def test_preuve_expiree_retire(client, seed):
    (bid, lid), = seed(1)
    r = _batch(client, "2026-01-01", [{"list_id": lid, "verdict": "supprimee", "preuve": "expiree"}])
    assert r["n_retires"] == 1 and r["anomalie"] is False
    assert _statut(bid) == "retiree" and _retiree_le(bid) is not None


def test_preuve_http_404_retire(client, seed):
    (bid, lid), = seed(1)
    r = _batch(client, "2026-01-02", [{"list_id": lid, "verdict": "supprimee", "preuve": "http_404"}])
    assert r["n_retires"] == 1
    assert _statut(bid) == "retiree"


# ── SANS PREUVE : jamais de retrait, compté « non vérifiée » ─────────────────────────────────────────

def test_supprimee_sans_preuve_ne_retire_pas(client, seed):
    """Le cœur du bug 28/10 : « supprimee » sans preuve (page bloquée/redirigée) NE retire PLUS."""
    (bid, lid), = seed(1)
    r = _batch(client, "2026-01-03", [{"list_id": lid, "verdict": "supprimee", "preuve": None}])
    assert r["n_retires"] == 0 and r["n_non_verifiees"] == 1
    assert _statut(bid) == "active"
    assert _passe("2026-01-03")["n_non_verifiees"] == 1


def test_verdict_inconnue_non_verifiee(client, seed):
    (bid, lid), = seed(1)
    r = _batch(client, "2026-01-04", [{"list_id": lid, "verdict": "inconnue"}])
    assert r["n_retires"] == 0 and r["n_non_verifiees"] == 1
    assert _statut(bid) == "active"


def test_preuve_non_reconnue_non_verifiee(client, seed):
    """Une « preuve » inventée (ni expiree ni http_404) n'est pas une preuve → non vérifiée."""
    (bid, lid), = seed(1)
    r = _batch(client, "2026-01-05", [{"list_id": lid, "verdict": "supprimee", "preuve": "bloquee"}])
    assert r["n_retires"] == 0 and r["n_non_verifiees"] == 1
    assert _statut(bid) == "active"


# ── PRÉSENTE : l'annonce active est confirmée ───────────────────────────────────────────────────────

def test_presente_confirme_actif(client, seed):
    (bid, lid), = seed(1, statut="a_reverifier")
    r = _batch(client, "2026-01-06", [{"list_id": lid, "verdict": "presente"}])
    assert r["n_retires"] == 0
    assert _statut(bid) == "active"   # a_reverifier → active


# ── GARDE-FOU DES 30 % ──────────────────────────────────────────────────────────────────────────────

def test_garde_fou_bloque_au_dessus_de_30pct(client, seed):
    """10 liens vérifiés, 4 vus retirés (40 %) : AUCUN retrait écrit, anomalie signalée."""
    paires = seed(10)
    items = []
    for i, (_bid, lid) in enumerate(paires):
        if i < 4:
            items.append({"list_id": lid, "verdict": "supprimee", "preuve": "expiree"})
        else:
            items.append({"list_id": lid, "verdict": "presente"})
    r = _batch(client, "2026-01-07", items)
    assert r["anomalie"] is True
    assert r["n_retires"] == 0
    assert all(_statut(bid) != "retiree" for bid, _lid in paires[:4])
    assert _passe("2026-01-07")["n_supprimees"] == 0


def test_garde_fou_laisse_passer_a_30pct(client, seed):
    """10 liens, 3 vus retirés (30 %, pas > 30 %) : les 3 (prouvés) sont retirés, pas d'anomalie."""
    paires = seed(10)
    items = []
    for i, (_bid, lid) in enumerate(paires):
        if i < 3:
            items.append({"list_id": lid, "verdict": "supprimee", "preuve": "expiree"})
        else:
            items.append({"list_id": lid, "verdict": "presente"})
    r = _batch(client, "2026-01-08", items)
    assert r["anomalie"] is False
    assert r["n_retires"] == 3
    assert all(_statut(bid) == "retiree" for bid, _lid in paires[:3])


# ── VOIE HISTORIQUE (un lien) : ne retire PLUS jamais ───────────────────────────────────────────────

def test_endpoint_simple_ne_retire_jamais(client, seed):
    """La voie historique /admin/radar/confirmation (un appel = un lien) ne peut plus retirer : même avec
    une preuve, le retrait exige une PASSE (où joue le garde-fou). Elle confirme encore les actives."""
    (bid, lid), = seed(1)
    r = client.post("/admin/radar/confirmation",
                    json={"list_id": lid, "verdict": "supprimee", "preuve": "expiree"}).json()
    assert r["ok"] is True and r["retire"] is False and r["non_verifiee"] is True
    assert _statut(bid) == "active"


def test_endpoint_simple_presente_confirme(client, seed):
    (bid, lid), = seed(1, statut="en_vente_longue")
    client.post("/admin/radar/confirmation", json={"list_id": lid, "verdict": "presente"})
    assert _statut(bid) == "active"   # en_vente_longue → active (re-vue)


def test_list_id_inconnu(client, seed):
    r = client.post("/admin/radar/confirmation",
                    json={"list_id": 1, "verdict": "presente"}).json()
    assert r["ok"] is False and r["motif"] == "list_id inconnu"
