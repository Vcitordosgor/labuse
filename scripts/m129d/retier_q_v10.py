"""M129-D (arbitrage Vic) — re-tiers du run SERVI q_v10_m129 : les bâties AVEC droits résiduels
sortent du déclassement « saturée ». MÊMES fonctions (statuts.py), mêmes entrées que le pipeline
(contrat de colonnes assign_tiers), reconstruites depuis les tables du run. UPDATE en place du
tier seul (p/rang inchangés : le modèle n'a pas bougé)."""
import numpy as np
import pandas as pd
from sqlalchemy import text

from labuse.db import session_scope
from labuse.scoring.p_v2.statuts import TierParams, assign_tiers, calibre_brulante, calibre_n_entree, plancher_c

RUN = "q_v10_m129"

with session_scope() as s:
    df = pd.read_sql(text("""
        SELECT s.parcelle_id AS idu, s.rang, s.copro, s.p_raw AS p, s.contrib_d, s.event_date,
               s.tier AS tier_avant,
               (d.status = 'exclue') AS ecartee_etage0,
               c.label AS declasse_cause,
               a.classe AS au_statut,
               COALESCE(rv.brv, false) AS bati_revele,
               (fb.idu IS NOT NULL) AS bati_sature,
               r.sdp_residuelle_m2, p2.surface_m2, z.zone_fam AS zone_plu,
               COALESCE(pau.dans, false) AS dans_pau
        FROM parcel_p_score_v2 s
        JOIN parcels p2 ON p2.idu = s.parcelle_id
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p2.id AND d.run_label = :r
        LEFT JOIN parcel_constructibilite c ON c.parcel_id = p2.id
        LEFT JOIN parcel_au_statut a ON a.parcel_id = p2.id
        LEFT JOIN (SELECT idu, true AS brv FROM parcel_bati_revele WHERE bande='regle' GROUP BY idu) rv
               ON rv.idu = s.parcelle_id
        LEFT JOIN (SELECT f.idu FROM parcel_filtre_bati f
                   WHERE f.decision='saturee' AND NOT EXISTS (
                     SELECT 1 FROM parcels px JOIN parcel_residuel rx ON rx.parcel_id = px.id
                     WHERE px.idu = f.idu AND rx.cause IS NULL AND rx.sdp_residuelle_m2 > 0)) fb
               ON fb.idu = s.parcelle_id
        LEFT JOIN parcel_residuel r ON r.parcel_id = p2.id AND r.cause IS NULL
        LEFT JOIN parcel_zone_plu z ON z.idu = s.parcelle_id
        LEFT JOIN (SELECT idu, true AS dans FROM parcel_pau GROUP BY idu) pau
               ON pau.idu = s.parcelle_id
        WHERE s.run_id = :r"""), s.connection(), params={"r": RUN})
    now = pd.Timestamp.now()
    ev = pd.to_datetime(df["event_date"], errors="coerce")
    df["event_age_mois"] = (now - ev).dt.days / 30.44
    print(f"{len(df):,} lignes · saturées (nouvelle règle) : {int(df.bati_sature.sum()):,}")
    elig = df[~df.copro & ~df.ecartee_etage0 & df.declasse_cause.isna() & df.au_statut.isna()
              & ~df.bati_revele & ~df.bati_sature & plancher_c(df, TierParams(1, 1))]
    n_e = calibre_n_entree(elig["rang"], cible=1150)
    params = TierParams(n_entree=n_e, n_sortie=int(round(1.4 * n_e)))
    prev = df["tier_avant"]
    tier = assign_tiers(df, params, prev)
    params = calibre_brulante(df[tier.isin(["chaude", "brulante"])], params)
    tier = assign_tiers(df, params, prev)
    ch = (tier != df["tier_avant"])
    print(f"N_entrée={n_e} · tiers changés : {int(ch.sum()):,}")
    print(pd.crosstab(df.loc[ch, "tier_avant"], tier[ch]).to_string())
    payload = [{"i": i, "t": t} for i, t in zip(df.loc[ch, "idu"], tier[ch])]
    if payload:
        s.execute(text(f"UPDATE parcel_p_score_v2 SET tier = :t WHERE run_id = '{RUN}' AND parcelle_id = :i"),
                  payload)
    print("UPDATE fait.")
