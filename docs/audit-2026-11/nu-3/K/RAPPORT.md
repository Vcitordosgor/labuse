# AUDIT-NU-3 — Lot K : charge, sauvegardes, navigateurs, Radar

**Branche** `audit/nu-3-k` · **worktree** `~/Desktop/labuse-nu3-k` · **ports** API 9320 / front 6520
**Date** 2026-11-01 (soir) · **Opus** · LECTURE SEULE sur la prod (`ssh labuse-vps`), aucune écriture, aucun redémarrage, **aucune charge envoyée à la prod** (toute la charge est locale). Aucun correctif, aucun merge.

Barème de gravité identique à `docs/audit-2026-11/nu-1/` : **bloquant / majeur / mineur / dette**.
Chaque constat : gravité · reproduction · affiché contre juste · capture/preuve · `fichier:ligne` · proposition.

> **Méthode — environnement local.** API bootée depuis CE worktree (`src/`) avec l'interpréteur PDF-capable
> (`~/Desktop/labuse-main/.venv/bin/python`, weasyprint OK ; l'env conda `labusedb` ne l'importe pas — cf.
> `README_DEV.md`), base locale `labuse` (46 Go, alignée prod lecture seule), run servi `q_v20`.
> `git diff main -- src frontend/src` = **vide** : la branche d'audit ne modifie aucun code applicatif, le
> binaire testé est donc bien celui de `main`. **Matériel : MacBook 8 cœurs / 8 Go RAM**, qui fait AUSSI
> serveur du Radar — les chiffres de charge sont ceux de cette machine, pas du VPS (**VPS = 6 cœurs / 11 Go /
> 96 Go disque, load < 0,2 au repos** : plus de RAM que le Mac, donc pas le même plafond). À interpréter comme
> « l'app sous charge », pas « capacité de la prod ».

---

## Synthèse

| # | Gravité | Domaine | Constat |
|---|---------|---------|---------|
| K-SAV-01 | **BLOQUANT** | Sauvegardes | **Aucun dump produit depuis le 29/10** : `backup-postgres` échoue chaque jour (30/10, 31/10, 01/11). `pg_dump` verrouille toutes les tables d'un coup et bute sur `pige_restauration_radarfix3` (propriétaire `postgres`, `labuse` sans SELECT) → `permission denied` → dump avorté. |
| K-SAV-02 | majeur | Sauvegardes | La copie **hors-VPS** (`.copie-externe.json`) date du **19/10** (13 j). Le seul exemplaire récent est le dump VPS du 29/10 ; au-delà, rien. Rétention annoncée « 2 quotidiens + 1 hebdo » = **1 seul dump réel**. |
| K-SAV-03 | mineur | Sauvegardes | `restore_test.json` absent : **aucune restauration de contrôle** n'est jamais enregistrée. Le dump n'est vérifié que par `pg_restore --list` (lisible ≠ restaurable complet). |
| K-SAV-04 | (repère) | Sauvegardes | **Temps de reprise mesuré ≈ 13 min 20 s** (rapatriement 157 s + `pg_restore` 615 s + boot 21 s + 3 fiches 9 s) — MAIS la 1ʳᵉ restauration a **échoué faute d'espace** sur le Mac (~30 Go libres < 22 Go + base de travail 46 Go). |
| K-SAV-05 | majeur | Sauvegardes | Le dump du 29/10 est **amputé de 2 tables présentes en prod** (`pige_restauration_radarfix3`, `signal_instantanes`, créées après le 29) ; restaurer les perd entièrement. Sinon **279/302 tables identiques** (le reste = drift J-3 + reconstructibles exclus). |
| K-RAD-01 | **majeur** | Radar | Le Mac **dort** la nuit (`pmset sleep 1`, sur **batterie**, `womp 0`, aucune alarme `pmset` de réveil pour la passe). Pendant le sommeil système, le battement d'alarme de l'extension ne part pas → passe du soir **ratée en silence**. Observé : **0 passe le 31/10 et le 01/11** (prod `pige_passes` : dernière = 30/10 02:39). |
| K-RAD-02 | **majeur** | Radar | **Pas de garde-fou sur le verrou `running`.** Si le worker est tué EN PLEINE passe (sommeil, fermeture de Chrome, éviction MV3), le `finally` qui remet `running=false` ne s'exécute pas → `running=true` persiste → **toutes les passes AUTO suivantes sont bloquées** jusqu'à un « Capturer maintenant » manuel. `background.js:679/733/789`. |
| K-RAD-03 | majeur | Radar | `autoRunDate` est posé **avant** le run (`maybeRunTonight` l.790). Une erreur réseau transitoire en début de passe est bien gérée (badge ✗, notif, `running` relâché) **mais brûle la nuit** : la marque « déjà fait ce soir » reste → **aucune reprise auto** même si le réseau revient. Seul le manuel rattrape. |
| K-RAD-04 | mineur | Radar | Le **journal de la passe** ne vit que dans le service worker + `chrome.storage` (`lastResult`/`lastRun`) — **illisible hors navigateur**. Côté serveur, une nuit ratée n'apparaît que passivement (« Déposer Radar » dans À faire) ; pas d'alerte active. |
| K-CHG-01 | **majeur** | Charge | La garantie « fiche & carte < 1 s pendant les études » **tient à 10 users** (sonde fiche p95 0,23 s / carte 0,11 s) mais **casse à 25** (sonde fiche p95 **10,7 s**, carte **10,1 s**) — sur ce Mac 8 cœurs / 8 Go. Détails § Charge. |
| K-CHG-02 | majeur | Charge | **Le PDF dossier (weasyprint) est le goulot** : p50 9,5 s à 10 users → **26 s à 25** (p95 38 s). Aucune erreur (0 × 500/503/timeout), que de la latence. |
| K-CHG-03 | mineur | Charge | Jusqu'à **26 processus enfants** d'étude simultanés (≈ 1 par user) → sur 8 Go, **swap saturé (~8 Go)** à 25 users = le vrai plafond. Pas de fuite non bornée (le pic RSS 1,7 Go retombe à ~0,5 Go). |
| K-NAV-01 | (vert) | Navigateurs | **Aucun écart** fonctionnel ni visuel Chromium / Firefox / WebKit à 1440 & 1024 px : carte/fiche/PLU/Copilote/PDF ok partout, 0 erreur console/page, 0 overflow, fiche identique au pixel. Détails § Navigateurs. |

