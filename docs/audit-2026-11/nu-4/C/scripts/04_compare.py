#!/usr/bin/env python3
"""NU4-C — confrontation fait par fait : LABUSE (out/labuse.json) vs sources officielles
(out/external500.json). Produit :
  - out/ecarts.csv            : un écart par ligne (idu, commune, fait, labuse, officiel, source, gravité, cause)
  - out/accuracy_by_fait.json : taux d'exactitude par fait (comparables, exacts, taux)
  - out/accuracy_by_commune.json
  - out/stats.json            : synthèse
Un écart = LABUSE ≠ source officielle sur un fait COMPARABLE (les deux renseignés).
Lecture seule."""
import json, os, csv, re, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")

def norm(s):
    if s is None: return None
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()

def toks(s):
    if not s: return set()
    s = norm(s)
    stop = {"RUE", "CHEMIN", "CHE", "ROUTE", "RTE", "IMPASSE", "IMP", "ALLEE", "AVENUE",
            "AV", "BOULEVARD", "RESIDENCE", "RES", "LOT", "LOTISSEMENT", "DE", "LA", "LE",
            "LES", "DES", "DU", "ET", "SAINT", "STE", "ST"}
    return {t for t in re.split(r"[^A-Z0-9]+", s) if len(t) >= 4 and t not in stop}

def to_int(x):
    try: return int(round(float(x)))
    except Exception: return None

