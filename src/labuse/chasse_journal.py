"""SOLIDITE-1 (Lot 2) — LE JOURNAL DU BANC CHASSE-DONNÉES : chaque nuit, les 25 gardes, sur la prod.

Le banc `scripts.coherence.chasse_donnees` tient une garde par écart reproductible de la chasse (surface
tuile vs fiche, export cascade vide, SIRENE cessée active, CatNat à zéro…). COHERENCE-1 a prouvé qu'un
cache périmé en silence fait mentir des écrans pendant des mois : ce journal rejoue les gardes chaque nuit
et, au PREMIER écart, ouvre un incident par la porte d'alerte UNIQUE (ops_alertes — mail Vic + cloche),
avec la garde, la parcelle témoin et l'écart. L'historique se lit dans la page Données.

Toute garde nouvelle ajoutée à `GARDES` (chasse_donnees) entre AUTOMATIQUEMENT dans le passage : on itère
la liste, jamais une copie tenue à la main.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import text

log = logging.getLogger("labuse.chasse")

DDL = """
CREATE TABLE IF NOT EXISTS chasse_runs (
  id serial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  n_gardes integer NOT NULL,
  n_ok integer NOT NULL,
  n_ecart integer NOT NULL,
  n_skip integer NOT NULL,
  ecarts jsonb NOT NULL DEFAULT '[]'::jsonb,
  ecart_cles jsonb NOT NULL DEFAULT '[]'::jsonb
)
"""


def ensure_table(db) -> None:
    db.execute(text(DDL))


def journaliser_passage(db, resultats: list[tuple[str, str, str]]) -> dict:
    """Résume un passage des gardes (liste (nom, verdict, detail), verdict ∈ OK/ECART/SKIP) dans
    `chasse_runs`, PUIS pour chaque garde : un écart ouvre/rappelle l'incident `chasse:<garde>` par la
    porte unique (mail + cloche) ; un retour au vert le referme. Compare aux clés d'écart du passage
    précédent pour COMPTER les écarts NOUVEAUX (le reste = rappel quotidien, pas une alerte neuve)."""
    ensure_table(db)
    ok = [r for r in resultats if r[1] == "OK"]
    ecarts = [r for r in resultats if r[1] == "ECART"]
    skips = [r for r in resultats if r[1] == "SKIP"]
    ecart_cles = sorted(r[0] for r in ecarts)
    precedent = db.execute(text(
        "SELECT ecart_cles FROM chasse_runs ORDER BY id DESC LIMIT 1")).scalar()
    connues = set(precedent or [])
    nouveaux = [c for c in ecart_cles if c not in connues]
    db.execute(text(
        "INSERT INTO chasse_runs (n_gardes, n_ok, n_ecart, n_skip, ecarts, ecart_cles) "
        "VALUES (:g, :ok, :e, :s, CAST(:ec AS jsonb), CAST(:cl AS jsonb))"),
        {"g": len(resultats), "ok": len(ok), "e": len(ecarts), "s": len(skips),
         "ec": json.dumps([{"garde": n, "detail": d} for n, v, d in ecarts], ensure_ascii=False),
         "cl": json.dumps(ecart_cles)})
    # alerte par la porte UNIQUE (Lot 1) : un incident par garde en écart, un retour au vert le referme.
    from . import ops_alertes
    for nom, verdict, detail in resultats:
        cle = f"chasse:{nom}"
        if verdict == "ECART":
            ops_alertes.signaler(db, cle, f"Banc chasse : écart sur « {nom} »",
                                 f"La garde « {nom} » du banc des données servies MORD : {detail}\n"
                                 "(Un client lit potentiellement une valeur fausse. Détail : page Données.)")
        elif verdict == "OK":
            ops_alertes.resoudre(db, cle)
        # SKIP (garde non évaluable ce soir) : on ne touche à rien — ni alerte, ni résolution hâtive.
    return {"n_gardes": len(resultats), "ok": len(ok), "ecart": len(ecarts),
            "skip": len(skips), "ecart_nouveaux": len(nouveaux),
            "ecarts": [n for n, v, d in ecarts]}


def derniers_passages(db, n: int = 14) -> list[dict]:
    """Les N derniers passages (onglet Données › Chasse)."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT ts, n_gardes, n_ok, n_ecart, n_skip, ecarts FROM chasse_runs "
        "ORDER BY id DESC LIMIT :n"), {"n": n}).mappings().all()
    return [{**dict(r), "ts": r["ts"].isoformat()} for r in rows]
