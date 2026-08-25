"""PHASE D — la batterie COPILOTE-REFONTE : 20 questions enchaînées dans UNE session réaliste,
appels RÉELS. Réplique le fil de l'endpoint (history + prior_params + prior_voie + faits_fil) sans
écrire en base (lecture seule hors code). Lancer : LABUSE_DEV_MODE=1 .venv/bin/python qa/ia/batterie_copilote.py
"""
from __future__ import annotations

from labuse.db import session_scope
from labuse.copilote_v2.answering import answer

QUESTIONS = [
    "combien de parcelles brûlantes à Saint-Paul ?",
    "et à Saint-Pierre ?",
    "montre-les sur la carte",
    "c'est quoi le délai d'instruction à Saint-Denis ?",
    "et les prix de l'ancien là-bas ?",
    "quel est le patrimoine foncier de la SHLMR ?",
    "combien de permis accordés au Port sur 24 mois ?",
    "qu'est-ce que la loi girardin ?",
    "elle est toujours en place à la Réunion ?",
    "c'est quoi une SUP pm1 ?",
    "un terrain pour 3 immeubles R+3 de 8 logements",
    "donne-moi le prix au m²",
    "ma parcelle BZ1065 à Saint-Denis, elle vaut quoi ?",
    "combien de piscines à Saint-Paul ?",
    "quelle commune a le plus de foncier disponible ?",
    "c'est quoi la différence entre SDP et SHAB ?",
    "fais-moi une recette de rougail saucisse",
    "t'es sûr ?",
    "résume-moi ce qu'on s'est dit",
    "combien de réserves foncières sur toute l'île ?",
]


def _voie(rep: dict) -> str:
    if rep.get("tenue"):
        return "tenue"
    if rep.get("general"):
        return "voie b (générale)"
    if rep.get("refus") == "hors_sujet":
        return "hors-domaine"
    if rep.get("clarification"):
        return "clarification"
    if rep.get("refus"):
        return f"refus:{rep.get('refus')}"
    if rep.get("web"):
        return "web"
    if rep.get("voie"):
        return f"voie-navig:{(rep.get('voie') or {}).get('cible')}"
    if rep.get("sources") or rep.get("tool"):
        return "voie a (sourcée)"
    return "?"


def main() -> None:
    history: list[dict] = []
    prior_params = None
    prior_voie = None
    faits_fil: list[dict] = []
    with session_scope() as db:
        for i, q in enumerate(QUESTIONS, 1):
            try:
                rep = answer(db, q, history=history, prior_params=prior_params,
                             prior_voie=prior_voie, faits_fil=faits_fil)
            except Exception as e:  # noqa: BLE001
                print(f"\n### Q{i}: {q}\n  EXCEPTION: {type(e).__name__}: {e}")
                continue
            route = rep.get("_route") or {}
            txt = " ".join((rep.get("text") or "").split())
            print(f"\n### Q{i}: {q}")
            print(f"  voie={_voie(rep)} | tool={rep.get('tool')} | sources={rep.get('sources')} "
                  f"| carte={'oui' if rep.get('carte_filtre') else '-'} | compris={bool(rep.get('compris'))}")
            print(f"  → {txt[:300]}")
            # --- threade le contexte pour le tour suivant, comme l'endpoint ---
            history = (history + [{"role": "user", "content": q},
                                  {"role": "assistant", "content": (rep.get("text") or "")[:400]}])[-12:]
            prior_params = route.get("params") or None
            prior_voie = route.get("voie")
            ft = rep.get("_faits_tour")
            if ft:
                faits_fil = (list(ft) + faits_fil)[:40]


if __name__ == "__main__":
    main()
