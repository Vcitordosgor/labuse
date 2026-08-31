"""CRON-1 (K5) — GOLDEN : run candidat AUTOMATIQUE, bascule MANUELLE (décision de Vic).

Après une ingestion réussie qui nourrit le scoring, on calcule un run CANDIDAT (jamais servi) et on le
COMPARE au run servi : parcelles promues, distribution des tiers, dérive en %. La BASCULE — faire du
candidat le run servi — est un geste explicite (`labuse golden promote <run>` ou le bouton admin). Aucune
bascule automatique : le classement servi aux clients ne change que par décision de Vic.

`config/served_run.txt` est le POINT DE VÉRITÉ UNIQUE du run servi (backend + bundle front le lisent).
`promote` le réécrit ; `candidat` ne fait que LIRE — il ne touche jamais le servi (ni le golden).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from .db import session_scope
from .scoring.score_v_constants import Q_A_RUN_LABEL

_SERVED_FILE = Path(__file__).resolve().parents[2] / "config" / "served_run.txt"


def _distribution(db, run_id: str) -> dict:
    rows = db.execute(text(
        "SELECT tier, count(*) n FROM parcel_p_score_v2 WHERE run_id = :r GROUP BY tier"),
        {"r": run_id}).mappings().all()
    d = {r["tier"]: int(r["n"]) for r in rows}
    d["_total"] = sum(v for k, v in d.items() if not k.startswith("_"))
    d["_promues"] = d.get("brulante", 0) + d.get("chaude", 0)
    return d


def comparer(candidat_run: str, servi_run: str | None = None) -> dict:
    """Comparaison LECTURE SEULE candidat vs servi (jamais de bascule). Rend promues, tiers, dérive %."""
    servi = servi_run or Q_A_RUN_LABEL
    with session_scope() as db:
        connus = {r[0] for r in db.execute(text("SELECT DISTINCT run_id FROM parcel_p_score_v2")).all()}
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
    if recent == Q_A_RUN_LABEL:
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
    if not recent or recent == Q_A_RUN_LABEL:
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
    """LA BASCULE — réécrit config/served_run.txt (le run servi). Valide que le run existe avant. Geste
    manuel : aucune bascule automatique n'appelle cette fonction. L'ancien run est retourné (traçabilité)."""
    with session_scope() as db:
        connus = {r[0] for r in db.execute(text("SELECT DISTINCT run_id FROM parcel_p_score_v2")).all()}
    if run not in connus:
        return {"ok": False, "motif": f"run inconnu (aucune parcelle scorée pour {run})"}
    ancien = Q_A_RUN_LABEL
    entete = ("# config/served_run.txt — POINT DE VÉRITÉ UNIQUE du run servi (backend + front).\n"
              "# Bascule via `labuse golden promote <run>` (geste de Vic). Une seule valeur active.\n")
    _SERVED_FILE.write_text(entete + run + "\n", encoding="utf-8")
    return {"ok": True, "ancien": ancien, "nouveau": run}
