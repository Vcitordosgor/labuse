# RECETTE-1 — rapport des correctifs (retours du 08/09/2026)

**Branche** : `feat/recette-1` (depuis `main`). **Worktree** : `~/Desktop/labuse-recette1`.
**Modèle** : mandat = Fable ; exécuté sous Opus 4.8 (signalé, sans incidence). **Aucun merge, aucune bascule, aucun rescoring.**
**Périmètre fermé** aux points R1–R41. Un commit par lot.

État possible : **corrigé** / **non reproduit** / **refusé**.

---

## LOT 1 — Bloquants  *(commit 1)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R1 | Export **Résumé** cassé (base `/socle/`) | **corrigé** | `frontend/vite.config.ts` — `/resume` ajouté au proxy dev |
| R2 | Export **Apporteur** cassé (base `/socle/`) | **corrigé** | `frontend/vite.config.ts` — `/apporteur` ajouté au proxy dev |
| R3 | **Financier** « Impossible de charger le questionnaire » | **corrigé** | `frontend/vite.config.ts` — `/financier` ajouté au proxy dev |
| R4 | **Faisabilité** — « Trouver les parcelles » ne fait rien | **non reproduit** | endpoint + câblage vérifiés (voir ci-dessous) |
| R5 | Cache carte — zoom bloqué sur la parcelle dans les outils suivants | **corrigé** | `frontend/src/store/useApp.ts:867` (`setModule` remet `focusIdu: null`) |
| R6 | Listing — « Adresse non disponible » sur **toutes** les parcelles | **non reproduit** | mesuré : 257 340/430 813 parcelles adressées, cache sain (voir ci-dessous) |
| R7 | Lenteur du chargement (Blocs fonciers, Densifier) | **corrigé** (cause dite) | `src/labuse/api/app.py:5422` — tri « score » sur index ; cause détaillée ci-dessous |

### R1 / R2 / R3 — trois documents du builder EXPORTS-2 hors du proxy dev
**Cause unique.** Les routes racine `/resume/{idu}.pdf`, `/apporteur/{idu}.pdf`, `/financier/{idu}.pdf` et le fetch `/financier/{idu}/questionnaire` (routeur `documents.py`, servi à la racine) n'étaient **pas** déclarées dans le proxy dev de `vite.config.ts`. En `npm run dev`, le lien PDF sortait donc de la base `/socle/` (message « public base URL of /socle/ ») et le fetch du questionnaire tombait sur Vite au lieu de FastAPI (« Impossible de charger le questionnaire »). Même famille exacte que `/dossier` et `/pre-dossier` (M70) qui, eux, étaient déjà proxifiés — d'où le fait que Dossier et Pré-dossier PC fonctionnaient et pas Résumé/Apporteur/Financier.
**Correctif** : ajout de `'/resume', '/apporteur', '/financier'` à `apiPaths`. Vérifié : `GET /resume/{idu}.pdf`, `/apporteur/{idu}.pdf` et `GET /financier/{idu}/questionnaire` répondent 200 sur l'API `:8000`. ⚠ **TRAIN 8** : ces mêmes préfixes doivent être routés côté Caddy en prod (comme `/argumentaire`, `/pre-dossier`).

### R4 — Faisabilité « Trouver les parcelles » : **non reproduit**
- L'outil « Faisabilité » du menu = `M22Programme.tsx` (registry `programme`), mappé sur `M22` (`ModulePanel.tsx:1670`).
- Le bouton (`M22Programme.tsx:156`) appelle `lancer()` → `setQuery(...)` → `useInfiniteQuery` POST `/modules/programme`. `/modules` **est** proxifié.
- `disabled={results.isLoading}` : en `@tanstack/react-query` v5, une requête `enabled:false` a `isLoading=false` (= `isPending && isFetching`), donc le bouton n'est **pas** figé.
- L'endpoint répond **200** : `POST /modules/programme` (commune nulle → 19 752 parcelles ; commune = nom → OK ; `CommuneScope` émet bien le **nom** de commune, attendu par `p.commune`).
- Aucune erreur de rendu (voisins `DestinationSelect`/`useDestinationsRef` sur `/outils/…`, proxifié et null-safe).
- **Conclusion** : câblage et backend sains sur la base de recette. Si le symptôme persiste chez Vic, il est d'environnement (API cold-start du worktree, ou `vite preview` — dont le proxy `server.proxy` ne s'applique pas). À noter : sous R5 (carte bloquée), les résultats se posaient bien mais la carte ne se recentrait pas dessus, ce qui pouvait donner l'impression que « rien ne se passe » — R5 corrigé.

