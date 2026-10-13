"""SOLIDITE-1 (Lot 1.2/1.3) — L'ALERTE D'EXPLOITATION, UNE SEULE PORTE.

La semaine du 07/10 a montré que le danger n'est pas le code mais le SILENCE : une sauvegarde cassée six
jours, dix-neuf tâches mortes, un disque à 96 %, sans qu'aucune alerte ne parte. Ce module est la porte
unique par laquelle toute panne d'exploitation devient visible le jour même :

  · `signaler(cle, sujet, detail)` — ouvre un INCIDENT (mail à Vic + cloche admin), UNE fois. Tant qu'il
    n'est pas résolu : AU PLUS un rappel par jour (pas de déluge). `cle` identifie l'incident (ex.
    'job-echec:backup-postgres', 'disque', 'readyz') : deux appels pour la même panne ne font qu'un.
  · `resoudre(cle)` — si l'incident était ouvert, envoie UN mail « résolu » et le referme. Sinon : rien.
  · `verifier_declencheurs(db)` — évalue d'un coup les quatre vigies qui n'ont pas de point d'appel
    naturel ailleurs (disque, /readyz, sauvegarde, jobs en retard) et ouvre/referme les incidents. Les
    ÉCHECS de job, eux, sont signalés en direct par `jobs.exec_one` (une alerte à l'instant de l'échec).

RÈGLE DRY-RUN (comme tout le reste de LABUSE) : sans SMTP, le mail est écrit en `.eml` (preuve), marqué
'dry-run', rien ne part sur le réseau. L'incident est quand même ouvert/refermé en base (la vigie
fonctionne, seule la notification est différée).
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from .config import get_settings

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
    db.execute(text(DDL))
    db.execute(text(DDL_INDEX))


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
    deja_aujourdhui = db.execute(text(
        "SELECT (dernier_envoi_at AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date "
        "FROM ops_incidents WHERE id = :i"), {"i": row["id"]}).scalar()
    if deja_aujourdhui:
        db.execute(text("UPDATE ops_incidents SET sujet = :s, detail = :d WHERE id = :i"),
                   {"s": sujet, "d": detail, "i": row["id"]})
        return "silence"
    db.execute(text(
        "UPDATE ops_incidents SET sujet = :s, detail = :d, dernier_envoi_at = now(), "
        "rappels = rappels + 1 WHERE id = :i"), {"s": sujet, "d": detail, "i": row["id"]})
    jour = datetime.now(timezone.utc).date().isoformat()
    _sink(db, f"{sujet_mail} (toujours ouvert)",
          detail + "\n\nIncident non résolu depuis l'ouverture — rappel quotidien.\n— LABUSE, exploitation",
          dedup=f"ops:{cle}:{jour}")
    return "rappel"


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
    """Jobs dont le dernier SUCCÈS est plus vieux que 1,5 × leur cadence (ils ont tourné, puis se sont
    tus — exactement le cas des 19 tâches mortes). Un job jamais réussi n'est PAS compté ici (il serait
    « en retard » dès la première installation) : son absence est dite par le récap, pas une alerte."""
    from .jobs import JOBS
    succes = {}
    try:
        from . import jobs_journal
        succes = jobs_journal.dernier_succes(db)
    except Exception as exc:  # noqa: BLE001
        log.warning("retards : historique job_runs illisible (%s)", exc)
    now = datetime.now(timezone.utc)
    retards = []
    for nom, j in JOBS.items():
        le = succes.get(nom)
        if le is None:
            continue
        inter = _intervalle_s(j.cron_utc)
        if inter is None:
            continue
        le_utc = le if le.tzinfo else le.replace(tzinfo=timezone.utc)
        age = (now - le_utc).total_seconds()
        if age > 1.5 * inter:
            retards.append({"nom": nom, "titre": j.titre, "cadence": j.cadence,
                            "dernier_succes": le_utc.isoformat(),
                            "age_h": round(age / 3600, 1), "seuil_h": round(1.5 * inter / 3600, 1)})
    return retards


def verifier_declencheurs(db) -> dict:
    """Évalue les quatre vigies sans point d'appel naturel, ouvre/referme les incidents, et renvoie un
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

    # 3) sauvegarde présente + pas rétrécie de plus de 30 %
    dumps = _dumps(s.backup_dir)
    if not dumps:
        out["sauvegarde"] = {"present": False}
        signaler(db, "sauvegarde-absente", "Aucune sauvegarde présente",
                 f"Aucun dump labuse-*.dump dans {s.backup_dir} — la sauvegarde ne tourne plus.")
    else:
        taille = dumps[0].stat().st_size
        prec = dumps[1].stat().st_size if len(dumps) > 1 else None
        out["sauvegarde"] = {"present": True, "dernier": dumps[0].name,
                             "taille_mo": round(taille / 1e6, 1),
                             "precedent_mo": round(prec / 1e6, 1) if prec else None}
        resoudre(db, "sauvegarde-absente")
        if prec and taille < 0.70 * prec:
            signaler(db, "sauvegarde-retrecie",
                     f"Sauvegarde rétrécie ({round(taille/1e6,1)} Mo vs {round(prec/1e6,1)} Mo)",
                     f"Le dernier dump ({dumps[0].name}, {round(taille/1e6,1)} Mo) est plus petit de "
                     f"plus de 30 % que le précédent ({round(prec/1e6,1)} Mo) — base tronquée ? coupure ?")
        elif prec:
            resoudre(db, "sauvegarde-retrecie")

    # 4) jobs en retard (ont tourné, se sont tus)
    retards = _jobs_en_retard(db)
    out["retards"] = retards
    noms_retard = {r["nom"] for r in retards}
    for r in retards:
        signaler(db, f"job-retard:{r['nom']}", f"Job en retard : {r['nom']}",
                 f"« {r['titre']} » ({r['cadence']}) n'a plus réussi depuis {r['dernier_succes']} "
                 f"(âge {r['age_h']} h > seuil {r['seuil_h']} h). Le cron est-il posé ? le job échoue-t-il ?")
    # referme les retards résolus (un job redevenu à l'heure)
    from .jobs import JOBS
    for nom in JOBS:
        if nom not in noms_retard:
            resoudre(db, f"job-retard:{nom}")

    out["incidents_ouverts"] = incidents_ouverts(db)
    return out
