"""BASCULE M28 — filtre client bâti + départage + badges (GO Vic 05/08, phase B).
Remplacement sous label (archive q_v8_calibre_pre_m28 par RENOMMAGE), conformité STRICTE
q_v12_m28, écart admis : AK1442 (V1) seul. Registre : V1 (override) + V2/V3/AT0870
(documentaires, tier inchangé). 6 gardes."""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope
from labuse.bascule_gardes import (check_run_absent, check_disque, check_peremption,
                                   ensure_backups, verify_completude, _ts)

LABEL, ARCHIVE, MESURE = "q_v8_calibre", "q_v8_calibre_pre_m28", "q_v12_m28"
REGISTRE = [
    # (idu, tier_override_ou_None, motif)
    ("97422000AK1442", "a_creuser",
     "V1 (Vic 05/08) : piscine centrale détectée (FLAIR, 88 m² intersectés, PVA 2025) — "
     "une piscine centrale ≠ terrain nu ; non servie en brûlante, tier a_creuser, "
     "en attente du signal piscine (phase 2)"),
    ("97404000AP0323", None,
     "V2 (Vic 05/08) : servie telle quelle — CoSIA 18 m² sous seuil (PVA 2025), aucune "
     "piscine ; ratio 0 % confirmé"),
    ("97411000HE0234", None,
     "V3 option c (Vic 05/08) : servie, badge géométrie non applicable (largeur 15,8 m, "
     "PP 0,424 — Sourcé cadastre 2026-06) ; nature « délaissé de voirie » non mesurable "
     "en l'état — dette #12 (couche voirie surfacique absente)"),
    ("97404000AT0870", None,
     "A9 (Vic 05/08) : angle mort image documenté — toiture visible ortho (PVA 21/07/2025) "
     "non captée par BD TOPO éd. 2026-06-15 (3 m²) ni CoSIA PVA 2025 (5 m²) ; PAS de code, "
     "exception documentaire"),
]

t0 = time.time()
with engine().connect() as c:
    n_parcels = c.execute(text("SELECT count(*) FROM parcels")).scalar()
    if (os.environ.get("LABUSE_REPRISE") != "1"
            and c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:a"), {"a": ARCHIVE}).scalar()):
        raise SystemExit(f"{ARCHIVE} existe déjà — LABUSE_REPRISE=1 pour reprendre.")
print(f"{_ts()} BASCULE M28 ({n_parcels} parcelles). Archive : {ARCHIVE}.", flush=True)
check_disque(LABEL); check_peremption(None); ensure_backups()

if os.environ.get("LABUSE_REPRISE") != "1":
    with engine().begin() as c:
        for tbl, col in [("parcel_p_score_v2", "run_id"), ("p_score_v2_runs", "run_id"),
                         ("score_snapshots", "run_label"), ("served_run_exceptions", "run_id")]:
            c.execute(text(f"UPDATE {tbl} SET {col}=:a WHERE {col}=:l"), {"a": ARCHIVE, "l": LABEL})
print("  [2] archivé (rename) — journal existant (CY0104…) suit l'archive", flush=True)
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
    raise SystemExit(f"NON-CONFORME à q_v12 : {len(diffs)} écarts {[d[0] for d in diffs[:5]]} — ROLLBACK.")
print("  [5] CONFORME STRICT à q_v12_m28 (0 écart avant registre)", flush=True)

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
with engine().connect() as c:
    dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:l GROUP BY 1 ORDER BY 2"),
                     {"l": LABEL}).all()
print(f"\n✓ BASCULE M28 COMPLÈTE en {time.time()-t0:.0f}s. Tiers servis :")
for tier, n in dist:
    print(f"  {tier:28s} {n:>8}")
print("  SUITE : build-mvt ; API LABUSE_M28_BADGES=1 ; golden_regen (+CY0104) ; rapport.")
