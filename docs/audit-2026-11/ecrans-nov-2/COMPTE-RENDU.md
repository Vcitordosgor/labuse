# ECRANS-NOV-2 — compte rendu

**Mandat** ECRANS-NOV-2 — l'écran **Analyse LABUSE par scénario**, **DANS le panneau de gauche**
(342 px, à côté de la carte), à la place de l'ancien bloc Score / Signal / Classer par.
**Branche** `feat/ecrans-nov-2` (worktree `~/Desktop/labuse-ecrans2`). **Aucun merge, aucun accès
production.** Front + API (lecture seule). Ports : front **9990**, back **7190**. Run servi **q_v20**
(base locale, 433 229 parcelles ; table `parcel_scenario_v2_runs` peuplée, keep/rebuild = 433 229).

Références : les maquettes `7-analyse-labuse.png` → `7b-analyse-etapes.png` → `7c-analyse-cartes.png`
(nov-2026), l'endpoint `GET /analyse/scenarios` (ALGO-FIX-1), la DA et les règles de focus (RETOURS-21).

---

## 0. Recette 2 (maquette 7c-analyse-cartes) — 7 points

1. **Phrase « Classées par bande… » retirée** (étape Choisir).
2. **Étape Choisir** : les 4 bandes en lignes à cocher, puis une ligne repliable **« Autres parcelles ·
   N ▸ »** regroupant À vérifier / À différer / Aucun ajout / Hors projet ; **les lignes à 0 sont
   masquées** (« Calcul à compléter 0 » n'apparaît plus).
3. Le résumé replié devient un bouton **« Modifier la recherche »** ; au-dessus de la liste, une ligne
   **« N parcelles · objectif · scénario »**.
4. **Bug carte** : le bandeau « trop large » comptait **toute la sélection** ; il compte désormais la
   **liste choisie** (`n_filtre`) et n'apparaît que si elle dépasse 20 000. **La carte peint EXACTEMENT
   la liste choisie** : l'endpoint renvoie les IDU des cohortes cochées (`carte=1`, ≤ 20 000), le
   panneau les pose dans `scenarioPaint`, et `MapView` les peint (ils priment sur le raccord /filtre).
   Vérifié WebKit : Saint-Denis + U, Excellente + Bonne → **2 569 IDU peints exactement**.
5. **Plus de détail à déplier** : la carte de résultat montre le **chiffre principal EN GROS** (gain
   vert, perte orange ; « net » en reconstruction) et, à droite en petit, **« capacité − existant »** ;
   une ligne de raison + une flèche ; **toute la carte ouvre la fiche parcelle** (bordure verte au
   survol). Plus de page séparée, plus de « Voir le détail ». Vérifié : clic → fiche DO0049 ouverte.
6. **Puce Signal renommée « Vente : faible / moyenne / forte »** partout (`NIVEAU_META` + `venteLabel`).
7. **Investigation (rapport, aucune correction)** : `INVESTIGATION-FONCIER-PUBLIC.md`. **97411000DO0049**
   (3 Allée des Étudiants) = **campus de lycées de la Région Réunion**, classé « Excellente, +112 339 m² ».
   Sur l'île, parmi les **49 980** parcelles Excellente + Bonne : **3 012** (6,0 %) sont du **foncier
   public** (Commune 2 385 · EP 255 · État 248 · Dépt 118 · Région 6), **3 705** (7,4 %) portent un
   équipement BPE (dont 43 lycée/collège/université, 53 hôpital) ; union public/équipement d'enseignement
   ou santé = **3 066**. Décision de règle (exclure / badge « foncier public ») laissée à Vic.

---

## 1. Placement + flux à DEUX ÉTAPES (recette Vic, maquette 7b-analyse-etapes.png)

Pas de vue plein écran séparée. Le parcours est : **Filtres (inchangé) → « Analyser avec LABUSE » → ce
panneau**, dans la colonne de gauche, à la place de l'ancien bloc Score / Signal / Classer par (retiré).
La carte **reste visible à droite** et peint les parcelles de la liste (mécanisme existant, même règle
au-delà de 20 000). Dans `LeftPanel`, `verdict && filters.analyseLabuse ? <AnalyseScenario/> :
VerdictHero + ResultsSection`.

**Deux étapes** (nouvelle maquette) :
- **Étape « Choisir »** : objectif (**Prospection** / **Potentiel** — libellés courts), scénario (Bâti
  conservé / Reconstruction), la phrase qui classe, puis la **liste des bandes et statuts à COCHER**
  (cases multiples, chacune son effectif servi, **Excellente + Bonne cochées par défaut**), au-dessus
  la **barre de répartition**. Un seul bouton : **« Voir les N parcelles → »** (N = somme des cochées,
  dérivée des effectifs, immédiate).
- **Étape « La liste »** : prend tout le panneau ; les choix se replient en **une ligne de résumé**
  (« Potentiel · Bâti conservé · Excellente, Bonne · N parcelles ») + **« Modifier ▾ »** qui rouvre
  l'étape « Choisir ». Cartes de résultat (bande · Signal, à-cheval « sur la portion U (X m²) »,
  reconstruction « Projet · existant · gain net signé » orange si négatif, carte entière → détail).

