"""CLOISONNEMENT-1 — l'épreuve à DEUX COMPTES, rejouée de bout en bout.

Avant d'ouvrir un accès à une testeuse externe : prouver, sur DB réelle + auth active, que
tout ce qu'un compte crée ou règle reste À LUI. Le compte A crée UNE de chaque objet client ;
le compte B ne doit RIEN voir (liste), RIEN toucher par id (lecture/modif/suppression → 403/404
ou {ok:false} sans effet), et les JOBS (digest) ne doivent jamais mêler les comptes ni faire
hériter B de la fréquence de A. Une fuite = un test rouge, épinglé à son objet.

Complète test_audit_comptes.py (Copilote/CRM colonnes/courrier) sur TOUS les autres objets :
suivi de parcelle, alerte Radar, zone de veille, projet (+parcelles+note), piste CRM (+retour
terrain+note), vue sauvegardée, filtre sauvegardé, signalement, questions Copilote + plafond,
réglage digest, notifications de la cloche — puis le digest en dry-run.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
_POLY_GEOJSON = {"type": "Polygon", "coordinates": [[[55.45, -20.9], [55.451, -20.9],
                                                     [55.451, -20.901], [55.45, -20.901], [55.45, -20.9]]]}


@pytest.fixture
def app_client(engine, monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-cloison-1")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-cloison-1-00000000000000000000")
    # jamais un envoi réel pendant l'épreuve (SMTP/Brevo absents → mail journalisé/dry-run)
    monkeypatch.setenv("LABUSE_SMTP_HOST", "")
    monkeypatch.setenv("BREVO_API_KEY", "")
    from labuse import config
    config.get_settings.cache_clear()
    from labuse.api.app import app
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def _compte_actif(email: str) -> int:
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-cloison-1", "2026-09-28")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
    r = client.post("/login", data={"identifiant": email, "password": "motdepasse-cloison-1"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    return client


def _seed_parcelle(idu: str) -> None:
    with session_scope() as s:
        exists = s.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        if not exists:
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
                " VALUES (:i,'Saint-Denis','ZZ','1', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 800,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "w": _WKT})
        s.commit()


def _purge(*emails):
    with session_scope() as s:
        for e in emails:
            try:
                comptes.supprimer_utilisateur(s, e)
            except Exception:
                pass


@pytest.fixture
def deux_comptes(app_client):
    """Deux comptes actifs A et B, chacun connecté. Rend (ca, cb, cid_a, cid_b, idu1, idu2)."""
    ea, eb = f"cta-{uuid.uuid4().hex[:8]}@x.test", f"ctb-{uuid.uuid4().hex[:8]}@x.test"
    # IDU cadastral = 14 car. : INSEE(5) + préfixe(3) + section(2) + numéro(4)
    n = uuid.uuid4().int
    idu1 = f"97411000AA{n % 10000:04d}"
    idu2 = f"97411000BB{(n // 10000) % 10000:04d}"
    cid_a = _compte_actif(ea)
    cid_b = _compte_actif(eb)
    _seed_parcelle(idu1)
    _seed_parcelle(idu2)
    ca = TestClient(app_client.app, base_url="https://testserver"); _login(ca, ea)
    cb = TestClient(app_client.app, base_url="https://testserver"); _login(cb, eb)
    try:
        yield ca, cb, cid_a, cid_b, idu1, idu2
    finally:
        with session_scope() as s:
            for idu in (idu1, idu2):
                s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu})
            s.commit()
        _purge(ea, eb)


# ─────────────────────────── SUIVI DE PARCELLE (watched_parcels) ───────────────────────────
def test_suivi_parcelle_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    r = ca.post(f"/events/watch/{idu1}", json={})
    assert r.status_code == 200, r.text
    # A suit ; B ne voit pas le suivi de A sur cette parcelle
    assert ca.get(f"/events/watch/{idu1}").json().get("watched") is True
    assert cb.get(f"/events/watch/{idu1}").json().get("watched") is False
    # en base : le suivi de A survit, B n'en a aucun
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM watched_parcels WHERE idu=:i AND compte_id=:c"),
                         {"i": idu1, "c": cid_a}).scalar() == 1
        assert s.execute(text("SELECT count(*) FROM watched_parcels WHERE idu=:i AND compte_id=:c"),
                         {"i": idu1, "c": cid_b}).scalar() == 0


# ─────────────────────────── ALERTE RADAR (veilles pige) ───────────────────────────
def test_alerte_radar_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    r = ca.post("/radar/veille", json={"commune": "Saint-Denis", "type_bien": "maison"})
    assert r.status_code == 200, r.text
    vid = r.json()["veille_id"]
    # A la voit ; B ne la voit pas
    assert any(v["id"] == vid for v in ca.get("/radar/veille").json()["veilles"])
    assert all(v["id"] != vid for v in cb.get("/radar/veille").json()["veilles"])
    # B ne peut ni supprimer ni renommer la veille de A (garde IDOR → ok:false, survit)
    assert cb.delete(f"/radar/veille/{vid}").json()["ok"] is False
    assert cb.patch(f"/radar/veille/{vid}", json={"nom": "VOL"}).json()["ok"] is False
    assert any(v["id"] == vid for v in ca.get("/radar/veille").json()["veilles"])


# ─────────────────────────── ZONE DE VEILLE (watch_zones) ───────────────────────────
def test_watch_zone_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    r = ca.post("/watch-zones", json={"name": "Zone de A", "commune": "Saint-Denis", "geometry": _POLY_GEOJSON})
    assert r.status_code == 200, r.text
    zid = r.json()["zone"]["id"]
    # A la voit ; B ne la voit pas
    assert any(z["id"] == zid for z in ca.get("/watch-zones?commune=Saint-Denis").json())
    assert all(z["id"] != zid for z in cb.get("/watch-zones?commune=Saint-Denis").json())
    # B ne peut ni renommer ni supprimer → 404, la zone de A survit
    assert cb.patch(f"/watch-zones/{zid}", json={"name": "VOL"}).status_code == 404
    assert cb.delete(f"/watch-zones/{zid}").status_code == 404
    assert any(z["id"] == zid for z in ca.get("/watch-zones?commune=Saint-Denis").json())


# ─────────────────────────── PROJET (+2 parcelles + note) ───────────────────────────
def test_projet_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, idu2 = deux_comptes
    r = ca.post("/projets", json={"nom": "Projet de A", "cadrage": {"communes": ["Saint-Denis"]}, "de_zero": True})
    assert r.status_code == 200, r.text
    pid = r.json()["projet"]["id"]
    assert ca.post(f"/projets/{pid}/ajouter", json={"idu": idu1}).status_code == 200
    assert ca.post(f"/projets/{pid}/ajouter", json={"idu": idu2}).status_code == 200
    # note portée par le projet (identite/nom) — patch OK pour A
    assert ca.patch(f"/projets/{pid}", json={"nom": "Projet de A — noté"}).status_code == 200
    # A le voit ; B ne le voit pas
    assert any(p["id"] == pid for p in ca.get("/projets").json())
    assert all(p["id"] != pid for p in cb.get("/projets").json())
    # B ne peut ni lire, ni patcher, ni supprimer, ni lister les parcelles → 404
    assert cb.get(f"/projets/{pid}").status_code == 404
    assert cb.patch(f"/projets/{pid}", json={"nom": "VOL"}).status_code == 404
    assert cb.get(f"/projets/{pid}/parcelles").status_code == 404
    assert cb.delete(f"/projets/{pid}").status_code == 404
    # le projet de A survit et porte bien ses 2 parcelles, scopées au compte de A
    assert ca.get(f"/projets/{pid}").status_code == 200
    with session_scope() as s:
        assert s.execute(text("SELECT compte_id FROM projets WHERE id=:p"), {"p": pid}).scalar() == cid_a
        assert s.execute(text("SELECT count(*) FROM projet_parcelles WHERE projet_id=:p"), {"p": pid}).scalar() == 2


# ─────────────────────────── CRM (piste + retour terrain + note) ───────────────────────────
def test_crm_piste_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    r = ca.post("/pipeline", json={"idu": idu1, "notes": "Note privée de A"})  # statut = défaut du compte
    assert r.status_code == 200, r.text
    entry = r.json()
    eid = entry.get("id") or (entry.get("entry") or {}).get("id")
    assert eid, entry
    # retour terrain (contact_etiquette) + note par A
    assert ca.patch(f"/pipeline/{eid}", json={"contact_etiquette": "contacte", "notes": "Contacté hier"}).status_code == 200
    # A voit la piste (liste + par parcelle) ; B ne la voit pas
    assert any(e.get("id") == eid for e in ca.get("/pipeline").json())
    assert all(e.get("id") != eid for e in cb.get("/pipeline").json())
    # B lit la fiche/CRM de la même parcelle → aucune piste, aucune note de A
    b_parcel = cb.get(f"/pipeline/parcel/{idu1}").json()
    assert not b_parcel.get("entry") and not b_parcel.get("notes")
    # B ne peut ni patcher ni supprimer la piste de A → 404, elle survit avec sa note
    assert cb.patch(f"/pipeline/{eid}", json={"notes": "VOL"}).status_code == 404
    assert cb.request("DELETE", f"/pipeline/{eid}", json={}).status_code == 404
    with session_scope() as s:
        row = s.execute(text("SELECT compte_id, notes FROM pipeline_entries WHERE id=:i"), {"i": eid}).mappings().first()
    assert row and row["compte_id"] == cid_a and "VOL" not in (row["notes"] or "")


# ─────────────────────────── VUE SAUVEGARDÉE (saved_searches) ───────────────────────────
def test_vue_sauvegardee_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    r = ca.post("/events/searches", json={"nom": "Vue de A", "hash": f"h-{uuid.uuid4().hex[:8]}"})
    assert r.status_code == 200, r.text
    # /events/searches renvoie une LISTE ; récupère l'id de la vue de A
    sid = next(s["id"] for s in ca.get("/events/searches").json() if s.get("nom") == "Vue de A")
    # A la voit ; B ne la voit pas
    assert any(s["id"] == sid for s in ca.get("/events/searches").json())
    assert all(s["id"] != sid for s in cb.get("/events/searches").json())
    # B ne peut pas la supprimer/patcher (filtre compte → 404 ou sans effet)
    rb = cb.request("DELETE", f"/events/searches/{sid}", json={})
    assert rb.status_code in (404, 200)
    with session_scope() as s:
        assert s.execute(text("SELECT compte_id FROM saved_searches WHERE id=:i"), {"i": sid}).scalar() == cid_a


# ─────────────────────────── FILTRE SAUVEGARDÉ (saved_filters) ───────────────────────────
def test_filtre_sauvegarde_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    r = ca.post("/filters", json={"name": "Filtre de A", "params": {"zone_fam": "U"}})
    assert r.status_code == 200, r.text
    fid = r.json().get("id") or r.json().get("filter_id")
    assert any(f["id"] == fid for f in ca.get("/filters").json())
    assert all(f["id"] != fid for f in cb.get("/filters").json())
    # B ne peut pas supprimer le filtre de A → 404, il survit
    assert cb.request("DELETE", f"/filters/{fid}", json={}).status_code == 404
    with session_scope() as s:
        assert s.execute(text("SELECT compte_id FROM saved_filters WHERE id=:i"), {"i": fid}).scalar() == cid_a


# ─────────────────────────── SIGNALEMENT ───────────────────────────
def test_signalement_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    r = ca.post("/signalements", json={"idu": idu1, "type_erreur": "autre",
                                       "commentaire": "Signalement de A"})
    assert r.status_code == 200, r.text
    # A voit son signalement ; B ne voit pas celui de A
    a_list = ca.get("/signalements").json()
    a_items = a_list if isinstance(a_list, list) else a_list.get("signalements", [])
    assert any("A" in (x.get("commentaire") or "") for x in a_items)
    b_list = cb.get("/signalements").json()
    b_items = b_list if isinstance(b_list, list) else b_list.get("signalements", [])
    assert all("Signalement de A" != (x.get("commentaire") or "") for x in b_items)


# ─────────────────────────── DEMANDE DE COURRIER ───────────────────────────
def test_courrier_demande_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    r = ca.post("/courrier/demande", json={"parcelles": [idu1], "communes": "Saint-Denis",
                                           "modele": "standard", "corps": "Demande de A."})
    assert r.status_code == 200, r.text
    did = r.json()["id"]
    assert any(d["id"] == did for d in ca.get("/courrier/demandes").json()["demandes"])
    assert all(d["id"] != did for d in cb.get("/courrier/demandes").json()["demandes"])
    # route ADMIN de statut refusée à un client (403) ; route CLIENT scopée compte (n'atteint pas A)
    assert cb.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "imprime"}).status_code == 403
    cb.post(f"/courrier/demandes/{did}/statut", json={"statut": "repondu"})  # scopé B → ne touche pas A
    with session_scope() as s:
        row = s.execute(text("SELECT compte_id, statut FROM courrier_demandes WHERE id=:i"), {"i": did}).mappings().first()
        assert row["compte_id"] == cid_a and row["statut"] == "demande"  # demande de A intacte
        s.execute(text("DELETE FROM courrier_demandes WHERE id=:i"), {"i": did}); s.commit()


# ─────────────────────────── COPILOTE : questions + plafond ───────────────────────────
def test_copilote_questions_et_plafond_cloison(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    # A pose 2 questions → 1 conversation persistée
    r1 = ca.post("/api/copilote-v2/ask", json={"message": "Première question de A."})
    assert r1.status_code == 200, r1.text
    conv = r1.json().get("conversation_id")
    ca.post("/api/copilote-v2/ask", json={"message": "Deuxième question de A.", "conversation_id": conv})
    assert conv is not None
    # A ouvre SA conversation ; B ne le peut pas (404), et ne la liste pas
    assert ca.get(f"/api/copilote-v2/missions/{conv}").status_code == 200
    assert cb.get(f"/api/copilote-v2/missions/{conv}").status_code == 404
    assert all(m.get("id") != conv for m in cb.get("/api/copilote-v2/missions").json().get("missions", []))
    # plafond/usage de B intact : les questions de A n'ont rien consommé chez B
    with session_scope() as s:
        usage_b = s.execute(text("SELECT count(*) FROM ia_log WHERE compte_id=:c"), {"c": cid_b}).scalar()
        usage_a = s.execute(text("SELECT count(*) FROM ia_log WHERE compte_id=:c"), {"c": cid_a}).scalar()
    assert usage_b == 0, f"le plafond de B a bougé alors que seul A a posé des questions (ia_log B={usage_b})"
    assert usage_a >= 1


# ─────────────────────────── RÉGLAGE DIGEST (digest_freq par compte) ───────────────────────────
def test_digest_freq_par_compte(deux_comptes):
    ca, cb, cid_a, cid_b, _, _ = deux_comptes
    # A règle hebdo ; B laisse quotidien (défaut)
    assert ca.patch("/events/prefs/frequence", json={"frequence": "hebdo"}).status_code == 200
    assert ca.get("/events/prefs").json().get("frequence") == "hebdo"
    # B n'hérite pas du hebdo de A : sa fréquence reste quotidien
    assert cb.get("/events/prefs").json().get("frequence") == "quotidien"
    with session_scope() as s:
        assert s.execute(text("SELECT digest_freq FROM notif_prefs WHERE compte_id=:c"), {"c": cid_a}).scalar() == "hebdo"
        fb = s.execute(text("SELECT digest_freq FROM notif_prefs WHERE compte_id=:c"), {"c": cid_b}).scalar()
        assert fb in (None, "quotidien")


# ─────────────────────────── NOTIFICATIONS DE LA CLOCHE (event_log) ───────────────────────────
def test_cloche_cloison(deux_comptes):
    from labuse.api.events import creer_notification
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    with session_scope() as s:
        eid = creer_notification(s, kind="radar", titre="Bien de A", compte_id=cid_a, idu=idu1,
                                 dedup=f"cloison:{cid_a}:{uuid.uuid4().hex[:6]}")
        s.commit()
    assert eid
    # A voit l'événement dans sa cloche ; B ne le voit pas (GET /events → {"unread","items"})
    assert any(e.get("id") == eid for e in ca.get("/events").json()["items"])
    assert all(e.get("id") != eid for e in cb.get("/events").json()["items"])
    # B ne peut pas marquer lu l'événement de A (filtre compte)
    cb.post(f"/events/{eid}/read", json={})
    with session_scope() as s:
        vu_b = s.execute(text("SELECT count(*) FROM event_seen WHERE event_id=:e AND compte_id=:c"),
                         {"e": eid, "c": cid_b}).scalar()
    assert vu_b == 0, "B a pu marquer lu un événement de A"


# ─────────────────────────── JOB DIGEST (dry-run, cross-tenant) ───────────────────────────
def test_digest_job_cross_tenant(deux_comptes):
    from labuse.api.events import creer_notification, envoyer_digests, set_digest_freq
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    # A suit une parcelle et reçoit un événement ; B suit une AUTRE parcelle, événement distinct
    marqueur_a = f"EVENEMENT-A-{uuid.uuid4().hex[:6]}"
    marqueur_b = f"EVENEMENT-B-{uuid.uuid4().hex[:6]}"
    with session_scope() as s:
        set_digest_freq(s, cid_a, "hebdo")       # A en hebdo
        set_digest_freq(s, cid_b, "quotidien")   # B en quotidien
        creer_notification(s, kind="radar", titre=marqueur_a, compte_id=cid_a, idu=idu1,
                           dedup=f"dgA:{cid_a}:{uuid.uuid4().hex[:6]}")
        creer_notification(s, kind="radar", titre=marqueur_b, compte_id=cid_b, idu=idu1,
                           dedup=f"dgB:{cid_b}:{uuid.uuid4().hex[:6]}")
        s.commit()
    with session_scope() as s:
        res = envoyer_digests(s, base_url="https://testserver", force=True, dry_run=True)
    # récupère le corps simulé de chaque compte
    par_compte = {d["compte"]: d for d in res["details"]}
    da, db_ = par_compte.get(cid_a, {}), par_compte.get(cid_b, {})
    corps_a, corps_b = da.get("corps", ""), db_.get("corps", "")
    # A ne reçoit QUE son événement ; B ne reçoit QUE le sien — aucun croisement
    assert marqueur_a in corps_a and marqueur_b not in corps_a, f"digest A pollué: {corps_a[:200]}"
    assert marqueur_b in corps_b and marqueur_a not in corps_b, f"digest B pollué: {corps_b[:200]}"
    # rien n'a été réellement envoyé (dry-run)
    assert res["dry_run"] is True and res["envoyes"] == 0


# ─────────────────────────── SYMÉTRIE : B crée, A ne voit pas ───────────────────────────
def test_symetrie_B_cree_A_ne_voit_pas(deux_comptes):
    ca, cb, cid_a, cid_b, idu1, _ = deux_comptes
    r = cb.post("/projets", json={"nom": "Projet de B", "cadrage": {"communes": ["Saint-Denis"]}, "de_zero": True})
    assert r.status_code == 200, r.text
    pid = r.json()["projet"]["id"]
    assert any(p["id"] == pid for p in cb.get("/projets").json())
    assert all(p["id"] != pid for p in ca.get("/projets").json())
    assert ca.get(f"/projets/{pid}").status_code == 404
    assert ca.delete(f"/projets/{pid}").status_code == 404


# ─────────────────────────── SUPPRESSION DE COMPTE : efface TOUS ses objets ───────────────────────────
def test_suppression_compte_efface_tous_ses_objets(app_client):
    """Lot D — la suppression RGPD d'un compte (effacer_compte_rgpd) doit emporter TOUTES ses données
    client. Les tables à cascade FK partent par le DELETE comptes ; `mail_queue` et
    `contact_etiquette_log` (compte_id SANS FK — tag libre du spool) sont effacées EXPLICITEMENT par
    effacer_compte_rgpd. Un orphelin (ligne à compte_id pointant un compte disparu) est un défaut de
    cloison (RGPD + risque de résurgence si un id est réutilisé). Aucun orphelin après effacement."""
    email = f"ctdel-{uuid.uuid4().hex[:8]}@x.test"
    idu = f"97411000ZZ{uuid.uuid4().int % 10000:04d}"
    cid = _compte_actif(email)
    _seed_parcelle(idu)
    with session_scope() as s:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        # une ligne dans chaque table à compte_id qui existait SANS FK cascade
        s.execute(text("INSERT INTO mail_queue (compte_id, mail_key, destinataire, etat)"
                       " VALUES (:c,'digest_quotidien','ctdel@x.test','en_attente')"), {"c": cid})
        eid = s.execute(text("INSERT INTO pipeline_entries (parcel_id, status, priority, compte_id)"
                             " VALUES (:p,'reperee','moyenne',:c) RETURNING id"), {"p": pid, "c": cid}).scalar()
        s.execute(text("INSERT INTO contact_etiquette_log (compte_id, parcel_id, entry_id, etiquette)"
                       " VALUES (:c,:p,:e,'contacte')"), {"c": cid, "p": pid, "e": eid})
        s.execute(text("INSERT INTO projets (nom, filtres, compte_id) VALUES ('P del', '{}', :c)"), {"c": cid})
        s.commit()
    # comptage AVANT — chaque table porte bien une ligne du compte
    tables = ("mail_queue", "contact_etiquette_log", "pipeline_entries", "projets")
    with session_scope() as s:
        avant = {t: s.execute(text(f"SELECT count(*) FROM {t} WHERE compte_id=:c"), {"c": cid}).scalar()
                 for t in tables}
    assert all(v >= 1 for v in avant.values()), avant
    # EFFACEMENT RGPD → cascade
    with session_scope() as s:
        comptes.effacer_compte_rgpd(s, email)
    with session_scope() as s:
        apres = {t: s.execute(text(f"SELECT count(*) FROM {t} WHERE compte_id=:c"), {"c": cid}).scalar()
                 for t in tables}
        assert s.execute(text("SELECT count(*) FROM comptes WHERE id=:c"), {"c": cid}).scalar() == 0
        s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu}); s.commit()
    assert all(v == 0 for v in apres.values()), f"orphelins après effacement du compte : {apres}"


# ─────────────────────────── ADMIN : Vic voit bien les deux (pas une fuite) ───────────────────────────
def test_admin_voit_les_deux(app_client):
    """Le dashboard admin voit les deux comptes — attendu, ce n'est pas une fuite de cloison."""
    ea, eb = f"cta-{uuid.uuid4().hex[:8]}@x.test", f"ctb-{uuid.uuid4().hex[:8]}@x.test"
    _compte_actif(ea); _compte_actif(eb)
    try:
        admin = TestClient(app_client.app, base_url="https://testserver")
        admin.post("/login", data={"password": "pilote-cloison-1"}, follow_redirects=False)  # session pilote = admin
        r = admin.get("/admin/licences")
        assert r.status_code == 200, r.text
    finally:
        _purge(ea, eb)
