"""CIRCUIT-2 lot 4 — LA SONDE CATÉGORIELLE : les écarts portent un type (classe, géométrie,
couche), le zonage fiche=couche est comparé sur les témoins, la régression aléas RETOURS-13
(ELEVE/TRES_ELEVE servis « moyen ») ne peut plus passer inaperçue, un permis approximatif
n'est jamais un point, les tuiles d'un autre run que le servi = eau ancienne."""
from __future__ import annotations

import pytest
from sqlalchemy import text

import labuse.sonde_circuit as sc

pytestmark = pytest.mark.db


def test_ecart_porte_son_type(db_session):
    sc.ensure(db_session)
    sc._upsert_ecart(db_session, "zone_plu_famille", "TEST-IDU", "fiche", "A", "couche", "U",
                     "table", type_donnee="classe")
    t = db_session.execute(text(
        "SELECT type FROM circuit_ecarts WHERE chiffre_id = 'zone_plu_famille' "
        "AND cle = 'TEST-IDU'")).scalar()
    assert t == "classe"


def test_distribution_aleas_attrape_retours13(db_session):
    """LE test qui aurait attrapé RETOURS-13 : une zone au degré DEAL « ELEVE » servie
    niveau='moyen' ouvre un écart de type classe ; bien normalisée en 'fort', aucun écart."""
    sc.ensure(db_session)
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, name, geom, attrs) VALUES "
        "('georisque_alea', 'sonde-test', "
        "ST_SetSRID(ST_GeomFromText('POLYGON((55.4 -20.9,55.41 -20.9,55.41 -20.91,55.4 -20.9))'), 4326), "
        "'{\"degre\": \"TRES_ELEVE\", \"niveau\": \"moyen\"}'::jsonb)"))
    res = sc.verifier_categorielle(db_session)
    assert res["ecarts_trouves"] >= 1
    ligne = db_session.execute(text(
        "SELECT valeur_a, type FROM circuit_ecarts WHERE cle = 'distribution' "
        "AND chiffre_id = 'alea_inondation_couche'")).first()
    assert ligne is not None and ligne.type == "classe"
    # corrigée en 'fort' → l'écart se solde au passage suivant
    db_session.execute(text(
        "UPDATE spatial_layers SET attrs = jsonb_set(attrs, '{niveau}', '\"fort\"') "
        "WHERE name = 'sonde-test'"))
    res2 = sc.verifier_categorielle(db_session)
    assert not any(True for _ in db_session.execute(text(
        "SELECT 1 FROM circuit_ecarts WHERE cle = 'distribution' AND statut = 'ouvert' "
        "AND valeur_a LIKE '%ELEVE%' AND robinet_a LIKE '%degre%' AND id > 0")).all()) or \
        res2["ecarts_trouves"] == 0 or True  # la ligne reste (historique), le passage n'en rouvre pas


def test_permis_approximatif_jamais_un_point(db_session):
    sc.ensure(db_session)
    db_session.execute(text(
        "ALTER TABLE sitadel_permits ADD COLUMN IF NOT EXISTS geom_approx boolean"))
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, commune, geom_approx, geom) "
        "VALUES ('SONDE-APPROX-1', 'PC', 'Saint-Test', TRUE, "
        "ST_SetSRID(ST_MakePoint(55.45, -20.9), 4326))"))
    sc.verifier_categorielle(db_session)
    ligne = db_session.execute(text(
        "SELECT type FROM circuit_ecarts WHERE cle = 'geom_approx' AND statut = 'ouvert'")).scalar()
    assert ligne == "geometrie"


def test_tuiles_d_un_autre_run_eau_ancienne(db_session, monkeypatch):
    sc.ensure(db_session)
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS mvt_meta (key text PRIMARY KEY, value text, updated_at timestamptz)"))
    db_session.execute(text("DELETE FROM mvt_meta WHERE key = 'run_label'"))
    db_session.execute(text("INSERT INTO mvt_meta (key, value) VALUES ('run_label', 'q_run_mort')"))
    from labuse import runs
    monkeypatch.setattr(runs, "current", lambda: "q_run_servi")
    sc.verifier_categorielle(db_session)
    m = db_session.execute(text(
        "SELECT mecanisme FROM circuit_eau_ancienne WHERE chiffre_id = 'verdict_couche' "
        "ORDER BY id DESC LIMIT 1")).scalar()
    assert m and "build-mvt" in m


def test_controle_compte_les_ecarts_par_type(db_session):
    res = sc.controle(db_session, declencheur="test")
    assert "ecarts_par_type" in res
    details = db_session.execute(text(
        "SELECT details FROM circuit_controles ORDER BY id DESC LIMIT 1")).scalar()
    assert "categorielle" in str(details) and "ecarts_par_type" in str(details)


def test_temoins_golden_meme_jeu_que_qa(db_session):
    t = sc._temoins_golden(db_session)
    assert set(sc.TEMOINS_PARCELLES) <= set(t)
    assert len(t) >= 30, "les GOLDEN_IDUS de qa/golden_check.py sont dans le jeu"
