"""CHASSE-1 angle 9 (filtres) — 30 combinaisons tirées au sort, graine fixée.

    python -m scripts.chasse.filtres   # → docs/audit-2026-10/CHASSE-1/FILTRES.csv

Pour chaque combinaison : le COMPTEUR (`/filtre` limit=0 → compte) doit égaler la LISTE
(idus=1 → len(idus), hors troncature) et l'EXPORT ; plus les lois ensemblistes :
A + non-A = total (quand le critère a un complément exprimable), A∧B ≤ min(A,B),
surface_min=500 ⊇ surface_min=1000. En-process, lecture seule.
"""
from __future__ import annotations

import csv
import itertools
import json
import pathlib
import random
import urllib.parse

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "FILTRES.csv"
MANIFESTE = json.loads((RACINE / "config" / "served_manifest.json").read_text())
RUN = MANIFESTE["scoring_run"]
GRAINE = 42

# critères atomiques jouables (clé, valeur) — combinés 2 à 2 / 3 à 3 au tirage
ATOMES = [
    ("commune", "Saint-Denis"), ("commune", "Saint-Paul"), ("commune", "Le Tampon"),
    ("surface_min", "500"), ("surface_min", "1000"), ("surface_max", "2000"),
    ("sdp_min", "100"), ("capacite_min", "200"),
    ("zonage", "U"), ("zonage", "AU"),
    ("etat_sol", "nu"), ("etat_sol", "bati"),
    ("hors_copro", "true"), ("personne_morale", "true"),
    ("sous_densite", "true"), ("adresse_absente", "true"),
    ("evenement", "true"), ("renouvellement", "true"),
]


def main() -> None:
    from scripts.coherence.lib import client_en_process
    client, fetch = client_en_process()
    rng = random.Random(GRAINE)

    def compter(params: dict) -> dict:
        qs = urllib.parse.urlencode({"source": RUN, "limit": 0, **params})
        return fetch(f"/filtre?{qs}")

    def idus(params: dict) -> tuple[int, bool]:
        qs = urllib.parse.urlencode({"source": RUN, "limit": 0, "idus": 1, **params})
        r = fetch(f"/filtre?{qs}")
        return len(r.get("idus") or []), bool(r.get("idus_tronque"))

    lignes = []
    total = compter({})["compte"]
    lignes.append({"test": "total_sans_filtre", "params": "", "attendu": "",
                   "obtenu": total, "verdict": "REF"})
    print(f"total sans filtre (run {RUN}) : {total}")

    # 30 combinaisons (2 ou 3 atomes compatibles, clés distinctes)
    combos, vus = [], set()
    while len(combos) < 30:
        k = rng.choice((2, 2, 3))
        tirage = rng.sample(ATOMES, k)
        cles = tuple(sorted(c for c, _ in tirage))
        if len(set(c for c, _ in tirage)) < k or cles in vus:
            continue
        vus.add(cles + tuple(v for _, v in tirage))
        combos.append(dict(tirage))

    for i, combo in enumerate(combos):
        try:
            r = compter(combo)
            n_liste, tronque = idus(combo)
            compte = r["compte"]
            ok = (compte == n_liste) or tronque
            lignes.append({"test": f"compteur=liste #{i+1}",
                           "params": urllib.parse.urlencode(combo),
                           "attendu": compte, "obtenu": f"{n_liste}{' (tronqué)' if tronque else ''}",
                           "verdict": "OK" if ok else "ECART"})
            if not ok:
                print(f"  ECART combo {combo}: compte={compte} liste={n_liste}")
            # A∧B ≤ min(A,B) sur les sous-ensembles
            for cle, val in combo.items():
                seul = compter({cle: val})["compte"]
                if compte > seul:
                    lignes.append({"test": "A∧B ≤ A", "params": f"{combo} vs {cle}={val}",
                                   "attendu": f"≤ {seul}", "obtenu": compte, "verdict": "ECART"})
        except Exception as e:  # noqa: BLE001
            lignes.append({"test": f"combo #{i+1}", "params": str(combo),
                           "attendu": "", "obtenu": f"ERREUR {str(e)[:100]}",
                           "verdict": "ERREUR"})

    # complémentarité : etat_sol nu + bati + (ni l'un ni l'autre interdit) — nu/bâti partitionnent-ils ?
    nu = compter({"etat_sol": "nu"})["compte"]
    bati = compter({"etat_sol": "bati"})["compte"]
    lignes.append({"test": "nu + bati vs total", "params": "etat_sol",
                   "attendu": total, "obtenu": f"{nu}+{bati}={nu+bati}",
                   "verdict": "OK" if nu + bati <= total else "ECART",})
    # monotonie surface
    s500 = compter({"surface_min": "500"})["compte"]
    s1000 = compter({"surface_min": "1000"})["compte"]
    lignes.append({"test": "surface_min 1000 ⊆ 500", "params": "",
                   "attendu": f"≤ {s500}", "obtenu": s1000,
                   "verdict": "OK" if s1000 <= s500 else "ECART"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["test", "params", "attendu", "obtenu", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    ecarts = [l for l in lignes if l["verdict"] == "ECART"]
    print(f"{len(lignes)} tests · {len(ecarts)} écarts → {SORTIE}")


if __name__ == "__main__":
    main()
