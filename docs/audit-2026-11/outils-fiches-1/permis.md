# Permis

Clé interne : `permis` (num M03) · alias caché `promesses` (num M04, même outil, filtre « Dormant » pré-activé) · composant : `frontend/src/components/outils/ModulePanel.tsx` (`function M03`, l. 532) + lib `frontend/src/lib/permisEtats.ts` · endpoints : `/modules/permis`, `/modules/permis/{permit_id}`, `/modules/parcelle-permis`, `/modules/promesses` (backend `src/labuse/api/modules.py`).

> Note de recette : le backend `:7300` a répondu aux premiers appels (comptes + 3 parcelles témoins, repris tels quels ci-dessous) puis s'est arrêté pendant mes essais sur la liste `/modules/promesses` (requête lourde). Les chiffres « Dormant » qui n'ont pas pu être servis par l'API ont été reconstitués en SQL direct (`psql`) et signalés comme tels.

---

## 1. À quoi il sert, et pour qui

Veille des autorisations d'urbanisme (permis de construire et assimilés) sur l'île : un démarcheur foncier voit, commune par commune ou autour d'une parcelle, les permis récents (où ça bouge), achevés, et surtout les **« Dormant »** = permis de construire anciens jamais menés à terme sur un terrain encore nu (opportunité de rachat). C'est un outil de prospection et de contrôle de terrain, pas un suivi administratif en temps réel (la source ne publie que des dossiers déjà aboutis).

## 2. Le parcours

L'outil est **un seul outil à deux entrées** : `permis` ouvre en mode « Récent » (radar), `promesses` ouvre le **même écran** avec le filtre « Dormant » déjà actif (`moduleKey === 'promesses'` → `seg='mort'`, fenêtre 36 mois ; l. 543, 552, 597). Les deux clés vivent pour ne casser aucun lien profond ; le toggle local devient maître ensuite.

Écran unique, panneau de gauche, trois zones :
- **Barre de recherche intelligente** (l. 806-836) : un seul champ pour une adresse, une commune, un n° de permis, un IDU de parcelle (14 car.), ou un propriétaire/SIREN. Un IDU complet ou une parcelle choisie **cible la parcelle** (zoom + cercle 200 m) et bascule tout l'outil dans ses 200 m. Une chaîne alphanumérique plus courte est lue comme un **n° de permis** et ouvre sa fiche en bulle.
- **Accordéon à 3 blocs** (un seul ouvert, l. 563) : « Filtrer par état » (segment 5 états, ouvert par défaut) · « Affiner » (nature PC/DP/PA/PD, commune, fenêtre en mois, filtre géocodage) · « Voir les permis » (la liste, repliée par défaut).
- **Segment à 5 états** qui partitionnent la base (l. 771-782) : **Récent** (90 derniers jours), **Dormant**, **Achevés** (DAACT), **Autres**, **Tous**. Chaque état porte son compteur réel.

Ce qu'il obtient : des **points cliquables sur la carte** colorés par état (récent vert, dormant corail, achevé/autre gris — `permisEtats.ts` l. 22-25), une liste paginée par 200 (« voir plus »), et pour chaque permis une **fiche** (bulle carte ou panneau droit) avec nature, porteur, surface, dates, délai d'instruction, statut. En mode parcelle, une phrase « N permis à moins de 200 m » + les points des 200 m colorés par leur propre récence.

## 3. Les données lues

