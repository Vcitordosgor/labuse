# EXIGU-FIX-1 — « terrain trop étroit » ne ment plus

Branche `fix/exigu-fix-1` · worktree `~/Desktop/labuse-exigu` · base locale `labuse` (run servi
`q_v20`, seq 17) · **lecture seule en prod (aucun accès), calcul seulement, pas de merge.**
À lire d'abord : `docs/audit-2026-11/algo-lecture-1/ALGO.md` §3.4 ; `~/Desktop/labuse-deploy3/reports/DEPLOY-GROUPE-3.md` §D et §E.

---

## 0. Résumé

Le moteur classait une parcelle `terrain_exigu` (« terrain trop étroit ») dès que l'emprise
calculée tombait sous 5 m² — **sans vérifier qu'un gros morceau d'un seul tenant restait
exploitable**. Sur de grandes parcelles, deux mécanismes produisaient ce faux positif :

1. **le moteur gabarit s'effondre** (zone d'implantation vidée par les reculs par côté) alors
   qu'un simple inset séparatif laisse des centaines de m² utiles ;
2. **la cause est alors mal attribuée** — « PPR rouge », « hors rouge sans accès », « portion
   réduite » — sur des parcelles dont 80–99 % sont pourtant hors rouge et constructibles.

Le correctif ajoute, **uniquement quand l'emprise tombe sous le seuil**, un **ré-examen
géométrique indépendant** : sur la géométrie **réparée** (`ST_MakeValid`), il mesure le **plus
grand morceau d'un seul tenant** de l'assiette nette = `(parcelle ∩ U/AU)` insetée des reculs,
amputée de l'**union** des contraintes certaines (ER/EBC/PPR rouge/PEB A-B/DPF/ravine/50 pas).
Trois issues, **sur preuve** :

- **assiette exploitable** (aire ≥ 5 m² ET largeur utile ≥ 3 m) → la capacité est **calculée sur ce
  morceau** (la parcelle retrouve un potentiel) ;
- **prouvé inexploitable** (morceau net mesuré petit/étroit, ou parcelle elle-même en ruban) →
  reste `terrain_exigu`, **avec la preuve mesurée** ;
- **douteux** (parcelle large mais aucune assiette nette fiable — contraintes superposées
  pathologiques, portion U/AU géométriquement incohérente, géométrie non réparable) → **nouvelle
  cause d'IGNORANCE `assiette_a_verifier`** (« à vérifier », jamais « trop étroit »).

**Garantie atteinte** : plus aucune parcelle > 1 000 m² ne porte « trop étroit » sans preuve
géométrique.

---

## 1. Périmètre (contrainte du mandat)

> « Le correctif ne modifie que la règle terrain_exigu et la préparation de la géométrie qui la
> précède. La session de déploiement recalculera seulement les 72 083 parcelles terrain_exigu du
> run candidat ; tout changement hors de cette règle rendrait ce recalcul partiel invalide. »

**Le ré-examen est strictement condamné (`if emprise < SEUIL_EXIGU_M2 …`)** : il ne s'exécute que
sur les parcelles que le code d'origine s'apprêtait à classer `terrain_exigu`. Une parcelle qui
n'aurait pas été `terrain_exigu` prend le chemin d'origine **inchangé, octet pour octet** → elle
n'est jamais recalculée par erreur, et le recalcul partiel des 72 083 reste valide.

Fichiers touchés (`git diff --stat` ci-dessous) et justification de chacun vis-à-vis du périmètre :

| Fichier | Nature | Périmètre |
|---|---|---|
| `faisabilite/db.py` | la **préparation de la géométrie** : SQL `_ASSIETTE_NETTE_ROBUSTE`, helper `_reexamen_exigu`, seam `_exigu_fix_actif`, bloc de ré-examen **condamné** à `emprise < seuil` | cœur du mandat |
| `faisabilite/engine.py` | la **règle** : la branche assiette-vide sert `assiette_a_verifier` au lieu de `terrain_exigu` sur un doute ; libellé de la nouvelle cause | cœur du mandat |
| `scoring/scenarios_v2_build.py` | **contrat de la nouvelle cause** : `assiette_a_verifier` rejoint les causes d'IGNORANCE (`eligibility='unknown'` → « À vérifier ») | 1 ligne ; **no-op pour toute autre cause** → aucune parcelle hors `terrain_exigu` affectée |
| `exports/blocs/comparatif.py` | libellé court « assiette à vérifier » | idem, no-op hors nouvelle cause |

