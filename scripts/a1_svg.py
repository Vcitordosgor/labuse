#!/usr/bin/env python
"""Génère la courbe à bosses (SVG pur, sans dépendance) depuis backtest.json.
Deux panneaux : (1) MONO maisons — la tranche actionnable ; (2) APPARTEMENT lot-level
surface-matché — la preuve propre du mécanisme. Marqueurs à +6 et +9 ans."""
import json, os

OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "a1-defisc")
J = json.load(open(os.path.join(OUT, "backtest.json")))

W, H = 860, 720
PADL, PADR, PADT = 70, 30, 46
PANEL_H = 300
GAP = 40
KMIN, KMAX = 3, 12          # on lit à partir de +3 (grâce de 2 ans masque +1/+2)


def hz(table):
    return [(r["k"], r["hazard"]) for r in table if KMIN <= r["k"] <= KMAX]


def panel(y0, title, series, ymax):
    """series = list of (label, table, color, width)."""
    px0, px1 = PADL, W - PADR
    py0, py1 = y0 + PADT, y0 + PANEL_H
    def X(k): return px0 + (k - KMIN) / (KMAX - KMIN) * (px1 - px0)
    def Y(v): return py1 - (v / ymax) * (py1 - py0)
    s = [f'<text x="{PADL}" y="{y0+26}" font-size="16" font-weight="bold" font-family="sans-serif">{title}</text>']
    # grille y
    for gy in range(0, int(ymax * 100) + 1, 10):
        v = gy / 100
        s.append(f'<line x1="{px0}" y1="{Y(v):.1f}" x2="{px1}" y2="{Y(v):.1f}" stroke="#eee"/>')
        s.append(f'<text x="{px0-8}" y="{Y(v)+4:.1f}" font-size="11" text-anchor="end" fill="#666" font-family="sans-serif">{v:.2f}</text>')
    # marqueurs fenêtres +6 et +9
    for k, lbl in ((6, "+6 (Girardin/Pinel 6 ans)"), (9, "+9 (Scellier/Duflot/Pinel 9 ans)")):
        s.append(f'<line x1="{X(k):.1f}" y1="{py0}" x2="{X(k):.1f}" y2="{py1}" stroke="#d33" stroke-dasharray="4 3" opacity="0.5"/>')
        s.append(f'<text x="{X(k)+4:.1f}" y="{py0+12}" font-size="10" fill="#d33" font-family="sans-serif">{lbl}</text>')
    # axes x
    for k in range(KMIN, KMAX + 1):
        s.append(f'<text x="{X(k):.1f}" y="{py1+16:.1f}" font-size="11" text-anchor="middle" fill="#333" font-family="sans-serif">+{k}</text>')
    s.append(f'<text x="{(px0+px1)/2:.0f}" y="{py1+34:.0f}" font-size="12" text-anchor="middle" fill="#333" font-family="sans-serif">ancienneté depuis l\'acquisition (ans)</text>')
    # courbes
    for label, table, color, width in series:
        pts = hz(table)
        d = " ".join(f"{'M' if i==0 else 'L'}{X(k):.1f},{Y(v):.1f}" for i,(k,v) in enumerate(pts))
        s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"/>')
        for k, v in pts:
            s.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="3" fill="{color}"/>')
    return "\n".join(s)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
svg.append(f'<rect width="{W}" height="{H}" fill="white"/>')
svg.append('<text x="16" y="22" font-size="12" fill="#666" font-family="sans-serif">Hazard de revente vs ancienneté — signature « sortie de défiscalisation » (DVF 2014-2025). Grâce 2 ans.</text>')
# légende unique (couleurs communes aux deux panneaux), ancrée à droite de la marge
svg.append(f'<text x="{W-PADR}" y="22" font-size="12" text-anchor="end" fill="#222" font-family="sans-serif">ancien</text>')
svg.append(f'<line x1="{W-PADR-58}" y1="18" x2="{W-PADR-40}" y2="18" stroke="#888" stroke-width="2"/>')
svg.append(f'<text x="{W-PADR-66}" y="22" font-size="12" text-anchor="end" fill="#222" font-family="sans-serif">neuf (VEFA + permis)</text>')
svg.append(f'<line x1="{W-PADR-208}" y1="18" x2="{W-PADR-190}" y2="18" stroke="#1a6" stroke-width="2.5"/>')

mono = J["hazard"]["mono"]
svg.append(panel(30, "1 · MAISONS / monopropriété — tranche actionnable (parcelle = 1 logement)",
                 [("neuf (VEFA + permis ≤3 ans)", mono["neuf"]["table"], "#1a6", 2.5),
                  ("ancien", mono["ancien"]["table"], "#888", 2.0)], ymax=0.09))

apt = J["appartement_lot"]
svg.append(panel(30 + PANEL_H + GAP, "2 · APPARTEMENTS lot-level (surface-matché) — preuve propre du mécanisme",
                 [("neuf VEFA", apt["hazard_neuf"]["table"], "#1a6", 2.5),
                  ("ancien", apt["hazard_anc"]["table"], "#888", 2.0)], ymax=0.45))
svg.append("</svg>")

path = os.path.join(OUT, "courbe_bosses.svg")
open(path, "w").write("\n".join(svg))
print("SVG ->", path)
