"""Combinaison V3 lexicographique + sortie unique (SCORING-6 lot E).

Assemble par parcelle : le Score LABUSE (lot B) + le Signal de mutation (lot D) + la
reclassification cascade v2 (lot C, motifs conservés pour les filtres), et les écrit dans UNE
table versionnée par run_label — `score_labuse` (clé run_label, parcel_id ; même idiome que
`dryrun_cascade_results` / `parcel_residuel_runs`).

**Combinaison V3 (décision Vic, SCORING-5-RETOUR)** : le classement est LEXICOGRAPHIQUE — d'abord
la BANDE de qualité foncière (A > B > C > D > NC), puis le Signal À L'INTÉRIEUR de la bande, puis
la SDP résiduelle et l'IDU pour le déterminisme. Le Signal ne franchit JAMAIS une frontière de
bande (les deux cas gravés du mandat sont satisfaits par construction).

AUCUN quota, AUCUN rang stocké, AUCUN percentile (contrat §11) : l'ordre est produit par
`ordonner()` / un `ORDER BY`, jamais matérialisé en colonne de rang.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from .cascade_v2 import reclasser_batch
from .score_labuse import charger_bareme, score_batch
from .signal_mutation import signal_niveau, signal_version

# Ordre des bandes pour le classement lexicographique (le Signal départage à l'intérieur).
BANDE_RANG = {"A": 0, "B": 1, "C": 2, "D": 3, "NC": 4}


@dataclass
class LigneScoreLabuse:
    run_label: str
    parcel_id: int
    idu: str
    commune: str
    score: int | None
    bande: str
    non_calculable: bool
    cause: str | None
    couverture_pct: int
    couverture_manquantes: list
    confiance_niveau: str
    confiance_notes: list
    contributions: list
    score_version: str
    signal_p: float | None
    signal_niveau: str | None
    signal_version: str | None
    cascade_exclue: bool
    cascade_motifs: list
    sdp_residuelle_m2: int | None


# ── schéma (idempotent) ──────────────────────────────────────────────────────
def ensure_schema(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS score_labuse_runs (
          run_label text PRIMARY KEY,
          score_version text, signal_version text,
          cascade_label text, signal_run_id text,
          communes text, n_parcelles integer,
          note text, computed_at timestamptz NOT NULL DEFAULT now())"""))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS score_labuse (
          run_label text NOT NULL,
          parcel_id integer NOT NULL REFERENCES parcels(id) ON DELETE CASCADE,
          idu text, commune text,
          score integer, bande text, non_calculable boolean, cause text,
          couverture_pct integer, couverture_manquantes jsonb,
          confiance_niveau text, confiance_notes jsonb,
          contributions jsonb, score_version text,
          signal_p double precision, signal_niveau text, signal_version text,
          cascade_exclue boolean, cascade_motifs jsonb,
          sdp_residuelle_m2 integer,
          computed_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (run_label, parcel_id))"""))
    conn.execute(text("CREATE INDEX IF NOT EXISTS score_labuse_run_bande "
                      "ON score_labuse (run_label, bande)"))


# ── lecture du Signal (p_raw d'un run p_score_v2, joint par IDU) ──────────────
_SIGNAL_SQL = text("""
SELECT p.id AS parcel_id, s.p_raw
FROM parcels p JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu
WHERE s.run_id = :run AND p.id = ANY(:ids)
""")


def lire_signal(session: Session, parcel_ids: list[int], signal_run_id: str) -> dict[int, float]:
    return {r.parcel_id: float(r.p_raw)
            for r in session.execute(_SIGNAL_SQL, {"run": signal_run_id, "ids": list(parcel_ids)})}


def combiner(session: Session, parcel_ids: list[int], run_label: str, *,
             cascade_label: str, signal_run_id: str | None = None,
             signal_recette: str = "q_v15") -> list[LigneScoreLabuse]:
    """Assemble Score × Signal × cascade v2 pour un sous-ensemble. Le Signal (`signal_run_id`)
    est optionnel : sans lui, `signal_p`/`signal_niveau` sont None (combinaison Score seul)."""
    bareme, version = charger_bareme()
    scores = {s.parcel_id: s for s in score_batch(
        session, parcel_ids, run_label, cascade_label=cascade_label,
        bareme=bareme, version=version)}
    signal = lire_signal(session, parcel_ids, signal_run_id) if signal_run_id else {}
    recl = reclasser_batch(session, parcel_ids, cascade_label)
    sver = signal_version(signal_recette) if signal_run_id else None

    lignes: list[LigneScoreLabuse] = []
    for pid in parcel_ids:
        sc = scores.get(pid)
        if sc is None:
            continue
        p = signal.get(pid)
        r = recl.get(pid)
        lignes.append(LigneScoreLabuse(
            run_label=run_label, parcel_id=pid, idu=sc.idu, commune=sc.commune,
            score=sc.score, bande=sc.bande, non_calculable=sc.non_calculable, cause=sc.cause,
            couverture_pct=sc.couverture.get("pct"),
            couverture_manquantes=sc.couverture.get("manquantes", []),
            confiance_niveau=sc.confiance.get("niveau"),
            confiance_notes=sc.confiance.get("notes", []),
            contributions=sc.contributions, score_version=sc.score_version,
            signal_p=p, signal_niveau=signal_niveau(p) if p is not None else None,
            signal_version=sver,
            cascade_exclue=(r.exclue if r else False),
            cascade_motifs=(r.motifs() if r else []),
            sdp_residuelle_m2=sc.details.get("sdp_residuelle_m2")))
    return lignes


def _cle_classement(l: LigneScoreLabuse) -> tuple:
    """Clé de tri V3 lexicographique : bande, puis Signal DANS la bande, puis SDP, puis IDU.
    (Le Signal ne franchit jamais une frontière de bande — il n'agit qu'à bande égale.)"""
    return (BANDE_RANG.get(l.bande, 9),
            -(l.signal_p if l.signal_p is not None else -1.0),
            -(l.sdp_residuelle_m2 or 0),
            l.idu or "")


def ordonner(lignes: list[LigneScoreLabuse]) -> list[LigneScoreLabuse]:
    """Classement V3 déterministe. Aucun rang matérialisé : c'est un ordre, pas un percentile."""
    return sorted(lignes, key=_cle_classement)


