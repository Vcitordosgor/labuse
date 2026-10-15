"""VERITE-TERRAIN-2 · volet B — TEMPS DE TRAJET & DISTANCES face à un routeur de référence.

Le volet A (VERITE-TERRAIN-1 / PLU) compare les RÈGLES. Ici on compare ce que LABUSE sert comme
TEMPS de trajet vers les équipements/établissements d'une zone — le « temps_min » (bande d'isochrone)
de `labuse.zone` — à un calcul d'itinéraire point-à-point INDÉPENDANT.

CE QUE LABUSE SERT (étudié dans `src/labuse/zone.py`) :
  · `_BANDES = (2,4,6,8,10,15)` minutes. `_bande_min(lon,lat,bandes)` = la PLUS PETITE bande
    d'isochrone contenant le POI → c'est le « temps_min » servi sur la fiche/étude de zone.
    C'est donc une BORNE HAUTE QUANTIFIÉE : un POI réellement à 1 min est servi « 2 min », un POI à
    4 min 30 est servi « 6 min ». LABUSE ne sert JAMAIS une distance en mètres pour ces POI, toujours
    une bande de temps (vérifié : `equipements_proches`, `concurrents_zone`, `entreprises_zone` portent
    `temps_min` ; `generateurs_flux` sert un COMPTE d'arrêts/pôles, sans aucun temps ni distance).
  · mode par défaut de l'étude de zone = celui passé par l'appelant ; le service `isochrone()` accepte
    'voiture' (profil car Valhalla) ou 'pied' (pedestrian). On traite la VOITURE (le mode avec une
    référence gratuite fiable) et on documente le piéton.

LECTURE SEULE STRICTE :
  · connexion DB en `read_only = True` (une écriture accidentelle LÈVE, elle ne passe pas) ;
  · on N'appelle PAS `zone.isochrone()` (qui INSÈRE dans `zone_isochrone_cache`) : on appelle
    directement `connectors.isochrone_ign.fetch_isochrone(...)` et on met le résultat en cache NOUS-MÊME
    sur disque, puis on REPRODUIT `_bande_min` avec PostGIS (ST_Contains) — sans écrire en base ;
  · aucune écriture VPS, aucune modification du code existant.

ROUTEUR DE RÉFÉRENCE :
  · PRIMAIRE = service d'itinéraire IGN (`data.geopf.fr/navigation/itineraire`, resource bdtopo-osrm,
    profil car). MÊME socle de données (BD TOPO IGN) que l'isochrone Valhalla → la divergence mesurée
    est principalement la QUANTIFICATION DE BANDE, pas un désaccord de réseau routier.
  · SECONDAIRE = OSRM démo public (`router.project-osrm.org`, driving, fond OSM) — contrôle croisé.
  · Piéton : pas de référence gratuite fiable retenue → traité honnêtement comme NON COMPARABLE.

    PYTHONPATH=src python -m labuse.verite_terrain_trajets echantillon [--n 300]
    PYTHONPATH=src python -m labuse.verite_terrain_trajets comparer [--n 0] [--ref ign|osrm]
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx
import psycopg

from .connectors.isochrone_ign import fetch_isochrone
from .verite_terrain import GRAINE, _dsn, _seed_frac  # réutilise graine + DSN read-only + setseed

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2"
CACHE = Path(os.environ.get("VT2_CACHE", SORTIE / "cache" / "trajets"))
ECHANTILLON_CSV = SORTIE / "echantillon_trajets.csv"
TRAJETS_CSV = SORTIE / "TRAJETS.csv"

# ───────────────────────── verdicts (mêmes libellés que le volet A)
CONFORME = "CONFORME"
FAUX = "LABUSE FAUX"
RECENTE = "SOURCE PLUS RÉCENTE"
NC = "NON COMPARABLE"

# ───────────────────────── LABUSE : bandes servies (COPIE FIDÈLE de zone._BANDES)
_BANDES = (2, 4, 6, 8, 10, 15)
_MINUTES_ETUDE = 15          # on calcule les isochrones jusqu'à la plus grande bande servie.
_MODE = "voiture"           # mode traité (voiture) — le piéton n'a pas de référence fiable.

# ───────────────────────── BPE : 5 domaines des « plus proches » (COPIE de zone._DOMAINES_EQUIP)
_DOMAINES_EQUIP = [
    ("C", "Enseignement"), ("B", "Commerces"), ("D", "Santé et action sociale"),
    ("A", "Services aux particuliers"), ("F", "Sports, loisirs et culture"),
]

# ───────────────────────── stratification : 4 strates ~75 chacune (voir TRAJETS-NOTES.md)
_STRATES = ("littoral", "mi-pentes", "Hauts", "cirques")
_PAR_STRATE = 75
# Communes « cirques » (accès/fond de cirque) — INSEE. Mafate est réparti sur La Possession/Saint-Paul
# mais sans isochrone routière (pas de route) → on retient les trois communes-cirques routières.
_CIRQUES = {"97424": "Cilaos", "97421": "Salazie", "97403": "Entre-Deux"}
# Communes « des Hauts » (plaines d'altitude) — complètent les cirques pour le stratum Hauts.
_HAUTS_COMMUNES = {"97406": "La Plaine-des-Palmistes", "97422": "Le Tampon"}
_SEUIL_LITTORAL_M = 1500.0   # parcelle à moins de 1,5 km du trait de côte = littoral
_SEUIL_HAUTS_M = 5000.0      # parcelle à plus de 5 km du trait de côte = Hauts (hors cirques)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CONNEXION READ-ONLY
# ═════════════════════════════════════════════════════════════════════════════════════════

def _connect():
    conn = psycopg.connect(_dsn())
    conn.read_only = True        # garde-fou : toute écriture LÈVE plutôt que de passer
    conn.autocommit = True
    return conn


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CACHE RÉSEAU DISQUE (isochrones IGN + itinéraires de référence) — jamais en base
# ═════════════════════════════════════════════════════════════════════════════════════════

def _cache_path(sous_dossier: str, cle: str) -> Path:
    h = hashlib.sha1(cle.encode()).hexdigest()
    return CACHE / sous_dossier / f"{h}.json"


def _cache_lire(sous_dossier: str, cle: str):
    p = _cache_path(sous_dossier, cle)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001 — cache corrompu → on refait
            return None
    return None


def _cache_ecrire(sous_dossier: str, cle: str, payload) -> None:
    p = _cache_path(sous_dossier, cle)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False))


_PAUSE_S = float(os.environ.get("VT2_PAUSE", "0.7"))   # appels séquentiels espacés (Mac 8 Go)


def isochrone_disque(client: httpx.Client, lon: float, lat: float, minutes: int,
                     mode: str = _MODE) -> dict | None:
    """Isochrone IGN en CACHE DISQUE (clé = mode|minutes|lon|lat arrondis, comme zone._cle). Ne touche
    JAMAIS la base. Retourne le dict geometry GeoJSON, ou None si le service est indisponible (dégradé
    honnête — on ne substitue jamais un cercle)."""
    cle = f"{mode}|{minutes}|{lon:.5f}|{lat:.5f}"
    hit = _cache_lire("isochrones", cle)
    if hit is not None:
        return hit.get("geom")
    try:
        geom = fetch_isochrone(lon, lat, minutes, mode, client=client)
    except Exception as exc:  # noqa: BLE001 — honnête : on NE met PAS en cache un échec
        print(f"  ! isochrone IGN indisponible ({type(exc).__name__}) pour {cle}", file=sys.stderr)
        return None
    time.sleep(_PAUSE_S)
    _cache_ecrire("isochrones", cle, {"cle": cle, "geom": geom})
    return geom


def bandes_isochrones_disque(client: httpx.Client, lon: float, lat: float,
                             mode: str = _MODE) -> dict[int, dict]:
    """Toutes les bandes servies (2..15) en cache disque. Reproduit zone.bandes_isochrones sans base."""
    out: dict[int, dict] = {}
    for b in _BANDES:
        g = isochrone_disque(client, lon, lat, b, mode)
        if g is not None:
            out[b] = g
    return out


def ref_itineraire_ign(client: httpx.Client, lon0: float, lat0: float,
                       lon1: float, lat1: float) -> float | None:
    """TEMPS DE RÉFÉRENCE (minutes) point-à-point en VOITURE via le service d'itinéraire IGN
    (data.geopf.fr/navigation/itineraire, resource bdtopo-osrm). Cache disque. None si indisponible."""
    cle = f"ign|{lon0:.5f},{lat0:.5f}|{lon1:.5f},{lat1:.5f}"
    hit = _cache_lire("ref_ign", cle)
    if hit is not None:
        return hit.get("minutes")
    try:
        r = client.get("https://data.geopf.fr/navigation/itineraire", params={
            "resource": "bdtopo-osrm", "start": f"{lon0:.6f},{lat0:.6f}",
            "end": f"{lon1:.6f},{lat1:.6f}", "profile": "car", "optimization": "fastest",
            "geometryFormat": "geojson", "getSteps": "false"}, timeout=30.0)
        r.raise_for_status()
        dur = r.json().get("duration")
        minutes = float(dur) / 60.0 if dur is not None else None
    except Exception as exc:  # noqa: BLE001
        print(f"  ! itinéraire IGN indisponible ({type(exc).__name__}) pour {cle}", file=sys.stderr)
        return None
    time.sleep(_PAUSE_S)
    _cache_ecrire("ref_ign", cle, {"cle": cle, "minutes": minutes})
    return minutes


def ref_itineraire_osrm(client: httpx.Client, lon0: float, lat0: float,
                        lon1: float, lat1: float) -> float | None:
    """TEMPS DE RÉFÉRENCE secondaire (minutes) via OSRM démo public (fond OSM). Cache disque."""
    cle = f"osrm|{lon0:.5f},{lat0:.5f}|{lon1:.5f},{lat1:.5f}"
    hit = _cache_lire("ref_osrm", cle)
    if hit is not None:
        return hit.get("minutes")
    try:
        r = client.get(
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon0:.6f},{lat0:.6f};{lon1:.6f},{lat1:.6f}",
            params={"overview": "false"}, timeout=30.0)
        r.raise_for_status()
        d = r.json()
        dur = (d.get("routes") or [{}])[0].get("duration") if d.get("code") == "Ok" else None
        minutes = float(dur) / 60.0 if dur is not None else None
    except Exception as exc:  # noqa: BLE001
        print(f"  ! OSRM indisponible ({type(exc).__name__}) pour {cle}", file=sys.stderr)
        return None
    time.sleep(_PAUSE_S)
    _cache_ecrire("ref_osrm", cle, {"cle": cle, "minutes": minutes})
    return minutes


# ═════════════════════════════════════════════════════════════════════════════════════════
#  LOGIQUE DE BANDE (REPRODUIT zone._bande_min, mais sur isochrones en cache disque, 0 écriture)
# ═════════════════════════════════════════════════════════════════════════════════════════

def bande_min_disque(conn, lon: float, lat: float, bandes: dict[int, dict]) -> int | None:
    """COPIE FIDÈLE de zone._bande_min : plus petite bande (minutes) dont l'isochrone CONTIENT le POI.
    = le temps_min que LABUSE sert. None si le POI est hors de toutes les bandes disponibles."""
    with conn.cursor() as cur:
        for mn in sorted(bandes):
            cur.execute(
                "SELECT ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), "
                "ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                (json.dumps(bandes[mn]), lon, lat))
            if cur.fetchone()[0]:
                return mn
    return None


# ═════════════════════════════════════════════════════════════════════════════════════════
#  ÉCHANTILLON STRATIFIÉ — 300 parcelles (littoral / mi-pentes / Hauts / cirques)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# RÈGLE DE STRATIFICATION (déterministe, graine GRAINE de verite_terrain) :
#   · cirques   = parcelle dans Cilaos / Salazie / Entre-Deux (communes d'accès de cirque) ;
#   · Hauts     = hors cirques, à PLUS de 5 km du trait de côte OU dans La Plaine-des-Palmistes /
#                 Le Tampon (plaines d'altitude) ;
#   · littoral  = hors cirques/Hauts, à MOINS de 1,5 km du trait de côte ;
#   · mi-pentes = tout le reste (entre côte et Hauts).
# Proxy ALTITUDE : la distance au trait de côte (couche spatial_layers kind='trait_de_cote', servie et
# complète) — le MNT rgealti en base ne couvre que 2 dalles de test, pas l'île → non utilisable
# comme altitude par parcelle. La distance à la côte est le proxy robuste retenu (documenté dans NOTES).
# Dans chaque strate on tire au hasard reproductible (setseed(_seed_frac(strate)) + ORDER BY random()).

def _tirer_strate(conn, strate: str, k: int) -> list[dict]:
    """k parcelles d'une strate, tirage reproductible. Chaque tirage sur-tire puis filtre côte en SQL."""
    cirques = list(_CIRQUES)
    hauts_c = list(_HAUTS_COMMUNES)
    # on veut le centroïde (lon/lat 4326) pour les appels réseau, + distance côte en mètres (KNN borné).
    dist_sql = (
        "(SELECT min(ST_Distance(p.geom_2975, l.geom_2975)) FROM spatial_layers l "
        " WHERE l.kind='trait_de_cote' AND ST_DWithin(p.geom_2975, l.geom_2975, 30000))")
    base = (
        f"SELECT p.idu, p.commune, substring(p.idu,1,5) AS insee, "
        f"       ST_X(ST_PointOnSurface(p.geom)) AS lon, ST_Y(ST_PointOnSurface(p.geom)) AS lat, "
        f"       {dist_sql} AS dist_cote_m "
        f"FROM parcels p WHERE p.cadastre_disparue_le IS NULL ")
    if strate == "cirques":
        where = "AND substring(p.idu,1,5) = ANY(%(cirques)s)"
        having = ""
    elif strate == "Hauts":
        where = "AND NOT (substring(p.idu,1,5) = ANY(%(cirques)s))"
        having = f" AND (insee = ANY(%(hauts_c)s) OR dist_cote_m > {_SEUIL_HAUTS_M} OR dist_cote_m IS NULL)"
    elif strate == "littoral":
        where = "AND NOT (substring(p.idu,1,5) = ANY(%(cirques)s)) AND NOT (substring(p.idu,1,5) = ANY(%(hauts_c)s))"
        having = f" AND dist_cote_m <= {_SEUIL_LITTORAL_M}"
    else:  # mi-pentes
        where = "AND NOT (substring(p.idu,1,5) = ANY(%(cirques)s)) AND NOT (substring(p.idu,1,5) = ANY(%(hauts_c)s))"
        having = (f" AND dist_cote_m > {_SEUIL_LITTORAL_M} AND dist_cote_m <= {_SEUIL_HAUTS_M}")
    # ORDER BY random() APRÈS setseed → reproductible ; sur-tire (×4) pour absorber le filtre côte.
    sql = (f"SELECT * FROM ({base} {where} ORDER BY random() LIMIT %(sur)s) q "
           f"WHERE true {having} LIMIT %(k)s")
    out: list[dict] = []
    with conn.cursor() as cur:
        cur.execute("SELECT setseed(%s)", (_seed_frac(f"trajets:{strate}"),))
        cur.execute(sql, {"cirques": cirques, "hauts_c": hauts_c, "sur": k * 8, "k": k})
        for idu, commune, insee, lon, lat, dist in cur.fetchall():
            out.append({"idu": idu, "commune": commune, "insee": insee,
                        "lon": float(lon), "lat": float(lat),
                        "dist_cote_m": None if dist is None else round(float(dist)),
                        "strate": strate})
    return out


