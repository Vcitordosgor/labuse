"""DASHBOARD-V1 — Tour de contrôle. D1 : capteurs (usage, retours, ia par compte, quota licence)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config
    from labuse.api import dashboard
    from labuse.api.app import app
    dashboard.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM retours"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_usage_event_compte_et_agregat(client, engine):
    """D1 — capteur d'usage : l'ouverture d'outil s'enregistre ; un kind inconnu → 422 (contrat)."""
    r = client.post("/usage/event", json={"kind": "outil", "outil": "courrier"})
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.post("/usage/event", json={"kind": "heartbeat"})
    assert r.status_code == 200
    with engine.begin() as c:
        rows = c.execute(text("SELECT kind, outil FROM usage_events ORDER BY id")).all()
    assert [tuple(x) for x in rows] == [("outil", "courrier"), ("heartbeat", None)]
    assert client.post("/usage/event", json={"kind": "n_importe_quoi"}).status_code == 422


def test_signalements_unifies_fiche_et_annonce(client, engine):
    """CONNEXIONS-2 Lot 3 (KO-4) — le « Signaler » de la fiche (type='fiche') ET celui du Radar
    (type='annonce') écrivent dans la MÊME table `signalements` ; l'admin les VOIT et les TRAITE au
    dashboard (plus de revue CLI-only) ; le compteur lit cette table. Échoue sur l'ancien code (deux
    tables disjointes, revue fiche CLI-only)."""
    with engine.begin() as c:
        c.execute(text("DELETE FROM signalements"))
    # 1) signalement FICHE (client → /signalements)
    r = client.post("/signalements", json={"idu": "97411000AB0001", "type_erreur": "zonage",
                                           "commentaire": "zone fausse"})
    assert r.status_code == 200
    # 2) signalement ANNONCE (Radar → pige.client.signaler) écrit dans la MÊME table
    from labuse.db import session_scope
    from labuse.pige.client import signaler
    with session_scope() as s:
        signaler(s, compte_id=None, bien_id=4242, motif="annonce retirée")
    # 3) l'admin VOIT les deux au dashboard, dans la file unique
    d = client.get("/admin/signalements").json()
    assert {x["type"] for x in d["signalements"]} == {"fiche", "annonce"}
    assert d["n_ouverts"] == 2
    annonce = next(x for x in d["signalements"] if x["type"] == "annonce")
    assert annonce["bien_id"] == 4242 and annonce["parcelle_id"] is None
    # 4) l'admin TRAITE un signalement → il quitte la file « à traiter », le compteur baisse
    sid = d["signalements"][0]["id"]
    assert client.post(f"/admin/signalements/{sid}/statut", json={"statut": "traite"}).status_code == 200
    d2 = client.get("/admin/signalements", params={"statut": "nouveau"}).json()
    assert d2["n_ouverts"] == 1 and all(x["statut"] == "nouveau" for x in d2["signalements"])
    # rouvrir est possible (réversible)
    assert client.post(f"/admin/signalements/{sid}/statut", json={"statut": "nouveau"}).status_code == 200
    assert client.get("/admin/signalements").json()["n_ouverts"] == 2


def test_retour_signaler(client, engine):
    """D1 — bouton « Signaler » : le retour s'enregistre statut 'nouveau' ; type invalide → 422."""
    r = client.post("/retours", json={"type": "bug", "message": "L'export CSV est lent."})
    assert r.status_code == 200 and r.json()["ok"] is True
    with engine.begin() as c:
        row = c.execute(text("SELECT type, message, statut FROM retours")).one()
    assert tuple(row) == ("bug", "L'export CSV est lent.", "nouveau")
    assert client.post("/retours", json={"type": "troll", "message": "xxx"}).status_code == 422
    assert client.post("/retours", json={"type": "bug", "message": "x"}).status_code == 422


def test_ia_log_attribue_au_compte(client, engine):
    """D1 — ia_budget : le coût IA est attribué au compte posé par la garde d'auth (ContextVar)."""
    from labuse.ai import core
    from labuse.db import session_scope
    with engine.begin() as c:
        c.execute(text("DELETE FROM ia_log"))
    core.poser_compte(4242)
    try:
        with session_scope() as s:
            core._log_cost(s, kind="test_d1", model=core.MODEL_FACTUAL, stub=False, tin=1000, tout=100)
    finally:
        core.poser_compte(None)
    with engine.begin() as c:
        row = c.execute(text("SELECT compte_id, cout_eur FROM ia_log WHERE kind = 'test_d1'")).one()
    assert row[0] == 4242 and float(row[1]) > 0


