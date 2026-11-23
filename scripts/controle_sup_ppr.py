#!/usr/bin/env python
"""MISE-EN-LIGNE-8 LOT 2 — contrôle indépendant PPR + SUP (servitudes), LECTURE SEULE.

Même esprit que le contrôle des prescriptions : la base (Mac) est comparée à la SOURCE OFFICIELLE
(API Carto GPU `assiette-sup-s`, téléchargée ICI, sans réutiliser le code d'ingestion). Les deux
ingestions concernées requêtent par BBOX (`ingest_ppr_sup` → kind='ppr' PM1 ; `sup_gpu` → kind='sup',
subtype=suptype) ; on vérifie que le débordement de bbox n'a pas ajouté/retiré de servitude.

Contrairement au PLU, les SUP ne sont PAS partitionnées par commune (une assiette couvre plusieurs
communes). Le téléchargement officiel se fait donc par la BBOX de la commune, puis la comparaison
PAR TYPE (suptype) se mesure LÀ OÙ ELLE COMPTE : les PARCELLES de CETTE commune touchées par la
différence (>50 m² et/ou >5 %). Le débordement voisin (assiette hors commune) tombe sur des parcelles
d'un AUTRE insee → `left(idu,5)=insee` l'écarte naturellement. La surface de différence rapportée est
donc celle qui RETOMBE SUR LES PARCELLES de la commune (métrique per-commune, pas de frontière requise).

NE CORRIGE RIEN. Usage :
  python scripts/controle_sup_ppr.py <insee> <commune>
  python scripts/controle_sup_ppr.py --json <insee> <commune>
"""
import json
import signal
import sys
import urllib.parse

from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid

# réutilise les briques ROBUSTES du contrôle prescriptions (jamais le code d'ingestion)
from controle_prescriptions_gpu import (  # type: ignore
    K, SEUIL_SURF_M2, _curl, _psql, _parcelles_touchees, _sig_components)

APICARTO = "https://apicarto.ign.fr/api/gpu"


def _commune_bbox(insee: str):
    """BBox 4326 (minx,miny,maxx,maxy) de l'emprise cadastrale de la commune (sert de geom apicarto)."""
    rows = _psql(f"SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
                 f"(SELECT ST_Extent(ST_Transform(geom,4326)) e FROM parcels WHERE left(idu,5)='{insee}') q")
    if not rows or not rows[0][0]:
        return None
    return tuple(float(x) for x in rows[0])


def _bbox_poly(b) -> dict:
    minx, miny, maxx, maxy = b
    return {"type": "Polygon", "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy],
                                                [minx, maxy], [minx, miny]]]}


def sup_officiel(bbox) -> dict:
    """assiette-sup-s officielle dans la bbox, paginée (plafond 1000/réponse), groupée par suptype.
    Un échec de page LÈVE (jamais partiel silencieux)."""
    import time
    geom = json.dumps(_bbox_poly(bbox))
    out: dict[str, list] = {}
    start = 0
    while True:
        q = urllib.parse.urlencode({"geom": geom, "_start": start, "_limit": 500})
        page = _curl(f"{APICARTO}/assiette-sup-s?{q}").get("features", []) or []
        for f in page:
            if not f.get("geometry"):
                continue
            tp = ((f.get("properties") or {}).get("suptype") or "").lower() or "?"
            out.setdefault(tp, []).append(make_valid(shape(f["geometry"])))
        if len(page) < 500:
            break
        start += len(page)
        time.sleep(0.4)
    return out


def sup_servi(commune: str) -> dict:
    """SUP/PPR servies par le Mac pour la commune, groupées par suptype (kind ppr→pm1 ; kind sup→subtype)."""
    cq = commune.replace("'", "''")
    rows = _psql(
        "SELECT lower(coalesce(CASE WHEN kind='ppr' THEN 'pm1' ELSE subtype END,'?')), "
        "ST_AsGeoJSON(ST_Transform(geom,4326),7) FROM spatial_layers "
        f"WHERE kind IN ('ppr','sup') AND commune='{cq}'")
    out: dict[str, list] = {}
    for r in rows:
        if len(r) == 2 and r[1]:
            out.setdefault(r[0], []).append(make_valid(shape(json.loads(r[1]))))
    return out


def _controler(insee: str, commune: str) -> dict:
    res = {"insee": insee, "commune": commune, "par_type": {}, "parcelles": {}}
    bbox = _commune_bbox(insee)
    if bbox is None:
        res["verdict"] = "SANS PARCELLES"
        return res
    off = sup_officiel(bbox)
    srv = sup_servi(commune)
    res["n_officiel"] = {k: len(v) for k, v in off.items()}
    res["n_servi"] = {k: len(v) for k, v in srv.items()}
    different = False
    for tp in sorted(set(off) | set(srv)):
        uo = unary_union(off.get(tp, [])) if off.get(tp) else None
        us = unary_union(srv.get(tp, [])) if srv.get(tp) else None
        add = uo.difference(us) if (uo and us) else uo        # officiel non servi
        rem = us.difference(uo) if (uo and us) else us        # servi non officiel
        ca = _sig_components(add) if add else []
        cr = _sig_components(rem) if rem else []
        if not ca and not cr:
            continue
        # parcelles de CETTE commune touchées par la différence (écarte le débordement voisin)
        tp_add = _parcelles_touchees(insee, ca) if ca else {"sig50": {}, "sig5pct": {}}
        tp_rem = _parcelles_touchees(insee, cr) if cr else {"sig50": {}, "sig5pct": {}}
        n_parc = len(set(tp_add["sig50"]) | set(tp_rem["sig50"]))
        # surface de différence RETOMBANT sur les parcelles de la commune (métrique per-commune)
        aire_add = sum(tp_add["sig50"].values())
        aire_rem = sum(tp_rem["sig50"].values())
        if n_parc > 0:
            different = True
        res["par_type"][tp] = {
            "ajoute_m2_sur_parcelles": round(aire_add), "retire_m2_sur_parcelles": round(aire_rem),
            "n_comp_ajout": len(ca), "n_comp_retrait": len(cr),
            "parcelles_touchees": n_parc,
            "idus_5pct": sorted(set(tp_add["sig5pct"]) | set(tp_rem["sig5pct"]))[:10]}
    res["verdict"] = "DIFFÉRENT (parcelles touchées)" if different else "identique (hors parcelles)"
    return res


def controler(insee: str, commune: str, cap_s: int = 600) -> dict:
    def _to(*_):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, _to)
    signal.alarm(cap_s)
    try:
        return _controler(insee, commune)
    except TimeoutError:
        return {"insee": insee, "commune": commune, "verdict": f"ARRÊTÉ (>{cap_s // 60} min)"}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


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
    print(f"=== {commune} ({insee}) — officiel {r.get('n_officiel',{})} · servi {r.get('n_servi',{})} ===")
    print(f"VERDICT : {r['verdict']}")
    for tp, v in r.get("par_type", {}).items():
        print(f"  {tp}: {v}")


if __name__ == "__main__":
    main()
