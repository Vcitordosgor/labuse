# LA BUSE — points de restauration (backups)

> **⚠️ Règle d'or : on ne committe JAMAIS un dump dans le dépôt — seulement sa documentation.**
> Les dumps (`*.dump`) vivent hors dépôt (`/var/backups/labuse`) ou dans `backups/` (gitignoré,
> cf. `.gitignore`). Ce fichier ne fait que **référencer** les backups (chemin, empreinte, contenu)
> pour pouvoir les retrouver et vérifier leur intégrité. Un dump pèse ~500 Mo : le versionner
> polluerait l'historique et fuiterait des données.

Format : `pg_dump -Fc` (custom, compressé). Restauration via `labuse restore-db` ou `pg_restore`.

---

## 🟢 Baseline courant — « post-LOT6 : 13 communes gold + 3 communes bloquées » (2026-06-23)

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