def tirer_echantillon(conn, par_strate: int = _PAR_STRATE) -> tuple[list[dict], list[str]]:
    choisis: dict[str, dict] = {}
    notes: list[str] = []
    for strate in _STRATES:
        rows = _tirer_strate(conn, strate, par_strate)
        pris = 0
        for r in rows:
            if r["idu"] not in choisis:
                choisis[r["idu"]] = r
                pris += 1
        if pris < par_strate:
            notes.append(f"{strate} : {pris}/{par_strate} parcelles (vivier filtré insuffisant)")
    return sorted(choisis.values(), key=lambda d: (d["strate"], d["idu"])), notes


# ═════════════════════════════════════════════════════════════════════════════════════════
#  POI LES PLUS PROCHES PAR DOMAINE BPE (REPRODUIT equipements_proches, borné à 1/domaine)
# ═════════════════════════════════════════════════════════════════════════════════════════

def pois_parcelle(conn, lon0: float, lat0: float, bandes: dict[int, dict]) -> list[dict]:
    """Pour chaque domaine BPE, l'équipement le plus proche DANS la zone 15 min (même filtre que
    equipements_proches : spatial_layers kind='amenite_bpe', subtype=domaine, dans l'isochrone max)."""
    if not bandes:
        return []
    zone = bandes[max(bandes)]           # isochrone de la plus grande bande servie = la « zone »
    out: list[dict] = []
    with conn.cursor() as cur:
        for dom, label in _DOMAINES_EQUIP:
            cur.execute(
                "SELECT name, ST_X(geom), ST_Y(geom) FROM spatial_layers "
                "WHERE kind='amenite_bpe' AND subtype=%s "
                "  AND ST_Contains(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),2975), "
                "                  ST_Transform(geom,2975)) "
                "ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s,%s),4326) LIMIT 1",
                (dom, json.dumps(zone), lon0, lat0))
            r = cur.fetchone()
            if r:
                out.append({"domaine": dom, "domaine_label": label, "nom": r[0],
                            "lon": float(r[1]), "lat": float(r[2])})
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  COMPARAISON & VERDICT (conscient de la bande)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# Le temps servi est la PLUS PETITE BANDE CONTENANT le POI : l'intervalle « vrai » du POI est donc
# ]bande_inférieure ; bande_servie]. Un POI à 1 min servi « 2 min » n'est PAS une erreur.
# RÈGLE DE TOLÉRANCE (band-aware) :
#   · soit la référence tombe DANS l'intervalle de la bande [borne_inf ; bande_servie]  → CONFORME ;
#   · soit elle est au plus à ±1 CRAN de bande de cet intervalle, OU à ±20 % de la borne de bande
#     servie (marge pour le bruit du moteur de routage)                                 → CONFORME ;
#   · plus loin                                                                          → LABUSE FAUX.
# La borne inférieure de la bande servie = la bande servie précédente (0 pour la bande 2).

