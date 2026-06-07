"""Veille (offre C, brief §5) — génération de signaux dans parcel_signals.

Amorce de la veille : on re-balaie les couches dynamiques déjà ingérées et on
matérialise des SIGNAUX par parcelle. Idempotent (purge avant regénération).

- MUTATION_DVF      : une mutation DVF s'est produite sur / près de la parcelle.
- NEW_PERMIT_NEARBY : un permis SITADEL récent à proximité (signal de zone, §7bis).
- ZONAGE_CHANGE     : changement de zonage PLU (nécessite un historique → à venir,
  détecté par diff au prochain ré-ingest).

En production la veille tourne sur signal (cron) avec une fenêtre « depuis le
dernier passage » ; ici la fenêtre est paramétrable.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

_PURGE = text(
    """DELETE FROM parcel_signals
       WHERE signal_type IN ('mutation_dvf', 'new_permit_nearby')
         AND parcel_id IN (SELECT id FROM parcels WHERE commune = :c)"""
)

_MUTATION_DVF = text(
    """
    INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
    SELECT p.id, 'mutation_dvf',
           jsonb_build_object('valeur_fonciere', d.valeur_fonciere,
                              'date_mutation', d.date_mutation,
                              'type_local', d.type_local, 'within_m', :r),
           now()
    FROM parcels p
    JOIN LATERAL (
        SELECT d.* FROM dvf_mutations d
        WHERE ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(d.geom, 2975), :r)
          AND (d.date_mutation IS NULL OR d.date_mutation >= now() - (:mo || ' months')::interval)
        ORDER BY d.date_mutation DESC NULLS LAST
        LIMIT 1
    ) d ON true
    WHERE p.commune = :c
    """
)

_NEW_PERMIT = text(
    """
    INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
    SELECT DISTINCT p.id, 'new_permit_nearby',
           jsonb_build_object('within_m', :r, 'lookback_months', :mo), now()
    FROM parcels p
    JOIN sitadel_permits s
      ON s.geom IS NOT NULL
     AND ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(s.geom, 2975), :r)
     AND (s.date IS NULL OR s.date >= now() - (:mo || ' months')::interval)
    WHERE p.commune = :c
    """
)


def generate_signals(session: Session, commune: str, *, dvf_radius_m: int = 150,
                     dvf_lookback_months: int = 120, permit_radius_m: int = 200,
                     permit_lookback_months: int = 36) -> dict[str, int]:
    """(Re)génère les signaux de veille pour la commune. Renvoie le compte par type."""
    session.execute(_PURGE, {"c": commune})
    nd = session.execute(_MUTATION_DVF, {"c": commune, "r": dvf_radius_m, "mo": dvf_lookback_months}).rowcount
    npm = session.execute(_NEW_PERMIT, {"c": commune, "r": permit_radius_m, "mo": permit_lookback_months}).rowcount
    session.flush()
    return {"mutation_dvf": int(nd or 0), "new_permit_nearby": int(npm or 0), "zonage_change": 0}
