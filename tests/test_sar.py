"""SAR (proxy de vocation, Région) — mapping prudent + cascade (jamais d'exclusion auto)."""
from sqlalchemy import text

from labuse.ingestion.layers_ingest import _sar_vocation


def test_vocation_urbaine_compatible():
    st, lib, niv = _sar_vocation("Espace urbanisé à densifier")
    assert st == "vocation_urbaine" and niv == "faible" and "compatible" in lib.lower()


def test_urbanisation_prioritaire_compatible():
    st, _, niv = _sar_vocation("Espace d'urbanisation prioritaire")
    assert st == "vocation_urbaine" and niv == "faible"


def test_agricole_est_un_flag():
    st, lib, niv = _sar_vocation("Agricole")
    assert st == "vocation_agricole" and niv == "fort" and "agricole" in lib.lower()


def test_naturel_protection_forte_flag_pas_exclusion():
    # PROXY : protection forte → FLAG « à vérifier », JAMAIS le subtype d'exclusion 'espace_naturel'.
    st, _, niv = _sar_vocation("Espace naturel de protection forte terrestres")
    assert st == "vocation_naturelle" and niv == "fort"
    assert st != "espace_naturel"


def test_continuite_ecologique_flag():
    st, _, niv = _sar_vocation("Continuité écologique")
    assert st == "vocation_continuite" and niv == "fort"


def test_mixte_urbain_plus_contrainte():
    st, lib, _ = _sar_vocation("Espace urbanisé à densifier,Agricole")
    assert st == "vocation_mixte" and "à vérifier" in lib.lower()


def test_rural_habite_faible():
    st, _, niv = _sar_vocation("Territoires ruraux habités")
    assert st == "vocation_rurale" and niv == "faible"


def test_cascade_sar_proxy_flague_sans_exclure(db_session):
    """Bout en bout : une vocation SAR naturelle (proxy) → FLAG FORT « à vérifier »,
    JAMAIS une exclusion. Le SAR contribue, il ne tranche pas seul."""
    from labuse.cascade import evaluate_parcels
    from labuse.enums import CascadeVerdict, Severity
    par = "POLYGON((55.40 -21.00,55.41 -21.00,55.41 -20.99,55.40 -20.99,55.40 -21.00))"
    sar = "POLYGON((55.39 -21.01,55.42 -21.01,55.42 -20.98,55.39 -20.98,55.39 -21.01))"
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, commune, geom, attrs) VALUES "
        "('sar','vocation_naturelle','SARVILLE', ST_GeomFromText(:w,4326), "
        "'{\"libelle\":\"espace naturel SAR (protection forte) — à vérifier\",\"statut\":\"strategique\"}'::jsonb)"),
        {"w": sar})
    pid = db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "('SAR00001','SARVILLE','S','1', ST_GeomFromText(:p,4326), 1000, "
        "ST_Centroid(ST_GeomFromText(:p,4326)), ST_Envelope(ST_GeomFromText(:p,4326))) RETURNING id"),
        {"p": par}).scalar()
    outs = evaluate_parcels([pid], db_session, persist=False)
    v = next((x for x in outs[0].verdicts if x.layer_name == "sar"), None)
    assert v is not None
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FORT   # flag, PAS exclusion
    assert "à vérifier" in v.detail