def _borne_inf(bande: int) -> int:
    idx = _BANDES.index(bande)
    return 0 if idx == 0 else _BANDES[idx - 1]


def _cran_voisin_haut(bande: int) -> int:
    idx = _BANDES.index(bande)
    return _BANDES[idx] if idx == len(_BANDES) - 1 else _BANDES[idx + 1]


def verdict_trajet(labuse_bande: int | None, ref_min: float | None) -> tuple[str, str, bool]:
    """Rend (verdict, note, dans_bande). labuse_bande None = POI hors isochrone max (NON COMPARABLE)."""
    if labuse_bande is None:
        return NC, "POI hors de l'isochrone 15 min servie (aucune bande ne le contient)", False
    if ref_min is None:
        return NC, "temps de référence indisponible (service injoignable)", False
    inf = _borne_inf(labuse_bande)
    dans_bande = inf < ref_min <= labuse_bande
    if dans_bande:
        return CONFORME, f"référence {ref_min:.1f} min dans l'intervalle de bande ]{inf};{labuse_bande}]", True
    # marge : ±1 cran de bande au-dessus/dessous, OU ±20 % de la borne de bande servie
    cran_haut = _cran_voisin_haut(labuse_bande)
    marge = 0.20 * labuse_bande
    proche = (ref_min <= cran_haut + marge) and (ref_min >= max(0.0, inf - marge))
    if proche:
        return (CONFORME,
                f"référence {ref_min:.1f} min hors ]{inf};{labuse_bande}] mais à ±1 cran/±20 % "
                f"(bande servie {labuse_bande})", False)
    sens = "sous-estime" if ref_min > labuse_bande else "sur-estime"
    return (FAUX,
            f"LABUSE sert {labuse_bande} min, référence {ref_min:.1f} min → LABUSE {sens} "
            f"(hors ]{inf};{labuse_bande}] et hors marge ±1 cran/±20 %)", False)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════════════════════════════════

