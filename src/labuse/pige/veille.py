"""RADAR P4 · D1 — VEILLE Radar : critères du client, branchée sur la table `veilles` existante.

Type `radar` (hors `evaluer_toutes` : c'est le DIGEST Radar qui l'évalue, pas la cron générique). Les
critères riches (commune, type, surfaces min, particulier only, événements cochés) vivent dans la
colonne `criteria` (jsonb). Le matching sert l'ALERTE veille (un des deux envois de fin de journée).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..copilote_v2.veilles import TYPE_RADAR

# événements qu'un client peut cocher (miroir des statuts/faits du Radar).
EVENEMENTS_VEILLE = ("nouvelle", "baisse", "retour")

# RADAR-2 (Lot 4) — la colonne `en_pause` (mise en pause d'une alerte) vit dans le DDL de la table
# `veilles` (copilote_v2/veilles.py), appliqué au démarrage de l'app. Pour les chemins qui n'ouvrent pas
# l'app (tests unitaires du digest), on la garantit ICI, une fois par process (IF NOT EXISTS, idempotent).
_COLS_OK = False


def _ensure_pause(db: Session) -> None:
    global _COLS_OK
    if _COLS_OK:
        return
    db.execute(text("ALTER TABLE veilles ADD COLUMN IF NOT EXISTS en_pause boolean DEFAULT false"))
    db.execute(text("ALTER TABLE veilles ADD COLUMN IF NOT EXISTS paused_at timestamptz"))
    _COLS_OK = True


def creer(db: Session, *, compte_id: int | None, criteria: dict) -> int:
    """Crée une veille Radar. `criteria` (modèle VEILLE-2) = {communes?:[...], type_bien?, surface_min?,
    surface_max?, prix_max?, particulier_only?}. Rétro-compat : commune (seule), prix_min. Retourne l'id.
    La colonne `commune` (affichage/index) reflète une commune UNIQUE ; une liste multi laisse la colonne
    vide (la vérité vit dans criteria.communes)."""
    commune = criteria.get("commune")
    communes = criteria.get("communes") or []
    if communes and not commune:
        commune = communes[0] if len(communes) == 1 else None
    return db.execute(text(
        "INSERT INTO veilles (compte_id, type, commune, criteria, actif) "
        "VALUES (:c, :t, :comm, CAST(:cr AS jsonb), true) RETURNING id"),
        {"c": compte_id, "t": TYPE_RADAR, "comm": commune, "cr": json.dumps(criteria)}).scalar()


def lister(db: Session, compte_id: int | None) -> list[dict]:
    _ensure_pause(db)
    rows = db.execute(text(
        "SELECT id, nom, commune, criteria, created_at, en_pause, paused_at FROM veilles "
        "WHERE type = :t AND actif AND compte_id IS NOT DISTINCT FROM :c ORDER BY id DESC"),
        {"t": TYPE_RADAR, "c": compte_id}).mappings().all()
    return [{"id": r["id"], "nom": r["nom"], "commune": r["commune"], "criteria": r["criteria"] or {},
             "created_at": r["created_at"].isoformat() if r["created_at"] else None,
             "en_pause": bool(r["en_pause"]),
             "paused_at": r["paused_at"].isoformat() if r["paused_at"] else None} for r in rows]


def basculer_pause(db: Session, compte_id: int | None, veille_id: int, en_pause: bool) -> bool:
    """RADAR-2 (Lot 4) — met une alerte EN PAUSE (ou la reprend). Distinct du soft-delete (`actif=false`) :
    l'alerte reste listée mais ne notifie plus et ne compte plus de nouveaux tant qu'elle est en pause.
    Même garde IDOR que supprimer/renommer (compte-scopé). Retourne True si une ligne du compte a bougé."""
    _ensure_pause(db)
    n = db.execute(text(
        "UPDATE veilles SET en_pause = :p, paused_at = CASE WHEN :p THEN now() ELSE NULL END "
        "WHERE id = :i AND type = :t AND actif AND compte_id IS NOT DISTINCT FROM :c"),
        {"p": bool(en_pause), "i": veille_id, "t": TYPE_RADAR, "c": compte_id}).rowcount
    return bool(n)


def apercu(db: Session, compte_id: int | None) -> dict:
    """RADAR-2 (Lot 1/4) — les alertes du compte, CHACUNE avec son nombre de « nouveaux depuis hier »
    (biens validés vivants saisis depuis le début d'hier, Réunion, correspondant aux critères). Une alerte
    en PAUSE ne compte aucun nouveau. Réutilise `_biens_du_jour` (contrat partagé avec le digest) et
    `matche` — jamais un second calcul de correspondance. Renvoie aussi le total (badge du hub)."""
    from .digests import _biens_du_jour
    depuis = db.execute(text(
        "SELECT ((now() AT TIME ZONE 'Indian/Reunion')::date - 1) AT TIME ZONE 'Indian/Reunion'")).scalar()
    biens = _biens_du_jour(db, depuis)
    alertes = []
    total = 0
    for v in lister(db, compte_id):
        n = 0 if v["en_pause"] else sum(1 for b in biens if matche(v["criteria"], b))
        if not v["en_pause"]:
            total += n
        alertes.append({**v, "nouveaux": n})
    return {"alertes": alertes, "nouveaux_total": total}


def supprimer(db: Session, compte_id: int | None, veille_id: int) -> bool:
    n = db.execute(text(
        "UPDATE veilles SET actif = false WHERE id = :i AND type = :t "
        "AND compte_id IS NOT DISTINCT FROM :c"),
        {"i": veille_id, "t": TYPE_RADAR, "c": compte_id}).rowcount
    return bool(n)


def renommer(db: Session, compte_id: int | None, veille_id: int, nom: str) -> bool:
    """RETOURS-11 A7 — renomme une veille Radar (compte-scopé, même garde IDOR que supprimer).
    Un nom vide efface l'étiquette (retour au résumé des critères). Retourne True si une ligne du
    compte a bougé."""
    val = (nom or "").strip()[:120] or None
    n = db.execute(text(
        "UPDATE veilles SET nom = :nom WHERE id = :i AND type = :t AND actif "
        "AND compte_id IS NOT DISTINCT FROM :c"),
        {"nom": val, "i": veille_id, "t": TYPE_RADAR, "c": compte_id}).rowcount
    return bool(n)


def _surface_pertinente(bien: dict):
    """La surface qui QUALIFIE le bien : terrain pour un terrain, habitable sinon (à défaut, la seule
    renseignée). Un critère de surface (min/max) s'applique à CELLE-LÀ — pas à un champ absent."""
    faits = bien.get("faits", {})
    if bien.get("type_bien") == "terrain":
        return faits.get("surface_terrain")
    if faits.get("surface_hab") is not None:
        return faits.get("surface_hab")
    return faits.get("surface_terrain")


def matche(criteria: dict, bien: dict) -> bool:
    """Un bien (dict servi par client.lister) correspond-il aux critères d'une veille ? CONSTAT strict :
    un critère absent n'exclut pas ; un critère présent doit être satisfait.

    VEILLE-2 (Lot 2) — critères du modèle : commune(s), type de bien, surface min/max, prix max.
    Rétro-compatible avec les veilles existantes (commune seule, surface_terrain_min/surface_hab_min)."""
    if not criteria:
        return True
    # COMMUNE(S) — nouveau : liste `communes` (le bien doit être dans l'une d'elles) ; rétro-compat :
    # `commune` seule. Une liste vide = aucun filtre commune (comme absente).
    communes = criteria.get("communes") or None
    if communes:
        if bien.get("commune") not in communes:
            return False
    elif criteria.get("commune") and bien.get("commune") != criteria["commune"]:
        return False
    if criteria.get("type_bien") and bien.get("type_bien") != criteria["type_bien"]:
        return False
    faits = bien.get("faits", {})
    # PRIX MAX (et prix_min conservé pour les veilles existantes).
    prix = faits.get("prix")
    pmin, pmax = criteria.get("prix_min"), criteria.get("prix_max")
    if pmin is not None and (prix is None or prix < pmin):
        return False
    if pmax is not None and (prix is None or prix > pmax):
        return False
    # SURFACE MIN/MAX — sur la surface pertinente du bien (terrain/habitable).
    surf = _surface_pertinente(bien)
    smin, smax = criteria.get("surface_min"), criteria.get("surface_max")
    if smin is not None and (surf is None or surf < smin):
        return False
    if smax is not None and (surf is None or surf > smax):
        return False
    # rétro-compat : anciens critères de surface minimale par nature.
    st_min = criteria.get("surface_terrain_min")
    if st_min is not None and (faits.get("surface_terrain") is None or faits["surface_terrain"] < st_min):
        return False
    sh_min = criteria.get("surface_hab_min")
    if sh_min is not None and (faits.get("surface_hab") is None or faits["surface_hab"] < sh_min):
        return False
    if criteria.get("particulier_only") and faits.get("particulier_pro") != "particulier":
        return False
    return True
