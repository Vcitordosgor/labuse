#!/usr/bin/env python
"""NU5-A — harnais outil × parcelle (LECTURE SEULE).

Pour chaque parcelle-piège et chaque outil du menu Outils, on appelle l'endpoint HTTP
RÉEL servi par le backend local (port 9730, auth désactivée en env=local), on enregistre
le statut, les chiffres clés, et on les confronte à la FICHE (`GET /parcels/{idu}`).

Produit : preuves/resultats.json  (brut appel par appel)
          preuves/matrice.csv      (outil × parcelle : vert/orange/rouge + note)

Les 20 idus et leur commune/siren de contexte sont figés dans PARCELLES (issus de
select_parcelles.py). Les cas-limites de saisie (champs vides/zéro/négatif/très grand/
virgule) sont dans une passe séparée (edge_cases.py).

Usage : BASE=http://127.0.0.1:9730 PYTHONPATH=src \
        /Users/openclaw/Desktop/labuse/.venv/bin/python harness.py
"""
from __future__ import annotations
import os, json, time
import urllib.request, urllib.error, urllib.parse

BASE = os.environ.get("BASE", "http://127.0.0.1:9730")
OUT = "docs/audit-2026-11/nu-5/A/preuves"

# ── Les 20 parcelles-pièges (figées depuis select_parcelles.py) ───────────────────────
# chaque entrée : clé-piège -> {idu, commune, note}. (siren de contexte rempli au runtime
# depuis la fiche quand l'outil en a besoin.)
PARCELLES: dict[str, dict] = {}  # rempli par load_choix()

def load_choix():
    with open(f"{OUT}/choix.json") as f:
        return json.load(f)

# ── HTTP helpers ──────────────────────────────────────────────────────────────────────
def _req(method, path, body=None, timeout=90):
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            dt = round(time.time() - t0, 2)
            try:
                return {"status": r.status, "ms": dt, "json": json.loads(raw)}
            except Exception:
                return {"status": r.status, "ms": dt, "text": raw[:500]}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:500]
        return {"status": e.code, "ms": round(time.time()-t0,2), "error": raw}
    except Exception as e:
        return {"status": "EXC", "ms": round(time.time()-t0,2), "error": str(e)[:300]}

def GET(path, **q):
    if q:
        path += "?" + urllib.parse.urlencode({k: v for k, v in q.items() if v is not None})
    return _req("GET", path)

def POST(path, body):
    return _req("POST", path, body)

# ── Fiche : référence de cohérence ──────────────────────────────────────────────────────
def fiche_ref(idu):
    r = GET(f"/parcels/{idu}")
    if r.get("status") != 200:
        return {"_erreur_fiche": r}
    d = r["json"]
    pot = d.get("potentiel_a_batir") or {}
    zones = (d.get("reglement_plu") or {}).get("zones") or []
    aleas = (d.get("aleas") or {}).get("liste") or []
    pm = d.get("proprietaire_moral") or {}
    tx = d.get("taxe_amenagement") or {}
    terr = d.get("terrain") or {}
    return {
        "surface_terrain_m2": d.get("surface_terrain_m2"),
        "surface_dessin_m2": d.get("surface_dessin_m2"),
        "contenance_m2": d.get("contenance_m2"),
        "etat_bien": d.get("etat_bien"),
        "zone_lib": pot.get("zone_lib") or (zones[0].get("zone") if zones else None),
        "zone_fam": pot.get("zone_fam"),
        "constructible": pot.get("constructible"),
        "rien_a_batir": pot.get("rien_a_batir"),
        "sdp_restante_m2": pot.get("sdp_restante_m2"),
        "aleas": [{"nature": a.get("nature"), "niveau": a.get("niveau"),
                   "part_pct": a.get("part_pct"), "redhibitoire": a.get("redhibitoire")} for a in aleas],
        "pm_denomination": pm.get("denomination"), "pm_siren": pm.get("siren"),
        "taux_communal_pct": tx.get("taux_communal_pct"),
        "pente_moy_deg": terr.get("pente_moy_deg"),
        "coproprietes_n": len(d.get("coproprietes") or []),
        "prix_ancien_median": (d.get("prix_ancien") or {}).get("median"),
        "prix_ancien_fiable": (d.get("prix_ancien") or {}).get("fiable"),
    }

# ── Appels outil par parcelle ────────────────────────────────────────────────────────────
def appels_parcelle(idu, commune, siren):
    """Tous les outils qui prennent une parcelle (ou son contexte commune/siren)."""
    a = {}
    a["risques"]          = GET(f"/servitudes-invisibles/{idu}")
    a["gabarit"]          = GET(f"/outils/gabarit/{idu}")
    a["taxe_prefill"]     = GET(f"/outils/taxe-amenagement/prefill", idu=idu)
    a["estimation"]       = GET(f"/radar/annonce/estimation/{idu}")
    a["solaire_parcelle"] = GET(f"/modules/prospection-solaire/parcelle/{idu}")
    a["temps_epoque"]     = GET(f"/moteurs/parcellaire-epoque/{idu}")
    a["parcelle_permis"]  = GET(f"/modules/parcelle-permis", idu=idu)
    a["comparer"]         = GET(f"/compare", idus=idu)
    a["etude_zone"]       = POST("/outils/etude-zone", {"idu": idu, "rayon_km": 1})
    a["assemblage_seule"] = POST("/moteurs/assemblage", {"idus": [idu]})
    a["calculette"]       = POST(f"/modules/faisabilite/{idu}/charge",
                                 {"cout_construction_m2": 1800, "marge_frais_pct": 25})
    # portefeuille / commune
    a["communes_acq"]     = GET(f"/communes/{urllib.parse.quote(commune)}/acquisitions-pm", limit=50) if commune else {"skip": "no commune"}
    if siren:
        a["patrimoine"]   = GET("/modules/patrimoine", siren=siren)
    else:
        a["patrimoine"]   = {"skip": "pas de personne morale (particulier/inconnu)"}
    return a

def main():
    choix = load_choix()
    only = [x for x in os.environ.get("ONLY", "").split(",") if x]
    res = {"base": BASE, "parcelles": {}}
    if only and os.path.exists(f"{OUT}/resultats.json"):   # mode fusion : on repart de l'existant
        res = json.load(open(f"{OUT}/resultats.json"))
    for piege, meta in choix.items():
        if only and piege not in only:
            continue
        idu = meta["idu"]; commune = meta.get("commune")
        print(f"[{piege}] {idu} ({commune})", flush=True)
        ref = fiche_ref(idu)
        siren = ref.get("pm_siren")
        calls = appels_parcelle(idu, commune, siren)
        res["parcelles"][piege] = {"idu": idu, "commune": commune, "fiche": ref, "outils": calls}
    with open(f"{OUT}/resultats.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print("-> resultats.json écrit", flush=True)

if __name__ == "__main__":
    main()
