#!/usr/bin/env python
"""INDEPENDENT oracle for 'prix médian de secteur' (chirurgical-2).
Reproduces bilan.sector_price logic from scratch (own SQL + pure Python),
WITHOUT importing any app function. Read-only."""
import csv, json, math, os, statistics, sys
import psycopg

DSN = "postgresql://openclaw@localhost:5432/labuse"
FICHE_DIR = os.path.expanduser("~/Desktop/chasse-1")
OUT = os.path.dirname(os.path.abspath(__file__))

ANNEE_REF = 2026                 # today_reunion().year on 2026-11-15
PERIODE_ANS = 5
AN_RECENT = ANNEE_REF - PERIODE_ANS + 1   # 2022
MIN_N = 8
RAYONS = (500.0, 1000.0, 1500.0)
TRIM_FRAC = 0.05
BORNES = (1000.0, 12000.0)

IDUS = ["97422000AD0887","97416000HT0538","97403000AR1517","97404000AM0838",
        "97417000AO0050","97411000IS0448","97404000AY0153","97414000CO0153",
        "97421000BN0260","97422000BW2635","97412000CV0446","97424000AO1198"]

# --- SQL: candidate bati sales for a parcelle (same WHERE as _ventes_bati_dedup) ---
SQL_SALES = """
SELECT d.mutation_id AS mid, d.valeur_fonciere AS val, d.surface_reelle_bati AS surf,
  d.valeur_fonciere / d.surface_reelle_bati AS prix,
  CASE WHEN d.type_local ILIKE '%%APPARTEMENT%%' THEN 'appartement' ELSE 'maison' END AS cat,
  (d.nature_mutation ILIKE '%%futur%%') AS vefa,
  extract(year FROM d.date_mutation)::int AS annee,
  COALESCE(d.surface_terrain, 0) AS terr,
  round(ST_Distance(d.geom::geography, p.centroid::geography)) AS dist
FROM dvf_mutations d, parcels p
WHERE p.id = %(pid)s AND d.commune = p.commune AND d.surface_reelle_bati >= 20
  AND d.valeur_fonciere > 20000
  AND d.nature_mutation IN ('Vente', 'Vente en l''état futur d''achèvement')
  AND d.type_local ILIKE ANY(ARRAY['%%APPARTEMENT%%','%%MAISON%%'])
"""

# Independent derivation of `tp` (type_prioritaire) the app passes to sector_price:
# nature of the parcelle's last DVF sale (histo UNION geo), else bati-non-copro -> maison.
SQL_NATURE = """
WITH u AS (
  SELECT id_mutation, date_mutation d, type_local, surface_terrain terr FROM dvf_mutations_parcelle WHERE id_parcelle=%(idu)s
  UNION ALL
  SELECT id_mutation, date_mutation d, type_local, surface_terrain terr FROM dvf_mutations_histo WHERE id_parcelle=%(idu)s),
lm AS (SELECT id_mutation,d FROM u ORDER BY d DESC LIMIT 1)
SELECT count(*) FILTER (WHERE u.type_local='Maison') n_m,
       count(*) FILTER (WHERE u.type_local='Appartement') n_a,
       max(u.terr) terr
FROM lm JOIN u ON u.id_mutation=lm.id_mutation AND u.d=lm.d
"""
SQL_BATI = """
SELECT (fb.idu IS NOT NULL) AS batie,
  EXISTS(SELECT 1 FROM rnic_coproprietes rc WHERE rc.parcelle_idu = p.idu) AS copro
FROM parcels p LEFT JOIN parcel_filtre_bati fb ON fb.idu = p.idu WHERE p.idu = %(idu)s
"""

SQL_SUBJECT = """
SELECT (SELECT sum(surface_reelle_bati) FROM dvf_mutations_parcelle
          WHERE id_parcelle = p.idu AND type_local IN ('Maison','Appartement')
            AND date_mutation = (SELECT max(date_mutation) FROM dvf_mutations_parcelle
              WHERE id_parcelle = p.idu AND nature_mutation IN ('Vente','Vente terrain à bâtir'))) AS surf,
  COALESCE(p.contenance_m2, p.surface_m2) AS terr
FROM parcels p WHERE p.id = %(pid)s
"""


def dedup(rows):
    seen, sales = {}, []
    for r in rows:
        key = r["mid"] if r["mid"] else (float(r["val"]), float(r["surf"]), int(r["annee"]))
        if key in seen:
            seen[key]["dist"] = min(seen[key]["dist"], float(r["dist"]))
            continue
        d = {"prix": float(r["prix"]), "cat": r["cat"], "annee": int(r["annee"]),
             "dist": float(r["dist"]), "vefa": bool(r["vefa"]),
             "surf": float(r["surf"] or 0), "terr": float(r["terr"] or 0)}
        seen[key] = d
        sales.append(d)
    return sales, len(rows) - len(sales)


