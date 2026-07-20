"""PHASE A cycle 2, volet 2 (badge) — « PC caducs ».

Table ADDITIVE `pc_caducs`, dérivée en LECTURE de Sitadel/m10. Ne touche JAMAIS les tables servies
(`parcel_p_score_v2`, `dryrun_*`, runs `q_v7_defisc`/`q_v6_m8`). Signal parcellaire et horodaté :
la parcelle et ses dates, JAMAIS le demandeur (personne physique possible) ni un jugement du propriétaire.

Doctrine (cf. A1_PC_CADUCS_CADRAGE.md) : un PC OCTROYÉ jamais réalisé porte une constructibilité prouvée
et une intention abandonnée → propension de revente ×1,6 vs PC réalisé comparable (backtest, seed 974).
Signal RÉTROSPECTIF (l'arène le juge de plein droit).

Définition parcelle (état Sitadel — la DOC/ouverture de chantier n'existe pas dans les données ; la
contre-vérif bâti est inopérante, cf. cadrage §3.2) :
  - réalisé = ≥1 PC achevé (etat=6 OU DAACT présent) ;
  - caduc   = octroyé (etat∈{4,6}) MAIS aucun réalisé → accordé jamais achevé ;
  - Y+4 dépassé (marge d'un an au-delà des 3 ans légaux, prorogations invisibles) → Y ≤ ref_year-4.
Autorisation = Sourcé (Sitadel) ; caducité = Estimé (inférée).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_REF_YEAR = 2026        # Y+4 dépassé → caduc probable pour Y ≤ ref_year-4

DDL = """
CREATE TABLE IF NOT EXISTS pc_caducs (
  idu                 varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  pc_annee            int  NOT NULL,       -- Y : plus ancienne autorisation OCTROYÉE (Sourcé, Sitadel)
  caduc_depuis        int  NOT NULL,       -- Y+3 : seuil légal de caducité (Estimé)
  n_pc_octroyes       int  NOT NULL,       -- nb de PC octroyés sur la parcelle
  statut_autorisation text NOT NULL DEFAULT 'Sourcé',
  statut_caducite     text NOT NULL DEFAULT 'Estimé',
  libelle_court       text NOT NULL,       -- « PC autorisé AAAA · jamais commencé · caduc probable »
  detail              text NOT NULL,       -- survol : mécanisme + ×1,6 sourcé + faits datés, non accusatoire
  updated_at          timestamptz DEFAULT now()
);
"""

# Caduc = octroyé jamais réalisé, Y+4 dépassé. Une parcelle = plusieurs PC → agrégation.
_SELECT_RAW = """
WITH pc AS (
  SELECT pmp.idu, EXTRACT(YEAR FROM pmp.date_autorisation)::int AS y,
         (sp.raw->>'etat') AS etat, (md.date_achevement IS NOT NULL) AS daact
  FROM p_model_permits pmp
  JOIN sitadel_permits sp ON sp.permit_id = pmp.permit_id
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND pmp.date_autorisation IS NOT NULL),
parc AS (
  SELECT idu,
         min(y) FILTER (WHERE etat IN ('4','6')) AS y_octroye,
         bool_or(daact OR etat = '6') AS realized,
         bool_or(etat IN ('4','6'))   AS granted,
         count(*) FILTER (WHERE etat IN ('4','6')) AS n_octroyes
  FROM pc GROUP BY idu)
SELECT parc.idu, parc.y_octroye, parc.n_octroyes
FROM parc
JOIN parcels p ON p.idu = parc.idu          -- univers servi uniquement (FK + périmètre)
WHERE parc.granted AND NOT parc.realized AND parc.y_octroye <= :ycut;
"""

_INSERT = """
INSERT INTO pc_caducs
  (idu, pc_annee, caduc_depuis, n_pc_octroyes, statut_autorisation, statut_caducite,
   libelle_court, detail, updated_at)
VALUES
  (:idu, :y, :caduc_depuis, :n, 'Sourcé', 'Estimé', :court, :detail, now())
ON CONFLICT (idu) DO UPDATE SET
  pc_annee = EXCLUDED.pc_annee, caduc_depuis = EXCLUDED.caduc_depuis,
  n_pc_octroyes = EXCLUDED.n_pc_octroyes, libelle_court = EXCLUDED.libelle_court,
  detail = EXCLUDED.detail, updated_at = now();
"""


def _row(idu: str, y: int, n: int) -> dict:
    caduc_depuis = y + 3
    court = f"PC autorisé {y} · jamais commencé · caduc probable"
    detail = (
        f"Permis de construire autorisé en {y} (Sitadel, Sourcé), sans achèvement déclaré ni réalisation — "
        f"caducité probable depuis {caduc_depuis} (Estimé). Ce profil — constructibilité déjà prouvée par "
        f"l'instruction, projet non mené — revend ×1,6 plus qu'un PC réalisé comparable (backtest apparié, "
        f"seed 974). Faits datés uniquement : aucun jugement du propriétaire, aucune date de vente, aucune personne."
    )
    return {"idu": idu, "y": y, "caduc_depuis": caduc_depuis, "n": n, "court": court, "detail": detail}


def build_pc_caducs(session: Session, *, ref_year: int = DEFAULT_REF_YEAR,
                    commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `pc_caducs` (rebuild complet idempotent). Lecture seule des sources.
    `commit=False` pour les tests transactionnels. Renvoie {'total': n}."""
    session.execute(text("DROP TABLE IF EXISTS pc_caducs"))
    session.execute(text(DDL))
    raw = session.execute(text(_SELECT_RAW), {"ycut": ref_year - 4}).mappings().all()
    rows = [_row(r["idu"], int(r["y_octroye"]), int(r["n_octroyes"])) for r in raw]
    for r in rows:
        session.execute(text(_INSERT), r)
    if commit:
        session.commit()
    log(f"pc_caducs : {len(rows)} parcelles caduc probable (PC octroyé jamais achevé, Y ≤ {ref_year - 4})")
    return {"total": len(rows)}
