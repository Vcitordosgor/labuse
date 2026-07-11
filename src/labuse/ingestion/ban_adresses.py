"""Liaison adresses ↔ parcelles — ingestion BAN 974 (mandat wave-adresses, Lot 1).

Source : export départemental officiel de la Base Adresse Nationale (Licence Ouverte),
~340 000 adresses. Table `adresses` = LA référence locale de géocodage du produit
(règle générale : tout géocodage — Flash, Copro, publipostage — passe par cette table,
plus par l'API BAN en ligne).

Rattachement parcelle, dans l'ordre :
  1. `parcelle`   — point-dans-parcelle (ST_Contains, méthode principale du mandat) ;
  2. `ban_cad`    — référence cadastrale portée par la BAN elle-même (cad_parcelles,
                    remplie à ~35 %), quand le point tombe hors de toute parcelle ;
  3. `proche_20m` — plus proche parcelle à moins de 20 m ;
  4. NULL         — adresse non rattachable (rare).

Refresh MENSUEL (la BAN bouge) : deploy/cron.d/ban — remplacement complet idempotent.
"""
from __future__ import annotations

import gzip
import logging
import shutil
import tempfile
import time
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.ingestion.ban")

BAN_URL = "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz"

DDL_ADRESSES = """
CREATE TABLE IF NOT EXISTS adresses (
  id_ban        varchar(40) PRIMARY KEY,      -- clé d'interopérabilité BAN
  numero        varchar(8),
  rep           varchar(16),                  -- bis/ter/…
  voie          varchar(200) NOT NULL,        -- nom_voie, sinon lieu-dit
  code_postal   varchar(5),
  commune       varchar(80),
  insee         varchar(5),
  geom          geometry(Point, 4326),
  geom_2975     geometry(Point, 2975),
  idu           varchar(14),                  -- parcelle rattachée (NULL si non rattachable)
  rattachement  varchar(12),                  -- 'parcelle' | 'ban_cad' | 'proche_20m'
  refreshed_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS adresses_idu_idx ON adresses (idu);
CREATE INDEX IF NOT EXISTS adresses_geom_2975_gix ON adresses USING gist (geom_2975);
-- autocomplete : préfixe de voie dans une commune (lower + varchar_pattern_ops → LIKE 'x%')
CREATE INDEX IF NOT EXISTS adresses_insee_voie_idx
  ON adresses (insee, lower(voie) varchar_pattern_ops);

-- INDEX INVERSE n-n (mandat Lot 1.3) : une parcelle porte plusieurs adresses ET une
-- adresse dessert plusieurs parcelles (assiette cad_parcelles BAN, bâtiment à cheval).
-- adresses.idu reste la parcelle PRINCIPALE (celle du point). Cette table sert les
-- lectures parcelle → adresses (fiche, exports, dossier).
CREATE TABLE IF NOT EXISTS adresse_parcelles (
  id_ban  varchar(40) NOT NULL REFERENCES adresses(id_ban) ON DELETE CASCADE,
  idu     varchar(14) NOT NULL,
  source  varchar(14) NOT NULL,   -- 'principal' | 'ban_cad' | 'bati_partage'
  PRIMARY KEY (id_ban, idu)
);
CREATE INDEX IF NOT EXISTS adresse_parcelles_idu_idx ON adresse_parcelles (idu);
"""

#: colonnes du CSV BAN (ordre du fichier officiel — vérifié sur l'export du 10/07/2026)
_CSV_COLS = ("id, id_fantoir, numero, rep, nom_voie, code_postal, code_insee, nom_commune,"
             " code_insee_ancienne_commune, nom_ancienne_commune, x, y, lon, lat,"
             " type_position, alias, nom_ld, libelle_acheminement, nom_afnor,"
             " source_position, source_nom_voie, certification_commune, cad_parcelles")


