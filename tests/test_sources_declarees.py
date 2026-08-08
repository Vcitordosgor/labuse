"""M-H — garde de traçabilité source ↔ couche : check_sources_declarees + backfill."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse import bascule_gardes
from labuse.bascule_gardes import check_sources_declarees

pytestmark = pytest.mark.db

_GEOM = "ST_SetSRID(ST_MakePoint(55.3, -21.0), 4326)"


def test_orphelin_detecte(db_session):
    """Validation #2 : un orphelin introduit volontairement (kind sans data_source_id) est ORPHELIN."""
    s = db_session
    s.execute(text(f"INSERT INTO spatial_layers (kind, geom) VALUES ('_mh_orphelin', {_GEOM})"))
    out = check_sources_declarees(session=s)
    assert out["_mh_orphelin"] == "ORPHELIN"


def test_source_liee_ok(db_session):
    """Une couche portant un data_source_id est OK."""
    s = db_session
    sid = s.execute(text("SELECT id FROM data_sources LIMIT 1")).scalar()
    assert sid is not None
    s.execute(text(f"INSERT INTO spatial_layers (kind, geom, data_source_id) "
                   f"VALUES ('_mh_liee', {_GEOM}, :sid)"), {"sid": sid})
    out = check_sources_declarees(session=s)
    assert out["_mh_liee"] == "OK"


def test_source_absente_detectee(db_session, monkeypatch):
    """Un kind mappé (KIND_SOURCE) à un nom data_sources inexistant → SOURCE ABSENTE."""
    from labuse.ingestion import layers_ingest
    s = db_session
    monkeypatch.setitem(layers_ingest.KIND_SOURCE, "_mh_absente", "Source Qui N'existe Pas (M-H)")
    s.execute(text(f"INSERT INTO spatial_layers (kind, geom) VALUES ('_mh_absente', {_GEOM})"))
    out = check_sources_declarees(session=s)
    assert out["_mh_absente"] == "SOURCE ABSENTE"


def test_garde_meme_regime_non_bloquant(db_session):
    """Régime check_coherence_tables_run_scopees : bruyante, NON bloquante (retourne un dict, ne lève pas)."""
    s = db_session
    s.execute(text(f"INSERT INTO spatial_layers (kind, geom) VALUES ('_mh_orphelin2', {_GEOM})"))
    out = check_sources_declarees(session=s)          # ne lève pas malgré l'orphelin
    assert isinstance(out, dict) and out["_mh_orphelin2"] == "ORPHELIN"


def test_garde_branchee_dans_build_mvt():
    """Validation #3 : la garde est appelée dans la MÊME séquence que les autres (build_mvt)."""
    src = Path(bascule_gardes.__file__).with_name("api").joinpath("tiles.py").read_text(encoding="utf-8")
    assert "check_sources_declarees" in src, "garde non branchée dans api/tiles.py (build_mvt)"
    # dans le même bloc que la garde M50 sœur
    assert "check_coherence_tables_run_scopees" in src


def test_backfill_idempotent_et_sans_lien_faux(db_session):
    """Le backfill ne touche que les lignes NULL et ne fabrique jamais un lien vers une source absente."""
    from labuse.ingestion import layers_ingest
    s = db_session
    # kind connu de KIND_SOURCE dont la source EXISTE → un orphelin est rattaché
    s.execute(text(f"INSERT INTO spatial_layers (kind, geom) VALUES ('cinquante_pas', {_GEOM})"))
    before_null = s.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='cinquante_pas' AND data_source_id IS NULL")).scalar()
    rattaches = layers_ingest.backfill_layer_sources(s)
    after_null = s.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='cinquante_pas' AND data_source_id IS NULL")).scalar()
    assert before_null >= 1 and after_null == 0
    assert rattaches.get("cinquante_pas", 0) >= 1
