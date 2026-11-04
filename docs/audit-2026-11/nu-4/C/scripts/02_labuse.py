#!/usr/bin/env python3
"""NU4-C — « ce que LABUSE affiche » : relevé des faits de la FICHE SERVIE, par l'API réelle
(GET /parcels/{idu}?source=q_v20), pour les 500 parcelles. C'est le point d'entrée que le front
appelle (api.ts getFiche) — donc le texte réellement montré au client, pas une relecture SQL.
Résumé par idu dans out/labuse.json ; les fiches brutes sont cachées sous out/cache/fiche/.
Lecture seule."""
import json, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "http://127.0.0.1:9650"
RUN = "q_v20"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
FCACHE = os.path.join(OUT, "cache", "fiche")

def get(idu):
    fp = os.path.join(FCACHE, idu + ".json")
    if os.path.exists(fp) and os.path.getsize(fp) > 50:
        return json.load(open(fp))
    url = f"{API}/parcels/{idu}?source={RUN}"
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                d = json.loads(r.read().decode("utf-8"))
            json.dump(d, open(fp, "w"), ensure_ascii=False)
            return d
        except Exception as e:
            err = str(e); time.sleep(1.0)
    return {"__err__": err}

def pick(d, path, default=None):
    o = d
    for k in path.split("."):
        if isinstance(o, dict): o = o.get(k)
        else: return default
    return o if o is not None else default

def resume(idu, d):
    if "__err__" in d:
        return {"idu": idu, "err": d["__err__"]}
    zones = pick(d, "reglement_plu.zones", []) or []
    # zone dominante = plus grande part
    zmaj = None
    if zones:
        zmaj = sorted(zones, key=lambda z: -(z.get("part") or 0))[0]
    dm = pick(d, "dvf_parcelle.derniere_mutation")
    aleas = pick(d, "aleas.liste", []) or []
    copros = pick(d, "coproprietes", []) or []
    return {
        "idu": idu,
        "commune": pick(d, "commune"),
        "adresse": pick(d, "adresse"),
        # surfaces
        "contenance_m2": pick(d, "contenance_m2"),
        "surface_terrain_m2": pick(d, "surface_terrain_m2"),
        "surface_dessin_m2": pick(d, "surface_dessin_m2"),
        "surface_m2": pick(d, "surface_m2"),
        "surface_source": pick(d, "surface_source"),
        # zone PLU
        "zone": (zmaj or {}).get("zone"),
        "zone_part": (zmaj or {}).get("part"),
        "zones_all": [z.get("zone") for z in zones],
        "zone_famille": pick(d, "reglement_plu.zone_famille"),
        # bâti
        "nb_batiments": pick(d, "le_bien.nb_batiments"),
        "emprise_batie_m2": pick(d, "le_bien.emprise_batie_m2"),
        "hauteur_bati_m": pick(d, "le_bien.hauteur_bati_m"),
        "source_bati": pick(d, "le_bien.source_bati"),
        # dernière vente DVF
        "dvf_derniere": dm,
        # copro
        "copro_flag": pick(d, "score_v2.copro"),
        "n_coproprietes": len(copros),
        "coproprietes": copros[:3],
        # aléas / PPR
        "aleas_n": pick(d, "aleas.n"),
        "aleas_natures": [a.get("nature") for a in aleas],
        "aleas_liste": aleas,
        # scot
        "scot_nom": pick(d, "scot.nom"),
        "scot_statut": pick(d, "scot.statut"),
        # prix
        "prix_median": pick(d, "prix_ancien.median"),
        "prix_type": pick(d, "prix_ancien.type_prix"),
        "prix_fiabilite": pick(d, "prix_ancien.fiabilite"),
    }

def main():
    os.makedirs(FCACHE, exist_ok=True)
    sample = json.load(open(os.path.join(OUT, "sample500.json")))
    idus = [r["idu"] for r in sample]
    out = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(get, idu): idu for idu in idus}
        for f in as_completed(futs):
            idu = futs[f]
            out[idu] = resume(idu, f.result())
            done += 1
            if done % 50 == 0: print(f"{done}/{len(idus)}", flush=True)
    json.dump(out, open(os.path.join(OUT, "labuse.json"), "w"), ensure_ascii=False, indent=1)
    errs = sum(1 for v in out.values() if "err" in v)
    print(f"relevé LABUSE : {len(out)} fiches, {errs} erreurs -> labuse.json")

if __name__ == "__main__":
    main()
