"""RETOURS-13 Lot 3 — les tests qui auraient attrapé les défauts R22 / R26 / R29 / R30.

R22 : le compteur annuaire disait « 21 PLU disponibles » en cachant 2 règlements non servis —
      un PLU en révision RESTE en vigueur : 23 = 24 communes − 1 RNU, et les trous sont NOMMÉS.
R26 : la surface taxable n'était pas préremplie — LABUSE connaît la SDP au gabarit (résiduel).
R29 : le chiffre « N opérations » ne disait pas ce qu'il compte (parcelles encore possédées).
R30 : un permis dont la parcelle a disparu du cadastre (division) restait sans geom → invisible ;
      le repli adresse → parcelle (exact, approché, interpolé) le localise et LE DIT.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


# ── R22 — compteur PLU réconcilié ──────────────────────────────────────────────────────────

def test_r22_compteur_plu_en_vigueur(db_session):
    from labuse.api.modules import plu_annuaire_communes
    out = plu_annuaire_communes(db=db_session)
    assert out["n_plu_vigueur"] == out["n_communes"] - out["n_rnu"]   # révision ≠ PLU absent
    # les règlements non servis par le GPU sont NOMMÉS (jamais cachés dans le compteur)
    assert isinstance(out["non_servis"], list)
    for c in out["communes"]:
        if c["statut"] == "revision":
            assert c["commune"] in out["non_servis"]


# ── R26 — préremplissage de la taxe d'aménagement ─────────────────────────────────────────

def test_r26_prefill_sert_la_sdp_gabarit(db_session):
    from labuse.api.app import taxe_amenagement_prefill
    row = db_session.execute(text(
        "SELECT p.idu FROM parcels p JOIN parcel_residuel r ON r.parcel_id = p.id "
        "WHERE r.sdp_residuelle_m2 > 0 LIMIT 1")).first()
    if not row:
        pytest.skip("pas de résiduel en base de test")
    out = taxe_amenagement_prefill(idu=row[0], db=db_session)
    assert out["sdp_gabarit_m2"] is not None and out["sdp_gabarit_m2"] > 0


# ── R29 — le chiffre dit ce qu'il compte ──────────────────────────────────────────────────

def test_r29_frise_porte_le_perimetre_et_le_petitionnaire(db_session):
    from labuse.api.veille_promoteurs import promoteur_frise
    out = promoteur_frise("000000000", db=db_session)   # SIREN inexistant : structure seule
    assert "possède encore" in out["perimetre_note"]     # le périmètre est DIT
    assert "petitionnaire" in out and "n_permis" in out["petitionnaire"]
    assert isinstance(out["filiales_identifiees"], list)


# ── R30 — repli adresse → parcelle des permis orphelins ───────────────────────────────────

def test_r30_geocode_par_adresse_rattache_et_le_dit(db_session):
    from labuse.ingestion.permits_sdes import geocode_par_adresse
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '__test_r30__'"))
    db_session.execute(text("DELETE FROM adresses WHERE id_ban = '__test_r30__'"))
    # une adresse BAN connue…
    db_session.execute(text(
        "INSERT INTO adresses (id_ban, numero, voie, insee, commune, geom) VALUES "
        "('__test_r30__', '12', 'Rue Des Filaos', '97411', 'Saint-Denis', "
        " ST_SetSRID(ST_MakePoint(55.45, -20.9), 4326))"))
    # …et un permis SANS geom dont la parcelle a « disparu » (idu inconnu), adresse au formulaire
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw) VALUES "
        "('__test_r30__', 'PC', '2016-11-18', '[\"97411000ZZ9999\"]'::jsonb, 'Saint-Denis', NULL, "
        " CAST(:raw AS jsonb))"),
        {"raw": json.dumps({"insee": "97411", "adr_num": "12", "adr_voie": "RUE DES FILAOS",
                            "destination": "2", "famille": "locaux"})})
    geocode_par_adresse(db_session, log=lambda *_: None)
    r = db_session.execute(text(
        "SELECT geom IS NOT NULL AS ok, raw->>'geoloc' AS geoloc "
        "FROM sitadel_permits WHERE permit_id = '__test_r30__'")).mappings().first()
    assert r["ok"], "le permis doit être rattaché par son adresse"
    assert r["geoloc"] and "adresse" in r["geoloc"]     # la nature de la position est DITE


def test_r30_destination_hotel_servie(db_session):
    from labuse.api.modules import _DESTINATION_LABELS
    assert _DESTINATION_LABELS["2"] == "hôtels"          # dictionnaire Sitadel3 officiel (SDES)
    assert _DESTINATION_LABELS["9"].startswith("service public")
