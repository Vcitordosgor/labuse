"""Tests Lot 2B (wave-adresses) : courrier — stub, responsabilité, plafond, tarif."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config, courrier
    from labuse.api.app import app
    courrier.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM courrier_envois"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_statut_stub_sans_compte(client):
    """Sans compte prestataire : disponible=false — le front N'AFFICHE PAS le bouton."""
    r = client.get("/courrier/statut").json()
    assert r["disponible"] is False and r["provider"] == "stub"
    # M82 #fuite : la raison est SERVIE au client — jamais le prestataire ni les variables d'env.
    assert r["raison"] and "Merci Facteur" not in r["raison"] and "MERCIFACTEUR" not in r["raison"]
    assert "envoi postal" in r["raison"].lower()
    # tarif = coût prestataire × marge (défauts : 2,69 × 1,5)
    assert r["tarif"]["prix_client_eur"] == round(2.69 * 1.5, 2)


def test_envoi_exige_responsabilite(client):
    r = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": False})
    assert r.status_code == 422 and "responsabilité" in r.json()["detail"]


def test_envoi_stub_et_plafond(client, monkeypatch, engine):
    monkeypatch.setenv("LABUSE_COURRIER_MAX_JOUR", "2")
    from labuse import config
    config.get_settings.cache_clear()

    r = client.post("/courrier/envois", json={
        "destinataires": [
            {"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"},
            {"idu": "97416000AA0002", "adresse": "14 Rue X, 97410 Saint-Pierre"}],
        "modele": "renovation", "assume_contenu": True})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "stub"
    assert all(e["statut"] == "simule" for e in body["envois"])   # RIEN ne part en stub
    assert body["total_eur"] == round(2 * body["prix_unitaire_eur"], 2)

    # plafond/jour atteint → refus
    r2 = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0003", "adresse": "16 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": True})
    assert r2.status_code == 422 and "Plafond" in r2.json()["detail"]

    # suivi
    suivi = client.get("/courrier/envois").json()
    assert suivi["n"] == 2 and suivi["envois"][0]["modele"] == "renovation"

def test_courrier_pdf_ne_leve_pas_sur_les_3_modeles(client):
    """Patron test_m136_exports_ne_crashent_pas : POST /courrier/pdf rend un PDF VALIDE (jamais de
    FPDFException) sur les 3 modèles réels ; contenu fidèle au texte affiché (ponctuation → pas de
    « ? », lignes vides des \\n\\n gérées). Le bug d'origine : multi_cell(w=0) sur une ligne vide."""
    import io
    from labuse.api.modules import _COURRIER
    pypdf = pytest.importorskip("pypdf")
    assert set(_COURRIER) == {"standard", "indivision", "succession"}   # les 3, pas un seul
    for motif, tpl in _COURRIER.items():
        texte = tpl.format(ref="BV 912", commune="Saint-Paul", surface=3948,
                           signature="LABUSE — prospection foncière")
        r = client.post("/courrier/pdf", json={"idu": "97415000BV0912", "motif": motif, "texte": texte})
        assert r.status_code == 200, f"{motif}: HTTP {r.status_code}"
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-", f"{motif}: pas un PDF"
        txt = "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(io.BytesIO(r.content)).pages).replace("\n", " ")
        assert "Saint-Paul" in txt and "BV 912" in txt, f"{motif}: contenu absent du PDF"
        assert "?" not in txt, f"{motif}: ponctuation dégradée en « ? »"


# ── FIX-GB-013 — idempotence de POST /courrier/demande (dédup douce + ceinture concurrence) ──

def test_gb013_demande_idempotente_sequentielle(engine):
    """Deux demandes IDENTIQUES rapprochées → une seule ligne ; la 2ᵉ renvoie l'existante."""
    from labuse import courrier
    courrier.ensure_tables(engine)
    corps = "[test] gb013 seq idempotence"
    with engine.begin() as c:
        c.execute(text("DELETE FROM courrier_demandes WHERE corps = :c"), {"c": corps})
    args = dict(compte_id=None, parcelles=["97411000BZ1065", "97411000BZ1066"],
                communes="X", modele="libre", corps=corps)
    with engine.begin() as c1:
        d1 = courrier.creer_demande(c1, **args)
    with engine.begin() as c2:
        d2 = courrier.creer_demande(c2, **args)
    assert d1["existing"] is False
    assert d2["existing"] is True and d2["id"] == d1["id"]
    with engine.connect() as c:
        n = c.execute(text("SELECT count(*) FROM courrier_demandes WHERE corps = :c"), {"c": corps}).scalar()
    assert n == 1, f"attendu 1 ligne, eu {n}"


