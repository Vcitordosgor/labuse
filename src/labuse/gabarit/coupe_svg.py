"""GABARIT-3D-1 (pilote) — COUPES en SVG vectoriel, produites par le serveur.

Deux coupes automatiques depuis la SCÈNE (``scene.build_scene``) : la plus grande pente (A-A') et
la voie→parcelle par l'accès (B-B'). Profil au pas de 1 m, limites, bâtiments coupés, étendue de la
zone d'implantation, cotes (altitudes, dénivelé, pente). ÉCHELLE HORIZONTALE = VERTICALE (1:1, aucune
exagération — la forme du terrain est vraie). Les échelles sont visibles (graduations + barre). Une
coupe s'INTERROMPT au droit d'une lacune (le profil est tracé par morceaux). AUCUN plafond de hauteur
n'est dessiné (les hauteurs en pente sont le mandat suivant). Le même SVG alimente l'écran et le PDF.

Un PLAN-CLÉ (``plan_cle_svg``) reporte les deux axes sur le plan (parcelle + zone), comme demandé.
"""
from __future__ import annotations

from typing import Any

C_TERRAIN = "#6b7280"      # ligne de terrain naturel
C_TERRAIN_FILL = "#eceff2"
C_LIMITE = "#111827"       # limites parcellaires
C_ZONE = "#36c99a"         # zone d'implantation
C_BATI = "#7c828a"         # bâti existant coupé
C_AXE = "#e0a44a"          # trace des axes sur le plan
C_GRID = "#d5d7db"
C_TXT = "#374151"

_FONT = 'font-family="Inter, sans-serif"'


def _nice_step(span: float, cible: int = 6) -> float:
    """Pas de graduation « rond » (1/2/5 × 10^k) pour ~`cible` graduations sur `span`."""
    if span <= 0:
        return 1.0
    import math
    brut = span / cible
    p = 10 ** math.floor(math.log10(brut))
    for m in (1, 2, 5, 10):
        if m * p >= brut:
            return m * p
    return 10 * p


def _fmt(v: float) -> str:
    return (f"{v:.0f}" if abs(v - round(v)) < 1e-6 else f"{v:.1f}").replace(".", ",")


