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
               "sous_bati": "#f2b35e", "head": "#1a1f27"},
    "clair": {"bg": "#ffffff", "plot": "#ffffff", "terrain": "#374151", "fill": "#eef1f4",
              "limite": "#111827", "zone": "#2c9f7c", "bati": "#6b7280", "txt": "#1f2937",
              "txt_dim": "#6b7280", "grid": "#dadfe4", "lacune": "#c0392b", "axe": "#9a6a12",
              "sous_bati": "#b26a00", "head": "#f3f4f6"},
}
_FONT = 'font-family="Inter, Helvetica, Arial, sans-serif"'
_PONT_RECONSTITUE_M = 3.0
# GABARIT-3D-3 (LOT 1) — le losange « rupture à vérifier » ne s'affiche QUE si le terrain varie d'au moins
# ce seuil sur le segment du bâti (d0 → d1+3 m). En dessous : rien (ni losange, ni libellé, ni ligne de
# légende). Une pente douce près d'un bâti n'est pas une rupture à signaler.
_RUPTURE_SEUIL_M = 1.5
# GABARIT-3D-3 (correction LOT 2) — ÉLÉMENT COUVERT pris pour du sol par le LiDAR (varangue/auvent/abri) :
# SOUS l'emprise bâtie, là où le sol dépasse de ≥ ce seuil le sol des façades (appuis extérieurs interpolés),
# le profil n'est PAS dessiné comme mesuré — trait distinct « sol non mesuré sous un élément couvert », sans
# cote. Rien d'inventé ailleurs : le reste du sol LiDAR 0,5 m est dessiné tel quel.
_COUVERT_SEUIL_M = 1.5


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


