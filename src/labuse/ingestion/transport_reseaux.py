"""M106 P4 — TRANSPORT PUBLIC, TÉLÉPHÉRIQUE, LIGNES HAUTE TENSION (arbitrage Vic 17/08/2026).

Quatre kinds nouveaux dans spatial_layers (île entière, commune=NULL — servis partout) :
· `transport_arret`  — les quais GTFS des 7 réseaux (Licence Ouverte, PAN), attrs.nb_lignes ;
· `transport_ligne`  — les tracés (shapes GTFS) par ligne, MultiLineString ;
· `pole_echange`     — DEUX sources DITES : subtype='osm' (stations/gares routières OSM,
  Sourcé) et subtype='gtfs' (DÉRIVÉ : arrêt desservi par ≥ seuil lignes — seuil en config
  config/transport.yaml, statut Estimé). Concordance OSM↔GTFS mesurée et écrite dans attrs
  (confirme / osm_seul / gtfs_seul) — une contradiction se DIT, elle n'est pas tranchée en
  silence (arbitrage) ;
· `telepherique`     — le Papang SEUL (OSM aerialway=gondola EN SERVICE + stations).
  La ligne 2 « Zèl La Montagne » (2029) n'a AUCUN tracé publié : le way OSM `proposed`
  est une anticipation de contributeur — EXCLU explicitement (faux positif banquier) ;
· `ligne_ht`         — BD TOPO IGN `ligne_electrique` (EDF SEI a retiré ses couches le
  24/12/2025 — aucun contournement). La tension voyage en attrs. La servitude I4 n'existe
  pas en vectoriel : on sert la DISTANCE, jamais la servitude (le libellé fiche le dit).

Ingestion versionnée (IngestionRun), idempotente (DELETE kind avant ré-insertion),
millésimes amont écrits dans data_sources (jamais la date d'ingestion en dur).

M137-V — BACKLOG (trou de couverture GTFS) : la mesure OSM famille E × GTFS (< 50 m) montre que
6 464 arrêts de bus OSM sont à 92,6 % déjà dans `transport_arret` — ils ont donc été RETIRÉS de
l'affichage de la couche Équipements (doublon visible). MAIS 478 arrêts OSM (les 24 communes)
n'ont PAS d'équivalent GTFS : ce sont des trous du GTFS (réseaux/quais manquants au PAN), à
traiter ICI — enrichir `transport_arret` depuis OSM — et NON à laisser dans Équipements. Non fait
(demande de donnée / arbitrage réseau à ouvrir).
"""
from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from collections import Counter, defaultdict

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config as _cfg
from .layers_ingest import KIND_SOURCE, _insert_layer, _source_ids

log = logging.getLogger("labuse")

ILE_BBOX = (55.20, -21.42, 55.90, -20.85)
OVERPASS = "https://overpass-api.de/api/interpreter"
PAN_LIST = "https://transport.data.gouv.fr/api/datasets"

#: les 7 jeux GTFS du Point d'Accès National (slug PAN → nom de réseau servi à l'écran).
GTFS_RESEAUX: list[tuple[str, str]] = [
    ("horaires-theoriques-au-format-gtfs-et-horaires-temps-reel-au-format-gtfs-rt-du-reseau-car-jaune-a-la-reunion", "Car Jaune"),
    ("horaire-du-reseau-citalis", "Citalis"),
    ("citalis-telepherique-papang", "Papang"),
    ("reseau-karouest", "Kar'Ouest"),
    ("donnees-du-reseau-alterneo", "Alternéo"),
    ("referentiel-topologique-reseau-carsud", "Carsud"),
    ("jeu-de-donnee-spl-estival-2025", "Estival"),
]

SRC_GTFS = "Transport public — GTFS (PAN, 7 réseaux)"
SRC_OSM_TRANSPORT = "OSM — transport (pôles d'échange & téléphérique)"
SRC_BDTOPO = "BD TOPO IGN"
#: RETOURS-13 R5 — la couche TCSP « en service » est extraite d'OSM (voies bus en site propre) :
#: aucune source SIG publique d'axe TCSP n'existe au 974 (recherche du 05/09/2026, URL par URL au
#: compte-rendu : PEIGEO/AGORAH 0 fiche, data.regionreunion 0 jeu, transecoexpress.re injoignable,
#: EPCI sans SIG — le « SIG TCSP » CIVIS est un récolement paysager d'un tronçon, pas un axe).
SRC_OSM_TCSP = "TCSP — voies bus en site propre (OSM)"


