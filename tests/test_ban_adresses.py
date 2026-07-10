"""Tests Lot 1 (wave-adresses) : ingestion BAN → adresses ↔ parcelles + exports BAN."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

#: en-tête officiel de l'export CSV BAN (delimiter ;)
_HEADER = ("id;id_fantoir;numero;rep;nom_voie;code_postal;code_insee;nom_commune;"
           "code_insee_ancienne_commune;nom_ancienne_commune;x;y;lon;lat;type_position;"
           "alias;nom_ld;libelle_acheminement;nom_afnor;source_position;source_nom_voie;"
           "certification_commune;cad_parcelles")

#: parcelle de test : carré ~100 m autour de (55.45, -21.30) — zone de validité 2975
_POLY = "POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995, 55.4495 -21.2995, 55.4495 -21.3005))"


@pytest.fixture
def parcelle(db_session):
    db_session.execute(text(
        f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
            VALUES ('97416000ZZ0001', 'Saint-Pierre', 'ZZ', '0001', 11000,
                    ST_GeomFromText('{_POLY}', 4326),
                    ST_Transform(ST_GeomFromText('{_POLY}', 4326), 2975))"""))
    return "97416000ZZ0001"


def _csv(tmp_path, rows: list[str]):
    p = tmp_path / "ban_test.csv"
    p.write_text(_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def test_ingest_ban_rattachement(db_session, parcelle, tmp_path):
    """Point dans la parcelle → 'parcelle' ; point à ~12 m dehors → 'proche_20m' ;
    index inverse peuplé ; cad_parcelles alimente l'assiette."""
    from labuse.ingestion.ban_adresses import ingest_ban

    rows = [
        # dans la parcelle
        "97416_test_1;;12;;Rue des Tests;97410;97416;Saint-Pierre;;;0;0;55.4500;-21.3000;"
        "entrée;;;SAINT PIERRE;RUE DES TESTS;commune;commune;1;",
        # ~12 m à l'est de la limite, SANS cad_parcelles → plus proche parcelle < 20 m
        "97416_test_2;;14;bis;Rue des Tests;97410;97416;Saint-Pierre;;;0;0;55.45062;-21.3000;"
        "entrée;;;SAINT PIERRE;RUE DES TESTS;commune;commune;1;",
        # ~200 m dehors mais assiette cad_parcelles valide → 'ban_cad'
        "97416_test_4;;16;;Rue des Tests;97410;97416;Saint-Pierre;;;0;0;55.4525;-21.3000;"
        "entrée;;;SAINT PIERRE;RUE DES TESTS;commune;commune;1;97416000ZZ0001",
        # sans coordonnées → ignorée
        "97416_test_3;;1;;Rue Vide;97410;97416;Saint-Pierre;;;0;0;;;entrée;;;X;X;commune;commune;1;",
    ]
    res = ingest_ban(db_session, _csv(tmp_path, rows))
    assert res["adresses"] == 3 and res["liees"] == 3

    ratt = dict(db_session.execute(text(
        "SELECT id_ban, rattachement FROM adresses")).all())
    assert ratt["97416_test_1"] == "parcelle"
    assert ratt["97416_test_2"] == "proche_20m"
    assert ratt["97416_test_4"] == "ban_cad"
    # index inverse : les deux adresses desservent la parcelle (point + assiette cad)
    inv = db_session.execute(text(
        "SELECT id_ban, source FROM adresse_parcelles WHERE idu = :idu ORDER BY id_ban"),
        {"idu": parcelle}).all()
    assert {i for i, _ in inv} == {"97416_test_1", "97416_test_2", "97416_test_4"}


def test_export_colonnes_ban(db_session, parcelle, tmp_path):
    """L'adresse BAN normalisée est prépendue à tout export ; sans la table → omise."""
    from labuse.ingestion.ban_adresses import ingest_ban
    from labuse.segments import engine as seg_engine
    from labuse.segments.registry import reset_availability_cache

    ingest_ban(db_session, _csv(tmp_path, [
        "97416_test_1;;12;;Rue des Tests;97410;97416;Saint-Pierre;;;0;0;55.4500;-21.3000;"
        "entrée;;;SAINT PIERRE;RUE DES TESTS;commune;commune;1;"]))
    reset_availability_cache()
    q = seg_engine.build(db_session, [], "surface_desc", colonnes_export=["surface_m2"])
    assert [c for c, _ in q.export_cols][:4] == [
        "adresse_numero", "adresse_voie", "adresse_cp", "adresse_ville"]
    row = next(iter(seg_engine.run_export_rows(db_session, q, limit=1)))
    assert row["adresse_voie"] == "Rue des Tests" and row["adresse_numero"] == "12"

    # résilience : table simulée absente → colonnes BAN omises, jamais d'erreur
    q2 = seg_engine.build(db_session, [], "surface_desc", colonnes_export=["surface_m2"],
                          simulate_missing=frozenset({"adresses"}))
    assert "adresse_voie" not in [c for c, _ in q2.export_cols]
    reset_availability_cache()


def test_norm_voie_abreviations():
    from labuse.ingestion.ban_adresses import _norm_voie

    assert _norm_voie("che Louis Fontaine") == "chemin louis fontaine"
    assert _norm_voie("R Alexis de Villeneuve") == "rue alexis de villeneuve"
    assert _norm_voie("Rue de l'Étang-Salé") == "rue de l etang sale"


def test_rattacher_copros_par_adresse(db_session, parcelle, tmp_path):
    """Copro RNIC sans parcelle + adresse abrégée → rattachée via la table adresses."""
    from labuse.ingestion.ban_adresses import ingest_ban, rattacher_copros_par_adresse
    from labuse.ingestion.rnic import DDL as DDL_RNIC

    db_session.execute(DDL_RNIC)
    ingest_ban(db_session, _csv(tmp_path, [
        "97416_test_1;;12;;Rue des Tests;97410;97416;Saint-Pierre;;;0;0;55.4500;-21.3000;"
        "entrée;;;SAINT PIERRE;RUE DES TESTS;commune;commune;1;"]))
    db_session.execute(text(
        """INSERT INTO rnic_coproprietes (numero_immatriculation, insee, commune, adresse,
                                          rattachement)
           VALUES ('TEST-COPRO-1', '97416', 'Saint-Pierre',
                   '12 r des tests 97410 Saint-Pierre', 'aucun')"""))
    res = rattacher_copros_par_adresse(db_session)
    assert res["liees"] == 1
    idu = db_session.execute(text(
        "SELECT parcelle_idu FROM rnic_coproprietes WHERE numero_immatriculation = 'TEST-COPRO-1'"
    )).scalar()
    assert idu == parcelle
