# OUTILS-S2 — Successions · Courrier propriétaire · retours Dashboard / CRM / Carte

**Branche** `fix/outils-s2` · **base main** `ce77ae8d` · worktree `~/Desktop/labuse-s2` ·
ports **8465 / 5665** · **NON mergée**. Un commit par lot.

| Commit | Lot |
|---|---|
| `9c084099` | A — Successions : signal restreint aux formes où l'âge du dirigeant compte + UI épurée |
| `f3c9c436` | B — Courrier propriétaire : prix affiché + blocage terrain nu |
| `7837b90e` | C — Dashboard : source courbes, titre unique, cartes compactes, verrou G8 |
| `84ffaad7` | C (suite C.1) — courbes rattachées à RGE ALTI (pas de source distincte) |
| `4d30851c` | D — CRM note à hauteur fixe + légende carte fermée par défaut |

**Vérification** : tsc/build verts · **vitest 188/188** · pytest des zones touchées **verts**
(courrier 13, score_v13 11, outils_muscler1 6, circuit p_lot1/p4/p7, lot2_sources 41, sentinelle,
verrou couches WMTS). Un balayage large (`-k circuit/sources/verrou/seed`, 526 tests) laisse **8
échecs PRÉ-EXISTANTS** (dérives test↔code sur le vocabulaire des garanties « jamais vérifié·e » et
les libellés de cadence cron, + verrous « base réelle » dépendant de la fraîcheur runtime), dans des
zones **non touchées** par ce mandat (cf. §Vérification).

---

## Lot A — Successions à venir

### A.1 — Vérité (recompte des 5 lignes)

Endpoint `GET /modules/successions` (`api/modules.py:1000`), table `parcel_veille_succession`
(Score V v1.3, `scoring/score_v.py`). Vérifié en direct (API :8465) et par SQL sur `labuse`.

| Ligne | Source | Millésime | Recompte | OK / écart |
|---|---|---|---|---|
| **Dirigeant (âge)** | RNE INPI `pm_dirigeants` → `v.dirigeant_age` | RNE lu **06/07/2026** (`data_sources.last_sync_at`, servi au bandeau) | aîné des dirigeants PP ≥ 70 ans | **OK** — le nom et la date de naissance RNE ne sont **jamais** exposés (privacy) : seul l'âge |
| **Société (SIREN → parcelles)** | DGFiP `parcelle_personne_morale` (dénomination + SIREN), jointe par `idu` | fichiers PM DGFiP | PM à **SIREN confirmé** (`CONF_SIREN_DIRECT`, jamais un match par nom) | **OK** |
| **Résiduel « Estimé »** | `p_model_ext_dataset.sdp_residuelle_m2`, `annee = max` = **2026** | feature store (moteur de la fiche) | enveloppe = capacité PLU − bâti existant ; `—` si hors PLU | **écart de libellé** : ce n'est **pas** `parcel_residuel` run 10 mais le **feature store** `p_model_ext_dataset` (année 2026), qui porte le même résiduel que la fiche. Attribution corrigée dans le « i » |
| **Millésime du signal** | `parcel_veille_succession.computed_at` | **09/08/2026** (dernier run Score V) | date du calcul, globale (snapshot mono-run) | **OK** — conforme au mandat (« signal RNE INPI au 09/08/2026 ») |
| **Radar 3-7 ans** | constante `VEILLE_SUCCESSION_HORIZON = "3-7 ans"` (`score_v_constants.py:173`), doctrine A0 (Vic) | — | libellé codé, jamais un fait par parcelle | **OK** — l'écran ne dit **jamais** « en succession » |

**Total avant restriction : 7 129 parcelles** (7 122 par âge, 7 seulement par « SCI dormante »).

### A.2 — Le signal était faux pour les PM non familiales — restriction

Le signal « dirigeant ≥ 70 ans » se déclenchait pour **toute** forme juridique, y compris les
sociétés de capitaux et institutionnelles : **SA d'économie mixte NORDEV** (forme `SEM`, dirigeant
84 ans), **SA** à conseil, sociétés d'HLM… Une SEM/SA/HLM ne « succède » pas quand son président
vieillit — sa direction se renouvelle statutairement.

