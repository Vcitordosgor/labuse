"""État / readiness de LA BUSE — quatre niveaux, jamais confondus (industrialisation pilote).

1. **App démarrée**  → /healthz : le process répond (zéro accès DB).
2. **Schéma prêt**   → tables, colonnes critiques, triggers, index — réparable en secondes
   (models.ensure_schema, auto au boot).
3. **Données prêtes**→ parcelles + geom_2975 peuplée + couches critiques (PPR/SAR/DVF/OSM)
   + évaluations — reconstruites par `labuse rebuild-demo` (jamais auto au boot).
4. **Démo prête**    → healthcheck 13/13 + parcelles de démo conformes + cache chaud
   (`labuse warm-demo`).

Le serveur qui tourne ne veut PAS dire que LA BUSE est prête : ce module rend chaque
niveau observable (endpoints /readyz, /demo-status ; CLI doctor / prepare-pilot).
Lecture seule — ne modifie jamais rien.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

# Commandes conseillées (affichées telles quelles à l'utilisateur — ne pas cacher l'erreur).
CMD_REBUILD = "labuse rebuild-demo --commune 97415"
CMD_WARM = "labuse warm-demo"
CMD_DOCTOR = "labuse doctor"

_TABLES = ("parcels", "spatial_layers", "dvf_mutations", "parcel_evaluations",
           "cascade_results", "pipeline_entries", "data_sources", "parcel_enrichment")
_COLUMNS = (("parcels", "geom_2975"), ("pipeline_entries", "prospection"))
_TRIGGERS = ("trg_parcels_geom_2975", "trg_layers_geom_2975")
_INDEXES = ("idx_parcels_geom_2975", "idx_spatial_layers_geom_2975", "idx_dvf_geom_2975")


def schema_status(session: Session) -> dict:
    """Niveau 2 — le schéma permet-il de servir sans 500 ? {ok, missing[]}."""
    missing: list[str] = []
    have_tables = {t for (t,) in session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).all()}
    missing += [f"table {t}" for t in _TABLES if t not in have_tables]
    for tbl, col in _COLUMNS:
        if tbl in have_tables and not session.execute(text(
                "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
                {"t": tbl, "c": col}).scalar():
            missing.append(f"colonne {tbl}.{col}")
    have_trg = {t for (t,) in session.execute(text("SELECT tgname FROM pg_trigger")).all()}
    missing += [f"trigger {t}" for t in _TRIGGERS if t not in have_trg]
    have_idx = {i for (i,) in session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname='public'")).all()}
    missing += [f"index {i}" for i in _INDEXES if i not in have_idx]
    return {"ok": not missing, "missing": missing}


def data_status(session: Session, commune: str) -> dict:
    """Niveau 3 — les données critiques de la commune sont-elles là ? {ok, missing[]}.

    Couvre exactement ce que `rebuild-demo` reconstruit ; ne juge PAS la conformité
    fine (top 20, exports…) qui relève du healthcheck complet (niveau 4)."""
    missing: list[str] = []

    def scal(sql: str, **kw) -> int:
        return int(session.execute(text(sql), {"c": commune, **kw}).scalar() or 0)

    n_parcels = scal("SELECT count(*) FROM parcels WHERE commune = :c")
    if n_parcels == 0:
        missing.append(f"parcelles ({commune})")
    elif scal("SELECT count(*) FROM parcels WHERE commune = :c AND geom_2975 IS NULL"):
        missing.append("geom_2975 non peuplée (backfill)")
    for kind, label in (("sar", "SAR"), ("osm_faux_positif", "OSM faux positifs")):
        if not scal("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind=:k", k=kind):
            missing.append(label)
    if not scal("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind IN ('ppr','georisque_alea')"):
        missing.append("PPR / aléas")
    if not scal("SELECT count(*) FROM dvf_mutations WHERE commune = :c"):
        missing.append("DVF geo-dvf")
    if n_parcels and not scal(
            "SELECT count(*) FROM parcel_evaluations e JOIN parcels p ON p.id=e.parcel_id WHERE p.commune=:c"):
        missing.append("évaluations (cascade)")
    return {"ok": not missing, "missing": missing}


def readiness(session: Session, commune: str) -> dict:
    """Vue /readyz : schéma + données critiques, avec l'action à lancer si dégradé."""
    schema = schema_status(session)
    data = data_status(session, commune) if schema["ok"] else {"ok": False, "missing": ["(schéma d'abord)"]}
    actions: list[str] = []
    if not schema["ok"]:
        actions.append(f"{CMD_DOCTOR}  (répare le schéma en secondes)")
    if not data["ok"]:
        actions.append(f"{CMD_REBUILD}  (reconstruit couches + évaluation, ~5 min)")
    return {"ready": schema["ok"] and data["ok"], "commune": commune,
            "schema": schema, "data": data, "actions": actions,
            "checked_at": datetime.now(timezone.utc).isoformat()}


def demo_status(session: Session, commune: str) -> dict:
    """Vue /demo-status (niveau 4) : healthcheck complet + parcelles de démo + cache chaud.

    `ready_for_demo` n'est vrai QUE si healthcheck OK, parcelles conformes ET cache chaud —
    jamais « prêt » juste parce que le serveur tourne."""
    from . import demo as demo_mod

    hc = demo_mod.healthcheck(session, commune)
    overview = demo_mod.demo_overview(session, commune)
    all_conform = bool(overview) and all(p["conforme"] for p in overview)
    idus = [p["idu"] for p in overview]
    warmed = int(session.execute(text(
        "SELECT count(*) FROM parcel_enrichment pe JOIN parcels p ON p.id = pe.parcel_id "
        "WHERE p.idu = ANY(:idus)"), {"idus": idus}).scalar() or 0)
    warm_done = warmed == len(idus) and len(idus) > 0

    actions: list[str] = []
    if not hc["ok"] or not all_conform:
        actions.append(f"{CMD_REBUILD}  (puis revérifier : labuse demo-healthcheck)")
    if not warm_done:
        actions.append(f"{CMD_WARM}  (pré-chauffe les fiches de démo + vérifie conformité/exports)")

    return {
        "commune": commune,
        "healthcheck": {"ok": hc["ok"], "checks": hc["checks"]},
        "demo": {"all_conform": all_conform, "parcels": overview},
        "warm": {"done": warm_done, "warmed": warmed, "total": len(idus)},
        "ready_for_demo": hc["ok"] and all_conform and warm_done,
        "actions": actions,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
