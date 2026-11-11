"""GABARIT-3D-1 (pilote) — COUPES en SVG vectoriel, produites par le serveur (révision Astra).

Deux coupes depuis la SCÈNE (``scene.build_scene``) : A « pente dominante », B orientée par la voie.
Exigences appliquées :
  - CADRE (B6) : terrain, sommets de bâti et marges des cotes tiennent dans la vue ; rien ne déborde ;
    flèches dessinées en TRACÉS.
  - ÉCHELLE (B7) : « H = V · sans exagération verticale » + barre graphique ; échelle chiffrée
    seulement si la largeur imprimée (``largeur_mm``) est fournie (PDF).
  - INTERVALLES (B9) : traversées de la parcelle et de la zone en BANDES COTÉES sous le profil, par tronçon.
  - TRAITS N&B (B10) : terrain plein (mesuré), terrain reconstitué en TIRETS (seulement si appuis des
    deux côtés), lacune OUVERTE, limites en trait fin, aplat léger pour le bâti coupé.
  - COTES (B11) : au décimètre, « Altitudes en m, IGN 1989 » une fois, aux POINTS VÉRIFIÉS seulement.
  - INDICATEURS (B12) : pente entre limites (signée) et amplitude séparément ; pente max sur 5 m
    (emplacement reporté) ; pente d'accès si établie.
  - THÈMES (B13) : clair (PDF) / sombre (écran), MÊME contenu.
AUCUN plafond de hauteur n'est dessiné.

Le PLAN-CLÉ (``plan_cle_svg``) : contour cadastral, axe + sens de lecture, bâti traversé, voie, nord.
"""
from __future__ import annotations

import math
from typing import Any

_THEMES = {
    "sombre": {"bg": "#0f1115", "plot": "#161a20", "terrain": "#cbd5e1", "fill": "#1f2630",
               "limite": "#e5e7eb", "zone": "#36c99a", "bati": "#9aa0a6", "txt": "#cbd5e1",
               "txt_dim": "#8b93a1", "grid": "#262c35", "lacune": "#f0603a", "axe": "#e0a44a"},
    "clair": {"bg": "#fafbfc", "plot": "#ffffff", "terrain": "#374151", "fill": "#eceff2",
              "limite": "#111827", "zone": "#2c9f7c", "bati": "#7c828a", "txt": "#374151",
              "txt_dim": "#6b7280", "grid": "#d9dce0", "lacune": "#c0392b", "axe": "#9a6a12"},
}
_FONT = 'font-family="Inter, sans-serif"'
_PONT_RECONSTITUE_M = 3.0   # on relie en tirets un trou ≤ 3 m bordé d'appuis des deux côtés


def _esc(s: Any) -> str:
    import html
    return html.escape(str(s or ""), quote=False)


def _fmt(v: float, dec: int = 0) -> str:
    return (f"{v:.{dec}f}").replace(".", ",")


def _nice_step(span: float, cible: int = 6) -> float:
    if span <= 0:
        return 1.0
    brut = span / cible
    p = 10 ** math.floor(math.log10(brut))
    for m in (1, 2, 5, 10):
        if m * p >= brut:
            return m * p
    return 10 * p


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


def _fleche(x0, y0, x1, y1, col, w=1.4) -> str:
    """Flèche dessinée en tracés (ligne + tête triangulaire)."""
    ang = math.atan2(y1 - y0, x1 - x0)
    hl, ha = 7, math.radians(22)
    xa, ya = x1 - hl * math.cos(ang - ha), y1 - hl * math.sin(ang - ha)
    xb, yb = x1 - hl * math.cos(ang + ha), y1 - hl * math.sin(ang + ha)
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-width="{w}"/>'
            f'<polygon points="{x1:.1f},{y1:.1f} {xa:.1f},{ya:.1f} {xb:.1f},{yb:.1f}" fill="{col}"/>')


