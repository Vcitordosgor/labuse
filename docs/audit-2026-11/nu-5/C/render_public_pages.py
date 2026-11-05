#!/usr/bin/env python3
"""NU5-C — rend les pages PUBLIQUES server-rendered (0 DB, 0 serveur) en .html pour capture.

Ces pages sont les PREMIERS écrans d'un nouveau client (avant tout login) : elles sont construites
par des fonctions PURES (pas de requête base) que l'on appelle directement. Zéro effet de bord.
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "captures" / "pages"
OUT.mkdir(parents=True, exist_ok=True)


def _html(obj) -> str:
    if isinstance(obj, str):
        return obj
    body = getattr(obj, "body", None)
    if body is not None:
        return body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)
    return str(obj)


def main() -> None:
    from labuse.api import auth, onboarding
    pages = {
        "01_login": auth.login_page(error=False),
        "02_login_erreur": auth.login_page(error=True),
        "03_invitation_sans_token": onboarding.invitation_page(token="", db=None),
        "04_cgv": onboarding.cgv_page(),
        "05_reset_demande": onboarding.reset_page(token=""),
        "06_onboarding_bienvenue": onboarding.onboarding_retour(ok=1),
        "07_onboarding_interrompu": onboarding.onboarding_retour(ok=0),
    }
    for nom, obj in pages.items():
        html = _html(obj)
        (OUT / f"{nom}.html").write_text(html, encoding="utf-8")
        print(f"{nom}: {len(html)} octets")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