### R6 — « Adresse non disponible » partout : **non reproduit**
- Le texte n'existe qu'en `ResultsSection.tsx:47/127` (listing principal après « Voir les parcelles »). Il lit `p.adresse`.
- Île (défaut analyse groupé) : `getResults` → `/filtre` renvoie l'adresse (ex. « 6 Rue des Glorieuses, 97410 Saint-Pierre »).
- Commune : `/map/parcels.geojson` — mesuré sur Saint-Pierre : **25 849 / 42 304 features adressées** (pas « toutes » vides).
- Cache matérialisé `parcel_adresse` **sain** : 257 340 lignes, toutes `ban_voie` renseignée, = `count(distinct idu)` de `adresse_parcelles` → `_adresse_ready` vrai (le bug historique « moitié construit » que ce garde résout n'est pas présent).
- ~40 % des parcelles (173 473) n'ont **légitimement** aucune adresse BAN (grandes emprises, parcelles EDF/publiques…) : « Adresse non disponible » y est correct, jamais un blanc.
- **Conclusion** : non reproduit sur la base de recette (60 % adressées, cache sain). Un « tout vide » chez Vic pointerait vers un `parcel_adresse` vide/périmé au moment de la recette (état d'ingestion, pas de bug de code).

### R7 — Lenteur : **cause dite, puis corrigé**
**Cause.** Ce **n'est pas** la requête des deux outils. Mesuré bout-en-bout sur la base de recette (`:8000`) :
- `/modules/blocs` (liste) : **87 ms** ; détail d'un bloc : **10 ms** ; page profonde (offset 4000) : **37 ms**.
- `/renouvellement/liste` : **169 ms** ; page profonde (offset 6000) : **460 ms**.

Les deux outils lisent des tables **précalculées** (`parcel_blocs` 11 225 lignes, `parcel_renouvellement` 67 260) avec jointures indexées ; la sous-requête `idu_repr` des Blocs passe par la PK (Index Only Scan, pas un N+1). La carte surligne les IDU par filtre sur une couche déjà chargée (`MapView.tsx:2069`), **sans** fetch par parcelle.
La « lenteur » perçue correspond donc soit au **démarrage à froid de l'API du worktree** (1ʳᵉ requête ~70–140 s, documenté), soit au **GeoJSON commune plein** (`/map/parcels.geojson`, ~60 k features, ~11 s non caché puis caché) — indépendants de ces deux outils. Aucun de ces deux points n'est un défaut de code corrigeable ici (l'un est un cold-start d'env, l'autre déjà caché par `_geojson_cached`).

**Correctif appliqué (la seule inefficacité mesurable de requête).** Le tri par défaut « score » de Densifier lisait `renouv_score DESC, r.idu` — **sans index** → Parallel Seq Scan + top-N sort des 67 260 lignes à chaque page (18 ms de tri, croissant avec l'OFFSET). Or `rang_segment` est bâti exactement comme `rank() OVER (ORDER BY score DESC, idu)` (idu unique ⇒ bijection). Bascule du tri « score » sur `r.rang_segment` (indexé `ix_renouv_rang`) : **Index Scan**, tri 18 ms → **3,4 ms**, ordre vérifié **strictement identique** (`diff` des 20 IDU à offset 6000 = identiques). Aucun changement de schéma, aucune ligne réordonnée.

**Vérifs Lot 1** : `python -m py_compile src/labuse/api/app.py` OK ; `tsc --noEmit` (frontend) exit 0.

---

## LOT 2 — Doctrine du scoring  *(commit 2)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R8 | Le scoring ne s'affiche que sur demande | **corrigé** | pastilles retirées de 7 outils (liste ci-dessous) |

**Règle appliquée.** La pastille de palier (Priorité / À suivre / Sans signal / Écartée = `TierBadge` / `verdictMeta`) et tout classement issu de q_v14 ne restent que dans **deux** endroits :
1. le parcours « Demander à LABUSE » = la liste d'analyse (`ResultsSection.tsx:34`, affichée seulement en mode analyse ; le mode factuel était déjà neutre) ;
2. la **fiche parcelle** (`Fiche.tsx:627`, bloc verdict + `ScoreV2Block`).

**Endroits nettoyés (pastille retirée) :**
| Outil | Fichier:ligne (avant) | Ce qui a été retiré |
|-------|----------------------|---------------------|
| Étudier un bien | `EtudierBien.tsx:141` | pastille « Classement » de l'en-tête (le classement reste en fiche, au clic) |
| Faisabilité | `M22Programme.tsx:231` | `TierBadge` de chaque ligne (la marge de capacité `×N` reste — métrique de faisabilité) |
| Scan patrimoine | `ModulePanel.tsx:356` | `right={<TierBadge/>}` des lignes |
| Assemblage | `moteurs.tsx:401` | `TierBadge` des lignes de voisines |
| Simulateur ZAN | `moteurs.tsx:548` | `TierBadge` des parcelles alignées ZAN |
| Pièges & risques | `ModulePanel.tsx:1563` | `right={<TierBadge/>}` du crible |
| Densifier l'existant | `Renouvellement.tsx:228+257` | colonne **« Classement »** (en-tête + cellule) ; « Score densif. » et « Rang commune » **restent** (métriques propres à l'outil, cf. R40) |

`Row` (ModulePanel) : prop `right` rendue **facultative** (les outils ne la passent plus).

**Non touché, avec motif :**
- **Blocs fonciers** : n'affichait déjà aucune pastille (rien à retirer).
- **`ParcoursTinder.tsx:169`** : `setParcours` n'a **aucun appelant** dans le code → surface **inatteignable** (ne rend jamais rien à un client). Laissée en l'état ; à décider par Vic (parcours de tri d'un projet).
- **`ModulePanel.tsx:1025` (M06 « Mode bailleur »)** : outil **dormant**, retiré du menu le 20/08/2026 (non câblé). Pas une surface visible.

**Vérifs Lot 2** : `tsc --noEmit` exit 0 ; `vitest run` **194/194** (deux tests basculés en « la pastille est ABSENTE » : `ScanRetraits.test.tsx`, `DensifierTable.test.tsx`).

---

## LOT 3 — Vérifications de données (réponses)  *(commit 3)*

| # | Point | État | Résumé |
|---|-------|------|--------|
| R9 | CBO Territoria — 1 833 parcelles / 245 logements | **répondu** | les deux vrais, univers distincts ; 1 flottement signalé |
| R10 | PLU simuler — seulement AUc→U / AUs→U | **répondu** | réalité des règlements (data-driven) ; cible « U » en dur (choix) |
| R11 | Rechercher dans le PLU — commune sélectionnée ? | **répondu** | oui, filtré par `insee` ; corpus par commune |
| R12 | Fraîcheur des dates de source | **répondu** | majorité vivante ; liste des figées ci-dessous |
| R13 | Numérotation courrier propre au compte ? | **corrigé (signalé)** | était GLOBAL (bug) → rang par compte |
| R14 | Sources SOURCES-1 branchées à la fiche | **répondu** | blocs branchés ; DPF/zones humides/ENP/RPG orphelins du corps fiche |
| R15 | Outils utilisant SOURCES-1 (Pièges & risques) | **répondu** | sous-consommé : `_KINDS` à étendre + cascade non basculée |
| R16 | Remonter le temps — existe ? | **répondu** | oui, complet (`/moteurs/histoire`, 4 familles) |
| R17 | Info classement / Info scoring à jour ? | **répondu (à corriger par Vic)** | scoring à jour ; classement cite l'ancien modèle q_v8 |

### R9 — CBO Territoria (SIREN 452038805)
Les **deux chiffres sont vrais**, ce sont **deux univers différents**, aucun n'est faux.
- **1 833 parcelles détenues** = `/modules/patrimoine` (`modules.py:394`, INNER JOIN `parcelle_personne_morale` × `parcels`). Recompte DB : 1 871 lignes au fichier foncier DGFiP (millésime 2025), dont **1 833 géolocalisées** dans `parcels` (38 idu orphelins de géométrie).
- **245 logements depuis 2013** = veille-promoteurs `/frise` `n_logements` (`veille_promoteurs.py:250`), somme des `nb_lgt` des permis Sit@del (`sitadel_permits`) portés sur des parcelles du SIREN. Recompte DB : **110 permis, 245 logements**, dépôts 2013→2026 (2013 = début du flux Sit@del). Exact.
- **Écart expliqué** : 1 833 = *stock foncier possédé aujourd'hui* ; 245 = *flux de logements autorisés sur 13 ans*. Un foncier peut détenir des milliers de parcelles (réserves, nu) et n'avoir bâti que sur une fraction ; les opérations livrées puis revendues sortent du compte.
- ⚠ **À signaler** : double définition du compte parcelles — `/modules/patrimoine` affiche **1 833** (inner join), mais `/promoteur/{siren}/acquisitions` et `/frise` comptent **1 871** (`count(*)`). Deux onglets du même outil donnent deux totaux. Non corrigé (hors périmètre R9 = vérifier les chiffres).

### R10 — PLU · simuler un changement
**Réalité des règlements, pas une limite du code** (pour la zone de départ). Les zones candidates viennent des données réelles : `/moteurs/simulplu/zones` (`moteurs.py:46-53`) fait `SELECT subtype … WHERE kind='plu_gpu_zone' AND subtype LIKE 'AU%'`. Le GPU des 24 communes ne contient que **3** sous-types AU : `AUc` (21 communes), `AUs` (19), `AU` nu (2 : Saint-André, Saint-Leu). L'outil propose bien `AU` là où il existe — si seuls AUc/AUs ont été vus, c'est que Saint-André/Saint-Leu n'ont pas été testées. **Nuance** : la zone d'**arrivée « U » est codée en dur** (`moteurs.py:67`) — la simulation ne modélise que l'ouverture vers U, jamais une autre cible. Choix de périmètre assumé (« V1 : une commune, un zonage »), pas un bug.

### R11 — Rechercher dans le PLU
**Oui, les extraits proviennent bien de la commune sélectionnée.** `/modules/plu-annuaire/search` reçoit `insee` et l'applique en SQL (`plu_ingest.py:162-178`, clause `insee = :insee`). Corpus `plu_reglement_extrait` par commune (3 258 extraits, 21 communes, aucun texte générique partagé). Preuve : « hauteur » sans filtre = 653 extraits/21 communes ; avec `insee=97411` = 54 (une commune). L'UI impose de choisir une commune avant que la barre n'apparaisse. **Réserve mineure** : l'API autorise une recherche île-entière si `insee` absent (chemin non atteignable par l'UI).

### R12 — Fraîcheur des dates de source
**La majorité des dates sont VIVANTES** (lues d'un champ API / colonne DB `millesime`, `source_millesime`, `derniere_donnee`, `maj` : page Sources, légendes `Legend.fmtFraich`, blocs fiche marché/fibre/risques/quartier/PM, outils Radar/Secteur/PLU/Successions/Blocs/Densifier…). **Endroits FIGÉS** (littéraux, ne bougeront PAS à une réingestion) :
- **Famille CoSIA « 2025 » — 5 endroits** : `bati.py:200` (fiche « Le bien »), `faisabilite/bati_revele.py:29`, `ingestion/cosia.py:36` (écrit en base → fige à l'ingest), `ingestion/fraicheur.py:127`, front `fiche/leBien.tsx:39`. **Le plus sensible** (à éditer en 5 points à la prochaine campagne CoSIA).
- **`proprietaire_historique.py:23`** `_MILLESIME_SERVI = 2025` → « situation au 1ᵉʳ janvier 2025 » : constante, pas un `max(millesime)` de `pm_proprietaires_millesimes`.
- **Front `lib/layers.ts` + `Legend.tsx`** : dates en prose des descriptions de couches (QPV 2024, BPE 2025, ZNIEFF 2025, EDF « ~02/2020 republiée 16/10/2025 », Cerema 2022/2023, CBS 2022…). Une partie sont des **références réglementaires** (décrets ZFANG/FRR dans `territory_fiscal.py:30,33`) → figées **par nature**.
- **`TaxeAmenagement.tsx:133`** « Valeurs 2026 » (le reste du tip est vivant) ; **`strings.ts:173,201,328`** « ventes 2017-2025 » (explications du score).
*(Réponse = liste ; non corrigé — c'est une vérification.)*

### R13 — Numérotation des demandes de courrier → **GLOBAL (bug), corrigé**
Le numéro montré (« Demande n° 44 ») était le **`id` PK, séquence GLOBALE à tous les comptes** (`courrier.py` RETURNING id ; front `ModulePanel.tsx:1388/1408`). Un client voyait donc son 1ᵉʳ courrier numéroté « 44 » → **fuite du volume total de la plateforme** + numéros non contigus. La lecture restait cloisonnée par `compte_id` (pas d'accès croisé), c'était un défaut d'affichage.
**Corrigé** : back expose un **rang propre au compte** (`courrier.py` `_rang_compte()` + `row_number() OVER (ORDER BY id)` dans `demandes_de`), front affiche `rang_compte ?? id` (`ModulePanel.tsx`). Le `id` PK reste la clé technique (admin, notifs). Vérifié en base : compte 31 → n° 1..5 (au lieu des ids 30..34). Tests `CourrierService.test.tsx` bascule sur « n° 3, pas n° 42 ».

### R14 — SOURCES-1 et la fiche parcelle
**Branchées** (lecture LIVE, rendues au front) : `dispositifs` (ER/EBC, DPU, PEB, SUP — `app.py:3829+`→`constructibilite.tsx:711`), `sols` (SIS/CASIAS — `risques.tsx:29`), `fibre` Arcep, `filiation` DFI, `iris_quartier` RP2022 ; côté commune/Financier : zonage A/B/C, TFPB REI, ORT, loyers OLL, coût construction SDES. **Orphelines du CORPS de la fiche parcelle** : **DPF (ravines), zones humides, ENP, RPG** — présentes sur la CARTE seulement ; elles n'apparaîtraient au bloc `aleas` que via la cascade servie, or le run servi `q_v11_m137` est **antérieur à SOURCES-1**. Trou réel jusqu'à bascule d'un run SOURCES-1.

### R15 — SOURCES-1 et les outils (Pièges & risques)
Les autres outils (Scan, Radar, Successions, Blocs, Solaire) sont orthogonaux (rien à consommer). **« Pièges et risques » sous-consomme**, à deux titres :
1. `servitudes-invisibles` (LIVE `spatial_layers`) crible SIS/CASIAS + SUP, mais son dictionnaire `_KINDS` (`servitudes.py:28`) **n'a pas été étendu** aux nouveaux kinds : `peb` a été **retiré** (l.25), et `dpu`, `dpf`, `zone_humide`, `ens`/ENP, `plu_gpu_prescription` (ER/EBC) manquent. **Gap corrigeable sans run** — signalé, non corrigé (choix produit : décider quels kinds remonter).
2. le crible `duediligence` et `faisabilite` lisent la **cascade servie** (`runs.cascade()`=`q_v11_m137`) → aucun motif SOURCES-1 tant qu'un run SOURCES-1 n'est pas basculé (geste Vic, conforme au « jamais basculé »).

### R16 — Remonter le temps
**Existe et est complet.** Back `GET /moteurs/histoire/{idu}` (`moteurs.py:354`), front `HistoireFrise.tsx` sous le comparateur d'orthos de « Remonter le temps » (`TimeMachine.tsx:232`). **4 familles de faits datés** : Vente (`dvf_mutations_parcelle`), Permis (`sitadel_permits`, dépôt à la maille année), Propriétaire PM (`pm_proprietaires_millesimes`, maille millésime), Découpe (`dfi_filiation`). Millésimes servis en pied, état vide honnête. Rien ne manque.

### R17 — Info classement / Info scoring (écran d'analyse)
Les deux textes sont dans `LeftPanel.tsx` (`AlgoExplainer`/`ScoringExplainer`), contenus dans `strings.ts`. **Run réellement servi = `q_v11_m137`** (`served_manifest.json`), q_v14 **non** basculé.
- **« Info scoring » (paliers) = À JOUR** ✅ : rend les 4 paliers `priorite`/`a_suivre`/`sans_signal`/`ecartee` (`status.ts:65`, `strings.ts:123-128`), classification en probabilité absolue, vocabulaire PALIERS-1. Aucun terme ancien.
- **« Info classement » (méthode) = PÉRIMÉ** ⚠ : la section « Comment » (`strings.ts:319-323`) dit « le modèle a appris … **année 2023, vérifié sur les ventes 2024** » et le code s'ancre sur **`q_v8_calibre`** (12/08/2026) — soit **deux générations avant le run servi**. À corriger, MAIS le libellé correct dépend du run que Vic servira (q_v11_m137 aujourd'hui, q_v14 visé par le mandat) : je **ne réécris pas** une fenêtre d'entraînement non vérifiable, et le garde-fou interdit la bascule. **À traiter par Vic en même temps que la bascule** (signalé, non corrigé).

**Vérifs Lot 3** : `py_compile courrier.py` OK ; `tsc` 0 ; tests courrier/scan verts ; rang par compte vérifié en base.

---

## LOT 4 — Ordre du menu Outils  *(commit 4)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R18 | Ordonner le menu Outils | **corrigé** | `registry.ts` — `MODULES` réordonné |

Le menu est rendu à plat par `Rail.tsx:232` (`MODULES.filter((m) => !m.hidden)`), donc l'ordre du menu = l'ordre du tableau `MODULES`. Réordonné exactement selon le mandat : **1 PLU · 2 Permis · 3 Commune · 4 Étudier un bien · 5 Scan patrimoine · 6 Assemblage · 7 Comparer des parcelles · 8 Pièges et risques · 9 Étude de zone · 10 Remonter le temps · 11 Faisabilité · 12 Taxe d'aménagement · 13 Prospection solaire · 14 Densifier l'existant · 15 Blocs fonciers · 16 Successions à venir · 17 Courrier propriétaire.** Les 5 clés `hidden` (alias résolvants : calculette, mon-secteur, veille-promoteurs, barometre, promesses) sont conservées près de l'outil qui les résout — sans effet sur le menu. Aucun champ d'objet modifié (seul l'ordre). `tsc` 0.

---

## LOT 5 — Couches de la carte  *(commit 5)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R19 | Aucune sous-couche | **corrigé** | `LeftPanel.tsx` — `LAYER_SUBOPTIONS = {}` |
| R20 | 8 familles, ordre et contenu | **corrigé** | `LeftPanel.tsx` — `LAYER_FAMILIES` réécrit |

Le panneau des couches est 100 % piloté par deux tableaux (`LeftPanel.tsx`). **R19** : `LAYER_SUBOPTIONS` vidé — « Limites officielles du PLU » (`zonage`) et « TVA réduite primo-accédant » (`tva_primo`) ne sont plus imbriquées ; elles deviennent des couches normales, placées dans « Urbanisme » et « Dispositifs et marché ». **R20** : `LAYER_FAMILIES` réécrit aux 8 intitulés exacts et dans l'ordre du mandat (`Le fond`→**Repères**, `Eau et domanialité`→**Domanialité** ; `zonage` inséré dans Urbanisme après le calibré ; `tva_primo` dans Dispositifs après QPV ; les 6 autres familles inchangées). Les 33 couches sont couvertes 1:1, rien perdu ni inventé. La légende bas-droite (`Legend.tsx`, dynamique) traite déjà ces deux couches indépendamment — aucune retouche. `tsc` 0 ; `layersCoquilles.test` vert.

---

## LOT 6 — Architecture de deux outils  *(commit 6)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R21 | Blocs fonciers — 2 temps + clic ligne = fiche | **corrigé** | `Blocs.tsx` |
| R22 | Piscine — rien avant « Voir les parcelles » | **corrigé** | `ProspectionSolaire.tsx` (`ModePiscines`) |
| R23 | Piscine — retirer Courrier + Comparer | **corrigé** | idem |
| R24 | PLU — deux onglets | **non reproduit** (déjà en place) | `ProcedureChangement.tsx:37,60-68` |

**R21** — Blocs fonciers en deux temps : ajout d'un état `montre` + `filtresOuverts`. Les filtres (CommuneScope + paliers + « inclure publics ») sont désormais dans un `<details>` **accordéon** ; le bouton **« Voir les parcelles »** (`data-blocs-voir`) déclenche la requête (`enabled: montre`) et **replie l'accordéon**. Le bouton **« Voir la fiche »** de chaque parcelle du bloc est supprimé : la **ligne entière est cliquable** (`role="button"`, Enter/Espace, `select(idu)`). Pas de défilement horizontal (cartes empilées, `truncate`/`min-w-0` déjà en place).

**R22** — Outil Piscine : les requêtes agrégat + listing passent en `enabled: montre` ; tout le résultat (compteur, bouton carte, listing) est masqué tant que **« Voir les parcelles »** (`data-piscines-voir`) n'est pas cliqué — les textes **naissent au clic**.

**R23** — Outil Piscine : « Préparer les courriers » et « Comparer » retirés, **avec la sélection de lignes** (cases « tout sélectionner » + par ligne + état `sel` + ponts) qui ne servait qu'à eux. Cliquer une ligne ouvre toujours la fiche. Imports/hooks devenus inutiles retirés.

**R24** — non reproduit : les deux onglets « Par parcelle » et « Simuler l'ouverture » **existent déjà** (`ProcedureChangement.tsx`, refonte OUTILS-FIX-2 C1) — tab bar `role="tablist"`, contenu de chaque onglet gaté par `tab`. Rien à faire.

**Vérifs Lot 6** : `tsc` 0 ; `vitest` **194/194** (3 tests Piscine adaptés à R22/R23).

---

## LOT 7 — Textes à retirer  *(commit 7)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R25 | Retirer « Liste groupée par priorité… trier par Surface » | **corrigé** | `ResultsSection.tsx` (bloc `data-tri-groupe` retiré) |
| R26 | Retirer « · 3 PROCÉDURES EN COURS » | **corrigé** | `PluAnnuaire.tsx:67` |
| R27 | Retirer l'encadré « Envoi automatique indisponible… » | **corrigé** | `ModulePanel.tsx` (carte d'état gated `disponible`) |
| R28 | Retirer les infobulles au survol | **corrigé (ciblé + limite dite)** | voir ci-dessous |
| R29 | Analyse LABUSE écran 1 : redondant avec écran 2 ? | **répondu** (ne pas supprimer) | voir ci-dessous |

**R25** — le bloc `{groupes && <span data-tri-groupe>Liste …</span>}` est retiré ; le groupement par palier reste actif, on ne l'explique plus par ce texte.
**R26** — le fragment `· {n} procédure(s) en cours` du bandeau annuaire PLU est retiré (le « N PLU en vigueur (…) » reste).
**R27** — la carte d'état du Courrier ne s'affiche **que** quand le service est disponible (elle porte alors le plafond du jour) ; l'encadré « Envoi automatique indisponible — L'envoi postal n'est pas encore disponible » ne s'affiche plus jamais.

**R28** — Infobulles au survol. Deux mécanismes coexistent : le natif `title=` (~271 attributs) et le composant maison `<Tip>` (44, bulle stylée). J'ai appliqué la règle du mandat aux **infobulles redondantes sur les contrôles déjà étiquetés** (là où le libellé du bouton/tuile/ligne suffit) — exactement la catégorie des exemples cités :
- `+ CRM` (`Fiche.tsx:377`, « Ajouter au CRM (suivi de prospection) ») ;
- tuiles d'export **Résumé** (« … PDF, 3 pages »), **Apporteur**, **Courrier** (`Fiche.tsx:1641/1644/1647`) ;
- lignes « Ouvrir la fiche de la parcelle » (`Successions.tsx:123` ; `Blocs.tsx` déjà fait au R21).

**Conservés, avec motif** (ne sont pas des « bandeaux explicatifs redondants ») : les `<Tip>` d'information volontaire (définitions des paliers, méthode, sources — et le nouveau « i » de R40) ; les `title` **fonctionnels** (liens à icône seule Cadastre/Maps = nom accessible ; tuiles désactivées dont le `title` dit *pourquoi* ; `title` qui montre la valeur complète d'un texte tronqué). **Limite dite** : une purge de la totalité des ~271 `title` natifs (dont beaucoup fonctionnels/accessibilité) et/ou la neutralisation globale de `<Tip>` dépasse le geste « retirer les infobulles redondantes » et changerait de l'information voulue — **à confirmer par Vic** s'il veut aller jusque-là.

**R29** — Analyse LABUSE, écran 1 (« LABUSE a analysé les N parcelles… »). Écran 2 (zone résultats) reprend **toute la partie quantitative** (le code le dit : mêmes nombres, source unique `getFiltre`) et montre une ventilation **plus riche** (5 paliers vs 3) + la barre empilée + le compteur `N/total`. Écran 1 n'est donc **pas** 100 % redondant : il porte en propre (a) le rappel « Selon vos critères (…) », (b) le cadrage « … de {périmètre} », (c) le **CTA « Voir les parcelles »** qui fait la bascule révélation→liste. **Réponse** : le supprimer ferait perdre le rappel des critères et le geste de bascule ; si Vic veut le supprimer, il faudrait reporter ces trois éléments sur l'écran 2. **Non supprimé** (accord Vic requis, cf. mandat).

**Vérifs Lot 7** : `tsc` 0 ; `vitest` **194/194**.

---

## LOT 8 à 10 — à faire
*(non entamés)*
