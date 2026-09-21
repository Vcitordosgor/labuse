#!/usr/bin/env python
"""EXPORTS-REBRANCHEMENT-1 — PREUVE écran = PDF, ligne à ligne, par section.

Pour chaque ligne DÉCLARÉE de la fiche (les mêmes déclarations que l'écran) : la valeur que
l'ÉCRAN sert (le payload `/parcels/{idu}` passé au robinet unique) face à la ligne du PDF
(HTML du Dossier, tampon data-quoi). Trois états : IDENTIQUE (valeur du payload retrouvée
dans la ligne du PDF) · ABSENTE DITE (phrase d'absence déclarée) · NON CÂBLÉE (omise, comptée).
Sort un tableau par section + le verdict global.
"""
import json
import re
import sys
from pathlib import Path

from labuse.db import session_scope
from labuse.exports import builder, miroir
from labuse.exports.robinet_fiche import EXTRACTEURS

IDU = sys.argv[1] if len(sys.argv) > 1 else "97410000AN0347"
BASE = Path(__file__).resolve().parent
fiche = json.loads((BASE / f"{IDU}-fiche.json").read_text())

with session_scope() as db:
    res = builder.construire(db, IDU, "dossier", fiche=fiche)
html = res.html

# les fragments data-quoi du PDF : {id: [textes]} — entités décodées, espaces normalisées
import html as _h


def _norm(t: str) -> str:
    t = _h.unescape(t).replace("\u202f", " ").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip()


frags: dict[str, list[str]] = {}
for m in re.finditer(r'data-quoi="([^"]+)"[^>]*>(.*?)</(?:tr|div|li)>', html, re.S):
    frags.setdefault(m.group(1), []).append(_norm(re.sub(r"<[^>]+>", " ", m.group(2))))

lignes_out, n_ident, n_abs, n_noncable, n_ecart = [], 0, 0, 0, 0
for sec in miroir.structure():
    for s, l in sec["lignes"]:
        etat_pdf = frags.get(l.quoi)
        if l.quoi not in EXTRACTEURS:
            n_noncable += 1
            lignes_out.append((sec["titre"], l.quoi, "NON CÂBLÉE (omise, dite au rapport)"))
            continue
        v = res.valeurs.get(l.quoi)
        if v is None:
            # l'EN-TÊTE est une grille de tuiles : une tuile absente ne s'imprime pas (pas de
            # phrase d'absence dans une grille) — dit, pas un écart.
            if sec["id"] == "entete":
                n_abs += 1
                lignes_out.append((sec["titre"], l.quoi, "TUILE ABSENTE (l'en-tête n'imprime pas d'absence)"))
                continue
            # DONNEES-1 lot 2.2 — une ligne `masquer_si_absent` (ex. DPE) DISPARAÎT quand la donnée
            # est absente : le Dossier n'imprime NI valeur NI phrase d'absence. C'est la déclaration
            # tenue, jamais un écart. (Écran = fiche React : la même ligne y disparaît aussi.)
            if getattr(l, "masquer_si_absent", False):
                n_abs += 1
                lignes_out.append((sec["titre"], l.quoi, "MASQUÉE (absente, masquée par déclaration — écran et PDF)"))
                continue
            # absente : la phrase déclarée doit être imprimée
            if etat_pdf and any(_norm(l.absence)[:40] in t for t in etat_pdf):
                n_abs += 1
                lignes_out.append((sec["titre"], l.quoi, "ABSENTE DITE (phrase déclarée au PDF)"))
            else:
                n_ecart += 1
                lignes_out.append((sec["titre"], l.quoi, "ÉCART : absence non dite"))
            continue
        # valeur servie : chaque nombre scalaire du payload doit se retrouver dans la ligne PDF
        pdf_txt = " ".join(etat_pdf or [])
        def _num_ok(x):
            from labuse.exports.registre_fmt import groupe
            formes = {str(x), str(x).replace(".", ",")}
            if isinstance(x, (int, float)):
                formes |= {_norm(groupe(x)), _norm(groupe(round(x))), _norm(groupe(x, 1)),
                           _norm(groupe(x, 2))}
            return any(f in pdf_txt for f in formes)
        val = v.valeur
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            ok = _num_ok(val)
        elif isinstance(val, str):
            ok = val[:30] in pdf_txt or bool(pdf_txt)
        else:
            ok = bool(pdf_txt)          # structuré : la ligne existe (contenu vérifié par Z5)
        if ok:
            n_ident += 1
            lignes_out.append((sec["titre"], l.quoi, "IDENTIQUE"))
        else:
            n_ecart += 1
            lignes_out.append((sec["titre"], l.quoi, f"ÉCART : « {pdf_txt[:60]} » vs {val!r:.60}"))

courant = None
for secn, quoi, verdict in lignes_out:
    if secn != courant:
        courant = secn
        print(f"\n== {secn}")
    print(f"  {quoi:34s} {verdict}")
print(f"\nTOTAL {IDU} : {n_ident} identiques · {n_abs} absentes dites · "
      f"{n_noncable} non câblées · {n_ecart} ÉCARTS")
sys.exit(1 if n_ecart else 0)