def coupe_svg(coupe: dict, *, width: int = 900, h_max: int = 460) -> str | None:
    """SVG d'une coupe. None si le profil n'a aucun point valide (relief indisponible)."""
    profil = coupe.get("profil") or []
    valides = [p for p in profil if p["z"] is not None]
    if len(valides) < 2:
        return None
    L = coupe["longueur_m"]
    zmin = min(p["z"] for p in valides)
    zmax = max(p["z"] for p in valides)
    zspan = max(zmax - zmin, 1.0)

    PAD_L, PAD_R, PAD_T, PAD_B = 58, 16, 54, 46
    plot_w = width - PAD_L - PAD_R
    # échelle 1:1 : mêmes px/m en X et Y. On cale sur la largeur, puis on borne la hauteur.
    s = plot_w / max(L, 1e-6)
    plot_h = s * zspan
    if plot_h > (h_max - PAD_T - PAD_B):
        # profil très accidenté : on recale sur la hauteur (toujours 1:1), largeur réduite
        s = (h_max - PAD_T - PAD_B) / zspan
        plot_w = s * L
    height = int(plot_h + PAD_T + PAD_B) if plot_h <= (h_max - PAD_T - PAD_B) else h_max
    plot_h = height - PAD_T - PAD_B

    def X(d): return PAD_L + d * s
    def Y(z): return PAD_T + plot_h - (z - zmin) * s

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="{_esc(coupe.get("titre",""))}" {_FONT} '
           f'style="background:#fafbfc;border:1px solid #d5d7db">']

    # grille + graduations (échelle visible) — X en distance, Y en altitude
    xs = _nice_step(L); zs = _nice_step(zspan)
    d = 0.0
    while d <= L + 1e-6:
        out.append(f'<line x1="{X(d):.1f}" y1="{PAD_T:.1f}" x2="{X(d):.1f}" y2="{PAD_T+plot_h:.1f}" '
                   f'stroke="{C_GRID}" stroke-width="0.5"/>')
        out.append(f'<text x="{X(d):.1f}" y="{PAD_T+plot_h+14:.1f}" text-anchor="middle" '
                   f'font-size="9" fill="{C_TXT}">{_fmt(d)}</text>')
        d += xs
    z = zmin - (zmin % zs)
    while z <= zmax + 1e-6:
        if z >= zmin - 1e-6:
            out.append(f'<line x1="{PAD_L:.1f}" y1="{Y(z):.1f}" x2="{PAD_L+plot_w:.1f}" y2="{Y(z):.1f}" '
                       f'stroke="{C_GRID}" stroke-width="0.5"/>')
            out.append(f'<text x="{PAD_L-6:.1f}" y="{Y(z)+3:.1f}" text-anchor="end" '
                       f'font-size="9" fill="{C_TXT}">{_fmt(z)}</text>')
        z += zs
    out.append(f'<text x="{PAD_L+plot_w/2:.1f}" y="{height-6:.1f}" text-anchor="middle" '
               f'font-size="10" fill="{C_TXT}">distance (m) — échelle 1:1 (H = V), 1 px = {_fmt(1/s)} m</text>')
    out.append(f'<text x="14" y="{PAD_T+plot_h/2:.1f}" text-anchor="middle" font-size="10" '
               f'fill="{C_TXT}" transform="rotate(-90 14 {PAD_T+plot_h/2:.1f})">altitude (m, REUN89)</text>')

    # zone d'implantation : bandes au sol (étendue traversée)
    for d0, d1 in coupe.get("zone_implantation_d") or []:
        out.append(f'<rect x="{X(d0):.1f}" y="{PAD_T+plot_h-6:.1f}" width="{(d1-d0)*s:.1f}" height="6" '
                   f'fill="{C_ZONE}" fill-opacity="0.8"/>')

    # terrain : par morceaux (interruption aux lacunes), avec un remplissage sous la ligne
    for run in _runs(profil):
        if len(run) < 2:
            continue
        pts = " ".join(f"{X(p['d']):.1f},{Y(p['z']):.1f}" for p in run)
        base = f"{X(run[-1]['d']):.1f},{PAD_T+plot_h:.1f} {X(run[0]['d']):.1f},{PAD_T+plot_h:.1f}"
        out.append(f'<polygon points="{pts} {base}" fill="{C_TERRAIN_FILL}" stroke="none"/>')
        out.append(f'<polyline points="{pts}" fill="none" stroke="{C_TERRAIN}" stroke-width="1.6"/>')
    # marque les lacunes (segments manquants) par un liseré rouge pointillé à la base
    for d0, d1 in _lacunes(profil):
        out.append(f'<line x1="{X(d0):.1f}" y1="{PAD_T+plot_h:.1f}" x2="{X(d1):.1f}" y2="{PAD_T+plot_h:.1f}" '
                   f'stroke="#e8491d" stroke-width="2" stroke-dasharray="3 2"/>')

    # bâtiments coupés : rectangle posé sur le terrain (hauteur mesurée/estimée)
    for b in coupe.get("batiments") or []:
        h = b.get("hauteur_m")
        if not h or h <= 0:
            continue
        zt = _z_terrain(profil, (b["d0"] + b["d1"]) / 2) or zmin
        x0, x1 = X(b["d0"]), X(b["d1"])
        yb, yt = Y(zt), Y(zt + h)
        out.append(f'<rect x="{x0:.1f}" y="{yt:.1f}" width="{max(x1-x0,1):.1f}" height="{yb-yt:.1f}" '
                   f'fill="{C_BATI}" fill-opacity="0.55" stroke="{C_BATI}" stroke-width="0.8"/>')
        prov = b.get("provenance") or ""
        out.append(f'<text x="{(x0+x1)/2:.1f}" y="{yt-3:.1f}" text-anchor="middle" font-size="8" '
                   f'fill="{C_BATI}">{_fmt(h)} m ({_esc(prov)})</text>')

    # limites parcellaires : traits verticaux noirs aux entrées/sorties
    bornes = sorted({round(v, 2) for sp in (coupe.get("limites_parcelle_d") or []) for v in sp})
    for dloc in bornes:
        out.append(f'<line x1="{X(dloc):.1f}" y1="{PAD_T:.1f}" x2="{X(dloc):.1f}" y2="{PAD_T+plot_h:.1f}" '
                   f'stroke="{C_LIMITE}" stroke-width="1" stroke-dasharray="5 3"/>')
    if bornes:
        out.append(f'<text x="{X(bornes[0]):.1f}" y="{PAD_T-6:.1f}" text-anchor="middle" font-size="8" '
                   f'fill="{C_LIMITE}">limite</text>')

    # titre + cotes
    co = coupe.get("cotes") or {}
    out.append(f'<text x="{PAD_L}" y="16" font-size="12" font-weight="600" fill="#111827">'
               f'{_esc(coupe.get("titre",""))}</text>')
    sous = f"longueur {_fmt(L)} m"
    if coupe.get("voie"):
        sous += f" · depuis {_esc(coupe['voie'])}"
    if co.get("disponible"):
        sous += (f" · dénivelé {_fmt(co['denivele_m'])} m · pente moyenne {_fmt(co['pente_moyenne_pct'])} %"
                 f" · plus forte pente {_fmt(co['pente_max_pct'])} %")
        if co.get("n_lacune"):
            sous += f" · {co['n_lacune']} lacune(s) — profil interrompu"
    out.append(f'<text x="{PAD_L}" y="32" font-size="9.5" fill="{C_TXT}">{sous}</text>')
    out.append("</svg>")
    return "".join(out)


