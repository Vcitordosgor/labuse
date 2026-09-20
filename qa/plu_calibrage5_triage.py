"""PLU-CALIBRAGE-5 lot 1 — TRIAGE des 419 règles `propose` en trois familles.

Chaque `propose` porte une `raison` (posée par la conversion PLU-CALIBRAGE-3). On les regroupe par
TRAITEMENT (ce que feront les lots 2-4) :

  A — formules déduites : la valeur est une INTERPRÉTATION du texte, pas un nombre écrit (barème de
      stationnement « 1 place / 75 m² SDP », recul « H/2 min N », conditionnel). raison =
      « stationnement non chiffrable » | « valeur non numérique ».
  B — écarts / attributions : la valeur (ou son attribution de secteur) est à CONFIRMER contre la
      page citée. raison = « harmonisation ≠ texte » (valeur N absente de la citation) |
      « attribution douteuse » (citation sous secteur None). La plus grosse famille.
  C — citation non retrouvée : la règle existe mais le texte n'a pas été localisé. raison =
      « citation non retrouvée » | « INTROUVABLE ».

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage5_triage.py
Écrit captures/plu-calibrage5/TRIAGE-419.md (+ .json pour les lots suivants).
"""
from __future__ import annotations
import json, re
from pathlib import Path
from labuse.plu import destinations as D

_VAL_KEYS = ("m", "pct", "min_m", "places", "r_plus", "formule", "valeur", "texte")


# indices qu'une citation décrit une FORMULE / un barème / un renvoi (pas un chiffre unique écrit) :
# recul relatif à la hauteur (H/2…), implantation conditionnelle (sur limite OU recul), barème de
# stationnement (par tranche / par logement conditionné), renvoi à une autre zone.
_FORMULE_RX = re.compile(
    r"h\s*/\s*2|moiti[ée]|hauteur de la construction|[ée]gale?\s+à\s+la\s+hauteur|l\s*[≥>=]+\s*h"
    r"|sur\s+(?:l['’]une|les?\s+deux)?\s*limite|en\s+limite|soit\s+sur\s+(?:l['’]une|une|les)"
    r"|par\s+tranche|/\s*m²|par\s+logement\s*\(|se\s+reporter|r[èe]glement\s+de\s+la\s+zone",
    re.I)


def famille(r: dict) -> str:
    raison = (r.get("raison") or "").lower()
    if "non retrouv" in raison or "introuvable" in raison:
        return "C"
    if "non chiffrable" in raison:                    # barèmes de stationnement → A
        return "A"
    if "non numérique" in raison or "non numerique" in raison:
        # formule/barème/renvoi (pas de chiffre unique écrit) → A ; sinon un nombre est RÉCUPÉRABLE
        # de la citation trouvée → B (relecture de la page, comme les écarts).
        return "A" if _FORMULE_RX.search(str(r.get("citation") or "")) else "B"
    if "harmonisation" in raison or "attribution douteuse" in raison:
        return "B"
    return "?"


def valeur(f: dict):
    for k in _VAL_KEYS:
        if f.get(k) is not None:
            return f"{k}={f[k]}"
    return "—"


