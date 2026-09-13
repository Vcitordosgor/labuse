"""REPARATIONS-1 lot 1 — LE CANDIDAT ASSUMÉ : un run candidat non basculé est un état normal,
pas une anomalie.

V3a doit distinguer une génération en trop NON DÉCLARÉE (le vrai danger : des tuiles ou une
table fabriquées en douce, personne ne sait pour quoi) d'un candidat DÉCLARÉ ET ASSUMÉ (Vic a
fabriqué q_v14, ne le basculera pas — il refond l'algorithme, le prochain run sera q_v15 — et
le garde en base comme point de comparaison).

Le geste : `declarer(run_label, par, motif)` — explicite, JOURNALISÉ (circuit_journal, geste
« candidat »), RÉVERSIBLE (`retirer()` ne supprime rien : il tamponne retire_le/retire_par,
l'historique reste). Une seule déclaration active par run. V3a lit `actif()` : si les tuiles
servent exactement le run déclaré, le verrou reste VERT et NOMME le candidat dans sa preuve ;
tout autre écart de génération reste rouge. deploy.sh passe par la même porte (le code retour
des verrous) — aucun chemin de contournement n'est ajouté.
"""
from __future__ import annotations

from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS circuit_candidat_assume (
  id bigserial PRIMARY KEY,
  run_label varchar(64) NOT NULL,
  assume_par varchar(120),
  assume_le timestamptz NOT NULL DEFAULT now(),
  motif text,
  retire_par varchar(120),
  retire_le timestamptz
)
"""


def ensure(db) -> None:
    db.execute(text(DDL))


def actif(db) -> dict | None:
    """La déclaration active (non retirée) la plus récente — None si aucun candidat assumé."""
    ensure(db)
    row = db.execute(text(
        "SELECT run_label, assume_par, assume_le, motif FROM circuit_candidat_assume "
        "WHERE retire_le IS NULL ORDER BY assume_le DESC LIMIT 1")).mappings().first()
    return dict(row) if row else None


def declarer(db, run_label: str, par: str, motif: str) -> dict:
    """Déclarer un run candidat assumé (idempotent : re-déclarer le même run met à jour le
    motif au lieu d'empiler). Journalisé. Le run reste en base, rien n'est purgé."""
    from . import circuit_journal
    ensure(db)
    deja = db.execute(text(
        "SELECT id FROM circuit_candidat_assume WHERE run_label = :r AND retire_le IS NULL"),
        {"r": run_label}).scalar()
    if deja:
        db.execute(text(
            "UPDATE circuit_candidat_assume SET motif = :m, assume_par = :p WHERE id = :i"),
            {"m": motif, "p": par, "i": deja})
    else:
        db.execute(text(
            "INSERT INTO circuit_candidat_assume (run_label, assume_par, motif) "
            "VALUES (:r, :p, :m)"), {"r": run_label, "p": par, "m": motif})
    circuit_journal.journaliser(db, "candidat", run_label, par, "ok",
                                {"geste": "assumer", "motif": motif})
    return {"run_label": run_label, "assume_par": par, "motif": motif,
            "mis_a_jour": bool(deja)}


def retirer(db, run_label: str, par: str) -> dict:
    """Retirer la déclaration (le geste inverse — réversible en re-déclarant). Journalisé.
    Ne touche jamais le run lui-même : seule la déclaration est tamponnée retirée."""
    from . import circuit_journal
    ensure(db)
    n = db.execute(text(
        "UPDATE circuit_candidat_assume SET retire_le = now(), retire_par = :p "
        "WHERE run_label = :r AND retire_le IS NULL"), {"p": par, "r": run_label}).rowcount
    circuit_journal.journaliser(db, "candidat", run_label, par, "ok" if n else "refuse",
                                {"geste": "retirer", "retirees": n})
    return {"run_label": run_label, "retirees": n}


def historique(db, limit: int = 20) -> list[dict]:
    ensure(db)
    return [dict(r) for r in db.execute(text(
        "SELECT run_label, assume_par, assume_le, motif, retire_par, retire_le "
        "FROM circuit_candidat_assume ORDER BY assume_le DESC LIMIT :l"),
        {"l": limit}).mappings().all()]
