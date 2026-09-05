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

# RETOURS-10 (T2) — cache des écarts (candidat, servi) → immuable (runs append-only). Vidé à la bascule
# (le run servi change) par `_ECART_CACHE.clear()` dans le chemin de bascule ; sinon borné (~12 runs).
_ECART_CACHE: dict[tuple[str, str], dict] = {}

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
    # RETOURS-10 (T2) — écarts de runs (Circuit) : le servi change → l'écart de chaque candidat à lui aussi.
    _try("flux (_ECART_CACHE)", _ECART_CACHE.clear)
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


def runs_termines(db: Session, limit_ecart: int = 4) -> list[dict]:
    """F2.3 — la liste des runs terminés, avec pour chacun l'ÉCART au run courant (tiers qui changent,
    répartition Priorité/À suivre avant/après). Le run servi est marqué. Lecture seule.

    RETOURS-9 (Q1) — l'écart est COÛTEUX à calculer (par run non-servi : `comparer()` ~5 s +
    un COUNT self-join sur parcel_p_score_v2, 3 M lignes, ~2,4 s). Sur la base réelle de Vic
    (7 runs, 6 non-servis) cela faisait ~50 s et bloquait toute la page Circuit. On ne calcule
    donc l'écart QUE pour les `limit_ecart` premiers runs non-servis — exactement ceux que la
    page affiche (elle en montre 4). Les autres sortent avec `ecart=None` (label + « basculable »
    restent disponibles). `limit_ecart=None` = tout calculer (compat/CLI)."""
    from . import run_progress, runs
    from .golden_ops import comparer
    labels = [r[0] for r in db.execute(text(
        "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 12")).all()]
    out = []
    servi_run = runs.current()
    # DONNEES-2 (B2) — le STATUT de chaque run (D3). Le précédent est lu VIVANT (B4), plus la constante.
    precedent_run = runs.precedent()
    servi_at = db.execute(text("SELECT computed_at FROM p_score_v2_runs WHERE run_id = :r"),
                          {"r": servi_run}).scalar()
    # réconcilie les états lancés : un run tué / un process disparu passe « abandonné » (D3).
    complets_all = {r[0] for r in db.execute(text("SELECT run_id FROM p_score_v2_runs")).all()}
    run_progress.reconcile(complets_all)

    def _statut(lab: str, complet: bool, computed_at) -> str:
        if lab == servi_run:
            return "servi"
        if lab == precedent_run:
            return "retour_arriere"
        if not complet:
            return "abandonne"          # présent en base mais pas servable (rare) — traité comme les tués
        if servi_at is not None and computed_at is not None and computed_at >= servi_at:
            return "termine"            # complet et PLUS RÉCENT que le servi = candidat en avant (recommandé)
        return "ancien"                 # complet mais plus ancien que le servi = retour arrière profond

    ecarts_calcules = 0
    for lab in labels:
        est_servi = (lab == servi_run)
        ecart = None
        calcul_ok = limit_ecart is None or ecarts_calcules < limit_ecart
        if not est_servi and calcul_ok:
            ecarts_calcules += 1
            # RETOURS-10 (T2) — l'écart (candidat, servi) est IMMUABLE (les runs sont append-only, jamais
            # réécrits sous le même id) : on le mémoïse. Le COUNT self-join sur parcel_p_score_v2 (~1,5 s)
            # et la comparaison ne se refont plus à chaque ouverture de Circuit. Clé = (lab, servi).
            ecart = _ECART_CACHE.get((lab, servi_run))
            if ecart is None:
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
                    _ECART_CACHE[(lab, servi_run)] = ecart
        complet, motif = _run_complet(db, lab)
        row = db.execute(text(
            "SELECT computed_at, n_parcelles, model_version, "
            "       params ->> 'recette' AS recette, "
            "       params ->> 'note_de_version' AS note_de_version "
            "FROM p_score_v2_runs WHERE run_id = :r"),
            {"r": lab}).mappings().first()
        out.append({"label": lab, "servi": est_servi, "complet": complet, "motif": motif,
                    "statut": _statut(lab, complet, row["computed_at"] if row else None),
                    "calcule_le": row["computed_at"].isoformat() if row and row["computed_at"] else None,
                    "n_parcelles": row["n_parcelles"] if row else None, "ecart": ecart,
                    # SCORING-3 (L1.3) — la note de version du candidat, lisible AVANT de basculer.
                    "modele": row["model_version"] if row else None,
                    "recette": (row["recette"] or row["model_version"]) if row else None,
                    "note_de_version": row["note_de_version"] if row else None})
    # DONNEES-2 (B2/D3) — AJOUTE les runs LANCÉS mais non terminés (en cours / abandonnés) : ils
    # n'existent pas dans p_score_v2_runs (aucune ligne écrite), seulement via leur état de progression.
    connus = {r["label"] for r in out}
    for st in run_progress.list_states():
        lab = st.get("label")
        if not lab or lab in connus or lab in complets_all or st.get("kind") != "run":
            continue
        statut = st.get("statut") or "abandonne"
        out.append({"label": lab, "servi": False, "complet": False,
                    "motif": st.get("error") or ("en cours" if statut == "en_cours" else "run abandonné"),
                    "statut": statut, "calcule_le": st.get("started_at"),
                    "n_parcelles": st.get("n_parcelles"), "ecart": None,
                    "modele": None, "recette": st.get("recette"), "note_de_version": None,
                    "progress": {"phase": st.get("phase"), "commune": st.get("commune"),
                                 "pct": st.get("pct"), "done": st.get("done"), "total": st.get("total")}})
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
    # DONNEES-2 (B4) — le SENS (avant / retour arrière) se lit du pointeur VIVANT AVANT de le réécrire :
    # « arrière » = on rebascule vers ce qui était le run précédent. La constante figée mentait ici.
    ancien_precedent = runs.precedent()
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

    # CIRCUIT-1 lot 3.1/3.2 — LE MANIFESTE : un seul écrit ATOMIQUE déplace scoring, résiduel,
    # mvt et division (décision Vic n° 5). Revenir (nouveau == ancien précédent) restaure le
    # manifeste PRÉCÉDENT ENTIER (résiduel et division compris) — une bascule scoring ne peut
    # plus laisser le résiduel derrière. served_run.txt/run_precedent.txt (ci-dessus) et
    # residuel_runs.is_served (ci-dessous) sont désormais des VUES DÉRIVÉES de cet écrit.
    from . import manifeste as _manifeste
    m_avant = _manifeste.lire() or _manifeste.construire_depuis_pointeurs(db)
    if nouveau_run == ancien_precedent and m_avant.get("precedent"):
        cible = dict(m_avant["precedent"])            # retour arrière : le manifeste entier
    else:
        cible = {"scoring_run": nouveau_run, "mvt_run": nouveau_run, "division_run": nouveau_run,
                 "residuel_run_seq": m_avant.get("residuel_run_seq")}
    from datetime import datetime as _dt, timezone as _tz
    nouveau_manifeste = {**cible,
                         "promoted_at": _dt.now(tz=_tz.utc).isoformat(), "par": par[:120],
                         "precedent": {k: m_avant.get(k) for k in
                                       ("scoring_run", "residuel_run_seq", "mvt_run", "division_run")}}
    _manifeste.ecrire(nouveau_manifeste)
    # vue dérivée résiduel : is_served suit le manifeste (jamais un autre chemin — lot 3.1).
    if nouveau_manifeste.get("residuel_run_seq") is not None:
        try:
            from .faisabilite import residuel_runs as _rr
            _rr.set_served(db, int(nouveau_manifeste["residuel_run_seq"]))
        except Exception:  # noqa: BLE001 — chaîne résiduel absente (base de test) : la vue suit plus tard
            pass
    runs.invalidate()                   # DONNEES-2 (B4) — servi ET précédent relus au prochain appel

    caches = purger_caches_run()
    # CIRCUIT-1 lot 2.7 — le cache spatial des isochrones se purge AUSSI à la bascule (en plus du
    # TTL 30 j lu par zone.isochrone) : après un geste qui change le servi, plus aucune géométrie
    # figée. Un cache qui refuse de se purger ne casse pas la bascule (même règle que les autres).
    try:
        n_iso = db.execute(text("DELETE FROM zone_isochrone_cache")).rowcount
        caches.append(f"zone_isochrone_cache ({n_iso} entrées)")
    except Exception:  # noqa: BLE001
        pass
    sens = "arriere" if nouveau_run == ancien_precedent else "avant"

    # garde de cohérence IMMÉDIATE, mesurée contre le NOUVEAU run (lu frais du fichier).
    from . import coherence_flux
    coherence = coherence_flux.verifier(db, run=nouveau_run)

    import json as _json
    db.execute(text(
        "INSERT INTO run_bascule_journal (ancien, nouveau, par, sens, caches_purges, coherence) "
        "VALUES (:a, :n, :p, :s, :c, :co)"),
        {"a": ancien, "n": nouveau_run, "p": par[:120], "s": sens,
         "c": _json.dumps(caches), "co": _json.dumps(coherence)})
    # CIRCUIT-1 lot 3.6 — le journal UNIFIÉ des gestes (en plus du journal de bascule dédié).
    from . import circuit_journal
    circuit_journal.journaliser(
        db, "revenir" if sens == "arriere" else "basculer", nouveau_run, par, "ok",
        {"ancien": ancien, "manifeste": nouveau_manifeste, "coherence_ok": coherence.get("ok")})

    return {"ok": True, "ancien": ancien, "nouveau": nouveau_run, "caches_purges": caches,
            "sens": sens, "coherence": coherence,
            "note": "Effective immédiatement (served_run.txt relu à la requête). Les tables servies "
                    "run-scopées et les tuiles se reconstruisent ensuite (build-mvt détaché)."}


