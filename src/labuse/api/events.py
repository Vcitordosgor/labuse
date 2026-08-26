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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/events", tags=["events"])
log = logging.getLogger("labuse.events")
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)

# M137-M — la BASCULE = « notre verdict qui change » = le TIER V2 SERVI (parcel_p_score_v2.tier),
# plus la matrice morte (matrice_statut/q_score, NULL depuis M129). Les tiers PRIORITAIRES sont ceux
# dont l'entrée mérite une alerte ; le rang donne le sens (montée = vers un tier plus chaud).
# VOCABULAIRE SERVI (M135/M137) : jamais « brûlante/chaude » à l'écran — tout libellé passe par le
# mapping canonique tiers_client.court() (chips : Priorité / À suivre / Long terme / Neutre / Faible /
# Écartée). Les clés internes (brulante, chaude) restent en base, jamais servies.
from ..scoring.tiers_client import court as _tier_court   # noqa: E402
_TIERS_PRIORITE = ("brulante", "chaude")
_TIER_RANG = {"brulante": 0, "chaude": 1, "reserve_fonciere": 2, "a_creuser": 3,
              "declasse_bati_revele": 4, "declasse_bati_sature": 5, "declasse_non_constructible": 6,
              "declasse_zone_fermee": 7, "declasse_au_statut_inconnu": 8, "declasse_au_fermee": 9,
              "ecartee": 10}


def _monte(de: str | None, vers: str | None) -> bool:
    """Bascule MONTANTE : le tier de destination est plus chaud que celui d'origine (rang plus bas)."""
    return _TIER_RANG.get(vers or "", 99) < _TIER_RANG.get(de or "", 99)


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
-- M85-B — trace des ANNONCES (chaîne 3) : qui, quoi, quand, combien de destinataires, statut.
CREATE TABLE IF NOT EXISTS annonces (
  id serial PRIMARY KEY, type varchar(20), titre text, corps text, lien text,
  envoye_par text, at timestamptz DEFAULT now(),
  n_cible int, n_mail_ok int, n_mail_echec int, n_cloche int
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        from ..db import sql_statements  # FIX-GB-011 : plus de split(';') naif
        for stmt in sql_statements(DDL):
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
                       dedup: str | None = None, demo: bool = False,
                       envoi_statut: str = "na", permanent: bool = False) -> int:
    """Insère UNE notification dans event_log si dédup + plafond l'autorisent. Retourne l'id créé, ou
    0 si dédupliqué/plafonné. `dedup` : clé stable (ex. 'veille:12:2026-08-14') — même clé le même jour
    ne s'empile pas. `kind` hors _MARKET_KINDS = cloisonné au compte (NULL = pilote/admin, jamais client).

    `permanent` (fix veille-notifs #3) : pour un FAIT UNIQUE (ex. un permis, clé (idu, permit_id)), la
    dédup est PERMANENTE (NOT EXISTS sur la clé, toutes dates) — un rejeu N'EMPILE JAMAIS un doublon,
    comme les kinds bascule/bodacc (NOT EXISTS sur le tuple de run). Défaut = fenêtre jour (rappels
    récurrents, ex. fraîcheur `source:date`).

    M85-B — LE REGISTRE fait loi : un `kind` non déclaré (ni type de registre, ni kind historique connu)
    est REFUSÉ (ValueError). Personne n'ajoute un envoi hors inventaire."""
    from ..notif_registry import _KIND_VERS_TYPE, est_declare
    if kind not in _KIND_VERS_TYPE and not est_declare(kind):
        log.error("NOTIF REFUSÉE — kind/type « %s » non déclaré au registre (M85-B).", kind)
        raise ValueError(f"type de notification non déclaré au registre : {kind!r}")
    _ensure_cols(db)
    _fenetre = "" if permanent else "AND ts::date = now()::date "   # #3 : permanent = toutes dates
    if dedup and db.execute(text(
            "SELECT 1 FROM event_log WHERE dedup = :d AND compte_id IS NOT DISTINCT FROM :c "
            + _fenetre + "LIMIT 1"), {"d": dedup, "c": compte_id}).scalar():
        return 0
    n_jour = db.execute(text(
        "SELECT count(*) FROM event_log WHERE kind = :k AND compte_id IS NOT DISTINCT FROM :c "
        "AND ts::date = now()::date"), {"k": kind, "c": compte_id}).scalar() or 0
    if n_jour >= NOTIF_CAP_JOUR:
        # V2 (FIX-VEILLE) — le débordement n'est plus SILENCIEUX : un SEUL event agrégé par
        # (kind, compte, jour), « +N autres … aujourd'hui », dont le compteur monte. Le client sait
        # qu'il y a plus, rien n'est jeté sans trace.
        _debordement(db, kind, compte_id)
        log.warning("NOTIF PLAFOND — kind=%s compte=%s ≥ %d/jour : agrégé en « +N autres » (pas jeté)",
                    kind, compte_id, NOTIF_CAP_JOUR)
        return 0
    return db.execute(text(
        "INSERT INTO event_log (kind, titre, detail, compte_id, source, lien, idu, dedup, demo, envoi_statut) "
        "VALUES (:k, :t, :d, :c, :s, :l, :i, :dd, :demo, :es) RETURNING id"),
        {"k": kind, "t": titre, "d": detail, "c": compte_id, "s": source, "l": lien,
         "i": idu, "dd": dedup, "demo": demo, "es": envoi_statut}).scalar() or 0


def _debordement(db: Session, kind: str, compte_id: int | None) -> None:
    """V2 (FIX-VEILLE) — quand le plafond quotidien d'un (kind, compte) est atteint, on n'écarte plus
    le surplus EN SILENCE : on tient UN event agrégé par jour (« +N autres … aujourd'hui »), dont le
    compteur N monte à chaque fait surnuméraire. Écrit en SQL DIRECT (hors plafond → pas de récursion),
    dédup jour dédié → une seule ligne. Le kind = celui des notifs plafonnées (donc VISIBLE dans le
    même flux, cloche/digest). L'évaluation tourne côté cron (mono-thread) : read-modify-write sûr."""
    dd = f"debordement:{kind}"
    prev = db.execute(text(
        "SELECT id, titre FROM event_log WHERE dedup = :dd AND compte_id IS NOT DISTINCT FROM :c "
        "AND ts::date = now()::date LIMIT 1"), {"dd": dd, "c": compte_id}).mappings().first()
    n = 1
    if prev:
        try:                                            # format contrôlé « +N autres … » → on relit N
            n = int((prev["titre"] or "").split(" ", 1)[0].lstrip("+")) + 1
        except (ValueError, IndexError):
            n = 2
    titre = f"+{n} autre(s) « {kind} » aujourd'hui — plafond de {NOTIF_CAP_JOUR} atteint"
    detail = (f"Le plafond quotidien de {NOTIF_CAP_JOUR} notifications « {kind} » est atteint. {n} fait(s) "
              f"supplémentaire(s) aujourd'hui ne sont pas listés un par un ; le détail reste consultable à la source.")
    if prev:
        db.execute(text("UPDATE event_log SET titre = :t, detail = :d, ts = now() WHERE id = :i"),
                   {"t": titre, "d": detail, "i": prev["id"]})
    else:
        db.execute(text(
            "INSERT INTO event_log (kind, titre, detail, compte_id, dedup, envoi_statut) "
            "VALUES (:k, :t, :d, :c, :dd, 'na')"),
            {"k": kind, "t": titre, "d": detail, "c": compte_id, "dd": dd})


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