def test_stripe_lecture_non_configure(client, monkeypatch):
    """D2 — sans clé restreinte : mode « non configuré » PROPRE (aucun crash, raison servie)."""
    from labuse import config, stripe_lecture
    monkeypatch.delenv("LABUSE_STRIPE_RESTRICTED_KEY", raising=False)
    monkeypatch.delenv("STRIPE_RESTRICTED_KEY", raising=False)
    config.get_settings.cache_clear()
    stripe_lecture.vider_cache()
    r = client.get("/admin/stripe")
    assert r.status_code == 200
    d = r.json()
    assert d["configure"] is False and "restreinte" in d["raison"].lower() or "LABUSE_STRIPE" in d["raison"]


def test_admin_stripe_exige_session_hors_local(client, monkeypatch):
    """D2 — hors mode local, /admin/stripe sans session → 401 (le gate admin est actif)."""
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "sha256:" + "0" * 64)
    from labuse import config
    config.get_settings.cache_clear()
    try:
        assert client.get("/admin/stripe").status_code == 401
    finally:
        config.get_settings.cache_clear()


@pytest.fixture
def compte_test(client, engine):
    """Un compte + utilisateur de test, détruits en fin de test."""
    from labuse.comptes import ensure_tables as comptes_ens
    from labuse.db import session_scope
    with session_scope() as s:
        comptes_ens(s)
    with engine.begin() as c:
        cid = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Client D4', 'integral', 'actif') RETURNING id"
        )).scalar_one()
        c.execute(text(
            "INSERT INTO utilisateurs (compte_id, email, role, statut) "
            "VALUES (:c, 'd4@test.re', 'titulaire', 'actif')"), {"c": cid})
    yield cid
    with engine.begin() as c:
        c.execute(text("DELETE FROM licence_mails WHERE compte_id = :c"), {"c": cid})
        c.execute(text("DELETE FROM utilisateurs WHERE compte_id = :c"), {"c": cid})
        c.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid})


def test_licences_liste_et_suspension(client, engine, compte_test):
    """D4 — la fiche liste le compte ; suspension MANUELLE réversible (données intactes)."""
    d = client.get("/admin/licences").json()
    lic = next((x for x in d["licences"] if x["id"] == compte_test), None)
    assert lic is not None and lic["statut"] == "actif" and lic["email"] == "d4@test.re"
    assert lic["kpi"]["copilote_quota"] == 80        # défaut mandat
    # suspension → statut suspendu, données intactes ; rétablissement → actif
    assert client.post(f"/admin/licences/{compte_test}/suspendre", json={}).json()["statut"] == "suspendu"
    with engine.begin() as c:
        assert c.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": compte_test}).scalar() == "suspendu"
        assert c.execute(text("SELECT COUNT(*) FROM utilisateurs WHERE compte_id = :c"), {"c": compte_test}).scalar() == 1
    assert client.post(f"/admin/licences/{compte_test}/retablir").json()["statut"] == "actif"
    with engine.begin() as c:
        assert c.execute(text("SELECT statut FROM comptes WHERE id = :c"), {"c": compte_test}).scalar() == "actif"


def test_mail_brevo_non_configure_propre(client, compte_test, monkeypatch):
    """D4/MAILS — Brevo absent : bouton répond {envoye:false, raison explicite}, rien de silencieux."""
    monkeypatch.delenv("LABUSE_BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_API_KEY", raising=False)   # REVUE · R7 — repli sans préfixe aussi retiré
    from labuse import config
    config.get_settings.cache_clear()
    r = client.post(f"/admin/licences/{compte_test}/mail", json={"key": "onboarding1"}).json()
    assert r["ok"] is True and r["envoye"] is False and "BREVO_API_KEY" in r["raison"]
    # clé de template inconnue → 422 (contrat)
    assert client.post(f"/admin/licences/{compte_test}/mail", json={"key": "zzz"}).status_code == 422


