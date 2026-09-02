"""Pré-vol M7 · P4 — observabilité d'exploitation : l'état des CRONS exposé par l'API.

`GET /healthz/crons` : pour chaque tâche planifiée (deploy/cron.d/*), l'âge du dernier passage
réussi, lu dans les traces DÉJÀ écrites (ingestion_runs, data_sources.last_sync_at) — zéro table
nouvelle. Un cron silencieusement mort se voit en un GET (le jour J, le monitoring VPS s'y branche).

Public (comme /healthz) : n'expose AUCUNE donnée métier — uniquement des âges et des statuts.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
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
    # (cron « catnat » retiré avec le spin-off « Vues » — M12 Lot C-bis : c'était le signal
    #  CATNAT du moteur de segments.)
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
    retards = None
    dpe_reveil = None
    try:
        from ..ingestion import fraicheur
        sources = fraicheur.etat_sources(db)
        # M84 — le VERDICT de fraîcheur (statut dérivé de 2× cadence) : les seules sources réellement
        # en retard. Champ FORT et visible (la sentinelle VPS et la page Sources le lisent) — mais SÉPARÉ
        # du bit `ok` : `ok` = santé PROCESS/cron (un job mort, capté par la liveness `crons` ci-dessus,
        # dégrade). Un retard amont CHRONIQUE (ex. DPE ~3 sem. côté ADEME) ne doit pas faire sonner en
        # boucle la sonde uptime — il a sa propre sentinelle dédiée (`labuse check-fraicheur`, code 1).
        # Cadences libres/annuelles jamais comptées (anti-faux-positif : DVF 226 j, Sudocuh 591 j…).
        retards = [{"source": e["source"], "delta_jours": e["delta_donnee_jours"],
                    "seuil_jours": e["seuil_jours"], "derniere_donnee": e["derniere_donnee"]}
                   for e in sources if e.get("statut") == "en_retard"]
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
    # PREMIER EURO · E5 — sentinelle webhook Stripe : l'âge du dernier événement reçu.
    # « jamais_vu » avant la mise en live (normal) ; en live, un silence prolongé = panne
    # de webhook → la sentinelle VPS lit ce champ.
    stripe_webhook = None
    try:
        with db.begin_nested():
            dernier = db.execute(text(
                "SELECT max(at) FROM evenements_compte WHERE type LIKE 'stripe_%'")).scalar()
        stripe_webhook = {"dernier": str(dernier) if dernier else None,
                          "statut": "ok" if dernier else "jamais_vu"}
    except Exception:  # noqa: BLE001
        pass
    return {"ok": not degrade, "crons": out, "sources": sources, "retards": retards,
            "dpe_reveil": dpe_reveil, "radar": radar, "stripe_webhook": stripe_webhook}


# ═══════════════════════════ SECTEUR-1 (S2) — Contacts institutionnels (admin) ═══════════════════════════

@router.get("/admin/contacts-institutionnels")
def admin_contacts(request: Request):
    """Les contacts institutionnels réunis et triables : les 24 mairies (la MÊME donnée que la fiche
    commune, `mairie_de`), les EPCI (config BANATIC), la DEAL et l'ADIL. Pas de notes de relation — le
    CRM de Vic reste dans Notion."""
    from ..api.auth import exiger_admin
    from ..config import load_yaml_config
    from ..db import session_scope
    from sqlalchemy import text
    exiger_admin(request)
    with session_scope() as db:
        mairies = [dict(r) for r in db.execute(text(
            "SELECT insee, commune, nom, adresse, code_postal, telephone, email, site_officiel, url_annuaire, "
            "       source, date_import "
            "FROM mairies ORDER BY commune")).mappings()]
        # ADMIN-1 (AD10) — contacts nommés ajoutés, groupés par INSEE, pour enrichir les cartes commune.
        from .. import commune_contacts as _cc
        contacts_par_insee: dict[str, list] = {}
        for g in _cc.lister_tous(db):
            contacts_par_insee[g["insee"]] = g["contacts"]
    for m in mairies:
        m["date_import"] = m["date_import"].isoformat() if m.get("date_import") else None
        m["contacts"] = contacts_par_insee.get(m.get("insee"), [])   # AD10 — contacts nommés de la commune
    try:
        epci_cfg = load_yaml_config("epci_974")["epci"]
        epci = [{"code": k, "nom": v.get("nom"), "communes": v.get("communes", [])} for k, v in epci_cfg.items()]
    except Exception:  # noqa: BLE001
        epci = []
    # DEAL / ADIL — contacts institutionnels publics de La Réunion (une institution unique chacun).
    autres = [
        {"type": "DEAL", "nom": "DEAL La Réunion (Direction de l'Environnement, de l'Aménagement et du Logement)",
         "adresse": "2 rue Juliette Dodu, 97706 Saint-Denis Cedex 9", "telephone": "02 62 40 26 00",
         "site": "https://www.reunion.developpement-durable.gouv.fr"},
        {"type": "ADIL", "nom": "ADIL de La Réunion (Agence Départementale d'Information sur le Logement)",
         "adresse": "12 rue Colbert, 97400 Saint-Denis", "telephone": "02 62 41 14 24",
         "site": "https://www.adil974.re"},
    ]
    return {"mairies": mairies, "epci": epci, "autres": autres,
            "note": "Même donnée que la fiche commune, réunie et triable. Pas de notes de relation "
                    "(le CRM reste dans Notion)."}


# ═══════════════════════════ ADMIN-1 (AD10) — carnet des contacts nommés de communes ═══════════════════════════

class _ContactIn(BaseModel):
    insee: str = Field(min_length=1, max_length=5)
    commune_nom: str | None = Field(default=None, max_length=120)
    nom: str = Field(min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    telephone: str | None = Field(default=None, max_length=60)
    email: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=1000)


class _ContactPatch(BaseModel):
    commune_nom: str | None = Field(default=None, max_length=120)
    nom: str | None = Field(default=None, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    telephone: str | None = Field(default=None, max_length=60)
    email: str | None = Field(default=None, max_length=160)
    note: str | None = Field(default=None, max_length=1000)


@router.get("/communes/{insee}/contacts")
def commune_contacts_publics(insee: str):
    """LECTURE OUVERTE (tout utilisateur connecté) : les contacts nommés d'une commune, servis à la
    carte « Mairie » de la fiche commune (tous comptes). Contacts partagés, non cloisonnés."""
    from .. import commune_contacts as cc
    from ..db import session_scope
    with session_scope() as db:
        return {"contacts": cc.lister(db, insee)}


@router.get("/admin/commune-contacts")
def admin_commune_contacts(request: Request):
    """ADMIN — tous les contacts nommés, groupés par commune (page Contacts)."""
    from ..api.auth import exiger_admin
    from .. import commune_contacts as cc
    from ..db import session_scope
    exiger_admin(request)
    with session_scope() as db:
        return {"communes": cc.lister_tous(db)}


@router.post("/admin/commune-contacts")
def admin_commune_contact_creer(body: _ContactIn, request: Request):
    """ADMIN — ajoute un contact nommé à une commune (depuis la page Contacts OU la fiche commune)."""
    from ..api.auth import exiger_admin
    from .. import commune_contacts as cc
    from ..db import session_scope
    info = exiger_admin(request)
    with session_scope() as db:
        out = cc.creer(db, insee=body.insee, commune_nom=body.commune_nom, nom=body.nom,
                       role=body.role, telephone=body.telephone, email=body.email, note=body.note,
                       cree_par=(info or {}).get("email") or (info or {}).get("role"))
        db.commit()
        return {"ok": True, "contact": out}


@router.patch("/admin/commune-contacts/{contact_id}")
def admin_commune_contact_modifier(contact_id: int, body: _ContactPatch, request: Request):
    """ADMIN — édition en place d'un contact."""
    from fastapi import HTTPException
    from ..api.auth import exiger_admin
    from .. import commune_contacts as cc
    from ..db import session_scope
    exiger_admin(request)
    with session_scope() as db:
        out = cc.modifier(db, contact_id, **body.model_dump(exclude_none=True))
        db.commit()
    if out is None:
        raise HTTPException(404, "Contact introuvable.")
    return {"ok": True, "contact": out}