# ─────────────── M85 / M85-B · préférences par TYPE (registre) et par CANAL ───────────────
REUNION_TZ = timezone(timedelta(hours=4))   # UTC+4 EXPLICITE — JAMAIS le fuseau de la machine (doctrine M85)
DIGEST_HEURE_REUNION = 7                     # 7h00 heure Réunion (config)

# M85-B — les types de préférence sont ceux du REGISTRE (source unique). notif_canaux porte les
# surcharges ; les défauts viennent du registre (tout activé). `maintenance` est VERROUILLÉ (e-mail
# toujours on, non désactivable — conséquences réelles). Le marché partagé (compte NULL) n'est PAS un
# type de préférence : flux CLOCHE informatif, hors des 3 chaînes, jamais d'e-mail.
_KINDS_PAR_PREF = {   # type de registre → kinds event_log (perso) qu'il gouverne à la cloche
    "veille_zone": ("veille", "match", "veille_zone"),
    "parcelle_suivie": ("permis", "bascule", "bodacc", "parcelle_suivie"),
    "annonce_produit": ("annonce_produit",),
    "maintenance": ("maintenance",),
}


def _pref_type(kind: str, is_market: bool = False) -> str:
    """kind event_log → type de préférence du REGISTRE (source unique)."""
    from ..notif_registry import type_pour_kind
    return type_pour_kind(kind)


def prefs_compte(db: Session, cid: int | None) -> dict:
    """Préférences EFFECTIVES {type: {cloche, email, verrou, label}} : défauts du registre (tout activé),
    écrasés par notif_canaux. `maintenance` : e-mail FORCÉ à True + verrou (jamais désactivable)."""
    from ..notif_registry import REGISTRE, TYPES_CLIENT, canaux, desactivable
    out = {t: {"cloche": "cloche" in canaux(t), "email": "mail" in canaux(t),
               "verrou": not desactivable(t), "label": REGISTRE[t]["libelle"]} for t in TYPES_CLIENT}
    if cid is not None:
        for r in db.execute(text("SELECT pref_type, cloche, email FROM notif_canaux WHERE compte_id=:c"),
                            {"c": cid}).mappings():
            if r["pref_type"] in out:
                out[r["pref_type"]].update(cloche=bool(r["cloche"]), email=bool(r["email"]))
    for t in out:                                    # maintenance : e-mail jamais coupable
        if out[t]["verrou"]:
            out[t]["email"] = True
    return out


def set_pref(db: Session, cid: int, pref_type: str, *, cloche: bool, email: bool) -> None:
    from ..notif_registry import TYPES_CLIENT, desactivable
    if pref_type not in TYPES_CLIENT:
        return
    if not desactivable(pref_type):                  # maintenance : e-mail non désactivable
        email = True
    db.execute(text(
        "INSERT INTO notif_canaux (compte_id, pref_type, cloche, email) VALUES (:c,:p,:cl,:em) "
        "ON CONFLICT (compte_id, pref_type) DO UPDATE SET cloche=:cl, email=:em"),
        {"c": cid, "p": pref_type, "cl": cloche, "em": email})


def desabonner_email(db: Session, cid: int) -> None:
    """Désinscription e-mail GLOBALE (lien légal / List-Unsubscribe) : coupe l'e-mail des types
    DÉSACTIVABLES (maintenance reste ON — conséquences réelles) ; la cloche reste intacte."""
    from ..notif_registry import TYPES_CLIENT, desactivable
    cur = prefs_compte(db, cid)
    for p in TYPES_CLIENT:
        if desactivable(p):
            set_pref(db, cid, p, cloche=cur[p]["cloche"], email=False)


def _cloche_filter_sql(prefs: dict) -> str:
    """Fragment WHERE excluant les types (registre) dont la CLOCHE est coupée. Le marché partagé
    (compte NULL) reste TOUJOURS visible (flux informatif hors préférences) ; `systeme` jamais exclu."""
    excl = []
    for t, kinds in _KINDS_PAR_PREF.items():
        if t in prefs and not prefs[t]["cloche"]:
            ks = ",".join(f"'{k}'" for k in kinds)
            excl.append(f"NOT (e.kind IN ({ks}) AND e.compte_id IS NOT DISTINCT FROM :cid)")
    return (" AND " + " AND ".join(excl)) if excl else ""


# ─────────────── M85-B · le SUIVI DE PARCELLE (producteur unique, SQL, ZÉRO modèle) ───────────────
# La règle du mandant : « ma parcelle a changé » dit MA parcelle (maille stricte, jamais le secteur —
# le secteur, c'est les veilles de zone). Cinq changements, avec une HIÉRARCHIE :
#   · MUTATION (vente) = l'événement MAJEUR → libellé distinct, en tête ;
#   · BASCULE DE TIER = NOTRE verdict qui change (pas un fait du monde) → formulé comme tel, et
#     seulement les bascules significatives (vers/depuis chaude|brûlante) [traitée dans detect_events] ;
#   · PERMIS, MUTATION, BODACC détectés ICI à chaque ingestion ; ZONAGE par comparaison d'empreinte.
# Dédup par ÉVÉNEMENT (un permis/mutation donné notifie une fois) ; fenêtre = après la pose du suivi
# (pas de backfill). Type de registre : `parcelle_suivie`.
SUIVIS_MAX = 50   # plafond de parcelles suivies par compte (config M85-B)


def _ensure_suivi_cols(db: Session) -> None:
    db.execute(text("ALTER TABLE watched_parcels ADD COLUMN IF NOT EXISTS zone_snap varchar(64)"))


