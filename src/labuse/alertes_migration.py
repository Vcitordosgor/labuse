"""OUTIL-PERMIS-FIX-12 (LOT 2) — mise à niveau des ANCIENNES alertes de zone déjà enregistrées.

Contre-audit ASTRA-6 (point 1) : 3 111 alertes `permis_in_zone` portent encore « Permis déposé » /
une date de dépôt rejetée, alors que leur dépôt échoue à la validation (fonction unique). La liste les
restitue telles qu'enregistrées (le calcul ne rejoue pas l'historique). On les RÉÉCRIT en base — titre,
détail et `fait_date` alignés sur l'ÉVÉNEMENT réellement daté (dépôt affichable sinon autorisation),
EXACTEMENT comme `alertes.compute_alertes` les produirait aujourd'hui.

Contraintes :
  · on ne touche QUE la table `alertes` (autorisé par Vic, cette table et elle seule) ;
  · on NE RÉÉMET AUCUNE notification : `event_log` n'est jamais écrit (pas de cloche, pas de digest) ;
  · sauvegarde datée + empreinte AVANT ; rollback écrit et testé.

Les fonctions sont GÉNÉRIQUES (la session décide de la base) ; le garde-fou « base = labuse » vit dans
le script d'exécution `scripts/outil_permis_fix8/fix12_migrer_alertes.py`.
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import permis_classe

#: préfixe des tables de sauvegarde (horodatées par le script)
BAK_PREFIX = "alertes_bak_fix12__"


def _exprs() -> tuple[str, str, str]:
    """(label, detail, evenement_date) recalculés — MÊMES expressions que `alertes.compute_alertes`,
    alias `a` (alertes) / `sp` (sitadel_permits)."""
    cond = permis_classe.depot_affichable_cond_sql("sp.")
    ev = permis_classe.evenement_date_sql("sp.")
    label = ("((CASE WHEN " + cond + " THEN 'Permis déposé dans « ' "
             "ELSE 'Permis autorisé dans « ' END) || coalesce(a.payload->>'zone','') || ' »')")
    detail = ("(coalesce(sp.type,'Permis') || ' ' || sp.permit_id || "
              "CASE WHEN " + cond + " THEN ' déposé le ' || sp.date_depot::date::text "
              "WHEN sp.date IS NOT NULL THEN ' autorisé le ' || sp.date::date::text ELSE '' END)")
    return label, detail, ev


def empreinte(session: Session) -> dict:
    """Empreinte des alertes `permis_in_zone` (nombre + md5 ordonné) — à comparer avant/après/rollback."""
    row = session.execute(text(
        "SELECT count(*) AS n, "
        "       md5(coalesce(string_agg(id::text || ':' || coalesce(label,'') || ':' || "
        "            coalesce(payload::text,''), '|' ORDER BY id), '')) AS h "
        "FROM alertes WHERE kind = 'permis_in_zone'")).mappings().first()
    return {"n": int(row["n"]), "md5": row["h"]}


def a_corriger(session: Session) -> dict:
    """Combien d'alertes divergent de l'événement réellement daté, SANS rien écrire (diagnostic)."""
    label, detail, ev = _exprs()
    n = session.execute(text(
        f"SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id = a.source_ref "
        f"WHERE a.kind = 'permis_in_zone' AND ("
        f"  a.label IS DISTINCT FROM {label} "
        f"  OR (a.payload->>'fait_date') IS DISTINCT FROM ({ev})::text "
        f"  OR (a.payload->>'detail') IS DISTINCT FROM {detail})")).scalar()
    deposes_invalides = session.execute(text(
        f"SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id = a.source_ref "
        f"WHERE a.kind='permis_in_zone' AND a.label ILIKE '%déposé%' "
        f"AND NOT ({permis_classe.depot_affichable_cond_sql('sp.')})")).scalar()
    return {"a_corriger": int(n), "deposes_invalides": int(deposes_invalides)}


def sauvegarder(session: Session, *, suffix: str) -> str:
    """Photographie (id, label, payload) des alertes `permis_in_zone` dans une table datée. Renvoie le
    nom de la table de sauvegarde. `suffix` est assaini (une migration = une sauvegarde identifiable)."""
    safe = re.sub(r"[^a-z0-9_]+", "_", suffix.lower()).strip("_") or "run"
    table = BAK_PREFIX + safe
    session.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
    session.execute(text(
        f'CREATE TABLE "{table}" AS '
        f"SELECT id, label, payload FROM alertes WHERE kind = 'permis_in_zone'"))
    return table


def corriger(session: Session) -> int:
    """RÉÉCRIT titre/détail/`fait_date` des alertes `permis_in_zone` divergentes, sur l'événement
    réellement daté. N'écrit QUE dans `alertes` (jamais `event_log` → aucune réémission). Renvoie le
    nombre de lignes corrigées."""
    label, detail, ev = _exprs()
    res = session.execute(text(
        f"UPDATE alertes a SET "
        f"  label = {label}, "
        f"  payload = a.payload || jsonb_build_object('fait_date', ({ev}), 'detail', {detail}) "
        f"FROM sitadel_permits sp "
        f"WHERE a.kind = 'permis_in_zone' AND sp.permit_id = a.source_ref AND ("
        f"  a.label IS DISTINCT FROM {label} "
        f"  OR (a.payload->>'fait_date') IS DISTINCT FROM ({ev})::text "
        f"  OR (a.payload->>'detail') IS DISTINCT FROM {detail})"))
    return res.rowcount or 0


_ANNOT = " · annulé depuis"


def a_annoter(session: Session) -> int:
    """Combien d'alertes `permis_in_zone` concernent un permis AUJOURD'HUI annulé et ne l'indiquent pas
    encore dans leur détail (diagnostic, sans écriture) — OUTIL-PERMIS-FIX-13 (LOT 4)."""
    return int(session.execute(text(
        f"SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id = a.source_ref "
        f"WHERE a.kind='permis_in_zone' AND {permis_classe.annule_sql('sp.')} "
        f"AND (a.payload->>'detail') IS NOT NULL "
        f"AND position(:marq in (a.payload->>'detail')) = 0"), {"marq": _ANNOT}).scalar())


def annoter_annules(session: Session) -> int:
    """Ajoute «  · annulé depuis » au DÉTAIL des alertes `permis_in_zone` dont le permis est AUJOURD'HUI
    annulé (ETAT_DAU=4) et qui ne le disent pas encore. N'écrit QUE dans `alertes` (jamais `event_log` →
    aucune réémission). Idempotent (le marqueur déjà présent n'est pas réappliqué). Renvoie le nb de lignes."""
    res = session.execute(text(
        f"UPDATE alertes a SET payload = jsonb_set(a.payload, '{{detail}}', "
        f"  to_jsonb((a.payload->>'detail') || :marq)) "
        f"FROM sitadel_permits sp "
        f"WHERE a.kind='permis_in_zone' AND sp.permit_id = a.source_ref AND {permis_classe.annule_sql('sp.')} "
        f"AND (a.payload->>'detail') IS NOT NULL "
        f"AND position(:marq in (a.payload->>'detail')) = 0"), {"marq": _ANNOT})
    return res.rowcount or 0


def rollback(session: Session, table: str) -> int:
    """Restaure label/payload depuis une table de sauvegarde. Renvoie le nombre de lignes restaurées."""
    if not re.fullmatch(r"[a-z0-9_]+", table) or not table.startswith(BAK_PREFIX):
        raise ValueError(f"table de sauvegarde invalide : {table!r}")
    res = session.execute(text(
        f"UPDATE alertes a SET label = b.label, payload = b.payload "
        f'FROM "{table}" b WHERE a.id = b.id'))
    return res.rowcount or 0
