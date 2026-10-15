"""CHASSE-INVARIANTS-2 — Famille F1 « Le schéma ».

Générateur d'invariants de SCHÉMA : pour chaque colonne servie au client (colonnes des
tables servies — cf. BRIEF), on introspecte le type (`colonnes`) et on émet des RuleSpec
VRAIES PAR CONSTRUCTION, dérivées d'un petit dictionnaire métier nom→type-de-règle :

  · non-négativité        colonnes dont la SÉMANTIQUE interdit le négatif
                          (surface/m2/aire/n_/nb_/count/montant/prix/valeur/taux/pct/age/
                           annee/niveaux/hauteur/logements/places/distance/dist/duree/score/
                           couverture/sdp/contenance/pente/nombre).
  · bornes métier         année ∈ [1800, année courante] ; âge ∈ [0,120] ;
                          pct/taux SERVI/RENDU ≤ 100 ; probabilité (signal_p / geocode_score) ≤ 1 ;
                          pente ≤ 90°.
  · dates ni futures ni absurdes   colonnes date/timestamp d'ÉVÉNEMENT : pas > now(),
                          pas < '1900-01-01'. Écartées si elles portent légitimement du futur
                          (date_limite/echeance/expiration/caducite/horizon/fin_validite).
  · énumérations          UNIQUEMENT là où un domaine légal FERMÉ est connu
                          (DPE/GES ∈ A–G ; bande score ∈ {A,B,C,D,0,NC} ; …).
  · nullité attendue       colonnes qui doivent être non-nulles sur les lignes servies
                          (le run servi doit avoir une bande ; estimable ⇒ prix non-null ; …).

Discipline : une règle sans sens est ÉCARTÉE AVANT de tourner (Ecartee + raison). On ne
borne JAMAIS une colonne de BASE qui dépasse légitimement (taux_emprise_pct / pct_potentiel,
vague-1 E-01), ni une colonne qui peut être négative par nature (delta/marge/solde/ecart/
longitude/latitude).

Lecture seule stricte. Import du noyau partagé.
"""
from __future__ import annotations

import datetime
import re

from scripts.coherence.invariants2.noyau import (
    Ecartee,
    RuleSpec,
    api_dispo,
    api_json,
    bilan,
    colonnes,
    connexion,
    run_specs,
    table_existe,
)

API = "http://127.0.0.1:8793"
ANNEE = datetime.date.today().year
RUN_SERVI = "q_v18"  # run servi (score_labuse)

# ── tables servies au client (feeders fiche / carte / liste) ──────────────────────────────────
# Chaque entrée : (table, predicat-de-lignes-servies). Le prédicat borne la règle aux lignes
# RÉELLEMENT servies (ex : score_labuse multi-run → on ne juge que le run servi).
TABLES_SERVIES: list[tuple[str, str]] = [
    ("parcels", "cadastre_disparue_le IS NULL"),       # parcelles vivantes
    ("parcel_residuel", "TRUE"),
    ("parcel_zone_plu", "TRUE"),
    ("score_labuse", f"run_label = '{RUN_SERVI}'"),     # seul le run servi
    ("score_e", "TRUE"),
    ("dpe_records", "TRUE"),
    ("sitadel_permits", "TRUE"),
    ("dvf_mutations", "TRUE"),
    ("dvf_mutations_parcelle", "TRUE"),
    ("parcelle_personne_morale", "TRUE"),
    ("pm_dirigeants", "TRUE"),
    ("parcel_terrain", "TRUE"),
    ("parcel_amenites", "TRUE"),
    ("parcel_viabilisation", "TRUE"),
    ("parcel_constructibilite", "TRUE"),
    ("parcel_signals", "TRUE"),
    ("taxe_amenagement_taux", "TRUE"),
    # — autres feeders fiche parcelle (rendus sur la fiche via /parcels/{idu}) —
    ("parcel_solar", "TRUE"),              # §3/§10 potentiel solaire
    ("parcel_vegetation", "TRUE"),         # §2 canopée/NDVI
    ("parcel_equipements", "TRUE"),        # piscine / PV détectés
    ("parcel_ocsge", "TRUE"),              # artificialisation
    ("batiment_hauteur_lidar", "TRUE"),    # hauteur_faitage_lidar_m servie (app.py:6423, gabarit.py)
    ("toiture_lidar", "TRUE"),             # toiture
    ("piscines", "TRUE"),                  # détections piscine
    ("parcel_renouvellement", "TRUE"),     # §10 densifier l'existant
    ("parcel_acquerabilite", "TRUE"),      # acquérabilité
    ("parcel_bati_revele", "TRUE"),        # bâti révélé
    # — feeders fiche commune (/communes/{c}/contexte) —
    ("rpls_commune", "TRUE"),              # parc social
    ("commune_rei", "TRUE"),               # fiscalité locale
    ("commune_conso_enaf", "TRUE"),        # conso ENAF
    ("population_legale", "TRUE"),         # population
    ("iris_rp", "TRUE"),                   # recensement IRIS (fiche_commune)
    ("commune_insee_logement", "TRUE"),    # logements INSEE (fiche_commune)
    ("commune_contexte_sru", "TRUE"),      # taux SRU/LLS (contexte commune)
    ("mvt_parcels", "TRUE"),               # parcelles carte/tuiles (mouvement)
]

