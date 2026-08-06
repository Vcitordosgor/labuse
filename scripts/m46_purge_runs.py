"""M46 Lot B — purge des runs archivés `q_v8_calibre_pre_*` (avec GARDE d'usage).

Doctrine (règle permanente M46) : AUCUNE suppression sans preuve qu'aucun code/config/test ne
lit le label. Ce script matérialise cette preuve : il REFUSE de purger un label lu par du code
vivant, et ne purge que ceux dont l'inutilité est prouvée. Idempotent (re-run = no-op).

Constat sur pièces (M46) :
  - `q_v8_calibre_pre_m32`  → PURGEABLE : aucun lecteur vivant (seul `scripts/bascule_m32.py`,
    script historique déjà exécuté, le cite ; absent de `lignee_tete.CHAINE_GESTES`). PURGÉ.
  - `q_v8_calibre_pre_pond` → **REFUSÉ** : LU par `labuse/scoring/lignee_tete.py` (CHAINE_GESTES,
    geste « pondération AU ») qui alimente `parcel_entree_tete` (signal fiche servi, dette #9).
    Le purger casserait le calcul de l'entrée-en-tête à la prochaine bascule. → à arbitrer par Vic
    (adapter lignee_tete d'abord, OU conserver l'archive).
  - `q_v8_calibre_pre_regle`, `q_v8_calibre_pre_m28` → **REFUSÉS** : idem, lus par CHAINE_GESTES.
  - `q_v8_calibre_pre_m39`  → **CONSERVÉ** : rollback de la bascule M39 du 06/08 (mandat).
Runs hors périmètre M46 (autres lignées, non touchés) : q_v7_defisc (dette), q_v12_m28, q_v13_m32_mesure.

Usage : PYTHONPATH=src python scripts/m46_purge_runs.py [--apply]   (défaut : dry-run).
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")

from sqlalchemy import text  # noqa: E402

from labuse.db import engine  # noqa: E402

PURGEABLES = ("q_v8_calibre_pre_m32",)   # prouvés sans lecteur vivant
PROTEGES = {                             # lus par du code vivant OU rollback → JAMAIS purgés ici
    "q_v8_calibre_pre_pond": "lu par lignee_tete.CHAINE_GESTES (parcel_entree_tete, dette #9)",
    "q_v8_calibre_pre_regle": "lu par lignee_tete.CHAINE_GESTES",
    "q_v8_calibre_pre_m28": "lu par lignee_tete.CHAINE_GESTES",
    "q_v8_calibre_pre_m39": "rollback de la bascule M39 (06/08) — conservé",
}
# (label_col par table portant un run q_v8_calibre_pre_*)
TABLES = [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
          ("score_snapshots", "run_label"), ("served_run_exceptions", "run_label")]


def _labels_lus_par_lignee() -> set[str]:
    """GARDE dynamique (arbitrage Vic M46-LotE) : la chaîne d'archives de `lignee_tete` est la
    SOURCE du signal servi `parcel_entree_tete` (dette #9). Tout label qui y figure est une
    DÉPENDANCE PRODUIT — jamais un déchet purgeable. Lu dynamiquement pour rester en phase : si un
    geste futur référence une nouvelle archive, elle est protégée automatiquement."""
    from labuse.scoring.lignee_tete import CHAINE_GESTES
    lus: set[str] = set()
    for avant, apres, *_ in CHAINE_GESTES:
        lus.update((avant, apres))
    return lus


def main() -> None:
    apply = "--apply" in sys.argv
    lignee = _labels_lus_par_lignee()
    # GARDE : refuser tout PURGEABLE lu par lignee_tete (dépendance produit) — avant tout DELETE.
    conflit = [lbl for lbl in PURGEABLES if lbl in lignee]
    if conflit:
        raise SystemExit(f"REFUS : {conflit} est lu par lignee_tete.CHAINE_GESTES "
                         "(source de parcel_entree_tete, dette #9). Purge interdite — mandat dédié requis.")
    print(f"garde lignee_tete : {sorted(lignee)} PROTÉGÉS (dépendance produit)\n")
    with engine().connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        for label in PURGEABLES:
            total = 0
            for t, col in TABLES:
                cols = [x[0] for x in c.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=:t"), {"t": t})]
                col = col if col in cols else ("run_id" if "run_id" in cols else "run_label")
                n = c.execute(text(f"SELECT count(*) FROM {t} WHERE {col}=:l"), {"l": label}).scalar() or 0
                if n and apply:
                    c.execute(text(f"DELETE FROM {t} WHERE {col}=:l"), {"l": label})
                total += n
                print(f"  {t}.{col} = {label} : {n} ligne(s){' → SUPPRIMÉES' if (n and apply) else ''}")
            if apply and total:
                c.execute(text("VACUUM ANALYZE parcel_p_score_v2"))
        print("\nPROTÉGÉS (jamais purgés — preuve d'usage) :")
        for lbl, why in PROTEGES.items():
            print(f"  {lbl} : {why}")
        if not apply:
            print("\n(dry-run — relancer avec --apply pour purger les PURGEABLES)")


if __name__ == "__main__":
    main()
