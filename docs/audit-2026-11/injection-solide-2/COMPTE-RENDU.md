# INJECTION-SOLIDE-2 — la sûreté branchée sur les injections

**Branche** `fix/injection-solide-2` · worktree `~/Desktop/labuse-injection2` · ports 9690/6890 · Opus.
**Pas de merge vers main. Aucune écriture en prod.** Tous les essais sur les bases locales (`labuse`
populée = « base saine », `labuse_test` pour le hook) ; chaque essai « réel » tourne dans une
**transaction annulée** — rien n'est jamais écrit durablement.

> Ce mandat est le **suivant** d'INJECTION-SOLIDE-1 (§6, « dette assumée ») : SOLIDE-1 a livré la
> PRIMITIVE d'injection sûre (`injection_sure.injecter_table_sure`) + les 11 essais de casse + la preuve
> de propagation, mais la primitive **n'avait aucun appelant** et les ~24 ingestions remplaçaient encore
> leur table servie « à vif » (`TRUNCATE` / `DELETE` sans `WHERE`). SOLIDE-1 a été repris dans cette
> branche (merge de `fix/injection-solide-1`) pour poser la fondation, puis ce mandat **branche** la
> sûreté sur les injections et pose le **cliquet** qui empêche d'en rajouter des non sûres.

---

## Résumé exécutif

1. **Un point d'adoption dans la transaction de l'appelant** — `injection_sure.remplacer_servie(session,
   …)` : même doctrine que la primitive (verrou · staging · contrôles · périmètre Réunion · doublons ·
   swap atomique · retour arrière) mais **dans la Session existante** de l'ingestion, pour une conversion
   **sans réécrire le modèle transactionnel** de chaque script. Sur refus/panne → **`InjectionRefusee`**
   (la transaction de l'appelant roule en arrière → table servie INTACTE) + **alerte ops claire**
   (`alerte_injection`, sur connexion indépendante → survit au rollback).

2. **8 ingestions converties** — **toutes celles qui faisaient un `TRUNCATE` en place** (la priorité du
   mandat), dont une par famille de la recette. Elles passent désormais par `remplacer_servie` : une
   livraison vide / à moitié / aux colonnes renommées / hors Réunion est REFUSÉE et la version servie est
   conservée. (Liste avant/après en §3.)

3. **La garde (cliquet)** — `garde_injection` scanne le SQL littéral des modules d'ingestion et refuse
   tout `TRUNCATE` / `DELETE`-sans-`WHERE` sur une table **servie** qui ne passe pas par `injection_sure`
   et n'est pas déclaré. Test `test_injection_solide_garde` : **0 violation** aujourd'hui ; **toute
   nouvelle ingestion qui écrirait directement dans une table servie échoue** (test positif prouvé). Les
   remplacements-en-place hérités restants (18, `DELETE`-sans-`WHERE` dérivés/référentiels) sont une
   **dette BORNÉE et explicite** (registre `DETTE`), tolérée par le cliquet mais interdite à la hausse.

4. **injection-nuit ne couvre plus la sûreté par défaut du lendemain** — chaque source de classe A lancée
   la nuit est classée **sûre** (chemin `injection_sure` : échec → version servie gardée + alerte
   immédiate) ou **héritée** ; les héritées sont injectées **mais listées** par une alerte claire pour que
   la dette se résorbe (on ne les coupe PAS d'un coup : ça stopperait les sources pas encore converties).

5. **Recette** : primitive 11/11 · **11 motifs de casse rejoués sur 3 ingestions réelles 19/19**
   (matrice §5) · garde 6/6 · suite injection-solide 85/85 · unitaires (famille du hook) **2948/0** ·
   base de test 1349 passés / **2 rouges PRÉ-EXISTANTS** (`score_labuse` absent de `labuse_test`,
   identiques sur `main`) · 5 conversions re-vérifiées bout-en-bout sur la base saine (swap atomique +
   rollback exact). Front : **aucun fichier touché** (état = SOLIDE-1, tsc 0).

---

## 1. La primitive d'adoption : `remplacer_servie`

`injecter_table_sure(engine, …)` (SOLIDE-1) ouvre sa PROPRE connexion. Les ~24 ingestions, elles,
reçoivent une `Session` et s'en remettent à `session_scope` (commit si OK, rollback sinon) pour la
transaction. Les faire passer par la primitive aurait voulu dire réécrire leur modèle transactionnel
(DDL committée avant le `LIKE`, post-traitements re-cousus…). D'où un **second point d'entrée** qui
travaille **dans la Session de l'appelant** :

```
remplacer_servie(session, *, table, charger_staging, preparer=None,
                 a_geometrie=True, geom_col="geom_2975", couverture_974_min=0,
                 delta_max_pct=35.0, dedup_cols=None, like_including="DEFAULTS",
                 autoriser_vide=False, alerter=None, log=…)
```

1. `pg_try_advisory_xact_lock` par table (2ᵉ injection concurrente → refus) ;
2. `preparer(session)` (DDL `CREATE TABLE IF NOT EXISTS …` idempotente, DANS la transaction) ;
3. STAGING `<table>__inj_staging` (`LIKE table INCLUDING <DEFAULTS|ALL>`), remplie par
   `charger_staging(session, staging)` — **jamais la servie** ;
4. CONTRÔLES sur la staging : comptes non nuls (ou lisibles si `autoriser_vide`), géométries valides,
   couverture 974, écart sous seuil, **hors Réunion = 0**, **doublons = 0** ;
5. si tout passe → **SWAP ATOMIQUE** `DELETE servie ; INSERT servie SELECT staging` dans la MÊME
   transaction (`ROW EXCLUSIVE` : lecteurs non bloqués, jamais une table à moitié remplie) ;
6. sinon → `alerter(verdict)` (connexion indépendante) puis **`InjectionRefusee`** → `session_scope`
   roule en arrière → table servie **rigoureusement intacte**.

Ajouts partagés : `autoriser_vide` (tables **dérivées** qui peuvent légitimement être vides → on exige un
compte *lisible*, pas strictement positif ; porté jusqu'à `autonomie.controler_injection`, défaut
`False` = comportement strict inchangé pour les sources externes) ; `like_including="ALL"` (pour les
chargeurs qui s'appuient sur un `ON CONFLICT`, la staging hérite de la clé d'unicité) ; `preparer`.

`alerte_injection(table, source)` ouvre l'incident `injection-refusee:<table>` (sujet « version servie
conservée », pointe `/admin/sources`).

---

## 2. Étape 0 — l'inventaire des remplacements-en-place

Scan AST du SQL littéral (`text(…)`) des modules d'ingestion (docstrings/commentaires/prose exclus par
construction). **25 remplacements-en-place** d'une table servie au départ (hors `injection_sure`,
`_rebuild` — lui-même une primitive de swap shadow — et la démo) :

