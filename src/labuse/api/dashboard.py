"""TOUR DE CONTRÔLE (dashboard admin) — capteurs + endpoints /admin/* (mandat DASHBOARD-V1).

D1 — CAPTEURS. L'app s'instrumente, léger et RGPD-sobre : des COMPTEURS, jamais du contenu.
  · usage_events : ouverture d'outil + heartbeat de session (temps d'usage estimé par pas de
    5 min côté client). Fire-and-forget : l'endpoint ne lève JAMAIS (un capteur qui casse une
    requête client serait pire que pas de capteur).
  · retours : bouton « Signaler » de l'app cliente (bug/idée/question + message) → table
    `retours`, statut nouveau/traité/répondu. Notif cloche admin best-effort.
  · ia_budget : la conso IA est attribuée PAR COMPTE dans ia_log (colonne compte_id, posée par
    la garde d'auth via ai.core.poser_compte — réimplémentation propre du WIP fix/ia-modele-budget,
    branche NON mergée : divergée des fichiers remaniés).
  · quota Copilote PAR LICENCE : comptes.copilote_quota_jour (NULL = défaut config 80/jour) —
    lu par la porte NL de /ia (cf. ia.quota_nl_du_compte).
  · actifs/jour : rien à écrire ici — utilisateurs.dernier_login_at (existant) + usage_events.

Tout endpoint /admin/* passe par auth.exiger_admin (403 client, 401 sans session) — le
cloisonnement EXISTANT, réutilisé, jamais un nouveau mécanisme.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

log = logging.getLogger("labuse.dashboard")

router = APIRouter(tags=["dashboard"])

#: types de retours clients (bouton « Signaler ») — libellés courts, jamais de texte libre ici.
RETOUR_TYPES = ("bug", "idee", "question")
RETOUR_STATUTS = ("nouveau", "traite", "repondu")
#: outils/vues comptés — borne de longueur, pas de liste fermée (le front envoie sa clé d'outil ;
#: une clé inconnue reste un compteur honnête, jamais une erreur).
USAGE_KINDS = ("outil", "heartbeat")


def ensure_tables(engine) -> None:
    """Idempotent, appelé au boot (heal résilient FIX-GB-011)."""
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS usage_events ("
            " id bigserial PRIMARY KEY, ts timestamptz DEFAULT now(),"
            " compte_id integer, kind varchar(16) NOT NULL, outil varchar(48))"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_ts ON usage_events(ts)"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_events_compte_ts ON usage_events(compte_id, ts)"))
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS retours ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), compte_id integer,"
            " type varchar(12) NOT NULL, message text NOT NULL,"
            " statut varchar(12) NOT NULL DEFAULT 'nouveau', updated_at timestamptz DEFAULT now())"))
        # RETOURS-11F M11 — un retour VENU DE LA FICHE (« donnée ») porte l'IDU et la SECTION d'origine,
        # pour un lien cliquable vers la fiche dans Produit (le bandeau global reste sans contexte).
        c.execute(text("ALTER TABLE retours ADD COLUMN IF NOT EXISTS idu varchar(14)"))
        c.execute(text("ALTER TABLE retours ADD COLUMN IF NOT EXISTS section varchar(64)"))
        # ia_budget (D1) — attribution du coût IA au compte : colonne sur le ledger EXISTANT ia_log
        # (créé par ai.core._log_cost) ; ALTER d'abord au cas où la table précède cette colonne.
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS ia_log ("
            " id serial PRIMARY KEY, ts timestamptz DEFAULT now(), kind varchar(24), model varchar(64),"
            " stub boolean, tokens_in integer, tokens_out integer, cout_eur numeric(8,5))"))
        c.execute(text("ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id integer"))
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_ia_log_compte_ts ON ia_log(compte_id, ts)"))
        # quota Copilote PAR LICENCE (NULL = défaut config copilote_questions_jour_defaut)
        c.execute(text("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS copilote_quota_jour integer"))
        # RETOURS-8 (R3) — plafond Copilote/IA en EUROS/jour PAR LICENCE (NULL = défaut config 2,00 €).
        c.execute(text("ALTER TABLE comptes ADD COLUMN IF NOT EXISTS copilote_budget_eur numeric(6,2)"))
        # D4 — séquence d'onboarding : statut + date d'envoi STOCKÉS par (compte, mail)
        c.execute(text(
            "CREATE TABLE IF NOT EXISTS licence_mails ("
            " compte_id integer NOT NULL, mail_key varchar(24) NOT NULL,"
            " statut varchar(12) NOT NULL DEFAULT 'envoye', sent_at timestamptz DEFAULT now(),"
            " PRIMARY KEY (compte_id, mail_key))"))
    # FLUX-1 (F2.3) — le journal des bascules de run (qui, quand, de quel run vers lequel).
    from ..bascule_flux import ensure_tables as _bascule_ens
    _bascule_ens(engine)


# ───────────────────────── capteurs côté CLIENT ─────────────────────────
class UsageIn(BaseModel):
    kind: str = Field(pattern="^(outil|heartbeat)$")
    outil: str | None = Field(default=None, max_length=48)


@router.post("/usage/event")
def usage_event(body: UsageIn, request: Request) -> dict:
    """Capteur d'usage — fire-and-forget : TOUJOURS {ok}, une panne de capteur ne casse jamais
    l'app cliente. RGPD-sobre : (compte, outil, ts), aucun contenu."""
    try:
        from ..db import engine
        cid = getattr(request.state, "compte_id", None)
        with engine().begin() as c:
            c.execute(text("INSERT INTO usage_events (compte_id, kind, outil) VALUES (:c, :k, :o)"),
                      {"c": cid, "k": body.kind, "o": (body.outil or None)})
    except Exception as exc:  # noqa: BLE001 — capteur best-effort, jamais bloquant
        log.debug("usage_event avalé : %s", exc)
    return {"ok": True}


class RetourIn(BaseModel):
    # RETOURS-11F M11 — quatre types (Bug / Idée / Question / Donnée). « donnee » vient de la fiche et
    # porte alors l'IDU + la section ; les trois autres viennent du bandeau global (sans contexte).
    type: str = Field(pattern="^(bug|idee|question|donnee)$")
    message: str = Field(min_length=3, max_length=2000)
    idu: str | None = None
    section: str | None = None


@router.post("/retours")
def creer_retour(body: RetourIn, request: Request) -> dict:
    """Bouton « Signaler » (app cliente) : bug/idée/question/donnée + message. Un retour « donnée »
    venu de la fiche porte l'IDU et la section d'origine (lien cliquable vers la fiche dans Produit)."""
    from ..db import engine
    cid = getattr(request.state, "compte_id", None)
    idu = (body.idu or "").strip()[:14] or None
    section = (body.section or "").strip()[:64] or None
    with engine().begin() as c:
        rid = c.execute(text(
            "INSERT INTO retours (compte_id, type, message, idu, section) "
            "VALUES (:c, :t, :m, :idu, :sec) RETURNING id"),
            {"c": cid, "t": body.type, "m": body.message.strip(), "idu": idu, "sec": section}).scalar_one()
    # cloche admin best-effort (patron courrier_demande) — l'échec de la notif ne perd jamais le retour
    try:
        from ..db import session_scope
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Retour",
                               titre=f"Nouveau retour client ({body.type})",
                               detail=body.message[:280], lien=(f"#idu={idu}" if idu else "/admin"),
                               dedup=f"retour:{rid}", permanent=True)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": rid}


# ───────── CONNEXIONS-2 Lot 3 (KO-4) — SIGNALEMENTS (file unique, traitée au dashboard) ─────────
# Le « Signaler » de la fiche (type='fiche') ET celui du Radar (type='annonce') écrivent dans la
# MÊME table `signalements`. L'admin les VOIT et les TRAITE ici (plus de revue CLI-only).

@router.get("/admin/signalements")
def admin_signalements(request: Request, statut: str | None = None) -> dict:
    """Liste TOUS les signalements (tous comptes), fiche + annonce, du plus récent au plus ancien.
    `statut` filtre (défaut : tous). Chaque ligne : type, IDU/bien, motif, auteur, date, statut."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    where = " WHERE s.statut = :s" if statut else ""
    with engine().connect() as c:
        rows = [dict(r) for r in c.execute(text(
            "SELECT s.id, s.type, s.parcelle_id, s.bien_id, s.type_erreur, s.champ, s.commentaire,"
            "       s.utilisateur, s.statut, s.created_at, s.traite_at, s.compte_id,"
            "       k.nom AS compte_nom"
            "  FROM signalements s LEFT JOIN comptes k ON k.id = s.compte_id"
            f"{where} ORDER BY s.created_at DESC LIMIT 500"), {"s": statut}).mappings()]
        n_ouverts = int(c.execute(text(
            "SELECT count(*) FROM signalements WHERE statut = 'nouveau'")).scalar() or 0)
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
        r["traite_at"] = r["traite_at"].isoformat() if r["traite_at"] else None
        # RETOURS-11F M11 — lien cliquable vers la fiche (signalement d'erreur venu de la fiche) ;
        # `champ` porte la section. Une annonce Radar (type='annonce') n'a pas de fiche parcelle.
        r["fiche_lien"] = (f"#idu={r['parcelle_id']}" if r.get("type") == "fiche" and r.get("parcelle_id") else None)
    return {"signalements": rows, "n_ouverts": n_ouverts}


class SignalementStatutIn(BaseModel):
    statut: str = Field(pattern="^(nouveau|traite)$")


@router.post("/admin/signalements/traiter-internes")
def admin_signalements_traiter_internes(request: Request) -> dict:
    """RETOURS-8 (R13) — traite en UNE fois tous les signalements ouverts qui viennent d'un compte
    INTERNE / de TEST (comptes.plan = 'interne', ou compte_id NULL = pilote/admin/interne — rendu
    « interne » côté Produit). Rien n'est SUPPRIMÉ : tout est marqué `traite` (horodaté), de sorte que
    le compteur Pilotage retombe au nombre réel de signalements CLIENTS. Réversible (rouvrir à l'unité)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE signalements SET statut = 'traite', traite_at = now()"
            " WHERE statut = 'nouveau' AND id IN ("
            "   SELECT s.id FROM signalements s LEFT JOIN comptes k ON k.id = s.compte_id"
            "   WHERE s.compte_id IS NULL OR k.plan = 'interne')")).rowcount
    return {"ok": True, "traites": int(n or 0)}


