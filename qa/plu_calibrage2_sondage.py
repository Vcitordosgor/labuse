"""PLU-CALIBRAGE-2 lot 0 — LE SONDAGE. Tire 10 règles au hasard parmi les 63 validées de
Saint-Denis (toutes zones/rubriques), et pour chacune sort — dans UN fichier lisible que Vic
lit à la place du PDF — la zone, la rubrique, la valeur retenue, la citation, et l'extrait de la
page du PDF autour de la citation (5 lignes avant, 5 après).

Contrôle : si une citation ne se retrouve pas sur sa page (la règle « ne tient pas »), on le dit
et on S'ARRÊTE (le mandat ne continue pas sur un calibrage douteux). Graine fixe → tirage
reproductible.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage2_sondage.py
"""
from __future__ import annotations

import random
import re
import sys
import unicodedata
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.plu import destinations as D  # noqa: E402

INSEE = "97411"
GRAINE = 20260920           # tirage reproductible
N = 10
SORTIE = Path(__file__).resolve().parents[1] / "captures" / "plu-calibrage2" / "sondage_10_regles.txt"

_VAL_KEYS = ("m", "r_plus", "pct", "m2", "formule", "min_m", "places", "par_m2", "detail",
             "seuil_logements", "seuil_m2", "quota_pct", "portee")


def _valeur(leaf: dict) -> str:
    if leaf.get("absent"):
        return "non réglementé (silence prouvé)"
    return " · ".join(f"{k} = {leaf[k]}" for k in _VAL_KEYS
                      if k in leaf and leaf.get(k) is not None) or "(aucune valeur)"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _extrait_autour(page_texte: str, citation: str, avant: int = 5, apres: int = 5):
    """Localise la citation dans le texte de la page (par recouvrement de mots) et rend
    (lignes autour, taux de recouvrement, index de la ligne trouvée)."""
    lignes = page_texte.splitlines()
    mots = [m for m in _norm(citation).split() if len(m) > 3]
    if not mots:
        return lignes[:avant + apres + 1], 0.0, 0
    best_i, best_score = 0, 0.0
    # fenêtre glissante de 3 lignes (une citation peut chevaucher des retours à la ligne)
    for i in range(len(lignes)):
        fen = _norm(" ".join(lignes[i:i + 3]))
        score = sum(1 for w in mots if w in fen) / len(mots)
        if score > best_score:
            best_score, best_i = score, i
    d, f = max(0, best_i - avant), min(len(lignes), best_i + 1 + apres)
    return lignes[d:f], best_score, best_i


# PLU-CALIBRAGE-2 — CONTRÔLE D'ATTRIBUTION (permanent, vaut pour les 22 autres communes) :
# une citation ne suffit pas — elle doit relever de LA zone revendiquée, pas d'un secteur voisin.
# Robuste au texte quasi identique entre secteurs frères : on cherche si la citation apparaît,
# QUELQUE PART sur la page, sous un marqueur (« En secteur <X> [, <Y>] » ou « Article <X>.n »)
# COMPATIBLE avec la zone — OK si un tel emplacement existe ; misattribution si la citation
# n'apparaît QUE sous d'autres secteurs (le vrai bug : une base portant une valeur de secteur).
# Un code de ZONE réel commence par U/AU ; on ignore « article R.421 » et la prose.
_MARQUEUR = re.compile(r"(?:En\s+secteur|secteur|Article)\s+((?:U[a-z]{1,6}|AU[a-z0-9]*)(?:\s*,\s*U[a-z]{1,6})*)")
_ZONETOK = re.compile(r"U[a-z]{1,6}|AU[a-z0-9]*")


def _compatible(marqueurs: list[str], zone: str) -> bool:
    """Un marqueur (ou l'un des codes d'un marqueur joint « Udop, Udp ») convient à la zone si
    c'est la même zone, OU si la zone est un SECTEUR sous l'article de sa base (« Upr » sous
    « Up »)."""
    from labuse.faisabilite.zone_norm import normalize_key
    zz = normalize_key(zone)
    for mk in marqueurs:
        for tok in _ZONETOK.findall(mk):
            mz = normalize_key(tok)
            if mz == zz or zz.startswith(mz):
                return True
    return False


def _attribution(page_txt: str, citation: str, zone: str, best_i: int):
    """(marqueur, verdict) — verdict ∈ {ok, misattribue, general}. On repère TOUTES les fenêtres
    où la citation apparaît (recouvrement ≥ 0,7) ; pour chacune, le marqueur de portée le plus
    proche au-dessus. OK si l'une est compatible avec la zone ; misattribue si des fenêtres
    existent mais AUCUNE compatible ; general si aucun marqueur (dispositions générales)."""
    lignes = page_txt.splitlines()
    mots = [w for w in _norm(citation).split() if len(w) > 3]
    if not mots:
        return None, "general"
    fenetres = [i for i in range(len(lignes))
                if sum(1 for w in mots if w in _norm(" ".join(lignes[i:i + 3]))) / len(mots) >= 0.7]
    if not fenetres:
        fenetres = [best_i]
    vu_marqueur = False
    for i in fenetres:
        proches: list[str] = []
        for j in range(min(i, len(lignes) - 1), max(-1, i - 45), -1):
            m = _MARQUEUR.search(lignes[j])
            if m:
                proches.append(m.group(1))
                break
        if proches:
            vu_marqueur = True
            if _compatible(proches, zone):
                return proches[0], "ok"
    return (None, "misattribue") if vu_marqueur else (None, "general")


