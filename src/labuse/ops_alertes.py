"""SOLIDITE-1 (Lot 1.2/1.3) — L'ALERTE D'EXPLOITATION, UNE SEULE PORTE.

La semaine du 07/10 a montré que le danger n'est pas le code mais le SILENCE : une sauvegarde cassée six
jours, dix-neuf tâches mortes, un disque à 96 %, sans qu'aucune alerte ne parte. Ce module est la porte
unique par laquelle toute panne d'exploitation devient visible le jour même :

  · `signaler(cle, sujet, detail)` — ouvre un INCIDENT (mail à Vic + cloche admin), UNE fois. Tant qu'il
    n'est pas résolu : AU PLUS un rappel par jour (pas de déluge). `cle` identifie l'incident (ex.
    'job-echec:backup-postgres', 'disque', 'readyz') : deux appels pour la même panne ne font qu'un.
  · `resoudre(cle)` — si l'incident était ouvert, envoie UN mail « résolu » et le referme. Sinon : rien.
  · `verifier_declencheurs(db)` — évalue d'un coup les cinq vigies qui n'ont pas de point d'appel
    naturel ailleurs (disque, /readyz, sauvegarde, copie externe, jobs en retard) et ouvre/referme les
    incidents. Les
    ÉCHECS de job, eux, sont signalés en direct par `jobs.exec_one` (une alerte à l'instant de l'échec).

RÈGLE DRY-RUN (comme tout le reste de LABUSE) : sans SMTP, le mail est écrit en `.eml` (preuve), marqué
'dry-run', rien ne part sur le réseau. L'incident est quand même ouvert/refermé en base (la vigie
fonctionne, seule la notification est différée).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from .config import get_settings
from .tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (D-04) — le « jour » de dédup = jour Réunion

log = logging.getLogger("labuse.ops")

DDL = """
CREATE TABLE IF NOT EXISTS ops_incidents (
  id serial PRIMARY KEY,
  cle varchar(96) NOT NULL,
  sujet text NOT NULL,
  detail text,
  ouvert_at timestamptz NOT NULL DEFAULT now(),
  premier_envoi_at timestamptz,
  dernier_envoi_at timestamptz,
  rappels integer NOT NULL DEFAULT 0,
  resolu_at timestamptz
)
"""
# un seul incident OUVERT par clé (index partiel) : deux déclenchements de la même panne ne s'empilent pas.
DDL_INDEX = ("CREATE UNIQUE INDEX IF NOT EXISTS ux_ops_incidents_cle_ouvert "
             "ON ops_incidents (cle) WHERE resolu_at IS NULL")

PREFIX = "[LABUSE]"


def ensure_table(db) -> None:
    """ORF-02 (FIX-ORFEVRE-1) — plus AUCUNE DDL sur le chemin d'alerte quand le schéma est en place :
    `signaler()` passait par CREATE TABLE/CREATE UNIQUE INDEX « IF NOT EXISTS » à CHAQUE appel ; pendant
    la fenêtre pg_dump 13:30-13:48, ces DDL attendaient le verrou → timeout 120 s → l'alerte disque ne
    s'écrivait JAMAIS au moment précis où le disque franchissait le seuil (journaux prod 14-18/10).
    La garde est une lecture des catalogues (to_regclass) : zéro verrou, jouable pendant le backup."""
    present = db.execute(text(
        "SELECT to_regclass('ops_incidents') IS NOT NULL "
        "AND to_regclass('ux_ops_incidents_cle_ouvert') IS NOT NULL")).scalar()
    if present:
        return
    db.execute(text(DDL))
    db.execute(text(DDL_INDEX))


#: ORF-02 — fichier de REPLI : quand l'alerte elle-même ne peut pas s'écrire en base (base verrouillée,
#: injoignable…), elle doit exister QUELQUE PART. Une ligne JSON horodatée par alerte, dans le répertoire
#: d'état des jobs (toujours inscriptible par le user du service), en plus de stderr/journald (log.error).
FICHIER_REPLI = "ops_alertes_repli.log"


def repli_local(cle: str, sujet: str, detail: str, erreur: str) -> Path | None:
    """Écrit l'alerte en LOCAL (fichier + stderr/journald) quand la base est indisponible. Ne lève
    jamais : le repli qui rate laisse au moins la trace stderr. Retourne le chemin écrit (ou None)."""
    log.error("ALERTE OPS EN REPLI (base indisponible : %s) — %s : %s — %s", erreur, cle, sujet, detail)
    try:
        d = Path(get_settings().jobs_state_dir)
        d.mkdir(parents=True, exist_ok=True)
        p = d / FICHIER_REPLI
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "quand": datetime.now(timezone.utc).isoformat(), "cle": cle, "sujet": sujet,
                "detail": detail, "erreur_base": erreur}, ensure_ascii=False) + "\n")
        return p
    except Exception:  # noqa: BLE001 — le repli ne doit jamais faire tomber la sonde
        log.error("repli local d'alerte impossible (le log ci-dessus reste la seule trace)")
        return None


def _destinataire(s) -> str | None:
    """À QUI partent les alertes : LABUSE_ADMIN_EMAIL en priorité, sinon le contact (victor@labuse.immo)."""
    return s.admin_email or s.contact_email


# ─────────────────────────────── la porte d'envoi unique ───────────────────────────────

def _sink(db, sujet: str, corps: str, *, dedup: str) -> str:
    """Envoie l'alerte par les DEUX canaux : mail (Brevo/SMTP via la façade `mail`) + cloche admin.
    Retourne le détail d'envoi mail ('ok' | 'dry-run' | 'no-config' | 'error: …'). Jamais bloquant :
    la cloche qui rate ne doit pas empêcher le mail, et inversement."""
    s = get_settings()
    detail_mail = "pas-de-destinataire"
    dest = _destinataire(s)
    if dest:
        try:
            from .mail import envoyer_ops
            detail_mail = envoyer_ops(dest, sujet, corps, settings=s).detail
        except Exception as exc:  # noqa: BLE001 — l'échec d'envoi ne casse pas la vigie
            detail_mail = f"error: {type(exc).__name__}"
            log.warning("alerte ops : mail impossible (%s)", exc)
    try:
        from .api.events import creer_notification
        creer_notification(db, kind="systeme", compte_id=None, source="Exploitation",
                           titre=sujet.replace(PREFIX, "").strip(), detail=(corps or "")[:500],
                           lien="/admin", dedup=dedup)
    except Exception as exc:  # noqa: BLE001 — la cloche qui rate ne casse pas l'alerte mail
        log.warning("alerte ops : cloche impossible (%s)", exc)
    log.info("alerte ops « %s » — mail=%s", sujet, detail_mail)
    return detail_mail


# ─────────────────────────────── incidents (ouvrir / rappeler / résoudre) ───────────────────────────────

def signaler(db, cle: str, sujet: str, detail: str) -> str:
    """Ouvre l'incident `cle` s'il n'existe pas (→ 'ouvert', une alerte part), ou le rappelle AU PLUS une
    fois par jour (→ 'rappel'), sinon met juste à jour le détail sans rien envoyer (→ 'silence').
    Le `sujet`/`detail` reçus rafraîchissent toujours l'incident (dernier état connu)."""
    ensure_table(db)
    row = db.execute(text(
        "SELECT id, dernier_envoi_at FROM ops_incidents WHERE cle = :c AND resolu_at IS NULL"),
        {"c": cle}).mappings().first()
    sujet_mail = f"{PREFIX} {sujet}"
    if row is None:
        db.execute(text(
            "INSERT INTO ops_incidents (cle, sujet, detail, premier_envoi_at, dernier_envoi_at, rappels) "
            "VALUES (:c, :s, :d, now(), now(), 0)"), {"c": cle, "s": sujet, "d": detail})
        _sink(db, sujet_mail, detail + "\n\n— LABUSE, exploitation", dedup=f"ops:{cle}:ouvert")
        return "ouvert"
    # FIX-ORFEVRE-1 pt 3 (D-04) — UNE SEULE définition du « jour » de dédup des alertes : le jour
    # RÉUNION (comme protection._aujourdhui et les clés de jobs_impl). Avant : jour UTC ici, jour
    # process dans jobs_impl → autour de 04:00 Réunion un rappel pouvait partir deux fois ou être
    # retenu un jour de plus. Fuseau EXPLICITE dans le SQL (indépendant du timezone de session).
    deja_aujourdhui = db.execute(text(
        "SELECT (dernier_envoi_at AT TIME ZONE 'Indian/Reunion')::date "
        "= (now() AT TIME ZONE 'Indian/Reunion')::date "
        "FROM ops_incidents WHERE id = :i"), {"i": row["id"]}).scalar()
    if deja_aujourdhui:
        db.execute(text("UPDATE ops_incidents SET sujet = :s, detail = :d WHERE id = :i"),
                   {"s": sujet, "d": detail, "i": row["id"]})
        return "silence"
    db.execute(text(
        "UPDATE ops_incidents SET sujet = :s, detail = :d, dernier_envoi_at = now(), "
        "rappels = rappels + 1 WHERE id = :i"), {"s": sujet, "d": detail, "i": row["id"]})
    jour = today_reunion().isoformat()   # FIX-ORFEVRE-1 pt 3 (D-04) — même jour que le test SQL ci-dessus
    _sink(db, f"{sujet_mail} (toujours ouvert)",
          detail + "\n\nIncident non résolu depuis l'ouverture — rappel quotidien.\n— LABUSE, exploitation",
          dedup=f"ops:{cle}:{jour}")
    return "rappel"


