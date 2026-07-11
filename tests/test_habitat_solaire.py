"""Tests du mandat Habitat Solaire — schéma, Lot 5 (flags), Lot 1 (score/percentile)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

#: parcelle de test : carré ~100 m autour de (55.45, -21.30)
_POLY = ("POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995, "
         "55.4495 -21.2995, 55.4495 -21.3005))")


@pytest.fixture
def parcelle(db_session):
    from labuse.ingestion.habitat_solaire_schema import ensure_schema

    ensure_schema(db_session)
    db_session.execute(text(
        f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
            VALUES ('97416000ZZ0001', 'Saint-Pierre', 'ZZ', '0001', 11000,
                    ST_GeomFromText('{_POLY}', 4326),
                    ST_Transform(ST_GeomFromText('{_POLY}', 4326), 2975))"""))
    return "97416000ZZ0001"


def test_schema_idempotent(db_session):
    from labuse.ingestion.habitat_solaire_schema import ensure_schema

    ensure_schema(db_session)
    ensure_schema(db_session)  # rejouable sans erreur
    for t in ("solar_grid", "parcel_solar", "parkings_aper", "pv_registry",
              "grid_capacity", "solar_api_cache"):
        assert db_session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() >= 0


def test_flag_amiante_dpe(db_session, parcelle):
    from labuse.ingestion.solaire_flags import compute_flag_amiante

    db_session.execute(text(
        "INSERT INTO dpe_records (numero_dpe, annee_construction, parcelle_idu)"
        " VALUES ('DPETEST1', 1985, :idu)"), {"idu": parcelle})
    assert compute_flag_amiante(db_session) == 1
    flag = db_session.execute(text(
        "SELECT flag_amiante FROM parcel_solar WHERE idu = :idu"), {"idu": parcelle}).scalar_one()
    assert flag is True


def test_azimut_bati_ns(db_session, parcelle):
    """Bâtiment allongé nord-sud → azimut du grand axe ≈ 0° (mod 180), confiance haute."""
    from labuse.ingestion.solaire_flags import compute_azimut

    db_session.execute(text(
        """INSERT INTO spatial_layers (kind, subtype, name, geom)
           VALUES ('batiment', 'Indifférenciée', 'test',
                   ST_GeomFromText(:wkt, 4326))"""),
        {"wkt": ("POLYGON((55.4499 -21.3003, 55.45 -21.3003, 55.45 -21.2998, "
                 "55.4499 -21.2998, 55.4499 -21.3003))")})
    assert compute_azimut(db_session) == 1
    az, conf = db_session.execute(text(
        "SELECT azimut_bati_deg, azimut_confiance FROM parcel_solar WHERE idu = :idu"),
        {"idu": parcelle}).one()
    # grand axe N-S : azimut mod 180 proche de 0 ou de 180
    assert min(az, 180 - az) < 15
    assert conf == "haute"


def test_proba_proprio_fallback_commune(db_session, parcelle):
    """Sans carreau Filosofi : repli sur le taux communal ; mutation maison < 24 mois → +15."""
    from labuse.ingestion.solaire_flags import compute_proba_proprio_occupant

    # tables créées hors repo (mandats précédents) : stubs minimaux pour la base de test
    db_session.execute(text(
        """CREATE TABLE IF NOT EXISTS commune_insee_logement
             (insee varchar(5), commune text, proprietaires_pct numeric);
           CREATE TABLE IF NOT EXISTS filosofi_carreaux_200m
             (fid serial, geom geometry(Polygon, 2975), men numeric, men_prop numeric);
           CREATE TABLE IF NOT EXISTS dvf_mutations_parcelle
             (id bigserial, id_mutation text, date_mutation date, id_parcelle varchar(14),
              type_local text, millesime smallint)"""))
    db_session.execute(text(
        "INSERT INTO commune_insee_logement (insee, commune, proprietaires_pct)"
        " VALUES ('97416', 'Saint-Pierre', 50)"))
    db_session.execute(text(
        "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, id_parcelle,"
        " type_local, millesime) VALUES ('m1', CURRENT_DATE - 100, :idu, 'Maison', 2026)"),
        {"idu": parcelle})
    assert compute_proba_proprio_occupant(db_session) == 1
    score = db_session.execute(text(
        "SELECT proba_proprio_occupant FROM parcel_solar WHERE idu = :idu"),
        {"idu": parcelle}).scalar_one()
    assert score == 65  # 50 (commune) + 15 (mutation récente)