**Restriction (décision Vic 25/09) : formes civiles + familiales + agricoles** — celles où une
personne physique vieillissante porte réellement le patrimoine. La **SCI dormante** reste toujours
éligible (elle EST une SCI). Comparaison **EXACTE** du libellé DGFiP `forme_juridique`
(= `forme_dgfip` du scoring) — jamais une sous-chaîne (« SC » ne capte pas « SCA »).

| Forme | n (par âge) | Retenue ? | Motif |
|---|---:|:---:|---|
| **SCI** — société civile immobilière | 3 711 | ✅ | patrimoine familial |
| **GFA** — groupement foncier agricole | 821 | ✅ | patrimoine familial agricole |
| **SARL / EURL** | 807 | ✅ | souvent familiale |
| **SC** — société civile | 581 | ✅ | holding familial |
| **SNC** — société en nom collectif | 120 | ✅ | responsabilité personnelle |
| **SCEA** — société civile d'exploitation agricole | 35 | ✅ | familiale agricole |
| **SCM** — société civile de moyens | 11 | ✅ | patrimoine porté par des personnes physiques |
| **EARL** — exploitation agricole à resp. limitée | 6 | ✅ | familiale agricole |
| **SA** — société anonyme (incl. HLM) | 729 | ❌ | société de capitaux, direction renouvelée |
| **SAS** — société par actions simplifiée | 250 | ❌ | société de capitaux |
| **SEM** — société d'économie mixte (**ex. NORDEV**) | 19 | ❌ | public-privé, pas de « succession » |
| **SCA** — société en commandite par actions | 19 | ❌ | société de capitaux |
| **AUPM** — autre personne morale | 10 | ❌ | forme non confirmée familiale |
| **ASS** — association | 2 | ❌ | pas de patrimoine successoral d'un dirigeant |
| **GIE** — groupement d'intérêt économique | 1 | ❌ | structure inter-entreprises |

**Compte avant / après : 7 129 → 6 099 servis** (1 030 formes de capitaux/institutionnelles
écartées). Prouvé en direct : `GET /modules/successions` renvoie **total 6 099** ; la SEM NORDEV
(dirigeant 84 ans) est **absente** de la liste servie.

**« SCI dormante » — définition exacte** (`score_v.py:famille_b`, constantes
`score_v_constants.py:192-193`) : SCI (forme DGFiP `SCI` **ou** nature juridique RNE `6540`) créée il
y a **≥ 20 ans** (`SCI_DORMANTE_AGE_ANS`) **et** sans mise à jour RNE depuis **≥ 5 ans**
(`SCI_DORMANTE_INACTIVITE_ANS`, ou aucune date de mise à jour). **Source : registre RNE (INPI)**
(`date_creation`, `date_mise_a_jour_rne`). Ce n'est **pas** « pas de mutation » ni « pas de dépôt de
comptes » (ce dernier, BODACC, renforce le motif quand il existe mais ne le définit pas).

**Où c'est corrigé** : constante partagée `VEILLE_SUCCESSION_FORMES` ; `veille_succession_eligible()`
prend la forme (corrige les runs Score V futurs) **et** filtre au **service** (`api/modules.py`,
`v.sci_dormante OR upper(pm.forme_juridique) = ANY(:formes)`) — corrige le snapshot courant **sans
re-run** de l'île (interdit en session parallèle).

### A.3 — UI (décisions Vic)

- **« Préparer les courriers » RETIRÉ** — le pont Courrier et l'état associé disparaissent.
- **Cases à cocher RETIRÉES** — la sélection multiple ne servait **qu'**au courrier → supprimée.
- **« Détail et méthode » (bas-gauche) RETIRÉ** — son contenu (le signal, ce qu'il n'est pas, les
  chiffres Sourcé/Estimé) est **replié dans le « i » de l'en-tête**. Ce qu'il contenait est
  intégralement conservé, juste déplacé.
