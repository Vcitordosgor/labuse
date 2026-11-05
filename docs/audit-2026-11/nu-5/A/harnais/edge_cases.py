#!/usr/bin/env python
"""NU5-A — cas-limites de saisie (LECTURE SEULE).

Teste chaque champ de saisie libre des outils avec : vide, zéro, négatif, très grand,
décimale (virgule/point), texte dans un champ numérique. On vérifie que l'outil :
 - ne plante pas (pas de 500 non géré),
 - dit clairement quand il ne peut pas répondre,
 - ne renvoie pas un chiffre absurde présenté comme crédible.

Cible principale : Calculette foncière (POST /modules/faisabilite/{idu}/charge),
Taxe d'aménagement (GET /outils/taxe-amenagement), Prospection solaire (filtres),
Assemblage (idus), Comparer (idus), Estimer (url), Étude de zone (rayon).

Produit : preuves/edge.json
"""
from __future__ import annotations
import os, json
import urllib.request, urllib.error, urllib.parse

BASE = os.environ.get("BASE", "http://127.0.0.1:9730")
OUT = "docs/audit-2026-11/nu-5/A/preuves"
IDU = os.environ.get("IDU_EDGE", "97416000EI1048")  # une parcelle U constructible saine

def _req(method, path, body=None, raw_body=None):
    url = BASE + path
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body.encode(); headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            t = r.read().decode()
            try: return {"status": r.status, "json": json.loads(t)}
            except Exception: return {"status": r.status, "text": t[:300]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:300]}
    except Exception as e:
        return {"status": "EXC", "error": str(e)[:300]}

def GET(path, **q):
    if q: path += "?" + urllib.parse.urlencode({k:v for k,v in q.items() if v is not None})
    return _req("GET", path)
def POST(path, body=None, raw_body=None): return _req("POST", path, body, raw_body)

def calc_resume(r):
    """Extrait l'essentiel d'une réponse calculette pour juger l'absurde."""
    if r.get("status") != 200: return {"status": r["status"], "err": r.get("error","")[:120]}
    j = r.get("json", {})
    cf = (j.get("charge_fonciere") or {})
    return {"status": 200, "calculable": j.get("calculable"),
            "charge_central": cf.get("central"), "par_m2": cf.get("par_m2_terrain"),
            "inputs": j.get("inputs"), "note": (j.get("note") or j.get("message"))}