def _escalade(db, cle: str, sujet: str, detail: str) -> str:
    """FIX-NU3-3 (décision Vic) — l'ESCALADE d'une alerte critique (sauvegarde HS > 24 h, automate jamais
    réussi, Radar muet 2 nuits). Passe par la MÊME porte que `signaler` (mail à l'adresse de Vic +
    cloche, un envoi puis au plus un rappel par jour tant que ça dure) mais avec un sujet EXPLICITE
    préfixé « ESCALADE — » : Vic reçoit un mail clairement critique, distinct de l'incident ordinaire,
    au moment où la panne franchit le cran du dessus. `cle` préfixée `escalade:` (titre rouge dédié)."""
    return signaler(db, cle, f"ESCALADE — {sujet}", detail)


def resoudre(db, cle: str) -> bool:
    """Referme l'incident `cle` s'il était ouvert (→ True, un mail « résolu » part). Sinon rien (→ False :
    on n'envoie JAMAIS un « résolu » pour un incident qui n'existait pas — pas de bruit)."""
    ensure_table(db)
    row = db.execute(text(
        "SELECT id, sujet, ouvert_at FROM ops_incidents WHERE cle = :c AND resolu_at IS NULL"),
        {"c": cle}).mappings().first()
    if row is None:
        return False
    db.execute(text("UPDATE ops_incidents SET resolu_at = now() WHERE id = :i"), {"i": row["id"]})
    ouvert = row["ouvert_at"]
    if ouvert is not None:
        ouvert = (ouvert if ouvert.tzinfo else ouvert.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    depuis = ouvert.strftime("%d/%m %H:%M") if ouvert else "?"
    _sink(db, f"{PREFIX} résolu — {row['sujet']}",
          f"L'incident ouvert le {depuis} (UTC) est résolu.\n— LABUSE, exploitation",
          dedup=f"ops:{cle}:resolu")
    return True


def incidents_ouverts(db) -> list[dict]:
    """Les incidents encore ouverts (pour le récap du matin + la page admin)."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT cle, sujet, detail, ouvert_at, dernier_envoi_at, rappels FROM ops_incidents "
        "WHERE resolu_at IS NULL ORDER BY ouvert_at")).mappings().all()
    return [{**dict(r), "ouvert_at": r["ouvert_at"].isoformat(),
             "dernier_envoi_at": r["dernier_envoi_at"].isoformat() if r["dernier_envoi_at"] else None}
            for r in rows]


# ─────────────────────────────── les vigies sans point d'appel naturel ───────────────────────────────

def _readyz_local() -> tuple[bool, str]:
    """Sonde /readyz EN LOCAL (le process servi, pas l'URL publique). Port surchargeable par
    LABUSE_HEALTH_PORT (défaut 8000 = prod). Retourne (ready, détail)."""
    import json as _json
    import urllib.request
    port = os.environ.get("LABUSE_HEALTH_PORT", "8000")
    url = f"http://127.0.0.1:{port}/readyz"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            corps = resp.read().decode("utf-8", "replace")
            ready = resp.status == 200
    except urllib.error.HTTPError as e:   # 503 = pas prêt → on lit quand même le corps
        corps = e.read().decode("utf-8", "replace") if hasattr(e, "read") else str(e)
        ready = False
    except Exception as exc:  # noqa: BLE001 — injoignable = pas prêt
        return False, f"injoignable : {type(exc).__name__}"
    try:
        d = _json.loads(corps)
        motif = d.get("error") or ("prêt" if ready else "ready=false")
    except ValueError:
        motif = "réponse illisible"
    return ready, motif


def _dumps(backup_dir: str) -> list[Path]:
    """Les dumps de sauvegarde présents, du plus récent au plus ancien (formats .dump et .sql.gz).
    Dossier absent ou illisible (poste de dev sans /var/backups) → liste vide, jamais d'exception."""
    try:
        p = Path(backup_dir)
        if not p.exists():
            return []
        fichiers = list(p.glob("labuse-*.dump")) + list(p.glob("labuse-*.sql.gz"))
        return sorted(fichiers, key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return []


# DISQUE-EXTERNE-1 (14/10) — la copie hors-VPS vit sur le disque externe du Mac. Après chaque copie
# VÉRIFIÉE (sha256 + pg_restore --list), le Mac dépose ce marqueur dans backup_dir (via ssh, utilisateur
# labuse). Le VPS ne fait que le LIRE : il ne pousse plus rien lui-même. C'est volontairement un fichier
# (pas la DB) pour que l'écriture par le Mac ne dépende d'aucun code applicatif déployé.
MARQUEUR_COPIE_EXTERNE = ".copie-externe.json"


def lire_copie_externe(backup_dir: str) -> dict | None:
    """Le marqueur de la dernière copie hors-VPS, ou None s'il est absent/illisible/mal formé.
    Renvoie {copie_at: datetime (tz-aware), dump, sha256, taille_mo, disque}. Jamais d'exception."""
    try:
        p = Path(backup_dir) / MARQUEUR_COPIE_EXTERNE
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        brut = d.get("copie_at")
        if not brut:
            return None
        quand = datetime.fromisoformat(str(brut).replace("Z", "+00:00"))
        if quand.tzinfo is None:
            quand = quand.replace(tzinfo=timezone.utc)
        return {"copie_at": quand, "dump": d.get("dump"), "sha256": d.get("sha256"),
                "taille_mo": d.get("taille_mo"), "disque": d.get("disque")}
    except (OSError, ValueError, TypeError):
        return None


# DONNEES-ETAT-FIX-2 (Lot A) — marqueur du test de restauration mensuel (écrit par l'agent Mac
# deploy/mac/restore_test.sh). Même esprit que la copie externe : un FICHIER lu par le Tableau de bord,
# indépendant de tout code applicatif déployé. Statut : ok | ko | refuse.
MARQUEUR_RESTORE_TEST = ".restore-test.json"


def lire_restore_test(backup_dir: str) -> dict | None:
    """Le marqueur du dernier test de restauration, ou None s'il est absent/illisible. Renvoie le dict
    tel qu'écrit par restore_test.sh : {test_at, statut, message, dump, run_servi, run_servi_lignes,
    tables, min_go}. Jamais d'exception."""
    try:
        p = Path(backup_dir) / MARQUEUR_RESTORE_TEST
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and d.get("statut") else None
    except (OSError, ValueError, TypeError):
        return None


def _intervalle_s(cron_utc: str) -> float | None:
    """Secondes entre deux exécutions consécutives d'une planif cron (via le parseur du registre).
    None si on ne peut pas trouver deux occurrences sous l'horizon (planif très rare)."""
    from .jobs import prochaine
    p1 = prochaine(cron_utc, horizon_jours=60)
    if p1 is None:
        return None
    p2 = _prochaine_apres(cron_utc, p1)   # la PROCHAINE occurrence strictement après p1
    if p2 is None:
        return None
    return (p2 - p1).total_seconds()


def _prochaine_apres(cron_utc: str, apres: datetime) -> datetime | None:
    from datetime import timedelta
    from .jobs import _champ_match
    m, h, dom, mon, dow = cron_utc.split()
    t = apres.replace(second=0, microsecond=0) + timedelta(minutes=1)
    fin = t + timedelta(days=60)
    while t < fin:
        cron_dow = (t.weekday() + 1) % 7
        if (_champ_match(t.minute, m) and _champ_match(t.hour, h) and _champ_match(t.day, dom)
                and _champ_match(t.month, mon) and _champ_match(cron_dow, dow)):
            return t
        t += timedelta(minutes=1)
    return None


def _jobs_en_retard(db) -> list[dict]:
    """Les jobs planifiés qui ne sont pas à l'heure. FIX-NU3-3 (I-ADM-01/03, L-JOB-01) — trois motifs,
    plus seulement « a tourné puis s'est tu » :

      · `bloque`  — dernier état « en_cours » dépassé (tué en plein run, verrou figé) : I-ADM-03 ;
      · `jamais`  — planifié, jamais réussi, alors que le SYSTÈME tourne depuis plus d'une cadence
                    (cron jamais tiré OU premier passage qui échoue en boucle) : I-ADM-01/L-JOB-01 ;
      · `stale`   — dernier succès > 1,5 × cadence (les 19 tâches mortes historiques).

    Un job GELÉ (gel volontaire) ou NON planifié (manuel seul) n'est jamais compté : son silence est
    voulu. Chaque entrée porte `motif` pour que la vigie choisisse la bonne clé d'incident + escalade."""
    from .jobs import JOBS, bloque_depuis, lire_etat
    succes = {}
    premiere = None
    try:
        from . import jobs_journal
        succes = jobs_journal.dernier_succes(db)
        premiere = jobs_journal.premiere_activite(db)
    except Exception as exc:  # noqa: BLE001
        log.warning("retards : historique job_runs illisible (%s)", exc)
    if premiere is not None and premiere.tzinfo is None:
        premiere = premiere.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    retards = []
    for nom, j in JOBS.items():
        if j.gel or not j.planifie:        # gel volontaire / manuel-seul : silence voulu
            continue
        inter = _intervalle_s(j.cron_utc)
        if inter is None:
            continue
        seuil_h = round(1.5 * inter / 3600, 1)
        # (a) BLOQUÉ — tué en plein run (prioritaire : un en_cours figé masque tout le reste).
        e = lire_etat(nom) or {}
        bl = bloque_depuis(e.get("statut"), e.get("debut"), j.timeout_s)
        if bl is not None:
            retards.append({"nom": nom, "titre": j.titre, "cadence": j.cadence, "motif": "bloque",
                            "dernier_succes": None, "depuis": bl.isoformat(),
                            "age_h": round((now - bl).total_seconds() / 3600, 1), "seuil_h": seuil_h})
            continue
        le = succes.get(nom)
        if le is None:
            # (b) JAMAIS RÉUSSI — en retard dès que le système vit depuis plus d'une cadence entière
            # (réf = plus ancien passage de N'IMPORTE quel job). Base vierge (premiere None) → silence.
            if premiere is None:
                continue
            age = (now - premiere).total_seconds()
            if age > inter:
                retards.append({"nom": nom, "titre": j.titre, "cadence": j.cadence, "motif": "jamais",
                                "dernier_succes": None, "age_h": round(age / 3600, 1),
                                "seuil_h": round(inter / 3600, 1)})
            continue
        # (c) A TOURNÉ PUIS S'EST TU — dernier succès trop vieux.
        le_utc = le if le.tzinfo else le.replace(tzinfo=timezone.utc)
        age = (now - le_utc).total_seconds()
        if age > 1.5 * inter:
            retards.append({"nom": nom, "titre": j.titre, "cadence": j.cadence, "motif": "stale",
                            "dernier_succes": le_utc.isoformat(),
                            "age_h": round(age / 3600, 1), "seuil_h": seuil_h})
    return retards


def verifier_declencheurs(db) -> dict:
    """Évalue les cinq vigies sans point d'appel naturel, ouvre/referme les incidents, et renvoie un
    état lisible (consommé par le récap du matin + `labuse ops verifier`)."""
    s = get_settings()
    out: dict = {}
    ensure_table(db)                 # ops_incidents présente avant toute ouverture/résolution
    try:
        from . import jobs_journal
        jobs_journal.ensure_table(db)    # job_runs présente avant le détecteur de retard
    except Exception:  # noqa: BLE001
        pass

    # 1) disque
    chemin = s.backup_dir if os.access(s.backup_dir, os.R_OK) else "."
    try:
        u = shutil.disk_usage(chemin)
        pct = round(100 * u.used / u.total, 1)
    except OSError:
        pct = None
    out["disque_pct"] = pct
    if pct is not None and pct >= s.disque_seuil_pct:
        signaler(db, "disque", f"Disque à {pct}% (seuil {s.disque_seuil_pct}%)",
                 f"Le disque du serveur est à {pct}% (seuil d'alerte {s.disque_seuil_pct}%). "
                 "Faire de la place (cf. inventaire SOLIDITE-1 Lot 3).")
    elif pct is not None:
        resoudre(db, "disque")

    # 2) /readyz
    ready, motif = _readyz_local()
    out["readyz"] = {"ready": ready, "motif": motif}
    if not ready:
        signaler(db, "readyz", "/readyz répond « pas prêt »",
                 f"La sonde /readyz locale répond que le service n'est pas prêt : {motif}.")
    else:
        resoudre(db, "readyz")

    # 3) sauvegarde : présente + FRAÎCHE (pas seulement présente) + pas rétrécie de plus de 30 %.
    # FIX-NU3-3 (K-SAV + OPS-SAUVEGARDE-1 §7) — l'incident du 30/10 n'a alerté personne parce que la
    # vigie ne testait que l'EXISTENCE d'un .dump (le vieux du 29/10 était là) et son non-rétrécissement,
    # jamais son ÂGE. On juge désormais la fraîcheur : > 30 h = alerte ; panne durable (> 24 h après) = escalade.
    dumps = _dumps(s.backup_dir)
    if not dumps:
        out["sauvegarde"] = {"present": False}
        signaler(db, "sauvegarde-absente", "Aucune sauvegarde présente",
                 f"Aucun dump labuse-*.dump dans {s.backup_dir} — la sauvegarde ne tourne plus.")
        resoudre(db, "sauvegarde-perimee")
        resoudre(db, "escalade:sauvegarde")
    else:
        taille = dumps[0].stat().st_size
        prec = dumps[1].stat().st_size if len(dumps) > 1 else None
        age_h = round((datetime.now(timezone.utc).timestamp() - dumps[0].stat().st_mtime) / 3600, 1)
        seuil_h = getattr(s, "sauvegarde_seuil_h", 30)
        escal_h = seuil_h + getattr(s, "sauvegarde_escalade_h", 24)
        out["sauvegarde"] = {"present": True, "dernier": dumps[0].name, "age_h": age_h,
                             "seuil_h": seuil_h, "taille_mo": round(taille / 1e6, 1),
                             "precedent_mo": round(prec / 1e6, 1) if prec else None}
        resoudre(db, "sauvegarde-absente")
        # fraîcheur : le dernier dump a-t-il moins de `seuil_h` heures ?
        if age_h > seuil_h:
            signaler(db, "sauvegarde-perimee",
                     f"Sauvegarde périmée ({age_h} h, seuil {seuil_h} h)",
                     f"Le dernier dump ({dumps[0].name}) date d'il y a {age_h} h (seuil {seuil_h} h). "
                     "La sauvegarde ne tourne plus — vérifier le job backup-postgres et pg_dump.")
            if age_h > escal_h:
                _escalade(db, "escalade:sauvegarde",
                          "Sauvegarde HS depuis plus de 24 h",
                          f"Plus aucune sauvegarde fraîche depuis {age_h} h "
                          f"(dernier dump : {dumps[0].name}). La panne dure depuis plus de 24 h : "
                          "intervention nécessaire — un incident disque ou une table illisible "
                          "(pg_dump LOCK TABLE) bloque sans doute le dump.")
            else:
                resoudre(db, "escalade:sauvegarde")
        else:
            resoudre(db, "sauvegarde-perimee")
            resoudre(db, "escalade:sauvegarde")
        if prec and taille < 0.70 * prec:
            signaler(db, "sauvegarde-retrecie",
                     f"Sauvegarde rétrécie ({round(taille/1e6,1)} Mo vs {round(prec/1e6,1)} Mo)",
                     f"Le dernier dump ({dumps[0].name}, {round(taille/1e6,1)} Mo) est plus petit de "
                     f"plus de 30 % que le précédent ({round(prec/1e6,1)} Mo) — base tronquée ? coupure ?")
        elif prec:
            resoudre(db, "sauvegarde-retrecie")

    # 4) copie externe (hors-VPS, sur le disque du Mac) — fraîcheur : « branche le disque » au-delà du seuil
    seuil_j = getattr(s, "copie_externe_seuil_j", 10)
    ce = lire_copie_externe(s.backup_dir)
    if not ce:
        out["copie_externe"] = {"present": False, "derniere": None, "seuil_j": seuil_j}
        signaler(db, "copie-externe-ancienne", "Aucune copie externe — branche le disque",
                 "Aucune copie des sauvegardes hors du VPS n'a encore été enregistrée. Un VPS perdu "
                 "emporterait tout : branche le disque externe pour que le Mac en fasse une.")
    else:
        quand = ce["copie_at"]
        age_j = (datetime.now(timezone.utc) - quand).days
        out["copie_externe"] = {"present": True, "derniere": quand.astimezone().strftime("%d/%m"),
                                "copie_at": quand.isoformat(), "dump": ce.get("dump"),
                                "age_j": age_j, "disque": ce.get("disque"), "seuil_j": seuil_j}
        if age_j > seuil_j:
            signaler(db, "copie-externe-ancienne",
                     f"Copie externe ancienne ({age_j} j) — branche le disque",
                     f"La dernière copie des sauvegardes hors du VPS date du "
                     f"{quand.astimezone().strftime('%d/%m à %H:%M')} ({age_j} j, seuil {seuil_j} j). "
                     f"Branche le disque externe : le Mac rapatriera et rangera le dernier dump.")
        else:
            resoudre(db, "copie-externe-ancienne")

    # 4 bis) test de restauration de contrôle MENSUEL (K-SAV-03) — jadis seulement une carte passive :
    # une restauration de contrôle jamais enregistrée (ou vieille de plus de ~35 j) devient un incident
    # ACTIF. Le marqueur est écrit par l'agent Mac (deploy/mac/restore_test.sh) ; absent = jamais joué.
    rt = lire_restore_test(s.backup_dir)
    seuil_rt_j = getattr(s, "restore_test_seuil_j", 35)
    if rt is None:
        out["restore_test"] = {"present": False, "seuil_j": seuil_rt_j}
        signaler(db, "restore-test-ancien", "Aucune restauration de contrôle enregistrée",
                 "Aucun test de restauration mensuel n'a jamais été enregistré (.restore-test.json "
                 f"absent de {s.backup_dir}). Une sauvegarde non testée n'est pas une sauvegarde : "
                 "brancher l'agent Mac restore_test.sh (mensuel).")
    else:
        statut_rt = (rt.get("statut") or "").lower()
        age_rt_j = None
        try:
            ta = datetime.fromisoformat(str(rt.get("test_at")).replace("Z", "+00:00"))
            if ta.tzinfo is None:
                ta = ta.replace(tzinfo=timezone.utc)
            age_rt_j = (datetime.now(timezone.utc) - ta).days
        except (ValueError, TypeError):
            pass
        out["restore_test"] = {"present": True, "statut": statut_rt, "age_j": age_rt_j,
                               "seuil_j": seuil_rt_j}
        if statut_rt == "ko":
            signaler(db, "restore-test-ancien", "La dernière restauration de contrôle a ÉCHOUÉ",
                     rt.get("message") or "Le dernier test de restauration a échoué — la sauvegarde "
                     "ne se restaure pas correctement.")
        elif age_rt_j is not None and age_rt_j > seuil_rt_j:
            signaler(db, "restore-test-ancien",
                     f"Restauration de contrôle ancienne ({age_rt_j} j)",
                     f"Le dernier test de restauration date de {age_rt_j} j (seuil {seuil_rt_j} j) : "
                     "la restauration mensuelle n'est plus jouée (agent Mac à relancer).")
        else:
            resoudre(db, "restore-test-ancien")

    # 5) jobs pas à l'heure — trois motifs (bloque / jamais / stale), chacun sa clé + son escalade.
    # FIX-NU3-3 (I-ADM-01/03, L-JOB-01) : un job BLOQUÉ (tué en plein run) et un job JAMAIS réussi
    # étaient invisibles — ils apparaissent désormais, et « jamais réussi » escalade (mail Vic).
    retards = _jobs_en_retard(db)
    out["retards"] = retards
    par_nom = {r["nom"]: r for r in retards}
    for r in retards:
        nom, titre, cad, motif = r["nom"], r["titre"], r["cadence"], r.get("motif")
        if motif == "bloque":
            signaler(db, f"job-bloque:{nom}", f"Job bloqué : {nom}",
                     f"« {titre} » ({cad}) est « en_cours » depuis {r['age_h']} h sans fin — il a été "
                     "tué en plein travail (OOM, redémarrage) : le verrou reste pris et aucune passe "
                     "ne repart. Relancer le job (« Lancer maintenant ») relâche le verrou.")
        elif motif == "jamais":
            signaler(db, f"job-retard:{nom}", f"Job jamais réussi : {nom}",
                     f"« {titre} » ({cad}) n'a JAMAIS réussi, alors que le serveur tourne depuis "
                     f"{r['age_h']} h (> cadence {r['seuil_h']} h). Le cron est-il posé ? le premier "
                     "passage échoue-t-il en boucle ?")
            _escalade(db, f"escalade:job-jamais:{nom}", f"Automate jamais réussi : {nom}",
                      f"« {titre} » ({cad}) n'a jamais réussi depuis la mise en service du serveur "
                      f"(il y a {r['age_h']} h). À vérifier d'urgence (cron absent ou cassé).")
        else:   # stale
            signaler(db, f"job-retard:{nom}", f"Job en retard : {nom}",
                     f"« {titre} » ({cad}) n'a plus réussi depuis {r['dernier_succes']} "
                     f"(âge {r['age_h']} h > seuil {r['seuil_h']} h). Le cron est-il posé ? le job échoue-t-il ?")
    # referme les incidents des jobs redevenus à l'heure (chaque clé selon le motif courant).
    from .jobs import JOBS
    for nom in JOBS:
        r = par_nom.get(nom)
        motif = r.get("motif") if r else None
        if motif != "bloque":
            resoudre(db, f"job-bloque:{nom}")
        if motif not in ("jamais", "stale"):
            resoudre(db, f"job-retard:{nom}")
        if motif != "jamais":
            resoudre(db, f"escalade:job-jamais:{nom}")

    # 6) RADAR MUET — vigie SERVEUR du silence de l'ingestion Radar (K-RAD-01 + escalade Vic). Si aucune
    # passe (pige_passes) n'est arrivée depuis le seuil, l'extension du Mac ne nourrit plus la prod
    # (Mac endormi, verrou `running` figé). Ne touche PAS l'extension : c'est le serveur qui constate
    # son propre silence et le dit. 2 nuits muettes → escalade mail à Vic. Table absente → pas de vigie.
    out["radar_muet"] = _vigie_radar_muet(db, s)

    # 6 bis) AUTONOMIE-1 — « 3 pointeurs de run au lieu d'un » : si le manifeste et served_run.txt
    # divergent (le front étiquetterait le mauvais run), on OUVRE un incident ; cohérents → résolu.
    try:
        from . import runs
        p = runs.pointeurs()
        out["pointeurs_run"] = p
        if not p["coherents"]:
            signaler(db, "pointeurs-run-divergents",
                     "Pointeurs de run divergents (manifeste ≠ served_run.txt)",
                     f"Le run servi est pointé à deux valeurs différentes : {p['divergence']}. Le backend "
                     "sert le manifeste, mais le bundle front lit served_run.txt → étiquette possiblement "
                     "fausse. Rejouer la bascule (qui réécrit les deux ensemble) ou aligner served_run.txt.")
        else:
            resoudre(db, "pointeurs-run-divergents")
    except Exception as exc:  # noqa: BLE001 — la vigie pointeurs ne doit jamais faire tomber le reste
        log.warning("vigie pointeurs run impossible (%s)", exc)

    # 7) AUTONOMIE-1 — INCIDENTS VIVANTS : tout incident ouvert depuis plus de 3 jours REMONTE dans le
    # mail quotidien (escalade `escalade:ancien:<cle>`, un rappel/jour via la porte unique). Les
    # incidents d'escalade eux-mêmes ne ré-escaladent pas (pas de boucle). Un incident qui se referme
    # (cause disparue) voit son escalade d'ancienneté se refermer avec lui au passage suivant.
    ouverts = incidents_ouverts(db)
    out["incidents_ouverts"] = ouverts
    seuil_anc = getattr(s, "incident_ancien_seuil_j", 3)
    try:
        from . import autonomie
        anciens = autonomie.incidents_anciens(ouverts, seuil_anc, datetime.now(timezone.utc))
    except Exception:  # noqa: BLE001 — jamais faire tomber la vigie pour la remontée d'ancienneté
        anciens = []
    cles_anciennes = set()
    for inc in anciens:
        cle = inc.get("cle", "")
        if cle.startswith("escalade:"):
            continue   # on n'escalade pas une escalade (anti-boucle)
        cles_anciennes.add(cle)
        _escalade(db, f"escalade:ancien:{cle}",
                  f"Incident non résolu depuis {inc.get('age_jours')} j : {inc.get('sujet')}",
                  f"L'incident « {inc.get('sujet')} » (clé {cle}) est ouvert depuis "
                  f"{inc.get('age_jours')} jours (seuil {seuil_anc} j) — il demande une décision. "
                  f"Détail : {inc.get('detail') or ''}")
    # referme les escalades d'ancienneté dont l'incident sous-jacent n'est plus ni ouvert ni ancien
    for inc in ouverts:
        cle = inc.get("cle", "")
        if cle.startswith("escalade:ancien:") and cle[len("escalade:ancien:"):] not in cles_anciennes:
            resoudre(db, cle)
    out["incidents_anciens"] = [{"cle": i["cle"], "age_jours": i.get("age_jours")} for i in anciens]
    return out


def _vigie_radar_muet(db, s) -> dict:
    """FIX-NU3-3 (K-RAD-01, escalade Vic) — l'âge de la dernière passe Radar (pige_passes). Ouvre
    `radar-muet` au-delà du seuil, escalade à 2 nuits. Jamais d'exception (table absente → inactif)."""
    try:
        with db.begin_nested():
            dernier = db.execute(text("SELECT max(created_at) FROM pige_passes")).scalar()
    except Exception:  # noqa: BLE001 — table absente (env sans Radar) : vigie inactive, jamais un crash
        return {"actif": False}
    seuil_h = getattr(s, "radar_muet_seuil_h", 30)
    escal_h = getattr(s, "radar_muet_escalade_h", 48)
    if dernier is None:
        # aucune passe DU TOUT : en env prod c'est anormal, mais en base neuve c'est normal — on ne
        # crie pas (comme pour « jamais lancé » sur une base vierge). Résout tout incident résiduel.
        resoudre(db, "radar-muet")
        resoudre(db, "escalade:radar")
        return {"actif": True, "derniere_passe": None}
    d = dernier if dernier.tzinfo else dernier.replace(tzinfo=timezone.utc)
    age_h = round((datetime.now(timezone.utc) - d).total_seconds() / 3600, 1)
    out = {"actif": True, "derniere_passe": d.isoformat(), "age_h": age_h, "seuil_h": seuil_h}
    if age_h > seuil_h:
        signaler(db, "radar-muet", f"Radar muet depuis {age_h} h",
                 f"Aucune passe Radar depuis {age_h} h (seuil {seuil_h} h) : l'extension du Mac ne "
                 "nourrit plus la prod (Mac endormi la nuit, ou verrou « running » figé après un run "
                 "tué). Réveiller le Mac / relancer une capture manuelle.")
        if age_h > escal_h:
            _escalade(db, "escalade:radar", "Radar muet depuis deux nuits",
                      f"Aucune passe Radar depuis {age_h} h (plus de deux nuits). La collecte s'est "
                      "tue : brancher le Mac sur secteur (scommeil) et relâcher le verrou « running ».")
        else:
            resoudre(db, "escalade:radar")
    else:
        resoudre(db, "radar-muet")
        resoudre(db, "escalade:radar")
    return out
