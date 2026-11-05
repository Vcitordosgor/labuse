# NU4-E — Banc de charge (50 clients) + relecture des 7 nuits de prod

**Branche** `audit/nu4-e` · worktree `~/Desktop/labuse-nu4e` · ports 9670 (API) / 6870 (front).
**Posture** : LECTURE SEULE sur le code, aucune correction. Les essais de charge tournent sur la
**version LOCALE** (base Mac `labuse`, run servi `q_v20`) — **jamais la prod**. La relecture des
journaux de prod est en **lecture seule** (ssh `labuse-vps`, `journalctl`/`psql SELECT`).

Date : 2026-11-05. Modèle : Opus. Commit : voir `git log` de la branche.

---

## 0. Résumé exécutif

Deux mandats : (A) tenir 50 clients simultanés 30 min et mesurer, en nominal puis pendant une
injection et un calcul de nuit ; (B) relire 7 nuits de journaux de prod.

**Ce qui tient.** Le trafic DOMINANT (tuiles MVT, recherche, fiche TIÈDE servie par le cache)
reste rapide jusqu'à ~16 requêtes réellement simultanées. La vue `v_parcel_dvf_last` **n'est PAS**
lente par le chemin applicatif (≈ 50 ms, pas les 50 s qu'on lit en SQL `psql` littéral — artefact de
plan, cf. §4). L'API prod est stable (`NRestarts=0`, `/readyz` vert sur les 7 nuits). Les
sauvegardes sont saines (6,5 Go, copie hors-VPS + test de restauration verts).

**Points de rupture trouvés (détail §3 et §6).**
- **R1 — Les workers meurent sous charge pendant la génération PDF** (weasyprint/Cairo/Pango) :
  **13 morts / 18 démarrages sur 30 min** (et 2–4 par fenêtre `real` de 10 min, 22 cumulées),
  **sans trace Python** (crash natif ou tuerie mémoire OS). Prod-pertinent (mêmes libs). → GRAVE.
