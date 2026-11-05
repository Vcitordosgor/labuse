# RETOURS-16 — compte-rendu

**Branche** `fix/retours-16` · worktree `~/Desktop/labuse-retours16` · ports 9610 (API) / 6810 (front)
**Modèle** Opus · **Prod** jamais touchée ni sondée · base Mac `labuse` (q_v20 servi)
**Périmètre** les 10 retours de Vic (11 points). Pas de merge. Injections et vigies NON touchées
(sessions INJECTION-SOLIDE-1 / CHASSE-1 A & B en parallèle).

Captures avant/après : `captures/retours-16/`. Mockup de référence : `captures/retours-16/maquette-crm-full.png`.

---

## Vue d'ensemble

| # | Retour | Fichier(s) | Preuve |
|---|--------|-----------|--------|
| P1 | Bouton « Dans le CRM · Propriétaire à identifier » touche les bords | `styles/index.css`, `fiche/Fiche.tsx` | padding `0 10px` + span `.truncate` (avant `padding:0`, texte 238/238 px) |
| P2 | Confirmation « Ajoutée à … » recouvre « 2 projets » | `fiche/Fiche.tsx` | toast global DA (bas-centre), `overlap:false` (avant `overlap:true`) |
| P3 | Survol menu des projets : nom noir sur fond sombre | `fiche/Fiche.tsx` | texte `rgb(232,239,234)` (avant ink `rgb(7,16,9)` sur fond transparent) |
| P4 | 6 boutons de la fiche | `fiche/Fiche.tsx` (+ store, `AnalyserAnnonce.tsx`) | Dossier · Étude de zone · Gabarit · Estimer · Remonter le temps · Courrier |
| P5 | Docs « Mes documents » boutons sur 1 ligne | `documents/DocumentsView.tsx` | `flex-nowrap` + colonne 320 px ; 0/99 lignes repliées à 1120 px |
| P6 | Menu « Fiche commune » refait comme les autres déroulants | `header/Header.tsx` | survol `bg-surface-3`, texte clair, `px-3 py-2` |
| P7 | Retirer bouton « Archivées » | `crm/Kanban.tsx` | bouton supprimé |
| P8 | Retirer la phrase « N parcelles suivies · … » | `crm/Kanban.tsx` | `<p>` supprimé |
| P9 | Projet → « → CRM » : les retenues n'arrivent pas | `api/projets.py`, `lib/api.ts`, `projets/ProjetKanban.tsx` | bout-en-bout prouvé (voir §P9) |
| P10 | Carte parcelle CRM selon la maquette | `crm/Kanban.tsx`, `api/app.py`, `lib/types.ts` | IDU · surface · secteur (commune · zone PLU) · note entière · Déplacer ; projet/proprio retirés |
| P11 | Outil Permis trop lent | `outils/ModulePanel.tsx`, `api/modules.py`, `models.py` | **1,19 s/6,5 Mo/50 074 pts → 0,12 s/148 Ko/715 pts** |

---

## P1 — marges du bouton « Dans le CRM · … »

`captures/P1-crm-button-AVANT.png` · `P1-P4-fiche-boutons-APRES.png`

Le bouton `.act` n'avait **aucune marge horizontale** (`padding:0`) : avec le libellé long
« ✓ Dans le CRM · Propriétaire à identifier » et `whitespace-nowrap`, le texte remplissait le
bouton **bord à bord** (mesuré : largeur 238 px, texte 238 px).

Fix (DA) : `styles/index.css` `.fiche-v6 .act` reçoit `padding:0 10px`, `min-width:0`,
`overflow:hidden` ; le libellé passe dans un `<span class="min-w-0 truncate">`. Le texte garde ses
marges intérieures et se **coupe proprement (…)** si l'étape est longue. Mesuré après : `padding:0px 10px`,
span `.truncate` présent. Effet collatéral mobile corrigé (voir §Mobile).

## P2 — toast « Ajoutée à … » ne recouvre plus rien

`captures/P2-toast-AVANT.png` · `P2-toast-APRES.png` · `P2-toast-APRES-visuel.png`

La confirmation était une bulle `absolute bottom-10 left-0` **dans le wrapper du bouton « + Projet »**
→ elle se dessinait **par-dessus** le bouton « ✓ N projets » (mesuré avant : toast top 573-604,
bouton 576-612, `overlap:true`).

