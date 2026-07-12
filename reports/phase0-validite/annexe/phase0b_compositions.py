import csv, importlib.util, sys
from collections import defaultdict
from datetime import date
from pathlib import Path
sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("bt", "scripts/score-v/backtest.py")
bt = importlib.util.module_from_spec(spec); spec.loader.exec_module(bt)
from sqlalchemy import text
from labuse.db import session_scope
from labuse.scoring import score_v_constants as C
from labuse.scoring.score_v import (_load_denom_lookups, _load_enrichments, _load_friches,
    _load_owner_links, _retain, _signal, _tenure_qualifiee, classify_owner, resolve_owner)
OUT = Path("reports/phase0-validite")
with session_scope() as s:
    links = {lk["idu"]: lk for lk in _load_owner_links(s)}
    lookups = _load_denom_lookups(s); fiches = _load_enrichments(s); friches = _load_friches(s)
    ages_ym = dict(s.execute(text(
        "SELECT siren, min(date_naissance) FROM ("
        " SELECT siren, date_naissance FROM pm_dirigeants WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL"
        " UNION ALL SELECT siren, date_naissance FROM pm_dirigeant_gigogne WHERE date_naissance IS NOT NULL) x GROUP BY siren")).all())
    bodacc = defaultdict(list)
    for siren, fam, nature, d in s.execute(text(
            "SELECT siren, famille, COALESCE(nature,''), date_annonce FROM bodacc_annonces_owner")).all():
        bodacc[siren].append({"famille": fam, "nature": nature.lower(), "date": d})
    mutations = defaultdict(list)
    for idu, d, nat in s.execute(text(
            "SELECT id_parcelle, date_mutation, nature_mutation FROM dvf_mutations_parcelle WHERE date_mutation IS NOT NULL")).all():
        mutations[idu].append((d, nat))
    def detail(t, idu):
        lk = links.get(idu); ow = None
        if lk:
            res = resolve_owner(lk, lookups)
            fiche0 = fiches.get(res["siren"]) if res["siren"] else None
            ow = {**res, "owner_type": classify_owner(lk, res["siren"], fiche0), "forme": lk["forme"]}
        otype = ow["owner_type"] if ow else "pp"
        if otype in ("public", "bailleur"): return None, []
        cands = []
        matched = bool(ow and ow.get("siren") and ow.get("confiance"))
        factor = C.FALLBACK_AFFECTED_FAMILIES if (matched and ow["confiance"] == C.CONF_DENOMINATION) else None
        m = {"type": "bt", "valeur": idu, "confiance": 1.0}
        fiche = fiches.get(ow["siren"]) if matched else None
        gg = bool(fiche and fiche.get("categorie_entreprise") in C.GRANDS_GROUPES_CATEGORIES)
        if matched:
            a_pts = bt.famille_a_at(bodacc.get(ow["siren"], []), t)
            if a_pts:
                cands.append(_signal({35:"BODACC_LJ",30:"BODACC_RJ",25:"BODACC_RADIATION",20:"BODACC_SAUVEGARDE",10:"BODACC_CESSION_FONDS"}[a_pts], source="BT", match=m))
            if not gg and fiche and fiche.get("etat_administratif") == "C" and fiche.get("date_fermeture"):
                try:
                    if date.fromisoformat(fiche["date_fermeture"]) <= t: cands.append(_signal("RNE_CESSATION", source="BT", match=m))
                except ValueError: pass
            ym = ages_ym.get(ow["siren"])
            if ym and not gg:
                age_t = t.year - int(ym[:4]) - (1 if t.month < int(ym[5:7] or 12) else 0)
                code = "RNE_DIRIGEANT_75" if age_t >= 75 else "RNE_DIRIGEANT_70" if age_t >= 70 else "RNE_DIRIGEANT_65" if age_t >= 65 else None
                if code: cands.append(_signal(code, source="BT", match=m))
            if fiche and fiche.get("date_creation") and not gg:
                est_sci = str(fiche.get("nature_juridique")) == "6540" or "SCI" in (ow.get("forme") or "")
                try:
                    if est_sci and date.fromisoformat(fiche["date_creation"]) <= t.replace(year=t.year - C.SCI_DORMANTE_AGE_ANS):
                        cands.append(_signal("RNE_SCI_DORMANTE", source="BT", match=m))
                except ValueError: pass
            if fiche and not gg:
                siege = fiche.get("siege") or {}
                if siege.get("code_pays_etranger") or (siege.get("departement") and siege["departement"] != "974"):
                    cands.append(_signal("GEO_HORS_ILE", source="BT", match=m))
                elif siege.get("commune_insee") and siege["commune_insee"] != idu[:5]:
                    cands.append(_signal("GEO_AUTRE_COMMUNE", source="BT", match=m))
        if idu in friches: cands.append(_signal("FRICHE", source="BT", match=m))
        antecedentes = [d for d, _ in mutations.get(idu, []) if d <= t]
        if not antecedentes and _tenure_qualifiee(cands): cands.append(_signal("DVF_TENURE_OBS5", source="BT", match=m))
        retained, total = _retain(cands, factor)
        if antecedentes and max(antecedentes) >= bt.months_before(t, C.ACHAT_RECENT_WINDOW_MONTHS):
            total += C.MALUS_ACHAT_RECENT[1]
        return max(0, min(100, total)), sorted(f"{sg['code']}" for sg in retained)
    rows = []
    with open("reports/score-v/backtest_cohorte.csv") as f:
        for r in csv.DictReader(f):
            if r["v"] not in ("", "None") and 8 <= int(r["v"]) < 25:
                rows.append((r["idu"], int(r["vendue"]), date.fromisoformat(r["t"])))
    combo = defaultdict(lambda: [0, 0])
    out = []
    for idu, vendue, t in rows:
        v, codes = detail(t, idu)
        key = ";".join(codes)
        combo[key][0] += 1; combo[key][1] += vendue
        out.append([idu, vendue, t.isoformat(), v, key])
    with open(OUT / "lot2_bande_8_24_composition.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["idu", "vendue", "T", "v_recalcule", "codes"]); w.writerows(out)
    print("── bande 8-24 : top combos (n, vendues, taux) ──")
    for k, (n, v) in sorted(combo.items(), key=lambda x: -x[1][0])[:10]:
        print(f"{n:>5} {v:>4} {v/n:5.1%}  {k or '(aucun)'}")
    # à surveiller : décomposition du verrou
    r = s.execute(text(
        "SELECT count(*), count(*) FILTER (WHERE a_score < 60) a_bas, "
        "count(*) FILTER (WHERE a_score >= 60 AND COALESCE(a_completude,0) < 50) verrou_completude "
        "FROM dryrun_parcel_evaluations WHERE run_label='q_v3_datagap' AND matrice_statut='a_surveiller'")).one()
    print(f"a_surveiller: {r[0]} | A<60: {r[1]} | A≥60 mais complétude<50 (ou hors-zone): {r[2]}")
