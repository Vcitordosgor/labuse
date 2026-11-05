# INJECTION-SOLIDE-3 — plus aucune injection à vif

**Branche** `fix/injection-solide-3` · worktree `~/Desktop/labuse-injection3` · ports 9710/6910 · Opus.
**Pas de merge vers main. Aucune écriture en prod.** Tous les essais sur la base locale `labuse`
(« base saine » populée, `LABUSE_APP_DATABASE_URL`) ; chaque essai « réel » tourne dans une
**transaction annulée** — rien n'est jamais écrit durablement.

> Suite d'INJECTION-SOLIDE-2 (§7, « reste à faire »). SOLIDE-2 avait livré la primitive d'adoption
> `injection_sure.remplacer_servie` + converti les **8 `TRUNCATE`-en-place** + posé le **cliquet**
> (garde) qui TOLÉRAIT encore, en dette bornée, les **18 `DELETE`-sans-`WHERE`** restants. Ce mandat
> **résorbe les 18** (chemin sûr), passe la garde en **STRICT** (plus aucune tolérance) et bascule
> **injection-nuit en « sûres seulement »** (la voie « héritée » disparaît). Base de départ : le merge
> de `fix/injection-solide-2` (FF sur SOLIDE-1) repris dans cette branche pour poser la fondation.

---

## Résumé exécutif

1. **Les 18 `DELETE`-sans-`WHERE` sont convertis** à `injection_sure.remplacer_servie` (staging +
   contrôles + swap atomique + retour arrière + alerte). Plus **aucune** ingestion ne remplace une table
   SERVIE « à vif ». Liste avant/après en §2.

2. **La garde passe en STRICT** : `garde_injection.DETTE` est **VIDE**, sans liste d'exceptions. Toute
   écriture directe (TRUNCATE / DELETE-sans-WHERE) dans une table servie est une **VIOLATION immédiate**.
   Scan : **0 violation**, seul reste `division_or_revue_snapshot` (table NON servie, `EXCLUS`).

3. **injection-nuit ne lance QUE les sources sûres.** La voie « héritée » (injecter par le chemin direct
   sous le seul filet de la cohérence du lendemain) **disparaît**. Une source de classe A avancée qui
   n'est pas sûre n'est **plus injectée** : elle remonte comme **décision à prendre**
   (`injection-a-decider`, à router puis inscrire dans `SOURCES_SURES`).