def coupe_svg(coupe: dict, *, theme: str = "sombre", width: int = 960, h_max: int = 520,
              largeur_mm: float | None = None) -> str | None:
    """SVG d'une coupe. None si le profil n'a aucun point valide."""
    T = _THEMES.get(theme, _THEMES["sombre"])
    profil = coupe.get("profil") or []
    valides = [p for p in profil if p["z"] is not None]
    if len(valides) < 2:
        return None
    L = coupe["longueur_m"]
    batis = coupe.get("batiments") or []

    # extent vertical : terrain + pieds + SOMMETS de bâti (rien ne déborde — B6)
    zs_all = [p["z"] for p in valides]
    for b in batis:
        for pied in (b.get("pied_amont_m"), b.get("pied_aval_m")):
            if pied is not None:
                zs_all += [pied, pied + (b.get("hauteur_m") or 0)]
    zmin, zmax = min(zs_all), max(zs_all)
    zspan = max(zmax - zmin, 1.0)

    PAD_L, PAD_R, PAD_T = 64, 20, 58
    BANDES_H, IND_H, AX_H = 46, 64, 30            # footer : bandes de traversée, indicateurs, axe X
    plot_w = width - PAD_L - PAD_R
    s = plot_w / max(L, 1e-6)                      # 1:1 : px/m identiques en X et Y
    plot_h = s * zspan
    h_dispo = h_max - PAD_T - BANDES_H - IND_H - AX_H
    if plot_h > h_dispo:
        s = h_dispo / zspan                        # recale (toujours 1:1), largeur réduite, centrée
        plot_w = s * L
        plot_h = h_dispo
    off_x = PAD_L + (width - PAD_L - PAD_R - plot_w) / 2
    y_base = PAD_T + plot_h
    height = int(y_base + AX_H + BANDES_H + IND_H)

    def X(d): return off_x + d * s
    def Y(z): return PAD_T + plot_h - (z - zmin) * s

    def z_terrain(d):
        for run in _runs(profil):
            if run[0]["d"] - 1e-6 <= d <= run[-1]["d"] + 1e-6:
                for a, b in zip(run, run[1:]):
                    if a["d"] <= d <= b["d"] and b["d"] > a["d"]:
                        t = (d - a["d"]) / (b["d"] - a["d"])
                        return a["z"] + t * (b["z"] - a["z"])
        return None

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="{_esc(coupe.get("titre",""))}" {_FONT} '
           f'style="background:{T["bg"]}">']
    out.append(f'<rect x="{off_x:.1f}" y="{PAD_T}" width="{plot_w:.1f}" height="{plot_h:.1f}" '
               f'fill="{T["plot"]}" stroke="{T["grid"]}" stroke-width="0.5"/>')

    # graduations (échelle visible)
    xs = _nice_step(L); zstep = _nice_step(zspan)
    d = 0.0
    while d <= L + 1e-6:
        out.append(f'<line x1="{X(d):.1f}" y1="{PAD_T}" x2="{X(d):.1f}" y2="{y_base:.1f}" stroke="{T["grid"]}" stroke-width="0.4"/>')
        out.append(f'<text x="{X(d):.1f}" y="{y_base+13:.1f}" text-anchor="middle" font-size="9" fill="{T["txt_dim"]}">{_fmt(d)}</text>')
        d += xs
    z = zmin - (zmin % zstep)
    while z <= zmax + 1e-6:
        if z >= zmin - 1e-6:
            out.append(f'<line x1="{off_x:.1f}" y1="{Y(z):.1f}" x2="{off_x+plot_w:.1f}" y2="{Y(z):.1f}" stroke="{T["grid"]}" stroke-width="0.4"/>')
            out.append(f'<text x="{off_x-6:.1f}" y="{Y(z)+3:.1f}" text-anchor="end" font-size="9" fill="{T["txt_dim"]}">{_fmt(z)}</text>')
        z += zstep

    # zone d'implantation : liseré au sol
    for d0, d1 in coupe.get("zone_implantation_d") or []:
        out.append(f'<rect x="{X(d0):.1f}" y="{y_base-5:.1f}" width="{(d1-d0)*s:.1f}" height="5" fill="{T["zone"]}" fill-opacity="0.85"/>')

    # terrain : plein (mesuré) par morceaux + remplissage ; reconstitué en tirets si pont court
    runs = _runs(profil)
    for run in runs:
        if len(run) < 2:
            continue
        pts = " ".join(f"{X(p['d']):.1f},{Y(p['z']):.1f}" for p in run)
        base = f"{X(run[-1]['d']):.1f},{y_base:.1f} {X(run[0]['d']):.1f},{y_base:.1f}"
        out.append(f'<polygon points="{pts} {base}" fill="{T["fill"]}" stroke="none"/>')
        out.append(f'<polyline points="{pts}" fill="none" stroke="{T["terrain"]}" stroke-width="1.8"/>')
    for a, b in zip(runs, runs[1:]):               # terrain reconstitué (tirets) sur trou court
        gap = b[0]["d"] - a[-1]["d"]
        if gap <= _PONT_RECONSTITUE_M:
            out.append(f'<line x1="{X(a[-1]["d"]):.1f}" y1="{Y(a[-1]["z"]):.1f}" x2="{X(b[0]["d"]):.1f}" '
                       f'y2="{Y(b[0]["z"]):.1f}" stroke="{T["terrain"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    for d0, d1 in _lacunes(profil):                # lacune OUVERTE (marque rouge pointillée au sol)
        if (d1 - d0) > _PONT_RECONSTITUE_M:
            out.append(f'<line x1="{X(d0):.1f}" y1="{y_base:.1f}" x2="{X(d1):.1f}" y2="{y_base:.1f}" stroke="{T["lacune"]}" stroke-width="2" stroke-dasharray="2 2"/>')

    # bâti coupé : parallélogramme sur les DEUX pieds (amont/aval), aplat léger ; cote si mesurée
    for b in batis:
        pa, pv, h = b.get("pied_amont_m"), b.get("pied_aval_m"), b.get("hauteur_m")
        if pa is None or pv is None or not h:
            continue
        x0, x1 = X(b["d0"]), X(b["d1"])
        pts = (f'{x0:.1f},{Y(pa):.1f} {x1:.1f},{Y(pv):.1f} {x1:.1f},{Y(pv+h):.1f} {x0:.1f},{Y(pa+h):.1f}')
        # coté (mesuré, 1 seul bâti) = plein ; schématique (hauteur non attribuée) = contour tireté
        dash = '' if b.get("cotee") else ' stroke-dasharray="4 3"'
        op = "0.35" if b.get("cotee") else "0.18"
        out.append(f'<polygon points="{pts}" fill="{T["bati"]}" fill-opacity="{op}" stroke="{T["bati"]}" stroke-width="0.8"{dash}/>')
        yl = Y(max(pa, pv) + h) - 3
        if b.get("cotee"):
            out.append(f'<text x="{(x0+x1)/2:.1f}" y="{yl:.1f}" text-anchor="middle" font-size="8" '
                       f'fill="{T["bati"]}">{_fmt(h,1)} m · {_esc(b.get("provenance"))}</text>')
        else:                                           # volume schématique : mention, SANS chiffre
            out.append(f'<text x="{(x0+x1)/2:.1f}" y="{yl:.1f}" text-anchor="middle" font-size="7.5" '
                       f'fill="{T["txt_dim"]}">{_esc(b.get("provenance") or "hauteur non attribuée")}</text>')

    # limites parcellaires : trait fin vertical
    bornes = sorted({round(v, 2) for sp in (coupe.get("limites_parcelle_d") or []) for v in sp})
    for dl in bornes:
        out.append(f'<line x1="{X(dl):.1f}" y1="{PAD_T}" x2="{X(dl):.1f}" y2="{y_base:.1f}" stroke="{T["limite"]}" stroke-width="0.8" stroke-dasharray="5 3"/>')

    # cotes aux POINTS VÉRIFIÉS seulement (décimètre) — B11
    for pt in (coupe.get("cotes_points") or {}).get("points", []):
        if pt["z"] is None:
            continue
        x, y = X(pt["d"]), Y(pt["z"])
        up = pt["role"] in ("haut", "voie")
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{T["txt"]}"/>')
        out.append(f'<text x="{x:.1f}" y="{(y-5) if up else (y+11):.1f}" text-anchor="middle" '
                   f'font-size="8" fill="{T["txt"]}">{_fmt(pt["z"],1)}</text>')

    # flèche « sens de lecture » (B6) en haut du cadre
    out.append(_fleche(off_x + 6, PAD_T - 8, off_x + 54, PAD_T - 8, T["axe"]))
    sens = "voie vers parcelle" if (coupe.get("voie") and coupe["voie"].get("etablie")) else f'{coupe["label"]} vers {coupe["label"]}′'
    out.append(f'<text x="{off_x+60:.1f}" y="{PAD_T-5:.1f}" font-size="9" fill="{T["txt_dim"]}">{_esc(sens)}</text>')

    # titre + échelle (B7)
    out.append(f'<text x="{PAD_L}" y="18" font-size="13" font-weight="600" fill="{T["txt"]}">{_esc(coupe.get("titre",""))}</text>')
    ech = "H = V · sans exagération verticale · Altitudes en m, IGN 1989"
    if largeur_mm:                                  # échelle chiffrée seulement si largeur imprimée maîtrisée
        ratio = (L / (largeur_mm / 1000.0)) * (plot_w / width)   # m terrain / m papier
        ech += f" · 1:{int(round(ratio))}"
    out.append(f'<text x="{PAD_L}" y="34" font-size="9.5" fill="{T["txt_dim"]}">{_esc(ech)}</text>')
    # barre graphique
    barre = _nice_step(L, 5)
    bx, by = off_x, PAD_T - 26
    out.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx+barre*s:.1f}" y2="{by:.1f}" stroke="{T["txt"]}" stroke-width="2"/>')
    out.append(f'<line x1="{bx:.1f}" y1="{by-3:.1f}" x2="{bx:.1f}" y2="{by+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>')
    out.append(f'<line x1="{bx+barre*s:.1f}" y1="{by-3:.1f}" x2="{bx+barre*s:.1f}" y2="{by+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>')
    out.append(f'<text x="{bx+barre*s+5:.1f}" y="{by+3:.1f}" font-size="8.5" fill="{T["txt_dim"]}">{_fmt(barre)} m</text>')

    # bandes de traversée cotées, par tronçon (B9)
    yb0 = y_base + AX_H
    out.append(_bande(coupe.get("limites_parcelle_d") or [], yb0, X, "parcelle", T))
    out.append(_bande(coupe.get("zone_implantation_d") or [], yb0 + 20, X, "zone d'implantation", T, col=T["zone"]))

    # indicateurs (B12)
    out.append(_indicateurs_txt(coupe, X, Y, z_terrain, y_base + AX_H + BANDES_H, PAD_L, T))

    out.append("</svg>")
    return "".join(out)