---

## 1. Sauvegardes du VPS

### Inventaire (lecture seule)

`/var/backups/labuse/` au 01/11 :

```
labuse-labuse-20261029-161844.dump          6,1 Go   29/10 16:37   ← SEUL dump
labuse-pige-captures-20261029-161844.tar.gz 1,4 Mo   29/10 16:37
.copie-externe.json                          199 o   19/10 16:34   ← marqueur copie externe (périmée)
incoming/                                    (vide)
purges-20261020/                             1,5 Mo
```

`du` : dump 6,1 Go. `df /` : 96 Go, 56 utilisés, **41 Go libres** (donc l'échec n'est PAS un manque d'espace).

**Rétention réelle vs annoncée.** Le script `deploy/scripts/backup_postgres.sh` annonce `KEEP=2` quotidiens
+ 1 hebdo (dimanche, hardlink). Dans les faits : **un seul dump** (29/10). Raison : voir K-SAV-01 — les
dumps des 30, 31/10 et 01/11 n'ont jamais été écrits (avortés), donc rien à tourner.

### K-SAV-01 — BLOQUANT — aucun dump depuis le 29/10 (job cassé 3 jours)

**Reproduction / preuve** (prod, lecture seule) :

```sql
select nom, statut, debut, duree_s from job_runs where nom='backup-postgres' order by debut desc limit 6;
 backup-postgres | echec | 2026-11-01 13:30:03 | 0.2   ← RuntimeError backup_postgres.sh (code 1)
 backup-postgres | echec | 2026-10-31 13:30:03 | 0.2
 backup-postgres | echec | 2026-10-30 13:30:03 | 0.2
 backup-postgres | ok    | 2026-10-29 13:30:04 | 1130  ← dernier dump réussi (~19 min)
 backup-postgres | ok    | 2026-10-28 13:30:04 | 1186
```

Journal PostgreSQL (`/var/log/postgresql/postgresql-18-main.log`, 01/11 09:30:03 UTC = 13:30 Réunion) :

```
ERROR:  permission denied for table pige_restauration_radarfix3
STATEMENT:  LOCK TABLE public.abuse_scores, …, public.pige_restauration_radarfix3, … IN ACCESS SHARE MODE
```

**Mécanisme.** `pg_dump` (lancé par le rôle `labuse`) pose **un seul `LOCK TABLE` sur TOUTES les tables**
au démarrage. Une seule table refusée fait échouer tout le dump :

```sql
select tableowner from pg_tables where tablename='pige_restauration_radarfix3';        → postgres
select has_table_privilege('labuse','pige_restauration_radarfix3','SELECT');            → f (false)
```

La table `pige_restauration_radarfix3` (posée par un correctif Radar) appartient à `postgres`, et le rôle de
dump `labuse` n'a **aucun droit** dessus. C'est **exactement** le mode d'échec déjà vu le 07→12/10 pour un
*schéma* (`sauvegarde_*`), que le script a corrigé avec `--exclude-schema=sauvegarde_*`
(`backup_postgres.sh:45-49`). Mais l'exclusion ne couvre **pas** une table *du schéma `public`*.

**Affiché contre juste.** Le cockpit/vigie montre le job en échec (bien), MAIS le dossier `/var/backups/labuse`
garde un `.dump` du 29/10 qui *paraît* récent ; sans regarder `job_runs`, on croit la sauvegarde vivante.
**Juste** : il n'y a plus de point de reprise frais depuis 3 jours.

**`fichier:ligne`** : `deploy/scripts/backup_postgres.sh:76` (le `pg_dump` sans `--exclude-table` pour cette
table ni fallback par-table) ; cause racine = droits manquants sur `public.pige_restauration_radarfix3`.

**Proposition** (hors mandat d'exécution) : soit `GRANT SELECT ON pige_restauration_radarfix3 TO labuse;`
(et auditer toute table `public` non lisible par `labuse`), soit ajouter `--exclude-table=pige_restauration_radarfix3`
si la table est jetable, soit dumper en `postgres`. Mieux : une garde qui **échoue bruyamment ET escalade**
(le job alerte déjà, mais 3 jours sans dump auraient dû remonter d'un cran).

### K-SAV-02 — majeur — copie hors-VPS périmée (19/10)

`.copie-externe.json` : `{"copie_at":"2026-10-19T12:33:03Z","dump":"labuse-labuse-20261019-133004.dump",
"taille_mo":6921.3,"disque":"MUSIQUE-VIDEO"}`. Le commentaire du script (`:19-22`) assume que
« l'historique vit AILLEURS (le Mac rapatrie chaque matin + disque externe) » — or ce marqueur n'a pas bougé
depuis **le 19/10**. Donc la défense « le VPS ne garde qu'une courte fenêtre, le long terme est externe »
**ne tient pas** : l'externe est à J-13 et le VPS à J-3. En cas de perte VPS aujourd'hui, le point de reprise
le plus récent **où qu'il soit** est le 29/10.

### K-SAV-03 — mineur — aucune restauration de contrôle enregistrée

`lire_restore_test()` (`ops_alertes.py:269`) lit un `restore_test.json` qui **n'existe pas** dans
`/var/backups/labuse`. La seule vérification d'un dump est `pg_restore --list` (`backup_postgres.sh:81`) —
elle prouve que l'archive est *lisible*, pas qu'elle *restaure une base fonctionnelle*. Le présent lot comble
ce trou **manuellement** (§ ci-dessous) ; rien ne le fait en routine.

### K-SAV-04 — Temps de reprise mesuré (rapatriement → restauration → service)

Drill réel sur le Mac (base **à part `labuse_restore`**, supprimée à la fin) à partir du dump du 29/10 :

| étape | durée |
|---|---|
| rapatriement du dump (6,55 Go @ ~41 Mo/s, rsync/ssh) | **157 s** |
| `createdb labuse_restore` | 0 s |
| `pg_restore -j 3 --clean --if-exists` (→ **22 Go** restaurés) | **615 s** |
| boot API sur la base restaurée → `/healthz` 200 | **20,7 s** |
| ouverture de **3 fiches** (froides : 4,5 + 2,1 + 2,2 s) | **~9 s** |
| **TOTAL technique** | **≈ 802 s ≈ 13 min 20 s** |

Les 3 fiches reviennent **200 avec du contenu réel** (Sainte-Suzanne 35 m², Saint-André 791 m², Saint-Paul
732 m² ; 78 champs chacune) → **la base restaurée sert l'app correctement**. `pg_restore` **rc=0** (restauration
complète, index reconstruits).

> **Ce que « 13 min » ne dit PAS** (le vrai délai de remise en service est plus long) :
> 1. Il **suppose** un poste avec **PostgreSQL + PostGIS + l'app déjà installés** et un dump **déjà identifié**.
>    Sur une machine nue, ajouter l'installation (postgres-18, postgis, pango pour les PDF, le dépôt, le venv).
> 2. Il **suppose ~22 Go libres** : la **1ʳᵉ tentative a ÉCHOUÉ** sur ce Mac — garde-disque déclenché à 2 Go
>    libres (le Mac n'avait que ~30 Go libres, le lean restaure à 22 Go **à côté** des 46 Go de la base de
>    travail). Il a fallu **libérer de l'espace** pour que la 2ᵉ passe aboutisse. **La machine de secours n'a
>    pas confortablement la place.**
> 3. Surtout : on restaure le **29/10** (K-SAV-01). Une reprise réelle **aujourd'hui perdrait 3 jours** de
>    données (comptes, projets, CRM, veilles, captures Radar depuis le 29/10).

### K-SAV-05 — majeur — le dump du 29/10 est AMPUTÉ de 2 tables présentes en prod

Comparaison des comptes **toutes tables** (304 prod vs 302 restaurées, méthode `n_live_tup` après `ANALYZE`) :

- **279/302 tables communes identiques** (ou < 2 %). Les écarts restants sont du **drift normal J-3** (prod plus
  récente) : `job_runs` +1 460, `pige_annonces/biens/faits` +131/122/122 (captures 29-30/10), `parcel_residuel_runs`
  **restore > prod** de 185 k (prod a **purgé** depuis), `event_log`/`usage_events`/`mvt_tile_cache`… — rien
  d'anormal.
- **Reconstructibles** (data exclue du dump lean, schéma gardé) : `cascade_results` 9,2 M → 0, `dryrun_cascade_results`
  42,3 M → 0, `p_model_candidates` 4,3 M → 0, `p_model_ext_dataset` 4,3 M → 0, `score_snapshot_parcelles` 3,0 M → 0.
  **Attendu et documenté** (rebâti par ingestion/scoring au besoin) — mais à savoir : une reprise ne redonne PAS
  ces tables telles quelles, il faut les recalculer.
- **2 tables EN PROD mais ABSENTES du dump** : `public.pige_restauration_radarfix3` et `public.signal_instantanes`.
  La 1ʳᵉ est justement celle qui casse les backups (K-SAV-01) : créée **après le 29/10** et appartenant à
  `postgres` → ni dans le dump du 29, ni dans aucun dump depuis. `signal_instantanes` idem (créée après le 29).
  **Conséquence** : restaurer depuis le dernier dump disponible **perd entièrement ces 2 tables** (schéma + data).

---

## 2. Charge locale (10 puis 25 users, 10 min)

**Parcours par user** (bouclé avec think-time 0,3–0,7 s) sur les endpoints réels :
`GET /parcels/{idu}?source=q_v20` (fiche) · `GET /map/parcels.geojson?limit=2000&commune=…` (carte) ·
`GET /radar/annonce/estimation/{idu}?surface_hab=90` (**Estimer un bien** = clé `analyser-annonce`) ·
`POST /modules/etude` (**Étude de faisabilité**, calcul en **processus enfant tuable**, borne 60 s) ·
`GET /parcels/{idu}/export.pdf` → redirige vers `/dossier/{idu}.pdf` (**PDF weasyprint**).
Une **sonde indépendante** (hors des users) tape fiche+carte toutes les 3 s pour mesurer la latence *perçue*
pendant que les études tournent. Harnais : `~/labuse-restore-k/charge.py` (stdlib, threads).

### 10 users / 10 min — 1 845 requêtes, **0 erreur**

| étape | n | p50 | p95 | max | codes |
|---|---|---|---|---|---|
| fiche | 371 | **0,022 s** | **0,141 s** | 1,94 s | 200×371 |
| carte | 371 | **0,021 s** | **0,155 s** | 0,38 s | 200×371 |
| estimer | 371 | 0,045 s | 0,224 s | 0,45 s | 200×371 |
| étude | 370 | 4,46 s | 8,69 s | 10,97 s | 200×370 |
| pdf | 362 | **9,53 s** | **11,15 s** | 12,64 s | 200×362 |

**Sonde pendant les études** : fiche p95 **0,23 s**, carte p95 **0,11 s** → **< 1 s largement tenu** (K-CHG-01). ✅
**Mémoire** : RSS (parent+enfants) 242 → **max 1 139 Mo** → 512 Mo en fin ; après retour au repos, **406 Mo**.
**Processus enfants** : jusqu'à **11** simultanés. `vm_free` min 1 187 Mo (pas d'épuisement).

### 25 users / 10 min — 1 729 requêtes, **0 erreur**

| étape | n | p50 | p95 | max | codes |
|---|---|---|---|---|---|
| fiche | 350 | 0,494 s | **11,76 s** | 14,69 s | 200×350 |
| carte | 350 | 0,128 s | 1,22 s | 14,05 s | 200×350 |
| estimer | 350 | 0,227 s | 1,67 s | 14,18 s | 200×350 |
| étude | 350 | 9,37 s | 17,78 s | 24,45 s | 200×350 |
| pdf | 329 | **26,0 s** | **38,4 s** | 41,5 s | 200×329 |

**Sonde pendant les études** : fiche p95 **10,73 s**, carte p95 **10,11 s** → **la garantie < 1 s N'EST PLUS
TENUE** à 25 users (K-CHG-01 : OK à 10, cassé à 25).
**Mémoire** : RSS max **1 713 Mo**, retour à **469 Mo** en fin, **611 Mo** au repos 25 s après.
**Processus enfants** : jusqu'à **26** simultanés (≈ 1 processus d'étude par user actif).
**Swap** : la machine 8 Go **sature et pagine fort** (≈ 8,2 Go de swap utilisés pendant le run) — c'est le vrai
plafond ici. Malgré ça, **aucune requête n'échoue** (ni 500, ni 503, ni timeout) : la dégradation est en
latence, pas en erreurs. L'étude reste **sous sa borne 60 s** (max 24 s) donc **jamais de 503**.

