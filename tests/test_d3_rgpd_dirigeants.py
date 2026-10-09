"""CORRECTIFS-1 D3 — la purge RGPD retire la nationalité des payloads et vide `raw` des non diffusibles."""
import json

import pytest
from sqlalchemy import text

from labuse.rgpd_dirigeants import purger_nationalite_et_raw


@pytest.fixture
def _seed_d3(engine):
    with engine.begin() as c:
        c.execute(text("DELETE FROM owner_enrichment WHERE siren LIKE '900%'"))
        c.execute(text("DELETE FROM pm_dirigeants WHERE siren LIKE '900%'"))
        # payload avec nationalité à la racine ET dans un dirigeant
        c.execute(text("INSERT INTO owner_enrichment (siren, denomination, source, payload) "
                       "VALUES ('900000001', 'SCI TEST', 'recherche_entreprises', CAST(:p AS jsonb))"),
                  {"p": json.dumps({"nationalite": "Française",
                                    "dirigeants": [{"nom": "X", "nationalite": "Française"},
                                                   {"nom": "Y"}]})})
        # pm_dirigeants : diffusible TRUE (raw conservé), FALSE et NULL (raw à vider)
        for rid, diff in (("r-diff", True), ("r-nondiff", False), ("r-null", None)):
            c.execute(text("INSERT INTO pm_dirigeants (siren, representant_id, diffusible, raw) "
                           "VALUES ('900000002', :r, :d, CAST(:raw AS jsonb))"),
                      {"r": rid, "d": diff, "raw": json.dumps({"nom": "Z", "nationalite": "Fr"})})
    yield
    with engine.begin() as c:
        c.execute(text("DELETE FROM owner_enrichment WHERE siren LIKE '900%'"))
        c.execute(text("DELETE FROM pm_dirigeants WHERE siren LIKE '900%'"))


def test_purge_retire_nationalite_et_vide_raw_non_diffusible(engine, _seed_d3):
    res = purger_nationalite_et_raw(engine)
    assert res["payloads_nettoyes"] == 1
    assert res["raw_vides"] == 2   # le FALSE et le NULL, jamais le TRUE

    with engine.connect() as c:
        payload = c.execute(text("SELECT payload FROM owner_enrichment WHERE siren='900000001'")).scalar()
        assert "nationalite" not in payload                          # racine retirée
        assert all("nationalite" not in d for d in payload["dirigeants"])  # chaque dirigeant
        assert payload["dirigeants"][0]["nom"] == "X"                # le reste intact

        raws = dict(c.execute(text(
            "SELECT representant_id, raw FROM pm_dirigeants WHERE siren='900000002'")).all())
        assert raws["r-diff"] is not None       # diffusible → conservé
        assert raws["r-nondiff"] is None        # non diffusible → vidé
        assert raws["r-null"] is None           # diffusibilité inconnue → vidé


def test_purge_idempotente(engine, _seed_d3):
    purger_nationalite_et_raw(engine)
    res2 = purger_nationalite_et_raw(engine)   # rejeu : plus rien à toucher
    assert res2 == {"payloads_nettoyes": 0, "raw_vides": 0}