@router.post("/admin/signalements/{sid}/statut")
def admin_signalement_statut(sid: int, body: SignalementStatutIn, request: Request) -> dict:
    """Traite (ou rouvre) un signalement : statut nouveau ↔ traite. `traite_at` horodaté au passage."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE signalements SET statut = (:st)::varchar,"
            "       traite_at = CASE WHEN (:st)::varchar = 'traite' THEN now() ELSE NULL END"
            " WHERE id = :i"), {"st": body.statut, "i": sid}).rowcount
    if not n:
        raise HTTPException(404, "Signalement introuvable.")
    return {"ok": True, "id": sid, "statut": body.statut}


# ───────────────────────── D2 — STRIPE (lecture seule) ─────────────────────────
@router.get("/admin/stripe")
def admin_stripe(request: Request, force: bool = False) -> dict:
    """Vue Stripe du dashboard (MRR, abonnements, statuts, CA/mois, rapprochement) — clé
    RESTREINTE lecture, cache 5 min, mode « non configuré » propre. Admin seulement (403 client)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..stripe_lecture import apercu
    return apercu(force=force)


# ───────────────────────── D3 — PILOTAGE ─────────────────────────
def _age_backup() -> dict:
    """Âge + taille du dernier dump (GB-054 · RETOURS-8 R10). La tuile lit le MÊME endroit ET les
    MÊMES motifs que les DEUX voies de sauvegarde : le cron `backup-postgres` (`labuse-*.sql.gz`,
    jobs_impl) ET la CLI `backup-db` (`*.dump`, format custom). L'ancien glob `*.dump` SEUL ne voyait
    jamais les dumps du cron → « aucun » à tort alors qu'un backup existait.
    ambre ≥ 2 j · rouge ≥ 7 j · « absent » si le répertoire existe mais est vide · « non configuré »
    si le répertoire n'existe pas (LABUSE_BACKUP_DIR non renseigné en local)."""
    import glob
    import os
    import time as _t
    from .. import config
    rep = config.get_settings().backup_dir
    if not rep or not os.path.isdir(rep):
        return {"etat": "non_configure", "chemin": rep, "age_jours": None}
    try:
        dumps = glob.glob(os.path.join(rep, "labuse-*.sql.gz")) + glob.glob(os.path.join(rep, "*.dump"))
        if not dumps:
            return {"etat": "absent", "chemin": rep, "age_jours": None}
        recent = max(dumps, key=os.path.getmtime)
        mtime = os.path.getmtime(recent)
        taille_mo = round(os.path.getsize(recent) / 1e6, 1)
        age_j = (_t.time() - mtime) / 86400
        etat = "rouge" if age_j >= 7 else "ambre" if age_j >= 2 else "ok"
        return {"etat": etat, "chemin": rep, "age_jours": round(age_j, 1),
                "mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "fichier": os.path.basename(recent), "taille_mo": taille_mo}
    except Exception:  # noqa: BLE001 — la tuile dit « absent », jamais un 500
        return {"etat": "absent", "chemin": rep, "age_jours": None}


@router.get("/admin/pilotage")
def admin_pilotage(request: Request) -> dict:
    """L'état de LABUSE en cinq secondes (héros + tuiles + LED du rail). AUCUN chiffre métier
    recalculé : tout est LU (Stripe lecture, ledgers, event_log, /readyz du process)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    from ..stripe_lecture import apercu
    stripe = apercu()

    with engine().begin() as c:
        licences_actives = c.execute(text(
            "SELECT COUNT(*) FROM comptes WHERE statut = 'actif'")).scalar() or 0
        # actifs 24 h = un login OU un capteur d'usage dans les dernières 24 h (par compte)
        actifs_24h = c.execute(text(
            "SELECT COUNT(*) FROM ("
            " SELECT DISTINCT compte_id FROM usage_events"
            "  WHERE ts > now() - interval '24 hours' AND compte_id IS NOT NULL"
            " UNION"
            " SELECT DISTINCT compte_id FROM utilisateurs"
            "  WHERE dernier_login_at > now() - interval '24 hours' AND compte_id IS NOT NULL) t"
        )).scalar() or 0
        ia = c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) AS cout, COUNT(*) AS appels FROM ia_log"
            " WHERE ts >= date_trunc('month', now())")).mappings().one()
        # fil admin : les événements SYSTÈME (compte NULL = feed pilote/admin, patron existant)
        fil = [dict(r) for r in c.execute(text(
            "SELECT id, ts, kind, source, titre, detail, lien FROM event_log"
            " WHERE compte_id IS NULL AND kind = 'systeme'"
            " ORDER BY ts DESC LIMIT 30")).mappings()]
        gels = [dict(r) for r in c.execute(text(
            "SELECT sujet, motif, ts FROM acces_gels WHERE actif ORDER BY ts DESC LIMIT 20")).mappings()]
        # CONNEXIONS-2 Lot 4 — KPI « courriers à déposer » : agrégat des demandes par bucket, vocabulaire
        # unique (courrier.STATUT_BUCKET). « à déposer » = ce que LABUSE doit encore déposer (statut demande).
        from .. import courrier as _courrier
        courrier_kpi = {"a_deposer": 0, "en_cours": 0, "clos": 0}
        if c.execute(text("SELECT to_regclass('courrier_demandes')")).scalar():
            rows_k = c.execute(text(
                "SELECT statut, count(*) AS n FROM courrier_demandes WHERE corps IS NOT NULL GROUP BY statut"
            )).mappings().all()
            for rk in rows_k:
                courrier_kpi[_courrier.STATUT_BUCKET.get(
                    _courrier.normaliser_statut(rk["statut"]), "en_cours")] += int(rk["n"])
        # SCORING-3 (L5.3) — étiquettes de retour terrain POSÉES (journal, jamais agrégé par
        # compte ni par parcelle ici : des COMPTES GLOBAUX seulement). Quand le cumul dépassera
        # 200, TERRAIN-1 aura de la matière.
        etiquettes = {"semaine": 0, "total": 0}
        if c.execute(text("SELECT to_regclass('contact_etiquette_log')")).scalar():
            r_et = c.execute(text(
                "SELECT count(*) FILTER (WHERE ts > now() - interval '7 days' "
                "                        AND etiquette IS NOT NULL) AS semaine, "
                "       count(*) FILTER (WHERE etiquette IS NOT NULL) AS total "
                "FROM contact_etiquette_log")).mappings().one()
            etiquettes = {"semaine": int(r_et["semaine"]), "total": int(r_et["total"])}
        # LED rail : run servi + date de la carte (même vérité que /map/tiles/meta)
        run_label = carte_le = None
        if c.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
            row = c.execute(text(
                "SELECT value, updated_at FROM mvt_meta WHERE key = 'run_label'")).mappings().first()
            if row:
                run_label, carte_le = row["value"], row["updated_at"]
        # ADMIN-1 (AD5) — deux rangées de tuiles : « À faire » (ambre, un geste attendu) et « Santé »
        # (vert, traction). Tous les chiffres sont LUS d'une table existante (jamais recalculés/inventés).
        # RETOURS-8 (R1) — les deux gestes « sources » dérivent de la LISTE UNIQUE `etats_sources`
        # (même arbitre que le Catalogue et la page client) : impossible qu'ils se contredisent.
        from .. import etats_sources as _es
        _cpt_sources = _es.compteurs(_es.lister_etats(c))
        af_nouvelle_version = _cpt_sources["nouvelle_version"]
        af_manuelles_retard = _cpt_sources["a_rafraichir"]
        af_essais_24h = int(c.execute(text(
            "SELECT COUNT(*) FROM comptes WHERE statut = 'actif' AND essai_expire_at IS NOT NULL"
            " AND essai_expire_at > now() AND essai_expire_at < now() + interval '24 hours'")).scalar() or 0)
        af_signalements = 0
        if c.execute(text("SELECT to_regclass('signalements')")).scalar():
            af_signalements = int(c.execute(text(
                "SELECT COUNT(*) FROM signalements WHERE statut = 'nouveau'")).scalar() or 0)
        # A4 — ventilation PAR TYPE des retours clients « Signaler » (bug/idée/question/donnée) encore
        # ouverts (statut nouveau). Lu de la table `retours` — sert le mini-compteur du Pilotage.
        retours_par_type: dict[str, int] = {}
        if c.execute(text("SELECT to_regclass('retours')")).scalar():
            retours_par_type = {r[0]: int(r[1]) for r in c.execute(text(
                "SELECT type, COUNT(*) FROM retours WHERE statut = 'nouveau' GROUP BY type"))}
        veilles_7j = 0
        if c.execute(text("SELECT to_regclass('alertes')")).scalar():
            veilles_7j = int(c.execute(text(
                "SELECT COUNT(*) FROM alertes WHERE detected_at > now() - interval '7 days'")).scalar() or 0)

    from .app import app as _app
    heal = getattr(_app.state, "schema_heal", None) or {}
    # ok None = heal jamais passé (boot sans lifespan, ex. tests) → la tuile dit « inconnu »,
    # jamais un faux rouge ni un faux vert.
    sante = {"ok": heal.get("ok"), "total": heal.get("total"),
             "en_echec": [f.get("module") for f in heal.get("failures", [])]}
    # CONNEXIONS-2 Lot 7.2 (N3) — sonde RUNTIME des endpoints métier (avec DB) : capte le cas
    # « /accueil/chiffres vivant mais écran vide » que le heal boot ne voit pas.
    from ..db import session_scope as _ss
    from . import sante as _sante
    try:
        with _ss() as _s:
            _sonde = _sante.sonde_metier(_s)
        sante["endpoints_ok"] = _sonde["ok"]
        sante["endpoints"] = _sonde["endpoints"]
    except Exception:  # noqa: BLE001 — la sonde ne casse jamais la page Pilotage
        sante["endpoints_ok"] = None
        sante["endpoints"] = []

    # FLUX-1 (F3.5) — tuile Radar : la donnée qui s'accumule (compteurs + écart demandé/acté).
    radar_tuile = None
    try:
        from ..pige import releves
        with _ss() as _s:
            radar_tuile = {"compteurs": releves.compteurs(_s), "ecart": releves.ecart_par_type(_s)}
    except Exception:  # noqa: BLE001 — la tuile Radar ne casse jamais la page Pilotage
        radar_tuile = None

    # ADMIN-1 (AD5) — garde de cohérence : on LIT le dernier état du job coherence-run (jamais de
    # re-sonde ici, qui serait coûteuse). Compteurs posés par jobs_impl.coherence_run (ok/n_surfaces).
    coherence = {"ok": None, "n_surfaces": None, "verifie_le": None}
    try:
        from .. import jobs as _jobs
        etat = _jobs.lire_etat("coherence-run") or {}
        cpt = etat.get("compteurs") or {}
        coherence = {"ok": cpt.get("ok"), "n_surfaces": cpt.get("n_surfaces"),
                     "verifie_le": etat.get("fin") or etat.get("debut")}
    except Exception:  # noqa: BLE001 — la tuile Santé ne casse jamais la page
        pass

    for r in fil:
        r["ts"] = r["ts"].isoformat() if r["ts"] else None
    for g in gels:
        g["ts"] = g["ts"].isoformat() if g["ts"] else None
    return {
        "stripe": stripe,
        "radar": radar_tuile,   # FLUX-1 F3.5 — tuile « la donnée qui s'accumule »
        "licences_actives": licences_actives,
        "actifs_24h": actifs_24h,
        "ia_mois": {"cout_eur": float(ia["cout"]), "appels": int(ia["appels"])},
        "backup": _age_backup(),
        "sante": sante,
        "courrier": courrier_kpi,   # CONNEXIONS-2 Lot 4 — {a_deposer, en_cours, clos}
        # SCORING-3 (L5.3) — étiquettes de retour terrain posées (7 j + cumul, seuil TERRAIN-1 : 200)
        "etiquettes_terrain": etiquettes,
        "run": {"label": run_label, "carte_le": carte_le.isoformat() if carte_le else None},
        # ADMIN-1 (AD5) — rangée « À faire » (ambre) : chaque tuile = un geste attendu, cliquable.
        # RETOURS-11 A4 — `a_faire` reste 4 compteurs ENTIERS (contrat testé) ; la ventilation par type
        # des retours « Signaler » vit à côté (clé sœur `retours_par_type`, dict), pas dans `a_faire`.
        "a_faire": {"sources_nouvelle_version": af_nouvelle_version, "essais_24h": af_essais_24h,
                    "signalements_ouverts": af_signalements, "manuelles_retard": af_manuelles_retard},
        "retours_par_type": retours_par_type,
        # ADMIN-1 (AD5) — rangée « Santé · traction » (vert). mrr_eur = Stripe (lecture), paires = Radar
        # (relevés), veilles_7j = alertes détectées, coherence = dernier passage de la garde.
        "traction": {"mrr_eur": stripe.get("mrr_eur"), "veilles_7j": veilles_7j,
                     "coherence": coherence},
        "fil": fil,
        "gels": gels,
    }


@router.get("/admin/sante-endpoints")
def admin_sante_endpoints(request: Request) -> dict:
    """CONNEXIONS-2 Lot 7.2 (N3) — sonde des endpoints MÉTIER (avec DB), à la demande. La tuile
    « Santé » du dashboard poll ceci : dernier passage + endpoints en échec (forme et non-vacuité)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import session_scope
    from . import sante
    with session_scope() as s:
        return sante.sonde_metier(s)


class DegelerIn(BaseModel):
    sujet: str = Field(min_length=1, max_length=128)


@router.post("/admin/degeler")
def admin_degeler(body: DegelerIn, request: Request) -> dict:
    """Dégel d'un sujet (gel anti-burst) depuis le fil Pilotage — même geste que la CLI
    `labuse ungel`, journalisé."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine, session_scope
    with engine().begin() as c:
        n = c.execute(text("UPDATE acces_gels SET actif = false WHERE sujet = :s AND actif"),
                      {"s": body.sujet}).rowcount
    if n:
        try:
            from .events import creer_notification
            with session_scope() as s:
                creer_notification(s, kind="systeme", compte_id=None, source="Sécurité",
                                   titre=f"Gel anti-burst levé sur {body.sujet[:64]}",
                                   detail="Dégel manuel depuis la Tour de contrôle.",
                                   dedup=f"degel:{body.sujet[:64]}")
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "degele": bool(n)}


# ───────────────────────── D4 — LICENCES ─────────────────────────
def _rappels_onboarding(created_at, mails: dict) -> list[str]:
    """L'app RAPPELLE, Vic déclenche (mandat MAILS) : Mail 2 à J+3, Mail 3 à J+10 — en ambre
    sur la fiche tant que non envoyés. Jamais d'envoi automatique."""
    if created_at is None:
        return []
    age_j = (datetime.now(tz=timezone.utc) - created_at).total_seconds() / 86400
    rappels = []
    if age_j >= 3 and "onboarding2" not in mails:
        rappels.append("Mail 2 à envoyer (J+3 atteint)")
    if age_j >= 10 and "onboarding3" not in mails:
        rappels.append("Mail 3 à envoyer (J+10 atteint)")
    return rappels


@router.get("/admin/licences")
def admin_licences(request: Request) -> dict:
    """Une fiche par client : statut app + Stripe, onboarding (mails stockés + rappels),
    KPI (usage 7 j via heartbeats, dernière connexion, Copilote jour/quota)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..brevo import etat_configuration
    from ..db import engine
    from ..stripe_lecture import apercu
    stripe = apercu()
    abos_par_cust = {a["customer_id"]: a for a in (stripe.get("abonnements") or [])}
    defaut_quota = int(config.get_settings().copilote_questions_jour_defaut)
    with engine().begin() as c:
        comptes = [dict(r) for r in c.execute(text(
            "SELECT k.id, k.nom, k.plan, k.statut, k.sieges, k.created_at, k.updated_at,"
            "       k.stripe_customer_id, k.copilote_quota_jour, k.essai_expire_at,"
            "       (SELECT u.email FROM utilisateurs u WHERE u.compte_id = k.id"
            "         ORDER BY u.id LIMIT 1) AS email,"
            "       (SELECT MAX(u.dernier_login_at) FROM utilisateurs u WHERE u.compte_id = k.id)"
            "         AS derniere_connexion"
            " FROM comptes k WHERE k.statut != 'resilie' ORDER BY k.created_at DESC")).mappings()]
        mails_rows = c.execute(text(
            "SELECT compte_id, mail_key, statut, sent_at FROM licence_mails")).mappings().all()
        usage_rows = c.execute(text(
            "SELECT compte_id, COUNT(*) AS hb FROM usage_events"
            " WHERE kind = 'heartbeat' AND ts > now() - interval '7 days'"
            "   AND compte_id IS NOT NULL GROUP BY compte_id")).mappings().all()
        nl_rows = c.execute(text(
            "SELECT sujet, n FROM usage_compteurs WHERE jour = CURRENT_DATE AND kind = 'nl'"
        )).mappings().all()
    mails_par_compte: dict[int, dict] = {}
    for m in mails_rows:
        mails_par_compte.setdefault(m["compte_id"], {})[m["mail_key"]] = {
            "statut": m["statut"], "sent_at": m["sent_at"].isoformat() if m["sent_at"] else None}
    hb = {u["compte_id"]: int(u["hb"]) for u in usage_rows}
    nl = {s["sujet"]: int(s["n"]) for s in nl_rows}
    # A5 — signal de partage de compte (sessions actives + IP distinctes), par compte
    from ..comptes import sessions_actives_par_compte
    from ..db import session_scope
    with session_scope() as _s:
        partage = {p["compte_id"]: p for p in sessions_actives_par_compte(_s)}
    out = []
    for k in comptes:
        mails = mails_par_compte.get(k["id"], {})
        pg = partage.get(k["id"])
        out.append({
            "id": k["id"], "nom": k["nom"], "email": k["email"], "plan": k["plan"],
            "statut": k["statut"], "created_at": k["created_at"].isoformat() if k["created_at"] else None,
            "essai_expire_at": k["essai_expire_at"].isoformat() if k["essai_expire_at"] else None,
            "stripe": abos_par_cust.get(k["stripe_customer_id"]),
            "mails": mails,
            "rappels": _rappels_onboarding(k["created_at"], mails),
            # A5 — sessions simultanées : purement informatif (jamais de blocage/déconnexion)
            "partage": {"sessions": int(pg["sessions"]), "ips": int(pg["ips"] or 0),
                        "probable": bool(pg["partage_probable"])} if pg else None,
            "kpi": {
                # heartbeat = 1 balise / 5 min onglet visible → temps d'usage ESTIMÉ (dit au front)
                "usage_7j_min": hb.get(k["id"], 0) * 5,
                "derniere_connexion": k["derniere_connexion"].isoformat() if k["derniere_connexion"] else None,
                "copilote_jour": nl.get(f"c:{k['id']}", 0),
                "copilote_quota": k["copilote_quota_jour"] or defaut_quota,
            },
        })
    from ..brevo import LIBELLES as _MAIL_LIBELLES
    return {"licences": out, "stripe_configure": bool(stripe.get("configure")),
            "rapprochement": stripe.get("rapprochement"), "brevo": etat_configuration(),
            # ADMIN-1 (AD4) — libellés servis des mails (fini « Mail 1/2/3 »), source unique = brevo.LIBELLES.
            "mail_libelles": dict(_MAIL_LIBELLES),
            "partage_seuil": int(config.get_settings().sessions_signal_seuil)}


@router.get("/admin/partage")
def admin_partage(request: Request) -> dict:
    """A5 — partage de compte OBSERVÉ : par compte, sessions actives + IP distinctes simultanées,
    et le drapeau `partage_probable` (≥ seuil). Purement informatif : Vic décide, l'app informe —
    AUCUNE déconnexion, AUCUN blocage. RGPD : n'expose que des comptes et des NOMBRES (les
    empreintes sont hachées en base, jamais servies)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..comptes import sessions_actives_par_compte
    from ..db import engine, session_scope
    with session_scope() as s:
        lignes = sessions_actives_par_compte(s)
    noms = {}
    if lignes:
        with engine().begin() as c:
            noms = {r["id"]: r["nom"] for r in c.execute(text(
                "SELECT id, nom FROM comptes WHERE id = ANY(:ids)"),
                {"ids": [x["compte_id"] for x in lignes]}).mappings()}
    for x in lignes:
        x["nom"] = noms.get(x["compte_id"])
    signales = [x for x in lignes if x["partage_probable"]]
    return {"seuil": int(config.get_settings().sessions_signal_seuil),
            "comptes": sorted(lignes, key=lambda x: (-int(x["ips"] or 0), -int(x["sessions"]))),
            "n_signales": len(signales)}


class NouveauClientIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    nom: str | None = Field(default=None, max_length=120)


@router.post("/admin/licences/creer")
def admin_licence_creer(body: NouveauClientIn, request: Request) -> dict:
    """Parcours « nouveau client » étape 1 — le MÉCANISME OFFICIEL existant (creer_invitation :
    compte + utilisateur `invite`, token 7 j). Renvoie le lien d'invitation (envoi à la main,
    décision Vic historique conservée)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import creer_invitation
    from ..db import session_scope
    try:
        with session_scope() as s:
            inv = creer_invitation(s, body.email.strip(), nom=(body.nom or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, **inv}


class EssaiIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    nom: str | None = Field(default=None, max_length=120)
    heures: int | None = Field(default=None, ge=1, le=24 * 30)


@router.post("/admin/licences/creer-essai")
def admin_licence_creer_essai(body: EssaiIn, request: Request) -> dict:
    """D9 — compte d'ESSAI : même mécanisme officiel que le nouveau client (invitation), mais
    le compte est ACTIF tout de suite avec une date d'échéance (défaut 48 h, paramétrable).
    À l'échéance : bascule automatique sur la suspension (accès coupé, données conservées,
    écran « abonnement à régulariser »). Le lien d'invitation s'envoie à la main."""
    from fastapi import HTTPException
    from .. import config
    from ..comptes import creer_invitation
    from ..db import engine, session_scope
    from .auth import exiger_admin
    exiger_admin(request)
    heures = body.heures or int(config.get_settings().essai_duree_heures)
    try:
        with session_scope() as s:
            inv = creer_invitation(s, body.email.strip(), nom=(body.nom or "").strip() or None)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with engine().begin() as c:
        expire = c.execute(text(
            "UPDATE comptes SET statut = 'actif', essai_expire_at = now() + (:h || ' hours')::interval,"
            " updated_at = now() WHERE id = :c RETURNING essai_expire_at"),
            {"h": heures, "c": inv["compte_id"]}).scalar_one()
    return {"ok": True, **inv, "essai": True, "heures": heures, "essai_expire_at": expire.isoformat()}


@router.post("/admin/licences/{compte_id}/convertir")
def admin_licence_convertir(compte_id: int, request: Request) -> dict:
    """D9 — « Convertir en abonnement » : l'échéance d'essai tombe, le compte repasse `invite`
    (jamais payé) → le mécanisme OFFICIEL de reprise de paiement prend le relais au login
    (Checkout). Données conservées."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE comptes SET essai_expire_at = NULL,"
            " statut = CASE WHEN stripe_subscription_id IS NULL THEN 'invite' ELSE statut END,"
            " updated_at = now() WHERE id = :c"), {"c": compte_id}).rowcount
    if not n:
        raise HTTPException(404, "Compte introuvable.")
    return {"ok": True, "detail": "Essai levé — le compte paiera via le parcours officiel (login → Checkout)."}


