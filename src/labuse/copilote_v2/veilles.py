"""M78 · Phase 4 — VEILLE : « Préviens-moi de tout nouveau permis à Saint-Paul ».

Une veille = un trigger PERSISTÉ (compte, type, périmètre, critères, fréquence). L'évaluation tourne
à CHAQUE ingestion de données — ZÉRO appel modèle : du SQL et des notifications. Le modèle ne sert
qu'à la CRÉATION (parser la demande). En production, le cron J+1 (Train 8) appelle `evaluer_toutes`.

M85 — LE CANAL EXISTE désormais : une veille qui se déclenche écrit dans le CENTRE unifié
(`event_log` via `events.creer_notification`), visible à la cloche + repris par le digest. La table
`veille_notifications` (store parallèle M78) a été SUPPRIMÉE — un seul centre, plus de doublon.
Nomenclature M85 : VEILLES = ces déclencheurs ; NOTIFICATIONS = ce qu'ils produisent (event_log) ;
SECTEURS = les zones géographiques DVF (M54, sans rapport).
"""
from __future__ import annotations

import hashlib
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# FIX-VEILLE (option A) — `TYPES` réduit à ce qui S'ÉVALUE. Les 3 types jamais branchés (ventes,
# procedure_plu, bodacc) sont RETIRÉS : ils n'avaient pas d'évaluateur, et le seul chemin qui les
# proposait (preparer_veille) était mort. Ne reste que `permis`, dont la source (Sitadel) est branchée.
TYPES = {
    "permis": "permis de construire (Sitadel)",
}
EVALUABLES = {"permis"}   # invariant : TYPES.keys() == EVALUABLES (plus de type non évaluable)

# FIX-VEILLE (V3/V4) — colonnes `criteres`/`frequence` EN EXTINCTION : jamais lues, plus jamais
# écrites (le seul écrivain, l'ancien preparer_veille/_executer_veille, est retiré). On ne les
# DÉCLARE plus (déploiement neuf sans elles) ; on ne les DROP PAS sur l'existant (pas de migration
# destructive) — elles resteront inertes dans les tables déjà créées, ignorées par tout le code.
# RADAR P4 — le type « radar » vit dans CETTE table (branché sur le mécanisme de veille), mais il est
# évalué par le DIGEST Radar (pige/digests.py), PAS par `evaluer_toutes` (qui ne traite que EVALUABLES)
# → aucun double-envoi. Ses critères riches vivent dans la colonne `criteria` (jsonb).
TYPE_RADAR = "radar"

DDL = """
CREATE TABLE IF NOT EXISTS veilles (
  id serial PRIMARY KEY, compte_id int, type varchar(24), commune varchar(64),
  actif boolean DEFAULT true, last_evaluated_at timestamptz, created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_veilles_compte ON veilles (compte_id, actif);
ALTER TABLE veilles ADD COLUMN IF NOT EXISTS criteria jsonb DEFAULT '{}'::jsonb;
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL))
        # FIX-VEILLE (option A) — DÉSACTIVE les veilles FANTÔMES (type non évaluable, ex. la `bodacc`
        # id=2 du bucket démo) : jamais évaluées, elles ne doivent plus apparaître comme actives.
        # Idempotent et NON destructif (actif=false réversible ; aucune ligne supprimée ; les 7 veilles
        # `permis` — type évaluable — ne sont pas touchées).
        # RADAR P4 : `radar` est un type LÉGITIME géré hors evaluer_toutes → épargné du désactivage.
        c.execute(text("UPDATE veilles SET actif = false WHERE actif AND type <> :radar "
                       "AND NOT (type = ANY(:t))"),
                  {"t": list(EVALUABLES), "radar": TYPE_RADAR})
        # RADAR-VEILLE-1 (V3) — retrait des filtres d'événement. Une veille annonces notifie désormais sur
        # TOUT événement d'un bien correspondant (le filtre `evenements` n'a jamais été appliqué par
        # `pige.veille.matche` — il était inerte). On retire la clé des critères stockés → aucune veille
        # orpheline : celles qui n'avaient qu'un type coché passent à « tous les événements ». Idempotent
        # (ne touche que les radar portant encore la clé) et non destructif (le reste des critères intact).
        c.execute(text("UPDATE veilles SET criteria = criteria - 'evenements' "
                       "WHERE type = :radar AND criteria ? 'evenements'"), {"radar": TYPE_RADAR})


def creer(db: Session, *, compte_id: int | None, type_: str, commune: str | None) -> dict:
    """Insère une veille — UNIQUEMENT d'un type ÉVALUABLE. FIX-VEILLE : la garde est ICI (plus dans un
    appelant qui pouvait l'ignorer) → il est désormais IMPOSSIBLE de poser une veille qui ne
    s'évaluerait jamais. `criteres`/`frequence` ne sont plus écrites (colonnes en extinction, V3/V4)."""
    if type_ not in EVALUABLES:
        raise ValueError(f"type de veille non évaluable (aucune source branchée) : {type_!r}")
    db.execute(text(DDL))
    vid = db.execute(text(
        "INSERT INTO veilles (compte_id, type, commune) VALUES (:c, :t, :co) RETURNING id"),
        {"c": compte_id, "t": type_, "co": commune}).scalar()
    return {"id": vid, "type": type_, "commune": commune, "evaluable": True}


