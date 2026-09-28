"""PLU-VERIF-1 — vérificateur permanent des règles chiffrées calibrées.

Pour chaque feuille du bloc `regles` d'une zone calibrée (hauteur, emprise,
reculs, pleine terre, stationnement, mixité), ouvre le PDF du règlement servi
(millésime au catalogue), lit le texte de la page citée (±1), y cherche l'article
et la VALEUR dans ses formes (« 9 m », « neuf mètres », « 60 % », « 0,6 »,
« R+2 », « 1,90 mètre », « à l'alignement »…), détecte les exceptions non quotées,
et rend un verdict automatique :

  TROUVE    l'article et la valeur sont sur la page, dans le paragraphe cité.
  AMBIGU    valeur sur la page mais exception/sous-secteur/valeurs multiples → à relire.
  ABSENT    article ou valeur introuvable sur la page citée (±1).
  ILLISIBLE page sans couche texte (scan → OCR requis).

C'est le socle de la commande `labuse plu verif` (rejouée à chaque nouvelle règle
validée / nouveau millésime — cf. sentinelle du Circuit) et de l'onglet Cohérence.

Les PDF des règlements sont cherchés dans (par ordre) :
  $LABUSE_PLU_PDF_DIR · data/plu_reglements/ (repo) · ~/Desktop/labuse/data/plu_reglements/
"""
from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from pathlib import Path

from . import destinations as D

_REPO = Path(__file__).resolve().parents[3]


def pdf_dir() -> Path:
    """Répertoire des règlements PDF (env prioritaire, puis repo, puis worktree voisin)."""
    cands = []
    if os.environ.get("LABUSE_PLU_PDF_DIR"):
        cands.append(Path(os.environ["LABUSE_PLU_PDF_DIR"]))
    cands.append(_REPO / "data" / "plu_reglements")
    cands.append(Path.home() / "Desktop" / "labuse" / "data" / "plu_reglements")
    for c in cands:
        if c.is_dir():
            return c
    return cands[0]


# Marqueurs d'une VRAIE dérogation / valeur alternative — PAS les connecteurs
# boilerplate (« en cas de retrait… ») qui ouvrent la règle elle-même. Le mandat
# vise l'exception qu'une fiche pourrait masquer.
EXCEPTION_MOTS = [
    "sauf", "toutefois", "a l'exception", "excepte", "hormis",
    "dans le secteur", "dans les secteurs", "derogation",
    "a l'exclusion", "ne s'applique pas", "par exception", "a titre exceptionnel",
]

MOTS_NB = {0: "zero", 1: "un", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six",
           7: "sept", 8: "huit", 9: "neuf", 10: "dix", 11: "onze", 12: "douze", 13: "treize",
           14: "quatorze", 15: "quinze", 16: "seize", 17: "dix-sept", 18: "dix-huit",
           19: "dix-neuf", 20: "vingt", 25: "vingt-cinq", 30: "trente", 40: "quarante",
           50: "cinquante", 60: "soixante", 70: "soixante-dix", 75: "soixante-quinze",
           80: "quatre-vingts", 90: "quatre-vingt-dix", 100: "cent"}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def _num_variants(x: float) -> set[str]:
    out: set[str] = set()
    if x == int(x):
        i = int(x)
        out.add(str(i)); out.add(f"{i},0"); out.add(f"{i}.0")
        if i in MOTS_NB:
            out.add(MOTS_NB[i])
    else:
        s = f"{x:g}"
        out.add(s.replace(".", ",")); out.add(s.replace(",", "."))
    return out


def _re_num(v: str) -> str:
    """Nombre borné (pas de chiffre collé), tolérant aux zéros de queue :
    entier « 3 » ↔ « 3,00 » ; décimal « 1,9 » ↔ « 1,90 »."""
    m = re.fullmatch(r"(\d+)(?:[.,](\d+))?", v)
    if not m:
        return r"(?<![\d.,])" + re.escape(v) + r"(?![\d])"
    ent, frac = m.group(1), m.group(2)
    core = re.escape(ent) + (r"(?:[.,]0+)?" if frac is None
                             else r"[.,]" + re.escape(frac) + r"0*")
    return r"(?<![\d.,])" + core + r"(?![\d])"