def trim_aberrants(sales):
    # filtre bornes [1000,12000] puis trim 5% extremes (floor(n*2.5%) each tail)
    lo_b, hi_b = BORNES
    xs = [s for s in sales if lo_b <= s["prix"] <= hi_b]
    xs_sorted = sorted(xs, key=lambda s: s["prix"])
    n = len(xs_sorted)
    k = int(n * (TRIM_FRAC / 2))
    if k == 0:
        return xs_sorted
    prices = sorted(s["prix"] for s in xs_sorted)
    lo, hi = prices[k], prices[n - 1 - k]
    return [s for s in xs_sorted if lo <= s["prix"] <= hi]


def selection(sales, base_plans):
    for _plabel, an_min in (("recente", AN_RECENT), ("elargie", 0)):
        for label, cats, r, commune in base_plans:
            sub = [s for s in sales if s["cat"] in cats and s["annee"] >= an_min
                   and (commune or s["dist"] <= r)]
            kept = trim_aberrants(sub)
            if len(kept) >= MIN_N:
                return (label, kept, r, commune, sub, _plabel)
    return None


POIDS = {
    "appartement": {"h_dist": 500.0, "h_surf": 160.0, "halflife": 2.0, "h_terr": None},
    "maison":      {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "h_terr": 1500.0},
}
POIDS_DEFAUT = {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "h_terr": None}


def mediane_ponderee(kept, subj_surf, subj_terr, type_bien):
    par = POIDS.get(type_bien or "", POIDS_DEFAUT)
    ref_an = max((s["annee"] for s in kept), default=0)
    is_maison = (type_bien == "maison")
    vw = []
    for s in kept:
        w = 1.0
        hd = par.get("h_dist")
        if hd and isinstance(s.get("dist"), (int, float)):
            w *= math.exp(-((float(s["dist"]) / hd) ** 2))
        hs = par.get("h_surf")
        if hs and subj_surf and subj_surf > 0 and s.get("surf"):
            w *= math.exp(-abs(float(s["surf"]) - float(subj_surf)) / hs)
        ht = par.get("h_terr")
        if ht and is_maison and subj_terr and subj_terr > 0 and (s.get("terr") or 0) > 0:
            w *= math.exp(-abs(float(s["terr"]) - float(subj_terr)) / ht)
        hl = par.get("halflife")
        if hl:
            w *= 0.5 ** (max(0, ref_an - s["annee"]) / hl)
        if not (w > 0) or not math.isfinite(w):
            w = 1e-12
        vw.append((float(s["prix"]), w))
    vw.sort(key=lambda t: t[0])
    total = sum(w for _, w in vw)
    qs, cum = {}, 0.0
    for v, w in vw:
        cum += w
        for c in (0.25, 0.5, 0.75):
            if c not in qs and cum >= total * c:
                qs[c] = v
    for c in (0.25, 0.5, 0.75):
        qs.setdefault(c, vw[-1][0])
    return qs[0.25], qs[0.5], qs[0.75]


def base_plans_for(tp):
    if tp:
        return [(tp, {tp}, r, False) for r in RAYONS] + [(tp, {tp}, 1500.0, True)]
    return ([("appartement", {"appartement"}, r, False) for r in RAYONS]
            + [("mixte (appart+maison)", {"appartement", "maison"}, r, False) for r in RAYONS]
            + [("appartement", {"appartement"}, 1500.0, True),
               ("mixte (appart+maison)", {"appartement", "maison"}, 1500.0, True)])


