"""M127 Phase 1 — le dataset v2 : p_model_dataset_v2 + manifeste.

PRÉMISSE CORRIGÉE (mesurée avant de bâtir) : le clamp 2021 est DÉJÀ levé dans le dataset
d'entraînement — `ext_sql.py` construit depuis M3.5/M3.6 sur l'UNION prod+histo
(EXT_DVF_START = 2014-01-01, tenure sans clamp) ; l'artefact servi 6,73 a été ENTRAÎNÉ avec
la profondeur. La marche « B = profondeur » de l'échelle d'ablation est donc un no-op — dit
en rouge au rapport. L'échelle réelle : A (nettoyage) → C (zéros M125) → D (candidates M126).

Le v2 est un OVERLAY du dataset existant (la machinerie as-of — fenêtres, tenure, labels —
ne se reconstruit pas, elle est déjà correcte et profonde) :
  · les 7 features mortes/retirées SORTENT physiquement (qpv, friche, window_coverage,
    pv_candidat, permis_24m_norm, filo_dens_pop, dormance_droits — window_coverage reste
    en MÉTA pour le shrinkage des rotations, jamais une feature) ;
  · sdp_residuelle_m2 / sous_densite / pct_potentiel REJOINTS FRAIS depuis parcel_residuel
    (zéros M125 + cause ; hors_plu → NULL dit) — invariant par année (statique) ;
  · les colonnes M126 jointes sur (idu, annee) — division_recente exclue (morte-née).

Usage : python scripts/m127/build_dataset_v2.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope

REPORTS = Path("reports/m127")

SQL = """
DROP TABLE IF EXISTS p_model_dataset_v2;
CREATE TABLE p_model_dataset_v2 AS
SELECT
  -- méta (window_coverage reste : shrinkage des rotations — méta, plus une feature)
  d.idu, d.annee, d.label, d.label_l2, d.commune, d.secteur, d.owner_type,
  d.window_coverage, d.n_mut_nu_36m, d.n_mut_bati_36m, d.stock_secteur,
  -- bloc Z conservé (profondeur 2014 DÉJÀ dedans)
  d.rot_nu_brute, d.rot_bati_brute, d.med_pm2_terrain_36m, d.med_pm2_bati_36m,
  d.tendance_pm2_bati, d.dens_bati_secteur, d.pct_bati_secteur,
  d.filo_snv_pp, d.filo_pct_pauv, d.filo_pct_prop,
  d.pente_moy_deg, d.dist_ecole_m, d.dist_sante_m, d.dist_commerce_m, d.dist_tcsp_m,
  d.zone_plu,
  -- bloc D conservé
  d.nu, d.nu_constructible, d.surface_m2, d.emprise_bati_m2,
  d.tenure_bin, d.permis_bin, d.canopee_pct, d.ndvi_moyen, d.piscine,
  -- C · zéros M125 (rejoints FRAIS — la vérité de parcel_residuel, causes comprises)
  r.sdp_residuelle_m2  AS sdp_residuelle_m2_v2,
  r.sous_densite       AS sous_densite_v2,
  r.pct_potentiel      AS pct_potentiel_v2,
  r.cause              AS residuel_cause,
  -- ancien état (58,7 % renseigné) gardé pour l'échelle A (comparaison propre)
  d.sdp_residuelle_m2  AS sdp_residuelle_m2_v1,
  d.sous_densite       AS sous_densite_v1,
  -- D · les 7 candidates M126 (division_recente exclue — morte-née, dalle)
  c.proc_collective, c.proc_coll_depuis_mois,
  c.succession_indivision,
  c.age_dirigeant_bin,
  c.pm_nue_dormante,
  c.contagion_voisinage, c.n_voisins,
  c.vente_tab_proximite,
  c.permis_etat, c.pc_accorde_jamais_commence
FROM p_model_ext_dataset d
LEFT JOIN parcels p            ON p.idu = d.idu
LEFT JOIN parcel_residuel r    ON r.parcel_id = p.id
LEFT JOIN p_model_candidates c ON c.idu = d.idu AND c.annee = d.annee;
CREATE UNIQUE INDEX ON p_model_dataset_v2 (idu, annee);
CREATE INDEX ON p_model_dataset_v2 (annee);
"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with session_scope() as s:
        s.execute(text(SQL))
        s.flush()
    with session_scope() as s:
        eff = s.execute(text(
            "SELECT annee, count(*) n, sum(label) pos, sum(label_l2) pos_l2 "
            "FROM p_model_dataset_v2 GROUP BY 1 ORDER BY 1")).all()
        sdp = s.execute(text(
            "SELECT count(sdp_residuelle_m2_v2)::float / count(*) FROM p_model_dataset_v2")).scalar()
        cand = s.execute(text(
            "SELECT count(contagion_voisinage)::float / count(*) FROM p_model_dataset_v2")).scalar()
    manifest = {
        "table": "p_model_dataset_v2",
        "grille": "p_model_ext_dataset (2017-2026, labels L2-F/L2, as-of M3.6)",
        "profondeur_dvf": "2014-2025 (EXT_DVF_START=2014 — clamp DÉJÀ levé M3.5/M3.6 ; "
                          "vérifié : tenure 2026 connue 17,1 % = mesure M124)",
        "retraits_physiques": ["qpv", "friche", "window_coverage(feature)", "pv_candidat",
                               "permis_24m_norm", "filo_dens_pop", "dormance_droits"],
        "zeros_m125": {"couverture_sdp_v2": round(float(sdp), 4),
                       "source": "parcel_residuel (cause portée ; hors_plu → NULL dit)"},
        "candidates_m126": {"couverture_contagion": round(float(cand), 4),
                            "exclue": "division_recente (morte-née — filiation absente)"},
        "effectifs": [{"annee": r.annee, "n": r.n,
                       "positifs_l2f": int(r.pos) if r.pos is not None else None,
                       "positifs_l2": int(r.pos_l2) if r.pos_l2 is not None else None}
                      for r in eff],
        "duree_s": round(time.time() - t0, 1),
    }
    (REPORTS / "manifest-dataset-v2.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
