"""M78 · Phase 4 — VEILLE : « Préviens-moi de tout nouveau permis à Saint-Paul ».

Une veille = un trigger PERSISTÉ (compte, type, périmètre, critères, fréquence). L'évaluation tourne
à CHAQUE ingestion de données — ZÉRO appel modèle : du SQL et des notifications. Le modèle ne sert
qu'à la CRÉATION (parser la demande). En production, le cron J+1 (Train 8) appelle `evaluer_toutes`.

DÉPENDANCE (la « moitié manquante ») : le CANAL de notification (cloche in-app, digest e-mail) est au
BACKLOG, non livré. Ici on POSE la veille, on ÉVALUE, et on STOCKE la notification dans
`veille_notifications`. Ce qui manque pour qu'elle ATTEIGNE le client est décrit dans RAPPORT_M78.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Types v1 (label client). permis = évaluable maintenant ; les autres : veille POSABLE, requête
# d'évaluation à brancher sur leur source (documenté — honnête, jamais une évaluation qui ment).
TYPES = {
    "permis": "permis de construire (Sitadel)",
    "ventes": "ventes (DVF)",
    "procedure_plu": "procédures PLU (Sudocuh/annuaire)",
    "bodacc": "BODACC sur un propriétaire suivi",
}
_EVALUABLES = {"permis"}   # branchés sur leur source ; le reste attend son mandat de source

DDL = """
CREATE TABLE IF NOT EXISTS veilles (
  id serial PRIMARY KEY, compte_id int, type varchar(24), commune varchar(64),
  criteres jsonb DEFAULT '{}', frequence varchar(12) DEFAULT 'ingestion', actif boolean DEFAULT true,
  last_evaluated_at timestamptz, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS veille_notifications (
  id serial PRIMARY KEY, veille_id int REFERENCES veilles(id) ON DELETE CASCADE, compte_id int,
  titre text, detail text, ref varchar(64), vu boolean DEFAULT false, created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_veilles_compte ON veilles (compte_id, actif);
CREATE INDEX IF NOT EXISTS ix_veille_notif_compte ON veille_notifications (compte_id, vu, created_at DESC);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL))


def creer(db: Session, *, compte_id: int | None, type_: str, commune: str | None,
          criteres: dict | None = None) -> dict:
    db.execute(text(DDL))
    vid = db.execute(text(
        "INSERT INTO veilles (compte_id, type, commune, criteres) VALUES (:c, :t, :co, :cr) RETURNING id"),
        {"c": compte_id, "t": type_, "co": commune, "cr": __import__("json").dumps(criteres or {})}).scalar()
    return {"id": vid, "type": type_, "commune": commune, "evaluable": type_ in _EVALUABLES}


def lister(db: Session, compte_id: int | None) -> list[dict]:
    db.execute(text(DDL))
    rows = db.execute(text(
        "SELECT v.id, v.type, v.commune, v.actif, v.created_at, "
        "  (SELECT count(*) FROM veille_notifications n WHERE n.veille_id=v.id AND NOT n.vu) AS non_vues "
        "FROM veilles v WHERE v.compte_id IS NOT DISTINCT FROM :c AND v.actif ORDER BY v.created_at DESC"),
        {"c": compte_id}).mappings().all()
    return [dict(r) for r in rows]


def supprimer(db: Session, compte_id: int | None, veille_id: int) -> bool:
    n = db.execute(text("UPDATE veilles SET actif=false WHERE id=:i AND compte_id IS NOT DISTINCT FROM :c"),
                   {"i": veille_id, "c": compte_id}).rowcount
    return bool(n)


def compter_actives(db: Session, compte_id: int | None) -> int:
    db.execute(text(DDL))
    return db.execute(text("SELECT count(*) FROM veilles WHERE compte_id IS NOT DISTINCT FROM :c AND actif"),
                      {"c": compte_id}).scalar() or 0


# ───────────────────────── ÉVALUATION (SQL pur, ZÉRO modèle) ─────────────────────────
def _nouveaux_permis(db: Session, commune: str, since) -> list[dict]:
    rows = db.execute(text(
        "SELECT permit_id, date_depot, nature FROM m10_permit_delais "
        "WHERE commune=:c AND date_depot > :s ORDER BY date_depot DESC LIMIT 100"),
        {"c": commune, "s": since}).mappings().all()
    return [{"titre": f"Nouveau permis à {commune}",
             "detail": f"Déposé le {r['date_depot']}" + (f" — {r['nature']}" if r["nature"] else ""),
             "ref": r["permit_id"]} for r in rows]


_EVALUATEURS = {"permis": _nouveaux_permis}   # ventes/procedure_plu/bodacc : source à brancher (BACKLOG)


def evaluer(db: Session, veille: dict) -> int:
    """Évalue UNE veille depuis son watermark (last_evaluated_at) : nouvelles données → notifications.
    ZÉRO modèle. Retourne le nombre de notifications créées. Idempotent via le watermark."""
    ev = _EVALUATEURS.get(veille["type"])
    since = veille.get("last_evaluated_at")
    if since is None:
        since = db.execute(text("SELECT now() - interval '90 days'")).scalar()   # 1re éval : fenêtre récente
    hits = ev(db, veille["commune"], since) if (ev and veille.get("commune")) else []
    for h in hits:
        db.execute(text(
            "INSERT INTO veille_notifications (veille_id, compte_id, titre, detail, ref) "
            "VALUES (:v, :c, :t, :d, :r)"),
            {"v": veille["id"], "c": veille.get("compte_id"), "t": h["titre"], "d": h["detail"], "r": h.get("ref")})
    db.execute(text("UPDATE veilles SET last_evaluated_at=now() WHERE id=:i"), {"i": veille["id"]})
    return len(hits)


def evaluer_toutes(db: Session) -> dict:
    """Point d'entrée du CRON J+1 (Train 8) : évalue toutes les veilles actives évaluables. À câbler
    sur le pipeline d'ingestion (labuse detect-events / cron) — livré ici, prêt à être déclenché."""
    veilles = db.execute(text(
        "SELECT id, compte_id, type, commune, last_evaluated_at FROM veilles WHERE actif AND type = ANY(:t)"),
        {"t": list(_EVALUABLES)}).mappings().all()
    total = sum(evaluer(db, dict(v)) for v in veilles)
    return {"veilles_evaluees": len(veilles), "notifications_creees": total}


def notifications(db: Session, compte_id: int | None, limite: int = 50) -> list[dict]:
    rows = db.execute(text(
        "SELECT id, veille_id, titre, detail, ref, vu, created_at FROM veille_notifications "
        "WHERE compte_id IS NOT DISTINCT FROM :c ORDER BY created_at DESC LIMIT :l"),
        {"c": compte_id, "l": limite}).mappings().all()
    return [dict(r) for r in rows]
