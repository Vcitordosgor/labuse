# LA BUSE — points de restauration (backups)

> **⚠️ Règle d'or : on ne committe JAMAIS un dump dans le dépôt — seulement sa documentation.**
> Les dumps (`*.dump`) vivent hors dépôt (`/var/backups/labuse`) ou dans `backups/` (gitignoré,
> cf. `.gitignore`). Ce fichier ne fait que **référencer** les backups (chemin, empreinte, contenu)
> pour pouvoir les retrouver et vérifier leur intégrité. Un dump pèse ~500 Mo : le versionner
> polluerait l'historique et fuiterait des données.

Format : `pg_dump -Fc` (custom, compressé). Restauration via `labuse restore-db` ou `pg_restore`.

---

## 🟢 Baseline courant — « post-Étape A batch 3 : Bras-Panon · Les Avirons · Le Port · Sainte-Suzanne · Petite-Île · Sainte-Marie re-cascadées, 24/24 communes, 17 gold » (2026-06-27)

Point de restauration **propre et recommandé** après le **mini-batch 3 de généralisation de l'Étape A PPR** :
re-cascade **seule** de **6 communes gold** — **Bras-Panon (97402)**, **Les Avirons (97401)**, **Le Port
(97407)**, **Sainte-Suzanne (97420)**, **Petite-Île (97405)**, **Sainte-Marie (97418)** — qui précédaient
l'Étape A (PPR faible = 0 avant). **Sans ré-import, sans changement de code / config / scoring / seuil 65 /
Étape B.** **Saint-Denis & Saint-André exclus (décision).** La base reste **24/24 communes** et **17 gold** ; les
6 communes **restent gold**. Opportunités **1 581 → 1 538** (net **−43**) : **+9 via l'Étape A** (déflag marginal,
**0 perte imputable**) **+ 161 re-scoring montant** (dont **Le Port +157**, cf. ⚠️ ci-dessous), **−213 faux
positifs assainis** (`declassement` déjà bâti / micro). **Effet dominant = re-homogénéisation** de communes
cascadées en 06-22/06-23 au code courant (qualité ↑, volume ↓ marginal). État figé : `main` à `88e0b85`. **Aucun
changement scoring / seuil 65 / PPR Étape B / config gold.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-stepa-batch3-17gold-24communes-20260627-085453.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-stepa-batch3-17gold-24communes-20260627-085453.dump` |
| **Date / heure** | **2026-06-27 08:54:53 UTC** |
| **Taille** | **1189 Mo** (1 188 591 528 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `aed21860dc11408844f1745e993300882d33e5d63838392bead18da248c28479` |
| **Sidecar** | `…-085453.dump.sha256` |

### Contenu du baseline (post-Étape A batch 3, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`88e0b85`** (`docs: merge PPR step A batch 3 report`) — scoring **inchangé** (rules `2b45db742f40`) ; batch = docs-only + re-cascade DB |
| Communes en base | **24 / 24** |
| Parcelles | **431 663** |
| Communes **gold** (17) | inchangées — les **6 communes du batch restent gold** (re-cascade, pas de re-passage gold) |
| **Bras-Panon (re-cascadée Étape A)** | 6 041 parc. · 100 % évaluées · **opp 210→155 (−55)** · **PPR fort 1 624→1 425** · **PPR faible 0→437** · **+1 via Étape A** · **−56 assainis** |
| **Les Avirons (re-cascadée Étape A)** | 8 611 parc. · 100 % évaluées · **opp 104→93 (−11)** · **PPR fort 3 883→3 403** · **PPR faible 0→1 013** · **+1 via Étape A** · **−12 assainis** |
| **Le Port (re-cascadée Étape A)** | 10 195 parc. · 100 % évaluées · **opp 74→236 (+162)** · **PPR fort 836→761** · **PPR faible 0→112** · **+5 via Étape A** · **+157 re-scoring** (cf. ⚠️) |
| **Sainte-Suzanne (re-cascadée Étape A)** | 12 527 parc. · 100 % évaluées · **opp 321→231 (−90)** · **PPR fort 5 633→4 988** · **PPR faible 0→1 157** · **+1 via Étape A** · **−91 assainis** |
| **Petite-Île (re-cascadée Étape A)** | 13 137 parc. · 100 % évaluées · **opp 115→116 (+1)** · **PPR fort 5 650→4 856** · **PPR faible 0→1 453** · **+1 via Étape A** |
| **Sainte-Marie (re-cascadée Étape A)** | 16 746 parc. · 100 % évaluées · **opp 757→707 (−50)** · **PPR fort 9→1** · **PPR faible 0→41** · **+4 re-scoring** · **−54 assainis** |
| Non-gold restants (7) | Saint-Leu (provisoire AGORAH 2007) · Saint-Philippe (PLU absent GPU) · La Plaine-des-Palmistes · Les Trois-Bassins · Sainte-Rose · Salazie · Cilaos |

> **Mini-batch 3 (généralisation Étape A)** : re-cascade `evaluate_commune` séquentielle (Bras-Panon → Les Avirons
> → Le Port → Sainte-Suzanne → Petite-Île → Sainte-Marie), **67 257 parcelles, sans ré-import**. L'Étape A a
> déflagué les parcelles PM1-marginales → **PPR faible 0 → 4 213** → **+9 opportunités** réelles (via flag
> marginal), **0 perte imputable**. La re-cascade a aussi ré-appliqué le code courant → **−213 anciennes
> opportunités retirées** (`declassement` déjà bâti / micro) **+ 161 re-scoring montant**. **Net 1 581 → 1 538 =
> −43** (re-homogénéisation, qualité ↑). **⚠️ Le Port +157 hors Étape A** : montée de **complétude uniforme +10**
> (74→84) sur **9 903 / 10 195 parcelles** (couche de données absente à la cascade du 06-22, désormais présente) →
> 157 parcelles `à creuser` (score 49–64) franchissent le seuil 65 → `opportunité` (**5/162 seulement** portent le
> flag marginal Étape A). Contrôle **read-only** (échantillon 40 parcelles) : profils **sains** (zone U/AUc, 0 PPR,
> non bâti, DVF positive) → **+157 ACCEPTABLES** comme re-homogénéisation au scoring/complétude courant — **dérive
> de complétude inter-version** à traiter dans le chantier d'optimisation (non bloquant, **pas un effet Étape A**).
> Détail : `docs/communes/PPR_STEP_A_BATCH3.md`. Backup **pré-batch 3** : **aucun créé** — la baseline pré-batch 3
> est le backup stable **post-batch 2** (`…batch2-…230000.dump`).

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK (rc=0) — **175 entrées TOC** (+ 15 lignes d'en-tête `;` = 190 lignes, convention
  des baselines antérieurs) ; tables `parcels`, `spatial_layers`, `cascade_results`, `parcel_evaluations`,
  `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-085453.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=88e0b85` (= `origin/main`), working tree
  clean, **24 communes / 431 663 parcelles**, **17 gold** (les 6 du batch **restent gold**), opp **Bras-Panon 155 /
  Les Avirons 93 / Le Port 236 / Sainte-Suzanne 231 / Petite-Île 116 / Sainte-Marie 707** (Σ 1 538 ; canonique =
  dernière éval/parcelle). **Aucun changement scoring / seuil 65 / PPR Étape B / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-stepa-batch3-17gold-24communes-20260627-085453.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-stepa-batch3-17gold-24communes-20260627-085453.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, les 6 du batch re-cascadées Étape A)
```

---

## Baseline précédent — « post-Étape A batch 2 : Saint-Louis · Saint-Joseph · Saint-Benoît re-cascadées, 24/24 communes, 17 gold » (2026-06-26)

