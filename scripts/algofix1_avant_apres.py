"""ALGO-FIX-1 — BILAN UNIQUE avant/après, régénéré depuis UN MÊME INSTANTANÉ (run servi q_v20).

Lu de la table de run `parcel_scenario_v2_runs` (écrite par `algofix1_persist_run.py`) pour les
statuts/bandes V2, et des CACHES de score (`_ENTREES_SQL`) pour la DÉCOMPOSITION à entrées
constantes. Sections (avis Astra §1/§5.E/§7) :

  1. Cohortes NOMMÉES : où vont les anciens 0 / HC / NC / A / B / C / D (statut + bande V2).
  2. Matrice COMPLÈTE bande V1 × (statut V2) et bande V1 × (bande V2), y compris les changements
     entre deux bandes encore estimées.
  3. Décomposition à ENTRÉES CONSTANTES (même R, pente, forme, accès) isolant : retrait du
     coefficient bâti · retrait du ×0,5 AU · (recalcul de capacité et changements de statut notés).

Lecture seule.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import Session                   # noqa: E402

from labuse import runs                              # noqa: E402
from labuse.scoring import score_labuse as sl        # noqa: E402

RUN = "q_v20"
STATUTS = ["ESTIMATED", "PRESTUDY", "COMPUTE_PENDING", "TO_VERIFY", "DEFERRED",
           "NO_MARGIN", "OUTSIDE_OBJECTIVE"]
BANDES = ["A", "B", "C", "D", "0", "NC", "HC"]
V2_BANDES = ["A", "B", "C", "D"]


def _session() -> Session:
    url = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")
    return Session(bind=create_engine(url))


def _table(counter, order, total=None):
    total = total or (sum(counter.values()) or 1)
    lines = ["| clé | n | part |", "|---|---:|---:|"]
    for k in order + [x for x in sorted(counter) if x not in order]:
        if k in counter:
            lines.append(f"| {k} | {counter[k]} | {100*counter[k]/total:.1f} % |")
    return "\n".join(lines)


def _matrice(session, cols, col_expr, bande_order):
    """Grille bande_v1 (lignes) × `col_expr` (colonnes) sur la conservation."""
    rows = session.execute(text(
        f"SELECT bande_v1, {col_expr} AS c, count(*) FROM parcel_scenario_v2_runs "
        f"WHERE run_label=:r AND scenario='keep' AND bande_v1 IS NOT NULL GROUP BY 1,2"),
        {"r": RUN})
    grid = defaultdict(Counter)
    for v1, c, n in rows:
        grid[v1][c if c is not None else "—"] += 1 and n
    out = ["| V1 ↓ / V2 → | " + " | ".join(cols) + " | (total) |",
           "|" + "---|" * (len(cols) + 2)]
    for v1 in bande_order:
        if v1 in grid:
            tot = sum(grid[v1].values())
            out.append("| " + v1 + " | " + " | ".join(str(grid[v1].get(c, 0)) for c in cols)
                       + f" | {tot} |")
    return "\n".join(out)


# ── Décomposition à entrées constantes (depuis les caches de Score) ──────────
def _f_decompose(e: sl.ScoreEntrees, bareme: dict):
    """Renvoie (score_v1, score_sans_bati, score_v2) à R, pente, forme, accès IDENTIQUES.
    v1 = barème(R, au_classe)·pente·forme·accès·bâti ; sans_bati = idem sans bâti ; v2 = sans bâti
    ET sans ×0,5 AU. Isole exactement l'effet du retrait du coefficient bâti puis du ×0,5 AU."""
    cap, fa = bareme.get("capacite", {}), bareme.get("faisabilite", {})
    bareme_cap_au, _ = sl._bareme_capacite(e.sdp_residuelle_m2, e.au_classe, cap)   # avec ×0,5 AU
    bareme_cap_no, _ = sl._bareme_capacite(e.sdp_residuelle_m2, None, cap)          # sans ×0,5 AU
    f_p, _ = sl._f_pente(e.pente_moy_deg, fa)
    f_fo = sl._f_forme(e.aire_m2, e.perimetre_m, fa)
    f_ac = sl._f_acces(e.acces, fa)
    f_ba = sl._f_bati(e.taux_emprise_pct, e.faitage_m, fa)
    plancher = float(fa.get("plancher", 0.4))
    coef_v1 = max(plancher, f_p * f_fo * f_ac * f_ba)
    coef_no = max(plancher, f_p * f_fo * f_ac)
    s_v1 = min(100, round(bareme_cap_au * coef_v1))
    s_nb = min(100, round(bareme_cap_au * coef_no))      # bâti retiré, AU encore présent
    s_v2 = min(100, round(bareme_cap_no * coef_no))      # bâti ET ×0,5 AU retirés
    return s_v1, s_nb, s_v2


