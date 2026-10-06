# BILAN-1 — Suivi d'exécution

Branche `feat/bilan-1` · worktree `~/Desktop/labuse-bilan1` · ports 8820 / 6020.
Base = `origin/main` du jour (`01965f44`). Modèle : Opus.

Venv : `~/Desktop/labuse/.venv/bin/python` ; imports LABUSE depuis ce worktree avec
`PYTHONPATH=src`. Le xlsx de la promotrice est copié en `docs/audit-2026-10/bilan-1/modele-promotrice.xlsx`
(gitignoré, jamais commité).

## État des lots
| Lot | Sujet | État | Commit |
|-----|-------|------|--------|
| 0 | Vérifs + pièces en place | **fini** | — |
| 1 | Catalogue `postes.yaml` | **fini** | bfe82e8e |
| 2 | Moteur `bilan/moteur.py` | **fini** | (ce commit) |
| 3 | Écran onglet Bilan + porte Docs | à faire | — |
| 4 | Ratios du compte `bilan_ratios` | à faire | — |
| 5 | Sorties PDF + Excel + documents_generes | à faire | — |
| 6 | Page Docs 8 cartes | à faire | — |
| 7 | Recette + rapport + captures | à faire | — |

## Étape 0 — faits
- `pwd` = /Users/openclaw/Desktop/labuse-bilan1 ; branche `feat/bilan-1` ; arbre propre (seul le dossier bilan-1 non suivi).
- Base `01965f44` = `origin/main` : contient DOCS-1 + DOCS-FIX-1. **TUILES-TX-1 (`2f6cf7ec`) n'est PAS mergé dans origin/main** (signalé à Vic) — sans effet sur ce mandat (fix tuiles MVT, hors périmètre bilan/docs).
- `maquette.html` = maquette-bilan-v2.html (identique au téléchargement). `modele-promotrice.xlsx` copié + gitignoré.

## Analyse du modèle (xlsx) — faite
- 2 feuilles : **BILAN** (`A1:G147`, la cible) et **Grille surface** (hors mandat).
- Le classeur a des `definedNames` cassés (`#N/A`, legacy) → openpyxl refuse ; lu via copie temporaire patchée (`/tmp`), l'original n'est jamais touché.
- **45 postes de charges** en 4 blocs (règle de comptage déterministe, cf. rapport) :
  - Terrain / Charge foncière : 18 postes (lignes 43-60)
  - Construction & honoraires techniques : 10 postes (66-75)
  - Gestion : 10 postes (81-90)
  - Frais de vente / Commercialisation : 7 postes (98-104)
- + **2 lignes produit** (CA) : lignes 112-113 (« Programme = une ligne par produit »).
- Cellules cassées du modèle (non reproduites, listées au rapport) : `E13` coût const./SHON = `#DIV/0!` (SHON `E6` vide).
- Nom de société dans le modèle : « Cash flow océanis » (lignes 122/128) + chemin SharePoint en métadonnée (fichier non commité) → libellé rendu « Cash flow » / « Cash flow sans aléas ».

## Décisions / points pour Vic
- **Repères « ratio de place ».** La doctrine écrite dit « un repère sans source publique ne s'affiche pas », mais la maquette v2 (validée) montre des repères de ratio (commission 3 %, notaire 1,5 %, honoraires…) et sa propre note liste « ratios de place » comme source de repère. J'ai tranché **selon la maquette** : deux familles de repères, `registre` (source publique : DVF, outil Taxe, archéo, coût de référence, Faisabilité) et `ratio_place` (ratio de place, étiqueté honnêtement). Aucun n'entre dans le calcul sans clic. À vetoer si tu préfères masquer les ratios de place.
- **Non-régression — 2 écarts de convention assumés.** Le moteur reproduit le bilan de la promotrice **au centime sur 43 des 45 lignes**. Deux lignes diffèrent car elle a composé leur assiette à la main : assurances **D.O / C.N.R** et **TRC + GAREAT** ont pour base « total (2) + étude de sol − imprévus » ; la maquette validée a simplifié en « total (2) ». Écart : +1 109,96 € (DO) et +263,50 € (TRC) sur un bilan de 12,4 M€ → résultat net 1 243 623 € vs 1 244 997 € (−1 373 €). Résidu inexpliqué = 0. La commission d'apport (3 % TTC) est, elle, reproduite exactement via `base: ttc`.
- **Cellule cassée du modèle non reproduite.** `E13` (coût construction / SHON) = `#DIV/0!` car la SHON `E6` est vide dans le modèle témoin ; c'est un ratio d'affichage, sans effet sur les totaux.
