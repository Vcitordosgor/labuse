# Blocs fonciers

Clé interne : `blocs-fonciers` (num M29) · composant : `frontend/src/components/outils/Blocs.tsx` · endpoint(s) : `GET /modules/blocs`, `GET /modules/blocs/{bloc_id}`

> Note : le fichier `frontend/src/components/outils/blocB.tsx` (pointé par le mandat) n'est PAS le composant de cet outil : c'est un fichier « BLOC B » qui héberge d'autres modules (O5Servitudes, O6Comparateur, CommunesLegende). Le vrai composant est `Blocs.tsx`. De même, `src/labuse/exports/blocs/` est un répertoire d'exports de la FICHE parcelle (annonce, bilan, gabarit…), sans rapport avec cet outil ; et `tests/test_blocs_documents.py` teste des blocs de contenu ANC/réhabilitation. Aucun de ces trois ne concerne l'outil Blocs fonciers.

## 1. À quoi il sert, et pour qui
Pour un prospecteur foncier : repérer, sur toute l'île, les **assiettes contiguës d'un même propriétaire personne morale** (une société qui possède plusieurs parcelles qui se touchent — donc un terrain d'un seul tenant déjà réuni sous une seule main). Il sert à trouver des cibles d'acquisition groupée sans avoir à démarcher parcelle par parcelle, et renvoie directement vers le Scan patrimoine (SIREN) et l'Assemblage (les IDU du bloc).

## 2. Le parcours
Un seul chemin (liste → détail dans la même page).
1. **Filtres (toujours déployés).** 4 menus en grille 2×2 : commune (défaut « Toute l'île »), surface totale min (paliers 0 / 1 000 / 5 000 / 10 000 / 50 000 m², `Blocs.tsx:30`), plancher restant min (paliers 0 / 200 / 500 / 1 000 / 5 000 m², `Blocs.tsx:34`), nombre de parcelles min (≥ 2 / 3 / 6 / 11, défaut 2, `Blocs.tsx:38`). Une case « Inclure les propriétaires publics » (décochée par défaut) et un lien « Réinitialiser » quand un filtre diffère du défaut. La liste se recharge à chaque changement de filtre (`Blocs.tsx:179-185`), pas de bouton « valider ».
2. **Bandeau + liste.** Un bandeau « N blocs appartenant à des sociétés · M blocs publics masqués » (`Blocs.tsx:255-259`). Puis une carte par bloc : dénomination + SIREN, « commune · N parcelles », deux tuiles **Surface** et **plancher restant** (marqué « Estimé »), et les zonages PLU en puces (5 max, « +N » déplie le reste). Tri serveur par plancher résiduel décroissant (`modules.py:1260`). Pagination 200 (`Blocs.tsx:384` / `ListPaginationFooter`).
3. **Détail (clic sur une carte).** La carte s'ouvre et liste les parcelles du bloc (IDU · surface · zone · résiduel), surligne leur emprise sur la carte (`useModuleMap`, `Blocs.tsx:57`), et expose deux boutons : « Assembler ce bloc → » (pré-remplit les IDU dans l'Assemblage) et « Scan patrimoine → » (pré-remplit le SIREN). Un clic sur une ligne IDU ouvre la fiche parcelle (`Blocs.tsx:66`).

## 3. Les données lues
Le calcul est fait EN AMONT par le batch `labuse blocs-build` (CLI `src/labuse/cli.py:1204`, moteur `src/labuse/blocs.py`). Les endpoints ne font que lire les deux tables produites. Le batch, lui, lit :

| Source (nom catalogue) | Table SQL lue | Millésime servi | Cadence |
|---|---|---|---|
| DGFiP — parcelles des personnes morales | `parcelle_personne_morale` (colonnes `siren`, `denomination`, `groupe`, `forme_juridique`, `millesime`) — `blocs.py:75`, `115` | **2025** (max(millesime) servi, mesuré) ; panel 2019→2025, situation 1ᵉʳ janvier | annuelle |
| Cadastre (API Carto PCI / Etalab) | `parcels` (géométrie `geom_2975`, `surface_m2`, `commune`) — `blocs.py:73`, jointure `pa.idu = p.idu` | PCI/Etalab « latest » ingérée | (non versionné au catalogue) |
| PLU zonage | `parcel_zone_plu` (`COALESCE(zone_lib, zone_fam)`) — `blocs.py:107-108` | sert ce qui est ingéré | sur clic / ingestion PLU |
| Résiduel SDP (vue servie) | `parcel_residuel` (vue sur le run servi) — `blocs.py:104-105` | run épinglé au build (`residuel_run_seq`) | recalcul nocturne |

Tables produites et lues par l'écran : `parcel_blocs` (header, 13 colonnes) et `parcel_bloc_membres` (parcelles). Le millésime affiché au bandeau est relu séparément par l'endpoint (`modules.py:1265-1266`) ; la date « maj » = `max(built_at)` du batch (`modules.py:1267`, mesuré **17/10/2026**).

## 4. Les calculs
Tout est fait par `blocs.py:compute_blocs` (`blocs.py:63-150`). Aucun calcul métier au front ni dans l'endpoint.

- **Contiguïté (constante clé).** Deux parcelles du MÊME SIREN sont reliées par une arête si `ST_DWithin(geom_2975, geom_2975, 0,5 m)` (`blocs.py:83-87`). La constante `ADJ_BUFFER_M = 0,5 m` est **importée** depuis `src/labuse/assemblage.py` (`blocs.py:28`) — source unique, même contact cadastral que l'outil Assemblage. Origine : codée en dur dans le code (pas une config servie, pas un barème légal).
- **Bloc = composante connexe.** Union-Find sur les arêtes (`blocs.py:45-97`) ; on ne garde que les composantes d'au moins `MIN_PARCELLES = 2` parcelles (`blocs.py:32`, `97`). Constante codée en dur.
- **Surface totale** = somme des `round(surface_m2)` des membres (`blocs.py:137`). Arrondi : chaque surface est arrondie à l'entier à l'extraction (`round(...)::int`, `blocs.py:74`). Sourcé (cadastre).
- **SDP résiduelle agrégée** = SOMME des `sdp_residuelle_m2` servis des membres, en ignorant les parcelles sans résiduel connu (`blocs.py:126-127`). `sdp_couverture` = nombre de parcelles dont le résiduel est connu (`blocs.py:128`). **Estimé** (hérite du statut de la vue `parcel_residuel`). L'écran affiche « plancher restant » avec un badge « Estimé » et, si la couverture est partielle, « sur K/N » (`Blocs.tsx:131-133`).
- **Communes / zonages** = l'ensemble trié et dédupliqué des valeurs des membres (`blocs.py:124-125`). Sourcé (cadastre / PLU).
- **Propriétaire public/privé** = `classify_dgfip(groupe, forme, denomination)` (`src/labuse/proprietaire_type.py:151`), via `blocs.py:130`, `135`. Est **public** si le groupe DGFiP ∈ {1 État, 2-3 collectivité, 4 commune, 9 établissement public} (`proprietaire_type.py:52`, `PUBLIC_DGFIP_GROUPES`), affiné par la dénomination pour les EPF. Classement par **catégorie juridique** de la source, jamais par une liste de noms. Les groupes 5 (bailleur social), 6 (SEM), 7 (copro), 8 (indivision), 0 (SCI/société) sont **privés**.
- **Clé de bloc** `bloc_key = "{siren}:{min(idu)}"` (`blocs.py:132`) — déterministe, garantit l'idempotence (DELETE + rebuild).

## 5. Chaque chiffre affiché
| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| Dénomination (titre carte) | `parcel_blocs.denomination` = `max(denomination)` DGFiP du SIREN (`blocs.py:115`) | Sourcé |
| SIREN | `parcel_blocs.siren` (DGFiP PM) | Sourcé |
| « commune · N parcelles » | `communes[0]` + `n_parcelles` (compte des membres, `blocs.py:137`) | Sourcé |
| Surface (tuile) | `surface_totale_m2` = somme cadastre arrondie | Sourcé |
| Plancher restant (tuile, badge « Estimé ») | `sdp_residuelle_m2` = somme des résiduels servis | **Estimé** |
| « sur K/N » | `sdp_couverture` / `n_parcelles` | Sourcé (mécanique) |
| Zonages (puces) | `zonages` dédupliqués du PLU | Sourcé |
| Bandeau « N blocs … · M masqués » | `total` et `n_publics` (count SQL, `modules.py:1251-1254`) | Sourcé (comptages) |
| Détail : IDU · surface · zone · résiduel | `parcel_bloc_membres` | surface/zone Sourcés, résiduel **Estimé** |

## 6. Les limites
- **Ne voit que les personnes morales.** Les particuliers (pas d'identité stable d'une parcelle à l'autre) sont hors périmètre par construction (`blocs.py:11`, jointure sur `parcelle_personne_morale`). Un terrain d'un seul tenant appartenant à une personne physique n'apparaîtra JAMAIS.
- **Dépend de la couverture DGFiP PM.** Un SIREN absent du millésime 2025, ou un `siren` vide (filtré, `blocs.py:77`), fait disparaître le bloc.
- **Contiguïté purement cadastrale à 0,5 m.** Deux parcelles séparées par une route, une rivière ou une parcelle tierce ne sont PAS reliées, même si le même propriétaire les possède : le « bloc » peut être plus petit que l'emprise réelle maîtrisée. Inversement, 0,5 m peut relier des parcelles qui se frôlent à un coin.
- **Résiduel partiel silencieux au niveau du total.** La SDP agrégée somme les résiduels CONNUS ; les parcelles sans résiduel sont ignorées (pas comptées à zéro). La tuile n'affiche « sur K/N » que si K < N, donc une sous-couverture est signalée — mais la valeur reste une somme hétérogène de valeurs toutes « Estimé ».
- **Instantané du batch.** Les chiffres datent du dernier `blocs-build` (`built_at`, ici 17/10/2026). Un changement récent de PLU, de résiduel servi ou de propriété n'est pas reflété tant que le batch n'a pas rejoué.
- **Les regroupements ne tiennent pas compte de l'usage réel** (bâti, voirie, servitudes) : un « bloc » peut agréger des parcelles non constructibles (A, N) et surconstruites.

## 7. Les tests
- `tests/test_blocs.py` (backend, `pytest.mark.db`, PostGIS réel) garantit : un bloc connu vérifié à la main (surface 1240, résiduel 450, zonages UA/UB, `bloc_key` déterministe) ; parcelle isolée NON regroupée ; SIREN différents NON regroupés ; particulier (sans PM) hors périmètre ; même SIREN mais > 0,5 m NON regroupés ; endpoints liste+détail (filtres à paliers, 404) ; **propriétaires publics écartés par défaut + rétablis par `inclure_publics` + comptés** (`test_proprietaires_publics_ecartes_par_defaut`) ; idempotence du rebuild. C'est une couverture solide du moteur.
- **Aucun test front** : il n'y a pas de `Blocs.test.tsx`. L'affichage des cartes, le badge « Estimé », la mécanique « +N » zonages, les ponts Assembler/Scan et le compteur du bandeau ne sont vérifiés par aucun test automatique.
- Aucun test ne vérifie la **jointure amont** (couverture DGFiP PM réelle, parcelles sans résiduel), ni le choix de `0,5 m` comme critère, ni le tri/pagination à grande échelle.

## 8. Les documents liés (PDF, exports)
**Aucun.** Le commentaire d'en-tête du composant le dit explicitement : « aucun export ; aucune surface IA » (`Blocs.tsx:7`). Il n'y a ni PDF, ni export CSV/Excel propre à cet outil. Les ponts (Assembler, Scan patrimoine) rouvrent d'AUTRES outils avec les IDU/SIREN du bloc ; ceux-là peuvent produire leurs propres documents, mais à partir de leurs propres sources, pas d'un export « bloc ». Il n'y a donc pas de risque d'écart écran↔PDF ici.

## 9. Trois cas rejoués
Les 3 parcelles témoins du mandat sont peu adaptées : cet outil est par **propriétaire/bloc**, pas par parcelle. J'ai vérifié chacune en base, puis complété par un bloc témoin réel.

**a) `97409000AK0804` (Saint-André) — APPARTIENT à un bloc.** `psql` sur `parcel_bloc_membres` :
```
idu=97409000AK0804  bloc_id=33697  surface_m2=28258  commune=Saint-André  zone=UB  sdp_residuelle_m2=34223
```
Header du bloc 33697 (`parcel_blocs`) : `siren=219740099 · denomination=COMMUNE DE SAINT ANDRE · n_parcelles=71 · surface_totale_m2=163642 · communes={Saint-André} · sdp_residuelle_m2=139576 · sdp_couverture=71 · is_public=t · zonages={UB}`. **Point notable : ce bloc est PUBLIC (commune, groupe 4) → il est MASQUÉ par défaut dans l'outil.** L'utilisateur ne le verra qu'en cochant « Inclure les propriétaires publics ». `curl /modules/blocs/33697` renvoie les 71 membres triés résiduel décroissant (AK0804 en tête : 28258 m² / 34223 résiduel).

**b) `97411000BZ1065` (Saint-Denis) — PAS dans un bloc.** Absente de `parcel_bloc_membres` et de `parcelle_personne_morale` : aucun propriétaire PM rattaché → hors périmètre (soit particulier, soit non PM dans le millésime). Elle n'apparaît dans aucun bloc.

