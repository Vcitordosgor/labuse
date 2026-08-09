"""ÉVÉNEMENTS (Vague 3) — le socle de la rétention : M11 alertes · M12 portefeuille vivant ·
M13 digest hebdo · M14 suivi de cible.

`detect_events(run_from, run_to)` diffe deux runs de scoring et émet : bascule de statut,
nouvel événement BODACC, nouveau permis proche d'une parcelle suivie (pipeline + watched).
Cronable via `labuse detect-events`. Sans second run réel, un run de DÉMONSTRATION étiqueté
(`q_v2_demo`, colonne demo=true partout) fait vivre le système — bascule réelle documentée.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/events", tags=["events"])
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)


def get_db():
    from .app import get_db as _g
    yield from _g()


# compte_id : cloison multi-tenant (NULL = bucket pilote/démo hérité). La colonne est posée
# ici pour les installs neufs ; sur une base existante, api/tenant.ensure_scoping l'ajoute
# (idempotent) + la FK ON DELETE CASCADE + l'unique (compte_id, idu) de watched_parcels.
DDL = """
CREATE TABLE IF NOT EXISTS event_log (
  id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
  kind varchar(24) NOT NULL,            -- bascule | bodacc | permis | veille
  idu varchar(14),
  titre varchar(200) NOT NULL,
  detail text,
  run_from varchar(40), run_to varchar(40),
  demo boolean DEFAULT false,           -- événement de DÉMONSTRATION (étiqueté à l'écran)
  lu boolean DEFAULT false,             -- lu PARTAGÉ : ne vaut que pour les events du compte (perso + pilote NULL)
  compte_id integer                     -- cloison : NULL = feed pilote/démo (marché, données publiques)
);
-- M-V V2 : suivi « vu » PAR COMPTE des events de MARCHÉ (compte_id NULL, ligne partagée). Un
-- compte réel ne peut PAS écrire `lu` sur une ligne partagée sans l'écraser pour tous → il pose
-- ici une ligne (compte_id, event_id). PK composite, idempotente. FK event → CASCADE (les vus
-- d'un event supprimé partent avec). La FK compte_id → comptes(id) est posée par tenant.ensure_scoping
-- (comptes n'existe pas encore quand ce DDL tourne au boot).
CREATE TABLE IF NOT EXISTS event_seen (
  compte_id integer NOT NULL,
  event_id  integer NOT NULL REFERENCES event_log(id) ON DELETE CASCADE,
  seen_at   timestamptz DEFAULT now(),
  PRIMARY KEY (compte_id, event_id)
);
CREATE TABLE IF NOT EXISTS watched_parcels (
  idu varchar(14) NOT NULL, created_at timestamptz DEFAULT now(),
  compte_id integer                     -- cloison : le suivi de cible est privé au compte
);
CREATE TABLE IF NOT EXISTS saved_searches (
  id serial PRIMARY KEY, nom varchar(80) NOT NULL, hash text NOT NULL,
  created_at timestamptz DEFAULT now()
);
-- M21-B3 : préférences de notification par compte (désinscription obligatoire du digest e-mail).
CREATE TABLE IF NOT EXISTS veille_reprise (
  id serial PRIMARY KEY,
  compte_id integer,
  idu varchar(14) NOT NULL,
  mois integer NOT NULL,                 -- 3 | 6 | 12 | 24 (réalerte M23-C)
  echeance date NOT NULL,
  tier_archivage varchar(24),            -- état SERVI au moment de l'archivage (diff à l'échéance)
  event_date_archivage date,             -- dernier événement daté connu à l'archivage
  created_at timestamptz DEFAULT now(),
  traite_at timestamptz                  -- NULL = en attente d'échéance
);
CREATE TABLE IF NOT EXISTS notif_prefs (
  compte_id integer PRIMARY KEY,
  unsubscribed boolean DEFAULT false,   -- opt-out du digest e-mail (jamais d'envoi sans arrêt possible)
  token varchar(48),                    -- jeton de désinscription en 1 clic (lien + List-Unsubscribe)
  digest_freq varchar(12) DEFAULT 'hebdo',   -- hebdo | quotidien (réglable)
  last_digest_at timestamptz
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


# ───────────────────────── détection (le job cronable) ─────────────────────────

def detect_events(db: Session, run_from: str, run_to: str, demo: bool = False) -> dict:
    """Diffe deux runs → événements. Idempotent par (kind, idu, run_from, run_to)."""
    inserted = {"bascule": 0, "bodacc": 0, "permis": 0}

    # 1. bascules de statut (jointure sur les parcelles présentes dans les DEUX runs)
    rows = db.execute(text("""
        SELECT p.idu, a.matrice_statut AS de, b.matrice_statut AS vers
        FROM dryrun_parcel_evaluations a
        JOIN dryrun_parcel_evaluations b ON b.parcel_id = a.parcel_id AND b.run_label = :to
        JOIN parcels p ON p.id = a.parcel_id
        WHERE a.run_label = :from AND a.matrice_statut <> b.matrice_statut"""),
        {"from": run_from, "to": run_to}).mappings().all()
    for r in rows:
        up = r["vers"] == "chaude" or (r["vers"] == "a_surveiller" and r["de"] in ("a_creuser", "ecartee"))
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo)
            SELECT 'bascule', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bascule' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"{'▲' if up else '▼'} {r['idu'][8:]} : {r['de']} → {r['vers']}",
             "detail": f"Bascule de statut au recalcul ({run_from} → {run_to}).",
             "from": run_from, "to": run_to, "demo": demo}).rowcount
        inserted["bascule"] += n

    # 2. nouveaux événements BODACC (rouge présent dans run_to, absent de run_from)
    rows = db.execute(text("""
        SELECT DISTINCT p.idu FROM dryrun_cascade_results b
        JOIN parcels p ON p.id = b.parcel_id
        WHERE b.run_label = :to AND b.evenement = 'rouge'
          AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results a
                          WHERE a.run_label = :from AND a.parcel_id = b.parcel_id AND a.evenement = 'rouge')"""),
        {"from": run_from, "to": run_to}).mappings().all()
    for r in rows:
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo)
            SELECT 'bodacc', CAST(:idu AS varchar), CAST(:titre AS varchar), 'Procédure collective ouverte (BODACC) détectée au recalcul.', CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bodacc' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"● BODACC : procédure ouverte sur {r['idu'][8:]}",
             "from": run_from, "to": run_to, "demo": demo}).rowcount
        inserted["bodacc"] += n

    # 2 bis. VEILLES : une bascule vers un statut « montant » qui MATCHE une recherche sauvegardée
    # → notification nominative (M11 : « une recherche filtrée nommée = une veille »).
    _veilles_match(db, run_to, demo)

    # 3. nouveau permis proche (≤ 300 m) d'une parcelle SUIVIE (pipeline + watched) — permis
    # récents relativement à la fin des données Sitadel (12 derniers mois de données).
    # CLOISON : l'événement appartient au COMPTE qui suit la parcelle (une même parcelle suivie
    # par A et B produit un événement pour chacun, jamais partagé).
    rows = db.execute(text("""
        WITH suivies AS (
          SELECT p.id, p.idu, p.geom_2975, pe.compte_id
          FROM parcels p JOIN pipeline_entries pe ON pe.parcel_id = p.id
          UNION
          SELECT p.id, p.idu, p.geom_2975, w.compte_id
          FROM parcels p JOIN watched_parcels w ON w.idu = p.idu
        )
        SELECT s.idu, s.compte_id, sp.permit_id, sp.type, sp.date::date::text AS date
        FROM suivies s
        JOIN sitadel_permits sp ON sp.geom IS NOT NULL
          AND ST_DWithin(s.geom_2975, ST_Transform(sp.geom, 2975), 300)
          AND sp.date >= (SELECT max(date) FROM sitadel_permits) - interval '12 months'"""),
    ).mappings().all()
    for r in rows:
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo, compte_id)
            SELECT 'permis', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean), :cid
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='permis' AND idu=:idu AND detail=:detail
                              AND compte_id IS NOT DISTINCT FROM :cid)"""),
            {"idu": r["idu"], "titre": f"Permis {r['type']} à ≤ 300 m de {r['idu'][8:]}",
             "detail": f"{r['permit_id']} du {r['date']} — le secteur bouge autour d'une parcelle suivie.",
             "from": run_from, "to": run_to, "demo": demo, "cid": r["compte_id"]}).rowcount
        inserted["permis"] += n
    db.flush()
    # M23-C : reprises de veille ÉCHUES → le MÊME canal que les veilles (event_log kind='veille',
    # cron detect-events existant) — jamais un second circuit de notification.
    inserted["reprises"] = traiter_reprises(db)
    return inserted


def traiter_reprises(db: Session) -> int:
    """M23-C — échéances de reprise atteintes : une entrée event_log kind='veille' avec la
    MENTION DE CE QUI A CHANGÉ depuis l'archivage (tier servi, nouveaux événements datés).
    Idempotent : traite_at marque la reprise consommée."""
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    dus = db.execute(text(
        "SELECT id, compte_id, idu, mois, echeance, tier_archivage, event_date_archivage "
        "FROM veille_reprise WHERE traite_at IS NULL AND echeance <= CURRENT_DATE")).mappings().all()
    n = 0
    for r in dus:
        cur = db.execute(text(
            "SELECT tier, event_date FROM parcel_p_score_v2 "
            "WHERE run_id = :run AND parcelle_id = :idu"),
            {"run": Q_A_RUN_LABEL, "idu": r["idu"]}).mappings().first()
        tier_now = cur["tier"] if cur else None
        ev_now = cur["event_date"] if cur else None
        changes = []
        if tier_now and r["tier_archivage"] and tier_now != r["tier_archivage"]:
            changes.append(f"tier {r['tier_archivage']} → {tier_now}")
        elif tier_now:
            changes.append(f"tier inchangé ({tier_now})")
        if ev_now and (r["event_date_archivage"] is None or ev_now > r["event_date_archivage"]):
            changes.append(f"nouvel événement daté ({ev_now})")
        else:
            changes.append("aucun nouvel événement")
        detail = (f"Réalerte à {r['mois']} mois après archivage — depuis : "
                  + " · ".join(changes) + ".")
        db.execute(text(
            "INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, compte_id) "
            "SELECT 'veille', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), 'archivage', 'reprise', :cid "
            "WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='veille' AND idu=:idu "
            "  AND titre=:titre AND compte_id IS NOT DISTINCT FROM :cid)"),
            {"idu": r["idu"], "titre": f"⏰ Reprise de veille : {r['idu']}",
             "detail": detail, "cid": r["compte_id"]})
        db.execute(text("UPDATE veille_reprise SET traite_at = now() WHERE id = :i"), {"i": r["id"]})
        n += 1
    db.flush()
    return n


def _parse_hash_filters(h: str) -> dict:
    """Filtres d'une veille depuis son hash (#f=1&st=…&vm=1…) — même sérialisation que le front."""
    from urllib.parse import parse_qs
    q = parse_qs(h.lstrip("#"))
    g = lambda k: q.get(k, [None])[0]  # noqa: E731
    # M17-B : honorer AUSSI `tv` (tiers du front, filtersToHash) et `cs` (commune) — jusqu'ici la
    # veille lisait `st`/rien pour la commune, donc sur-alertait sur ces deux dimensions (silencieux).
    st = (g("st") or "").split(",") if g("st") else []
    tv = (g("tv") or "").split(",") if g("tv") else []
    return {"st": list(dict.fromkeys([*st, *tv])),
            "cm": (g("cs") or "").split(",") if g("cs") else [],
            "ev": g("ev") == "1", "q": int(g("q")) if g("q") else None,
            "smin": int(g("smin")) if g("smin") else None, "smax": int(g("smax")) if g("smax") else None,
            "sdp": int(g("sdp")) if g("sdp") else None, "fl": (g("fl") or "").split(",") if g("fl") else []}


