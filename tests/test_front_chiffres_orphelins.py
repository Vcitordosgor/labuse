"""FRONT-CHIFFRES-1 — VERROU : aucun chiffre client fabriqué au front hors registre.

Le banc de cohérence (scripts/coherence) ne voit que les chiffres qui passent par le
registre. Le « 999 % » d'hier vivait dans un composant, invisible du banc. Ce verrou
grep les DEUX motifs du lot A qui fabriquent un chiffre que le client lit — sans passer
par une valeur servie — et échoue sur toute NOUVELLE occurrence non inscrite en liste
blanche (motif présentation-pure, commenté avec sa raison).

Deux familles surveillées (les plus dangereuses de l'inventaire — cf.
docs/audit-2026-09/FRONT-CHIFFRES-1/) :

  Z. ZÉRO-POUR-ABSENCE avec unité : `?? 0` / `|| 0` sur la même ligne qu'une unité
     affichée (€, €/m², m², ha, %, k€, M€, logements). Fabrique « 0 €/m² » / « 0 ha »
     pour une donnée ABSENTE — indistinguable d'un vrai 0. FRONT-CHIFFRES-1 en a corrigé
     six (MonSecteur, RadarMarcheColonne, ModulePanel, ProfilAltimetrique ×… ).

  T. TOTAL D'ÎLE FIGÉ : le littéral de code 431663 / 431_663 (et 227_545), périmé à chaque
     bascule de run. FRONT-CHIFFRES-1 les a remplacés par la notion servie n_parcelles_ile.
     La PROSE « 431 663 » (espace insécable, textes descriptifs) n'est PAS visée ici —
     c'est une dette de catégorie 4 (textes) documentée au rapport, pas un littéral calculé.

Un test SANS framework JS (comme test_front_m2.py) : lit les fichiers en texte.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "frontend" / "src"

# ── liste blanche : occurrences PRÉSENTATION-PURE, chacune avec sa raison ──────────────
# (chemin relatif à frontend/src, sous-chaîne identifiant la ligne) -> pourquoi c'est légitime.
BLANCHE_ZERO: dict[tuple[str, str], str] = {
    ("components/outils/moteurs.tsx", "active.surface_min ?? 0"):
        "récap des BORNES DE FILTRE saisies par l'utilisateur (0 = pas de minimum), pas une mesure servie",
    # COHERENCE-FIX-1 (lot D, fusion) — l'entrée Licences.tsx « (v ?? 0).toFixed(2) » est RETIRÉE :
    # le formateur est corrigé à la racine (montant absent → « — », plus de zéro fabriqué).
}
BLANCHE_TOTAL: dict[tuple[str, str], str] = {}

ZERO = re.compile(r"(\?\?|\|\|)\s*0\b")
# unités AFFICHÉES au client. Bornes de mot pour éviter les faux positifs :
#  · \bha\b  → pas « écHANtillon » / « HAlo » ;
#  · \blogements\b → pas les CHAMPS `logements_au_sol` / `logements_par_batiment` (le « _ »
#    est un caractère de mot : « logements_ » n'a pas de frontière → seul le mot-unité affiché
#    « 30 logements » matche).
UNITE = re.compile(r"€|m²|k€|M€|\bha\b|\s%|\blogements\b")
TOTAL_FIGE = re.compile(r"431_?663|227_?545")


def _fichiers() -> list[Path]:
    return [p for p in SRC.rglob("*.ts*")
            if p.suffix in (".ts", ".tsx") and ".test." not in p.name]


def _sans_commentaire(ligne: str) -> str:
    """retire un commentaire de fin de ligne `// …` (naïf : suffit pour ce grep)."""
    i = ligne.find("//")
    return ligne[:i] if i >= 0 else ligne


def test_front_sans_chiffre_orphelin():
    coupables: list[str] = []
    for p in _fichiers():
        rel = p.relative_to(SRC).as_posix()
        for n, brute in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            ligne = _sans_commentaire(brute)
            if not ligne.strip():
                continue

            # Famille Z — zéro-pour-absence avec unité
            if ZERO.search(ligne) and UNITE.search(ligne):
                if not any(rel == f and marq in ligne for (f, marq) in BLANCHE_ZERO):
                    coupables.append(f"[Z zéro-pour-absence] {rel}:{n}  {ligne.strip()[:110]}")

            # Famille T — total d'île figé en littéral de code
            if TOTAL_FIGE.search(ligne):
                if not any(rel == f and marq in ligne for (f, marq) in BLANCHE_TOTAL):
                    coupables.append(f"[T total figé] {rel}:{n}  {ligne.strip()[:110]}")

    assert not coupables, (
        "Chiffre(s) client fabriqué(s) au front, hors registre et hors liste blanche.\n"
        "Rendez l'absence par le vocabulaire du registre (null → « — » via lib/format.ts), "
        "ou lisez la notion servie ; sinon inscrivez l'occurrence en liste blanche AVEC sa raison "
        "(présentation pure).\n  " + "\n  ".join(coupables))


def test_liste_blanche_a_jour():
    """une entrée de liste blanche qui ne correspond plus à aucune ligne = à retirer
    (empêche la liste de pourrir et de masquer une régression future)."""
    textes = {p.relative_to(SRC).as_posix(): p.read_text(encoding="utf-8")
              for p in _fichiers()}
    mortes = [f"{f} :: {marq}" for (f, marq) in {**BLANCHE_ZERO, **BLANCHE_TOTAL}
              if marq not in textes.get(f, "")]
    assert not mortes, "Entrée(s) de liste blanche périmée(s) : " + " | ".join(mortes)


def test_correctifs_front_chiffres_ne_regressent_pas():
    """garde POSITIVE des cinq correctifs (commit « supprimer ») — verrouille le geste."""
    def lire(rel: str) -> str:
        return (SRC / rel).read_text(encoding="utf-8")

    # FiltreLabuse lit la notion servie, ne code plus le total d'île
    fl = lire("components/panel/FiltreLabuse.tsx")
    assert "getAccueilChiffres" in fl and "totalIle" in fl
    assert "431_663" not in fl and "431663" not in fl
    # MonSecteur : prix médian absent → « — », plus de ?? 0
    ms = lire("components/outils/MonSecteur.tsx")
    assert "sb.median_eur_m2 != null" in ms and "sb.median_eur_m2 ?? 0" not in ms
    # ModulePanel : surface totale via formateur partagé (m²/ha + null → « — »)
    assert "fmtM2(d['surface_totale_m2']" in lire("components/outils/ModulePanel.tsx")
    # TaxeAmenagement : millésime servi, plus de « 2026 » figé
    assert "Valeurs ${c.meta.annee}" in lire("components/outils/TaxeAmenagement.tsx")
