"""M39 P1.1 — enregistre la couche piscine aux conventions millésime M32 (dette #13).

Écriture DB HORS SCORING (catalogue `data_sources` uniquement, comme M32/M35) : ne touche NI
tier, NI run, NI cache scoring, NI vigilances M37. Idempotent, surgical (une seule ligne de
catalogue : « BD ORTHO 20 cm (IGN) », l'imagerie amont dont l'âge = l'âge du signal piscine).

Fait :
  1. Upsert de la SEULE source BD ORTHO (depuis seed_sources.SOURCES) si absente — jamais le
     catalogue entier (pas de churn sur les autres lignes).
  2. persist_millesime(only='ortho_piscine') → source_millesime/horizon/cadence sur data_sources.
  3. check_fraicheur → confirme que la couche est DATÉE sans déclencher d'alerte de retard
     (cadence pluriannuelle non bornée, comme gpu_plu).

Usage : PYTHONPATH=src python scripts/m39_register_source.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import select  # noqa: E402

from labuse.bascule_gardes import check_fraicheur  # noqa: E402
from labuse.db import session_scope  # noqa: E402
from labuse.ingestion import seed_sources  # noqa: E402
from labuse.ingestion.fraicheur import persist_millesime  # noqa: E402
from labuse.models import DataSource  # noqa: E402

DS_NAME = "BD ORTHO 20 cm (IGN)"


def main() -> None:
    row = next((r for r in seed_sources.SOURCES if r["name"] == DS_NAME), None)
    if row is None:
        raise SystemExit(f"Source introuvable dans seed_sources.SOURCES : {DS_NAME!r}")
    with session_scope() as s:
        existing = s.execute(select(DataSource).where(DataSource.name == DS_NAME)).scalar_one_or_none()
        if existing is None:
            s.add(DataSource(**row))
            print(f"  [1] data_sources : « {DS_NAME} » INSÉRÉE (catalogue).")
        else:
            for k, v in row.items():
                setattr(existing, k, v)
            print(f"  [1] data_sources : « {DS_NAME } » déjà présente — champs catalogue alignés.")
        s.flush()
        rendu = persist_millesime(s, only="ortho_piscine", commit=False)
        print(f"  [2] millésime persisté : {rendu}")
        s.commit()
    # 3) fraîcheur : DOIT être silencieuse pour l'ortho (cadence pluriannuelle non bornée)
    res = check_fraicheur()
    ortho_retard = [r for r in res["retards"] if "ORTHO" in r["source"].upper()]
    print(f"  [3] check_fraicheur : {res['n_retards']} retard(s) global ; ortho en retard = "
          f"{len(ortho_retard)} (attendu 0 — cadence pluriannuelle non évaluée).")
    print("✓ M39 P1.1 — couche piscine datée (data_sources), 0 écriture scoring.")


if __name__ == "__main__":
    main()
