"""Ingestion des COUCHES STRUCTURANTES réelles → spatial_layers  [✓ live].

Remplace les couches synthétiques de la démo par les vrais flux confirmés au
SPIKE. Chaque fonction range son résultat dans le `kind`/`subtype` exact que la
cascade phase 1 consomme (cf. cascade/layers/phase1.py + config/cascade_rules.yaml).

Discipline : géométries stockées en 4326 (ST_GeomFromGeoJSON + ST_MakeValid) ;
toute mesure se fait en 2975 côté cascade. Résultats partiels (brief §4) : une
source en échec n'empêche pas les autres — chaque couche est isolée.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import re
import tempfile
import time
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from ..connectors.wfs import WfsConnector
from . import agorah_plu

APICARTO = "https://apicarto.ign.fr/api"
ODS_BASE = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"
ALTI_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
# Indicateur national d'érosion côtière (Cerema/GéoLittoral), emprise Réunion, EPSG:2975.
EROSION_URL = ("https://geolittoral.din.developpement-durable.gouv.fr/telechargement/"
               "couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip")

# kind LA BUSE -> nom canonique de data_sources (pour data_source_id).
KIND_SOURCE = {
    "water": "BD TOPO IGN",
    "voirie": "BD TOPO IGN",
    "batiment": "BD TOPO IGN",
    "ravine": "BD TOPO IGN",
    "plu_gpu_zone": "Urbanisme PLU/GPU (API Carto)",
    "plu_gpu_prescription": "Urbanisme PLU/GPU (API Carto)",
    "parc_national": "Parc National de La Réunion (INPN)",
    "abf": "ABF / Monuments historiques",
    "potentiel_foncier": "data.regionreunion.com — Potentiel foncier",
    "ocs_ge": "OCS GE (IGN)",
    "pente": "RGE ALTI (altimétrie)",
    "trait_de_cote": "DEAL Réunion — trait de côte",
    "osm_faux_positif": "OpenStreetMap / Overpass",
    "ppr": "DEAL Réunion — PPR / aléas",            # zonage rouge/bleu (fallback PM1 API Carto si commune sans PPR approuvé)
    "georisque_alea": "DEAL Réunion — PPR / aléas",
    "sar": "data.regionreunion.com — SAR (vocation via potentiel foncier)",
}

# Risques PPR codés dans le nom de fichier de la servitude (PM1_PPR_<code>_<COMMUNE>_...).
PPR_RISK_LABELS = {
    "i_mvt": "inondation + mouvement de terrain", "mvt": "mouvement de terrain",
    "i": "inondation", "l": "littoral / aléa côtier", "i_mvt_alea_cotier": "inondation, mouvement de terrain, littoral",
    "t": "feux de forêt", "s": "séisme",
}

# Faux positifs géométriques OSM : tags → subtype consommé par la cascade
# (config/cascade_rules.yaml : hard cemetery/school ; flag pitch/parking).
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_OSM_FP_QUERY = """[out:json][timeout:90];
(
  way["landuse"="cemetery"]({s},{w},{n},{e});
  relation["landuse"="cemetery"]({s},{w},{n},{e});
  way["amenity"="grave_yard"]({s},{w},{n},{e});
  way["amenity"="school"]({s},{w},{n},{e});
  relation["amenity"="school"]({s},{w},{n},{e});
  way["leisure"="pitch"]({s},{w},{n},{e});
  way["amenity"="parking"]({s},{w},{n},{e});
  relation["amenity"="parking"]({s},{w},{n},{e});
);
out geom;"""


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=max(get_settings().http_timeout_s, 60.0),
        headers={"User-Agent": constants.USER_AGENT},
        follow_redirects=True,
    )


def _bbox_polygon(bbox: tuple[float, float, float, float]) -> dict:
    minlon, minlat, maxlon, maxlat = bbox
    return {"type": "Polygon", "coordinates": [[
        [minlon, minlat], [maxlon, minlat], [maxlon, maxlat], [minlon, maxlat], [minlon, minlat],
    ]]}


def _source_ids(session: Session) -> dict[str, int]:
    return {n: i for (n, i) in session.execute(text("SELECT name, id FROM data_sources")).all()}


def _insert_layer(session: Session, kind: str, subtype: str | None, name: str | None,
                  geometry: dict, source_id: int | None, commune: str | None,
                  run_id: int | None, attrs: dict | None = None) -> None:
    """Insère une entité dans spatial_layers (4326, géométrie validée)."""
    session.execute(
        text(
            """
            INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune, ingestion_run_id)
            VALUES (:k, :s, :n,
                    ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                    CAST(:a AS jsonb), :sid, :c, :run)
            """
        ),
        {"k": kind, "s": subtype, "n": name, "g": json.dumps(geometry),
         "a": json.dumps(attrs or {}), "sid": source_id, "c": commune, "run": run_id},
    )


def _ods_records(client: httpx.Client, dataset: str, *, where: str | None = None,
                 select: str | None = None, page: int = 100, cap: int = 10000) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while offset < cap:
        params: dict = {"limit": page, "offset": offset}
        if where:
            params["where"] = where
        if select:
            params["select"] = select
        r = client.get(f"{ODS_BASE}/{dataset}/records", params=params)
        r.raise_for_status()
        res = r.json().get("results", []) or []
        out.extend(res)
        if len(res) < page:
            break
        offset += page
    return out


# ───────────────────────── couches ─────────────────────────

def ingest_gpu_zones(session, insee, bbox, commune, run_id, sids) -> int:
    """PLU/GPU zone-urba (API Carto) → kind='plu_gpu_zone', subtype=typezone.

    Repli AGORAH (Open Data Réunion) si le GPU ne sert AUCUNE zone PROPRE `DU_<insee>`
    ET la commune est allowlistée (cf. agorah_plu.should_use_agorah_fallback). Sinon
    comportement inchangé. `attrs.source` distingue API Carto GPU vs AGORAH.
    """
    part = agorah_plu.agorah_partition(insee)
    with _client() as c:
        r = c.get(f"{APICARTO}/gpu/zone-urba", params={"geom": json.dumps(_bbox_polygon(bbox))})
        r.raise_for_status()
        feats = r.json().get("features", []) or []
    n = propre = 0
    for f in feats:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        if p.get("partition") == part:
            propre += 1
        _insert_layer(session, "plu_gpu_zone", (p.get("typezone") or "").strip() or None,
                      p.get("libelong") or p.get("libelle"), f["geometry"],
                      sids.get(KIND_SOURCE["plu_gpu_zone"]), commune, run_id,
                      {"source": "API_CARTO_GPU", "libelle": p.get("libelle"),
                       "partition": p.get("partition"), "idurba": p.get("idurba")})
        n += 1
    logging.getLogger("labuse").info(
        "ingest_gpu_zones[%s] : %d zones GPU (%d propres %s)", commune, n, propre, part)
    if agorah_plu.should_use_agorah_fallback(insee, propre):
        logging.getLogger("labuse").warning(
            "ingest_gpu_zones[%s] : 0 zone propre %s au GPU + commune allowlistée → REPLI AGORAH", commune, part)
        n += agorah_plu.ingest_agorah_plu_zones(
            session, insee, commune, run_id, sids.get(KIND_SOURCE["plu_gpu_zone"]))
    return n


# Endpoints prescriptions GPU : (geom_kind interne, chemin API).
_PRESCRIPTION_ENDPOINTS = (("surf", "prescription-surf"), ("lin", "prescription-lin"), ("pct", "prescription-pct"))


def ingest_gpu_prescriptions(session, bbox, commune, run_id, sids) -> int:
    """Prescriptions du PLU (API Carto GPU) → kind='plu_gpu_prescription', subtype=typepsc.

    Surfaciques + linéaires + ponctuelles : emplacements réservés (ER), secteurs de mixité
    sociale, espaces boisés classés (EBC), zonage des eaux pluviales… Ce sont de VRAIES
    contraintes opposables, jusqu'ici non ingérées (la cascade ne lisait que le zonage).
    Le GPU fournit le LIBELLÉ lisible : on le stocke tel quel (jamais inventé). La géométrie
    surf est un polygone (couverture mesurable) ; lin/pct sont ligne/point (présence seule).
    Source/url/millésime (idurba) tracés. Idempotent à l'appelant (purge avant rechargement)."""
    poly = json.dumps(_bbox_polygon(bbox))
    src = sids.get(KIND_SOURCE["plu_gpu_prescription"])
    n = 0
    with _client() as c:
        for geom_kind, endpoint in _PRESCRIPTION_ENDPOINTS:
            try:
                r = c.get(f"{APICARTO}/gpu/{endpoint}", params={"geom": poly})
                r.raise_for_status()
                feats = r.json().get("features", []) or []
            except Exception:
                continue  # un endpoint vide/en échec n'empêche pas les autres (résultats partiels)
            for f in feats:
                if not f.get("geometry"):
                    continue
                p = f.get("properties") or {}
                typepsc = (p.get("typepsc") or "").strip() or None
                libelle = (p.get("libelle") or p.get("txt") or "prescription PLU").strip()
                _insert_layer(
                    session, "plu_gpu_prescription", typepsc, libelle[:255], f["geometry"],
                    src, commune, run_id,
                    {"typepsc": typepsc, "stypepsc": p.get("stypepsc"), "libelle": libelle,
                     "txt": p.get("txt") or None, "geom_kind": geom_kind, "idurba": p.get("idurba"),
                     "partition": p.get("partition"),
                     "source": f"API Carto GPU — {endpoint}",
                     "url_source": f"{APICARTO}/gpu/{endpoint}", "millesime": p.get("idurba")})
                n += 1
    return n