def _value_regexes(rubrique_sous: str, feuille: dict):
    """(regex compilées, valeur_affichée, multi_secteur, sans_valeur)."""
    multi = any(k in feuille for k in ("plage", "plage_m", "plage_pct",
                                       "secteurs_m", "secteurs_pct"))
    r = rubrique_sous
    regs, disp = [], None

    def meters(val):
        pats = []
        for v in _num_variants(val):
            if v in MOTS_NB.values():
                pats.append(v + r"\s+metres?")
            else:
                pats.append(_re_num(v) + r"\s*(m\b|metres?|ml\b)")
        return pats

    def pct(val):
        pats = [_re_num(v) + r"\s*(%|pour ?cent)" for v in _num_variants(val)]
        frac = f"{val / 100.0:g}"
        pats.append(_re_num(frac.replace(".", ",")))
        pats.append(_re_num(frac.replace(",", ".")))
        return pats

    if r in ("hauteur.faitage", "hauteur.egout"):
        if feuille.get("m") is not None:
            disp = f"{feuille['m']} m"; regs = meters(float(feuille["m"]))
    elif r == "hauteur.niveaux":
        rp = feuille.get("r_plus")
        if rp is not None:
            disp = f"R+{rp}"; regs = [r"r\s*\+\s*" + re.escape(str(int(rp)))]
    elif r == "emprise_sol.ces":
        if feuille.get("pct") is not None:
            disp = f"{feuille['pct']} %"; regs = pct(float(feuille["pct"]))
    elif r == "pleine_terre.pct":
        if feuille.get("pct") is not None:
            disp = f"{feuille['pct']} %"; regs = pct(float(feuille["pct"]))
        elif "espaces_verts_pct" in feuille:
            ev = feuille.get("espaces_verts_pct")
            disp = f"{ev}% ev × {feuille.get('pleine_terre_part')}"
            regs = pct(float(ev)) if ev is not None else []
            multi = True
    elif r in ("retraits.voie", "retraits.limites_separatives"):
        if feuille.get("min_m") is not None:
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
        regs = pct(float(q)) if q is not None else []

    sans_val = (not regs) and disp is None
    return [re.compile(p) for p in regs], disp, multi, sans_val


def _art_core(article: str):
    a = re.sub(r"^articles?\s+", "", norm(article))
    m = re.match(r"([a-z0-9]+)\D+(\d+)", a)
    if m:
        return re.compile(re.escape(m.group(1)) + r"\s*" + re.escape(m.group(2)))
    m2 = re.match(r"([a-z0-9]+)", a)
    return re.compile(re.escape(m2.group(1))) if m2 else None


def _cite_hit(cite_n: str, page_texts: list[str]) -> bool:
    if not cite_n or len(cite_n) < 12:
        return False
    frag = cite_n[:90]
    for t in page_texts:
        if t and (frag in t or cite_n in t):
            return True
    toks = [w for w in cite_n.split() if len(w) > 3]
    if len(toks) < 5:
        return False
    for t in page_texts:
        if t and sum(1 for w in toks if w in t) / len(toks) >= 0.85:
            return True
    return False


def _exception_near(page_text: str, reg, cite_n: str) -> bool:
    in_cite = any(m in cite_n for m in EXCEPTION_MOTS)
    if not page_text or reg is None:
        return False
    m = reg.search(page_text)
    if not m:
        return False
    win = page_text[max(0, m.start() - 260):m.end() + 260]
    return any(mot in win for mot in EXCEPTION_MOTS) and not in_cite


def _distinct_same_unit(page_text: str, rubrique_sous: str) -> int:
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


def _pages_norm_factory():
    import fitz  # import paresseux : PyMuPDF n'est requis que pour la vérif
    cache: dict[str, list[str] | None] = {}
    pd = pdf_dir()

    def get(insee: str):
        if insee in cache:
            return cache[insee]
        doc_name = D.etat_commune(insee).get("document")
        p = pd / doc_name if doc_name else None
        if not p or not p.exists():
            cache[insee] = None
            return None
        d = fitz.open(str(p))
        cache[insee] = [norm(d[i].get_text()) for i in range(d.page_count)]
        d.close()
        return cache[insee]
    return get


