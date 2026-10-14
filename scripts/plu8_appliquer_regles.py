#!/usr/bin/env python3
"""PLU-CALIBRAGE-8 (oct.) Lot B — insère les blocs `regles` transcrits (propose/relecteur, citations
RELUES au règlement md5-vérifié) dans les YAML, SANS reparser/réécrire le reste du fichier.

Chaque bloc est dumpé par yaml.safe_dump (quoting correct) puis indenté de 4 espaces et inséré juste
après la ligne-clé de la zone (`  <ZONE>:`). N'ajoute que des feuilles `valide` sourcées (article +
page_pdf + citation verbatim). Idempotent : refuse si la zone a déjà un bloc `regles`.
"""
from __future__ import annotations

import sys
import yaml

DEST = "config/plu_destinations"


def feuille(statut="valide", **kw):
    d = dict(kw)
    d["statut"] = statut
    return d


# ── Saint-Denis (97411) — zones AU à chapitre propre (md5 43426a8faf55efcdaa2a235e95a45d2f) ──────
SD = {
    "AUm": {
        "hauteur": {
            "faitage": feuille(m=10.0, article="AUm.10", page_pdf=98,
                citation="La hauteur des constructions n’excèdera pas : - 10 m pour la hauteur maximale H"),
            "egout": feuille(m=7.0, article="AUm.10", page_pdf=98,
                citation="La hauteur des constructions n’excèdera pas : (...) - 7 m pour la hauteur d’égout he"),
        },
        "emprise_sol": {"ces": feuille(pct=50.0, article="AUm.9", page_pdf=98,
            citation="L'emprise au sol des constructions est limitée à 50 % de la superficie de l'unité foncière.")},
        "retraits": {
            "voie": feuille(min_m=4.0, article="AUm.6", page_pdf=97,
                citation="Les constructions seront implantées avec un recul de 4 m minimum par rapport à l’alignement.",
                note="Exceptions (non modélisées) : 3 m mini en bordure de voies d'emprise < 3,50 m ; annexes de stationnement à l'alignement."),
            "limites_separatives": feuille(forme="alignement", article="AUm.7", page_pdf=98,
                citation="Chaque construction pourra s'implanter sur 1 ou 2 limites séparatives sur une longueur maximale de 10 m par limite.",
                note="Implantation EN LIMITE admise (recul 0) ; sinon retrait L ≥ h/2 avec minimum 4 m (non modélisé)."),
        },
    },
    "AUj": {
        "hauteur": {
            "faitage": feuille(m=13.0, article="AUj.10", page_pdf=93,
                citation="La hauteur des constructions n’excèdera pas : - 13 m pour la hauteur maximale H"),
            "egout": feuille(m=10.0, article="AUj.10", page_pdf=93,
                citation="La hauteur des constructions n’excèdera pas : (...) - 10 m pour la hauteur d’égout he"),
        },
        "emprise_sol": {"ces": feuille(pct=60.0, article="AUj.9", page_pdf=93,
            citation="L’emprise au sol des constructions est limitée à 60% de la superficie de l’unité foncière.")},
        "retraits": {
            "voie": feuille(min_m=4.0, article="AUj.6", page_pdf=92,
                citation="Les constructions principales seront implantées avec un recul de 4 m minimum par rapport à l’alignement.",
                note="Règle générale ; exceptions (non modélisées) : prospect L ≥ H à l'axe, 3 m en voies étroites, annexes à l'alignement."),
            "limites_separatives": feuille(forme="alignement", article="AUj.7", page_pdf=92,
                citation="Chaque construction pourra s'implanter sur 1 ou 2 limites séparatives sur une longueur maximale de 18 mètres par limite.",
                note="Implantation EN LIMITE admise (recul 0) ; sinon retrait L ≥ h/2 avec minimum 4 m (non modélisé)."),
        },
    },
    "AUh": {
        "hauteur": {
            "faitage": feuille(m=7.0, article="AUh.10", page_pdf=103,
                citation="La hauteur des constructions n’excèdera pas : - 7 m pour la hauteur maximale H"),
            "egout": feuille(m=4.5, article="AUh.10", page_pdf=103,
                citation="La hauteur des constructions n’excèdera pas : (...) - 4,5 m pour la hauteur d’égout he"),
        },
        "emprise_sol": {"ces": feuille(pct=30.0, article="AUh.9", page_pdf=103,
            citation="L’emprise au sol des constructions est limitée à 30% de la superficie de l’unité foncière.")},
        "retraits": {
            "voie": feuille(min_m=4.0, article="AUh.6", page_pdf=102,
                citation="Les constructions seront implantées avec un recul de 4 m minimum par rapport à l’alignement.",
                note="Exceptions (non modélisées) : 3 m mini en voies étroites ; annexes de stationnement à l'alignement."),
            "limites_separatives": feuille(forme="alignement", article="AUh.7", page_pdf=103,
                citation="Chaque construction pourra s'implanter sur 1 limite séparative sur une longueur maximale de 10 mètres et sur une hauteur maximale H de 4,5m.",
                note="Implantation EN LIMITE admise (recul 0) ; sinon retrait L ≥ h/2 avec minimum 4 m (non modélisé)."),
        },
    },
}

