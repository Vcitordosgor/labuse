"""LOT 11 (data-gap) — RPLS : parc locatif social par commune (SDES, via API Dido).

Source (VÉRIFIÉE live 10/07/2026) : « Données détaillées au logement du RPLS », datafile Dido
`f3c2f2cb-8fb1-40fd-8733-964247744c9a`, millésime 2025-01, FILTRÉ SERVEUR sur le 974 :
  https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/
  f3c2f2cb-8fb1-40fd-8733-964247744c9a/csv?millesime=2025-01&withColumnName=true&DEP_CODE=eq:974
→ 87 553 logements sociaux au 01/01/2025 (une ligne par logement).

Agrégation COMMUNE → table `rpls_commune` (nb logements, année de construction médiane,
% en QPV, surface habitable moyenne). Contexte marché fiche/module bailleur — pas de scoring.

Usage : LABUSE_DATABASE_URL=… python scripts/ingest_rpls.py [chemin_csv_deja_telecharge]
"""
from __future__ import annotations

import collections
import csv
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402

URL = ("https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/"
       "f3c2f2cb-8fb1-40fd-8733-964247744c9a/csv?millesime=2025-01"
       "&withColumnName=true&DEP_CODE=eq:974")

DDL = """
CREATE TABLE IF NOT EXISTS rpls_commune (
  insee            varchar(5) PRIMARY KEY,
  commune          varchar(64),
  millesime        varchar(8) NOT NULL,
  nb_logements     integer NOT NULL,
  construct_median integer,
  pct_qpv          numeric(4,1),
  surfhab_moy      numeric(5,1),
  computed_at      timestamptz NOT NULL DEFAULT now()
)"""


def main() -> None:
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print("téléchargement RPLS 974 (Dido, filtré serveur)…")
        path = tempfile.mktemp(suffix=".csv")
        with httpx.Client(timeout=600.0, follow_redirects=True) as c:
            r = c.get(URL)
            r.raise_for_status()
            Path(path).write_text(r.text)
    agg = collections.defaultdict(lambda: {"n": 0, "constr": [], "qpv": 0, "surf": [], "lib": ""})
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            insee = (r.get("DEPCOM") or "").strip('"')
            if not insee:
                continue
            d = agg[insee]
            d["n"] += 1
            d["lib"] = r.get("LIBCOM") or d["lib"]
            if (r.get("CONSTRUCT") or "").isdigit():
                d["constr"].append(int(r["CONSTRUCT"]))
            if (r.get("QPV_CODE") or "").strip():
                d["qpv"] += 1
            try:
                d["surf"].append(float((r.get("SURFHAB") or "").replace(",", ".")))
            except ValueError:
                pass
    with session_scope() as s:
        s.execute(text(DDL))
        s.execute(text("TRUNCATE rpls_commune"))
        for insee, d in sorted(agg.items()):
            s.execute(text(
                "INSERT INTO rpls_commune (insee, commune, millesime, nb_logements, "
                "construct_median, pct_qpv, surfhab_moy) "
                "VALUES (:i, :c, '2025-01', :n, :cm, :q, :sm)"), {
                "i": insee, "c": d["lib"], "n": d["n"],
                "cm": int(statistics.median(d["constr"])) if d["constr"] else None,
                "q": round(100 * d["qpv"] / d["n"], 1),
                "sm": round(sum(d["surf"]) / len(d["surf"]), 1) if d["surf"] else None})
        s.commit()
    print(f"✓ rpls_commune : {len(agg)} communes, {sum(d['n'] for d in agg.values())} logements")


if __name__ == "__main__":
    main()
