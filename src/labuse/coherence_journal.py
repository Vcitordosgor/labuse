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
  fichier text,
  -- OPS-3 (A) — le résultat NOMME le run contrôlé (`run_servi`) et dit s'il est allé au bout
  -- (`acheve`). Un passage qui n'a pas achevé ses phases, ou qui a sauté une vérification (banc2
  -- indisponible, gardes toutes en SKIP, balayage illisible…) porte `acheve = false` + le motif :
  -- les contrôles de promotion, le résumé et les incidents le lisent comme un ÉCHEC, jamais un vert.
  run_servi text,
  acheve boolean NOT NULL DEFAULT true,
  incomplet_motif text
)
"""
#: colonnes ajoutées par OPS-3 sur une table déjà créée (CREATE IF NOT EXISTS ne les pose pas).
_MIGRATIONS = (
    "ALTER TABLE coherence_runs ADD COLUMN IF NOT EXISTS run_servi text",
    "ALTER TABLE coherence_runs ADD COLUMN IF NOT EXISTS acheve boolean NOT NULL DEFAULT true",
    "ALTER TABLE coherence_runs ADD COLUMN IF NOT EXISTS incomplet_motif text",
)


def _assurer_schema(db) -> None:
    db.execute(text(DDL))
    for sql in _MIGRATIONS:
        db.execute(text(sql))


def lire_ecarts(fichier: Path | None = None) -> list[dict]:
    p = fichier or ECARTS_CSV
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def journaliser_passage(db, mode: str, fichier: Path | None = None, *,
                        run_servi: str | None = None, acheve: bool = True,
                        incomplet_motif: str | None = None) -> dict:
    """Résume ECARTS.csv du jour dans `coherence_runs` + cloche au premier FAUX-CLIENT nouveau.
    Les lignes « erreur lecteur » (API indisponible/limitée) sont comptées À PART : un banc qui
    n'a pas pu lire ne fabrique pas de faux écarts — il le dit.

    OPS-3 (A) — le passage NOMME le run contrôlé (`run_servi`) et déclare s'il est allé au bout
    (`acheve` + `incomplet_motif`). Renvoie en plus `id` (pour `marquer_incomplet`), `run_servi`,
    `acheve`, `incomplet_motif`."""
    _assurer_schema(db)
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
    rid = db.execute(text(
        "INSERT INTO coherence_runs (mode, n_ecarts, faux_client, incoherent, tolerable,"
        " erreurs_lecteur, faux_client_cles, fichier, run_servi, acheve, incomplet_motif) "
        "VALUES (:m, :n, :f, :i, :t, :e, CAST(:c AS jsonb), :fp, :rs, :ac, :im) RETURNING id"),
        {"m": mode, "n": len(reels), "f": len(fc), "i": len(inco), "t": len(tol),
         "e": len(erreurs), "c": json.dumps(cles_fc), "fp": str(fichier or ECARTS_CSV),
         "rs": run_servi, "ac": bool(acheve), "im": incomplet_motif}).scalar()
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
    return {"id": int(rid), "mode": mode, "ecarts": len(reels), "faux_client": len(fc),
            "incoherent": len(inco), "tolerable": len(tol),
            "erreurs_lecteur": len(erreurs), "faux_client_nouveaux": len(nouvelles),
            "run_servi": run_servi, "acheve": bool(acheve), "incomplet_motif": incomplet_motif}


def marquer_incomplet(db, run_id: int, motif: str) -> None:
    """OPS-3 (A) — scelle un passage déjà journalisé comme NON ACHEVÉ (banc2 indisponible, gardes
    toutes en SKIP, banc interrompu…). Le passage n'est plus lu comme un vert nulle part."""
    _assurer_schema(db)
    db.execute(text(
        "UPDATE coherence_runs SET acheve = false, "
        "incomplet_motif = COALESCE(NULLIF(incomplet_motif, ''), :m) WHERE id = :id"),
        {"m": motif, "id": int(run_id)})


def derniers_passages(db, n: int = 14) -> list[dict]:
    """Les N derniers passages (onglet Cohérence de la page Données)."""
    _assurer_schema(db)
    rows = db.execute(text(
        "SELECT ts, mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur,"
        " faux_client_cles, fichier, run_servi, acheve, incomplet_motif "
        "FROM coherence_runs ORDER BY id DESC LIMIT :n"),
        {"n": n}).mappings().all()
    return [{**dict(r), "ts": r["ts"].isoformat()} for r in rows]
