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

from ..scoring.score_v_constants import Q_A_RUN_LABEL

log = logging.getLogger("labuse.flash")

# Rayons d'analyse (m) — projection locale 2975 (mètres vrais).
# MANDAT_DVF-B — le rayon/fenêtre DVF (profil secteur_dossier) vient de config/dvf_profils.yaml : plus
# aucun rayon/fenêtre DVF en dur. Lu au chargement (valeurs identiques → golden stable) ; le 500/3 n'est
# qu'un repli prudent si la config est absente. Les rayons PERMIS/ICPE ne sont pas des lectures DVF.
def _dvf_secteur_cfg() -> tuple[int, int]:
    try:
        from ..marche_service import profil_meta
        m = profil_meta("secteur_dossier")
        return int(m["rayon_m"]), int(m["fenetre_ans"])
    except Exception:  # noqa: BLE001 — config absente = repli, jamais un crash
        return 500, 3


RAYON_MARCHE_M, FENETRE_MARCHE_ANNEES = _dvf_secteur_cfg()


def _reserve_dvf() -> str:
    """MANDAT_DVF-B — la réserve de méthode DVF (helper UNIQUE marche_service.reserve_methode)."""
    try:
        from ..marche_service import reserve_methode
        return reserve_methode()
    except Exception:  # noqa: BLE001
        return ""
RAYON_PERMIS_M = 500
RAYON_ICPE_M = 500
FENETRE_PERMIS_MOIS = 24

