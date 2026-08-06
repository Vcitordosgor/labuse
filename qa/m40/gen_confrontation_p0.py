"""M40 P0 — digest de confrontation GPU (spatial_layers) vs mairie (plu_millesimes.yaml).

Constate SUR PIÈCES, par commune : l'idurba mairie (config) vs l'idurba réellement ingéré au GPU
(spatial_layers), le statut config, le match, et les têtes servies. Lecture seule.

Usage : PYTHONPATH=src python qa/m40/gen_confrontation_p0.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse import config as _cfg  # noqa: E402
from labuse.db import engine  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "confrontation_gpu_mairie_p0.csv")


def main() -> None:
    communes = (_cfg.load_yaml_config("plu_millesimes") or {}).get("communes", {})
    with engine().connect() as c:
        gpu = {}
        for r in c.execute(text(
            "SELECT left(attrs->>'idurba',5) insee, string_agg(DISTINCT attrs->>'idurba', ' | ' ORDER BY attrs->>'idurba') idus, "
            "count(*) zones FROM spatial_layers WHERE kind='plu_gpu_zone' GROUP BY 1")).mappings():
            gpu[r["insee"]] = (r["idus"], r["zones"])
        heads = {}
        for r in c.execute(text(
            "SELECT substring(parcelle_id,1,5) insee, "
            "count(*) FILTER (WHERE tier IN ('brulante','chaude')) tetes, "
            "count(*) FILTER (WHERE tier='reserve_fonciere') reserve, count(*) servi "
            "FROM parcel_p_score_v2 WHERE run_id='q_v8_calibre' GROUP BY 1")).mappings():
            heads[r["insee"]] = (r["tetes"], r["reserve"], r["servi"])
    rows = []
    for insee in sorted(communes):
        cfg = communes[insee]
        gidus, gzones = gpu.get(insee, ("(aucune)", 0))
        cidu = cfg.get("idurba") or "(aucun)"
        # match : l'idurba mairie apparaît-il tel quel dans le GPU (insensible à la casse PLU/plu) ?
        gset = [x.strip().lower() for x in (gidus or "").split("|")]
        match = "OUI" if cidu != "(aucun)" and cidu.lower() in gset else (
            "RNU" if cfg.get("statut") == "rnu" else "NON/AUTRE")
        residu = "OUI" if len([x for x in gset if x and x != "(aucune)"]) > 1 else ""
        t, res, servi = heads.get(insee, (0, 0, 0))
        rows.append({
            "insee": insee, "commune": cfg.get("commune"), "statut_config": cfg.get("statut"),
            "idurba_mairie": cidu, "date_mairie": cfg.get("date_mairie"),
            "idurba_gpu_ingere": gidus, "gpu_zones": gzones, "match_doc": match,
            "residu_multi_idurba": residu, "tetes_brul_chaude": t, "reserve": res, "servi": servi,
            "note_config": (cfg.get("note") or "")[:80]})
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n_match = sum(1 for r in rows if r["match_doc"] == "OUI")
    n_rnu = sum(1 for r in rows if r["match_doc"] == "RNU")
    n_autre = sum(1 for r in rows if r["match_doc"] == "NON/AUTRE")
    n_residu = sum(1 for r in rows if r["residu_multi_idurba"])
    print(f"✓ {OUT} — {len(rows)} communes : {n_match} idurba GPU=mairie · {n_rnu} RNU · "
          f"{n_autre} non/autre · {n_residu} avec résidu multi-idurba")


if __name__ == "__main__":
    main()
