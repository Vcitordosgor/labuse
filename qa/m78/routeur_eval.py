"""M78 · 1a — TEST DU ROUTEUR (bloquant, avant toute UI).

45 messages étiquetés : les 7 intentions (clair) + 5 ambigus + 5 corrections de tour 2 + hors-sujet
+ OUTIL dont 2 sans outil correspondant. Cible : précision >= 95 % sur les intentions CLAIRES.
Sortie : matrice de confusion + précision + détail des ratés + coût mesuré (ia_log).

Usage : .venv/bin/python qa/m78/routeur_eval.py
Nécessite ANTHROPIC_API_KEY (via .env) — c'est un gate à modèle réel, pas un test unitaire mické.
"""
from __future__ import annotations

import json
import sys

from labuse.copilote_v2.router import INTENTS, classify
from labuse.db import session_scope

IDU = "97415000AC0253"   # parcelle U réelle (canari des mandats précédents)

# category : "clair" (compte pour la précision) · "ambigu" (attend clarification) · "correction"
# (tour 2 : bon intent + IDU conservé). expect = intent attendu. no_tool : OUTIL sans outil (aval).
CASES: list[dict] = [
    # ── QUESTION (clair) ──
    {"m": "Combien de parcelles constructibles de plus de 1000 m² à Saint-Paul ?", "e": "QUESTION", "c": "clair"},
    {"m": "Quel est le prix médian du terrain nu à Saint-Pierre ?", "e": "QUESTION", "c": "clair"},
    {"m": "Combien de temps un dossier met à être instruit par la mairie de Saint-Benoît ?", "e": "QUESTION", "c": "clair"},
    {"m": "Quelles parcelles la SCI Dupont possède-t-elle ?", "e": "QUESTION", "c": "clair"},
    {"m": "Quelle est la population de Cilaos ?", "e": "QUESTION", "c": "clair"},
    {"m": "Quel est le taux de logement social à Saint-Louis ?", "e": "QUESTION", "c": "clair"},
    {"m": f"Y a-t-il des risques sur la parcelle {IDU} ?", "e": "QUESTION", "c": "clair"},
    {"m": "Combien de ventes DVF à Saint-André l'an dernier ?", "e": "QUESTION", "c": "clair"},
    # ── RECHERCHE (clair) ──
    {"m": "Trouve-moi des terrains à fort potentiel à Saint-Leu pour 15 logements.", "e": "RECHERCHE", "c": "clair"},
    {"m": "Je cherche de grandes parcelles détenues par des personnes morales à Saint-André.", "e": "RECHERCHE", "c": "clair"},
    {"m": "Montre-moi les meilleures opportunités foncières au Tampon sous 500 000 €.", "e": "RECHERCHE", "c": "clair"},
    {"m": "Liste les friches en zone U à Saint-Denis.", "e": "RECHERCHE", "c": "clair"},
    {"m": "Des parcelles de bailleurs sociaux à Sainte-Marie, s'il te plaît.", "e": "RECHERCHE", "c": "clair"},
    {"m": "Sors-moi une shortlist de terrains divisibles à Saint-Louis.", "e": "RECHERCHE", "c": "clair"},
    # ── VERIFICATION (clair) ──
    {"m": f"Cette parcelle {IDU} vaut-elle bien ses 320 000 € demandés ?", "e": "VERIFICATION", "c": "clair"},
    {"m": f"Le vendeur demande 280 000 € pour {IDU}, est-ce raisonnable ?", "e": "VERIFICATION", "c": "clair"},
    {"m": f"Vérifie si {IDU} est à son juste prix.", "e": "VERIFICATION", "c": "clair"},
    {"m": "Est-ce que 97401000AB0001 est surévaluée à 400 000 € ?", "e": "VERIFICATION", "c": "clair"},
    # ── OUTIL (clair) — dont 2 SANS outil (division, décision M-ENTREE) ──
    {"m": "Je veux assembler plusieurs parcelles contiguës.", "e": "OUTIL", "c": "clair"},
    {"m": f"Écris un courrier au propriétaire de {IDU}.", "e": "OUTIL", "c": "clair"},
    {"m": f"Calcule la charge foncière que je peux supporter sur {IDU}.", "e": "OUTIL", "c": "clair"},
    {"m": "Compare ces trois parcelles côte à côte.", "e": "OUTIL", "c": "clair"},
    {"m": f"Est-ce que je peux diviser ce terrain {IDU} ?", "e": "OUTIL", "c": "clair", "no_tool": True},
    {"m": f"Je veux découper cette grande parcelle {IDU} en lots à bâtir.", "e": "OUTIL", "c": "clair", "no_tool": True},
    # ── VEILLE (clair) ──
    {"m": "Préviens-moi de tout nouveau permis à Saint-Paul.", "e": "VEILLE", "c": "clair"},
    {"m": "Alerte-moi quand une parcelle se vend à Saint-Joseph.", "e": "VEILLE", "c": "clair"},
    {"m": "Surveille les procédures PLU à L'Étang-Salé.", "e": "VEILLE", "c": "clair"},
    {"m": "Tiens-moi au courant du BODACC sur la société SCI Martin.", "e": "VEILLE", "c": "clair"},
    # ── PROJET (clair) ──
    {"m": "J'ai un nouveau projet : résidence de 12 lots à Bras-Panon.", "e": "PROJET", "c": "clair"},
    {"m": "Crée un projet de 30 logements sociaux à Saint-André.", "e": "PROJET", "c": "clair"},
    {"m": "Nouveau projet : 2000 m² de bureaux à Saint-Denis.", "e": "PROJET", "c": "clair"},
    # ── HORS_SUJET (clair) ──
    {"m": "Quelle est la météo demain à Saint-Gilles ?", "e": "HORS_SUJET", "c": "clair"},
    {"m": "Peux-tu m'écrire un poème sur l'océan ?", "e": "HORS_SUJET", "c": "clair"},
    {"m": "Quel est le meilleur restaurant créole de Saint-Pierre ?", "e": "HORS_SUJET", "c": "clair"},
    {"m": "Comment tu vas aujourd'hui ?", "e": "HORS_SUJET", "c": "clair"},
    # ── AMBIGU (attend une clarification) ──
    {"m": "Saint-Paul.", "e": None, "c": "ambigu"},
    {"m": "Cette parcelle.", "e": None, "c": "ambigu"},
    {"m": "Je veux investir.", "e": None, "c": "ambigu"},
    {"m": "Combien ça coûte ?", "e": None, "c": "ambigu"},
    {"m": "Le terrain là-bas, tu peux regarder ?", "e": None, "c": "ambigu"},
    # ── CORRECTIONS DE TOUR 2 (history + prior_params ; bon intent + IDU/critère conservé) ──
    {"m": "Non, je voulais dire à 250 000 €.", "e": "VERIFICATION", "c": "correction",
     "history": [{"role": "user", "content": f"Vérifie le prix de {IDU} à 300 000 €."},
                 {"role": "assistant", "content": "Instruction en cours…"}],
     "prior": {"idu": IDU, "prix_eur": 300000}, "keep": "idu"},
    {"m": "Et à Saint-Benoît ?", "e": "QUESTION", "c": "correction",
     "history": [{"role": "user", "content": "Combien de parcelles de plus de 1000 m² à Saint-Paul ?"},
                 {"role": "assistant", "content": "Instruction en cours…"}],
     "prior": {"commune": "Saint-Paul", "surface_min": 1000}, "keep": "surface_min"},
    {"m": "En fait, plutôt à Saint-Pierre.", "e": "RECHERCHE", "c": "correction",
     "history": [{"role": "user", "content": "Trouve des terrains à Saint-Leu pour 15 logements."},
                 {"role": "assistant", "content": "Instruction en cours…"}],
     "prior": {"commune": "Saint-Leu", "programme_logements": 15}, "keep": "programme_logements"},
    {"m": f"Non, je voulais dire vérifier le prix de {IDU}.", "e": "VERIFICATION", "c": "correction",
     "history": [{"role": "user", "content": "Assemble des parcelles."},
                 {"role": "assistant", "content": "Instruction en cours…"}],
     "prior": {}, "keep": None},
    {"m": f"Ajoute la parcelle {IDU} à ce projet.", "e": "PROJET", "c": "correction",
     "history": [{"role": "user", "content": "Crée un projet 12 lots à Bras-Panon."},
                 {"role": "assistant", "content": "Projet créé."}],
     "prior": {"commune": "Bras-Panon", "programme_logements": 12}, "keep": "commune"},
]


