# CHASSE-FIX-3 — corriger CHASSE-3, dernier verrou avant le déploiement

> **Les 8 écarts de CHASSE-3 sont traités : 7 corrigés (dont les 2 bloquants), 1 classé avec
> preuve (C3-02, garantie G5, remède opérationnel). Les deux tables dérivées périmées ont été
> reconstruites avec le code du jour (pc_caducs 2 161→4 822, veille succession 7 129→6 256), et un
> garde-fou neuf — chaque table dérivée porte la version de sa règle — fera désormais signaler
> « à reconstruire » par le contrôle de fraîcheur dès qu'une règle bouge sans rebuild.
> `/readyz` répond ready=true sur l'état servi ; les 24 verrous du circuit sont verts.**

Branche `fix/chasse-3` (base origin/main, audit/chasse-3 mergé), worktree
`~/Desktop/labuse-chassefix3`, ports 8835/6035. Règle tenue : chaque écart corrigé a sa
reproduction rejouée → 0 **et** un test qui le verrouille ; `pg_stat_activity` vérifié avant chaque
requête lourde ; **aucun run résiduel rejoué, aucune bascule** (le rebuild des dérivés ne touche ni
la cascade ni le scoring q/a servi) ; pas de merge.

---

## Lot 1 — les 2 bloquants

### C3-01 (DISCORDANT, bloquant) — /readyz mentait, le healthcheck de déploiement aurait échoué

**Le défaut.** `state.py:111` (`served_run_status`) testait
`dryrun_parcel_evaluations WHERE run_label='q_v16'` au label BRUT → 0 ligne, alors que l'app sert
juste : `q_v16` est un run EMPRUNTEUR dont la cascade vit sous l'étage 0 réutilisé
`q_v13_sources1` (params `etage0_run`). Les lecteurs clients résolvent déjà via `resoudre_cascade_run`
(CHASSE-FIX-2 D05, `_cascade_run`) ; la sonde, non → `/readyz` disait « run q_v16 non matérialisé »,
action trompeuse « lancer labuse score-v2 », et `deploy_vps.sh` aurait marqué le déploiement ✗.

**Le correctif.** `served_run_status` résout désormais la cascade pour le contrôle dryrun — le
MÊME run que lisent les lecteurs. Le contrôle des scores (`p_score_v2`) reste au label servi
(présent). Lecture seule, aucune écriture.

**Preuve (base servie).**
```
served_run_status: {'ok': True, 'run': 'q_v16', 'missing': []}
/readyz (commune pilote Saint-Paul) : ready=True · served_run.ok=True
```
Base : `dryrun_parcel_evaluations` porte 431 663 lignes SOUS `q_v13_sources1`, 0 sous `q_v16` ;
`p_score_v2_runs.params` de q_v16 = `{"etage0_run": "q_v13_sources1", …}`.