- **R2 — Épuisement du pool de connexions** : `QueuePool size 5 + overflow 10` par worker ; sous
  forte concurrence (skew d'un worker, ou endpoints lents qui tiennent la connexion), le pool se
  vide et la requête **échoue en 500 après 30 s d'attente**. → GRAVE.
- **R3 — Endpoints « modèle » synchrones qui tiennent une transaction DB ouverte pendant tout
  l'appel Anthropic** (`/ask` Copilote 11–17 s, `/explain` 16–27 s). Sous charge, accumulation de
  connexions *idle in transaction* (jusqu'à 43) et transactions de 50–135 s → pression sur
  `max_connections` (100) et risque d'`idle_in_transaction_session_timeout` (ce qui a tué
  `calcul-nuit` en prod, cf. §6). → MAJEUR.
- **R4 — `calcul-nuit` en prod ne termine JAMAIS un passage complet** (timeout 4 h le 11-03,
  puis abandon « fin de fenêtre 5 h » les 11-04/05, `promu:false`) ; l'incident « jamais réussi »
  reste ouvert. → MAJEUR.
- **R5 — 4 nuits de sauvegarde en échec (10-30→11-02)** sur verrou `pg_dump` (récupéré, aucune
  perte) ; **5 nuits `coherence-banc` en échec** (fichier manquant, corrigé le 11-02). → MOYEN.
- **R6 — DDL par le chemin de heal prend un ACCESS EXCLUSIVE sur des tables chaudes**
  (`ALTER TABLE sirene_etablissements ADD COLUMN IF NOT EXISTS …`) → convoi de verrous qui gèle
  les lectures. **Local uniquement** (prod pose `LABUSE_SKIP_BOOT_HEAL=1` + heal pré-service), mais
  révèle une fragilité si le heal venait à tourner pendant le trafic. → MOYEN (local) / à surveiller.
- **R7 — Radar « passe de confirmation SUSPECTE » 3 nuits de suite, escaladant 32 %→43 %→100 % de
  retraits** ; disque prod à 94,6 % le 11-05 00:15 (redescendu à 82 %). → MOYEN.

---

## 1. Mandat & méthode

### Mandat
50 clients simulés qui naviguent, ouvrent des fiches, lancent outils et PDF, parlent au Copilote,
30 min ; mesurer latences, erreurs, mémoire, connexions DB, verrous. Refaire pendant une injection
(chemin sûr INJECTION-SOLIDE) et pendant un calcul de nuit. Vérifier en particulier la vue des
dernières ventes DVF (dépassement de délai sous 8 requêtes // vu en NU4-C). Puis relire 7 nuits de
journaux de prod.

### Environnement de test (local)
- Mac **8 cœurs / 8 Go** (prod : 6 vCores / 12 Go — plus de RAM, moins de cœurs).
- API : `uvicorn labuse.api.app:app --workers 5` (identique à prod), auth **désactivée** (local).
- PostgreSQL local : `max_connections=100`, `shared_buffers=2GB`, `work_mem=4MB`,
  `statement_timeout=0` au niveau serveur.
- Pool SQLAlchemy par worker : `pool_size=5`, `max_overflow=10` ⇒ **15 connexions/worker**, soit
  **75 max** côté API. `statement_timeout` **API** = 60 s (posé par requête, `after_begin`).
- Base servie : `q_v20`, 434 582 parcelles, `dvf_mutations_parcelle` = 102 551 lignes / 20 Mo.

### Harnais (livré, rejouable — `docs/audit-2026-11/nu-4/E/scripts/`)
- `load.py` — N clients `httpx.AsyncClient` indépendants (keep-alive « navigateur »), boucle
  d'actions pondérées + think-time 0,5–3 s. Deux mix : `stress` (défaut, sur-pondère `/explain`)
  et `real` (`LOAD_MIX=real` : pas de `/explain` — le front ne l'appelle plus depuis M54-EXPO-2 ;
  Copilote rare). Journalise action/endpoint/status/latence par requête (CSV).
- `sample_server.py` — toutes les 2 s : RSS workers, connexions app, actives, *idle in tx*,
  lock-waits, transaction la plus longue, verrous non accordés.
- `dvf_bench.py` — concurrence croissante (1/4/8/16/32) de fiches FROIDES (hors cache) pour
  reproduire le symptôme DVF de NU4-C.
- `inject_safe.py` — rejoue le CHEMIN SÛR (`injection_sure.injecter_table_sure` : staging +
  contrôle de delta + verrou consultatif + swap atomique DELETE+INSERT sans ACCESS EXCLUSIVE) sur
  `dvf_mutations_parcelle` (lue par la vue DVF), réinjection à l'identique (delta 0 %, réversible).
- `analyze.py` — synthèse latences/erreurs/débit + pics serveur.

Mix d'actions `stress` : navigate 50 / search 10 / fiche 25 / explain 5 / tool 8 / copilote 2.
Mix `real` : navigate 55 / search 12 / fiche 25 / tool 7 / copilote 1.
« tool » = `gabarit.pdf` | `export.pdf` (→ redirige vers `dossier/{idu}.pdf`, weasyprint) |
`POST evaluate`. Appels modèle réels (clé Anthropic présente) pour `/ask` et `/explain`.

---

## 2. Mesures de charge — tableaux

> Latences en **ms** sauf mention. p50/p95/p99/max. « ok% » = 2xx/204.

### 2.1 Référence — 50 clients / 30 min (mix `stress`)
19 139 requêtes · fenêtre 1856 s · débit **10,3 req/s** · **80,0 % de 2xx**.
Non-2xx/erreurs (449) : 94× **500** (pool), **199× RemoteProtocolError + 29× ReadError**
(connexion coupée quand un worker meurt en cours de réponse → R1), 3× ReadTimeout, 80× 422, 44× 404.

| action | n | ok% | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| navigate (tuiles) | 13 873 | 100 | 294 | 2 143 | 5 170 | 30 942 |
| fiche | 3 208 | 94 | 3 381 | 41 771 | 85 073 | 120 037 |
| search | 896 | 96 | 2 194 | 24 425 | 32 512 | 43 551 |
| tool (pdf/evaluate) | 699 | 80 | 12 597 | 78 408 | 100 935 | 120 364 |
| explain | 439 | 91 | 22 705 | 43 671 | 52 095 | 69 265 |
| copilote | 24 | 96 | 20 244 | 40 359 | 42 844 | 42 844 |

**Lecture.** Même le trafic léger (tuiles) part en tails de 30 s, et la fiche atteint p99 **85 s**
(max 120 s = plafond client). Cause : les **13 morts de worker / 18 démarrages** (R1) coupent les
requêtes en vol et, en local, chaque relance relance le heal (R6) → convois de verrous. Serveur :
pic **59 connexions app**, **43 actives**, **43 idle-in-tx**, **42 lock-waits**, transaction la plus
longue **99 s**, 42 verrous non accordés. **388** `QueuePool…timeout 30.00` dans `api.log`. Ce mix
`stress` sur-pondère `/explain` (endpoint sans entrée front) : la §2.2 donne l'image LIVE.

### 2.2 Réaliste — 50 clients (mix `real`, 10 min) — contrôle
9 087 requêtes · 612 s · débit **14,8 req/s** · **98,6 % de 2xx**.
Non-2xx (131) : 42× 500, 32× RemoteProtocolError, 20× ReadError, 1 ReadTimeout, 28× 422, 8× 404.

| action | n | ok% | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| navigate (tuiles) | 6 879 | 100 | 314 | 2 250 | 4 949 | 32 475 |
| fiche | 1 411 | 97 | 1 581 | 30 504 | 53 039 | 68 779 |
| search | 514 | 98 | 2 096 | 13 927 | 31 106 | 34 642 |
| tool (pdf/evaluate) | 275 | 81 | 19 323 | 69 895 | 104 221 | 120 804 |
| copilote | 8 | 62 | 35 610 | 84 296 | 84 296 | 84 296 |

**Lecture.** Sans `/explain`, le taux de 2xx remonte à **98,6 %** (vs 80 % en `stress`) et le débit
à 14,8 req/s — l'occupation des workers par les appels modèle était bien un facteur majeur. **Mais
les ruptures persistent** : **4 morts de worker + 164 pool-500 en 10 min**, PDF (`tool`) p50 **19 s**
/ max 120 s, fiche p99 **53 s**, Copilote **62 % ok**. Serveur : pic conns **52**, actives **42**,
idle-in-tx **28**, lock-waits **25**, tx la plus longue **99,6 s**, **RSS workers pic 743 Mo**
(≈ 124 Mo/worker moyen, pics PDF plus hauts). R1/R2 ne sont donc PAS un artefact du mix `stress`.

### 2.3 Réaliste + injection SÛRE concurrente (10 min)
Charge mix `real` + `inject_safe.py` rejouant le swap sûr de `dvf_mutations_parcelle` en continu.
9 867 requêtes · 614 s · débit **16,1 req/s** · **99,0 % de 2xx**. **33 injections sûres, 0 refusée**
(swap min 5,5 s / médian 13,6 s / max 22,3 s sous charge — vs 1,7 s à vide ; rows préservées
102 551). **2 morts de worker, 0 pool-500.**

| action | n | ok% | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| navigate (tuiles) | 7 310 | 100 | 384 | 1 958 | 4 245 | 7 342 |
| fiche | 1 675 | 99 | 512 | 19 359 | 48 612 | 67 837 |
| search | 556 | 99 | 1 656 | 4 701 | 15 947 | 27 622 |
| tool (pdf/evaluate) | 318 | 79 | 18 925 | 116 867 | 120 852 | 121 673 |
| copilote | 8 | 100 | 27 044 | 63 919 | 63 919 | 63 919 |

**Lecture — l'injection sûre tient.** L'injection concurrente **ne dégrade PAS** les lectures
clients : ok% **99,0 %** (≥ contrôle), lock-waits pic **35** (vs 25 au contrôle, pas d'explosion),
pas de 500 pool. Le swap `DELETE+INSERT` en une transaction prend un **ROW EXCLUSIVE** (compatible
ACCESS SHARE des lecteurs) et le MVCC sert l'ancienne version jusqu'au COMMIT → **aucun blocage de
lecture** (la garantie revendiquée par INJECTION-SOLIDE est vérifiée sous 50 clients). Coûts
observés : connexion dédiée tenue 5–22 s par swap (conns pic **61**, idle-in-tx **38**,
RSS **879 Mo**), et **bloat de table** (20 Mo → 82 Mo après 33 swaps, nettoyé par autovacuum).
⚠ **Effet de bord révélé** : pendant cette fenêtre un worker relancé a lancé le heal de boot, dont
l'étape `pige` a échoué en **`LockNotAvailable` (lock timeout)** sous contention → `/readyz` est
resté **503 en permanence** alors que les endpoints servaient normalement (tuile/fiche 200 en
~50 ms). Mode d'échec AUTONOMIE-2 (heal sous trafic) ; prod l'évite via heal pré-service +
`LABUSE_SKIP_BOOT_HEAL=1`. Cf. R6.

### 2.4 Réaliste + calcul de nuit (`flux-run`) concurrent (10 min)
Charge mix `real` + `flux-run --label nu4e_calc1 --recette m36` (cascade+scoring sous label
candidat, NON promu — comme `calcul-nuit`). Pendant la fenêtre, flux-run a reconstruit le cache
`spatial_layers_sub` (**1 548 768 pièces**) puis entamait la cascade (arrêté proprement — reprenable).
12 094 requêtes · 611 s · débit **19,8 req/s** · **98,8 % de 2xx** · **3 morts de worker, 0 pool-500.**

| action | n | ok% | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| navigate (tuiles) | 9 067 | 100 | 317 | 1 549 | 3 526 | 7 010 |
| fiche | 1 985 | 99 | 400 | 12 626 | 27 585 | 55 913 |
| search | 678 | 99 | 1 732 | 5 578 | 8 999 | 16 152 |
| tool (pdf/evaluate) | 356 | 71 | 24 345 | 61 077 | 71 516 | 85 172 |
| copilote | 8 | 100 | 29 203 | 49 435 | 49 435 | 49 435 |

**Lecture.** Le calcul de nuit concurrent **ne fait pas s'effondrer** le service de lecture : ok%
**98,8 %**, fiche p50 **400 ms**, pas de 500 pool, conns pic **56**. Le coût est **CPU** (la cascade
et le rebuild `spatial_layers_sub` disputent le CPU aux requêtes spatiales de la fiche) et touche
surtout les PDF (`tool` 71 % ok, p50 24 s). ⚠ **Limite** : cette fenêtre de 10 min couvre la phase
de PRÉPARATION (rebuild du cache) et le DÉBUT de cascade, **pas** les heures de cascade par commune
où la prod accumule l'*idle-in-transaction* qui a tué `calcul-nuit` (R4). À rejouer plus longtemps
pour toucher ce régime.

### 2.5 État serveur (échantillonneur) par scénario — pics observés

| scénario | 2xx% | débit | morts worker | pool-500 | conns | actives | idle-in-tx | lock-waits | tx max (s) | RSS workers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stress 30 min | 80,0 | 10,3 | 13 | 388 | 59 | 43 | 43 | 42 | 99 | — |
| real contrôle | 98,6 | 14,8 | 4 | 164 | 52 | 42 | 28 | 25 | 99,6 | **743 Mo** |
| real + injection | 99,0 | 16,1 | 2 | 0 | 61 | 48 | 38 | 35 | 99,0 | **879 Mo** |
| real + calcul nuit | 98,8 | 19,8 | 3 | 0 | 56 | 42 | 25 | 35 | 99,7 | n/d* |

`*` échantillonneur RSS non fiable sur cette fenêtre (n'a capté que le parent). Rappels :
`max_connections=100` (serveur), **75** connexions API théoriques (5 workers × 15). Les « tx max
99 s » sont le plafond d'observation lié au cycle de vie des requêtes lentes (fiche/PDF/modèle)
tenant une transaction. **22 morts de worker cumulées** sur ~70 min de charge (toutes corrélées PDF).
Les pool-500 (388) se concentrent sur le mix `stress` (occupation par `/explain`) ; les mix `real`
en ont peu voire zéro, mais les **morts de worker persistent dans tous les scénarios**.

---

## 3. Points de rupture (détail mécaniste)

### R1 — Morts de workers pendant la génération PDF (GRAVE)
Sur la référence 30 min : **13 morts de worker / 18 démarrages** ; et **4 (contrôle) / 2 (injection)
/ 3 (calcul)** sur les fenêtres `real` de 10 min — soit **22 morts cumulées** sur ~70 min de charge,
dans TOUS les scénarios (`Child process [pid] died`, uvicorn relance). Les morts ont systématiquement
une activité **weasyprint**
(PDF `dossier`/`gabarit`) dans les ~20 lignes précédentes (marqueurs : `Creating PDF`,
`fontTools.varLib.instancer`, récupération de tuiles ortho `data.geopf.fr` embarquées). **Aucune
trace Python** n'accompagne ces morts (les 78 `Traceback` du log sont les 500 du pool, cf. R2) : le
process meurt au niveau **natif** (Cairo/Pango/HarfBuzz/fontTools sous rendu concurrent) ou est
**tué par la pression mémoire de l'OS** (un PDF avec plusieurs tuiles ortho embarquées est un pic
RAM). Les handlers PDF sont **synchrones** → plusieurs rendus weasyprint tournent en parallèle sur
les threads du même worker. Prod-pertinent (mêmes libs, mêmes 5 workers). Conséquence : les requêtes
en vol sur ce worker sont coupées, et (local) le redémarrage déclenche R6.

### R2 — Épuisement du pool de connexions → 500 (GRAVE)
Sous forte concurrence, on observe des 500 avec :
`sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out,
timeout 30.00`. Le pool est **par worker** (15 connexions). Deux déclencheurs :
1. **Skew de distribution** : en keep-alive, les connexions TCP se « collent » à un worker ; au
   micro-banc conc=32 en keep-alive partagé, **3× 500 à ~34 s** (30 s d'attente pool + calcul) ;
   la même charge SANS keep-alive (réparti sur les 5 workers) passe à **0 erreur, p50 0,24 s**
   (cf. §4). Donc un worker peut saturer ses 15 slots pendant que les autres chôment.
2. **Endpoints lents qui tiennent la connexion** (R3) : chaque fiche/outil/Copilote garde 1
   connexion pour toute sa durée ; quelques appels lents suffisent à vider les 15 slots d'un worker.
Résultat : **500 dur** (pas une lenteur) après 30 s. En prod (derrière Caddy) la distribution
diffère mais le plafond de 15/worker et les handlers synchrones restent la fragilité structurelle.

### R3 — Endpoints « modèle » tiennent une transaction ouverte (MAJEUR)
`/parcels/{idu}/ask` (Copilote) et `/parcels/{idu}/explain` sont des handlers **synchrones** qui
font `fiche = _build_fiche(db, …)` **puis** l'appel Anthropic (`explain_parcel` / cœur IA) **sans
fermer la session** : la connexion DB reste *idle in transaction* pendant tout l'appel modèle
(11–27 s mesurés). Sous charge : jusqu'à **43 connexions *idle in transaction*** simultanées et des
transactions de **50–135 s** (échantillonneur). Deux dangers : (a) pression sur `max_connections`
(100) — on a vu **56 connexions app** sous 50 clients seuls ; un calcul de nuit concurrent ajoute
les siennes ; (b) sur prod, `idle_in_transaction_session_timeout` (120 s, cf. OPS-NUIT-1) **tue**
ces connexions → 500. C'est exactement le mode d'échec qui a abattu `calcul-nuit` (§6, R4).
Note : `/explain` n'a **plus de point d'entrée front** (M54-EXPO-2) — risque surtout latent ; le
risque LIVE est `/ask`.

### Fiche FROIDE vs TIÈDE (cache)
La fiche premium passe par un cache 2 niveaux (`_FICHE_CACHE` L1 par worker + `fiche_cache` L2 en
base). Une fiche **tiède** (déjà en cache) ≈ 1,2 s. Une fiche **froide** seule ≈ 1,3 s, mais sous
50 clients elle **gonfle à 5–13 s** (contention CPU/connexions + les dizaines de requêtes spatiales
qu'un `_q_v2_fiche` enchaîne : `ST_Intersection(geom_2975)`, toiture/solaire, trafic RN, ANC,
fibre…). **La clé de cache inclut l'empreinte du run servi** (`_fiche_db_cle`) : **toute promotion
d'un nouveau run (calcul de nuit) invalide tout le cache** → le lendemain matin, les premières
ouvertures sont toutes froides. C'est le pire moment pour 50 clients simultanés.

---

## 4. La vue des dernières ventes DVF (`v_parcel_dvf_last`) — mise au point

NU4-C notait « 5 fiches 500-timeout transitoire sous 8 requêtes // » attribué au
`statement_timeout` de `v_parcel_dvf_last`. **Mise au point mesurée :**

- La requête par parcelle en **`psql` avec littéral** (`WHERE idu='…'`) prend **≈ 50 s** : le
  planificateur ne pousse pas le prédicat dans les deux agrégats pleine-table de la vue
  (`mutation_tot`, `bati_mutation`, chacun Seq-Scan des 102 k lignes) et les HashAggregate
  **débordent sur disque** (`work_mem=4MB`).
- La **MÊME requête par le chemin applicatif** (psycopg paramétré `$1`, via le moteur de l'app) :
  **≈ 46 ms**, puis **< 2 ms** à chaud. Pas de bascule plan générique (testé 12 exécutions
  d'affilée sur une connexion). Le plan paramétré pousse l'égalité par l'index `ix_dvfp_parcelle`.
- Avec `work_mem=256MB`, même la version littérale tombe à **171 ms**. Le « 50 s » est donc un
  **artefact de plan `psql` + work_mem**, **pas** le coût réel vu par l'application.

**Micro-banc fiche froide (chemin client réel), concurrence croissante :**

| conc | n | ok | 500 | p50 s | p95 s | p99 s | max s | rps |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1  | 48 | 47 | 0 | 0.61 | 0.88 | 1.09 | 1.09 | 1.6 |
| 4  | 48 | 47 | 0 | 0.68 | 1.19 | 1.46 | 1.46 | 5.3 |
| 8  | 48 | 48 | 0 | 1.17 | 1.96 | 2.14 | 2.14 | 6.3 |
| 16 | 48 | 48 | 0 | 2.28 | 2.90 | 4.45 | 4.45 | 6.6 |
| 32 | 48 | 44 | **3** | 4.62 | **34.2** | 34.2 | 34.2 | 1.4 |
| 32 (sans keep-alive) | 48 | 47 | **0** | 0.24 | 1.89 | — | 2.30 | 20.8 |

**Conclusion DVF** : à 8 requêtes // sur la base q_v20 actuelle, **0 timeout** (p50 1,17 s). Les 3×
500 à conc=32 sont de l'**épuisement de pool par skew keep-alive** (R2), pas la SQL DVF. Le symptôme
NU4-C relevait très probablement du **pool/skew** (même famille de harnais httpx) et non d'une vue
intrinsèquement à 50 s en prod. La vraie dette DVF reste la conception **full-scan par parcelle**
(la vue recalcule deux agrégats pleine-table), aujourd'hui masquée par le plan paramétré ; elle se
dégradera si `dvf_mutations_parcelle` grossit ou si `work_mem` est serré.

---

## 5. Injection sûre & calcul de nuit sous charge — synthèse

**Injection sûre (§2.3)** — bonne nouvelle. La primitive `injecter_table_sure` (staging + contrôle
de delta + verrou consultatif + swap atomique `DELETE+INSERT` **sans ACCESS EXCLUSIVE**) a été
rejouée en continu sur `dvf_mutations_parcelle` (table lue par la vue DVF) pendant 50 clients.
**Aucun blocage de lecture** : 99,0 % de 2xx, lock-waits à peine au-dessus du contrôle (35 vs 25),
0 pool-500 ; le MVCC sert l'ancienne version entière jusqu'au COMMIT. La garantie de conception est
donc **vérifiée sous charge**. Coûts : une connexion tenue 5–22 s par swap (vs 1,7 s à vide),
RSS 879 Mo, et **bloat de table** (20→82 Mo après 33 swaps) rattrapé par autovacuum. L'effet de
bord `/readyz` 503 (heal `pige` en lock-timeout sur un worker relancé) est un artefact LOCAL de
config (prod : heal pré-service + `SKIP_BOOT_HEAL`), relaté en R6.

**Calcul de nuit (§2.4)** — tolérable sur la fenêtre testée, mais test partiel. `flux-run` (le même
calcul que `calcul-nuit`) tournant en concurrence n'a pas effondré le service (98,8 % de 2xx, fiche
p50 400 ms). Le coût dominant est **CPU** (cascade + rebuild du cache `spatial_layers_sub` de 1,5 M
pièces vs requêtes spatiales de la fiche), pénalisant surtout les PDF. **MAIS** la fenêtre de 10 min
ne couvre que la préparation + le début de cascade — pas les heures de cascade par commune où la
prod accumule l'*idle-in-transaction* et a dépassé sa fenêtre (R4). Le vrai risque prod « charge
pendant calcul de nuit » est donc **la compétition pour `max_connections`** (le calcul ajoute ses
connexions longues aux 75 de l'API) **et le CPU sur des heures**, pas une collision de verrous.

**Rappel couplage cache↔calcul** : promouvoir un nouveau run **invalide tout `fiche_cache`** (clé =
empreinte du run servi). Le matin suivant un calcul de nuit, toutes les fiches repartent FROIDES —
c'est précisément là que 50 clients simultanés paient le plus cher (R2/R3 + §3 fiche froide).

---

## 6. Relecture des 7 nuits de prod (2026-10-29 → 2026-11-05)

Source de vérité : table `job_runs` + `event_log` + `/var/backups/labuse` + `pige_annonces`
(cron en heure Réunion UTC+4 ; `job_runs` en UTC). Commandes reproductibles dans
`raw/prod-logs-7nights.md`. **Aucune écriture.** `labuse.service` (Uvicorn) `NRestarts=0`,
`/readyz` vert tout le long.

| Nuit (local) | injection 01:00 | calcul-nuit 02:00 | john 03:00 | coherence 03:45 | radar 04:00 | backup 13:30 | resume 07:30 |
|---|---|---|---|---|---|---|---|
| 10-29 | –* | –* | – | **ÉCHEC** | ok | ok | – |
| 10-30 | –* | –* | – | **ÉCHEC** | ok | **ÉCHEC** | – |
| 10-31 | –* | –* | – | **ÉCHEC** | ok | **ÉCHEC** | – |
| 11-01 | –* | –* | – | **ÉCHEC** | ok | **ÉCHEC** | – |
| 11-02 | –* | –* | – | ÉCHEC→ok (manuel) | ok | **ÉCHEC**→ok (manuel) | – |
| 11-03 | ok | **ÉCHEC (14341 s timeout)** | – | ok 836 s | ok | ok | – |
| 11-04 | ok | ok* (partiel, `promu:false`) | ok | ok 921 s | ok | ok | ok |
| 11-05 | ok | ok* (partiel, `promu:false`) | ok | ok 574 s | ok | ok | ok **[URGENT]** |

`*` Pas de ligne `job_runs` avant le 11-03 pour injection/calcul/john/resume (registre régénéré le
11-02 au passage q_v21) ; `event_log` les marquait « jamais réussi » jusque-là.

**R4 — calcul-nuit ne termine jamais.** 11-03 : 14341 s (~4 h) puis `SousProcessTimeout` →
`psycopg.errors.IdleInTransactionSessionTimeout` (7 communes faites avant la coupure). 11-04/05 :
« ok » mais **partiels** — `{"label":"q_v21","promu":false,"abandon":"fin de fenêtre 5 h atteinte
avant la fin du calcul — reprise la nuit prochaine"}`. **q_v21 jamais promu** (gate
`LABUSE_CALCUL_NUIT_PROMEUT=0`). L'incident « Job jamais réussi : calcul-nuit » (11-03 23:00,
11-04 00:00 « toujours ouvert ») **n'a pas de ligne résolu**. C'est le même mode d'échec
*idle-in-transaction* que R3 reproduit sous charge.

**R5a — backups.** 4 nuits en échec (10-30→11-02) : `pg_dump` ne prend pas le verrou `ACCESS SHARE`
(surface_d_events, mvt_parcels, parcel_flags, fiche_cache, tuyau_subdivise…) ; le 11-02
`FATAL: terminating connection due to administrator command` pendant `COPY tuyau_subdivise`. La
**garde anti-rétrécissement a fonctionné** (dump partiel supprimé, rien de corrompu gardé). Récupéré
en manuel le 11-02 16:33. Dumps sains ≈ **6,5 Go** (GARDE-… 6,56 Go le 11-02/03 ; 6,54/6,53 Go
11-04/05), **copie hors-VPS** (TOSHIBA, 11-04 20:41Z, sha256) et **test de restauration** vert
(11-05 01:00Z, « 1814 objets TOC »).

**R5b — coherence-banc.** 5 nuits en échec (10-29→11-02) : `FileNotFoundError …/COHERENCE-1/ECHANT…`
(fichier d'échantillon disparu après un déploiement), escaladé « non résolu depuis 5 j » (11-02
18:45). Corrigé le 11-02 ; vert depuis (574–921 s). ⚠ `coherence-banc` (03:45) chevauche
`calcul-nuit` (02:00) qui tourne > 4 h — à surveiller.

**R7 — radar & disque.** `radar-cycle` tourne chaque nuit (ok). **« Passe de confirmation SUSPECTE »
3 nuits de suite, escaladant 32 % (11-02) → 43 % (11-03) → 100 % de retraits (11-04)** —
signal qualité à trier (pas un crash). Comptages pige/nuit/portail présents (Bien'ici/Leboncoin)
avec des **trous** les 10-31/11-01/11-05. **Disque à 94,6 %** (seuil 85 %) le 11-05 00:15, redescendu
à **82 %** ; `/var/backups/labuse` = **25 Go** (4 × 6,5 Go) — rétention proche du plafond.

**Veille / sondes.** Tourne chaque nuit. Récidivistes : **3 sources Overpass/OSM `injoignable`**
chaque passe (miroirs kumi/private.coffee hors-ligne, non bloquant) ; **BODACC `illisible`**
(réponse non-JSON) ; SIS/OCS GE/SCOT étaient illisibles 10-31→11-04 puis **rétablis le 11-05**.

**John.** `john-veille` enregistré le 11-05 (00:19 + 03:00), 2 runs ok 14–15 s, `n_items:0`, aucun
plafond atteint. Double run bénin (manuel post-déploiement + planifié). `resume-matin` 11-05 =
**[URGENT]** « Résumé du matin — à regarder ».

**Redémarrages / santé.** `labuse.service` NRestarts=0, pas de flap. Pics `/readyz` 120 s alignés
sur les backups 13:30 et les fenêtres de déploiement (attendus, auto-résolus).

---

## 7. Findings classés par gravité

| # | Gravité | Finding | Preuve |
|---|---|---|---|
| R1 | **GRAVE** | Workers meurent sous charge pendant la génération PDF (weasyprint), sans trace Python | 22 morts cumulées (13 sur 30 min), 100 % corrélées weasyprint ; `api.log` |
| R2 | **GRAVE** | Épuisement pool (15/worker) → 500 après 30 s sous skew/endpoints lents | `QueuePool … timeout 30.00` ; micro-banc conc=32 |
| R3 | **MAJEUR** | `/ask` & `/explain` synchrones tiennent une transaction DB pendant l'appel modèle (11–27 s) → idle-in-tx ≤43, tx 50–135 s | échantillonneur `pg_stat_activity` |
| R4 | **MAJEUR** | Prod : `calcul-nuit` ne finit jamais (timeout/abandon 5 h, `promu:false`), incident ouvert | `job_runs`/`event_log` |
| R5 | **MOYEN** | Prod : 4 nuits backup + 5 nuits coherence-banc en échec (récupérés) | `job_runs` |
| R6 | **MOYEN** (local) | DDL `ADD COLUMN IF NOT EXISTS` (heal) = ACCESS EXCLUSIVE sur table chaude → convoi de verrous | blocking tree `pg_locks` |
| R7 | **MOYEN** | Prod : radar 100 % retraits 3 nuits ; disque 94,6 % ; rétention backups 25 Go | `event_log` ; `df`/`du` |
| — | INFO | DVF `v_parcel_dvf_last` : rapide par l'app (46 ms) ; full-scan/parcelle = dette latente | §4 |

### Recommandations (hors mandat — aucune correction appliquée)
- R1 : rendre la génération PDF hors-process/sérialisée (worker dédié, file), ou limiter la
  concurrence PDF/worker ; surveiller la RAM par worker (prod ~700 Mo plafond).
- R2 : augmenter `pool_size`/`max_overflow`, et/ou passer les endpoints lents en `async` pour ne
  pas tenir une connexion pendant un I/O réseau ; borner `pool_timeout`.
- R3 : fermer la session DB **avant** l'appel modèle (libérer la connexion), ou rendre ces routes
  `async` + client Anthropic async ; aligner un `idle_in_transaction_session_timeout` conscient.
- R4 : budget/temps `calcul-nuit` ou parallélisation par commune ; fermer proprement l'incident.
- R6 : sortir tout `ALTER`/DDL des chemins servis (déjà le cas en prod via heal pré-service).

---

## 8. Limites & honnêteté
- Base LOCALE `q_v20` (= la base de NU4-C) ; prod non sollicitée pour la charge. `work_mem=4MB`
  local peut différer de prod (sensibilité DVF, §4).
- Mac 8 Go < prod 12 Go : la pression mémoire (R1) peut être **plus** sévère en local — à rejouer
  sur un banc iso-prod avant de trancher « crash natif » vs « tuerie mémoire OS ».
- Pas de Caddy en frontal local : le skew keep-alive (R2) se comporte différemment derrière un
  reverse-proxy ; le plafond de pool (15/worker) reste néanmoins réel.
- Appels modèle réels (clé Anthropic) : `/ask` et `/explain` ont consommé des tokens pendant le
  banc (plafond local 5 €).
- INJECTION-SOLIDE-2 n'est **pas mergé** sur cette branche ; on a exercé la primitive sûre MERGÉE
  `injecter_table_sure` (même doctrine), seule disponible ici.
- **Journal serveur** : `api.log` a été roté au redémarrage propre mi-audit (avant la fenêtre
  calcul), donc le `api.log` conservé ne couvre que la fenêtre + calcul de nuit. Les compteurs
  serveur par scénario (morts de worker, pool-500, convoi ACCESS EXCLUSIVE, idle-in-tx) ont été
  relevés **en direct** pendant chaque run et sont reportés ici et dans `raw/api_evidence.txt` ;
  les **CSV clients** (`raw/*_load.csv`, `raw/*_sample.csv`) sont complets pour les 4 runs.
- Les 3 fenêtres `real` durent 10 min (le régime permanent se stabilise en 2–3 min) ; seule la
  référence `stress` dure 30 min. Artefacts locaux laissés en base : run candidat `nu4e_calc1`
  (NON promu) + cache `spatial_layers_sub` reconstruit (le run servi reste `q_v20`).
