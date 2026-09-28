"""COHERENCE-1 lot A — LE RÉFÉRENTIEL DES NOTIONS.

Une *notion* = une chose que le client lit (surface, zone PLU, SDP restante, prix médian…).
Le référentiel n'est PAS saisi à la main : il est DÉRIVÉ des quatre déclarations que le code
porte déjà, croisées ici une fois :

  · registre/donnees.py   → les 286 données (libellé, unité, type, moteur, réservoirs) ;
  · registre/robinets.py  → les écrans qui les servent (catégorie, route, mode de rendu) ;
  · registre/lectures.py  → les arêtes fines table→fichier lecteur ;
  · declarations/*.yaml   → les câbles par surface (rang, format, PHRASE D'ABSENCE) ;
  · docs/audit-2026-09/SOURCES-AUDIT-3/BRANCHEMENT.csv → fichier:ligne mesurés par consommateur.

Sorties (docs/audit-2026-09/COHERENCE-1/) :
  · NOTIONS.csv   — une ligne par notion : id · libellé client · unité · type
                    (mesuré/dérivé/agrégé) · sources · tolérance · n lecteurs · lecteurs ;
  · LECTEURS.csv  — le format long : une ligne par (notion, lecteur) avec route/fichier ;
  · ABSENCES.csv  — le vocabulaire d'absence déclaré : phrase exacte par notion et surface.

Usage : PYTHONPATH=src python scripts/coherence/referentiel.py
Lecture seule sur le code ; n'écrit que sous docs/audit-2026-09/COHERENCE-1/.
"""
from __future__ import annotations

import csv
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))

from labuse.registre.donnees import DONNEES          # noqa: E402
from labuse.registre.robinets import ROBINETS        # noqa: E402
from labuse.registre.lectures import LECTURES        # noqa: E402
from labuse.registre import declarations             # noqa: E402

SORTIE = RACINE / "docs" / "audit-2026-09" / "COHERENCE-1"
BRANCHEMENT = RACINE / "docs" / "audit-2026-09" / "SOURCES-AUDIT-3" / "BRANCHEMENT.csv"


def type_notion(d) -> str:
    """mesuré = passe-plat d'une source ; agrégé = statistique de niveau commune/zone/global
    calculée par un moteur ; dérivé = tout calcul par parcelle (moteur, SQL propre, front)."""
    if d.calcul in ("passe_plat", "constante"):
        return "mesure"
    if d.niveau in ("commune", "zone", "global") and d.calcul in ("moteur", "sql_propre"):
        return "agrege"
    return "derive"


#: tolérance de comparaison admise entre deux lecteurs de la même notion.
#: classes/textes/verdicts : 0 (identité stricte). Pourcentages : 0,5 point (arrondi
#: d'affichage). Montants et surfaces : 1 % relatif (arrondis d'affichage documentés).
def tolerance(d) -> str:
    t = d.type if d.type != "auto" else {"classe": "classe", "verdict": "texte",
                                         "tranche": "classe", "date": "texte"}.get(d.unite, "nombre")
    if t in ("classe", "texte", "liste", "geometrie", "couche"):
        return "0 (identité)"
    if d.unite == "%":
        return "0,5 point"
    if d.unite in ("€", "€/m²"):
        return "1 %"
    if d.unite in ("m²", "m", "ha"):
        return "1 %"
    if d.unite in ("logements", "nombre"):
        return "0 (entier)"
    return "1 %"


