"""RETOURS-13 R4 — LIGNES MOYENNE TENSION (HTA) — EDF Réunion open data.

La recherche du 05/09/2026 (mandat R4, URL par URL — compte-rendu RETOURS-13) établit que le
portail open data d'EDF à La Réunion (opendata-reunion.edf.fr, refondu sous Koumoul/data-fair —
l'ancien portail Opendatasoft répond 404/410) publie TOUJOURS les deux jeux HTA :

· « Lignes haute tension (HTA aérien) — La Réunion »   : 4 211 tronçons, données « mises à jour
  en février 2020 », dernière publication 16/10/2025 ;
· « Lignes haute tension (HTA souterrain) — La Réunion » : 15 269 tronçons, 16/10/2025.

« HTA » dans le vocabulaire EDF = la MOYENNE TENSION de distribution (15-20 kV) — à ne pas
confondre avec la HTB (transport 63/90 kV, couche `ligne_ht` BD TOPO). Licence Ouverte v2.0.
Champs servis : statut (« En exploitation ») + géométrie LineString SEULS — ni tension exacte,
ni nom de départ : EDF a réduit le contenu « afin de renforcer la sécurité publique »
(mention portée par les fiches du portail). Les POSTES SOURCES, eux, ont été VIDÉS
(0 enregistrement au 24/12/2025) : pas de couche postes — l'absence est dite, pas contournée.

kind='ligne_mt', subtype='aerien'|'souterrain', commune=NULL (île entière).
Ingestion idempotente (DELETE kind avant ré-insertion), millésime amont écrit au catalogue.
"""
from __future__ import annotations

import csv
import io
import json
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .layers_ingest import _insert_layer, _source_ids

log = logging.getLogger("labuse")

SRC_EDF_MT = "EDF Réunion — lignes moyenne tension HTA (open data)"

#: data-fair « data-files » du portail Koumoul (résolus depuis les fiches datasets, 05/09/2026).
#: Si EDF refond encore le portail, l'échec est BRUYANT (raise) — jamais une couche vide muette.
URLS_MT = {
    "aerien": ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
               "lihub-72mnuv47c249qzvlhv/data-files/lignes-haute-tension-hta-aerien.csv"),
    "souterrain": ("https://opendata-reunion.edf.fr/data-fair/api/v1/datasets/"
                   "l034et0jh84agf75y9m-0fu6/data-files/2-lignes-haute-tension-hta-souterrain.csv"),
}
#: millésime amont AFFICHÉ (fiche portail : données 02/2020, republiées 16/10/2025).
MILLESIME_MT = "EDF géométrie ~02/2020 · publié 16/10/2025"


def ingest_lignes_mt(session: Session, run_id: int | None = None,
                     fichiers: dict[str, str] | None = None) -> dict:
    """Ingère les deux jeux HTA (aérien + souterrain) → kind='ligne_mt'.

    `fichiers` (tests / rejeu hors-ligne) : {subtype: chemin CSV local} — sinon téléchargement
    live depuis URLS_MT. CSV EDF : colonnes statut;geo_shape;geo_point_2d (geo_shape = GeoJSON)."""
    sids = _source_ids(session)
    sid = sids.get(SRC_EDF_MT)
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'ligne_mt'"))
    bilan: dict = {"aerien": 0, "souterrain": 0}
    for subtype, url in URLS_MT.items():
        if fichiers and subtype in fichiers:
            raw = open(fichiers[subtype], "rb").read()
        else:
            with httpx.Client(follow_redirects=True) as client:
                r = client.get(url, timeout=300)
                r.raise_for_status()
                raw = r.content
        n = 0
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";"):
            shape = row.get("geo_shape")
            if not shape:
                continue
            try:
                geom = json.loads(shape)
            except json.JSONDecodeError:
                continue
            _insert_layer(session, "ligne_mt", subtype,
                          f"Ligne moyenne tension (HTA) — {subtype}", geom, sid, None, run_id,
                          {"statut": row.get("statut"), "millesime": MILLESIME_MT,
                           "precision": ("tracé indicatif publié par EDF — contenu réduit pour "
                                          "raison de sécurité publique ; ne remplace pas une DT-DICT")})
            n += 1
        if n == 0:
            raise RuntimeError(f"ligne_mt/{subtype} : 0 tronçon lu — source EDF changée ou vide "
                               "(échec bruyant, on ne pose pas une couche vide en silence)")
        bilan[subtype] = n
    session.execute(text("UPDATE data_sources SET source_millesime = :m, last_sync_at = now() "
                         "WHERE name = :n"), {"m": MILLESIME_MT[:64], "n": SRC_EDF_MT})
    return bilan
