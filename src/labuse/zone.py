"""ÉTUDE DE ZONE · Z2 — LE MOTEUR DE ZONE (un seul moteur, deux visages).

Pour un point (parcelle/adresse) ou un polygone, on calcule la zone atteignable (isochrone IGN) puis
on COMPTE chaque couche dedans — population (Filosofi), établissements SIRENE par NAF, équipements
BPE, ventes DVF, annonces Radar. Les « plus proches » portent leur TEMPS de trajet (bande
d'isochrone), jamais une distance en mètres.

DOCTRINES (mandat) :
- UN SEUL POINT DE CALCUL Filosofi : `population_zone()` est l'unique agrégateur ; aucun écran ne doit
  afficher deux « revenus de secteur » divergents.
- Isochrone : CACHE obligatoire (une zone demandée deux fois ne rappelle pas l'API). Échec API →
  dégradé HONNÊTE et NOMMÉ (statut 'indisponible'), JAMAIS un cercle substitué en silence.
- « hors trafic » accompagne chaque temps (posé par l'appelant/UI ; le service ne modélise pas le trafic).
- Revenu = ESTIMÉ (valeurs INSEE lissées). Zone sans population → digne (aucun chiffre inventé).
- MOBPRO reste à la maille COMMUNE, dit comme tel — pas de fausse précision zonale.
- AUCUNE prévision de chiffre d'affaires, aucun score, aucune note d'attractivité.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .connectors.isochrone_ign import fetch_isochrone
from .db import sql_statements

#: bandes de temps (minutes) pour dater les « plus proches » — sous-multiples de la zone demandée.
_BANDES = (2, 4, 6, 8, 10, 15)

#: familles d'équipements BPE présentées avec leur temps — maille DOMAINE (colonne `dom` toujours
#: renseignée ; on évite d'inventer un code TYPEQU/SDOM non prouvé). Ordre = pertinence quotidienne.
_DOMAINES_EQUIP = [
    ("C", "Enseignement"), ("B", "Commerces"), ("D", "Santé et action sociale"),
    ("A", "Services aux particuliers"), ("F", "Sports, loisirs et culture"),
]

def _source_peuplee(session: Session, table: str) -> bool:
    """LOT A — la source est-elle réellement SERVIE (table présente ET ≥ 1 ligne) ? Une table vide
    (créée par le heal mais jamais ingérée : SIRENE, MOBPRO) est « non couverte », pas « 0 résultat »."""
    if session.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
        return False
    return bool(session.execute(text(f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)")).scalar())


def _millesime(source_name: str, session: Session) -> str:
    """Millésime amont d'une source (data_sources.source_millesime), sinon un libellé honnête."""
    m = session.execute(text("SELECT source_millesime FROM data_sources WHERE name = :n"),
                        {"n": source_name}).scalar()
    return m or "millésime non renseigné"


DDL = """
CREATE TABLE IF NOT EXISTS zone_isochrone_cache (
  cache_key  text PRIMARY KEY,          -- mode|minutes|lon|lat (arrondis) : une zone = une clé
  mode       varchar(12),
  minutes    integer,
  lon        double precision,
  lat        double precision,
  geom       geometry(Geometry, 4326),  -- polygone isochrone (IGN)
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_zone_iso_geom ON zone_isochrone_cache USING gist (geom);
"""


def ensure_tables(session: Session) -> None:
    for stmt in sql_statements(DDL):
        session.execute(text(stmt))
    session.flush()


def _cle(lon: float, lat: float, minutes: int, mode: str) -> str:
    # arrondi 5 décimales (~1 m) : deux demandes quasi identiques partagent le cache.
    return f"{mode}|{minutes}|{lon:.5f}|{lat:.5f}"


def isochrone(session: Session, lon: float, lat: float, minutes: int, mode: str, *,
              client: httpx.Client | None = None, fetch=None) -> dict:
    """Zone atteignable en `minutes` depuis (lon, lat) en `mode`. CACHE d'abord, puis IGN.

    Retour : {"statut": 'cache'|'ign'|'indisponible', "geom_geojson": dict|None, "minutes", "mode"}.
    Échec API → statut 'indisponible', geom None (JAMAIS un cercle en silence). Ne lève pas.
    `fetch` non fourni → `fetch_isochrone` (résolu comme global du module, donc monkeypatchable)."""
    fetch = fetch or fetch_isochrone
    ensure_tables(session)
    cle = _cle(lon, lat, minutes, mode)
    # CIRCUIT-1 lot 2.7 — TTL 30 jours : la voirie bouge, une isochrone figée à la 1re demande
    # était de l'eau ancienne sans étiquette. Au-delà du TTL l'entrée est ignorée (ré-interrogation
    # IGN, remplacement à l'écriture) ; la bascule purge aussi le cache (bascule_flux).
    row = session.execute(text(
        "SELECT ST_AsGeoJSON(geom) AS gj FROM zone_isochrone_cache "
        "WHERE cache_key = :k AND created_at > now() - interval '30 days'"),
        {"k": cle}).mappings().first()
    if row and row["gj"]:
        return {"statut": "cache", "geom_geojson": json.loads(row["gj"]), "minutes": minutes, "mode": mode}
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": "labuse/etude-zone"})
    try:
        geom = fetch(lon, lat, minutes, mode, client=client)
    except Exception as exc:  # noqa: BLE001 — dégradé honnête, jamais un cercle substitué
        return {"statut": "indisponible", "geom_geojson": None, "minutes": minutes, "mode": mode,
                "detail": f"service isochrone IGN indisponible ({type(exc).__name__})"}
    finally:
        if own:
            client.close()
    session.execute(text(
        "INSERT INTO zone_isochrone_cache (cache_key, mode, minutes, lon, lat, geom) "
        "VALUES (:k, :m, :mn, :lon, :lat, ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)) "
        "ON CONFLICT (cache_key) DO UPDATE SET geom = EXCLUDED.geom, created_at = now()"),
        {"k": cle, "m": mode, "mn": minutes, "lon": lon, "lat": lat, "g": json.dumps(geom)})
    session.flush()
    return {"statut": "ign", "geom_geojson": geom, "minutes": minutes, "mode": mode}


def bandes_isochrones(session: Session, lon: float, lat: float, minutes: int, mode: str, *,
                      client: httpx.Client | None = None, fetch=None) -> dict[int, dict]:
    """Isochrones concentriques (sous-multiples de `minutes`) pour dater les POI. Chacune passe par le
    cache. Retourne {minutes_bande: geom_geojson} pour les bandes disponibles (peut être vide si l'API
    est indisponible et le cache froid)."""
    cibles = sorted({b for b in _BANDES if b <= minutes} | {minutes})
    out: dict[int, dict] = {}
    for b in cibles:
        res = isochrone(session, lon, lat, b, mode, client=client, fetch=fetch)
        if res["geom_geojson"] is not None:
            out[b] = res["geom_geojson"]
    return out


def _zone2975() -> str:
    """Fragment SQL : la géométrie de zone (GeoJSON bind :zone, 4326) projetée en 2975 (métrique local)."""
    return "ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:zone), 4326), 2975)"


def _bande_min(session: Session, lon: float, lat: float, bandes: dict[int, dict]) -> int | None:
    """Plus petite bande d'isochrone (minutes) contenant le point — le TEMPS de trajet du POI. None si
    aucune bande disponible ou le point tombe hors de toutes (au bord de la zone maximale)."""
    for mn in sorted(bandes):
        g = bandes[mn]
        inside = session.execute(text(
            "SELECT ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), "
            "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))"),
            {"g": json.dumps(g), "lon": lon, "lat": lat}).scalar()
        if inside:
            return mn
    return None