# ── dictionnaire métier : motifs de NOM → sémantique ──────────────────────────────────────────
# non-négatif : la grandeur ne peut pas être < 0 (surface, compte, prix, distance…)
_RX_NON_NEGATIF = re.compile(
    r"(surface|_m2$|^m2|_aire|aire_|^n_|_n_|nb_|_nb$|nombre|count|montant|^prix|_prix|valeur_fonciere"
    r"|niveaux|hauteur|logements|places|place_|distance|^dist_|_dist$|duree|^score$|_score$"
    r"|couverture|sdp|contenance|pente|c100|c200|voie10|voie75|surface_reelle|surface_habitable"
    r"|surface_terrain|part_communale|charge_supportable|prix_probable|part_|pct_potentiel"
    r"|taux_emprise|surface_terrain_m2|faitage|egout|emprise|canopee|artif|conso|hab_20|pop_|prod_"
    r"|ghi|comp_|renouv|contrainte_pct|surfhab|surelevation|part_pentue|n_cellules|base_|eur"
    r"|tfpb|tfpnb|teom|cfe"
    # census IRIS / logements communaux / SRU / tuiles
    r"|^log$|^rp$|logvac|^maison$|^appart$|^men$|^pop|nper|^ach_|res_princip|res_second|vacants"
    r"|prelevement|completeness|^rang_v2$|^mult_v2$|^etage0$|taux_lls|objectif_pct)",
    re.IGNORECASE,
)
# PEUT être négatif légitimement → écarté de la non-négativité
# (NDVI ∈ [-1,1] ; evol_* = évolution signée ; ecart/delta/marge/solde ; coordonnées)
_RX_PEUT_NEGATIF = re.compile(
    r"(delta|marge|solde|ecart|^lon$|_lon$|^lat$|_lat$|longitude|latitude|^lng$|offset|variation|diff"
    r"|ndvi|^evol|_evol)",
    re.IGNORECASE,
)
# colonne « technique » sans sens métier (id, clé, geom…) → aucune règle non-nég/borne
_RX_TECHNIQUE = re.compile(
    r"(^id$|_id$|^parcel_id$|geom|bbox|centroid|^idu$|_run_id$|^raw$|payload|contributions"
    r"|_notes$|_motifs$|manquantes|_version$|^siren$|gerant_siren|representant_id|permit_id"
    r"|mutation_id|id_mutation|id_parcelle|numero_dpe|rnb_id|code_insee|code_postal|code_commune)",
    re.IGNORECASE,
)
# années (colonne entière = millésime)
_RX_ANNEE = re.compile(r"(^annee|_annee|annee_|millesime)", re.IGNORECASE)
# âge (mot entier « age » séparé par _ — PAS le substring dans « faitage », « ecart…age »)
_RX_AGE = re.compile(r"(^age$|^age_|_age$|_age_)", re.IGNORECASE)
# pct / taux : à ne BORNER ≤100 que si la valeur est SERVIE/rendue (pas une base dépassante)
_RX_PCT = re.compile(r"(_pct$|^pct_|pourcent|taux)", re.IGNORECASE)
# pct de BASE qui dépasse légitimement 100 (clampé au rendu — vague-1 E-01) → PAS de borne ≤100
_RX_PCT_BASE_DEPASSE = {"taux_emprise_pct", "pct_potentiel"}
# taux d'imposition / de vote : un taux communal (TFPB/TFPNB/TEOM/CFE/part_communale TA) n'a pas de
# plafond légal garanti à 100 — on ne le borne PAS ≤100 (éviterait un faux positif un jour).
_RX_TAUX_IMPOT = re.compile(r"(tfpb|tfpnb|teom|cfe|part_communale)", re.IGNORECASE)
# dates d'événement passé (jamais futures) ; on écarte celles qui portent légitimement du futur
_RX_DATE_FUTUR_OK = re.compile(
    r"(limite|echeance|expiration|caducite|horizon|fin_validite|validite|prevue|cible)",
    re.IGNORECASE,
)
# angles de pente → ≤ 90°
_RX_PENTE = re.compile(r"pente", re.IGNORECASE)
# hauteurs de bâtiment en mètres → plafond PHYSIQUE généreux 300 m (le plus haut bâti de l'île
# ne dépasse pas ~60 m ; > 300 m = bruit LiDAR, jamais une vraie hauteur).
_RX_HAUTEUR_M = re.compile(r"(^faitage_m$|^egout_m$|^hauteur_bdtopo_m$|_hauteur_m$)", re.IGNORECASE)
# probabilités / scores normalisés 0..1 (vérifiés : toutes servies, échelle [0,1])
_RX_PROBA = {
    ("score_labuse", "signal_p"),
    ("dpe_records", "geocode_score"),
    ("parcel_equipements", "piscine_confiance"),
    ("parcel_equipements", "pv_confiance"),
    ("piscines", "confiance"),
    ("toiture_lidar", "confiance"),
}

