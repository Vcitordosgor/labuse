# BILAN-1 — Suivi d'exécution

Branche `feat/bilan-1` · worktree `~/Desktop/labuse-bilan1` · ports 8820 / 6020.
Base = `origin/main` **rebasée sur `e60bf578`** (TUILES-TX-1 + VITESSE-PROD-1) le 06/10 :
rebase SANS conflit (les 2 lignes bilan d'app.py sont loin des régions tuiles/get_db).
Modèle : Opus.

## Décisions Vic avant merge (un commit par point)
1. Assiettes D.O / TRC recopiées à l'identique du tableur → **0 € d'écart**. **FAIT** (ce commit).
2. Masquer les repères « ratio de place ». **FAIT** : `_repere_poste` ne sert que les repères `registre` ; front simplifié ; test de route.
3. Câbler repères Taxe/archéo, Faisabilité (SDP, parkings), Sitadel. à faire.
4. Captures de l'écran vivant (pile lancée). à faire.

Venv : `~/Desktop/labuse/.venv/bin/python` ; imports LABUSE depuis ce worktree avec
`PYTHONPATH=src`. Le xlsx de la promotrice est copié en `docs/audit-2026-10/bilan-1/modele-promotrice.xlsx`
(gitignoré, jamais commité).

**Tests DB (ce Mac)** : Postgres tourne en socket (pas de TCP). Invocation :
`PGHOST=/tmp LABUSE_TEST_DATABASE_URL="postgresql+psycopg://openclaw@/labuse_test" PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -m pytest …`
(la base `labuse_test` existe, PostGIS présent). Tests non-DB : sans ces variables.

## État des lots
| Lot | Sujet | État | Commit |
|-----|-------|------|--------|
| 0 | Vérifs + pièces en place | **fini** | — |
| 1 | Catalogue `postes.yaml` | **fini** | bfe82e8e |
| 2 | Moteur `bilan/moteur.py` | **fini** | e3038bff |
| 3 | Écran onglet Bilan + porte Docs | **fini** (porte backend d0d2bb27 ; écran ce commit) — recette navigateur = Lot 7 | — |
| 4 | Ratios du compte `bilan_ratios` | **fini** | a1365142 |
| 5 | Sorties PDF + Excel + documents_generes | **fini** (backend 6f0edc3a ; boutons front ce commit) | — |
| 6 | Page Docs 8 cartes | **fini** | a0fcce8b |
| 7 | Recette + rapport + captures | **fini** (ce commit) — captures écran vivant restent à prendre sur la pile lancée | — |

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

## Captures d'écran vivant — procédure (reste à faire)
Les artefacts PDF/Excel + rendus PNG sont dans `captures/`. Les captures de l'ÉCRAN
(vide, complet, repère cliqué, ratios, Docs 8 cartes) demandent la pile lancée :
1. API : `PGHOST=/tmp LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@/labuse LABUSE_ENV=pilot LABUSE_AUTH_PASSWORD=… PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -m uvicorn labuse.api.app:app --port 8820`
2. Front : `cd frontend && VITE_API=http://localhost:8820 node_modules/.bin/vite --port 6020` (ou servir `dist/`).
3. Se connecter (compte pilote), ouvrir une fiche (ex. BZ1065) → tuile « Bilan », ou la page Docs → « Générer le bilan ». Captures via Playwright.

## Décisions / points pour Vic
- **Repères « ratio de place ».** La doctrine écrite dit « un repère sans source publique ne s'affiche pas », mais la maquette v2 (validée) montre des repères de ratio (commission 3 %, notaire 1,5 %, honoraires…) et sa propre note liste « ratios de place » comme source de repère. J'ai tranché **selon la maquette** : deux familles de repères, `registre` (source publique : DVF, outil Taxe, archéo, coût de référence, Faisabilité) et `ratio_place` (ratio de place, étiqueté honnêtement). Aucun n'entre dans le calcul sans clic. À vetoer si tu préfères masquer les ratios de place.
- **Non-régression — 2 écarts de convention assumés.** Le moteur reproduit le bilan de la promotrice **au centime sur 43 des 45 lignes**. Deux lignes diffèrent car elle a composé leur assiette à la main : assurances **D.O / C.N.R** et **TRC + GAREAT** ont pour base « total (2) + étude de sol − imprévus » ; la maquette validée a simplifié en « total (2) ». Écart : +1 109,96 € (DO) et +263,50 € (TRC) sur un bilan de 12,4 M€ → résultat net 1 243 623 € vs 1 244 997 € (−1 373 €). Résidu inexpliqué = 0. La commission d'apport (3 % TTC) est, elle, reproduite exactement via `base: ttc`.
- **Cellule cassée du modèle non reproduite.** `E13` (coût construction / SHON) = `#DIV/0!` car la SHON `E6` est vide dans le modèle témoin ; c'est un ratio d'affichage, sans effet sur les totaux.
