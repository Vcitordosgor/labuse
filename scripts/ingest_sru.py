#!/usr/bin/env python3
"""Ingestion SRU (mandat contexte-commune, vague 1) — bilan officiel DHUP par commune.

Source (vérifiée, extrait relu ligne à ligne) :
  « Communes et inventaire SRU » — data.gouv.fr, Ministère de la Transition écologique (DHUP)
  https://www.data.gouv.fr/datasets/communes-et-inventaire-sru
  CSV v2 du 18/12/2025 — périmètre SRU au 01/01/2025, INVENTAIRE LLS AU 01/01/2024,
  prélèvements 2025. Licence Ouverte v2.0. Encodage Windows-1252, séparateur « ; ».

Statuts restitués (l'exemption EST un statut du fichier, pas une invention) :
  conforme | deficitaire | carencee | exemptee — et « non_soumise » si une commune 974
  n'apparaissait pas au périmètre (aucune au millésime 2025 : les 24 sont soumises).
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

import psycopg

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
URL = ("https://static.data.gouv.fr/resources/communes-et-inventaire-sru/"
       "20251219-143258/donnees-sru-data-gouv-2025-v2.csv")
SOURCE_NOM = "Communes et inventaire SRU (DHUP) — inventaire au 01/01/2024, v2 du 18/12/2025"
MILLESIME = "inventaire LLS 01/01/2024 · périmètre 01/01/2025 · prélèvement 2025"


def fnum(v: str) -> float | None:
    v = (v or "").strip().replace(" ", "").replace(" ", "").replace(",", ".").replace("€", "").replace("%", "")
    try:
        return float(v)
    except ValueError:
        return None


def main() -> int:
    path = Path("/tmp/sru2025.csv")
    if not path.exists():
        urllib.request.urlretrieve(URL, path)
    rows = list(csv.DictReader(path.read_text(encoding="windows-1252").splitlines(), delimiter=";"))
    r974 = [r for r in rows if (r.get("Code_INSEE_commune") or "").startswith("974")]
    if len(r974) != 24:
        print(f"✗ attendu 24 communes 974, trouvé {len(r974)} — STOP (source à revérifier)")
        return 1
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM commune_contexte_sru")
        for r in r974:
            carencee = (r.get("Commune_carencée") or "").strip() == "1"
            deficitaire = (r.get("commune_deficitaire") or "").strip() == "1"
            exemptee = (r.get("Commune_exemptée_2023_2025") or "").strip() == "1"
            statut = ("carencee" if carencee else "exemptee" if exemptee
                      else "deficitaire" if deficitaire else "conforme")
            cur.execute("""
                INSERT INTO commune_contexte_sru
                  (insee, commune, millesime, taux_lls, objectif_pct, statut, prelevement_eur,
                   detail, source_nom, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)""", (
                r["Code_INSEE_commune"].strip(),
                r["Nom_commune"].strip().title(),
                MILLESIME,
                fnum(r.get("Taux_SRU_au_01_01_2024", "")),
                fnum(r.get("Taux_cible_commune_2023_2025", "")),
                statut,
                fnum(r.get("Prélèvement_net_2025_dont_majoration", "")),
                # le nombre de LLS (colonne avec espace parasite dans la source, fidèlement lue)
                json.dumps({
                    "nb_lls": fnum(r.get("Nombre_lls_ Inventaire_au_01_01_2024", "")),
                    "epci": (r.get("Nom_EPCI") or "").strip(),
                    "population_2025": fnum(r.get("Population_municipale_01_01_2025", "")),
                }),
                SOURCE_NOM, URL,
            ))
        cur.execute("SELECT statut, count(*) FROM commune_contexte_sru GROUP BY 1 ORDER BY 2 DESC")
        for st, n in cur.fetchall():
            print(f"  {st}: {n}")
        conn.commit()
    print("✓ SRU ingéré (24 communes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
