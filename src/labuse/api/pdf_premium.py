"""Export PDF de la fiche premium (Brique 3) — IMPRESSION : fond BLANC, encre noire.

Le dark est pour l'écran ; un dossier comité s'imprime. L'identité LABUSE reste par la typo
(Space Grotesk/Inter/JetBrains Mono) et la menthe en ACCENTS FINS (filets, puces, chip statut).
Rendu fpdf2 (pur Python) avec les fontes du design system (OFL, embarquées dans api/fonts/).
Contenu = la fiche complète : en-tête (IDU/statut/surface), bandeau événement, scores Q/A +
complétude, lignes cascade TRACÉES par onglet (poids signé, détail, source, date), flags,
footer non-garantie. Les données viennent de _q_v2_fiche — même source que l'écran.
"""
from __future__ import annotations

import math
from pathlib import Path

from fpdf import FPDF

from ..verdict_servi import TIER_LABELS, DECLASSE_RGB  # source unique des libellés client (écran = papier)

FONTS = Path(__file__).resolve().parent / "fonts"

# Palette IMPRESSION (fond blanc). Menthe écran #5CE6A1 → déclinée en encres qui tiennent le papier.
BG = (255, 255, 255)
SURFACE = (244, 248, 246)  # cartouches gris-vert très pâle
LINE = (216, 226, 220)
MINT = (30, 158, 88)       # M73-G — vert print CANON #1E9E58 (mandat + les 4 weasyprint), AA sur blanc
MINT_SOFT = (226, 247, 237)  # fond de chip
TXT_HI = (17, 24, 20)      # quasi-noir
TXT = (40, 50, 45)
TXT_MUT = (95, 108, 101)
TXT_DIM = (140, 152, 145)
RED = (183, 63, 50)        # rouge d'impression
RED_SOFT = (250, 233, 230)
AMBER = (168, 121, 22)

# M-P (P2-62) : la table STATUT (matrice Q/A, avec `a_surveiller`) est SUPPRIMÉE — matrice éteinte
# (M37), plus jamais un verdict matriciel dans un document client. Le verdict d'en-tête vient du
# tier v2 (étage 0 prime) ; sans run v2 → libellé neutre « Classement historique ».
# M-P (P2-63) : un PDF circule plus loin qu'une page web — on exclut la donnée personnelle sensible
# `age_dirigeant` (âge d'un dirigeant), comme share_public (COUCHES_PROPRIETAIRE). L'onglet PROPRIO
# reste imprimé (document abonné, derrière auth, PM publique DGFiP) ; seule cette ligne est retirée.
COUCHES_EXCLUES = {"age_dirigeant"}