def download_ban_csv(dest_dir: Path, timeout_s: float = 120.0) -> Path:
    """Télécharge et décompresse l'export BAN 974 → chemin du CSV."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    gz = dest_dir / "adresses-974.csv.gz"
    csv = dest_dir / "adresses-974.csv"
    with httpx.stream("GET", BAN_URL, timeout=timeout_s, follow_redirects=True) as resp:
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False) as tmp:
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
    Path(tmp.name).replace(gz)
    with gzip.open(gz, "rb") as fin, open(csv, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    log.info("BAN 974 téléchargée : %s (%.1f Mo)", csv, csv.stat().st_size / 1e6)
    return csv


def _copy_staging(session: Session, csv_path: Path) -> int:
    """CSV → table de staging (COPY psycopg3 — 340 k lignes en quelques secondes)."""
    cols_ddl = ", ".join(f"{c.strip()} text" for c in _CSV_COLS.split(","))
    session.execute(text(f"CREATE TEMP TABLE ban_staging ({cols_ddl}) ON COMMIT DROP"))
    raw = session.connection().connection  # connexion psycopg3 sous SQLAlchemy
    with raw.cursor() as cur, cur.copy(
            "COPY ban_staging FROM STDIN (FORMAT csv, DELIMITER ';', HEADER true)") as cp:
        with open(csv_path, "rb") as fh:
            while chunk := fh.read(1 << 20):
                cp.write(chunk)
    return int(session.execute(text("SELECT count(*) FROM ban_staging")).scalar() or 0)


def _rattacher(session: Session) -> dict[str, int]:
    """Les trois passes de rattachement parcelle (ordre du mandat)."""
    stats: dict[str, int] = {}
    # 1) Point-dans-parcelle — méthode principale.
    stats["parcelle"] = session.execute(text(
        """UPDATE adresses a SET idu = p.idu, rattachement = 'parcelle'
           FROM parcels p
           WHERE a.idu IS NULL AND ST_Contains(p.geom_2975, a.geom_2975)""")).rowcount
    # 2) Référence cadastrale BAN (cad_parcelles, valeurs multiples séparées par |) —
    #    seulement si l'IDU existe vraiment dans nos parcelles.
    stats["ban_cad"] = session.execute(text(
        """UPDATE adresses a SET idu = c.idu, rattachement = 'ban_cad'
           FROM (SELECT DISTINCT ON (s.id) s.id, p.idu
                 FROM ban_staging s,
                      unnest(string_to_array(s.cad_parcelles, '|')) AS cad
                 JOIN parcels p ON p.idu = cad
                 WHERE s.cad_parcelles <> '' ORDER BY s.id, p.idu) c
           WHERE a.id_ban = c.id AND a.idu IS NULL""")).rowcount
    # 3) Plus proche parcelle < 20 m (KNN sur le reliquat).
    session.execute(text(
        """UPDATE adresses a SET idu = (
               SELECT p.idu FROM parcels p
               WHERE ST_DWithin(p.geom_2975, a.geom_2975, 20)
               ORDER BY p.geom_2975 <-> a.geom_2975 LIMIT 1)
           WHERE a.idu IS NULL"""))
    stats["proche_20m"] = session.execute(text(
        "UPDATE adresses SET rattachement = 'proche_20m' "
        "WHERE idu IS NOT NULL AND rattachement IS NULL")).rowcount
    return stats


def _index_inverse(session: Session) -> dict[str, int]:
    """Reconstruit adresse_parcelles (index inverse n-n) — trois sources, dans l'ordre.

    1. `principal`    : la parcelle du point (adresses.idu) ;
    2. `ban_cad`      : TOUTES les parcelles de l'assiette cad_parcelles BAN (une adresse
                        peut desservir plusieurs parcelles de la même propriété) ;
    3. `bati_partage` : un bâtiment (BD TOPO, recouvrement > 15 m² de part et d'autre)
                        à cheval sur une parcelle adressée et une parcelle sans adresse →
                        même propriété, l'adresse vaut pour les deux.
    """
    session.execute(text("DELETE FROM adresse_parcelles"))
    out: dict[str, int] = {}
    out["inv_principal"] = session.execute(text(
        """INSERT INTO adresse_parcelles (id_ban, idu, source)
           SELECT id_ban, idu, 'principal' FROM adresses WHERE idu IS NOT NULL
           ON CONFLICT DO NOTHING""")).rowcount
    out["inv_ban_cad"] = session.execute(text(
        """INSERT INTO adresse_parcelles (id_ban, idu, source)
           SELECT DISTINCT s.id, cad, 'ban_cad'
           FROM ban_staging s
           CROSS JOIN LATERAL unnest(string_to_array(s.cad_parcelles, '|')) AS cad
           JOIN parcels p ON p.idu = cad
           JOIN adresses a ON a.id_ban = s.id
           WHERE s.cad_parcelles <> ''
           ON CONFLICT DO NOTHING""")).rowcount
    # Bâtiment à cheval : parcelle bâtie SANS adresse ← adresse de la parcelle voisine
    # partageant le même bâtiment (seuil 15 m² des deux côtés : évite les débords de toit).
    # Résilience : la passe est sautée si ses sources manquent (base partielle, tests).
    sources_ok = session.execute(text(
        "SELECT to_regclass('parcel_residuel_bati') IS NOT NULL"
        " AND to_regclass('spatial_layers') IS NOT NULL")).scalar()
    if not sources_ok:
        out["inv_bati_partage"] = 0
        return out
    out["inv_bati_partage"] = session.execute(text(
        """INSERT INTO adresse_parcelles (id_ban, idu, source)
           SELECT DISTINCT ap.id_ban, s.idu, 'bati_partage'
           FROM (SELECT p.idu, p.geom_2975 FROM parcel_residuel_bati rb
                 JOIN parcels p ON p.idu = rb.idu
                 WHERE rb.emprise_batie_m2 >= 20
                   AND NOT EXISTS (SELECT 1 FROM adresse_parcelles x WHERE x.idu = rb.idu)) s
           JOIN spatial_layers b ON b.kind = 'batiment'
             AND ST_Intersects(b.geom_2975, s.geom_2975)
             AND ST_Area(ST_Intersection(b.geom_2975, s.geom_2975)) > 15
           JOIN parcels p2 ON p2.idu <> s.idu
             AND ST_Intersects(b.geom_2975, p2.geom_2975)
             AND ST_Area(ST_Intersection(b.geom_2975, p2.geom_2975)) > 15
           JOIN adresse_parcelles ap ON ap.idu = p2.idu
           ON CONFLICT DO NOTHING""")).rowcount
    return out


def ingest_ban(session: Session, csv_path: Path | str) -> dict:
    """Ingestion complète (remplacement idempotent) + rattachement parcelles → stats."""
    t0 = time.monotonic()
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV BAN introuvable : {csv_path}")
    for stmt in DDL_ADRESSES.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))
    n_staging = _copy_staging(session, csv_path)

    session.execute(text("DELETE FROM adresses"))
    session.execute(text(
        """INSERT INTO adresses (id_ban, numero, rep, voie, code_postal, commune, insee,
                                 geom, geom_2975)
           SELECT id, NULLIF(numero, ''), NULLIF(rep, ''),
                  COALESCE(NULLIF(nom_voie, ''), NULLIF(nom_ld, '')),
                  NULLIF(code_postal, ''), nom_commune, code_insee,
                  ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326),
                  ST_Transform(ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326), 2975)
           FROM ban_staging
           WHERE lon <> '' AND lat <> ''
             AND COALESCE(NULLIF(nom_voie, ''), NULLIF(nom_ld, '')) IS NOT NULL
           ON CONFLICT (id_ban) DO NOTHING"""))
    total = int(session.execute(text("SELECT count(*) FROM adresses")).scalar() or 0)

    stats = _rattacher(session)
    stats.update(_index_inverse(session))
    session.execute(text("ANALYZE adresses"))
    session.execute(text("ANALYZE adresse_parcelles"))
    liees = int(session.execute(text(
        "SELECT count(*) FROM adresses WHERE idu IS NOT NULL")).scalar() or 0)
    out = {"staging": n_staging, "adresses": total, "liees": liees,
           "taux_liees": round(liees / total, 4) if total else 0.0,
           **stats, "duree_s": round(time.monotonic() - t0, 1)}
    log.info("BAN ingérée : %s", out)
    return out


def couverture_bati_residentiel(session: Session, emprise_min: float = 20.0) -> dict:
    """Critère d'acceptation : part des parcelles bâties résidentielles portant AU MOINS
    une adresse (index inverse). Proxy « résidentiel » = emprise BD TOPO ≥ emprise_min
    (le seuil est discutable — une annexe isolée de 25 m² n'est pas un logement)."""
    row = session.execute(text(
        """SELECT count(*) AS baties,
                  count(*) FILTER (WHERE EXISTS (
                      SELECT 1 FROM adresse_parcelles ap WHERE ap.idu = rb.idu)) AS avec_adresse
           FROM parcel_residuel_bati rb
           WHERE rb.emprise_batie_m2 >= :emprise_min""",
        ), {"emprise_min": emprise_min}).mappings().first()
    baties = int(row["baties"] or 0)
    avec = int(row["avec_adresse"] or 0)
    return {"parcelles_baties": baties, "avec_adresse": avec, "emprise_min": emprise_min,
            "taux": round(avec / baties, 4) if baties else 0.0}


# ── Copropriétés RNIC sans parcelle : rattachement PAR ADRESSE (ajout session 10/07) ──

#: abréviations usuelles du RNIC → libellés BAN (comparaison après normalisation)
_ABREV = {"r": "rue", "av": "avenue", "ave": "avenue", "bd": "boulevard", "che": "chemin",
          "chem": "chemin", "imp": "impasse", "all": "allee", "pl": "place", "rte": "route",
          "sq": "square", "res": "residence", "lot": "lotissement", "crs": "cours",
          "prom": "promenade", "sen": "sentier", "mte": "montee"}


def _norm_voie(v: str) -> str:
    import re
    import unicodedata
    v = unicodedata.normalize("NFKD", v.lower()).encode("ascii", "ignore").decode()
    mots = [m for m in re.split(r"[^a-z0-9]+", v) if m]
    if mots and mots[0] in _ABREV:
        mots[0] = _ABREV[mots[0]]
    return " ".join(mots)


def rattacher_copros_par_adresse(session: Session) -> dict:
    """Rattache les copropriétés RNIC sans parcelle via la table `adresses`.

    Match exigeant (numéro + voie normalisée + INSEE, candidat UNIQUE) : mieux vaut un
    « aucun » honnête qu'un rattachement faux — le reliquat reste rattachement='aucun'.
    """
    import re
    copros = session.execute(text(
        "SELECT numero_immatriculation, adresse, insee FROM rnic_coproprietes "
        "WHERE parcelle_idu IS NULL AND adresse IS NOT NULL")).mappings().all()
    lies, ambigues, sans_match = 0, 0, 0
    for c in copros:
        m = re.match(r"\s*(\d+)\s*(?:[-/]\d+)*\s+(.+?)\s+97\d{3}\b", c["adresse"])
        if not m:
            sans_match += 1
            continue
        numero, voie_norm = m.group(1), _norm_voie(m.group(2))
        cands = session.execute(text(
            "SELECT DISTINCT voie, idu FROM adresses "
            "WHERE insee = :insee AND numero = :num AND idu IS NOT NULL"),
            {"insee": c["insee"], "num": numero}).all()
        idus = {idu for voie, idu in cands if _norm_voie(voie) == voie_norm}
        if len(idus) == 1:
            session.execute(text(
                "UPDATE rnic_coproprietes SET parcelle_idu = :idu, rattachement = 'adresse' "
                "WHERE numero_immatriculation = :ni"),
                {"idu": idus.pop(), "ni": c["numero_immatriculation"]})
            lies += 1
        elif len(idus) > 1:
            ambigues += 1
        else:
            sans_match += 1
    out = {"candidates": len(copros), "liees": lies, "ambigues": ambigues,
           "sans_match": sans_match}
    log.info("copros RNIC rattachées par adresse : %s", out)
    return out