def _norm_commune(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return re.sub(r"[\s'-]+", "_", s).upper().strip("_")


def _ppr_risque(fichier: str) -> tuple[str, str]:
    """'PM1_PPR_i_mvt_SAINT_PAUL_2016..._act.pdf' → ('i_mvt', 'inondation + mouvement de terrain').

    Les codes de risque (minuscules) suivent 'PPR' ; le nom de commune (majuscules) suit."""
    codes, started = [], False
    for tok in fichier.split("_"):
        if tok.upper() in ("PM1", "PPR"):
            started = True
            continue
        if started and tok and tok.islower():
            codes.append(tok)
        elif started:
            break
    code = "_".join(codes) or "ppr"
    return code, PPR_RISK_LABELS.get(code, "risque naturel (PPR)")


def ingest_ppr_sup(session, bbox, commune, run_id, sids) -> int:
    """PPR RÉGLEMENTAIRE (risques naturels) via API Carto GPU — servitudes d'utilité publique PM1.

    Le PPR est exposé comme SUP PM1 : l'assiette est le PÉRIMÈTRE réglementaire (MultiPolygon).
    Elle ne porte PAS le zonage interne rouge/bleue → on stocke le périmètre comme contrainte à
    PRESCRIPTIONS (jamais une exclusion automatique : on ne sait pas si la parcelle est en rouge).
    Le type de risque est lu dans le nom de la servitude. Réglementaire, daté, source tracée.
    """
    want = _norm_commune(commune)
    with _client() as c:
        r = c.get(f"{APICARTO}/gpu/assiette-sup-s", params={"geom": json.dumps(_bbox_polygon(bbox))})
        r.raise_for_status()
        feats = r.json().get("features", []) or []
    n = 0
    for f in feats:
        p = f.get("properties") or {}
        fichier = p.get("fichier") or ""
        if not f.get("geometry") or (p.get("suptype") or "").lower() != "pm1" or "PPR" not in fichier.upper():
            continue  # PM2/PM3 = établissements dangereux (≠ risque naturel) → écartés
        if want and want not in _norm_commune(fichier):
            continue  # la bbox renvoie aussi les PPR des communes voisines → on filtre
        code, libelle = _ppr_risque(fichier)
        _insert_layer(session, "ppr", code, f"PPR {libelle}", f["geometry"],
                      sids.get(KIND_SOURCE["ppr"]), commune, run_id,
                      {"risque": libelle, "code_risque": code, "suptype": "PM1",
                       "statut": "reglementaire", "fichier": fichier, "idass": p.get("idass"),
                       "nomreg": p.get("nomreg"), "urlreg": p.get("urlreg") or p.get("href")})
        n += 1
    return n


# Aléas DEAL : degré → (niveau cascade faible/moyen/fort, résiduel). Codes RÉELS validés (spike 2026-06).
_ALEA_NIVEAU = {
    "FAIBLE": ("faible", False), "MOYEN": ("moyen", False), "FORT": ("fort", False),
    "RESIDUEL_MOYEN": ("moyen", True), "RESIDUEL_FORT": ("fort", True),
    "RESIDUEL_FORT_AGGRAVE": ("fort", True),
}


def _normalise_alea(degre: str | None) -> tuple[str, bool]:
    """`degre` DEAL → (niveau ∈ {faible,moyen,fort} pour alea_severity_map ; résiduel:bool).
    « résiduel » = derrière une protection (digue) → niveau de base CONSERVÉ + flag (prudence)."""
    d = (degre or "").strip().upper()
    if d in _ALEA_NIVEAU:
        return _ALEA_NIVEAU[d]
    residuel = d.startswith("RESIDUEL")
    niveau = "fort" if "FORT" in d else "moyen" if "MOYEN" in d else "faible" if "FAIBLE" in d else "moyen"
    return niveau, residuel


def _prop(props: dict, name: str):
    """Lecture INSENSIBLE À LA CASSE d'une propriété GeoJSON. La casse des champs varie selon
    la couche WFS DEAL : PPR_APPROUVE en MAJUSCULES (DEGRE…), ALEA_* en casse mixte (Degre…).
    Verrouillé par test (test_deal_risques)."""
    if name in props:
        return props[name]
    low = name.lower()
    return next((v for k, v in props.items() if k.lower() == low), None)


def ingest_ppr_zone(session, bbox, commune, run_id, sids, insee) -> int:
    """PPR ZONÉ RÉGLEMENTAIRE (rouge/bleu) via WFS DEAL Réunion (Lizmap) → kind='ppr'.

    subtype = DEGRE : 'INTERDICTION' (rouge, inconstructible — cf. ppr_red_subtypes) /
    'PRESCRIPTION' (bleu, constructible sous conditions). Filtré CODE_INSEE.
    FALLBACK : si 0 zone DEAL pour la commune (PPR non approuvé/dématérialisé), on retombe
    sur le PÉRIMÈTRE PM1 (API Carto GPU, ingest_ppr_sup). Une seule fonction alimente
    kind='ppr', jamais les deux (DELETE-avant-ingestion garantit l'absence de doublon)."""
    wfs = WfsConnector("deal_reunion")
    fc = wfs.fetch_layer("deal_reunion", "PPR_APPROUVE", exp_filter=f"CODE_INSEE = '{insee}'")
    n = 0
    for f in fc.get("features", []) or []:
        p = f.get("properties") or {}
        degre = (_prop(p, "degre") or "").strip()
        if not f.get("geometry") or not degre:
            continue
        code_degre, risque = _prop(p, "code_degre"), _prop(p, "risque")
        _insert_layer(session, "ppr", degre, f"PPR {risque} — {code_degre}", f["geometry"],
                      sids.get(KIND_SOURCE["ppr"]), commune, run_id,
                      {"code_degre": code_degre, "risque": risque, "document": _prop(p, "document"),
                       "code_insee": _prop(p, "code_insee"), "approbation": _prop(p, "approbatio"),
                       "statut": "zonage_reglementaire", "source": "DEAL Réunion — Lizmap"})
        n += 1
    if n == 0:
        return ingest_ppr_sup(session, bbox, commune, run_id, sids)   # repli périmètre PM1
    return n


_ALEA_LAYERS = (("ALEA_INONDATION", "inondation"), ("ALEA_MOUVEMENT_TERRAIN", "mouvement_terrain"))


def ingest_georisque_alea(session, bbox, commune, run_id, sids, insee) -> int:
    """Aléas zonés (inondation, mouvement de terrain) via WFS DEAL Réunion → kind='georisque_alea'.

    subtype = type d'aléa ; attrs.niveau ∈ {faible,moyen,fort} (consommé par alea_severity_map),
    + flag `residuel` (zones derrière protection). Filtré code_insee."""
    wfs = WfsConnector("deal_reunion")
    n = 0
    for typename, subtype in _ALEA_LAYERS:
        fc = wfs.fetch_layer("deal_reunion", typename, exp_filter=f"code_insee = '{insee}'")
        for f in fc.get("features", []) or []:
            p = f.get("properties") or {}
            degre = (_prop(p, "degre") or "").strip()
            if not f.get("geometry") or not degre:
                continue
            niveau, residuel = _normalise_alea(degre)
            _insert_layer(session, "georisque_alea", subtype,
                          f"Aléa {subtype.replace('_', ' ')} — {degre.lower()}", f["geometry"],
                          sids.get(KIND_SOURCE["georisque_alea"]), commune, run_id,
                          {"niveau": niveau, "degre": degre, "code_degre": _prop(p, "code_degre"),
                           "residuel": residuel, "risque": _prop(p, "risque") or _prop(p, "theme"),
                           "code_insee": _prop(p, "code_insee"), "source": "DEAL Réunion — Lizmap"})
            n += 1
    return n


def ingest_parc_national(session, commune, run_id, sids) -> int:
    """Parc National (Région ODS pnrun_2021) → subtype 'coeur' | 'adhesion'."""
    with _client() as c:
        recs = _ods_records(c, "pnrun_2021", select="type,code_type,geo_shape", page=50)
    n = 0
    for rec in recs:
        shape = rec.get("geo_shape") or {}
        geom = shape.get("geometry") if shape.get("type") == "Feature" else shape
        if not geom:
            continue
        libelle = (rec.get("type") or "")
        subtype = "coeur" if "coeur" in libelle.lower() or "cœur" in libelle.lower() else "adhesion"
        _insert_layer(session, "parc_national", subtype, libelle, geom,
                      sids.get(KIND_SOURCE["parc_national"]), commune, run_id,
                      {"type": libelle, "code_type": rec.get("code_type")})
        n += 1
    return n


def ingest_potentiel_foncier(session, insee, commune, run_id, sids) -> int:
    """Potentiel foncier Région (grain parcelle) → kind='potentiel_foncier' (bonus §1)."""
    with _client() as c:
        recs = _ods_records(c, "potentiel-foncier", where=f'insee="{insee}"',
                            select="section,parcelle,espacesar,zpu,geo_shape", page=100)
    n = 0
    for rec in recs:
        shape = rec.get("geo_shape") or {}
        geom = shape.get("geometry") if shape.get("type") == "Feature" else shape
        if not geom:
            continue
        _insert_layer(session, "potentiel_foncier", "ilot", "Îlot potentiel foncier Région", geom,
                      sids.get(KIND_SOURCE["potentiel_foncier"]), commune, run_id,
                      {"espacesar": rec.get("espacesar"), "zpu": rec.get("zpu"),
                       "section": rec.get("section"), "parcelle": rec.get("parcelle")})
        n += 1
    return n


def _sar_vocation(espacesar: str | None) -> tuple[str, str, str]:
    """Mappe la vocation SAR (champ `espacesar` du potentiel foncier Région) → (subtype, libellé, niveau).

    PRUDENCE (proxy de vocation, grain îlot, souvent multi-classe) : aucune vocation ne
    déclenche d'EXCLUSION automatique — les contraintes deviennent des FLAGS « à vérifier ».
    Le SAR contribue au verdict ; il ne prouve ni la constructibilité ni l'interdiction."""
    s = (espacesar or "").lower()
    urb = any(k in s for k in ("urbanis", "densifier", "urbain"))
    if "protection forte" in s or "espace naturel" in s:
        return ("vocation_mixte", "vocation mixte SAR (naturel + urbain) — à vérifier", "fort") if urb \
            else ("vocation_naturelle", "espace naturel SAR (protection forte) — à vérifier", "fort")
    if "coupure" in s:
        return ("vocation_coupure", "coupure d'urbanisation SAR — à vérifier (bloquant potentiel)", "fort")
    if "continuit" in s:
        return ("vocation_continuite", "continuité écologique SAR (trame verte/bleue) — à vérifier", "fort")
    if "agricole" in s:
        return ("vocation_mixte", "vocation mixte SAR (agricole + urbain) — à vérifier", "fort") if urb \
            else ("vocation_agricole", "espace agricole SAR (risque préemption SAFER) — à vérifier", "fort")
    if "urbanisation prioritaire" in s:
        return ("vocation_urbaine", "espace d'urbanisation prioritaire SAR — compatible", "faible")
    if urb:
        return ("vocation_urbaine", "espace urbanisé à densifier SAR — compatible", "faible")
    if "rur" in s:
        return ("vocation_rurale", "territoires ruraux habités SAR", "faible")
    return ("vocation_autre", espacesar or "vocation SAR non précisée", "faible")


def ingest_sar(session, insee, commune, run_id, sids) -> int:
    """SAR (Schéma d'Aménagement Régional) — vocation via le potentiel foncier Région (ODS).

    Faute de zonage SAR réglementaire en flux libre (DEAL/PEIGEO injoignables, rien sur la
    Géoplateforme pour 974), on utilise la classification officielle `espacesar` de la Région
    (géolocalisée, grain îlot). C'est une COUCHE DE COHÉRENCE TERRITORIALE (vocation/orientation),
    PAS le zonage opposable ni un substitut au PLU/PPR. Couverture PARTIELLE (îlots à potentiel).
    """
    with _client() as c:
        recs = _ods_records(c, "potentiel-foncier", where=f'insee="{insee}"',
                            select="espacesar,geo_shape", page=100)
    n = 0
    for rec in recs:
        shape = rec.get("geo_shape") or {}
        geom = shape.get("geometry") if shape.get("type") == "Feature" else shape
        if not geom or not rec.get("espacesar"):
            continue
        subtype, libelle, niveau = _sar_vocation(rec.get("espacesar"))
        _insert_layer(session, "sar", subtype, f"SAR — {libelle}", geom,
                      sids.get(KIND_SOURCE["sar"]), commune, run_id,
                      {"libelle": libelle, "vocation": rec.get("espacesar"), "niveau": niveau,
                       "statut": "strategique (orientation SAR — Région)",
                       "source": "data.regionreunion.com / potentiel-foncier",
                       "couverture": "partielle (îlots à potentiel foncier)"})
        n += 1
    return n


def ingest_abf(session, bbox, commune, run_id, sids) -> int:
    """ABF — SUP « abords MH » (API Carto GPU assiette-sup-s, filtre suptype AC1)."""
    with _client() as c:
        r = c.get(f"{APICARTO}/gpu/assiette-sup-s", params={"geom": json.dumps(_bbox_polygon(bbox))})
        r.raise_for_status()
        feats = r.json().get("features", []) or []
    n = 0
    for f in feats:
        p = f.get("properties") or {}
        suptype = (p.get("suptype") or "").upper()
        if suptype != "AC1" or not f.get("geometry"):   # AC1 = abords de monuments historiques (ABF)
            continue
        _insert_layer(session, "abf", suptype, p.get("nomass") or "Servitude AC1", f["geometry"],
                      sids.get(KIND_SOURCE["abf"]), commune, run_id,
                      {"suptype": suptype, "nomass": p.get("nomass")})
        n += 1
    return n


def ingest_bdtopo(session, bbox, commune, run_id, sids, kind: str, typename: str,
                  page_size: int = 5000, max_total: int = 60000) -> int:
    """BD TOPO via WFS Géoplateforme (bbox lon,lat) → kind (water | voirie). **PAGINÉ**.

    Le serveur Géoplateforme PLAFONNE une réponse GetFeature à 5 000 entités : sans pagination, la
    voirie/water des communes denses étaient TRONQUÉES à 5 000 (proxy d'accès faussé → faux « accès
    non identifié », cf. docs/VOIRIE_CAP_5000_AUDIT.md). Augmenter `count`/`max_features` NE SUFFIT PAS
    (le serveur ignore au-delà de son plafond) — il faut PAGINER : count/startIndex + tri stable
    `cleabs` (comme le bâti), jusqu'à une page incomplète. Garde-fou anti-boucle : `max_total`.
    """
    wfs = WfsConnector("geoplateforme_wfs")
    n, start, pages = 0, 0, 0
    while True:
        fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=bbox,
                             max_features=page_size, start_index=start, sort_by="cleabs")
        feats = fc.get("features", []) or []
        for f in feats:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            # voirie : on garde largeur de chaussée + importance + nb voies (même flux WFS, jusque-là
            # jetés) → alimentent la hauteur PROSPECT (Ud/Uu, A3). water : aucun attribut utile.
            attrs = ({"largeur": p.get("largeur_de_chaussee"), "importance": p.get("importance"),
                      "nb_voies": p.get("nombre_de_voies")} if kind == "voirie" else None)
            _insert_layer(session, kind, p.get("nature"), p.get("nature") or typename.split(":")[-1],
                          f["geometry"], sids.get(KIND_SOURCE[kind]), commune, run_id, attrs)
            n += 1
        pages += 1
        if len(feats) < page_size:        # page incomplète / vide → c'est la dernière
            break
        start += page_size
        if start >= max_total:            # garde-fou anti-boucle (serveur qui renverrait toujours plein)
            logging.getLogger("labuse").warning(
                "ingest_bdtopo[%s] : garde-fou max_total=%d atteint (commune %s) — voirie tronquée ?",
                kind, max_total, commune)
            break
    logging.getLogger("labuse").info(
        "ingest_bdtopo[%s] : %d objet(s) en %d page(s) (commune %s)", kind, n, pages, commune)
    return n


