#!/usr/bin/env python3
"""Calibrage zonage PLU — export DB → YAML versionné + sidecar, import symétrique, round-trip.

CE QUE LA DB SAIT (et donc ce qu'on re-grave) : le ZONAGE OPPOSABLE ingéré aux sessions de
calibrage (idurba, zones, libellés, attrs, géométries) — c'est ce que la cascade lit.
CE QUE LA DB NE SAIT PAS (consigné, hors périmètre) : les règles chiffrées par zone
(hauteurs/articles, constructible_neuf) extraites des règlements PDF — elles ne vivaient que
dans les config/plu_<commune>.yaml perdus ; à re-graver depuis les règlements, pas depuis la DB.

Format :
  config/calibrage/zonage_<slug>.yaml   MANIFESTE versionné (git) : provenance, idurba,
                                        inventaire par zone + md5(géométrie EWKB)
  data/calibrage/zonage_<slug>.geoms.jsonl.gz  géométries EWKB hex (gitignoré par politique
                                        du dépôt « pas de dump de données publiques » —
                                        couvert par les backups, régénérable par export)

Usage :
  calibrage_zonage.py export                    # 24 communes → manifestes + sidecars
  calibrage_zonage.py import --commune <nom> --table spatial_layers_temoin
  calibrage_zonage.py roundtrip                 # DB → YAML → table témoin → ZÉRO écart (prouvé)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

import psycopg
import yaml

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "calibrage"
DATA = ROOT / "data" / "calibrage"
RUN_REF = "q_v2"


def slug(commune: str) -> str:
    s = unicodedata.normalize("NFD", commune).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", "_").replace("'", "_").replace("-", "_")


def commune_insee(cur, commune: str) -> str | None:
    """Code INSEE de la commune, dérivé du cadastre (préfixe IDU) — zéro dépendance."""
    cur.execute("SELECT left(min(idu), 5) AS insee FROM parcels WHERE commune = %(c)s", {"c": commune})
    r = cur.fetchone()
    return r["insee"] if r else None


def export(cur, only_commune: str | None = None) -> None:
    CFG.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    cur.execute("SELECT DISTINCT commune FROM spatial_layers WHERE kind='plu_gpu_zone'"
                " AND commune IS NOT NULL AND commune NOT LIKE '%%,%%' ORDER BY 1")
    communes = [r["commune"] for r in cur.fetchall()]
    if only_commune:
        communes = [c for c in communes if c == only_commune]
    for c in communes:
        insee = commune_insee(cur, c)
        cur.execute("""
            SELECT subtype, name, attrs, encode(ST_AsEWKB(geom), 'hex') AS ewkb,
                   round(ST_Area(geom_2975)::numeric)::bigint AS surface_m2
            FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune=%(c)s
            ORDER BY subtype, name, md5(ST_AsEWKB(geom)::text)""", {"c": c})
        rows = cur.fetchall()
        zones, geoms, debords = [], [], []
        for r in rows:
            # MANDAT RNU A1 — filtre ANTI-DÉBORD (général, toutes communes) : une zone dont
            # l'idurba appartient à une AUTRE commune est un artefact d'ingestion par bbox
            # (PLU voisin qui mord l'emprise). Elle ne doit JAMAIS être gravée au manifeste
            # de CETTE commune : c'est ainsi que zonage_saint_philippe.yaml a figé 19 zones
            # de Saint-Joseph/Sainte-Rose sous le nom de Saint-Philippe (commune au RNU —
            # cf. reports/algo1b-diagnostic-rr.md, annexe). Exclue et COMPTÉE, jamais tue.
            zid = ((r["attrs"] or {}).get("idurba") or "")
            if insee and zid and not zid.startswith(insee):
                debords.append(zid)
                continue
            md5 = hashlib.md5(bytes.fromhex(r["ewkb"])).hexdigest()
            zones.append({"subtype": r["subtype"], "name": r["name"], "attrs": r["attrs"],
                          "surface_m2": int(r["surface_m2"] or 0), "geom_md5": md5})
            geoms.append({"geom_md5": md5, "ewkb_hex": r["ewkb"]})
        idurbas = sorted({(z["attrs"] or {}).get("idurba") for z in zones if (z["attrs"] or {}).get("idurba")})
        manifest = {
            "provenance": {
                "extrait_le": date.today().isoformat(),
                "source_tables": ["spatial_layers (kind='plu_gpu_zone')"],
                "run_de_reference": RUN_REF,
                "note": ("Zonage OPPOSABLE tel qu'ingéré aux sessions de calibrage (juin-juillet "
                         "2026, cf. docs/communes/ et mémoires). Les RÈGLES chiffrées par zone "
                         "(hauteurs/articles) ne sont PAS en DB — cf. en-tête du script."),
            },
            "commune": c, "idurba": idurbas, "n_zones": len(zones),
            "geoms_sidecar": f"data/calibrage/zonage_{slug(c)}.geoms.jsonl.gz",
            "zones": zones,
        }
        if debords:
            # traçabilité : les débords exclus restent visibles au manifeste (jamais silencieux)
            manifest["zones_debord_exclues"] = {
                "n": len(debords), "idurba": sorted(set(debords)),
                "note": ("zones de PLU VOISINS mordant l'emprise (artefact bbox) — exclues du "
                         "manifeste : aucune parcelle ne doit hériter d'un règlement voisin "
                         "(mandat RNU A1)")}
        if not zones and insee:
            manifest["statut_document"] = (
                "AUCUNE zone propre — commune sans document local ingéré ; si la commune est "
                "au RNU (cf. config/rnu_communes.yaml), c'est l'état ATTENDU, ne pas réimporter")
        (CFG / f"zonage_{slug(c)}.yaml").write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
        with gzip.open(DATA / f"zonage_{slug(c)}.geoms.jsonl.gz", "wt", encoding="utf-8") as f:
            for g in geoms:
                f.write(json.dumps(g) + "\n")
        print(f"  {c}: {len(zones)} zones · idurba {','.join(i for i in idurbas)}")
    print(f"✓ export : {len(communes)} manifestes → {CFG} · sidecars → {DATA}")


def do_import(cur, commune: str, table: str) -> int:
    man = yaml.safe_load((CFG / f"zonage_{slug(commune)}.yaml").read_text(encoding="utf-8"))
    geoms = {}
    with gzip.open(ROOT / man["geoms_sidecar"], "rt", encoding="utf-8") as f:
        for line in f:
            g = json.loads(line)
            geoms[g["geom_md5"]] = g["ewkb_hex"]
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
        id serial PRIMARY KEY, kind text, subtype text, name text, geom geometry,
        attrs jsonb, commune text)""")
    cur.execute(f"DELETE FROM {table} WHERE commune = %(c)s", {"c": commune})
    n = 0
    for z in man["zones"]:
        cur.execute(
            f"INSERT INTO {table} (kind, subtype, name, geom, attrs, commune)"
            " VALUES ('plu_gpu_zone', %(st)s, %(nm)s, ST_GeomFromEWKB(decode(%(g)s, 'hex')),"
            " %(at)s, %(c)s)",
            {"st": z["subtype"], "nm": z["name"], "g": geoms[z["geom_md5"]],
             "at": json.dumps(z["attrs"]), "c": commune})
        n += 1
    return n