def _ecrire_echantillon(ech: list[dict], notes: list[str]) -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(ECHANTILLON_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "commune", "insee", "strate", "lon", "lat", "dist_cote_m"])
        for d in ech:
            w.writerow([d["idu"], d["commune"], d["insee"], d["strate"],
                        f"{d['lon']:.6f}", f"{d['lat']:.6f}", d["dist_cote_m"]])
    from collections import Counter
    par = Counter(d["strate"] for d in ech)
    print(f"échantillon : {len(ech)} parcelles → {ECHANTILLON_CSV}")
    for s in _STRATES:
        print(f"  {s}: {par.get(s,0)}")
    for n in notes:
        print("  (note)", n)


def cmd_echantillon(par_strate: int) -> None:
    conn = _connect()
    try:
        ech, notes = tirer_echantillon(conn, par_strate)
    finally:
        conn.close()
    _ecrire_echantillon(ech, notes)


def _charger_echantillon() -> list[dict]:
    if not ECHANTILLON_CSV.exists():
        raise SystemExit("échantillon absent — lancer d'abord : "
                         "python -m labuse.verite_terrain_trajets echantillon")
    out = []
    with open(ECHANTILLON_CSV, newline="") as f:
        for r in csv.DictReader(f):
            out.append({"idu": r["idu"], "commune": r["commune"], "insee": r["insee"],
                        "strate": r["strate"], "lon": float(r["lon"]), "lat": float(r["lat"]),
                        "dist_cote_m": r["dist_cote_m"]})
    return out


