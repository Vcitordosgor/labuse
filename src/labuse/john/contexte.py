"""JOHN-TAYLOR-1 — LES LECTURES de John (contexte autorisé, 100 % lecture seule).

« John lit tout. » Chaque fonction ici lit l'exploitation RÉELLE (jobs, incidents, sources et leur
fraîcheur, runs servis et calculés, contrôles et verrous, sauvegardes et copie externe, Radar, journaux
d'erreur, carnet, rapports du dépôt) et rend un dict JSON-sérialisable. AUCUNE écriture, aucun SQL libre
venu du modèle : le modèle choisit un OUTIL (cf. `outils.py`), jamais une requête.

Chaque gatherer est best-effort : une lecture qui rate rend `{"indisponible": "..."}` au lieu de lever —
une panne de lecture ne doit jamais faire taire John sur le reste. Rien de sensible (secret, donnée
client nominative) n'entre ici : ce sont des faits d'exploitation.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text


def _indispo(exc: Exception) -> dict:
    return {"indisponible": f"lecture impossible ({type(exc).__name__})"}


# ════════════════════════════════ JOBS ════════════════════════════════
def jobs_etat(db) -> dict:
    """Tous les jobs du registre avec leur dernier passage, et l'état calculé (en retard / bloqué).
    Résume aussi les jobs EN ÉCHEC / EN RETARD (ceux qui attendent peut-être un geste)."""
    try:
        from .. import jobs as _jobs
        liste = _jobs.liste()
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    jobs = []
    en_echec, en_retard = [], []
    for j in liste:
        d = j.get("dernier") or {}
        statut = d.get("statut")
        item = {"nom": j["nom"], "libelle": j.get("libelle") or j["titre"], "famille": j.get("famille"),
                "cadence": j["cadence"], "heure_reunion": j.get("heure_reunion"),
                "lancable": j.get("lancable"), "gel": j.get("gel"),
                "dernier_statut": statut, "dernier_fin": d.get("fin"), "erreur": d.get("erreur"),
                "bloque": j.get("bloque"), "perime": j.get("perime"),
                "prochaine_reunion": j.get("prochaine_reunion")}
        jobs.append(item)
        if statut in ("echec", "timeout") or j.get("bloque"):
            en_echec.append(j["nom"])
        elif j.get("perime"):
            en_retard.append(j["nom"])
    return {"n": len(jobs), "en_echec": en_echec, "en_retard": en_retard, "jobs": jobs}


def job_detail(db, nom: str, n: int = 8) -> dict:
    """L'historique récent d'UN job (pour une enquête ciblée)."""
    try:
        from .. import jobs_journal
        return {"nom": nom, "historique": jobs_journal.historique(db, nom, n)}
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)


# ════════════════════════════════ INCIDENTS ════════════════════════════════
def incidents(db) -> dict:
    """Les incidents ouverts (+ ceux rentrés dans l'ordre depuis 26 h)."""
    try:
        from .. import ops_alertes
        return {"ouverts": ops_alertes.incidents_ouverts(db),
                "resolus_recents": ops_alertes.incidents_resolus_depuis(db, 26)}
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)


# ════════════════════════════════ SOURCES & FRAÎCHEUR ════════════════════════════════
def sources(db) -> dict:
    """Toutes les sources : catégorie, statut, millésime servi, fraîcheur, veille (dernier vu amont),
    et la CLASSE A/B (qui décide si l'injection est automatique ou attend Vic)."""
    try:
        from ..autonomie import classe_source
        rows = db.execute(text(
            "SELECT d.id, d.name, d.category, d.status, d.source_millesime, d.source_horizon_at,"
            "       d.source_cadence, COALESCE(d.affichage_desactive, false) AS off,"
            "       v.dernier_statut, v.dernier_vu, v.dernier_passage_at, v.echecs_consecutifs,"
            "       v.actif AS veille_active"
            " FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id"
            " ORDER BY d.name")).mappings().all()
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    out, nouvelles, en_panne = [], [], []
    for r in rows:
        cl, raison = classe_source(r["name"], r["category"])
        item = {"id": r["id"], "nom": r["name"], "categorie": r["category"], "statut": r["status"],
                "classe": cl, "classe_raison": raison, "millesime_servi": r["source_millesime"],
                "horizon": r["source_horizon_at"].isoformat() if r["source_horizon_at"] else None,
                "cadence": r["source_cadence"], "desactivee": r["off"],
                "veille_statut": r["dernier_statut"], "amont_vu": r["dernier_vu"],
                "veille_passage": r["dernier_passage_at"].isoformat() if r["dernier_passage_at"] else None,
                "echecs_consecutifs": r["echecs_consecutifs"]}
        out.append(item)
        if r["dernier_statut"] == "nouvelle_version":
            nouvelles.append({"nom": r["name"], "classe": cl, "amont_vu": r["dernier_vu"]})
        if r["dernier_statut"] in ("injoignable", "illisible"):
            en_panne.append({"nom": r["name"], "statut": r["dernier_statut"]})
    return {"n": len(out), "nouvelles_versions": nouvelles, "veille_en_panne": en_panne, "sources": out}


