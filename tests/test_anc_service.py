"""M88 — l'ANC servi : trois états, jamais quatre, AUCUN seuil. Invariants DURS : `proba_anc` n'est
plus lu (une proba élevée sans zonage ni taux de secteur = Absent, jamais un verdict) ; un NULL n'est
jamais un raccordement ; jamais « probablement », jamais « collectif » présumé. Le chemin Sourcé
(secteur) — taux INSEE par IRIS/commune, spatial — est couvert par la recette (géométrie requise)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import anc_service


def _ensure(db):
    # parcel_anc seule (le vrai `parcels` a un schéma NOT NULL — statut_anc tolère commune=None ; sans
    # géométrie ni anc_maille_taux, le chemin SECTEUR ne trouve rien → Absent, ce qui est exactement vrai).
    db.execute(text("CREATE TABLE IF NOT EXISTS parcel_anc (idu varchar(14) PRIMARY KEY, zone_anc text, "
                    "source text, proba_anc int, updated_at timestamptz)"))
    db.execute(text("DELETE FROM parcel_anc WHERE idu IN ('T_A','T_B','T_C','T_D','T_E')"))
    # A = ANC réglementaire ; B = collectif réglementaire ; C = ex-« estimé » (proba haute, IGNORÉE) ;
    # D = ex-« sous seuil » ; E = pas de ligne. C/D/E → Absent (proba_anc n'est plus lu).
    db.execute(text("INSERT INTO parcel_anc (idu, zone_anc, source, proba_anc) VALUES "
                    "('T_A','anc','zonage_officiel',80),('T_B','collectif','zonage_officiel',80),"
                    "('T_C',NULL,'proba_insee',95),('T_D',NULL,'proba_insee',10)"))


@pytest.mark.db
def test_anc_etats_sources_et_absent(db_session):
    _ensure(db_session)
    a = anc_service.statut_anc(db_session, "T_A")
    assert a["statut"] == "source" and a["anc"] is True and "non collectif" in a["libelle"].lower()
    b = anc_service.statut_anc(db_session, "T_B")
    assert b["statut"] == "source" and b["anc"] is False and "collectif" in b["libelle"].lower()
    # M88 : proba_anc n'est PLUS lu — une proba de 95 sans zonage ni taux de secteur = Absent.
    for idu in ("T_C", "T_D", "T_E"):
        r = anc_service.statut_anc(db_session, idu)
        assert r["statut"] == "absent", f"{idu} devrait être Absent (proba_anc ignorée)"


@pytest.mark.db
def test_proba_anc_ne_fabrique_plus_de_verdict(db_session):
    _ensure(db_session)
    # T_C portait proba_anc=95 → jamais « estimé », jamais « source_secteur » sans taux réel, jamais
    # un seuil. Le péché mortel évité : jamais « collectif », jamais « probablement », pas de raccordement.
    r = anc_service.statut_anc(db_session, "T_C")
    assert r["statut"] == "absent"
    low = r["phrase"].lower()
    assert "probablement" not in low and "collectif" not in low
    assert "pas un raccordement" in low


@pytest.mark.db
def test_absent_jamais_collectif_ni_raccordement(db_session):
    _ensure(db_session)
    for idu in ("T_D", "T_E"):
        r = anc_service.statut_anc(db_session, idu)
        assert r["statut"] == "absent"
        low = r["phrase"].lower()
        assert "collectif" not in low and "probablement" not in low
        assert "pas un raccordement" in low


@pytest.mark.db
def test_source_commune_office_eau_dit_echelle_et_millesime(db_session):
    """M95 — commune classée INTÉGRALEMENT en ANC (Office de l'eau) : 3ᵉ échelle de Sourcé, distincte du
    parcellaire et du secteur. L'ÉCHELLE (commune entière) et le MILLÉSIME (source amont) sont DITS ; une
    commune < 100 % NE bascule PAS (jamais un « intégralement » inventé)."""
    _ensure(db_session)   # parcel_anc existe mais VIDE pour ces idus → pas de zone parcellaire
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS anc_office_eau_commune (insee varchar(5) PRIMARY KEY, commune text, "
        "pct_anc int, detail text, millesime text, source_ref text, updated_at timestamptz)"))
    db_session.execute(text("DELETE FROM anc_office_eau_commune WHERE insee IN ('97421','97499')"))
    db_session.execute(text(
        "INSERT INTO anc_office_eau_commune (insee, commune, pct_anc, millesime, source_ref) VALUES "
        "('97421','Salazie',100,'Chronique n°149 — données 2023','Office de l''eau Réunion, texte p.13'),"
        "('97499','Autre',80,'x','y')"))                 # 80 % ≠ intégral → PAS source_commune
    r = anc_service.statut_anc(db_session, "97421000TESTA1")
    assert r["statut"] == "source_commune" and r["maille_type"] == "commune" and r["anc"] is True
    assert "données 2023" in r["millesime"]
    low = r["phrase"].lower()
    assert "intégralement" in low and "commune entière" in low   # l'échelle est DITE
    # une commune sous 100 % ne fabrique JAMAIS un « intégralement »
    assert anc_service.statut_anc(db_session, "97499000TESTB1")["statut"] != "source_commune"
