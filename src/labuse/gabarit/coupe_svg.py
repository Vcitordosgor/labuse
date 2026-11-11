"""GABARIT-3D-1 (pilote) — PLANCHES de coupe en SVG serveur (révision Astra, étape 1 ter).

B5  Bâti : emprise marquée AU SOL ; terrain coté au droit des deux façades si possible ; mention à part
    « Hauteur au faîtage estimée par LiDAR · X m » quand attribuée ; AUCUN toit. Sous l'emprise le trait
    s'interrompt ; les tirets sont réservés à un profil reconstruit entre deux appuis extérieurs (légende).
B6  Pente max sur 5 m : 5 m entiers, un seul tronçon valide, dans la parcelle, hors emprise bâtie ±1 m ;
    DEUX bornes dessinées. Cotes de limite, bandes et pente entre limites partagent les mêmes bornes.
B7  Échelle : barre graphique dans un EMPLACEMENT RÉSERVÉ (écran + PDF) ; ratio chiffré au PDF seulement.
B8  Voie à son intersection ; « pente sur l'axe de la voie à la limite » seulement si profil continu.
B9  Pas de collision de textes (anti-collision) ; une seule cote par point ; en-tête identifiant+adresse ;
    thème SOMBRE complet ; bande d'implantation « non traversée »/« indisponible ».
AUCUN plafond de hauteur n'est dessiné.
"""
from __future__ import annotations

import math
from typing import Any

_THEMES = {
    "sombre": {"bg": "#0f1115", "plot": "#161a20", "terrain": "#cbd5e1", "fill": "#1f2630",
               "limite": "#e5e7eb", "zone": "#36c99a", "bati": "#9aa0a6", "txt": "#d7dce3",
               "txt_dim": "#8b93a1", "grid": "#262c35", "lacune": "#f0603a", "axe": "#e0a44a",
               "head": "#1a1f27"},
    "clair": {"bg": "#ffffff", "plot": "#ffffff", "terrain": "#374151", "fill": "#eef1f4",
              "limite": "#111827", "zone": "#2c9f7c", "bati": "#6b7280", "txt": "#1f2937",
              "txt_dim": "#6b7280", "grid": "#dadfe4", "lacune": "#c0392b", "axe": "#9a6a12",
              "head": "#f3f4f6"},
}
_FONT = 'font-family="Inter, Helvetica, Arial, sans-serif"'
_PONT_RECONSTITUE_M = 3.0


def _esc(s: Any) -> str:
    import html
    return html.escape(str(s or ""), quote=False)


def _fmt(v, dec=0) -> str:
    if v is None:
        return "—"
    return (f"{v:.{dec}f}").replace(".", ",")


def _nice_step(span, cible=6):
    if span <= 0:
        return 1.0
    brut = span / cible
    p = 10 ** math.floor(math.log10(brut))
    for m in (1, 2, 5, 10):
        if m * p >= brut:
            return m * p
    return 10 * p


def _runs(profil):
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


def _soustraire(seg, spans):
    """Retire de [d0,d1] les intervalles `spans` (emprises bâties) → liste de sous-segments."""
    out = [seg]
    for a, b in spans:
        nxt = []
        for s0, s1 in out:
            if b <= s0 or a >= s1:
                nxt.append((s0, s1))
            else:
                if s0 < a:
                    nxt.append((s0, a))
                if b < s1:
                    nxt.append((b, s1))
        out = nxt
    return out


def _fleche(x0, y0, x1, y1, col, w=1.4):
    ang = math.atan2(y1 - y0, x1 - x0)
    hl, ha = 7, math.radians(22)
    xa, ya = x1 - hl * math.cos(ang - ha), y1 - hl * math.sin(ang - ha)
    xb, yb = x1 - hl * math.cos(ang + ha), y1 - hl * math.sin(ang + ha)
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-width="{w}"/>'
            f'<polygon points="{x1:.1f},{y1:.1f} {xa:.1f},{ya:.1f} {xb:.1f},{yb:.1f}" fill="{col}"/>')