def test_ia_conso_et_quota_editable(client, engine, compte_test):
    """D5 / CONNEXIONS-2 Lot 2 — /admin/ia sert la conso lue du ledger + le quota par licence est
    ÉDITABLE, RELU à la requête suivante par la fonction UNIQUE `quota_du_compte` (partagée /ia + /ask),
    et le dashboard expose consommé/plafond par compte."""
    from labuse.api.dashboard import quota_du_compte, quota_nl_du_compte
    assert quota_nl_du_compte is quota_du_compte           # l'alias pointe la fonction unifiée
    d = client.get("/admin/ia").json()
    assert d["quota_defaut"] == 80 and "mois" in d and "jours" in d and "par_licence" in d
    ligne = next(k for k in d["quotas"] if k["id"] == compte_test)
    assert "plafond_effectif" in ligne and "consomme_aujourdhui" in ligne   # tuile consommé/plafond
    r = client.post(f"/admin/licences/{compte_test}/quota", json={"quota": 120})
    assert r.status_code == 200
    assert quota_du_compte(compte_test) == 120             # /ia ET /ask liront 120 à la requête suivante
    assert next(k for k in client.get("/admin/ia").json()["quotas"]
                if k["id"] == compte_test)["plafond_effectif"] == 120
    client.post(f"/admin/licences/{compte_test}/quota", json={"quota": None})
    assert quota_du_compte(compte_test) == 80


def test_sources_cadence_et_badge(client, engine):
    """D6 — cadence réglable par source + badge « À mettre à jour » calculé automatiquement."""
    d = client.get("/admin/sources").json()
    # SENTINELLE-1 (W4.2) — la synthèse porte désormais aussi le compte des nouvelles versions + surveillées.
    assert d["sources"] and set(d["synthese"]) == {"a_mettre_a_jour", "ok", "sans_echeance", "nouvelle_version", "surveillees"}
    sid = d["sources"][0]["id"]
    # pose 'mensuelle' → normalisée ; valeur inconnue → 422
    assert client.post(f"/admin/sources/{sid}/cadence", json={"cadence": "mensuel"}).json()["cadence"] == "mensuelle"
    assert client.post(f"/admin/sources/{sid}/cadence", json={"cadence": "lunaire"}).status_code == 422
    with engine.begin() as c:
        from sqlalchemy import text as _t
        # vieillit l'ingestion → le badge doit passer « à mettre à jour » (a_jour false)
        c.execute(_t("UPDATE data_sources SET last_sync_at = now() - interval '90 days' WHERE id = :i"), {"i": sid})
    d2 = client.get("/admin/sources").json()
    s = next(x for x in d2["sources"] if x["id"] == sid)
    assert s["a_jour"] is False and s["cadence"] == "mensuelle"
    # remet la cadence à null (état d'origine : la plupart des sources n'en ont pas encore)
    client.post(f"/admin/sources/{sid}/cadence", json={"cadence": None})


def test_source_relance_sans_commande_404(client, engine):
    """D6 — « Relancer » n'existe QUE si une commande est mappée (sinon 404, bouton absent)."""
    d = client.get("/admin/sources").json()
    sans = next((s for s in d["sources"] if s["relance"] is None), None)
    avec = [s for s in d["sources"] if s["relance"]]
    assert sans is not None
    assert client.post(f"/admin/sources/{sans['id']}/relancer").status_code == 404
    # le mapping YAML couvre bien les crons connus (sitadel/bodacc/dvf/dpe/ban présents en base)
    assert {s["relance"] for s in avec} >= {"bodacc", "dvf", "dpe", "ban"}


def test_produit_usage_et_statut_retour(client, engine):
    """D7 — usage par outil agrégé + statut de retour éditable (nouveau→traité→répondu)."""
    client.post("/usage/event", json={"kind": "outil", "outil": "courrier"})
    rid = client.post("/retours", json={"type": "idee", "message": "Les DPE sur la carte ?"}).json()["id"]
    d = client.get("/admin/produit").json()
    assert any(u["outil"] == "courrier" for u in d["usage"])
    r = next(x for x in d["retours"] if x["id"] == rid)
    assert r["statut"] == "nouveau"
    assert client.post(f"/admin/retours/{rid}/statut", json={"statut": "traite"}).json()["statut"] == "traite"
    assert client.post(f"/admin/retours/{rid}/statut", json={"statut": "zzz"}).status_code == 422


