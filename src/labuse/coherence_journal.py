"""COHERENCE-FIX-1 (lot G) — LE JOURNAL DU BANC : chaque passage compte, le premier écart sonne.

Le banc (`labuse coherence`, job nocturne `coherence-banc`) écrit ECARTS.csv ; ce module
résume le passage dans `coherence_runs` (l'onglet « Cohérence » de la page Données le lit)
et fait SONNER la cloche admin au premier écart FAUX-CLIENT NOUVEAU (comparé au passage
précédent par (notion, objet) — un écart déjà connu ne re-sonne pas chaque nuit).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy import text

_RACINE = Path(__file__).resolve().parents[2]
ECARTS_CSV = _RACINE / "docs" / "audit-2026-09" / "COHERENCE-1" / "ECARTS.csv"

DDL = """
CREATE TABLE IF NOT EXISTS coherence_runs (
  id serial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  mode varchar(16) NOT NULL,
  n_comparaisons integer,
  n_ecarts integer NOT NULL,
  faux_client integer NOT NULL,
  incoherent integer NOT NULL,
  tolerable integer NOT NULL,
  erreurs_lecteur integer NOT NULL DEFAULT 0,
  faux_client_cles jsonb NOT NULL DEFAULT '[]'::jsonb,
  fichier text
)
"""


def lire_ecarts(fichier: Path | None = None) -> list[dict]:
    p = fichier or ECARTS_CSV
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def journaliser_passage(db, mode: str, fichier: Path | None = None) -> dict:
    """Résume ECARTS.csv du jour dans `coherence_runs` + cloche au premier FAUX-CLIENT nouveau.
    Les lignes « erreur lecteur » (API indisponible/limitée) sont comptées À PART : un banc qui
    n'a pas pu lire ne fabrique pas de faux écarts — il le dit."""
    db.execute(text(DDL))
    lignes = lire_ecarts(fichier)
    erreurs = [l for l in lignes if l.get("cause") == "erreur"]
    reels = [l for l in lignes if l.get("cause") != "erreur"]
    fc = [l for l in reels if l.get("gravite") == "FAUX-CLIENT"]
    inco = [l for l in reels if l.get("gravite") == "INCOHERENT"]
    tol = [l for l in reels if l.get("gravite") == "TOLERABLE"]
    cles_fc = sorted({f"{l.get('notion')}|{l.get('objet')}" for l in fc})
    precedent = db.execute(text(
        "SELECT faux_client_cles FROM coherence_runs ORDER BY id DESC LIMIT 1")).scalar()
    connues = set(precedent or [])
    nouvelles = [c for c in cles_fc if c not in connues]
    db.execute(text(
        "INSERT INTO coherence_runs (mode, n_ecarts, faux_client, incoherent, tolerable,"
        " erreurs_lecteur, faux_client_cles, fichier) "
        "VALUES (:m, :n, :f, :i, :t, :e, CAST(:c AS jsonb), :fp)"),
        {"m": mode, "n": len(reels), "f": len(fc), "i": len(inco), "t": len(tol),
         "e": len(erreurs), "c": json.dumps(cles_fc), "fp": str(fichier or ECARTS_CSV)})
    if nouvelles:
        try:
            from .api.events import creer_notification
            creer_notification(
                db, kind="systeme", compte_id=None, source="Cohérence",
                titre=f"Banc de cohérence : {len(nouvelles)} écart(s) FAUX-CLIENT nouveau(x)",
                detail=("Un client lit une valeur fausse quelque part : "
                        + " ; ".join(nouvelles[:5])
                        + (f" (+{len(nouvelles)-5})" if len(nouvelles) > 5 else "")
                        + ". Détail : ECARTS.csv du jour (page Données › Cohérence)."),
                lien="/admin", dedup=f"coherence-fc:{len(nouvelles)}:{cles_fc[:1]}")
        except Exception:  # noqa: BLE001 — une cloche qui rate ne casse pas le passage
            pass
    return {"mode": mode, "ecarts": len(reels), "faux_client": len(fc),
            "incoherent": len(inco), "tolerable": len(tol),
            "erreurs_lecteur": len(erreurs), "faux_client_nouveaux": len(nouvelles)}


def derniers_passages(db, n: int = 14) -> list[dict]:
    """Les N derniers passages (onglet Cohérence de la page Données)."""
    db.execute(text(DDL))
    rows = db.execute(text(
        "SELECT ts, mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur,"
        " faux_client_cles, fichier FROM coherence_runs ORDER BY id DESC LIMIT :n"),
        {"n": n}).mappings().all()
    return [{**dict(r), "ts": r["ts"].isoformat()} for r in rows]
