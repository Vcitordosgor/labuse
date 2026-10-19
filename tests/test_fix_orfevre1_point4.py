"""FIX-ORFEVRE-1 · point 4 — gênants restants (ORF-05/07/08/09/10/14/15/16/21).

Chaque test grave UNE racine corrigée :
  · ORF-05 — parts CoSIA = de vraies PARTS (dénominateur max(surface, Σ CoSIA), jamais > 100 %) ;
  · ORF-07 — le worker mail ANNULE (motif dit) les lignes d'un compte supprimé / dues trop vieilles ;
  · ORF-08 — revendication `parti` : deux consommateurs concurrents = UN SEUL envoi ; reprise des
    `parti` orphelins ;
  · ORF-09 — dépôt Radar idempotent (hash unique) + journal dédupliqué EN BASE (dedup + jour) ;
  · ORF-10 — un sous-process d'ingestion qui dépasse son budget est TUÉ (groupe), jamais orphelin ;
  · ORF-14 — une piscine sans parcelle (idu NULL) n'est JAMAIS servie (carte, liste, compteurs) ;
  · ORF-15 — délai négatif (même au jour près, delai_mois = 0) ⇒ valide = false, toujours ;
  · ORF-16 — score_labuse_runs.n_parcelles = cumul RÉEL du run, pas la taille du dernier lot ;
  · ORF-21 — /moi/prefs-carte en mode local : 200 prefs vides / no-op, plus jamais un 401 par écran.
"""
from __future__ import annotations

import time
import uuid
from datetime import date

import pytest
from sqlalchemy import text

# Marque `db` posée PAR TEST (pas au module) : les tests purs (ORF-10/15/21) tournent aussi dans le
# filet pre-push (famille « unitaires sans base »).
dbtest = pytest.mark.db


# ───────────────────────── ORF-05 — parts CoSIA bornées par construction ─────────────────────────

def _seed_cosia(db, idu: str, rows: list[tuple[str, float]]) -> None:
    from labuse.ingestion.cosia_couverture import ensure_table
    ensure_table(db)
    db.execute(text("DELETE FROM parcel_cosia_couverture WHERE idu = :i"), {"i": idu})
    for classe, m2 in rows:
        db.execute(text("INSERT INTO parcel_cosia_couverture (idu, classe, m2, source_millesime)"
                        " VALUES (:i, :c, :m, 'test')"), {"i": idu, "c": classe, "m": m2})


@dbtest
def test_orf05_cosia_deborde_parts_saturees_mais_bornees(db_session):
    """Le raster CoSIA déborde le dessin (389 m² mesurés / 154 m² cadastrés, cas réel 97420000BH1222) :
    les parts restent des PARTS (≤ 100, somme ≤ 100) et le débordement est DIT."""
    from labuse.bati import _cosia_couverture
    idu = "97400TESTC001"
    _seed_cosia(db_session, idu, [("Bâtiment", 300.0), ("Pelouse", 60.0), ("Sol nu", 29.0)])
    out = _cosia_couverture(db_session, idu, 154.0)
    assert out is not None
    assert out["mesure_saturee"] is True
    assert "saturé" in out["source"]
    parts = [out["part_impermeabilisee_pct"], out["part_vegetalisee_boisee_pct"], out["part_sol_nu_pct"]]
    assert all(0 <= p <= 100 for p in parts), parts
    assert sum(parts) <= 100.2   # arrondis 0,1 près
    # l'imperméabilisé domine toujours (l'ordre des parts est préservé par le nouveau dénominateur)
    assert out["part_impermeabilisee_pct"] > out["part_vegetalisee_boisee_pct"]


@dbtest
def test_orf05_cosia_normal_inchange(db_session):
    """Cas sain (Σ CoSIA ≤ surface) : dénominateur = surface cadastrale, valeurs identiques à avant."""
    from labuse.bati import _cosia_couverture
    idu = "97400TESTC002"
    _seed_cosia(db_session, idu, [("Bâtiment", 50.0), ("Pelouse", 30.0)])
    out = _cosia_couverture(db_session, idu, 200.0)
    assert out["part_impermeabilisee_pct"] == 25.0
    assert out["part_vegetalisee_boisee_pct"] == 15.0
    assert out["mesure_saturee"] is False


# ───────────────────── ORF-07 — gardes du worker (compte supprimé, dû trop vieux) ─────────────────

@pytest.fixture()
def eng_mail(engine):
    from labuse import mailfile
    mailfile.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM mail_queue"))
    return engine


