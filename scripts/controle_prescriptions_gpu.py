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
K = 111_000 * 103_600  # deg²→m² approx (La Réunion, lat ~-21)
SEUIL_SURF_M2 = 200.0     # plancher de bruit : un écart ZIP(2975→4326) vs servi(apicarto 4326) crée des slivers <~200 m² ; au-delà = vrai objet
SEUIL_DEPL_PCT = 2.0      # lin/pct : déplacement relatif < 2 % = bruit
LABELS = {"01": "EBC", "05": "ER", "02": "secteur conditionné"}


class _DownloadError(RuntimeError):
    """Téléchargement GPU en échec (timeout/HTTP/JSON tronqué) — JAMAIS confondu avec « 0 objet »."""


def _curl(url: str) -> dict:
    """GET JSON robuste : 3 essais, timeout 120 s, lève `_DownloadError` sur échec persistant
    (sinon une réponse tronquée/vide passerait pour « document vide » → faux « tout retiré »)."""
    last = ""
    for _ in range(3):
        p = subprocess.run(["curl", "-s", "-m", "120", "--retry", "2", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError as e:
                last = f"JSON tronqué ({e})"
                continue
        last = f"curl rc={p.returncode} {p.stderr.strip()[:80]}"
    raise _DownloadError(f"{url} : {last}")


def gpu_document(insee: str, kind: str) -> list[dict]:
    """Features du document EN VIGUEUR de la commune (partition DU_<insee>), paginées, sans voisin.
    Pages de 300 (les grosses communes — Saint-Denis 2908 prescriptions — dépassaient 10 Mo/page et
    la réponse était tronquée). Un échec de page LÈVE (jamais un résultat partiel silencieux)."""
    import time
    part = f"DU_{insee}"
    feats, start = [], 0
    while True:
        q = urllib.parse.urlencode({"partition": part, "_start": start, "_limit": 300})
        page = _curl(f"{APICARTO}/{ENDPOINTS[kind]}?{q}").get("features", []) or []
        feats += [f for f in page if (f.get("properties") or {}).get("partition") == part]
        if len(page) < 300:
            break
        start += len(page)
        time.sleep(0.4)                              # politesse : évite le throttling d'apicarto
    return feats


# ───────────────── repli ZIP officiel (pack GPU), source qui FAIT FOI (PLU-MAJ-2) ─────────────────
def _doc_meta(insee: str) -> tuple[str, str] | None:
    """(id, originalName) du document EN VIGUEUR au GPU — pour construire l'URL du pack ZIP."""
    d = _curl(f"https://www.geoportail-urbanisme.gouv.fr/api/document?grid={insee}&status=document.production")
    items = d if isinstance(d, list) else d.get("items") or d.get("content") or []
    if not items:
        return None
    x = items[0]
    return x.get("id"), x.get("originalName")


def gpu_document_zip(insee: str) -> dict:
    """Pack OFFICIEL du document (un fichier zip, pas d'API paginée — PLU-MAJ-2). Lit les shapefiles
    PRESCRIPTION_{SURF,LIN,PCT} (EPSG:2975), reprojette en 4326 pour comparer au servi. Rend
    {kind: [ {geometry, properties:{typepsc}} ]}. Source qui fait foi quand apicarto est instable."""
    import os
    import tempfile
    import zipfile

    import shapefile
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform as shp_transform

    meta = _doc_meta(insee)
    if not meta:
        raise _DownloadError(f"document GPU introuvable pour {insee}")
    doc_id, name = meta
    url = f"https://www.geoportail-urbanisme.gouv.fr/api/document/{doc_id}/download/{name}.zip"
    tmpd = tempfile.mkdtemp(prefix="ml7zip_")
    zp = os.path.join(tmpd, "doc.zip")
    p = subprocess.run(["curl", "-sL", "-m", "600", "-o", zp, url], capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(zp) or os.path.getsize(zp) < 10_000:
        raise _DownloadError(f"ZIP {url} : curl rc={p.returncode}")
    tr = Transformer.from_crs(2975, 4326, always_xy=True)
    out: dict = {}
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        for kind in ENDPOINTS:
            tag = f"PRESCRIPTION_{kind.upper()}"
            base = next((n[:-4] for n in names if tag in n.upper() and n.upper().endswith(".SHP")), None)
            feats = []
            if base:
                for ext in (".shp", ".dbf", ".shx"):
                    m = next((n for n in names if n[:-4] == base and n.lower().endswith(ext)), None)
                    if m:
                        z.extract(m, tmpd)
                shp = os.path.join(tmpd, base + ".shp")
                if os.path.exists(shp):
                    # .dbf parfois en Latin-1 (byte 0xe9 = « é ») : latin-1 décode tous les octets
                    # sans crash ; on ne lit que TYPEPSC (chiffres ASCII) + la géométrie.
                    r = shapefile.Reader(shp, encoding="latin-1", encodingErrors="replace")
                    fields = [f[0] for f in r.fields[1:]]
                    # champ TYPEPSC — casse variable selon la version CNIG du document
                    # (« TYPEPSC » pour Saint-Paul, « typepsc » pour Les Avirons) → insensible à la casse.
                    ipsc = next((i for i, f in enumerate(fields) if f.strip().lower() == "typepsc"), None)
                    for sr in r.shapeRecords():
                        g = shp_transform(lambda x, y, z=None: tr.transform(x, y), shape(sr.shape.__geo_interface__))
                        tp = (str(sr.record[ipsc]).strip() if ipsc is not None else "") or None
                        feats.append({"geometry": mapping(g), "properties": {"typepsc": tp,
                                      "partition": f"DU_{insee}"}})
            out[kind] = feats
    subprocess.run(["rm", "-rf", tmpd])
    return out


def _psql(sql: str, sep: str = "\x1f") -> list[list[str]]:
    import os
    # Cible PROD en LECTURE SEULE si CONTROLE_PROD_SSH est posé (ex. « labuse-vps ») : la géométrie
    # et le ZIP restent calculés sur le Mac ; seules les requêtes `servi`/parcelles passent sur la prod
    # via ssh + sudo -u postgres (auth peer, sans mot de passe). Multiplexage ssh pour la vitesse.
    prod = os.environ.get("CONTROLE_PROD_SSH")
    if prod:
        psep = "§"   # séparateur imprimable, sûr à travers ssh (ni geojson ni idu n'en contiennent)
        full = f"SET statement_timeout='170s';\n{sql}"
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30",
             "-o", "ControlMaster=auto", "-o", "ControlPath=/tmp/cm_controle_%r@%h:%p",
             "-o", "ControlPersist=60s", prod,
             f"sudo -u postgres psql -At -F '{psep}' -d labuse"],
            input=full, capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip()[:300])
        return [line.split(psep) for line in out.stdout.splitlines()
                if line.strip() and line.strip() != "SET"]   # « SET » = écho du statement_timeout
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
    _cq = commune.replace("'", "''")                 # apostrophe (L'Étang-Salé) doublée pour le SQL
    rows = _psql("SELECT DISTINCT attrs->>'idurba' FROM spatial_layers WHERE kind='plu_gpu_prescription' "
                 f"AND commune='{_cq}' AND attrs->>'idurba' LIKE '{insee}\\_%'")
    cands = [r[0] for r in rows if r and r[0]]
    return sorted(cands)[-1] if cands else None


def servi_geoms(commune: str, kind: str, idurba: str) -> list[tuple[str, object]]:
    _cq = commune.replace("'", "''")
    rows = _psql(
        "SELECT coalesce(attrs->>'typepsc',''), ST_AsGeoJSON(ST_Transform(geom,4326),7) "
        f"FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='{_cq}' "
        f"AND attrs->>'geom_kind'='{kind}' AND attrs->>'idurba'='{idurba}'")
    return [(r[0], make_valid(shape(json.loads(r[1])))) for r in rows if len(r) == 2 and r[1]]


def _polygones(geom) -> list:
    """Composantes POLYGONALES à plat — la différence de deux polygones quasi-coïncidents rend souvent
    une GeometryCollection (polygones + bouts de lignes) ; son geom_type n'est NI « Multi… » NI
    « Polygon », donc l'ancien filtre la laissait passer en bloc (plancher contourné). On n'extrait
    QUE les polygones (les slivers dégénérés en ligne ont une aire nulle → écartés)."""
    if geom is None or geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [geom]
    if gt.startswith("Multi") or gt == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_polygones(g))
        return out
    return []  # LineString/Point : aire nulle, pas une vraie prescription surfacique