Point de restauration **propre et recommandé** après le **mini-batch 2 de généralisation de l'Étape A PPR** :
re-cascade **seule** de **3 communes gold** — **Saint-Louis (97414)**, **Saint-Joseph (97412)**, **Saint-Benoît
(97410)** — qui précédaient l'Étape A (PPR faible = 0 avant). **Sans ré-import, sans changement de
code / config / scoring / seuil 65 / Étape B.** La base reste **24/24 communes** et **17 gold** ; les 3 communes
**restent gold**. Opportunités **1 593 → 1 596** (net **+3**) : **+26 via l'Étape A** (déflag marginal) **+ 2
re-scoring**, **−25 faux positifs assainis** (`declassement` / `prescription_plu`) — **qualité ↑, volume stable**
(batch quasi net-neutre, bien plus doux que batch 1 à −136). État figé : `main` à `bfdb3a1`. **Aucun changement
scoring / seuil 65 / PPR Étape B / config gold.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-stepa-batch2-17gold-24communes-20260626-230000.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-stepa-batch2-17gold-24communes-20260626-230000.dump` |
| **Date / heure** | **2026-06-26 23:00:00 UTC** |
| **Taille** | **1188 Mo** (1 187 865 456 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `5680393d09ba903d821ccdeefe33590ff5f0c9b79efddfae2b19eed2a8c734ae` |
| **Sidecar** | `…-230000.dump.sha256` |

### Contenu du baseline (post-Étape A batch 2, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`bfdb3a1`** (`docs: merge PPR step A batch 2 report`) |
| Communes en base | **24 / 24** |
| Parcelles | **431 663** |
| Communes **gold** (17) | inchangées — les **3 communes du batch restent gold** (re-cascade, pas de re-passage gold) |
| **Saint-Louis (re-cascadée Étape A)** | 29 241 parc. · 100 % évaluées · **opp 474→489 (+15)** · **PPR fort 8 214→7 163** · **PPR faible 0→2 131** · **+14 via Étape A** |
| **Saint-Joseph (re-cascadée Étape A)** | 28 959 parc. · 100 % évaluées · **opp 530→514 (−16, assainissement)** · **PPR fort 9 948→8 712** · **PPR faible 0→2 536** · **+5 via Étape A** |
| **Saint-Benoît (re-cascadée Étape A)** | 21 671 parc. · 100 % évaluées · **opp 589→593 (+4)** · **PPR fort 7 148→5 808** · **PPR faible 0→2 829** · **+7 via Étape A** |
| Non-gold restants (7) | Saint-Leu (provisoire AGORAH 2007) · Saint-Philippe (PLU absent GPU) · La Plaine-des-Palmistes · Les Trois-Bassins · Sainte-Rose · Salazie · Cilaos |

> **Mini-batch 2 (généralisation Étape A)** : re-cascade `evaluate_commune` séquentielle (Saint-Louis → Saint-Joseph
> → Saint-Benoît), **79 871 parcelles, sans ré-import**. L'Étape A a déflagué les parcelles PM1-marginales →
> **PPR faible 0 → 7 496** → **+26 opportunités** réelles (via flag marginal), **0 perte imputable**. La re-cascade
> a aussi ré-appliqué le code courant → **−25 anciennes opportunités retirées** (21 `declassement` déjà bâti/micro,
> 1 `prescription_plu` emplacement réservé, 3 re-scoring borderline). **Net 1 593 → 1 596 = +3** (quasi neutre,
> qualité ↑). **Note perf** : Saint-Joseph/Saint-Benoît **CPU-bound géométrique** (communes denses, ~5–10× plus
> lentes) — **pas une régression** ; un **`ANALYZE` de maintenance** (stats seules, **zéro impact verdicts**) a été
> appliqué, et Saint-Joseph **re-cascadée en entier** (idempotent) jusqu'à 100 % propre. Détail :
> `docs/communes/PPR_STEP_A_BATCH2.md`. Backup **pré-batch** :
> `labuse-pre-stepa-batch2-saint-louis-saint-joseph-saint-benoit-20260626-140509.dump` (SHA `78ccbb82…f808a`) —
> **PURGÉ le 2026-06-27** (sur GO explicite, pour libérer l'espace disque nécessaire au backup post-batch 3) :
> batch 2 validé / mergé et couvert par le baseline **post-batch 2** ci-dessous — ce point de retour pré-run n'a
> plus d'utilité critique. État restaurable = baselines `post-*`.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — **175 entrées TOC** (+ 15 lignes d'en-tête `;` = 190 lignes, convention des
  baselines antérieurs) ; tables `parcels`, `spatial_layers`, `cascade_results`, `parcel_evaluations`,
  `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-230000.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=bfdb3a1` (= `origin/main`), working tree
  clean, **24 communes / 431 663 parcelles**, **17 gold** (les 3 du batch **restent gold**), opp **Saint-Louis 489 /
  Saint-Joseph 514 / Saint-Benoît 593**. **Aucun changement scoring / seuil 65 / PPR Étape B / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). **Saint-Joseph**
> porte en plus le set du run partiel (~10 000) + le run complet (28 959) — verdict canonique = la dernière éval.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-stepa-batch2-17gold-24communes-20260626-230000.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-stepa-batch2-17gold-24communes-20260626-230000.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, les 3 du batch re-cascadées Étape A)
```

---

## Baseline précédent — « post-Étape A batch 1 : Le Tampon · La Possession · L'Étang-Salé re-cascadées, 24/24 communes, 17 gold » (2026-06-26)

Point de restauration **propre et recommandé** après le **mini-batch 1 de généralisation de l'Étape A PPR** :
re-cascade **seule** de **3 communes gold** — **Le Tampon (97422)**, **La Possession (97408)**, **L'Étang-Salé
(97404)** — qui précédaient l'Étape A (PPR faible = 0 avant). **Sans ré-import de couches, sans changement de
code / config / scoring / seuil 65 / Étape B.** La base reste **24/24 communes** et **17 gold** ; les 3 communes
**restent gold** (re-cascade, pas de re-passage gold). Opportunités **1 702 → 1 566** (net **−136**) : **+54 via
l'Étape A** (PPR marginal < 10 % déflagué) **+ 1 re-scoring montant**, **−191 faux positifs assainis** par
`declassement` / `prescription_plu` (déjà bâti, micro-parcelles, emplacements réservés — **assainissement qualité,
pas une perte**). État figé : `main` à `a2fb54f`. **Aucun changement scoring / seuil 65 / PPR Étape B / config gold.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-stepa-batch1-17gold-24communes-20260626-130808.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-stepa-batch1-17gold-24communes-20260626-130808.dump` |
| **Date / heure** | **2026-06-26 13:08:08 UTC** |
| **Taille** | **1187 Mo** (1 187 117 140 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `c1566da80a84a21261e98c5b30d2f9d482c1e9dc9a591fc6fe1564b6c6fa748b` |
| **Sidecar** | `…-130808.dump.sha256` |

### Contenu du baseline (post-Étape A batch 1, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`a2fb54f`** (`docs: merge PPR step A batch 1 report`) |
| Communes en base | **24 / 24** |
| Parcelles | **431 663** |
| Communes **gold** (17) | inchangées — les **3 communes du batch restent gold** (re-cascade, pas de re-passage gold) |
| **Le Tampon (re-cascadée Étape A)** | 42 756 parc. · 100 % évaluées · **opp 749→657** · **PPR fort 12 421→9 760** · **PPR faible 0→4 342** · **+23 via Étape A** (+1 re-scoring) · **−116 faux positifs assainis** |
| **La Possession (re-cascadée Étape A)** | 13 338 parc. · 100 % évaluées · **opp 611→620 (+9, seule nette positive)** · **PPR fort 4 294→3 467** · **PPR faible 0→1 251** · **+29 via Étape A** · **−20 assainis** |
| **L'Étang-Salé (re-cascadée Étape A)** | 9 070 parc. · 100 % évaluées · **opp 342→289** · **PPR fort 3 646→3 305** · **PPR faible 0→837** · **+2 via Étape A** · **−55 assainis** |
| Non-gold restants (7) | Saint-Leu (provisoire AGORAH 2007) · Saint-Philippe (PLU absent GPU) · La Plaine-des-Palmistes · Les Trois-Bassins · Sainte-Rose · Salazie · Cilaos |

> **Mini-batch 1 (généralisation Étape A)** : re-cascade `evaluate_commune` séquentielle (Le Tampon → La Possession
> → L'Étang-Salé), **65 164 parcelles, sans ré-import**. L'Étape A a déflagué les parcelles PM1-marginales →
> **PPR faible 0 → 6 430** → **+54 opportunités** réelles (via flag marginal), **0 perte imputable**. La re-cascade
> a aussi ré-appliqué le code courant → **−191 anciennes opportunités retirées** : **184 par `declassement`**
> (micro-parcelles < 100 m² / **déjà bâti** BD TOPO « ensemble bâti »), **2 par `prescription_plu`** (emplacements
> réservés ER : carrefour 77 % / création de voie 100 %), **5 par re-scoring** borderline sous le seuil 65 ;
> **score inchangé** (statut corrigé). **Symétrie de seuil** : **+1** parcelle re-scorée vers le haut (Le Tampon
> 29383 : 64 → 65, sans PPR) → **gains totaux +55**, soit **net 1 702 → 1 566 = −136** (= 55 − 191). **Assainissement
> qualité** (leads plus fiables), pas une perte commerciale. Détail + contrôle de cohérence arithmétique :
> `docs/communes/PPR_STEP_A_BATCH1.md`. Backup **pré-batch** :
> `labuse-pre-stepa-batch1-tampon-possession-etang-sale-20260626-101136.dump` (SHA `eb25b4da…29473`) —
> **PURGÉ le 2026-06-27** (sur GO explicite, pour libérer l'espace disque nécessaire au backup post-batch 3) :
> batch 1 validé / mergé et couvert par le baseline **post-batch 1** ci-dessous — ce point de retour pré-run n'a
> plus d'utilité critique. État restaurable = baselines `post-*`.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — **175 entrées TOC** (= backup pré-batch 175, identique → aucun objet perdu ;
  les baselines antérieurs notaient « 190 » = ces 175 entrées **+ 15 lignes d'en-tête `;`**, même contenu, simple
  différence de comptage) ; tables `parcels`, `spatial_layers`, `cascade_results`, `parcel_evaluations`,
  `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-130808.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=a2fb54f` (= `origin/main`), working tree
  clean, **24 communes / 431 663 parcelles**, **17 gold** (les 3 du batch **restent gold**), opp **Le Tampon 657 /
  La Possession 620 / L'Étang-Salé 289**. **Aucun changement scoring / seuil 65 / PPR Étape B / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). **Le Tampon,
> La Possession et L'Étang-Salé** portent désormais un nouveau set d'éval (Étape A) en plus des sets antérieurs —
> verdict canonique = la dernière (Étape A).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-stepa-batch1-17gold-24communes-20260626-130808.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-stepa-batch1-17gold-24communes-20260626-130808.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, les 3 du batch re-cascadées Étape A)
```

