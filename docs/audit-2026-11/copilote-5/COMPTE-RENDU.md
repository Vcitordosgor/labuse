# COPILOTE-5 — le Copilote atteint toute l'app

- **Branche** : `fix/copilote-5` · worktree `~/Desktop/labuse-copilote5` · ports 9550 (API) / 6750 (front).
- **Portée** : le moteur du Copilote (`copilote_v2/`). **Pas de merge, aucun accès prod** (merge = geste de Vic).
  Deux autres sessions tournent (SILENCE-1, JOHN-TAYLOR-2) : **seul le Copilote est touché**.
- **Lu d'abord** : `docs/audit-2026-11/copilote3/COMPTE-RENDU.md`, `docs/audit-2026-11/copilote-4/COMPTE-RENDU.md`.
- **Règle gravée de COPILOTE-3, intacte** : *le Copilote n'affirme que ce qu'un outil porte ; sans champ,
  il dit « je n'ai pas cette donnée »*. Le verrou anti-invention (`_verdicts_coherents`, `_anti_invention`)
  n'est **pas touché** — preuve : `test_copilote3_verdicts.py` **14 passed** et les **20 questions
  COPILOTE-3 rejouées à l'identique** (0 web, 0 source suspecte).

---

## Étape 0 — état des lieux (avant COPILOTE-5)

### Quel modèle répond, avec quels paramètres

Le Copilote **n'a pas un seul modèle** : il enchaîne des étapes DÉTERMINISTES (aucun modèle) et, seulement
au besoin, des appels modèle par `kind` (registre `ai_models.SURFACES`, résolu par `model_for`).

| Étape | `kind` (ia_log) | modèle AVANT | paramètres |
|---|---|---|---|
| Routage d'intention (7 intents) | `copilote-route` | `claude-haiku-4-5-20251001` | `max_tokens=400`, `temperature=0` (haiku 4.5 **accepte** `temperature`) |
| Sélection d'outil (chemin OUTIL) | `copilote-select` | `claude-haiku-4-5` | idem |
| **Formulation** (phrase servie) | `copilote-formule` | `claude-haiku-4-5` | `max_tokens=350`, `temperature=0` |
| Web — connaissance / recherche | `copilote-general` / `copilote-web` | `claude-haiku-4-5` | web_search natif |
| Préparer un script | `copilote-prepare` | `claude-haiku-4-5` | — |
| **Chemins déterministes** (résumé, champ précis, copropriété, PPR, règle PLU, constructibilité) | — | **AUCUN modèle** | les valeurs sont LUES du robinet ; le modèle, s'il tourne, ne fait que la phrase |

Le repli et la `temperature` passent par `ai.core.complete` : un identifiant `not_found` rejoue **une fois**
sur son repli (`REPLI_MODELES`), et `temperature` est **omis** pour les modèles qui le refusent
(`NO_TEMPERATURE_MODELS`).

### Les outils qu'il peut appeler (catalogue `OUTILS`, 13) et ce qu'ils couvrent

