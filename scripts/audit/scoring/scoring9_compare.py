"""SCORING-9 — répartition des bandes île AVANT (q_v15, servi 25/09, résiduel run 10) vs APRÈS
(q_v16, résiduel run 13) + 20 plus grosses MONTÉES / DESCENTES de score, avec cause.

Source AUTORITAIRE : les deux runs STOCKÉS dans `score_labuse` (run_label q_v15 et q_v16), joints
par parcel_id. C'est le before/after réel, tel que servi/servable. La cause du mouvement est
tirée de la transition du RÉSIDUEL entre run_seq 10 et 13 (`parcel_residuel_runs`), moteur
dominant mesuré par EXPLIQUE-RUN13 (recalcul du bâti existant, niveaux LiDAR égout + coef 0,95).

Contrôle croisé : la répartition q_v15 doit être proche de reports/scoring-7/bandes_ile.csv
(même run ; tout écart = re-persistance ultérieure du run q_v15, signalé).

Sorties : reports/scoring-9/bandes_ile.csv, montees_descentes.csv + stdout.

Usage : DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=<worktree>/src \
        python scripts/audit/scoring/scoring9_compare.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "reports" / "scoring-9"
S7_BANDES = ROOT / "reports" / "scoring-7" / "bandes_ile.csv"
BANDES = ("A", "B", "C", "D", "0", "NC")
RUN_AV, RUN_AP = 10, 13


def _fam(cause: str | None) -> str:
    return "calculee" if not cause else cause.split(":", 1)[0]


def _cause_mouvement(sdp10, sdp13, cause10, cause13) -> str:
    f10, f13 = _fam(cause10), _fam(cause13)
    d = (sdp13 or 0) - (sdp10 or 0)
    if f13 == "terrain_exigu" and f10 != "terrain_exigu":
        return "assiette recalculée → terrain exigu (enveloppe PPR/SUP déduite)"
    if f13.startswith("regle_plu_non_validee") and not f10.startswith("regle_plu_non_validee"):
        return "règle PLU retirée (PLU-VERIF-1) → non calculable"
    if f10 == "terrain_exigu" and f13 == "calculee":
        return "ré-ouverture : assiette recalculée, SDP de nouveau calculée"
    if f10 != "calculee" and f13 == "calculee":
        return f"cause levée ({f10} → calculée)"
    if f10 == "calculee" and f13 != "calculee":
        return f"cause posée (calculée → {f13})"
    if f10 == "calculee" and f13 == "calculee":
        if d > 0:
            return "bâti existant recalculé (niveaux LiDAR égout + coef 0,95) → SDP résiduelle ↑"
        if d < 0:
            return "assiette/bâti recalculé → SDP résiduelle ↓"
    if d:
        return f"SDP {int(sdp10 or 0)}→{int(sdp13 or 0)} m² ({f10}→{f13})"
    return f"{f10}→{f13} (coef faisabilité / autre cache)"


def main() -> None:
    os.environ.setdefault(
        "LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
    from sqlalchemy import text

    from labuse.db import engine
    OUT.mkdir(parents=True, exist_ok=True)

    with engine().begin() as c:
        # ── répartition par bande (autoritaire) ──────────────────────────────
        dist = {"q_v15": {}, "q_v16": {}}
        for run in ("q_v15", "q_v16"):
            for b, n in c.execute(text(
                    "SELECT bande, count(*) FROM score_labuse WHERE run_label=:r GROUP BY bande"),
                    {"r": run}):
                dist[run][b] = n

        # ── mouvements de score (both scores non-null) + cause résiduel ──────
        rows = c.execute(text("""
            SELECT v.idu, v.commune,
                   v.score AS s15, v.bande AS b15,
                   w.score AS s16, w.bande AS b16, w.contributions AS contr16,
                   a.sdp_residuelle_m2 AS sdp10, a.cause AS cause10,
                   b.sdp_residuelle_m2 AS sdp13, b.cause AS cause13
            FROM score_labuse v
            JOIN score_labuse w ON w.parcel_id = v.parcel_id AND w.run_label='q_v16'
            JOIN parcels p ON p.id = v.parcel_id
            LEFT JOIN parcel_residuel_runs a ON a.parcel_id = p.id AND a.run_seq=:s10
            LEFT JOIN parcel_residuel_runs b ON b.parcel_id = p.id AND b.run_seq=:s13
            WHERE v.run_label='q_v15'
              AND v.score IS NOT NULL AND w.score IS NOT NULL AND v.score <> w.score
        """), {"s10": RUN_AV, "s13": RUN_AP}).all()

        # transitions NC (non rankables numériquement) — comptées à part
        nc_trans = c.execute(text("""
            SELECT (v.bande='NC') AS nc15, (w.bande='NC') AS nc16, count(*)
            FROM score_labuse v JOIN score_labuse w
              ON w.parcel_id=v.parcel_id AND w.run_label='q_v16'
            WHERE v.run_label='q_v15' AND (v.bande='NC' OR w.bande='NC')
            GROUP BY 1,2 ORDER BY 1,2
        """)).all()

    n_tot = sum(dist["q_v16"].values())
    print(f"=== RÉPARTITION ÎLE DES BANDES — AVANT q_v15 (25/09, run10) → APRÈS q_v16 (run13) ===")
    print(f"  {'bande':<5}{'avant':>9}{'après':>9}{'Δ':>9}{'%après':>9}")
    with (OUT / "bandes_ile.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bande", "avant_qv15", "apres_qv16", "delta", "pct_apres"])
        for b in BANDES:
            a, p = dist["q_v15"].get(b, 0), dist["q_v16"].get(b, 0)
            pct = round(100 * p / n_tot, 2) if n_tot else 0
            w.writerow([b, a, p, p - a, pct])
            print(f"  {b:<5}{a:>9}{p:>9}{p-a:>+9}{pct:>8.2f}%")
    print(f"  total avant={sum(dist['q_v15'].values())} après={sum(dist['q_v16'].values())}")

    if S7_BANDES.exists():
        hist = {r["bande"]: int(r["n"]) for r in csv.DictReader(S7_BANDES.open())}
        print("\n  [contrôle] q_v15 (DB) vs reports/scoring-7/bandes_ile.csv :")
        for b in BANDES:
            diff = dist["q_v15"].get(b, 0) - hist.get(b, 0)
            print(f"    {b:<3} DB={dist['q_v15'].get(b,0):>8}  scoring7={hist.get(b,0):>8}  "
                  f"{'✓' if diff == 0 else f'Δ {diff:+}'}")

    # mouvements
    mv = []
    for r in rows:
        d = r.s16 - r.s15
        contr = ""
        try:
            cs = r.contr16 if isinstance(r.contr16, list) else json.loads(r.contr16 or "[]")
            contr = " · ".join(x.get("libelle", "") for x in cs[:2])
        except Exception:
            pass
        mv.append((d, r.idu, r.commune, r.s15, r.s16, r.b15, r.b16,
                   _cause_mouvement(r.sdp10, r.sdp13, r.cause10, r.cause13), contr))
    mv.sort(key=lambda x: x[0])
    descentes, montees = mv[:20], mv[-20:][::-1]
    with (OUT / "montees_descentes.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sens", "idu", "commune", "score_qv15", "score_qv16", "delta",
                    "bande_qv15", "bande_qv16", "cause", "contributions_qv16"])
        for tag, grp in (("montée", montees), ("descente", descentes)):
            for d, idu, com, s15, s16, b15, b16, cause, contr in grp:
                w.writerow([tag, idu, com, s15, s16, d, b15, b16, cause, contr])

    print("\n=== 20 PLUS GROSSES MONTÉES (score q_v15 → q_v16) ===")
    for d, idu, com, s15, s16, b15, b16, cause, _ in montees:
        print(f"  {idu} {com[:14]:<14} {s15:>3}→{s16:>3} ({d:+4}) {b15}→{b16}  {cause}")
    print("\n=== 20 PLUS GROSSES DESCENTES ===")
    for d, idu, com, s15, s16, b15, b16, cause, _ in descentes:
        print(f"  {idu} {com[:14]:<14} {s15:>3}→{s16:>3} ({d:+4}) {b15}→{b16}  {cause}")

    print(f"\n{len(mv)} parcelles ont changé de score (score non-NC des deux côtés).")
    print("Transitions NC (score non numérique) :")
    for nc15, nc16, n in nc_trans:
        sens = ("NC→NC" if nc15 and nc16 else "→NC (nouvelle)" if nc16 else "NC→ calculée")
        print(f"    {sens:<16} {n}")
    print(f"\nécrit dans {OUT}/")


if __name__ == "__main__":
    main()
