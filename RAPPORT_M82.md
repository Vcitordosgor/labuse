# RAPPORT M82 — La section Outils : audit des 29, vérité, sort proposé

Branche `feat/m82-outils`. Run servi = **q_v9_m81** (`config/served_run.txt`). Audit mené par
6 passes parallèles, **véracité prouvée par SQL indépendant** sur la base `labuse` (SELECT seul) et,
quand nécessaire, par frappe réelle des endpoints (uvicorn local). Aucune donnée inventée.

Convention d'état : **LIVE** (lit q_v9_m81) · **fonctionne** · **dégradé** (marche à moitié) · **mort**
(500 / liste vide / indisponible). « Sort » = ce que je propose ; **tu tranches**.

---

## 1. Verdict d'ensemble

Sur 29 outils : **aucun n'est mort à la base** — la donnée existe partout. Mais **6 sont cassés ou muets
à l'écran**, pour des causes de plomberie (SQL, proxy, affichage), pas de fond :

| Symptôme écran | Outils | Cause RÉELLE |
|---|---|---|
| Liste HTTP 500 | **promesses** | bug SQL (`s2.tier` hors CTE, `modules.py:408`) — le compteur, chemin séparé, marche (9142) |
| Liste vide | **zan** | prédicat impossible (`ocs_ge weight_applied>0`, or 431 663 lignes toutes à 0 au run) |
| « indisponible » | **servitudes**, **comparateur** | `/servitudes-invisibles` et `/comparateur-communes` **absents du proxy Vite** — vivants en PROD |
| « non calculé (lancer `labuse renouv`) » | **renouvellement** | faux négatif : table pleine (67 258 @ q_v9_m81), l'ErrorState se déclenche sur toute panne réseau |
| 1 seule ligne du 27/07 | **quoi de neuf** | `detect-events q_v8→q_v9_m81` jamais lancé → 0 bascule au journal |
| promesse fausse | **courriers** | `courrier_demandes` = table **dead-letter** (0 lecteur dans tout le repo) |

**Compteur des sorts** : GARDER **10** · RÉPARER **13** · REFONDRE **5** · à ARBITRER pour retrait **1**
(matching). Détail plus bas.

**Deux transverses majeurs, à trancher :**
1. **Le mauve** : le token `violet #B497F0` est encore la « couleur module » (doctrine pré-M61). M61 a
   réservé le mauve à l'IA. Le mandat demande le vert partout hors IA → **corrigé en Phase 1** (le
   `VIOLET` du registre = outils-only, jamais importé par le Copilote ; repointé vers `mint`).
2. **Le panneau outil `w-[320px]` + `overflow-hidden`** (~288 px utiles) fait déborder deux outils
   (Rareté, bouton Matching) et coupe des mots (Comparateur, Annuaire) — c'est une contrainte de
   largeur globale, pas un défaut par outil.

---

## 2. Les 10 cas particuliers (A–J) élucidés

**A. Division parcellaire — LA CONTRADICTION LEVÉE.** Le « score 0-100 » vient d'une table précalculée
`module_division` (formule géométrique, `modules.py:12` + 137-143) : `ST_MaximumInscribedCircle` sur la
parcelle érodée du bâti → place libre / emprise / forme / accès voirie. **C'est un score de FACILITÉ
géométrique de détachement, pas une probabilité inventée — explicable au client, honnête.** Les 3 169
candidats = 4 428 bruts (score≥70) − 1 259 exclus étage 0 (q_v9_m81). **M-ENTREE avait raison** : il n'y
a **aucun endpoint de divisibilité PAR PARCELLE** (lookup par IDU) — ce score vit en table batch,
interrogée en LISTE, alimentée par un `compute` **admin manuel** (23/24 communes). Les deux constats
coexistent : score de liste ≠ lookup fiche. → Le BACKLOG M-ENTREE reste vrai ; MAIS si on expose un
lookup par IDU, la porte fiche + le branchement Copilote redeviennent possibles (le contenu est solide).
**Sort : RÉPARER** (automatiser le compute dans le pipeline, 24ᵉ commune, retirer la fuite « (SQL) »).

