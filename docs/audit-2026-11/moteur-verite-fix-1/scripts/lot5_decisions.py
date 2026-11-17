"""MOTEUR-VERITE-FIX-1 LOT 5 — applique les DÉCISIONS du donneur d'ordre sur les 10
interprétations + le nouveau vocabulaire mesurable (bande depuis la voie, plafond de linéaire,
bascule de surface). Génère implantation/LOT5-DECISIONS.csv (mêmes 11 colonnes que les lectures,
citations CONSERVÉES depuis les CSV d'origine) puis le fait injecter par
`injecter_implantation.injecter` (remplacement idempotent des feuilles).

Décisions appliquées :
 1. Le Port Ub latérales : bande de 20 m modélisée (limite dans la bande, retrait au-delà) ;
    ≤ 12 m de largeur → deux limites imposées, sinon au moins une (mode imposé).
 2. Le Port Ud fond : retrait + mention (le texte vise l'alignement sur voisins, pas le fond).
 7. Saint-Joseph U4 : bascule à 400 m² de terrain (≤ 400 → deux limites, > 400 → une seule).
 8. Saint-André UC/UD fond : mention « retrait de fond non chiffré au règlement, valeur des
    latérales appliquée, à vérifier ».
 + Saint-Pierre : plafond de linéaire (60-80 %) et imposition du premier rideau encodés avec le
   vocabulaire mesurable ; la part hauteur-sur-bande reste une mention.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

IMPL = Path(__file__).resolve().parents[1] / "implantation"

#: (insee, zone, cote) → nouveau condition_modelable (None = garder) + mode éventuel + texte ajouté
PATCHES: dict[tuple, dict] = {
    ("97407", "Ub", "laterales"): {"condition_modelable": "profondeur_bande:20 m + largeur_terrain_max:12 m"},
    ("97407", "Ud", "fond"): {"mode": "limite_sous_conditions", "condition_modelable": "non",
                              "condition_texte": "alignement sur les constructions limitrophes "
                              "existantes (décision LOT 5 : ne vise pas le fond) — retrait avec mention"},
    ("97412", "U4", "laterales"): {"condition_modelable": "bascule_surface:400 m²"},
    ("97412", "U4", "fond"): {"condition_modelable": "bascule_surface:400 m²"},
    ("97409", "UC", "fond"): {"condition_texte": "retrait de fond non chiffré au règlement, "
                              "valeur des latérales appliquée, à vérifier"},
    ("97409", "UD", "fond"): {"condition_texte": "retrait de fond non chiffré au règlement, "
                              "valeur des latérales appliquée, à vérifier"},
}

#: Saint-Pierre — latérales : zéro-jeton + plafond de linéaire par zone (lecture agent LOT 2) ;
#: le reste de la condition (hauteur sur bande, 2e rideau) reste en mention via « non ».
SP_LINEAIRE = {"Ug": ("deux_limites_max", 70), "AUg": ("deux_limites_max", 70),
               "Ud": ("une_seule_limite", 80), "Udl": ("une_seule_limite", 80),
               "Ucv": ("une_seule_limite", 80), "UdBO": ("une_seule_limite", 65),
               "Uf": ("une_seule_limite", 60), "UfCA": ("une_seule_limite", 60),
               "AUf": ("une_seule_limite", 60), "AUfGB": ("une_seule_limite", 60)}


def main() -> None:
    rows_out = []
    for insee in ("97407", "97409", "97412", "97416"):
        for r in csv.DictReader(open(IMPL / f"{insee}.csv", newline=""), delimiter=";"):
            key = (insee, (r["zone"] or "").strip(), (r["cote"] or "").strip())
            patch = dict(PATCHES.get(key) or {})
            if insee == "97416" and key[2] == "laterales" and key[1] in SP_LINEAIRE:
                zjeton, pct = SP_LINEAIRE[key[1]]
                patch["condition_modelable"] = f"{zjeton} + lineaire_max_pct:{pct} + non"
            if not patch:
                continue
            nr = dict(r)
            nr.update(patch)
            rows_out.append(nr)
    cols = ["insee", "zone", "cote", "mode", "condition_texte", "condition_modelable",
            "retrait_min_m", "retrait_formule", "citation_verbatim", "article", "page_pdf"]
    with open(IMPL / "LOT5-DECISIONS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)
    print(f"→ LOT5-DECISIONS.csv ({len(rows_out)} feuilles de remplacement)")

    # injection (remplacement idempotent, par commune)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import injecter_implantation as inj
    src = IMPL / "LOT5-DECISIONS.csv"
    for insee in ("97407", "97409", "97412", "97416"):
        rows = [r for r in csv.DictReader(open(src, newline=""), delimiter=";")
                if r["insee"] == insee]
        if not rows:
            continue
        tmp = IMPL / f"_lot5_{insee}.csv"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
            w.writeheader()
            w.writerows(rows)
        orig = inj.IMPL
        try:
            # ruse minimale : injecter() lit IMPL/<insee>.csv — on pointe un dossier temporaire
            import shutil, tempfile
            with tempfile.TemporaryDirectory() as td:
                shutil.copy(tmp, Path(td) / f"{insee}.csv")
                inj.IMPL = Path(td)
                inj.injecter(insee)
        finally:
            inj.IMPL = orig
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
