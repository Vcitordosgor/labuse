"""SCORING-DONNEES-1 · Lot C — gestes précurseurs déjà en base.

Pour chaque geste : existence, couverture 974, dates disponibles, as-of possible,
mesure K0 (quand l'as-of tient).

  inventaire — la table c1 (un geste par ligne, verdict as-of).
  k0         — les 3 gestes datables mesurés SEULS ajoutés au candidat q_v12 :
               dp_parcelle_36m, pc_caduc_asof, pc_pm_sur_parcelle_pp_36m.
               (division cadastrale : as-of IMPOSSIBLE ; DPE : 17 lignes → noté.)

Usage : .venv/bin/python scripts/audit/scoring/donnees1_c.py inventaire|k0
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donnees1_commun as dc  # noqa: E402
from donnees1_commun import OUT, YEARS, _ARENE, log  # noqa: E402
from _common import engine  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec  # noqa: E402


# ────────────────────────────── C1 — inventaire ──────────────────────────────

def inventaire() -> None:
    eng = engine()
    rows = []
    div = pd.read_sql("""
        SELECT (SELECT count(*) FROM sitadel_permits WHERE raw ? 'origine_redecoupee') AS redecoupes,
               (SELECT count(*) FROM division_or_candidates) AS or_candidates,
               (SELECT count(*) FROM module_division) AS module_division""", eng).iloc[0]
    rows.append({
        "geste": "division cadastrale (parcelle créée/découpée récemment)",
        "existence": f"traces indirectes seulement : sitadel_permits.raw.origine_redecoupee "
                     f"({int(div['redecoupes'])} permis pointant une parcelle redécoupée), "
                     f"division_or_candidates ({int(div['or_candidates'])}), "
                     f"module_division ({int(div['module_division'])})",
        "couverture_974": "anecdotique (cadastre_historique 6 495 géométries, cf. Lot A2)",
        "dates": "AUCUNE date de création de parcelle portée en base "
                 "(parcels.created_at = date d'ingestion 2026)",
        "asof_possible": "NON — variable documentée, pas mesurée",
    })
    dp = pd.read_sql("""
        SELECT type, count(*) AS n, count(DISTINCT pp.idu) AS n_idu,
               min(date_autorisation) AS dmin, max(date_autorisation) AS dmax
        FROM p_model_permits pp WHERE type IN ('DP','PA','PD') GROUP BY 1""", eng)
    for r in dp.itertuples():
        rows.append({
            "geste": {"DP": "déclaration préalable (dont divisions — nature non distinguée)",
                      "PA": "permis d'aménager (lotissement)",
                      "PD": "permis de démolir"}[r.type],
            "existence": f"p_model_permits type={r.type} : {r.n} permis, {r.n_idu} parcelles",
            "couverture_974": "toute l'île (Sitadel)",
            "dates": f"{r.dmin} → {r.dmax} (date_autorisation, 100 % datée)",
            "asof_possible": "OUI — mesuré au K0 (dp_parcelle_36m ; PA voisin déjà dans "
                             "la recette via operations_pa_400m_24m)" if r.type == "DP"
                             else "OUI (PA 400 m déjà dans la recette q_v12 ; PD non mesuré : "
                             f"{r.n} permis, geste de chantier plus que précurseur de vente)",
        })
    rows.append({
        "geste": "permis refusés",
        "existence": "ABSENTS : Sitadel open data ne publie que les autorisés "
                     "(etat_dau 2/4/5/6 en base, aucun refus)",
        "couverture_974": "—", "dates": "—",
        "asof_possible": "NON — source à part (registres communaux), documenté",
    })
    cad = pd.read_sql(
        "SELECT count(*) AS n, min(pc_annee) AS amin, max(pc_annee) AS amax, "
        "min(caduc_depuis) AS cmin, max(caduc_depuis) AS cmax FROM pc_caducs", eng).iloc[0]
    rows.append({
        "geste": "PC autorisé jamais commencé, devenu caduc",
        "existence": f"pc_caducs : {int(cad['n'])} parcelles "
                     f"(PC {int(cad['amin'])}-{int(cad['amax'])}, "
                     f"caducité estimée {int(cad['cmin'])}-{int(cad['cmax'])})",
        "couverture_974": "toute l'île (dérivé Sitadel)",
        "dates": "pc_annee + caduc_depuis (années) ; « jamais commencé » constaté en "
                 "2026 vaut a fortiori pour tout 01/01/Y antérieur",
        "asof_possible": "OUI — mesuré au K0 (pc_caduc_asof)",
    })
    pm = pd.read_sql("""
        SELECT count(*) AS n,
               count(*) FILTER (WHERE coalesce(raw->>'petitioner_siren','') <> '') AS avec_siren
        FROM sitadel_permits WHERE type = 'PC'""", eng).iloc[0]
    rows.append({
        "geste": "PC déposé par une personne morale sur une parcelle détenue par un "
                 "particulier (promoteur sous compromis)",
        "existence": f"sitadel_permits.raw.petitioner_siren : {int(pm['avec_siren'])} PC "
                     f"sur {int(pm['n'])} portent un SIREN demandeur (les demandeurs "
                     "particuliers sont anonymisés, sans SIREN)",
        "couverture_974": "toute l'île",
        "dates": "date_autorisation (100 %)",
        "asof_possible": "OUI — mesuré au K0 (pc_pm_sur_parcelle_pp_36m ; le côté "
                         "« détenue par un particulier » lit owner_type, statique — "
                         "les millésimes PM 2019-2024 ne couvrent pas 2017-2018)",
    })
    dpe = pd.read_sql(
        "SELECT count(*) AS n, count(DISTINCT parcelle_idu) AS n_idu, "
        "min(date_etablissement) AS dmin, max(date_etablissement) AS dmax "
        "FROM dpe_records", eng).iloc[0]
    rows.append({
        "geste": "DPE frais sur la parcelle sans vente derrière (ADEME)",
        "existence": f"dpe_records : {int(dpe['n'])} DPE en tout "
                     f"({int(dpe['n_idu'])} parcelles, {dpe['dmin']} → {dpe['dmax']})",
        "couverture_974": f"{int(dpe['n_idu'])}/431 663 parcelles ≈ 0,004 % — très en "
                          "dessous du seuil des 5 % du mandat",
        "dates": "date_etablissement (datée)",
        "asof_possible": "OUI en théorie, mais couverture quasi nulle → NOTÉE, pas "
                         "candidate (règle des 5 %) ; l'ingestion ADEME réelle est un "
                         "préalable (la source est connectée mais 17 lignes en base)",
    })
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT / "c1_inventaire_gestes.csv", index=False)
    print(inv.to_string(index=False))


# ─────────────────────────────── C2 — mesures K0 ───────────────────────────────

SPECS_C = [
    FeatureSpec("dp_parcelle_36m", "D", "bool", 0,
                "déclaration préalable Sitadel SUR la parcelle dans les 36 mois "
                "avant asof (les DP de division ne sont pas distinguées : toutes "
                "natures)", "as-of 01/01/Y", _ARENE,
                "positifs rares (~200 DP/an sur l'île) — absence = 0 explicite"),
    FeatureSpec("pc_caduc_asof", "D", "bool", 0,
                "PC autorisé jamais commencé dont la caducité estimée est acquise "
                "au 01/01/Y (pc_caducs : pc_annee < Y et caduc_depuis ≤ Y ; "
                "« jamais commencé » constaté en 2026 vaut pour tout Y antérieur)",
                "as-of 01/01/Y", _ARENE),
    FeatureSpec("pc_pm_sur_parcelle_pp_36m", "D", "bool", 0,
                "PC autorisé dans les 36 mois avant asof dont le demandeur porte un "
                "SIREN (personne morale), sur une parcelle dont le propriétaire est "
                "un particulier (owner_type='pp', statique) — le promoteur sous "
                "compromis", "as-of 01/01/Y (demandeur) × statique (propriétaire)",
                _ARENE),
]


def _colonnes_c(eng) -> pd.DataFrame:
    dp = pd.read_sql(
        "SELECT idu, date_autorisation FROM p_model_permits WHERE type = 'DP'", eng)
    pcpm = pd.read_sql("""
        SELECT pp.idu, pp.date_autorisation
        FROM p_model_permits pp
        JOIN sitadel_permits s ON s.permit_id = pp.permit_id
        WHERE pp.type = 'PC' AND coalesce(s.raw->>'petitioner_siren','') <> ''""", eng)
    cad = pd.read_sql("SELECT idu, pc_annee, caduc_depuis FROM pc_caducs", eng)
    frames = []
    for y in YEARS:
        asof = pd.Timestamp(f"{y}-01-01")
        deb = asof - pd.DateOffset(months=36)
        w_dp = dp[(pd.to_datetime(dp.date_autorisation) >= deb)
                  & (pd.to_datetime(dp.date_autorisation) < asof)]["idu"].unique()
        w_pm = pcpm[(pd.to_datetime(pcpm.date_autorisation) >= deb)
                    & (pd.to_datetime(pcpm.date_autorisation) < asof)]["idu"].unique()
        w_cad = cad[(cad.pc_annee < y) & (cad.caduc_depuis <= y)]["idu"].unique()
        idus = pd.Index(np.union1d(np.union1d(w_dp, w_pm), w_cad), name="idu")
        f = pd.DataFrame(index=idus).reset_index()
        f["annee"] = y
        f["dp_parcelle_36m"] = f["idu"].isin(set(w_dp))
        f["pc_caduc_asof"] = f["idu"].isin(set(w_cad))
        f["pc_pm_36m_brut"] = f["idu"].isin(set(w_pm))
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def k0() -> None:
    eng = engine()
    log("[C2] colonnes candidates (DP / PC caduc / PC de PM)…")
    cols = _colonnes_c(eng)
    df, _ = dc.base_enrichie(eng)
    owner_pp = df[["idu", "annee"]].assign(
        _pp=(df["owner_type"].fillna("pp") == "pp"))
    cols = cols.merge(owner_pp, on=["idu", "annee"], how="left")
    cols["pc_pm_sur_parcelle_pp_36m"] = (cols["pc_pm_36m_brut"]
                                         & cols["_pp"].fillna(True))
    cols = cols.drop(columns=["pc_pm_36m_brut", "_pp"])
    stats = (cols.groupby("annee")[["dp_parcelle_36m", "pc_caduc_asof",
                                    "pc_pm_sur_parcelle_pp_36m"]].sum())
    stats.to_csv(OUT / "c2_positifs_par_annee.csv")
    print(stats.to_string())

    def une(nom: str) -> pd.DataFrame:
        c = cols[["idu", "annee", nom]].copy()
        return c

    for spec in SPECS_C:
        # bool : absence de ligne = False explicite (fill_false — le WoE lit une
        # catégorielle 2 niveaux, jamais un NA muet)
        dc.mesurer(f"C_{spec.name}", [spec], colonnes=une(spec.name),
                   fill_false=[spec.name])


if __name__ == "__main__":
    {"inventaire": inventaire, "k0": k0}[
        sys.argv[1] if len(sys.argv) > 1 else "inventaire"]()