def _config() -> dict:
    """Seuils du mandat — config/transport.yaml, jamais en dur (défauts si fichier absent)."""
    cfg = _cfg.load_yaml_config("transport") or {}
    pole = cfg.get("pole_echange") or {}
    return {"seuil_lignes": int(pole.get("seuil_lignes", 12)),
            "rayon_grappe_m": int(pole.get("rayon_grappe_m", 150)),
            "rayon_concordance_m": int(pole.get("rayon_concordance_m", 300))}


# ────────────────────────────── GTFS (PAN) ──────────────────────────────

def _pan_urls(client: httpx.Client) -> dict[str, tuple[str, str]]:
    """slug → (url GTFS, updated) via la LISTE du PAN (l'endpoint par slug n'existe pas ;
    les URLs static.data.gouv sont horodatées et périment — on résout à chaque ingestion)."""
    r = client.get(PAN_LIST, timeout=120)
    r.raise_for_status()
    out: dict[str, tuple[str, str]] = {}
    for d in r.json():
        slug = d.get("slug")
        if slug not in {s for s, _ in GTFS_RESEAUX}:
            continue
        for res in d.get("resources", []):
            if (res.get("format") or "").upper() == "GTFS" and res.get("url"):
                out[slug] = (res["url"], (d.get("updated") or "")[:10])
                break
    return out


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict]:
    try:
        with zf.open(name) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))
    except KeyError:
        return []