# ── Saint-Leu (97413) — chapitre ZONE AU unique, valeurs PAR SECTEUR (md5 d74416f9b25fbe571505f084ab486b0a) ──
_SL_VOIE = {
    "AUa": (2.0, "Dans le secteur AUa, les constructions peuvent s’implanter soit à l’alignement, soit avec un recul minimum de 2,00m par rapport à l’alignement.", "Alignement OU recul min 2 m ; plancher 2 m retenu."),
    "AUb": (2.0, "Dans le secteur AUb, les constructions doivent s’implanter avec un recul minimum de 2,00m par rapport à l’alignement.", "Recul minimum 2 m."),
    "AUc": (4.0, "Dans le secteur AUc et AUd, les constructions doivent s’implanter avec un recul minimum de 4,00m par rapport à l’alignement.", "Recul minimum 4 m."),
    "AUd": (4.0, "Dans le secteur AUc et AUd, les constructions doivent s’implanter avec un recul minimum de 4,00m par rapport à l’alignement.", "Recul minimum 4 m."),
    "AUe": (5.0, "Dans le secteur AUe, les constructions doivent s’implanter en retrait par rapport à l’alignement en respectant un prospect L=1/2H(*) avec un minimum de 5,00m.", "Prospect L=1/2H, plancher 5 m (10 m si ICPE) ; recul 55 m le long de la route des Tamarins — non modélisés."),
}
_SL_LIM = {
    "AUa": "Dans les secteurs AUa, AUa-rc, AUb et Aub-rc : Les constructions peuvent joindre une ou deux limites séparatives qui touchent la voie",
    "AUb": "Dans les secteurs AUa, AUa-rc, AUb et Aub-rc : Les constructions peuvent joindre une ou deux limites séparatives qui touchent la voie",
    "AUc": "Dans les secteurs AUc et AUd : Les constructions peuvent être implantées sur une limite séparative (ou les deux limites, si celles-ci sont distantes de moins de 18 mètres l’une de l’autre)",
    "AUd": "Dans les secteurs AUc et AUd : Les constructions peuvent être implantées sur une limite séparative (ou les deux limites, si celles-ci sont distantes de moins de 18 mètres l’une de l’autre)",
    "AUe": "Dans le secteur AUe, la mitoyenneté sur une limite séparative peut être admise sous réserve de la construction d’un mur coupe-feu.",
}
_SL_H = {"AUa": (12.0, 9.0, "12,00m au faîtage", "9,00m à l’égout du toit"),
         "AUb": (10.0, 7.0, "10,00m au faîtage", "7,00m à l’égout du toit"),
         "AUc": (9.0, 6.0, "9,00m au faîtage", "6,00m à l’égout du toit"),
         "AUd": (6.0, 4.0, "6,00m au faîtage", "4,00m à l’égout du toit"),
         "AUe": (None, 10.0, None, "10,00m à l'égout du toit")}