def coupe_svg(coupe, *, theme="sombre", width=960, h_max=520, adresse=None, idu=None):
    """SVG d'une coupe. None si le profil n'a aucun point valide."""
    T = _THEMES.get(theme, _THEMES["sombre"])
    profil = coupe.get("profil") or []
    valides = [p for p in profil if p["z"] is not None]
    if len(valides) < 2:
        return None
    L = coupe["longueur_m"]
    batis = coupe.get("batiments") or []
    bati_spans = [(b["d0"], b["d1"]) for b in batis]

    zs_all = [p["z"] for p in valides]
    for b in batis:                                   # inclure pied + faîtage au cadrage
        if b.get("pied_m") is not None:
            zs_all.append(b["pied_m"])
            if b.get("hauteur_m"):
                zs_all.append(b["pied_m"] + b["hauteur_m"])
    zmin, zmax = min(zs_all), max(zs_all)
    zspan = max(zmax - zmin, 1.0)

    HEAD = 38
    PAD_L, PAD_R, PAD_T = 64, 20, HEAD + 34
    BANDES_H, IND_H, AX_H = 44, 70, 28
    plot_w = width - PAD_L - PAD_R
    s = plot_w / max(L, 1e-6)
    plot_h = s * zspan
    h_dispo = h_max - PAD_T - BANDES_H - IND_H - AX_H
    if plot_h > h_dispo:
        s = h_dispo / zspan
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

    # data-plot-x0/x1 : bornes px du RECTANGLE du tracé (cale le survol de la coupe en 3D — B8)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="{_esc(coupe.get("titre",""))}" {_FONT} '
           f'data-plot-x0="{off_x:.1f}" data-plot-x1="{off_x+plot_w:.1f}" '
           f'style="background:{T["bg"]}">']
    # en-tête (C10) : titre · adresse · référence cadastrale (PLUS d'identifiant de scène) + sens de lecture
    out.append(f'<rect x="0" y="0" width="{width}" height="{HEAD}" fill="{T["head"]}"/>')
    out.append(f'<text x="{PAD_L}" y="17" font-size="13" font-weight="600" fill="{T["txt"]}">{_esc(coupe.get("titre",""))}</text>')
    sub = [x for x in (_esc(adresse) if adresse else "", _esc(idu) if idu else "") if x]
    sens = "voie vers parcelle" if (coupe.get("voie") and coupe["voie"].get("etablie")) else f'{coupe["label"]} vers {coupe["label"]}′'
    sub.append(_esc(sens))
    out.append(f'<text x="{PAD_L}" y="31" font-size="9" fill="{T["txt_dim"]}">{" · ".join(sub)}</text>')
    out.append(f'<rect x="{off_x:.1f}" y="{PAD_T}" width="{plot_w:.1f}" height="{plot_h:.1f}" '
               f'fill="{T["plot"]}" stroke="{T["grid"]}" stroke-width="0.6"/>')

    # graduations
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

    # TERRAIN : le RELEVÉ reste visible sous le bâti (C11) ; interruption SEULEMENT si les appuis
    # manquent (portion sans support). Le liseré vert au bas est RETIRÉ (C10).
    runs = _runs(profil)
    # portions sans appuis (sous un bâti dont la comparaison parallèle échoue) → interrompues
    sans_appui = [(b["d0"], b["d1"]) for b in batis if b.get("appuis") is False]
    for run in runs:
        if len(run) < 2:
            continue
        for s0, s1 in _soustraire((run[0]["d"], run[-1]["d"]), sans_appui):
            pts = [(p["d"], p["z"]) for p in run if s0 - 1e-6 <= p["d"] <= s1 + 1e-6]
            if len(pts) < 2:
                continue
            path = " ".join(f"{X(d):.1f},{Y(zz):.1f}" for d, zz in pts)
            base = f"{X(pts[-1][0]):.1f},{y_base:.1f} {X(pts[0][0]):.1f},{y_base:.1f}"
            out.append(f'<polygon points="{path} {base}" fill="{T["fill"]}" stroke="none"/>')
            out.append(f'<polyline points="{path}" fill="none" stroke="{T["terrain"]}" stroke-width="1.8"/>')
    for a, b in zip(runs, runs[1:]):          # profil reconstruit (tirets) sur lacune courte avec appuis
        gap = (a[-1]["d"], b[0]["d"])
        if gap[1] - gap[0] <= _PONT_RECONSTITUE_M:
            out.append(f'<line x1="{X(gap[0]):.1f}" y1="{Y(a[-1]["z"]):.1f}" x2="{X(gap[1]):.1f}" y2="{Y(b[0]["z"]):.1f}" '
                       f'stroke="{T["terrain"]}" stroke-width="1.4" stroke-dasharray="4 3"/>')

    # BÂTI : emprise au sol + RUPTURE du terrain à vérifier (repère distinct des cotes) ; aucun toit
    faitages = []
    rupture = False
    for b in batis:
        x0, x1 = X(b["d0"]), X(b["d1"])
        out.append(f'<line x1="{x0:.1f}" y1="{y_base:.1f}" x2="{x1:.1f}" y2="{y_base:.1f}" stroke="{T["bati"]}" stroke-width="3"/>')
        out.append(f'<line x1="{x0:.1f}" y1="{y_base-4:.1f}" x2="{x0:.1f}" y2="{y_base+4:.1f}" stroke="{T["bati"]}" stroke-width="1"/>')
        out.append(f'<line x1="{x1:.1f}" y1="{y_base-4:.1f}" x2="{x1:.1f}" y2="{y_base+4:.1f}" stroke="{T["bati"]}" stroke-width="1"/>')
        out.append(f'<text x="{(x0+x1)/2:.1f}" y="{y_base-7:.1f}" text-anchor="middle" font-size="7.5" fill="{T["bati"]}">emprise bâtie</text>')
        # repère de rupture (losange) au pied amont, distinct des cotes ordinaires
        zr = z_terrain(b["d0"])
        if zr is not None:
            yr = Y(zr)
            out.append(f'<path d="M{x0:.1f},{yr-4:.1f} l4,4 l-4,4 l-4,-4 z" fill="none" stroke="{T["lacune"]}" stroke-width="1.2"/>')
            rupture = True
        if b.get("attribution") == "bdtopo" and b.get("hauteur_m"):
            faitages.append(f"Hauteur du bâtiment (BD TOPO) · {_fmt(b['hauteur_m'],1)} m")

    # limites parcellaires (mêmes bornes que bandes/pente) — B6
    bornes = sorted({round(v, 2) for sp in (coupe.get("limites_parcelle_d") or []) for v in sp})
    for dl in bornes:
        out.append(f'<line x1="{X(dl):.1f}" y1="{PAD_T}" x2="{X(dl):.1f}" y2="{y_base:.1f}" stroke="{T["limite"]}" stroke-width="0.8" stroke-dasharray="5 3"/>')

    # pente max sur 5 m : DEUX bornes dessinées (B6)
    pm = (coupe.get("indicateurs") or {}).get("pente_max_5m") or {}
    if pm.get("disponible"):
        for dd in (pm["d0"], pm["d1"]):
            zt = z_terrain(dd)
            if zt is not None:
                out.append(f'<line x1="{X(dd):.1f}" y1="{Y(zt):.1f}" x2="{X(dd):.1f}" y2="{Y(zt)-14:.1f}" stroke="{T["lacune"]}" stroke-width="1.2"/>')
        zc = z_terrain((pm["d0"] + pm["d1"]) / 2)
        if zc is not None:
            out.append(f'<text x="{X((pm["d0"]+pm["d1"])/2):.1f}" y="{Y(zc)-17:.1f}" text-anchor="middle" font-size="7.5" fill="{T["lacune"]}">pente max 5 m</text>')

    # cotes aux points vérifiés, UNE par point, anti-collision (B9/B11)
    out.append(_cotes(coupe.get("cotes_points", {}).get("points", []), X, Y, T))

    # VOIE nommée LÀ OÙ la coupe la traverse (C10, coupe B)
    voie = coupe.get("voie") or {}
    if voie.get("etablie") and voie.get("nom") and voie.get("intersection_d") is not None:
        dv = voie["intersection_d"]
        if 0 <= dv <= L:
            zv = z_terrain(dv)
            yc0 = Y(zv) if zv is not None else y_base
            out.append(f'<circle cx="{X(dv):.1f}" cy="{yc0:.1f}" r="2.5" fill="none" stroke="{T["axe"]}" stroke-width="1.3"/>')
            out.append(f'<line x1="{X(dv):.1f}" y1="{yc0-3:.1f}" x2="{X(dv):.1f}" y2="{PAD_T+11:.1f}" stroke="{T["axe"]}" stroke-width="0.5" stroke-dasharray="2 2"/>')
            out.append(f'<text x="{X(dv):.1f}" y="{PAD_T+9:.1f}" text-anchor="middle" font-size="8" fill="{T["axe"]}">{_esc(voie["nom"])}</text>')

    # ÉCHELLE : barre graphique dans un emplacement réservé + datum (PDF : barre SEULE, pas de ratio — A2)
    out.append(_echelle(off_x, PAD_T - 24, L, s, T))

    # bandes de traversée cotées (mêmes bornes que les limites)
    yb0 = y_base + AX_H
    out.append(_bande(coupe.get("limites_parcelle_d") or [], yb0, X, "parcelle", T))
    yb1 = yb0 + 20
    zspans = coupe.get("zone_implantation_d") or []
    if zspans:
        out.append(_bande(zspans, yb1, X, "zone d'implantation", T, col=T["zone"]))
    else:                                              # bande d'implantation à états (B9)
        etat = "non traversée" if coupe.get("zone_presente") else "indisponible"
        out.append(f'<text x="8" y="{yb1+4:.1f}" font-size="8.5" fill="{T["txt_dim"]}">zone d\'implantation</text>')
        out.append(f'<text x="{off_x:.1f}" y="{yb1+4:.1f}" font-size="8.5" fill="{T["txt_dim"]}">— {etat}</text>')

    # indicateurs + mentions faîtage + rupture au pied du bâti (C11)
    out.append(_indicateurs(coupe, faitages, rupture, y_base + AX_H + BANDES_H, PAD_L, T))

    out.append("</svg>")
    return "".join(out)