### Fuite mémoire

| moment | RSS arbre API |
|---|---|
| boot à froid | 71 Mo |
| après 10u, au repos | 406 Mo |
| pic 25u | 1 713 Mo |
| après 25u, au repos | 611 Mo |

La mémoire **redescend du pic** après chaque charge (1 713 → ~500-600 Mo) → **pas de fuite non bornée**.
Le palier de repos monte avec l'intensité (71 → 406 → 611 Mo) : c'est cohérent avec des **caches chauds**
(`fiche_cache`, médianes DVF, caches de tuiles) qui se remplissent et ne sont pas purgés — à surveiller sur
un process longue-durée, mais ce n'est pas une fuite au sens strict (pas de croissance monotone sous charge
constante ; le pic retombe).

### Lecture

- **Fiche & carte sont excellentes** (p95 ~150 ms) et le restent sous charge, y compris pendant les études —
  réponse directe à la question du mandat. Le premier accès à une fiche *froide* coûte ~1 s (cache `fiche_cache`),
  d'où le `max` à 1,9 s ; une fois chaude, 20 ms.
- **Le PDF dossier (weasyprint) est le point lourd** (K-CHG-02) : ~9,5 s à 10 users. C'est du CPU pur dans le
  threadpool ; à 25 users il faut regarder s'il sature (voir tableau 25u).
