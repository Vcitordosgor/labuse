"""Pré-vol M7 · P4 — observabilité d'exploitation : l'état des CRONS exposé par l'API.

`GET /healthz/crons` : pour chaque tâche planifiée (deploy/cron.d/*), l'âge du dernier passage
réussi, lu dans les traces DÉJÀ écrites (ingestion_runs, data_sources.last_sync_at) — zéro table
nouvelle. Un cron silencieusement mort se voit en un GET (le jour J, le monitoring VPS s'y branche).

Public (comme /healthz) : n'expose AUCUNE donnée métier — uniquement des âges et des statuts.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.ops")
router = APIRouter(tags=["ops"])

# Tâche cron → (source de trace, motif SQL, périodicité attendue en jours, note)
# Alignées sur deploy/cron.d/* ; « attendu_jours » = période cron + marge (détection de cron mort).
CRONS = {
    "sitadel": {"trace": "ingestion_runs", "motif": "974 (SDES Sitadel3%", "attendu_jours": 35,
                "note": "mensuel (le 5) — permis SDES/Dido"},
    "ban": {"trace": "data_sources", "motif": "Base Adresse Nationale", "attendu_jours": 35,
            "note": "mensuel (le 5) — adresses BAN (trace : data_sources.last_sync_at)"},
    "catnat": {"trace": "data_sources", "motif": "%CatNat%", "attendu_jours": 35,
               "note": "mensuel (le 5) — arrêtés CatNat (trace : data_sources.last_sync_at)"},
    "abuse-scan": {"trace": "aucune", "motif": None, "attendu_jours": 2,
                   "note": "quotidien — pas de trace DB dédiée (log fichier) ; vérifier /var/log/labuse"},
    "backup": {"trace": "aucune", "motif": None, "attendu_jours": 2,
               "note": "quotidien — vérifier LABUSE_BACKUP_DIR (backup_postgres.sh) côté système"},
    # J+2 (post-M7) — la chaîne de fraîcheur
    "bodacc": {"trace": "data_sources", "motif": "BODACC%", "attendu_jours": 2,
               "note": "quotidien — procédures collectives (SIREN propriétaires)"},
    "dvf": {"trace": "data_sources", "motif": "DVF / valeurs foncières", "attendu_jours": 10,
            "note": "hebdo (détection Last-Modified ; livraison Etalab semestrielle)"},
    "dpe": {"trace": "data_sources", "motif": "DPE ADEME%", "attendu_jours": 10,
            "note": "hebdo — flux ADEME continu (upsert numero_dpe)"},
}


def get_db():
    from .app import get_db as _g
    yield from _g()


@router.get("/healthz/crons")
def healthz_crons(db: Session = Depends(get_db)) -> dict:
    """État de chaque cron : dernier passage OK (ingestion_runs) et verdict frais/en retard/inconnu."""
    out: dict[str, dict] = {}
    degrade = False
    for nom, c in CRONS.items():
        if c["trace"] == "aucune":
            out[nom] = {"statut": "non_trace_db", "note": c["note"]}
            continue
        try:
            if c["trace"] == "data_sources":
                dernier = db.execute(text(
                    "SELECT max(last_sync_at) FROM data_sources WHERE name ILIKE :m"),
                    {"m": c["motif"]}).scalar()
            else:
                row = db.execute(text(
                    """SELECT max(finished_at) AS dernier FROM ingestion_runs
                       WHERE commune LIKE :m AND status = 'ok'"""),
                    {"m": c["motif"]}).mappings().first()
                dernier = row["dernier"] if row else None
            if dernier is None:
                out[nom] = {"statut": "jamais_vu", "note": c["note"]}
                degrade = True
                continue
            age_j = db.execute(text("SELECT extract(epoch FROM now() - CAST(:d AS timestamptz)) / 86400"),
                               {"d": str(dernier)}).scalar()
            en_retard = age_j > c["attendu_jours"]
            out[nom] = {"statut": "en_retard" if en_retard else "ok",
                        "dernier_ok": str(dernier), "age_jours": round(float(age_j), 1),
                        "attendu_jours": c["attendu_jours"], "note": c["note"]}
            degrade = degrade or en_retard
        except Exception as exc:  # noqa: BLE001 — l'observabilité ne casse jamais
            out[nom] = {"statut": "erreur_lecture", "detail": type(exc).__name__}
            degrade = True
    # J+2 : la matrice de fraîcheur des SOURCES (dates de données, pas seulement les crons)
    #        + le compteur de réveil du badge DPE en réserve (visible dès qu'il bouge).
    sources = None
    dpe_reveil = None
    try:
        from ..ingestion import fraicheur
        sources = fraicheur.etat_sources(db)
        import json as _json
        with db.begin_nested():   # table absente → savepoint, jamais une TX avortée
            raw = db.execute(text(
                "SELECT valeur FROM fraicheur_etat WHERE cle = 'dpe:compteur_reveil'")).scalar()
        dpe_reveil = _json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001 — l'observabilité ne casse jamais
        pass
    # B3 (BLOC B) : le RADAR — sources amont ayant PUBLIÉ depuis la dernière sonde. Une
    # source réglementaire qui bouge est VISIBLE ici (et la sentinelle du VPS lit ce champ).
    # Le radar signale, l'humain décide : jamais d'auto-ingestion des couches cascade.
    radar = None
    try:
        from ..radar import etat_radar
        etats = etat_radar(db)
        if etats:
            bouge = [{"source": e["source_name"], "mode": e["mode"],
                      "publication": e["valeur"], "detecte_le": str(e["dernier_changement"])}
                     for e in etats if e["statut"] == "nouvelle_publication"]
            radar = {"sondees": len(etats), "publications_detectees": bouge,
                     "derniere_passe": max((str(e["derniere_verif"]) for e in etats
                                            if e["derniere_verif"]), default=None)}
    except Exception:  # noqa: BLE001 — l'observabilité ne casse jamais
        pass
    return {"ok": not degrade, "crons": out, "sources": sources, "dpe_reveil": dpe_reveil,
            "radar": radar}
