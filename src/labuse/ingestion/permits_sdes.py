"""Ingestion SITADEL — flux national SDES/Dido, dispositif Sitadel3  [✓ live 10/07/2026].

Source VIVANTE des autorisations d'urbanisme (l'ODS Région, cf. permits.py, est mort depuis
2023-09). Dataset Dido « Liste des permis de construire et autres autorisations d'urbanisme »
(id 6513f0189d7d312c80ec5b5b, licence LO, MAJ MENSUELLE, historique 2013+, Sitadel3 depuis
mars 2026) — page : statistiques.developpement-durable.gouv.fr/donnees-des-permis-de-construire…

Endpoint retenu (API Dido v1, VÉRIFIÉ live) — export CSV filtré serveur, par datafile :
  GET https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1
      /datafiles/{rid}/csv?withColumnName=true&DEP_CODE=eq:974
      [&DATE_REELLE_AUTORISATION=gte:YYYY-MM-DD]        ← delta du refresh mensuel
4 datafiles : PC/DP logements · PC/DP locaux non résidentiels · PA · PD (rids ci-dessous).

Schéma Sitadel3 VÉRIFIÉ sur données réelles (endpoint /rows, 10/07/2026), pas deviné :
 - identifiant/type : TYPE_DAU + NUM_DAU (logements, locaux) ; NUM_PA ; NUM_PD
 - état : ETAT_DAU | ETAT_PA | ETAT_PD (code) ; dates : DATE_REELLE_AUTORISATION,
   DATE_REELLE_DAACT (logements/locaux seulement), DPC_* ;
 - nature : NB_LGT_TOT_CREES, SURF_HAB_CREEE, DESTINATION_PRINCIPALE (logements) ;
 - cadastre : SEC_CADASTREn/NUM_CADASTREn — 3 paires aujourd'hui, JUSQU'À 15 annoncées
   (déploiement progressif Sitadel3) → boucle GÉNÉRIQUE sur les colonnes présentes ;
 - pétitionnaire : DENOM_DEM / SIREN_DEM / SIRET_DEM présents dans le flux OPEN DATA
   (personnes morales seulement, les physiques sont anonymisées — champs vides) →
   stockés dans raw (petitioner_name / petitioner_siren / petitioner_siret), index
   d'interrogation sur (raw->>'petitioner_siret') posé par ensure_indexes() ;
 - photovoltaïque : ANNONCÉ par le SDES, PAS ENCORE dans le flux au 10/07/2026 —
   capté automatiquement dans raw['pv'] dès qu'une colonne PV*/I_PHOTOVOLT* apparaîtra.

Contrats PRÉSERVÉS : schéma sitadel_permits inchangé (les évolutions passent par idu_codes
et raw), clés raw identiques à l'ODS (nb_lgt, surf_hab, destination, daact, etat) pour que
_nature()/_statut() (permits.py) et le signal new_permit_nearby restent intacts.

CLI idempotente :  python -m labuse.ingestion.permits_sdes            (backfill complet 2013+)
                   python -m labuse.ingestion.permits_sdes --refresh  (delta, recouvrement 3 mois)
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .permits import _idu  # même reconstruction IDU 14 car. que la voie ODS historique

DIDO = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1"
DATASET_ID = "6513f0189d7d312c80ec5b5b"
SOURCE_NAME = "SITADEL (autorisations d'urbanisme)"
DEP = "974"

#: rid Dido par famille (VÉRIFIÉS live 10/07/2026) + colonnes identifiant/état propres à chacune.
DATAFILES = {
    "logements": {"rid": "8b35affb-55fc-4c1f-915b-7750f974446a",
                  "num": "NUM_DAU", "type_col": "TYPE_DAU", "etat": "ETAT_DAU"},
    "locaux":    {"rid": "f8f0700f-806c-40a7-83b1-f21cf507e7c4",
                  "num": "NUM_DAU", "type_col": "TYPE_DAU", "etat": "ETAT_DAU"},
    "pa":        {"rid": "96883f50-538b-41f9-a059-c6eb97e6a23a",
                  "num": "NUM_PA", "type_fixe": "PA", "etat": "ETAT_PA"},
    "pd":        {"rid": "1a9a2f0c-56fe-4e69-84a7-fbbda2121f02",
                  "num": "NUM_PD", "type_fixe": "PD", "etat": "ETAT_PD"},
}

REFRESH_OVERLAP_MONTHS = 3   # recouvrement du delta : capte les états/DAACT tardifs
_RX_CAD = re.compile(r"^SEC_CADASTRE(\d+)$")
_RX_PV = re.compile(r"PHOTOVOLT|^PV_|^I_PV", re.IGNORECASE)


def _fetch_csv(rid: str, since: str | None = None, timeout: float = 300.0) -> str:
    """CSV du datafile, FILTRÉ SERVEUR (DEP 974 [+ date ≥ since]) — dernier millésime."""
    params = ["withColumnName=true", "withColumnDescription=false", "withColumnUnit=false",
              f"DEP_CODE=eq:{DEP}"]
    if since:
        params.append(f"DATE_REELLE_AUTORISATION=gte:{since}")
    url = f"{DIDO}/datafiles/{rid}/csv?" + "&".join(params)
    with httpx.Client(timeout=timeout, headers={"User-Agent": constants.USER_AGENT},
                      follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def _commune_map(session: Session) -> dict[str, str]:
    """INSEE → nom de commune, dérivé du référentiel parcelles (les 24 communes)."""
    rows = session.execute(text(
        "SELECT DISTINCT substring(idu FROM 1 FOR 5), commune FROM parcels")).all()
    return {r[0]: r[1] for r in rows}


def _cadastre_pairs(fieldnames: list[str]) -> list[tuple[str, str]]:
    """Paires (SEC_CADASTREn, NUM_CADASTREn) RÉELLEMENT présentes — génériques (3 → 15)."""
    pairs = []
    for f in fieldnames:
        m = _RX_CAD.match(f)
        if m and f"NUM_CADASTRE{m.group(1)}" in fieldnames:
            pairs.append((f, f"NUM_CADASTRE{m.group(1)}"))
    return sorted(pairs, key=lambda p: int(_RX_CAD.match(p[0]).group(1)))


_UPSERT = text(
    """INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw)
       SELECT :pid, :typ, :dt, CAST(:idus AS jsonb), :c,
              (SELECT centroid FROM parcels WHERE idu = ANY(:idu_arr) LIMIT 1),
              CAST(:raw AS jsonb)
       ON CONFLICT (permit_id) DO UPDATE SET
         type = EXCLUDED.type, date = EXCLUDED.date, idu_codes = EXCLUDED.idu_codes,
         commune = EXCLUDED.commune, raw = EXCLUDED.raw,
         geom = COALESCE(EXCLUDED.geom, sitadel_permits.geom)""")


def ensure_indexes(session: Session, log=print) -> None:
    """Contrainte unique permit_id (après PURGE des doublons préexistants, le meilleur survit :
    géolocalisé d'abord, puis le plus récent) + index pétitionnaire (raw->>'petitioner_siret')."""
    purged = session.execute(text(
        """DELETE FROM sitadel_permits s USING (
             SELECT id, row_number() OVER (PARTITION BY permit_id
                      ORDER BY (geom IS NOT NULL) DESC, id DESC) AS rn
             FROM sitadel_permits WHERE permit_id IS NOT NULL) d
           WHERE s.id = d.id AND d.rn > 1""")).rowcount
    if purged:
        log(f"  doublons préexistants purgés : {purged}")
    session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sitadel_permit ON sitadel_permits (permit_id)"))
    session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_sitadel_petitioner_siret "
        "ON sitadel_permits ((raw->>'petitioner_siret'))"))
    session.flush()