# ── énumérations à domaine légal FERMÉ connu ─────────────────────────────────────────────────
ENUMS: list[tuple[str, str, str, tuple]] = [
    # (table, colonne, predicat-lignes, valeurs légales)
    ("dpe_records", "etiquette_dpe", "TRUE", ("A", "B", "C", "D", "E", "F", "G")),
    ("dpe_records", "etiquette_ges", "TRUE", ("A", "B", "C", "D", "E", "F", "G")),
    ("score_labuse", "bande", f"run_label='{RUN_SERVI}'", ("A", "B", "C", "D", "0", "NC")),
]

# ── nullités attendues sur lignes servies ───────────────────────────────────────────────────
NON_NULS: list[tuple[str, str, str, str]] = [
    # (table, predicat-lignes, colonne-qui-doit-etre-non-nulle, libelle)
    ("score_labuse", f"run_label='{RUN_SERVI}'", "bande",
     "le run servi attribue une bande à chaque parcelle"),
    ("score_labuse", f"run_label='{RUN_SERVI}' AND non_calculable = FALSE", "score",
     "une parcelle calculable du run servi a un score"),
    ("score_e", "estimable = TRUE", "prix_probable",
     "une parcelle estimable a un prix probable"),
    ("parcels", "cadastre_disparue_le IS NULL", "commune",
     "toute parcelle vivante a une commune"),
]


def _non_negatif(col) -> bool:
    return bool(_RX_NON_NEGATIF.search(col.nom)) and not _RX_PEUT_NEGATIF.search(col.nom)


