"""FLUX-1 (F2.3/F2.4) — LA BASCULE : changer le run courant, en connaissance de cause et sans dette.

La bascule est l'unique événement qui change ce que voient les clients côté scores. Elle :
  1. REFUSE si le run n'est pas complet (cascade + score v2 présents pour le label) ;
  2. réécrit le pointeur unique (`golden_ops.promote` → `config/served_run.txt`) ;
  3. fait suivre `config/run_precedent.txt` (l'ancien run) — jamais un nom de run en dur (doctrine M80) ;
  4. PURGE tous les caches recensés en CONNEXIONS-1 A6 (dans le process API) ;
  5. JOURNALISE qui, quand, de quel run vers lequel (`run_bascule_journal`) ;
  6. exécute la garde de cohérence IMMÉDIATEMENT (F4.3) et l'affiche.

Le RETOUR ARRIÈRE est la même action dans l'autre sens (basculer vers le run précédent). Aucun run
n'est jamais supprimé. Rien n'est automatique : c'est un geste humain (admin).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

_RUN_PRECEDENT_FILE = Path(__file__).resolve().parents[2] / "config" / "run_precedent.txt"

#: les caches recensés en CONNEXIONS-1 A6 — chacun avec le nom de son purgeur. Purge best-effort (un
#: cache absent/déjà froid n'est jamais une erreur). Ceux auto-invalidés (tuiles LRU sur mvt_meta)
#: sont purgés aussi par prudence. Renvoyé au journal : ce qui a réellement été purgé.
def purger_caches_run() -> list[str]:
    """Purge, dans CE process, tous les caches A6 dont le contenu dépend du run servi. Retourne la
    liste des caches effectivement purgés (traçabilité de la bascule)."""
    purges: list[str] = []

    def _try(nom: str, fn) -> None:
        try:
            fn()
            purges.append(nom)
        except Exception:  # noqa: BLE001 — un cache qui refuse de se purger ne casse pas la bascule
            pass

    from . import config as _config
    _try("config (yaml/settings/rules_version)", _config.reset_config_cache)
    from . import rnu as _rnu
    _try("rnu (_entries)", _rnu.clear_cache)
    from .api import projets as _projets
    _try("projets (_COMPTEUR_CACHE)", lambda: _projets._COMPTEUR_CACHE.clear())
    from .api import banquier as _banquier
    _try("banquier (_PDF_CACHE)", lambda: _banquier._PDF_CACHE.clear())
    from .api import accueil as _accueil
    _try("accueil (chiffres/contexte/fraîcheur)", lambda: (
        _accueil._cache.update(at=0.0, data=None),
        _accueil._cs_cache.update(at=0.0, data=None),
        _accueil._fr_cache.update(at=0.0, data=None)))
    from .api import protection as _protection
    _try("protection (_gels_cache)", lambda: _protection._gels_cache.update(at=0.0, sujets={}))
    from .api import tiles as _tiles
    _try("tuiles carte (LRU)", lambda: _tiles._CACHE.clear())
    return purges


def ensure_tables(engine) -> None:
    """Idempotent — le journal des bascules (qui, quand, de quel run vers lequel + caches purgés)."""
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS run_bascule_journal ("
            " id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),"
            " ancien varchar(64), nouveau varchar(64) NOT NULL,"
            " par varchar(120), sens varchar(12) NOT NULL DEFAULT 'avant',"   # avant | arriere
            " caches_purges jsonb NOT NULL DEFAULT '[]'::jsonb,"
            " coherence jsonb)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_bascule_journal_ts ON run_bascule_journal(ts DESC)"))


def _run_complet(db: Session, run: str) -> tuple[bool, str]:
    """Le run est-il SERVABLE ? Présent en score v2 (`p_score_v2_runs`) ET en cascade
    (`dryrun_parcel_evaluations`) — sinon la fiche retomberait en repli legacy silencieux
    (cf. `bascule_gardes.check_coherence_run_fiche`). Refus BRUYANT sinon."""
    v2 = db.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id = :r"), {"r": run}).scalar()
    casc = None
    if db.execute(text("SELECT to_regclass('dryrun_parcel_evaluations')")).scalar():
        casc = db.execute(text(
            "SELECT 1 FROM dryrun_parcel_evaluations WHERE run_label = :r LIMIT 1"), {"r": run}).scalar()
    if not v2:
        return False, f"run « {run} » absent de p_score_v2_runs (non scoré) — bascule refusée."
    if casc is None:
        return True, "cascade non vérifiable (table absente) — toléré hors production."
    if not casc:
        return False, f"run « {run} » absent de la cascade (dryrun_parcel_evaluations) — bascule refusée."
    return True, "run complet (score v2 + cascade)."


def runs_termines(db: Session) -> list[dict]:
    """F2.3 — la liste des runs terminés, avec pour chacun l'ÉCART au run courant (tiers qui changent,
    répartition Priorité/À suivre avant/après). Le run servi est marqué. Lecture seule."""
    from . import runs
    from .golden_ops import comparer
    labels = [r[0] for r in db.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 12")).all()]
    out = []
    servi_run = runs.current()
    for lab in labels:
        est_servi = (lab == servi_run)
        ecart = None
        if not est_servi:
            c = comparer(lab)
            if c.get("ok"):
                n_change = db.execute(text(
                    "SELECT count(*) FROM parcel_p_score_v2 a JOIN parcel_p_score_v2 b "
                    " ON a.parcelle_id = b.parcelle_id "
                    "WHERE a.run_id = :cand AND b.run_id = :servi AND a.tier IS DISTINCT FROM b.tier"),
                    {"cand": lab, "servi": servi_run}).scalar() or 0
                ecart = {"tiers_changes": int(n_change),
                         "promues_candidat": c["promues_candidat"], "promues_servi": c["promues_servi"],
                         "derive_promues_pct": c["derive_promues_pct"]}
        complet, motif = _run_complet(db, lab)
        row = db.execute(text(
            "SELECT computed_at, n_parcelles FROM p_score_v2_runs WHERE run_id = :r"),
            {"r": lab}).mappings().first()
        out.append({"label": lab, "servi": est_servi, "complet": complet, "motif": motif,
                    "calcule_le": row["computed_at"].isoformat() if row and row["computed_at"] else None,
                    "n_parcelles": row["n_parcelles"] if row else None, "ecart": ecart})
    return out


def derniere_bascule(db: Session) -> dict | None:
    """La dernière bascule journalisée (pour la garde « caches purgés à la dernière bascule »)."""
    if not db.execute(text("SELECT to_regclass('run_bascule_journal')")).scalar():
        return None
    r = db.execute(text(
        "SELECT ts, ancien, nouveau, par, sens, caches_purges FROM run_bascule_journal "
        "ORDER BY ts DESC LIMIT 1")).mappings().first()
    if not r:
        return None
    return {"ts": r["ts"].isoformat() if r["ts"] else None, "ancien": r["ancien"],
            "nouveau": r["nouveau"], "par": r["par"], "sens": r["sens"],
            "caches_purges": r["caches_purges"] or []}


def basculer(db: Session, nouveau_run: str, par: str) -> dict:
    """LA BASCULE (F2.3). Refuse un run incomplet ; sinon promeut, fait suivre le précédent, purge les
    caches, journalise, et lance la garde de cohérence immédiatement (F4.3). `par` = qui (traçabilité).
    Le retour arrière est cette même fonction appelée avec le run précédent."""
    from . import runs
    from .golden_ops import promote

    ancien = runs.current()
    if nouveau_run == ancien:
        return {"ok": False, "motif": f"« {nouveau_run} » est déjà le run servi — rien à basculer."}
    complet, motif = _run_complet(db, nouveau_run)
    if not complet:
        return {"ok": False, "motif": motif}

    prom = promote(nouveau_run)         # réécrit config/served_run.txt (valide l'existence en base)
    if not prom.get("ok"):
        return {"ok": False, "motif": prom.get("motif", "promotion refusée")}
    # run_precedent.txt suit (M80) — l'ancien run servi devient le précédent, pour un retour arrière tracé.
    entete = ("# config/run_precedent.txt — run servi PRÉCÉDENT (M80). Suit served_run.txt à chaque\n"
              "# bascule (FLUX-1 F2.4 : le retour arrière est la bascule dans l'autre sens).\n")
    _RUN_PRECEDENT_FILE.write_text(entete + ancien + "\n", encoding="utf-8")

    caches = purger_caches_run()
    from .scoring.score_v_constants import RUN_PRECEDENT
    sens = "arriere" if nouveau_run == RUN_PRECEDENT else "avant"

    # garde de cohérence IMMÉDIATE, mesurée contre le NOUVEAU run (lu frais du fichier, pas la
    # constante import-time encore chaude dans ce process).
    from . import coherence_flux
    coherence = coherence_flux.verifier(db, run=nouveau_run)

    import json as _json
    db.execute(text(
        "INSERT INTO run_bascule_journal (ancien, nouveau, par, sens, caches_purges, coherence) "
        "VALUES (:a, :n, :p, :s, :c, :co)"),
        {"a": ancien, "n": nouveau_run, "p": par[:120], "s": sens,
         "c": _json.dumps(caches), "co": _json.dumps(coherence)})

    return {"ok": True, "ancien": ancien, "nouveau": nouveau_run, "caches_purges": caches,
            "coherence": coherence,
            "note": "Effectif au redémarrage du process API (le pointeur est versionné ; "
                    "la constante Q_A_RUN_LABEL est relue au démarrage)."}
