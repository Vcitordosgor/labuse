"""Transport e-mail UNIQUE de LABUSE (M21-A).

Un seul module, quatre appelants (reset mot de passe, avis d'échéance Chatel, digest
notifications, + `labuse mail-test`). Aucune duplication de transport.

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
                   *, headers: dict[str, str] | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="labuse.immo")
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(body_text)
    return msg


def send_email(to: str, subject: str, body_text: str, *,
               headers: dict[str, str] | None = None, settings=None) -> SendResult:
    """Envoi SYNCHRONE. Retourne un état honnête (l'appelant décide du message UI).

    `headers` : en-têtes additionnels (ex. `List-Unsubscribe` pour le digest).
    """
    s = settings or get_settings()
    from_addr = getattr(s, "mail_from", None) or getattr(s, "smtp_from", "LABUSE <contact@labuse.immo>")

    if not s.smtp_host:
        # A2 — pas de config : on JOURNALISE le mail (debug) et on retourne non-envoyé.
        log.info("MAIL NON ENVOYÉ (SMTP non configuré) — to=%s subject=%r\n%s",
                 to, subject, body_text)
        return SendResult(False, "no-config")

    msg = _build_message(to, subject, body_text, from_addr, headers=headers)
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
        log.warning("MAIL ÉCHEC — to=%s subject=%r cause=%s", to, subject, cause)
        return SendResult(False, f"error: {type(exc).__name__}")


def send_email_async(to: str, subject: str, body_text: str, *,
                     headers: dict[str, str] | None = None) -> None:
    """A3 — envoi en TÂCHE DE FOND : ne bloque jamais la requête HTTP. Résultat seulement logué
    (les appelants qui ont besoin d'un retour honnête utilisent `send_email`)."""
    threading.Thread(
        target=lambda: send_email(to, subject, body_text, headers=headers),
        daemon=True, name="labuse-mail-async",
    ).start()


def mail_configured(settings=None) -> bool:
    """True si un transport SMTP est réellement configuré (sinon mode journal/dev)."""
    return bool((settings or get_settings()).smtp_host)