# M73 — libellés client des COUCHES de la cascade servie (par layer_name). Le DÉTAIL de chaque
# ligne est déjà arbitré/libellé par served_cascade ; seul le libellé de couche est dérivé ici.
_LAYER_LABELS = {
    "risques": "Aléa / PPR (Géorisques · DEAL)",
    "sol_pollue": "Sites et sols pollués",
    "cavite": "Cavité souterraine (BRGM)",
    "icpe": "Installation classée (ICPE)",
    "mvt": "Mouvement de terrain (BRGM)",
    "pente": "Pente du terrain",
    "ravine": "Voisinage de ravine",
    "trait_de_cote": "Recul du trait de côte",
    "eau": "Hydrographie",
    "bruit_route": "Classement sonore routier",
    "cinquante_pas": "50 pas géométriques",
    "abf": "Monument historique / ABF",
    "ens": "Espace Naturel Sensible",
    "qpv": "Quartier Prioritaire de la Ville",
    "friche": "Friche (Cartofriches)",
    "parc_national": "Parc National de La Réunion",
    "foret_publique": "Forêt publique (ONF)",
}


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
    # M18 enrichissement Flash — contexte commune (chacune détectée, section omise si absente)
    "m10_permit_delais", "commune_contexte_sru", "commune_conso_enaf", "parcel_solar",
    # Mandats pas encore mergés — le jour où ils atterrissent, la section apparaît seule.
    "parcel_vegetation", "parcel_anc",
    # M75 — obligation APER (grand parking) : section omise si la table est absente.
    "parkings_aper",
    # M73 §F — faisceau de viabilisation (réseaux) dans « Terrain & réseaux ».
    "parcel_viabilisation",
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
    out: dict[str, Any] = {"zones": [], "prescriptions": [], "regles": None,
                           "zonage_verdict": None}
    # M73 « le dryrun servi fait foi » : le VERDICT de constructibilité du zonage vient de la ligne
    # SERVIE 'zonage_plu_gpu' (onglet 'regles'), arbitrée et libellée — jamais recalculé ici. Le
    # libellé de zone (A/U/RNU…) et la part de recouvrement restent lus en direct dans spatial_layers
    # (détail d'affichage non porté par le servi).
    from ..api.served_cascade import served_cascade_lines, served_group
    zline = next((l for l in served_group(served_cascade_lines(db, idu), "regles")
                  if l["layer_name"] == "zonage_plu_gpu"), None)
    if zline:
        out["zonage_verdict"] = {"result": zline["result"], "detail": zline["detail"]}
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
               WHERE p.idu = :idu AND pr.cause IS NULL"""), {"idu": idu}).mappings().first()
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
        # M-P (P2-67) : la grille matrice Q/A (out["score"], seuils scoring_matrice) est RETIRÉE du
        # Flash — document VENDU 79 €, l'acheteur n'a aucun contexte pour arbitrer un second verdict
        # issu d'un rail éteint (M37). Un seul verdict : le tier v2 (out["verdict_v2"]) ci-dessous.
        # M6 2a (P0 « une seule vérité ») : verdict v2 — le tier v2 pilote, l'étage 0 du run SERVI prime.
        etage0 = bool(r["etage0"]) if r else False
        v2 = None
        # M-L (P1-15) : sur la page de garde du Flash (document VENDU 79 €), le tier v2 est ÉPINGLÉ
        # au run SERVI (Q_A_RUN_LABEL) — EXACTEMENT le même run que l'étage 0 lu quelques lignes plus
        # haut (`d.run_label = Q_A_RUN_LABEL`). Plus jamais « le dernier run calculé » : sinon le
        # rapport mélangeait l'étage 0 du run servi et le tier v2 d'un run CANDIDAT non arbitré
        # (deux verdicts, un faux). Les deux DOIVENT lire le même run. Le garde `to_regclass` reste
        # la résilience propre du Flash (rail v2 pas déployé → section omise, jamais d'erreur) ; la
        # garantie « run servi matérialisé » est portée en amont par /readyz (state.served_run_status).
        if db.execute(text("SELECT to_regclass('p_score_v2_runs') IS NOT NULL")).scalar():
            v2 = db.execute(text(
                """SELECT s2.tier, s2.rang, s2.mult_base
                   FROM parcel_p_score_v2 s2
                   WHERE s2.parcelle_id = :idu AND s2.run_id = :run"""),
                {"idu": idu, "run": Q_A_RUN_LABEL}).mappings().first()
        if v2 or etage0:
            # M54-AB C1 : libellé CLIENT + motif = POINT DE TRADUCTION UNIQUE (verdict_servi),
            # jamais une table recopiée dans le générateur (l'ancienne, incomplète, laissait
            # « declasse_bati_sature » brut fuir au client). + dénominateur du rang.
            from ..verdict_servi import TIER_LABELS, verdict_servi, rang_total
            tier_eff = "ecartee" if etage0 else (v2["tier"] if v2 else None)
            if tier_eff:
                vs = verdict_servi(db, idu)
                out["verdict_v2"] = {
                    "tier": tier_eff, "libelle": TIER_LABELS.get(tier_eff, tier_eff),
                    "etage0": etage0,
                    "declasse": tier_eff.startswith("declasse_"),
                    # motif servi (« pourquoi ») — même phrase que l'écran ; jamais sur l'étage 0
                    # (l'exclusion dure a sa propre note ci-dessous).
                    "motif": (None if etage0 else vs.get("motif")),
                    "rang": (None if etage0 or not v2 else v2["rang"]),
                    "rang_total": (None if etage0 or not v2 else rang_total(db)),
                    "mult": (None if etage0 or not v2 or v2["mult_base"] is None
                             else round(float(v2["mult_base"]), 1))}
        # M-RENOUV (B3) : UNE ligne conditionnelle dans la synthèse — segment + rang +
        # les 2 composantes dominantes. Pas de refonte du template ; wording doctrinal
        # (« potentiel de renouvellement urbain », jamais « opportunité »).
        if db.execute(text("SELECT to_regclass('parcel_renouvellement') IS NOT NULL")).scalar():
            rn = db.execute(text(
                "SELECT renouv_score, rang_segment, comp_potentiel, comp_assiette, "
                "       comp_marche, comp_divisibilite, "
                "       (SELECT count(*) FROM parcel_renouvellement) AS total "
                "FROM parcel_renouvellement WHERE idu = :idu"), {"idu": idu}).mappings().first()
            if rn:
                from ..renouvellement import LIBELLES_COMPOSANTES
                dominantes = sorted(
                    ((k, int(rn[k])) for k in ("comp_potentiel", "comp_assiette",
                                               "comp_marche", "comp_divisibilite")),
                    key=lambda kv: kv[1], reverse=True)[:2]
                dom = " · ".join(f"{LIBELLES_COMPOSANTES[k]} ({v} pts)" for k, v in dominantes)
                out["renouvellement_ligne"] = (
                    f"Segment Renouvellement — parcelle occupée, potentiel de renouvellement "
                    f"urbain : rang {rn['rang_segment']}/{rn['total']} "
                    f"(score {rn['renouv_score']}/100). Composantes dominantes : {dom}.")
        # MANDAT RNU (B3) : étiquetage export — UNE ligne conditionnelle, flag commune-level
        # général (config/rnu_communes.yaml). Jamais d'affirmation de constructibilité RNU.
        from .. import rnu as _rnu
        blk = _rnu.rnu_block(idu, db)
        if blk:
            pau_txt = {True: " Parcelle DANS l'enveloppe urbanisée estimée.",
                       False: " Parcelle HORS de l'enveloppe urbanisée estimée.",
                       None: ""}[blk["dans_pau"]]
            out["rnu_ligne"] = (f"{blk['libelle']}. {blk['detail']}{pau_txt} "
                                f"{blk['avertissement_pau']} "
                                f"(statut vérifié le {blk['verifie_le']}).")
    # Constructibilité (déclassement tête-de-liste) — motif AFFICHÉ dès qu'un verdict moteur
    # existe, INDÉPENDAMMENT du tier servi : le défaut « tête de liste non constructible » est
    # signalé sur la fiche même AVANT la bascule du run avec déclassement. Trois motifs distincts
    # (A zone fermée / B parcelle inconstructible / C non vérifiable).
    if db.execute(text("SELECT to_regclass('parcel_constructibilite') IS NOT NULL")).scalar():
        cst = db.execute(text(
            "SELECT c.label, c.motif FROM parcel_constructibilite c "
            "JOIN parcels p ON p.id = c.parcel_id WHERE p.idu = :idu"),
            {"idu": idu}).mappings().first()
        if cst:
            out["constructibilite"] = {"label": cst["label"], "motif": cst["motif"]}
    # AU-OUVERTURE (Vic 30/07) — statut d'ouverture de la zone AU, LU INDÉPENDAMMENT du tier servi
    # (comme la constructibilité) → le motif SURVIT à la bascule et reste consultable AVANT elle.
    # Deux traitements selon la classe :
    #   · dimensions-seules (servie) : la mention se place EN TÊTE, dans le bloc VERDICT (exigence
    #     Vic « la mention doit être vue ») — jamais reléguée en bas de fiche.
    #   · générique (déclassée) : motif dédié, toujours consultable (bloc `au_statut`) ; après
    #     bascule le tier devient `declasse_au_statut_inconnu` et le libellé le porte aussi en tête.
    if db.execute(text("SELECT to_regclass('parcel_au_statut') IS NOT NULL")).scalar():
        au = db.execute(text(
            "SELECT a.classe, a.motif FROM parcel_au_statut a "
            "JOIN parcels p ON p.id = a.parcel_id WHERE p.idu = :idu"),
            {"idu": idu}).mappings().first()
        if au:
            out["au_statut"] = {"classe": au["classe"], "motif": au["motif"], "source": "Absent"}
            if isinstance(out.get("verdict_v2"), dict):
                # mention/motif remonté EN TÊTE (bloc VERDICT), vu avant tout le reste de la fiche.
                out["verdict_v2"]["mention_ouverture"] = au["motif"]
    return out or None


# M73 — layers de l'onglet 'risques' présentés en section Risques (aléas/PPR/mvt/cavité/sol
# pollué/ICPE/pente/ravine/trait de côte/eau). ABF & ENS sont traités par _patrimoine.
_RISQUE_LAYERS = {"risques", "sol_pollue", "cavite", "icpe", "mvt", "pente", "ravine",
                  "trait_de_cote", "eau", "bruit_route", "cinquante_pas"}


def _risques(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "spatial_layers" not in avail:
        return None
    # M73 « le dryrun servi fait foi » : les couches de risque viennent des lignes SERVIES
    # (dédupliquées + arbitrées + libellées) — un seul niveau d'aléa (le plus contraignant),
    # PPR réglementaire sans « intersection marginale < 10 % », libellés FR propres. Fini les
    # 3 niveaux d'aléa côte à côte lus en direct dans spatial_layers.
    from ..api.served_cascade import served_cascade_lines, served_group
    lines = served_group(served_cascade_lines(db, idu), "risques")
    items = []
    for l in lines:
        if l["layer_name"] not in _RISQUE_LAYERS:
            continue
        if l["result"] not in ("HARD_EXCLUDE", "SOFT_FLAG"):
            continue
        items.append({"kind": l["layer_name"],
                      "label": _LAYER_LABELS.get(l["layer_name"], l["layer_name"]),
                      "detail": l["detail"]})
    # Liste ICPE-proximité (5 plus proches, ST_Distance) : DÉTAIL non porté par le servi (une seule
    # ligne ICPE arbitrée) — conservée telle quelle (spatial_layers), pas une contradiction.
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
    # ENS/QPV/friche/parc_national/foret_publique : DÉTAIL (nom de périmètre) non porté par le servi
    # → conservés en lecture directe spatial_layers.
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT DISTINCT sl.kind, sl.subtype, sl.name
           FROM spatial_layers sl, p
           WHERE sl.kind = ANY(ARRAY['ens', 'qpv', 'friche', 'parc_national', 'foret_publique'])
             AND ST_Intersects(sl.geom_2975, p.geom_2975)"""), {"idu": idu}).mappings().all()
    items = [{"kind": r["kind"], "label": _LAYER_LABELS.get(r["kind"], r["kind"]),
              "detail": r["name"] or r["subtype"] or ""} for r in rows]
    # M73 « le dryrun servi fait foi » : l'ABF vient de la LIGNE SERVIE (result/detail), plus de
    # ST_Distance à un tampon 500 m → fini le « 0 m » (distance-à-tampon). La couche ABF = tampons
    # + endpoint décommissionné M74 : on ne re-source pas, on cesse d'afficher une distance-à-tampon.
    from ..api.served_cascade import served_cascade_lines, served_group
    abf_note = next((l["detail"] for l in served_group(served_cascade_lines(db, idu), "risques")
                     if l["layer_name"] == "abf" and l["result"] in ("HARD_EXCLUDE", "SOFT_FLAG",
                                                                      "UNKNOWN")), None)
    return {"couches": sorted(items, key=lambda x: x["label"]), "abf_note": abf_note,
            "rien": not (items or abf_note)}


