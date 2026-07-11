"""Registry DÉCLARATIF des filtres du moteur de segments (Lot 1).

Chaque filtre = {clé, libellé, type, source SQL, unité, disponibilité détectée}.
SÉCURITÉ : le SQL (expressions, jointures, tris) vit UNIQUEMENT ici, côté serveur.
Le client n'envoie que des clés (validées contre ce registry) et des valeurs
(passées en paramètres bindés) — aucune requête construite depuis du texte client.

DISPONIBILITÉ : un filtre déclare ses prérequis (`requires` = tables/colonnes,
`requires_rows` = table qui doit être NON VIDE pour que le filtre ait un sens).
Les sources absentes (parcel_solar, parcel_equipements, parcel_anc,
parcel_vegetation — mandats Habitat Solaire / Détection Ortho / ANC-Végétation)
donnent un filtre GRISÉ « disponible prochainement », jamais une erreur.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import text

from ..scoring.score_v_constants import Q_A_RUN_LABEL

# ── Jointures nommées (assemblées par l'évaluateur, jamais par le client) ──
# Les LATERAL dédupliquent les sources 1-n (plusieurs DPE / lignes cascade par parcelle).
JOINS: dict[str, str] = {
    "dvf": "LEFT JOIN v_parcel_dvf_last dvf ON dvf.idu = p.idu",
    "tb": ("LEFT JOIN LATERAL (SELECT d.type_local FROM dvf_mutations_parcelle d"
           " WHERE d.id_parcelle = p.idu AND d.type_local IS NOT NULL AND d.type_local <> ''"
           " ORDER BY d.date_mutation DESC LIMIT 1) tb ON true"),
    "dpe": ("LEFT JOIN LATERAL (SELECT min(d.annee_construction) AS annee"
            " FROM dpe_records d WHERE d.parcelle_idu = p.idu"
            " AND d.annee_construction IS NOT NULL) dpe ON true"),
    "adr": ("LEFT JOIN LATERAL (SELECT d2.adresse FROM dpe_records d2"
            " WHERE d2.parcelle_idu = p.idu AND d2.adresse IS NOT NULL"
            " ORDER BY d2.date_etablissement DESC NULLS LAST LIMIT 1) adr ON true"),
    "ter": "LEFT JOIN parcel_terrain ter ON ter.idu = p.idu",
    "rb": "LEFT JOIN parcel_residuel_bati rb ON rb.idu = p.idu",
    "fil": ("LEFT JOIN LATERAL (SELECT (100.0 * f.men_prop / NULLIF(f.men, 0)) AS prop_pct"
            " FROM filosofi_carreaux_200m f"
            " WHERE ST_Contains(f.geom, ST_Transform(p.centroid, 2975)) LIMIT 1) fil ON true"),
    "zc": ("LEFT JOIN LATERAL (SELECT cr.detail FROM dryrun_cascade_results cr"
           " WHERE cr.parcel_id = p.id AND cr.run_label = :cascade_run"
           " AND cr.layer_name = 'zonage_plu_gpu' ORDER BY cr.id LIMIT 1) zc ON true"),
    # Adresse BAN de la parcelle (mandat wave-adresses Lot 1.5) : la MEILLEURE adresse de
    # l'index inverse — priorité au rattachement direct du point, puis numéro le plus bas
    # (déterministe). Le publipostage « à l'occupant » se fonde sur CES champs normalisés.
    "ban": ("LEFT JOIN LATERAL (SELECT a.numero, a.rep, a.voie, a.code_postal,"
            " a.commune AS ban_commune FROM adresse_parcelles ap"
            " JOIN adresses a ON a.id_ban = ap.id_ban WHERE ap.idu = p.idu"
            " ORDER BY (ap.source = 'principal') DESC, (a.numero IS NULL),"
            " NULLIF(regexp_replace(a.numero, '\\D', '', 'g'), '')::int NULLS LAST, a.id_ban"
            " LIMIT 1) ban ON true"),
    "ab": ("LEFT JOIN LATERAL (SELECT cr2.result FROM dryrun_cascade_results cr2"
           " WHERE cr2.parcel_id = p.id AND cr2.run_label = :cascade_run"
           " AND cr2.layer_name = 'abf' ORDER BY cr2.id LIMIT 1) ab ON true"),
}

# La classe de zone est dérivée du run de cascade DÉJÀ résolu par parcelle (zéro jointure
# spatiale à la volée). L'ordre des LIKE compte : « AU » avant « U » (préfixe commun).
_ZONE_EXPR = ("(CASE WHEN zc.detail LIKE 'Zone PLU « AU%' THEN 'AU'"
              " WHEN zc.detail LIKE 'Zone PLU « U%' THEN 'U'"
              " WHEN zc.detail LIKE 'Zone A PLU%' THEN 'A'"
              " WHEN zc.detail LIKE 'Zone N PLU%' THEN 'N'"
              " ELSE 'hors' END)")

_JARDIN_EXPR = "GREATEST(p.surface_m2 - COALESCE(rb.emprise_batie_m2, 0), 0)"

# catnat_recent : commune sous arrêté CATNAT (périls configurés) de moins de N mois.
# :catnat_mois / :catnat_perils sont des paramètres SERVEUR (config), jamais client.
_CATNAT_EXPR = ("EXISTS (SELECT 1 FROM catnat_arretes ca WHERE ca.commune = p.commune"
                " AND ca.date_arrete >= (CURRENT_DATE - make_interval(months => :catnat_mois))"
                " AND ca.type_peril ILIKE ANY(:catnat_perils))")

_QPV_EXPR = ("EXISTS (SELECT 1 FROM spatial_layers q WHERE q.kind = 'qpv'"
             " AND ST_Intersects(q.geom_2975, p.geom_2975))")


@dataclass(frozen=True)
class FilterDef:
    cle: str
    libelle: str
    type: str                                  # 'range' | 'bool' | 'enum'
    expr: str                                  # expression SQL (serveur uniquement)
    joins: tuple[str, ...] = ()
    unite: str | None = None
    groupe: str = "Parcelle"                   # groupe d'affichage du query builder
    requires: tuple[str, ...] = ()             # "table" ou "table.colonne" à détecter
    requires_rows: str | None = None           # table qui doit être non vide
    enum_values: tuple[str, ...] = ()
    description: str = ""
    mandat: str | None = None                  # mandat qui livrera la source si absente


# NB : les clés sont l'API publique des presets (seed + admin) — ne pas renommer sans
# migration des jsonb `segment_presets.filtres`.
FILTERS: dict[str, FilterDef] = {f.cle: f for f in [
    # ── Marché / mutation (DVF) ──
    # Ancré sur le DERNIER MILLÉSIME DVF connu (pas now()) : DVF publie avec ~6 mois de
    # retard — « mutation < 6 mois » = les 6 derniers mois DU FLUX, sinon le segment
    # « emménagements » serait structurellement vide entre deux millésimes.
    FilterDef("anciennete_mutation_mois", "Ancienneté de la dernière mutation", "range",
              "(EXTRACT(EPOCH FROM ((SELECT max(date_mutation) FROM dvf_mutations_parcelle)"
              "::timestamp - dvf.date_mutation::timestamp)) / 2629800.0)",
              joins=("dvf",), unite="mois", groupe="Marché",
              requires=("dvf_mutations_parcelle", "v_parcel_dvf_last"),
              requires_rows="dvf_mutations_parcelle",
              description="Mois écoulés depuis la dernière vente DVF de la parcelle, "
                          "comptés depuis la donnée DVF la plus récente en base "
                          "(les parcelles jamais mutées sont exclues quand ce filtre est actif)."),
    FilterDef("prix_mutation_eur", "Prix de la dernière mutation", "range", "dvf.valeur",
              joins=("dvf",), unite="€", groupe="Marché",
              requires=("dvf_mutations_parcelle", "v_parcel_dvf_last"),
              requires_rows="dvf_mutations_parcelle",
              description="Valeur foncière de la dernière vente (DVF)."),
    FilterDef("type_bien", "Type de bien (dernière mutation)", "enum", "tb.type_local",
              joins=("tb",), groupe="Marché",
              requires=("dvf_mutations_parcelle.type_local",),
              requires_rows="dvf_mutations_parcelle",
              enum_values=("Maison", "Appartement", "Dépendance",
                           "Local industriel. commercial ou assimilé"),
              description="Type de local de la dernière mutation DVF."),
    # ── Bâti ──
    FilterDef("periode_construction", "Période de construction (DPE)", "range", "dpe.annee",
              joins=("dpe",), unite="année", groupe="Bâti",
              requires=("dpe_records.annee_construction",), requires_rows="dpe_records",
              description="Année de construction du logement le plus ancien connu au DPE "
                          "(couverture partielle : logements ayant un DPE)."),
    FilterDef("flag_amiante", "Amiante probable (bâti < 1997)", "bool", "(dpe.annee < 1997)",
              joins=("dpe",), groupe="Bâti",
              requires=("dpe_records.annee_construction",), requires_rows="dpe_records",
              description="Proxy réglementaire : construction antérieure à l'interdiction de "
                          "l'amiante (1er juillet 1997), d'après l'année DPE."),
    FilterDef("emprise_batie_m2", "Surface d'emprise bâtie", "range", "rb.emprise_batie_m2",
              joins=("rb",), unite="m²", groupe="Bâti",
              requires=("parcel_residuel_bati",), requires_rows="parcel_residuel_bati",
              description="Emprise au sol du bâti BD TOPO sur la parcelle."),
    FilterDef("jardin_m2", "Surface de jardin (parcelle − emprise bâtie)", "range",
              _JARDIN_EXPR, joins=("rb",), unite="m²", groupe="Parcelle",
              requires=("parcel_residuel_bati",), requires_rows="parcel_residuel_bati",
              description="Surface non bâtie de la parcelle — le « jardin » du prospect."),
    FilterDef("ces_probable_pct", "CES probable (emprise/parcelle)", "range",
              "(100.0 * rb.emprise_batie_m2 / NULLIF(p.surface_m2, 0))",
              joins=("rb",), unite="%", groupe="Bâti",
              requires=("parcel_residuel_bati",), requires_rows="parcel_residuel_bati",
              description="Coefficient d'emprise au sol constaté (bâti BD TOPO / surface)."),
    # ── Terrain ──
    FilterDef("pente_moy_deg", "Pente moyenne", "range", "ter.pente_moy_deg",
              joins=("ter",), unite="°", groupe="Terrain",
              requires=("parcel_terrain.pente_moy_deg",), requires_rows="parcel_terrain",
              description="Pente moyenne de la parcelle (RGE ALTI 5 m)."),
    FilterDef("pente_max_deg", "Pente maximale", "range", "ter.pente_max_deg",
              joins=("ter",), unite="°", groupe="Terrain",
              requires=("parcel_terrain.pente_max_deg",), requires_rows="parcel_terrain",
              description="Pente maximale de la parcelle (RGE ALTI 5 m)."),
    # ── Équipements détectés (mandat Détection Ortho — pas encore ingéré) ──
    FilterDef("piscine", "Piscine détectée", "bool", "eq.piscine", joins=("eq",),
              groupe="Équipements", requires=("parcel_equipements",),
              description="Piscine détectée sur orthophoto.",
              mandat="Détection Ortho"),
    FilterDef("pv_detecte", "Panneaux PV détectés", "bool", "eq.pv", joins=("eq",),
              groupe="Équipements", requires=("parcel_equipements",),
              description="Panneaux photovoltaïques détectés sur orthophoto.",
              mandat="Détection Ortho"),
    # ── Solaire (mandat Habitat Solaire — pas encore ingéré) ──
    FilterDef("score_solaire", "Score solaire", "range", "sol.score", joins=("sol",),
              unite="/100", groupe="Énergie", requires=("parcel_solar",),
              description="Gisement solaire de la toiture.", mandat="Habitat Solaire"),
    FilterDef("facture_elec_estimee_eur", "Facture électrique estimée", "range",
              "sol.facture_estimee", joins=("sol",), unite="€/an", groupe="Énergie",
              requires=("parcel_solar",),
              description="Facture électricité estimée du ménage.", mandat="Habitat Solaire"),
    # ── Végétation / ANC (mandat ANC & Végétation — pas encore ingéré) ──
    FilterDef("ombrage_vegetal", "Ombrage végétal", "range", "veg.ombrage_pct",
              joins=("veg",), unite="%", groupe="Végétation", requires=("parcel_vegetation",),
              description="Part de la parcelle sous canopée.", mandat="ANC & Végétation"),
    FilterDef("canopee_limite", "Canopée en limite de parcelle", "bool", "veg.canopee_limite",
              joins=("veg",), groupe="Végétation", requires=("parcel_vegetation",),
              description="Arbres en limite (élagage).", mandat="ANC & Végétation"),
    FilterDef("zone_anc", "Zone d'assainissement non collectif", "bool", "anc.zone_anc",
              joins=("anc",), groupe="Réseaux", requires=("parcel_anc",),
              description="Parcelle en zonage ANC (probabilité de fosse).",
              mandat="ANC & Végétation"),
    # ── Réglementaire / contexte ──
    FilterDef("flag_abf", "Périmètre ABF / abords MH", "bool", "(ab.result = 'UNKNOWN')",
              joins=("ab",), groupe="Réglementaire",
              requires=("dryrun_cascade_results",), requires_rows="dryrun_cascade_results",
              description="Parcelle dans un périmètre des Architectes des Bâtiments de "
                          "France (abords Monuments historiques ~500 m — cascade)."),
    FilterDef("zonage_plu", "Classe de zonage PLU", "enum", _ZONE_EXPR, joins=("zc",),
              groupe="Réglementaire",
              requires=("dryrun_cascade_results",), requires_rows="dryrun_cascade_results",
              enum_values=("U", "AU", "A", "N", "hors"),
              description="Classe de zone PLU résolue au run de référence."),
    FilterDef("qpv", "Quartier prioritaire (QPV)", "bool", _QPV_EXPR,
              groupe="Réglementaire", requires=("spatial_layers",),
              description="Parcelle en Quartier Prioritaire de la Ville."),
    FilterDef("communes", "Commune(s)", "enum", "p.commune", groupe="Parcelle",
              description="Limiter aux communes choisies."),
    FilterDef("proprio_occupant_pct", "Ménages propriétaires (carreau 200 m)", "range",
              "fil.prop_pct", joins=("fil",), unite="%", groupe="Contexte",
              requires=("filosofi_carreaux_200m",), requires_rows="filosofi_carreaux_200m",
              description="Part de ménages propriétaires du carreau Filosofi 200 m — proxy "
                          "de probabilité propriétaire-occupant."),
    # ── Droits résiduels (Lot 2) ──
    FilterDef("emprise_residuelle_m2", "Emprise résiduelle constructible", "range",
              "rb.emprise_residuelle_m2", joins=("rb",), unite="m²", groupe="Foncier bâti",
              requires=("parcel_residuel_bati.emprise_residuelle_m2",),
              requires_rows="parcel_residuel_bati",
              description="Potentiel indicatif estimé : emprise max du zonage − emprise "
                          "bâtie. Les règles complètes du PLU (retraits, prospects, "
                          "servitudes) peuvent le réduire."),
    FilterDef("surelevation_possible", "Surélévation possible", "bool",
              "rb.surelevation_possible", joins=("rb",), groupe="Foncier bâti",
              requires=("parcel_residuel_bati.surelevation_possible",),
              requires_rows="parcel_residuel_bati",
              description="Hauteur max du zonage − hauteur du bâtiment (BD TOPO) ≥ 2,8 m — "
                          "potentiel indicatif estimé, pas une étude de faisabilité."),
    # ── Signal CATNAT (Lot 3) ──
    FilterDef("catnat_recent", "Commune en CATNAT récent", "bool", _CATNAT_EXPR,
              groupe="Signaux", requires=("catnat_arretes",), requires_rows="catnat_arretes",
              description="Commune sous arrêté de catastrophe naturelle (vent cyclonique, "
                          "inondation) récent — fenêtre configurable."),
    # ── Adresse (mandat wave-adresses Lot 1) ──
    FilterDef("adresse_ban", "Adresse BAN connue", "bool", "(ban.voie IS NOT NULL)",
              joins=("ban",), groupe="Parcelle",
              requires=("adresses", "adresse_parcelles"), requires_rows="adresses",
              description="La parcelle porte au moins une adresse BAN rattachée — "
                          "prérequis d'un courrier « à l'occupant » fiable."),
]}

# Jointures vers des tables FUTURES (mandats non mergés) : déclarées pour mémoire, jamais
# assemblées tant que la table manque (la disponibilité l'empêche).
JOINS.setdefault("eq", "LEFT JOIN parcel_equipements eq ON eq.idu = p.idu")
JOINS.setdefault("sol", "LEFT JOIN parcel_solar sol ON sol.idu = p.idu")
JOINS.setdefault("veg", "LEFT JOIN parcel_vegetation veg ON veg.idu = p.idu")
JOINS.setdefault("anc", "LEFT JOIN parcel_anc anc ON anc.idu = p.idu")


@dataclass(frozen=True)
class SortDef:
    cle: str
    libelle: str
    order_by: str
    joins: tuple[str, ...] = ()
    requires_rows: str | None = None


SORTS: dict[str, SortDef] = {s.cle: s for s in [
    SortDef("mutation_recente", "Mutation la plus récente d'abord",
            "dvf.date_mutation DESC NULLS LAST", ("dvf",), "dvf_mutations_parcelle"),
    SortDef("prix_mutation_desc", "Prix de mutation décroissant",
            "dvf.valeur DESC NULLS LAST", ("dvf",), "dvf_mutations_parcelle"),
    SortDef("jardin_desc", "Jardin le plus grand d'abord",
            _JARDIN_EXPR + " DESC", ("rb",), "parcel_residuel_bati"),
    SortDef("age_bati_desc", "Bâti le plus ancien d'abord",
            "dpe.annee ASC NULLS LAST", ("dpe",), "dpe_records"),
    SortDef("residuel_desc", "Emprise résiduelle décroissante",
            "rb.emprise_residuelle_m2 DESC NULLS LAST", ("rb",), "parcel_residuel_bati"),
    SortDef("surface_desc", "Surface de parcelle décroissante", "p.surface_m2 DESC"),
]}

# ── Colonnes d'export « à l'occupant » (RGPD : JAMAIS de nom de personne physique) ──
# clé → (en-tête CSV lisible en français, expression SQL, jointures).
EXPORT_COLS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "adresse": ("Adresse (source DPE, si connue)", "adr.adresse", ("adr",)),
    # Adresse BAN NORMALISÉE (mandat wave-adresses Lot 1.5) : émise d'office sur tous les
    # exports quand la table est là (cf. engine.BAN_EXPORT_KEYS) — remplace l'approximation DPE.
    "adresse_numero": ("Numéro", "NULLIF(concat_ws(' ', ban.numero, ban.rep), '')", ("ban",)),
    "adresse_voie": ("Voie (BAN)", "ban.voie", ("ban",)),
    "adresse_cp": ("Code postal", "ban.code_postal", ("ban",)),
    "adresse_ville": ("Ville", "ban.ban_commune", ("ban",)),
    "surface_m2": ("Surface parcelle (m²)", "round(p.surface_m2)", ()),
    "jardin_m2": ("Jardin estimé (m²)", f"round({_JARDIN_EXPR})", ("rb",)),
    "emprise_batie_m2": ("Emprise bâtie (m²)", "round(rb.emprise_batie_m2)", ("rb",)),
    "date_mutation": ("Dernière vente (date)", "dvf.date_mutation", ("dvf",)),
    "valeur_mutation": ("Dernière vente (€)", "dvf.valeur", ("dvf",)),
    "type_bien": ("Type de bien", "tb.type_local", ("tb",)),
    "annee_construction": ("Année de construction (DPE)", "dpe.annee", ("dpe",)),
    "pente_moy_deg": ("Pente moyenne (°)", "round(ter.pente_moy_deg::numeric, 1)", ("ter",)),
    "emprise_residuelle_m2": ("Emprise résiduelle estimée (m²)",
                              "round(rb.emprise_residuelle_m2)", ("rb",)),
    "surelevation_possible": ("Surélévation possible (indicatif)",
                              "rb.surelevation_possible", ("rb",)),
    "confiance_residuel": ("Confiance du potentiel résiduel", "rb.confiance", ("rb",)),
    "zonage_plu": ("Classe de zone PLU", _ZONE_EXPR, ("zc",)),
    "proprio_occupant_pct": ("Ménages propriétaires du carreau (%)",
                             "round(fil.prop_pct)", ("fil",)),
}

# Jointures/colonnes utilisées par une colonne d'export dont la source manque → colonne omise.
_EXPORT_REQUIRES: dict[str, str] = {
    "adresse_numero": "adresse_ban", "adresse_voie": "adresse_ban",
    "adresse_cp": "adresse_ban", "adresse_ville": "adresse_ban",
    "jardin_m2": "jardin_m2", "emprise_batie_m2": "emprise_batie_m2",
    "date_mutation": "anciennete_mutation_mois", "valeur_mutation": "prix_mutation_eur",
    "type_bien": "type_bien", "annee_construction": "periode_construction",
    "pente_moy_deg": "pente_moy_deg", "emprise_residuelle_m2": "emprise_residuelle_m2",
    "surelevation_possible": "surelevation_possible", "confiance_residuel": "emprise_residuelle_m2",
    "zonage_plu": "zonage_plu", "proprio_occupant_pct": "proprio_occupant_pct",
}


def export_col_available(key: str, avail: dict[str, dict]) -> bool:
    """Une colonne d'export est émise si le filtre qui porte sa source est disponible."""
    dep = _EXPORT_REQUIRES.get(key)
    return dep is None or bool(avail.get(dep, {}).get("disponible"))