class SuspendreIn(BaseModel):
    motif: str = Field(default="manuel", max_length=120)


@router.post("/admin/licences/{compte_id}/suspendre")
def admin_licence_suspendre(compte_id: int, body: SuspendreIn, request: Request) -> dict:
    """Suspension MANUELLE (mandat : jamais automatique sur un échec de carte) — flag en base,
    sessions coupées, données INTACTES, réversible. Le client voit « abonnement à régulariser »
    + lien de paiement à son prochain login (cf. branche /login)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import suspendre_compte
    from ..db import session_scope
    with session_scope() as s:
        suspendre_compte(s, compte_id, motif=f"dashboard:{body.motif}")
    return {"ok": True, "statut": "suspendu"}


@router.post("/admin/licences/{compte_id}/retablir")
def admin_licence_retablir(compte_id: int, request: Request) -> dict:
    from .auth import exiger_admin
    exiger_admin(request)
    from ..comptes import reactiver_compte
    from ..db import session_scope
    with session_scope() as s:
        reactiver_compte(s, compte_id, motif="dashboard:retabli")
    return {"ok": True, "statut": "actif"}


class MailIn(BaseModel):
    key: str = Field(min_length=2, max_length=24)


@router.post("/admin/licences/{compte_id}/mail")
def admin_licence_mail(compte_id: int, body: MailIn, request: Request) -> dict:
    """Envoi MANUEL d'un template Brevo au titulaire (onboarding 1/2/3, souscription, relance…).
    Non configuré → {envoye:false, raison} — le bouton du dashboard l'affiche, rien de silencieux.
    Statut + date STOCKÉS (licence_mails) quand l'envoi part."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..brevo import LIBELLES              # LIBELLES = données d'affichage (pas un transport)
    from ..mail import envoyer_template       # CONNEXIONS-2 Lot 9.1 (KO-12) — envoi via la façade unique
    from ..db import engine
    if body.key not in LIBELLES:
        raise HTTPException(422, f"Template inconnu « {body.key} ».")
    with engine().begin() as c:
        row = c.execute(text(
            "SELECT k.nom, (SELECT u.email FROM utilisateurs u WHERE u.compte_id = k.id"
            " ORDER BY u.id LIMIT 1) AS email FROM comptes k WHERE k.id = :c"),
            {"c": compte_id}).mappings().first()
    if not row or not row["email"]:
        raise HTTPException(404, "Compte introuvable ou sans utilisateur.")
    res = envoyer_template(row["email"], body.key, params={"nom": row["nom"]})
    if res.get("envoye"):
        with engine().begin() as c:
            c.execute(text(
                "INSERT INTO licence_mails (compte_id, mail_key, statut) VALUES (:c, :k, 'envoye')"
                " ON CONFLICT (compte_id, mail_key)"
                " DO UPDATE SET statut = 'envoye', sent_at = now()"),
                {"c": compte_id, "k": body.key})
    return {"ok": True, **res}


@router.get("/admin/licences/{compte_id}/mail/{key}/apercu")
def admin_licence_mail_apercu(compte_id: int, key: str, request: Request) -> dict:
    """ADMIN-1 (AD4) — APERÇU du mail réel (template Brevo rendu avec les variables du compte) AVANT
    « Envoyer ». Non configuré → aperçu honnête (raison + variables qui SERAIENT injectées)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..brevo import LIBELLES, apercu_template
    from ..db import engine
    if key not in LIBELLES:
        raise HTTPException(422, f"Template inconnu « {key} ».")
    with engine().begin() as c:
        row = c.execute(text(
            "SELECT k.nom, (SELECT u.email FROM utilisateurs u WHERE u.compte_id = k.id"
            " ORDER BY u.id LIMIT 1) AS email FROM comptes k WHERE k.id = :c"),
            {"c": compte_id}).mappings().first()
    if not row:
        raise HTTPException(404, "Compte introuvable.")
    return apercu_template(key, params={"nom": row["nom"], "email": row["email"]})


# ───────────────────────── D5 — IA (section mauve) ─────────────────────────
@router.get("/admin/ia")
def admin_ia(request: Request) -> dict:
    """Conso IA lue du ledger ia_log (D1) : mois courant, coût moyen/question, 30 jours de
    barres, ventilation par licence, projection fin de mois AU RYTHME DES 7 DERNIERS JOURS.
    Le solde Anthropic n'est PAS exposé par l'API : conso trackée localement (note honnête)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import config
    from ..db import engine
    with engine().begin() as c:
        mois = c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) AS cout, COUNT(*) AS appels FROM ia_log"
            " WHERE ts >= date_trunc('month', now())")).mappings().one()
        jours = [dict(r) for r in c.execute(text(
            "SELECT date_trunc('day', ts)::date AS jour, ROUND(SUM(cout_eur), 4) AS cout,"
            "       COUNT(*) AS appels"
            " FROM ia_log WHERE ts > now() - interval '30 days'"
            " GROUP BY 1 ORDER BY 1")).mappings()]
        par_licence = [dict(r) for r in c.execute(text(
            "SELECT l.compte_id, COALESCE(k.nom, 'Vous (admin/pilote)') AS nom,"
            "       ROUND(SUM(l.cout_eur), 4) AS cout, COUNT(*) AS appels"
            " FROM ia_log l LEFT JOIN comptes k ON k.id = l.compte_id"
            " WHERE l.ts > now() - interval '30 days'"
            " GROUP BY l.compte_id, k.nom ORDER BY SUM(l.cout_eur) DESC")).mappings()]
        cout_7j = float(c.execute(text(
            "SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log"
            " WHERE ts > now() - interval '7 days'")).scalar() or 0)
        quotas = [dict(r) for r in c.execute(text(
            "SELECT id, nom, copilote_quota_jour, copilote_budget_eur FROM comptes"
            " WHERE statut NOT IN ('resilie') ORDER BY created_at DESC")).mappings()]
    # RETOURS-8 (R3) — le plafond est désormais en EUROS/jour par compte. Pour chaque licence :
    # le budget € effectif (override ou défaut), la dépense du jour en €, le nombre d'appels (mention
    # secondaire), et l'équivalent « ≈ N questions » au coût moyen réel du compte.
    _budget_defaut = float(config.get_settings().copilote_budget_eur_defaut)
    for q in quotas:
        b = float(q["copilote_budget_eur"]) if q["copilote_budget_eur"] is not None else _budget_defaut
        cmoy = cout_moyen_appel(int(q["id"]))
        q["budget_eur"] = round(b, 2)
        q["depense_eur"] = round(depense_eur_aujourdhui(int(q["id"])), 4)
        q["equiv_questions"] = int(b / cmoy) if cmoy > 0 else None
        q["appels_aujourdhui"] = consomme_copilote_aujourdhui(int(q["id"]))
    from datetime import date
    import calendar
    today = date.today()
    jours_restants = calendar.monthrange(today.year, today.month)[1] - today.day
    projection = float(mois["cout"]) + (cout_7j / 7.0) * jours_restants
    appels = int(mois["appels"])
    for r in jours:
        r["jour"] = r["jour"].isoformat()
        r["cout"] = float(r["cout"])
    for r in par_licence:
        r["cout"] = float(r["cout"])
    # RETOURS-7 Z7 — TABLEAU « surface → modèle » : quel modèle sert chaque usage IA, LU depuis la
    # config (registre ai_models.SURFACES + override env résolu), jamais un nom en dur. C'est la même
    # source que celle réellement appelée (model_for), donc ce tableau EST la vérité servie.
    from .. import ai_models
    surfaces = ai_models.surfaces_table()
    # RETOURS-8 (R3) — coût unitaire d'UNE question : le coût moyen réel (mois), repli sur le plancher
    # config (0,008 €). Affiché « 0,008 € / question » (plus « pour 1 000 questions »).
    cout_unitaire = (float(mois["cout"]) / appels) if appels else float(
        config.get_settings().copilote_cout_moyen_defaut)
    return {
        "mois": {"cout_eur": float(mois["cout"]), "appels": appels,
                 "cout_moyen_question": (float(mois["cout"]) / appels) if appels else None},
        "cout_unitaire_question_eur": round(cout_unitaire, 5),
        "projection_fin_mois_eur": round(projection, 2),
        "jours": jours,
        "par_licence": par_licence,
        # RETOURS-8 (R3) — le plafond par défaut est en EUROS/jour (défaut config), éditable par licence.
        "budget_defaut_eur": round(float(config.get_settings().copilote_budget_eur_defaut), 2),
        "quotas": quotas,
        "modeles_par_surface": surfaces,
        "note": "Solde Anthropic non exposé par l'API — consommation trackée localement (ledger ia_log).",
    }


class QuotaIn(BaseModel):
    # RETOURS-8 (R3) — le plafond s'édite désormais en EUROS/jour (0,50 · 1 · 2 · 5 ou libre). null =
    # retour au défaut config. `quota` (appels) reste ACCEPTÉ pour rétro-compatibilité d'un vieux front.
    budget_eur: float | None = Field(default=None, ge=0.0, le=1_000.0)
    quota: int | None = Field(default=None, ge=1, le=10_000)