def evaluer_suivis(db: Session) -> dict:
    """Pour chaque parcelle suivie, détecte les changements SUR elle depuis la pose du suivi et crée des
    notifications typées `parcelle_suivie` (dédupliquées par événement). Cronable (à chaque ingestion).
    ZÉRO modèle. Retourne le compte par catégorie."""
    _ensure_suivi_cols(db)
    court = lambda idu: idu[8:] if idu and len(idu) > 8 else idu   # noqa: E731 — libellé court
    suivis = db.execute(text(
        "SELECT idu, compte_id, created_at, zone_snap FROM watched_parcels WHERE idu IS NOT NULL")).mappings().all()
    out = {"mutation": 0, "permis": 0, "bodacc": 0, "zonage": 0}
    for s in suivis:
        idu, cid, depuis = s["idu"], s["compte_id"], s["created_at"]
        # 1) MUTATION (vente) — l'événement majeur, libellé distinct « Vente ».
        for m in db.execute(text(
                "SELECT id_mutation, date_mutation, valeur_fonciere, nature_mutation "
                "FROM dvf_mutations_parcelle WHERE id_parcelle = :idu AND date_mutation >= :d"),
                {"idu": idu, "d": depuis}).mappings():
            prix = f" — {int(m['valeur_fonciere']):,} €".replace(",", " ") if m["valeur_fonciere"] else ""
            out["mutation"] += 1 if creer_notification(
                db, kind="parcelle_suivie", compte_id=cid, source="Mutation", idu=idu,
                titre=f"Vente : votre parcelle {court(idu)} a changé de mains",
                detail=f"Mutation du {m['date_mutation']}{prix} ({m['nature_mutation'] or 'vente'}).",
                lien=f"/socle/#parcelle={idu}", dedup=f"suivi:mut:{idu}:{m['id_mutation']}") else 0
        # 2) PERMIS SUR la parcelle (idu_codes contient l'idu) — jamais la proximité (secteur = veille).
        for p in db.execute(text(
                "SELECT permit_id, type, date_depot FROM sitadel_permits "
                "WHERE idu_codes @> to_jsonb(CAST(:idu AS text)) AND date_depot >= :d"),
                {"idu": idu, "d": depuis}).mappings():
            out["permis"] += 1 if creer_notification(
                db, kind="parcelle_suivie", compte_id=cid, source="Permis", idu=idu,
                titre=f"Nouveau permis sur votre parcelle {court(idu)}",
                detail=f"{p['type']} {p['permit_id']} déposé le {p['date_depot']}.",
                lien=f"/socle/#parcelle={idu}",
                # #3 — fait UNIQUE (idu, permit_id) : dédup PERMANENTE, un rejeu ne recrée jamais le doublon.
                dedup=f"suivi:permis:{idu}:{p['permit_id']}", permanent=True) else 0
        # 3) BODACC sur le propriétaire (personne morale) de la parcelle.
        for b in db.execute(text(
                "SELECT bp.annonce_id, bp.type_procedure, bp.date_annonce, pm.denomination "
                "FROM parcelle_personne_morale pm JOIN bodacc_procedures bp ON bp.siren = pm.siren "
                "WHERE pm.idu = :idu AND pm.siren IS NOT NULL AND bp.date_annonce >= :d"),
                {"idu": idu, "d": depuis}).mappings():
            out["bodacc"] += 1 if creer_notification(
                db, kind="parcelle_suivie", compte_id=cid, source="BODACC", idu=idu,
                titre=f"Procédure sur le propriétaire de {court(idu)}",
                detail=f"{b['type_procedure']} publiée le {b['date_annonce']} — {b['denomination'] or 'propriétaire'}.",
                lien=f"/socle/#parcelle={idu}", dedup=f"suivi:bodacc:{idu}:{b['annonce_id']}") else 0
        # 4) ZONAGE — comparaison d'empreinte (le zonage n'a pas de date ; on compare au dernier vu).
        zone = db.execute(text("SELECT zone_lib FROM parcel_zone_plu WHERE idu = :idu"),
                          {"idu": idu}).scalar()
        snap = s["zone_snap"]
        if zone is not None and snap is not None and zone != snap:
            out["zonage"] += 1 if creer_notification(
                db, kind="parcelle_suivie", compte_id=cid, source="Zonage", idu=idu,
                titre=f"Changement de zonage sur votre parcelle {court(idu)}",
                detail=f"Le zonage PLU est passé de « {snap} » à « {zone} ».",
                lien=f"/socle/#parcelle={idu}", dedup=f"suivi:zone:{idu}:{zone}") else 0
        if zone is not None and zone != snap:                # mémorise l'empreinte courante
            db.execute(text("UPDATE watched_parcels SET zone_snap = :z WHERE idu = :idu AND compte_id IS NOT DISTINCT FROM :c"),
                       {"z": zone, "idu": idu, "c": cid})
    return out


# ───────────────────────── détection (le job cronable) ─────────────────────────

def run_precedent_servi(db: Session, servi: str = RUN) -> str | None:
    """Fix veille-notifs #4 — le run de référence du REJEU vient de la TABLE DES RUNS (le dernier run
    calculé AVANT le servi), JAMAIS d'une constante (fini le q_v9_m81 codé en dur du rejeu). None si le
    servi est le seul run connu."""
    return db.execute(text(
        "SELECT run_id FROM p_score_v2_runs WHERE run_id <> :s ORDER BY computed_at DESC LIMIT 1"),
        {"s": servi}).scalar()


