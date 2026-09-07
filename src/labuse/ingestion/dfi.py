"""SOURCES-1 lot 6 — Documents de filiation informatisés (DFI) des parcelles, DGFiP.

La généalogie OFFICIELLE des parcelles (mère → filles), agrégée par la DGFiP et diffusée en
open data (data.gouv « Agrégation des fichiers de DFI des parcelles », trimestriel — vérifié
live 07/09/2026 : parquet national 199 Mo, 409 623 lignes 974, dates 1989-12-06 → 2025-12-29,
24 communes, 6 natures d'événement).

Lecture DISTANTE du parquet via duckdb (httpfs, range requests) filtrée code_departement='974'
— on ne télécharge jamais les 3,5 Go du CSV national. IDU reconstruits au format LABUSE :
insee(5) + prefixe(3) + parcelle(6, section 2 + numéro 4) = 14 caractères.

Pièges (fiche 18 du rapport, DITS) : ne couvre que les modifications DEPUIS l'informatisation
(1980-90+) ; exclut les aménagements fonciers ruraux ; géomètre anonymisé. L'écart avec le
canal « cadastre d'époque » (intersection géométrique des millésimes) est un CONTRÔLE croisé,
pas un conflit : la filiation dit l'événement officiel, l'époque dit la géométrie.

Rattachement des permis orphelins (mandat) : un permis Sitadel sans géométrie dont l'IDU
référence une parcelle MÈRE disparue est posé sur ses FILLES TERMINALES actuelles (descente
récursive de la filiation), geom = ST_PointOnSurface de l'union des filles présentes au
cadastre courant — même doctrine que cadastre_historique.rattacher_par_geometrie.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

PARQUET_URL = "https://dataeng-open.s3.rbx.io.cloud.ovh.net/dfi/dfi.parquet"
SOURCE_NAME = "DFI — documents de filiation informatisés (DGFiP)"

DDL = """
CREATE TABLE IF NOT EXISTS dfi_filiation (
    id               integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    insee            varchar(5)  NOT NULL,
    identifiant_dfi  varchar(12) NOT NULL,
    nature           varchar(64),
    date_validation  date,
    idu_mere         varchar(14) NOT NULL,
    idu_fille        varchar(14) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_dfi_mere  ON dfi_filiation (idu_mere);
CREATE INDEX IF NOT EXISTS ix_dfi_fille ON dfi_filiation (idu_fille);
CREATE INDEX IF NOT EXISTS ix_dfi_insee ON dfi_filiation (insee);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                cx.execute(text(stmt))


def ingest_dfi(session: Session, *, url: str = PARQUET_URL, log=print) -> dict:
    """Ingère la filiation 974 depuis le parquet DISTANT (duckdb/httpfs). Purge + réinsertion
    (idempotent, la source est un agrégat complet trimestriel). Rend les compteurs mesurés."""
    import duckdb

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    rows = con.execute(
        """SELECT code_insee, prefixe_section, identifiant_dfi, nom_nature_dfi,
                  date_validation_dfi, parcelle_mere, parcelle_fille
           FROM read_parquet(?) WHERE code_departement = '974'""", [url]).fetchall()
    con.close()
    session.execute(text("DELETE FROM dfi_filiation"))
    n = 0
    batch: list[dict] = []
    ins = text(
        "INSERT INTO dfi_filiation (insee, identifiant_dfi, nature, date_validation, "
        "idu_mere, idu_fille) VALUES (:i, :d, :n, :dt, :m, :f)")
    for insee, prefixe, ident, nature, dt, mere, fille in rows:
        if not (insee and mere and fille):
            continue
        pref = (prefixe or "000").zfill(3)
        batch.append({"i": insee, "d": ident, "n": nature, "dt": dt,
                      "m": f"{insee}{pref}{mere}", "f": f"{insee}{pref}{fille}"})
        n += 1
        if len(batch) >= 5000:
            session.execute(ins, batch)
            batch = []
    if batch:
        session.execute(ins, batch)
    session.flush()
    d = session.execute(text(
        "SELECT count(DISTINCT insee), min(date_validation), max(date_validation), "
        "count(DISTINCT idu_mere) FROM dfi_filiation")).one()
    log(f"  DFI 974 : {n} liens mère→fille · {d[0]} communes · {d[1]} → {d[2]} · "
        f"{d[3]} parcelles mères")
    return {"liens": n, "communes": int(d[0]),
            "date_min": str(d[1]), "date_max": str(d[2]), "meres": int(d[3])}


def filiation_parcelle(session: Session, idu: str, limit: int = 24) -> dict | None:
    """La filiation OFFICIELLE d'une parcelle : d'où elle vient (mères), ce qu'elle est
    devenue (filles). Passe-plat trié par date. None si la parcelle n'apparaît dans aucun
    DFI (l'absence est normale : informatisation 1980-90+, jamais un zéro menteur)."""
    meres = session.execute(text(
        "SELECT idu_mere AS idu, nature, date_validation FROM dfi_filiation "
        "WHERE idu_fille = :i ORDER BY date_validation DESC NULLS LAST LIMIT :l"),
        {"i": idu, "l": limit}).mappings().all()
    filles = session.execute(text(
        "SELECT idu_fille AS idu, nature, date_validation FROM dfi_filiation "
        "WHERE idu_mere = :i ORDER BY date_validation DESC NULLS LAST LIMIT :l"),
        {"i": idu, "l": limit}).mappings().all()
    if not meres and not filles:
        return None
    # codes AMONT (pas des parcelles) : fille 'PDP' = passage au domaine public ;
    # mère 'EDNC' = issue d'un ensemble non cadastré — étiquetés lisiblement, jamais joints.
    _CODES = {"PDP": "passage au domaine public", "EDNC": "issue du non-cadastré"}

    def _fmt(rows):
        out = []
        for r in rows:
            code = r["idu"][8:] if len(r["idu"]) != 14 else None
            out.append({"idu": r["idu"], "nature": r["nature"],
                        "code_amont": _CODES.get(code) if code else None,
                        "date": r["date_validation"].isoformat() if r["date_validation"] else None})
        return out
    derniere = max((r["date_validation"] for r in [*meres, *filles] if r["date_validation"]),
                   default=None)
    return {"meres": _fmt(meres) or None, "filles": _fmt(filles) or None,
            "division_recente": bool(filles and derniere and
                                     (derniere.year >= 2023)),
            "source": "DGFiP — documents de filiation informatisés (trimestriel)"}


def rattacher_permis_par_filiation(session: Session, log=print) -> dict:
    """Mandat SOURCES-1 lot 6 — rejoue les permis Sitadel SANS géométrie via la filiation
    officielle : IDU référencé = parcelle mère disparue → filles TERMINALES (récursif, garde
    de profondeur 8) présentes au cadastre courant → geom = ST_PointOnSurface(union des
    filles). raw.geoloc dit la provenance ('filiation DFI'), raw.parcelles_actuelles liste
    les filles. Ne touche JAMAIS un permis déjà géolocalisé. Rend les compteurs mesurés."""
    avant = session.execute(text(
        "SELECT count(*) FROM sitadel_permits WHERE geom IS NULL")).scalar() or 0
    n = session.execute(text("""
        WITH RECURSIVE orphelins AS (
          SELECT s.id, t.idu
          FROM sitadel_permits s
          JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS t(idu) ON true
          WHERE s.geom IS NULL),
        descente AS (
          SELECT o.id, o.idu AS origine, f.idu_fille, 1 AS prof
          FROM orphelins o JOIN dfi_filiation f ON f.idu_mere = o.idu
          UNION
          SELECT d.id, d.origine, f.idu_fille, d.prof + 1
          FROM descente d JOIN dfi_filiation f ON f.idu_mere = d.idu_fille
          WHERE d.prof < 8),
        terminales AS (   -- filles présentes au cadastre COURANT (la descente s'y arrête)
          SELECT DISTINCT d.id, d.origine, p.idu AS idu_actuel, p.geom_2975
          FROM descente d JOIN parcels p ON p.idu = d.idu_fille),
        rattache AS (
          SELECT id, min(origine) AS origine,
                 jsonb_agg(DISTINCT idu_actuel) AS actuelles,
                 ST_PointOnSurface(ST_Union(geom_2975)) AS g
          FROM terminales GROUP BY id)
        UPDATE sitadel_permits s
        SET geom = ST_Transform(r.g, 4326),
            raw = s.raw || jsonb_build_object(
              'geoloc', 'filiation DFI (mère → filles, DGFiP)',
              'parcelle_origine', r.origine,
              'parcelles_actuelles', r.actuelles,
              'origine_redecoupee', jsonb_array_length(r.actuelles) > 1)
        FROM rattache r WHERE s.id = r.id""")).rowcount
    session.flush()
    apres = session.execute(text(
        "SELECT count(*) FROM sitadel_permits WHERE geom IS NULL")).scalar() or 0
    log(f"  filiation DFI : {n} permis orphelins rattachés · {avant} → {apres} sans géométrie")
    return {"avant": int(avant), "rattaches": int(n), "restants": int(apres)}