@router.post("/admin/licences/{compte_id}/quota")
def admin_licence_quota(compte_id: int, body: QuotaIn, request: Request) -> dict:
    """RETOURS-8 (R3) — édite le plafond Copilote/IA de LA licence, en EUROS/jour (`budget_eur`),
    null = retour au défaut config. /ia, /api/copilote-v2/ask ET les missions lourdes le lisent tous
    à la requête suivante (garde unique `etat_plafond_ia`) — l'édition agit sur les trois surfaces."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE comptes SET copilote_budget_eur = :b, updated_at = now() WHERE id = :c"),
            {"b": body.budget_eur, "c": compte_id}).rowcount
    if not n:
        raise HTTPException(404, "Compte introuvable.")
    return {"ok": True, "budget_eur": body.budget_eur}


# ───────────────────────── D6 — SOURCES ─────────────────────────
#: cadence normalisée → délai (jours, marge comprise) au-delà duquel « À mettre à jour ».
#: None = pas d'échéance calculable (pluriannuelle : le millésime amont bouge rarement).
CADENCES: dict[str, int | None] = {
    "hebdomadaire": 10, "mensuelle": 40, "trimestrielle": 100,
    "semestrielle": 200, "annuelle": 400, "pluriannuelle": None, "continue": 10,
}


def _cadence_normalisee(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip().lower()
    for k in CADENCES:
        if v.startswith(k[:6]):     # 'mensuel'/'mensuelle', 'semestriel(le)'… → clé canonique
            return k
    return None


def _commandes_ingestion() -> list[dict]:
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "config" / "sources_ingestion.yaml"
    try:
        return (yaml.safe_load(p.read_text()) or {}).get("commandes", [])
    except Exception:  # noqa: BLE001 — pas de mapping → pas de bouton, jamais un 500
        return []


def _relance_pour(nom: str) -> dict | None:
    import fnmatch
    for cmd in _commandes_ingestion():
        if fnmatch.fnmatch(nom.lower(), cmd["motif"].lower().replace("%", "*")):
            return cmd
    return None


@router.get("/admin/sources")
def admin_sources(request: Request) -> dict:
    """Les 59 : millésime amont, ingéré le, cadence ATTENDUE (configurable ici), badge
    « À mettre à jour » = cadence dépassée (calcul auto sur last_sync_at), bouton Relancer
    quand une commande existe (config/sources_ingestion.yaml). + dernières exécutions
    d'ingestion (ingestion_runs — les crons ne journalisent pas event_log, la table est
    leur vraie trace ; le verdict des crons vit sur /healthz/crons, l'écran l'affiche)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    from ..sources_catalog import est_affichee
    from .. import sentinelle
    from .. import etats_sources
    from .. import flux as _flux_mod
    now = datetime.now(tz=timezone.utc)
    with engine().begin() as c:
        rows = [dict(r) for r in c.execute(text(
            "SELECT d.id, d.name, d.category, d.provider, d.status, d.technical_notes, d.last_sync_at,"
            "       d.source_millesime, d.source_horizon_at, d.source_cadence,"
            "       COALESCE(d.affichage_desactive, false) AS affichage_desactive,"
            # SENTINELLE-1 (W4) — état de veille amont (LEFT JOIN : une source non surveillée = état normal).
            "       v.actif AS veille_actif, v.methode AS veille_methode, v.dernier_statut AS veille_statut,"
            "       v.dernier_vu AS veille_vu, v.dernier_passage_at AS veille_passage, v.dernier_message AS veille_message,"
            "       v.echecs_consecutifs AS veille_echecs,"
            "       v.injection_lancee_at AS veille_inj_at, v.injection_vu AS veille_inj_vu,"
            "       COALESCE(v.mail_alerte, false) AS veille_mail_alerte,"   # SUITE-1 S4.1
            # SENTINELLE-3 (Y4) — rappel de rafraîchissement des sources manuelles.
            "       v.cadence_attendue_jours AS veille_cadence_attendue, v.convention_echeance AS veille_convention"
            " FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id ORDER BY d.name")).mappings()]
        runs = [dict(r) for r in c.execute(text(
            "SELECT r.started_at, r.finished_at, r.status, r.parcels_count, d.name"
            " FROM ingestion_runs r LEFT JOIN data_sources d ON d.id = r.data_source_id"
            " ORDER BY r.started_at DESC NULLS LAST LIMIT 10")).mappings()]
    sources = []
    for r in rows:
        if not est_affichee(r["name"], r.get("technical_notes"), r["status"]):
            continue
        cad = _cadence_normalisee(r["source_cadence"])
        delai = CADENCES.get(cad) if cad else None
        a_jour = None
        if delai is not None and r["last_sync_at"] is not None:
            a_jour = (now - r["last_sync_at"]).days <= delai
        relance = _relance_pour(r["name"])
        # RETOURS-8 (R1) — l'état unique (un des quatre : nouvelle_version / a_rafraichir / a_jour /
        # non_surveillee), calculé par le MÊME arbitre que Pilotage et la page client. Le constat de
        # l'agent gagne sur l'heuristique de cadence (DPE/DVF : « à jour » même si le producteur traîne).
        _et = etats_sources.etat_source(r, now=now)
        sources.append({
            "id": r["id"], "name": r["name"], "category": r["category"],
            "millesime": r["source_millesime"],
            "horizon": r["source_horizon_at"].isoformat() if r["source_horizon_at"] else None,
            "ingere_le": r["last_sync_at"].isoformat() if r["last_sync_at"] else None,
            "cadence": cad,
            # RETOURS-8 (R1) — état unique + phrase honnête + projection client (2 états).
            "etat": _et["etat"], "etat_client": _et["etat_client"],
            "etat_phrase": _et["phrase_admin"], "publie_le": _et["publie_le"],
            # a_jour : true OK · false à mettre à jour · null = pas d'échéance calculable
            "a_jour": a_jour,
            "relance": relance["label"] if relance else None,
            # CONNEXIONS-2 Lot 6.3 — état du flag pour le toggle admin (désactivée ⇒ hors vitrine).
            "affichage_desactive": bool(r.get("affichage_desactive")),
            # SENTINELLE-1 (W4) — bloc veille amont. `surveillee` = une ligne source_veille existe.
            # `nouvelle_version` = la sonde a constaté un millésime amont postérieur au servi (statut ambre).
            # SENTINELLE-2 (X4) — `fournisseur` pour la colonne/regroupement du tableau de veille ;
            # `raison` (X3.3) = pourquoi une source N'EST PAS surveillée (infobulle, jamais un blanc).
            "fournisseur": r.get("provider"),
            # SUITE-1 (S2 bis) — colonne « Alimente » : moteurs + surfaces nourris, LUS de la matrice
            # réelle (flux.py) ; jamais écrit à la main. `cable=False` → « non câblée ».
            "alimente": _flux_mod.alimente_pour_source(r["name"]),
            "veille": {
                # SENTINELLE-3 (Y5.4) — `nature` distingue les 4 états : version détectable (api/page),
                # changement détectable (entete/temoin), rappel manuel (Y4), non surveillable (rien).
                # `surveillee` = une VRAIE sonde amont existe (un rappel manuel n'en est PAS une).
                "nature": sentinelle.nature(r.get("veille_methode")),
                "surveillee": r.get("veille_methode") in ("api", "page", "entete", "temoin"),
                "actif": bool(r.get("veille_actif")) if r.get("veille_actif") is not None else None,
                "methode": r.get("veille_methode"),
                "statut": r.get("veille_statut"),
                "millesime_amont": r.get("veille_vu"),
                "nouvelle_version": r.get("veille_statut") == "nouvelle_version",
                "passage_at": r["veille_passage"].isoformat() if r.get("veille_passage") else None,
                "message": r.get("veille_message"),
                "echecs": int(r.get("veille_echecs") or 0),
                # sonde en échec CONFIRMÉ (≥3 passages ratés) : distinct d'un aléa transitoire (X5.2).
                "echec_confirme": (r.get("veille_statut") in ("injoignable", "illisible")
                                   and int(r.get("veille_echecs") or 0) >= sentinelle.SEUIL_ECHECS_NOTIF),
                # raison précise (X3.3) tant que ce N'EST PAS une vraie sonde (non surveillée OU rappel manuel).
                "raison": None if r.get("veille_methode") in ("api", "page", "entete", "temoin")
                          else sentinelle.raison_non_surveillee(r["name"]),
                # SENTINELLE-2 (X6) — `injectable` = une commande d'ingestion existe (sinon injection
                # manuelle, pas de bouton). Trace de la dernière injection déclenchée à la main par Vic.
                "injectable": relance is not None,
                "injection_lancee_at": r["veille_inj_at"].isoformat() if r.get("veille_inj_at") else None,
                "injection_vu": r.get("veille_inj_vu"),
                "mail_alerte": bool(r.get("veille_mail_alerte")),   # SUITE-1 S4.1

                # SENTINELLE-3 (Y4) — rappel manuel : cadence attendue + retard calculé (last_sync_at),
                # échéance de convention si connue. `rappel_retard` = donnée manuelle non rafraîchie à temps.
                "cadence_attendue_jours": r.get("veille_cadence_attendue"),
                "convention_echeance": r["veille_convention"].isoformat() if r.get("veille_convention") else None,
                "jours_depuis_maj": (now - r["last_sync_at"]).days if r.get("last_sync_at") else None,
                "rappel_retard": bool(
                    r.get("veille_methode") == "rappel" and r.get("veille_cadence_attendue") is not None
                    and r.get("last_sync_at") is not None
                    and (now - r["last_sync_at"]).days > r["veille_cadence_attendue"]),
            },
        })
    # « à mettre à jour » d'abord (mandat), puis nom
    sources.sort(key=lambda s: (s["a_jour"] is not False, s["name"].lower()))
    for r in runs:
        r["started_at"] = r["started_at"].isoformat() if r["started_at"] else None
        r["finished_at"] = r["finished_at"].isoformat() if r["finished_at"] else None
    return {"sources": sources,
            "synthese": {"a_mettre_a_jour": sum(1 for s in sources if s["a_jour"] is False),
                         "ok": sum(1 for s in sources if s["a_jour"] is True),
                         "sans_echeance": sum(1 for s in sources if s["a_jour"] is None),
                         # RETOURS-8 (R1) — compteurs d'état UNIQUE, dérivés de la même liste que
                         # Pilotage et la page client (test d'égalité : test_etats_sources).
                         "etat_nouvelle_version": sum(1 for s in sources if s["etat"] == "nouvelle_version"),
                         "etat_a_rafraichir": sum(1 for s in sources if s["etat"] == "a_rafraichir"),
                         # RETOURS-9 (Q2) — 5e état : surveillée jamais sondée (l'agent n'est pas passé).
                         "etat_jamais_verifiee": sum(1 for s in sources if s["etat"] == "jamais_verifiee"),
                         "etat_a_jour": sum(1 for s in sources if s["etat"] == "a_jour"),
                         "etat_non_surveillee": sum(1 for s in sources if s["etat"] == "non_surveillee"),
                         "pas_a_jour_client": sum(1 for s in sources if s["etat_client"] == "pas_a_jour"),
                         # SENTINELLE-1 (W4.2) — nombre de sources avec une nouvelle version disponible.
                         "nouvelle_version": sum(1 for s in sources if s["veille"]["nouvelle_version"]),
                         "surveillees": sum(1 for s in sources if s["veille"]["surveillee"]),
                         # SENTINELLE-2 (X4) — pour le tableau à 30+ lignes : sondes en échec confirmé,
                         # et sources non surveillées (état explicite, pas un blanc).
                         "sonde_echec": sum(1 for s in sources if s["veille"]["echec_confirme"]),
                         "non_surveillees": sum(1 for s in sources if not s["veille"]["surveillee"]),
                         # SENTINELLE-3 — ventilation par nature (Y5.4) + rappels manuels en retard (Y4).
                         "version": sum(1 for s in sources if s["veille"]["nature"] == "version"),
                         "changement": sum(1 for s in sources if s["veille"]["nature"] == "changement"),
                         "rappels": sum(1 for s in sources if s["veille"]["nature"] == "rappel"),
                         "rappels_en_retard": sum(1 for s in sources if s["veille"]["rappel_retard"])},
            "cadences": list(CADENCES.keys()),
            "runs": runs}


