# CARTO_FRONT — Cartographie du frontend LABUSE

> Document factuel, lecture seule. Généré par sweep du répertoire `frontend/`.
> Périmètre : `frontend/src/**`, config Vite/Tailwind, scripts QA Playwright (`qa/*.mjs` + `frontend/qa/*.mjs`).

---

## 1. Intro — stack et service

**Stack.** React 18 (`react` / `react-dom` `^18.3.1`) + TypeScript (`typescript ^5.6.3`) + Vite (`vite ^5.4.9`, plugin `@vitejs/plugin-react`). Rendu carte : MapLibre GL (`maplibre-gl ^4.7.1`). Données serveur : `@tanstack/react-query ^5.59.0` (client `QueryClient` unique, `staleTime` 60 s, `refetchOnWindowFocus: false`, retry désactivé sur 429). État global : Zustand (`zustand ^5.0.0`, store unique `useApp`). Styles : Tailwind (`tailwindcss ^3.4.14`, design system dérivé de `docs/design/mockups/`, cf. `frontend/DERIVATIONS.md`), PostCSS + autoprefixer.

**Chaîne de service.** `npm run build` = `tsc -b && vite build` → sortie `frontend/dist/`. Vite est configuré avec `base: '/socle/'` (`vite.config.ts`) : en production, FastAPI (`app.py`) sert `dist/` sous le préfixe `/socle`. En dev, `vite` sert à la racine (port 5173) et proxifie l'API FastAPI (`http://127.0.0.1:8000`) pour les chemins `/map`, `/parcels`, `/stats`, `/sources`, `/filters`, `/discover`, `/health`, `/coverage`, `/assemblage`, `/compare`, `/mutation`, `/communes`. Chunks manuels : `maplibre` (maplibre-gl) et `vendor` (react, react-dom, react-query, zustand).

**Le hook `window.__labuse`.** Trois hooks globaux exposés à `window` à des fins d'auto-QA (aucun effet produit) :
- `window.__labuse` (`App.tsx:238`) = `{ select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict, setMsel }` — pilotage direct du store depuis Playwright.
- `window.__labuse_tm` (`TimeMachine.tsx:72`) = `{ past, now }` — synchro de la machine à remonter le temps.
- `window.__labuse_map` (`MapView.tsx:440`) = l'instance MapLibre — ping sémantique de la carte.

**Point d'entrée** (`main.tsx`) : `ReactDOM.createRoot` → `<StrictMode>` → `<ErrorBoundary>` → `<QueryClientProvider>` → `<App />`. Import de `./styles/index.css`.

---

## 2. Arborescence commentée

42 fichiers `.ts`/`.tsx` dans `frontend/src`, ~10 310 lignes au total. `wc -l` entre parenthèses.

### Racine `src/`
| Fichier | Lignes | Rôle |
|---|---|---|
| `main.tsx` | 29 | Point d'entrée : montage React, `QueryClient`, `ErrorBoundary`. |
| `App.tsx` | 302 | Voir détail ci-dessous. |

**`App.tsx` (302 l.).** Racine de l'app. Contient 3 composants locaux : `IaRestitution` (carte flottante de restitution du copilote — compteur animé rAF, top cliquables, « pourquoi » par parcelle, boutons Enregistrer projet / PDF / Ouvrir kanban / M22, bannières `stub` / `criteres_non_appliques` / relance 0-résultat), `Toast` (message auto-éteint 4 s), et `App` (default export). `App` : lit/écrit les filtres + zone + commune + module + verdict + page dans le hash URL (`#f=…&c=…&v=1&m=…&pg=vues`, `replaceState`), installe le hook `window.__labuse`, et route l'affichage selon `view` : `cartes` (LeftPanel/ModulePanel/ParcoursTinder + MapView/TimeMachine), `crm` (Kanban), `sources` (SourcesPage), `segments` (SegmentsPage), `projets` (ProjetsPanel), `ia` (IAStub) ; superpose Fiche, ContextePanel, SourceDrawer, Toast, IaRestitution.

