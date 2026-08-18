"""M115 — Phase 3 conversation : rupture sur chips, préremplissage projet vide."""
from __future__ import annotations
import json, time
from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

def full(titre, msg, **kw):
    with session_scope() as db:
        r=answer(db, msg, **kw)
    print(f"\n### {titre}")
    print(f"  DEMANDE: {msg!r} kw={ {k:v for k,v in kw.items() if k!='history'} }")
    nn={k:v for k,v in r.items() if v not in (None,'',[],{}) and k!='_route'}
    for k,v in nn.items():
        s=json.dumps(v,ensure_ascii=False) if not isinstance(v,str) else v
        print(f"  {k} = {s[:240]}")
    return r

T1="des terrains ≥ 20000 m² à Saint-Paul pour 30 logements"
HIST=[{"role":"user","content":T1},{"role":"assistant","content":"Instruction en cours…"}]
PRIOR={"commune":"Saint-Paul","surface_min":20000,"programme_logements":30}

print("========== PHASE 3.1 — RUPTURE DE SUJET par chip ==========")
print("(T1 = '%s' ; T2 doit NE PAS hériter surface_min=20000)" % T1)
full("rupture DONNEES (T2 friches Cilaos)", "combien de friches à Cilaos", scenario="donnees", history=HIST, prior_params=PRIOR)
full("rupture PARCELLE (T2 terrains Cilaos 8 log)", "des terrains à Cilaos pour 8 logements", scenario="parcelle", history=HIST, prior_params=PRIOR)
full("rupture WEB (T2 maire) — classify court-circuité ?", "qui est le maire de Cilaos", scenario="web", history=HIST, prior_params=PRIOR)

print("\n========== PHASE 3.4 — PRÉREMPLISSAGE PROJET depuis texte libre VIDE ==========")
full("projet texte non exploitable", "créer", scenario="projet")
full("projet texte vide-ish", "un projet svp", scenario="projet")
full("projet libre sans chip (intent PROJET)", "je veux monter une opération immobilière")
