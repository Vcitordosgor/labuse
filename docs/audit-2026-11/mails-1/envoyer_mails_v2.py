#!/usr/bin/env python3
"""MAILS-1 — ENVOI des 21 mails V2 (gabarit unique, rendus par l'app) vers l'adresse de test.

Chaque mail est rendu par `labuse.mails_contenu` (le gabarit unique) — exactement ce que l'app
enverra en prod, Brevo n'étant qu'un transport. On pousse `htmlContent` + `textContent` à Brevo
`/smtp/email` (plus aucun `templateId`), sujet préfixé « [V2 nn/21] », un envoi toutes les 10 s,
dans l'ordre du catalogue NU5-C.

GARDE-FOU : destinataire VERROUILLÉ sur l'adresse de test, vérifié AVANT chaque appel réseau.
Aucune écriture en base, aucun vrai client touché. Nécessite LABUSE_MAIL_REEL=1 + BREVO_API_KEY.
"""
from __future__ import annotations

import email.utils as eu
import json
import sys
import time
from pathlib import Path

import httpx

from labuse import brevo, mails_contenu as mc
from labuse.config import envoi_reel_autorise, get_settings

TEST = "victorlaganepro+mails@gmail.com"   # UNIQUE destinataire autorisé
API = "https://api.brevo.com/v3/smtp/email"
PAUSE = 10                                 # secondes entre deux envois
ICI = Path(__file__).resolve().parent
# mails récurrents : en-tête de désinscription 1 clic (RFC 8058), comme en prod.
RECURRENTS = {"radar_digest", "radar_alerte", "smtp_digest_notifications", "smtp_annonce",
              "smtp_mise_en_vente"}


def _sender() -> dict:
    nom, adr = eu.parseaddr(getattr(get_settings(), "mail_from", "LABUSE <contact@labuse.immo>"))
    s = {"email": adr or "contact@labuse.immo"}
    if nom:
        s["name"] = nom
    return s


def _poster(subject: str, html: str, texte: str, headers: dict | None) -> dict:
    if TEST != "victorlaganepro+mails@gmail.com":
        raise SystemExit("GARDE : adresse de test altérée — ABANDON.")
    payload = {"sender": _sender(), "to": [{"email": TEST}], "subject": subject,
               "htmlContent": html, "textContent": texte, "disableTracking": True}
    if headers:
        payload["headers"] = headers
    api_key = brevo._api_key()
    if not api_key:
        return {"envoye": False, "raison": "BREVO_API_KEY absente"}
    r = httpx.post(API, headers={"api-key": api_key, "content-type": "application/json"},
                   json=payload, timeout=20.0)
    if r.status_code // 100 == 2:
        try:
            mid = r.json().get("messageId")
        except Exception:
            mid = None
        return {"envoye": True, "message_id": mid}
    return {"envoye": False, "raison": f"HTTP {r.status_code}: {r.text[:200]}"}


def main() -> int:
    if not envoi_reel_autorise():
        print("REFUS : envoi réel non autorisé (poser LABUSE_MAIL_REEL=1).", file=sys.stderr)
        return 2
    keys = mc.ORDRE_CATALOGUE
    n = len(keys)
    print(f"{n} mails V2 à envoyer → {TEST} (un toutes les {PAUSE}s)")
    resultats = []
    for i, key in enumerate(keys, 1):
        m = mc.rendre(key, mc.SPECIMENS[key])
        prefixe = f"[V2 {i:02d}/{n}] "
        sujet = prefixe + m.sujet
        headers = dict(m.headers or {})
        if key in RECURRENTS:
            desabo = mc.SPECIMENS[key].get("LIEN_DESABO")
            if desabo:
                headers.setdefault("List-Unsubscribe", f"<{desabo}>")
                headers.setdefault("List-Unsubscribe-Post", "List-Unsubscribe=One-Click")
        res = _poster(sujet, m.html, m.texte, headers or None)
        ligne = {"n": i, "cle": key, "sujet": sujet, "parti": bool(res.get("envoye")),
                 "message_id": res.get("message_id"), "raison": res.get("raison")}
        resultats.append(ligne)
        etat = "OK" if ligne["parti"] else f"ÉCHEC ({ligne['raison']})"
        print(f"  {prefixe}{key:<26} {etat}  mid={ligne['message_id']}")
        (ICI / "envois_v2.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
        if i < n:
            time.sleep(PAUSE)
    partis = sum(1 for r in resultats if r["parti"])
    print(f"\nTerminé : {partis}/{n} partis.")
    return 0 if partis == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
