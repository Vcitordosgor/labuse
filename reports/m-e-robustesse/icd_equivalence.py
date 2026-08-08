"""M-E / P2-7 — mesure d'équivalence ICD : implémentation SQL (batch) ↔ Python (fiche).

Rejoue les DEUX implémentations sur toutes les parcelles réelles (p_model_ext_dataset,
année servie) et compare icd + chaque groupe. Aucune écriture. Le SQL est généré depuis
ICD_GROUPS.sql_test (fidèle à _update_sql) ; le Python depuis compute_from_row.
"""
from __future__ import annotations

import os
from collections import Counter

from sqlalchemy import create_engine, text

from labuse.scoring.icd import ICD_GROUPS, compute_from_row

eng = create_engine(os.environ["LABUSE_DATABASE_URL"])

# Groupe ICD -> colonne(s) brute(s) lue(s) par _eval_group (pour les exemples).
GROUP_COL = {"residuel": "pct_potentiel", "zone_plu": "zone_plu", "vegetation": "canopee_pct",
             "prix_terrain": "med_pm2_terrain_36m", "prix_bati": "med_pm2_bati_36m",
             "filosofi": "filo_snv_pp", "tenure": "tenure_bin",
             "tendance_prix": "tendance_pm2_bati", "pente": "pente_moy_deg"}
RAW_COLS = list(GROUP_COL.values())

# Côté SQL : mêmes prédicats que _update_sql (les sql_test de ICD_GROUPS), aliasés par clé.
sql_group_exprs = ",\n  ".join(f"({g.sql_test}) AS sql_{g.key}" for g in ICD_GROUPS)
sql_icd = " + ".join(f"(CASE WHEN {g.sql_test} THEN {g.poids} ELSE 0 END)" for g in ICD_GROUPS)

with eng.connect() as c:
    annee = c.execute(text("SELECT max(annee) FROM p_model_ext_dataset")).scalar()
    q = text(f"""
        SELECT d.idu,
               {", ".join("d." + col for col in RAW_COLS)},
               ({sql_icd})::int AS sql_icd,
               {sql_group_exprs}
          FROM p_model_ext_dataset d
         WHERE d.annee = :annee
    """)
    rows = c.execute(q, {"annee": annee}).mappings().all()

n = len(rows)
icd_mismatch = 0
group_mismatch = Counter()          # group key -> nb parcelles où py_present != sql_present
examples: dict[str, list] = {}

for r in rows:
    row_dict = {col: r[col] for col in RAW_COLS}
    py_icd, py_detail = compute_from_row(row_dict)
    if py_icd != r["sql_icd"]:
        icd_mismatch += 1
    for g in ICD_GROUPS:
        py_present = py_detail[g.key]
        sql_present = bool(r[f"sql_{g.key}"])
        if py_present != sql_present:
            group_mismatch[g.key] += 1
            examples.setdefault(g.key, [])
            if len(examples[g.key]) < 3:
                col = GROUP_COL[g.key]
                examples[g.key].append((r["idu"], {col: row_dict[col]}, py_present, sql_present))


print(f"=== ICD équivalence SQL ↔ Python — année {annee}, {n} parcelles ===\n")
print(f"Parcelles où icd_python != icd_sql : {icd_mismatch} / {n}")
print("\nDésaccords par groupe (py_present != sql_present) :")
if not group_mismatch:
    print("  AUCUN — les deux implémentations coïncident sur toutes les parcelles.")
for g in ICD_GROUPS:
    k = group_mismatch.get(g.key, 0)
    flag = "  <-- DIVERGENCE" if k else ""
    print(f"  {g.key:14s} : {k}{flag}")
    for idu, cols, py, sql in examples.get(g.key, []):
        print(f"      {idu}  {cols}  py={py} sql={sql}")
