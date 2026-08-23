"""AUDIT PAIEMENT · PARTIE A — sécurité de l'accès (tests ADVERSARIAUX permanents).

Chaque test attaque une faille : s'il tombe, la cloison est ouverte. Ils RESTENT dans la
suite (régression). DB réelle (labuse_test), auth active, deux comptes réels.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db


@pytest.fixture
def app_client(engine, monkeypatch):
    """App en mode auth active (comme la prod) — cookie Secure → base https."""
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-audit")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-audit-000000000000000000")
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app
    yield TestClient(app, base_url="https://testserver")
    # Nettoyage À LA SOURCE : les settings « pilote » chargés en cache lru fuiraient sinon
    # vers les tests suivants (ordre alphabétique → test_auth voit une auth active à tort).
    config.get_settings.cache_clear()


def _compte_actif(email: str) -> int:
    """Crée + active un compte (paiement simulé : statut compte 'actif'), renvoie compte_id."""
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-audit-1", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client: TestClient, email: str) -> TestClient:
    r = client.post("/login", data={"identifiant": email, "password": "motdepasse-audit-1"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    return client


def _purge(*emails):
    with session_scope() as s:
        for e in emails:
            try:
                comptes.supprimer_utilisateur(s, e)
            except Exception:
                pass


# ─────────────────────────── SEC-IDOR : cloison multi-tenant ───────────────────────────

def test_idor_projets_cloison_totale(app_client):
    """Compte A crée un projet ; compte B ne le voit, ni ne le lit, modifie, supprime,
    ou n'exporte via l'id d'URL — 404 partout, jamais une fuite."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver")
        cb = TestClient(app_client.app, base_url="https://testserver")
        _login(ca, ea); _login(cb, eb)

        # A crée un projet
        r = ca.post("/projets", json={"nom": "Secret de A", "fiche": {"type_programme": "logements"}})
        assert r.status_code == 200, r.text
        pid = r.json()["projet"]["id"]

        # A le voit dans SA liste
        assert any(p["id"] == pid for p in ca.get("/projets").json())
        # B ne le voit PAS
        assert all(p["id"] != pid for p in cb.get("/projets").json())
        # B ne peut ni lire, ni patcher, ni rejouer, ni supprimer, ni exporter (404)
        assert cb.get(f"/projets/{pid}").status_code == 404
        assert cb.patch(f"/projets/{pid}", json={"nom": "vol"}).status_code == 404
        assert cb.post(f"/projets/{pid}/rejouer").status_code == 404
        assert cb.get(f"/projets/{pid}/parcelles").status_code == 404
        assert cb.get(f"/projets/{pid}/export.pdf").status_code == 404
        assert cb.delete(f"/projets/{pid}").status_code == 404
        # A toujours intact après les tentatives de B
        assert ca.get(f"/projets/{pid}").status_code == 200
    finally:
        _purge(ea, eb)


def test_idor_pipeline_cloison_et_meme_parcelle(app_client):
    """Le CRM : B ne voit pas les pistes de A, ne peut pas les modifier/supprimer par id,
    et LES DEUX peuvent suivre la MÊME parcelle (la clé (compte, parcelle) le permet)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        idu = f"974990SEC{uuid.uuid4().hex[:5].upper()}"   # parcelle DÉDIÉE (nettoyée en finally)
        _wkt = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
        with session_scope() as s:
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
                " centroid, bbox) VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "w": _wkt})
            s.commit()

        ra = ca.post("/pipeline", json={"idu": idu})
        assert ra.status_code == 200 and not ra.json()["already"], ra.text
        eid_a = ra.json()["entry"]["id"]
        # B suit LA MÊME parcelle → autorisé (plus de UNIQUE(parcel_id) global), entrée distincte
        rb = cb.post("/pipeline", json={"idu": idu})
        assert rb.status_code == 200 and not rb.json()["already"], rb.text
        assert rb.json()["entry"]["id"] != eid_a

        # B ne voit pas la piste de A ; ne peut pas la patcher/supprimer
        assert all(e["id"] != eid_a for e in cb.get("/pipeline").json())
        assert cb.patch(f"/pipeline/{eid_a}", json={"priority": "haute"}).status_code == 404
        assert cb.delete(f"/pipeline/{eid_a}").status_code == 404
        # la parcelle vue par A reste « in_pipeline » pour A, indépendamment de B
        assert ca.get(f"/pipeline/parcel/{idu}").json()["in_pipeline"] is True
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def test_idor_veilles_cloison(app_client):
    """Veilles (recherches sauvegardées) : B ne voit pas celles de A, ni ne les supprime."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        assert ca.post("/events/searches", json={"nom": "veille A", "hash": "#f=1"}).status_code == 200
        mine = ca.get("/events/searches").json()
        assert len(mine) == 1 and mine[0]["nom"] == "veille A"
        sid = mine[0]["id"]
        # B ne voit rien, et un DELETE ciblé sur l'id de A ne détruit rien chez A
        assert cb.get("/events/searches").json() == []
        cb.delete(f"/events/searches/{sid}")
        assert len(ca.get("/events/searches").json()) == 1   # intacte
    finally:
        _purge(ea, eb)