def population_zone(session: Session, geom_geojson: dict) -> dict:
    """UNIQUE point de calcul Filosofi (mandat) — agrège les carreaux 200 m dont le CENTROÏDE est dans
    la zone (règle d'inclusion documentée). Revenu = ESTIMÉ (INSEE lissé). Zone sans population = digne.

    Colonnes lues : ind/men/men_pauv/men_prop/ind_snv (contexte fiche existant) + tranches d'âge
    ind_0_3…ind_18_24 (part des moins de 25 ans). Millésime Filosofi 2021."""
    r = session.execute(text(
        f"""SELECT
              coalesce(round(sum(f.ind)), 0)                                    AS habitants,
              coalesce(round(sum(f.men)), 0)                                    AS menages,
              round(sum(f.ind_snv) / NULLIF(sum(f.ind), 0))                     AS revenu_median_eur,
              round(100 * sum(f.ind_0_3 + f.ind_4_5 + f.ind_6_10 + f.ind_11_17 + f.ind_18_24)
                    / NULLIF(sum(f.ind), 0))                                    AS pct_moins_25,
              round(100 * sum(f.men_pauv) / NULLIF(sum(f.men), 0))              AS taux_pauvrete_pct,
              count(*)                                                          AS n_carreaux
            FROM filosofi_carreaux_200m f
            WHERE ST_Contains({_zone2975()}, ST_Centroid(f.geom))"""),
        {"zone": json.dumps(geom_geojson)}).mappings().first()
    millesime = "Filosofi 2021 (INSEE, carreaux 200 m)"
    if not r or (r["n_carreaux"] or 0) == 0 or (r["habitants"] or 0) == 0:
        return {"inhabitee": True, "millesime": millesime}
    # LOT 3 — imputation PILOTÉE PAR LA DONNÉE (i_est_200 : '1' = carreau imputé depuis la maille 1 km).
    # Défensif : la colonne peut manquer en base de test → on n'invente pas, on laisse None (garde).
    n_imp = n_car_rev = None
    has_iest = session.execute(text("SELECT 1 FROM information_schema.columns "
                                    "WHERE table_name='filosofi_carreaux_200m' AND column_name='i_est_200'")).first()
    if has_iest:
        imp = session.execute(text(
            f"""SELECT count(*) FILTER (WHERE f.i_est_200 = '1') n_imp, count(*) n_tot
                FROM filosofi_carreaux_200m f
                WHERE f.ind > 0 AND ST_Contains({_zone2975()}, ST_Centroid(f.geom))"""),
            {"zone": json.dumps(geom_geojson)}).mappings().first()
        n_imp, n_car_rev = int(imp["n_imp"]), int(imp["n_tot"])
    majorite_imputee = bool(n_imp is not None and n_car_rev and n_imp > n_car_rev / 2)
    # SOURCES-1 lot 6 — l'overlay QUARTIERS (IRIS RP2022) de la zone : vacance et âge du bâti
    # des IRIS intersectés (maille IRIS DITE — complète Filosofi, ne le remplace pas).
    iris_zone = None
    has_iris = session.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'iris_rp'")).first()
    if has_iris:
        rz = session.execute(text(
            f"""SELECT count(*) AS n_iris,
                  round((100.0 * sum(i.logvac) / NULLIF(sum(i.log), 0))::numeric, 1)  AS vacance_pct,
                  round((100.0 * sum(i.ach_1919 + i.ach_1945 + i.ach_1970 + i.ach_1990)
                        / NULLIF(sum(i.ach_tot), 0))::numeric, 1)           AS part_bati_avant_1990_pct
                FROM iris_rp i
                JOIN spatial_layers sl ON sl.kind = 'iris_insee' AND sl.subtype = i.iris
                WHERE ST_Intersects(sl.geom_2975, {_zone2975()})"""),
            {"zone": json.dumps(geom_geojson)}).mappings().first()
        if rz and rz["n_iris"]:
            iris_zone = {"n_iris": int(rz["n_iris"]),
                         "vacance_pct": float(rz["vacance_pct"]) if rz["vacance_pct"] is not None else None,
                         "part_bati_avant_1990_pct": (float(rz["part_bati_avant_1990_pct"])
                                                      if rz["part_bati_avant_1990_pct"] is not None else None),
                         "source": "INSEE RP2022 par IRIS (quartiers intersectés)"}
    return {
        "inhabitee": False,
        "iris": iris_zone,
        "habitants": int(r["habitants"]),
        "menages": int(r["menages"]),
        "revenu_median_eur": int(r["revenu_median_eur"]) if r["revenu_median_eur"] is not None else None,
        "revenu_estime": True,   # Filosofi winsorisé → toujours ESTIMÉ (jamais présenté comme mesuré)
        "revenu_impute_n": n_imp,             # carreaux (à revenu) imputés · None si non mesurable
        "revenu_carreaux_n": n_car_rev,       # carreaux (à revenu) total
        "revenu_majorite_imputee": majorite_imputee,   # → « valeur approchée sur N carreaux sur M »
        "pct_moins_25": int(r["pct_moins_25"]) if r["pct_moins_25"] is not None else None,
        "taux_pauvrete_pct": int(r["taux_pauvrete_pct"]) if r["taux_pauvrete_pct"] is not None else None,
        "n_carreaux": int(r["n_carreaux"]),
        "millesime": millesime,
    }


# CIRCUIT-6 lot 6 (G6) — `emplois_communes` (MOBPRO) SUPPRIMÉE : source retirée le
# 06/09/2026, lecteur sans appelant (code mort vérifié CIRCUIT-5b) — le verrou G6 a
# attrapé la lecture résiduelle de mobpro_commune ; on cesse de lire, la table reste.

#: tranches d'effectif SIRENE (code INSEE → bornes de la fourchette de salariés). 53 = « 10 000+ »
#: (borne haute ouverte). 'NN' / null = non renseigné (compté à part, jamais additionné).
TRANCHE_BORNES = {
    "00": (0, 0), "01": (1, 2), "02": (3, 5), "03": (6, 9), "11": (10, 19), "12": (20, 49),
    "21": (50, 99), "22": (100, 199), "31": (200, 249), "32": (250, 499), "41": (500, 999),
    "42": (1000, 1999), "51": (2000, 4999), "52": (5000, 9999), "53": (10000, None),
}


def emplois_zone(session: Session, geom_geojson: dict) -> dict:
    """LOT 2 — « postes salariés déclarés dans la zone » (remplace MOBPRO, ABANDONNÉ : l'INSEE ne traite
    pas l'emploi au lieu de travail à une maille infracommunale — un nombre d'actifs sur 86 ha serait une
    invention). On somme les TRANCHES d'effectif SIRENE des établissements de la zone → une FOURCHETTE
    (jamais un point). Les établissements SANS tranche renseignée sont comptés à part et dits."""
    rows = session.execute(text(
        f"""SELECT tranche_effectif, count(*) n
            FROM sirene_etablissements
            WHERE actif AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
            GROUP BY tranche_effectif"""),
        {"zone": json.dumps(geom_geojson)}).all()
    lo = hi = 0
    hi_ouvert = False
    n_avec = n_sans = n_etab = 0
    for tranche, n in rows:
        n_etab += n
        bornes = TRANCHE_BORNES.get(tranche or "")
        if bornes is None:                       # 'NN' / null : non renseigné → compté à part
            n_sans += n
            continue
        n_avec += n
        lo += bornes[0] * n
        if bornes[1] is None:
            hi_ouvert = True
        else:
            hi += bornes[1] * n
    return {"postes_min": lo, "postes_max": hi, "postes_max_ouvert": hi_ouvert,
            "n_etablissements": n_etab, "n_avec_tranche": n_avec, "n_sans_tranche": n_sans,
            "libelle": "postes salariés déclarés dans la zone"}


#: F2 (OUTILS-4) — SEUIL d'ancienneté du dernier traitement SIRENE au-delà duquel on invite à vérifier
#: sur place. JUSTIFICATION : l'INSEE retraite un établissement à chaque changement déclaré (création,
#: adresse, activité, CESSATION) ; un enregistrement non retouché depuis 24 mois n'a plus vu passer de
#: déclaration récente — c'est précisément le cas où une fermeture réelle non signalée (ex. CHANTECLAIR)
#: peut se cacher. En-deçà, le registre a été confirmé récemment. 24 mois = 2 cycles annuels déclaratifs.
SEUIL_FRAICHEUR_MOIS = 24