Les deux derniers fichiers sont le **contrat minimal de la valeur de cause produite par la règle**
(sans eux, les parcelles « à vérifier » seraient servies « eligible/allowed » — un bug). Ils ne se
déclenchent que sur `assiette_a_verifier`, cause **qu'aucune parcelle ne porte tant que la règle
corrigée ne l'a pas produite** — donc **no-op** pour les 362 499 parcelles hors `terrain_exigu`, et
le recalcul partiel reste valide. Le reste de l'écosystème de causes est *function-driven*
(`cause_certaine()`), donc une cause d'ignorance nouvelle tombe automatiquement en bande NC /
« À vérifier » / SDP ∅ partout ailleurs (Score, fiche, PDF, Copilote) sans autre changement.

Un **seam de mesure** `LABUSE_EXIGU_FIX=0` rejoue le chemin d'origine (pour l'avant/après sur la
même population) ; **actif par défaut**, jamais lu par la prod.

---

## 2. Diagnostic — pourquoi le contour après reculs est vide (parcelles > 1 000 m²)

Mesure sur toutes les parcelles `terrain_exigu` de plus de 1 000 m² (code courant, fix OFF ; île
entière, base locale ; parcelles touchant une zone U/AU). Pour chacune : cause attribuée par le
moteur (`raison`), état géométrique (validité, multipolygone) et métriques du ré-examen (plus grand
morceau net, largeur). Script `scripts/exigu_fix_1_mesure.py` → agrégé par `scripts/exigu_fix_1_agg.py`.