def ingest_ravines(session, bbox, commune, run_id, sids, page_size: int = 1000) -> int:
    """Ravines (BD TOPO `troncon_hydrographique`, `nature='Ravine'`) — Lot C1.

    Disponibilité vérifiée (rapport C1) : 98 tronçons « Ravine » sur Saint-Paul, géométries
    LineString. À La Réunion, les ravines sont des thalwegs (souvent à sec) au régime de crue
    brutal : la PROXIMITÉ est une contrainte de constructibilité (recul, risque). On stocke la
    ligne ; la cascade calcule la distance (buffer paramétrable, jamais figé à l'ingestion)."""
    wfs = WfsConnector("geoplateforme_wfs")
    n, start = 0, 0
    while True:
        fc = wfs.fetch_layer("geoplateforme_wfs", "BDTOPO_V3:troncon_hydrographique", bbox=bbox,
                             max_features=page_size, start_index=start, sort_by="cleabs")
        feats = fc.get("features", []) or []
        for f in feats:
            p = f.get("properties") or {}
            if not f.get("geometry") or (p.get("nature") or "") != "Ravine":
                continue
            topo = p.get("cpx_toponyme_de_cours_d_eau") or p.get("cpx_toponyme_d_entite_de_transition")
            _insert_layer(session, "ravine", "ravine", topo or "Ravine (BD TOPO)",
                          f["geometry"], sids.get(KIND_SOURCE["ravine"]), commune, run_id,
                          {"nature": "Ravine", "toponyme": topo,
                           "code_hydro": p.get("code_hydrographique"),
                           "source": "BD TOPO IGN (Géoplateforme WFS) — troncon_hydrographique"})
            n += 1
        if len(feats) < page_size:
            return n
        start += page_size


