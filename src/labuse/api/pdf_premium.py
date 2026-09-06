"""Export PDF de la fiche premium (Brique 3) — IMPRESSION : fond BLANC, encre noire.

Le dark est pour l'écran ; un dossier comité s'imprime. L'identité LABUSE reste par la typo
(Space Grotesk/Inter/JetBrains Mono) et la menthe en ACCENTS FINS (filets, puces, chip statut).
Rendu fpdf2 (pur Python) avec les fontes du design system (OFL, embarquées dans api/fonts/).
Contenu = DONNÉES PURES de la fiche (M124-A : plus de verdict/rang/score/complétude — l'analyse
LABUSE reste à l'écran) : en-tête (IDU/adresse/surface), bandeau événement, droits à bâtir (SDP),
contexte commune, lignes cascade TRACÉES par onglet, puis TOUS les blocs de données de la fiche
(M125-A, exhaustif : règlement/fraîcheur PLU, procédures, dispositifs, réseaux, marché, copro,
sources par-fiche…), footer non-garantie. Les données viennent de _q_v2_fiche — même source que l'écran.
"""
from __future__ import annotations

import math
import re
import statistics
from pathlib import Path

from fpdf import FPDF


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

# ── M126 — DA LABUSE v3 : palette de la refonte VISUELLE (apparence seule, contenu inchangé).
# Une seule couleur d'accent, le vert #4ADE80 : il ACCENTUE (filets, barres de titre, trait
# d'en-tête), il ne remplit JAMAIS du texte. Le reste est de l'encre grise/noire.
GREEN = (74, 222, 128)     # #4ADE80 — accent : trait d'en-tête, barre verticale de titre, filets
NUMBG = (230, 242, 232)    # #E6F2E8 — fond des 3 cases chiffres
TXT1 = (26, 35, 28)        # #1A231C — texte principal
TXT2 = (61, 82, 68)        # #3d5244 — texte secondaire (labels, colonne « point »)
SRC = (154, 168, 158)      # #9aa89e — sources / mentions / pied de page
FILET = (227, 232, 228)    # #e3e8e4 — filet 0.5 px entre les lignes de tableau

# M-P (P2-62) : la table STATUT (matrice Q/A, avec `a_surveiller`) est SUPPRIMÉE — matrice éteinte
# (M37), plus jamais un verdict matriciel dans un document client. Le verdict d'en-tête vient du
# tier v2 (étage 0 prime) ; sans run v2 → libellé neutre « Classement historique ».
# M-P (P2-63) : un PDF circule plus loin qu'une page web — on exclut la donnée personnelle sensible
# `age_dirigeant` (âge d'un dirigeant), comme share_public (COUCHES_PROPRIETAIRE). L'onglet PROPRIO
# reste imprimé (document abonné, derrière auth, PM publique DGFiP) ; seule cette ligne est retirée.
COUCHES_EXCLUES = {"age_dirigeant"}

ONGLETS = [("regles", "RÈGLES"), ("risques", "RISQUES"), ("marche", "MARCHÉ"), ("proprio", "PROPRIO")]


class _Pdf(FPDF):
    def header(self):
        # M126 — l'en-tête COMPLET (logo + IDU + trait vert) est en page 1, dans le corps. Sur les
        # pages de continuation : seulement un filet vert FIN, discret, en tête.
        if self.page_no() > 1:
            self.set_draw_color(*GREEN)
            self.set_line_width(0.3)
            self.line(14, 9, self.w - 14, 9)
            self.set_line_width(0.2)
        self.set_y(12)

    def footer(self):
        # M126 — pied de page sur UNE SEULE ligne (~9 px), gris SRC : mention + sources abrégées +
        # pagination. Garde le disclaimer légal AU MOT PRÈS (obligation M6). Ne passe plus par
        # export_commun.pied_de_page_pdf (4 lignes, partagé avec les autres docs — laissé intact).
        from .export_commun import DISCLAIMER_CU
        fam = "inter" if "inter" in getattr(self, "fonts", {}) else "helvetica"
        self.set_y(-11)
        self.set_draw_color(*FILET)
        self.set_line_width(0.2)
        self.line(14, self.get_y() - 1.2, self.w - 14, self.get_y() - 1.2)
        self.set_font(fam, size=6.5)
        self.set_text_color(*SRC)
        ligne = (f"Estimations indicatives — {DISCLAIMER_CU}  ·  Sources : DGFiP · IGN · Géorisques · "
                 f"INSEE · SDES · BAN  ·  LABUSE · page {self.page_no()}/{{nb}}")
        # si ça déborde de la largeur utile, on rogne les SOURCES (jamais le disclaimer)
        while self.get_string_width(ligne) > self.w - 28 and " · " in ligne:
            ligne = ligne.replace(" · BAN", "", 1).replace(" · SDES", "", 1).replace(" · INSEE", "", 1)
            if self.get_string_width(ligne) <= self.w - 28:
                break
            ligne = ligne.replace(" · Géorisques", "", 1).replace(" · IGN", "", 1)
        self.cell(0, 4, ligne, align="C")


#: silhouette officielle (path labuse.immo, échantillonné) — polygone rempli
_LOGO_PTS = [(2.0,15.0),(8.9,14.4),(15.7,14.0),(22.3,13.7),(28.8,13.5),(35.1,13.5),(41.2,13.5),(47.2,13.6),(53.0,13.9),(58.7,14.2),(64.1,14.7),(69.4,15.2),(74.5,15.8),(79.4,16.4),(84.1,17.1),(88.6,17.9),(93.0,18.8),(97.1,19.7),(101.0,20.6),(104.7,21.6),(108.2,22.6),(111.5,23.7),(114.5,24.8),(117.4,25.9),(120.0,27.0),(122.6,25.9),(125.5,24.8),(128.5,23.7),(131.8,22.6),(135.3,21.6),(139.0,20.6),(142.9,19.7),(147.0,18.8),(151.4,17.9),(155.9,17.1),(160.6,16.4),(165.5,15.8),(170.6,15.2),(175.9,14.7),(181.3,14.2),(187.0,13.9),(192.8,13.6),(198.8,13.5),(204.9,13.5),(211.2,13.5),(217.7,13.7),(224.3,14.0),(231.1,14.4),(238.0,15.0),(233.5,16.7),(228.9,18.4),(224.3,20.1),(219.7,21.7),(215.1,23.3),(210.5,24.9),(205.9,26.4),(201.3,27.9),(196.7,29.4),(192.1,30.8),(187.6,32.2),(183.1,33.5),(178.7,34.8),(174.3,36.0),(170.0,37.2),(165.7,38.4),(161.5,39.5),(157.4,40.6),(153.4,41.6),(149.5,42.6),(145.7,43.5),(142.0,44.4),(138.4,45.2),(135.0,46.0),(134.0,46.4),(133.1,46.8),(132.1,47.2),(131.2,47.6),(130.4,48.0),(129.6,48.5),(128.8,48.9),(128.0,49.4),(127.3,49.9),(126.6,50.4),(125.9,50.9),(125.2,51.5),(124.6,52.1),(124.1,52.7),(123.5,53.3),(123.0,53.9),(122.5,54.6),(122.1,55.3),(121.6,56.0),(121.2,56.7),(120.9,57.5),(120.6,58.3),(120.3,59.1),(120.0,60.0),(119.7,59.1),(119.4,58.3),(119.1,57.5),(118.8,56.7),(118.4,56.0),(117.9,55.3),(117.5,54.6),(117.0,53.9),(116.5,53.3),(115.9,52.7),(115.4,52.1),(114.8,51.5),(114.1,50.9),(113.4,50.4),(112.7,49.9),(112.0,49.4),(111.2,48.9),(110.4,48.5),(109.6,48.0),(108.8,47.6),(107.9,47.2),(106.9,46.8),(106.0,46.4),(105.0,46.0),(101.6,45.2),(98.0,44.4),(94.3,43.5),(90.5,42.6),(86.6,41.6),(82.6,40.6),(78.5,39.5),(74.3,38.4),(70.0,37.2),(65.7,36.0),(61.3,34.8),(56.9,33.5),(52.4,32.2),(47.9,30.8),(43.3,29.4),(38.7,27.9),(34.1,26.4),(29.5,24.9),(24.9,23.3),(20.3,21.7),(15.7,20.1),(11.1,18.4),(6.5,16.7),(2.0,15.0)]


