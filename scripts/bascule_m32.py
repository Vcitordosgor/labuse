"""BASCULE M32 — intégration AU 21 communes + départage (GO Vic). Remplacement sous label
(archive q_v8_calibre_pre_m32 par RENOMMAGE), conformité STRICTE q_v13_m32_mesure, écarts admis =
le REGISTRE seul (5 entrées : 4 M28 + AL1154 piscine). 6 gardes + check_fraicheur.
Pré-requis : cache parcel_au_statut reconstruit (config 21 communes corrigée) AVANT le re-scoring.
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope
from labuse.bascule_gardes import (check_run_absent, check_disque, check_peremption,
                                   ensure_backups, verify_completude, check_fraicheur, _ts)

LABEL, ARCHIVE, MESURE = "q_v8_calibre", "q_v8_calibre_pre_m32", "q_v13_m32_mesure"
REGISTRE = [
    ("97422000AK1442", "a_creuser",
     "V1 (M28) : piscine centrale FLAIR 88 m² (PVA 2025) — piscine ≠ terrain nu ; a_creuser, dette #13"),
    ("97419000AL1154", "a_creuser",
     "M32 (Vic) : piscine détectée (FLAIR 0,888, PVA 2025) — comme AK1442 ; a_creuser, dette #13"),
    ("97404000AP0323", None,
     "V2 (M28) : servie telle quelle — CoSIA 18 m² sous seuil (PVA 2025), ratio 0 % confirmé"),
    ("97411000HE0234", None,
     "V3 opt. c (M28) : servie, badge géométrie non applicable (15,8 m, PP 0,424) — dette #12"),
    ("97404000AT0870", None,
     "A9 (M28) : angle mort image documenté — toiture ortho non captée BD TOPO/CoSIA ; exception doc"),
]

t0 = time.time()
# ── PRÉ : reconstruire le cache AU (config 21 communes corrigée) = l'état de la mesure ──
if os.environ.get("LABUSE_REPRISE") != "1":
    from labuse.faisabilite.au_ouverture import build_au_ouverture, _config
    with session_scope() as s:
        cpt = build_au_ouverture(s, list(_config().keys()))
    print(f"{_ts()} [0] cache AU reconstruit (21 communes) : {cpt}", flush=True)

with engine().connect() as c:
    n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()
    if (os.environ.get("LABUSE_REPRISE") != "1"
            and c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar()):
        raise SystemExit(f"{ARCHIVE} existe déjà — LABUSE_REPRISE=1 pour reprendre.")
print(f"{_ts()} BASCULE M32 ({n_parcels} parcelles). Archive : {ARCHIVE}.", flush=True)
check_disque(LABEL); check_peremption(None); ensure_backups()

if os.environ.get("LABUSE_REPRISE") != "1":
    with engine().begin() as c:
        for tbl, col in [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
                         ("score_snapshots", "run_label"), ("served_run_exceptions", "run_id")]:
            c.execute(text(f"UPDATE {tbl} SET {col}=:a WHERE {col}=:l"), {"a": ARCHIVE, "l": LABEL})
print("  [2] archivé (rename) — registre M28 existant suit l'archive", flush=True)
check_run_absent(LABEL)

os.environ["LABUSE_ETAGE0_RUN"] = LABEL
for k in ("LABUSE_DISABLE_FILTRE_BATI", "LABUSE_DISABLE_DEPARTAGE", "LABUSE_DISABLE_AU_POND",
          "LABUSE_DISABLE_BATI_REVELE", "LABUSE_DISABLE_BATI_COSIA", "LABUSE_DISABLE_AU_STATUT"):
    os.environ.pop(k, None)
from labuse.scoring.p_v2.pipeline import run_score_v2
with session_scope() as s:
    res = run_score_v2(s, run_id=LABEL, rebuild=False, snapshot=True)
print(f"  [4] scoring servi : {res['n']} parcelles, snapshot {res.get('snapshot')}", flush=True)

with engine().connect() as c:
    diffs = c.execute(text("""SELECT s.parcelle_id FROM parcel_p_score_v2 s
        JOIN parcel_p_score_v2 m ON m.parcelle_id=s.parcelle_id AND m.run_id=:m
        WHERE s.run_id=:l AND s.tier IS DISTINCT FROM m.tier"""),
        {"l": LABEL, "m": MESURE}).all()
if diffs:
    raise SystemExit(f"NON-CONFORME à {MESURE} : {len(diffs)} écarts {[d[0] for d in diffs[:8]]} — ROLLBACK.")
print(f"  [5] CONFORME STRICT à {MESURE} (0 écart avant registre)", flush=True)

with engine().begin() as c:
    for idu, override, motif in REGISTRE:
        nat = c.execute(text("SELECT tier FROM parcel_p_score_v2 WHERE run_id=:l AND parcelle_id=:i"),
                        {"l": LABEL, "i": idu}).scalar()
        servi = override or nat
        if override and override != nat:
            c.execute(text("UPDATE parcel_p_score_v2 SET tier=:t WHERE run_id=:l AND parcelle_id=:i"),
                      {"t": override, "l": LABEL, "i": idu})
        c.execute(text("INSERT INTO served_run_exceptions (run_id, idu, tier_origine, tier_servi, motif) "
                       "VALUES (:l, :i, :o, :s, :m)"),
                  {"l": LABEL, "i": idu, "o": nat, "s": servi, "m": motif})
        print(f"  [6] registre {idu}: {nat} → {servi}", flush=True)

counts = verify_completude(LABEL, n_expected_cascade=n_parcels, n_expected_scores=n_parcels)
print(f"  [7] complétude : {counts}", flush=True)
check_fraicheur()   # garde de fraîcheur (bruyante, non bloquante) — arbitrage Vic
with engine().connect() as c:
    dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:l GROUP BY 1 ORDER BY 2 DESC"),
                     {"l": LABEL}).all()
print(f"\n✓ BASCULE M32 (scoring) en {time.time()-t0:.0f}s. Tiers servis :")
for tier, n in dist:
    print(f"  {tier:28s} {n:>8}")
print("  SUITE : golden_regen (6e garde) ; build-mvt ; SDP bâti_revele ; recompte.")