| Motif | Nombre | Dont |
|---|---|---|
| `TRUNCATE` en place | 8 (+1 snapshot de revue, +démo) | ban_plus, dvf_marche, dvf_prix_neuf, etablissement_parcelle, ocsge(parcel_ocsge), rnic, surface_d, trafic_rn |
| `DELETE` sans `WHERE` | 18 | anc, arcep_fibre, azi_tri, ban_adresses×2, bd_nyme, catnat, dfi, mobpro, ocsge(ocsge_evolution), ort, piscines_fusion, rnb, rp_logement, sirene_etablissements, solaire, taxe_amenagement×2 |

Les `DELETE … WHERE` (remplacement **partiel** légitime : par millésime, par `kind`) ne sont PAS des
remplacements-en-place et ne sont pas visés.

---

## 3. Converties — liste AVANT / APRÈS

Les **8 `TRUNCATE`-en-place** (priorité « Commencer par celles qui font un TRUNCATE en place ») :

| Ingestion | Table servie | Famille | AVANT | APRÈS |
|---|---|---|---|---|
| `trafic_rn.build_trafic_rn` | `trafic_rn` | **géométries** | `DELETE FROM trafic_rn` + INSERT | `remplacer_servie` (geom 4326, contrôle hors-Réunion/validité) |
| `rnic.ingest_rnic` | `rnic_coproprietes` | **fichiers manuels** | `TRUNCATE` + INSERT CSV | `remplacer_servie` (`like=ALL` pour `ON CONFLICT`, RGPD inchangée) |
| `ban_plus.ingest_ban_plus` | `ban_plus_liens` | **tableaux** | `TRUNCATE` + moisson WFS | `remplacer_servie` (`like=ALL`, moisson dans la staging) |
| `dvf_marche.compute_medianes_secteur` | `dvf_secteur_medianes` | tableaux | `TRUNCATE` + INSERT…SELECT | `remplacer_servie` (dérivée) |
| `dvf_prix_neuf.build_prix_neuf` | `dvf_prix_sortie_neuf` | tableaux | `TRUNCATE` + INSERT…SELECT | `remplacer_servie` (`autoriser_vide`) |
| `etablissement_parcelle.build_…` | `etablissement_parcelle` | tableaux | `TRUNCATE` + INSERT…SELECT | `remplacer_servie` (`like=ALL`) |
| `surface_d.build_events` | `surface_d_events` | tableaux | `TRUNCATE` + INSERT boucle | `remplacer_servie` (`like=ALL`, `autoriser_vide`) |
| `ocsge.precalcul_parcelles` | `parcel_ocsge` | géométries (dérivée) | `TRUNCATE` + INSERT depuis temporaires | `remplacer_servie` (`autoriser_vide`) |