def roundtrip(cur) -> bool:
    """DB → YAML → table témoin → comparaison zone à zone (subtype, name, attrs, md5 géométrie).
    ZÉRO écart exigé — sans cette preuve, des YAML que rien ne sait relire = demi-feature."""
    cur.execute("SELECT DISTINCT commune FROM spatial_layers WHERE kind='plu_gpu_zone'"
                " AND commune IS NOT NULL AND commune NOT LIKE '%%,%%' ORDER BY 1")
    communes = [r["commune"] for r in cur.fetchall()]
    ok = True
    for c in communes:
        n = do_import(cur, c, "spatial_layers_temoin")
        # MANDAT RNU A1 : la face DB de la comparaison exclut les DÉBORDS (idurba d'une autre
        # commune) — même règle que l'export. Le ZÉRO écart porte sur les zones PROPRES.
        insee = commune_insee(cur, c)
        cur.execute("""
            WITH a AS (SELECT subtype, name, attrs::text AS at, md5(ST_AsEWKB(geom)::text) AS g
                       FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune=%(c)s
                         AND (coalesce(attrs->>'idurba','') = ''
                              OR %(insee)s::text IS NULL
                              OR attrs->>'idurba' LIKE %(insee)s::text || '%%')),
                 b AS (SELECT subtype, name, attrs::text AS at, md5(ST_AsEWKB(geom)::text) AS g
                       FROM spatial_layers_temoin WHERE commune=%(c)s)
            SELECT (SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b) x)
                 + (SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a) y) AS d""",
            {"c": c, "insee": insee})
        diff = cur.fetchone()["d"]
        status = "✓ ZÉRO écart" if diff == 0 else f"✗ {diff} écart(s)"
        print(f"  {c}: {n} zones réimportées → {status}")
        ok = ok and diff == 0
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["export", "import", "roundtrip"])
    ap.add_argument("--commune")
    ap.add_argument("--table", default="spatial_layers_temoin")
    args = ap.parse_args()
    with psycopg.connect(DB) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        if args.action == "export":
            export(cur, only_commune=args.commune)
        elif args.action == "import":
            n = do_import(cur, args.commune, args.table)
            conn.commit()
            print(f"✓ {n} zones importées dans {args.table}")
        else:
            ok = roundtrip(cur)
            conn.rollback()   # le témoin est jetable : rien ne persiste après la preuve
            print("ROUND-TRIP " + ("PROUVÉ — zéro écart sur toutes les communes" if ok else "EN ÉCHEC"))
            return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
