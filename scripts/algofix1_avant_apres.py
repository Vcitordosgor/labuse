"""ALGO-FIX-1 — comparaison AVANT/APRÈS sur le même instantané (run servi q_v20, base locale).

Calcule V1 (bande servie `score_labuse`) et V2 (statut + bande du scénario) EN PARALLÈLE, SANS
toucher au service (spec §14.4). Produit, par commune :

  · la répartition des bandes V1 (servie) vs V2 conservation ;
  · les effectifs par STATUT V2 (conservation ET reconstruction) ;
  · le croisement bande V1 → statut V2 ;
  · la liste des parcelles qui CHANGENT (avec la raison) ;
  · ce que la reconstruction récupère sur les parcelles « 0 » saturées (échantillon enrichi).

Usage :
    LABUSE_REEL_DATABASE_URL=… python scripts/algofix1_avant_apres.py [Commune ...] \
        [--enrich-sature N] [--out docs/audit-2026-11/algo-fix-1/AVANT-APRES.md]

Lecture seule. Aucune écriture en base.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import Session                   # noqa: E402

from labuse.scoring import scenarios_v2 as v2        # noqa: E402
from labuse.scoring import scenarios_v2_build as build  # noqa: E402

RUN = "q_v20"
DEFAULT_COMMUNES = ["Entre-Deux"]


def _session() -> Session:
    url = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")
    return Session(bind=create_engine(url))


def _bar(counter: Counter, order: list[str]) -> str:
    total = sum(counter.values()) or 1
    lines = []
    for k in order:
        n = counter.get(k, 0)
        lines.append(f"| {k} | {n} | {100 * n / total:.1f} % |")
    for k in sorted(set(counter) - set(order)):
        n = counter[k]
        lines.append(f"| {k} | {n} | {100 * n / total:.1f} % |")
    return "\n".join(lines)


def analyser_commune(session: Session, commune: str, enrich_sature: int,
                     enrich_all: bool = False) -> dict:
    ids = build.parcel_ids_for_commune(session, commune, run_label=RUN)
    records = build.records_for_parcels(session, ids, run_label=RUN, enrich=enrich_all)

    v1_bandes = Counter()
    v2_keep_statut = Counter()
    v2_keep_bande = Counter()
    v2_rebuild_statut = Counter()
    crois = defaultdict(Counter)                   # bande V1 → statut V2 (conservation)
    changements = []                               # parcelles qui changent de « verdict »
    sature_v1_zero = []                            # parcelles V1 « 0 » saturées (à enrichir)

    for rec, v1 in records:
        v1 = v1 or "?"
        v1_bandes[v1] += 1
        k = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
        r = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
        v2_keep_statut[k.status] += 1
        v2_rebuild_statut[r.status] += 1
        if k.band:
            v2_keep_bande[k.band] += 1
        crois[v1][k.status] += 1

        # « change » = la V1 disait « 0 / NC / HC » (non retenue, muette) mais la V2 nomme une
        # suite actionnable (capacité, préétude, à vérifier avec diagnostic, à différer, hors
        # projet prouvé) ; ou l'inverse (V1 bande constructible → V2 à vérifier / hors projet).
        v1_muette = v1 in ("0", "NC", "HC")
        v2_actionnable = k.status in ("ESTIMATED", "DEFERRED") or r.status == "ESTIMATED"
        if v1_muette and v2_actionnable:
            changements.append((rec.id, v1, k.status, r.status, ";".join(k.cause_codes) or
                                ";".join(r.cause_codes)))
        elif v1 in ("A", "B", "C", "D") and k.status in ("TO_VERIFY", "OUTSIDE_OBJECTIVE"):
            changements.append((rec.id, v1, k.status, r.status, ";".join(k.cause_codes)))

        if v1 == "0" and rec.cause_engine is None and (rec.residual_m2 == 0):
            sature_v1_zero.append(rec.id)

    # Enrichissement : reconstruction exacte sur un échantillon de parcelles « 0 » saturées.
    recup = {"n_testees": 0, "estimees": 0, "net_negatif": 0, "exemples": []}
    if enrich_sature and sature_v1_zero:
        ech = sature_v1_zero[:enrich_sature]
        pid_by_idu = {r[0]: r[1] for r in session.execute(
            text("SELECT idu, id FROM parcels WHERE idu = ANY(:i)"), {"i": ech})}
        pids = [pid_by_idu[i] for i in ech if i in pid_by_idu]
        enr = build.records_for_parcels(session, pids, run_label=RUN, enrich=True)
        for rec, _ in enr:
            r = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
            recup["n_testees"] += 1
            if r.status == "ESTIMATED":
                recup["estimees"] += 1
                if (r.quantities["net_signed"] or 0) < 0:
                    recup["net_negatif"] += 1
                if len(recup["exemples"]) < 5:
                    recup["exemples"].append(
                        (rec.id, r.band, r.quantities["project_total"],
                         r.quantities["existing"], r.quantities["net_signed"]))

    return {"commune": commune, "n": len(records), "v1_bandes": v1_bandes,
            "v2_keep_statut": v2_keep_statut, "v2_keep_bande": v2_keep_bande,
            "v2_rebuild_statut": v2_rebuild_statut, "crois": crois,
            "changements": changements, "n_sature_zero": len(sature_v1_zero), "recup": recup}


def rendu_markdown(resultats: list[dict]) -> str:
    BANDES = ["A", "B", "C", "D", "0", "NC", "HC", "?"]
    STATUTS = ["ESTIMATED", "PRESTUDY", "TO_VERIFY", "DEFERRED", "NO_MARGIN", "OUTSIDE_OBJECTIVE"]
    out = ["# ALGO-FIX-1 — AVANT / APRÈS (run servi q_v20, base locale, lecture seule)",
           "",
           "V1 = bande servie `score_labuse` (note unique 0–100 → bande). V2 = statut + bande du",
           "scénario (conservation sauf mention). Calcul EN PARALLÈLE, service inchangé.",
           ""]
    for r in resultats:
        out.append(f"## {r['commune']} — {r['n']} parcelles")
        out.append("")
        out.append("### Bandes V1 (servies)")
        out.append("| Bande | n | part |\n|---|---:|---:|")
        out.append(_bar(r["v1_bandes"], BANDES))
        out.append("")
        out.append("### Statuts V2 — conservation (bâti conservé)")
        out.append("| Statut | n | part |\n|---|---:|---:|")
        out.append(_bar(r["v2_keep_statut"], STATUTS))
        out.append("")
        out.append("### Statuts V2 — reconstruction")
        out.append("| Statut | n | part |\n|---|---:|---:|")
        out.append(_bar(r["v2_rebuild_statut"], STATUTS))
        out.append("")
        out.append("### Bandes V2 (conservation, parcelles « Capacité estimée »)")
        out.append("| Bande | n | part |\n|---|---:|---:|")
        out.append(_bar(r["v2_keep_bande"], ["A", "B", "C", "D"]))
        out.append("")
        out.append("### Croisement bande V1 → statut V2 (conservation)")
        hdr = "| V1 ↓ / V2 → | " + " | ".join(STATUTS) + " |"
        out.append(hdr)
        out.append("|" + "---|" * (len(STATUTS) + 1))
        for v1 in BANDES:
            if v1 not in r["crois"]:
                continue
            row = r["crois"][v1]
            out.append("| " + v1 + " | " + " | ".join(str(row.get(s, 0)) for s in STATUTS) + " |")
        out.append("")
        rec = r["recup"]
        if rec["n_testees"]:
            out.append("### Reconstruction sur parcelles « 0 » saturées (échantillon enrichi)")
            out.append(f"- {rec['n_testees']} parcelles V1 « Non retenue » (saturées) testées en "
                       f"reconstruction ; **{rec['estimees']} obtiennent un scénario** "
                       f"« Capacité estimée » (dont {rec['net_negatif']} à gain net négatif — "
                       "démolition-reconstruction qui perd de la SDP, affichée signée).")
            if rec["exemples"]:
                out.append("")
                out.append("| IDU | bande V2 | C_rebuild | E | D_net |\n|---|---|---:|---:|---:|")
                for idu, band, c, e, net in rec["exemples"]:
                    out.append(f"| {idu} | {band} | {c:.0f} | {e:.0f} | {net:+.0f} |")
            out.append("")
        out.append(f"### Parcelles qui changent de verdict : {len(r['changements'])}")
        out.append("(V1 muette « 0/NC/HC » → V2 actionnable, ou V1 constructible → V2 à vérifier / "
                   "hors projet, avec la raison V2.)")
        out.append("")
        out.append("| IDU | V1 | V2 conservation | V2 reconstruction | raison V2 |")
        out.append("|---|---|---|---|---|")
        for idu, v1, ks, rs, cause in r["changements"][:40]:
            out.append(f"| {idu} | {v1} | {ks} | {rs} | {cause} |")
        if len(r["changements"]) > 40:
            out.append(f"| … | | | | (+{len(r['changements']) - 40} autres) |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("communes", nargs="*", default=DEFAULT_COMMUNES)
    ap.add_argument("--enrich-sature", type=int, default=50)
    ap.add_argument("--enrich-all", action="store_true",
                    help="calcule C/E live pour TOUTE la commune (~80 ms/parcelle) → reconstruction réelle")
    ap.add_argument("--out", default="docs/audit-2026-11/algo-fix-1/AVANT-APRES.md")
    args = ap.parse_args()
    communes = args.communes or DEFAULT_COMMUNES

    with _session() as s:
        resultats = [analyser_commune(s, c, args.enrich_sature, args.enrich_all) for c in communes]
    md = rendu_markdown(resultats)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    # Résumé console
    for r in resultats:
        print(f"{r['commune']}: {r['n']} parcelles ; V1 bandes={dict(r['v1_bandes'])}")
        print(f"   V2 keep statuts={dict(r['v2_keep_statut'])}")
        print(f"   V2 rebuild statuts={dict(r['v2_rebuild_statut'])}")
        print(f"   saturées 0={r['n_sature_zero']} ; recup={r['recup']['estimees']}/"
              f"{r['recup']['n_testees']} ; changements={len(r['changements'])}")
    print(f"→ écrit {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
