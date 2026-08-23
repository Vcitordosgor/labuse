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
  -- ⚰️ PV MORT DEUX FOIS — ne PAS ressusciter ces colonnes sans un jeu ÉTIQUETÉ :
  --   1) proxy communal 'commune_forte_densite' (jamais une détection) ;
  --   2) détection colorimétrique V0 (ortho_pv.py) — précision 0 % mesurée (SOLAIRE M2, essai 51
  --      parcelles : 28 faux positifs / 0 vrai — piscines, toits bleutés, serres, terrains de sport).
  -- Renoncement acté : pv_detecte n'est plus matérialisé ni servi (cf. qa/solaire/PV_PHASE1.md).
  -- Colonnes conservées inertes (aucune migration destructive) ; le seul feu vert = un modèle de
  -- segmentation entraîné sur ~500 toits PV annotés (mandat DONNÉE), pas une heuristique.
  pv_detecte          boolean,          -- INERTE (renoncement SOLAIRE M2)
  pv_surface_m2       double precision,  -- INERTE
  pv_confiance        double precision,  -- INERTE
  pv_probable_ces     boolean,          -- INERTE (ex chauffe-eau solaire probable, Lot 4)
  updated_at          timestamptz DEFAULT now()
);
"""


def _profil() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["materialisation"]["piscine_profil_strict"]


def materialiser_piscines(session: Session) -> dict[str, Any]:
    """Depuis la cascade (11/07 soir) : le JUGE FLAIR × probe (90,7 % mesuré) remplace
    le profil colorimétrique — vérité humaine (validation) toujours prioritaire."""
    session.execute(text(DDL))
    j = load_yaml_config("detection_ortho")["materialisation"]["juge"]
    n = session.execute(text("""
        WITH retenues AS (
          SELECT d.idu, d.surface_m2, d.confiance
          FROM ortho_detections d
          WHERE d.type = 'piscine' AND d.idu IS NOT NULL
            AND (
              d.validation = 'ok'                       -- vérité humaine, prime
              OR (d.validation IS NULL                  -- juge de la cascade
                  AND d.juge_flair >= :fmin AND d.probe_score >= :pmin)
            )
        )
        INSERT INTO parcel_equipements (idu, piscine, piscine_surface_m2,
                                        piscine_confiance, updated_at)
        SELECT idu, true, max(surface_m2), max(confiance), now()
        FROM retenues GROUP BY idu
        ON CONFLICT (idu) DO UPDATE SET
          piscine = true, piscine_surface_m2 = EXCLUDED.piscine_surface_m2,
          piscine_confiance = EXCLUDED.piscine_confiance, updated_at = now()
    """), {"fmin": j["flair_min"], "pmin": j["probe_min"]}).rowcount
    # les parcelles que le juge ne retient plus (et sans verdict ok) repassent à false
    session.execute(text("""
        UPDATE parcel_equipements pe SET piscine = false, piscine_surface_m2 = NULL,
               piscine_confiance = NULL, updated_at = now()
        WHERE pe.piscine AND NOT EXISTS (
          SELECT 1 FROM ortho_detections d
          WHERE d.idu = pe.idu AND d.type = 'piscine'
            AND (d.validation = 'ok'
                 OR (d.validation IS NULL
                     AND d.juge_flair >= :fmin AND d.probe_score >= :pmin)))
    """), {"fmin": j["flair_min"], "pmin": j["probe_min"]})
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
    """SOLAIRE M2 — RENONCEMENT : la matérialisation PV est DÉSACTIVÉE (no-op).

    La détection PV V0 (colorimétrie, ortho_pv.py) a une précision mesurée de 0 % (essai empirique,
    qa/solaire/PV_PHASE1.md) : on ne sert pas un filtre qui ment. Les 23 529 candidats V0 ont été
    purgés. Ce point ne se ré-arme que sur un MODÈLE ENTRAÎNÉ (segmentation + jeu étiqueté ~500 toits),
    pas sur l'heuristique — d'où le no-op ici (ne réécrit jamais parcel_equipements.pv_*)."""
    return {"pv_materialise": False, "precision_pv": None,
            "note": "détection PV V0 abandonnée (précision 0 % ; renoncement SOLAIRE M2)"}


def branchements_solaire(session: Session, log=print) -> dict[str, Any]:
    """SOLAIRE M1 — RETIRÉ (no-op). Écrivait parcel_solar.pv_existant/repowering, colonnes-proxys
    ABANDONNÉES (schéma 14 colonnes, cf. ingestion/solaire.py). Conservé en stub pour ne casser aucun
    import ; ne fait plus rien. La détection PV vit dans parcel_equipements.pv_detecte, sans pont vers
    parcel_solar (pv_detecte = 0 sur le parc de toute façon)."""
    return {"pv_existant_detecte": 0, "repowering": 0, "signaux_repowering": 0}


def run(session: Session, log=print) -> dict[str, Any]:
    out = materialiser_piscines(session)
    log(f"  parcel_equipements : {out['parcelles_piscine']} parcelles piscine")
    out["signaux"] = signal_piscines(session)
    log(f"  signaux piscine_detectee : {out['signaux']}")
    pv = materialiser_pv(session, log=log)
    log(f"  PV : {pv}")
    out.update(pv)
    # SOLAIRE M1 — `branchements_solaire` (écriture parcel_solar.pv_existant/repowering) RETIRÉ :
    # ces colonnes-proxys sont abandonnées (schéma 14 colonnes, cf. ingestion/solaire.py). La détection
    # PV reste dans parcel_equipements (pv_detecte) ; plus aucun pont vers parcel_solar.
    return out