@dbtest
def test_orf07_compte_supprime_et_du_trop_vieux_annules(eng_mail, monkeypatch):
    from labuse import mailfile
    appels = []
    monkeypatch.setattr("labuse.mail.envoyer_template",
                        lambda *a, **k: appels.append(a) or {"envoye": True, "message_id": "x"})
    with eng_mail.begin() as c:
        # compte inexistant (999999 — la table comptes du schéma de test ne le porte pas), dû maintenant
        c.execute(text(
            "INSERT INTO mail_queue (compte_id, mail_key, destinataire, params, etat, prevu_at)"
            " VALUES (999999, 'retablissement', 'orphelin@labuse.test', '{}', 'a_rejouer', now())"))
        # dû depuis 9 jours (résidu de recette) — compte NULL pour isoler la garde de fraîcheur
        c.execute(text(
            "INSERT INTO mail_queue (compte_id, mail_key, destinataire, params, etat, prevu_at, cree_at)"
            " VALUES (NULL, 'retablissement', 'vieux@labuse.test', '{}', 'a_rejouer',"
            " now() - interval '9 days', now() - interval '9 days')"))
    r = mailfile.consommer(eng_mail)
    assert r["annules"] == 2 and r["envoyes"] == 0 and appels == []
    with eng_mail.begin() as c:
        rows = c.execute(text("SELECT etat, erreur FROM mail_queue ORDER BY id")).all()
    assert all(e == "annule" for e, _ in rows)
    assert any("compte supprimé" in (err or "") for _, err in rows)
    assert any("dû depuis plus de" in (err or "") for _, err in rows)


# ─────────────── ORF-08 — revendication `parti` : 2 consommateurs = 1 envoi · reprise ───────────────

@dbtest
def test_orf08_deux_consommateurs_un_seul_envoi(eng_mail, monkeypatch):
    """Course worker ↔ « rejouer » admin, rejouée DÉTERMINISTIQUEMENT : le second consommateur entre
    PENDANT l'appel transport du premier (la revendication `parti` est déjà committée) → il ressort
    sans envoyer. Avant le fix, le client recevait le mail DEUX fois."""
    from labuse import mailfile
    envois = []
    resultats_concurrents = []

    with eng_mail.begin() as c:
        mid = c.execute(text(
            "INSERT INTO mail_queue (compte_id, mail_key, destinataire, params, etat)"
            " VALUES (NULL, 'retablissement', 'double@labuse.test',"
            " '{\"PRENOM\": \"Vic\"}', 'en_attente') RETURNING id")).scalar()

    def _transport(to, key, params):
        # LE SECOND CONSOMMATEUR frappe ici, en plein envoi du premier.
        resultats_concurrents.append(mailfile._tenter_depart(eng_mail, mid))
        envois.append(to)
        return {"envoye": True, "message_id": "<brevo-unique@labuse>"}

    monkeypatch.setattr("labuse.mail.envoyer_template", _transport)
    r = mailfile._tenter_depart(eng_mail, mid)
    assert r["etat"] == "recu"
    assert envois == ["double@labuse.test"], "le transport doit être appelé UNE seule fois"
    # le concurrent a vu l'entrée revendiquée (`parti`) et n'a PAS envoyé
    assert resultats_concurrents[0]["etat"] == "parti"


@dbtest
def test_orf08_reprise_des_parti_orphelins(eng_mail, monkeypatch):
    """Un `parti` vieux (processus tué pendant l'envoi) est repris par le worker → renvoyé."""
    from labuse import mailfile
    monkeypatch.setattr("labuse.mail.envoyer_template",
                        lambda *a, **k: {"envoye": True, "message_id": "<reprise@labuse>"})
    with eng_mail.begin() as c:
        mid = c.execute(text(
            "INSERT INTO mail_queue (compte_id, mail_key, destinataire, params, etat, parti_at)"
            " VALUES (NULL, 'retablissement', 'repris@labuse.test',"
            " '{\"PRENOM\": \"Vic\"}', 'parti', now() - interval '20 minutes') RETURNING id")).scalar()
    r = mailfile.consommer(eng_mail)
    assert r["repris"] == 1
    with eng_mail.begin() as c:
        assert c.execute(text("SELECT etat FROM mail_queue WHERE id=:i"), {"i": mid}).scalar() == "recu"


# ───────────── ORF-09 — dépôt Radar idempotent : hash unique + journal dédupliqué en base ──────────