def concurrents_zone(session: Session, geom_geojson: dict, naf: str, *, bandes: dict[int, dict],
                     maxi: int = 40) -> dict:
    """Établissements SIRENE du NAF dans la zone (concurrents). Nom masqué si non diffusible. Chaque
    « plus proche » porte son TEMPS (plus petite bande le contenant), jamais une distance en mètres."""
    rows = session.execute(text(
        f"""SELECT siret, naf, denomination, enseigne, diffusible,
                   extract(year FROM date_creation)::int AS annee_creation,
                   to_char(date_dernier_traitement, 'YYYY-MM-DD') AS date_maj,
                   (date_dernier_traitement < (now() - make_interval(months => :seuil)))::bool AS maj_ancienne,
                   ST_X(geom) AS lon, ST_Y(geom) AS lat
            FROM sirene_etablissements
            WHERE naf = :naf AND actif AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
            LIMIT :maxi"""),
        {"zone": json.dumps(geom_geojson), "naf": naf, "maxi": maxi, "seuil": SEUIL_FRAICHEUR_MOIS}).mappings().all()
    items = []
    for r in rows:
        # A3-bis (OUTILS-2) — enseigne PUIS dénomination (masqué si non diffusible) ; `annee_creation`
        # (SIRENE dateCreationEtablissement) sert le « depuis AAAA » de la fiche. Jamais inventée : null
        # possible (établissement sans date renseignée à la source).
        # F2 (OUTILS-4) — `date_maj` = dateDernierTraitementEtablissement : la fraîcheur DÉCLARATIVE de
        # l'établissement au registre (« mis à jour MM/YYYY »). Le front la rend et alerte au-delà du seuil.
        nom = (r["enseigne"] or r["denomination"]) if r["diffusible"] else None
        items.append({
            "siret": r["siret"], "naf": r["naf"],
            "nom": nom or "Établissement (nom non diffusé)",
            "annee_creation": r["annee_creation"], "date_maj": r["date_maj"], "maj_ancienne": bool(r["maj_ancienne"]),
            "diffusible": r["diffusible"], "lon": r["lon"], "lat": r["lat"],
            "temps_min": _bande_min(session, r["lon"], r["lat"], bandes),
        })
    items.sort(key=lambda x: (x["temps_min"] is None, x["temps_min"] or 999))
    # F1 (OUTILS-3) — libellé NAF LISIBLE (« Boulangerie et boulangerie-pâtisserie ») servi à côté du
    # code brut « 1071C » : le code reste, mais l'humain lit l'activité. Source unique : naf_labels.
    from .naf_labels import label as _naf_label
    return {"n": len(items), "naf": naf, "naf_label": _naf_label(naf),
            "seuil_fraicheur_mois": SEUIL_FRAICHEUR_MOIS, "items": items}


#: F3 (OUTILS-4) — au-delà de ce nombre d'établissements chargés, on plafonne l'aperçu par famille (les
#: COMPTES restent exacts : ils viennent d'un GROUP BY sur toute l'emprise, pas de l'échantillon chargé).
ENTREPRISES_CAP_CARTE = 1000   # établissements détaillés (listes dépliables + pastilles carte)
ENTREPRISES_CAP_LISTE = 40     # par famille, dans le déplié


def entreprises_zone(session: Session, geom_geojson: dict, *, cap_carte: int = ENTREPRISES_CAP_CARTE,
                     cap_liste: int = ENTREPRISES_CAP_LISTE) -> dict:
    """F3 — TOUTES les entreprises ACTIVES de la zone, GROUPÉES PAR FAMILLE d'activité (section NAF A-U).
    Une zone dense dépasse le millier : on lit d'abord la STRUCTURE (comptes exacts par famille via un
    GROUP BY sur toute l'emprise), puis on creuse (établissements détaillés plafonnés, jamais le count).
    Mêmes règles que les concurrents : actifs seuls, nom ou « non diffusé », activité en clair, date de
    création, date de dernier traitement (fraîcheur), lien parcelle (lon/lat pour la carte). Familles et
    libellés viennent de la source UNIQUE `naf_nomenclature` (jamais en dur au front)."""
    from .naf_labels import label as _naf_label
    from .naf_nomenclature import NAF_SOUS_CLASSES, SECTIONS
    zone = {"zone": json.dumps(geom_geojson)}
    _sec = lambda naf: (NAF_SOUS_CLASSES.get((naf or "").upper()) or (None, None))[1] or "?"

    # COMPTES EXACTS par NAF → agrégés par famille (section) sur TOUTE l'emprise. La somme = le total.
    fam_n: dict[str, int] = {}
    total = 0
    for naf, n in session.execute(text(
            f"""SELECT naf, count(*) AS n FROM sirene_etablissements
                WHERE actif AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
                GROUP BY naf"""), zone).all():
        total += int(n)
        fam_n[_sec(naf)] = fam_n.get(_sec(naf), 0) + int(n)

    # ÉTABLISSEMENTS DÉTAILLÉS (plafonnés) — pour les listes dépliables et les pastilles carte.
    ets = session.execute(text(
        f"""SELECT siret, naf, denomination, enseigne, diffusible,
                   extract(year FROM date_creation)::int AS annee_creation,
                   to_char(date_dernier_traitement, 'YYYY-MM-DD') AS date_maj,
                   ST_X(geom) AS lon, ST_Y(geom) AS lat
            FROM sirene_etablissements
            WHERE actif AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
            ORDER BY date_creation DESC NULLS LAST
            LIMIT :cap"""), {**zone, "cap": cap_carte}).mappings().all()
    par_fam: dict[str, list] = {}
    for r in ets:
        nom = (r["enseigne"] or r["denomination"]) if r["diffusible"] else None
        par_fam.setdefault(_sec(r["naf"]), []).append({
            "siret": r["siret"], "naf": r["naf"], "naf_label": _naf_label(r["naf"]),
            "nom": nom or "Établissement (nom non diffusé)",
            "annee_creation": r["annee_creation"], "date_maj": r["date_maj"],
            "diffusible": r["diffusible"], "lon": r["lon"], "lat": r["lat"]})

    familles = []
    for sec, n in sorted(fam_n.items(), key=lambda x: (-x[1], x[0])):
        charges = par_fam.get(sec, [])
        familles.append({"section": sec, "nom": SECTIONS.get(sec, "Activité non classée"), "n": n,
                         "etablissements": charges[:cap_liste], "charges": min(len(charges), cap_liste)})
    return {"total": total, "familles": familles, "n_charges": len(ets), "cap_carte": cap_carte,
            "millesime": session.execute(text(
                "SELECT millesime FROM sirene_etablissements WHERE millesime IS NOT NULL "
                "ORDER BY ingested_at DESC LIMIT 1")).scalar()}


def equipements_proches(session: Session, lon0: float, lat0: float, geom_geojson: dict, *,
                        bandes: dict[int, dict]) -> list[dict]:
    """L'équipement BPE le plus proche de chaque DOMAINE présent dans la zone, AVEC son temps (bande).
    Maille domaine (colonne `dom`/subtype garantie) : on ne devine aucun code TYPEQU/SDOM non prouvé."""
    out: list[dict] = []
    for dom, label in _DOMAINES_EQUIP:
        r = session.execute(text(
            f"""SELECT name, ST_X(geom) AS lon, ST_Y(geom) AS lat
                FROM spatial_layers
                WHERE kind = 'amenite_bpe' AND subtype = :dom
                  AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT 1"""),
            {"zone": json.dumps(geom_geojson), "dom": dom, "lon": lon0, "lat": lat0}).mappings().first()
        if r:
            out.append({"domaine": label, "nom": r["name"],
                        "temps_min": _bande_min(session, r["lon"], r["lat"], bandes)})
    out.sort(key=lambda x: (x["temps_min"] is None, x["temps_min"] or 999))
    return out


def generateurs_flux(session: Session, geom_geojson: dict) -> list[dict]:
    """Générateurs de flux dans la zone : établissements d'enseignement (BPE dom C), arrêts/pôles de
    transport (GTFS/OSM). Faits comptés, jamais une prévision de fréquentation."""
    out = []
    ens = session.execute(text(
        f"SELECT count(*) FROM spatial_layers WHERE kind='amenite_bpe' AND subtype='C' "
        f"AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))"),
        {"zone": json.dumps(geom_geojson)}).scalar() or 0
    if ens:
        out.append({"label": f"{ens} établissement(s) d'enseignement", "source": "BPE (INSEE)"})
    poles = session.execute(text(
        f"SELECT count(*) FROM spatial_layers WHERE kind IN ('pole_echange','transport_arret') "
        f"AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))"),
        {"zone": json.dumps(geom_geojson)}).scalar() or 0
    if poles:
        out.append({"label": f"{poles} arrêt(s)/pôle(s) de transport", "source": "GTFS / OSM"})
    return out


