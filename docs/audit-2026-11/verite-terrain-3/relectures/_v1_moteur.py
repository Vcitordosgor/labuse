"""VT3-relecture volet 1 — rejoue le moteur (lecture seule) sur les parcelles des 21 régressions."""
import json, sys
from pathlib import Path
sys.path.insert(0, "/Users/openclaw/Desktop/labuse-verite3/src")
import labuse.verite_terrain_capacite as vt
from labuse.faisabilite.db import parcel_faisabilite

IDUS = """97402000AD0387 97402000AH1916 97406000AP0422 97408000AC3753 97408000AC3757 97408000AC3429
97408000AN1382 97408000AN1912 97408000AS0457 97408000AS0498 97408000AS0583 97408000AO1919
97408000AB0302 97408000AB0333 97408000AC3538 97408000AC3540 97408000AS0606 97412000BO0496
97412000CT0213 97412000CD0348 97412000CD0857 97412000BK1935 97412000BK1938 97414000CH1873
97414000CH1877 97414000CH1879 97419000AS0725 97419000AL1122 97419000AL1109""".split()

sess = vt._session()
conn = vt._connect()
out = {}
for idu in IDUS:
    with conn.cursor() as cur:
        cur.execute("SELECT id, surface_m2, contenance_m2 FROM parcels WHERE idu=%s", (idu,))
        pid, surf, cont = cur.fetchone()
        cur.execute("SELECT emprise_bati_m2 FROM p_model_bati WHERE idu=%s", (idu,))
        b = cur.fetchone()
    res = parcel_faisabilite(sess, pid)
    d = {"surface_m2": float(surf or 0), "contenance_m2": cont, "bati_m2": float(b[0]) if b else None}
    if res is None:
        d["moteur"] = None
    else:
        ctx, f = res
        d["constructible"] = f.constructible
        d["verdict"] = f.verdict
        d["cause"] = f.cause
        d["exigu_raison"] = f.exigu_raison
        d["zone"] = f.zone
        d["calibree"] = f.calibree
        fr = f.fourchette or {}
        d["fourchette"] = {k: fr.get(k) for k in ("niveaux", "niveaux_max", "hauteur_m",
            "zone_implantation_m2", "emprise_sol_max_m2", "emprise_constructible_m2",
            "emprise_batie_max_m2", "surface_plancher_m2", "logements_au_sol", "assiette_source")}
        d["steps"] = [{"label": s.label, "formule": s.formule, "valeur": s.valeur, "source": s.source}
                      for s in (f.steps or [])]
        d["hypotheses"] = f.hypotheses
        d["avertissements"] = f.avertissements
    out[idu] = d
    print(idu, d.get("verdict", "∅"), flush=True)
Path("/Users/openclaw/Desktop/labuse-verite3/docs/audit-2026-11/verite-terrain-3/relectures/_v1_moteur.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1))
print("OK", len(out))