def _routes_par_arret(zf: zipfile.ZipFile) -> dict[str, set[str]]:
    """stop_id → routes distinctes (via trips) — la matière de la dérivation de pôles."""
    trip_route = {t["trip_id"]: t["route_id"] for t in _read_csv(zf, "trips.txt")}
    out: dict[str, set[str]] = defaultdict(set)
    try:
        with zf.open("stop_times.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                rid = trip_route.get(row.get("trip_id") or "")
                if rid:
                    out[row["stop_id"]].add(rid)
    except KeyError:
        pass
    return out


def _shapes(zf: zipfile.ZipFile) -> dict[str, list[tuple[float, float]]]:
    pts: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    try:
        with zf.open("shapes.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                try:
                    pts[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                                                 float(row["shape_pt_lon"]), float(row["shape_pt_lat"])))
                except (KeyError, ValueError):
                    continue
    except KeyError:
        return {}
    return {sid: [(x, y) for _, x, y in sorted(v)] for sid, v in pts.items()}


def ingest_gtfs(session: Session, run_id: int | None, sids: dict) -> dict:
    """Les 7 GTFS → transport_arret + transport_ligne + pole_echange(subtype='gtfs')."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('transport_arret', 'transport_ligne')"))
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'pole_echange' AND subtype = 'gtfs'"))
    sid_gtfs = sids.get(SRC_GTFS)
    bilan = {"reseaux": 0, "arrets": 0, "lignes": 0, "poles_gtfs": 0, "maj": []}
    with httpx.Client(follow_redirects=True) as client:
        urls = _pan_urls(client)
        for slug, reseau in GTFS_RESEAUX:
            if slug not in urls:
                log.warning("transport : GTFS %s introuvable au PAN — réseau sauté (dit, pas masqué)", reseau)
                bilan["maj"].append(f"{reseau}: ABSENT DU PAN")
                continue
            url, updated = urls[slug]
            raw = client.get(url, timeout=300).content
            zf = zipfile.ZipFile(io.BytesIO(raw))
            bilan["maj"].append(f"{reseau}: {updated}")
            routes = {r["route_id"]: r for r in _read_csv(zf, "routes.txt")}
            par_arret = _routes_par_arret(zf)
            # ── arrêts (quais, location_type vide/0) ──
            for s in _read_csv(zf, "stops.txt"):
                if (s.get("location_type") or "0") not in ("", "0"):
                    continue   # stations parentes = groupements de quais, pas des arrêts
                try:
                    lon, lat = float(s["stop_lon"]), float(s["stop_lat"])
                except (KeyError, ValueError):
                    continue
                # M106-B arbitrage : les IDENTIFIANTS de lignes voyagent avec l'arrêt (préfixés
                # réseau) — la dérivation des pôles CUMULE les réseaux d'une grappe spatiale,
                # elle a besoin de l'union DISTINCTE, pas d'un simple compte par arrêt.
                lignes = sorted(f"{reseau}:{rid}" for rid in par_arret.get(s["stop_id"], ()))
                # RETOURS-13 R9 — les NOMS de lignes (route_short_name de routes.txt) voyagent
                # aussi : la bulle d'un arrêt cliqué dit « ligne E3 », jamais un route_id opaque.
                noms = sorted({(routes.get(rid, {}).get("route_short_name")
                                or routes.get(rid, {}).get("route_long_name") or rid)
                               for rid in par_arret.get(s["stop_id"], ())})
                _insert_layer(session, "transport_arret", reseau, s.get("stop_name") or s["stop_id"],
                              {"type": "Point", "coordinates": [lon, lat]}, sid_gtfs, None, run_id,
                              {"reseau": reseau, "stop_id": s["stop_id"], "nb_lignes": len(lignes),
                               "lignes": lignes, "lignes_noms": noms, "gtfs_maj": updated})
                bilan["arrets"] += 1
            # ── tracés par ligne (jusqu'à 4 variantes de shape, MultiLineString) ──
            shapes = _shapes(zf)
            route_shapes: dict[str, Counter] = defaultdict(Counter)
            for t in _read_csv(zf, "trips.txt"):
                if t.get("shape_id"):
                    route_shapes[t["route_id"]][t["shape_id"]] += 1
            for rid, cnt in route_shapes.items():
                lines = [shapes[sid] for sid, _ in cnt.most_common(4) if len(shapes.get(sid, ())) >= 2]
                if not lines:
                    continue
                r = routes.get(rid, {})
                nom = " — ".join(x for x in (r.get("route_short_name"), r.get("route_long_name")) if x) or rid
                _insert_layer(session, "transport_ligne", reseau, nom,
                              {"type": "MultiLineString", "coordinates": lines}, sid_gtfs, None, run_id,
                              {"reseau": reseau, "route_id": rid, "route_type": r.get("route_type"),
                               "gtfs_maj": updated})
                bilan["lignes"] += 1
            bilan["reseaux"] += 1
    # M106-B arbitrage — la dérivation des pôles se fait APRÈS tous les réseaux : correction
    # de DÉFINITION (un pôle d'échange EST un lieu où plusieurs réseaux se croisent) — le
    # comptage par réseau ratait structurellement les vrais nœuds (cas témoin : Savanna).
    bilan["poles_gtfs"] = deriver_poles(session, run_id, sid_gtfs)
    return bilan


def deriver_poles(session: Session, run_id: int | None, sid_gtfs: int | None,
                  seuil: int | None = None, rayon: int | None = None) -> int:
    """Pôles DÉRIVÉS (Estimé) = GRAPPES spatiales d'arrêts (DBSCAN, rayon config = distance de
    correspondance à pied) desservies par ≥ seuil lignes DISTINCTES, TOUS RÉSEAUX CUMULÉS
    (union des identifiants réseau:ligne — jamais une somme qui double-compte). Le seuil reste
    12 (arbitrage : appliqué au bon dénombrement). Le critère complet voyage en attrs jusqu'à
    la légende. `seuil`/`rayon` surchargent la config pour la CALIBRATION seulement."""
    cfg = _config()
    seuil = seuil if seuil is not None else cfg["seuil_lignes"]
    rayon = rayon if rayon is not None else cfg["rayon_grappe_m"]
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'pole_echange' AND subtype = 'gtfs'"))
    n = session.execute(text("""
        WITH quais AS (
          SELECT id, name, geom, attrs,
                 ST_ClusterDBSCAN(ST_Transform(geom, 2975), eps := :rayon, minpoints := 1)
                   OVER () AS grappe
          FROM spatial_layers WHERE kind = 'transport_arret'),
        agg AS (
          SELECT q.grappe,
                 count(DISTINCT l.ligne) AS nb_lignes,
                 count(DISTINCT split_part(l.ligne, ':', 1)) AS nb_reseaux,
                 ST_Centroid(ST_Collect(DISTINCT q.geom)) AS centre
          FROM quais q
          CROSS JOIN LATERAL jsonb_array_elements_text(q.attrs->'lignes') AS l(ligne)
          GROUP BY q.grappe
          HAVING count(DISTINCT l.ligne) >= :seuil),
        nommage AS (
          -- le nom du pôle = celui du quai le plus desservi de la grappe (jamais un code)
          SELECT DISTINCT ON (grappe) grappe, name
          FROM quais ORDER BY grappe, jsonb_array_length(attrs->'lignes') DESC, name)
        INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, ingestion_run_id)
        SELECT 'pole_echange', 'gtfs', initcap(n.name), a.centre,
               jsonb_build_object(
                 'nb_lignes', a.nb_lignes, 'nb_reseaux', a.nb_reseaux,
                 'seuil', CAST(:seuil AS int), 'rayon_grappe_m', CAST(:rayon AS int),
                 'statut', 'Estimé',
                 'critere', 'arrêts groupés à ≤ ' || :rayon || ' m desservis par ≥ ' || :seuil ||
                            ' lignes, tous réseaux cumulés (dérivé GTFS)'),
               :sid, :run
        FROM agg a JOIN nommage n USING (grappe)
        RETURNING 1"""), {"seuil": seuil, "rayon": rayon, "sid": sid_gtfs, "run": run_id}).rowcount
    return int(n)


# ────────────────────────────── OSM (Overpass) ──────────────────────────────

def _overpass(query: str) -> list[dict]:
    """Overpass avec User-Agent explicite (le défaut httpx se fait refuser en 406) et
    repli miroir (l'instance principale rend des 5xx par intermittence — constaté à l'audit)."""
    headers = {"User-Agent": "LABUSE/1.0 (prequalification fonciere La Reunion)"}
    derniere: Exception | None = None
    for url in (OVERPASS, "https://overpass.kumi.systems/api/interpreter"):
        try:
            with httpx.Client(headers=headers) as c:
                r = c.post(url, data={"data": query}, timeout=180)
                r.raise_for_status()
                return r.json().get("elements", [])
        except Exception as e:  # noqa: BLE001 — on tente le miroir, puis on relève
            derniere = e
    raise derniere  # type: ignore[misc]


def ingest_poles_osm(session: Session, run_id: int | None, sids: dict) -> int:
    """Stations / gares routières OSM (Sourcé) → pole_echange subtype='osm'."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'pole_echange' AND subtype = 'osm'"))
    q = ('[out:json][timeout:120];area["ISO3166-2"="FR-RE"]->.a;'
         '(nwr["public_transport"="station"](area.a);nwr["amenity"="bus_station"](area.a););out center;')
    n = 0
    for el in _overpass(q):
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        if lon is None or lat is None:
            continue
        tags = el.get("tags") or {}
        nom = tags.get("name") or "Station (sans nom OSM)"
        _insert_layer(session, "pole_echange", "osm", nom,
                      {"type": "Point", "coordinates": [lon, lat]},
                      sids.get(SRC_OSM_TRANSPORT), None, run_id,
                      {"statut": "Sourcé", "osm_id": f"{el.get('type')}/{el.get('id')}",
                       "operateur": tags.get("operator"), "sans_nom": "name" not in tags})
        n += 1
    return n