def _cotes(points, X, Y, T):
    """Cotes (décimètre, virgule), UNE par point, sans collision : rangées alternées + TRAIT DE RAPPEL
    (C10) reliant le point à son étiquette quand elle est décalée."""
    items = sorted(points, key=lambda p: p["d"])
    rows = [[], []]       # occupation x par rangée (0 = au-dessus, 1 = en dessous)
    frag = []
    for p in items:
        if p["z"] is None:
            continue
        x, y = X(p["d"]), Y(p["z"])
        placed = None
        for r in (0, 1):
            if all(abs(x - xx) >= 24 for xx in rows[r]):
                rows[r].append(x); placed = r; break
        if placed is None:
            continue
        yy = (y - 9) if placed == 0 else (y + 13)
        frag.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{T["txt"]}"/>')
        frag.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{yy+(2 if placed else -7):.1f}" stroke="{T["txt_dim"]}" stroke-width="0.5"/>')  # trait de rappel
        frag.append(f'<text x="{x:.1f}" y="{yy:.1f}" text-anchor="middle" font-size="8" fill="{T["txt"]}">{_fmt(p["z"],1)} m</text>')
    return "".join(frag)


def _echelle(x, y, L, s, T):
    """Barre graphique SEULE (pas de ratio chiffré, même au PDF — A2) + datum une fois."""
    barre = _nice_step(L, 5)
    return "".join([
        f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+barre*s:.1f}" y2="{y:.1f}" stroke="{T["txt"]}" stroke-width="2"/>',
        f'<line x1="{x:.1f}" y1="{y-3:.1f}" x2="{x:.1f}" y2="{y+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>',
        f'<line x1="{x+barre*s:.1f}" y1="{y-3:.1f}" x2="{x+barre*s:.1f}" y2="{y+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>',
        f'<text x="{x+barre*s+6:.1f}" y="{y+3:.1f}" font-size="8.5" fill="{T["txt_dim"]}">{_fmt(barre)} m · Altitudes en m · IGN 1989 · H = V</text>'])


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


