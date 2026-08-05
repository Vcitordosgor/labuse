"""M34 (dette #14) — POINT DE TRADUCTION UNIQUE tier servi → verdict de fiche.

Le verdict affiché par TOUTE surface non-v2 (fiche legacy, exports md/html/one-pager,
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

from .scoring.score_v_constants import Q_A_RUN_LABEL

#: tiers actifs (servables) — même liste que le front (LEGEND_V2_ORDER).
TIERS_SERVABLES = ("brulante", "chaude", "reserve_fonciere", "a_creuser")

#: libellés client — MIROIR de frontend/src/lib/status.ts (TIER_V2_META + TIER_DECLASSE_META).
TIER_LABELS = {
    "brulante": "Brûlante",
    "chaude": "Chaude",
    "reserve_fonciere": "Réserve foncière",
    "a_creuser": "À creuser",
    "ecartee": "Écartée",
    "declasse_bati_sature": "Déclassée — bâti saturé",
    "declasse_non_constructible": "Déclassée — inconstructible (géométrie)",
    "declasse_bati_revele": "Déclassée — bâti révélé",
    "declasse_zone_fermee": "Déclassée — fermée à l'urbanisation",
    "declasse_au_statut_inconnu": "Déclassée — AU à statut inconnu",
    "declasse_au_fermee": "Déclassée — AU fermée",
}

BADGE_DIVISION = "bâtie + division possible"

#: hors run servi (parcelle absente de la table) — on le DIT, jamais un repli legacy muet.
NON_EVALUEE = {
    "statut": "non_evaluee", "label": "Non évaluée au run servi", "tier": None,
    "rang": None, "servable": False, "declasse": False,
    "badge_division": False, "badge_division_libelle": None,
    "motif": None, "exception_registre": False, "run": None,
}

def _sql(db: Session) -> str:
    """SELECT de traduction — les caches optionnels (`parcel_filtre_bati`, registre
    `served_run_exceptions`) sont joints SEULEMENT s'ils existent (base de test, install
    neuve) : leur absence dégrade en badge/motif absents, jamais en 500."""
    has_fb = bool(db.execute(text(
        "SELECT to_regclass('parcel_filtre_bati') IS NOT NULL")).scalar())
    has_ex = bool(db.execute(text(
        "SELECT to_regclass('served_run_exceptions') IS NOT NULL")).scalar())
    fb_cols = ("fb.decision AS fb_decision, fb.ratio_pct AS fb_ratio, fb.motif AS fb_motif"
               if has_fb else
               "NULL AS fb_decision, NULL::float AS fb_ratio, NULL AS fb_motif")
    fb_join = "LEFT JOIN parcel_filtre_bati fb ON fb.idu = s.parcelle_id" if has_fb else ""
    ex_col = "ex.motif AS ex_motif" if has_ex else "NULL AS ex_motif"
    ex_join = ("LEFT JOIN served_run_exceptions ex ON ex.run_id = s.run_id "
               "AND ex.idu = s.parcelle_id" if has_ex else "")
    return (f"SELECT s.parcelle_id AS idu, s.tier, s.rang, {fb_cols}, {ex_col} "
            f"FROM parcel_p_score_v2 s {fb_join} {ex_join} "
            f"WHERE s.run_id = :run AND s.parcelle_id = ANY(:idus)")


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
        badge_lib = (f"{BADGE_DIVISION} (bâtie à ~{round(ratio)} %)"
                     if ratio is not None else BADGE_DIVISION)
    # Motif : registre d'abord (exception motivée), sinon motif du filtre bâti pour les
    # déclassées bâti saturé, sinon aucun — jamais un motif inventé.
    motif = row["ex_motif"]
    if motif is None and tier == "declasse_bati_sature":
        motif = row["fb_motif"]
    return {
        "statut": tier, "label": TIER_LABELS.get(tier, tier), "tier": tier,
        "rang": row["rang"], "servable": servable, "declasse": declasse,
        "badge_division": badge, "badge_division_libelle": badge_lib,
        "motif": motif, "exception_registre": row["ex_motif"] is not None,
        "run": run,
    }


def verdict_servi_batch(db: Session, idus: list[str], run: str = Q_A_RUN_LABEL) -> dict[str, dict]:
    """{idu → verdict} en UNE requête. IDU absent du run → NON_EVALUEE (présent dans le retour)."""
    out: dict[str, dict] = {i: dict(NON_EVALUEE) for i in idus}
    if not idus:
        return out
    for r in db.execute(text(_sql(db)), {"run": run, "idus": list(idus)}).mappings().all():
        out[r["idu"]] = _traduire(r["idu"], r, run)
    return out


def verdict_servi(db: Session, idu: str, run: str = Q_A_RUN_LABEL) -> dict:
    """Verdict traduit d'UNE parcelle (fiche). Toujours un dict — jamais None, jamais legacy."""
    return verdict_servi_batch(db, [idu], run)[idu]


def sql_exists_servable(alias_parcels: str = "p", param_run: str = "vs_run") -> str:
    """Fragment WHERE pour les SÉLECTIONS (shortlist, voisinage, enrichment) : la parcelle est
    servie dans un tier actif du run. À utiliser avec params[param_run] = Q_A_RUN_LABEL.
    Un seul point de vérité pour « actionnable » — plus jamais e.status legacy."""
    tiers = ", ".join(f"'{t}'" for t in TIERS_SERVABLES)
    return (f"EXISTS (SELECT 1 FROM parcel_p_score_v2 vs WHERE vs.parcelle_id = {alias_parcels}.idu "
            f"AND vs.run_id = :{param_run} AND vs.tier IN ({tiers}))")
