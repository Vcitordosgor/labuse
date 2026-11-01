#!/usr/bin/env python3
"""AUDIT-NU-3-J — la vérité confrontée au monde extérieur, pour 20 parcelles.
Sources : cadastre.gouv (apicarto : contenance, numéro), Géoportail de l'urbanisme
(apicarto GPU : zone), DVF Etalab (dernière vente), Géorisques (risques commune),
BAN (adresse). Un fait qui diffère de la source extérieure = écart de vérité.
Lecture seule ; appels HTTP sortants best-effort."""
import json, os, sys, time, urllib.parse, subprocess
import psycopg
from psycopg.rows import dict_row
PG = "postgresql://openclaw@localhost:5432/labuse"
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")

def jget(url, timeout=25):
    # SSL intercepté dans le bac à sable → curl (certs système) plutôt qu'urllib.
    try:
        p = subprocess.run(["curl","-s","-m",str(timeout),"-A","labuse-audit-nu3j",url],
                           capture_output=True, timeout=timeout+5)
        return json.loads(p.stdout.decode("utf-8","replace"))
    except Exception as e:
        return {"__err__": str(e)}

def parse_idu(idu):
    insee = idu[:5]; rest = idu[5:]
    com_abs = rest[:3]; section = rest[3:-4]; numero = rest[-4:]
    return insee, com_abs, section, numero

# 20 parcelles : réparties sur 20 communes, variété DVF/PPR/zone
def choisir20(sample):
    by_comm = {}
    for r in sample: by_comm.setdefault(r["commune"], []).append(r)
    chosen = []
    # une par commune, en privilégiant une vente DVF récente puis PPR puis bâti
    for comm in sorted(by_comm):
        if len(chosen) >= 20: break
        cand = sorted(by_comm[comm], key=lambda r: (
            0 if r.get("dvf_date") else 1, 0 if r.get("ppr") else 1, 0 if "bati" in r.get("profils",[]) else 1, r["idu"]))
        chosen.append(cand[0])
    return chosen[:20]

def main():
    sample = json.load(open(os.path.join(OUT, "sample120.json")))
    truth = json.load(open(os.path.join(OUT, "truth.json")))
    cible = choisir20(sample)
    with psycopg.connect(PG, row_factory=dict_row) as cx:
        meta = {r["idu"]: r for r in cx.execute(
            "select idu, ST_X(ST_Centroid(geom))::float lon, ST_Y(ST_Centroid(geom))::float lat from parcels where idu = any(%s)",
            ([c["idu"] for c in cible],)).fetchall()}
        adr = {r["idu"]: r["adresse"] for r in cx.execute(
            "select idu, (select concat_ws(' ', numero, voie, code_postal, commune) from adresses a where a.idu=p.idu limit 1) adresse from parcels p where idu=any(%s)",
            ([c["idu"] for c in cible],)).fetchall()}
    res = []
    for c in cible:
        idu = c["idu"]; t = truth.get(idu, {})
        insee, com_abs, section, numero = parse_idu(idu)
        lon = meta.get(idu,{}).get("lon"); lat = meta.get(idu,{}).get("lat")
        row = {"idu": idu, "commune": c["commune"]}
        # 1) cadastre contenance + numero
        cad = jget(f"https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={insee}&section={section}&numero={numero}")
        f = (cad.get("features") or [{}])
        cp = f[0].get("properties", {}) if f else {}
        row["ext_contenance"] = cp.get("contenance")
        row["int_contenance"] = t.get("contenance_m2")
        row["ext_numero"] = cp.get("numero")
        row["ecart_surface"] = (row["ext_contenance"] is not None and row["int_contenance"] is not None
                                and int(row["ext_contenance"]) != int(row["int_contenance"]))
        time.sleep(0.3)
        # 2) GPU zone par point centroïde
        if lon and lat:
            geom = urllib.parse.quote(json.dumps({"type":"Point","coordinates":[lon,lat]}))
            gpu = jget(f"https://apicarto.ign.fr/api/gpu/zone-urba?geom={geom}")
            gf = gpu.get("features") or []
            row["ext_zone"] = (gf[0]["properties"].get("libelle") if gf else None)
            row["ext_zone_type"] = (gf[0]["properties"].get("typezone") if gf else None)
        row["int_zone"] = t.get("zone_lib")
        row["ecart_zone"] = (row.get("ext_zone") and row["int_zone"]
                             and str(row["ext_zone"]).strip().upper() != str(row["int_zone"]).strip().upper())
        time.sleep(0.3)
        # 3) DVF etalab — dernière vente de la parcelle
        dvf = jget(f"https://app.dvf.etalab.gouv.fr/api/mutations3/{insee}/{com_abs}{section}")
        muts = [m for m in (dvf.get("mutations") or []) if m.get("id_parcelle")==idu]
        muts.sort(key=lambda m: m.get("date_mutation",""), reverse=True)
        last = muts[0] if muts else None
        row["ext_vente"] = ({"date":last["date_mutation"],"valeur":last.get("valeur_fonciere"),"nature":last.get("nature_mutation")} if last else None)
        iv = t.get("derniere_vente")
        row["int_vente"] = ({"date":iv["d"],"valeur":iv["val"]} if iv else None)
        row["ecart_vente"] = None
        if last and iv:
            row["ecart_vente"] = (str(last["date_mutation"]) != str(iv["d"]))
        elif bool(last) != bool(iv):
            row["ecart_vente"] = True
        time.sleep(0.3)
        # 4) Géorisques — risques de la commune (sanity : PPR mouvement/inondation présent ?)
        gr = jget(f"https://www.georisques.gouv.fr/api/v1/gaspar/risques?code_insee={insee}&page_size=1")
        dd = (gr.get("data") or [{}])[0] if isinstance(gr.get("data"),list) else {}
        row["ext_risques_commune"] = [x.get("libelle_risque_long") for x in (dd.get("risques_detail") or [])]
        row["int_ppr_rouge_pct"] = t.get("ppr_rouge_pct")
        row["int_aleas"] = list((t.get("aleas_par_risque") or {}).keys())
        time.sleep(0.3)
        # 5) BAN reverse — adresse au centroïde
        if lon and lat:
            ban = jget(f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}")
            bf = ban.get("features") or []
            row["ext_adresse"] = (bf[0]["properties"].get("label") if bf else None)
        row["int_adresse"] = adr.get(idu)
        res.append(row)
        print(f"{idu} {c['commune']:16} surf ext={row['ext_contenance']} int={row['int_contenance']} "
              f"zone ext={row.get('ext_zone')} int={row['int_zone']} vente_ecart={row['ecart_vente']}", flush=True)
    json.dump(res, open(os.path.join(OUT, "external20.json"), "w"), ensure_ascii=False, indent=1)
    ns = sum(1 for r in res if r["ecart_surface"]); nz = sum(1 for r in res if r["ecart_zone"])
    nv = sum(1 for r in res if r["ecart_vente"])
    print(f"\n20 parcelles — écarts surface={ns} zone={nz} vente={nv}")

if __name__ == "__main__":
    main()
