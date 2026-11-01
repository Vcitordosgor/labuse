"""Prépare le manifeste q_v21 (déploiement) et le SERT EN LOCAL, puis joue les CONTRÔLES de bascule
(cohérence des flux + étage 0 aligné + compte des parcelles). Ne touche que scoring_run + cascade_run ;
mvt/division/résiduel restent ceux de q_v20 (hors mandat). Local seulement — jamais la prod."""
import json, shutil
from pathlib import Path
from sqlalchemy import text
from labuse.db import session_scope
from labuse import manifeste, runs, bascule_gardes, coherence_flux, bascule_flux

MF = Path("config/served_manifest.json")
shutil.copy(MF, "docs/audit-2026-11/scoring-copro-1/served_manifest.q_v20.bak.json")
avant = json.loads(MF.read_text())
print("AVANT:", json.dumps(avant, ensure_ascii=False))

with session_scope() as db:
    casc, motif = bascule_flux.resoudre_cascade_run(db, "q_v21")
    print("resoudre_cascade_run(q_v21) ->", casc, "|", motif)
    complet, m = bascule_flux._run_complet(db, "q_v21")
    print("_run_complet(q_v21) ->", complet, "|", m)
    assert complet, m
    # compte des parcelles : q_v21 == q_v20 (même dataset, rebuild=False)
    n20, n21 = (db.execute(text("SELECT n_parcelles FROM p_score_v2_runs WHERE run_id=:r"),{"r":r}).scalar() for r in ("q_v20","q_v21"))
    print(f"compte parcelles : q_v20={n20}  q_v21={n21}  (écart {int(n21)-int(n20)})")

# manifeste candidat : SEULS scoring_run + cascade_run bougent (mvt/division/résiduel inchangés).
nouveau = {
    "scoring_run": "q_v21", "cascade_run": casc,
    "mvt_run": avant["mvt_run"], "division_run": avant["division_run"],
    "residuel_run_seq": avant["residuel_run_seq"],
    "promoted_at": avant.get("promoted_at"),  # réécrit ci-dessous à l'heure réelle serait non reproductible → on garde
    "par": "SCORING-COPRO-1 — q_v21 servi EN LOCAL (copro hors palier + PPR i + étage 0 aligné). PAS prod.",
    "precedent": {k: avant.get(k) for k in ("scoring_run","mvt_run","division_run","residuel_run_seq","cascade_run")},
}
manifeste.ecrire(nouveau); runs.invalidate()
print("APRÈS:", json.dumps(json.loads(MF.read_text()), ensure_ascii=False))
print("runs.current()=",runs.current()," runs.cascade()=",runs.cascade())

with session_scope() as db:
    print("\n=== CONTRÔLES ===")
    e0 = bascule_gardes.check_etage0_aligne(session=db)
    print("étage0:", e0.get("statut"), e0)
    coh = coherence_flux.verifier(db, run="q_v21")
    print("coherence_flux ok:", coh.get("ok"))
    for c in coh.get("checks", []):
        print(f"  [{'ok' if c.get('ok') else 'KO'}] {c.get('libelle')}" + (f" — {c.get('detail')}" if c.get('detail') else ""))