- **Cartes lisibles** conservées : IDU · résiduel **Estimé** · commune · surface · zone · société ·
  SIREN · « dirigeant N ans » **ou** « SCI dormante » (+ « aucun dépôt de comptes depuis N ans »
  BODACC quand disponible — le registre ne publie pas de « dormante depuis N ans » par parcelle).

**Captures** : `A-successions-panel.png` (panneau épuré, 6 099, formes civiles/familiales),
`A-successions-apres.png` (vue complète).

---

## Lot B — Courrier propriétaire

### B.1 — Vérité (CV0441, source unique)

La lettre est **composée serveur** (`courrier_compose.py`), aperçu front = PDF (`/courrier/composer`).
Chaque fait lu de `_synthese()` sur les **mêmes tables que la fiche**.

| Fait de la lettre / verso | Source (fonction) | Table | CV0441 (Saint-Paul) | OK ? |
|---|---|---|---|---|
| Surface | `_synthese` | `parcels.surface_m2` | **743 m²** | OK (= fiche) |
| Zone | `_synthese` | `parcel_zone_plu.zone_lib` | **U3c** | OK (= fiche) |
| Bâtie / non bâtie | `_synthese` | `parcel_filtre_bati` | **bâtie** → ouverture B | OK (mandat : « déjà bâtie ») |
| « 42 mutations sur 3 ans » | `_synthese` | `dvf_mutations_parcelle` (rayon 500 m, 3 ans) | N mutations dans le périmètre | OK (même maille que le marché) |
| Adresse d'envoi | `courrier_adressage` | `parcel_adresse.ban_voie` | BAN de la parcelle | OK |

**« Adressage à l'occupant, non nominatif »** : confirmé. Aucun nom de personne physique ne fuit —
le destinataire PP est **« À l'occupant »** à l'adresse BAN (`resoudre_destinataire`). Il n'existe
**aucune** table de propriétaires particuliers en base (MAJIC absent) : le nominatif est
techniquement impossible pour les PP.

**Compteur « VOS DEMANDES n° 12-17 » et « Projets → Mes courriers » : MÊME table**
`courrier_demandes` (le n° affiché = `rang_compte`, rang **propre au compte**, pas l'`id` global qui
fuiterait le volume plateforme). Le suivi client (`ProjetsPanel`) et l'aperçu wizard lisent la même
source.

### B.2 — La signature (réponse au mandat)

**Ce que fait le code** : la lettre porte `_signature(exp)` où `exp` vient de la **marque blanche du
compte** (`comptes.marque` → `signataire`, `raison_sociale`, `coordonnees`). Quand la marque est
vide, repli : « Cette étude vous est offerte par **LABUSE** » + « Cordialement, » **sans signataire**.
**Constat** : aucun compte n'a de marque renseignée et **aucun éditeur n'existe** → en pratique
**100 % des lettres tombent sur le repli LABUSE**, exactement l'observation du mandat.

**Doctrine tranchée par Vic (25/09) : « LABUSE écrit et envoie ».** La lettre reste signée « offerte
par LABUSE » ; le « Cordialement, » sans nom est **assumé** (LABUSE est l'expéditeur). → **Aucun bloc
signataire ajouté à la Rédaction. Aucun changement de code** pour ce point (documenté ici).

### B.3 — Le prix (décision Vic)

**Revient sur COURRIER-2 Lot 5** (« aucun prix affiché »). Le tarif unitaire est de nouveau **servi
et affiché**.

| Élément | Valeur | Source |
|---|---|---|
| Tarif unitaire TTC | **4,04 €** (= coût prestataire 2,69 € × marge 1,5) | `courrier.tarif(db)["prix_client_eur"]`, coût de `config.py:164` ou paramètre admin — **jamais codé dans le composant** |
| Ligne à l'étape 3 (avant « Demander l'envoi ») | « **N courrier × 4,04 € = total € TTC** — impression, mise sous pli, affranchissement, suivi » | `ModulePanel.tsx`, lit `/courrier/statut.tarif_unitaire_eur` |
| Confirmation « Demande transmise » | **même montant** repris (N = `demande.n`) | idem |
| Repli si tarif absent | « Tarif communiqué sous 24 h ouvrées. » | — |