def test_gb013_demande_idempotente_concurrente(engine):
    """Le vrai test du mandat : deux créations VRAIMENT concurrentes (threads, connexions séparées) →
    une seule ligne (le verrou consultatif transactionnel sérialise les identiques)."""
    import threading
    from sqlalchemy.orm import sessionmaker
    from labuse import courrier
    courrier.ensure_tables(engine)
    corps = "[test] gb013 concurrent idempotence"
    with engine.begin() as c:
        c.execute(text("DELETE FROM courrier_demandes WHERE corps = :c"), {"c": corps})
    SM = sessionmaker(bind=engine)
    args = dict(compte_id=None, parcelles=["97411000BZ1065"], communes="X", modele="libre", corps=corps)
    out: list = []
    barriere = threading.Barrier(2)

    def worker():
        s = SM()
        try:
            barriere.wait()                         # démarrage simultané
            d = courrier.creer_demande(s, **args)
            s.commit()                              # libère le verrou xact (comme le handler)
            out.append(d)
        finally:
            s.close()

    ts = [threading.Thread(target=worker) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    with engine.connect() as c:
        n = c.execute(text("SELECT count(*) FROM courrier_demandes WHERE corps = :c"), {"c": corps}).scalar()
    assert n == 1, f"double POST concurrent : attendu 1 ligne, eu {n}"
    assert sum(1 for d in out if not d.get("existing")) == 1
    assert sum(1 for d in out if d.get("existing")) == 1


# ─────────────────────── COURRIER-2 Lot 1 — OPPOSITION (stop@labuse.immo) ───────────────────────
def test_opposition_bloque_le_depot_tous_comptes(client, engine):
    """Une opposition (par IDU) bloque le DÉPÔT d'un pli vers cette parcelle, POUR TOUS LES COMPTES.
    Preuve : deux comptes distincts préparent un pli sur la même parcelle ; après opposition, aucun
    des deux ne peut être déposé (garde globale, sans scope compte)."""
    from labuse import courrier
    idu = "97411000BZ1065"
    with engine.begin() as db:
        db.execute(text("DELETE FROM courrier_opposition"))
        db.execute(text("DELETE FROM courrier_demandes WHERE corps IN ('cA-opp','cB-opp')"))
        cA = db.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('OppA','integral','actif') RETURNING id")).scalar()
        cB = db.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('OppB','integral','actif') RETURNING id")).scalar()
        dA = courrier.creer_demande(db, compte_id=cA, parcelles=[idu], communes="Saint-Denis ×1",
                                    modele="B", corps="cA-opp")
        dB = courrier.creer_demande(db, compte_id=cB, parcelles=[idu], communes="Saint-Denis ×1",
                                    modele="B", corps="cB-opp")
    # avant opposition : le dépôt fonctionne (compte A)
    with engine.begin() as db:
        assert courrier.set_statut_demande(db, dA["id"], "depose")["statut"] == "depose"
    # Vic enregistre l'opposition (par IDU) — globale
    with engine.begin() as db:
        opp = courrier.ajouter_opposition(db, adresse=None, idu=idu, reference="BZ 1065", par="test")
        assert opp["idu"] == idu
    # dépôt du compte B (AUTRE compte) refusé avec le motif unique
    with engine.begin() as db:
        with pytest.raises(ValueError, match=courrier.MOTIF_OPPOSITION):
            courrier.set_statut_demande(db, dB["id"], "depose")
    # même refus au travers de l'API admin (422, motif servi)
    r = client.post(f"/courrier/admin/demandes/{dB['id']}/statut", json={"statut": "depose"})
    assert r.status_code == 422 and courrier.MOTIF_OPPOSITION in r.json()["detail"]
    # le registre est lisible au dashboard
    assert any(o["idu"] == idu for o in client.get("/courrier/admin/oppositions").json()["oppositions"])
    with engine.begin() as db:
        db.execute(text("DELETE FROM courrier_opposition"))
        db.execute(text("DELETE FROM courrier_demandes WHERE corps IN ('cA-opp','cB-opp')"))


def test_opposition_deposer_tout_exclut_les_opposees(client, engine):
    """« Marquer les N déposés » n'emporte JAMAIS une demande opposée : elle reste à déposer et est
    comptée comme bloquée."""
    from labuse import courrier
    idu_opp, idu_ok = "97411000BZ1065", "97411000BZ9999"
    with engine.begin() as db:
        db.execute(text("DELETE FROM courrier_opposition"))
        db.execute(text("DELETE FROM courrier_demandes WHERE corps IN ('dt-opp','dt-ok')"))
        cid = db.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('OppDT','integral','actif') RETURNING id")).scalar()
        d_opp = courrier.creer_demande(db, compte_id=cid, parcelles=[idu_opp], communes="SD",
                                       modele="B", corps="dt-opp")
        d_ok = courrier.creer_demande(db, compte_id=cid, parcelles=[idu_ok], communes="SD",
                                      modele="B", corps="dt-ok")
        courrier.ajouter_opposition(db, adresse=None, idu=idu_opp, reference=None, par="test")
    with engine.begin() as db:
        touchees = courrier.marquer_deposes(db)
        assert d_ok["id"] in [t["id"] for t in touchees]
        assert d_opp["id"] not in [t["id"] for t in touchees]
    with engine.begin() as db:
        assert courrier.bloquees_a_deposer(db) >= 1
        assert db.execute(text("SELECT statut FROM courrier_demandes WHERE id=:i"),
                          {"i": d_opp["id"]}).scalar() == "demande"
        db.execute(text("DELETE FROM courrier_opposition"))
        db.execute(text("DELETE FROM courrier_demandes WHERE corps IN ('dt-opp','dt-ok')"))


# ─────────────────────── COURRIER-2 Lot 2 — ADRESSAGE (occupant / siège / bloqué) ───────────────────────
def _ensure_adressage_tables(db):
    """labuse_test n'a qu'un schéma partiel : on crée (IF NOT EXISTS) les tables lues par le
    résolveur d'adressage, avec le minimum de colonnes utilisées. No-op si déjà présentes."""
    db.execute(text("CREATE TABLE IF NOT EXISTS parcel_filtre_bati (parcel_id int, idu varchar(14), "
                    "ratio_pct double precision, emprise_max_m2 double precision, etage smallint, annee_etiquette varchar(8))"))
    db.execute(text("CREATE TABLE IF NOT EXISTS parcel_adresse (idu varchar(14) PRIMARY KEY, ban_voie text, ban_cp varchar(5), ban_commune varchar(80))"))
    db.execute(text("CREATE TABLE IF NOT EXISTS parcelle_personne_morale (idu varchar(14), denomination varchar(200), siren varchar(20))"))
    db.execute(text("CREATE TABLE IF NOT EXISTS owner_enrichment (siren varchar(9) PRIMARY KEY, payload jsonb NOT NULL, fetched_at timestamptz NOT NULL DEFAULT now())"))


def _seed_parcel(db, idu, *, commune="Saint-Paul", section="AB", numero="0001", surface=800,
                 batie=False, ban=None, pm_denom=None, siren=None, siege_payload=None):
    _ensure_adressage_tables(db)
    pid = db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom) "
        "VALUES (:i,:c,:s,:n,:su, ST_SetSRID(ST_GeomFromText('POLYGON((55.5 -21,55.5001 -21,55.5001 -21.0001,55.5 -21))'),4326)) "
        "ON CONFLICT (idu) DO UPDATE SET commune=EXCLUDED.commune RETURNING id"),
        {"i": idu, "c": commune, "s": section, "n": numero, "su": surface}).scalar()
    if batie:
        db.execute(text("INSERT INTO parcel_filtre_bati (parcel_id, idu, ratio_pct, emprise_max_m2, etage, annee_etiquette) "
                        "VALUES (:p,:i,40,100,1,'2020') ON CONFLICT DO NOTHING"), {"p": pid, "i": idu})
    if ban:
        db.execute(text("INSERT INTO parcel_adresse (idu, ban_voie, ban_cp, ban_commune) VALUES (:i,:v,:cp,:co) "
                        "ON CONFLICT (idu) DO UPDATE SET ban_voie=EXCLUDED.ban_voie"),
                   {"i": idu, "v": ban[0], "cp": ban[1], "co": ban[2]})
    if pm_denom:
        db.execute(text("INSERT INTO parcelle_personne_morale (idu, denomination, siren) VALUES (:i,:d,:s) "
                        "ON CONFLICT DO NOTHING"), {"i": idu, "d": pm_denom, "s": siren})
    if siren and siege_payload is not None:
        import json as _j
        db.execute(text("INSERT INTO owner_enrichment (siren, payload) VALUES (:s, cast(:p AS jsonb)) "
                        "ON CONFLICT (siren) DO UPDATE SET payload=EXCLUDED.payload"),
                   {"s": siren, "p": _j.dumps(siege_payload)})
    return pid


