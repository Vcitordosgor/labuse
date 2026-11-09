# ECRANS-NOV-2 — compte rendu

**Mandat** ECRANS-NOV-2 — l'écran **Analyse LABUSE par scénario**, **DANS le panneau de gauche**
(342 px, à côté de la carte), à la place de l'ancien bloc Score / Signal / Classer par.
**Branche** `feat/ecrans-nov-2` (worktree `~/Desktop/labuse-ecrans2`). **Aucun merge, aucun accès
production.** Front + API (lecture seule). Ports : front **9990**, back **7190**. Run servi **q_v20**
(base locale, 433 229 parcelles ; table `parcel_scenario_v2_runs` peuplée, keep/rebuild = 433 229).

Références : la maquette `docs/design/maquettes/nov-2026/7-analyse-labuse.png`, l'endpoint
`GET /analyse/scenarios` (ALGO-FIX-1), la DA et les règles de focus/sélection uniques (RETOURS-21).

---

## 1. Placement — l'écran EST le mode analyse du panneau de gauche

Pas de vue plein écran séparée. Le parcours est : **Filtres → « Analyser avec LABUSE » → ce panneau**,
à la place de l'ancien bloc Score / Signal / Classer par (retiré). La carte **reste visible à droite**
et peint les parcelles de la liste (mécanisme existant, même règle au-delà de 20 000). **« ← Retour »**
revient aux filtres (`store.retourFiltres`).

Intégration : dans `LeftPanel`, quand l'analyse est allumée (`verdict && filters.analyseLabuse`), le
corps du panneau devient `<AnalyseScenario />` au lieu de `VerdictHero + ResultsSection` ; le **tri
factuel** (analyse éteinte) garde l'ancien rendu. La bascule « Analyser avec LABUSE » (`voirParcelles →
setAnalyse(true)`) et le retour (`retourFiltres → analyseLabuse=false`) sont inchangés.

L'écran : en-tête « Analyse LABUSE · N parcelles » + « ← Retour » + « Comprendre l'analyse » ; objectif
Prospection vente / Potentiel foncier ; en potentiel, scénario Bâti conservé / Reconstruction ; **la
phrase qui classe**, toujours ; **bloc de filtres repliable** en une ligne de résumé (« Potentiel
foncier · Bâti conservé · Toutes ▾ ») ; **barre de répartition** + **puces comptées** (effectifs de
l'API, ils font le total ; une puce narrowe la liste) ; **cartes de résultat** (bande · Signal — le
Signal principal en prospection ; à-cheval « sur la portion U (X m²) » ; reconstruction « Projet ·
existant · gain net signé », orange si négatif ; la carte entière ouvre le détail en potentiel) ;
**détail** (deux gros chiffres, gain net, « Ce qui explique » = points × facteurs = score → bande,
« À vérifier avant d'aller plus loin ») ; **au-delà de 20 000**, un message dit que la carte peint
les meilleures bandes (Excellente + Bonne).

**Supprimés** (replacement) : la vue plein écran `analyse` + l'entrée du rail + le deep-link
`#analyse=1` + la valeur `View 'analyse'` du store.

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

`analyse_payload_filtre` calcule **en SQL** (pas de lecture Python de toute la sélection) : effectifs
par statut / bande (potentiel) ou par niveau de Signal (prospection) sur toute la sélection ; et la
**page** triée (groupe → bande → quantité → IDU, ou Signal décroissant) et **narrowée par la puce**
(LIMIT/OFFSET). Vérifié : **n_selection = compteur `/filtre`** à l'identique (Entre-Deux 6 336 ;
Saint-Denis + zonage U ≈ 34,5 k). `n_filtre` (après puce) à côté de `n_selection`.

Recette d'Astra conservée (ECRANS-NOV-2, 1ʳᵉ passe) : codes **AU phasés** 1AU/2AU reconnus ;
`effectifs.par_signal` de prospection ; échec d'enrichissement remonté (`enrichissement` +
`etat_calcul`) ; adresse BAN factuelle servie pour la page.

### Fichiers back
- **Modifiés** : `src/labuse/api/app.py` (`_scenario_selection_sql` + endpoint sur `FiltreCriteres`),
  `src/labuse/scoring/scenarios_v2_persist.py` (`analyse_payload_filtre` + helpers SQL `_order_by_
  potential`/`_chip_where`/`_versions_run`, row-mapping partagé), `scenarios_v2_build.py` (AU phasée,
  `adresses_pour`, `etat_calcul`, `enrichissement`), `scenarios_v2.py` (`enrich_state` dans `details`).
- **Ajouté** : `tests/test_ecrans_nov_2_api.py` (23 : AU phasée, helpers de puce/tri, et contrôles DB
  — effectifs font le total, puce narrowe la liste pas les effectifs, par_signal, enrichissement).

---

## 3. Vérifications (hook + WebKit, parcours complet)

- **Front** : `tsc -b` **0 erreur** · **vitest 322** (310 + 12) · `vite build` OK · secrets « rien ».
- **Back** : `pytest -m "not db and not local and not reel and not network"` → **3200 passed** ;
  `test_ecrans_nov_2_api` + `test_algofix1_*` + `test_proxy_dev_couvre_routes_api` **verts** (base q_v20) ;
  `test_aucun_fichier_du_signal_modifie` vert (le Signal n'est pas touché).
- **WebKit (Safari, playwright 1.49.1 / webkit-2104, `reducedMotion`)** — PARCOURS COMPLET piloté
  (`qa/ecrans_nov_2_webkit.mjs`) : filtres **Saint-Denis + zonage U** → **« Analyser avec LABUSE »** →
  le panneau d'analyse apparaît (à côté de la carte) → **changement d'objectif** (Prospection) et de
  **scénario** (Reconstruction) → **clic sur une carte de résultat** → **détail** (deux chiffres,
  gain net, « Ce qui explique », « À vérifier ») → **Retour** (revient aux filtres,
  `analyseLabuse=false` mesuré). **Focus APRÈS CLIC** : clic sur une puce → `data-input=mouse`,
  `activeElement=BODY`, `aContour=false` — aucun contour, sélection vert opaque. Captures
  `frontend/captures/ecrans-nov-2/webkit-00…06.png`.

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
