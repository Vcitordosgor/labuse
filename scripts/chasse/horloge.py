"""CHASSE-1 angle 7 — le temps qui passe.

    python -m scripts.chasse.horloge   # → docs/audit-2026-10/CHASSE-1/HORLOGE.csv

Deux lectures EN-PROCESS de la même fiche : à l'heure vraie, puis sous freezegun à
+400 jours. freezegun ne gèle QUE l'horloge Python : un champ qui change = calculé en
Python « depuis aujourd'hui » à la requête ; un champ qui ne change pas = figé au run OU
calculé en SQL (now() de PostgreSQL, non gelé). Un couple de lecteurs d'une même notion
où l'un bouge et pas l'autre = DISCORDANT temporel (deux horloges pour un même fait).
Complété par un inventaire grep des horloges (datetime.now naïf vs UTC vs Réunion).
Lecture seule.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "HORLOGE.csv"
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "ECHANTILLON.csv"

# témoins : un de chaque famille sensible au temps (permis caduc, DVF récent, dormant…)
N_PARCELLES = 8


def _feuilles(prefixe: str, x, out: dict) -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            _feuilles(f"{prefixe}.{k}", v, out)
    elif isinstance(x, list):
        out[prefixe + ".len"] = len(x)
        for i, v in enumerate(x[:30]):
            _feuilles(f"{prefixe}[{i}]", v, out)
    else:
        out[prefixe] = x


def main() -> None:
    from scripts.coherence.lib import client_en_process
    client, fetch = client_en_process()

    with open(ECHANTILLON, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["idu"]]
    cibles = ([r for r in rows if r["classe"] == "permis_caduc"][:3]
              + [r for r in rows if r["bloc"] == "oracle1"][:5])[:N_PARCELLES]

    avant: dict[str, dict] = {}
    for r in cibles:
        avant[r["idu"]] = fetch(f"/parcels/{r['idu']}")

    import freezegun
    plus400 = dt.datetime.now() + dt.timedelta(days=400)
    lignes = []
    with freezegun.freeze_time(plus400, tick=False, real_asyncio=True):
        for r in cibles:
            idu = r["idu"]
            try:
                apres = fetch(f"/parcels/{idu}")
            except Exception as e:  # noqa: BLE001
                lignes.append({"idu": idu, "champ": "(fiche entière)",
                               "avant": "", "apres": f"ERREUR {str(e)[:120]}",
                               "verdict": "erreur_sous_gel"})
                continue
            fa, fb = {}, {}
            _feuilles("", avant[idu], fa)
            _feuilles("", apres, fb)
            for k in sorted(set(fa) | set(fb)):
                va, vb = fa.get(k), fb.get(k)
                if va != vb:
                    lignes.append({"idu": idu, "champ": k,
                                   "avant": str(va)[:100], "apres": str(vb)[:100],
                                   "verdict": "bouge_horloge_python"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "champ", "avant", "apres", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    from collections import Counter
    champs = Counter(l["champ"].split("[")[0] for l in lignes)
    print(f"{len(lignes)} champs qui bougent à +400 j sur {len(cibles)} fiches → {SORTIE}")
    for c, n in champs.most_common(25):
        print(f"  {n:3d} {c}")


if __name__ == "__main__":
    main()
