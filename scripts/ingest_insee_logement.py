#!/usr/bin/env python3
"""Ingestion INSEE RP Logement 2023 (mandat contexte-commune, vague 4) — par commune 974.

Source (vérifiée, valeurs relues) :
  « Logement en 2023 » — INSEE, recensement de la population, chiffres détaillés,
  base comparateur de communes, PUBLIÉ LE 25/06/2026 (dernier millésime disponible).
  https://www.insee.fr/fr/statistiques/8997194?sommaire=9003154
  Fichier : base_cc_logement_2023.xlsx (feuille COM_2023, valeurs PONDÉRÉES → décimales,
  arrondies à l'entier à l'affichage). Licence Ouverte / Etalab 2.0 —
  mention « Source : Insee, RP 2023, exploitation principale ».

La « typologie » restituée = répartition par NOMBRE DE PIÈCES (1p…5p+), proxy honnête du
T1…T5+ (l'INSEE ne publie pas la typologie Tn stricte à la commune) — libellé exact au volet.
"""
from __future__ import annotations

import json
import sys

import openpyxl
import psycopg

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
XLSX = "/tmp/insee_log/base_cc_logement_2023.xlsx"
SOURCE_NOM = "INSEE RP 2023 — base comparateur logement (publié 25/06/2026)"
SOURCE_URL = "https://www.insee.fr/fr/statistiques/8997194?sommaire=9003154"
MILLESIME = "RP 2023 (exploitation principale, géographie 01/01/2026)"

# indices de colonnes (feuille COM_2023, en-têtes vérifiés)
COL = {"code": 0, "lib": 1, "log": 2, "rp": 3, "rsec": 4, "vac": 5, "maison": 6, "appart": 7,
       "p1": 8, "p2": 9, "p3": 10, "p4": 11, "p5": 12, "prop": 63, "loc": 64, "hlm": 65}


def main() -> int:
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb["COM_2023"]
    n = 0
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM commune_insee_logement")
        for row in ws.iter_rows(min_row=2, values_only=True):
            code = str(row[COL["code"]] or "")
            if not code.startswith("974"):
                continue
            g = lambda k: float(row[COL[k]] or 0)
            rp = g("rp") or 1.0
            logt = g("log") or 1.0
            cur.execute("""
                INSERT INTO commune_insee_logement
                  (insee, commune, millesime, logements, res_principales, res_secondaires,
                   vacants, proprietaires_pct, locataires_pct, maisons_pct, apparts_pct,
                   typologie, source_nom, source_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""", (
                code, str(row[COL["lib"]]), MILLESIME,
                round(g("log")), round(rp), round(g("rsec")), round(g("vac")),
                round(100 * g("prop") / rp, 1), round(100 * g("loc") / rp, 1),
                round(100 * g("maison") / logt, 1), round(100 * g("appart") / logt, 1),
                json.dumps({
                    "libelle": "répartition des résidences principales par nombre de pièces "
                               "(proxy T1…T5+, l'INSEE ne publie pas la typologie Tn à la commune)",
                    "p1": round(g("p1")), "p2": round(g("p2")), "p3": round(g("p3")),
                    "p4": round(g("p4")), "p5p": round(g("p5")),
                    "hlm_louees_vides": round(g("hlm")),
                    "vacance_pct": round(100 * g("vac") / logt, 1),
                }),
                SOURCE_NOM, SOURCE_URL))
            n += 1
        conn.commit()
    print(f"✓ INSEE logement 2023 ingéré : {n} communes 974" + (" — ✗ ATTENDU 24 !" if n != 24 else ""))
    return 0 if n == 24 else 1


if __name__ == "__main__":
    sys.exit(main())
