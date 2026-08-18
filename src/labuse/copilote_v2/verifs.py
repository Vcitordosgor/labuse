"""M78 · 1d — COMPARATEUR réponse Copilote ↔ oracle (hand-SQL). Utilisé par qa/m78/veracite.py.

Échec si : un chiffre diffère de la base · le Copilote répond à une question sans outil · un refus
attendu ne se produit pas · une couverture partielle tait sa réserve.
"""
from __future__ import annotations

from .answering import _nombres
from .outils import _fold_py


def _fold(s: str) -> str:
    return _fold_py(str(s or "").lower())


def _num_match(oracle, text: str) -> bool:
    nums = _nombres(text)
    try:
        o = float(oracle)
    except (TypeError, ValueError):
        return False
    return any(abs(n - o) <= 1 or abs(round(n) - round(o)) <= 1 for n in nums)


def juger(item: dict, rep: dict, oracle) -> tuple[bool, str]:
    cat = item["cat"]
    text = rep.get("text", "")
    ft = _fold(text)

    if cat == "exacte":
        if isinstance(oracle, str) and not oracle.replace(".", "").isdigit():
            return (_fold(oracle) in ft, f"attendu «{oracle}» absent de: {text[:90]}")
        return (_num_match(oracle, text), f"chiffre {oracle} absent de: {text[:90]}")

    if cat == "partielle":
        ok_num = oracle is None or _num_match(oracle, text)
        manques = [m for m in item.get("manque", []) if _fold(m) not in ft]
        if not ok_num:
            return (False, f"chiffre {oracle} absent de: {text[:90]}")
        if manques:
            return (False, f"réserve tue (manque {manques}) dans: {text[:110]}")
        return (True, "")

    if cat == "cna":
        # M116 · D11 (révise M109) — critère non applicable : l'AVEU D'ABORD, jamais le compte non
        # filtré présenté comme la réponse. Le critère lâché reste NOMMÉ + marqué absent. Deux formes
        # conformes : (a) AVEU SEUL (refus critere_non_applicable) quand aucun critère applicable n'a
        # filtré → le total (oracle) doit être ABSENT ; (b) AVEU + SOUS-COMPTE quand des critères
        # applicables ont filtré → le sous-compte (oracle) doit être servi, après l'aveu.
        manques = [m for m in item.get("manque", []) if _fold(m) not in ft]
        marqueur = any(w in ft for w in ("pas applique", "non applique", "pas interrogeable",
                                         "pas encore interrogeable", "n'est pas encore"))
        if manques:
            return (False, f"critère lâché non nommé (manque {manques}): {text[:110]}")
        if not marqueur:
            return (False, f"critère lâché servi SANS marqueur d'absence (miscompte muet): {text[:110]}")
        if rep.get("refus") == "critere_non_applicable":
            if oracle is not None and _num_match(oracle, text):
                return (False, f"total NON FILTRÉ {oracle} servi malgré l'aveu (D11): {text[:110]}")
            return (True, "")
        if oracle is not None and not _num_match(oracle, text):
            return (False, f"sous-compte {oracle} attendu absent: {text[:110]}")
        return (True, "")

    if cat == "refus_pp":
        ok = rep.get("refus") == "proprietaire_pp" or "publicite fonciere" in ft
        return (ok, f"refus PP attendu, obtenu: {text[:90]}")

    if cat == "refus_proj":
        ok = rep.get("refus") == "projection" or ("projection" in ft or "constate" in ft)
        return (ok, f"refus projection attendu, obtenu: {text[:90]}")

    if cat == "refus_hs":
        ok = rep.get("intent") == "HORS_SUJET" or "foncier" in ft
        return (ok, f"réponse hors-sujet attendue, obtenu: {text[:90]}")

    if cat == "outil_porte":
        return (rep.get("porte") == item["porte"], f"porte {item['porte']} attendue, obtenu {rep.get('porte')}")

    if cat == "refus_voie":
        # M118 — ce qui quitte le chat (ouvrir un outil, trancher une divisibilité…) : refus + voie
        # cliquable (navigation) vers la surface qui le fait. Aucun chiffre LABUSE (gate négative).
        got = (rep.get("voie") or {}).get("cible")
        ok = rep.get("refus") == "hors_mission" and got == item["voie"]
        return (ok, f"refus-voie {item['voie']} attendu, obtenu refus={rep.get('refus')} voie={got}")

    return (False, f"catégorie inconnue {cat}")