- **L'étude** spawn un processus enfant par appel (ETUDE-ASYNC-1) : bon pour l'isolation (tuable à 60 s), mais
  **N études simultanées = N processus** — sur 8 Go c'est le facteur limitant mémoire (K-CHG-03).

---

## 3. Navigateurs — Firefox / WebKit / Chromium (1440 px & 1024 px)

> **Note matériel/outil.** Le poste est en **macOS 13.0.1 / arm64**, sous le plancher de support de Playwright
> récent (1.62 refuse d'installer : « does not support chromium on mac13-arm64 »). Les moteurs ont donc été
> pilotés avec **Playwright 1.49.1** (Chromium 131 / Firefox 133 / WebKit 18.2), qui installe et tourne ici.
> Flux réel par moteur × résolution : accueil carte → **recherche IDU → clic suggestion → fiche** → outil
> **PLU** → **Copilote** (question) → **PDF** dossier ; plus console/erreurs page/réseau + overflow horizontal.
> Harnais : `~/labuse-restore-k/browser2.mjs`, captures `browser2/*.png`.

**Matrice (poste au repos, run propre)** — 3 moteurs × 2 largeurs :

| config | carte | fiche | PLU | Copilote | PDF | console err | page err | réseau ≥400 | overflow |
|---|---|---|---|---|---|---|---|---|---|
| chromium 1440 | ok | ok | ok | ok | ok (pdf) | 0 | 0 | 0 | 0 |
| chromium 1024 | ok | ok | ok | ok | ok | 0/1* | 0 | 429 copilote* | 0 |
| firefox 1440 | ok | ok | ok | ok | ok | 0 | 0 | 429 copilote* | 0 |
| firefox 1024 | ok | ok | ok | ok | ok | 0 | 0 | 429 copilote* | 0 |
| webkit 1440 | ok | ok | ok | ok | ok | 0/1* | 0 | 429 copilote* | 0 |
| webkit 1024 | ok | ok | ok | ok | ok | 0/1* | 0 | 429 copilote* | 0 |

\* Le seul non-200 est un **HTTP 429 sur `/api/copilote-v2/ask`** — c'est le **quota IA** (`ia_ask_quota`) qui
se déclenche parce que l'audit a posé 6 fois la même question en 2 min ; il apparaît **de façon identique
sur les 3 moteurs**, ce n'est pas un écart navigateur (la console error associée n'est que l'écho du 429).

**Verdict : AUCUN écart fonctionnel ni visuel entre Chromium, Firefox et WebKit, à 1440 px comme à 1024 px.**
- Parité **visuelle** vérifiée sur captures : le panneau gauche (« Cartes ») et le **panneau fiche à droite**
  (en-tête parcelle, « Demander à LABUSE / Poser une question », identité, Terrain, Bâti, « Le droit du sol »,
  Urbanisme, Risques, Réseaux) sont **identiques au pixel près** entre Chromium et WebKit. La seule différence
  d'image est la **position de caméra de la carte au moment du screenshot** (fly-to vers la parcelle : Chromium
  capturé île entière, WebKit capturé zoomé) — artefact de timing, pas de rendu ; MapLibre GL rend correctement
  sur les trois.