# ═══════════════ CIRCUIT-1 lot 3.3 — la NOTE DE VERSION (registre) + garde résiduel ═══════════════

def residuel_entrees_changees(db: Session) -> dict:
    """Lot 3.2 — les ENTRÉES du résiduel (PLU/GPU, cadastre, CoSIA) ont-elles bougé depuis le run
    résiduel SERVI ? Comparaison par les tampons de data_sources (last_sync_at) contre la date de
    calcul du run servi (residuel_runs.computed_at_max). Si oui : un candidat résiduel doit être
    calculé AVANT la bascule (sinon le manifeste candidat reporte le servi, décision « au plus malin »)."""
    try:
        servi = db.execute(text(
            "SELECT computed_at_max FROM residuel_runs WHERE is_served LIMIT 1")).scalar()
    except Exception:  # noqa: BLE001 — chaîne résiduel absente (base de test)
        return {"changees": False, "detail": "chaîne résiduel absente"}
    if servi is None:
        return {"changees": False, "detail": "aucun run résiduel servi"}
    rows = db.execute(text(
        "SELECT name, last_sync_at FROM data_sources WHERE (name ILIKE 'Urbanisme PLU/GPU%' "
        "OR name ILIKE 'Cadastre (API Carto%' OR name ILIKE 'CoSIA%') AND last_sync_at IS NOT NULL"
    )).mappings().all()
    plus_recentes = [r["name"] for r in rows if r["last_sync_at"] and r["last_sync_at"] > servi]
    return {"changees": bool(plus_recentes),
            "detail": (", ".join(plus_recentes) or "aucune entrée plus récente que le run servi")}


