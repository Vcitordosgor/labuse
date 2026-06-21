# LA BUSE — points de restauration (backups)

> **⚠️ Règle d'or : on ne committe JAMAIS un dump dans le dépôt — seulement sa documentation.**
> Les dumps (`*.dump`) vivent hors dépôt (`/var/backups/labuse`) ou dans `backups/` (gitignoré,
> cf. `.gitignore`). Ce fichier ne fait que **référencer** les backups (chemin, empreinte, contenu)
> pour pouvoir les retrouver et vérifier leur intégrité. Un dump pèse ~500 Mo : le versionner
> polluerait l'historique et fuiterait des données.

Format : `pg_dump -Fc` (custom, compressé). Restauration via `labuse restore-db` ou `pg_restore`.

---

## 🟢 Baseline courant — « 3 communes gold + voirie complète » (2026-06-21)

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