def marche_zone(session: Session, geom_geojson: dict) -> dict:
    """Marché immobilier de la zone (maquette écran 3) : ventes DVF 12 mois, médian €/m² bâti (36 mois,
    ventes bâties), annonces Radar actives, permis 36 mois (SITADEL géolocalisé). Faits sourcés, jamais
    une prévision. DVF est clé par `id_parcelle` (≡ parcels.idu) — join documenté. Chaque métrique se
    garde sur table absente (contrat data-gap : 0/None, jamais un 500)."""
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson)}

    def _existe(table: str) -> bool:
        return session.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None

    ventes = prix = annonces = permis = None
    if _existe("dvf_mutations"):
        # SOURCES-FIX-1 (E1) — l'Étude de zone lit désormais la MÊME table que le bloc Marché de la
        # fiche : `dvf_mutations` (maille MUTATION), via le point de calcul UNIQUE `dvf_mediane`.
        # Avant, cette section lisait `dvf_mutations_parcelle` (table éclatée par parcelle) : une
        # vente d'immeuble répétée sur N parcelles gonflait le compte des ventes et faisait exploser
        # la médiane (artefact du « 100 888 €/m² »). Même table, même filtres, même borne, même
        # fenêtre que `prix_par_type_zone` → une seule médiane à périmètre égal.
        ventes = session.execute(text(
            f"""SELECT count(*) FROM dvf_mutations dm
                WHERE dm.geom IS NOT NULL AND dm.nature_mutation ILIKE 'vente%'
                  AND dm.date_mutation >= (now() - interval '12 months')
                  AND ST_Contains({z}, ST_Transform(dm.geom, 2975))"""), p).scalar()
        from .dvf_mediane import mediane_bati
        prix = mediane_bati(session, geom_geojson=geom_geojson)["median"]
    if _existe("pige_biens") and _existe("parcels"):
        annonces = session.execute(text(
            f"""SELECT count(*) FROM pige_biens b JOIN parcels p ON p.idu = b.idu
                WHERE b.statut IN ('active','en_vente_longue')
                  AND ST_Contains({z}, ST_Transform(p.centroid, 2975))"""), p).scalar()
    if _existe("sitadel_permits"):
        permis = session.execute(text(
            f"""SELECT count(*) FROM sitadel_permits s
                WHERE s.geom IS NOT NULL AND s.date >= (now() - interval '36 months')
                  AND ST_Contains({z}, ST_Transform(s.geom, 2975))"""), p).scalar()
    # EXPORTS-1 (5.5) : le compte d'annonces Radar n'est JAMAIS un compteur de marché — la pige
    # est manuelle et partielle (audit B11 : 104 annonces, 12/24 communes, née fin août). Servi
    # comme MINIMUM avec sa réserve, jamais un total.
    return {"ventes_12m": int(ventes or 0),
            "prix_m2_median_bati": int(prix) if prix is not None else None,
            "annonces_actives": int(annonces or 0),
            "annonces_reserve": "annonces suivies par la pige LABUSE (collecte manuelle, "
                                "couverture partielle) — un minimum, pas un total de marché",
            "permis_36m": int(permis or 0)}


def trafic_zone(session: Session, geom_geojson: dict) -> dict:
    """LOT 5 — trafic VÉHICULES sur ROUTES NATIONALES traversant ou bordant la zone (Région Réunion,
    TMJA véhicules/jour). Par route, le comptage le plus RÉCENT (millésime porté). Aucune RN dans la
    zone → « aucun axe national dans la zone », jamais un zéro. Pas de flux piéton, pas de départemental."""
    if session.execute(text("SELECT to_regclass('trafic_rn')"), {}).scalar() is None:
        return {"couverte": False, "axes": []}
    rows = session.execute(text(
        f"""SELECT DISTINCT ON (route) route, annee, tmja
            FROM trafic_rn
            WHERE tmja IS NOT NULL
              AND ST_DWithin(ST_Transform(geom, 2975), {_zone2975()}, 30)
            ORDER BY route, annee DESC, tmja DESC"""),
        {"zone": json.dumps(geom_geojson)}).mappings().all()
    axes = [{"route": r["route"], "tmja": int(r["tmja"]), "annee": r["annee"]} for r in rows]
    axes.sort(key=lambda x: -x["tmja"])
    return {"couverte": True, "axes": axes,
            "libelle": "trafic véhicules sur routes nationales (véhicules/jour)",
            "vide": len(axes) == 0}


def contraintes_plu(session: Session, geom_geojson: dict) -> dict:
    """LOT 7 — les zones PLU que la zone d'étude recouvre (tableau ZONE / PART / DOCUMENT, comme le
    dossier banquier). Un polygone peut couvrir PLUSIEURS zones PLU — on les sert TOUTES avec leur part,
    jamais une zone unique choisie arbitrairement. Le libellé de zone (UA commerçante, A agricole…) dit
    déjà où le commerce est admis ou non. Verbatim géré à l'échelle du document (idurba).

    Portée assumée (compte-rendu) : les destinations autorisées/conditionnelles/interdites FINES par
    activité ne sont calibrées que dans 2 des 24 communes (les autres en texte libre ou RNU) — les
    mapper NAF→destination partout serait un faux positif. On sert donc le FAIT géométrique (zones +
    part + document), qui est toujours vrai, et on marque « non calibré » l'absence, jamais un silence."""
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson)}
    if session.execute(text("SELECT to_regclass('spatial_layers')"), {}).scalar() is None:
        return {"zones": [], "note": "PLU non disponible."}
    aire = session.execute(text(f"SELECT ST_Area({z})"), p).scalar() or 0
    if not aire:
        return {"zones": [], "note": "PLU non disponible."}
    p["aire"] = float(aire)
    # ETUDE-ZONE-1 A2 — LA zone servie est le TOKEN de zone (1er mot du libellé GPU : « Usdu »,
    # « U2c », « AU3c »…), PAS le `subtype` (typezone générique « U »/« AUc »). C'est l'unique
    # vérité déjà utilisée par la fiche (app.py `_reglement_plu_block`, EXPORTS-REBRANCHEMENT-1) :
    # les calibrations de destinations (module plu.destinations) sont clées sur ce token. En lisant
    # `subtype`, la zone « U » ne matchait aucune calibration → « calibration en cours » à tort sur
    # Saint-Paul (pourtant calibré/validé). On aligne l'outil sur la fiche : token du libellé, repli name.
    rows = session.execute(text(
        f"""SELECT COALESCE(NULLIF(rtrim(split_part(btrim(l.attrs->>'libelle'), ' ', 1), ':'), ''),
                            rtrim(split_part(btrim(l.name), ' ', 1), ':'),
                            l.subtype, '?') AS zone,
                   l.commune, l.attrs->>'idurba' AS document,
                   round(100 * sum(ST_Area(ST_Intersection(ST_Transform(l.geom,2975), {z})))
                         / :aire) AS part_pct
            FROM spatial_layers l
            WHERE l.kind='plu_gpu_zone' AND ST_Intersects(ST_Transform(l.geom,2975), {z})
            GROUP BY 1,2,3
            HAVING round(100 * sum(ST_Area(ST_Intersection(ST_Transform(l.geom,2975), {z}))) / :aire) > 0
            ORDER BY part_pct DESC LIMIT 12"""), p).mappings().all()
    zones = [{"zone": r["zone"], "part_pct": int(r["part_pct"] or 0), "commune": r["commune"],
              "document": r["document"]} for r in rows]
    return {
        "zones": zones,
        "cdac_vigilance": ("Au-delà de 1 000 m² de surface de vente, une autorisation d'exploitation "
                           "commerciale (CDAC) peut être requise — point de vigilance à instruire, non instruit ici."),
        "note": ("Zones PLU recouvertes par la zone (part de surface). Le libellé de zone indique où le "
                 "commerce est admis ; la règle fine par activité se lit au règlement du document. "
                 "Commune en RNU ou non calibrée : « non calibré », jamais une absence de contrainte."),
    }