---

## Baseline précédent — « post-Saint-Pierre PPR Étape A : 24/24 communes, 17 gold (Saint-Pierre re-cascadée, assainissement qualité) » (2026-06-26)

Point de restauration **propre et recommandé** après le **pilote de généralisation de l'Étape A PPR** (re-cascade
**seule** de Saint-Pierre, sans ré-import ni changement de code). La base reste **24/24 communes** et **17 gold** ;
**Saint-Pierre reste gold** mais ses verdicts sont **re-cascadés** : opportunités **1 534 → 1 380**, dont **+28 via
l'Étape A** (PPR marginal < 10 % déflagué) et **−182 faux positifs « déjà bâti » / micro-parcelles retirés** par la
couche `declassement` (**assainissement qualité, pas une perte** ; 120/182 déjà non-opp au baseline 06-08). État
figé : `main` à `ef65998`. **Aucun changement scoring / seuil 65 / PPR Étape B.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-saint-pierre-ppr-stepa-17gold-24communes-20260626-064042.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-saint-pierre-ppr-stepa-17gold-24communes-20260626-064042.dump` |
| **Date / heure** | **2026-06-26 06:40:42 UTC** |
| **Taille** | **1186 Mo** (1 186 477 225 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `f2722380e6ec72da4f18daf1c8936935a675c3374b027868fc34328013425f7b` |
| **Sidecar** | `…-064042.dump.sha256` |

### Contenu du baseline (post-Saint-Pierre PPR Étape A, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`ef65998`** (`docs: merge Saint-Pierre PPR Step A pilot report`) |
| Communes en base | **24 / 24** |
| Parcelles | **431 663** |
| Communes **gold** (17) | inchangées — **Saint-Pierre reste gold** (re-cascade, pas de re-passage gold) |
| **Saint-Pierre (re-cascadée Étape A)** | 42 425 parc. · 100 % évaluées · **opp 1 380** (était 1 534) · **PPR fort 9 835→8 219** · **PPR faible 0→2 705** · **+28 via Étape A** · **−182 faux positifs « déjà bâti » assainis** |
| **Saint-Leu** | analysée provisoirement (AGORAH 2007, **non-gold**) — inchangée |
| Non-gold restants (7) | Saint-Leu (provisoire) · Saint-Philippe (PLU absent) · La Plaine-des-Palmistes · Les Trois-Bassins · Sainte-Rose · Salazie · Cilaos |

> **Pilote Saint-Pierre (généralisation Étape A)** : re-cascade `evaluate_commune` (42 425 parcelles, sans ré-import).
> L'Étape A a déflagué **2 705** parcelles PM1-marginales (PPR fort 9 835→8 219) → **+28 opportunités** réelles, 0 perte
> imputable. La re-cascade a aussi ré-appliqué le code courant (`rules_version 2b45db→fb6a54`) → **−182 anciennes
> opportunités retirées** par la couche `declassement` : **micro-parcelles (<100 m²) et parcelles déjà bâties (BD TOPO
> « ensemble bâti »)**, **score inchangé** (statut corrigé). **120/182 étaient déjà non-opp au baseline 06-08** →
> correction, pas régression. **Net 1 534→1 380 = assainissement qualité** (leads plus fiables). Détail :
> `docs/communes/saint_pierre_PPR_STEP_A.md`. Backup pré-run : `labuse-pre-saint-pierre-ppr-stepa-20260625-213017.dump`
> (SHA `5c3ef253…de830`) — **⚠️ PURGÉ le 2026-06-26** : point de retour d'un pilote **terminé et accepté** (pas de
> rollback) ; **plus sur disque** ; état restaurable = **ce baseline `post-Saint-Pierre`** (l'état pré-pilote =
> baseline `post-Saint-Leu`, conservé).

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `cascade_results`,
  `parcel_evaluations`, `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-064042.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=ef65998`, working tree clean,
  **24 communes / 431 663 parcelles**, **17 gold** (Saint-Pierre **reste gold**), Saint-Pierre **1 380 opportunités**.
  **Aucun changement scoring / seuil 65 / PPR Étape B / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). **Saint-Pierre**
> porte désormais 3 jeux d'éval (06-08 / 06-21 / 06-26) — verdict canonique = la dernière (Étape A).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-saint-pierre-ppr-stepa-17gold-24communes-20260626-064042.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-saint-pierre-ppr-stepa-17gold-24communes-20260626-064042.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, Saint-Pierre 1380 opp)
```

---

## Baseline précédent — « post-Saint-Leu provisoire : 24/24 communes, 17 gold + Saint-Leu analysée (AGORAH 2007, non-gold) » (2026-06-25)

Point de restauration **propre et recommandé** après l'**analyse PROVISOIRE de Saint-Leu (97413)** via le repli
**AGORAH PLU 2007** : la base reste à **24/24 communes** et **17 gold** ; Saint-Leu (22 959 parcelles, 3ᵉ marché
DVF du département) est désormais **analysée (100 % évaluée)** mais **reste NON-gold** (zonage 2007 en révision).
État figé : `main` à `6d4f615` (`docs: merge provisional Saint-Leu AGORAH run report`). **Aucun changement
scoring / seuil 65 / PPR.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-saint-leu-provisional-17gold-24communes-20260625-204545.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-saint-leu-provisional-17gold-24communes-20260625-204545.dump` |
| **Date / heure** | **2026-06-25 20:45:45 UTC** |
| **Taille** | **1186 Mo** (1 186 010 566 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `97d165a332faa742be1d92665a48a1f4a609264532f1cb1ef9c1769439f174cb` |
| **Sidecar** | `…-204545.dump.sha256` |

### Contenu du baseline (post-Saint-Leu provisoire, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`6d4f615`** (`docs: merge provisional Saint-Leu AGORAH run report`) |
| Communes en base | **24 / 24** |
| Parcelles | **431 663** |
| Communes **gold** (17) | inchangées — **Saint-Leu NON-gold** (analyse provisoire) |
| **Saint-Leu (analysée provisoire)** | 22 959 parc. · **100 % évaluées** · zonage **AGORAH PLU 2007** (`97413_20070226`, 368 zones, couverture propre **99,60 %**) · bâti 0→35 339 · pente 0→6 582 · voirie 5 000→11 761 · **976 opportunités PROVISOIRES** (4,3 %) · DVF 1 307 (geo-dvf 2021-2025) |
| Non-gold restants (7) | **Saint-Leu** (provisoire AGORAH 2007) · Saint-Philippe (PLU absent GPU) · La Plaine-des-Palmistes · Les Trois-Bassins · Sainte-Rose · Salazie · Cilaos |

> **Saint-Leu** (97413, vague 2, **re_couches_re_cascade via repli AGORAH 2007**) : commune côtière à fort enjeu
> commercial, débloquée pour analyse alors que son PLU est **absent du GPU** (`DU_97413` = 0). Repli AGORAH
> `97413_20070226` (datappro 2007-02-26, 368 zones, couverture parcellaire **99,60 %**). **RESTE NON-gold** car le
> PLU 2007 est en révision (avis Région défavorable, approbation 2ᵉ sem. 2026 non stabilisée, géométrie révisée non
> publiée en SIG) → **les 976 opportunités sont PROVISOIRES**, à recalculer dès publication du PLU révisé. Détail +
> disclaimer : `docs/communes/saint_leu_RESULTS.md`. Backup pré-run : `labuse-pre-saint-leu-agorah-20260625-185202.dump`
> (SHA `35173977…0e9d2c`) — **⚠️ PURGÉ le 2026-06-26** : point de retour d'un run **terminé / validé / mergé** ;
> **plus sur disque** ; état restaurable = baseline `post-Saint-Leu` (l'état pré-run = baseline `post-Entre-Deux`, conservé).

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `cascade_results`,
  `parcel_evaluations`, `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-204545.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=6d4f615`, working tree clean,
  **24 communes / 431 663 parcelles**, **17 gold** (Saint-Leu **non-gold**), Saint-Leu **22 959/22 959 évaluées**.
  **Aucun changement scoring / seuil 65 / PPR / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). **Saint-Leu**
> porte une éval AGORAH **provisoire** (set unique — elle n'était pas évaluée avant).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-saint-leu-provisional-17gold-24communes-20260625-204545.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-saint-leu-provisional-17gold-24communes-20260625-204545.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, Saint-Leu non-gold/provisoire)
```

