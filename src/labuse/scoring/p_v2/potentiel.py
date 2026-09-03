"""SCORING-3 · L4 — le potentiel, prêt pour la Priorité v2 (calculé et stocké,
PAS affiché — l'affichage est PALIERS-1).

Par parcelle du run candidat (colonnes de `parcel_p_score_v2`, run-scopées) :
  - `potentiel_sdp_m2`     : SDP résiduelle lue EN ENTIER (doctrine K3 :
    0 = réponse du moteur, NULL = hors_plu seul réellement inconnaissable) ;
  - `prix_secteur_eur_m2`  : médiane €/m² bâti de la COMMUNE, année Y-1 du run
    (DVF L2-F, `p_model_ext_mut_l2` — la même source que le modèle) ;
  - `valeur_creee_eur`     : SDP résiduelle × prix de secteur ; l'intervalle
    honnête `valeur_creee_min/max_eur` = SDP × [q1, q3] communal ;
  - `indice_opportunite`   : probabilité 12 mois × valeur créée, NORMALISÉ PAR
    COMMUNE (percentile 0-100 intra-commune) — un produit de deux colonnes
    existantes, pas un nouveau modèle ;
  - accès : `acces_pm_siren` (propriétaire PM identifiable via SIREN — les PP
    restent inconnus sans les fichiers fonciers) et `acces_courrier` (adresse
    BAN connue → un courrier est possible).

« Déjà contacté par un compte » (piste CRM, courrier) est PAR COMPTE et n'est
JAMAIS partagé : il vit dans la vue `v_parcelle_contact_compte` (clé compte_id
× parcelle), jamais dans les colonnes communes du run.

Les définitions et sources de chaque terme sont écrites dans
`p_score_v2_runs.params -> 'potentiel'` (traçabilité datée).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

#: définitions écrites au registre du run — chaque terme nomme sa source.
DEFINITIONS = {
    "potentiel_sdp_m2": "SDP résiduelle (parcel_residuel M125, lue en entier : "
                        "0 = réponse du moteur, NULL = hors_plu)",
    "prix_secteur_eur_m2": "médiane €/m² bâti de la commune, année Y-1 du run "
                           "(DVF L2-F, p_model_ext_mut_l2, hors exclusions L2F)",
    "valeur_creee_eur": "SDP résiduelle × prix de secteur (médiane communale)",
    "valeur_creee_min_eur": "SDP résiduelle × 1er quartile communal (borne basse honnête)",
    "valeur_creee_max_eur": "SDP résiduelle × 3e quartile communal (borne haute honnête)",
    "indice_opportunite": "percentile intra-commune (0-100) de p_raw × valeur_creee_eur "
                          "— produit de deux colonnes existantes, aucun nouveau modèle",
    "acces_pm_siren": "propriétaire personne morale identifiable (parcel_v_score.owner_siren)",
    "acces_courrier": "adresse BAN connue (parcel_adresse.ban_voie) — courrier possible",
    "deja_contacte": "PAR COMPTE, vue v_parcelle_contact_compte (piste CRM ou courrier) "
                     "— jamais partagé entre comptes, jamais dans le run commun",
}

COLONNES_SQL = """
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS potentiel_sdp_m2 integer;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS prix_secteur_eur_m2 real;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS valeur_creee_eur double precision;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS valeur_creee_min_eur double precision;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS valeur_creee_max_eur double precision;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS indice_opportunite real;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS acces_pm_siren boolean;
    ALTER TABLE parcel_p_score_v2 ADD COLUMN IF NOT EXISTS acces_courrier boolean;
"""


def ensure_vue_contact(session: Session) -> None:
    """La vue PAR COMPTE « déjà contacté » : piste CRM vivante OU courrier.
    Cloisonnée par construction (compte_id dans la clé) ; les lecteurs DOIVENT
    filtrer sur le compte courant — aucun agrégat inter-comptes n'est produit."""
    session.execute(text("""
        CREATE OR REPLACE VIEW v_parcelle_contact_compte AS
        SELECT pe.compte_id, p.idu AS parcelle_idu,
               'piste_crm'::text AS contact_via, pe.created_at AS contacte_le
        FROM pipeline_entries pe
        JOIN parcels p ON p.id = pe.parcel_id
        WHERE pe.archived_at IS NULL
        UNION
        SELECT cd.compte_id, cd.idu AS parcelle_idu,
               'courrier'::text AS contact_via, cd.ts AS contacte_le
        FROM courrier_demandes cd
        WHERE cd.idu IS NOT NULL AND cd.compte_id IS NOT NULL
    """))


