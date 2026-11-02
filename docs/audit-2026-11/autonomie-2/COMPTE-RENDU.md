# AUTONOMIE-2 — lever les derniers bloqueurs de l'autonomie

Branche `fix/autonomie-2` · worktree `~/Desktop/labuse-autonomie2` · Opus · **prod en lecture seule**
(aucun merge, aucun push). À lire d'abord : `reports/DEPLOY-AUTONOMIE.md`.

> **Bilan en une ligne.** Le lecteur « tuile » du banc est réaligné sur le MVT servi (décodeur
> protobuf **en Python pur**, sans node) → `erreurs_lecteur` **1198 → 0** ; le heal de schéma ne
> tourne **plus pendant le service** (joué **avant le port, en série**, par `ExecStartPre`) →
> `/readyz` **stable sur 3 redémarrages sous charge** ; les 6 verrous sont **diagnostiqués un à un
> contre la prod réelle** (lecture seule) — **3 corrigés dans le code** (V1c, V4a, G5), **3 sont des
> signaux d'exploitation/donnée** (V3b DPE, V6b golden, G8 sonde) avec leur remédiation prod écrite,
> G8 étant **déjà non bloquant au déploiement** (`-w G8`, CRON-1 lot 3).

---

## 1 — Lecteur « tuile » du banc de cohérence (réaligné sur le MVT servi)

**Cause.** Depuis la vague `couches_tuyau` (servie au DEPLOY-FINAL du matin), `/map/tiles/z/x/y.pbf`
sert du **protobuf MVT**. Le lecteur `tuile:` du banc (`scripts/coherence/lib.py:tuile_props`)
décodait la tuile en **sous-processus node** (`decode_tile.mjs` → `@mapbox/vector-tile`, via les
`node_modules` du front). En prod — et sur tout poste sans le front installé — node renvoyait un corps
**vide** → `json.loads('')` → « Expecting value: line 1 column 1 » sur **chaque** parcelle →
**1198 `erreurs_lecteur`**, ce qui bloque le contrôle de cohérence (il exige `erreurs_lecteur = 0`),
donc la promotion automatique du calcul de nuit. *Reproduit localement à l'identique* (le worktree n'a
pas `@mapbox/vector-tile`).