- **0 overflow horizontal** partout (pas de casse de mise en page propre à un moteur), à 1440 comme à 1024.
- Le PDF (`/parcels/{idu}/export.pdf`) renvoie **`application/pdf`** sur les trois moteurs.

**Limites honnêtes.** (1) Le harnais n'enchaîne pas proprement l'ouverture de plusieurs outils d'affilée
(ré-ouvrir « Outils » après un 1ᵉʳ outil ouvert) → « Estimer » et « Pièges et risques » ressortent « FAIL » dans
la matrice, **à l'identique sur les 3 moteurs** ; j'ai vérifié **à la main (MCP)** qu'ils s'ouvrent bien
(`#m=analyser-annonce` et le menu Outils rendent leur panneau) — ce n'est donc **pas** un écart navigateur mais
une limite de mon script. (2) Un 1ᵉʳ passage joué **pendant la restauration** (machine saturée) a fait échouer
`fiche`/`PLU` sur `webkit_1440` par **timeout de clic 6 s** (aucune erreur réseau) ; **rejoué au repos → ok** —
flake de contention, conservé dans `browser2_contended/` comme preuve.

---

## 4. Le Mac comme serveur du Radar

**Montage.** Extension Chrome MV3 (`outils/radar-extension/`) sur le Mac, qui **nourrit la prod**
(`labuseUrl` par défaut `https://app.labuse.immo`, `background.js:79`). Les passes du soir atterrissent donc
dans `pige_passes` **de la prod**. Fenêtre du soir : **21:00 → minuit, heure de LA RÉUNION** (ancrée horloge
murale Réunion quelle que soit l'horloge OS, `fenetreSoir()` `:764`). Battement d'alarme toutes les **5 min**
(`HEARTBEAT_MIN`, `:758`) qui, dans la fenêtre et si « pas déjà fait ce soir », déclenche **une** capture auto.

### État observé

```sql
-- prod, lecture seule
select nom='…', max(created_at) from pige_passes;   → dernière passe 2026-10-30 02:39
select count(*) from pige_passes where created_at::date >= '2026-10-31';  → 0
```
→ **0 passe les nuits du 31/10 et du 01/11.** Captures locales (`/Users/openclaw/labuse-pige/captures`) :
dernier fichier **26/10 21:37**. Chrome **tourne** en ce moment (process `--extension-process` présent).

> **Note — les crons serveur du Radar vont bien.** `radar-cycle`, `radar-cycle-dvf`, `radar-cycle-mensuel`
> tournent et réussissent sur le VPS (01/11 04:00-05:30). Ce qui est mort, c'est **l'INGESTION depuis
> l'extension du Mac** : le pipeline serveur traite… de moins en moins de nouvelles annonces.

### Preuve forensique — l'état réel de l'extension (lu dans `chrome.storage`)

`~/Library/Application Support/Google/Chrome/Default/Local Extension Settings/nghdglghmbgjiokidffphmpkodnhgnpg/000003.log`
(dernière écriture **31/10 21:00 CET = 01/11 00:00 Réunion**). Valeurs, dans l'ordre d'écriture (offset octet) :

```
…1268  lastResult = "OK 20:17 (manuel, rattrapage) …"   ← dernier SUCCÈS = MANUEL
 1417  running     = false                               ← finally du run manuel : OK
 1534  autoRunDate = "2026-10-29"                         ← dernier AUTO marqué : 29/10
 1579  running     = true                                 ← DERNIER état de running : TRUE, jamais remis à false
 1612  todayTargetDate = "2026-10-30"
 1695  todayTargetDate = "2026-10-31"
 1778  todayTargetDate = "2026-11-01"                      ← heartbeat VIVANT (nouvelle cible chaque jour)
```

**Lecture.** Le dernier run AUTO (29/10) a posé `autoRunDate=29/10` (l.790) puis `running=true` (l.679)… et **le
`finally` n'a jamais tourné** (pas de `running=false` après) : le worker est mort **en pleine passe** (sommeil /
fermeture / éviction MV3). Depuis, le battement réveille bien le worker chaque soir — il écrit la nouvelle
`todayTargetDate` (30/10, 31/10, 01/11, l.781) — **mais se heurte à `if (opts.running) return` (l.789)** car
`running` est resté `true`. `autoRunDate` est donc **gelé au 29/10** et **aucune passe auto ne repartira**
tant qu'un « Capturer maintenant » manuel ne relâchera pas le verrou. **C'est K-RAD-02, observé EN DIRECT**,
déclenché par K-RAD-01 (le run tué était un run interrompu par le sommeil). Le seul succès récent est **manuel**.

