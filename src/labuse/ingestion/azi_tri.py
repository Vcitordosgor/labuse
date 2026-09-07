"""SOURCES-1 lot 2 — AZI et TRI par commune (Géorisques GASPAR).

Le FAIT documentaire : quelles communes sont couvertes par un atlas des zones inondables
(AZI) et par un territoire à risque important d'inondation (TRI), avec libellé, risques et
dates — vérifié live 07/09/2026 (`gaspar/azi` et `gaspar/tri`, ex. 97411 : AZI « La
Montagne » 2004, TRI Saint-Denis/Sainte-Marie 2013).

La GÉOMÉTRIE d'aléa inondation n'est PAS ré-ingérée ici : l'ALEA_INONDATION du WFS Carmen
DEAL (75 zones) est un doublon vérifié de `georisque_alea` subtype `inondation` (76 entités
DEAL Lizmap) déjà servies par la couche cascade `risques` — l'AZI/TRI entre comme fait par
commune (fiche commune, Risques), jamais deux couches pour la même emprise.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .run_all import REUNION_COMMUNES

SOURCE_NAME = "AZI / TRI — inondation (Géorisques GASPAR)"
BASE = "https://www.georisques.gouv.fr/api/v1/gaspar"

DDL = """
CREATE TABLE IF NOT EXISTS azi_communes (
    insee        varchar(5) NOT NULL,
    type_doc     varchar(3) NOT NULL,           -- azi | tri
    code_national varchar(24) NOT NULL,
    libelle      varchar(160),
    risques      text,
    date_diffusion varchar(10),
    maj_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (insee, type_doc, code_national)
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def ingest_azi_tri(session: Session, log=print, client: httpx.Client | None = None) -> dict:
    """Réingère AZI + TRI des 24 communes (remplacement complet, idempotent)."""
    session.execute(text("DELETE FROM azi_communes"))
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 60.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    n_azi = n_tri = 0
    communes_azi: set[str] = set()
    communes_tri: set[str] = set()
    try:
        for insee, nom in REUNION_COMMUNES:
            for type_doc in ("azi", "tri"):
                r = c.get(f"{BASE}/{type_doc}",
                          params={"code_insee": insee, "page": 1, "page_size": 100})
                r.raise_for_status()
                for d in (r.json().get("data") or []):
                    code = d.get(f"code_national_{type_doc}")
                    if not code:
                        continue
                    risques = " ; ".join(
                        x.get("libelle_risque_long") or "" for x in
                        (d.get("liste_libelle_risque") or []))
                    session.execute(text(
                        "INSERT INTO azi_communes (insee, type_doc, code_national, libelle, "
                        "risques, date_diffusion, maj_at) VALUES (:i, :t, :c, :l, :r, :d, now()) "
                        "ON CONFLICT (insee, type_doc, code_national) DO UPDATE SET "
                        "libelle = :l, risques = :r, date_diffusion = :d, maj_at = now()"),
                        {"i": insee, "t": type_doc, "c": code,
                         "l": d.get(f"libelle_{type_doc}"), "r": risques,
                         "d": d.get("date_diffusion") or d.get("date_arrete_pcb")})
                    if type_doc == "azi":
                        n_azi += 1
                        communes_azi.add(nom)
                    else:
                        n_tri += 1
                        communes_tri.add(nom)
    finally:
        if own:
            c.close()
    session.flush()
    sans = sorted({nom for _, nom in REUNION_COMMUNES} - communes_azi - communes_tri)
    return {"azi": n_azi, "tri": n_tri, "communes_azi": len(communes_azi),
            "communes_tri": len(communes_tri), "communes_sans_document": sans}


def azi_tri_commune(session: Session, insee: str) -> dict | None:
    """Le fait AZI/TRI d'une commune, sourcé — None si table non peuplée (jamais deviné)."""
    rows = session.execute(text(
        "SELECT type_doc, libelle, risques, date_diffusion FROM azi_communes "
        "WHERE insee = :i ORDER BY type_doc, libelle"), {"i": insee}).mappings().all()
    if not rows:
        peuplee = session.execute(text("SELECT 1 FROM azi_communes LIMIT 1")).first()
        return ({"azi": [], "tri": [],
                 "detail": "aucun AZI ni TRI recensé pour cette commune (GASPAR)"}
                if peuplee else None)
    return {"azi": [dict(r) for r in rows if r["type_doc"] == "azi"],
            "tri": [dict(r) for r in rows if r["type_doc"] == "tri"]}
