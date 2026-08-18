"""M115 — AUDIT PUR des chemins du Copilote (aucune correction). Rejoue des cas nominaux et dégradés
via answer() et dump la réponse EXACTE + le chrono. Preuve reproductible pour AUDIT_M115_CHEMINS.md."""
from __future__ import annotations
import json, time
from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

CLES = ("text", "intent", "scenario", "compris", "porte", "carte_filtre", "surveillance",
        "document", "projet_form", "web", "sources", "clarification", "refus", "criteres_non_appliques",
        "criteres_appliques", "degraded", "en_construction", "needs_confirmation", "clarification_recap",
        "brief_effectif", "recap")

def montre(titre, msg, scenario=None, **kw):
    with session_scope() as db:
        t0 = time.perf_counter()
        r = answer(db, msg, scenario=scenario, **kw)
        ms = round((time.perf_counter()-t0)*1000)
    print(f"\n### {titre}")
    print(f"  DEMANDE  : {msg!r}  scenario={scenario}")
    print(f"  CHRONO   : {ms} ms")
    txt = r.get("text") or ""
    print(f"  text[{len(txt)}]: {txt[:240]!r}")
    porte = {k: r.get(k) for k in ("porte","carte_filtre","surveillance","document","projet_form") if r.get(k)}
    print(f"  intent={r.get('intent')} scenario_servi={r.get('scenario')} clar={r.get('clarification')} refus={r.get('refus')}")
    print(f"  compris  : {r.get('compris')!r}")
    if r.get('criteres_non_appliques'): print(f"  CNA(M109): {r.get('criteres_non_appliques')}")
    if porte: print(f"  PORTE    : {json.dumps(porte, ensure_ascii=False)[:260]}")
    if r.get('sources'): print(f"  sources  : {r.get('sources')}")
    return r

print("========== PHASE 1 — NOMINAL, LES SIX CHIPS ==========")
montre("1a donnees", "Combien de parcelles en procédure judiciaire à Saint-Denis ?", "donnees")
montre("1b parcelle", "des terrains à fort potentiel à Saint-Leu pour 15 logements", "parcelle")
montre("1c projet", "résidence 12 lots à Bras-Panon", "projet")
montre("1d web", "Qui est le maire de La Possession ?", "web")
montre("1e surveillance", "préviens-moi des nouveaux permis à Saint-Paul", "surveillance")
montre("1f outil", "le baromètre du foncier", "outil")
