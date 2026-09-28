#!/usr/bin/env python
"""PLU-VERIF-1 Lot A — vérificateur automatique.

Pour chaque règle calibrée (bloc `regles` : hauteur, emprise, reculs, pleine
terre, stationnement, mixité), ouvre le PDF du règlement servi, lit le texte de
la page citée (±1), y cherche l'article et la VALEUR (dans ses formes), détecte
les exceptions, et rend un verdict TROUVÉ / AMBIGU / ABSENT / ILLISIBLE.

Livrable : docs/audit-2026-09/PLU-VERIF-1/REGLES.csv
Sert aussi de socle à `labuse plu-verif` (Lot D).
"""
import sys, csv, re, json, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
import fitz  # PyMuPDF
from labuse.plu import destinations as D

PDF_DIR = Path.home() / "Desktop" / "labuse" / "data" / "plu_reglements"
OUT = REPO / "docs/audit-2026-09/PLU-VERIF-1"

# Marqueurs d'une VRAIE dérogation/valeur alternative (pas les connecteurs boilerplate
# « en cas de retrait… » qui ouvrent la règle elle-même). Le mandat vise l'exception
# qu'une fiche pourrait masquer.
EXCEPTION_MOTS = [
    "sauf", "toutefois", "a l'exception", "excepte", "hormis",
    "dans le secteur", "dans les secteurs", "derogation",
    "a l'exclusion", "ne s'applique pas", "par exception", "a titre exceptionnel",
]

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def norm(s: str) -> str:
    s = strip_accents((s or "").lower())
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace(" ", " ").replace(" ", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# ---- PDF cache -----------------------------------------------------------
_PDF = {}
def pages_norm(insee: str):
    if insee in _PDF:
        return _PDF[insee]
    etat = D.etat_commune(insee)
    doc_name = etat.get("document")
    p = PDF_DIR / doc_name if doc_name else None
    if not p or not p.exists():
        _PDF[insee] = None
        return None
    d = fitz.open(str(p))
    pages = [norm(d[i].get_text()) for i in range(d.page_count)]
    d.close()
    _PDF[insee] = pages
    return pages

# ---- value forms ---------------------------------------------------------
MOTS_NB = {0:"zero",1:"un",2:"deux",3:"trois",4:"quatre",5:"cinq",6:"six",7:"sept",
           8:"huit",9:"neuf",10:"dix",11:"onze",12:"douze",13:"treize",14:"quatorze",
           15:"quinze",16:"seize",17:"dix-sept",18:"dix-huit",19:"dix-neuf",20:"vingt",
           25:"vingt-cinq",30:"trente",40:"quarante",50:"cinquante",60:"soixante",
           70:"soixante-dix",75:"soixante-quinze",80:"quatre-vingts",90:"quatre-vingt-dix",100:"cent"}

def _num_variants(x: float):
    """Formes numériques nues d'un nombre (sans unité) : entier ou décimal virgule/point."""
    out = set()
    if x == int(x):
        i = int(x)
        out.add(str(i))
        out.add(f"{i},0"); out.add(f"{i}.0")
        if i in MOTS_NB:
            out.add(MOTS_NB[i])
    else:
        s = f"{x:g}"
        out.add(s.replace(".", ",")); out.add(s.replace(",", "."))
    return out

def _re_num(v: str) -> str:
    # borne : pas de chiffre collé de part et d'autre. Tolère les zéros de queue :
    # entier « 3 » ↔ « 3,00 » ; décimal « 1,9 » ↔ « 1,90 ». Virgule ou point.
    m = re.fullmatch(r"(\d+)(?:[.,](\d+))?", v)
    if not m:
        return r"(?<![\d.,])" + re.escape(v) + r"(?![\d])"
    ent, frac = m.group(1), m.group(2)
    if frac is None:
        core = re.escape(ent) + r"(?:[.,]0+)?"
    else:
        core = re.escape(ent) + r"[.,]" + re.escape(frac) + r"0*"
    return r"(?<![\d.,])" + core + r"(?![\d])"

def value_regexes(rubrique_sous: str, feuille: dict):
    """Retourne (liste_regex_compilées, valeur_affichee, multi_secteur_bool, sans_valeur_bool)."""
    multi = any(k in feuille for k in ("plage", "plage_m", "plage_pct",
                                       "secteurs_m", "secteurs_pct"))
    r = rubrique_sous
    regs, disp = [], None
    def meters(val):
        vs = _num_variants(val)
        pats = []
        for v in vs:
            if v in MOTS_NB.values():
                pats.append(v + r"\s+metres?")
            else:
                pats.append(_re_num(v) + r"\s*(m\b|metres?|ml\b)")
        return pats
    def pct(val):
        vs = _num_variants(val)
        pats = []
        for v in vs:
            pats.append(_re_num(v) + r"\s*(%|pour ?cent)")
        # forme fraction 0,X
        frac = val / 100.0
        fs = f"{frac:g}"
        pats.append(_re_num(fs.replace(".", ",")))
        pats.append(_re_num(fs.replace(",", ".")))
        return pats
    if r in ("hauteur.faitage", "hauteur.egout"):
        if "m" in feuille and feuille["m"] is not None:
            disp = f"{feuille['m']} m"; regs = meters(float(feuille["m"]))
    elif r == "hauteur.niveaux":
        rp = feuille.get("r_plus")
        if rp is not None:
            disp = f"R+{rp}"
            regs = [r"r\s*\+\s*" + re.escape(str(int(rp)))]
    elif r == "emprise_sol.ces":
        if "pct" in feuille and feuille["pct"] is not None:
            disp = f"{feuille['pct']} %"; regs = pct(float(feuille["pct"]))
    elif r == "pleine_terre.pct":
        if "pct" in feuille and feuille["pct"] is not None:
            disp = f"{feuille['pct']} %"; regs = pct(float(feuille["pct"]))
        elif "espaces_verts_pct" in feuille:
            ev = feuille.get("espaces_verts_pct")
            disp = f"{ev}% ev × {feuille.get('pleine_terre_part')}"
            regs = pct(float(ev)) if ev is not None else []
            multi = True  # composée → à lire
    elif r in ("retraits.voie", "retraits.limites_separatives"):
        if "min_m" in feuille and feuille["min_m"] is not None:
            disp = f"{feuille['min_m']} m"; regs = meters(float(feuille["min_m"]))
        if "formule" in feuille:
            disp = (disp + " +formule") if disp else "formule"
    elif r == "stationnement.par_logement":
        pl = feuille.get("places")
        if pl is not None:
            disp = f"{pl} place(s)"
            vs = _num_variants(float(pl))
            regs = [_re_num(v) + r"\s*place" for v in vs] + [_re_num(v) for v in vs]
    elif r == "mixite":
        sl = feuille.get("seuil_logements"); q = feuille.get("quota_pct")
        disp = f"seuil {sl} log / quota {q}%"
        regs = []
        if q is not None:
            regs += pct(float(q))
    sans_val = (not regs) and disp is None
    compiled = [re.compile(p) for p in regs]
    return compiled, disp, multi, sans_val

def _art_core(article: str):
    """Noyau d'article cherchable : 'Ua 10.2' -> regex 'ua\\s*10' ; 'U2 6.2/7.3' -> 'u2\\s*6'."""
    a = norm(article)
    a = re.sub(r"^articles?\s+", "", a)
    m = re.match(r"([a-z0-9]+)\D+(\d+)", a)
    if m:
        return re.compile(re.escape(m.group(1)) + r"\s*" + re.escape(m.group(2)))
    m2 = re.match(r"([a-z0-9]+)", a)
    return re.compile(re.escape(m2.group(1))) if m2 else None

def cite_hit(cite_n: str, page_texts: list) -> bool:
    """La citation (normalisée) est-elle présente sur l'une des pages ? Substring exact
    sinon fort recouvrement de tokens (>0.85) sur une fenêtre glissante grossière."""
    if not cite_n or len(cite_n) < 12:
        return False
    frag = cite_n[:90]
    for t in page_texts:
        if not t:
            continue
        if frag in t or cite_n in t:
            return True
    # recouvrement de tokens (citation tronquée/coupée par retour ligne)
    toks = [w for w in cite_n.split() if len(w) > 3]
    if len(toks) < 5:
        return False
    for t in page_texts:
        if not t:
            continue
        hit = sum(1 for w in toks if w in t)
        if hit / len(toks) >= 0.85:
            return True
    return False

def exception_near(page_text: str, reg: re.Pattern, cite_n: str) -> bool:
    """Une exception que la citation LABUSE n'a PAS captée mais qui figure sur la page,
    près de la valeur. Si le marqueur est DANS la citation, LABUSE l'a déjà quotée →
    pas d'alerte (c'est capté)."""
    in_cite = any(m in cite_n for m in EXCEPTION_MOTS)
    if not page_text or reg is None:
        return False
    m = reg.search(page_text)
    if not m:
        return False
    lo, hi = max(0, m.start() - 260), min(len(page_text), m.end() + 260)
    win = page_text[lo:hi]
    on_page = any(mot in win for mot in EXCEPTION_MOTS)
    # exception sur la page ET absente de la citation = potentiellement masquée par la fiche
    return on_page and not in_cite

def distinct_same_unit(page_text: str, rubrique_sous: str) -> int:
    """Nb de valeurs distinctes de la même unité sur la page (indice de multi-candidats)."""
    if not page_text:
        return 0
    if rubrique_sous in ("hauteur.faitage", "hauteur.egout",
                         "retraits.voie", "retraits.limites_separatives"):
        vals = re.findall(r"(?<![\d.,])(\d{1,2}(?:[.,]\d)?)\s*(?:m\b|metres?)", page_text)
    elif rubrique_sous in ("emprise_sol.ces", "pleine_terre.pct"):
        vals = re.findall(r"(?<![\d.,])(\d{1,3})\s*%", page_text)
    else:
        return 0
    return len({v.replace(".", ",") for v in vals})

def main():
    rows = list(D.iter_regles_calibrees())
    out_rows = []
    counts = {"TROUVE": 0, "AMBIGU": 0, "ABSENT": 0, "ILLISIBLE": 0}
    for r in rows:
        insee = r["insee"]; zone = r["zone"]; chemin = r["chemin"]
        article = (r.get("article") or "").strip()
        page = r.get("page_pdf")
        statut = (r.get("statut") or "").strip().lower()
        cite = r.get("citation") or ""
        cite_n = norm(cite)
        absent_flag = bool(r.get("absent"))
        pages = pages_norm(insee)

        regs, disp, multi, sans_val = value_regexes(chemin, r)

        # fenêtre de pages ±1 (page_pdf 1-based → index page-1)
        page_texts, primary = [], ""
        if pages and isinstance(page, int) and 1 <= page <= len(pages):
            idx = page - 1
            primary = pages[idx]
            for j in (idx - 1, idx, idx + 1):
                if 0 <= j < len(pages):
                    page_texts.append(pages[j])
        elif pages is None:
            out_rows.append([insee, zone, chemin, disp or "", page, article,
                             "ABSENT", "PDF introuvable"]); counts["ABSENT"] += 1
            continue

        chit = cite_hit(cite_n, page_texts)
        acore = _art_core(article) if article else None
        ahit = any(acore.search(t) for t in page_texts) if acore else False

        # texte pour extrait
        def extrait():
            if cite:
                return cite[:300]
            return (primary[:300] if primary else "")

        # --- ILLISIBLE : page vide (scan sans texte)
        if pages and (not any(page_texts) or (primary == "" and sum(len(t) for t in page_texts) < 40)):
            out_rows.append([insee, zone, chemin, disp or "", page, article,
                             "ILLISIBLE", "page sans texte (OCR requis)"]); counts["ILLISIBLE"] += 1
            continue

        # --- feuille sans valeur numérique (absent / exempt / sans_objet)
        if absent_flag or sans_val:
            if chit:
                v = "TROUVE"; note = "silence/exemption prouvé (citation sur la page)"
            elif ahit:
                v = "AMBIGU"; note = "article présent, citation non retrouvée"
            else:
                v = "ABSENT"; note = "citation d'absence non retrouvée"
            out_rows.append([insee, zone, chemin, disp or "(sans valeur)", page,
                             article, v, note + " | " + extrait()[:200]])
            counts[v] += 1
            continue

        # --- recul « à l'alignement » (min_m = 0, forme alignement) : la valeur 0 ne
        #     s'écrit pas « 0 m » mais « à l'alignement » / « en limite »
        is_align = chemin.startswith("retraits") and (
            r.get("forme") == "alignement" or r.get("min_m") == 0)
        if is_align:
            mots_al = ("alignement", "en limite", "sur la limite", "sur les limites")
            al_on = chit or any(any(mt in t for mt in mots_al) for t in page_texts)
            if al_on:
                v = "TROUVE"; note = "implantation à l'alignement/en limite (recul 0 explicite)"
            elif ahit:
                v = "AMBIGU"; note = "article présent, mention alignement non retrouvée"
            else:
                v = "ABSENT"; note = "mention alignement/limite introuvable"
            out_rows.append([insee, zone, chemin, disp or "0 m", page, article, v,
                             (note + " | " + extrait())[:300]]); counts[v] += 1
            continue

        # --- recul en formule seule (prospect, sans min_m) : vérifier la citation
        if chemin.startswith("retraits") and not regs and (r.get("formule") or disp == "formule"):
            if chit:
                v = "TROUVE"; note = "règle en formule (prospect) — citation sur la page"
            elif ahit:
                v = "AMBIGU"; note = "formule : article présent, citation non retrouvée"
            else:
                v = "ABSENT"; note = "formule : citation introuvable"
            out_rows.append([insee, zone, chemin, disp or "formule", page, article, v,
                             (note + " | " + extrait())[:300]]); counts[v] += 1
            continue

        # --- multi-secteur (plage / secteurs / pleine terre composée) → à lire
        if multi:
            out_rows.append([insee, zone, chemin, disp or "", page, article,
                             "AMBIGU", "valeur variable par secteur/composée | " + extrait()[:220]])
            counts["AMBIGU"] += 1
            continue

        # --- règle numérique standard
        val_on = None
        for reg in regs:
            for t in page_texts:
                if reg.search(t):
                    val_on = reg; break
            if val_on:
                break
        val_in_cite = any(reg.search(cite_n) for reg in regs)
        exc = exception_near(primary or (page_texts[0] if page_texts else ""),
                             val_on, cite_n) if val_on else any(m in cite_n for m in EXCEPTION_MOTS)
        ndist = distinct_same_unit(primary, chemin)

        if val_on is None:
            v = "ABSENT"; note = "valeur introuvable sur page±1"
        elif chit and val_in_cite and not exc:
            v = "TROUVE"; note = "citation+valeur sur la page, article %s" % ("ok" if ahit else "≠?")
        elif exc:
            v = "AMBIGU"; note = "valeur présente mais exception dans le paragraphe"
        elif ndist > 1 and not (chit and val_in_cite):
            v = "AMBIGU"; note = f"{ndist} valeurs candidates (même unité) sur la page"
        elif val_in_cite and ahit:
            v = "TROUVE"; note = "valeur dans la citation, article sur la page"
        elif not ahit:
            v = "AMBIGU"; note = "valeur sur la page mais article non localisé"
        else:
            v = "AMBIGU"; note = "valeur sur la page, citation non alignée"
        out_rows.append([insee, zone, chemin, disp or "", page, article, v,
                         (note + " | " + extrait())[:300]])
        counts[v] += 1

    # chaque itération a produit exactement une ligne, dans l'ordre de `rows` :
    # on réinjecte statut + raison de calibration (pré-signalements de l'équipe).
    assert len(out_rows) == len(rows), (len(out_rows), len(rows))
    enr = []
    for src, o in zip(rows, out_rows):
        # o = [insee, zone, chemin, disp, page, article, verdict, note]
        enr.append(o[:6] + [(src.get("statut") or ""), (src.get("raison") or "")[:160]] + o[6:])
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "REGLES.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["insee", "zone", "regle", "valeur_labuse", "page", "article",
                    "statut", "raison_calibration", "verdict", "note_extrait"])
        w.writerows(enr)
    print("verdicts:", counts, "total", sum(counts.values()))
    (OUT / "verdicts_auto.json").write_text(json.dumps(counts, ensure_ascii=False))

if __name__ == "__main__":
    main()