@dbtest
def test_orf09_journaliser_dedup_tenu_par_la_base(db_session):
    from labuse.pige import tables as pg
    dedup = f"pige:depot:test-{uuid.uuid4().hex[:12]}"
    eid1 = pg.journaliser(db_session, pg.EV_DEPOT_HTML, "[ORF-09] dépôt", dedup=dedup)
    eid2 = pg.journaliser(db_session, pg.EV_DEPOT_HTML, "[ORF-09] dépôt (rejeu)", dedup=dedup)
    assert eid1 > 0 and eid2 == 0, "le rejeu du même événement le même jour doit être un no-op"
    n = db_session.execute(text("SELECT count(*) FROM event_log WHERE dedup = :d"), {"d": dedup}).scalar()
    assert n == 1
    db_session.execute(text("DELETE FROM event_log WHERE dedup = :d"), {"d": dedup})
    db_session.commit()


@dbtest
def test_orf09_pige_depots_hash_unique(db_session):
    h = uuid.uuid4().hex * 2   # 64 hexa, comme un sha256
    ins = text("INSERT INTO pige_depots (nom_fichier, hash, chemin_archive, nb_annonces)"
               " VALUES ('t.html', :h, '/tmp/t', 1)"
               " ON CONFLICT (hash) WHERE hash <> '' DO NOTHING RETURNING id")
    id1 = db_session.execute(ins, {"h": h}).scalar()
    id2 = db_session.execute(ins, {"h": h}).scalar()
    assert id1 is not None and id2 is None, "le même fichier (hash) ne crée jamais un 2e dépôt"
    n = db_session.execute(text("SELECT count(*) FROM pige_depots WHERE hash = :h"), {"h": h}).scalar()
    assert n == 1
    db_session.execute(text("DELETE FROM pige_depots WHERE hash = :h"), {"h": h})
    db_session.commit()


# ──────────────── ORF-10 — sous-process borné : le dormeur est TUÉ, jamais orphelin ────────────────

def test_orf10_sous_process_dormeur_tue():
    import os
    import sys

    from labuse.jobs_impl import SousProcessTimeout, _run_sous_process_borne
    t0 = time.monotonic()
    with pytest.raises(SousProcessTimeout) as exc:
        _run_sous_process_borne([sys.executable, "-c", "import time; time.sleep(60)"], budget_s=1.0)
    assert time.monotonic() - t0 < 10, "le kill doit frapper au budget, pas à la fin du sleep"
    with pytest.raises(ProcessLookupError):
        os.kill(exc.value.pid, 0)   # le process n'existe plus (tué ET récolté)


def test_orf10_sous_process_sain_passe():
    import sys

    from labuse.jobs_impl import _run_sous_process_borne
    proc = _run_sous_process_borne([sys.executable, "-c", "print('ok')"], budget_s=30.0)
    assert proc.returncode == 0 and "ok" in proc.stdout


# ─────────────── ORF-14 — une piscine sans parcelle (idu NULL) n'est jamais servie ────────────────

@dbtest
def test_orf14_piscine_sans_idu_exclue_des_lecteurs(db_session):
    from labuse.api.modules import prospection_piscines_points
    from labuse.ingestion.piscines_fusion import ensure as ensure_piscines
    from labuse.registre.moteurs.commune import compte_piscines
    ensure_piscines(db_session)
    marker = 777001.5   # surface improbable = marqueur du test
    db_session.execute(text("DELETE FROM piscines WHERE surface_m2 = :m"), {"m": marker})
    db_session.execute(text(
        "INSERT INTO piscines (idu, commune, surface_m2, source, classe, statut, geom, geom_2975)"
        " VALUES (NULL, NULL, :m, 'cosia', 'cosia_confirmee', 'servie',"
        "         ST_SetSRID(ST_Point(55.45, -20.9), 4326),"
        "         ST_Transform(ST_SetSRID(ST_Point(55.45, -20.9), 4326), 2975))"), {"m": marker})
    db_session.commit()
    try:
        # carte : aucun point sans idu (le marqueur n'apparaît pas)
        fc = prospection_piscines_points(db=db_session)
        assert all(f["properties"]["idu"] is not None for f in fc["features"])
        assert all(f["properties"]["piscine_m2"] != marker for f in fc["features"])
        # compteur du bandeau : avec un idu la ligne compte, sans idu elle ne compte plus
        total_sans = compte_piscines(db_session, None, "tous", 0, True)["total"]
        db_session.execute(text("UPDATE piscines SET idu = '97400ORF14X001', commune = 'TestVille'"
                                " WHERE surface_m2 = :m"), {"m": marker})
        db_session.commit()
        total_avec = compte_piscines(db_session, None, "tous", 0, True)["total"]
        assert total_avec == total_sans + 1, "la même détection compte avec idu, jamais sans"
    finally:
        db_session.execute(text("DELETE FROM piscines WHERE surface_m2 = :m"), {"m": marker})
        db_session.commit()


