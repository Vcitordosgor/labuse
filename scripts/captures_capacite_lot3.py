"""FIX-PRIX-ET-OPPORTUNITES lot 3 — captures AVANT/APRÈS de la capacité « maximum réglementaire ».

Rend sans base les blocs d'export (programme Financier, Comparatif) + une page d'étiquettes
(fiche/Gabarit/Copilote). AVANT = code main (stashé), APRÈS = ce lot.
    PYTHONPATH=src python scripts/captures_capacite_lot3.py apres|avant
"""
from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def main() -> None:
    etat = sys.argv[1] if len(sys.argv) > 1 else "apres"
    out = RACINE / "captures" / "prix-et-opportunites" / etat
    out.mkdir(parents=True, exist_ok=True)
    css = ("<style>body{font-family:sans-serif;padding:24px;background:#fff;color:#111;max-width:720px}"
           "h2,h3{color:#1b5}td{padding:4px 10px;border-bottom:1px solid #eee}.note,p{color:#555;"
           "font-size:12px}.num{font-weight:600}</style>")

    # 1) Bloc Financier — « Le programme » (SDP + logements).
    from labuse.exports.blocs import financier
    prog = {"surface_plancher": 2001, "surface_vendable": 1740, "logements": 24}
    html_prog = financier._programme(prog, {})
    (out / "programme.html").write_text("<html><head><meta charset='utf-8'>" + css + "</head><body>"
                                        + html_prog + "</body></html>")

    # 2) Bloc Comparatif (2 parcelles).
    from labuse.exports.blocs import comparatif
    rows = [{"idu": "97404000AW0099", "commune": "L'Étang-Salé", "zone": "Ua",
             "zone_constructible": True, "sdp_max_m2": 4148, "sdp_residuelle_m2": 4148,
             "logements_possibles": 36, "logements_min": 28, "gabarit_niveaux_max": 4},
            {"idu": "97411000AV0110", "commune": "Saint-Denis", "zone": "U2",
             "zone_constructible": True, "sdp_max_m2": 2600, "sdp_residuelle_m2": 1200,
             "logements_possibles": 20, "logements_min": 14, "gabarit_niveaux_max": 3}]
    (out / "comparatif.html").write_text("<html><head><meta charset='utf-8'>" + css + "</head><body>"
                                         + comparatif.rendu(rows) + "</body></html>")

    # 3) Étiquettes fiche / Gabarit / Copilote.
    if etat == "apres":
        from labuse.capacite_max import MENTION, MENTION_COURTE
        fiche = f"SDP <b>max</b> 2 001 m² · 24 logts<br><span class='note'>{MENTION}</span>"
        gabarit = f"Zone d'implantation · Plafond d'emprise · Hauteur réglementaire<br><span class='note'>{MENTION_COURTE}</span>"
        copil = f"SDP résiduelle : ~2 001 m². C'est un {MENTION_COURTE}."
    else:
        fiche = "SDP 2 001 m² · 24 logts <span class='note'>(aucune mention « maximum »)</span>"
        gabarit = "Zone d'implantation · Plafond d'emprise · Hauteur réglementaire <span class='note'>(aucune mention)</span>"
        copil = "SDP résiduelle : ~2 001 m²."
    (out / "capacite_labels.html").write_text(
        "<html><head><meta charset='utf-8'>" + css.replace("#fff", "#0f1512").replace("#111", "#cfe")
        + "</head><body style='background:#0f1512;color:#cfe'>"
        f"<h3>Fiche · Constructibilité</h3><p>{fiche}</p>"
        f"<h3>Outil Gabarit</h3><p>{gabarit}</p>"
        f"<h3>Copilote · question capacité</h3><p>{copil}</p></body></html>")

    print(f"[{etat}] écrit dans {out}")
    for f in sorted(out.glob("programme.html")) + sorted(out.glob("comparatif.html")) + sorted(out.glob("capacite_labels.html")):
        print("  ", f.name)


if __name__ == "__main__":
    main()