# ════════════════════════════════ RUNS (servi / calculé) ════════════════════════════════
def runs_etat(db) -> dict:
    """Le run SERVI (ce que voient les clients), le précédent, les trois pointeurs et leur cohérence,
    et le candidat le plus récent (calculé, pas encore promu) s'il existe."""
    try:
        from .. import runs
        base = {"servi": runs.current(), "precedent": runs.precedent(),
                "pointeurs": runs.pointeurs()}
        try:
            base["promu_at"] = runs.promu_at().isoformat() if runs.promu_at() else None
        except Exception:  # noqa: BLE001
            base["promu_at"] = None
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    # candidat : le run le plus récent présent en base mais PAS servi (best-effort).
    try:
        cand = db.execute(text(
            "SELECT DISTINCT run_label FROM dryrun_cascade_results "
            "WHERE run_label <> :servi ORDER BY run_label DESC LIMIT 1"),
            {"servi": base["servi"]}).scalar()
        base["candidat"] = cand
    except Exception:  # noqa: BLE001
        base["candidat"] = None
    return base


# ════════════════════════════════ CONTRÔLES & VERROUS ════════════════════════════════
def controles(db) -> dict:
    """Le dernier passage de la suite de cohérence (le banc) : écarts, faux-client, lecteurs en erreur,
    écarts tolérés. C'est le juge « aucun chiffre faux chez le client »."""
    try:
        r = db.execute(text(
            "SELECT ts, mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur "
            "FROM coherence_runs ORDER BY ts DESC LIMIT 1")).mappings().first()
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    if not r:
        return {"coherence": None, "note": "aucun passage de cohérence enregistré"}
    return {"coherence": {
        "quand": r["ts"].isoformat(), "mode": r["mode"], "n_ecarts": r["n_ecarts"],
        "faux_client": r["faux_client"], "incoherent": r["incoherent"],
        "tolerable": r["tolerable"], "erreurs_lecteur": r["erreurs_lecteur"],
        "vert": (r["faux_client"] or 0) == 0 and (r["erreurs_lecteur"] or 0) == 0}}


# ════════════════════════════════ SAUVEGARDES & COPIE EXTERNE ════════════════════════════════
def sauvegardes(db) -> dict:
    """Le dernier dump (nom, taille, âge) et la copie hors-VPS (marqueur `.copie-externe.json`)."""
    from ..config import get_settings
    import time as _time
    s = get_settings()
    out: dict = {}
    try:
        bdir = Path(s.backup_dir)
        dumps = sorted(bdir.glob("*.dump"), key=lambda p: p.stat().st_mtime, reverse=True) if bdir.exists() else []
        if dumps:
            p = dumps[0]
            st = p.stat()
            age_h = (_time.time() - st.st_mtime) / 3600.0
            out["dernier_dump"] = {"fichier": p.name, "mo": round(st.st_size / 1e6, 1),
                                   "age_h": round(age_h, 1), "age_j": round(age_h / 24.0, 1),
                                   "n_dumps": len(dumps)}
        else:
            out["dernier_dump"] = {"indisponible": f"aucun .dump dans {s.backup_dir}"}
        marq = bdir / ".copie-externe.json"
        if marq.exists():
            m = json.loads(marq.read_text(encoding="utf-8"))
            out["copie_externe"] = {"quand": m.get("when"), "restore_test": m.get("restore_test")}
        else:
            out["copie_externe"] = {"indisponible": "aucun marqueur de copie externe"}
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    return out