def zone_demain(session: Session, geom_geojson: dict) -> dict:
    """LOT 8 — « la zone de demain » (données déjà en base, signal DATÉ, jamais une projection) :
    logements autorisés sur 36 mois glissants (Sitadel `raw.nb_lgt`) = population à venir ; zones AU
    ouvertes intersectant la zone = urbanisation programmée. Chaque métrique se garde sur table absente."""
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson)}

    def _existe(t: str) -> bool:
        return session.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar() is not None

    logements = permis = None
    if _existe("sitadel_permits"):
        r = session.execute(text(
            f"""SELECT count(*) n, coalesce(sum((s.raw->>'nb_lgt')::int), 0) lgt
                FROM sitadel_permits s
                WHERE s.geom IS NOT NULL AND s.date >= (now() - interval '36 months')
                  AND ST_Contains({z}, ST_Transform(s.geom, 2975))"""), p).mappings().first()
        permis, logements = int(r["n"] or 0), int(r["lgt"] or 0)
    au_n = au_ha = None
    if _existe("spatial_layers"):
        r = session.execute(text(
            f"""SELECT count(*) n, round((coalesce(sum(ST_Area(ST_Transform(geom,2975))),0)/10000)::numeric) ha
                FROM spatial_layers
                WHERE kind='plu_gpu_zone' AND subtype LIKE 'AU%'
                  AND ST_Intersects({z}, ST_Transform(geom, 2975))"""), p).mappings().first()
        au_n, au_ha = int(r["n"] or 0), int(r["ha"] or 0)
    return {"logements_autorises_36m": logements, "permis_36m": permis,
            "au_zones_n": au_n, "au_zones_ha": au_ha,
            "source": "Sitadel (autorisations) · PLU/GPU (zones AU) — signal daté, pas une projection"}


# ============================================================================
# ETUDE-ZONE-2 Lot B — agrégateurs de zone ADDITIONNELS. Règle transversale (mandat) : chaque
# fonction RÉUTILISE un point de calcul existant (flash._marche pour DVF, les couches DEAL de
# spatial_layers pour les risques comme l'outil Pièges & risques, parcelle_personne_morale par
# SIREN comme Scan patrimoine, BPE de spatial_layers). Aucun recalcul maison — c'est ce qui avait
# produit le 100 888 €/m² (ETUDE-ZONE-1). % de recouvrement d'une catégorie = ST_Area(ST_Intersection
# (ST_Union(geom_2975), zone)) / ST_Area(zone) (ST_Union pour ne jamais compter deux fois un
# chevauchement interne), sur geom_2975. Faits sourcés et datés, jamais une projection.
# ============================================================================

def _aire_zone(session: Session, geom_geojson: dict) -> float:
    return float(session.execute(text(f"SELECT ST_Area({_zone2975()})"),
                                 {"zone": json.dumps(geom_geojson)}).scalar() or 0)


def age_structure_zone(session: Session, geom_geojson: dict) -> dict | None:
    """B1 — structure d'âge de la zone, agrégée sur les IRIS intersectés et PONDÉRÉE par la part de
    surface de chaque IRIS dans la zone (RP 2022, INSEE). L'ÉVOLUTION 2016→2022 n'est PAS servie :
    iris_rp ne porte que le millésime RP2022 (aucune population 2016 en base) — on ne l'invente pas."""
    if session.execute(text("SELECT to_regclass('iris_rp')")).scalar() is None:
        return None
    z = _zone2975()
    r = session.execute(text(
        f"""WITH w AS (
              SELECT i.pop, i.pop_0014, i.pop_1529, i.pop_3044, i.pop_4559, i.pop_6074, i.pop_75p,
                     ST_Area(ST_Intersection(sl.geom_2975, {z})) / NULLIF(ST_Area(sl.geom_2975), 0) AS frac
              FROM iris_rp i JOIN spatial_layers sl ON sl.kind='iris_insee' AND sl.subtype = i.iris
              WHERE ST_Intersects(sl.geom_2975, {z}))
            SELECT count(*) n_iris, round(sum(pop*frac)) pop,
                   round(sum(pop_0014*frac)) p0014, round(sum(pop_1529*frac)) p1529,
                   round(sum(pop_3044*frac)) p3044, round(sum(pop_4559*frac)) p4559,
                   round(sum(pop_6074*frac)) p6074, round(sum(pop_75p*frac)) p75p
            FROM w"""), {"zone": json.dumps(geom_geojson)}).mappings().first()
    if not r or not r["n_iris"] or not (r["pop"] or 0):
        return None
    pop = float(r["pop"]) or 1.0
    tr = [("0–14 ans", r["p0014"]), ("15–29 ans", r["p1529"]), ("30–44 ans", r["p3044"]),
          ("45–59 ans", r["p4559"]), ("60–74 ans", r["p6074"]), ("75 ans et +", r["p75p"])]
    return {"n_iris": int(r["n_iris"]), "pop_iris": int(r["pop"]),
            "tranches": [{"label": lbl, "n": int(v or 0), "pct": round(100 * float(v or 0) / pop)}
                         for lbl, v in tr],
            "millesime": "RP 2022 (INSEE, par IRIS — pondéré par la part de surface d'IRIS dans la zone)",
            "evolution_indisponible": "Évolution 2016→2022 non servie : la base ne porte que le millésime RP2022."}


def prix_par_type_zone(session: Session, geom_geojson: dict) -> dict:
    """B3 — prix médian €/m² par TYPE (maison, appartement, terrain nu) dans la zone, 36 mois.
    RÉUTILISE le point de calcul du bloc Marché de la fiche (flash.data._marche) : table dvf_mutations
    (maille MUTATION, pas la table éclatée par parcelle → pas d'artefact du 100 888), ventes seules,
    €/m² BÂTI (surface_reelle_bati≥20) pour maison/appartement, €/m² TERRAIN (surface_terrain≥100 et
    bâti<20) pour le terrain nu. Sous 5 ventes → médiane « — » (échantillon insuffisant, dit)."""
    if session.execute(text("SELECT to_regclass('dvf_mutations')")).scalar() is None:
        return {"types": []}
    z = _zone2975()
    from .dvf_mediane import mediane_bati
    rows = []
    # SOURCES-FIX-1 (E1) — maison / appartement passent par le point de calcul UNIQUE `dvf_mediane`
    # (même table, filtres, borne, fenêtre que l'Étude de zone `marche_zone`). Le terrain nu garde son
    # ratio propre (valeur / surface_terrain), hors périmètre de la médiane bâtie.
    for slug, label, tl in (("maison", "Maison", "Maison"), ("appartement", "Appartement", "Appartement")):
        m = mediane_bati(session, geom_geojson=geom_geojson, type_local=tl)
        rows.append({"type": slug, "label": label, "base": "bâti", "n": m["n"],
                     "median_eur_m2": m["median"], "periode": m["periode"]})
    rt = session.execute(text(
        f"""SELECT count(*) n,
                   round(percentile_cont(0.5) WITHIN GROUP (
                     ORDER BY dm.valeur_fonciere / NULLIF(dm.surface_terrain, 0))::numeric) med,
                   to_char(min(dm.date_mutation), 'MM/YYYY') d0,
                   to_char(max(dm.date_mutation), 'MM/YYYY') d1
            FROM dvf_mutations dm
            WHERE dm.geom IS NOT NULL AND dm.nature_mutation ILIKE 'vente%'
              AND dm.valeur_fonciere > 0 AND dm.type_local IS NULL
              AND dm.surface_terrain >= 100 AND coalesce(dm.surface_reelle_bati, 0) < 20
              AND dm.date_mutation >= (now() - interval '36 months')
              AND ST_Contains({z}, ST_Transform(dm.geom, 2975))"""),
        {"zone": json.dumps(geom_geojson)}).mappings().first()
    nt = int(rt["n"] or 0)
    rows.append({"type": "terrain", "label": "Terrain nu", "base": "terrain", "n": nt,
                 "median_eur_m2": int(rt["med"]) if (nt >= 5 and rt["med"] is not None) else None,
                 "periode": [rt["d0"], rt["d1"]] if nt else None})
    return {"types": rows, "seuil": 5,
            "millesime": "DVF (DGFiP/Etalab) — ventes 36 mois, même lecture que le bloc Marché de la fiche"}