#: fichier d'avancement APPEND-ONLY (une parcelle traitée y est écrite sitôt finie). Permet la REPRISE :
#: un run tué (ex. plafond de temps de l'orchestrateur) relancé repart des parcelles manquantes. Le CSV
#: final TRAJETS.csv est reconstruit à partir de ce journal à la fin (trié par strate puis parcelle).
PARTIEL_CSV = SORTIE / "_trajets_partiel.csv"


def _parcelles_faites() -> set[str]:
    """Parcelles déjà écrites dans le journal partiel (reprise)."""
    if not PARTIEL_CSV.exists():
        return set()
    with open(PARTIEL_CSV, newline="") as f:
        return {r["parcelle"] for r in csv.DictReader(f)}


def cmd_comparer(n: int, ref: str) -> None:
    ech = _charger_echantillon()
    if n:
        ech = ech[:n]
    deja = _parcelles_faites()
    reste = [p for p in ech if p["idu"] not in deja]
    conn = _connect()
    client = httpx.Client(headers={"User-Agent": "labuse/verite-terrain-2"})
    ref_fn = ref_itineraire_osrm if ref == "osrm" else ref_itineraire_ign
    ref_nom = "OSRM démo (OSM, driving)" if ref == "osrm" else "IGN itinéraire (bdtopo-osrm, car)"
    SORTIE.mkdir(parents=True, exist_ok=True)
    nouveau = not PARTIEL_CSV.exists()
    jour = open(PARTIEL_CSV, "a", newline="")
    w = csv.DictWriter(jour, fieldnames=_COLS)
    if nouveau:
        w.writeheader(); jour.flush()
    print(f"reprise : {len(deja)} parcelles déjà faites · {len(reste)} à faire (sur {len(ech)})")
    try:
        for i, p in enumerate(reste, 1):
            lon0, lat0 = p["lon"], p["lat"]
            bandes = bandes_isochrones_disque(client, lon0, lat0)
            lignes_p: list[dict] = []
            if not bandes:
                lignes_p.append(_ligne(p, _MODE, "", "", lon0, lat0, None, None, ref_nom,
                                       NC, "isochrone IGN indisponible — aucune bande", False))
                tag = "isochrone indisponible"
            else:
                pois = pois_parcelle(conn, lon0, lat0, bandes)
                if not pois:
                    lignes_p.append(_ligne(p, _MODE, "", "", lon0, lat0, None, None, ref_nom,
                                           NC, "aucun équipement BPE dans l'isochrone 15 min", False))
                    tag = "0 POI"
                else:
                    for poi in pois:
                        bande = bande_min_disque(conn, poi["lon"], poi["lat"], bandes)
                        ref_min = ref_fn(client, lon0, lat0, poi["lon"], poi["lat"])
                        v, note, dans = verdict_trajet(bande, ref_min)
                        lignes_p.append(_ligne(p, _MODE, f"BPE {poi['domaine']}·{poi['domaine_label']}",
                                               poi["nom"], poi["lon"], poi["lat"], bande, ref_min,
                                               ref_nom, v, note, dans))
                    tag = f"{len(pois)} POI comparés"
            for l in lignes_p:
                w.writerow(l)
            jour.flush()                       # flush → une parcelle finie survit à un kill
            print(f"[{i}/{len(reste)}] {p['idu']} ({p['strate']}) — {tag}", flush=True)
    finally:
        jour.close()
        client.close()
        conn.close()
    _finaliser_trajets(ref_nom)