def ingest_batiments(session, bbox, commune, run_id, sids, page_size: int = 5000) -> int:
    """Bâtiments BD TOPO (IGN) — correctif R1 « déjà bâti » : la source bâtiment la plus
    complète disponible en open data (OSM sous-cartographie La Réunion, vérifié à l'audit :
    BP0571 ressortait à 18 % de bâti OSM alors que l'orthophoto montre une résidence
    entière). PAGINÉ (count/startIndex + tri stable cleabs) : >10k bâtiments par commune,
    bien au-delà du plafond d'une requête GetFeature.

    Consommé par le déclassement (ratio bâti par parcelle) et la fiche « Occupation » —
    PAS par la cascade (exclu de la pré-computation, cf. EvalContext.prime)."""
    wfs = WfsConnector("geoplateforme_wfs")
    n, start = 0, 0
    while True:
        fc = wfs.fetch_layer("geoplateforme_wfs", "BDTOPO_V3:batiment", bbox=bbox,
                             max_features=page_size, start_index=start, sort_by="cleabs")
        feats = fc.get("features", []) or []
        for f in feats:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            _insert_layer(session, "batiment", p.get("nature"), p.get("usage_1") or "bâtiment",
                          f["geometry"], sids.get(KIND_SOURCE["batiment"]), commune, run_id,
                          {"nature": p.get("nature"), "usage": p.get("usage_1"),
                           "nb_logements": p.get("nombre_de_logements"),
                           # Hauteur/étages BD TOPO (Lot B — SDP existante du potentiel résiduel).
                           "hauteur": p.get("hauteur"),
                           "nombre_d_etages": p.get("nombre_d_etages"),
                           "source": "BD TOPO IGN (Géoplateforme WFS)"})
            n += 1
        if len(feats) < page_size:
            return n
        start += page_size


