# Construire les 24 communes — et les rendre DURABLES

## Le piège : la base est éphémère

Dans l'environnement *Claude Code on the web*, la base PostGIS vit dans le
conteneur. Le hook `.claude/hooks/session-start.sh` se contente de **créer une
base vide** (`CREATE DATABASE IF NOT EXISTS` + extension PostGIS) — il **ne
charge aucune donnée**. Les communes présentes au démarrage proviennent donc du
**répertoire de données PostgreSQL figé dans l'image du conteneur**.

Conséquence :

| Évènement | Effet sur les données |
|---|---|
| **Redémarrage** du même conteneur | conservées (cluster PG intact) |
| **Remplacement** du conteneur (image neuve) | **repart de l'image** — tout ajout runtime est perdu |

Autrement dit : **ingérer/évaluer des communes pendant une session ne survit pas
à un remplacement de conteneur.** Et la charge est trop grosse pour être commitée
dans git (≈ 950 Mo : `cascade_results` ~500 Mo + `parcels` ~220 Mo +
`spatial_layers` ~200 Mo + `parcel_evaluations` ~30 Mo ; le dépôt fait ~3 Mo, sans
git-lfs).

## Construire les 24 communes (rapide, parallèle, reprenable)

```bash
python scripts/build_communes.py --workers 4
```

- parallélise l'**évaluation** (CPU/DB) par commune et chevauche l'**ingestion**
  réseau des communes absentes ;
- **idempotent / reprenable** : saute les communes déjà `ok`, ré-évalue les
  `ingested`, (re)ingère + évalue les absentes ;
- verdicts identiques à `labuse ingest-island` (la cascade n'est pas touchée).

Ordre de grandeur : l'ingestion des communes manquantes est rapide (~minutes),
mais l'**évaluation complète des 24 prend plusieurs heures** (cascade spatiale
lourde, ~4–7 parcelles/s agrégé).

## Rendre les 24 communes DURABLES

Puisque les données vivent dans l'image, la seule voie durable est de **cuire
les 24 communes dans l'image** puis de la re-snapshotter :

1. Démarrer un conteneur de build, base à l'état courant.
2. `python scripts/build_communes.py` → attendre `DONE — 24/24 communes complètes`.
3. **Re-snapshotter l'image de l'environnement** à partir de ce conteneur
   (étape côté gestion de l'environnement / pipeline d'image — pas réalisable
   depuis une session Claude Code).

Tant que cette cuisson n'est pas faite, chaque conteneur neuf repart de l'image
courante (**18 communes présentes, 12 évaluées**).