### `src/store/`
| Fichier | Lignes | Rôle |
|---|---|---|
| `useApp.ts` | 258 | Store Zustand unique. Détaillé §3. Exporte `useApp`, `EMPTY_FILTERS`, types `View`, `LayerToggles`, `Filters`, `ProjetBrouillon`, `IaTop`, `IaRestitution`, `Basemap`, `OrthoYear`, `MapTool`. |

### `src/lib/`
| Fichier | Lignes | Rôle / exports |
|---|---|---|
| `api.ts` | 429 | Toutes les fonctions d'appel HTTP (fetch). Détaillé §4. Constante `SOURCE = 'q_v6_m8'`, classe `ApiError`, helper `is429`. |
| `types.ts` | 233 | Types de données partagés (`Fiche`, `FicheLine`, `ParcelResult`, `Statut`, `VBand`, `PipelineEntry`, `PipelineMeta`, `SourceInfo`, `Stats`, …). |
| `filters.ts` | 179 | Modèle des filtres carte/liste : `ParcelProps`, `FLAG_DEFS`, `V_SIGNAL_DEFS`, `vSignalCodes`, `matchScope`/`matchAll`/`hasScopeFilters` (filtrage client), `activeChips`/`removeToken` (chips), `filtersToHash`/`filtersFromHash` (URL). |
| `status.ts` | 116 | Source de vérité des couleurs/labels de verdict : `STATUT_META`, `TIER_V2_META`, `verdictMeta`, `effectiveTier`, `statutColor`, `completudeColor`, `V_BAND_META`, `ZONE_FAM_META`, `SCORE_TIP` (tooltips Q/A/V), `ageSignal` (fraîcheur CRED-4). |
| `useApplySearch.ts` | 105 | Hook `useApplySearch` : chorégraphie partagée (copilote + rejouer projet) périmètre→filtres→verdict→vol caméra→restitution (chiffres serveur). Helper `filtresToFilters`. |
| `geo.ts` | 62 | Géométrie légère sans turf : `haversine`, `pathLength`, `polygonArea` (shoelace), `pointInPolygon` (ray casting), `roughCentroid`, `fmtDistance`, `fmtArea`. |

