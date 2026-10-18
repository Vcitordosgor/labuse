"""ZONE-DONNÉES · LOT 1 — INGESTION SIRENE ÉTABLISSEMENTS ACTIFS GÉOLOCALISÉS (974) → `sirene_etablissements`.

Annuaire d'établissements adressés/géocodés, interrogeable par code NAF FIN dans une zone (les
« concurrents » de l'Étude de zone). DISTINCT du SIRENE d'enrichissement propriétaire (Score V).

SOURCE (choix M1, cf. docs/ZONE/RAPPORT-DONNEES-LOT0.md) : **fichier INSEE « Géolocalisation des
établissements du répertoire Sirene pour les études statistiques »** (parquet mensuel) JOINT à
**StockEtablissement** (parquet mensuel) sur le SIRET. Filtré 974 par DuckDB en lecture parquet
DISTANTE (pushdown `codeCommune LIKE '974%'`) — on ne télécharge jamais le national entier.

- POSITION : le fichier géo porte `x_longitude`/`y_latitude` en degrés décimaux (GPS) → on ingère le
  lon/lat DIRECTEMENT (`ST_MakePoint(lon, lat), 4326`), AUCUNE reprojection (La Réunion=EPSG 2975 mais
  on ne touche pas au x/y projeté — piège « océan » écarté). `qualite_xy` (LU, doc INSEE) est conservé.
- ACTIFS uniquement (`etatAdministratifEtablissement='A'`), NAF à la SOUS-CLASSE FINE (jamais agrégé).
- DIFFUSION : `statutDiffusionEtablissement`≠'O' (personne physique opposée) → dénomination/enseigne/
  adresse NON stockées en clair (`diffusible=false`) ; SIRET/NAF/position/commune restent (le NAF est
  diffusible → l'établissement compte dans la zone, son nom n'est jamais servi). Obligation légale.
- Effectif (`trancheEffectifsEtablissement`), IRIS (`plg_iris`) et QPV (`plg_qp24`) conservés (LOT 2/4).
- Millésime = date de publication du fichier géo (fraîcheur = source amont, jamais la date du run).

Idempotent : purge de la table avant réinsertion. CLI `ingest-sirene-etab` (cron mensuel Réunion).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "SIRENE établissements géolocalisés"
#: datasets data.gouv.fr (résolus à l'exécution → dernière publication mensuelle)
GEO_DATASET_ID = "61d5e2d372a52d9f9411ff88"     # géolocalisation INSEE pour études statistiques
STOCK_DATASET_ID = "5b7ffc618b4c4169d30727e0"   # base Sirene (StockEtablissement)

DDL = """
CREATE TABLE IF NOT EXISTS sirene_etablissements (
  siret          varchar(14) PRIMARY KEY,
  siren          varchar(9)  NOT NULL,
  naf            varchar(6),                 -- activité principale NAF rév.2 FINE (ex. 1071C)
  denomination   text,                       -- NULL si non diffusible (personne physique opposée)
  enseigne       text,                       -- NULL si non diffusible
  adresse        text,                       -- NULL si non diffusible
  commune        varchar(60),                -- nom canonique (== parcels.commune)
  insee          varchar(5),
  geom           geometry(Point, 4326),
  actif          boolean NOT NULL DEFAULT true,
  diffusible     boolean NOT NULL DEFAULT true,
  tranche_effectif varchar(2),               -- LOT 2 : code tranche INSEE ('NN' = non renseigné)
  date_creation  date,                       -- A3-bis (OUTILS-2) : date de création de l'établissement
                                              -- (StockEtablissement.dateCreationEtablissement) → « depuis AAAA »
  date_dernier_traitement date,              -- F2 (OUTILS-4) : dateDernierTraitementEtablissement — la
                                              -- FRAÎCHEUR déclarative par établissement (« mis à jour MM/YYYY »)
  qualite_xy     varchar(2),                 -- qualité de position (doc INSEE : 11/12/21/22/33)
  iris           varchar(9),                 -- rattachement IRIS (LOT 4) ; NULL si commune sans IRIS
  qp24           varchar(12),                -- rattachement QPV 2024
  millesime      varchar(64),                -- publication du fichier géo (fraîcheur amont)
  data_source_id integer,
  ingested_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_geom ON sirene_etablissements USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_naf  ON sirene_etablissements (naf);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_insee ON sirene_etablissements (insee);
-- FIX-ORFEVRE-1 point 3 (ORF-18 / H2.1) : fiche propriétaire WHERE siren = <siren> (app.py) + jointures
-- `ON se.siren = pm.siren` — sans lui, 1 seq scan de 155 k lignes PAR fiche (129 ms → 0,1 ms).
-- Le rebuild (DELETE+INSERT ci-dessous) PRÉSERVE les index ; aussi déclaré côté boot
-- (models.ensure_index_lectures_unitaires) pour les bases déjà créées.
CREATE INDEX IF NOT EXISTS ix_sirene_etab_siren ON sirene_etablissements (siren);
"""
#: colonnes ajoutées après coup (table pré-existante d'un mandat antérieur) — migration douce.
_ALTERS = [
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS tranche_effectif varchar(2)",
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS date_creation date",   # A3-bis (OUTILS-2)
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS date_dernier_traitement date",   # F2 (OUTILS-4)
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS qualite_xy varchar(2)",
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS iris varchar(9)",
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS qp24 varchar(12)",
    "ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS millesime varchar(64)",
    "ALTER TABLE sirene_etablissements ALTER COLUMN millesime TYPE varchar(64)",
]


def ensure_tables(session: Session) -> None:
    from ..db import sql_statements       # découpe GB-011-safe (un « ; » dans un commentaire ne casse pas)
    for stmt in sql_statements(DDL):
        session.execute(text(stmt))
    for a in _ALTERS:
        session.execute(text(a))
    session.flush()


def _latest_parquet(dataset_id: str, title_contains: str, title_excludes: tuple[str, ...] = ()) -> tuple[str, str]:
    """Résout l'URL du dernier parquet d'un dataset data.gouv + un millésime (AAAA-MM depuis l'URL)."""
    import re
    import httpx
    r = httpx.get(f"https://www.data.gouv.fr/api/1/datasets/{dataset_id}/", timeout=30.0)
    r.raise_for_status()
    for res in r.json().get("resources", []):
        t = res.get("title", "")
        if res.get("format") == "parquet" and title_contains in t and not any(x in t for x in title_excludes):
            url = res["url"]
            m = re.search(r"/(\d{4})(\d{2})\d{2}-", url)          # .../20260821-.../
            mill = f"{m.group(1)}-{m.group(2)}" if m else "millésime non daté"
            return url, mill
    raise RuntimeError(f"parquet « {title_contains} » introuvable dans le dataset {dataset_id}")


def build_sirene_etablissements(session: Session, *, geo_url: str | None = None,
                                stock_url: str | None = None, log=lambda *_: None) -> dict:
    """Joint le fichier géo INSEE et StockEtablissement (974, actifs) via DuckDB et charge la table.
    `geo_url`/`stock_url` permettent d'injecter des fichiers de test locaux ; sinon on résout les
    derniers parquets publiés sur data.gouv."""
    import duckdb

    from ..referentiel_communes import CORRECTIONS_INSEE_HERITEES
    from .run_all import REUNION_COMMUNES

    ensure_tables(session)
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": SOURCE_NAME}).scalar()
    # Noms canoniques : le code est la vérité (REUNION_COMMUNES), commune_conso_enaf par-dessus
    # (mêmes noms en pratique ; le repli évite un `commune` NULL si la table n'est pas chargée).
    insee2nom = dict(REUNION_COMMUNES)
    insee2nom.update(session.execute(text("SELECT insee, commune FROM commune_conso_enaf")).all())
    # FIX-ORFEVRE-1 (1c) — le référentiel communes (CIRCUIT-5) contraint l'ENTRÉE par FK
    # (`fk_sirene_etablissements_commune`, VALIDÉE) : un code INSEE hors 97401→97424 fait
    # échouer TOUT le rechargement (DELETE+INSERT rollback). Le chargeur applique donc les
    # corrections de coquilles CONNUES (ex. siret 83939934200147 : 97454 → 97411, CIRCUIT-5b)
    # puis ÉCARTE en comptant tout code resté hors référentiel (l'amont INSEE porte la coquille).
    corrections_insee = {(c["cle"], c["de"]): c["vers"] for c in CORRECTIONS_INSEE_HERITEES
                         if c["table"] == "sirene_etablissements"
                         and c["cle_col"] == "siret" and c["col"] == "insee"}
    insee_valides = {i for i, _ in REUNION_COMMUNES}

    mill = "millésime non daté"
    if geo_url is None:
        geo_url, mill = _latest_parquet(GEO_DATASET_ID, "géolocalisation établissements")
    if stock_url is None:
        stock_url, _ = _latest_parquet(STOCK_DATASET_ID, "StockEtablissement",
                                       title_excludes=("Historique", "Succession", "Doublons"))
    log(f"SIRENE : géo={mill} · jointure 974 actifs (DuckDB, parquet distant)…")

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET enable_progress_bar=false;")
    # jointure : stock (NAF/effectif/état/diffusion/noms) × géo (position GPS/qualité/IRIS/QPV) sur SIRET.
    rows = con.execute(f"""
        SELECT s.siret, s.activitePrincipaleEtablissement AS naf,
               s.statutDiffusionEtablissement AS diff, s.denominationUsuelleEtablissement AS denom,
               s.enseigne1Etablissement AS enseigne, s.codeCommuneEtablissement AS insee,
               s.trancheEffectifsEtablissement AS tranche,
               s.dateCreationEtablissement AS date_creation,   -- A3-bis (OUTILS-2)
               s.dateDernierTraitementEtablissement AS date_dernier_traitement,   -- F2 (OUTILS-4)
               trim(concat_ws(' ', s.numeroVoieEtablissement, s.typeVoieEtablissement,
                              s.libelleVoieEtablissement)) AS adresse,
               g.x_longitude AS lon, g.y_latitude AS lat, g.qualite_xy AS qualite,
               CASE WHEN g.plg_iris IN ('CSZ','') OR g.plg_iris IS NULL THEN NULL
                    ELSE concat(g.plg_code_commune, g.plg_iris) END AS iris,
               g.plg_qp24 AS qp24
        FROM read_parquet('{stock_url}') s
        JOIN (SELECT * FROM read_parquet('{geo_url}') WHERE plg_code_commune LIKE '974%') g
          ON g.siret = s.siret
        WHERE s.codeCommuneEtablissement LIKE '974%' AND s.etatAdministratifEtablissement = 'A'
          AND g.x_longitude IS NOT NULL AND g.y_latitude IS NOT NULL
    """).fetchall()
    log(f"  jointure : {len(rows)} établissements actifs géolocalisés — chargement…")

    session.execute(text("DELETE FROM sirene_etablissements"))
    raw = session.connection().connection            # DBAPI (psycopg) pour un executemany rapide
    cur = raw.cursor()
    sql = ("INSERT INTO sirene_etablissements (siret, siren, naf, denomination, enseigne, adresse, "
           "commune, insee, geom, actif, diffusible, tranche_effectif, date_creation, date_dernier_traitement, qualite_xy, iris, qp24, "
           "millesime, data_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s, "
           "ST_SetSRID(ST_MakePoint(%s,%s),4326), true, %s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (siret) DO NOTHING")
    batch, n, n_masq, n_hors_ref = [], 0, 0, 0
    for (siret, naf, diff, denom, enseigne, insee, tranche, date_creation, date_dernier_traitement, adresse, lon, lat, qualite, iris, qp24) in rows:
        if not siret or len(siret) != 14:
            continue
        insee = corrections_insee.get((siret, insee), insee)
        if insee not in insee_valides:            # FK communes : jamais un code hors référentiel
            n_hors_ref += 1
            continue
        diffusible = (diff == "O")
        if diffusible:
            den = (denom or "").strip()[:255] or None
            ens = (enseigne or "").strip()[:255] or None
            adr = (adresse or "").strip()[:255] or None
        else:                                        # diffusion partielle : ni nom ni adresse en clair
            den = ens = adr = None
            n_masq += 1
        naf_n = (naf or "").replace(".", "").strip().upper()[:6] or None
        batch.append((siret, siret[:9], naf_n, den, ens, adr, insee2nom.get(insee), insee,
                      float(lon), float(lat), diffusible, (tranche or None), date_creation, date_dernier_traitement,
                      (qualite or None), iris, (qp24 or None), f"SIRENE géolocalisé {mill} (INSEE)", sid))
        n += 1
        if len(batch) >= 5000:
            cur.executemany(sql, batch); batch.clear(); log(f"  … {n}")
    if batch:
        cur.executemany(sql, batch)
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now(), source_millesime = :m WHERE name = :n"),
        {"m": f"SIRENE géolocalisé {mill} (INSEE)", "n": SOURCE_NAME})
    session.flush()
    log(f"SIRENE établissements 974 : {n} actifs ({n_masq} en diffusion partielle, noms masqués, "
        f"{n_hors_ref} écartés hors référentiel communes) · {mill}")
    return {"n": n, "n_diffusion_partielle": n_masq, "n_hors_referentiel": n_hors_ref, "millesime": mill}
