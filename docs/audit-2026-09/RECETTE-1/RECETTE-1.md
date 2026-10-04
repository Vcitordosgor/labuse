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
| E1 · E4 | ✅ FAIT | |
| E2 | ⏳ NON FAIT | retrait encart Capacité — sites repérés (voir § session 2) |
| E3 | ⏳ NON FAIT | cases cochées par défaut (sémantique hash/vues) |
| F1–F4 (règles outils) | ⏳ NON FAIT | refonte d'état transverse aux outils |
| G + H1–H16 (outils) | ⏳ NON FAIT | audit branchement + refontes outil par outil |
| B (vitesse carte) | ⏳ NON FAIT | mesure avant/après (en dernier, ordre Vic) |

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