def main():
    lab = json.load(open(os.path.join(OUT, "labuse.json")))
    ext = json.load(open(os.path.join(OUT, "external500.json")))
    idus = [i for i in lab if i in ext]

    ecarts = []
    # compteurs: fait -> {comparable, exact}
    fait = defaultdict(lambda: {"comparable": 0, "exact": 0, "labuse_present": 0, "src_present": 0})
    comm = defaultdict(lambda: defaultdict(lambda: {"comparable": 0, "exact": 0}))

    def rec(f, idu, c, ok, comparable=True):
        if comparable:
            fait[f]["comparable"] += 1
            comm[c][f]["comparable"] += 1
            if ok:
                fait[f]["exact"] += 1
                comm[c][f]["exact"] += 1

    def ecart(idu, c, f, labv, offv, src, grav, cause):
        ecarts.append({"idu": idu, "commune": c, "fait": f, "labuse": labv,
                       "officiel": offv, "source": src, "gravite": grav, "cause": cause})

    for idu in idus:
        L = lab[idu]; E = ext[idu]
        if "err" in L: continue
        c = L.get("commune") or E.get("commune")

        # ---- 1. CONTENANCE (cadastre.gouv) ----
        lc = to_int(L.get("surface_terrain_m2") if L.get("surface_terrain_m2") is not None
                    else L.get("contenance_m2"))
        ec = to_int(E.get("cad_contenance"))
        if lc is not None: fait["contenance"]["labuse_present"] += 1
        if ec is not None: fait["contenance"]["src_present"] += 1
        if lc is not None and ec is not None:
            ok = (lc == ec)
            rec("contenance", idu, c, ok)
            if not ok:
                d = abs(lc - ec); pct = 100.0 * d / max(ec, 1)
                grav = "GRAVE" if pct > 5 else ("MAJEUR" if d > 1 else "MINEUR")
                ecart(idu, c, "contenance", lc, ec, "cadastre.gouv (apicarto)", grav,
                      "surface servie ≠ contenance cadastrale (acte périmé/ré-ingestion ou arrondi)")

        # ---- 2. ZONE PLU (Géoportail de l'urbanisme) ----
        lz = norm(L.get("zone")); gz = norm(E.get("gpu_zone"))
        if lz: fait["zone_plu"]["labuse_present"] += 1
        if gz: fait["zone_plu"]["src_present"] += 1
        if lz and gz:
            ok = (lz == gz)
            rec("zone_plu", idu, c, ok)
            if not ok:
                # même famille (1re lettre) = divergence plus douce (millésime/sous-zone)
                same_fam = lz[0] == gz[0]
                grav = "MAJEUR" if not same_fam else "MINEUR"
                ecart(idu, c, "zone_plu", L.get("zone"), E.get("gpu_zone"),
                      "GPU zone-urba (apicarto)", grav,
                      ("zone au centroïde ≠ zone dominante LABUSE (parcelle à cheval)"
                       if same_fam else "libellé/millésime PLU divergent ou parcelle à cheval"))

        # ---- 3. DERNIERE VENTE (DVF officiel) ----
        ldm = L.get("dvf_derniere")
        ld_date = None
        if isinstance(ldm, dict):
            ld_date = ldm.get("date") or ldm.get("date_mutation") or ldm.get("derniere_date")
        edm = E.get("dvf_last")
        ed_date = edm.get("date") if isinstance(edm, dict) else None
        l_has = bool(ld_date); e_has = bool(ed_date)
        if L.get("dvf_derniere") is not None: fait["derniere_vente"]["labuse_present"] += 1
        if edm: fait["derniere_vente"]["src_present"] += 1
        # comparable dès qu'au moins une source se prononce
        if l_has or e_has:
            ok = (str(ld_date)[:10] == str(ed_date)[:10]) if (l_has and e_has) else False
            # présence commune (les deux "pas de vente") = exact
            rec("derniere_vente", idu, c, ok)
            if not ok:
                if l_has != e_has:
                    grav = "MAJEUR"
                    cause = ("vente affichée absente de DVF (VEFA/mutation récente non encore publiée, "
                             "ou rattachement parcellaire)" if l_has else
                             "vente DVF non affichée par LABUSE (fenêtre d'ingestion / rattachement)")
                else:
                    grav = "MINEUR"
                    cause = "date de dernière mutation divergente (multi-mutations / tri)"
                ecart(idu, c, "derniere_vente", ld_date, ed_date, "DVF Etalab", grav, cause)
        # note: les deux absents -> on ne compte PAS (non comparable), évite de gonfler le taux

        # ---- 4. ADRESSE (BAN) — indicatif (fuzzy) ----
        la = L.get("adresse"); ba = E.get("ban_label")
        if la: fait["adresse"]["labuse_present"] += 1
        if ba: fait["adresse"]["src_present"] += 1
        if la and ba:
            shared = toks(la) & toks(ba)
            dist = E.get("ban_dist_m")
            ok = bool(shared) or (isinstance(dist, (int, float)) and dist < 50)
            rec("adresse", idu, c, ok)
            if not ok:
                ecart(idu, c, "adresse", la, ba, "BAN (reverse centroïde)", "MINEUR",
                      "voie LABUSE ≠ voie BAN au centroïde (adressage bâti vs point géométrique)")

        # ---- 5. ALEAS / RISQUES (Géorisques) — containment commune ----
        lfam = set()
        for nat in (L.get("aleas_natures") or []):
            n = norm(nat) or ""
            if "INOND" in n: lfam.add("Inondation")
            if "MOUVEMENT" in n or "TERRAIN" in n: lfam.add("Mouvement de terrain")
            if "SUBMERS" in n: lfam.add("Inondation")
            if "FEU" in n: lfam.add("Feu de forêt")
            if "VOLCAN" in n or "ERUPT" in n: lfam.add("Eruption volcanique")
            if "SEISME" in n or "SISMI" in n: lfam.add("Séisme")
        gfam = set(E.get("geo_familles") or [])
        if L.get("aleas_natures"): fait["aleas_familles"]["labuse_present"] += 1
        if gfam: fait["aleas_familles"]["src_present"] += 1
        if lfam and gfam:
            invented = lfam - gfam
            ok = not invented
            rec("aleas_familles", idu, c, ok)
            if not ok:
                ecart(idu, c, "aleas_familles", sorted(lfam), sorted(gfam),
                      "Géorisques (gaspar commune)", "MAJEUR",
                      f"famille d'aléa affichée absente des risques déclarés de la commune : {sorted(invented)}")

    # ---- agrégats ----
    acc_fait = {}
    for f, d in sorted(fait.items()):
        cmp_ = d["comparable"]
        acc_fait[f] = {"comparable": cmp_, "exact": d["exact"],
                       "taux_pct": round(100.0 * d["exact"] / cmp_, 2) if cmp_ else None,
                       "labuse_present": d["labuse_present"], "src_present": d["src_present"]}
    acc_comm = {}
    for c, fs in sorted(comm.items()):
        acc_comm[c] = {}
        for f, d in fs.items():
            acc_comm[c][f] = {"comparable": d["comparable"], "exact": d["exact"],
                              "taux_pct": round(100.0 * d["exact"] / d["comparable"], 2) if d["comparable"] else None}

    # écriture
    with open(os.path.join(OUT, "ecarts.csv"), "w", newline="") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=["idu", "commune", "fait", "labuse", "officiel", "source", "gravite", "cause"])
        w.writeheader()
        for e in sorted(ecarts, key=lambda x: (["GRAVE", "MAJEUR", "MINEUR"].index(x["gravite"]), x["fait"], x["commune"])):
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in e.items()})
    json.dump(acc_fait, open(os.path.join(OUT, "accuracy_by_fait.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(acc_comm, open(os.path.join(OUT, "accuracy_by_commune.json"), "w"), ensure_ascii=False, indent=1)
    grav_counts = defaultdict(int)
    for e in ecarts: grav_counts[e["gravite"]] += 1
    fait_counts = defaultdict(int)
    for e in ecarts: fait_counts[e["fait"]] += 1
    stats = {"n_parcelles": len(idus), "n_ecarts": len(ecarts),
             "par_gravite": dict(grav_counts), "par_fait": dict(fait_counts),
             "accuracy_by_fait": acc_fait}
    json.dump(stats, open(os.path.join(OUT, "stats.json"), "w"), ensure_ascii=False, indent=1)

    print(f"parcelles confrontées : {len(idus)}")
    print(f"écarts : {len(ecarts)}  {dict(grav_counts)}")
    print("\ntaux d'exactitude par fait :")
    for f, a in acc_fait.items():
        print(f"  {f:18} {a['exact']:4}/{a['comparable']:4}  = {a['taux_pct']}%   (labuse={a['labuse_present']} src={a['src_present']})")

if __name__ == "__main__":
    main()
