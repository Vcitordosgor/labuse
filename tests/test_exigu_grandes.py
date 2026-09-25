"""EXIGU-GRANDES — verrou du correctif : les zones AU NUMÉROTÉES (1AU/2AU/3AU) doivent être
reconnues par le clip d'assiette constructible.

Le bug : `_EMPRISE` / `_GREVE_CERTAINE` clippaient la portion U/AU sur `spatial_layers.name`
(ILIKE 'U%'/'AU%'). Les zones à urbaniser numérotées portent un `name` commençant par un chiffre
('1AUb') et leur code GPU dans `subtype` ('AUc') → 0/422 matchaient `name` → assiette vidée →
`terrain_exigu` à tort sur de grandes parcelles. Correctif borné : rattrapage via `subtype`
quand `name` est numérique.

- Test 1 (sans base) : la clause de rattrapage est présente dans les deux requêtes.
- Test 2 (base applicative, skip si absente) : une parcelle témoin en zone AU numérotée n'est
  plus déclarée terrain_exigu par vidage d'assiette.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from labuse.faisabilite import db as fdb

APP_URL = os.environ.get("LABUSE_AUDIT_DATABASE_URL") \
    or "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"
WITNESS = "97407000BM0011"   # 1AUmut, 72 704 m² — vidée à tort avant le fix


def test_clause_rattrapage_zones_au_numerotees_presente():
    """Les deux requêtes de clip d'assiette rattrapent les zones numérotées via subtype."""
    for q in (fdb._EMPRISE, fdb._GREVE_CERTAINE):
        sql = str(q)
        assert "z.name ~ '^[0-9]'" in sql, "clause name-numérique absente"
        assert "z.subtype ILIKE ANY(:uau_pats)" in sql, "rattrapage subtype absent"


def test_temoin_numerotee_portion_uau_recuperee():
    """Sur la base applicative : le clip d'assiette du témoin (zone AU numérotée) trouve une
    portion U/AU NON NULLE avec le fix (subtype), alors que l'ancien clip (name seul) la ratait.

    Test au niveau SQL — indépendant de session_scope (que conftest redirige vers la base de
    test) et du bâti : c'est exactement la clause corrigée que l'on vérifie."""
    try:
        eng = create_engine(APP_URL)
        with eng.connect() as c:
            pid = c.execute(text("SELECT id FROM parcels WHERE idu = :i"),
                            {"i": WITNESS}).scalar()
    except Exception as exc:  # noqa: BLE001 — base indisponible → skip, jamais rouge en CI
        pytest.skip(f"base applicative indisponible ({type(exc).__name__})")
    if pid is None:
        pytest.skip(f"parcelle témoin {WITNESS} absente")
    UAU = text("""
      WITH p AS (SELECT commune, ST_Buffer(geom_2975, -3.0) AS b FROM parcels WHERE id = :pid)
      SELECT COALESCE(ST_Area(ST_Intersection(p.b, ST_Union(z.geom_2975))), 0.0)
      FROM spatial_layers z, p
      WHERE z.kind='plu_gpu_zone' AND z.commune=p.commune AND ST_Intersects(z.geom_2975, p.b)
        AND ({clause})
      GROUP BY p.b""")
    with eng.connect() as c:
        # ancien clip : name seul → portion U/AU ratée (0 / vide)
        old = c.execute(text(str(UAU).format(
            clause="z.name ILIKE ANY(:pats)")), {"pid": pid, "pats": ["U%", "AU%"]}).scalar()
        # nouveau clip : rattrapage subtype quand name numérique → portion retrouvée
        new = c.execute(text(str(UAU).format(
            clause="z.name ILIKE ANY(:pats) OR (z.name ~ '^[0-9]' "
                   "AND z.subtype ILIKE ANY(:pats))")), {"pid": pid, "pats": ["U%", "AU%"]}).scalar()
    eng.dispose()
    assert (old or 0) < 5.0, f"témoin déjà matché par name — choisir un autre (old={old})"
    assert (new or 0) > 1000.0, f"fix ne récupère pas la portion U/AU (new={new})"