def test_idor_signalements_cloison(app_client):
    """Signalements (file de QA) : B ne voit NI ne liste NI n'exporte ceux de A."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        idu = f"974SIG{uuid.uuid4().hex[:8].upper()}"
        r = ca.post("/signalements", json={"idu": idu, "type_erreur": "zonage", "commentaire": "erreur de A"})
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        # A le voit dans SA file ; B ne voit rien (ni liste, ni export CSV)
        assert any(s["id"] == sid for s in ca.get("/signalements").json())
        assert all(s["id"] != sid for s in cb.get("/signalements").json())
        assert str(sid) not in cb.get("/signalements/export.csv").text.split("\n", 1)[1]
        # A reste intact
        assert any(s["id"] == sid for s in ca.get("/signalements").json())
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM signalements WHERE parcelle_id LIKE '974SIG%'")); s.commit()


def test_idor_saved_filters_cloison(app_client):
    """Filtres sauvegardés : B ne voit pas ceux de A, et un DELETE ciblé sur l'id de A
    renvoie 404 (jamais 403) sans rien détruire chez A — corrige l'IDOR d'écriture."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        r = ca.post("/filters", json={"name": "filtre A", "params": {"q": 65}})
        assert r.status_code == 200, r.text
        fid = r.json()["id"]
        # A le voit ; B ne voit rien
        assert any(f["id"] == fid for f in ca.get("/filters").json())
        assert cb.get("/filters").json() == []
        # B tente de supprimer le filtre de A par id → 404, et le filtre survit chez A
        assert cb.delete(f"/filters/{fid}").status_code == 404
        assert any(f["id"] == fid for f in ca.get("/filters").json())
        # A peut supprimer le sien
        assert ca.delete(f"/filters/{fid}").status_code == 200
    finally:
        _purge(ea, eb)


def test_idor_event_log_cloison(app_client):
    """Cloche de notifications : B ne voit pas les événements de A, et ni son « lire »
    ciblé ni son « tout lire » ne touchent l'événement de A."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    cid_a = _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        # un événement (ex. veille) appartenant à A
        with session_scope() as s:
            eid = s.execute(text(
                "INSERT INTO event_log (kind, idu, titre, compte_id) "
                "VALUES ('veille', '974EVT00000001', 'évt privé de A', :cid) RETURNING id"),
                {"cid": cid_a}).scalar()
            s.commit()
        # A le voit (non lu) ; B ne le voit pas et son compteur l'ignore
        assert any(e["id"] == eid for e in ca.get("/events").json()["items"])
        assert ca.get("/events/count").json()["unread"] >= 1
        assert all(e["id"] != eid for e in cb.get("/events").json()["items"])
        # B « lit » l'événement de A par id, puis « tout lire » : sans effet sur A
        cb.post(f"/events/{eid}/read"); cb.post("/events/read-all")
        with session_scope() as s:
            assert s.execute(text("SELECT lu FROM event_log WHERE id = :i"), {"i": eid}).scalar() is False
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM event_log WHERE idu = '974EVT00000001'")); s.commit()


def test_broadcast_marche_visible_de_tous_mais_perso_cloisonne(app_client):
    """M-T V2 : un événement de MARCHÉ (compte_id NULL, kind bascule) est visible de TOUS les
    abonnés ; un événement PERSONNEL de A (veille) reste invisible de B (cloison non régressée)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    cid_a = _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        with session_scope() as s:
            mid = s.execute(text(
                "INSERT INTO event_log (kind, idu, titre, compte_id) "
                "VALUES ('bascule', '974MKT00000001', '▲ bascule marché', NULL) RETURNING id")).scalar()
            pid = s.execute(text(
                "INSERT INTO event_log (kind, idu, titre, compte_id) "
                "VALUES ('veille', '974PRV00000001', 'veille privée de A', :c) RETURNING id"),
                {"c": cid_a}).scalar()
            s.commit()
        a_items = ca.get("/events").json()["items"]
        b_items = cb.get("/events").json()["items"]
        # MARCHÉ (NULL) visible des DEUX comptes
        assert any(e["id"] == mid for e in a_items) and any(e["id"] == mid for e in b_items)
        # PERSONNEL de A : A le voit, B jamais (cloison stricte préservée)
        assert any(e["id"] == pid for e in a_items) and all(e["id"] != pid for e in b_items)
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM event_log WHERE idu IN ('974MKT00000001','974PRV00000001')"))
            s.commit()