def _marche(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "dvf_mutations" not in avail:
        return None
    # M54-AB C5 : bloc Marché COMMUNE (M-U) condensé — prix ancien, tendance, liquidité, chacun DATÉ.
    # Calculé en tête pour figurer même sans comparable de proximité ; les comparables restent.
    commune_marche: list = []
    commune = db.execute(text("SELECT commune FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if commune:
        from ..api.marche_bloc import bloc_condense
        commune_marche = bloc_condense(db, commune, ["prix_ancien_median", "tendance_12m", "liquidite"])
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
        return {"n": 0, "rien": True, "rayon_m": RAYON_MARCHE_M, "annees": FENETRE_MARCHE_ANNEES,
                "commune_marche": commune_marche, "reserve": _reserve_dvf()}
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
           "comparables": [dict(c) for c in comps], "derniere_mutation": None, "secteur": [],
           # M-P (P2-66) : étiquette de MÉTHODE — ce bloc est un indicateur de marché LOCAL (tous
           # types, rayon fixe, sans exclusion d'aberrants), DISTINCT du prix de sortie du bilan
           # (sector_price : appartements, rayon adaptatif 500→1500→commune, aberrants exclus).
           # Les deux médianes peuvent légitimement différer — la méthode l'explique, jamais un écart nu.
           "methode": (f"Médiane €/m² observée, tous types de biens, rayon {RAYON_MARCHE_M} m sur "
                       f"{FENETRE_MARCHE_ANNEES} ans, sans exclusion d'aberrants — indicateur de marché "
                       "local, distinct du prix de sortie du bilan (appartements, rayon adaptatif, "
                       "aberrants exclus)."),
           # MANDAT_DVF-B — la réserve de méthode DVF voyage avec le chiffre (helper unique).
           "reserve": _reserve_dvf()}
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
    out["commune_marche"] = commune_marche
    return out


def _dynamique(db: Session, idu: str, avail: set[str]) -> dict | None:
    if "sitadel_permits" not in avail:
        return None
    # Compte + logements : agrégats SQL (COUNT/SUM) sur toute la fenêtre — jamais une matérialisation
    # de toutes les lignes côté Python. n et total_logements restent donc EXACTS.
    agg = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT count(*) AS n,
                  COALESCE(sum(NULLIF(sp.raw->>'nb_lgt', '')::int), 0) AS total_lgt
           FROM sitadel_permits sp, p
           WHERE sp.geom IS NOT NULL
             AND sp.date >= (CURRENT_DATE - make_interval(months => :mois))
             AND ST_DWithin(ST_Transform(sp.geom, 2975), p.geom_2975, :r)"""),
        {"idu": idu, "mois": FENETRE_PERMIS_MOIS, "r": RAYON_PERMIS_M}).mappings().first()
    n = int(agg["n"]) if agg else 0
    if not n:
        return {"n": 0, "rien": True, "rayon_m": RAYON_PERMIS_M, "mois": FENETRE_PERMIS_MOIS}
    # P3-8 : seuls les 3 plus gros projets sont AFFICHÉS → LIMIT côté SQL (borne le payload en
    # secteur dense, où le rayon pouvait ramener des centaines de permis sans raison). Les compteurs
    # ci-dessus restent exacts ; « cohérent avec l'affichage » = on ne rapatrie que ce qui est montré.
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sp.type, to_char(sp.date, 'MM/YYYY') AS mois,
                  NULLIF(sp.raw->>'nb_lgt', '')::int AS nb_lgt,
                  sp.raw->>'famille' AS famille
           FROM sitadel_permits sp, p
           WHERE sp.geom IS NOT NULL
             AND sp.date >= (CURRENT_DATE - make_interval(months => :mois))
             AND ST_DWithin(ST_Transform(sp.geom, 2975), p.geom_2975, :r)
             AND NULLIF(sp.raw->>'nb_lgt', '')::int > 0
           ORDER BY nb_lgt DESC NULLS LAST LIMIT 3"""),
        {"idu": idu, "mois": FENETRE_PERMIS_MOIS, "r": RAYON_PERMIS_M}).mappings().all()
    return {"n": n, "rayon_m": RAYON_PERMIS_M, "mois": FENETRE_PERMIS_MOIS,
            "total_logements": int(agg["total_lgt"]),
            "plus_gros": [dict(r) for r in rows]}


