"""M41 P1 — SEED (one-shot) de config/veille_plu.yaml depuis Sudocuh (P0) + M40.

Génère le registre INITIAL proposé au STOP (validé par Vic). Après ce seed, le fichier est
CURATÉ À LA MAIN (ne PAS re-lancer sur un fichier curaté — il écraserait la curation). Le seed
encode la logique de confiance arbitrée par Vic :
- procédure Sudocuh en cours + opposable M40 NON postérieur à la prescription → CIBLE, confiance
  SOURCE (la prescription est sourcée Sudocuh) ; débat PADD = ABSENT (à curer → arme le sursis) ;
- procédure Sudocuh en cours + opposable M40 postérieur → cloturee, confiance DEDUIT (raisonnement
  écrit ; on ne sert pas une inférence — hors radar actif, tracée) ;
- Sudocuh « Aucun » → aucune, confiance SOURCE (l'absence de procédure lourde est datée).

Usage (one-shot) : PYTHONPATH=src python scripts/m41_seed_veille_plu.py > config/veille_plu.yaml
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from labuse import config as C  # noqa: E402

SUD_URL = "https://www.data.gouv.fr/api/1/datasets/r/61541a0f-e9b0-43dc-bace-6c3905714400"
MILL = "Sudocuh 31/12/2024"
CONSTAT = "2026-08-06"
CSV = os.path.join(os.path.dirname(__file__), "..", "qa", "m41", "sudocuh_974_p0.csv")

TYPE = {"PLU": "revision_plu"}  # affiné ci-dessous pour élaboration (RNU opposable)


def main() -> None:
    m40 = (C.load_yaml_config("plu_millesimes") or {}).get("communes", {})
    sud = {}
    with open(CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sud[r["insee"]] = r
    lines = [
        "# M41 — RADAR PROCÉDURES PLU : registre curaté des 24 communes (chair du radar).",
        "# Squelette = Sudocuh (data.gouv.fr, Licence Ouverte 2.0). Chair = ce registre, curaté à la",
        "# main, rafraîchi par passe trimestrielle (scripts/veille_plu_check.py).",
        "#",
        "# DOCTRINE (arbitrages Vic M41) :",
        "# - `confiance` OBLIGATOIRE par entrée : SOURCE (pièce référencée) | DEDUIT (raisonnement",
        "#   écrit) | ABSENT (on ne sait pas). Le lint (labuse.veille_plu) refuse toute entrée",
        "#   incomplète ou sans confiance.",
        "# - Le radar ne SERT EN VIGILANCE que les entrées confiance=SOURCE. DEDUIT/ABSENT sont",
        "#   tracés mais jamais servis (on ne sert pas une inférence comme un fait).",
        "# - Vigilance SURSIS : servie UNIQUEMENT si `debat_padd` est une date constatée (sourcée).",
        "#   Tant que débat PADD = ABSENT, AUCUNE vigilance sursis (pas de conditionnel flou en fiche).",
        "# - Base légale sursis : Code de l'urbanisme L.153-11 (seuil = débat PADD) + L.424-1 (max 2 ans),",
        "#   révision/élaboration seulement (une modification n'a pas de PADD → pas de sursis L.153-11).",
        "# - Le radar dit le STADE et ses conséquences juridiques ACTUELLES, JAMAIS l'issue de la procédure.",
        "#",
        "# Schéma strict (tous champs obligatoires) : commune, procedure, stade, date_acte, debat_padd,",
        "#   source, source_url, date_constat, confiance. `raisonnement` obligatoire si confiance=DEDUIT.",
        "meta:",
        f'  source_squelette: "{MILL} (Planification nationale PLU/PLUi/CC/RNU — SuDocUH)"',
        f'  source_url: "{SUD_URL}"',
        f'  date_constat_initial: "{CONSTAT}"',
        '  cadence: "annuelle (Sudocuh) ; curation trimestrielle (registre) ; radar actif = 30 j"',
        "communes:",
    ]

    def emit(insee, d):
        lines.append(f'  "{insee}":')
        for k in ("commune", "procedure", "stade", "date_acte", "debat_padd", "source",
                  "source_url", "date_constat", "confiance"):
            v = d[k]
            lines.append(f'    {k}: "{v}"' if v not in ("ABSENT",) else f'    {k}: ABSENT')
        if d.get("raisonnement"):
            lines.append(f'    raisonnement: "{d["raisonnement"]}"')
        if d.get("note"):
            lines.append(f'    note: "{d["note"]}"')

    for insee in sorted(sud):
        s = sud[insee]
        m = m40.get(insee, {})
        commune = s["commune"]
        en_cours = s["du_en_cours"] != "Aucun"
        presc = s["prescription_proc_en_cours"] or ""
        approb = s["approbation_du_vigueur"] or ""
        dm = m.get("date_mairie") or ""
        opp_is_rnu = (m.get("statut") == "rnu") or (s["du_opposable"] == "RNU")
        if en_cours:
            proc = "elaboration_plu" if opp_is_rnu else "revision_plu"
            if dm and presc and dm > presc and not opp_is_rnu:
                # opposable M40 postérieur à la prescription → clôture déduite
                emit(insee, {
                    "commune": commune, "procedure": "cloturee", "stade": "approuvee_probable",
                    "date_acte": "ABSENT", "debat_padd": "ABSENT",
                    "source": f"{MILL} (procédure) + M40 plu_millesimes (opposable {dm})",
                    "source_url": SUD_URL, "date_constat": CONSTAT, "confiance": "DEDUIT",
                    "raisonnement": (f"Sudocuh liste une révision prescrite {presc} MAIS l'opposable "
                                     f"M40/GPU est daté {dm} (postérieur) → la révision a été approuvée "
                                     f"depuis (Sudocuh 31/12/2024 périmé). Non confirmé par la délibération "
                                     f"d'approbation elle-même → DEDUIT, hors radar actif.")})
            else:
                stade = "prescrite" if not opp_is_rnu else "prescrite_dormante"
                note = None
                if opp_is_rnu:
                    note = ("Élaboration PLU prescrite il y a 24 ans, commune toujours en RNU, aucun acte "
                            "postérieur connu — dormante. Au radar (factuel) mais pas de vigilance sursis.")
                emit(insee, {
                    "commune": commune, "procedure": proc, "stade": stade,
                    "date_acte": presc or "ABSENT", "debat_padd": "ABSENT",
                    "source": f"{MILL} (prescription)", "source_url": SUD_URL,
                    "date_constat": CONSTAT, "confiance": "SOURCE", "note": note})
        else:
            note = None
            if "modif" in (m.get("note") or "").lower():
                note = ("Sudocuh ne trace pas les modifications (procédure légère) : d'éventuelles modifs "
                        "postérieures ne sont pas visibles ici — l'absence de procédure LOURDE est datée, "
                        "les modifs restent à confirmer en mairie (M40).")
            emit(insee, {
                "commune": commune, "procedure": "aucune", "stade": "aucune",
                "date_acte": "ABSENT", "debat_padd": "ABSENT",
                "source": f"{MILL} (aucune procédure lourde)", "source_url": SUD_URL,
                "date_constat": CONSTAT, "confiance": "SOURCE", "note": note})

    print("\n".join(lines))


if __name__ == "__main__":
    main()