def test_seen_marche_par_compte(app_client):
    """M-V V2 : A marque LU un event de MARCHÉ → SON badge descend, celui de B est INCHANGÉ
    (jamais d'UPDATE sur la ligne partagée) ; les events perso gardent le comportement d'avant ;
    « tout lire » couvre aussi le marché ; la ligne partagée `lu` reste false."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    cid_a = _compte_actif(ea); _compte_actif(eb)
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        with session_scope() as s:
            mid = s.execute(text(
                "INSERT INTO event_log (kind, idu, titre, compte_id) "
                "VALUES ('bascule', '974SEEN0000001', '▲ bascule marché', NULL) RETURNING id")).scalar()
            pid_a = s.execute(text(
                "INSERT INTO event_log (kind, idu, titre, compte_id) "
                "VALUES ('veille', '974SEEN0000002', 'veille privée de A', :c) RETURNING id"),
                {"c": cid_a}).scalar()
            s.commit()
        a0 = ca.get("/events/count").json()["unread"]
        b0 = cb.get("/events/count").json()["unread"]
        assert a0 >= 2 and b0 >= 1  # A voit marché + sa veille ; B voit le marché

        # A marque LU l'event de MARCHÉ (par id, puis vérifie l'item passe à lu=true côté A)
        assert ca.post(f"/events/{mid}/read").json()["ok"]
        assert ca.get("/events/count").json()["unread"] == a0 - 1        # badge de A descend
        assert cb.get("/events/count").json()["unread"] == b0            # badge de B INCHANGÉ
        assert next(e for e in ca.get("/events").json()["items"] if e["id"] == mid)["lu"] is True
        assert next(e for e in cb.get("/events").json()["items"] if e["id"] == mid)["lu"] is False
        with session_scope() as s:  # la ligne partagée n'a JAMAIS été écrite
            assert s.execute(text("SELECT lu FROM event_log WHERE id=:i"), {"i": mid}).scalar() is False
            assert s.execute(text("SELECT count(*) FROM event_seen WHERE event_id=:i"), {"i": mid}).scalar() == 1

        # « tout lire » de B couvre le marché (et sa propre veille éventuelle) → badge B à ses perso près
        assert cb.post("/events/read-all").json()["ok"]
        assert next(e for e in cb.get("/events").json()["items"] if e["id"] == mid)["lu"] is True
        assert ca.get("/events").json()  # A intact : son marché déjà lu, sa veille encore non lue
        assert next(e for e in ca.get("/events").json()["items"] if e["id"] == pid_a)["lu"] is False
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM event_log WHERE idu IN ('974SEEN0000001','974SEEN0000002')"))
            s.commit()


def test_digest_resume_marche_sans_evenement_perso():
    """M-T V2 : un abonné SANS veille reçoit un digest si le résumé marché est non vide (fin du
    « digest vide à vie »). Le marché est BORNÉ en résumé (jamais la liste) + lien de désinscription."""
    from labuse.emails import digest_notifications
    sujet, corps = digest_notifications([], "https://x/events/desabonner?c=1&t=zz",
                                        marche={"total": 5, "dans_vos_communes": 2})
    assert "5 mouvement" in corps and "dont 2 dans vos communes" in corps
    assert "mouvement" in sujet                       # sujet marché quand aucun événement perso
    assert "desabonner" in corps                      # désinscription obligatoire présente
    # « vos communes » absent → total seul (pas de parcelles suivies)
    _, corps2 = digest_notifications([], "https://x/d", marche={"total": 3, "dans_vos_communes": None})
    assert "sur l'île" in corps2 and "dans vos communes" not in corps2


def test_idor_watched_parcels_cloison(app_client):
    """Suivi de cible : A et B peuvent suivre la MÊME parcelle sans se voir ; B « unwatch »
    ne défait pas le suivi de A."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    idu = f"974990WA{uuid.uuid4().hex[:6].upper()}"
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        _wkt = "POLYGON((55.46 -20.9,55.461 -20.9,55.461 -20.901,55.46 -20.901,55.46 -20.9))"
        with session_scope() as s:
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
                " centroid, bbox) VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "w": _wkt}); s.commit()
        # A suit la parcelle
        assert ca.post(f"/events/watch/{idu}").json()["watched"] is True
        assert ca.get(f"/events/watch/{idu}").json()["watched"] is True
        # B ne la suit pas encore (isolation de lecture)
        assert cb.get(f"/events/watch/{idu}").json()["watched"] is False
        # B peut suivre LA MÊME parcelle (clé (compte, idu)), puis se dé-suit : A reste suivi
        assert cb.post(f"/events/watch/{idu}").json()["watched"] is True
        assert cb.post(f"/events/watch/{idu}").json()["watched"] is False   # B unwatch
        assert ca.get(f"/events/watch/{idu}").json()["watched"] is True     # A intact
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM watched_parcels WHERE idu = :i"), {"i": idu})
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu}); s.commit()


