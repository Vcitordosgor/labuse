"""Lot 5 Habitat Solaire — flags de qualification (trivial, forte valeur).

Quatre dérivations de l'EXISTANT (zéro ingestion), écrites dans parcel_solar :
- flag_amiante          : bâti pré-1997 au DPE — un signal de PRUDENCE commerciale
                          (« risque amiante toiture à vérifier »), jamais un diagnostic.
                          NULL sans DPE (vague pilote : 910 DPE → flag rare, honnête).
- flag_abf              : périmètre ABF/abords MH via la cascade pré-calculée
                          (layer 'abf', result UNKNOWN = dans le périmètre).
- azimut_bati_deg       : orientation du grand axe de l'emprise bâtie principale
                          (ST_OrientedEnvelope) ; confiance 'haute' si élongation
                          > seuil (bâti carré = orientation non significative).
                          Rappel UI : hémisphère sud → versant NORD optimal.
- proba_proprio_occupant: part de ménages propriétaires du carreau Filosofi 200 m
                          (INSEE, déjà en base — plus fin que l'IRIS), repli commune
                          (commune_insee_logement), +15 pts si mutation DVF < 24 mois
                          sur maison, borné 5-95. Statistique, jamais nominatif.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import habitat_solaire
from ..segments.registry import CASCADE_RUN
from .habitat_solaire_schema import ensure_schema


def _cfg() -> dict[str, Any]:
    return habitat_solaire()["flags"]


def compute_flag_amiante(session: Session) -> int:
    seuil = int(_cfg()["amiante_annee_max"])
    return session.execute(text("""
        INSERT INTO parcel_solar (idu, flag_amiante, updated_at)
        SELECT d.parcelle_idu, min(d.annee_construction) < :seuil, now()
        FROM dpe_records d
        JOIN parcels p ON p.idu = d.parcelle_idu
        WHERE d.annee_construction IS NOT NULL
        GROUP BY d.parcelle_idu
        ON CONFLICT (idu) DO UPDATE
          SET flag_amiante = EXCLUDED.flag_amiante, updated_at = now()
    """), {"seuil": seuil}).rowcount


def compute_flag_abf(session: Session) -> int:
    """Pure jointure sur la cascade pré-calculée (même sémantique que le filtre
    segments flag_abf : UNKNOWN = parcelle dans un périmètre ABF)."""
    return session.execute(text("""
        INSERT INTO parcel_solar (idu, flag_abf, updated_at)
        SELECT p.idu, bool_or(cr.result = 'UNKNOWN'), now()
        FROM parcels p
        JOIN dryrun_cascade_results cr
          ON cr.parcel_id = p.id AND cr.run_label = :run AND cr.layer_name = 'abf'
        GROUP BY p.idu
        ON CONFLICT (idu) DO UPDATE
          SET flag_abf = EXCLUDED.flag_abf, updated_at = now()
    """), {"run": CASCADE_RUN}).rowcount


def compute_azimut(session: Session) -> int:
    """Grand axe du bâtiment principal (plus grande emprise commune avec la parcelle).

    ST_OrientedEnvelope → rectangle orienté ; azimut du côté LONG, réduit à [0, 180[
    (une toiture n'a pas de sens de parcours). Élongation L/l < seuil → 'basse'.
    """
    elong_min = float(_cfg()["azimut_elongation_min"])
    return session.execute(text("""
        WITH pairs AS (
          SELECT p.idu, sl.geom_2975 AS g,
                 ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975)) AS inter
          FROM parcels p
          JOIN spatial_layers sl
            ON sl.kind = 'batiment' AND ST_Intersects(sl.geom_2975, p.geom_2975)
        ),
        bati AS (
          SELECT idu, g, inter,
                 row_number() OVER (PARTITION BY idu ORDER BY inter DESC) AS rn
          FROM pairs
        ),
        env AS (
          SELECT idu, ST_OrientedEnvelope(g) AS e
          FROM bati WHERE rn = 1 AND inter >= 20
        ),
        pts AS (
          SELECT idu,
                 ST_PointN(ST_ExteriorRing(e), 1) AS a,
                 ST_PointN(ST_ExteriorRing(e), 2) AS b,
                 ST_PointN(ST_ExteriorRing(e), 3) AS c
          FROM env WHERE ST_GeometryType(e) = 'ST_Polygon'
        ),
        az AS (
          SELECT idu,
                 CASE WHEN ST_Distance(a, b) >= ST_Distance(b, c)
                      THEN degrees(ST_Azimuth(a, b)) ELSE degrees(ST_Azimuth(b, c)) END AS azimut,
                 GREATEST(ST_Distance(a, b), ST_Distance(b, c))
                   / NULLIF(LEAST(ST_Distance(a, b), ST_Distance(b, c)), 0) AS elong
          FROM pts
        )
        INSERT INTO parcel_solar (idu, azimut_bati_deg, azimut_confiance, updated_at)
        SELECT idu, round((azimut::numeric % 180.0), 1),
               CASE WHEN elong > :emin THEN 'haute' ELSE 'basse' END, now()
        FROM az WHERE azimut IS NOT NULL
        ON CONFLICT (idu) DO UPDATE
          SET azimut_bati_deg = EXCLUDED.azimut_bati_deg,
              azimut_confiance = EXCLUDED.azimut_confiance, updated_at = now()
    """), {"emin": elong_min}).rowcount


def compute_proba_proprio_occupant(session: Session, *, aujourd_hui: date | None = None) -> int:
    """Taux de propriétaires du carreau Filosofi 200 m au centroïde (INSEE, maille la
    plus fine en base — le mandat visait l'IRIS, le carreau est PLUS fin), repli sur
    le taux communal INSEE. Bonus mutation récente (l'acheteur d'une maison y habite
    le plus souvent), plafonné [proprio_min, proprio_max] : score STATISTIQUE."""
    cfg = _cfg()
    ref = aujourd_hui or date.today()  # heure LOCALE python (leçon QA wave : pas CURRENT_DATE)
    depuis = ref - timedelta(days=int(cfg["proprio_bonus_fenetre_mois"]) * 30)
    return session.execute(text("""
        WITH base AS (
          SELECT p.idu,
                 COALESCE(
                   (SELECT 100.0 * f.men_prop / NULLIF(f.men, 0)
                    FROM filosofi_carreaux_200m f
                    WHERE ST_Contains(f.geom, ST_Transform(p.centroid, 2975))
                      AND f.men > 0
                    LIMIT 1),
                   (SELECT cil.proprietaires_pct FROM commune_insee_logement cil
                    WHERE cil.insee = left(p.idu, 5))
                 ) AS pct,
                 EXISTS (SELECT 1 FROM dvf_mutations_parcelle d
                         WHERE d.id_parcelle = p.idu AND d.type_local = 'Maison'
                           AND d.date_mutation >= :depuis) AS mut_recente
          FROM parcels p
        )
        INSERT INTO parcel_solar (idu, proba_proprio_occupant, updated_at)
        SELECT idu,
               LEAST(:pmax, GREATEST(:pmin,
                 round(pct + CASE WHEN mut_recente THEN :bonus ELSE 0 END)))::int,
               now()
        FROM base WHERE pct IS NOT NULL
        ON CONFLICT (idu) DO UPDATE
          SET proba_proprio_occupant = EXCLUDED.proba_proprio_occupant, updated_at = now()
    """), {"depuis": depuis, "bonus": int(cfg["proprio_bonus_mutation_pts"]),
           "pmin": int(cfg["proprio_min"]), "pmax": int(cfg["proprio_max"])}).rowcount


def run(session: Session, log=print) -> dict[str, int]:
    ensure_schema(session)
    out = {"flag_amiante": compute_flag_amiante(session)}
    log(f"  flag_amiante : {out['flag_amiante']} parcelles (DPE pilote : volumétrie faible attendue)")
    out["flag_abf"] = compute_flag_abf(session)
    log(f"  flag_abf : {out['flag_abf']} parcelles")
    out["azimut"] = compute_azimut(session)
    log(f"  azimut bâti : {out['azimut']} parcelles")
    out["proprio_occupant"] = compute_proba_proprio_occupant(session)
    log(f"  proba propriétaire-occupant : {out['proprio_occupant']} parcelles")
    return out