def _logo(pdf: FPDF, x: float, y: float, w: float) -> None:
    k = w / 240.0
    pdf.set_fill_color(*GREEN)                       # M126 — vert canonique #4ADE80
    with pdf.new_path() as path:
        path.style.fill_color = "#4ADE80"
        path.style.stroke_width = 0
        path.move_to(x + 2 * k, y + 15 * k)
        for px, py in _LOGO_PTS:
            path.line_to(x + px * k, y + py * k)
        path.close()


def _chip(pdf: _Pdf, x: float, y: float, label: str, color: tuple) -> float:
    pdf.set_font("inter", size=7.5)
    w = pdf.get_string_width(label) + 6
    pdf.set_fill_color(*(MINT_SOFT if color == GREEN else
                         RED_SOFT if color == RED else (238, 241, 239)))
    pdf.rect(x, y, w, 5.4, style="F", round_corners=True, corner_radius=2.6)
    pdf.set_text_color(*color)
    pdf.set_xy(x + 3, y + 0.7)
    pdf.cell(w - 6, 4, label)
    return w


def _signaux(n: int) -> str:
    """M124-C10 — accord singulier/pluriel : « 1 signal » / « 14 signaux » (fin de « signal(aux) »)."""
    return f"{n} signal" if n == 1 else f"{n} signaux"


def _indispo(pdf: _Pdf, titre: str) -> None:
    """M125 (boussole) — bloc « donnée indisponible — erreur technique » : une PANNE d'un builder de
    fiche ne s'imprime JAMAIS en absence sourcée. Rendu en clair (ambre), jamais un blanc muet.
    M126 — titre de section unifié (barre verte + petites capitales)."""
    _titre_section(pdf, titre)
    pdf.set_font("inter", size=7.8)
    pdf.set_text_color(*AMBER)
    pdf.multi_cell(pdf.w - 28, 3.8, "Donnée indisponible — erreur technique. Le calcul n'a pas abouti "
                   "(incident) ; ce n'est pas une absence de donnée.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.0)


def _is_indispo(bloc) -> bool:
    """Vrai si un bloc de fiche porte l'état PANNE (M125) — à tester AVANT de lire ses champs."""
    return isinstance(bloc, dict) and bool(bloc.get("indisponible"))


def _section(pdf: _Pdf, titre: str, lignes, source: str | None = None) -> None:
    """M125-A — SECTION sobre réutilisable : titre mono + lignes inter + ligne source/millésime dim.
    `lignes` : itérable ; les valeurs vides sont ignorées. Rien n'est imprimé si tout est vide.
    Saut de page anti-orphelin quand on est trop bas (le titre ne reste jamais seul en pied)."""
    lignes = [str(x) for x in lignes if x]
    if not lignes:
        return
    _titre_section(pdf, titre)                       # M126 — barre verte + petites capitales
    pdf.set_font("inter", size=7.8)
    pdf.set_text_color(*TXT1)
    for ln in lignes:
        pdf.multi_cell(pdf.w - 28, 4.0, ln, new_x="LMARGIN", new_y="NEXT")
    if source:
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*SRC)
        pdf.multi_cell(pdf.w - 28, 3.4, source, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.0)


def _millesime(m) -> str:
    """M125/EXPORTS-1 (6.4) — fraîcheur HONNÊTE : le vrai millésime (éventuellement composé —
    sentinelle ou date d'ingestion ÉTIQUETÉE) ; sans aucune date nulle part, cellule MASQUÉE
    (chaîne vide), plus le pavé « millésime non renseigné »."""
    return str(m) if m else ""