def main() -> int:
    rows = [r for r in D.iter_regles_calibrees() if r.get("statut") == "propose"]
    fam = {"A": [], "B": [], "C": [], "?": []}
    for r in rows:
        r["_famille"] = famille(r)
        fam[r["_famille"]].append(r)
    # table
    L = ["# PLU-CALIBRAGE-5 lot 1 — triage des 419 règles `propose`\n",
         f"**{len(rows)} propose** — A (formules déduites) **{len(fam['A'])}** · "
         f"B (écarts / attributions) **{len(fam['B'])}** · C (citation non retrouvée) **{len(fam['C'])}**"
         + (f" · NON CLASSÉ **{len(fam['?'])}**" if fam['?'] else "") + ".\n",
         "**Méthode.** On classe par TRAITEMENT (ce que feront les lots 2-4), depuis la `raison` de "
         "chaque propose et le CONTENU de sa citation :\n"
         "- **A — formules déduites** : la valeur est une interprétation du texte, pas un chiffre "
         "écrit — barème de stationnement (`non chiffrable`), recul relatif (H/2, « sur limite OU "
         "recul »), renvoi (« se reporter au règlement de la zone »). Une `valeur non numérique` "
         "dont la citation contient un tel motif de formule.\n"
         "- **B — écarts / attributions** : une citation est trouvée mais la valeur (ou son "
         "attribution de secteur) est à CONFIRMER contre la page — `harmonisation ≠ texte` (l'ancien "
         "nombre n'est pas dans la citation), `attribution douteuse` (citation sous secteur None), "
         "ou `valeur non numérique` dont la citation porte un chiffre RÉCUPÉRABLE. La plus grosse.\n"
         "- **C — citation non retrouvée** : `non retrouvée` / `INTROUVABLE` — la règle existe, le "
         "texte n'a pas été localisé.\n\n"
         "La frontière A/B reste provisoire : une règle B peut, à la relecture (lot 2), révéler une "
         "formule (traitée comme A) ou l'absence de règle (→ `absent`).\n"]
    # répartition par rubrique × famille
    import collections
    byrub = collections.Counter((r["chemin"].split(".")[0], r["_famille"]) for r in rows)
    L.append("## Répartition rubrique × famille\n")
    L.append("| rubrique | A | B | C |")
    L.append("| --- | --- | --- | --- |")
    for rub in ("hauteur", "emprise_sol", "retraits", "stationnement", "pleine_terre", "mixite"):
        a, b, c = byrub[(rub, "A")], byrub[(rub, "B")], byrub[(rub, "C")]
        if a or b or c:
            L.append(f"| {rub} | {a} | {b} | {c} |")
    # tableau complet
    L.append("\n## Les 419, par famille\n")
    name = {r["insee"]: (D._load_yaml(str(p)) or {}).get("meta", {}).get("commune")
            for p in Path("config/plu_destinations").glob("974??_*.yaml")
            for r in [{"insee": p.name[:5]}]}
    for F, titre in (("A", "Famille A — formules déduites"),
                     ("B", "Famille B — écarts / attributions (à confirmer contre la page)"),
                     ("C", "Famille C — citation non retrouvée")):
        L.append(f"\n### {titre} ({len(fam[F])})\n")
        L.append("| commune | zone | rubrique | valeur proposée | pourquoi propose | p. |")
        L.append("| --- | --- | --- | --- | --- | --- |")
        for r in sorted(fam[F], key=lambda x: (x["insee"], x["zone"], x["chemin"])):
            cn = name.get(r["insee"]) or r["insee"]
            raison = re.sub(r"\s+", " ", str(r.get("raison") or "")).strip()
            L.append(f"| {cn} | {r['zone']} | {r['chemin']} | {valeur(r)} | {raison} | {r.get('page_pdf','')} |")
    Path("captures/plu-calibrage5/TRIAGE-419.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # json pour lots 2-4
    slim = [{"insee": r["insee"], "fichier": r["fichier"], "zone": r["zone"], "chemin": r["chemin"],
             "famille": r["_famille"], "raison": r.get("raison"), "page_pdf": r.get("page_pdf"),
             "article": r.get("article"), "citation": r.get("citation"),
             "valeur": {k: r[k] for k in _VAL_KEYS if r.get(k) is not None}} for r in rows]
    Path("captures/plu-calibrage5/triage_419.json").write_text(
        json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} propose → A {len(fam['A'])} · B {len(fam['B'])} · C {len(fam['C'])}"
          + (f" · ?? {len(fam['?'])}" if fam['?'] else " · 0 non classé"))
    if fam["?"]:
        for r in fam["?"][:10]:
            print("  NON CLASSÉ", r["insee"], r["zone"], r["chemin"], "|", r.get("raison"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