def test_idor_alertes_watch_zones_cloison(app_client):
    """M-K (P1-9) — Alertes intelligentes : B ne voit NI les zones de veille NI les nouveautés
    de A, ne matérialise rien de A dans son scope au refresh, ne peut ni accuser réception de
    l'alerte de A ni supprimer sa zone (404). Et si A et B suivent la MÊME parcelle, un permis
    proche alerte CHACUN (dédup PAR COMPTE — l'ancienne clé (parcel_id, source_ref) mangeait
    l'alerte du 2e compte)."""
    ea, eb = f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    commune = "AlertIDOR"
    idu = f"974AZ{uuid.uuid4().hex[:7].upper()}"
    poly = {"type": "Polygon", "coordinates": [[
        [55.50, -21.20], [55.52, -21.20], [55.52, -21.18], [55.50, -21.18], [55.50, -21.20]]]}
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        # A crée une zone de veille ; une vente DVF tombe dedans → une nouveauté POUR A
        rz = ca.post("/watch-zones", json={"name": "Zone secrète de A", "geometry": poly, "commune": commune})
        assert rz.status_code == 200, rz.text
        zid_a = rz.json()["zone"]["id"]
        with session_scope() as s:
            s.execute(text("INSERT INTO dvf_mutations (date_mutation, valeur_fonciere, nature_mutation, commune, geom) "
                           "VALUES (now(), 300000, 'Vente', :c, ST_SetSRID(ST_MakePoint(55.51,-21.19),4326))"), {"c": commune})
            s.commit()
        assert ca.post("/alertes/refresh", params={"commune": commune}).json()["dvf_in_zone"] == 1
        # A voit SA zone et SA nouveauté
        assert any(z["id"] == zid_a for z in ca.get("/watch-zones", params={"commune": commune}).json())
        a_alertes = ca.get("/alertes", params={"commune": commune}).json()
        assert len(a_alertes) == 1 and a_alertes[0]["kind"] == "dvf_in_zone"
        aid = a_alertes[0]["id"]
        # B ne voit NI la zone NI la nouveauté de A ; son refresh ne matérialise rien dans SON scope
        assert cb.get("/watch-zones", params={"commune": commune}).json() == []
        assert cb.get("/alertes", params={"commune": commune}).json() == []
        assert cb.post("/alertes/refresh", params={"commune": commune}).json()["dvf_in_zone"] == 0
        # B ne peut ni accuser réception de l'alerte de A (0 effet) ni supprimer sa zone (404)
        assert cb.post("/alertes/ack", json={"id": aid, "commune": commune}).json()["acknowledged"] == 0
        assert cb.delete(f"/watch-zones/{zid_a}").status_code == 404
        # A reste intact : zone présente, nouveauté toujours non-lue
        assert any(z["id"] == zid_a for z in ca.get("/watch-zones", params={"commune": commune}).json())
        assert len(ca.get("/alertes", params={"commune": commune, "only_new": True}).json()) == 1

        # M54-EXPO-2 (arbitrage Vic) : le canal alertes NE traite PLUS les permis (retiré — la cloche
        # les couvre). Même avec 2 comptes suivant la MÊME parcelle ET un permis proche, /alertes/refresh
        # n'émet AUCUN permit_near_followed (clé absente pour chacun).
        _wkt = "POLYGON((55.51 -21.19,55.5105 -21.19,55.5105 -21.1905,55.51 -21.1905,55.51 -21.19))"
        with session_scope() as s:
            s.execute(text("INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
                           "VALUES (:i,:c,'ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
                           " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                      {"i": idu, "c": commune, "w": _wkt})
            s.execute(text("INSERT INTO sitadel_permits (type, date, commune, geom) "
                           "VALUES ('PC', now(), :c, ST_SetSRID(ST_MakePoint(55.5102,-21.1902),4326))"), {"c": commune})
            s.commit()
        assert ca.post("/pipeline", json={"idu": idu}).status_code == 200
        assert cb.post("/pipeline", json={"idu": idu}).status_code == 200
        assert "permit_near_followed" not in ca.post("/alertes/refresh", params={"commune": commune}).json()
        assert "permit_near_followed" not in cb.post("/alertes/refresh", params={"commune": commune}).json()
    finally:
        _purge(ea, eb)
        with session_scope() as s:
            s.execute(text("DELETE FROM watch_zones WHERE commune = :c"), {"c": commune})
            s.execute(text("DELETE FROM dvf_mutations WHERE commune = :c"), {"c": commune})
            s.execute(text("DELETE FROM sitadel_permits WHERE commune = :c"), {"c": commune})
            s.execute(text("DELETE FROM pipeline_entries WHERE parcel_id IN (SELECT id FROM parcels WHERE idu=:i)"), {"i": idu})
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
            s.commit()


# ─────────────────────── Statuts × routes (la matrice d'accès) ───────────────────────

def _session_cookie(compte_id: int, email: str) -> str:
    with session_scope() as s:
        uid = s.execute(text("SELECT id FROM utilisateurs WHERE email=:e"), {"e": email}).scalar()
        return "u." + comptes.creer_session(s, uid)


def test_statut_matrice_acces(app_client):
    """invite → dehors · paiement_requis → dedans · suspendu/resilie → dehors · actif → dedans.
    Le statut du COMPTE décide à CHAQUE requête (route API protégée représentative)."""
    email = f"m-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        c.cookies.set("labuse_session", _session_cookie(cid, email))
        attendu = {"actif": 401, "paiement_requis": 401, "invite": 401, "suspendu": 401, "resilie": 401}
        # 401 attendu SEULEMENT hors accès ; dedans = 200 (ou 404 si parcelle absente, jamais 401)
        for statut, dedans in [("actif", True), ("paiement_requis", True),
                               ("invite", False), ("suspendu", False), ("resilie", False)]:
            with session_scope() as s:
                s.execute(text("UPDATE comptes SET statut=:st WHERE id=:c"), {"st": statut, "c": cid})
                s.commit()
            code = c.get("/parcels?limit=1").status_code
            if dedans:
                assert code != 401, f"{statut} devrait AVOIR accès (reçu {code})"
            else:
                assert code == 401, f"{statut} ne devrait PAS avoir accès (reçu {code})"
    finally:
        _purge(email)


def test_revocation_session_immediate(app_client):
    """Résiliation → la requête SUIVANTE tombe (pas au prochain login). Re-preuve HTTP."""
    email = f"rev-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        c.cookies.set("labuse_session", _session_cookie(cid, email))
        assert c.get("/parcels?limit=1").status_code != 401
        with session_scope() as s:
            comptes.suspendre_compte(s, cid, "audit")
        assert c.get("/parcels?limit=1").status_code == 401
    finally:
        _purge(email)


# ─────────────────────────────── Tokens ───────────────────────────────

def test_tokens_rejoues_expires_forges(app_client):
    """Invitation consommée/rejouée, reset rejoué, token expiré, token forgé → tous refusés."""
    email = f"tok-{uuid.uuid4().hex[:8]}@x.test"
    try:
        with session_scope() as s:
            inv = comptes.creer_invitation(s, email)
        tok = inv["lien"].split("token=")[1]
        c = TestClient(app_client.app, base_url="https://testserver")
        # invitation valide une fois
        assert c.get(f"/invitation?token={tok}").status_code == 200
        # consommée → rejeu refusé (page 404)
        with session_scope() as s:
            comptes.activer_par_invitation(s, tok, "motdepasse-token-1", "2026-07-22")
        assert c.get(f"/invitation?token={tok}").status_code == 404
        # token forgé / inexistant → 404, jamais une fuite
        assert c.get(f"/invitation?token={'z'*43}").status_code == 404
        assert c.get("/invitation?token=").status_code == 404
        # reset : rejeu refusé
        with session_scope() as s:
            s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
            s.commit()
            r = comptes.demander_reset(s, email)
        rtok = r["lien"].split("token=")[1]
        with session_scope() as s:
            assert comptes.appliquer_reset(s, rtok, "nouveau-mdp-reset-1") is True
        with session_scope() as s:
            assert comptes.appliquer_reset(s, rtok, "encore-un-mdp-1") is False   # rejeu
        # invitation expirée → refusée
        with session_scope() as s:
            inv2 = comptes.creer_invitation(s, f"exp-{email}")
            tok2 = inv2["lien"].split("token=")[1]
            s.execute(text("UPDATE utilisateurs SET invite_expire_at = now() - interval '1 day'"
                           " WHERE email=:e"), {"e": f"exp-{email}"})
            s.commit()
            assert comptes.valider_invitation(s, tok2) is None
    finally:
        _purge(email, f"exp-{email}")


# ────────────────── PARTIE E · bascule Checkout : reachabilité + jeton signé ──────────────────

def test_bascule_paiement_atteignable_sans_session_mais_jeton_signe(app_client):
    """L'écran de bascule Checkout (partie E) est PUBLIC (atteint juste après l'invitation,
    avant toute session) mais sa sécurité est le jeton HMAC signé, PAS la session : jeton
    valide → 200 ; absent/altéré/forgé → 400 gracieux (jamais un 401 qui casserait le
    parcours d'onboarding, jamais un 500, jamais une fuite). La MÉCANIQUE de paiement
    (creer_checkout) n'est pas touchée : ce test verrouille seulement la porte présentational."""
    from labuse.api import coffre_ui
    cid = _compte_actif(email := f"basc-{uuid.uuid4().hex[:8]}@x.test")
    try:
        c = TestClient(app_client.app, base_url="https://testserver")   # AUCUNE session
        # jeton signé valide → l'écran s'affiche (pas de 401 : la page est publique par nature)
        bon = coffre_ui.pay_token(cid)
        r = c.get(f"/onboarding/paiement?t={bon}")
        assert r.status_code == 200 and "349" in r.text, r.text[:200]
        # jeton altéré : on retourne le DERNIER caractère de la signature vers une valeur
        # garantie différente (sinon 1/16 des signatures finissant par « 0 » rendraient la
        # mutation neutre → test flaky). Signature 1 bit à côté ⇒ compare_digest doit rejeter.
        altere = bon[:-1] + ("1" if bon[-1] == "0" else "0")
        # absent / non-parsable / forgé (bonne forme, mauvaise signature) / altéré → 400 gracieux,
        # jamais 401/500, jamais de Checkout lancé.
        for bad in ("", "bogus", f"{cid}.9999999999.0", altere):
            rb = c.get(f"/onboarding/paiement?t={bad}")
            assert rb.status_code == 400, (bad, rb.status_code)
            assert "expiré" in rb.text.lower()
    finally:
        _purge(email)


# ─────────────────────────── Brute force / verrou ───────────────────────────

def test_brute_force_verrou_non_contournable_par_casse(app_client):
    """Le verrou (5 échecs) suit l'email NORMALISÉ : changer la casse ne remet pas le compteur
    et n'ouvre pas une seconde fenêtre d'essais."""
    email = f"bf-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        # 4 échecs en minuscules puis 1 en MAJUSCULES → 5 au total sur le MÊME compte → verrou
        for i in range(5):
            ident = email if i < 4 else email.upper()
            assert c.post("/login", data={"identifiant": ident, "password": "faux"},
                          follow_redirects=False).status_code == 401
        # le bon mot de passe est maintenant refusé (compte verrouillé) — la casse n'a pas aidé
        assert c.post("/login", data={"identifiant": email, "password": "motdepasse-audit-1"},
                      follow_redirects=False).status_code == 401
    finally:
        _purge(email)


# ─────────────────────── Partie C — entrées hostiles (jamais un 500 nu) ───────────────────────

def test_entrees_login_jamais_500(app_client):
    """Login avec email malformé / unicode / casse / mot de passe limite → 401 propre, jamais 500."""
    c = TestClient(app_client.app, base_url="https://testserver")
    hostiles = [
        {"identifiant": "pas-un-email", "password": "x"},
        {"identifiant": "é@üñïçödé.tëst", "password": "motdepasse"},
        {"identifiant": "A@B.TEST", "password": ""},
        {"identifiant": "x" * 5000 + "@x.test", "password": "y" * 5000},
        {"identifiant": "", "password": ""},
        {"identifiant": "robert'); DROP TABLE comptes;--@x.test", "password": "z"},
    ]
    for data in hostiles:
        r = c.post("/login", data=data, follow_redirects=False)
        assert r.status_code in (401, 303), f"{data} → {r.status_code}"   # jamais 500
    # les comptes existent toujours (l'injection n'a rien cassé)
    with session_scope() as s:
        assert s.execute(text("SELECT to_regclass('comptes')")).scalar() is not None


def test_entrees_flash_idu_jamais_500(app_client):
    """/flash avec IDU inexistant / malformé / trop court → 4xx/redirect propre, jamais 500."""
    c = TestClient(app_client.app, base_url="https://testserver")
    for idu in ["", "court", "PASUNIDUVALIDE!!", "00000000000000", "'; DROP--xxxxx"]:
        r = c.get(f"/flash?idu={idu}", follow_redirects=False)
        assert r.status_code < 500, f"GET /flash?idu={idu} → {r.status_code}"
    # POST /flash (achat) sur un IDU inconnu → redirection vers la saisie, jamais 500
    r = c.post("/flash", data={"idu": "00000000000000"}, follow_redirects=False)
    assert r.status_code < 500


# ─────────────────────── P1 — durcissements rapides (audit 360) ───────────────────────

def test_logout_revoque_la_session_en_base(app_client):
    """La déconnexion RÉVOQUE le jeton côté serveur (pas seulement le cookie) : un cookie
    rejoué après /logout ne rouvre pas l'accès."""
    email = f"lo-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(email)

    def _n_sessions() -> int:
        with session_scope() as s:
            return s.execute(text(
                "SELECT count(*) FROM sessions_auth sa JOIN utilisateurs u ON u.id = sa.utilisateur_id"
                " WHERE u.email = :e"), {"e": email}).scalar()
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        _login(c, email)
        assert _n_sessions() >= 1                    # session ouverte en base
        c.get("/logout", follow_redirects=False)
        assert _n_sessions() == 0                     # révoquée côté serveur
    finally:
        _purge(email)


def test_hsts_en_https_jamais_en_clair(app_client):
    """HSTS posé en HTTPS (derrière Caddy) mais JAMAIS en http (un HSTS en clair bloquerait
    l'accès http à localhost en dev)."""
    r_https = TestClient(app_client.app, base_url="https://testserver").get("/healthz")
    assert r_https.headers.get("Strict-Transport-Security", "").startswith("max-age=")
    r_http = TestClient(app_client.app, base_url="http://testserver").get("/healthz")
    assert "Strict-Transport-Security" not in r_http.headers


# ─────────────────────── LABUSE_SECRET_KEY : fail-closed en prod (P0-3) ───────────────────────

def test_secret_key_exigee_hors_local(monkeypatch):
    """Hors 'local', l'absence de LABUSE_SECRET_KEY DOIT empêcher le démarrage (fail-closed) :
    sans clé stable, le jeton de paiement serait forgeable. En 'local', clé éphémère tolérée."""
    from labuse import config
    from labuse.api import auth
    # local sans secret → toléré (clé éphémère)
    monkeypatch.setenv("LABUSE_ENV", "local")
    monkeypatch.delenv("LABUSE_SECRET_KEY", raising=False)
    config.get_settings.cache_clear()
    auth.exiger_secret_prod()                    # ne lève pas
    # production sans secret → refus de démarrer, message clair
    monkeypatch.setenv("LABUSE_ENV", "production")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        auth.exiger_secret_prod()
    # production AVEC secret → OK
    monkeypatch.setenv("LABUSE_SECRET_KEY", "x" * 32)
    config.get_settings.cache_clear()
    auth.exiger_secret_prod()                    # ne lève pas
    config.get_settings.cache_clear()


def test_env_local_avec_secret_key_refuse_le_boot(monkeypatch):
    """M149 L2 (audit M148 F4) : garde symétrique de exiger_secret_prod. Une clé de signature
    posée en env='local' trahit un déploiement laissé en dev (auth désactivée = routes ouvertes) →
    le démarrage DOIT échouer, pas ouvrir. Le dev pur (local, clé éphémère) démarre normalement."""
    from labuse import config
    from labuse.api import auth
    # local + clé de signature posée = misconfig de déploiement → refus de démarrer
    monkeypatch.setenv("LABUSE_ENV", "local")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "cle-persistante-de-deploiement-000")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="local.*SECRET_KEY|SECRET_KEY.*local|déploiement"):
        auth.exiger_env_deploiement()
    # dev pur : local SANS clé (éphémère, défaut documenté) → ne lève pas
    monkeypatch.delenv("LABUSE_SECRET_KEY", raising=False)
    config.get_settings.cache_clear()
    auth.exiger_env_deploiement()
    # déploiement correct : pilot AVEC clé → ne lève pas
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "cle-persistante-de-deploiement-000")
    config.get_settings.cache_clear()
    auth.exiger_env_deploiement()
    config.get_settings.cache_clear()


