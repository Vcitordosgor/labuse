"""VEILLE-FIX-2 · Lot B — les événements manquants, une ligne de grille à la fois.

  · baisse de prix (radar_baisse)  → aux comptes dont les critères matchent, cloche + digest ;
  · retrait confirmé (radar_retrait) → idem ;
  · mise en vente d'une parcelle SUIVIE (parcelle_en_vente) → au suiveur, cloche EN TÊTE + MAIL IMMÉDIAT ;
  · bascule / nouvelle source → cloche pour TOUS, JAMAIS dans le mail.

Destinataires exacts (ni plus, ni moins). [VF2-B] purgés en fin.
"""
from __future__ import annotations

import datetime as _dt
import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import digests, veille

pytestmark = pytest.mark.db


def _compte(db, nom, email):
    cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                          "VALUES (:n,'integral',false,'actif',1) RETURNING id"), {"n": nom}).scalar()
    db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                    "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": email})
    return cid


def _bien(db, commune, statut="active", idu=None, retiree=False):
    bid = db.execute(text(
        "INSERT INTO pige_biens (commune,type_bien,est_copro,statut,a_qualifier,idu,date_premiere_saisie,retiree_le) "
        "VALUES (:c,'maison',false,:s,false,:i, now(), :r) RETURNING bien_id"),
        {"c": commune, "s": statut, "i": idu,
         "r": _dt.datetime.now(_dt.timezone.utc) if retiree else None}).scalar()
    db.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,particulier_pro,valide_at) "
                    "VALUES (:b,300000,'maison',90,'particulier',now())"), {"b": bid})
    db.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
               {"b": bid, "u": f"https://leboncoin.fr/vf2b-{bid}"})
    return bid


def _reset_wm(db):
    digests._ensure_watermark(db)
    db.execute(text("DELETE FROM pige_watermark WHERE nom=:n"), {"n": digests._WATERMARK_RADAR})


def _events(db, cid, kind):
    return db.execute(text("SELECT titre, detail FROM event_log WHERE compte_id=:c AND kind=:k"),
                      {"c": cid, "k": kind}).mappings().all()


def test_baisse_et_retrait_vont_aux_criteres_qui_matchent():
    tag = uuid.uuid4().hex[:6]
    com = f"ZZVF2B-{tag}"
    ids, biens = {}, []
    try:
        with session_scope() as db:
            _reset_wm(db)
            ids["match"] = _compte(db, f"[VF2-B] m{tag}", f"m{tag}@vf2b.test")
            ids["sans"] = _compte(db, f"[VF2-B] s{tag}", f"s{tag}@vf2b.test")
            veille.creer(db, compte_id=ids["match"], criteria={"commune": com, "type_bien": "maison"})
            veille.creer(db, compte_id=ids["sans"], criteria={"commune": f"AILLEURS-{tag}"})
            # baisse
            bb = _bien(db, com); biens.append(bb)
            db.execute(text("INSERT INTO pige_prix_historique (bien_id,ancien_prix,nouveau_prix,date_constat) "
                            "VALUES (:b,350000,300000, now())"), {"b": bb})
            # retrait confirmé
            br = _bien(db, com, statut="retiree", retiree=True); biens.append(br)
            db.commit()

            r = digests.evaluer_radar_cloche(db)
            assert r["radar_baisse"] >= 1 and r["radar_retrait"] >= 1, r
            eb = _events(db, ids["match"], "radar_baisse")
            assert eb and "350 000" in eb[0]["detail"] and "300 000" in eb[0]["detail"]
            er = _events(db, ids["match"], "radar_retrait")
            assert er and "retirée" in er[0]["detail"]
            # le compte SANS critère matchant ne reçoit RIEN
            assert not _events(db, ids["sans"], "radar_baisse")
            assert not _events(db, ids["sans"], "radar_retrait")
    finally:
        with session_scope() as db:
            if biens:
                db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": biens})
            for cid in ids.values():
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM veilles WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            _reset_wm(db)
            db.commit()


