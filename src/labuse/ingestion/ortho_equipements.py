"""Wave Détection Ortho, Lot 5 — matérialisation `parcel_equipements` + branchements.

Piscines (V0, 11/07/2026) : AUCUN seuil de confiance n'atteint les 90 % du mandat sur
les 966 verdicts Vic (max mesuré : 79,3 % sur le profil « strict » multi-critères —
teinte 88-104, saturation ≥ 130, V ≥ 160, surface 15-80 m²). Décision : matérialiser
le PROFIL STRICT (précision mesurée affichée, fiabilité statistique assumée à l'UI),
GO Lot 8 ML documenté au rapport — les verdicts sont le dataset d'amorce.

Sont matérialisées : détections du profil strict NON invalidées par Vic
(validation ≠ 'faux_positif') ∪ détections validées 'ok' hors profil (vérité humaine
> heuristique). PV (Lot 4) : seuil confiance config, cible ≥ 75 % — en dessous, les
candidats RESTENT en base sans matérialisation (règle du mandat).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config

DDL = """
CREATE TABLE IF NOT EXISTS parcel_equipements (
  idu                 varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  piscine             boolean,
  piscine_surface_m2  double precision,
  piscine_confiance   double precision,
  pv_detecte          boolean,
  pv_surface_m2       double precision,
  pv_confiance        double precision,
  pv_probable_ces     boolean,          -- chauffe-eau solaire probable (Lot 4, 4-8 m²)
  updated_at          timestamptz DEFAULT now()
);
"""


def _profil() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["materialisation"]["piscine_profil_strict"]


def materialiser_piscines(session: Session) -> dict[str, Any]:
    session.execute(text(DDL))
    p = _profil()
    n = session.execute(text("""
        WITH retenues AS (
          SELECT d.idu, d.surface_m2, d.confiance
          FROM ortho_detections d
          WHERE d.type = 'piscine' AND d.idu IS NOT NULL
            AND (
              d.validation = 'ok'                       -- vérité humaine, prime
              OR (d.validation IS NULL                  -- profil strict non invalidé
                  AND (d.criteres->'hsv_moyen'->>0)::float BETWEEN :h0 AND :h1
                  AND (d.criteres->'hsv_moyen'->>1)::float >= :smin
                  AND (d.criteres->'hsv_moyen'->>2)::float >= :vmin
                  AND d.surface_m2 BETWEEN :su0 AND :su1)
            )
        )
        INSERT INTO parcel_equipements (idu, piscine, piscine_surface_m2,
                                        piscine_confiance, updated_at)
        SELECT idu, true, max(surface_m2), max(confiance), now()
        FROM retenues GROUP BY idu
        ON CONFLICT (idu) DO UPDATE SET
          piscine = true, piscine_surface_m2 = EXCLUDED.piscine_surface_m2,
          piscine_confiance = EXCLUDED.piscine_confiance, updated_at = now()
    """), {"h0": p["hsv_h"][0], "h1": p["hsv_h"][1], "smin": p["hsv_s_min"],
           "vmin": p["hsv_v_min"], "su0": p["surface_m2"][0], "su1": p["surface_m2"][1]}).rowcount
    # les faux positifs de Vic RETIRENT la piscine si plus aucune détection retenue
    session.execute(text("""
        UPDATE parcel_equipements pe SET piscine = false, piscine_surface_m2 = NULL,
               piscine_confiance = NULL, updated_at = now()
        WHERE pe.piscine AND NOT EXISTS (
          SELECT 1 FROM ortho_detections d
          WHERE d.idu = pe.idu AND d.type = 'piscine'
            AND (d.validation = 'ok' OR d.validation IS NULL))
    """))
    return {"parcelles_piscine": n}


def signal_piscines(session: Session) -> int:
    session.execute(text(
        "DELETE FROM parcel_signals WHERE signal_type = 'piscine_detectee'"))
    return session.execute(text("""
        INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
        SELECT p.id, 'piscine_detectee',
               jsonb_build_object('surface_m2', round(pe.piscine_surface_m2::numeric),
                                  'confiance', pe.piscine_confiance,
                                  'source', 'ortho IGN 2025 — fiabilité statistique'),
               now()
        FROM parcel_equipements pe JOIN parcels p ON p.idu = pe.idu
        WHERE pe.piscine
    """)).rowcount


def run(session: Session, log=print) -> dict[str, Any]:
    out = materialiser_piscines(session)
    log(f"  parcel_equipements : {out['parcelles_piscine']} parcelles piscine")
    out["signaux"] = signal_piscines(session)
    log(f"  signaux piscine_detectee : {out['signaux']}")
    return out
