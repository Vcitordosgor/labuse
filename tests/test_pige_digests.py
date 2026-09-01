"""RADAR-DIGESTS — les deux digests (12 digest quotidien + 13 alerte de veille) branchés sur Brevo.

On gèle : deux envois DISTINCTS · jamais un mail vide · le lien de carte pointe vers le PORTAIL (décision
mandat) · CHAQUE valeur d'annonce échappée (contrainte Brevo) · plafond 10 + « et N autres » · idempotence
sur la journée · échec BRUYANT · lecture effective de la clé Brevo (RV-013). [RADAR-TEST] purgés en fin.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import digests, veille

pytestmark = pytest.mark.db


@pytest.fixture
def seed(engine):
    tag = uuid.uuid4().hex[:5]
    st = {"tag": tag}
    with session_scope() as s:
        for k, mail in (("match", f"m-{tag}@rt.test"), ("plain", f"p-{tag}@rt.test")):
            cid = s.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                 "VALUES (:n,'integral',false,'actif',1) RETURNING id"),
                            {"n": f"RT {tag} {k}"}).scalar()
            s.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                           "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": mail})
            st[k] = cid
        veille.creer(s, compte_id=st["match"],
                     criteria={"commune": "Saint-Benoît", "surface_terrain_min": 2000, "particulier_only": True})
        bid = s.execute(text("INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut) "
                             "VALUES ('Saint-Benoît','terrain',false,'absent','active') RETURNING bien_id")).scalar()
        s.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                  {"b": bid, "u": f"https://www.leboncoin.fr/rt-{tag}"})
        s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_terrain,particulier_pro,valide_at) "
                       "VALUES (:b,150000,'terrain',2500,'particulier',now())"), {"b": bid})
        st["bien"] = bid
    yield st
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE commune='Saint-Benoît' AND bien_id=:b"), {"b": st["bien"]})
        s.execute(text("DELETE FROM veilles WHERE compte_id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM utilisateurs WHERE compte_id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM comptes WHERE id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM event_log WHERE kind IN ('pige.digest_envoye','systeme') AND source='Radar'"))


def test_deux_envois_distincts_dry_run(seed):
    with session_scope() as db:
        r = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=True)
    types = [(d["compte_id"], d["type_envoi"]) for d in r["details"]]
    assert (seed["match"], "digest") in types and (seed["plain"], "digest") in types
    assert (seed["match"], "alerte") in types
    assert (seed["plain"], "alerte") not in types
    assert r["simules"] >= 3


def test_jamais_de_mail_vide(seed):
    with session_scope() as db:
        db.execute(text("UPDATE pige_faits SET valide_at=NULL WHERE bien_id=:b"), {"b": seed["bien"]})
        db.commit()
        r = digests.envoyer(db, dry_run=True)
    assert r["n_biens_du_jour"] == 0 and r["simules"] == 0 and r["envoyes"] == 0


def test_carte_lien_vers_portail_et_non_rattache():
    """Décision mandat : la carte pointe vers le PORTAIL (l'annonce), et un bien non rattaché le DIT."""
    row = {"bien_id": 1, "commune": "Saint-Paul", "type_bien": "terrain", "est_copro": False, "idu": None,
           "prix": 349000, "surface_hab": None, "surface_terrain": 800, "particulier_pro": "particulier",
           "portail": "leboncoin", "url_sortante": "https://www.leboncoin.fr/x", "date_releve": None,
           "ancien_prix": None, "nouveau_prix": None}
    it = digests._carte_item("https://app.labuse.immo", row)
    h = digests.carte_html(it)
    assert "leboncoin.fr/x" in h and "Voir l'annonce sur" in h
    assert "Non rattaché à une parcelle" in h
    assert "349 000 €" in h                      # prix formaté (Brevo ne met rien en forme)
    assert "€/m²" in h                            # prix/m² calculé (349000/800)


def test_carte_echappe_guillemet_et_chevron():
    """Contrainte 3 : une valeur d'annonce avec un guillemet ET un chevron est ÉCHAPPÉE — mise en page
    intacte, injection impossible."""
    row = {"bien_id": 2, "commune": 'Sainte-"Marie" <b>', "type_bien": "maison", "est_copro": False,
           "idu": None, "prix": 200000, "surface_hab": 90, "surface_terrain": None,
           "particulier_pro": "pro", "portail": "leboncoin",
           "url_sortante": 'https://x.test/"><script>', "date_releve": None,
           "ancien_prix": None, "nouveau_prix": None}
    h = digests.carte_html(digests._carte_item("", row))
    assert "<script>" not in h and "<b>" not in h            # aucun tag injecté
    assert "&lt;b&gt;" in h and "&lt;script&gt;" in h        # échappés
    assert '"><script>' not in h                              # l'attribut href ne casse pas


def test_plafond_dix_et_n_autres():
    """25 biens → 10 cartes + « et 15 autres sur le Radar »."""
    rows = [{"bien_id": i, "commune": "Saint-Denis", "type_bien": "terrain", "est_copro": False,
             "idu": None, "prix": 100000 + i, "surface_hab": None, "surface_terrain": 500,
             "particulier_pro": "particulier", "portail": "leboncoin", "url_sortante": f"https://x/{i}",
             "date_releve": None, "ancien_prix": None, "nouveau_prix": None} for i in range(25)]
    h = digests.cartes_html(rows, "")
    assert h.count("border:1px solid #e7e5e4") == 10          # exactement 10 cartes
    assert "et 15 autres sur le Radar" in h


def test_ordre_baisse_d_abord():
    """La baisse de prix passe AVANT les biens sans baisse (signal actionnable daté)."""
    rows = [
        {"bien_id": 1, "commune": "A", "type_bien": "terrain", "est_copro": False, "idu": None,
         "prix": 100000, "surface_hab": None, "surface_terrain": 500, "particulier_pro": None,
         "portail": "leboncoin", "url_sortante": "https://x/1", "date_releve": None,
         "ancien_prix": None, "nouveau_prix": None},
        {"bien_id": 2, "commune": "B", "type_bien": "terrain", "est_copro": False, "idu": None,
         "prix": 80000, "surface_hab": None, "surface_terrain": 500, "particulier_pro": None,
         "portail": "leboncoin", "url_sortante": "https://x/2", "date_releve": None,
         "ancien_prix": 100000, "nouveau_prix": 80000},   # baisse
    ]
    items = digests._ordonner([digests._carte_item("", r) for r in rows])
    assert items[0]["_bien_id"] == 2, "le bien en baisse est en premier"


def test_idempotence_par_jour(seed, monkeypatch):
    """Rejouée le même jour, la commande ne ré-envoie pas le même digest/alerte au même client."""
    # CONNEXIONS-2 Lot 9.1 (KO-12) — l'envoi passe désormais par la FAÇADE unique `mail.envoyer_template`.
    monkeypatch.setattr(digests.mail, "envoyer_template", lambda to, key, params: {"envoye": True})
    with session_scope() as db:
        r1 = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=False)
    with session_scope() as db:
        r2 = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=False)
    assert r1["envoyes"] >= 2                     # digest+alerte partis au 1er passage
    assert r2["envoyes"] == 0 and r2["deja"] >= 2, "2e passage : rien de renvoyé (idempotent)"


def test_cle_brevo_lue_depuis_l_environnement(monkeypatch):
    """RV-013 — la clé API Brevo est LUE depuis l'environnement (sinon aucun mail ne partirait)."""
    from labuse import brevo
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    assert brevo._api_key() is None
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-TEST")
    assert brevo._api_key() == "xkeysib-TEST", "la clé du .env est bien lue par le code"


def test_echec_envoi_bruyant(seed):
    with session_scope() as db:
        r = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=False)
    assert r["echecs"] >= 1 and r["envoyes"] == 0
    with session_scope() as db:
        n = db.execute(text("SELECT count(*) FROM event_log WHERE kind='systeme' AND source='Radar' "
                            "AND titre LIKE 'Échec envoi Radar%'")).scalar()
    assert n >= 1