def _veilles_match(db: Session, run_to: str, demo: bool) -> int:
    # Batch : on parcourt TOUTES les veilles (tous comptes), et chaque événement produit est
    # attribué au COMPTE propriétaire de la veille (v["compte_id"]) — jamais partagé.
    veilles = db.execute(text("SELECT id, nom, hash, compte_id FROM saved_searches")).mappings().all()
    if not veilles:
        return 0
    # bascules « montantes » de CE diff (déjà en event_log, kind=bascule, run_to)
    rows = db.execute(text("""
        SELECT e.idu, p.commune, p.surface_m2, d.matrice_statut, d.q_score, r.sdp_residuelle_m2,
               EXISTS (SELECT 1 FROM dryrun_cascade_results cr WHERE cr.run_label = :to
                       AND cr.parcel_id = p.id AND cr.evenement = 'rouge') AS a_evenement
        FROM event_log e
        JOIN parcels p ON p.idu = e.idu
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :to
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE e.kind = 'bascule' AND e.run_to = :to AND e.titre LIKE '▲%'"""),
        {"to": run_to}).mappings().all()
    n = 0
    for v in veilles:
        f = _parse_hash_filters(v["hash"])
        for r in rows:
            if f["st"] and r["matrice_statut"] not in f["st"]:
                continue
            if f["cm"] and r["commune"] not in f["cm"]:   # M17-B : commune honorée
                continue
            if f["ev"] and not r["a_evenement"]:
                continue
            if f["q"] is not None and (r["q_score"] or 0) < f["q"]:
                continue
            if f["smin"] is not None and (r["surface_m2"] or 0) < f["smin"]:
                continue
            if f["smax"] is not None and (r["surface_m2"] or 0) > f["smax"]:
                continue
            if f["sdp"] is not None and (r["sdp_residuelle_m2"] or 0) < f["sdp"]:
                continue
            n += db.execute(text("""
                INSERT INTO event_log (kind, idu, titre, detail, run_to, demo, compte_id)
                SELECT 'veille', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text),
                       CAST(:to AS varchar), CAST(:demo AS boolean), :cid
                WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='veille' AND idu=:idu AND titre=:titre
                                  AND compte_id IS NOT DISTINCT FROM :cid)"""),
                {"idu": r["idu"], "titre": f"🔭 Veille « {v['nom']} » : {r['idu'][8:]} correspond",
                 "detail": f"Bascule vers {r['matrice_statut']} qui matche votre veille (run {run_to}).",
                 "to": run_to, "demo": demo, "cid": v["compte_id"]}).rowcount
    return n


