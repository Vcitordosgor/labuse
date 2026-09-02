"""ADMIN-1 (AD10) — carnet des CONTACTS NOMMÉS de communes (au-delà du standard officiel).

Table `commune_contacts` : des contacts ajoutés à la main (nom, rôle, tél, mail, note), rattachés à
une commune par son code INSEE. NON cloisonnée par compte : ces contacts sont un savoir partagé de
LABUSE, visibles sur la fiche commune de TOUS les comptes (AD10.2), édités par l'admin uniquement.

Le module ne fait que du CRUD idempotent ; les gardes (exiger_admin en écriture, lecture ouverte)
vivent dans les endpoints (api/ops.py).
"""
from __future__ import annotations

from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS commune_contacts (
    id serial PRIMARY KEY,
    insee varchar(5) NOT NULL,
    commune_nom text,
    nom text NOT NULL,
    role text,
    telephone text,
    email text,
    note text,
    cree_le timestamptz NOT NULL DEFAULT now(),
    cree_par text
)
"""


def ensure_table(engine_or_conn) -> None:
    """DDL idempotente (CREATE IF NOT EXISTS + index). Accepte un Engine (begin) ou une connexion/session."""
    idx = "CREATE INDEX IF NOT EXISTS ix_commune_contacts_insee ON commune_contacts (insee)"
    exec_ = getattr(engine_or_conn, "execute", None)
    if exec_ is not None and not hasattr(engine_or_conn, "begin"):
        # connexion ou session déjà ouverte
        engine_or_conn.execute(text(DDL))
        engine_or_conn.execute(text(idx))
        return
    with engine_or_conn.begin() as c:
        c.execute(text(DDL))
        c.execute(text(idx))


def _row(r) -> dict:
    d = dict(r)
    d["cree_le"] = d["cree_le"].isoformat() if d.get("cree_le") else None
    return d


def lister(db, insee: str) -> list[dict]:
    """Contacts nommés d'une commune (code INSEE), les plus récents d'abord."""
    rows = db.execute(text(
        "SELECT id, insee, commune_nom, nom, role, telephone, email, note, cree_le, cree_par"
        " FROM commune_contacts WHERE insee = :i ORDER BY cree_le DESC, id DESC"),
        {"i": insee}).mappings().all()
    return [_row(r) for r in rows]


def lister_tous(db) -> list[dict]:
    """Tous les contacts groupés par commune (INSEE), communes AVEC contacts triées par nom."""
    rows = db.execute(text(
        "SELECT id, insee, commune_nom, nom, role, telephone, email, note, cree_le, cree_par"
        " FROM commune_contacts ORDER BY commune_nom NULLS LAST, insee, cree_le DESC")).mappings().all()
    groupes: dict[str, dict] = {}
    for r in rows:
        d = _row(r)
        g = groupes.setdefault(d["insee"], {"insee": d["insee"], "commune_nom": d["commune_nom"], "contacts": []})
        if d["commune_nom"] and not g["commune_nom"]:
            g["commune_nom"] = d["commune_nom"]
        g["contacts"].append(d)
    return list(groupes.values())


def creer(db, *, insee: str, commune_nom: str | None, nom: str, role: str | None = None,
          telephone: str | None = None, email: str | None = None, note: str | None = None,
          cree_par: str | None = None) -> dict:
    r = db.execute(text(
        "INSERT INTO commune_contacts (insee, commune_nom, nom, role, telephone, email, note, cree_par)"
        " VALUES (:insee, :commune_nom, :nom, :role, :telephone, :email, :note, :cree_par)"
        " RETURNING id, insee, commune_nom, nom, role, telephone, email, note, cree_le, cree_par"),
        {"insee": insee, "commune_nom": commune_nom, "nom": nom, "role": role,
         "telephone": telephone, "email": email, "note": note, "cree_par": cree_par}).mappings().one()
    return _row(r)


def modifier(db, contact_id: int, **champs) -> dict | None:
    """Met à jour les champs fournis (nom/role/telephone/email/note/commune_nom). Renvoie la ligne ou None."""
    autorises = {"nom", "role", "telephone", "email", "note", "commune_nom"}
    maj = {k: v for k, v in champs.items() if k in autorises}
    if not maj:
        r = db.execute(text(
            "SELECT id, insee, commune_nom, nom, role, telephone, email, note, cree_le, cree_par"
            " FROM commune_contacts WHERE id = :i"), {"i": contact_id}).mappings().first()
        return _row(r) if r else None
    set_sql = ", ".join(f"{k} = :{k}" for k in maj)
    r = db.execute(text(
        f"UPDATE commune_contacts SET {set_sql} WHERE id = :i"
        " RETURNING id, insee, commune_nom, nom, role, telephone, email, note, cree_le, cree_par"),
        {**maj, "i": contact_id}).mappings().first()
    return _row(r) if r else None


def supprimer(db, contact_id: int) -> bool:
    n = db.execute(text("DELETE FROM commune_contacts WHERE id = :i"), {"i": contact_id}).rowcount
    return bool(n)