def detect_events(db: Session, run_from: str, run_to: str, demo: bool = False,
                  rattrapage: bool = False) -> dict:
    """Diffe deux runs → événements. Idempotent par (kind, idu, run_from, run_to).

    M137-M — `rattrapage` : les bascules d'un run PASSÉ rejoué (ex. rattrapage q_v9→q_v10 après un
    correctif) sont marquées `envoi_statut='rattrapage'` → EXCLUES du digest e-mail (jamais 808 mails
    « arrivés ce matin ») mais visibles à la cloche/page événements, étiquetées « (rattrapage) »."""
    inserted = {"bascule": 0, "bodacc": 0, "permis": 0}
    _es = "rattrapage" if rattrapage else "na"
    _tag = " (rattrapage)" if rattrapage else ""

    # 1. bascules de TIER V2 (M137-M) : « notre verdict qui change » = parcel_p_score_v2.tier, pas la
    # matrice morte. Bornées aux bascules SIGNIFICATIVES (entrée/sortie d'un tier prioritaire) pour ne
    # pas inonder la cloche du remue-ménage des declasse_*. Les DEUX runs vivent dans parcel_p_score_v2.
    rows = db.execute(text("""
        SELECT p.idu, a.tier AS de, b.tier AS vers
        FROM parcel_p_score_v2 a
        JOIN parcel_p_score_v2 b ON b.parcelle_id = a.parcelle_id AND b.run_id = :to
        JOIN parcels p ON p.idu = a.parcelle_id
        WHERE a.run_id = :from AND a.tier IS DISTINCT FROM b.tier
          AND (a.tier = ANY(:prio) OR b.tier = ANY(:prio))"""),
        {"from": run_from, "to": run_to, "prio": list(_TIERS_PRIORITE)}).mappings().all()
    for r in rows:
        up = _monte(r["de"], r["vers"])
        n = db.execute(text("""
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo, envoi_statut)
            SELECT 'bascule', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean), CAST(:es AS varchar)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bascule' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"{'▲' if up else '▼'} {r['idu'][8:]} : {_tier_court(r['de'])} → {_tier_court(r['vers'])}",
             "detail": f"Classement passé de « {_tier_court(r['de'])} » à « {_tier_court(r['vers'])} » au recalcul.{_tag}",
             "from": run_from, "to": run_to, "demo": demo, "es": _es}).rowcount
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
            INSERT INTO event_log (kind, idu, titre, detail, run_from, run_to, demo, envoi_statut)
            SELECT 'bodacc', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text), CAST(:from AS varchar), CAST(:to AS varchar), CAST(:demo AS boolean), CAST(:es AS varchar)
            WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='bodacc' AND idu=:idu
                              AND run_from=:from AND run_to=:to)"""),
            {"idu": r["idu"], "titre": f"● BODACC : procédure ouverte sur {r['idu'][8:]}",
             "detail": f"Procédure collective ouverte (BODACC) détectée au recalcul.{_tag}",
             "from": run_from, "to": run_to, "demo": demo, "es": _es}).rowcount
        inserted["bodacc"] += n

    # 2 bis. VEILLES : une bascule vers un statut « montant » qui MATCHE une recherche sauvegardée
    # → notification nominative (M11 : « une recherche filtrée nommée = une veille »).
    _veilles_match(db, run_to, demo, rattrapage=rattrapage)

    # 3. M85-B — BASCULE DE TIER sur une parcelle SUIVIE = NOTRE VERDICT qui change (jamais un fait du
    # monde réel). Seulement les bascules SIGNIFICATIVES (vers/depuis 'chaude', le tier prioritaire).
    # REMPLACE l'ancien bloc « permis ≤ 300 m » : la proximité est un fait de SECTEUR, pas de parcelle —
    # c'est ce que couvrent les veilles de zone. « Permis à proximité » (opt-in, rayon choisi) → BACKLOG.
    # Les changements SUR la parcelle (permis/mutation/BODACC/zonage) sont produits par evaluer_suivis
    # à chaque ingestion — ici, uniquement le verdict de classement (qui dépend d'un diff de run).
    rows = db.execute(text("""
        SELECT p.idu, w.compte_id, a.tier AS de, b.tier AS vers
        FROM parcel_p_score_v2 a
        JOIN parcel_p_score_v2 b ON b.parcelle_id = a.parcelle_id AND b.run_id = :to
        JOIN parcels p ON p.idu = a.parcelle_id
        JOIN watched_parcels w ON w.idu = p.idu
        WHERE a.run_id = :from AND a.tier IS DISTINCT FROM b.tier
          AND (a.tier = ANY(:prio) OR b.tier = ANY(:prio))"""),
        {"from": run_from, "to": run_to, "prio": list(_TIERS_PRIORITE)}).mappings().all()
    for r in rows:
        sens = "passée en" if _monte(r["de"], r["vers"]) else "redescendue en"
        inserted["permis"] += creer_notification(
            db, kind="parcelle_suivie", compte_id=r["compte_id"], source="Classement", idu=r["idu"],
            titre=f"Le classement de votre parcelle {r['idu'][8:]} a évolué",
            detail=("Suite à une mise à jour de NOS données, votre parcelle est "
                    f"{sens} « {_tier_court(r['vers'])} » (auparavant « {_tier_court(r['de'])} »). Ce n'est pas "
                    f"un événement extérieur : c'est notre analyse qui a changé.{_tag}"),
            lien=f"/socle/#parcelle={r['idu']}", dedup=f"suivi:tier:{r['idu']}:{run_to}", demo=demo,
            envoi_statut=_es)
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


def _veilles_match(db: Session, run_to: str, demo: bool, rattrapage: bool = False) -> int:
    # Batch : on parcourt TOUTES les veilles (tous comptes), et chaque événement produit est
    # attribué au COMPTE propriétaire de la veille (v["compte_id"]) — jamais partagé.
    veilles = db.execute(text("SELECT id, nom, hash, compte_id FROM saved_searches")).mappings().all()
    if not veilles:
        return 0
    # bascules « montantes » de CE diff (déjà en event_log, kind=bascule, run_to)
    # M137-M : le statut servi lu ici = parcel_p_score_v2.tier au run_to (plus matrice_statut morte).
    # q_score retiré (matrice morte) : le critère de veille `q` (seuil de score matrice) n'existe plus
    # côté front (scoreMin retiré) → f["q"] est toujours None ; on ne lit ni ne filtre plus dessus.
    rows = db.execute(text("""
        SELECT e.idu, p.commune, p.surface_m2, s2.tier, r.sdp_residuelle_m2,
               EXISTS (SELECT 1 FROM dryrun_cascade_results cr WHERE cr.run_label = :to
                       AND cr.parcel_id = p.id AND cr.evenement = 'rouge') AS a_evenement
        FROM event_log e
        JOIN parcels p ON p.idu = e.idu
        JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :to
        LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
        WHERE e.kind = 'bascule' AND e.run_to = :to AND e.titre LIKE '▲%'"""),
        {"to": run_to}).mappings().all()
    n = 0
    for v in veilles:
        f = _parse_hash_filters(v["hash"])
        for r in rows:
            if f["st"] and r["tier"] not in f["st"]:
                continue
            if f["cm"] and r["commune"] not in f["cm"]:   # M17-B : commune honorée
                continue
            if f["ev"] and not r["a_evenement"]:
                continue
            if f["smin"] is not None and (r["surface_m2"] or 0) < f["smin"]:
                continue
            if f["smax"] is not None and (r["surface_m2"] or 0) > f["smax"]:
                continue
            if f["sdp"] is not None and (r["sdp_residuelle_m2"] or 0) < f["sdp"]:
                continue
            n += db.execute(text("""
                INSERT INTO event_log (kind, idu, titre, detail, run_to, demo, compte_id, envoi_statut)
                SELECT 'veille', CAST(:idu AS varchar), CAST(:titre AS varchar), CAST(:detail AS text),
                       CAST(:to AS varchar), CAST(:demo AS boolean), :cid, CAST(:es AS varchar)
                WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE kind='veille' AND idu=:idu AND titre=:titre
                                  AND compte_id IS NOT DISTINCT FROM :cid)"""),
                {"idu": r["idu"], "titre": f"🔭 Veille « {v['nom']} » : {r['idu'][8:]} correspond",
                 "detail": f"Passée en « {_tier_court(r['tier'])} » — correspond à votre veille."
                           + (" (rattrapage)" if rattrapage else ""),
                 "to": run_to, "demo": demo, "cid": v["compte_id"],
                 "es": ("rattrapage" if rattrapage else "na")}).rowcount
    return n


