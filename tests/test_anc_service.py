"""M86-B — l'ANC servi : trois états, jamais quatre. Invariants DURS : sous le seuil = Absent (JAMAIS
« collectif »), un NULL n'est jamais un raccordement, l'Estimé est SECTORIEL (maille IRIS)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import anc_service


def _ensure(db):
    # parcel_anc seule (le vrai `parcels` a un schéma NOT NULL — statut_anc tolère commune=None).
    db.execute(text("CREATE TABLE IF NOT EXISTS parcel_anc (idu varchar(14) PRIMARY KEY, zone_anc text, "
                    "source text, proba_anc int, updated_at timestamptz)"))
    db.execute(text("DELETE FROM parcel_anc WHERE idu IN ('T_A','T_B','T_C','T_D','T_E')"))
    # A = ANC réglementaire ; B = collectif réglementaire ; C = estimé (≥seuil) ; D = sous seuil ; E = pas de ligne
    db.execute(text("INSERT INTO parcel_anc (idu, zone_anc, source, proba_anc) VALUES "
                    "('T_A','anc','zonage_officiel',80),('T_B','collectif','zonage_officiel',80),"
                    "('T_C',NULL,'proba_insee',95),('T_D',NULL,'proba_insee',10)"))


@pytest.mark.db
def test_anc_trois_etats(db_session):
    _ensure(db_session)
    a = anc_service.statut_anc(db_session, "T_A")
    assert a["statut"] == "source" and a["anc"] is True and "non collectif" in a["libelle"].lower()
    b = anc_service.statut_anc(db_session, "T_B")
    assert b["statut"] == "source" and b["anc"] is False and "collectif" in b["libelle"].lower()
    c = anc_service.statut_anc(db_session, "T_C")
    assert c["statut"] == "estime" and "iris" in c["maille"].lower()
    d = anc_service.statut_anc(db_session, "T_D")
    assert d["statut"] == "absent"
    e = anc_service.statut_anc(db_session, "T_E")             # aucune ligne parcel_anc
    assert e["statut"] == "absent"


@pytest.mark.db
def test_sous_seuil_jamais_collectif_ni_raccordement(db_session):
    _ensure(db_session)
    for idu in ("T_D", "T_E"):                                # sous seuil + sans ligne
        r = anc_service.statut_anc(db_session, idu)
        assert r["statut"] == "absent"
        # LE PÉCHÉ MORTEL évité : jamais « collectif », jamais « probablement », jamais un raccordement présumé
        low = r["phrase"].lower()
        assert "collectif" not in low and "probablement" not in low
        assert "pas un raccordement" in low


@pytest.mark.db
def test_estime_est_sectoriel_jamais_parcellaire(db_session):
    _ensure(db_session)
    r = anc_service.statut_anc(db_session, "T_C")
    low = r["phrase"].lower()
    assert "secteur" in low and "spanc" in low                # propriété de secteur + orientation SPANC
    assert "cette parcelle est" not in low                     # jamais une affirmation parcellaire


def test_seuil_en_config_pas_en_dur():
    assert anc_service.seuil_fiche() == 75                     # M86-B : lu de config/anc_vegetation.yaml
