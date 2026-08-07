"""M48 P0/P1 — GRILLE DE COHÉRENCE (lecture seule, OUTILLÉE).

Pour chaque parcelle de l'échantillon, extrait de CHAQUE surface les grandeurs comparables et
détecte les divergences (G1 contradiction · G2 précision/format · G3 asymétrie · G4 étiquette).

Surfaces interrogées (API live sur le run servi + tables matérialisées) :
  - fiche V2 (premium, front)      GET /parcels/{idu}?source=RUN        → _q_v2_fiche
  - fiche legacy (exports/défaut)   GET /parcels/{idu}                   → _build_fiche
  - export markdown                 GET /parcels/{idu}/export?format=md
  - one-pager comité                GET /parcels/{idu}/export?format=onepager
  - bilan/calculette                GET /modules/faisabilite/{idu}
  - mode B                          GET /parcels/{idu}/mode-b
  - carte (tuiles matérialisées)    DB mvt_parcels
  - vérité de classement            DB parcel_p_score_v2 (run servi)
  - SDP résiduelle                  DB parcel_residuel

Le TIER EFFECTIF (ce que le client voit) suit la règle front verdictMeta : étage 0 → 'ecartee',
sinon tier_v2 ; le champ mort `statut`/`status` (matrice v1, M37) N'EST PAS le tier — s'il diffère
du tier effectif on le consigne comme PIÈGE LATENT, pas comme G1 client.
"""
from __future__ import annotations
import csv, json, re, urllib.request, urllib.error
from labuse.db import make_engine
from sqlalchemy import text

BASE = "http://127.0.0.1:8000"
RUN = "q_v8_calibre"
eng = make_engine()