def decomposition(session, bareme, version):
    """À entrées constantes, sur les parcelles CALCULABLES (résiduel présent, R défini). Compte les
    changements de bande à chaque étape ET vérifie l'invariant : retirer le seul bâti ne baisse
    jamais le score."""
    ids = [r[0] for r in session.execute(text(
        "SELECT parcel_id FROM score_labuse WHERE run_label=:r ORDER BY parcel_id"), {"r": RUN})]
    cl = runs.cascade()
    chg_bati = Counter()   # (bande_v1 → bande_sans_bati)
    chg_au = Counter()     # (bande_sans_bati → bande_v2)
    invariant_viole = 0
    n = 0
    for i in range(0, len(ids), 5000):
        lot = ids[i:i + 5000]
        for row in session.execute(sl._ENTREES_SQL, {"ids": lot, "clabel": cl}):
            m = row._mapping
            e = sl.ScoreEntrees(
                parcel_id=m["id"], idu=m["idu"], commune=m["commune"],
                residuel_present=m["residuel_present"], sdp_residuelle_m2=m["sdp"],
                taux_emprise_pct=m["emp"], cause=m["cause"], capacite_estimee=m["capacite_estimee"],
                pente_moy_deg=m["pente_moy_deg"], aire_m2=m["aire"], perimetre_m=m["perim"],
                faitage_m=m["faitage_m"], au_classe=m["au_classe"], acces=m["acces"])
            if sl._cause_nc(e) is not None:            # non calculable : hors décomposition de bande
                continue
            s_v1, s_nb, s_v2 = _f_decompose(e, bareme)
            if s_nb < s_v1:                            # INVARIANT : retrait bâti ne baisse jamais
                invariant_viole += 1
            b_v1, b_nb, b_v2 = (sl.bande_de_score(s_v1, bareme), sl.bande_de_score(s_nb, bareme),
                                sl.bande_de_score(s_v2, bareme))
            if b_nb != b_v1:
                chg_bati[f"{b_v1}→{b_nb}"] += 1
            if b_v2 != b_nb:
                chg_au[f"{b_nb}→{b_v2}"] += 1
            n += 1
    return {"n": n, "chg_bati": chg_bati, "chg_au": chg_au, "invariant_viole": invariant_viole}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/audit-2026-11/algo-fix-1/AVANT-APRES.md")
    ap.add_argument("--no-decomp", action="store_true")
    args = ap.parse_args()
    bareme, version = sl.charger_bareme()
    out = ["# ALGO-FIX-1 — BILAN avant/après, un seul instantané (run servi q_v20)",
           "",
           "Statuts/bandes V2 lus de la table de run `parcel_scenario_v2_runs` ; décomposition lue",
           "des caches de Score. Conservation = analogue direct de la note V1. Reconstruction : les",
           "capacités non chiffrées sont « Calcul à compléter » (jamais « Capacité estimée » déduite).",
           ""]
    with _session() as s:
        n_keep = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r "
                                "AND scenario='keep'"), {"r": RUN}).scalar()

        # ── 0. Répartitions d'ensemble ────────────────────────────────────────
        out.append(f"## Île entière — {n_keep} parcelles\n")
        out.append("### Bandes V1 (servies)")
        out.append(_table({r[0]: r[1] for r in s.execute(text(
            "SELECT bande_v1,count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND "
            "scenario='keep' AND bande_v1 IS NOT NULL GROUP BY 1"), {"r": RUN})}, BANDES, n_keep))
        for scn, titre in (("keep", "conservation"), ("rebuild", "reconstruction")):
            out.append(f"\n### Statuts V2 — {titre}")
            out.append(_table({r[0]: r[1] for r in s.execute(text(
                "SELECT status,count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND "
                "scenario=:s GROUP BY 1"), {"r": RUN, "s": scn})}, STATUTS, n_keep))
        out.append("\n### Bandes V2 — conservation (parcelles « Capacité estimée » seulement)")
        out.append(_table({r[0]: r[1] for r in s.execute(text(
            "SELECT band,count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND scenario='keep' "
            "AND band IS NOT NULL GROUP BY 1"), {"r": RUN})}, V2_BANDES))

        # ── 1. Matrice complète ───────────────────────────────────────────────
        out.append("\n## Matrice complète bande V1 × V2 (conservation)\n")
        out.append("### bande V1 × STATUT V2")
        out.append(_matrice(s, STATUTS, "status", BANDES))
        out.append("\n### bande V1 × BANDE V2 (y compris les changements entre deux bandes estimées)")
        out.append(_matrice(s, V2_BANDES + ["—"], "band", BANDES))

        # ── 2. Cohortes nommées ───────────────────────────────────────────────
        out.append("\n## Cohortes nommées (où vont les anciennes bandes)\n")
        for v1 in BANDES:
            rows = s.execute(text(
                "SELECT status, band, count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND "
                "scenario='keep' AND bande_v1=:v GROUP BY 1,2 ORDER BY 3 DESC"), {"r": RUN, "v": v1}).fetchall()
            if not rows:
                continue
            tot = sum(r[2] for r in rows)
            dest = ", ".join(f"{r[0]}{'/'+r[1] if r[1] else ''} {r[2]}" for r in rows[:6])
            out.append(f"- **Anciennes « {v1} » ({tot})** → {dest}"
                       + (" …" if len(rows) > 6 else ""))

        # ── 3. Décomposition à entrées constantes ─────────────────────────────
        if not args.no_decomp:
            out.append("\n## Décomposition à ENTRÉES CONSTANTES (même R, pente, forme, accès)\n")
            d = decomposition(s, bareme, version)
            out.append(f"Sur **{d['n']}** parcelles calculables. Isole les coefficients du recalcul "
                       "de capacité (ici R est tenu CONSTANT = R servi).")
            out.append(f"\n**Invariant retrait bâti** : parcelles dont le score BAISSE en retirant le "
                       f"seul coefficient bâti = **{d['invariant_viole']}** (doit être 0 ; f_bâti ≤ 1).")
            out.append("\n### Changements de bande dus au SEUL retrait du coefficient bâti")
            out.append(_table(d["chg_bati"], []) if d["chg_bati"] else "_aucun_")
            out.append("\n### Changements de bande dus au SEUL retrait du ×0,5 AU (après bâti)")
            out.append(_table(d["chg_au"], []) if d["chg_au"] else "_aucun_")
            out.append("\n> Le reste des mouvements de bande V1→V2 (hors ces deux colonnes) vient du "
                       "RECALCUL des capacités (R servi vs R recalculé) et des changements de statut — "
                       "distincts de l'effet des coefficients.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"→ écrit {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
