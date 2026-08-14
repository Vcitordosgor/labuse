"""M85 — le centre de notifications unifié (event_log). Producteur UNIQUE : dédup, plafond dur,
regroupement. Chaînes veille→cloche et ingestion(systeme)→cloche testées de bout en bout. ZÉRO
appel modèle dans la chaîne (du SQL + des gabarits). Un bug de producteur (400 faits) → 1 notif."""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text

from labuse.api import events
from labuse.copilote_v2 import veilles


def _ensure(db):
    """Tables + colonnes M85 dans la base de test (idempotent, transactionnel)."""
    for stmt in events.DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))
    db.execute(text(veilles.DDL))
    db.execute(text("CREATE TABLE IF NOT EXISTS m10_permit_delais ("
                    "permit_id varchar(64), commune varchar(64), nature varchar(64), "
                    "date_depot date)"))
    events._ensure_cols(db)


@pytest.mark.db
def test_dedup_meme_cle_meme_jour(db_session):
    _ensure(db_session)
    a = events.creer_notification(db_session, kind="systeme", titre="x", dedup="cle:1")
    b = events.creer_notification(db_session, kind="systeme", titre="x", dedup="cle:1")
    assert a > 0 and b == 0                       # même clé, même jour → une seule ligne


@pytest.mark.db
def test_plafond_dur_par_kind_compte_jour(db_session):
    _ensure(db_session)
    crees = sum(1 for i in range(events.NOTIF_CAP_JOUR + 25)
                if events.creer_notification(db_session, kind="veille", compte_id=None, titre=f"n{i}"))
    assert crees == events.NOTIF_CAP_JOUR         # le plafond borne un producteur en boucle


@pytest.mark.db
def test_chaine_veille_vers_cloche_et_regroupement(db_session):
    """Le test du bug qui génère 400 : 400 faits le même jour → UNE notification à N entrées."""
    _ensure(db_session)
    db_session.execute(text("DELETE FROM event_log WHERE kind='veille'"))   # base de test propre
    vid = veilles.creer(db_session, compte_id=None, type_="permis", commune="Test-Ville")["id"]
    assert vid
    db_session.execute(text("DELETE FROM m10_permit_delais WHERE commune='Test-Ville'"))
    for i in range(400):
        db_session.execute(text(
            "INSERT INTO m10_permit_delais (permit_id, commune, date_depot) "
            "VALUES (:p, 'Test-Ville', now()::date)"), {"p": f"PC-{i:04d}"})
    out = veilles.evaluer_toutes(db_session)
    # _nouveaux_permis borne à 100 (LIMIT) : 400 injectés → 100 récupérés — mais l'invariant qui
    # compte est le REGROUPEMENT : quel que soit N, UNE seule notification (jamais N).
    assert out["notifications_creees"] == 100
    rows = db_session.execute(text(
        "SELECT titre, detail, source, kind FROM event_log WHERE kind='veille'")).mappings().all()
    assert len(rows) == 1                         # ...mais UNE notification (regroupement)
    assert "100" in rows[0]["titre"] and rows[0]["source"] == "Copilote · veille"
    # rejeu du MÊME lot → dédup par contenu : aucune notif de plus (idempotent)
    db_session.execute(text("UPDATE veilles SET last_evaluated_at=NULL WHERE id=:i"), {"i": vid})
    veilles.evaluer_toutes(db_session)
    again = db_session.execute(text("SELECT count(*) FROM event_log WHERE kind='veille'")).scalar()
    assert again == 1                             # même contenu → pas de doublon


@pytest.mark.db
def test_producteur_systeme_dit_sa_source_et_son_lien(db_session):
    """La notif d'ingestion (systeme) porte source + lien /sources, et reste PILOTE (compte NULL)."""
    _ensure(db_session)
    nid = events.creer_notification(
        db_session, kind="systeme", compte_id=None, source="Ingestion · dpe",
        titre="Source en retard : DPE", lien="/sources", dedup="fraicheur:dpe:test")
    row = db_session.execute(text(
        "SELECT kind, source, lien, compte_id FROM event_log WHERE id=:i"), {"i": nid}).mappings().first()
    assert row["kind"] == "systeme" and row["source"] == "Ingestion · dpe"
    assert row["lien"] == "/sources" and row["compte_id"] is None   # tuyauterie = pilote, pas client


@pytest.mark.db
def test_prefs_defauts_et_override(db_session):
    _ensure(db_session)
    p = events.prefs_compte(db_session, None)
    assert p["veille"]["email"] and p["suivi"]["cloche"] and not p["marche"]["email"]   # défauts
    events.set_pref(db_session, 55, "veille", cloche=False, email=False)
    p2 = events.prefs_compte(db_session, 55)
    assert not p2["veille"]["cloche"] and not p2["veille"]["email"]                       # override


@pytest.mark.db
def test_desabonner_coupe_email_garde_cloche(db_session):
    _ensure(db_session)
    events.desabonner_email(db_session, 56)
    p = events.prefs_compte(db_session, 56)
    assert all(not v["email"] for v in p.values())    # e-mail coupé partout (désinscription globale)
    assert all(v["cloche"] for v in p.values())        # la cloche reste (défaut intact)


@pytest.mark.db
def test_cloche_filtre_exclut_le_type_coupe_jamais_systeme(db_session):
    _ensure(db_session)
    db_session.execute(text("DELETE FROM event_log"))
    events.creer_notification(db_session, kind="veille", compte_id=None, titre="v1")
    events.creer_notification(db_session, kind="systeme", compte_id=None, titre="s1", source="Ingestion")
    prefs = events.prefs_compte(db_session, None)
    prefs["veille"]["cloche"] = False
    cf = events._cloche_filter_sql(prefs)
    n = db_session.execute(text(
        f"SELECT count(*) FROM event_log e WHERE e.compte_id IS NOT DISTINCT FROM :cid {cf}"),
        {"cid": None, "market": list(events._MARKET_KINDS)}).scalar()
    assert n == 1                                      # veille exclue ; systeme (pilote) jamais exclu


def test_reunion_tz_explicite_utc4():
    assert events.REUNION_TZ.utcoffset(None) == timedelta(hours=4)   # UTC+4, jamais la machine
    assert events.DIGEST_HEURE_REUNION == 7


def test_pref_type_mapping():
    assert events._pref_type("veille", False) == "veille"
    assert events._pref_type("permis", False) == "suivi"
    assert events._pref_type("bascule", True) == "marche"
    assert events._pref_type("systeme", False) is None    # tuyauterie ingestion : hors pref client


def test_zero_modele_dans_le_module_veilles():
    """Garde-fou doctrine : le module de la chaîne n'appelle aucun modèle (anthropic/openai/llm)."""
    from pathlib import Path
    src = Path(veilles.__file__).read_text(encoding="utf-8").lower()
    for interdit in ("anthropic", "openai", "import llm", "call_model", "chat.completions"):
        assert interdit not in src, f"appel modèle interdit dans la chaîne : {interdit}"