def _finaliser_trajets(ref_nom: str) -> None:
    """Reconstruit TRAJETS.csv (trié) depuis le journal partiel APPEND-ONLY, puis affiche le bilan."""
    with open(PARTIEL_CSV, newline="") as f:
        lignes = list(csv.DictReader(f))
    lignes.sort(key=lambda l: (l["strate"], l["parcelle"], l["poi_type"]))
    _ecrire_trajets(lignes, ref_nom)


def _ligne(p, mode, poi_type, poi_nom, poi_lon, poi_lat, bande, ref_min, ref_source,
           verdict, note, dans_bande):
    ecart = "" if (bande is None or ref_min is None) else f"{ref_min - bande:+.1f}"
    return {"parcelle": p["idu"], "strate": p["strate"], "commune": p["commune"], "mode": mode,
            "poi_type": poi_type, "poi_nom": poi_nom or "",
            "poi_lon": f"{poi_lon:.6f}" if poi_lon else "", "poi_lat": f"{poi_lat:.6f}" if poi_lat else "",
            "labuse_temps_min_bande": "" if bande is None else bande,
            "ref_temps_min": "" if ref_min is None else f"{ref_min:.1f}",
            "ref_source": ref_source, "ecart": ecart,
            "dans_bande": "oui" if dans_bande else "non", "verdict": verdict, "note": note}