def _titre_section(pdf: _Pdf, texte: str) -> None:
    """M126 — titre de section : petites capitales à lettrage espacé + barre verticale verte 3 px à
    gauche (l'accent, jamais du remplissage de texte). Remplace les anciens titres tout en mono."""
    if pdf.get_y() > pdf.h - 22:                     # anti-orphelin : le titre ne reste pas seul en pied
        pdf.add_page()
    pdf.ln(1.6)
    y = pdf.get_y()
    pdf.set_fill_color(*GREEN)
    pdf.rect(14, y + 0.3, 1.1, 4.0, style="F")       # barre verticale ~3 px
    pdf.set_xy(17.5, y)
    pdf.set_font("grotesk", size=8)
    pdf.set_text_color(*TXT1)
    pdf.set_char_spacing(0.6)                         # lettrage espacé (petites capitales)
    pdf.cell(0, 4.6, texte.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_char_spacing(0)
    pdf.ln(1.2)


#: M126 pt.6 — colonnes du tableau de signaux : point 32 % | valeur | source 18 %.
_COL_POINT = 0.32
_COL_SRC = 0.18

#: M126-B (B1b) — nom COURT du producteur pour la colonne source (le millésime détaillé vit dans
#: « SOURCES UTILISÉES SUR CETTE FICHE » en fin de document). Priorité au 1er producteur rencontré.
_PRODUCTEURS = [
    ("Géorisques", "Géorisques"), ("Cerema", "Cerema"), ("GéoLittoral", "Cerema"), ("INPN", "INPN"),
    ("DEAL", "DEAL"), ("ONF", "ONF"), ("DGFiP", "DGFiP"), ("DVF", "DGFiP"), ("INPI", "INPI"),
    ("BODACC", "BODACC"), ("SDES", "SDES"), ("Sitadel", "SDES"), ("ADEME", "ADEME"), ("BRGM", "BRGM"),
    ("Filosofi", "INSEE"), ("INSEE", "INSEE"), ("RPLS", "RPLS"), ("Région", "Région"),
    ("regionreunion", "Région"), ("Overpass", "OSM"), ("OpenStreetMap", "OSM"), ("OSM", "OSM"),
    ("Base Adresse", "BAN"), ("BAN", "BAN"), ("DINUM", "BAN"),
    # M126-C (C2) — « ABF / Monuments » est une couche, pas un producteur : le vrai est la base
    # Mérimée (Ministère de la Culture).
    ("Mérimée", "Mérimée"), ("Monuments", "Mérimée"), ("ABF", "Mérimée"),
    ("API Carto", "IGN"), ("GPU", "IGN"), ("BD TOPO", "IGN"), ("BD CARTO", "IGN"),
    ("RGE ALTI", "IGN"), ("RPG", "IGN"), ("IGN", "IGN"),
]


def _source_courte(source: str | None) -> str:
    """M126-B (B1b) — abrège la source au NOM DU PRODUCTEUR (le premier rencontré), SANS millésime.
    Le détail complet (millésime, jeu) reste dans « SOURCES UTILISÉES SUR CETTE FICHE ». Recherche
    au MOT ENTIER (\\b) : « BAN » ne doit pas matcher « urBANisme », « IGN » pas « désIGNé »…"""
    if not source:
        return ""
    trouve = []
    for k, court in _PRODUCTEURS:
        m = re.search(r"\b" + re.escape(k) + r"\b", source, re.IGNORECASE)
        if m:
            trouve.append((m.start(), court))
    # M126-C (C2) — jamais un NOM DE COUCHE déguisé en producteur : à défaut de producteur connu,
    # colonne source VIDE (mieux que « ABF / Monuments » ou une URL).
    return min(trouve)[1] if trouve else ""


def _ligne_signal(pdf: _Pdf, point: str, valeur: str, source: str = "") -> None:
    """M126 pt.6/7 — une ligne de signal en 3 COLONNES : point (32 %, TXT2) | valeur (TXT1) |
    source (18 %, aligné à droite, ~9 px SRC). AUCUNE troncature : chaque colonne passe à la ligne
    (multi_cell) ; la hauteur de la ligne = colonne la plus haute. Filet 0.5 px sous la ligne."""
    x0, full = 14.0, pdf.w - 28
    wp, ws = full * _COL_POINT, full * _COL_SRC
    wv = full - wp - ws
    if pdf.get_y() > pdf.h - 18:
        pdf.add_page()
    y = pdf.get_y()
    pdf.set_font("inter", size=7.6)
    hp = len(pdf.multi_cell(wp - 1, 3.7, point or "", dry_run=True, output="LINES"))
    hv = len(pdf.multi_cell(wv - 2, 3.7, valeur or "", dry_run=True, output="LINES"))
    pdf.set_font("inter", size=6.5)
    hs = len(pdf.multi_cell(ws, 3.4, source or "", dry_run=True, output="LINES"))
    h = max(hp, hv, 1) * 3.7
    h = max(h, hs * 3.4, 4.0)
    pdf.set_xy(x0, y)
    pdf.set_font("inter", size=7.6)
    pdf.set_text_color(*TXT2)
    pdf.multi_cell(wp - 1, 3.7, point or "", align="L")
    pdf.set_xy(x0 + wp, y)
    pdf.set_text_color(*TXT1)
    pdf.multi_cell(wv - 2, 3.7, valeur or "", align="L")
    if source:
        pdf.set_xy(x0 + wp + wv, y)
        pdf.set_font("inter", size=6.5)
        pdf.set_text_color(*SRC)
        pdf.multi_cell(ws, 3.4, source, align="R")
    yb = y + h + 1.3
    pdf.set_draw_color(*FILET)
    pdf.set_line_width(0.2)
    pdf.line(x0, yb, pdf.w - 14, yb)
    pdf.set_y(yb + 0.7)


# M126-C — le regroupement « rien à signaler » repose sur le CONTENU du constat, JAMAIS sur la couche
# ni sur le résultat/score (le verdict PASS d'un moteur peut porter une info : « Pente forte », « Bâti
# à vérifier », une prescription…). Règle (boussole : pas de faux négatif) :
#   • RESTE dans son onglet tout constat PORTEUR — valeur qualifiée/graduée (forte/modérée/élevée/
#     faible…), prescription/contrainte (imposée, rétention, recul…), incertitude (à vérifier/à
#     instruire, présence, probable/possible), exclusion, ou tout constat POSITIF/présent ;
#   • REGROUPE seulement l'ABSENCE AVÉRÉE — le constat commence par « Hors…/Aucun(e)…/Pas une/de…/
#     Sans objet », OU une donnée absente (« … non couverte/disponible/ingérée/renseignée/recensée »),
#     OU « hors îlot » / « aucune contrainte … déduite ».
# M126-D — l'ABSENCE EN TÊTE prime : un constat qui COMMENCE par « Hors… / Aucun(e)… / Pas une/de… /
# Sans objet » est une absence avérée, même s'il contient plus loin un mot qui ressemble à une
# prescription (« Hors zone de RECUL du trait de côte » : « recul » ne la rend pas porteuse). Vérifié :
# TOUS les constats débutant par ces mots sont de vraies absences (aucun « Aucun accès — enclavé »).
_DATAGAP_RX = re.compile(r"\bnon (couvert|disponible|ingér|renseign|recens)\w*", re.IGNORECASE)
_ABSENCE_DEBUT_RX = re.compile(r"^\s*(hors\b|aucun|sans objet|pas une |pas de |non concern)", re.IGNORECASE)


def _sans_signal(ln: dict) -> bool:
    """M126-C/D — vrai UNIQUEMENT si le CONTENU du constat est une absence avérée (regroupé en fin de
    document) : absence EN TÊTE (« Hors… / Aucun… / Pas une… / Sans objet »), OU donnée absente
    (« … non couverte/disponible/ingérée/renseignée/recensée »), OU « hors îlot » / « aucune contrainte
    … déduite ». Tout le reste (valeur qualifiée, prescription, incertitude, finding) RESTE dans l'onglet."""
    d = (ln.get("detail") or "").strip()
    if not d:
        return True
    dl = d.lower()
    return bool(_ABSENCE_DEBUT_RX.search(d) or _DATAGAP_RX.search(dl)
                or "hors îlot" in dl or ("aucune contrainte" in dl and "déduite" in dl))


def _bloc_plan(pdf: _Pdf, fiche: dict) -> None:
    """M126 pt.4 — PLAN DE SITUATION, remonté en PAGE 1 (rendu identique, seule la position change).
    Échelle + nord + millésime ortho + attribution. Un échec de carte n'affiche jamais un cadre vide."""
    import io as _io
    plan = fiche.get("plan_situation") or {}
    disp_w = pdf.w - 28
    _titre_section(pdf, "Plan de situation")
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
            pdf.set_draw_color(*TXT1)
            pdf.set_line_width(0.5)
            pdf.line(bx, by, bx + bar_mm, by)
            pdf.line(bx, by - 1.2, bx, by + 1.2)
            pdf.line(bx + bar_mm, by - 1.2, bx + bar_mm, by + 1.2)
            pdf.set_font("mono", size=6)
            pdf.set_text_color(*TXT1)
            pdf.set_xy(bx, by - 3.4)
            pdf.cell(bar_mm, 2.2, f"{round(nice)} m", align="C")
            pdf.set_line_width(0.2)
        pdf.set_fill_color(255, 255, 255)               # ── nord (haut-droite)
        pdf.rect(pdf.w - 14 - 8, y0 + 2, 6, 8, style="F")
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*TXT1)
        pdf.set_xy(pdf.w - 14 - 8, y0 + 2.2)
        pdf.cell(6, 3.4, "N", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(pdf.w - 14 - 8, y0 + 5.4)
        pdf.cell(6, 3.4, "^", align="C")
        pdf.set_y(y0 + disp_h + 1)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*SRC)
        mill = str(fiche.get("ortho_millesime") or "millésime non renseigné")
        pdf.multi_cell(pdf.w - 28, 3.2, f"Fond : {plan.get('attribution') or 'IGN — BD ORTHO'} · {mill}. "
                       "Contour parcellaire (cadastre) posé sur l'orthophotographie.",
                       new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4, f"Plan de situation indisponible — {plan.get('echec', 'raison inconnue')}. "
                       "Le reste du document n'est pas affecté.", new_x="LMARGIN", new_y="NEXT")