# ════════════════════════════════ RADAR ════════════════════════════════
def radar(db) -> dict:
    """La dernière passe Radar (pige) : quand, combien de pages. « Muet » si trop vieux."""
    try:
        from ..config import get_settings
        row = db.execute(text(
            "SELECT max(created_at) AS dernier FROM pige_passes")).mappings().first()
        dernier = row["dernier"] if row else None
        pages = db.execute(text(
            "SELECT COALESCE(sum(n_pages), 0) FROM pige_passes "
            "WHERE created_at >= now() - interval '24 hours'")).scalar()
        seuil = get_settings().radar_muet_seuil_h
        age_h = None
        if dernier is not None:
            age_h = db.execute(text(
                "SELECT EXTRACT(EPOCH FROM (now() - :d)) / 3600.0"), {"d": dernier}).scalar()
        return {"derniere_passe": dernier.isoformat() if dernier else None,
                "age_h": round(float(age_h), 1) if age_h is not None else None,
                "age_j": round(float(age_h) / 24.0, 1) if age_h is not None else None,
                "pages_24h": int(pages or 0),
                "muet": age_h is not None and float(age_h) > seuil}
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)


# ════════════════════════════════ JOURNAUX D'ERREUR ════════════════════════════════
def journaux(db, n: int = 12) -> dict:
    """Les derniers passages de jobs EN ÉCHEC (avec leur message d'erreur) + l'état du fournisseur IA."""
    try:
        rows = db.execute(text(
            "SELECT nom, debut, statut, erreur FROM job_runs "
            "WHERE statut IN ('echec','timeout') ORDER BY debut DESC LIMIT :n"),
            {"n": max(1, min(n, 50))}).mappings().all()
        echecs = [{"job": r["nom"], "quand": r["debut"].isoformat(), "statut": r["statut"],
                   "erreur": (r["erreur"] or "")[:400]} for r in rows]
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    ia = {}
    try:
        from ..ai import core as _core
        ia = {"provider": _core.provider_status().get("provider"), "derniere_erreur": _core.last_error()}
    except Exception:  # noqa: BLE001
        ia = {}
    return {"jobs_en_echec": echecs, "ia": ia}


# ════════════════════════════════ RAPPORTS DU DÉPÔT ════════════════════════════════
def rapports(db=None) -> dict:
    """Les comptes-rendus des mandats récents (docs/audit-2026-11/*/COMPTE-RENDU.md) : titre + 1ʳᵉ ligne.
    Lecture seule du dépôt, bornée (le modèle demande ensuite un rapport précis s'il en a besoin)."""
    racine = Path(__file__).resolve().parents[3]
    out = []
    try:
        base = racine / "docs" / "audit-2026-11"
        if base.exists():
            for d in sorted(base.iterdir()):
                cr = d / "COMPTE-RENDU.md"
                if cr.exists():
                    tete = ""
                    for ligne in cr.read_text(encoding="utf-8", errors="replace").splitlines():
                        if ligne.strip().startswith("#"):
                            tete = ligne.strip("# ").strip()
                            break
                    out.append({"mandat": d.name, "titre": tete, "chemin": f"docs/audit-2026-11/{d.name}/COMPTE-RENDU.md"})
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
    return {"n": len(out), "rapports": out}


def rapport_texte(db=None, *, chemin: str = "", max_chars: int = 8000) -> dict:
    """Le texte d'UN rapport du dépôt (chemin relatif validé : docs/… ou reports/… en .md seulement)."""
    racine = Path(__file__).resolve().parents[3]
    rel = (chemin or "").lstrip("/")
    if not rel.endswith(".md") or ".." in rel or not (rel.startswith("docs/") or rel.startswith("reports/")):
        return {"refuse": "chemin non autorisé (seuls docs/… et reports/… en .md, sans « .. »)"}
    p = (racine / rel).resolve()
    try:
        if not str(p).startswith(str(racine)) or not p.exists():
            return {"indisponible": f"rapport introuvable : {rel}"}
        txt = p.read_text(encoding="utf-8", errors="replace")
        return {"chemin": rel, "tronque": len(txt) > max_chars, "texte": txt[:max_chars]}
    except Exception as exc:  # noqa: BLE001
        return _indispo(exc)