def permis_par_type_zone(session: Session, geom_geojson: dict) -> dict:
    """B3 — permis autorisés par TYPE dans la zone, 36 mois (Sitadel `raw.famille`). La famille Sitadel
    distingue de façon FIABLE les LOGEMENTS des LOCAUX d'activité ; le code destination fin (commerce
    vs activité) n'est pas décodé en base → on ne le devine pas (dit en note). Logements : nb_lgt cumulé."""
    if session.execute(text("SELECT to_regclass('sitadel_permits')")).scalar() is None:
        return {"types": []}
    z = _zone2975()
    # KELFONCIER-FIX-1 (Lot C) — les permis ANNULÉS (ETAT_DAU=4) ne gonflent plus les comptes
    # « autorisés par type » : ils sont EXCLUS des types et comptés à part (`n_annules`). L'état vit
    # dans `raw->>'etat'` (source unique ingestion.permits).
    r = session.execute(text(
        f"""SELECT
              count(*) FILTER (WHERE raw->>'famille'='logements' AND raw->>'etat' IS DISTINCT FROM '4') AS n_log,
              coalesce(sum((raw->>'nb_lgt')::int) FILTER (WHERE raw->>'famille'='logements' AND raw->>'etat' IS DISTINCT FROM '4'), 0) AS lgt,
              count(*) FILTER (WHERE raw->>'famille'='locaux' AND raw->>'etat' IS DISTINCT FROM '4')     AS n_loc,
              count(*) FILTER (WHERE raw->>'famille' IN ('pa','pd') AND raw->>'etat' IS DISTINCT FROM '4') AS n_amng,
              count(*) FILTER (WHERE raw->>'etat' = '4')                            AS n_annules
            FROM sitadel_permits
            WHERE geom IS NOT NULL AND date >= (now() - interval '36 months')
              AND ST_Contains({z}, ST_Transform(geom, 2975))"""),
        {"zone": json.dumps(geom_geojson)}).mappings().first()
    types = [{"type": "logement", "label": "Logement", "n": int(r["n_log"] or 0),
              "detail": f"{int(r['lgt'] or 0)} logements créés"},
             {"type": "locaux", "label": "Locaux d'activité", "n": int(r["n_loc"] or 0), "detail": None}]
    if int(r["n_amng"] or 0):
        types.append({"type": "amenagement", "label": "Aménager / démolir",
                      "n": int(r["n_amng"]), "detail": None})
    return {"types": types,
            "n_annules": int(r["n_annules"] or 0),   # KELFONCIER-FIX-1 (Lot C) — annulés, hors des types
            "note": "Type = famille Sitadel (logements / locaux d'activité) ; les permis ANNULÉS sont "
                    "exclus des comptes et affichés à part. Le détail commerce vs activité (code "
                    "destination SDES) n'est pas décodé en base — non deviné.",
            "millesime": "Sitadel (SDES) — autorisations 36 mois"}


def proprietaires_pm_zone(session: Session, geom_geojson: dict, *, top: int = 5) -> dict:
    """B4 — top propriétaires PERSONNES MORALES par surface cumulée dans la zone. MÊME source et MÊME
    jointure que Scan patrimoine : parcelle_personne_morale (DGFiP) jointe aux parcelles par idu,
    groupée par SIREN, parcelles dont le centroïde est dans la zone. Les particuliers ne sont JAMAIS
    nommés (table PM uniquement)."""
    if session.execute(text("SELECT to_regclass('parcelle_personne_morale')")).scalar() is None:
        return {"proprietaires": []}
    z = _zone2975()
    rows = session.execute(text(
        f"""SELECT pm.siren, max(pm.denomination) denom,
                   count(*) n_parcelles, round(sum(p.surface_m2)) surface_m2
            FROM parcelle_personne_morale pm JOIN parcels p ON p.idu = pm.idu
            WHERE ST_Contains({z}, ST_Transform(p.centroid, 2975))
            GROUP BY pm.siren
            ORDER BY surface_m2 DESC NULLS LAST
            LIMIT :top"""), {"zone": json.dumps(geom_geojson), "top": top}).mappings().all()
    mill = session.execute(text("SELECT max(millesime) FROM parcelle_personne_morale")).scalar()
    return {"proprietaires": [{"siren": r["siren"], "denomination": r["denom"],
                               "n_parcelles": int(r["n_parcelles"]), "surface_m2": int(r["surface_m2"] or 0)}
                              for r in rows],
            "millesime": (f"DGFiP — parcelles des personnes morales (millésime {mill})" if mill
                          else "DGFiP — parcelles des personnes morales")}


#: humanisation des types d'aléa (georisque_alea.subtype) et ordre des niveaux (attrs->>'niveau').
_ALEA_LABEL = {"mouvement_terrain": "Mouvement de terrain", "inondation": "Inondation",
               "submersion_marine": "Submersion marine", "submersion_marine_cc": "Submersion marine (2100)"}
_NIVEAU_RANG = {"fort": 3, "moyen": 2, "faible": 1}


def risques_zone(session: Session, geom_geojson: dict) -> dict:
    """B5 — PPR et aléas recouvrant la zone, en % de sa surface. RÉUTILISE les couches DEAL déjà servies
    par l'outil Pièges & risques (spatial_layers) : `ppr` (INTERDICTION=rouge / PRESCRIPTION=bleu) et
    `georisque_alea` (niveau fort/moyen/faible par type). % = ST_Area(ST_Intersection(ST_Union(geom_2975),
    zone)) / aire, par catégorie (ST_Union → jamais de double compte sur un chevauchement interne)."""
    aire = _aire_zone(session, geom_geojson)
    if not aire or session.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        return {"ppr": [], "aleas": [], "source": "DEAL Réunion — PPR / aléas (Lizmap)"}
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson), "aire": aire}
    # PERF — on CLIPPE chaque feature contre la zone AVANT de l'unir (les morceaux clippés sont petits →
    # ST_Union rapide), au lieu d'unir les multipolygones entiers puis d'intersecter (15 s constatés sur
    # georisque_alea). La zone n'est parsée qu'une fois (CTE `zn`). L'aire d'union est calculée une seule
    # fois (CTE `agg`) puis filtrée > 0 — plus de double ST_Union en SELECT + HAVING.
    ppr_rows = session.execute(text(
        f"""WITH zn AS (SELECT {z} AS g),
                 clip AS (SELECT sl.subtype, ST_Intersection(sl.geom_2975, zn.g) AS gg
                          FROM spatial_layers sl, zn
                          WHERE sl.kind='ppr' AND sl.subtype IN ('INTERDICTION','PRESCRIPTION')
                            AND ST_Intersects(sl.geom_2975, zn.g)),
                 agg AS (SELECT subtype, ST_Area(ST_Union(gg)) a FROM clip GROUP BY subtype)
            SELECT subtype, round(100 * a / :aire) pct FROM agg WHERE a > 0"""), p).mappings().all()
    _PPR_LBL = {"INTERDICTION": ("interdiction", "Zone rouge (interdiction)"),
                "PRESCRIPTION": ("prescription", "Zone bleue (prescription)")}
    ppr = [{"niveau": _PPR_LBL[r["subtype"]][0], "label": _PPR_LBL[r["subtype"]][1], "pct": int(r["pct"])}
           for r in ppr_rows if r["pct"] and int(r["pct"]) > 0 and r["subtype"] in _PPR_LBL]
    ppr.sort(key=lambda x: -x["pct"])
    alea_rows = session.execute(text(
        f"""WITH zn AS (SELECT {z} AS g),
                 clip AS (SELECT sl.subtype, sl.attrs->>'niveau' AS niveau,
                                 ST_Intersection(sl.geom_2975, zn.g) AS gg
                          FROM spatial_layers sl, zn
                          WHERE sl.kind='georisque_alea' AND ST_Intersects(sl.geom_2975, zn.g)),
                 agg AS (SELECT subtype, niveau, ST_Area(ST_Union(gg)) a FROM clip GROUP BY subtype, niveau)
            SELECT subtype, niveau, round(100 * a / :aire) AS pct FROM agg WHERE a > 0"""),
        p).mappings().all()
    aleas = sorted(
        [{"risque": r["subtype"], "label": _ALEA_LABEL.get(r["subtype"], (r["subtype"] or "").replace("_", " ").capitalize()),
          "niveau": r["niveau"], "pct": int(r["pct"])} for r in alea_rows],
        key=lambda a: (-_NIVEAU_RANG.get(a["niveau"], 0), -a["pct"]))
    return {"ppr": ppr, "aleas": aleas, "source": "DEAL Réunion — PPR / aléas (Lizmap)"}


