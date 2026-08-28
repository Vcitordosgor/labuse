"""RADAR P4 · D1 — les DEUX digests de fin de journée (heure Réunion), via le template Brevo ID 12.

(a) DIGEST quotidien : à tous les clients actifs, les nouveautés du jour.
(b) ALERTE veille    : aux clients dont les critères Radar correspondent.
Un client concerné reçoit LES DEUX (ils ne se remplacent pas). **Un mail ne part JAMAIS vide** — s'il
n'y a rien, il n'y a pas d'envoi. Contenu : FAITS + lien vers la FICHE LABUSE (jamais un lien portail —
le clic passe par la fiche, mesurable). Échec d'envoi **bruyant** (event_log système, visible dashboard),
jamais silencieux (souvenir RV-013). Chaque envoi émet `pige.digest_envoye` (miroir cloche).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import brevo
from ..api.events import creer_notification
from ..tz import today_reunion
from . import veille as veille_mod
from .tables import EV_DIGEST, journaliser

log = logging.getLogger("labuse.pige.digests")

NIV_LABEL = {"source": "Sourcé", "estime": "Estimé", "absent": "Non rattachée"}


def _clients_actifs(db: Session) -> list[dict]:
    """Comptes ACTIFS avec l'e-mail + prénom du titulaire (patron du digest existant)."""
    return [dict(r) for r in db.execute(text(
        "SELECT c.id AS compte_id, c.prenoms AS prenom, "
        " min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id = c.id "
        "WHERE c.statut = 'actif' GROUP BY c.id, c.prenoms ORDER BY c.id")).mappings()]


def _biens_du_jour(db: Session) -> list[dict]:
    """Biens VALIDÉS saisis AUJOURD'HUI (heure Réunion), statuts vivants. Dicts légers pour le matching
    de veille + la construction des items (faits + rattachement, jamais de contenu d'annonce)."""
    rows = db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.idu, b.rattachement_niveau, "
        "       f.prix, f.surface_hab, f.surface_terrain, f.particulier_pro "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE f.valide_at IS NOT NULL AND b.statut IN ('active','en_vente_longue') "
        "AND b.date_premiere_saisie AT TIME ZONE 'Indian/Reunion' >= (now() AT TIME ZONE 'Indian/Reunion')::date "
        "ORDER BY b.bien_id DESC")).mappings().all()
    return [{"bien_id": r["bien_id"], "commune": r["commune"], "type_bien": r["type_bien"],
             "idu": r["idu"], "rattachement_niveau": r["rattachement_niveau"],
             "faits": {"prix": r["prix"], "surface_hab": float(r["surface_hab"]) if r["surface_hab"] is not None else None,
                       "surface_terrain": float(r["surface_terrain"]) if r["surface_terrain"] is not None else None,
                       "particulier_pro": r["particulier_pro"]}} for r in rows]


def _lien_fiche(base_url: str, b: dict) -> str:
    """Lien vers la FICHE LABUSE (jamais le portail). Rattaché → la fiche parcelle ; sinon l'outil Radar."""
    base = (base_url or "").rstrip("/")
    return f"{base}/socle/#idu={b['idu']}" if b.get("idu") else f"{base}/socle/#m=radar"


def _item(base_url: str, b: dict) -> dict:
    f = b["faits"]
    surface = (f"{f['surface_hab']:.0f} m² hab." if f.get("surface_hab")
               else f"{f['surface_terrain']:.0f} m² terrain" if f.get("surface_terrain") else "—")
    return {"type": (b.get("type_bien") or "bien") + (" (copro)" if b.get("type_bien") == "appartement" else ""),
            "commune": b["commune"],
            "prix": f"{f['prix']:,} €".replace(",", " ") if f.get("prix") is not None else "—",
            "surface": surface,
            "rattachement": NIV_LABEL.get(b["rattachement_niveau"], "—"),
            "url_fiche": _lien_fiche(base_url, b)}