def ingest_sdes(session: Session, since: str | None = None, log=print) -> dict:
    """Ingestion (backfill si since=None, delta sinon) des 4 datafiles — idempotente (upsert)."""
    communes = _commune_map(session)
    stats = {"lignes": 0, "upserts": 0, "sans_cadastre": 0, "petitioner": 0, "pv_col": None}
    for key, df in DATAFILES.items():
        raw_csv = _fetch_csv(df["rid"], since=since)
        reader = csv.DictReader(io.StringIO(raw_csv), delimiter=";")
        fields = reader.fieldnames or []
        pairs = _cadastre_pairs(fields)
        pv_cols = [f for f in fields if _RX_PV.search(f)]
        if pv_cols and not stats["pv_col"]:
            stats["pv_col"] = pv_cols[0]
        n_file = 0
        for rec in reader:
            stats["lignes"] += 1
            insee = (rec.get("COMM") or "").strip()
            pid = (rec.get(df["num"]) or "").strip()
            if not insee or not pid:
                continue
            idus = []
            for sec_col, num_col in pairs:
                idu = _idu(insee, rec.get(sec_col), rec.get(num_col))
                if idu and idu not in idus:
                    idus.append(idu)
            if not idus:
                stats["sans_cadastre"] += 1   # même règle que la voie ODS : pas de réf = pas de ligne
                continue
            raw = {"src": "SDES Dido — Sitadel3 (974)",
                   "nb_lgt": rec.get("NB_LGT_TOT_CREES"),
                   "surf_hab": rec.get("SURF_HAB_CREEE"),
                   "destination": rec.get("DESTINATION_PRINCIPALE"),
                   "daact": rec.get("DATE_REELLE_DAACT") or None,
                   "etat": rec.get(df["etat"]),
                   "famille": key}
            denom, siren, siret = (rec.get("DENOM_DEM") or "").strip(), \
                (rec.get("SIREN_DEM") or "").strip(), (rec.get("SIRET_DEM") or "").strip()
            if denom or siret or siren:   # personnes morales seulement (PP anonymisées → vides)
                raw.update({"petitioner_name": denom or None,
                            "petitioner_siren": siren or None,
                            "petitioner_siret": siret or None})
                stats["petitioner"] += 1
            for col in pv_cols:
                if rec.get(col) not in (None, ""):
                    raw["pv"] = rec[col]
            session.execute(_UPSERT, {
                "pid": pid, "typ": (rec.get(df.get("type_col")) or df.get("type_fixe") or "").strip() or None,
                "dt": rec.get("DATE_REELLE_AUTORISATION") or None,
                "idus": json.dumps(idus), "idu_arr": idus,
                "c": communes.get(insee, insee),
                "raw": json.dumps(raw, ensure_ascii=False)})
            stats["upserts"] += 1
            n_file += 1
            if n_file % 2000 == 0:
                session.flush()
                log(f"  {key} : {n_file}…")
        session.flush()
        log(f"  ✓ {key} : {n_file} upserts")
    return stats


