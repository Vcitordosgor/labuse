"""Tests Lot 3 (wave-adresses) : quotas fiches, rate limiting, watermark, abuse-scan."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine, monkeypatch):
    from labuse import config
    from labuse.api import protection
    from labuse.api.app import app

    protection.ensure_tables(engine)
    with engine.begin() as c:
        for t in ("usage_compteurs", "consultation_log", "acces_gels", "admin_alertes",
                  "abuse_scores", "export_fingerprints"):
            c.execute(text(f"DELETE FROM {t}"))
    protection.reset_etat_memoire()
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    protection.reset_etat_memoire()
    config.get_settings.cache_clear()


def test_quota_fiches_gel_jusqua_minuit(client, engine, monkeypatch):
    """301e fiche distincte du jour → 429 (critère d'acceptation, ici quota réduit à 3)."""
    monkeypatch.setenv("LABUSE_QUOTA_FICHES_JOUR", "3")
    from labuse import config
    config.get_settings.cache_clear()

    for i in range(3):
        client.get(f"/parcels/97416000AA000{i}")          # 404 métier : compte quand même
    r = client.get("/parcels/97416000AA0009")
    assert r.status_code == 429
    assert "minuit" in r.json()["detail"]
    # une fiche DÉJÀ VUE aujourd'hui reste consultable (dédup par idu)
    r2 = client.get("/parcels/97416000AA0001")
    assert r2.status_code != 429
    with engine.connect() as c:
        n = c.execute(text("SELECT n FROM usage_compteurs WHERE kind = 'fiche'")).scalar()
    assert n == 3


def test_rate_limit_defi_puis_gel(client, monkeypatch, engine):
    """Burst → 429 + défi arithmétique ; bonne réponse → répit ; récidive → gel + alerte."""
    monkeypatch.setenv("LABUSE_RATE_LIMIT_RPM", "5")
    monkeypatch.setenv("LABUSE_RATE_BURST_GEL", "2")
    from labuse import config
    config.get_settings.cache_clear()

    for _ in range(5):
        client.get("/discover")
    r = client.get("/discover")
    assert r.status_code == 429 and "defi" in r.json()
    # les dépassements suivants restent le MÊME épisode (pas de sur-comptage)
    assert client.get("/discover").status_code == 429
    a, _, b = r.json()["defi"].partition(" + ")
    ok = client.post("/protection/defi", json={"reponse": int(a) + int(b)})
    assert ok.status_code == 200

    # défi résolu → fenêtre purgée, la limite normale reprend ; nouveau burst =
    # 2e ÉPISODE du jour → gel + alerte admin (seuil réglé à 2)
    for _ in range(6):
        client.get("/discover")
    r2 = client.get("/discover")
    assert r2.status_code == 429
    with engine.connect() as c:
        gels = c.execute(text("SELECT count(*) FROM acces_gels WHERE actif")).scalar()
        alertes = c.execute(text("SELECT count(*) FROM admin_alertes")).scalar()
    assert gels == 1 and alertes >= 1
    # sujet gelé → toute requête métier répond 429 gel
    r3 = client.get("/discover")
    assert r3.status_code == 429 and r3.json().get("gel") is True


def test_filigrane_export(db_session, engine):
    """Colonne ref + 2-3 canaris (micro-variations de voie) + export_fingerprints."""
    from labuse.api import protection

    protection.ensure_tables(engine)
    headers = ["Parcelle (IDU)", "Voie (BAN)", "Ville"]
    rows = [[f"97416000AA{i:04d}", "Rue des Tests", "Saint-Pierre"] for i in range(10)]
    ref = protection.filigrane_export(db_session, "s:test", headers, rows,
                                      slug="test-preset")
    assert headers[-1] == "ref" and all(r[-1] == ref for r in rows)
    fp = db_session.execute(text(
        "SELECT ref, n_lignes, canaris FROM export_fingerprints WHERE sujet = 's:test'"
    )).mappings().first()
    assert fp["ref"] == ref and fp["n_lignes"] == 10
    canaris = fp["canaris"] if isinstance(fp["canaris"], list) else json.loads(fp["canaris"])
    assert 1 <= len(canaris) <= 3
    variees = [r for r in rows if r[1] != "Rue des Tests"]
    assert len(variees) == len(canaris)       # variations réellement appliquées


def test_abuse_scan_sequences_regulieres(db_session, engine):
    """Séquence d'IDU consécutifs + cadence machinale + nocturne → score élevé + alerte."""
    from labuse.api import protection

    protection.ensure_tables(engine)
    hier = date.today() - timedelta(days=1)
    t0 = datetime.combine(hier, datetime.min.time(), tzinfo=timezone.utc)  # 04h Réunion
    for i in range(60):
        db_session.execute(text(
            "INSERT INTO consultation_log (ts, sujet, chemin, idu) "
            "VALUES (:ts, 's:robot', 'fiche', :idu)"),
            {"ts": t0 + timedelta(seconds=2 * i), "idu": f"97416000AA{i:04d}"})
    res = protection.scan_abus(db_session, hier)
    sc = res["scores"]["s:robot"]
    assert sc["seq_idu_max"] >= 10 and sc["score"] >= 60
    assert res["alertes"] >= 1


# ── Phase A audit UI (11/07) : exemption dev + IP réelle derrière proxy ──────────────────

def test_dev_mode_exempte_rate_limit_et_quota(client, monkeypatch):
    """LABUSE_DEV_MODE=1 → ni rate-limit ni quota (audit/crawl local). Le flag est
    EXPLICITE : jamais d'exemption localhost (derrière nginx tout arrive en 127.0.0.1)."""
    monkeypatch.setenv("LABUSE_RATE_LIMIT_RPM", "5")
    monkeypatch.setenv("LABUSE_QUOTA_FICHES_JOUR", "3")
    monkeypatch.setenv("LABUSE_DEV_MODE", "1")
    from labuse import config
    config.get_settings.cache_clear()

    for _ in range(25):                       # 25 req > 5 rpm : aucun 429
        assert client.get("/discover").status_code != 429
    for i in range(8):                        # 8 fiches distinctes > quota 3 : aucun 429
        assert client.get(f"/parcels/97416000AA00{i:02d}").status_code != 429


def test_dev_mode_absent_la_garde_reste_active(client, monkeypatch):
    """Sans le flag, le rate-limit répond bien 429 (la garde n'est pas cassée par l'ajout)."""
    monkeypatch.setenv("LABUSE_RATE_LIMIT_RPM", "5")
    monkeypatch.delenv("LABUSE_DEV_MODE", raising=False)
    from labuse import config
    config.get_settings.cache_clear()

    for _ in range(6):
        client.get("/discover")
    assert client.get("/discover").status_code == 429


class _ReqStub:
    def __init__(self, peer, xff=None):
        self.client = type("C", (), {"host": peer})()
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.cookies = {}


def test_ip_reelle_sans_proxy_de_confiance(monkeypatch):
    """Pair inconnu → IP du pair, X-Forwarded-For IGNORÉ (en-tête forgeable)."""
    monkeypatch.delenv("LABUSE_TRUSTED_PROXIES", raising=False)
    from labuse import config
    from labuse.api import protection
    config.get_settings.cache_clear()
    assert protection.ip_reelle(_ReqStub("203.0.113.7", xff="1.2.3.4")) == "203.0.113.7"


def test_ip_reelle_derriere_proxy_de_confiance(monkeypatch):
    """Pair = proxy de confiance → 1er hop non-proxy DEPUIS LA DROITE de X-Forwarded-For
    (la gauche est forgeable : un client qui envoie son propre XFF ne choisit pas son IP)."""
    monkeypatch.setenv("LABUSE_TRUSTED_PROXIES", "127.0.0.1, 10.0.0.2")
    from labuse import config
    from labuse.api import protection
    config.get_settings.cache_clear()
    # chaîne : client réel 203.0.113.7 → proxy 10.0.0.2 → nginx 127.0.0.1 → app
    assert protection.ip_reelle(
        _ReqStub("127.0.0.1", xff="6.6.6.6, 203.0.113.7, 10.0.0.2")) == "203.0.113.7"
    # XFF forgé entièrement par un pair NON proxy : ignoré
    assert protection.ip_reelle(_ReqStub("198.51.100.9", xff="127.0.0.1")) == "198.51.100.9"
    # proxy de confiance sans XFF : on retombe sur le pair (pas de crash)
    assert protection.ip_reelle(_ReqStub("127.0.0.1")) == "127.0.0.1"
    config.get_settings.cache_clear()