def _envoyer(db: Session, *, compte_id, email: str, prenom: str, type_envoi: str,
             biens: list[dict], base_url: str, dry_run: bool, rapport: list) -> str:
    """UN envoi (digest ou alerte). Jamais vide (garanti par l'appelant). Échec BRUYANT. Retourne
    'simule' | 'envoye' | 'echec'."""
    date_jour = today_reunion().strftime("%d/%m/%Y")
    intro = ("Les nouveautés du Radar aujourd'hui :" if type_envoi == "digest"
             else "Des biens correspondent à vos critères de veille :")
    params = {"prenom": prenom or "", "type_envoi": type_envoi, "date_jour": date_jour,
              "n_items": len(biens), "intro": intro,
              "items": [_item(base_url, b) for b in biens],
              "lien_preferences": f"{(base_url or '').rstrip('/')}/socle/#m=radar"}
    if dry_run:
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": len(biens), "statut": "simule"})
        return "simule"
    res = brevo.envoyer_template(email, "radar", params)
    if res.get("envoye"):
        journaliser(db, EV_DIGEST, f"Radar — {type_envoi} envoyé ({len(biens)})",
                    detail=f"{type_envoi} · {len(biens)} bien(s)", compte_id=compte_id,
                    dedup=f"pige:digest:{compte_id}:{type_envoi}:{today_reunion().isoformat()}")
        rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": len(biens), "statut": "envoye"})
        return "envoye"
    # ÉCHEC BRUYANT (RV-013) — jamais silencieux : log.error + event système visible au dashboard.
    raison = res.get("raison", "inconnue")
    log.error("RADAR digest NON ENVOYÉ (%s) à compte=%s : %s", type_envoi, compte_id, raison)
    try:
        creer_notification(db, kind="systeme", compte_id=None, source="Radar",
                           titre=f"Échec envoi Radar ({type_envoi})",
                           detail=f"Compte {compte_id} : {raison}. Template Brevo 12 monté ?",
                           dedup=f"pige:digest-echec:{type_envoi}:{today_reunion().isoformat()}")
    except Exception:  # noqa: BLE001 — la trace ne doit pas masquer l'échec d'origine
        pass
    rapport.append({"compte_id": compte_id, "type_envoi": type_envoi, "n": len(biens),
                    "statut": "echec", "raison": raison})
    return "echec"


def envoyer(db: Session, *, base_url: str = "", dry_run: bool = False) -> dict:
    """Les DEUX envois de fin de journée. Retourne le rapport (envoyes/echecs/simules par type)."""
    biens = _biens_du_jour(db)
    clients = _clients_actifs(db)
    rapport: list = []
    # (a) DIGEST quotidien — à tous les clients actifs, SI il y a des nouveautés (jamais vide).
    if biens:
        for c in clients:
            if not c.get("email"):
                continue
            _envoyer(db, compte_id=c["compte_id"], email=c["email"], prenom=c.get("prenom"),
                     type_envoi="digest", biens=biens, base_url=base_url, dry_run=dry_run, rapport=rapport)
    # (b) ALERTE veille — à chaque client, les biens du jour qui matchent SES veilles (jamais vide).
    for c in clients:
        if not c.get("email"):
            continue
        crits = [v["criteria"] for v in veille_mod.lister(db, c["compte_id"])]
        if not crits:
            continue
        matches = [b for b in biens if any(veille_mod.matche(cr, b) for cr in crits)]
        if matches:
            _envoyer(db, compte_id=c["compte_id"], email=c["email"], prenom=c.get("prenom"),
                     type_envoi="alerte", biens=matches, base_url=base_url, dry_run=dry_run, rapport=rapport)
    if not dry_run:
        db.commit()
    envoyes = sum(1 for r in rapport if r["statut"] == "envoye")
    echecs = sum(1 for r in rapport if r["statut"] == "echec")
    simules = sum(1 for r in rapport if r["statut"] == "simule")
    return {"n_biens_du_jour": len(biens), "envoyes": envoyes, "echecs": echecs,
            "simules": simules, "dry_run": dry_run, "details": rapport}
