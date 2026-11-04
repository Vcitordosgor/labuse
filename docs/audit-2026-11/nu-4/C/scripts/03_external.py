#!/usr/bin/env python3
"""NU4-C — confrontation aux sources OFFICIELLES en ligne, pour les 500 parcelles.
Sources (API publiques) :
  - cadastre.gouv  : apicarto IGN /cadastre/parcelle    -> contenance (acte)
  - PLU            : apicarto IGN /gpu/zone-urba (point) -> zone opposable (libelle/typezone)
  - servitudes     : apicarto IGN /gpu/assiette-sup-s    -> SUP présentes au point
  - DVF officiel   : app.dvf.etalab /mutations3          -> dernière vente de la parcelle
  - Géorisques     : /api/v1/gaspar/risques (commune)    -> familles de risques déclarées
  - BAN            : api-adresse reverse (centroïde)      -> adresse de référence
Chaque réponse brute est cachée sous out/cache/<source>/<idu>.json : REJOUABLE et RESUMABLE
(relance = ne refait que les trous). Lecture seule, HTTP sortant best-effort via curl (certs système).
"""
import json, os, time, subprocess, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg
from psycopg.rows import dict_row

PG = "postgresql://openclaw@localhost:5432/labuse"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
UA = "labuse-audit-nu4c"

def curl(url, timeout=30):
    p = subprocess.run(["curl", "-s", "-m", str(timeout), "-A", UA, url],
                       capture_output=True, timeout=timeout + 8)
    return p.stdout.decode("utf-8", "replace")

def cached(source, idu, url, timeout=30, retries=3):
    """Récupère url, cache sous cache/source/idu.json. Renvoie l'objet JSON ou {'__err__':...}."""
    d = os.path.join(CACHE, source); os.makedirs(d, exist_ok=True)
    fp = os.path.join(d, idu + ".json")
    if os.path.exists(fp) and os.path.getsize(fp) > 2:
        try:
            obj = json.load(open(fp))
            if not (isinstance(obj, dict) and "__err__" in obj):
                return obj
        except Exception:
            pass
    last = None
    for i in range(retries):
        txt = ""
        try:
            txt = curl(url, timeout)
            obj = json.loads(txt)
            json.dump(obj, open(fp, "w"), ensure_ascii=False)
            return obj
        except Exception as e:
            last = f"{e}: {txt[:120]}"
            time.sleep(0.8 * (i + 1))
    obj = {"__err__": last}
    json.dump(obj, open(fp, "w"), ensure_ascii=False)
    return obj

def parse_idu(idu):
    insee = idu[:5]; rest = idu[5:]
    com_abs = rest[:3]; section = rest[3:-4]; numero = rest[-4:]
    return insee, com_abs, section, numero

def pt(lon, lat):
    return urllib.parse.quote(json.dumps({"type": "Point", "coordinates": [lon, lat]}))

