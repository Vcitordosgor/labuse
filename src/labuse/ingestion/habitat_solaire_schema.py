"""Schéma du module Habitat Solaire (mandat habitat-solaire, §3).

Six tables, créées idempotemment (pattern ban_adresses) :
- solar_grid        : points PVGIS bruts (grille ~400 m, Lot 1)
- parcel_solar      : la table pivot par parcelle (idu) — remplie par les Lots 1/2/4/5
- parkings_aper     : parcs de stationnement assujettis loi APER (Lot 3)
- pv_registry       : registre national des installations PV, dép. 974 (Lot 4)
- grid_capacity     : capacités d'accueil réseau EDF SEI (Lot 7, best effort)
- solar_api_cache   : cache Google Solar API, TTL 30 j STRICT (Lot 8, conditionnel)

`parcel_solar` est jointe au moteur de segments par `JOINS["sol"]` (registry.py) :
la table qui apparaît = les filtres solaires dégrisés, sans autre changement
(règle de convergence des mandats).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

DDL_HABITAT_SOLAIRE = """
CREATE TABLE IF NOT EXISTS solar_grid (
  id            serial PRIMARY KEY,
  geom          geometry(Point, 4326) NOT NULL,
  prod_spec_kwh_kwc  double precision,
  ghi_kwh_m2_an      double precision,
  source        varchar(32) NOT NULL,          -- 'pvgis_v5_3'
  fetched_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS solar_grid_geom_gix ON solar_grid USING gist (geom);

CREATE TABLE IF NOT EXISTS parcel_solar (
  idu           varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  prod_spec_kwh_kwc  double precision,         -- interpolé depuis solar_grid (Lot 1)
  score_solaire      integer,                  -- 0-100, percentile île (Lot 1)
  azimut_bati_deg    double precision,         -- grand axe du bâti principal (Lot 5)
  azimut_confiance   varchar(8),               -- 'haute'|'basse' selon élongation
  flag_abf           boolean,
  flag_amiante       boolean,                  -- bâti pré-1997 (DPE) — prudence, PAS un diagnostic
  flag_topo_ombrage  boolean,                  -- fond de cirque / rempart (Lot 1)
  conso_est_kwh_an   integer,                  -- estimation STATISTIQUE (Lot 2)
  facture_est_eur_mois integer,                -- arrondie à la dizaine (Lot 2)
  proba_proprio_occupant integer,              -- 0-100 (Lot 5)
  pv_existant        varchar(24),              -- null|'commune_forte_densite'|'detecte'
  repowering         boolean,                  -- contrat d'achat 2006-2013 en fin de vie (Lot 4)
  updated_at         timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parkings_aper (
  id            serial PRIMARY KEY,
  geom          geometry(Polygon, 4326) NOT NULL,
  geom_2975     geometry(Polygon, 2975),
  surface_m2    double precision NOT NULL,
  source        varchar(16) NOT NULL,          -- 'osm'|'bdtopo'
  source_ref    varchar(40),                   -- ex. osm way id (dédup re-runs)
  idus          jsonb,                         -- parcelles support
  proprio_pm    text,
  proprio_siren varchar(9),
  tranche       varchar(16),                   -- '1000_10000'|'sup_10000' (seuil Réunion : décret 2025-802)
  echeance      date,
  equipe        boolean,                       -- NULL = inconnu (pas de détection ombrière)
  exempt_probable varchar(16),                 -- null|'arbres'|'autre'
  updated_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS parkings_aper_geom_2975_gix ON parkings_aper USING gist (geom_2975);
CREATE UNIQUE INDEX IF NOT EXISTS parkings_aper_source_ref_uix
  ON parkings_aper (source, source_ref) WHERE source_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS pv_registry (
  id            serial PRIMARY KEY,
  commune       varchar(80),
  insee         varchar(5),
  filiere       varchar(40),
  puissance_kw  double precision,
  date_mise_service date,
  individualise boolean,
  geom          geometry(Point, 4326),
  raw           jsonb,
  ingested_at   timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pv_registry_insee_idx ON pv_registry (insee);

CREATE TABLE IF NOT EXISTS grid_capacity (
  id            serial PRIMARY KEY,
  poste_source  varchar(120) NOT NULL,
  geom          geometry(Point, 4326),
  capa_dispo_mw double precision,
  source        text,
  fetched_at    timestamptz DEFAULT now()
);

-- ToS Google : TTL 30 jours STRICT, purge par le refresh mensuel, refresh lazy uniquement.
CREATE TABLE IF NOT EXISTS solar_api_cache (
  building_key  varchar(64) PRIMARY KEY,
  idu           varchar(14),
  payload       jsonb,
  imagery_quality varchar(16),
  imagery_date  date,
  fetched_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS solar_api_cache_idu_idx ON solar_api_cache (idu);
"""


def ensure_schema(session: Session) -> None:
    """Crée les tables du module si absentes (idempotent)."""
    session.execute(text(DDL_HABITAT_SOLAIRE))