@router.post("/admin/sources/{source_id}/veille/verifier")
def admin_source_veille_verifier(source_id: int, request: Request) -> dict:
    """SENTINELLE-1 (W4.3) — « Vérifier maintenant » : lance la sonde sur CETTE source, en direct
    (forcer=True, hors cadence), et renvoie le verdict. N'écrit que dans source_veille, jamais dans
    data_sources. 404 si la source n'est pas surveillée (pas de ligne source_veille)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import session_scope
    from .. import sentinelle
    with session_scope() as s:
        # SENTINELLE-3 — une vraie SONDE seulement (un 'rappel' manuel n'est pas sondable : 404 honnête).
        existe = s.execute(text("SELECT 1 FROM source_veille WHERE source_id = :i"
                                " AND methode IN ('api', 'page', 'entete', 'temoin')"),
                           {"i": source_id}).scalar()
        if not existe:
            raise HTTPException(404, "Cette source n'est pas surveillée (aucune sonde amont).")
        recap = sentinelle.passer(s, source_ids=[source_id], forcer=True, notifier=True, delai_s=0)
        s.commit()
    detail = recap["details"][0] if recap["details"] else {}
    return {"ok": True, "statut": detail.get("statut"), "millesime_amont": detail.get("vu"),
            "servi": detail.get("servi"), "message": detail.get("message"), "notifs": recap["notifs"]}


class VeilleActiveIn(BaseModel):
    actif: bool


@router.post("/admin/sources/{source_id}/veille/active")
def admin_source_veille_active(source_id: int, body: VeilleActiveIn, request: Request) -> dict:
    """SENTINELLE-1 (W4.3) — active / désactive la SURVEILLANCE d'une source (flag source_veille.actif).
    Désactivée ⇒ le job quotidien la saute (état normal, pas une erreur). 404 si non surveillée."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text("UPDATE source_veille SET actif = :a, updated_at = now() WHERE source_id = :i"),
                      {"a": body.actif, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Cette source n'est pas surveillée (aucune ligne de veille).")
    return {"ok": True, "actif": body.actif}


class VeilleMailIn(BaseModel):
    mail_alerte: bool


@router.post("/admin/sources/{source_id}/veille/mail")
def admin_source_veille_mail(source_id: int, body: VeilleMailIn, request: Request) -> dict:
    """SUITE-1 (S4.1) — abonne/désabonne une source à l'alerte MAIL (défaut off). L'alerte in-app
    reste toujours déposée ; ce drapeau décide seulement si le digest part AUSSI par mail. 404 si la
    source n'est pas surveillée (aucune ligne de veille)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text("UPDATE source_veille SET mail_alerte = :m, updated_at = now()"
                           " WHERE source_id = :i"), {"m": body.mail_alerte, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Cette source n'est pas surveillée (aucune ligne de veille).")
    return {"ok": True, "mail_alerte": body.mail_alerte}


class CadenceIn(BaseModel):
    cadence: str | None = None


@router.post("/admin/sources/{source_id}/cadence")
def admin_source_cadence(source_id: int, body: CadenceIn, request: Request) -> dict:
    """La cadence attendue de chaque source se règle SUR CETTE PAGE (mandat D6)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    cad = _cadence_normalisee(body.cadence) if body.cadence else None
    if body.cadence and cad is None:
        raise HTTPException(422, f"Cadence inconnue « {body.cadence} » (attendues : {', '.join(CADENCES)}).")
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text("UPDATE data_sources SET source_cadence = :v WHERE id = :i"),
                      {"v": cad, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Source introuvable.")
    return {"ok": True, "cadence": cad}


class AffichageIn(BaseModel):
    actif: bool


@router.post("/admin/sources/{source_id}/affichage")
def admin_source_affichage(source_id: int, body: AffichageIn, request: Request) -> dict:
    """CONNEXIONS-2 Lot 6.3 (M2) — DÉSACTIVER / réactiver une source depuis le dashboard (admin seul).
    Écrit le flag `affichage_desactive` EN BASE (remplace `SOURCES_MASQUEES` en dur). Désactivée ⇒
    retirée de la vitrine (WHERE_AFFICHEES) ET les consommateurs (couches/outils) servent « source
    désactivée » via `sources_catalog.source_active`. Relu à la requête suivante (aucun cache)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        # ceinture : la colonne existe (heal boot) ; ADD IF NOT EXISTS pour une base jamais healée.
        c.execute(text("ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS affichage_desactive "
                       "boolean NOT NULL DEFAULT false"))
        n = c.execute(text("UPDATE data_sources SET affichage_desactive = :d WHERE id = :i"),
                      {"d": not body.actif, "i": source_id}).rowcount
    if not n:
        raise HTTPException(404, "Source introuvable.")
    return {"ok": True, "actif": body.actif, "affichage_desactive": not body.actif}


def _lancer_ingestion(nom: str) -> dict:
    """Lance — détaché, depuis la racine du repo — la commande d'ingestion EXISTANTE d'une source (la
    MÊME que le cron), journalisée dans un log fichier. Point de sortie UNIQUE du lancement d'ingestion
    (réutilisé par « Relancer » et par « Injecter cette version », X6). Lève HTTPException si aucune
    commande n'est connue (404) ou si le lancement échoue (500). NE fait AUCUNE ingestion en propre :
    il délègue au job existant."""
    import subprocess
    import sys
    from pathlib import Path
    from fastapi import HTTPException
    cmd = _relance_pour(nom)
    if not cmd:
        raise HTTPException(404, "Aucune commande d'ingestion connue pour cette source.")
    argv = list(cmd["argv"])
    if argv and argv[0] == "python":
        argv[0] = sys.executable          # le python du process (venv), jamais un python du PATH
    racine = Path(__file__).resolve().parents[3]
    log_path = f"/tmp/labuse-relance-{cmd['label']}.log"
    try:
        with open(log_path, "ab") as fh:
            subprocess.Popen(argv, cwd=str(racine), stdout=fh, stderr=fh, start_new_session=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Lancement impossible ({type(exc).__name__}).") from exc
    return {"label": cmd["label"], "log": log_path}


@router.post("/admin/sources/{source_id}/relancer")
def admin_source_relancer(source_id: int, request: Request) -> dict:
    """Relance l'ingestion d'une source dont la commande est CONNUE (même geste que le cron,
    détaché) — journalisée. Sans mapping : 404, le front n'affiche pas le bouton."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine, session_scope
    with engine().begin() as c:
        row = c.execute(text("SELECT name, source_millesime FROM data_sources WHERE id = :i"),
                        {"i": source_id}).mappings().first()
    if not row:
        raise HTTPException(404, "Source introuvable.")
    nom, servi = row["name"], row.get("source_millesime")
    r = _lancer_ingestion(nom)
    # SUITE-1 (S2.2) — UNE SEULE TRACE : tout lancement manuel (Recharger comme Injecter) écrit
    # `injection_lancee_at` + la version constatée. Recharger recharge la MÊME version → on trace le
    # millésime servi. Best-effort : les sources sans ligne de veille (manuelles) n'ont pas ce slot.
    with engine().begin() as c:
        c.execute(text("UPDATE source_veille SET injection_lancee_at = now(), injection_vu = :v,"
                       " updated_at = now() WHERE source_id = :i"), {"v": servi, "i": source_id})
    try:
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Sources",
                               titre=f"Ingestion rechargée à la main : {r['label']}",
                               detail=f"{nom} — recharge de la version servie {servi or '?'} "
                                      f"(même commande que le cron, détachée ; log {r['log']}).",
                               dedup=f"relance:{r['label']}:{datetime.now(tz=timezone.utc):%Y%m%d%H%M}")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "label": r["label"], "log": r["log"], "millesime": servi}


