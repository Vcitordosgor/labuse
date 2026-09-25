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


def test_clip_assiette_via_source_famille_unique():
    """ZONES-FAMILLE-1 : le clip d'assiette lit la SOURCE SQL UNIQUE (labuse_zone_famille sur
    subtype), plus jamais `name ILIKE 'U%'/'AU%'` (qui ratait numérotées + libellés littéraux)."""
    for q in (fdb._EMPRISE, fdb._GREVE_CERTAINE):
        sql = str(q)
        assert "labuse_zone_famille(z.subtype) = ANY(:uau_fams)" in sql, "source famille absente"
        assert "name ILIKE ANY(:uau_pats)" not in sql, "devine encore la famille depuis name"


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
        # ancien clip : name seul → portion U/AU ratée (NULL/0)
        old = c.execute(text(str(UAU).format(
            clause="z.name ILIKE ANY(:pats)")), {"pid": pid, "pats": ["U%", "AU%"]}).scalar()
        # nouveau clip : SOURCE UNIQUE labuse_zone_famille(subtype) → portion retrouvée
        new = c.execute(text(str(UAU).format(
            clause="labuse_zone_famille(z.subtype) = ANY(:fams)")),
            {"pid": pid, "fams": ["U", "AU"]}).scalar()
    eng.dispose()
    assert (old or 0) < 5.0, f"témoin déjà matché par name — choisir un autre (old={old})"
    assert (new or 0) > 1000.0, f"source famille ne récupère pas la portion U/AU (new={new})"


def test_temoin_commune_libelle_litteral_clippee():
    """8 communes à `name` littéral : témoin (Sainte-Marie) dont l'assiette passait PLEINE
    (name jamais matché) et devient CLIPPÉE à sa portion U/AU réelle via la source famille."""
    LITT = "97418000AP0696"   # Sainte-Marie — full 12162 m² → portion U/AU ~476 m²
    try:
        eng = create_engine(APP_URL)
        with eng.connect() as c:
            pid = c.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": LITT}).scalar()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base applicative indisponible ({type(exc).__name__})")
    if pid is None:
        pytest.skip(f"parcelle témoin {LITT} absente")
    with eng.connect() as c:
        full = c.execute(text(
            "SELECT ST_Area(ST_Buffer(geom_2975,-3.0)) FROM parcels WHERE id=:p"), {"p": pid}).scalar()
        old = c.execute(text(
            "WITH p AS (SELECT commune, ST_Buffer(geom_2975,-3.0) b FROM parcels WHERE id=:p) "
            "SELECT ST_Area(ST_Intersection(p.b, ST_Union(z.geom_2975))) FROM spatial_layers z, p "
            "WHERE z.kind='plu_gpu_zone' AND z.commune=p.commune AND ST_Intersects(z.geom_2975,p.b) "
            "AND z.name ILIKE ANY(ARRAY['U%','AU%']) GROUP BY p.b"), {"p": pid}).scalar()
        new = c.execute(text(
            "WITH p AS (SELECT commune, ST_Buffer(geom_2975,-3.0) b FROM parcels WHERE id=:p) "
            "SELECT ST_Area(ST_Intersection(p.b, ST_Union(z.geom_2975))) FROM spatial_layers z, p "
            "WHERE z.kind='plu_gpu_zone' AND z.commune=p.commune AND ST_Intersects(z.geom_2975,p.b) "
            "AND labuse_zone_famille(z.subtype) = ANY(ARRAY['U','AU']) GROUP BY p.b"), {"p": pid}).scalar()
    eng.dispose()
    assert old is None, f"témoin déjà matché par name (old={old}) — choisir un autre"
    assert new is not None and 5.0 < new < 0.9 * full, \
        f"assiette non clippée par la source famille (full={full}, new={new})"