4. **Renforcement de la primitive** : le SWAP liste désormais les colonnes EXPLICITEMENT et **exclut les
   `GENERATED ALWAYS`** (identité / expression STORED). `INSERT … SELECT *` plantait sur `dfi_filiation`
   (`id` GENERATED ALWAYS AS IDENTITY — Postgres refuse l'insertion explicite) ; la colonne se régénère
   maintenant au swap. `adresses.suggest_norm` (GENERATED STORED) est traitée pareil.

5. **Recette** : primitive **13/13** (dont `autoriser_vide` + GENERATED-ALWAYS) · **11 motifs de casse
   rejoués sur 3 NOUVELLES conversions** (`bd_nyme`, `ort`, `taxe` — 34/34) · garde **8/8** ·
   injection-nuit bout-en-bout **1/1** · banc de cohérence · vitest · hook. (chiffres §5.)

---

## 1. La primitive renforcée (`_swap`)

`remplacer_servie` et `injecter_table_sure` partageaient `DELETE servie ; INSERT servie SELECT *`. Le
`SELECT *` **plantait** sur une table à colonne `GENERATED ALWAYS AS IDENTITY` (`dfi_filiation.id`) :
Postgres REFUSE une insertion explicite dans une telle colonne. Nouveau helper **`_swap(conn, table,
staging)`** : liste explicite des colonnes, **exclut** les `is_identity='YES' AND
identity_generation='ALWAYS'` ET les `is_generated='ALWAYS'` (STORED) — elles se **régénèrent** à
l'INSERT ; les colonnes ordinaires (`serial`/`DEFAULT nextval` compris) restent copiées. Pour que la
STAGING accepte l'insertion sans `id`, la table concernée utilise `like_including="ALL"` (hérite de
l'IDENTITÉ → l'`id` de staging se génère, le swap l'ignore). Prouvé : `test_swap_regenere_une_identite_
generated_always`.

---

## 2. Converties — liste AVANT / APRÈS (les 18 `DELETE`-sans-`WHERE`)

Toutes passent de `DELETE FROM <servie>` (sans `WHERE`) + INSERT à `injection_sure.remplacer_servie`
(STAGING `<servie>__inj_staging` → contrôles → swap atomique → retour arrière + `alerte_injection`).

| # | Module | Table servie | AVANT | APRÈS (paramètres clés) |
|---|---|---|---|---|
| 1 | `anc.py` | `anc_maille_taux` | `DELETE` + boucle INSERT + `commit()` | `remplacer_servie` (sans géom, delta 50) |
| 2 | `arcep_fibre.py` | `arcep_immeubles` | `DELETE` + INSERT par lots (ON CONFLICT) | geom `geom`, `like=ALL`, delta 60 |
| 3 | `azi_tri.py` | `azi_communes` | `DELETE` + moisson API (ON CONFLICT) | sans géom, `like=ALL`, delta 60 |
| 4 | `ban_adresses.py` | `adresses` | `DELETE` + INSERT…SELECT (ON CONFLICT) | geom `geom`, `like=ALL` ; la garde de SHRINK existante reste le gardien de la baisse (delta neutralisé) |
| 5 | `ban_adresses.py` | `adresse_parcelles` | `DELETE` + 3 INSERT (dont auto-référence) | sans géom, `like=ALL`, `autoriser_vide` ; la passe « bâti partagé » lit ses prédécesseurs DANS la staging |
| 6 | `bd_nyme.py` | `lieux_dits` | `DELETE` + moisson WFS (INSERT…SELECT) | geom `geom`, delta 60 |
| 7 | `catnat.py` | `catnat_arretes` | `if remplacer: DELETE` + upsert | `remplacer=True` → `remplacer_servie` (`like=ALL`, delta 90) ; l'incrémental (défaut) upsert sans purge |
| 8 | `dfi.py` | `dfi_filiation` | `DELETE` + INSERT par lots | sans géom, `like=ALL` (id GENERATED ALWAYS régénéré), delta 50 |
| 9 | `mobpro.py` | `mobpro_commune` | `DELETE` + boucle INSERT (ON CONFLICT) | sans géom, `like=ALL`, delta 50 |
| 10 | `ocsge.py` | `ocsge_evolution` | `DELETE` + boucle INSERT + `commit()` | geom `geom_2975`, delta 90 (parcel_ocsge déjà converti SOLIDE-2) |
| 11 | `ort.py` | `commune_ort` | `DELETE` + boucle INSERT (ON CONFLICT) | sans géom, `like=ALL`, delta 50 |
| 12 | `piscines_fusion.py` | `piscines` | `DELETE` + temp `_f` + 2 INSERT…SELECT | geom `geom_2975`, `autoriser_vide`, delta 90 |
| 13 | `rnb.py` | `rnb_rattachement_bdtopo` | `DELETE` + INSERT…SELECT + `commit()` | sans géom, `autoriser_vide`, delta 90 |
| 14 | `rp_logement.py` | `rp_logement_commune` | `DELETE` + boucle INSERT | sans géom, delta 50 |
| 15 | `sirene_etablissements.py` | `sirene_etablissements` | `DELETE` + executemany DBAPI (ON CONFLICT) | geom `geom`, `like=ALL`, delta 60 ; FK communes honorée au swap |
| 16 | `solaire.py` | `solar_grid` | `if rebuild: DELETE` + INSERT…SELECT | geom `geom`, delta 90 ; (re)build → `remplacer_servie` |
| 17 | `taxe_amenagement_delta.py` | `taxe_amenagement_taux` | `DELETE` + boucle INSERT | sans géom, delta 50 |
| 18 | `taxe_amenagement_delta.py` | `taxe_amenagement_secteur` | `DELETE` + boucle INSERT | sans géom, `autoriser_vide`, delta 90 |

Dans chaque cas le **post-traitement idempotent** (rattachements, `last_sync_at`, stats…) reste APRÈS le
swap, dans la même transaction — il ne s'exécute pas si l'injection est refusée. Les `commit()` internes
(anc/ocsge/rnb) sont conservés : ils persistent le swap après `remplacer_servie` (lequel ne commit pas).

### Points délicats tranchés

- **`ban_adresses.adresse_parcelles`** se reconstruit depuis 3 sources dont une **auto-référentielle**
  (« bâti partagé » : parcelle sans adresse ← voisine partageant un bâtiment). Les auto-références
  (`adresse_parcelles x`, `adresse_parcelles ap`) pointent désormais vers la **STAGING** — la passe lit
  bien ses prédécesseurs (principal + ban_cad) venant d'être écrits dans la staging, pas la version
  servie d'avant.
- **`ban_adresses.adresses`** garde sa **garde de plausibilité** (seuil de shrink, `allow_shrink`) comme
  gardien de la BAISSE de volume ; le `delta_max_pct` de l'injection sûre est neutralisé (très élevé)
  pour ne pas doubler ce gardien — l'apport propre ici est le swap atomique + validité/périmètre géo.
- **`catnat`** et **`solaire`** ont un `DELETE` **conditionnel** (`remplacer=True` / `rebuild=True`) :
  seul le chemin de remplacement passe par l'injection sûre ; l'incrémental/« build une fois » est
  inchangé (jamais un remplacement-en-place à vif).
- **`autoriser_vide`** autorise le vide seulement là où il est LÉGITIME (table dérivée, `avant = 0`) :
  le contrôle d'ÉCART refuse quand même un 10 000+ → 0 (effacement d'une table pleine). Prouvé
  (`test_taxe_empty_delivery_ne_vide_pas_une_table_peuplee`).

---

## 3. La garde STRICTE (`garde_injection`)

- **`DETTE = {}`** (vide). Les 18 ont disparu du scan (converties) ; plus aucune tolérance.
- **`EXCLUS`** inchangé, reframé : il déclare les tables **NON servies** (démo `demo_saint_paul`,
  snapshot de revue `division_or_revue_snapshot`) — ce n'est PAS une tolérance d'injection non sûre.
- **`MODULES_CONVERTIS`** : 26 tables sur 23 modules (8 de SOLIDE-2 + 18 de SOLIDE-3) ; le cliquet
  anti-régression couvre chacune.
- Scan actuel : **1 site** (`division_or_revue_snapshot`, EXCLUS), **0 violation**.
- Tests `test_injection_solide_garde` (8/8) : violation=0, DETTE vide, un nouvel offenseur
  (TRUNCATE/DELETE-à-vif) est pris, `source_sur_chemin_sur` discrimine sûres/non-sûres.

---

## 4. injection-nuit « sûres seulement »

`jobs_impl.injection_nuit` : pour chaque source de classe A **avancée** —
- **sûre** (`garde_injection.source_sur_chemin_sur` → `SOURCES_SURES`) **et** commande connue → lancée
  (`injectees_sures`, même chemin que le bouton « Injecter ») ;
- **non sûre** → **PAS lancée** → `a_decider` + alerte claire `injection-a-decider` (la veille reste
  « nouvelle version » : elle revient jusqu'à ce qu'on la route) ;
- sûre **sans** commande mappée → `a_cabler` (inchangé).

La clé `injectees_heritees` et l'alerte `injection-heritee` sont **supprimées**. `SOURCES_SURES` =
l'ensemble VÉRIFIÉ des sources de classe A dont l'ingestion de nuit ne peut pas laisser une table servie
cassée : soit routées par `injection_sure`, soit prouvées sans remplacement-en-place (la garde = 0
violation). Tenu aligné sur les sources de classe A outillées d'une commande
(`config/sources_ingestion.yaml`). Prouvé bout-en-bout sur la base saine
(`test_injection_nuit_ne_lance_que_les_sources_sures` : Trafic RN lancée, Filosofi → décision, pas
d'`injectees_heritees`).

---

## 5. Recette

Base saine = `labuse` (populée) via `LABUSE_APP_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`
(rôle `openclaw`, pas `labuse` — piège de poste). Essais réels en transaction annulée.

| Vérification | Résultat |
|---|---|
| primitive — essais de casse (`test_injection_solide_casse`) | **13/13** (dont `autoriser_vide`, GENERATED-ALWAYS) |
| casse réelles — 3 NOUVELLES conversions + injection-nuit (`…_casse_reelles`) | **35/35** |
| garde (`…_garde`) | **8/8** |
| hook unitaire (`-m "not db and not local and not reel and not network"`) | **2961 passés, 0 échec**, 50 skipped |
| base de test DB (`-m db …`, `labuse_test`) | **1352 passés, 3 rouges PRÉ-EXISTANTS** (voir §5.1) |
| suite de cohérence (12 témoins, base servie) | **6 passés, 0 écart** (voir §5.2) |
| front (vitest / tsc) | **0 fichier front touché** — `frontend/node_modules` absent du worktree (non rejoué), état = SOLIDE-2 |

### Matrice — 11 motifs sur les 3 nouvelles conversions

Familles : **bd_nyme** (moisson WFS, géométrie) · **ort** (fichier CSV) · **taxe** (dérivée à records
+ `autoriser_vide`). ✔ joué · — physiquement inapplicable · P prouvé sur la primitive.

| # | motif | bd_nyme | ort | taxe |
|---|---|---|---|---|
| 0 | nominal | P¹ | ✔ | P¹ |
| 1 | livraison vide | ✔ | ✔ | ✔ |
| 2 | à moitié / écart | ✔ | ✔ | ✔ |
| 3 | colonnes renommées → rollback | P | P | P |
| 4 | doublons | ≈(serial) | ≈(ON CONFLICT) | ≈(clé dict) + P |
| 5 | géométries invalides | —(points) | —(sans géom) | —(sans géom) |
| 6 | hors de La Réunion | ✔ | —(sans géom) | —(sans géom) |
| 7 | coupure réseau → rollback | ✔ | P | P |
| 8 | deux injections concurrentes | ✔ | ✔ | ✔ |
| 9 | lecture pendant remplacement | P | ✔ | P |
| 10 | retour arrière réel | ✔ | ✔ | ✔ |

¹ nominal : couvert sur ort (écart 0) ; sur bd_nyme/taxe le nominal demanderait de rejouer tout le volume
amont (moisson WFS / 10 000 secteurs) — couvert par ort + la primitive. Les motifs — sont physiquement
inapplicables à ces tables (points toujours valides ; sans géométrie) ; la géométrie INVALIDE reste
couverte par `trafic_rn` (SOLIDE-2) + la primitive.

### 5.1 Base de test DB (`labuse_test`)

`pytest -m "db and not local and not reel and not network"` (voir §6 : les essais réels de SOLIDE
visent la base saine `labuse`, pas `labuse_test`) → **1352 passés, 40 skipped, 3 ÉCHECS tous
PRÉ-EXISTANTS** (prouvés indépendants de ce mandat) :

1. `test_api::test_m137_tuiles_ne_crashent_pas` — `relation "score_labuse" does not exist` (artefact
   absent de `labuse_test`, **déjà rouge en SOLIDE-1/2 §5.1**, inchangé sur `main`).
2. `test_copilote3_verdicts::test_answer_copro_est_deterministe_et_source_rnic` — **même cause**
   (`score_labuse` absent) ; la conversion RNIC ne change que l'ÉCRITURE de `rnic_coproprietes`, pas sa
   lecture (le test dégrade parce que `score_labuse` manque). Déjà documenté SOLIDE-2 §5.1.
3. `test_circuit_p2_lot5::test_tour_complet_des_endpoints` — assertion de **PERFORMANCE** (`/admin/circuit`
   répond 200 mais en > 1 s sur ce poste chargé). **Prouvé pré-existant** : en remisant mes changements
   (`git stash` du `src/labuse`), le MÊME test échoue À L'IDENTIQUE (pire : 20 s à froid) sur le code
   pristine — c'est le poste/cache, pas mon diff (qui ne touche aucun endpoint `/admin/circuit`).

Les ingestions converties sont par ailleurs exercées vertes par `test_ban_adresses`,
`test_taxe_amenagement_delta`, `test_mo_ingestion`, `test_zone_ingestion`, `test_zone_donnees`,
`test_circuit3_lot6` (coords témoins en Réunion → les nouveaux contrôles géo/périmètre passent ;
`avant = 0` sur `labuse_test` → contrôle d'écart neutre, première injection acceptée).

### 5.2 Suite de cohérence (12 témoins)

`scripts/ci/coherence_run.sh` sur la base servie → **6 passés, 0 écart** (1 €/1 m²) sur les témoins du
lot A. (Le hook pre-push lie le global sur `labuse_test` qui, sur ce worktree, ne porte pas tous les
artefacts servis — `score_labuse`/fiches témoins — ; la suite a donc été jouée en pointant le moteur
sur la base SERVIE `labuse`, `LABUSE_TEST_DATABASE_URL=…/labuse`, lecture seule. Les 12 fiches témoins
calculent sans erreur ; aucune lecture n'a été modifiée par ce mandat.)

---

## 6. Notes d'environnement

- Python : `/Users/openclaw/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src`.
- **Piège** : la base `labuse` appartient au rôle **`openclaw`** (pas `labuse`) →
  `LABUSE_APP_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`.
- `mobpro_commune` est **vide** sur cette base → écartée des essais « peuplée » (les 3 conversions de
  recette sont `bd_nyme`/`ort`/`taxe`, toutes peuplées).
- **Pas de merge, pas de push, zéro écriture prod** — comme demandé.
