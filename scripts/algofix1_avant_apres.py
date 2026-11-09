"""ALGO-FIX-1 — comparaison AVANT/APRÈS sur TOUTE L'ÎLE (run servi q_v20), LUE de la table de run
`parcel_scenario_v2_runs` (écrite par `algofix1_persist_run.py`).

Par commune et par scénario : répartition des bandes V1 (servies) et des STATUTS V2 (conservation +
reconstruction), plus le TOP 20 des changements de bande avec la raison. Lecture seule.

Usage : LABUSE_REEL_DATABASE_URL=… python scripts/algofix1_avant_apres.py \
            [--out docs/audit-2026-11/algo-fix-1/AVANT-APRES.md]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import Session                   # noqa: E402

RUN = "q_v20"
STATUTS = ["ESTIMATED", "PRESTUDY", "TO_VERIFY", "DEFERRED", "NO_MARGIN", "OUTSIDE_OBJECTIVE"]
BANDES = ["A", "B", "C", "D", "0", "NC", "HC"]


def _session() -> Session:
    url = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")
    return Session(bind=create_engine(url))


def _dist(session, scenario, col, commune=None):
    w = "AND commune=:c" if commune else ""
    p = {"r": RUN, "s": scenario}
    if commune:
        p["c"] = commune
    rows = session.execute(text(
        f"SELECT {col}, count(*) FROM parcel_scenario_v2_runs "
        f"WHERE run_label=:r AND scenario=:s {w} AND {col} IS NOT NULL GROUP BY {col}"), p)
    return {r[0]: r[1] for r in rows}


def _table(counter, order, total=None):
    total = total or (sum(counter.values()) or 1)
    lines = ["| clé | n | part |", "|---|---:|---:|"]
    for k in order + sorted(set(counter) - set(order)):
        if k in counter:
            lines.append(f"| {k} | {counter[k]} | {100*counter[k]/total:.1f} % |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/audit-2026-11/algo-fix-1/AVANT-APRES.md")
    args = ap.parse_args()
    out = ["# ALGO-FIX-1 — AVANT / APRÈS sur toute l'île (run servi q_v20)",
           "",
           "Lu de la table de run `parcel_scenario_v2_runs` (écrite par le calcul du run, pas par",
           "l'endpoint). V1 = bande servie `score_labuse`. V2 = statut + bande du scénario.",
           "Reconstruction : statut dérivé sur toute l'île ; bandes & quantités chiffrées (enrich)",
           "sur Entre-Deux + Saint-Denis (échantillon).", ""]
    with _session() as s:
        # ── Île entière ───────────────────────────────────────────────────────
        n_keep = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r "
                                "AND scenario='keep'"), {"r": RUN}).scalar()
        out.append(f"## Île entière — {n_keep} parcelles")
        out.append("")
        out.append("### Bandes V1 (servies)")
        out.append(_table(_dist(s, "keep", "bande_v1"), BANDES, n_keep))
        out.append("\n### Statuts V2 — conservation")
        out.append(_table(_dist(s, "keep", "status"), STATUTS, n_keep))
        out.append("\n### Statuts V2 — reconstruction")
        out.append(_table(_dist(s, "rebuild", "status"), STATUTS, n_keep))
        out.append("\n### Bandes V2 — conservation (parcelles « Capacité estimée »)")
        out.append(_table(_dist(s, "keep", "band"), ["A", "B", "C", "D"]))
        out.append("")

        # ── Croisement bande V1 → statut V2 conservation (île) ────────────────
        out.append("### Croisement bande V1 → statut V2 (conservation, île)")
        cx = s.execute(text(
            "SELECT bande_v1, status, count(*) FROM parcel_scenario_v2_runs "
            "WHERE run_label=:r AND scenario='keep' AND bande_v1 IS NOT NULL GROUP BY 1,2"), {"r": RUN})
        grid = {}
        for v1, st, n in cx:
            grid.setdefault(v1, {})[st] = n
        out.append("| V1 ↓ / V2 → | " + " | ".join(STATUTS) + " |")
        out.append("|" + "---|" * (len(STATUTS) + 1))
        for v1 in BANDES:
            if v1 in grid:
                out.append("| " + v1 + " | " + " | ".join(str(grid[v1].get(st, 0)) for st in STATUTS) + " |")
        out.append("")

        # ── TOP 20 des changements de bande (V1 → V2 conservation), avec la raison ──
        out.append("### Top 20 des changements de bande (conservation), avec la raison")
        out.append("Changement = la V1 sert une bande constructible (A/B/C/D) que la V2 refuse")
        out.append("(À vérifier / Hors projet / Aucun ajout), ou la V1 sert « 0/HC » que la V2 nomme")
        out.append("« Capacité estimée ». Classé par écart de rang de bande.")
        out.append("")
        chg = s.execute(text("""
            WITH r AS (
              SELECT idu, commune, bande_v1, status, band, cause,
                CASE bande_v1 WHEN 'A' THEN 0 WHEN 'B' THEN 1 WHEN 'C' THEN 2 WHEN 'D' THEN 3
                     WHEN '0' THEN 4 WHEN 'NC' THEN 5 WHEN 'HC' THEN 6 ELSE 9 END AS v1r,
                CASE band WHEN 'A' THEN 0 WHEN 'B' THEN 1 WHEN 'C' THEN 2 WHEN 'D' THEN 3 ELSE 8 END AS v2r
              FROM parcel_scenario_v2_runs
              WHERE run_label=:r AND scenario='keep' AND bande_v1 IS NOT NULL)
            SELECT idu, commune, bande_v1, status, band, cause, abs(v1r - v2r) AS ecart
            FROM r
            WHERE (bande_v1 IN ('A','B','C','D') AND status <> 'ESTIMATED')
               OR (bande_v1 IN ('0','HC') AND status IN ('ESTIMATED','DEFERRED'))
            ORDER BY ecart DESC, idu
            LIMIT 20"""), {"r": RUN})
        out.append("| IDU | commune | V1 | V2 statut | V2 bande | raison (cause V2) |")
        out.append("|---|---|---|---|---|---|")
        for idu, commune, v1, st, band, cause, _e in chg:
            c = ";".join(cause) if isinstance(cause, list) else (cause or "")
            out.append(f"| {idu} | {commune} | {v1} | {st} | {band or '—'} | {c} |")
        out.append("")

        # ── Par commune (statuts V2 conservation + reconstruction) ────────────
        out.append("## Par commune")
        out.append("")
        communes = [r[0] for r in s.execute(text(
            "SELECT DISTINCT commune FROM parcel_scenario_v2_runs WHERE run_label=:r "
            "AND commune IS NOT NULL ORDER BY commune"), {"r": RUN})]
        out.append("| commune | n | V2 keep: EST / NO_MARGIN / TO_VERIFY / DEFERRED / OUTSIDE | "
                   "V2 rebuild: EST / autres |")
        out.append("|---|---:|---|---|")
        for c in communes:
            k = _dist(s, "keep", "status", c)
            rb = _dist(s, "rebuild", "status", c)
            nk = sum(k.values())
            keepstr = " / ".join(str(k.get(x, 0)) for x in
                                 ["ESTIMATED", "NO_MARGIN", "TO_VERIFY", "DEFERRED", "OUTSIDE_OBJECTIVE"])
            rebstr = f"{rb.get('ESTIMATED',0)} / {nk - rb.get('ESTIMATED',0)}"
            out.append(f"| {c} | {nk} | {keepstr} | {rebstr} |")
        out.append("")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"→ écrit {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