**c) `97415000DH0076` (Saint-Pierre) — PAS dans un bloc.** Idem : absente des deux tables. Hors périmètre de l'outil.

**d) Bloc témoin réel (liste `curl /modules/blocs?limit=3`, tri par défaut).** Le 1ᵉʳ bloc privé servi : `bloc_id=33679 · CBO TERRITORIA · SIREN 452038805 · 118 parcelles · surface 2 782 076 m² · plancher restant 311 598 m² (couverture 118/118) · Saint-Paul · zonages A/AU2c/AU2h/Acu/N/Ncor/Ncu/Nerl/U2c/U2e/U2h · is_public=false`. Explication : CBO TERRITORIA (groupe 0 / société privée) possède 118 parcelles qui se touchent à ≤ 0,5 m à Saint-Paul, réunies en une assiette ; le plancher restant 311 598 m² est la SOMME des résiduels (Estimé) des 118 parcelles.

**Compteurs globaux (mesurés par curl/psql) :** `total=6357` blocs privés servis ; `n_publics=4865` blocs publics masqués ; en base `6357` is_public=false / `4865` is_public=true ; `parcelle_personne_morale` : 12 605 SIREN, 82 701 lignes, millésime max 2025.

## 10. Tes doutes (par gravité)
1. **Les propriétaires publics sont la majorité des blocs (4865 publics vs 6357 privés) et sont masqués par défaut.** Le prospecteur voit « 6357 blocs » sans réaliser que presque autant lui sont cachés ; pour un terrain à fort potentiel comme celui de Saint-André (71 parcelles, 139 576 m² de résiduel), il faut cocher une case. Le choix « rarement cessible à un promoteur » (tooltip) est défendable mais le masquage par défaut d'un si gros gisement mérite d'être questionné.
2. **Le critère de contiguïté `0,5 m` est codé en dur** et ne tient pas compte des coupures physiques (route, cours d'eau). Un même propriétaire dont les parcelles sont séparées par une voie apparaîtra en plusieurs petits blocs, sous-estimant l'assiette maîtrisée ; aucun test ne mesure cet effet sur données réelles.
3. **La SDP agrégée somme des « Estimé » hétérogènes** et ignore (ne met pas à zéro) les parcelles sans résiduel. Sur un bloc à couverture partielle, le « plancher restant » affiché peut suggérer un potentiel plus franc qu'il n'est ; le badge « Estimé » + « sur K/N » atténue mais ne lève pas l'ambiguïté.
4. **Zéro test front** : tout l'affichage (badge Estimé, bandeau de masquage, ponts) repose sur la relecture de code, non sur des tests. Une régression d'UI passerait inaperçue.
5. **Fraîcheur dépendante d'un batch manuel.** Les chiffres datent du dernier `blocs-build` (17/10/2026) ; rien à l'écran n'alerte si le batch est vieux de plusieurs semaines pendant qu'un PLU ou un run résiduel a changé entre-temps.