def assainissement_zone(session: Session, geom_geojson: dict) -> dict:
    """B5 — assainissement de la zone : % en zonage COLLECTIF vs ANC (spatial_layers
    kind='zonage_assainissement', subtype collectif/anc — SIG GPU). Couverture partielle (communes
    dotées d'un zonage SIG) : hors couverture, dit « non couvert », jamais un 0 trompeur."""
    aire = _aire_zone(session, geom_geojson)
    if not aire or session.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        return {"couvert": False}
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson), "aire": aire}
    out = {}
    for st in ("collectif", "anc"):
        out[st] = int(session.execute(text(
            f"""SELECT coalesce(round(100 * ST_Area(ST_Intersection(ST_Union(geom_2975), {z})) / :aire), 0)
                FROM spatial_layers WHERE kind='zonage_assainissement' AND subtype=:st
                  AND ST_Intersects(geom_2975, {z})"""), {**p, "st": st}).scalar() or 0)
    couvert = (out["collectif"] + out["anc"]) > 0
    return {"couvert": couvert, "collectif_pct": out["collectif"], "anc_pct": out["anc"],
            "millesime": "Zonage d'assainissement (GPU) — communes dotées d'un SIG"}


#: espaces protégés & zonages fiscaux/prioritaires recouvrant une zone (kind → libellé).
_ESPACES_KINDS = [("znieff", "ZNIEFF (inventaire)"), ("ens", "Espace naturel protégé (ENS / réserve)"),
                  ("parc_national", "Parc national"), ("zfang", "ZFANG (zone franche)"),
                  ("frr", "FRR (ex-ZRR)"), ("qpv", "QPV (quartier prioritaire)")]


def espaces_zonages_zone(session: Session, geom_geojson: dict) -> dict:
    """B5 — espaces protégés (ZNIEFF, ENS, Parc national) et zonages fiscaux/prioritaires (ZFANG, FRR,
    QPV) recouvrant la zone, en % de surface. Couches spatial_layers, % ST_Union/aire (jamais de double
    compte). Une catégorie à 0 % n'est pas listée (fait présent seulement)."""
    aire = _aire_zone(session, geom_geojson)
    if not aire or session.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        return {"items": []}
    z = _zone2975()
    p = {"zone": json.dumps(geom_geojson), "aire": aire}
    items = []
    for kind, label in _ESPACES_KINDS:
        pct = session.execute(text(
            f"""SELECT round(100 * ST_Area(ST_Intersection(ST_Union(geom_2975), {z})) / :aire)
                FROM spatial_layers WHERE kind=:k AND ST_Intersects(geom_2975, {z})"""),
            {**p, "k": kind}).scalar()
        if pct and int(pct) > 0:
            items.append({"kind": kind, "label": label, "pct": int(pct)})
    return {"items": items, "source": "INPN / DEAL / ANCT / Légifrance (couches servies)"}


#: BPE — domaines A→G COMPLETS (INSEE), au lieu des 5 domaines des « plus proches ». Même source que
#: `equipements_proches` (spatial_layers kind='amenite_bpe', subtype = lettre de domaine).
_DOMAINES_BPE = [
    ("A", "Services aux particuliers"), ("B", "Commerces"), ("C", "Enseignement"),
    ("D", "Santé et action sociale"), ("E", "Transports et déplacements"),
    ("F", "Sports, loisirs et culture"), ("G", "Tourisme"),
]


def equipements_bpe_zone(session: Session, geom_geojson: dict, lon0: float, lat0: float, *,
                         bandes: dict[int, dict]) -> dict:
    """B6 — équipements BPE de la zone par DOMAINE complet (A→G) : le COMPTE par domaine + les 3 plus
    proches (avec leur temps de trajet quand les bandes d'isochrone existent). Même couche que
    `equipements_proches` (spatial_layers kind='amenite_bpe')."""
    if session.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        return {"domaines": []}
    z = _zone2975()
    domaines = []
    for dom, label in _DOMAINES_BPE:
        rows = session.execute(text(
            f"""SELECT name, ST_X(geom) AS lon, ST_Y(geom) AS lat
                FROM spatial_layers
                WHERE kind='amenite_bpe' AND subtype=:dom AND ST_Contains({z}, ST_Transform(geom, 2975))
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)"""),
            {"zone": json.dumps(geom_geojson), "dom": dom, "lon": lon0, "lat": lat0}).mappings().all()
        if not rows:
            continue
        proches = [{"nom": r["name"], "temps_min": _bande_min(session, r["lon"], r["lat"], bandes)}
                   for r in rows[:3]]
        domaines.append({"domaine": dom, "label": label, "n": len(rows), "proches": proches})
    return {"domaines": domaines, "millesime": "BPE (INSEE) — base permanente des équipements"}


def acquisitions_pm_zone(session: Session, geom_geojson: dict, *, top: int = 5) -> dict:
    """B7 — acquisitions récentes de PERSONNES MORALES dans la zone : parcelles dont un SIREN est
    propriétaire au DERNIER millésime disponible mais PAS au précédent (pm_proprietaires_millesimes,
    DGFiP). Signal daté, jamais une projection ; particuliers jamais nommés."""
    if session.execute(text("SELECT to_regclass('pm_proprietaires_millesimes')")).scalar() is None:
        return {"acquereurs": [], "n_parcelles": 0}
    mills = [int(r[0]) for r in session.execute(text(
        "SELECT DISTINCT millesime FROM pm_proprietaires_millesimes ORDER BY millesime DESC")).all()]
    if len(mills) < 2:
        return {"acquereurs": [], "n_parcelles": 0}
    cur, prev = mills[0], mills[1]
    z = _zone2975()
    rows = session.execute(text(
        f"""WITH cur AS (
              SELECT DISTINCT pm.siren, pm.idu, pm.denomination
              FROM pm_proprietaires_millesimes pm JOIN parcels p ON p.idu = pm.idu
              WHERE pm.millesime = :cur AND ST_Contains({z}, ST_Transform(p.centroid, 2975))),
            nouv AS (
              SELECT c.* FROM cur c
              WHERE NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes o
                                WHERE o.millesime = :prev AND o.idu = c.idu AND o.siren = c.siren))
            SELECT siren, max(denomination) denom, count(*) n FROM nouv
            GROUP BY siren ORDER BY n DESC LIMIT :top"""),
        {"zone": json.dumps(geom_geojson), "cur": cur, "prev": prev, "top": top}).mappings().all()
    n_total = int(session.execute(text(
        f"""SELECT count(*) FROM (
              SELECT DISTINCT pm.siren, pm.idu FROM pm_proprietaires_millesimes pm
              JOIN parcels p ON p.idu = pm.idu
              WHERE pm.millesime = :cur AND ST_Contains({z}, ST_Transform(p.centroid, 2975))
                AND NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes o
                                WHERE o.millesime = :prev AND o.idu = pm.idu AND o.siren = pm.siren)) t"""),
        {"zone": json.dumps(geom_geojson), "cur": cur, "prev": prev}).scalar() or 0)
    return {"acquereurs": [{"siren": r["siren"], "denomination": r["denom"], "n_parcelles": int(r["n"])}
                           for r in rows],
            "n_parcelles": n_total, "millesime_courant": cur, "millesime_precedent": prev,
            "source": f"DGFiP — parcelles des personnes morales, {prev} → {cur} (signal daté)"}


