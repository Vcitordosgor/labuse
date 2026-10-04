"""SCORING-8 lot C — re-caler et graver les bandes APRÈS q_v16 servi.

À LANCER quand Vic a fait : (1) run_cascade_2026_10.py, (2) run_qv16.py, (3) residuel-serve de
q_v16 (la vue `parcel_residuel` reflète alors le résiduel de q_v16). Tant que q_v16 n'est pas
servi, ce harnais tourne sur le résiduel SERVI COURANT et sert de BASELINE (reproduit SCORING-7)
+ de contrôle des invariants — il NE GRAVE RIEN (la gravure du yaml est un geste manuel séparé,
conditionné à « tout tient » sur q_v16).

Modes :
  temoins  : rescored les 30 témoins sur la table servie, tableau avant (SCORING-7)/après,
             contrôle des invariants (bonnes ≥ 80 sauf AB0798, mauvaises ≤ 25, pas d'inversion,
             aucune NC à 0).
  ile      : répartition île des bandes + 20 plus grosses montées/descentes vs la baseline
             SCORING-7 (reports/scoring-7/bandes_ile.csv). Rescoring île (~15 min).

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src \
        ~/Desktop/labuse/.venv/bin/python scripts/audit/scoring/scoring8_lotC.py temoins
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

TEMOINS = ROOT / "reports" / "scoring-5" / "TEMOINS.csv"
S7_TEMOINS = ROOT / "reports" / "scoring-7" / "temoins_q_v15.json"
S7_BANDES = ROOT / "reports" / "scoring-7" / "bandes_ile.csv"
# étage 0 d'où l'accès est lu : cascade_2026_10 une fois q_v16 servi, sinon la cascade courante.
CASCADE = os.environ.get("S8_CASCADE", "q_v13_sources1")
AB0798 = "97411000AB0798"   # cas d'école : « bonne » mais 64 (lame bâtie) — exempté du seuil 80


def _temoins_cat() -> dict[str, str]:
    return {r["idu"]: r["categorie"] for r in csv.DictReader(TEMOINS.open())}


def mode_temoins(s) -> int:
    from sqlalchemy import text

    from labuse.scoring.score_labuse import score_batch
    cat = _temoins_cat()
    avant = {d["idu"]: d for d in json.loads(S7_TEMOINS.read_text())}
    idus = list(cat)
    ids = {r[1]: r[0] for r in s.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:i)"), {"i": idus})}
    scores = {sc.idu: sc for sc in score_batch(
        s, [ids[i] for i in idus if i in ids], "scoring8_lotC", cascade_label=CASCADE)}

    print(f"{'IDU':<16} {'cat':<9} {'avant':>6} {'→':<2} {'après':>6}  bande  note")
    anomalies: list[str] = []
    scores_par_cat: dict[str, list[int]] = {"bonne": [], "mauvaise": [], "limite": []}
    for idu in idus:
        sc = scores.get(idu)
        if sc is None:
            print(f"{idu:<16} {cat[idu]:<9}  (absente de la table servie)")
            continue
        av = avant.get(idu, {})
        av_s = av.get("score")
        note = ""
        c = cat[idu]
        if sc.non_calculable:
            # aucune NC à 0 : une NC doit porter score None, jamais 0.
            if sc.score == 0:
                anomalies.append(f"{idu} : NC à 0 (interdit)")
                note = "⛔ NC à 0"
        else:
            if c in scores_par_cat:
                scores_par_cat[c].append(sc.score)
            if c == "bonne" and idu != AB0798 and sc.score < 80:
                anomalies.append(f"{idu} : bonne mais {sc.score} < 80")
                note = "⚠ bonne <80"
            if c == "mauvaise" and sc.score > 25:
                anomalies.append(f"{idu} : mauvaise mais {sc.score} > 25")
                note = "⚠ mauvaise >25"
        chg = "" if av_s == sc.score else "  ←CHG"
        print(f"{idu:<16} {c:<9} {str(av_s):>6} {'→':<2} {str(sc.score):>6}  "
              f"{sc.bande:<5} {note}{chg}")

    # inversion bonne < mauvaise (pire bonne vs meilleure mauvaise, hors cas d'école/NC)
    bonnes = [v for v in scores_par_cat["bonne"]]
    mauvaises = [v for v in scores_par_cat["mauvaise"]]
    if bonnes and mauvaises and min(bonnes) < max(mauvaises):
        anomalies.append(f"inversion : pire bonne {min(bonnes)} < meilleure mauvaise {max(mauvaises)}")

    print("\n=== INVARIANTS ===")
    if anomalies:
        for a in anomalies:
            print(f"  ⛔ {a}")
        print("→ NE RIEN GRAVER. Expliquer la cause et proposer le seuil (mandat C.3).")
    else:
        print("  ✓ bonnes ≥ 80 (sauf AB0798), mauvaises ≤ 25, pas d'inversion, aucune NC à 0.")
        print("  → si q_v16 est bien le run servi : gravure du yaml autorisée (geste manuel).")
    return 1 if anomalies else 0


def mode_ile(s) -> int:
    from sqlalchemy import text

    from labuse.scoring.score_labuse import score_batch
    t0 = time.time()
    ids = [r[0] for r in s.execute(text("SELECT id FROM parcels ORDER BY id"))]
    apres = Counter()
    scores_now: dict[int, int | None] = {}
    for k in range(0, len(ids), 5000):
        for sc in score_batch(s, ids[k:k + 5000], "scoring8_lotC", cascade_label=CASCADE):
            apres[sc.bande] += 1
            scores_now[sc.parcel_id] = sc.score
        if k % 50000 == 0:
            print(f"  … {k}/{len(ids)} ({time.time()-t0:.0f}s)", flush=True)
    n = sum(apres.values())
    avant = {r["bande"]: int(r["n"]) for r in csv.DictReader(S7_BANDES.open())}
    print("\n=== RÉPARTITION ÎLE DES BANDES (avant SCORING-7 → après) ===")
    for b in ("A", "B", "C", "D", "0", "NC"):
        av = avant.get(b, 0)
        ap = apres.get(b, 0)
        print(f"  {b:<3} {av:>8} → {ap:>8}  ({100*ap/n:.2f}%)  Δ {ap-av:+}")
    print(f"  total {n}")
    print("\n(20 plus grosses montées/descentes : nécessite le score PARCELLE avant — "
          "lire reports/scoring-7 ou le run score_labuse q_v15 — à brancher après q_v16.)")
    return 0


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from labuse.db import session_scope
    mode = sys.argv[1] if len(sys.argv) > 1 else "temoins"
    print(f"[lotC] mode={mode} cascade={CASCADE} "
          f"(⚠ q_v16 servi ? sinon = baseline sur le résiduel servi courant)\n")
    with session_scope() as s:
        rc = mode_temoins(s) if mode == "temoins" else mode_ile(s)
    sys.exit(rc)


if __name__ == "__main__":
    main()
