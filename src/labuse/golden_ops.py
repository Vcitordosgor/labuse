"""CRON-1 (K5) — GOLDEN : run candidat AUTOMATIQUE, bascule MANUELLE (décision de Vic).

Après une ingestion réussie qui nourrit le scoring, on calcule un run CANDIDAT (jamais servi) et on le
COMPARE au run servi : parcelles promues, distribution des tiers, dérive en %. La BASCULE — faire du
candidat le run servi — est un geste explicite passant par l'UNIQUE chemin `bascule_flux.basculer()`
(page Circuit / bouton admin, ou l'alias `labuse golden promote <run>`). Aucune bascule automatique :
le classement servi aux clients ne change que par décision de Vic.

BASCULE-1 : le POINT DE VÉRITÉ du run servi est le MANIFESTE `config/served_manifest.json` (lu en
premier par `runs.current()`). `config/served_run.txt` n'en est qu'une VUE DÉRIVÉE ; `promote` l'écrit
mais n'est plus un chemin de bascule (voir `basculer()`). `candidat` ne fait que LIRE — il ne touche
jamais le servi (ni le golden).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from . import runs
from .db import session_scope

_SERVED_FILE = Path(__file__).resolve().parents[2] / "config" / "served_run.txt"


# RETOURS-10 (T2) — la distribution des tiers d'un run est IMMUABLE (un run n'est jamais réécrit sous le
# même id). On la mémoïse : `comparer()` la relit pour le run servi à CHAQUE run comparé (runs_termines en
# compare 4) — sans cache c'était 8 Parallel Seq Scan de 3 M lignes (~2 s chacun) par ouverture de Circuit.
_DISTRIB_CACHE: dict[str, dict] = {}


def _distribution(db, run_id: str) -> dict:
    cached = _DISTRIB_CACHE.get(run_id)
    if cached is not None:
        return cached
    rows = db.execute(text(
        "SELECT tier, count(*) n FROM parcel_p_score_v2 WHERE run_id = :r GROUP BY tier"),
        {"r": run_id}).mappings().all()
    d = {r["tier"]: int(r["n"]) for r in rows}
    d["_total"] = sum(v for k, v in d.items() if not k.startswith("_"))
    d["_promues"] = (d.get("brulante", 0) + d.get("chaude", 0)
                     + d.get("priorite", 0) + d.get("a_suivre", 0))  # PALIERS-1 : deux vocabulaires
    if d["_total"] > 0:  # ne mémoïse qu'un run RÉEL (un run vide/inconnu peut se remplir ensuite)
        _DISTRIB_CACHE[run_id] = d
    return d


def comparer(candidat_run: str, servi_run: str | None = None) -> dict:
    """Comparaison LECTURE SEULE candidat vs servi (jamais de bascule). Rend promues, tiers, dérive %."""
    servi = servi_run or runs.current()
    with session_scope() as db:
        # RETOURS-10 (T2) — les runs connus se lisent du REGISTRE (`p_score_v2_runs`, ~12 lignes), pas d'un
        # `DISTINCT run_id` sur parcel_p_score_v2 (Parallel Seq Scan de 3 M lignes, ~1,9 s mesuré).
        connus = {r[0] for r in db.execute(text("SELECT run_id FROM p_score_v2_runs")).all()}
        if candidat_run not in connus:
            return {"ok": False, "motif": f"run candidat inconnu : {candidat_run}"}
        dc, ds = _distribution(db, candidat_run), _distribution(db, servi)
    promues_c, promues_s = dc["_promues"], ds["_promues"] or 1
    derive_pct = round(100.0 * (promues_c - ds["_promues"]) / promues_s, 1)
    return {"ok": True, "candidat": candidat_run, "servi": servi,
            "promues_candidat": promues_c, "promues_servi": ds["_promues"],
            "derive_promues_pct": derive_pct,
            "tiers_candidat": {k: v for k, v in dc.items() if not k.startswith("_")},
            "tiers_servi": {k: v for k, v in ds.items() if not k.startswith("_")}}


def candidat() -> str:
    """Rapport texte : le run le plus récent (par computed_at) comparé au servi. Informatif — jamais servi."""
    with session_scope() as db:
        recent = db.execute(text(
            "SELECT run_id FROM parcel_p_score_v2 GROUP BY run_id ORDER BY max(computed_at) DESC LIMIT 1")).scalar()
    if not recent:
        return "Aucun run en base."
    if recent == runs.current():
        return (f"Le run le plus récent ({recent}) EST déjà le run servi — pas de candidat à comparer.\n"
                "Un candidat apparaîtra après la prochaine ingestion scoring (sitadel/dvf/cadastre).")
    c = comparer(recent)
    if not c.get("ok"):
        return f"Comparaison impossible : {c.get('motif')}"
    return (f"RUN CANDIDAT : {c['candidat']}   (servi : {c['servi']})\n"
            f"Parcelles promues : {c['promues_candidat']} candidat vs {c['promues_servi']} servi "
            f"→ dérive {c['derive_promues_pct']:+.1f}%\n"
            f"Tiers candidat : {c['tiers_candidat']}\n"
            f"Tiers servi    : {c['tiers_servi']}\n\n"
            f"Bascule (geste de Vic) : labuse golden promote {c['candidat']}")


def rapport_candidat(dry_run: bool = True) -> dict:
    """CRON-2 (K5) — DÉCLENCHÉ EN FIN D'INGESTION SCORING (sitadel) : compare le run candidat (le plus
    récent, non servi) au run servi et envoie un RAPPORT mail (parcelles promues, tiers, dérive %). La
    promotion reste MANUELLE (`golden promote`). Respecte dry-run : sans SMTP, le rapport est logué, rien
    n'est envoyé. Retourne un dict de compteurs pour l'état du job."""
    import logging
    from .config import get_settings
    from .mail import send_email
    with session_scope() as db:
        recent = db.execute(text(
            "SELECT run_id FROM parcel_p_score_v2 GROUP BY run_id ORDER BY max(computed_at) DESC LIMIT 1")).scalar()
    if not recent or recent == runs.current():
        return {"candidat": None, "note": "aucun run candidat (le plus récent est déjà le servi)"}
    c = comparer(recent)
    if not c.get("ok"):
        return {"candidat": recent, "note": c.get("motif")}
    corps = (
        "RUN CANDIDAT — calculé en fin d'ingestion. La bascule reste un geste de Vic (jamais automatique).\n\n"
        f"Candidat : {c['candidat']}   ·   Servi : {c['servi']}\n"
        f"Parcelles promues : {c['promues_candidat']} (candidat) vs {c['promues_servi']} (servi) "
        f"→ dérive {c['derive_promues_pct']:+.1f}%\n"
        f"Tiers candidat : {c['tiers_candidat']}\n"
        f"Tiers servi    : {c['tiers_servi']}\n\n"
        f"Pour servir ce run aux clients : labuse golden promote {c['candidat']}\n\n— LABUSE")
    s = get_settings()
    dest = s.admin_email or s.contact_email
    r = send_email(dest, f"[LABUSE] run candidat {c['candidat']} — comparaison", corps, settings=s) if dest else None
    logging.getLogger("labuse.golden").info("rapport candidat %s — dérive %.1f%% — mail=%s",
                                            c["candidat"], c["derive_promues_pct"],
                                            (r.detail if r else "pas de destinataire"))
    return {"candidat": c["candidat"], "derive_promues_pct": c["derive_promues_pct"],
            "promues_candidat": c["promues_candidat"], "promues_servi": c["promues_servi"],
            "mail": (r.detail if r else "pas de destinataire"),
            "dry_run": bool(r and not r.sent) or dry_run}


def promote(run: str) -> dict:
    """Écrit la VUE DÉRIVÉE `config/served_run.txt`. BASCULE-1 : ce n'est PLUS un chemin de bascule —
    depuis CIRCUIT, `runs.current()` lit le MANIFESTE (`served_manifest.json`) qui fait foi, et
    `served_run.txt` n'en est qu'une vue. Appelée UNIQUEMENT par `bascule_flux.basculer()` (l'unique
    geste), qui écrit ENSUITE le manifeste et relit `runs.current()` pour confirmer. Valide l'existence
    du run avant. L'ancien run est retourné (traçabilité)."""
    with session_scope() as db:
        connus = {r[0] for r in db.execute(text("SELECT DISTINCT run_id FROM parcel_p_score_v2")).all()}
    if run not in connus:
        return {"ok": False, "motif": f"run inconnu (aucune parcelle scorée pour {run})"}
    from . import runs
    ancien = runs.current()
    entete = ("# config/served_run.txt — VUE DÉRIVÉE du run servi (le point de vérité est\n"
              "# config/served_manifest.json). Bascule : `bascule_flux.basculer()` (page Circuit /\n"
              "# bouton admin, ou l'alias `labuse golden promote <run>`). Écrit par la bascule seule.\n")
    _SERVED_FILE.write_text(entete + run + "\n", encoding="utf-8")
    runs.invalidate()   # SUITE-1 S3 — bascule EFFECTIVE À CHAUD : la prochaine lecture relit le pointeur.
    return {"ok": True, "ancien": ancien, "nouveau": run}
