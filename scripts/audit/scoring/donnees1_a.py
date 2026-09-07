"""SCORING-DONNEES-1 · Lot A — le faux passé (priorité 1).

A1  biais       — sur les lignes d'apprentissage labellisées 1 (2017-2024), part
                  des parcelles dont l'état 2026 contredit l'état à la vente.
                  Une table par variable statique (bâti/nu, résiduel, zone).
A2  inventaire  — ce qui permet (ou pas) de reconstruire l'as-of : millésimes
                  cadastre, BD TOPO, GPU, dates Sitadel. Années, table, clé.
A3  k0          — reconstruction as-of du bâti/nu (Sitadel + DVF, la zone est
                  IMPOSSIBLE en base) rejouée au banc K0 : la mesure la plus
                  importante du mandat.

Lecture seule ; n'écrit QUE dans reports/score-v2-arene/donnees1/.
Usage : .venv/bin/python scripts/audit/scoring/donnees1_a.py biais|inventaire|k0
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

TRAIN_LAB = (2017, 2024)  # « lignes d'apprentissage labellisées 1 » (train+cal)


# ────────────────────────────── A1 — mesurer le biais ──────────────────────────────

#: la vente qui fabrique le label : première mutation L2-F de l'année, avec son
#: flag `bati` (la mutation portait-elle du bâti ?) — p_model_ext_mut_l2.bati
_SQL_LABELS_1 = f"""
WITH lab AS (
  SELECT m.idu, extract(year FROM m.date_mutation)::int AS annee,
         min(m.date_mutation) AS date_vente,
         bool_or(m.bati) AS vendue_batie
  FROM p_model_ext_mut_l2 m
  WHERE NOT m.exclue_l2f
    AND m.date_mutation >= '{TRAIN_LAB[0]}-01-01'
    AND m.date_mutation <  '{TRAIN_LAB[1] + 1}-01-01'
  GROUP BY 1, 2)
SELECT l.*, (st.emprise_bati_m2 > 20) AS batie_2026, st.zone_plu,
       r.sdp_residuelle_m2 AS sdp_v2, split_part(r.cause, ':', 1) AS residuel_cause,
       prem.prem_pc_auto, prem.prem_achev
FROM lab l
JOIN p_model_static st USING (idu)
LEFT JOIN parcels p ON p.idu = l.idu
LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
LEFT JOIN (
  SELECT pp.idu, min(pp.date_autorisation) AS prem_pc_auto,
         min(m.date_achevement) AS prem_achev
  FROM p_model_permits pp
  LEFT JOIN m10_permit_delais m USING (permit_id)
  WHERE pp.type = 'PC' GROUP BY 1) prem ON prem.idu = l.idu