def geocode_missing(session: Session, log=print, cap_pairs: int = 400) -> dict:
    """Fallback géoloc des permis SANS geom : centroïdes cadastraux via API Carto, PAR
    (commune, section) réellement référencée — version CIBLÉE de
    permits.geocode_permits_via_cadastre (qui balaye toutes les sections d'UNE commune)."""
    from ..connectors.cadastre import CadastreConnector, parse_parcelles
    before = session.execute(text(
        "SELECT count(*) FROM sitadel_permits WHERE geom IS NOT NULL")).scalar()
    pairs = session.execute(text(
        """SELECT DISTINCT substring(idu FROM 1 FOR 5) AS insee, substring(idu FROM 9 FOR 2) AS sec
           FROM (SELECT jsonb_array_elements_text(idu_codes) AS idu
                 FROM sitadel_permits WHERE geom IS NULL) q
           WHERE idu IS NOT NULL ORDER BY 1, 2""")).all()
    if len(pairs) > cap_pairs:
        log(f"  ⚠ {len(pairs)} couples (commune, section) — plafonné à {cap_pairs} (relancer pour la suite)")
        pairs = pairs[:cap_pairs]
    conn = CadastreConnector()
    lookup: dict[str, str] = {}
    for insee, sec in pairs:
        try:
            fc = conn.fetch_by_section(insee, sec)
        except Exception:  # noqa: BLE001 — une section qui échoue n'arrête pas le lot
            continue
        for p in parse_parcelles(fc):
            if p.get("idu") and p.get("geometry"):
                lookup[p["idu"]] = json.dumps(p["geometry"])
    n = 0
    for pid, idus in session.execute(text(
            "SELECT id, idu_codes FROM sitadel_permits WHERE geom IS NULL")).all():
        gj = next((lookup[i] for i in (idus or []) if i in lookup), None)
        if gj:
            session.execute(text(
                "UPDATE sitadel_permits SET geom = ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:gj),4326)) "
                "WHERE id = :id"), {"gj": gj, "id": pid})
            n += 1
    session.flush()
    after = session.execute(text(
        "SELECT count(*) FROM sitadel_permits WHERE geom IS NOT NULL")).scalar()
    return {"avant": int(before), "ajoutes": n, "apres": int(after), "paires": len(pairs)}


