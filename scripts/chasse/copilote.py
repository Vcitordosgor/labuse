"""CHASSE-1 angle 9 (Copilote) — 60 questions sur 10 parcelles, chiffre énoncé = chiffre fiche.

    python -m scripts.chasse.copilote   # → docs/audit-2026-10/CHASSE-1/COPILOTE.csv

6 questions factuelles par parcelle (surface, zone, taxe, SDP/logements, ventes, commune)
sur 10 parcelles de l'échantillon. Pour chaque réponse : les NOMBRES énoncés doivent se
retrouver sur la fiche JSON de la parcelle (normalisation espaces/séparateurs), sinon le
Copilote doit refuser explicitement. Un chiffre inventé = FAUX. Appels LLM réels (haiku),
quota 20/fiche/jour respecté (6 ≪ 20). En-process, lecture seule de la base.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "COPILOTE.csv"
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "ECHANTILLON.csv"

QUESTIONS = [
    "Quelle est la surface cadastrale de cette parcelle en m² ?",
    "Dans quelle zone du PLU se trouve cette parcelle ?",
    "Quelle est la capacité constructible restante (SDP résiduelle) en m² ?",
    "Combien de logements pourrait-on construire ici, d'après la fiche ?",
    "Quelle a été la dernière vente (date et prix) sur cette parcelle ?",
    "Cette parcelle est-elle concernée par un risque naturel (PPR) ?",
]

REFUS = re.compile(r"ne (peux|puis|dispose|figure)|pas (disponible|calculable|de donnée)"
                   r"|absent|non calculé|je n'ai pas|aucune donnée|indisponible", re.I)


def _nombres(texte: str) -> set[str]:
    """Nombres ≥ 2 chiffres significatifs énoncés dans le texte, normalisés (sans espaces
    fines/insécables ni séparateurs de milliers)."""
    t = re.sub(r"[   ](?=\d)", "", texte)
    return {n.replace(",", ".").rstrip(".0") or "0"
            for n in re.findall(r"\d[\d   ]*[.,]?\d*", t)
            if len(re.sub(r"\D", "", n)) >= 2}


def _nombres_fiche(fiche: dict) -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (int, float)) and x == x:
            for forme in (f"{x}", f"{x:.0f}" if isinstance(x, float) else None,
                          f"{round(x)}" if isinstance(x, float) else None):
                if forme and len(re.sub(r"\D", "", forme)) >= 2:
                    out.add(forme.rstrip(".0") or "0")
        elif isinstance(x, str):
            out.update(_nombres(x))
    walk(fiche)
    return out


def main() -> None:
    from scripts.coherence.lib import client_en_process
    client, fetch = client_en_process()

    with open(ECHANTILLON, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["idu"]]
    # 10 parcelles : les 5 premiers témoins ORACLE-1 + 5 pièges variés
    cibles = [r["idu"] for r in rows if r["bloc"] == "oracle1"][:5]
    for classe in ("permis_caduc", "ppr_rouge_partiel", "copropriete",
                   "sans_adresse_ban", "score_top50"):
        c = next((r["idu"] for r in rows if r["classe"] == classe), None)
        if c:
            cibles.append(c)
    cibles = cibles[:10]

    lignes = []
    for idu in cibles:
        fiche = fetch(f"/parcels/{idu}")
        base = _nombres_fiche(fiche)
        # tolérances d'arrondi : pour chaque nombre de la fiche, admettre ±1 entier
        admis = set(base)
        for n in list(base):
            try:
                v = float(n)
                admis |= {f"{v+1:.0f}".rstrip(".0"), f"{v-1:.0f}".rstrip(".0")}
            except ValueError:
                pass
        for q in QUESTIONS:
            try:
                r = client.post(f"/parcels/{idu}/ask", json={"question": q})
                rep = r.json()
                texte = rep.get("texte") or rep.get("text") or json.dumps(rep)[:300]
            except Exception as e:  # noqa: BLE001
                lignes.append({"idu": idu, "question": q, "reponse": f"ERREUR {str(e)[:80]}",
                               "nombres_hors_fiche": "", "verdict": "ERREUR"})
                continue
            enonces = _nombres(texte)
            # années/quotas usuels tolérés (dates du jour, « 20 questions », pourcentages ronds)
            hors = {n for n in enonces if n not in admis
                    and n not in {"2024", "2025", "2026", "20", "100", "24", "36", "12"}}
            if not enonces and REFUS.search(texte):
                verdict = "REFUS_OK"
            elif hors:
                verdict = "NOMBRE_HORS_FICHE"
            else:
                verdict = "OK"
            lignes.append({"idu": idu, "question": q, "reponse": texte[:220].replace("\n", " "),
                           "nombres_hors_fiche": "; ".join(sorted(hors)[:8]),
                           "verdict": verdict})
            print(f"  {verdict:18s} {idu} — {q[:40]}")

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "question", "reponse",
                                          "nombres_hors_fiche", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    from collections import Counter
    print(f"\n{len(lignes)} réponses : {dict(Counter(l['verdict'] for l in lignes))} → {SORTIE}")


if __name__ == "__main__":
    main()