@router.delete("/admin/commune-contacts/{contact_id}")
def admin_commune_contact_supprimer(contact_id: int, request: Request):
    """ADMIN — supprime un contact."""
    from fastapi import HTTPException
    from ..api.auth import exiger_admin
    from .. import commune_contacts as cc
    from ..db import session_scope
    exiger_admin(request)
    with session_scope() as db:
        ok = cc.supprimer(db, contact_id)
        db.commit()
    if not ok:
        raise HTTPException(404, "Contact introuvable.")
    return {"ok": True}


# ═══════════════════════════ CRON-1 (K7) — la page CRON de l'admin (état des jobs) ═══════════════════════════

@router.get("/admin/cron")
def admin_cron(request: Request):
    """Un rang par job : nom, description, planification (heure Réunion), dernier passage (statut, durée,
    compteurs), état dry-run. Servi par les fichiers d'état de K1 (labuse.jobs.liste)."""
    from ..api.auth import exiger_admin
    from .. import jobs as jobs_mod
    exiger_admin(request)
    return {"jobs": jobs_mod.liste(),
            "note": "Heures affichées en Réunion (UTC+4). « Lancer maintenant » passe par la CLI "
                    "(même verrou flock que le cron). L'état dry-run reste visible tant que Brevo/SMTP "
                    "n'est pas branché."}


@router.get("/admin/cron/{nom}/log")
def admin_cron_log(nom: str, request: Request, lignes: int = 40):
    """Les dernières lignes du log d'un job (consultation depuis l'admin)."""
    from pathlib import Path
    from ..api.auth import exiger_admin
    from ..config import get_settings
    exiger_admin(request)
    p = Path(get_settings().jobs_log_dir) / f"{nom}.log"
    if not p.exists():
        return {"nom": nom, "lignes": [], "note": "aucun log encore (job jamais lancé sur ce serveur)."}
    txt = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"nom": nom, "lignes": txt[-max(1, min(lignes, 200)):]}


@router.post("/admin/cron/{nom}/run")
def admin_cron_run(nom: str, request: Request):
    """« Lancer maintenant » (admin) — passe par la CLI, donc le MÊME verrou : un job en cours refuse le
    double lancement (code 200) et le dit. Ne bloque pas la requête (lancement détaché)."""
    import subprocess
    import sys
    from pathlib import Path
    from ..api.auth import exiger_admin
    from .. import jobs as jobs_mod
    exiger_admin(request)
    if nom not in jobs_mod.JOBS:
        return {"ok": False, "motif": f"job inconnu : {nom}"}
    labuse_bin = str(Path(sys.executable).parent / "labuse")
    bin_cmd = labuse_bin if Path(labuse_bin).exists() else "labuse"
    # détaché : l'admin voit « en cours » à la prochaine lecture d'état ; le verrou gère le double-clic.
    subprocess.Popen([bin_cmd, "jobs", "run", nom],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"ok": True, "nom": nom, "note": "lancé (détaché) — l'état se met à jour à la fin ; "
            "un job déjà en cours refuse ce lancement (verrou)."}
