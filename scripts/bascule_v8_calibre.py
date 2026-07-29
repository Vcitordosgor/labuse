"""BASCULE v7 → v8 — le calibrage de 21 communes atteint le scoring servi.

Matérialise un NOUVEAU run servi `q_v8_calibre` :
  1. migration de données : parcel_residuel ← parcel_residuel_rerun (SDP calibrée) — la prod ;
  2. rebuild p_model_static (features résiduel) depuis le nouveau parcel_residuel ;
  3. run_score_v2(run_id='q_v8_calibre') : champion INCHANGÉ (sha gelé), features calibrées +
     déclassement (parcel_constructibilite) → nouveaux tiers, computed_at postérieur → dernier run.

`q_v7_defisc` est INTÉGRALEMENT conservé (aucune ligne touchée) → hystérésis / rollback.
Sauvegardes préalables requises : parcel_residuel_pre_v8, p_model_static_pre_v8 (créées à la main
avant la première bascule ; le script les crée si absentes).

Bascule des SURFACES (hors DB, à la charge de l'opérateur, comme A1) :
  export LABUSE_SERVED_RUN=q_v8_calibre ; (front) VITE_RUN_LABEL=q_v8_calibre npm run build ;
  labuse build-mvt --label q_v8_calibre.
Rollback : python scripts/rollback_v8_calibre.py  (+ re-pointer les surfaces sur q_v7_defisc).
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sqlalchemy import text
from labuse.db import engine, session_scope
from labuse.scoring.p_v2.pipeline import run_score_v2

TARGET = "q_v8_calibre"


def _ensure_backups(conn):
    for src, bak in [("parcel_residuel", "parcel_residuel_pre_v8"),
                     ("p_model_static", "p_model_static_pre_v8")]:
        exists = conn.execute(text("SELECT to_regclass(:b)"), {"b": bak}).scalar()
        if not exists:
            conn.execute(text(f"CREATE TABLE {bak} AS SELECT * FROM {src}"))
            print(f"  backup créé : {bak}")


def main():
    eng = engine()
    with eng.begin() as c:
        if c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:t"), {"t": TARGET}).scalar():
            raise SystemExit(f"{TARGET} existe déjà — rollback d'abord (aucun écrasement silencieux).")
        _ensure_backups(c)
        # 1) migration parcel_residuel ← rerun (SDP calibrée), sémantique prod (constructibles seulement)
        c.execute(text("TRUNCATE parcel_residuel"))
        c.execute(text(
            "INSERT INTO parcel_residuel (parcel_id, taux_emprise_pct, pct_potentiel, sous_densite,"
            " sdp_residuelle_m2, capacite_estimee, computed_at) "
            "SELECT parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2,"
            " false, now() FROM parcel_residuel_rerun WHERE dispo_rerun"))
        n_res = c.execute(text("SELECT count(*) FROM parcel_residuel")).scalar()
        print(f"  parcel_residuel migré : {n_res} lignes (SDP calibrée)")
    # 2) rebuild p_model_static depuis le nouveau parcel_residuel
    from labuse.scoring.p_model import sql as p_sql
    with session_scope() as s:
        p_sql.build_static(s); s.commit()
    print("  p_model_static reconstruit (features résiduel calibrées)")
    # 3) run du champion (sha gelé) → nouveau run servi
    t0 = time.time()
    with session_scope() as s:
        res = run_score_v2(s, run_id=TARGET, rebuild=True, snapshot=True)
    print(f"  run {TARGET} : {res['n']} parcelles, {res.get('duree_s','?')}s")
    with engine().connect() as c:
        dist = c.execute(text("SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:t GROUP BY tier ORDER BY count(*)"), {"t": TARGET}).all()
    print(f"\nBASCULE MATÉRIALISÉE en {(time.time()-t0)/60:.1f} min. Tiers du nouveau run servi :")
    for tier, n in dist:
        print(f"  {tier:28s} {n:>8}")
    print(f"\n  SURFACES : export LABUSE_SERVED_RUN={TARGET} ; VITE_RUN_LABEL={TARGET} npm run build ; labuse build-mvt --label {TARGET}")
    print(f"  GOLDEN   : LABUSE_GOLDEN_RUN_LABEL={TARGET} python qa/golden_check.py")
    print(f"  ROLLBACK : python scripts/rollback_v8_calibre.py")


if __name__ == "__main__":
    main()
