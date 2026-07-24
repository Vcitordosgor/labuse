# M15 — LOT A : les outils cassés (diagnostic + réparation)

**Branche** : `fix/m15-a-casses` · **Base** : `main` (M12→M14). Build 0 erreur. Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuves `qa/m15/A/`.

Résultat clé : sur les 4 outils signalés « cassés », **1 l'était vraiment (Assemblage), 1 nécessite une refonte (Matching), et 2 ne sont PAS des bugs de code** (données vides / fonctionne déjà). Diagnostic honnête plutôt que maquillage.

## A1 — Outil « Assemblage » (M16, `moteurs.tsx`) : **RÉPARÉ ✓**

**Cause racine** (trouvée à l'exécution, pas en lisant le code) : le mécanisme de clic marche (`MapView:396` ajoute l'idu à `msel`), **mais en vue Outils les parcelles ne sont pas visibles** : la couche cliquable `ile-fill` est à opacité ~0,03 (style verdict éteint) et les contours `ile-limites` sont gris 0,3 px / 0,4 — invisibles. De plus, à l'échelle de l'île, les tuiles de parcelles ne sont pas chargées. → l'utilisateur voit une carte vide, clique dans le vide, conclut « ne fonctionne pas ».

**Réparation** :
1. Nouvelle couche `ile-pick` (MapView) — contours **violets, bien lisibles, de TOUTES les parcelles**, visible **uniquement quand l'outil Assemblage est actif** (aucun impact ailleurs). Dès qu'on zoome, la grille cadastrale apparaît.
2. Bannière re-guidée : « **Zoomez sur le secteur** pour faire apparaître les contours, puis cliquez-les ».

**Preuve** : `qa/m15/A/a1_grid_zoom.png` (grille cadastrale violette de Saint-Denis visible) + `a1_assemblage_multi.png` (**3 parcelles cumulées par clic**). Reproduire : Outils → Assemblage → zoomer sur une commune → cliquer les parcelles.

## A2 — Outil « Bascules datées » (O10Bascules, `blocB.tsx`) : **PAS UN BUG — données vides, consigné**

**Cause racine** : l'outil lit `/events?limit=100` — **le même journal que la cloche de notifications**. Une « bascule » est un CHANGEMENT d'état d'une parcelle **entre deux runs de scoring**. Avec **un seul run servi**, le journal est vide tant qu'un nouveau run n'a pas été comparé au précédent (ou que la démo n'a pas été semée, `POST /events/demo`). Ce n'est **pas** un bug d'affichage : la requête part, le rendu est monté, l'état vide s'affiche.

**Ce que l'outil est censé faire** (pour la décision de Vic) : lister les bascules datées du run — parcelle passée chaude, match de profil, événement BODACC — avec leur date. C'est le « quoi de neuf » du lundi.

**Action** : message d'état vide réécrit pour l'expliquer honnêtement (plus de « le prochain run alimentera » sec). **Renommage → LOT F.** Discussion ouverte à Vic (le mandat la demande).

## A3 — Outil « Matching promoteurs » (M19, `moteurs.tsx`) : **refonte UI — NON FAITE (consignée)**

**Diagnostic** : l'outil mélange 3-4 sections sans hiérarchie claire — (1) compatibilité parcelle × profils **DÉMO** (illustratif), (2) promoteurs **réellement actifs** SITADEL (réel), (3) profils de recherche (alertes), (4) formulaire d'ajout. Les « zones non cliquables » signalées par Vic = les cartes de profils (`moteurs.tsx:388`) et de promoteurs (`:376`) qui **ressemblent à des boutons mais n'ont aucun `onClick`**. Le champ IDU accepte déjà le clic-carte (via `selectedIdu`).

**Statut** : la **refonte UI/UX complète** demandée est un chantier substantiel (redéfinir ce que chaque carte fait au clic, séparer clairement DÉMO/RÉEL, bandeau RG2). **Non réalisée dans ce bloc** — signalée honnêtement, pas maquillée. À traiter en pass dédiée (elle croise le renommage F et les entrées G). Décision utile pour Vic : dire ce que les cartes profil/promoteur doivent déclencher au clic.

## A4 — Outil « Due diligence » (M10, `ModulePanel.tsx`) : **PAS CASSÉ — multi-parcelles fonctionne (prouvé)**

**Diagnostic** : l'UI a **déjà** un `<textarea>` multi-lignes (une référence par ligne). Test direct de l'endpoint `/modules/duediligence` :
- 2 IDU complets (`97423000AB1908`, `97408000AP1647`) → **n_demandes 2, n_trouvées 2, items 2** ✓
- 2 refs courtes (`AC0253`, `AB1908`) → résolues (`97409000AC0253`, `97420000AB1908`), **2/2** ✓

**Le multi-parcelles fonctionne** — le libellé « Analyser le lot » est **correct**. Ce que fait l'outil : un rapport de risque (score déterministe + checklist cascade + PDF) **par parcelle** d'un lot collé. Le vrai manque = **modes d'entrée** (clic-carte, adresse) — c'est **LOT G (G1)**, pas une réparation A.

## Bilan LOT A
| Outil | Verdict | Preuve |
|---|---|---|
| Assemblage | **Réparé** (grille violette visible + clic + zoom) | `a1_grid_zoom.png`, `a1_assemblage_multi.png` |
| Bascules datées | **Données vides** (pas un bug), état clarifié, discussion Vic | — (empty state) |
| Matching | **Refonte UI non faite** — consignée, à faire en pass dédiée | — |
| Due diligence | **Fonctionne** (multi prouvé) — gap = entrées (LOT G) | test endpoint 2/2 |
