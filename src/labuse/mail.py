"""Point d'entrée e-mail UNIQUE de LABUSE (M21-A ; CONNEXIONS-2 Lot 9.1, KO-12).

`mail` est la SEULE FAÇADE d'envoi de LABUSE — invitation, veille, courrier, Radar y passent tous.
Elle a DEUX voies de livraison, jamais appelées en direct ailleurs (garde : test_transport_unique) :
  · SMTP (ce module) pour le mail TECHNIQUE brut (reset, échéance, digest de notifications) ;
  · Brevo (`brevo.py`, transactionnel par template) via `mail.envoyer_template` — pour le CYCLE DE VIE
    client (essai/onboarding/suspension) et les digests Radar. `brevo` n'est importé QUE par `mail`.
Un seul EXPÉDITEUR (`contact@labuse.immo`, alias vérifié). L'ancienne doctrine « transport unique »
disait vrai à moitié (Brevo coexistait, appelé en direct) : désormais c'est bien UNE façade, UN sender.

Règles dures :
- **Aucun secret en dur, jamais logué.** La config vient de l'environnement (LABUSE_SMTP_*,
  LABUSE_MAIL_FROM). Le mot de passe d'application n'apparaît ni dans le code, ni dans un log,
  ni dans un message d'erreur.
- **Sans hôte SMTP configuré** (dev sans secrets) : le mail est JOURNALISÉ et l'état retourné est
  `sent=False, detail='no-config'`. Aucune interface ne doit prétendre qu'un mail est parti.
- **STARTTLS sur 587**, expéditeur affiché = LABUSE_MAIL_FROM (alias vérifié `contact@labuse.immo`),
  jamais l'adresse Gmail brute.
- Un échec est **logué avec sa cause** (classe d'exception, jamais le mot de passe) et remonté à
  l'appelant. Envoi synchrone (résultat honnête) OU en tâche de fond (ne bloque pas la requête).
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .config import get_settings

log = logging.getLogger("labuse.mail")

# Plafond Gmail gratuit (C2) — indicatif : au-delà, refus explicite plutôt qu'échec silencieux.
GMAIL_DAILY_CAP = 500


@dataclass(frozen=True)
class SendResult:
    """Résultat d'une tentative d'envoi. Ne contient JAMAIS de secret."""
    sent: bool
    detail: str  # 'ok' | 'no-config' | 'error: <ClasseException>'

    @property
    def ok(self) -> bool:
        return self.sent


def _build_message(to: str, subject: str, body_text: str, from_addr: str,
                   *, headers: dict[str, str] | None = None, body_html: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="labuse.immo")
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(body_text)
    if body_html:                                    # M85 — alternative HTML (DA LABUSE) ; le texte
        msg.add_alternative(body_html, subtype="html")   # reste le repli (clients sans HTML, délivrabilité)
    return msg


def send_email(to: str, subject: str, body_text: str, *,
               headers: dict[str, str] | None = None, body_html: str | None = None,
               settings=None) -> SendResult:
    """Envoi SYNCHRONE. Retourne un état honnête (l'appelant décide du message UI).

    `headers` : en-têtes additionnels (ex. `List-Unsubscribe` pour le digest).
    `body_html` : alternative HTML (multipart/alternative) — le texte reste le repli.
    """
    s = settings or get_settings()
    from_addr = getattr(s, "mail_from", None) or getattr(s, "smtp_from", "LABUSE <contact@labuse.immo>")

    if not s.smtp_host:
        # A2 — pas de config : on JOURNALISE le mail (debug) et on retourne non-envoyé.
        log.info("MAIL NON ENVOYÉ (SMTP non configuré) — to=%s subject=%r\n%s",
                 to, subject, body_text)
        return SendResult(False, "no-config")

    msg = _build_message(to, subject, body_text, from_addr, headers=headers, body_html=body_html)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            server.ehlo()
            if s.smtp_starttls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if s.smtp_user and s.smtp_password:
                # login() n'inclut jamais le mot de passe dans ses exceptions (réponse serveur only).
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        log.info("MAIL envoyé — to=%s subject=%r", to, subject)
        return SendResult(True, "ok")
    except Exception as exc:  # noqa: BLE001 — on veut TOUTE cause, mais jamais silencieuse
        # str(exc) = réponse SMTP / message socket — ne contient pas le mot de passe.
        cause = f"{type(exc).__name__}: {str(exc)[:200]}"
        low = str(exc).lower()
        # C2 — plafond Gmail (~500/j) : refus EXPLICITE (jamais silencieux). Gmail répond
        # « 550 5.4.5 Daily user sending limit exceeded » / « 4.7.0 ... rate » selon le cas.
        if any(k in low for k in ("5.4.5", "sending limit", "rate limit", "quota", "too many")):
            log.error("MAIL REFUSÉ — plafond d'envoi atteint (Gmail gratuit ≈ %d/jour) : "
                      "passer à un relais SMTP transactionnel. to=%s cause=%s", GMAIL_DAILY_CAP, to, cause)
            return SendResult(False, "error: quota")
        log.warning("MAIL ÉCHEC — to=%s subject=%r cause=%s", to, subject, cause)
        return SendResult(False, f"error: {type(exc).__name__}")


def send_email_async(to: str, subject: str, body_text: str, *,
                     headers: dict[str, str] | None = None, contexte: str = "") -> None:
    """A3 — envoi en TÂCHE DE FOND : ne bloque jamais la requête HTTP. N1 (FIX-VEILLE) — un échec RÉEL
    (pas le mode journal dev « no-config ») n'est plus AVALÉ : il est tracé en event_log `systeme`
    (visible ADMIN à la cloche). Aucun renvoi automatique (décision Vic). Les appelants qui veulent un
    retour synchrone utilisent `send_email`. `contexte` : libellé court pour l'admin (ex. « Courrier »)."""
    def _run() -> None:
        res = send_email(to, subject, body_text, headers=headers)
        if not res.ok and res.detail != "no-config":   # échec RÉEL (le mode journal dev n'est pas un échec)
            _journaliser_echec_admin(to, subject, res.detail, contexte)
    threading.Thread(target=_run, daemon=True, name="labuse-mail-async").start()


def _journaliser_echec_admin(to: str, subject: str, detail: str, contexte: str) -> None:
    """N1 — trace un échec d'envoi ASYNC dans event_log `systeme` (feed admin, jamais un client).
    Best-effort : une trace qui échoue ne masque JAMAIS l'échec initial (déjà logué en clair)."""
    log.warning("MAIL ASYNC ÉCHEC — to=%s subject=%r cause=%s%s", to, subject, detail,
                f" contexte={contexte}" if contexte else "")
    try:
        from .api.events import creer_notification
        from .db import session_scope
        ctx = f" ({contexte})" if contexte else ""
        with session_scope() as db:
            creer_notification(
                db, kind="systeme", compte_id=None, source="E-mail",
                titre=f"Un e-mail n'est pas parti{ctx}",
                detail=f"Destinataire {to} — « {subject} ». Cause : {detail}. Aucun renvoi automatique.",
                dedup=f"mail-echec:{to}")   # une trace/jour/destinataire (pas de tempête)
    except Exception:  # noqa: BLE001 — la trace est best-effort ; le log ci-dessus reste la garantie
        log.exception("MAIL ASYNC — journalisation event_log impossible (l'échec initial reste logué)")


def mail_configured(settings=None) -> bool:
    """True si un transport SMTP est réellement configuré (sinon mode journal/dev)."""
    return bool((settings or get_settings()).smtp_host)


def envoyer_template(to: str, key: str, params: dict | None = None) -> dict:
    """CONNEXIONS-2 Lot 9.1 (KO-12) — FAÇADE unique pour les mails TEMPLATISÉS (cycle de vie client,
    digests Radar) : délègue au relais transactionnel Brevo. C'est le SEUL point d'entrée des templates —
    `brevo` n'est jamais appelé en direct ailleurs (garde test_transport_unique). Renvoie {envoye, raison?}."""
    from . import brevo
    return brevo.envoyer_template(to, key, params)