def coupe_svg(coupe, *, theme="sombre", width=960, h_max=520, adresse=None, idu=None, detail=False, header=True):
    """SVG d'une coupe. APERÇU (detail=False) : profil, limites, emprise, rupture, 2–3 cotes — ce qui
    reste lisible. DÉTAIL (detail=True) : toutes les cotes, bandes, les DEUX pentes de la coupe B.
    header=False : titre + datum RETIRÉS du SVG (la visionneuse les met dans un bandeau HTML, à côté du
    bouton « Agrandir », pour qu'il ne recouvre plus le datum). None si le profil n'a aucun point valide."""
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

    # 3 bis : les deux bandes (parcelle, zone) + la légende figurent dans l'APERÇU COMME dans le DÉTAIL
    # (mêmes bornes) ; la ligne d'indicateurs reste réservée au détail.
    HEAD = 22 if header else 15   # sans titre/datum (header=False), on garde une voie d'étiquettes au-dessus du tracé
    PAD_L, PAD_R, PAD_T = 58, 16, HEAD + 8
    BANDES_H, AX_H = 54, 20       # longueurs des bandes posées SOUS chaque bande (leur propre ligne)
    IND_H = 16 if detail else 0
    CIEL = 28                     # ciel RÉSERVÉ au-dessus de la crête pour les étiquettes (jamais sur la courbe)
    plot_w = width - PAD_L - PAD_R
    s = min(plot_w / max(L, 1e-6), (h_max - PAD_T - CIEL - BANDES_H - IND_H - AX_H) / zspan)   # H = V, JAMAIS tronqué
    plot_w = s * L
    plot_h = CIEL + s * zspan     # ciel + relief
    off_x = PAD_L + (width - PAD_L - PAD_R - plot_w) / 2
    y_base = PAD_T + plot_h
    height = int(y_base + AX_H + BANDES_H + IND_H)

    def X(d): return off_x + d * s
    def Y(z): return PAD_T + CIEL + (zmax - z) * s      # crête (zmax) à PAD_T+CIEL, zmin à y_base

    def z_terrain(d):
        for run in _runs(profil):
            if run[0]["d"] - 1e-6 <= d <= run[-1]["d"] + 1e-6:
                for a, b in zip(run, run[1:]):
                    if a["d"] <= d <= b["d"] and b["d"] > a["d"]:
                        t = (d - a["d"]) / (b["d"] - a["d"])
                        return a["z"] + t * (b["z"] - a["z"])
        return None

    def sky_top(xc, half):
        """Y du TERRAIN le plus haut (min Y) dans la bande [xc−half, xc+half] → plafond pour poser une
        étiquette AU-DESSUS de la courbe (jamais dessus). Échantillonne la bande (bords compris) ET les
        points du profil : un segment raide qui entre par un bord compte aussi."""
        ys = [Y(p["z"]) for p in profil if p["z"] is not None and xc - half <= X(p["d"]) <= xc + half]
        for k in range(9):
            zk = z_terrain((xc - half + 2 * half * k / 8 - off_x) / s)
            if zk is not None:
                ys.append(Y(zk))
        return min(ys) if ys else PAD_T + CIEL

    # data-plot-x0/x1 : bornes px du RECTANGLE du tracé (cale le survol de la coupe en 3D — B8)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
           f'height="{height}" role="img" aria-label="{_esc(coupe.get("titre",""))}" {_FONT} '
           f'data-plot-x0="{off_x:.1f}" data-plot-x1="{off_x+plot_w:.1f}" '
           f'style="background:{T["bg"]}">']
    # en-tête UNE LIGNE (2 quater) : titre à gauche, datum à droite — RETIRÉ si header=False (bandeau HTML)
    if header:
        out.append(f'<text x="{PAD_L}" y="15" font-size="12" font-weight="600" fill="{T["txt"]}">{_esc(coupe.get("titre",""))}</text>')
        out.append(f'<text x="{width-PAD_R}" y="15" text-anchor="end" font-size="9" fill="{T["txt_dim"]}">Altitudes en m · IGN 1989 · H = V</text>')
    out.append(f'<rect x="{off_x:.1f}" y="{PAD_T}" width="{plot_w:.1f}" height="{plot_h:.1f}" '
               f'fill="{T["plot"]}" stroke="{T["grid"]}" stroke-width="0.6"/>')

    # graduations
    xs = _nice_step(L); zstep = _nice_step(zspan)
    d = 0.0
    while d <= L + 1e-6:
        out.append(f'<line x1="{X(d):.1f}" y1="{PAD_T}" x2="{X(d):.1f}" y2="{y_base:.1f}" stroke="{T["grid"]}" stroke-width="0.4"/>')
        out.append(f'<text x="{X(d):.1f}" y="{y_base+13:.1f}" text-anchor="middle" font-size="9.5" fill="{T["txt_dim"]}">{_fmt(d)}</text>')
        d += xs
    z = zmin - (zmin % zstep)
    while z <= zmax + 1e-6:
        if z >= zmin - 1e-6:
            out.append(f'<line x1="{off_x:.1f}" y1="{Y(z):.1f}" x2="{off_x+plot_w:.1f}" y2="{Y(z):.1f}" stroke="{T["grid"]}" stroke-width="0.4"/>')
            out.append(f'<text x="{off_x-6:.1f}" y="{Y(z)+3:.1f}" text-anchor="end" font-size="9" fill="{T["txt_dim"]}">{_fmt(z)}</text>')
        z += zstep

    # ÉLÉMENT COUVERT (varangue/auvent pris pour du sol SOUS le bâti) : une BOSSE locale ≥ _COUVERT_SEUIL_M
    # au-dessus des DEUX sols voisins. On ne la DESSINE PAS (ni dans le tracé principal, ni dans le profil sous
    # le bâti) : un trait pointillé DROIT relie les deux sols voisins, et un seul libellé l'explique. Pas de
    # losange de rupture dessus. Détecté AVANT le tracé pour pouvoir retirer la bosse du relevé principal.
    couvert_present = False
    couvert_anchor = None
    batis_couverts = {}            # index bâti → (d_a, d_b) couvert : pas de losange de rupture sur cette portion
    couvert_spans = []             # (d, d) à RETIRER du tracé principal (de sol voisin à sol voisin)
    couvert_traits = []            # (pL, pR) trait DROIT reliant les deux sols voisins
    sous_bati_runs = []            # runs de sol MESURÉ sous le bâti → profil sous le bâti (pointillé orange)
    _GND = 0.5                     # point à moins de 0,5 m au-dessus du sol voisin = « au sol »
    for bi, b in enumerate(batis):
        d0, d1 = b["d0"], b["d1"]
        pb = [(p["d"], p["z"]) for p in profil if d0 - 1e-6 <= p["d"] <= d1 + 1e-6 and p["z"] is not None]
        if len(pb) < 2:
            continue
        av = [p["z"] for p in profil if p["z"] is not None and d0 - 10.0 <= p["d"] < d0]
        ap = [p["z"] for p in profil if p["z"] is not None and d1 < p["d"] <= d1 + 10.0]
        refs = ([min(av)] if av else []) + ([min(ap)] if ap else [])
        ref = max(refs) if refs else min(z for _, z in pb)
        # fenêtre élargie (± 3 m) : une varangue dépasse souvent l'emprise (rampe + dalle + bord de dalle). On
        # découpe les RÉGIONS qui QUITTENT le sol voisin (z > ref + 0,5) ; une région dont le PIC dépasse de
        # ≥ 1,5 m est un élément couvert → trait DROIT du dernier point AU SOL avant au premier point AU SOL après.
        win = [(p["d"], p["z"]) for p in profil if d0 - 3.0 <= p["d"] <= d1 + 3.0 and p["z"] is not None]
        above = [z > ref + _GND for _, z in win]
        couvert_sous = []
        i = 0
        while i < len(win):
            if not above[i]:
                i += 1; continue
            j = i
            while j + 1 < len(win) and above[j + 1]:
                j += 1
            region = win[i:j + 1]
            if max(z for _, z in region) - ref >= _COUVERT_SEUIL_M:   # élément couvert (varangue)
                d_a, d_b = region[0][0], region[-1][0]
                before = [p for p in profil if p["z"] is not None and p["d"] < d_a - 1e-6]
                after = [p for p in profil if p["z"] is not None and p["d"] > d_b + 1e-6]
                pL = before[-1] if before else {"d": d_a, "z": ref}
                pR = after[0] if after else {"d": d_b, "z": ref}
                couvert_present = True
                couvert_spans.append((pL["d"], pR["d"]))
                couvert_sous.append((pL["d"], pR["d"]))
                couvert_traits.append((pL, pR))
                prev = batis_couverts.get(bi)
                batis_couverts[bi] = (min(prev[0], d_a), max(prev[1], d_b)) if prev else (d_a, d_b)
                if couvert_anchor is None:
                    couvert_anchor = ((X(pL["d"]) + X(pR["d"])) / 2, (Y(pL["z"]) + Y(pR["z"])) / 2)
            i = j + 1
        # sol MESURÉ sous le bâti = emprise hors des portions couvertes → pointillé orange
        for s0, s1 in _soustraire((pb[0][0], pb[-1][0]), couvert_sous):
            run = [(d, z) for d, z in pb if s0 - 1e-6 <= d <= s1 + 1e-6]
            if len(run) >= 2:
                sous_bati_runs.append(run)

    # TERRAIN : le RELEVÉ reste visible sous le bâti (C11) ; interruption si les appuis manquent OU si c'est un
    # élément couvert (la bosse n'est pas tracée). Le liseré vert au bas est RETIRÉ (C10).
    runs = _runs(profil)
    sans_appui = [(b["d0"], b["d1"]) for b in batis if b.get("appuis") is False]
    coupe_hors = sans_appui + couvert_spans
    for run in runs:
        if len(run) < 2:
            continue
        for s0, s1 in _soustraire((run[0]["d"], run[-1]["d"]), coupe_hors):
            pts = [(p["d"], p["z"]) for p in run if s0 - 1e-6 <= p["d"] <= s1 + 1e-6]
            if len(pts) < 2:
                continue
            path = " ".join(f"{X(d):.1f},{Y(zz):.1f}" for d, zz in pts)
            base = f"{X(pts[-1][0]):.1f},{y_base:.1f} {X(pts[0][0]):.1f},{y_base:.1f}"
            out.append(f'<polygon points="{path} {base}" fill="{T["fill"]}" stroke="none"/>')
            out.append(f'<polyline points="{path}" fill="none" stroke="{T["terrain"]}" stroke-width="1.8"/>')
    for a, b in zip(runs, runs[1:]):          # profil reconstruit (tirets) sur lacune courte avec appuis
        gap = (a[-1]["d"], b[0]["d"])
        if gap[1] - gap[0] <= _PONT_RECONSTITUE_M and not any(s0 <= gap[0] and gap[1] <= s1 for s0, s1 in couvert_spans):
            out.append(f'<line x1="{X(gap[0]):.1f}" y1="{Y(a[-1]["z"]):.1f}" x2="{X(gap[1]):.1f}" y2="{Y(b[0]["z"]):.1f}" '
                       f'stroke="{T["terrain"]}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    # élément couvert : trait DROIT (pointillé) entre les deux sols voisins, à la place de la bosse
    for pL, pR in couvert_traits:
        out.append(f'<line x1="{X(pL["d"]):.1f}" y1="{Y(pL["z"]):.1f}" x2="{X(pR["d"]):.1f}" y2="{Y(pR["z"]):.1f}" '
                   f'stroke="{T["lacune"]}" stroke-width="1.6" stroke-dasharray="1 3"/>')
    # profil SOUS le bâti là où c'est du sol MESURÉ (interpolé par l'IGN) : pointillé orange
    for run in sous_bati_runs:
        pts = " ".join(f"{X(d):.1f},{Y(zz):.1f}" for d, zz in run)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{T["sous_bati"]}" stroke-width="2.2" stroke-dasharray="3 2.5"/>')

    # BÂTI : emprise au sol + RUPTURE du terrain à vérifier (repère distinct des cotes) ; aucun toit
    faitages = []
    rupture = False
    prot = []   # A2 — libellés à FOND OPAQUE émis EN DERNIER (aucun trait au travers) : (svg,)
    for bi, b in enumerate(batis):
        x0, x1 = X(b["d0"]), X(b["d1"])
        out.append(f'<line x1="{x0:.1f}" y1="{y_base:.1f}" x2="{x1:.1f}" y2="{y_base:.1f}" stroke="{T["bati"]}" stroke-width="3"/>')
        out.append(f'<line x1="{x0:.1f}" y1="{y_base-4:.1f}" x2="{x0:.1f}" y2="{y_base+4:.1f}" stroke="{T["bati"]}" stroke-width="1"/>')
        out.append(f'<line x1="{x1:.1f}" y1="{y_base-4:.1f}" x2="{x1:.1f}" y2="{y_base+4:.1f}" stroke="{T["bati"]}" stroke-width="1"/>')
        # « emprise bâtie » : plus d'étiquette SUR la courbe → la barre grise est expliquée dans la LÉGENDE.
        # repère de rupture (losange) sur la PORTION CONCERNÉE = plus forte pente autour du bâti (pas le 1ᵉʳ pied).
        # LOT 1 — on ne le pose QUE si le terrain varie d'au moins _RUPTURE_SEUIL_M sur le segment du bâti.
        # Correction : si la rupture tombe sur un ÉLÉMENT COUVERT, pas de losange — elle est déjà expliquée
        # par « sol non mesuré sous un élément couvert » (un seul libellé, pas de doublon qui se chevauche).
        d1c = min(b["d1"] + 3.0, L)
        seg_zs = [p["z"] for p in profil if b["d0"] - 1e-6 <= p["d"] <= d1c + 1e-6 and p["z"] is not None]
        ecart_m = (max(seg_zs) - min(seg_zs)) if seg_zs else 0.0
        drb = _rupture_d(profil, b["d0"], d1c)
        zr = z_terrain(drb) if drb is not None else None
        cs = batis_couverts.get(bi)
        sur_couvert = cs is not None and drb is not None and cs[0] - 1.5 <= drb <= cs[1] + 1.5
        if zr is not None and ecart_m >= _RUPTURE_SEUIL_M and not sur_couvert:
            out.append(f'<path d="M{X(drb):.1f},{Y(zr)-4:.1f} l4,4 l-4,4 l-4,-4 z" fill="none" stroke="{T["lacune"]}" stroke-width="1.4"/>')
            out.append(f'<circle cx="{X(drb):.1f}" cy="{Y(zr):.1f}" r="1.6" fill="{T["lacune"]}"/>')
            rupture = True
            # « Rupture du terrain à vérifier » posée dans la VOIE D'ÉTIQUETTES au-dessus du tracé (JAMAIS sur la
            # courbe) + trait de rappel jusqu'au losange ; fond opaque (aucun trait au travers).
            a_end = X(drb) > off_x + plot_w / 2                 # losange à droite → texte vers la gauche
            out.append(f'<line x1="{X(drb):.1f}" y1="{Y(zr)-5:.1f}" x2="{X(drb):.1f}" y2="{PAD_T:.1f}" stroke="{T["lacune"]}" stroke-width="0.5" stroke-dasharray="2 2"/>')
            prot.append(_label_box(X(drb) + (-6 if a_end else 6), PAD_T - 4, "Rupture du terrain à vérifier",
                                   T["lacune"], T["bg"], anchor=("end" if a_end else "start")))
        if b.get("attribution") == "bdtopo" and b.get("hauteur_m"):
            faitages.append(f"Hauteur du bâtiment (BD TOPO) · {_fmt(b['hauteur_m'],1)} m")

    # limites parcellaires (mêmes bornes que bandes/pente) — B6
    bornes = sorted({round(v, 2) for sp in (coupe.get("limites_parcelle_d") or []) for v in sp})
    for dl in bornes:
        out.append(f'<line x1="{X(dl):.1f}" y1="{PAD_T}" x2="{X(dl):.1f}" y2="{y_base:.1f}" stroke="{T["limite"]}" stroke-width="0.8" stroke-dasharray="5 3"/>')

    # pente max sur 5 m : DEUX bornes dessinées (B6)
    pente_obstacle = []            # BOÎTES (x0,x1,y0,y1) du libellé pente → les cotes les ÉVITENT en 2D (anti-chevauchement)
    pm = (coupe.get("indicateurs") or {}).get("pente_max_5m") or {}
    if pm.get("disponible"):
        for dd in (pm["d0"], pm["d1"]):
            zt = z_terrain(dd)
            if zt is not None:
                out.append(f'<line x1="{X(dd):.1f}" y1="{Y(zt):.1f}" x2="{X(dd):.1f}" y2="{Y(zt)-14:.1f}" stroke="{T["lacune"]}" stroke-width="1.2"/>')
        zc = z_terrain((pm["d0"] + pm["d1"]) / 2)
        if zc is not None:
            # VALEUR MESURÉE : « pente max N % sur 5 m » (se lit comme une pente, pas des mètres) — fond opaque,
            # posée AU-DESSUS du terrain LOCAL (jamais sur la courbe, pt 4).
            xcp = X((pm["d0"] + pm["d1"]) / 2)
            txt = f"pente max {_fmt(pm.get('pente_pct'), 0)} % sur 5 m" if pm.get("pente_pct") is not None else "pente max sur 5 m"
            halfp = max(len(txt) * 9 * 0.56 / 2 + 3, 8.0)
            ypm = max(sky_top(xcp, halfp) - 6, PAD_T + 9)
            prot.append(_label_box(xcp, ypm, txt, T["lacune"], T["plot"]))
            pente_obstacle.append((xcp - halfp, xcp + halfp, ypm - 9, ypm + 4))

    # élément couvert détecté sous le bâti : UN SEUL libellé dans le ciel + rappel au trait droit (aucune cote).
    if couvert_present and couvert_anchor is not None:
        xA, yA = couvert_anchor
        a_end = xA > off_x + plot_w / 2
        out.append(f'<line x1="{xA:.1f}" y1="{yA-4:.1f}" x2="{xA:.1f}" y2="{PAD_T+9:.1f}" stroke="{T["lacune"]}" stroke-width="0.5" stroke-dasharray="1 3"/>')
        prot.append(_label_box(xA + (-6 if a_end else 6), PAD_T + 4, "sol non mesuré sous un élément couvert",
                               T["lacune"], T["bg"], anchor=("end" if a_end else "start")))

    # cotes : APERÇU = voie + CHAQUE entrée de limite + haut/bas ; DÉTAIL = toutes. Dans le ciel, fond opaque.
    # AUCUNE cote sur un élément couvert (le « haut » peut tomber sur la dalle d'une varangue → on l'écarte).
    pts = coupe.get("cotes_points", {}).get("points", [])
    if not detail:
        pts = [p for p in pts if p.get("role") in ("voie", "limite", "haut", "bas")]
    pts = [p for p in pts if not any(s0 - 0.5 <= p["d"] <= s1 + 0.5 for s0, s1 in couvert_spans)]
    out.append(_cotes(pts, X, Y, T, PAD_T, prot, sky_top, pente_obstacle))

    # VOIE nommée LÀ OÙ la coupe la traverse (C10, coupe B)
    voie = coupe.get("voie") or {}
    if voie.get("etablie") and voie.get("nom") and voie.get("intersection_d") is not None:
        dv = voie["intersection_d"]
        if 0 <= dv <= L:
            zv = z_terrain(dv)
            yc0 = Y(zv) if zv is not None else y_base
            out.append(f'<circle cx="{X(dv):.1f}" cy="{yc0:.1f}" r="2.5" fill="none" stroke="{T["axe"]}" stroke-width="1.3"/>')
            # repère vers le HAUT, s'arrête AU bord du tracé ; le nom est posé AU-DESSUS du cadre (hors profil)
            out.append(f'<line x1="{X(dv):.1f}" y1="{yc0-3:.1f}" x2="{X(dv):.1f}" y2="{PAD_T:.1f}" stroke="{T["axe"]}" stroke-width="0.5" stroke-dasharray="2 2"/>')
            prot.append(_label_box(X(dv), PAD_T - 3, voie["nom"], T["axe"], T["bg"]))

    # ÉCHELLE : barre dans un COIN du tracé (2 quater), barre seule
    out.append(_echelle(off_x + 8, y_base - 7, L, s, T))

    # BANDES (parcelle blanc, zone vert) : APERÇU ET DÉTAIL, MÊMES BORNES. Longueurs SOUS chaque bande
    # (leur propre ligne, +11) → jamais sur les graduations. Puis légende de la coupe.
    yb0 = y_base + AX_H
    out.append(_bande(coupe.get("limites_parcelle_d") or [], yb0, X, "parcelle", T))
    yb1 = yb0 + 21
    zspans = coupe.get("zone_implantation_d") or []
    if zspans:
        out.append(_bande(zspans, yb1, X, "zone d'implantation", T, col=T["zone"]))
    else:
        etat = "non traversée" if coupe.get("zone_presente") else "indisponible"
        out.append(f'<text x="8" y="{yb1+3:.1f}" font-size="9" fill="{T["txt_dim"]}">zone d\'implantation — {etat}</text>')
    out.append(_legende_coupe(yb1 + 19, off_x, T, rupture, bool(batis), couvert_present))
    # indicateurs (deux pentes, pente max 5 m, accès, bâti) : DÉTAIL seulement
    if detail:
        out.append(_indicateurs(coupe, faitages, rupture, y_base + AX_H + BANDES_H, PAD_L, width - PAD_R, T))

    # A2 — libellés à fond opaque EN DERNIER : aucun trait ne les traverse à l'écran
    out.extend(prot)
    out.append("</svg>")
    return "".join(out)


def _label_box(cx, y, text, color, bg, anchor="middle", fs=9):
    """A2 — libellé avec FOND OPAQUE (local), émis EN DERNIER : aucun trait (grille, limite, repère) ne
    le traverse à l'écran. Largeur estimée au glyphe pour cadrer le fond."""
    w = max(len(text) * fs * 0.56, 8.0)
    if anchor == "middle":
        rx = cx - w / 2 - 3
    elif anchor == "end":
        rx = cx - w - 3
    else:
        rx = cx - 3
    return (f'<rect x="{rx:.1f}" y="{y-fs:.1f}" width="{w+6:.1f}" height="{fs+4:.1f}" rx="2" '
            f'fill="{bg}" opacity="0.92"/>'
            f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{fs}" fill="{color}">{_esc(text)}</text>')


def _cotes(points, X, Y, T, ytop, prot, sky_top, obstacles=()):
    """Cotes (décimètre, virgule) posées AU-DESSUS du terrain LOCAL (jamais sur la courbe), à FOND OPAQUE
    (aucun trait vertical au travers) + trait de rappel jusqu'au bord de l'étiquette (pt 3/4). Les étiquettes
    partent dans `prot` → émises EN DERNIER ; seuls les points et traits de rappel reviennent pour le corps.
    `obstacles` = BOÎTES (x0,x1,y0,y1) déjà posées (ex. « pente max ») : une cote qui chevaucherait une boîte
    (en 2D, pas seulement en x) monte d'une rangée → plus de chevauchement « pente max » / cote (finition 4a)."""
    items = sorted((p for p in points if p["z"] is not None), key=lambda p: p["d"])
    rows = [[], [], [], []]   # rangées empilées vers le haut (occupation x) ; une 4e rangée de secours
    frag = []

    def chevauche(x0, x1, y0, y1):
        return any(not (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1)
                   for bx0, bx1, by0, by1 in obstacles)

    for p in items:
        x, y = X(p["d"]), Y(p["z"])
        half = len(f'{_fmt(p["z"],1)} m') * 9 * 0.56 / 2 + 3
        placed, yy = None, None
        for r in range(len(rows)):
            if not all(abs(x - xx) >= 2 * half + 4 for xx in rows[r]):
                continue
            cand = max(sky_top(x, half) - 6 - r * 15, ytop + 9)   # empilé vers le haut (pas de 15 > hauteur de boîte 13 → 2 px d'écart)
            if chevauche(x - half - 3, x + half + 3, cand - 9, cand + 4):   # boîte de la cote vs boîtes obstacles
                continue
            rows[r].append(x); placed, yy = r, cand; break
        if placed is None:
            continue
        frag.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{T["txt"]}"/>')
        frag.append(f'<line x1="{x:.1f}" y1="{y-2:.1f}" x2="{x:.1f}" y2="{yy+4:.1f}" stroke="{T["txt_dim"]}" stroke-width="0.5"/>')  # rappel jusqu'au bord de l'étiquette
        prot.append(_label_box(x, yy, f'{_fmt(p["z"],1)} m', T["txt"], T["plot"]))
    return "".join(frag)


def _echelle(x, y, L, s, T):
    """Barre graphique SEULE (pas de ratio), dans un coin du tracé."""
    barre = _nice_step(L, 5)
    return "".join([
        f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+barre*s:.1f}" y2="{y:.1f}" stroke="{T["txt"]}" stroke-width="2"/>',
        f'<line x1="{x:.1f}" y1="{y-3:.1f}" x2="{x:.1f}" y2="{y+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>',
        f'<line x1="{x+barre*s:.1f}" y1="{y-3:.1f}" x2="{x+barre*s:.1f}" y2="{y+3:.1f}" stroke="{T["txt"]}" stroke-width="1"/>',
        f'<text x="{x+barre*s+5:.1f}" y="{y+3:.1f}" font-size="9" fill="{T["txt_dim"]}">{_fmt(barre)} m</text>'])


def _bande(spans, y, X, label, T, col=None):
    """Bande de traversée : la LIGNE à `y` (ticks aux bornes) ; les LONGUEURS sont posées SOUS la bande
    (`y+11`, leur propre ligne) → elles ne croisent jamais les graduations de l'axe de distance (3 ter)."""
    col = col or T["limite"]
    key = "zone" if "zone" in label else "parcelle"
    frag = [f'<text x="8" y="{y+4:.1f}" font-size="9" fill="{T["txt_dim"]}">{_esc(label)}</text>']
    for d0, d1 in spans:
        x0, x1 = X(d0), X(d1)
        # bornes (d) portées en attribut → comparables entre aperçu et détail (3 bis)
        frag.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2.5" '
                    f'data-band="{key}" data-d0="{d0:.2f}" data-d1="{d1:.2f}"/>')
        frag.append(f'<line x1="{x0:.1f}" y1="{y-3:.1f}" x2="{x0:.1f}" y2="{y+3:.1f}" stroke="{col}" stroke-width="1"/>')
        frag.append(f'<line x1="{x1:.1f}" y1="{y-3:.1f}" x2="{x1:.1f}" y2="{y+3:.1f}" stroke="{col}" stroke-width="1"/>')
        frag.append(f'<text x="{(x0+x1)/2:.1f}" y="{y+11:.1f}" text-anchor="middle" font-size="9" fill="{T["txt_dim"]}">{_fmt(d1-d0,1)} m</text>')
    return "".join(frag)