Population : **65 954** parcelles > 1 000 m² touchant une zone U/AU ; **9 933** déclarées
`terrain_exigu` par le code courant (fix OFF). (La règle ne peut naître que sur une zone U/AU —
ailleurs c'est `zone_non_constructible` ; le préfiltre est donc sans perte.) Colonnes « régain /
exigu / à vérifier » = ce que le fix en fait (cause servie, `cause_on`).

| cause du contour vide | n | régain | exigu (preuve) | à vérifier |
|---|--:|--:|--:|--:|
| portion U/AU réduite | 6 725 | 5 321 | 480 | 917 |
| contraintes superposées (PPR rouge) | 1 377 | 102 | 256 | 1 019 |
| contraintes superposées (PEB/DPF/ravine/50 pas) | 567 | 0 | 44 | 523 |
| contraintes superposées (ER) | 516 | 2 | 70 | 444 |
| contraintes superposées (hors rouge < 200 m²) | 349 | 268 | 80 | 0 |
| reculs (tous côtés / forme très découpée) | 269 | 111 | 147 | 11 |
| contraintes superposées (hors rouge enclavé) | 99 | 99 | 0 | 0 |
| contraintes superposées (EBC) | 30 | 0 | 3 | 27 |
| multipolygone (reculs sur morceaux disjoints) | 1 | 1 | 0 | 0 |
| **total** | **9 933** | **5 904** | **1 080** | **2 941** |

Trois exemples par cause (hors les 5 témoins détaillés plus bas) :

- **portion U/AU réduite** — `97406000AS0061` (1 943 750 m²→à vérifier) · `97412000AN0208`
  (1 024 263 m²→à vérifier) · `97408000AV0934` (977 022 m²→à vérifier)
- **contraintes superposées (PPR rouge)** — `97411000CE1266` (102 084 m²→exigu) · `97423000AK0342`
  (73 950 m²→exigu) · `97401000AD1560` (54 459 m²→exigu)
- **contraintes superposées (PEB/DPF/ravine/50 pas)** — `97424000AK0072` (573 975 m²→à vérifier) ·
  `97415000AH0019` (448 500 m²→à vérifier) · `97411000CI0240` (304 259 m²→à vérifier)
- **contraintes superposées (ER)** — `97415000CN0232` (98 298 m²→à vérifier) · `97411000IR0368`
  (58 210 m²→à vérifier) · `97410000AI0268` (44 287 m²→à vérifier)
- **contraintes superposées (hors rouge < 200 m²)** — `97415000BW0038` (8 688 m²→régain) ·
  `97404000AD0882` (8 625 m²→régain) · `97422000CO0647` (7 750 m²→exigu)
- **reculs (tous côtés / forme très découpée)** — `97415000AB0732` (82 818 m²→régain) ·
  `97412000CH0354` (65 973 m²→exigu) · `97415000AB0731` (42 981 m²→régain)
- **contraintes superposées (hors rouge enclavé)** — `97415000EY2132` (47 559 m²→régain) ·
  `97415000DI0313` (44 270 m²→régain) · `97415000DI0994` (42 646 m²→régain)
- **contraintes superposées (EBC)** — `97411000BX0146` (193 715 m²→exigu) · `97411000CL0258`
  (74 390 m²→à vérifier) · `97411000DH0114` (66 547 m²→à vérifier)
- **multipolygone (reculs sur morceaux disjoints)** — `97411000HS0531` (1 080 m²→régain)

**Constat clé** : l'inset séparatif uniforme (−3 m) ne vide **pas** ces parcelles (il laisse
systématiquement un gros morceau d'un seul tenant). Le vidage vient de **l'effondrement du moteur
gabarit** (reculs par côté) et du **clip des contraintes** ; la « cause » affichée (`reculs`,
`ppr_rouge`, `hors_rouge_sans_acces`, `portion_reduite`) est le plus souvent **mal attribuée** —
d'où le mot « trop étroit » sur des terrains qui ne le sont pas.

### Les cinq témoins du mandat

| IDU | Commune | Surface | Zone | cause d'origine (fix OFF) | morceau net (fix) | largeur | **verdict fix ON** |
|---|---|--:|---|---|--:|--:|---|
| `97418000AY0416` | Sainte-Marie | 2 061 m² | UA | terrain_exigu / **reculs** | **814 m²** | 8,3 m | **capacité** (SDP max 1 831 m²) |
| `97411000DK0447` | Saint-Denis | 2 288 m² | Ui | terrain_exigu / **ppr_rouge** (20 % rouge) | **734 m²** | 9,8 m | **capacité** (SDP max 1 077 m²) |
| `97415000CW0252` | Saint-Paul | 2 157 m² | U3c | terrain_exigu / **hors_rouge_sans_acces** (1 % rouge) | **1 618 m²** | 34,6 m | **capacité** (SDP max 1 747 m²) |
| `97419000AN0398` | Sainte-Rose | 5 926 m² | Uc | terrain_exigu / ppr_rouge (57 % rouge, 11 % U/AU) | **5 m²** | 0,6 m | **terrain_exigu** (prouvé : net 5 m², largeur 0,6 m) |
| `97403000AL0258` | Entre-Deux | 114 600 m² | Ua | terrain_exigu / portion_reduite (0 % U/AU géométrique) | ∅ (parcelle 146 m de large) | — | **assiette_a_verifier** |

- **AY0416/DK0447/CW0252** : faux positifs typiques — le gabarit s'effondrait ou la cause rouge/accès
  était mal attribuée alors que 80–99 % de la parcelle est hors rouge et constructible → **régain**.
- **AN0398** : la portion réellement constructible (11 % U/AU, hors des 57 % de rouge) se réduit à
  ~5 m² de large 0,6 m → **vraiment inexploitable**, `terrain_exigu` **confirmé avec preuve**.
- **AL0258** : 11,4 ha, 146 m de large, mais **0 % d'intersection U/AU géométrique** (le zonage
  résolu dit « Ua » mais aucune couche U/AU ne recouvre la parcelle) et des PPR superposés
  pathologiques → aucune assiette nette fiable → **`assiette_a_verifier`** (ni capacité, ni « trop
  étroit » : un 11 ha n'est pas « trop étroit »).

---

## 3. Le correctif

### 3.1 Préparation de la géométrie (db.py)

`_ASSIETTE_NETTE_ROBUSTE` (lecture seule, isolée en `SAVEPOINT`) mesure, sur la géométrie
**réparée** `ST_MakeValid(geom_2975)` :

- `pre_m2` — aire du plus grand morceau d'un seul tenant de `(parcelle insetée −recul) ∩ U/AU`
  (assiette **avant** contraintes) ;
- `net_m2` — aire du plus grand morceau d'un seul tenant après soustraction de l'**union** des
  contraintes certaines (même définition que `_GREVE_LEGACY_UNION`) ;
- `net_largeur` — diamètre du **cercle inscrit** (`ST_MaximumInscribedCircle`) de ce morceau net
  (largeur utile) ;
- `parc_largeur` — diamètre inscrit de la parcelle (détecte un vrai ruban) ;
- `has_net`, `valide`.

Toutes les aires sont ramenées à l'échelle de la **contenance** (règle C3) côté Python.

### 3.2 La règle de décision (`_reexamen_exigu`)

```
exception / géométrie nette non réparable            → assiette_a_verifier   (douteux)
morceau net : aire ≥ 5 m²  ET  largeur ≥ 3 m          → CAPACITÉ sur ce morceau (régain)
morceau net mesuré, mais trop petit OU trop étroit     → terrain_exigu  (preuve : net petit/étroit)
aucun morceau net, parcelle elle-même étroite (< 2·recul+1 m) → terrain_exigu  (preuve : ruban)
aucun morceau net, parcelle large                      → assiette_a_verifier   (douteux)
```

Seuils : `SEUIL_EXIGU_M2 = 5` (aire ; constante historique, **inchangée** — elle sert aussi la
condamnation du bloc), `LARGEUR_MIN_EXPLOITABLE_M = 3` (largeur utile du morceau net). Le seam
`LABUSE_EXIGU_FIX` permet la mesure avant/après.

### 3.3 La nouvelle cause `assiette_a_verifier`

Cause d'**ignorance** (pas un verdict ferme) : `cause_certaine()` renvoie `False` → partout bande
**NC / « À vérifier »**, SDP ∅, « Analyse incomplète — assiette constructible à vérifier ». Jamais
le mot « étroit ». `batch ≡ fiche` par construction (le batch `compute_residuel` appelle le même
`parcel_faisabilite`).

---

## 4. Mesure avant / après (toutes les parcelles terrain_exigu de l'île)

La mesure utilise le seam `LABUSE_EXIGU_FIX` : fix OFF = chemin d'origine (avant), fix ON = chemin
corrigé (après), **sur la même parcelle**. L'état « après » est la **cause réellement servie** par
le moteur (`cause_on` : `None`→régain capacité ; `terrain_exigu`→reste exigu ; `assiette_a_verifier`→
à vérifier).

### 4.1 Parcelles > 1 000 m² (census complet des 9 933 terrain_exigu du code courant)

| tranche | n exigu (avant) | régain capacité | reste exigu (preuve) | à vérifier |
|---|--:|--:|--:|--:|
| 1 000–2 000 m² | 3 554 | 1 687 | 522 | 1 340 |
| 2 000–5 000 m² | 3 020 | 1 764 | 275 | 978 |
| 5 000–10 000 m² | 1 413 | 942 | 130 | 341 |
| > 10 000 m² | 1 946 | 1 511 | 153 | 282 |
| **total** | **9 933** | **5 904 (59 %)** | **1 080 (11 %)** | **2 941 (30 %)** |

**59 % des « terrains trop étroits » de plus de 1 000 m² retrouvent une capacité** ; 30 % passent
« à vérifier » (aucune assiette nette fiable — contraintes/portion à confirmer) ; 11 % restent
exigus, **chacun avec une preuve géométrique**.

### 4.2 Parcelles ≤ 1 000 m² (échantillon aléatoire de 4 200 terrain_exigu servis)

| tranche | n (échantillon) | régain | reste exigu | à vérifier |
|---|--:|--:|--:|--:|
| < 300 m² | 3 432 | 36 (1 %) | 3 285 (95 %) | 111 (3 %) |
| 300–1 000 m² | 766 | 217 (28 %) | 223 (29 %) | 326 (42 %) |

Les petites parcelles restent très majoritairement exiguës (95 % sous 300 m²) : **le fix ne leur
invente pas de capacité** — il corrige le mensonge sur les GRANDES, pas le verdict juste sur les
petites.

### 4.3 Garantie du mandat (vérifiée sur les métriques AUTORITAIRES du moteur)

Sur les **1 080** parcelles > 1 000 m² qui restent `terrain_exigu` après le fix (dont **147** portant
le libellé « trop étroit » / raison reculs), **0 (zéro) n'est servie sans preuve géométrique** : le
moteur ne conserve `terrain_exigu` que lorsque son propre ré-examen renvoie `exigu` (plus grand
morceau net mesuré sous 5 m² ou 3 m de large, ou parcelle elle-même en ruban) — la conservation EST
la preuve, et un recoupement sur la trace `ctx.reexamen_exigu` des 1 080 le confirme (0 violation).
**Plus aucune parcelle de plus de 1 000 m² ne porte « trop étroit » sans preuve géométrique.**

---

## 5. Vérifications

- **`batch ≡ fiche`** sur les 5 témoins **et** 20 parcelles tirées au hasard dans la population
  touchée : **25/25** (même cause servie par `compute_residuel` et `parcel_faisabilite`).
- **Banc** `tests/test_exigu_fix_1.py` — 12 tests (5 purs + 7 réels) **verts** : ignorance de la
  nouvelle cause, bascule `eligibility='unknown'`, seam, les 5 témoins, batch≡fiche, et la
  **garantie > 1 000 m²** (aucun `terrain_exigu` conservé sans preuve, lue de la trace
  `ctx.reexamen_exigu` que le moteur expose).
- **Non-régression** : `test_faisabilite` / `test_residuel*` / `test_exigu_grandes` /
  `test_algofix1*` (62 passés, 2 skips base) ; suite scénarios/scoring (237 passés).
- **Hook complet** (pre-push) : scan de secrets **propre** · front **tsc −b exit 0** · front
  **vitest 326/326** · Python unitaires (sans base) **3 253 passés / 50 skips** (skips = base
  applicative absente, attendus) · **cohérence 12 témoins : 6 passés, aucun écart (1 €/1 m²)**.
  (Un run du hook a connu un `Segmentation fault` natif à l'import de `sklearn` — flake
  d'environnement sans rapport avec ce correctif, qui ne touche ni sklearn ni `p_model` ; les
  unitaires repassent **3 253/3 253** à la relance, deux fois vert.)

---

## 6. Liste des identifiants à recalculer (déploiement §E)

La session de déploiement recalcule **seulement les parcelles `cause='terrain_exigu'`** du run
candidat. **La liste à recalculer se DÉFINIT par requête sur le run promu**, pas par un fichier figé :

```sql
SELECT p.idu FROM parcel_residuel_runs r JOIN parcels p ON p.id = r.parcel_id
WHERE r.run_seq = <seq du run candidat> AND r.cause = 'terrain_exigu';
```

Sur le VPS (seq 18) = **72 083** parcelles (DEPLOY-GROUPE-3 §E). Localement (run servi `q_v20`,
seq 17) = **64 757**. Deux fichiers (un IDU par ligne) sont joints comme artefacts :

- `reports/data/exigu_a_recalculer_run_servi.txt` — **64 757** IDU = TOUTES les `terrain_exigu` du
  run servi local (la liste littérale « toutes les parcelles terrain_exigu de l'île ») ;
- `reports/data/exigu_a_recalculer_gt1000.txt` — **9 933** IDU = les `terrain_exigu` > 1 000 m² du
  **code courant** (population du diagnostic + garantie ; inclut les témoins que le run servi, calculé
  sous l'ancien code, ne marquait pas encore exigu).

Le correctif ne *relâche* que la règle `terrain_exigu` (aucune parcelle hors de cet ensemble ne peut
*devenir* terrain_exigu ; cascade, socle et Signal inchangés), donc le recalcul partiel est valide
tel que décrit en §E. Les parcelles qui changent de verdict (régain ou à vérifier) rapportées au
recalcul : **~89 %** de la cohorte > 1 000 m² (8 845 / 9 933 = régain + à vérifier).

---

## 7. Diff

```
 src/labuse/exports/blocs/comparatif.py   |   1 +   (libellé court « assiette à vérifier »)
 src/labuse/faisabilite/db.py             | 154 +   (SQL robuste, _reexamen_exigu, seam, bloc condamné, trace)
 src/labuse/faisabilite/engine.py         |  20 +   (règle : cause assiette_a_verifier + libellé)
 src/labuse/scoring/scenarios_v2_build.py |   5 +-  (assiette_a_verifier → eligibility 'unknown')
 4 files changed, 178 insertions(+), 2 deletions(-)
```

Plus (hors `src/`, non servis par la prod) : `tests/test_exigu_fix_1.py` (12 tests),
`scripts/exigu_fix_1_mesure.py` + `scripts/exigu_fix_1_agg.py` (outils de mesure),
`reports/data/exigu_a_recalculer_*.txt` (listes d'IDU). `.gitignore` : les JSONL/logs de mesure
intermédiaires ne sont pas versionnés.

---

*Fin. Calcul seulement, aucun accès prod, pas de merge. Le ré-examen est actif par défaut
(`LABUSE_EXIGU_FIX`≠0) et strictement condamné à la branche `terrain_exigu` : le recalcul partiel
des parcelles `terrain_exigu` du run candidat reste valide.*

---

# Précisions avant merge (demandées par Vic)

## P1 — Sur quelle assiette les 59 % retrouvent une capacité, et doctrine RESIDUEL-2

**La capacité des régains est calculée sur un RETRAIT UNIFORME DE REPLI, pas sur le gabarit par
côté.** Quand le ré-examen conclut `regain`, le moteur pose `emprise = plus grand morceau d'un seul
tenant de l'inset séparatif uniforme (−recul)` et `assiette_source = 'residuel_legacy'`
(`db.py`) — il NE réutilise PAS la zone d'implantation du gabarit (qui s'était effondrée).

**Conséquence RESIDUEL-2 (automatique, vérifiée) :** `assiette_source='residuel_legacy'` ⇒
`assiette_qualifiee = False` (`scenarios_v2_build.py:324`) ⇒ dans l'Analyse V2, le scénario rend
`finish("TO_VERIFY", "ASSIETTE_A_CONFIRMER")` dès que la capacité est positive
(`scenarios_v2.py:608`). **Ces parcelles sont donc servies « À vérifier » (amber), JAMAIS
« Estimée » (vert)** — exactement la doctrine RESIDUEL-2 (« tant que l'application des règles n'est
pas prouvée »). La bande ferme reste vide ; une **bande provisoire** (consultable, non servie
comme sûre) est calculée sur la capacité de repli.

### Répartition des 9 933 (> 1 000 m²) dans l'Analyse V2 après correction

Dans l'Analyse LABUSE V2 — qui combine la **cascade étage-0** (exclusions dures sourcées) ET le
résiduel corrigé — les 9 933 (> 1 000 m², code courant) se répartissent :

| statut V2 (client) | n | sens |
|---|--:|---|
| **Hors de ce projet** (OUTSIDE_OBJECTIVE) | 8 599 (87 %) | exclusion DURE de cascade prouvée — **PAS** « trop étroit » |
| **À vérifier** (TO_VERIFY) | 1 082 (11 %) | assiette de repli (`ASSIETTE_A_CONFIRMER`) ou douteuse (`CALCUL_ASSIETTE_DOUTEUX`) |
| **Aucun ajout** (NO_MARGIN) | 174 (2 %) | régain mais saturé (C ≤ E) |
| À différer (DEFERRED) | 1 | AU fermée |

- **Bande FERME : vide** (aucune des 9 933 n'est servie « Estimée ») — conforme RESIDUEL-2.
- **Bande PROVISOIRE** (consultable, non servie comme sûre) des lignes À vérifier / Aucun ajout :
  A 50 · B 91 · C 63 · D 178 · 0 419.

Le 87 % « Hors de ce projet » **n'est pas** un faux « trop étroit » : la cascade exclut ces parcelles
**sur preuve sourcée** — zone A/N dominante (`zonage_plu_gpu`), PPR (`risques`), marchepied DPF,
forêt publique, SAFER, Parc National… (8 586 / 9 933 sont `cascade_exclue`). Ces grandes parcelles
résolvaient une **minuscule sous-zone U/AU** (d'où `terrain_exigu` au faisabilité) alors que la
parcelle entière est en zone dure : le verdict honnête est « Hors de ce projet », pas « terrain trop
étroit ». **Après correction, 0 des 9 933 n'affiche « trop étroit » dans l'Analyse, et 0 n'est servie
« Estimée ».**

> Deux niveaux à distinguer : au niveau **résiduel** (cause du moteur, §4) 59 % « retrouvent une
> capacité » (capacité calculée sur la sous-zone U/AU) ; au niveau **Analyse client** (cascade +
> résiduel) la cascade ramène 87 % à « Hors de ce projet ». Les deux sont cohérents — la capacité
> résiduelle sur la sous-zone existe, mais la cascade exclut la parcelle pour l'objectif logement.
> Dans les DEUX niveaux, le mot « trop étroit » a disparu.

### Les 5 témoins — capacité (SDP résiduelle) avant / dans q_v23 / après

| témoin | q_v20 (servi, ancien code) | q_v23 (candidat = code courant) | **après correction** |
|---|---|---|---|
| `97418000AY0416` | **1 828 m²** (capacité, « Estimée ») | `terrain_exigu` (0) | **1 831 m²**, statut **À vérifier** (bande prov. A) |
| `97411000DK0447` | **1 324 m²** (capacité) | `terrain_exigu` (0) | **1 077 m²**, **À vérifier** (bande prov. B) |
| `97415000CW0252` | **1 270 m²** (capacité) | `terrain_exigu` (0) | **1 270 m²**, **À vérifier** (bande prov. B) |
| `97419000AN0398` | 7 m² | `terrain_exigu` (0) | **`terrain_exigu`** (preuve : net 5 m², largeur 0,6 m ; bande prov. 0) |
| `97403000AL0258` | `terrain_exigu` (0) | `terrain_exigu` (0) | **`assiette_a_verifier`** → V2 **Hors de ce projet** (cascade : exclusion dure prouvée pré-empte la cause) |

Lecture : q_v23 (le candidat, code courant) avait transformé en `terrain_exigu` des parcelles que
q_v20 servait en capacité (effondrement gabarit + clip RESIDUEL-1) ; la correction **restitue** la
capacité que q_v23 retirait à tort, mais **plus honnêtement** (« À vérifier » sur assiette de repli,
plus jamais « Estimée » ferme).

### Pourquoi le gabarit par côté vide de GRANDES parcelles (causes du diagnostic, en clair)

Le gabarit applique les reculs **par limite** (voie ~5–6 m sur la façade sur rue, séparatifs sur
les autres) et **découpe** le PPR zone rouge + les ER/EBC. Il s'effondre quand la portion réellement
constructible est **étroite ou grevée**, par ordre de fréquence (diagnostic §2) :
1. **Portion U/AU réduite (6 725 / 9 933)** — parcelle à cheval : l'essentiel est en zone A/N, seule
   une bande U/AU est constructible ; les reculs par côté la vident. C'est le cas d'`AL0258`
   (0 % d'intersection U/AU géométrique malgré un zonage résolu « Ua »).
2. **Contraintes superposées (~2 990)** — PPR rouge découpé + PEB A/B / marchepied DPF / ravine /
   50 pas / ER / EBC : ce qui reste après découpe par côté est nul.
3. **Reculs / forme très découpée (269)** — géométrie tourmentée (ravines, concavités) : l'inset par
   côté mange tout, même sur 10 ha.

**Est-ce un défaut du gabarit à corriger à part ?** Le gabarit par côté n'est **pas faux** : il est
conservateur et juste là où la portion constructible est franche. Le défaut était **(a)** l'absence
de repli quand il s'effondre, et **(b)** le libellé « trop étroit » plaqué sur cet effondrement. Ce
correctif traite les deux (repli mesuré + cause honnête `à vérifier`). Savoir si le gabarit
sur-applique ses reculs par côté sur certaines géométries tourmentées est une **investigation
distincte** (revue du moteur gabarit lui-même), **hors périmètre** ici : le repli + « à vérifier »
empêchent déjà le mensonge, sans toucher au gabarit (qui sert, inchangé, toutes les parcelles
non-exiguës).

## P2 — Toutes les tailles : census complet par tranche (pas un échantillon)

Population : les **64 757** parcelles `terrain_exigu` du run servi (q_v20) — **TOUTES, pas un
échantillon**. « Après » = cause réellement servie par le moteur corrigé (fix ON).

| tranche | n | reste exiguë | retrouve une capacité | passe « à vérifier » |
|---|--:|--:|--:|--:|
| < 300 m² | 45 421 | 43 109 (95 %) | 608 (1 %) | 1 704 (4 %) |
| 300–600 m² | 6 026 | 2 152 (36 %) | 1 583 (26 %) | 2 286 (38 %) |
| 600–1 000 m² | 3 596 | 809 (22 %) | 1 280 (36 %) | 1 505 (42 %) |
| > 1 000 m² | 9 714 | 1 032 (11 %) | 5 741 (59 %) | 2 934 (30 %) |
| **total** | **64 757** | **47 102 (73 %)** | **9 212 (14 %)** | **8 429 (13 %)** |

(14 parcelles basculent `terrain_exigu` → `redhibitoire` au recalcul — contrainte dure confirmée,
négligeable, comptées hors des 3 colonnes.) **Lecture : plus la parcelle est GRANDE, plus le faux
« trop étroit » était fréquent** — sous 300 m² le verdict reste juste (95 % restent exiguës, à raison),
au-delà de 1 000 m² il s'effondrait (89 % changent de verdict). La colonne « retrouve une capacité »
est la cause RÉSIDUELLE ; au niveau Analyse client, la cascade en ramène une partie à « Hors de ce
projet » (cf. P1, sans jamais « trop étroit »).

## P3 — Tous les lecteurs de la cause `assiette_a_verifier`

Carte des lecteurs de `cause` et ce que chacun affiche pour la nouvelle valeur. Un test
(`tests/test_exigu_fix_1.py::test_tous_les_lecteurs_connaissent_assiette_a_verifier` +
`::test_potentiel_batir_assemble_motif_a_verifier`) **échoue si un lecteur ne la connaît pas** (ou
retombe sur un repli ferme « non constructible / surface insuffisante / trop étroit / rien à bâtir /
pas de potentiel » ou « éligible/Estimée »).

| Lecteur (surface produit) | Fonction | Affiche pour `assiette_a_verifier` |
|---|---|---|
| **Score LABUSE — bande** | `score_labuse._cause_nc` | cause non certaine → `NC_IGNORANCE` → **bande « NC » / « À vérifier »**, SDP ∅ |
| **Carte « Analyse LABUSE » (fiche)** | `scenarios_v2_build._eligibilite` + `scenarios_v2.scenario` | `eligibility='unknown'` → statut **TO_VERIFY « Analyse à compléter »** (amber) ; `OUTSIDE_OBJECTIVE` seulement si une exclusion DURE de cascade est prouvée |
| **Libellé cause (fiche, liste, Dossier PDF, Copilote)** | `engine.cause_libelle` (source unique) | « **Analyse incomplète — assiette constructible à vérifier (géométrie : contraintes, portion U/AU ou reculs à confirmer)** » |
| **Filtres** | bande/statut (pas de lecture directe de la cause) | hérite la **bande NC** → filtrable sous « À vérifier » |
| **Documents / exports (Comparatif, verdicts)** | `exports/blocs/comparatif._cause_court` | tag court « **assiette à vérifier** » |
| **Constructibilité (candidature/déclassement)** | `faisabilite/constructibilite.classify_constructibilite` | **`NON_VERIFIABLE`** « Constructibilité non vérifiable — assiette à vérifier » (∉ `_CONSTR_FERME` : **signalée, PAS déclassée** « surface insuffisante ») |
| **Motif fiche parcelle non-constructible** | `faisabilite/scenarios._cause_limite` | « **Assiette constructible à vérifier (géométrie).** » |
| **Avertissement verdict servi (liste/Flash)** | `verdict_servi._avertissement_non_constructible` | « **Assiette constructible à vérifier — potentiel à confirmer (géométrie).** » (jamais « rien à bâtir ») |
| **Potentiel à bâtir (fiche/Flash/PDF)** | `faisabilite/potentiel_batir._assemble` | motif « **Assiette constructible à vérifier (géométrie)** » |

**Note de déploiement (caches).** Trois lecteurs lisent des CACHES, pas le calcul live :
`potentiel_batir`/`est_ferme` lisent `parcel_residuel` **et** `parcel_constructibilite` ;
`classify_constructibilite` alimente le cache `parcel_constructibilite`. Pour que la nouvelle cause
s'affiche correctement (et ne reste pas sur l'ancien label « non constructible »), le déploiement
doit **recalculer `parcel_constructibilite`** pour les parcelles recalculées, en plus du résiduel /
Score / scénarios V2 du §E. (Les surfaces LIVE — fiche, Analyse V2 enrichie, Copilote — sont déjà
correctes sans recompute.)