def note_version(db: Session, candidat: str) -> dict:
    """Lot 3.3 — LA NOTE DE VERSION du candidat, produite PAR LE REGISTRE : réservoirs et
    millésimes utilisés (photo du run F2.2 si enregistrée, sinon l'état courant de data_sources),
    chiffres recalculés (portée `run` du registre), écart de classement vs servi (distribution
    des tiers, golden_ops). Servie au bouton Basculer (lot 5) : on ne bascule qu'après lecture."""
    from . import registre, runs
    from .flux import snapshot_source_millesimes

    try:
        photo = db.execute(text(
            "SELECT source_millesimes FROM p_score_v2_runs WHERE run_id = :r"), {"r": candidat}).scalar()
    except Exception:  # noqa: BLE001 — colonne absente (photo F2.2 non posée sur cette base)
        db.rollback()
        photo = None
    if photo:
        import json as _json
        reservoirs = photo if isinstance(photo, list) else _json.loads(photo)
    else:
        reservoirs = snapshot_source_millesimes(db)
    chiffres_run = sorted(cid for cid, c in registre.CHIFFRES.items() if c.portee == "run")
    ecart = None
    try:
        from .golden_ops import comparer
        ecart = comparer(candidat, runs.current())
    except Exception:  # noqa: BLE001 — pas de comparaison possible (run partiel) : la note le dit
        ecart = None
    return {"candidat": candidat, "servi": runs.current(),
            "reservoirs": reservoirs, "chiffres_recalcules": chiffres_run,
            "ecart_classement": ecart,
            "note": "Basculer déplace scoring + résiduel + mvt + division en un seul écrit "
                    "(manifeste) ; Revenir restaure le manifeste précédent entier."}
