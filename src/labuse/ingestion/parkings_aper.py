"""Lot 3 Habitat Solaire — parkings APER : le lead à deadline légale.

Cadre juridique VÉRIFIÉ (11/07/2026) :
- loi n° 2023-175 du 10/03/2023 (APER), art. 40 : ombrières avec production d'EnR
  sur ≥ 50 % de la superficie des parcs de stationnement EXTÉRIEURS (mixte
  PV/végétalisé admis depuis la loi Huwart) ;
- décret n° 2024-1023 du 13/11/2024 : superficie = emplacements + voies de
  circulation (espaces verts et zones de stockage exclus) ; exemptions (ombrage
  arboré, contraintes techniques/patrimoniales, coût disproportionné) ;
- décret n° 2025-802 du 11/08/2025 : seuil ADAPTÉ OUTRE-MER — LA RÉUNION = 1 000 m²
  (métropole 1 500, Guyane 2 500) ;
- échéances parcs existants : 1er juillet 2026 (≥ 10 000 m²) — DÉPASSÉE —,
  1er juillet 2028 (1 000-10 000 m²). Sanctions ANNUELLES jusqu'à mise en
  conformité : 20 k€ (< 10 000 m²) / 40 k€ (≥ 10 000 m²).
Tous les seuils/dates vivent en config (habitat_solaire.yaml, section aper).

Détection : polygones OSM amenity=parking DÉJÀ ingérés (spatial_layers
kind='osm_faux_positif', couche d'exclusion du résiduel, 24 communes, dédup par
osm_id) — pas de couche stationnement BD TOPO en base. Complétude OSM déclarative :
la volumétrie est un PLANCHER, pas un recensement. `equipe` reste NULL (l'ombrière
existante n'est pas détectable sans ML ortho — Lot 4.3 stub) ; `exempt_probable`
reste NULL (pas de couche végétation BD TOPO en base — ne pas sur-ingénierer).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import habitat_solaire
from .habitat_solaire_schema import ensure_schema


def _cfg() -> dict[str, Any]:
    return habitat_solaire()["aper"]


def build_parkings(session: Session) -> dict[str, int]:
    """Couche OSM → parkings_aper (dédup osm_id, surface géodésique, tranches/échéances)."""
    ensure_schema(session)
    cfg = _cfg()
    n = session.execute(text("""
        WITH osm AS (
          SELECT DISTINCT ON (sl.attrs ->> 'osm_id')
                 sl.attrs ->> 'osm_id' AS osm_id,
                 -- relations multipolygones : on garde le plus grand polygone
                 (SELECT (d.geom) FROM ST_Dump(ST_CollectionExtract(ST_MakeValid(sl.geom), 3)) d
                  ORDER BY ST_Area(d.geom) DESC LIMIT 1) AS geom
          FROM spatial_layers sl
          WHERE sl.kind = 'osm_faux_positif' AND sl.subtype = 'parking'
          ORDER BY sl.attrs ->> 'osm_id', sl.id
        ),
        mesure AS (
          SELECT osm_id, geom, ST_Area(geom::geography) AS surface_m2 FROM osm
          WHERE geom IS NOT NULL
        )
        INSERT INTO parkings_aper (geom, geom_2975, surface_m2, source, source_ref,
                                   tranche, echeance)
        SELECT geom, ST_Transform(ST_SetSRID(geom, 4326), 2975), round(surface_m2)::numeric,
               'osm', osm_id,
               CASE WHEN surface_m2 >= :haute THEN 'sup_10000'
                    WHEN surface_m2 > :seuil THEN '1000_10000' END,
               CASE WHEN surface_m2 >= :haute THEN CAST(:ech_haute AS date)
                    WHEN surface_m2 > :seuil THEN CAST(:ech_basse AS date) END
        FROM mesure
        WHERE surface_m2 > :detect
        ON CONFLICT (source, source_ref) WHERE source_ref IS NOT NULL
        DO UPDATE SET geom = EXCLUDED.geom, geom_2975 = EXCLUDED.geom_2975,
                      surface_m2 = EXCLUDED.surface_m2, tranche = EXCLUDED.tranche,
                      echeance = EXCLUDED.echeance, updated_at = now()
    """), {"detect": float(cfg["surface_detection_min_m2"]),
           "seuil": float(cfg["surface_assujettie_m2"]),
           "haute": float(cfg["tranche_haute_m2"]),
           "ech_haute": str(cfg["echeance_tranche_haute"]),
           "ech_basse": str(cfg["echeance_tranche_basse"])}).rowcount
    counts = dict(session.execute(text(
        "SELECT coalesce(tranche, 'sous_seuil'), count(*) FROM parkings_aper GROUP BY 1")).all())
    return {"parkings": n, **counts}


def rattacher(session: Session) -> dict[str, int]:
    """Parcelles support (jointure spatiale) + propriétaire personne morale DGFiP."""
    session.execute(text("""
        UPDATE parkings_aper pk SET idus = sub.idus, updated_at = now()
        FROM (
          SELECT pk2.id, jsonb_agg(DISTINCT p.idu) AS idus
          FROM parkings_aper pk2
          JOIN parcels p ON ST_Intersects(p.geom_2975, pk2.geom_2975)
            AND ST_Area(ST_Intersection(p.geom_2975, pk2.geom_2975)) > 50
          GROUP BY pk2.id
        ) sub WHERE sub.id = pk.id
    """))
    n_pm = session.execute(text("""
        UPDATE parkings_aper pk
        SET proprio_pm = pm.denomination, proprio_siren = pm.siren, updated_at = now()
        FROM (
          SELECT DISTINCT ON (pk2.id) pk2.id, m.denomination, m.siren
          FROM parkings_aper pk2
          JOIN parcels p ON ST_Intersects(p.geom_2975, pk2.geom_2975)
          JOIN parcelle_personne_morale m ON m.idu = p.idu AND m.denomination IS NOT NULL
          ORDER BY pk2.id,
                   ST_Area(ST_Intersection(p.geom_2975, pk2.geom_2975)) DESC
        ) pm WHERE pm.id = pk.id
    """)).rowcount
    total, avec_idus = session.execute(text(
        "SELECT count(*), count(idus) FROM parkings_aper")).one()
    return {"total": total, "avec_parcelles": avec_idus, "avec_pm": n_pm}


def signaux_deadline(session: Session, *, aujourd_hui: date | None = None) -> int:
    """Signal `aper_deadline` : parkings ASSUJETTIS, non exemptés, échéance < 24 mois
    OU DÉPASSÉE (au 10/07/2026, l'échéance ≥ 10 000 m² est passée : sanctions annuelles
    encourues, sous réserve d'exemptions) — posé sur chaque parcelle support."""
    cfg = _cfg()
    ref = aujourd_hui or date.today()
    session.execute(text(
        "DELETE FROM parcel_signals WHERE signal_type = 'aper_deadline'"))
    return session.execute(text("""
        INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
        SELECT p.id, 'aper_deadline',
               jsonb_build_object(
                 'parking_id', pk.id, 'surface_m2', pk.surface_m2,
                 'tranche', pk.tranche, 'echeance', pk.echeance,
                 'statut', CASE WHEN pk.echeance < CAST(:ref AS date)
                                THEN 'depassee' ELSE 'a_venir' END,
                 'sanction_eur_an', CASE WHEN pk.tranche = 'sup_10000'
                                         THEN :s_haute ELSE :s_basse END,
                 'proprio_pm', pk.proprio_pm),
               now()
        FROM parkings_aper pk
        JOIN parcels p ON jsonb_exists(pk.idus, p.idu)
        WHERE pk.tranche IS NOT NULL
          AND pk.exempt_probable IS NULL
          AND coalesce(pk.equipe, false) = false
          AND pk.echeance < (CAST(:ref AS date)
                             + make_interval(months => CAST(:fenetre AS int)))
    """), {"ref": ref, "fenetre": int(cfg["signal_fenetre_mois"]),
           "s_haute": int(cfg["sanction_haute_eur"]),
           "s_basse": int(cfg["sanction_basse_eur"])}).rowcount


def run(session: Session, log=print) -> dict[str, Any]:
    b = build_parkings(session)
    log(f"  parkings OSM > seuil de détection : {b}")
    r = rattacher(session)
    log(f"  rattachement : {r}")
    n_sig = signaux_deadline(session)
    log(f"  signaux aper_deadline : {n_sig} parcelles")
    return {**b, **r, "signaux": n_sig}
