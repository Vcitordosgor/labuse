#!/usr/bin/env python
"""OUTIL-SCAN-FIX-2 (item 6) — SÉQUENCE DE BASCULE 2026 pour la base commune `labuse` (locale) ou prod.

NON EXÉCUTÉE par l'agent : Vic choisit le moment (d'autres sessions utilisent la base). Lancer À LA MAIN :

    export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
    .venv/bin/python scripts/bascule_2026_labuse.py --dry-run     # inspection, n'écrit rien
    .venv/bin/python scripts/bascule_2026_labuse.py --go          # applique (fenêtre contrôlée)

Ordre impératif (chaque étape idempotente, relançable) :
  0. SAUVEGARDE rollback : dump des DEUX tables servies touchées (parcelle_personne_morale +
     pm_proprietaires_millesimes). parcelle_pm_droit est ADDITIVE (droppable).
  1. `parcelle_pm_droit` 2025 ET 2026 (tous titulaires/droits) — ADDITIF, aucun lecteur existant touché.
  2. ARCHIVE 2025 par la MÊME RÈGLE (principal propriétaire-first) dans pm_proprietaires_millesimes
     → SCAN-FIX-2 (M3) : Communes ne montrera que les VRAIS changements (≈963), pas les ≈1 056 artefacts.
  3. FLIP : parcelle_personne_morale = titulaire principal 2026 (via injection_sure.remplacer_servie :
     staging LIKE, contrôles, SWAP atomique sous ACCESS EXCLUSIVE ; refus = table servie intacte).
  4. RAFRAÎCHIR bodacc_depots (fait daté « dernier dépôt », cas 449090075) : `labuse ingest-bodacc-depots`.
  5. RECALCUL V-SCORE derrière le flip (le classement lit parcelle_personne_morale : 2 711 SIREN / 3 989
     groupes changent) : `labuse p-score-v2 --label <nouveau_run> --rebuild` puis promotion du run.
  (programmes et sirene_etablissements sont DÉJÀ en base `labuse` — 9 et ~155 505 — rien à recharger ;
   seule ma base dédiée scanfix en manquait. Si une base cible les a vides, recharger : programmes via
   l'admin `/admin/programmes/collecter+valider`, sirene via `labuse ingest-sirene-etab`.)
"""
from __future__ import annotations

import sys


def main(go: bool) -> None:
    from labuse.db import session_scope
    from labuse.ingestion import pm_droits, pm_millesimes
    from sqlalchemy import text

    with session_scope() as s:
        # état avant
        n_pm = s.execute(text("SELECT count(*) FROM parcelle_personne_morale")).scalar()
        mil = s.execute(text("SELECT max(millesime) FROM parcelle_personne_morale")).scalar()
        print(f"[état] parcelle_personne_morale : {n_pm} lignes, millésime servi {mil}")
        if not go:
            print("[dry-run] AUCUNE écriture. Étapes qui SERAIENT faites :")
            print("  1. ingest_droits(2025) + ingest_droits(2026) → parcelle_pm_droit")
            print("  2. archive_principal_depuis_droits('2025') → pm_proprietaires_millesimes (même règle)")
            print("  3. recompute_principal('2026') → flip parcelle_personne_morale (swap atomique)")
            print("  4. `labuse ingest-bodacc-depots` (hors de ce script)")
            print("  5. recalcul V-score + promotion du run (hors de ce script)")
            return

        # 1. droits 2025 + 2026 (additif)
        pm_droits.ingest_droits(s, pm_millesimes.fetch_974_csv(2025), "2025", log=print)
        pm_droits.ingest_droits(s, pm_droits.fetch_974_csv(), "2026", log=print)
        # 2. archive 2025 par la même règle (M3)
        pm_droits.archive_principal_depuis_droits(s, "2025", log=print)
        # 3. flip principal 2026 (swap atomique, invariante 1-ligne/idu re-contrôlée par le garde-fou)
        pm_droits.recompute_principal(s, "2026", log=print)
        print("[OK] bascule données faite. ENSUITE, hors script : "
              "`labuse ingest-bodacc-depots` puis recalcul V-score + promotion du run.")


if __name__ == "__main__":
    go = "--go" in sys.argv
    if not go and "--dry-run" not in sys.argv:
        print("Précise --dry-run (sûr) ou --go (applique). Rien fait."); sys.exit(2)
    main(go)
