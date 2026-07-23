"""Collecte des données du rapport Flash — une parcelle, sections CONDITIONNELLES.

Même résilience que le moteur de segments (segments/registry) : chaque section détecte
les tables/colonnes disponibles via information_schema et s'omet PROPREMENT sans donnée
— jamais de section vide, jamais d'erreur parce qu'un mandat n'est pas encore mergé.

Le rapport présente les attributs de LA parcelle en valeur ABSOLUE : aucun classement,
aucun percentile île, aucune comparaison multi-parcelles (mandat §2).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.flash")

# Rayons d'analyse (m) — projection locale 2975 (mètres vrais).
RAYON_MARCHE_M = 500
RAYON_PERMIS_M = 500
RAYON_ICPE_M = 500
RAYON_ABF_M = 500          # abords Monuments historiques — même convention que la cascade
FENETRE_MARCHE_ANNEES = 3
FENETRE_PERMIS_MOIS = 24

# Libellés lisibles des kinds spatial_layers utilisés par le rapport.
_KIND_LABELS = {
    "georisque_alea": "Aléa Géorisques",
    "ppr": "Plan de Prévention des Risques (DEAL)",
    "mvt": "Mouvement de terrain (BRGM)",
    "cavite": "Cavité souterraine (BRGM)",
    "sol_pollue": "Sites et sols pollués",
    "bruit_route": "Classement sonore routier",
    "peb": "Plan d'Exposition au Bruit",
    "trait_de_cote": "Recul du trait de côte",
    "cinquante_pas": "50 pas géométriques",
    "abf": "Monument historique / ABF",
    "ens": "Espace Naturel Sensible",
    "qpv": "Quartier Prioritaire de la Ville",
    "friche": "Friche (Cartofriches)",
    "parc_national": "Parc National de La Réunion",
    "foret_publique": "Forêt publique (ONF)",
}

_SOL_POLLUE_LABELS = {"sis": "Secteur d'Information sur les Sols (SIS)",
                      "casias": "Ancien site industriel (CASIAS)",
                      "instruction": "Site en cours d'instruction"}


# ── Disponibilité (pattern segments/registry : information_schema, jamais d'exception) ──

def _existing_tables(db: Session, names: set[str]) -> set[str]:
    rows = db.execute(text(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = 'public' AND table_name = ANY(:n)"
        " UNION SELECT table_name FROM information_schema.views"
        " WHERE table_schema = 'public' AND table_name = ANY(:n)"), {"n": list(names)})
    return {r[0] for r in rows}


def _existing_columns(db: Session, table: str) -> set[str]:
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND table_name = :t"), {"t": table})
    return {r[0] for r in rows}


_NEEDED_TABLES = {
    "parcels", "spatial_layers", "dvf_mutations", "v_parcel_dvf_last",
    "dvf_secteur_medianes", "sitadel_permits", "parcel_terrain", "parcel_residuel",
    "parcel_residuel_bati", "dryrun_parcel_evaluations", "rpls_commune",
    "filosofi_carreaux_200m", "data_sources",
    # Mandats pas encore mergés — le jour où ils atterrissent, la section apparaît seule.
    "parcel_vegetation", "parcel_anc",
}


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


def _i(v: Any) -> int | None:
    return int(round(float(v))) if v is not None else None


# ── Sections ─────────────────────────────────────────────────────────────────────────────

def _parcelle(db: Session, idu: str) -> dict | None:
    row = db.execute(text(
        """SELECT p.idu, p.commune, p.section, p.numero, p.surface_m2,
                  ST_Y(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lat,
                  ST_X(ST_Transform(ST_Centroid(p.geom_2975), 4326)) AS lon,
                  ST_AsGeoJSON(p.geom, 7) AS geojson,
                  round(ST_Area(p.geom_2975)::numeric) AS surface_geom_m2
           FROM parcels p WHERE p.idu = :idu"""), {"idu": idu}).mappings().first()
    if not row:
        return None
    return {
        "idu": row["idu"], "commune": row["commune"], "insee": idu[:5],
        "section": row["section"], "numero": row["numero"],
        "surface_m2": _i(row["surface_m2"]),
        "surface_geom_m2": _i(row["surface_geom_m2"]),
        "lat": round(row["lat"], 6), "lon": round(row["lon"], 6),
        "geojson": row["geojson"],
        # Préfixe commune + section + numéro tels que lus sur un extrait cadastral.
        "reference": f"{idu[:5]} {row['section'] or ''} {row['numero'] or ''}".strip(),
    }


def _identite(db: Session, idu: str, avail: set[str]) -> dict:
    """Zonage PLU + règles calibrées (LA valeur différenciante : calibrage premium fin)."""
    out: dict[str, Any] = {"zones": [], "prescriptions": [], "regles": None}
    if "spatial_layers" in avail:
        zones = db.execute(text(
            """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
               SELECT sl.subtype AS classe, sl.attrs->>'libelle' AS libelle,
                      sl.attrs->>'idurba' AS idurba,
                      round((100 * ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975))
                             / NULLIF(ST_Area(p.geom_2975), 0))::numeric) AS pct
               FROM spatial_layers sl, p
               WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975)
               ORDER BY pct DESC"""), {"idu": idu}).mappings().all()
        out["zones"] = [dict(z) for z in zones if z["pct"] and z["pct"] >= 1]
        presc = db.execute(text(
            """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
               SELECT DISTINCT sl.attrs->>'libelle' AS libelle, sl.attrs->>'txt' AS code
               FROM spatial_layers sl, p
               WHERE sl.kind = 'plu_gpu_prescription'
                 AND ST_Intersects(sl.geom_2975, p.geom_2975)"""),
            {"idu": idu}).mappings().all()
        out["prescriptions"] = [dict(r) for r in presc if r["libelle"]]
    if "parcel_residuel_bati" in avail:
        r = db.execute(text(
            "SELECT zone, emprise_max_m2, hauteur_max_m, confiance FROM parcel_residuel_bati "
            "WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if r and (r["emprise_max_m2"] is not None or r["hauteur_max_m"] is not None):
            out["regles"] = {"zone": r["zone"], "emprise_max_m2": _i(r["emprise_max_m2"]),
                             "hauteur_max_m": _f(r["hauteur_max_m"]), "confiance": r["confiance"]}
    return out


def _constructibilite(db: Session, idu: str, avail: set[str]) -> dict | None:
    out: dict[str, Any] = {}
    if "parcel_residuel_bati" in avail:
        r = db.execute(text(
            "SELECT emprise_batie_m2, hauteur_bati_m, emprise_max_m2, emprise_residuelle_m2, "
            "       hauteur_max_m, surelevation_possible, confiance "
            "FROM parcel_residuel_bati WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if r:
            out["bati"] = {"emprise_batie_m2": _i(r["emprise_batie_m2"]),
                           "hauteur_bati_m": _f(r["hauteur_bati_m"]),
                           "emprise_max_m2": _i(r["emprise_max_m2"]),
                           "emprise_residuelle_m2": _i(r["emprise_residuelle_m2"]),
                           "hauteur_max_m": _f(r["hauteur_max_m"]),
                           "surelevation_possible": r["surelevation_possible"],
                           "confiance": r["confiance"]}
    if "parcel_residuel" in avail:
        r = db.execute(text(
            """SELECT pr.taux_emprise_pct, pr.sdp_residuelle_m2
               FROM parcel_residuel pr JOIN parcels p ON p.id = pr.parcel_id
               WHERE p.idu = :idu"""), {"idu": idu}).mappings().first()
        if r:
            out["residuel"] = {"taux_emprise_pct": _f(r["taux_emprise_pct"]),
                               "sdp_residuelle_m2": _i(r["sdp_residuelle_m2"])}
    if "dryrun_parcel_evaluations" in avail:
        r = db.execute(text(
            """SELECT d.q_score, d.a_score, d.a_completude,
                      (d.status IN ('exclue', 'faux_positif_probable')) AS etage0
               FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
               WHERE p.idu = :idu AND d.run_label = :run"""),
            {"idu": idu, "run": Q_A_RUN_LABEL}).mappings().first()
        if r and r["q_score"] is not None:
            seuils = config.load_yaml_config("scoring_matrice").get("seuils", {})
            # Score en valeur ABSOLUE + grille de lecture — jamais de classement (mandat §2).
            out["score"] = {"q": r["q_score"], "a": r["a_score"],
                            "completude": r["a_completude"],
                            "grille": {"q_seuil": seuils.get("q_chaude", 65),
                                       "a_seuil": seuils.get("a_chaude", 60),
                                       "q_faible": seuils.get("q_ecartee", 50)}}
        # M6 2a (P0 « une seule vérité ») : verdict v2 EN PREMIER — même doctrine que la
        # fiche et pdf_premium (le tier v2 pilote, l'étage 0 du run SERVI prime) ; la
        # grille matrice Q/A ci-dessus est reléguée en complément « historique ».
        etage0 = bool(r["etage0"]) if r else False
        v2 = None
        if db.execute(text("SELECT to_regclass('p_score_v2_runs') IS NOT NULL")).scalar():
            v2 = db.execute(text(
                """SELECT s2.tier, s2.rang, s2.mult_base
                   FROM parcel_p_score_v2 s2
                   WHERE s2.parcelle_id = :idu
                     AND s2.run_id = (SELECT run_id FROM p_score_v2_runs
                                      ORDER BY computed_at DESC LIMIT 1)"""),
                {"idu": idu}).mappings().first()
        if v2 or etage0:
            libelles = {"brulante": "Brûlante", "chaude": "Chaude",
                        "reserve_fonciere": "Réserve foncière", "a_creuser": "À creuser",
                        "ecartee": "Écartée"}
            tier_eff = "ecartee" if etage0 else (v2["tier"] if v2 else None)
            if tier_eff:
                out["verdict_v2"] = {
                    "tier": tier_eff, "libelle": libelles.get(tier_eff, tier_eff),
                    "etage0": etage0,
                    "rang": (None if etage0 or not v2 else v2["rang"]),
                    "mult": (None if etage0 or not v2 or v2["mult_base"] is None
                             else round(float(v2["mult_base"]), 1))}
    return out or None


def _risques(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "spatial_layers" not in avail:
        return None
    kinds = ["georisque_alea", "ppr", "mvt", "cavite", "sol_pollue", "bruit_route",
             "peb", "trait_de_cote", "cinquante_pas"]
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT DISTINCT sl.kind, sl.subtype, sl.name
           FROM spatial_layers sl, p
           WHERE sl.kind = ANY(:kinds) AND ST_Intersects(sl.geom_2975, p.geom_2975)"""),
        {"idu": idu, "kinds": kinds}).mappings().all()
    items = []
    for r in rows:
        detail = r["name"] or r["subtype"] or ""
        if r["kind"] == "sol_pollue":
            detail = _SOL_POLLUE_LABELS.get((r["subtype"] or "").lower(), detail)
        elif r["kind"] == "bruit_route":
            detail = f"catégorie {r['subtype'].removeprefix('cat')}" if r["subtype"] else detail
        elif r["kind"] == "ppr":
            detail = f"{(r['subtype'] or '').capitalize()} — {r['name']}" if r["name"] else (r["subtype"] or "")
        elif r["name"]:
            detail = r["name"]          # le libellé porte déjà l'aléa — pas de doublon subtype
        items.append({"kind": r["kind"], "label": _KIND_LABELS.get(r["kind"], r["kind"]),
                      "detail": detail})
    icpe = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sl.name, sl.subtype AS regime,
                  round(ST_Distance(sl.geom_2975, p.geom_2975))::int AS dist_m
           FROM spatial_layers sl, p
           WHERE sl.kind = 'icpe' AND ST_DWithin(sl.geom_2975, p.geom_2975, :r)
           ORDER BY dist_m LIMIT 5"""),
        {"idu": idu, "r": RAYON_ICPE_M}).mappings().all()
    return {"couches": sorted(items, key=lambda x: x["label"]),
            "icpe": [dict(r) for r in icpe]} if (items or icpe) else {"couches": [], "icpe": [],
                                                                       "rien": True}


def _patrimoine(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "spatial_layers" not in avail:
        return None
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT DISTINCT sl.kind, sl.subtype, sl.name
           FROM spatial_layers sl, p
           WHERE sl.kind = ANY(ARRAY['ens', 'qpv', 'friche', 'parc_national', 'foret_publique'])
             AND ST_Intersects(sl.geom_2975, p.geom_2975)"""), {"idu": idu}).mappings().all()
    items = [{"kind": r["kind"], "label": _KIND_LABELS.get(r["kind"], r["kind"]),
              "detail": r["name"] or r["subtype"] or ""} for r in rows]
    # ABF : abords Monuments historiques ~500 m (même convention que la cascade).
    abf = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sl.name, round(ST_Distance(sl.geom_2975, p.geom_2975))::int AS dist_m
           FROM spatial_layers sl, p
           WHERE sl.kind = 'abf' AND ST_DWithin(sl.geom_2975, p.geom_2975, :r)
           ORDER BY dist_m LIMIT 3"""),
        {"idu": idu, "r": RAYON_ABF_M}).mappings().all()
    return {"couches": sorted(items, key=lambda x: x["label"]), "abf": [dict(r) for r in abf],
            "rien": not (items or abf)}


def _marche(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "dvf_mutations" not in avail:
        return None
    stats = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT count(*) AS n,
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY dm.valeur_fonciere
                      / NULLIF(dm.surface_reelle_bati, 0))
                      FILTER (WHERE dm.surface_reelle_bati >= 20) AS med_m2_bati,
                  percentile_cont(0.5) WITHIN GROUP (ORDER BY dm.valeur_fonciere
                      / NULLIF(dm.surface_terrain, 0))
                      FILTER (WHERE dm.surface_terrain >= 100
                              AND COALESCE(dm.surface_reelle_bati, 0) < 20) AS med_m2_terrain
           FROM dvf_mutations dm, p
           WHERE dm.geom IS NOT NULL
             AND dm.date_mutation >= (CURRENT_DATE - make_interval(years => :annees))
             AND dm.nature_mutation ILIKE 'vente%'
             AND dm.valeur_fonciere > 0
             AND ST_DWithin(ST_Transform(dm.geom, 2975), p.geom_2975, :r)"""),
        {"idu": idu, "annees": FENETRE_MARCHE_ANNEES, "r": RAYON_MARCHE_M}).mappings().first()
    if not stats or not stats["n"]:
        return {"n": 0, "rien": True, "rayon_m": RAYON_MARCHE_M, "annees": FENETRE_MARCHE_ANNEES}
    # Comparables ANONYMISÉS : type, surface, prix, mois — JAMAIS d'adresse exacte (mandat).
    comps = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT dm.type_local, dm.surface_reelle_bati, dm.surface_terrain,
                  dm.valeur_fonciere, to_char(dm.date_mutation, 'MM/YYYY') AS mois
           FROM dvf_mutations dm, p
           WHERE dm.geom IS NOT NULL
             AND dm.date_mutation >= (CURRENT_DATE - make_interval(years => :annees))
             AND dm.nature_mutation ILIKE 'vente%'
             AND dm.valeur_fonciere > 0 AND dm.type_local IS NOT NULL
             AND ST_DWithin(ST_Transform(dm.geom, 2975), p.geom_2975, :r)
           ORDER BY dm.date_mutation DESC LIMIT 5"""),
        {"idu": idu, "annees": FENETRE_MARCHE_ANNEES, "r": RAYON_MARCHE_M}).mappings().all()
    out = {"n": int(stats["n"]), "rayon_m": RAYON_MARCHE_M, "annees": FENETRE_MARCHE_ANNEES,
           "med_m2_bati": _i(stats["med_m2_bati"]), "med_m2_terrain": _i(stats["med_m2_terrain"]),
           "comparables": [dict(c) for c in comps], "derniere_mutation": None, "secteur": []}
    if "v_parcel_dvf_last" in avail:
        last = db.execute(text(
            "SELECT date_mutation, nature, valeur, prix_m2_bati, prix_m2_terrain "
            "FROM v_parcel_dvf_last WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if last:
            dm = last["date_mutation"]
            out["derniere_mutation"] = {**dict(last),
                                        "date": dm.isoformat()[:10] if dm else None}
    if "dvf_secteur_medianes" in avail:
        sect = db.execute(text(
            "SELECT type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre "
            "FROM dvf_secteur_medianes WHERE secteur = substring(:idu FROM 1 FOR 10) "
            "ORDER BY n_ventes DESC"), {"idu": idu}).mappings().all()
        out["secteur"] = [dict(s) for s in sect]
    return out


def _dynamique(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "sitadel_permits" not in avail:
        return None
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sp.type, to_char(sp.date, 'MM/YYYY') AS mois,
                  NULLIF(sp.raw->>'nb_lgt', '')::int AS nb_lgt,
                  sp.raw->>'famille' AS famille
           FROM sitadel_permits sp, p
           WHERE sp.geom IS NOT NULL
             AND sp.date >= (CURRENT_DATE - make_interval(months => :mois))
             AND ST_DWithin(ST_Transform(sp.geom, 2975), p.geom_2975, :r)
           ORDER BY nb_lgt DESC NULLS LAST"""),
        {"idu": idu, "mois": FENETRE_PERMIS_MOIS, "r": RAYON_PERMIS_M}).mappings().all()
    if not rows:
        return {"n": 0, "rien": True, "rayon_m": RAYON_PERMIS_M, "mois": FENETRE_PERMIS_MOIS}
    total_lgt = sum(r["nb_lgt"] or 0 for r in rows)
    return {"n": len(rows), "rayon_m": RAYON_PERMIS_M, "mois": FENETRE_PERMIS_MOIS,
            "total_logements": total_lgt,
            "plus_gros": [dict(r) for r in rows[:3] if (r["nb_lgt"] or 0) > 0]}