def ingest_ocsge(session, bbox, commune, run_id, sids) -> int:
    """Occupation du sol (proxy BD CARTO `occupation_du_sol`, OCS GE 974 non exposé en WFS)."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "BDCARTO_V5:occupation_du_sol", bbox=bbox, max_features=3000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        nat = ((f.get("properties") or {}).get("nature") or "")
        low = nat.lower()
        if any(w in low for w in ("forêt", "foret", "bois", "végé", "vege", "lande", "verger", "haie")):
            sub = "naturel"
        elif any(w in low for w in ("cult", "agric", "vigne", "prairie", "canne")):
            sub = "agricole"
        else:
            sub = "artificialise"
        _insert_layer(session, "ocs_ge", sub, nat or "occupation du sol", f["geometry"],
                      sids.get(KIND_SOURCE["ocs_ge"]), commune, run_id, {"nature": nat, "src": "BDCARTO_V5"})
        n += 1
    return n


def ingest_pente(session, bbox, commune, run_id, sids, step_m: float = 180.0, chunk: int = 100) -> int:
    """Pente par échantillonnage RGE ALTI sur une GRILLE régulière (≈raster), batché.

    Indépendant du nombre de parcelles (grille fixe sur le bbox) → tient la commune
    entière sans des dizaines de milliers d'appels. Affichée, NON éliminatoire (§2)."""
    minlon, minlat, maxlon, maxlat = bbox
    dlat = step_m / 110574.0
    dlon = step_m / ((111320.0 * math.cos(math.radians((minlat + maxlat) / 2))) or 1.0)
    lats, y = [], minlat
    while y <= maxlat + dlat:
        lats.append(y)
        y += dlat
    lons, x = [], minlon
    while x <= maxlon + dlon:
        lons.append(x)
        x += dlon
    nodes = [(i, j, lons[j], lats[i]) for i in range(len(lats)) for j in range(len(lons))]
    elev: dict[tuple[int, int], float] = {}
    with _client() as c:
        for k in range(0, len(nodes), chunk):
            part = nodes[k:k + chunk]
            r = c.get(ALTI_URL, params={
                "lon": "|".join(f"{p[2]:.6f}" for p in part),
                "lat": "|".join(f"{p[3]:.6f}" for p in part),
                "resource": "ign_rge_alti_wld", "zonly": "true"})
            for idx, h in enumerate(r.json().get("elevations", [])):
                elev[(part[idx][0], part[idx][1])] = h
            time.sleep(0.21)  # quota 5 req/s
    n = 0
    for i in range(len(lats) - 1):
        for j in range(len(lons) - 1):
            hs = [elev.get((i, j)), elev.get((i, j + 1)), elev.get((i + 1, j)), elev.get((i + 1, j + 1))]
            hs = [h for h in hs if h is not None and h > -9999]
            if len(hs) < 2:
                continue
            slope = (max(hs) - min(hs)) / step_m * 100.0
            cell = {"type": "Polygon", "coordinates": [[
                [lons[j], lats[i]], [lons[j + 1], lats[i]], [lons[j + 1], lats[i + 1]],
                [lons[j], lats[i + 1]], [lons[j], lats[i]]]]}
            _insert_layer(session, "pente", None, "Pente RGE ALTI (grille)", cell,
                          sids.get(KIND_SOURCE["pente"]), commune, run_id, {"slope_pct": round(slope, 1)})
            n += 1
    return n


