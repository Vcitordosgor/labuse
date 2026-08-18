# AUDIT M119 — LE FLUX PROJET, DE LA CRÉATION AU TRI

**Branche** : `audit/m119-flux-projet` — audit pur, aucune correction, jamais mergé.
**Méthode** : lecture croisée (4 sondes parallèles + relecture manuelle des fichiers cités).
Chaque constat porte son `fichier:ligne`.

---

## SYNTHÈSE POUR VIC (la réponse à la question centrale)

> « les parcelles présentes le sont suite aux filtres qu'il a cliqués »

**Aujourd'hui, non — pas les filtres de la carte.** Les parcelles d'un projet viennent
d'un **run automatique** (`proposer`) qui rejoue le **cadrage** du projet (la *fiche*)
sur le run servi. Le cadrage produit par le parcours M114 ne contient, en pratique, que
**deux critères** : la **commune** et le **programme** (→ SDP minimale). Les 44 facettes
de la carte (`FiltreCriteres`) ne touchent **jamais** le projet.

Les trois vérités structurantes :

1. **Deux systèmes de filtres parallèles, pas un.** La carte a `FiltreCriteres` (44
   facettes, `app.py:1170`). Le projet a une *fiche* de cadrage (~7 champs,
   `projet_schema.py:38`). Aucune n'alimente l'autre ; le projet **dérive** un
   sous-ensemble minuscule (`derive_filtres`, `projets.py:134`) : `communes`, `sdpMin`,
   `flagsExclus`. Rien d'autre de la richesse de la carte n'entre.

2. **Le parcours M114 ne collecte que 2 critères utiles au run.** `ParcoursProjet.tsx:53`
   fige `type_programme:'logements'`, ne collecte **jamais** de contraintes (donc
   `flagsExclus` reste vide), et range budget + critères libres dans des champs
   **jamais lus** par le moteur. Le cadrage servi = `{commune, sdpMin}`.

3. **Les parcelles d'un projet ne sont écrites que par 4 chemins, tous dans `projets.py`**
   (`proposer`, `chercher-plus`, `ajouter`, `fusionner`). Le moteur du Copilote
   (RECHERCHE) n'a **aucun** lien avec `projet_parcelles` (grep `copilote/` = 0). Il
   n'existe donc **pas** de « run d'instruction cadrage → moteurs → shortlist » branché
   sur le projet : le seul « run » est `proposer`, déclenché **à l'ouverture** de l'écran.

---

## PHASE 1 — LE PARCOURS DE CRÉATION (M114)

### 1.1 Le composant et ses étapes

Le parcours vivant est **`frontend/src/components/projets/ParcoursProjet.tsx`** (211 l.),
monté par `ProjetsPanel.tsx:13`. **`ProjetEntretien.tsx`** (l'ancien cadreur IA
conversationnel) n'est **importé nulle part** (`grep import ProjetEntretien` = 0) → **code
mort**.

5 étapes, dans l'ordre (`ParcoursProjet.tsx:95-101`, rendu `125-178`) :

| # | Étape | Champ(s) exact(s) | Type | Obligatoire ? |
|---|-------|-------------------|------|---------------|
| 0 | **Nom** | `nom` (state `:32`) | texte | Non — repli `Projet {commune}` (`:51`) |
| 1 | **Commune** | `commune` (`:33`) | `<select>` du référentiel `getCommunes()` (`:29`) | **OUI** — bloque (`peutAvancer`, `:61`) |
| 2 | **Programme** | `mode` `'logements'\|'surface'` (`:34`) + `logements`/`surface` (`:35-36`) | nombre, `min=1` | **OUI** — `progNum > 0` (`:61`) |
| 3 | **Critères** | `budget` (`:37`), `criteres` (`:38`) | nombre / texte | **Non** — `etape===3 ? true` (`:61`) |
| 4 | **Récap** | affichage seul (`:168-178`) | — | — |

### 1.2 Ce que chaque champ DEVIENT

Construction de la fiche (`ParcoursProjet.tsx:53-59`) :

