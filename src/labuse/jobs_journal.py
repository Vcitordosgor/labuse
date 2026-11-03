"""SOLIDITE-1 (Lot 1.1) — L'HISTORIQUE DES JOBS EN BASE : `job_runs`.

Le fichier d'état JSON (`labuse.jobs.state_path`) ne garde que le DERNIER passage de chaque job ; il est
écrasé à chaque tour. Pour qu'une panne ne passe plus en silence, chaque passage laisse AUSSI une ligne
durable ici (début, fin, statut, durée, erreur, compteurs). On en déduit : le dernier SUCCÈS par job (pour
voir un job EN RETARD), l'historique (page admin), et de quoi écrire le récap du matin.

Écrit par `jobs.exec_one` à la toute fin d'un passage, dans une session courte dédiée — jamais bloquant
(une trace qui rate ne doit pas transformer un job réussi en échec)."""
from __future__ import annotations

import json
import logging

from sqlalchemy import text

log = logging.getLogger("labuse.jobs.journal")

DDL = """
CREATE TABLE IF NOT EXISTS job_runs (
  id serial PRIMARY KEY,
  nom varchar(64) NOT NULL,
  debut timestamptz NOT NULL,
  fin timestamptz,
  statut varchar(16) NOT NULL,
  duree_s double precision,
  dry_run boolean NOT NULL DEFAULT false,
  erreur text,
  compteurs jsonb NOT NULL DEFAULT '{}'::jsonb
)
"""
# un index sur (nom, debut) sert les deux lectures chaudes : dernier succès d'un job, et son historique.
DDL_INDEX = "CREATE INDEX IF NOT EXISTS ix_job_runs_nom_debut ON job_runs (nom, debut DESC)"

#: statuts considérés « réussis » (un dry-run EST un succès fonctionnel : le job a tourné, il n'a
#: simplement rien envoyé faute de SMTP). Tout autre statut (echec/timeout) = passage non réussi.
STATUTS_OK = ("ok", "dry-run")


def ensure_table(db) -> None:
    db.execute(text(DDL))
    db.execute(text(DDL_INDEX))


def enregistrer(db, etat: dict) -> None:
    """Pose UNE ligne `job_runs` depuis l'état d'un passage (cf. jobs.exec_one). Jamais bloquant."""
    ensure_table(db)
    db.execute(text(
        "INSERT INTO job_runs (nom, debut, fin, statut, duree_s, dry_run, erreur, compteurs) "
        "VALUES (:nom, :debut, :fin, :statut, :duree_s, :dry_run, :erreur, CAST(:compteurs AS jsonb))"),
        {"nom": etat.get("nom"), "debut": etat.get("debut"), "fin": etat.get("fin"),
         "statut": etat.get("statut") or "inconnu", "duree_s": etat.get("duree_s"),
         "dry_run": bool(etat.get("dry_run")), "erreur": etat.get("erreur"),
         "compteurs": json.dumps(etat.get("compteurs") or {}, ensure_ascii=False)})


