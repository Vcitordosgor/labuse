"""OUTIL-PERMIS-FIX-12 (LOT 2) — EXÉCUTION de la mise à niveau des anciennes alertes sur `labuse`.

Autorisé par Vic : la table `alertes` et elle SEULE. Aucune réémission (jamais `event_log`).

Déroulé (par défaut) :
  1. garde-fou DUR : refuse si `current_database() <> 'labuse'` ;
  2. empreinte AVANT + diagnostic (combien à corriger / combien « déposé » à dépôt invalide) ;
  3. TEST du rollback SUR COPIE, dans une sous-transaction ANNULÉE (sauvegarde → corriger → rollback →
     empreinte restaurée == AVANT) — ne persiste rien ;
  4. MIGRATION réelle : sauvegarde datée → corriger → empreinte APRÈS → vérifie 0 « déposé » invalide
     → COMMIT ;
  5. rappelle la commande de retour arrière.

  --rollback <table>   restaure label/payload depuis une table de sauvegarde `alertes_bak_fix12__*`.
  --dry                s'arrête après l'étape 3 (aucune écriture persistée).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse import alertes_migration as mig  # noqa: E402
from labuse import permis_classe  # noqa: E402
from labuse.db import session_scope  # noqa: E402


def _garde(s) -> None:
    base = s.execute(text("SELECT current_database()")).scalar()
    if base != "labuse":
        raise SystemExit(f"REFUS — base courante {base!r} ≠ 'labuse' (migration autorisée sur labuse seule)")


def migrer(dry: bool) -> int:
    with session_scope() as s:
        _garde(s)
        avant = mig.empreinte(s)
        diag = mig.a_corriger(s)
        print(f"AVANT     : {avant['n']} alertes permis_in_zone · md5={avant['md5']}")
        print(f"diagnostic: à corriger {diag['a_corriger']} · « déposé » à dépôt invalide {diag['deposes_invalides']}")

        # 3 · TEST du rollback sur copie (sous-transaction annulée → rien ne persiste)
        sp = s.begin_nested()
        bak_test = mig.sauvegarder(s, suffix="test_rollback")
        n_test = mig.corriger(s)
        restaure = mig.rollback(s, bak_test)
        apres_rb = mig.empreinte(s)
        ok_rb = (apres_rb == avant)
        sp.rollback()
        print(f"TEST copie: corrigées {n_test} → rollback {restaure} → empreinte restaurée == AVANT : {ok_rb}")
        if not ok_rb:
            raise SystemExit("REFUS — le rollback ne restaure pas l'empreinte d'origine")
        if dry:
            print("--dry : arrêt avant écriture réelle.")
            return 0

        # 4 · MIGRATION réelle
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = mig.sauvegarder(s, suffix=suffix)
        n = mig.corriger(s)
        apres = mig.empreinte(s)
        restant = s.execute(text(
            "SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id = a.source_ref "
            "WHERE a.kind='permis_in_zone' AND a.label ILIKE '%déposé%' "
            "AND NOT (" + permis_classe.depot_affichable_cond_sql("sp.") + ")")).scalar()
        print(f"sauvegarde: {bak}")
        print(f"corrigées : {n}")
        print(f"APRÈS     : {apres['n']} alertes · md5={apres['md5']}")
        print(f"« Permis déposé » à dépôt INVALIDE restantes : {restant} (attendu 0)")
        if restant != 0:
            raise SystemExit(f"REFUS — il reste {restant} alertes « déposé » à dépôt invalide (pas de commit)")
        # session_scope commit à la sortie du bloc
        print(f"\nRETOUR ARRIÈRE : labuse ... --rollback {bak}")
    return 0


def rollback(table: str) -> int:
    with session_scope() as s:
        _garde(s)
        avant = mig.empreinte(s)
        n = mig.rollback(s, table)
        apres = mig.empreinte(s)
        print(f"rollback depuis {table} : {n} lignes · {avant['md5']} → {apres['md5']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollback", metavar="TABLE", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.rollback:
        return rollback(a.rollback)
    return migrer(a.dry)


if __name__ == "__main__":
    raise SystemExit(main())
