# RADAR-2 — retouches 2 (recette Vic)

Branche `feat/radar-2`, worktree `labuse-radar2b`, ports 8565/5765. Pas de merge.
Captures avant/après à 1440 px sous `avant/` et `apres/`.

## 1. Prix acté vide (priorité) — CAUSE & correctif

**Symptôme** : « Le marché · Toute l'île » affichait, pour les maisons, « médiane DVF · 0 vente »
(prix acté « sous le seuil »), alors que la médiane actée existe bel et bien.

**Cause** : dans `marche.tableau` → `_demande_acte(t)` (`src/labuse/pige/marche.py`), l'acté DVF
n'était calculé **que `if commune`**. Pour « Toute l'île » (`commune is None`), `av/an` restaient
`None/0` → tous les types île sortaient « 0 vente ». Les communes, elles, marchaient déjà.

**Correctif (un seul moteur, aucun chiffre nouveau)** :
- `signaux._dvf_bati_type(db, commune=None, type)` : le filtre `commune = :c` devient optionnel →
  médiane ÎLE ENTIÈRE du type (maison/appartement), même filtre de retenue `_BAROMETRE_RETENUE`.
- `signaux._dvf_terrain(db, commune=None)` : branche ÎLE (médiane du terrain nu en zones U/AU,
  `dvf_mutations_parcelle` dédupliqué par mutation — même logique que `ligne2_terrain_zone`, sans le
  filtre commune).
- `marche._demande_acte` : le garde `if commune` tombe → l'acté est servi **pour chaque type, île ET
  commune**. La cohérence « 4 chiffres du haut = ligne maison du tableau » est conservée (même appel).

**Vérifié (LIVE, DB prod)** :

| Portée | acté maison €/m² (n) | terrain | appartement |
|---|---|---|---|
| Toute l'île | **2 623 (15 091 ventes)** | 330 | 2 564 |
| Saint-Denis | 3 085 (1 810) | 485 | 2 391 |
| Saint-Benoît | 1 948 (532) | 237 | 1 428 |

Avant le correctif, l'île renvoyait `{valeur: None, n: 0}` ; après, `{valeur: 2623, n: 15091}`.

## 2. Une seule vue — bloc « Ce bien » en tête de la colonne marché

L'écran séparé « Ce bien face à son marché » disparaît. La colonne de droite reste **toujours** le
marché de la commune. Quand une annonce est sélectionnée, un bloc compact **« Ce bien »** s'insère en
tête (au-dessus des 4 chiffres) : €/m², prix, écart vs demandé et vs acté (de sa commune + son type),
ancienneté (vs médiane commune), historique en une ligne, « Voir l'annonce ↗ », croix pour fermer.
Le marché affiché **bascule sur la commune de l'annonce** (`RadarMarcheColonne` prend `bienId` +
`onCloseBien` ; la portée = commune du bien). `BienVsMarche` (plein écran) est supprimé.

## 3. « M'alerter sur ces critères » retiré de Radar

Le bouton et sa mutation `creerRadarVeille` quittent `RadarEcran`. Créer une alerte se fait désormais
dans la Veille (§4).

## 4. Créer une alerte dans Veille · les annonces

« + Nouvelle alerte » (plus « depuis Radar ») ouvre un **formulaire** dans l'écran : commune(s) (chips
+ ajout), type, prix max, surface min, vendeur. **Au moins une commune OU un type** est exigé (message
sinon). Un **doublon** est refusé côté serveur (HTTP 409 « Vous avez déjà une alerte avec ces
critères. ») via `veille.existe_identique` / `_norme` (forme canonique : communes triées, commune seule
fondue dans `communes`) — insensible à l'ordre de saisie.

Vérifié LIVE : création `{communes:[Cilaos],type_bien:terrain}` → 200 ; ré-émission
`{type_bien:terrain,communes:[Cilaos]}` → **409** (message ci-dessus).

### ⚠ Alertes SANS aucun critère existantes (signalées, PAS supprimées)

Deux alertes du corpus n'ont **aucun critère** (chips « Tous les biens ») : **ids 27 et 28**. Elles
sont conservées telles quelles (le mandat demande de les signaler, pas de les purger). Le nouveau
formulaire empêche d'en créer d'autres (règle « au moins une commune ou un type »).

## 5. Défilement Veille · le foncier / les annonces

Les écrans du hub étaient rendus dans un conteneur parent `overflow-hidden` sans propre zone de
défilement → contenu long tronqué. Chaque écran plein écran (portes Radar, portes Veille, foncier,
annonces) est enveloppé d'un `min-h-0 flex-1 overflow-y-auto` → la page défile jusqu'en bas.

## 6. Veille · le foncier — invite carte retirée

`ParcelInput` reçoit `withCarte={false}` sur cette page (il n'y a pas de carte) → l'invite « ou
cliquez une parcelle sur la carte » disparaît (et le geste clic-carte, sans objet ici, est désactivé).

## Vérifications

`tsc` 0 · `build` OK · `vitest` 218/218 · pytest ciblé (pige_marche, pige_api, veille2 lots 1-3,
veille_fix2 lot A) 18/18. Captures 5 écrans × avant/après (1440 px).

## Fichiers touchés

- `src/labuse/pige/signaux.py` — `_dvf_bati_type`/`_dvf_terrain` acceptent `commune=None` (médiane île).
- `src/labuse/pige/marche.py` — `_demande_acte` sert l'acté île+commune (garde `if commune` retiré).
- `src/labuse/pige/veille.py` — `_norme` + `existe_identique` (anti-doublon).
- `src/labuse/pige/api.py` — POST `/radar/veille` refuse un doublon (409).
- `frontend/…/RadarMarcheColonne.tsx` — bloc « Ce bien » en tête, bascule de portée, `BienVsMarche` retiré.
- `frontend/…/RadarEcran.tsx` — « M'alerter » retiré ; colonne = marché unique (bienId/onCloseBien).
- `frontend/…/VeilleEcrans.tsx` — formulaire d'alerte, défilement, `withCarte={false}` (foncier).
- `frontend/…/RadarHub.tsx` — défilement de l'écran des portes.