"""


def biais() -> None:
    eng = engine()
    log("[A1] lignes labellisées 1 (2017-2024) + état 2026…")
    d = pd.read_sql(_SQL_LABELS_1, eng)
    d["date_vente"] = pd.to_datetime(d["date_vente"])
    n = len(d)
    batie = d["batie_2026"].fillna(False)
    vb = d["vendue_batie"].astype(bool)

    # 1) bâti / nu (état 2026) vs la nature de la vente (DVF `bati`)
    t1 = pd.DataFrame([{
        "variable": "bati/nu (emprise BD TOPO 2026)",
        "n_labels_1": n,
        "n_batie_2026": int(batie.sum()),
        "n_batie_2026_vendue_nue": int((batie & ~vb).sum()),
        "pct_batie_2026_vendue_nue": round(100 * (batie & ~vb).sum() / max(batie.sum(), 1), 1),
        "n_nue_2026_vendue_batie": int((~batie & vb).sum()),
        "pct_nue_2026_vendue_batie": round(100 * (~batie & vb).sum() / max((~batie).sum(), 1), 1),
        "preuve": "p_model_ext_mut_l2.bati × p_model_static.emprise_bati_m2",
    }])

    # 2) confirmation Sitadel : achèvement/autorisation POSTÉRIEURS à la vente
    achev = pd.to_datetime(d["prem_achev"])
    auto = pd.to_datetime(d["prem_pc_auto"])
    post_achev = batie & ~vb & achev.notna() & (achev > d["date_vente"])
    post_auto = batie & ~vb & auto.notna() & (auto > d["date_vente"])
    t2 = pd.DataFrame([{
        "variable": "date d'achèvement/autorisation Sitadel vs vente",
        "n_batie_2026_vendue_nue": int((batie & ~vb).sum()),
        "n_achevement_posterieur_vente": int(post_achev.sum()),
        "n_autorisation_posterieure_vente": int(post_auto.sum()),
        "pct_confirmes_sitadel": round(
            100 * (post_achev | post_auto).sum() / max((batie & ~vb).sum(), 1), 1),
        "preuve": "m10_permit_delais.date_achevement, p_model_permits.date_autorisation",
    }])

    # 3) résiduel (état 2026) : les vendues nues → bâties ont un résiduel POST-construction
    flip = batie & ~vb
    t3 = pd.DataFrame([{
        "variable": "sdp_residuelle_m2 / sous_densite (moteur M125, état 2026)",
        "n_flip_nue_puis_batie": int(flip.sum()),
        "n_flip_sdp_v2_zero": int((flip & (pd.to_numeric(d["sdp_v2"], errors="coerce") == 0)).sum()),
        "n_flip_sdp_v2_pos": int((flip & (pd.to_numeric(d["sdp_v2"], errors="coerce") > 0)).sum()),
        "note": "le résiduel est calculé APRÈS la construction : la parcelle a appris "
                "« peu de droits restants » alors qu'elle était nue au moment de la vente",
        "preuve": "parcel_residuel.sdp_residuelle_m2 (statique)",
    }])

    # 4) zone PLU : borne haute par la date d'approbation du PLU servi (SUDOCUH)
    sud = pd.read_sql(
        "SELECT insee, approbation_opp FROM sudocuh_procedures", eng)
    d["insee"] = d["idu"].str.slice(0, 5)
    d = d.merge(sud, on="insee", how="left")
    appro = pd.to_datetime(d["approbation_opp"])
    avant_plu = appro.notna() & (d["date_vente"] < appro)
    t4 = pd.concat([
        pd.DataFrame([{
            "variable": "zone_plu (GPU, zonage SERVI = dernier approuvé)",
            "n_labels_1": n,
            "n_vendues_avant_approbation_plu_servi": int(avant_plu.sum()),
            "pct": round(100 * avant_plu.sum() / n, 1),
            "note": "BORNE HAUTE : ces ventes sont apprises avec un zonage approuvé "
                    "APRÈS la vente ; le flip parcelle par parcelle est immesurable "
                    "(aucune archive GPU par parcelle en base — cf. A2)",
            "preuve": "sudocuh_procedures.approbation_opp × date de vente",
        }]),
    ])
    par_annee = (d.assign(avant=avant_plu).groupby("annee")["avant"]
                 .agg(["count", "sum", "mean"]).reset_index()
                 .rename(columns={"count": "n_labels_1", "sum": "n_avant_plu_servi",
                                  "mean": "part"}))
    par_annee["part"] = (100 * par_annee["part"]).round(1)

    t1.to_csv(OUT / "a1_biais_bati_nu.csv", index=False)
    t2.to_csv(OUT / "a1_biais_sitadel_posterieur.csv", index=False)
    t3.to_csv(OUT / "a1_biais_residuel.csv", index=False)
    t4.to_csv(OUT / "a1_biais_zone_plu.csv", index=False)
    par_annee.to_csv(OUT / "a1_biais_zone_plu_par_annee.csv", index=False)
    for t in (t1, t2, t3, t4, par_annee):
        print(t.to_string(index=False), "\n")


# ─────────────────────────── A2 — inventaire des as-of ───────────────────────────

def inventaire() -> None:
    eng = engine()
    rows = []
    ch = pd.read_sql(
        "SELECT millesime, count(*) AS n, count(DISTINCT left(idu,5)) AS n_communes "
        "FROM cadastre_historique GROUP BY 1 ORDER BY 1", eng)
    rows.append({
        "source": "cadastre_historique (géométries)", "table": "cadastre_historique",
        "cle": "idu × millesime",
        "annees": " / ".join(f"{r.millesime} ({r.n})" for r in ch.itertuples()),
        "verdict_asof": "INUTILISABLE pour le bâti : 6 495 lignes en tout "
                        "(géométries parcellaires ponctuelles, pas d'emprise bâtie, "
                        "couverture anecdotique sur 431 663 parcelles)"})
    fb = pd.read_sql(
        "SELECT count(*) AS n, count(annee_construction) AS avec_annee "
        "FROM parcel_filtre_bati", eng).iloc[0]
    rows.append({
        "source": "année de construction (MAJIC via filtre bâti)",
        "table": "parcel_filtre_bati.annee_construction", "cle": "idu",
        "annees": f"{int(fb['avec_annee'])} renseignées sur {int(fb['n'])}",
        "verdict_asof": "INUTILISABLE : 184 années de construction renseignées "
                        "sur 294 865 (0,06 %)"})
    rows.append({
        "source": "BD TOPO (emprise bâtie)", "table": "p_model_bati / p_model_bati_cosia",
        "cle": "idu",
        "annees": "édition UNIQUE (2026) + CoSIA millésime 2025",
        "verdict_asof": "IMPOSSIBLE seul : aucune édition antérieure en base"})
    rows.append({
        "source": "GPU / zonage PLU", "table": "parcel_zone_plu (427 419)",
        "cle": "idu",
        "annees": "dernier zonage approuvé seulement ; plu_reglement_extrait porte "
                  "20 millésimes de RÈGLEMENTS (textes), pas de géométries",
        "verdict_asof": "IMPOSSIBLE par parcelle : aucune archive de zonage "
                        "géométrique ; sudocuh_procedures.approbation_opp donne la "
                        "seule borne (date d'approbation du PLU servi, par commune)"})
    si = pd.read_sql("""
        SELECT count(*) AS n, min(date_autorisation) AS dmin, max(date_autorisation) AS dmax,
               count(*) FILTER (WHERE type='PC') AS n_pc,
               count(*) FILTER (WHERE type='PA') AS n_pa,
               count(*) FILTER (WHERE type IN ('DP')) AS n_dp
        FROM p_model_permits""", eng).iloc[0]
    m10 = pd.read_sql(
        "SELECT count(*) AS n, count(date_depot) AS avec_depot, "
        "count(date_autorisation) AS avec_auto, count(date_achevement) AS avec_achev "
        "FROM m10_permit_delais", eng).iloc[0]
    rows.append({
        "source": "Sitadel (dates de permis)",
        "table": "p_model_permits (idu) + m10_permit_delais (dates dépôt/auto/achèvement)",
        "cle": "permit_id → idu (p_model_permits.idu)",
        "annees": f"{si['dmin']} → {si['dmax']} ; {int(si['n'])} permis "
                  f"(PC {int(si['n_pc'])}, PA {int(si['n_pa'])}, DP {int(si['n_dp'])}) ; "
                  f"achèvement daté : {int(m10['avec_achev'])}/{int(m10['n'])}",
        "verdict_asof": "UTILISABLE : autorisation 100 % datée (2013+), achèvement 41 % "
                        "— socle de la reconstruction bâti/nu as-of (A3)"})
    rows.append({
        "source": "DVF (nature de la vente : nue ou bâtie)",
        "table": "p_model_ext_mut_l2.bati (union histo 2014-2020 + courant 2021+)",
        "cle": "idu × date_mutation",
        "annees": "2014 → 2025",
        "verdict_asof": "UTILISABLE : une mutation bâtie prouve le bâti à sa date ; "
                        "une mutation nue prouve le nu à sa date"})
    pm = pd.read_sql(
        "SELECT min(millesime) AS a, max(millesime) AS b FROM pm_proprietaires_millesimes",
        eng).iloc[0]
    rows.append({
        "source": "propriétaires PM (millésimes DGFiP)",
        "table": "pm_proprietaires_millesimes", "cle": "idu × millesime × siren",
        "annees": f"{int(pm['a'])} → {int(pm['b'])} (situation au 01/01)",
        "verdict_asof": "UTILISABLE (Lot D) : état propriétaire PM au 01/01 de "
                        "chaque année 2019-2024"})
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT / "a2_inventaire_asof.csv", index=False)
    print(inv.to_string(index=False))


# ──────────────── A3 — bâti/nu rejoué as-of, mesuré au banc K0 ────────────────

SPECS_A = [
    FeatureSpec("nu_constructible_asof", "D", "cat", 0,
                "bâti/nu RECONSTRUIT à l'état physique du 01/01/Y : Sitadel (1er PC "
                "autorisé, achèvement) + DVF (mutations nues/bâties datées) ; "
                "catégories : bati / nu_droits (zone U-AU) / nu_sans_droits (A-N) / "
                "nu_non_calcule — remplace nu_constructible_v3 (état 2026)",
                "as-of 01/01/Y (reconstruction)", _ARENE,
                "la zone reste le zonage servi (aucune archive GPU) ; le flip ne "
                "porte que sur l'état bâti/nu"),
    FeatureSpec("pct_bati_secteur_asof", "Z", "num", 0,
                "part de parcelles bâties du secteur, RECONSTRUITE au 01/01/Y "
                "(mêmes preuves que nu_constructible_asof) — remplace "
                "pct_bati_secteur (état 2026)", "as-of 01/01/Y (reconstruction)",
                _ARENE),
]

_SQL_EVIDENCE = """
SELECT st.idu, (st.emprise_bati_m2 > 20) AS batie_2026,
       prem.prem_pc_auto, prem.prem_achev,
       mb.prem_mut_batie, mn.dern_mut_nue
