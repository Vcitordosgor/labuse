"""Phase 1.A — GATE GPU : test du PLU de Saint-Paul (INSEE 97415) sur l'API Carto GPU.

Objectif (brief LA BUSE v2, Phase 1.A « STOP & VALIDATE ») : prouver que le PLU de
Saint-Paul est dématérialisé sur le Géoportail de l'Urbanisme (format CNIG), interrogeable
en direct, et comparer le zonage LIVE renvoyé par l'API à ce que LA BUSE a déjà ingéré
(table spatial_layers.kind='plu_gpu_zone') et au verdict de sa cascade.

Endpoints testés (apicarto.ign.fr/api/gpu) :
  - /municipality?insee=97415          → le document d'urbanisme est-il rattaché à la commune
  - /document?geom=<point>             → métadonnées du doc (partition, datappro, datvalidoc…)  [fraîcheur]
  - /zone-urba?geom=<polygone>         → zonage (typezone U/AUc/A/N, libelle, libelong, partition)
  - /prescription-surf|-lin|-pct?geom= → prescriptions surfaciques / linéaires / ponctuelles
  - /assiette-sup-s?geom=<polygone>    → assiettes de servitudes d'utilité publique (bonus)

LECTURE SEULE : aucune écriture en base, aucune modification de la cascade. Discipline
réseau : retry + backoff exponentiel + cache disque (reports/phase1a_gpu/cache/).

Usage : python scripts/gpu_witness_test.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from labuse.db import session_scope  # noqa: E402

BASE = "https://apicarto.ign.fr/api/gpu"
INSEE = "97415"
OUT_DIR = ROOT / "reports" / "phase1a_gpu"
CACHE_DIR = OUT_DIR / "cache"

# Parcelles témoins (sélectionnées en base par zone PLU dominante > 95 % de couverture,
# dernière évaluation de la cascade) :
#   U   — Saint-Paul, zone urbaine constructible, classée « opportunité » par LA BUSE
#   A   — zone agricole, « à creuser » (flag SAFER)
#   AUc — à urbaniser, « opportunité » PLU mais SAR proxy la signale « espace naturel » à 98 %
WITNESSES = [
    {"idu": "97415000BV0912", "attendu": "U",   "role": "urbaine / centre"},
    {"idu": "97415000BV0405", "attendu": "A",   "role": "agricole / SAFER"},
    {"idu": "97415000BV1431", "attendu": "AUc", "role": "à urbaniser"},
]


def _cache_path(url: str, params: dict) -> Path:
    key = hashlib.sha1((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def gpu_get(path: str, params: dict, *, retries: int = 4) -> dict | None:
    """GET poli sur l'API Carto GPU : cache disque, retry + backoff exponentiel (2,4,8 s)."""
    url = f"{BASE}/{path}"
    cp = _cache_path(url, params)
    if cp.exists():
        return json.loads(cp.read_text())
    last_err = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=30.0, headers={"User-Agent": "LA-BUSE/0.1 (phase1a-gate)"}) as c:
                r = c.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_text(json.dumps(data))
                return data
            last_err = f"HTTP {r.status_code}"
            # 400/404 = pas de couche à cet endroit (réponse métier), inutile de réessayer
            if r.status_code in (400, 404):
                return {"_http_error": r.status_code, "_body": r.text[:200]}
        except Exception as exc:  # réseau / timeout / DNS
            last_err = f"{type(exc).__name__}: {exc}"
        if attempt < retries - 1:
            time.sleep(2 ** (attempt + 1))
    return {"_error": last_err}


def fetch_witness_geometries() -> dict[str, dict]:
    """Géométries des parcelles témoins : centroïde (point) + polygone simplifié (GeoJSON 4326).

    + zonage déjà ingéré (plu_gpu_zone dominant) et verdicts de cascade, pour la comparaison.
    """
    out: dict[str, dict] = {}
    idus = [w["idu"] for w in WITNESSES]
    with session_scope() as s:
        rows = s.execute(text("""
            SELECT idu, surface_m2,
                   ST_AsGeoJSON(centroid) AS centroid,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.00002)) AS poly
            FROM parcels WHERE idu = ANY(:idus)
        """), {"idus": idus}).mappings().all()
        for r in rows:
            out[r["idu"]] = {
                "surface_m2": round(r["surface_m2"] or 0),
                "centroid": json.loads(r["centroid"]),
                "polygon": json.loads(r["poly"]),
            }
        # zonage ingéré (dominant) + verdicts cascade
        for idu in idus:
            dom = s.execute(text("""
                SELECT z.subtype, z.attrs,
                       ST_Area(ST_Intersection(p.geom_2975, z.geom_2975))/NULLIF(ST_Area(p.geom_2975),0) AS cov
                FROM parcels p
                JOIN spatial_layers z ON z.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975, z.geom_2975)
                WHERE p.idu = :idu
                ORDER BY cov DESC LIMIT 1
            """), {"idu": idu}).mappings().first()
            verdicts = s.execute(text("""
                SELECT c.layer_name, c.result, c.severity, c.detail
                FROM parcels p JOIN cascade_results c ON c.parcel_id = p.id
                WHERE p.idu = :idu AND c.layer_name IN ('zonage_plu_gpu','sar','safer')
                ORDER BY c.layer_name
            """), {"idu": idu}).mappings().all()
            if idu in out:
                out[idu]["ingested_zone"] = dict(dom) if dom else None
                out[idu]["cascade"] = [dict(v) for v in verdicts]
    return out