def _legende_coupe(y, x, T, rupture, has_bati, couvert=False):
    """Légende de la COUPE (aperçu et détail) : terrain, profil sous le bâti (trait différent), rupture,
    sol non mesuré sous un élément couvert."""
    frag, cx = [], x
    def ent(label, draw, w):
        nonlocal cx
        frag.append(draw(cx))
        frag.append(f'<text x="{cx+22:.1f}" y="{y+3:.1f}" font-size="9" fill="{T["txt_dim"]}">{_esc(label)}</text>')
        cx += 22 + len(label) * 5.2 + 16
    ent("terrain", lambda c: f'<line x1="{c:.1f}" y1="{y:.1f}" x2="{c+16:.1f}" y2="{y:.1f}" stroke="{T["terrain"]}" stroke-width="2"/>', 16)
    if has_bati:
        # barre grise = emprise bâtie (plus d'étiquette sur la courbe, pt 4) ; et profil sous le bâti INTERPOLÉ
        # par l'IGN (MNT bare-earth sans retour sol).
        ent("emprise bâtie", lambda c: f'<line x1="{c:.1f}" y1="{y:.1f}" x2="{c+16:.1f}" y2="{y:.1f}" stroke="{T["bati"]}" stroke-width="3"/>', 16)
        ent("profil sous le bâti (interpolé)", lambda c: f'<line x1="{c:.1f}" y1="{y:.1f}" x2="{c+16:.1f}" y2="{y:.1f}" stroke="{T["sous_bati"]}" stroke-width="2.2" stroke-dasharray="3 2.5"/>', 16)
    if couvert:
        ent("sol non mesuré sous un élément couvert", lambda c: f'<line x1="{c:.1f}" y1="{y:.1f}" x2="{c+16:.1f}" y2="{y:.1f}" stroke="{T["lacune"]}" stroke-width="1.6" stroke-dasharray="1 3"/>', 16)
    if rupture:
        ent("rupture du terrain à vérifier", lambda c: f'<path d="M{c+8:.1f},{y-4:.1f} l4,4 l-4,4 l-4,-4 z" fill="none" stroke="{T["lacune"]}" stroke-width="1.4"/>', 16)
    return "".join(frag)


