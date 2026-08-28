"""ÉTUDE DE ZONE · Z1 — INGESTION SIRENE ÉTABLISSEMENTS ACTIFS GÉOLOCALISÉS (974) → table dédiée
`sirene_etablissements`.

DISTINCTE du SIRENE déjà présent : celui-ci enrichit le PROPRIÉTAIRE par SIREN (Score V,
owner_enrichment). Ici on ingère un ANNUAIRE d'établissements adressés/géocodés, interrogeable par
code NAF dans une zone — pour les « concurrents » de l'Étude de zone. Aucune fusion avec l'existant.

STATUT DE DIFFUSION (obligation légale INSEE, art. A123-96 CGI / opposition des personnes physiques) :
`statutDiffusionEtablissement` = 'O' (diffusible) → tout est stocké ; 'P' (diffusion PARTIELLE, la
personne physique s'est opposée) → on NE stocke NI n'affiche EN CLAIR la dénomination, l'enseigne ni
l'adresse ; seuls les champs diffusibles (SIRET, NAF, commune, position) sont conservés, avec
`diffusible = false`. Un établissement 'P' compte encore comme « un établissement de tel NAF dans la
zone » (le NAF est diffusible), mais son nom n'est jamais servi. Prouvé par test.

Source : fichier géolocalisé SIRENE (INSEE / data.gouv « GéoSIRENE » ou StockEtablissement géocodé,
Licence Ouverte 2.0). CLI rejouable avec --file (le fichier national est volumineux ; on filtre le 974).
Idempotent : purge de la table avant réinsertion.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE_NAME = "SIRENE établissements géolocalisés"

DDL = """
CREATE TABLE IF NOT EXISTS sirene_etablissements (
  siret         varchar(14) PRIMARY KEY,
  siren         varchar(9)  NOT NULL,
  naf           varchar(6),                 -- activité principale (APE/NAF, ex. 1071C)
  denomination  text,                       -- NULL si non diffusible (personne physique opposée)
  enseigne      text,                       -- NULL si non diffusible
  adresse       text,                       -- NULL si non diffusible
  commune       varchar(60),                -- nom canonique (== parcels.commune)
  insee         varchar(5),
  geom          geometry(Point, 4326),
  actif         boolean NOT NULL DEFAULT true,
  diffusible    boolean NOT NULL DEFAULT true,
  data_source_id integer,
  ingested_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_geom ON sirene_etablissements USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_naf  ON sirene_etablissements (naf);
CREATE INDEX IF NOT EXISTS ix_sirene_etab_insee ON sirene_etablissements (insee);
"""


def ensure_tables(session: Session) -> None:
    for stmt in filter(None, (s.strip() for s in DDL.split(";"))):
        session.execute(text(stmt))
    session.flush()


# noms de colonnes du fichier géolocalisé SIRENE (INSEE) — tolérant aux variantes de casse/nommage.
def _col(row: dict, *names: str) -> str | None:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def build_sirene_etablissements(session: Session, *, file: str, log=lambda *_: None) -> dict:
    """Ingère le fichier géolocalisé SIRENE, filtré 974, établissements ACTIFS. Respecte la diffusion.
    `file` = chemin du CSV géolocalisé (téléchargé hors de l'app — le national est volumineux)."""
    path = Path(file)
    if not path.exists():
        raise FileNotFoundError(f"fichier SIRENE géolocalisé introuvable : {path}")
    ensure_tables(session)
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"), {"n": SOURCE_NAME}).scalar()
    insee2nom = {i: n for i, n in session.execute(text("SELECT insee, commune FROM commune_conso_enaf")).all()}

    session.execute(text("DELETE FROM sirene_etablissements"))
    n = n_masques = 0
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=",")
        for row in reader:
            insee = _col(row, "codeCommuneEtablissement", "codecommuneetablissement", "CODE_COMMUNE")
            if not insee or not insee.startswith("974"):
                continue
            etat = _col(row, "etatAdministratifEtablissement", "etatadministratifetablissement") or "A"
            if etat != "A":                                   # seulement les établissements ACTIFS
                continue
            lon = _col(row, "longitude", "LONGITUDE", "geo_adresse_longitude")
            lat = _col(row, "latitude", "LATITUDE", "geo_adresse_latitude")
            if not lon or not lat:
                continue                                       # non géolocalisé : écarté (pas de faux point)
            try:
                lonf, latf = float(lon), float(lat)
            except ValueError:
                continue
            siret = (_col(row, "siret", "SIRET") or "").strip()
            if len(siret) != 14:
                continue
            naf = (_col(row, "activitePrincipaleEtablissement", "activiteprincipaleetablissement", "APET700") or "").replace(".", "").strip()[:6] or None
            diff = (_col(row, "statutDiffusionEtablissement", "statutdiffusionetablissement") or "O").strip().upper()
            diffusible = diff == "O"
            if diffusible:
                denom = (_col(row, "denominationUsuelleEtablissement", "enseigne1Etablissement",
                              "denominationUniteLegale", "denomination") or "").strip()[:255] or None
                enseigne = (_col(row, "enseigne1Etablissement", "enseigne") or "").strip()[:255] or None
                adresse = " ".join(filter(None, [
                    _col(row, "numeroVoieEtablissement"), _col(row, "typeVoieEtablissement"),
                    _col(row, "libelleVoieEtablissement")])).strip()[:255] or _col(row, "adresse")
            else:
                # DIFFUSION PARTIELLE — obligation légale : ni stocké ni affiché en clair.
                denom = enseigne = adresse = None
                n_masques += 1
            session.execute(text(
                """INSERT INTO sirene_etablissements
                   (siret, siren, naf, denomination, enseigne, adresse, commune, insee, geom, actif, diffusible, data_source_id)
                   VALUES (:sir, :srn, :naf, :den, :ens, :adr, :com, :ins,
                           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), true, :dif, :sid)
                   ON CONFLICT (siret) DO NOTHING"""),
                {"sir": siret, "srn": siret[:9], "naf": naf, "den": denom, "ens": enseigne,
                 "adr": adresse, "com": insee2nom.get(insee), "ins": insee,
                 "lon": lonf, "lat": latf, "dif": diffusible, "sid": sid})
            n += 1
            if n % 5000 == 0:
                log(f"  … {n}")
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
    session.flush()
    log(f"SIRENE établissements 974 : {n} actifs géolocalisés ({n_masques} en diffusion partielle, noms masqués)")
    return {"n": n, "n_diffusion_partielle": n_masques}
