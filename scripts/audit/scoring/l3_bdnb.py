"""SCORING-3 · L3.2 — les variables candidates BDNB, au banc K0 AVANT toute
inscription au modèle.

Variables par parcelle (agrégées depuis bdnb_* via bdnb_rel_parcelle — la
jointure bâtiment→parcelle par l'emprise, croisement cadastre fait par le CSTB) :
  - bdnb_annee_construction : plus ancienne année de construction (FF) ;
  - bdnb_avant_1975 : bool (bâti d'avant la première réglementation thermique) ;
  - bdnb_dpe_classe : pire classe DPE représentative des bâtiments ;
  - bdnb_dpe_fg : bool (F ou G — passoire) ;
  - bdnb_ecart_surface_pct : (surface d'emprise BDNB − emprise BD TOPO LABUSE)
    / emprise BD TOPO — une extension non déclarée ?

Caveat consigné : millésime UNIQUE en base (2026-02-a) — features statiques,
même convention de fuite faible que zone_plu/filo (consignée au dictionnaire).
Années de construction et classes DPE sont des états quasi permanents.

Verdict (L3.2) : elles n'entrent dans le candidat q_v12 QUE si elles gagnent
la précision en haut de liste SANS dégrader l'ECE — sinon elles attendent.
Sortie : ligne « q_v12_bdnb » dans k0_table.csv + l3_bdnb_couverture.csv.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protocole  # noqa: E402
from _common import engine, ROOT  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec  # noqa: E402
from labuse.scoring.p_v2 import qv12  # noqa: E402

CACHE = ROOT / "reports/score-v2-arene/cache"
QDIR = ROOT / "reports/q-v12"
QDIR.mkdir(parents=True, exist_ok=True)
YEARS = tuple(range(2017, 2027))

_SRC = "BDNB (CSTB) millésime 2026-02-a — statique, fuite faible consignée"

SPECS_BDNB = [
    FeatureSpec("bdnb_annee_construction", "D", "num", 0,
                "BDNB ffo : plus ancienne année de construction des bâtiments "
                "de la parcelle ; parcelle sans bâtiment BDNB → manquant explicite",
                "statique (millésime 2026-02-a)", _SRC),
    FeatureSpec("bdnb_avant_1975", "D", "bool", 0,
                "bâti d'avant 1975 (première RT) — proxy d'âge du bien",
                "statique", _SRC),
    FeatureSpec("bdnb_dpe_classe", "D", "cat", 0,
                "pire classe DPE représentative (A→G) des bâtiments de la "
                "parcelle ; sans DPE → manquant explicite", "statique", _SRC),
    FeatureSpec("bdnb_dpe_fg", "D", "bool", 0,
                "classe F ou G (passoire) — « une maison de 1965 en G, c'est "
                "une vente à venir » (plan v2 §2.4)", "statique", _SRC),
    FeatureSpec("bdnb_ecart_surface_pct", "D", "num", 0,
                "(surface emprise BDNB − emprise BD TOPO LABUSE) / emprise BD "
                "TOPO — extension non déclarée ?", "statique", _SRC),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def charger_bdnb(eng) -> pd.DataFrame:
    """Variables BDNB par parcelle (statique : mêmes valeurs toutes années)."""
    df = pd.read_sql("""
        SELECT r.parcelle_idu AS idu,
               min(NULLIF(f.annee_construction, '')::float) AS bdnb_annee_construction,
               max(NULLIF(g.s_geom_groupe_m2, '')::float)   AS bdnb_s_geom_m2,
               max(d.classe_dpe) FILTER (WHERE d.classe_dpe IN
                   ('A','B','C','D','E','F','G'))           AS bdnb_dpe_classe
        FROM bdnb_rel_parcelle r
        LEFT JOIN bdnb_ffo f ON f.batiment_groupe_id = r.batiment_groupe_id
        LEFT JOIN bdnb_dpe d ON d.batiment_groupe_id = r.batiment_groupe_id
        LEFT JOIN bdnb_groupe g ON g.batiment_groupe_id = r.batiment_groupe_id
        GROUP BY 1""", eng)
    return df


def appliquer_bdnb(df: pd.DataFrame, bdnb: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(bdnb, on="idu", how="left")
    an = pd.to_numeric(df["bdnb_annee_construction"], errors="coerce")
    df["bdnb_annee_construction"] = an.where((an >= 1600) & (an <= 2026))
    df["bdnb_avant_1975"] = (df["bdnb_annee_construction"] < 1975).astype(bool)
    df["bdnb_dpe_fg"] = df["bdnb_dpe_classe"].isin(["F", "G"]).astype(bool)
    emprise = pd.to_numeric(df.get("emprise_bati_m2"), errors="coerce")
    s_bdnb = pd.to_numeric(df["bdnb_s_geom_m2"], errors="coerce")
    df["bdnb_ecart_surface_pct"] = np.where(
        (emprise > 0) & s_bdnb.notna(), (s_bdnb - emprise) / emprise, np.nan)
    return df


def main() -> None:
    eng = engine()
    # constat 03/09/2026 (mesuré) : l'export France 2026-02-a ne couvre pas le 974.
    # Tant que les tables bdnb_* sont vides, le verdict L3.2 est « elles attendent »
    # — ce banc est REJOUABLE tel quel dès qu'un millésime couvrira La Réunion.
    vide = pd.read_sql("SELECT to_regclass('bdnb_rel_parcelle') t", eng)["t"].iloc[0] is None \
        or pd.read_sql("SELECT count(*) n FROM bdnb_rel_parcelle", eng)["n"].iloc[0] == 0
    if vide:
        verdict = ("ATTENDENT — l'export amont BDNB (2026-02-a, seule distribution) "
                   "couvre la métropole seule : 0 ligne 974 sur 22,3 M "
                   "(batiment_groupe_ffo_bat, vérifié ligne à ligne le 03/09/2026). "
                   "Banc K0 rejouable dès qu'un millésime couvre La Réunion.")
        pd.DataFrame([{"gagne_tete": None, "ece_ok": None, "verdict": verdict}]).to_csv(
            QDIR / "l3_bdnb_verdict.csv", index=False)
        print(verdict)
        return
    log("variables BDNB par parcelle…")
    bdnb = charger_bdnb(eng)
    log(f"  {len(bdnb)} parcelles avec ≥ 1 bâtiment BDNB")

    log("chargement 2017-2026 + enrichissement recette q_v12…")
    df = protocole.load_range(eng, YEARS)
    df = qv12.enrichir(eng, df, YEARS, cache_dir=CACHE)
    df = appliquer_bdnb(df, bdnb)

    y26 = df[df.annee == protocole.SCORE_YEAR]
    couverture = {
        "parcelles_bdnb": int(len(bdnb)),
        "annee_construction_pct": round(100 * float(
            y26["bdnb_annee_construction"].notna().mean()), 1),
        "avant_1975_pct": round(100 * float(y26["bdnb_avant_1975"].mean()), 1),
        "dpe_classe_pct": round(100 * float(y26["bdnb_dpe_classe"].notna().mean()), 1),
        "dpe_fg_pct": round(100 * float(y26["bdnb_dpe_fg"].mean()), 1),
        "ecart_surface_pct_couv": round(100 * float(
            y26["bdnb_ecart_surface_pct"].notna().mean()), 1),
    }
    pd.DataFrame([couverture]).to_csv(QDIR / "l3_bdnb_couverture.csv", index=False)
    print(couverture)

    names, specs, inter = qv12.features_qv12()
    names_b = names + [s.name for s in SPECS_BDNB]
    specs_b = specs + SPECS_BDNB
    copro = qv12.copro_de(eng, df)
    seg_all = qv12.segmenter(df, copro)

    log("fit AVEC BDNB (même protocole que q_v12)…")
    m = qv12.fit_qv12(df, seg_all, names_b, specs_b, inter)
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = m.predict_proba(ctx.test, seg_test)
    d_feats = [s.name for s in specs_b if s.bloc == "D"]
    cd = m.contributions(ctx.test)[
        [c for c in d_feats if c in m.base.coefs]].sum(axis=1).to_numpy()
    p26 = m.predict_proba(ctx.score26, seg_26)
    row = protocole.metriques(ctx, "q_v12_bdnb", p, cd, p26)
    table = protocole.enregistrer(row)
    print(table[table.candidat.isin(["ligne_de_base", "q_v12", "q_v12_bdnb"])]
          .to_string(index=False))

    q = table[table.candidat == "q_v12"].iloc[0]
    b = table[table.candidat == "q_v12_bdnb"].iloc[0]
    gagne_tete = (b["prec@100_commune_mediane"] > q["prec@100_commune_mediane"]) or (
        b["prec@100_commune_mediane"] == q["prec@100_commune_mediane"]
        and b["lift_decile_sup"] > q["lift_decile_sup"])
    ece_ok = b["ece_global"] <= q["ece_global"] + 1e-4
    verdict = ("ENTRENT dans le candidat (gain tête sans dégrader l'ECE)"
               if gagne_tete and ece_ok else
               "ATTENDENT (pas de gain en tête ou ECE dégradé) — hors du candidat q_v12")
    print(f"\nVerdict L3.2 : {verdict}")
    pd.DataFrame([{"gagne_tete": gagne_tete, "ece_ok": ece_ok,
                   "verdict": verdict}]).to_csv(QDIR / "l3_bdnb_verdict.csv", index=False)


if __name__ == "__main__":
    main()
