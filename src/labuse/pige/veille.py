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


def creer(db: Session, *, compte_id: int | None, criteria: dict) -> int:
    """Crée une veille Radar. `criteria` = {commune?, type_bien?, surface_terrain_min?, surface_hab_min?,
    particulier_only?, evenements:[nouvelle|baisse|retour]}. Retourne l'id."""
    commune = criteria.get("commune")
    return db.execute(text(
        "INSERT INTO veilles (compte_id, type, commune, criteria, actif) "
        "VALUES (:c, :t, :comm, CAST(:cr AS jsonb), true) RETURNING id"),
        {"c": compte_id, "t": TYPE_RADAR, "comm": commune, "cr": json.dumps(criteria)}).scalar()


def lister(db: Session, compte_id: int | None) -> list[dict]:
    rows = db.execute(text(
        "SELECT id, nom, commune, criteria, created_at FROM veilles "
        "WHERE type = :t AND actif AND compte_id IS NOT DISTINCT FROM :c ORDER BY id DESC"),
        {"t": TYPE_RADAR, "c": compte_id}).mappings().all()
    return [{"id": r["id"], "nom": r["nom"], "commune": r["commune"], "criteria": r["criteria"] or {},
             "created_at": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


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


def matche(criteria: dict, bien: dict) -> bool:
    """Un bien (dict servi par client.lister) correspond-il aux critères d'une veille ? CONSTAT strict :
    un critère absent n'exclut pas ; un critère présent doit être satisfait."""
    if not criteria:
        return True
    if criteria.get("commune") and bien.get("commune") != criteria["commune"]:
        return False
    if criteria.get("type_bien") and bien.get("type_bien") != criteria["type_bien"]:
        return False
    faits = bien.get("faits", {})
    # RADAR-CATÉGORIE (T4) — le prix rejoint les critères de veille (demandé par le mandat ; les
    # veilles existantes sans prix restent valides, un critère absent n'exclut pas).
    prix = faits.get("prix")
    pmin, pmax = criteria.get("prix_min"), criteria.get("prix_max")
    if pmin is not None and (prix is None or prix < pmin):
        return False
    if pmax is not None and (prix is None or prix > pmax):
        return False
    st_min = criteria.get("surface_terrain_min")
    if st_min is not None and (faits.get("surface_terrain") is None or faits["surface_terrain"] < st_min):
        return False
    sh_min = criteria.get("surface_hab_min")
    if sh_min is not None and (faits.get("surface_hab") is None or faits["surface_hab"] < sh_min):
        return False
    if criteria.get("particulier_only") and faits.get("particulier_pro") != "particulier":
        return False
    return True
