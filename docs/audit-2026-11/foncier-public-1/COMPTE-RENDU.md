# FONCIER-PUBLIC-1 — équipements publics & foncier public dans l'Analyse LABUSE

Branche `fix/foncier-public-1` (worktree `~/Desktop/labuse-foncier`, ports 10020/7220). **Aucun merge,
aucun accès prod.** Suite du point 7 de ECRANS-NOV-2 (`INVESTIGATION-FONCIER-PUBLIC.md`) : le moteur
classait des campus de lycées, des hôpitaux et du foncier d'État parmi les parcelles les mieux
notées. Il ne lisait ni le propriétaire ni l'usage. Ce lot applique les deux décisions de Vic.

## 0. Substrat — intégration de `feat/ecrans-nov-2`

Les livrables (case « Inclure le foncier public » à l'étape **Choisir**, drapeau servi par
`/analyse/scenarios`, puce sur la **carte**) vivent dans des fichiers qui n'existent QUE sur
`feat/ecrans-nov-2` (`AnalyseScenario.tsx`, endpoint `/analyse/scenarios` par `FiltreCriteres`). La
branche, partie de `main`, **intègre `feat/ecrans-nov-2`** (merge, seul `app.py` en conflit, résolu
automatiquement). Ce n'est PAS un merge vers `main` (toujours interdit) : c'est le socle sur lequel le
lot se greffe. `main` apporte en plus RESIDUEL-2 (reconstruction) ; la branche a donc les deux.

## 1. Les deux règles (décisions de Vic)

1. **Équipement public en place → « Hors de ce projet »**, cause `équipement public : <type>`, dans
   les DEUX scénarios (bâti conservé ET reconstruction). Verdict sourcé (BPE/INSEE), prioritaire sur
   le résiduel réglementaire. **Les commerces et services privés de la BPE ne comptent pas.**
2. **Terrain public SANS équipement → la bande est GARDÉE**, avec un **drapeau « foncier public »**.
   À l'étape Choisir, une case **« Inclure le foncier public », décochée par défaut**, le fait entrer
   dans la sélection ; une **puce « Foncier public »** (liseré bleu + légende) le marque sur la carte.
3. **Le Signal n'est jamais touché** : la vue Prospection relaie l'état servi, inchangé — l'équipement
   public n'y force aucun « Hors projet » (le drapeau reste seulement informatif).

### Propriétaire public (foncier public)

Source unique `proprietaire_type.PUBLIC_DGFIP_GROUPES` = groupes DGFiP **1 (État), 2 (Région),
3 (Département), 4 (Commune), 9 (Établissement public)**, lus de `parcelle_personne_morale.groupe`.

### Équipement public — codes BPE RETENUS et EXCLUS