```ts
const fiche = { type_programme: 'logements',                       // FIGÉ en dur (:54)
  ampleur: mode==='logements' ? {logements: progNum} : {sdp_m2: progNum},   // :55
  perimetre: { mode: 'communes', communes: commune ? [commune] : [] },      // :56
  ...(budget.trim()   ? { budget_foncier_eur: parseInt(budget) } : {}),     // :57
  ...(criteres.trim() ? { criteres_libres: criteres.trim() }     : {}) }    // :58
```

| Champ front | → fiche | Devient quoi côté moteur | Statut |
|-------------|---------|--------------------------|--------|
| `nom` | argument `nom` (hors fiche) | libellé seulement | **informatif** |
| `commune` | `perimetre.communes[0]` | `filtres.communes` (`derive_filtres`, `projets.py:148-151`) → clause `communes` du run | **alimente le moteur** · obligatoire |
| `logements`/`surface` | `ampleur.logements`/`sdp_m2` | `sdpMin` (`derive_sdp_besoin`, `projet_schema.py:134`) **et** `programme` M22 si logements (`derive_programme`, `projets.py:161`) | **alimente le moteur** · obligatoire |
| `budget` | `budget_foncier_eur` | **rien** — jamais lu par `derive_filtres` ni le run (voir 1.3) | **informatif** (PDF/affichage) |
| `criteres` (texte libre) | `criteres_libres` | **rien** — `grep criteres_libres src/…/projets.py` = 0 occurrence | **informatif mort** (stocké, jamais relu) |

**Constats saillants Phase 1 :**
- **`type_programme` est figé à `'logements'`** (`:54`) : étudiant/bureaux/autre du schéma
  (`projet_schema.py:11`) sont **inatteignables** par le parcours M114.
- **Les `contraintes` (→ `flagsExclus`) ne sont jamais collectées** par M114. Donc l'exclusion
  PPR/pollution/ABF/ICPE (`CONTRAINTE_FLAG`, `projet_schema.py:15`) — pourtant câblée dans
  la dérivation (`projets.py:155-157`) — reste **toujours vide** pour un projet né du parcours.
- **`niveaux` (gabarit R+n)** existe au schéma (`projet_schema.py:50`) mais n'est pas non
  plus collecté par M114.

### 1.3 Le budget : bloquant ou informatif ?

**Purement informatif.** N'apparaît pas dans `peutAvancer` (`:61`), ni dans le `disabled`
du bouton créer (`:192`). Côté serveur, la doctrine est **écrite explicitement** :

> « Le budget foncier reste une donnée de fiche (aucun prix par parcelle en base → un
> filtre budget serait menteur ; consigné). » — `projets.py:10-11`

`budget_foncier_eur` n'est lu par **aucune** dérivation (`derive_filtres`/`derive_programme`
ne le mentionnent pas, `projets.py:134-181`) ; seule trace d'usage : le PDF projet. **Aucun
impact sur le run** (pas de filtre budget, pas de charge foncière). *(À noter : la carte,
elle, a un `budget_max` dans `FiltreCriteres` (`app.py:1210`) — mais il n'a rien à voir avec
le budget du projet.)*

### 1.4 Où finit le parcours — un run part-il au clic final ?

**Le projet est créé « vide ». Aucun run au clic final.**

`creer()` (`ParcoursProjet.tsx:63-70`) → `createProjet({fiche, nom})` →
`POST /projets` (`projets.py:444-460`). Cette route **dérive** `filtres`/`programme` et
**persiste le projet uniquement** (`db.add(p)`, `:458`). Elle **n'écrit aucune parcelle**
(aucun `INSERT projet_parcelles` dans `projet_create`). Dédup douce : un projet actif
identique est renvoyé (`existing:true`, `:454`).

**Le run part à l'OUVERTURE**, pas à la création. `ProjetKanban.tsx:97-101` (et
`ParcoursTinder.tsx:29-33`) appellent `proposerProjet(pid)` dans un `useEffect` monté une
fois (`proposed.current`) → `POST /projets/{pid}/proposer` remplit « À trier ». C'est le
« run » réel, idempotent et non destructif (`ON CONFLICT DO NOTHING`, `projets.py:688`).

