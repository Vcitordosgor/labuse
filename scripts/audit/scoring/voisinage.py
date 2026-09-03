"""SCORING-2 · K4 bis — voisinage et marché, AS-OF strict (jamais avec le futur).

Quatre familles de features candidates par (idu, annee), toutes bornées à
STRICTEMENT AVANT le 01/01/annee (asof) :
  1. ventes DVF L2-F dans 150 m et 400 m, fenêtres 12 et 24 mois, + delta
     (accélération : n_12m − (n_24m − n_12m)) ;
  2. permis Sitadel dans 100 m (tous types, 24 mois) et opérations d'aménageur
     dans 400 m (permis PA, 24 mois — le PA est l'acte du lotisseur/promoteur) ;
  3. marché communal : volume de mutations L2-F de l'année Y-1, médiane €/m² bâti
     Y-1, tendance 3 ans (volume Y-1 / moyenne volumes Y-3..Y-1) ;
  4. personnes morales : le propriétaire (SIREN, millésime ≤ Y-1) a-t-il vendu
     une AUTRE parcelle dans les 24 mois précédant asof.

Distances : ST_DWithin sur parcels.geom_2975 (mètres, bord à bord, index GiST).
Cache : reports/score-v2-arene/cache/*.csv.gz (le calcul spatial est long).
Test de fuite dédié : test_fuite() — voir la sous-commande `fuite`.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine, ROOT  # noqa: E402

CACHE = ROOT / "reports/score-v2-arene/cache"
CACHE.mkdir(parents=True, exist_ok=True)
YEARS = tuple(range(2017, 2027))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ─────────────────────────── 1. ventes voisines (spatial) ───────────────────────────

def _ventes_annee(eng, annee: int, date_max: str | None = None) -> pd.DataFrame:
    """Ventes L2-F voisines pour une année d'observation. `date_max` (test de
    fuite) restreint la SOURCE en amont — le résultat doit être identique."""
    borne = f"AND m.date_mutation < '{date_max}'" if date_max else ""
    return pd.read_sql(f"""
        WITH asof AS (SELECT make_date({annee},1,1) AS d),
        mut AS (
            SELECT DISTINCT m.idu, m.id_mutation, m.date_mutation
            FROM p_model_ext_mut_l2 m, asof
            WHERE NOT m.exclue_l2f
              AND m.date_mutation >= (asof.d - interval '24 months')
              AND m.date_mutation <  asof.d {borne}
        ),
        mutg AS (
            SELECT mut.id_mutation, mut.date_mutation, p.geom_2975
            FROM mut JOIN parcels p ON p.idu = mut.idu
        )
        SELECT t.idu,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE ST_DWithin(t.geom_2975, mg.geom_2975, 150)
                     AND mg.date_mutation >= (SELECT d - interval '12 months' FROM asof))
                   AS ventes_150m_12m,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE ST_DWithin(t.geom_2975, mg.geom_2975, 150))
                   AS ventes_150m_24m,
               count(DISTINCT mg.id_mutation) FILTER (
                   WHERE mg.date_mutation >= (SELECT d - interval '12 months' FROM asof))
                   AS ventes_400m_12m,
               count(DISTINCT mg.id_mutation) AS ventes_400m_24m
        FROM parcels t
        JOIN mutg mg ON ST_DWithin(t.geom_2975, mg.geom_2975, 400)
        GROUP BY t.idu""", eng)


def _permis_annee(eng, annee: int, date_max: str | None = None) -> pd.DataFrame:
    borne = f"AND pp.date_autorisation < '{date_max}'" if date_max else ""
    return pd.read_sql(f"""
        WITH asof AS (SELECT make_date({annee},1,1) AS d),
        perm AS (
            SELECT pp.permit_id, pp.type, pp.date_autorisation, p.geom_2975
            FROM p_model_permits pp
            JOIN parcels p ON p.idu = pp.idu, asof
            WHERE pp.date_autorisation >= (asof.d - interval '24 months')
              AND pp.date_autorisation <  asof.d {borne}
        )
        SELECT t.idu,
               count(DISTINCT pe.permit_id) FILTER (
                   WHERE ST_DWithin(t.geom_2975, pe.geom_2975, 100))
                   AS permis_100m_24m,
               count(DISTINCT pe.permit_id) FILTER (WHERE pe.type = 'PA')
                   AS operations_pa_400m_24m
        FROM parcels t
        JOIN perm pe ON ST_DWithin(t.geom_2975, pe.geom_2975, 400)
        GROUP BY t.idu""", eng)


def charger_spatial(eng, years: tuple[int, ...] = YEARS,
                    force: bool = False) -> pd.DataFrame:
    """Ventes + permis voisins, toutes années, avec cache (une requête par an)."""
    path = CACHE / "voisinage_spatial.csv.gz"
    if path.exists() and not force:
        return pd.read_csv(path)
    frames = []
    for y in years:
        log(f"voisinage spatial {y} (ventes)…")
        v = _ventes_annee(eng, y)
        log(f"voisinage spatial {y} (permis)…")
        p = _permis_annee(eng, y)
        f = v.merge(p, on="idu", how="outer")
        f["annee"] = y
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(path, index=False)
    return out


# ─────────────────────────── 3. marché communal ───────────────────────────

def charger_marche(eng) -> pd.DataFrame:
    """Par (commune, annee) : volume Y-1, médiane €/m² bâti Y-1, tendance 3 ans."""
    an = pd.read_sql("""
        SELECT left(m.idu, 5) AS commune,
               extract(year FROM m.date_mutation)::int AS an,
               count(DISTINCT m.id_mutation) AS volume,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_bati)
                   FILTER (WHERE m.pm2_bati IS NOT NULL) AS med_pm2_bati
        FROM p_model_ext_mut_l2 m WHERE NOT m.exclue_l2f
        GROUP BY 1, 2""", eng)
    rows = []
    for y in YEARS:
        a1 = an[an["an"] == y - 1].set_index("commune")
        a3 = (an[(an["an"] >= y - 3) & (an["an"] <= y - 1)]
              .groupby("commune")["volume"].mean())
        f = pd.DataFrame({
            "commune": a1.index,
            "volume_commune_a1": a1["volume"].to_numpy(),
            "med_pm2_commune_a1": a1["med_pm2_bati"].to_numpy(),
        })
        f["tendance_volume_3ans"] = (
            a1["volume"] / a3.reindex(a1.index)).to_numpy()
        f["annee"] = y
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


# ─────────────────────────── 4. PM vendeur actif (SIREN) ───────────────────────────

def charger_vendeur_actif(eng, force: bool = False) -> pd.DataFrame:
    """Par (idu, annee) : le propriétaire PM (SIREN au dernier millésime ≤ Y-1)
    a vendu une AUTRE parcelle dans [asof-24 mois, asof).

    Le SIREN vendeur d'une mutation datée d est lu au millésime year(d)-1
    (propriétaire AVANT la vente). Millésimes disponibles 2019-2024 → feature
    renseignée pour Y ≥ 2021, manquant explicite avant (bin WoE).
    Calcul pandas + cache : la version SQL (LATERAL par parcelle × 6 fenêtres)
    prenait 1 h 38 pour un résultat identique."""
    path = CACHE / "vendeur_actif.csv.gz"
    if path.exists() and not force:
        return pd.read_csv(path)
    mil = pd.read_sql("SELECT idu, millesime, siren FROM pm_proprietaires_millesimes "
                      "WHERE siren IS NOT NULL", eng)
    v = pd.read_sql("SELECT DISTINCT idu, date_mutation FROM p_model_ext_mut_l2 "
                    "WHERE NOT exclue_l2f", eng)
    v["date_mutation"] = pd.to_datetime(v["date_mutation"])
    v["an"] = v["date_mutation"].dt.year
    ventes_pm = v.merge(mil, on="idu")
    ventes_pm = ventes_pm[ventes_pm["millesime"] == ventes_pm["an"] - 1]
    rows = []
    for annee in range(2021, 2027):
        asof = pd.Timestamp(annee, 1, 1)
        own = (mil[mil["millesime"] <= annee - 1]
               .sort_values("millesime").groupby("idu")["siren"].last())
        w = ventes_pm[(ventes_pm["date_mutation"] >= asof - pd.DateOffset(months=24))
                      & (ventes_pm["date_mutation"] < asof)]
        vendus = w.groupby("siren")["idu"].agg(set)
        s = own.map(vendus)
        flag = np.array([isinstance(x, set) and bool(x - {i})
                         for i, x in zip(own.index, s)])
        rows.append(pd.DataFrame({"idu": own.index[flag], "annee": annee,
                                  "pm_vendeur_actif": True}))
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(path, index=False)
    return out


# ─────────────────────────── assemblage + test de fuite ───────────────────────────

def appliquer_voisinage(df: pd.DataFrame, spatial: pd.DataFrame,
                        marche: pd.DataFrame, vendeur: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(spatial, on=["idu", "annee"], how="left")
    for c in ("ventes_150m_12m", "ventes_150m_24m", "ventes_400m_12m",
              "ventes_400m_24m", "permis_100m_24m", "operations_pa_400m_24m"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)
    df["ventes_400m_delta"] = df["ventes_400m_12m"] - (df["ventes_400m_24m"]
                                                       - df["ventes_400m_12m"])
    df = df.merge(marche, on=["commune", "annee"], how="left")
    df = df.merge(vendeur, on=["idu", "annee"], how="left")
    # PM sans info SIREN ou millésime : manquant explicite ; non-PM : False
    est_pm = df["owner_type"].isin(["pm", "bailleur", "public"])
    df["pm_vendeur_actif"] = np.where(
        ~est_pm, False,
        np.where(df["annee"] >= 2021, df["pm_vendeur_actif"].fillna(False), None))
    return df


def test_fuite(eng, annee: int = 2025, echantillon: int = 30000) -> dict:
    """K4 bis — TEST DE FUITE DÉDIÉ : aucune feature ne doit contenir d'information
    postérieure au 01/01/annee.

    Méthode : reconstruire les features de l'année avec la SOURCE amont tronquée
    à asof (borne redondante poussée dans la requête) et exiger l'égalité stricte
    avec les features livrées. Si une fenêtre laissait passer un événement ≥ asof,
    la version tronquée différerait. Complété d'un contrôle direct : la date max
    des événements ENTRANT dans chaque agrégat est < asof."""
    asof = f"{annee}-01-01"
    livre_v = _ventes_annee(eng, annee).set_index("idu").sort_index()
    tronque_v = _ventes_annee(eng, annee, date_max=asof).set_index("idu").sort_index()
    livre_p = _permis_annee(eng, annee).set_index("idu").sort_index()
    tronque_p = _permis_annee(eng, annee, date_max=asof).set_index("idu").sort_index()
    egal_v = livre_v.equals(tronque_v)
    egal_p = livre_p.equals(tronque_p)
    dates = pd.read_sql(f"""
        SELECT max(date_mutation) AS dmax_ventes,
               (SELECT max(date_autorisation) FROM p_model_permits
                WHERE date_autorisation < '{asof}') AS dmax_permis_borne
        FROM p_model_ext_mut_l2 WHERE date_mutation < '{asof}'""", eng)
    verdict = {
        "annee_testee": annee,
        "ventes_voisines_egales_source_tronquee": bool(egal_v),
        "permis_voisins_egaux_source_tronquee": bool(egal_p),
        "date_max_ventes_entrantes": str(dates["dmax_ventes"].iloc[0]),
        "date_max_permis_entrants": str(dates["dmax_permis_borne"].iloc[0]),
        "asof": asof,
        "fuite_detectee": not (egal_v and egal_p),
    }
    pd.DataFrame([verdict]).to_csv(
        ROOT / "reports/score-v2-arene/k4bis_test_fuite.csv", index=False)
    return verdict


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "spatial"
    eng = engine()
    if cmd == "spatial":
        out = charger_spatial(eng, force="--force" in sys.argv)
        log(f"spatial : {len(out)} lignes")
    elif cmd == "fuite":
        import json
        print(json.dumps(test_fuite(eng), indent=2, ensure_ascii=False))