# CHASSE-INVARIANTS-FIX-2 — recadrage « vérité servie » (comme FIX-1 a recadré ses gardes) : les
# hauteurs LiDAR BRUTES portent des artefacts de mesure « dalle » (négatifs, 53 401 m), source non
# réécrite ; mais la valeur SERVIE/CALCULÉE est bornée partout par labuse_hauteur_lidar_m (fix point 1).
# La garde vise donc la valeur SERVIE (bornée), pas la colonne brute.
_SERVIE_BORNEE_LIDAR = {("batiment_hauteur_lidar", "faitage_m"), ("batiment_hauteur_lidar", "egout_m")}


def _expr_servie(table: str, col: str) -> str:
    return f"labuse_hauteur_lidar_m({col})" if (table, col) in _SERVIE_BORNEE_LIDAR else col


def _check_dpe_annee_servie(cx, api):
    """CHASSE-INVARIANTS-FIX-2 (2) — vérifie la VÉRITÉ SERVIE : pour toute parcelle dont l'année de
    construction ADEME brute est aberrante (< 1800 ou future — source non réécrite), la fiche ne sert
    JAMAIS cette année (garde au service + builder bornés) : `filtre_bati.annee_construction` est NULL
    (« année inconnue ») ou dans [1800, ANNEE]. SKIP si l'API n'est pas joignable."""
    with cx.conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT parcelle_idu FROM dpe_records WHERE parcelle_idu IS NOT NULL "
            "AND annee_construction IS NOT NULL AND (annee_construction < 1800 OR annee_construction > %s) "
            "LIMIT 50", (ANNEE,))
        idus = [r[0] for r in cur.fetchall()]
    if not idus:
        return ("OK", "aucune année de construction ADEME aberrante en source — rien à borner")
    if not api or not api_dispo(api):
        return ("SKIP", "API non joignable (la garde vérifie la valeur SERVIE sur la fiche)")
    mauvais = []
    for idu in idus:
        _st, payload = api_json(api, f"/parcels/{idu}?source={RUN_SERVI}")
        if not payload:
            continue
        ac = ((payload.get("filtre_bati") or {}).get("annee_construction"))
        if ac is not None and (ac < 1800 or ac > ANNEE):
            mauvais.append((idu, ac))
    if mauvais:
        return ("ECART", f"année de construction aberrante SERVIE sur {len(mauvais)} parcelle(s) : {mauvais[:3]}")
    return ("OK", f"{len(idus)} parcelle(s) à année ADEME aberrante — toutes servies « année inconnue »")


