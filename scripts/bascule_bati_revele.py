"""BASCULE RÈGLE « BÂTIE RÉVÉLÉE » + emprise max(BD TOPO, CoSIA) — GO Vic 04/08 (option 1).

Remplacement du scoring sous label (v2 épinglé Q_A_RUN_LABEL, cascade inchangée) :
archive par RENOMMAGE (q_v8_calibre_pre_regle — rien détruit), features re-matérialisées
CoSIA ON + règle ON (protocole IDENTIQUE à la mesure validée q_v11_regle_apres), re-score,
CONFORMITÉ STRICTE ≡ q_v11 (échec bruyant sinon), exception CY0104 (arbitrage), 6 gardes.
Rollback : renommage inverse + rebuild features kill-switch ON.
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope
from labuse.bascule_gardes import (check_run_absent, check_disque, check_peremption,
                                   ensure_backups, verify_completude, check_golden_regenere,
                                   GoldenPerimeError, _ts)

LABEL, ARCHIVE, MESURE = "q_v8_calibre", "q_v8_calibre_pre_regle", "q_v11_regle_apres"
CY = "97415000CY0104"
MOTIF_CY = ("bâti vérifié ortho Vic 04/08 — connu BD TOPO (164 m²) et CoSIA (185 m²), "
            "en attente du filtre client bâti (train 5)")

t0 = time.time()
with engine().connect() as c:
    n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()
    if (os.environ.get("LABUSE_REPRISE") != "1"
            and c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar()):
        raise SystemExit(f"{ARCHIVE} existe déjà — bascule déjà passée ? (LABUSE_REPRISE=1 pour reprendre)")
print(f"{_ts()} BASCULE BÂTIE RÉVÉLÉE ({n_parcels} parcelles). Archive : {ARCHIVE}.", flush=True)
check_disque(LABEL); check_peremption(None); ensure_backups()

if os.environ.get("LABUSE_REPRISE") != "1":               # archive par renommage (1er passage)
    with engine().begin() as c:
        for tbl, col in [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
                         ("score_snapshots", "run_label"), ("served_run_exceptions", "run_id")]:
            c.execute(text(f"UPDATE {tbl} SET {col}=:a WHERE {col}=:l"), {"a": ARCHIVE, "l": LABEL})
print(f"  [2] archivé (rename) — le journal des 17 suit l'archive (remplacées par la règle)", flush=True)
check_run_absent(LABEL)

os.environ["LABUSE_ETAGE0_RUN"] = LABEL                  # protocole ≡ mesure q_v11
for k in ("LABUSE_DISABLE_BATI_COSIA", "LABUSE_DISABLE_BATI_REVELE",
          "LABUSE_DISABLE_AU_POND", "LABUSE_DISABLE_AU_STATUT"):
    os.environ.pop(k, None)
from labuse.scoring.p_model import sql as p_sql
from labuse.scoring.p_v2.pipeline import run_score_v2
if os.environ.get('LABUSE_REPRISE') != '1':
    with session_scope() as s:
        p_sql.build_bati(s); p_sql.build_static(s); s.commit()
print(f"  [4a] features max(BD TOPO, CoSIA) matérialisées ({time.time()-t0:.0f}s)", flush=True)
with session_scope() as s:
    res = run_score_v2(s, run_id=LABEL, rebuild=(os.environ.get('LABUSE_REPRISE') != '1'), snapshot=True)
print(f"  [4b] scoring servi : {res['n']} parcelles, snapshot {res.get('snapshot')}", flush=True)

with engine().connect() as c:                            # conformité STRICTE avant exception
    diffs = c.execute(text("""
        SELECT s.parcelle_id FROM parcel_p_score_v2 s
        JOIN parcel_p_score_v2 m ON m.parcelle_id=s.parcelle_id AND m.run_id=:m
        WHERE s.run_id=:l AND s.tier IS DISTINCT FROM m.tier"""),
        {"l": LABEL, "m": MESURE}).all()
if diffs:
    raise SystemExit(f"NON-CONFORME à q_v11 : {len(diffs)} écarts ({[d[0] for d in diffs[:5]]}) — ROLLBACK.")
print("  [5] CONFORME STRICT à la mesure validée q_v11 (0 écart)", flush=True)

with engine().begin() as c:                              # exception CY0104 (arbitrage Vic)
    nat = c.execute(text("SELECT tier FROM parcel_p_score_v2 WHERE run_id=:l AND parcelle_id=:i"),
                    {"l": LABEL, "i": CY}).scalar()
    c.execute(text("UPDATE parcel_p_score_v2 SET tier='declasse_non_constructible' "
                   "WHERE run_id=:l AND parcelle_id=:i"), {"l": LABEL, "i": CY})
    c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif) "
                   "VALUES (:l, :i, :o, 'declasse_non_constructible', :m)"),
              {"l": LABEL, "i": CY, "o": nat, "m": MOTIF_CY})
print(f"  [6] CY0104 : {nat} → declasse_non_constructible (journalisée, motif corrigé)", flush=True)

counts = verify_completude(LABEL, n_expected_cascade=n_parcels, n_expected_scores=n_parcels)
print(f"  [7] complétude : {counts}", flush=True)
with engine().connect() as c:
    dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:l GROUP BY 1 ORDER BY 2"),
                     {"l": LABEL}).all()
print(f"\n✓ BASCULE COMPLÈTE en {time.time()-t0:.0f}s. Tiers servis :")
for tier, n in dist:
    print(f"  {tier:28s} {n:>8}")
try:
    check_golden_regenere(LABEL)
    print("  [8] golden à jour")
except GoldenPerimeError as e:
    print(f"  [8] ⚠ GARDE GOLDEN : régénérer dans le même geste (build-mvt, API, golden_regen).")
print("  SUITE : build-mvt ; golden_regen ; purge q_v10/q_v11 ; rapport.")
