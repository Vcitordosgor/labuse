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
    row = session.execute(text("SELECT ST_AsGeoJSON(geom) AS gj FROM zone_isochrone_cache WHERE cache_key = :k"),
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
    return {
        "inhabitee": False,
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


def emplois_communes(session: Session, geom_geojson: dict) -> list[dict]:
    """MOBPRO — « N actifs y travaillent », maille COMMUNE (dit comme tel). On identifie les communes
    dont une parcelle a son centroïde dans la zone, puis on joint l'agrégat d'emplois. Pas de prorata :
    le chiffre est celui de la commune entière, jamais une fausse précision zonale."""
    communes = session.execute(text(
        f"""SELECT DISTINCT p.commune
            FROM parcels p
            WHERE ST_Contains({_zone2975()}, ST_Transform(p.centroid, 2975))"""),
        {"zone": json.dumps(geom_geojson)}).scalars().all()
    out = []
    for commune in communes:
        r = session.execute(text(
            """SELECT m.emplois_lieu_travail AS e, m.millesime
               FROM commune_insee_logement c JOIN mobpro_commune m ON m.insee = c.insee
               WHERE c.commune = :c LIMIT 1"""), {"c": commune}).mappings().first()
        if r and r["e"]:
            out.append({"commune": commune, "actifs_lieu_travail": int(r["e"]),
                        "millesime": r["millesime"] or "MOBPRO (INSEE)"})
    out.sort(key=lambda x: -x["actifs_lieu_travail"])
    return out


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


def concurrents_zone(session: Session, geom_geojson: dict, naf: str, *, bandes: dict[int, dict],
                     maxi: int = 40) -> dict:
    """Établissements SIRENE du NAF dans la zone (concurrents). Nom masqué si non diffusible. Chaque
    « plus proche » porte son TEMPS (plus petite bande le contenant), jamais une distance en mètres."""
    rows = session.execute(text(
        f"""SELECT siret, naf, denomination, enseigne, diffusible,
                   extract(year FROM date_creation)::int AS annee_creation,
                   ST_X(geom) AS lon, ST_Y(geom) AS lat
            FROM sirene_etablissements
            WHERE naf = :naf AND actif AND ST_Contains({_zone2975()}, ST_Transform(geom, 2975))
            LIMIT :maxi"""),
        {"zone": json.dumps(geom_geojson), "naf": naf, "maxi": maxi}).mappings().all()
    items = []
    for r in rows:
        # A3-bis (OUTILS-2) — enseigne PUIS dénomination (masqué si non diffusible) ; `annee_creation`
        # (SIRENE dateCreationEtablissement) sert le « depuis AAAA » de la fiche. Jamais inventée : null
        # possible (établissement sans date renseignée à la source).
        nom = (r["enseigne"] or r["denomination"]) if r["diffusible"] else None
        items.append({
            "siret": r["siret"], "naf": r["naf"],
            "nom": nom or "Établissement (nom non diffusé)",
            "annee_creation": r["annee_creation"],
            "diffusible": r["diffusible"], "lon": r["lon"], "lat": r["lat"],
            "temps_min": _bande_min(session, r["lon"], r["lat"], bandes),
        })
    items.sort(key=lambda x: (x["temps_min"] is None, x["temps_min"] or 999))
    # F1 (OUTILS-3) — libellé NAF LISIBLE (« Boulangerie et boulangerie-pâtisserie ») servi à côté du
    # code brut « 1071C » : le code reste, mais l'humain lit l'activité. Source unique : naf_labels.
    from .naf_labels import label as _naf_label
    return {"n": len(items), "naf": naf, "naf_label": _naf_label(naf), "items": items}


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
    if _existe("dvf_mutations_parcelle") and _existe("parcels"):
        ventes = session.execute(text(
            f"""SELECT count(*) FROM dvf_mutations_parcelle d JOIN parcels p ON p.idu = d.id_parcelle
                WHERE d.date_mutation >= (now() - interval '12 months')
                  AND ST_Contains({z}, ST_Transform(p.centroid, 2975))"""), p).scalar()
        prix = session.execute(text(
            f"""SELECT round(percentile_cont(0.5) WITHIN GROUP (
                      ORDER BY d.valeur_fonciere / NULLIF(d.surface_reelle_bati, 0))::numeric)
                FROM dvf_mutations_parcelle d JOIN parcels p ON p.idu = d.id_parcelle
                WHERE d.date_mutation >= (now() - interval '36 months')
                  AND d.valeur_fonciere > 0 AND coalesce(d.surface_reelle_bati, 0) > 0
                  AND ST_Contains({z}, ST_Transform(p.centroid, 2975))"""), p).scalar()
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
    return {"ventes_12m": int(ventes or 0),
            "prix_m2_median_bati": int(prix) if prix is not None else None,
            "annonces_actives": int(annonces or 0),
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
    rows = session.execute(text(
        f"""SELECT coalesce(l.subtype, l.attrs->>'libelle', '?') AS zone,
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


def etude_de_zone(session: Session, lon: float, lat: float, minutes: int, mode: str, *,
                  geom_geojson: dict | None = None, naf: str | None = None,
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
    }
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
