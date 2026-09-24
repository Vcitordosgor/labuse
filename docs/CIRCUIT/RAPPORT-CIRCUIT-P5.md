# RAPPORT CIRCUIT-P5

Date : 23/09/2026 · Modèle : Opus · Branche : `feat/circuit-p5` (depuis `main` `2370a9da`, qui
contient déjà CIRCUIT-P4 mergé) · Worktree : `~/Desktop/labuse-p5` · Ports : 8175 / 5375 ·
**PAS mergée**. Deux commits, un par tâche : `dd3ca660` (1) · `941d6ace` (2) + ce rapport.

Suite directe de l'arbitrage **G** de CIRCUIT-P4 (tâche 1) et du lot 1 de P4 (les « jamais
vérifiées », tâche 2).

> **Contrainte du jour** : un run résiduel tournait encore sur la base réelle (PID 68936, depuis
> 8:08). Le démarrage de l'app complète se bloque sur son **verrou DDL** (constaté, comme en P4) —
> les captures live des deltas d'écran de P5 n'étaient donc pas réalisables sur la base réelle, et
> le harness/`labuse_test` n'a ni les calibrages PLU (qui commandent le lien de la tâche 1) ni la
> page Données (le lien du bas). Les preuves sont donc le **diff de code** (tâche 1) et le **run réel
> mesuré** (tâche 2). La CLI `agent source`, elle, tourne sans souci sur la base réelle (elle ne
> fait pas le lourd `ensure_tables` du démarrage de l'app).

---

## Tâche 1 — le calibrage `plu_destinations` passe dans le détail de la source

**Avant** : la page Données affichait, EN BAS, un lien « Destinations PLU — le détail du réservoir
plu_destinations (calibrage par commune) → » qui ouvrait le composant `DestinationsDetail`.

**Après** : ce lien du bas a disparu. Le détail complet du calibrage s'ouvre depuis la **page de
détail de la source GPU** (« Urbanisme PLU/GPU (API Carto) »), là où la carte « Calibrages PLU »
(commune × état) vivait déjà : un lien « **Voir le calibrage complet par commune (Destinations
PLU) →** » y ouvre `DestinationsDetail`.

Pourquoi la source GPU : `plu_destinations` est un **moteur** (transcription LABUSE), pas une source
du catalogue `data_sources` ; sa carte de calibrages était déjà rattachée au réservoir GPU
(`calibragesParSource`, PLU-CALIBRAGE-1). C'est l'hôte naturel. *(Arbitrage : redirection d'un mot
si Vic vise une autre source.)*

Trois fichiers, **`DestinationsDetail` INCHANGÉ** (`git diff … Destinations.tsx` = vide → le
composant n'est pas cassé, exigence du mandat) :

- `circuit/Circuit.tsx` — nouveau type de détail `destinations` (transitoire, hors deep-link) qui
  rend `<DestinationsDetail onBack={fermerDetail}/>` ; `onOpen` élargi.
- `circuit/Detail.tsx` — le lien dans la carte « Calibrages PLU » du détail réservoir (GPU).
- `Donnees.tsx` — lien du bas + toggle retirés ; la page Données = le Circuit, rien d'autre.

**Portes** : `tsc -b` + `vite build` verts ; `Donnees.test` mis à jour (il vérifie désormais que le
lien « Destinations PLU » du bas a **disparu**) + snapshot régénéré.

---

## Tâche 2 — les agents sur les 12 « jamais vérifiées »

### Deux gestes moteur (car un agent « a_jour » ne marquait rien)

Constat : `lancer_agent` n'écrivait dans `source_veille` **que** sur un verdict `nouvelle`. Un
verdict `a_jour` (le producteur confirme la version servie) ne laissait **aucune trace** →
`dernier_passage_at` restait nul → la source restait « jamais vérifiée » malgré le contrôle.

1. **`lancer_agent` enregistre le contrôle** : sur `a_jour` (statut `ok`) comme sur `nouvelle`, il
   pose `dernier_passage_at = now()` (la date du contrôle). La source passe alors « à jour » ou
   « nouvelle version ». Pas de contrainte unique sur `source_id` → **UPDATE puis INSERT** ; une
   source sans ligne de veille (jamais sondée) est **créée en `methode='agent'`** — jamais reprise
   par la sentinelle (`'agent' ∉ api/page/entete/temoin`), mais son contrôle est désormais visible.

2. **Parseur JSON robuste** (`_valider`) : le `\{.*\}` glouton avalait la **prose** du modèle dès
   qu'elle contenait une accolade (« l'endpoint `…/api/companies/{siren}` ») AVANT le vrai bloc
   JSON → « JSON invalide » **alors que l'agent avait trouvé la réponse** (cas réel INPI RNE). On
   collecte les objets à accolades **équilibrées** (+ un bloc ```json```) et on garde le DERNIER qui
   parse et porte un `verdict`. Sur un premier passage, 8/11 tombaient « JSON invalide » ; après le
   correctif, INPI (v3.0), PVGIS et CBS sont récupérés.

Tests (`test_circuit1_lot6`, **17 passed**) : +3 — `a_jour` enregistre le contrôle · une source sans
veille est créée en `agent` · la prose-avec-accolade parse.

### Le run réel (base réelle, contrôle du 2026-09-24)

**Coût** : `ia_log` — **21 appels agent_source, 816 952 jetons in + 22 092 out, 2,78 € (coût
jetons)**. Le **web_search** natif est facturé séparément par Anthropic (~0,01 $/recherche, jusqu'à
6/agent) et **n'entre pas** au ledger → estimation ~0,6 à 1,2 € en sus. Coût réel total ≈ **3,4 à
4,0 €** pour les 12 sources (2 passages : run initial + reprise après le correctif du parseur).

**Résultat** (détail source par source : `captures/p5/etats-agents-avant-apres.md`) :

| | avant | après |
|---|---|---|
| à jour | 0 | **3** — RTAA DOM, PVGIS, ZFANG (contrôlés le 24/09) |
| nouvelle version | 0 | **2** — INSEE RP Logement 2023, DEAL CBS (la vanne apparaît) |
| jamais vérifiée | 12 | **7** |

- **5 sources ont une réponse datée** → 3 confirmées « à jour » avec la date du contrôle, 2 avec une
  version plus récente (« nouvelle version »). C'est exactement ce que demandait le mandat.
- **7 restent « jamais vérifiée »**, chacune pour une raison honnête : OSM (flux continu, aucune
  version datée) et INPI RNE (expose v3.0 mais sans extrait daté → anti-invention 6.2), Coût de
  construction (donnée interne, pas de producteur), et 4 dont la sortie du modèle n'était pas
  exploitable en JSON (un nouveau passage pourrait en résoudre — le correctif du parseur a déjà
  prouvé qu'il récupère les faux « JSON invalide »).

---

## Captures avant / après

- **Tâche 2** : `docs/CIRCUIT/captures/p5/etats-agents-avant-apres.md` — le tableau avant (12 jamais
  vérifiée) / après (3 à jour + 2 nouvelle version + 7 jamais), source par source, avec ce que
  chaque agent a trouvé. C'est l'avant/après réel (état = donnée).
- **Tâche 1** : l'avant/après est le **diff de code** (lien du bas retiré de `Donnees.tsx` ; lien
  ajouté dans le détail source de `Detail.tsx`), `DestinationsDetail` inchangé. La capture live des
  écrans n'était pas réalisable (run résiduel bloquant l'app réelle ; harness/`labuse_test` sans
  calibrages ni page Données). À rejouer une fois le run résiduel terminé si Vic veut la capture
  d'écran : Sources → « Urbanisme PLU/GPU » → « Voir le calibrage complet par commune ».

---

## Commandes et résultats

| Quoi | Commande | Résultat |
|---|---|---|
| Tâche 1 | `tsc -b` · `vite build` | verts ; `Donnees.test` + snapshot mis à jour |
| Tâche 2 tests | `pytest test_circuit1_lot6 test_circuit4_lot2` | 17 + 10 passed |
| Tâche 2 run | `labuse agent source --ids 148,31,19,25,40,43,117,41,131,72,48,73` | 5 réponses datées, 3 « à jour » |
| Coût | `SELECT sum(cout_eur) FROM ia_log WHERE kind='agent_source'` | 2,78 € (jetons) + web_search à part |

**Reste à Vic** : merge ; injecter les 2 « nouvelle version » (INSEE RP Logement 2023, CBS) quand il
veut ; relancer les 4 sorties non-JSON après le run résiduel si utile.
