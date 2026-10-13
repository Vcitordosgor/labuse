# SOLIDITE-1 Lot 3.1 — Inventaire disque du VPS + projection 3 mois

Relevé **lecture seule** le 13/10/2026 sur `labuse-vps` (51.255.163.56), base servie **q_v18**.

## 1. Occupation (df + du)

| Poste | Taille | Note |
|---|---|---|
| **Disque `/` (sda1)** | **96 Go — 90 Go utilisés — 6,6 Go libres — 94 %** | au-dessus du seuil d'alerte 85 % (Lot 1 sonnerait) |
| `/var/lib/postgresql` | 47 Go | la base `labuse` = **45 Go** |
| `/var/backups/labuse` | 24 Go | 3 dumps quotidiens ~6,5 Go + `pre-maj-20260827` 4,1 Go |
| `/opt/labuse` | 16 Go | `app` 11 Go + `app-avant-0610` 4,2 Go (vieux) + `venv` 0,9 Go |
| `/var/log` | 540 Mo | |
| `/home`, `/tmp` | 449 Mo / 1,3 Mo | |

## 2. Base `labuse` (45 Go) — table par table

Schémas : **public 54 Go** (indices compris) · pg_toast 6,1 Go · `sauvegarde_20261006` **10 Mo** (reliquat).

Top tables :

| Table | Taille | Runs présents |
|---|---|---|
| `dryrun_cascade_results` | **13 Go** | q_v18_sources (21,2 M, **servi**) · q_v13_sources1 (17,6 M) · q_v11_m137 (15,9 M) |
| `parcel_p_score_v2` | 4,6 Go | q_v18 (**servi**) · q_v16 (**préc.**) · **q_v8_calibre_pre_regle / _m28 / _m39 / _pond** · q_v11_m137 · q_v2_demo |
| `score_labuse` | 3,4 Go | q_v18 · q_v16 (déjà propre : 2 runs) |
| `spatial_layers` (+`_sub`) | 3,2 + 1,7 Go | couches carto |
| `p_model_dataset_v2bis / _v2 / _ (base)` | 1,85 + 1,6 + 0,77 Go | **datasets d'entraînement modèle** |
| `p_model_ext_dataset` | 1,56 Go | ⚠ **LU par l'API — à GARDER** (cf. DISQUE-VPS-1) |
| `tuyau_subdivise`, `cascade_results`, `parcel_couche_intersection` | 1,8 / 1,4 / 1,1 Go | |

## 3. Gisement récupérable (sans toucher au servi/précédent/secours)

Règle du mandat : garder **le run servi (q_v18) + le précédent (q_v16) + un secours (q_v11_m137)**.

| Cible | Gain estimé | Risque | Geste |
|---|---|---|---|
| `parcel_p_score_v2` : 4 runs morts **q_v8_calibre_pre_\*** | ~2–2,5 Go | nul (runs calibration abandonnés) | DELETE + VACUUM FULL |
| `dryrun_cascade_results` : runs au-delà de servi+secours | jusqu'à ~8 Go | **à confirmer** quel run est le « précédent » cascade (q_v13_sources1 ou q_v11_m137) | DELETE + VACUUM FULL |
| `p_model_dataset` / `_v2` / `_v2bis` (PAS `_ext_`) | ~4,2 Go | faible — datasets d'entraînement, **non servis** (confirmé DISQUE-VPS-1) ; `_ext_dataset` GARDÉ | TRUNCATE |
| `/opt/labuse/app-avant-0610` | 4,2 Go | nul (ancienne version, supprimable ~20/10 — DISQUE-VPS-1) | `rm -rf` |
| `/opt/labuse/app` sources d'ingestion brutes | jusqu'à ~9,7 Go | moyen — non lues en prod mais à vérifier au cas par cas | hors de ce lot |
| schéma `sauvegarde_20261006` | 10 Mo | nul | DROP SCHEMA (après accord Vic) |
| `pre-maj-20260827` (sauvegarde pré-maj) | 4,1 Go | nul si maj validée | `rm` (accord Vic) |

**Total réaliste immédiat (hors sources app) : ~20 Go** — cohérent avec l'estimation DISQUE-VPS-1 (~30 Go
avec les sources d'ingestion). Le script `deploy/scripts/menage_disque.sh` fait tout cela en **dry-run par
défaut** (liste ce qu'il ferait, ne touche rien) ; `--execute` seulement après ton feu vert.

## 4. Projection 3 mois

- **Sauvegardes** : stables à ~26 Go (rotation 4 quotidiennes). Pas de dérive.
- **Base** : un **nouveau run** q_vN coûte ~**6–8 Go** (cascade ~6 Go + score ~1 Go + datasets). Au rythme
  d'un run/mois **sans purge**, +18–24 Go sur 3 mois.
- **Contrainte dure** : il ne reste que **6,6 Go libres**. Un seul run supplémentaire a besoin de plus de
  place que ça (il écrit avant de pouvoir purger l'ancien). **Le disque est au bord du plein : le prochain
  run risque de le saturer** — c'est exactement le scénario du 07/10.

**Conséquence** : le ménage (§3) est à faire **avant le prochain run** pour regagner ~20 Go ; et un disque
plus grand est nécessaire pour travailler sans marcher sur le fil.

## 5. Proposition disque (Vic décide et commande chez OVH)

Le VPS est un OVH ~96 Go. Pour 3 mois de marge confortable (purge + 2–3 runs + sauvegardes) il faut viser
**~160–200 Go**.

- **Option A — agrandir le volume** : si le VPS est sur un plan à disque extensible (ou ajouter un *Additional
  Disk* / *Block Storage* OVH monté sur `/var/lib/postgresql`). ~0,04 €/Go/mois en Block Storage → +100 Go ≈
  **~4 €/mois**. Le moins disruptif (pas de migration).
- **Option B — passer au gabarit VPS supérieur** (plus de CPU/RAM + disque) : utile aussi car `shared_buffers`
  est à 128 Mo (VITESSE-PROD-1) — un gabarit avec plus de RAM aiderait les requêtes chaudes.

👉 **À confirmer par Vic sur l'espace client OVH** (les prix bougent ; je ne commande rien). Recommandation :
**Option A (+100 Go Block Storage sur la partition PostgreSQL)** si disponible — rapide, bon marché, réversible.

## 6. Ce qui attend un geste de Vic

1. Lancer le **ménage** (`menage_disque.sh --execute`) après revue — regagne ~20 Go. *Geste VPS, je te le montre avant.*
2. **Commander le disque** chez OVH (§5).
3. Fournir le **compte de stockage objet** + la **clé de chiffrement** pour la copie hors-VPS (Lot 3.2).
