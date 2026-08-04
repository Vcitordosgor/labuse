"""Régénération de la référence golden DANS LE MÊME GESTE qu'une bascule/exception (garde #6).

Outille la procédure apprise à la bascule pondération : le `--dump` nu de golden_check retombe
sur les 32 GOLDEN_IDUS internes et PERD les 84 ancres J3 (format plat). Ce script :
  1. lit la référence COURANTE (liste des IDs + ancres) ;
  2. dump l'état courant sur CES IDs (subprocess, pas de word-splitting shell) ;
  3. reconstruit les ancres au format PLAT (anchor/commune/motif/validation conservés,
     triplet cascade_status/matrice_statut/tier_v2 rafraîchi) ;
  4. écrit la référence, relance golden_check, imprime le bilan.
Pré-requis : API up (LABUSE_API_BASE, défaut 127.0.0.1:8010) + LABUSE_SERVED_RUN.
Le diff git de la référence EST la revue Vic.
"""
from __future__ import annotations
import json, os, subprocess, sys

REF = os.path.join(os.path.dirname(__file__), "..", "reports", "m6-audit", "golden",
                   "golden-parcelles.json")

old = json.load(open(REF, encoding="utf-8"))
idus = list(old["parcelles"].keys())
anchors = {i for i, e in old["parcelles"].items() if e.get("anchor")}
print(f"référence courante : {len(idus)} parcelles, {len(anchors)} ancres")

r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "golden_check.py"),
                    "--dump", "--idu", *idus], capture_output=True, text=True, env=os.environ)
if r.returncode != 0:
    sys.exit(f"dump en échec : {r.stderr[-400:]}")
new = json.loads(r.stdout)
assert len(new["parcelles"]) == len(idus), f"dump incomplet : {len(new['parcelles'])}/{len(idus)}"

moved = []
for i, olde in old["parcelles"].items():
    fresh = new["parcelles"][i]["db"]
    if olde.get("anchor"):
        e = dict(olde)
        triple = {"cascade_status": fresh.get("cascade_status"),
                  "matrice_statut": fresh.get("matrice_statut"),
                  "tier_v2": (fresh.get("score_v2") or {}).get("tier")}
        if any(olde.get(k) != v for k, v in triple.items()):
            moved.append((i, {k: (olde.get(k), v) for k, v in triple.items() if olde.get(k) != v}))
        e.update(triple)
        new["parcelles"][i] = e
new["meta"]["n_parcelles"] = len(new["parcelles"])
json.dump(new, open(REF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"référence régénérée (run {new['meta'].get('run_v2_servi')}) ; "
      f"ancres dont le triplet a bougé : {len(moved)}")
for i, d in moved:
    print("  ", i, d)

chk = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "golden_check.py")],
                     capture_output=True, text=True, env=os.environ)
print(chk.stdout.strip().splitlines()[-1] if chk.stdout.strip() else chk.stderr[-200:])
sys.exit(chk.returncode)
