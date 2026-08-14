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
    db.execute(text("CREATE TABLE IF NOT EXISTS sitadel_permits ("
                    "permit_id varchar(64), commune varchar(64), date_depot date, date date, "
                    "type varchar(8), idu_codes jsonb)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS dvf_mutations_parcelle ("
                    "id_mutation varchar(32), id_parcelle varchar(14), date_mutation date, "
                    "valeur_fonciere numeric, nature_mutation varchar(32))"))
    db.execute(text("CREATE TABLE IF NOT EXISTS parcelle_personne_morale (idu varchar(14), siren varchar(9), denomination text)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS bodacc_procedures (annonce_id varchar(32), siren varchar(9), type_procedure text, date_annonce date)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS parcel_zone_plu (idu varchar(14), zone_lib varchar(64))"))
    events._ensure_cols(db)
    events._ensure_suivi_cols(db)


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
    # M85-B — types du registre ; défaut tout activé. maintenance verrouillée (e-mail toujours on).
    assert p["veille_zone"]["email"] and p["parcelle_suivie"]["cloche"]
    assert p["maintenance"]["verrou"] and p["maintenance"]["email"]
    assert "marche" not in p                                                    # marché n'est plus un type
    events.set_pref(db_session, 55, "veille_zone", cloche=False, email=False)
    p2 = events.prefs_compte(db_session, 55)
    assert not p2["veille_zone"]["cloche"] and not p2["veille_zone"]["email"]   # override


@pytest.mark.db
def test_desabonner_coupe_desactivables_garde_maintenance(db_session):
    _ensure(db_session)
    events.desabonner_email(db_session, 56)
    p = events.prefs_compte(db_session, 56)
    # e-mail coupé sur les DÉSACTIVABLES, mais maintenance reste ON (conséquences réelles) ; cloche intacte.
    assert not p["parcelle_suivie"]["email"] and not p["veille_zone"]["email"]
    assert p["maintenance"]["email"] is True
    assert all(v["cloche"] for v in p.values())


@pytest.mark.db
def test_cloche_filtre_exclut_le_type_coupe_jamais_systeme(db_session):
    _ensure(db_session)
    db_session.execute(text("DELETE FROM event_log"))
    events.creer_notification(db_session, kind="veille", compte_id=None, titre="v1")
    events.creer_notification(db_session, kind="systeme", compte_id=None, titre="s1", source="Ingestion")
    prefs = events.prefs_compte(db_session, None)
    prefs["veille_zone"]["cloche"] = False
    cf = events._cloche_filter_sql(prefs)
    n = db_session.execute(text(
        f"SELECT count(*) FROM event_log e WHERE e.compte_id IS NOT DISTINCT FROM :cid {cf}"),
        {"cid": None, "market": list(events._MARKET_KINDS)}).scalar()
    assert n == 1                                      # veille exclue ; systeme (pilote) jamais exclu


def test_reunion_tz_explicite_utc4():
    assert events.REUNION_TZ.utcoffset(None) == timedelta(hours=4)   # UTC+4, jamais la machine
    assert events.DIGEST_HEURE_REUNION == 7


def test_adresse_placeholder_bloquee():
    """Réputation Brevo : jamais un envoi réel vers une adresse factice (bounce = domaine dégradé)."""
    f = events._adresse_placeholder
    assert f("ton-email@test.com") and f("qa-m23@labuse.test") and f("x@example.com")
    assert f(None) and f("") and f("sans-arobase")
    assert not f("kampusreunion@gmail.com") and not f("bob@labuse.immo")


def test_pref_type_mapping_registre():
    # M85-B — kind → type de registre (source unique)
    assert events._pref_type("veille") == "veille_zone"
    assert events._pref_type("permis") == "parcelle_suivie"
    assert events._pref_type("bascule") == "parcelle_suivie"
    assert events._pref_type("systeme") == "systeme_pilote"


def test_registre_refuse_type_non_declare():
    """M85-B — un type hors registre est REFUSÉ (personne n'ajoute un envoi hors inventaire)."""
    from labuse import notif_registry as R
    assert R.est_declare("parcelle_suivie") and not R.est_declare("bidon")
    assert not R.desactivable("maintenance") and R.desactivable("parcelle_suivie")
    assert R.peut_mail("annonce_produit") and not R.peut_mail("systeme_pilote")