def main() -> int:
    with session_scope() as db:
        results = []
        confusion: dict[str, dict[str, int]] = {}
        for case in CASES:
            r = classify(db, case["m"], history=case.get("history"), prior_params=case.get("prior"))
            if r.degraded or r.error:
                print(f"ÉCHEC INFRA sur « {case['m'][:40]} » : degraded={r.degraded} err={r.error}", file=sys.stderr)
                if r.degraded:
                    print("ANTHROPIC_API_KEY absente ou API indisponible — gate non exécutable.", file=sys.stderr)
                    return 2
            got = r.intent
            ok = None
            note = ""
            if case["c"] == "clair":
                ok = (got == case["e"])
                confusion.setdefault(case["e"], {}).setdefault(got, 0)
                confusion[case["e"]][got] += 1
            elif case["c"] == "ambigu":
                # correct si une clarification est posée (l'intent indicatif importe peu)
                ok = bool(r.clarification)
                note = "clarification posée" if ok else f"PAS de clarification (intent={got})"
            elif case["c"] == "correction":
                keep = case.get("keep")
                idu_ok = (keep is None) or (str(r.params.get(keep)) == str(case["prior"].get(keep)))
                ok = (got == case["e"]) and idu_ok
                note = f"keep {keep}={r.params.get(keep)}" if keep else "reclass"
            results.append({"m": case["m"][:52], "cat": case["c"], "attendu": case["e"],
                            "obtenu": got, "ok": ok, "clarif": bool(r.clarification),
                            "params": r.params, "no_tool": case.get("no_tool", False), "note": note})

        clair = [x for x in results if x["cat"] == "clair"]
        n_clair_ok = sum(1 for x in clair if x["ok"])
        prec_clair = round(100 * n_clair_ok / len(clair), 1) if clair else 0.0
        amb = [x for x in results if x["cat"] == "ambigu"]
        cor = [x for x in results if x["cat"] == "correction"]

        # coût mesuré (ia_log de cette exécution)
        row = db.execute(__import__("sqlalchemy").text(
            "SELECT count(*) n, coalesce(sum(cout_eur),0) c, coalesce(sum(tokens_in),0) ti, "
            "coalesce(sum(tokens_out),0) to_ FROM ia_log WHERE kind LIKE 'copilote-route%' "
            "AND ts > now() - interval '10 minutes'")).mappings().first()

        print("\n=== MATRICE DE CONFUSION (lignes = attendu, colonnes = obtenu) ===")
        cols = INTENTS
        print("attendu\\obtenu".ljust(16) + "".join(c[:5].ljust(7) for c in cols))
        for att in cols:
            r_ = confusion.get(att, {})
            print(att.ljust(16) + "".join(str(r_.get(c, "·")).ljust(7) for c in cols))

        print("\n=== RATÉS ===")
        for x in results:
            if x["ok"] is False:
                print(f"  [{x['cat']}] « {x['m']} » attendu={x['attendu']} obtenu={x['obtenu']} {x['note']}")
        if not any(x["ok"] is False for x in results):
            print("  (aucun)")

        summary = {
            "n_total": len(results),
            "n_clair": len(clair), "clair_ok": n_clair_ok, "precision_claire_pct": prec_clair,
            "gate_95": prec_clair >= 95.0,
            "ambigu_ok": f"{sum(1 for x in amb if x['ok'])}/{len(amb)}",
            "correction_ok": f"{sum(1 for x in cor if x['ok'])}/{len(cor)}",
            "cout_eur": round(float(row["c"]), 5), "appels": int(row["n"]),
            "tokens_in": int(row["ti"]), "tokens_out": int(row["to_"]),
        }
        print("\n=== BILAN ===")
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return 0 if summary["gate_95"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