def generer(cx):
    specs: list[RuleSpec] = []
    ecartees: list[Ecartee] = []
    n_gen = 0

    for table, pred in TABLES_SERVIES:
        if not table_existe(cx, table):
            ecartees.append(Ecartee(f"F1.{table}", "F1", table, "table absente"))
            continue
        cols = colonnes(cx, table)
        for col in cols:
            base_id = f"F1.{table}.{col.nom}"

            # ── 1. non-négativité (colonnes numériques à sémantique ≥0) ────────────────────
            if col.numerique or col.type_sql == "real":
                n_gen += 1
                if _RX_TECHNIQUE.search(col.nom):
                    ecartees.append(Ecartee(f"{base_id}.non_negatif", "F1", base_id,
                        "colonne technique (id/clé/geom/code) — pas de sémantique de grandeur"))
                elif not _non_negatif(col):
                    if _RX_PEUT_NEGATIF.search(col.nom):
                        ecartees.append(Ecartee(f"{base_id}.non_negatif", "F1", base_id,
                            "peut être négatif légitimement (delta/marge/solde/ecart/longitude/latitude)"))
                    else:
                        ecartees.append(Ecartee(f"{base_id}.non_negatif", "F1", base_id,
                            "pas de sémantique non-négative connue pour ce nom"))
                else:
                    _ex = _expr_servie(table, col.nom)      # FIX-2 : valeur SERVIE (bornée pour le LiDAR)
                    specs.append(RuleSpec(
                        id=f"{base_id}.non_negatif", famille="F1", source=base_id,
                        libelle=f"{table}.{col.nom} ≥ 0 sur les lignes servies",
                        gravite="FAUX-CLIENT", attendu="0 ligne < 0",
                        sql_violations=f"SELECT count(*) FROM {table} WHERE ({pred}) AND {_ex} < 0",
                        exemples_sql=f"SELECT * FROM {table} WHERE ({pred}) AND {_ex} < 0 LIMIT 3",
                    ))

            # ── 2a. bornes : années ────────────────────────────────────────────────────────
            if (col.numerique) and _RX_ANNEE.search(col.nom) and not _RX_TECHNIQUE.search(col.nom):
                n_gen += 1
                if (table, col.nom) == ("dpe_records", "annee_construction"):
                    # CHASSE-INVARIANTS-FIX-2 (2) — l'année brute vient de l'ADEME (source, non réécrite ;
                    # 1 DPE à 1761). La garde vise la VALEUR SERVIE sur la fiche (callable), pas la source
                    # ADEME : une année aberrante n'est jamais servie (« année inconnue »). Comme FIX-1 a
                    # recadré ses gardes sur la vérité servie.
                    specs.append(RuleSpec(
                        id=f"{base_id}.annee_servie_bornee", famille="F1",
                        source="/parcels/{idu}.filtre_bati.annee_construction (servie)",
                        libelle="année de construction SERVIE ∈ [1800, "
                                f"{ANNEE}] ou « année inconnue » (jamais la valeur ADEME aberrante)",
                        gravite="INCOHERENT", attendu="0 parcelle servie hors [1800,ANNEE]",
                        check=_check_dpe_annee_servie,
                    ))
                else:
                    specs.append(RuleSpec(
                        id=f"{base_id}.annee_bornee", famille="F1", source=base_id,
                        libelle=f"{table}.{col.nom} ∈ [1800, {ANNEE}] sur les lignes servies",
                        gravite="INCOHERENT", attendu=f"0 ligne hors [1800,{ANNEE}]",
                        sql_violations=(
                            f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND ({col.nom} < 1800 OR {col.nom} > {ANNEE})"),
                        exemples_sql=(
                            f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND ({col.nom} < 1800 OR {col.nom} > {ANNEE}) LIMIT 3"),
                    ))

            # ── 2b. bornes : âge ────────────────────────────────────────────────────────────
            if col.numerique and _RX_AGE.search(col.nom) and not _RX_TECHNIQUE.search(col.nom):
                n_gen += 1
                specs.append(RuleSpec(
                    id=f"{base_id}.age_borne", famille="F1", source=base_id,
                    libelle=f"{table}.{col.nom} ∈ [0,120]",
                    gravite="INCOHERENT", attendu="0 ligne hors [0,120]",
                    sql_violations=(
                        f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND ({col.nom} < 0 OR {col.nom} > 120)"),
                    exemples_sql=(
                        f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND ({col.nom} < 0 OR {col.nom} > 120) LIMIT 3"),
                ))

            # ── 2c. bornes : pct / taux ≤ 100 (UNIQUEMENT valeur servie/rendue) ─────────────
            if (col.numerique or col.type_sql == "real") and _RX_PCT.search(col.nom):
                n_gen += 1
                if col.nom in _RX_PCT_BASE_DEPASSE:
                    ecartees.append(Ecartee(f"{base_id}.pct_max100", "F1", base_id,
                        "pct de BASE qui dépasse légitimement 100 (clampé au rendu — vague-1 E-01)"))
                elif _RX_TAUX_IMPOT.search(col.nom):
                    ecartees.append(Ecartee(f"{base_id}.pct_max100", "F1", base_id,
                        "taux d'imposition/vote (TFPB/TFPNB/TEOM/CFE/part_communale) — pas de plafond 100 garanti"))
                elif _RX_TECHNIQUE.search(col.nom):
                    ecartees.append(Ecartee(f"{base_id}.pct_max100", "F1", base_id,
                        "colonne technique malgré le motif pct/taux"))
                else:
                    specs.append(RuleSpec(
                        id=f"{base_id}.pct_max100", famille="F1", source=base_id,
                        libelle=f"{table}.{col.nom} ≤ 100 (pct servi) sur les lignes servies",
                        gravite="FAUX-CLIENT", attendu="0 ligne > 100",
                        sql_violations=(
                            f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND {col.nom} > 100"),
                        exemples_sql=(
                            f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND {col.nom} > 100 LIMIT 3"),
                    ))

            # ── 2d. bornes : pente ≤ 90° ────────────────────────────────────────────────────
            if (col.numerique or col.type_sql == "real") and _RX_PENTE.search(col.nom):
                n_gen += 1
                specs.append(RuleSpec(
                    id=f"{base_id}.pente_max90", famille="F1", source=base_id,
                    libelle=f"{table}.{col.nom} ≤ 90° (angle de pente)",
                    gravite="INCOHERENT", attendu="0 ligne > 90",
                    sql_violations=(
                        f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND {col.nom} > 90"),
                    exemples_sql=(
                        f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND {col.nom} > 90 LIMIT 3"),
                ))

            # ── 2d-bis. bornes : hauteur de bâtiment ≤ 300 m (plafond physique) ─────────────
            if (col.numerique or col.type_sql == "real") and _RX_HAUTEUR_M.search(col.nom):
                n_gen += 1
                _ex = _expr_servie(table, col.nom)          # FIX-2 : valeur SERVIE (bornée pour le LiDAR)
                specs.append(RuleSpec(
                    id=f"{base_id}.hauteur_max300", famille="F1", source=base_id,
                    libelle=f"{table}.{col.nom} ≤ 300 m (hauteur bâti physiquement plausible)",
                    gravite="FAUX-CLIENT", attendu="0 ligne > 300",
                    sql_violations=(
                        f"SELECT count(*) FROM {table} WHERE ({pred}) AND {_ex} IS NOT NULL "
                        f"AND {_ex} > 300"),
                    exemples_sql=(
                        f"SELECT * FROM {table} WHERE ({pred}) AND {_ex} IS NOT NULL "
                        f"AND {_ex} > 300 LIMIT 3"),
                ))

            # ── 2e. bornes : probabilité / score normalisé 0..1 ─────────────────────────────
            if (table, col.nom) in _RX_PROBA:
                n_gen += 1
                specs.append(RuleSpec(
                    id=f"{base_id}.proba_max1", famille="F1", source=base_id,
                    libelle=f"{table}.{col.nom} ∈ [0,1] (probabilité / score normalisé)",
                    gravite="INCOHERENT", attendu="0 ligne hors [0,1]",
                    sql_violations=(
                        f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND ({col.nom} < 0 OR {col.nom} > 1)"),
                    exemples_sql=(
                        f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND ({col.nom} < 0 OR {col.nom} > 1) LIMIT 3"),
                ))

            # ── 3. dates d'événement : ni futures ni absurdement anciennes ──────────────────
            if col.date_like and not _RX_TECHNIQUE.search(col.nom):
                n_gen += 2
                if _RX_DATE_FUTUR_OK.search(col.nom):
                    ecartees.append(Ecartee(f"{base_id}.date_pas_future", "F1", base_id,
                        "date portant légitimement du futur (limite/echeance/expiration/validite)"))
                else:
                    specs.append(RuleSpec(
                        id=f"{base_id}.date_pas_future", famille="F1", source=base_id,
                        libelle=f"{table}.{col.nom} n'est pas dans le futur (> now())",
                        gravite="INCOHERENT", attendu="0 ligne > now()",
                        sql_violations=(
                            f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND {col.nom} > now()"),
                        exemples_sql=(
                            f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                            f"AND {col.nom} > now() LIMIT 3"),
                    ))
                # trop ancienne : TOUJOURS une anomalie (même date_limite ne remonte pas avant 1900)
                specs.append(RuleSpec(
                    id=f"{base_id}.date_pas_absurde", famille="F1", source=base_id,
                    libelle=f"{table}.{col.nom} n'est pas antérieure à 1900",
                    gravite="INCOHERENT", attendu="0 ligne < 1900-01-01",
                    sql_violations=(
                        f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND {col.nom} < '1900-01-01'"),
                    exemples_sql=(
                        f"SELECT * FROM {table} WHERE ({pred}) AND {col.nom} IS NOT NULL "
                        f"AND {col.nom} < '1900-01-01' LIMIT 3"),
                ))

    # ── 4. énumérations à domaine légal fermé ────────────────────────────────────────────────
    for table, col, pred, valeurs in ENUMS:
        n_gen += 1
        if not table_existe(cx, table):
            ecartees.append(Ecartee(f"F1.{table}.{col}.enum", "F1", f"{table}.{col}", "table absente"))
            continue
        liste = ", ".join("'%s'" % v for v in valeurs)
        specs.append(RuleSpec(
            id=f"F1.{table}.{col}.enum", famille="F1", source=f"{table}.{col}",
            libelle=f"{table}.{col} ∈ {{{', '.join(valeurs)}}} (domaine légal fermé)",
            gravite="FAUX-CLIENT", attendu="0 ligne hors domaine",
            sql_violations=(
                f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col} IS NOT NULL "
                f"AND {col} NOT IN ({liste})"),
            exemples_sql=(
                f"SELECT * FROM {table} WHERE ({pred}) AND {col} IS NOT NULL "
                f"AND {col} NOT IN ({liste}) LIMIT 3"),
        ))

    # ── 5. nullités attendues sur lignes servies ────────────────────────────────────────────
    for table, pred, col, lib in NON_NULS:
        n_gen += 1
        if not table_existe(cx, table):
            ecartees.append(Ecartee(f"F1.{table}.{col}.non_nul", "F1", f"{table}.{col}", "table absente"))
            continue
        specs.append(RuleSpec(
            id=f"F1.{table}.{col}.non_nul", famille="F1", source=f"{table}.{col}",
            libelle=f"{lib} ({table}.{col} non-null)",
            gravite="FAUX-CLIENT", attendu="0 ligne servie sans valeur",
            sql_violations=f"SELECT count(*) FROM {table} WHERE ({pred}) AND {col} IS NULL",
            exemples_sql=f"SELECT * FROM {table} WHERE ({pred}) AND {col} IS NULL LIMIT 3",
        ))

    return specs, ecartees, n_gen


def main():
    cx = connexion()
    specs, ecartees, n_gen = generer(cx)
    print(f"GÉNÉRÉES : {n_gen}")
    print(f"RETENUES : {len(specs)}")
    print(f"ÉCARTÉES : {len(ecartees)}")
    raisons = {}
    for e in ecartees:
        raisons[e.raison] = raisons.get(e.raison, 0) + 1
    print("— raisons d'écart :")
    for r, c in sorted(raisons.items(), key=lambda x: -x[1]):
        print(f"    {c:4d}  {r}")

    print("\n— exécution des règles retenues (lecture seule) —")
    resultats = run_specs(cx, specs, api=API)
    b = bilan(resultats)
    print(f"OK={b.get('OK',0)}  ECART={b.get('ECART',0)}  SKIP={b.get('SKIP',0)}")

    for r in resultats:
        if r.statut == "ECART":
            print(f"\n  ECART · {r.spec.id} · {r.spec.gravite}")
            print(f"    {r.message}")
            for ex in r.exemples[:3]:
                petit = {k: v for k, v in list(ex.items())[:6]}
                print(f"    ex: {petit}")
    for r in resultats:
        if r.statut == "SKIP":
            print(f"  SKIP · {r.spec.id} : {r.message}")


if __name__ == "__main__":
    main()