**Correction (sans toucher à la carte).** Décodage MVT **en Python pur**, sur les octets **réellement
servis** — même philosophie « décodeur sans dépendance » que `circuit_tuiles.py` (qui décode la
GÉOMÉTRIE ; celui-ci décode les **propriétés** clés/valeurs d'où le banc tire `idu`/`surface_m2`/
`zone_lib`/`zone_fam`). Ajouté dans `scripts/coherence/lib.py` : `decode_tile_props()` +
`_mvt_varint/_mvt_value/_mvt_layer`. `tuile_props` lit désormais `decode_tile_props(pbf.read_bytes())`.
Le sous-processus node et `decode_tile.mjs` sont **supprimés** (c'était la fragilité). Un corps vide
(parcelle hors tuile) rend `{}` → **ABSENT** (pas comparé), plus jamais une fausse erreur.

**Preuve.** Banc échantillon (120 parcelles, 24 communes, en-process) : **`erreurs_lecteur` = 0**
(était 1198), `faux_client = 0`. Les 78 comparaisons `tuile:surface_m2` s'exécutent désormais (valeur
décodée == SQL `mvt_parcels` à l'octet près, ex. 2223 == 2223) ; les quelques écarts résiduels sont le
dual-source **connu** `contenance` (tuile) vs `surface_m2`/dessin (fiche), majoritairement TOLERABLE,
jamais FAUX-CLIENT. Le contrôle de cohérence du calcul de nuit (vert = `faux_client` + `erreurs_lecteur`)
**passe** désormais.

---

## 2 — Les 6 verrous (diagnostic contre la prod réelle, lecture seule)

Contexte clé : le déploiement joue `labuse circuit verrous **-w G8**` (CRON-1 lot 3 — G8 mesure la
fraîcheur de la veille, pas la santé du code). Un verdict **`a_decider`** n'est **pas** un `casse`
(il attend le geste de Vic). « Contrôle vert » = **aucun bloquant**.

État mesuré **sur la prod** (code déployé `17eb6f8b2`, lecture seule) — reproduit mon diagnostic
exactement :

| Verrou | Cause (prod réelle) | Nature | Correction | Vérif |
|---|---|---|---|---|
| **V4a** | 21 tables de maille commune **sans clé étrangère** : `poser_fks` n'était appelé que par `labuse init-db`, **jamais au déploiement**. | **code (gap de déploiement)** | `referentiel_communes_fk` **ajouté au heal pré-service** (`_executer_heal_schema`) → chaque déploiement pose+valide les FK, en série, hors trafic. `poser_fks` corrige d'abord la coquille INSEE héritée (Saint-Denis 97454→97411, seule ligne fautive prod) puis VALIDATE. | local **24/24 validées** ; `labuse schema-heal` les pose ; verrou → **ok/a_decider** (non-casse) |
| **V1c** | 7 orphelines sans action : `pg_stat_statements` + `pg_stat_statements_info` (vues d'**extension**), `signal_instantanes` (table **vivante**), `mvt_overlays` (**retirée**), `_cad_sm1_disparues/geommodif/nouvelles` (tables de **travail d'audit**). | **code + registre** | (a) `relations_schema` **exclut les objets d'extension** (`pg_depend deptype='e'`) — ce ne sont pas des tables de LA BUSE (comme PostGIS) ; (b) `signal_instantanes` **déclarée** en `TABLES_EXPLOITATION` (écriveur+lecteur servis, comme `coherence_runs`) ; (c) `mvt_overlays` + `_cad_sm1_*` **nommées** dans `ACTIONS_PROPOSEES` (purge/archive). | recalculé contre les **316 relations prod** → **0 sans action** → verrou **`a_decider`** (non-casse) |
| **G5** | `EduGéo Réunion 1980` (et `SCAN 50 1950`) en mode `one_shot` **sans date** → « aucune date ni mention jamais ». Or ce sont des **cartes historiques figées** (WMTS, millésime immuable, **aucun flux amont**, cf. `sentinelle.py`). | **code (catalogue)** | Seed `seed_sources.py` : les deux passées de `one_shot` à **`sans_millesime`** (« à jour par construction, aucun producteur amont à contrôler » — même bucket qu'OSM/INPI). G5 les exempte alors. | appliqué en prod par `labuse seed-sources` (upsert `mode_remplissage`) → verrou **ok** |
| **V3b** | 1 eau ancienne ouverte : **DPE** — amont vu **28/10**, dernière ingestion **13/10** (15 j de retard réel). | **exploitation / fraîcheur donnée** | **Ré-ingérer le DPE** (`cron DPE --force`) → `last_sync_at` rattrape → l'eau se ferme. Pas un bug de code : le verrou signale justement que la donnée prod est en retard sur l'amont. | local **vert** (DPE local à jour) ; remédiation prod = ré-ingestion |
| **V6b** | Le q_v20 **servi en prod** dérive du golden **accepté en dev** : **11 dérives bénignes** « cohérent-mais-changé » — `rang_score` sur les 7 témoins (gigue de rang = ré-éval de la population), `sdp_residuelle` ±1-2 m², 1 bascule de drapeau, `hauteur_faitage 8,1→None` (dérive **connue** ROUGES-7 / faisa A-005). | **donnée (divergence dev↔prod)** | **Ré-accepter le golden contre le servi** (`labuse coherence --accepter`, motif au commit) OU resynchroniser les artefacts q_v20 dev↔prod. Pas un bug de code : le golden **détecte** correctement que la donnée servie ≠ donnée acceptée. | local **vert** (le golden correspond au local) ; remédiation prod = ré-acceptation |
| **G8** | 94 (prod : ~8 structurelles) sources « sonde muette » : la sonde des sources `sonde-sources` n'a pas tourné récemment ; l'agent LLM est à 0 €. | **exploitation / temps** | **Signal d'exploitation, pas un bug ni une règle retirée** (décision retenue avec Vic). **Déjà non bloquant au déploiement** (`-w G8`). Vert quand la sonde de nuit `sonde-sources` tourne ; les sources structurellement sans sonde (agent 0 €) sont nommées par le Résumé. | local rouge (instantané figé, sonde 21/10) ; non bloquant par conception |

**Résumé.** 3 verrous **corrigés dans le code** (V4a, V1c, G5) deviennent non-casse (V4a/V1c au prochain
déploiement via le heal + le registre ; G5 via `labuse seed-sources`). 3 sont des **signaux
exploitation/donnée** (V3b, V6b, G8) — remédiation prod écrite ci-dessus ; **G8 ne bloque déjà pas** le
déploiement. Localement, **`labuse circuit verrous -w G8` = vert (exit 0)** — la commande exacte du
déploiement.

---

## 3 — `/readyz` qui oscille au redémarrage (heal de schéma sous charge)

**Cause.** Le heal de schéma tournait **dans chaque worker uvicorn** au démarrage. Son
`ALTER TABLE event_log ADD COLUMN IF NOT EXISTS …` (no-op quand la colonne existe, mais qui exige quand
même un verrou **ACCESS EXCLUSIVE**) percutait les écritures `event_log` concurrentes (réchauffage,
sondes, mes PDF) → `lock_timeout` (5 s) ×3 → `schema_heal.ok=false` → `/readyz` **503 figé** sur ce
worker (récurrence DEPLOY-1028b / DEPLOY-FINAL / DEPLOY-AUTONOMIE).

**Correction — le heal ne tourne plus pendant le service.**
- Heal **extrait** du lifespan dans `_executer_heal_schema()` (réutilisable).
- CLI **`labuse schema-heal`** le joue **une fois, en série**, et **sort en code 1** si un step échoue.
- Unit systemd : **`ExecStartPre=/opt/labuse/venv/bin/labuse schema-heal`** + **`Environment=LABUSE_SKIP_BOOT_HEAL=1`**.
  Sur `systemctl restart`, l'ancien service est **déjà arrêté** quand l'ExecStartPre tourne → **aucune
  écriture `event_log` concurrente** → le heal aboutit ; les workers **sautent** le heal
  (`LABUSE_SKIP_BOOT_HEAL=1`) → ils ne touchent **jamais** au schéma pendant le service. Un heal
  pré-service raté fait échouer `ExecStartPre` → le service **ne démarre pas** (bruyant), jamais un 503
  silencieux. `TimeoutStartSec` 60 → **180 s** (couvre le heal sérialisé). En dev/test (flag absent),
  heal au boot inchangé — aucune contention locale.

**Preuve — 3 redémarrages sous charge simulée** (`docs/audit-2026-11/autonomie-2/preuve_readyz.py`).
Un lecteur tient un ACCESS SHARE sur `event_log` (bloque l'ALTER, pas les INSERT/SELECT) + charge HTTP
concurrente :
- **AVANT** (heal dans le worker) : le service **ne devient jamais prêt** sous contention (le lifespan
  reste bloqué sur l'ALTER — même la journalisation de l'échec re-percute le verrou). `/readyz` : 0/20 à 200.
- **APRÈS** (`schema-heal` pré-service puis workers `LABUSE_SKIP_BOOT_HEAL=1`) : **redémarrage 1/3, 2/3,
  3/3 → `/readyz` 200 × 15/15 chacun, STABLE**, verrou `event_log` tenu + charge HTTP concurrente.

---

## Recette

- **Banc de cohérence complet sans erreur de lecteur** : `erreurs_lecteur` **1198 → 0** (banc échantillon, en-process). ✅
- **Verrous** : local `labuse circuit verrous -w G8` **vert** (commande de déploiement) ; V1c/V4a/G5 corrigés dans le code, V3b/V6b/G8 remédiation prod écrite (G8 non bloquant). ✅
- **3 redémarrages sans oscillation** : `/readyz` 200 stable 15/15 × 3, sous verrou + charge. ✅
- **Banc complet 0 rouge** : unitaires **2849 passed / 0 failed** ; base (famille `db`) **1330 passed / 0 failed** ; front **tsc 0 + vitest 301 passed** ; cohérence écrans **6 passed, aucun écart (1 €/1 m²)**.
  - *Régression corrigée en cours de recette* : le step FK (V4a) ajouté au heal posait la FK commune sur la base de TEST → 12 tests VEFA (communes fictives 97499) cassaient. Corrigé : `pose_fk` n'est vrai qu'au PRÉ-SERVICE (CLI `schema-heal`), jamais au boot worker/test. Base de test re-verte (1330/0).
- **Hook** pre-push (secrets · front tsc+vitest · unitaires · cohérence) : **vert**.

## Remédiation prod (lecture seule ici — à appliquer au déploiement)
1. **V4a** : automatique — `ExecStartPre labuse schema-heal` pose+valide les FK commune.
2. **V1c** : automatique — le registre corrigé (code) ; les 4 orphelines restantes passent en `a_decider` (purge au geste de Vic : `labuse tables purger`).
3. **G5** : `labuse seed-sources` (applique EduGéo/SCAN 50 → `sans_millesime`).
4. **V3b** : ré-ingérer le DPE (`--force`) pour rattraper l'amont (28/10).
5. **V6b** : `labuse coherence --accepter` contre le servi (dérives bénignes) **ou** resynchroniser q_v20 dev↔prod.
6. **G8** : laisser la sonde de nuit `sonde-sources` tourner ; non bloquant au déploiement (`-w G8`).
