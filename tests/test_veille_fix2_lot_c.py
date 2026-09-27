"""VEILLE-FIX-2 · Lot C — la fréquence est LUE et RÉGLABLE.

`digest_freq` était stocké mais jamais appliqué (un compte « hebdo » recevait le quotidien). Désormais le
digest respecte la cadence de CHAQUE compte : quotidien (défaut) · hebdo (lundi) · cloche_seule (jamais).

Preuve 1 : le décideur pur `_cadence_digest` sur 7 jours simulés → le bon nombre de mails par fréquence.
Preuve 2 (base réelle) : 3 comptes, 3 fréquences → cloche_seule ignoré, quotidien envoyé ; get/set OK.
[VF2-C] purgés en fin.
"""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import text

from labuse.api import events
from labuse.db import session_scope

pytestmark = pytest.mark.db

REU = dt.timezone(dt.timedelta(hours=4))


def _simuler_7_jours(freq: str) -> int:
    """Combien de mails en 7 jours consécutifs (départ un LUNDI) pour cette fréquence ?"""
    envois = 0
    last = None
    base = dt.datetime(2026, 9, 28, 3, 15, tzinfo=dt.timezone.utc)   # 2026-09-28 = un lundi
    for d in range(7):
        now = base + dt.timedelta(days=d)
        jour_semaine = now.astimezone(REU).weekday()
        ok, _motif = events._cadence_digest(freq, jour_semaine, last, now, force=False)
        if ok:
            envois += 1
            last = now
    return envois


def test_cadence_sur_7_jours():
    assert _simuler_7_jours("quotidien") == 7, "quotidien = un mail chaque jour"
    assert _simuler_7_jours("hebdo") == 1, "hebdo = un seul mail (le lundi)"
    assert _simuler_7_jours("cloche_seule") == 0, "cloche seule = aucun mail"
    # une valeur inconnue retombe sur le défaut (quotidien)
    assert _simuler_7_jours("n'importe quoi") == 7


def test_get_set_frequence_et_effet_reel():
    tag = uuid.uuid4().hex[:6]
    ids = {}
    try:
        with session_scope() as db:
            from labuse.mailfile import ensure_tables as _mq
            events.ensure_tables(db.get_bind())
            _mq(db.get_bind())
            for k in ("q", "h", "c"):
                cid = db.execute(text("INSERT INTO comptes (nom, plan, founding, statut, sieges) "
                                      "VALUES (:n,'integral',false,'actif',1) RETURNING id"),
                                 {"n": f"[VF2-C] {k}{tag}"}).scalar()
                db.execute(text("INSERT INTO utilisateurs (compte_id, email, role, statut, echecs_login) "
                                "VALUES (:c,:e,'titulaire','actif',0)"), {"c": cid, "e": f"{k}{tag}@vf2c.test"})
                ids[k] = cid
            # régler les fréquences via l'API interne
            assert events.set_digest_freq(db, ids["q"], "quotidien") == "quotidien"
            assert events.set_digest_freq(db, ids["h"], "hebdo") == "hebdo"
            assert events.set_digest_freq(db, ids["c"], "cloche_seule") == "cloche_seule"
            # get round-trip
            assert events.get_digest_freq(db, ids["h"]) == "hebdo"
            # une valeur inconnue → défaut quotidien
            assert events.set_digest_freq(db, ids["q"], "foo") == "quotidien"
            # chaque compte a un événement e-mailable
            for k in ("q", "h", "c"):
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": ids[k]})
                db.execute(text("INSERT INTO event_log (kind, titre, compte_id, source) "
                                "VALUES ('parcelle_suivie', :t, :c, 'Mutation')"),
                           {"t": f"Vente sur votre parcelle ({tag})", "c": ids[k]})
            db.commit()

            r = events.envoyer_digests(db, base_url="https://app.labuse.immo", dry_run=True)
            d = {x["compte"]: x for x in r["details"] if x["compte"] in ids.values()}
            # cloche_seule : JAMAIS de mail
            assert d[ids["c"]]["statut"] == "ignoré" and "cloche seulement" in d[ids["c"]]["motif"]
            # quotidien : envoyé (simulé en dry-run)
            assert d[ids["q"]]["statut"] == "simulé"
            # hebdo : envoyé SEULEMENT le lundi — motif explicite les autres jours
            jour = dt.datetime.now(REU).weekday()
            if jour == 0:
                assert d[ids["h"]]["statut"] == "simulé"
            else:
                assert d[ids["h"]]["statut"] == "ignoré" and "hebdomadaire" in d[ids["h"]]["motif"]
    finally:
        with session_scope() as db:
            for cid in ids.values():
                db.execute(text("DELETE FROM mail_queue WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM event_log WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM notif_prefs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM notif_canaux WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM utilisateurs WHERE compte_id=:c"), {"c": cid})
                db.execute(text("DELETE FROM comptes WHERE id=:c"), {"c": cid})
            db.commit()
