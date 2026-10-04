# RECETTE-1 — retours de recette de Vic (4 oct.) — rapport

Branche `fix/recette-1` (base `origin/main` = `3e3a2afa`, après merge ORACLE-FIX-1) · worktree
`~/Desktop/labuse-recette1` · API 8695 / front 5895 · Opus · 1 session.

**Règle du run** : aucun run, aucune bascule. Toute valeur affichée qui change est consignée dans
`CHANGEMENTS.csv` avec la colonne **touche le run (oui/non)**. Le run q_v16 est un geste de Vic.

## État de départ (Étape 0)
- `pwd` = worktree · branche `fix/recette-1` · `git status` propre (hors `docs/.../RECETTE-1/`).
- base = `origin/main` du jour, contient le merge ORACLE-FIX-1 (`d5c90ea9`, `3e70a6b8`).
- `.env` copié depuis `~/Desktop/labuse/.env` ; base réelle île `labuse` (431 663 parcelles) pour
  les témoins/oracles ; base de test isolée pour pytest.
- **Python** : l'env conda `labusedb` n'a pas de binaire python ; on utilise `~/Desktop/labuse/.venv`
  avec `PYTHONPATH=src` (résout bien le code du worktree) + `PROJ_DATA` de l'env conda.
- **5 oracles (baseline)** : `50 vrai · 0 faux · 90 non vérifiable` (API 8695, le reste des
  témoins est non vérifiable quand l'API externe — Géorisques/IGN/BAN/RNB — ne répond pas). **0 faux
  = point de départ à préserver.** (⚠ la forme `LABUSE_ORACLE_API=:8695` donne une URL malformée ;
  utiliser l'URL complète `http://127.0.0.1:8695`.)
- **pytest faisabilité** (base réelle via `LABUSE_AUDIT_DATABASE_URL`) : 2 échecs PRÉ-EXISTANTS
  (`test_u1pru_stationnement_exempte_non_borne`, `test_plafond_densite_borne_les_zones_denses`) —
  confirmés rouges sur la base, avant toute modification (cf. CALCULS-FIX-1). Hors périmètre.
- **V6b** (banc de cohérence île, long) : à rejouer en fin de mandat (job nocturne).

---

## Lot A — ce qui peut toucher le run

### A1 · Faisabilité — verdict « terrain trop exigu » sur de grandes parcelles — ✅ FAIT
**Diagnostic (prouvé à la volée, 0 run).**
1. Le test « cercle inscrit » sur la géométrie ENTIÈRE de la parcelle est trompeur : la plupart des
   grandes parcelles `terrain_exigu` sont **à cheval** (zone dominante A/N + mince portion U/AU) ou
   couvertes par un **PPR zone rouge** / un **emplacement réservé**. L'assiette calculée est la
   portion U/AU clippée, pas la parcelle entière → le 0 m² est souvent **substantiellement correct**.
2. Mesure île (échantillon 400 parcelles `terrain_exigu` > 800 m², clip U/AU puis cercle inscrit de
   la portion) : 295 portion U/AU < 50 m² (légitime), 82 portion large (candidats « faux »), 23
   étroites (légitime).
3. Les 82 « candidats » examinés un par un : tous dissous — PPR INTERDICTION ~100 % (ex.
   `97415000BN1169`, U1b 19 047 m², 100 % PPR rouge), ER ~100 % (ex. `97401000AI0016`, Ud 5 345 m²,
   100 % « ER logements/mixité »), ou petites parcelles/slivers où les **reculs par côté du gabarit**
   (voie ~6 m + limites 3 m, bien plus qu'un inset uniforme de 3 m) vident légitimement l'assiette.
4. **La vraie cause (bug de Vic)** : le message « Terrain trop exigu compte tenu des reculs (4 m) »
   était affiché dès que l'emprise se vidait, **quelle que soit la raison** — y compris un PPR rouge
   ou un ER couvrant 19 000 m². Le chiffre (0 m²) est juste ; le **message** était faux.
   (Le bug de CAPACITÉ structurel — clip `name` vs `subtype` sur zones AU numérotées — avait déjà été
   corrigé par EXIGU-GRANDES ; c'est pourquoi le code courant donne des aires non nulles là où le run
   servi, antérieur, affiche encore `terrain_exigu`.)

**Correctif (run-safe).** `parcel_faisabilite` mesure désormais la **raison réelle** du vidage
(`extras['assiette_vide']`), passée au moteur. `estimate_capacity` choisit le message et pose
`Faisabilite.exigu_raison` ∈ {`reculs`, `ppr_rouge`, `emplacement_reserve`, `ebc`, `contraintes`,
`portion_reduite`}. Le `cause` reste `terrain_exigu` et la capacité reste 0 → **AUCUNE valeur du run
ne change** (SDP identique). `scenarios._cause_limite` suit la même raison pour « ce qui limite ».

**Témoins (après correctif).**
| idu | zone | surf | raison | message |
|---|---|---|---|---|
| 97415000BN1169 | U1b | 19 047 | `ppr_rouge` | « Parcelle couverte par le PPR en zone rouge… » |
| 97401000AI0016 | Ud | 5 345 | `emplacement_reserve` | « Emplacement réservé couvrant la parcelle… » |
| 97415000AS0941 | N | 1 625 | `portion_reduite` | « Portion constructible U/AU trop réduite… » |
| 97407000AK1335 | Uc | 167 | `reculs` | « Terrain trop exigu compte tenu des reculs (4 m)… » |

**Portée (échantillon 200 `terrain_exigu`, code courant)** : `reculs` 67 % (message déjà juste),
`ppr_rouge` 14 %, `portion_reduite` 14 %, `emplacement_reserve` 4 %, `contraintes` 1 % → **~33 %**
(≈ 20 600 parcelles île) recevaient un message trompeur « reculs », désormais exact.
**Touche le run : NON** (capacité et `cause` inchangés ; seul le libellé/`exigu_raison` est servi en
direct par le moteur). Verrou : `tests/test_recette1_a1.py` (5 tests verts, dont 4 témoins base réelle).

### A2 · Gabarit — « Plafond d'emprise — non réglementé » en U1e Saint-Paul — ✅ FAIT (aucun correctif)
PLU de Saint-Paul (`97415_reglement_20251217`), chapitre **Zones U1e, U1l**, **Article 9 — Emprise au
sol des constructions : « Il n'est pas fixé de règle. »** Le règlement est **réellement muet** sur
l'emprise au sol en U1e. Le modèle (`maxFootprint status='absent'`, « non réglementé — silence du
règlement ») est **correct**. Ce n'est PAS le cas ORACLE-FIX-1 lot A (où une valeur existait et
manquait). Rien à corriger ; la recherche île sur la règle emprise n'est pas à relancer pour ce motif.
**Touche le run : NON.**

---

## Lot D — « i », fiches, Copilote, Radar, Sources (prioritaire « corrections visibles », Vic 04/10)

- **D1 · Tous les « i » au survol** — ✅ FAIT. `Tip` (LE composant tooltip de l'app, rôle `InfoBulle`)
  rétablit le SURVOL (délai 150 ms) + FOCUS clavier + TAP tactile + fermeture Échap / sortie
  (annule FINITIONS-1 P1 qui l'avait retiré). Le gate `garder` est conservé (seuls les « i »/contrôles
  montent, pas de bulle sauvage) ; `survol` devient un no-op (compat). 34 fichiers portent des « i »
  via `Tip`, tous désormais au survol ; aucun « i » à click-popover custom (grep : 0). Verrou
  `Tip.test.tsx` réécrit (4 tests : survol après délai, focus+Échap, gate sans `garder`, tactile).
- **D2 · Barre grise** — ✅ FAIT. Le filet 1 px (`borderTop` gris) entre la rangée « + CRM / + Projet »
  (cartes bord vert/ambre) et la grille des tuiles (Dossier/Financier/Apporteur) est retiré ; la
  respiration (height) est conservée. (`Fiche.tsx`, la seule barre horizontale décorative de la page ;
  les autres `border-t` sont des bords de conteneurs fonctionnels, pas des filets.)
- **D3 · Fiche parcelle — défilement en tête de section** — ✅ FAIT. `RefDrawer` (primitives.tsx)
  faisait déjà `scrollIntoView` à l'ouverture, mais `scrollMarginTop` valait 8 px → le titre atterrissait
  DERRIÈRE l'en-tête collant (`.tete-collee`), d'où « la vue ne bouge pas » ressenti. Désormais
  `scrollMarginTop` = hauteur MESURÉE de l'en-tête collant + 8 px → le titre arrive bien en haut, sous
  l'en-tête. Accordéon exclusif inchangé.
- **D4 · Fiche commune — premier tiroir seul ouvert** — ✅ FAIT. `ContextePanel.tsx` : l'accordéon
  passe d'un modèle « un `<details>` mémorisé par id en localStorage » (non exclusif → « tous ouverts »)
  à un **accordéon EXCLUSIF** (contexte partagé `CommuneAccProvider`) : un seul tiroir ouvert, le
  **premier** (Identité) ouvert par défaut (revendiqué au montage, réinitialisé par commune via `key`),
  défilement en tête du tiroir ouvert (comme D3, offset `[data-ctx-tete]` → 8 px, pas d'en-tête sticky ici).
- **D5 · Copilote** — ✅ FAIT. `ReponseInline.tsx` : la ligne « journal » (« › J'ai lu la fiche… ») est
  retirée de l'affichage ; le tag interne « SOURCE · FICHE LABUSE (RUN SERVI) » est filtré de la ligne
  SOURCE (les sources EXTERNES restent). `v2.sources` reste intact (choix de variante inchangé) →
  sourçage interne non modifié. Le bouton « Voir la fiche parcelle complète → » est conservé.
- **D6 · Radar / Veille (hub)** — ✅ FAIT. `RadarHub.tsx` : « Ouvrir → » retiré (carte entièrement
  cliquable, `cursor-pointer`), la ligne de bas des deux cartes (« N biens en vente · dernière
  capture … », « N parcelles suivies · N alertes ») retirée ; reste icône + titre + une description.
  La requête `getRadarApercu` (compteurs) n'est plus appelée sur le hub. (Les sous-portes Veille
  gardent leur compteur — hors D6.)
- **D7 · Sources — section « Réserve »** — ✅ FAIT. `SourcesPage.tsx` : le `<details data-sources-reserves>`
  entier est retiré (données inchangées, seul l'affichage). `dvfMaxAnnee`/`TOKENS` devenus inutiles supprimés.

## Lot E — Filtres
- **E1 · phrase « Terrain nu = … »** — ✅ FAIT. `FiltreLabuse.tsx` : phrase retirée (clause SQL inchangée).
- **E2 · encart « Capacité »** — ⏳ À FAIRE (touche le hash / Mes vues / Veille — traité à part).
- **E3 · cases cochées par défaut** — ⏳ À FAIRE.
- **E4 · survol code commune → nom** — ✅ FAIT. `FiltreLabuse.tsx` : la puce de code commune portait
  déjà un `Tip` mais SANS `garder` (donc aucune bulle depuis le gate D1) ; ajout de `garder` + libellé
  « `<code> — <commune>` » (ex. « 97460 — Saint-Paul »). S'ouvre au survol (D1).

## C1 · C3 — carte couches & légende (déjà traités, cf. Lot C)
- **C1 · La légende s'ouvre au cochage** — ✅ FAIT (`CouchesTuyau.tsx`). Cocher une couche REND la main
  à l'auto-ouverture (ré-ouvre la légende même après un repli manuel) ; décocher la dernière couche
  non-défaut la replie ; le repli manuel reste possible.
- **C3 · Couche SCOT retirée de la carte** — ✅ FAIT (`couches_tuyau.py`, endpoint `/map/tuyau/couches`).
  SCOT absent de la liste des couches ET de la légende ; info conservée en fiche (TCO nom+date,
  CINOR nom+statut — date absente du GPU, Bras-Panon hors périmètre publié) et au Dossier PDF.

## Suivi global

| Point | État | Note |
|---|---|---|
| A1 · A2 | ✅ FAIT | run-safe |
| B (vitesse carte) | ⏳ NON FAIT | mesure avant/après + pistes cache/MVT — lot le plus lourd (mesure, non choisi cette session) |
| C1 · C3 | ✅ FAIT | légende auto-ouverte, SCOT hors carte (session 1) |
| C2 · C4 · C5 · C6 · C7 · C8 | ✅ FAIT | **session 2** — Lot C complet (voir ci-dessous) |
| D1–D7 | ✅ FAIT | lot D complet |
| E1 · E2 · E3 · E4 | ✅ FAIT | **Lot E complet** (session 2) |
| C5 (décision Vic) | ✅ FAIT | fiche = carte (même rattachement ST_Contains) |
| F1–F4 (règles outils) | 🔶 EN COURS | composants partagés faits + 1 outil (Taxe) ; pattern vérifié live |
| G + H1–H16 (outils) | ⏳ NON FAIT | audit branchement + refontes outil par outil |
| B (vitesse carte) | ⏳ NON FAIT | mesure avant/après (en dernier, ordre Vic) |

### Session 2 (suite) — Lot F : fondation + 1er outil
- **F2/F3 composants partagés** (`frontend/src/components/outils/EntreeParcelle.tsx`, `ui/Reinitialiser.tsx`,
  verrou `EntreeParcelle.test.tsx`) : `EntreeParcelle` = UN champ adresse/IDU OU « clic carte », l'une
  grise l'autre (opacité 40 %) ; `Reinitialiser` = Chip ↻ en haut à droite. Commit `565a9c57`.
- **Taxe d'aménagement** (commit `33ba998d`) — **pattern F appliqué + VÉRIFIÉ LIVE** (Playwright :
  champ pick → invite carte grisée + Réinitialiser apparaît). Recette du pattern (à répliquer) :
  1. imports `EntreeParcelle`/`Reinitialiser` + `select` du store ;
  2. état `source` + effet qui synchronise `prefillIdu ↔ selectedIdu` (y compris null = fermer la
     fiche vide l'outil, F1) et pose `source` ('adresse' au champ, 'carte' au changement de selectedIdu) ;
  3. `resetAll()` = `select(null)` + remise à zéro de tous les champs locaux (F3) ;
  4. remplacer `ParcelInput` par `<EntreeParcelle source onPick={(i,src)=>{setSource(src);…focusParcelle(i,{fiche:true})}}/>` ;
  5. `{prefillIdu && <Reinitialiser onReset={resetAll} />}` dans l'en-tête du corps ;
  6. F4 : outil mono-niveau → seul « ← Outils » du shell ; outils multi-niveaux (ScanPatrimoine,
     EtudeZone, Blocs, Plu, Communes, ProspectionSolaire) = conserver les « ← <palier> » APRÈS recherche.
- **Gabarit** (commit `25404bb9`) — F1/F2/F3 + **H11 pt2** : quitter l'outil remet la vue en 2D
  (cleanup `setTerrain3d(false)`) → revenir = 2D fond sombre. (⚠ si le fond passe en ortho en 3D, le
  reset du basemap en sombre reste à vérifier live ; le 2D est bien remis.)

**Carte outil↔composant** (ModulePanel MODULES) : taxe-amenagement→TaxeAmenagement (fait), gabarit→Gabarit
(fait), patrimoine→ScanPatrimoine (H4), permis/promesses→M03 (H2), temps→M08 (H9), courriers→M09 (H16),
risques→Risques (Pièges), comparer→CompareModule (H6), assemblage→M16 (`moteurs.tsx`, H5), communes→Communes
(H3), plu→Plu (H1), prospection-solaire→ProspectionSolaire (H13 + Ensoleillement), successions→Successions
(H15), blocs-fonciers→Blocs (H14), etude-zone→EtudeZone (H8), calculette-fonciere→CalculetteFonciere.
Faisabilité = dans la FICHE (`fiche/constructibilite.tsx`), pas un module (H10).

**Recette F par outil (établie + vérifiée live sur Taxe)** :
1. imports `EntreeParcelle`/`Reinitialiser` + `select` du store ;
2. état `source` ; effet : adopter `selectedIdu` quand il change (source='carte'), et si `selectedIdu→null`
   alors que source='carte' → vider l'outil (F1 « fermer la fiche vide l'outil ») ;
3. `resetAll()` : `select(null)` si une parcelle est ouverte + remise à zéro de TOUS les champs/états locaux (F3) ;
4. remplacer `ParcelInput` par `<EntreeParcelle source onPick={(i,src)=>{setSource(src);setIdu(i);focusParcelle(i[,{fiche:true}])}}/>`
   (`{fiche:true}` pour les outils déjà couplés à la fiche comme Taxe ; SANS pour les outils carte-centrés
   comme Gabarit, pour ne pas ouvrir la fiche par-dessus la 3D) ;
5. `{idu && <Reinitialiser onReset={resetAll} />}` en haut à droite du corps ;
6. F4 : mono-niveau → seul « ← Outils » (PanelRetour, shell) ; multi-niveaux (ScanPatrimoine, EtudeZone,
   Blocs, Plu, Communes, ProspectionSolaire) → conserver les « ← <palier> » APRÈS la recherche.

**RESTE F (~11 outils, chacun = recette + son point H)** : Risques/Pièges (F1 scénario 2), Permis M03 (H2),
Temps M08 (H9), ProspectionSolaire (H13 refonte piscines + Ensoleillement), Assemblage M16 (H5 refonte en
étapes, garde `msel` DANS l'outil), ScanPatrimoine (H4 liste+carte, F4 paliers après recherche), EtudeZone
(H8 fusion 2 chemins), CompareModule (H6 colonnes), Communes (H3), Plu (H1), Blocs (H14), Successions (H15),
Courrier M09 (H16), Faisabilité (H10, dans la fiche). `setModule` vide déjà moduleMap/tool/zone/focusIdu
(carte) ⇒ F1 « revenir = vierge » en partie centralisé ; reste `msel`/`tempsPinIdu` à vider au changement
d'outil si on veut le faire au store (sinon géré par outil à cause de l'exception Assemblage H5).

**PUIS : G + reste de H → B** (non commencés). B bloqué tant que l'API n'est pas relancée sans concurrence
(CHASSE-FIX-1 partage peut-être la base — vérifier `pg_stat_activity` avant tout). L'API + le front
tournent (8695/5895) ; C5 vérifié live.

### Session 2 — suite : C5 (décision), E2, E3 faits
- **C5 (décision Vic)** : la fiche « ICPE sur la parcelle » lit le MÊME rattachement que la carte
  (ST_Contains, TOUS régimes, régime affiché) ; la ligne « à proximité ≤ 500 m » reste et passe aussi
  à tous les régimes (exclusion « Non ICPE » levée) ; verdict/poids du run servi inchangés (run-safe) ;
  légende « Parcelle d'implantation (point Géorisques) » (compte 69 au rapport, pas dans la légende).
- **E2** : encart « Capacité » retiré en entier (UI + hash `sdp/sdpx/cap/rnv/dst` + API + prédicat) ;
  champs inertes ⇒ vieux hash/vue ignoré sans erreur (verrou vitest). **0 vue/veille** affectée
  (saved_searches 0/3, saved_filters 0/0, veilles 0/14). Lien « Chercher par capacité → » part avec H10.
- **E3** : cases « partition » (**État du sol** nu/bâti = toutes les parcelles) → tout coché par défaut,
  décocher restreint, tout décocher = 0 parcelle (sentinelle `__aucun__`, back etat_sol → FALSE).
  Rétro-compatible (es=nu = seulement nu). **zfangRegime/frrClassement NON concernés** : il existe une
  catégorie implicite « sans ZFANG / hors dispositif » non listée dans les cases, donc « tout coché »
  ≠ « pas de restriction » — la règle E3 ne s'y applique pas (seul groupe partition affiché = État du sol).

## Session 2 (`fix/recette-1b`, base `origin/main` = `182a6f88`) — Lot C complété

Ordre Vic : **C2, C4–C8 → E2, E3 → F1–F4 → G+H → B**. Fait : **tout Lot C**.
- **C2** minzoom par densité (couches_carte vérifié) : ER z13, zone_activité z12, 50 pas z12, friches
  z13, cimetières z13, ABF z12, SAR z11, SIS z11, QPV/ANRU/TVA-primo z12, postes z11. Pastille déjà générique.
- **C4** SUP **VÉRIFIÉ déjà correct** (décode tuile : 8 subtypes pm1..el10 lowercase, 8 fills, PM1 au
  fond) — « magenta/brun » = état d'avant la dissolution SUP. Remonté, pas fabriqué.
- **C5** ICPE en **parcelles** : `build_tuyau_icpe` (ST_Contains), aplat rouge + contour, régime au clic ;
  **1268 → 1199 rattachés, 69 hors parcelle** non dessinées. ⚠ vérif tuile *live* en attente d'un run
  API (migration `origine` sur base partagée = geste Vic, refusée à CC).
- **C6** ERC : 3 rendus distincts (surface rose / ligne orange / point cyan) ; complétude DB 24 ≥ WFS 20.
- **C7** EnR gated z13, source raster suit zoom_min, légende sans répétition.
- **C8** réseaux : HTB orange, HTA jaune, pylône orange+contour, poste rouge-orangé.

### Reste (ordre Vic) — repérage fait pour accélérer
- **E2 (encart Capacité)** : `CapaciteSection` (`FiltreLabuse.tsx:288`, appelée `:838-840`) + bloc SDP/Déjà-bâti
  (`:365-372`). Sites : `lib/filters.ts` (`F_NUMS`/`F_STRS`, prédicat `:76`, résumé `:160-162`, chips `:182`,
  **table hash `:213-240`** tokens `sdp/sdpx/cap/rnv/dst`), `lib/api.ts:88/98/101/102`, `store/useApp.ts`
  (type `:98-99`, défaut `:153`, `chercherParCapacite:1026`). Garder les champs **inertes** ⇒ hash/vue
  ancien ignoré sans erreur. Compter vues/veilles portant la clé. Lien Faisabilité part avec (H10).
- **E3** cases cochées par défaut (tout coché = pas de restriction, hash sérialise rien). 
- **F1–F4, G+H1–H16, B** : non commencés.

**⚠ Incident base partagée** : `ALTER TABLE parcels ADD COLUMN origine` (migration de `main`, au
démarrage API) prend un verrou EXCLUSIF ; concurrent d'un gros read, il a bloqué toute la base `labuse`
(une autre session y lançait `pytest`). Corrigé : annulation du SEUL ALTER orphelin (le mien). Relancer
l'API proprement demande que la migration `origine` passe une fois sur la base partagée — **geste Vic**.

**Fait cette session** (bucket « corrections visibles » choisi par Vic) : A1, A2, C1, C3, D1, D2, D3, D4,
D5, D6, D7, E1, E4 — **13 points**, chacun commité, `tsc` 0 · `vitest` 225 · pytest ciblé vert · oracles
0 faux préservé. L'app se lance sans erreur de rendu (smoke test Playwright : 0 erreur hors
`/config/run` 404 et `/moi` 401 d'environnement).

**Non fait, avec motif** (hors bucket cette session) : B (mesure vitesse, lot le plus lourd) ; C2/C4–C8
(couches carte, nécessitent rendu carte + DB) ; E2/E3 (touchent la sérialisation hash/Mes vues/Veille) ;
F1–F4 et G+H1–H16 (refontes d'état et audit branchement des 16 outils, le gros du mandat). Aucun point
n'est sauté silencieusement : ils restent à traiter dans une session suivante.

**⚠ Captures avant/après** : à produire avec l'app lancée via script node Playwright direct (le
screenshot MCP expire à 5 s sur ce poste — constat récurrent des mandats précédents). L'app tourne
(API 8695 / front 5895) ; la base des captures « après » est en place (`captures-apres/`).

> Captures de Vic : **5** présentes dans `captures-vic/` (le mandat en annonce ~20 ; les points se
> lisent sans elles, comme prévu). Signalé, non bloquant.

---

## Session 3 (`fix/recette-1c`) — Lot F : le reste des outils (pattern F appliqué/jugé par outil)

**Règle tenue** : 0 valeur servie changée (aucune ligne CHANGEMENTS.csv — ce sont des changements de
STRUCTURE d'état/affordance, pas de valeur), run-safe. `tsc` 0 sur mes 9 fichiers (⚠ voir note maplibre),
`vitest` **230 verts**.

**Invariant du pattern (corrigé cette session)** : `source='carte'` ne doit JAMAIS être posé tant que
`selectedIdu` est faux — sinon l'effet F1 (« fermer la fiche vide l'outil ») se déclenche AU MONTAGE et
efface une parcelle pré-remplie par une PORTE (calcPrefill, solairePrefill…). Les portes laissent donc
`source=null` (parcelle chargée, les deux entrées restent actives jusqu'au Réinitialiser). Bug attrapé par
les tests ProspectionSolaire ; corrigé aussi dans Calculette (même schéma).

### Outils RÉÉCRITS au pattern F cette session
- **Calculette foncière** (`CalculetteFonciere.tsx`) — F1/F2/F3. Couplée à `selectedIdu` (comme Taxe),
  porte `calcPrefill` conservée (source=null). `{fiche:true}` au pick.
- **Remonter le temps M08** (`ModulePanel.tsx`) — F2 (EntreeParcelle, `designer(id, src)`) + F3
  (Réinitialiser : vide `tempsPinIdu` + remet l'année ancienne à 1950). Carte-centré via `parcelPrefill`
  (source='carte'). **= le « H9 »** (le reste de M08 — frise, épingle — était déjà en place).
- **Étude de zone** (`EtudeZone.tsx`) — F3/F4. `nouvelleEtude` scindé : `resetEtude` (Réinitialiser,
  reste dans la porte) + `nouvelleEtude` (`← Changer la zone`, retour accueil 2 portes). Le bouton
  « Nouvelle étude » du bas devient le Réinitialiser unique. **H8 « fusion 2 chemins »** : les deux
  entrées (point / polygone) alimentent DÉJÀ un seul pipeline de résultat (en-tête qui nomme le périmètre
  réel) → la fusion était faite ; F la rend cohérente côté reset.
- **Prospection solaire** (`ProspectionSolaire.tsx`) — F2/F3 dans **Ensoleillement** (EntreeParcelle +
  Réinitialiser + adoption `selectedIdu`). F4 déjà là (2 cartes d'entrée + BackBar). **Piscines** garde
  son « Toute l'île » (clear commune) + reset auto au changement de commune — pas de reset fait-main à
  unifier. **= H13** (les 2 métiers/2 entrées existaient déjà ; F complète Ensoleillement).
- **Comparer** (`compare/ComparePanel.tsx`) — F3 : « tout vider » → Réinitialiser unique en tête. Multi-add
  (jusqu'à 3) ⇒ PAS d'EntreeParcelle (le champ cumule, il ne « grise » pas). **H6 colonnes** déjà en place.
- **Blocs fonciers** (`Blocs.tsx`) — F3 : Réinitialiser (remet TOUS les filtres au défaut + replie le
  listing + ferme la fiche). Entrée commune+filtres ⇒ PAS d'EntreeParcelle.
- **Successions** (`Successions.tsx`) — F3 : Réinitialiser (revient « toute l'île » + ferme la fiche).
  Entrée commune ⇒ PAS d'EntreeParcelle.
- **Pièges & risques** (`blocB.tsx` `O5Servitudes`) — F2 (EntreeParcelle : champ → `allerA` zoom SANS
  ouvrir la fiche ; clic carte → effet `selectedIdu` qui analyse + ouvre) + F3. F1 déjà inhérent (le
  wrapper `Risques` remonte O5 par `key={selectedIdu}`). **= « F1 scénario 2 »**.
- **Assemblage M16** (`moteurs.tsx`) — F3 : « vider » → Réinitialiser (vide `msel` + anneaux voisines +
  résultat). Multi-sélection (`msel`) ⇒ PAS d'EntreeParcelle (clic-carte cumule). **H5 « garde msel DANS
  l'outil »** : `msel` est bien store-local à l'outil (purgé au démontage, GB-010). La « refonte en étapes »
  détaillée demande le texte recette de Vic (non persisté) — voir § H à spécifier.

### Outils JUGÉS déjà conformes F (aucun code changé, motivé)
- **Scan patrimoine** (H4) — owner-centric, `ParcelInput` multi-callback (onPick/onProprietaire/onAddress)
  → EntreeParcelle ne convient pas. F4 **déjà** là (`Retour` des 2 portes + « changer » = reset du
  propriétaire). F1 via `setModule`/ponts consommés. Conforme en l'état.
- **Communes** (H3) & **Plu** (H1) — hubs multi-niveaux (portes + `Retour`), entrée commune/zone, pas de
  parcelle unique ni de reset fait-main. F4 **déjà** satisfait. Conformes en l'état.
- **Permis M03** (H2) & **Courrier M09** (H16) — radar / flux multi-destinataires guidé : pas d'entrée
  « une parcelle » (M03 = AddressAutocomplete large ; M09 = liste de destinataires), pas de reset fait-main
  (« effacer » déjà retiré par RETOURS-15, « vider le champ suffit »). F2/F3 ne s'appliquent pas ; F1/F4
  déjà couverts (setModule / stepper+Retour). **H2/H16 = items recette à part** (texte non persisté).
- **Mon secteur** (S1) — `hidden` (contenu déplacé dans la fiche §Marché) : laissé tel quel.
- **Faisabilité** (H10) — dans la FICHE (`fiche/constructibilite.tsx`), pas un module. Non touché.

### ⚠ À SPÉCIFIER par Vic (bloquant pour faire « juste »)
Le **détail** des points H (H1,H2,H3,H5-refonte,H9,H13-refonte-piscines,H14,H15,H16) n'est persisté NULLE
PART — seules les descriptions d'une ligne du présent rapport existent (le texte recette original est dans
la session d'origine, perdu). J'ai appliqué **F partout où il s'applique** + les H **évidents dans le code**.
Les « refontes » (H5 étapes, H13 piscines) et les H non décrits ont besoin du texte de Vic.

### ⚠ maplibre / node_modules symlinké
Mi-session, `tsc` a mis à sortir des erreurs `maplibre-gl` (« no default export ») dans `map/*` et
`TimeMachine.tsx` — **fichiers NON touchés par moi**. `node_modules` est un **symlink vers le worktree
principal** `~/Desktop/labuse/frontend/node_modules`, réécrit par une autre session/worktree pendant le
mandat (drift de version maplibre). Mes 9 fichiers compilent proprement ; `vitest` 230 verts. Env, pas mon
code — à re-vérifier `tsc` quand le node_modules partagé est stable.

### RESTE (ordre Vic) : **G + reste de H (si Vic fournit le détail) → B**
B = vitesse carte : **NON commencé** ; exige l'API relancée + `pg_stat_activity` vérifié d'abord
(CHASSE-FIX-1 partage la base). API/front PAS lancés cette session (travail purement front/tsc/vitest).

---

## Session 4 (`fix/recette-1c`) — H1–H4 corrigés (Vic : « pas déjà conformes ») sur les parties FRONT

Vic a fourni le détail H1–H4 + répondu à 8 points d'arbitrage. ⚠ Le texte **H5→H16 + Lot G** n'est
**toujours pas parvenu** (attachement puis gros collage : seul le texte autour arrive de mon côté — les
blocs collés/pièces jointes sont tronqués dans mon contexte). À redonner en **texte simple dans le message**.

Commits `853aa478` (H1/H2 sans ambiguïté) + `b66c425f` (H2/H4 front). tsc 0, vitest **230**.

### FAIT (front, vérifié)
- **H1 PLU** — (1) « les vérifications » : `VerifProcedure` (onglet *Par parcelle*) passe au pattern F
  (EntreeParcelle + Réinitialiser + adoption/clear `selectedIdu`). (2) placeholder annuaire coupé →
  raccourci « ex. hauteur de clôture » (le « dans <commune> » redondant + tronqué sur noms longs).
- **H2 Permis** — (1) **phrase ≤ 200 m sans accordéon** (compte + détail en clair). (3) **pastilles
  retirées** : « approx. (adresse) »/« non localisé » et le badge « autorisé » (état_libelle) retirés de la
  ligne ; **point de couleur d'état gardé** ; précision du géocodage **déplacée dans la bulle**. (bulle↓)
  **BULLE au clic** sur le point permis (MapView) : nature+date+état+commune+précision + « détails → »
  (ouvre le drawer) — comme opérations/concurrents. `commune`/`geoloc` portés à la feature.
- **H4 Scan patrimoine** — (a) « Voir ses parcelles → » = **vrai bouton primaire pleine largeur** (marge
  standard). (b) le bloc **« Blocs contigus » se replie** quand la liste s'ouvre ; **les 4 tuiles de
  compteurs RESTENT** (la barre compacte qui les masquait est supprimée) ; liste **en surbrillance carte**
  (useModuleMap, déjà là). (c) retour **« ← Scan patrimoine » gardé APRÈS recherche** (état 2).

### RESTE H1–H4 — besoin de l'API/DB (à grouper avec B)
- **H2 (2) périmètre 200 m** : quand une parcelle est saisie → les compteurs d'état **comptent dans les
  200 m**, le filtre s'applique dans ce périmètre, la carte ne montre **que** ces permis colorés par état ;
  dessin **contour parcelle + cercle 200 m discret** ; **Réinitialiser revient à l'île**. ⇒ vérifier les
  champs servis par `/modules/parcelle-permis` (classification d'état par item) + dessin cercle (centroïde).
- **H3 Communes** : (7) **diagnostiquer chaque trou** de l'évolution (ex. 2024T1 ancien vide alors que
  terrain = 449 ventes = bug requête ; permis vides 2024T1-T3 ; 2026 vide = DVF non publié) → corriger le
  bug / expliquer le vrai trou ; en-tête = **nombre de lignes réellement affichées** (11, pas « 8 trim. »).
  (8) **cadence Radar** : vérifier que la capture tourne chaque jour (page « dernière capture 27/09 » un
  4 oct → dire pourquoi) ; le bloc Marché des annonces **affiche la date de dernière capture**.

### Toujours bloquant
- **H5→H16 + Lot G** : texte non reçu (voir ⚠ ci-dessus). Impossible de faire « juste » sans.
- **API non lancée** : la relance passe la migration `origine` (verrou exclusif sur base partagée
  CHASSE-FIX-1) = geste Vic. H2-périmètre / H3 / B l'exigent → **green-light + état migration `origine`
  attendus de Vic** avant de démarrer l'API (puis `pg_stat_activity` vérifié, pas de mass-kill).

---

## Session 5 (`fix/recette-1c`) — mandat complet reçu (`MANDAT-RECETTE-1-GH.md`) ; H1–H4 FINIS, API up

Le mandat G + H1→H16 est enfin lisible (fichier `MANDAT-RECETTE-1-GH.md`, fait foi). Feu vert API donné
(colonne `origine` déjà en base, aucune migration). API 8695 relancée après vérif `pg_stat_activity`
(0 requête > 30 s sur `parcels`) ; jamais de backend tué. Ordre Vic : **H2-périmètre + H3 → H5→H16 → G → B**.

**H1–H4 FINIS** (commits `853aa478` · `b66c425f` · `bee676d5` · `9c049309`) — tsc 0, vitest 230, vérifiés
sur l'API réelle :
- **H1 PLU** : VerifProcedure → pattern F ; placeholder annuaire raccourci. (reste H1.1-3 = Protocole G.)
- **H2 Permis** : phrase ≤200 m sans accordéon · bulle au clic sur le point (MapView) · pastilles
  « approx./autorisé » retirées (point d'état gardé) · **périmètre 200 m** (compteurs/filtre/liste/carte
  scopés, cercle 200 m + contour, « Revenir à l'île »). (reste H2.1-2 complétude/exactitude = Protocole G.)
- **H3 Communes** : évolution — **axe de trimestres commun** (axis_min) corrige les faux trous (2024T1
  ancien 957 ventes, permis 2024T1-T3) ; vrais trous 2026 expliqués (DVF jusqu'au 2025T4) ; en-tête = nb
  lignes réelles (11). Radar — **date de dernière capture** affichée (27/09, 7 j de retard au 04/10) ;
  **la capture passe par l'EXTENSION Mac (RADAR-AUTO-1), pas un cron VPS** → la « cadence VPS » du mandat
  n'existe pas ; la staleness est désormais visible. (reste H3.1 Protocole G 4 chemins.)
- **H4 Scan** : « Voir ses parcelles » vrai bouton primaire pleine largeur · bloc « Blocs contigus » se
  replie à l'ouverture de la liste · **4 tuiles de compteurs gardées** (barre compacte supprimée) · retour
  « ← Scan patrimoine » après recherche · surbrillance carte (useModuleMap, déjà là).

### RESTE (ordre Vic) : H5→H16 (UI + Protocole G), puis Lot G, puis B
- **UI refontes** encore à faire : **H5** Assemblage (refonte en étapes 1/2, 8 max, contiguïté/isolées,
  retirer voisines + bouton courrier), **H6** Comparer (2ᵉ colonne trop large → colonnes égales), **H7**
  Méthode & limites (texte = sources lues + rond flèche contrasté), **H8** Étude de zone (fusion 1 entrée
  parcelle + choix « zone seule / zone + chalandise », retirer « temps de trajet », auto-ouverture étape 2),
  **H9** Temps (bouton « 1980 carte » : corriger WMTS ou retirer), **H10** Faisabilité (3D→Gabarit, pied
  retiré, bloc règles mis en valeur, Réinit), **H13** Solaire piscines (« N confirmées · N à confirmer »
  24 communes, retirer plafond 1 000 → pagination 50, parcelles colorées, retirer colonne m²).
- **Lot G** (protocole de branchement) : **gros audit** — pour CHAQUE outil, chaque chiffre/libellé relié
  à son id registre (V5f) + ligne BRANCHEMENT.csv, recalcul SQL/fonction sur 3 témoins (Saint-Paul ·
  Bras-Panon · Saint-Denis pour les outils commune), écarts→bug→fix→test, V6b complété. Livrable
  `BRANCHEMENT-OUTILS.csv`. = effort multi-session (H12/H14/H15/H16 = Protocole G seul).
- **B** vitesse carte : en dernier.

⚠ API 8695 laissée up (mandat en cours, feu vert Vic). À arrêter en vraie fin de session.

---

## Session 6 (`fix/recette-1c`) — H5 Assemblage FINI (refonte + Protocole G cité)

- **H5.2/H5.3 refonte** (commit `9a354425`) : Assemblage en **étapes** (modèle Comparer communes).
  Étape 1 « Choisir les parcelles » (EntreeParcelle adresse/clic carte + liste ✕, **8 max** avec message,
  « Vérifier l'assemblage ») ; Étape 2 « Assemblage » — contiguës → en-tête « N contiguës · surface
  totale » + bilan ; **non contiguës → « Pas d'assemblage possible » + parcelles isolées, rien d'autre**
  (back renvoie `isolees`). Réinitialiser vide la liste. **Retiré** : section « parcelles voisines »
  (rings/voisines) + bouton « Préparer courrier propriétaire ». tsc 0, vitest 231 (Assemblage.test réécrit).
- **H5.1 Protocole G** (commit `07b9e30c`, `BRANCHEMENT-OUTILS.csv`) : chaque chiffre tracé à sa fonction.
  SDP/charge/logements = `aggregate_assiette` → `fiche_payload` + `_capacite_union` (**même moteur que la
  fiche, sur l'UNION des géométries** — vérifié `assemblage.py:244`, jamais la somme des résiduels) → cité
  CALCULS-AUDIT-1 (non recalculé, conformément au mandat). NB : l'Assemblage affiche la **charge** foncière
  (bilan d'opération), pas la **taxe** foncière annuelle. 0 écart.

**Avancement mandat** : G + H1·H2·H3·H4·H5·H11 faits. **Reste** H6·H7·H8·H9·H10·H12·H13·H14·H15·H16
(UI + Protocole G par outil, `BRANCHEMENT-OUTILS.csv` à étendre), puis **B** (vitesse carte).
