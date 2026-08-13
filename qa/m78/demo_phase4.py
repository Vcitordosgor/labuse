"""M78 · STOP Phase 4 — DÉMO VEILLE : pose d'une veille + déclenchement simulé (le cron) → notification.
Usage : .venv/bin/python qa/m78/demo_phase4.py"""
from __future__ import annotations

from fastapi.testclient import TestClient

from labuse.api.app import app


def main() -> int:
    c = TestClient(app)
    print("=" * 78, "\nPOSE d'une veille (le modèle ne sert QU'ICI, à la création)\n" + "=" * 78)
    r = c.post("/api/copilote-v2/ask",
               json={"message": "Préviens-moi de tout nouveau permis à Saint-Paul"}).json()
    print(f"\n▸ « Préviens-moi de tout nouveau permis à Saint-Paul »")
    print(f"  Copilote : {r.get('text')}  (veille #{r.get('veille_id')})")

    print("\n  Type non couvert → DIT, avec les types disponibles :")
    r2 = c.post("/api/copilote-v2/ask",
                json={"message": "Préviens-moi des changements de couleur de façade à Cilaos"}).json()
    print(f"  ▸ Copilote : {r2.get('text')[:120]}")

    print("\n" + "=" * 78, "\nDÉCLENCHEMENT (le cron J+1 de prod appellera ceci ; ZÉRO modèle, du SQL)\n" + "=" * 78)
    ev = c.post("/api/copilote-v2/veilles/evaluer").json()
    print(f"\n  evaluer_toutes → {ev}")
    notifs = c.get("/api/copilote-v2/notifications").json()["notifications"]
    print(f"  {len(notifs)} notification(s) STOCKÉE(s) :")
    for n in notifs[:3]:
        print(f"    • {n['titre']} — {n['detail']}")

    print("\n" + "=" * 78, "\nLA MOITIÉ MANQUANTE (pour que l'alerte ATTEIGNE le client)\n" + "=" * 78)
    print("  LIVRÉ  : pose (table veilles) · évaluation SQL sans modèle (evaluer_toutes) ·")
    print("           stockage des notifications (veille_notifications) · écran liste/suppression.")
    print("  MANQUE : (1) le CRON J+1 (Train 8) qui APPELLE evaluer_toutes à chaque ingestion —")
    print("               la fonction et l'endpoint existent, le déclencheur de prod n'est pas câblé ;")
    print("           (2) la CLOCHE in-app (centre de notifications) — BACKLOG : les notifs sont")
    print("               stockées et comptées par veille, mais rien ne les POUSSE globalement ;")
    print("           (3) le DIGEST e-mail (SMTP non branché, BACKLOG) pour l'atteinte hors-app.")
    print("  → Une veille se POSE et s'ÉVALUE ; elle n'ALERTE pas encore proactivement. C'est là,")
    print("    exactement, la moitié manquante : le déclencheur de prod + le canal (cloche/e-mail).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