def backfill_run(session: Session, run_id: str) -> dict:
    """Calcule et stocke le potentiel pour UN run (run-scopé, idempotent).
    Ne touche ni p_raw, ni rang, ni tier — colonnes annexes cloisonnées du
    score, comme l'ICD."""
    for stmt in COLONNES_SQL.strip().split(";"):
        if stmt.strip():
            session.execute(text(stmt))

    annee = session.execute(text(
        "SELECT (params ->> 'annee_features')::int FROM p_score_v2_runs "
        "WHERE run_id = :r"), {"r": run_id}).scalar()
    if annee is None:
        raise RuntimeError(f"run inconnu au registre : {run_id!r}")

    # 1 — prix de secteur communal, année Y-1 du run (as-of : jamais l'année courante)
    session.execute(text("""
        CREATE TEMP TABLE _prix_secteur ON COMMIT DROP AS
        SELECT left(m.idu, 5) AS commune,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY m.pm2_bati) AS q1,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY m.pm2_bati) AS med,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY m.pm2_bati) AS q3,
               count(*) AS n_ventes
        FROM p_model_ext_mut_l2 m
        WHERE NOT m.exclue_l2f AND m.pm2_bati IS NOT NULL
          AND extract(year FROM m.date_mutation)::int = :a1
        GROUP BY 1"""), {"a1": annee - 1})

    # 2 — SDP (lecture K3), prix, valeur créée + intervalle, accès
    n = session.execute(text("""
        UPDATE parcel_p_score_v2 s
        SET potentiel_sdp_m2 = r.sdp_residuelle_m2,
            prix_secteur_eur_m2 = px.med,
            valeur_creee_eur     = CASE WHEN r.sdp_residuelle_m2 IS NULL OR px.med IS NULL
                                        THEN NULL ELSE r.sdp_residuelle_m2 * px.med END,
            valeur_creee_min_eur = CASE WHEN r.sdp_residuelle_m2 IS NULL OR px.q1 IS NULL
                                        THEN NULL ELSE r.sdp_residuelle_m2 * px.q1 END,
            valeur_creee_max_eur = CASE WHEN r.sdp_residuelle_m2 IS NULL OR px.q3 IS NULL
                                        THEN NULL ELSE r.sdp_residuelle_m2 * px.q3 END,
            acces_pm_siren = EXISTS (SELECT 1 FROM parcel_v_score v
                                     WHERE v.parcelle_id = s.parcelle_id
                                       AND v.owner_siren IS NOT NULL),
            acces_courrier = EXISTS (SELECT 1 FROM parcel_adresse a
                                     WHERE a.idu = s.parcelle_id
                                       AND a.ban_voie IS NOT NULL)
        FROM parcels p
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        LEFT JOIN _prix_secteur px ON px.commune = left(p.idu, 5)
        WHERE s.run_id = :r AND s.parcelle_id = p.idu"""), {"r": run_id}).rowcount

    # 3 — indice d'opportunité : percentile intra-commune de p_raw × valeur créée
    #     (0-100 ; valeur NULL → indice NULL, honnête : hors_plu / commune sans ventes)
    session.execute(text("""
        UPDATE parcel_p_score_v2 s
        SET indice_opportunite = q.pct
        FROM (SELECT id, round((100 * percent_rank() OVER (
                     PARTITION BY left(parcelle_id, 5)
                     ORDER BY p_raw * valeur_creee_eur))::numeric, 1) AS pct
              FROM parcel_p_score_v2
              WHERE run_id = :r AND valeur_creee_eur IS NOT NULL) q
        WHERE s.id = q.id"""), {"r": run_id})

    ensure_vue_contact(session)

    # 4 — les définitions/sources, datées, au registre du run
    session.execute(text("""
        UPDATE p_score_v2_runs
        SET params = params || jsonb_build_object('potentiel',
            jsonb_build_object('definitions', CAST(:d AS jsonb),
                               'annee_prix_secteur', :a1,
                               'n_lignes', :n))
        WHERE run_id = :r"""), {
        "d": json.dumps(DEFINITIONS, ensure_ascii=False),
        "a1": annee - 1, "n": int(n or 0), "r": run_id})

    stats = session.execute(text("""
        SELECT count(*) FILTER (WHERE valeur_creee_eur IS NOT NULL) AS n_valeur,
               count(*) FILTER (WHERE valeur_creee_eur > 0)          AS n_valeur_pos,
               count(*) FILTER (WHERE acces_pm_siren)                AS n_pm,
               count(*) FILTER (WHERE acces_courrier)                AS n_courrier,
               count(*) AS n
        FROM parcel_p_score_v2 WHERE run_id = :r"""), {"r": run_id}).mappings().first()
    return dict(stats)
