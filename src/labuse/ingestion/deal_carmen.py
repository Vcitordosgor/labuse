"""SOURCES-1 lot 2 — couches DEAL Réunion servies par le WFS Carmen (nœud 29).

Service RÉEL vérifié le 07/09/2026 : `DEAL_REUNION_2020` (MapServer WFS 1.0.0, GML,
EPSG:2975, 187 couches — le nœud Carmen N'A PAS migré pour ces couches, contrairement à la
réserve du rapport). Trois sources du mandat y puisent :

· **Ravines DPF** (`deal_dpf_dpe`) — `Cours_d_eau_DPF` (275 tronçons, arrêté préfectoral
  n°06-3077/SG/DRCTV du 21/08/2006) + `Plan_d_eau_DPF` (6) → kind='dpf'. La fiche Sextant
  du rapport n'offre AUCUNE distribution (WMS de visualisation seul) — c'est CE WFS qui sert.
· **Zones humides** (`deal_zones_humides`) — les inventaires DEAL par SECTEURS (couverture
  partielle DITE, jamais une preuve d'absence) → kind='zone_humide' :
  Habitats_ZH_2011 (1 507), ZH_2009 (187) + espaces fonctionnels (30), ZH_2003 (49),
  Zones_humides_basse_altitude_2019 (1 349).
· **Espaces protégés complémentaires** — `RAMSAR` (1, Étang Saint-Paul) et
  `Sites_Class_Inscr` (7, attribut Type classe/inscrit) → kind='ens', subtypes `ramsar`,
  `site_classe`, `site_inscrit` (complètent l'ENP INPN ; purge par SUBTYPE seulement,
  jamais le kind entier — les subtypes INPN restent).

GML → GeoJSON par `ogr2ogr` (GDAL, présent dans l'env) : Carmen ne sert PAS de GeoJSON
(ServiceException vérifiée). Purge par (kind, subtypes du module), idempotent.
`ALEA_INONDATION` (75) N'EST PAS ingérée : doublon vérifié de `georisque_alea/inondation`
(76 entités DEAL Lizmap déjà servies par la couche cascade `risques`).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .layers_ingest import _insert_layer

BASE = "http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020"
SOURCE_DPF = "Ravines — domaine public fluvial (DEAL Carmen)"
SOURCE_ZH = "Zones humides — inventaires DEAL (Carmen)"
SOURCE_ENP_C = "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)"

#: typename Carmen → (kind, subtype, nom de source data_sources, champs d'attrs gardés)
LAYERS: list[dict] = [
    {"typename": "Cours_d_eau_DPF", "kind": "dpf", "subtype": "cours_eau",
     "source": SOURCE_DPF, "props": ("TOPONYME", "CLASSE", "CODE_HYDRO")},
    {"typename": "Plan_d_eau_DPF", "kind": "dpf", "subtype": "plan_eau",
     "source": SOURCE_DPF, "props": ("Toponyme", "Commune", "Typologie")},
    {"typename": "Habitats_ZH_2011", "kind": "zone_humide", "subtype": "habitats_2011",
     "source": SOURCE_ZH, "props": ("Nature", "Localite")},
    {"typename": "ZH_2009", "kind": "zone_humide", "subtype": "inventaire_2009",
     "source": SOURCE_ZH, "props": ("Nom", "Typologie", "Surface_ha", "Statut_de_")},
    {"typename": "ZH_2009_Espace_Fonct", "kind": "zone_humide",
     "subtype": "espace_fonctionnel_2009", "source": SOURCE_ZH,
     "props": ("Nom", "SAGE", "Nature")},
    {"typename": "ZH_2003", "kind": "zone_humide", "subtype": "inventaire_2003",
     "source": SOURCE_ZH, "props": ("Toponyme", "Type")},
    {"typename": "Zones_humides_basse_altitude_2019", "kind": "zone_humide",
     "subtype": "basse_altitude_2019", "source": SOURCE_ZH,
     "props": ("zone", "date", "organisme", "type_obs")},
    {"typename": "RAMSAR", "kind": "ens", "subtype": "ramsar",
     "source": SOURCE_ENP_C, "props": ("nom", "surf")},
    # Reserve_Naturelle Carmen = RNN Étang Saint-Paul (zones A/B) + RÉSERVE MARINE (absente
    # du jeu INPN local, vérifié 07/09/2026). Chevauche l'entité INPN
    # réserve_naturelle_nationale (Étang) — même verdict cascade (hard), chevauchement DIT.
    {"typename": "Reserve_Naturelle", "kind": "ens", "subtype": "reserve_naturelle",
     "source": SOURCE_ENP_C, "props": ("NOM", "DATE", "ZONE", "SURFACE_HA")},
    # Sites_Class_Inscr : subtype résolu par entité (Type = classe | inscrit)
    {"typename": "Sites_Class_Inscr", "kind": "ens", "subtype": None,
     "source": SOURCE_ENP_C, "props": ("NOM", "Date", "Type")},
]

SUBTYPES_DU_MODULE = ("ramsar", "site_classe", "site_inscrit", "reserve_naturelle")


def _fetch_geojson(typename: str, client: httpx.Client, tmpdir: str) -> list[dict]:
    """GetFeature GML complet → ogr2ogr → features GeoJSON (EPSG:4326)."""
    gml = Path(tmpdir) / f"{typename}.gml"
    gj = Path(tmpdir) / f"{typename}.json"
    with client.stream("GET", BASE, params={
            "SERVICE": "WFS", "VERSION": "1.0.0", "REQUEST": "GetFeature",
            "TYPENAME": typename}) as r:
        r.raise_for_status()
        with open(gml, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    res = subprocess.run(
        ["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", "-s_srs", "EPSG:2975",
         str(gj), str(gml)],
        capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"ogr2ogr {typename} : {res.stderr[:300]}")
    return json.load(open(gj)).get("features") or []


def _site_subtype(props: dict) -> str:
    t = (props.get("Type") or "").strip().lower()
    return "site_classe" if t == "classe" else ("site_inscrit" if t == "inscrit" else "site_classe")


def ingest_deal_carmen(session: Session, source_ids: dict[str, int | None] | None = None,
                       run_id: int | None = None, log=print,
                       client: httpx.Client | None = None) -> dict:
    """Ingère les 9 couches Carmen. Purge : kinds dpf/zone_humide entiers + subtypes ens du
    module (jamais le kind ens entier). Rend {typename: n}."""
    sids = source_ids or {}
    session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('dpf', 'zone_humide')"))
    session.execute(text(
        "DELETE FROM spatial_layers WHERE kind = 'ens' AND subtype = ANY(:st)"),
        {"st": list(SUBTYPES_DU_MODULE)})
    out: dict[str, int] = {}
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 300.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            for lay in LAYERS:
                feats = _fetch_geojson(lay["typename"], c, tmpdir)
                n = 0
                for f in feats:
                    g = f.get("geometry")
                    if not g:
                        continue
                    p = f.get("properties") or {}
                    sub = lay["subtype"] or _site_subtype(p)
                    nom = (p.get("TOPONYME") or p.get("Toponyme") or p.get("NOM")
                           or p.get("Nom") or p.get("nom") or p.get("Nature")
                           or lay["typename"])
                    attrs = {k.lower(): p.get(k) for k in lay["props"] if p.get(k) is not None}
                    attrs["source"] = "DEAL Réunion — Carmen (DEAL_REUNION_2020)"
                    attrs["typename"] = lay["typename"]
                    _insert_layer(session, lay["kind"], sub, str(nom)[:250], g,
                                  sids.get(lay["source"]), None, run_id, attrs=attrs)
                    n += 1
                out[lay["typename"]] = n
                log(f"  {lay['typename']} : {n} entité(s) → {lay['kind']}"
                    + (f"/{lay['subtype']}" if lay["subtype"] else " (classe/inscrit)"))
    finally:
        if own:
            c.close()
    session.flush()
    return out
