"""M-E / P2-7 — équivalence ICD : implémentation SQL (batch, source unique de vérité)
↔ implémentation Python de référence (`compute_from_row`).

L'ICD est décrit par une SEULE liste `ICD_GROUPS`, mais chaque groupe porte DEUX prédicats
maintenus à la main : `sql_test` (chaîne SQL, jouée par `_update_sql`/`backfill_run`) et la
branche correspondante de `_eval_group` (Python de référence, utilisée en fiche/tests). Rien
dans le typage ne garantit qu'ils restent d'accord — c'est exactement le risque « deux chiffres
pour une même réalité » que M53 traque. Ce test verrouille l'équivalence.

Méthode : on sème dans un temp table calqué sur `p_model_ext_dataset` des lignes qui couvrent
les états qui pourraient FAIRE diverger les deux implémentations (NULL, 'inconnu', chaîne vide,
0, négatif, valeur nominale), puis on compare, par groupe ET sur l'ICD total, le Python et le
VRAI SQL joué par Postgres. La preuve à grande échelle (0/431 663 sur le run servi) est dans
reports/m-e-robustesse/icd_equivalence.py.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse.scoring.icd import ICD_GROUPS, POIDS_TOTAL, compute_from_row

# Colonnes lues par les prédicats ICD, avec un type compatible p_model_ext_dataset.
_COLS = [
    ("pct_potentiel", "integer"),
    ("zone_plu", "varchar"),
    ("canopee_pct", "double precision"),
    ("med_pm2_terrain_36m", "double precision"),
    ("med_pm2_bati_36m", "double precision"),
    ("filo_snv_pp", "double precision"),
    ("tenure_bin", "text"),
    ("tendance_pm2_bati", "double precision"),
    ("pente_moy_deg", "real"),
]
_COL_NAMES = [c for c, _ in _COLS]

# Lignes représentatives : chaque dict = valeurs par colonne (clé absente → NULL).
_ROWS: list[dict] = [
    # 1. tout renseigné (nominal) → ICD attendu = 100
    {"pct_potentiel": 42, "zone_plu": "U", "canopee_pct": 12.0, "med_pm2_terrain_36m": 300.0,
     "med_pm2_bati_36m": 2500.0, "filo_snv_pp": 21000.0, "tenure_bin": "8-15",
     "tendance_pm2_bati": 1.03, "pente_moy_deg": 4.5},
    # 2. tout NULL → ICD = 0
    {},
    # 3. les deux groupes textuels à 'inconnu' → ABSENTS ; le reste présent
    {"pct_potentiel": 0, "zone_plu": "inconnu", "canopee_pct": 0.0, "med_pm2_terrain_36m": 0.0,
     "med_pm2_bati_36m": 0.0, "filo_snv_pp": 0.0, "tenure_bin": "inconnu",
     "tendance_pm2_bati": 0.0, "pente_moy_deg": 0.0},
    # 4. chaîne VIDE sur les groupes textuels — piège NULL/''/inconnu (doit compter PRÉSENT
    #    des deux côtés : '' IS NOT NULL AND '' <> 'inconnu')
    {"pct_potentiel": 7, "zone_plu": "", "canopee_pct": 3.0, "med_pm2_terrain_36m": 150.0,
     "med_pm2_bati_36m": 1800.0, "filo_snv_pp": 15000.0, "tenure_bin": "",
     "tendance_pm2_bati": 0.9, "pente_moy_deg": 2.0},
    # 5. valeurs 0 / négatives sur les groupes numériques → PRÉSENT (test = « n'est pas NULL »)
    {"pct_potentiel": -1, "zone_plu": "AUs", "canopee_pct": -2.0, "med_pm2_terrain_36m": -10.0,
     "med_pm2_bati_36m": 0.0, "filo_snv_pp": -5.0, "tenure_bin": "0-2",
     "tendance_pm2_bati": -0.5, "pente_moy_deg": 0.0},
    # 6. mélange épars : un présent par-ci, un absent par-là
    {"pct_potentiel": 90, "canopee_pct": 8.0, "filo_snv_pp": 30000.0, "pente_moy_deg": 12.0},
]


def _sql_select() -> str:
    """SELECT qui joue les MÊMES prédicats que _update_sql (sql_test de ICD_GROUPS, alias d)."""
    icd_expr = " + ".join(
        f"(CASE WHEN {g.sql_test} THEN {g.poids} ELSE 0 END)" for g in ICD_GROUPS)
    group_exprs = ", ".join(f"({g.sql_test}) AS grp_{g.key}" for g in ICD_GROUPS)
    return (f"SELECT rid, ({icd_expr})::int AS sql_icd, {group_exprs} "
            f"FROM tmp_icd_equiv d ORDER BY rid")


def test_icd_sql_python_equivalence(db_session):
    """Le prédicat SQL et le prédicat Python coïncident, groupe par groupe et sur l'ICD total,
    sur toutes les lignes représentatives (dont les pièges NULL/'inconnu'/'')."""
    cols_ddl = ", ".join(f"{c} {t}" for c, t in _COLS)
    db_session.execute(text(f"CREATE TEMP TABLE tmp_icd_equiv (rid int, {cols_ddl})"))
    for i, r in enumerate(_ROWS):
        vals = {"rid": i, **{c: r.get(c) for c in _COL_NAMES}}
        placeholders = ", ".join(f":{c}" for c in ["rid", *_COL_NAMES])
        db_session.execute(
            text(f"INSERT INTO tmp_icd_equiv (rid, {', '.join(_COL_NAMES)}) VALUES ({placeholders})"),
            vals)

    sql_rows = {row["rid"]: row for row in
                db_session.execute(text(_sql_select())).mappings().all()}

    for i, r in enumerate(_ROWS):
        py_icd, py_detail = compute_from_row(r)
        sql_row = sql_rows[i]
        assert py_icd == sql_row["sql_icd"], f"ligne {i}: icd py={py_icd} != sql={sql_row['sql_icd']}"
        for g in ICD_GROUPS:
            py_present = py_detail[g.key]
            sql_present = bool(sql_row[f"grp_{g.key}"])
            assert py_present == sql_present, (
                f"ligne {i}, groupe {g.key}: py={py_present} != sql={sql_present} "
                f"(valeur brute={r.get(g.sql_test.split('.')[1].split(' ')[0], None)!r})")

    # bornes attendues des lignes témoins (nominal=100, tout-NULL=0)
    assert compute_from_row(_ROWS[0])[0] == POIDS_TOTAL == 100
    assert compute_from_row(_ROWS[1])[0] == 0