Prouvé en direct : `/courrier/statut` renvoie `tarif_unitaire_eur = 4.04` ; l'étape 3 affiche
« **1 courrier × 4,04 € = 4,04 € TTC** ». Capture `B-prix-etape3.png`.

### B.4 — Terrain nu (décision Vic)

Un pli « à l'occupant » n'atteint personne sur une parcelle sans bâti ni adresse. À **l'ajout** d'un
destinataire, l'adressabilité est résolue d'abord ; un terrain **nu / sans adresse** → **ajout
REFUSÉ** avec message clair + lien vers le **Courrier SPF** (ouvre la fiche, qui porte le pli SPF
d'identification du propriétaire). L'**opposition** reste traitée au dépôt (motif à part) ; une panne
réseau ne crée **jamais** un faux blocage (repli : on ajoute).

| Parcelle | Bâti | `code` (resolution) | Comportement |
|---|---|---|---|
| **BZ1065** (bâtie) | oui | `null` (type `occupant`) | **ajoutable** — « À l'occupant » |
| **AC0433** (Les Avirons, nue) | non | **`nu`** | **ajout refusé** : « Terrain nu, aucun occupant à qui écrire — passez par le Courrier SPF » + « Ouvrir la fiche (Courrier SPF) → » |

Codes machine ajoutés (`courrier_adressage.py`) : `nu` / `sans_adresse` / `sans_canal` / `inconnue`
(bloquent l'ajout) vs `opposition` (au dépôt). Prouvé en direct + capture `B-terrain-nu-panel.png`.

---

## Lot C — Dashboard (page Données)

### C.1 — Sources à 92 après courbes de niveau + profil altimétrique

**Finding** : le **profil altimétrique** utilise l'API RGE ALTI (source **« RGE ALTI (altimétrie) »**,
déjà cataloguée — c'est pourquoi il n'a pas créé de source). Les **« Courbes de niveau »**
(overlay WMTS `ELEVATION.CONTOUR.LINE`) étaient servies **sans rattachement** à une source.

**Vérité** : `ELEVATION.CONTOUR.LINE` est un **canal de diffusion WMTS** de la donnée **RGE ALTI** (les
courbes sont dérivées du modèle altimétrique). Sa **source EST RGE ALTI**, déjà cataloguée — comme le
profil. **Le compte de 92 est donc CORRECT** : les deux fonctions dérivent d'une source existante, ce
n'est pas un oubli. Un overlay WMTS live **n'est pas un réservoir** de données (pas de table servie,
pas de couche `spatial_layers`) → pas une ligne de vitrine distincte.

> ⚠ **Nuance vs mandat** : le mandat suggérait « si non, l'ajouter (source ELEVATION.CONTOUR.LINE) ».
> J'ai d'abord ajouté une ligne distincte ; elle **cassait 3 verrous du catalogue** (V2a pont
> `NOM_VERS_SLUG`, sentinelle « toute source classée », pont↔carte couvrent le seed) qui exigent
> qu'une source de vitrine soit un **réservoir avec sa couche**. La bonne réponse (rattachement à RGE
> ALTI + note au `technical_notes` de RGE ALTI) respecte le modèle. **Si Vic veut malgré tout une
> ligne cataloguée distincte pour l'overlay**, il faudra étendre le modèle du catalogue aux sources
> « live sans réservoir » (hors-vitrine + classification sentinelle). Posé à Vic.

**Verrou** : `tests/test_outils_s2_couches_source.py` — tout overlay WMTS proxy
(`ortho_proxy._CONTOUR_LAYER`) doit avoir sa source rattachée dans `seed_sources.SOURCES`. Ferme la
brèche laissée par `check_sources_declarees` (qui ne couvre que les couches vecteur via
`spatial_layers`). ✅ vert.

### C.2 — Titre « Données » en double