| Source (catalogue) | Table SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|
| SITADEL (autorisations d'urbanisme) | `sitadel_permits` (colonnes `type`, `date`, `commune`, `geom`, `idu_codes`, `raw` JSON : `etat`, `daact`, `nb_lgt`, `surf_hab`, `destination`, `geoloc`, `petitioner_name/siren`) | 2026-08 (données jusqu'au **2026-08-31**, servi par l'API) | mensuelle |
| — (table dérivée interne) | `m10_permit_delais` (LEFT JOIN : `date_depot`, `valide`, `delai_mois`, `date_achevement`) | dérivé de SITADEL | — |
| — (table dérivée interne) | `via_permits_geo` (permis géolocalisés autorisés, EPSG 2975 ; 47 070 lignes) — lue par `/parcelle-permis`, même table que le score viabilisation M-VIA | dérivé de SITADEL | — |
| — (run moteur) | `dryrun_parcel_evaluations`, `dryrun_cascade_results`, `parcels`, `parcel_p_score_v2` — lus par `/promesses` pour vérifier « parcelle toujours non bâtie » et joindre le score V2 | run cascade courant | par run |

Le catalogue `data_sources` donne : `SITADEL (autorisations d'urbanisme) | dynamique | 2026-08 | mensuelle | source_horizon_at 2026-06-30 | connecte`. Base locale : **50 809 permits**, du **2013-01-02 au 2026-08-31** ; 50 075 géocodés (98,5 %).

## 4. Les calculs

L'outil **ne calcule pas de valeur foncière** : il compte, filtre par date et géo-localise. Les « formules » sont des découpages temporels.

- **Fenêtre « Récent »** (`_permis_etat_pred`, `modules.py` l. 538-540) : `date >= dmax - interval '24 months'`, où `dmax = max(date)` de la base (l. 564). **Ancrage sur la fin des données, pas sur aujourd'hui** (honnêteté : le flux s'arrête avant la date du jour). La coupure servie `coupure_recent` = `dmax − 24 mois` = **2024-08-31** (rejoué). Note : le **libellé** écran dit « 90 derniers jours » et la fenêtre par défaut à l'ouverture est 3 mois (`setMonths(3)`, l. 605), mais le compteur « Récent » de l'entrée est calculé avec `modPermis(3,…)` → 3 mois ; le seuil de **couleur** (vert/gris) sur la carte en mode « Tous » utilise la coupure 24 mois (`cut24`, ModulePanel l. 703). Deux fenêtres « récent » coexistent (3 mois pour le compteur, 24 mois pour la couleur).
- **Achevé** (l. 542) : `date < dmax−24m AND raw->>'daact' IS NOT NULL` (déclaration d'achèvement présente).
- **Autre** (l. 543-553) : non récent, sans DAACT, et explicitement **pas** un dormant.
- **Dormant / « Au point mort »** (`/promesses`, l. 816-834 ; moteur `permis_point_mort`, `commune.py` l. 313-326) : permis de type **PC**, `date < now() − N mois` (défaut N=36 = caducité légale du PC, l. 600), `daact IS NULL`, ET parcelle rattachée **toujours non bâtie** (aucune ligne `dryrun_cascade_results.layer_name='bati' result='HARD_EXCLUDE'` au run courant). Ce filtre « non bâti » est le seul vrai calcul métier, et il s'appuie sur le run du moteur LABUSE, pas sur SITADEL seul. Attention : ici la fenêtre est ancrée sur **`now()`** (date du jour), contrairement à « Récent » ancré sur `dmax`.
- **Délai d'instruction** (`/permis/{id}`, l. 704-707) : affiché seulement si `m10_permit_delais.valide` ; libellé « N mois entre dépôt et autorisation ». Non recalculé ici, lu de la table dérivée.
- **Distance parcelle** (`/parcelle-permis`, l. 754) : `round(ST_Distance(geom_2975 parcelle, geom_2975 permis))`, rayons 100 m / 200 m. Les comptes `c100`/`c200` sont des **COUNT exacts** (pas le `len()` de la liste plafonnée à 500 ; l. 765-771).
- **% géocodé** (l. 656) : `round(100 × geocodes / total)`.

Constantes : `MONTHS_RADAR = [3,12,24,48,72,240]` et `MONTHS_PM = [24,36,48,60]` (ModulePanel l. 599-600, codées en dur). `_NATURE_LABELS`, `_DESTINATION_LABELS`, `ETAT_LABELS` : dictionnaires de libellés codés en dur d'après le dictionnaire SDES Sitadel3 (`modules.py` l. 675-679 ; `ingestion/permits.py` l. 97). États réels présents pour le 974 : **2 autorisé, 4 annulé, 5 travaux commencés, 6 travaux achevés** (comptés en base : 6→20 989, 2→14 281, 5→11 212, 4→4 327 ; refusé/sans-suite absents).

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé / estimé |
|---|---|---|
| « Récent » N | `/modules/permis?months=3` → `total` (COUNT sur `sitadel_permits`) | sourcé |
| « Dormant » N | `/modules/promesses?months=36&count_only` → `permis_point_mort` (COUNT distinct, run moteur) | sourcé (dépend du run LABUSE) |
| « Achevés » N | `/modules/permis?months=240&etat=acheve&count_only` | sourcé |
| « Autres » N | **dérivé** = Tous − Récent − Dormant − Achevés (ModulePanel l. 656) | estimé (soustraction, jamais compté directement) |
| « Tous » N | `/modules/permis?months=240&count_only` → `total` | sourcé |
| « Données jusqu'au » | `max(date)` de `sitadel_permits` (`donnees_jusqu_au`) | sourcé |
| % géocodés | `round(100×geocodes/total)` | sourcé (dérivé) |
| « N permis à moins de 200 m » | `/parcelle-permis` → `c200` / `localises` | sourcé |
| Distance d'un permis | `ST_Distance` parcelle↔permis | sourcé |
| Statut (fiche) | `etat_libelle(raw)` : DAACT⇒achevé sinon code `etat` décodé | sourcé |
| Nature / Destination (fiche) | `_NATURE_LABELS` / `_DESTINATION_LABELS` sur `type` / `raw.destination` | sourcé (décodé via dict codé en dur) |
| Délai d'instruction | `m10_permit_delais.delai_mois` si `valide` | sourcé (dérivé) |
| Porteur / SIREN | `raw.petitioner_name` / `raw.petitioner_siren` ; sinon « personne physique anonymisée » | sourcé |

## 6. Les limites

- **Censure structurelle de la source** : SITADEL ne publie **que les dossiers aboutis** (autorisés), datés à leur dépôt. Ni refus, ni dossiers en cours, ni demandes en instance ne sont visibles (`ingestion/permits.py` l. 118-121). L'outil ne peut donc pas montrer « ce qui se prépare ».
- **Fenêtre « Récent » ancrée sur `dmax`** (2026-08-31) et non sur aujourd'hui : un permis « récent » peut avoir plusieurs mois. Le « Dormant », lui, est ancré sur `now()` — les deux voies ne partagent pas la même origine de temps.
- **Deux définitions de « récent » coexistent** (3 mois pour le compteur, 24 mois pour la couleur carte) : risque d'incohérence perçue entre le chiffre du segment et ce qui est peint.
- **« Autres » est une soustraction** : si l'un des trois autres compteurs est indisponible, « Autres » affiche « … » et la partition n'est pas garantie exacte à l'instant du chargement.
- **« Dormant » dépend du run moteur LABUSE** (non-bâti au run courant) : un changement de run change le compte ; ce n'est pas purement SITADEL.
- **Géocodage** : 1,5 % des permits n'ont pas de point ; `/parcelle-permis` ne renvoie que du géolocalisé (`via_permits_geo`), donc un permis non localisé rattaché à la parcelle n'apparaît ni en point ni dans le compte dessinable.
- **« À moins de 200 m » ≠ « sur la parcelle »** : la phrase compte le **voisinage** 200 m (même assiette que le signal viabilisation), pas les permis littéralement sur l'IDU (cas témoin BZ1065 : 0 permis sur la parcelle, 11 dans les 200 m).
- Les **codes `etat`/destination ne sont pas documentés** par la source pour certaines valeurs — l'interprétation (2/4/5/6) est codée en dur d'après une lecture SDES, affichée telle quelle.

## 7. Les tests

- `frontend/src/components/outils/PermisDouble.test.tsx` (mock) : garantit la double entrée, les compteurs réels du segment (« Récent » / « Dormant »), les lignes enrichies (commune, pastille d'état = couleur carte via `data-permis-row-etat`), le survol qui allume le point (`permitHover`), le badge « Dormant · Sans DAACT · N ans », et le comportement d'accordéon (un seul bloc ouvert, Échap referme). Il mocke `fetch` : il ne teste **pas** les requêtes SQL réelles.
- `tests/test_retours16_permis.py` : vérifie côté API que l'état est servi par la fonction partagée `etat_libelle` (autorisé/annulé), que `count_only` renvoie `total`/`geocodes` sans `items`/`carte` et est cohérent avec l'appel complet, et des assertions de libellés (« Dormant », « permis dormants »). `tests/test_mf_permits.py` : garde de fraîcheur des features permis (échoue si permis périmés/vides).
- **Non vérifié par aucun test** : l'exactitude du filtre « non bâti » du Dormant contre le terrain réel ; la cohérence des deux fenêtres « récent » (3 vs 24 mois) ; la justesse des distances `ST_Distance` ; le décodage destination ; la performance/robustesse de `/promesses` (requête lourde — observée instable pendant cet audit).

## 8. Les documents liés (PDF, exports)

L'outil Permis **n'a pas d'export PDF propre**. En revanche la **fiche parcelle** (PDF Dossier / Oracle) porte un bloc « dépôts à proximité » via `exports/robinet_fiche.py` (l. 783-789) qui appelle `nearby_permits(db, pid, radius_m=500, fenetre_mois=24)` — **500 m / 24 mois**, un **chemin et une assiette DIFFÉRENTS** de l'écran Permis (qui travaille à 200 m via `via_permits_geo`, ou par commune/fenêtre libre). Les deux lisent la même source `sitadel_permits` mais **avec des rayons et fenêtres distincts** : le compte du PDF parcelle ne coïncidera pas forcément avec le « N permis à 200 m » de l'outil. L'écran Permis lui-même est la source directe de ses propres chiffres (pas de double lecture).

## 9. Trois cas rejoués

**Entrées** : `/modules/parcelle-permis?idu=<IDU>` sur les 3 parcelles témoins. **Sorties réelles** (curl bruts, avant l'arrêt du backend) :

- **97411000BZ1065 (Saint-Denis)** : `c100=5, c200=11, affiches=11, tronque=false, localises=11, non_localises=0`. Plus proche : `97441113A0067` PC 2013-04-29 (état 5, 11 m). Dont `97441123A0163` PC 2023-09-12 (état 6 achevé, 36 m). → **0 permis littéralement sur la parcelle, 11 dans les 200 m**, tous géolocalisés.
- **97409000AK0804 (Saint-André)** : `c100=32, c200=42, affiches=42, localises=42`. Plus proche : `97440922A0170` PC 2022-10-18 (état 5, 7 m) ; `97440923A0182` PC 2024-04-10 (état 2 autorisé, 9 m). → voisinage très dense (42 permis à 200 m).
- **97415000DH0076 (Saint-Pierre/sud)** : `c100=4, c200=7, affiches=7, localises=7`. Mélange PC et une `DP` (`97441522G0068` DP 2022-03-16, 37 m). → 7 permis à 200 m.

**Fiche permis rejouée** (`/modules/permis/97441113A0067`) : PC Saint-Denis, porteur personne physique anonymisée, 1 lot, 118 m² hab., dépôt 2013-01-01 → autorisation 2013-04-29, **délai 3 mois**, statut « travaux commencés » (état 5), destination « habitation », parcelle `97411000BZ1288`, géolocalisé.

**Compteurs île rejoués** : `/modules/permis?months=240&count_only` → **total 50 808, géocodés 50 074, jusqu'au 2026-08-31, coupure_recent 2024-08-31**. « Récent » (`months=3`) → **total 760** (94 % géocodés). « Dormant » (`/modules/promesses?months=36&count_only`) → **total 15 723**.

**Dormant rejoué en SQL** (le `/promesses` liste n'a pas répondu — backend arrêté ; requête répliquée en `psql` sur Salazie) : 3 PC dormants anciens, ex. `97442112A0057` 2013-01-17 (état 4, parcelle `97421000AV0926`, 642 m²), `97442112A0061` 2013-02-11, `97442112A0069` 2013-03-20 (état 5, 1091 m²). Confirme que le filtre renvoie bien des PC sans DAACT sur parcelles non exclues « bâti ».

## 10. Tes doutes (par gravité)

1. **`/modules/promesses` (liste) instable** : la requête liste (CTE `MATERIALIZED` + jointures latérales + run moteur) a **fait tomber le backend `:7300`** pendant l'audit (connexion refusée ensuite). C'est le cœur du mode « Dormant » / `promesses` ; sa robustesse en production (île entière, sans filtre commune) est un vrai risque, cohérent avec les notes « COUNT ~4 s » et « 28 s → 5 s » du code.
2. **Deux origines de temps incohérentes** : « Récent/Achevé/Autre » ancrés sur `dmax` (fin des données), mais « Dormant » ancré sur `now()`. Un même permis peut basculer différemment selon la voie ; l'utilisateur ne voit pas cette asymétrie.
3. **Double fenêtre « récent » (3 mois compteur vs 24 mois couleur)** : le chiffre du segment « Récent » et la couleur verte des points en mode « Tous » ne décrivent pas la même population — source possible de « je compte 760 mais j'en vois beaucoup plus en vert ».
4. **« Dormant » dépend du run LABUSE**, pas seulement de SITADEL : le compte « opportunités » peut varier avec un recalcul interne sans que la source amont ait bougé — à surveiller pour la stabilité du discours commercial.
5. **« Autres » dérivé par soustraction** : non compté directement ; si un sous-compteur manque, la partition peut être momentanément fausse ou afficher « … ».