def marquer_concordance(session: Session) -> dict:
    """L'arbitrage : « si les deux sources se contredisent, le dire » — chaque pôle porte sa
    concordance (confirme / osm_seul / gtfs_seul) mesurée au rayon config. Géographie 4326
    (ST_DWithin sur geography) : indépendant du backfill geom_2975."""
    r = _config()["rayon_concordance_m"]
    upd = ("UPDATE spatial_layers p SET attrs = p.attrs || jsonb_build_object('concordance', CASE "
           "WHEN EXISTS (SELECT 1 FROM spatial_layers o WHERE o.kind = 'pole_echange' AND o.subtype = :autre "
           "AND ST_DWithin(o.geom::geography, p.geom::geography, :r)) THEN 'confirme' ELSE :seul END, "
           "'rayon_concordance_m', :r) WHERE p.kind = 'pole_echange' AND p.subtype = :moi")
    session.execute(text(upd), {"moi": "osm", "autre": "gtfs", "seul": "osm_seul", "r": r})
    session.execute(text(upd), {"moi": "gtfs", "autre": "osm", "seul": "gtfs_seul", "r": r})
    rows = session.execute(text(
        "SELECT subtype, attrs->>'concordance', count(*) FROM spatial_layers "
        "WHERE kind = 'pole_echange' GROUP BY 1, 2 ORDER BY 1, 2")).all()
    return {f"{s}/{c}": n for s, c, n in rows}