def _sig_components(geom):
    # plancher de bruit appliqué à CHAQUE polygone (slivers de reprojection <~200 m² écartés).
    return [c for c in _polygones(geom) if c.area * K > SEUIL_SURF_M2]


def _parcelles_touchees(insee: str, comp_geoms: list) -> dict:
    """Parcelles dont l'intersection avec les composantes de changement dépasse 50 m² ET/OU 5 % de
    leur surface — JAMAIS d'estimation. Rapide et robuste : la diff (un ruban d'EBC peut être fin mais
    toucher 600+ parcelles) est reprojetée en 2975, DÉCOUPÉE par `ST_Subdivide` (≤64 sommets/pièce) et
    jointe à `parcels.geom_2975` INDEXÉE ; l'aire d'intersection est SOMMÉE par parcelle. Pas d'API."""
    from shapely.ops import unary_union
    if not comp_geoms:
        return {"sig50": {}, "sig5pct": {}}
    wkt = make_valid(unary_union(comp_geoms)).wkt
    rows = _psql(
        "WITH d AS (SELECT (ST_Dump(ST_Subdivide("
        f"  ST_MakeValid(ST_Transform(ST_GeomFromText('{wkt}',4326),2975)),64))).geom g) "
        "SELECT idu, round(sum(a)::numeric) m2, round((100*sum(a)/max(parc))::numeric,1) pct FROM ("
        "  SELECT p.idu, ST_Area(ST_Intersection(p.geom_2975, d.g)) a, ST_Area(p.geom_2975) parc "
        f"  FROM parcels p JOIN d ON p.geom_2975 && d.g AND ST_Intersects(p.geom_2975, d.g) "
        f"  WHERE left(p.idu,5)='{insee}'"
        ") z GROUP BY idu HAVING sum(a) > 50")
    sig50, sig5 = {}, {}
    for r in rows:
        idu, m2, pct = r[0], float(r[1]), float(r[2] or 0)
        sig50[idu] = m2
        if pct > 5.0:
            sig5[idu] = pct
    return {"sig50": sig50, "sig5pct": sig5}