def dernier_succes(db) -> dict[str, object]:
    """Pour chaque job : l'instant du dernier passage RÉUSSI (ok/dry-run). Clé = nom, valeur = datetime.
    Un job jamais réussi n'apparaît pas (l'appelant traite l'absence comme « en retard »)."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT nom, max(fin) AS le FROM job_runs "
        "WHERE statut IN ('ok','dry-run') GROUP BY nom")).all()
    return {r[0]: r[1] for r in rows if r[1] is not None}


def premiere_activite(db):
    """FIX-NU3-3 (I-ADM-01 / L-JOB-01) — le plus ANCIEN passage journalisé, tous jobs confondus :
    « le système tourne au moins depuis cet instant ». Sert de référence pour dire qu'un job planifié
    qui n'a JAMAIS réussi (ni même tourné) est EN RETARD — un cron jamais tiré est invisible sinon.
    None si la table est vide (système tout neuf : on ne crie pas « jamais lancé » sur une base vierge)."""
    ensure_table(db)
    return db.execute(text("SELECT min(debut) FROM job_runs")).scalar()


# OPS-NUIT-2 — ANCRE « premier passage prévu » : l'instant où un job planifié devient CONNU (déployé).
# Avant, « jamais réussi » se jugeait sur l'âge du SYSTÈME (premiere_activite) : un job NEUF (resume-matin,
# ajouté en journée) était crié « jamais réussi » dès son déploiement, bien AVANT son premier passage
# prévu (07h30). Désormais la vigie ancre le délai sur la 1ʳᵉ fois qu'elle VOIT le job : son premier
# passage cron se calcule à partir de là, et on n'alerte qu'une fois ce passage + marge dépassé. Un job
# qui a DÉJÀ un historique s'ancre sur son tout premier run (il existait bien avant d'être « vu »).
DDL_PREMIERE_VUE = """
CREATE TABLE IF NOT EXISTS job_premiere_vue (
  nom varchar(64) PRIMARY KEY,
  vue_at timestamptz NOT NULL DEFAULT now()
)
"""


def _ensure_premiere_vue(db) -> None:
    present = db.execute(text("SELECT to_regclass('job_premiere_vue') IS NOT NULL")).scalar()
    if not present:
        db.execute(text(DDL_PREMIERE_VUE))


def premiere_vue(db) -> dict[str, object]:
    """Pour chaque job connu : l'instant où il a été vu pour la première fois (ancre du 1er passage prévu)."""
    _ensure_premiere_vue(db)
    rows = db.execute(text("SELECT nom, vue_at FROM job_premiere_vue")).all()
    return {r[0]: r[1] for r in rows}


def marquer_vues(db, noms) -> None:
    """Enregistre la 1ʳᵉ vue des jobs encore inconnus. Un job qui a DÉJÀ tourné s'ancre sur son plus
    ancien run (il existait avant d'être « vu ») ; sinon sur maintenant. Idempotent (ON CONFLICT DO
    NOTHING) : la valeur n'est jamais écrasée une fois posée. Jamais bloquant."""
    _ensure_premiere_vue(db)
    for nom in noms:
        # CAST explicite : `:n` sert deux fois (valeur insérée + filtre du sous-SELECT) → sans type forcé,
        # Postgres hésite entre text et varchar (AmbiguousParameter) et AVORTE la transaction.
        db.execute(text(
            "INSERT INTO job_premiere_vue (nom, vue_at) "
            "SELECT CAST(:n AS varchar), "
            "       COALESCE((SELECT min(debut) FROM job_runs WHERE nom = CAST(:n AS varchar)), now()) "
            "ON CONFLICT (nom) DO NOTHING"), {"n": nom})


def dernier_passage(db) -> dict[str, dict]:
    """Pour chaque job : son DERNIER passage quel qu'en soit le statut (le plus récent par `debut`)."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT DISTINCT ON (nom) nom, statut, fin, duree_s, erreur, dry_run "
        "FROM job_runs ORDER BY nom, debut DESC")).mappings().all()
    return {r["nom"]: {"statut": r["statut"], "fin": r["fin"].isoformat() if r["fin"] else None,
                       "duree_s": r["duree_s"], "erreur": r["erreur"], "dry_run": r["dry_run"]}
            for r in rows}


def historique(db, nom: str, n: int = 30) -> list[dict]:
    """Les N derniers passages d'un job (page admin › Horloge)."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT debut, fin, statut, duree_s, dry_run, erreur, compteurs FROM job_runs "
        "WHERE nom = :nom ORDER BY debut DESC LIMIT :n"), {"nom": nom, "n": n}).mappings().all()
    return [{**dict(r), "debut": r["debut"].isoformat(),
             "fin": r["fin"].isoformat() if r["fin"] else None} for r in rows]
