"""RNIC copropriétés — règle RGPD (syndic non pro jamais nominatif) + rattachement proche_20m.

Mandat Wave copro (re-scopé 11/07/2026) : `syndic_nom`/`syndic_siret` UNIQUEMENT si
`syndic_type='professionnel'` — y compris dans `raw` (clés représentant légal retirées).
"""
from __future__ import annotations

import csv

import pytest
from sqlalchemy import text

from labuse.ingestion.rnic import complements, ingest_rnic, purge_rgpd

_COLS = ["numero_d_immatriculation", "code_officiel_departement", "code_officiel_commune",
         "nom_officiel_commune", "commune_adresse_de_reference", "adresse_de_reference",
         "nom_d_usage_de_la_copropriete", "nombre_total_de_lots",
         "nombre_de_lots_a_usage_d_habitation", "periode_de_construction",
         "type_de_syndic_benevole_professionnel_non_connu",
         "raison_sociale_du_representant_legal", "siret_du_representant_legal",
         "mandat_en_cours_dans_la_copropriete", "reference_cadastrale_1",
         "reference_cadastrale_2", "reference_cadastrale_3", "long", "lat"]


def _csv_974(tmp_path, rows):
    path = tmp_path / "rnic.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in _COLS})
    return str(path)


def _row(num, syndic_type, nom="SYNDIC SARL", siret="12345678900011", **kw):
    base = {"numero_d_immatriculation": num, "code_officiel_departement": "974",
            "code_officiel_commune": "97415", "nom_officiel_commune": "Saint-Paul",
            "adresse_de_reference": "12 r des Bougainvilliers 97460 Saint-Paul",
            "nombre_total_de_lots": "24", "nombre_de_lots_a_usage_d_habitation": "20",
            "periode_de_construction": "1975-1993",
            "type_de_syndic_benevole_professionnel_non_connu": syndic_type,
            "raison_sociale_du_representant_legal": nom,
            "siret_du_representant_legal": siret,
            "mandat_en_cours_dans_la_copropriete": "oui"}
    base.update(kw)
    return base


@pytest.mark.db
def test_rgpd_syndic_non_pro_jamais_nominatif(db_session, tmp_path):
    path = _csv_974(tmp_path, [
        _row("AA0000001", "professionnel"),
        _row("AA0000002", "bénévole", nom="Jean Payet"),
        _row("AA0000003", "non connu", nom="Marie Hoarau"),
        _row("ZZ0000001", "bénévole", code_officiel_departement="75"),  # hors 974 : filtré
    ])
    res = ingest_rnic(db_session, path, log=lambda *_: None)
    assert res["copros_974"] == 3

    rows = {r[0]: r for r in db_session.execute(text(
        "SELECT numero_immatriculation, syndic_type, syndic_nom, syndic_siret, "
        "raw ? 'raison_sociale_du_representant_legal' AS raw_nom "
        "FROM rnic_coproprietes")).all()}
    assert rows["AA0000001"][2] == "SYNDIC SARL" and rows["AA0000001"][3]  # pro : nominatif OK
    for num in ("AA0000002", "AA0000003"):                                # non pro : JAMAIS
        assert rows[num][2] is None and rows[num][3] is None and not rows[num][4]

    # critère d'acceptation du mandat : 0 syndic non professionnel nominatif
    assert db_session.execute(text(
        "SELECT count(*) FROM rnic_coproprietes "
        "WHERE syndic_type <> 'professionnel' AND syndic_nom IS NOT NULL")).scalar() == 0


@pytest.mark.db
def test_purge_rgpd_sur_base_existante(db_session):
    """La purge nettoie des lignes historiques ingérées AVANT la règle (nom + raw)."""
    db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS rnic_coproprietes (
          numero_immatriculation varchar(12) PRIMARY KEY, insee varchar(5), commune varchar(64),
          nom_usage text, adresse text, nb_lots_total integer, nb_lots_habitation integer,
          periode_construction varchar(24), syndic_type varchar(16), syndic_nom text,
          syndic_siret varchar(14), mandat_en_cours boolean,
          idu_codes jsonb NOT NULL DEFAULT '[]', parcelle_idu varchar(14),
          rattachement varchar(12), geom geometry(Point, 4326), raw jsonb,
          ingested_at timestamptz NOT NULL DEFAULT now())"""))
    db_session.execute(text("""
        INSERT INTO rnic_coproprietes (numero_immatriculation, syndic_type, syndic_nom, raw)
        VALUES ('AA0000010', 'bénévole', 'Jean Payet',
                '{"raison_sociale_du_representant_legal": "Jean Payet", "commune": "Saint-Paul"}'),
               ('AA0000011', 'professionnel', 'SYNDIC SARL',
                '{"raison_sociale_du_representant_legal": "SYNDIC SARL"}')
        ON CONFLICT (numero_immatriculation) DO NOTHING"""))
    assert purge_rgpd(db_session) == 1
    ben = db_session.execute(text(
        "SELECT syndic_nom, raw FROM rnic_coproprietes WHERE numero_immatriculation='AA0000010'")).first()
    assert ben[0] is None and "raison_sociale" not in str(ben[1]) and ben[1]["commune"] == "Saint-Paul"
    pro = db_session.execute(text(
        "SELECT syndic_nom FROM rnic_coproprietes WHERE numero_immatriculation='AA0000011'")).first()
    assert pro[0] == "SYNDIC SARL"          # le pro reste nominatif (personne morale)
    assert purge_rgpd(db_session) == 0      # idempotent


@pytest.mark.db
def test_rattachement_proche_20m(db_session, tmp_path):
    """Point RNIC sur la voirie (hors polygone) mais < 20 m de la parcelle → 'proche_20m'."""
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "('97415000AB0001', 'Saint-Paul', "
        " ST_SetSRID(ST_GeomFromText('POLYGON((55.290 -21.010, 55.292 -21.010, 55.292 -21.008, "
        "  55.290 -21.008, 55.290 -21.010))'),4326), "
        " ST_Transform(ST_SetSRID(ST_GeomFromText('POLYGON((55.290 -21.010, 55.292 -21.010, "
        "  55.292 -21.008, 55.290 -21.008, 55.290 -21.010))'),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"))
    # ~55.2921 : à ~10 m à l'est du bord de parcelle ; 55.35 : à plusieurs km.
    path = _csv_974(tmp_path, [
        _row("AA0000020", "professionnel", long="55.29215", lat="-21.009"),
        _row("AA0000021", "professionnel", long="55.35", lat="-21.009"),
    ])
    ingest_rnic(db_session, path, log=lambda *_: None)
    res = complements(db_session, log=lambda *_: None)
    rows = {r[0]: r[1:] for r in db_session.execute(text(
        "SELECT numero_immatriculation, parcelle_idu, rattachement FROM rnic_coproprietes "
        "WHERE numero_immatriculation IN ('AA0000020','AA0000021')")).all()}
    assert rows["AA0000020"] == ("97415000AB0001", "proche_20m")
    assert rows["AA0000021"] == (None, "aucun")
    assert res["rattachement"].get("proche_20m", 0) >= 1
