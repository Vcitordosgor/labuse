"""FRAICHEUR-FIX-1 (point 6) — la sentinelle lit le bon signal : le millésime réellement ingéré
comparé au dernier publié ; `etats_sources` ne projette « à jour » que si c'est prouvé, sinon
« à vérifier ». Test par source : un retard ressort « en retard » AVANT correction, « à jour » APRÈS."""
from datetime import date

import pytest
from sqlalchemy import text

from labuse import controle_millesime as cm
from labuse import etats_sources


def test_periode_normalise_les_millesimes_heterogenes():
    assert cm.periode("2026-S1") == 202606
    assert cm.periode("2026-S2") == 202612
    assert cm.periode("2026-09") == 202609
    assert cm.periode("RP2023") == 202312
    assert cm.periode("2022") == 202212
    assert cm.periode(date(2025, 12, 31)) == 202512
    assert cm.periode(date(2026, 6, 30)) == 202606
    assert cm.periode("2026-10-30T15:13:14.102Z") == 202610  # timestamp SITADEL → année-mois
    assert cm.periode(None) is None
    # un hash d'empreinte (témoin/entête) ne porte pas de millésime → None (pas de faux contrôle)
    assert cm.periode("2:f68766ddc759c4bd") is None
    assert cm.periode("52-8ab5b0e699b930d5b6ac4158") is None


def _row(name, dernier_vu, horizon):
    return {"name": name, "dernier_vu": dernier_vu, "source_horizon_at": horizon}


def test_dvf_en_retard_avant_puis_a_jour_apres():
    # AVANT : amont publie S1 2026, LABUSE sert jusqu'au 31/12/2025 → EN RETARD (prouvé)
    v = cm.verdict(None, _row("DVF / valeurs foncières", "2026-S1", date(2025, 12, 31)))
    assert v["etat"] == "en_retard"
    assert v["publie"] == "2026" or v["publie"].endswith("2026")  # juin 2026 = 06/2026
    assert v["ingere"] == "2025"
    # APRÈS reload : la donnée servie atteint le 30/06/2026 → À JOUR (prouvé)
    v2 = cm.verdict(None, _row("DVF / valeurs foncières", "2026-S1", date(2026, 6, 30)))
    assert v2["etat"] == "a_jour"


def test_sitadel_en_retard_avant_puis_a_jour_apres():
    # AVANT : SDES couvre jusqu'au 30/09 (sonde `temporal_coverage.end`), LABUSE sert août → EN RETARD
    nom = "SITADEL (autorisations d'urbanisme)"
    v = cm.verdict(None, _row(nom, "2026-09-30", date(2026, 8, 31)))
    assert v["etat"] == "en_retard"
    assert v["publie"] == "09/2026" and v["ingere"] == "08/2026"
    # APRÈS ingestion de septembre : à jour (prouvé)
    v2 = cm.verdict(None, _row(nom, "2026-09-30", date(2026, 9, 30)))
    assert v2["etat"] == "a_jour"


def test_a_verifier_quand_ingere_inconnu():
    v = cm.verdict(None, _row("DVF / valeurs foncières", "2026-S1", None))
    assert v["etat"] == "a_verifier"
    assert v["ingere"] is None


def test_source_hors_controle_rend_none():
    assert cm.verdict(None, _row("Une source continue quelconque", "2026-11-07", date(2026, 11, 1))) is None


# ─────────────── intégration : lister_etats applique le contrôle (DB) ───────────────

def _poser_dvf(s, dernier_vu, horizon):
    """UPSERT (jamais de DELETE — la table est référencée par spatial_layers) : la source DVF existe
    avec un horizon donné, surveillée par une sonde `dvf` au dernier publié donné."""
    sid = s.execute(text("SELECT id FROM data_sources WHERE name='DVF / valeurs foncières'")).scalar()
    if sid is None:
        sid = s.execute(text(
            "INSERT INTO data_sources (name, status, source_cadence, source_horizon_at) "
            "VALUES ('DVF / valeurs foncières', 'connecte', 'semestriel', :h) RETURNING id"),
            {"h": horizon}).scalar()
    else:
        s.execute(text("UPDATE data_sources SET status='connecte', source_cadence='semestriel', "
                       "source_horizon_at=:h, affichage_desactive=false, technical_notes=NULL "
                       "WHERE id=:id"), {"h": horizon, "id": sid})
    existe = s.execute(text("SELECT 1 FROM source_veille WHERE source_id=:s"), {"s": sid}).scalar()
    if existe:
        s.execute(text("UPDATE source_veille SET methode='dvf', dernier_statut='ok', dernier_vu=:vu, "
                       "actif=true WHERE source_id=:s"), {"s": sid, "vu": dernier_vu})
    else:
        s.execute(text(
            "INSERT INTO source_veille (source_id, methode, dernier_statut, dernier_vu, cadence_heures, "
            " echecs_consecutifs, actif, mail_alerte) "
            "VALUES (:s, 'dvf', 'ok', :vu, 24, 0, true, false)"), {"s": sid, "vu": dernier_vu})


@pytest.mark.db
def test_lister_etats_flip_dvf(db_session):
    s = db_session
    _poser_dvf(s, "2026-S1", date(2025, 12, 31))
    etats = etats_sources.lister_etats(s)
    dvf = next(e for e in etats if e["name"] == "DVF / valeurs foncières")
    assert dvf["etat"] == "en_retard"
    assert dvf["etat_client"] == "pas_a_jour"
    assert etats_sources.compteurs(etats)["en_retard"] >= 1

    # APRÈS correction (données ingérées jusqu'au 30/06/2026)
    _poser_dvf(s, "2026-S1", date(2026, 6, 30))
    etats2 = etats_sources.lister_etats(s)
    dvf2 = next(e for e in etats2 if e["name"] == "DVF / valeurs foncières")
    assert dvf2["etat"] == "a_jour"
    assert dvf2["etat_client"] == "a_jour"
