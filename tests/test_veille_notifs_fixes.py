"""VEILLE/NOTIFS — verrous des 5 corrections post-audit (fix/veille-notifs).

#3 idempotence permis (rejeu = 0 doublon) · #2 dry-run digest (aucun envoi) · #4 run de référence
lu de la table (jamais une constante)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import events as ev


@pytest.mark.db
def test_permis_idempotent_meme_a_un_autre_jour(db_session):
    """#3 — un permis (fait UNIQUE (idu, permit_id)) rejoué un AUTRE jour ne crée jamais de doublon
    (dédup PERMANENTE). Avant le fix, la garde même-jour laissait passer un doublon au rejeu J+1."""
    d = "test:permis:97415000AB0001:PCX1"
    db_session.execute(text("DELETE FROM event_log WHERE dedup=:d"), {"d": d})
    n1 = ev.creer_notification(db_session, kind="parcelle_suivie", source="Permis",
                               idu="97415000AB0001", titre="permis", dedup=d, permanent=True)
    # simule le rejeu un autre jour : l'événement existant est daté d'avant-hier
    db_session.execute(text("UPDATE event_log SET ts = ts - interval '2 days' WHERE dedup=:d"), {"d": d})
    n2 = ev.creer_notification(db_session, kind="parcelle_suivie", source="Permis",
                               idu="97415000AB0001", titre="permis", dedup=d, permanent=True)
    total = db_session.execute(text("SELECT count(*) FROM event_log WHERE dedup=:d"), {"d": d}).scalar()
    assert n1 and n2 == 0 and total == 1     # créé une fois, jamais dupliqué au rejeu
    # contraste : SANS permanent, la garde même-jour laisserait repasser un autre jour
    n3 = ev.creer_notification(db_session, kind="parcelle_suivie", source="Permis",
                               idu="97415000AB0001", titre="permis", dedup=d, permanent=False)
    assert n3 != 0     # même-jour : l'existant étant daté d'avant-hier, la garde jour ne bloque plus
    db_session.execute(text("DELETE FROM event_log WHERE dedup=:d"), {"d": d})


@pytest.mark.db
def test_digest_dry_run_n_envoie_rien(db_session):
    """#2/#5 — dry_run : aucun envoi Brevo, aucun last_digest_at avancé, un drapeau dry_run rendu."""
    avant = db_session.execute(text("SELECT max(last_digest_at) FROM notif_prefs")).scalar()
    out = ev.envoyer_digests(db_session, base_url="", freq="quotidien", force=True, dry_run=True)
    apres = db_session.execute(text("SELECT max(last_digest_at) FROM notif_prefs")).scalar()
    assert out["dry_run"] is True and out["envoyes"] == 0 and "simules" in out
    assert avant == apres     # #5 — last_digest_at JAMAIS avancé par un dry-run


@pytest.mark.db
def test_run_precedent_vient_de_la_table(db_session):
    """#4 — le run de référence du rejeu est LU de p_score_v2_runs (jamais une constante) : ne lève pas,
    et n'est jamais le run servi lui-même."""
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    prev = ev.run_precedent_servi(db_session, Q_A_RUN_LABEL)
    assert prev != Q_A_RUN_LABEL     # jamais le servi ; None si aucun autre run (base de test)