# correctif M5 : tiers v2 (P×C) — verdict d'en-tête quand un run v2 existe (étage 0 prime)
TIER_V2 = {
    "brulante": ("Brûlante v2", RED),
    "chaude": ("Chaude v2", AMBER),
    "a_creuser": ("À creuser", (95, 108, 101)),
    "reserve_fonciere": ("Potentiel long terme", (58, 100, 148)),
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
        # M6 2a : pied de page commun (non-garantie + disclaimer CU au mot près +
        # attributions sources + date de génération) — une seule vérité, export_commun.
        from .export_commun import pied_de_page_pdf
        # M55-H point 11 : le nom technique du run ne parait plus sur le document
        pied_de_page_pdf(self, "fiche parcelle")


#: silhouette officielle (path labuse.immo, échantillonné) — polygone rempli
_LOGO_PTS = [(2.0,15.0),(8.9,14.4),(15.7,14.0),(22.3,13.7),(28.8,13.5),(35.1,13.5),(41.2,13.5),(47.2,13.6),(53.0,13.9),(58.7,14.2),(64.1,14.7),(69.4,15.2),(74.5,15.8),(79.4,16.4),(84.1,17.1),(88.6,17.9),(93.0,18.8),(97.1,19.7),(101.0,20.6),(104.7,21.6),(108.2,22.6),(111.5,23.7),(114.5,24.8),(117.4,25.9),(120.0,27.0),(122.6,25.9),(125.5,24.8),(128.5,23.7),(131.8,22.6),(135.3,21.6),(139.0,20.6),(142.9,19.7),(147.0,18.8),(151.4,17.9),(155.9,17.1),(160.6,16.4),(165.5,15.8),(170.6,15.2),(175.9,14.7),(181.3,14.2),(187.0,13.9),(192.8,13.6),(198.8,13.5),(204.9,13.5),(211.2,13.5),(217.7,13.7),(224.3,14.0),(231.1,14.4),(238.0,15.0),(233.5,16.7),(228.9,18.4),(224.3,20.1),(219.7,21.7),(215.1,23.3),(210.5,24.9),(205.9,26.4),(201.3,27.9),(196.7,29.4),(192.1,30.8),(187.6,32.2),(183.1,33.5),(178.7,34.8),(174.3,36.0),(170.0,37.2),(165.7,38.4),(161.5,39.5),(157.4,40.6),(153.4,41.6),(149.5,42.6),(145.7,43.5),(142.0,44.4),(138.4,45.2),(135.0,46.0),(134.0,46.4),(133.1,46.8),(132.1,47.2),(131.2,47.6),(130.4,48.0),(129.6,48.5),(128.8,48.9),(128.0,49.4),(127.3,49.9),(126.6,50.4),(125.9,50.9),(125.2,51.5),(124.6,52.1),(124.1,52.7),(123.5,53.3),(123.0,53.9),(122.5,54.6),(122.1,55.3),(121.6,56.0),(121.2,56.7),(120.9,57.5),(120.6,58.3),(120.3,59.1),(120.0,60.0),(119.7,59.1),(119.4,58.3),(119.1,57.5),(118.8,56.7),(118.4,56.0),(117.9,55.3),(117.5,54.6),(117.0,53.9),(116.5,53.3),(115.9,52.7),(115.4,52.1),(114.8,51.5),(114.1,50.9),(113.4,50.4),(112.7,49.9),(112.0,49.4),(111.2,48.9),(110.4,48.5),(109.6,48.0),(108.8,47.6),(107.9,47.2),(106.9,46.8),(106.0,46.4),(105.0,46.0),(101.6,45.2),(98.0,44.4),(94.3,43.5),(90.5,42.6),(86.6,41.6),(82.6,40.6),(78.5,39.5),(74.3,38.4),(70.0,37.2),(65.7,36.0),(61.3,34.8),(56.9,33.5),(52.4,32.2),(47.9,30.8),(43.3,29.4),(38.7,27.9),(34.1,26.4),(29.5,24.9),(24.9,23.3),(20.3,21.7),(15.7,20.1),(11.1,18.4),(6.5,16.7),(2.0,15.0)]


def _logo(pdf: FPDF, x: float, y: float, w: float) -> None:
    k = w / 240.0
    pdf.set_fill_color(*MINT)
    with pdf.new_path() as path:
        path.style.fill_color = "#1E9E58"
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


def _motif_verdict(s2: dict) -> str | None:
    """UNE phrase de « pourquoi » sous le verdict — assemblée depuis les DONNÉES moteur
    (probabilité de mutation vs base + motif servi). Déterministe, pas d'IA ; c'est le MÊME
    motif que l'écran et le one-pager (verdict_servi). Borné pour tenir sur ~2 lignes."""
    bouts: list[str] = []
    if s2.get("mult_base") is not None:
        bouts.append(f"probabilité de mutation ×{s2['mult_base']:.1f} vs base")
    if s2.get("motif"):
        bouts.append(str(s2["motif"]))
    phrase = " — ".join(bouts)
    if not phrase:
        return None
    return phrase if len(phrase) <= 190 else phrase[:187].rstrip() + "…"


def render_fiche_pdf(fiche: dict) -> bytes:
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=26)   # pied de page commun (4 lignes)
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
    pdf.cell(0, 6, "LABUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 4, "Radar foncier premium — La Réunion · fiche parcelle",
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

    # ── IDU + adresse postale BAN + statut + méta
    pdf.set_font("mono", size=14)
    pdf.set_text_color(*TXT_HI)
    pdf.cell(0, 7, fiche["idu"], new_x="LMARGIN", new_y="NEXT")
    # M6 2a : l'adresse BAN sous l'IDU — « Adresse non disponible » si aucune rattachée
    adr = fiche.get("adresse_ban")
    pdf.set_font("inter", size=8.5)
    pdf.set_text_color(*(TXT if adr else TXT_DIM))
    pdf.cell(0, 4.6, adr or "Adresse non disponible", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)
    # M-P (P2-62) : UN SEUL verdict. La matrice Q/A est ÉTEINTE (M37) — plus jamais imprimée en
    # second verdict « historique » sur un document remis à un comité/banquier. étage 0 du run servi
    # prime → Écartée ; sinon le tier v2 pilote ; sinon (aucun run v2 sur ce parc) libellé NEUTRE —
    # jamais un statut matriciel mort présenté comme un verdict.
    s2 = fiche.get("score_v2")
    v2_pilote = bool(s2) and not fiche.get("etage0")
    motif = None
    if v2_pilote:
        tier = s2["tier"]
        is_declasse = bool(s2.get("declasse")) or (isinstance(tier, str) and tier.startswith("declasse_"))
        # M54-AB C1 : libellé CLIENT (source unique verdict_servi), JAMAIS le code technique ni « v2 ».
        label = s2.get("label") or TIER_LABELS.get(tier, tier)
        # couleur « terre » pour tout déclassement (palette M-Q) ; sinon la couleur du tier servable.
        color = DECLASSE_RGB if is_declasse else TIER_V2.get(tier, ("", TXT_MUT))[1]
        # rang AVEC son dénominateur (un rang seul ne dit rien) — pour tout tier classé.
        if s2.get("rang") is not None:
            label += f" · rang {s2['rang']:,}".replace(",", " ")
            if s2.get("rang_total"):
                label += f" / {s2['rang_total']:,}".replace(",", " ")
        motif = _motif_verdict(s2)  # la « ×1.3 » migre du gros titre vers la phrase de motif
    elif fiche.get("etage0"):
        label, color = "Écartée", RED
    else:
        label, color = "Classement historique", TXT_MUT
    # ── M22-F C4 : VERDICT EN TÊTE, hiérarchie M19 — carte pleine largeur, gros label + motif
    surf = f"{fiche['surface_m2']:,} m²".replace(",", " ") if fiche.get("surface_m2") else "surface n/d"
    lon, lat = fiche.get("coords", [None, None])
    y = pdf.get_y() + 1
    card_h = 21.5 if motif else 15
    pdf.set_fill_color(*SURFACE)
    pdf.rect(14, y, pdf.w - 28, card_h, style="F", round_corners=True, corner_radius=2.4)
    pdf.set_xy(19, y + 2.2)
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 3.6, "VERDICT LABUSE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(19, y + 6.6)
    pdf.set_font("grotesk", size=14)
    pdf.set_text_color(*color)
    pdf.cell(110, 6.5, label)
    pdf.set_font("inter", size=7.2)
    pdf.set_text_color(*TXT_MUT)
    pdf.set_xy(14, y + 7.8)
    pdf.cell(pdf.w - 33, 4.6, f"{surf} · {fiche.get('commune', '')} · {lat}, {lon}", align="R")
    if motif:
        pdf.set_xy(19, y + 13.2)
        pdf.set_font("inter", size=7.4)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 38, 3.4, motif)
    pdf.set_y(y + card_h + 2)
    # M-P (P2-62) : le second verdict issu de la matrice éteinte est SUPPRIMÉ — un seul verdict/document.

    # ── Scores (Q / A — le score ne s'affiche jamais seul)
    # M36 Lot B : la jauge COMPLÉTUDE est RETIRÉE (3 valeurs sur tout le parc — n'informe
    # pas ; arbitrage Vic M35 D3). L'ICD ci-dessous est la vraie jauge par parcelle.
    y = pdf.get_y()
    cw = (pdf.w - 28 - 4) / 2
    vals = [("QUALITÉ", fiche["q_score"], MINT), ("ACCESSIBILITÉ", fiche["a_score"], (23, 122, 88))]
    for i, (k, v, c) in enumerate(vals):
        x = 14 + i * (cw + 4)
        pdf.set_fill_color(*SURFACE)
        pdf.rect(x, y, cw, 17, style="F", round_corners=True, corner_radius=2.4)
        pdf.set_xy(x + 5, y + 2.6)
        pdf.set_font("grotesk", size=15)
        pdf.set_text_color(*c)
        pdf.cell(cw - 10, 7, str(v))
        pdf.set_xy(x + 5, y + 10.6)
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_DIM)
        # M54-AB F8 : chiffre de tête étiqueté (doctrine Sourcé/Estimé du banquier) — Q/A = Estimé.
        pdf.cell(cw - 10, 4, f"{k} / 100 · ESTIMÉ")
    pdf.set_y(y + 21)

    # ── M9 lot 1 — INDICE DE CONFIANCE DONNÉES (ICD). Méta d'affichage CLOISONNÉE du
    # score : dit la complétude des données, pas l'opportunité. Mention OBLIGATOIRE si < 60.
    icd = fiche.get("icd")
    if icd and icd.get("score") is not None:
        val, bande = icd["score"], icd.get("bande")
        col = AMBER if bande == "faible" else (TXT_MUT if bande == "partielle" else (23, 122, 88))
        pdf.set_font("inter", size=7.4)
        pdf.set_text_color(*col)
        # M54-AB F8 : « Confiance des DONNÉES » (complétude) — dit ce qu'elle mesure, à ne pas
        # confondre avec la « Confiance du calibrage (règles PLU) » du dossier parcelle.
        txt = f"Confiance des données (complétude) : {val}/100 — {icd.get('libelle', '')}"
        manque = icd.get("manquants") or []
        if manque:
            txt += " · manque : " + ", ".join(manque[:4]) + ("…" if len(manque) > 4 else "")
        # M54-AB F8 : X réinitialisé à la marge avant chaque multi_cell — sinon le cadre dérive et
        # « L'indice mes… » était coupé au bord droit de la p.1. Largeur = pleine colonne (marges 14).
        pdf.set_x(14)
        pdf.multi_cell(pdf.w - 28, 3.8, txt)
        if bande == "faible":
            pdf.set_font("inter", size=7)
            pdf.set_text_color(*AMBER)
            pdf.set_x(14)
            pdf.multi_cell(pdf.w - 28, 3.4,
                           "⚠ Confiance faible : données de la parcelle incomplètes — "
                           "verdict à confirmer par vérification terrain/CU.")
        pdf.set_text_color(*TXT_DIM)
        pdf.set_font("inter", size=7)
        pdf.set_x(14)
        pdf.multi_cell(pdf.w - 28, 3.2,
                       "L'indice mesure la complétude des données ; il n'entre pas dans le score d'opportunité.")
        pdf.ln(1.2)

    # ── M9 lot 4 — POTENTIEL DE TRANSFORMATION (fond de l'ancien outil Mutabilité)
    pt = fiche.get("potentiel_transformation")
    if pt and pt.get("niveau") and pt["niveau"] != "indetermine":
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, "POTENTIEL DE TRANSFORMATION", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7.6)
        pdf.set_text_color(40, 50, 45)
        ligne = pt.get("libelle", "")
        if pt.get("pct_consomme") is not None:
            ligne += f" · SDP consommée {pt['pct_consomme']} % de l'autorisé"
        if pt.get("sdp_residuelle_m2"):
            ligne += f" · ~{pt['sdp_residuelle_m2']:,} m² SDP résiduelle".replace(",", " ")
        if pt.get("surelevation_possible"):
            marge = pt.get("hauteur_marge_m")
            ligne += f" · surélévation possible" + (f" (marge ~{marge} m)" if marge else "")
        pdf.multi_cell(pdf.w - 28, 3.8, ligne)
        pdf.ln(1.2)

    # ── CONTEXTE COMMUNE (mandat promotrice) — SRU · QPV/ANRU · marché, sourcé
    ctx = fiche.get("contexte_commune") or {}
    if ctx:
        pdf.set_font("mono", size=7)
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
        # M54-AB C5 : UNE ligne de synthèse marché DVF datée (M-U), pas les 9 lignes du bloc complet.
        if fiche.get("marche_synthese"):
            lignes.append(fiche["marche_synthese"])
        for ln_txt in lignes:
            pdf.multi_cell(pdf.w - 28, 4.0, ln_txt, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 3.6, "Sources : inventaire SRU DHUP (01/01/2024) · DEAL Réunion/ANCT (NPNRU) · "
                         "INSEE RP 2023 — contexte informatif, hors scoring.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── RTAA DOM (5bis) — rappel réglementaire de conception (vérifié Légifrance)
    rtaa = fiche.get("rtaa") or {}
    if rtaa:
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, "RTAA DOM — RAPPEL RÉGLEMENTAIRE (CONSTRUCTION NEUVE DE LOGEMENTS)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7.2)
        pdf.set_text_color(40, 50, 45)
        # M-C (F6) : accents restaurés (la fonte inter est unicode, le reste du document est accentué ;
        # l'ASCII-isation était un vieux contournement d'encodage inutile). Opérateurs >=/<= laissés
        # en ASCII (non demandés, pas d'unicode math ailleurs dans le doc).
        resume = {
            "thermique": "Protection solaire (parois : S<=0,03/0,09 ; baies : S max par orientation, "
                         "seuils 400/600 m) · ventilation naturelle traversante (séjour 22 %, chambres 18 % "
                         "sous 400 m ; exemption > 600 m, régime isolation) · brasseurs d'air.",
            "acoustique": "Séparatifs >= 350 kg/m² ou Rw+C >= 54 dB · plancher >= 450 kg/m² · équipements "
                          "<= 35 dB(A) pièces principales · isolement de façade en secteur d'infrastructure classée.",
            "aération": "Cuisine : baie >= 1 m² sur l'extérieur · SdB/WC ouvrants ou extraction mécanique · "
                        "ventilation mécanique obligatoire si pièces climatisées.",
            "ecs": "ECS obligatoire, produite à >= 50 % par sources de chaleur renouvelables "
                   "(solaire thermique en pratique) — CCH R.192-2, en vigueur 01/01/2025.",
        }
        for volet, txt in resume.items():
            pdf.set_font("inter", size=7.2)
            pdf.multi_cell(pdf.w - 28, 3.8, f"{volet.upper()} — {txt}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.4,
                       "Références : arrêtés du 17/04/2009 (thermique, acoustique, aération) modifiés par "
                       "l'arrêté du 11/01/2016 (PC/DP depuis le 01/07/2016) ; cadre CCH R.192-1 à R.192-4 "
                       "(décret n° 2024-168, 01/01/2025). Rappel de conception — ne remplace pas l'étude "
                       "réglementaire du maître d'œuvre.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── Lignes tracées, par onglet — M22-F C4 : SECTIONS CARTOUCHES (hiérarchie M19)
    # + PLAFOND 2 PAGES : au-delà, on n'imprime plus (compteur honnête, fiche écran complète).
    TITRES_M19 = {"regles": "Règles d'urbanisme", "risques": "Risques",
                  "marche": "Marché", "proprio": "Propriétaire"}
    # M70 décision 6 — libellés FR des couches (miroir de frontend/src/lib/layers.ts LAYER_LABEL,
    # source canonique) : le PDF ne montre plus la clé technique brute de couche au client.
    _LAYER_LABEL = {
        "zonage_plu_gpu": "Zonage PLU", "prescription_plu": "Prescriptions PLU",
        "foncier_public": "Foncier public", "emprise_lineaire": "Emprise linéaire",
        "emprise_routiere": "Emprise routière", "residuel_socle": "SDP résiduelle",
        "safer": "SAFER", "sar": "SAR (aménagement régional)", "surface": "Surface parcelle",
        "parc_national": "Parc national", "foret_publique": "Forêt publique",
        "cinquante_pas": "50 pas géométriques", "sup": "Servitudes (SUP)",
        "risques": "Risques PPR", "sol_pollue": "Sols pollués", "cavite": "Cavités",
        "icpe": "ICPE", "mvt": "Mouvement de terrain", "pente": "Pente", "ravine": "Ravines",
        "trait_de_cote": "Trait de côte", "abf": "ABF / Monuments",
        "ens": "Espace naturel sensible", "eau": "Eau", "bruit_route": "Bruit routier",
        "dvf": "Marché DVF", "sitadel": "Permis SITADEL", "amenites": "Aménités",
        "potentiel_foncier_region": "Potentiel foncier Région", "ocs_ge": "Occupation du sol",
        "friche": "Friche", "acces": "Accès voirie", "proprietaire": "Propriétaire",
        "bodacc": "BODACC", "assemblage": "Assemblage", "bati": "Bâti",
        "osm_faux_positif": "Contrôle géométrique OSM",     # M73 D — clé brute rendue avant
    }

    def _layer_label(key: str) -> str:
        # M73 D — jamais la clé technique brute : à défaut de libellé mappé, on humanise
        # (underscores → espaces, capitale) plutôt que d'imprimer « osm_faux_positif ».
        return _LAYER_LABEL.get(key) or key.replace("_", " ").capitalize()
    omises = 0
    sections_omises: list[str] = []   # M-P (P2-64) : NOMMER la section tronquée, pas juste compter
    for key, titre in ONGLETS:
        # M-P (P2-63) : `age_dirigeant` (donnée personnelle) exclue du PDF (COUCHES_EXCLUES).
        lines = [ln for ln in fiche["lines"] if ln["onglet"] == key and ln["layer"] not in COUCHES_EXCLUES]
        if not lines:
            continue
        if pdf.page >= 2 and pdf.get_y() > pdf.h - 60:
            omises += len(lines)
            sections_omises.append(TITRES_M19.get(key, titre))
            continue
        pdf.ln(1.5)
        # en-tête de section en CARTOUCHE (comme un tiroir M19) + résumé à droite
        # M70 décision 5 — plus de « somme +{poids} » (score brut) au client ; juste le compte.
        resume = f"{len(lines)} signal(aux)"
        y = pdf.get_y()
        pdf.set_fill_color(*SURFACE)
        pdf.rect(14, y, pdf.w - 28, 7, style="F", round_corners=True, corner_radius=2)
        pdf.set_xy(18, y + 1.6)
        pdf.set_font("grotesk", size=8.5)
        pdf.set_text_color(*TXT_HI)
        pdf.cell(90, 4, TITRES_M19.get(key, titre))
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_MUT)
        pdf.set_xy(14, y + 1.8)
        pdf.cell(pdf.w - 32, 4, resume, align="R")
        pdf.set_y(y + 8.6)
        titre_m19 = TITRES_M19.get(key, titre)
        for ln in lines:
            if pdf.page >= 2 and pdf.get_y() > pdf.h - 44:
                omises += 1
                if titre_m19 not in sections_omises:   # section tronquée en cours d'impression
                    sections_omises.append(titre_m19)
                continue
            if pdf.get_y() > pdf.h - 34:
                pdf.add_page()
            # M70 décisions 5+6 — plus de préfixe de poids signé, plus de clé technique de couche :
            # libellé FR ferré à gauche (comme la fiche), le « pourquoi » chiffré vit ailleurs.
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*TXT)
            pdf.cell(51, 4.4, _layer_label(ln["layer"])[:34])
            pdf.set_font("inter", size=7.2)
            pdf.set_text_color(*TXT_MUT)
            x = pdf.get_x()
            # M54-AB C7 : la pente client = RGE ALTI (parcel_terrain), en ° ET %, MÊME source que
            # dossier/flash — plus de « ~10 % » (relief coarse) contredisant « 11,4° ≈ 20 % ».
            detail = ln["detail"] or ""
            if ln["layer"] == "pente" and fiche.get("pente_terrain"):
                detail = f"Pente {fiche['pente_terrain']} — RGE ALTI 5 m, non éliminatoire."
            pdf.multi_cell(pdf.w - 14 - x, 3.6, detail, new_x="LMARGIN", new_y="NEXT")
            # traçabilité : source + MILLÉSIME AMONT. M70 décision 6 — plus de clé technique.
            # M73 E : on n'affiche PLUS la date de run (uniforme = date pipeline, pas une fraîcheur
            # par ligne) ; on montre le millésime amont réel de la source quand il est renseigné.
            src = ln.get("source") or ""
            pdf.set_x(65)
            pdf.set_font("mono", size=6)
            pdf.set_text_color(*TXT_DIM)
            pdf.cell(0, 3.4, "  ".join(x for x in (src, ln.get("millesime_amont") or "") if x),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.8)

    if omises:
        # plafond 2 pages (C4) — jamais silencieux : le compteur dit ce qui n'est pas imprimé,
        # et M-P (P2-64) NOMME la/les section(s) tronquée(s) (souvent PROPRIO, la plus utile en
        # prospection) — le lecteur sait EXACTEMENT ce qui manque, pas juste un total.
        quoi = " · ".join(sections_omises)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.6,
                       f"… {omises} signal(aux) non imprimé(s) (format 2 pages)"
                       + (f" — section(s) : {quoi}" if quoi else "")
                       + ". La fiche écran porte la liste complète.", new_x="LMARGIN", new_y="NEXT")

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
                       f"construction {round(inp.get('cout_construction_m2') or 0):,} €/m² · "
                       f"marge & frais {inp.get('marge_frais_pct')} %.".replace(",", " "),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)
        pdf.set_font("grotesk", size=12)
        pdf.set_text_color(*MINT)
        pdf.cell(0, 6, f"Charge foncière supportable : {_e(cf.get('central'))}  "
                 f"(~ {round(cf.get('par_m2_terrain') or 0):,} €/m² terrain)".replace(",", " "),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 4, f"fourchette {_e(cf.get('bas'))} - {_e(cf.get('haut'))} · "
                 f"fiabilité prix : {calc.get('fiabilite')}", new_x="LMARGIN", new_y="NEXT")
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
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.4, "Calcul a partir de VOS hypotheses — estimation indicative, "
                       "ne vaut ni conseil ni engagement.", new_x="LMARGIN", new_y="NEXT")

    # ── M73-F — PLAN DE SITUATION (ortho) : image compositée par plan_situation (via build_situation_map,
    # point d'appel unique). Échelle + nord + millésime ortho (lu de data_sources) + source. Un échec de
    # carte NE MASQUE PAS le bloc : on écrit la RAISON (réseau ≠ hors emprise), jamais un cadre vide.
    import io as _io
    plan = fiche.get("plan_situation") or {}
    disp_w = pdf.w - 28
    # M73-G — anti-orphelin : on réserve la hauteur du BLOC ENTIER (titre + image + attribution) AVANT de
    # poser le titre. Fini le titre seul en bas de page, l'image sautant à la suivante (dette M73-F).
    besoin = (8 + disp_w * (plan["height"] / plan["width"]) + 9) if plan.get("ok") else 16
    if pdf.get_y() + besoin > pdf.h - 16:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("mono", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 5, "PLAN DE SITUATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINE)
    pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
    pdf.ln(1.4)
    if plan.get("ok"):
        disp_h = disp_w * (plan["height"] / plan["width"])
        y0 = pdf.get_y()
        pdf.image(_io.BytesIO(plan["jpeg"]), x=14, y=y0, w=disp_w, h=disp_h)
        mm_par_srcpx = disp_w / plan["width"]
        mpp = plan.get("metres_par_px")
        if mpp:                                          # ── barre d'échelle (bas-gauche), valeur ronde
            m_par_mm = mpp / mm_par_srcpx
            cible_m = 28 * m_par_mm                       # ~28 mm de barre
            p = 10 ** math.floor(math.log10(cible_m)) if cible_m > 0 else 1
            nice = next((f * p for f in (5, 2, 1) if f * p <= cible_m), p)
            bar_mm = nice / m_par_mm
            bx, by = 14 + 4, y0 + disp_h - 6
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(bx - 2, by - 3.4, bar_mm + 4, 6.4, style="F")
            pdf.set_draw_color(*TXT_HI)
            pdf.set_line_width(0.5)
            pdf.line(bx, by, bx + bar_mm, by)
            pdf.line(bx, by - 1.2, bx, by + 1.2)
            pdf.line(bx + bar_mm, by - 1.2, bx + bar_mm, by + 1.2)
            pdf.set_font("mono", size=6)
            pdf.set_text_color(*TXT_HI)
            pdf.set_xy(bx, by - 3.4)
            pdf.cell(bar_mm, 2.2, f"{round(nice)} m", align="C")
            pdf.set_line_width(0.2)
        pdf.set_fill_color(255, 255, 255)               # ── nord (haut-droite) : tuiles nord en haut
        pdf.rect(pdf.w - 14 - 8, y0 + 2, 6, 8, style="F")
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_HI)
        pdf.set_xy(pdf.w - 14 - 8, y0 + 2.2)
        pdf.cell(6, 3.4, "N", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(pdf.w - 14 - 8, y0 + 5.4)
        pdf.cell(6, 3.4, "^", align="C")
        pdf.set_y(y0 + disp_h + 1)
        pdf.set_font("inter", size=7)                    # M73-G — source/attribution ≥ 7 pt (technique)
        pdf.set_text_color(*TXT_DIM)
        mill = str(fiche.get("ortho_millesime") or "millésime non renseigné")
        pdf.multi_cell(pdf.w - 28, 3.2, f"Fond : {plan.get('attribution') or 'IGN — BD ORTHO'} · {mill}. "
                       "Contour parcellaire (cadastre) posé sur l'orthophotographie.",
                       new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4, f"Plan de situation indisponible — {plan.get('echec', 'raison inconnue')}. "
                       "Le reste du document n'est pas affecté.", new_x="LMARGIN", new_y="NEXT")

    # ── M73-E Volet B — COMPARABLES DVF : la table du premium, via marche_service (aucun appel DVF
    # direct). Chaque vente porte date/distance/surface/prix (requête les garantit) ; n + rayon dits ;
    # liste vide → on l'écrit, jamais un tableau vide. Rappel de méthode sous le tableau.
    cmp = fiche.get("comparables") or {}
    lst = cmp.get("comparables") or []
    if pdf.get_y() > pdf.h - 62:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("mono", size=7.5)
    pdf.set_text_color(*TXT_DIM)
    pdf.cell(0, 5, f"COMPARABLES DVF — {cmp.get('n', 0)} VENTE(S) A MOINS DE {cmp.get('rayon_m', '?')} M "
             f"({cmp.get('fenetre_ans', '?')} ANS)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*LINE)
    pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
    pdf.ln(1.2)
    if not lst:
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4, f"Aucune vente comparable dans le rayon retenu ({cmp.get('rayon_m', '?')} m).",
                       new_x="LMARGIN", new_y="NEXT")
    else:
        # MANDAT_DVF — effectif trop faible (< seuil du profil) : on le DIT, le tableau ne doit pas
        # paraître solide (mesuré : sous n≈8 la médiane oscille ±44 %). Grandeur affichée aussi.
        if cmp.get("effectif_suffisant") is False:
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*AMBER)
            pdf.multi_cell(pdf.w - 28, 4, f"Échantillon insuffisant ({cmp.get('n')} vente(s), minimum "
                           f"{cmp.get('seuil_effectif', 8)}) — comparables indicatifs, à lire avec prudence.",
                           new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.6)
        if cmp.get("grandeur"):
            pdf.set_font("inter", size=7)
            pdf.set_text_color(*TXT_DIM)
            pdf.multi_cell(pdf.w - 28, 3.4, f"Grandeur : {cmp['grandeur']}.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.4)
        # M73-G — chiffres alignés à DROITE (Date à gauche), unités présentes ; en-têtes assortis.
        cols = [("Date", 24, "L"), ("Distance", 20, "R"), ("Surface", 22, "R"),
                ("Prix", 30, "R"), ("€/m²", 22, "R")]
        pdf.set_x(14)
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT_DIM)
        for lbl, w, al in cols:
            pdf.cell(w, 4.4, lbl, new_x="RIGHT", new_y="TOP", align=al)
        pdf.ln(4.4)
        pdf.set_font("inter", size=8)
        pdf.set_text_color(*TXT)
        for c in lst:
            pdf.set_x(14)
            pdf.cell(24, 4.6, str(c.get("date") or "—"), new_x="RIGHT", new_y="TOP", align="L")
            pdf.cell(20, 4.6, f"{c.get('distance_m')} m", new_x="RIGHT", new_y="TOP", align="R")
            pdf.cell(22, 4.6, f"{c.get('surface_m2')} m²", new_x="RIGHT", new_y="TOP", align="R")
            pdf.cell(30, 4.6, f"{c.get('prix_eur'):,} €".replace(",", " "), new_x="RIGHT", new_y="TOP", align="R")
            pdf.cell(22, 4.6, str(c.get("prix_m2") or "—"), new_x="RIGHT", new_y="TOP", align="R")
            pdf.ln(4.6)
        pdf.ln(0.8)
        pdf.set_font("inter", size=8)                    # M73-G — réserve de méthode ≥ 8 pt (lisible)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4, "Les ventes récentes mettent 1 à 3 ans à apparaître dans DVF : "
                       "les niveaux les plus récents sont provisoires, le classement reste fiable.",
                       new_x="LMARGIN", new_y="NEXT")

    # ── M73-D — ASSAINISSEMENT + RÉHABILITATION : la forme NEUTRE partagée (blocs_documents), dessinée
    # en fpdf. Le premium POSE le MÊME texte que les 4 weasyprint (aucune reformulation — c'est la
    # divergence que M73-C/D réparent). Jamais recalculé, jamais masqué (l'absence est un état).
    # M73-G — habillage CARTOUCHE (maquette DA-PDF-v2 .carte/.chef/.past) : fond SURFACE, coin arrondi,
    # titre + pastille d'état colorée par le statut, lignes en 8 pt (réserves lisibles, jamais corps 6).
    from .blocs_documents import anc_bloc, rehab_bloc
    pad, lh = 4.0, 4.4
    inner_w = pdf.w - 28 - 2 * pad
    for bloc in (anc_bloc(fiche.get("anc")), rehab_bloc(fiche.get("mode_b"))):
        if not bloc:
            continue
        etat_col = (MINT if bloc["statut"] in ("source", "source_secteur")
                    else AMBER if bloc["statut"] in ("dispo", "trop_petit") else TXT_DIM)
        pdf.set_font("inter", size=8)
        body_h = sum(max(1, len(pdf.multi_cell(inner_w, lh, t, dry_run=True, output="LINES"))) * lh
                     for _, t in bloc["lignes"])
        card_h = 8.5 + body_h + 2 * pad
        if pdf.get_y() + card_h > pdf.h - 16:          # veuve/orpheline : la carte ne se coupe pas
            pdf.add_page()
        pdf.ln(2)
        y0 = pdf.get_y()
        pdf.set_fill_color(*SURFACE)
        pdf.rect(14, y0, pdf.w - 28, card_h, style="F", round_corners=True, corner_radius=2.4)
        pdf.set_xy(14 + pad, y0 + pad)                 # .chef : titre + pastille d'état
        pdf.set_font("grotesk", size=11)
        pdf.set_text_color(*TXT_HI)
        pdf.cell(inner_w * 0.62, 5, bloc["titre"])
        _chip(pdf, pdf.w - 14 - pad - (pdf.get_string_width(bloc["etat"]) + 6), y0 + pad + 0.2,
              bloc["etat"], etat_col)
        pdf.set_xy(14 + pad, y0 + pad + 8.5)
        for role, texte in bloc["lignes"]:
            pdf.set_x(14 + pad)
            pdf.set_font("inter", size=8)
            pdf.set_text_color(*(etat_col if role == "phrase_forte" else TXT))
            pdf.multi_cell(inner_w, lh, texte, new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(y0 + card_h + 1)

    # ── M73 §5 — « Ce que ce document ne peut pas dire » : matérialisation du 3e terme de la
    # doctrine (ce qui est absent + où le chercher). Source unique export_commun.limites_document.
    from .export_commun import LIMITES_TITRE, limites_document
    limites = limites_document("premium")
    if limites:
        if pdf.get_y() > pdf.h - 46:
            pdf.add_page()
        pdf.ln(2.5)
        pdf.set_font("mono", size=7.5)
        pdf.set_text_color(*TXT_DIM)
        pdf.cell(0, 5, LIMITES_TITRE.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LINE)
        pdf.line(14, pdf.get_y(), pdf.w - 14, pdf.get_y())
        pdf.ln(1.4)
        for absence, ou in limites:
            pdf.set_font("inter", size=7.6)
            pdf.set_text_color(*TXT)
            pdf.cell(72, 4, f"{absence}", new_x="RIGHT", new_y="TOP")
            pdf.set_font("inter", size=7.6)
            pdf.set_text_color(*TXT_MUT)
            pdf.set_x(88)
            pdf.multi_cell(pdf.w - 14 - 88, 4, f"→ {ou}", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    return bytes(out)