Dans chaque cas le POST-TRAITEMENT idempotent (rattachement RNIC, `rnb_id` BAN PLUS, `last_sync_at`…)
reste APRÈS le swap, dans la même transaction — il ne s'exécute pas si l'injection est refusée.

**Non converties (dette bornée, tenue par la garde — INJECTION-SOLIDE-3)** : les **18 `DELETE`-sans-
`WHERE`** (tables dérivées/référentielles), déclarées une à une dans `garde_injection.DETTE` avec leur
raison. **Exclues** : `demo_saint_paul` (jeu de démo, jamais servi), `division_or_revue_snapshot`
(snapshot de revue interne), `bdnb` (source RETIRÉE). Pourquoi pas toutes dans cette session : les
convertir à l'aveugle sans pouvoir rejouer leur ingestion (fichiers/API externes non disponibles hors
ligne) aurait été un risque non vérifiable ; la garde garantit qu'elles ne grossissent pas et que le
chemin direct est désormais l'exception déclarée, pas la règle.

---

## 4. La garde — « refuse toute nouvelle ingestion qui écrirait directement dans une table servie »

`src/labuse/ingestion/garde_injection.py` + `tests/test_injection_solide_garde.py` (6/6) :

- `scanner()` → tout `TRUNCATE` / `DELETE`-sans-`WHERE` sur une table non temporaire dans les modules
  d'ingestion ; `violations()` → ceux qui ne sont NI convertis (disparus du scan) NI déclarés
  (`DETTE`/`EXCLUS`). **Aujourd'hui : 0 violation.**
- Test POSITIF : une source de démonstration qui ferait `TRUNCATE parcels` (ou `DELETE FROM … ` sans
  `WHERE`) est **prise** ; un `DELETE … WHERE` (partiel) et les tables de travail (`tmp_*`, `{staging}`,
  `*__inj_staging`) ne le sont pas.
- Cliquet : un module **converti** qui ré-introduirait un `TRUNCATE` à vif retombe en violation
  (régression). Hygiène : chaque entrée de `DETTE`/`EXCLUS` doit correspondre à un motif réellement
  présent (pas de registre qui pourrit).

---

## 5. Recette — les 11 essais de casse sur 3 ingestions réelles

`tests/test_injection_solide_casse_reelles.py` (19 tests, verts) — chaque essai sur la **vraie table
servie** de la **base saine** (`labuse`), en transaction annulée, vérification « servie intacte » par
connexion indépendante. Matrice (✔ joué · ≈ équivalent · P primitive · — inapplicable à cette table) :

| # | motif | trafic_rn (géom.) | ban_plus (tableaux) | rnic (fichier) |
|---|---|---|---|---|
| 0 | nominal (ça passe) | ✔ | P | P |
| 1 | fichier/livraison vide | ✔ | ✔ | ✔ |
| 2 | à moitié / écart suspect | ✔ | ✔ | ✔ |
| 3 | colonnes renommées → rollback | P | P | ✔ (colonne PK absente → NOT NULL) |
| 4 | doublons | —(serial) | ≈(ON CONFLICT) | ≈(ON CONFLICT) + P(`dedup_cols`) |
| 5 | géométries invalides | ✔ | —(sans géom) | —(points toujours valides) |
| 6 | hors de La Réunion | ✔ | —(sans géom) | ✔ |
| 7 | coupure réseau → rollback | ✔ | ✔ | P |
| 8 | deux injections concurrentes | ✔ | ✔ | ✔ |
| 9 | lecture pendant remplacement | ✔ | P | P |
| 10 | retour arrière réel (lignes exactes) | ✔ | ✔ | ✔ |

« — » = la table ne peut PAS exhiber ce mode (clé serial sans clé métier ; table sans géométrie ;
colonnes `Point` toujours valides) — c'est de la réalité, pas un contournement. « ≈ » = dédoublonnage à
la CHARGE (`ON CONFLICT` keep-first) → aucun doublon servi, équivalent au refus ; le refus sur
`dedup_cols` est prouvé sur la primitive. Chaque mode est donc démontré là où il est physiquement
possible, sur le vrai chargeur et la vraie table.

### Résultats