def main():
    E = {}

    # ── Calculette foncière : champs cout_construction_m2, marge_frais_pct, vrd_m2, prix_demande_eur
    ch = f"/modules/faisabilite/{IDU}/charge"
    E["calculette"] = {
        "nominal":        calc_resume(POST(ch, {"cout_construction_m2": 1800, "marge_frais_pct": 25})),
        "vide":           calc_resume(POST(ch, {})),
        "cout_zero":      calc_resume(POST(ch, {"cout_construction_m2": 0, "marge_frais_pct": 25})),
        "cout_negatif":   calc_resume(POST(ch, {"cout_construction_m2": -1800, "marge_frais_pct": 25})),
        "cout_enorme":    calc_resume(POST(ch, {"cout_construction_m2": 1e12, "marge_frais_pct": 25})),
        "marge_negative": calc_resume(POST(ch, {"cout_construction_m2": 1800, "marge_frais_pct": -50})),
        "marge_sup_100":  calc_resume(POST(ch, {"cout_construction_m2": 1800, "marge_frais_pct": 500})),
        "prix_negatif":   calc_resume(POST(ch, {"cout_construction_m2": 1800, "marge_frais_pct": 25, "prix_demande_eur": -100000})),
        "decimale_virgule": {"status": POST(ch, raw_body='{"cout_construction_m2": "1800,50", "marge_frais_pct": 25}').get("status"),
                             "note": "virgule décimale dans un champ numérique JSON"},
        "texte_dans_num": {"status": POST(ch, raw_body='{"cout_construction_m2": "abc", "marge_frais_pct": 25}').get("status")},
    }

    # ── Taxe d'aménagement : surface_taxable_m2 (float ouvert) + taux
    tx = "/outils/taxe-amenagement"
    def tx_resume(r):
        if r.get("status")!=200: return {"status": r["status"], "err": r.get("error","")[:120]}
        j=r["json"]; return {"status":200, "total_eur": j.get("total_eur"),
                             "assiette_m2": j.get("assiette_m2"), "part_comm": j.get("part_communale_eur")}
    E["taxe"] = {
        "nominal":   tx_resume(GET(tx, surface_taxable_m2=100, insee="97416")),
        "zero":      tx_resume(GET(tx, surface_taxable_m2=0, insee="97416")),
        "negatif":   tx_resume(GET(tx, surface_taxable_m2=-100, insee="97416")),
        "enorme":    tx_resume(GET(tx, surface_taxable_m2=1e9, insee="97416")),
        "decimale":  tx_resume(GET(tx, surface_taxable_m2=100.5, insee="97416")),
        "vide":      {"status": GET(tx, insee="97416").get("status")},
        "taux_negatif": tx_resume(GET(tx, surface_taxable_m2=100, taux_communal_pct=-5)),
        "taux_enorme":  tx_resume(GET(tx, surface_taxable_m2=100, taux_communal_pct=9999)),
    }

    # ── Prospection solaire : filtres numériques
    ps = "/modules/prospection-solaire"
    def ps_resume(r):
        if r.get("status")!=200: return {"status": r["status"], "err": r.get("error","")[:120]}
        j=r["json"]; return {"status":200, "n": j.get("n"), "total": j.get("total")}
    E["solaire"] = {
        "nominal":        ps_resume(GET(ps, commune="Saint-Pierre")),
        "potentiel_negatif": ps_resume(GET(ps, commune="Saint-Pierre", potentiel_min=-100)),
        "potentiel_enorme":  ps_resume(GET(ps, commune="Saint-Pierre", potentiel_min=10_000_000)),
        "proba_sup_100":  ps_resume(GET(ps, commune="Saint-Pierre", proba_occ_min=500)),
        "piscine_surf_negatif": ps_resume(GET(ps, commune="Saint-Pierre", piscine_surf_min=-5)),
        "commune_bidon":  ps_resume(GET(ps, commune="Zzz-Inexistante")),
    }

    # ── Assemblage : idus (contiguïté)
    E["assemblage"] = {
        "vide":        POST("/moteurs/assemblage", {"idus": []}),
        "une_seule":   POST("/moteurs/assemblage", {"idus": [IDU]}),
        "idu_bidon":   POST("/moteurs/assemblage", {"idus": [IDU, "00000000ZZ9999"]}),
        # deux parcelles NON contiguës (communes différentes) -> doit refuser/flaguer isolées
        "non_contigu": POST("/moteurs/assemblage", {"idus": ["97416000EI1048", "97411000AY0015"]}),
    }

    # ── Comparer : idus invalides
    E["comparer"] = {
        "un_bidon":    GET("/compare", idus="00000000ZZ9999"),
        "mix":         GET("/compare", idus=f"{IDU},00000000ZZ9999"),
        "vide":        GET("/compare", idus=""),
        "quatre":      GET("/compare", idus=f"{IDU},{IDU},{IDU},{IDU}"),
    }

    # ── Estimer un bien : url
    E["estimer"] = {
        "url_vide":    POST("/radar/annonce/analyser", {"url": ""}),
        "url_hors_lbc": POST("/radar/annonce/analyser", {"url": "https://evil.example.com/x"}),
        "url_texte":   POST("/radar/annonce/analyser", {"url": "pas une url"}),
    }

    # ── Étude de zone : rayon hors liste / négatif
    ez = "/outils/etude-zone"
    def ez_resume(r):
        if r.get("status")!=200: return {"status": r["status"], "err": r.get("error","")[:120]}
        j=r["json"]; return {"status":200, "zone_disponible": j.get("zone_disponible"), "rayon_km": j.get("rayon_km")}
    E["etude_zone"] = {
        "rayon_hors_liste": ez_resume(POST(ez, {"idu": IDU, "rayon_km": 999})),
        "rayon_negatif":    ez_resume(POST(ez, {"idu": IDU, "rayon_km": -1})),
        "rayon_zero":       ez_resume(POST(ez, {"idu": IDU, "rayon_km": 0})),
        "idu_bidon":        ez_resume(POST(ez, {"idu": "00000000ZZ9999", "rayon_km": 1})),
    }

    with open(f"{OUT}/edge.json", "w") as f:
        json.dump(E, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(E, ensure_ascii=False, indent=1, default=str))

if __name__ == "__main__":
    main()