def seed_demo(db: Session) -> dict:
    """Run de DÉMONSTRATION `q_v2_demo` : copie de q_v2 sur 8 parcelles avec statut modifié,
    ÉTIQUETÉ démo — pour voir le système vivre avant le prochain run réel de scoring."""
    db.execute(text("DELETE FROM event_log WHERE demo"))  # démo REJOUABLE : la cloche se rallume
    db.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = 'q_v2_demo'"))
    db.execute(text("""
        INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score,
          opportunity_score, opportunity_base, status, q_score, a_score, a_completude, matrice_statut)
        SELECT 'q_v2_demo', parcel_id, completeness_score, opportunity_score, opportunity_base,
               status, q_score, a_score, a_completude,
               CASE WHEN rn <= 5 THEN 'chaude' ELSE 'a_surveiller' END
        FROM (
          SELECT d.*, row_number() OVER (ORDER BY d.q_score DESC) AS rn
          FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
          WHERE d.run_label = :run
            AND d.matrice_statut = CASE WHEN true THEN 'a_surveiller' ELSE '' END
          LIMIT 5
        ) monte
    """), {"run": RUN})
    db.execute(text("""
        INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score,
          opportunity_score, opportunity_base, status, q_score, a_score, a_completude, matrice_statut)
        SELECT 'q_v2_demo', parcel_id, completeness_score, opportunity_score, opportunity_base,
               status, q_score, a_score, a_completude, 'a_surveiller'
        FROM (
          SELECT d.* FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
          WHERE d.run_label = :run AND d.matrice_statut = 'chaude'
          ORDER BY d.q_score ASC LIMIT 3
        ) descend
    """), {"run": RUN})
    out = detect_events(db, RUN, "q_v2_demo", demo=True)
    db.flush()
    return {"run_demo": "q_v2_demo", "events": out,
            "note": "Événements de DÉMONSTRATION (étiquetés). La bascule réelle = prochain run de scoring "
                    "(labuse dryrun-evaluate --label <run> puis labuse detect-events q_v2 <run>)."}