def palier_max_m(profil, bati_spans=()) -> float:
    """GABARIT-3D-3 (contrôle anti-escalier) — longueur du plus long PALIER PLAT (points consécutifs à
    l'altitude de départ, à ±1 cm) HORS emprise bâtie. Un relief naturel fin (LiDAR HD 0,5 m) ne fait pas
    de longs paliers plats ; une maille grossière RÉÉCHANTILLONNÉE (ex. RGE ALTI 5 m servi en 0,5 m) en
    fait. Un palier ≥ ~2 m signale une donnée « en escalier ». (Sur une pente douce, le 3ᵉ point s'écarte
    de >1 cm du départ → le palier reste court : pas de faux positif.)"""
    seg = [p for p in profil if p["z"] is not None
           and not any(a - 1e-6 <= p["d"] <= b + 1e-6 for a, b in bati_spans)]
    best = 0.0
    i = 0
    while i < len(seg):
        z0, j = seg[i]["z"], i
        while j + 1 < len(seg) and abs(seg[j + 1]["z"] - z0) <= 0.01:
            j += 1
        best = max(best, seg[j]["d"] - seg[i]["d"])
        i = j + 1
    return best


def _rupture_d(profil, d0, d1):
    """Distance de la PORTION la plus raide dans [d0,d1] (= la rupture près du bâti, pas le 1ᵉʳ pied)."""
    seg = [p for p in profil if d0 - 1e-6 <= p["d"] <= d1 + 1e-6 and p["z"] is not None]
    best, bd = -1.0, None
    for a, b in zip(seg, seg[1:]):
        dd = b["d"] - a["d"]
        if dd <= 0:
            continue
        sl = abs(b["z"] - a["z"]) / dd
        if sl > best:
            best, bd = sl, (a["d"] + b["d"]) / 2
    return bd if bd is not None else (d0 + d1) / 2