---

## PHASE 2 — LE LIEN PROJET ↔ FILTRES ↔ MOTEURS

### 2.1 D'où viennent les parcelles d'un projet ?

**D'un seul mécanisme : `_search_items(fiche)` appelé par `proposer`.** Les 4 seuls
écrivains de `projet_parcelles` (grep `INSERT INTO projet_parcelles`) sont tous dans
`projets.py` :

| Écrivain | Ligne | Source des parcelles | Déclenché par |
|----------|-------|----------------------|---------------|
| `projet_proposer` | `686` | `_search_items(db, p.fiche, lim)` (`:676`) | **auto à l'ouverture** du kanban/tinder |
| `_upsert_proposee` (via `chercher-plus`) | `803` | `_search_items` avec overrides (île / surface) (`:827`) | bouton « chercher plus » |
| `_upsert_proposee` (via `ajouter`) | `803` | 1 IDU précis (`:848-860`) | ajout manuel / clic-carte |
| `projets_fusionner` | `499` | union de projets doublons (`:487`) | fusion |

- **(a) Le run d'instruction (cadrage → moteurs → shortlist)** : **inexistant en tant que
  pipeline dédié.** Le « moteur » est `_search_items` (`projets.py:630-662`) : il dérive
  les filtres de la fiche puis interroge **soit M22** (`faisabilite_sens2`, si `programme`
  défini, `:641`) **soit le run servi q_v2** (`_q_v2_list`/`_q_v2_where`, `:646-661`).
  Le moteur du **Copilote RECHERCHE** (`copilote/moteurs.py`, `copilote/interpreteur.py`)
  n'écrit **jamais** dans `projet_parcelles` (grep `copilote/` = 0) — il est totalement
  déconnecté du projet.
- **(b) Les filtres de la carte** : **jamais.** `FiltreCriteres` sert `/parcels`,
  `/parcels/export.csv`, le compteur (`app.py:1253, 1290, 1709`) — de l'affichage carte,
  pas de l'écriture projet.
- **(c) L'ajout manuel depuis une fiche** : **oui**, `POST /projets/{pid}/ajouter`
  (`projets.py:848`) — un IDU, statut `proposee`, dédupliqué. C'est le **seul** point où
  un geste utilisateur (hors cadrage) fait entrer une parcelle précise.

### 2.2 Carte et cadrage : le même objet, ou deux systèmes ?

**Deux systèmes parallèles, reliés par une dérivation à sens unique fiche → filtres.**
Ils convergent seulement au fond : les deux finissent par appeler `_q_v2_where`
(`FiltreCriteres.where()` `app.py:1225` ; `_search_items` `projets.py:651`). Mais ce qu'ils
lui passent diffère radicalement.

| | **Carte — `FiltreCriteres`** (`app.py:1170-1237`) | **Cadrage projet — fiche** (`projet_schema.py:38-66`) |
|---|---|---|
| Nature | params de requête (session/URL) | objet persistant (`projets.fiche` JSONB) |
| Nombre de critères | **~44 facettes** | **~7 champs** (dont 2 réellement moteur) |
| Qui le remplit | l'utilisateur, clic par clic | le parcours M114 (2 champs) |
| Persistance | non (volatile) | oui (`projets` + `projets.filtres` dérivés) |

**Recouvrement (dans les deux, via `derive_filtres` `projets.py:134-158`) :**
`communes` (périmètre) · `sdpMin` (SDP besoin) · `flagsExclus` (contraintes — mais jamais
peuplé par M114, cf. 1.2).

