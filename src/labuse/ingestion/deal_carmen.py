"""SOURCES-1 lot 2, MIGRÉ SOURCES-2 lot 1 — couches DEAL Réunion par le WFS LIZMAP.

Endpoint RÉEL vérifié le 13/09/2026 : `deal974.lizmap.com` (QGIS Server, WFS 1.0.0/1.1.0,
GeoJSON NATIF, EPSG:2975 reprojeté 4326 par srsName) — le portail cartographique PROPRE de la
DEAL, à la place du nœud Carmen 29 (`DEAL_REUNION_2020`, MapServer, GML seul → ogr2ogr).
Ce que la migration change : plus de dépendance GDAL, le GeoJSON arrive tel quel ; et le
projet `00cartogenerale/deal_reunion` sert EN PLUS la couche `Espace_Naturel_Sensible` du
Département (gestionnaire, propriété, dateMAJ — jamais servie par Carmen) et le projet
`02sprinr/02etat_ppr_pac` la couche « état des PAC, PPR, PPRL et leur date d'approbation »
(24 communes, statuts Approuve/En revision + dates) qui sert la FRAÎCHEUR des PPR.
Les noms de sources au registre gardent leur id historique « (DEAL Carmen) » — c'est la clé
stable de `data_sources` ; l'endpoint et les notes disent la vérité Lizmap.

Trois sources du mandat y puisent :
· **Ravines DPF** — `Cours_d_eau_DPF` (275 tronçons, arrêté préfectoral n°06-3077/SG/DRCTV
  du 21/08/2006) + `Plan_d_eau_DPF` (6) → kind='dpf'.
· **Zones humides** — inventaires DEAL par SECTEURS (couverture partielle DITE, jamais une
  preuve d'absence) → kind='zone_humide' : Zones_Humides_2011, Zones_humides_2009 (+ espaces
  fonctionnels), Zones_humides_2003, Zones_humides_basse_altitude__2019.
· **Espaces protégés complémentaires** — ramsar, Sites_Classes_-_Inscrits, réserves
  naturelles (Étang Saint-Paul + RNMR marine) + `Espace_Naturel_Sensible` (Département)
  → kind='ens', subtypes du module (purge par SUBTYPE seulement, jamais le kind entier —
  les subtypes INPN restent).

`ALEA_INONDATION` n'est PAS ingérée ici : doublon vérifié de `georisque_alea/inondation`
(déjà servie par la couche cascade `risques`, même WFS Lizmap projet 01risque).
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .layers_ingest import _insert_layer

BASE_CARTOGEN = ("https://deal974.lizmap.com/cartes/index.php/lizmap/service"
                 "?repository=00cartogenerale&project=deal_reunion")
BASE_ETAT_PPR = ("https://deal974.lizmap.com/cartes/index.php/lizmap/service"
                 "?repository=02sprinr&project=02etat_ppr_pac")
SOURCE_DPF = "Ravines — domaine public fluvial (DEAL Carmen)"
SOURCE_ZH = "Zones humides — inventaires DEAL (Carmen)"
SOURCE_ENP_C = "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)"
SOURCE_PPR = "DEAL Réunion — PPR / aléas"

#: typename Lizmap (00cartogenerale/deal_reunion) → (kind, subtype, source, attrs gardés)
LAYERS: list[dict] = [
    {"typename": "Cours_d_eau_DPF", "kind": "dpf", "subtype": "cours_eau",
     "source": SOURCE_DPF, "props": ("TOPONYME", "CLASSE", "CODE_HYDRO")},
    {"typename": "Plan_d_eau_DPF", "kind": "dpf", "subtype": "plan_eau",
     "source": SOURCE_DPF, "props": ("Toponyme", "Commune", "Typologie")},
    {"typename": "Zones_Humides_2011", "kind": "zone_humide", "subtype": "habitats_2011",
     "source": SOURCE_ZH, "props": ("Nature", "Localite")},
    {"typename": "Zones_humides_2009", "kind": "zone_humide", "subtype": "inventaire_2009",
     "source": SOURCE_ZH, "props": ("Nom", "Typologie", "Surface_ha", "Statut_de_")},
    {"typename": "Zones_humides_2009_Espace_de_fonctionnalite", "kind": "zone_humide",
     "subtype": "espace_fonctionnel_2009", "source": SOURCE_ZH,
     "props": ("Nom", "SAGE", "Nature")},
    {"typename": "Zones_humides_2003", "kind": "zone_humide", "subtype": "inventaire_2003",
     "source": SOURCE_ZH, "props": ("Toponyme", "Type")},
    {"typename": "Zones_humides_basse_altitude__2019", "kind": "zone_humide",
     "subtype": "basse_altitude_2019", "source": SOURCE_ZH,
     "props": ("zone", "date", "organisme", "type_obs")},
    {"typename": "ramsar", "kind": "ens", "subtype": "ramsar",
     "source": SOURCE_ENP_C, "props": ("nom", "surf")},
    # Deux couches distinctes sur Lizmap (Carmen les fusionnait) : RNN Étang Saint-Paul
    # (zones A/B) + réserve marine RNMR. Chevauchement avec l'entité INPN DIT (même verdict).
    {"typename": "Reserve_naturelle_Etang_de_Saint-Paul", "kind": "ens",
     "subtype": "reserve_naturelle", "source": SOURCE_ENP_C,
     "props": ("NOM", "DATE", "ZONE", "SURFACE_HA")},
    {"typename": "Reserve_Naturelle_Marine_Regionale__RNMR", "kind": "ens",
     "subtype": "reserve_naturelle", "source": SOURCE_ENP_C,
     "props": ("Nom_zone", "Statut_RNM", "Secteur", "Surface_ha")},
    # Sites_Classes_-_Inscrits : subtype résolu par entité (Type = classe | inscrit)
    {"typename": "Sites_Classes_-_Inscrits", "kind": "ens", "subtype": None,
     "source": SOURCE_ENP_C, "props": ("NOM", "Date", "Type")},
    # SOURCES-2 — la couche ENS du DÉPARTEMENT (« ms:ENS » du rapport producteurs), jamais
    # servie par Carmen : gestionnaire, propriété, dateMAJ, date d'acquisition.
    {"typename": "Espace_Naturel_Sensible", "kind": "ens", "subtype": "ens_departement",
     "source": SOURCE_ENP_C, "props": ("LieuDit", "Propriété", "Gestion_Op", "type",
                                       "dateMAJ", "dateacqui", "SurfaceSIG")},
]

SUBTYPES_DU_MODULE = ("ramsar", "site_classe", "site_inscrit", "reserve_naturelle",
                      "ens_departement")


def _fetch_geojson(base: str, typename: str, client: httpx.Client) -> list[dict]:
    """GetFeature GeoJSON natif (QGIS Server), reprojeté EPSG:4326 par srsName."""
    r = client.get(base.split("?")[0], params=dict(
        [kv.split("=", 1) for kv in base.split("?", 1)[1].split("&")],
        SERVICE="WFS", VERSION="1.0.0", REQUEST="GetFeature",
        TYPENAME=typename, OUTPUTFORMAT="GeoJSON", SRSNAME="EPSG:4326"))
    r.raise_for_status()
    return r.json().get("features") or []


def _site_subtype(props: dict) -> str:
    t = (props.get("Type") or "").strip().lower()
    return "site_classe" if t == "classe" else ("site_inscrit" if t == "inscrit" else "site_classe")


def _nettoyer_geom(g: dict) -> dict | None:
    """QGIS Server sert tels quels des anneaux DÉGÉNÉRÉS (tous points identiques — ogr2ogr les
    nettoyait pour Carmen) : on retire les anneaux < 3 points distincts ; None si rien ne reste."""
    def _ring_ok(ring: list) -> bool:
        return len({tuple(pt) for pt in ring}) >= 3

    if g.get("type") == "Polygon":
        rings = [r for r in g.get("coordinates") or [] if _ring_ok(r)]
        return {"type": "Polygon", "coordinates": rings} if rings else None
    if g.get("type") == "MultiPolygon":
        polys = []
        for poly in g.get("coordinates") or []:
            rings = [r for r in poly if _ring_ok(r)]
            if rings:
                polys.append(rings)
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None
    return g


def ingest_deal_carmen(session: Session, source_ids: dict[str, int | None] | None = None,
                       run_id: int | None = None, log=print,
                       client: httpx.Client | None = None) -> dict:
    """Ingère les couches DEAL depuis le WFS Lizmap. Purge : kinds dpf/zone_humide entiers +
    subtypes ens du module (jamais le kind ens entier). Rend {typename: n}."""
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
        for lay in LAYERS:
            feats = _fetch_geojson(BASE_CARTOGEN, lay["typename"], c)
            n = 0
            for f in feats:
                g = _nettoyer_geom(f.get("geometry")) if f.get("geometry") else None
                if not g:
                    continue
                p = f.get("properties") or {}
                sub = lay["subtype"] or _site_subtype(p)
                nom = (p.get("TOPONYME") or p.get("Toponyme") or p.get("NOM")
                       or p.get("Nom") or p.get("nom") or p.get("Nom_zone")
                       or p.get("LieuDit") or p.get("Nature") or lay["typename"])
                attrs = {k.lower(): p.get(k) for k in lay["props"] if p.get(k) is not None}
                attrs["source"] = "DEAL Réunion — Lizmap (deal974.lizmap.com)"
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


# ─────────────── état des PPR / PAC par commune (SOURCES-2 lot 1 — la fraîcheur) ───────────────

_TN_ETAT_PPR = "PPR_inondation_et_mouvement_de_terrain_approuves_et_leur_date_d_approbation"


def _fr_date_iso(v: str | None) -> str | None:
    """'26/03/2012' → '2012-03-26' (None si vide/illisible)."""
    try:
        j, m, a = (v or "").strip().split("/")
        return f"{a}-{m}-{j}"
    except ValueError:
        return None


def ingest_ppr_etat(session: Session, source_ids: dict[str, int | None] | None = None,
                    run_id: int | None = None, log=print,
                    client: httpx.Client | None = None) -> dict:
    """SOURCES-2 lot 1 — la couche « état des PAC, PPR, PPRL et leur date d'approbation »
    (projet Lizmap 02sprinr/02etat_ppr_pac, 24 communes) → kind='ppr_etat', une entité par
    commune : statuts PPR-L / PPR-i-mvt (Approuve | En revision | 0) et dates (approbation,
    PAC inondation/mvt/submersion/RTC). Sert la FRAÎCHEUR : le `source_millesime` de la
    source PPR devient la plus récente date d'approbation lue chez le producteur."""
    sids = source_ids or {}
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        feats = _fetch_geojson(BASE_ETAT_PPR, _TN_ETAT_PPR, c)
    finally:
        if own:
            c.close()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'ppr_etat'"))
    n, dates = 0, []
    for f in feats:
        p = f.get("properties") or {}
        insee, nom = p.get("code_insee"), p.get("nom")
        if not insee or not f.get("geometry"):
            continue
        attrs = {
            "code_insee": insee,
            "ppr_littoral_statut": p.get("PPR-L"),
            "ppr_littoral_date": _fr_date_iso(p.get("Date_Litto")),
            "ppr_inond_mvt_statut": p.get("PPR-i-mvt"),
            "ppr_inond_mvt_date": _fr_date_iso(p.get("Date_i-mvt")),
            "pac_inondation": _fr_date_iso(p.get("PAC_inond_")),
            "pac_mouvement_terrain": _fr_date_iso(p.get("PAC_mvt")),
            "pac_submersion_marine": _fr_date_iso(p.get("PAC_sub-ma")),
            "pac_recul_trait_cote": _fr_date_iso(p.get("PAC_RTC")),
            "source": "DEAL Réunion — Lizmap (02etat_ppr_pac)",
        }
        dates += [d for d in (attrs["ppr_littoral_date"], attrs["ppr_inond_mvt_date"]) if d]
        _insert_layer(session, "ppr_etat", (p.get("PPR-i-mvt") or "inconnu").lower(),
                      f"État PPR — {nom}", f["geometry"],
                      sids.get(SOURCE_PPR), nom, run_id, attrs=attrs)
        n += 1
    if dates:
        session.execute(text(
            "UPDATE data_sources SET source_millesime = :m WHERE name = :n"),
            {"m": f"PPR le plus récent approuvé le {max(dates)} (état DEAL)",  # varchar(64)
             "n": SOURCE_PPR})
    session.flush()
    log(f"  état PPR/PAC : {n} commune(s), millésime producteur = {max(dates) if dates else '—'}")
    return {"communes": n, "millesime": max(dates) if dates else None}
