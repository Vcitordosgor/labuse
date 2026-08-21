"""M137-U — INGESTION BPE (INSEE, Base Permanente des Équipements) → spatial_layers kind='amenite_bpe'.

Couche ÉQUIPEMENTS distincte d'OpenStreetMap (kind 'amenite') : DEUX items étiquetés par source,
jamais fusionnés — pas de doublon caché (un même collège apparaît sur sa couche, l'utilisateur voit
la provenance). Le modèle NE CHANGE PAS : `acces_equipements` continue de lire OSM ; « BPE remplace
ou complète OSM ? » se tranchera au prochain réentraînement, pas ici.

  subtype = domaine BPE (A Services · B Commerces · C Enseignement · D Santé/social ·
            E Transports · F Sport/loisir/culture · G Tourisme)

Source : fichier national géolocalisé BPE25 (CSV, Licence Ouverte Etalab 2.0), millésime 2025
(géographie au 01/01/2025). On filtre DEP=974, on géolocalise par LONGITUDE/LATITUDE (WGS84), on
rattache la commune par DEPCOM (INSEE → nom canonique en base). Idempotent : purge kind='amenite_bpe'.
"""
from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

BPE25_URL = "https://www.insee.fr/fr/statistiques/fichier/8217525/BPE25.zip"
SOURCE_NAME = "BPE INSEE"
DOM_LABEL = {
    "A": "Services aux particuliers", "B": "Commerces", "C": "Enseignement",
    "D": "Santé et action sociale", "E": "Transports et déplacements",
    "F": "Sports, loisirs et culture", "G": "Tourisme",
}


def build_bpe(session: Session, log=lambda *_: None) -> dict:
    """Télécharge le fichier national, filtre DEP=974, ingère les équipements géolocalisés."""
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    # DEPCOM (INSEE) → nom de commune canonique (== parcels.commune), via la table contexte 24 lignes.
    insee2nom = {i: n for i, n in session.execute(
        text("SELECT insee, commune FROM commune_conso_enaf")).all()}

    log("téléchargement BPE25 (~136 Mo)…")
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        with httpx.stream("GET", BPE25_URL, timeout=600.0, follow_redirects=True) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes(1 << 20):
                tmp.write(chunk)
        tmp.flush()
        zf = zipfile.ZipFile(tmp.name)
        member = zf.namelist()[0]
        session.execute(text("DELETE FROM spatial_layers WHERE kind = 'amenite_bpe'"))
        counts: dict[str, int] = {}
        n = 0
        with zf.open(member) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                                    delimiter=";")
            for row in reader:
                if row.get("DEP") != "974":
                    continue
                lon, lat = row.get("LONGITUDE"), row.get("LATITUDE")
                if not lon or not lat:
                    continue                                     # équipement non géolocalisé : écarté
                try:
                    lonf, latf = float(lon), float(lat)
                except ValueError:
                    continue
                dom = (row.get("DOM") or "").strip()
                nom = (row.get("CNOMRS") or row.get("NOMRS") or DOM_LABEL.get(dom, "équipement")).strip()
                session.execute(text(
                    """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
                       VALUES ('amenite_bpe', :s, :n, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                               CAST(:a AS jsonb), :sid, :c)"""),
                    {"s": dom or None, "n": nom[:255], "lon": lonf, "lat": latf,
                     "a": json.dumps({"dom": dom, "dom_label": DOM_LABEL.get(dom),
                                      "sdom": row.get("SDOM"), "typequ": row.get("TYPEQU")}),
                     "sid": sid, "c": insee2nom.get(row.get("DEPCOM"))})
                counts[dom] = counts.get(dom, 0) + 1
                n += 1
                if n % 5000 == 0:
                    log(f"  … {n}")
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
    session.flush()
    log(f"BPE 974 : {n} équipements géolocalisés")
    return counts
