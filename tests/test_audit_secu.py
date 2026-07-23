"""AUDIT PAIEMENT · PARTIE A — sécurité de l'accès (tests ADVERSARIAUX permanents).

Chaque test attaque une faille : s'il tombe, la cloison est ouverte. Ils RESTENT dans la
suite (régression). DB réelle (labuse_test), auth active, deux comptes réels.
"""
from __future__ import annotations

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
    return TestClient(app, base_url="https://testserver")


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
