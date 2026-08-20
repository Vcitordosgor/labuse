"""M133 · vérification — les exemples de l'accueil v3, joués TELS QUELS en TEXTE LIBRE (aucun
scénario forcé : l'accueil v3 n'en envoie plus), aboutissent chacun à leur mission. Et le
PLACEHOLDER, joué tel quel, aboutit à la mission 1 (donnée), jamais à un refus.

Source de vérité : `accueil_publie()` (le serveur) — on teste EXACTEMENT ce qui est affiché.
Usage : .venv/bin/python qa/m133/exemples.py   (nécessite ANTHROPIC_API_KEY + base réelle)
"""
from __future__ import annotations

import re
import sys

from labuse.copilote_v2.answering import accueil_publie, answer
from labuse.db import session_scope


def _compte_servi(txt: str) -> str | None:
    """Un compte servi (mission 1) = un nombre suivi de « parcelle(s) » ou tout entier NON-année.
    Accepte les petits comptes (ex. « 126 parcelles ») — l'anti-année 1000+ de la gate M118 était
    une gate NÉGATIVE, ici on veut prouver qu'un compte EST servi."""
    m = re.search(r"(\d[\d  ]*)\s*parcelle", txt or "")
    if m:
        return m.group(1).strip()
    for m in re.findall(r"\d[\d  ]{2,}\d|\d{2,6}", txt or ""):
        n = int(re.sub(r"\D", "", m))
        if not (1900 <= n <= 2099):
            return m.strip()
    return None


def _juge(cle: str, r: dict) -> tuple[bool, str]:
    txt = r.get("text") or ""
    refus = r.get("refus")
    if refus:
        return False, f"REFUS={refus} (voie={(r.get('voie') or {}).get('cible')})"
    if cle == "donnees":   # mission 1 — donnée app : QUESTION, non refus, un compte servi
        return (r.get("intent") == "QUESTION" and _compte_servi(txt) is not None,
                f"intent={r.get('intent')} chiffre={_compte_servi(txt)}")
    if cle == "web":       # web : marqué web, non refus
        return (r.get("intent") == "QUESTION" and r.get("web") is True,
                f"intent={r.get('intent')} web={r.get('web')}")
    if cle == "expliquer":
        return (r.get("intent") == "EXPLIQUER" and len(txt) > 40,
                f"intent={r.get('intent')} len={len(txt)}")
    if cle == "preparer":
        return (r.get("intent") == "PREPARER" and len(txt) > 40,
                f"intent={r.get('intent')} len={len(txt)}")
    return False, "clé inconnue"


def main() -> int:
    meta = accueil_publie()
    ok = total = 0
    with session_scope() as db:
        print("========== 4 EXEMPLES (texte libre, aucun scénario) ==========")
        for cap in meta["capacites"]:
            r = answer(db, cap["exemple"])          # AUCUN scenario — texte libre
            if r.get("degraded"):
                print("INDÉTERMINÉ — service indisponible (quota).", file=sys.stderr); return 2
            v, d = _juge(cap["cle"], r)
            total += 1; ok += v
            print(f"{'OK  ' if v else 'FAIL'} [{cap['cle']:>9}] « {cap['exemple']} » → {d}")

        print("\n========== PLACEHOLDER (texte libre) → mission 1, jamais un refus ==========")
        ph = meta["placeholder"]
        r = answer(db, ph)
        if r.get("degraded"):
            print("INDÉTERMINÉ — service indisponible (quota).", file=sys.stderr); return 2
        v = not r.get("refus") and r.get("intent") == "QUESTION" and _compte_servi(r.get("text") or "") is not None
        total += 1; ok += bool(v)
        print(f"{'OK  ' if v else 'FAIL'} « {ph} » → intent={r.get('intent')} refus={r.get('refus')} "
              f"chiffre={_compte_servi(r.get('text') or '')}")

    print(f"\n=== BILAN M133 : {ok}/{total} ===")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