> **Confirmation live ce soir (01/11).** Le Mac est resté **éveillé toute la soirée** (activité de l'audit) et
> Chrome tournait, donc K-RAD-01 (sommeil) ne s'appliquait PAS ce soir — pourtant, à 23:56 Réunion (fenêtre
> quasi close), **toujours aucune passe** (`max(pige_passes.created_at)` = 30/10 02:39). Le blocage tient donc
> bien au **verrou `running` figé** (K-RAD-02), pas (ce soir) au sommeil : la preuve que le garde-fou manque.

### K-RAD-01 — majeur — le Mac dort pendant la fenêtre → passe ratée en silence

**Preuve** (`pmset`) :

```
sleep                1 (1 min d'inactivité)      womp 0 (pas de wake-on-LAN)
Now drawing from 'Battery Power'  33%; discharging
pmset -g log : 2026-11-01 00:30:30  Entering Sleep state … Using Batt (Charge:70%)
               (cycles Sleep ↔ DarkWake 5-7 s toutes les ~16 min toute la nuit)
pmset -g sched : AUCUN réveil programmé pour la fenêtre du soir (seuls des wakes calendrier/acmd)
```

Pendant un **Sleep** système, les alarmes `chrome.alarms` **ne se déclenchent pas** ; les DarkWake de
maintenance (5-7 s) n'exécutent pas les timers de l'extension. La fenêtre 21:00-00:00 Réunion
(= 18:00-21:00 CET) tombe en pleine inactivité → sommeil → **le battement ne part jamais**. Après minuit
Réunion, le code **s'abstient volontairement** (`maybeRunTonight` `:787` `if (now > fin) return`) et **il n'y a
aucun rattrapage le lendemain matin**. Résultat = la nuit est perdue, sans trace active. C'est la cause la plus
probable des 0 passes du 31/10 et du 01/11 (le Mac est un portable sur batterie, pas un serveur éveillé).