def ingest_telepherique(session: Session, run_id: int | None, sids: dict) -> dict:
    """Le Papang (OSM, EN SERVICE seulement) → telepherique (ligne + stations).
    EXCLUSION EXPLICITE des tracés `proposed`/`construction` (ligne 2 « Zèl La Montagne »,
    2029 : aucun tracé publié — l'OSM proposed est une anticipation de contributeur)."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'telepherique'"))
    q = ('[out:json][timeout:120];area["ISO3166-2"="FR-RE"]->.a;'
         '(way["aerialway"="gondola"](area.a);way["aerialway"="station"](area.a);'
         'node["aerialway"="station"](area.a););out geom;')
    n_lignes = n_stations = 0
    for el in _overpass(q):
        tags = el.get("tags") or {}
        if tags.get("proposed") or tags.get("construction") or tags.get("aerialway") in ("proposed", "construction"):
            continue   # jamais un tracé imaginaire sur un document remis à un banquier
        nom = tags.get("name") or ("Téléphérique Papang" if tags.get("aerialway") == "gondola" else "Station")
        attrs = {"operateur": tags.get("operator"), "osm_id": f"{el.get('type')}/{el.get('id')}",
                 "statut": "en service", "source_licence": "OSM (ODbL)"}
        if tags.get("aerialway") == "gondola":
            coords = [[p["lon"], p["lat"]] for p in el.get("geometry") or []]
            if len(coords) < 2:
                continue
            _insert_layer(session, "telepherique", "ligne", nom,
                          {"type": "LineString", "coordinates": coords},
                          sids.get(SRC_OSM_TRANSPORT), None, run_id, attrs)
            n_lignes += 1
        else:
            if el.get("type") == "node":
                pt = [el["lon"], el["lat"]]
            else:
                geom = el.get("geometry") or []
                if not geom:
                    continue
                pt = [sum(p["lon"] for p in geom) / len(geom), sum(p["lat"] for p in geom) / len(geom)]
            _insert_layer(session, "telepherique", "station", nom,
                          {"type": "Point", "coordinates": pt},
                          sids.get(SRC_OSM_TRANSPORT), None, run_id, attrs)
            n_stations += 1
    # une STATION n'existe que le long d'une LIGNE EN SERVICE — mesuré : OSM porte aussi des
    # vestiges (« Ancien téléphérique forestier ») tagués aerialway=station ; on les écarte
    # par principe (≤ 500 m d'une ligne ingérée), on ne les sert jamais comme transport.
    orphelines = session.execute(text(
        "DELETE FROM spatial_layers s WHERE s.kind = 'telepherique' AND s.subtype = 'station' "
        "AND NOT EXISTS (SELECT 1 FROM spatial_layers l WHERE l.kind = 'telepherique' "
        "AND l.subtype = 'ligne' AND ST_DWithin(l.geom::geography, s.geom::geography, 500)) "
        "RETURNING s.name")).all()
    return {"lignes": n_lignes, "stations": n_stations - len(orphelines),
            "stations_ecartees": [r[0] for r in orphelines]}


# ────────────────────────────── TCSP (RETOURS-13 R5) ──────────────────────────────

def ingest_tcsp(session: Session, run_id: int | None, sids: dict) -> dict:
    """RETOURS-13 R5 — la VRAIE couche TCSP « Transport en commun en site propre ».

    EN SERVICE (le seul état avec une géométrie publique traçable) : les voies bus d'OSM sur le
    974, en DEUX natures dites —
    · subtype='site_propre' : `highway=busway` (chaussée dédiée aux bus — un site propre au sens
      plein : boulevard sud de Saint-Denis, tronçons CIVIS livrés à Saint-Pierre…) ;
    · subtype='couloir'     : `busway=lane/opposite_lane`, `lanes:psv`, `psv=designated` (couloir
      réservé sur chaussée partagée — ce N'EST PAS un site propre au sens de l'art. L151-36 :
      il ne déclenche JAMAIS le drapeau stationnement, la distinction voyage en attrs).
    EN TRAVAUX (Rico Carpaye/TCO, ESTI+/CIREST) et EN PROJET (Réunion Express, débat public
    19/08→26/11/2026) : AUCUNE géométrie publique (recherche URL par URL au compte-rendu) —
    jamais un tracé numérisé à la main ; ces états vivent dans le « i » de la couche et à la
    sentinelle (Réunion Express ré-ouvert après le débat).

    Puis dérivation des STATIONS desservies : kind='tcsp_station' = grappes d'arrêts GTFS à
    ≤ 60 m d'un tronçon en site propre (le drapeau fiche L151-36 se mesure À LA STATION,
    à vol d'oiseau — Conseil d'État 2022 — jamais au tracé)."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('tcsp_troncon', 'tcsp_station')"))
    q = ('[out:json][timeout:120];area["ISO3166-2"="FR-RE"]->.a;('
         'way["highway"="busway"](area.a);'
         'way["busway"~"lane|opposite_lane"](area.a);'
         'way["lanes:psv"](area.a);'
         'way["psv"="designated"]["highway"](area.a););out tags geom;')
    n_sp = n_couloir = 0
    sid = sids.get(SRC_OSM_TCSP)
    for el in _overpass(q):
        tags = el.get("tags") or {}
        if tags.get("proposed") or tags.get("construction") or tags.get("highway") in ("proposed", "construction"):
            continue   # jamais un tracé anticipé servi comme en service
        coords = [[p["lon"], p["lat"]] for p in el.get("geometry") or []]
        if len(coords) < 2:
            continue
        site_propre = tags.get("highway") == "busway"
        nom = tags.get("name") or ("Voie bus en site propre" if site_propre else "Couloir bus")
        _insert_layer(session, "tcsp_troncon", "site_propre" if site_propre else "couloir", nom,
                      {"type": "LineString", "coordinates": coords}, sid, None, run_id,
                      {"etat": "en_service", "osm_id": f"way/{el.get('id')}",
                       "source_licence": "OSM (ODbL)",
                       "nature": ("chaussée dédiée aux bus (site propre)" if site_propre
                                  else "couloir réservé sur chaussée partagée — pas un site propre L151-36")})
        n_sp += 1 if site_propre else 0
        n_couloir += 0 if site_propre else 1
    # STATIONS TCSP (Dérivé) : arrêts GTFS à ≤ 60 m d'un tronçon en SITE PROPRE, groupés en
    # grappes (les quais aller/retour = une station), nommés par le quai le plus desservi.
    n_st = session.execute(text("""
        WITH quais AS (
          SELECT a.id, a.name, a.geom, a.attrs,
                 ST_ClusterDBSCAN(ST_Transform(a.geom, 2975), eps := 60, minpoints := 1) OVER () AS grappe
          FROM spatial_layers a
          WHERE a.kind = 'transport_arret' AND EXISTS (
            SELECT 1 FROM spatial_layers t WHERE t.kind = 'tcsp_troncon'
            AND t.subtype = 'site_propre'
            AND ST_DWithin(t.geom::geography, a.geom::geography, 60))),
        agg AS (
          SELECT grappe, ST_Centroid(ST_Collect(DISTINCT geom)) AS centre,
                 count(*) AS nb_quais
          FROM quais GROUP BY grappe),
        nommage AS (
          SELECT DISTINCT ON (grappe) grappe, name,
                 attrs->'lignes_noms' AS lignes_noms, attrs->>'reseau' AS reseau
          FROM quais ORDER BY grappe, jsonb_array_length(COALESCE(attrs->'lignes', '[]'::jsonb)) DESC, name)
        INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, ingestion_run_id)
        SELECT 'tcsp_station', 'en_service', initcap(n.name), a.centre,
               jsonb_build_object('statut', 'Dérivé', 'nb_quais', a.nb_quais,
                                  'reseau', n.reseau, 'lignes_noms', COALESCE(n.lignes_noms, '[]'::jsonb),
                                  'critere', 'arrêt GTFS à ≤ 60 m d''une voie bus en site propre (OSM)'),
               :sid, :run
        FROM agg a JOIN nommage n USING (grappe)
        RETURNING 1"""), {"sid": sid, "run": run_id}).rowcount
    # RETOURS-14 S8 — ZONE « STATIONNEMENT ALLÉGÉ » matérialisée (kind='tcsp_zone') :
    # (a) subtype='rayon' = union des cercles de 800 m autour des stations (c'est un RAYON à vol
    # d'oiseau depuis la station — donc une pastille de 1,6 km de large) ; (b) subtype='parcelles'
    # = union des parcelles réellement couvertes (leur teinte exacte à l'écran). Les COULOIRS bus
    # ne génèrent PAS de zone (pas un site propre au sens de l'art. L151-36).
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'tcsp_zone'"))
    session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id) "
        "SELECT 'tcsp_zone', 'rayon', 'Zone stationnement allégé (800 m des stations TCSP)', "
        "ST_Multi(ST_SimplifyPreserveTopology(ST_Union(ST_Buffer(geom::geography, 800)::geometry), 0.0001)), "
        "jsonb_build_object('statut','Dérivé','rayon_m',800,'critere',"
        "'rayon de 800 m à vol d''oiseau autour de chaque station en service (art. L151-36)'), :sid "
        "FROM spatial_layers WHERE kind = 'tcsp_station'"), {"sid": sid})
    session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id) "
        "SELECT 'tcsp_zone', 'parcelles', 'Parcelles à moins de 800 m d''une station TCSP', "
        "ST_Multi(ST_SimplifyPreserveTopology(ST_Union(p.geom), 0.0001)), "
        "jsonb_build_object('statut','Dérivé','n_parcelles', count(*)), :sid "
        "FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers s "
        "WHERE s.kind='tcsp_station' AND ST_DWithin(s.geom_2975, p.geom_2975, 800))"), {"sid": sid})
    session.execute(text(
        "UPDATE spatial_layers SET geom_simple = ST_SimplifyPreserveTopology(geom, 0.0002) "
        "WHERE kind = 'tcsp_zone'"))
    session.execute(text("UPDATE data_sources SET source_millesime = :m, last_sync_at = now() "
                         "WHERE name = :n"),
                    {"m": "extraction Overpass (OSM, ODbL) — voies bus 974", "n": SRC_OSM_TCSP})
    return {"site_propre": n_sp, "couloirs": n_couloir, "stations": int(n_st)}


