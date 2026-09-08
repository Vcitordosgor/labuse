# COHÉRENCE-RUN-1 — les tables annexes doivent suivre le run servi

**Branche** : `feat/paliers-1` (worktree `~/Desktop/labuse-paliers1`), à la suite de BASCULE-1.
**Date** : 2026-09-08. **Modèle** : Fable. **Interdits respectés** : aucun merge, aucun rescoring du
modèle P, aucune bascule (q_v14 reste servi en local), périmètre borné aux 5 tables.

---

## Étape 0 — état des lieux

- `pwd` = `~/Desktop/labuse-paliers1` ✓
- branche = `feat/paliers-1` ✓
- arbre **PAS strictement propre** : 3 fichiers modifiés non commités —
  `config/served_manifest.json`, `config/served_run.txt`, `config/run_precedent.txt`.
  Ce sont **exactement** les pointeurs de service qui portent le « q_v14 basculé en local »
  (`served_manifest.json` : `scoring_run=q_v14`, `par=cli`, `promoted_at=2026-09-08T11:51`).
  Par la doctrine BASCULE-1 ces vues sont un **état LOCAL de service**, pas un artefact à commiter.
  **Laissés intacts** (ne pas les commiter reviendrait à ne pas toucher au servi ; les commiter =
  une bascule déguisée, interdite). Le mandat déclare lui-même cet état (« q_v14 est basculé en local »).

**Base** : `labuse` sur `localhost` (rôle `openclaw`) ; l'installe éditable pointe sur CE worktree
(`labuse.__file__` = `labuse-paliers1/src/labuse`) — pas d'écart d'arbre.

---

## Comment lire ce diagnostic — la découverte centrale

Les cinq avertissements **ne sont pas de même nature**. Il y a **une racine** (la cascade) et le
reste en découle. Résumé avant le détail :

| Table | Run porté | Run servi | Dépend de la cascade ? | Guéri par `build-mvt` ? | Vrai écart client ? |
|---|---|---|---|---|---|
| `dryrun_parcel_evaluations` (cascade, per-parcelle) | *(pas de q_v14)* | q_v14 | **c'est la racine** | non (rejeu = heures) | **oui — voir §5** |
| `dryrun_cascade_results` (cascade, par couche) | *(pas de q_v14)* | q_v14 | **c'est la racine** | non (rejeu = heures) | **oui — voir §5** |
| `parcel_renouvellement` | q_v11_m137 (67 260) | q_v14 | **OUI** (lit la cascade) | **non — le viderait** | oui, mais bloqué par la racine |
| `parcel_flags` | q_v11_m137 (2 208 373) | q_v14 | non | **oui** (~indépendant) | oui — badges vigilance absents |
| `score_e` | q_v13_sources1 (285 781) | q_v14 | non (lit `parcel_p_score_v2`) | **oui** | écart d'étiquette, faible risque chiffré |
| `division_or_candidates` | q_v13_sources1 (10) + q_v10_m129 (23) | q_v14 | n/a | n/a | **non — exception légitime** |

**La cascade est la clé de voûte.** `q_v14` a été scoré en **réutilisant volontairement** l'étage 0
de `q_v13_sources1` (`LABUSE_ETAGE0_RUN=q_v13_sources1`, SCORING-4, `pipeline.py:375`) — le rejeu de
cascade (24 communes, 431 663 parcelles) « se compte en heures » et a été **sciemment évité**. Mais
cette réutilisation n'existe **qu'au moment du scoring**. Au moment de **servir**, tous les lecteurs de
cascade interrogent `runs.current()` = `q_v14` → **0 ligne**. Il n'y a **aucun alias étage-0 côté
service**. C'est ça, le vrai trou.

---

## Lot A — diagnostic (lecture seule)

### 1. `dryrun_parcel_evaluations` + `dryrun_cascade_results` (la cascade) — LA RACINE

**Ce que porte la base** : `q_v14` est **présent** dans `parcel_p_score_v2` et `p_score_v2_runs`
(431 663 parcelles, scoré le 2026-09-08 03:50) mais **absent des deux tables de cascade** (elles
s'arrêtent à `q_v13_sources1` : 431 663 lignes d'évaluations / 17 599 544 lignes de résultats).

**Qui les lit, et ce que voit le client sous q_v14** — le verdict/tier de fiche NE dépend PAS de la
cascade (`verdict_servi.py` lit `parcel_p_score_v2` seul → q_v14 OK). Mais **beaucoup d'autres surfaces
servies** lisent la cascade au run courant. Vérifiés directement :