def test_adressage_occupant_nu_siege_et_opposition(client, engine):
    """Le résolveur d'adressage : PP bâtie → à l'occupant ; PP nue → bloquée ; PM avec siège →
    nominatif au siège ; opposition → bloquée. Aucune substitution silencieuse (bien ≠ adresse d'envoi)."""
    from labuse import courrier_adressage as ca, courrier
    pp_batie, pp_nue, pm_siege = "97499000ZA0001", "97499000ZA0002", "97499000ZA0003"
    with engine.begin() as db:
        _ensure_adressage_tables(db)
        db.execute(text("DELETE FROM courrier_opposition"))
        for i in (pp_batie, pp_nue, pm_siege):
            db.execute(text("DELETE FROM parcel_filtre_bati WHERE idu=:i"), {"i": i})
            db.execute(text("DELETE FROM parcel_adresse WHERE idu=:i"), {"i": i})
            db.execute(text("DELETE FROM parcelle_personne_morale WHERE idu=:i"), {"i": i})
        _seed_parcel(db, pp_batie, batie=True, ban=("12 Rue du Test", "97460", "Saint-Paul"))
        _seed_parcel(db, pp_nue, batie=False)
        _seed_parcel(db, pm_siege, batie=True, ban=("3 Rue Bien", "97410", "Saint-Pierre"),
                     pm_denom="SCCV TEST", siren="123456789",
                     siege_payload={"siege": {"adresse": "1 Rue Siege 97400 Saint-Denis",
                                              "code_postal": "97400", "libelle_commune": "Saint-Denis"}})
    with engine.begin() as db:
        r1 = ca.resoudre_destinataire(db, pp_batie)
        assert r1["type"] == "occupant" and not r1["bloque"] and r1["destinataire"] == "À l'occupant"
        assert "non nominatif" in r1["mention"]
        r2 = ca.resoudre_destinataire(db, pp_nue)
        assert r2["bloque"] and r2["motif"] == ca.MOTIF_NU
        r3 = ca.resoudre_destinataire(db, pm_siege)
        assert r3["type"] == "siege" and not r3["bloque"]
        assert r3["destinataire"] == "SCCV TEST — au siège social déclaré"
        assert r3["adresse_envoi"] == "1 Rue Siege 97400 Saint-Denis"
        # bien concerné ≠ adresse d'envoi : preuve d'absence de substitution silencieuse
        assert r3["bien"]["adresse"] == "3 Rue Bien, 97410 Saint-Pierre"
        # opposition sur la parcelle bâtie → bloquée avec le motif unique
        courrier.ajouter_opposition(db, adresse=None, idu=pp_batie, reference=None, par="test")
    with engine.begin() as db:
        r4 = ca.resoudre_destinataire(db, pp_batie)
        assert r4["bloque"] and r4["motif"] == courrier.MOTIF_OPPOSITION
    # l'endpoint sert bien les résolutions au front (écran avant dépôt)
    res = client.post("/courrier/adressage", json={"idus": [pp_nue, pm_siege]}).json()["resolutions"]
    assert res[0]["motif"] == ca.MOTIF_NU and res[1]["type"] == "siege"
    with engine.begin() as db:
        db.execute(text("DELETE FROM courrier_opposition"))
        for i in (pp_batie, pp_nue, pm_siege):
            db.execute(text("DELETE FROM parcel_filtre_bati WHERE idu=:i"), {"i": i})
            db.execute(text("DELETE FROM parcel_adresse WHERE idu=:i"), {"i": i})
            db.execute(text("DELETE FROM parcelle_personne_morale WHERE idu=:i"), {"i": i})