def summarize_zones(fc: dict | None) -> list[dict]:
    if not fc or "features" not in fc:
        return []
    out = []
    for feat in fc.get("features", []):
        p = feat.get("properties", {}) or {}
        out.append({
            "typezone": p.get("typezone"),
            "libelle": p.get("libelle"),
            "libelong": p.get("libelong"),
            "partition": p.get("partition"),
            "idurba": p.get("idurba"),
            "datappro": p.get("datappro"),
            "datvalid": p.get("datvalid") or p.get("datvalidoc"),
            "gpu_status": p.get("gpu_status"),
            "gpu_timestamp": p.get("gpu_timestamp"),
        })
    return out


def summarize_prescriptions(fc: dict | None) -> list[dict]:
    """Prescriptions GPU (surf/lin/pct) : nature lisible (typepsc + libellé)."""
    if not fc or "features" not in fc:
        return []
    out = []
    for feat in fc.get("features", []):
        p = feat.get("properties", {}) or {}
        out.append({
            "typepsc": p.get("typepsc"),
            "stypepsc": p.get("stypepsc"),
            "libelle": p.get("libelle"),
            "idurba": p.get("idurba"),
        })
    return out


def count_features(fc: dict | None) -> int | str:
    if not fc:
        return "—"
    if "_http_error" in fc:
        return f"HTTP {fc['_http_error']}"
    if "_error" in fc:
        return f"ERR {fc['_error']}"
    return len(fc.get("features", []))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {"insee": INSEE, "base": BASE, "witnesses": []}

    # 1) municipality — le document est-il rattaché à la commune ?
    print(f"[1] /municipality?insee={INSEE}")
    muni = gpu_get("municipality", {"insee": INSEE})
    muni_zones = []
    if muni and "features" in muni:
        for feat in muni["features"]:
            pr = feat.get("properties", {}) or {}
            muni_zones.append({k: pr.get(k) for k in ("partition", "is_rnu", "name", "insee")})
    report["municipality"] = {"feature_count": count_features(muni), "properties": muni_zones}
    print(f"    features={count_features(muni)}  props={muni_zones}")

    geoms = fetch_witness_geometries()

    for w in WITNESSES:
        idu = w["idu"]
        g = geoms.get(idu)
        print(f"\n[parcelle] {idu}  (attendu zone {w['attendu']} — {w['role']})")
        if not g:
            print("    !! géométrie introuvable en base")
            continue
        pt = g["centroid"]
        poly = g["polygon"]

        doc = gpu_get("document", {"geom": json.dumps(pt)})
        zu = gpu_get("zone-urba", {"geom": json.dumps(poly)})
        presc = {k: gpu_get(f"prescription-{k}", {"geom": json.dumps(poly)}) for k in ("surf", "lin", "pct")}
        assiette = gpu_get("assiette-sup-s", {"geom": json.dumps(poly)})

        zones = summarize_zones(zu)
        doc_props = summarize_zones(doc)
        ingested = g.get("ingested_zone") or {}
        cascade = g.get("cascade") or []

        rec = {
            "idu": idu,
            "attendu": w["attendu"],
            "role": w["role"],
            "surface_m2": g["surface_m2"],
            "gpu_live": {
                "zone_urba": zones,
                "document": doc_props,
                "prescription_counts": {k: count_features(v) for k, v in presc.items()},
                "prescriptions": {k: summarize_prescriptions(v) for k, v in presc.items()},
                "assiette_sup_s": count_features(assiette),
            },
            "deja_ingere": {
                "subtype": ingested.get("subtype"),
                "coverage": round(float(ingested.get("cov") or 0), 3),
                "attrs": ingested.get("attrs"),
            },
            "cascade": cascade,
        }
        report["witnesses"].append(rec)

        live = ", ".join(f"{z['typezone']}({z['libelle']})" for z in zones) or "∅"
        print(f"    GPU live zone-urba : {live}")
        print(f"    GPU document       : {[d.get('partition') for d in doc_props]}  "
              f"datappro={[d.get('datappro') for d in doc_props]}")
        print(f"    prescriptions      : surf={rec['gpu_live']['prescription_counts']['surf']} "
              f"lin={rec['gpu_live']['prescription_counts']['lin']} "
              f"pct={rec['gpu_live']['prescription_counts']['pct']}  "
              f"assiette_sup={rec['gpu_live']['assiette_sup_s']}")
        print(f"    déjà ingéré (DB)   : {ingested.get('subtype')} (cov {rec['deja_ingere']['coverage']})")
        for c in cascade:
            print(f"      cascade[{c['layer_name']}] = {c['result']}"
                  + (f"/{c['severity']}" if c.get("severity") else "")
                  + f" — {c['detail'][:90]}")

    out_json = OUT_DIR / "gpu_witness_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n✓ rapport JSON écrit : {out_json.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
