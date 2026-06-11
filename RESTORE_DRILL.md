# LA BUSE — Exercice de restauration (restore drill)

> Un backup qu'on n'a jamais restauré n'est pas un backup. Cette procédure a été
> **exécutée réellement** : dump 242 Mo → restauration **46 s** → doctor ✅ sur la base
> restaurée, pipeline (9 entrées, 4 prospections manuelles) intact, parcelles de démo
> présentes. À rejouer **avant chaque pilote** puis périodiquement.

## La règle

On restaure d'abord dans une base **TEMPORAIRE** (`--target-url`) — jamais directement
dans la base de production. On ne touche la vraie base qu'après vérification du dump.

## Procédure (≈ 2 minutes)

```bash
# 0. Choisir le dump à éprouver
DUMP=$(ls -1t backups/labuse-*.dump | head -1) && echo "$DUMP"

# 1. Créer une base temporaire (compose : exécuter dans le conteneur db)
docker compose -f docker-compose.pilot.yml exec db \
  psql -U labuse -d postgres -c 'DROP DATABASE IF EXISTS labuse_drill' \
                              -c 'CREATE DATABASE labuse_drill'

# 2. Restaurer DANS LA TEMPORAIRE (≈ 46 s pour ~240 Mo)
docker compose -f docker-compose.pilot.yml exec app labuse restore-db \
  --file "backups/$(basename "$DUMP")" \
  --target-url "postgresql+psycopg://labuse:$POSTGRES_PASSWORD@db:5432/labuse_drill" --yes

# 3. Vérifier la base RESTAURÉE avec doctor (pointé sur la temporaire)
docker compose -f docker-compose.pilot.yml exec \
  -e LABUSE_DATABASE_URL="postgresql+psycopg://labuse:$POSTGRES_PASSWORD@db:5432/labuse_drill" \
  app labuse doctor --json
#    → attendu : "ready_for_demo": true, healthcheck ok, warm 8/8

# 4. Vérifier le PIPELINE (seule donnée non reconstructible depuis les sources publiques)
docker compose -f docker-compose.pilot.yml exec db \
  psql -U labuse -d labuse_drill -c \
  "SELECT count(*) AS entrees, count(*) FILTER (WHERE prospection != '{}'::jsonb) AS prospections FROM pipeline_entries"

# 5. Nettoyer
docker compose -f docker-compose.pilot.yml exec db \
  psql -U labuse -d postgres -c 'DROP DATABASE labuse_drill'
```

## Critères de réussite

- [ ] restauration sans erreur (`✓ Restauration terminée.`) ;
- [ ] `doctor --json` sur la temporaire → `ready_for_demo: true` ;
- [ ] nombre d'entrées pipeline = celui attendu (saisies manuelles préservées) ;
- [ ] parcelles de démo présentes (le panneau Démo guidée serait vert).

## Restauration RÉELLE (incident)

Même commande **sans** `--target-url` (cible = base de production) — `restore-db` exige
une confirmation explicite et ÉCRASE l'existant :

```bash
docker compose -f docker-compose.pilot.yml stop app                    # personne n'écrit
docker compose -f docker-compose.pilot.yml start app                   # (db reste up)
docker compose -f docker-compose.pilot.yml exec app labuse restore-db --file backups/<dump>
docker compose -f docker-compose.pilot.yml exec app labuse doctor     # ✅ attendu
docker compose -f docker-compose.pilot.yml exec app labuse warm-demo  # re-pré-chauffe
```

Cas d'échec connus :
- *« Fichier invalide (pas une archive pg_dump) »* → le dump est corrompu/incomplet :
  prendre le précédent (d'où la rotation à 14 et la copie EXTERNE).
- erreurs `--clean` sur objets absents → bénin (`--if-exists` les ignore).
- doctor dégradé après restore → relancer `labuse doctor` (répare le schéma léger) puis
  `rebuild-demo` si une couche manque réellement.
