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
| 1 | Catalogue `postes.yaml` | **fini** | (ce commit) |
| 2 | Moteur `bilan/moteur.py` | à faire | — |
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
- (aucun bloquant pour l'instant)
