"""ÉVÉNEMENTS (Vague 3) — le socle de la rétention : M11 alertes · M12 portefeuille vivant ·
M13 digest hebdo · M14 suivi de cible.

`detect_events(run_from, run_to)` diffe deux runs de scoring et émet : bascule de statut,
nouvel événement BODACC, nouveau permis proche d'une parcelle suivie (pipeline + watched).
Cronable via `labuse detect-events`. Sans second run réel, un run de DÉMONSTRATION étiqueté
(`q_v2_demo`, colonne demo=true partout) fait vivre le système — bascule réelle documentée.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/events", tags=["events"])
log = logging.getLogger("labuse.events")
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
-- M85 — event_log DEVIENT le centre unifié de notifications. Trois objets distincts (démêlés en M85) :
--   · NOTIFICATIONS = les lignes ci-dessous (ce que le client reçoit, servi à la cloche) ;
--   · VEILLES       = les déclencheurs Copilote (copilote_v2/veilles.py) qui PRODUISENT des notifs ;
--   · SECTEURS      = les zones géographiques DVF (M54, panneau carte) — renommées, sans rapport ici.
-- Colonnes M85 (idempotentes) : source (« dit sa source »), lien (cible directe : parcelle OU /sources),
-- dedup (clé de déduplication/regroupement), envoi_statut (trace e-mail par ligne — motif M84).
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS source varchar(48);
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS lien text;
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS dedup varchar(96);
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS envoi_statut varchar(16) DEFAULT 'na';
CREATE INDEX IF NOT EXISTS ix_event_log_dedup ON event_log (dedup, compte_id);
-- M85 — préférences par TYPE et par CANAL (remplacent l'opt-out GLOBAL de notif_prefs). Un type non
-- désiré ne s'affiche PAS à la cloche (cloche=false) et/ou ne part PAS en e-mail (email=false).
-- notif_prefs subsiste UNIQUEMENT pour la comptabilité d'envoi (token désinscription, last_digest_at).
CREATE TABLE IF NOT EXISTS notif_canaux (
  compte_id integer NOT NULL,
  pref_type varchar(16) NOT NULL,       -- veille | suivi | marche
  cloche boolean NOT NULL DEFAULT true,
  email  boolean NOT NULL DEFAULT true,
  PRIMARY KEY (compte_id, pref_type)
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def _ensure_cols(db: Session) -> None:
    """Colonnes M85 idempotentes — appelées par le producteur (une base servie avant ce mandat les
    reçoit à la 1re notification). Pas de migration lourde : ADD COLUMN IF NOT EXISTS."""
    for stmt in ("ALTER TABLE event_log ADD COLUMN IF NOT EXISTS source varchar(48)",
                 "ALTER TABLE event_log ADD COLUMN IF NOT EXISTS lien text",
                 "ALTER TABLE event_log ADD COLUMN IF NOT EXISTS dedup varchar(96)",
                 "ALTER TABLE event_log ADD COLUMN IF NOT EXISTS envoi_statut varchar(16) DEFAULT 'na'"):
        db.execute(text(stmt))


# ─────────────── M85 · le PRODUCTEUR UNIQUE du centre (dédup · plafond · rétention) ───────────────
# Tout producteur (Copilote-veille, ingestion/fraîcheur, futur brief) passe par ICI — jamais un INSERT
# direct. Trois garde-fous contre le bug qui inonderait un client : DÉDUP (même clé + même jour → une
# seule ligne), REGROUPEMENT (au producteur : N faits = 1 notif à N entrées) et PLAFOND DUR (par
# kind/compte/jour). ZÉRO appel modèle : du SQL et des gabarits.
NOTIF_RETENTION_JOURS = 90    # rétention (config M85) — au-delà, purge
NOTIF_CAP_JOUR = 50           # plafond dur par (kind, compte, jour) — backstop anti-inondation


def creer_notification(db: Session, *, kind: str, titre: str, detail: str | None = None,
                       compte_id: int | None = None, source: str | None = None,
                       lien: str | None = None, idu: str | None = None,
                       dedup: str | None = None, demo: bool = False) -> int:
    """Insère UNE notification dans event_log si dédup + plafond l'autorisent. Retourne l'id créé, ou
    0 si dédupliqué/plafonné. `dedup` : clé stable (ex. 'veille:12:2026-08-14') — même clé le même jour
    ne s'empile pas. `kind` hors _MARKET_KINDS = cloisonné au compte (NULL = pilote/admin, jamais client)."""
    _ensure_cols(db)
    if dedup and db.execute(text(
            "SELECT 1 FROM event_log WHERE dedup = :d AND compte_id IS NOT DISTINCT FROM :c "
            "AND ts::date = now()::date LIMIT 1"), {"d": dedup, "c": compte_id}).scalar():
        return 0
    n_jour = db.execute(text(
        "SELECT count(*) FROM event_log WHERE kind = :k AND compte_id IS NOT DISTINCT FROM :c "
        "AND ts::date = now()::date"), {"k": kind, "c": compte_id}).scalar() or 0
    if n_jour >= NOTIF_CAP_JOUR:
        log.warning("NOTIF PLAFOND — kind=%s compte=%s ≥ %d/jour : ligne refusée (producteur en boucle ?)",
                    kind, compte_id, NOTIF_CAP_JOUR)
        return 0
    return db.execute(text(
        "INSERT INTO event_log (kind, titre, detail, compte_id, source, lien, idu, dedup, demo) "
        "VALUES (:k, :t, :d, :c, :s, :l, :i, :dd, :demo) RETURNING id"),
        {"k": kind, "t": titre, "d": detail, "c": compte_id, "s": source, "l": lien,
         "i": idu, "dd": dedup, "demo": demo}).scalar() or 0