def main() -> int:
    path = D._fichier_commune(INSEE)
    doc = D._load_yaml(str(path))
    meta = doc.get("meta", {})
    pdf_path = Path(__file__).resolve().parents[1] / "data" / "plu_reglements" / meta["document"]
    if not pdf_path.is_file():
        from labuse.plu.extraction import telecharger_reglement
        pdf_path = telecharger_reglement(meta)
    pdf = fitz.open(str(pdf_path))

    valides = [r for r in D.regles_commune(INSEE) if r.get("statut") == "valide"]
    if len(valides) < N:
        print(f"seulement {len(valides)} règles validées (< {N}) — rien à sonder", file=sys.stderr)
        return 2
    rnd = random.Random(GRAINE)
    tirage = rnd.sample(valides, N)

    lignes_out: list[str] = []
    W = lignes_out.append
    W("=" * 92)
    W(f"PLU-CALIBRAGE-2 — SONDAGE : {N} règles tirées au hasard parmi {len(valides)} validées")
    W(f"Commune : {meta.get('commune')} ({INSEE}) · règlement {meta.get('document')} "
      f"· millésime {meta.get('millesime')} · md5 {meta.get('md5')}")
    W(f"Tirage reproductible (graine {GRAINE}). Vic lit CE fichier, pas le PDF.")
    W("=" * 92)

    douteuses: list[str] = []
    misattribuees: list[str] = []
    for n, r in enumerate(tirage, 1):
        page_no = r.get("page_pdf")
        page_txt = pdf.load_page(page_no - 1).get_text() if isinstance(page_no, int) and 1 <= page_no <= pdf.page_count else ""
        extrait, score, best_i = _extrait_autour(page_txt, r.get("citation", ""))
        tient = score >= 0.5
        # une feuille PLAGE est un résumé de BASE des variations par secteur : elle cite
        # légitimement plusieurs secteurs → jamais jugée « misattribuée ».
        if r.get("plage"):
            marq, att = "plage (base)", "plage"
        else:
            marq, att = _attribution(page_txt, r.get("citation", ""), r["zone"], best_i)
        if not tient:
            douteuses.append(f"#{n} {r['zone']}/{r['chemin']} (p.{page_no}, recouvrement {score:.0%})")
        if att == "misattribue":
            misattribuees.append(f"#{n} {r['zone']}/{r['chemin']} : citation sous « secteur {marq} » (p.{page_no})")
        att_lbl = {"ok": f"attribuée à {marq}", "misattribue": f"⚠ ATTRIBUÉE À {marq} (≠ {r['zone']})",
                   "general": "dispositions générales / tête d'article",
                   "plage": "plage de base (variations par secteur)"}[att]
        W("")
        W(f"── {n}/{N} ── zone {r['zone']} · rubrique {r['rubrique']}"
          + (f" · feuille {r['feuille']}" if r.get("feuille") else "")
          + f"   [{'OK' if (tient and att != 'misattribue') else 'DOUTEUSE'} · recouvrement {score:.0%} · {att_lbl}]")
        W(f"   valeur retenue : {_valeur(r)}")
        W(f"   article        : {r.get('article')}   ·   page PDF : {page_no}")
        W(f"   citation       : {r.get('citation')}")
        W(f"   — extrait du PDF autour de la citation (p.{page_no}, 5 lignes avant / 5 après) —")
        for l in extrait:
            W(f"     | {l.rstrip()}")

    W("")
    W("=" * 92)
    if douteuses or misattribuees:
        W(f"VERDICT : {len(douteuses)} citation(s) introuvable(s) · {len(misattribuees)} "
          f"misattribution(s) de zone — le mandat S'ARRÊTE.")
        for d in douteuses:
            W(f"   ⚠ citation : {d}")
        for m in misattribuees:
            W(f"   ⚠ attribution : {m}")
    else:
        W(f"VERDICT : les {N} règles tiennent — citation retrouvée ET attribuée à la bonne zone "
          "(ou aux dispositions générales). Calibrage sûr.")
    W("=" * 92)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(lignes_out) + "\n", encoding="utf-8")
    print("\n".join(lignes_out))
    print(f"\n→ écrit : {SORTIE}")
    return 1 if (douteuses or misattribuees) else 0


if __name__ == "__main__":
    raise SystemExit(main())
