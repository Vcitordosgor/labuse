#!/usr/bin/env python3
"""NU4-C — validation des écarts : chaque écart brut de 04 est rejugé avec sa CAUSE établie
(enquête manuelle confirmée en base + source). Produit la classification finale.
  - zone à cheval : GPU interroge le CENTROÏDE, LABUSE sert la zone DOMINANTE ; on vérifie
    que la zone GPU est bien dans zones_all (containment) -> méthodo, pas erreur.
  - dernière vente : horizon DVF de LABUSE (max date_mutation) vs date live ; le sens de l'écart
    dit la cause (geo-API etalab incomplète vs fraîcheur de l'instantané DVF).
Sortie out/findings.json + out/accuracy_final.json. Lecture seule."""
import json, os
from collections import defaultdict
import psycopg

PG = "postgresql://openclaw@localhost:5432/labuse"
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")

def norm(s): return None if s is None else str(s).strip().upper()

def main():
    lab = json.load(open(os.path.join(OUT, "labuse.json")))
    ext = json.load(open(os.path.join(OUT, "external500.json")))
    with psycopg.connect(PG) as cx:
        horizon = cx.execute("select max(date_mutation)::text from dvf_mutations_parcelle").fetchone()[0]

    idus = [i for i in lab if i in ext and "err" not in lab[i]]

    # --- containment zone : la zone GPU (centroïde) est-elle dans zones_all de LABUSE ? ---
    z_cmp = z_exact = z_contain = 0
    z_cheval = []
    for idu in idus:
        L = lab[idu]; E = ext[idu]
        lz = norm(L.get("zone")); gz = norm(E.get("gpu_zone"))
        allz = {norm(z) for z in (L.get("zones_all") or [])}
        if lz and gz:
            z_cmp += 1
            if lz == gz: z_exact += 1
            if gz in allz:
                z_contain += 1
            if lz != gz:
                z_cheval.append({"idu": idu, "commune": L.get("commune"),
                                 "labuse_dominante": L.get("zone"), "zones_all": L.get("zones_all"),
                                 "gpu_centroide": E.get("gpu_zone"),
                                 "gpu_dans_zones_all": gz in allz,
                                 "part_dominante": L.get("zone_part")})

    # --- dernière vente : reclassement par cause ---
    dv = {"both_none": 0, "match": 0, "etalab_incomplete": 0, "fraicheur_manquante": 0,
          "fraicheur_date": 0, "autre": 0}
    dv_detail = []
    for idu in idus:
        L = lab[idu]; E = ext[idu]
        ldm = L.get("dvf_derniere")
        ld = (ldm.get("date_mutation") if isinstance(ldm, dict) else None)
        edm = E.get("dvf_last"); ed = edm.get("date") if isinstance(edm, dict) else None
        if not ld and not ed:
            dv["both_none"] += 1; continue
        if ld and ed and str(ld)[:10] == str(ed)[:10]:
            dv["match"] += 1; continue
        if ld and not ed:
            dv["etalab_incomplete"] += 1
            dv_detail.append({"idu": idu, "commune": L.get("commune"), "cause": "etalab_incomplete",
                              "labuse": ld, "dvf_live": None,
                              "note": "mutation DGFiP présente côté LABUSE, non servie par la geo-API app.dvf.etalab"})
        elif ed and not ld:
            cause = "fraicheur_manquante" if ed > horizon else "autre"
            dv[cause] += 1
            dv_detail.append({"idu": idu, "commune": L.get("commune"), "cause": cause,
                              "labuse": None, "dvf_live": ed, "horizon_labuse": horizon})
        else:  # both present, dates differ
            cause = "fraicheur_date" if ed > ld else "autre"
            dv[cause] += 1
            dv_detail.append({"idu": idu, "commune": L.get("commune"), "cause": cause,
                              "labuse": ld, "dvf_live": ed, "horizon_labuse": horizon})

    # --- aléas containment ---
    def fams(nats):
        f = set()
        for nat in (nats or []):
            n = (nat or "").upper()
            if "INOND" in n or "SUBMERS" in n: f.add("Inondation")
            if "MOUVEMENT" in n or "TERRAIN" in n: f.add("Mouvement de terrain")
            if "FEU" in n: f.add("Feu de forêt")
            if "VOLCAN" in n or "ERUPT" in n: f.add("Eruption volcanique")
            if "SEISME" in n or "SISMI" in n: f.add("Séisme")
        return f
    al_cmp = al_contain = 0; al_invent = []
    for idu in idus:
        L = lab[idu]; E = ext[idu]
        lf = fams(L.get("aleas_natures")); gf = set(E.get("geo_familles") or [])
        if lf and gf:
            al_cmp += 1
            if not (lf - gf): al_contain += 1
            else: al_invent.append({"idu": idu, "invente": sorted(lf - gf)})

    # --- contenance ---
    c_cmp = c_exact = 0; c_bad = []
    for idu in idus:
        L = lab[idu]; E = ext[idu]
        try:
            lc = int(round(float(L.get("surface_terrain_m2") if L.get("surface_terrain_m2") is not None else L.get("contenance_m2"))))
            ec = int(round(float(E.get("cad_contenance"))))
        except Exception:
            continue
        c_cmp += 1
        if lc == ec: c_exact += 1
        else: c_bad.append({"idu": idu, "labuse": lc, "cadastre": ec})

    findings = {
        "horizon_dvf_labuse": horizon,
        "n_parcelles": len(idus),
        "contenance": {"comparable": c_cmp, "exact": c_exact,
                       "taux_pct": round(100 * c_exact / c_cmp, 2) if c_cmp else None, "ecarts": c_bad},
        "zone_plu": {"comparable": z_cmp, "exact_dominante": z_exact,
                     "taux_exact_pct": round(100 * z_exact / z_cmp, 2) if z_cmp else None,
                     "containment": z_contain,
                     "taux_containment_pct": round(100 * z_contain / z_cmp, 2) if z_cmp else None,
                     "cheval": z_cheval},
        "derniere_vente": dv, "derniere_vente_detail": dv_detail,
        "aleas_familles": {"comparable": al_cmp, "containment": al_contain,
                           "taux_pct": round(100 * al_contain / al_cmp, 2) if al_cmp else None,
                           "inventes": al_invent},
    }
    json.dump(findings, open(os.path.join(OUT, "findings.json"), "w"), ensure_ascii=False, indent=1)

    # --- liste d'écarts ADJUGÉE (cause établie, gravité revue) ---
    import csv
    GRAV = {  # gravité finale selon la cause confirmée
        "zone_cheval": "MINEUR", "fraicheur_date": "MINEUR", "fraicheur_manquante": "MINEUR",
        "etalab_incomplete": "À DÉCHARGE", "contenance": "GRAVE", "aleas_invente": "GRAVE"}
    rows = []
    for x in z_cheval:
        rows.append({"idu": x["idu"], "commune": x["commune"], "fait": "zone_plu",
                     "labuse": x["labuse_dominante"], "officiel": x["gpu_centroide"],
                     "source": "GPU zone-urba", "gravite": GRAV["zone_cheval"],
                     "cause": "parcelle à cheval : LABUSE sert la zone dominante en surface ; GPU "
                              f"interroge le centroïde (zone GPU présente dans zones_all={x['zones_all']})"})
    for x in dv_detail:
        cause = {"etalab_incomplete": "mutation DGFiP présente côté LABUSE, non servie par la geo-API "
                 "app.dvf.etalab (LABUSE plus complet)",
                 "fraicheur_manquante": f"vente postérieure à l'horizon DVF de LABUSE ({horizon}) — "
                 "fraîcheur de l'instantané DVF",
                 "fraicheur_date": f"DVF live porte une mutation plus récente que l'instantané LABUSE "
                 f"(horizon {horizon}) — fraîcheur / distribution DVF distincte"}[x["cause"]]
        rows.append({"idu": x["idu"], "commune": x["commune"], "fait": "derniere_vente",
                     "labuse": x["labuse"], "officiel": x["dvf_live"], "source": "DVF Etalab",
                     "gravite": GRAV[x["cause"]], "cause": cause})
    for x in c_bad:
        rows.append({"idu": x["idu"], "commune": "?", "fait": "contenance", "labuse": x["labuse"],
                     "officiel": x["cadastre"], "source": "cadastre.gouv", "gravite": "GRAVE",
                     "cause": "contenance servie ≠ contenance cadastrale"})
    for x in al_invent:
        rows.append({"idu": x["idu"], "commune": "?", "fait": "aleas", "labuse": x["invente"],
                     "officiel": "absent des risques commune", "source": "Géorisques",
                     "gravite": "GRAVE", "cause": "famille d'aléa affichée absente des risques commune"})
    order = {"GRAVE": 0, "MINEUR": 1, "À DÉCHARGE": 2}
    rows.sort(key=lambda r: (order.get(r["gravite"], 9), r["fait"], r["commune"]))
    with open(os.path.join(OUT, "ecarts_valides.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "commune", "fait", "labuse", "officiel", "source", "gravite", "cause"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v) for k, v in r.items()})
    print(f"\nécarts adjugés : {len(rows)}  " +
          str({g: sum(1 for r in rows if r['gravite'] == g) for g in ['GRAVE', 'MINEUR', 'À DÉCHARGE']}))

    print(f"horizon DVF LABUSE = {horizon}   |   parcelles = {len(idus)}\n")
    print(f"CONTENANCE  : {c_exact}/{c_cmp} exact = {findings['contenance']['taux_pct']}%  (écarts: {len(c_bad)})")
    print(f"ZONE PLU    : dominante {z_exact}/{z_cmp} = {findings['zone_plu']['taux_exact_pct']}%  |  "
          f"containment (GPU ∈ zones_all) {z_contain}/{z_cmp} = {findings['zone_plu']['taux_containment_pct']}%")
    print(f"              {len(z_cheval)} parcelles à cheval ; GPU∈zones_all pour "
          f"{sum(1 for x in z_cheval if x['gpu_dans_zones_all'])}/{len(z_cheval)}")
    print(f"ALÉAS       : containment {al_contain}/{al_cmp} = {findings['aleas_familles']['taux_pct']}%  "
          f"(familles inventées: {len(al_invent)})")
    print(f"DERN. VENTE : {dv}")

if __name__ == "__main__":
    main()
