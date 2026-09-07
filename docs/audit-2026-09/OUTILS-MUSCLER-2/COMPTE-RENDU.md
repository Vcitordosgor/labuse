# OUTILS-MUSCLER-2 — compte-rendu (07/09/2026)

**Verdict A (3 lignes).** Les quatre familles sont servables : ventes (DVF vivante 2021-25 + histo 2014-20, jour), permis
(autorisation jour, dépôt 83 % année seule, DAACT jour 41,5 %), découpes (DFI `date_validation` jour, 1989-2025 — datables,
la famille RESTE) ; propriétaires PM à la maille MILLÉSIME (écart constaté 2019→2025, jamais une date). Aucune écartée.

**Commits.** Lot A `228e52bf` (inventaire) · Lot B `67f99195` (endpoint + 5 tests) · Lot C (frise + 4 tests vitest + recette).
**Preuves.** PNG impossibles (Playwright expire, comme 1B) → `captures/PREUVE-DOM.md` : 10 faits/4 familles sur AS0641,
mailles visibles (« 2013 (année seule…) », « entre le 1ᵉʳ janv. 2019 et le 1ᵉʳ janv. 2020 »), ponts aller-retour vérifiés
(Permis → tiroir du permis exact + fil restaurant la parcelle ; vente → fiche tiroir « marche » ouvert ; PM → Scan), C5/C6.
**B4.** HTTP, base labuse : AB0009 107/34/28 ms · AC0024 35/28/34 ms · AE0003 33/34/30 ms (à froid ~107, chaud < 40).

**A résisté.** (1) Découpes pressenties non datables : `dfi_filiation` (409 623 lignes, source enregistrée) porte une vraie
date jour — mais la table n'avait AUCUN lecteur (`src/labuse` : zéro référence) ; la frise est son premier service, garde
`to_regclass` (non-ORM, `moteurs.py:398`). (2) Un remaniement lie jusqu'à 789 parcelles à une fille → regroupement par
(date, nature, sens), liste bornée à 12, total toujours servi (`_HISTOIRE_CAP_FILIATION`). (3) Fil de retour du pont vente
RETIRÉ après recette : la fiche est un overlay au-dessus de l'outil resté ouvert — un fil « temps→temps » (FIX-3 = outil→outil).

**Décisions faute d'instruction.** Permis = un fait PAR ÉVÉNEMENT daté (dépôt/autorisation/DAACT — B1 les nomme) ; axe
linéaire 1950→auj. portant les repères TEMPS_MILLESIMES à leur année (la frise catégorielle du panneau M08 ne bouge pas) ;
prix DVF étiqueté « mutation entière » (il peut couvrir plusieurs parcelles) ; marqueurs = tokens DA existants
(amber/mint/blue/violet). Aucune lecture run-scopée (aucun score servi) — la constante de run n'est pas sollicitée.

**Tests.** Back : 5 neufs verts ; suite 2 721 passed / 10 failed = 9 PRÉ-EXISTANTS (mêmes qu'avant le mandat : verrous
base-réelle ×3, courrier_boucle ×2, dashboard, front_reliquats, run_serving, sentinelle) + `test_non_contradiction[BV0120]`
FLOTTANT d'ordre (vert en isolation, patron RETOURS-11F ; l'endpoint neuf ne touche aucun chemin existant).
Front : tsc 0 · vitest 191/191 (dont 4 frise) · build OK. ⚠ serveurs de recette arrêtés — redémarrage à la charge de Vic.