def seed_demo(db: Session) -> dict:
    """Run de DÉMONSTRATION `q_v2_demo` : copie du run servi sur 8 parcelles avec le TIER V2 modifié,
    ÉTIQUETÉ démo — pour voir le système vivre avant le prochain run réel de scoring.
    M137-M : la démo bâtit un run `parcel_p_score_v2` (le tier v2, source de la bascule), plus la
    matrice morte — 5 montées (a_creuser → chaude, ▲) et 3 descentes (chaude → a_creuser, ▼)."""
    db.execute(text("DELETE FROM event_log WHERE demo"))  # démo REJOUABLE : la cloche se rallume
    db.execute(text("DELETE FROM parcel_p_score_v2 WHERE run_id = 'q_v2_demo'"))
    db.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE run_label = 'q_v2_demo'"))
    _cols = ("parcelle_id, p_raw, mult_base, percentile, rang, contrib_z, contrib_d, "
             "top5_contributions, copro, model_version, event_date")
    # 5 MONTÉES : des a_creuser du run servi promues 'chaude' dans le run démo → bascule ▲
    db.execute(text(f"""
        INSERT INTO parcel_p_score_v2 (run_id, tier, {_cols})
        SELECT 'q_v2_demo', 'chaude', {_cols} FROM parcel_p_score_v2
        WHERE run_id = :run AND tier = 'a_creuser' AND NOT copro
        ORDER BY rang ASC LIMIT 5"""), {"run": RUN})
    # 3 DESCENTES : des chaude du run servi rétrogradées 'a_creuser' → bascule ▼
    db.execute(text(f"""
        INSERT INTO parcel_p_score_v2 (run_id, tier, {_cols})
        SELECT 'q_v2_demo', 'a_creuser', {_cols} FROM parcel_p_score_v2
        WHERE run_id = :run AND tier = 'chaude' AND NOT copro
        ORDER BY rang DESC LIMIT 3"""), {"run": RUN})
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
# M85-B — kinds PERSO éligibles au DIGEST du matin (chaînes 1+2) : suivi de parcelle + veille de zone
# (historiques permis/veille + nouveaux types de registre). annonce/maintenance sont IMMÉDIATS (chaîne
# 3), hors digest ; systeme_pilote = cloche seule.
_PERSO_KINDS = ("permis", "veille", "parcelle_suivie", "veille_zone")


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
def list_events(request: Request, unread_only: bool = False,
                limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),   # FIX-C5 GB-034
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
               e.demo, e.source, e.lien, p.commune AS commune,
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
    # M85-B — plafond de parcelles suivies par compte (config), garde-fou anti-emballement.
    n = db.execute(text("SELECT count(*) FROM watched_parcels WHERE compte_id IS NOT DISTINCT FROM :cid"),
                   {"cid": cid}).scalar() or 0
    if n >= SUIVIS_MAX:
        raise HTTPException(409, f"Plafond de {SUIVIS_MAX} parcelles suivies atteint — retirez-en une.")
    db.execute(text("INSERT INTO watched_parcels (idu, compte_id) VALUES (:i, :cid)"), {"i": idu, "cid": cid})
    return {"watched": True}


@router.get("/suivis")
def suivis_liste(request: Request, db: Session = Depends(get_db)) -> dict:
    """M85-B — les parcelles SUIVIES du compte + la date du DERNIER changement détecté. Une parcelle
    qui n'a jamais bougé le DIT (dernier_changement = null) — c'est une information, pas un vide."""
    from .tenant import current_compte
    cid = current_compte(request)
    rows = db.execute(text("""
        SELECT w.idu, w.created_at::date::text AS depuis, p.commune,
               (SELECT max(e.ts)::date::text FROM event_log e
                 WHERE e.idu = w.idu AND e.kind = 'parcelle_suivie'
                   AND e.compte_id IS NOT DISTINCT FROM :cid) AS dernier_changement
        FROM watched_parcels w LEFT JOIN parcels p ON p.idu = w.idu
        WHERE w.compte_id IS NOT DISTINCT FROM :cid
        ORDER BY dernier_changement DESC NULLS LAST, w.created_at DESC"""),
        {"cid": cid}).mappings().all()
    return {"suivis": [dict(r) for r in rows], "plafond": SUIVIS_MAX}


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
_TRIGGERS_TXT = ("Aujourd'hui, une veille vous alerte quand une parcelle MONTE dans le classement "
                 "(passe en Priorité ou À suivre), éventuellement filtrée par commune, surface, SDP ou "
                 "procédure BODACC. Reformulez vers l'un de ces déclencheurs — ex. « les grandes "
                 "parcelles à Saint-Paul qui passent en Priorité ».")


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
    # FIX-SCOREMIN : `scoreMin` retiré du récap — le matcher de veille (_veilles_match) ne l'a
    # jamais lu (q_score matrice morte) ; l'annoncer « potentiel ≥ N » promettait un déclencheur
    # qui ne se déclenchait pas. On ne le lit plus, donc on ne le promet plus.
    trig = {"tiers": tiers, "communes": communes, "evenement": bool(fr.get("evenement")),
            "surfaceMin": fr.get("surfaceMin"),
            "surfaceMax": fr.get("surfaceMax"), "sdpMin": fr.get("sdpMin")}
    if not (tiers or communes or trig["evenement"]
            or trig["surfaceMin"] or trig["surfaceMax"] or trig["sdpMin"]):
        return {"ok": False, "refus": f"Je n'ai pas su en tirer un critère déclenchable. {_TRIGGERS_TXT}"}
    # 4) résumé lisible (ce que la veille fera VRAIMENT) — vocabulaire SERVI = chips (M135/M137),
    #    jamais « brûlante/chaude » : mapping canonique tiers_client.court().
    bits = []
    if tiers:
        bits.append("passe en " + " / ".join(_tier_court(t) or t for t in tiers))
    else:
        bits.append("monte dans le classement (passe en Priorité ou À suivre)")
    if communes:
        bits.append("à " + ", ".join(communes))
    if trig["surfaceMin"]:
        bits.append(f"surface ≥ {trig['surfaceMin']} m²")
    if trig["surfaceMax"]:
        bits.append(f"surface ≤ {trig['surfaceMax']} m²")
    if trig["sdpMin"]:
        bits.append(f"SDP ≥ {trig['sdpMin']} m²")
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


def _digest_data(db: Session, cid: int | None = None, jours: int = 7) -> dict:
    # PERSONNEL : listé en détail, CLOISON STRICTE (le marché n'apparaît PAS ici). M85-B : fenêtre
    # paramétrable (J-1 pour le digest quotidien du matin). ORDRE (hiérarchie du mandant) : la MUTATION
    # d'abord (événement majeur), puis les autres changements de parcelle SUIVIE, puis les veilles de zone.
    events = db.execute(text("""
        SELECT e.kind, e.idu, e.titre, e.detail, e.demo, e.source, d.q_score, d.a_score, d.matrice_statut
        FROM event_log e
        LEFT JOIN parcels p ON p.idu = e.idu
        LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE e.ts >= now() - make_interval(days => :jours)
          AND e.compte_id IS NOT DISTINCT FROM :cid AND e.kind = ANY(:perso)
          AND e.envoi_statut IS DISTINCT FROM 'rattrapage'   -- M137-M : le rattrapage vit à la cloche, jamais au digest/mail
        ORDER BY (e.source = 'Mutation') DESC, (e.kind = 'parcelle_suivie') DESC,
                 e.ts DESC NULLS LAST LIMIT 20"""),
        {"run": RUN, "cid": cid, "perso": list(_PERSO_KINDS), "jours": jours}).mappings().all()
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


# ─────────────── M85 Phase 3 · le BRIEF DU MATIN (déterministe, zéro modèle) ───────────────