def test_courrier_transitions_journalisees(client, engine, compte_test):
    """D8 / CONNEXIONS-2 Lot 4 (KO-6) — vocabulaire UNIQUE : Demandé → Déposé → Envoyé, transitions
    journalisées (event_log admin + client), statut illégal → 422. Les statuts LEGACY (imprime/poste)
    sont ACCEPTÉS mais NORMALISÉS (imprime→depose)."""
    from labuse import courrier
    courrier.ensure_tables(engine)
    with engine.begin() as c:
        did = c.execute(text(
            "INSERT INTO courrier_demandes (compte_id, parcelles, n, communes, modele, corps, statut)"
            " VALUES (:c, '[\"97415000AB0001\"]'::jsonb, 1, 'Saint-Paul', 'standard', 'Corps de test D8', 'demande')"
            " RETURNING id"), {"c": compte_test}).scalar_one()
    try:
        r = client.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "depose"})
        assert r.status_code == 200 and r.json()["statut"] == "depose"
        # alias legacy encore accepté, normalisé → depose (aucune régression sur d'anciens clients)
        r = client.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "imprime"})
        assert r.status_code == 200 and r.json()["statut"] == "depose"
        r = client.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "envoye"})
        assert r.status_code == 200 and r.json()["statut"] == "envoye"
        assert client.post(f"/courrier/admin/demandes/{did}/statut", json={"statut": "brule"}).status_code == 422
        with engine.begin() as c:
            # journalisée côté admin (compte NULL) ET côté client (compte de la demande)
            n_admin = c.execute(text(
                "SELECT COUNT(*) FROM event_log WHERE dedup LIKE :d"), {"d": f"courrier:statut:{did}:%"}).scalar()
            n_client = c.execute(text(
                "SELECT COUNT(*) FROM event_log WHERE dedup LIKE :d AND compte_id = :c"),
                {"d": f"courrier:statut-client:{did}:%", "c": compte_test}).scalar()
        # 3 clics mais 2 statuts distincts (depose dédupliqué) → 2 traces admin + 2 client
        assert n_admin == 2 and n_client == 2
        # la liste admin porte le nom du client (jointure comptes)
        d = client.get("/courrier/admin/demandes").json()
        row = next(x for x in d["demandes"] if x["id"] == did)
        assert row["client"] == "Client D4" and row["statut"] == "envoye"
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM event_log WHERE dedup LIKE :d"), {"d": f"courrier:statut%:{did}:%"})
            c.execute(text("DELETE FROM courrier_demandes WHERE id = :i"), {"i": did})


def test_essai_expiration_prouvee(client, engine):
    """D9 — CRITÈRE DE FIN : compte d'essai créé, date FORCÉE dans le passé, bascule
    automatique CONSTATÉE (session refusée + statut suspendu), puis compte DÉTRUIT."""
    from labuse import comptes as C
    from labuse.db import session_scope
    r = client.post("/admin/licences/creer-essai",
                    json={"email": "essai-d9@test.re", "nom": "Essai D9", "heures": 48})
    assert r.status_code == 200
    d = r.json()
    cid = d["compte_id"]
    assert d["essai"] is True and d["heures"] == 48 and d["lien"]
    try:
        with engine.begin() as c:
            statut, exp = c.execute(text(
                "SELECT statut, essai_expire_at FROM comptes WHERE id = :c"), {"c": cid}).one()
            uid = c.execute(text(
                "SELECT id FROM utilisateurs WHERE compte_id = :c"), {"c": cid}).scalar_one()
        assert statut == "actif" and exp is not None          # accès complet pendant l'essai
        with session_scope() as s:
            tok = C.creer_session(s, uid)
            assert C.session_utilisateur(s, tok) is not None   # la session vit
        # DATE FORCÉE dans le passé → la prochaine requête bascule le compte
        with engine.begin() as c:
            c.execute(text("UPDATE comptes SET essai_expire_at = now() - interval '1 hour'"
                           " WHERE id = :c"), {"c": cid})
        with session_scope() as s:
            assert C.session_utilisateur(s, tok) is None       # session refusée (bascule)
        with engine.begin() as c:
            assert c.execute(text("SELECT statut FROM comptes WHERE id = :c"),
                             {"c": cid}).scalar() == "suspendu"   # BASCULE CONSTATÉE
            # données intactes (l'utilisateur existe toujours)
            assert c.execute(text("SELECT COUNT(*) FROM utilisateurs WHERE compte_id = :c"),
                             {"c": cid}).scalar() == 1
        # « Convertir en abonnement » : l'échéance tombe, le compte repart au parcours officiel
        assert client.post(f"/admin/licences/{cid}/convertir").status_code == 200
        with engine.begin() as c:
            st, exp2 = c.execute(text(
                "SELECT statut, essai_expire_at FROM comptes WHERE id = :c"), {"c": cid}).one()
        assert exp2 is None and st in ("invite", "suspendu")
    finally:
        with engine.begin() as c:                              # PUIS DÉTRUIT (critère de fin)
            c.execute(text("DELETE FROM utilisateurs WHERE compte_id = :c"), {"c": cid})
            c.execute(text("DELETE FROM evenements_compte WHERE compte_id = :c"), {"c": cid})
            c.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid})