def test_conso_facture_estimee(db_session, parcelle):
    """Modèle additif : baseline commune × ratio surface, facture arrondie à la dizaine."""
    from labuse.ingestion.solaire_conso import DDL_BASELINE, compute_conso

    db_session.execute(text(DDL_BASELINE))
    db_session.execute(text(
        """CREATE TABLE IF NOT EXISTS parcel_residuel_bati
             (idu varchar(14) PRIMARY KEY, emprise_batie_m2 double precision)"""))
    db_session.execute(text(
        "INSERT INTO conso_baseline_commune (insee, commune, annee, kwh_an_logement)"
        " VALUES ('97416', 'Saint-Pierre', 2024, 3000)"))
    db_session.execute(text(
        "INSERT INTO parcel_residuel_bati (idu, emprise_batie_m2) VALUES (:idu, 100)"),
        {"idu": parcelle})
    db_session.execute(text(
        """INSERT INTO spatial_layers (kind, name, geom, attrs)
           VALUES ('batiment', 'test-res', ST_GeomFromText(:wkt, 4326),
                   '{"usage": "Résidentiel"}'::jsonb)"""),
        {"wkt": ("POLYGON((55.4499 -21.3003, 55.45 -21.3003, 55.45 -21.2998, "
                 "55.4499 -21.2998, 55.4499 -21.3003))")})
    res = compute_conso(db_session)
    assert res["parcelles"] == 1
    conso, facture = db_session.execute(text(
        "SELECT conso_est_kwh_an, facture_est_eur_mois FROM parcel_solar WHERE idu = :idu"),
        {"idu": parcelle}).one()
    assert conso == 3000  # 100 m² × 0.9 = 90 m² = surface_ref → ratio 1.0
    assert facture == round(3000 * 0.25 / 12 / 10) * 10 == 60
    assert facture % 10 == 0


def test_score_percentile_et_ombrage(db_session, parcelle):
    """score_solaire = percentile île ; flag_topo_ombrage sous 80 % de la médiane commune."""
    from labuse.ingestion.solaire_pvgis import interpolate

    # 3 parcelles supplémentaires de la même commune, autour de la première
    for i, (dx, prod) in enumerate([(0.002, 1400.0), (0.004, 1450.0), (0.006, 1500.0)], start=2):
        poly = (f"POLYGON(({55.4495 + dx} -21.3005, {55.4505 + dx} -21.3005, "
                f"{55.4505 + dx} -21.2995, {55.4495 + dx} -21.2995, {55.4495 + dx} -21.3005))")
        db_session.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
                VALUES ('97416000ZZ000{i}', 'Saint-Pierre', 'ZZ', '000{i}', 11000,
                        ST_GeomFromText('{poly}', 4326),
                        ST_Transform(ST_GeomFromText('{poly}', 4326), 2975))"""))
        db_session.execute(text(
            """INSERT INTO solar_grid (geom, prod_spec_kwh_kwc, source)
               VALUES (ST_SetSRID(ST_Point(:x, -21.30), 4326), :p, 'test')"""),
            {"x": 55.45 + dx, "p": prod})
    # point de grille SOMBRE sur la parcelle 1 (fond de cirque simulé : < 80 % de la médiane)
    db_session.execute(text(
        """INSERT INTO solar_grid (geom, prod_spec_kwh_kwc, source)
           VALUES (ST_SetSRID(ST_Point(55.45, -21.30), 4326), 900.0, 'test')"""))
    db_session.execute(text("UPDATE parcels SET centroid = ST_Centroid(geom)"))
    res = interpolate(db_session, log=lambda *_: None)
    assert res["parcelles"] == 4
    rows = dict(db_session.execute(text(
        "SELECT idu, score_solaire FROM parcel_solar")).all())
    assert rows["97416000ZZ0001"] == 0          # la plus sombre
    assert max(rows.values()) == 100            # la plus claire
    flag = db_session.execute(text(
        "SELECT flag_topo_ombrage FROM parcel_solar WHERE idu = '97416000ZZ0001'")).scalar_one()
    assert flag is True