# ────────────────────────────── BD TOPO — lignes HT ──────────────────────────────

def ingest_lignes_ht(session: Session, run_id: int | None, sids: dict) -> int:
    """BD TOPO `ligne_electrique` (Licence Ouverte) → kind='ligne_ht', tension en attrs.
    EDF SEI a RETIRÉ ses couches le 24/12/2025 (sécurité publique) — on ne les contourne pas ;
    la BD TOPO est la source officielle restante (aérien seul, la BD TOPO ne porte pas le
    souterrain). La servitude I4 n'existe pas en vectoriel (0 objet GPU 974) : on sert la
    distance, jamais un périmètre de servitude."""
    from ..connectors.wfs import WfsConnector
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'ligne_ht'"))
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "BDTOPO_V3:ligne_electrique",
                         bbox=ILE_BBOX, max_features=1000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        tension = p.get("voltage") or p.get("tension") or "tension non renseignée"
        _insert_layer(session, "ligne_ht", str(tension), f"Ligne électrique — {tension}",
                      f["geometry"], sids.get(SRC_BDTOPO), None, run_id,
                      {"tension": tension, "etat": p.get("etat_de_l_objet"),
                       "cleabs": p.get("cleabs")})
        n += 1
    return n


# ────────────────────────────── BD TOPO — axes structurants (M106-B P3) ──────────────────────────────