- **Cascade servie des documents et de la fiche** — `api/served_cascade.py:33-40` :
  `served_cascade_lines(db, idu, run=runs.current())` → `WHERE cr.run_label = :run` → **[] sous q_v14**.
  Docstring : « les 4 documents — premium, dossier, banquier, fiche écran — lisent la MÊME cascade
  servie ». Conséquence : **les motifs / risques / règles issus de la cascade disparaissent** de la
  fiche et des documents générés (sections aléas, PPR, zonage arbitré) — un client verrait des blocs
  vides là où il y avait des vigilances.
- **anti-fiche** (`/anti-fiche/{idu}`, `api/anti_fiche.py`) — s'appuie sur `served_cascade_lines` →
  synthèse « aucun motif d'écartement » alors que la parcelle en a (silencieux).
- **Carte GeoJSON** (`api/app.py`, `_q_v2_geojson`) — `flags`/`etage0` joints au run courant →
  pastilles/flags manquants sur la carte île.
- **`renouvellement.build`** (voir §3) — dépend directement de la cascade au run.
- Autres lecteurs tracés (agent, non tous re-vérifiés un à un) : `api/moteurs.py` (simulplu, assemblage),
  `api/modules.py` (diligence dossier, réseaux), `api/projets.py` (événements « rouge »),
  `api/events.py` (journal BODACC entre runs), `flash/data.py` (`etage0`). Tous filtrent `run_label =
  run courant` → dégradés/vides sous q_v14. Certains chemins PDF sont dormants (EXPORTS-2).

**Comment se recalcule** : `labuse flux-run --label q_v14` (cascade sur 24 communes **puis** scoring) —
ou la cascade seule via `labuse dryrun-evaluate` commune par commune (`cli.py:598`). **Durée : des
HEURES** pour l'île entière (documenté SCORING-4 §Réserve 1 + `cli.py:668` + CIRCUIT-1 déc. n°16).
`flux-run` **rejoue aussi le scoring** (`run_score_v2`) = **rescoring du modèle P → INTERDIT** par le
mandat. La cascade seule (`dryrun-evaluate` × 24) évite le modèle mais **dépasse 1 h** → **règle du
mandat : STOP, arbitrage de Vic**.

**Est-ce un vrai écart ?** **Oui pour les lecteurs de cascade, mais la solution « rejouer » est fausse.**
La cascade de `q_v14` serait, par construction, **identique** à celle de `q_v13_sources1` (même étage 0,
mêmes sources/millésimes de cascade — c'est le principe de la réutilisation). La rejouer ne ferait que
**dupliquer** 431 663 + 17,6 M lignes sous un label redondant, pour des heures de calcul. Le geste juste
n'est pas un rejeu : c'est **apprendre à la couche de service la réutilisation d'étage 0** (voir Lot C).

**Bug démasqué au passage** — `bascule_flux._run_complet` (`bascule_flux.py:99-114`) devait refuser un run
sans cascade. Or il fait `casc = SELECT 1 … WHERE run_label=:r LIMIT 1` : **0 ligne → `.scalar()` = None**,
et la branche suivante `if casc is None: return True, "cascade non vérifiable (table absente) — toléré
hors production."` **ne distingue pas « table absente » de « table présente, 0 ligne pour ce run »**.
C'est **par ce trou** que `golden promote q_v14` (alias de `basculer()`, `cli.py:4235`) a laissé passer
q_v14 malgré une cascade absente, écrit le manifeste et affiché les 5 avertissements de cohérence.
(Le journal `run_bascule_journal` n'a d'ailleurs pas d'entrée q_v14 — dernière bascule tracée : 2026-09-05
q_v12→q_v11_m137 — l'écriture du manifeste a eu lieu sans journalisation complète, cohérent avec un
retour anticipé sur relecture d'arbre / commit non abouti.)

### 2. `parcel_flags` — q_v11_m137 (2 208 373 lignes)

**Qui la lit / ce que voit le client** : `/search` et les facettes de vigilance filtrent
`parcel_flags.run_label = run courant` (tracé `api/app.py` ~1381). Sous q_v14 → **0 ligne** → les
**badges/filtres de vigilance disparaissent** des résultats et de la carte (les alertes ne s'affichent
plus, le compteur tombe à 0). Écart **visible mais bénin** (une absence, pas un chiffre faux).

**Comment se recalcule** : `build_parcel_flags_table` (`api/tiles.py:196`), appelé par
`rebuild_mvt_servies` = **`labuse build-mvt`** (défaut = run servi). **Indépendant de la cascade**
(construit sur `spatial_layers` ∩ géométrie servie). **Durée : quelques minutes** (build-mvt total
mesuré ~146 s, DONNEES-2). **Guéri proprement par build-mvt.**

### 3. `parcel_renouvellement` — q_v11_m137 (67 260 lignes)

**Qui la lit / ce que voit le client** : `/renouvellement/liste` filtre `run_label = run courant`
(tracé `api/app.py` ~5478) — l'outil « Densifier / renouvellement urbain ». Sous q_v14 → **0 ligne** →
**outil vide**.

**Comment se recalcule** : `renouvellement.build` via `rebuild_mvt_servies` (`build-mvt`) ou `labuse
renouv`. **MAIS elle lit la cascade** : `dryrun_cascade_results WHERE run_label = :run`
(`renouvellement.py:138,161,170,178,189`). Comme q_v14 n'a **pas** de cascade, **`build-mvt` sur q_v14
produirait un `parcel_renouvellement` VIDE (0 ligne)** — il **remplacerait** 67 260 lignes q_v11_m137
par 0, aggravant l'écran. **⇒ Non guérissable tant que la racine (cascade) n'est pas résolue.**

### 4. `score_e` — q_v13_sources1 (285 781 lignes)

**Qui la lit / ce que voit le client** : le bloc « Score É / marge estimée » de la fiche —
`api/app.py:5756` : `SELECT … FROM score_e WHERE idu = :i` — **SANS filtre de run**. Donc la fiche sert
**toujours le dernier `score_e` en base**, aujourd'hui `q_v13_sources1`, sous une fiche q_v14. C'est un
**écart d'étiquette de cohérence** (le reste de la fiche dit q_v14, ce bloc vient d'un autre run) au
**risque chiffré faible** : `score_e` ne dépend que de `parcel_p_score_v2` (tiers non-écartés) + médianes
DVF, et q_v14 partageant l'étage 0 de q_v13_sources1, la population non-écartée est quasi identique — les
marges seraient proches. Reste que l'absence de scoping est une dette (une lecture non-scopée ne peut pas
mentir sur le run si le run ne change pas la donnée, mais elle **empêche la garde de le vérifier**).

