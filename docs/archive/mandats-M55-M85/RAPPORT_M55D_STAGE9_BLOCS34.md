# RAPPORT M55-D stage 9 — blocs 3 & 4 : périmètre/filtre, accordéon

Branche `feat/m55-d-stage9-suite` (base `main` ce5ad8f7 — les blocs 1 « accueil qui prouve » et
2 « responsive » de ce mandat sont DÉJÀ livrés et mergés, cf. RAPPORT_M55D_STAGE9_PHASE1/2).
Un commit par bloc. tsc 0, vitest 32/32, build vert.

## Bloc 3 — le périmètre propose, le filtre dispose (commit 370c5eba)
- **Header** : le sélecteur mono-commune est **restauré** — « Saint-Leu » → **zoom 11,9** sur son
  emprise + **CP 97424 coché visiblement** dans le filtre Communes + compteur borné (**22 959**,
  le parc de Saint-Leu — requête `/filtre?communes=Saint-Leu` prouvée). « ⓘ Contexte » conservé.
- **Sens unique** : décocher au panneau → filtre retiré, **compteur recalculé à l'île (431 663)**,
  **la carte reste où elle est** (zoom inchangé 11,9 — prouvé). `setCommunesFilter` ne touche
  plus la vue carte.
- **« Toute l'île »** au header → **dézoom (9,8)** + décoche + header vidé (prouvé).
- **Multi** (≥ 2, posé au panneau) : le header devient une **vue** « N communes » dont le clic
  ouvre le panneau. Clic-commune M55-C : même règle (zoom + fiche + pré-coche, inchangé).
- **Plomberie** : les appels `/filtre` (compteur, liste, stats, **export CSV** — doctrine M46
  « mêmes facettes que le compteur ») ne portent **plus la commune-vue** (builder `qf` sans
  `commune()`) : le périmètre du compteur est `filters.communes` seul. Les endpoints carte
  (couches, geojson) gardent la vue — ils servent ce que la carte regarde. **Jamais deux états
  divergents : le header est la vue de `filters.communes`.**
- **Libellé header — proposition au rapport** : j'ai gardé le sobre « Saint-Leu » ; l'alternative
  « **Vue : Saint-Leu** » est prête si tu la préfères (un mot à dire).

## Bloc 4 — l'accordéon devient une propriété de l'état (commit dernier)
**Mesure des chemins d'ouverture** : titres/chevrons Couches et Filtres (exclusifs via toggles) ;
MAIS `openFiltres()` (header-périmètre, **« Commencer → » de l'accueil**) posait
`filtresOpen:true` **sans toucher `couchesOpen`** — un état **local** de LeftPanel, **ouvert par
défaut** → deux sections ouvertes (le constat exact). L'exclusivité n'était qu'un effet de bord
du clic.

**Fix** : `panneauSection: 'couches' | 'filtres' | null` (store, défaut `couches`) — **une seule
section ouverte possible par construction**, quel que soit le chemin (toggles, openFiltres,
rétract de la Révélation, repli à l'allumage de l'analyse). `couchesOpen`/`filtresOpen` sont
dérivés, plus jamais posés indépendamment.

**Validation, chaque chemin** : défaut = Couches seule ✓ · « Commencer → » = Filtres ouvre ET
Couches ferme ✓ · toggles exclusifs ✓ · header-périmètre puis Filtres = une seule ouverte ✓.
Captures `s9s_accordeon_commencer`, `s9s_perimetre_coche`.

## Non-régression globale (vert)
5 combinaisons `/filtre` identiques (9822 · 188 · 1710 · 3770 · 51129) · vieux lien
`tv+smin` 0 erreur, analyse héritée · **rituel 3,00 s** · **synchro stage 8 préservée**
(compteur 9822 == bandeau 9822).

CC ne merge jamais.