@pytest.mark.db
def test_creer_notification_refuse_hors_registre(db_session):
    """Le garde-fou EN DUR : creer_notification lève sur un type non déclaré."""
    _ensure(db_session)
    with pytest.raises(ValueError):
        events.creer_notification(db_session, kind="campagne_bidon", titre="spam")


def test_annonce_et_maintenance_gabarits():
    """M85-B — annonce désactivable (a une désinscription) ; maintenance NON (aucune désinscription,
    fenêtre de coupure en évidence)."""
    from labuse.emails import annonce_email, maintenance_email
    s, txt = annonce_email("Titre", "Corps.", lien_desabo="/d", lien_prefs="/p")
    assert s == "LABUSE — Titre" and "ne plus recevoir" in txt.lower()              # a une désinscription
    ms, mtxt, mhtml = maintenance_email("Serveur", "Coupure planifiée.", debut="dim 3h", duree="30 min")
    assert "maintenance" in ms.lower() and "coupure" in mtxt.lower()
    assert "pas désactivable" in mtxt.lower() and "ne plus recevoir" not in mtxt.lower()   # jamais de désinscription


@pytest.mark.db
def test_chaine_suivi_parcelle_bout_en_bout(db_session):
    """M85-B — suivre une parcelle → injecter un permis SUR elle → evaluer_suivis → notification
    typée parcelle_suivie. Dédup : la ré-évaluation ne crée pas de doublon."""
    _ensure(db_session)
    idu = "97411000AB0001"
    db_session.execute(text("DELETE FROM event_log WHERE idu=:i"), {"i": idu})
    db_session.execute(text("INSERT INTO watched_parcels (idu, compte_id, created_at) VALUES (:i, NULL, now()-interval '1 day')"), {"i": idu})
    db_session.execute(text("INSERT INTO sitadel_permits (permit_id, type, idu_codes, date_depot) "
                            "VALUES ('PC-X','PC', to_jsonb(ARRAY[:i]), now()::date)"), {"i": idu})
    out = events.evaluer_suivis(db_session)
    assert out["permis"] == 1
    rows = db_session.execute(text("SELECT titre, source, kind FROM event_log WHERE idu=:i AND kind='parcelle_suivie'"),
                              {"i": idu}).mappings().all()
    assert len(rows) == 1 and rows[0]["source"] == "Permis"
    events.evaluer_suivis(db_session)                     # ré-éval → dédup
    n = db_session.execute(text("SELECT count(*) FROM event_log WHERE idu=:i AND kind='parcelle_suivie'"),
                           {"i": idu}).scalar()
    assert n == 1                                         # aucun doublon


@pytest.mark.db
def test_brief_vide_le_dit_honnetement(db_session):
    """Phase 3 — un brief sans veille ni permis ne s'invente RIEN : vide=True + un motif explicite."""
    _ensure(db_session)
    b = events.brief_matin(db_session, 99999)          # compte sans veille ni parcelle suivie
    assert b["vide"] is True and b["cause_vide"]        # honnête : dit pourquoi, ne remplit pas
    assert b["genere_le"].endswith("+04:00")           # 7h Réunion — fuseau UTC+4 explicite


@pytest.mark.db
def test_brief_liste_les_veilles_declenchees(db_session):
    """Phase 3 — DÉTERMINISTE : le brief liste les veilles déclenchées récentes, pas de la prose."""
    _ensure(db_session)
    db_session.execute(text("DELETE FROM event_log WHERE kind='veille'"))
    events.creer_notification(db_session, kind="veille", compte_id=None,
                              titre="Nouveau permis à Saint-Paul", source="Copilote · veille")
    b = events.brief_matin(db_session, None)
    assert not b["vide"] and len(b["veilles"]) == 1
    assert b["veilles"][0]["titre"] == "Nouveau permis à Saint-Paul"


def test_zero_modele_dans_le_module_veilles():
    """Garde-fou doctrine : le module de la chaîne n'appelle aucun modèle (anthropic/openai/llm)."""
    from pathlib import Path
    src = Path(veilles.__file__).read_text(encoding="utf-8").lower()
    for interdit in ("anthropic", "openai", "import llm", "call_model", "chat.completions"):
        assert interdit not in src, f"appel modèle interdit dans la chaîne : {interdit}"
