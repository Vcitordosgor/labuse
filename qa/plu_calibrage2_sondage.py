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
    for n, r in enumerate(tirage, 1):
        page_no = r.get("page_pdf")
        page_txt = pdf.load_page(page_no - 1).get_text() if isinstance(page_no, int) and 1 <= page_no <= pdf.page_count else ""
        extrait, score, _ = _extrait_autour(page_txt, r.get("citation", ""))
        tient = score >= 0.5
        if not tient:
            douteuses.append(f"#{n} {r['zone']}/{r['chemin']} (p.{page_no}, recouvrement {score:.0%})")
        W("")
        W(f"── {n}/{N} ── zone {r['zone']} · rubrique {r['rubrique']}"
          + (f" · feuille {r['feuille']}" if r.get("feuille") else "")
          + f"   [{'OK' if tient else 'DOUTEUSE'} · recouvrement {score:.0%}]")
        W(f"   valeur retenue : {_valeur(r)}")
        W(f"   article        : {r.get('article')}   ·   page PDF : {page_no}")
        W(f"   citation       : {r.get('citation')}")
        W(f"   — extrait du PDF autour de la citation (p.{page_no}, 5 lignes avant / 5 après) —")
        for l in extrait:
            W(f"     | {l.rstrip()}")

    W("")
    W("=" * 92)
    if douteuses:
        W(f"VERDICT : {len(douteuses)} règle(s) DOUTEUSE(S) — le mandat S'ARRÊTE.")
        for d in douteuses:
            W(f"   ⚠ {d}")
    else:
        W(f"VERDICT : les {N} règles tiennent (citation retrouvée sur sa page). Calibrage sûr.")
    W("=" * 92)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(lignes_out) + "\n", encoding="utf-8")
    print("\n".join(lignes_out))
    print(f"\n→ écrit : {SORTIE}")
    return 1 if douteuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
