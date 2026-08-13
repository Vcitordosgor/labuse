"""M78 · STOP Phase 2 — DÉMO. 3 recherches réelles · 1 critère non traduisible · 1 modif de chip en
cours · 1 arrêt propre. Les deux derniers sont INTERACTIFS (run M26-A) : couverts par vitest 38 et
l'audit backend (pas de zombie) — référencés ici, pas rejouables dans un script. Le reste est réel.

Usage : .venv/bin/python qa/m78/demo_phase2.py
"""
from __future__ import annotations

from labuse.copilote.interpreteur import interpreter_brief
from labuse.copilote_v2 import heros as H
from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

RECHERCHES = [
    "Terrain de 1 200 m² constructible à Saint-André pour 10 logements",
    "15 logements à Saint-Paul, budget foncier 800 k€, hors zone inondable",
    "Des parcelles de personnes morales d'au moins 2000 m² à Saint-Pierre",
]
NON_TRADUISIBLE = "10 logements à Saint-Leu, proche de la mer, déjà en vente"


def _chips(bj: dict) -> str:
    """Mirroir Python des chips COMPRIS (front ChipsCompris) — pour montrer le client-facing."""
    c = []
    for x in bj.get("communes", []):
        c.append(x)
    p = bj.get("programme") or {}
    if p.get("logements") is not None:
        c.append(f"{p['logements']} logements → SDP ≥ {round(p.get('sdp_cible_m2') or 0)} m²")
    if bj.get("budget_max_eur"):
        c.append(f"budget ≤ {round(bj['budget_max_eur'] / 1000)} k€")
    ct = bj.get("contraintes") or {}
    if ct.get("zones"):
        c.append("zones " + " · ".join(ct["zones"]))
    if ct.get("exclure_ppr_rouge"):
        c.append("hors PPR rouge")
    return "  ·  ".join(c)


def main() -> int:
    with session_scope() as db:
        print("=" * 78, "\n3 RECHERCHES RÉELLES — routage + interprétation + chips COMPRIS\n" + "=" * 78)
        for q in RECHERCHES:
            r = answer(db, q)
            it = interpreter_brief(q, "instruire")
            print(f"\n▸ {q}")
            print(f"  routeur → {r.get('intent')}  (mission lourde lancée : run M26-A)")
            if it.brief:
                print(f"  COMPRIS : {_chips(it.brief)}")

        print("\n" + "=" * 78, "\n1 CRITÈRE NON TRADUISIBLE — DIT, jamais promis\n" + "=" * 78)
        it = interpreter_brief(NON_TRADUISIBLE, "instruire")
        print(f"\n▸ {NON_TRADUISIBLE}")
        if it.brief:
            print(f"  COMPRIS : {_chips(it.brief)}")
            for c in it.brief.get("criteres_non_appliques", []):
                print(f"  ⚠ « {c} » non applicable (chip amber — dit au client, télémétrie §1e)")

        print("\n" + "=" * 78, "\nLE HÉROS — phrase à verrou anti-invention (§2e)\n" + "=" * 78)
        P = {"idu": "97415000AC0253", "commune": "Saint-Paul", "surface_m2": 1815, "sdp_m2": 920,
             "prix_probable_eur": 350000, "charge_fonciere_eur": 280000, "tier": "chaude",
             "au_dessus_charge_supportable": True, "zone": "U", "n_signaux_risques": 1}
        h = H.phrase(db, P, 300000)
        print(f"\n  « {h['phrase']} »")
        print(f"  [gabarit={h['gabarit']} — tout nombre vérifié ∈ JSON parcelle]")

        print("\n" + "=" * 78, "\nMODIF DE CHIP EN COURS + ARRÊT PROPRE (interactifs)\n" + "=" * 78)
        print("  ✓ modifier une chip pendant l'instruction = annuler propre + relancer")
        print("    → testé : etats2a5 « retirer une chip EN COURS → POST /cancel puis nouveau run » (vitest 38)")
        print("  ✓ arrêt propre, aucun job zombie")
        print("    → testé : etats2a5 « annulation active → POST /cancel » + l'exécuteur backend vérifie")
        print("      le statut à CHAQUE étape (executeur.py) → le run s'arrête vraiment côté serveur")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