---

## Baseline précédent — « post-Entre-Deux gold : 24/24 communes, 17 gold (Entre-Deux réparée) » (2026-06-25)

Point de restauration **propre et recommandé** après le **passage gold d'Entre-Deux (97403)**, réparée puis
validée au standard : la base reste à **24/24 communes** (couverture Réunion complète) et passe à **17 communes
gold**. Entre-Deux avait une évaluation **périmée** (bâti=0) ; un `re_couches_re_cascade` + **réparation ciblée
de la couche `pente`** (échec ALTI transitoire au 1er run → re-fetch ciblé) l'ont fiabilisée. État figé : `main`
à `096cd87` (`LOT6: validate Entre-Deux gold`). **Aucun changement scoring / seuil 65 / PPR.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-entredeux-17gold-24communes-20260625-164553.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-entredeux-17gold-24communes-20260625-164553.dump` |
| **Date / heure** | **2026-06-25 16:45:53 UTC** |
| **Taille** | **1160 Mo** (1 159 602 234 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `6dc66e48eec84148239ab8a0009297b7bc79ae0253cee2ec07cdaaaaa2164a7d` |
| **Sidecar** | `…-164553.dump.sha256` |

### Contenu du baseline (post-Entre-Deux gold, 24 communes / 17 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`096cd87`** (`LOT6: validate Entre-Deux gold`) |
| Communes en base | **24 / 24** (couverture Réunion complète) |
| Parcelles | **431 663** |
| Communes **gold** (17) | les 16 précédentes + **Entre-Deux** (97403, réparée) |
| **Entre-Deux (nouvelle gold)** | bâti 0→**46 493** · pente réparée **4 140** · voirie 5 000→**8 802** · géom invalide 1→**0** · PLU propre 97403 **100 %** · opp **1** (0,0 %) · fpp 0→**3 729** |
| Non-gold restants (7) | Saint-Leu, Saint-Philippe (PLU absent GPU) · La Plaine-des-Palmistes, Les Trois-Bassins, Sainte-Rose, Salazie, Cilaos (faible opportunité structurelle) |

> **Entre-Deux** (97403, vague 6, **re_couches_re_cascade + réparation pente ciblée**) : l'évaluation initiale était
> périmée (bâti=0, fpp=0, 9 fausses opportunités). Le 1er run a tout réparé sauf `pente` (échec transitoire RGE ALTI,
> couche critique → exit 1) ; **pas de rollback** (décision), puis **re-fetch ciblé `pente`** (4 140 cellules,
> couverture parcellaire 100 %) + **re-cascade**. Verdicts finaux fiables : opp **1** · à creuser **1 642** ·
> écartée **940** · faux positif probable **3 729**. Détails : `docs/communes/entre_deux_RESULTS.md`. Backups de la
> réparation : `labuse-pre-entre-deux-20260625-140800.dump` + `labuse-pre-entre-deux-pente-fix-20260625-143536.dump`
> — **⚠️ PURGÉS le 2026-06-25** : points de retour pré-run / pré-fix d'une opération **terminée, validée et mergée** ;
> **plus disponibles sur disque** ; état restaurable courant = **ce baseline `post-Entre-Deux 17 gold`**.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `cascade_results`,
  `parcel_evaluations`, `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-164553.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=096cd87`, working tree clean,
  **24 communes / 431 663 parcelles**, **17 gold** (Entre-Deux incluse), Entre-Deux bâti 46 493 / pente 4 140.
  **Aucun changement scoring / seuil 65 / PPR ; config gold = seul le passage Entre-Deux validé.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). Entre-Deux porte
> l'ancien set (bâti=0) + le set réparé (bâti+pente) — verdict canonique = dernière éval.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-entredeux-17gold-24communes-20260625-164553.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-entredeux-17gold-24communes-20260625-164553.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 17, Entre-Deux incluse)
```

---

## Baseline précédent — « post-Cilaos : import complet (24/24 communes — couverture Réunion totale) » (2026-06-25)

Point de restauration **propre et recommandé** après l'**import complet de Cilaos (97424)**, **dernière
commune** de La Réunion : la base atteint la **complétude 24/24** — **toutes les communes du département sont
désormais présentes et enrichies au standard**. Cilaos est un **cirque** (cœur de parc national, forêt
publique, relief fort) : importée et **100 % évaluée**, **4 opportunités (0,1 %)** — quasi-nul, attendu.
État figé : `main` à `e6f045d` (`docs: merge Cilaos import complet report`). **Cilaos n'est PAS marquée gold**
(import de complétude) → **gold count inchangé = 16**, scoring et seuil 65 inchangés. **Salazie inchangée.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-cilaos-24communes-20260625-134819.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-cilaos-24communes-20260625-134819.dump` |
| **Date / heure** | **2026-06-25 13:48:19 UTC** |
| **Taille** | **1144 Mo** (1 143 550 250 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `a05900d98d4acf5a9ecbaab34e6539043390c3c4c0eca98276f532de4b80174f` |
| **Sidecar** | `…-134819.dump.sha256` |

### Contenu du baseline (post-Cilaos, 24 communes — COMPLET)

| Élément | Valeur |
|---|---|
| `main` (code) | **`e6f045d`** (`docs: merge Cilaos import complet report`) |
| Communes en base | **24 / 24** (toutes les communes de La Réunion) |
| Parcelles | **431 663** (425 103 + 6 560) |
| Communes **gold** (16) | inchangées — **Cilaos & Salazie non-gold** (imports de complétude) |
| **Importée complétude (1)** | **Cilaos** (`97424`, 6 560 parc., 100 % évaluées, **4 opportunités / 0,1 %** — cirque) |
| **Communes absentes** | **aucune** — couverture Réunion totale atteinte |

> **Cilaos** (vague 6, INSEE 97424, **import_complet** d'une commune absente ; `strategie: attendre`
> surclassée par décision de complétude) : 6 560 parcelles · 13 sections · 100 % évaluées · bâti **5 584** ·
> voirie **2 327** · pente **4 080** · zonage propre **DU_97424 100 %** (IDURBA dominant `97424_plu_20240213`,
> 149 zones · 232 au total avec limitrophes) · `plu_gpu_prescription` **255** · **PPR 2** · SAR **31** ·
> ravines **402** · DVF **128** · `parc_national` **3** + `foret_publique` **9** (cirque, cœur de parc).
> 0 doublon de couche. Verdicts : opportunité **4** · à creuser **2 074** · écartée **1 434** · faux positif
> probable **3 048** (taux **0,1 %**, attendu pour le cirque). Détail : `docs/communes/cilaos_RESULTS.md`.
> Backup **pré-commune** : `labuse-pre-cilaos-20260625-130353.dump` (SHA `83bdd2f9…1148b`) — **⚠️ PURGÉ le 2026-06-25** :
> point de retour d'une opération **terminée / validée / mergée** ; **plus sur disque** ; restaurable courant = baseline `post-Entre-Deux 17 gold`.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `cascade_results`,
  `parcel_evaluations`, `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-134819.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=e6f045d`, working tree clean,
  **24 communes / 431 663 parcelles**, **16 gold** (inchangé), Cilaos présente / 100 % évaluée / **non-gold**,
  **Salazie inchangée (7 035)**. **Aucun changement scoring / seuil 65 / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).
> **Cilaos & Salazie** sont des imports uniques (sans stale).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-cilaos-24communes-20260625-134819.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-cilaos-24communes-20260625-134819.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=24 parcels=431663 (gold = 16, couverture Réunion totale)
```

