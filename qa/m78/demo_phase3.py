"""M78 · STOP Phase 3 — DÉMO. Création de projet (vérifiée dans Projets, champ à champ) + une
vérification complète. Modèle réel. Usage : .venv/bin/python qa/m78/demo_phase3.py"""
from __future__ import annotations

from fastapi.testclient import TestClient

from labuse.api.app import app


def main() -> int:
    c = TestClient(app)
    print("=" * 78, "\n3b — PROJET : création RÉELLE par le Copilote (API projets), puis relu champ à champ\n" + "=" * 78)
    r = c.post("/api/copilote-v2/ask", json={
        "message": "J'ai un nouveau projet : résidence de 12 logements à Bras-Panon, budget 600 k€"}).json()
    print(f"\n▸ « J'ai un nouveau projet : résidence de 12 logements à Bras-Panon, budget 600 k€ »")
    print(f"  Copilote : {r.get('text')}  (pid {r.get('projet_id')})")
    p = c.get(f"/projets/{r['projet_id']}").json()
    p = p.get("projet", p)
    fiche = p.get("fiche", {})
    print(f"  RELU par l'API projets — nom: {p.get('nom')}")
    print(f"    fiche.ampleur.logements = {fiche.get('ampleur', {}).get('logements')}  (attendu 12)")
    print(f"    fiche.perimetre.communes = {fiche.get('perimetre', {}).get('communes')}  (attendu ['Bras-Panon'])")
    print(f"    fiche.budget_foncier_eur = {fiche.get('budget_foncier_eur')}  (attendu 600000)")

    print("\n" + "=" * 78, "\n3a — VÉRIFICATION complète (fiche + marché terrain M79 + avis à verrou)\n" + "=" * 78)
    v = c.post("/api/copilote-v2/ask", json={
        "message": "Cette parcelle 97415000AC0253 vaut-elle ses 320 000 € demandés ?"}).json()
    print(f"\n▸ « Cette parcelle 97415000AC0253 vaut-elle ses 320 000 € demandés ? »")
    print(f"  Copilote : {v.get('text')}")
    print(f"  [intent={v.get('intent')} · sorties={v.get('actions')}]")

    print("\n  Une seule question si le prix manque :")
    v2 = c.post("/api/copilote-v2/ask", json={"message": "Vérifie la parcelle 97415000AC0253"}).json()
    print(f"  ▸ « Vérifie la parcelle 97415000AC0253 » → « {v2.get('text')} »")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