def test_admin_403_depuis_compte_client(engine, monkeypatch):
    """CRITÈRE DE FIN — 403 admin PROUVÉ depuis un compte CLIENT (role titulaire, session
    réelle, auth active) : tout /admin/* refuse ; l'admin (role admin) passe."""
    import uuid
    from labuse import comptes, config
    from labuse.db import session_scope
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-d9")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-d9-0000000000000000000000")
    config.get_settings.cache_clear()
    from labuse.api.app import app
    email = f"client-{uuid.uuid4().hex[:8]}@x.test"
    try:
        with session_scope() as s:
            inv = comptes.creer_invitation(s, email)
            comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-d9-x", "2026-08-27")
            from sqlalchemy import text as _t
            s.execute(_t("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
            uid = s.execute(_t("SELECT id FROM utilisateurs WHERE email=:e"), {"e": email}).scalar()
            tok = comptes.creer_session(s, uid)
            s.commit()
        c = TestClient(app, base_url="https://testserver")
        c.cookies.set("labuse_session", f"u.{tok}")
        # le CLIENT est bien DANS l'app (une route métier passe)…
        assert c.get("/moi").status_code == 200
        # …mais TOUT /admin/* le refuse : 403 (mandat, périmètre et accès)
        for route in ("/admin/pilotage", "/admin/licences", "/admin/ia",
                      "/admin/sources", "/admin/produit", "/admin/stripe"):
            assert c.get(route).status_code == 403, f"{route} devrait refuser un client"
        assert c.post("/admin/degeler", json={"sujet": "x"}).status_code == 403
        # un utilisateur au rôle ADMIN, lui, passe
        with session_scope() as s:
            from sqlalchemy import text as _t
            s.execute(_t("UPDATE utilisateurs SET role='admin' WHERE email=:e"), {"e": email})
            s.commit()
        assert c.get("/admin/pilotage").status_code == 200
    finally:
        config.get_settings.cache_clear()
        with session_scope() as s:
            comptes.supprimer_utilisateur(s, email)


def test_quota_copilote_par_licence(client, engine):
    """D1 — quota Copilote PAR LICENCE : override du compte sinon défaut config (80/jour)."""
    from labuse.api.dashboard import quota_nl_du_compte
    from labuse.comptes import ensure_tables as comptes_ens
    from labuse.db import session_scope
    with session_scope() as s:
        comptes_ens(s)
    with engine.begin() as c:
        cid = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Test D1', 'integral', 'actif') RETURNING id"
        )).scalar_one()
        c.execute(text("UPDATE comptes SET copilote_quota_jour = 5 WHERE id = :c"), {"c": cid})
    try:
        assert quota_nl_du_compte(cid) == 5                       # override licence
        with engine.begin() as c:
            c.execute(text("UPDATE comptes SET copilote_quota_jour = NULL WHERE id = :c"), {"c": cid})
        assert quota_nl_du_compte(cid) == 80                      # défaut config (mandat)
        assert quota_nl_du_compte(None) is None                   # pilote/anonyme → quota historique
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid})