**B. Renouvellement — PAS mort.** La table `parcel_renouvellement` a **67 258 lignes sur q_v9_m81**
(computed_at 2026-08-13). L'écran « non calculé » est un **faux négatif** : `Renouvellement.tsx:39`
affiche l'ErrorState sur *toute* erreur HTTP (API down comprise), pas seulement le vrai 503 « table
absente ». Ce n'est PAS une table absente de la bascule M80. **Sort : RÉPARER** (distinguer 503 réel vs
panne réseau) + Phase 1 : retirer la fuite CLI `labuse renouv`.

**C. Comparateur de communes — mort en DEV seulement.** SQL et 6 tables **sains** (24 communes
retournées). Cause : `/comparateur-communes` **absent du proxy Vite** (`vite.config.ts`), comme jadis
`/bilan` (M58). Vivant en prod (même origine FastAPI). **Sort : RÉPARER** (+1 ligne proxy) + Phase 1 :
mots coupés (chips pondération → libellés courts `O6_COLS` déjà définis, blocB.tsx:120).

**D. Servitudes invisibles — mort en DEV seulement.** Idem C : `/servitudes-invisibles` absent du proxy.
Endpoint 200 en prod, donnée vraie sur le canari (SUP PPR, source GPU datée). **Sort : RÉPARER** (+1
ligne proxy).