_COLS = ["parcelle", "strate", "commune", "mode", "poi_type", "poi_nom", "poi_lon", "poi_lat",
         "labuse_temps_min_bande", "ref_temps_min", "ref_source", "ecart", "dans_bande",
         "verdict", "note"]


def _ecrire_trajets(lignes: list[dict], ref_nom: str) -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(TRAJETS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        for l in lignes:
            w.writerow(l)
    from collections import Counter
    bilan = Counter(l["verdict"] for l in lignes)
    print(f"\n{len(lignes)} pairs comparés → {TRAJETS_CSV}  (réf : {ref_nom})")
    for v in (CONFORME, FAUX, RECENTE, NC):
        print(f"  {v}: {bilan.get(v,0)}")


def main(argv: list[str] | None = None) -> None:
    import argparse
    pa = argparse.ArgumentParser(prog="labuse.verite_terrain_trajets")
    sub = pa.add_subparsers(dest="cmd", required=True)
    pe = sub.add_parser("echantillon")
    pe.add_argument("--n", type=int, default=_PAR_STRATE * 4)
    pc = sub.add_parser("comparer")
    pc.add_argument("--n", type=int, default=0, help="0 = tout l'échantillon")
    pc.add_argument("--ref", choices=["ign", "osrm"], default="ign")
    a = pa.parse_args(argv)
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    if a.cmd == "echantillon":
        cmd_echantillon(max(1, a.n // 4))
    elif a.cmd == "comparer":
        cmd_comparer(a.n, a.ref)


if __name__ == "__main__":
    main()