# ───────────────────────── API ─────────────────────────

# M-T V2 — BROADCAST BORNÉ DU MARCHÉ. Les événements de MARCHÉ (compte_id NULL, données publiques :
# bascule de statut, procédure BODACC, match de marché) deviennent visibles de TOUS les abonnés en
# LECTURE. Les kinds PERSONNELS (permis suivis, veilles, reprises de veille) restent cloisonnés
# STRICT (jamais partagés — cf. cloison M-K). Le broadcast ne touche QUE ces trois kinds.
_MARKET_KINDS = ("bascule", "bodacc", "match")
_PERSO_KINDS = ("permis", "veille")


def _visible(alias: str = "e") -> str:
    """Fragment SQL de visibilité d'un event_log : SES lignes (cloison) ∪ le marché public
    (compte_id NULL sur un kind de marché). `:cid` et `:market` doivent être liés par l'appelant."""
    p = f"{alias}." if alias else ""
    return (f"({p}compte_id IS NOT DISTINCT FROM :cid "
            f"OR ({p}compte_id IS NULL AND {p}kind = ANY(:market)))")


def _seen(alias: str = "e") -> str:
    """Fragment SQL : l'event est-il LU pour le compte courant ? (M-V V2)
    - event du compte (perso, ou pilote sur ses lignes NULL) → colonne partagée `lu`.
    - event de MARCHÉ vu par un compte réel → présence dans `event_seen` (jamais la colonne
      partagée, qui appartient au bucket pilote). `:cid` lié par l'appelant."""
    p = f"{alias}." if alias else ""
    return (f"(CASE WHEN {p}compte_id IS NOT DISTINCT FROM :cid THEN {p}lu "
            f"ELSE EXISTS (SELECT 1 FROM event_seen s WHERE s.event_id = {p}id AND s.compte_id = :cid) END)")


@router.get("")
def list_events(request: Request, unread_only: bool = False, limit: int = 100, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)
    mk = list(_MARKET_KINDS)
    rows = db.execute(text(f"""
        SELECT e.id, e.ts::date::text AS date, e.kind, e.idu, e.titre, e.detail, e.demo,
               {_seen('e')} AS lu,
               d.matrice_statut AS statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE {_visible('e')} {f"AND NOT {_seen('e')}" if unread_only else ""}
        ORDER BY e.ts DESC, e.id DESC LIMIT :lim"""),
        {"lim": limit, "run": RUN, "cid": cid, "market": mk}).mappings().all()
    unread = db.execute(text(f"SELECT count(*) FROM event_log e WHERE {_visible('e')} AND NOT {_seen('e')}"),
                        {"cid": cid, "market": mk}).scalar()
    return {"unread": int(unread or 0), "items": [dict(r) for r in rows]}


@router.get("/count")
def events_count(request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)
    mk = list(_MARKET_KINDS)
    n = db.execute(text(f"SELECT count(*) FROM event_log e WHERE {_visible('e')} AND NOT {_seen('e')}"),
                   {"cid": cid, "market": mk}).scalar()
    per = db.execute(text(f"SELECT idu, count(*) FROM event_log e WHERE idu IS NOT NULL"
                          f" AND {_visible('e')} AND NOT {_seen('e')} GROUP BY idu"),
                     {"cid": cid, "market": mk}).all()
    return {"unread": int(n or 0), "par_parcelle": {r[0]: r[1] for r in per}}


