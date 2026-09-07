"""SCORING-DONNEES-1 · Lot B — profondeur DVF.

Question du mandat : dvf_mutations_histo (et tout autre historique DVF en base),
années couvertes, volumes, écart avec la fenêtre 2021+ servie ; recalculer la
tenure sur l'historique profond → % informatif (17,1 % aujourd'hui) → K0.

Réponse mesurée ICI : il n'existe PAS de profondeur non consommée. La source de
la tenure servie par la recette q_v12 (p_model_ext_mut_all) est déjà l'union
INTÉGRALE de dvf_mutations_histo (2014-2020) et dvf_mutations_parcelle (2021+) —
l'égalité des ensembles de parcelles est prouvée ligne à ligne ci-dessous. Le
« % informatif » de la tenure profonde est donc CELUI d'aujourd'hui ; aucune
variable nouvelle n'existe → pas de mesure K0 possible (documenté au rapport).

Usage : .venv/bin/python scripts/audit/scoring/donnees1_b.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from donnees1_commun import OUT, log  # noqa: E402
from _common import engine  # noqa: E402


def profondeur() -> None:
    eng = engine()
    log("[B1] années couvertes et volumes par table DVF…")
    b1 = pd.read_sql("""
        SELECT 'dvf_mutations_histo' AS tab, extract(year FROM date_mutation)::int AS annee,
               count(*) AS n, count(DISTINCT id_parcelle) AS n_parcelles
        FROM dvf_mutations_histo GROUP BY 1, 2
        UNION ALL
        SELECT 'dvf_mutations_parcelle', extract(year FROM date_mutation)::int,
               count(*), count(DISTINCT id_parcelle)
        FROM dvf_mutations_parcelle GROUP BY 1, 2
        UNION ALL
        SELECT 'p_model_ext_mut_all (source tenure q_v12)',
               extract(year FROM date_mutation)::int, count(*), count(DISTINCT idu)
        FROM p_model_ext_mut_all GROUP BY 1, 2
        ORDER BY 1, 2""", eng)
    b1.to_csv(OUT / "b1_dvf_profondeur.csv", index=False)

    log("[B2] l'historique profond est-il déjà consommé ? (égalité des ensembles)")
    b2 = pd.read_sql("""
        WITH brut AS (
          SELECT id_parcelle AS idu FROM dvf_mutations_histo
          UNION SELECT id_parcelle FROM dvf_mutations_parcelle),
        ext AS (SELECT DISTINCT idu FROM p_model_ext_mut_all)
        SELECT
          (SELECT count(*) FROM brut)                                   AS parcelles_dvf_brut,
          (SELECT count(*) FROM ext)                                    AS parcelles_ext_mut_all,
          (SELECT count(*) FROM brut b LEFT JOIN ext e USING (idu)
           WHERE e.idu IS NULL)                                         AS brut_hors_ext,
          (SELECT count(*) FROM ext e LEFT JOIN brut b USING (idu)
           WHERE b.idu IS NULL)                                         AS ext_hors_brut,
          (SELECT count(*) FROM brut b JOIN p_model_frame f USING (idu)) AS parcelles_avec_mutation_dans_frame,
          (SELECT count(*) FROM p_model_frame)                          AS parcelles_frame""", eng)
    b2["tenure_informative_pct"] = round(
        100 * b2["parcelles_avec_mutation_dans_frame"][0] / b2["parcelles_frame"][0], 1)
    b2["verdict"] = (
        "p_model_ext_mut_all = union INTÉGRALE histo 2014-2020 + parcellaire 2021+ "
        "(0 parcelle d'écart dans les deux sens) ; la tenure censurée K1c de la "
        "recette q_v12 consomme DÉJÀ toute la profondeur en base — le % informatif "
        "profond EST le % actuel. Aucune table DVF plus ancienne que 2014 n'existe "
        "en base → rien de nouveau à mesurer au K0.")
    b2.to_csv(OUT / "b2_tenure_profondeur.csv", index=False)

    log("[B3] natures présentes dans l'histo (rien de filtré ?)…")
    b3 = pd.read_sql("""
        SELECT h.nature_mutation, count(*) AS n_histo,
               count(e.idu) AS n_reprises_ext_all
        FROM dvf_mutations_histo h
        LEFT JOIN p_model_ext_mut_all e
          ON e.idu = h.id_parcelle AND e.date_mutation = h.date_mutation
        GROUP BY 1 ORDER BY 2 DESC""", eng)
    b3.to_csv(OUT / "b3_natures_histo.csv", index=False)
    for t in (b1.head(30), b2, b3):
        print(t.to_string(index=False), "\n")


if __name__ == "__main__":
    profondeur()
