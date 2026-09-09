"""SOURCES-1 lot 5 — taux de taxe foncière votés (fichier REI, DGFiP, annuel).

Source vérifiée live 07/09/2026 : ZIP `REI-2025-fichier-notice-trace.zip` (data.economie.gouv.fr,
18,5 Mo — REI_2025.csv 112 Mo, 1 043 colonnes, 24 lignes 974). Colonnes RETENUES, identifiées
par la TRACE officielle (TRACE_REI_2025.xlsx, lue) :
  · E12  — taux TFPB appliqué sur le territoire de la commune (mesuré 29,55→68,40 % au 974) ;
  · E12VOTE — taux TFPB VOTÉ par la commune (identique à E12 sur les 24 en 2025) ;
  · E32  — taux TFPB intercommunal applicable (0→3 %) ;
  · F22  — taux TEOM net « taux plein » (15,80→16,00 % mesurés).
⚠ La taxe d'aménagement n'est PAS dans le REI (sa source reste CIRCUIT-3 lot 6.2).
Impositions PRIMITIVES (fiche 13) — dit dans le millésime. Purge + upsert (idempotent).
"""
from __future__ import annotations

import csv
import io
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_NAME = "Taux de taxe foncière — fichier REI (DGFiP)"
URL_ZIP = ("https://data.economie.gouv.fr/api/v2/catalog/datasets/"
           "impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-dir/"
           "attachments/rei_2025_fichier_notice_tracezip")
MILLESIME = "REI 2025 (impositions primitives)"

DDL = """
CREATE TABLE IF NOT EXISTS commune_rei (
    insee            varchar(5) PRIMARY KEY,
    commune          varchar(64) NOT NULL,
    tfpb_commune_pct numeric(6,2),
    tfpb_vote_pct    numeric(6,2),
    tfpb_epci_pct    numeric(6,2),
    teom_pct         numeric(6,2),
    millesime        varchar(64) NOT NULL,
    maj_at           timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def _num(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def ingest_rei(session: Session, *, url: str = URL_ZIP, zip_bytes: bytes | None = None,
               client: httpx.Client | None = None, log=print) -> dict:
    """Télécharge le ZIP REI (ou lit `zip_bytes`), extrait les 24 lignes 974, upsert.
    Rend {"n", "manquantes", "hors_bornes"}."""
    if zip_bytes is None:
        own = client is None
        c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 600.0),
                                   headers={"User-Agent": constants.USER_AGENT},
                                   follow_redirects=True)
        try:
            r = c.get(url)
            r.raise_for_status()
            zip_bytes = r.content
        finally:
            if own:
                c.close()
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    nom_csv = next(n for n in zf.namelist() if n.upper().startswith("REI") and n.endswith(".csv"))
    n = 0
    vus: set[str] = set()
    hors_bornes: list[str] = []
    with zf.open(nom_csv) as fh:
        rdr = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";")
        for row in rdr:
            if row.get("DEP") != "974" and row.get(rdr.fieldnames[0]) != "974":
                continue
            insee = (row.get("IDCOM") or "").strip()
            if not insee.startswith("974"):
                continue
            taux = {k: _num(row.get(k)) for k in ("E12", "E12VOTE", "E32", "F22")}
            # bornes de plausibilité : un taux est un % ∈ [0 ; 100] — hors bornes = écarté + listé
            for k, v in taux.items():
                if v is not None and not (0.0 <= v <= 100.0):
                    hors_bornes.append(f"{insee}:{k}={v}")
                    taux[k] = None
            session.execute(text(
                "INSERT INTO commune_rei (insee, commune, tfpb_commune_pct, tfpb_vote_pct, "
                " tfpb_epci_pct, teom_pct, millesime, maj_at) "
                "VALUES (:i, :c, :t1, :t2, :t3, :t4, :m, now()) "
                "ON CONFLICT (insee) DO UPDATE SET commune = :c, tfpb_commune_pct = :t1, "
                " tfpb_vote_pct = :t2, tfpb_epci_pct = :t3, teom_pct = :t4, millesime = :m, "
                " maj_at = now()"),
                {"i": insee, "c": (row.get("LIBCOM") or "").strip().title(),
                 "t1": taux["E12"], "t2": taux["E12VOTE"], "t3": taux["E32"],
                 "t4": taux["F22"], "m": MILLESIME})
            vus.add(insee)
            n += 1
    session.flush()
    from .run_all import REUNION_COMMUNES
    manquantes = sorted(nom for insee, nom in REUNION_COMMUNES if insee not in vus)
    if manquantes:
        log(f"  ⚠ REI : communes absentes : {manquantes}")
    return {"n": n, "manquantes": manquantes, "hors_bornes": hors_bornes}


def rei_commune(session: Session, insee: str) -> dict | None:
    """Les taux fonciers d'une commune, sourcés + datés — None si non ingérés."""
    row = session.execute(text(
        "SELECT insee, commune, tfpb_commune_pct, tfpb_epci_pct, teom_pct, millesime, maj_at "
        "FROM commune_rei WHERE insee = :i"), {"i": insee}).mappings().first()
    if row is None:
        return None
    d = dict(row)
    for k in ("tfpb_commune_pct", "tfpb_epci_pct", "teom_pct"):
        d[k] = float(d[k]) if d[k] is not None else None
    d["maj_at"] = d["maj_at"].isoformat() if d.get("maj_at") else None
    return d