**Proposition** : `caffeinate` persistant la nuit OU `pmset repeat wake` pour réveiller le Mac avant la fenêtre
OU brancher sur secteur avec `sleep 0` ; et surtout une **alerte serveur** si aucune passe n'est arrivée dans
les 26 h (le serveur sait que le Radar est muet, il ne le dit pas).

### K-RAD-02 — majeur — verrou `running` sans garde-fou (blocage indéfini)

`runEvening` pose `running=true` (`:679`) et ne le remet à `false` que dans un `finally` (`:733`).
`maybeRunTonight` refuse tout nouveau run auto tant que `running` est vrai (`:789`). **Si le worker meurt en
pleine passe** — sommeil du Mac, fermeture de Chrome, éviction du service worker MV3 (les passes durent
**10-30 min** : `NAV_MIN=4 s`, `CONF_MIN=8 s` entre pages, jusqu'à 40 pages + Bien'ici) — **le `finally` ne
s'exécute pas**, `running=true` reste en `chrome.storage`, et **aucune passe auto ne repartira** jusqu'à un
« Capturer maintenant » manuel (seul chemin qui, via son propre `finally`, relâche le verrou). Aucun
`onStartup`/watchdog ne réinitialise un `running` périmé (vérifié : `running` n'apparaît qu'aux lignes 90/679/733/789).

