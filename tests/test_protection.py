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


# ── P0 exfiltration (audit 360) : quotas carto (tuiles + geojson île) + masquage proprio ──

def test_quota_tuiles_gel_jusqua_minuit(client, monkeypatch):
    """Tuiles vectorielles : au-delà du quota JOURNALIER → 429 « reprend à minuit » (ici 3)."""
    monkeypatch.setenv("LABUSE_QUOTA_TUILES_JOUR", "3")
    from labuse import config
    config.get_settings.cache_clear()
    for i in range(3):
        assert client.get(f"/map/tiles/12/{2000 + i}/{2000 + i}.pbf").status_code != 429
    r = client.get("/map/tiles/12/9/9.pbf")
    assert r.status_code == 429 and "minuit" in r.json()["detail"]


def test_tuiles_hors_rate_limit_60min(client, monkeypatch):
    """Une carte qui panne charge des dizaines de tuiles/s : les tuiles ne sont JAMAIS soumises
    au rate-limit 60/min (sinon la navigation normale tripperait le défi). Quota tuiles large."""
    monkeypatch.setenv("LABUSE_RATE_LIMIT_RPM", "5")
    monkeypatch.setenv("LABUSE_QUOTA_TUILES_JOUR", "100000")
    from labuse import config
    config.get_settings.cache_clear()
    for i in range(12):                                  # 12 tuiles > 5 rpm : aucun 429
        assert client.get(f"/map/tiles/13/{100 + i}/{100 + i}.pbf").status_code != 429


def test_quota_carto_geojson_ile(client, monkeypatch):
    """Dump geojson île : quota d'appels JOURNALIER (ici 2) → 3e appel 429 (borne la moisson)."""
    monkeypatch.setenv("LABUSE_QUOTA_CARTO_JOUR", "2")
    from labuse import config
    config.get_settings.cache_clear()
    assert client.get("/map/parcels.geojson?limit=1").status_code != 429
    assert client.get("/map/parcels.geojson?limit=1").status_code != 429
    r = client.get("/map/parcels.geojson?limit=1")
    assert r.status_code == 429 and "minuit" in r.json()["detail"]


def test_abuse_scan_voit_le_volume_carto(db_session, engine):
    """Un moissonneur 100 % tuiles ne laisse AUCUNE ligne dans consultation_log : le scan doit
    quand même le voir via son compteur de tuiles (sinon il reste invisible — le trou de l'audit)."""
    from labuse.api import protection

    protection.ensure_tables(engine)
    hier = date.today() - timedelta(days=1)
    db_session.execute(text(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) VALUES (:j, 's:tilebot', 'tuile', 35000)"),
        {"j": hier})
    res = protection.scan_abus(db_session, hier)
    sc = res["scores"]["s:tilebot"]                       # présent MALGRÉ zéro fiche loggée
    assert sc["carto"]["tuiles"] == 35000 and sc["score"] >= 40


def test_geojson_ile_masque_le_proprietaire(client, engine):
    """Le nom du propriétaire (PM) sort en mode COMMUNE (borné) mais JAMAIS dans le dump île
    entière (le canal de masse ne déverse pas l'identité des propriétaires)."""
    idu, commune, run = "974990PR000001", "ProprioVille", "q_v_prtest"
    wkt = "POLYGON((55.47 -20.9,55.471 -20.9,55.471 -20.901,55.47 -20.901,55.47 -20.9))"
    with engine.begin() as c:
        pid = c.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
            " centroid, bbox) VALUES (:i,:cm,'ZZ','1', ST_GeomFromText(:w,4326),"
            " ST_Transform(ST_GeomFromText(:w,4326),2975), 2000,"
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
            {"i": idu, "cm": commune, "w": wkt}).scalar()
        c.execute(text("INSERT INTO parcelle_personne_morale (idu, denomination, date_import)"
                       " VALUES (:i, 'SCI SECRETE', now())"), {"i": idu})
        c.execute(text("INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score,"
                       " opportunity_score, matrice_statut, q_score, a_score) "
                       "VALUES (:r,:p,50,50,'chaude',70,70)"), {"r": run, "p": pid})
    try:
        fc = client.get(f"/map/parcels.geojson?source={run}&commune={commune}").json()
        mine = [f["properties"] for f in fc["features"] if f["properties"]["idu"] == idu]
        assert mine and mine[0]["proprio"] == "SCI SECRETE"       # commune : exposé
        fc2 = client.get(f"/map/parcels.geojson?source={run}").json()
        mine2 = [f["properties"] for f in fc2["features"] if f["properties"]["idu"] == idu]
        assert mine2 and mine2[0]["proprio"] is None and mine2[0]["owner_type"] is None  # île : masqué
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = :r"), {"r": run})
            c.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": idu})
            c.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})


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