`compter_parcelles` (comptage à facettes) · `compter_permis` (Sitadel) · `parcelles_par_entreprise`
(patrimoine d'une PM, DGFiP/SIREN) · `fiche_parcelle` (surface·commune·zone·copro·PM, chaque fait sa
source) · `stats_commune` (SRU + INSEE logement) · `delais_instruction` (Sitadel) · `marche` (DVF/DHUP) ·
`compter_piscines` · `destination_zone` (PLU, calibré) · `regles_plu_zone` (hauteur/emprise/reculs
calibrés) · `statut_ppr` (DEAL) · `loyer_parcelle` (OLL) · `recherche_web`.
Plus les **champs de fiche déterministes** lus du robinet `exports.robinet_fiche` (le MÊME producteur que
l'écran et le Dossier) via `resume_fiche.champ_precis` — **mais seulement ~9 des ~30 champs** étaient
mappés (propriétaire, taxe d'aménagement, taxe foncière, zone, risques, pente, exposition, surface, SDP).

### Ce qu'il NE pouvait PAS atteindre

- **La résolution d'une adresse en parcelle** : rien ne transformait « 3 chemin de la Citerne » en IDU.
  L'omnibox de l'app (barre de recherche) sait le faire (BAN + cadastre + propriétaire, endpoint
  `/api/recherche/suggest`), mais le Copilote **n'y était pas branché**.
- **La référence cadastrale courte** (« BZ 1065 ») hors IDU 14 caractères.
- **~20 champs de fiche** présents au robinet mais non exposés en Q&R : adresse, emprise/hauteur/bâti,
  toiture, piscine, fibre, viabilisation, transport, servitudes/dispositifs, prix du terrain, ventes DVF,
  quartier/IRIS, équipements de proximité, statut du PLU, surface libre, pollution (CASIAS)…
- Les **outils graphiques du menu** (Gabarit, Remonter le temps, Comparer, Assemblage, Étude de zone) :
  atteignables seulement par une **voie cliquable** (refus-voie), jamais répondus dans le chat — c'est
  correct (un plan 2D ne se rend pas en texte), mais non documenté comme tel.

### Comment une question est routée — et pourquoi « 3 chemin de la Citerne » partait en « réponse générale »

Ordre réel (`answering.answer`) : méta-tours déterministes (résumé/doute/provenance/anaphore) →
chemins fiche déterministes **si un IDU est présent** (PPR, règle, loyer, copropriété, constructibilité,
champ précis, résumé) → sinon `classify` (routeur haiku, 7 intents) → `_answer_with_route`
(EXPLIQUER → web ; QUESTION → chemin fiche, puis `_select_tool` → outil / web / `_sans_outil`).

« **Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La Montagne** » :
1. **aucun IDU de 14 caractères** dans le message → tous les chemins fiche déterministes sont sautés
   (ils exigent un IDU) ;
2. `classify` → QUESTION ; `_chemin_fiche` ne trouve ni IDU ni commune-résumé (« La Montagne » n'est pas
   l'une des 24 communes — c'est un quartier de Saint-Denis) → `None` ;
3. `_select_tool` ne connaît aucun outil « adresse → parcelle » → `_sans_outil` ;
4. `_sans_outil`, sans IDU ni donnée, **bascule sur `_general`** → **RECHERCHE WEB** (« réponse générale,
   hors données LABUSE »).

La parcelle existe pourtant (`97411000BZ1065`) et l'omnibox la retrouve en une frappe. Le trou était
**l'absence de résolution d'entrée** dans le Copilote.

---

## Ce que COPILOTE-5 change

### 1. La résolution d'entrée devient la PREMIÈRE étape (`copilote_v2/resolveur.py`, neuf)

Les **trois familles de l'omnibox** deviennent la première étape du Copilote, **au MÊME point de calcul**
que la barre de recherche (on appelle `api.recherche._sugg_adresse` / `_sugg_cadastre` — jamais une 2ᵉ
source, jamais une requête maison). Déterministe, **aucun appel modèle**.

- **Adresse (BAN)** : on extrait la portion adresse du message (mot-voie + numéro de tête), puis on
  résout par **relaxe par jetons** — on retire le dernier mot tant que la recherche ne rend rien (un
  quartier hors toponyme officiel, « La Montagne » pour 97417 Saint-Denis, ne fait plus tout échouer).
- **Référence cadastrale courte** (« BZ 1065 ») : ancrée par « parcelle/section/cadastr… », section en
  **majuscules** (jamais « plus **de** 1000 m² » pris pour la section « DE 1000 »).
- **Propriétaire** : la voie existante (`parcelles_par_entreprise`) est conservée (même producteur).

**Une seule parcelle** → l'IDU est injecté dans le contexte et le flux fiche reprend (PPR/règle/loyer/
copropriété/constructibilité/champ/résumé). **Plusieurs candidates** → le Copilote les **propose** (jamais
un tir au hasard) : le numéro exact porté par chaque candidate départage (« 3 Chemin… » = la bonne), sinon
la liste s'affiche.

> **Rejeu du mandat** : « Donne-moi toutes les infos sur la parcelle 3 chemin de la Citerne, 97417 La
> Montagne » → **IDU 97411000BZ1065 résolu, fiche complète servie** (plus aucune réponse générale).

### 2. Couverture complète : chaque section de la fiche a son champ Copilote (`resume_fiche.py`)

Le tableau `_CHAMPS` passe de **9 à ~30 champs**, chacun LU du **MÊME extracteur `robinet_fiche`** que
l'écran et le Dossier (le point de calcul unique — jamais une 2ᵉ source), avec **la vraie source par
champ** (`_SOURCE_CHAMP`) et un rendu lisible (jamais un dict brut au client — filet de sécurité).

| Section de la fiche | champ Copilote AVANT | champ Copilote APRÈS (extracteur robinet) |
|---|---|---|
| En-tête (6 tuiles) | résumé (déjà) | résumé (déjà) |
| Identité | — | **adresse** (`adresse_ban`, BAN) |
| Terrain | pente, exposition | + **surface libre** (`surface_libre_sol_m2`) |
| Bâti | — | **emprise bâtie, hauteur du bâti, nb bâtiments, toiture, piscine** |
| Urbanisme | zone | + **statut du PLU** (`statut_plu`), **servitudes/dispositifs** (`dispositifs_parcelle`), **RTAA** |
| Risques | aléas/PPR | + **pollution des sols** (`casias_statut`) |
| Réseaux | — | **fibre** (`fibre_parcelle`), **viabilisation** (`viabilisation_verdict`), **transport** (`distance_arret_m`) |
| Fiscalité | taxe aménagement, taxe foncière | (inchangé) |
| Marché | loyer (voie dédiée) | + **prix du terrain secteur**, **ventes DVF**, **dernier prix d'achat** |
| Quartier | — | **quartier/IRIS** (`iris_quartier`), **équipements de proximité** (`equipements_proximite_liste`) |
| Potentiel | SDP restante | + **potentiel constructible**, **capacité en logements**, DPE |

Les **outils graphiques du menu** (Gabarit 2D, Remonter le temps, Comparer, Assemblage, Étude de zone)
restent servis par une **voie cliquable préremplie** (un plan ne se rend pas en texte) — comportement
existant, désormais assumé et documenté.

Correctif de robustesse : `_quel_champ` matche les mots-clés **courts acronymiques** (« plu », « ppr »,
« dpu », « dpe » ≤ 3 car.) avec **bornes de mot** (fini « plu » happé par « **plu**s proche »), et garde la
sous-chaîne pour les mots plus longs (« servitude » attrape « servitudes », « viabilis » attrape
« viabilisée »).

### 3. Modèle : Opus 5.5 pour la formulation, repli 4.x (`ai_models.py`)

`copilote-formule` passe de Haiku à **`claude-opus-5-5`** (le plus capable, comme John), **repli
automatique `claude-opus-4-8`** si `not_found` (câblé dans `core.complete`). Opus **refuse** `temperature`
→ **omis** (`NO_TEMPERATURE_MODELS` contient opus-5-5 ET opus-4-8). Routage et sélection restent sur Haiku
(extraction, pas rédaction). **Le modèle ne calcule ni ne choisit aucun chiffre** : le verrou
anti-invention de COPILOTE-3 est inchangé. Test mis à jour : `test_copilote2_memoire.test_modeles_par_chemin`.

### 4. « Réponse générale » bridée (`answering._sans_outil`, `_est_domaine_labuse`)

Une question qui porte sur une **parcelle, une adresse, un propriétaire ou une commune de La Réunion** ne
part **JAMAIS** sur le web. Si aucun outil LABUSE n'a répondu, le Copilote le **dit honnêtement — ce qu'il
a cherché et où** (`_RIEN_TROUVE_LABUSE`), au lieu de basculer en recherche générale. Le web reste réservé
aux questions **hors données LABUSE** (un maire, une loi — routées en amont vers `recherche_web`, elles
n'atteignent pas ce point). Vérifié : « des termites sur la parcelle… » → honnête (pas de web) ; « qui est
le maire de Saint-Benoît ? » → web ; « c'est quoi la loi Girardin ? » → voie b.

### Forme (inchangée, conforme au mandat)

Les **trois points d'attente en mauve**, la couleur du Copilote et le texte **« Le Copilote cherche votre
réponse… »** (`frontend/.../ui.tsx`) sont **conservés** — aucune ligne de front touchée (`git status`
frontend : vide). La proposition de candidates voyage par la structure `clarification` déjà rendue par
l'écran (+ un champ `candidats` structuré pour un futur clic).

---

## Recette

`docs/audit-2026-11/copilote-5/recette.py` (sortie `captures/copilote5/recette.txt`) — base de DEV, run
servi `q_v20`, lecture seule.

- **6 parcelles témoins** atteintes par les **trois familles** : `97411000BZ1065` (adresse, Saint-Denis),
  `97416000DW0279` (adresse, Saint-Pierre), `97411000AW0692` (propriétaire SCI ALOE / IDU),
  `97404000AV0167` (IDU, L'Étang-Salé), `97416000CD0448` (IDU, Saint-Pierre), `97410000AN0347` (IDU,
  Saint-Benoît) — **4 communes**.
- **25 questions** — par adresse / IDU / propriétaire, **≥ 5 outils** (fiche champ+résumé, `statut_ppr`,
  `regles_plu_zone`, `parcelles_par_entreprise`, `compter_parcelles`, `marche`, `stats_commune`),
  **2+ communes** : **TOUT VERT** (0 contrôle en échec). Garde anti-web vérifiée sur chaque question
  LABUSE-locale ; sources correctes par fait.
- **Preuve de résolution** : les 4 cas (adresse exacte → IDU, adresse 2ᵉ commune → IDU, adresse vague →
  5 candidates proposées, référence cadastrale → IDU).
- **20 questions COPILOTE-3 rejouées** → **20/20 identiques** (0 web, 0 source « cadastre » sur un verdict
  non cadastral) ; verrou qualitatif refuse toujours l'hallucination de la fiche legacy.

### Hook

- **Back** (base de dev / `labuse_test`) : `test_copilote3_verdicts.py` **14 passed** · suite `-k copilote`
  **162 passed / 13 skip** · `test_copilote2_memoire.py` **5 passed** (nouvelle politique de modèle) ·
  `test_ai_*` / `test_dashboard` / `test_john_registre` / `test_retours7` **66 passed**.
- **Front** : **non touché** (`git status` frontend vide). `tsc -b` **0 erreur** · `vitest` **268 tests
  passed, 0 échec de test** ; les 8 suites « carte » en échec d'IMPORT sont l'**artefact de node_modules
  emprunté en lien symbolique** (vite refuse le worker `maplibre-gl` hors racine) — identique au constat
  des sessions précédentes, **sans rapport avec le diff** (aucun fichier front modifié ; avec
  `node_modules` en place = 301/301).

## Fichiers touchés (`copilote_v2/` + modèle + 1 test)

| Fichier | Nature |
|---|---|
| `src/labuse/copilote_v2/resolveur.py` | **neuf** — résolution d'entrée (adresse BAN / cadastre), MÊME grammaire que l'omnibox |
| `src/labuse/copilote_v2/answering.py` | résolution branchée avant les chemins fiche ; web bridé (`_est_domaine_labuse`, `_RIEN_TROUVE_LABUSE`) ; mots-clés résumé élargis |
| `src/labuse/copilote_v2/resume_fiche.py` | `_CHAMPS` 9 → ~30 champs (chaque section de la fiche), `_SOURCE_CHAMP`, rendus, `_quel_champ` hybride |
| `src/labuse/ai_models.py` | `copilote-formule` → `claude-opus-5-5` (repli `opus-4-8`, `temperature` omise) |
| `tests/test_copilote2_memoire.py` | `test_modeles_par_chemin` (nouvelle politique : formulation Opus, extraction Haiku) |
| `docs/audit-2026-11/copilote-5/recette.py` + `COMPTE-RENDU.md` | neufs |

*Recette jouée le 2026-11-04. Branche `fix/copilote-5`, commit sur la branche. Pas de merge, pas de push,
aucun accès prod. Merge = geste de Vic.*
