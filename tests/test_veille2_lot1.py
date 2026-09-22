"""VEILLE-2 · Lot 1 — Chemin PARCELLE.

Un seul suivi (table watched_parcels), cinq déclencheurs : vente (DVF), permis (Sitadel), procédure
(BODACC), changement de propriétaire PM, bascule du score (produite par detect-events). Le ZONAGE n'est
plus un déclencheur. La barre IDU (watch_toggle) refuse AVEC MOTIF un IDU invalide ou hors des 24 communes.

Tests robustes au résidu (base partagée) : commune/IDU dédiés ZZV2, aucune assertion sur un compteur global.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from labuse.api import events


def _ensure(db):
    for stmt in events.DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))
    db.execute(text("CREATE TABLE IF NOT EXISTS sitadel_permits ("
                    "permit_id varchar(64), commune varchar(64), date_depot date, date date, "
                    "type varchar(8), idu_codes jsonb)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS dvf_mutations_parcelle ("
                    "id_mutation varchar(32), id_parcelle varchar(14), date_mutation date, "
                    "valeur_fonciere numeric, nature_mutation varchar(32))"))
    db.execute(text("CREATE TABLE IF NOT EXISTS parcelle_personne_morale ("
                    "idu varchar(14), siren varchar(20), denomination text)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS bodacc_procedures ("
                    "annonce_id varchar(32), siren varchar(20), type_procedure text, date_annonce date)"))
    events._ensure_cols(db)
    events._ensure_suivi_cols(db)


# ─────────────── la barre IDU refuse AVEC MOTIF (invalide / hors des 24) ───────────────

def test_watch_refuse_idu_invalide():
    """IDU malformé (≠ 14 car.) → 422 avec le mot « invalide » (jamais un 404 muet). La validation
    est AVANT toute résolution de compte/base : request/db non touchés."""
    with pytest.raises(HTTPException) as e:
        events.watch_toggle("BW0917", request=None, db=None)          # trop court
    assert e.value.status_code == 422 and "invalide" in e.value.detail.lower()


def test_watch_refuse_hors_24_communes():
    """IDU bien formé (14 car., code commune numérique) mais commune hors des 24 → 422 « hors des 24
    communes ». 97500 = 5 chiffres valides, pas une commune de La Réunion."""
    with pytest.raises(HTTPException) as e:
        events.watch_toggle("97500000AB0001", request=None, db=None)
    assert e.value.status_code == 422 and "24 communes" in e.value.detail


def test_watch_accepte_idu_du_perimetre_puis_404_si_absent(db_session):
    """Un IDU d'une des 24 communes (97411 = un code Réunion valide) passe les deux gardes de format et
    échoue seulement sur l'absence en base → 404 « Parcelle inconnue » (motif distinct)."""
    _ensure(db_session)

    class _Req:  # request minimal — current_compte lit request.state
        class state:  # noqa: N801
            compte_id = None
    db_session.execute(text("DELETE FROM parcels WHERE idu='97411000ZZ0001'"))
    with pytest.raises(HTTPException) as e:
        events.watch_toggle("97411000ZZ0001", request=_Req(), db=db_session)
    assert e.value.status_code == 404 and "inconnue" in e.value.detail.lower()


# ─────────────── déclencheur « changement de propriétaire PM » (empreinte SIREN) ───────────────

@pytest.mark.db
def test_changement_proprietaire_pm(db_session):
    """Suivre une parcelle → propriétaire PM (SIREN A) → premier evaluer_suivis POSE l'empreinte SANS
    alerter (pas de backfill) → le SIREN devient B → evaluer_suivis crée UNE notification
    « Changement de propriétaire ». Ré-évaluation = dédup."""
    _ensure(db_session)
    idu = "97411000ZZ0009"
    db_session.execute(text("DELETE FROM event_log WHERE idu=:i"), {"i": idu})
    db_session.execute(text("DELETE FROM watched_parcels WHERE idu=:i"), {"i": idu})
    db_session.execute(text("DELETE FROM parcelle_personne_morale WHERE idu=:i"), {"i": idu})
    db_session.execute(text("INSERT INTO watched_parcels (idu, compte_id, created_at) "
                            "VALUES (:i, NULL, now()-interval '1 day')"), {"i": idu})
    db_session.execute(text("INSERT INTO parcelle_personne_morale (idu, siren, denomination) "
                            "VALUES (:i, '111111111', 'SOCIETE A')"), {"i": idu})

    out1 = events.evaluer_suivis(db_session)
    assert out1["proprietaire"] == 0                      # premier passage = empreinte posée, pas d'alerte
    assert "zonage" not in out1                           # le zonage n'est plus un déclencheur

    # la parcelle change de mains morales : SIREN A → SIREN B
    db_session.execute(text("UPDATE parcelle_personne_morale SET siren='222222222', denomination='SOCIETE B' "
                            "WHERE idu=:i"), {"i": idu})
    out2 = events.evaluer_suivis(db_session)
    assert out2["proprietaire"] == 1
    rows = db_session.execute(text(
        "SELECT titre, source FROM event_log WHERE idu=:i AND kind='parcelle_suivie'"), {"i": idu}).mappings().all()
    assert len(rows) == 1 and rows[0]["source"] == "Propriétaire"
    assert "propriétaire" in rows[0]["titre"].lower()

    events.evaluer_suivis(db_session)                     # ré-éval → dédup, aucun doublon
    n = db_session.execute(text("SELECT count(*) FROM event_log WHERE idu=:i AND kind='parcelle_suivie'"),
                           {"i": idu}).scalar()
    assert n == 1


@pytest.mark.db
def test_zonage_nest_plus_un_declencheur(db_session):
    """Un changement de zonage PLU sur une parcelle suivie ne produit PLUS d'événement (retiré du modèle
    VEILLE-2). La table parcel_zone_plu peut exister ou non : evaluer_suivis ne la lit plus."""
    _ensure(db_session)
    idu = "97411000ZZ0010"
    db_session.execute(text("DELETE FROM event_log WHERE idu=:i"), {"i": idu})
    db_session.execute(text("DELETE FROM watched_parcels WHERE idu=:i"), {"i": idu})
    db_session.execute(text("INSERT INTO watched_parcels (idu, compte_id, created_at, zone_snap) "
                            "VALUES (:i, NULL, now()-interval '1 day', 'U')"), {"i": idu})
    # aucune mutation/permis/bodacc/pm : la seule chose « changée » serait le zonage — ignoré.
    out = events.evaluer_suivis(db_session)
    assert out == {"mutation": 0, "permis": 0, "bodacc": 0, "proprietaire": 0}
    n = db_session.execute(text("SELECT count(*) FROM event_log WHERE idu=:i AND kind='parcelle_suivie'"),
                           {"i": idu}).scalar()
    assert n == 0