def ingest_axes(session: Session, run_id: int | None, sids: dict) -> dict:
    """Axes structurants = la HIÉRARCHIE DE LA BD TOPO elle-même, jamais une invention :
    `importance` IN ('1','2') (réseau routier majeur IGN — mesuré : 3 481 tronçons sur l'île,
    N1/N2/N6/D400…, dont la route des Tamarins). Nom (cpx_numero/toponyme) et nature voyagent
    en attrs — la fiche sert « distance à l'axe le plus proche, nom, nature ».

    PIÈGE mesuré : le cql_filter Géoplateforme veut la BBOX en ordre LAT/LON (axis order du
    CRS par défaut) — l'ordre lon/lat renvoie silencieusement 0."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'axe_structurant'"))
    n, start = 0, 0
    with httpx.Client() as c:
        while True:
            r = c.get("https://data.geopf.fr/wfs/ows", params={
                "service": "WFS", "version": "2.0.0", "request": "GetFeature",
                "typenames": "BDTOPO_V3:troncon_de_route", "outputFormat": "application/json",
                "count": 5000, "startIndex": start, "sortBy": "cleabs",
                "cql_filter": "importance IN ('1','2') AND BBOX(geometrie,-21.42,55.20,-20.85,55.90)"},
                timeout=300)
            r.raise_for_status()
            feats = r.json().get("features", []) or []
            for f in feats:
                if not f.get("geometry"):
                    continue
                p = f.get("properties") or {}
                nom = p.get("cpx_numero") or p.get("cpx_toponyme_route_nommee") or (p.get("nature") or "axe")
                _insert_layer(session, "axe_structurant", str(p.get("importance") or ""), str(nom),
                              f["geometry"], sids.get(SRC_BDTOPO), None, run_id,
                              {"importance": p.get("importance"), "nature": p.get("nature"),
                               "numero": p.get("cpx_numero"),
                               "toponyme": p.get("cpx_toponyme_route_nommee"),
                               "nb_voies": p.get("nombre_de_voies")})
                n += 1
            if len(feats) < 5000:
                break
            start += 5000
    return {"troncons": n}


# ────────────────────────────── orchestration ──────────────────────────────

def run_m106(session: Session, log_fn=print) -> dict:
    """Ingestion versionnée des couches M106 (un IngestionRun), millésimes amont posés."""
    from .. import models
    run = models.IngestionRun(commune=None, status="m106_couches")
    session.add(run)
    session.flush()
    sids = _source_ids(session)
    out: dict = {"run_id": run.id}
    out["gtfs"] = ingest_gtfs(session, run.id, sids)
    out["poles_osm"] = ingest_poles_osm(session, run.id, sids)
    out["concordance"] = marquer_concordance(session)
    out["telepherique"] = ingest_telepherique(session, run.id, sids)
    out["lignes_ht"] = ingest_lignes_ht(session, run.id, sids)
    out["axes"] = ingest_axes(session, run.id, sids)
    # millésimes AMONT dans data_sources (fraîcheur = amont, jamais la date d'ingestion)
    maj = [m.split(": ")[1] for m in out["gtfs"]["maj"] if "ABSENT" not in m]
    if maj:
        session.execute(text("UPDATE data_sources SET source_millesime = :m WHERE name = :n"),
                        {"m": f"7 jeux PAN, màj {min(maj)} → {max(maj)}"[:64], "n": SRC_GTFS})
    session.execute(text("UPDATE data_sources SET source_millesime = :m WHERE name = :n"),
                    {"m": "extraction Overpass (base OSM vivante, ODbL)", "n": SRC_OSM_TRANSPORT})
    run.status = "ok"
    session.execute(text("UPDATE ingestion_runs SET finished_at = now() WHERE id = :i"), {"i": run.id})
    session.commit()
    log_fn(f"✓ M106 couches : {json.dumps(out, ensure_ascii=False, default=str)}")
    return out
