# SAINT-PAUL — LOT 1 : Backup & Sécurité

> Prérequis de sécurité **avant** tout import (LOT 2). Exécuté le **2026-06-20** sur la branche
> `claude/brave-davinci-NaRd4`.
>
> **Aucune donnée modifiée. Aucun import. Aucune suppression sur la base principale. Aucun merge,
> aucun déploiement, aucun recalcul cascade.** La seule base créée (`labuse_restore_test`) était
> **temporaire** et a été supprimée après vérification ; la base principale `labuse` n'a **jamais**
> été touchée.

---

## 1. Backup complet PostgreSQL / PostGIS

| Élément | Valeur |
|---|---|
| **Chemin exact** | `/var/backups/labuse/labuse-labuse-20260620-101644.dump` |
| **Hors dossier projet ?** | ✅ OUI (`/var/backups/labuse/`, hors `/home/user/labuse`) |
| Format | `pg_dump -Fc --no-owner` (custom, compressé) |
| **Taille** | **235 Mo** (246 176 194 octets) |
| **SHA-256** | `5de67e101a38f761c1b27f2b8789ab153005eb268f750792ac3e4c9adcd20256` |
| Fichier checksum | `…/labuse-labuse-20260620-101644.dump.sha256` |
| Commande utilisée | `labuse backup-db --dir /var/backups/labuse` |

Vérifier l'intégrité du fichier à tout moment :
```bash
sha256sum -c /var/backups/labuse/labuse-labuse-20260620-101644.dump.sha256
```

## 2. Test de restaurabilité (sur base TEMPORAIRE)

La restauration a été **réellement testée** sur une base jetable `labuse_restore_test` (jamais sur
`labuse`), puis la base de test a été supprimée.

**2a. Archive valide + tables critiques présentes** (`pg_restore --list`) : 22 tables, dont les 6 critiques —

| Table | Dans le dump |
|---|---|
| `parcels` · `spatial_layers` · `cascade_results` · `parcel_evaluations` · `dvf_mutations` · `bilan_params` | ✅ toutes présentes |

**2b. Restauration réelle** : `pg_restore --no-owner --jobs=4` → **exit 0, 23 s, 0 erreur**.

**2c. Intégrité (comptages source vs restauré, identiques)** :

| Table | `labuse` (principale) | `labuse_restore_test` | Match |
|---|---:|---:|:--:|
| parcels | 329 065 | 329 065 | ✅ |
| spatial_layers | 254 289 | 254 289 | ✅ |
| cascade_results | 3 472 464 | 3 472 464 | ✅ |
| parcel_evaluations | 215 859 | 215 859 | ✅ |
| dvf_mutations | 39 317 | 39 317 | ✅ |
| bilan_params | 16 | 16 | ✅ |
| **parcels Saint-Paul** | **3 000** | **3 000** | ✅ |

PostGIS opérationnel dans la base restaurée (géométries `geom_2975` valides). **Base temporaire
supprimée** ; bases restantes : `labuse` (intacte), `labuse_test`.

> **Statut de vérification : ✅ RESTAURABLE ET INTÈGRE** (testé de bout en bout, pas seulement documenté).

## 3. Snapshot Saint-Paul — état de référence AVANT import

Gelé au **2026-06-20T10:19Z** (point de comparaison pour valider le LOT 2 a posteriori).

| Indicateur | Valeur |
|---|---|
| Parcelles Saint-Paul | **3 000** (IDU uniques : 3 000) |
| Sections présentes | **14** (sur 98 au cadastre complet) |
| **Verdicts** | faux positif **1 969** · à creuser **782** · écartée **166** · opportunité **83** |
| Parcelles évaluées | **3 000 / 3 000** (100 %) |
| Taille base totale | **1 153 Mo** |
| `cascade_results` | 596 Mo |
| `spatial_layers` | 254 Mo |
| `parcels` | 234 Mo |
| `parcel_evaluations` | 31 Mo |
| `dvf_mutations` | 13 Mo |
| **Temps moyen fiche** | **117 ms** (min 85 · max 164, à chaud, 5 parcelles) |
| Santé `/healthz` | **200** |
| Santé `/readyz` | **200** |
| Santé `/demo-status` | **200** · `ready_for_demo=true` · **14/14** checks |

> Cible après LOT 2 : 51 129 parcelles / 98 sections (cf. `docs/SAINT_PAUL_QUALITY_AUDIT.md`).

## 4. Procédure de ROLLBACK

En cas de problème pendant/après le LOT 2, revenir à cet instantané exact :

```bash
# 1) ARRÊTER l'app (aucune écriture concurrente pendant la restauration)
#    - VPS  : systemctl stop labuse
#    - local: pkill -f "labuse api"

# 2) RESTAURER le dump (pg_restore --clean : remet la base dans l'état du 2026-06-20 10:16)
labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-101644.dump --yes
#    équivalent direct :
#    pg_restore --clean --if-exists --no-owner -d labuse \
#      /var/backups/labuse/labuse-labuse-20260620-101644.dump

# 3) VÉRIFIER la restauration (les comptages doivent retrouver le snapshot ci-dessus)
labuse doctor --json | head
psql -h localhost -U labuse -d labuse -X -c \
  "SELECT count(*) FILTER (WHERE commune ILIKE 'saint-paul') AS sp, count(*) AS total FROM parcels;"
#    attendu : sp=3000, total=329065

# 4) REDÉMARRER l'app
#    - VPS  : systemctl start labuse
#    - local: nohup labuse api >/tmp/labuse.log 2>&1 & disown
```

| Aspect | Détail |
|---|---|
| **Durée estimée** | ~1–2 min (restauration mesurée à **23 s** ici ; + arrêt/redémarrage + vérif) |
| **À arrêter / redémarrer** | l'**app LA BUSE** uniquement (Uvicorn/systemd). PostgreSQL reste en marche. |
| **Risques** | `pg_restore --clean` **écrase** l'état courant (c'est le but du rollback) → ne lancer qu'en connaissance de cause, app arrêtée. Le dump est l'état EXACT pré-LOT 2 : aucune perte au-delà de ce qui a été fait après le backup. |
| **Garantie** | le backup étant **hors `labuse`** et **vérifié** (checksum + test de restauration), le rollback est sûr et reproductible. |

## 5. Conclusion — feu vert ?

| Critère LOT 1 | Statut |
|---|---|
| Backup complet créé | ✅ |
| Hors dossier projet | ✅ (`/var/backups/labuse/`) |
| Taille vérifiée | ✅ 235 Mo |
| Checksum SHA-256 | ✅ |
| Restaurabilité **testée** (base temporaire) | ✅ exit 0, comptages identiques |
| Tables critiques confirmées | ✅ 6/6 |
| Snapshot Saint-Paul figé | ✅ |
| Rollback documenté + chiffré | ✅ |
| Base principale intacte | ✅ (jamais touchée) |

**✅ FEU VERT pour PRÉPARER le LOT 2** (préparation du détail technique uniquement — l'exécution
de l'import reste soumise à validation explicite).

---

*LOT 1 terminé. Aucune donnée modifiée. Le point de retour est en place et prouvé restaurable.*