def _indicateurs(coupe, faitages, rupture, y0, pad_l, right_x, T):
    """DÉTAIL : chaque TRAVERSÉE avec sa pente (les DEUX pentes de la coupe B) · pente max 5 m ·
    « de la voie à la limite sur l'axe » · bâti ; mention rupture distincte à droite."""
    ind = coupe.get("indicateurs") or {}
    bits = []
    for tr in ind.get("traversees") or []:
        if tr.get("pente_pct") is not None:
            sgn = "+" if tr["pente_pct"] > 0 else ""  # montée explicite (+2,5 %) vs descente (−23,8 %)
            bits.append(f"traversée {_fmt(tr['d0'],1)}–{_fmt(tr['d1'],1)} m : {sgn}{_fmt(tr['pente_pct'],1)} %")
    pm = ind.get("pente_max_5m") or {}
    if pm.get("disponible"):
        bits.append(f"pente max 5 m {_fmt(pm['pente_pct'],1)} %")
    if ind.get("pente_acces_pct") is not None:
        bits.append(f"de la voie à la limite sur l'axe : {_fmt(ind['pente_acces_pct'],1)} %")
    for f in faitages:
        bits.append(f.replace("Hauteur du bâtiment (BD TOPO) · ", "bâti "))
    # rupture : expliquée à côté du losange + en légende (3 bis) → plus de mention répétée ici
    return f'<text x="{pad_l}" y="{y0+11:.1f}" font-size="9" fill="{T["txt"]}">{_esc(" · ".join(bits))}</text>'


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
    # lettres d'axe (A A′ B B′) : chacune AU BOUT de son axe, juste au-delà de l'extrémité (hors du dessin de
    # la parcelle). Si deux lettres (ou la pastille voie) se gênent, on décale LE LONG de l'axe (sortant) — la
    # lettre reste près de son extrémité, jamais rejetée au loin (finition : « B » collé au bout de son axe).
    lettres_boxes = []
    for p in voie_pts:                                 # la pastille « voie » est un obstacle pour les lettres d'axe
        vx, vy = X(p[0]) + 5, Y(p[1]) + 3
        lettres_boxes.append((vx - 2, vx + len("voie") * 9 * 0.56, vy - 9, vy + 3))

    def _pose_lettre(px, py, ux, uy, txt):
        fs, g = 10, 2.0; hw = max(len(txt) * fs * 0.56, 4) / 2 + 2
        cx, cy = px + ux * 9, py + uy * 9              # juste au-delà de l'extrémité, le long de l'axe (sortant)
        for _ in range(8):
            cx = min(max(cx, hw + 1), width - hw - 1); cy = min(max(cy, fs + 1), height - 2)
            box = (cx - hw - g, cx + hw + g, cy - fs - g, cy + 3 + g)
            if not any(not (box[1] < b[0] or box[0] > b[1] or box[3] < b[2] or box[2] > b[3]) for b in lettres_boxes):
                break
            cx += ux * (fs + 2); cy += uy * (fs + 2)   # déjà pris : on glisse LE LONG de l'axe, pas vers le haut
        lettres_boxes.append((cx - hw, cx + hw, cy - fs, cy + 3))
        return f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="{fs}" font-weight="600" fill="{T["axe"]}">{txt}</text>'
    for label, a in axes.items():
        x0, y0, x1, y1 = X(a["p0"][0]), Y(a["p0"][1]), X(a["p1"][0]), Y(a["p1"][1])
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{T["axe"]}" stroke-width="2"/>')
        out.append(_fleche(x0 + (x1 - x0) * 0.72, y0 + (y1 - y0) * 0.72, x1, y1, T["axe"]))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        for px, py, txt in ((x0, y0, label), (x1, y1, f"{label}′")):
            dx, dy = px - mx, py - my; n = (dx * dx + dy * dy) ** 0.5 or 1.0
            out.append(_pose_lettre(px, py, dx / n, dy / n, txt))
    for p in voie_pts:                                 # voie à son intersection (B8)
        out.append(f'<circle cx="{X(p[0]):.1f}" cy="{Y(p[1]):.1f}" r="3.5" fill="none" stroke="{T["axe"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{X(p[0])+5:.1f}" y="{Y(p[1])+3:.1f}" font-size="9" fill="{T["axe"]}">voie</text>')
    nx, ny = width - 22, 30
    out.append(_fleche(nx, ny + 16, nx, ny - 8, T["txt"]))
    out.append(f'<text x="{nx:.1f}" y="{ny-11:.1f}" text-anchor="middle" font-size="9" font-weight="600" fill="{T["txt"]}">N</text>')
    out.append("</svg>")
    return "".join(out)