@router.post("/{event_id}/read")
def mark_read(event_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)
    # 1) event du compte (perso, ou pilote sur ses lignes NULL) : on marque la colonne partagée.
    #    SEC-IDOR : compte_id IS NOT DISTINCT FROM :cid → jamais l'event d'un autre compte.
    marque = db.execute(
        text("UPDATE event_log SET lu = true WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
        {"i": event_id, "cid": cid}).rowcount
    # 2) event de MARCHÉ (ligne partagée compte_id NULL) vu par un compte réel : on pose un « vu »
    #    PAR COMPTE — jamais d'UPDATE sur la ligne partagée. Le WHERE borne au marché : impossible
    #    de « voir » ainsi l'event perso d'autrui ni une ligne NULL hors marché.
    if not marque and cid is not None:
        db.execute(text(
            "INSERT INTO event_seen (compte_id, event_id) "
            "SELECT :cid, e.id FROM event_log e "
            "WHERE e.id = :i AND e.compte_id IS NULL AND e.kind = ANY(:market) "
            "ON CONFLICT (compte_id, event_id) DO NOTHING"),
            {"cid": cid, "i": event_id, "market": list(_MARKET_KINDS)})
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)
    # perso (+ pilote sur ses NULL) : colonne partagée.
    n = db.execute(text("UPDATE event_log SET lu = true WHERE NOT lu AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"cid": cid}).rowcount
    # marché vu par un compte réel : un « vu » par compte pour chaque event de marché pas encore vu.
    if cid is not None:
        n += db.execute(text(
            "INSERT INTO event_seen (compte_id, event_id) "
            "SELECT :cid, e.id FROM event_log e "
            "WHERE e.compte_id IS NULL AND e.kind = ANY(:market) "
            "  AND NOT EXISTS (SELECT 1 FROM event_seen s WHERE s.event_id = e.id AND s.compte_id = :cid) "
            "ON CONFLICT (compte_id, event_id) DO NOTHING"),
            {"cid": cid, "market": list(_MARKET_KINDS)}).rowcount
    return {"ok": True, "marques": n}


@router.post("/detect")
def api_detect(run_from: str = RUN, run_to: str = "q_v2_demo", db: Session = Depends(get_db)) -> dict:
    return detect_events(db, run_from, run_to, demo=run_to.endswith("_demo"))


@router.post("/demo")
def api_demo(db: Session = Depends(get_db)) -> dict:
    return seed_demo(db)


# ── M14 — suivi de cible ──

@router.get("/watch/{idu}")
def watch_status(idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    w = db.execute(text("SELECT 1 FROM watched_parcels WHERE idu = :i AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"i": idu, "cid": current_compte(request)}).scalar()
    return {"watched": bool(w)}


@router.post("/reprise/{idu}")
def reprise_veille(idu: str, payload: dict, request: Request, db: Session = Depends(get_db)) -> dict:
    """M23-C — remise en veille d'une parcelle ARCHIVÉE du pipeline : réalerte à 3/6/12/24
    mois. Snapshot de l'état SERVI (tier + dernier événement) au moment de l'archivage —
    l'échéance dira CE QUI A CHANGÉ. Circuit M17 (event_log kind='veille'), pas un second."""
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    mois = int(payload.get("mois") or 0)
    if mois not in (3, 6, 12, 24):
        raise HTTPException(422, "mois ∈ {3, 6, 12, 24}")
    if not db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).scalar():
        raise HTTPException(404, "Parcelle inconnue")
    # M-K (P2-65) : chemin UNIQUE — current_compte (request.state, posé par la garde d'auth).
    # Plus de lecture cookie à la main : une session invalide est déjà 401 en amont ; None =
    # bucket pilote légitime. Avant, un try/except silencieux rangeait la réalerte dans le feed
    # pilote (compte_id NULL) au lieu du client, sans erreur.
    from .tenant import current_compte
    compte_id = current_compte(request)
    cur = db.execute(text(
        "SELECT tier, event_date FROM parcel_p_score_v2 WHERE run_id = :r AND parcelle_id = :i"),
        {"r": Q_A_RUN_LABEL, "i": idu}).mappings().first()
    row = db.execute(text(
        "INSERT INTO veille_reprise (compte_id, idu, mois, echeance, tier_archivage, event_date_archivage) "
        "VALUES (:c, :i, :m, CURRENT_DATE + make_interval(months => :m), :t, :e) "
        "RETURNING id, echeance"),
        {"c": compte_id, "i": idu, "m": mois,
         "t": cur["tier"] if cur else None,
         "e": cur["event_date"] if cur else None}).mappings().first()
    db.commit()
    return {"ok": True, "id": row["id"], "idu": idu, "mois": mois,
            "echeance": str(row["echeance"]),
            "tier_archivage": cur["tier"] if cur else None}


@router.post("/watch/{idu}")
def watch_toggle(idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)   # CLOISON : le suivi est privé au compte (A et B peuvent suivre la même parcelle)
    if not db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).scalar():
        raise HTTPException(404, "Parcelle inconnue")
    if db.execute(text("SELECT 1 FROM watched_parcels WHERE idu = :i AND compte_id IS NOT DISTINCT FROM :cid"),
                  {"i": idu, "cid": cid}).scalar():
        db.execute(text("DELETE FROM watched_parcels WHERE idu = :i AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"i": idu, "cid": cid})
        return {"watched": False}
    db.execute(text("INSERT INTO watched_parcels (idu, compte_id) VALUES (:i, :cid)"), {"i": idu, "cid": cid})
    return {"watched": True}


# ── M11 — veilles (recherches sauvegardées) ──

class SearchSaveIn(BaseModel):
    nom: str
    hash: str


@router.get("/searches")
def searches_list(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    from .tenant import current_compte
    return [dict(r) for r in db.execute(text(
        "SELECT id, nom, hash, created_at::date::text AS date FROM saved_searches"
        " WHERE compte_id IS NOT DISTINCT FROM :cid ORDER BY id DESC"),
        {"cid": current_compte(request)}).mappings()]


@router.post("/searches")
def searches_add(body: SearchSaveIn, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    db.execute(text("INSERT INTO saved_searches (nom, hash, compte_id) VALUES (:n, :h, :cid)"),
               {"n": body.nom[:80], "h": body.hash, "cid": current_compte(request)})
    return {"ok": True}


# ── M17-B : veille en langage naturel — RÉUTILISE la brique NL (ia_search, validée par schéma) ;
# ne produit QUE des veilles réellement déclenchables (garde-fou audit M16-A5). ──
class VeilleNLIn(BaseModel):
    text: str


#: intentions naturelles NON détectables aujourd'hui (M16-A5) → refus honnête, jamais de veille muette.
_INDECLENCHABLE = [
    (("plu", "zonage", "constructible", "zone"), ("chang", "passe", "devien", "évolu", "modif", "révis"),
     "un changement de PLU / de zonage"),
    (("permis",), ("aband", "annul", "refus", "retir", "caduc", "périm", "expir"),
     "l'abandon ou l'annulation d'un permis (on ne détecte que l'APPARITION d'un permis)"),
    (("prix", "vente", "vendu", "dvf", "valeur"), ("baiss", "monte", "chang", "évolu"),
     "un mouvement de prix / de valeur"),
    (("dpe", "énerg", "passoire"), ("chang", "amélior", "rénov"), "un changement de DPE"),
]
_TRIGGERS_TXT = ("Aujourd'hui, une veille vous alerte quand une parcelle bascule (devient plus chaude), "
                 "éventuellement filtrée par commune, surface, score, SDP ou procédure BODACC. "
                 "Reformulez vers l'un de ces déclencheurs — ex. « les grandes parcelles à Saint-Paul qui deviennent chaudes ».")


@router.post("/veille-nl")
def veille_nl(body: VeilleNLIn, db: Session = Depends(get_db)) -> dict:
    txt = (body.text or "").strip()
    low = txt.lower()
    if len(txt) < 3:
        return {"ok": False, "refus": "Décrivez en quelques mots ce que vous voulez suivre."}
    # 1) garde-fou : intention explicitement NON détectable → refus ciblé (jamais de veille muette)
    for sujets, verbes, libelle in _INDECLENCHABLE:
        if any(s in low for s in sujets) and any(v in low for v in verbes):
            return {"ok": False, "indeclenchable": True,
                    "refus": f"Cette veille n'est pas encore possible : on ne sait pas détecter {libelle}. {_TRIGGERS_TXT}"}
    # 2) traduction par la brique existante (schéma = garde-fou : jamais de filtre inventé)
    from .ia import SearchIn, ia_search
    res = ia_search(SearchIn(text=txt), db)
    fr = res.get("filters")
    if not isinstance(fr, dict):
        # programme / out_of_scope / projet_intent → ce n'est pas une veille filtrable
        return {"ok": False, "refus": f"Je n'ai pas su en tirer une veille déclenchable. {_TRIGGERS_TXT}"}
    # 3) ne garder QUE les dimensions que le matcher de veille honore réellement
    tiers = list(fr.get("tiers") or [])
    for s in (fr.get("statuts") or []):        # statuts matrice → tiers (recouvrement chaude/a_creuser/ecartee)
        if s in ("chaude", "a_creuser", "ecartee") and s not in tiers:
            tiers.append(s)
    communes = list(fr.get("communes") or []) or ([fr["commune"]] if fr.get("commune") else [])
    trig = {"tiers": tiers, "communes": communes, "evenement": bool(fr.get("evenement")),
            "scoreMin": fr.get("scoreMin"), "surfaceMin": fr.get("surfaceMin"),
            "surfaceMax": fr.get("surfaceMax"), "sdpMin": fr.get("sdpMin")}
    if not (tiers or communes or trig["evenement"] or trig["scoreMin"]
            or trig["surfaceMin"] or trig["surfaceMax"] or trig["sdpMin"]):
        return {"ok": False, "refus": f"Je n'ai pas su en tirer un critère déclenchable. {_TRIGGERS_TXT}"}
    # 4) résumé lisible (ce que la veille fera VRAIMENT)
    STA = {"brulante": "brûlante", "chaude": "chaude", "a_creuser": "à creuser", "ecartee": "écartée"}
    bits = []
    if tiers:
        bits.append("devient " + " / ".join(STA.get(t, t) for t in tiers))
    else:
        bits.append("bascule (devient plus chaude)")
    if communes:
        bits.append("à " + ", ".join(communes))
    if trig["surfaceMin"]:
        bits.append(f"surface ≥ {trig['surfaceMin']} m²")
    if trig["surfaceMax"]:
        bits.append(f"surface ≤ {trig['surfaceMax']} m²")
    if trig["sdpMin"]:
        bits.append(f"SDP ≥ {trig['sdpMin']} m²")
    if trig["scoreMin"]:
        bits.append(f"potentiel ≥ {trig['scoreMin']}")
    if trig["evenement"]:
        bits.append("avec procédure BODACC")
    # critères compris MAIS non déclenchables par une veille (honnêteté : on le dit)
    ignores = []
    if fr.get("zonage"):
        ignores.append("zonage PLU")
    if fr.get("flags"):
        ignores.append("contraintes (flags)")
    if fr.get("personneMorale"):
        ignores.append("propriétaire personne morale")
    return {"ok": True, "filters": trig, "resume": "Alerte quand une parcelle " + ", ".join(bits) + ".",
            "ignores": ignores, "explication": res.get("explanation")}


@router.delete("/searches/{sid}")
def searches_del(sid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    db.execute(text("DELETE FROM saved_searches WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
               {"i": sid, "cid": current_compte(request)})   # SEC-IDOR
    return {"ok": True}


class SearchRenameIn(BaseModel):
    nom: str


@router.patch("/searches/{sid}")
def searches_rename(sid: int, body: SearchRenameIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M52 L5 — renommer une vue/veille sauvegardée (compte-scopé, SEC-IDOR comme la suppression)."""
    from .tenant import current_compte
    db.execute(text("UPDATE saved_searches SET nom = :n WHERE id = :i AND compte_id IS NOT DISTINCT FROM :cid"),
               {"n": body.nom[:80], "i": sid, "cid": current_compte(request)})
    return {"ok": True}


# ── M13 — digest hebdo ──

def _mes_communes(db: Session, cid: int | None) -> list[str]:
    """Communes des parcelles SUIVIES/en veille du compte (« dont M dans vos communes »).
    Vide (ou pilote) → le résumé marché montre le total seul."""
    if cid is None:
        return []
    rows = db.execute(text(
        "SELECT DISTINCT p.commune FROM watched_parcels w JOIN parcels p ON p.idu = w.idu "
        "WHERE w.compte_id = :c AND p.commune IS NOT NULL"), {"c": cid}).all()
    return [r[0] for r in rows]


def _digest_data(db: Session, cid: int | None = None) -> dict:
    # PERSONNEL : listé en détail, CLOISON STRICTE (le marché n'apparaît PAS ici — il est borné
    # en résumé plus bas ; jamais la liste exhaustive du marché dans un digest).
    events = db.execute(text("""
        SELECT e.kind, e.idu, e.titre, e.detail, e.demo, d.q_score, d.a_score, d.matrice_statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE e.ts >= now() - interval '7 days'
          AND e.compte_id IS NOT DISTINCT FROM :cid AND e.kind = ANY(:perso)
        ORDER BY (e.kind = 'bascule') DESC, d.q_score DESC NULLS LAST LIMIT 10"""),
        {"run": RUN, "cid": cid, "perso": list(_PERSO_KINDS)}).mappings().all()
    # MARCHÉ : RÉSUMÉ BORNÉ (jamais la liste). « N au total, dont M dans vos communes » ; si le
    # compte n'a pas de parcelles suivies (communes vides) → total seul (`dans_vos_communes=None`).
    communes = _mes_communes(db, cid)
    marche = db.execute(text("""
        SELECT e.kind, count(*) AS n,
               count(*) FILTER (WHERE p.commune = ANY(:coms)) AS n_communes
        FROM event_log e LEFT JOIN parcels p ON p.idu = e.idu
        WHERE e.ts >= now() - interval '7 days' AND e.compte_id IS NULL AND e.kind = ANY(:market)
        GROUP BY e.kind"""), {"market": list(_MARKET_KINDS), "coms": communes}).mappings().all()
    marche_resume = {"total": sum(r["n"] for r in marche),
                     "dans_vos_communes": (sum(r["n_communes"] for r in marche) if communes else None),
                     "par_kind": {r["kind"]: r["n"] for r in marche}}
    # TOP 5 sur les TIERS SERVIS (plus jamais matrice_statut morte M37 — comme /reperes en M36).
    # « chaudes » = les deux tiers les plus chauds servis (brulante + chaude), run ÉPINGLÉ.
    top = db.execute(text("""
        SELECT p.idu, p.commune, d.q_score, d.a_score, round(p.surface_m2) AS surface_m2,
               r.sdp_residuelle_m2, s.tier
        FROM parcel_p_score_v2 s
        JOIN parcels p ON p.idu = s.parcelle_id
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE s.run_id = :run AND s.tier IN ('brulante', 'chaude')
        ORDER BY s.rang NULLS LAST LIMIT 5"""), {"run": RUN}).mappings().all()
    return {"evenements": [dict(r) for r in events], "marche_resume": marche_resume,
            "top_chaudes": [dict(r) for r in top]}


@router.get("/digest")
def digest(request: Request, db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    return _digest_data(db, current_compte(request))


@router.get("/digest.html", response_class=HTMLResponse)
def digest_html(request: Request, db: Session = Depends(get_db)) -> str:
    """Digest « les pépites de la semaine » — HTML email-ready (styles inline, table layout).
    L'envoi SMTP = config à brancher (cf. NOTES) ; le contenu est généré ici."""
    from .tenant import current_compte
    d = _digest_data(db, current_compte(request))
    ev_rows = "".join(
        f"<tr><td style='padding:8px 12px;border-bottom:1px solid #e5e9e7;font:13px sans-serif'>"
        f"{'🟣 DÉMO · ' if e['demo'] else ''}{e['titre']}"
        f"<div style='color:#667;font-size:11px'>{e['detail'] or ''}</div></td></tr>"
        for e in d["evenements"]) or "<tr><td style='padding:12px;font:13px sans-serif;color:#667'>Aucun événement cette semaine.</td></tr>"
    top_rows = "".join(
        f"<tr><td style='padding:6px 12px;font:600 13px monospace'>{t['idu'][8:]}</td>"
        f"<td style='padding:6px;font:13px sans-serif'>{t.get('commune') or ''} · Q {t['q_score']} · A {t['a_score']}</td>"
        f"<td style='padding:6px;font:12px sans-serif;color:#667'>{t['surface_m2'] or '—'} m² · SDP {round(t['sdp_residuelle_m2'] or 0)} m²</td></tr>"
        for t in d["top_chaudes"])
    # M-T V2 : résumé marché BORNÉ (jamais la liste). Ici la cloche/preview PEUT donner le détail,
    # mais le digest e-mail reste au résumé — on affiche le compte agrégé.
    mr = d["marche_resume"]
    cadre = (f", dont {mr['dans_vos_communes']} dans vos communes"
             if mr.get("dans_vos_communes") is not None else " sur l'île")
    marche_row = (
        f"<tr><td style='padding:8px 12px;border-bottom:1px solid #e5e9e7;font:13px sans-serif'>"
        f"{mr['total']} mouvement(s) de marché (bascules, BODACC, matchs){cadre}."
        f"<div style='color:#667;font-size:11px'>Résumé — le détail est dans la cloche.</div></td></tr>"
        if mr.get("total") else "")
    return f"""<!doctype html><html><body style="margin:0;background:#f2f5f3;padding:24px">
<table width="600" align="center" style="background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#060A08;padding:18px 24px">
  <span style="display:inline-flex;align-items:center;gap:8px"><svg viewBox="0 0 240 82" style="height:16px;filter:drop-shadow(0 0 6px rgba(47,224,160,.35))" fill="#2FE0A0"><path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg><span style="font:700 16px sans-serif;color:#5CE6A1">LABUSE</span></span>
  <span style="font:12px sans-serif;color:#8FA69A"> · la chasse au trésor de la semaine</span></td></tr>
<tr><td style="padding:16px 12px 4px;font:700 13px sans-serif;color:#111">CE QUI A BOUGÉ</td></tr>
{ev_rows}
{marche_row}
<tr><td style="padding:16px 12px 4px;font:700 13px sans-serif;color:#111">TOP 5 CHAUDES (île entière)</td></tr>
<tr><td><table width="100%">{top_rows}</table></td></tr>
<tr><td style="padding:14px 24px;font:10px sans-serif;color:#99a">Estimations indicatives issues de
données publiques — ne valent ni conseil juridique ni garantie de constructibilité.</td></tr>
</table></body></html>"""


# ── M21-B3 — ENVOI du digest par e-mail (le contenu M13 existait, l'envoi jamais) ──
# Un DIGEST (pas un mail par événement), avec désinscription OBLIGATOIRE (lien + List-Unsubscribe).
# Ne notifie que des déclencheurs RÉELS (bascule / bodacc / permis / veille) ; jamais les démos.

def _notif_token(db: Session, cid: int) -> str:
    import secrets
    tok = db.execute(text("SELECT token FROM notif_prefs WHERE compte_id=:c"), {"c": cid}).scalar()
    if tok:
        return tok
    tok = secrets.token_urlsafe(24)
    db.execute(text("INSERT INTO notif_prefs (compte_id, token) VALUES (:c,:t) "
                    "ON CONFLICT (compte_id) DO UPDATE SET token=COALESCE(notif_prefs.token,:t)"),
               {"c": cid, "t": tok})
    return db.execute(text("SELECT token FROM notif_prefs WHERE compte_id=:c"), {"c": cid}).scalar()


def envoyer_digests(db: Session, *, base_url: str = "", freq: str = "hebdo", force: bool = False) -> dict:
    """Envoie le digest aux comptes actifs abonnés ayant des événements RÉELS récents. Respecte
    l'opt-out (`notif_prefs.unsubscribed`) et un intervalle mini (anti-double-envoi)."""
    from datetime import datetime, timedelta, timezone

    from ..emails import digest_notifications
    from ..mail import send_email

    interval_h = 20 if freq == "quotidien" else 24 * 6  # hebdo ≈ 6 j
    now = datetime.now(timezone.utc)
    recipients = db.execute(text(
        "SELECT c.id AS cid, u.email FROM comptes c "
        "JOIN utilisateurs u ON u.compte_id = c.id AND u.role = 'titulaire' "
        "WHERE c.statut = 'actif'")).mappings().all()
    envoyes = ignores = 0
    for r in recipients:
        cid, email = r["cid"], r["email"]
        pref = db.execute(text("SELECT unsubscribed, last_digest_at FROM notif_prefs WHERE compte_id=:c"),
                          {"c": cid}).first()
        if pref and pref[0]:                          # désinscrit → jamais d'envoi
            ignores += 1
            continue
        last = pref[1] if pref else None
        if not force and last and (now - last) < timedelta(hours=interval_h):
            ignores += 1
            continue
        data = _digest_data(db, cid)
        evs = [e for e in data["evenements"] if not e.get("demo")]   # jamais de démo dans un vrai digest
        marche = data["marche_resume"]
        # M-T V2 : un abonné SANS veille reçoit désormais un digest si le RÉSUMÉ MARCHÉ est non vide
        # (le « digest vide à vie » était le bug). L'opt-out et le mini-intervalle ont déjà filtré
        # AU-DESSUS, et List-Unsubscribe est posé à l'envoi → les deux garanties tiennent sur ce chemin.
        if not evs and not marche.get("total"):
            ignores += 1
            continue
        tok = _notif_token(db, cid)
        lien_desabo = f"{base_url}/events/desabonner?c={cid}&t={tok}"
        sujet, corps = digest_notifications(
            evs, lien_desabo, base_url=base_url, marche=marche,
            periode="aujourd'hui" if freq == "quotidien" else "cette semaine")
        send_email(email, sujet, corps, headers={"List-Unsubscribe": f"<{lien_desabo}>"})
        db.execute(text("INSERT INTO notif_prefs (compte_id, last_digest_at) VALUES (:c,:n) "
                        "ON CONFLICT (compte_id) DO UPDATE SET last_digest_at=:n"), {"c": cid, "n": now})
        envoyes += 1
    db.commit()
    return {"envoyes": envoyes, "ignores": ignores}


@router.get("/desabonner", response_class=HTMLResponse, include_in_schema=False)
def desabonner(c: int, t: str, db: Session = Depends(get_db)) -> str:
    """Désinscription en 1 clic du digest e-mail (lien public, jeton par compte). Obligation légale."""
    tok = db.execute(text("SELECT token FROM notif_prefs WHERE compte_id=:c"), {"c": c}).scalar()
    if not tok or tok != t:
        return HTMLResponse("<!doctype html><meta charset=utf-8><p style='font:15px sans-serif;padding:40px'>"
                            "Lien de désinscription invalide ou expiré.</p>", status_code=400)
    db.execute(text("UPDATE notif_prefs SET unsubscribed = true WHERE compte_id = :c"), {"c": c})
    db.commit()
    return ("<!doctype html><meta charset=utf-8><body style='font:15px sans-serif;padding:40px;max-width:520px'>"
            "<h1 style='color:#2FE0A0'>Désinscription confirmée</h1>"
            "<p>Vous ne recevrez plus le résumé e-mail LABUSE. Les notifications restent visibles dans "
            "l'application. Vous pouvez réactiver le résumé depuis votre espace compte.</p></body>")