def notifier_fraicheur(db: Session) -> int:
    """M85/M84 — producteur INGESTION : chaque source réellement en retard (check_fraicheur) → une notif
    `systeme` pour le pilote/admin (compte_id NULL, hors marché → INVISIBLE aux clients : la tuyauterie
    ne les concerne pas). Dédup par source/jour : une source qui décroche N jours ne fait pas N notifs."""
    from ..ingestion import fraicheur
    crees = 0
    for e in fraicheur.etat_sources(db):
        if e.get("statut") != "en_retard":
            continue
        crees += 1 if creer_notification(
            db, kind="systeme", compte_id=None, source=f"Ingestion · {e['source']}",
            titre=f"Source en retard : {e['label']}",
            detail=(f"Dernière donnée {e['derniere_donnee']} — Δ{e['delta_donnee_jours']} j "
                    f"(seuil {e['seuil_jours']} j, soit 2× la cadence). À rattraper."),
            lien="/sources", dedup=f"fraicheur:{e['source']}:{date.today()}") else 0
    return crees


def purge_notifications(db: Session, jours: int = NOTIF_RETENTION_JOURS) -> int:
    """Rétention (config) : supprime les notifications de plus de `jours` (défaut 90). `event_seen`
    part en cascade (FK). À appeler par le cron quotidien."""
    return db.execute(text("DELETE FROM event_log WHERE ts < now() - make_interval(days => :j)"),
                      {"j": jours}).rowcount


# ─────────────── M85 · préférences par TYPE et par CANAL (le client contrôle ce qu'il reçoit) ───────────────
REUNION_TZ = timezone(timedelta(hours=4))   # UTC+4 EXPLICITE — JAMAIS le fuseau de la machine (doctrine M85)
DIGEST_HEURE_REUNION = 7                     # 7h00 heure Réunion (config)

