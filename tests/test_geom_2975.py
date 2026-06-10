"""Robustesse géométrique : geom_2975 (trigger ST_MakeValid) — durable au rebuild.

Sécurise l'ingestion PPR : une assiette GPU auto-sécante NE DOIT PAS casser la cascade
(GEOS « side location conflict »). Tests DB (skippés si PostGIS injoignable)."""
from sqlalchemy import text


def test_geom_2975_genere_a_l_insertion(db_session):
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, geom) "
        "VALUES ('ppr','t_ok', ST_GeomFromText(:w, 4326))"),
        {"w": "POLYGON((55.30 -21.00,55.32 -21.00,55.32 -20.98,55.30 -20.98,55.30 -21.00))"})
    ok, valid, srid = db_session.execute(text(
        "SELECT geom_2975 IS NOT NULL, ST_IsValid(geom_2975), ST_SRID(geom_2975) "
        "FROM spatial_layers WHERE kind='ppr' AND subtype='t_ok'")).one()
    assert ok is True and valid is True and srid == 2975   # pré-projeté, valide


def test_geom_invalide_reparee_par_trigger(db_session):
    # polygone « nœud papillon » auto-sécant = invalide en entrée
    bowtie = "POLYGON((55.30 -21.00,55.31 -20.99,55.31 -21.00,55.30 -20.99,55.30 -21.00))"
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, geom) VALUES ('ppr','t_bad', ST_GeomFromText(:w, 4326))"),
        {"w": bowtie})
    valid = db_session.execute(text(
        "SELECT ST_IsValid(geom_2975) FROM spatial_layers WHERE kind='ppr' AND subtype='t_bad'")).scalar()
    assert valid is True   # réparé par ST_MakeValid → plus de crash GEOS


def test_intersection_ppr_sans_crash_geos(db_session):
    # parcelle valide × assiette PPR auto-sécante : ST_Intersects ne plante pas.
    bowtie = "POLYGON((55.300 -21.000,55.310 -20.990,55.310 -21.000,55.300 -20.990,55.300 -21.000))"
    par = "POLYGON((55.302 -20.996,55.308 -20.996,55.308 -20.992,55.302 -20.992,55.302 -20.996))"
    db_session.execute(text("INSERT INTO spatial_layers (kind, subtype, geom) VALUES ('ppr','t_x', ST_GeomFromText(:w,4326))"), {"w": bowtie})
    n = db_session.execute(text(
        "SELECT count(*) FROM spatial_layers s WHERE s.kind='ppr' AND s.subtype='t_x' "
        "AND ST_Intersects(s.geom_2975, ST_Transform(ST_GeomFromText(:p,4326),2975))"), {"p": par}).scalar()
    assert n >= 0   # le seul fait de ne pas lever GEOS suffit


def test_cascade_lit_ppr_assiette_flag_prudent(db_session):
    """Bout en bout : une assiette PPR (servitude) → flag FORT « prescriptions », JAMAIS
    une exclusion (zonage interne inconnu). La cascade lit la couche PPR sans erreur."""
    from labuse.cascade import evaluate_parcels
    from labuse.enums import CascadeVerdict, EvaluationStatus, Severity
    par = "POLYGON((55.300 -21.000,55.310 -21.000,55.310 -20.990,55.300 -20.990,55.300 -21.000))"
    ppr = "POLYGON((55.290 -21.010,55.320 -21.010,55.320 -20.980,55.290 -20.980,55.290 -21.010))"
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, commune, geom, attrs) VALUES "
        "('ppr','i_mvt','TESTVILLE', ST_GeomFromText(:w,4326), "
        "'{\"risque\":\"inondation + mouvement de terrain\",\"statut\":\"reglementaire\"}'::jsonb)"), {"w": ppr})
    pid = db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "('TESTPPR01','TESTVILLE','T','1', ST_GeomFromText(:p,4326), 1000, "
        "ST_Centroid(ST_GeomFromText(:p,4326)), ST_Envelope(ST_GeomFromText(:p,4326))) RETURNING id"),
        {"p": par}).scalar()
    outs = evaluate_parcels([pid], db_session, persist=False)
    v = next((x for x in outs[0].verdicts if x.layer_name == "risques"), None)
    assert v is not None and "PPR" in v.detail and "prescriptions" in v.detail
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FORT   # flag, PAS exclusion
    assert outs[0].status == EvaluationStatus.A_CREUSER.value                     # jamais « opportunité »


def test_index_gist_geom_2975(engine):
    with engine.connect() as c:
        idx = {r[0] for r in c.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname IN "
            "('idx_parcels_geom_2975','idx_spatial_layers_geom_2975')")).all()}
    assert "idx_parcels_geom_2975" in idx and "idx_spatial_layers_geom_2975" in idx