**Divergences :**
- **Seulement dans la carte** (absent du cadrage projet) : `score_min`, `surface_min/max`,
  `sdp_max`, `evenement`, `veille`, `hors_copro`, `tiers`, `personne_morale`, `zonage`,
  `constructibilite`, `etat_sol`, `capacite_min`, `marge_min`, `zone_plu`, `sous_densite`,
  `mult_min`, `rang_max`, `renouvellement`, `division_or`, `proprietaire_type`,
  `etat_societe`, `copro`, `npnru`, `adresse_absente`, `budget_max`, `charge_min/max`,
  `prix_marche_min/max`, `marche_fiable`, `ca_min`, `mode_b_rentable` (+ 3 params mode B),
  `signaux`, `flags` (inclusifs), `defisc_active`, `pc_caduc` (`app.py:1174-1223`).
- **Seulement dans le cadrage** (absent de la carte) : `type_programme`, `ampleur.niveaux`,
  `budget_foncier_eur`, `criteres_libres` — tous **informatifs**, aucun ne filtre.

**Conséquence directe pour Vic :** la puissance de tri de la carte (charge foncière,
signaux de vie, prix marché, propriétaire, événement…) **n'est pas mobilisable** pour
composer le vivier d'un projet. Un projet cible « les logements dans telle commune de
telle SDP », rien de plus fin.

### 2.3 Re-exécution et modification du cadrage

- **Re-jouer le run** : **oui.** `proposer` (`:669`) rejoue les critères du jour à chaque
  ouverture — non destructif, et marque « hors critères actuels » (`hors_criteres`,
  `:692-696`) une décision qui ne matche plus, sans l'évincer (règle M2 de non-perte).
  `POST /{pid}/rejouer` (`:572-580`) **horodate** `derniere_execution_at` mais ne
  re-peuple pas lui-même (le front rappelle `proposer`).
- **Modifier le cadrage** : **oui**, `PATCH /projets/{pid}` avec `fiche`
  (`:542-559`) revalide et **re-dérive** `filtres` + `programme` (`:555-557`). Les décisions
  déjà posées (`projet_parcelles`) sont préservées. **Mais** : le parcours M114 n'offre pas
  d'écran d'édition de cadrage — seul le **nom** est éditable au kanban (`ProjetKanban.tsx:146`).
  Modifier commune/programme après création n'a **pas de porte UI** (le `PATCH` fiche existe
  côté API, non câblé au front pour la fiche).

---

## PHASE 3 — L'ÉCRAN DE TRI (le kanban de la capture)

Fichier : **`frontend/src/components/projets/ProjetKanban.tsx`** (359 l.). Deux surfaces de
tri partagent le même état (`['parcours', pid]`, mêmes statuts) : le **kanban** 3 colonnes
et le **`ParcoursTinder`** plein écran (deck sur la carte, ouvert par « Trier »,
`ProjetKanban.tsx:207` → `openParcours`).

### 3.1 Les trois colonnes et la mécanique par carte

Colonnes (`ProjetKanban.tsx:41-45`) : **À trier** (`proposee`) · **Retenues** (`retenue`) ·
**Écartées** (`ecartee`). *(Le 4e statut `a_analyser` n'a pas de colonne : il remonte en
tête de « À trier », cf. 3.4.)*

- **À trier** = liste dense `ProposeeRow` (`:287-308`, encaisse 50+), boutons inline :
  **✓** `retenue` (`:302`) · **◑** `a_analyser` (`:303`, masqué si déjà a_analyser) ·
  **✕** `ecartee` (`:304`).
- **Retenues/Écartées** = cartes visuelles `KanbanCard` (`:312-358`) avec vignette ortho
  IGN (`:263-268`), boutons de repli **✓ Retenir** / **✕ Écarter** / **↩ À trier**
  (ou « Récupérer » depuis écartée, `:352-354`).
- Tout geste appelle **la même** mutation `decide` → `setStatutParcelle(pid, idu, statut)`
  (`:105-106`) → `PATCH /projets/{pid}/parcelle/{idu}` (`projets.py:776`). Mise à jour
  optimiste (`:107-113`), puis resync CRM + compteurs (`:114-118`). Drag & drop natif
  (`:191-194`, `onDrop :131`) appelle la même mutation.

### 3.2 « → CRM » : ce que fait le lien