**Comment se recalcule** : `score_e.build_score_e` (`ingestion/score_e.py:167`) via `rebuild_mvt_servies`
(`build-mvt`) ou `labuse score-e`. **Indépendant de la cascade** (lit `parcel_p_score_v2 WHERE run_id=:run
AND tier<>'ecartee'`, q_v14 présent). **Durée : minutes** (inclus dans les ~146 s de build-mvt).
**Guéri proprement par build-mvt.**

### 5. `division_or_candidates` — q_v13_sources1 (10) + q_v10_m129 (23) — EXCEPTION LÉGITIME

**Comment c'est peuplé** : par commune, à la main (`labuse division-or --communes …`), estampillé
`run_label = runs.current()` **au moment de la passe** — **pas** au rebuild d'un run. C'est un
**workflow de revue humaine** (dossier 20 cartes validé par Vic, pattern J3). L'outil est **`EXPOSE =
False`** (`ingestion/division_or.py`, dormant depuis M129-C) : **rien n'est servi au client** aujourd'hui.

**Qui la lit** : ligne « Division » de fiche (`api/app.py:_division_fiche`, filtre `division_run` du
manifeste) et facette « Divisible » (filtre `run_label = run courant`). Sous q_v14 → 0 ligne → ligne
« divisibilité non recalculée pour ce run » ou absente. Comme l'outil est dormant, **impact client nul**.

**Est-ce un vrai écart ?** **Non.** C'est déjà `_TOLEREES` (`coherence_flux.py:97`) et marqué
`workflow_par_commune=True` (`bascule_gardes.py:763`). Un workflow de revue par commune **retarde
légitimement** le run servi. La sonde le signale **mais tolère** (`⚠ … (workflow revue par commune —
toléré)`) — c'est le comportement voulu (test `test_division_or_perimee_toleree_mais_flaggee`). **Rien à
recalculer.** Seule remarque : la sonde pourrait le classer explicitement en « toléré » plutôt qu'en
« PÉRIMÉE tolérée » pour ne pas le compter comme un écart (Lot C, secondaire).

---

## Lot B — ce qui a été recalculé (arbitrage Vic : voie (a) — C2 puis C1, puis build-mvt, AUCUN rejeu)

Après lecture du diagnostic, Vic a tranché : **on n'a PAS rejoué la cascade** (ni le modèle P). On a
appris la réutilisation d'étage 0 à la couche de service (C1), puis matérialisé les annexes par
**`build-mvt` sur q_v14** (mesuré ~2 min, base réelle `labuse`). Après C1, chaque table LIT la cascade
RÉELLE (empruntée à `q_v13_sources1`) tout en STAMPANT le run servi `q_v14` :

| Table | Avant | Après build-mvt | Statut sonde |
|---|---|---|---|
| `mvt_parcels` (carte) | q_v11_m137 | **q_v14** (431 663) | ✓ |
| `parcel_flags` | q_v11_m137 (2 208 373) | **q_v14** (2 322 429) | ✓ OK |
| `parcel_renouvellement` | q_v11_m137 (67 260) | **q_v14** (67 260) — **PAS vide** (C1 lit la cascade empruntée) | ✓ OK |
| `score_e` | q_v13_sources1 (285 781) | **q_v14** (281 403) | ✓ OK |
| `dryrun_*` (cascade) | pas de q_v14 (empruntée) | inchangée — **empruntée EXPLICITEMENT** (manifeste `cascade_run`) | ✓ présente (431 663) |
| `division_or_candidates` | q_v13_sources1 + q_v10_m129 | inchangée — **exception légitime** | ⚠ toléré |

## Lot C — que ça ne se reproduise pas (IMPLÉMENTÉ : C2 puis C1)

**C2 — la bascule ne peut plus servir un run sans cascade** (`bascule_flux._run_complet`, commit
`ea3772d2`). Le trou : `SELECT 1 … LIMIT 1` sur 0 ligne rendait `None` comme une table absente → « toléré
hors production ». On distingue désormais l'ABSENCE de table (indéterminé) du VIDE pour ce run (refus).
C'était le **second faux positif de la journée** dans ce code. Garde `test_run_scoré_sans_cascade_est_refusé`.

**C1 — la couche de service connaît l'étage 0 emprunté** (commits `98e0cd80` + `54f43374`). Le manifeste
porte un champ **explicite** `cascade_run` (jamais un défaut implicite deviné — exigence Vic) : la bascule
l'écrit et le VÉRIFIE en base (`resoudre_cascade_run` : cascade propre au run, ou étage 0 emprunté lu dans
`params` (`etage0_run`/`prev_run`) et confirmé ; refus si introuvable). `runs.cascade()` le relit à la
requête. Tous les lecteurs de cascade (fiche + 4 documents, carte, autocomplete, renouvellement,
`build-mvt`, moteurs, modules, projets, copilote, events, nl, partners, solaire) et les gardes
(`_run_complet`, `check_coherence_run_fiche`) résolvent `q_v14 → q_v13_sources1` — **sans dupliquer 17,6 M
lignes**, no-op pour tout run à cascade propre (zéro changement prod/tests). Les `:run` mixtes
cascade+score ont été séparés (`:run` cascade, `:v2run` score).

**SONDE NOCTURNE (exigence Vic)** — `coherence_flux.verifier` check 7 : « la cascade servie EXISTE
ENCORE ». Le `cascade_run` servi doit avoir des lignes ; sinon écart bruyant. **Un run servi ne peut plus
pointer vers une cascade purgée** — à la bascule (C1/C2) comme chaque nuit. Garde
`test_run_emprunteur_de_cascade_est_accepté_et_résolu`.

---

## Re-vérification après build-mvt (exigence Vic « montre-moi les avertissements restants »)

**Sonde `coherence_flux.verifier` → `ok global = True` (7/7)** :
- ✓ 20 surfaces lisent le run courant (q_v14) — run fiche cohérent (v2 q_v14 + cascade empruntée q_v13_sources1)
- ✓ Tier identique fiche/Projets/Scan · ✓ Date de valeur · ✓ Exports = écran · ✓ Endpoints vivants
- ✓ **Cascade servie présente : q_v13_sources1 (empruntée par q_v14) — 431 663 lignes**
- ✓ Aucune lecture de table obsolète — toléré (revue par commune) : division_or_candidates

**Avertissements de promote restants** :
- `parcel_flags` / `parcel_renouvellement` / `score_e` → **OK** (q_v14).
- `division_or_candidates` → **⚠ PÉRIMÉE mais TOLÉRÉE** (workflow de revue par commune, `EXPOSE=False`) —
  **seul avertissement restant, et il est légitime** (rien à recalculer ; cf. lot A §5).

**Il ne reste aucun écart réel** : les cinq entrées du mandat sont soldées (trois recalculées et alignées
sur q_v14, la cascade empruntée EXPLICITEMENT + surveillée, `division_or` tolérée). `test_tuiles_mvt_…`
passe sur la base réelle.

## Notes / limites
- Deux couches `spatial_layers` restent ORPHELINES de source (`tcsp_zone`, `vefa_neuf`) — signalé par
  `check_sources_declarees` au build, **pré-existant et hors périmètre** des 5 tables.
- `entonnoir_motifs` (cache de motifs du funnel, hors des 5 tables) reste run-scopé sur le scoring : sous
  un run emprunteur ses motifs seraient vides. Adjacent, non traité (hors mandat) — à signaler si repris.
- Interdits respectés : aucun merge, aucun rescoring du modèle P, aucune bascule (q_v14 reste servi en
  local), aucun rejeu de cascade. `config/served_manifest.json` local complété du champ
  `cascade_run: q_v13_sources1` (état de service LOCAL, non commité — comme les autres pointeurs).
