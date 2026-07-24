"""Wave ANC & Végétation, Lot A — agrégation EGOUL, proba modulée, zonages, signal.

Aucun réseau : l'INSEE est rejoué depuis un zip de fixture, le GPU n'est pas appelé
(les zonages sont insérés directement dans spatial_layers comme le ferait l'ingestion).
"""
from __future__ import annotations

import csv
import io
import zipfile

import pytest
from sqlalchemy import text

from labuse.config import load_yaml_config
from labuse.ingestion.anc import (
    DDL,
    _appliquer_zonages,
    _classer_libelle,
    compute_proba,
    ingest_insee_egoul,
    signal_mutation,
)

# ───────────────────────── pur : classification des libellés GPU ─────────────────────────

_CLS = load_yaml_config("anc_vegetation")["anc"]["gpu"]["classification"]


def test_classer_libelle_constate():
    # libellés RÉELS constatés au GPU le 11/07/2026 (4 communes)
    assert _classer_libelle("Assainissement non collectif", _CLS) == "anc"
    assert _classer_libelle("Zonage d'assainissement Autonome", _CLS) == "anc"
    assert _classer_libelle("Zone d'assainissement - long terme", _CLS) == "anc"
    assert _classer_libelle("Zone d'assainissement - actuel", _CLS) == "collectif"
    assert _classer_libelle("Zonage assainissement - Semi-collectif", _CLS) == "collectif"
    assert _classer_libelle("Zonage d'assainissement Collectif", _CLS) == "collectif"
    # pollution typeinf 19 (L'Étang-Salé) : captages → ignorés
    assert _classer_libelle("Périmètre de captage rapproché : Marengo", _CLS) is None


def test_classer_non_collectif_avant_collectif():
    # « non collectif » contient « collectif » : l'ordre des règles est structurel
    assert _classer_libelle("assainissement NON COLLECTIF", _CLS) == "anc"


# ───────────────────────── db ─────────────────────────

def _parcel(db, idu, commune, wkt2975, surface=500.0):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES (:i, :c, :s,"
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326))"
        " ON CONFLICT (idu) DO NOTHING"),
        {"i": idu, "c": commune, "s": surface, "w": wkt2975})
    db.execute(text(
        "UPDATE parcels SET centroid = ST_Centroid(geom) WHERE idu = :i"), {"i": idu})


def _sq(x, y, d=20):
    return f"POLYGON(({x} {y}, {x + d} {y}, {x + d} {y + d}, {x} {y + d}, {x} {y}))"