# ── persistance (upsert idempotent par run_label, parcel_id) ─────────────────
_UPSERT = text("""
INSERT INTO score_labuse
  (run_label, parcel_id, idu, commune, score, bande, non_calculable, cause,
   couverture_pct, couverture_manquantes, confiance_niveau, confiance_notes,
   contributions, score_version, signal_p, signal_niveau, signal_version,
   cascade_exclue, cascade_motifs, sdp_residuelle_m2, computed_at)
VALUES
  (:run_label, :parcel_id, :idu, :commune, :score, :bande, :non_calculable, :cause,
   :couverture_pct, :couverture_manquantes, :confiance_niveau, :confiance_notes,
   :contributions, :score_version, :signal_p, :signal_niveau, :signal_version,
   :cascade_exclue, :cascade_motifs, :sdp_residuelle_m2, now())
ON CONFLICT (run_label, parcel_id) DO UPDATE SET
  idu=EXCLUDED.idu, commune=EXCLUDED.commune, score=EXCLUDED.score, bande=EXCLUDED.bande,
  non_calculable=EXCLUDED.non_calculable, cause=EXCLUDED.cause,
  couverture_pct=EXCLUDED.couverture_pct, couverture_manquantes=EXCLUDED.couverture_manquantes,
  confiance_niveau=EXCLUDED.confiance_niveau, confiance_notes=EXCLUDED.confiance_notes,
  contributions=EXCLUDED.contributions, score_version=EXCLUDED.score_version,
  signal_p=EXCLUDED.signal_p, signal_niveau=EXCLUDED.signal_niveau,
  signal_version=EXCLUDED.signal_version, cascade_exclue=EXCLUDED.cascade_exclue,
  cascade_motifs=EXCLUDED.cascade_motifs, sdp_residuelle_m2=EXCLUDED.sdp_residuelle_m2,
  computed_at=now()
""")


def persister(session: Session, run_label: str, lignes: list[LigneScoreLabuse], *,
              cascade_label: str, signal_run_id: str | None, communes: str | None) -> int:
    """Écrit les lignes dans la table versionnée `score_labuse` + la métadonnée de run.
    Table NEUVE (jamais lue par le servi) — aucune écriture dans une table de service."""
    if not lignes:
        return 0
    sv = lignes[0].score_version
    sigv = next((l.signal_version for l in lignes if l.signal_version), None)
    session.execute(text("""
        INSERT INTO score_labuse_runs
          (run_label, score_version, signal_version, cascade_label, signal_run_id,
           communes, n_parcelles)
        VALUES (:r, :sv, :sigv, :cl, :sr, :com, :n)
        ON CONFLICT (run_label) DO UPDATE SET
          score_version=EXCLUDED.score_version, signal_version=EXCLUDED.signal_version,
          cascade_label=EXCLUDED.cascade_label, signal_run_id=EXCLUDED.signal_run_id,
          communes=EXCLUDED.communes, n_parcelles=EXCLUDED.n_parcelles, computed_at=now()"""),
        {"r": run_label, "sv": sv, "sigv": sigv, "cl": cascade_label, "sr": signal_run_id,
         "com": communes, "n": len(lignes)})
    for l in lignes:
        session.execute(_UPSERT, {
            "run_label": l.run_label, "parcel_id": l.parcel_id, "idu": l.idu, "commune": l.commune,
            "score": l.score, "bande": l.bande, "non_calculable": l.non_calculable, "cause": l.cause,
            "couverture_pct": l.couverture_pct,
            "couverture_manquantes": json.dumps(l.couverture_manquantes, ensure_ascii=False),
            "confiance_niveau": l.confiance_niveau,
            "confiance_notes": json.dumps(l.confiance_notes, ensure_ascii=False),
            "contributions": json.dumps(l.contributions, ensure_ascii=False),
            "score_version": l.score_version, "signal_p": l.signal_p,
            "signal_niveau": l.signal_niveau, "signal_version": l.signal_version,
            "cascade_exclue": l.cascade_exclue,
            "cascade_motifs": json.dumps(l.cascade_motifs, ensure_ascii=False),
            "sdp_residuelle_m2": l.sdp_residuelle_m2})
    session.flush()
    return len(lignes)


def as_dicts(lignes: list[LigneScoreLabuse]) -> list[dict]:
    return [asdict(l) for l in lignes]