def test_pay_token_sans_secret_en_dur(monkeypatch):
    """Le jeton de bascule paiement ne repose plus sur une constante en dur : un jeton forgé
    avec l'ancien secret « labuse-dev-secret » est REFUSÉ ; un vrai jeton est accepté."""
    import time

    from labuse import config
    from labuse.api import coffre_ui
    monkeypatch.setenv("LABUSE_ENV", "local")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "vraie-cle-secrete-0000000000000000")
    config.get_settings.cache_clear()
    payload = f"42.{int(time.time()) + 1800}"
    forge = hmac.new(b"labuse-dev-secret", payload.encode(), hashlib.sha256).hexdigest()[:32]
    assert coffre_ui.pay_cid(f"{payload}.{forge}") is None       # ancien secret en dur → refusé
    assert coffre_ui.pay_cid(coffre_ui.pay_token(42)) == 42       # vrai jeton → accepté
    config.get_settings.cache_clear()


def test_entrees_pipeline_idu_jamais_500(app_client):
    """API pipeline/parcelle avec IDU hostile → 4xx propre (auth d'abord), jamais 500."""
    email = f"in-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        c.cookies.set("labuse_session", _session_cookie(cid, email))
        for idu in ["court", "PASBON!!", "'; DROP TABLE parcels;--"]:
            assert c.get(f"/pipeline/parcel/{idu}").status_code < 500
            assert c.post("/pipeline", json={"idu": idu}).status_code < 500
    finally:
        _purge(email)