### `src/components/` — racine
| Fichier | Lignes | Composant(s) exportés · props |
|---|---|---|
| `ErrorBoundary.tsx` | 37 | `ErrorBoundary` (classe, props `{children}`) — filet global, jamais d'écran noir. |
| `Loading.tsx` | 27 | `Loading({label, className, big, accent})`, `Skeleton({className})`. |
| `Rail.tsx` | 188 | `Rail()` — barre latérale de navigation (vues + cartes d'outils). Composant local `OutilCard`. |

### `components/contexte/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `ContextePanel.tsx` | 203 | `ContextePanel()` — volet contexte commune (SRU / ANRU / QPV / PLH / marché). |

### `components/crm/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `Kanban.tsx` | 186 | `Kanban()` — pipeline CRM (kanban, drag-and-drop). Composant local `Card({e, onDragStart, newEvents})`. |

### `components/fiche/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `Fiche.tsx` | 1277 | `Fiche({idu})` — fiche parcelle complète (le plus long du front). |
| `AskBar.tsx` | 181 | `AskBar({idu})` — barre question libre sourcée (M11 Surface A). Exporte `renderRich`. Local `ProvChip`. |
| `ScoreV2Block.tsx` | 132 | `ScoreV2Block({idu})` — bloc « pourquoi ce score » v2. |
| `GestionnairesBlock.tsx` | 63 | `GestionnairesBlock({g: Gestionnaires})`. Locaux `Conf`, `Row`. |
| `SourceDrawer.tsx` | 90 | `SourceDrawer()` — tiroir source ouvert depuis une ligne de fiche. Local `Row`. |
| `ViabilisationBlock.tsx` | 73 | `ViabilisationBlock({via: Viabilisation})`. |
| `PermitsProximityBlock.tsx` | 45 | `PermitsProximityBlock({idu})`. |

### `components/header/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `Header.tsx` | 372 | `Header()` — barre du haut : recherche, sélecteur commune, filtres. Locaux `NumField`, `CheckRow`. |

### `components/ia/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `IAStub.tsx` | 230 | `IAStub()` — vue copilote IA (recherche langage naturel). |

### `components/map/`
| Fichier | Lignes | Composant / export · props |
|---|---|---|
| `MapView.tsx` | 886 | `MapView()` — carte MapLibre (2e plus long). Expose `window.__labuse_map`. |
| `MapToolbar.tsx` | 147 | `MapToolbar()` — outils carte (fond de plan, mesure, 3D). |
| `Legend.tsx` | 67 | `Legend({inline})`, hook `useV2Actif()`. |
| `basemaps.ts` | 35 | `WMTS`, `BASEMAP_SOURCES`, `BASEMAP_CHOICES`, `basemapLabel`, type `BasemapDef`. |

### `components/outils/`
| Fichier | Lignes | Composant / export · props |
|---|---|---|
| `ModulePanel.tsx` | 805 | `ModulePanel()` (panneau des modules outils), `PermitDrawer({permitId, onClose})`. Locaux `Banner`, `Row`, `V`, `F`. |
| `moteurs.tsx` | 401 | Moteurs Vague 4 : `M15`, `M16`, `M17`, `M18`, `M19`. Locaux `Banner`, `SrcTag`, `IndicateurCommune`. |
| `TimeMachine.tsx` | 159 | `TimeMachine({center})` — machine à remonter le temps (ortho historique). Expose `window.__labuse_tm`. |
| `M22Programme.tsx` | 129 | `M22()` — formulaire programme/capacité (préremplissable copilote). |
| `ScoringV2.tsx` | 91 | `ScoringV2Module()`. |
| `registry.ts` | 72 | Registre des outils : `VIOLET`, `VIOLET_DIM`, type `OutilGroup` (`detecter`/`analyser`/`agir`), `ModuleDef`, `GROUPS`, `MODULES` (16 modules : programme, division, fantome, patrimoine, bailleur, matching, assemblage, barometre, permis, promesses, velocite, simulplu, zan, temps, duediligence, courriers). |
| `TierBadge.tsx` | 25 | `TierBadge({tier, etage0, statut})`. |

### `components/panel/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `ResultsSection.tsx` | 433 | `ResultsSection()` — liste des résultats. Locaux `CompletudeRing`, `ResultCard`, `TierChips`, `EntonnoirLine`. |
| `LeftPanel.tsx` | 178 | `LeftPanel()` — panneau gauche (couches + résultats) en vue cartes. |

### `components/projets/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `ParcoursTinder.tsx` | 294 | `ParcoursTinder()` — parcours de sélection type Tinder. Locaux `DecisionCard`, `SectionsDrawer`, `Row`. |
| `ProjetKanban.tsx` | 282 | `ProjetKanban({pid, nom})` — kanban 3 colonnes du projet. Locaux `ProprioLine`, `KanbanCard`. |
| `ProjetEntretien.tsx` | 238 | `ProjetEntretien({initial, onClose})` — entretien de cadrage copilote-projet. Local `RepereBadge`. |
| `ProjetsPanel.tsx` | 168 | `ProjetsPanel()` — liste « Mes projets » + ouverture. Local `ProjetCard`. |

### `components/segments/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `SegmentsPage.tsx` | 742 | `SegmentsPage()` — moteur de segments Habitat / Vues (presets, filtres, exports, publipostage). |

### `components/sources/`
| Fichier | Lignes | Composant · props |
|---|---|---|
| `SourcesPage.tsx` | 341 | `SourcesPage()` — page catalogue des sources de données. |

---

## 3. Store global `store/useApp.ts`

Store Zustand unique (`create<AppState>`), pas de persistance. Groupes d'état et actions clés :

- **Navigation / vue.** `view: 'ia'|'cartes'|'crm'|'sources'|'projets'|'segments'` ; `setView` applique une **navigation exclusive** — change la vue ET remet à null fiche/module/contexte/drawer/restitution/parcours/openProjet + ferme le tiroir outils. `outilsOpen` + `toggleOutils` (bascule sur le fond carte). `openSources(focus)`.
- **Commune / contexte.** `commune` (null = « Toute l'île »), `setCommune` (remet `zone` à null). `contexteCommune` + `setContexteCommune` (volet SRU/ANRU/PLH/marché).
- **Parcelle & fiche.** `selectedIdu` + `select(idu)`. `sourceLine` + `openSourceDrawer`/`closeSourceDrawer`.
- **Filtres.** `filters: Filters` (14 champs : `tiers` v2, `scoreMin`, `surfaceMin/Max`, `sdpMin`, `evenement`, `vueMer`, `veille`, `horsCopro`, `flags`, `flagsExclus`, `communes`, `vSignals`, `personneMorale`, `zonagePlu`) ; `setFilter`/`setFilters`/`resetFilters` ; `EMPTY_FILTERS`. `query`/`setQuery`. `verdict`/`setVerdict` (le tri est un geste : carte neutre → analyse allumée, URL `v=1`).
- **Copilote / restitution.** `iaRestitution` + `setIaRestitution` (compteur + top + pourquoi + projet). `projetBrouillon` + `setProjetBrouillon`.
- **Projets & parcours.** `openProjet` (kanban) + `setOpenProjet` (bascule view=projets, nettoyage exclusif). `parcours` (Tinder) + `setParcours` + `openParcours` (préserve `openProjet`).
- **Carte.** `layers: LayerToggles` (12 couches : zonage, zonage_parcelle, parcelles, ppr, vue_mer, parc, limites, anru, equipements, communes, cinquante_pas) + `toggleLayer`. `basemap` (`dark`/`plan`/`ortho`) + `setBasemap`. `orthoYear` (`now`/`2000`/`1950`) + `setOrthoYear`. `terrain3d` + `toggleTerrain`. `tool` (`distance`/`surface`/`alti`/`zone`) + `setTool`. `zone` (polygone dessiné = filtre) + `setZone`. `flyTo` + `setFlyTo`. `panelOpen` + `togglePanel`.
- **Modules outils.** `module` + `setModule` (bascule view=cartes, réinit moduleMap/moduleFiche). `moduleMap` (idus surlignés + géométries) + `setModuleMap`. `moduleFiche` (bloc module en tête de fiche) + `setModuleFiche`. `msel` (multi-sélection M16 assemblage) + `setMsel`. `m22Prefill`/`setM22Prefill`, `m02Prefill`/`setM02Prefill` (SIREN patrimoine). `calculette` (charge foncière) + `setCalculette`.
- **UX.** `toast` + `setToast`. `sourcesFocus`.

---

## 4. `lib/api.ts` — groupes de fonctions d'appel

Constante `SOURCE = 'q_v6_m8'` (run de référence), `commune()` (lit le store), classe `ApiError` (porte le statut HTTP), `is429`, helper interne `j<T>` (fetch typé), `q()`/`filterParams()` (construction query params). Groupes :

- **Communes / stats.** `getCommunes`, `getContexteCommune`, `getEntonnoir`, `getStats`, `parcelAt`.
- **Recherche & liste parcelles.** `searchParcels`, `getResults`, `getFiche`, `csvExportUrl`, `getParcelsGeojson`, `getMapLayer`, `getTilesMeta`, `pdfUrl` (avec paramètres calculette).
- **Pipeline / CRM.** `getPipelineMeta`, `getPipeline`, `getPipelineForParcel`, `addToPipeline`, `patchPipeline`, `deletePipeline`. `postSignalement` (QA humaine M9).
- **Sources.** `getSources`.
- **Modules outils (Vague 1).** `modDivision`, `modPatrimoineSearch`, `modPatrimoine`, `modPermis`, `modPermisFiche`, `modParcellePermis`, `modPromesses`, `modVelocite`, `modBailleur`, `modFantome`. Habitat solaire : `getSolaireFiche`, `modSolaireParkings`, `modSolaireTertiaire`, `getOrthoEquipements`. Courriers : `modCourriers`, `courrierDemande`. `modDueDiligence`.
- **Copilote IA (Vague 2).** `iaStatus`, `iaSearch`, `iaSynthese`, `iaPourquoi`, `askParcel` (M11 Surface A, sourcé).
- **Événements (Vague 3).** `getEvents`, `getEventsCount`, `markEventRead`, `markAllEventsRead`, `getWatch`, `toggleWatch`, `getSavedSearches`, `saveSearch`, `deleteSearch`.
- **Moteurs (Vague 4).** `motSimulPluZones`, `motSimulPlu`, `motAssemblage`, `motZan`, `zanParcelle`, `motBarometre`.
- **Matching / partage (Vague 5).** `getProfiles`, `addProfile`, `runMatch`, `matchCompatibilite`, `promoteursActifs`, `createShare`, `listShares`.
- **Faisabilité / bilan (M22).** `getFaisabilite`, `faisabiliteExplain` (M11 Surface C), `postChargeFonciere`, `postProgramme`.
- **Projets (copilote-projet).** `iaEntretien`, `getReperes`, `getProjets`, `getProjet`, `deriveProjet`, `createProjet`, `getApercu`, `projetPdfUrl`, `patchProjet`, `rejouerProjet`, `deleteProjet`.
- **Parcours Tinder.** `proposerProjet`, `getParcoursEtat`, `getCarteDecision`, `setStatutParcelle`, `chercherPlus`, `ajouterParcelle`.
- **Segments Habitat.** `getSegments`, `querySegment`, `exportSegmentCsv`, `exportPublipostage` (téléchargement blob), `getGabarits`, `createSegmentPreset`, `updateSegmentPreset`, `deleteSegmentPreset`, `refreshSegmentCounts`, `nlSegmentsSearch`.

---

## 5. Scripts QA Playwright (`.mjs`)

**Nombre.** 89 fichiers `.mjs` au total : 78 sous `frontend/qa/`, 11 sous `qa/` (racine).

**Rôle global.** Scripts Playwright autonomes (Node ESM), pas de test-runner : chacun lance un navigateur, pilote l'app servie et vérifie/capture des parcours. Ils s'appuient sur les hooks `window.__labuse*` pour piloter le store directement. La grande majorité vise `http://127.0.0.1:8010/socle/` (83 occurrences) ; quelques scripts ciblent d'autres ports (8011×5, 8020×2, 8000×2, 8021, 8023 — instances de test parallèles). Playwright déclaré en `devDependencies` (`playwright ^1.61.1`) ; aucun script npm dédié (pas de `test` dans `package.json`) — lancés à la main via `node <fichier>.mjs`.

**Familles (préfixe de nom).** `qa_*` (24), `audit_*` (12, ex. `audit_m6_boutons`, `audit_m6_fiche`, `audit_couches_m51`), `fix_*` (8, ex. `fix_ia_fiche`, `fix_lot1_captures`), `health_*` (5, ex. `health_journeys`, `health_saintpaul`, `health_voletA/B`), `nuit_*` (4, batch de nuit), `m6_*` (4), `m11_*` (4), `e2e_*` (11, sous `qa/` : `e2e_m9_fiche`, `e2e_m10`, `e2e_habitat_solaire`, `e2e_anc_vegetation`, `e2e_wave_ortho`, `e2e_429`…), `projet_*` (3), `perf_*` (2), `inspect_*` (2), `finitions_*` (2), plus isolés `zan_*`, `swipe_*`, `score_*`, `matching_*`, `m61_ui`, `capture_*`, `assemblage_plus`, `pack_*`.

**Exemples représentatifs.** `qa/e2e_m9_fiche.mjs`, `qa/e2e_habitat_solaire.mjs`, `frontend/qa/health_journeys.mjs`, `frontend/qa/audit_m6_fiche.mjs`, `frontend/qa/fix_ia_fiche.mjs`, `frontend/qa/swipe_*` (parcours Tinder).

---

## 6. Métriques

**Top fichiers longs (`.tsx`/`.ts`).**
1. `components/fiche/Fiche.tsx` — 1277
2. `components/map/MapView.tsx` — 886
3. `components/outils/ModulePanel.tsx` — 805
4. `components/segments/SegmentsPage.tsx` — 742
5. `components/panel/ResultsSection.tsx` — 433
6. `lib/api.ts` — 429
7. `components/outils/moteurs.tsx` — 401
8. `components/header/Header.tsx` — 372
9. `components/sources/SourcesPage.tsx` — 341
10. `App.tsx` — 302

**TODO / FIXME / HACK / XXX.** Aucune occurrence de ces marqueurs dans `frontend/src` (`grep -rnE 'TODO|FIXME|HACK|XXX'` → 0 résultat). Les annotations de dette/incidents sont rédigées en commentaires prose (ex. « A1 (post-revue) », « clamp bas » dans `App.tsx`) sans balise conventionnelle.

**Composants apparemment jamais importés.** Aucun. Après vérification par grep du nom de base de chaque fichier dans le reste de `src`, tous les fichiers `.ts`/`.tsx` sont référencés au moins une fois ailleurs. (Un premier passage avait produit des faux positifs dus à une erreur de glob zsh, corrigé ensuite.)

---

## 7. Histoire

- Dernier commit touchant `frontend/src` : **2026-07-20 14:40:35 +0200**.
- Nombre de commits touchant `frontend/src` : **146** (`git log --oneline -- frontend/src`).

---

## 8. Observations factuelles

- Un **seul store Zustand** (`useApp`) centralise tout l'état ; pas de Context React applicatif hormis `QueryClientProvider` et `ErrorBoundary`.
- `App.tsx` héberge trois composants (`IaRestitution`, `Toast`, `App`) plutôt qu'un fichier par composant.
- **Navigation exclusive** : `setView`, `setModule`, `openProjet`, `toggleOutils`, `openSources`, `openParcours` réinitialisent systématiquement fiche/module/contexte/drawer/restitution — un seul panneau/vue actif à la fois.
- L'**URL est la source de partage** : filtres + zone + commune + module + verdict + page sérialisés dans le hash (`filtersToHash`/`filtersFromHash`) ; alias legacy géré (`pg=segments` → `pg=vues`, anciens `st=` ignorés).
- Les **couleurs/labels de verdict** ont une source de vérité unique (`lib/status.ts`) ; commentaires renvoient à `frontend/DERIVATIONS.md` et `docs/design/mockups/`.
- Le run de données servi est **codé en dur** dans `api.ts` : `SOURCE = 'q_v6_m8'` (aligné sur `Q_A_RUN_LABEL` côté backend, « JAMAIS parcel_evaluations »).
- **Aucun turf** : la géométrie (`geo.ts`) est réimplémentée à la main (haversine, shoelace, ray casting) — justifié par l'échelle communale.
- Gestion **429 spécifique** : `ApiError` porte le statut, retry désactivé sur 429 dans `main.tsx`, message dédié côté UI.
- Trois **hooks `window.__labuse*`** exposés pour la QA Playwright (aucun effet produit annoncé).
- **89 scripts QA `.mjs`** sont des scripts autonomes (pas de runner), lancés manuellement, majoritairement contre `127.0.0.1:8010/socle/`.
- **Privacy** présente dans les types (`ProprietairePublic` : personne morale nommée / particulier masqué) — porté jusqu'au front (parcours, kanban projet).
- Le module `registry.ts` déclare **16 modules outils** répartis en 3 groupes (`detecter`/`analyser`/`agir`).