# Catégories client, mappées depuis event_log.kind (+ cloison marché). Défauts raisonnables : veilles et
# suivi de parcelles poussent partout (cloche + e-mail) ; le marché, volumineux et informatif, reste à la
# cloche (e-mail OFF par défaut, activable). `systeme` (tuyauterie ingestion) est HORS préférences client.
PREF_TYPES = {
    "veille": {"label": "Vos veilles", "cloche": True, "email": True},
    "suivi": {"label": "Vos parcelles suivies", "cloche": True, "email": True},
    "marche": {"label": "Le marché (bascules, BODACC, matchs)", "cloche": True, "email": False},
}


def _pref_type(kind: str, is_market: bool) -> str | None:
    """kind (+ cloison marché) → catégorie de préférence. `systeme` = pilote/admin, HORS pref client."""
    if kind == "systeme":
        return None
    if kind == "veille":
        return "veille"
    return "marche" if is_market else "suivi"


def prefs_compte(db: Session, cid: int | None) -> dict:
    """Préférences EFFECTIVES {pref_type: {cloche, email}} : les défauts, écrasés par notif_canaux."""
    out = {k: {"cloche": v["cloche"], "email": v["email"]} for k, v in PREF_TYPES.items()}
    if cid is None:
        return out
    for r in db.execute(text("SELECT pref_type, cloche, email FROM notif_canaux WHERE compte_id=:c"),
                        {"c": cid}).mappings():
        if r["pref_type"] in out:
            out[r["pref_type"]] = {"cloche": bool(r["cloche"]), "email": bool(r["email"])}
    return out


def set_pref(db: Session, cid: int, pref_type: str, *, cloche: bool, email: bool) -> None:
    if pref_type not in PREF_TYPES:
        return
    db.execute(text(
        "INSERT INTO notif_canaux (compte_id, pref_type, cloche, email) VALUES (:c,:p,:cl,:em) "
        "ON CONFLICT (compte_id, pref_type) DO UPDATE SET cloche=:cl, email=:em"),
        {"c": cid, "p": pref_type, "cl": cloche, "em": email})


def desabonner_email(db: Session, cid: int) -> None:
    """Désinscription e-mail GLOBALE (lien légal / List-Unsubscribe) : coupe l'e-mail de TOUS les types,
    laisse la cloche intacte. Le client ré-affine ensuite dans ses préférences."""
    cur = prefs_compte(db, cid)
    for p in PREF_TYPES:
        set_pref(db, cid, p, cloche=cur[p]["cloche"], email=False)