def controler(insee: str, commune: str, avec_parcelles: bool = True, cap_s: int = 600) -> dict:
    """Verdict + surfaces (1er temps) ; parcelles touchées (2e temps) si `avec_parcelles`.
    Cap de `cap_s` (défaut 10 min) par commune : au-delà → verdict « ARRÊTÉ (>10 min) »."""
    import signal

    def _timeout(*_a):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(cap_s)
    try:
        return _controler(insee, commune, avec_parcelles)
    except TimeoutError:
        return {"insee": insee, "commune": commune, "verdict": f"ARRÊTÉ (>{cap_s // 60} min)"}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _controler(insee: str, commune: str, avec_parcelles: bool) -> dict:
    own = servi_idurba(insee, commune)
    res = {"insee": insee, "commune": commune, "idurba_servi": own, "par_type": {}, "parcelles": {}}
    if own is None:
        res["verdict"] = "SANS DOCUMENT SERVI"
        return res
    # Source PRINCIPALE = pack ZIP officiel du GPU (un fichier, fait foi — Vic) ; apicarto en SECOURS.
    # La source et le NOMBRE d'objets par type sont rapportés → un téléchargement incomplet se VOIT.
    def _via_apicarto() -> dict:
        return {kind: gpu_document(insee, kind) for kind in ENDPOINTS}

    gpu_par_kind: dict[str, list] = {}
    try:
        gpu_par_kind = gpu_document_zip(insee)
        res["source"] = "ZIP officiel GPU"
        # certains documents anciens sont en MapInfo TAB (pas .shp) → le lecteur ZIP rend 0 objet ;
        # si le servi a des prescriptions, c'est une LECTURE ZIP ratée → on bascule sur apicarto.
        if sum(len(v) for v in gpu_par_kind.values()) == 0 and any(
                servi_geoms(commune, k, own) for k in ENDPOINTS):
            gpu_par_kind = _via_apicarto()
            res["source"] = "apicarto (ZIP non-shapefile)"
    except _DownloadError:
        try:
            gpu_par_kind = _via_apicarto()
            res["source"] = "apicarto (secours)"
        except _DownloadError as e:
            res["verdict"] = "ERREUR TÉLÉCHARGEMENT"       # jamais « tout retiré » sur un échec réseau
            res["erreur"] = str(e)[:150]
            return res
    res["n_gpu"] = {k: len(v) for k, v in gpu_par_kind.items()}

    diff_surf_by_type: dict[str, list] = {}
    different = False
    for kind in ENDPOINTS:
        gpu = gpu_par_kind[kind]
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
                b = 1.8e-5  # ~2 m en degrés
                bg = unary_union([x.buffer(b) for x in gg]) if gg else None
                bs = unary_union([x.buffer(b) for x in sg]) if sg else None
                sym = (bg.symmetric_difference(bs).area if (bg and bs)
                       else max(bg.area if bg else 0, bs.area if bs else 0))
                base = max(bg.area if bg else 0, bs.area if bs else 0, 1e-12)
                pct = 100 * sym / base
                if pct > SEUIL_DEPL_PCT:
                    different = True
                    res["par_type"][f"{kind}/{tp}"] = {"deplacement_pct": round(pct, 1)}
    res["verdict"] = "DIFFÉRENT" if different else "identique"
    # 2e temps — parcelles touchées, seulement si demandé ET commune différente.
    if avec_parcelles and different:
        for tp, comps in diff_surf_by_type.items():
            t = _parcelles_touchees(insee, comps)
            res["parcelles"][LABELS.get(tp, f"type {tp}")] = {
                "sig50_n": len(t["sig50"]), "sig5pct_n": len(t["sig5pct"]),
                "sig5pct_idus": sorted(t["sig5pct"])}
    return res


def main():
    args = sys.argv[1:]
    json_only = verdict_only = False
    while args and args[0] in ("--json", "--verdict-only"):
        if args[0] == "--json":
            json_only = True
        else:
            verdict_only = True      # 1er temps : verdict + surfaces, SANS les parcelles
        args = args[1:]
    insee, commune = args[0], args[1]
    r = controler(insee, commune, avec_parcelles=not verdict_only)
    if json_only:
        print(json.dumps(r, ensure_ascii=False))
        return
    print(f"=== {commune} ({insee}) — servi {r.get('idurba_servi')} — source {r.get('source','?')} — n_gpu {r.get('n_gpu',{})} ===")
    print(f"VERDICT : {r['verdict']}")
    for k, v in r.get("par_type", {}).items():      # .get : un verdict ARRÊTÉ/ERREUR n'a pas ces clés
        print(f"  {k}: {v}")
    for lbl, v in r.get("parcelles", {}).items():
        print(f"  parcelles {lbl} : >50 m² = {v['sig50_n']} · >5% = {v['sig5pct_n']} {v['sig5pct_idus'][:10]}")


if __name__ == "__main__":
    main()