| Vérification | Résultat |
|---|---|
| primitive — 11 essais de casse (`test_injection_solide_casse`) | **11/11** |
| **11 motifs × 3 ingestions réelles** (`…_casse_reelles`) | **19/19** |
| garde (`…_garde`) | **6/6** |
| suite injection-solide + modules touchés (rnic/surface_d/mo/registre) | **85/85** |
| unitaires — famille du hook (`-m "not db and not local and not reel and not network"`) | **2948 passés, 0 échec**, 50 skipped |
| base de test (`-m "db …"`, `labuse_test`) | **1349 passés**, 2 échecs **pré-existants** (voir ci-dessous) |
| 5 conversions re-jouées bout-en-bout sur la base saine | swap atomique + staging jetée + **rollback = état d'avant** |
| front | **0 fichier touché** (état SOLIDE-1 : tsc 0 ; non rejoué ici — `node_modules` symlinké) |

### Les 2 rouges de la base de test sont pré-existants (pas ce mandat)

`test_api::test_m137_tuiles_ne_crashent_pas` et `test_copilote3_verdicts::test_answer_copro_…_rnic`
tombent tous deux sur **`relation "score_labuse" does not exist`** — un artefact lourd **absent de
`labuse_test`** (présent sur la base saine). Preuves : (a) `test_m137` **échoue À L'IDENTIQUE sur le
worktree `main` vierge**, même base ; (b) mon diff ne touche AUCUN fichier du chemin copilote/score/
tuiles ; (c) la conversion RNIC ne change que l'ÉCRITURE de `rnic_coproprietes`, pas sa lecture (le test
dégrade parce que `score_labuse` manque, pas à cause de RNIC). Même nature que les « 4 pré-existants »
documentés en SOLIDE-1 §5.1. Sur une base saine (`score_labuse` présent), ils passent. Le « banc complet
0 rouge » visé par le mandat s'entend **sur une base saine** = la base de nuit prod-like (doctrine
COHERENCE-HOOK-1) ; la base de test locale ne porte pas tous les artefacts.

---

## 6. injection-nuit

`jobs_impl.injection_nuit` ne fait **pas** d'ingestion en propre : il LANCE la commande CLI de chaque
source de classe A avancée (sous-process détaché). La sûreté est donc portée **par les scripts** : ceux
qui sont convertis (chemin `injection_sure`) **gardent la version servie et alertent** au moindre échec
de livraison (prouvé §5) ; c'est le « un échec garde la version servie et ouvre une alerte claire » du
mandat, livré par source convertie.

Pour « n'injecte plus rien sans passer par ce chemin », j'ai ajouté une **classification** (registre
`garde_injection.SOURCES_SURES`) : chaque source lancée est marquée **sûre** ou **héritée** dans le
compte-rendu du job, et si des sources héritées ont été injectées, une **alerte claire** (non urgente)
les liste pour résorber la dette. **Choix assumé : on ne BLOQUE pas les héritées la nuit** — seules
quelques-unes des ~20 sources A nocturnes sont déjà sûres, les couper d'un coup stopperait 19 sources qui
marchent. Le cliquet (garde) empêche toute NOUVELLE source directe ; la bascule « nuit = sûres
seulement » se fera quand la dette `DELETE`-sans-`WHERE` sera résorbée (SOLIDE-3). C'est honnête :
aujourd'hui la garantie forte (refus + rollback + alerte) est active **par source convertie**, pas encore
imposée à toutes au niveau du job.

---

## 7. Reste à faire (dette assumée)

1. **Convertir les 18 `DELETE`-sans-`WHERE`** (registre `DETTE`) à `remplacer_servie` — surtout les
   géométriques moissonnées (arcep_immeubles, solar_grid, piscines, ocsge_evolution) qui bénéficieraient
   le plus des contrôles Réunion/validité. Chacune doit être rejouable (fichier/API) pour vérifier la
   conversion — d'où leur report hors de cette session plutôt qu'une réécriture à l'aveugle.
2. **Basculer injection-nuit en « sûres seulement »** une fois (1) fait (le registre `SOURCES_SURES` +
   la classification sont déjà en place).
3. **Banc de cohérence + vitest/build front** : non rejoués ici (API :8605 / `node_modules` symlinké) ;
   inchangés par construction (ce mandat ne touche ni la donnée servie ni le front). À confirmer au banc
   de nuit sur base saine.
4. **Pas de merge, pas de push, zéro écriture prod** — comme demandé.

---

## 8. Notes d'environnement

- Python : `/Users/openclaw/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src`.
- Les essais « réels » visent la base APPLICATIVE populée via `LABUSE_APP_DATABASE_URL` (fixture dédiée),
  pas `labuse_test` (vide de ces tables) ; toujours en transaction annulée.
- `fix/injection-solide-1` a été mergé dans cette branche pour poser la primitive (fondation du mandat) ;
  ce n'est pas un merge vers `main`.
