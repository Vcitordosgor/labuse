"""SCORING-DONNEES-1 · Lot E — ce que le PLU annonce.

Emplacements réservés, OAP, ZAC, changement de zonage entre millésimes GPU,
commune en procédure : existence, couverture, as-of, K0.

État mesuré en base :
  - ER : 741 polygones (spatial_layers kind='plu_gpu_prescription') — STATIQUES
    (un seul millésime GPU) → documentés, pas mesurés (règle as-of du mandat) ;
  - OAP / ZAC : ABSENTS des couches en base ;
  - changement de zonage entre millésimes GPU : IMPOSSIBLE (aucune archive) ;
  - procédures : sudocuh_procedures (approbation_opp datée par commune,
    prescription_proc pour les procédures EN COURS seulement — l'historique des
    procédures closes n'existe pas → « commune en procédure as-of » incomplet).

La SEULE variable proprement as-of : l'ancienneté du PLU servi
(anciennete_plu_annees, mesurée au K0) — manquant explicite pour les années
antérieures à l'approbation (l'approbation précédente est inconnue).

Usage : .venv/bin/python scripts/audit/scoring/donnees1_e.py inventaire|k0
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donnees1_commun as dc  # noqa: E402
from donnees1_commun import OUT, _ARENE, log  # noqa: E402
from _common import engine  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec  # noqa: E402


def inventaire() -> None:
    eng = engine()
    er = pd.read_sql("""
        SELECT count(*) FILTER (WHERE attrs->>'libelle' = 'Emplacement réservé') AS er,
               count(*) AS prescriptions
        FROM spatial_layers WHERE kind = 'plu_gpu_prescription'""", eng).iloc[0]
    kinds = pd.read_sql(
        "SELECT string_agg(DISTINCT kind, ', ') AS kinds FROM spatial_layers",
        eng).iloc[0, 0]
    sud = pd.read_sql(
        "SELECT count(*) AS n, count(prescription_proc) AS en_proc, "
        "count(approbation_opp) AS avec_appro, min(approbation_opp) AS amin, "
        "max(approbation_opp) AS amax FROM sudocuh_procedures", eng).iloc[0]
    inv = pd.DataFrame([
        {"objet": "emplacements réservés",
         "existence": f"OUI — {int(er['er'])} polygones GPU "
                      f"(sur {int(er['prescriptions'])} prescriptions surfaciques)",
         "asof": "NON (un seul millésime GPU) → documenté, pas mesuré",
         "preuve": "spatial_layers kind='plu_gpu_prescription', attrs.libelle"},
        {"objet": "OAP", "existence": "ABSENTES des couches en base",
         "asof": "—", "preuve": f"kinds spatial_layers : {kinds[:180]}…"},
        {"objet": "ZAC", "existence": "ABSENTES des couches en base "
         "(le SAR et le potentiel foncier existent, pas les périmètres ZAC)",
         "asof": "—", "preuve": "même liste de kinds"},
        {"objet": "changement de zonage entre millésimes GPU",
         "existence": "IMPOSSIBLE : aucune archive de zonage géométrique "
                      "(cf. Lot A2) ; plu_reglement_extrait = textes seulement",
         "asof": "—", "preuve": "a2_inventaire_asof.csv"},
        {"objet": "commune en procédure (outil Procédure)",
         "existence": f"sudocuh_procedures : {int(sud['n'])} communes, "
                      f"{int(sud['en_proc'])} en procédure (prescription datée), "
                      f"approbation du PLU servi datée pour {int(sud['avec_appro'])} "
                      f"({sud['amin']} → {sud['amax']}) ; + registre humain "
                      "config/veille_plu.yaml (dates d'acte, débat PADD)",
         "asof": "PARTIEL : les procédures CLOSES n'ont pas d'historique → "
                 "« en procédure au 01/01/Y » irreconstructible ; l'ANCIENNETÉ du "
                 "PLU approuvé est elle proprement as-of → mesurée au K0",
         "preuve": "sudocuh_procedures.prescription_proc / approbation_opp"},
    ])
    inv.to_csv(OUT / "e1_inventaire_plu.csv", index=False)
    print(inv.to_string(index=False))


SPECS_E = [
    FeatureSpec("anciennete_plu_annees", "Z", "num", 0,
                "années écoulées au 01/01/Y depuis l'approbation du PLU de la "
                "commune (sudocuh_procedures.approbation_opp) ; PLU approuvé "
                "APRÈS asof → manquant explicite (l'approbation précédente est "
                "inconnue de la base)", "as-of 01/01/Y", _ARENE,
                "un PLU jeune ouvre des zones : signal d'offre nouvelle"),
]


def k0() -> None:
    eng = engine()
    sud = pd.read_sql(
        "SELECT insee, approbation_opp FROM sudocuh_procedures "
        "WHERE approbation_opp IS NOT NULL", eng)
    df, _ = dc.base_enrichie(eng)
    cols = df[["idu", "annee"]].copy()
    cols["insee"] = cols["idu"].str.slice(0, 5)
    cols = cols.merge(sud, on="insee", how="left")
    asof = pd.to_datetime(cols["annee"].astype(str) + "-01-01")
    appro = pd.to_datetime(cols["approbation_opp"])
    anc = (asof - appro).dt.days / 365.25
    cols["anciennete_plu_annees"] = anc.where(anc >= 0)
    cols = cols[["idu", "annee", "anciennete_plu_annees"]]
    couv = (cols.assign(connue=cols["anciennete_plu_annees"].notna())
            .groupby("annee")["connue"].mean().mul(100).round(1))
    couv.to_csv(OUT / "e2_couverture_anciennete_plu.csv")
    print(couv.to_string())
    dc.mesurer("E_anciennete_plu_annees", SPECS_E, colonnes=cols)


if __name__ == "__main__":
    {"inventaire": inventaire, "k0": k0}[
        sys.argv[1] if len(sys.argv) > 1 else "inventaire"]()
