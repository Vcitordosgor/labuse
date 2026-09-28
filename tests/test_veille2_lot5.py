"""VEILLE-2 · Lot 5 — Un mail par jour.

Le digest du matin porte TOUT ce qui change pour le compte : parcelles suivies + Radar + nouveautés.
Plus d'alerte Radar séparée. Un compte sans événement la veille = pas de mail. Un compte = un mail
maximum par jour (dédup mail_queue), prouvé en dry-run sur 3 comptes.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse import comptes
from labuse.api import events
from labuse.db import session_scope

pytestmark = pytest.mark.db


def _compte(db, email: str) -> int:
    try:
        comptes.supprimer_utilisateur(db, email)
    except Exception:
        pass
    inv = comptes.creer_invitation(db, email)
    comptes.activer_par_invitation(db, inv["lien"].split("token=")[1], "motdepasse-veille2", "2026-07-22")
    db.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
    db.commit()
    return inv["compte_id"]


def _ev(db, *, kind, cid, titre, lien=None, source=None, idu=None):
    db.execute(text("INSERT INTO event_log (kind, idu, titre, compte_id, lien, source) "
                    "VALUES (:k, :i, :t, :c, :l, :s)"),
               {"k": kind, "i": idu, "t": titre, "c": cid, "l": lien, "s": source})


def _lignes_digest(db, cid) -> int:
    return db.execute(text("SELECT count(*) FROM mail_queue WHERE compte_id=:c AND mail_key='digest_quotidien'"),
                      {"c": cid}).scalar()


def test_un_seul_mail_par_jour_trois_comptes():
    """A (parcelle suivie + Radar) et B (parcelle suivie) reçoivent CHACUN un mail ; C (rien) aucun.
    Rejouer le digest ne crée pas un 2ᵉ mail (un par compte par jour)."""
    tag = uuid.uuid4().hex[:6]
    ea, eb, ec = f"a{tag}@labuse.immo", f"b{tag}@labuse.immo", f"c{tag}@labuse.immo"
    with session_scope() as db:
        from labuse.mailfile import ensure_tables as _mq
        _mq(db.get_bind())
        A, B, C = _compte(db, ea), _compte(db, eb), _compte(db, ec)
        for cid in (A, B, C):
            db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
            db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
        # A : une parcelle suivie + une annonce Radar (deux catégories, UN seul mail)
        _ev(db, kind="parcelle_suivie", cid=A, titre="Vente sur votre parcelle", source="Mutation", idu=None)
        _ev(db, kind="radar", cid=A, titre="Nouvelle annonce pour votre veille — Terrain à Saint-Denis",
            lien="https://www.leboncoin.fr/ad/ventes_immobilieres/123", source="Radar")
        # B : une parcelle suivie seulement
        _ev(db, kind="parcelle_suivie", cid=B, titre="Nouveau permis sur votre parcelle", source="Permis")
        # C : rien
        db.commit()

        r1 = events.envoyer_digests(db, base_url="https://app.labuse.immo", dry_run=True)
        d = {x["compte"]: x for x in r1["details"] if x["compte"] in (A, B, C)}
        assert d[A]["statut"] == "simulé" and d[B]["statut"] == "simulé"
        assert d[C]["statut"] == "ignoré" and "aucun événement" in d[C]["motif"]
        # le mail de A porte le Radar (une des deux catégories) — corps de la simulation
        assert "annonce" in (d[A].get("corps") or "").lower()
        assert _lignes_digest(db, A) == 1 and _lignes_digest(db, B) == 1 and _lignes_digest(db, C) == 0

        # TESTS-FIX-1 — chaque passage du digest est SA propre transaction en production (le job
        # envoyer_digests ouvre/valide un session_scope par run). Le test enchaînait deux appels dans
        # UNE transaction non validée : le 1er run laisse des lignes mail_queue verrouillées (non
        # commit), et `_mq_ensure` du 2ᵉ run (DDL « CREATE/ALTER mail_queue IF NOT EXISTS » sur une
        # connexion SÉPARÉE du pool) attendait ce verrou → la connexion `db` restait idle-in-transaction
        # et se faisait tuer (idle_in_transaction_session_timeout, ~600 s). On valide donc le 1er run
        # avant le rejeu, comme en production — la dédup mail_queue (compte, jour) reste vérifiée.
        db.commit()

        # rejeu le MÊME jour → dédup mail_queue : toujours une seule ligne par compte
        events.envoyer_digests(db, base_url="https://app.labuse.immo", dry_run=True)
        assert _lignes_digest(db, A) == 1 and _lignes_digest(db, B) == 1 and _lignes_digest(db, C) == 0

        for e in (ea, eb, ec):
            comptes.supprimer_utilisateur(db, e)
        db.execute(text("DELETE FROM mail_queue WHERE compte_id = ANY(:c)"), {"c": [A, B, C]})
        db.execute(text("DELETE FROM event_log WHERE compte_id = ANY(:c)"), {"c": [A, B, C]})
        db.commit()


def test_digest_porte_radar_et_nouveaute():
    """Le digest d'un compte inclut ses événements Radar (compte-scopé) ET les nouveautés de l'app
    (broadcast, postérieures à sa création) — plus d'alerte Radar séparée."""
    tag = uuid.uuid4().hex[:6]
    email = f"n{tag}@labuse.immo"
    with session_scope() as db:
        from labuse.mailfile import ensure_tables as _mq
        _mq(db.get_bind())
        cid = _compte(db, email)
        db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
        _ev(db, kind="radar", cid=cid, titre="Nouvelle annonce pour votre veille — Maison à Saint-Paul",
            lien="https://www.leboncoin.fr/ad/ventes_immobilieres/456", source="Radar")
        # VEILLE-FIX-2 (grille Vic 27/09) — la NOUVELLE SOURCE est désormais CLOCHE POUR TOUS, JAMAIS
        # dans le mail (l'inclusion `nouveaute` de VEILLE-2 Lot 5 est retirée) : le digest porte le Radar,
        # pas la nouveauté.
        events.annoncer_nouveaute(db, "Nouvelle source dans LABUSE (test)")
        db.commit()

        r = events.envoyer_digests(db, base_url="https://app.labuse.immo", dry_run=True)
        d = next(x for x in r["details"] if x["compte"] == cid)
        assert d["statut"] == "simulé"
        corps = (d.get("corps") or "").lower()
        assert "annonce" in corps                          # le Radar est présent…
        assert "nouvelle source dans labuse" not in corps  # …mais PLUS la nouveauté (grille : mail=non)

        comptes.supprimer_utilisateur(db, email)
        db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
        db.execute(text("DELETE FROM event_log WHERE compte_id=:c OR titre='Nouvelle source dans LABUSE (test)'"),
                   {"c": cid})
        db.commit()
