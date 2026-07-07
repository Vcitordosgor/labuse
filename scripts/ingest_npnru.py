#!/usr/bin/env python3
"""Ingestion NPNRU (mandat contexte-commune, vague 2) — périmètres officiels DEAL Réunion.

Source géométries (vérifiée, archive relue) :
  Couche « NPNRU » — WFS Carmen DEAL_REUNION_2020 (MapServer, EPSG:2975), shapefile
  http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020?...typename=NPNRU
  8 quartiers d'intérêt NATIONAL (arrêté du 29/04/2015) — AUCUN intérêt régional à La Réunion.
  Les périmètres = périmètres QPV 2015 (les conventions NPNRU y sont adossées) ; la base
  porte les QPV génération 2024 → les DEUX couches coexistent, chacune datée.
Source liste (croisement) :
  « Le NPNRU » — ANCT, data.gouv.fr, millésime 2022, Licence Ouverte v2.0.

→ spatial_layers kind='anru', subtype='national' + table anru_quartiers (volet contexte).
"""
from __future__ import annotations

import json
import sys

import psycopg
import shapefile  # pyshp

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
SHP = "/tmp/npnru/NPNRU"
SOURCE_NOM = "NPNRU — DEAL Réunion (WFS Carmen, périmètres QPV 2015) · liste ANCT 2022 (LOv2)"
SOURCE_URL = ("http://ws.carmen.developpement-durable.gouv.fr/WFS/29/DEAL_REUNION_2020"
              "?request=GetFeature&service=WFS&typename=NPNRU&outputFormat=SHAPE&version=1.0.0")

#: correspondance QP2015 → QP2024 (source ANCT liste-correspondance-qp2024-qp2015.csv, vérifiée)
QP2024 = {"QP974001": "QN97401I", "QP974009": "QN97409M", "QP974018": "QN97418M",
          "QP974021": "QN97421I", "QP974025": "QN97425M", "QP974027": "QN97427I",
          "QP974028": "QN97428I", "QP974029": "QN97429I"}

INSEE = {"Saint-Louis": "97414", "Saint-Pierre": "97416", "Le Port": "97407",
         "Saint-André": "97409", "Saint-Benoît": "97410", "Saint-Denis": "97411"}


def ring_wkt(pts) -> str:
    return "(" + ", ".join(f"{x} {y}" for x, y in pts) + ")"


def shape_wkt(shp) -> str:
    """pyshp Polygon → WKT MULTIPOLYGON (anneaux découpés par `parts`)."""
    pts, parts = shp.points, list(shp.parts) + [len(shp.points)]
    rings = [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
    # heuristique simple : chaque anneau devient un polygone (les trous sont rares ici et
    # ST_MakeValid recolle) — les périmètres NPNRU 974 sont des polygones simples
    polys = ", ".join(f"({ring_wkt(r)})" for r in rings)
    return f"MULTIPOLYGON ({polys})"


def main() -> int:
    r = shapefile.Reader(SHP, encoding="cp1252")   # DBF Carmen en Windows-1252 (apostrophe courbe de « Bois D’Olives »)
    fields = [f[0] for f in r.fields[1:]]
    feats = [(dict(zip(fields, rec.record)), rec.shape) for rec in r.iterShapeRecords()]
    if len(feats) != 8:
        print(f"✗ attendu 8 quartiers NPNRU, trouvé {len(feats)} — STOP")
        return 1
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM data_sources WHERE name ILIKE '%%DEAL%%' LIMIT 1")
        row = cur.fetchone()
        sid = row[0] if row else None
        cur.execute("DELETE FROM spatial_layers WHERE kind='anru'")
        cur.execute("DELETE FROM anru_quartiers")
        for attrs, shp in feats:
            code, nom, commune = attrs.get("Code_qp"), attrs.get("Nom_qp"), attrs.get("Commune_qp")
            commune = {"Saint-Benoit": "Saint-Benoît", "Saint-Andre": "Saint-André"}.get(commune, commune)
            # le DBF DEAL porte un « ? » littéral dans ce nom — libellé OFFICIEL = liste ANCT
            if code == "QP974009":
                nom = "Bois D'Olives"
            wkt = shape_wkt(shp)
            cur.execute("""
                INSERT INTO spatial_layers (kind, subtype, name, geom, geom_2975, attrs,
                                            data_source_id, commune)
                VALUES ('anru', 'national', %(nom)s,
                        ST_Transform(ST_MakeValid(ST_GeomFromText(%(wkt)s, 2975)), 4326),
                        ST_MakeValid(ST_GeomFromText(%(wkt)s, 2975)),
                        %(attrs)s::jsonb, %(sid)s, %(c)s)""", {
                "nom": nom, "wkt": wkt, "sid": sid, "c": commune,
                "attrs": json.dumps({"code_qp_2015": code, "nom_qp": nom,
                                     "code_qp_2024": QP2024.get(code),
                                     "interet": "national", "programme": "NPNRU",
                                     "source": "DEAL_REUNION_WFS"}),
            })
            cur.execute("""
                INSERT INTO anru_quartiers (commune, insee, nom, interet, code_qpv,
                                            source_nom, source_url)
                VALUES (%s, %s, %s, 'national', %s, %s, %s)""",
                        (commune, INSEE.get(commune), nom, code, SOURCE_NOM, SOURCE_URL))
            print(f"  {commune}: {nom} ({code} → {QP2024.get(code)})")
        conn.commit()
    print("✓ NPNRU ingéré : 8 quartiers d'intérêt national (couche anru + table quartiers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
