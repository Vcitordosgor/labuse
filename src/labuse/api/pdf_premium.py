"""Export PDF de la fiche premium (Brique 3) — IMPRESSION : fond BLANC, encre noire.

Le dark est pour l'écran ; un dossier comité s'imprime. L'identité LABUSE reste par la typo
(Space Grotesk/Inter/JetBrains Mono) et la menthe en ACCENTS FINS (filets, puces, chip statut).
Rendu fpdf2 (pur Python) avec les fontes du design system (OFL, embarquées dans api/fonts/).
Contenu = la fiche complète : en-tête (IDU/statut/surface), bandeau événement, scores Q/A +
complétude, lignes cascade TRACÉES par onglet (poids signé, détail, source, date), flags,
footer non-garantie. Les données viennent de _q_v2_fiche — même source que l'écran.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence (bascule centralisée)

FONTS = Path(__file__).resolve().parent / "fonts"

# Palette IMPRESSION (fond blanc). Menthe écran #5CE6A1 → déclinée en encres qui tiennent le papier.
BG = (255, 255, 255)
SURFACE = (244, 248, 246)  # cartouches gris-vert très pâle
LINE = (216, 226, 220)
MINT = (11, 138, 95)       # menthe d'impression (accents, positifs) — contraste AA sur blanc
MINT_SOFT = (226, 247, 237)  # fond de chip
TXT_HI = (17, 24, 20)      # quasi-noir
TXT = (40, 50, 45)
TXT_MUT = (95, 108, 101)
TXT_DIM = (140, 152, 145)
RED = (183, 63, 50)        # rouge d'impression
RED_SOFT = (250, 233, 230)
AMBER = (168, 121, 22)

STATUT = {
    "chaude": ("Chaude", MINT),
    "a_surveiller": ("À surveiller", (23, 122, 88)),
    "a_creuser": ("À creuser", AMBER),
    "ecartee": ("Écartée", RED),
    "exclue": ("Exclue", (107, 122, 114)),
}

# correctif M5 : tiers v2 (P×C) — verdict d'en-tête quand un run v2 existe (étage 0 prime)
TIER_V2 = {
    "brulante": ("Brûlante v2", RED),
    "chaude": ("Chaude v2", AMBER),
    "a_creuser": ("À creuser", (95, 108, 101)),
    "reserve_fonciere": ("Réserve foncière", (58, 100, 148)),
    "ecartee": ("Écartée", RED),
}
ONGLETS = [("regles", "RÈGLES"), ("risques", "RISQUES"), ("marche", "MARCHÉ"), ("proprio", "PROPRIO")]


class _Pdf(FPDF):
    def header(self):  # fond blanc (papier) — un filet menthe fin signe l'identité en tête de page
        self.set_draw_color(*MINT)
        self.set_line_width(0.6)
        self.line(14, 8, self.w - 14, 8)
        self.set_line_width(0.2)
        self.set_y(12)

    def footer(self):
        self.set_y(-16)
        self.set_font("inter", size=6.5)
        self.set_text_color(*TXT_DIM)
        self.cell(0, 4, "Estimations indicatives issues de données publiques — ne valent ni conseil "
                        "juridique/notarial ni garantie de constructibilité. À vérifier au règlement et "
                        "auprès des services.", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, f"LA BUSE · radar foncier La Réunion · export du {date.today().isoformat()} · "
                        f"page {self.page_no()}/{{nb}}", align="C")


#: silhouette officielle (path labuse.immo, échantillonné) — polygone rempli
_LOGO_PTS = [(2.0,15.0),(8.9,14.4),(15.7,14.0),(22.3,13.7),(28.8,13.5),(35.1,13.5),(41.2,13.5),(47.2,13.6),(53.0,13.9),(58.7,14.2),(64.1,14.7),(69.4,15.2),(74.5,15.8),(79.4,16.4),(84.1,17.1),(88.6,17.9),(93.0,18.8),(97.1,19.7),(101.0,20.6),(104.7,21.6),(108.2,22.6),(111.5,23.7),(114.5,24.8),(117.4,25.9),(120.0,27.0),(122.6,25.9),(125.5,24.8),(128.5,23.7),(131.8,22.6),(135.3,21.6),(139.0,20.6),(142.9,19.7),(147.0,18.8),(151.4,17.9),(155.9,17.1),(160.6,16.4),(165.5,15.8),(170.6,15.2),(175.9,14.7),(181.3,14.2),(187.0,13.9),(192.8,13.6),(198.8,13.5),(204.9,13.5),(211.2,13.5),(217.7,13.7),(224.3,14.0),(231.1,14.4),(238.0,15.0),(233.5,16.7),(228.9,18.4),(224.3,20.1),(219.7,21.7),(215.1,23.3),(210.5,24.9),(205.9,26.4),(201.3,27.9),(196.7,29.4),(192.1,30.8),(187.6,32.2),(183.1,33.5),(178.7,34.8),(174.3,36.0),(170.0,37.2),(165.7,38.4),(161.5,39.5),(157.4,40.6),(153.4,41.6),(149.5,42.6),(145.7,43.5),(142.0,44.4),(138.4,45.2),(135.0,46.0),(134.0,46.4),(133.1,46.8),(132.1,47.2),(131.2,47.6),(130.4,48.0),(129.6,48.5),(128.8,48.9),(128.0,49.4),(127.3,49.9),(126.6,50.4),(125.9,50.9),(125.2,51.5),(124.6,52.1),(124.1,52.7),(123.5,53.3),(123.0,53.9),(122.5,54.6),(122.1,55.3),(121.6,56.0),(121.2,56.7),(120.9,57.5),(120.6,58.3),(120.3,59.1),(120.0,60.0),(119.7,59.1),(119.4,58.3),(119.1,57.5),(118.8,56.7),(118.4,56.0),(117.9,55.3),(117.5,54.6),(117.0,53.9),(116.5,53.3),(115.9,52.7),(115.4,52.1),(114.8,51.5),(114.1,50.9),(113.4,50.4),(112.7,49.9),(112.0,49.4),(111.2,48.9),(110.4,48.5),(109.6,48.0),(108.8,47.6),(107.9,47.2),(106.9,46.8),(106.0,46.4),(105.0,46.0),(101.6,45.2),(98.0,44.4),(94.3,43.5),(90.5,42.6),(86.6,41.6),(82.6,40.6),(78.5,39.5),(74.3,38.4),(70.0,37.2),(65.7,36.0),(61.3,34.8),(56.9,33.5),(52.4,32.2),(47.9,30.8),(43.3,29.4),(38.7,27.9),(34.1,26.4),(29.5,24.9),(24.9,23.3),(20.3,21.7),(15.7,20.1),(11.1,18.4),(6.5,16.7),(2.0,15.0)]


def _logo(pdf: FPDF, x: float, y: float, w: float) -> None:
    k = w / 240.0
    pdf.set_fill_color(*MINT)
    with pdf.new_path() as path:
        path.style.fill_color = "#0B8A5F"
        path.style.stroke_width = 0
        path.move_to(x + 2 * k, y + 15 * k)
        for px, py in _LOGO_PTS:
            path.line_to(x + px * k, y + py * k)
        path.close()


def _chip(pdf: _Pdf, x: float, y: float, label: str, color: tuple) -> float:
    pdf.set_font("inter", size=7.5)
    w = pdf.get_string_width(label) + 6
    pdf.set_fill_color(*(MINT_SOFT if color == MINT else
                         RED_SOFT if color == RED else (238, 241, 239)))
    pdf.rect(x, y, w, 5.4, style="F", round_corners=True, corner_radius=2.6)
    pdf.set_text_color(*color)
    pdf.set_xy(x + 3, y + 0.7)
    pdf.cell(w - 6, 4, label)
    return w


def render_fiche_pdf(fiche: dict) -> bytes:
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    # ── En-tête produit : la buse officielle (labuse.immo) + wordmark
    _logo(pdf, 14, pdf.get_y() + 1, 13)
    pdf.set_x(30)
    pdf.set_font("grotesk", size=13)
    pdf.set_text_color(*MINT)
    pdf.cell(0, 6, "LA BUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 4, f"Radar foncier premium — La Réunion · fiche parcelle (scoring v2, run {RUN})",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── Bandeau événement (héros) — C5 : il raconte SON histoire en une phrase
    if fiche.get("evenement") == "rouge":
        pm = (fiche.get("proprietaire_moral") or {}).get("denomination")
        detail = (f"Chaude par ÉVÉNEMENT : le propriétaire{f' ({pm})' if pm else ''} est en "
                  f"procédure collective — {fiche.get('evenement_detail') or 'procédure BODACC ouverte'}. "
                  f"Le score qualité ({fiche.get('q_score')}) n'a pas déclenché ce statut : "
                  "l'urgence du dossier vendeur prime (doctrine bascule).")
        # hauteur du bandeau = titre + détail wrap (mesuré avant de peindre le fond)
        pdf.set_font("inter", size=7)
        n_lines = max(1, len(pdf.multi_cell(pdf.w - 36, 3.6, detail, dry_run=True, output="LINES")))
        h = 7.6 + n_lines * 3.6 + 2
        y = pdf.get_y()
        pdf.set_fill_color(*RED_SOFT)
        pdf.rect(14, y, pdf.w - 28, h, style="F", round_corners=True, corner_radius=2)
        pdf.set_xy(18, y + 1.6)
        pdf.set_font("inter", size=8.5)
        pdf.set_text_color(*RED)
        pdf.cell(0, 4, "● ÉVÉNEMENT — force « chaude »", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(18, y + 7.2)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(120, 52, 44)
        pdf.multi_cell(pdf.w - 36, 3.6, detail)
        pdf.set_y(y + h + 3)

    # ── IDU + statut + méta
    pdf.set_font("mono", size=14)
    pdf.set_text_color(*TXT_HI)
    pdf.cell(0, 7, fiche["idu"], new_x="LMARGIN", new_y="NEXT")
    # verdict d'en-tête (correctif M5) : étage 0 → écartée ; sinon tier v2 s'il existe ;
    # sinon statut matrice. Le statut matrice descend en « historique » (ligne dim).
    s2 = fiche.get("score_v2")
    v2_pilote = bool(s2) and not fiche.get("etage0")
    if v2_pilote:
        label, color = TIER_V2.get(s2["tier"], (s2["tier"], TXT_MUT))
        if s2["tier"] in ("brulante", "chaude") and s2.get("rang") is not None:
            label += f" · rang {s2['rang']}"
        if s2.get("mult_base") is not None:
            label += f" · ×{s2['mult_base']:.1f}"
    else:
        label, color = STATUT.get(fiche["statut"], ("?", TXT_MUT))
    y = pdf.get_y() + 1
    w = _chip(pdf, 14, y, label, color)
    pdf.set_font("inter", size=8)
    pdf.set_text_color(*TXT_MUT)
    surf = f"{fiche['surface_m2']:,} m²".replace(",", " ") if fiche.get("surface_m2") else "surface n/d"
    lon, lat = fiche.get("coords", [None, None])
    pdf.set_xy(14 + w + 4, y + 0.4)
    pdf.cell(0, 4.6, f"{surf} · {fiche.get('commune', '')} · {lat}, {lon}")
    pdf.set_y(y + 9)
    if v2_pilote:
        hist, _ = STATUT.get(fiche["statut"], ("?", TXT_MUT))
        pdf.set_font("inter", size=6.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 3.6, f"Statut matrice (historique) : {hist} — remplacé par le scoring v2 (P×C)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # ── Scores (Q / A / complétude — le score ne s'affiche jamais seul)
    y = pdf.get_y()
    cw = (pdf.w - 28 - 8) / 3
    vals = [("QUALITÉ", fiche["q_score"], MINT), ("ACCESSIBILITÉ", fiche["a_score"], (23, 122, 88)),
            ("COMPLÉTUDE", fiche["completeness_score"],
             MINT if fiche["completeness_score"] >= 50 else AMBER)]
    for i, (k, v, c) in enumerate(vals):
        x = 14 + i * (cw + 4)
        pdf.set_fill_color(*SURFACE)
        pdf.rect(x, y, cw, 17, style="F", round_corners=True, corner_radius=2.4)
        pdf.set_xy(x + 5, y + 2.6)
        pdf.set_font("grotesk", size=15)
        pdf.set_text_color(*c)
        pdf.cell(cw - 10, 7, str(v))
        pdf.set_xy(x + 5, y + 10.6)
        pdf.set_font("mono", size=6.3)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(cw - 10, 4, f"{k} / 100" if k != "COMPLÉTUDE" else f"{k} %")
    pdf.set_y(y + 21)

    # ── CONTEXTE COMMUNE (mandat promotrice) — SRU · QPV/ANRU · marché, sourcé
    ctx = fiche.get("contexte_commune") or {}
    if ctx:
        pdf.set_font("mono", size=6.6)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, f"CONTEXTE COMMUNE — {fiche.get('commune', '').upper()}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7.6)
        pdf.set_text_color(40, 50, 45)
        lignes = []
        sru = ctx.get("sru")
        if sru:
            st = {"carencee": "CARENCÉE", "deficitaire": "déficitaire",
                  "exemptee": "exemptée 2023-2025", "conforme": "conforme"}.get(sru["statut"], sru["statut"])
            lignes.append(f"SRU : {sru['taux_lls']} % de logements sociaux — objectif {sru['objectif_pct']} % — {st}"
                          + (f" (prélèvement 2025 : {int(sru['prelevement_eur']):,} €)".replace(",", " ")
                             if (sru.get("prelevement_eur") or 0) > 0 else ""))
        qpv, anru = ctx.get("qpv") or [], ctx.get("anru") or []
        lignes.append(f"Politique de la ville : {len(qpv)} QPV (génération 2024)"
                      + (f" · NPNRU : {', '.join(a['nom'] for a in anru)} (intérêt national)" if anru else " · aucun périmètre NPNRU"))
        mar = ctx.get("marche")
        if mar:
            lignes.append(f"Marché (INSEE RP 2023) : {int(mar['logements']):,} logements — "
                          f"{mar['locataires_pct']} % locataires · {mar['maisons_pct']} % maisons · "
                          f"{mar['typologie'].get('vacance_pct')} % de vacance".replace(",", " "))
        for ln_txt in lignes:
            pdf.multi_cell(pdf.w - 28, 4.0, ln_txt, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=6.2)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 3.6, "Sources : inventaire SRU DHUP (01/01/2024) · DEAL Réunion/ANCT (NPNRU) · "
                         "INSEE RP 2023 — contexte informatif, hors scoring.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── RTAA DOM (5bis) — rappel réglementaire de conception (vérifié Légifrance)
    rtaa = fiche.get("rtaa") or {}
    if rtaa:
        pdf.set_font("mono", size=6.6)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, "RTAA DOM — RAPPEL RÉGLEMENTAIRE (CONSTRUCTION NEUVE DE LOGEMENTS)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7.2)
        pdf.set_text_color(40, 50, 45)
        resume = {
            "thermique": "Protection solaire (parois : S<=0,03/0,09 ; baies : S max par orientation, "
                         "seuils 400/600 m) · ventilation naturelle traversante (sejour 22 %, chambres 18 % "
                         "sous 400 m ; exemption > 600 m, regime isolation) · brasseurs d'air.",
            "acoustique": "Separatifs >= 350 kg/m2 ou Rw+C >= 54 dB · plancher >= 450 kg/m2 · equipements "
                          "<= 35 dB(A) pieces principales · isolement de facade en secteur d'infrastructure classee.",
            "aeration": "Cuisine : baie >= 1 m2 sur l'exterieur · SdB/WC ouvrants ou extraction mecanique · "
                        "ventilation mecanique obligatoire si pieces climatisees.",
            "ecs": "ECS obligatoire, produite a >= 50 % par sources de chaleur renouvelables "
                   "(solaire thermique en pratique) — CCH R.192-2, en vigueur 01/01/2025.",
        }
        for volet, txt in resume.items():
            pdf.set_font("inter", size=7.2)
            pdf.multi_cell(pdf.w - 28, 3.8, f"{volet.upper()} — {txt}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=6.2)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.4,
                       "References : arretes du 17/04/2009 (thermique, acoustique, aeration) modifies par "
                       "l'arrete du 11/01/2016 (PC/DP depuis le 01/07/2016) ; cadre CCH R.192-1 a R.192-4 "
                       "(decret n 2024-168, 01/01/2025). Rappel de conception - ne remplace pas l'etude "
                       "reglementaire du maitre d'oeuvre.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── Lignes tracées, par onglet
    for key, titre in ONGLETS:
        lines = [ln for ln in fiche["lines"] if ln["onglet"] == key]
        if not lines:
            continue
        pdf.ln(1.5)
        pdf.set_font("mono", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 5, titre, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LINE)
        pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
        pdf.ln(1.2)
        for ln in lines:
            if pdf.get_y() > pdf.h - 34:
                pdf.add_page()
            w0 = ln.get("weight")
            wtxt = ("+" + str(w0) if (w0 or 0) > 0 else str(w0)) if w0 is not None else \
                ("?" if ln["result"] == "UNKNOWN" else "·")
            wcol = MINT if (w0 or 0) > 0 else (RED if (w0 or 0) < 0 else TXT_DIM)
            pdf.set_font("mono", size=8)
            pdf.set_text_color(*wcol)
            pdf.cell(11, 4.4, wtxt, align="R")
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*TXT)
            pdf.cell(40, 4.4, ln["layer"][:26])
            pdf.set_font("inter", size=7.2)
            pdf.set_text_color(*TXT_MUT)
            x = pdf.get_x()
            pdf.multi_cell(pdf.w - 14 - x, 3.6, ln["detail"] or "", new_x="LMARGIN", new_y="NEXT")
            # traçabilité : source + référence + date (exigence fraîcheur par ligne)
            src = ln.get("source") or ""
            ref = f"{ln['source_table']}#{ln['source_id']}" if ln.get("source_id") is not None else ""
            pdf.set_x(65)
            pdf.set_font("mono", size=6)
            pdf.set_text_color(*TXT_DIM)
            pdf.cell(0, 3.4, "  ".join(x for x in (src, ref, ln.get("date") or "") if x),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.8)

    # ── A6 (mandat bilan-calculette) : CHARGE FONCIÈRE « selon vos hypothèses », si passée à l'export
    calc = fiche.get("calculette")
    if calc and calc.get("calculable"):
        cf = calc.get("charge_fonciere") or {}
        inp = calc.get("inputs") or {}

        def _e(x: float | None) -> str:
            if x is None:
                return "—"
            ax = abs(x)
            if ax >= 1_000_000:
                return f"{x / 1_000_000:.1f} M€"
            if ax >= 1_000:
                return f"{round(x / 1_000):,} k€".replace(",", " ")
            return f"{round(x):,} €".replace(",", " ")

        if pdf.get_y() > pdf.h - 48:
            pdf.add_page()
        pdf.ln(2)
        pdf.set_font("mono", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 5, "CHARGE FONCIÈRE — SELON VOS HYPOTHÈSES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LINE)
        pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
        pdf.ln(1.4)
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4,
                       "Hypothèses promoteur (saisies, non estimées par LABUSE) : coût de "
                       f"construction {round(inp.get('cout_construction_m2') or 0):,} EUR/m2 · "
                       f"marge & frais {inp.get('marge_frais_pct')} %.".replace(",", " "),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)
        pdf.set_font("grotesk", size=12)
        pdf.set_text_color(*MINT)
        pdf.cell(0, 6, f"Charge foncière supportable : {_e(cf.get('central'))}  "
                 f"(~ {round(cf.get('par_m2_terrain') or 0):,} EUR/m2 terrain)".replace(",", " "),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, f"fourchette {_e(cf.get('bas'))} - {_e(cf.get('haut'))} · "
                 f"fiabilite prix : {calc.get('fiabilite')}", new_x="LMARGIN", new_y="NEXT")
        ach = calc.get("achat")
        if ach:
            pdf.ln(0.3)
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*(MINT if ach.get("supportable") else RED))
            v = (f"Prix demande {_e(ach.get('prix_demande_eur'))} : SUPPORTABLE "
                 f"(marge {_e(ach.get('ecart_eur'))}, {ach.get('ecart_pct')} %)"
                 if ach.get("supportable") else
                 f"Prix demande {_e(ach.get('prix_demande_eur'))} : TROP CHER "
                 f"(ecart {_e(ach.get('ecart_eur'))}, {ach.get('ecart_pct')} %)")
            pdf.multi_cell(pdf.w - 28, 4, v, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.3)
        pdf.set_font("inter", size=6.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.4, "Calcul a partir de VOS hypotheses — estimation indicative, "
                       "ne vaut ni conseil ni engagement.", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    return bytes(out)