def refresh_since(session: Session) -> str:
    """Borne du delta : max(date) en base − 3 mois (recouvrement états/DAACT tardifs)."""
    mx = session.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()
    base = (mx or datetime(2013, 1, 1, tzinfo=timezone.utc))
    return (base - timedelta(days=REFRESH_OVERLAP_MONTHS * 31)).date().isoformat()


def run(refresh: bool = False, geocode: bool = True, log=print) -> dict:
    """Point d'entrée (CLI + cron) : ingestion + fallback géoloc + traçage ingestion_runs."""
    from ..db import session_scope

    with session_scope() as s:
        run_id = s.execute(text(
            "INSERT INTO ingestion_runs (commune, status) VALUES (:c, 'running') RETURNING id"),
            {"c": f"974 (SDES Sitadel3{' — refresh' if refresh else ' — backfill'})"}).scalar()
        s.flush()
        try:
            ensure_indexes(s, log=log)
            since = refresh_since(s) if refresh else None
            log(f"SDES Sitadel3 — {'delta depuis ' + since if since else 'backfill complet 2013+'}")
            stats = ingest_sdes(s, since=since, log=log)
            if geocode:
                stats["geocode"] = geocode_missing(s, log=log)
            s.execute(text(
                "UPDATE ingestion_runs SET finished_at = now(), status = 'ok', "
                "parcels_count = :n WHERE id = :id"), {"n": stats["upserts"], "id": run_id})
            s.execute(text(
                "UPDATE data_sources SET last_sync_at = now() WHERE name = :n"),
                {"n": SOURCE_NAME})
        except Exception:
            s.execute(text(
                "UPDATE ingestion_runs SET finished_at = now(), status = 'error' WHERE id = :id"),
                {"id": run_id})
            s.commit()
            raise
        s.commit()
    log(f"✓ SDES Sitadel3 : {stats}")
    return stats


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Ingestion SITADEL via SDES/Dido (Sitadel3, dep 974)")
    ap.add_argument("--refresh", action="store_true",
                    help="delta seulement (max(date) − 3 mois de recouvrement) — cron mensuel")
    ap.add_argument("--no-geocode", action="store_true",
                    help="sauter le fallback géoloc API Carto (réseau)")
    args = ap.parse_args()
    get_settings()  # échoue tôt si l'env DB est absent
    run(refresh=args.refresh, geocode=not args.no_geocode)
