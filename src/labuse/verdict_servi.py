"""M34 (dette #14) — POINT DE TRADUCTION UNIQUE tier servi → verdict de fiche.

Le verdict affiché par TOUTE surface non-v2 (fiche legacy, exports md/html,
comparateur, assistant IA, shortlist, Kanban, /parcels sans source) est une TRADUCTION du
tier servi (`parcel_p_score_v2`, run `Q_A_RUN_LABEL`) — jamais un re-calcul. Le rail cascade
legacy (`parcel_evaluations.status`, logique pré-M28) ne pilote plus aucun verdict : ses
signaux non-francs (accès, pente, surface, bâti partiel) restent des points de VIGILANCE
informatifs, ils ne contredisent plus le classement (constat M34-P0 : 3 251 déclassements
silencieux + 2 263 divergences montantes).

Ce module LIT :
- `parcel_p_score_v2.tier/rang` (run servi) — la seule vérité de classement ;
- `parcel_filtre_bati.decision/ratio_pct/motif` — badge « bâtie + division possible »
  (étage 3 divisible = servable, M28) et motif des bâties saturées ;
- `served_run_exceptions.motif` — motif du registre quand la parcelle y figure.

Il n'écrit RIEN. Libellés alignés sur le front (`frontend/src/lib/status.ts`,
TIER_V2_META / TIER_DECLASSE_META) — une seule échelle à l'écran comme au papier.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import runs

#: tiers actifs (servables) — même liste que le front (LEGEND_V2_ORDER).
TIERS_SERVABLES = ("brulante", "chaude", "reserve_fonciere", "a_creuser")

# M135 — les libellés client des tiers viennent du MAPPING CANONIQUE UNIQUE (tiers_client).
# M137 — TIER_LABELS = le CHIP COURT (« Priorité », « À suivre »…), le mot SERVI PARTOUT : chips,
# bande de résumé, cartes, fiche, PDF, exports, assistant. Un seul vocabulaire à l'écran, celui
# des chips — le client relie toujours le même palier au même mot. Le libellé LONG (« À contacter
# en priorité ») ne vit QUE dans l'explication du « i » des paliers (front), accolé à son chip.
from .scoring.tiers_client import TIERS_CLIENT  # noqa: E402  # GB-012 : tier_court/tier_long retirés (imports morts)
TIER_LABELS = {k: v[0] for k, v in TIERS_CLIENT.items()}

# M129-C P3 (réconciliation) : le badge M28 lisait `parcel_filtre_bati` et prétendait juger la
# DIVISIBILITÉ — c'était un 2e juge (l'audit division_or l'a nommé). Il se RENOMME : il dit un
# FAIT bâti (emprise marginale), le SEUL juge de divisibilité servi est division_or_candidates
# (industrialisé M129-C), lu par la fiche (ligne « Division ») et la facette « Divisible ».
BADGE_DIVISION = "bâtie — emprise marginale"

#: couleur des déclassements — « terre éteinte », MIROIR de DECLASSE_COLOR (frontend/status.ts),
#: hors palette thermique (jamais « chaude »). Une seule valeur écran / papier / carte M-Q.
DECLASSE_COLOR = "#8C7468"
DECLASSE_RGB = (140, 116, 104)


# M89 — le PÉRIMÈTRE du dénominateur + le motif copro, écrits UNE fois (un critère = un endroit).
# rang_total exclut les copropriétés (hors univers de classement) : le chiffre servi doit le DIRE, jamais
# un dénominateur nu. Mesuré M89 : les 3 424 sans rang = exactement les 3 424 copropriétés (corrélation
# 100 %). Raison EXACTE (arbitrage Vic) : ce n'est pas le morcellement qui exclut, c'est l'absence
# d'assiette foncière mobilisable. Banquier ET fiche portent le même libellé corrigé.
_COPRO_RAISON = "pas d'assiette foncière mobilisable"
RANG_PERIMETRE = f"copropriétés hors univers de classement — {_COPRO_RAISON}"
#: motif servi sur la FICHE d'une copropriété, à la place du rang omis (jamais un vide).
COPRO_MOTIF = f"Copropriété — hors univers de classement ({_COPRO_RAISON})"


def rang_total(db: Session, run: str | None = None) -> int | None:
    """Dénominateur du rang servi : nombre de parcelles CLASSÉES (hors copropriétés) du run.
    Un rang ne dit rien sans lui (« rang 57 643 / 428 239 »). Lecture seule, niveau run."""
    if run is None:
        run = runs.current()
    return db.execute(text(
        "SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r AND rang IS NOT NULL"),
        {"r": run}).scalar()

#: hors run servi (parcelle absente de la table) — on le DIT, jamais un repli legacy muet.
NON_EVALUEE = {
    "statut": "non_evaluee", "label": "Non évaluée au run servi", "tier": None,
    "rang": None, "servable": False, "declasse": False,
    "badge_division": False, "badge_division_libelle": None,
    "motif": None, "exception_registre": False, "run": None,
}

#: repli quand une exception du registre n'a pas (encore) de motif client — on dit le fait
#: sans exposer la machinerie interne (M35 Lot B : le motif brut ne sort JAMAIS).
MOTIF_CLIENT_FALLBACK = ("Classement ajusté après vérification manuelle — détail disponible "
                         "sur demande.")


def _sql(db: Session) -> str:
    """SELECT de traduction — les caches optionnels (`parcel_filtre_bati`, registre
    `served_run_exceptions`) sont joints SEULEMENT s'ils existent (base de test, install
    neuve) : leur absence dégrade en badge/motif absents, jamais en 500.

    M35 Lot B : le registre porte DEUX motifs — `motif` (interne, traçabilité, jamais servi)
    et `motif_client` (formulation produit). Seul `motif_client` sort d'ici ; une exception
    sans motif client reçoit MOTIF_CLIENT_FALLBACK, jamais le motif brut."""
    has_fb = bool(db.execute(text(
        "SELECT to_regclass('parcel_filtre_bati') IS NOT NULL")).scalar())
    has_ex = bool(db.execute(text(
        "SELECT to_regclass('served_run_exceptions') IS NOT NULL")).scalar())
    has_ex_client = has_ex and bool(db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'served_run_exceptions' AND column_name = 'motif_client')")).scalar())
    fb_cols = ("fb.decision AS fb_decision, fb.ratio_pct AS fb_ratio, fb.motif AS fb_motif"
               if has_fb else
               "NULL AS fb_decision, NULL::float AS fb_ratio, NULL AS fb_motif")
    fb_join = "LEFT JOIN parcel_filtre_bati fb ON fb.idu = s.parcelle_id" if has_fb else ""
    if has_ex:
        ex_col = ("ex.motif_client AS ex_motif_client, (ex.idu IS NOT NULL) AS ex_present"
                  if has_ex_client else
                  "NULL AS ex_motif_client, (ex.idu IS NOT NULL) AS ex_present")
        ex_join = ("LEFT JOIN served_run_exceptions ex ON ex.run_id = s.run_id "
                   "AND ex.idu = s.parcelle_id")
    else:
        ex_col = "NULL AS ex_motif_client, false AS ex_present"
        ex_join = ""
    # ZONE-1 pt2 : zone DOMINANTE de l'écran jointe pour la garde de lecture du résiduel.
    has_zp = bool(db.execute(text(
        "SELECT to_regclass('parcel_zone_plu') IS NOT NULL")).scalar())
    zp_cols = ("zp.zone_fam AS zone_fam, zp.zone_lib AS zone_lib" if has_zp else
               "NULL AS zone_fam, NULL AS zone_lib")
    zp_join = "LEFT JOIN parcel_zone_plu zp ON zp.idu = s.parcelle_id" if has_zp else ""
    return (f"SELECT s.parcelle_id AS idu, s.tier, s.rang, rsd.sdp_residuelle_m2, "
            f"{zp_cols}, {fb_cols}, {ex_col} "
            f"FROM parcel_p_score_v2 s {fb_join} {ex_join} {zp_join} "
            "LEFT JOIN parcels prc ON prc.idu = s.parcelle_id "
            "LEFT JOIN parcel_residuel rsd ON rsd.parcel_id = prc.id AND rsd.cause IS NULL "
            f"WHERE s.run_id = :run AND s.parcelle_id = ANY(:idus)")


def _label_bati(tier: str, row) -> str | None:
    """M129-D P1 — le bâti a DEUX états, jamais un slug : « on peut encore construire »
    (SDP résiduelle > 0) / « construite au maximum ». Repli générique si la SDP n'est pas
    dans la row (SELECT appelant non enrichi)."""
    if tier != "declasse_bati_sature":
        return None
    try:
        sdp = row["sdp_residuelle_m2"]
    except (KeyError, TypeError):
        return None
    if sdp is None:
        return None
    # ZONE-1 pt2 — garde de lecture : en zone dominante A/N, la SDP servie vaut 0 par règle
    # (le chiffre du run suivra à la prochaine bascule).
    try:
        from .faisabilite.zone_servie import garde_sdp_residuelle
        sdp, _ = garde_sdp_residuelle(float(sdp), row["zone_fam"], row["zone_lib"])
    except (KeyError, TypeError):
        pass
    return ("Bâtie — on peut encore construire" if float(sdp) > 0
            else "Bâtie — construite au maximum")


def _traduire(idu: str, row, run: str) -> dict:
    """Ligne SQL → verdict. Pur (testable sans DB via un mapping-like)."""
    tier = row["tier"]
    servable = tier in TIERS_SERVABLES
    declasse = bool(tier and tier.startswith("declasse_"))
    # Badge M28 : bâtie marginale/ancienne DIVISIBLE servie (étage 3 du filtre bâti).
    badge = bool(servable and row["fb_decision"] == "divisible")
    badge_lib = None
    if badge:
        ratio = row["fb_ratio"]
        # M35 Lot C : chaque pourcentage dit CE qu'il mesure — ici bâti au sol / surface de
        # LA PARCELLE (source max BD TOPO/CoSIA), à ne pas confondre avec le taux d'emprise
        # constructible du résiduel.
        badge_lib = (f"{BADGE_DIVISION} (bâti au sol ~{round(ratio)} % de la parcelle)"
                     if ratio is not None else BADGE_DIVISION)
    # Motif : registre d'abord (exception motivée — motif CLIENT uniquement, repli neutre si
    # absent, jamais le motif interne), sinon motif du filtre bâti pour les déclassées bâti
    # saturé, sinon aucun — jamais un motif inventé.
    ex_present = bool(row["ex_present"])
    motif = None
    if ex_present:
        motif = row["ex_motif_client"] or MOTIF_CLIENT_FALLBACK
    elif tier == "declasse_bati_sature":
        motif = row["fb_motif"]
    return {
        # M135 — le label du tier suit l'ÉCHELLE D'ACTION (tiers_client) ; l'état du bâti
        # (« construite au maximum » / « on peut encore construire ») n'est plus dans le tier,
        # il vit sur le badge d'état du bien (M131). Le motif fin reste en `motif`, consultable.
        "statut": tier, "label": TIER_LABELS.get(tier, tier), "tier": tier,
        "rang": row["rang"], "servable": servable, "declasse": declasse,
        "badge_division": badge, "badge_division_libelle": badge_lib,
        "motif": motif, "exception_registre": ex_present,
        "run": run,
    }


def verdict_servi_batch(db: Session, idus: list[str], run: str | None = None) -> dict[str, dict]:
    """{idu → verdict} en UNE requête. IDU absent du run → NON_EVALUEE (présent dans le retour)."""
    if run is None:
        run = runs.current()
    out: dict[str, dict] = {i: dict(NON_EVALUEE) for i in idus}
    if not idus:
        return out
    for r in db.execute(text(_sql(db)), {"run": run, "idus": list(idus)}).mappings().all():
        out[r["idu"]] = _traduire(r["idu"], r, run)
    return out


def verdict_servi(db: Session, idu: str, run: str | None = None) -> dict:
    """Verdict traduit d'UNE parcelle (fiche). Toujours un dict — jamais None, jamais legacy."""
    return verdict_servi_batch(db, [idu], run)[idu]


def sql_exists_servable(alias_parcels: str = "p", param_run: str = "vs_run") -> str:
    """Fragment WHERE pour les SÉLECTIONS (shortlist, voisinage, enrichment) : la parcelle est
    servie dans un tier actif du run. À utiliser avec params[param_run] = Q_A_RUN_LABEL.
    Un seul point de vérité pour « actionnable » — plus jamais e.status legacy."""
    tiers = ", ".join(f"'{t}'" for t in TIERS_SERVABLES)
    return (f"EXISTS (SELECT 1 FROM parcel_p_score_v2 vs WHERE vs.parcelle_id = {alias_parcels}.idu "
            f"AND vs.run_id = :{param_run} AND vs.tier IN ({tiers}))")
