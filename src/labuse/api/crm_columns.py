"""M12 LOT H — CRM personnalisable : les colonnes du Kanban de prospection, stockées PAR
TENANT en base (fini le `config/pipeline.yaml` en dur).

Chaque compte possède SES colonnes (`crm_columns`) : il peut les renommer, en ajouter,
en supprimer, les réordonner, et « Réinitialiser » au kanban LABUSE par défaut. Le compte
pilote/legacy (compte_id NULL) a aussi son jeu, semé paresseusement au premier accès.

Ligne rouge produit (la boussole) : **on ne perd JAMAIS une carte**. Une parcelle suivie
qui disparaîtrait en silence est inacceptable. Donc :
  - supprimer une colonne PEUPLÉE exige une colonne cible `move_to` (déplacement obligatoire) ;
  - on REFUSE de supprimer la DERNIÈRE colonne restante ;
  - « Réinitialiser » remappe toutes les cartes sur la 1re colonne par défaut avant de re-semer.

Modèle : les cartes (`pipeline_entries.status`) référencent la colonne par sa `key` STABLE
(ascii) — inchangé. Renommer = changer `label` (la `key` ne bouge pas → aucune carte touchée).
Ajouter = nouvelle `key` dérivée du label (slug + suffixe anti-collision). Supprimer avec
`move_to` = UPDATE des cartes vers la key cible, puis suppression de la ligne colonne.

Cloison multi-tenant : TOUTE requête filtre `compte_id IS NOT DISTINCT FROM :cid` (IDOR-safe).
"""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from .tenant import current_compte

router = APIRouter(prefix="/pipeline/columns", tags=["crm-columns"])


def get_db():
    from .app import get_db as _g
    yield from _g()


DDL = (
    "CREATE TABLE IF NOT EXISTS crm_columns ("
    " id serial PRIMARY KEY,"
    " compte_id integer REFERENCES comptes(id) ON DELETE CASCADE,"
    " key varchar(64) NOT NULL,"
    " label varchar(80) NOT NULL,"
    " tone varchar(16),"
    " position integer NOT NULL,"
    " is_default boolean NOT NULL DEFAULT false,"
    " created_at timestamptz NOT NULL DEFAULT now())"
)


