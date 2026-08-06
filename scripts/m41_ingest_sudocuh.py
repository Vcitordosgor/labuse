"""M41 P1.1 — Ingestion Sudocuh (squelette du radar) aux conventions millésime.

Charge les 24 communes 974 de Sudocuh (état 31/12/2024, Licence Ouverte 2.0) dans une petite
table de PROVENANCE `sudocuh_procedures`, enregistre la source dans `data_sources`, et la date via
`persist_millesime`. `check_fraicheur` NE l'alarme PAS (cadence_norme absente, comme gpu_plu — un
Sudocuh d'un an n'est pas une faute : le registre curaté est la chair servie).

Écriture DB HORS SCORING (table de provenance + catalogue) : ne touche NI tier, NI run, NI cascade.
Idempotent. Source de vérité servie = config/veille_plu.yaml, PAS cette table (provenance/garde).

Usage : PYTHONPATH=src python scripts/m41_ingest_sudocuh.py
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.bascule_gardes import check_fraicheur  # noqa: E402
from labuse.db import engine, session_scope  # noqa: E402
from labuse.ingestion.fraicheur import persist_millesime  # noqa: E402

CSV = os.path.join(os.path.dirname(__file__), "..", "qa", "m41", "sudocuh_974_p0.csv")
MILLESIME_DATE = "2024-12-31"
DS_NAME = "Sudocuh (procédures d'urbanisme)"

DDL = """
CREATE TABLE IF NOT EXISTS sudocuh_procedures (
  insee                varchar(5) PRIMARY KEY,
  commune              text,
  du_opposable         text,
  du_en_cours          text,
  etat_detaille        text,
  prescription_proc    date,
  approbation_opp      date,
  millesime_date       date,
  ingested_at          timestamptz DEFAULT now()
);
"""


def _d(x):
    x = (x or "").strip()
    return x if x and x != "ABSENT" else None


def main() -> None:
    rows = []
    with open(CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    with engine().begin() as c:
        c.execute(text(DDL))
        for r in rows:
            c.execute(text("""
                INSERT INTO sudocuh_procedures
                  (insee,commune,du_opposable,du_en_cours,etat_detaille,prescription_proc,approbation_opp,millesime_date)
                VALUES (:i,:c,:o,:e,:d,:p,:a,:m)
                ON CONFLICT (insee) DO UPDATE SET commune=EXCLUDED.commune, du_opposable=EXCLUDED.du_opposable,
                  du_en_cours=EXCLUDED.du_en_cours, etat_detaille=EXCLUDED.etat_detaille,
                  prescription_proc=EXCLUDED.prescription_proc, approbation_opp=EXCLUDED.approbation_opp,
                  millesime_date=EXCLUDED.millesime_date, ingested_at=now()"""),
                {"i": r["insee"], "c": r["commune"], "o": _d(r["du_opposable"]),
                 "e": _d(r["etat_detaille"]), "d": _d(r.get("etat_detaille")),
                 "p": _d(r["prescription_proc_en_cours"]), "a": _d(r["approbation_du_vigueur"]),
                 "m": MILLESIME_DATE})
        n = c.execute(text("SELECT count(*) FROM sudocuh_procedures")).scalar()
    print(f"  [1] sudocuh_procedures : {n} communes 974 chargées (millésime {MILLESIME_DATE}).")
    # data_sources : upsert de la ligne catalogue (surgical)
    with session_scope() as s:
        exists = s.execute(text("SELECT 1 FROM data_sources WHERE name=:n"), {"n": DS_NAME}).scalar()
        if not exists:
            s.execute(text("""INSERT INTO data_sources (name,category,provider,access_type,status,
                reliability_level,documentation_url,endpoint_url,legal_notes,technical_notes,created_at,updated_at)
                VALUES (:n,'urbanisme','Ministère Cohésion des territoires / DGALN','téléchargement XLSX',
                'connecte','verifie','https://www.data.gouv.fr/datasets/planification-nationale-des-documents-durbanisme-plu-plui-cc-rnu-donnees-sudocuh-dernier-etat-des-lieux-annuel-au-31-decembre-2024',
                'https://www.data.gouv.fr/api/1/datasets/r/61541a0f-e9b0-43dc-bace-6c3905714400',
                'Licence Ouverte / Open Licence 2.0 — attribution Ministère.',
                'SuDocUH — suivi des procédures PLU/PLUi/CC/RNU. Squelette du radar M41 ; chair = config/veille_plu.yaml.',
                now(),now())"""), {"n": DS_NAME})
            print(f"  [2] data_sources : « {DS_NAME} » insérée.")
        else:
            print(f"  [2] data_sources : « {DS_NAME} » déjà présente.")
        rendu = persist_millesime(s, only="sudocuh", commit=False)
        print(f"  [3] millésime persisté : {rendu}")
        s.commit()
    res = check_fraicheur()
    alarme_sudo = [r for r in res["retards"] if "sudocuh" in r["source"].lower()]
    print(f"  [4] check_fraicheur : {res['n_retards']} retard(s) global ; sudocuh alarmé = "
          f"{len(alarme_sudo)} (attendu 0 — cadence non bornée, comme gpu_plu).")
    print("✓ M41 P1.1 — Sudocuh ingéré + daté, 0 écriture scoring.")


if __name__ == "__main__":
    main()