def _terrain(db: Session, idu: str, avail: set[str]) -> dict | None:
    out: dict[str, Any] = {}
    if "parcel_terrain" in avail:
        r = db.execute(text(
            "SELECT pente_moy_deg, pente_max_deg, flag_terrassement_lourd "
            "FROM parcel_terrain WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if r and r["pente_moy_deg"] is not None:
            # M54-AB C7 : la pente est SERVIE en degrés ET en % (même source RGE ALTI), avec son
            # qualificatif — une seule mesure partout (fin du « ~10 % » coarse vs « 11,4° »).
            from ..pente_fmt import pente_pct, pente_label
            moy = round(float(r["pente_moy_deg"]), 1)
            out["pente"] = {"moy_deg": moy, "moy_pct": pente_pct(moy),
                            "label": pente_label(pente_pct(moy)),
                            "max_deg": round(float(r["pente_max_deg"]), 1)
                            if r["pente_max_deg"] is not None else None,
                            "max_pct": pente_pct(float(r["pente_max_deg"]))
                            if r["pente_max_deg"] is not None else None,
                            "terrassement_lourd": bool(r["flag_terrassement_lourd"])}
    # Mandats futurs (ANC & Végétation) : colonnes déclarées par le registre des
    # segments — la sous-section apparaît TOUTE SEULE le jour où la table est mergée.
    # M88 — point de calcul UNIQUE (anc_service.statut_anc), partagé avec la fiche écran et l'export.
    # CORRIGE le bug `bool(zone_anc)` (M59→M86-B) qui servait « ANC » aux 47 803 parcelles en COLLECTIF :
    # bool('collectif') = bool('anc') = True. Désormais Sourcé / Sourcé secteur (taux INSEE) / Absent
    # distincts, jamais un faux ANC, jamais un verdict de secteur (M88 a retiré l'Estimé proba_anc).
    if "parcel_anc" in avail and {"zone_anc"} <= _existing_columns(db, "parcel_anc"):
        from ..anc_service import statut_anc
        out["anc"] = statut_anc(db, idu)
    # M73-D — réhabilitation via le helper UNIQUE (compute_mode_b), jamais recalculée. Absence = état
    # affiché (« Non évaluée »), jamais masquée. Le template rend anc + mode_b par le bloc partagé.
    try:
        from ..faisabilite.bilan import compute_mode_b
        out["mode_b"] = compute_mode_b(db, idu)          # run=None → run servi (Q_A_RUN_LABEL)
    except Exception:  # noqa: BLE001
        pass
    if "parcel_vegetation" in avail and {"ombrage_pct"} <= _existing_columns(db, "parcel_vegetation"):
        r = db.execute(text("SELECT ombrage_pct FROM parcel_vegetation WHERE idu = :idu"),
                       {"idu": idu}).mappings().first()
        if r and r["ombrage_pct"] is not None:
            out["canopee"] = {"ombrage_pct": _i(r["ombrage_pct"])}
    # M18 → M75 — gisement solaire PVGIS. POINT DE CALCUL UNIQUE partagé avec la fiche
    # (viabilisation_build.solaire_note) : le PDF affiche EXACTEMENT le même libellé que la fiche
    # (exigence Vic — une donnée, un libellé). Le score_solaire /100 (score LABUSE opaque) N'EST
    # PLUS exposé ; on garde le productible SOURCÉ (kWh/kWc/an, réserve SARAH3 dans la note).
    if "parcel_solar" in avail:
        from ..faisabilite.viabilisation_build import solaire_note
        sol = solaire_note(db, idu)
        if sol:
            out["solaire"] = sol
    # M73 §F — faisceau de VIABILISATION (réseaux) : la section « Terrain & réseaux » portait pente/
    # assainissement/solaire mais AUCUN réseau (le titre mentait). On branche le faisceau de preuves
    # servi (permis + DAACT « raccordements réalisés », façade sur voirie urbanisée), MÊME point de
    # calcul que la fiche (V.build_indicateur) — aucun tracé réseau fabriqué, jamais une certitude.
    if "parcel_viabilisation" in avail:
        from ..faisabilite import viabilisation as V
        from ..faisabilite.viabilisation_build import ilot_s3renr_note
        vr = db.execute(text(
            "SELECT zone_fam, c100, c200, c100_recent, c100_acheve, voie10, voie75, "
            "bati10, bati30, bati75, assainissement_zonage "
            "FROM parcel_viabilisation WHERE idu = :idu"), {"idu": idu}).mappings().first()
        if vr:
            ind = V.build_indicateur(dict(vr), elec_pv=ilot_s3renr_note(db), solaire=None)
            if ind:
                out["viabilisation"] = {
                    "libelle": ind.get("libelle"),
                    "preuves": [{"libelle": c.get("libelle"), "detail": c.get("detail")}
                                for c in (ind.get("contributions") or []) if c.get("signe") == "+"][:3]}
    return out or None


def _aper(db: Session, idu: str, avail: set[str]) -> dict | None:
    """M75 — obligation APER (grand parking > 1 500 m²). Point de calcul unique = fiche."""
    if "parkings_aper" not in avail:
        return None
    from ..faisabilite.viabilisation_build import aper_note
    return aper_note(db, idu)


# ── Sources & millésimes (page argument de vente, pas une annexe — mandat §3.9) ──────────

# M-P (P2-68) : sources référencées par NOM CANONIQUE data_sources (les serial `id` dépendent de
# l'ordre d'insertion du seed → sur une base reconstruite, le rapport VENDU attribuait la mauvaise
# date de synchro au mauvais bloc). Les noms sont déclarés « NE PAS renommer » (seed_sources).
# tuple : (clé section, libellé affiché, NOM data_sources | None, millésime statique).
_SECTION_SOURCES: list[tuple[str, str, str | None, str | None]] = [
    ("identite", "Cadastre Etalab (DGFiP)", "Cadastre Etalab (bulk DGFiP/Etalab)", None),
    ("identite", "PLU / GPU (API Carto, IGN)", "Urbanisme PLU/GPU (API Carto)", None),
    ("identite", "Droits résiduels — calibrage LABUSE sur règlements PLU", None,
     "calibrage continu 2026"),
    ("risques", "Géorisques (BRGM / MTE)", "Géorisques", None),
    ("risques", "Géorisques — sites et sols pollués", "Géorisques — sites et sols pollués", None),
    ("risques", "Géorisques — cavités souterraines", "Géorisques — cavités souterraines", None),
    ("risques", "Géorisques — ICPE", "Géorisques — ICPE", None),
    ("risques", "Géorisques — mouvements de terrain", "Géorisques — mouvements de terrain", None),
    ("risques", "PPR / aléas (DEAL Réunion)", "DEAL Réunion — PPR / aléas", None),
    ("risques", "Classement sonore ITT (Cerema)", "Classement sonore ITT (Cerema)", None),
    ("risques", "Recul du trait de côte (Cerema / GéoLittoral)", "DEAL Réunion — trait de côte", None),
    ("risques", "50 pas géométriques (DEAL)", "50 pas géométriques — limite haute (DEAL)", None),
    ("patrimoine", "Base Mérimée / ABF (Ministère de la Culture)", "ABF / Monuments historiques", None),
    ("patrimoine", "ENS (INPN / Département)", "ENS (Département)", None),
    ("patrimoine", "QPV 2024 (ANCT)", "QPV 2024 (ANCT)", None),
    ("patrimoine", "Cartofriches (Cerema)", "Cartofriches (Cerema)", None),
    ("patrimoine", "Parc National de La Réunion (INPN)", "Parc National de La Réunion (INPN)", None),
    ("marche", "DVF — valeurs foncières (DGFiP / Cerema)", "DVF / valeurs foncières", None),
    ("dynamique", "Sitadel — autorisations d'urbanisme (SDES)", "SITADEL (autorisations d'urbanisme)", None),
    ("terrain", "RGE ALTI 5 m (IGN)", "RGE ALTI (altimétrie)", None),
    ("terrain", "PVGIS — gisement solaire (Commission européenne)", None, "modèle SARAH3"),
    ("carte", "Fond de carte © OpenStreetMap contributors (ODbL)", "OpenStreetMap / Overpass", None),
    ("adresse", "Base Adresse Nationale (DINUM / IGN)", "Base Adresse Nationale", None),
    # M18 — contexte commune
    ("contexte_commune", "Sitadel — délais d'instruction (SDES/Dido)", "SITADEL (autorisations d'urbanisme)", "historique 2013+"),
    ("contexte_commune", "Inventaire SRU / LLS (DHUP)", None, "inventaire 2024 · périmètre 2025"),
    ("contexte_commune", "QPV (ANCT)", "QPV 2024 (ANCT)", "génération 2024"),
    ("contexte_commune", "Consommation d'espace ENAF (Cerema)", None, "2009-2024 · publié 05/2025"),
]


def _contexte_commune(db: Session, idu: str, commune: str, avail: set[str]) -> dict | None:
    """M18 — contexte COMMUNE (agrégats sourcés, JAMAIS d'identité de personne physique) :
    vélocité d'instruction PC (Sitadel, dossiers accordés), leviers social/bailleur (SRU + QPV),
    consommation d'espace observée (Cerema ENAF). Le budget/horizon ZAN (estimé, SAR non
    territorialisé) est VOLONTAIREMENT EXCLU — donnée trop incertaine (garde-fou : pas de champ faux)."""
    out: dict[str, Any] = {}

    # 1) Vélocité administrative — délai médian d'instruction PC (dépôt → autorisation).
    # Source Sitadel/SDES : dossiers ACCORDÉS uniquement ; cohortes mûres (dépôts > 12 mois) ;
    # seuil de fiabilité ≥ 8 dossiers (sinon médiane non significative → on n'affiche pas).
    if "m10_permit_delais" in avail:
        v = db.execute(text("""
            WITH cut AS (SELECT (max(date_depot) - make_interval(months => 12))::date AS c
                         FROM m10_permit_delais WHERE nature = 'PC')
            SELECT count(*) FILTER (WHERE valide AND date_depot <= (SELECT c FROM cut)) AS n,
              round(percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois)
                    FILTER (WHERE valide AND date_depot <= (SELECT c FROM cut))) AS med,
              round(percentile_cont(0.25) WITHIN GROUP (ORDER BY delai_mois)
                    FILTER (WHERE valide AND date_depot <= (SELECT c FROM cut))) AS p25,
              round(percentile_cont(0.75) WITHIN GROUP (ORDER BY delai_mois)
                    FILTER (WHERE valide AND date_depot <= (SELECT c FROM cut))) AS p75
            FROM m10_permit_delais WHERE commune = :c AND nature = 'PC'"""),
            {"c": commune}).mappings().first()
        if v and v["med"] is not None and (v["n"] or 0) >= 8:
            out["velocite"] = {"median_mois": _i(v["med"]), "p25_mois": _i(v["p25"]),
                               "p75_mois": _i(v["p75"]), "n": int(v["n"])}

    # 2) Leviers social / bailleur — SRU (déficit LLS) + QPV (TVA réduite). Sourcé (millésime porté).
    sru = None
    if "commune_contexte_sru" in avail:
        r = db.execute(text(
            "SELECT statut, taux_lls, objectif_pct, millesime, (detail->>'nb_lls')::float AS nb_lls"
            " FROM commune_contexte_sru WHERE commune = :c"), {"c": commune}).mappings().first()
        if r:
            deficit = None
            tx, obj, nb = _f(r["taux_lls"]), _f(r["objectif_pct"]), r["nb_lls"]
            if tx and obj and nb and 0 < tx < obj:   # déficitaire → besoin estimé de LLS
                deficit = round(float(nb) * (obj - tx) / tx)
            sru = {"statut": r["statut"], "taux_lls": tx, "objectif_pct": obj,
                   "deficit_logements": deficit, "millesime": r["millesime"]}
    qpv = False
    if "spatial_layers" in avail:
        qpv = bool(db.execute(text(
            "WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)"
            " SELECT 1 FROM spatial_layers sl, p WHERE sl.kind = 'qpv'"
            " AND ST_Intersects(sl.geom_2975, p.geom_2975) LIMIT 1"), {"idu": idu}).scalar())
    if sru or qpv:
        out["leviers"] = {"sru": sru, "qpv": qpv}

    # 3) Consommation d'espace OBSERVÉE (Cerema ENAF) — Sourcé. On montre le rythme, PAS de budget/
    # horizon ZAN (estimé, non territorialisé → exclu par garde-fou).
    if "commune_conso_enaf" in avail:
        e = db.execute(text(
            "SELECT conso_2011_2021_m2 AS c1, conso_2021_2024_m2 AS c2, millesime"
            " FROM commune_conso_enaf WHERE commune = :c"), {"c": commune}).mappings().first()
        if e and e["c1"] is not None:
            out["enaf"] = {
                "conso_1121_ha": round((e["c1"] or 0) / 10000, 1),
                "conso_2124_ha": round((e["c2"] or 0) / 10000, 1),
                "rythme_1121_m2an": round((e["c1"] or 0) / 10),   # 2011-2021 = 10 ans
                "rythme_2124_m2an": round((e["c2"] or 0) / 3),    # 2021-2024 = 3 ans
                "acceleration": (e["c2"] or 0) / 3 > (e["c1"] or 0) / 10,
                "millesime": e["millesime"]}
    return out or None


def _sources(db: Session, avail: set[str], sections_rendues: set[str]) -> list[dict]:
    # M-P (P2-68) : synchro indexée par NOM (stable), plus par id serial (dépendant du seed).
    # M54-AB F9 : on LIT `source_millesime` (millésime AMONT réel). Priorité : statique → millésime
    # amont → motif honnête.
    # M73 E : la date de SYNCHRO (last_sync_at) est une date d'INGESTION — la doctrine INTERDIT de la
    # présenter comme un millésime. On ne bascule PLUS sur « synchronisé le … » : quand le millésime
    # amont est NULL, on l'assume (« horizon amont non publié »). Le peuplement de source_millesime
    # reste une dette data. La date de GÉNÉRATION du document reste, elle, légitime (en pied).
    mill_amont: dict[str, str] = {}
    if "data_sources" in avail:
        for r in db.execute(text("SELECT name, source_millesime FROM data_sources")):
            if r[1]:
                mill_amont[r[0]] = r[1]
    out, vus = [], set()
    for section, label, src_name, statique in _SECTION_SOURCES:
        if section not in sections_rendues or label in vus:
            continue
        vus.add(label)
        if statique:
            millesime = statique
        elif src_name and mill_amont.get(src_name):
            millesime = mill_amont[src_name]
        else:
            # GPU/PLU, Géorisques… n'exposent pas d'horizon amont daté (NULL) — on le DIT, jamais un
            # « — » muet ni une date d'ingestion déguisée en millésime.
            millesime = "horizon amont non publié"
        out.append({"section": section, "source": label, "millesime": millesime})
    return out


_SECTION_LABELS = {"identite": "Identité parcellaire", "constructibilite": "Constructibilité",
                   "risques": "Risques", "patrimoine": "Patrimoine & environnement",
                   "marche": "Marché", "dynamique": "Dynamique locale",
                   "terrain": "Terrain & réseaux", "carte": "Carte de situation",
                   "adresse": "Adresse", "contexte_commune": "Contexte commune & leviers"}


# ── Point d'entrée ───────────────────────────────────────────────────────────────────────

def _rnu_flag(idu: str) -> bool:
    from .. import rnu as _rnu
    return _rnu.is_rnu_idu(idu)


def _marche_via_service(db: Session, idu: str, avail: set[str]) -> dict | None:
    """M73-B Volet C — le dossier LIT le marché par le point d'appel UNIQUE (profil nommé), qui délègue
    à `_marche` (calcul inchangé). `avail` est passé pour éviter une seconde résolution des tables."""
    from .. import marche_service
    return marche_service.marche_dvf(db, idu, profil=marche_service.DVF_SECTEUR_DOSSIER, avail=avail)


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
        "marche": _marche_via_service(db, idu, avail),   # M73-B Volet C — point d'appel UNIQUE
        "dynamique": _dynamique(db, idu, avail),
        "terrain": _terrain(db, idu, avail),
        "contexte_commune": _contexte_commune(db, idu, parcelle["commune"], avail),
        # M75 — obligation APER (grand parking) : MÊME libellé que la fiche (point de calcul unique).
        "aper": _aper(db, idu, avail),
        "date_generation": date.today().isoformat(),
        # MANDAT RNU : flag top-level — le template remplace les règles de capacité par
        # « non applicable — RNU » (jamais un tableau vide qui laisserait croire à une
        # absence de contrainte — ajout Vic 26/07/2026).
        "rnu": _rnu_flag(idu),
    }
    rendues = {k for k in ("identite", "constructibilite", "risques", "patrimoine",
                           "marche", "dynamique", "terrain", "contexte_commune") if data.get(k)}
    if adresse:
        rendues.add("adresse")
    data["sources"] = _sources(db, avail, rendues | {"carte"})
    data["section_labels"] = _SECTION_LABELS
    return data
