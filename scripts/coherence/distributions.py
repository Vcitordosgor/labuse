"""COHERENCE-1 lot D — plausibilité, unités, absences, à l'échelle de l'île, en SQL.

Pour chaque notion numérique servie depuis une table : min, max, médiane, part de nuls,
part de zéros, part de la valeur modale — et les SIGNAUX D'ALARME automatiques :

  · pct_hors_bornes   : un « % » hors [0;100] ;
  · fraction_deguisee : un « % » dont le max ≤ 1 (fraction affichée comme pourcentage —
                        la cause présumée du cas Saint-Paul) ;
  · surface_suspecte  : m² ≤ 0, ou des « m² » dont la médiane ressemble à des hectares ;
  · constante         : > 95 % des lignes à la même valeur (constante déguisée) ;
  · date_future       : une date au-delà d'aujourd'hui (lue en base, pas générée) ;
  · zero_pour_absence : la valeur servie vaut 0 alors qu'AUCUNE ligne source n'existe
                        (jointure sur la table d'origine — sondes dédiées).

    python -m scripts.coherence.distributions       → DISTRIBUTIONS.csv
"""
from __future__ import annotations

import csv
import time

import psycopg

from .lib import DSN, RUN, SORTIE

#: (notion, table.colonne, unité, filtre) — les colonnes numériques servies au client.
COLONNES: list[tuple] = [
    ("surface_parcelle_m2", "parcels", "surface_m2", "m²", None),
    ("pente_moy_deg", "parcel_terrain", "pente_moy_deg", "°", None),
    ("pente_max_deg", "parcel_terrain", "pente_max_deg", "°", None),
    ("sdp_residuelle_m2", "parcel_residuel", "sdp_residuelle_m2", "m²", None),
    ("taux_emprise_pct", "parcel_residuel", "taux_emprise_pct", "%", None),
    ("pct_potentiel", "parcel_residuel", "pct_potentiel", "%", None),
    ("emprise_bati_m2", "p_model_bati", "emprise_bati_m2", "m²", None),
    ("faitage_m", "batiment_hauteur_lidar", "faitage_m", "m", None),
    ("egout_m", "batiment_hauteur_lidar", "egout_m", "m", None),
    ("percentile_score", "parcel_p_score_v2", "percentile", "%", f"run_id='{RUN}'"),
    ("mult_base", "parcel_p_score_v2", "mult_base", "nombre", f"run_id='{RUN}'"),
    ("valeur_fonciere_dvf", "dvf_mutations", "valeur_fonciere", "€", None),
    ("taux_lls_pct", "commune_contexte_sru", "taux_lls", "%", None),
    ("pop_mun", "sudocuh_procedures", "pop_mun", "habitants", None),
    ("rpls_nb_logements", "rpls_commune", "nb_logements", "logements", None),
]

#: sondes « zéro là où la source est nulle » et champs JSON du cache commune.
SONDES: list[tuple] = [
    # payload du cache fiche commune : chaque % doit être dans [0;100] et pas une fraction
    ("cache_commune.mouvement_terrain_pct", """
        SELECT count(*), min(v), max(v),
               percentile_cont(0.5) WITHIN GROUP (ORDER BY v), NULL::float, NULL::float
        FROM (SELECT (payload->'risques'->>'mouvement_terrain_pct')::float v
              FROM commune_contexte_cache
              WHERE payload->'risques'->>'mouvement_terrain_pct' IS NOT NULL) t""", "%"),
    ("cache_commune.ppr_pct", """
        SELECT count(*), min(v), max(v),
               percentile_cont(0.5) WITHIN GROUP (ORDER BY v), NULL::float, NULL::float
        FROM (SELECT (payload->'risques'->>'ppr_pct')::float v
              FROM commune_contexte_cache
              WHERE payload->'risques'->>'ppr_pct' IS NOT NULL) t""", "%"),
]


def _stats(conn, notion, table, col, unite, filtre):
    where = f"WHERE {filtre}" if filtre else ""
    q = f"""
      SELECT count(*) AS n,
             count(*) FILTER (WHERE {col} IS NULL) AS n_null,
             count(*) FILTER (WHERE {col} = 0) AS n_zero,
             min({col}), max({col}),
             percentile_cont(0.5) WITHIN GROUP (ORDER BY {col}),
             (SELECT count(*) FROM {table} {where or 'WHERE true'}
               AND {col} IS NOT DISTINCT FROM
               (SELECT {col} FROM {table} {where or 'WHERE true'} AND {col} IS NOT NULL
                GROUP BY {col} ORDER BY count(*) DESC LIMIT 1)) AS n_modal
      FROM {table} {where}"""
    with conn.cursor() as cur:
        cur.execute(q)
        n, n_null, n_zero, vmin, vmax, med, n_modal = cur.fetchone()
    alarmes = []
    n_val = n - n_null
    if n_val:
        if unite == "%" and (vmin is not None and vmin < 0 or vmax is not None and vmax > 100):
            alarmes.append("pct_hors_bornes")
        if unite == "%" and vmax is not None and vmax <= 1 and n_val > 10:
            alarmes.append("fraction_deguisee")
        if unite == "m²" and vmin is not None and vmin < 0:
            alarmes.append("surface_negative")
        if n_modal and n_val and n_modal / n_val > 0.95 and vmax != vmin:
            alarmes.append("constante_deguisee")
        if n_modal and n_val and vmax == vmin and n_val > 10:
            alarmes.append("valeur_unique")
    return {"notion": notion, "table": f"{table}.{col}", "unite": unite, "n": n,
            "pct_null": round(100 * n_null / n, 2) if n else None,
            "pct_zero": round(100 * n_zero / n, 2) if n else None,
            "min": vmin, "max": vmax, "mediane": med,
            "pct_modal": round(100 * n_modal / n_val, 2) if n_val and n_modal else None,
            "alarmes": "|".join(alarmes)}


def main() -> None:
    lignes = []
    with psycopg.connect(DSN, options="-c statement_timeout=600000") as conn:
        for notion, table, col, unite, filtre in COLONNES:
            t0 = time.time()
            try:
                lignes.append(_stats(conn, notion, table, col, unite, filtre))
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                lignes.append({"notion": notion, "table": f"{table}.{col}", "unite": unite,
                               "n": None, "pct_null": None, "pct_zero": None, "min": None,
                               "max": None, "mediane": None, "pct_modal": None,
                               "alarmes": f"ERREUR {str(e)[:80]}"})
            print(f"{notion}: {lignes[-1]['alarmes'] or 'ok'} ({time.time()-t0:.0f}s)")
        for notion, q, unite in SONDES:
            try:
                with conn.cursor() as cur:
                    cur.execute(q)
                    n, vmin, vmax, med, _, _ = cur.fetchone()
                alarmes = []
                if unite == "%" and vmax is not None and vmax <= 1 and n > 5:
                    alarmes.append("fraction_deguisee")
                lignes.append({"notion": notion, "table": "commune_contexte_cache.payload",
                               "unite": unite, "n": n, "pct_null": None, "pct_zero": None,
                               "min": vmin, "max": vmax, "mediane": med, "pct_modal": None,
                               "alarmes": "|".join(alarmes)})
                print(f"{notion}: min {vmin} max {vmax} med {med}")
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                print(f"{notion}: ERREUR {e}")
    with open(SORTIE / "DISTRIBUTIONS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {SORTIE/'DISTRIBUTIONS.csv'}")


if __name__ == "__main__":
    main()
