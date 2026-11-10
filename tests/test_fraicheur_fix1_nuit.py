"""FRAICHEUR-FIX-1 (point 7) — le contrôle PERMANENT : le tableau des sources rejoué chaque nuit ;
toute source qui passe « en retard » remonte chez John, à l'admin (cloche/incident) et à la page
Données (instantané) avec le nom de la source et le millésime attendu ; la récupération résout l'incident."""
from datetime import date

import pytest
from sqlalchemy import text

from labuse import jobs_impl
from labuse.jobs import JobContext

pytestmark = pytest.mark.db


def _poser_dvf(s, dernier_vu, horizon):
    sid = s.execute(text("SELECT id FROM data_sources WHERE name='DVF / valeurs foncières'")).scalar()
    if sid is None:
        sid = s.execute(text(
            "INSERT INTO data_sources (name, status, source_cadence, source_horizon_at) "
            "VALUES ('DVF / valeurs foncières', 'connecte', 'semestriel', :h) RETURNING id"),
            {"h": horizon}).scalar()
    else:
        s.execute(text("UPDATE data_sources SET status='connecte', source_cadence='semestriel', "
                       "source_horizon_at=:h, affichage_desactive=false, technical_notes=NULL WHERE id=:id"),
                  {"h": horizon, "id": sid})
    if s.execute(text("SELECT 1 FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar():
        s.execute(text("UPDATE source_veille SET methode='dvf', dernier_statut='ok', dernier_vu=:vu, "
                       "actif=true WHERE source_id=:s"), {"s": sid, "vu": dernier_vu})
    else:
        s.execute(text(
            "INSERT INTO source_veille (source_id, methode, dernier_statut, dernier_vu, cadence_heures, "
            " echecs_consecutifs, actif, mail_alerte) VALUES (:s,'dvf','ok',:vu,24,0,true,false)"),
            {"s": sid, "vu": dernier_vu})


def test_fraicheur_nuit_signale_les_retards(db_session):
    s = db_session
    _poser_dvf(s, "2026-S1", date(2025, 12, 31))   # amont S1 2026, servi 2025 → EN RETARD

    ctx = JobContext(db=s, dry_run=True)
    jobs_impl.fraicheur_nuit(ctx)

    # (1) instantané de la page Données
    snap = s.execute(text("SELECT etat, millesime_publie FROM fraicheur_controle_nuit "
                          "WHERE name='DVF / valeurs foncières'")).mappings().first()
    assert snap and snap["etat"] == "en_retard"
    assert ctx.compteurs["retards"] >= 1
    assert "DVF / valeurs foncières" in ctx.compteurs["noms_en_retard"]

    # (2) incident admin ouvert (cloche + mail), lien /sources
    inc = s.execute(text("SELECT 1 FROM ops_incidents WHERE cle='fraicheur-retard:DVF / valeurs foncières' "
                         "AND resolu_at IS NULL")).scalar()
    assert inc == 1

    # (3) remonté chez John (axe sources, millésime attendu)
    john = s.execute(text("SELECT titre, date_vue FROM john_veille WHERE axe='sources' "
                          "AND source='DVF / valeurs foncières'")).mappings().first()
    assert john and "en retard" in john["titre"]

    # ── récupération : données ingérées jusqu'au 30/06/2026 → plus de retard, incident résolu ──
    _poser_dvf(s, "2026-S1", date(2026, 6, 30))
    ctx2 = JobContext(db=s, dry_run=True)
    jobs_impl.fraicheur_nuit(ctx2)
    assert "DVF / valeurs foncières" not in ctx2.compteurs["noms_en_retard"]
    assert ctx2.compteurs["incidents_resolus"] >= 1
    resolu = s.execute(text("SELECT resolu_at FROM ops_incidents "
                            "WHERE cle='fraicheur-retard:DVF / valeurs foncières'")).scalar()
    assert resolu is not None
    snap2 = s.execute(text("SELECT etat FROM fraicheur_controle_nuit "
                           "WHERE name='DVF / valeurs foncières'")).scalar()
    assert snap2 == "a_jour"
