"""M78-ter — les 4 tests de l'outil recherche_web (ajout au test de véracité) :
1. « Qui est le maire de Saint-Denis ? » → réponse WEB, marquage source + date, JAMAIS Sourcé/Estimé.
2. « Un nouveau PLU pour Saint-Leu ? » → outil INTERNE (Vérif procédure PLU), le web n'est PAS appelé.
3. « Recette du rougail saucisse ? » → BARRIÈRE, le web n'est PAS appelé.
4. Coût : le routage + la recherche web sont journalisés (ia_log kind copilote-web).

Usage : .venv/bin/python qa/m78/veracite_web.py — modèle réel + recherche web réelle.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse.copilote_v2.answering import answer
from labuse.db import session_scope

CAS = [
    {"q": "Qui est le maire de Saint-Denis de La Réunion ?", "attendu": "web"},
    {"q": "Un nouveau PLU est-il disponible pour Saint-Leu ?", "attendu": "interne"},
    {"q": "Quelle est la recette du rougail saucisse ?", "attendu": "barriere"},
]


def main() -> int:
    with session_scope() as db:
        echecs, details = [], []
        for cas in CAS:
            r = answer(db, cas["q"])
            t = r.get("text") or ""
            a = cas["attendu"]
            if a == "web":
                ok = (r.get("web") is True and "Source : web" in t and "consulté le" in t
                      and "Sourcé" not in t and "Estimé" not in t)   # marquage web, jamais Sourcé/Estimé
            elif a == "interne":
                ok = not r.get("web") and r.get("porte") is not None   # outil interne (porte), web NON appelé
            else:   # barriere
                ok = not r.get("web") and r.get("intent") == "HORS_SUJET"
            details.append((a, cas["q"][:42], "web=%s" % r.get("web"), "porte=%s" % r.get("porte"),
                            "intent=%s" % r.get("intent"), "OK" if ok else "ÉCHEC"))
            if not ok:
                echecs.append(cas["q"])
        n_web = db.execute(text("SELECT count(*) FROM ia_log WHERE kind='copilote-web' "
                                "AND ts > now() - interval '10 minutes'")).scalar() or 0
        for d in details:
            print(" ", *d)
        print(f"\nCoût web journalisé (ia_log copilote-web, 10 min) : {n_web} appel(s)")
        print(f"BILAN : {len(CAS) - len(echecs)}/{len(CAS)} + coût journalisé={'oui' if n_web > 0 else 'NON'}")
        return 0 if (not echecs and n_web > 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