def commune_contexte_zone(session: Session, geom_geojson: dict) -> dict | None:
    """B7 — LOYER À L'ÉCHELLE DE LA COMMUNE (dit tel quel, jamais maquillé en zonal) : loyer médian OLL
    de la commune DOMINANTE de la zone (celle qui porte le plus de parcelles centrées dans la zone). Le
    loyer OLL est publié à la maille SECTEUR (jamais à la parcelle) — d'où l'échelle commune assumée. La
    FIBRE, elle, est servie ZONALEMENT par l'endpoint (arcep_immeubles ∩ zone), donc pas répétée ici."""
    z = _zone2975()
    row = session.execute(text(
        f"""SELECT left(p.idu, 5) AS insee, p.commune, count(*) n FROM parcels p
            WHERE ST_Contains({z}, ST_Transform(p.centroid, 2975))
            GROUP BY 1, 2 ORDER BY n DESC LIMIT 1"""),
        {"zone": json.dumps(geom_geojson)}).mappings().first()
    if not row:
        return None
    insee, commune = row["insee"], row["commune"]
    loyer = None
    if (session.execute(text("SELECT to_regclass('oll_loyers')")).scalar() is not None
            and session.execute(text("SELECT to_regclass('oll_zonage')")).scalar() is not None):
        loyer = session.execute(text(
            """SELECT l.loyer_median FROM oll_zonage z JOIN oll_loyers l ON l.zone = z.zone AND l.annee = z.annee
               WHERE z.insee = :insee AND l.type_habitat = 'tous' AND l.pieces = 'tous'
               ORDER BY z.annee DESC LIMIT 1"""), {"insee": insee}).scalar()
    # KELFONCIER-FIX-1 (Lot F) — dispositif de commune (Petites Villes de Demain / ACV / ORT),
    # à l'échelle de la commune, lu par la MÊME fonction que la fiche §7 et la fiche commune
    # (ingestion.ort.ort_commune). None si la commune n'est dans aucun programme.
    dispositif_ort = None
    try:
        from .ingestion.ort import ort_commune
        o = ort_commune(session, insee)
        if o:
            _lib = {"pvd": "Petites Villes de Demain (PVD)", "acv": "Action Cœur de Ville (ACV)"}.get(o.get("statut"))
            if _lib or o.get("ort_signee"):
                dispositif_ort = {
                    "libelle": _lib or "Opération de Revitalisation de Territoire (ORT)",
                    "ort_signee": bool(o.get("ort_signee")),
                    "date_signature": o.get("date_signature"),
                    "source": f"DGALN/ANCT — {o.get('millesime', 'table ORT')}"}
    except Exception:  # noqa: BLE001 — jamais casser l'Étude de zone
        dispositif_ort = None
    if loyer is None and dispositif_ort is None:
        return None
    return {"commune": commune, "insee": insee, "echelle": "commune",
            "loyer_median_eur_m2": float(loyer) if loyer is not None else None,
            "dispositif_ort": dispositif_ort,
            "millesime": "OLL 2024 — loyer médian €/m² (tous logements, secteur OLL) — à l'échelle de la commune"}


def etude_de_zone(session: Session, lon: float, lat: float, minutes: int, mode: str, *,
                  geom_geojson: dict | None = None, naf: str | None = None,
                  sous_destination: str | None = None,
                  client: httpx.Client | None = None, fetch=None) -> dict:
    """Agrégat complet d'une zone : isochrone (+ bandes pour dater les POI) → population, emplois,
    équipements, concurrents (si NAF), générateurs de flux, marché. `geom_geojson` force la géométrie
    (polygone dessiné) et court-circuite l'isochrone. Dégradé honnête si l'isochrone est indisponible."""
    bandes: dict[int, dict] = {}
    surface_ha = None
    if geom_geojson is not None:
        zone = geom_geojson
        statut = "polygone"
        surface_ha = session.execute(text(
            "SELECT round((ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g),4326),2975))/10000)::numeric)"),
            {"g": json.dumps(geom_geojson)}).scalar()
    else:
        res = isochrone(session, lon, lat, minutes, mode, client=client, fetch=fetch)
        statut = res["statut"]
        zone = res["geom_geojson"]
        if zone is None:
            # dégradé honnête et nommé — aucune couche comptée sur un cercle inventé
            return {"statut": statut, "detail": res.get("detail"), "zone_disponible": False,
                    "minutes": minutes, "mode": mode}
        bandes = bandes_isochrones(session, lon, lat, minutes, mode, client=client, fetch=fetch)
    out = {
        "statut": statut, "zone_disponible": True, "minutes": minutes, "mode": mode,
        "surface_ha": int(surface_ha) if surface_ha is not None else None,
        "geom": zone,
        # anneaux concentriques pour la carte (isochrones intermédiaires) — vide en mode polygone
        "bandes": [{"minutes": mn, "geom": g} for mn, g in sorted(bandes.items())],
        "population": population_zone(session, zone),
        # LOT 2 — emplois = tranches d'effectif SIRENE (fourchette), non MOBPRO. Couverture = SIRENE servie.
        "emplois": emplois_zone(session, zone),
        "emplois_couverture": "servie" if _source_peuplee(session, "sirene_etablissements") else "non_couverte",
        "equipements": equipements_proches(session, lon, lat, zone, bandes=bandes),
        "generateurs_flux": generateurs_flux(session, zone),
        "marche": marche_zone(session, zone),
        "zone_demain": zone_demain(session, zone),   # LOT 8 — signal daté (logements autorisés + AU)
        "contraintes_plu": contraintes_plu(session, zone),   # LOT 7 — zones PLU recouvertes (tableau)
        "trafic": trafic_zone(session, zone),        # LOT 5 — trafic RN traversant/bordant la zone
        # ETUDE-ZONE-2 Lot B — enrichissements par section (faits sourcés et datés, jamais une projection)
        "age": age_structure_zone(session, zone),                 # B1 · Population — structure d'âge (IRIS)
        "prix_par_type": prix_par_type_zone(session, zone),       # B3 · Immobilier — €/m² maison/appart/terrain
        "permis_par_type": permis_par_type_zone(session, zone),   # B3 · Immobilier — permis par famille
        "proprietaires_pm": proprietaires_pm_zone(session, zone), # B4 · Foncier — top 5 PM par surface
        "risques": risques_zone(session, zone),                   # B5 · Contraintes — PPR + aléas par niveau
        "assainissement": assainissement_zone(session, zone),     # B5 · Contraintes — collectif vs ANC
        "espaces_zonages": espaces_zonages_zone(session, zone),   # B5 · Contraintes — protégés + fiscaux
        "bpe": equipements_bpe_zone(session, zone, lon, lat, bandes=bandes),  # B6 · Équipements — BPE A→G
        "acquisitions_pm": acquisitions_pm_zone(session, zone),   # B7 · Dynamique — acquisitions PM récentes
        "commune_contexte": commune_contexte_zone(session, zone), # B7 · Dynamique — loyer OLL (commune)
    }
    # DESTINATIONS-1 (X4.1) — verdict de la sous-destination choisie sur chaque zone PLU
    # recouverte : autorisé / sous condition / interdit / en cours de calibration. Lecture
    # UNIQUE via plu.destinations (calibration citée article/page/millésime, CDAC L752-1).
    if sous_destination:
        from .plu.destinations import verdicts_zones_etude
        try:
            out["destinations"] = verdicts_zones_etude(
                out["contraintes_plu"].get("zones", []), sous_destination)
        except ValueError as e:
            out["destinations"] = {"erreur": str(e)}
    # LOT A — concurrents : trois états distincts (servie+0 / non ingérée / erreur), jamais un faux zéro
    if naf:
        if not _source_peuplee(session, "sirene_etablissements"):
            out["concurrents"] = {"couverture": "non_couverte", "naf": naf, "n": 0, "items": []}
        else:
            try:
                c = concurrents_zone(session, zone, naf, bandes=bandes)
                c["couverture"] = "servie"
                # F1 (OUTILS-3) — millésime RÉEL des lignes servies (pas un libellé générique de
                # data_sources, que seed_sources peut clobberer) : le client doit connaître la fraîcheur
                # de ce qu'il lit (une fermeture très récente peut ne pas encore être dans SIRENE).
                c["millesime"] = session.execute(text(
                    "SELECT millesime FROM sirene_etablissements WHERE millesime IS NOT NULL "
                    "ORDER BY ingested_at DESC LIMIT 1")).scalar() or _millesime(
                    "SIRENE établissements géolocalisés", session)
                out["concurrents"] = c
            except Exception as exc:  # noqa: BLE001 — requête en erreur ≠ « 0 résultat »
                out["concurrents"] = {"couverture": "erreur", "naf": naf, "n": 0, "items": [],
                                      "detail": type(exc).__name__}
    return out