FROM p_model_static st
LEFT JOIN (
  SELECT pp.idu, min(pp.date_autorisation) AS prem_pc_auto,
         min(m.date_achevement) AS prem_achev
  FROM p_model_permits pp
  LEFT JOIN m10_permit_delais m USING (permit_id)
  WHERE pp.type = 'PC' GROUP BY 1) prem ON prem.idu = st.idu
LEFT JOIN (SELECT idu, min(date_mutation) AS prem_mut_batie
           FROM p_model_ext_mut_l2 WHERE bati GROUP BY 1) mb ON mb.idu = st.idu
LEFT JOIN (SELECT idu, max(date_mutation) AS dern_mut_nue
           FROM p_model_ext_mut_l2 WHERE NOT bati GROUP BY 1) mn ON mn.idu = st.idu
"""


def _nu_asof_grille(eng) -> pd.DataFrame:
    """(idu, annee, nu_asof) pour 2017-2026 — l'état PHYSIQUE bâti/nu au 01/01/Y,
    reconstruit depuis des événements datés ANTÉRIEURS à Y (permis, mutations).

    Règles (conservatrices, documentées au rapport) :
      - parcelle bâtie 2026 : nue au 01/01/Y si son PREMIER PC est autorisé à
        partir de Y et qu'aucune mutation bâtie n'est antérieure à Y (une vente
        nue postérieure au 01/01/Y conforte, jamais n'infirme) ;
        pas de PC connu → réputée bâtie (construite avant 2013, hors Sitadel) ;
      - parcelle nue 2026 : bâtie au 01/01/Y si une mutation BÂTIE est datée
        après Y (le bâtiment existait alors — démoli depuis).
    """
    ev = pd.read_sql(_SQL_EVIDENCE, eng)
    for c in ("prem_pc_auto", "prem_achev", "prem_mut_batie", "dern_mut_nue"):
        ev[c] = pd.to_datetime(ev[c])
    frames = []
    for y in YEARS:
        asof = pd.Timestamp(f"{y}-01-01")
        batie26 = ev["batie_2026"].fillna(False).to_numpy()
        flip_vers_nu = (batie26
                        & ev["prem_pc_auto"].notna().to_numpy()
                        & (ev["prem_pc_auto"] >= asof).to_numpy()
                        & ~(ev["prem_mut_batie"] < asof).to_numpy())
        flip_vers_bati = (~batie26 & (ev["prem_mut_batie"] >= asof).to_numpy())
        nu_asof = np.where(flip_vers_nu, True,
                  np.where(flip_vers_bati, False, ~batie26))
        frames.append(pd.DataFrame({"idu": ev["idu"], "annee": y,
                                    "nu_asof": nu_asof}))
    return pd.concat(frames, ignore_index=True)


def _colonnes_a(eng) -> pd.DataFrame:
    """Les 2 colonnes candidates par (idu, annee) : nu_constructible_asof
    (catégorielle) + pct_bati_secteur_asof (agrégat secteur)."""
    g = _nu_asof_grille(eng)
    zone = pd.read_sql(
        "SELECT idu, st.zone_plu, f.secteur FROM p_model_static st "
        "JOIN p_model_frame f USING (idu)", eng)
    g = g.merge(zone, on="idu", how="left")
    z = g["zone_plu"].fillna("inconnu")
    g["nu_constructible_asof"] = np.select(
        [~g["nu_asof"], z.isin(["U", "AU"]), z == "inconnu"],
        ["bati", "nu_droits", "nu_non_calcule"], default="nu_sans_droits")
    sect = (g.groupby(["secteur", "annee"])["nu_asof"]
            .agg(lambda s: 1.0 - s.mean()).rename("pct_bati_secteur_asof")
            .reset_index())
    g = g.merge(sect, on=["secteur", "annee"], how="left")
    return g[["idu", "annee", "nu_constructible_asof", "pct_bati_secteur_asof"]]


def _rappel_flip(eng) -> None:
    """Contrôle : parmi les labels 1 vendus NUS mais bâtis 2026 (le biais A1),
    quelle part la reconstruction rebascule-t-elle en nu à l'année de la vente ?"""
    d = pd.read_sql(_SQL_LABELS_1, eng)
    g = _nu_asof_grille(eng)
    d = d.merge(g, on=["idu", "annee"], how="left")
    flip = d["batie_2026"].fillna(False) & ~d["vendue_batie"].astype(bool)
    rec = pd.DataFrame([{
        "n_flip_a_corriger": int(flip.sum()),
        "n_rebascules_nu_asof": int((flip & d["nu_asof"].fillna(False)).sum()),
        "rappel_pct": round(100 * (flip & d["nu_asof"].fillna(False)).sum()
                            / max(flip.sum(), 1), 1),
        "note": "le solde = constructions sans PC en base (DP, non déclaré, "
                "permis antérieur à la vente d'un terrain à re-bâtir)",
    }])
    rec.to_csv(OUT / "a3_rappel_reconstruction.csv", index=False)
    print(rec.to_string(index=False))


def k0() -> None:
    eng = engine()
    log("[A3] reconstruction as-of bâti/nu…")
    cols = _colonnes_a(eng)
    _rappel_flip(eng)
    log("[A3] mesure — nu as-of seul (remplace nu_constructible_v3)…")
    dc.mesurer("A_nu_asof", [SPECS_A[0]], colonnes=cols[
        ["idu", "annee", "nu_constructible_asof"]],
        remplacees={"nu_constructible_v3": "nu_constructible_asof"})
    log("[A3] mesure — pct bâti secteur as-of seul (remplace pct_bati_secteur)…")
    dc.mesurer("A_pct_bati_secteur_asof", [SPECS_A[1]], colonnes=cols[
        ["idu", "annee", "pct_bati_secteur_asof"]],
        remplacees={"pct_bati_secteur": "pct_bati_secteur_asof"})
    log("[A3] mesure — les deux ensemble…")
    dc.mesurer("A_asof_combine", SPECS_A, colonnes=cols,
               remplacees={"nu_constructible_v3": "nu_constructible_asof",
                           "pct_bati_secteur": "pct_bati_secteur_asof"})


if __name__ == "__main__":
    {"biais": biais, "inventaire": inventaire, "k0": k0}[
        sys.argv[1] if len(sys.argv) > 1 else "biais"]()