def _bande(spans, y, X, label, T, col=None):
    col = col or T["limite"]
    frag = [f'<text x="8" y="{y+4:.1f}" font-size="8.5" fill="{T["txt_dim"]}">{_esc(label)}</text>']
    for d0, d1 in spans:
        x0, x1 = X(d0), X(d1)
        frag.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2.5"/>')
        frag.append(f'<line x1="{x0:.1f}" y1="{y-3:.1f}" x2="{x0:.1f}" y2="{y+3:.1f}" stroke="{col}" stroke-width="1"/>')
        frag.append(f'<line x1="{x1:.1f}" y1="{y-3:.1f}" x2="{x1:.1f}" y2="{y+3:.1f}" stroke="{col}" stroke-width="1"/>')
        frag.append(f'<text x="{(x0+x1)/2:.1f}" y="{y-5:.1f}" text-anchor="middle" font-size="8" fill="{T["txt_dim"]}">{_fmt(d1-d0,1)} m</text>')
    return "".join(frag)


def _indicateurs_txt(coupe, X, Y, z_terrain, y0, pad_l, T):
    ind = coupe.get("indicateurs") or {}
    lignes = []
    for tr in ind.get("traversees") or []:
        p = tr.get("pente_pct")
        sens = tr.get("sens", "")
        lignes.append(f"traversée {_fmt(tr['d0'],1)}–{_fmt(tr['d1'],1)} m : pente {_fmt(p,1) if p is not None else '—'} % ({_esc(sens)}) · amplitude {_fmt(tr['amplitude_m'],1)} m")
    pm = ind.get("pente_max_5m") or {}
    frag = []
    if pm.get("disponible"):
        lignes.append(f"pente max sur 5 m (hors bâti) : {_fmt(pm['pente_pct'],1)} % à {_fmt(pm['d'],1)} m")
        zt = z_terrain(pm["d"])
        if zt is not None:                           # emplacement reporté sur le dessin
            frag.append(f'<line x1="{X(pm["d"]):.1f}" y1="{Y(zt):.1f}" x2="{X(pm["d"]):.1f}" y2="{Y(zt)-18:.1f}" stroke="{T["lacune"]}" stroke-width="1.2"/>')
            frag.append(f'<text x="{X(pm["d"]):.1f}" y="{Y(zt)-20:.1f}" text-anchor="middle" font-size="7.5" fill="{T["lacune"]}">pente max 5 m</text>')
    if ind.get("pente_acces_pct") is not None:
        lignes.append(f"pente d'accès : {_fmt(ind['pente_acces_pct'],1)} %")
    for i, ln in enumerate(lignes[:4]):
        frag.append(f'<text x="{pad_l}" y="{y0+12+i*12:.1f}" font-size="8.5" fill="{T["txt"]}">{_esc(ln)}</text>')
    return "".join(frag)


