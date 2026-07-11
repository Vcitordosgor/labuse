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


def precision_validee(session: Session, type_: str) -> float | None:
    """Précision mesurée sur les verdicts Vic pour un type — None si < 30 verdicts."""
    ok, tot = session.execute(text(
        "SELECT count(*) FILTER (WHERE validation = 'ok'), count(validation)"
        " FROM ortho_detections WHERE type = :t AND validation IS NOT NULL"),
        {"t": type_}).one()
    return (ok / tot) if tot >= 30 else None


def materialiser_pv(session: Session, log=print) -> dict[str, Any]:
    """PV : matérialisé UNIQUEMENT si la précision validée ≥ 75 % (règle mandat) —
    sinon les candidats restent en base (confiance) sans remonter."""
    session.execute(text(DDL))
    cfg = load_yaml_config("detection_ortho")["materialisation"]
    prec = precision_validee(session, "pv")
    if prec is None or prec < float(cfg["precision_min_pv"]):
        return {"pv_materialise": False, "precision_pv": prec,
                "note": "candidats en base, non matérialisés (validation < 75 % ou "
                        "insuffisante — /ortho/validation?type=pv, échantillon 150)"}
    seuil = float(cfg["seuil_confiance_pv"])
    n = session.execute(text("""
        WITH retenues AS (
          SELECT d.idu, d.surface_m2, d.confiance, (d.criteres ->> 'ces') = 'true' AS ces
          FROM ortho_detections d
          WHERE d.type = 'pv' AND d.idu IS NOT NULL
            AND (d.validation = 'ok' OR (d.validation IS NULL AND d.confiance >= :seuil))
        )
        INSERT INTO parcel_equipements (idu, pv_detecte, pv_surface_m2, pv_confiance,
                                        pv_probable_ces, updated_at)
        SELECT idu, bool_or(NOT ces), sum(surface_m2) FILTER (WHERE NOT ces),
               max(confiance) FILTER (WHERE NOT ces), bool_or(ces), now()
        FROM retenues GROUP BY idu
        ON CONFLICT (idu) DO UPDATE SET
          pv_detecte = EXCLUDED.pv_detecte, pv_surface_m2 = EXCLUDED.pv_surface_m2,
          pv_confiance = EXCLUDED.pv_confiance,
          pv_probable_ces = EXCLUDED.pv_probable_ces, updated_at = now()
    """), {"seuil": seuil}).rowcount
    return {"pv_materialise": True, "precision_pv": round(prec, 3), "parcelles_pv": n}


def branchements_solaire(session: Session, log=print) -> dict[str, Any]:
    """Lot 5.2 — branchements inter-modules (uniquement si le PV est matérialisé) :
    - parcel_solar.pv_existant = 'detecte' (supplante le proxy communal) ;
    - repowering : PV détecté × commune à installations 2006-2013 (registre) —
      LA SEULE voie de localisation des candidats (registre national anonymisé
      sans géoloc, cf. mandat Habitat Solaire) + signal repowering_candidate.
    """
    n_det = session.execute(text("""
        UPDATE parcel_solar ps SET pv_existant = 'detecte', updated_at = now()
        FROM parcel_equipements pe
        WHERE pe.idu = ps.idu AND pe.pv_detecte
          AND ps.pv_existant IS DISTINCT FROM 'detecte'
    """)).rowcount
    cfg = load_yaml_config("habitat_solaire")["pv_registry"]
    n_rep = session.execute(text("""
        WITH communes_fenetre AS (
          SELECT DISTINCT insee FROM pv_registry
          WHERE individualise AND date_mise_service
                BETWEEN CAST(:d1 AS date) AND CAST(:d2 AS date)
        )
        UPDATE parcel_solar ps SET repowering = true, updated_at = now()
        FROM parcel_equipements pe
        WHERE pe.idu = ps.idu AND pe.pv_detecte
          AND left(ps.idu, 5) IN (SELECT insee FROM communes_fenetre)
          AND ps.repowering IS DISTINCT FROM true
    """), {"d1": str(cfg["repowering_debut"]), "d2": str(cfg["repowering_fin"])}).rowcount
    session.execute(text(
        "DELETE FROM parcel_signals WHERE signal_type = 'repowering_candidate'"))
    n_sig = session.execute(text("""
        INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
        SELECT p.id, 'repowering_candidate',
               jsonb_build_object('source', 'PV détecté (ortho 2025) × commune à '
                 || 'installations 2006-2013 (registre national)',
                 'pv_surface_m2', round(pe.pv_surface_m2::numeric)),
               now()
        FROM parcel_solar ps
        JOIN parcels p ON p.idu = ps.idu
        JOIN parcel_equipements pe ON pe.idu = ps.idu
        WHERE ps.repowering AND pe.pv_detecte
    """)).rowcount
    return {"pv_existant_detecte": n_det, "repowering": n_rep, "signaux_repowering": n_sig}


def run(session: Session, log=print) -> dict[str, Any]:
    out = materialiser_piscines(session)
    log(f"  parcel_equipements : {out['parcelles_piscine']} parcelles piscine")
    out["signaux"] = signal_piscines(session)
    log(f"  signaux piscine_detectee : {out['signaux']}")
    pv = materialiser_pv(session, log=log)
    log(f"  PV : {pv}")
    out.update(pv)
    if pv.get("pv_materialise"):
        br = branchements_solaire(session, log=log)
        log(f"  branchements solaire : {br}")
        out.update(br)
    return out
