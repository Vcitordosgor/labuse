# CHASSE-ORFEVRE-1 — ANGLE H : le code lui-même

Date : 2026-10-18 · Worktree : `~/Desktop/labuse-orfevre` (= main) · **Lecture seule** (aucune
écriture base, aucun fichier applicatif touché ; outils tiers dans un venv jetable `/tmp/audit_venv`).
Commandes rejouables : `../scripts/angle_h_code.sh`. Base inspectée via `LABUSE_DATABASE_URL` du `.env`
(⚠ base de **dev** : les stats `pg_stat_user_tables` incluent les runs d'audit/batch locaux — un
`seq_scan` élevé y est un **indice**, pas une preuve de ce que verrait la prod).

Volumes : backend 613 fichiers `.py` sous `src/labuse/` ; front 224 fichiers `.ts/.tsx`.

---

## H1 — Fonctions mortes

**Méthode.** `vulture --min-confidence 60` (1 385 candidats bruts, dont 1 029 fonctions/classes/
méthodes) puis croisement anti-faux-positifs (`/tmp/dead_check2.py`, archivé en annexe A) :
tokenisation du repo ENTIER (py/ts/tsx/js/yaml/sql/sh/html/toml/json/md — 3 979 fichiers), de sorte
qu'une référence **même en chaîne de caractères** compte comme vivante ; exclusion de TOUTE fonction
décorée (routes FastAPI, `@extracteur` de `robinet_fiche.py`, `@app.command`, validators… = 777
candidats écartés, tous vérifiés enregistrés dynamiquement par leur décorateur) ; exclusion des noms
dont la **variante à tirets** existe quelque part (dispatch des jobs par nom : `"pg-maintenance"` →
`getattr(jobs_impl, nom.replace("-","_"))`, `src/labuse/jobs.py:297-301`).

### H1.a Mort sûr — backend (41) · gravité : cosmétique (dette), gênant pour les gros modules

« Mort sûr » = le nom n'apparaît **nulle part ailleurs** dans le repo (ni code, ni test, ni doc, ni
chaîne, ni variante à tirets), fonction non décorée. 45 sorties brutes du croisement, moins **4
faux positifs d'interface** retirés à la main (méthodes appelées par un framework, pas par le repo) :
`promo/collecte.py:62/70/77` (`handle_starttag/endtag/data` = callbacks `HTMLParser` stdlib) et
`ingestion/bdnb.py:101` (`readinto` = protocole file-like). Restent **41** :

```
src/labuse/ai_models.py:115                      function  bloc_ia
src/labuse/api/ia.py:64                          function  _note_erreur
src/labuse/api/ia.py:68                          function  _note_succes
src/labuse/api/pdf_premium.py:121                function  _signaux
src/labuse/api/pre_dossier.py:603                function  _bati_geojson
src/labuse/connectors/recherche_entreprises.py:124  method  fetch_by_sirens
src/labuse/copilote_v2/answering.py:1304         function  _brief_effectif_recherche
src/labuse/copilote_v2/answering.py:1322         function  _recap_recherche
src/labuse/exports/miroir.py:882                 function  _entete_tuiles
src/labuse/faisabilite/filtre_bati.py:52         function  build_parcel_filtre_bati   (⚠ voir note 1)
src/labuse/faisabilite/vue_mer.py:130            function  temoins_commune
src/labuse/implantation/capacite.py:53           function  _sdp_logement
src/labuse/implantation/rendu.py:55              function  rendre_plan_png
src/labuse/ingestion/bodacc.py:143               function  demojibake_existant
src/labuse/ingestion/cosia_couverture.py:109     function  build_couverture
src/labuse/ingestion/dvf_detail.py:66            function  build_dvf_detail
src/labuse/ingestion/fraicheur.py:250            function  retards_live
src/labuse/ingestion/fraicheur.py:421            function  check_couches_cascade
src/labuse/ingestion/ocsge.py:239                function  construire_couche
src/labuse/ingestion/vegetation.py:151           function  purge_irc_cache
src/labuse/jobs_impl.py:29                       function  _libpq_url
src/labuse/ml/juge_flair.py:140                  function  choisir_seuil_sur_train
src/labuse/ml/juge_vlm.py:46                     function  generer_crop_vlm
src/labuse/notif_registry.py:126                 function  defaut_prefs
src/labuse/pige/portails.py:25                   function  est_portail
src/labuse/pige/signaux.py:181                   function  annonce_vs_referentiel
src/labuse/pige/signaux.py:352                   function  badge_bien
src/labuse/quota.py:89                           function  usage_du_jour
src/labuse/registre/lectures.py:649              function  lectures_de
src/labuse/reglages.py:104                       function  get_str
src/labuse/reglages.py:116                       function  set_str
src/labuse/scoring/dryrun.py:22                  function  _compute_matrice_morte_m129
src/labuse/scoring/lignee_tete.py:63             function  build_parcel_acquerabilite
src/labuse/scoring/score_labuse_combine.py:228   function  as_dicts
src/labuse/scoring/tiers_client.py:76            function  palier_da
src/labuse/veille_grille.py:48                   function  kinds_tete
src/labuse/veille_grille.py:75                   function  mode_mail
src/labuse/verdict_servi.py:146                  function  _label_bati
src/labuse/verite_terrain_plu_regles.py:69       function  choisir_100
src/labuse/verite_terrain_plu_toutes.py:196      function  _pdf_texte_complet
src/labuse/verite_terrain_sources.py:23          function  _haversine
```

**Note 1 (piège de merge)** : `build_parcel_filtre_bati` est mort sur **main**, mais la branche
`fix/chasse-invariants-2` (poussée, non mergée) modifie `filtre_bati.py` (garde année DPE). Le
supprimer avant ce merge créerait un conflit. Même prudence pour tout ce qui touche
`verite_terrain_*` (modules d'audit récents, chantiers vivants).

**Correction proposée (non appliquée)** : suppression par lots avec `git log -S` au préalable
(certaines sont des survivances de refontes : `_compute_matrice_morte_m129` l'annonce dans son nom).

### H1.b Probablement mort — backend (98) · cosmétique

Référencées **uniquement** dans `tests/` ou des `.md` de docs (le test maintient du code que rien ne
sert). Liste complète en **annexe B**. Deux nuances importantes :
- **17 classes ORM de `models.py`** (SpatialLayer, DvfMutation, SitadelPermit, ScoreSnapshot*,
  ParcelSignal, WatchSnapshot…) : la CLASSE n'est référencée nulle part (tout le code requête ces
  tables en SQL brut), mais elle **définit la table** pour `create_all` — « morte » comme classe,
  pas supprimable sans déplacer le DDL. À requalifier plutôt qu'à supprimer.
- Fonctions testées-mais-jamais-appelées typiques : `totp.code_totp:40` (le code 2FA réel passe par
  un autre chemin), `rgpd_dirigeants.purger_nationalite_et_raw:37`, `scoring/lignee_tete.
  build_parcel_entree_tete:25`, `api/pdf_premium.render_fiche_pdf:344`, `brevo.verifier_templates:164`.
  Chacune mérite un « soit on la câble, soit on supprime fonction+test ».

### H1.c Vulture ≥ 80 % — variables/imports morts (13) · cosmétique

```
src/labuse/api/dashboard.py:2475  unused variable 'plafond_eur'
src/labuse/api/events.py:303      unused variable 'is_market'
src/labuse/api/servitudes.py:198  unused variable 'db_unused'
src/labuse/bilan/excel.py:22-23   unused imports 'Alignment', 'get_column_letter'
src/labuse/circuit_verrous.py:96  unused variable 'parameters'
src/labuse/faisabilite/hauteur_lidar_dalles.py:33,230  unused imports 'ET', 'array_bounds'
src/labuse/ingestion/division_or.py:628  unused variable 'decoupe'
src/labuse/ingestion/ortho_tiles.py:192  unused variable 'keep_tables'
src/labuse/marque.py:34           unused variable 'mime_declare'
src/labuse/millesime_source.py:84 unused variable 'dernier_vu'
src/labuse/verite_terrain_dpe_permis.py:547  unused variable 'cle_mots'
```

### H1.d Front — exports jamais importés (122) · cosmétique à gênant

`npx ts-prune -p tsconfig.json` (hors « used in module ») : **122 exports**, liste complète en
**annexe C**. Les gros postes :
- `src/lib/api.ts` : **69 bindings d'API morts** (getWatchZones, getAlertes, radar*, admin*,
  financierQuestionnaire*, getScoringBacktest…). Beaucoup correspondent à des **endpoints backend
  décorés que vulture voyait vivants** : le couple front-mort + endpoint jamais appelé (ex.
  `watch_zones_*` app.py:8610-8656, `alertes_*` app.py:8660-8690, `scoring_backtest` app.py:6634,
  `financier_questionnaire_*` app.py:8315-8426) est en réalité une **feature morte de bout en bout** —
  vérifier au cas par cas avant suppression (certaines sont appelées hors front : curl ops, QA).
- Composants exportés jamais importés : `ConstructibiliteSection` (constructibilite.tsx:1063),
  `LeBienSection` (leBien.tsx:240), `O7Carnet/O9Rarete/O10Bascules` (blocB.tsx), `M17/M19/
  MarcheCommune` (moteurs.tsx), `CopiloteEmbarque`, `DepotAgence`, 9 `default` d'ui/*.
- Constantes : `PERIM_RESIDUEL/PERIM_POTENTIEL` (perimetres.ts), `V_BAND_META`, `EQUIP_META`,
  `BANDE_QUALITE` (status.ts).

---

## H2 — Index manquants

Croisement requêtes du code ↔ `pg_indexes` ↔ `pg_stat_user_tables`. Le schéma est globalement très
bien indexé (sitadel `idu_codes` a son GIN, dvf_mutations_parcelle a `id_parcelle`, event_log a
`(dedup, compte_id)`…). Une seule table >10k lignes sans AUCUN index : `parcel_couche_intersection_build`
(table de build jetable — normal). Trois manques réels :

### H2.1 `sirene_etablissements(siren)` — **gênant, prouvé**
- Index existants : pkey(siret), naf, insee, gist(geom). **Rien sur `siren`** (varchar).
- Requêtes qui en souffrent :
  - `src/labuse/api/app.py:5944` — `FROM sirene_etablissements WHERE siren = :s` (fiche
    propriétaire, **par requête utilisateur**) ;
  - `src/labuse/api/app.py:1819` — `JOIN sirene_etablissements sea ON sea.siren = pma.siren` ;
  - `src/labuse/proprietaire_facettes.py:75` — `JOIN sirene_etablissements se ON se.siren = pm.siren`.
- Mesure (dev) : 158 515 lignes / 97 MB ; **46 205 seq_scan, 2,44 G tuples lus en séquentiel**
  (vs 410 k idx_scan). Chaque fiche propriétaire balaie la table.
