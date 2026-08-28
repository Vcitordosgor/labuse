"""RADAR P4 · D1 — veille Radar + les deux digests (digest quotidien + alerte veille).

On sème un client actif + une veille + un bien du jour, et on gèle : deux envois DISTINCTS, jamais un
mail vide, échec d'envoi BRUYANT (event système), aucun lien portail dans le mail (faits + lien fiche).
[RADAR-TEST] purgés en fin.
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
    st = {}
    with session_scope() as s:
        # RD-503 (chasse) : ne plus créer de colonne `prenoms` — elle n'existe PAS en prod ; le digest
        # sert `comptes.nom` (colonne réelle). L'ancien ALTER masquait le bug du cron.
        # compte actif + titulaire (matching veille) ; compte actif sans veille (digest seul)
        for k, mail in (("match", f"m-{tag}@rt.test"), ("plain", f"p-{tag}@rt.test")):
            cid = s.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                 "VALUES (:n,'integral',false,'actif',1) RETURNING id"),
                            {"n": f"RT {tag} {k}"}).scalar()
            s.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                           "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": mail})
            st[k] = cid
        # veille pour le compte « match » : Saint-Benoît, terrain > 2000 m², particuliers
        veille.creer(s, compte_id=st["match"],
                     criteria={"commune": "Saint-Benoît", "surface_terrain_min": 2000, "particulier_only": True})
        # un bien du jour validé qui matche
        bid = s.execute(text("INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut) "
                             "VALUES ('Saint-Benoît','terrain',false,'absent','active') RETURNING bien_id")).scalar()
        s.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                  {"b": bid, "u": f"https://www.leboncoin.fr/rt-{tag}"})
        s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_terrain,particulier_pro,valide_at) "
                       "VALUES (:b,150000,'terrain',2500,'particulier',now())"), {"b": bid})
        st["bien"] = bid
    yield st
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": st["bien"]})
        s.execute(text("DELETE FROM veilles WHERE compte_id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM utilisateurs WHERE compte_id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM comptes WHERE id = ANY(:c)"), {"c": [st["match"], st["plain"]]})
        s.execute(text("DELETE FROM event_log WHERE kind IN ('pige.digest_envoye','systeme') AND source='Radar'"))


def test_deux_envois_distincts_dry_run(seed):
    with session_scope() as db:
        r = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=True)
    types = [(d["compte_id"], d["type_envoi"]) for d in r["details"]]
    # digest à TOUS les actifs (2 comptes) + alerte au SEUL compte dont la veille matche
    assert (seed["match"], "digest") in types and (seed["plain"], "digest") in types
    assert (seed["match"], "alerte") in types
    assert (seed["plain"], "alerte") not in types      # pas de veille → pas d'alerte
    # digest à mes 2 comptes + alerte au compte « match » (d'autres comptes actifs du corpus de test
    # peuvent s'ajouter → au moins 3, mes tuples présents).
    assert r["simules"] >= 3


def test_jamais_de_mail_vide(seed):
    # on dé-valide le bien → aucune nouveauté du jour → aucun envoi (ni digest ni alerte)
    with session_scope() as db:
        db.execute(text("UPDATE pige_faits SET valide_at=NULL WHERE bien_id=:b"), {"b": seed["bien"]})
        db.commit()
        r = digests.envoyer(db, dry_run=True)
    assert r["n_biens_du_jour"] == 0 and r["simules"] == 0 and r["envoyes"] == 0


def test_pas_de_lien_portail_dans_le_mail(seed):
    bien = {"commune": "Saint-Benoît", "type_bien": "terrain", "idu": None,
            "rattachement_niveau": "absent", "faits": {"prix": 150000, "surface_terrain": 2500}}
    item = digests._item("https://app.labuse.immo", bien)
    assert item["url_fiche"].startswith("https://app.labuse.immo/socle/")   # fiche LABUSE
    assert "leboncoin" not in item["url_fiche"] and "url_sortante" not in item


def test_alerte_veille_part_vers_email_du_compte(seed, monkeypatch):
    """RV2-V3 — PREUVE : l'alerte de veille (et le digest) partent vers l'E-MAIL DU COMPTE (titulaire
    de la licence), jamais vers une adresse d'ailleurs. On capture le destinataire réel passé à Brevo."""
    captures: list[tuple[str, str]] = []
    monkeypatch.setattr(digests.brevo, "envoyer_template",
                        lambda to, key, params: (captures.append((to, key)), {"envoye": True})[1])
    with session_scope() as db:
        email_match = db.execute(text(
            "SELECT email FROM utilisateurs WHERE compte_id=:c AND role='titulaire'"),
            {"c": seed["match"]}).scalar()
        digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=False)
    tos = [to for to, _ in captures]
    # le compte dont la veille matche a bien reçu ses envois à SON e-mail de titulaire
    assert email_match in tos, tos
    # AUCUN envoi ne part vers une adresse qui n'est pas l'e-mail titulaire d'un compte ACTIF
    with session_scope() as db:
        emails_actifs = set(db.execute(text(
            "SELECT u.email FROM utilisateurs u JOIN comptes c ON c.id=u.compte_id "
            "WHERE c.statut='actif' AND u.role='titulaire'")).scalars())
    hors = set(tos) - emails_actifs
    assert not hors, f"une alerte/digest est partie vers une adresse HORS compte actif : {hors}"


def test_echec_envoi_bruyant(seed):
    # sans clé/template Brevo (env de test), l'envoi RÉEL échoue → compté + event système visible.
    with session_scope() as db:
        r = digests.envoyer(db, base_url="https://app.labuse.immo", dry_run=False)
    assert r["echecs"] >= 1 and r["envoyes"] == 0
    with session_scope() as db:
        n = db.execute(text("SELECT count(*) FROM event_log WHERE kind='systeme' AND source='Radar' "
                            "AND titre LIKE 'Échec envoi Radar%'")).scalar()
    assert n >= 1
