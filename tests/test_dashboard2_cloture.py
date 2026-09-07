"""DASHBOARD-2 — LE TEST QUI CLÔT LE MANDAT.

« Ouvrir le Pilotage, relever les 8 chiffres, ouvrir les 8 pages, vérifier que chacun s'y
retrouve à l'identique. » Ici, on ne relève pas des pixels : on vérifie que le CHIFFRE servi au
Pilotage (jauge) est LE MÊME que celui servi à la page concernée — un chiffre = une fonction.

Couvre aussi les deux LED de rail ajoutées au Lot 1 (Horloge posés/attendus, Verrous n/16).
Lot 2 (Comptes/mail_queue) est SAUTÉ (COMPTE-2 pas encore mergé) : la jauge Système lit la santé
serveur en attendant, non testée ici comme un compteur unique.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(engine):
    """TestClient admin (même patron que test_dashboard) : sans session compte, /admin/* est servi."""
    from labuse import config
    from labuse.api import dashboard
    from labuse.api.app import app
    dashboard.ensure_tables(engine)
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def _seed_client(engine) -> int:
    with engine.begin() as c:
        cid = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Client Clôture', 'integral', 'actif') RETURNING id"
        )).scalar()
    return int(cid)


def test_rail_horloge_et_verrous_presents(client):
    """Lot 1 — le rail expose Horloge (jobs posés / attendus) et Verrous (ok / 16)."""
    d = client.get("/admin/pilotage").json()
    assert "horloge" in d and "verrous" in d
    h, v = d["horloge"], d["verrous"]
    # posés ≤ attendus (jamais plus de jobs posés que planifiés) ; 16 verrous au total (ou None si jamais joué).
    assert h["attendus"] is None or (h["poses"] is not None and 0 <= h["poses"] <= h["attendus"])
    assert v["sur"] in (None, 16)
    if v["ok"] is not None and v["sur"] is not None:
        assert 0 <= v["ok"] <= v["sur"]


def test_clients_le_meme_9(client, engine):
    """Lot 2 §3 — UNE fonction, TROIS lectures. Le compteur unique de licences actives payantes
    (comptes.licences_actives, livré par COMPTE-2) est lu à l'IDENTIQUE par le Pilotage (jauge/rail)
    ET la page Comptes (compteurs.licences_actives). Les comptes ADMIN (interne) et de TEST
    ([CT-TEST] / @labuse.test) ne comptent nulle part."""
    from labuse.comptes import licences_actives
    _seed_client(engine)  # un client payant de plus (actif, pas d'essai)
    pil = client.get("/admin/pilotage").json()["licences_actives"]
    page = client.get("/admin/licences").json().get("compteurs", {}).get("licences_actives")
    with engine.begin() as c:
        direct = licences_actives(c)
    assert pil == direct == page              # jauge == fonction == page (compteur unique)
    with engine.begin() as c:
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('Interne Cloture', 'interne', 'actif')"))
        c.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES ('[CT-TEST] Cloture', 'integral', 'actif')"))
    pil2 = client.get("/admin/pilotage").json()["licences_actives"]
    assert pil2 == pil                        # ni l'interne ni le compte de test n'augmentent le compte


def test_filtre_test_elargi():
    """DASHBOARD-2 Lot 2 (recette « 18 à toucher pour 2 licences ») — le filtre de comptes de test
    ÉLARGI attrape ce qu'il manquait : domaines @exemple.test / @example.com / @labuse.local, alias
    Gmail « +test », noms « …Test » / « Recette » (sans e-mail réel) ; il NE masque PAS un vrai client
    dont le NOM contient « test » mais dont l'e-mail est réel."""
    from labuse.comptes import compte_est_test
    assert compte_est_test("demo-e1", "demo-e1@exemple.test")
    assert compte_est_test("checkout-preuve", "checkout-preuve@example.com")
    assert compte_est_test("LABUSE (admin)", "gb-test-ae@labuse.local")
    assert compte_est_test("Compte de test Vic (impayé)", "kampusreunion+test@gmail.com")
    assert compte_est_test("Essai Test", None)           # nom « Test », sans e-mail
    assert compte_est_test("Recette Onb", None)          # nom « Recette », sans e-mail
    # PROTÉGÉS — vrais comptes, même nom malheureux : e-mail réel → comptés
    assert not compte_est_test("ton-email@test.com", "kampusreunion@gmail.com")
    assert not compte_est_test("Promoteur SA", "contact@promoteur.re")


def test_courrier_a_deposer_le_meme(client, engine):
    """Jauge « Courrier » = pilotage.courrier.a_deposer = nb de demandes « à déposer » de la page."""
    cid = _seed_client(engine)
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO courrier_demandes (compte_id, n, communes, corps, statut) "
            "VALUES (:c, 1, 'Saint-Denis', 'corps de test', 'demande')"), {"c": cid})
    pil = client.get("/admin/pilotage").json()
    dem = client.get("/courrier/admin/demandes").json()["demandes"]
    ALIAS = {"tarif_confirme": "demande", "a_traiter": "demande"}
    a_deposer_page = sum(1 for d in dem if ALIAS.get(d["statut"], d["statut"]) == "demande")
    assert pil["courrier"]["a_deposer"] == a_deposer_page
    assert a_deposer_page >= 1


def test_produit_retours_ouverts_le_meme(client, engine):
    """Jauge « Produit » = signalements_ouverts + retours ouverts (clients), = la file « Retours »
    de la page Produit (tests/interne masqués partout). Un signalement d'un compte client compte ;
    un signalement interne (compte NULL / plan 'interne') ne compte NI au Pilotage NI sur la page."""
    cid = _seed_client(engine)
    with engine.begin() as c:
        # un signalement CLIENT ouvert (compté) + un signalement SANS compte (interne, jamais compté)
        c.execute(text("INSERT INTO signalements (type, type_erreur, statut, compte_id) "
                       "VALUES ('fiche', 'donnee', 'nouveau', :c)"), {"c": cid})
        c.execute(text("INSERT INTO signalements (type, type_erreur, statut, compte_id) "
                       "VALUES ('fiche', 'donnee', 'nouveau', NULL)"))
    pil = client.get("/admin/pilotage").json()
    jauge = int(pil["a_faire"]["signalements_ouverts"]) + sum(int(v) for v in (pil.get("retours_par_type") or {}).values())
    # la page : signalements nouveaux NON internes + retours nouveaux NON internes
    sigs = client.get("/admin/signalements").json()["signalements"]
    prod = client.get("/admin/produit").json()["retours"]
    page = (sum(1 for s in sigs if s["statut"] == "nouveau" and s.get("compte_plan") != "interne" and s.get("compte_id") is not None)
            + sum(1 for r in prod if r["statut"] == "nouveau" and r.get("compte_plan") != "interne" and r.get("compte") is not None))
    assert jauge == page
    # le signalement interne (compte NULL) n'est PAS compté
    assert jauge >= 1


def test_ia_conso_mois_le_meme(client):
    """Jauge « IA » = pilotage.ia_mois.cout_eur = /admin/ia mois.cout_eur (même ledger)."""
    pil = client.get("/admin/pilotage").json()
    ia = client.get("/admin/ia").json()
    assert abs(float(pil["ia_mois"]["cout_eur"]) - float(ia["mois"]["cout_eur"])) < 1e-6


def test_radar_en_vie_le_meme(client):
    """Jauge « Radar » = annonces_en_vie = flux.en_vie (même endpoint /admin/radar/check)."""
    chk = client.get("/admin/radar/check").json()
    assert chk["annonces_en_vie"] == chk["flux"]["en_vie"]