def _terrain(db: Session, idu: str, avail: set[str]) -> dict | None:
    out: dict[str, Any] = {}
    if "parcel_terrain" in avail:
        r = db.execute(text(
            "SELECT pente_moy_deg, pente_max_deg, flag_terrassement_lourd "
            "FROM parcel_terrain WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if r and r["pente_moy_deg"] is not None:
            out["pente"] = {"moy_deg": round(float(r["pente_moy_deg"]), 1),
                            "max_deg": round(float(r["pente_max_deg"]), 1)
                            if r["pente_max_deg"] is not None else None,
                            "terrassement_lourd": bool(r["flag_terrassement_lourd"])}
    # Mandats futurs (ANC & Végétation) : colonnes déclarées par le registre des
    # segments — la sous-section apparaît TOUTE SEULE le jour où la table est mergée.
    if "parcel_anc" in avail and {"zone_anc"} <= _existing_columns(db, "parcel_anc"):
        r = db.execute(text("SELECT zone_anc FROM parcel_anc WHERE idu = :idu"),
                       {"idu": idu}).mappings().first()
        if r:
            out["anc"] = {"zone_anc": bool(r["zone_anc"])}
    if "parcel_vegetation" in avail and {"ombrage_pct"} <= _existing_columns(db, "parcel_vegetation"):
        r = db.execute(text("SELECT ombrage_pct FROM parcel_vegetation WHERE idu = :idu"),
                       {"idu": idu}).mappings().first()
        if r and r["ombrage_pct"] is not None:
            out["canopee"] = {"ombrage_pct": _i(r["ombrage_pct"])}
    return out or None


# ── Sources & millésimes (page argument de vente, pas une annexe — mandat §3.9) ──────────

# section rendue -> [(id data_sources, complément de millésime statique)]
_SECTION_SOURCES: list[tuple[str, str, int | None, str | None]] = [
    # (clé section, libellé source si data_sources indisponible, ds_id, millésime statique)
    ("identite", "Cadastre Etalab (DGFiP)", 2, None),
    ("identite", "PLU / GPU (API Carto, IGN)", 3, None),
    ("identite", "Droits résiduels — calibrage LABUSE sur règlements PLU", None,
     "calibrage continu 2026"),
    ("risques", "Géorisques (BRGM / MTE)", 4, None),
    ("risques", "Géorisques — sites et sols pollués", 32, None),
    ("risques", "Géorisques — cavités souterraines", 33, None),
    ("risques", "Géorisques — ICPE", 34, None),
    ("risques", "Géorisques — mouvements de terrain", 36, None),
    ("risques", "PPR / aléas (DEAL Réunion)", 30, None),
    ("risques", "Classement sonore ITT (Cerema)", 46, None),
    ("risques", "Recul du trait de côte (Cerema / GéoLittoral)", 28, None),
    ("risques", "50 pas géométriques (DEAL)", 47, None),
    ("patrimoine", "Base Mérimée / ABF (Ministère de la Culture)", 24, None),
    ("patrimoine", "ENS (INPN / Département)", 25, None),
    ("patrimoine", "QPV 2024 (ANCT)", 38, None),
    ("patrimoine", "Cartofriches (Cerema)", 35, None),
    ("patrimoine", "Parc National de La Réunion (INPN)", 7, None),
    ("marche", "DVF — valeurs foncières (DGFiP / Cerema)", 5, None),
    ("dynamique", "Sitadel — autorisations d'urbanisme (SDES)", 16, None),
    ("terrain", "RGE ALTI 5 m (IGN)", 6, None),
    ("carte", "Fond de carte © OpenStreetMap contributors (ODbL)", 19, None),
    ("adresse", "Base Adresse Nationale (DINUM / IGN)", 18, None),
]


def _sources(db: Session, avail: set[str], sections_rendues: set[str]) -> list[dict]:
    sync: dict[int, str] = {}
    if "data_sources" in avail:
        for r in db.execute(text(
                "SELECT id, last_sync_at FROM data_sources WHERE last_sync_at IS NOT NULL")):
            sync[r[0]] = r[1].date().isoformat()
    out, vus = [], set()
    for section, label, ds_id, statique in _SECTION_SOURCES:
        if section not in sections_rendues or label in vus:
            continue
        vus.add(label)
        millesime = statique or (sync.get(ds_id) and f"synchronisé le {sync[ds_id]}") or "—"
        out.append({"section": section, "source": label, "millesime": millesime})
    return out


_SECTION_LABELS = {"identite": "Identité parcellaire", "constructibilite": "Constructibilité",
                   "risques": "Risques", "patrimoine": "Patrimoine & environnement",
                   "marche": "Marché", "dynamique": "Dynamique locale",
                   "terrain": "Terrain & réseaux", "carte": "Carte de situation",
                   "adresse": "Adresse"}


# ── Point d'entrée ───────────────────────────────────────────────────────────────────────

def collect_report_data(db: Session, idu: str, adresse: str | None = None) -> dict:
    """Assemble toutes les sections du rapport pour UNE parcelle.

    Lève ValueError si la parcelle est inconnue ; toute autre absence de donnée se traduit
    par une section None (le template l'omet proprement). M6 2a : si aucune adresse n'est
    fournie par l'appelant, l'adresse postale BAN rattachée en base est utilisée.
    """
    avail = _existing_tables(db, _NEEDED_TABLES)
    if "parcels" not in avail:
        raise RuntimeError("Table parcels absente — base non initialisée.")
    parcelle = _parcelle(db, idu)
    if not parcelle:
        raise ValueError(f"Parcelle {idu} inconnue.")
    if adresse is None:
        # import paresseux (évite tout cycle flash ↔ api au chargement des modules)
        from ..api.export_commun import adresse_ban_texte
        adresse = adresse_ban_texte(db, idu)

    data: dict[str, Any] = {
        "parcelle": parcelle,
        "adresse": adresse,
        "identite": _identite(db, idu, avail),
        "constructibilite": _constructibilite(db, idu, avail),
        "risques": _risques(db, idu, avail),
        "patrimoine": _patrimoine(db, idu, avail),
        "marche": _marche(db, idu, avail),
        "dynamique": _dynamique(db, idu, avail),
        "terrain": _terrain(db, idu, avail),
        "date_generation": date.today().isoformat(),
    }
    rendues = {k for k in ("identite", "constructibilite", "risques", "patrimoine",
                           "marche", "dynamique", "terrain") if data.get(k)}
    if adresse:
        rendues.add("adresse")
    data["sources"] = _sources(db, avail, rendues | {"carte"})
    data["section_labels"] = _SECTION_LABELS
    return data