def test_mise_en_vente_parcelle_suivie_event_et_mail_immediat():
    tag = uuid.uuid4().hex[:6]
    idu = f"9741100VF{tag[:3].upper()}"[:14]
    cid = None
    bid = None
    try:
        with session_scope() as db:
            from labuse.mailfile import ensure_tables as _mq
            _mq(db.get_bind())
            _reset_wm(db)
            cid = _compte(db, f"[VF2-B] mev{tag}", f"mev{tag}@vf2b.test")
            db.execute(text("INSERT INTO watched_parcels (compte_id, idu, created_at) VALUES (:c,:i,'2025-01-01')"),
                       {"c": cid, "i": idu})
            bid = _bien(db, f"ZZMEV-{tag}", idu=idu)
            db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
            db.commit()

            r = digests.evaluer_radar_cloche(db)
            assert r["parcelle_en_vente"] >= 1, r
            ev = _events(db, cid, "parcelle_en_vente")
            assert ev and "mise en vente" in ev[0]["titre"].lower()
            # MAIL IMMÉDIAT : une ligne mail_queue (dry-run car SMTP absent en test)
            mq = db.execute(text("SELECT mail_key, etat FROM mail_queue WHERE compte_id=:c "
                                 "AND mail_key='mise_en_vente'"), {"c": cid}).mappings().all()
            assert len(mq) == 1, f"un mail immédiat de mise en vente attendu, obtenu {mq}"
            # rejeu : pas de 2ᵉ event ni 2ᵉ mail (dédup)
            digests.evaluer_radar_cloche(db)
            assert len(_events(db, cid, "parcelle_en_vente")) == 1
            assert db.execute(text("SELECT count(*) FROM mail_queue WHERE compte_id=:c "
                                   "AND mail_key='mise_en_vente'"), {"c": cid}).scalar() == 1
    finally:
        with session_scope() as db:
            if bid:
                db.execute(text("DELETE FROM pige_biens WHERE bien_id=:b"), {"b": bid})
            if cid:
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM watched_parcels WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            _reset_wm(db)
            db.commit()


def test_bascule_et_nouveaute_cloche_mais_jamais_mail():
    """Bascule + nouvelle source : à la cloche (broadcast), JAMAIS dans le digest e-mail."""
    from labuse.api import events
    tag = uuid.uuid4().hex[:6]
    cid = None
    try:
        with session_scope() as db:
            from labuse.mailfile import ensure_tables as _mq
            _mq(db.get_bind())
            cid = _compte(db, f"[VF2-B] bn{tag}", f"bn{tag}@vf2b.test")
            db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
            # une bascule marché (broadcast) + une nouvelle source, postérieures à la création du compte
            events.creer_notification(db, kind="bascule", compte_id=None, source="Scoring",
                                      titre=f"▲ Classement mis à jour ({tag})", idu=None,
                                      dedup=f"bascule:test:{tag}")
            events.annoncer_nouveaute(db, f"Nouvelle source importée ({tag})")
            db.commit()
            # digest dry-run : le compte n'a AUCUN événement e-mailable (bascule/nouveaute hors mail)
            r = events.envoyer_digests(db, base_url="https://app.labuse.immo", freq="quotidien",
                                       force=True, dry_run=True)
            d = next((x for x in r["details"] if x["compte"] == cid), None)
            assert d and d["statut"] == "ignoré" and "aucun événement" in d["motif"], d
            assert db.execute(text("SELECT count(*) FROM mail_queue WHERE compte_id=:c"), {"c": cid}).scalar() == 0
    finally:
        with session_scope() as db:
            db.execute(text("DELETE FROM event_log WHERE titre LIKE :t OR titre LIKE :u"),
                       {"t": f"%({tag})%", "u": f"%{tag}%"})
            if cid:
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            db.commit()