**Test.** `tests/test_chasse_fix3.py::test_c3_01_readyz_resout_la_cascade` — sème un run emprunteur
(cascade seulement sous l'étage 0), casse si la sonde relit le label brut.

### C3-06 + C3-07 (FAUX) — deux tables dérivées jamais rebâties après un changement de règle

**(a) Reconstruction avec le code du jour.** `pg_stat_activity` : 0 transaction idle ou longue avant
chaque rebuild. Dump AVANT des deux tables sous `rebuild/avant_pc_caducs_succession.sql.gz`
(point de restauration), dump APRÈS sous `rebuild/apres_…`. Rebuilds journalisés (`circuit_journal`, lot CHASSE-FIX-3). Bornés à ces
tables (pc_caducs par `rebuild_swap` shadow ; la veille succession par `score-v-compute`, stage 3
ADDITIF qui ne touche NI cascade NI run q/a).

| table | avant | après | règle appliquée | durée |
|---|---|---|---|---|
| `pc_caducs` | 2 161 | **4 822** | ORACLE-FIX-1 : octroyé = états {2,5,6}, jamais annulé (4) | 1,6 s |
| `parcel_veille_succession` | 7 129 | **6 256** | OUTILS-S2 Lot A : formes patrimoniales + âge 70 + SCI dormante | 29,1 s |

Témoins :
- **CO0833** (`97416000CO0833`, seul PC état 4 ANNULÉ) → désormais **ABSENT** de pc_caducs : la fiche
  ne se contredit plus (liste permis « annulé » vs bloc caducité « jamais commencé »).
- **CO0258** (`97416000CO0258`, PC état 2 de 2013 jamais commencé) → désormais **PRÉSENT** (caduc
  depuis 2016).
- Saint-Pierre : **434** dormants servis (cohérent avec les ~418 vrais dormants de l'audit ; les 301
  fausses cibles d'état 4 ont disparu).
- Veille succession : **0 forme SA/SAS/SEM/SCA/GIE** restante ; les témoins SAS/SA de l'audit
  (`97422000AK0603`, `97422000AH0351`) sont **ABSENTS**.
- Note honnête : la SCI 320878358 (dirigeant 84 ans, 23 parcelles) reste HORS veille — non par la
  doctrine des formes (c'est une SCI) mais parce que sa fiche SIRENE la classe **ETI** : la règle v1.1
  exclut les catégories GE/ETI du signal « dirigeant âgé » (un administrateur d'un grand groupe ne
  signale pas une vente foncière). Le rebuild applique donc **toutes** les règles du jour, pas seulement
  l'exclusion SA/SAS — comportement voulu, pas un manque.

**(b) Empêcher que ça revienne — version de règle par table dérivée.** Chaque table dérivée porte
désormais une `RULE_VERSION` dans le code (`pc_caducs.RULE_VERSION` ;
`score_v_constants.VEILLE_SUCCESSION_RULE_VERSION`, DÉRIVÉE des formes+âge donc auto-bougeante). Au
rebuild, elle est gravée dans `fraicheur_etat` (`derive:<table>:rule_version`) par
`fraicheur_caches.marquer_regle_derivee`. Le contrôle de fraîcheur
(`fraicheur_caches._etat_derives_regle`, ajouté à `etat()` — servi par `/sante/fraicheur`, page
Données, joué par `labuse rebuild --dry-run`, la fumée du déploiement) confronte version gravée vs
version du code : **mismatch ⇒ périmé « à reconstruire »**, exactement le mécanisme « clé attendue /
clé réelle » des autres caches.

C'était le bug fondateur : la table du 08/08 (octroyé {4,6}) servie après ORACLE-FIX-1 ({2,5,6}),
celle du 09/08 servie après la doctrine des formes du 25/09 — en silence. Désormais le circuit crie.

**Preuve du garde-fou.** AVANT rebuild : `_etat_derives_regle` = périmé, détail « règle gravée ∅
(jamais stampée) ≠ code … → labuse pc-caducs / labuse score-v-compute ». APRÈS rebuild : **frais**
(« chaque table porte la version de règle du code »).

**Tests.** `test_c3_06_07_derives_signalent_a_reconstruire` (périmé avant stamp, frais après, re-périmé
si la version gravée diffère) ; `test_c3_06_07_versions_de_regle_non_vides`. La table `fraicheur_etat`
— désormais matérialisée en permanence par le stamp — a été déclarée au registre
(`TABLES_EXPLOITATION`) pour garder le verrou V1c vert (même motif que `coherence_runs`).

---

## Lot 2 — le reste d'ECARTS.csv

### C3-03 (TROMPEUR, grave) — « VEFA » collait sur deux chiffres différents

`strings.ts:142` étiquetait « Prix du neuf VEFA (€/m²) » la ligne `prix_sortie_neuf` du bloc Marché,
qui est le **neuf OBSERVÉ** (ventes ≤ 3 ans post-achèvement, `resolve_prix_neuf_marche`) — pas la VEFA
déclarée à l'acte. À Saint-Denis : bloc Marché 4 275 « VEFA » vs comparateur/contexte/baromètre/couche
carte/Dossier PDF 4 878 « VEFA déclaré à l'acte ». Deux « VEFA » dans la même app.

**Correctif :** libellé → « **Prix du neuf observé (€/m²)** » (aligné sur « Neuf observé » déjà employé
par le ContextePanel). Le mot « VEFA » reste réservé à la valeur à l'acte, partout. Seul libellé front
touché (le backend distinguait déjà `neuf_eur_m2` vs `prix_neuf_observe`). tsc 0, vitest vert.

### C3-04 (SALE) + C3-05 (DISCORDANT) — ignorances stockées SDP=0

Au run servi, 10 778 causes d'IGNORANCE (`zone_non_resolue` 10 463, `regle_plu_non_validee` 313,
`hauteur_indispo` 2) sont stockées SDP=0 au lieu de ∅. Aucun lecteur ne les sert « 0 » (le scoring
neutralise par la cause, la fiche recalcule null + « Analyse incomplète ») **sauf** 2 parcelles
`hauteur_indispo` (`97415000AB0858/AB0860`) qui fuient en bande « 0 ».

**Correctif.** `_cause_nc` (score_labuse) délègue la partition à `faisabilite.engine.cause_certaine`
(source unique) : **toute cause présente mais NON certaine est une ignorance → NC « Analyse
incomplète », jamais bande « 0 », même SDP=0 stocké**. `hauteur_indispo` porte son motif propre
(`NC_HAUTEUR`, celui de la fiche). Le filet C26 (SDP NULL → `NC_SDP`) est conservé et joué AVANT, pour
garder le motif juste quand c'est la SDP elle-même qui manque. Couvre `indetermine`, `bati_non_ingere`
et toute cause d'ignorance future sans la réénumérer.

**Reproduction.** Le stock (10 778) n'est servi « 0 » par aucun lecteur ; les 2 parcelles passent NC au
Score. Dry-run `score-labuse --no-persist` sur les 2 témoins : pipeline propre, 0 s.

**⚠ Recalcul du Score — à faire par Vic, PAS par moi (mandat).** Le reclassement des 2 parcelles
devient effectif au prochain Score LABUSE. Commande exacte (île, run servi) :
```
labuse score-labuse --run q_v16 --cascade-label q_v13_sources1
```
**Durée mesurée : ~2 min** (dry-run `--no-persist` sur l'île entière, 431 663 parcelles, 115 s ;
compter un peu plus avec l'écriture `--persist`). Déterministe, idempotent, versionné par run_label ;
n'est PAS une bascule. (Mesuré ici en `--no-persist` — n'écrit rien ; le mandat interdit de
matérialiser le Score servi.)

**Tests.** 4 tests (`test_c3_05_*`) : hauteur_indispo + toutes les ignorances → NC ; causes certaines
gardent leur vrai 0 ; `bande_de_score(None)`=NC, `bande_de_score(0)`≠NC ; partition alignée sur engine.

### C3-08 (DISCORDANT) — le « siège » flappait, et n'était pas un siège

`_pm_identite` (app.py) lisait `sirene_etablissements … ORDER BY actif, date_creation LIMIT 1` : EDF
(siren 552081317) a **7 établissements ex æquo** sur (actif, date_creation) = 1986-07-08 → la fiche
flappait entre deux adresses, toutes deux dites « siège ».

**Correctif :**
- **Départage déterministe** par `siret ASC` en dernier (clé primaire). 3 appels de `_pm_identite`
  pour EDF → une seule valeur (« 14 RUE SAINTE ANNE », SIRET minimal des 7 ex æquo).
- **Honnêteté du libellé** : SIRENE géolocalisé ne couvre que La Réunion et ne porte pas le drapeau
  établissement-siège → le front affiche désormais « **Établissement** » (pas « Siège »), le backend le
  documente. (Bloc fiche uniquement — aucun PDF ne lit `_pm_identite`, l'invariant écran=papier 254/254
  n'est pas touché.)
- **Recensement des autres LIMIT 1 du même genre** (choisir UNE ligne parmi plusieurs pour l'affichage,
  sans départage) → tous rendus déterministes :
  - `api/promo.py` (`_resoudre_promoteur`) : dénomination par SIREN → `ORDER BY denomination`.
  - `api/veille_promoteurs.py` ×2 (`promoteur_frise`, `patrimoine_promoteur`) : idem.
  - `proprietaire_facettes.py` (`_source_millesime`) : millésime → `ORDER BY millesime DESC` (le plus
    récent, pas une ligne au hasard).
  - (Classés déterministes sans changement : `zone.py` ×3 `ORDER BY ingested_at DESC`,
    `courrier_adressage.py` `ORDER BY fetched_at DESC`, `served_cascade.py`/`context.py` clés primaires.)

**Test.** `test_c3_08_pm_identite_deterministe` — sème 3 établissements ex æquo, exige 1 seule valeur
stable sur 4 appels (le SIRET minimal).

### C3-02 (TROMPEUR) — CLASSÉ avec preuve

4 sources vitrine (Contraintes EnR, SCAN 50 1950, INPN espaces protégés, EduGéo 1980) s'affichent
« à jour » sans date de dernier contrôle → **garantie G5 « casse »**.

**Pourquoi classé, pas corrigé :**
1. **G5 est une GARANTIE, pas un des 24 verrous de déploiement.** Le gate du mandat (« circuit verrous
   24/24 ») porte sur les verrous V — tous verts. Les garanties G sont consultatives (G8, gel local des
   horloges, est cassée depuis DASHBOARD-AUDIT-1).
2. **G5 fait correctement son travail** : les 4 sources sont `mode_remplissage='one_shot'` et ont été
   ingérées **sans `last_sync_at`** ni ligne `source_veille` (vérifié en base) ; elles affichent « à
   jour » sans date — exactement ce que G5 doit dénoncer. Ce n'est pas un bug de code mais un état de
   DONNÉE/exploitation.
3. **Le remède est opérationnel, réservé à l'exploitant** (il écrit dans `data_sources`/`source_veille`
   de la base servie, hors du périmètre « tables dérivées » de ce mandat) : un passage de sonde
   (`labuse sonde-sources`) ou l'horodatage de la date d'ingestion de ces 4 one-shot. Fabriquer une date
   `now()` serait malhonnête (contrôle non fait aujourd'hui).
4. **Aucun chiffre client n'est faux** : les 4 sources SONT servies correctement ; seule la date de
   dernier contrôle est blanche.

Même famille que G8 — un manque opérationnel, nommé, pas un mensonge sur une valeur.

### p95 sous charge — noté pour l'audit vitesse (non corrigé, hors mandat)

Rappel des mesures CHARGE de CHASSE-3 (10 clients × 10 min, Mac local, uvicorn mono-worker) :
**fiche p95 13,7 s** (p50 9,1 s), **filtre p95 23,9 s** (max 39 s), PDF 22,8 s ; solo au calme fiche
1,3–2 s. 0 corps différent sous charge, 0 5xx, 0 timeout. À re-mesurer sur le VPS avant d'en faire un
chantier — hors périmètre CHASSE-FIX-3.

---

## État des portes (fin de mandat)

- **/readyz** (gate de `deploy_vps.sh`) : `ready=true` sur l'état servi (commune pilote Saint-Paul). ✓
- **circuit verrous** : **24/24 verrous V verts** (`labuse circuit verrous`, base servie — dont V6b
  « golden 7 témoins rejoués » et V1c rendu vert par la déclaration de `fraicheur_etat` au registre).
  « 0 fuite » : G7 vert. Restent cassées, consultatives et pré-existantes : **G5** (C3-02, classé) et
  **G8** (gel local des horloges, DASHBOARD-AUDIT-1) — mêmes deux garanties qu'à l'audit (30/32).
  ⚠ à la 1ʳᵉ exécution sous charge (pytest complet en parallèle), V6b a faussement signalé 4 « notions
  disparues » sur 2 témoins golden : artefact de contention (le TestClient de la fiche affamé) — la
  donnée est intacte en base (EO0796=U5b/U, AX0990=U4a/U = attendus golden) et V6b repasse vert à froid.
- **tsc** : 0. **vitest** : 243 verts. ✓
- **pytest** : régression ciblée sur toutes les surfaces touchées (chasse, scoring, score_labuse, c26,
  state, fraicheur, registre, garanties, score_v) = **139 verts** (1 test de fraîcheur mis à jour :
  9ᵉ cache ajouté). ✓
- **contrôle de fraîcheur** : les tables dérivées portent leur version de règle, état « frais ». ✓

## Rejeu des harnais

- **`make -C scripts/chasse chasse`** (CHASSE-1 + CHASSE-2, lecture directe de la base — pas d'API) :
  rejoué pour la régression (echantillon/invariants/couverture/intruses/face_a_face/filtres/horloge +
  volets CHASSE-2). Résultat sous `/tmp/make_chasse.txt` au moment du commit ; aucun des écarts
  corrigés de CHASSE-FIX-1/2 ne réapparaît, et les rebuilds (pc_caducs/veille/Score V additif) ne
  déplacent pas les invariants servis (la cascade et le run q/a ne sont pas touchés).
- **CHASSE-3** : chaque volet du mandat a été rejoué DIRECTEMENT à sa reproduction (SQL/Python sur la
  base servie), pas via `make chasse3` — ce dernier exige le build de prod servi par une API vivante
  (`LABUSE_CHASSE3_API`, charge3 = 10 min, mobile3 = Playwright), hors proportion pour revérifier des
  écarts déjà prouvés un à un : C3-06 (pc_caducs 2 161→4 822, CO0833/CO0258), C3-07 (veille 7 129→6 256,
  SA/SAS=0), C3-04/05 (`_cause_nc` + dry-run), C3-03 (grep libellés front), C3-08 (EDF 3 appels → 1
  valeur), C3-01 (`/readyz` ready=true). Le build de prod a été produit (`vite build --base=/socle/`)
  et sert de base aux tests front.

## Fichiers touchés

Code : `src/labuse/state.py` (C3-01) · `src/labuse/scoring/score_labuse.py` (C3-04/05) ·
`src/labuse/ingestion/pc_caducs.py` + `src/labuse/scoring/score_v_constants.py` +
`src/labuse/scoring/score_v.py` + `src/labuse/fraicheur_caches.py` + `src/labuse/registre/tables.py`
(C3-06/07 + versioning) · `src/labuse/api/app.py` + `src/labuse/api/promo.py` +
`src/labuse/api/veille_promoteurs.py` + `src/labuse/proprietaire_facettes.py` (C3-08) ·
`frontend/src/lib/strings.ts` (C3-03) · `frontend/src/components/fiche/Fiche.tsx` (C3-08).
Tests : `tests/test_chasse_fix3.py` (12 tests). Données : rebuilds pc_caducs + veille succession
(dumps avant/après + journal sous `CHASSE-FIX-3/rebuild/`).