_GEO_DVF_CACHE: list[dict] | None = None  # dept 974 agrégé, téléchargé une fois par process


def ingest_dvf(session, insee, commune, run_id, sids) -> int:
    """DVF géolocalisé (Etalab, data.gouv) pour la commune.

    Remplace l'ancien flux ODS Région (2014-2021, surfaces lacunaires, mutation_id =
    parcelle). Apporte : millésime récent (5 ans glissants), id_mutation RÉEL (traçabilité),
    surface bâtie correcte agrégée PAR MUTATION (€/m² juste, plus de surcompte multi-lots),
    VEFA exploitable (= comparable « neuf »), et une vraie coordonnée de mutation."""
    global _GEO_DVF_CACHE
    if _GEO_DVF_CACHE is None:
        _GEO_DVF_CACHE = fetch_geo_dvf()  # dept 974 entier, une seule fois
    muts = [m for m in _GEO_DVF_CACHE if m["insee"] == insee]
    if not muts:
        return 0
    stmt = text(
        """INSERT INTO dvf_mutations
           (mutation_id, date_mutation, valeur_fonciere, type_local, surface_reelle_bati,
            surface_terrain, nature_mutation, commune, geom, raw)
           VALUES (:mid, :dt, :val, :tl, :sb, :st, :nat, :com,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:raw AS jsonb))""")
    params = [{**m, "com": commune,
               "raw": json.dumps({"source": "geo-dvf Etalab (data.gouv)",
                                  "id_mutation": m["mid"], "vefa": m["vefa"]})}
              for m in muts]
    session.execute(stmt, params)
    return len(params)


GEO_DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dep}.csv.gz"
GEO_DVF_YEARS = (2021, 2022, 2023, 2024, 2025)  # millésime « latest » Etalab (5 ans glissants)


def _geo_dvf_aggregate(rows: list[dict]) -> list[dict]:
    """Agrège les lignes geo-dvf (DVF géolocalisé Etalab) PAR MUTATION RÉELLE.

    DVF éclate une vente en plusieurs lignes (un local / lot / parcelle par ligne) qui
    portent TOUTES la valeur foncière TOTALE de la mutation. Un €/m² calculé ligne par
    ligne surévalue donc les ventes multi-lots. On regroupe par id_mutation, on somme la
    surface bâtie des locaux RÉSIDENTIELS (Maison/Appartement) et on divise la valeur par
    cette surface — €/m² correct, et dédoublonnage exact (le vrai défaut du flux ODS).

    On ne garde que les mutations mono-type, géolocalisées et avec surface : aucun prix
    fabriqué. La VEFA est conservée SI elle a une surface (geo-dvf la fournit, au contraire
    du flux ODS où elle vaut 0) — c'est le comparable « neuf » que vend un promoteur.
    """
    from collections import defaultdict
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["id_mutation"]].append(r)
    out: list[dict] = []
    for mid, rs in by.items():
        locs = [r for r in rs if r["type_local"] in ("Maison", "Appartement")
                and r["surface_reelle_bati"] and float(r["surface_reelle_bati"]) > 0]
        if not locs:
            continue
        types = {r["type_local"] for r in locs}
        if len(types) > 1:            # mutation appart+maison : €/m² ambigu → écartée
            continue
        vals = [float(r["valeur_fonciere"]) for r in rs if r["valeur_fonciere"]]
        coords = next(((r["longitude"], r["latitude"]) for r in locs
                       if r["longitude"] and r["latitude"]), None)
        if not vals or not coords:    # sans prix ou sans géolocalisation : inexploitable
            continue
        terr = next((float(r["surface_terrain"]) for r in rs if r.get("surface_terrain")), None)
        out.append({
            "mid": mid, "dt": rs[0]["date_mutation"], "val": max(vals),
            "tl": next(iter(types)),
            "sb": round(sum(float(r["surface_reelle_bati"]) for r in locs), 2),
            "st": terr, "nat": rs[0]["nature_mutation"], "insee": rs[0]["code_commune"],
            "lon": float(coords[0]), "lat": float(coords[1]),
            "vefa": any("futur" in r["nature_mutation"].lower() for r in rs),
        })
    return out


def fetch_geo_dvf(years: tuple[int, ...] = GEO_DVF_YEARS, dep: str = "974") -> list[dict]:
    """Télécharge geo-dvf (data.gouv, Etalab) pour un département et agrège par mutation."""
    import csv
    import gzip
    rows: list[dict] = []
    with _client() as c:
        for y in years:
            r = c.get(GEO_DVF_URL.format(year=y, dep=dep), timeout=120.0)
            r.raise_for_status()
            txt = gzip.decompress(r.content).decode("utf-8", "replace")
            rows += list(csv.DictReader(txt.splitlines()))
    return _geo_dvf_aggregate(rows)