# ── Détection de disponibilité (cache court : l'existence d'une table ne change pas
#    en cours de session, mais les tests et les ensure_tables doivent pouvoir invalider) ──
_AVAIL_TTL_S = 600.0
_avail_cache: dict = {"at": 0.0, "value": None, "key": None}


def reset_availability_cache() -> None:
    _avail_cache.update(at=0.0, value=None, key=None)


def _existing_tables(session, names: set[str]) -> set[str]:
    rows = session.execute(text(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = 'public' AND table_name = ANY(:n)"
        " UNION SELECT table_name FROM information_schema.views"
        " WHERE table_schema = 'public' AND table_name = ANY(:n)"),
        {"n": sorted(names)}).scalars().all()
    return set(rows)


def _existing_columns(session, pairs: set[tuple[str, str]]) -> set[tuple[str, str]]:
    if not pairs:
        return set()
    rows = session.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND table_name = ANY(:t)"),
        {"t": sorted({t for t, _ in pairs})}).all()
    return {(t, c) for t, c in rows} & pairs


def _non_empty(session, table: str) -> bool:
    try:
        return bool(session.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar())  # noqa: S608 — nom de table issu du registry, jamais du client
    except Exception:  # noqa: BLE001 — table absente entre-temps
        return False


def compute_availability(session, *, simulate_missing: frozenset[str] = frozenset(),
                         use_cache: bool = True) -> dict[str, dict]:
    """{clé filtre: {disponible, raison, mandat}} — détection à l'exécution.

    `simulate_missing` (tests de résilience) : tables considérées absentes même si
    présentes — le critère d'acceptation « base SANS parcel_solar/parcel_equipements ».
    """
    cache_key = tuple(sorted(simulate_missing))
    now = time.monotonic()
    if (use_cache and _avail_cache["value"] is not None
            and _avail_cache["key"] == cache_key and now - _avail_cache["at"] < _AVAIL_TTL_S):
        return _avail_cache["value"]

    tables_needed: set[str] = set()
    cols_needed: set[tuple[str, str]] = set()
    for f in FILTERS.values():
        for req in f.requires:
            t, _, c = req.partition(".")
            tables_needed.add(t)
            if c:
                cols_needed.add((t, c))
        if f.requires_rows:
            tables_needed.add(f.requires_rows)

    have_tables = _existing_tables(session, tables_needed) - simulate_missing
    have_cols = {(t, c) for t, c in _existing_columns(session, cols_needed)
                 if t not in simulate_missing}
    rows_ok: dict[str, bool] = {}

    out: dict[str, dict] = {}
    for f in FILTERS.values():
        disponible, raison = True, None
        for req in f.requires:
            t, _, c = req.partition(".")
            if t not in have_tables or (c and (t, c) not in have_cols):
                disponible, raison = False, f"source absente : {req}"
                break
        if disponible and f.requires_rows:
            t = f.requires_rows
            if t not in rows_ok:
                rows_ok[t] = t in have_tables and _non_empty(session, t)
            if not rows_ok[t]:
                disponible, raison = False, f"source vide : {f.requires_rows}"
        out[f.cle] = {"disponible": disponible, "raison": raison, "mandat": f.mandat}

    if use_cache:
        _avail_cache.update(at=now, value=out, key=cache_key)
    return out


CASCADE_RUN = Q_A_RUN_LABEL
