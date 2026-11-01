#!/usr/bin/env python3
"""AUDIT-NU-3-J — matrice fait × surface sur les surfaces JSON (temps réel).
Pour chaque parcelle, chaque fait (notion) est relevé sur chaque surface qui l'affiche :
  fiche API, comparateur (liste/carte), carte geojson, Gabarit, Étude de faisabilité,
  Estimer un bien (+ classement). Les PDF/Docs sont traités par docs_coherence (03).
Une cellule par couple (fait, surface). Écart = valeurs différentes (après normalisation
de FORME seulement : 625≠630 reste un écart). Lecture seule."""
import json, os, sys, csv, urllib.request, urllib.parse
API = "http://127.0.0.1:9310"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")

def get(path, timeout=60):
    try:
        with urllib.request.urlopen(API + path, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        return {"__err__": str(e)}

def gp(o, path, default=None):
    cur = o
    for k in path.split("."):
        if isinstance(cur, list):
            try: cur = cur[int(k)]
            except Exception: return default
        elif isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
        if cur is None:
            return default
    return cur

# ── normalisation de forme (pas de tolérance de valeur) ──
def nnum(v):
    if v is None: return None
    try:
        f = float(v)
        return int(round(f)) if abs(f - round(f)) < 1e-9 else round(f, 1)
    except Exception:
        return v
def nzone(v):
    if v is None: return None
    return str(v).strip().upper()
def nstr(v):
    if v is None: return None
    return str(v).strip().lower()
def nbool(v):
    if v is None: return None
    return bool(v)

# ── extracteurs : notion -> {surface: (fetchkey, fn)} ──
# surfaces : fiche, compare, map, gabarit, faisa, estimer, classement
def E(fn, norm): return (fn, norm)

NOTIONS = {
 "surface_contenance_m2": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"contenance_m2"), nnum),
    "fiche_terrain": E(lambda f,c,m,g,fa,es,cl: gp(f,"surface_terrain_m2"), nnum),
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"surface_m2"), nnum),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"surface_terrain_m2"), nnum),
    "gabarit": E(lambda f,c,m,g,fa,es,cl: gp(g,"raccordement.parcelle.surface_m2"), nnum),
 },
 "surface_dessin_m2": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"surface_dessin_m2"), nnum),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"surface_m2"), nnum),
 },
 "zone_plu": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"reglement_plu.zones.0.zone"), nzone),
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"zone"), nzone),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"zone_lib"), nzone),
    "gabarit": E(lambda f,c,m,g,fa,es,cl: gp(g,"raccordement.zone.code"), nzone),
    "faisa":   E(lambda f,c,m,g,fa,es,cl: gp(fa,"capacite.zone"), nzone),
 },
 "sdp_residuelle_m2": {
    "fiche_potentiel": E(lambda f,c,m,g,fa,es,cl: gp(f,"potentiel_transformation.sdp_residuelle_m2"), nnum),
    "fiche_labuse":    E(lambda f,c,m,g,fa,es,cl: gp(f,"analyse_labuse.sdp_residuelle_m2"), nnum),
    "compare":         E(lambda f,c,m,g,fa,es,cl: gp(c,"sdp_residuelle_m2"), nnum),
    "map":             E(lambda f,c,m,g,fa,es,cl: gp(m,"sdp_residuelle_m2"), nnum),
 },
 "sdp_max_regl_m2": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"sdp_max_m2"), nnum),
    "faisa":   E(lambda f,c,m,g,fa,es,cl: gp(fa,"capacite.fourchette.surface_plancher_m2"), nnum),
 },
 "emprise_ces_pct": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"emprise_ces_pct"), nnum),
    "gabarit": E(lambda f,c,m,g,fa,es,cl: gp(g,"raccordement.plu.emprise_pct"), nnum),
 },
 "bati_existant_pct": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"bati_existant_pct"), nnum),
    "fiche":   E(lambda f,c,m,g,fa,es,cl: (round(100*gp(f,"le_bien.emprise_batie_m2")/gp(f,"le_bien.surface_parcelle_m2"))
                                           if gp(f,"le_bien.emprise_batie_m2") and gp(f,"le_bien.surface_parcelle_m2") else None), nnum),
 },
 "emprise_batie_m2": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"le_bien.emprise_batie_m2"), nnum),
 },
 "hauteur_bati_mesuree_m": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"le_bien.hauteur_faitage_m") or gp(f,"le_bien.hauteur_bati_m"), nnum),
 },
 "hauteur_plu_faitage_m": {
    "gabarit": E(lambda f,c,m,g,fa,es,cl: gp(g,"raccordement.plu.hauteur_faitage_m"), nnum),
 },
 "pente_moy_deg": {
    "fiche":      E(lambda f,c,m,g,fa,es,cl: gp(f,"terrain.pente_moy_deg"), nnum),
    "exposition": E(lambda f,c,m,g,fa,es,cl: gp(es,"__expo_pente__"), nnum),
 },
 "pente_bande": {
    "fiche": E(lambda f,c,m,g,fa,es,cl: gp(f,"terrain.pente_bande"), nstr),
 },
 "exposition_orient": {
    "fiche":      E(lambda f,c,m,g,fa,es,cl: gp(f,"exposition.orientation") or gp(f,"exposition"), nstr),
    "exposition": E(lambda f,c,m,g,fa,es,cl: gp(es,"__expo_orient__"), nstr),
 },
 "n_aleas": {
    "estimer": E(lambda f,c,m,g,fa,es,cl: gp(es,"n_aleas"), nnum),
    "fiche":   E(lambda f,c,m,g,fa,es,cl: len(gp(f,"aleas") or []) if isinstance(gp(f,"aleas"),list) else gp(f,"aleas.n"), nnum),
 },
 "derniere_vente_valeur": {
    "fiche": E(lambda f,c,m,g,fa,es,cl: gp(f,"dvf_parcelle.derniere_mutation.valeur"), nnum),
 },
 "derniere_vente_date": {
    "fiche": E(lambda f,c,m,g,fa,es,cl: gp(f,"dvf_parcelle.derniere_mutation.date_mutation"), nstr),
 },
 "mediane_bati_eur_m2": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"prix_ancien.median"), nnum),
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"prix_secteur_bati_m2"), nnum),
    "estimer": E(lambda f,c,m,g,fa,es,cl: gp(es,"median") if gp(es,"type_comparateur")=="bati" else None, nnum),
 },
 "mediane_terrain_eur_m2": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"terrain_zone_eur_m2"), nnum),
    "estimer": E(lambda f,c,m,g,fa,es,cl: gp(es,"median") if gp(es,"type_comparateur")=="terrain" else None, nnum),
 },
 "proprietaire_type": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: ("personne morale" if gp(f,"proprietaire_moral") else None), nstr),
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"proprietaire"), nstr),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"owner_type"), nstr),
 },
 "palier_tier": {
    "fiche":      E(lambda f,c,m,g,fa,es,cl: gp(f,"score_v2.tier"), nstr),
    "compare":    E(lambda f,c,m,g,fa,es,cl: gp(c,"tier_v2"), nstr),
    "map":        E(lambda f,c,m,g,fa,es,cl: gp(m,"tier_v2"), nstr),
 },
 "classement_bande": {
    "fiche":      E(lambda f,c,m,g,fa,es,cl: gp(f,"analyse_labuse.bande"), nstr),
    "classement": E(lambda f,c,m,g,fa,es,cl: gp(cl,"bande"), nstr),
 },
 "rang_v2": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"rang_v2"), nnum),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"rang_v2"), nnum),
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"score_v2.rang"), nnum),
 },
 "copro": {
    "fiche":   E(lambda f,c,m,g,fa,es,cl: gp(f,"score_v2.copro"), nbool),
    "map":     E(lambda f,c,m,g,fa,es,cl: gp(m,"copro_v2"), nbool),
 },
 "constructible": {
    "compare": E(lambda f,c,m,g,fa,es,cl: gp(c,"constructible"), nbool),
 },
}