# ── Plan-clé (B8) : cadastre, axe + sens, bâti traversé, voie, nord ────────────────────────────────

def plan_cle_svg(scene: dict, *, theme: str = "sombre", width: int = 380, height: int = 320) -> str | None:
    T = _THEMES.get(theme, _THEMES["sombre"])
    cad = scene.get("contour_cadastral") or scene.get("parcelle") or []
    if not cad:
        return None
    zone = scene.get("zone_implantation") or []
    batis = scene.get("batiments") or []
    axes = scene.get("axes_plan") or {}

    allpts = [p for poly in cad for p in poly.get("ext", [])]
    for a in axes.values():
        allpts += [a["p0"], a["p1"]]
    if not allpts:
        return None
    minx = min(p[0] for p in allpts); maxx = max(p[0] for p in allpts)
    miny = min(p[1] for p in allpts); maxy = max(p[1] for p in allpts)
    PAD = 26
    s = min((width - 2 * PAD) / max(maxx - minx, 1e-6), (height - 2 * PAD) / max(maxy - miny, 1e-6))
    offx = (width - (maxx - minx) * s) / 2
    offy = (height - (maxy - miny) * s) / 2

    def X(x): return offx + (x - minx) * s
    def Y(y): return height - offy - (y - miny) * s      # nord vers le haut

    def path(poly):
        d = "M" + "L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in poly["ext"]) + "Z"
        for tr in poly.get("trous", []):                  # trous conservés
            d += "M" + "L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in tr) + "Z"
        return d

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="Plan-clé des coupes" {_FONT} '
           f'style="background:{T["bg"]}">']
    for poly in zone:
        out.append(f'<path d="{path(poly)}" fill="{T["zone"]}" fill-opacity="0.4" stroke="{T["zone"]}" stroke-width="1" fill-rule="evenodd"/>')
    for poly in batis:
        emp = poly.get("empreinte") or []
        for sub in emp:
            out.append(f'<path d="{path(sub)}" fill="{T["bati"]}" fill-opacity="0.45" stroke="{T["bati"]}" stroke-width="0.6" fill-rule="evenodd"/>')
    for poly in cad:
        out.append(f'<path d="{path(poly)}" fill="none" stroke="{T["limite"]}" stroke-width="1.4" stroke-dasharray="4 2" fill-rule="evenodd"/>')
    # axes + sens de lecture (flèche en tracés)
    for label, a in axes.items():
        x0, y0, x1, y1 = X(a["p0"][0]), Y(a["p0"][1]), X(a["p1"][0]), Y(a["p1"][1])
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{T["axe"]}" stroke-width="2"/>')
        out.append(_fleche(x0 + (x1 - x0) * 0.72, y0 + (y1 - y0) * 0.72, x1, y1, T["axe"]))
        out.append(f'<text x="{x0:.1f}" y="{y0-5:.1f}" font-size="10" font-weight="600" fill="{T["axe"]}">{label}</text>')
        out.append(f'<text x="{x1:.1f}" y="{y1-5:.1f}" font-size="10" font-weight="600" fill="{T["axe"]}">{label}′</text>')
    # nord
    nx, ny = width - 22, 30
    out.append(_fleche(nx, ny + 16, nx, ny - 8, T["txt"]))
    out.append(f'<text x="{nx:.1f}" y="{ny-11:.1f}" text-anchor="middle" font-size="9" font-weight="600" fill="{T["txt"]}">N</text>')
    out.append(f'<text x="{PAD}" y="16" font-size="10" fill="{T["txt_dim"]}">Plan-clé — contour cadastral, axes et sens de lecture</text>')
    out.append("</svg>")
    return "".join(out)
