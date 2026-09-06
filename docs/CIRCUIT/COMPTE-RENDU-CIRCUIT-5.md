# COMPTE-RENDU CIRCUIT-5 — Les verrous

Branche `feat/circuit-5`, créée depuis `origin/main` à jour (`48fd98d7` = merge CIRCUIT-4).
Reprise : « continue CIRCUIT-5 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md ».

## État d'avancement

- [x] Étape 0 — branche, baseline, lecture des comptes-rendus
- [x] Lot 1 — verrou des tables
- [x] Lot 2 — verrou des sources (68 = 68)
- [x] Lot 3 — verrou des versions
- [x] Lot 4 — verrou des communes
- [x] Lot 5 — verrou des concepts et des moteurs
- [x] Lot 6 — commande, porte, page, VERROUS.md

**MANDAT TERMINÉ le 06/09/2026 — 16 verrous, 0 cassé, rien mergé.**

## Étape 0 — baseline (06/09/2026)

`main` est occupée par le worktree `~/Desktop/labuse-merge` → branche créée par
`git checkout -b feat/circuit-5 origin/main` (même contenu, l'autre worktree n'est pas touché).

Suites au départ (base locale accumulée, pas d'A/B fraîche) :

- **pytest** : `4 failed, 2615 passed, 50 skipped` en 81 s
  (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` requis, sinon `test_non_contradiction`
  erre à la collecte sur libgobject/WeasyPrint — FZ-002 pré-existant).
  Les 4 échecs sont **pré-existants par construction** (la branche = `origin/main` + le seul
  commit du mandat) :
  - `test_courrier_boucle.py::test_boucle_piste_courrier_reponse` — IntegrityError FK
    `pipeline_entries`→compte (accumulation de `labuse_test`)
  - `test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque` — idem
  - `test_dashboard.py::test_ia_log_attribue_au_compte` — idem
  - `test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel` — AssertionError
- **tsc** : 0 erreur
- **vitest** : 181 passed (43 fichiers)

Règle tenue pendant tout le mandat : zéro échec NOUVEAU par rapport à cette baseline.

## Décisions prises en autonomie

- D0-1 : `main` étant réservée par le worktree `labuse-merge`, la branche part de
  `origin/main` (identique) plutôt que de déplacer le checkout — option la plus sûre.
- D0-2 : baseline notée avec ses 4 échecs d'accumulation de base de test plutôt que de
  recréer `labuse_test` (une recréation aurait changé l'environnement de tout le poste
  en début de mandat) ; le critère devient « zéro échec nouveau ».
- D1-1 : les moteurs lisent aussi des tables FABRIQUÉES (produits de la pompe :
  `parcel_flags`, `score_e`, `p_model_*`…) — la carte les déclare dans une famille propre
  (`TABLES_FABRIQUEES`, avec leur fabricant) plutôt que de les coller à un réservoir
  arbitraire ou de les laisser orphelines. Le verrou couvre l'union (réservoirs ∪
  fabrications ∪ exploitation).
- D1-2 : DOUTE du CSV résolus par le code : `rpg_proxy_ign` → kind `safer` (layers_ingest),
  `inpn_espaces_proteges` → kind `ens`, `deal_wms_wfs` → canal sans table propre (QPV/NPNRU
  portent les tables), `spanc_epci` → manuel sans table.
- D1-3 : `p_model_static_pre_v8`/`parcel_residuel_pre_v8` (lecteur `bascule_gardes.py`)
  restent orphelines « archiver, à débrancher d'abord » — l'option sûre : pas de débranchage
  de garde en autonomie.
- D1-4 : `labuse tables purger --apply` PAS joué (geste de Vic) ; le mode liste seul a été
  vérifié ; V1c retourne `a_decider` (jamais `casse`) tant que chaque orpheline a son
  action — un déploiement ne doit pas être bloqué par des tables que seul Vic peut purger.
- D1-5 : les 9 « réservoirs sans lecteur » et les 4 « à rattacher » ne sont PAS corrigés en
  autonomie (pas de donnée inventée au registre, pas de ligne catalogue créée) — listés
  pour le Résumé « à décider » (lot 6).
- D2-1 : BDNB, Réunion Express et Taxe d'aménagement restent `a_faire` (chantier nommé) —
  le mandat dit « morte ou essai → retiree », or aucune des trois n'est morte par notre
  choix : l'amont peut couvrir, le débat public suit son cours, les taux attendent Vic.
  Retirer serait mentir ; V2b exige leur chantier en note.
- D2-2 : la migration des statuts est appliquée sur la base locale par
  `appliquer_statuts_circuit` seul (pas un `seed()` complet, qui ré-upserterait 71 lignes
  et leurs notes) ; le seed l'appelle pour les bases futures.
- D2-3 : `retiree_le` = date du GESTE de retrait (posée une fois, `COALESCE`), pas une date
  d'historien : les notes gardent l'histoire, la colonne garde le geste.
- D3-1 : `dpe_connu` déclarée au registre n'est PAS une invention (interdit D1-5) : le bloc
  est construit et servi au payload (`app.py:5312`), c'est le registre qui avait un trou —
  la déclaration est `en_attente` (aucun robinet ne l'affiche), fidèle à l'écran.
- D3-2 : le trio « injecter, calculer, basculer » du 3.2 est joué sur BODACC en réel pour
  l'injection ; « calculer/basculer » ne s'appliquent pas (source LIVE, servie à
  l'injection — le cycle pompe complet coûterait des heures de scoring et changerait l'état
  servi local). Le verrou V3b tient l'invariant EN CONTINU (sonde de nuit + deploy), ce qui
  est plus fort qu'un drill unique.
- D3-3 : l'eau DPE « ouverte » depuis CIRCUIT-4 était un FAUX SIGNAL (publication amont vs
  date de contenu) — corrigé par comparaison à `last_sync_at`, ET l'eau réellement bue
  (`ingest-dpe --force`) avant de solder les lignes : jamais un test ajusté pour passer,
  le rafraîchissement a eu lieu.
- D4-1 : la ligne SIRENE `insee='97454'` (code inexistant) n'est PAS supprimée — la FK reste
  NOT VALID sur cette table, l'entrée est bloquée, la ligne est nommée par V4a « à
  décider » ; la correction viendra d'une ré-ingestion SIRENE ou d'un geste de Vic.
- D4-2 : le test géographique ne couvre pas les aléas — les couches Géorisques/DEAL sont
  ingérées À L'ÎLE (jamais découpées par commune) : le scénario « couche de la commune
  voisine collée » n'existe que pour les documents GPU (partition `DU_<insee>`), couvert.
  L'intégrité aléa reste tenue par la sonde catégorielle 4.2 (degré non rétrogradé).
- D4-3 : les écarts « Saint-Denis population » et « Saint-Joseph CatNat » sont marqués
  `ecart_assume` AVEC leur raison dans les fichiers d'échantillon plutôt que tolérés en
  silence (faux vert) ou laissés en avertissement éternel (bruit) — une dérive NOUVELLE
  au-delà sortira `ecart`.
- D4-4 : le cache fiche commune rafraîchi (24 communes) après la trouvaille CatNat — la
  racine (cache jamais invalidé à l'ingestion) reste une dette nommée, le filet est
  désormais le rejeu producteur (V4b/avertissant) qui verra toute rechute.
- D5-1 : le mandat dit « un couple jamais sondé est un verrou cassé » — le prendre au pied
  de la lettre aujourd'hui bloquerait tout déploiement (la sonde compare 8 couples sur 120
  multi). L'option sûre retenue : le CASSÉ sanctionne le SILENCE — chaque couple est sondé,
  mono-robinet (golden/règles font foi), ou porte sa raison NOMMÉE dans `NON_SONDES` (dont
  « extension sonde à décider Vic » quand c'est la seule vérité). Rien n'est un « non
  couvert » muet ; étendre la sonde couple par couple est un chantier listé, pas un verrou
  menti.
- D5-2 : les groupes assumés de V5a vivent dans le CODE (pas parsés du .md — un document ne
  peut pas être une garde) ; CONCEPTS-CANONIQUES.md les documente pour Vic.

## Lot 1 — verrou des tables (livré)

**La carte** : `src/labuse/registre/tables.py` — 80 réservoirs déclarés (tables +
couches `spatial_layers` + millésime ; les hors-vitrine avec leur note), 74 fabrications
de la pompe, 78 tables d'exploitation, 5 relations PostGIS. Les orphelines sont
**calculées** (schéma − carte), jamais énumérées : seules les actions proposées sont
curées (`ACTIONS_PROPOSEES`).

**Les verrous** (`src/labuse/circuit_verrous.py`, joués par `labuse circuit verrous`) :
- **V1a** (statique) : les noms de tables dans les requêtes de `registre/moteurs/` et les
  `Donnee.table` des passe-plats ⊆ carte. Seul un candidat qui EST une relation du schéma
  est une violation (élimine les faux positifs : imports Python, `parcels.surface_m2`,
  tuilages WMTS distants). Sur la base réelle : **ok** (6 modules, 168 données).
- **V1b** (exécution) : `journal_requetes()` (event `before_cursor_execute`) capture les
  tables touchées pendant `sonde_circuit.verifier_robinets` — 10 tables, toutes dans la
  carte. Les suffixes `__attente`/`__precedente` (échange CIRCUIT-3) sont rattachés à leur
  table de base.
- **V1c** : orphelines listées avec action, jamais un DROP — verdict **à décider**
  (32 orphelines, 1,56 Go, `TABLES-ORPHELINES.md`). Une orpheline NOUVELLE sans action
  proposée = verrou **cassé** (trou de curation).
- **V1d** : réservoir sans lecteur au registre = **à décider** — 9 trouvés (dont DPE :
  nulle part dans le registre alors que `dpe_records` nourrit scoring et passoire ;
  MOBPRO : abandonné par ZONE-DONNÉES mais resté en vitrine).

**Preuves cassé → vert** (`tests/verrous/test_lot1_tables.py`, 15 tests, marque `verrous`) :
- V1a : fonction témoin `moteur_temoin.py` lisant `zz_orpheline_temoin` (posée dans le
  schéma injecté) → `casse`, le détail nomme fichier et table ; témoin ne lisant que la
  carte → `ok`.
- V1b : sonde monkeypatchée lisant `zz_orpheline_v1b` (table posée exprès en base de test)
  → `casse` ; sonde fidèle → `ok`.
- V1c : `zz_perdue_expres` dans le schéma sans action → `casse` ; avec action → `a_decider`.
- V1d : réservoir `zz_reservoir_muet` (table que personne ne lit) → listé `a_decider`.
  (Premier essai avec `tables=("parcels",)` : NON détecté car « lu » via la table partagée —
  le test le prouve en creux, un réservoir qui partage une table lue n'est pas muet.)
- `-m local` : `jouer_tous()` sur la base réelle `labuse` → **0 cassé** (2 à décider).

**CLI** : `labuse circuit verrous [--complet] [--sans-journal]` (une ligne par verrou :
phrase, verdict, preuve ; sort en erreur au premier cassé ; journalise geste `controle`,
cible `verrous`) · `labuse tables purger [--apply]` (déplace vers le schéma `poubelle`,
`ALTER TABLE … SET SCHEMA` — jamais un DROP ; `--apply` NON joué : geste de Vic).
PIÈGE connu : `python -m labuse.cli` ne voit pas les commandes tardives (garde `__main__`
en milieu de fichier) → passer par le binaire `labuse` (PYTHONPATH sur le worktree).

**Trouvailles chemin faisant** :
- La vitrine locale compte DÉJÀ **68** réservoirs servis (le merge CIRCUIT-4/RETOURS a
  amené EDF HTA/TCSP) ; 80 lignes en base → 12 hors vitrine pour le lot 2 (3 DOUBLON,
  2 hub, 7 a_faire dont 2 « RETIRÉ »).
- `data_sources` 96 (Cadastre d'époque) et 97 (CatNat GASPAR) manquaient au pont
  `NOM_VERS_SLUG` et à `reservoirs.csv` → slugs `cadastre_epoque`/`catnat_gaspar` créés
  dans la carte (le pont sera complété au lot 2).
- Le registre référençait déjà `annuaire_service_public` (mairies) et `rnic_anah`
  (RNIC) : des slugs SANS ligne `data_sources` — au Résumé « à décider » (avec
  `rpls_commune` et `commune_conso_enaf`, servies sans slug ni ligne).
- `spatial_layers` porte une couche archivée `plu_gpu_zone__archive_m40` (3 lignes) —
  relevée dans TABLES-ORPHELINES.md, pas une table à purger.

## Lot 2 — verrou des sources : 68, pas un de plus (livré)

**Les 12 lignes hors vitrine traitées une par une** (`seed_sources.appliquer_statuts_circuit`,
idempotent, appelé par `seed()` ; colonnes `alias_de`/`retiree_le`/`retiree_raison` posées ;
enum `DataSourceStatus` élargi de `alias` et `retiree` — colonne varchar, pas d'enum PG,
aucune migration de type) :
- **doublon → alias** (l'ancien id reste, `alias_de` pointe la canonique) : 2 Cadastre Etalab
  → 1 ; 65 RGE ALTI 5 m → 6 ; 67 GPU info-surf → 63.
- **morte/essai → retiree** (date posée une fois + raison) : 49 EDF SEI (amont 410 Gone),
  50 ODRÉ (jamais branché), 80 ZNIEFF Région (canal jamais alimenté, canonique INPN).
- **hub** : 11 Région ODS, 14 Géoplateforme (déjà hub), 12 PEIGEO (était a_faire).
- **a_faire gardés** (chantier nommé dans la note — décision D2-1) : 89 BDNB (amont
  métropole seule, peut couvrir 974 un jour), 95 Réunion Express (débat public), 98 Taxe
  d'aménagement (mécanisme CIRCUIT-3 prêt, taux à saisir). Rien n'est effacé.

**Les verrous** :
- **V2a** : `68 = 68 = 68` — vitrine SQL (`WHERE_AFFICHEES`), prédicat Python
  (`est_affichee`), page (`flux.construire_flux`, ce que sert `/admin/circuit`) ; et chaque
  source servie a son slug dans le pont `NOM_VERS_SLUG` ET dans la carte table → réservoir.
  Mesuré vert sur la base locale. (Le « 68 » n'est jamais un littéral : égalité de comptes.)
- **V2b** : toute ligne hors vitrine porte un statut de première classe motivé — alias avec
  cible en vitrine, retirée datée et motivée, hub, a_faire avec chantier, ou masquée d'un
  geste admin (`affichage_desactive`, CONNEXIONS-2). Un doublon caché (statut de vitrine +
  note DOUBLON) = cassé.
- **2.3, le seed refuse** : `verifier_catalogue()` — name, producteur, mode d'accès,
  mode de remplissage + cadence (MODE_ET_CADENCE), sonde ou raison d'absence
  (RAISONS_NON_SURVEILLEES) ; `seed()` lève AVANT toute écriture.
  **La garde a mordu à sa pose** : CatNat, Taxe d'aménagement et Cadastre d'époque
  n'avaient ni mode ni cadence — déclarés (77 → 80 dans MODE_ET_CADENCE, épingle de
  `test_modes_cadences_declares` mise à jour avec la raison).

**Preuves cassé → vert** (`tests/verrous/test_lot2_sources.py`, 11 tests) : doublon caché →
casse ; alias sans cible / vers une ligne hors vitrine → casse ; retirée sans date-raison →
casse ; a_faire sans chantier → casse ; servie ET alias → contradiction ; catalogue
discipliné → [] ; seed avec ligne fantôme → ValueError avant toute écriture ; catalogue
réel → garde verte ; `-m local` : V2a/V2b verts sur la base réelle, et V2a prouvé cassé
quand la page ment (flux monkeypatché → « comptes divergents : SQL 68 · Python 68 · page 0 »).

## Lot 3 — verrou des versions : une seule version servie, partout (livré)

**Les verrous** :
- **V3a** : pour chaque table servie d'un réservoir, les seules générations admises dans le
  schéma sont `x`, `x__attente`, `x__precedente` (échange CIRCUIT-3) ; les tuiles servent le
  run du manifeste (`mvt_meta.run_label == runs.current()`). Vert : 64 tables, une
  génération chacune.
- **V3b** : zéro eau ancienne ouverte hors « gelé, étiqueté », mesurée MAINTENANT
  (`sonde_circuit.eau_lignes`, extrait pur de `verifier_eau_ancienne` — le verrou lit l'état,
  jamais les archives du journal). S'il en reste une, le détail nomme la donnée et le robinet.
- **V3c** : la sonde écrit des ids (la dette CIRCUIT-P3) — un libellé qui EST un robinet du
  registre sans son `robinet_id`, ou un `chiffre_id` hors registre, casse le verrou
  (exceptions admises : `exports_recette`/`mots_interdits`, les cas recette PDF du 0-bis).

**La migration 3.3** (`sonde_circuit.ensure()`, idempotente, backfill compris) :
- `circuit_ecarts.robinet_a_id/robinet_b_id`, `circuit_eau_ancienne.robinet_id` ;
- `robinet_id_de()` : l'id du registre si le libellé en est un, `CORRESPONDANCES_ROBINETS`
  sinon (`http:/parcels` → `fiche_parcelle_entete`, `attrs.niveau (servi)` →
  `couche_alea_inondation`…), None quand le côté n'est pas un robinet (moteur, SQL, règle) —
  le libellé reste ;
- `_upsert_ecart` et l'insert d'eau posent les ids À l'écriture.

**L'eau DPE — la dette soldée, et un FAUX SIGNAL corrigé** :
- l'ancien contrôle comparait `source_veille.dernier_vu` (date de PUBLICATION du jeu amont)
  au `max(date_etablissement)` (date de CONTENU) → « ouvert » permanent même base à jour.
  Prouvé par le rafraîchissement réel : `labuse ingest-dpe --force` du 06/09 → 16 DPE
  authentiques 974, max de contenu INCHANGÉ (21/07) — le dernier DPE réunionnais date de
  juillet, l'amont republie le JEU chaque semaine. Nouveau comparant : `last_sync_at`
  (notre geste d'ingestion).
- la ligne devient attribuable : donnée **`dpe_connu` déclarée au registre** (passe-plat
  `app.py:5312`, réservoir `dpe_ademe`, `en_attente` : le bloc payload est construit mais
  plus AFFICHÉ — commentaire `Fiche.tsx:1492`, rétablissement premium = décision Vic).
  → `dpe_ademe` n'est plus un réservoir muet (V1d passe de 9 à 8).
- les 9 lignes historiques `(chiffres DPE)` : migrées `dpe_connu` + soldées (l'eau a été bue).

**Le geste 3.2 joué sur la base locale** : `labuse ingest-bodacc` réel (9 733 SIREN
interrogés, 680 procédures, dernière annonce 21/08) puis V3b rejoué → **ok, zéro eau
ouverte après l'injection** (2 gels étiquetés : solaire, division). BODACC est une source
LIVE : servie à l'injection, sans calculer/basculer (décision D3-2).

**Preuves cassé → vert** (`tests/verrous/test_lot3_versions.py`, 9 tests) : génération
`dvf_mutations__essai` posée → casse ; `__attente`/`__precedente` admises → ok ; eau ouverte
posée → casse en nommant donnée+robinet, étiquetée → ok ; écart écrit à l'ancienne (id NULL)
→ casse, `ensure()` backfille → vert ; `chiffre_id` fantôme → casse ; upsert pose les ids ;
`-m local` : V3a/V3b/V3c verts sur la base réelle.

## Lot 4 — verrou des communes : la bonne ligne pour la bonne commune (livré)

**4.1 — la clé étrangère partout** (`src/labuse/referentiel_communes.py`) :
`communes_referentiel` (24 lignes, seedée depuis `REUNION_COMMUNES` — le code est la vérité)
et une FK par table à maille commune (24 tables relevées à l'information_schema, orphelines
exclues). Posées `NOT VALID` (l'ENTRÉE est bloquée immédiatement) puis validées : **23/24
validées** ; `sirene_etablissements` garde sa FK NOT VALID pour UNE ligne héritée
(`insee='97454'`, code inexistant — nommée, jamais supprimée en autonomie). Preuve vivante :
`INSERT … insee='97499'` → `Key (insee)=(97499) is not present in table
"communes_referentiel"`. Branché dans `labuse init-db` pour les bases neuves.

**4.2 — la permutation** (V4b) : Saint-Benoît (97410) et Sainte-Marie (97418) — le
producteur les distingue nettement sur CatNat (17 vs 22). Le verrou lit le payload que la
page sert (`commune_contexte_cache`, PAR la session du verrou — jamais un TestClient qui
pointerait une autre base), vérifie l'IDENTITÉ du bloc SRU (`sru.insee`, `sru.commune`) et
rejoue les attendus producteur de l'échantillon. Preuves : jointure décalée (payload de B
servi sous A) → cassé par l'identité ET par CatNat ; « première ligne par défaut » (même
valeur partout) → cassé.

**4.3 — les parcelles frontière** (V4c) : 3 témoins AU CONTACT d'une limite (requête
ST_DWithin du 06/09) — `97410000CE0039` (St-Benoît/Ste-Rose), `97415000AM0169`
(St-Paul/Trois-Bassins), `97418000AK0061` (Ste-Marie/Ste-Suzanne), épinglés dans
`filtres/echantillons/communes/frontieres.json`. Vérifiés : commune de rattachement servie
+ partition GPU de la zone au centroïde (`DU_<insee>` — une couche de la commune voisine
collée casserait). Preuve : attendus permutés vers la voisine → 3 témoins cassés.

**4.4 — l'échantillon producteur, 15 cartes × 24 communes**
(`filtres/echantillon_communes.py` + `filtres/echantillons/communes/*.json`, verrou V4d
structurel : une ligne par carte × commune sinon cassé) :
- **population** : 24 attendus INSEE réels (geo.api.gouv.fr, relevé CIRCUIT-3 06/09) ;
- **risques (CatNat)** : 24 attendus GASPAR réels lus à l'API le 06/09 — **et ce relevé a
  mordu le jour même** : (1) le cache fiche commune du 31/08 servait encore `catnat=10`
  TRONQUÉ (le bug d'avant la réparation CIRCUIT-3 — la table était réparée, l'écran servait
  le cache d'avant) → cache des 24 rafraîchi ; (2) un arrêté GASPAR nouveau à Saint-Joseph
  → `ingest-catnat` rejoué (427 lignes producteur) ;
- 13 cartes `a_valider` avec proposition par carte (ECHANTILLONS-A-VALIDER.md § communes) ;
- 2 écarts de définition ASSUMÉS et notés dans les fichiers (verdict `assume`, jamais un
  faux vert ni un warning éternel) : Saint-Denis population (Filosofi carreaux sous-couvre
  la commune dense, −16 % vs légale) ; Saint-Joseph CatNat (doublon strict GASPAR
  dédoublonné par notre contrainte unique : 20 servi / 21 producteur).

**Preuves cassé → vert** (`tests/verrous/test_lot4_communes.py`, 11 tests) : code fantôme
rejeté par Postgres ; contrainte absente → cassé ; lignes héritées → à décider ; jointure
décalée → cassé ; première-ligne-partout → cassé ; frontières permutées → 3 cassés ; trou
d'échantillon posé → cassé ; `ecart`/`assume` distingués (une dérive NOUVELLE sort `ecart`).

## Lot 5 — verrou des concepts et des moteurs (livré)

**V5a — un concept = un id** : libellés et définitions NORMALISÉS (casse, accents, espaces)
sur les 168 données — zéro collision hors DEUX groupes assumés, déclarés dans le code
(`DEFINITIONS_PARTAGEES_ASSUMEES`) et motivés dans CONCEPTS-CANONIQUES.md (les deux
hypothèses saisies de la calculette ; les 5 mosaïques ortho par période). La revue
CIRCUIT-2 est rejouée par construction : le verrou balaie TOUT le registre (fiches, outils,
PDF, couches) à chaque passage.

**V5b — une donnée = une fonction** : chaque id porte un producteur nommé ; `sql_propre = 0`
et `front = 0` (les gardes CIRCUIT-2, réunies dans les verrous) ; l'intégrité du registre
(`verifier()`) est jouée dans le même verrou. Mesure réelle : 113 moteur · 53 passe_plat ·
3 constantes.

**V5c — zéro couple silencieux** : les 238 couples (donnée, robinet) déclarés sont ventilés
— 8 sondés (`SONDE_COUVRE`, la vérité de ce que la sonde compare, vérité CROISÉE avec le
registre par test), 112 raisonnés (`NON_SONDES` : chaque chiffre multi-robinets non comparé
porte SA raison — golden, recette_exports1, V2a, recomptage humain, ou « extension sonde à
décider Vic »), 118 mono-robinet (aucun partenaire de comparaison : golden/règles font foi).
Un couple sans rien = cassé, jamais un « non couvert ».

**5.3 — témoins tournants** : `sonde_circuit.temoins_tournants(db)` — 50 parcelles tirées
parmi celles CONSULTÉES la veille (`consultation_log.idu`), tirage déterministe du jour
(`md5(idu || date)` — rejouable dans la nuit, différent chaque jour), ajoutées aux témoins
fixes dans `verifier_categorielle` (compte `temoins_tournants` au verdict).

**Preuves cassé → vert** (`tests/verrous/test_lot5_concepts.py`, 10 tests) : doublon de
libellé normalisé posé → casse ; définition partagée non assumée → casse ; `sql_propre`
réintroduit → casse ; donnée sans fonction → casse ; chiffre retiré de NON_SONDES (silence
posé) → casse en nommant le couple ; tirage tournant déterministe, borné, et vide si rien
n'a été consulté la veille.

## Lot 6 — la commande, la porte, la page (livré)

**6.1 — une commande, trois joueurs** :
- `labuse circuit verrous` joue les 16 verrous (lots 1-5), une ligne chacun (phrase,
  verdict, preuve), sort en erreur au premier cassé, journalise (geste `controle`, cible
  `verrous`). PIÈGE : passer par le binaire `labuse` (garde `__main__` en milieu de cli.py).
- **pytest** : marque `verrous` — `tests/verrous/` (65 tests, 5 fichiers), plus `-m local`
  qui rejoue tout sur la base réelle.
- **la sonde de nuit** : le job `coherence-robinets` joue AUSSI les verrous après le
  contrôle (résultat au Journal + notification admin dédupliquée si cassé).
- **`deploy.sh`** : la PORTE, jouée AVANT toute pose — binaire introuvable = refus, verrou
  cassé = refus, aucun contournement (vérifié par test).

**6.2 — la page** (aucun nouvel onglet) :
- le Résumé reçoit trois lignes composées CÔTÉ SERVEUR (`composer(verrous=…)`) depuis la
  synthèse à coût page (`synthese_pour_page` : dernier passage journalisé + orphelines et
  muets immédiats — jamais V1b rejoué au chargement) : **« verrous cassés »** (rouge, À
  corriger), **« tables orphelines à purger »** et **« réservoirs sans lecteur, données
  sans réservoir »** (gris, À décider). Sans synthèse, le Résumé d'avant est inchangé
  (testé).
- le détail du repère « 68 » montre **la carte table → réservoir** (68 réservoirs, tables +
  couches + millésime — la déclaration de `registre/tables.py`), et les « lignes en base
  non servies » disent désormais leur statut de PREMIÈRE CLASSE (« alias de … »,
  « retirée — raison », hub, chantier).
- **captures** : `docs/CIRCUIT/RECETTE-CIRCUIT-5/` (harnais CIRCUIT-P réutilisé, fixtures
  RÉELLES du 06/09, zéro base touchée — `qa/circuit5_captures.mjs`) : 01 avant · 02 après
  (lignes à décider) · 03 verrou cassé (ligne rouge V3b/V4b, variante composée par le VRAI
  composer) · 04 la carte au détail du 68.

**6.3 — VERROUS.md** : une page pour Vic, un verrou par ligne (la phrase, ce qui le
garantit, où ça se lit), les cinq phrases du mandat rattachées à leurs verrous, et les
gestes qui restent. Un test vérifie que chaque verrou y a sa ligne.

## Définition de fini — l'état

- `labuse circuit verrous` existe, joue les 16 verrous des lots 1-5, **passe sur la base
  locale (0 cassé, 3 à décider)** ; `deploy.sh` le joue en porte. ✔
- Chaque verrou prouvé cassé sur un cas construit puis vert — preuves REJOUABLES dans
  `tests/verrous/` (65 tests), citées lot par lot ci-dessus. ✔
- **68 = 68 = 68** partout (vitrine SQL, prédicat, page) ; aucune table lue hors carte
  (statique + exécution) ; TABLES-ORPHELINES.md livré (32, 1,56 Go) avec `labuse tables
  purger` — rien de supprimé. ✔
- 15 cartes × 24 communes : population et CatNat à attendus producteur RÉELS, 13 cartes
  « à valider » avec proposition. ✔
- VERROUS.md se lit sans le code. ✔
- Suites : pytest **2680 passed** (4 échecs = la baseline d'accumulation, inchangés),
  vitest 181, tsc 0. Rien mergé, branche poussée. ✔

## Preuves des verrous (cassé → vert)

Chaque verrou a son couple de preuves DANS les tests (`tests/verrous/`) — rejouables à
chaque suite, pas des sorties d'un soir. Les sections de lot ci-dessus citent le cas
construit et le verdict des deux sens.

## Dettes reprises des comptes-rendus 0→4 et P

Lues dans COMPTE-RENDU-CIRCUIT-1→4 et P (P3 surtout), vérifiées dans le code :

- **La sonde écrit des libellés, pas des ids** (dette CIRCUIT-P3) : `circuit_ecarts.robinet_a/robinet_b`
  et `circuit_eau_ancienne.robinet` portent des chaînes d'affichage (« attrs.degre (DEAL brut) »,
  « fiche parcelle / filtres ») — DDL dans `sonde_circuit.py`. Le rattachement au registre passe
  aujourd'hui par `circuit_etats.robinets_touches()` (join par `chiffre_id`). → lot 3.3.
- **Eau DPE non attribuable** : lignes d'eau ancienne avec `chiffre_id` hors registre
  (« (chiffres DPE) ») → invisibles au niveau robinet. → lot 3.3.
- **Lignes `data_sources` hors vitrine** (CIRCUIT-0 lot 1) : doublons id 2/65/67, retirés 49/50,
  hubs 11/12/14, a_faire 80/89/95 (+ ECLN/LOVAC voulues-absentes). La vitrine = `WHERE_AFFICHEES`
  (`sources_catalog.py:36`) : statuts `connecte|manuel`, préfixes `DOUBLON/RETIRÉ/DORMANT` dans
  `technical_notes`, `affichage_desactive`, `masquees`. → lot 2 (statut de première classe).
- **Tables mortes CIRCUIT-0** : `parcel_residuel_base_legacy`, `parcel_au_statut_pre_m32`,
  `m6_snapshot_*`, `*_pre_v8` — aucun SELECT dans `src/labuse/api/`. → lot 1.3.
- **Nombre de réservoirs** : base locale = **66** servis (68 = production, EDF HTA 93 / TCSP 94 /
  Réunion Express 95 sont sur `fix/retours-12` non mergé). Le verrou « 68 = 68 » est donc une
  **égalité de comptes vivante** (data_sources servies = vitrine = registre = page), jamais un
  68 littéral (interdit « valeur codée en dur »).
- **Matière première du lot 1** : `docs/CIRCUIT/inventaire/reservoirs.csv` porte déjà
  `tables_servies` + `millesime_servi` par réservoir (79 lignes) ; les ids réservoir du registre
  (`Donnee.reservoirs`) sont ceux de ce CSV.
- **Référentiel 24 communes** : `ingestion/run_all.py:REUNION_COMMUNES` (97401→97424),
  exposé `INSEE_24`/`NOMS_24` dans `filtres/cadre.py`.

---

# 5b — Les restes tranchés (CIRCUIT-5b, 06/09/2026)

*Branche `feat/circuit-5b`, depuis `main` (CIRCUIT-5 mergé, `18261fc9`). Cinq lots, un commit
et un push chacun, rien mergé. Décisions prises par Vic le 06/09/2026 ; CC les applique et
vérifie avec `labuse circuit verrous --complet` en fin de chaque lot.*

**Repère « avant » (base locale, main).** `labuse circuit verrous --complet` : **16 verrous
joués, 0 cassé, 3 à décider** — V1c (2 orphelines `p_model_static_pre_v8`,
`parcel_residuel_pre_v8`), V1d (**8 réservoirs sans lecteur** : bd_ortho_irc, cadastre_epoque,
inpi_rne, lidar_hd_mnh, mobpro, office_eau_chroniques, parkings_osm_aper,
recherche_entreprises_dinum), V4a (1 ligne SIRENE hors référentiel, contrainte NOT VALID).
V2a : **68 = 68 = 68**.

## Lot 1 — les quatre « à rattacher » entrent au catalogue

Les quatre tables servies sans ligne `data_sources` (RATTACHEMENTS_A_DECIDER de CIRCUIT-5)
sont désormais des **sources de première classe**. Pour chacune : une ligne `data_sources`
complète (`ingestion/seed_sources.py`), une entrée `MODE_ET_CADENCE`, une raison de
non-surveillance (`sentinelle.RAISONS_NON_SURVEILLEES` — millésimes annuels/mensuels sans
témoin amont à empreinte stable, suivis par la cadence et la page Circuit), un slug au pont
(`circuit_etats.NOM_VERS_SLUG`), sa place à la carte (`registre/tables.py:RESERVOIR_TABLES`)
et ses lecteurs déclarés au registre (`registre/donnees.py`) :

| Table | Slug | Producteur | Cadence | Lecteur(s) déclaré(s) |
|---|---|---|---|---|
| `mairies` | `annuaire_service_public` | DILA (service-public.fr) | mensuelle | `mairie_coordonnees` (déjà déclaré) |
| `rnic_coproprietes` | `rnic_anah` | Anah (RNIC) | annuelle | `coproprietes_liste` (déjà déclaré) |
| `rpls_commune` | `rpls_sdes` | SDES (RPLS) | annuelle | **`parc_social_rpls_logements`** (nouvelle donnée, robinet `fiche_parcelle_marche`) |
| `commune_conso_enaf` | `enaf_cerema` | Cerema (artificialisation) | annuelle | `pression_zan_ha`, `zan_reste_ha` (réservoir déclaré) |

`rpls_commune` et `commune_conso_enaf` quittent `TABLES_EXPLOITATION` (elles étaient marquées
« servie sans réservoir ») pour `RESERVOIR_TABLES` ; `annuaire_service_public` et `rnic_anah`
y étaient déjà (leurs lecteurs aussi). `RATTACHEMENTS_A_DECIDER` est désormais **vide**.

**Doute écrit (décision : option la plus sûre).** Le mandat dit que RPLS « porte les données
`taux_lls_pct` et voisines ». Le code sert en réalité `taux_lls_pct` depuis l'inventaire SRU
(`commune_contexte_sru` → réservoir `sru_dhup`, source « Inventaire SRU (DHUP) »), tandis que
`rpls_commune` porte le **parc social** (nb_logements, construction médiane) servi au contexte
marché de la fiche parcelle, au Flash et au PDF (`api/app.py` marche_secteur, `flash/data.py`,
`pdf_premium.py`). Repointer `taux_lls_pct` sur RPLS aurait **changé une valeur servie** (le
taux LLS vient bien du SRU). Choix : ne rien déplacer de servi ; déclarer le vrai lecteur de
RPLS — une donnée neuve `parc_social_rpls_logements` (parc social RPLS, millésime 01/01/2025).

**Résultat.** V2a : **72 = 72 = 72** (vitrine SQL, prédicat Python, page) ; 66 tables de
réservoir, une génération chacune (V3a). `labuse circuit verrous --complet` : 0 cassé, 3 à
décider inchangées (V1c, V1d, V4a — lots 2/3/4). Tests : `tests/verrous/` +
`tests/test_sentinelle.py` (couverture 71 → **75** sources) + `tests/test_registre.py`
(MODE_ET_CADENCE 80 → **84**) verts. `VERROUS.md` mis à 72.