def fetch_all(idu, commune, mapidx):
    f  = get(f"/parcels/{urllib.parse.quote(idu)}?source=q_v20")
    c0 = get(f"/compare?idus={urllib.parse.quote(idu)}")
    c  = (gp(c0,"parcels.0") or {}) if "__err__" not in c0 else c0
    m  = mapidx.get(idu, {})
    g  = get(f"/outils/gabarit/{urllib.parse.quote(idu)}")
    fa = get(f"/modules/faisabilite/{urllib.parse.quote(idu)}")
    es = get(f"/radar/annonce/estimation/{urllib.parse.quote(idu)}")
    cl = get(f"/radar/annonce/classement/{urllib.parse.quote(idu)}")
    ex = get(f"/parcels/{urllib.parse.quote(idu)}/exposition")
    # replie l'exposition dans es sous des clés privées
    if isinstance(es, dict):
        es = dict(es)
        es["__expo_pente__"] = gp(ex, "pente_moyenne_deg")
        es["__expo_orient__"] = gp(ex, "orientation")
    return f, c, m, g, fa, es, cl

def load_map_index():
    idx = {}
    sample = json.load(open(os.path.join(OUT, "sample120.json")))
    want = {r["idu"] for r in sample}
    for comm in sorted({r["commune"] for r in sample}):
        d = get(f"/map/parcels.geojson?commune={urllib.parse.quote(comm)}&source=q_v20&limit=200000", timeout=180)
        for ft in (d.get("features") or []):
            p = ft.get("properties") or {}
            if p.get("idu") in want:
                idx[p["idu"]] = p
        print(f"  carte {comm}: {sum(1 for r in sample if r['commune']==comm and r['idu'] in idx)}/5", flush=True)
    return idx