def ensure_tables(engine) -> None:
    """Crée `crm_columns` (idempotent). L'unicité (compte_id, key) empêche deux colonnes de
    même clé pour un compte ; NULLS NOT DISTINCT garde la même garantie pour le bucket pilote."""
    with engine.begin() as c:
        c.execute(text(DDL))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_crm_columns_compte ON crm_columns(compte_id)"))
        has_uq = c.execute(text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_crm_columns_compte_key'")).scalar()
        if not has_uq:
            try:
                c.execute(text("ALTER TABLE crm_columns ADD CONSTRAINT uq_crm_columns_compte_key"
                               " UNIQUE NULLS NOT DISTINCT (compte_id, key)"))
            except Exception:  # noqa: BLE001 — PG < 15
                c.execute(text("ALTER TABLE crm_columns ADD CONSTRAINT uq_crm_columns_compte_key"
                               " UNIQUE (compte_id, key)"))


def _default_columns() -> list[dict]:
    """Le kanban LABUSE par défaut (config/pipeline.yaml) — un bon défaut, on le garde."""
    return list(config.pipeline().get("columns", []))


def _slugify(label: str) -> str:
    """Clé ascii stable dérivée d'un libellé (accents retirés, non-alphanum → _)."""
    norm = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", norm.lower()).strip("_")
    return slug or "colonne"


def _existing_keys(db: Session, cid: int | None) -> set[str]:
    rows = db.execute(text(
        "SELECT key FROM crm_columns WHERE compte_id IS NOT DISTINCT FROM :cid"), {"cid": cid})
    return {r[0] for r in rows}


def _unique_key(db: Session, cid: int | None, base: str) -> str:
    taken = _existing_keys(db, cid)
    if base not in taken:
        return base
    i = 2
    while f"{base}_{i}" in taken:
        i += 1
    return f"{base}_{i}"


def seed_if_empty(db: Session, cid: int | None) -> None:
    """Sème PARESSEUSEMENT le kanban par défaut pour un tenant qui n'a AUCUNE colonne.
    Idempotent : ne fait rien si le compte a déjà des colonnes (personnalisées ou non)."""
    n = db.execute(text(
        "SELECT count(*) FROM crm_columns WHERE compte_id IS NOT DISTINCT FROM :cid"),
        {"cid": cid}).scalar()
    if n:
        return
    for pos, col in enumerate(_default_columns()):
        db.execute(text(
            "INSERT INTO crm_columns (compte_id, key, label, tone, position, is_default)"
            " VALUES (:cid, :k, :l, :t, :p, true)"
            " ON CONFLICT DO NOTHING"),
            {"cid": cid, "k": col["key"], "l": col["label"], "t": col.get("tone"), "p": pos})
    db.flush()


def columns_for(db: Session, cid: int | None) -> list[dict]:
    """Colonnes du tenant (semées si vide), triées par position. Source de vérité du Kanban."""
    seed_if_empty(db, cid)
    rows = db.execute(text(
        "SELECT id, key, label, tone, position, is_default FROM crm_columns"
        " WHERE compte_id IS NOT DISTINCT FROM :cid ORDER BY position, id"), {"cid": cid}).mappings()
    return [dict(r) for r in rows]


def col_keys(db: Session, cid: int | None) -> list[str]:
    """Les `key` valides pour ce tenant — remplace l'ancien _col_keys() basé sur la config."""
    return [c["key"] for c in columns_for(db, cid)]


def default_status(db: Session, cid: int | None) -> str:
    """La colonne d'entrée par défaut = la 1re du tenant (fallback config)."""
    cols = columns_for(db, cid)
    if cols:
        return cols[0]["key"]
    return config.pipeline().get("defaults", {}).get("status", "reperee")


# ─────────────────────────────────── I/O ───────────────────────────────────

class CreateIn(BaseModel):
    label: str
    tone: str | None = None


class RenameIn(BaseModel):
    label: str
    tone: str | None = None       # None = inchangé ; "" = neutre


class ReorderIn(BaseModel):
    order: list[int]              # ids de colonnes DU compte, dans le nouvel ordre


class DeleteIn(BaseModel):
    move_to: int | None = None    # id de la colonne cible (obligatoire si la colonne a des cartes)


def _own_column(db: Session, cid: int | None, col_id: int) -> dict:
    """Récupère UNE colonne du tenant (IDOR : 404 si elle n'est pas à lui)."""
    r = db.execute(text(
        "SELECT id, key, label, tone, position, is_default FROM crm_columns"
        " WHERE id = :id AND compte_id IS NOT DISTINCT FROM :cid"),
        {"id": col_id, "cid": cid}).mappings().first()
    if not r:
        raise HTTPException(404, "Colonne inconnue")
    return dict(r)


def _cards_in(db: Session, cid: int | None, key: str) -> int:
    return db.execute(text(
        "SELECT count(*) FROM pipeline_entries WHERE compte_id IS NOT DISTINCT FROM :cid"
        " AND status = :k"), {"cid": cid, "k": key}).scalar() or 0


@router.get("")
def list_columns(request: Request, db: Session = Depends(get_db)) -> dict:
    """Colonnes du tenant (semées au défaut LABUSE si aucune)."""
    cid = current_compte(request)
    cols = columns_for(db, cid)
    counts = {r[0]: r[1] for r in db.execute(text(
        "SELECT status, count(*) FROM pipeline_entries WHERE compte_id IS NOT DISTINCT FROM :cid"
        " GROUP BY status"), {"cid": cid})}
    for c in cols:
        c["cards"] = counts.get(c["key"], 0)
    return {"columns": cols}


@router.post("")
def create_column(body: CreateIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Ajoute une colonne à la fin du kanban du tenant."""
    cid = current_compte(request)
    seed_if_empty(db, cid)
    label = (body.label or "").strip()
    if not label:
        raise HTTPException(422, "Le nom de colonne est requis.")
    if len(label) > 80:
        raise HTTPException(422, "Nom de colonne trop long (80 caractères max).")
    key = _unique_key(db, cid, _slugify(label))
    maxpos = db.execute(text(
        "SELECT coalesce(max(position), -1) FROM crm_columns WHERE compte_id IS NOT DISTINCT FROM :cid"),
        {"cid": cid}).scalar()
    db.execute(text(
        "INSERT INTO crm_columns (compte_id, key, label, tone, position, is_default)"
        " VALUES (:cid, :k, :l, :t, :p, false)"),
        {"cid": cid, "k": key, "l": label, "t": body.tone or None, "p": (maxpos or -1) + 1})
    db.flush()
    return {"ok": True, "columns": columns_for(db, cid)}


@router.patch("/{col_id}")
def rename_column(col_id: int, body: RenameIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Renomme une colonne (la `key` STABLE ne bouge pas → aucune carte n'est touchée)."""
    cid = current_compte(request)
    _own_column(db, cid, col_id)
    label = (body.label or "").strip()
    if not label:
        raise HTTPException(422, "Le nom de colonne est requis.")
    if len(label) > 80:
        raise HTTPException(422, "Nom de colonne trop long (80 caractères max).")
    if body.tone is not None:
        db.execute(text("UPDATE crm_columns SET label = :l, tone = :t WHERE id = :id"),
                   {"l": label, "t": (body.tone or None), "id": col_id})
    else:
        db.execute(text("UPDATE crm_columns SET label = :l WHERE id = :id"), {"l": label, "id": col_id})
    db.flush()
    return {"ok": True, "columns": columns_for(db, cid)}


@router.post("/reorder")
def reorder_columns(body: ReorderIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Réordonne : `order` = la liste EXACTE des ids du tenant dans le nouvel ordre."""
    cid = current_compte(request)
    owned = {c["id"] for c in columns_for(db, cid)}
    if set(body.order) != owned:
        raise HTTPException(422, "L'ordre doit lister exactement toutes les colonnes du compte.")
    for pos, cidx in enumerate(body.order):
        db.execute(text(
            "UPDATE crm_columns SET position = :p WHERE id = :id AND compte_id IS NOT DISTINCT FROM :cid"),
            {"p": pos, "id": cidx, "cid": cid})
    db.flush()
    return {"ok": True, "columns": columns_for(db, cid)}


@router.delete("/{col_id}")
def delete_column(col_id: int, body: DeleteIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Supprime une colonne. LIGNE ROUGE : on ne perd jamais une carte.
      - la DERNIÈRE colonne ne peut pas être supprimée (422) ;
      - une colonne PEUPLÉE exige `move_to` (colonne cible du tenant, ≠ elle-même) : les cartes
        y sont déplacées AVANT suppression (jamais perdues)."""
    cid = current_compte(request)
    col = _own_column(db, cid, col_id)
    cols = columns_for(db, cid)
    if len(cols) <= 1:
        raise HTTPException(422, "Impossible de supprimer la dernière colonne du kanban.")
    n = _cards_in(db, cid, col["key"])
    if n > 0:
        if body.move_to is None:
            raise HTTPException(
                422, "Cette colonne contient des cartes : indiquez une colonne cible (move_to) "
                     "vers laquelle les déplacer — aucune carte n'est perdue.")
        if body.move_to == col_id:
            raise HTTPException(422, "La colonne cible doit être différente de celle supprimée.")
        target = _own_column(db, cid, body.move_to)   # IDOR : cible aussi au tenant
        db.execute(text(
            "UPDATE pipeline_entries SET status = :dst"
            " WHERE compte_id IS NOT DISTINCT FROM :cid AND status = :src"),
            {"dst": target["key"], "src": col["key"], "cid": cid})
    db.execute(text("DELETE FROM crm_columns WHERE id = :id AND compte_id IS NOT DISTINCT FROM :cid"),
               {"id": col_id, "cid": cid})
    db.flush()
    return {"ok": True, "moved": n, "columns": columns_for(db, cid)}


@router.post("/reset")
def reset_columns(request: Request, db: Session = Depends(get_db)) -> dict:
    """« Réinitialiser » : restaure le kanban LABUSE par défaut. Toutes les cartes du tenant
    sont d'abord remappées sur la 1re colonne par défaut (jamais perdues), puis les colonnes
    custom sont supprimées et les défauts re-semés."""
    cid = current_compte(request)
    first_key = _default_columns()[0]["key"]
    # remap TOUTES les cartes du tenant vers la 1re colonne par défaut (aucune orpheline)
    db.execute(text(
        "UPDATE pipeline_entries SET status = :k WHERE compte_id IS NOT DISTINCT FROM :cid"),
        {"k": first_key, "cid": cid})
    db.execute(text("DELETE FROM crm_columns WHERE compte_id IS NOT DISTINCT FROM :cid"), {"cid": cid})
    db.flush()
    seed_if_empty(db, cid)
    return {"ok": True, "columns": columns_for(db, cid),
            "note": "Toutes les cartes ont été replacées dans la première colonne par défaut."}