@pytest.fixture()
def anc_env(db_session):
    s = db_session
    s.execute(text(DDL))
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_residuel_bati (
          idu varchar(14) PRIMARY KEY, commune varchar(80), zone varchar(40),
          emprise_batie_m2 double precision, hauteur_bati_m double precision,
          emprise_max_m2 double precision, emprise_residuelle_m2 double precision,
          hauteur_max_m double precision, surelevation_possible boolean,
          confiance varchar(10), updated_at timestamptz DEFAULT now())
    """))
    # trois parcelles bâties à Saint-Paul : une dans l'IRIS-test, une loin de toute
    # zone U (bonus), une couverte par un zonage officiel ANC
    _parcel(s, "97415000AA0001", "Saint-Paul", _sq(340000, 7650000))
    _parcel(s, "97415000AA0002", "Saint-Paul", _sq(342000, 7650000))
    _parcel(s, "97415000AA0003", "Saint-Paul", _sq(344000, 7650000))
    for idu in ("97415000AA0001", "97415000AA0002", "97415000AA0003"):
        s.execute(text(
            "INSERT INTO parcel_residuel_bati (idu, emprise_batie_m2) VALUES (:i, 120)"
            " ON CONFLICT (idu) DO NOTHING"), {"i": idu})
    # taux : IRIS couvrant SEULEMENT la parcelle 1 (60 %), commune 40 %
    s.execute(text("DELETE FROM anc_maille_taux"))
    s.execute(text("""
        INSERT INTO anc_maille_taux (maille, code, insee, taux_non_racc, n_logements, millesime)
        VALUES ('iris', '974150101', '97415', 60, 1000, 'RP2022'),
               ('commune', '97415', '97415', 40, 5000, 'RP2022')
    """))
    s.execute(text(
        "DELETE FROM spatial_layers WHERE kind IN ('iris_insee', 'zonage_assainissement')"))
    s.execute(text("""
        INSERT INTO spatial_layers (kind, subtype, geom, commune)
        VALUES ('iris_insee', '974150101',
                ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326), 'Saint-Paul')
    """), {"w": _sq(339900, 7649900, 300)})
    # zone U à < 100 m des parcelles 1 et 3, LOIN de la 2 (→ bonus pour la 2)
    for x in (340050, 344050):
        s.execute(text("""
            INSERT INTO spatial_layers (kind, subtype, geom, commune)
            VALUES ('plu_gpu_zone', 'U',
                    ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326), 'Saint-Paul')
        """), {"w": _sq(x, 7650050, 30)})
    # zonage officiel ANC couvrant la parcelle 3
    s.execute(text("""
        INSERT INTO spatial_layers (kind, subtype, name, geom, commune)
        VALUES ('zonage_assainissement', 'anc', 'Assainissement non collectif',
                ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326), 'Saint-Paul')
    """), {"w": _sq(343900, 7649900, 300)})
    s.execute(text("DELETE FROM parcel_anc"))
    s.flush()
    return s


@pytest.mark.db
def test_proba_iris_commune_bonus_et_zonage(anc_env):
    s = anc_env
    res = compute_proba(s, log=lambda *_: None)
    assert res["parcelles"] == 3
    rows = {r[0]: r for r in s.execute(text(
        "SELECT idu, proba_anc, zone_anc, source FROM parcel_anc ORDER BY idu")).all()}
    # parcelle 1 : taux IRIS 60, zone U proche → pas de bonus
    assert rows["97415000AA0001"][1] == 60
    assert rows["97415000AA0001"][3] == "proba_insee"
    # parcelle 2 : repli commune 40 + bonus 15 (aucune zone U à < 100 m)
    assert rows["97415000AA0002"][1] == 55
    # parcelle 3 : zonage officiel ANC (proba conservée : commune 40, U proche)
    assert rows["97415000AA0003"][2] == "anc"
    assert rows["97415000AA0003"][3] == "zonage_officiel"
    assert rows["97415000AA0003"][1] == 40


@pytest.mark.db
def test_proba_sans_plu_pas_de_bonus(db_session):
    """Commune SANS zonage PLU ingéré : le bonus « loin de toute zone U » ne
    s'applique pas (on ne surestime pas toute la commune)."""
    s = db_session
    s.execute(text(DDL))
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS parcel_residuel_bati (
          idu varchar(14) PRIMARY KEY, commune varchar(80), zone varchar(40),
          emprise_batie_m2 double precision, hauteur_bati_m double precision,
          emprise_max_m2 double precision, emprise_residuelle_m2 double precision,
          hauteur_max_m double precision, surelevation_possible boolean,
          confiance varchar(10), updated_at timestamptz DEFAULT now())
    """))
    _parcel(s, "97421000AA0001", "Salazie", _sq(360000, 7660000))
    s.execute(text(
        "INSERT INTO parcel_residuel_bati (idu, emprise_batie_m2) VALUES (:i, 120)"
        " ON CONFLICT (idu) DO NOTHING"), {"i": "97421000AA0001"})
    s.execute(text("DELETE FROM anc_maille_taux"))
    s.execute(text("""
        INSERT INTO anc_maille_taux (maille, code, insee, taux_non_racc, n_logements, millesime)
        VALUES ('commune', '97421', '97421', 97.8, 2700, 'RP2022')
    """))
    s.execute(text("DELETE FROM spatial_layers WHERE kind = 'plu_gpu_zone'"
                   " AND commune = 'Salazie'"))
    s.execute(text("DELETE FROM parcel_anc"))
    compute_proba(s, log=lambda *_: None)
    proba = s.execute(text(
        "SELECT proba_anc FROM parcel_anc WHERE idu = '97421000AA0001'")).scalar_one()
    assert proba == 95   # 97.8 sans bonus, plafonné à 95


@pytest.mark.db
def test_signal_anc_mutation_fenetre_ancree(anc_env):
    s = anc_env
    compute_proba(s, log=lambda *_: None)
    _appliquer_zonages(s)
    # mutations : récente sur la parcelle 3 (zone ANC), VIEILLE sur la 1 (proba 60 < 70)
    s.execute(text("DELETE FROM dvf_mutations_parcelle"))
    s.execute(text("""
        INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, valeur_fonciere,
                                            id_parcelle, millesime)
        VALUES ('m1', '2025-11-15', 250000, '97415000AA0003', 2025),
               ('m2', '2024-01-10', 180000, '97415000AA0001', 2024),
               ('m3', '2025-12-31', 300000, '97415000AA0001', 2025)
    """))
    n = signal_mutation(s)
    # parcelle 3 : zone ANC + mutation < 12 mois du flux → signal.
    # parcelle 1 : proba 60 < 70 et pas de zone officielle → PAS de signal malgré m3.
    assert n == 1
    payload = s.execute(text("""
        SELECT sg.payload FROM parcel_signals sg JOIN parcels p ON p.id = sg.parcel_id
        WHERE sg.signal_type = 'anc_mutation' AND p.idu = '97415000AA0003'
    """)).scalar_one()
    assert payload["zone_anc"] == "anc"
    assert "L.271-4" in payload["mecanisme"]          # le délai d'1 an est au CCH, pas au CSP


# ───────────────────────── db : agrégation EGOUL depuis un zip fixture ─────────────────────────

@pytest.mark.db
def test_ingest_egoul_fixture(db_session, tmp_path):
    rows = [
        # métropole : ignorée
        {"COMMUNE": "75056", "IRIS": "751010101", "EGOUL": "Z", "IPONDL": "1.0"},
        # Saint-Paul IRIS A : 2 raccordés (w=1), 1 fosse (w=2) → 50 % non raccordé
        {"COMMUNE": "97415", "IRIS": "974150101", "EGOUL": "1", "IPONDL": "1.0"},
        {"COMMUNE": "97415", "IRIS": "974150101", "EGOUL": "1", "IPONDL": "1.0"},
        {"COMMUNE": "97415", "IRIS": "974150101", "EGOUL": "2", "IPONDL": "2.0"},
        # hors résidence principale : ignorée
        {"COMMUNE": "97415", "IRIS": "974150101", "EGOUL": "Y", "IPONDL": "1.0"},
        # IRIS non diffusé (Z) : compte au niveau commune seulement
        {"COMMUNE": "97415", "IRIS": "ZZZZZZZZZ", "EGOUL": "4", "IPONDL": "1.0"},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["COMMUNE", "IRIS", "EGOUL", "IPONDL"], delimiter=";")
    w.writeheader()
    w.writerows(rows)
    zpath = tmp_path / "rp.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("FD_LOGEMT_2022.csv", buf.getvalue())
    res = ingest_insee_egoul(db_session, fichier=str(zpath), log=lambda *_: None)
    assert res["logements_974"] == 4    # EGOUL ∈ 1-4 : Y (hors RP) exclu
    taux = {(m, c): t for m, c, t in db_session.execute(text(
        "SELECT maille, code, taux_non_racc FROM anc_maille_taux")).all()}
    assert taux[("iris", "974150101")] == 50.0
    assert taux[("commune", "97415")] == 60.0        # (2 + 1) / 5 pondéré


# (test_presets_anc_valides + test_mention_legale_delai_un_an_au_cch retirés avec le
#  spin-off « Vues » — M12 Lot C-bis : ils validaient le preset ANC et sa mention légale
#  du moteur de segments, parti avec « Vues ». Le calcul ANC lui-même reste couvert
#  ci-dessus. Archivés dans docs/mandats/M12_LOT_C_BIS.md.)
