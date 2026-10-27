"""POSTDEPLOY-1027 (P3) — l'ingestion DEAL Carmen nomme la Réserve Naturelle Marine (RNMR) de façon
RETROUVABLE, pour que le verrou de quarantaine `d_enp_reserve_marine` passe SANS dérogation.

La migration Carmen→Lizmap du 13/09 sert la RNMR en 150 features par secteur nommés `Nom_zone`
(COT_*/DAR_*) : aucun ne contient « marine », donc l'entité « Réserve Naturelle Marine » que Carmen
fusionnait disparaissait aux yeux du verrou (et des consommateurs), alors que la géométrie était
toujours là. Le correctif préfixe les secteurs à l'ingestion. On le vérifie SANS réseau (client WFS
simulé) : un secteur COT_* entré ressort nommé « …Marine… », subtype reserve_naturelle, et le verrou
ne bloque plus.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import deal_carmen

pytestmark = pytest.mark.db


class _FakeResp:
    def __init__(self, feats):
        self._feats = feats

    def raise_for_status(self):
        pass

    def json(self):
        return {"features": self._feats}


class _FakeClient:
    """Client WFS simulé : rend les features cannées pour chaque TYPENAME, [] sinon."""
    def __init__(self, par_typename):
        self._par = par_typename

    def get(self, url, params=None):
        return _FakeResp(self._par.get((params or {}).get("TYPENAME"), []))


def _carre(x0=55.20, y0=-21.03):
    # polygone à 4 sommets distincts (survit à _nettoyer_geom qui exige ≥ 3 points distincts par anneau)
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x0 + 0.01, y0], [x0 + 0.01, y0 + 0.01],
                                                [x0, y0 + 0.01], [x0, y0]]]}


def test_rnmr_prefixe_rend_la_reserve_marine_retrouvable(db_session):
    rnmr = [{"type": "Feature", "geometry": _carre(),
             "properties": {"Nom_zone": "COT_Cap_Champagne", "Statut_RNM": "HR"}}]
    client = _FakeClient({"Reserve_Naturelle_Marine_Regionale__RNMR": rnmr})

    deal_carmen.ingest_deal_carmen(db_session, source_ids={}, client=client)

    noms = [n for (n,) in db_session.execute(text(
        "SELECT name FROM spatial_layers WHERE kind='ens' AND subtype='reserve_naturelle'")).all()]
    assert len(noms) == 1
    assert "marine" in noms[0].lower(), f"le secteur RNMR doit porter l'identité « marine » : {noms[0]!r}"
    assert "COT_Cap_Champagne" in noms[0], "le secteur d'origine reste lisible dans le nom"

    # le verrou de quarantaine d_enp_reserve_marine ne bloque plus (NOT EXISTS → False)
    bloque = db_session.execute(text(
        "SELECT NOT EXISTS (SELECT 1 FROM spatial_layers WHERE kind='ens' "
        "AND subtype='reserve_naturelle' AND name ILIKE '%marine%')")).scalar()
    assert bloque is False


def test_layer_rnmr_declare_un_prefixe_marine():
    """Garde statique : l'entrée RNMR du module porte un préfixe d'identité contenant « marine »."""
    rnmr = next(l for l in deal_carmen.LAYERS
                if l["typename"] == "Reserve_Naturelle_Marine_Regionale__RNMR")
    assert "marine" in (rnmr.get("nom_prefixe") or "").lower()
