"""CIRCUIT-1 lot 0 — les bloquants.

  · 0.2 — UN SEUL compte de sources : l'écran Circuit (flux.construire_flux) compte le MÊME
    périmètre que la vitrine (WHERE_AFFICHEES) et que l'arbitre unique (etats_sources.lister_etats).
    Avant : count(*) brut (77) vs vitrine (66) — le « 77 dont 49 » du constat Vic 05/09/2026.
  · 0.3 — le tampon DPE ne ment plus : un passage qui n'a rien interrogé (handle["tampon"]=False)
    laisse `data_sources.last_sync_at` INCHANGÉ ; un passage réel le pose (défaut True).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse import etats_sources, flux
from labuse.ingestion import fraicheur
from labuse.sources_catalog import est_affichee

pytestmark = pytest.mark.db


@pytest.fixture
def seed_catalogue(db_session):
    """Quatre sources : affichée+sondée · affichée+rappel · DOUBLON · désactivée au dashboard."""
    tag = uuid.uuid4().hex[:6]
    ids = {}
    ids["ok"] = db_session.execute(text(
        "INSERT INTO data_sources (name, status) VALUES (:n, 'connecte') RETURNING id"),
        {"n": f"Source sondée {tag}"}).scalar()
    db_session.execute(text(
        "INSERT INTO source_veille (source_id, methode, dernier_statut, actif) "
        "VALUES (:i, 'api', 'ok', true)"), {"i": ids["ok"]})
    ids["rappel"] = db_session.execute(text(
        "INSERT INTO data_sources (name, status) VALUES (:n, 'manuel') RETURNING id"),
        {"n": f"Source manuelle {tag}"}).scalar()
    db_session.execute(text(
        "INSERT INTO source_veille (source_id, methode, actif) VALUES (:i, 'rappel', true)"),
        {"i": ids["rappel"]})
    ids["doublon"] = db_session.execute(text(
        "INSERT INTO data_sources (name, status, technical_notes) "
        "VALUES (:n, 'connecte', 'DOUBLON de « Source sondée »') RETURNING id"),
        {"n": f"Source doublon {tag}"}).scalar()
    # le DOUBLON porte une veille active : avant 0.2 elle gonflait le compte « surveillées »
    db_session.execute(text(
        "INSERT INTO source_veille (source_id, methode, dernier_statut, actif) "
        "VALUES (:i, 'entete', 'ok', true)"), {"i": ids["doublon"]})
    ids["off"] = db_session.execute(text(
        "INSERT INTO data_sources (name, status, affichage_desactive) "
        "VALUES (:n, 'connecte', true) RETURNING id"), {"n": f"Source désactivée {tag}"}).scalar()
    return ids


def test_02_trois_ecrans_un_seul_nombre(db_session, seed_catalogue):
    """Circuit (flux) == arbitre unique (etats_sources) == vitrine : même périmètre, même nombre."""
    d = flux.construire_flux(db_session)
    etats = etats_sources.lister_etats(db_session)
    assert d["comptes"]["total"] == len(etats), (
        "l'écran Circuit doit compter le MÊME périmètre que la page Sources / le Catalogue")
    # le total est celui des lignes réellement servies par l'écran (jamais un count(*) brut)
    assert d["comptes"]["total"] == len(d["sources"])
    ids_servis = {s["id"] for s in d["sources"]}
    assert seed_catalogue["ok"] in ids_servis
    assert seed_catalogue["doublon"] not in ids_servis, "un DOUBLON ne compte pas"
    assert seed_catalogue["off"] not in ids_servis, "une source désactivée ne compte pas"


def test_02_surveillees_vraies_sondes_du_perimetre(db_session, seed_catalogue):
    """« surveillées » = sondes RÉELLES (api/page/entete/temoin, actives) PARMI les affichées :
    ni un rappel manuel, ni la veille d'un DOUBLON hors vitrine."""
    d = flux.construire_flux(db_session)
    servies = {s["id"]: s for s in d["sources"]}
    # même critère que le code : vraie sonde ET active — la sonde du DOUBLON (hors vitrine),
    # le rappel manuel et une sonde désactivée ne comptent pas
    attendu = sum(1 for s in servies.values()
                  if s["nature"] in ("version", "changement")
                  and (s["veille"] is None or s["veille"].get("actif") is not False)
                  ) if servies and "veille" in next(iter(servies.values())) else None
    if attendu is None:      # le payload ne porte pas la veille brute : on vérifie par SQL
        attendu = db_session.execute(text(
            "SELECT count(*) FROM data_sources d JOIN source_veille v ON v.source_id = d.id "
            "WHERE v.methode IN ('api','page','entete','temoin') AND COALESCE(v.actif, true) "
            "AND lower(d.status) IN ('connecte','manuel') "
            "AND COALESCE(d.technical_notes,'') NOT LIKE 'DOUBLON%' "
            "AND COALESCE(d.technical_notes,'') NOT LIKE 'RETIRÉ%' "
            "AND COALESCE(d.technical_notes,'') NOT LIKE 'DORMANT%' "
            "AND COALESCE(d.affichage_desactive, false) = false")).scalar()
    assert d["comptes"]["surveillees"] == attendu
    assert d["comptes"]["surveillees"] <= d["comptes"]["total"]


def test_02_predicat_affichage_desactive():
    """dashboard.py passe désormais le flag au prédicat canonique : une source désactivée sort."""
    assert est_affichee("X", None, "connecte", False) is True
    assert est_affichee("X", None, "connecte", True) is False


def test_03_tampon_false_ne_pose_pas_last_sync(db_session):
    """0 commune interrogée → handle['tampon']=False → last_sync_at INCHANGÉ (le test qui aurait
    attrapé le mensonge DPE de CIRCUIT-0 : /healthz « ok » sur un passage à vide)."""
    nom = f"Source tampon {uuid.uuid4().hex[:6]}"
    db_session.execute(text(
        "INSERT INTO data_sources (name, status) VALUES (:n, 'connecte')"), {"n": nom})
    db_session.commit()
    with fraicheur.trace_ingestion(db_session, "test (tampon à vide)", [nom]) as h:
        h["tampon"] = False          # rien n'a été interrogé (toutes communes sautées)
    assert db_session.execute(text(
        "SELECT last_sync_at FROM data_sources WHERE name = :n"), {"n": nom}).scalar() is None
    # la trace ingestion_runs, elle, existe et dit 'ok' (le passage a bien eu lieu)
    st = db_session.execute(text(
        "SELECT status FROM ingestion_runs WHERE commune = 'test (tampon à vide)' "
        "ORDER BY id DESC LIMIT 1")).scalar()
    assert st == "ok"


def test_03_tampon_defaut_pose_last_sync(db_session):
    """Défaut inchangé (bodacc/géorisques) : un passage réel pose last_sync_at."""
    nom = f"Source tampon {uuid.uuid4().hex[:6]}"
    db_session.execute(text(
        "INSERT INTO data_sources (name, status) VALUES (:n, 'connecte')"), {"n": nom})
    db_session.commit()
    with fraicheur.trace_ingestion(db_session, "test (tampon réel)", [nom]):
        pass
    assert db_session.execute(text(
        "SELECT last_sync_at FROM data_sources WHERE name = :n"), {"n": nom}).scalar() is not None
