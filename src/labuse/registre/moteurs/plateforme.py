"""CIRCUIT-2 lot 1.6 — moteur `plateforme_compteurs` : les compteurs GLOBAUX de la plateforme
(accueil, pilotage admin, notifications, kanban, Radar admin), extraits des endpoints. Un robinet
ne calcule pas : il appelle ici.

Restent chez leur producteur nommé (délégation, une seule vérité — pas de copie ici) :
`n_a_faire` (etats_sources.compteurs sur lister_etats), `n_veilles` (copilote_v2/veilles.py:lister),
`projet_cadrage_n`/`projet_retenues_n` (api/projets.py:_counts_by_projet) et `courrier_demandes_n`
(courrier.py:demandes_de).
"""
from __future__ import annotations

from sqlalchemy import text


def compte_parcelles_ile(db, run: str | None) -> int | None:
    """n_parcelles_ile — count parcels du run servi, MESURÉ jamais en dur : registre
    `p_score_v2_runs.n_parcelles` (lecture par clé primaire, RETOURS-10 T2), repli count vif si le
    registre ne connaît pas le run. Un chiffre indisponible vaut null (jamais une invention)."""
    def _one(sql: str, params: dict) -> int | None:
        try:
            v = db.execute(text(sql), params).scalar()
            return int(v) if v is not None else None
        except Exception:  # noqa: BLE001 — un chiffre indisponible = null, jamais une invention
            return None
    return (_one("SELECT n_parcelles FROM p_score_v2_runs WHERE run_id = :r", {"r": run})
            or _one("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r", {"r": run}))


def bascules_tiers_hauts(db, run_courant: str | None, run_precedent: str | None) -> int | None:
    """n_bascules_7j — parcelles entrées dans les tiers hauts (brûlante/chaude) entre le run
    précédent et le run servi (pointeur vivant, DONNEES-2 B4). Extraction de api/accueil.py."""
    try:
        v = db.execute(text(
            "SELECT count(*) FROM parcel_p_score_v2 a "
            "JOIN parcel_p_score_v2 b ON b.parcelle_id = a.parcelle_id AND b.run_id = :cur "
            "WHERE a.run_id = :prev AND b.tier IN ('brulante','chaude') "
            "  AND (a.tier IS NULL OR a.tier NOT IN ('brulante','chaude'))",
        ), {"cur": run_courant, "prev": run_precedent}).scalar()
        return int(v) if v is not None else None
    except Exception:  # noqa: BLE001 — un chiffre indisponible = null, jamais une invention
        return None


def comptes_actifs(c) -> int:
    """n_comptes_actifs — count comptes au statut actif (tuile Pilotage). Extraction de
    api/dashboard.py:admin_pilotage."""
    return int(c.execute(text("SELECT COUNT(*) FROM comptes WHERE statut = 'actif'")).scalar() or 0)


def conso_ia_mois(c) -> dict:
    """ia_cout_eur — somme des coûts du ledger ia_log sur le mois courant (+ nombre d'appels).
    Extraction de api/dashboard.py (admin_pilotage + admin_ia, MÊME requête des deux côtés)."""
    return c.execute(text(
        "SELECT COALESCE(SUM(cout_eur), 0) AS cout, COUNT(*) AS appels FROM ia_log"
        " WHERE ts >= date_trunc('month', now())")).mappings().one()


def conso_ia_30j(c) -> dict:
    """ia_cout_eur — la ventilation 30 jours du ledger ia_log : barres par jour, par licence, et
    cumul 7 jours (projection fin de mois). Extraction de api/dashboard.py:admin_ia."""
    jours = [dict(r) for r in c.execute(text(
        "SELECT date_trunc('day', ts)::date AS jour, ROUND(SUM(cout_eur), 4) AS cout,"
        "       COUNT(*) AS appels"
        " FROM ia_log WHERE ts > now() - interval '30 days'"
        " GROUP BY 1 ORDER BY 1")).mappings()]
    par_licence = [dict(r) for r in c.execute(text(
        "SELECT l.compte_id, COALESCE(k.nom, 'Vous (admin/pilote)') AS nom,"
        "       ROUND(SUM(l.cout_eur), 4) AS cout, COUNT(*) AS appels"
        " FROM ia_log l LEFT JOIN comptes k ON k.id = l.compte_id"
        " WHERE l.ts > now() - interval '30 days'"
        " GROUP BY l.compte_id, k.nom ORDER BY SUM(l.cout_eur) DESC")).mappings()]
    cout_7j = float(c.execute(text(
        "SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log"
        " WHERE ts > now() - interval '7 days'")).scalar() or 0)
    return {"jours": jours, "par_licence": par_licence, "cout_7j": cout_7j}


def usage_par_outil(c, jours: int) -> list[dict]:
    """usage_outil_n — compte d'événements d'usage par outil sur la fenêtre choisie (7/30/90 j).
    Extraction de api/dashboard.py:admin_produit."""
    return [dict(r) for r in c.execute(text(
        "SELECT outil, COUNT(*) AS n FROM usage_events"
        " WHERE kind = 'outil' AND outil IS NOT NULL AND ts > now() - make_interval(days => :j)"
        " GROUP BY outil ORDER BY COUNT(*) DESC"), {"j": jours}).mappings()]


def notifications_non_lues(db, cid: int | None, *, cloche_filter_sql: str = "") -> int:
    """n_notifications — count event_log non lus du compte (fragments _visible/_seen d'events.py,
    la SÉMANTIQUE de visibilité/lecture reste chez events). Extraction de api/events.py
    (list_events + events_count, même requête des deux côtés)."""
    from ...api.events import _MARKET_KINDS, _seen, _visible
    return int(db.execute(text(
        f"SELECT count(*) FROM event_log e WHERE {_visible('e')} AND NOT {_seen('e')}{cloche_filter_sql}"),
        {"cid": cid, "market": list(_MARKET_KINDS)}).scalar() or 0)


def cartes_par_colonne(db, cid: int | None) -> dict[str, int]:
    """crm_cartes_n · pipeline_entrees_n — count des entrées du pipeline (retour terrain) par
    statut/colonne, périmètre du compte. Extraction de api/crm_columns.py:list_columns."""
    return {r[0]: r[1] for r in db.execute(text(
        "SELECT status, count(*) FROM pipeline_entries WHERE compte_id IS NOT DISTINCT FROM :cid"
        " GROUP BY status"), {"cid": cid})}


def depots_a_verifier(c) -> int:
    """n_depots_a_verifier — la file d'extraction Radar : faits déposés en attente de validation
    humaine (pige_faits.valide_at NULL). Extraction de pige/api.py:radar_check."""
    return int(c.execute(text(
        "SELECT count(*) FROM pige_faits WHERE valide_at IS NULL")).scalar() or 0)
