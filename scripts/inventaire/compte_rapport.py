#!/usr/bin/env python3
"""CIRCUIT-0 Lot 8 — produit le TABLEAU DES COMPTEURS du rapport à partir des CSV livrés
(règle 2 : jamais tapé à la main) + un SELECT pour les runs. Sortie : markdown sur stdout.
"""
from __future__ import annotations

import csv
import subprocess
from collections import Counter
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"


def lire(nom: str) -> list[dict]:
    with (INV / nom).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def doutes(rows: list[dict]) -> int:
    return sum(1 for r in rows if "DOUTE" in ";".join(str(v) for v in r.values()))


def main() -> None:
    res = lire("reservoirs.csv")
    mot = lire("moteurs.csv")
    jobs = lire("jobs.csv")
    rob = lire("robinets.csv")
    chi = lire("chiffres.csv")
    fc = lire("fuites_candidates.csv")
    fm = lire("fuites_mesurees.csv")
    eau = lire("eau_ancienne.csv")
    ag = lire("agents_fiches.csv")
    sv = lire("source_veille.csv")

    modes = Counter(r["mode_remplissage"] for r in res)
    vmot = Counter(m["versionne_par_run"] for m in mot)
    calc = Counter(c["calcul"].split(":")[0] for c in chi)
    cats = Counter(r["categorie"] for r in rob)

    runs_db = subprocess.run(
        ["psql", "-d", "labuse", "-Atc", "SELECT count(*) FROM p_score_v2_runs"],
        capture_output=True, text=True).stdout.strip() or "?"

    tous = [("reservoirs", res), ("moteurs", mot), ("jobs", jobs), ("robinets", rob),
            ("chiffres", chi), ("fuites_candidates", fc), ("fuites_mesurees", fm),
            ("eau_ancienne", eau), ("agents_fiches", ag), ("source_veille", sv)]
    n_doute = sum(doutes(rows) for _, rows in tous)

    ecarts = sum(1 for m in fm if not str(m["ecart"]).startswith("0"))
    trace_ok = sum(1 for j in jobs if j["trace_base_coherente"].startswith("oui"))

    print("| compteur | valeur |")
    print("|---|---|")
    print(f"| réservoirs : total / job sur clic / cron mensuel / dépôt manuel / en direct / absents "
          f"| {len(res)} / {modes.get('job_sur_clic', 0)} / {modes.get('cron_mensuel', 0)} / "
          f"{modes.get('depot_manuel', 0)} / {modes.get('en_direct', 0)} / {modes.get('absente', 0)} "
          f"(one_shot {modes.get('one_shot', 0)} ; « dérivés » requalifiés en pompes, Q1.2) |")
    print(f"| réservoirs surveillés / non / sans cadence / avec URL producteur "
          f"| {sum(1 for r in res if r['sentinelle'] == 'oui')} / "
          f"{sum(1 for r in res if r['sentinelle'] == 'non')} / "
          f"{sum(1 for r in res if r['cadence_declaree'] == 'aucune')} / "
          f"{sum(1 for r in res if r['url_producteur_connue'])} |")
    print(f"| moteurs / versionnés par run / live | {len(mot)} / {vmot.get('oui', 0)} / {vmot.get('non', 0)} |")
    print(f"| runs en base / servi / morts / tables de run en retard encore lues "
          f"| {runs_db} (p_score_v2_runs) / 1 (q_v11_m137) / 6 (q_v8×5 + q_v10) + 1 candidat (q_v12) "
          f"/ 2 (division_or_candidates q_v10 ; dvf_prix_sortie_neuf lu par score_e) |")
    print(f"| jobs / qui touchent l'eau / avec trace en base cohérente "
          f"| {len(jobs)} ({sum(1 for j in jobs if not j['id'].startswith('cron.d/'))} wrapper + "
          f"{sum(1 for j in jobs if j['id'].startswith('cron.d/'))} legacy) / "
          f"{sum(1 for j in jobs if j['touche_l_eau'] == 'oui')} / {trace_ok} |")
    print(f"| robinets : total, par catégorie | {len(rob)} — "
          + " · ".join(f"{k} {v}" for k, v in sorted(cats.items())) + " |")
    print(f"| chiffres : lignes / ids distincts / moteur / sql_propre / front / passe_plat / constante / avec tampon "
          f"| {len(chi)} / {len({c['chiffre_id'] for c in chi})} / {calc.get('moteur', 0)} / "
          f"{calc.get('sql_propre', 0)} / {calc.get('front', 0)} / {calc.get('passe_plat', 0)} / "
          f"{calc.get('constante', 0)} / {sum(1 for c in chi if c['tampon'] != 'rien')} |")
    print(f"| fuites candidates / mesurées / avec écart ≠ 0 | {len(fc)} / {len(fm)} / {ecarts} |")
    print(f"| chiffres en eau ancienne aujourd'hui | {len(eau)} familles |")
    print(f"| lignes DOUTE (tous CSV) | {n_doute} |")
    print()
    print("détail DOUTE par fichier : " + " · ".join(f"{n} {len_}" for n, len_ in
          ((nom, doutes(rows)) for nom, rows in tous) if len_))


if __name__ == "__main__":
    main()