def load_dvf_geo(session: Session, target: str = "dvf_mutations",
                 years: tuple[int, ...] = GEO_DVF_YEARS) -> int:
    """Charge geo-dvf dans `target` : mutation_id = id_mutation RÉEL (traçabilité corrigée),
    géométrie = vraie coordonnée lon/lat de la mutation (plus le centroïde de parcelle).
    N'insère que les communes ayant des parcelles chargées (jointure commune du moteur).
    Idempotent à l'appelant : vider `target` avant si rechargement. Renvoie le nombre inséré."""
    muts = fetch_geo_dvf(years)
    insee2com = {idu[:5]: com for (com, idu) in session.execute(
        text("SELECT commune, min(idu) FROM parcels GROUP BY commune")).all()}
    stmt = text(f"""
        INSERT INTO {target}
          (mutation_id, date_mutation, valeur_fonciere, type_local,
           surface_reelle_bati, surface_terrain, nature_mutation, commune, geom, raw)
        VALUES
          (:mid, :dt, :val, :tl, :sb, :st, :nat, :com,
           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:raw AS jsonb))""")
    params = []
    for m in muts:
        com = insee2com.get(m["insee"])
        if com is None:
            continue
        params.append({**m, "com": com,
                       "raw": json.dumps({"source": "geo-dvf Etalab (data.gouv)",
                                          "id_mutation": m["mid"], "vefa": m["vefa"]})})
    if params:
        session.execute(stmt, params)
    return len(params)


def ingest_foret_publique(session, bbox, commune, run_id, sids) -> int:
    """Forêts publiques / régime forestier — BD TOPO (IGN/ONF) via WFS Géoplateforme."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "BDTOPO_V3:foret_publique", bbox=bbox, max_features=5000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        topo = p.get("toponyme") or ""
        subtype = "domaniale" if "domanial" in topo.lower() else "publique"
        _insert_layer(session, "foret_publique", subtype, topo or "Forêt publique", f["geometry"],
                      sids.get("Forêts publiques (ONF)"), commune, run_id,
                      {"toponyme": topo, "src": "BDTOPO_V3:foret_publique"})
        n += 1
    return n


def ingest_rpg_agricole(session, bbox, commune, run_id, sids) -> int:
    """Parcelles agricoles déclarées (RPG, IGN/ASP via WFS) → proxy zonage agricole/SAFER."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "RPG.LATEST:parcelles_graphiques", bbox=bbox, max_features=12000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        _insert_layer(session, "safer", "rpg", f"Parcelle agricole RPG ({p.get('code_cultu') or '?'})",
                      f["geometry"], sids.get("Zonage SAFER (DAAF)"), commune, run_id,
                      {"code_cultu": p.get("code_cultu"), "code_group": p.get("code_group"), "src": "RPG.LATEST"})
        n += 1
    return n


_PROTECTED = [
    ("patrinat_apb:apb", "APB"),
    ("patrinat_aphn:aire_protection_habitats_naturels", "APHN"),
    ("patrinat_rnn:rnn", "Réserve naturelle nationale"),
    ("patrinat_rnr:rnr", "Réserve naturelle régionale"),
    ("patrinat_rb:reserve_biologique", "Réserve biologique"),
    ("patrinat_cen:cen", "Conservatoire d'espaces naturels"),
    ("patrinat_cdl:conservatoire_littoral", "Conservatoire du littoral"),
]


def ingest_espaces_proteges(session, bbox, commune, run_id, sids) -> int:
    """Espaces protégés réglementaires (INPN/MNHN via WFS Géoplateforme) → couche `ens`.

    ENS départemental proprement dit non public ; on intègre les protections
    réglementaires (APB/APHN/réserves/conservatoires) qui jouent le même rôle de
    contrainte. Étiquetées par leur vrai type."""
    wfs = WfsConnector("geoplateforme_wfs")
    n = 0
    for typename, label in _PROTECTED:
        try:
            fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=bbox, max_features=2000)
        except Exception:
            continue
        for f in fc.get("features", []) or []:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            # M1 : ne JAMAIS flaguer du foncier terrestre avec une protection MARINE
            # (ex. Réserve naturelle marine de La Réunion). On garde les protections terrestres.
            if str(p.get("marin", "")).strip().upper() in ("T", "OUI", "TRUE", "1"):
                continue
            nom = p.get("nom_site") or p.get("nom") or p.get("toponyme") or p.get("libelle") or label
            _insert_layer(session, "ens", label.lower().replace(" ", "_")[:48], f"{label} — {nom}"[:255],
                          f["geometry"], sids.get("ENS (Département)"), commune, run_id,
                          {"type": label, "src": typename, "marin": p.get("marin")})
            n += 1
    return n


def _taux_subtype(taux) -> str:
    """Mappe le taux d'évolution (m/an) du trait de côte vers le vocabulaire cascade."""
    if taux is None or taux <= -9000:
        return "indetermine"           # -9999 = donnée absente
    if taux <= -1.0:
        return "bande_courte"          # recul fort → HARD_EXCLUDE
    if taux < -0.1:
        return "bande_longue"          # recul modéré → SOFT_FLAG
    return "stable"                    # stable / accrétion → PASS


def ingest_trait_de_cote(session, commune, run_id, sids) -> int:
    """Indicateur national d'érosion côtière (Cerema/GéoLittoral) — SHP Réunion EPSG:2975.

    Téléchargé puis reprojeté 2975→4326 (pyproj). `taux` (m/an) → recul fort = exclude,
    recul modéré = flag (cf. config/cascade_rules.yaml : trait_de_cote)."""
    import shapefile  # pyshp
    from pyproj import Transformer

    with _client() as c:
        r = c.get(EROSION_URL)
        r.raise_for_status()
    tmp = tempfile.mkdtemp(prefix="labuse_tdc_")
    zipfile.ZipFile(io.BytesIO(r.content)).extractall(tmp)
    shp = next((os.path.join(tmp, f) for f in os.listdir(tmp) if f.lower().endswith(".shp")), None)
    if not shp:
        return 0
    rd = shapefile.Reader(shp)
    flds = [f[0] for f in rd.fields[1:]]
    ti = flds.index("taux") if "taux" in flds else None
    tr = Transformer.from_crs(2975, 4326, always_xy=True)
    n = 0
    for srec in rd.shapeRecords():
        sh = srec.shape
        if not sh.points or sh.shapeType not in (5, 15, 25):
            continue
        taux = float(srec.record[ti]) if ti is not None else None
        parts = list(sh.parts) + [len(sh.points)]
        polys = []
        for k in range(len(parts) - 1):
            ring = sh.points[parts[k]:parts[k + 1]]
            coords = [list(tr.transform(x, y)) for (x, y) in ring]
            if len(coords) >= 4:
                polys.append([coords])
        if not polys:
            continue
        _insert_layer(session, "trait_de_cote", _taux_subtype(taux),
                      f"Évolution trait de côte (taux {taux} m/an)",
                      {"type": "MultiPolygon", "coordinates": polys},
                      sids.get(KIND_SOURCE["trait_de_cote"]), commune, run_id,
                      {"taux": taux, "src": "GéoLittoral/Cerema — indicateur érosion (SHP, EPSG:2975)"})
        n += 1
    return n


