#!/usr/bin/env python3
"""SCORING-7 §5 — comparaison du candidat q_v15 contre le SERVI q_v11_m137 (LECTURE SEULE).

q_v15 : score_labuse (run_label 'q_v15', bandes A/B/C/D/0/NC + Signal fort/moyen/faible).
servi : parcel_p_score_v2 (run_id 'q_v11_m137', p_raw + tier → ancien palier client).
Rien n'est servi, rien n'est promu. Sorties CSV/JSON dans reports/scoring-7/.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text

from labuse.db import engine

OUT = Path(__file__).resolve().parent
TEMOINS = Path("/Users/openclaw/Desktop/labuse-scoring5/reports/scoring-5/TEMOINS.csv")
BANDES = ("A", "B", "C", "D", "0", "NC")
NIVEAUX = ("fort", "moyen", "faible", None)

# ancien tier q_v11 → palier client (RAW, sans la projection PRIORITE_SERVIE : on VEUT voir
# où partent les « Priorité » d'origine = brûlante).
PALIER = defaultdict(lambda: "Sans signal", {
    "brulante": "Priorité", "chaude": "À suivre", "exclue": "Écartée", "ecartee": "Écartée"})
PALIER_ORDRE = ["Priorité", "À suivre", "Sans signal", "Écartée"]


def _load(eng):
    q15 = {r.idu: r for r in eng.execute(text(
        "SELECT idu, commune, score, bande, non_calculable, signal_p, signal_niveau, "
        "cascade_exclue, contributions FROM score_labuse WHERE run_label='q_v15'"))}
    servi = {r.idu: r for r in eng.execute(text(
        "SELECT parcelle_id AS idu, p_raw, tier FROM parcel_p_score_v2 WHERE run_id='q_v11_m137'"))}
    return q15, servi


def section1(q15):
    """Répartition île + par commune des bandes et des niveaux de Signal."""
    bande = Counter(r.bande for r in q15.values())
    niveau = Counter((r.signal_niveau or "—") for r in q15.values())
    par_commune = defaultdict(Counter)
    for r in q15.values():
        par_commune[r.commune][r.bande] += 1
    with (OUT / "bandes_ile.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["bande", "n", "pct"])
        tot = sum(bande.values())
        for b in BANDES:
            w.writerow([b, bande.get(b, 0), round(100 * bande.get(b, 0) / tot, 2)])
    with (OUT / "bandes_par_commune.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["commune", *BANDES, "total"])
        for com in sorted(par_commune):
            c = par_commune[com]
            w.writerow([com, *[c.get(b, 0) for b in BANDES], sum(c.values())])
    print("== §5.1 bandes île ==")
    tot = sum(bande.values())
    for b in BANDES:
        print(f"  {b:>3}: {bande.get(b,0):>7} ({100*bande.get(b,0)/tot:5.2f} %)")
    print("== niveaux Signal île ==", dict(niveau))
    return bande, niveau


def section2(q15, servi):
    """Croisement ancien palier q_v11 × nouvelle bande q_v15 — où partent les « Priorité »."""
    cross = defaultdict(Counter)
    for idu, r in q15.items():
        s = servi.get(idu)
        pal = PALIER[s.tier] if s else "Sans signal"
        cross[pal][r.bande] += 1
    with (OUT / "croisement_palier_bande.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["ancien_palier_q_v11", *BANDES, "total"])
        for pal in PALIER_ORDRE:
            c = cross[pal]
            w.writerow([pal, *[c.get(b, 0) for b in BANDES], sum(c.values())])
    print("\n== §5.2 ancien palier q_v11 × nouvelle bande q_v15 ==")
    print(f"  {'palier':<12}" + "".join(f"{b:>7}" for b in BANDES) + f"{'tot':>8}")
    for pal in PALIER_ORDRE:
        c = cross[pal]
        print(f"  {pal:<12}" + "".join(f"{c.get(b,0):>7}" for b in BANDES) + f"{sum(c.values()):>8}")
    # focus « Priorité »
    prio = cross["Priorité"]
    print(f"  → anciennes Priorité ({sum(prio.values())}) : " +
          ", ".join(f"{b}={prio.get(b,0)}" for b in BANDES if prio.get(b, 0)))
    return cross


def _contrib_fr(contribs):
    try:
        cs = contribs if isinstance(contribs, list) else json.loads(contribs or "[]")
    except Exception:
        cs = []
    return " · ".join(f"{c.get('sens','')}: {c.get('libelle','')}" for c in cs[:3])


def section3(q15, servi):
    """20 parcelles montées / 20 descendues le plus (delta du Signal p_raw→signal_p), + cause."""
    rows = []
    for idu, r in q15.items():
        s = servi.get(idu)
        if s is None or r.signal_p is None or s.p_raw is None:
            continue
        delta = float(r.signal_p) - float(s.p_raw)
        rows.append((delta, idu, r.commune, float(s.p_raw), float(r.signal_p),
                     PALIER[s.tier], r.bande, r.signal_niveau, _contrib_fr(r.contributions)))
    rows.sort(key=lambda x: x[0])
    desc = rows[:20]
    montees = rows[-20:][::-1]
    with (OUT / "montees_descentes.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sens", "idu", "commune", "p_servi", "signal_p_q_v15", "delta",
                    "ancien_palier", "bande_q_v15", "niveau_q_v15", "cause"])
        for tag, grp in (("montée", montees), ("descente", desc)):
            for d, idu, com, ps, pq, pal, b, niv, cause in grp:
                w.writerow([tag, idu, com, round(ps, 4), round(pq, 4), round(d, 4), pal, b, niv, cause])
    print("\n== §5.3 top 5 montées / descentes (Signal) ==")
    for tag, grp in (("MONTÉE", montees[:5]), ("DESCENTE", desc[:5])):
        for d, idu, com, ps, pq, pal, b, niv, cause in grp:
            print(f"  {tag:<8} {idu} {com[:12]:<12} p {ps:.3f}→{pq:.3f} ({d:+.3f}) {pal}→bande {b}/{niv}")
    return montees, desc


def section4(q15, servi):
    """Les 30 témoins : bande, signal, contributions FR."""
    ref = {r["idu"]: r for r in csv.DictReader(TEMOINS.open())}
    out = []
    print("\n== §5.4 30 témoins (q_v15) ==")
    print(f"  {'idu':<16}{'cat':<9}{'bande':<6}{'sig_p':>7}{'niv':>7}  contributions")
    for idu, meta in ref.items():
        r = q15.get(idu)
        if r is None:
            out.append({"idu": idu, "cat": meta["categorie"], "absent": True}); continue
        sp = f"{float(r.signal_p):.3f}" if r.signal_p is not None else "—"
        contrib = _contrib_fr(r.contributions)
        out.append({"idu": idu, "cat": meta["categorie"], "bande": r.bande,
                    "score": r.score, "signal_p": (float(r.signal_p) if r.signal_p is not None else None),
                    "signal_niveau": r.signal_niveau, "contributions": contrib})
        print(f"  {idu:<16}{meta['categorie']:<9}{r.bande:<6}{sp:>7}{str(r.signal_niveau or '—'):>7}  {contrib[:60]}")
    (OUT / "temoins_q_v15.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    with engine().begin() as eng:
        q15, servi = _load(eng)
    print(f"q_v15 lignes = {len(q15)} · servi q_v11 = {len(servi)}")
    section1(q15)
    section2(q15, servi)
    section3(q15, servi)
    section4(q15, servi)


if __name__ == "__main__":
    main()