def _indicateurs(coupe, faitages, rupture, y0, pad_l, T):
    ind = coupe.get("indicateurs") or {}
    lignes = []
    for tr in ind.get("traversees") or []:
        lignes.append((T["txt"], f"traversée {_fmt(tr['d0'],1)}–{_fmt(tr['d1'],1)} m : pente {_fmt(tr.get('pente_pct'),1)} % ({_esc(tr.get('sens'))}) · amplitude {_fmt(tr['amplitude_m'],1)} m"))
    pm = ind.get("pente_max_5m") or {}
    if pm.get("disponible"):
        lignes.append((T["txt"], f"pente max sur 5 m (hors bâti ±1 m) : {_fmt(pm['pente_pct'],1)} % entre {_fmt(pm['d0'],1)} et {_fmt(pm['d1'],1)} m"))
    if ind.get("pente_acces_pct") is not None:
        lignes.append((T["txt"], f"pente sur l'axe, de la voie à la limite : {_fmt(ind['pente_acces_pct'],1)} %"))
    lignes += [(T["txt"], f) for f in faitages]
    if rupture:                                   # mention distincte (repère ◆, couleur de rupture) — C11
        lignes.append((T["lacune"], "◆ Au pied du bâti · rupture du terrain à vérifier"))
    frag = []
    for i, (col, ln) in enumerate(lignes[:6]):
        frag.append(f'<text x="{pad_l}" y="{y0+12+i*11:.1f}" font-size="8.5" fill="{col}">{_esc(ln)}</text>')
    return "".join(frag)