**E. Scorer une adresse — échec du re-géocodage.** La mécanique adresse→parcelle **marche** (BAN vivant,
`ST_Contains` OK). L'échec : `onPick` (`ScoreurAdresse.tsx:31`) **jette l'`idu`/`lon`/`lat` déjà résolus
par l'autocomplétion** (table interne `adresses`) et ne garde que le label, que le backend **re-géocode
via BAN externe** (format « 12 Rue…, Saint-Paul (97460) » non natif BAN) → retombe hors parcelle →
« aucune parcelle ». **Sort : RÉPARER** (passer l'idu déjà résolu, supprimer le 2ᵉ aller-retour).

**F. Matching promoteurs — démo dans un produit payant.** `match_profiles` = **2 lignes `demo=t`**
(semées au boot). `event_log kind='match'` = **0** (aucun match jamais produit). La création d'un profil
RÉEL est **gelée derrière l'admin** (`exiger_admin`) → pour un client, `addProfile` renvoie 403. Donc
« enregistrez vos critères, soyez alerté » = **boucle morte**. RÉEL = uniquement le bloc « promoteurs
actifs SITADEL » (bas de l'outil, SIREN public) + l'allumage carte du filtre. **Sort : REFONDRE ou
DÉGONFLER** — c'est le seul candidat sérieux au **RETRAIT** si on ne livre pas la vraie boucle.

**G. Quoi de neuf — figé.** `event_log` = **1 seule ligne** (une reprise de veille du 27/07),
**0 bascule** : `detect-events q_v8_calibre q_v9_m81` n'a jamais tourné (les deux runs sont pourtant en
base). Recouvrement fort avec la **cloche** (même journal). **Trois circuits de veille cohabitent** :
O10/cloche (`event_log`) · M11 `saved_searches` · Copilote `veilles` (M78). **Sort : RÉPARER**
(lancer detect-events) **+ clarifier** les 3 circuits (recommandation : fusionner M11 dans le Copilote,
garder O10 en pur lecteur du journal).

**H. Radar des mutations — rangs à trous NORMAUX.** Le `rang` stocké est un **classement GLOBAL** ; vu à
travers le filtre `tier='brulante'`, les rangs manquants (#4,#6,#8…) appartiennent à d'autres tiers
mieux classés. Ce n'est pas un bug. Les 3 424 copropriétés ont `rang IS NULL` → dénominateur
`rang_total = 428 239` sur 431 663. La note « niveaux 2025-2026 provisoires / classement fiable » est
**cohérente** : le classement repose sur `mult_base` (×N relatif), pas sur le comptage de ventes
récentes ; le retard DVF dégrade la datation absolue sans casser l'ordre relatif. **Sort : GARDER** +
Phase 1 (badge copro en violet → neutre) ; utile : une phrase « rang global » pour que le client ne lise
pas « bug ».

**I. Assemblage — score non gardé.** Formule (`moteurs.py:156`) : `contigu 45 pts + owners 20 + tous-PM
10 + SDP 25`. La **contiguïté seule vaut 45 pts** ; 4 parcelles écartées (`faux_positif_probable`) à
0 m² SDP obtiennent **55/100** avec un badge vert « d'un seul tenant ». **Le score récompense la
géométrie, pas la constructibilité.** Comportement attendu : plancher bas (+ avertissement) si
`sdp_cumulee = 0` ou si toutes les parcelles sont en étage 0. **Sort : RÉPARER** (garde-fou score).

**J. Baromètre — trimestre en cours.** `2026T3` (trimestre COURANT) n'a qu'1 mutation isolée (max
`date_mutation = 2026-08-10`) → affiché en tête du graphe comme un **effondrement** (barre ~0). Artefact
réel. **Sort : Phase 1** — étiqueter « en cours (incomplet) » ou exclure `date_trunc('quarter') <
date_trunc('quarter', now())`. + le **PDF n'hérite PAS de la DA LABUSE** (FPDF brut, sans `_Pdf`/`_logo`/
`pied_de_page_pdf` de `pdf_premium.py`) → grief fondé, **Phase 3a**.

---

## 3. Le tableau des 29

Véracité = 2 valeurs vérifiées au SQL indépendant (✓ = concorde). « fuite » = vocabulaire interne rendu
au client.

### Détecter le foncier
| Outil | Branchement (route · table · run) | Véracité | État | Fuite / défaut | Sort |
|---|---|---|---|---|---|
| Radar des mutations | `/v2/*` · parcel_p_score_v2 · **q_v9_m81** | brûlantes 120 ✓ · rang_total 428 239 ✓ | LIVE | badge copro violet | **GARDER** + note « rang global » |
| Faisabilité | `/modules/programme` · dryrun+residuel · **q_v9_m81** | déterministe (SDP×1,15) ✓ | LIVE | — | **GARDER** |
| Division parcellaire | `/modules/division` · module_division · géo+étage0 | 3169 = 4428−1259 ✓ · scores 69-99 | dégradé (gisement admin 23/24) | « (SQL) » écran | **RÉPARER** |
| Foncier fantôme | `/modules/fantome` · pm+dryrun · **q_v9_m81** | 5848 ✓ · branche « dirigeant inactif » = 0 cas | dégradé | « PM », « RNE » | **RÉPARER** |
| Renouvellement | `/renouvellement/liste` · parcel_renouvellement · **q_v9_m81** | 67 258 @ run ✓ | faux négatif d'affichage | `labuse renouv` | **RÉPARER** |
| Scan patrimoine | `/modules/patrimoine` · pm foncier · **q_v9_m81** | SIDR 4183 ✓ · SDP 934 488 ✓ (−58 IDU non appariés) | LIVE | — | **GARDER** |
| Mode bailleur | `/modules/bailleur` · qpv+sru · **q_v9_m81** | 2611 QPV ✓ · 2 carencées ✓ | LIVE | — | **GARDER** |
| Rareté du foncier | `/pipeline-rarete` · commune_conso_enaf · **q_v9_m81** | Cilaos dépassé ✓ · St-Philippe ~1 an ✓ | données OK, **déborde H** | scroll horizontal (min-w) | **RÉPARER (CSS)** |
| Quoi de neuf | `/events` · event_log · q_v9_m81 | 1 reprise, **0 bascule** | quasi-mort | « nouveau run de scoring » | **RÉPARER + clarifier** |
| Matching promoteurs | `/partners/*` · match_profiles(démo)+sitadel | 2 profils démo, **0 match** | démo (boucle morte) | bouton « RÉEL·SITADEL » 2 lignes | **REFONDRE / RETIRER** |

### Analyser & simuler
| Outil | Branchement | Véracité | État | Fuite / défaut | Sort |
|---|---|---|---|---|---|
| Scorer une adresse | `/scoreur-adresse` · parcels+score_e · **q_v9_m81** | BAN→CZ1313 ✓ · score_e 45 801 estimables | dégradé (re-géocodage) | docstring q_v8 (commentaire) | **RÉPARER** |
| Vérif procédure PLU | `/verif-procedure/{idu}` · veille_plu.yaml | 24 communes, 4 en procédure ✓ | fonctionne | « Sudocuh » opaque | **GARDER** + afficher date/stade, entrée commune |
| Annuaire PLU | `/plu-annuaire/*` · plu_reglement_extrait | **21 communes indexées** (front dit « /24 ») | UX dégradée | scroll horizontal, « /24 » faux | **REFONTE 3b** |
| Calculette foncière | `/faisabilite/{idu}/charge` · bilan · **q_v9_m81** | CF 399 €/m² **vérifiée à la main** ✓ | fonctionne | — | **GARDER** |
| Comparateur communes | `/comparateur-communes` · 6 tables · **q_v9_m81** | 24 communes ✓ (SQL sain) | mort en DEV (proxy) | mots coupés (libellés) | **RÉPARER** |
| Servitudes invisibles | `/servitudes-invisibles/{idu}` · spatial_layers | canari SUP PPR ✓ | mort en DEV (proxy) | — | **RÉPARER** |
| Comparer les parcelles | `/compare` · _build_fiche · **q_v9_m81** | cohérent fiche | fonctionne (pauvre) | doublons fiche | **REFONTE 3d** |
| Assemblage | `/moteurs/assemblage` · residuel+dryrun · **q_v9_m81** | score 55 sur 0 m² SDP (formule vérifiée) | fonctionne (score non gardé) | badge vert trompeur | **RÉPARER** |
| Baromètre foncier | `/moteurs/barometre` · dvf+sitadel | trimestre en cours = faux effondrement | fonctionne | T-en-cours + PDF sans DA | **RÉPARER + 3a** |
| Marché | `/moteurs/marche/{c}` · build_marche_commune · **q_v9_m81** | U 479 / AU 328 **= SQL M79** ✓ | LIVE | (seuil réel 10, pas 5/3) | **GARDER** |
| Radar permis | `/modules/permis` · sitadel+m10 | St-Denis 437 ✓ · St-Paul 632 ✓ | fonctionne | « 3 m » = 3 mois (ambigu) | **GARDER** + libellé |
| Promesses mortes | `/modules/promesses` · sitadel+dryrun · **q_v9_m81** | compteur 9142 ✓ · **liste 500** | liste MORTE | — | **RÉPARER (1 ligne SQL)** |
| Vélocité admin | `/modules/velocite` · m10_permit_delais | St-Pierre 8mo/4897 ✓ · Ste-Suzanne 8mo/1178 ✓ | fonctionne | — | **GARDER (modèle de ton)** |
| Changement PLU | `/moteurs/simulplu` · spatial+residuel · **q_v9_m81** | ratio U 0.318 ✓ | fonctionne | — | **GARDER** |
| Simulateur ZAN | `/moteurs/zan` · commune_conso_enaf(Cerema) · **q_v9_m81** | St-Paul 434.9/90.0 ✓ **= Cerema** · **liste vide** | dégradé | liste 0 non signalée | **RÉPARER** |
| Remonter le temps | TimeMachine · WMTS IGN | fonds OK | dégradé (mal conçu) | 2 sélecteurs identiques, pas d'entrée parcelle | **REFONTE 3c** |

### Passer à l'action
| Outil | Branchement | Véracité | État | Fuite / défaut | Sort |
|---|---|---|---|---|---|
| Suivi de secteur | `/carnet-secteur` · dvf+signals+sitadel · **q_v9_m81** | 396 secteurs ✓ · La Possession 65 opp | fonctionne | **« post-M7 » + `note` servi (mandat + tables)** | **GARDER** + réparer fuite |
| Contrôle avant achat | `/modules/duediligence` · cascade · **q_v9_m81** | CZ1078 : 8 flags/0 excl ✓ | fonctionne | — | **GARDER** |
| Courrier propriétaire | `/modules/courriers` + `/courrier/demande` · courrier_demandes | 2 demandes `a_traiter`, **0 lue** | **dégradé / trompeur** | `title` (Merci Facteur + env + « action Vic ») ; promesse fausse | **REFONDRE** |

---

## 4. Fuites de vocabulaire interne (inventaire complet — Phase 1)

Rendu AU CLIENT (pas commentaire) :
- `labuse renouv` — Renouvellement.tsx:39 (+ backend app.py:3092)
- `post-M7` — blocB.tsx:246 (Carnet)
- champ `note` servi « mandat Auth & Plans » + tables `watch_zones` / `watched_parcels` — carnet.py:36-37
- `title={d.raison}` « Merci Facteur PRO — action Vic ; LABUSE_MERCIFACTEUR_API_KEY/SECRET » — courrier.py:33-34 (rendu ModulePanel.tsx:615)
- « (SQL) » — Division, ModulePanel.tsx:128
- « PM » / « RNE » — Foncier fantôme, modules.py:569
- « nouveau run de scoring » — Quoi de neuf, empty-state blocB.tsx

Commentaires code (non rendus, hygiène seule) : numéros de mandat M01…, docstring scoreur q_v8.

---

## 5. Le mauve hors IA (inventaire — Phase 1)

Le `VIOLET` du registre (`registry.ts:4` = `TOKENS.violet`) est **outils-only** — importé par outils +
page Outils (Rail) + un bloc fiche (PermitsProximityBlock), **jamais par le Copilote/IA** (qui utilise
les classes Tailwind `cp-violet`, séparées). ~120 usages : nombres de score, sliders (`accent-violet`),
liseré « ← Outils », bandeaux, badges. **Correction Phase 1** : repointer `VIOLET → mint`,
`VIOLET_DIM → vert atténué` (un seul point), + le badge copro `text-violet` (ScoringV2.tsx:92). Le
Copilote reste mauve (c'est de l'IA).

---

## 6. Proposition de TRI (Phase 2 — attend ton arbitrage)

Aujourd'hui 3 groupes (Détecter / Analyser / Agir). Le mandat propose **5 groupes dans l'ordre du geste**.
Répartition proposée (le client comprend en 5 s ce qui sert tous les jours) :

- **Trouver** — Radar des mutations★ · Faisabilité★ · Foncier fantôme★ · Scan patrimoine★ · Division ·
  Renouvellement · Mode bailleur · Rareté du foncier
- **Instruire** — Scorer une adresse★ · Calculette foncière · Contrôle avant achat★ · Vérif procédure PLU ·
  Annuaire PLU · Servitudes invisibles · Comparer les parcelles · Assemblage★ · Changement PLU
- **Contacter** — Courrier propriétaire · Matching promoteurs
- **Comprendre le marché** — Marché★ · Comparateur de communes★ · Baromètre foncier · Radar permis ·
  Vélocité admin · Promesses mortes · Simulateur ZAN
- **Suivre le temps** — Quoi de neuf · Suivi de secteur · Remonter le temps

**En-tête** : « Les moteurs métier de LABUSE » saute (« métier » n'est pas le sujet). Proposition :
**« Les outils LABUSE — 29 moteurs pour détecter, instruire et suivre le foncier. »** (ou plus court :
**« Vos outils : trouver, instruire, contacter, comprendre, suivre. »**). Aucun mot sur deux lignes.

---

## 7. Candidats au retrait (« si un outil n'apporte pas de valeur et n'est pas améliorable »)

- **Matching promoteurs** — SEUL candidat sérieux. La boucle « profil → alerte » n'a jamais fonctionné
  (0 match, création gelée admin, profils démo). Deux issues : (a) livrer la vraie boucle (profils
  compte-scopés + `match_run` cronné) — un chantier ; (b) **le retirer** et garder juste le bloc
  « promoteurs actifs SITADEL » ailleurs (recoupe déjà Radar permis / Vélocité). **Mon avis : retirer**
  tant que la boucle n'est pas livrée — un outil démo dans un produit à 349 €/mois coûte cher.
- **La LISTE de Simulateur ZAN** (pas l'outil) — structurellement vide (ocs_ge sans poids). Retirer la
  liste, garder l'indicateur commune + le signal parcelle (le cœur véridique).
- Tous les autres ont une valeur unique prouvée — aucun autre retrait recommandé.

---

## 8. Ce que j'ai corrigé en Phase 1 (strictement factuel, fait)

**Mauve→vert (§5)** : `VIOLET`/`VIOLET_DIM` du registre repointés vers `mint`/`vert atténué` (point
unique) + ~100 classes Tailwind `violet`→`mint` dans les outils + badge copro rendu neutre + les 2
mentions texte « nombre violet »→« nombre vert ». Le Copilote reste mauve. Vérifié aux captures.

**Fuites de vocabulaire (§4)** — toutes retirées côté client :
- `labuse renouv` → « momentanément indisponible » (front) + « (table absente) » (503 API)
- `post-M7` + `mandat Auth & Plans` + `watch_zones/watched_parcels` → « L'abonnement… n'est pas encore
  actif » (carnet, servi)
- `Merci Facteur PRO — action Vic ; LABUSE_MERCIFACTEUR_*` → « L'envoi postal n'est pas encore
  disponible » (courrier statut, servi)
- « (SQL) » retiré du compteur Division · « PM »/« RNE » → « société introuvable au registre » /
  « dirigeant inactif (registre des entreprises) » · « nouveau run de scoring » → « mise à jour des
  données ». Tests durcis (assertent désormais l'ABSENCE de fuite : `test_note_abonnement_sans_fuite`,
  `test_statut_stub_sans_compte`).

**Scroll horizontal** : Rareté — colonnes flexibles (`min-w-0 flex-1 truncate` + largeurs fixes réduites
+ `overflow-hidden`), tient dans les 288 px.

**Mots coupés / deux lignes** : Comparateur — libellés de pondération courts (`PONDER_LABELS`,
`whitespace-nowrap`) ; bouton Matching « RÉEL · SITADEL » forcé sur une ligne (`shrink-0 whitespace-nowrap`
+ label `truncate`).

**Baromètre — trimestre en cours** : exclu en SQL (`date_trunc('quarter', …) < date_trunc('quarter',
CURRENT_DATE)`) côté DVF et Sitadel. Vérifié : le 1ᵉʳ trimestre affiché passe de `2026T3` (0) à
**`2025T4` (1209 mutations)**. **Observation (arbitrage)** : le retard de publication DVF (1-3 ans) rend
AUSSI 2026T1/T2 vides — ils sont absents naturellement (0 vente publiée), mais si des ventes 2026
arrivent partielles, il faudra plafonner la série au dernier trimestre « DVF-complet », pas seulement
exclure le trimestre courant. À décider.

**Garde-fous atteints** : tsc 0 · vitest 36 · build · **golden 119/119 (diff 0)** · pytest carnet+courrier
8/8 · le mauve ne subsiste que sur l'IA · captures `qa/m82/captures/outils-*`.

**Je n'ai PAS touché** (attend ton arbitrage) : réparations d'outils morts (promesses SQL, zan, proxy
servitudes/comparateur, renouvellement affichage, courriers), les 3 refontes (Annuaire, Remonter le
temps, Comparer), le tri de la page + l'en-tête.

---

## 9. Ce qui attend ton arbitrage (Phase 1 réparations + Phase 2 tri + Phase 3 refontes)

**Réparations (cause non structurelle, faciles) :**
- promesses — 1 ligne SQL (`s2.tier` hors CTE)
- servitudes + comparateur — +2 lignes proxy `vite.config.ts`
- renouvellement — distinguer 503 réel vs panne réseau
- scoreur-adresse — passer l'idu déjà résolu
- assemblage — plancher le score si SDP=0 / étage 0
- fantome — peupler ou retirer la branche « dirigeant inactif »
- division — automatiser le compute (pipeline), 24ᵉ commune, lookup par IDU (lève le BACKLOG M-ENTREE)
- quoi de neuf — lancer detect-events + clarifier les 3 circuits de veille
- zan — rebrancher la détection d'artificialisé (ou retirer la liste)
- carnet / courriers — reformuler la promesse (le champ `note` et « notre équipe la traite »)

**Refontes (maquette avant code) :** Annuaire PLU (bibliothèque, §3b) · Remonter le temps (parcelle
d'abord, §3c) · Comparer (clic carte, §3d).

**Le point le plus grave** : **Courrier propriétaire** promet « notre équipe la traite et reviendra vers
vous » alors que `courrier_demandes` n'est **lue par personne** (dead-letter, 0 SELECT/UPDATE dans tout
le repo) et l'envoi postal est **structurellement** indisponible (aucun prestataire branché). À dire
AVANT l'étape 1, ou à brancher un vrai traitement.

---

## Garde-fous (Phase 1)
tsc 0 · vitest vert · build vert · golden diff 0 (les outils LISENT) · captures avant/après ·
le mauve ne subsiste que sur l'IA · aucune régression portes fiche / Copilote. **NE PAS MERGER.**