def quartiles(xs):
    xs = sorted(xs)
    n = len(xs)
    med = statistics.median(xs)
    return (statistics.median(xs[:n // 2]) if n > 1 else xs[0],
            med,
            statistics.median(xs[(n + 1) // 2:]) if n > 1 else xs[0])


def load_served(idu):
    p = os.path.join(FICHE_DIR, idu, "fiche.json")
    d = json.load(open(p))
    pa = d.get("prix_ancien") or {}
    return pa, d.get("marche_synthese")


def main():
    conn = psycopg.connect(DSN)
    rows_out = []
    for idu in IDUS:
        pa, synth = load_served(idu)
        type_servi = pa.get("type_prix")
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT id, commune FROM parcels WHERE idu=%(i)s", {"i": idu})
            pr = cur.fetchone()
            pid, commune = pr["id"], pr["commune"]
            # Derive tp INDEPENDENTLY (= what marche_dvf passes to sector_price)
            cur.execute(SQL_NATURE, {"idu": idu})
            nat = cur.fetchone()
            nm, na = int(nat["n_m"] or 0), int(nat["n_a"] or 0)
            if nm or na:
                nature = "maison" if nm >= na else "appartement"
            elif (nat["terr"] or 0) > 0:
                nature = "terrain"
            else:
                nature = None
            tp = nature if nature in ("maison", "appartement") else None
            if tp is None:
                cur.execute(SQL_BATI, {"idu": idu})
                b = cur.fetchone()
                if b and b["batie"] and not b["copro"]:
                    tp = "maison"
            cur.execute(SQL_SALES, {"pid": pid})
            raw = cur.fetchall()
            cur.execute(SQL_SUBJECT, {"pid": pid})
            subj = cur.fetchone()
        ssurf = float(subj["surf"]) if subj and subj["surf"] else None
        sterr = float(subj["terr"]) if subj and subj["terr"] else None
        sales, n_dup = dedup(raw)
        chosen = selection(sales, base_plans_for(tp))
        if chosen is None:
            sub = [s for s in sales if s["cat"] == tp] if tp else sales
            kept = trim_aberrants(sub)
            chosen = (tp or "mixte (appart+maison)", kept, 1500.0, True, sub, "elargie")
        label, kept_all, radius, commune_fb, sub, periode_seg = chosen
        kept = [s for s in kept_all if not s.get("vefa")]  # exclude VEFA for served median
        prices = [s["prix"] for s in kept]
        annees = [s["annee"] for s in kept]
        if prices:
            q1s, meds, q3s = quartiles(prices)
            simple_med = statistics.median(prices)
            q1w, medw, q3w = mediane_ponderee(kept, ssurf, sterr, tp)
            mn, mx = min(prices), max(prices)
            within = mn <= medw <= mx
            within_q = q1s <= medw <= q3s
            delta = 100 * (medw - simple_med) / simple_med if simple_med else None
        else:
            q1s = meds = q3s = simple_med = q1w = medw = q3w = mn = mx = None
            within = within_q = delta = None

        # served values
        s_med = pa.get("median")
        s_n = pa.get("n")
        s_rad = pa.get("radius_m")
        s_cf = pa.get("commune_fallback")
        s_per = pa.get("periode") or []
        # metadata match
        or_rad = "commune" if commune_fb else int(radius)
        se_rad = "commune" if s_cf else (int(s_rad) if s_rad else None)
        or_per = [min(annees), max(annees)] if annees else None
        meta_match = (s_n == len(kept) and se_rad == or_rad and s_per == or_per
                      and type_servi == label)
        note = ""
        if s_med is not None and medw is not None and abs(round(medw) - s_med) > 2:
            note += f"WEIGHTED_MED_DIFF served={s_med} oracle={round(medw)}; "
        if not meta_match:
            note += f"META n({s_n}/{len(kept)}) rad({se_rad}/{or_rad}) per({s_per}/{or_per}) lab({type_servi}/{label}); "
        if within is False:
            note += "SERVED_OUTSIDE_MINMAX; "
        if delta is not None and abs(delta) > 10:
            note += f"W_VS_SIMPLE {delta:+.1f}%; "

        rows_out.append({
            "idu": idu, "commune": commune, "type_servi": type_servi, "tp_oracle": tp,
            "n_servi": s_n, "rayon_servi": se_rad, "periode_servi": f"{s_per}" if s_per else "",
            "median_servi_weighted": s_med,
            "median_avant": (pa.get("distribution") or {}).get("avant", {}).get("median"),
            "median_apres": (pa.get("distribution") or {}).get("apres", {}).get("median"),
            "n_kept_oracle": len(kept), "radius_oracle": or_rad,
            "median_simple_oracle": round(simple_med) if simple_med else None,
            "median_weighted_oracle": round(medw) if medw else None,
            "min_oracle": round(mn) if mn else None, "max_oracle": round(mx) if mx else None,
            "q1_oracle": round(q1s) if q1s else None, "q3_oracle": round(q3s) if q3s else None,
            "periode_oracle": f"{or_per}" if or_per else "",
            "n_dup_oracle": n_dup, "periode_seg": periode_seg,
            "within_minmax": within, "within_q1q3_simple": within_q,
            "delta_weighted_vs_simple_pct": round(delta, 1) if delta is not None else None,
            "metadata_match": meta_match, "note": note.strip(),
        })
    conn.close()

    cols = ["idu","commune","type_servi","tp_oracle","n_servi","rayon_servi","periode_servi",
            "median_servi_weighted","median_avant","median_apres","n_kept_oracle",
            "radius_oracle","median_simple_oracle","median_weighted_oracle","min_oracle",
            "max_oracle","q1_oracle","q3_oracle","periode_oracle","n_dup_oracle","periode_seg",
            "within_minmax","within_q1q3_simple","delta_weighted_vs_simple_pct",
            "metadata_match","note"]
    with open(os.path.join(OUT, "oracle_prix.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)
    for r in rows_out:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