---

## Baseline précédent — « post-Salazie : import complet (23/24 communes, Cilaos seule absente) » (2026-06-25)

Point de restauration **propre et recommandé** après l'**import complet de Salazie (97421)** pour la
**complétude 24/24** de la couverture Réunion : la base passe à **23 communes** — **seule Cilaos (97424)
reste absente**. Salazie est un **cirque** (cœur de parc national + forêt publique) : importée et **100 %
évaluée**, **0 opportunité** (attendu). État figé : `main` à `2bd9a82` (`docs: merge Salazie import complet
report`). **Salazie n'est PAS marquée gold** (import de complétude) → **gold count inchangé = 16**, scoring
et seuil 65 inchangés.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-salazie-23communes-20260625-125248.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-salazie-23communes-20260625-125248.dump` |
| **Date / heure** | **2026-06-25 12:52:48 UTC** |
| **Taille** | **1119 Mo** (1 119 162 540 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `efc6ac5220ad9ebcfa20d7df544b4590d0aa65fc54c80fe6c3aa318c6f72423b` |
| **Sidecar** | `…-125248.dump.sha256` |

### Contenu du baseline (post-Salazie, 23 communes)

| Élément | Valeur |
|---|---|
| `main` (code) | **`2bd9a82`** (`docs: merge Salazie import complet report`) |
| Communes en base | **23** (22 + **Salazie**) |
| Parcelles | **425 103** (418 068 + 7 035) |
| Communes **gold** (16) | inchangées — **Salazie non-gold** (import de complétude) |
| **Importée complétude (1)** | **Salazie** (`97421`, 7 035 parc., 100 % évaluées, **0 opportunité** — cirque) |
| **Seule absente (1)** | **Cilaos** (`97424`) — dernier cirque ; complétude 24/24 en attente |

> **Salazie** (vague 6, INSEE 97421, **import_complet** d'une commune absente ; `strategie: attendre`
> surclassée par décision de complétude) : 7 035 parcelles · 32 sections · 100 % évaluées · bâti **7 410** ·
> voirie **2 736** · pente **5 986** · zonage propre **DU_97421 100 %** (336 zones) · `plu_gpu_prescription`
> **879** · **PPR 2** · SAR **57** · ravines **629** · DVF **109** · `parc_national` **3** + `foret_publique`
> **13** (cirque, cœur de parc). 0 doublon de couche. Verdicts : opportunité **0** · à creuser **836** ·
> écartée **761** · faux positif probable **5 438** (taux d'opportunité **0,0 %**, attendu pour le cirque).
> Détail : `docs/communes/salazie_RESULTS.md`. Backup **pré-commune** :
> `labuse-pre-salazie-20260625-114234.dump` (SHA `682e06f4…866fa`) — **⚠️ PURGÉ le 2026-06-25** :
> point de retour d'une opération **terminée / validée / mergée** ; **plus sur disque** ; restaurable courant = baseline `post-Entre-Deux 17 gold`.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `cascade_results`,
  `parcel_evaluations`, `dvf_mutations`, `bilan_params` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-125248.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=2bd9a82`, working tree clean,
  **23 communes / 425 103 parcelles**, **16 gold** (inchangé), Salazie présente / 100 % évaluée / **non-gold**,
  **Cilaos absente**. **Aucun changement scoring / seuil 65 / config gold.**

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » des communes re-cascadées aux jalons
> précédents (verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).
> **Salazie** est un import unique (sans stale).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-salazie-23communes-20260625-125248.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-salazie-23communes-20260625-125248.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=23 parcels=425103 (gold = 16, Cilaos absente)
```

---

## Baseline précédent — « post-PPR Étape A : pilote Saint-Paul re-cascadé (quick-win PM1 < 10 %) » (2026-06-25)

Point de restauration **propre et recommandé** après le **pilote Étape A PPR v2** : la commune gold
**Saint-Paul** a été **re-cascadée** avec le quick-win « périmètre PM1 marginal (< 10 %) → flag faible »
(le reste du portefeuille est inchangé). État figé : `main` à `8d55016` (`docs: merge Saint-Paul PPR step A
pilot`). **Gold count inchangé = 16** (Saint-Paul était déjà gold ; aucun passage gold).

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-ppr-stepa-saintpaul-20260625-110124.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-ppr-stepa-saintpaul-20260625-110124.dump` |
| **Date / heure** | **2026-06-25 11:01:24 UTC** |
| **Taille** | **1069 Mo** (1 068 754 078 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `e879f0edad704f4ed1542a484f52c7b7d8ede92cc43beb3c0d31f3a1256752bf` |
| **Sidecar** | `…-110124.dump.sha256` |

### Contenu du baseline (post-PPR Étape A, pilote Saint-Paul)

| Élément | Valeur |
|---|---|
| `main` (code) | **`8d55016`** (`docs: merge Saint-Paul PPR step A pilot` ; Étape A PPR v2 mergée à `7490f75`) |
| Communes en base | **22** |
| Parcelles | **418 068** |
| Communes **gold** (16) | inchangées (Saint-Paul … Saint-André) |
| **Re-cascadée Étape A** | **Saint-Paul** (97415) — périmètre PM1 marginal < 10 % → flag **faible** (au lieu de fort bloquant) |

> **Pilote Saint-Paul (Étape A PPR v2)** : 51 129 parcelles re-cascadées (`evaluate_commune`, sans ré-import).
> Verdicts : opportunité **1 848 → 1 905** (+57 net) · à creuser 15 852→15 397 · écartée 1 532→1 537 · faux
> positif 31 897→32 290. **Effet Étape A propre = +81 opportunités** (via flag marginal), 0 perte imputable ;
> **4 742** parcelles déflaguées (PPR fort 17 577→15 081, PPR faible 0→4 742). Seuil 65 inchangé, rouge/bleu
> non utilisé (0 PPR hard_exclude). Détail : `docs/communes/saint_paul_PPR_STEP_A_PILOT.md`.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-110124.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=8d55016`, working tree clean,
  **22 communes / 418 068 parcelles**, **16 gold** (inchangé), Saint-Paul re-cascadée Étape A.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (Saint-Paul porte désormais l'ancien
> set + le set Étape A — verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-ppr-stepa-saintpaul-20260625-110124.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-ppr-stepa-saintpaul-20260625-110124.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=22 parcels=418068 (gold = 16)
```

---

## Baseline précédent — « post-16-gold : Saint-André (repli AGORAH) + 2 communes NO-GO » (2026-06-23)

Point de restauration **propre et recommandé** de l'état courant : **16 communes gold** — dont **Saint-André**,
**première commune débloquée par le repli AGORAH** (PLU absent du Géoportail de l'Urbanisme) — **+ 2 communes
importées techniquement propres mais différées NO-GO** (quasi-0 opportunité : Les Trois-Bassins, Sainte-Rose).
État figé : `main` à `287d0f0` (`LOT6: validate Saint-André gold`). **Gold count = 16.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-16gold-saint-andre-agorah-20260623-205249.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-16gold-saint-andre-agorah-20260623-205249.dump` |
| **Date / heure** | **2026-06-23 20:52:49 UTC** |
| **Taille** | **1068 Mo** (1 068 320 420 octets, `pg_dump -Fc --no-owner`) |
| **SHA-256** | `acd81c616dc9d6ceba07adab34f9892d0b917f535e0cd505b532c73f1fca4714` |
| **Sidecar** | `…-205249.dump.sha256` |

### Contenu du baseline (post-16-gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`287d0f0`** (`LOT6: validate Saint-André gold`) |
| Communes en base | **22** |
| Parcelles | **418 068** |
| Communes **gold** (16) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · Le Port · Petite-Île · Saint-Benoît · Sainte-Marie · Sainte-Suzanne · **Saint-André** |
| **Importées NO-GO (2)** | **Les Trois-Bassins** (`97423`) · **Sainte-Rose** (`97419`) — quasi-0 opportunité, différées (cf. `*_NO_GO_QUASI_0_OPPORTUNITE.md`) |
| **Différées scoring/métier (en DB)** | La Plaine-des-Palmistes · Entre-Deux (+ les 2 ci-dessus) |
| **Bloquées (2)** | **Saint-Leu** (`97413`) · **Saint-Philippe** (`97417`) — PLU/GPU propre absent |

> **Saint-André** (nouveau **16ᵉ** gold, vague 3, INSEE 97409, **re_couches_re_cascade**) — **PREMIER gold
> débloqué par le repli AGORAH**. PLU absent du Géoportail de l'Urbanisme (0 zone propre `DU_97409` au GPU,
> API Carto + WFS) → **142 zones** PLU servies par la **Base permanente des PLU de La Réunion** (AGORAH /
> Open Data Réunion ; `attrs.source=AGORAH_BASE_PERMANENTE_PLU_REUNION`, idurba `97409_20190228`, datappro
> `2019-02-28`, typezones U=41/AU=40/A=40/N=21), **couverture propre `DU_97409` = 100 %**. 22 600 parcelles ·
> 33 sections · 100 % évaluées · bâti **50 910** · voirie **13 264** (non plafonnée, ≠ 5 000) · DVF **934** ·
> PPR **4** · SAR **121** · prescriptions **308** · 0 doublon de couche. Verdicts : opportunité **54** (taux
> **0,2 %**, profil comparable au gold Saint-Denis — **pas** un quasi-0 façon La Plaine / Trois-Bassins /
> Sainte-Rose) · à creuser **6 851** · écartée **548** · faux positif probable **15 147**.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-205249.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=287d0f0`, working tree clean,
  **22 communes / 418 068 parcelles**, **16 gold**, Saint-André gold/reliable/`attendu=22600`,
  Sainte-Suzanne & Sainte-Marie & Saint-Benoît gold, Saint-Leu & Saint-Philippe non-gold,
  La Plaine-des-Palmistes & Entre-Deux & Les Trois-Bassins & Sainte-Rose non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (communes ex-`partiel_evalue` /
> re-cascadées — verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-16gold-saint-andre-agorah-20260623-205249.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-16gold-saint-andre-agorah-20260623-205249.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=22 parcels=418068 (gold = 16)
```

---

## Baseline précédent — « post-15-gold + 2 communes importées NO-GO (Les Trois-Bassins, Sainte-Rose) » (2026-06-23)

Point de restauration **propre et recommandé** de l'état courant : 15 communes gold (inchangées) **+ 2
communes importées techniquement propres mais différées NO-GO** (quasi-0 opportunité) — Les Trois-Bassins
et Sainte-Rose. État figé : `main` à `632e30d` (docs NO-GO Sainte-Rose mergée). **Gold count inchangé = 15.**

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-nogo-trois-bassins-sainte-rose-20260623-164812.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-nogo-trois-bassins-sainte-rose-20260623-164812.dump` |
| **Date / heure** | **2026-06-23 16:48:12 UTC** |
| **Taille** | **1027 Mo** (1 027 482 569 octets, `pg_dump -Fc`) |
| **SHA-256** | `26ba3c9be6ba489a30dc53ce3386543b2b12abd11db923b2dbff6b5f3771f8ae` |
| **Sidecar** | `…-164812.dump.sha256` |

### Contenu du baseline (post-no-go)

| Élément | Valeur |
|---|---|
| `main` (code) | **`632e30d`** (`docs: merge Sainte-Rose no-go documentation`) |
| Communes en base | **22** (20 + Les Trois-Bassins + Sainte-Rose) |
| Parcelles | **418 068** (406 467 + 5 314 + 6 287) |
| Communes **gold** (15) | inchangées (Saint-Paul … Saint-Benoît · Sainte-Marie · Sainte-Suzanne) |
| **Importées NO-GO (2)** | **Les Trois-Bassins** (97423, 5 314 parc., 1 opp / 0,0 %) · **Sainte-Rose** (97419, 6 287 parc., 8 opp / 0,1 %, après dédup `safer` ciblée) — quasi-0 opportunité, différées (cf. `*_NO_GO_QUASI_0_OPPORTUNITE.md`) |
| **Différées scoring/métier (en DB)** | La Plaine-des-Palmistes · Entre-Deux (+ les 2 ci-dessus) |
| **Bloquées (3)** | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU/GPU propre absent |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-164812.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=632e30d`, working tree clean,
  **22 communes / 418 068 parcelles**, **15 gold** (inchangé), Sainte-Rose & Les Trois-Bassins non-gold,
  La Plaine-des-Palmistes & Entre-Deux non-gold, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : Les Trois-Bassins et Sainte-Rose sont **importées et conservées en DB** (runs techniquement
> propres — Sainte-Rose après dédup `safer` ciblée `1357421`) **mais non-gold** (NO-GO métier quasi-0
> opportunité). Lignes `parcel_evaluations` « stale » présentes (re-cascades / sets osm-less) — verdict
> canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-nogo-trois-bassins-sainte-rose-20260623-164812.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-nogo-trois-bassins-sainte-rose-20260623-164812.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=22 parcels=418068 (gold inchangé = 15)
```

---

## Baseline précédent — « post-LOT6 : 15 communes gold + 3 communes bloquées » (2026-06-23)

Point de restauration **propre et recommandé** après LOT6 (15 communes gold). État figé : `main` à
`f685f95` (Sainte-Suzanne gold mergée), 15 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-15gold-saintesuzanne-20260623-145720.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-15gold-saintesuzanne-20260623-145720.dump` |
| **Date / heure** | **2026-06-23 14:57:20 UTC** |
| **Taille** | **978 Mo** (977 512 604 octets, `pg_dump -Fc`) |
| **SHA-256** | `3f48faa6d1b33a1c7252b22e56ed3d37b1110612c62b4c958e891ed967c949ef` |
| **Sidecar** | `…-145720.dump.sha256` |

### Contenu du baseline (post-LOT6, 15 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`f685f95`** (`LOT6: validate Sainte-Suzanne gold`) |
| Communes en base | **20** |
| Parcelles | **406 467** |
| Communes **gold** (15) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · Le Port · Petite-Île · Saint-Benoît · Sainte-Marie · **Sainte-Suzanne** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

> **Sainte-Suzanne** (nouveau gold, vague 5, INSEE 97420, **import_complet** d'une commune absente) :
> 12 527 parcelles · 100 % évaluées · bâti **28 794** · voirie **10 884** (non plafonnée, ≠ 5 000) ·
> zonage propre **DU_97420 100 %** (idurba `97420_plu_20250929`) · `attendu` confirmé **12 527** ·
> `plu_gpu_prescription` **481** (02=18, 15/24=0) · DVF **383** · **PPR 4** · 0 doublon de couche.
> `osm_faux_positif` **0 → 175** corrigé post-run (re-fetch ciblé + re-cascade Sainte-Suzanne uniquement).
> Verdicts : opportunité **321** (taux **2,6 %**) · à creuser **3 475** · écartée **212** · faux positif probable **8 519**.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-145720.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=f685f95`, working tree clean,
  **20 communes / 406 467 parcelles**, **15 gold**, Sainte-Suzanne gold/reliable/`attendu=12527`,
  Sainte-Marie & Saint-Benoît gold, La Plaine-des-Palmistes & Entre-Deux non-gold, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (communes ex-`partiel_evalue` / re-cascadées ;
> Sainte-Suzanne porte l'ancien set osm-less + le set osm-aware — verdict canonique = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-15gold-saintesuzanne-20260623-145720.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-15gold-saintesuzanne-20260623-145720.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=20 parcels=406467 (puis 15 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 14 communes gold + 3 communes bloquées » (2026-06-23)

Point de restauration **propre et recommandé** après LOT6 (14 communes gold). État figé : `main` à
`c87957d` (Sainte-Marie gold mergée), 14 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-14gold-saintemarie-20260623-124203.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-14gold-saintemarie-20260623-124203.dump` |
| **Date / heure** | **2026-06-23 12:42:03 UTC** |
| **Taille** | **925 Mo** (925 425 108 octets, `pg_dump -Fc`) |
| **SHA-256** | `6dbe8e8e541b325232659784ed57121ac8369de00c232b02b219879a6c105ba6` |
| **Sidecar** | `…-124203.dump.sha256` |

### Contenu du baseline (post-LOT6, 14 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`c87957d`** (`LOT6: validate Sainte-Marie gold`) |
| Communes en base | **19** |
| Parcelles | **393 940** |
| Communes **gold** (14) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · Le Port · Petite-Île · Saint-Benoît · **Sainte-Marie** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

> **Sainte-Marie** (nouveau gold, vague 5, INSEE 97418, **import_complet** d'une commune absente) :
> 16 746 parcelles · 100 % évaluées · bâti **48 795** · voirie **12 745** (non plafonnée, ≠ 5 000) ·
> zonage propre **DU_97418 100 %** (idurba `97418_plu_20251126`) · `attendu` confirmé **16 746** ·
> `plu_gpu_prescription` **1 093** (vigilance typepsc 02/15/24) · DVF **967** · 0 doublon de couche.
> Verdicts : opportunité **757** (taux **4,5 %**, accepté avec vigilance < 5 %) · à creuser **5 142** ·
> écartée **424** · faux positif probable **10 423**. PPR absent (non bloquant).

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-124203.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=c87957d`, working tree clean,
  **19 communes / 393 940 parcelles**, **14 gold**, Sainte-Marie gold/reliable/`attendu=16746`,
  Saint-Benoît gold, La Plaine-des-Palmistes & Entre-Deux non-gold, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (communes ex-`partiel_evalue` / re-cascadées —
> verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées). Sainte-Marie (import_complet) : éval unique, sans stale.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-14gold-saintemarie-20260623-124203.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-14gold-saintemarie-20260623-124203.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=19 parcels=393940 (puis 14 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 13 communes gold + 3 communes bloquées » (2026-06-23)

Point de restauration **propre et recommandé** après LOT6 (13 communes gold). État figé : `main` à
`54a4a52` (Saint-Benoît gold mergée), 13 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-13gold-saintbenoit-20260623-111447.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-13gold-saintbenoit-20260623-111447.dump` |
| **Date / heure** | **2026-06-23 11:14:47 UTC** |
| **Taille** | **859 Mo** (858 559 195 octets, `pg_dump -Fc`) |
| **SHA-256** | `bdc364d7b0ef40560614f958f216dd9095bb6daa53783c43752b4878a8b42a32` |
| **Sidecar** | `…-111447.dump.sha256` |

### Contenu du baseline (post-LOT6, 13 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`54a4a52`** (`LOT6: validate Saint-Benoît gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (13) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · Le Port · Petite-Île · **Saint-Benoît** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

> **Saint-Benoît** (nouveau gold, vague 3, INSEE 97410) : 21 671 parcelles · 100 % évaluées · bâti **34 683** ·
> voirie **14 922** · zonage 100 % (DU_97410) · `attendu` confirmé **21 671** · `plu_gpu_prescription`
> **2 078** après **dédup ciblée** du doublon exact (ids `1133604`/`1133675` → suppression de `1133675` ;
> `dup_groups` 1→0). Verdicts : opportunité **589** · à creuser **4 611** · écartée **1 035** · faux positif probable **15 436**.

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes (schéma + TABLE DATA).
- ✅ **SHA-256** généré (sidecar `…-111447.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=54a4a52`, working tree clean,
  **18 communes / 377 194 parcelles**, **13 gold**, Saint-Benoît gold/reliable/`attendu=21671`,
  La Plaine-des-Palmistes & Entre-Deux non-gold, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (communes ex-`partiel_evalue`, dont
> Saint-Benoît — verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-13gold-saintbenoit-20260623-111447.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-13gold-saintbenoit-20260623-111447.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 13 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 12 communes gold + 3 communes bloquées » (2026-06-22)

Point de restauration **propre et recommandé** après LOT6 (12 communes gold). État figé : `main` à
`d8c6861` (Petite-Île gold mergée), 12 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-12gold-petiteile-20260622-161233.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-12gold-petiteile-20260622-161233.dump` |
| **Date / heure** | **2026-06-22 16:12:33 UTC** |
| **Taille** | **787 Mo** (787 180 856 octets, `pg_dump -Fc`) |
| **SHA-256** | `b42dd09d427e5182b8d2ce3f28dd711422406ce955e2681bf0e5e2acb413ade8` |
| **Sidecar** | `…-161233.dump.sha256` |

### Contenu du baseline (post-LOT6, 12 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`d8c6861`** (`LOT6: validate Petite-Île gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (12) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · Le Port · **Petite-Île** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-161233.dump.sha256`), vérifié `sha256sum -c` → « …dump: OK ».
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=d8c6861`, working tree clean,
  **18 communes / 377 194 parcelles**, **12 gold**, Petite-Île gold/reliable, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (Bras-Panon, Les Avirons, Le Port,
> Petite-Île, ex-`partiel_evalue`, ×2 — verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-12gold-petiteile-20260622-161233.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-12gold-petiteile-20260622-161233.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 12 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 11 communes gold + 3 communes bloquées » (2026-06-22)

Point de restauration **propre et recommandé** après LOT6 (11 communes gold). État figé : `main` à
`5b6a393` (Le Port gold mergé + correctif faux positif dédup), 11 communes validées au standard
Saint-Paul, 3 communes bloquées (PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-11gold-leport-20260622-145015.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-11gold-leport-20260622-145015.dump` |
| **Date / heure** | **2026-06-22 14:50:15 UTC** |
| **Taille** | **779 Mo** (779 147 452 octets, `pg_dump -Fc`) |
| **SHA-256** | `ffefe0f73927e8a96a778e6da9defe243259c9f639bb443989801a51bfd122eb` |
| **Sidecar** | `…-145015.dump.sha256` |

### Contenu du baseline (post-LOT6, 11 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`5b6a393`** (`LOT6: validate Le Port gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (11) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · Les Avirons · **Le Port** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-145015.dump.sha256`).
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=5b6a393`, working tree clean,
  **18 communes / 377 194 parcelles**, **11 gold**, Saint-Leu/André/Philippe non-gold, DVF Le Port 526.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » (Bras-Panon, Les Avirons, Le Port,
> ex-`partiel_evalue`, ×2 — verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-11gold-leport-20260622-145015.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-11gold-leport-20260622-145015.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 11 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 10 communes gold + 3 communes bloquées » (2026-06-22)

Point de restauration **propre et recommandé** après LOT6 (10 communes gold). État figé : `main` à
`3bb5955` (Les Avirons gold mergée), 10 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-10gold-lesavirons-20260622-133842.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-10gold-lesavirons-20260622-133842.dump` |
| **Date / heure** | **2026-06-22 13:38:42 UTC** |
| **Taille** | **774 Mo** (773 569 342 octets, `pg_dump -Fc`) |
| **SHA-256** | `5a806e2f2470a67988e0ab407d0c86e2c4f9ee062d978c2bff36f88fded343a1` |
| **Sidecar** | `…-133842.dump.sha256` |

### Contenu du baseline (post-LOT6, 10 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`3bb5955`** (`LOT6: validate Les Avirons gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (10) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · Bras-Panon · **Les Avirons** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-133842.dump.sha256`).
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=3bb5955`, working tree clean,
  **18 communes / 377 194 parcelles**, **10 gold**, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » pour Bras-Panon et Les Avirons
> (ex-`partiel_evalue`, ×2 — verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-10gold-lesavirons-20260622-133842.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-10gold-lesavirons-20260622-133842.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 10 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 9 communes gold + 3 communes bloquées » (2026-06-22)

Point de restauration **propre et recommandé** après LOT6 (9 communes gold). État figé : `main` à
`b1eabe6` (Bras-Panon gold mergée), 9 communes validées au standard Saint-Paul, 3 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-9gold-braspanon-20260622-124630.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-9gold-braspanon-20260622-124630.dump` |
| **Date / heure** | **2026-06-22 12:46:30 UTC** |
| **Taille** | **764 Mo** (764 103 985 octets, `pg_dump -Fc`) |
| **SHA-256** | `94ffa24c1c1cbe001c0fb6bf1939f798e870776249f984e7830fc19f2bfe2f7b` |
| **Sidecar** | `…-124630.dump.sha256` |

### Contenu du baseline (post-LOT6, 9 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`b1eabe6`** (`LOT6: validate Bras-Panon gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (9) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · Saint-Joseph · **Bras-Panon** |
| **Bloquées** (3) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) · **Saint-Philippe** (`97417`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-124630.dump.sha256`).
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=b1eabe6`, working tree clean,
  **18 communes / 377 194 parcelles**, **9 gold**, Saint-Leu/André/Philippe non-gold.

> ℹ️ Note : ce baseline inclut des lignes `parcel_evaluations` « stale » pour Bras-Panon (ex-`partiel_evalue`,
> ×2 — verdicts canoniques = dernière éval/parcelle, impact fonctionnel nul ; non nettoyées).

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-9gold-braspanon-20260622-124630.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-9gold-braspanon-20260622-124630.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 9 communes gold)
```

---

## Baseline précédent — « post-LOT6 : 8 communes gold + Saint-Leu/Saint-André bloquées » (2026-06-22)

Point de restauration **propre et recommandé** après LOT6 (8 communes gold). État figé : `main` à
`69748a4` (Saint-Joseph gold mergée), 8 communes validées au standard Saint-Paul, 2 communes bloquées
(PLU/GPU propre absent), base locale propre après tous les runs / dédups.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-lot6-8gold-saintjoseph-20260622-113036.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-lot6-8gold-saintjoseph-20260622-113036.dump` |
| **Date / heure** | **2026-06-22 11:30:36 UTC** |
| **Taille** | **730 Mo** (729 840 418 octets, `pg_dump -Fc`) |
| **SHA-256** | `5bdea2e2ae50345acb81a82f2d39684603aa95114e4c4deec10a896232d6afb2` |
| **Sidecar** | `…-113036.dump.sha256` |

### Contenu du baseline (post-LOT6, 8 gold)

| Élément | Valeur |
|---|---|
| `main` (code) | **`69748a4`** (`LOT6: validate Saint-Joseph gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (8) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · Saint-Louis · Saint-Denis · **Saint-Joseph** |
| **Bloquées** (2) | **Saint-Leu** (`97413`) · **Saint-André** (`97409`) — PLU propre absent du GPU (cf. notes `*_BLOCKED_PLU_GPU.md`) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-113036.dump.sha256`).
- ✅ Vérifs avant/après (lecture seule, inchangées par le backup) : `main=69748a4`, working tree clean,
  **18 communes / 377 194 parcelles**, **8 gold**, Saint-Leu & Saint-André non-gold.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-lot6-8gold-saintjoseph-20260622-113036.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-lot6-8gold-saintjoseph-20260622-113036.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis 8 communes gold)
```

---

## Baseline précédent — « post-vague 2 : 6 communes gold + Saint-Leu bloquée » (2026-06-21)

Point de restauration **propre et recommandé** après la vague 2. État figé : `main` à `cf58f28`
(Saint-Louis gold mergée + Saint-Leu documentée bloquée), 6 communes validées au standard Saint-Paul,
base locale propre après tous les runs / dédups / rollbacks.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-vague2-6gold-saintleu-blocked-20260621-205329.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-vague2-6gold-saintleu-blocked-20260621-205329.dump` |
| **Date / heure** | **2026-06-21 20:53:29 UTC** |
| **Taille** | **646 Mo** (646 351 261 octets, `pg_dump -Fc`) |
| **SHA-256** | `e0007a6763d0ada538f6d3d7fb48e1657046a3d7cb3ccd8eae75c110a1a6e982` |
| **Sidecar** | `…-205329.dump.sha256` |

### Contenu du baseline (post-vague 2)

| Élément | Valeur |
|---|---|
| `main` (code) | **`cf58f28`** (`LOT6: validate Saint-Louis gold`) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** (6) | Saint-Paul · L'Étang-Salé · La Possession · Saint-Pierre · Le Tampon · **Saint-Louis** |
| **Saint-Leu** | **non-gold / bloquée** — PLU `97413` absent du GPU (cf. `docs/communes/saint_leu_BLOCKED_PLU_GPU.md`) |
| Saint-Louis (nouveau gold) | 29 241 parcelles · 100 % évaluées · voirie **9 020** (dé-plafonnée) · bâti **41 031** |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **SHA-256** généré (sidecar `…-205329.dump.sha256`).
- ✅ Vérifs **avant/après** (lecture seule, inchangées par le backup) : `main=cf58f28`, working tree clean,
  **18 communes / 377 194 parcelles**, `/communes/status` = **6 gold**, Saint-Louis **gold**, Saint-Leu **non-gold**.

### Restaurer ce baseline

```bash
# 1) intégrité
cd /var/backups/labuse
sha256sum -c labuse-post-vague2-6gold-saintleu-blocked-20260621-205329.dump.sha256   # attendu : « …dump: OK »
# 2) restauration (écrase la base de travail ; --yes saute la confirmation)
labuse restore-db --file /var/backups/labuse/labuse-post-vague2-6gold-saintleu-blocked-20260621-205329.dump --yes
# 3) vérification
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c \
  "SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;"
# attendu : communes=18 parcels=377194 (puis /communes/status = 6 gold)
```

---

## Baseline précédent — « 3 communes gold + voirie complète » (2026-06-21)

Point de restauration **propre et recommandé** avant la vague 2. État figé : correctif de pagination
voirie dans `main` + les 3 communes gold re-fetchées au standard voirie complet.

| Champ | Valeur |
|---|---|
| **Nom** | `labuse-post-voirie-gold-3communes-20260621-104321.dump` |
| **Chemin exact** | `/var/backups/labuse/labuse-post-voirie-gold-3communes-20260621-104321.dump` |
| **Date / heure** | **2026-06-21 10:43:21 UTC** |
| **Taille** | **513 Mo** (`pg_dump -Fc --no-owner`) |
| **SHA-256** | `24c33b68a1f5aa6e151a3c17bdf5e81a18afcd0e23350de494d4c77f934af7db` |
| **Sidecar** | `…-104321.dump.sha256` |

### Contenu du baseline

| Élément | Valeur |
|---|---|
| `main` (code) | **`9fa3ec3`** (correctif pagination voirie + 3 rapports re-fetch mergés) |
| Communes en base | **18** |
| Parcelles | **377 194** |
| Communes **gold** | **3** (Saint-Paul, La Possession, L'Étang-Salé) |
| Voirie L'Étang-Salé | **6 986** tronçons (dé-plafonnée) |
| Voirie La Possession | **11 825** tronçons (dé-plafonnée) |
| Voirie Saint-Paul | **22 999** tronçons (dé-plafonnée) |

### Preuve d'intégrité (à la création)

- ✅ **`pg_restore --list`** : OK — 190 entrées TOC ; tables `parcels`, `spatial_layers`, `parcel_evaluations` présentes.
- ✅ **Test de restauration RÉEL** dans une base temporaire isolée (`labuse_restore_test`, **sans toucher**
  la base de travail) : `pg_restore` **exit 0**, aucune erreur bloquante ; contenu restauré vérifié —
  **parcels = 377 194**, **communes = 18**, voirie **6 986 / 11 825 / 22 999** (identiques à la source).
- ✅ **Base temporaire supprimée** après vérification (aucune base `labuse_restore%` résiduelle).

---

## Restaurer ce baseline

**1. Vérifier l'intégrité du dump AVANT toute restauration :**

```bash
cd /var/backups/labuse
sha256sum -c labuse-post-voirie-gold-3communes-20260621-104321.dump.sha256
# attendu : « …dump: OK »
```

**2a. Restauration via la CLI LA BUSE (recommandé)** — écrase la base de travail, demande confirmation
(`--yes` pour la sauter) :

```bash
labuse restore-db --file /var/backups/labuse/labuse-post-voirie-gold-3communes-20260621-104321.dump --yes
```

**2b. Alternative `pg_restore`** (équivalent bas niveau) :

```bash
PGPASSWORD=labuse pg_restore -h localhost -p 5432 -U labuse -d labuse \
  --clean --if-exists --no-owner --no-acl \
  /var/backups/labuse/labuse-post-voirie-gold-3communes-20260621-104321.dump
```

**3. Vérifier après restauration :**

```bash
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c "
SELECT 'communes='||count(DISTINCT commune)||' parcels='||count(*) FROM parcels;
SELECT commune||' voirie='||count(*) FROM spatial_layers WHERE kind='voirie'
  AND commune IN ('Saint-Paul','La Possession','L''Étang-Salé') GROUP BY commune;"
# attendu : communes=18 parcels=377194 ; voirie 6986 / 11825 / 22999
```

---

## Autres points de restauration disponibles (`/var/backups/labuse`)

Sauvegardes **pré-run** par commune (rollback ponctuel d'un re-fetch voirie ; conserver tant que le
baseline n'est pas jugé définitif) :

| Backup | Pris avant |
|---|---|
| `labuse-labuse-20260620-214358.dump` | re-fetch voirie L'Étang-Salé |
| `labuse-labuse-20260620-220104.dump` | re-fetch voirie La Possession |
| `labuse-labuse-20260621-085854.dump` | re-fetch voirie Saint-Paul |

> Ces dumps pré-run précèdent les re-fetch ; le **baseline post-voirie** ci-dessus est l'état **après**
> les 3 re-fetch (à privilégier pour repartir propre).

---

## Convention

- **Backup complet** : `labuse backup-db --dir <dossier>` → `labuse-<db>-<horodatage>.dump` (+ générer le `.sha256`).
- **Backup nommé** (jalon) : `pg_dump -Fc --no-owner -d labuse -f <dossier>/labuse-<libellé>-<horodatage>.dump`.
- **Toujours** : générer le `.sha256`, vérifier `pg_restore --list`, et pour un jalon important, un test de
  restauration dans une base temporaire jetable.
- **Jamais** : committer un `*.dump` (gitignoré). Documenter ici à la place.