**En-tête sur UNE ligne** : « Analyse LABUSE » + **« i »** (Comprendre) + « ← Retour » (aucun bouton sur
deux lignes). **Détail** (overlay) : deux gros chiffres, gain net, « Ce qui explique » (points ×
facteurs = score → bande), « À vérifier avant d'aller plus loin ».

**Plus d'écran de chargement à « 0 parcelle »** : les effectifs arrivent avec l'étape « Choisir » (requête
`limit=0`, cachée) ; changer d'objectif ou de scénario **garde l'affichage précédent** le temps de la
mise à jour (`placeholderData=prev` + indicateur « mise à jour… »).

**Supprimés** : la vue plein écran `analyse` + l'entrée du rail + le deep-link `#analyse=1` + `View 'analyse'`.

### Fichiers front
- **Ajoutés** : `src/components/analyse/AnalyseScenario.tsx` (l'écran, dans le panneau), `src/lib/
  scenario.ts` (vocabulaire + ordonnancement, les libellés du mandat), `src/lib/__tests__/scenario.
  test.ts` (12), `qa/ecrans_nov_2_webkit.mjs` (parcours WebKit).
- **Modifiés** : `src/components/panel/LeftPanel.tsx` (le panneau analyse remplace le bloc Score/
  Signal/Classer par), `src/lib/api.ts` (`getAnalyseScenarios(f, opts)` = jeu de filtres complet +
  `getAnalyseScenarioDetail`), `vite.config.ts` (proxy `/analyse/scenarios`). **Revenus en arrière**
  (vue plein écran retirée) : `src/App.tsx`, `src/components/Rail.tsx`, `src/store/useApp.ts`.

---

## 2. API — `/analyse/scenarios` accepte le JEU DE FILTRES COMPLET

L'endpoint prend désormais `FiltreCriteres` (comme `/filtre`), **pas seulement commune/IDU** : la
sélection est EXACTEMENT celle de l'analyse actuelle. `_scenario_selection_sql` réutilise la
résolution d'IDU de la liste carte (`/filtre?idus=1`) — même masque des slivers < 2 m², mêmes filtres
`_q_v2_where` — **sans plafond** (les effectifs portent sur TOUTE la sélection) et **sans** les
filtres Analyse bande/Signal de l'ancien écran (les puces V2 sont appliquées en aval). On **n'exclut
pas** l'étage 0 : l'analyse COMPTE toutes les parcelles filtrées (les exclues dures = « Hors projet »),
comme le compteur `/filtre`.

`effectifs_filtre` calcule les effectifs **en UNE SEULE passe** (la sélection n'est résolue qu'une
fois : à l'échelle île c'était 5 passes ≈ **10 s**, désormais **~2,8 s**, et **~0,3 s** une fois
**cachés 30 s** au robinet par `(filtre × mode × scénario)`). `analyse_payload_filtre` dérive
`n_selection` et le **N des cohortes cochées** (`n_filtre`) DES effectifs — aucune requête de count — ;
la **page** (cohortes cochées, OR) est une seule requête triée (groupe → bande → quantité → IDU, ou
Signal décroissant). `limit=0` = effectifs seuls (l'étape « Choisir »). Vérifié : **n_selection =
compteur `/filtre`** à l'identique (Entre-Deux 6 336 ; Saint-Denis + zonage U 34 499).

**Cases à cocher multiples** : paramètres `bands` / `statuts` (potentiel) et `niveaux` (prospection),
CSV ; union (OR) sur la LISTE, jamais sur les effectifs. Rien de coché = liste vide.

### Bug (4) corrigé — le scénario change les effectifs

Vic : en Reconstruction, les effectifs affichés étaient ceux du Bâti conservé (« Aucun ajout 64 880 »,
« Calcul à compléter 0 »). **Cause** : côté FRONT, la bascule de scénario montrait les effectifs
précédents (`placeholderData`) pendant une requête île **de ~10 s** — perçue comme figée. **Fix** :
effectifs en une passe + cache → la bascule se met à jour en ~0,3 s (et garde l'affichage précédent le
temps du calcul, comme demandé). L'API, elle, distinguait déjà : **conservation** NO_MARGIN 64 880 /
COMPUTE_PENDING 0 ; **reconstruction** NO_MARGIN 0 / COMPUTE_PENDING 211 759. Garde-fou :
`test_le_scenario_change_les_effectifs` (keep≠rebuild) + vérif WebKit (keep Aucun ajout 12 349 /
Calcul 0 ; rebuild 0 / 20 651 sur Saint-Denis + U).

Recette d'Astra conservée (1ʳᵉ passe) : codes **AU phasés** 1AU/2AU reconnus ; `effectifs.par_signal`
de prospection ; échec d'enrichissement remonté (`enrichissement` + `etat_calcul`) ; adresse BAN
factuelle servie pour la page.

### Fichiers back
- **Modifiés** : `src/labuse/api/app.py` (`_scenario_selection_sql` + endpoint sur `FiltreCriteres`),
  `src/labuse/scoring/scenarios_v2_persist.py` (`analyse_payload_filtre` + helpers SQL `_order_by_
  potential`/`_chip_where`/`_versions_run`, row-mapping partagé), `scenarios_v2_build.py` (AU phasée,
  `adresses_pour`, `etat_calcul`, `enrichissement`), `scenarios_v2.py` (`enrich_state` dans `details`).
- **Ajouté** : `tests/test_ecrans_nov_2_api.py` (23 : AU phasée, helpers de puce/tri, et contrôles DB
  — effectifs font le total, puce narrowe la liste pas les effectifs, par_signal, enrichissement).

---

## 3. Vérifications (hook + WebKit, parcours complet)

- **Front** : `tsc -b` **0 erreur** · **vitest 323** · `vite build` OK · secrets « rien ».
- **Back** : `pytest -m "not db and not local and not reel and not network"` → **3200 passed** ;
  `test_ecrans_nov_2_api` (helpers cohortes/tri + DB : effectifs font le total, cohortes narrowent la
  liste, **le scénario change les effectifs**) + `test_algofix1_*` + `test_proxy_dev_couvre_routes_api`
  **verts** (base q_v20) ; `test_aucun_fichier_du_signal_modifie` vert (Signal intact).
- **WebKit (Safari, playwright 1.49.1 / webkit-2104, `reducedMotion`)** — PARCOURS COMPLET À 2 ÉTAPES
  (`qa/ecrans_nov_2_webkit.mjs`) : filtres **Saint-Denis + zonage U** → **« Analyser »** → étape
  **« Choisir »** (Excellente + Bonne cochées, « Voir les 2 569 parcelles ») → **changement de scénario
  → les effectifs changent** (keep : Aucun ajout 12 349 / Calcul 0 ; rebuild : 0 / 20 651 — bug 4
  corrigé, mesuré) → **changement d'objectif** (Prospection) → cocher « À étudier » → **« Voir les N
  parcelles »** → étape **« La liste »** → **clic sur une carte** → **détail** → **« Modifier ▾ »** (rouvre
  Choisir) → **Retour** (`analyseLabuse=false` mesuré). **Focus APRÈS CLIC** (cocher une ligne) :
  `data-input=mouse`, `activeElement=BODY`, `aContour=false` — aucun contour. Captures
  `frontend/captures/ecrans-nov-2/webkit-01…06.png`.

---

## 4. Décision carte (inchangée, par réutilisation)

La carte **reste la carte existante**, à droite du panneau : elle peint la sélection filtrée par
bande via `getFiltreIdus(f, bande)` + plafond serveur 20 000 + toast « meilleures bandes » (RETOURS-21,
inchangé). Le panneau d'analyse lit la MÊME sélection (le jeu de filtres global) → carte et effectifs
sont cohérents. Croisement île (keep/ESTIMATED band B) = **43 122 ≈ 43 000**.

---

## 5. Limites honnêtes

- Reconstruction chiffrée persistée seulement à Entre-Deux + Saint-Denis (ailleurs « Calcul à
  compléter ») ; le **détail** force `enrich=1` par parcelle (≤ 500) pour chiffrer à la demande.
- Le **type de bien** (« bâti » / « terrain nu ») est dérivé de l'existant E (E>0 vs E=0) — factuel,
  pas inventé ; l'endpoint ne sert pas « maison / immeuble ».
- Les effectifs incluent les exclues dures en « Hors projet » (comme le compteur `/filtre`) ; la carte,
  elle, ne peint que les bandes (une exclue dure n'est pas une bande).

---

*Fin du compte rendu. Branche `feat/ecrans-nov-2`, non mergée, run servi intact, Signal intact.*