def fetch_one(rec):
    idu = rec["idu"]; lon = rec["lon"]; lat = rec["lat"]
    insee, com_abs, section, numero = parse_idu(idu)
    r = {"idu": idu, "commune": rec["commune"], "insee": insee}

    # 1) cadastre contenance
    cad = cached("cadastre", idu,
        f"https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={insee}&section={section}&numero={numero}")
    feats = cad.get("features") if isinstance(cad, dict) else None
    cp = (feats[0].get("properties", {}) if feats else {})
    r["cad_contenance"] = cp.get("contenance")
    r["cad_numero"] = cp.get("numero")
    r["cad_found"] = bool(feats)
    r["cad_err"] = cad.get("__err__") if isinstance(cad, dict) else None

    # 2) GPU zone au centroïde
    gpu = cached("gpu_zone", idu,
        f"https://apicarto.ign.fr/api/gpu/zone-urba?geom={pt(lon, lat)}")
    gf = gpu.get("features") if isinstance(gpu, dict) else None
    gp = (gf[0].get("properties", {}) if gf else {})
    r["gpu_zone"] = gp.get("libelle")
    r["gpu_typezone"] = gp.get("typezone")
    r["gpu_libelong"] = gp.get("libelong")
    r["gpu_n"] = len(gf or [])
    r["gpu_err"] = gpu.get("__err__") if isinstance(gpu, dict) else None

    # 3) GPU servitudes (SUP) au point
    sup = cached("gpu_sup", idu,
        f"https://apicarto.ign.fr/api/gpu/assiette-sup-s?geom={pt(lon, lat)}")
    sf = sup.get("features") if isinstance(sup, dict) else None
    r["sup_n"] = len(sf or [])
    r["sup_cats"] = sorted({(f.get("properties", {}) or {}).get("categorie")
                            for f in (sf or [])} - {None})

    # 4) DVF etalab
    dvf = cached("dvf", idu,
        f"https://app.dvf.etalab.gouv.fr/api/mutations3/{insee}/{com_abs}{section}")
    muts = [m for m in ((dvf.get("mutations") if isinstance(dvf, dict) else None) or [])
            if m.get("id_parcelle") == idu]
    muts.sort(key=lambda m: m.get("date_mutation", ""), reverse=True)
    last = muts[0] if muts else None
    r["dvf_n"] = len(muts)
    r["dvf_last"] = ({"date": last["date_mutation"], "valeur": last.get("valeur_fonciere"),
                      "nature": last.get("nature_mutation"),
                      "type_local": last.get("type_local")} if last else None)
    r["dvf_err"] = dvf.get("__err__") if isinstance(dvf, dict) else None

    # 5) Géorisques — familles de risques de la commune (une fois / commune, caché par insee)
    gr = cached("georisques", "COMM_" + insee,
        f"https://www.georisques.gouv.fr/api/v1/gaspar/risques?code_insee={insee}&page_size=1")
    dd = {}
    if isinstance(gr, dict) and isinstance(gr.get("data"), list) and gr["data"]:
        dd = gr["data"][0]
    r["geo_familles"] = sorted({x.get("libelle_risque_long")
                                for x in (dd.get("risques_detail") or [])} - {None})

    # 6) BAN reverse au centroïde
    ban = cached("ban", idu,
        f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}")
    bf = ban.get("features") if isinstance(ban, dict) else None
    bp = (bf[0].get("properties", {}) if bf else {})
    r["ban_label"] = bp.get("label")
    r["ban_dist_m"] = bp.get("distance")
    r["ban_type"] = bp.get("type")
    return r

def main():
    sample = json.load(open(os.path.join(OUT, "sample500.json")))
    idus = [s["idu"] for s in sample]
    with psycopg.connect(PG, row_factory=dict_row) as cx:
        meta = {r["idu"]: r for r in cx.execute(
            "select idu, commune, ST_X(ST_Centroid(ST_Transform(geom,4326)))::float lon, "
            "ST_Y(ST_Centroid(ST_Transform(geom,4326)))::float lat "
            "from parcels where idu = any(%s)", (idus,)).fetchall()}
    recs = [meta[i] for i in idus if i in meta]
    out = {}; done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_one, rec): rec["idu"] for rec in recs}
        for f in as_completed(futs):
            idu = futs[f]
            try:
                out[idu] = f.result()
            except Exception as e:
                out[idu] = {"idu": idu, "__fatal__": str(e)}
            done += 1
            if done % 25 == 0:
                print(f"{done}/{len(recs)}", flush=True)
                json.dump(out, open(os.path.join(OUT, "external500.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(OUT, "external500.json"), "w"), ensure_ascii=False, indent=1)
    cad_ok = sum(1 for v in out.values() if v.get("cad_found"))
    gpu_ok = sum(1 for v in out.values() if v.get("gpu_n"))
    print(f"externe : {len(out)} parcelles ; cadastre trouvé {cad_ok} ; GPU zone {gpu_ok} -> external500.json")

if __name__ == "__main__":
    main()
