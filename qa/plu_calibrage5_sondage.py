"""PLU-CALIBRAGE-5 — SONDAGE : 10 règles tirées au hasard parmi les valide de ce mandat.

Reproductible (`random.seed(5)`). Pour chaque règle : la valeur gravée, sa source, la PREUVE
verbatim retenue (sous-chaîne exacte du règlement) et la page PDF où cette preuve se trouve
réellement (les zones 1AU renvoient à leur zone U : la preuve est sur la page de l'article U).
Écrit captures/plu-calibrage5/SONDAGE-10.md — le fichier que Vic lit.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage5_sondage.py
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pypdf

from labuse.plu import destinations as D

_CAP = Path("captures/plu-calibrage5")
_VK = ("m", "pct", "min_m", "places", "r_plus", "formule")


def _leaf(ins, zone, chemin):
    reg = D.regles_zone(ins, zone)
    p = chemin.split(".")
    return reg.get(p[0]) if len(p) == 1 else (reg.get(p[0]) or {}).get(p[1])


def main() -> int:
    # les feuilles tranchées par ce mandat (lots 2/3/4), désormais valide
    dmap = {}
    for sub in ("b_decisions", "a_decisions", "c_decisions"):
        for f in sorted((_CAP / sub).glob("974??.json")):
            ins = f.name[:5]
            for d in json.loads(f.read_text(encoding="utf-8"))["decisions"]:
                if d["geste"] in ("valider", "corriger", "absent"):
                    dmap[(ins, d["zone"], d["chemin"])] = d
    valide = [k for k in dmap if (_leaf(*k) or {}).get("statut") == "valide"]
    random.seed(5)
    sample = random.sample(valide, 10)

    name = {p.name[:5]: (D._load_yaml(str(p)) or {}).get("meta", {}).get("commune")
            for p in Path("config/plu_destinations").glob("974??_*.yaml")}
    pdfp = {p.name[:5]: p for p in Path("data/plu_reglements").glob("*.pdf")}
    readers: dict = {}

    def find_page(ins, preuve):
        if ins not in readers:
            readers[ins] = pypdf.PdfReader(str(pdfp[ins]))
        loose = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
        key = loose(preuve)[:40]
        for i, pg in enumerate(readers[ins].pages, 1):
            if key and key in loose(pg.extract_text() or ""):
                return i, re.sub(r"\n{2,}", "\n", (pg.extract_text() or "")).strip()
        return None, ""

    L = ["# PLU-CALIBRAGE-5 — SONDAGE : 10 règles validées par ce mandat (tirage aléatoire, seed=5)\n",
         "Pour chaque règle : la valeur gravée, sa source, la PREUVE verbatim retenue (sous-chaîne "
         "exacte du règlement, vérifiée littéralement présente), et la page PDF où cette preuve se "
         "trouve réellement (les zones 1AU renvoient à leur zone U). Reproductible : `random.seed(5)`.\n"]
    for i, (ins, zone, chemin) in enumerate(sample, 1):
        leaf, dec = _leaf(ins, zone, chemin), dmap[(ins, zone, chemin)]
        val = ("absent — non réglementé (silence prouvé)" if leaf.get("absent")
               else " · ".join(f"{k}={leaf[k]}" for k in _VK if leaf.get(k) is not None))
        preuve = dec.get("preuve") or leaf.get("citation") or ""
        pg, txt = find_page(ins, preuve)
        m = re.search(re.escape(preuve[:20]), txt) if (txt and preuve) else None
        win = (txt[max(0, m.start() - 90):m.start() + len(preuve) + 90] if m
               else (txt[:300] if txt else "(preuve non relocalisée — voir citation)"))
        L += [f"## {i}. {name.get(ins)} — zone {zone} — {chemin}  [{dec['geste']}]\n",
              f"- **Valeur gravée** : {val}",
              f"- **Source** : Art. {leaf.get('article')} · p.{leaf.get('page_pdf')} (réf.) · "
              f"preuve trouvée p.{pg} du PDF",
              f"- **Preuve verbatim** : « {preuve[:260]} »",
              f"- **Extrait de la page {pg}** :\n\n  > " + win.replace("\n", "\n  > ") + "\n"]
    (_CAP / "SONDAGE-10.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"SONDAGE-10.md — {len(sample)} règles (seed=5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