# ── Plan-clé (B8) : cadastre, axe + sens, bâti, voie à son intersection, nord ──────────────────────

def plan_cle_svg(scene, *, theme="sombre", width=380, height=320):
    T = _THEMES.get(theme, _THEMES["sombre"])
    cad = scene.get("contour_cadastral") or scene.get("contour_gabarit") or []
    if not cad:
        return None
    zone = scene.get("zone_implantation") or []
    batis = scene.get("batiments") or []
    axes = scene.get("axes_plan") or {}
    voie_pts = [c["voie"]["point_local"] for c in (scene.get("coupes") or [])
                if c.get("voie") and c["voie"].get("point_local")]

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
    def Y(y): return height - offy - (y - miny) * s

    def path(poly):
        d = "M" + "L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in poly["ext"]) + "Z"
        for tr in poly.get("trous", []):
            d += "M" + "L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in tr) + "Z"
        return d

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="Plan-clé des coupes" {_FONT} style="background:{T["bg"]}">']
    for poly in zone:
        out.append(f'<path d="{path(poly)}" fill="{T["zone"]}" fill-opacity="0.4" stroke="{T["zone"]}" stroke-width="1" fill-rule="evenodd"/>')
    for poly in batis:
        for sub in poly.get("empreinte") or []:
            out.append(f'<path d="{path(sub)}" fill="{T["bati"]}" fill-opacity="0.45" stroke="{T["bati"]}" stroke-width="0.6" fill-rule="evenodd"/>')
    for poly in cad:
        out.append(f'<path d="{path(poly)}" fill="none" stroke="{T["limite"]}" stroke-width="1.4" stroke-dasharray="4 2" fill-rule="evenodd"/>')
    for label, a in axes.items():
        x0, y0, x1, y1 = X(a["p0"][0]), Y(a["p0"][1]), X(a["p1"][0]), Y(a["p1"][1])
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{T["axe"]}" stroke-width="2"/>')
        out.append(_fleche(x0 + (x1 - x0) * 0.72, y0 + (y1 - y0) * 0.72, x1, y1, T["axe"]))
        out.append(f'<text x="{x0:.1f}" y="{y0-5:.1f}" font-size="10" font-weight="600" fill="{T["axe"]}">{label}</text>')
        out.append(f'<text x="{x1:.1f}" y="{y1-5:.1f}" font-size="10" font-weight="600" fill="{T["axe"]}">{label}′</text>')
    for p in voie_pts:                                 # voie à son intersection (B8)
        out.append(f'<circle cx="{X(p[0]):.1f}" cy="{Y(p[1]):.1f}" r="3.5" fill="none" stroke="{T["axe"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{X(p[0])+5:.1f}" y="{Y(p[1])+3:.1f}" font-size="8" fill="{T["axe"]}">voie</text>')
    nx, ny = width - 22, 30
    out.append(_fleche(nx, ny + 16, nx, ny - 8, T["txt"]))
    out.append(f'<text x="{nx:.1f}" y="{ny-11:.1f}" text-anchor="middle" font-size="9" font-weight="600" fill="{T["txt"]}">N</text>')
    out.append(f'<text x="{PAD}" y="16" font-size="10" fill="{T["txt_dim"]}">Plan-clé — cadastre, axes, sens, voie, nord</text>')
    out.append("</svg>")
    return "".join(out)
