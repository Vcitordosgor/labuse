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

# SOURCES-4 lot 2 — BPE25 publie 95 colonnes ; on n'en gardait que 4 (dom/sdom/typequ + nom).
# On capture désormais l'ANNÉE (AN, par enregistrement), l'adresse, le SIRET, la qualité de
# géoloc, et les CARACTÉRISTIQUES SECTORIELLES (capacité d'une école, salles d'un cinéma, bornes
# de recharge, secteur public/privé, spécialité santé…). Les modalités « _Z » (sans objet pour ce
# type d'équipement) et les vides sont écartées → attrs compact, propre au type. Pas de varmod
# fourni par l'INSEE dans le ZIP → les libellés de TYPEQU/SDOM ne sont pas dérivables ici ; le nom
# de l'établissement (NOMRS) reste le libellé humain servi.
_BPE_SECTORIELS = (
    "CANTINE", "INTERNAT", "RPI", "EP", "CL_PGE", "SECT", "SECTEUR",
    "ACCES_AIRE_PRATIQUE", "ACCES_LIBRE", "ACCES_SANITAIRE", "ACCES_VESTIAIRE",
    "CAPACITE_D_ACCUEIL", "PRES_DOUCHE", "PRES_SANITAIRE", "SAISONNIER", "COUVERT",
    "ECLAIRE", "CATEGORIE", "MULTIPLEXE", "STRUCTURE_EXERCICE", "SPECIALITE", "ACCUEIL",
    "ITINERANCE", "MODE_GESTION", "SSTYPHEB", "TYPE", "TYPERESTO", "IMPLANTATION_STATION",
    "GPL", "CAPACITE", "NBEQUIDENT", "NBSALLES", "NBLIEUX", "NB_PDC", "NB_PDC_PA",
    "NB_PDC_ACCELEREE", "NB_PDC_LENTE", "NB_PDC_RAPIDE", "NB_PDC_ULTRARAPIDE", "NB_JOURS_OUVERT",
)


def _bpe_attrs(row: dict) -> dict:
    """Construit les attrs BPE MAXIMUM d'une ligne : dom/sdom/typequ + année + adresse + SIRET +
    qualité géoloc + caractéristiques sectorielles non vides (hors modalité « _Z »)."""
    dom = (row.get("DOM") or "").strip()
    carac = {k.lower(): v.strip() for k in _BPE_SECTORIELS
             if (v := (row.get(k) or "")).strip() not in ("", "_Z")}
    adresse = " ".join(x for x in (
        (row.get("NUMVOIE") or "").strip(), (row.get("TYPVOIE") or "").strip(),
        (row.get("LIBVOIE") or "").strip()) if x) or None
    return {
        "dom": dom, "dom_label": DOM_LABEL.get(dom),
        "sdom": row.get("SDOM"), "typequ": row.get("TYPEQU"),
        "an": (row.get("AN") or "").strip() or None,                 # année du millésime BPE
        "adresse": adresse,
        "code_postal": (row.get("CODPOS") or "").strip() or None,
        "siret": (row.get("SIRET") or "").strip() or None,
        "qualite_xy": (row.get("QUALITE_XY") or "").strip() or None,
        "caracteristiques": carac or None,
    }


def build_bpe(session: Session, log=lambda *_: None, zip_path: str | None = None) -> dict:
    """Télécharge le fichier national (ou lit `zip_path` local s'il est fourni — SOURCES-4, évite un
    re-download), filtre DEP=974, ingère les équipements géolocalisés avec attrs MAXIMUM."""
    sid = session.execute(text("SELECT id FROM data_sources WHERE name = :n"),
                          {"n": SOURCE_NAME}).scalar()
    # DEPCOM (INSEE) → nom de commune canonique (== parcels.commune), via la table contexte 24 lignes.
    insee2nom = {i: n for i, n in session.execute(
        text("SELECT insee, commune FROM commune_conso_enaf")).all()}

    tmp_ctx = open(zip_path, "rb") if zip_path else tempfile.NamedTemporaryFile(suffix=".zip")
    with tmp_ctx as tmp:
        if not zip_path:
            log("téléchargement BPE25 (~136 Mo)…")
            with httpx.stream("GET", BPE25_URL, timeout=600.0, follow_redirects=True) as r:
                r.raise_for_status()
                for chunk in r.iter_bytes(1 << 20):
                    tmp.write(chunk)
            tmp.flush()
        zf = zipfile.ZipFile(tmp.name if not zip_path else zip_path)
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
                     "a": json.dumps(_bpe_attrs(row)),
                     "sid": sid, "c": insee2nom.get(row.get("DEPCOM"))})
                counts[dom] = counts.get(dom, 0) + 1
                n += 1
                if n % 5000 == 0:
                    log(f"  … {n}")
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = :n"), {"n": SOURCE_NAME})
    session.flush()
    log(f"BPE 974 : {n} équipements géolocalisés")
    return counts
