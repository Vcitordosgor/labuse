"""IMPLANTATION-3 — le document « Étude de faisabilité » (8 pages + annexe).

L'EXPORT FIGÉ de l'outil : ce module rend en HTML la MÊME réponse que l'écran (le payload de
`POST /modules/etude`, assemblé par `implantation.service.etudier_payload`). Il ne RECALCULE rien :
chaque valeur imprimée est lue dans le payload. Le même builder et le même thème que les autres
documents (`exports.rendu.page_html` + `theme.css` + `render_pdf`).

Verrou « toute ligne du PDF est une ligne de l'outil » (extension de V5d/V5f) : `nombres_hors_payload`
confronte CHAQUE nombre imprimé aux nombres servis par le payload (après normalisation : les
séparateurs de milliers sont retirés) ; seuls quelques jetons de STRUCTURE (pagination, R+n, date,
n° de document, code EPSG, millésime d'année) sont tolérés. Un test rejoue ce crible (0 fuite).

Aucune requête, aucun accès au moteur ici : le payload entre, le HTML sort.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from .rendu import Cartouche, esc, page_html

# ── palette (reprise EXACTE de implantation.rendu._COUL, en hex pour le SVG) ──────────────────
_COUL = {
    "parcelle": ("#FBFCFB", "#9AA0A6"),
    "assiette": (None, "#DC2626"),
    "zone": ("#4ADE80", "#15803D"),
    "espace_libre": ("#BBF7D0", "#86EFAC"),
    "allee": ("#D1D5DB", "#9CA3AF"),
    "place": ("#FFFFFF", "#6B7280"),
    "acces": ("#B45309", "#B45309"),
    "batiment_emprise": ("#1F2A24", "#1F2A24"),
    "noyau": ("#9CA3AF", "#4B5563"),
    "coursive": ("#E5E7EB", "#9CA3AF"),
    "module": ("#ECFDF3", "#15803D"),
    "voie": (None, "#B45309"),
    "ppr_rouge": ("#DC2626", "#991B1B"),
    "ppr_bleue": ("#3B82F6", "#1D4ED8"),
    # ETUDE-V6-4 (item 9) — niveau −1 dessiné : emprise enterrée, allée, places, rampe (mêmes clés qu'à l'écran).
    "sous_sol_emprise": ("#E2E8F0", "#64748B"),
    "place_ss": ("#FFFFFF", "#6B7280"),
    "allee_ss": ("#D1D5DB", "#9CA3AF"),
    "rampe": ("#FDE68A", "#B45309"),
}
#: ordre de dessin (z-order) : contexte terrain d'abord, objets du plan ensuite.
_Z = ["parcelle", "assiette", "ppr_rouge", "ppr_bleue", "zone", "espace_libre",
      "sous_sol_emprise", "allee", "allee_ss", "acces", "place", "place_ss", "rampe",
      "batiment_emprise", "coursive", "noyau", "module", "voie"]

# ── CSS scopé à l'Étude (le reste vient de theme.css) ─────────────────────────────────────────
# N'invente aucun nouveau jeton couleur : réutilise les variables de theme.css. Ne porte QUE les
# formes propres à l'Étude (deux statuts, pastilles de contrôle 4 états, citation, grille de synthèse).
_STYLE = """
.ef-synth { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8pt; margin: 10pt 0 8pt; }
.ef-synth .tile { border: 1px solid var(--line); border-radius: 3pt; padding: 8pt 10pt; }
.ef-synth .tile .v { font-size: 15pt; font-weight: 700; line-height: 1.1; }
.ef-synth .tile .l { font-size: 8pt; color: var(--muted); margin-top: 2pt; }
.ef-status { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; margin: 8pt 0; }
.ef-status > div { border: 1px solid var(--line); border-radius: 3pt; padding: 7pt 10pt; font-size: 9.5pt; }
.ef-status b { display: block; font-size: 8pt; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); margin-bottom: 2pt; }
table.ef-scn { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 6pt 0 4pt; }
table.ef-scn th, table.ef-scn td { padding: 4.5pt 6pt; border-bottom: 1px solid var(--line); text-align: left; }
table.ef-scn th { font-weight: 600; font-size: 8pt; color: var(--muted); border-bottom: 1.5px solid var(--ink); }
table.ef-scn td.num, table.ef-scn th.num { text-align: right; }
table.ef-scn tr.retenu { background: var(--mint-bg); }
.cite { display: block; font-size: 7.5pt; color: var(--muted); margin-top: 1pt; }
.art { border-left: 2pt solid var(--mint); padding: 2pt 0 2pt 7pt; margin: 5pt 0; }
.art-ref { font-size: 8pt; font-weight: 600; color: var(--mint-ink); }
.art-cit { font-size: 8.5pt; font-style: italic; color: var(--ink); margin-top: 1pt; }
.url { font-family: monospace; font-size: 7pt; word-break: break-all; color: var(--muted); }
.st { display: inline-block; font-size: 7.5pt; padding: 2pt 5pt; border-radius: 2pt; white-space: nowrap; }
.st.ok { color: var(--mint-ink); background: var(--mint-bg); border: 1px solid var(--mint); }
.st.cp { color: var(--amber); background: var(--amber-bg); border: 1px solid var(--amber); }
.st.no { color: var(--rose); background: var(--rose-bg); border: 1px solid #f0b3ac; }
.res { font-weight: 600; font-size: 8.5pt; }
.res.ok { color: var(--mint-ink); } .res.ko { color: var(--rose); } .res.ne { color: var(--muted); }
.ef-fig { border: 1px solid var(--line); border-radius: 3pt; padding: 6pt; margin: 6pt 0; background: #FBFCFB; page-break-inside: avoid; }
.ef-fig svg { width: 100%; height: auto; display: block; }
.ef-leg { font-size: 7.8pt; color: var(--muted); margin-top: 3pt; display: flex; flex-wrap: wrap; gap: 10pt; }
.ef-leg i { display: inline-block; width: 9pt; height: 9pt; border-radius: 1.5pt; vertical-align: -1pt; margin-right: 3pt; }
/* IMPLANTATION-4 — la PLANCHE plan masse (le MÊME SVG qu'à l'écran) sur une page PAYSAGE pleine. */
@page planche-land { size: A4 landscape; margin: 9mm; }
.ef-planche-page { page: planche-land; }
/* le SVG porte width="100%" + viewBox : WeasyPrint le dimensionne seul. Ne PAS forcer height:auto ici
   (sous page paysage nommée, WeasyPrint calcule alors une hauteur nulle → planche blanche). */
.ef-planche { width: 96%; margin: 0 auto; border: 1px solid var(--line); border-radius: 3pt; background: #fff; }
"""

# ── format ────────────────────────────────────────────────────────────────────────────────────
# IMPLANTATION-4 (format des nombres) — LE helper UNIQUE (planche + PDF), miroir de lib/format.ts.
# Milliers en espace INSÉCABLE (retiré par le crible de provenance `_canon`). `_grp`/`_dec`/`_m2`
# deviennent de simples alias pour ne rien changer aux appels existants du document.
from labuse.implantation.format import dec_souple, groupe_fr, m2_fr   # noqa: E402

_grp = groupe_fr
_dec = dec_souple
_m2 = m2_fr


def _statut_court(s: str) -> str:
    s = s or ""
    if s.startswith("exploitable"):
        return "Exploitable"
    if s == "à compléter":
        return "À compléter"
    if s == "ne tient pas":
        return "Ne tient pas"
    return "Simulation impossible"


def _statut_classe(s: str) -> str:
    s = s or ""
    return "ok" if s.startswith("exploitable") else "cp" if s == "à compléter" else "no"


# ── choix du scénario retenu ────────────────────────────────────────────────────────────────
def scenario_retenu(payload: dict, ref: Optional[str] = None) -> Optional[dict]:
    """Le scénario que le document met en avant : celui AFFICHÉ (ref transmise par l'outil) sinon le
    premier EXPLOITABLE, sinon le mieux classé (scenarios[0]). None si aucun scénario."""
    scn = payload.get("scenarios") or []
    if scn:
        if ref:
            for s in scn:
                if s.get("ref") == ref:
                    return s
        for s in scn:
            if str(s.get("statut_etude", "")).startswith("exploitable"):
                return s
        return scn[0]
    # ETUDE-V6-3 (item 12) — AUCUN scénario (la demande ne tient pas) : on retient la variante « votre
    # programme » (best-effort) pour que le PDF se génère QUAND MÊME, le dépassement écrit dans le document.
    for v in (payload.get("variantes") or []):
        if not v.get("absente"):
            return v
    return None


def _scn_label(s: dict) -> str:
    """ETUDE-V6-3 (item 10) — libellé AFFICHABLE d'un scénario : jamais un nom technique (« votre_programme »).
    Les scénarios Pareto gardent leur repère A/B/C ; une variante de rôle devient « retenu »."""
    r = str(s.get("ref", ""))
    return "retenu" if r in ("votre_programme", "optimisation", "alternative") else r


def _refs_parcelles(payload: dict) -> str:
    """ETUDE-V6-4 (item 12) — « AW 99, 451, 624, 625 » : section une fois, numéros groupés."""
    idus = payload.get("entrees", {}).get("idus") or [p.get("idu", "") for p in payload.get("terrain", {}).get("parcelles", [])]
    groupes: dict = {}
    for idu in idus:
        if len(idu) >= 11:
            sec, num = idu[8:10], str(int(idu[10:])) if idu[10:].isdigit() else idu[10:]
            groupes.setdefault(sec, []).append(num)
    return " · ".join(f"{sec} {', '.join(nums)}" for sec, nums in groupes.items()) or "—"


def _mode_label(mode: Optional[str]) -> str:
    """ETUDE-V6-4 (item 12) — accents corrects : aerien → « aérien », sous_sol → « sous-sol »."""
    return {"aerien": "aérien", "sous_sol": "sous-sol"}.get(mode or "aerien", "aérien")


def _stationnement_label(retenu: dict, entrees: dict) -> str:
    """ETUDE-V6-5 — libellé du stationnement avec le nombre de niveaux CHOISI (« sous-sol 1 niveau »)."""
    mode = retenu.get("stationnement", {}).get("mode") or entrees.get("stationnement") or "aerien"
    if mode != "sous_sol":
        return "aérien"
    niv = retenu.get("stationnement", {}).get("niveaux_sous_sol") or entrees.get("niveaux_sous_sol") or 1
    return f"sous-sol {int(niv)} niveau" + ("x" if int(niv) > 1 else "")


def _stationnement_3lignes(payload: dict, retenu: dict) -> str:
    """ETUDE-V6-4 (items 4/5/11) — stationnement en TROIS lignes (identiques à l'écran, mêmes mots) + mixité."""
    reg = payload.get("stationnement_regimes") or {}
    g = reg.get("general") or {}
    pf = reg.get("plafond_national")
    commune = payload["entrees"].get("commune") or ""
    mode = retenu.get("stationnement", {}).get("mode") or payload["entrees"].get("stationnement") or "aerien"
    places = retenu.get("stationnement", {}).get("places")
    niveaux = retenu.get("stationnement", {}).get("niveaux_sous_sol") or 1
    regleg = g.get("regle_courte") or (f"{_dec(g.get('ratio_par_logement'))} place/logt" if g.get("ratio_par_logement") is not None else "un barème par typologie")
    # ETUDE-V6-5 — le lieu reflète le NOMBRE DE NIVEAUX choisi (−1, ou −1 et −2).
    lieu = (f"au sous-sol ({'niveaux −1 et −2' if niveaux >= 2 else 'niveau −1'})" if mode == "sous_sol"
            else "en aérien (au sol)")
    lignes = [f"Le PLU de {esc(commune)} (art. {esc(g.get('article') or '—')}) exige {esc(regleg)}."]
    if pf:
        lignes.append(f"La loi nationale (Code de l'urbanisme, art. {esc(pf.get('reference') or 'L151-35')}) "
                      f"plafonne à {_dec(pf.get('ratio_plafond'))} place/logt si le projet est éligible — à confirmer.")
    lignes.append(f"LABUSE a dessiné {int(places) if places is not None else '—'} places {lieu} selon la règle du PLU.")
    mix_html = ""
    mx = next((l for l in payload["regles"].get("lignes", []) if "mixit" in (l.get("nom") or "").lower()), None)
    if mx and mx.get("valeur") is not None:
        aides = retenu.get("programme", {}).get("logements_aides_imposes")
        appl = retenu.get("programme", {}).get("mixite_applicable")
        etat = (f"Applicable : {int(aides)} logements aidés imposés." if appl and aides is not None
                else "Non applicable (seuil non atteint).")
        mix_html = (f'<p><b>Mixité sociale</b> (art. {esc(mx.get("article") or "—")}) : {_dec(mx.get("valeur"))} % '
                    f'de logements aidés{" au-delà de " + _grp(mx.get("seuil_m2")) + " m² de SDP" if mx.get("seuil_m2") else ""}. {esc(etat)}</p>')
    return ('<section><h2>Stationnement &amp; mixité</h2>'
            + "".join(f'<p>{l}</p>' for l in lignes) + mix_html + '</section>')


def _fourchette(payload: dict) -> Optional[tuple[int, int]]:
    """Fourchette de logements des scénarios EXPLOITABLE seulement (jamais « ce terrain permet N »)."""
    xs = [int(s["resume"]["logements"]) for s in (payload.get("scenarios") or [])
          if str(s.get("statut_etude", "")).startswith("exploitable")
          and s.get("resume", {}).get("logements") is not None]
    return (min(xs), max(xs)) if xs else None


# ── SVG depuis le GeoJSON (4326) ──────────────────────────────────────────────────────────────
def _rings_of(geom: dict) -> list[list[list[float]]]:
    """Liste d'anneaux [ [ [lon,lat], ... ], ... ] quelle que soit la géométrie (Polygon/MultiPolygon)."""
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    if t == "LineString":
        return [c]            # traité comme une polyligne (voie)
    return []


def _svg_plan(fc: dict, kinds: list[str], *, w: int = 620, h: int = 440) -> str:
    """Projette les features du GeoJSON (WGS84) en SVG. Projection équirectangulaire locale (x corrigé
    par cos(lat)), cadrée sur l'emprise des features retenues, y inversé. Aucun nombre imprimé (dessin
    seul) : les mesures restent dans les tableaux."""
    feats = [f for f in (fc.get("features") or [])
             if (f.get("properties") or {}).get("kind") in kinds and f.get("geometry")]
    pts: list[tuple[float, float]] = []
    for f in feats:
        for ring in _rings_of(f["geometry"]):
            pts.extend((float(x), float(y)) for x, y in ring)
    if not pts:
        return ""
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    import math
    lat0 = (min(lats) + max(lats)) / 2.0
    kx = math.cos(math.radians(lat0)) or 1.0
    xs = [lon * kx for lon in lons]
    minx, maxx, miny, maxy = min(xs), max(xs), min(lats), max(lats)
    dx = (maxx - minx) or 1e-9
    dy = (maxy - miny) or 1e-9
    pad = 14.0
    sc = min((w - 2 * pad) / dx, (h - 2 * pad) / dy)
    ox = (w - sc * dx) / 2.0
    oy = (h - sc * dy) / 2.0

    def px(lon, lat):
        X = ox + (lon * kx - minx) * sc
        Y = h - (oy + (lat - miny) * sc)   # inversion y (nord en haut)
        return X, Y

    body: list[str] = ['<rect width="%d" height="%d" fill="#FBFCFB"/>' % (w, h)]
    order = {k: i for i, k in enumerate(_Z)}
    for f in sorted(feats, key=lambda f: order.get((f["properties"] or {}).get("kind"), 99)):
        kind = (f["properties"] or {}).get("kind")
        face, edge = _COUL.get(kind, (None, "#6B7280"))
        g = f["geometry"]
        if g.get("type") == "LineString":
            pts2 = " ".join("%.1f,%.1f" % px(x, y) for x, y in g["coordinates"])
            body.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3" '
                        'stroke-linecap="round"/>' % (pts2, edge))
            continue
        dash = ' stroke-dasharray="6 3"' if kind == "assiette" else (
            ' stroke-dasharray="4 3"' if kind == "zone" else "")
        op = ' fill-opacity="0.2"' if kind in ("zone", "ppr_rouge", "ppr_bleue", "espace_libre") else ""
        for ring in _rings_of(g):
            d = "M " + " L ".join("%.1f %.1f" % px(x, y) for x, y in ring) + " Z"
            body.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s"%s%s/>' % (
                d, (face or "none"), (edge or "none"), ("1.6" if kind == "assiette" else "0.8"), dash, op))
    # flèche nord
    body.append('<g transform="translate(%d,24)"><path d="M0,-12 6,6 0,2 -6,6 Z" fill="#1F2A24"/>'
                '<text x="-4" y="20" font-size="10" fill="#1F2A24">N</text></g>' % (w - 26))
    return ('<div class="ef-fig"><svg viewBox="0 0 %d %d" width="100%%">%s</svg></div>'
            % (w, h, "".join(body)))


def _legende(kinds: list[str]) -> str:
    labels = {
        "parcelle": "Parcelles", "assiette": "Assiette", "zone": "Zone d'implantation",
        "batiment_emprise": "Bâtiment proposé", "place": "Places", "allee": "Allée",
        "acces": "Accès", "espace_libre": "Espaces libres", "voie": "Limite classée voie",
        "ppr_rouge": "PPR rouge (retirée)", "ppr_bleue": "PPR bleue (signalée)",
        "module": "Modules logements", "noyau": "Noyau",
        # ETUDE-V6-4 (item 9) — niveau −1.
        "sous_sol_emprise": "Emprise enterrée", "place_ss": "Places (−1)",
        "allee_ss": "Allée (−1)", "rampe": "Rampe d'accès",
    }
    out = []
    for k in kinds:
        if k not in labels:
            continue
        face, edge = _COUL.get(k, (None, "#6B7280"))
        bg = face or "#FFFFFF"
        out.append('<span><i style="background:%s;border:1px solid %s"></i>%s</span>'
                   % (bg, edge or "#6B7280", esc(labels[k])))
    return '<div class="ef-leg">' + "".join(out) + "</div>"


# ── citation d'une règle ──────────────────────────────────────────────────────────────────────
def _cite(ligne: dict) -> str:
    art = ligne.get("article")
    pg = ligne.get("page_pdf")
    if not art and pg is None:
        return ""
    bits = []
    if art:
        bits.append(f"art. {esc(str(art))}")
    if pg is not None:
        bits.append(f"p. {esc(str(pg))}")
    return f'<span class="cite">PLU · {" · ".join(bits)}</span>'


def _num_de_regle(regle: str) -> Optional[str]:
    """Premier nombre (avec unité m²) d'une chaîne de contrôle « ≤ 1222 m² (70 % …) » → « 1 222 »."""
    m = re.search(r"([\d\s]+)\s*m²", regle or "")
    if not m:
        return None
    return _grp(int(m.group(1).replace(" ", "")))


# ════════════════════════════════════════════════════════════════════════════════════════════
#   LES PAGES
# ════════════════════════════════════════════════════════════════════════════════════════════
_WARN = ("Pré-faisabilité automatisée : scénarios indicatifs d'implantation établis à partir des "
         "règles publiées du PLU et des données publiques. Ce document n'est ni une étude "
         "d'architecte, ni une preuve de conformité, ni un dossier de permis.")


def _p1_synthese(payload: dict, retenu: dict, numero: str, genere_le: str) -> str:
    e = payload["entrees"]
    t = payload["terrain"]
    refs = _refs_parcelles(payload)
    fr = _fourchette(payload)
    scn = payload.get("scenarios") or []
    # verdict (fourchette des Exploitable ; un scénario « à compléter » cité à part, jamais « permet »)
    if fr:
        a, b = fr
        txt = (f"Selon nos hypothèses d'implantation, ce terrain peut recevoir "
               f"{'entre ' + str(a) + ' et ' + str(b) if a != b else str(a)} logements en collectif "
               f"avec stationnement aérien.")
        acomp = [s for s in scn if s.get("statut_etude") == "à compléter"]
        if acomp:
            m = max(int(s["resume"]["logements"]) for s in acomp)
            txt += f" Un scénario à {m} logements reste à compléter."
        vclass = "verdict"
    else:
        txt = (payload.get("message")
               or "Aucun scénario exploitable sur ce terrain selon nos hypothèses — voir le détail.")
        # ETUDE-V6-3 (item 12) — le document se génère MÊME si la demande ne tient pas : le dépassement
        # est ÉCRIT (comme à l'écran), chiffré depuis le payload (jamais un PDF manquant).
        dep = payload.get("depassement")
        if dep:
            txt += (f" Dépassement : {dep['total_demande']} logements demandés, "
                    f"{dep['total_tiennent']} tiennent au mieux sur ce terrain.")
        vclass = "verdict warn"
    cc = retenu["controles_compte"]
    # tuiles de synthèse (chaque nombre vient du payload : contrôles, règles, programme, terrain)
    emp = next((c for c in retenu["controles"] if c["nom"] == "Emprise au sol"), None)
    emp_m2 = _num_de_regle(emp["regle"]) if emp else None
    haut = next((l for l in payload["regles"]["lignes"] if "égout" in (l.get("nom") or "")
                 or "hauteur" in (l.get("nom") or "").lower()), None)
    aides = retenu["programme"].get("logements_aides_imposes")
    aides_txt = (str(aides) if retenu["programme"].get("mixite_applicable") and aides is not None
                 else "sans objet")
    places_imp = retenu["stationnement"].get("places_imposees")
    tiles = [
        (_m2(t.get("contenance_totale_m2")), "Contenance cadastrale"),
        ((emp_m2 + " m²") if emp_m2 else "—", "Emprise au sol max"),
        ((f"{_grp(haut['valeur'])} {esc(str(haut.get('unite') or 'm'))}") if haut and haut.get("valeur") is not None else "—",
         esc(f"Hauteur ({haut['nom']})" if haut else "Hauteur")),
        (aides_txt, "Logements aidés imposés"),
        (str(places_imp) if places_imp is not None else "—", f"Places imposées (scénario {_scn_label(retenu)})"),
        (str(cc["non_effectue"]), "Contrôles non effectués"),
    ]
    tiles_html = "".join('<div class="tile"><div class="v">%s</div><div class="l">%s</div></div>'
                         % (v, l) for v, l in tiles)
    # tableau des scénarios (si la demande ne tient pas, on montre AU MOINS le scénario retenu best-effort)
    rows = []
    for s in (scn or [retenu]):
        cls = ' class="retenu"' if s["ref"] == retenu["ref"] else ""
        stc = _statut_classe(s["statut_etude"])
        rows.append(
            f'<tr{cls}><td>{esc(_scn_label(s))}{" (retenu)" if s["ref"] == retenu["ref"] and _scn_label(s) != "retenu" else ""}</td>'
            f'<td>{esc(str(s.get("forme", "")).replace("_", " "))}</td>'
            f'<td class="num">{s["resume"]["logements"]}</td>'
            f'<td class="num">{esc(s.get("niveaux_label", ""))}</td>'
            f'<td class="num">{_grp(s["resume"]["sdp_m2"])}</td>'
            f'<td class="num">{s["resume"]["places"]}</td>'
            f'<td><span class="st {stc}">{esc(_statut_court(s["statut_etude"]))}</span></td></tr>')
    scn_table = (
        '<table class="ef-scn"><tr><th>Scénario</th><th>Forme</th><th class="num">Logements</th>'
        '<th class="num">Niveaux</th><th class="num">SDP du scénario</th><th class="num">Places</th>'
        '<th>Étude</th></tr>' + "".join(rows) + "</table>") if rows else ""
    # CHASSE-DOCS-FIX-1 (vérif #2) — caveat d'ouverture AU (« ouverture sous conditions »), comme la
    # fiche §4 et Comparer : jamais une capacité servie nue sur une zone AU conditionnée.
    _au = payload.get("au_ouverture") if isinstance(payload, dict) else None
    _au_html = (f'<p class="note"><b>Zone à urbaniser (AU)</b> — {esc(_au.get("statut") or "")}. '
                f'{esc(_au.get("motif") or "")}</p>' if _au else '')
    return (
        '<div class="cover">'
        f'<div class="kicker">LABUSE · Document n° {esc(numero)}</div>'
        f'<h1>Étude de faisabilité — {esc(t.get("commune") or "")} · parcelles {esc(_refs_parcelles(payload))}</h1>'
        f'<p class="idu">{_m2(t.get("contenance_totale_m2"))} · zone {esc(e.get("zone") or "")} · '
        f'collectif · stationnement {esc(_stationnement_label(retenu, e))}</p>'
        + _au_html
        + f'<div class="{vclass}">{esc(txt)}</div>'
        # ETUDE-V6-4 (items 10/11/13) — LA phrase « ce qui limite », identique au bandeau de l'écran
        # (champ serveur unique). Absente si rien ne limite (terrain sans contrainte dominante).
        + (f'<p class="note"><b>Ce qui limite :</b> {esc(payload.get("facteur_limitant") or "")}.</p>'
           if payload.get("facteur_limitant") else '')
        # ETUDE-V6-4 (item 10) — en sous-sol, pourquoi la hauteur plafonne (même phrase qu'à l'écran).
        + (f'<p class="note">{esc(payload.get("facteur_limitant_detail") or "")}</p>'
           if payload.get("facteur_limitant_detail") else '')
        + '<div class="ef-status">'
        f'<div><b>Contrôles automatisés (scénario {esc(_scn_label(retenu))})</b>'
        f'{cc["reussi"]} réussis · {cc["echoue"]} échoués · {cc["non_effectue"]} non effectués</div>'
        f'<div><b>Statut de l\'étude</b>{esc(_statut_court(retenu["statut_etude"]))} — '
        'à faire confirmer par un architecte</div></div>'
        + scn_table
        + '<p class="note">Fourchette = scénarios « Exploitable » seulement. '
          'Jamais « ce terrain permet N logements » ; ce document n\'affirme aucune conformité '
          'réglementaire.</p>'
        + f'<div class="ef-synth">{tiles_html}</div>'
        + f'<div class="aside rose">{esc(_WARN)}</div>'
        '</div>')


def _p2_terrain(payload: dict, retenu: dict) -> str:
    t = payload["terrain"]
    prows = []
    for p in t.get("parcelles", []):
        prows.append(f'<tr><td class="k">{esc(p.get("numero") or p.get("idu", ""))}</td>'
                     f'<td>{_m2(p.get("contenance_m2"))}</td>'
                     f'<td class="n"><span class="chip s">Sourcé</span></td></tr>')
    prows.append(f'<tr><td class="k"><strong>Assiette fusionnée</strong></td>'
                 f'<td><strong>{_m2(t.get("contenance_totale_m2"))}</strong></td><td class="n"></td></tr>')
    # terrain (pente, limites, accès)
    trows = []
    pente = t.get("pente_lidar")
    if isinstance(pente, dict):
        pm = pente.get("pente_moyenne_pct") or pente.get("pente_pct") or pente.get("pente")
        if pm is not None:
            trows.append(f'<tr><td class="k">Pente moyenne</td><td>{esc(_dec(pm))} %</td>'
                         f'<td class="n"><span class="chip s">LiDAR HD</span></td></tr>')
    note = t.get("note_limites")
    if note:
        trows.append(f'<tr><td class="k">Limites</td><td>{esc(str(note))}</td>'
                     f'<td class="n"><span class="chip s">BD TOPO · cadastre</span></td></tr>')
    acces = retenu.get("stationnement", {}).get("acces")
    if acces:
        trows.append(f'<tr><td class="k">Accès véhicule</td>'
                     f'<td>{esc(acces.get("note") or "possible")} — à confirmer</td>'
                     f'<td class="n"><span class="chip d">Dérivé</span></td></tr>')
    fig = _svg_plan(retenu["geojson"], ["parcelle", "assiette", "voie"], h=380)
    verdict = (f'{len(t.get("parcelles", []))} parcelle(s), {_m2(t.get("contenance_totale_m2"))} au '
               f'cadastre' + (f" ; {esc(str(note))}" if note else "") + ".")
    return (
        '<section><h2>1. Le terrain</h2>'
        f'<div class="verdict">{verdict}</div>'
        + fig + _legende(["parcelle", "assiette", "voie"])
        + '<table class="kv"><tr><th>Parcelle</th><th>Contenance</th><th class="n">Nature</th></tr>'
        + "".join(prows) + "</table>"
        + ('<table class="kv"><tr><th>Terrain</th><th>Valeur</th><th class="n">Nature</th></tr>'
           + "".join(trows) + "</table>" if trows else "")
        + '</section>')


def _p3_regles(payload: dict, retenu: dict) -> str:
    r = payload["regles"]
    rows = []
    for l in r.get("lignes", []):
        val = l.get("valeur")
        unite = l.get("unite") or ""
        vtxt = (f"{_grp(val)} {esc(str(unite))}" if isinstance(val, (int, float)) and not isinstance(val, bool)
                else (esc(str(val)) if val is not None else "—"))
        if l.get("seuil_m2") is not None:
            vtxt += f" · seuil {_m2(l['seuil_m2'])}"
        nat = "Sourcé" if l.get("validee") else "Non validée"
        chip = "s" if l.get("validee") else "d"
        rows.append(f'<tr><td class="k">{esc(l.get("nom") or "")}{_cite(l)}</td>'
                    f'<td>{vtxt}</td><td class="n"><span class="chip {chip}">{nat}</span></td></tr>')
    # contraintes cartographiées (lignes absentes quand la contrainte ne touche pas le terrain)
    t = payload["terrain"]
    ct = t.get("contraintes") or {}
    crows = []
    if ct.get("ppr_rouge"):
        crows.append(f'<tr><td class="k">PPR zone rouge</td><td>{_m2(t.get("ppr_rouge_m2"))}</td>'
                     f'<td>retirée de l\'implantation (hypothèse prudente ; prescriptions à lire)</td></tr>')
    if ct.get("ppr_bleue"):
        crows.append(f'<tr><td class="k">PPR zone bleue</td><td>{_m2(t.get("ppr_bleue_m2"))}</td>'
                     f'<td>signalée, non interprétée ; si elle touche l\'implantation, « à compléter »</td></tr>')
    for k, lib in (("emplacement_reserve", "Emplacement réservé"), ("ebc", "EBC"),
                   ("sup", "Servitude d'utilité publique"), ("servitude", "Servitude")):
        if ct.get(k):
            crows.append(f'<tr><td class="k">{esc(lib)}</td><td>présente</td>'
                         f'<td>retirée seulement si elle interdit de construire ; sinon signalée</td></tr>')
    contraintes = ("<h3>Contraintes cartographiées</h3>"
                   '<table class="kv"><tr><th>Contrainte</th><th>Sur le terrain</th>'
                   '<th>Traitement</th></tr>' + "".join(crows) + "</table>"
                   + '<p class="note">Ligne absente quand la contrainte ne touche pas le terrain.</p>'
                   ) if crows else '<p class="note">Aucune contrainte cartographiée ne touche le terrain.</p>'
    return (
        '<section><h2>2. Règles et contraintes</h2>'
        f'<div class="verdict">Zone {esc(r.get("zone") or "")} du PLU. Chaque valeur est citée ; '
        'une règle non validée reste « non effectuée », jamais tenue pour acquise.</div>'
        '<table class="kv"><tr><th>Règle</th><th>Valeur</th><th class="n">Nature</th></tr>'
        + "".join(rows) + "</table>" + contraintes + '</section>')


def _p4_enveloppe(payload: dict, retenu: dict) -> str:
    t = payload["terrain"]
    emp = next((c for c in retenu["controles"] if c["nom"] == "Emprise au sol"), None)
    fig = _svg_plan(retenu["geojson"], ["parcelle", "assiette", "ppr_rouge", "ppr_bleue", "zone", "voie"], h=380)
    rows = [
        f'<tr><td class="k">Terrain (contenance)</td><td>{_m2(t.get("contenance_totale_m2"))}</td>'
        f'<td class="n"><span class="chip s">Sourcé</span></td></tr>',
        f'<tr><td class="k">Zone d\'implantation réglementaire</td><td>{_m2(t.get("zone_implantation_m2"))}</td>'
        f'<td class="n"><span class="chip d">Dérivé</span></td></tr>',
    ]
    if t.get("ppr_rouge_m2"):
        rows.append(f'<tr><td class="k">Retiré par PPR rouge</td><td>{_m2(t.get("ppr_rouge_m2"))}</td>'
                    f'<td class="n"><span class="chip s">Sourcé</span></td></tr>')
    if emp:
        rows.append(f'<tr><td class="k">Plafond d\'emprise</td><td>{esc(emp["regle"])}</td>'
                    f'<td class="n"><span class="chip d">Dérivé</span></td></tr>')
    return (
        '<section><h2>3. Enveloppe constructible</h2>'
        f'<div class="verdict">Zone d\'implantation de {_m2(t.get("zone_implantation_m2"))} après reculs '
        'et contraintes. Ce plafond n\'est pas ce qu\'on peut construire : c\'est le scénario (plan masse) '
        'qui le dit.</div>'
        + fig + _legende(["parcelle", "assiette", "zone", "ppr_rouge", "ppr_bleue", "voie"])
        + '<table class="kv"><tr><th>Surface</th><th>Valeur</th><th class="n">Nature</th></tr>'
        + "".join(rows) + "</table></section>")


def _p5_plan_masse(payload: dict, retenu: dict, *, titre: str = None) -> str:
    sc = retenu
    forme = str(sc.get("forme", "")).replace("_", " ")
    kinds = ["parcelle", "assiette", "zone", "espace_libre", "allee", "acces", "place",
             "batiment_emprise", "voie"]
    fig = _svg_plan(sc["geojson"], kinds, h=420)
    sm = sc.get("surfaces_mesurees_m2") or {}
    rows = [
        f'<tr><td class="k">Emprise des bâtiments</td><td>{_m2(sc.get("emprise_sol_m2"))}</td>'
        f'<td class="n"><span class="chip e">Estimé</span></td></tr>',
        f'<tr><td class="k">Places dessinées</td><td>{sc["stationnement"]["places"]}</td>'
        f'<td class="n"><span class="chip e">Estimé</span></td></tr>',
        f'<tr><td class="k">Espaces libres · dont pleine terre</td><td>{_m2(sc.get("pleine_terre_m2"))}</td>'
        f'<td class="n"><span class="chip d">Dérivé</span></td></tr>',
    ]
    acces = sc["stationnement"].get("acces")
    if acces:
        rows.append(f'<tr><td class="k">Accès</td><td>{esc(acces.get("note") or "sur la voie")}</td>'
                    f'<td class="n"><span class="chip d">Dérivé</span></td></tr>')
    h2 = titre or f"4. Plan masse du scénario {_scn_label(sc)}"
    # ETUDE-V6-4 (items 9/11) — en sous-sol, les places ne sont PAS aériennes : on le dit, et on ajoute le
    # plan du niveau −1 dessiné sur la vraie géométrie (emprise enterrée, allée, places, rampe).
    st = sc.get("stationnement") or {}
    sous_sol = (st.get("mode") == "sous_sol")
    lieu_places = "au sous-sol (niveau −1)" if sous_sol else "aériennes"
    return (
        f'<section><h2>{esc(h2)}</h2>'
        f'<div class="verdict">Scénario {esc(_scn_label(sc))} — {esc(forme)} en {esc(sc.get("niveaux_label", ""))} : '
        f'{sc["resume"]["logements"]} logements, {st.get("places")} places {lieu_places}.</div>'
        + fig + _legende(["batiment_emprise", "place", "allee", "espace_libre", "acces", "zone"])
        + '<table class="kv"><tr><th>Élément</th><th>Valeur</th><th class="n">Nature</th></tr>'
        + "".join(rows) + "</table>"
        + '<p class="note">Chaque nombre de ce tableau = nombre d\'objets dans la géométrie '
          '(verrou de test). Plan rendu depuis la géométrie servie.</p>'
        + (_sous_sol_plan(sc) if sous_sol else '')
        + '</section>')


def _fc_niveau(fc: dict, niveau: int) -> dict:
    """Sous-FeatureCollection pour UN niveau de sous-sol : l'assiette/voie (cadre) + les objets enterrés
    (emprise/allée/places/rampe) tagués `niveau`. Permet un plan PAR niveau (−1 et −2 ne se chevauchent pas)."""
    objets = {"sous_sol_emprise", "allee_ss", "place_ss", "rampe"}
    feats = []
    for f in (fc.get("features") or []):
        p = f.get("properties") or {}
        k = p.get("kind")
        if k in ("assiette", "voie"):
            feats.append(f)
        elif k in objets and p.get("niveau") == niveau:
            feats.append(f)
    return {"type": "FeatureCollection", "features": feats}


def _sous_sol_plan(sc: dict) -> str:
    """ETUDE-V6-4 (item 9) / V6-5 — UN plan PAR niveau de sous-sol choisi (−1, et −2 si 2 niveaux), DESSINÉ
    sur la vraie géométrie (contour de l'emprise, allée, places, rampe). Identique à l'écran. La capacité est
    bornée aux niveaux CHOISIS — jamais un 2ᵉ niveau supposé."""
    st = sc.get("stationnement") or {}
    par_niv = st.get("places_sous_sol_par_niveau") or 0
    niveaux = st.get("niveaux_sous_sol") or 1
    n1 = st.get("places_niveau_moins1") or 0
    n2 = st.get("places_niveau_moins2") or 0
    kinds = ["assiette", "sous_sol_emprise", "allee_ss", "place_ss", "rampe", "voie"]
    blocs = [
        f'<h3>Stationnement en sous-sol — {niveaux} niveau{"x" if niveaux > 1 else ""} '
        f'({par_niv} places / niveau)</h3>',
        f'<div class="verdict">{int(st.get("places_sous_sol") or 0)} places au total · emprise enterrée '
        f'{_m2(st.get("emprise_sous_sol_m2"))} (≤ emprise réglementaire) · rampe {_m2(st.get("rampe_m2"))}. '
        'Plan de principe dessiné sur la géométrie réelle.</div>',
        f'<h4>Niveau −1 — {n1} places</h4>',
        _svg_plan(_fc_niveau(sc["geojson"], -1), kinds, h=320),
    ]
    if niveaux >= 2 and n2 > 0:
        blocs += [f'<h4>Niveau −2 — {n2} places</h4>',
                  _svg_plan(_fc_niveau(sc["geojson"], -2), kinds, h=320)]
    blocs.append(_legende(["sous_sol_emprise", "place_ss", "allee_ss", "rampe"]))
    return "".join(blocs)


def _p_planche(payload: dict, retenu: dict) -> str:
    """La PLANCHE plan masse « façon archi » — le MÊME SVG que l'écran (servi dans le payload par
    `service.etudier_payload`), sur une page paysage pleine. Rien n'est redessiné ici."""
    svg = retenu.get("planche_svg") or ""
    if not svg:
        return ""
    # pas de <h2> ici : la planche porte SON cartouche (titre) ; un en-tête en plus débordait la page
    # paysage et laissait une page d'orphelin. On garde juste le dessin pleine page + une note discrète.
    return ('<section class="ef-planche-page"><div class="ef-planche">' + svg + '</div>'
            '<p class="note">Planche — plan masse « façon architecte », dessinée depuis la géométrie du '
            "scénario (contexte : cadastre et bâti voisins BD TOPO, voies nommées, TN LiDAR aux angles). "
            "Esquisse indicative — pas une étude d'architecte.</p></section>")


def _p6_distribution(payload: dict, retenu: dict) -> str:
    sc = retenu
    types = sorted({k for d in sc["distribution_niveaux"] for k in (d.get("par_type") or {})})
    thead = "".join(f'<th class="num">{esc(x)}</th>' for x in types)
    rows = []
    tot = {x: 0 for x in types}
    for d in sorted(sc["distribution_niveaux"], key=lambda d: -int(d.get("niveau", 0))):
        pt = d.get("par_type") or {}
        for x in types:
            tot[x] += int(pt.get(x, 0))
        cells = "".join(f'<td class="num">{int(pt.get(x, 0))}</td>' for x in types)
        niv = int(d.get("niveau", 0))
        lab = "RDC" if niv == 0 else f"R+{niv}"
        rows.append(f'<tr><td class="k">{lab}</td>{cells}<td class="num">{_grp(d.get("sdp_m2"))}</td></tr>')
    totcells = "".join(f'<td class="num">{tot[x]}</td>' for x in types)
    rows.append(f'<tr><td class="k"><strong>Total</strong></td>{totcells}'
                f'<td class="num"><strong>{_grp(sc["resume"]["sdp_m2"])}</strong></td></tr>')
    # COUPE DE PRINCIPE — le MÊME SVG que l'écran (servi dans le payload par service.etudier_payload),
    # dessiné depuis la géométrie (TN LiDAR, limites, bâtiment en coupe + niveaux, hauteurs). Repli : une
    # note seule si le dessin a échoué (jamais l'ancien schéma en dur, qui n'était pas tiré de la donnée).
    coupe_svg = retenu.get("coupe_svg") or ""
    coupe = (
        ('<div class="ef-fig">' + coupe_svg + '</div>') if coupe_svg else ''
    ) + ('<p class="note">Coupe de principe : le volume bâti sous la règle de hauteur, le terrain '
         'naturel (LiDAR), le stationnement aérien au sol. Esquisse indicative, pas une étude '
         "d'architecte.</p>")
    return (
        '<section><h2>5. Distribution et coupe</h2>'
        f'<div class="verdict">{esc(sc.get("niveaux_label", ""))} : la répartition des logements par '
        'niveau, chaque module dessiné = un logement compté.</div>'
        f'<table class="kv"><tr><th>Niveau</th>{thead}<th class="num">SDP du scénario</th></tr>'
        + "".join(rows) + "</table>" + coupe + "</section>")


def _p7_capacite(payload: dict, retenu: dict) -> str:
    sc = retenu
    prog = sc["programme"]
    pt = prog.get("par_type") or {}
    shab = prog.get("shab_par_type_m2") or {}
    surf = payload["hypotheses"].get("surfaces") or {}
    # ETUDE-V6-4 (item 11) — montrer la varangue, comme à l'écran (30/56/70/80 + varangues).
    varg = payload["hypotheses"].get("varangues") or {}
    prows = []
    for x in sorted(pt):
        vcell = f'{_m2(surf.get(x))}' + (f' <span style="color:#6b7280;font-size:0.82em">dont {_m2(varg.get(x))} varangue</span>' if varg.get(x) else '')
        prows.append(f'<tr><td class="k">{esc(x)}</td><td class="num">{int(pt[x])}</td>'
                     f'<td class="num">{vcell}</td><td class="num">{_m2(shab.get(x))}</td>'
                     f'<td class="n"><span class="chip e">Estimé</span></td></tr>')
    if prog.get("mixite_applicable") and prog.get("logements_aides_imposes") is not None:
        prows.append(f'<tr><td class="k">Dont logements aidés</td>'
                     f'<td class="num">{int(prog["logements_aides_imposes"])}</td>'
                     f'<td class="num" colspan="2">quota PLU appliqué au programme</td>'
                     f'<td class="n"><span class="chip s">Sourcé</span></td></tr>')
    # ETUDE-V6-4 (item 12) — phrase « Projet saisi par le client » corrigée (une seule fois, claire).
    prog_src = ("Programme saisi par le client (ses lignes T1–T4)." if payload["entrees"].get("programme_mode") == "saisi"
                else "Répartition proposée par le moteur pour l'objectif choisi.")
    # contrôles 4 états
    crows = []
    for c in sc["controles"]:
        res = c["resultat"]
        rc = "ok" if res == "Réussi" else "ko" if res == "Échoué" else "ne"
        cite = f'<span class="cite">{esc(c["citation"])}</span>' if (res == "Réussi" and c.get("citation")) else ""
        crows.append(f'<tr><td class="k">{esc(c["nom"])}{cite}</td><td>{esc(c["regle"])}</td>'
                     f'<td>{esc(c["mesure"])}</td>'
                     f'<td class="n"><span class="res {rc}">{esc(res)}</span></td></tr>')
    return (
        '<section><h2>6. Capacité et contrôles</h2>'
        f'<div class="verdict">Scénario {esc(_scn_label(sc))} : {sc["controles_compte"]["reussi"]} contrôles '
        f'réussis, {sc["controles_compte"]["echoue"]} échoués, {sc["controles_compte"]["non_effectue"]} '
        'non effectués. Ce n\'est pas une validation réglementaire.</div>'
        '<table class="kv"><tr><th>Programme</th><th class="num">Nombre</th><th class="num">Surface moy.</th>'
        '<th class="num">SHAB estimée</th><th class="n">Nature</th></tr>' + "".join(prows) + "</table>"
        + f'<p class="note">{esc(prog_src)}</p>'
        + '<table class="kv"><tr><th>Contrôle</th><th>Règle</th><th>Scénario</th><th class="n">Résultat</th>'
          '</tr>' + "".join(crows) + "</table>"
        + '<p class="note">Un contrôle « Échoué » retire le scénario des « Exploitable ». '
          '« Non effectué » ne vaut jamais « Réussi ».</p></section>')


def _p8_hypotheses(payload: dict, retenu: dict, numero: str) -> str:
    h = payload["hypotheses"]
    surf = h.get("surfaces") or {}
    surf_txt = " / ".join(f"{_grp(surf[k])}" for k in sorted(surf)) + " m²" if surf else "—"
    pl = h.get("place_m") or []
    place_txt = (f"{_dec(pl[0])} × {_dec(pl[1])} m · allée {_dec(h.get('allee_largeur_m'))} m"
                 if len(pl) == 2 else "—")
    hrows = [
        ("Profondeur de bâtiment", f"{_grp(h.get('profondeur_m'))} m", "logements traversants, coursive extérieure"),
        ("Surface moyenne par type", surf_txt, "modifiable"),
        ("Plancher → habitable", _dec(h.get('coef_plancher_habitable')), "circulations et noyaux hors habitable"),
        ("Place · allée", place_txt, "dimensions usuelles"),
        ("Hauteur de niveau", f"{_grp(h.get('hauteur_etage_m'))} m", "convention"),
        # ETUDE-V6-4/5 (items 11/12) — le MODE réel + le nombre de niveaux CHOISI (hypothèse explicite).
        ("Stationnement", _stationnement_label(retenu, payload["entrees"]),
         "aérien (au sol) ou sous-sol (niveaux choisis : −1, ou −1 et −2)"),
    ]
    hrows_html = "".join(f'<tr><td class="k">{esc(a)}</td><td>{b}</td><td>{esc(c)}</td></tr>'
                         for a, b, c in hrows)
    confier = [
        ("Distance entre constructions · locaux vélos et déchets", "règles non modélisées"),
        ("Prescriptions PPR bleue · servitudes signalées", "signalées, non interprétées"),
        ("Accès véhicule", "limite classée voie ; visibilité et autorisation non vérifiées"),
        ("Sol, réseaux, arbres, vues, voisinage", "aucune donnée publique fiable à la parcelle"),
        ("Conception (plans, façades)", "métier de l'architecte"),
    ]
    conf_html = "".join(f'<tr><td class="k">{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in confier)
    m = payload["moteur"]
    sources = [
        (f"PLU — zone {esc(payload['regles'].get('zone') or '')}", "règlement, zonage, prescriptions publiés"),
        ("Cadastre DGFiP · PPR, servitudes (GPU, Géorisques)", "données publiques"),
        ("LiDAR HD IGN · BD TOPO", "terrain naturel, limites"),
        # ETUDE-V6-4 (item 12) — plus de nom technique (livrable IMPLANTATION-2, version conventions).
        ("Moteur d'implantation LABUSE", f"hypothèses « {esc(m.get('etiquette') or 'Estimé')} », modifiables dans l'outil"),
    ]
    src_html = "".join(f'<tr><td class="k">{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in sources)
    return (
        '<section><h2>7. Hypothèses, limites, sources</h2>'
        '<div class="verdict neutral">Ce que l\'étude suppose, ce qu\'elle ne sait pas, d\'où viennent '
        'les chiffres.</div>'
        '<h3>Hypothèses (toutes « Estimé », modifiables dans l\'outil)</h3>'
        '<table class="kv"><tr><th>Hypothèse</th><th>Valeur</th><th>Convention</th></tr>'
        + hrows_html + "</table>"
        '<h3>À faire confirmer par l\'architecte</h3>'
        '<table class="kv"><tr><th>Point</th><th>Pourquoi</th></tr>' + conf_html + "</table>"
        '<h3>Sources</h3><table class="kv"><tr><th>Source</th><th>Nature</th></tr>' + src_html + "</table>"
        f'<p class="note">Entrées, configuration, version du moteur et des règles archivées avec le '
        f'document n° {esc(numero)} : le scénario se rejoue à l\'identique.</p></section>')


def _annexe_reglement(payload: dict) -> str:
    """ETUDE-V6-4 (item 3) — annexe « extraits du règlement » : pour chaque règle, l'extrait VERBATIM
    (texte cité), l'article, la page et le millésime, avec le lien vers le document PLU officiel — les
    mêmes éléments que « Lire l'article » à l'écran. Rien d'affiché qui ne soit dans le payload."""
    r = payload["regles"]
    lignes = [l for l in r.get("lignes", []) if l.get("citation")]
    if not lignes:
        return ""
    mill = r.get("millesime")
    doc_url = r.get("source_url")
    blocs = []
    for l in lignes:
        art = l.get("article")
        pg = l.get("page_pdf")
        ref = " · ".join(x for x in (
            f"art. {esc(str(art))}" if art else None,
            f"p. {esc(str(pg))}" if pg is not None else None,
            f"millésime {esc(str(l.get('millesime') or mill))}" if (l.get("millesime") or mill) else None,
        ) if x)
        blocs.append(
            f'<div class="art"><div class="art-ref">{esc(l.get("nom") or "")}{(" — " + ref) if ref else ""}</div>'
            f'<div class="art-cit">« {esc(l.get("citation"))} »</div></div>')
    lien = (f'<p class="note">Document PLU officiel : <span class="url">{esc(doc_url)}</span></p>'
            if doc_url else '<p class="note">Document PLU officiel non disponible en lien direct.</p>')
    return (
        '<div class="pb"></div>'
        '<section><h2>Annexe — extraits du règlement</h2>'
        f'<div class="verdict">PLU de {esc(r.get("commune") or "")} · zone {esc(r.get("zone") or "")}'
        f'{(" · millésime " + esc(str(mill))) if mill else ""}. Chaque règle appliquée est citée mot pour mot.</div>'
        + "".join(blocs) + lien + '</section>')


def _annexe(payload: dict, retenu: dict) -> str:
    """Les autres scénarios (hors retenu) : un plan masse par scénario, en annexe."""
    autres = [s for s in (payload.get("scenarios") or []) if s["ref"] != retenu["ref"]]
    if not autres:
        return ""
    out = ['<div class="pb"></div>']
    for s in autres:
        out.append(_p5_plan_masse(payload, s, titre=f"Annexe — plan masse du scénario {_scn_label(s)}"))
    return "".join(out)


# ════════════════════════════════════════════════════════════════════════════════════════════
# n° de document : source UNIQUE dans implantation.planche (partagée planche + PDF).
from labuse.implantation.planche import numero_etude   # noqa: E402,F401


def rendu_etude(payload: dict, *, genere_le: str, scenario_ref: Optional[str] = None) -> dict:
    """payload (/modules/etude) → {html, numero, retenu_ref}. HTML prêt pour `rendu.render_pdf`.
    Lève ValueError si aucun scénario (le document n'a rien à montrer)."""
    retenu = scenario_retenu(payload, scenario_ref)
    if retenu is None:
        raise ValueError(payload.get("message") or "aucun scénario : l'étude ne peut pas être rendue")
    idus = payload["entrees"].get("idus") or []
    numero = numero_etude(idus, genere_le)
    refs = _refs_parcelles(payload)
    cart = Cartouche(
        doc_title=f"LABUSE — Étude de faisabilité · {payload['terrain'].get('commune') or ''}",
        doc_ref=f"{refs} · {numero}",
        doc_foot=(f"Étude de faisabilité · {refs} · scénario {_scn_label(retenu)} · "
                  f"Généré via LABUSE le {genere_le} · pré-faisabilité, non contractuel"))
    corps = (
        f"<style>{_STYLE}</style>"
        + _p1_synthese(payload, retenu, numero, genere_le)
        + _p2_terrain(payload, retenu)
        + _p3_regles(payload, retenu)
        + _stationnement_3lignes(payload, retenu)
        + _p4_enveloppe(payload, retenu)
        + _p5_plan_masse(payload, retenu)
        + _p_planche(payload, retenu)
        + _p6_distribution(payload, retenu)
        + _p7_capacite(payload, retenu)
        + _p8_hypotheses(payload, retenu, numero)
        + _annexe_reglement(payload)
        + _annexe(payload, retenu))
    html = page_html("Étude de faisabilité", cart, corps)
    return {"html": html, "numero": numero, "retenu_ref": retenu["ref"]}


def rendu_lotissement(payload: dict, *, genere_le: str) -> dict:
    """ETUDE-V6 (Lot E) — PDF du LOTISSEMENT depuis le MÊME payload que l'écran (même study_id, mêmes
    chiffres : verrou `nombres_hors_payload`). Tableau des lots, voirie, pleine terre (contrôle), bilan
    surfacique CLOS, stationnement, raccordements, régime. Ne rend que des nombres du payload."""
    def fr(x):
        return "—" if x is None else (f"{x:,.0f}".replace(",", " ") if abs(x) >= 1000 else
                                      (f"{x:.0f}" if float(x).is_integer() else f"{x:.1f}".replace(".", ",")))
    lot = payload["lotissement"]
    idus = payload["entrees"].get("idus") or []
    numero = payload.get("study_id") or numero_etude(idus, genere_le)
    tl, pt, b, st = lot["tableau_lots"], lot["pleine_terre"], lot["bilan_surfacique"], lot["stationnement"]
    commune, zone = lot.get("commune") or "", lot.get("zone") or ""
    cart = Cartouche(
        doc_title=f"LABUSE — Lotissement · {commune}",
        doc_ref=f"{idus[0][8:] if idus else ''} · {numero}",
        doc_foot=f"Lotissement · zone {zone} · Généré via LABUSE le {genere_le} · pré-faisabilité, non contractuel")
    lignes = "".join(f"<tr><td>Lot {i}</td><td class='n'>{fr(s)} m²</td></tr>"
                     for i, s in enumerate(tl["surfaces_m2"], 1))
    racc = "".join(f"<tr><td>{r['reseau']}</td><td class='n'>{'non vérifié' if r['distance_m'] is None else fr(r['distance_m'])+' m'}</td></tr>"
                   for r in lot["raccordements"])
    # ETUDE-V6-6 (item 1) — article de règle servie ou « règle non servie » ; (item 2) — raison si 0 lot.
    pt_art = esc(pt["article"]) if pt.get("article") else "règle non servie (hypothèse)"
    st_art = esc(st["article"]) if st.get("article") else "hypothèse (barème non servi)"
    raison_html = ""
    if tl["nombre"] == 0 and lot.get("raison"):
        raison_html = (f"<div class='aside rose'><b>Aucun lot dessinable.</b> {esc(lot['raison'])}"
                       + (f" <b>Ce qui le permettrait :</b> {esc(lot['remede'])}" if lot.get("remede") else "")
                       + "</div>")
    corps = (
        f"<style>{_STYLE}</style>"
        f"<section class='page'><h1>Lotissement — {commune} · zone {zone}</h1>"
        f"<p class='sub'>Division foncière indicative (pré-faisabilité). {lot['note']}</p>"
        + raison_html
        + f"<div class='kpis'><div class='kpi'><b>{fr(tl['nombre'])}</b><span>lots</span></div>"
        f"<div class='kpi'><b>{fr(tl['surface_moyenne_m2'])} m²</b><span>surface moyenne</span></div>"
        f"<div class='kpi'><b>{fr(lot['voirie_m2'])} m²</b><span>voirie · {lot['voirie_config']}</span></div></div>"
        f"<h2>Pleine terre — {pt['resultat']}</h2>"
        f"<p>{fr(pt['estimee_m2'])} m² (jardins privatifs {fr(pt['jardins_privatifs_m2'])} + communs "
        f"{fr(pt['communs_m2'])}) pour {fr(pt['exigee_m2'])} m² exigés ({fr(pt['exigee_pct'])} % · {pt_art}).</p>"
        f"<h2>Stationnement</h2><p>{fr(st['total_lots'])} places ({fr(st['par_lot'])}/lot · {st_art}) "
        f"+ {fr(st['visiteurs_estimes'])} visiteurs (estimé).</p>"
        f"<h2>Bilan surfacique {'(clos)' if b['clos'] else '(à ajuster)'}</h2>"
        f"<table class='t'><tr><td>Lots</td><td class='n'>{fr(b['lots_m2'])} m²</td></tr>"
        f"<tr><td>Voirie</td><td class='n'>{fr(b['voirie_m2'])} m²</td></tr>"
        f"<tr><td>Espaces communs</td><td class='n'>{fr(b['communs_m2'])} m²</td></tr>"
        f"<tr><td>PPR rouge (retiré)</td><td class='n'>{fr(b['ppr_rouge_m2'])} m²</td></tr>"
        f"<tr><td>Hors zone (A/N, marges)</td><td class='n'>{fr(b['hors_zone_m2'])} m²</td></tr>"
        f"<tr class='tot'><td>Total = assiette</td><td class='n'>{fr(b['somme_m2'])} m² (écart {fr(b['ecart_m2'])})</td></tr></table>"
        f"<h2>Raccordements</h2><table class='t'>{racc}</table>"
        f"<p class='note'>{lot['min_lot_plu']['note']}</p>"
        f"<p class='note'>{lot['regime_procedural']}</p></section>"
        f"<section class='page'><h2>Tableau des lots</h2><table class='t'>{lignes}</table></section>")
    html = page_html("Lotissement", cart, corps)
    return {"html": html, "numero": numero, "retenu_ref": "lotissement"}


# ── verrou « toute ligne du PDF est une ligne de l'outil » ────────────────────────────────────
#: un nombre = groupes de 3 chiffres séparés par une espace de MILLIERS (« 1 746 »), OU un entier/décimal.
#: Ne franchit pas une espace ordinaire autre qu'un groupe de 3 → deux cellules adjacentes (« AW 99 »
#: puis « 501 ») ne fusionnent pas (les balises sont remplacées par des sauts de ligne avant lecture).
_RE_NB = re.compile(r"\d{1,3}(?:[\s\u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def _canon(tok: str) -> str:
    """Forme canonique d'un nombre : espaces retirées, décimale en point, zéros/point final élagués.
    « 1 746 »→« 1746 » · « 2,5 »→« 2.5 » · « 500,0 »→« 500 » · « 0,80 »→« 0.8 »."""
    s = re.sub(r"[\s\u00a0\u202f]", "", tok)
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _nombres(texte: str) -> list[str]:
    return [c for m in _RE_NB.findall(texte) if (c := _canon(m))]


def _texte_sans_balises(html_str: str) -> str:
    import html as _h
    s = re.sub(r"<style.*?</style>", "\n", html_str, flags=re.S)
    s = re.sub(r"<svg.*?</svg>", "\n", s, flags=re.S)         # le SVG est un dessin, pas une ligne
    s = re.sub(r"<[^>]+>", "\n", s)                           # saut de ligne = coupe les runs de chiffres
    return _h.unescape(s)                                     # &#x27; → ' (l'entité n'est pas un nombre)


def _ancres(obj, out: set) -> None:
    """Ancres numériques du payload : CHAQUE nombre servi, sous sa forme exacte ET arrondie (le document
    arrondit les m² à l'entier, comme l'écran et la maquette) ; et les nombres NICHÉS dans les chaînes
    servies (les contrôles portent « ≤ 1222 m² (70 % …) », « R+2 ≈ 9 m »…)."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        f = float(obj)
        out.add(_canon(repr(obj)))
        out.add(_canon(str(int(round(f)))))     # m² arrondi affiché
        out.add(_canon(f"{f:.1f}"))              # 1 décimale (pente, ratios)
    elif isinstance(obj, str):
        out.update(_nombres(obj))                # nombres dans les chaînes de contrôle/règle
    elif isinstance(obj, dict):
        for v in obj.values():
            _ancres(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _ancres(v, out)


def nombres_hors_payload(payload: dict, html: str, *, genere_le: str = "") -> list[str]:
    """Liste des nombres IMPRIMÉS (hors SVG, hors structure) absents du payload servi. Doit être vide :
    c'est le verrou « toute ligne du PDF est une ligne de l'outil » (extension V5d/V5f)."""
    ancres: set = set()
    _ancres(payload, ancres)
    # jetons de structure tolérés : pagination 1..9, date du jour, n° de document, codes EPSG, année.
    struct = {str(i) for i in range(0, 10)}                       # pagination + petits indices de texte
    struct |= set(_nombres(genere_le)) | set(_nombres(numero_etude(payload["entrees"].get("idus") or [], genere_le)))
    struct |= {"2975", "4326"}                                     # CRS cités dans le payload moteur de toute façon
    for p in payload["terrain"].get("parcelles", []):             # refs cadastrales (AW 99…)
        struct |= set(_nombres(p.get("numero") or ""))
        struct |= set(_nombres((p.get("idu") or "")))
    manquants = []
    for n in _nombres(_texte_sans_balises(html)):
        if n in ancres or n in struct:
            continue
        # un entier contenu dans une ancre (p.ex. « 12 » dans « 1222 ») n'est pas une fuite s'il figure
        # tel quel ailleurs ; on exige l'égalité stricte, donc on ne fait PAS de sous-chaîne.
        manquants.append(n)
    return manquants