@router.post("/admin/sources/{source_id}/veille/injecter")
def admin_source_veille_injecter(source_id: int, request: Request) -> dict:
    """SENTINELLE-2 (X6) — « Injecter cette version » : le pont SUPERVISÉ entre « une nouvelle version
    est disponible » et l'ingestion. Sur CLIC HUMAIN de Vic (exiger_admin), lance le job d'ingestion
    EXISTANT de la source (`_lancer_ingestion`, même commande que le cron), et TRACE le geste dans
    source_veille (injection_lancee_at + le millésime amont injecté) pour un suivi VISIBLE au tableau.

    DOCTRINE INTACTE : la sentinelle n'ingère RIEN d'elle-même — aucune ingestion ne part sans ce clic.
    404 si la source n'est pas surveillée ou si aucune commande d'ingestion n'est connue (injection
    manuelle). Le suivi de l'exécution reste sur ingestion_runs / /healthz/crons (panneau CRON)."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine, session_scope
    with engine().begin() as c:
        r = c.execute(text(
            "SELECT d.name, v.dernier_vu, v.dernier_statut FROM source_veille v"
            " JOIN data_sources d ON d.id = v.source_id WHERE v.source_id = :i"),
            {"i": source_id}).mappings().first()
    if not r:
        raise HTTPException(404, "Cette source n'est pas surveillée (aucune ligne de veille).")
    nom, millesime = r["name"], r.get("dernier_vu")
    lance = _lancer_ingestion(nom)   # 404 si pas de commande connue → le front n'affiche pas le bouton
    with engine().begin() as c:      # trace du geste (suivi visible, X6)
        c.execute(text("UPDATE source_veille SET injection_lancee_at = now(), injection_vu = :v,"
                       " updated_at = now() WHERE source_id = :i"), {"v": millesime, "i": source_id})
    try:
        from .events import creer_notification
        with session_scope() as s:
            creer_notification(s, kind="systeme", compte_id=None, source="Veille sources",
                               titre=f"Injection lancée à la main : {nom}"
                                     + (f" → {millesime}" if millesime else ""),
                               detail=f"Job d'ingestion « {lance['label']} » lancé (même commande que le cron, "
                                      f"détachée). Suivi : panneau CRON / ingestion_runs. Log {lance['log']}.",
                               lien="/sources",
                               dedup=f"injection:{source_id}:{millesime or ''}:"
                                     f"{datetime.now(tz=timezone.utc):%Y%m%d%H%M}")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "label": lance["label"], "log": lance["log"], "millesime": millesime}


# ═══════════════════════════ FLUX-1 — la page « Flux » du dashboard ═══════════════════════════

@router.get("/admin/flux")
def admin_flux(request: Request) -> dict:
    """FLUX-1 (F1/F2/F3/F4) — la page Flux, construite depuis les métadonnées vivantes : la fourmilière
    (sources → moteurs → surfaces + run courant), le bandeau de mise à jour, le bloc Radar (accumulation),
    et la garde de cohérence exécutée en direct. Lecture seule ; AUCUN chiffre recalculé au front."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import bascule_flux, coherence_flux, flux
    from ..db import session_scope
    from ..pige import releves

    # RETOURS-8 (R4.2) — le Circuit restait bloqué sur « Chargement… » : UNE brique qui lève (radar,
    # runs, dernière bascule) faisait tomber TOUT l'endpoint, et la page ne rendait jamais. Chaque
    # brique est désormais ISOLÉE avec un repli TYPÉ valide (jamais un 500, jamais une forme cassée)
    # + une note d'erreur visible côté admin. `coherence` était déjà gardée ; on généralise à tout.
    #
    # RETOURS-9 (Q1) — le Circuit affichait ENCORE « Chargement… » chez Vic : le repli marchait, mais
    # sur la base réelle l'endpoint mettait ~55 s (mesuré). Cause exacte : `runs_termines` calcule,
    # pour chacun des runs non-servis, l'écart au run courant (`comparer()` ~5 s + un COUNT self-join
    # sur parcel_p_score_v2, 3 M lignes) → ~50 s à lui seul. Le front attend la charge COMPLÈTE avant
    # de rendre (`if (!d) Chargement…`). On sort donc les runs de la charge initiale : `/admin/flux`
    # ne garde que les briques rapides (~6 s, coherence domine) et rend le Circuit tout de suite ;
    # les runs terminés + écarts arrivent en RENDU PROGRESSIF via `/admin/flux/runs` (2e requête).
    def _garde(label, fn, repli):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — une brique qui casse ne bloque plus le Circuit
            erreurs.append(f"{label}: {type(e).__name__}: {e}"[:160])
            return repli

    _FLUX_VIDE = {"run": None, "sources": [], "moteurs": [], "surfaces": [],
                  "comptes": {"total": 0, "surveillees": 0, "nouvelle_version": 0,
                              "plus_recentes_que_run": 0, "n_surfaces": 0},
                  "plus_recentes": [], "genere_le": None}
    _RADAR_VIDE = {"compteurs": {}, "ecart": [], "courbe": {"points": [], "depuis_le": None}}
    erreurs: list[str] = []
    with session_scope() as s:
        fourmiliere = _garde("flux", lambda: flux.construire_flux(s), _FLUX_VIDE)
        radar = _garde("radar", lambda: releves.bloc_radar(s), _RADAR_VIDE)
        coherence = _garde("coherence", lambda: coherence_flux.verifier(s),
                           {"ok": None, "checks": []})
        # Q1 — les runs terminés (coûteux) NE sont plus dans la charge initiale : rendu progressif
        # via /admin/flux/runs. On garde seulement `derniere` (0,01 s) pour le bandeau « Basculer ».
        derniere = _garde("derniere", lambda: bascule_flux.derniere_bascule(s), None)
    return {"flux": fourmiliere, "radar": radar, "coherence": coherence,
            "bascule": {"derniere": derniere},
            # R4.2 — si une brique a lâché, la page rend quand même (repli) et DIT quoi a échoué.
            "erreurs": erreurs or None}


@router.get("/admin/flux/runs")
def admin_flux_runs(request: Request) -> dict:
    """La liste des runs terminés + écart au run courant (F2.3), rafraîchie seule (poll pendant un run)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import bascule_flux
    from ..db import session_scope
    with session_scope() as s:
        return {"runs": bascule_flux.runs_termines(s), "derniere": bascule_flux.derniere_bascule(s)}


def _estimation_run(db) -> str:
    """Durée estimée d'un run = durée du dernier run scoré si connue, sinon repli honnête (~3 h,
    la cascade domine). Purement indicatif (affiché à côté du bouton « Lancer un run »)."""
    d = db.execute(text(
        "SELECT duration_s FROM p_score_v2_runs WHERE duration_s IS NOT NULL "
        "ORDER BY computed_at DESC LIMIT 1")).scalar()
    if not d:
        return "~3 h estimées (cascade + scoring)"
    # le score-v2 seul (duration_s) sous-estime : la cascade des 24 communes domine. On borne au-dessus.
    minutes = max(30, int(d / 60) + 120)
    return f"~{minutes // 60} h {minutes % 60:02d} estimées" if minutes >= 60 else f"~{minutes} min estimées"


class LancerRunIn(BaseModel):
    # SCORING-3 (L1) — recette du scoring : m36 (servie) ou q_v12 (candidat gelé).
    recette: str = Field(default="m36", pattern="^(m36|q_v12)$")


@router.post("/admin/flux/run/lancer")
def admin_flux_lancer_run(request: Request, body: LancerRunIn | None = None) -> dict:
    """FLUX-1 (F2.2) — LANCE un run comme un JOB détaché (même mécanique que « Injecter », X6) : la
    commande CLI `flux-run` chaîne le pipeline EXISTANT (cascade + score-v2, aucune réécriture). Le run
    n'est PAS servi (la bascule reste manuelle). Retourne le label lancé + une durée estimée + le log.
    SCORING-3 (L1) — `recette` optionnelle : q_v12 lance le MÊME pipeline avec l'artefact candidat gelé."""
    import subprocess
    import sys
    from pathlib import Path
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import run_progress
    from ..db import engine, session_scope
    # DONNEES-2 (B3) — UN SEUL run à la fois : réconcilie l'état (les runs tués passent « abandonné »)
    # puis REFUSE de lancer si un run est réellement EN COURS (process vivant). Sinon deux runs se
    # marcheraient dessus (mêmes tables dryrun_*).
    with engine().begin() as c:
        complets = {r[0] for r in c.execute(text("SELECT run_id FROM p_score_v2_runs")).all()}
    run_progress.reconcile(complets)
    encours = run_progress.en_cours()
    if encours:
        raise HTTPException(409, f"Un run est déjà en cours ({encours.get('label')}) — arrêtez-le "
                                 f"ou attendez sa fin avant d'en lancer un autre.")
    recette = body.recette if body else "m36"
    prefixe = "q_v12" if recette == "q_v12" else "q_flux"
    label = f"{prefixe}_{datetime.now(tz=timezone.utc):%Y%m%d_%H%M}"
    if label in complets:
        raise HTTPException(409, f"Un run « {label} » existe déjà — réessayer dans une minute.")
    # SCORING-3 — `-m labuse.cli` (module exécutable), PAS `-m labuse` : le paquet n'a pas de
    # __main__.py, l'ancien argv échouait silencieusement dans le log (constaté au run q_v12).
    argv = [sys.executable, "-m", "labuse.cli", "flux-run", "--label", label, "--recette", recette]
    racine = Path(__file__).resolve().parents[3]
    log_path = f"/tmp/labuse-flux-run-{label}.log"
    try:
        with open(log_path, "ab") as fh:
            proc = subprocess.Popen(argv, cwd=str(racine), stdout=fh, stderr=fh, start_new_session=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Lancement impossible ({type(exc).__name__}).") from exc
    # DONNEES-2 (B3) — ouvre l'état AVEC le pid du process détaché (celui que « Arrêter » signalera) ;
    # le process flux-run le ré-ouvrira avec sa progression réelle dès qu'il démarre.
    run_progress.start(label, pid=proc.pid, kind="run", recette=recette, log=log_path)
    with session_scope() as s:
        estimation = _estimation_run(s)
        try:
            from .events import creer_notification
            creer_notification(s, kind="systeme", compte_id=None, source="Flux",
                               titre=f"Run lancé à la main : {label}",
                               detail=f"Pipeline existant (cascade + score-v2) chaîné, détaché. "
                                      f"{estimation}. Non servi — bascule manuelle. Log {log_path}.",
                               lien="/admin", dedup=f"flux-run:{label}")
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "label": label, "estimation": estimation, "log": log_path}


class ArreterRunIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)


@router.post("/admin/flux/run/arreter")
def admin_flux_arreter_run(request: Request, body: ArreterRunIn) -> dict:
    """DONNEES-2 (B3) — ARRÊT PROPRE d'un run en cours : SIGTERM au groupe de process (le run est
    détaché, chef de son groupe), puis l'état passe « abandonné ». Geste humain, tracé."""
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import run_progress
    res = run_progress.stop(body.label)
    if not res.get("ok"):
        raise HTTPException(404, res.get("motif", "run inconnu"))
    return res


@router.get("/admin/flux/run/etat")
def admin_flux_run_etat(request: Request) -> dict:
    """DONNEES-2 (B3) — l'ÉTAT du run en cours (phase, commune, %, pid), pour la barre de l'étape 2.
    Léger : lu des fichiers d'état, réconcilié (un run mort n'apparaît plus « en cours »)."""
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import run_progress
    from ..db import engine
    with engine().begin() as c:
        complets = {r[0] for r in c.execute(text("SELECT run_id FROM p_score_v2_runs")).all()}
    run_progress.reconcile(complets)
    return {"en_cours": run_progress.en_cours()}


class BasculeIn(BaseModel):
    run: str = Field(min_length=1, max_length=64)


