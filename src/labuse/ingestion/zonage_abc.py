"""SOURCES-1 lot 1 — zonage A/B/C des communes (arrêté national, DHUP).

Source vérifiée live 06/09/2026 : jeu data.gouv « Liste des communes selon le zonage ABC »
(Ministère de la Transition écologique / DHUP), CSV national `CODGEO;DEP;LIBGEO;Zonage…`,
en vigueur depuis l'arrêté du 26 juin 2026 (modifiant l'arrêté du 1er août 2014, D. 304-1 CCH).
Mesuré au téléchargement : 24 communes 974, zones A (Les Avirons, L'Étang-Salé, Saint-Leu,
Saint-Paul) et B1 (les 20 autres).

Table `commune_zonage_abc` (insee PK) — classe par commune, pas de couche carte, pas de
cascade (mandat SOURCES-1) : le zonage ABC dit le régime d'aides/défiscalisation, pas la
constructibilité. Passe-plat : la zone est SERVIE telle que publiée, jamais recalculée.
"""
from __future__ import annotations

import csv
import io

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .run_all import REUNION_COMMUNES

SOURCE_NAME = "Zonage ABC des communes (DHUP)"
URL_CSV = ("https://static.data.gouv.fr/resources/liste-des-communes-selon-le-zonage-abc/"
           "20260703-091314/liste-ensemble-des-communes-zonage-abc-en-vigueur-26-juin-2026.csv")
MILLESIME = "arrêté du 23/06/2026 — en vigueur 26/06/2026"
ZONES_CONNUES = {"Abis", "A", "B1", "B2", "C"}

DDL = """
CREATE TABLE IF NOT EXISTS commune_zonage_abc (
    insee      varchar(5) PRIMARY KEY,
    commune    varchar(64) NOT NULL,
    zone       varchar(8)  NOT NULL,
    millesime  varchar(96) NOT NULL,
    maj_at     timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def ingest_zonage_abc(session: Session, *, url: str = URL_CSV,
                      client: httpx.Client | None = None, log=print) -> dict:
    """Télécharge le CSV national, garde le 974, upsert par insee. Rend
    {"n": .., "zones": {...}, "manquantes": [...], "hors_domaine": [...]}."""
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        r = c.get(url)
        r.raise_for_status()
        contenu = r.content.decode("utf-8-sig", errors="replace")
    finally:
        if own:
            c.close()
    lignes = list(csv.reader(io.StringIO(contenu), delimiter=";"))
    if not lignes or len(lignes[0]) < 4:
        raise ValueError("CSV zonage ABC illisible (moins de 4 colonnes)")
    n = 0
    zones: dict[str, int] = {}
    hors_domaine: list[str] = []
    vus: set[str] = set()
    for row in lignes[1:]:
        if len(row) < 4 or row[1] != "974":
            continue
        insee, libgeo, zone = row[0].strip(), row[2].strip(), row[3].strip()
        if zone not in ZONES_CONNUES:
            hors_domaine.append(f"{insee}={zone}")
            continue
        session.execute(text(
            "INSERT INTO commune_zonage_abc (insee, commune, zone, millesime, maj_at) "
            "VALUES (:i, :c, :z, :m, now()) "
            "ON CONFLICT (insee) DO UPDATE SET commune = :c, zone = :z, millesime = :m, "
            "maj_at = now()"),
            {"i": insee, "c": libgeo, "z": zone, "m": MILLESIME})
        vus.add(insee)
        zones[zone] = zones.get(zone, 0) + 1
        n += 1
    manquantes = sorted(nom for insee, nom in REUNION_COMMUNES if insee not in vus)
    if manquantes:
        log(f"  ⚠ zonage ABC : communes 974 absentes du CSV national : {manquantes}")
    session.flush()
    return {"n": n, "zones": zones, "manquantes": manquantes, "hors_domaine": hors_domaine}


def zonage_commune(session: Session, insee: str) -> dict | None:
    """La classe ABC d'une commune, sourcée + datée — None si non ingérée (jamais devinée)."""
    row = session.execute(text(
        "SELECT insee, commune, zone, millesime FROM commune_zonage_abc WHERE insee = :i"),
        {"i": insee}).mappings().first()
    return dict(row) if row else None
