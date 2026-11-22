#!/usr/bin/env python3
"""MISE-EN-LIGNE-7 LOT 2 — CONTRÔLE INDÉPENDANT des prescriptions PLU (GPU vs base servie).

N'importe RIEN du code d'ingestion de LABUSE : il télécharge lui-même le document GPU d'une
commune (API Carto, par partition), lit ce que la base SERT (psql, lecture seule), et compare
PAR TYPE (geom_kind × typepsc) en DIFFÉRENCE SYMÉTRIQUE D'AIRE — ajouts ET retraits. C'est ce
contrôle qui fait foi pour toutes les preuves du mandat.

Verdict par commune : « identique » (aucun objet surfacique significatif ajouté/retiré, aucun
déplacement lin/pct) ou « DIFFÉRENT », avec les surfaces. Les parcelles touchées sont comptées
par composante significative (découpage — jamais une estimation ; pas d'effleurement de bord).

Usage :
  scripts/controle_prescriptions_gpu.py <INSEE> "<Commune>"          # une commune, détail + JSON
  scripts/controle_prescriptions_gpu.py --json <INSEE> "<Commune>"   # JSON seul (pour le LOT 3)
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse

from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import unary_union

APICARTO = "https://apicarto.ign.fr/api/gpu"
ENDPOINTS = {"surf": "prescription-surf", "lin": "prescription-lin", "pct": "prescription-pct"}
# conversion deg²→m² au voisinage de La Réunion (lat ~-21) : 1° lat ≈ 111 km, 1° lon ≈ 103,6 km
K = 111_000 * 103_600
SEUIL_SURF_M2 = 50.0      # une composante d'aire < 50 m² = sliver de bord, ignorée
SEUIL_DEPL_PCT = 2.0      # lin/pct : déplacement relatif < 2 % = bruit
LABELS = {"01": "EBC", "05": "ER", "02": "secteur conditionné"}


def _curl(url: str) -> dict:
    out = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else {"features": []}


def gpu_document(insee: str, kind: str) -> list[dict]:
    """Features du document EN VIGUEUR de la commune (partition DU_<insee>), paginées, sans voisin."""
    part = f"DU_{insee}"
    feats, start = [], 0
    while True:
        q = urllib.parse.urlencode({"partition": part, "_start": start, "_limit": 1000})
        page = _curl(f"{APICARTO}/{ENDPOINTS[kind]}?{q}").get("features", []) or []
        feats += [f for f in page if (f.get("properties") or {}).get("partition") == part]
        if len(page) < 1000:
            break
        start += len(page)
    return feats


def _psql(sql: str, sep: str = "\x1f") -> list[list[str]]:
    import os
    # statement_timeout par PGOPTIONS (et pas un `-c SET …` qui émettrait une ligne « SET »
    # parasite, prise à tort pour une donnée).
    env = {**os.environ, "PGOPTIONS": "-c statement_timeout=170000"}
    # SQL par STDIN (les WKT de prescriptions dépassent la limite d'argument de la ligne de commande).
    out = subprocess.run(["psql", "-d", "labuse", "-At", "-F", sep], input=sql,
                         capture_output=True, text=True, env=env)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300])
    return [line.split(sep) for line in out.stdout.splitlines() if line.strip()]


def servi_idurba(insee: str, commune: str) -> str | None:
    """L'idurba du DOCUMENT PROPRE de la commune servi en base (exclut les débordements voisins)."""
    rows = _psql("SELECT DISTINCT attrs->>'idurba' FROM spatial_layers WHERE kind='plu_gpu_prescription' "
                 f"AND commune='{commune}' AND attrs->>'idurba' LIKE '{insee}\\_%'")
    cands = [r[0] for r in rows if r and r[0]]
    return sorted(cands)[-1] if cands else None


def servi_geoms(commune: str, kind: str, idurba: str) -> list[tuple[str, object]]:
    rows = _psql(
        "SELECT coalesce(attrs->>'typepsc',''), ST_AsGeoJSON(ST_Transform(geom,4326),7) "
        f"FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='{commune}' "
        f"AND attrs->>'geom_kind'='{kind}' AND attrs->>'idurba'='{idurba}'")
    return [(r[0], make_valid(shape(json.loads(r[1])))) for r in rows if len(r) == 2 and r[1]]


def _sig_components(geom):
    if geom is None or geom.is_empty:
        return []
    parts = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
    return [c for c in parts if (c.area * K > SEUIL_SURF_M2 if "Polygon" in c.geom_type else True)]


def _parcelles_dune_tuile(insee: str, wkt: str) -> list[list[str]]:
    """Intersection parcelles × géométrie (déjà simplifiée/petite) ; mesure l'aire d'intersection
    en 2975. Rend [(idu, m2, pct)]. Peut lever (timeout) → l'appelant découpe en grille."""
    return _psql(
        "SELECT p.idu, round(a::numeric) m2, round((100*a/nullif(parc,0))::numeric,1) pct FROM ("
        "  SELECT p.idu, "
        "    ST_Area(ST_Transform(ST_Intersection(ST_MakeValid(ST_Transform(p.geom,4326)),"
        f"      ST_MakeValid(ST_GeomFromText('{wkt}',4326))),2975)) a, "
        "    ST_Area(ST_Transform(p.geom,2975)) parc "
        f"  FROM parcels p WHERE left(p.idu,5)='{insee}' "
        f"    AND ST_Intersects(ST_Transform(p.geom,4326), ST_MakeValid(ST_GeomFromText('{wkt}',4326)))"
        ") p WHERE a > 50")