def plan_cle_svg(scene: dict, *, width: int = 360, height: int = 300) -> str | None:
    """Plan-clé : parcelle + zone d'implantation + trace des deux axes (A-A', B-B')."""
    parcelle = scene.get("parcelle") or []
    if not parcelle:
        return None
    zone = scene.get("zone_implantation") or []
    axes = scene.get("axes_plan") or {}
    pts = [p for ring in parcelle for p in ring]
    for a in axes.values():
        pts += [a["p0"], a["p1"]]
    minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
    PAD = 20
    s = min((width - 2 * PAD) / max(maxx - minx, 1e-6), (height - 2 * PAD) / max(maxy - miny, 1e-6))
    offx = (width - (maxx - minx) * s) / 2
    offy = (height - (maxy - miny) * s) / 2

    def X(x): return offx + (x - minx) * s
    def Y(y): return height - offy - (y - miny) * s   # nord vers le haut

    def path(ring):
        return "M" + "L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in ring) + "Z"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="Plan-clé des coupes" {_FONT} '
           f'style="background:#fafbfc;border:1px solid #d5d7db">']
    for ring in zone:
        out.append(f'<path d="{path(ring)}" fill="{C_ZONE}" fill-opacity="0.45" stroke="{C_ZONE}" stroke-width="1"/>')
    for ring in parcelle:
        out.append(f'<path d="{path(ring)}" fill="none" stroke="{C_LIMITE}" stroke-width="1.4" stroke-dasharray="4 2"/>')
    for label, a in axes.items():
        x0, y0 = X(a["p0"][0]), Y(a["p0"][1]); x1, y1 = X(a["p1"][0]), Y(a["p1"][1])
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                   f'stroke="{C_AXE}" stroke-width="2"/>')
        out.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="3" fill="{C_AXE}"/>')
        out.append(f'<text x="{x0:.1f}" y="{y0-5:.1f}" font-size="10" font-weight="600" fill="#9a6a12">{label}</text>')
        out.append(f'<text x="{x1:.1f}" y="{y1-5:.1f}" font-size="10" font-weight="600" fill="#9a6a12">{label}′</text>')
    out.append(f'<text x="{PAD}" y="16" font-size="10" fill="{C_TXT}">Plan-clé — axes des coupes</text>')
    out.append("</svg>")
    return "".join(out)


# ── helpers ───────────────────────────────────────────────────────────────────────────────────────

def _runs(profil: list[dict]) -> list[list[dict]]:
    runs, cur = [], []
    for p in profil:
        if p["z"] is None:
            if cur:
                runs.append(cur); cur = []
        else:
            cur.append(p)
    if cur:
        runs.append(cur)
    return runs


def _lacunes(profil: list[dict]) -> list[tuple[float, float]]:
    out, start = [], None
    for p in profil:
        if p["z"] is None and start is None:
            start = p["d"]
        elif p["z"] is not None and start is not None:
            out.append((start, p["d"])); start = None
    if start is not None:
        out.append((start, profil[-1]["d"]))
    return out


def _z_terrain(profil: list[dict], d: float) -> float | None:
    """Altitude du terrain interpolée à la distance d (None si lacune locale)."""
    valides = [p for p in profil if p["z"] is not None]
    if not valides:
        return None
    for a, b in zip(valides, valides[1:]):
        if a["d"] <= d <= b["d"] and b["d"] > a["d"]:
            t = (d - a["d"]) / (b["d"] - a["d"])
            return a["z"] + t * (b["z"] - a["z"])
    return min(valides, key=lambda p: abs(p["d"] - d))["z"]


def _esc(s: Any) -> str:
    import html
    return html.escape(str(s or ""), quote=False)
