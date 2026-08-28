"""ÉTUDE DE ZONE · Z1 — ingestion MOBPRO (agrégat emplois au lieu de travail).

NB : les tests SIRENE ont migré vers `test_zone_donnees.py` (ZONE-DONNÉES LOT 1 — ingestion sur le
fichier INSEE géolocalisé × StockEtablissement via DuckDB, plus l'ancien CSV local). MOBPRO reste
testé ici mais est ABANDONNÉ pour l'Étude de zone (LOT 2 : les emplois viennent des tranches SIRENE) ;
le code d'ingestion subsiste (table non supprimée).
Données de test créées puis PURGÉES.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion import seed_sources
from labuse.ingestion.mobpro import build_mobpro, ensure_tables as mobpro_ens

pytestmark = pytest.mark.db

_MOBPRO_CSV = """COMMUNE;DCLT;IPONDI
97411;97409;120.0
97409;97409;80.5
97409;97411;15.0
75056;75056;9.0
"""


def test_mobpro_agrege_les_emplois_au_lieu_de_travail(engine, tmp_path):
    p = tmp_path / "mobpro.csv"
    p.write_text(_MOBPRO_CSV, encoding="utf-8")
    with session_scope() as s:
        seed_sources.seed(s)
        mobpro_ens(s)
        build_mobpro(s, file=str(p), millesime="MOBPRO test")
    with session_scope() as s:
        emplois = {r[0]: r[1] for r in s.execute(text(
            "SELECT insee, emplois_lieu_travail FROM mobpro_commune WHERE insee LIKE '974%'"))}
    # LIEU DE TRAVAIL 97409 : 120 (depuis 97411) + 80,5 (depuis 97409) = 200,5 → 200 ; 97411 = 15
    assert emplois["97409"] == 200 and emplois["97411"] == 15
    assert "75056" not in emplois, "seul le 974 est retenu (DCLT)"
    with session_scope() as s:
        s.execute(text("DELETE FROM mobpro_commune WHERE millesime='MOBPRO test'"))
