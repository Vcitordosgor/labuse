"""VERITE-TERRAIN-3 — faisabilité en DIRECT (moteur de main) des parcelles R et T.

Sert la « surface à retenir » du LOT 4 : pour ces parcelles sans Étude dessinée, la surface à
retenir de la fiche = l'estimation rapide (faisabilite/surface_retenue.py, règle LOT D : la plus
petite des deux, esquisse absente → estimation). On calcule donc l'estimation rapide du moteur.
Réutilise la fonction et le CACHE du rejeu (docs/.../cache/capacite/).

    PYTHONPATH=src:docs/audit-2026-11/verite-terrain-3/scripts \
      python docs/audit-2026-11/verite-terrain-3/scripts/lot4_faisa_live.py
"""
from __future__ import annotations

import csv
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
COHORTES = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3" / "cohortes"
SORTIE = COHORTES / "FAISA-LIVE-R-T.csv"


def main() -> None:
    from rejouer_capacite_vt3 import capacite_labuse_vt3, vt

    idus: dict[str, str] = {}
    with open(COHORTES / "R.csv", newline="") as f:
        for r in csv.DictReader(f):
            idus[r["idu"]] = "R"
    with open(COHORTES / "T.csv", newline="") as f:
        for r in csv.DictReader(f):
            idus.setdefault(r["idu"], "T")

    conn = vt._connect()
    out = []
    for i, (idu, coh) in enumerate(sorted(idus.items()), 1):
        c = capacite_labuse_vt3(conn, idu)
        out.append({"idu": idu, "cohorte": coh, "constructible": c.get("constructible"),
                    "cause": c.get("cause"), "zone": c.get("zone"), "zone_fam": c.get("zone_fam"),
                    "sdp_estimation_m2": c.get("sdp_max_m2"),
                    "emprise_constructible_m2": c.get("emprise_constructible_m2"),
                    "niveaux_max": c.get("niveaux_max")})
        if i % 200 == 0:
            print(f"  {i}/{len(idus)}", flush=True)
    conn.close()

    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"→ {SORTIE} ({len(out)} lignes)")


if __name__ == "__main__":
    main()