def lister(db: Session, compte_id: int | None) -> list[dict]:
    db.execute(text(DDL))
    rows = db.execute(text(
        "SELECT v.id, v.type, v.commune, v.actif, v.created_at "
        "FROM veilles v WHERE v.compte_id IS NOT DISTINCT FROM :c AND v.actif ORDER BY v.created_at DESC"),
        {"c": compte_id}).mappings().all()
    return [dict(r) for r in rows]


def supprimer(db: Session, compte_id: int | None, veille_id: int) -> bool:
    n = db.execute(text("UPDATE veilles SET actif=false WHERE id=:i AND compte_id IS NOT DISTINCT FROM :c"),
                   {"i": veille_id, "c": compte_id}).rowcount
    return bool(n)


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
    """Évalue UNE veille depuis son watermark (last_evaluated_at) : nouvelles données → 1 notification
    dans le CENTRE (event_log). ZÉRO modèle. REGROUPEMENT : N faits = 1 notif à N entrées (jamais N
    notifs). DÉDUP par contenu (rejeu du MÊME lot = pas de doublon ; un lot NOUVEAU passe). Retourne le
    nombre de faits. Idempotent via watermark + dédup."""
    ev = _EVALUATEURS.get(veille["type"])
    since = veille.get("last_evaluated_at")
    if since is None:
        since = db.execute(text("SELECT now() - interval '90 days'")).scalar()   # 1re éval : fenêtre récente
    hits = ev(db, veille["commune"], since) if (ev and veille.get("commune")) else []
    if hits:
        from ..api.events import creer_notification
        commune = veille["commune"]
        if len(hits) == 1:
            titre, detail = hits[0]["titre"], hits[0]["detail"]
        else:                                             # REGROUPEMENT
            titre = f"{len(hits)} nouveaux permis à {commune}"
            detail = "\n".join(f"· {h['detail']} (réf. {h['ref']})" for h in hits[:20])
            if len(hits) > 20:
                detail += f"\n… et {len(hits) - 20} autres."
        refs = "|".join(sorted(str(h.get("ref")) for h in hits))
        dedup = f"veille:{veille['id']}:" + hashlib.md5(refs.encode()).hexdigest()[:16]
        creer_notification(db, kind="veille", compte_id=veille.get("compte_id"),
                           titre=titre, detail=detail, source="Copilote · veille",
                           lien=f"/copilote?veille={veille['id']}", dedup=dedup)
    db.execute(text("UPDATE veilles SET last_evaluated_at=now() WHERE id=:i"), {"i": veille["id"]})
    return len(hits)


def evaluer_toutes(db: Session) -> dict:
    """Point d'entrée du CRON J+1 (Train 8) : évalue toutes les veilles actives évaluables. À câbler
    sur le pipeline d'ingestion (labuse detect-events / cron) — livré ici, prêt à être déclenché."""
    veilles = db.execute(text(
        "SELECT id, compte_id, type, commune, last_evaluated_at FROM veilles WHERE actif AND type = ANY(:t)"),
        {"t": list(EVALUABLES)}).mappings().all()
    total = sum(evaluer(db, dict(v)) for v in veilles)
    return {"veilles_evaluees": len(veilles), "notifications_creees": total}
