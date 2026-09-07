# OUTILS-MUSCLER-2 — preuve d'écran (DOM mesuré, app réelle, base labuse)

Playwright expire sur cet écran (timeout MCP 5 s avant écriture du PNG — canvas WebGL masqué sans
effet), comme en MUSCLER-1B → preuve DOM, conformément au mandat.

## Avant (main @ 29eaea05)
L'outil Remonter le temps = comparateur swipe seul (TimeMachine) + panneau M08. Aucune frise de
faits, aucun endpoint `/moteurs/histoire` — l'utilisateur devine ce qui s'est passé entre deux orthos.

## Après — parcelle riche 97401000AS0641 (Les Avirons), mesuré sur http://localhost:5173
- `friseSousComparateur: true` (rect de `[data-histoire-frise]` sous celui du comparateur — C1,
  poignée et libellés du swipe intacts : `poignee: true`, `comparateurIntact: true`).
- **10 faits, 4 familles, mailles visibles dans les titres** (C2) :
  VEFA 12/04/2024 · Vente 30/07/2021 · Changement de propriétaire (PM) « entre le 1ᵉʳ janv. 2019
  et le 1ᵉʳ janv. 2020 » · PC déposé 06/09/2018 · Vente 30/08/2018 · PC autorisé 22/09/2017 ·
  DAACT 26/03/2015 · PC autorisé 27/05/2014 · **PC déposé « 2013 (année seule — la source ne
  publie pas le jour) »** · Parcelle issue d'un document d'arpentage 12/12/1991.
- Repères : point plein = jour, anneau large = année seule, tirets = entre deux millésimes ;
  légende rendue (`[data-histoire-legende]`). Empilement par rangées, aucun fait masqué (C3).
- **Détail au clic** (C3) : « Vente en l'état futur d'achèvement · 12/04/2024 · 54 250 €
  (mutation entière) · Sourcé · DVF (DGFiP) — ventes actées · Voir la fiche — ventes → ».
- **Ponts C4 vérifiés en aller-retour** :
  · permis → tiroir Permis du permis EXACT (97440117A0031, Les Avirons, parcelle AS0641 listée) ;
    fil « ← Remonter le temps » → retour restaure l'outil, parcelle ré-épinglée, 10 faits ré-affichés ;
  · vente → fiche parcelle ouverte, tiroir « marche » (ventes) OUVERT (`marcheOuvert: true`) —
    sans fil de retour (fiche = overlay au-dessus de l'outil resté ouvert) ;
  · propriétaire PM → Scan patrimoine sur le SIREN (même mécanisme m02Prefill, garde vitest).
- **Bandeau C6** : « Faits datés — DVF (DGFiP) : 31/12/2025 · Sit@del (SDES) : 31/07/2026 ·
  Fichiers fonciers PM (DGFiP) : millésimes 2019→2024 · DFI (DGFiP) : 29/12/2025 ».

## Après — parcelle sans fait 97417000AE0003 (Saint-Philippe, RNU)
`[data-histoire-vide]` : « Aucun fait daté connu pour cette parcelle (ventes, permis,
propriétaire, découpes). » — comparateur et poignée intacts (C5).

Console : 18 erreurs = 404 de tuiles ortho AU LARGE (comportement documenté du proxy V1,
préexistant, sans lien avec la frise).