def _parcelles_touchees(insee: str, comp_geoms: list) -> dict:
    """Découpage : une requête par COMPOSANTE significative, idus dédupliqués. Jamais d'estimation.
    Robustesse (mandat) : la géométrie est simplifiée à ~1 m (tol 1e-5°) pour alléger l'intersection ;
    si une composante dépasse quand même le délai, on la DÉCOUPE en grille 4×4 et on somme."""
    from shapely import simplify
    from shapely.geometry import box
    sig50, sig5 = {}, {}

    def _ajouter(rows):
        for r in rows:
            idu, m2, pct = r[0], float(r[1]), float(r[2] or 0)
            sig50[idu] = max(sig50.get(idu, 0), m2)
            if pct > 5.0:
                sig5[idu] = max(sig5.get(idu, 0), pct)

    for g0 in comp_geoms:
        g = make_valid(simplify(g0, 1e-5))
        if g.is_empty:
            continue
        try:
            _ajouter(_parcelles_dune_tuile(insee, g.wkt))
        except RuntimeError:                       # timeout → découpe en grille 4×4
            minx, miny, maxx, maxy = g.bounds
            nx = ny = 4
            dx, dy = (maxx - minx) / nx, (maxy - miny) / ny
            for i in range(nx):
                for j in range(ny):
                    tuile = g.intersection(box(minx + i * dx, miny + j * dy,
                                               minx + (i + 1) * dx, miny + (j + 1) * dy))
                    if tuile.is_empty:
                        continue
                    _ajouter(_parcelles_dune_tuile(insee, make_valid(tuile).wkt))
    return {"sig50": sig50, "sig5pct": sig5}


def controler(insee: str, commune: str) -> dict:
    own = servi_idurba(insee, commune)
    res = {"insee": insee, "commune": commune, "idurba_servi": own, "par_type": {}, "parcelles": {}}
    if own is None:
        res["verdict"] = "SANS DOCUMENT SERVI"
        return res
    diff_surf_by_type: dict[str, list] = {}
    different = False
    for kind in ENDPOINTS:
        gpu = gpu_document(insee, kind)
        srv = servi_geoms(commune, kind, own)
        types = sorted({(f.get("properties") or {}).get("typepsc") or "" for f in gpu} | {t for t, _ in srv})
        for tp in types:
            gg = [make_valid(shape(f["geometry"])) for f in gpu
                  if (f.get("properties") or {}).get("typepsc") == tp and f.get("geometry")]
            sg = [g for t, g in srv if t == tp]
            ug = unary_union(gg) if gg else None
            us = unary_union(sg) if sg else None
            if kind == "surf":
                add = ug.difference(us) if (ug and us) else ug
                rem = us.difference(ug) if (ug and us) else us
                ca, cr = _sig_components(add), _sig_components(rem)
                aa = sum(c.area * K for c in ca)
                ar = sum(c.area * K for c in cr)
                if ca or cr:
                    different = True
                    res["par_type"][f"surf/{tp}"] = {"ajoute_m2": round(aa), "retire_m2": round(ar),
                                                      "n_ajout": len(ca), "n_retrait": len(cr)}
                    diff_surf_by_type[tp] = ca + cr
            else:
                b = 1.8e-5
                bg = unary_union([x.buffer(b) for x in gg]) if gg else None
                bs = unary_union([x.buffer(b) for x in sg]) if sg else None
                sym = (bg.symmetric_difference(bs).area if (bg and bs)
                       else max(bg.area if bg else 0, bs.area if bs else 0))
                base = max(bg.area if bg else 0, bs.area if bs else 0, 1e-12)
                pct = 100 * sym / base
                if pct > SEUIL_DEPL_PCT:
                    different = True
                    res["par_type"][f"{kind}/{tp}"] = {"deplacement_pct": round(pct, 1)}
    # parcelles touchées — par type surf qui a changé, avec découpage par composante
    for tp, comps in diff_surf_by_type.items():
        t = _parcelles_touchees(insee, comps)
        res["parcelles"][LABELS.get(tp, f"type {tp}")] = {
            "sig50_n": len(t["sig50"]), "sig5pct_n": len(t["sig5pct"]),
            "sig5pct_idus": sorted(t["sig5pct"])}
    res["verdict"] = "DIFFÉRENT" if different else "identique"
    return res


def main():
    args = sys.argv[1:]
    json_only = False
    if args and args[0] == "--json":
        json_only = True
        args = args[1:]
    insee, commune = args[0], args[1]
    r = controler(insee, commune)
    if json_only:
        print(json.dumps(r, ensure_ascii=False))
        return
    print(f"=== {commune} ({insee}) — document servi {r['idurba_servi']} ===")
    print(f"VERDICT : {r['verdict']}")
    for k, v in r["par_type"].items():
        print(f"  {k}: {v}")
    for lbl, v in r["parcelles"].items():
        print(f"  parcelles {lbl} : >50 m² = {v['sig50_n']} · >5% = {v['sig5pct_n']} {v['sig5pct_idus'][:10]}")


if __name__ == "__main__":
    main()