def _cloche_filter_sql(prefs: dict) -> str:
    """Fragment WHERE excluant les types dont la cloche est coupée (bornage par cloison). Vide si tout
    est actif. `:cid`/`:market` sont déjà liés par l'appelant. `systeme` n'est JAMAIS exclu (pilote)."""
    excl = []
    if not prefs["veille"]["cloche"]:
        excl.append("NOT (e.kind='veille' AND e.compte_id IS NOT DISTINCT FROM :cid)")
    if not prefs["suivi"]["cloche"]:
        excl.append("NOT (e.kind IN ('permis','bascule','bodacc') AND e.compte_id IS NOT DISTINCT FROM :cid)")
    if not prefs["marche"]["cloche"]:
        excl.append("NOT (e.compte_id IS NULL AND e.kind = ANY(:market))")
    return (" AND " + " AND ".join(excl)) if excl else ""


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
def list_events(request: Request, unread_only: bool = False, limit: int = 100, offset: int = 0,
                db: Session = Depends(get_db)) -> dict:
    from .tenant import current_compte
    cid = current_compte(request)
    mk = list(_MARKET_KINDS)
    # M85 — non-lues D'ABORD (cloche), puis récentes ; paginé (offset). source/lien/ts exposés pour
    # que la cloche affiche « dit sa source et sa date » + le lien direct vers l'objet. Le FILTRE cloche
    # (préférences par type) borne la liste ET le compteur : un type coupé ne s'affiche ni ne compte.
    cf = _cloche_filter_sql(prefs_compte(db, cid))
    rows = db.execute(text(f"""
        SELECT e.id, e.ts::date::text AS date, e.ts::text AS ts, e.kind, e.idu, e.titre, e.detail,
               e.demo, e.source, e.lien,
               {_seen('e')} AS lu,
               d.matrice_statut AS statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE {_visible('e')} {f"AND NOT {_seen('e')}" if unread_only else ""}{cf}
        ORDER BY {_seen('e')} ASC, e.ts DESC, e.id DESC LIMIT :lim OFFSET :off"""),
        {"lim": limit, "off": max(0, offset), "run": RUN, "cid": cid, "market": mk}).mappings().all()
    unread = db.execute(text(
        f"SELECT count(*) FROM event_log e WHERE {_visible('e')} AND NOT {_seen('e')}{cf}"),
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
    """Aperçu HTML du digest (le MÊME gabarit DA que l'e-mail réel — vert #1E9E58 sur blanc, sans
    mauve, sans image externe). Les liens désabo/préférences sont réels si le compte a un jeton."""
    from ..emails import digest_html_email
    from .tenant import current_compte
    cid = current_compte(request)
    d = _digest_data(db, cid)
    evs = [e for e in d["evenements"] if not e.get("demo")]
    prefs = prefs_compte(db, cid)
    if cid is not None:
        tok = _notif_token(db, cid); db.commit()
        lien_desabo = f"/events/desabonner?c={cid}&t={tok}"
        lien_prefs = f"/events/preferences?c={cid}&t={tok}"
    else:
        lien_desabo = lien_prefs = "#"
    marche = d["marche_resume"] if prefs["marche"]["email"] else {"total": 0}
    return digest_html_email(evs, marche, d.get("top_chaudes", []), lien_desabo, lien_prefs,
                             periode="aujourd'hui")


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


def envoyer_digests(db: Session, *, base_url: str = "", freq: str = "quotidien", force: bool = False) -> dict:
    """Envoie le digest aux comptes actifs, FILTRÉ par préférence e-mail (par type/canal). Garanties :
    anti-double-envoi (last_digest_at + intervalle mini), un digest VIDE ne part pas, désinscription +
    préférences dans chaque e-mail (légal), statut d'envoi tracé (jamais silencieux — motif M84).
    Fuseau explicite UTC+4 pour la fenêtre quotidienne (jamais hérité de la machine)."""
    from ..emails import digest_html_email, digest_notifications
    from ..mail import send_email

    interval_h = 20 if freq == "quotidien" else 24 * 6   # quotidien ≈ 20 h ; hebdo ≈ 6 j
    now = datetime.now(timezone.utc)
    periode = "aujourd'hui" if freq == "quotidien" else "cette semaine"
    # LEFT JOIN (pas INNER) : un compte actif SANS utilisateur titulaire n'est plus SILENCIEUSEMENT
    # exclu — il apparaît avec email=NULL et un motif « pas d'adresse ». Le silence est le défaut qu'on
    # ferme partout : chaque compte reçoit un STATUT + un MOTIF explicites (Vic, M85).
    recipients = db.execute(text(
        "SELECT c.id AS cid, min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id = c.id "
        "WHERE c.statut = 'actif' GROUP BY c.id ORDER BY c.id")).mappings().all()
    envoyes = ignores = echecs = 0
    details: list[dict] = []

    def _note(cid, email, statut, motif):
        details.append({"compte": cid, "email": email, "statut": statut, "motif": motif})

    for r in recipients:
        cid, email = r["cid"], r["email"]
        if not email or not str(email).strip():
            ignores += 1
            _note(cid, email, "ignoré", "pas d'adresse (aucun utilisateur titulaire avec e-mail)")
            continue
        prefs = prefs_compte(db, cid)
        if not any(p["email"] for p in prefs.values()):
            ignores += 1
            _note(cid, email, "ignoré", "e-mail désactivé (préférences : tous les canaux e-mail coupés)")
            continue
        last = db.execute(text("SELECT last_digest_at FROM notif_prefs WHERE compte_id=:c"),
                          {"c": cid}).scalar()
        if not force and last and (now - last) < timedelta(hours=interval_h):
            ignores += 1
            _note(cid, email, "ignoré", f"anti-double-envoi (dernier digest {last:%Y-%m-%d %H:%M} UTC)")
            continue
        data = _digest_data(db, cid)
        # FILTRE par préférence e-mail PAR TYPE : un type dont l'e-mail est coupé n'entre pas au digest.
        evs = [e for e in data["evenements"]
               if not e.get("demo") and prefs.get(_pref_type(e["kind"], False), {}).get("email")]
        marche = data["marche_resume"] if prefs["marche"]["email"] else {"total": 0}
        if not evs and not marche.get("total"):
            ignores += 1
            _note(cid, email, "ignoré", "aucune notification en attente (rien d'e-mail-activé sur 7 j + marché vide)")
            continue
        tok = _notif_token(db, cid)
        lien_desabo = f"{base_url}/events/desabonner?c={cid}&t={tok}"
        lien_prefs = f"{base_url}/events/preferences?c={cid}&t={tok}"
        sujet, corps = digest_notifications(evs, lien_desabo, base_url=base_url, marche=marche,
                                            periode=periode, lien_prefs=lien_prefs)
        html = digest_html_email(evs, marche, data.get("top_chaudes", []), lien_desabo, lien_prefs,
                                 base_url=base_url, periode=periode)
        res = send_email(email, sujet, corps, body_html=html,
                         headers={"List-Unsubscribe": f"<{lien_desabo}>"})
        if res.ok:
            envoyes += 1
            _note(cid, email, "envoyé", f"{len(evs)} événement(s)" + (f" + {marche['total']} marché" if marche.get("total") else ""))
        else:                                                  # échec tracé, jamais silencieux
            echecs += 1
            _note(cid, email, "échec", f"envoi refusé : {res.detail}")
            log.warning("DIGEST non envoyé — compte=%s cause=%s", cid, res.detail)
        db.execute(text("INSERT INTO notif_prefs (compte_id, last_digest_at) VALUES (:c,:n) "
                        "ON CONFLICT (compte_id) DO UPDATE SET last_digest_at=:n"), {"c": cid, "n": now})
    db.commit()
    return {"envoyes": envoyes, "ignores": ignores, "echecs": echecs, "details": details}


def _token_ok(db: Session, c: int, t: str) -> bool:
    tok = db.execute(text("SELECT token FROM notif_prefs WHERE compte_id=:c"), {"c": c}).scalar()
    return bool(tok and t and tok == t)


@router.get("/desabonner", response_class=HTMLResponse, include_in_schema=False)
def desabonner(c: int, t: str, db: Session = Depends(get_db)) -> str:
    """Désinscription en 1 clic du digest e-mail (lien public, jeton par compte). Obligation légale.
    M85 : coupe l'e-mail de TOUS les types (les préférences fines restent réglables) ; la cloche reste."""
    if not _token_ok(db, c, t):
        return HTMLResponse("<!doctype html><meta charset=utf-8><p style='font:15px sans-serif;padding:40px'>"
                            "Lien de désinscription invalide ou expiré.</p>", status_code=400)
    desabonner_email(db, c)
    db.commit()
    lien_prefs = f"/events/preferences?c={c}&t={t}"
    return ("<!doctype html><meta charset=utf-8><body style='font:15px sans-serif;padding:40px;max-width:520px'>"
            "<h1 style='color:#1E9E58'>Désinscription confirmée</h1>"
            "<p>Vous ne recevrez plus d'e-mail LABUSE. Les notifications restent visibles dans "
            f"l'application. Vous pouvez <a href='{lien_prefs}' style='color:#1E9E58'>régler vos "
            "préférences par type</a> à tout moment.</p></body>")


# ── M85 · les PRÉFÉRENCES par type et par canal ──

def _page_preferences(db: Session, c: int, t: str, sauve: bool = False) -> str:
    prefs = prefs_compte(db, c)
    lignes = ""
    for k, meta in PREF_TYPES.items():
        p = prefs[k]
        lignes += (
            f"<tr><td style='padding:10px 8px;font:14px sans-serif'>{meta['label']}</td>"
            f"<td style='text-align:center;padding:10px 8px'><input type='checkbox' name='{k}_cloche'"
            f"{' checked' if p['cloche'] else ''}></td>"
            f"<td style='text-align:center;padding:10px 8px'><input type='checkbox' name='{k}_email'"
            f"{' checked' if p['email'] else ''}></td></tr>")
    ok = ("<p style='background:#e8f7ee;color:#1E9E58;padding:8px 12px;border-radius:8px;"
          "font:13px sans-serif'>✓ Préférences enregistrées.</p>" if sauve else "")
    return (f"<!doctype html><meta charset=utf-8><body style='font:15px sans-serif;padding:32px;"
            f"max-width:560px;margin:auto'>"
            f"<h1 style='color:#1E9E58;font-size:20px'>Vos préférences de notification</h1>"
            f"<p style='color:#555'>Pour chaque type, choisissez la <b>cloche</b> (dans l'application) "
            f"et/ou l'<b>e-mail</b> (le résumé quotidien). Décochez tout pour ne rien recevoir.</p>{ok}"
            f"<form method='post' action='/events/preferences?c={c}&t={t}'>"
            f"<table style='width:100%;border-collapse:collapse;margin:16px 0'>"
            f"<tr style='border-bottom:2px solid #1E9E58'><th style='text-align:left;padding:8px'>Type</th>"
            f"<th style='padding:8px'>Cloche</th><th style='padding:8px'>E-mail</th></tr>{lignes}</table>"
            f"<button type='submit' style='background:#1E9E58;color:#fff;border:0;border-radius:8px;"
            f"padding:10px 20px;font:600 14px sans-serif;cursor:pointer'>Enregistrer</button></form></body>")


@router.get("/preferences", response_class=HTMLResponse, include_in_schema=False)
def preferences_page(c: int, t: str, db: Session = Depends(get_db)) -> str:
    """Page PRÉFÉRENCES par type/canal (lien de l'e-mail, jeton par compte). Le client contrôle tout."""
    if not _token_ok(db, c, t):
        return HTMLResponse("<!doctype html><meta charset=utf-8><p style='font:15px sans-serif;"
                            "padding:40px'>Lien invalide ou expiré.</p>", status_code=400)
    return _page_preferences(db, c, t)


@router.post("/preferences", response_class=HTMLResponse, include_in_schema=False)
async def preferences_save(c: int, t: str, request: Request, db: Session = Depends(get_db)) -> str:
    if not _token_ok(db, c, t):
        return HTMLResponse("Lien invalide.", status_code=400)
    form = await request.form()
    for k in PREF_TYPES:
        set_pref(db, c, k, cloche=f"{k}_cloche" in form, email=f"{k}_email" in form)
    db.commit()
    return _page_preferences(db, c, t, sauve=True)


@router.get("/prefs")
def prefs_get(request: Request, db: Session = Depends(get_db)) -> dict:
    """API in-app : les préférences du compte courant (+ leurs libellés)."""
    from .tenant import current_compte
    cid = current_compte(request)
    p = prefs_compte(db, cid)
    return {"types": [{"key": k, "label": PREF_TYPES[k]["label"], **p[k]} for k in PREF_TYPES]}


class PrefIn(BaseModel):
    pref_type: str
    cloche: bool
    email: bool


@router.patch("/prefs")
def prefs_patch(body: PrefIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """API in-app : régler un type/canal. Le pilote (compte NULL) ne persiste pas (défauts servis)."""
    from .tenant import current_compte
    cid = current_compte(request)
    if cid is None:
        return {"ok": False, "motif": "session pilote — préférences non persistées"}
    set_pref(db, cid, body.pref_type, cloche=body.cloche, email=body.email)
    db.commit()
    return {"ok": True}