def main():
    sample = json.load(open(os.path.join(OUT, "sample120.json")))
    print(f"indexation carte ({len({r['commune'] for r in sample})} communes)...", flush=True)
    mapidx = load_map_index()
    print(f"carte indexée : {len(mapidx)} parcelles", flush=True)
    rows = []  # (idu, commune, notion, surface, valeur_norm, valeur_brute)
    ecarts = []  # (idu, notion, {surface:val})
    for i, r in enumerate(sample, 1):
        idu, comm = r["idu"], r["commune"]
        f, c, m, g, fa, es, cl = fetch_all(idu, comm, mapidx)
        for notion, surfaces in NOTIONS.items():
            cells = {}
            for surf, (fn, norm) in surfaces.items():
                try:
                    raw = fn(f, c, m, g, fa, es, cl)
                except Exception:
                    raw = None
                val = norm(raw) if raw is not None else None
                rows.append([idu, comm, notion, surf, "" if val is None else val,
                             "" if raw is None else json.dumps(raw, ensure_ascii=False)])
                if val is not None:
                    cells[surf] = val
            distinct = set(cells.values())
            if len(distinct) > 1:
                ecarts.append({"idu": idu, "commune": comm, "notion": notion, "cells": cells})
        if i % 20 == 0:
            print(f"  {i}/120", flush=True)
    # écriture
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "matrix_json.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["idu","commune","notion","surface","valeur","brut"])
        w.writerows(rows)
    json.dump(ecarts, open(os.path.join(OUT, "ecarts_json.json"), "w"), ensure_ascii=False, indent=1)
    # résumé
    n_cells = sum(1 for r in rows if r[4] != "")
    print(f"\nCELLULES NON VIDES : {n_cells}  (lignes CSV {len(rows)})")
    print(f"ÉCARTS inter-surfaces : {len(ecarts)}")
    from collections import Counter
    byn = Counter(e["notion"] for e in ecarts)
    for n, k in byn.most_common():
        print(f"  {n:28} {k}")

if __name__ == "__main__":
    main()