- Correction proposée : `CREATE INDEX ix_sirene_etab_siren ON sirene_etablissements (siren);`
  (+ le recréer dans l'ingestion `sirene_etablissements.py` qui fait `DELETE` + reload).

### H2.2 `dvf_mutations(date_mutation)` — **gênant, prouvé**
- Index existants : pkey, commune, gist(geom), gist(st_transform(geom,2975)). Rien sur la date.
- Requête : l'**ancre DVF** `ANCRE_DVF_SQL` (`src/labuse/dvf_fenetre.py:15-16`) =
  `SELECT max(date_mutation) FROM dvf_mutations WHERE date_mutation = date_trunc('day', date_mutation)`,
  injectée dans CHAQUE fenêtre de ventes (fiche « Mon secteur » `marche_service.py:258`, Flash
  `flash/data.py:490,516`, Dossier, PDF…).
- Mesure (dev) : table minuscule (29 566 lignes / 11 MB) mais **885 231 seq_scan / 11,2 G tuples
  lus** — de loin le plus gros compteur de seq_scan de la base. Coût unitaire faible, fréquence
  énorme (plusieurs ancres par fiche).
- Correction proposée : `CREATE INDEX ix_dvf_date_mutation ON dvf_mutations (date_mutation DESC);`
  — le `max()` devient un parcours descendant qui saute la seule ligne parasite non-minuit.
  (Un index PARTIEL `WHERE date_mutation = date_trunc('day', date_mutation)` serait idéal mais la
  colonne est `timestamptz` → `date_trunc` non IMMUTABLE, prédicat refusé.) Alternative structurelle :
  mémoïser l'ancre par requête/process (elle ne change qu'à l'ingestion mensuelle).

### H2.3 `parcelle_personne_morale(siren)` — à surveiller (indice)
- Seul index : pkey(idu). 82 701 lignes.
- Requêtes par siren : `signaux_vie.py:78` (sous-requête `SELECT siren FROM parcelle_personne_morale`),
  `ingestion/deposants_actifs.py:46` (GROUP BY), `proprietaire_facettes.py:75/117` (jointures/agrégats),
  scan patrimoine. La plupart sont des agrégats pleine-table (seq légitime) ; un btree(siren) ne
  devient utile que si le « patrimoine d'un SIREN » se requête unitairement à chaud — c'est le cas
  dans quelques chemins fiche. Taille faible : coût de l'index négligeable, bénéfice modéré.

### H2.4 Non-problèmes à consigner (pour éviter de futurs faux débats)
- `dryrun_parcel_evaluations` : 51 G tuples lus en seq, mais les requêtes portent `run_label = :r`
  qui matche la quasi-totalité de la table (1,3 M lignes pour ~2 runs) → le planner a RAISON de
  choisir seq. Idem `score_labuse` (16,4 G). C'est le profil des runs batch d'audit sur la base de dev.
- `parcel_ocsge` (seq 16 k) : `scoring/cascade_v2.py:158` joint la table ENTIÈRE au scoring — seq légitime.
- Cosmétique : les 3 index de `parcel_couche_intersection` s'appellent encore
  `parcel_couche_intersection_build_*` (hérités du rename build→servie) — nom menteur, rien de cassé.

---

## H3 — Requêtes N+1

Scan AST (`/tmp/scan_n1.py`, annexe A) : **357 boucles** contenant un `execute/scalar/query` dans
`src/labuse/`. Après tri (itération sur un résultat ≠ N+1 ; listes DDL fixes ≠ N+1), les vrais
« une requête par élément » avec leur volumétrie RÉELLE (comptée en base le 18/10) :

### Côté API / jobs servis — aucun bloquant AUJOURD'HUI, gênants en croissance
| Site | Boucle | Requêtes/élément | Volumétrie actuelle | Verdict |
|---|---|---|---|---|
| `api/events.py:435-493` (`detecter_suivis`, job veille) | `watched_parcels` | **4 à 5** (mutation, permis, bodacc, PM, update snap) | **14** parcelles suivies → ~70 req/passage | Gênant : linéaire en clients. À 5 000 suivis = 25 000 req/job. Réécriture ensembliste possible (4 jointures). |
| `api/events.py:602` (relances dues) | `dus` | 3 | dizaines | Défendable (petit, transactionnel) |
| `api/events.py:1367` (envoi digest) | `recipients` | 2 | 47 comptes max | Défendable (mail par destinataire de toute façon) |
| `api/modules.py:1709-1713` (outil « contraintes en lot ») | `tokens[:60]` | 1 lookup parcelle + `contraintes_parcelle()` | **60 max par requête UTILISATEUR** (borné) | À surveiller : le lookup `WHERE idu=:t OR (section||numero)=:t…` par token est indexé idu mais l'OR concat ne l'est pas → 60 scans possibles sur `parcels` (433 k). Préférer un `= ANY` préparé. |
| `api/projets.py:662,702,798` | projets actifs / items | 1-2 | **8** projets actifs | Défendable aujourd'hui |
| `api/app.py:8453` (comparateur D2) | `ids` choisis par l'utilisateur | 1 + fiche complète | borné par la sélection | Défendable (la fiche domine le coût) |
| `api/dashboard.py:3082` (« Envoyer les agents ») | agents | 2 + appel LLM | plafonné en € | Par conception (coût lu après chaque agent) |

### Côté batch (le coût est en heures de run, pas en latence)
| Site | Boucle | Volumétrie | Verdict |
|---|---|---|---|
| `faisabilite/residuel.py:314-344` (`compute_residuel_batch`) | `parcel_ids` : 1 `compute_residuel` + **1 UPSERT par parcelle** | **431 663** parcelles en run île | Gênant assumé : c'est le run de ~2 h 20 connu. L'UPSERT unitaire (433 k aller-retours) serait regroupable par `executemany`/chunk — gain estimé substantiel sans toucher la LOGIQUE. |
| `faisabilite/constructibilite.py:92-108` | 1 `parcel_faisabilite` + 1 DELETE/INSERT par parcelle | île | Idem (cache de déclassement) |
| `ingestion/signals.py:95-105` | 1 UPSERT `watch_snapshots` par pid | tous les pids suivis | Petit aujourd'hui |
| `ingestion/score_v_fetch.py:78,138` | 2 à 4 req/SIREN après appel réseau | plafonné `limit` | Défendable (le réseau domine) |
| `ingestion/permits_sdes.py:191-234` | 1 INSERT par ligne CSV | ~60 k permis | Gênant : `executemany`/COPY ferait ×10 (le voisin `ban_adresses.py:121` montre la bonne pratique COPY). |
| `scoring/dryrun.py:237`, `pige/digests.py:389` | 2 / 1 par élément | centaines | Défendable |

**Constat global** : aucune N+1 ne casse l'app aujourd'hui (volumes clients minuscules : 14 suivis,
8 projets, 47 comptes), mais `events.py:435` et `modules.py:1709` sont les deux à réécrire AVANT que
la base clients grossisse ; côté batch, l'UPSERT unitaire de `residuel.py` est le gain de temps de
run le plus évident.

---

## H4 — Exceptions avalées

Scan AST (`/tmp/scan_except.py`, annexe A) : handler dont le corps se réduit à `pass` / `continue` /
`return <constante>` SANS `raise` ni appel de log/print → **418 sites** dans `src/labuse/`
(liste exhaustive fichier:ligne + type attrapé + geste : **annexe D**). À mettre en regard des ~612
`except` annotés `noqa: BLE001` : la maison a une doctrine « best-effort qui SE DIT » (beaucoup de
handlers loggent et sont donc hors de ce décompte) — les 418 restants sont ceux qui se taisent.

### Répartition et lecture
| Zone | Sites | Lecture dominante |
|---|---|---|
| `api/` (app 29, dashboard 24, pige/api 16, …) | ~150 | Enrichissement de payload best-effort : une donnée annexe qui casse ⇒ champ absent, pas de 500. Défendable dans l'esprit, mais UN champ qui disparaît en silence est invisible (pas de compteur). |
| `ingestion/`, `connectors/` | ~90 | Réseau/parse best-effort, souvent commenté (« un endpoint vide n'empêche pas les autres »). Défendable. |
| audits `verite_*`, `sonde_circuit`, `fraicheur_caches` | ~50 | Lecture seule, strates indépendantes. Défendable. |
| `exports/`, `registre/` | ~25 | ⚠ documents clients (voir dangereux ci-dessous). |
| `scoring/`, `faisabilite/`, `cascade/` | ~25 | ⚠ chaîne de calcul (voir dangereux). |
| divers (cli, circuit_*, comptes…) | reste | Mixte. |

### Les dangereux (erreur de DONNÉES masquée) — à corriger
1. **`faisabilite/zonage.py:478-481`** (`_exceptions_effet`) — `except (FileNotFoundError,
   ValueError): return {}` sur `config/plu_exceptions_effet.json`. Un JSON **corrompu** (ValueError)
   fait disparaître EN SILENCE les 81 exceptions PLU `modifie_calcul=true` → capacités recalculées
   sans elles, zéro signal. FileNotFoundError est défendable (base de test nue), ValueError ne l'est
   pas. **Gênant**. Correction : séparer les deux, logger+lever sur JSON invalide.
2. **`faisabilite/zonage.py:821-824`** (`_hypotheses_ile`) — `except Exception: return {}` sur le
   YAML d'hypothèses : un YAML cassé ⇒ repli silencieux sur les défauts dataclass (chiffres qui
   bougent sans trace). Même famille, commentaire assume le repli « fichier absent » mais attrape
   TOUT. **Gênant**.
3. **`cascade/layers/etage0_ext.py:26-31`** (`_seuils_cfg`) — idem : seuils géométrie YAML → `{}`
   silencieux, repli « historique ». Le repli est documenté diff-zéro, mais une config corrompue en
   prod repasserait sur les seuils figés sans bruit. **À surveiller**.
4. **`exports/robinet_fiche.py:38-41`** (`collecte`) — `except Exception: val = None` autour de
   CHAQUE extracteur : un extracteur qui plante ⇒ la donnée est « absente » dans le DOCUMENT CLIENT
   avec la phrase d'absence déclarée — un bug de code devient indistinguable d'une vraie absence.
   Défendable (jamais un 500 sur un PDF) mais il manque un COMPTEUR/log de l'échec. **Gênant**.
   Même motif : `exports/builder.py:32,330,373,410,430` (Return None/dict vide).
5. **`registre/moteurs/commune.py:179,204`, `registre/moteurs/plateforme.py:23,40`** — moteurs de
   chiffres du registre : `except Exception: return None/pass` ⇒ un chiffre déclaré devient muet
   sans trace (famille du défaut que le circuit des verrous est censé attraper — vérifier que V5x
   les couvre). **À surveiller**.
6. **`models.py:2245-2251`** (seed sentinelle au boot) — `except Exception: pass` documenté « un
   souci de seed ne doit JAMAIS bloquer le boot ». Défendable, mais un seed qui échoue TOUJOURS ne
   se verrait jamais. **Cosmétique**.

### Frères du bug G3 (attribut posé sur un proxy SQLAlchemy) — recherche exhaustive : UN SEUL site
- Le site G3 lui-même : **`jobs_impl.py:500-508`** (`pg_maintenance`) — `raw =
  engine().raw_connection()` (= `PoolProxiedConnection`) puis `raw.autocommit = True` : l'attribut
  se pose sur le PROXY (`__setattr__` non délégué), la connexion psycopg reste en transaction
  implicite → `VACUUM cannot run inside a transaction block` → attrapé par l'`except` du for
  (`log.warning("VACUUM %s ignoré")`) → **job vert, VACUUM jamais exécuté** (constat angle F, confirmé).
- Tous les AUTRES `conn.autocommit/read_only = …` du repo (16 sites : `verite_terrain*.py`,
  `verite_sources.py`, `scripts/coherence/*`) posent l'attribut sur une **connexion psycopg ouverte
  en direct** (`psycopg.connect(...)`) → corrects. `scoring/score_v.py:585` passe par
  `.driver_connection` (la bonne porte). **Aucun autre frère.**
- Correction proposée pour G3 (non appliquée) : `raw.driver_connection.autocommit = True`, ou
  `with engine().connect().execution_options(isolation_level="AUTOCOMMIT") as c: c.exec_driver_sql("VACUUM ANALYZE …")`,
  et faire ÉCHOUER le job si `faites == []`.

### Motif « job faussement vert » au-delà de G3
- `pg_maintenance` compte `ctx.compte(tables=faites)` : si TOUT échoue, `faites=[]` et le job
  reste vert — le défaut est le silence du résultat, pas seulement l'autocommit. Les autres jobs
  examinés (`mail_queue_consommer`, `copilote_purge`, backups) comptent leurs échecs ou lèvent.

---

## H5 — Valeurs en dur

### Chemins absolus
- `/tmp` comme répertoire d'état et de logs de runs : `circuit_taches.py:26` et `run_progress.py:34`
  (`LABUSE_RUN_STATE_DIR` défaut `/tmp` — l'état de progression d'un run survit mal à un reboot/purge
  tmp, **à surveiller**) ; logs `cli.py:1054,1127,2690`, `api/dashboard.py:1623,1841,1957` ;
  caches téléchargement `ingestion/personnes_morales.py:100`, `pm_millesimes.py:67`,
  `api/division_review.py:136` (`/tmp/labuse_tiles`). Défendable (éphémère assumé), mais un
  `LABUSE_TMP_DIR` unique serait plus honnête. Aucun `/Users/…` ni `/Volumes/…` dans `src/`.

### URLs / ports
- **`ingestion/vegetation.py:455`** — l'URL renvoyée pour la validation ortho est codée
  `http://127.0.0.1:8000/ortho/validation?...` au lieu de `settings.public_base_url` → lien faux
  partout sauf en local. **Gênant** (petit).
- `jobs_impl.py:217` — `LABUSE_BANC2_API` défaut `http://127.0.0.1:8793` : surchageable, OK.
- `config.py:343` — `public_base_url` défaut local : OK (bascule selon env).

### Labels de runs / dates figées (les « autres q_v18 » demandés)
- **`verite_terrain.py:232`** — `WHERE s.run_label='q_v18'` codé en dur dans l'échantillonneur
  (même famille que le q_v18 de banc2 corrigé dans fix/chasse-invariants-2, NON mergé). Module
  d'audit lecture seule, mais il échantillonnera un run PÉRIMÉ après la bascule q_v19. **À
  surveiller**. Idem ligne 229 : bornes `created_at/updated_at >= '2026-10-01'` figées.
- **`verite_terrain_predictions.py:337`** — texte avec `run_label='q_v19'` et date figée
  « T₀ (18/10/2026) » : document d'audit daté, défendable, mais le label aurait pu venir de `runs`.
- **`bascule_gardes.py:35`** — `TARGET = "q_v8_calibre"` : défaut des gardes de bascule
  (`check_disque:225`, `check_run_absent:451`) pointant un run d'août. Les appels passent
  normalement le target explicite, mais le défaut est un piège. **À surveiller**.
- **`scoring/lignee_tete.py:25`** — `run_servi: str = "q_v8_calibre"` par défaut (le servi réel est
  q_v11_m137) ; la fonction `build_parcel_entree_tete` est par ailleurs « probablement morte » (H1.b).
- `cli.py:2566,2570` — défauts CLI `q_v13_sources1` / `q_v15` : assumés (traçabilité d'une recette),
  cosmétique.
- `api/accueil.py:31` — `TRAIN_ANNEES = (2017, 2023)` : **l'écart signalé par VERITE-TERRAIN-3
  ((2017,2024) ≠ FREEZE) est CORRIGÉ sur main.** Reste une constante locale qui devra suivre le
  prochain re-FREEZE.
- `api/modules.py:271` — repli `_date(2026, 1, 1)` si `now()` SQL revenait NULL (impossible) :
  cosmétique.
- `ingestion/cosia.py:37` — `SOURCE_HORIZON = "2025-01-01"` : millésime amont documenté, OK.

### INSEE / référentiel
- `sentinelle.py:587-611` — 97410 est désormais correctement LIBELLÉ « Saint-Benoît » (le piège
  de VERITE-TERRAIN-3 est corrigé sur main).
- INSEE en dur hors référentiel : concentrés dans `ingestion/run_all.py` (12), `registre/
  remplissage.py` (8), `ingestion/sis_projets.py` (7) — listes de communes d'ingestion/seed là où
  `referentiel_communes.py` existe. **Cosmétique** (données stables), à rapatrier au fil de l'eau.

### Emails / secrets
- Adresses en dur : `contact@labuse.immo` / `victor@labuse.immo` en DÉFAUTS de config (surchageables
  env) — défendable ; `kampusreunion@gmail.com` dans le User-Agent de `ingestion/rnb.py:95` —
  cosmétique (adresse personnelle dans le code).
- **Aucun secret/clé/token en clair trouvé** dans `src/` (grep motifs `api_key/token/secret/password
  = "…"` : zéro hit hors placeholders). Les identifiants passent par env (`INPI_API_*`, etc.).

---

## H6 — TODO / FIXME / XXX / HACK

76 hits bruts dans `src/labuse/` (annexe E) dont ~30 sont la VARIABLE `todo` (listes de travail des
batchs — faux positifs). Les ~45 vrais marqueurs se classent ainsi, **aucun ne décrit un bug actif
vérifié** :

- **« TODO étage 1 / étage 2 / bilan » (~35)** — marqueurs de PLAN, pas de dette : signaux ingérés
  volontairement NON branchés au score tant que le calibrage n'est pas tranché (`models.py:608,642,
  673,747,1659,1694,1771`, `ingestion/bodacc.py`, `inpi_rne.py`, `amenites.py`, `qpv.py`,
  `georisques_layers.py`, `cartofriches.py`, `abf_merimee.py`, `seed_sources.py` ×7,
  `scoring/declassement.py:20,50,55,60,66,76`, `cli.py` ×6). Statut : **amélioration planifiée**,
  cohérente avec la doctrine « rien ne touche le score sans calibrage ». Vérifié : les poids/flags
  concernés ne sont effectivement PAS consommés par le scoring servi.
- **`scoring/score_v_constants.py:130-134` — « TODO v2 : non tranché Phase 0 »** sur les poids
  BODACC (LJ 35, RJ 30…) : les poids SONT servis par score_v avec des valeurs posées d'autorité.
  C'est le seul TODO qui qualifie une VALEUR SERVIE de provisoire → **à trancher** (gênant léger).
- **`ingestion/vegetation.py:23` — « TODO v1.1 : pondération directionnelle »** : amélioration.
- Aucun FIXME, aucun XXX, aucun HACK réel dans `src/` (les hits XXX sont des exemples de libellés
  type « SUP xxx » `api/servitudes.py:78`). Dans `tests/qa/scripts` : 36 hits, même profil.

---

## H7 — Dépendances

### Python — prod (requirements.lock, ce que le VPS installe)
`pip-audit -r requirements.lock --no-deps` (18/10) : **77 paquets, 0 vulnérabilité connue.**
Le verrou PROPRETE-FIX-0 (anyio 4.14.2, starlette 1.3.1, urllib3 2.8.0, weasyprint 70.0,
pypdf 6.19.0…) est effectif. Versions clés : fastapi 0.136.3 · sqlalchemy 2.0.50 · starlette 1.3.1 ·
uvicorn 0.49.0 · pydantic 2.13.4 · psycopg 3.3.4 · stripe 15.3.0 · jinja2 3.1.6 — toutes récentes,
aucune lignée morte.

### Python — venv réel du Mac (`~/Desktop/labuse/.venv`, inclut [ml])
`pip freeze` (139 paquets) interrogé via l'API OSV (pip-audit -r sur le freeze impossible :
`backports.zstd` absent de l'index py3.14 du venv jetable + conflit setuptools — contournement
documenté dans le script) : **1 seule vulnérabilité** — **torch 2.11.0 · GHSA-rrmf-rvhw-rf47**
(= la PYSEC-2025-194 déjà documentée dans pyproject.toml : fix en 2.13.0, INDISPONIBLE sur l'index
macOS arm64). **Non exploitable dans ce contexte** : torch est [ml], JAMAIS installé sur le serveur
(le VPS installe depuis requirements.lock, cœur seulement). Verdict : acceptée et déjà tracée.
- Pin exact `anthropic==0.116.0` (doctrine HYGIÈNE H1 anti-régression VPS) : pas de CVE, mais lignée
  qui vieillit — à revisiter volontairement, jamais par accident.

### npm — front
- **`npm audit --omit=dev` (prod, package-lock seul) : 0 vulnérabilité** (0 info/low/moderate/high/critical).
- `npm audit` complet : **13 vulnérabilités, toutes DEV-ONLY** (8 high : braces/micromatch/
  chokidar/fast-glob/browserslist/source-map-js/tailwindcss≤3.4.19/undici ; 5 moderate :
  vitest/@vitest-mocker/postcss-nested/postcss-selector-parser/baseline-browser-mapping).
  **Non exploitables en service** : chaîne de build/test uniquement, rien n'est servi. À purger à la
  prochaine montée de toolchain (`npm audit fix` suffit pour la plupart). Gravité : à surveiller.
- Versions : react **18.3.1** (lignée 18 — 19 est stable depuis fin 2024 : migration à planifier,
  pas une dette de sécurité), vite 8.2.1 (récent), typescript 5.6.3.

---

## Verdict d'ensemble (angle H)

| Catégorie | Compte | Pire gravité |
|---|---|---|
| Fonctions mortes backend | 41 sûres + 98 probables + 13 vars/imports | cosmétique (dette) |
| Exports front morts | 122 (dont 69 bindings api.ts = features mortes bout-en-bout) | gênant (poids mort) |
| Index manquants | 2 prouvés + 1 indice | gênant (sirene.siren, dvf date) |
| N+1 | 2 côté API à réécrire avant croissance + 2 batch regroupables | gênant |
| Exceptions avalées | 418 silencieuses (sur ~612 broad-except) dont 6 familles dangereuses | gênant (zonage.py:480) |
| Valeurs en dur | 1 URL fausse hors local, 3 labels de run périmés, 0 secret | gênant (vegetation.py:455) |
| TODO | ~45 réels, 0 bug actif, 1 valeur servie « non tranchée » | cosmétique |
| Dépendances | prod Python 0 CVE · npm prod 0 CVE · 1 CVE ML locale tracée · 13 dev npm | à surveiller |

**Rien de bloquant.** Le code est anormalement propre côté dépendances et secrets ; la dette réelle
est (1) le poids mort accumulé (139 fonctions + 122 exports, dont des features entières mortes des
deux côtés), (2) deux index qui coûtent à chaque fiche, (3) les six avaloirs d'exceptions qui
peuvent masquer une donnée fausse, G3 (déjà connu) restant le seul « job faussement vert » prouvé.

---

## Annexe A — scripts d'analyse (rejouables, cf. ../scripts/angle_h_code.sh)

### /tmp/dead_check2.py
```python
#!/usr/bin/env python3
"""Fast dead-code cross-check: one pass tokenization of the whole repo, then classify
vulture 'unused function/class/method' findings."""
import re, os, sys, collections

REPO = os.path.expanduser('~/Desktop/labuse-orfevre')
EXTS = ('.py', '.ts', '.tsx', '.js', '.mjs', '.yaml', '.yml', '.sql', '.sh', '.html', '.toml', '.json', '.cfg', '.ini', '.j2', '.jinja', '.md')
DIRS = ['src', 'frontend/src', 'tests', 'scripts', 'qa', 'config', 'declarations', 'outils', 'deploy', 'docs']
SKIP = {'node_modules', '__pycache__', '.git', 'dist', 'build', 'audit-2026-10'}

token_files = collections.defaultdict(set)    # token -> set(files)
token_count = collections.Counter()
word = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
dashed = re.compile(r'[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+')
dashed_tokens = set()

files_scanned = 0
for d in DIRS:
    base = os.path.join(REPO, d)
    if not os.path.isdir(base): continue
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for fn in files:
            if not fn.endswith(EXTS): continue
            p = os.path.join(dirpath, fn)
            try:
                txt = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            files_scanned += 1
            rel = os.path.relpath(p, REPO)
            toks = word.findall(txt)
            for t in set(toks):
                token_files[t].add(rel)
            token_count.update(toks)
            dashed_tokens.update(dashed.findall(txt))

print(f"# files scanned: {files_scanned}", file=sys.stderr)

# parse vulture
items = []
for line in open('/tmp/vulture_60.txt'):
    m = re.match(r"(.+?):(\d+): unused (function|class|method) '(\w+)'", line)
    if m:
        items.append((m.group(1), int(m.group(2)), m.group(3), m.group(4)))

def decorators(path, lineno):
    try:
        lines = open(path, encoding='utf-8').read().splitlines()
    except Exception:
        return []
    decs = []
    # vulture reports the FIRST DECORATOR line when decorated: check reported line and upward
    if lineno - 1 < len(lines) and lines[lineno - 1].strip().startswith('@'):
        decs.append(lines[lineno - 1].strip())
    j = lineno - 2
    while j >= 0:
        s = lines[j].strip()
        if s.startswith('@'):
            decs.append(s); j -= 1
        elif s == '' or s.startswith('#') or s.endswith(',') or s.endswith('(') or s.endswith(')'):
            # multi-line decorator args — walk up past them
            j -= 1
        else:
            break
    return decs

DEC_ALIVE = re.compile(r'@(\w+)\.(get|post|put|delete|patch|head|options|websocket|middleware|exception_handler|on_event|command|callback|task|validator|field_validator|model_validator|listens_for|register|hookimpl|errorhandler)\b')

sure, probable, decorated = [], [], 0
for path, lineno, kind, name in items:
    full = path if path.startswith('/') else os.path.join(REPO, path)
    rel = os.path.relpath(full, REPO)
    decs = decorators(full, lineno)
    if decs:   # TOUT décorateur = enregistrement dynamique possible (extracteur, route, task…)
        decorated += 1
        continue
    if name.startswith('__') and name.endswith('__'):
        continue
    if name.replace('_', '-') in dashed_tokens:   # dispatch par nom à tirets (jobs, CLI)
        continue
    nfiles = token_files.get(name, set())
    cnt = token_count.get(name, 0)
    others = nfiles - {rel}
    # def site counts 1 occurrence; same-file recursion would raise count
    if not others and cnt <= 1:
        sure.append((rel, lineno, kind, name, cnt, ''))
    elif not others:
        # only own file: could be self-reference (recursion / __all__ / dict dispatch)
        probable.append((rel, lineno, kind, name, cnt, 'refs only in own file'))
    elif all(('tests/' in f or f.endswith('.md')) for f in others):
        probable.append((rel, lineno, kind, name, cnt, 'refs only tests/docs: ' + ','.join(sorted(others))[:120]))

print(f"== SURE ({len(sure)}) ==")
for r in sure: print("%s:%d\t%s\t%s\t(occ=%d)" % r[:5])
print(f"== PROBABLE ({len(probable)}) ==")
for r in probable: print("%s:%d\t%s\t%s\t(occ=%d)\t%s" % r)
print(f"# decorated skipped: {decorated}", file=sys.stderr)
```
### /tmp/scan_n1.py
```python
#!/usr/bin/env python3
"""Find for-loops whose body contains session/db execute or ORM query calls (N+1 candidates)."""
import ast, os, sys

root = sys.argv[1]
CALLS = ('execute', 'scalar', 'scalars', 'first', 'one', 'one_or_none', 'fetchone', 'fetchall', 'get')

def loop_queries(node):
    hits = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in ('execute', 'scalar', 'scalars'):
                # receiver name
                recv = sub.func.value
                rname = ''
                if isinstance(recv, ast.Name): rname = recv.id
                elif isinstance(recv, ast.Attribute): rname = recv.attr
                elif isinstance(recv, ast.Call):
                    f2 = recv.func
                    rname = getattr(f2, 'attr', getattr(f2, 'id', ''))
                if rname in ('session', 'db', 's', 'sess', 'conn', 'connection', 'cur', 'cursor', 'engine', 'sql'):
                    hits.append((sub.lineno, rname + '.' + sub.func.attr))
            if sub.func.attr == 'query':
                recv = sub.func.value
                if isinstance(recv, ast.Name) and recv.id in ('session', 'db', 's'):
                    hits.append((sub.lineno, recv.id + '.query'))
    return hits

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', '.git')]
    for fn in files:
        if not fn.endswith('.py'): continue
        p = os.path.join(dirpath, fn)
        try:
            tree = ast.parse(open(p, encoding='utf-8').read())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                hits = loop_queries(node)
                if hits:
                    rel = os.path.relpath(p, root)
                    iter_src = ''
                    if isinstance(node, ast.For):
                        try: iter_src = ast.unparse(node.iter)[:70]
                        except Exception: pass
                    print(f"{rel}:{node.lineno}\tloop over [{iter_src}]\t{len(hits)} query-calls: " +
                          ', '.join(f"L{l} {n}" for l, n in hits[:4]))
```
### /tmp/scan_except.py
```python
#!/usr/bin/env python3
"""Scan for swallowed exceptions: except handlers whose body is only pass/continue/return None/return const, with no logging/raise."""
import ast, sys, os

def body_is_swallow(handler):
    # True if handler body contains no call to logging/print/raise — i.e. silently swallows
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return False
        if isinstance(node, ast.Call):
            f = node.func
            name = ''
            if isinstance(f, ast.Attribute):
                name = f.attr
                # logger.warning etc
                if name in ('debug','info','warning','error','exception','critical','log','warn'):
                    return False
            elif isinstance(f, ast.Name):
                if f.id in ('print','log','logger'):
                    return False
    return True

def is_trivial(handler):
    body = handler.body
    if len(body) == 1:
        s = body[0]
        if isinstance(s, (ast.Pass, ast.Continue, ast.Break)):
            return True
        if isinstance(s, ast.Return):
            return True
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):
            return True
    return False

root = sys.argv[1]
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', '.git')]
    for fn in files:
        if not fn.endswith('.py'): continue
        p = os.path.join(dirpath, fn)
        try:
            tree = ast.parse(open(p, encoding='utf-8').read())
        except Exception as e:
            print(f"PARSE_FAIL {p}: {e}", file=sys.stderr); continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for h in node.handlers:
                    etype = ast.unparse(h.type) if h.type else 'BARE'
                    if is_trivial(h) and body_is_swallow(h):
                        kind = type(h.body[0]).__name__
                        val = ''
                        if isinstance(h.body[0], ast.Return) and h.body[0].value is not None:
                            val = ast.unparse(h.body[0].value)[:40]
                        rel = os.path.relpath(p, root)
                        print(f"{rel}:{h.lineno}\t{etype}\t{kind} {val}")
```
### /tmp/osv_check.py
```python
#!/usr/bin/env python3
"""Query OSV for a pip freeze list (ecosystem PyPI)."""
import json, sys, urllib.request, ssl
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

freeze = sys.argv[1]
pkgs = []
for line in open(freeze):
    line = line.strip()
    if not line or line.startswith('#') or '==' not in line:
        continue
    name, ver = line.split('==', 1)
    name = name.split('[')[0].strip()
    pkgs.append((name, ver.strip()))

queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pkgs]
out = []
for i in range(0, len(queries), 100):
    batch = queries[i:i+100]
    req = urllib.request.Request("https://api.osv.dev/v1/querybatch",
                                 data=json.dumps({"queries": batch}).encode(),
                                 headers={"Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=60, context=CTX))
    out.extend(res["results"])

n_vuln = 0
for (name, ver), r in zip(pkgs, out):
    vulns = r.get("vulns") or []
    if vulns:
        n_vuln += 1
        ids = [v["id"] for v in vulns]
        print(f"{name}=={ver}\t{','.join(ids)}")
print(f"# total pkgs={len(pkgs)} vuln={n_vuln}", file=sys.stderr)
```

## Annexe B — « Probablement mort » backend (98 : refs uniquement tests/docs)

```
src/labuse/alertes.py:67	function	rename_watch_zone	(occ=2)	refs only tests/docs: docs/audits/M54_EXPO3_statut.md
src/labuse/api/app.py:935	function	clear_mem_cache	(occ=5)	refs only tests/docs: docs/product/SAFE_BUGFIX_BATCH_REPORT.md,tests/conftest.py
src/labuse/api/app.py:3213	function	_division_fiche	(occ=8)	refs only tests/docs: docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-1.md,docs/audit-2026-09/COHERENCE-RUN-1.md,tests/test_circuit1_lot2.py
src/labuse/api/app.py:3971	function	parcelles_matchant_hash	(occ=7)	refs only tests/docs: docs/archive/chantiers-sept-2026/FILTRES-AUDIT-1.md,docs/audit-2026-09/VEILLE-AUDIT-1.md,tests/test_veille_parite.py
src/labuse/api/app.py:5032	function	_alea_nature	(occ=5)	refs only tests/docs: tests/test_fiche1_aleas.py
src/labuse/api/app.py:6958	function	_calculette_for_pdf	(occ=5)	refs only tests/docs: docs/archive/etat-diagnostic/AUDIT-FICHE-PDF.md,docs/audits/AUDIT_MANDAT_DVF.md,tests/test_prix_sortie1_unique.py
src/labuse/api/app.py:8822	function	_premium_head	(occ=8)	refs only tests/docs: qa/crm/AUDIT_M136.md,qa/crm/RAPPORT_M136_P1.md,qa/crm/RAPPORT_M137.md
src/labuse/api/enrichment.py:547	function	warm_commune	(occ=2)	refs only tests/docs: qa/m34/M34_BILAN.md
src/labuse/api/events.py:267	function	annoncer_nouveaute	(occ=4)	refs only tests/docs: docs/audit-2026-09/VEILLE-2.md,tests/test_veille2_lot5.py,tests/test_veille_fix2_lot_b.py
src/labuse/api/pdf_premium.py:344	function	render_fiche_pdf	(occ=14)	refs only tests/docs: docs/DETTE_SUITE.md,docs/archive/etat-diagnostic/AUDIT-FICHE-PDF.md,docs/audit-2026-09/EXPORTS/DONNEES-RAPPORT.md,docs/a
src/labuse/api/protection.py:177	function	reset_etat_memoire	(occ=5)	refs only tests/docs: tests/test_audit_secu.py,tests/test_protection.py
src/labuse/api/protection.py:523	function	filigrane_export	(occ=3)	refs only tests/docs: docs/cartographie/CARTO_API.md,tests/test_protection.py
src/labuse/brevo.py:164	function	verifier_templates	(occ=8)	refs only tests/docs: docs/COMPTE/COMPTE-AUDIT-2.md,docs/COMPTE/COMPTE-RENDU-COMPTE-2.md,docs/audit-2026-09/VEILLE-AUDIT-2.md,tests/test_compt
src/labuse/cascade/context.py:458	method	dvf_stats	(occ=9)	refs only tests/docs: docs/BACKLOG.md,docs/archive/mandats-M55-M85/RAPPORT_M79.md,docs/audits/AUDIT_M91.md,docs/cartographie/CARTO_SCORING.md,
src/labuse/communes.py:63	function	is_reliable	(occ=7)	refs only tests/docs: docs/cartographie/CARTO_CORE.md,tests/test_agorah_plu_connector.py,tests/test_communes_gold_standard.py
src/labuse/connectors/dpe.py:70	function	in_reunion	(occ=5)	refs only tests/docs: docs/cartographie/CARTO_INGESTION.md,tests/test_dpe.py
src/labuse/connectors/georisques.py:130	method	by_latlon	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_INGESTION.md
src/labuse/connectors/inpi_rne.py:107	function	compute_age	(occ=11)	refs only tests/docs: docs/archive/notes-sources-juillet/NOTES_INPI.md,docs/cartographie/CARTO_INGESTION.md,tests/test_inpi_rne.py
src/labuse/copilote_v2/answering.py:73	function	chemin_pour	(occ=2)	refs only tests/docs: tests/test_copilote2_routeur.py
src/labuse/copilote_v2/answering.py:545	function	_projet_form	(occ=5)	refs only tests/docs: docs/audits/AUDIT_M115_CHEMINS.md,docs/audits/AUDIT_M118_4_MISSIONS.md,tests/test_copilote_scenario.py
src/labuse/copilote_v2/missions_lourdes.py:28	function	preparer_projet	(occ=5)	refs only tests/docs: docs/audits/AUDIT_M108_CAPACITES.md,tests/test_copilote_projet.py
src/labuse/copilote_v2/recap.py:59	function	recap_recherche	(occ=4)	refs only tests/docs: docs/audits/AUDIT_M107.md,docs/audits/AUDIT_M108_CAPACITES.md,docs/audits/AUDIT_M118_4_MISSIONS.md
src/labuse/copilote_v2/recap.py:81	function	recap_verification	(occ=2)	refs only tests/docs: docs/audits/AUDIT_M108_CAPACITES.md
src/labuse/copilote_v2/telemetrie.py:52	function	critere_non_traduisible	(occ=5)	refs only tests/docs: docs/archive/chantiers-sept-2026/COPILOTE-AUDIT-1.md,docs/audits/AUDIT_M108_CAPACITES.md
src/labuse/courrier.py:512	function	kpi_dashboard	(occ=3)	refs only tests/docs: tests/test_courrier_boucle.py
src/labuse/emails.py:12	function	reset_password	(occ=3)	refs only tests/docs: docs/COMPTE/COMPTE-RENDU-COMPTE-2.md,docs/archive/mandats-M55-M85/RAPPORT_M85.md
src/labuse/exports/archive.py:33	function	lire_archive	(occ=3)	refs only tests/docs: tests/test_exports2_lot1.py,tests/test_exports2_lot2.py
src/labuse/exports/miroir.py:250	function	non_cables	(occ=4)	refs only tests/docs: tests/test_sources_fix1.py
src/labuse/faisabilite/zone_norm.py:45	function	zone_phasage	(occ=6)	refs only tests/docs: tests/test_zone_norm.py
src/labuse/filtres/__init__.py:108	function	sources_live	(occ=3)	refs only tests/docs: tests/test_circuit3_lot4.py
src/labuse/filtres/__init__.py:138	function	etat_pour_data_source	(occ=3)	refs only tests/docs: tests/test_circuit3_lot5.py
src/labuse/filtres/quarantaine.py:44	function	sources_live_registre	(occ=2)	refs only tests/docs: docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-3.md
src/labuse/gabarit/limites.py:86	function	elongation_from_obb	(occ=5)	refs only tests/docs: tests/gabarit/test_limites.py
src/labuse/geo.py:45	function	intersection_area_ratio	(occ=3)	refs only tests/docs: docs/GABARIT/A0-RAPPORT.md,docs/cartographie/CARTO_CORE.md
src/labuse/geo.py:64	function	geom_area_m2	(occ=7)	refs only tests/docs: docs/GABARIT/A0-RAPPORT.md,docs/cartographie/CARTO_CORE.md,tests/test_geo_surface.py
src/labuse/implantation/rendu.py:267	function	ecrire_scenario_json	(occ=2)	refs only tests/docs: tests/test_implantation1.py
src/labuse/ingestion/agorah_plu.py:145	function	agorah_plu_preflight	(occ=4)	refs only tests/docs: docs/cartographie/CARTO_INGESTION.md,tests/test_agorah_plu_connector.py
src/labuse/ingestion/bodacc.py:118	function	sirens_jamais_sondes	(occ=2)	refs only tests/docs: docs/archive/mandats-M55-M85/RAPPORT_M71.md
src/labuse/ingestion/bodacc.py:207	function	parcelles_sous_pression	(occ=5)	refs only tests/docs: docs/archive/notes-sources-juillet/NOTES_BODACC.md,docs/cartographie/CARTO_INGESTION.md,tests/test_bodacc.py
src/labuse/ingestion/cosia_couverture.py:149	function	build_cosia_piscines	(occ=2)	refs only tests/docs: docs/audit-2026-09/SOURCES/SOURCES-4.md
src/labuse/ingestion/division_or.py:571	function	check_exclusions_revue	(occ=3)	refs only tests/docs: docs/mandats/O12_PARTIEL_RAPPORT.md,tests/test_division_or.py
src/labuse/ingestion/dpe.py:373	function	ingest_orphelins	(occ=3)	refs only tests/docs: docs/archive/carte-maplibre/RAPPORT_M_V_DPE.md,docs/cartographie/CARTO_INGESTION.md
src/labuse/ingestion/georisques_layers.py:217	function	ingest_icpe_commune	(occ=2)	refs only tests/docs: docs/audit-2026-09/SOURCES/SOURCES-4.md
src/labuse/ingestion/georisques_layers.py:238	function	ingest_sols_pollues_commune	(occ=2)	refs only tests/docs: docs/audit-2026-09/SOURCES/SOURCES-4.md
src/labuse/ingestion/georisques_layers.py:257	function	ingest_cavites_commune	(occ=2)	refs only tests/docs: docs/audit-2026-09/SOURCES/SOURCES-4.md
src/labuse/ingestion/ortho_equipements.py:131	function	precision_validee	(occ=3)	refs only tests/docs: docs/archive/mandats-M55-M85/RAPPORT_M71.md,docs/cartographie/CARTO_INGESTION.md
src/labuse/ingestion/ortho_equipements.py:151	function	branchements_solaire	(occ=3)	refs only tests/docs: docs/cartographie/CARTO_INGESTION.md
src/labuse/ingestion/pv_detection.py:13	function	detect_rooftop_pv	(occ=5)	refs only tests/docs: docs/archive/fable-waves-juillet/MANDAT_FABLE_HABITAT_SOLAIRE.md,docs/archive/fable-waves-juillet/MANDAT_FABLE_WAVE_DETE
src/labuse/ingestion/sup_gpu.py:52	function	inventaire_974	(occ=2)	refs only tests/docs: docs/CIRCUIT/COMPTE-RENDU-SOURCES-1.md
src/labuse/mailfile.py:331	function	depart_des_programmes	(occ=6)	refs only tests/docs: docs/audit-2026-09/VEILLE-AUDIT-2.md,tests/test_compte2_mailfile.py
src/labuse/models.py:137	class	SourceVeille	(occ=2)	refs only tests/docs: docs/audit-2026-09/RAPPORT-SENTINELLE-1.md
src/labuse/models.py:186	class	ParcelSourceResult	(occ=3)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:341	class	ParcelVeilleSuccession	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:356	class	ScoreSnapshot	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:370	class	ScoreSnapshotParcelle	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:385	class	PmProprietaireMillesime	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:461	class	SourceCheck	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:479	class	ParcelSignal	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:505	class	WatchSnapshot	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:528	class	SpatialLayer	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:559	class	DvfMutation	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:578	class	SitadelPermit	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:602	class	BodaccProcedure	(occ=3)	refs only tests/docs: docs/archive/notes-sources-juillet/NOTES_BODACC.md,docs/cartographie/CARTO_CORE.md
src/labuse/models.py:631	class	PmDirigeant	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:694	class	DpeRecord	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:742	class	ParcelAmenite	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:847	class	ProjetParcelle	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:878	class	OwnerEnrichment	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:894	class	OwnerDenomLookup	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:910	class	BodaccAnnonceOwner	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:929	class	MatchingReviewQueue	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:941	class	ParcelVScore	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:965	class	DvfMutationParcelle	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:997	class	PScoreV2Run	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/models.py:1013	class	ParcelPScoreV2	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_CORE.md
src/labuse/notif_registry.py:93	function	peut_mail	(occ=3)	refs only tests/docs: tests/test_notifications_m85.py
src/labuse/obsimmo.py:121	function	get_market_by_parent_commune	(occ=3)	refs only tests/docs: docs/cartographie/CARTO_CORE.md,tests/test_obsimmo.py
src/labuse/pente_fmt.py:27	function	pente_texte	(occ=2)	refs only tests/docs: docs/archive/divers-sources-recon/CHAMPS-MORTS.md
src/labuse/pige/html_next.py:83	function	extraire_annonces	(occ=7)	refs only tests/docs: tests/test_pige_html.py
src/labuse/pige/signaux.py:364	function	distribution_ecarts	(occ=4)	refs only tests/docs: tests/test_pige_depot2.py
src/labuse/registre/couverture.py:109	function	probleme_cles	(occ=4)	refs only tests/docs: tests/test_circuit2_lot1.py
src/labuse/reglages.py:91	function	set_int	(occ=2)	refs only tests/docs: tests/test_copilote_retention_r11.py
src/labuse/regles/__init__.py:118	function	couverture_moteurs_pkg	(occ=2)	refs only tests/docs: tests/test_circuit4_lot1.py
src/labuse/renouvellement.py:63	function	code_from_detail	(occ=10)	refs only tests/docs: tests/test_renouvellement.py
src/labuse/rgpd_dirigeants.py:37	function	purger_nationalite_et_raw	(occ=5)	refs only tests/docs: tests/test_d3_rgpd_dirigeants.py
src/labuse/scoring/cascade_v2.py:163	function	lire_ocsge	(occ=2)	refs only tests/docs: docs/audit-2026-09/SCORING-6-RAPPORT.md
src/labuse/scoring/dryrun.py:111	function	matrice_report	(occ=2)	refs only tests/docs: docs/cartographie/CARTO_SCORING.md
src/labuse/scoring/icd.py:98	function	compute_from_row	(occ=14)	refs only tests/docs: docs/cartographie/CARTO_SCORING.md,tests/test_icd_equivalence.py,tests/test_scoring_pure.py
src/labuse/scoring/ingestion_journal.py:68	function	parcelles_a_recalculer	(occ=3)	refs only tests/docs: docs/audit-2026-09/SCORING-6-RAPPORT.md,tests/test_scoring6_exploitation.py
src/labuse/scoring/lignee_tete.py:25	function	build_parcel_entree_tete	(occ=5)	refs only tests/docs: docs/BASCULE_RUN_RUNBOOK.md,docs/archive/mandats-M55-M85/RAPPORT_M80.md,docs/audit-2026-09/CONNEXIONS-RAPPORT.md
src/labuse/scoring/score_labuse.py:212	function	libelle_client_bande	(occ=13)	refs only tests/docs: docs/audit-2026-09/SCORING-7-QV15.md,tests/test_scoring6_score_labuse.py,tests/test_scoring8_c26.py
src/labuse/scoring/tiers_client.py:125	function	montre_multiple	(occ=3)	refs only tests/docs: docs/audit-2026-09/PALIERS-1.md
src/labuse/stripe_lecture.py:148	function	vider_cache	(occ=2)	refs only tests/docs: tests/test_dashboard.py
src/labuse/surface.py:101	function	enrichir_payload	(occ=3)	refs only tests/docs: tests/test_contenance1_lot_b.py
src/labuse/totp.py:40	function	code_totp	(occ=9)	refs only tests/docs: tests/test_2fa.py
src/labuse/veille_grille.py:63	function	kinds_broadcast	(occ=2)	refs only tests/docs: tests/test_veille_grille.py
src/labuse/veille_grille.py:97	function	digest_heure_reunion	(occ=2)	refs only tests/docs: tests/test_veille_grille.py
src/labuse/verdict_servi.py:222	function	sql_exists_servable	(occ=5)	refs only tests/docs: qa/m34/M34_BILAN.md,tests/test_verdict_servi.py
```

## Annexe C — exports front jamais importés (ts-prune, 122)

```
src/components/Loading.tsx:79 - Loading
src/lib/api.ts:239 - getScoringBacktest
src/lib/api.ts:371 - Entonnoir
src/lib/api.ts:458 - postProfilLigne
src/lib/api.ts:462 - getParcelleZone
src/lib/api.ts:765 - getPromoteurAcquisitions
src/lib/api.ts:868 - getAccueilFraicheur
src/lib/api.ts:871 - AccueilCetteSemaine
src/lib/api.ts:974 - copiloteV2Heros
src/lib/api.ts:983 - CopiloteVeille
src/lib/api.ts:1022 - getProspectionSolaire
src/lib/api.ts:1025 - prospectionSolaireCsvUrl
src/lib/api.ts:1062 - getPiscinesPoints
src/lib/api.ts:1070 - postPasUnePiscine
src/lib/api.ts:1122 - getAssemblageVoisines
src/lib/api.ts:1200 - pdfUrl
src/lib/api.ts:1266 - CourrierEnvoi
src/lib/api.ts:1269 - ShortlistSujet
src/lib/api.ts:1275 - getWatchZones
src/lib/api.ts:1276 - createWatchZone
src/lib/api.ts:1280 - renameWatchZone
src/lib/api.ts:1282 - deleteWatchZone
src/lib/api.ts:1284 - getAlertes
src/lib/api.ts:1285 - refreshAlertes
src/lib/api.ts:1286 - ackAlerte
src/lib/api.ts:1332 - getExplain
src/lib/api.ts:1336 - postFeedback
src/lib/api.ts:1434 - modPatrimoineCsvUrl
src/lib/api.ts:1591 - getSavedSearches
src/lib/api.ts:1592 - saveSearch
src/lib/api.ts:1594 - deleteSearch
src/lib/api.ts:1597 - getSearchApercu
src/lib/api.ts:1601 - veilleNL
src/lib/api.ts:1687 - getAdminStripe
src/lib/api.ts:1887 - getAdminSources
src/lib/api.ts:1888 - postAdminSourceCadence
src/lib/api.ts:1890 - postAdminSourceRelancer
src/lib/api.ts:1893 - postAdminSourceAffichage
src/lib/api.ts:1896 - postAdminSourceVeilleVerifier
src/lib/api.ts:1901 - postAdminSourceVeilleMail
src/lib/api.ts:1906 - getHealthzCrons
src/lib/api.ts:1960 - getAdminFluxRunEtat
src/lib/api.ts:1961 - postAdminFluxArreterRun
src/lib/api.ts:1973 - getAdminFlux
src/lib/api.ts:1974 - getAdminFluxRuns
src/lib/api.ts:2076 - postFaisabiliteRecalcul
src/lib/api.ts:2095 - faisabiliteExplain
src/lib/api.ts:2225 - ProjetDerive
src/lib/api.ts:2231 - Apercu
src/lib/api.ts:2237 - rejouerProjet
src/lib/api.ts:2292 - projetCsvUrl
src/lib/api.ts:2349 - radarDeposer
src/lib/api.ts:2378 - getRadarDepotOuvert
src/lib/api.ts:2379 - radarDepotAgenceAnalyser
src/lib/api.ts:2387 - radarInteresse
src/lib/api.ts:2403 - getRadarAInstruire
src/lib/api.ts:2484 - getRadarBienDetail
src/lib/api.ts:2487 - radarSignaler
src/lib/api.ts:2504 - radarInstruire
src/lib/api.ts:2533 - getRadarSignaux
src/lib/api.ts:2537 - getRadarVeilles
src/lib/api.ts:2543 - renommerRadarVeille
src/lib/api.ts:2622 - getAdminCommuneContacts
src/lib/api.ts:2673 - postAdminCircuitVerrous
src/lib/api.ts:2675 - postAdminCircuitPurger
src/lib/api.ts:2725 - getFinancierQuestionnaire
src/lib/api.ts:2727 - putFinancierQuestionnaire
src/lib/api.ts:2741 - validerFinancierQuestionnaire
src/lib/api.ts:2815 - getBilanRatios
src/lib/filters.ts:191 - activeChips
src/lib/filters.ts:206 - removeToken
src/lib/filters.ts:76 - inDefaultPerimetre
src/lib/format.ts:36 - fmtPct
src/lib/layers.ts:180 - layerInfo
src/lib/perimetres.ts:11 - PERIM_RESIDUEL
src/lib/perimetres.ts:12 - PERIM_POTENTIEL
src/lib/perimetres.ts:23 - PERIM_RAYON_ADAPTATIF
src/lib/permisEtats.ts:36 - PERMIS_LEGENDE
src/lib/status.ts:303 - ageSignal
src/lib/status.ts:97 - DECLASSE_ORDER
src/lib/status.ts:129 - BANDE_QUALITE
src/lib/status.ts:179 - BPE_DOM_CODES
src/lib/status.ts:232 - statutColor
src/lib/status.ts:236 - completudeColor
src/lib/status.ts:242 - V_BAND_META
src/lib/status.ts:279 - EQUIP_META
src/lib/strings.ts:652 - ClientStrings
src/lib/types.ts:737 - DestinationsReferentiel
src/components/admin/Programmes.tsx:112 - ProgrammesSection
src/components/copilote/CopiloteEmbarque.tsx:13 - CopiloteEmbarque
src/components/copilote/ui.tsx:9 - Etiquette
src/components/copilote/ui.tsx:30 - SecHead
src/components/copilote/ui.tsx:44 - PillStatut
src/components/crm/DeplacerMenu.tsx:31 - default
src/components/documents/catalogue.ts:11 - DocBadge
src/components/fiche/AnalyseLabuseCard.tsx:73 - default
src/components/fiche/constructibilite.tsx:771 - FiscalLeviersBlock
src/components/fiche/constructibilite.tsx:1063 - ConstructibiliteSection
src/components/fiche/leBien.tsx:240 - LeBienSection
src/components/outils/blocB.tsx:311 - O7Carnet
src/components/outils/blocB.tsx:395 - O9Rarete
src/components/outils/blocB.tsx:452 - O10Bascules
src/components/outils/EntreeParcelle.tsx:42 - default
src/components/outils/moteurs.tsx:430 - M17
src/components/outils/moteurs.tsx:704 - MarcheCommune
src/components/outils/moteurs.tsx:755 - M19
src/components/outils/ParcelPicker.tsx:6 - ParcelPicker
src/components/outils/RadarDeclaratif.tsx:12 - Declaratif
src/components/outils/registry.ts:9 - VIOLET_DIM
src/components/outils/registry.ts:38 - GROUPS
src/components/outils/ScoringV2.tsx:50 - ScoringV2Module
src/components/panel/ResultsSection.tsx:274 - segmentOf
src/components/radar/DepotAgence.tsx:19 - DepotAgence
src/components/shared/IconTile.tsx:18 - default
src/components/ui/Badge.tsx:36 - default
src/components/ui/Bouton.tsx:59 - default
src/components/ui/Case.tsx:30 - default
src/components/ui/Chevron.tsx:24 - default
src/components/ui/Chip.tsx:44 - default
src/components/ui/Reinitialiser.tsx:36 - default
src/components/ui/Retour.tsx:20 - default
src/components/ui/Tri.tsx:28 - default
```

## Annexe D — exceptions avalées, liste exhaustive (418 · fichier:ligne · type attrapé · geste)

```
agent_regle.py:108	Exception	Pass 
agent_regle.py:122	Exception	Return (dict(vide), 'JSON invalide')
agent_source.py:112	Exception	Pass 
agent_source.py:141	Exception	Continue 
agent_source.py:149	Exception	Return None
ai/core.py:221	ValueError	Return None
ai/core.py:456	ValueError	Return IAResult(text='', model=model, degraded=
api/accueil.py:130	Exception	Return None
api/accueil.py:188	Exception	Pass 
api/accueil.py:198	Exception	Pass 
api/accueil.py:204	Exception	Pass 
api/accueil.py:54	Exception	Return (None, None)
api/accueil.py:69	Exception	Return None
api/app.py:104	Exception	Pass 
api/app.py:1093	Exception	Pass 
api/app.py:233	Exception	Pass 
api/app.py:2455	Exception	Pass 
api/app.py:3183	FileNotFoundError	Return None
api/app.py:3310	Exception	Pass 
api/app.py:3351	Exception	Pass 
api/app.py:357	UnicodeError	Pass 
api/app.py:5144	Exception	Return None
api/app.py:5308	Exception	Return _bloc_indisponible('depots')
api/app.py:5575	Exception	Return {'disponible': False, **_bloc_indisponib
api/app.py:5685	Exception	Return _bloc_indisponible('gestionnaires')
api/app.py:5784	Exception	Pass 
api/app.py:5800	Exception	Return _bloc_indisponible('radar_procedure')
api/app.py:5827	Exception	Return None
api/app.py:5876	Exception	Return None
api/app.py:5898	Exception	Return (None, None)
api/app.py:5950	Exception	Return None
api/app.py:6048	Exception	Return _bloc_indisponible('historique_site')
api/app.py:6059	Exception	Return _bloc_indisponible('voisinage_proche')
api/app.py:6188	Exception	Return _bloc_indisponible('reglement_plu')
api/app.py:6220	Exception	Return _bloc_indisponible('potentiel_transforma
api/app.py:6604	Exception	Pass 
api/app.py:7472	Exception	Return 400
api/app.py:7744	Exception	Pass 
api/app.py:819	Exception	Pass 
api/app.py:842	Exception	Return JSONResponse(status_code=503, content={'
api/app.py:8461	HTTPException	Continue 
api/app.py:87	Exception	Pass 
api/auth.py:172	Exception	Return None
api/auth.py:192	(ValueError, TypeError)	Return False
api/auth.py:279	(ValueError, TypeError)	Return None
api/bilan.py:314	Exception	Return ''
api/coffre_ui.py:51	(ValueError, TypeError)	Return None
api/couches_tuyau.py:218	Exception	Pass 
api/courrier.py:174	Exception	Pass 
api/dashboard.py:1321	Exception	Return []
api/dashboard.py:1456	Exception	Pass 
api/dashboard.py:1675	Exception	Pass 
api/dashboard.py:1722	Exception	Pass 
api/dashboard.py:182	Exception	Pass 
api/dashboard.py:1864	Exception	Pass 
api/dashboard.py:1931	Exception	Pass 
api/dashboard.py:194	Exception	Pass 
api/dashboard.py:2095	Exception	Return defaut
api/dashboard.py:2120	Exception	Pass 
api/dashboard.py:2152	Exception	Return 0.0
api/dashboard.py:2165	Exception	Return 0
api/dashboard.py:2344	Exception	Pass 
api/dashboard.py:2454	Exception	Return None
api/dashboard.py:2497	Exception	Pass 
api/dashboard.py:3055	Exception	Return []
api/dashboard.py:3064	Exception	Return []
api/dashboard.py:329	Exception	Return {'etat': 'absent', 'chemin': rep, 'age_j
api/dashboard.py:3327	Exception	Pass 
api/dashboard.py:343	Exception	Return {'poses': None, 'attendus': None}
api/dashboard.py:377	Exception	Return {'ok': None, 'sur': None, 'dernier_ts': 
api/dashboard.py:386	Exception	Return a_iso > b_iso
api/dashboard.py:532	Exception	Pass 
api/dashboard.py:639	Exception	Pass 
api/division_review.py:101	Exception	Continue 
api/documents.py:225	Exception	Pass 
api/documents_bibliotheque.py:103	Exception	Return None
api/documents_bibliotheque.py:53	Exception	Return {}
api/documents_bibliotheque.py:96	Exception	Return None
api/enrichment.py:147	Exception	Return {'available': False, 'note': f'RGE ALTI 
api/enrichment.py:174	Exception	Return {'available': False, 'note': f'RGE ALTI 
api/enrichment.py:333	Exception	Return (kind, None)
api/enrichment.py:498	Exception	Return {'available': False, 'note': f'Indisponi
api/fiche_ask.py:270	Exception	Return (request.client.host if request.client e
api/fiche_commune.py:456	Exception	Return False
api/ia.py:390	json.JSONDecodeError	Return {'stub': False, 'out_of_scope': 'réponse
api/ia.py:407	ValidationError	Return {'stub': False, 'out_of_scope': f'filtre
api/ia.py:582	json.JSONDecodeError	Return {'stub': False, 'fallback': True, 'messa
api/ia.py:595	ValidationError	Return {'stub': False, 'fallback': True, 'messa
api/marche_bloc.py:59	Exception	Return []
api/modules.py:2082	Exception	Pass 
api/modules.py:396	Exception	Pass 
api/modules.py:844	Exception	Return 500
api/mon_secteur.py:23	Exception	Return 8
api/moteurs.py:36	Exception	Return defaut
api/moteurs.py:47	Exception	Return [0.5, 1, 2, 5]
api/moteurs.py:664	Exception	Pass 
api/onboarding.py:415	ValueError	Return HTMLResponse(_page('mot de passe', f"<h1
api/onboarding.py:587	Exception	Pass 
api/onboarding.py:624	ValueError	Return HTMLResponse(_page('mot de passe', f"<h1
api/onboarding.py:941	Exception	Return ''
api/ops.py:134	Exception	Pass 
api/ops.py:150	Exception	Pass 
api/ops.py:162	Exception	Pass 
api/ops.py:172	Exception	Pass 
api/ops.py:375	Exception	Pass 
api/ortho_proxy.py:172	Exception	Return 'relais'
api/plan_situation.py:44	Exception	Return None
api/plan_situation.py:77	Exception	Continue 
api/pre_dossier.py:134	Exception	Pass 
api/pre_dossier.py:225	Exception	Pass 
api/pre_dossier.py:372	Exception	Pass 
api/pre_dossier.py:68	Exception	Return (False, None)
api/pre_dossier.py:862	Exception	Pass 
api/projets.py:1067	Exception	Pass 
api/projets.py:1092	Exception	Return {}
api/projets.py:1176	Exception	Pass 
api/projets.py:318	Exception	Return _SHORTLIST_MAX_DEFAUT
api/projets.py:33	Exception	Return {}
api/projets.py:358	Exception	Return {'total': None, 'etage0': None}
api/projets.py:375	Exception	Return None
api/protection.py:262	Exception	Pass 
api/protection.py:442	Exception	Return JSONResponse(status_code=422, content={'
api/sante.py:65	Exception	Return (False, f'config IA illisible ({type(e).
api/score_v2.py:49	AttributeError	Return f'Analyse LABUSE arrêtée au {str(ca)[:10
api/scoreur.py:147	Exception	Pass 
api/servitudes.py:208	Exception	Pass 
api/servitudes.py:218	Exception	Return detail
api/site_voisinage.py:27	Exception	Return (100, 36)
api/traducteur.py:138	Exception	Pass 
audit.py:150	Exception	Return AuditResult(ok=False, error='source_indi
audit.py:170	ValueError	Return AuditResult(ok=False, error='entree_inva
audit.py:172	geocode.BanIndisponible	Return AuditResult(ok=False, error='source_indi
audit.py:174	geocode.BanIntrouvable	Return AuditResult(ok=False, error='introuvable
audit.py:183	Exception	Return AuditResult(ok=False, error='source_indi
audit.py:203	Exception	Return AuditResult(ok=False, error='source_indi
audit.py:76	Exception	Pass 
bascule_flux.py:107	Exception	Pass 
bascule_flux.py:314	Exception	Return None
bascule_flux.py:408	Exception	Pass 
bascule_flux.py:433	Exception	Pass 
bascule_flux.py:461	Exception	Return {'changees': False, 'detail': 'chaîne ré
bascule_flux.py:64	FileNotFoundError	Return {'ok': False, 'fichiers': fichiers, 'mot
bascule_flux.py:66	Exception	Return {'ok': False, 'fichiers': fichiers, 'mot
bascule_flux.py:81	OSError	Return None
bascule_gardes.py:471	ValueError	Return None
bati.py:40	Exception	Return {}
bilan/reperes.py:28	Exception	Return None
brevo.py:334	Exception	Pass 
cascade/layers/etage0_ext.py:30	Exception	Return {}
chasse_banc.py:47	ValueError	Return r.text
circuit_dependance.py:160	Exception	Return []
circuit_garanties.py:327	Exception	Pass 
circuit_garanties.py:716	Exception	Return None
circuit_taches.py:29	OSError	Pass 
circuit_taches.py:49	(OSError, ValueError)	Return None
circuit_taches.py:59	OSError	Pass 
circuit_verrous.py:1043	(OSError, TypeError)	Return ''
circuit_verrous.py:835	Exception	Return ResultatVerrou('V6b', PHRASES['V6b'], 'c
circuit_verrous.py:962	OSError	Continue 
cli.py:3273	OSError	Pass 
cli.py:4105	Exception	Pass 
cli.py:5091	Exception	Pass 
coherence_journal.py:77	Exception	Pass 
comptes.py:59	KeyError	Return default
connectors/base.py:63	Exception	Return ConnectionTestResult(self.name, False, f
connectors/bodacc.py:58	(TypeError, ValueError)	Return None
connectors/cartofriches.py:79	Exception	Return None
connectors/inpi_rne.py:151	(TypeError, ValueError)	Return None
connectors/inpi_rne.py:349	Exception	Return ConnectionTestResult(self.name, False, f
connectors/inpi_rne.py:84	Exception	Return None
connectors/merimee.py:53	(TypeError, ValueError)	Return None
connectors/qpv.py:45	Exception	Pass 
connectors/wfs.py:92	Exception	Return ConnectionTestResult(f'WFS:{key}', False
copilote_v2/answering.py:1123	Exception	Return None
copilote_v2/answering.py:261	json.JSONDecodeError	Return None
copilote_v2/answering.py:280	ValueError	Pass 
copilote_v2/answering.py:357	(TypeError, ValueError)	Continue 
copilote_v2/historique.py:175	Exception	Return {'conversations': 0, 'messages': 0, 'oct
copilote_v2/outils.py:351	HTTPException	Return ToolResult('fiche_parcelle', ok=False, r
copilote_v2/outils.py:542	Exception	Return ToolResult('recherche_web', ok=False, re
copilote_v2/outils.py:557	Exception	Pass 
copilote_v2/outils.py:588	Exception	Return ToolResult('compter_piscines', ok=False,
copilote_v2/outils.py:610	Exception	Return ToolResult('compter_permis', ok=False, r
copilote_v2/outils.py:779	HTTPException	Return ToolResult('statut_ppr', ok=False, refus
copilote_v2/registre_faits.py:112	(TypeError, ValueError, KeyError)	Continue 
copilote_v2/resume_fiche.py:69	(TypeError, ValueError)	Return None
copilote_v2/resume_fiche.py:79	HTTPException	Return None
copilote_v2/router.py:204	json.JSONDecodeError	Return None
copilote_v2/router.py:218	(TypeError, ValueError)	Pass 
copilote_v2/router.py:224	ValidationError	Return None
copilote_v2/verifs.py:20	(TypeError, ValueError)	Return False
courrier_compose.py:105	Exception	Pass 
deploiement.py:32	Exception	Return None
deploiement.py:42	Exception	Return None
dvf_mediane.py:29	Exception	Return 8
etats_sources.py:164	Exception	Return []
etats_sources.py:184	Exception	Pass 
etats_sources.py:64	Exception	Return None
exports/blocs/apporteur.py:77	Exception	Return ''
exports/blocs/financier.py:89	(TypeError, ValueError)	Pass 
exports/builder.py:32	Exception	Return None
exports/builder.py:330	Exception	Return None
exports/builder.py:373	Exception	Return {'n': 0, 'membres': [], 'surface_totale_
exports/builder.py:410	Exception	Return None
exports/builder.py:430	Exception	Return None
exports/miroir.py:274	(TypeError, ValueError)	Pass 
exports/miroir.py:892	(KeyError, TypeError, ValueError)	Continue 
exports/robinet_fiche.py:776	Exception	Pass 
exports/robinet_fiche.py:799	Exception	Pass 
facturation.py:105	Exception	Return {'offre': cle, 'ok': False, 'detail': f'
facturation.py:334	ConfigError	Return False
facturation.py:363	ConfigError	Return False
faisabilite/au_differe.py:44	Exception	Return None
faisabilite/db.py:1009	Exception	Return (False, 'hors_rouge_invalide')
faisabilite/db.py:1022	Exception	Return (False, 'hors_rouge_invalide')
faisabilite/db.py:703	(ValueError, AttributeError)	Return None
faisabilite/db.py:944	Exception	Return None
faisabilite/hauteur_lidar.py:160	(AttributeError, IndexError)	Return None
faisabilite/hauteur_lidar.py:181	Exception	Pass 
faisabilite/hauteur_lidar_dalles.py:207	OSError	Pass 
faisabilite/hauteur_lidar_dalles.py:212	OSError	Pass 
faisabilite/profil_altimetrique.py:64	Exception	Pass 
faisabilite/residuel.py:357	Exception	Continue 
faisabilite/residuel.py:56	Exception	Pass 
faisabilite/zonage.py:480	(FileNotFoundError, ValueError)	Return {}
faisabilite/zonage.py:823	Exception	Return {}
filtres/__init__.py:84	Exception	Return set()
filtres/cadre.py:205	ValueError	Return None
filtres/echantillon.py:58	(TypeError, ValueError)	Return str(nous).strip().casefold() == str(atte
financier_questionnaire.py:377	(TypeError, ValueError)	Return None
fiscalite_libelle.py:21	(TypeError, ValueError)	Return None
flash/data.py:205	Exception	Pass 
flash/data.py:36	Exception	Return (500, 3)
flash/data.py:454	Exception	Return 5
flash/data.py:476	Exception	Pass 
flash/data.py:48	Exception	Return ''
flash/data.py:676	Exception	Pass 
flux.py:245	Exception	Return False
fraicheur_caches.py:159	Exception	Pass 
fraicheur_caches.py:183	Exception	Pass 
fraicheur_caches.py:204	Exception	Pass 
fraicheur_caches.py:254	Exception	Pass 
fraicheur_caches.py:295	Exception	Pass 
fraicheur_caches.py:373	Exception	Pass 
fraicheur_caches.py:72	Exception	Return 'sans-sources'
gabarit/validate.py:45	Exception	Return None
implantation/terrain.py:102	Exception	Return None
implantation/terrain.py:97	Exception	Return None
ingestion/annuaire_services.py:101	(ValueError, TypeError)	Return None
ingestion/annuaire_services.py:68	(ValueError, TypeError)	Return None
ingestion/annuaire_services.py:83	(ValueError, TypeError)	Return (None, None)
ingestion/arcep_fibre.py:142	(TypeError, ValueError)	Continue 
ingestion/bodacc.py:139	(UnicodeEncodeError, UnicodeDecodeError)	Return s
ingestion/bpe.py:108	ValueError	Continue 
ingestion/cadastre_bulk.py:48	(TypeError, ValueError)	Return None
ingestion/cadastre_historique.py:156	Exception	Continue 
ingestion/cartofriches.py:37	(ValueError, TypeError)	Return [v]
ingestion/catnat.py:53	ValueError	Pass 
ingestion/catnat.py:57	ValueError	Return None
ingestion/deal_carmen.py:182	ValueError	Return None
ingestion/division_or.py:585	Exception	Return [f'config illisible : {exc}']
ingestion/division_or.py:611	Exception	Return []
ingestion/division_or.py:63	Exception	Return {}
ingestion/division_or.py:671	Exception	Return {}
ingestion/dpe.py:51	(TypeError, ValueError)	Return None
ingestion/dpe.py:58	(TypeError, ValueError)	Return None
ingestion/dpe.py:65	(TypeError, ValueError)	Return None
ingestion/dvf_detail.py:48	ValueError	Return None
ingestion/dvf_detail.py:61	ValueError	Pass 
ingestion/fraicheur.py:289	Exception	Pass 
ingestion/garde_974.py:149	Exception	Pass 
ingestion/garde_974.py:92	(TypeError, ValueError)	Return None
ingestion/georisques_layers.py:41	(TypeError, ValueError)	Return None
ingestion/iris_rp.py:94	ValueError	Return None
ingestion/layers_ingest.py:293	Exception	Continue 
ingestion/mairies.py:56	(ValueError, TypeError)	Return None
ingestion/mairies.py:71	(ValueError, TypeError)	Return (None, None)
ingestion/oll_loyers.py:30	UnicodeDecodeError	Return io.StringIO(brut.decode('latin-1'))
ingestion/oll_loyers.py:81	ValueError	Return None
ingestion/ortho_tiles.py:145	httpx.HTTPError	Pass 
ingestion/ortho_tiles.py:86	httpx.HTTPError	Return None
ingestion/permit_delais_m10.py:89	ValueError	Return None
ingestion/permits.py:195	(TypeError, ValueError)	Pass 
ingestion/permits.py:202	(TypeError, ValueError)	Pass 
ingestion/permits.py:242	Exception	Continue 
ingestion/permits_sdes.py:282	Exception	Continue 
ingestion/personnes_morales.py:51	UnicodeDecodeError	Continue 
ingestion/pm_millesimes.py:98	UnicodeDecodeError	Continue 
ingestion/prospection_notion.py:85	(json.JSONDecodeError, OSError)	Return {}
ingestion/rei.py:66	ValueError	Return None
ingestion/reseaux_mt.py:77	json.JSONDecodeError	Continue 
ingestion/rnic.py:67	(TypeError, ValueError)	Return None
ingestion/sudocuh.py:72	(TypeError, ValueError)	Return None
ingestion/taxe_amenagement_delta.py:156	(TypeError, ValueError)	Continue 
ingestion/taxe_amenagement_delta.py:204	(TypeError, ValueError)	Continue 
ingestion/trafic_rn.py:47	(TypeError, ValueError)	Return None
ingestion/transport_reseaux.py:103	KeyError	Return []
ingestion/transport_reseaux.py:117	KeyError	Pass 
ingestion/transport_reseaux.py:130	(KeyError, ValueError)	Continue 
ingestion/transport_reseaux.py:132	KeyError	Return {}
ingestion/transport_reseaux.py:162	(KeyError, ValueError)	Continue 
ingestion/vegetation.py:178	httpx.HTTPError	Pass 
jobs.py:242	ValueError	Return False
jobs.py:87	(ValueError, OSError)	Return None
jobs_impl.py:678	Exception	Return 0.0
jobs_impl.py:838	Exception	Pass 
loyers.py:41	(OSError, ValueError)	Return {}
manifeste.py:92	Exception	Pass 
marche_service.py:175	Exception	Return {}
marche_service.py:191	(TypeError, ValueError)	Return 8
marche_service.py:201	(TypeError, ValueError)	Return defaut
marque.py:81	Exception	Return None
models.py:2250	Exception	Pass 
obsimmo.py:81	(OSError, ValueError)	Return []
occupation.py:35	(OSError, ValueError)	Return {}
ops_alertes.py:173	Exception	Return (False, f'injoignable : {type(exc).__nam
ops_alertes.py:192	OSError	Return []
ops_alertes.py:219	(OSError, ValueError, TypeError)	Return None
ops_alertes.py:289	Exception	Pass 
pige/api.py:1026	RuntimeError	Return {'ok': False, 'erreur': 'url_bloquee', '
pige/api.py:1031	html_next.NextDataError	Return {'ok': False, 'erreur': 'url_illisible',
pige/api.py:1039	html_next.NextDataError	Return {'ok': False, 'erreur': 'next_data', 'mo
pige/api.py:1055	ValueError	Return {'ok': False, 'motif': str(exc)}
pige/api.py:1071	ValueError	Return {'ok': False, 'motif': str(exc)}
pige/api.py:155	html_next.NextDataError	Return {'ok': False, 'erreur': 'next_data', 'mo
pige/api.py:157	html_ingest.DepotStockageError	Return {'ok': False, 'erreur': 'stockage', 'mot
pige/api.py:259	ValueError	Return {'ok': False, 'valide': False, 'motif': 
pige/api.py:58	Exception	Return {'statut': 'echec_extraction', 'motif': 
pige/api.py:583	Exception	Return out
pige/api.py:595	Exception	Pass 
pige/api.py:601	Exception	Pass 
pige/api.py:611	Exception	Pass 
pige/api.py:75	html_next.NextDataError	Return {'ok': False, 'erreur': 'next_data', 'mo
pige/api.py:78	html_ingest.DepotStockageError	Return {'ok': False, 'erreur': 'stockage', 'mot
pige/api.py:915	Exception	Return False
pige/coherence.py:34	Exception	Return None
pige/digests.py:280	Exception	Pass 
pige/extraction.py:64	json.JSONDecodeError	Return None
pige/html_next.py:65	ValueError	Return None
pige/intake.py:130	OSError	Return {'statut': 'echec_stockage', 'motif': f'
pige/intake.py:260	Exception	Pass 
pige/intake.py:281	(TypeError, ValueError)	Return None
pige/intake.py:320	Exception	Pass 
pige/rattachement_html.py:57	(TypeError, ValueError)	Return None
pige/signaux.py:106	Exception	Return {'eur_m2': None, 'n': 0, 'millesime': No
pige/signaux.py:116	Exception	Return {'eur_m2': None, 'n': 0, 'millesime': No
pige/signaux.py:143	Exception	Return {'eur_m2': None, 'n': 0, 'millesime': No
pige/tables.py:77	OSError	Return (False, f'{d} — inaccessible en écriture
pige/tables.py:92	OSError	Return (False, f'{d} — inaccessible en écriture
plh.py:18	Exception	Return None
plu/cli.py:24	Exception	Return None
plu/cli.py:44	Exception	Pass 
plu/extraction.py:203	Exception	Pass 
plu/extraction.py:219	Exception	Return ({}, ['JSON invalide'])
promo/collecte.py:104	Exception	Return (None, [], f'page illisible ({type(exc).
promo/collecte.py:167	json.JSONDecodeError	Return None
promo/collecte.py:92	Exception	Return (None, [], f'dépendance manquante ({exc}
promo/collecte.py:99	Exception	Return (None, [], f'page injoignable : {type(ex
proprietaire_historique.py:33	Exception	Return _MILLESIME_SERVI_REPLI
quota.py:50	Exception	Return None
radar.py:130	Exception	Return (None, f'{type(e).__name__}: {e}'[:180])
radar.py:52	(TypeError, ValueError)	Pass 
radar.py:57	ValueError	Pass 
registre/moteurs/commune.py:179	Exception	Return None
registre/moteurs/commune.py:204	Exception	Pass 
registre/moteurs/plateforme.py:23	Exception	Return None
registre/moteurs/plateforme.py:40	Exception	Return None
registre/remplissage.py:140	Exception	Continue 
reglages.py:47	Exception	Return None
rnu.py:106	Exception	Pass 
rnu.py:49	Exception	Return {}
run_progress.py:132	OSError	Pass 
run_progress.py:143	(OSError, ValueError)	Pass 
run_progress.py:37	OSError	Pass 
run_progress.py:56	(OSError, ValueError)	Return None
run_progress.py:70	OSError	Pass 
run_progress.py:79	(TypeError, ValueError)	Return False
run_progress.py:86	ProcessLookupError	Return False
run_progress.py:88	PermissionError	Return True
scoring/backtest.py:102	FileNotFoundError	Return None
scoring/score_v.py:60	ValueError	Return d.replace(year=d.year - years, day=28)
scoring/signal_mutation.py:30	(TypeError, ValueError)	Return None
sentinelle.py:113	(ValueError, IndexError)	Return None
sentinelle.py:132	ValueError	Return Sonde('illisible', message='réponse non-
sentinelle.py:150	re.error	Return Sonde('illisible', message=f'regex inval
sentinelle.py:199	ValueError	Return (None, Sonde('illisible', message='répon
sentinelle.py:276	Exception	Return Sonde('injoignable', message=f'{type(exc
solaire_toiture.py:218	Exception	Return None
sonde_circuit.py:242	Exception	Return {'ecarts_trouves': 0, 'mesures': 0, 'fam
sonde_circuit.py:252	Exception	Pass 
sonde_circuit.py:395	Exception	Return {'ecarts_trouves': 0, 'mesures': 0, 'err
sonde_circuit.py:473	Exception	Return {'erreur': f'recette injouable : {exc}'}
sonde_circuit.py:949	Exception	Pass 
sources_catalog.py:74	Exception	Return True
taxe_amenagement.py:131	Exception	Return None
taxe_amenagement.py:37	ValueError	Return d
taxe_amenagement.py:98	Exception	Return None
veille_plu.py:61	(ValueError, TypeError)	Return False
verdict_servi.py:154	(KeyError, TypeError)	Return None
verite_terrain.py:393	Exception	Continue 
verite_terrain.py:89	Exception	Pass 
verite_terrain_capacite.py:133	Exception	Return None
verite_terrain_capacite.py:241	(TypeError, ValueError)	Return 0.0
verite_terrain_capacite.py:248	(TypeError, ValueError)	Return 0
verite_terrain_capacite.py:449	(TypeError, ValueError)	Return None
verite_terrain_capacite.py:98	Exception	Continue 
verite_terrain_dpe_permis.py:113	Exception	Return None
verite_terrain_dpe_permis.py:238	Exception	Continue 
verite_terrain_dpe_permis.py:498	Exception	Return None
verite_terrain_dpe_permis.py:517	Exception	Return None
verite_terrain_plu_regles.py:57	Exception	Return None
verite_terrain_plu_regles.py:65	Exception	Return None
verite_terrain_plu_regles.py:94	Exception	Continue 
verite_terrain_plu_toutes.py:221	Exception	Return None
verite_terrain_plu_toutes.py:265	Exception	Return None
verite_terrain_sources.py:439	Exception	Continue 
verite_terrain_trajets.py:111	Exception	Return None
zone.py:102	Exception	Return {'statut': 'indisponible', 'geom_geojson
```

## Annexe E — TODO/FIXME bruts (src/labuse, 76 hits dont variables `todo`)

```
src/labuse/models.py:608:    (vue v_foncier_sous_pression). NE touche PAS au scoring (# TODO étage 2)."""
src/labuse/models.py:642:    au MOIS uniquement ('YYYY-MM', granularité diffusible RNE). NE touche PAS au score (# TODO étage 2)."""
src/labuse/models.py:673:    `pm_dirigeants` n'est PAS modifiée. RGPD : mêmes gardes (diffusibilité). # TODO étage 2."""
src/labuse/models.py:747:    « score d'aménités » est # TODO étage 1 (poids tranchés au calibrage). NE touche PAS au score."""
src/labuse/models.py:1659:    # TODO étage 2 : à brancher au scoring « accessibilité du deal » quand les 3 sources de
src/labuse/models.py:1694:    # TODO étage 2 : à brancher au scoring « accessibilité » quand les sources A seront là.
src/labuse/models.py:1771:    # TODO étage 2 : à brancher au score « propension à vendre » quand les sources seront prêtes.
src/labuse/cli.py:1003:        todo = [i for i in ids if i not in done]
src/labuse/cli.py:1005:                   f"{len(todo)} à évaluer à blanc.")
src/labuse/cli.py:1006:        if not todo:
src/labuse/cli.py:1010:        for k in range(0, len(todo), chunk):
src/labuse/cli.py:1011:            part = todo[k:k + chunk]
src/labuse/cli.py:1016:            typer.echo(f"  … {n}/{len(todo)} ({time.time() - t0:.0f}s)")
src/labuse/cli.py:1017:    typer.echo(f"✓ DRY-RUN [{label}] {nom} : {len(todo)} parcelles évaluées à blanc (tables dryrun_*).")
src/labuse/cli.py:1075:            todo = [i2 for i2 in ids if i2 not in done]
src/labuse/cli.py:1076:            for k in range(0, len(todo), 2000):
src/labuse/cli.py:1077:                evaluate_parcels(todo[k:k + 2000], s, persist=True, dryrun_label=label)
src/labuse/cli.py:1080:            typer.echo(f"  ✓ {nom} : {len(todo)} évaluées ({time.time() - t0:.0f}s)")
src/labuse/cli.py:1607:    (# TODO étage 2)."""
src/labuse/cli.py:1620:        todo = [x for x in sirens if x not in done]
src/labuse/cli.py:1623:                   f"{len(todo)} à traiter.")
src/labuse/cli.py:1624:        if not todo:
src/labuse/cli.py:1631:            for k in range(0, len(todo), chunk):
src/labuse/cli.py:1632:                part = todo[k:k + chunk]
src/labuse/cli.py:1637:                done_global = min(k + chunk, len(todo))
src/labuse/cli.py:1638:                typer.echo(f"  … {done_global}/{len(todo)} — +{res['dirigeants']} dirigeants "
src/labuse/cli.py:1641:            typer.echo(f"✗ QUOTA INPI ÉPUISÉ après {done_global}/{len(todo)} SIREN "
src/labuse/cli.py:1659:    anti-cycle. Identifiants en env INPI_API_*. Ne touche PAS au score (# TODO étage 2)."""
src/labuse/cli.py:2140:    (saute les communes déjà faites sauf --force). Ne touche PAS au score (# TODO étage 1)."""
src/labuse/cli.py:2236:    sauf --force). Ne touche PAS au score (# TODO étage 1/2)."""
src/labuse/cli.py:2332:    Une commune = une unité committée → résumable. Ne touche PAS au score (# TODO étage 1)."""
src/labuse/cli.py:2360:    PROMOTEUR (# TODO bilan), PAS le score. Idempotent (purge+réinsère)."""
src/labuse/cli.py:2377:    + distances par parcelle (parcel_amenites). Résumable. Signal calculé, poids # TODO étage 1."""
src/labuse/cli.py:2467:    île entière. FLAG QUALITÉ (# TODO étage 1), PAS exclusion étage 0. Remplace l'ancien GPU AC1."""
src/labuse/ingestion/seed_sources.py:170:         technical_notes="✓ live 05/07/2026 : /cavites (naturelle/carrière/ouvrage), lon-lat → Point. spatial_layers kind='cavite'. Vague B (# TODO étage 1)."),
src/labuse/ingestion/seed_sources.py:176:         technical_notes="✓ live 05/07/2026 : /mvt (coulée/glissement/éboulement, fiabilité), lon-lat → Point. spatial_layers kind='mvt'. Saint-Paul 160 objets. Vague C2 bonus (# TODO étage 1)."),
src/labuse/ingestion/seed_sources.py:182:         technical_notes="✓ live 05/07/2026 : /installations_classees (régime, statut Seveso, NAF), lon-lat → Point. spatial_layers kind='icpe'. Vague B (# TODO étage 1)."),
src/labuse/ingestion/seed_sources.py:365:         technical_notes="✓ live 05/07/2026 (schéma vérifié, record A200902491993). Filtre familleavis='collective' (BODACC A). Interrogé par SIREN (registre[]), batché registre IN(...). Vague A1 : flag foncier_sous_pression (# TODO étage 2). last_sync_at posé à l'ingestion."),
src/labuse/ingestion/seed_sources.py:371:         technical_notes="✓ login live 05/07/2026 (schéma vérifié, siren 913037362 SCI ALOE). Auth POST /api/sso/login (compte portail, identifiants en env INPI_API_*, JAMAIS en dur ; SFTP abandonné = firewall IP). GET /api/companies/{siren}. Champs : composition.pouvoirs[].individu.descriptionPersonne.dateDeNaissance (AAAA-MM). ⚠ pas de procédures collectives dans cet endpoint (restent BODACC A1). Vague A3 : signal propension_vendre / âge dirigeant (# TODO étage 2). last_sync_at posé à l'ingestion."),
src/labuse/ingestion/seed_sources.py:405:         technical_notes="✓ live 05/07/2026 : zip GeoJSON national, fichier ...Outre_Mer_WGS84, filtre insee_dep=974 → 57 QPV / 13 communes (MultiPolygon WGS84). spatial_layers kind='qpv'. Sert le BILAN PROMOTEUR (dispositifs/TVA en QPV), PAS le score (# TODO bilan). TVA 2,1% DOM = règle globale (pas un zonage). NPNRU absent open data. VEFA/ECLN = N/A DOM (métropole only)."),
src/labuse/ingestion/seed_sources.py:417:         technical_notes="✓ live 05/07/2026 (INSEE 97415) : host apidf-preprod.cerema.fr (apidf.cerema.fr ne résout pas), sans clé. /geofriches (GeoJSON MultiPolygon + unite_fonciere_refcad = IDU exacts), /friches/{id} (78 champs). Couverture 974 = 373 friches. spatial_layers kind='friche', rattachement EXACT via refcad. Vague C1 (# TODO étage 1/2). last_sync_at à l'ingestion."),
src/labuse/ingestion/bodacc.py:8:le branchera quand les 3 sources de la Vague A seront là (# TODO étage 2).
src/labuse/ingestion/bodacc.py:212:    url_source, source: "BODACC"}. # TODO étage 2 : consommé par le scoring « accessibilité ».
src/labuse/ingestion/amenites.py:8:en « score d'aménités » est # TODO étage 1 (poids au calibrage). NE touche PAS au score.
src/labuse/ingestion/inpi_rne.py:8:de la Vague A seront là (# TODO étage 2).
src/labuse/ingestion/vegetation.py:23:  OMNIDIRECTIONNELLE — TODO v1.1 : pondération directionnelle nord/est/ouest,
src/labuse/ingestion/score_v_fetch.py:71:    todo = [s for s in eligible_sirens(session)
src/labuse/ingestion/score_v_fetch.py:75:        todo = todo[:limit]
src/labuse/ingestion/score_v_fetch.py:76:    log(f"owner_enrichment : {len(todo)} SIREN à requêter (cache déjà chaud pour le reste)")
src/labuse/ingestion/score_v_fetch.py:78:    for i, siren in enumerate(todo, 1):
src/labuse/ingestion/score_v_fetch.py:95:            log(f"  … {i}/{len(todo)}")
src/labuse/ingestion/score_v_fetch.py:98:    return {"requetes": len(todo), "trouves": n_ok, "inconnus": n_miss}
src/labuse/ingestion/score_v_fetch.py:126:    todo: list[tuple[str, str]] = []
src/labuse/ingestion/score_v_fetch.py:133:        todo.append((denom, norm))
src/labuse/ingestion/score_v_fetch.py:135:        todo = todo[:limit]
src/labuse/ingestion/score_v_fetch.py:136:    log(f"owner_denom_lookup : {len(todo)} dénominations à requêter")
src/labuse/ingestion/score_v_fetch.py:138:    for i, (denom, norm) in enumerate(todo, 1):
src/labuse/ingestion/score_v_fetch.py:164:            log(f"  … {i}/{len(todo)}")
src/labuse/ingestion/abf_merimee.py:6:⚠ FLAG QUALITÉ (# TODO étage 1), PAS une exclusion étage 0. Le tampon 500 m SUR-COUVRE vs le
src/labuse/ingestion/abf_merimee.py:38:    Retourne des compteurs. ⚠ ÉCRIT + APPELS RÉSEAU. Ne touche PAS au score (# TODO étage 1)."""
src/labuse/ingestion/qpv.py:4:BILAN PROMOTEUR (dispositifs/abattements/TVA en QPV), PAS le score. # TODO bilan (non branché).
src/labuse/ingestion/qpv.py:40:    ⚠ ÉCRIT + APPEL RÉSEAU (un téléchargement). Ne touche PAS au score (# TODO bilan)."""
src/labuse/ingestion/georisques_layers.py:10:(# TODO étage 1 aux points d'accroche cascade). Ce module N'ALIMENTE PAS le score.
src/labuse/ingestion/georisques_layers.py:200:    commune AVANT réinsertion (rejouable sans doublon). Ne touche PAS au score (# TODO étage 1).
src/labuse/ingestion/cartofriches.py:8:(# TODO étage 1/2). Ce module N'ALIMENTE PAS le score.
src/labuse/scoring/declassement.py:20:# ── Seuils NON-francs (tunables). TODO étage 1 : migrer en YAML avec les flags de qualité. ──
src/labuse/scoring/declassement.py:50:    # TODO étage 1 : surface réduite mais > seuil franc (bande 100–250 m² sur un survivant).
src/labuse/scoring/declassement.py:55:    # TODO étage 1 : pente forte mais aménageable (bande 40–60 % sur un survivant).
src/labuse/scoring/declassement.py:60:    # TODO étage 1 : recouvrement partiel d'un équipement OSM (bande 30–50 % sur un survivant).
src/labuse/scoring/declassement.py:66:    # TODO étage 1 — Accès (audit O1) : signal présent UNIQUEMENT si la couche voirie est ingérée
src/labuse/scoring/declassement.py:76:    # TODO étage 1 — Correctif R1 « déjà bâti » : SEUL le cas NON-franc (partiellement bâti →
src/labuse/scoring/score_v_constants.py:130:    "BODACC_LJ":            ("A", 35, "Liquidation judiciaire en cours"),   # TODO v2 : non tranché Phase 0
src/labuse/scoring/score_v_constants.py:131:    "BODACC_LJ_CLOT":       ("A", 30, "Liquidation clôturée, parcelle toujours au nom"),  # TODO v2
src/labuse/scoring/score_v_constants.py:132:    "BODACC_RJ":            ("A", 30, "Redressement judiciaire en cours"),  # TODO v2
src/labuse/scoring/score_v_constants.py:134:    "BODACC_SAUVEGARDE":    ("A", 20, "Sauvegarde en cours"),               # TODO v2 (idem LJ/RJ)
src/labuse/api/servitudes.py:78:# audit-risques : ac3/el10/pm2 sortaient bruts (« SUP xxx ») → mappés ici. Sens confirmé sur la donnée
```