def _get_json(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        return {"__error__": str(e)}

def _get_text(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return ""

# label produit → tier (miroir verdict_servi.TIER_LABELS)
LABEL2TIER = {
    "brûlante": "brulante", "chaude": "chaude", "potentiel long terme": "reserve_fonciere",
    "à creuser": "a_creuser", "écartée": "ecartee",
    "déclassée — bâti saturé": "declasse_bati_sature",
    "déclassée — inconstructible (géométrie)": "declasse_non_constructible",
    "déclassée — bâti révélé": "declasse_bati_revele",
    "déclassée — fermée à l'urbanisation": "declasse_zone_fermee",
    "déclassée — au à statut inconnu": "declasse_au_statut_inconnu",
    "déclassée — au fermée": "declasse_au_fermee",
}
def _label_to_tier(txt):
    if not txt: return None
    low = txt.lower()
    for lab, t in LABEL2TIER.items():
        if lab in low:
            return t
    return None

def _md_tier(md):
    """Extrait le verdict de l'export md depuis la ligne « **Statut :** <label> »."""
    m = re.search(r"\*\*Statut :\*\*\s*([^(·\n*]+)", md)
    return _label_to_tier(m.group(1).strip()) if m else None

def _onepager_tier(op):
    """Extrait le verdict du one-pager depuis le bloc class="verdict">…</…> (pas le CSS)."""
    m = re.search(r'class="verdict"[^>]*>\s*([A-Za-zÀ-ÿ\'’ —-]+?)\s*<', op)
    return _label_to_tier(m.group(1).strip()) if m else None

def _tier_effectif_v2(fiche):
    """Règle front : étage0 → ecartee ; sinon score_v2.tier."""
    if not fiche or "__error__" in fiche: return None
    if fiche.get("etage0"): return "ecartee"
    sv = fiche.get("score_v2") or {}
    return sv.get("tier")

def _first_num(txt, pat):
    m = re.search(pat, txt)
    if not m: return None
    return int(m.group(1).replace(" ", "").replace(" ", "").replace(" ", "").replace(".", ""))

def extract(idu):
    """→ dict grandeur → {surface: value}."""
    v2 = _get_json(f"/parcels/{idu}?source={RUN}")
    lg = _get_json(f"/parcels/{idu}")
    md = _get_text(f"/parcels/{idu}/export?format=md")
    op = _get_text(f"/parcels/{idu}/export?format=onepager")
    faisa = _get_json(f"/modules/faisabilite/{idu}")
    modeb = _get_json(f"/parcels/{idu}/mode-b")
    with eng.connect() as c:
        db = c.execute(text("SELECT tier,rang,mult_base FROM parcel_p_score_v2 "
                            "WHERE run_id=:r AND parcelle_id=:i"), {"r": RUN, "i": idu}).mappings().first()
        tile = c.execute(text("SELECT tier_v2,rang_v2,mult_v2,status,etage0,sdp_residuelle_m2,flags "
                              "FROM mvt_parcels WHERE idu=:i"), {"i": idu}).mappings().first()
        resid = c.execute(text("SELECT sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id="
                               "(SELECT id FROM parcels WHERE idu=:i)"), {"i": idu}).scalar()

    g: dict[str, dict] = {}
    def put(gr, surf, val):
        if val is not None and val != "":
            g.setdefault(gr, {})[surf] = val

    # tier effectif (client)
    put("tier", "fiche_v2", _tier_effectif_v2(v2))
    put("tier", "fiche_legacy", (lg.get("verdict") or {}).get("tier") if "__error__" not in lg else None)
    if tile: put("tier", "carte_tuile", "ecartee" if tile["etage0"] else tile["tier_v2"])
    if db: put("tier", "db_verite", db["tier"])
    put("tier", "export_md", _md_tier(md))
    put("tier", "onepager", _onepager_tier(op))

    # rang
    put("rang", "fiche_v2", (v2.get("score_v2") or {}).get("rang"))
    put("rang", "fiche_legacy", (lg.get("verdict") or {}).get("rang"))
    if tile: put("rang", "carte_tuile", tile["rang_v2"])
    if db: put("rang", "db_verite", db["rang"])

    # mult (×N)
    put("mult", "fiche_v2", (v2.get("score_v2") or {}).get("mult_base"))
    if tile: put("mult", "carte_tuile", tile["mult_v2"])
    if db: put("mult", "db_verite", db["mult_base"])

    # score_e : prix probable / charge supportable / marge (bilan servi)
    for grge, key in (("prix_probable", "prix_probable"), ("charge_supportable", "charge_supportable"),
                      ("marge_estimee", "marge_estimee")):
        put(grge, "fiche_v2", (v2.get("score_e") or {}).get(key) if isinstance(v2.get("score_e"), dict) else None)
        put(grge, "fiche_legacy", (lg.get("score_e") or {}).get(key) if isinstance(lg.get("score_e"), dict) else None)

    # bilan CA + charge foncière (central) — MÊME compute_bilan attendu partout (Vic #1 : prix identiques)
    def _central(bilan, key):
        v = (bilan or {}).get(key)
        return v.get("central") if isinstance(v, dict) else v
    fa_bilan = faisa.get("bilan") if isinstance(faisa, dict) and "__error__" not in faisa else None
    lg_bilan = (lg.get("faisabilite") or {}).get("bilan") if "__error__" not in lg else None
    put("ca_central", "module_faisa", _central(fa_bilan, "ca"))
    put("ca_central", "fiche_legacy", _central(lg_bilan, "ca"))
    put("charge_fonciere_central", "module_faisa", _central(fa_bilan, "charge_fonciere"))
    put("charge_fonciere_central", "fiche_legacy", _central(lg_bilan, "charge_fonciere"))

    # mode B disponibilité
    put("modeb_dispo", "fiche_v2", (v2.get("mode_b") or {}).get("disponible"))
    put("modeb_dispo", "fiche_legacy", (lg.get("mode_b") or {}).get("disponible"))
    put("modeb_dispo", "endpoint_modeb", modeb.get("disponible") if isinstance(modeb, dict) else None)

    # SDP résiduelle
    put("sdp_residuelle", "fiche_v2", (v2.get("potentiel_transformation") or {}).get("sdp_residuelle_m2"))
    if tile: put("sdp_residuelle", "carte_tuile", tile["sdp_residuelle_m2"])
    put("sdp_residuelle", "db_residuel", resid)

    # vigilances SOFT — CLIENT voit la cascade complète via `lines` (pas le champ partiel `flags`) ;
    # like-for-like avec la tuile (SOFT_FLAG + abf/UNKNOWN, la tuile ne bake QUE ça).
    v2_soft = set()
    for ln in (v2.get("lines") or []):
        n = ln.get("layer") or ln.get("layer_name")
        res = ln.get("result")
        if n and (res == "SOFT_FLAG" or (n == "abf" and res == "UNKNOWN")):
            v2_soft.add(n)
    if v2_soft: put("vigilances", "fiche_v2", ",".join(sorted(v2_soft)))
    if tile and tile["flags"]:
        put("vigilances", "carte_tuile", ",".join(sorted(x for x in str(tile["flags"]).split(",") if x)))

    # étiquette source/millésime (présence)
    put("etiquette_renouv", "fiche_v2", "oui" if (v2.get("renouvellement") or {}).get("source") else None)

    return g, {"statut_mort_v2": v2.get("statut"), "status_mort_tuile": tile["status"] if tile else None,
               "tier_effectif": _tier_effectif_v2(v2)}

def classify(gr, vals):
    """→ (gravite, note). vals = {surface: value}."""
    surfs = list(vals)
    def _hash(v):
        if isinstance(v, float): return round(v, 2)
        if isinstance(v, (dict, list)): return json.dumps(v, ensure_ascii=False, sort_keys=True)
        return v
    uniq = set(_hash(v) for v in vals.values())
    if len(uniq) <= 1:
        return None, ""
    # numériques : distinguer arrondi (G2) de contradiction (G1)
    nums = [v for v in vals.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(nums) == len(vals) and nums:
        lo, hi = min(nums), max(nums)
        rel = (hi - lo) / max(1.0, abs(hi))
        if gr in ("prix_probable", "charge_supportable", "marge_estimee", "bilan_ca") and rel <= 0.01:
            return "G2", f"écart ≤1% (arrondi) {lo}→{hi}"
        if gr == "sdp_residuelle" and hi - lo <= 1:
            return "G2", f"±1 m² arrondi {lo}/{hi}"
        return "G1", f"valeurs contradictoires {vals}"
    if gr == "vigilances":
        return "G3", f"listes différentes {vals}"
    return "G1", f"valeurs différentes {vals}"

def main():
    with open("qa/m48/echantillon.csv") as f:
        sample = list(csv.DictReader(f))
    grid_rows, div_rows, trap_rows = [], [], []
    for s in sample:
        idu = s["idu"]
        g, traps = extract(idu)
        for gr, vals in g.items():
            for surf, val in vals.items():
                grid_rows.append({"idu": idu, "strate": s["strate"], "grandeur": gr,
                                  "surface": surf, "valeur": val})
            grav, note = classify(gr, vals)
            if grav:
                div_rows.append({"idu": idu, "strate": s["strate"], "grandeur": gr,
                                 "gravite": grav, "note": note})
        # piège latent : champ mort statut/status ≠ tier effectif
        te = traps["tier_effectif"]
        if traps["statut_mort_v2"] and te and traps["statut_mort_v2"] != te:
            trap_rows.append({"idu": idu, "champ": "fiche_v2.statut (matrice v1 morte)",
                              "valeur_morte": traps["statut_mort_v2"], "tier_effectif": te})
        if traps["status_mort_tuile"] and te and traps["status_mort_tuile"] != te:
            trap_rows.append({"idu": idu, "champ": "mvt_parcels.status (matrice v1 morte)",
                              "valeur_morte": traps["status_mort_tuile"], "tier_effectif": te})
        print(f"  {idu} {s['strate']}: {sum(1 for gr,vals in g.items() if classify(gr,vals)[0])} divergences")

    def dump(path, rows, cols):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    dump("qa/m48/grille.csv", grid_rows, ["idu", "strate", "grandeur", "surface", "valeur"])
    dump("qa/m48/divergences.csv", div_rows, ["idu", "strate", "grandeur", "gravite", "note"])
    dump("qa/m48/pieges_latents.csv", trap_rows, ["idu", "champ", "valeur_morte", "tier_effectif"])

    from collections import Counter
    byg = Counter(r["gravite"] for r in div_rows)
    print(f"\n=== {len(sample)} parcelles ===")
    print(f"divergences par gravité : {dict(byg)}")
    print(f"pièges latents (champ mort ≠ tier) : {len(trap_rows)}")
    print("grandeurs en divergence :", dict(Counter(r["grandeur"]+':'+r["gravite"] for r in div_rows)))

if __name__ == "__main__":
    main()