def test_entrees_idu_rail_premium_jamais_500(app_client):
    """M-K P2-31 : IDU hostile/malformé sur le rail premium (/v2, /modules) → 4xx propre
    (garde de forme _check_idu alignée sur le rail principal), jamais un 500 driver."""
    email = f"pr-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver")
        c.cookies.set("labuse_session", _session_cookie(cid, email))
        for idu in ["court!!", "'; DROP TABLE parcels;--", "x" * 40]:
            assert c.get(f"/v2/score/{idu}").status_code < 500, idu
            assert c.get(f"/modules/faisabilite/{idu}").status_code < 500, idu
    finally:
        _purge(email)


def test_protection_admin_exige_une_session(app_client):
    """M31 PC2 — les endpoints d'ADMINISTRATION (tableau de bord protection, gel/dégel d'un
    sujet) ne sont JAMAIS publics : sans session, la garde middleware répond 401 (jamais 200,
    jamais l'action). Adversarial : un audit avait signalé « aucun Depends() » sur ces routes —
    la protection vient de la garde globale (_auth_guard), pas d'une dépendance de route. Ce
    test verrouille l'invariant (freeze/unfreeze d'un client = action sensible)."""
    c = TestClient(app_client.app, base_url="https://testserver")   # aucune session posée
    assert c.get("/protection/admin").status_code == 401
    assert c.post("/protection/admin/gel/1.2.3.4").status_code == 401
    assert c.post("/protection/admin/degel/1.2.3.4").status_code == 401
    # invariant de liste blanche : ces chemins ne sont jamais dans le périmètre public
    from labuse.api import auth
    for p in ("/protection/admin", "/protection/admin/gel/x", "/protection/admin/degel/x"):
        assert not auth.is_public(p)


