"""Veille (offre C, brief §5) — moteur SNAPSHOT / DELTA.

Un run de veille compare l'état courant de la commune à la photo mémorisée au run
précédent (watch_snapshots) et écrit les CHANGEMENTS dans parcel_signals, puis
RE-DÉCLENCHE la cascade sur les parcelles concernées (le rapace re-regarde quand
la zone bouge — il ne fait pas que logguer).

État surveillé par parcelle :
- gpu_zone    : zone PLU/GPU dominante       → signal `zonage_change`
- dvf_last    : dernière mutation DVF ≤ rayon → signal `mutation_dvf`
- permit_last : dernier permis ≤ rayon        → signal `new_permit_nearby`

Premier run = photo de référence (aucune alerte). Sources DOM 974 RÉELLES :
DVF via ODS (l_idpar), permis via ODS (réf. cadastrale) — cf. ingestion/dvf & permits.
Les deltas mutation/permis ne se déclenchent qu'au rafraîchissement de ces sources
(données millésimées) ; zonage_change se déclenche dès qu'un zonage PLU évolue.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


def _current_state(session: Session, commune: str, dvf_radius_m: int, permit_radius_m: int):
    zones = dict(session.execute(
        text(
            """SELECT DISTINCT ON (p.id) p.id, sl.subtype
               FROM parcels p JOIN spatial_layers sl
                 ON sl.kind = 'plu_gpu_zone' AND ST_Intersects(p.geom, sl.geom)
               WHERE p.commune = :c
               ORDER BY p.id, ST_Area(ST_Intersection(ST_Transform(p.geom,2975), ST_Transform(sl.geom,2975))) DESC"""
        ), {"c": commune}
    ).all())
    dvf = dict(session.execute(
        text(
            """SELECT p.id, max(d.date_mutation) FROM parcels p JOIN dvf_mutations d
                 ON ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(d.geom,2975), :r)
               WHERE p.commune = :c GROUP BY p.id"""
        ), {"c": commune, "r": dvf_radius_m}
    ).all())
    permit = dict(session.execute(
        text(
            """SELECT p.id, max(s.date) FROM parcels p JOIN sitadel_permits s
                 ON s.geom IS NOT NULL AND ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(s.geom,2975), :r)
               WHERE p.commune = :c GROUP BY p.id"""
        ), {"c": commune, "r": permit_radius_m}
    ).all())
    return zones, dvf, permit


def run_watch(session: Session, commune: str, *, dvf_radius_m: int = 200,
              permit_radius_m: int = 200, reevaluate: bool = True) -> dict:
    """Exécute un run de veille : détecte les deltas, écrit les signaux, ré-évalue."""
    zones, dvf, permit = _current_state(session, commune, dvf_radius_m, permit_radius_m)
    snaps = {
        pid: (z, dl, pl)
        for pid, z, dl, pl in session.execute(
            text(
                """SELECT ws.parcel_id, ws.gpu_zone, ws.dvf_last, ws.permit_last
                   FROM watch_snapshots ws JOIN parcels p ON p.id = ws.parcel_id WHERE p.commune = :c"""
            ), {"c": commune}
        ).all()
    }
    baseline = len(snaps) == 0
    counts = {"zonage_change": 0, "mutation_dvf": 0, "new_permit_nearby": 0}
    affected: set[int] = set()

    def add_signal(pid: int, typ: str, payload: dict) -> None:
        session.execute(
            text(
                """INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
                   VALUES (:pid, :t, CAST(:p AS jsonb), now())"""
            ), {"pid": pid, "t": typ, "p": json.dumps(payload)}
        )
        counts[typ] += 1
        affected.add(pid)

    all_pids = set(zones) | set(dvf) | set(permit) | set(snaps)
    if not baseline:
        for pid in all_pids:
            if pid not in snaps:
                continue  # parcelle nouvelle → photographiée, pas d'alerte
            sz, sd, sp = snaps[pid]
            cz, cd, cp = zones.get(pid), dvf.get(pid), permit.get(pid)
            if cz and sz and cz != sz:
                add_signal(pid, "zonage_change", {"from": sz, "to": cz})
            if cd and (sd is None or cd > sd):
                add_signal(pid, "mutation_dvf", {"date_mutation": str(cd), "within_m": dvf_radius_m})
            if cp and (sp is None or cp > sp):
                add_signal(pid, "new_permit_nearby", {"date": str(cp), "within_m": permit_radius_m})

    # Mise à jour de la photo → état courant (upsert).
    for pid in all_pids:
        session.execute(
            text(
                """INSERT INTO watch_snapshots (parcel_id, gpu_zone, dvf_last, permit_last, updated_at)
                   VALUES (:pid, :z, :d, :p, now())
                   ON CONFLICT (parcel_id) DO UPDATE SET
                     gpu_zone = EXCLUDED.gpu_zone, dvf_last = EXCLUDED.dvf_last,
                     permit_last = EXCLUDED.permit_last, updated_at = now()"""
            ), {"pid": pid, "z": zones.get(pid), "d": dvf.get(pid), "p": permit.get(pid)}
        )
    session.flush()

    reev = 0
    if reevaluate and affected:
        from ..cascade import evaluate_parcels  # import local : évite un cycle
        evaluate_parcels(list(affected), session, persist=True)
        reev = len(affected)

    return {"baseline": baseline, **counts, "signals_total": sum(counts.values()), "reevaluated": reev}
