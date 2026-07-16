#!/usr/bin/env python3
"""Ingestion CONSOMMATION d'espaces NAF par commune (mandat ZAN enrichi).

Source (opendata, Licence Ouverte 2.0) :
  « Consommation d'espaces naturels, agricoles et forestiers du 1er janvier 2009 au
    1er janvier 2024 » (CONSOENAF 2009-2024) — Portail national de l'artificialisation
    des sols / Cerema, calculée sur les Fichiers fonciers. Publié le 12/05/2025.
  data.gouv.fr : /datasets/consommation-despaces-naturels-agricoles-et-forestiers-du-
                 1er-janvier-2009-au-1er-janvier-2024

Colonnes lues (fidèles au fichier) : `idcom` (INSEE), `idcomtxt` (nom), et les flux annuels
`nafYYartZZ` (ENAF consommés, m²) + destination habitat `artYYhabZZ`. On agrège les fenêtres
2011-2021 (10 flux) et 2021-2024 (3 flux) — celles utiles à l'indicateur ZAN (règle -50%).

DONNÉE OBSERVÉE (Sourcé). Aucune dérivation ici (budget/reste = calculés à la lecture, étiquetés
Estimé côté API). Zéro fabrication : si une commune 974 manque, on STOP (source à revérifier).
"""
from __future__ import annotations

import csv
import urllib.request
from pathlib import Path

import psycopg

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
URL = ("https://static.data.gouv.fr/resources/consommation-despaces-naturels-agricoles-et-"
       "forestiers-du-1er-janvier-2009-au-1er-janvier-2024/20250512-132201/"
       "conso2009-2024-resultats-com.csv")
SOURCE_NOM = ("Portail national de l'artificialisation / Cerema — Fichiers fonciers "
              "(CONSOENAF, indicateurs communaux)")
MILLESIME = "consommation ENAF 2009-2024 · publié 12/05/2025 · Licence Ouverte 2.0"

NAF_1121 = [f"naf{y:02d}art{y + 1:02d}" for y in range(11, 21)]   # 2011→2021
NAF_2124 = [f"naf{y:02d}art{y + 1:02d}" for y in range(21, 24)]   # 2021→2024
HAB_1121 = [f"art{y:02d}hab{y + 1:02d}" for y in range(11, 21)]
HAB_2124 = [f"art{y:02d}hab{y + 1:02d}" for y in range(21, 24)]

DDL = """
CREATE TABLE IF NOT EXISTS commune_conso_enaf (
  insee varchar(5) PRIMARY KEY,
  commune varchar(80) NOT NULL,
  conso_2011_2021_m2 double precision,
  conso_2021_2024_m2 double precision,
  hab_2011_2021_m2 double precision,
  hab_2021_2024_m2 double precision,
  source_nom text NOT NULL,
  source_url text NOT NULL,
  millesime varchar(80) NOT NULL,
  importe_le timestamptz NOT NULL DEFAULT now()
)"""


def _sum(row: dict, cols: list[str]) -> float:
    return sum(float(row.get(c) or 0) for c in cols)


def main() -> int:
    path = Path("/tmp/conso_enaf.csv")
    if not path.exists():
        urllib.request.urlretrieve(URL, path)
    first = path.read_text(encoding="utf-8").splitlines()[0]
    delim = ";" if ";" in first else ","
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=delim))
    r974 = [r for r in rows if (r.get("idcom") or "").startswith("974")]
    if len(r974) != 24:
        print(f"✗ attendu 24 communes 974, trouvé {len(r974)} — STOP (source à revérifier)")
        return 1
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute("DELETE FROM commune_conso_enaf")
        for r in r974:
            cur.execute(
                "INSERT INTO commune_conso_enaf (insee, commune, conso_2011_2021_m2, "
                "conso_2021_2024_m2, hab_2011_2021_m2, hab_2021_2024_m2, source_nom, "
                "source_url, millesime) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (r["idcom"].strip(), (r.get("idcomtxt") or "").strip(),
                 _sum(r, NAF_1121), _sum(r, NAF_2124), _sum(r, HAB_1121), _sum(r, HAB_2124),
                 SOURCE_NOM, URL, MILLESIME))
        conn.commit()
    print(f"✓ {len(r974)}/24 communes 974 ingérées dans commune_conso_enaf.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