def _login_admin(client: TestClient, email: str) -> TestClient:
    """Login puis élève l'utilisateur en role='admin' (le rôle est relu en base à chaque
    requête → l'élévation prend effet immédiatement)."""
    _login(client, email)
    with session_scope() as s:
        s.execute(text("UPDATE utilisateurs SET role='admin' WHERE email=:e"), {"e": email})
        s.commit()
    return client


def test_idor_partners_share_et_profiles(app_client):
    """M-K P2-45 : share_list est SCOPÉ au compte (B ne voit pas les tokens de A pour une même
    parcelle — un token = accès public en lecture) ; POST /partners/profiles est GELÉ admin
    (M19 démo) : un titulaire → 403, un admin → 200."""
    ea, eb, eadm = (f"a-{uuid.uuid4().hex[:8]}@x.test", f"b-{uuid.uuid4().hex[:8]}@x.test",
                    f"adm-{uuid.uuid4().hex[:8]}@x.test")
    _compte_actif(ea); _compte_actif(eb); _compte_actif(eadm)
    idu = f"974SH{uuid.uuid4().hex[:7].upper()}"
    _wkt = "POLYGON((55.47 -21.0,55.471 -21.0,55.471 -21.001,55.47 -21.001,55.47 -21.0))"
    try:
        ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
        cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
        with session_scope() as s:
            s.execute(text("INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
                           "VALUES (:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
                           " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                      {"i": idu, "w": _wkt}); s.commit()
        # A crée un lien de partage → A le voit ; B ne voit AUCUN lien pour la même parcelle
        rt = ca.post(f"/partners/share/{idu}")
        assert rt.status_code == 200, rt.text
        tok = rt.json()["token"]
        assert any(x["token"] == tok for x in ca.get(f"/partners/share/{idu}/list").json())
        assert cb.get(f"/partners/share/{idu}/list").json() == []
        # POST /partners/profiles : titulaire 403, admin 200
        assert ca.post("/partners/profiles", json={"nom": "profil pirate"}).status_code == 403
        cadm = TestClient(app_client.app, base_url="https://testserver"); _login_admin(cadm, eadm)
        assert cadm.post("/partners/profiles", json={"nom": "profil admin M-K"}).status_code == 200
    finally:
        _purge(ea, eb, eadm)
        with session_scope() as s:
            s.execute(text("DELETE FROM share_links WHERE idu = :i"), {"i": idu})
            s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
            s.execute(text("DELETE FROM match_profiles WHERE nom = 'profil admin M-K'"))
            s.commit()


def test_quota_ia_nl_429_au_depassement(app_client, monkeypatch):
    """M-K P2-5 : au-delà du plafond JOURNALIER (kind 'nl'), /ia/search renvoie un 429 honnête.
    Avant, /ia/* n'avait que le 60/min → un client scripté brûlait du sonnet toute la journée."""
    from labuse import config
    monkeypatch.setenv("LABUSE_NL_QUOTA_JOUR", "2")
    config.get_settings.cache_clear()
    email = f"nl-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver"); _login(c, email)
        assert c.post("/ia/search", json={"text": "terrains à Saint-Paul"}).status_code == 200
        assert c.post("/ia/search", json={"text": "grandes parcelles"}).status_code == 200
        r = c.post("/ia/search", json={"text": "encore une recherche"})   # 3e > quota 2
        assert r.status_code == 429, r.text
        assert "Quota" in r.json()["detail"]["detail"]
    finally:
        _purge(email)
        with session_scope() as s:
            s.execute(text("DELETE FROM usage_compteurs WHERE sujet=:s AND kind='nl'"), {"s": f"c:{cid}"}); s.commit()
        config.get_settings.cache_clear()


def test_quota_dossier_epingle_au_compte_survit_au_relogin(app_client):
    """M-K P2-38 : le quota mensuel de dossiers est compté PAR COMPTE — un logout/login ne le
    remet PAS à zéro (avant, le sujet-session changeait à chaque session → quota contournable,
    le mensuel Essentiel étant le plus exposé)."""
    email = f"q-{uuid.uuid4().hex[:8]}@x.test"
    cid = _compte_actif(email)
    try:
        c = TestClient(app_client.app, base_url="https://testserver"); _login(c, email)
        assert c.get("/dossier/statut").json()["utilises_mois"] == 0
        # un dossier généré ce mois-ci, compté sur le sujet COMPTE (« c:<cid> »)
        with session_scope() as s:
            s.execute(text("INSERT INTO usage_compteurs (jour, sujet, kind, n) "
                           "VALUES (CURRENT_DATE, :s, 'dossier', 1)"), {"s": f"c:{cid}"})
            s.commit()
        assert c.get("/dossier/statut").json()["utilises_mois"] == 1
        # logout puis relogin (nouvelle session, nouveau cookie) → le compteur NE bouge PAS
        c.get("/logout", follow_redirects=False)
        c2 = TestClient(app_client.app, base_url="https://testserver"); _login(c2, email)
        assert c2.get("/dossier/statut").json()["utilises_mois"] == 1
    finally:
        _purge(email)
        with session_scope() as s:
            s.execute(text("DELETE FROM usage_compteurs WHERE sujet = :s"), {"s": f"c:{cid}"}); s.commit()


def test_gate_admin_protection_et_bilan(app_client):
    """M-K P1-10/P1-11 : un TITULAIRE (client payant authentifié) est REFUSÉ (403) sur les
    routes d'administration (tableau protection, gel/dégel d'un sujet) et sur POST
    /bilan/params (paramètres servis à tous) ; un ADMIN n'est jamais 403."""
    et, eadm = f"t-{uuid.uuid4().hex[:8]}@x.test", f"adm-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(et); _compte_actif(eadm)
    routes = [("get", "/protection/admin", None),
              ("post", "/protection/admin/gel/1.2.3.4", None),
              ("post", "/protection/admin/degel/1.2.3.4", None),
              ("post", "/bilan/params", {"secteur": "*", "param": "prix_sortie_m2", "value": 2500})]
    try:
        ct = TestClient(app_client.app, base_url="https://testserver"); _login(ct, et)
        cadm = TestClient(app_client.app, base_url="https://testserver"); _login_admin(cadm, eadm)
        for meth, path, body in routes:
            kw = {"json": body} if body is not None else {}
            assert getattr(ct, meth)(path, **kw).status_code == 403, f"titulaire non bloqué sur {path}"
            radm = getattr(cadm, meth)(path, **kw).status_code
            assert radm != 403, f"admin bloqué à tort sur {path} (reçu {radm})"
    finally:
        _purge(et, eadm)


def test_marque_roundtrip_logo_relu(app_client):
    """M54-EXPO-2 A6 : upload logo (body brut) + marque, puis GET /moi/marque relit le tout
    (has_logo + logo_data_uri + les 3 champs). Round-trip fidèle : même compte que l'upload
    (_compte_session). Suppression du logo → le GET le reflète."""
    e = f"marque-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(e)
    try:
        c = TestClient(app_client.app, base_url="https://testserver"); _login(c, e)
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
        r = c.post("/moi/logo", content=png, headers={"Content-Type": "image/png"})
        assert r.status_code == 200 and r.json()["octets"] == len(png), r.text
        assert c.post("/moi/marque", json={"raison_sociale": "Foncière Test",
                                           "coordonnees": "01 23 45 67", "mention": "Doc interne"}).status_code == 200
        g = c.get("/moi/marque").json()
        assert g["has_logo"] is True
        assert g["logo_data_uri"].startswith("data:image/png;base64,")
        assert g["raison_sociale"] == "Foncière Test" and g["mention"] == "Doc interne"
        # suppression du logo → relu à false, marque conservée
        assert c.delete("/moi/logo").json()["ok"]
        g2 = c.get("/moi/marque").json()
        assert g2["has_logo"] is False and g2["raison_sociale"] == "Foncière Test"
    finally:
        _purge(e)
