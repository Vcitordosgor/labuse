# PHASE 0 « VALIDITÉ DU SIGNAL » — lecture seule. Sorties → reports/phase0-validite/.
# Réutilise la cohorte 2023-2025 telle quelle (reports/score-v/backtest_cohorte.csv) et le
# moteur daté du backtest (scripts/score-v/backtest.py) pour les recomputs à T.
from __future__ import annotations

import csv
import importlib.util
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("bt", "scripts/score-v/backtest.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.scoring import score_v_constants as C  # noqa: E402
from labuse.scoring.score_v import (  # noqa: E402
    _load_denom_lookups, _load_enrichments, _load_friches, _load_owner_links,
    _retain, _signal, _tenure_qualifiee, classify_owner, resolve_owner,
)

OUT = Path("reports/phase0-validite")
OUT.mkdir(parents=True, exist_ok=True)
MILLESIME_REF = date(2025, 1, 1)   # DGFiP « fichier des parcelles … situation 2025 » (cf. synthèse)
VENTE_DEBUT, VENTE_FIN = date(2023, 1, 1), date(2025, 12, 31)
SEED = 974

# ── stats : Wilson, Katz (log-ratio RR), Fisher exact bilatéral ──
def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)

def katz(k1, n1, k0, n0, z=1.959964):
    """RR = (k1/n1)/(k0/n0) avec IC95 log-ratio. Correction 0.5 si zéro."""
    if min(k1, k0) == 0:
        k1, n1, k0, n0 = k1 + 0.5, n1 + 0.5, k0 + 0.5, n0 + 0.5
    rr = (k1 / n1) / (k0 / n0)
    se = math.sqrt(1 / k1 - 1 / n1 + 1 / k0 - 1 / n0)
    return (rr, rr * math.exp(-z * se), rr * math.exp(z * se))

