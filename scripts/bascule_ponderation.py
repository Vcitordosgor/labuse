"""BASCULE PONDÉRATION au_sous_plancher (option B) — GO Vic 04/08, régime [S].

La pondération ne change QUE l'étage scoring v2 ; la cascade q_v8_calibre reste valide.
Le run v2 servi étant ÉPINGLÉ AU LABEL (Q_A_RUN_LABEL, app.py fix pré-lancement), la
procédure est un REMPLACEMENT SOUS LABEL, sans rien détruire :

  1. GARDES (module bascule_gardes du train 2) : disque, péremption, sauvegardes.
  2. ARCHIVE par RENOMMAGE : scoring q_v8_calibre → q_v8_calibre_pre_pond
     (parcel_p_score_v2, p_score_v2_runs, score_snapshots, served_run_exceptions).
     Rien n'est supprimé — ROLLBACK = python scripts/rollback_ponderation.py.
  3. GARDE anti-écrasement : check_run_absent('q_v8_calibre') doit passer post-rename.
  4. RE-SCORE sous le label servi : pondération ON, étage 0 q_v8_calibre, rebuild=False
     (features inchangées depuis v8 — le servi DOIT être exactement la mesure validée),
     snapshot inclus. Hystérésis prev = l'archive (mêmes tiers que la mesure).
  5. EXCEPTIONS (arbitrage Vic 04/08) : CX2555 LEVÉE (aucun override — le naturel fait
     foi) ; CH1893 PÉRENNISÉE (override + journal, motif dicté).
  6. GARDE complétude : verify_completude('q_v8_calibre', n, n) — cascade intacte,
     scores/snapshot/header du nouveau scoring complets.
  7. CONFORMITÉ À LA MESURE : tiers servis ≡ q_v9_pond_apres, écart attendu = {CH1893}.
Étapes suivantes (hors script) : labuse build-mvt --label q_v8_calibre (tuiles MVT
embarquent tier_v2) ; golden_check ; purge des jetables (arbitrage 6).
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope
from labuse.bascule_gardes import (
    check_run_absent, check_disque, check_peremption, ensure_backups, verify_completude,
    RunDejaExistantError, _ts)

LABEL = "q_v8_calibre"
ARCHIVE = "q_v8_calibre_pre_pond"
MESURE = "q_v9_pond_apres"          # la mesure à blanc validée par Vic
CH1893 = "97414000CH1893"
CX2555 = "97413000CX2555"
MOTIF_CH1893 = ("couche bâtiment lacunaire, vérifié ortho 04/08, à lever au rechargement "
                "de la couche (dette racine train 5 — cf. TRAIN1_PONDERATION_RAPPORT)")


def main():
    t0 = time.time()
    with engine().connect() as c:
        n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()
        if c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar():
            raise SystemExit(f"{ARCHIVE} existe déjà — bascule déjà passée ? rollback d'abord.")
    print(f"{_ts()} BASCULE PONDÉRATION → remplacement scoring sous {LABEL} "
          f"({n_parcels} parcelles). Archive : {ARCHIVE}.", flush=True)

    # 1 — gardes de démarrage
    check_disque(LABEL)
    check_peremption(None)
    ensure_backups()

    # 2 — archive par renommage (une transaction ; rien n'est détruit)
    with engine().begin() as c:
        c.execute(text("UPDATE parcel_p_score_v2 SET run_id=:a WHERE run_id=:l"),
                  {"a": ARCHIVE, "l": LABEL})
        c.execute(text("UPDATE p_score_v2_runs SET run_id=:a WHERE run_id=:l"),
                  {"a": ARCHIVE, "l": LABEL})
        c.execute(text("UPDATE score_snapshots SET run_label=:a WHERE run_label=:l"),
                  {"a": ARCHIVE, "l": LABEL})
        # journal d'exceptions : les rows décrivent l'état ARCHIVÉ (CX2555 chaude manuelle,
        # CH1893 v1) — elles suivent l'archive ; le nouveau run recevra SA row CH1893.
        c.execute(text("UPDATE served_run_exceptions SET run_id=:a WHERE run_id=:l"),
                  {"a": ARCHIVE, "l": LABEL})
    print(f"  [2] scoring archivé sous {ARCHIVE} (rename, zéro suppression)", flush=True)

    # 3 — anti-écrasement : le label doit être libre côté scoring
    n_free = check_run_absent(LABEL)
    print(f"  [3] label {LABEL} libre côté scoring ({n_free} parcelles attendues)", flush=True)

    # 4 — re-score sous le label servi, pondération ON (= la mesure validée)
    os.environ["LABUSE_ETAGE0_RUN"] = LABEL
    os.environ.pop("LABUSE_DISABLE_AU_POND", None)
    os.environ.pop("LABUSE_DISABLE_AU_STATUT", None)
    from labuse.scoring.p_v2.pipeline import run_score_v2
    with session_scope() as s:
        res = run_score_v2(s, run_id=LABEL, rebuild=False, snapshot=True)
    print(f"  [4] scoring servi re-calculé : {res['n']} parcelles, snapshot {res.get('snapshot')}", flush=True)

    # 5 — exceptions (arbitrage Vic) : CX2555 levée (rien) ; CH1893 pérennisée (override + journal)
    with engine().begin() as c:
        nat = c.execute(text("SELECT tier FROM parcel_p_score_v2 WHERE run_id=:l AND parcelle_id=:i"),
                        {"l": LABEL, "i": CH1893}).scalar()
        c.execute(text("UPDATE parcel_p_score_v2 SET tier='declasse_non_constructible' "
                       "WHERE run_id=:l AND parcelle_id=:i"), {"l": LABEL, "i": CH1893})
        c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif) "
                       "VALUES (:l, :i, :o, 'declasse_non_constructible', :m)"),
                  {"l": LABEL, "i": CH1893, "o": nat, "m": MOTIF_CH1893})
        cx = c.execute(text("SELECT tier, rang FROM parcel_p_score_v2 WHERE run_id=:l AND parcelle_id=:i"),
                       {"l": LABEL, "i": CX2555}).one()
    print(f"  [5] CH1893 pérennisée ({nat} → declasse_non_constructible, journalisée) ; "
          f"CX2555 LEVÉE — naturel servi : {cx.tier} rang {cx.rang}", flush=True)

    # 6 — garde complétude (cascade intacte + nouveau scoring complet)
    counts = verify_completude(LABEL, n_expected_cascade=n_parcels, n_expected_scores=n_parcels)
    print(f"  [6] complétude vérifiée : {counts}", flush=True)

    # 7 — conformité à la mesure validée : écart attendu = {CH1893} seul
    with engine().connect() as c:
        diffs = c.execute(text("""
            SELECT s.parcelle_id, m.tier AS mesure, s.tier AS servi
            FROM parcel_p_score_v2 s
            JOIN parcel_p_score_v2 m ON m.parcelle_id=s.parcelle_id AND m.run_id=:m
            WHERE s.run_id=:l AND s.tier IS DISTINCT FROM m.tier"""),
            {"l": LABEL, "m": MESURE}).all()
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:l "
                              "GROUP BY tier ORDER BY count(*)"), {"l": LABEL}).all()
    if [d[0] for d in diffs] != [CH1893]:
        raise SystemExit(f"NON-CONFORME à la mesure validée — écarts : {diffs[:10]} "
                         f"({len(diffs)} au total). NE PAS SERVIR — rollback.")
    print(f"  [7] CONFORME à la mesure validée (écart unique : CH1893, l'exception).", flush=True)

    print(f"\n✓ BASCULE PONDÉRATION COMPLÈTE en {time.time()-t0:.0f}s. Tiers servis :")
    for tier, n in dist:
        print(f"  {tier:28s} {n:>8}")
    print(f"\n  SUITE : build-mvt --label {LABEL} (tuiles) ; golden_check ; purge jetables.")
    print(f"  ROLLBACK : python scripts/rollback_ponderation.py")


if __name__ == "__main__":
    main()