@router.post("/admin/flux/bascule")
def admin_flux_bascule(request: Request, body: BasculeIn) -> dict:
    """FLUX-1 (F2.3/F2.4) — BASCULE le run courant vers `run` (ou retour arrière si c'est le précédent).
    Refuse un run incomplet ; sinon promeut le pointeur, fait suivre le précédent, PURGE les caches A6,
    JOURNALISE (qui/quand/de/vers) et exécute la garde de cohérence immédiatement. Geste humain."""
    import subprocess
    import sys
    from pathlib import Path
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from .. import bascule_flux
    from ..db import session_scope
    qui = getattr(getattr(request, "state", None), "compte_email", None) or "admin"
    with session_scope() as s:
        res = bascule_flux.basculer(s, body.run, par=str(qui))
        if not res.get("ok"):
            raise HTTPException(409, res.get("motif", "bascule refusée"))
        try:
            from .events import creer_notification
            creer_notification(s, kind="systeme", compte_id=None, source="Flux",
                               titre=f"Bascule de run : {res['ancien']} → {res['nouveau']}",
                               detail=f"Caches purgés : {', '.join(res['caches_purges']) or 'aucun'}. "
                                      f"Cohérence : {'OK' if res['coherence'].get('ok') else 'à vérifier'}. "
                                      f"{res['note']}",
                               lien="/admin", dedup=f"bascule:{res['nouveau']}:{datetime.now(tz=timezone.utc):%Y%m%d%H%M}")
        except Exception:  # noqa: BLE001
            pass
    # DONNEES-2 (B1) — les tables SERVIES run-scopées (parcel_flags · parcel_renouvellement · score_e)
    # et les tuiles carte ne « montent DANS le geste » que maintenant : la bascule LANCE, DÉTACHÉ, la
    # reconstruction pour le NOUVEAU run (`build-mvt`, le geste unique M48). On ne la fait PAS en ligne :
    # un DROP TABLE prend un verrou exclusif qui DEADLOCK avec les lectures de la garde (constaté). Tant
    # qu'elle tourne, la garde reste à 5/6 (tables encore sur l'ancien run) ; elle repasse 6/6 à la fin.
    reconstruction = None
    try:
        racine = Path(__file__).resolve().parents[3]
        rlog = f"/tmp/labuse-build-mvt-{res['nouveau']}.log"
        argv = [sys.executable, "-m", "labuse.cli", "build-mvt", "--label", res["nouveau"]]
        with open(rlog, "ab") as fh:
            subprocess.Popen(argv, cwd=str(racine), stdout=fh, stderr=fh, start_new_session=True)
        reconstruction = {"lancee": True, "run": res["nouveau"], "log": rlog}
    except Exception as exc:  # noqa: BLE001
        reconstruction = {"lancee": False, "motif": f"{type(exc).__name__}"}
    res["reconstruction"] = reconstruction
    return res


# ───────────────────────── D7 — PRODUIT ─────────────────────────
@router.get("/admin/produit")
def admin_produit(request: Request, jours: int = 30) -> dict:
    """Usage par outil sur la PÉRIODE choisie (ADMIN-1 AD7 : 7 / 30 / 90 j, défaut 30) + retours clients.
    Le bloc « jamais ouverts » est calculé côté front (catalogue registry.ts − outils vus). Les « retours
    clients » de la page Produit refondue s'appuient désormais sur la file signalements unifiée
    (/admin/signalements) — la table `retours` reste servie ici pour compat mais n'alimente plus l'UI."""
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    jours = jours if jours in (7, 30, 90) else 30
    with engine().begin() as c:
        usage = [dict(r) for r in c.execute(text(
            "SELECT outil, COUNT(*) AS n FROM usage_events"
            " WHERE kind = 'outil' AND outil IS NOT NULL AND ts > now() - make_interval(days => :j)"
            " GROUP BY outil ORDER BY COUNT(*) DESC"), {"j": jours}).mappings()]
        retours = [dict(r) for r in c.execute(text(
            "SELECT r.id, r.ts, r.type, r.message, r.statut, r.idu, r.section, k.nom AS compte"
            " FROM retours r LEFT JOIN comptes k ON k.id = r.compte_id"
            " ORDER BY r.ts DESC LIMIT 200")).mappings()]
    for r in retours:
        r["ts"] = r["ts"].isoformat() if r["ts"] else None
        # RETOURS-11F M11 — lien cliquable vers la fiche d'origine (retour « donnée » posé depuis la fiche).
        r["fiche_lien"] = (f"#idu={r['idu']}" if r.get("idu") else None)
    return {"usage": usage, "retours": retours, "jours": jours}


class RetourStatutIn(BaseModel):
    statut: str = Field(pattern="^(nouveau|traite|repondu)$")


@router.post("/admin/retours/{retour_id}/statut")
def admin_retour_statut(retour_id: int, body: RetourStatutIn, request: Request) -> dict:
    from fastapi import HTTPException
    from .auth import exiger_admin
    exiger_admin(request)
    from ..db import engine
    with engine().begin() as c:
        n = c.execute(text(
            "UPDATE retours SET statut = :s, updated_at = now() WHERE id = :i"),
            {"s": body.statut, "i": retour_id}).rowcount
    if not n:
        raise HTTPException(404, "Retour introuvable.")
    return {"ok": True, "statut": body.statut}


# ───────────────────────── quota Copilote PAR LICENCE ─────────────────────────
#: CONNEXIONS-2 Lot 2 (KO-3) — kind UNIQUE du compteur de quota Copilote, partagé par /ia (recherche
#: NL) ET /api/copilote-v2/ask. Un seul compteur, un seul plafond (`quota_du_compte`), une seule
#: fonction : l'admin édite `copilote_quota_jour` au dashboard et les DEUX surfaces la respectent.
#: (Avant : /ia comptait 'nl' plafonné per-compte, /ask comptait 'copilote_v2_ask' plafonné GLOBAL
#: `copilote_v2_missions_jour` — l'override dashboard était ignoré par le Copilote réellement servi.)
QUOTA_COPILOTE_KIND = "copilote"


def _fmt_eur(x: float) -> str:
    """2.0 → « 2,00 € » (virgule décimale française)."""
    return f"{float(x):.2f} €".replace(".", ",")


def budget_eur_du_compte(compte_id: int | None) -> float:
    """RETOURS-8 (R3) — le PLAFOND en euros/jour de CE compte : l'override licence
    (comptes.copilote_budget_eur), sinon le défaut config (2,00 €)."""
    from .. import config
    defaut = float(config.get_settings().copilote_budget_eur_defaut)
    if compte_id is None:
        return defaut
    try:
        from ..db import engine
        with engine().begin() as c:
            v = c.execute(text("SELECT copilote_budget_eur FROM comptes WHERE id = :c"),
                          {"c": compte_id}).scalar()
        return float(v) if v is not None else defaut
    except Exception:  # noqa: BLE001 — best-effort : jamais bloquer une question sur une panne
        return defaut


def cout_moyen_appel(compte_id: int | None) -> float:
    """RETOURS-8 (R3) — coût moyen RÉEL d'un appel IA sur 30 jours : d'abord pour CE compte, sinon le
    coût moyen global, sinon le plancher config (0,008 €). Sert à convertir le plafond € en « ≈ N
    questions » et à afficher le coût unitaire. Jamais 0 (division protégée)."""
    from .. import config
    plancher = float(config.get_settings().copilote_cout_moyen_defaut)
    try:
        from ..db import engine
        with engine().connect() as c:
            if compte_id is not None:
                r = c.execute(text(
                    "SELECT COALESCE(SUM(cout_eur), 0) AS s, COUNT(*) AS n FROM ia_log"
                    " WHERE compte_id = :c AND ts > now() - interval '30 days'"),
                    {"c": compte_id}).mappings().one()
                if r["n"] and float(r["s"]) > 0:
                    return float(r["s"]) / int(r["n"])
            g = c.execute(text(
                "SELECT COALESCE(SUM(cout_eur), 0) AS s, COUNT(*) AS n FROM ia_log"
                " WHERE ts > now() - interval '30 days'")).mappings().one()
            if g["n"] and float(g["s"]) > 0:
                return float(g["s"]) / int(g["n"])
    except Exception:  # noqa: BLE001
        pass
    return plancher


def quota_du_compte(compte_id: int | None) -> dict | None:
    """RETOURS-8 (R3) — LA fonction unique du plafond Copilote/IA, désormais en EUROS. Rend un budget
    € ET son équivalent en appels (au coût moyen réel du compte). None si pas de compte connecté
    (pilote/anonyme → l'appelant garde son plafond historique en appels, nl_quota_jour)."""
    if compte_id is None:
        return None
    budget = budget_eur_du_compte(compte_id)
    cmoy = cout_moyen_appel(compte_id)
    equiv = int(budget / cmoy) if cmoy > 0 else None
    return {"budget_eur": budget, "cout_moyen_eur": cmoy, "equiv_appels": equiv}


#: alias rétro-compatible (l'ancien nom pointe sur la fonction unifiée — plus de divergence).
quota_nl_du_compte = quota_du_compte


def depense_eur_aujourdhui(compte_id: int) -> float:
    """RETOURS-8 (R3) — la DÉPENSE IA en euros AUJOURD'HUI (jour Réunion) pour ce compte, lue du
    ledger ia_log (missions lourdes Sonnet comprises, à leur coût réel). Base du plafond en €."""
    from ..db import engine
    try:
        with engine().connect() as c:
            v = c.execute(text(
                "SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log"
                " WHERE compte_id = :c AND (ts AT TIME ZONE 'Indian/Reunion')::date"
                "       = (now() AT TIME ZONE 'Indian/Reunion')::date"), {"c": compte_id}).scalar()
        return float(v or 0)
    except Exception:  # noqa: BLE001 — best-effort, jamais un 500
        return 0.0


def consomme_copilote_aujourdhui(compte_id: int) -> int:
    """Nombre d'appels IA du compte AUJOURD'HUI (jour Réunion) — pour la mention « en petit » sous le
    compteur en euros. Lu du compteur unique (kind `QUOTA_COPILOTE_KIND`, scope `c:<id>`)."""
    from ..tz import today_reunion
    from .protection import compteur
    from ..db import engine
    try:
        with engine().connect() as c:
            return compteur(c, f"c:{compte_id}", QUOTA_COPILOTE_KIND, today_reunion().isoformat())
    except Exception:  # noqa: BLE001 — best-effort, jamais un 500 sur le dashboard
        return 0


def etat_plafond_ia(compte_id: int | None, sujet: str, jour_iso: str, *, nl_defaut: int) -> dict | None:
    """RETOURS-8 (R3) — LA garde unique du plafond IA, partagée par /ia, /ask et les missions lourdes.
    Incrémente TOUJOURS le compteur d'appels (mention « appels » de la tuile), puis :
      · compte connecté → plafond en EUROS : dépense du jour ≥ budget € → dépassement ;
      · sans compte (pilote/anonyme) → plafond historique en APPELS (nl_defaut).
    Rend None si tout va bien, sinon un `detail` prêt à servir en 429 (mêmes clés qu'avant + budget)."""
    from .protection import compteur_incr_et_lire
    n = compteur_incr_et_lire(jour_iso, sujet, QUOTA_COPILOTE_KIND)
    if compte_id is None:
        if n > nl_defaut:
            return {"detail": f"Quota d'analyses IA atteint ({nl_defaut}/jour). Reprend à minuit.",
                    "quota": nl_defaut, "gel_jusqua": "minuit"}
        return None
    budget = budget_eur_du_compte(compte_id)
    depense = depense_eur_aujourdhui(compte_id)
    if depense >= budget:
        return {"detail": f"Plafond IA du jour atteint ({_fmt_eur(budget)}/jour). Reprend à minuit.",
                "budget_eur": round(budget, 2), "depense_eur": round(depense, 4), "gel_jusqua": "minuit"}
    return None