def fisher_two_sided(a, b, c, d):
    """P(table) bilatéral exact (hypergéométrique)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    def pmf(x):
        return (math.comb(c1, x) * math.comb(n - c1, r1 - x)) / math.comb(n, r1)
    p_obs = pmf(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs * (1 + 1e-9))

FAMS = "ABCDE"

def fmt_ci(k, n):
    p, lo, hi = wilson(k, n)
    return f"{p:.1%} [{lo:.1%}–{hi:.1%}]"

with session_scope() as s:
    # ── chargements (identiques au backtest) ──
    links = {lk["idu"]: lk for lk in _load_owner_links(s)}
    lookups = _load_denom_lookups(s)
    fiches = _load_enrichments(s)
    friches = _load_friches(s)
    ages_ym = {}
    for siren, ym in s.execute(text(
            "SELECT siren, min(date_naissance) FROM ("
            "  SELECT siren, date_naissance FROM pm_dirigeants "
            "    WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL "
            "  UNION ALL SELECT siren, date_naissance FROM pm_dirigeant_gigogne "
            "    WHERE date_naissance IS NOT NULL) x GROUP BY siren")).all():
        ages_ym[siren] = ym
    bodacc = defaultdict(list)
    for siren, fam, nature, d in s.execute(text(
            "SELECT siren, famille, COALESCE(nature,''), date_annonce FROM bodacc_annonces_owner")).all():
        bodacc[siren].append({"famille": fam, "nature": nature.lower(), "date": d})
    mutations = defaultdict(list)
    for idu, d, nat in s.execute(text(
            "SELECT id_parcelle, date_mutation, nature_mutation FROM dvf_mutations_parcelle "
            "WHERE date_mutation IS NOT NULL")).all():
        mutations[idu].append((d, nat))

    # ── cohorte EXISTANTE (v stocké = V@T du backtest) ──
    coh = []
    with open("reports/score-v/backtest_cohorte.csv") as f:
        for row in csv.DictReader(f):
            v = int(row["v"]) if row["v"] not in ("", "None") else None
            coh.append({"idu": row["idu"], "vendue": int(row["vendue"]),
                        "t": date.fromisoformat(row["t"]), "v": v})
    vendues = [r for r in coh if r["vendue"] == 1]
    nonvend = [r for r in coh if r["vendue"] == 0]
    # date de vente L1 (min 'Vente' de la fenêtre — même définition que le backtest)
    vente_date = {}
    for r in vendues:
        ds = [d for d, nat in mutations.get(r["idu"], []) if nat == "Vente" and VENTE_DEBUT <= d <= VENTE_FIN]
        vente_date[r["idu"]] = min(ds) if ds else r["t"]  # repli : t + 12 impossible, garde t

    owners = {}
    def owner_of(idu):
        if idu not in owners:
            lk = links.get(idu)
            if lk:
                res = resolve_owner(lk, lookups)
                fiche = fiches.get(res["siren"]) if res["siren"] else None
                owners[idu] = {**res, "owner_type": classify_owner(lk, res["siren"], fiche),
                               "forme": lk["forme"]}
            else:
                owners[idu] = None
        return owners[idu]

    def score_detail(t, idu):
        """Miroir EXACT de bt.score_at + ventilation famille/codes. (None, …) = non applicable."""
        ow = owner_of(idu)
        otype = ow["owner_type"] if ow else "pp"
        if otype in ("public", "bailleur"):
            return None, {}, [], otype, False
        cands = []
        matched = bool(ow and ow.get("siren") and ow.get("confiance"))
        factor = (C.FALLBACK_AFFECTED_FAMILIES
                  if (matched and ow["confiance"] == C.CONF_DENOMINATION) else None)
        m = {"type": "bt", "valeur": idu, "confiance": 1.0}
        fiche = fiches.get(ow["siren"]) if matched else None
        grand_groupe = bool(fiche and fiche.get("categorie_entreprise") in C.GRANDS_GROUPES_CATEGORIES)
        if matched:
            a_pts = bt.famille_a_at(bodacc.get(ow["siren"], []), t)
            if a_pts:
                code = {35: "BODACC_LJ", 30: "BODACC_RJ", 25: "BODACC_RADIATION",
                        20: "BODACC_SAUVEGARDE", 10: "BODACC_CESSION_FONDS"}[a_pts]
                cands.append(_signal(code, source="BT", match=m))
            if not grand_groupe and fiche and fiche.get("etat_administratif") == "C" and fiche.get("date_fermeture"):
                try:
                    if date.fromisoformat(fiche["date_fermeture"]) <= t:
                        cands.append(_signal("RNE_CESSATION", source="BT", match=m))
                except ValueError:
                    pass
            ym = ages_ym.get(ow["siren"])
            if ym and not grand_groupe:
                age_t = t.year - int(ym[:4]) - (1 if t.month < int(ym[5:7] or 12) else 0)
                code = ("RNE_DIRIGEANT_75" if age_t >= 75 else "RNE_DIRIGEANT_70" if age_t >= 70
                        else "RNE_DIRIGEANT_65" if age_t >= 65 else None)
                if code:
                    cands.append(_signal(code, source="BT", match=m))
            if fiche and fiche.get("date_creation") and not grand_groupe:
                est_sci = str(fiche.get("nature_juridique")) == "6540" or "SCI" in (ow.get("forme") or "")
                try:
                    creation = date.fromisoformat(fiche["date_creation"])
                    if est_sci and creation <= t.replace(year=t.year - C.SCI_DORMANTE_AGE_ANS):
                        cands.append(_signal("RNE_SCI_DORMANTE", source="BT", match=m))
                except ValueError:
                    pass
            if fiche and not grand_groupe:
                siege = fiche.get("siege") or {}
                if siege.get("code_pays_etranger") or (siege.get("departement") and siege["departement"] != "974"):
                    cands.append(_signal("GEO_HORS_ILE", source="BT", match=m))
                elif siege.get("commune_insee") and siege["commune_insee"] != idu[:5]:
                    cands.append(_signal("GEO_AUTRE_COMMUNE", source="BT", match=m))
        if idu in friches:
            cands.append(_signal("FRICHE", source="BT", match=m))
        antecedentes = [d for d, _ in mutations.get(idu, []) if d <= t]
        if not antecedentes and _tenure_qualifiee(cands):
            cands.append(_signal("DVF_TENURE_OBS5", source="BT", match=m))
        retained, total = _retain(cands, factor)
        if antecedentes and max(antecedentes) >= bt.months_before(t, C.ACHAT_RECENT_WINDOW_MONTHS):
            total += C.MALUS_ACHAT_RECENT[1]
        fam_pts = defaultdict(int)
        codes = []
        for sg in retained:
            fam_pts[sg["famille"]] += sg["points"]
            codes.append(f"{sg['code']}:{sg['points']}")
        return max(0, min(100, total)), dict(fam_pts), codes, otype, matched

    # ═════════ LOT 1 ═════════
    # 1.1 couverture propriétaire
    n_pm_rows = s.execute(text("SELECT count(DISTINCT idu) FROM parcelle_personne_morale")).scalar()
    ot_counts = Counter()
    for r in coh:
        ow = owner_of(r["idu"])
        ot_counts[ow["owner_type"] if ow else "pp (non identifiée)"] += 1
    # 1.2 partition
    for r in vendues:
        r["vd"] = vente_date[r["idu"]]
        r["part"] = "VENDEUR_CERTAIN" if r["vd"] > MILLESIME_REF else "ACHETEUR_PROBABLE"
    nVC = sum(1 for r in vendues if r["part"] == "VENDEUR_CERTAIN")
    # détail des vendues à LEUR T (recompute, sanity vs v stocké)
    mismatch = 0
    for r in vendues:
        v2, fp, codes, otype, matched = score_detail(r["t"], r["idu"])
        r.update(v2=v2, fam=fp, codes=codes, otype=otype, matched=matched)
        if v2 != r["v"]:
            mismatch += 1
    # 1.3 ventilation des vendues V@T≥1
    vpos = [r for r in vendues if (r["v"] or 0) >= 1]
    rows13 = []
    for r in vpos:
        rows13.append([r["idu"], r["part"], r["vd"].isoformat(), r["v"], r["otype"],
                       *[r["fam"].get(f, 0) for f in FAMS], ";".join(r["codes"])])
    with open(OUT / "lot1_ventilation_vendues_Vpos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "partition", "date_vente", "v_at_T", "owner_type", *[f"pts_{f}" for f in FAMS], "codes"])
        w.writerows(rows13)
    pivot13 = defaultdict(lambda: Counter())
    for r in vpos:
        for f_ in FAMS:
            if r["fam"].get(f_, 0) > 0:
                pivot13[r["part"]][f_] += 1
        pivot13[r["part"]]["total"] += 1
        pivot13[r["part"]][f"ot:{r['otype']}"] += 1

    # 1.4 lift vendeur-certain : négatifs rescorés à T_ref_VC (même protocole)
    vc_dates = sorted(r["vd"] for r in vendues if r["part"] == "VENDEUR_CERTAIN")
    T_REF_VC = bt.months_before(vc_dates[len(vc_dates) // 2], 12)
    neg_vc = []
    for r in nonvend:
        v2, fp, codes, otype, matched = score_detail(T_REF_VC, r["idu"])
        neg_vc.append({"idu": r["idu"], "v": v2, "fam": fp, "otype": otype})
    def lift_block(pos, neg, sel):
        """pos/neg = listes scorées (v peut être None) ; sel(r) → bool exposition."""
        posS = [r for r in pos if r["v"] is not None]
        negS = [r for r in neg if r["v"] is not None]
        n1 = sum(1 for r in posS if sel(r)) ; n0v = sum(1 for r in negS if sel(r))
        expo_n = n1 + n0v
        base_k, base_n = len(posS), len(posS) + len(negS)
        # RR Katz : taux de vente exposés vs NON-exposés
        k_np = len(posS) - n1 ; n_np = (base_n - expo_n)
        rr, lo, hi = katz(n1, expo_n, k_np, n_np) if expo_n and n_np else (float("nan"),) * 3
        lift_base = (n1 / expo_n) / (base_k / base_n) if expo_n and base_k else float("nan")
        return {"expo_vendues": n1, "expo_n": expo_n, "taux_expo": fmt_ci(n1, expo_n) if expo_n else "—",
                "base": fmt_ci(base_k, base_n), "lift_vs_base": lift_base, "rr_katz": (rr, lo, hi)}
    posVC = [dict(v=r["v2"], fam=r["fam"], otype=r["otype"]) for r in vendues if r["part"] == "VENDEUR_CERTAIN"]
    L14 = {
        "V≥1 (toutes familles)": lift_block(posVC, neg_vc, lambda r: (r["v"] or 0) >= 1),
        "identitaires A+B+C ≥1 pt": lift_block(posVC, neg_vc, lambda r: sum(r["fam"].get(f_, 0) for f_ in "ABC") >= 1),
        "actif D+E ≥1 pt": lift_block(posVC, neg_vc, lambda r: sum(r["fam"].get(f_, 0) for f_ in "DE") >= 1),
    }
    # même bloc, période ACHETEUR_PROBABLE (comparaison) — négatifs au T_ref global stocké
    posAP = [dict(v=r["v2"], fam=r["fam"], otype=r["otype"]) for r in vendues if r["part"] == "ACHETEUR_PROBABLE"]
    T_REF_G = nonvend[0]["t"]
    neg_g = []
    for r in nonvend:
        v2, fp, codes, otype, matched = score_detail(T_REF_G, r["idu"])
        neg_g.append({"idu": r["idu"], "v": v2, "fam": fp, "otype": otype})
    L14_AP = {
        "V≥1 (toutes familles)": lift_block(posAP, neg_g, lambda r: (r["v"] or 0) >= 1),
        "identitaires A+B+C ≥1 pt": lift_block(posAP, neg_g, lambda r: sum(r["fam"].get(f_, 0) for f_ in "ABC") >= 1),
        "actif D+E ≥1 pt": lift_block(posAP, neg_g, lambda r: sum(r["fam"].get(f_, 0) for f_ in "DE") >= 1),
    }
    # 1.5 PM vs PP (vendeur-certain)
    L15 = {}
    for ot in ("pm", "pp"):
        L15[ot] = lift_block([r for r in posVC if r["otype"] == ot],
                             [r for r in neg_vc if r["otype"] == ot],
                             lambda r: (r["v"] or 0) >= 1)

    # ═════════ LOT 2 ═════════
    bandes = [("V = 0", 0, 1), ("V 1-7", 1, 8), ("V 8-24", 8, 25), ("V 25-49", 25, 50), ("V ≥ 50", 50, 101)]
    scored = [r for r in coh if r["v"] is not None]
    base_k = sum(r["vendue"] for r in scored)
    rows2 = []
    for label, lo_, hi_ in bandes:
        grp = [r for r in scored if lo_ <= r["v"] < hi_]
        k = sum(r["vendue"] for r in grp)
        rest_k = base_k - k ; rest_n = len(scored) - len(grp)
        rr = katz(k, len(grp), rest_k, rest_n) if grp and rest_n else (float("nan"),) * 3
        lift = (k / len(grp)) / (base_k / len(scored)) if grp else float("nan")
        rows2.append([label, len(grp), k, fmt_ci(k, len(grp)) if grp else "—",
                      f"{lift:.2f}×" if grp else "—",
                      f"{rr[0]:.2f} [{rr[1]:.2f}–{rr[2]:.2f}]" if grp else "—"])
    with open(OUT / "lot2_bandes.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["bande", "n", "vendues", "taux_wilson", "lift_vs_base", "RR_katz_vs_reste"]); w.writerows(rows2)
    # 2.2 composition 25-49 (recompute au T de chaque ligne)
    rows22 = []
    for r in scored:
        if 25 <= r["v"] < 50:
            v2, fp, codes, otype, matched = score_detail(r["t"], r["idu"])
            rows22.append([r["idu"], r["vendue"], r["t"].isoformat(), r["v"], v2, otype,
                           *[fp.get(f_, 0) for f_ in FAMS], ";".join(codes)])
    with open(OUT / "lot2_bande_25_49_composition.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "vendue", "T", "v_stocke", "v_recalcule", "owner_type", *[f"pts_{f_}" for f_ in FAMS], "codes"])
        w.writerows(rows22)
    # 2.3 Fisher 8-24 vs 25-49
    g824 = [r for r in scored if 8 <= r["v"] < 25]; g2549 = [r for r in scored if 25 <= r["v"] < 50]
    a = sum(r["vendue"] for r in g824); b = len(g824) - a
    c_ = sum(r["vendue"] for r in g2549); d_ = len(g2549) - c_
    p_fisher = fisher_two_sided(a, b, c_, d_)

    # ═════════ LOT 3 ═════════
    nat_an = s.execute(text(
        "SELECT extract(year FROM date_mutation)::int an, nature_mutation, count(DISTINCT id_parcelle) "
        "FROM dvf_mutations_parcelle WHERE date_mutation BETWEEN '2021-01-01' AND '2025-12-31' "
        "AND nature_mutation IN ('Adjudication','Echange','Expropriation','Vente terrain à bâtir',"
        "'Vente en l''état futur d''achèvement') GROUP BY 1,2 ORDER BY 1,2")).all()
    with open(OUT / "lot3_natures_par_an.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["annee", "nature", "parcelles"]); w.writerows(nat_an)
    L2_NAT = {"Vente", "Vente terrain à bâtir"}
    L3_NAT = L2_NAT | {"Adjudication"}   # « licitation » : nature absente de la base (6 natures seulement)
    def event_date(idu, natset):
        ds = [d for d, nat in mutations.get(idu, []) if nat in natset and VENTE_DEBUT <= d <= VENTE_FIN]
        return min(ds) if ds else None
    lots3 = {}
    for lab, natset in (("L2", L2_NAT), ("L3", L3_NAT)):
        reflag = []
        for r in nonvend:
            ev = event_date(r["idu"], natset)
            if ev:
                v2, fp, codes, otype, matched = score_detail(bt.months_before(ev, 12), r["idu"])
                reflag.append({"idu": r["idu"], "v": v2, "fam": fp, "otype": otype})
        pos_all = ([dict(v=r["v2"], fam=r["fam"], otype=r["otype"]) for r in vendues] + reflag)
        neg_ids = {r["idu"] for r in reflag}
        neg_all = [r for r in neg_g if r["idu"] not in neg_ids]
        blk = lift_block(pos_all, neg_all, lambda r: (r["v"] or 0) >= 1)
        # bandes sous ce label
        allrows = ([{"v": r["v"], "vendue": 1} for r in pos_all if r["v"] is not None]
                   + [{"v": r["v"], "vendue": 0} for r in neg_all if r["v"] is not None])
        bk = sum(r["vendue"] for r in allrows)
        brows = []
        for label, lo_, hi_ in bandes:
            grp = [r for r in allrows if lo_ <= r["v"] < hi_]
            k = sum(r["vendue"] for r in grp)
            lift = (k / len(grp)) / (bk / len(allrows)) if grp else float("nan")
            brows.append([label, len(grp), k, fmt_ci(k, len(grp)) if grp else "—", f"{lift:.2f}×" if grp else "—"])
        lots3[lab] = {"reflag": len(reflag), "lift_v1": blk, "bandes": brows}
    with open(OUT / "lot3_bandes_labels.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["label", "bande", "n", "vendues", "taux_wilson", "lift"])
        for lab in lots3:
            for b_ in lots3[lab]["bandes"]:
                w.writerow([lab, *b_])

    # ═════════ LOT 4 ═════════
    snaps = s.execute(text("SELECT run_label, min(created_at)::date, max(created_at)::date, count(*) "
                           "FROM dryrun_parcel_evaluations GROUP BY 1 ORDER BY 2")).all()
    dvf_max = s.execute(text("SELECT max(date_mutation) FROM dvf_mutations_parcelle")).scalar()

    # ═════════ LOT 5 ═════════
    sit_an = s.execute(text("SELECT extract(year FROM date)::int, count(*) FROM sitadel_permits GROUP BY 1 ORDER BY 1")).all()
    quads = s.execute(text(
        "SELECT d.matrice_statut, count(*), round(avg(d.q_score),1), round(avg(d.a_score),1), "
        "count(*) FILTER (WHERE vs.owner_type IN ('public','bailleur')) pub_bail, "
        "count(*) FILTER (WHERE vs.owner_type = 'pm') pm, "
        "count(*) FILTER (WHERE vs.owner_type = 'copro') copro "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id "
        "LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu "
        "WHERE d.run_label = 'q_v3_datagap' GROUP BY 1")).all()

    # ═════════ sorties récap ═════════
    def p(*a): print(*a)
    p("=== 1.1 ===", f"parcelles PM identifiées (table) : {n_pm_rows} ; cohorte par owner_type : {dict(ot_counts)}")
    p(f"sanity recompute vendues : {mismatch} écarts v_recalculé ≠ v_stocké / {len(vendues)}")
    p("=== 1.2 ===", f"vendues VC (> {MILLESIME_REF}) : {nVC} · AP : {len(vendues) - nVC} · T_REF_VC = {T_REF_VC}")
    p("=== 1.3 pivot ===")
    for part, cnt in pivot13.items():
        p(part, dict(cnt))
    p("=== 1.4 VC ===")
    for k_, v_ in L14.items():
        p(k_, v_)
    p("=== 1.4 AP (comparaison) ===")
    for k_, v_ in L14_AP.items():
        p(k_, v_)
    p("=== 1.5 PM/PP (VC) ===")
    for k_, v_ in L15.items():
        p(k_, v_)
    p("=== 2.1 ===")
    for r_ in rows2:
        p(r_)
    p("=== 2.2 ===", f"{len(rows22)} parcelles bande 25-49 (CSV)")
    p("=== 2.3 ===", f"Fisher 8-24 ({a}/{a+b}) vs 25-49 ({c_}/{c_+d_}) : p = {p_fisher:.4f}")
    p("=== 3.1 ===")
    for r_ in nat_an:
        p(r_)
    p("=== 3.2 ===")
    for lab in lots3:
        p(lab, "reflag:", lots3[lab]["reflag"], "| lift V≥1:", lots3[lab]["lift_v1"])
        for b_ in lots3[lab]["bandes"]:
            p("   ", b_)
    p("=== 4 ===", f"DVF max = {dvf_max}")
    for r_ in snaps:
        p(r_)
    p("=== 5.1 Sitadel/an ===", sit_an)
    p("=== 5.3 quadrants ===")
    for r_ in quads:
        p(r_)
print("OK →", OUT)
