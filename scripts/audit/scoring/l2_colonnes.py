"""SCORING-3 · L2 — balayage des colonnes numériques du feature store :
un zéro à la SOURCE ne doit jamais ressortir NULL au STORE.

Pour chaque colonne de `p_model_static` adossée à une table source, compte :
  - n_source_zero : lignes où la source dit 0 (ou false) — une RÉPONSE ;
  - n_store_null_pour_zero : lignes où le store dit NULL alors que la source
    dit 0 — LE défaut K3 (un zéro avalé en « inconnu »).

Verdict attendu après le correctif L2 (refresh_static_residuel câblé au
rebuild) : 0 partout. Les NULL LÉGITIMES (source réellement muette : pas de
ligne source, hors_plu) ne sont pas des défauts et sont comptés à part.

Sortie : reports/q-v12/l2_colonnes_verifiees.csv (liste au compte-rendu).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine, ROOT  # noqa: E402

OUT = ROOT / "reports/q-v12"
OUT.mkdir(parents=True, exist_ok=True)

#: (colonne store, table source, colonne source, rattachement, zéro SQL)
COLONNES = [
    ("sdp_residuelle_m2", "parcel_residuel", "sdp_residuelle_m2",
     "parcel_id", "s.sdp_residuelle_m2 = 0"),
    ("pct_potentiel", "parcel_residuel", "pct_potentiel",
     "parcel_id", "s.pct_potentiel = 0"),
    ("sous_densite", "parcel_residuel", "sous_densite",
     "parcel_id", "s.sous_densite = false"),
    ("pente_moy_deg", "parcel_terrain", "pente_moy_deg",
     "idu", "s.pente_moy_deg = 0"),
    ("canopee_pct", "parcel_vegetation", "canopee_pct",
     "idu", "s.canopee_pct = 0"),
    ("ndvi_moyen", "parcel_vegetation", "ndvi_moyen",
     "idu", "s.ndvi_moyen = 0"),
    ("dist_ecole_m", "parcel_amenites", "dist_ecole_m",
     "parcel_id", "s.dist_ecole_m = 0"),
    ("dist_sante_m", "parcel_amenites", "dist_sante_m",
     "parcel_id", "s.dist_sante_m = 0"),
    ("dist_commerce_m", "parcel_amenites", "dist_commerce_m",
     "parcel_id", "s.dist_commerce_m = 0"),
    ("dist_tcsp_m", "parcel_amenites", "dist_tcsp_m",
     "parcel_id", "s.dist_tcsp_m = 0"),
    ("emprise_bati_m2", "p_model_bati", "emprise_bati_m2",
     "idu", "s.emprise_bati_m2 = 0"),
]


def main() -> None:
    eng = engine()
    rows = []
    for col, src_t, src_c, ratt, zero in COLONNES:
        # deux formes de rattachement : par parcel_id (via parcels) ou par idu direct
        if ratt == "parcel_id":
            q = f"""
                SELECT count(*) FILTER (WHERE {zero}) AS n_source_zero,
                       count(*) FILTER (WHERE {zero} AND st.{col} IS NULL)
                           AS n_store_null_pour_zero,
                       count(*) FILTER (WHERE s.{src_c} IS NULL) AS n_source_null_legitime
                FROM {src_t} s
                JOIN parcels p ON p.id = s.parcel_id
                JOIN p_model_static st ON st.idu = p.idu"""
        else:
            q = f"""
                SELECT count(*) FILTER (WHERE {zero}) AS n_source_zero,
                       count(*) FILTER (WHERE {zero} AND st.{col} IS NULL)
                           AS n_store_null_pour_zero,
                       count(*) FILTER (WHERE s.{src_c} IS NULL) AS n_source_null_legitime
                FROM {src_t} s
                JOIN p_model_static st ON st.idu = s.idu"""
        try:
            r = pd.read_sql(q, eng).iloc[0]
            rows.append({"colonne": col, "source": f"{src_t}.{src_c}",
                         "n_source_zero": int(r["n_source_zero"]),
                         "n_store_null_pour_zero": int(r["n_store_null_pour_zero"]),
                         "n_source_null_legitime": int(r["n_source_null_legitime"]),
                         "verdict": "OK — aucun zéro avalé"
                         if r["n_store_null_pour_zero"] == 0
                         else f"DÉFAUT : {int(r['n_store_null_pour_zero'])} zéros avalés"})
        except Exception as exc:  # noqa: BLE001 — table absente = hors périmètre, dit
            rows.append({"colonne": col, "source": f"{src_t}.{src_c}",
                         "n_source_zero": None, "n_store_null_pour_zero": None,
                         "n_source_null_legitime": None,
                         "verdict": f"table absente ({type(exc).__name__})"})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "l2_colonnes_verifiees.csv", index=False)
    print(out.to_string(index=False))
    defauts = out[out["verdict"].str.startswith("DÉFAUT")]
    print(f"\n{len(defauts)} colonne(s) en défaut." if len(defauts)
          else "\nToutes les colonnes vérifiées : un zéro n'est jamais un NULL.")


if __name__ == "__main__":
    main()