# ───────────────── ORF-15 — délai négatif (même au jour près) ⇒ valide = false ────────────────────

def test_orf15_validite_couvre_la_causalite_au_jour():
    from labuse.ingestion.permit_delais_m10 import _months, _valide
    dep, aut = date(2016, 8, 24), date(2016, 8, 3)       # cas réel Entre-Deux : delai_mois = 0
    assert _months(dep, aut) == 0
    assert _valide(dep, aut, _months(dep, aut)) is False   # l'ancien `delai >= 0` disait true
    assert _valide(date(2016, 8, 3), date(2016, 8, 24), 0) is True
    assert _valide(date(2012, 1, 1), date(2013, 2, 22), 13) is True
    assert _valide(date(2026, 3, 2), date(2013, 2, 22), -157) is False
    assert _valide(None, date(2013, 2, 22), None) is False


# ───────────── ORF-16 — n_parcelles du run = cumul réel, pas la taille du dernier lot ─────────────

@dbtest
def test_orf16_n_parcelles_cumule_sur_les_lots(db_session):
    from labuse.scoring.score_labuse_combine import LigneScoreLabuse, ensure_schema, persister
    ensure_schema(db_session)
    run = f"test_orf16_{uuid.uuid4().hex[:8]}"
    pids = []
    for k in range(3):
        pid = db_session.execute(text(
            "INSERT INTO parcels (idu, commune, geom) VALUES (:i, 'TestVille',"
            " ST_SetSRID(ST_GeomFromText('POLYGON((55 -21,55.0001 -21,55.0001 -20.9999,55 -21))'), 4326))"
            " RETURNING id"), {"i": f"97400ORF16{k:04d}"}).scalar()
        pids.append(pid)

    def _l(pid, idu):
        return LigneScoreLabuse(run, pid, idu, "TestVille", 50, "C", False, None, 100, [],
                                "haute", [], [], "test", None, None, None, False, [], 10)

    try:
        # deux LOTS (persister par chunks, comme le run réel) : 2 puis 1
        persister(db_session, run, [_l(pids[0], "A"), _l(pids[1], "B")],
                  cascade_label="t", signal_run_id=None, communes=None)
        persister(db_session, run, [_l(pids[2], "C")],
                  cascade_label="t", signal_run_id=None, communes=None)
        meta = db_session.execute(text(
            "SELECT n_parcelles FROM score_labuse_runs WHERE run_label = :r"), {"r": run}).scalar()
        assert meta == 3, f"métadonnée {meta} ≠ cumul réel 3 (l'ancien code écrivait 1 = dernier lot)"
    finally:
        db_session.execute(text("DELETE FROM score_labuse WHERE run_label = :r"), {"r": run})
        db_session.execute(text("DELETE FROM score_labuse_runs WHERE run_label = :r"), {"r": run})
        db_session.execute(text("DELETE FROM parcels WHERE id = ANY(:p)"), {"p": pids})
        db_session.commit()


# ───────────── ORF-21 — /moi/prefs-carte : mode local = 200 (prefs vides / no-op), pas 401 ─────────

def _req(cookies: dict | None = None):
    from starlette.requests import Request
    headers = []
    if cookies:
        headers = [(b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode())]
    return Request({"type": "http", "method": "GET", "headers": headers, "query_string": b"",
                    "path": "/moi/prefs-carte"})


def test_orf21_prefs_carte_mode_local_200():
    from labuse.api.onboarding import moi_prefs_carte_get, moi_prefs_carte_set
    out = moi_prefs_carte_get(_req(), db=None)           # aucun cookie = mode local (comme /moi)
    assert out == {"basemap": None, "couches": None, "mode": "local"}
    out = moi_prefs_carte_set({"basemap": "ortho"}, _req(), db=None)
    assert out == {"ok": True, "mode": "local"}


def test_orf21_prefs_carte_session_invalide_401():
    from fastapi import HTTPException

    from labuse.api.auth import COOKIE
    from labuse.api.onboarding import moi_prefs_carte_get
    with pytest.raises(HTTPException) as exc:
        moi_prefs_carte_get(_req({COOKIE: "u.jeton-expire"}), db=None)
    assert exc.value.status_code == 401