def _overpass(query: str, tries: int = 3) -> dict:
    """POST Overpass, résilient : retries + bascule de mirror (Overpass est souvent saturé).

    ⚠ Client à 180 s : les requêtes portent `[timeout:90]` côté serveur ; le client DOIT attendre
    plus longtemps (le client par défaut à 60 s provoquait des ReadTimeout sur les grosses communes)."""
    last: Exception | None = None
    with httpx.Client(timeout=180.0, headers={"User-Agent": constants.USER_AGENT},
                      follow_redirects=True) as c:
        for mirror in OVERPASS_MIRRORS:
            for attempt in range(tries):
                try:
                    r = c.post(mirror, data={"data": query})
                    r.raise_for_status()
                    return r.json()
                except Exception as exc:  # noqa: BLE001 - on retente / on bascule
                    last = exc
                    time.sleep(2 ** attempt)
    raise last  # type: ignore[misc]


def _osm_fp_subtype(tags: dict) -> str | None:
    if tags.get("landuse") == "cemetery" or tags.get("amenity") == "grave_yard":
        return "cemetery"
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("leisure") == "pitch":
        return "pitch"
    if tags.get("amenity") == "parking":
        return "parking"
    return None


def _osm_ring(geometry: list) -> list | None:
    coords = [[g["lon"], g["lat"]] for g in (geometry or []) if g.get("lon") is not None]
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords if len(coords) >= 4 else None


def ingest_osm_faux_positifs(session, bbox, commune, run_id, sids) -> int:
    """Faux positifs géométriques OSM (cimetière / école / terrain de sport / parking) via
    Overpass → kind='osm_faux_positif'. Étiquettes mappées vers les subtypes que la cascade
    consomme (hard: cemetery/school ; flag: pitch/parking). Empêche qu'un équipement public
    ressorte en « opportunité »."""
    minlon, minlat, maxlon, maxlat = bbox
    data = _overpass(_OSM_FP_QUERY.format(s=minlat, w=minlon, n=maxlat, e=maxlon))
    src = sids.get(KIND_SOURCE["osm_faux_positif"])
    n = 0
    for el in data.get("elements", []) or []:
        sub = _osm_fp_subtype(el.get("tags", {}) or {})
        if not sub:
            continue
        geom = None
        if el.get("type") == "way":
            ring = _osm_ring(el.get("geometry"))
            if ring:
                geom = {"type": "Polygon", "coordinates": [ring]}
        elif el.get("type") == "relation":
            polys = [[r] for m in (el.get("members") or [])
                     if m.get("role") == "outer" and (r := _osm_ring(m.get("geometry")))]
            if polys:
                geom = {"type": "MultiPolygon", "coordinates": polys}
        if not geom:
            continue
        name = (el.get("tags", {}) or {}).get("name") or f"{sub} (OSM)"
        _insert_layer(session, "osm_faux_positif", sub, name[:255], geom, src, commune, run_id,
                      {"osm_id": el.get("id"), "osm_type": el.get("type"), "subtype": sub})
        n += 1
    return n


def ingest_layers(session: Session, insee: str, commune: str,
                  bbox: tuple[float, float, float, float], run_id: int | None) -> dict[str, object]:
    """Ingère toutes les couches géométriques réelles disponibles. Isolé par couche."""
    sids = _source_ids(session)
    counts: dict[str, object] = {}
    jobs = [
        ("plu_gpu_zone", lambda: ingest_gpu_zones(session, insee, bbox, commune, run_id, sids)),
        ("plu_gpu_prescription", lambda: ingest_gpu_prescriptions(session, bbox, commune, run_id, sids)),
        ("parc_national", lambda: ingest_parc_national(session, commune, run_id, sids)),
        ("potentiel_foncier", lambda: ingest_potentiel_foncier(session, insee, commune, run_id, sids)),
        ("abf", lambda: ingest_abf(session, bbox, commune, run_id, sids)),
        ("water", lambda: ingest_bdtopo(session, bbox, commune, run_id, sids, "water", "BDTOPO_V3:surface_hydrographique")),
        ("ravine", lambda: ingest_ravines(session, bbox, commune, run_id, sids)),
        ("voirie", lambda: ingest_bdtopo(session, bbox, commune, run_id, sids, "voirie", "BDTOPO_V3:troncon_de_route")),
        ("batiment", lambda: ingest_batiments(session, bbox, commune, run_id, sids)),
        ("ocs_ge", lambda: ingest_ocsge(session, bbox, commune, run_id, sids)),
        ("foret_publique", lambda: ingest_foret_publique(session, bbox, commune, run_id, sids)),
        ("safer", lambda: ingest_rpg_agricole(session, bbox, commune, run_id, sids)),
        ("ens", lambda: ingest_espaces_proteges(session, bbox, commune, run_id, sids)),
        ("trait_de_cote", lambda: ingest_trait_de_cote(session, commune, run_id, sids)),
        ("pente", lambda: ingest_pente(session, bbox, commune, run_id, sids)),
        ("osm_faux_positif", lambda: ingest_osm_faux_positifs(session, bbox, commune, run_id, sids)),
        ("ppr", lambda: ingest_ppr_zone(session, bbox, commune, run_id, sids, insee)),
        ("georisque_alea", lambda: ingest_georisque_alea(session, bbox, commune, run_id, sids, insee)),
        ("sar", lambda: ingest_sar(session, insee, commune, run_id, sids)),
        ("dvf", lambda: ingest_dvf(session, insee, commune, run_id, sids)),
    ]
    for kind, fn in jobs:
        try:
            # SAVEPOINT par couche : un échec n'annule QUE cette couche (§4), pas les parcelles.
            with session.begin_nested():
                counts[kind] = fn()
        except Exception as exc:
            counts[kind] = f"ERREUR {type(exc).__name__}: {exc}"
    return counts
