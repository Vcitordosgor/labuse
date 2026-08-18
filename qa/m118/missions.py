"""M118 · Phase 4 — LA GATE DES 4 MISSIONS + 4 REFUS-VOIES + la gate NÉGATIVE.

Le Copilote resserré fait 4 choses (donnée app · web · expliquer · préparer). Tout le reste
QUITTE le chat et reçoit un refus + une voie cliquable. La gate négative garantit qu'HORS mission 1
(la facette), aucun CHIFFRE LABUSE n'est servi (un compte/stat de la base) — un web fait sourcé ou
une année ne comptent pas.

Usage : .venv/bin/python qa/m118/missions.py   (nécessite ANTHROPIC_API_KEY + base réelle)
"""
from __future__ import annotations

import re
import sys

from sqlalchemy import text

from labuse.copilote_v2.answering import answer
from labuse.db import session_scope


def _oracle_sp(db) -> int:
    return int(db.execute(text("SELECT count(*) FROM parcels WHERE commune='Saint-Paul'")).scalar() or 0)


def _chiffre_labuse(txt: str) -> str | None:
    """Un nombre à 4-6 chiffres qui n'est PAS une année (1900-2099) = un compte/stat LABUSE probable."""
    for m in re.findall(r"\d[\d  ]{3,}\d|\d{4,6}", txt or ""):
        n = int(re.sub(r"\D", "", m))
        if 1000 <= n <= 999999 and not (1900 <= n <= 2099):
            return m.strip()
    return None


def main() -> int:
    ok = 0
    total = 0
    with session_scope() as db:
        vrai = _oracle_sp(db)
        print("========== 4 MISSIONS ==========")
        missions = [
            ("donnees", "Combien de parcelles à Saint-Paul ?"),
            ("web", "Qui est le maire de Saint-Denis ?"),
            ("expliquer", "Qu'est-ce qu'une zone AU ?"),
            ("preparer", "Prépare un argumentaire pour aborder le propriétaire"),
        ]
        for scen, msg in missions:
            r = answer(db, msg, scenario=scen)
            if r.get("degraded"):
                print(f"INDÉTERMINÉ [{scen}] service indisponible (quota).", file=sys.stderr); return 2
            v, d = _juge_mission(scen, r, vrai)
            total += 1; ok += v
            print(f"{'OK  ' if v else 'FAIL'} [mission {scen:>9}] {d}")

        print("\n========== 4 REFUS-VOIES (texte libre) ==========")
        voies = [
            ("trouve-moi un terrain à fort potentiel à Saint-Paul pour 15 logements", "projets"),
            ("préviens-moi des nouveaux permis à Saint-Paul", "surveillance"),
            ("ouvre le baromètre du foncier", "outils"),
            ("rédige un courrier au propriétaire de cette parcelle", "courriers"),
        ]
        for msg, cible in voies:
            r = answer(db, msg)
            if r.get("degraded"):
                print(f"INDÉTERMINÉ service indisponible (quota).", file=sys.stderr); return 2
            got = (r.get("voie") or {}).get("cible")
            neg = _chiffre_labuse(r.get("text") or "")
            v = r.get("refus") == "hors_mission" and got == cible and not neg
            total += 1; ok += v
            print(f"{'OK  ' if v else 'FAIL'} [refus-voie → {cible:>12}] refus={r.get('refus')} voie={got} chiffre_labuse={neg}")
    print(f"\n=== BILAN MISSIONS M118 : {ok}/{total} ===")
    return 0 if ok == total else 1


def _juge_mission(scen: str, r: dict, vrai: int) -> tuple[int, str]:
    txt = r.get("text") or ""
    neg = _chiffre_labuse(txt)
    if scen == "donnees":
        return (1 if str(vrai) in txt.replace(" ", "").replace(" ", "") and r.get("intent") == "QUESTION"
                else 0, f"compte {vrai} · intent={r.get('intent')}")
    if scen == "web":
        court = r.get("web") is True and len(txt) < 320
        return (1 if court and r.get("sources") else 0, f"web={r.get('web')} court={court} len={len(txt)}")
    if scen == "expliquer":
        # notion : intent EXPLIQUER, texte présent, AUCUN chiffre LABUSE (gate négative)
        return (1 if r.get("intent") == "EXPLIQUER" and len(txt) > 40 and not neg
                else 0, f"intent={r.get('intent')} chiffre_labuse={neg} len={len(txt)}")
    if scen == "preparer":
        return (1 if r.get("intent") == "PREPARER" and len(txt) > 40 and not neg
                else 0, f"intent={r.get('intent')} chiffre_labuse={neg} len={len(txt)}")
    return (0, "scénario inconnu")


if __name__ == "__main__":
    raise SystemExit(main())
