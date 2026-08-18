"""M115 — dumps COMPLETS (toutes clés non nulles) pour les chemins à défaut + Phase 2/3."""
from __future__ import annotations
import json, time
from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

def full(titre, msg, scenario=None, **kw):
    with session_scope() as db:
        t0=time.perf_counter(); r=answer(db, msg, scenario=scenario, **kw); ms=round((time.perf_counter()-t0)*1000)
    print(f"\n### {titre}  ({ms} ms)")
    print(f"  DEMANDE: {msg!r} scenario={scenario} kw={kw}")
    nn = {k:v for k,v in r.items() if v not in (None,'',[],{}) and k!='_route'}
    for k,v in nn.items():
        s=json.dumps(v, ensure_ascii=False) if not isinstance(v,str) else v
        print(f"  {k} = {s[:300]}")
    return r

print("========== 1b PARCELLE — dump complet ==========")
full("parcelle nominal", "des terrains à fort potentiel à Saint-Leu pour 15 logements", "parcelle")
print("\n========== 1d WEB — texte complet ==========")
r=full("web nominal", "Qui est le maire de La Possession ?", "web")

print("\n\n========== PHASE 2 — CHEMINS DÉGRADÉS ==========")
print("\n-- 2.1 LE VIDE (résultat zéro légitime) --")
full("vide donnees (friches Cilaos)", "Combien de friches à Cilaos ?", "donnees")
full("vide donnees (événement rouge Cilaos)", "Combien de parcelles à événement rouge à Cilaos ?", "donnees")

print("\n-- 2.3 L'AMBIGU (paramètre manquant) par chip --")
full("ambigu donnees", "combien de parcelles", "donnees")
full("ambigu parcelle", "je cherche des terrains", "parcelle")
full("ambigu surveillance (sans commune)", "préviens-moi des nouveaux permis", "surveillance")
full("ambigu outil (vague)", "ouvre un outil", "outil")
full("ambigu web (vide)", "cherche sur le web", "web")

print("\n-- 2.4 HORS PÉRIMÈTRE --")
full("hors-sujet donnees", "quelle est la météo demain à Saint-Denis", "donnees")
full("hors-sujet libre", "raconte-moi une blague")

print("\n-- 2.5 CRITÈRE NON APPLICABLE (M109) --")
full("CNA donnees", "combien de parcelles avec une charge foncière supérieure à 200 €/m² à Saint-Paul", "donnees")