**Ce n'est pas un lien cliquable — c'est un libellé + infobulle** dans l'en-tête de la
colonne Retenues (`ProjetKanban.tsx:211-214`, tooltip « Chaque retenue crée une piste CRM
(contact à préparer) »). L'effet réel est **automatique** au passage en `retenue`
(`_sync_crm_retenue`, `projets.py:591-611`) :

- `retenue` ⇒ `INSERT pipeline_entries` (statut `contact_a_preparer` — ou 1re colonne du
  compte si absente, `:601-608`), lié au projet et au compte, `ON CONFLICT DO NOTHING`.
- quitter `retenue` ⇒ `DELETE` de l'entrée **auto-liée à ce projet** (`:609-611`) ; une
  entrée manuelle d'un autre projet est préservée.

La carte Retenue affiche « ▸ dans le CRM · contact à préparer » + le propriétaire public
(`ProjetKanban.tsx:335-339`).

### 3.3 Le clic sur une parcelle ouvre-t-il la fiche ?

**Oui — déjà le cas.** Le corps de la carte (hors bouton) appelle `onFiche()`
(`ProjetKanban.tsx:293` pour `ProposeeRow`, `:319` pour `KanbanCard`) → `select(it.idu)`
(`:234, :241`) → `selectedIdu` dans le store (`useApp.ts`, `select:`) → la `Fiche` se rend
(`App.tsx`, `{selectedIdu && … <Fiche/>}`). **Le souhait de Vic est déjà satisfait** côté
kanban. *(Réserve : la fiche s'affiche via la logique d'overlay `selectedIdu` de `App.tsx` ;
à vérifier visuellement qu'elle passe bien au-dessus du kanban en vue Projets.)*

### 3.4 « Peut-être » / la demi-lune ◑ : c'est quoi aujourd'hui ?

**Un vrai 4e statut persisté en base**, pas un simple visuel. `a_analyser` existe dans :
`projet_parcelles.statut` (`models.py:714`), l'enum backend `_STATUTS` (`projets.py:587`),
le type front `StatutParcelle` (`api.ts:815`), et il a ses propres compteurs et groupe
(`projets.py:627, 732, 748`).

Il n'a **pas de colonne** : dans « À trier », les `a_analyser` sont **fusionnés en tête**
de la file (`ProjetKanban.tsx:182-187`), signalés ◑ + bande `st-creuser` (`:294-296`), avec
un filtre rapide « ◑ à analyser N » (`:201-205`). Un `a_analyser` est traité comme
« indécis, à revoir » — **non** compté comme écarté ni retenu, **préservé** au rejeu
(`hors_criteres` porte sur `retenue`/`a_analyser`, `projets.py:695`).

### 3.5 État visuel, dette, ce qui manque pour la DA

- **`ProjetKanban.tsx` n'a PAS été refondu par M114** : M114 n'a refait que la **liste**
  (`ProjetsPanel.tsx:1-5`, en-tête « refondue d'après DA-PROJETS-v1 »). Le kanban date de
  M2 (« PJ3 », `:78`) et n'a pas de maquette DA à jour.
- **Valeurs en dur** : largeurs colonnes `w-[340px]` / `w-[300px]` (`:195`), `APERCU = 3`
  cartes avant « + N autres » (`:46, :188`), vignette WMS géoplateforme construite à la main
  avec `d = 0.0009` (`:265-266`), libellés `TYPE_LABEL`/`CONTRAINTE_LABEL` dupliqués du
  backend (`:15-20`).
- **Manque pour la DA** : pas de tokens de densité/typo cohérents avec la nouvelle DA
  (styles inline/utilitaires épars) ; pas d'indicateur de charge/pagination au-delà du
  déroulé ; l'accent mint est encore utilisé (`bg-mint`, `:208`) là où la nouvelle DA
  distingue les surfaces ; le « → CRM » et « réversible » sont des mentions discrètes non
  maquettées.

---

## PHASE 4 — LA TUYAUTERIE

### 4.1 Modèle de données (schéma réel)

Deux tables + un rattachement CRM. Il n'existe **pas** de table `cadrage` ni `run` séparée :
le cadrage est la colonne JSONB `fiche`, le « run » est éphémère (résultat live de
`proposer`, jamais snapshoté).

**`projets`** (`models.py:663-695` ; DDL `projets.py:45-56`)
```
id PK · compte_id (index, cloison tenant, FK hors ORM) · nom varchar(160)
fiche JSONB (le CADRAGE, validé FICHE_SCHEMA) · filtres JSONB (DÉRIVÉ de fiche)
programme JSONB nullable (params M22 si défini) · statut varchar(16) actif|archive
derniere_execution_at timestamptz · created_at · updated_at
```

**`projet_parcelles`** (`models.py:697-722`) — le cœur du tri
```
id PK · projet_id FK→projets.id ON DELETE CASCADE (index)
parcel_id FK→parcels.id ON DELETE CASCADE
statut varchar(16)  ∈ {proposee, retenue, ecartee, a_analyser}
rang int nullable (best-first, rejoué) · proposee_at · hors_criteres bool (M2)
UNIQUE(projet_id, parcel_id) = uq_projet_parcelle   ← 1 parcelle / projet
```

**`pipeline_entries`** (CRM) reçoit `projet_id integer REFERENCES projets(id) ON DELETE SET
NULL` (`projets.py:57-58`) — supprimer un projet ne perd pas la piste CRM (parcelle
conservée, lien mis à NULL).

**Tables lues (jamais écrites par le projet)** : `parcels`, `dryrun_parcel_evaluations`
(run servi `RUN`, `projets.py:307-309, 716`), `parcel_p_score_v2` (tier v2, `:717`),
`commune_contexte_sru`, `defisc_fenetres`/`pc_caducs` (badges gardés `to_regclass`, `:725`).

### 4.2 Endpoints (servis / consommés)

Tous sous `prefix="/projets"` (`projets.py:37`). Client : `frontend/src/lib/api.ts`.

| Méthode · route | Rôle | Ligne serveur | Client (`api.ts`) |
|---|---|---|---|
| GET `/reperes` | chiffres sourcés par secteur/commune | `72` | `getReperes :792` |
| POST `/apercu` | aperçu relié (compteur + top « pourquoi ») | `266` | `getApercu :805` |
| POST `/derive` | prévisualise nom+filtres+programme sans persister | `337` | `deriveProjet :798` |
| GET `` (liste) | projets + compteurs + vignette d'emprise | `420` | `getProjets :795` |
| POST `` (create) | **crée le projet, sans parcelle** | `444` | `createProjet :800` |
| POST `/fusionner` | fusion doublons (union, statut avancé gagne) | `471` | `fusionnerProjets :820` |
| GET `/pour-parcelle/{idu}` | projets où une parcelle est rattachée | `511` | `projetsPourParcelle :848` |
| GET `/{pid}` | un projet | `536` | `getProjet :796` |
| PATCH `/{pid}` | nom/statut/**fiche (re-dérive)** | `542` | `patchProjet :808` |
| DELETE `/{pid}` | supprime (CRM → projet_id NULL) | `562` | `deleteProjet :812` |
| POST `/{pid}/rejouer` | horodate `derniere_execution_at` | `572` | `rejouerProjet :810` |
| POST `/{pid}/proposer` | **le run** : remplit « À trier » | `669` | `proposerProjet :831` |
| GET `/{pid}/parcelles` | l'état de tri groupé par statut | `702` | `getParcoursEtat :834` |
| GET `/{pid}/carte/{idu}` | carte de décision (forces/attentions) | `751` | `getCarteDecision :835` |
| PATCH `/{pid}/parcelle/{idu}` | fixe le statut (+ sync CRM) | `776` | `setStatutParcelle :836` |
| POST `/{pid}/chercher-plus` | élargit (île/surface), ajoute proposées | `816` | `chercherPlus :840` |
| POST `/{pid}/ajouter` | ajoute 1 IDU en proposée | `848` | `ajouterParcelle :843` |
| GET `/{pid}/export.pdf` | dossier PDF (fiche + top) | `863` | `projetPdfUrl :807` |

Consommateurs front : `ParcoursProjet.tsx` (create), `ProjetsPanel.tsx` (liste/patch/fusion),
`ProjetKanban.tsx` (get/proposer/parcelles/statut/patch/pdf), `ParcoursTinder.tsx`
(proposer/parcelles/statut/carte).

### 4.3 Ce qui casse si on change l'ordre des étapes de création

Dépendances réelles (pas cosmétiques) :

1. **Commune avant programme n'est pas contraint**, mais **les deux sont requis avant
   création** (`disabled={… || !commune || progNum<=0}`, `ParcoursProjet.tsx:192`).
   Retirer/valider vide l'un ⇒ `POST /projets` peut passer, mais :
   - **Sans périmètre** : `derive_filtres` ne pose pas `communes` (`projets.py:146-151`) →
     le run balaie **toute l'île** ; le garde `_valide_fiche` exige juste une cohérence
     mode/valeur (`:126-130`), pas une commune.
   - **Sans programme** : pas de `programme` (`derive_programme` renvoie `None`,
     `projet_schema`/`:170`) → `_search_items` bascule sur le **run q_v2** au lieu de M22
     (`projets.py:639-646`), et `sdpMin` reste absent → aucun filtre de taille.
2. **Le `type_programme` figé à `'logements'`** (`:54`) est une **précondition** de
   `derive_programme` (il teste `t in (None,'autre')`, `projets.py:170`) : le passer à
   `autre`/vide désactive M22 silencieusement.
3. **`perimetre.mode` est le seul champ requis du sous-objet** (`FICHE_SCHEMA`,
   `projet_schema.py:54`) ; un `mode:'secteur'` sans `secteur` valide **rejette 422**
   (`projets.py:127`). Le parcours écrit toujours `mode:'communes'` (`:56`) → cohérent, mais
   changer l'étape périmètre pour émettre `secteur` sans garantir `secteur` casserait la
   création.
4. Le tri (`proposer`) **suppose un projet déjà persisté** (`_projet_or_404`, `:674`) :
   déplacer l'auto-`proposer` avant la création (ordre inverse) échouerait (pas de `pid`).

Aucune contrainte SQL n'ordonne les étapes ; les dépendances sont **applicatives**
(dérivation) et **de garde-fou schéma**.

---

## DETTE & POINTS D'ATTENTION RELEVÉS (sans correction)

1. **`criteres_libres` est stocké mais jamais relu** (`grep` = 0 dans `projets.py`) — champ
   informatif mort, promet une prise en compte qu'il n'a pas.
2. **`contraintes`/`flagsExclus` jamais alimentés par M114** — la seule voie d'exclusion
   PPR/ABF/… est un `PATCH` de fiche non câblé au front.
3. **`type_programme` figé** — étudiant/bureaux/`niveaux` inatteignables par le parcours.
4. **Pas d'édition de cadrage au front** — `PATCH fiche` existe, aucune porte UI (seul le nom
   se modifie, `ProjetKanban.tsx:146`).
5. **`ProjetEntretien.tsx` = code mort** (jamais importé) — ancien cadreur IA.
6. **`ParcoursProjet` importé aussi dans `CopiloteView.tsx:328`** (gardé par `projetForm.prefill`)
   — vraisemblablement inatteignable depuis M118 (PROJET → refus-voie) : à confirmer comme
   dette M118.
7. **Le kanban n'a pas de maquette DA** (Phase 3.5) — hors périmètre M114.
8. **Deux surfaces de tri** (kanban + `ParcoursTinder`) à maintenir en cohérence — même
   état, deux rendus, deux `proposer` au montage.

---

## CE QUI N'A PAS ÉTÉ TOUCHÉ

Audit strictement en lecture. Aucune modification de code, de schéma, de test. Branche
`audit/m119-flux-projet` non mergée.