Le titre + sous-titre était rendu **deux fois** : l'en-tête générique d'`AdminView`
(`AdminView.tsx:484` — commun à **toutes** les sections admin) **et** le bloc `.cx-tete` de
`Circuit.tsx`. **Doublon retiré** de `Circuit.tsx` : seul l'en-tête d'AdminView porte le titre. ✅
Capture `C-dashboard-donnees.png` (un seul titre). Snapshot `Donnees.test.tsx` mis à jour.

### C.3 — Sonde de nuit / Agents : cartouches → boutons compacts

Les deux **gros cartouches** deviennent **deux boutons compacts sur une ligne** : « **Sonder
maintenant** » et « **Envoyer les agents ▾** », chacun suivi d'un « **i** » qui **replie/déplie**
l'explication actuelle (cadence, dernier passage, coût, plafond, prochain dimanche). Le texte ne
disparaît pas — il se replie dans le popover. Menu de portée + confirmation de coût + progression des
agents **conservés**. Captures `C-sources-cartes-compactes.png` (boutons compacts — le badge y
affiche « Sources 93 », pris **avant** la correction C.1 : la ligne contour temporaire ; après revert
le compte est **92**, l'évidence C.3 = la disposition des boutons, inchangée) et
`C-sonde-i-popover.png` (le « i » ouvre l'explication).

### C.4 — « À corriger : V1c » vs « Décider — verrou G8 cassé » : un ou deux ?

**Réponse : deux mécanismes DIFFÉRENTS, correctement distincts — mais G8 était mal présenté.**

- `casses` = **tous** les verrous cassés (les 22 verrous **+** les 8 garanties G1-G8, joués par
  `/verifier`). `bloquants` = `casses` **moins** l'ensemble `AVERTISSEMENT = {"G8"}`.
- Le **bandeau « À corriger »** lit **`bloquants`** → **exclut G8**. « V1c » y figure quand un verrou
  V-bloquant est cassé (déploiement refusé).
- La ligne **« Décider — verrou G8 cassé »** (onglet À faire) lisait **`casses`** → **incluait G8**, en
  **ROUGE « le déploiement refuse tant que ça tient »** — **contradiction** : G8 est un
  **avertissement NON bloquant** (fraîcheur de veille / sources sans contrôle ; `deploy -w G8`).
- **État live** : `circuit_journal` dernier contrôle = `casses = ["G8"]` → **un seul verrou cassé
  aujourd'hui, et c'est un avertissement.** (« V1c » du mandat provient d'un ancien message de tâche
  verrous, d'un run antérieur ; c'est un vrai bloquant **quand** il est cassé, distinct de G8.)

**Correctif** : constante **unique** `VERROUS_AVERTISSEMENT = {"G8"}` partagée
`circuit_resume` ↔ `api/dashboard` (source unique). En « À faire », G8 est rendu en **AMBRE, non
bloquant** : « avertissement de fraîcheur de veille — le déploiement PASSE (deploy -w) », déplacé dans
la section ambre (l'invariant rouge-avant-ambre tient). La ligne « verrous cassés » du RÉSUMÉ ne
compte que les **bloquants**. → Plus de contradiction : un bloquant (V1c) et un avertissement (G8)
apparaissent chacun à sa place, avec la bonne formulation. Vérifié live : la ligne dit désormais
« **Décider — verrou G8 (avertissement, non bloquant)** ».

**Toggle « ne montrer que ce qui cloche » RETIRÉ** du diagramme (`CircuitDiagram.tsx`, décision Vic).

---

## Lot D — CRM et Carte

### D.1 — CRM : note longue qui casse la colonne

La zone de note d'affichage (`crm/Kanban.tsx` `CardNote`) avait `overflow-wrap:anywhere` mais **aucune
hauteur max** → une note « [GB-TEST] » très longue **étirait la carte**. **Correctif** : hauteur fixe
**`max-h-[4.5rem]` (~4 lignes) + `overflow-y-auto overscroll-contain`**, texte toujours coupé en
lignes. **La carte garde sa taille** quelle que soit la note. Prouvé (note test de ~600 px) :
`clientHeight = 70 px`, `scrollHeight = 595 px` → clampée + défilement interne. Capture
`D-crm-note-hauteur-fixe.png`.

### D.2 — Carte : légende fermée par défaut

La légende des couches (`CouchesTuyau.tsx` `TuyauLegend`) est désormais **fermée par défaut** tant que
seules les **deux couches par défaut** (famille `reperes` : limites parcelles / limites communes) sont
actives ; elle **s'ouvre d'elle-même dès qu'une 3ᵉ couche** est activée
(`nonDefautActif = actives.some(c => !COCHE_DEFAUT(c))`). Une fois **ouverte/fermée à la main**, le
choix de l'utilisateur **prime pour la session** (`ouvertManuel` non nul l'emporte sur
l'auto-ouverture). Logique dérivée pure, typée (tsc vert).

> ⚠ **Capture non produite** : la carte MapLibre **ne s'initialise pas en headless** (WebGL absent) —
> la `TuyauLegend`, montée dans `MapView`, ne rend donc pas de DOM hors navigateur réel. Vérifié :
> `document.querySelector('canvas.maplibregl-canvas')` = absent → légende jamais montée en test
> headless. La logique est couverte par le typecheck et le raisonnement d'état ; à confirmer d'un œil
> en navigateur graphique.

---

## Vérification (détail)

- **Frontend** : `tsc -b` **exit 0**, `vitest run` **188 passed (47 fichiers)**.
- **Backend (zones touchées, verts)** : `test_courrier` 13, `test_score_v13` 11, `test_outils_muscler1`
  6, `test_outils_s2_couches_source`, `test_circuit_p_lot1` / `p4_afaire` / `p7_lot1` / `p7_lot4`,
  `verrous/test_lot2_sources` 41, `test_sentinelle`.
- **Balayage large** (`-k "circuit or sources or verrou or seed"`, 526 tests) : **8 échecs
  PRÉ-EXISTANTS**, hors périmètre du mandat :
  - `verrous/test_garanties` g2/g4/g5/g6 — dérive test↔code du vocabulaire d'état (`("gris",
    "jamais vérifiée")` côté code vs `("rouge", "jamais vérifié")` attendu par le test) — `etat_reservoir`
    **non touché** ;
  - `test_cron1_registre::test_agents_sources_dimanche` — libellé de cadence (`"hebdo (dim)"`),
    registre cron **non touché** (déjà noté pré-existant en mémoire projet) ;
  - `test_circuit1_lot6`, `test_circuit2_lot2`, `verrous/test_lot1_tables` — verrous « base réelle »
    dépendant de la fraîcheur runtime des sondes/contrôles.
  Aucun ne touche `circuit_resume` / `dashboard` (mes seules modifications de ce périmètre = la
  constante `VERROUS_AVERTISSEMENT`, même valeur `{"G8"}`).

## Captures — `captures/outils-s2/`

| Fichier | Contenu |
|---|---|
| `A-successions-panel.png` | Successions épuré : 6 099, cartes formes civiles/familiales, sans cases ni pont Courrier ni tiroir méthode |
| `A-successions-apres.png` | Vue complète Successions |
| `B-prix-etape3.png` | Étape 3 : « 1 courrier × 4,04 € = 4,04 € TTC » avant « Demander l'envoi » |
| `B-terrain-nu-panel.png` | Ajout refusé sur terrain nu (AC 0433) + lien « Ouvrir la fiche (Courrier SPF) » |
| `C-dashboard-donnees.png` | Page Données : **un seul** titre ; onglet À faire (G8 en avertissement) |
| `C-sources-cartes-compactes.png` | Onglet Sources : **boutons compacts** Sonder / Envoyer les agents + « i » |
| `C-sonde-i-popover.png` | Le « i » ouvre l'explication de la sonde (repliée, non supprimée) |
| `D-crm-note-hauteur-fixe.png` | Note CRM très longue clampée à ~4 lignes (défilement interne) |

*Aucun nom de personne physique dans les captures (Successions = PM nommées ; Courrier = « À
l'occupant »).*

## Hors mandat (rappel)

Le **tarif lui-même** (Vic décide — ici 4,04 € = défaut config, affiché tel quel) · le scoring · les
autres outils · **le merge**.
