# M12 — VAGUE QA 1 : RAPPORT DE VAGUE

**Mode** : autonome A→H. **CC n'a rien mergé** — 9 branches poussées, Vic merge lui-même en `git merge --no-ff`.
**Base** : `main` (5e50113). **Golden de référence** : 116/116 (fichier `reports/m6-audit/golden/golden-parcelles.json`, run servi `q_v7_defisc`).

---

## 1. ARRÊTS DURS

**Aucun.** Les trois conditions d'arrêt dur ne se sont pas déclenchées :

- **A3 — lift `×N` : le calcul N'EST PAS faux.** Vérifié en base : `mult_base = p_raw / taux_base` (`pipeline.py:260`), appliqué correctement. Les 5 parcelles de tête portent `p_raw = 1.0` (saturation haute du modèle) et `taux_base = 0.015636`, donc `1/0.015636 = 63.97` → affiché `×64.0`. Le « même ×64.0 pour les rangs 1-2-3 » est **réel** (égalité sur P), pas un bug d'affichage ni de calcul. **Aucune correction du scoring. La vague a continué.**
- **Golden rouge inexpliqué** : jamais. Un run à 84/116 est survenu **une fois** (lot E) — cause identifiée = **API crashée « Connection refused » sous charge concurrente** (5 agents + 6 golden simultanés sur un Postgres CPU-bound), reproduit 116/116 en isolation. Artefact d'environnement, **jamais « réparé »**.
- **Suppression irréversible** : aucune. C-bis archive avant de retirer, ne touche à aucune donnée ni à l'historique git.

---

## 2. DÉCISIONS PRISES PAR CC (défaut réversible R1 / le doute ne supprime pas R2)

