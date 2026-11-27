#!/usr/bin/env python
"""OUTIL-COMMUNES-FIX-10 LOT 1 — PREUVE : la fiche ne sert plus la phrase de marché STOCKÉE dans le
classement (cascade `dvf`, plancher de 3 au build), elle la RE-DÉRIVE à la lecture via la fonction
UNIQUE `dvf_secteur.prix_section` (seuil public 8). Sous le seuil : échantillon insuffisant, AUCUN
prix, AUCUN « contexte de marché favorable ».

Montre le cas du rapport (97412000AY0082, Saint-Joseph) : STOCKÉ « 50 €/m² — 6 ventes … favorable »
vs RE-DÉRIVÉ « échantillon insuffisant (1 vente) ». Chiffre la dérive et dit si le signal entre au score.

Usage :
    LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    PYTHONPATH=src /Users/openclaw/Desktop/labuse-main/.venv/bin/python scripts/communes_fix10_marche.py
"""
from __future__ import annotations

import os
import sys

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse import runs
from labuse.api.app import _dvf_terrain_detail_servi
from labuse.dvf_secteur import prix_section, seuil_section


def main() -> int:
    url = os.environ.get("LABUSE_TEST_DATABASE_URL")
    if not url:
        print("LABUSE_TEST_DATABASE_URL manquant", file=sys.stderr)
        return 2
    eng = create_engine(url)
    with Session(eng) as s:
        casc = runs.cascade()
        seuil = seuil_section()
        print(f"run de cascade servi : {casc} · seuil public de diffusion : {seuil}")

        # ── Cas du rapport : 97412000AY0082 (Saint-Joseph) ───────────────────────────────────────────
        idu = "97412000AY0082"
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        stored = s.execute(text(
            "SELECT detail FROM dryrun_cascade_results WHERE run_label=:r AND parcel_id=:p AND layer_name='dvf'"),
            {"r": casc, "p": pid}).scalar()
        live = prix_section(s, idu[:10], "terrain")
        servi = _dvf_terrain_detail_servi(s, idu)
        print(f"\n{idu} — section {idu[:10]}")
        print(f"  STOCKÉ au classement  : {stored}")
        print(f"  section LIVE (seuil 8): n={live['n']} · prix_m2={live['prix_m2']}")
        print(f"  RE-DÉRIVÉ servi (fix) : {servi}")
        ok_ay = ("50" not in servi and "6 ventes" not in servi and "favorable" not in servi.lower()
                 and "insuffisant" in servi and "1 vente" in servi)

        # ── Dérive globale : combien de « favorable » stockés reposent sur < 8 ventes ────────────────
        tot = s.execute(text(
            "SELECT count(*) FROM dryrun_cascade_results WHERE run_label=:r AND layer_name='dvf' "
            "AND detail ILIKE '%favorable%'"), {"r": casc}).scalar()
        sous8 = s.execute(text(
            "SELECT count(*) FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
            "WHERE cr.run_label=:r AND cr.layer_name='dvf' AND cr.detail ILIKE '%favorable%' "
            "AND NOT EXISTS (SELECT 1 FROM dvf_secteur_medianes m "
            "                WHERE m.secteur=left(p.idu,10) AND m.type_bien='terrain' AND m.n_ventes>=8)"),
            {"r": casc}).scalar()
        print(f"\nDÉRIVE : {tot} parcelles portent « contexte de marché favorable » stocké ; "
              f"{sous8} reposent sur une section à MOINS de 8 ventes (seuil public) aujourd'hui.")

        # ── Le signal entre-t-il au SCORE ? (poids config) ───────────────────────────────────────────
        wcfg = yaml.safe_load(open("config/opportunity_weights.yaml"))
        poids = (wcfg.get("bonuses") or {}).get("contexte_dvf_favorable")
        print(f"ENTRE AU SCORE : oui — bonus `contexte_dvf_favorable` = {poids} points (× magnitude) "
              f"dans le score d'opportunité (config/opportunity_weights.yaml). Le classement q_v20 étant "
              f"GELÉ (interdit de le modifier), le correctif agit à l'AFFICHAGE + sur le CALCUL FUTUR "
              f"(cascade/layers/phase2.py passe désormais par le seuil 8).")

        print(f"\n{'='*84}")
        if ok_ay and poids is not None:
            print("SUCCÈS : la fiche re-dérive la ligne DVF (seuil 8) ; sous le seuil, ni prix ni qualificatif.")
            return 0
        print(f"ÉCHEC : ok_ay={ok_ay} poids={poids}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