def brief_matin(db: Session, cid: int | None) -> dict:
    """La veille RACONTÉE, chaque matin — DÉTERMINISTE (des comptes et des listes, jamais de la prose
    générée ; ZÉRO modèle). Deux parties : (1) les veilles déclenchées récemment (24 h), (2) « depuis
    hier sur vos secteurs suivis » = nouveaux permis dans VOS communes, MÊME point de calcul que le bloc
    « cette semaine » de M83 (`sitadel_permits.date_depot`, aucun recalcul). HONNÊTE : si tout est à
    zéro (souvent, tant que les crons d'ingestion ne tournent pas), le brief le DIT et n'invente rien."""
    veilles = db.execute(text(
        "SELECT titre, detail, ts::text AS ts, lien, source FROM event_log "
        "WHERE kind='veille' AND compte_id IS NOT DISTINCT FROM :c AND ts >= now() - interval '24 hours' "
        "ORDER BY ts DESC LIMIT 20"), {"c": cid}).mappings().all()
    communes = _mes_communes(db, cid)
    permis_max = db.execute(text("SELECT max(date_depot) FROM sitadel_permits")).scalar()
    permis_hier = 0
    if communes:
        permis_hier = db.execute(text(
            "SELECT count(*) FROM sitadel_permits WHERE date_depot > now()::date - 1 "
            "AND commune = ANY(:coms)"), {"coms": communes}).scalar() or 0
    donnee_perimee = bool(permis_max and (date.today() - permis_max).days > 2)   # ingestion en attente ?
    # M87 P6 — la barre « N événements depuis hier » et le panneau latéral. Point de lecture UNIQUE :
    # event_log (fenêtre J-1, kinds perso) — MÊME source que le digest Brevo, pas deux fenêtres qui
    # divergent. Groupé par commune (maquette : une ligne par commune + « Voir les N → »).
    # M97 G3 (tranché par la mesure, 17/08/2026) : la ligne secteur ci-dessus (lecture DIRECTE de
    # sitadel_permits, M83) est un DOUBLE TUYAU assumé — event_log ne contient AUCUN événement permis
    # réel (mesure : 0 kind permis hors démo ; seuls 15 veille + 1 systeme), la chaîne evaluer_suivis
    # n'a jamais produit de permis ici. À SUPPRIMER quand le cron VPS evaluer-suivis alimentera
    # event_log en permis (critère : ≥1 événement permis réel hors seed) — sinon double-compte.
    # Voir audit M96 G3 (docs/audits/AUDIT_M96_TUYAUTERIE.md §1.4).
    groupes = db.execute(text(
        "SELECT COALESCE(p.commune, '—') AS commune, count(*) AS n, max(e.ts)::text AS ts_max, "
        "  (array_agg(DISTINCT e.idu) FILTER (WHERE e.idu IS NOT NULL))[1:3] AS idus, "
        "  (array_agg(DISTINCT e.source) FILTER (WHERE e.source IS NOT NULL)) AS sources "
        "FROM event_log e LEFT JOIN parcels p ON p.idu = e.idu "
        "WHERE e.ts >= now() - interval '24 hours' "
        "  AND e.compte_id IS NOT DISTINCT FROM :c AND e.kind = ANY(:perso) AND NOT e.demo "
        "GROUP BY COALESCE(p.commune, '—') ORDER BY max(e.ts) DESC"),
        {"c": cid, "perso": list(_PERSO_KINDS)}).mappings().all()
    n_evenements = sum(r["n"] for r in groupes) + int(permis_hier)
    vide = (len(veilles) == 0 and permis_hier == 0)
    cause = None
    if vide:
        if not communes:
            cause = "Vous ne suivez encore aucun secteur — suivez des parcelles pour un brief ciblé."
        elif donnee_perimee:
            cause = (f"Rien de neuf depuis hier, et les permis sont figés au {permis_max} : "
                     "l'ingestion quotidienne n'a pas encore tourné. Le brief se remplira dès que les "
                     "crons d'ingestion seront actifs (VPS).")
        else:
            cause = "Rien de nouveau sur vos secteurs depuis hier."
    return {
        "genere_le": datetime.now(REUNION_TZ).isoformat(timespec="minutes"),   # 7h Réunion (UTC+4)
        "veilles": [dict(r) for r in veilles],
        "secteurs": {"communes": communes, "permis_depuis_hier": int(permis_hier),
                     "derniere_donnee_permis": str(permis_max) if permis_max else None,
                     "donnee_perimee": donnee_perimee},
        "n": int(n_evenements),                       # M87 P6 — le compteur de la barre (0 → « rien de neuf »)
        "groupes": [dict(r) for r in groupes],        # M87 P6 — une ligne par commune pour le panneau latéral
        "vide": vide, "cause_vide": cause,
    }