| Point | Lot | Choix retenu | Alternative écartée | Comment revenir en arrière |
|---|---|---|---|---|
| QA-14 lexique | B1 | « rang P » → **« classement »** ; ×N + « plus probable » ; libellés centralisés `strings.ts` | Garder le jargon | Éditer `frontend/src/lib/strings.ts` |
| QA-16 « 92 » | B2 | Retiré de la liste, **conservé sur la fiche** | Le garder partout | Remettre `<CompletudeRing>` dans `ResultCard` |
| QA-35 modèle | B4 | Avertissement DVF visible, **technique replié** | Tout visible | `<details>` → contenu inline |
| QA-37 fraîcheur | B5 | « À VÉRIFIER » → **« Cadence non sondable »** (≠ douteuse) | Réduire à 2 statuts | `strings.ts` |
| QA-36 ANC | B7 | **GARDÉ** (A8 : utilisé par Flash) | Retirer avec les piscines | — |
| QA-12 algo | B8 | Libellé **« Comprendre le classement »** | « Comment LABUSE classe » / « Sur quoi repose ce classement ? » | `CLIENT.algo.bouton` |
| QA-20 bouton carré | A7/G2 | **GARDÉ** (marche en mode commune) + état désactivé clarifié | Supprimer | — |
| QA-05..11 panneaux | C | Tiroir replié, légendes fusionnées, verdict **replié** | Retirer C7 | chevrons |
| QA-09 colorisation | C5 | Famille U/AU/A/N (palette élargie) | Par zone précise U1a/U1c | data/tuiles = suite |
| QA-18 Dirigeant 65+ | E1 | **Masqué** (A5 : 0 résultat, données absentes) | Supprimer le code | retirer `.filter(d => d.key !== 'dirigeant')` |
| QA-19 chips verdict | E2 | **Retirés du bandeau** (doublon), chiffres conservés | Les garder | remettre `<TierChips>` |
| QA-15 plafond 500 | E3 | **Pagination** « Charger plus » (offset) | Scroll infini | `useQuery` limit 500 |
| QA-33 délai étapes | F4 | **Inchangé** — aucun délai artificiel (c'est le vrai aller-retour LLM) | Fabriquer un raccourci | — |
| QA-32 rattacher projet | F7 | **Multi-projets autorisé**, bouton violet (vs Pipeline menthe) | Interdire | doc F |
| QA-39 suppression colonne | H2 | **Déplacement obligatoire** des cartes + dernière colonne indéboulonnable | Perte silencieuse | — (jamais) |
| D1 autocomplete | D | **API BAN publique** (pas d'endpoint interne existant) | Créer un proxy interne | `banAutocomplete()` = point unique |

---

## 3. À RELIRE PAR VIC — TEXTE CLIENT (recopié intégralement)

> Source unique appliquée : `frontend/src/lib/strings.ts` (lots B) et `frontend/src/lib/layers.ts` (`LAYER_INFO`, lot C). Vic réécrit là.

### B1 — Lexique (voir aussi `docs/LEXIQUE_CLIENT.md`)
- `rang P` → **« Classement »** — infobulle : « Classement de la parcelle sur les 428 239 analysées : n°1 = la plus prometteuse. »
- `×N` → nombre + **« plus probable »** — infobulle : « Cette parcelle est classée N fois plus haut que la moyenne du parc analysé. Plafond ×64 = certitude maximale du modèle. »
- `Score Q` → **« Potentiel constructible »** (0-100). `SDP` → **« Surface constructible restante »** (m²).
- le `92` → **« Complétude des données »** (fiche seule).

### B4 — Bloc modèle (visible)
« Les ventes récentes mettent 1 à 3 ans à apparaître dans les bases publiques (DVF). Les niveaux de prix les plus récents sont donc provisoires — mais le CLASSEMENT ENTRE PARCELLES, lui, reste fiable. » + repli « détail technique ».

### B5 — Fraîcheur
- **À jour** — « donnée dans le rythme de publication de la source ».
- **Mise à jour dispo** — « une version plus récente est probablement parue ».
- **Cadence non sondable** — « ce producteur n'expose pas de calendrier vérifiable automatiquement » ; infobulle : « La donnée affichée est bien la dernière version que nous ayons ingérée — ce n'est pas une donnée douteuse. »
- En-tête (faute corrigée) : « Chaque source **a** sa fraîcheur maximale, prouvée. »

### B7 — En-tête preuve
Titre : « Ce que LABUSE mesure — et ne devine pas ». Intro : « La seule question sérieuse face à une app qui parle d'IA : "est-ce qu'elle invente ?". La réponse est un chiffre mesuré et une garantie d'architecture. »
- Adresses (BAN) — **99,99 %** — méthode : rattachement parcelle ↔ adresse certifiée BAN sur l'île entière.
- Recherche NL → filtres — **jamais de SQL généré** — chaque traduction validée par schéma (garantie d'architecture).
- Assainissement (ANC) — **calé Office de l'eau** — zonages SPANC + EGOUL RP à l'IRIS (signal, pas diagnostic ; conservé car utilisé par Flash).

### B8 — Comprendre le classement (à valider avant prod)
Titre « Comment LABUSE classe les parcelles » — 4 sections : (1) mesure la **mutabilité** (pas la valeur ni la constructibilité) ; (2) entraîné sur l'historique réel des mutations 974 × signaux publics ; (3) le ×N (plafond ×64 = certitude max) ; (4) ne dit PAS que le propriétaire veut vendre, ni le prix, ni la rentabilité.

### C2 — Pastilles « i » des couches (`LAYER_INFO`)
- **zonage** : « La carte officielle des zones du PLU (urbaine, à urbaniser, agricole, naturelle) telle que publiée par la commune — les grands aplats de couleur, sans découpage à la parcelle. »
- **zonage_parcelle** : « Chaque parcelle prend la couleur de sa zone du PLU. En zoomant, ou en cliquant une parcelle, le code exact de la zone (par ex. U1a, 1AUc) s'affiche. »
- **zonage_colorise** : « Colorie d'un coup TOUTES les parcelles selon leur type de zone (urbaine, à urbaniser, agricole, naturelle) — sans avoir à cliquer parcelle par parcelle. Une lecture d'ensemble du potentiel de constructibilité. »
- **parcelles** : « Les parcelles cadastrales, colorées selon l'avis de LABUSE (les plus prometteuses ressortent). C'est la couche de travail principale. »
- **ppr** : « Les zones exposées à un risque naturel connu (inondation, mouvement de terrain, littoral…) inscrites dans un Plan de Prévention des Risques — utile pour écarter tôt un terrain contraint. »
- **parc** : « Le périmètre du Parc national de La Réunion : à l'intérieur, l'urbanisation est très restreinte voire interdite. »
- **limites** : « Le simple tracé du contour de toutes les parcelles, sans couleur — pour lire le découpage cadastral sur le fond de carte. »
- **communes** : « Les frontières officielles entre les communes (le trait vert) — pour se repérer et savoir de quelle mairie dépend un terrain. »
- **anru** : « Les quartiers inscrits dans un programme de renouvellement urbain (ANRU) : secteurs prioritaires où des opérations d'aménagement sont soutenues par l'État. »
- **cinquante_pas** : « La bande littorale des "50 pas géométriques" (81,20 m depuis le rivage), un régime foncier propre à l'outre-mer où la constructibilité est très encadrée. »
- **equipements** : « Les équipements du quotidien à proximité (mairie, écoles, santé, commerces, transport, sport). Sur la fiche d'une parcelle, LABUSE indique la distance en mètres jusqu'à chaque équipement le plus proche. »

---

## 4. NON FAIT / BLOQUÉ (avec raison)

- **F4 (délai entre étapes)** : rien à réduire — **aucun `setTimeout` artificiel** dans le parcours ; le délai EST l'aller-retour LLM réel. Fabriquer un raccourci aurait trafiqué l'appel IA. Consigné, non fait.
- **C5 colorisation par zone précise (U1a/U1c)** : livré au niveau **famille U/AU/A/N** (palette élargie, lisible). Le par-zone-exact demande un travail data/tuiles hors périmètre (468 valeurs `zone_lib` dont bruit numérique). Repli autorisé par le mandat, rien de cassé.
- **B6 refonte forme complète des fiches source** : corrections de fond faites (vocabulaire, dash orphelin, lisibilité gris-sur-gris) ; une refonte visuelle plus poussée de la grille relève de la validation à l'œil de Vic.
- **E1 architecture filtres via IA** : proposée, **non implémentée** (Vic arbitre). Cible réutilisable = `useApplySearch`/`/ia/search` (partagé), pas le builder Vues (part au spin-off).
- **D1** : pas de proxy BAN interne créé (aucun n'existait) — API BAN publique réutilisée, point de reroutage unique.
- **Dette pré-existante notée** (non causée par la vague) : ordre de modules pytest (`test_audit_secu` avant `test_api`) pollue un cache LRU d'auth → reproduit sur main nu.

---

## 5. ORDRE DE MERGE CONSEILLÉ + CE QUE VIC REGARDE À L'ŒIL

Toutes les branches partent de `main`. Vic merge dans l'ordre qu'il veut ; conflits attendus signalés.

| Ordre | Branche | Lot | À regarder à l'œil | Conflit attendu |
|---|---|---|---|---|
| 1 | `audit/m12-a` | A + **ce rapport** | docs seulement (audit) | — |
| 2 | `feat/m12-b-preuve` | B | Sources : bloc modèle scindé, fraîcheur reformulée, preuve cliquable ; liste : « 92 » parti, ×N « plus probable » ; « Comprendre le classement » | **ResultsSection.tsx, SourcesPage.tsx** avec E et G |
| 3 | `feat/m12-c-carte` | C | Tiroir Couches replié, pastilles i, colorisation zonage, légendes fusionnées, verdict replié | LeftPanel.tsx avec E (léger) |
| 4 | `feat/m12-f-projet` | F | Jauge 5 segments (démarre à gauche), + Décrire ouvre direct, kanban post-recherche, bouton Projet violet sur fiche | Fiche.tsx avec D/G (léger) |
| 5 | `feat/m12-d-adresse` | D | Autocomplétion adresse (frappe), scoreur déplacé dans Outils, placeholder 3 entrées | Header.tsx avec E ; api.ts avec E |
| 6 | `feat/m12-e-filtres` | E | « + Filtre » : Dirigeant 65+ absent, Potentiel/Surf. constr. renommés ; bandeau sans chips ; « Charger plus » | **ResultsSection.tsx** avec B ; Header.tsx avec D |
| 7 | `fix/m12-g-finitions` | G | Misclic → pas de fausse erreur ; « 2000-2005 » sur une ligne ; Imprimer parti ; CRM colonnes lisibles | SourcesPage.tsx avec B ; MapView/Toolbar avec C |
| 8 | `feat/m12-h-crm` | H | Colonnes CRM renommables/ajout/suppr/reset ; **supprimer une colonne peuplée demande où déplacer** | Kanban.tsx avec G (léger) |
| 9 | `fenetre/m12-spinoff` | C-bis | Vues disparue du rail, nav cohérente ; fiche/Flash intacts | voir section C-bis ci-dessous |

**Conflit principal à anticiper** : `panel/ResultsSection.tsx` entre **B** (retire le 92 + libellés tri, dans `ResultCard`/`SORTS`) et **E** (retire les chips + pagine, dans `list`/footer/`TierChips`). Zones différentes → résolution manuelle simple. `SourcesPage.tsx` entre **B** (refonte en-tête) et **G** (retire Imprimer) — G ne touche que le bouton Imprimer.

**Vérification indépendante CC** : build `tsc+vite` 0 erreur sur chaque branche ; golden **116/116** re-prouvé en isolation ; H — 9 tests `test_crm_columns` re-exécutés par CC (dont « never lose a card ») = **9/9 pass**.

---

## C-bis — Spin-off « Vues » (détail)

- **Archive AVANT tout retrait, poussée** : tag `archive/vues-m12-5e50113` (= état `main` avec Vues intacte) + branche `fenetre/m12-spinoff` poussée pré-retrait. **Socle de la future marque « Plein Sud »/« Soley » — rien perdu.**
- **Retiré (code actif)** : front `SegmentsPage.tsx`, entrée rail « Vues » + icône, routage `App.tsx` + alias `#pg=vues`, bloc segments d'`api.ts` ; back `api/segments.py` (désenregistré), route `/ia/segments-search` + `ai/nl_segments.py`, package `segments/*`, routes `/ortho/validation*` (gardé `/ortho/equipements/{idu}`), CLI `segments-*`/`ingest-catnat`/`nl-eval` ; config `config/segment_presets.yaml`, `deploy/cron.d/catnat`. **32 fichiers, −4138 lignes.**
- **Gardé (partagé, A8)** : `IAStub`, `useApplySearch`, `/ia/search`, `nl_semantics`/`nl_aggregate`, `/ortho/equipements/{idu}`, `moteurs`/`rarete`/`M22Programme`, `plans.py`, toutes les tables socle + `detection_ortho.yaml` + scripts d'ingestion.
- **Laissé en place par doute (R2)** : table `ortho_detections` (lue aussi par `scoring/p_model` via SQL direct, indépendant des routes retirées) + `segment_presets`/`segment_preset_counts` — **tables endormies, aucun DROP, aucune donnée touchée, aucun historique réécrit.**
- **Vérif CC** : diff = **0 nouvelle instruction destructive** (tous les `DELETE`/`DROP` du diff sont des lignes RETIRÉES). Routes prouvées sur API bootée du code C-bis : `/segments` → 404, `/ia/search` → 200/422 (gardée). **Golden 116/116 en dev_mode** (sans dev_mode : throttle 60 rpm → 108/116, identique à main nu 84/116 dans les mêmes conditions — artefact d'environnement, jamais réparé).
- 1 échec pytest (`test_auth::test_local_par_defaut_tout_ouvert`) = artefact d'ordre de suite pré-existant (passe en isolation, zéro couplage Vues).

---

## Annexe — le piège golden de cette vague (pour la prochaine)

Le golden hammer >60 requêtes/min → **rate-limit 60 rpm** (`config.py:70`) → fiches dégradées (`a_score` absent) → FAIL en cascade (8, 32… selon la fenêtre). **Reproductible sur `main` nu** (84/116 constaté). **Solution : lancer le golden avec `LABUSE_DEV_MODE=1`** (quotas/rate-limit désactivés) ou via `LABUSE_QA_ALLOWLIST`. Jamais « réparer » le golden — c'était l'environnement, pas le code. Chaque branche de la vague est **116/116 PASS** vérifiée hors throttle.