def charger_branchement() -> list[dict]:
    if not BRANCHEMENT.exists():
        return []
    with open(BRANCHEMENT, newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)

    # 1. lecteurs par notion — trois familles de déclarations, dédoublonnées
    lecteurs: dict[str, list[dict]] = {cid: [] for cid in DONNEES}
    for rid, r in ROBINETS.items():
        for cid in r.chiffres:
            if cid in lecteurs:
                lecteurs[cid].append({"lecteur": rid, "famille": "robinet",
                                      "categorie": r.categorie, "nom": r.nom,
                                      "ou": r.route, "rendu": r.mode_rendu, "absence": ""})
    for lec in LECTURES:
        if lec.chiffre and lec.chiffre in lecteurs:
            lecteurs[lec.chiffre].append({"lecteur": f"lecture:{lec.fichier}",
                                          "famille": "lecture_fine", "categorie": "code",
                                          "nom": lec.note[:120], "ou": f"src/labuse/{lec.fichier} (table {lec.table})",
                                          "rendu": "", "absence": ""})
    absences: list[dict] = []
    surfaces, _generiques = declarations.charger()
    for s in surfaces:
        srf = s.surface
        route = s.route or ""
        fichier = str(s.chemin or "")
        for c in s.donnees or []:
            quoi = c.quoi
            if not quoi or quoi not in lecteurs:
                continue
            absence = c.absence or ""
            atype = c.absence_type or ""
            lecteurs[quoi].append({"lecteur": f"declaration:{srf}", "famille": "declaration",
                                   "categorie": getattr(s, "categorie", ""), "nom": srf,
                                   "ou": f"{route} ({fichier})", "rendu": "", "absence": absence})
            if absence:
                absences.append({"notion": quoi, "surface": srf, "route": route,
                                 "phrase_absence": absence, "absence_type": atype,
                                 "declaration": fichier})

    # 2. fichier:ligne mesurés (SOURCES-AUDIT-3) — rattachés par consommateur↔catégorie
    branchement = charger_branchement()

    # 3. NOTIONS.csv (une ligne par notion) + LECTEURS.csv (long)
    with open(SORTIE / "NOTIONS.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["notion_id", "libelle_client", "unite", "niveau", "type",
                    "calcul", "producteur", "sources", "portee", "tolerance",
                    "n_lecteurs", "lecteurs", "en_attente"])
        for cid, d in sorted(DONNEES.items()):
            ls = lecteurs[cid]
            w.writerow([cid, d.libelle, d.unite, d.niveau, type_notion(d),
                        d.calcul, d.fonction, "|".join(d.reservoirs), d.portee,
                        tolerance(d), len(ls),
                        " | ".join(sorted({x["lecteur"] for x in ls})),
                        d.en_attente or ""])

    with open(SORTIE / "LECTEURS.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["notion_id", "lecteur", "famille", "categorie", "nom_ecran",
                    "route_ou_fichier", "rendu", "phrase_absence"])
        for cid in sorted(DONNEES):
            for x in sorted(lecteurs[cid], key=lambda y: (y["famille"], y["lecteur"])):
                w.writerow([cid, x["lecteur"], x["famille"], x["categorie"],
                            x["nom"], x["ou"], x["rendu"], x["absence"]])

    with open(SORTIE / "ABSENCES.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["notion", "surface", "route", "phrase_absence",
                                          "absence_type", "declaration"])
        w.writeheader()
        w.writerows(sorted(absences, key=lambda a: (a["notion"], a["surface"])))

    # 4. compte-rendu console
    multi = sum(1 for cid in DONNEES if len({x["lecteur"] for x in lecteurs[cid]}) >= 2)
    zero = [cid for cid in DONNEES if not lecteurs[cid] and not DONNEES[cid].en_attente]
    print(f"notions: {len(DONNEES)} · lecteurs (robinets): {len(ROBINETS)} · "
          f"lectures fines: {len(LECTURES)} · branchement mesuré: {len(branchement)} lignes")
    print(f"notions à ≥2 lecteurs (candidates cohérence): {multi}")
    print(f"notions sans aucun lecteur déclaré (hors en_attente): {len(zero)} {zero[:8]}")
    print(f"phrases d'absence déclarées: {len(absences)}")
    print(f"→ {SORTIE}/NOTIONS.csv, LECTEURS.csv, ABSENCES.csv")


if __name__ == "__main__":
    main()