**Proposition** : estampiller `running` avec un timestamp et le considérer périmé après ~45 min (reset au
chargement du worker), ou poser le verrou via `chrome.alarms` à durée bornée.

### K-RAD-03 — majeur — une coupure réseau transitoire brûle la nuit

`maybeRunTonight` pose `autoRunDate = today` **AVANT** d'appeler `runEvening` (`:790`). Une coupure réseau en
début de passe est proprement gérée (`catch` l.721 : badge ✗, notif « Radar arrêté », `lastResult` lisible,
`running` relâché) — **mais** la marque « déjà capturé ce soir » est déjà posée, donc **aucune reprise
automatique** même si le réseau revient 10 min plus tard. La nuit est perdue sur un simple hoquet. Seul un
clic manuel rattrape. (À l'inverse, c'est volontaire pour éviter le matraquage ; le défaut est l'absence de
**retries bornés** dans la fenêtre.)

### K-RAD-04 — mineur — le journal de la passe est prisonnier du navigateur

Il n'existe pas de « journal de la passe » lisible hors Chrome : l'extension écrit `lastResult`/`lastRun` dans
`chrome.storage.local` et logge dans la console du service worker — invisible en CLI/ops. Côté serveur, la seule
trace d'une passe est une ligne `pige_passes` (quand elle réussit) ; une nuit **ratée** ne laisse **rien**
d'actif, juste l'item passif « Déposer Radar » dans À faire. Pour « les journaux de la passe de cette nuit » :
au moment de l'audit (≈ 23 h Réunion, encore dans la fenêtre), **aucune passe n'a eu lieu** ; dernière trace
serveur = 30/10 02:39.

---

## Annexes

- Harnais de charge : `~/labuse-restore-k/charge.py` ; résultats `charge_10u.json`, `charge_25u.json`.
- Matrice navigateurs : `~/labuse-restore-k/browser.mjs` ; `browser/*.json` + captures `browser/*.png`.
- Comptes prod (stats, sans scan) : `~/labuse-restore-k/prod_counts.txt` (304 tables).
- Dump rapatrié : `~/labuse-restore-k/labuse-labuse-20261029-161844.dump` (supprimé en fin de lot avec `labuse_restore`).
