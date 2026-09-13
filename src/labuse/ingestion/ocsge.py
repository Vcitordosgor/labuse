"""REPARATIONS-1 lot 5 — OCS GE : L'USAGE DU SOL ET L'ARTIFICIALISATION OFFICIELLE.

TÉLÉCHARGEMENT IGN OFFICIEL (data.geopf.fr/telechargement, Licence Ouverte 2.0), filtrage 974
au plus tôt : les produits DÉPARTEMENTAUX D974 seulement. DEUX MILLÉSIMES publiés pour le 974
(constaté au catalogue le 13/09/2026) :
  · OCS-GE_2-0__GPKG_RGR92UTM40S_D974_2017-01-01  (couverture + usage, 2017)
  · OCS-GE_2-0__GPKG_RGR92UTM40S_D974_2022-01-01  (couverture + usage, 2022)
  · OCS-GE-ARTIFICIALISATION_2-0_DIFF-2017-2022_…D974 (le CHANGEMENT officiel, flags artif IGN)
CRS INSPECTÉ, pas supposé : `gpkg_spatial_ref_sys` des GPKG déclare srs 2975 « RGR92 / UTM
zone 40S » (lu dans le fichier) — chargé tel quel en 2975, jamais re-deviné.

ARTIFICIALISATION : le statut par polygone suit la MÉTHODE OFFICIELLE du portail de
l'artificialisation (fiche indicateur, décret n° 2023-1096 du 27/11/2023, étape 1 —
affectation par couverture × usage) :
  · couverture anthropisée (CS1.1.*) → artificialisé, SAUF matériaux minéraux (CS1.1.2.1)
    à usage d'extraction (US1.3) ;
  · végétation NON LIGNEUSE (CS2.2.*) à usage résidentiel / mixte / production secondaire ou
    tertiaire / transport / transition / abandonné (US5, US235, US2, US3, US4.*, US6.1, US6.2)
    → artificialisé ;
  · tout le reste → non artificialisé.
Les étapes 2-3 de la fiche (regroupement + seuils d'enclaves 2 500 m²) ne sont PAS rejouées
ici : le flag par parcelle est dit « avant lissage réglementaire » ; le CHANGEMENT servi vient
du produit DIFF officiel (qui, lui, applique tout). OCS GE NE NOURRIT PAS LE SCORE.

Par parcelle, PRÉCALCULÉ à l'ingestion (`parcel_ocsge`) : part artificialisée, couverture et
usage dominants, changement 2017→2022 (m² artificialisés / renaturés, du produit officiel).
Granularité : donnée d'ÎLOT — la fiche dit « d'après OCS GE », jamais la précision cadastrale.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from sqlalchemy import text

log = logging.getLogger("labuse.ingestion.ocsge")

MILLESIMES = ("2017", "2022")

DDL = """
CREATE TABLE IF NOT EXISTS ocsge_sol (
  id bigserial PRIMARY KEY,
  millesime varchar(4) NOT NULL,
  code_cs varchar(16) NOT NULL,
  code_us varchar(16) NOT NULL,
  artif boolean NOT NULL,
  geom_2975 geometry(Geometry, 2975) NOT NULL,
  ingere_le timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ocsge_sol_geom ON ocsge_sol USING gist (geom_2975);
CREATE INDEX IF NOT EXISTS ix_ocsge_sol_mil ON ocsge_sol (millesime);
CREATE TABLE IF NOT EXISTS ocsge_evolution (
  id bigserial PRIMARY KEY,
  artificialisation varchar(24),        -- artificialisation | renaturation (produit officiel)
  cs_2017 varchar(16), us_2017 varchar(16), artif_2017 varchar(12),
  cs_2022 varchar(16), us_2022 varchar(16), artif_2022 varchar(12),
  surface_m2 real,
  geom_2975 geometry(Geometry, 2975) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ocsge_evol_geom ON ocsge_evolution USING gist (geom_2975);
CREATE TABLE IF NOT EXISTS parcel_ocsge (
  idu varchar(20) PRIMARY KEY,
  part_artif_pct real,                  -- part de la parcelle artificialisée (millésime récent)
  cs_dominant varchar(16),
  us_dominant varchar(16),
  artif_m2 real,
  evol_artif_m2 real,                   -- m² passés artificialisés 2017→2022 (produit officiel)
  evol_renat_m2 real,                   -- m² renaturés 2017→2022
  millesime varchar(4),
  calcule_le timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_tables(session) -> None:
    from ..db import sql_statements
    for stmt in sql_statements(DDL):
        session.execute(text(stmt))


def artif_decret(code_cs: str, code_us: str) -> bool:
    """Étape 1 de la fiche officielle (décret 2023-1096) — affectation couverture × usage."""
    cs, us = (code_cs or ""), (code_us or "")
    if cs.startswith("CS1.1"):
        return not (cs == "CS1.1.2.1" and us == "US1.3")
    if cs.startswith("CS2.2"):
        return (us in ("US5", "US235", "US2", "US3", "US6.1", "US6.2")
                or us.startswith("US4"))
    return False


def _srid_inspecte(gpkg: str, table: str) -> int:
    """Le CRS LU dans le fichier (gpkg_geometry_columns) — jamais supposé."""
    c = sqlite3.connect(gpkg)
    try:
        return int(c.execute(
            "SELECT srs_id FROM gpkg_geometry_columns WHERE table_name = ?", (table,)).fetchone()[0])
    finally:
        c.close()


def _wkb_rows(gpkg: str, table: str, cols: list[str]):
    """Lit le GPKG (SQLite) et rend (attrs…, WKB) — l'en-tête GeoPackageBinary est retiré
    pour livrer du WKB standard à PostGIS (flags envelope → offset variable)."""
    c = sqlite3.connect(gpkg)
    try:
        geom_col = c.execute(
            "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
            (table,)).fetchone()[0]
        for row in c.execute(f"SELECT {', '.join(cols)}, {geom_col} FROM {table}"):  # noqa: S608
            gp = row[-1]
            if gp is None:
                continue
            flags = gp[3]
            env = (flags >> 1) & 0x07
            offset = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
            yield row[:-1], gp[offset:]
    finally:
        c.close()


def ingest_ocsge(session, base_dir: str, *, log_fn=print) -> dict:
    """Charge les DEUX millésimes (OCCUPATION_SOL) + le produit DIFF officiel depuis les
    livraisons IGN extraites sous `base_dir`. Idempotent : TRUNCATE + INSERT par millésime."""
    ensure_tables(session)
    base = Path(base_dir)
    res: dict = {"millesimes": {}, "evolution": 0, "srid": {}}
    for mil in MILLESIMES:
        gpkg = next(base.glob(f"OCS-GE_2-0__GPKG_RGR92UTM40S_D974_{mil}-01-01/**/OCCUPATION_SOL.gpkg"))
        srid = _srid_inspecte(str(gpkg), "OCCUPATION_SOL")
        res["srid"][mil] = srid
        if srid != 2975:
            raise RuntimeError(f"CRS inattendu dans {gpkg.name} : {srid} (2975 attendu — inspection)")
        session.execute(text("DELETE FROM ocsge_sol WHERE millesime = :m"), {"m": mil})
        n = 0
        for (cs, us), wkb in _wkb_rows(str(gpkg), "OCCUPATION_SOL", ["code_cs", "code_us"]):
            session.execute(text(
                "INSERT INTO ocsge_sol (millesime, code_cs, code_us, artif, geom_2975) "
                "VALUES (:m, :cs, :us, :a, ST_SetSRID(ST_GeomFromWKB(:g), 2975))"),
                {"m": mil, "cs": cs, "us": us, "a": artif_decret(cs, us), "g": wkb})
            n += 1
            if n % 20000 == 0:
                session.commit()
                log_fn(f"  {mil}: {n}…")
        session.commit()
        res["millesimes"][mil] = n
        log_fn(f"  OCS GE {mil} : {n} polygones (CRS {srid} inspecté)")
    diff = next(base.glob("artif/**/zan_evol_2017_2022_974.gpkg"))
    srid = _srid_inspecte(str(diff), "zan_evol_2017_2022_974")
    res["srid"]["diff"] = srid
    session.execute(text("DELETE FROM ocsge_evolution"))
    n = 0
    for (artif, cs17, us17, a17, cs22, us22, a22, surf), wkb in _wkb_rows(
            str(diff), "zan_evol_2017_2022_974",
            ["artificialisation", "cs_2017", "us_2017", "artif_2017",
             "cs_2022", "us_2022", "artif_2022", "surface"]):
        session.execute(text(
            "INSERT INTO ocsge_evolution (artificialisation, cs_2017, us_2017, artif_2017,"
            " cs_2022, us_2022, artif_2022, surface_m2, geom_2975) VALUES"
            " (:ar, :c1, :u1, :a1, :c2, :u2, :a2, :s, ST_SetSRID(ST_GeomFromWKB(:g), :srid))"),
            {"ar": artif, "c1": cs17, "u1": us17, "a1": a17, "c2": cs22, "u2": us22,
             "a2": a22, "s": surf, "g": wkb, "srid": srid})
        n += 1
    session.commit()
    res["evolution"] = n
    log_fn(f"  évolution officielle 2017→2022 : {n} zones (CRS {srid} inspecté)")
    return res


def precalcul_parcelles(session, *, log_fn=print) -> dict:
    """PAR PARCELLE, précalculé à l'ingestion : part artificialisée (millésime récent),
    couverture et usage dominants (par aire intersectée), changement officiel 2017→2022.

    UNE SEULE passe d'intersections parcelle × OCS GE 2022 (table temporaire), puis des
    agrégats — la première version (trois LATERAL, chacun recalculant les intersections)
    tournait encore après 1 h sur 431 663 parcelles et VERROUILLAIT parcels (annulée).
    Idempotent (TRUNCATE + INSERT)."""
    ensure_tables(session)
    session.execute(text("DROP TABLE IF EXISTS tmp_ocsge_x"))
    session.execute(text("""
        CREATE TEMP TABLE tmp_ocsge_x AS
        SELECT p.idu, o.code_cs, o.code_us, o.artif,
               ST_Area(ST_Intersection(o.geom_2975, p.geom_2975)) AS aire
        FROM parcels p
        JOIN ocsge_sol o ON o.millesime = '2022'
          AND o.geom_2975 && p.geom_2975 AND ST_Intersects(o.geom_2975, p.geom_2975)
        WHERE p.geom_2975 IS NOT NULL"""))
    session.execute(text("CREATE INDEX ON tmp_ocsge_x (idu)"))
    session.execute(text("""
        CREATE TEMP TABLE tmp_ocsge_evol AS
        SELECT p.idu,
               sum(ST_Area(ST_Intersection(v.geom_2975, p.geom_2975)))
                 FILTER (WHERE v.artificialisation ILIKE 'artificialisation%') AS artif_m2,
               sum(ST_Area(ST_Intersection(v.geom_2975, p.geom_2975)))
                 FILTER (WHERE v.artificialisation ILIKE '%naturation%') AS renat_m2
        FROM parcels p
        JOIN ocsge_evolution v ON v.geom_2975 && p.geom_2975
          AND ST_Intersects(v.geom_2975, p.geom_2975)
        WHERE p.geom_2975 IS NOT NULL
        GROUP BY p.idu"""))
    session.execute(text("TRUNCATE parcel_ocsge"))
    session.execute(text("""
        INSERT INTO parcel_ocsge (idu, part_artif_pct, cs_dominant, us_dominant, artif_m2,
                                  evol_artif_m2, evol_renat_m2, millesime)
        SELECT a.idu,
               LEAST(100.0, GREATEST(0.0,
                   100.0 * a.artif_m2 / NULLIF(ST_Area(p.geom_2975), 0)))::real,
               a.cs_dominant, a.us_dominant, a.artif_m2::real,
               COALESCE(e.artif_m2, 0)::real, COALESCE(e.renat_m2, 0)::real, '2022'
        FROM (SELECT idu,
                     sum(aire) FILTER (WHERE artif) AS artif_m2,
                     (array_agg(code_cs ORDER BY aire DESC))[1] AS cs_dominant,
                     (array_agg(code_us ORDER BY aire DESC))[1] AS us_dominant
              FROM tmp_ocsge_x GROUP BY idu) a
        JOIN parcels p ON p.idu = a.idu
        LEFT JOIN tmp_ocsge_evol e ON e.idu = a.idu"""))
    session.execute(text("""
        UPDATE parcel_ocsge SET artif_m2 = COALESCE(artif_m2, 0),
                                part_artif_pct = COALESCE(part_artif_pct, 0)"""))
    session.commit()
    n = session.execute(text("SELECT count(*) FROM parcel_ocsge")).scalar()
    n_art = session.execute(text(
        "SELECT count(*) FROM parcel_ocsge WHERE part_artif_pct >= 50")).scalar()
    log_fn(f"  parcel_ocsge : {n} parcelles ({n_art} majoritairement artificialisées)")
    return {"parcelles": n, "majoritairement_artif": n_art}


def construire_couche(session, *, log_fn=print) -> dict:
    """La couche carte « Artificialisation (OCS GE) » (kind `artificialisation`, spatial_layers,
    servie par /map/layers.geojson comme les autres). Trois classes lisibles :
      · artificialise_2022 — l'artificialisé 2022 DISSOUS (méthode de la fiche officielle :
        regroupement des polygones de même catégorie), pièces ≥ 2 500 m² (le seuil réglementaire
        de détection — les confettis sous le seuil ne sont pas peints, dit dans le « i ») ;
      · evolution_artificialisation / evolution_renaturation — le produit DIFF officiel IGN.
    Désactivée par défaut au panneau. Idempotent (DELETE kind + INSERT)."""
    ensure_tables(session)
    sid = session.execute(text(
        "SELECT id FROM data_sources WHERE name LIKE 'OCS GE (IGN)%'")).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'artificialisation'"))
    n1 = session.execute(text("""
        INSERT INTO spatial_layers (kind, subtype, name, geom, geom_2975, data_source_id, attrs)
        SELECT 'artificialisation', 'artificialise_2022',
               'Artificialisé (OCS GE 2022)',
               ST_Transform(d.geom, 4326), d.geom, :sid,
               jsonb_build_object('classe', 'artificialise',
                                  'surface_m2', round(ST_Area(d.geom)),
                                  'source', 'OCS GE 2022 (IGN) — dissous, pièces ≥ 2 500 m²')
        FROM (SELECT (ST_Dump(ST_Union(geom_2975))).geom AS geom
              FROM ocsge_sol WHERE millesime = '2022' AND artif) d
        WHERE ST_Area(d.geom) >= 2500"""), {"sid": sid}).rowcount
    session.commit()
    n2 = session.execute(text("""
        INSERT INTO spatial_layers (kind, subtype, name, geom, geom_2975, data_source_id, attrs)
        SELECT 'artificialisation',
               CASE WHEN artificialisation ILIKE 'artificialisation%'
                    THEN 'evolution_artificialisation' ELSE 'evolution_renaturation' END,
               CASE WHEN artificialisation ILIKE 'artificialisation%'
                    THEN 'Artificialisé 2017→2022' ELSE 'Renaturé 2017→2022' END,
               ST_Transform(geom_2975, 4326), geom_2975, :sid,
               jsonb_build_object('classe',
                    CASE WHEN artificialisation ILIKE 'artificialisation%'
                         THEN 'evolution_artificialisation' ELSE 'evolution_renaturation' END,
                    'surface_m2', round(surface_m2::numeric),
                    'cs_2022', cs_2022, 'us_2022', us_2022,
                    'source', 'OCS GE — diff artificialisation 2017→2022 (IGN, officiel)')
        FROM ocsge_evolution"""), {"sid": sid}).rowcount
    session.commit()
    log_fn(f"  couche artificialisation : {n1} zones dissoutes + {n2} zones d'évolution")
    return {"artificialise": n1, "evolution": n2}