La BPE (INSEE, `spatial_layers kind='amenite_bpe'`, points) porte le domaine `dom`, le sous-domaine
`sdom` et le type fin `typequ`. La classification est figée dans **`labuse.scoring.equipement_public`**
(mirroir Python + expression SQL identique, source unique pour l'adaptateur, le backfill et les tests).

**RETENUS** (équipement public en place → Hors projet) :

| sdom | Domaine BPE | Catégorie servie | Exemples |
|---|---|---|---|
| A1 | Services publics | **administration** (mairie, EPCI, préfecture, justice/tribunaux, France services) ; **sécurité** si `typequ` A104*/A140* (gendarmerie, commissariat) | Tribunal judiciaire, Communauté d'agglo, Commissariat |
| C1,C2,C3,C4,C5,C7 | Enseignement | **enseignement** (écoles, collèges, lycées, supérieur, université, résidences/restaurants U) | Lycée Leconte de Lisle, Université, CROUS |
| D1 | Santé et action sociale | **santé** (établissements de santé) | CHU, Centre Hospitalier Ouest Réunion |
| F1 | Sports, loisirs, culture | **sport** | Bassin, stade, plateau multisport |
| F2 | Sports, loisirs, culture | **loisirs** (plein air) | Baignade surveillée |
| F3 | Sports, loisirs, culture | **culture** | Bibliothèque, archives départementales |

**EXCLUS** (commerces / services privés / hors périmètre — la parcelle n'est PAS marquée) :

| sdom | Pourquoi exclu |
|---|---|
| A2 | Banque, bureau de poste, pompes funèbres (services, pas équipement public d'usage du sol) |
| A3 | Automobile/moto (garages, contrôle technique, location) — privé |
| A4 | Artisans du bâtiment — privé |
| A5 | Restaurants, coiffure, beauté, vétérinaires — privé |
| B1,B2,B3 | Commerces — privé |
| C6 | Formation continue (organismes majoritairement privés : « A ZOT FORMATION »…) |
| D2 | Professions de santé libérales (médecins, infirmiers, kinés…) — privé |
| D3 | Pharmacies, laboratoires, transfusion, thermal — privé |
| D4,D5,D6,D7 | Action sociale, médico-social, hébergement social — hors « santé publique » nommée par Vic ; public/privé non séparable depuis la seule BPE → exclus par prudence |
| E1 | Transports (taxis, aéroport) — hors périmètre |
| G1 | Tourisme (agences de voyage, hôtels) — privé |

Un terrain portant plusieurs équipements prend la catégorie **dominante** (`PRIORITE` : santé >
enseignement > administration > sécurité > culture > sport > loisirs). Un snack (A5) ou un cabinet
libéral (D2) sur l'emprise d'un campus est **ignoré** (classé NULL).

## 2. Avant / après sur l'île (run servi `q_v20`, conservation)

`scripts/foncier_public_backfill.py` applique l'overlay aux lignes déjà persistées (les quantités
enrichies sont conservées ; seul le statut d'un équipement passe « Hors de ce projet »).

| Mesure | Valeur |
|---|---:|
| Parcelles portant un équipement public retenu | **2 198** |
| … dont bande A/B avant | 520 |
| … qui **SORTENT** (n'étaient pas déjà « Hors projet ») | **1 457** |
| Lignes passées « Hors de ce projet » (2 scénarios) | 4 396 |
| Foncier public SANS équipement (**drapeau**, bande gardée) | **34 747** |
| … dont bande A/B | 2 673 |
| Île — bande A/B (conservation) **avant → après** | 49 980 → **49 460** (− 520) |
| Île — « Hors de ce projet » (conservation) après | 145 949 (+ 1 457) |

Équipements qui sortent, par catégorie : sport 915 · enseignement 649 · santé 208 · administration
151 · loisirs 146 · culture 93 · sécurité 36.

**Lecture.** Peu de parcelles sortent (2 198 équipements, dont 520 seulement étaient A/B) : la BPE est
ponctuelle et beaucoup d'équipements sont déjà sur des parcelles non constructibles. Le gros du
« foncier public » (34 747) n'est PAS un équipement : il garde sa bande et n'est que signalé, invisible
par défaut (case décochée).

## 3. Les trois cas du mandat (vérifiés, `tests/test_foncier_public.py`)

| Parcelle | Attendu | Observé |
|---|---|---|
| **97411000DO0049** (campus de lycées, Région) | Hors projet, équipement public | `OUTSIDE_OBJECTIVE`, cause `EQUIPEMENT_PUBLIC:enseignement`, `foncier_public=true` (keep ET rebuild) |
| **97412000BM1251** (communale nue, zone U, Saint-Joseph) | bande gardée + drapeau | `ESTIMATED` bande A, `foncier_public=true`, `equipement_public=null` |
| **97412000CI0056** (privée + commerce B) | inchangée | `ESTIMATED` bande B, `foncier_public=false`, `equipement_public=null` |

## 4. Mise en œuvre

- **`equipement_public.py`** — classification (source unique) : `categorie` / `dominante` /
  `categorie_sql` / `priorite_sql`.
- **Moteur `scenarios_v2.py`** — `ScenarioRecord.public_facility` / `public_land` ; en potentiel, un
  équipement public renvoie « Hors de ce projet » (cause `EQUIPEMENT_PUBLIC:<cat>`) AVANT le résiduel,
  dans les deux scénarios ; les drapeaux sont portés par tous les statuts et les deux objectifs. La
  vue Prospection retourne en amont : le Signal n'est pas touché.
- **Adaptateur `scenarios_v2_build.py`** — `_foncier_public()` : join spatial point-dans-parcelle
  (`geom_2975` indexé) + propriétaire public ; drapeaux servis au contrat de sortie.
- **Persistance `scenarios_v2_persist.py`** — colonnes `public_facility` / `public_land` (table
  additive) ; la case « Inclure le foncier public » (`_foncier_clause`) sort le terrain public sans
  équipement des effectifs, de la liste ET des IDU carte ; `n_foncier_public` et `idus_foncier_public`
  servis.
- **Endpoint `/analyse/scenarios`** — paramètre `inclure_foncier_public` (défaut `false`), dans la clé
  de cache des effectifs.
- **Front** — case « Inclure le foncier public » à l'étape Choisir (décochée, avec compte) ; pastille
  « Équipement public : <type> » / « Foncier public » sur les cartes ; liseré bleu + légende
  « Foncier public » sur la carte (`parcels-foncier` / `ile-foncier`, pilotés par `scenarioPaint`).
- **Backfill `scripts/foncier_public_backfill.py`** — overlay sur le run `q_v20` déjà persisté.

## 5. Limites assumées (jamais masquées)

- **BPE ponctuelle** : un point d'équipement dans une parcelle marque TOUTE la parcelle. Correct pour
  un campus/hôpital ; un petit agrès de fitness public sur une grande parcelle mixte la marquerait
  aussi. Cas rares, à affiner si besoin (empreinte bâtie plutôt que point).
- **Action sociale (D4–D7)** et **formation continue (C6)** : exclues faute de séparation
  public/privé fiable depuis la seule BPE ; Vic a nommé « santé publique », pas « action sociale ».
  Révisable.
- Le backfill met à jour le run `q_v20` LOCAL ; l'adaptateur + la persistance produisent nativement
  les colonnes au prochain run (aucune table historique touchée).