_SL_CES = {"AUa": 80.0, "AUb": 60.0, "AUc": 50.0, "AUd": 40.0, "AUe": 60.0}
_SL_CES_CIT = {
    "AUa": "Dans le secteur AUa et AUa-rc, l’emprise au sol maximale autorisée (...) ne doit pas excéder 80% de l’unité foncière.",
    "AUb": "Dans les secteurs AUb, Aub-rc et AUe, l’emprise au sol maximale autorisée (...) ne doit pas excéder 60% de l’unité foncière.",
    "AUc": "Dans le secteur AUc, l’emprise au sol des bâtiments ne doit pas excéder 50% de l’unité foncière.",
    "AUd": "Dans le secteur AUd, l’emprise au sol des bâtiments ne doit pas excéder 40% de l’unité foncière.",
    "AUe": "Dans les secteurs AUb, Aub-rc et AUe, l’emprise au sol maximale autorisée (...) ne doit pas excéder 60% de l’unité foncière.",
}
SL = {}
for z in ("AUa", "AUb", "AUc", "AUd", "AUe"):
    hf, he, hf_cit, he_cit = _SL_H[z]
    haut = {"egout": feuille(m=he, article="AU 10", page_pdf=91,
            citation=f"Dans le secteur {z}, la hauteur maximale des constructions est limitée à : - {he_cit}")}
    if hf is not None:
        haut["faitage"] = feuille(m=hf, article="AU 10", page_pdf=91,
            citation=f"Dans le secteur {z}, la hauteur maximale des constructions est limitée à : - {hf_cit}")
    vmin, vcit, vnote = _SL_VOIE[z]
    SL[z] = {
        "hauteur": haut,
        "emprise_sol": {"ces": feuille(pct=_SL_CES[z], article="AU 9", page_pdf=90, citation=_SL_CES_CIT[z])},
        "retraits": {
            "voie": feuille(min_m=vmin, article="AU 6", page_pdf=87, citation=vcit, note=vnote),
            "limites_separatives": feuille(forme="alignement", article="AU 7", page_pdf=88, citation=_SL_LIM[z],
                note="Implantation EN LIMITE admise (recul 0) ; sinon marge d'isolement minimale (non modélisée)."),
        },
    }
if _SL_H["AUe"][0] is None:
    SL["AUe"].setdefault("_note_faitage", True)  # placeholder removed below


def bloc_regles_yaml(regles: dict) -> str:
    clean = {k: v for k, v in regles.items() if not k.startswith("_")}
    txt = yaml.safe_dump({"regles": clean}, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return "".join("    " + line if line.strip() else line for line in txt.splitlines(keepends=True))


def inserer(fichier: str, zones: dict):
    path = f"{DEST}/{fichier}"
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    for zone, regles in zones.items():
        key = f"  {zone}:\n"
        idx = next((i for i, l in enumerate(lines) if l == key), None)
        if idx is None:
            print(f"  !! {fichier}:{zone} introuvable"); continue
        # garde idempotence : pas déjà de regles sous la zone (avant la prochaine clé 2-espaces)
        j = idx + 1
        has = False
        while j < len(lines) and not (lines[j][:3] == "  " and lines[j][2] != " "):
            if lines[j].strip() == "regles:":
                has = True; break
            j += 1
        if has:
            print(f"  == {fichier}:{zone} a déjà un bloc regles — ignoré"); continue
        block = bloc_regles_yaml(regles)
        lines.insert(idx + 1, block)
        print(f"  ++ {fichier}:{zone} regles inséré ({len(block.splitlines())} lignes)")
    open(path, "w", encoding="utf-8").write("".join(lines))


if __name__ == "__main__":
    print("Saint-Denis:"); inserer("97411_saint_denis.yaml", SD)
    print("Saint-Leu:"); inserer("97413_saint_leu.yaml", SL)