def verifier() -> tuple[list[dict], dict]:
    """Rejoue la vérification sur toutes les règles calibrées. Retourne (lignes, compteurs).
    Chaque ligne : insee, zone, regle, valeur_labuse, page, article, statut,
    raison_calibration, verdict, note_extrait."""
    get_pages = _pages_norm_factory()
    rows = list(D.iter_regles_calibrees())
    out: list[dict] = []
    counts = {"TROUVE": 0, "AMBIGU": 0, "ABSENT": 0, "ILLISIBLE": 0}

    for r in rows:
        insee, zone, chemin = r["insee"], r["zone"], r["chemin"]
        article = (r.get("article") or "").strip()
        page = r.get("page_pdf")
        cite = r.get("citation") or ""
        cite_n = norm(cite)
        absent_flag = bool(r.get("absent"))
        pages = get_pages(insee)
        regs, disp, multi, sans_val = _value_regexes(chemin, r)

        def emit(v, note):
            out.append({"insee": insee, "zone": zone, "regle": chemin,
                        "valeur_labuse": disp or "", "page": page, "article": article,
                        "statut": r.get("statut") or "",
                        "raison_calibration": (r.get("raison") or "")[:160],
                        "verdict": v, "note_extrait": (note + " | " + (cite[:300]))[:300]})
            counts[v] += 1

        page_texts, primary = [], ""
        if pages and isinstance(page, int) and 1 <= page <= len(pages):
            idx = page - 1
            primary = pages[idx]
            for j in (idx - 1, idx, idx + 1):
                if 0 <= j < len(pages):
                    page_texts.append(pages[j])
        elif pages is None:
            emit("ABSENT", "PDF introuvable")
            continue

        chit = _cite_hit(cite_n, page_texts)
        acore = _art_core(article) if article else None
        ahit = any(acore.search(t) for t in page_texts) if acore else False

        if pages and (not any(page_texts)
                      or (primary == "" and sum(len(t) for t in page_texts) < 40)):
            emit("ILLISIBLE", "page sans texte (OCR requis)")
            continue

        if absent_flag or sans_val:
            if chit:
                emit("TROUVE", "silence/exemption prouvé (citation sur la page)")
            elif ahit:
                emit("AMBIGU", "article présent, citation non retrouvée")
            else:
                emit("ABSENT", "citation d'absence non retrouvée")
            continue

        is_align = chemin.startswith("retraits") and (
            r.get("forme") == "alignement" or r.get("min_m") == 0)
        if is_align:
            mots_al = ("alignement", "en limite", "sur la limite", "sur les limites")
            if chit or any(any(mt in t for mt in mots_al) for t in page_texts):
                emit("TROUVE", "implantation à l'alignement/en limite (recul 0 explicite)")
            elif ahit:
                emit("AMBIGU", "article présent, mention alignement non retrouvée")
            else:
                emit("ABSENT", "mention alignement/limite introuvable")
            continue

        if chemin.startswith("retraits") and not regs and (r.get("formule") or disp == "formule"):
            if chit:
                emit("TROUVE", "règle en formule (prospect) — citation sur la page")
            elif ahit:
                emit("AMBIGU", "formule : article présent, citation non retrouvée")
            else:
                emit("ABSENT", "formule : citation introuvable")
            continue

        if multi:
            emit("AMBIGU", "valeur variable par secteur/composée")
            continue

        val_on = None
        for reg in regs:
            if any(reg.search(t) for t in page_texts):
                val_on = reg
                break
        val_in_cite = any(reg.search(cite_n) for reg in regs)
        exc = (_exception_near(primary or (page_texts[0] if page_texts else ""), val_on, cite_n)
               if val_on else any(m in cite_n for m in EXCEPTION_MOTS))
        ndist = _distinct_same_unit(primary, chemin)

        if val_on is None:
            emit("ABSENT", "valeur introuvable sur page±1")
        elif chit and val_in_cite and not exc:
            emit("TROUVE", "citation+valeur sur la page, article %s" % ("ok" if ahit else "≠?"))
        elif exc:
            emit("AMBIGU", "valeur présente mais exception dans le paragraphe")
        elif ndist > 1 and not (chit and val_in_cite):
            emit("AMBIGU", f"{ndist} valeurs candidates (même unité) sur la page")
        elif val_in_cite and ahit:
            emit("TROUVE", "valeur dans la citation, article sur la page")
        elif not ahit:
            emit("AMBIGU", "valeur sur la page mais article non localisé")
        else:
            emit("AMBIGU", "valeur sur la page, citation non alignée")

    return out, counts


COLS = ["insee", "zone", "regle", "valeur_labuse", "page", "article",
        "statut", "raison_calibration", "verdict", "note_extrait"]


def ecrire_csv(rows: list[dict], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def resume() -> dict:
    """Compteurs pour l'onglet Cohérence : total, par verdict, N communes, N FAUSSES connues."""
    rows, counts = verifier()
    return {"total": len(rows), "verdicts": counts,
            "communes": len({r["insee"] for r in rows})}