def render_fiche_pdf(fiche: dict) -> bytes:
    pdf = _Pdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)   # M126 — pied de page sur UNE seule ligne
    pdf.add_font("inter", fname=str(FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("grotesk", fname=str(FONTS / "SpaceGrotesk-Bold.ttf"))
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    # ── EXPORTS-1 (1.3, arbitrage Q1) — le prix d'en-tête = `sector_price` PARCELLE (servi dans
    #    fiche["prix_ancien"], point d'appel unique marche_service), plus jamais la première
    #    médiane du secteur cadastral (3 804 vs 3 818 de l'audit A1). Repli : médiane des
    #    comparables affichés (mêmes ventes que la table), jamais un chiffre d'une 3e source.
    _rp0 = fiche.get("reglement_plu")
    _zones0 = _rp0.get("zones") if isinstance(_rp0, dict) else None
    zone_plu = ((_zones0[0].get("zone") if _zones0 and isinstance(_zones0[0], dict) else None) or "n/d")
    prix_sect = "n/d"
    _pa = fiche.get("prix_ancien")
    if isinstance(_pa, dict) and _pa.get("fiable") and _pa.get("median") is not None:
        prix_sect = f"{int(_pa['median']):,} €/m²".replace(",", " ")
    if prix_sect == "n/d":
        _cps = [c["prix_m2"] for c in ((fiche.get("comparables") or {}).get("comparables") or [])
                if isinstance(c.get("prix_m2"), (int, float)) and c["prix_m2"] > 0]
        if _cps:
            prix_sect = f"{int(statistics.median(_cps)):,} €/m²".replace(",", " ")

    # ── M126 pt.1 — EN-TÊTE : logo + wordmark LABUSE à gauche, IDU + date à droite, trait vert 3 px
    #    dessous. Plus de tagline « Radar foncier premium ».
    from datetime import date as _date
    y_top = pdf.get_y()
    _logo(pdf, 14, y_top + 1.2, 11)
    pdf.set_xy(27, y_top + 1.4)
    pdf.set_font("grotesk", size=14)
    pdf.set_text_color(*TXT1)
    pdf.set_char_spacing(1.4)
    pdf.cell(60, 6, "LABUSE")
    pdf.set_char_spacing(0)
    pdf.set_xy(pdf.w - 14 - 74, y_top)
    pdf.set_font("mono", size=9.5)
    pdf.set_text_color(*TXT1)
    pdf.cell(74, 4.8, fiche["idu"], align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(pdf.w - 14 - 74, y_top + 5.0)
    pdf.set_font("inter", size=8)
    pdf.set_text_color(*SRC)
    pdf.cell(74, 4, f"généré le {_date.today().strftime('%d/%m/%Y')}", align="R")
    y_line = y_top + 11.5
    pdf.set_draw_color(*GREEN)
    pdf.set_line_width(1.0)                           # ~3 px
    pdf.line(14, y_line, pdf.w - 14, y_line)
    pdf.set_line_width(0.2)
    pdf.set_y(y_line + 4)

    # ── Bandeau événement (héros) — C5 : il raconte SON histoire en une phrase
    if fiche.get("evenement") == "rouge":
        pm = (fiche.get("proprietaire_moral") or {}).get("denomination")
        # M124-A/B — FAIT public, sans cadrage de scoring : « priorité par événement », « force
        # chaude », « l'urgence prime » et « doctrine bascule » sont RETIRÉS (le PDF porte la donnée,
        # pas l'analyse LABUSE). Reste l'information vérifiable : procédure collective + source BODACC.
        detail = (f"Le propriétaire{f' ({pm})' if pm else ''} fait l'objet d'une procédure "
                  f"collective — {fiche.get('evenement_detail') or 'procédure ouverte'}. "
                  "Source : BODACC (annonces commerciales).")
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
        pdf.cell(0, 4, "● PROCÉDURE COLLECTIVE (BODACC)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(18, y + 7.2)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(120, 52, 44)
        pdf.multi_cell(pdf.w - 36, 3.6, detail)
        pdf.set_y(y + h + 3)

    # ── M126 pt.2 — IDENTITÉ : adresse (15 px, TXT1) ; dessous surface · Zone PLU · coordonnées
    #    (12 px gris). L'IDU n'est plus le gros titre (il est dans l'en-tête, à droite). La commune
    #    reste portée par la section « CONTEXTE COMMUNE » plus bas (aucune donnée perdue).
    adr = fiche.get("adresse")
    pdf.set_font("inter", size=11)
    pdf.set_text_color(*(TXT1 if adr else SRC))
    pdf.cell(0, 6, adr or "Adresse non disponible", new_x="LMARGIN", new_y="NEXT")
    surf = f"{fiche['surface_m2']:,} m²".replace(",", " ") if fiche.get("surface_m2") else "surface n/d"
    lon, lat = fiche.get("coords", [None, None])
    pdf.set_font("inter", size=8.5)
    pdf.set_text_color(*SRC)
    meta = f"{surf}  ·  Zone PLU {zone_plu}"
    if lat is not None and lon is not None:
        meta += f"  ·  {lat}, {lon}"
    pdf.cell(0, 4.6, meta, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2.4)

    # ── M126 pt.3 — BANDEAU 3 CHIFFRES (cases fond #E6F2E8) : Surface · Zone PLU · Prix secteur.
    #    Toutes ces valeurs sont DÉJÀ présentes dans le document — répétition d'en-tête, pas d'ajout.
    _cases = [("Surface", surf), ("Zone PLU", str(zone_plu)), ("Prix secteur", prix_sect)]
    _gap = 8.0
    _cw = (pdf.w - 28 - 2 * _gap) / 3
    _yb = pdf.get_y()
    for _i, (_lab, _val) in enumerate(_cases):
        _cx = 14 + _i * (_cw + _gap)
        pdf.set_fill_color(*NUMBG)
        pdf.rect(_cx, _yb, _cw, 11.6, style="F")
        pdf.set_xy(_cx + 3, _yb + 1.9)
        pdf.set_font("inter", size=6.5)
        pdf.set_text_color(*TXT2)
        pdf.set_char_spacing(0.7)
        pdf.cell(_cw - 6, 3, _lab.upper())
        pdf.set_char_spacing(0)
        pdf.set_xy(_cx + 3, _yb + 5.7)
        pdf.set_font("grotesk", size=10)
        pdf.set_text_color(*TXT1)
        pdf.cell(_cw - 6, 4.6, _val)
    pdf.set_y(_yb + 11.6 + 3)

    # ── M126 pt.4 — PLAN DE SITUATION remonté en PAGE 1, juste sous le bandeau.
    _bloc_plan(pdf, fiche)

    # ── M124-A2 — L'INDICE DE COMPLÉTUDE (« Confiance des données 90/100 ») est RETIRÉ : c'est une
    # méta d'analyse, pas une donnée de la parcelle. Le PDF ne porte plus de score, complétude comprise.

    # ── M124-B7 — DROITS À BÂTIR (SDP) : UN SEUL message hiérarchisé. Fin de la contradiction
    # « SDP résiduelle 0 m² / rien à construire » vs « 1175 m² gisement 37% » vs « surélévation
    # ~4,7 m » : le « 1175 m² » était la SURFACE de la parcelle (fait, gardé en couche « Surface »),
    # jamais de la SDP. Ici, la seule vérité à bâtir : la SDP RÉSIDUELLE au sol, puis — à défaut —
    # la surélévation, seule marge réelle. Les niveaux et le % de scoring de l'ancien « Potentiel de
    # transformation » (Task A) sont RETIRÉS ; `pt` ne sert que de source de FAITS (SDP m², hauteur).
    pt = fiche.get("potentiel_transformation") or {}
    constructible = False   # C9 — pilote l'affichage du rappel RTAA (faux par défaut / si panne)
    if _is_indispo(pt):
        _indispo(pdf, "DROITS À BÂTIR (SDP)")   # M125 — panne ≠ absence ; RTAA restera masqué
        sdp_res = surel = marge_h = None
    else:
        sdp_res = pt.get("sdp_residuelle_m2")
        surel = bool(pt.get("surelevation_possible"))
        marge_h = pt.get("hauteur_marge_m")
        constructible = bool((sdp_res or 0) > 0 or surel)
    if not _is_indispo(pt) and pt and (sdp_res is not None or surel):
        _titre_section(pdf, "Droits à bâtir (SDP)")
        pdf.set_font("inter", size=7.8)
        pdf.set_text_color(*TXT1)
        if sdp_res and sdp_res > 0:
            msg = f"SDP résiduelle estimée : ~{sdp_res:,} m² au sol.".replace(",", " ")
            if surel:
                msg += " Surélévation également possible" + (f" (marge ~{marge_h} m)." if marge_h else ".")
        elif surel:
            msg = ("Aucun droit à bâtir résiduel au sol (densité autorisée atteinte). "
                   "Seule marge : surélévation" + (f" (marge ~{marge_h} m)." if marge_h else " possible."))
        else:
            msg = "Aucun droit à bâtir résiduel au sol (densité autorisée atteinte)."
        pdf.multi_cell(pdf.w - 28, 3.8, msg, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*TXT_DIM)
        pdf.multi_cell(pdf.w - 28, 3.2, "Estimation (règles PLU calibrées x bâti BD TOPO) — "
                       "indicative, à confirmer au règlement et par un CU.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.2)

    # ── CONTEXTE COMMUNE (mandat promotrice) — SRU · QPV/ANRU · marché, sourcé
    ctx = fiche.get("contexte_commune") or {}
    if ctx:
        _titre_section(pdf, f"Contexte commune — {fiche.get('commune', '')}")
        pdf.set_font("inter", size=7.8)
        pdf.set_text_color(*TXT1)
        lignes = []
        sru = ctx.get("sru")
        if sru:
            st = {"carencee": "CARENCÉE", "deficitaire": "déficitaire",
                  "exemptee": "exemptée 2023-2025", "conforme": "conforme"}.get(sru["statut"], sru["statut"])
            lignes.append(f"SRU : {sru['taux_lls']} % de logements sociaux — objectif {sru['objectif_pct']} % — {st}"
                          + (f" (prélèvement 2025 : {int(sru['prelevement_eur']):,} €)".replace(",", " ")
                             if (sru.get("prelevement_eur") or 0) > 0 else ""))
        qpv, anru = ctx.get("qpv") or [], ctx.get("anru") or []
        npnru = (f" · NPNRU : {', '.join(a['nom'] for a in anru)} (intérêt national)"
                 if anru else " · aucun périmètre NPNRU")
        # M125-2 — anru CONSOLIDÉ ici (pas de bloc séparé) : la position PARCELLAIRE (dans/adjacente
        # au périmètre NPNRU) enrichit la ligne commune, au lieu d'un champ `anru` rendu nulle part.
        pa = fiche.get("anru") or {}
        if pa.get("quartier"):
            pos = "dans le" if pa.get("position") == "dans" else "adjacente au"
            npnru += f" · cette parcelle est {pos} périmètre « {pa['quartier']} »"
        lignes.append(f"Politique de la ville : {len(qpv)} QPV (génération 2024)" + npnru)
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
                         "INSEE RP 2023 — contexte informatif, sans effet sur le verdict.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── RTAA DOM (5bis) — rappel réglementaire de conception (vérifié Légifrance)
    # M124-C9 — n'a de sens que si la parcelle a un POTENTIEL CONSTRUCTIF (RTAA = construction neuve
    # de logements). Sans droits à bâtir résiduels ni surélévation, ce rappel serait du bruit → masqué.
    rtaa = fiche.get("rtaa") or {}
    if rtaa and constructible:
        _titre_section(pdf, "RTAA DOM — rappel réglementaire (construction neuve de logements)")
        pdf.set_font("inter", size=7.2)
        pdf.set_text_color(*TXT1)
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
        "safer": "Parcelle déclarée agricole (RPG)",
        "sar": "Potentiel foncier Région (indicatif)", "surface": "Surface parcelle",
        "parc_national": "Parc national", "foret_publique": "Forêt publique",
        "cinquante_pas": "50 pas géométriques", "sup": "Servitudes (SUP)",
        "risques": "Risques PPR", "sol_pollue": "Sols pollués", "cavite": "Cavités",
        "icpe": "ICPE", "mvt": "Mouvement de terrain", "pente": "Pente", "ravine": "Ravines",
        "trait_de_cote": "Indicateur d'érosion côtière (Cerema)", "abf": "ABF / Monuments",
        "ens": "Espace protégé réglementaire (INPN)", "eau": "Eau", "bruit_route": "Bruit routier",
        "dvf": "Marché DVF", "sitadel": "Permis SITADEL", "amenites": "Commerces et services à proximité",
        "potentiel_foncier_region": "Potentiel foncier Région",
        "ocs_ge": "Occupation du sol (BD CARTO V5 — grain grossier)",
        "friche": "Friche", "acces": "Accès voirie", "proprietaire": "Propriétaire",
        "bodacc": "BODACC", "assemblage": "Assemblage", "bati": "Bâti",
        "osm_faux_positif": "Contrôle géométrique OSM",     # M73 D — clé brute rendue avant
    }

    def _layer_label(key: str) -> str:
        # M73 D — jamais la clé technique brute : à défaut de libellé mappé, on humanise
        # (underscores → espaces, capitale) plutôt que d'imprimer « osm_faux_positif ».
        return _LAYER_LABEL.get(key) or key.replace("_", " ").capitalize()
    def _src_ligne(ln: dict) -> str:
        # M126-B (B1b) — nom court du producteur seul ; le millésime vit dans « SOURCES UTILISÉES ».
        return _source_courte(ln.get("source"))

    def _detail_ligne(ln: dict) -> str:
        # M54-AB C7 : la pente client = RGE ALTI (parcel_terrain), MÊME source que dossier/flash.
        if ln["layer"] == "pente" and fiche.get("pente_terrain"):
            return f"Pente {fiche['pente_terrain']} — RGE ALTI 5 m, non éliminatoire."
        return ln["detail"] or ""

    sans_signal_all: list = []   # M126 pt.9 — signaux « rien à signaler », REGROUPÉS en fin de document
    for key, titre in ONGLETS:
        # M-P (P2-63) : `age_dirigeant` exclue du PDF ; M124-B7 : `residuel_socle` vit dans « DROITS À BÂTIR ».
        lines = [ln for ln in fiche["lines"]
                 if ln["onglet"] == key and ln["layer"] not in COUCHES_EXCLUES
                 and ln["layer"] != "residuel_socle"]
        if not lines:
            continue
        # M126 pt.9 — on sépare les signaux PORTEURS d'information de ceux « rien à signaler ».
        porteurs = [ln for ln in lines if not _sans_signal(ln)]
        sans = [ln for ln in lines if _sans_signal(ln)]
        sans_signal_all += [(TITRES_M19.get(key, titre), ln) for ln in sans]
        _titre_section(pdf, TITRES_M19.get(key, titre))
        # M126 pt.6/7 — tableau 3 colonnes (point | valeur | source), sans aucune troncature.
        for ln in porteurs:
            _ligne_signal(pdf, _layer_label(ln["layer"]), _detail_ligne(ln), _src_ligne(ln))
        if sans:                                       # M126 pt.9 — le compte des regroupés est DIT ici
            pdf.set_font("inter", size=7)
            pdf.set_text_color(*SRC)
            pdf.multi_cell(pdf.w - 28, 3.6,
                           f"+ {len(sans)} sans signal, regroupé{'s' if len(sans) > 1 else ''} "
                           "en fin de document.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.6)

    # ═══ M125-A — DONNÉES EXHAUSTIVES : tout champ de DONNÉES de la fiche écran est porté au PDF ;
    #     seule l'ANALYSE LABUSE (verdict/rang/score/pourquoi/complétude/niveaux) reste exclue (M124-A1).
    #     Blocs sobres via _section ; PANNE (_is_indispo) rendue en clair ; fraîcheur honnête (_millesime).
    pdf.ln(1)

    # ── RÈGLES D'URBANISME ───────────────────────────────────────────────────────────────────
    rp = fiche.get("reglement_plu")
    if _is_indispo(rp):
        _indispo(pdf, "RÈGLEMENT PLU PAR ZONE")
    elif rp and rp.get("zones"):
        lignes = []
        for z in rp["zones"]:
            zcode = z.get("zone") or z.get("libelle") or "zone"
            entete = (f"Zone « {zcode} »"
                      + (f" — {z['libelle']}" if z.get("libelle") and z.get("libelle") != zcode else ""))
            arts = z.get("articles")
            if isinstance(arts, list) and arts:   # M125-C1 — articles = liste de dicts : rendu texte, jamais un repr()
                lignes.append(entete + " :")
                for a in arts:
                    ref = a.get("reference") or a.get("regle") if isinstance(a, dict) else a
                    if ref:
                        lignes.append(f"   · {ref}")
            elif z.get("note"):
                lignes.append(entete + f" : {z['note']}")
            else:
                lignes.append(entete)
        _section(pdf, "RÈGLEMENT PLU PAR ZONE", lignes, source=rp.get("disclaimer"))

    pf = fiche.get("plu_fraicheur")
    if pf:
        _section(pdf, "FRAÎCHEUR DU ZONAGE (GPU vs mairie)",
                 [pf.get("document_servi") or pf.get("libelle"), pf.get("fait_foi"),
                  (f"En cours (non servi) : {pf['en_cours']}" if pf.get("en_cours") else None),
                  (f"À faire : {pf['action']}" if pf.get("action") else None)],
                 source=(f"Note : {pf['note']}" if pf.get("note") else None))

    rpr = fiche.get("radar_procedure")
    if _is_indispo(rpr):
        _indispo(pdf, "PROCÉDURES PLU EN COURS")
    elif rpr:
        syn, sursis = rpr.get("synthese") or {}, rpr.get("sursis") or {}
        _section(pdf, "PROCÉDURES PLU EN COURS",
                 [syn.get("etat"),
                  (f"Prochaine étape : {syn['prochaine_etape']}" if syn.get("prochaine_etape") else None),
                  (f"Sursis à statuer : {sursis['texte']} ({sursis.get('base_legale', '')})" if sursis.get("texte") else None),
                  (f"Veille zone AU : {rpr['veille_au']}" if rpr.get("veille_au") else None)])

    rnu = fiche.get("rnu")
    if rnu:
        _section(pdf, "RNU — RÈGLEMENT NATIONAL D'URBANISME",
                 [rnu.get("libelle"), rnu.get("detail"),
                  ("Dans l'enveloppe urbanisée (PAU) — estimation." if rnu.get("dans_pau") is True
                   else "Hors enveloppe urbanisée (PAU) — estimation." if rnu.get("dans_pau") is False else None),
                  rnu.get("avertissement_pau")])

    # ── SOURCES-1 lot 1 — DISPOSITIFS ET PÉRIMÈTRES du droit des sols (même bloc que la fiche
    #    écran : _dispositifs_block — ER avec part, EBC avec part, DPU typé, zone PEB, SUP). Chaque
    #    absence est TYPÉE (« non déterminée — non publié par la commune »), jamais un zéro.
    dispo = fiche.get("dispositifs")
    if dispo:
        lignes = []
        for e in (dispo.get("er") or []):
            lignes.append(f"Emplacement réservé : {e.get('libelle') or 'ER'} — "
                          f"{e.get('part_pct')} % de la parcelle"
                          + (" (emprise majoritairement grevée)" if (e.get("part_pct") or 0) >= 50 else "")
                          + " ; surface déduite de l'emprise constructible.")
        for e in (dispo.get("ebc") or []):
            lignes.append(f"Espace boisé classé : {e.get('libelle') or 'EBC'} — "
                          f"{e.get('part_pct')} % de la parcelle ; construction interdite sur "
                          "l'emprise boisée (art. L113-1 CU), part soustraite de l'assiette du potentiel.")
        dpu = dispo.get("dpu") or {}
        if dpu.get("etat") == "servi":
            lignes.append(("Droit de préemption urbain RENFORCÉ" if dpu.get("statut") == "renforce"
                           else "Droit de préemption urbain")
                          + " — la commune peut préempter à la vente (DIA, ~2 mois).")
        elif dpu.get("etat") == "hors":
            lignes.append("DPU : hors périmètre de préemption publié.")
        elif dpu.get("etat") == "non_determinee":
            lignes.append(f"DPU : non déterminé — {dpu.get('detail')}.")
        peb = dispo.get("peb") or {}
        if peb.get("zone") in ("A", "B", "C", "D"):
            effet = ("constructions d'habitation interdites" if peb["zone"] in ("A", "B")
                     else "isolement acoustique renforcé obligatoire" if peb["zone"] == "C"
                     else "zone d'information sur le bruit")
            lignes.append(f"Plan d'exposition au bruit : zone {peb['zone']} — {effet} "
                          "(art. L112-10 CU).")
        elif peb.get("zone") == "hors":
            lignes.append("PEB : hors zones publiées"
                          + (f" — {peb['detail']}" if peb.get("detail") else "") + ".")
        for s_ in (dispo.get("sup") or []):
            lignes.append(f"Servitude {s_.get('categorie')} : {s_.get('libelle') or 'servitude'}.")
        if lignes:
            _section(pdf, "DISPOSITIFS ET PÉRIMÈTRES (DROIT DES SOLS)", lignes,
                     source="Géoportail de l'urbanisme (prescriptions et informations des PLU) · "
                            "PEB DGAC via annexes GPU — millésime : PLU de la commune")

    tf = fiche.get("territoire_fiscal")
    if tf:
        lignes, zf, frr = [], tf.get("zfang") or {}, tf.get("frr") or {}
        if zf.get("libelle"):
            lignes.append(f"ZFANG : {zf['libelle']} (réf. {zf.get('source_ref') or '—'})")
        if frr.get("libelle"):
            lignes.append(f"FRR (ex-ZRR) : {frr['libelle']} (réf. {frr.get('source_ref') or '—'})")
        for per in tf.get("perimetres") or []:
            lignes.append(f"{per.get('libelle', '')} — {per.get('detail', '')} ({per.get('source', '')})")
        _section(pdf, "DISPOSITIFS TERRITORIAUX (fiscal)", lignes, source=tf.get("avertissement"))

    aper = fiche.get("aper")
    if aper and aper.get("note"):
        _section(pdf, "OBLIGATION APER (ombrières photovoltaïques)", [aper["note"]],
                 source=(f"État : {aper['etat']}" if aper.get("etat") else None))

    # ── TERRAIN & RÉSEAUX ────────────────────────────────────────────────────────────────────
    if (fiche.get("terrain") or {}).get("flag_terrassement_lourd"):
        _section(pdf, "TERRAIN", ["Terrassement lourd probable (relief marqué) — RGE ALTI 5 m."])

    via = fiche.get("viabilisation")
    if _is_indispo(via):
        _indispo(pdf, "VIABILISATION (réseaux)")
    elif via:
        lignes = [via.get("libelle")]
        for c in via.get("contributions") or []:
            lignes.append(f"· {c.get('libelle', '')}" + (f" — {c['detail']}" if c.get("detail") else ""))
        cr = via.get("cout_raccordement")
        if isinstance(cr, dict):   # M125-C1 — dict {niveau, assainissement, disclaimer} : rendu texte
            if cr.get("niveau"):
                lignes.append(cr["niveau"])            # texte déjà auto-descriptif (« Raccordement a priori… »)
            if cr.get("assainissement"):
                lignes.append(cr["assainissement"])
        elif cr:
            lignes.append(f"Coût de raccordement indicatif : {cr}")
        for k in ("elec_pv", "solaire"):
            v = via.get(k)
            if isinstance(v, dict) and v.get("note"):
                lignes.append(v["note"])
        _section(pdf, "VIABILISATION (réseaux)", lignes, source=via.get("disclaimer"))

    gest = fiche.get("gestionnaires")
    if _is_indispo(gest):
        _indispo(pdf, "GESTIONNAIRES (raccordement)")
    elif gest:
        epci = gest.get("epci") or {}
        lignes = [(f"EPCI : {epci['nom']}" + (f" — {epci['contact']}" if epci.get("contact") else "")) if epci.get("nom") else None]
        for lbl, key in (("Eau", "eau"), ("Assainissement", "assainissement"),
                         ("SPANC", "spanc"), ("Électricité", "electricite")):
            v = gest.get(key)
            nom = (v.get("operateur") or v.get("gestionnaire")) if isinstance(v, dict) else v
            if nom:
                lignes.append(f"{lbl} : {nom}")
        if gest.get("note"):
            lignes.append(gest["note"])
        _section(pdf, "GESTIONNAIRES (raccordement)", lignes, source=gest.get("disclaimer"))

    prox = fiche.get("proximites")
    if _is_indispo(prox):
        _indispo(pdf, "PROXIMITÉS (transport, axes, réseaux)")
    elif prox:
        lignes, ar, po, te = [], prox.get("arret"), prox.get("pole"), prox.get("telepherique")
        if ar:
            lignes.append(f"Arrêt {ar.get('nom', '')} ({ar.get('reseau') or 'réseau n/d'}) — {ar.get('distance_m')} m")
        if po:
            lignes.append(f"Pôle d'échange {po.get('nom', '')} — {po.get('distance_m')} m ({po.get('statut', '')})")
        if te:
            lignes.append(f"Téléphérique {te.get('station', '')} — {te.get('distance_m')} m")
        if prox.get("axe"):
            lignes.append(prox["axe"].get("libelle"))
        if prox.get("ligne_ht"):
            lignes.append(prox["ligne_ht"].get("libelle"))
        _section(pdf, "PROXIMITÉS (transport, axes, réseaux)", lignes)

    # ── MARCHÉ & ACTIVITÉ ────────────────────────────────────────────────────────────────────
    hs = fiche.get("historique_site")
    if _is_indispo(hs):
        _indispo(pdf, "SUR CETTE PARCELLE (historique)")
    elif hs and (hs.get("permis") or hs.get("caducite")):
        lignes = [f"{p.get('type') or 'Autorisation'} — {p.get('date_autorisation') or p.get('date_depot') or '?'}"
                  for p in (hs.get("permis") or [])[:8]]
        cad = hs.get("caducite")
        if cad:
            lignes.append(cad.get("libelle_court") or cad.get("detail") or "Caducité signalée.")
        _section(pdf, "SUR CETTE PARCELLE (historique)", lignes, source=hs.get("honnetete"))

    vp = fiche.get("voisinage_proche")
    if _is_indispo(vp):
        _indispo(pdf, "AUTOUR, À MOINS DE 100 M")
    elif vp and (vp.get("ventes_dvf") or vp.get("permis")):
        # M125-C6 — ne JAMAIS afficher « ~0 k€ » : la médiane n'est montrée que si elle arrondit à
        # ≥ 1 k€ (une valeur < 500 € sur N ventes n'est pas une médiane servable) ; sinon note ou rien.
        _pmed = vp.get("prix_median_eur")
        prix = (f" · prix médian ~{round(_pmed / 1000)} k€" if _pmed and round(_pmed / 1000) >= 1
                else (f" · {vp['prix_note']}" if vp.get("prix_note") else ""))
        _section(pdf, "AUTOUR, À MOINS DE 100 M",
                 [f"{vp.get('ventes_dvf', 0)} vente(s){prix} · {vp.get('permis', 0)} permis "
                  f"(< {vp.get('rayon_m', 100)} m, {vp.get('fenetre_mois', 36)} mois)"],
                 source=vp.get("honnetete"))

    dvfp = fiche.get("dvf_parcelle")
    if dvfp:
        lignes, dm = [], dvfp.get("derniere_mutation")
        # EXPORTS-1 (1.3) : le prix de l'ancien (sector_price parcelle, n + rayon + période) ouvre
        # la section — les médianes du secteur cadastral suivent, étiquetées SECONDAIRES.
        if fiche.get("marche_synthese"):
            lignes.append(fiche["marche_synthese"])
        if dm:
            base_m = f"Dernière mutation : {dm.get('date_mutation') or '?'}"
            lignes.append(base_m + (f" — {int(dm['valeur']):,} €".replace(",", " ") if dm.get("valeur") else ""))
        _et = dvfp.get("secteur_etiquette")
        if _et and (dvfp.get("secteur") or []):
            lignes.append(f"({_et})")
        for s in (dvfp.get("secteur") or [])[:4]:
            # EXPORTS-1 (5.5) : une médiane NULL n'est pas un « — » muet — c'est un échantillon
            # sous le seuil, et on le dit (jamais un zéro/tiret sans couverture).
            _med = s.get("mediane_prix_m2")
            _vmed = (f"médiane {_med} €/m²" if _med
                     else "médiane sous seuil d'échantillon (non servie)")
            lignes.append(f"Secteur — {s.get('type_bien', '')} : {_vmed} "
                          f"({s.get('n_ventes', '?')} ventes, {s.get('fenetre', '')})")
        # EXPORTS-1 (1.4, Q3) : la ligne « Neuf VEFA » a quitté la fiche — un seul « neuf » servi,
        # celui du bilan (resolve_prix_neuf_marche).
        _section(pdf, "MARCHÉ DVF — MUTATION & SECTEUR", lignes, source=dvfp.get("caveat"))

    ms = fiche.get("marche_secteur")
    if ms:
        lignes, fi, rp2 = [], ms.get("filosofi_200m"), ms.get("rpls_commune")
        if fi:
            bits = []
            if fi.get("nivvie_moyen_eur"):
                bits.append(f"niveau de vie médian ~{int(fi['nivvie_moyen_eur']):,} €".replace(",", " "))
            if fi.get("men") and fi.get("men_prop") is not None:
                bits.append(f"{round(100 * fi['men_prop'] / fi['men'])} % propriétaires")
            if fi.get("taux_pauvrete_pct") is not None:
                bits.append(f"{fi['taux_pauvrete_pct']} % de pauvreté")
            if bits:
                lignes.append("Carreau 200 m : " + " · ".join(bits) + f" ({_millesime(fi.get('millesime'))})")
        if rp2 and rp2.get("nb_logements") is not None:
            lignes.append(f"Parc social commune : {int(rp2['nb_logements']):,} logements".replace(",", " ")
                          + (f" · {rp2['pct_qpv']} % en QPV" if rp2.get("pct_qpv") is not None else "")
                          + f" ({_millesime(rp2.get('millesime'))})")
        _section(pdf, "CONTEXTE SOCIO-ÉCONOMIQUE (secteur)", lignes,
                 source="INSEE Filosofi · RPLS — contexte informatif, sans effet sur le verdict.")

    dep = fiche.get("depots")
    if _is_indispo(dep):
        _indispo(pdf, "ACTIVITÉ DE DÉPÔT (Sitadel)")
    elif dep:
        par, sec = dep.get("parcelle") or {}, dep.get("secteur") or {}
        lignes = [dep.get("libelle")]
        if par.get("count"):
            lignes.append(f"Sur cette parcelle : {par['count']} dépôt(s)" + (f" (dernier {par['dernier']})" if par.get("dernier") else ""))
        if sec.get("count"):
            lignes.append(f"Sur le secteur : {sec['count']} dépôt(s)" + (f" (dernier {sec['dernier']})" if sec.get("dernier") else ""))
        _section(pdf, "ACTIVITÉ DE DÉPÔT (Sitadel)", lignes,
                 source=(f"{dep.get('source', 'SITADEL')} — {dep.get('fenetre_mois', '')} mois, informatif"
                         if dep.get("source") or dep.get("fenetre_mois") else None))

    # ── PROPRIÉTAIRE & POTENTIEL ─────────────────────────────────────────────────────────────
    copros = fiche.get("coproprietes") or []
    if copros:
        lignes = []
        for c in copros[:6]:
            nom = c.get("nom_usage") or c.get("numero_immatriculation") or "copropriété"
            lots = f"{c['nb_lots_total']} lots" if c.get("nb_lots_total") is not None else ""
            hab = f" (dont {c['nb_lots_habitation']} hab.)" if c.get("nb_lots_habitation") is not None else ""
            per = f" · {c['periode_construction']}" if c.get("periode_construction") else ""
            syn = (f" · syndic {c.get('syndic_type') or ''} {c.get('syndic_nom') or ''}".rstrip()
                   if c.get("syndic_type") or c.get("syndic_nom") else "")
            lignes.append(f"{nom} — {lots}{hab}{per}{syn}".strip(" —"))
        _section(pdf, "COPROPRIÉTÉ(S) RATTACHÉE(S)", lignes,
                 source="Source : RNIC (registre national des copropriétés) — information.")

    ren = fiche.get("renouvellement")
    if ren:
        # M125-A — SEGMENT seul : le RANG (rang_segment/total_segment) est de l'ANALYSE → EXCLU (M124-A1).
        _section(pdf, "SEGMENT RENOUVELLEMENT URBAIN",
                 [ren.get("libelle"),
                  (f"Bâti d'origine : "
                   f"{ {'deja_bati': 'déjà bâti', 'nu': 'terrain nu'}.get(ren['code_bati_origine'], ren['code_bati_origine']) }"
                   if ren.get("code_bati_origine") else None),
                  (f"Zone PLU : {ren['zone_plu']}" if ren.get("zone_plu") else None),
                  (f"SDP résiduelle estimée : ~{ren['sdp_residuelle_m2']:,} m²".replace(",", " ") if ren.get("sdp_residuelle_m2") else None),
                  (f"Surface parcelle : {ren['surface_m2']:,} m²".replace(",", " ") if ren.get("surface_m2") else None)])
        # M125-C2 — PAS de signature « Analyse LABUSE · {date} » (métadonnée d'analyse) : le PDF ne
        # porte pas de trace du moteur. Le segment est une donnée ; le rang (analyse) reste exclu.

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
        _titre_section(pdf, "Charge foncière — selon vos hypothèses")
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(*TXT_MUT)
        pdf.multi_cell(pdf.w - 28, 4,
                       "Hypothèses promoteur (saisies, non estimées par LABUSE) : coût de "
                       f"construction {round(inp.get('cout_construction_m2') or 0):,} €/m² · "
                       f"marge & frais {inp.get('marge_frais_pct')} %.".replace(",", " "),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)
        pdf.set_font("grotesk", size=12)
        pdf.set_text_color(*TXT1)                     # M126 — le vert n'emplit jamais du texte
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
            pdf.set_text_color(*(TXT1 if ach.get("supportable") else RED))
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

    # M126 pt.4 — le PLAN DE SITUATION est REMONTÉ en PAGE 1 (helper _bloc_plan appelé sous le
    #             bandeau des 3 chiffres). Il n'est plus rendu ici.

    # ── M73-E Volet B — COMPARABLES DVF : la table du premium, via marche_service (aucun appel DVF
    # direct). Chaque vente porte date/distance/surface/prix (requête les garantit) ; n + rayon dits ;
    # liste vide → on l'écrit, jamais un tableau vide. Rappel de méthode sous le tableau.
    cmp = fiche.get("comparables") or {}
    lst = cmp.get("comparables") or []
    # M126 pt.10 + M125-C5 — on écarte d'ABORD les €/m² ABERRANTS (mutations multi-parcelles : ex.
    # 6,2 M€ pour 70 m² = 88 749 €/m² ; seuil STATISTIQUE z-score modifié médiane/MAD > 3.5, jamais un
    # plafond dur), PUIS le compteur dit le nombre RÉELLEMENT AFFICHÉ (len(keep)), plus « 12 retenues ».
    _pm = [c["prix_m2"] for c in lst if isinstance(c.get("prix_m2"), (int, float)) and c["prix_m2"] > 0]
    _med = statistics.median(_pm) if len(_pm) >= 4 else None
    _mad = (statistics.median([abs(x - _med) for x in _pm]) or 1e-9) if _med is not None else None

    def _aberrant(c) -> bool:
        v = c.get("prix_m2")
        return (_med is not None and isinstance(v, (int, float)) and v > 0
                and abs(0.6745 * (v - _med) / _mad) > 3.5)
    keep = [c for c in lst if not _aberrant(c)]
    n_ab = len(lst) - len(keep)
    if pdf.get_y() > pdf.h - 62:
        pdf.add_page()
    _titre_section(pdf, f"Comparables DVF — rayon {cmp.get('rayon_m', '?')} m · {cmp.get('fenetre_ans', '?')} ans")
    _cap = " (12 plus récentes retenues)" if cmp.get("n", 0) >= 12 else ""
    pdf.set_font("inter", size=7)
    pdf.set_text_color(*SRC)
    _nk = len(keep)
    pdf.multi_cell(pdf.w - 28, 3.4,
                   f"{_nk} vente{'s' if _nk != 1 else ''} affichée{'s' if _nk != 1 else ''}{_cap} — "
                   "périmètre local, distinct de la synthèse marché de la commune.",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)
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
        # M126 — l'écartement des aberrants est calculé PLUS HAUT (avant le compteur, pt.10) ; ici on
        # ne fait que DIRE ce qui a été écarté, puis afficher `keep`.
        if n_ab:
            pdf.set_font("inter", size=7.5)
            pdf.set_text_color(*AMBER)
            pdf.multi_cell(pdf.w - 28, 3.6,
                           f"{n_ab} vente{'s' if n_ab > 1 else ''} au prix/m² aberrant écartée"
                           f"{'s' if n_ab > 1 else ''} du tableau "
                           "(prix incohérent avec la surface — mutation multi-parcelles probable).",
                           new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.4)
        lst = keep
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

    # ── M125-A — SOURCES UTILISÉES SUR CETTE FICHE (liste par-fiche, avec millésime réel + fiabilité).
    # Distincte de l'attribution générique du pied de page : ici, seulement ce qui a PRODUIT un constat.
    ds_list = fiche.get("data_sources") or []
    if ds_list:
        lignes = [f"{d.get('nom', '')}"
                  + (f" — {_millesime(d.get('millesime'))}" if d.get("millesime") else "")
                  + (f" · fiabilité {d['fiabilite']}" if d.get("fiabilite") else "")
                  for d in ds_list]
        _section(pdf, "SOURCES UTILISÉES SUR CETTE FICHE", lignes)

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
        etat_col = (GREEN if bloc["statut"] in ("source", "source_secteur", "source_commune")
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

    # ── M126 pt.9 — POINTS SANS SIGNAL : les signaux « rien à signaler » de tous les onglets,
    #    REGROUPÉS ici en fin de document (aucun n'est supprimé — seulement déplacé). Même tableau
    #    3 colonnes ; les pages de tête restent réservées aux signaux porteurs d'information.
    if sans_signal_all:
        # M126-B (B2) — anti-orphelin FORT : le bloc ne démarre pas si le titre + le résumé + ~2 lignes
        # ne tiennent pas (sinon une page ne portait que le pied de page). Réserve ~34 mm.
        if pdf.get_y() > pdf.h - 34:
            pdf.add_page()
        _titre_section(pdf, "Points sans signal")
        pdf.set_font("inter", size=7)
        pdf.set_text_color(*SRC)
        _n = len(sans_signal_all)
        pdf.multi_cell(pdf.w - 28, 3.6,
                       f"{_n} point{'s' if _n > 1 else ''} sans signal, regroupé{'s' if _n > 1 else ''} "
                       "ici pour l'exhaustivité (rien à signaler).",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.6)
        for _onglet, ln in sans_signal_all:
            _ligne_signal(pdf, _layer_label(ln["layer"]), _detail_ligne(ln), _src_ligne(ln))

    out = pdf.output()
    return bytes(out)