Fix : la confirmation passe par le **toast global de la DA** (`App.tsx`, bas-centre, auto-disparition
4 s) via `setToast('✓ Ajoutée à « nom »')` ; la bulle locale est supprimée. Mesuré après : toast
`top 802` (bas de l'écran), `overlap:false` avec le bouton projet.

## P3 — survol du menu des projets

`captures/P3-projet-menu-hover-AVANT.png` · `P3-projet-menu-hover-APRES.png`

Le « menu des projets » = le menu déroulant du bouton **« + Projet »** de la fiche. Ses lignes
utilisaient `hover-fill-amber` : au survol, le texte passait en **encre sombre** (`rgb(7,16,9)`)
mais le fond restait **transparent** → noir sur fond sombre, illisible (reproduit et mesuré).

Fix : survol aligné sur les autres déroulants de l'app (menu compte) — `hover:bg-surface-3
hover:text-txt-hi` : seul le **fond** change, le texte **reste clair**. Mesuré après : texte
`rgb(232,239,234)`, fond `rgb(22,28,25)`. (Même correctif appliqué au bouton « Nouveau projet ».)

## P4 — six boutons de la fiche

`captures/P4-fiche-boutons-AVANT.png` · `P1-P4-fiche-boutons-APRES.png`

Avant : Dossier · **Financier (Bilan)** · **Apporteur** · **Pré-dossier PC** · Courrier · Remonter le temps.
Après (ordre exact demandé) : **Dossier · Étude de zone · Gabarit · Estimer · Remonter le temps · Courrier**.
Mesuré après : `['Dossier','Étude de zone','Gabarit','Estimer','Remonter le temps','Courrier']`.

- **Bilan / Apporteur / Pré-dossier PC** quittent la fiche ; ils restent accessibles depuis la page
  **Docs** (cartes de génération Bilan / Apporteur / Pré-dossier PC) et, pour le Financier, l'onglet
  **Outils**. Les trois fonctions mortes (`BanquierButton`, `ApporteurTile`, `PreDossierTile`) +
  l'import `BilanEcran` et les imports devenus inutilisés sont retirés (tsc `noUnusedLocals`).
- **Étude de zone** : `setEtudeZonePrefill({ idu, commune, … })` + `setModule('etude-zone')` (même pont
  que la §Quartier).
- **Gabarit** : `setModule('gabarit')` ; l'outil lit la parcelle sélectionnée (`selectedIdu`), déjà
  celle de la fiche ouverte.
- **Estimer** : nouveau prefill `annonceParcellePrefill` (store) consommé par `AnalyserAnnonce`
  (ouvre directement l'écran rapport parcelle sur la parcelle courante).

## P5 — « Mes documents » : boutons sur une seule ligne

`captures/P5-docs-wrap-AVANT.png` · `P5-docs-APRES.png`

Le conteneur d'actions était `flex-wrap` → sur les lignes « Sources modifiées depuis » (3-4 boutons)
ou en écran étroit, les boutons **passaient à la ligne**. Reproduit à 1120 px (hauteur de ligne 58 px).

Fix : `flex-nowrap justify-end`, boutons `shrink-0 whitespace-nowrap`, colonne actions élargie
270 → **320 px** (colgroup). Le badge « Sources modifiées depuis » garde sa colonne (distincte).
Mesuré après à 1120 px : **0/99** lignes modifiées repliées (toutes h = 26 px, 1 ligne, alignées à droite).

## P6 — menu « Fiche commune »

`captures/P6-fiche-commune-AVANT.png` · `P6-fiche-commune-APRES.png`

Les lignes utilisaient `hover-fill` (aplat vert plein + encre sombre) et `py-1.5` (espacement serré).
Fix : alignées sur le déroulant standard (menu compte) — `rounded-lg px-3 py-2` + survol subtil
`hover:bg-surface-3 hover:text-txt-hi`. Mesuré après : survol fond `rgb(22,28,25)`, texte
`rgb(232,239,234)`, padding `8px 12px`.

## P7 — bouton « Archivées » retiré

`captures/CRM-AVANT.png` · `CRM-APRES.png` — bouton supprimé de la barre CRM. Le panneau d'archives
(restauration) reste au dépôt mais sans entrée UI.

## P8 — phrase du CRM retirée

`captures/CRM-AVANT.png` · `CRM-APRES.png` — le `<p>` « N parcelles suivies · glisser une carte… ·
ajout depuis la fiche (+ CRM) » est supprimé ; seul le titre « CRM — pipeline de prospection » reste.

## P9 — Projet → « → CRM » (bout-en-bout)

`captures/P9-projet-kanban-AVANT.png` · `P9-vers-crm-toast-APRES.png` · `P9-crm-arrivee-APRES.png`

**Cause.** Le bouton « → CRM » ne faisait que **naviguer** (`setView('crm')`) — aucun appel CRM. La
synchro automatique `_sync_crm_retenue` ne se déclenche qu'au **geste Tinder** (`/parcelle/{idu}`) et,
même appelée, n'unarchive que les cartes **de CE projet** (`WHERE projet_id=:pid`). Une retenue créée
autrement (fusion de doublons, reprise de cadrage, import), **ou** dont une carte CRM avait été
archivée au nom d'un autre projet, n'atterrissait jamais dans le CRM.

Diagnostic chiffré (base Mac) : projet « touty » = 4 retenues, dont **1 absente** du CRM
(`97415000AB0001`, carte CRM archivée `projet_id ≠ 240`).

**Fix.** Nouvel endpoint `POST /projets/{pid}/vers-crm` : pour chaque retenue, **UPSERT large**
(`ON CONFLICT (compte_id, parcel_id)`) — insère si absente (colonne « Contact à préparer » sinon 1re
colonne du compte), **restaure** si archivée (quel que soit le projet d'origine), ne touche pas une
carte déjà active. Idempotent, **zéro doublon**. Le bouton appelle l'endpoint, affiche un toast
chiffré, puis ouvre le CRM.

Preuve bout-en-bout :
- **Avant** : `97415000AB0001` ABSENT ; total pipeline actif = 194.
- **Clic « → CRM » (UI)** : toast « 1 parcelle ajoutée au CRM · 3 déjà présentes. » + navigation CRM.
- **Après** : les 4 retenues dans le CRM ; `97415000AB0001` → « Contact à préparer » (la bonne
  colonne) ; total 194 → **195** (exactement +1).
- **Idempotence** : 2ᵉ appel `{total:4, ajoutees:0, deja:4}`, total reste 195, **0 ligne en double**
  (requête `GROUP BY … HAVING count(*)>1` = 0 ligne).
- `captures/P9-crm-arrivee-APRES.png` : recherche CRM = `97415000AB0001`, **une seule carte** en
  colonne « Contact à préparer ».

## P10 — carte parcelle du CRM selon la maquette

`captures/maquette-crm-full.png` (référence) · `CRM-AVANT.png` · `CRM-APRES.png`

Carte réécrite d'après la maquette validée : **IDU** (mono) + poignée de glissement · **surface** ·
**secteur (commune · zone PLU en vert)** · **note affichée en entier** (« + Note » si vide) ·
**« Déplacer vers »**. Le **nom du projet** et la **mention propriétaire** quittent la carte.
Glisser-déposer conservé (HTML5 natif, inchangé).

- **Zone PLU** : nouveau champ `parcel.zone_plu` servi par `/pipeline` (et `/pipeline/archived`),
  même source que la fiche (`parcel_zone_plu.zone_libelle`/`zone_fam`), **batché** dans
  `_prefetch_maps` (pas de N+1) + repli mono-carte `_zone_plu`.
- La légende « Note du JJ/MM » de la maquette est **omise** : aucune date par note n'est tracée en
  base — préférer omettre plutôt qu'inventer une date.

## P11 — outil Permis : ouverture < 1 s

`captures/P11-permis-AVANT.png` · `P11-permis-APRES.png`

**Cause.** L'outil ouvrait sur le segment « Tous » = **240 mois** → à `offset=0` l'API sérialise
**tous les points géocodés** de la base (plafond 60 000). La pagination serveur (`useInfiniteQuery`
+ `limit/offset` + `has_more`) et les filtres serveur (nature/commune/état) existaient déjà ; c'est
la **fenêtre par défaut** qui chargeait tout.

Mesures API (`/modules/permis`, base 50 809 permis) :

| | HTTP | temps | taille | points carte | items |
|---|---|---|---|---|---|
| **Avant** (`months=240`, défaut) | 200 | **1,19 s** | **6,49 Mo** | **50 074** | 200 |
| **Après** (`months=3` ≈ 90 j, défaut) | 200 | **0,12 s** | **148 Ko** | **715** | 200 |

**Fix.** L'outil ouvre sur « Récent » = **90 derniers jours** (`seg='cours'`, `months=3`) ; chip
« Récent » relibellé « 90 derniers jours » et son compteur passé à 3 mois. Réseau à l'ouverture
(vérifié) : la charge lourde carte/liste est `months=3` ; les requêtes `months=240` restantes sont
`count_only=true` (COUNT légers pour les chips « Tous »/« Achevés », pas de payload carte). Filtres
et recherche interrogent toujours le serveur. Objectif < 1 s **atteint** (0,12 s). Index
`ix_sitadel_permits_date` ajouté (`models.py`) + créé `CONCURRENTLY` sur la base Mac pour le filtre de
fenêtre + le tri `ORDER BY date DESC` (passage à l'échelle).

---

## Mobile 390 px

`captures/P1-P4-fiche-mobile390-APRES.png` · `P10-crm-mobile390-APRES.png`

- **Fiche** : à 390 px, les deux boutons d'action partageaient mal la largeur et « + Projet » était
  **rogné** (le `.truncate` du bouton CRM ne se déclenchait pas car les wrappers `flex-1` n'avaient pas
  `min-w-0` → la largeur min-content du span `nowrap` bloquait le flex-shrink). Correctif :
  `min-w-0` sur les deux wrappers `relative flex-1`. Mesuré après : boutons **142 px chacun** (égaux),
  **0 débordement**, libellé CRM coupé proprement ; grille 6 tuiles intacte (3×2).
- **CRM** : colonnes paginées (flèches 1-5/8), cartes tronquées proprement (IDU `truncate`, chips
  `flex-wrap`) — aucune casse de mise en page.

---

## Recette

- **Front (hook)** : `tsc -b` **0 erreur** · `vitest run` **305/305** (64 fichiers) · `vite build` **OK**.
  (1 test `PermisDouble` figeait l'ancien défaut « Tous » → mis à jour pour « Récent » / 90 j.)
- **Backend** : unitaires **2936 passed** (49 skipped, 0 échec) · DB (pipeline/projet/crm/permis)
  **57 passed** dont le nouveau `test_retours16_vers_crm.py` (réconciliation idempotente, restauration
  d'archive, **0 doublon** — a d'ailleurs révélé un piège `ON CONFLICT` sur `compte_id` NULL en
  local, corrigé par une réconciliation explicite NULL-safe).
- **Banc cohérence** (`scripts.coherence.banc --echantillon`, 120 parcelles + 24 communes, lecteur
  `fiche:` pointé sur l'API 9610) : 3377 comparaisons, **6 écarts** — tous `sdp_residuelle_m2`
  (fiche ∅ vs tuile), le **résidu SDP-tuile pré-existant** documenté dans ECARTS-ZERO-1 (correctif à
  la source `tiles.py`, rebuild MVT différé). **0 écart nouveau** introduit par ce mandat (aucun
  fichier SDP/tuile/potentiel touché). _(Piège : le lecteur `fiche:` du banc lit en HTTP sur
  `LABUSE_COHERENCE_API` — défaut `:8605` ; le pointer sur l'API 9610 sinon 100 % « erreur lecteur ».)_
- Captures avant/après des 11 points : `captures/retours-16/`.
- P9 prouvé de bout en bout (DB + UI, idempotent, 0 doublon).
- Temps d'ouverture Permis mesuré avant/après (objectif < 1 s atteint : 1,19 s → 0,12 s).
- Mobile 390 px vérifié (fiche + CRM).
- **0 écriture en base `pipeline_entries` dupliquée** (vérifié : `GROUP BY compte_id,parcel_id HAVING count>1` = 0).

## Décisions / dettes

- Base Mac `labuse` partagée avec d'autres sessions : la démo P9 a laissé `97415000AB0001` dans le CRM
  (donnée de test cohérente — une retenue correctement synchronisée).
- Index `ix_sitadel_permits_date` : présent dans `models.py` (bases neuves/test) + créé sur la base Mac ;
  **à créer en prod au déploiement** (`CREATE INDEX CONCURRENTLY IF NOT EXISTS`).
- **Dette : merge de la PR** (pas de merge dans ce mandat).
</content>