@router.get("/brief")
def brief(request: Request, db: Session = Depends(get_db)) -> dict:
    """Le brief du matin du compte courant — servi au Copilote (carte d'accueil) et repris au digest."""
    from .tenant import current_compte
    return brief_matin(db, current_compte(request))


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
    # M85-B — le marché SORT du digest (règle mandant : mail SSI parcelle suivie / zone / annonce —
    # « rien d'autre »). Il reste un flux cloche informatif, jamais un e-mail.
    return digest_html_email(evs, {"total": 0}, d.get("top_chaudes", []), lien_desabo, lien_prefs,
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


# Domaines d'adresses FACTICES : jamais un envoi réel vers elles (protection réputation Brevo). La
# vraie hygiène — ne PAS créer de comptes actifs à adresse placeholder — est au BACKLOG ; ceci est la
# ceinture de sécurité côté expédition.
_DOMAINES_PLACEHOLDER = frozenset({"test.com", "example.com", "example.org", "example.net",
                                   "labuse.test", "test.test", "localhost", "invalid", "email.com"})


def _adresse_placeholder(email: str | None) -> bool:
    e = (email or "").strip().lower()
    dom = e.rsplit("@", 1)[-1] if "@" in e else ""
    return (not dom) or dom in _DOMAINES_PLACEHOLDER or e.startswith("ton-email@")


def envoyer_digests(db: Session, *, base_url: str = "", freq: str = "quotidien", force: bool = False,
                    dry_run: bool = False) -> dict:
    """Envoie le digest aux comptes actifs, FILTRÉ par préférence e-mail (par type/canal). Garanties :
    anti-double-envoi (last_digest_at + intervalle mini), un digest VIDE ne part pas, désinscription +
    préférences dans chaque e-mail (légal), statut d'envoi tracé (jamais silencieux — motif M84).
    Fuseau explicite UTC+4 pour la fenêtre quotidienne (jamais hérité de la machine)."""
    from ..emails import digest_html_email, digest_notifications
    from ..mail import send_email

    interval_h = 20 if freq == "quotidien" else 24 * 6   # quotidien ≈ 20 h ; hebdo ≈ 6 j
    fenetre_jours = 1 if freq == "quotidien" else 7      # M85-B — J-1 pour le digest du matin
    now = datetime.now(timezone.utc)
    periode = "hier" if freq == "quotidien" else "cette semaine"
    # LEFT JOIN (pas INNER) : un compte actif SANS utilisateur titulaire n'est plus SILENCIEUSEMENT
    # exclu — il apparaît avec email=NULL et un motif « pas d'adresse ». Le silence est le défaut qu'on
    # ferme partout : chaque compte reçoit un STATUT + un MOTIF explicites (Vic, M85).
    recipients = db.execute(text(
        "SELECT c.id AS cid, min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id = c.id "
        "WHERE c.statut = 'actif' GROUP BY c.id ORDER BY c.id")).mappings().all()
    envoyes = ignores = echecs = simules = 0
    details: list[dict] = []

    def _note(cid, email, statut, motif, corps=None):
        d = {"compte": cid, "email": email, "statut": statut, "motif": motif}
        if corps is not None:
            d["corps"] = corps[:600]   # #2 — aperçu du corps réel (dry-run : ce qui SERAIT envoyé)
        details.append(d)

    for r in recipients:
        cid, email = r["cid"], r["email"]
        if not email or not str(email).strip():
            ignores += 1
            _note(cid, email, "ignoré", "pas d'adresse (aucun utilisateur titulaire avec e-mail)")
            continue
        if _adresse_placeholder(email):
            # DÉFENSE réputation (Vic M85) : jamais un ENVOI RÉEL vers une adresse factice — Brevo
            # compterait l'envoi et le bounce dégraderait la réputation du domaine. On refuse ICI.
            ignores += 1
            _note(cid, email, "ignoré", "adresse placeholder — envoi bloqué (jamais un envoi réel vers une adresse factice)")
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
            # GB-020 — `last` (timestamptz) était libellé « UTC » mais rendu en +04 par le driver (4 h
            # d'écart dans le texte). On l'exprime EXPLICITEMENT en heure Réunion (doctrine M85, REUNION_TZ).
            _note(cid, email, "ignoré",
                  f"anti-double-envoi (dernier digest {last.astimezone(REUNION_TZ):%Y-%m-%d %H:%M} heure Réunion)")
            continue
        data = _digest_data(db, cid, jours=fenetre_jours)   # M85-B — fenêtre J-1 pour le quotidien
        # FILTRE par préférence e-mail PAR TYPE (registre) : un type dont l'e-mail est coupé n'entre pas.
        evs = [e for e in data["evenements"]
               if not e.get("demo") and prefs.get(_pref_type(e["kind"]), {}).get("email")]
        # M85-B — le marché SORT du digest (règle mandant : « rien d'autre »). Flux cloche seulement.
        marche = {"total": 0}
        # M85 P3 — enrichissement « depuis hier sur vos secteurs » (permis dans vos communes suivies,
        # même point de calcul que M83). Ligne présente SEULEMENT si non-nulle (honnêteté : pas de
        # remplissage — cf. le retard d'ingestion qui la garde souvent vide).
        sect = brief_matin(db, cid)["secteurs"]
        secteurs_ligne = (f"Depuis hier sur vos secteurs : {sect['permis_depuis_hier']} nouveau(x) permis "
                          f"dans {', '.join(sect['communes'][:5])}." if sect["permis_depuis_hier"] else "")
        if not evs and not marche.get("total") and not secteurs_ligne:
            ignores += 1
            _note(cid, email, "ignoré", "aucune notification en attente (rien d'e-mail-activé sur 7 j + marché + secteurs vides)")
            continue
        tok = _notif_token(db, cid)
        lien_desabo = f"{base_url}/events/desabonner?c={cid}&t={tok}"
        lien_prefs = f"{base_url}/events/preferences?c={cid}&t={tok}"
        sujet, corps = digest_notifications(evs, lien_desabo, base_url=base_url, marche=marche,
                                            periode=periode, lien_prefs=lien_prefs, secteurs_ligne=secteurs_ligne)
        html = digest_html_email(evs, marche, data.get("top_chaudes", []), lien_desabo, lien_prefs,
                                 base_url=base_url, periode=periode, secteurs_ligne=secteurs_ligne)
        # RFC 8058 — désinscription EN UN CLIC (mieux traitée par Gmail qu'un simple lien) : l'URL
        # accepte le POST `List-Unsubscribe=One-Click`. AUCUN en-tête de campagne (X-Campaign, List-ID
        # marketing…) : ce mail est TRANSACTIONNEL, pas une newsletter.
        if dry_run:
            # #2 — DRY-RUN : rend ce qui SERAIT envoyé (destinataire, sujet, corps) SANS appeler Brevo
            # ni avancer last_digest_at. C'est la brique de recette VPS (tester ≠ envoyer).
            simules += 1
            _note(cid, email, "simulé", f"{len(evs)} événement(s) — sujet « {sujet} »", corps=corps)
            continue
        res = send_email(email, sujet, corps, body_html=html,
                         headers={"List-Unsubscribe": f"<{lien_desabo}>",
                                  "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"})
        if res.ok:
            envoyes += 1
            _note(cid, email, "envoyé", f"{len(evs)} événement(s)" + (f" + {marche['total']} marché" if marche.get("total") else ""))
            # #5 — last_digest_at n'avance QUE si l'envoi a RÉUSSI : un échec Brevo ne se déguise plus en
            # « déjà envoyé » (l'anti-double-envoi laisse donc le prochain cron réessayer).
            db.execute(text("INSERT INTO notif_prefs (compte_id, last_digest_at) VALUES (:c,:n) "
                            "ON CONFLICT (compte_id) DO UPDATE SET last_digest_at=:n"), {"c": cid, "n": now})
        else:                                                  # #5 — échec VISIBLE : loggé en clair + compté, jamais avalé
            echecs += 1
            _note(cid, email, "échec", f"envoi refusé : {res.detail}")
            log.error("DIGEST ÉCHEC ENVOI — compte=%s email=%s cause=%s (last_digest_at NON avancé → réessai)",
                      cid, email, res.detail)
    db.commit()
    return {"envoyes": envoyes, "ignores": ignores, "echecs": echecs, "simules": simules,
            "dry_run": dry_run, "details": details}


# ─────────────── M85-B · l'ANNONCE (chaîne 3) : aperçu obligatoire, test à soi, trace ───────────────

def apercu_annonce(db: Session, *, type_: str, titre: str, corps: str, lien: str | None = None,
                   debut: str = "", fin: str = "", duree: str = "") -> dict:
    """APERÇU (sujet + texte) + nombre de destinataires, SANS envoyer. Obligatoire avant tout envoi
    réel — le mandant relit ce qui partira."""
    from ..emails import annonce_email, maintenance_email
    if type_ == "maintenance":
        sujet, txt, _ = maintenance_email(titre, corps, debut=debut, fin=fin, duree=duree)
    else:
        sujet, txt = annonce_email(titre, corps, lien=lien)
    n = db.execute(text(
        "SELECT count(DISTINCT c.id) FROM comptes c JOIN utilisateurs u ON u.compte_id=c.id "
        "AND u.role='titulaire' WHERE c.statut='actif'")).scalar() or 0
    return {"sujet": sujet, "texte": txt, "n_destinataires": int(n)}


def envoyer_annonce(db: Session, *, type_: str, titre: str, corps: str, lien: str | None = None,
                    base_url: str = "", envoye_par: str = "pilote", test_email: str | None = None,
                    debut: str = "", fin: str = "", duree: str = "") -> dict:
    """Envoie une ANNONCE (chaîne 3) → cloche + mail à TOUS les comptes actifs (ciblage v1 ; segments →
    BACKLOG). `test_email` = envoi UNIQUE de test à soi, sans cloche ni trace. Sinon : cloche typée +
    mail respectant les préférences (annonce désactivable ; maintenance NON), puis TRACE (qui/quoi/quand/
    destinataires/statut). `type_` ∈ {annonce_produit, maintenance} (déclaré au registre)."""
    from ..emails import annonce_email, annonce_html, maintenance_email
    from ..mail import send_email
    from ..notif_registry import est_declare
    if type_ not in ("annonce_produit", "maintenance") or not est_declare(type_):
        raise ValueError(f"type d'annonce invalide : {type_!r}")

    def _build(cid):
        if type_ == "maintenance":
            sujet, txt, html = maintenance_email(titre, corps, debut=debut, fin=fin, duree=duree)
            return sujet, txt, html, {}          # maintenance : PAS de désinscription (non désactivable)
        tok = _notif_token(db, cid) if cid is not None else "x"
        desabo = f"{base_url}/events/desabonner?c={cid}&t={tok}" if cid is not None else ""
        prefs_l = f"{base_url}/events/preferences?c={cid}&t={tok}" if cid is not None else ""
        sujet, txt = annonce_email(titre, corps, lien=lien, lien_desabo=desabo, lien_prefs=prefs_l)
        html = annonce_html(titre, corps, lien=lien, lien_desabo=desabo, lien_prefs=prefs_l)
        headers = ({"List-Unsubscribe": f"<{desabo}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
                   if desabo else {})
        return sujet, txt, html, headers

    if test_email:                               # ENVOI DE TEST à soi, AVANT le vrai (obligatoire)
        sujet, txt, html, _ = _build(None)
        res = send_email(test_email, "[TEST] " + sujet, txt, body_html=html)
        return {"test": True, "email": test_email, "statut": "ok" if res.ok else res.detail}

    recipients = db.execute(text(
        "SELECT c.id AS cid, min(u.email) FILTER (WHERE u.role='titulaire') AS email "
        "FROM comptes c LEFT JOIN utilisateurs u ON u.compte_id=c.id "
        "WHERE c.statut='actif' GROUP BY c.id")).mappings().all()
    n_cible = n_mail_ok = n_mail_echec = n_cloche = 0
    for r in recipients:
        cid, email = r["cid"], r["email"]
        n_cible += 1
        prefs = prefs_compte(db, cid)
        if prefs.get(type_, {}).get("cloche", True):    # cloche (respecte la pref ; maintenance toujours)
            n_cloche += 1 if creer_notification(db, kind=type_, compte_id=cid, source="LABUSE",
                titre=titre, detail=corps, lien=lien, dedup=f"annonce:{type_}:{titre}"[:96]) else 0
        if email and not _adresse_placeholder(email) and prefs.get(type_, {}).get("email", True):
            sujet, txt, html, headers = _build(cid)
            res = send_email(email, sujet, txt, body_html=html, headers=headers)
            if res.ok:
                n_mail_ok += 1
            else:
                n_mail_echec += 1
                log.warning("ANNONCE mail échec — compte=%s cause=%s", cid, res.detail)
    db.execute(text(
        "INSERT INTO annonces (type, titre, corps, lien, envoye_par, n_cible, n_mail_ok, n_mail_echec, n_cloche) "
        "VALUES (:t,:ti,:co,:l,:by,:nc,:ok,:ko,:cl)"),
        {"t": type_, "ti": titre, "co": corps, "l": lien, "by": envoye_par,
         "nc": n_cible, "ok": n_mail_ok, "ko": n_mail_echec, "cl": n_cloche})
    db.commit()
    return {"test": False, "n_cible": n_cible, "n_mail_ok": n_mail_ok,
            "n_mail_echec": n_mail_echec, "n_cloche": n_cloche}


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


@router.post("/desabonner", include_in_schema=False)
def desabonner_one_click(c: int, t: str, db: Session = Depends(get_db)) -> dict:
    """RFC 8058 — désinscription EN UN CLIC : le fournisseur (Gmail…) POST sur cette URL, sans page de
    confirmation. Même jeton que le GET. Réponse 200 minimale."""
    if not _token_ok(db, c, t):
        return JSONResponse({"ok": False}, status_code=400)
    desabonner_email(db, c)
    db.commit()
    return {"ok": True}


# ── M85 / M85-B · les PRÉFÉRENCES par type (registre) et par canal ──

def _page_preferences(db: Session, c: int, t: str, sauve: bool = False) -> str:
    from ..notif_registry import TYPES_CLIENT
    prefs = prefs_compte(db, c)
    lignes = ""
    # M125-fix — HTML sorti de la f-string : un backslash (ici les guillemets échappés de l'attribut
    # style) est INTERDIT dans une expression f-string avant Python 3.12. Constante = chaîne normale.
    _span_actif = ' <span style="color:#888;font-size:12px">(toujours actif)</span>'
    for k in TYPES_CLIENT:
        p = prefs[k]
        verrou = p.get("verrou")
        # maintenance : VERROUILLÉ (case e-mail cochée + désactivée + mention « conséquences réelles »).
        em_cell = (f"<input type='checkbox' checked disabled title='Non désactivable — conséquences réelles'>"
                   if verrou else
                   f"<input type='checkbox' name='{k}_email'{' checked' if p['email'] else ''}>")
        lignes += (
            f"<tr><td style='padding:10px 8px;font:14px sans-serif'>{p['label']}"
            f"{_span_actif if verrou else ''}</td>"
            f"<td style='text-align:center;padding:10px 8px'><input type='checkbox' name='{k}_cloche'"
            f"{' checked' if p['cloche'] else ''}></td>"
            f"<td style='text-align:center;padding:10px 8px'>{em_cell}</td></tr>")
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
    from ..notif_registry import TYPES_CLIENT
    form = await request.form()
    for k in TYPES_CLIENT:                               # maintenance : set_pref force l'e-mail (verrou)
        set_pref(db, c, k, cloche=f"{k}_cloche" in form, email=f"{k}_email" in form)
    db.commit()
    return _page_preferences(db, c, t, sauve=True)


@router.get("/entete")
def entete_cloche() -> dict:
    """M87 P5 — libellés de l'en-tête de la cloche, DÉRIVÉS du registre (jamais écrits à la main) : ce
    qu'on sait RÉELLEMENT détecter SUR une parcelle suivie. La cloche les concatène — l'en-tête ne peut
    plus mentir au prochain mandat (plus de « à proximité » figé, mutation et zonage inclus)."""
    from ..notif_registry import libelles_entete_cloche
    return {"libelles": libelles_entete_cloche()}


@router.get("/prefs")
def prefs_get(request: Request, db: Session = Depends(get_db)) -> dict:
    """API in-app : les préférences du compte courant (+ leurs libellés)."""
    from .tenant import current_compte
    cid = current_compte(request)
    from ..notif_registry import TYPES_CLIENT
    p = prefs_compte(db, cid)
    return {"types": [{"key": k, **p[k]} for k in TYPES_CLIENT]}


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
