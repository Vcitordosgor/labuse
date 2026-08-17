"""M113 - Phase 5 - LA GATE PAR SCENARIO CHIP. Chaque chip force son scenario ; la reponse doit etre
CONFORME au gabarit du scenario (Phase 4). Au meme rang que les gates du texte libre : le chemin
guide ne se livre pas sans sa gate. L'anti-invention reste verifie a l'identique (le comptage servi
doit etre le vrai - oracle SQL, comme la veracite).

Usage : .venv/bin/python qa/m113/scenarios.py   (necessite ANTHROPIC_API_KEY + base reelle)
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.copilote_v2.answering import answer
from labuse.db import session_scope


def _oracle_compte_saint_paul(db) -> int:
    row = db.execute(text("SELECT count(*) FROM parcels WHERE commune = :c"), {"c": "Saint-Paul"}).scalar()
    return int(row or 0)


def _juge(scen: str, r: dict, vrai_sp: int) -> tuple[int, str]:
    txt = (r.get("text") or "")
    if scen == "donnees":
        # anti-invention : le VRAI compte existe dans le resultat servi + le recap M109 est present.
        digits = "".join(c for c in txt if c.isdigit())      # neutralise tout separateur de milliers
        compte_ok = str(vrai_sp) in digits
        recap_ok = bool(r.get("compris"))
        return (1 if compte_ok and recap_ok else 0, f"compte={compte_ok} recap={recap_ok} (vrai={vrai_sp})")
    if scen == "web":
        court = r.get("web") is True and txt.count(".") <= 4 and len(txt) < 400
        source = "Source : web" in txt
        return (1 if court and source else 0, f"web={r.get('web')} court={court} source={source} len={len(txt)}")
    if scen == "parcelle":
        peage = bool(r.get("needs_confirmation") or r.get("clarification_recap") or r.get("recap")) \
            and r.get("intent") == "RECHERCHE"
        return (1 if peage else 0, f"intent={r.get('intent')} peage={peage}")
    if scen == "surveillance":
        veille = r.get("intent") == "VEILLE"
        porte = bool(r.get("surveillance")) or bool(r.get("clarification"))
        return (1 if veille and porte else 0, f"intent={r.get('intent')} surveillance={r.get('surveillance')}")
    if scen == "outil":
        return (1 if r.get("porte") else 0, f"porte={r.get('porte')}")
    if scen == "projet":
        pf = r.get("projet_form")
        prefill = (pf or {}).get("prefill") or {}
        bien = bool(pf) and prefill.get("commune") == "Bras-Panon" and prefill.get("programme_logements") == 12
        return (1 if bien else 0, f"projet_form={bool(pf)} prefill={prefill}")
    return (0, "scenario inconnu")


def main() -> int:
    ok = 0
    cas: list[tuple[str, str, str]] = [
        ("donnees", "Combien de parcelles a Saint-Paul ?", "compte + recap M109"),
        ("web", "Qui est le maire de Saint-Denis ?", "web court + source"),
        ("parcelle", "15 logements a Saint-Paul, >= 2000 m2", "recap-peage RECHERCHE"),
        ("surveillance", "les nouveaux permis a Saint-Paul", "VEILLE + porte Surveillance"),
        ("outil", "le barometre du foncier", "porte OUTIL"),
        ("projet", "residence 12 lots a Bras-Panon", "parcours guide prerempli"),
    ]
    with session_scope() as db:
        vrai_sp = _oracle_compte_saint_paul(db)
        for scen, msg, attendu in cas:
            r = answer(db, msg, scenario=scen)
            if r.get("degraded"):
                print(f"INDETERMINE [{scen}] service indisponible (quota) - gate non evaluable.", file=sys.stderr)
                return 2
            verdict, detail = _juge(scen, r, vrai_sp)
            ok += verdict
            mark = "OK  " if verdict else "FAIL"
            print(f"{mark} [{scen:>12}] {attendu:<30} | {detail}")
    print(f"\n=== BILAN SCENARIOS M113 : {ok}/{len(cas)} ===")
    return 0 if ok == len(cas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
