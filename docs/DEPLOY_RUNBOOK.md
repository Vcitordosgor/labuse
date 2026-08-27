# Runbook — déployer une mise à jour sur le VPS (état au 27/08/2026)

> Le geste courant tient en **une commande sur le VPS** : `sudo /opt/labuse/deploy.sh`.
> Source du script dans le repo : `deploy/scripts/deploy_vps.sh`. Le rollback est documenté
> **en tête du script** et rappelé en fin de ce runbook.
> Contexte machine complet : `docs/DEPLOYMENT_OVH_VPS.md`. Gestes du quotidien :
> `docs/EXPLOITATION.md`.

## 1. Avant : pousser le code

Le VPS tire par `git pull --ff-only` la **branche courante** du clone `/opt/labuse/app`
(`feat/vps-golive` tant que non mergée, `main` en régime normal). Donc :

```bash
# Sur le poste local — la branche déployée doit être poussée sur GitHub
git push origin <branche>
```

Vérifier au besoin quelle branche le VPS suit :

```bash
ssh labuse-vps 'sudo -u labuse git -C /opt/labuse/app branch --show-current'
```

## 2. Déployer

```bash
ssh labuse-vps
sudo /opt/labuse/deploy.sh
```

Ce que fait le script, dans l'ordre, avec garde (il s'arrête à la première erreur) :

0. **Backup automatique** de la base (`backup_postgres.sh` — un dump illisible fait échouer
   le déploiement, rien ne part sans point de retour) ;
1. `git fetch` + `git pull --ff-only` sur la branche courante — **le commit d'avant est
   affiché en début de run** (c'est la cible du rollback) ;
2. `pip install -e` dans le venv (les dépendances suivent `pyproject.toml`) ;
3. `labuse init-db` — migrations en schéma **additif idempotent** (`CREATE TABLE IF NOT
   EXISTS`) ;
4. **build du front** (`npm ci` + `npx vite build --base=/`) **seulement si `frontend/` a
   bougé** (ou si `dist/` est absent) ;
5. `systemctl restart labuse` + **healthcheck `/readyz`** : le script attend jusqu'à 60 s que
   `"ready": true` réponde, sinon il sort en erreur avec la commande de rollback.

Succès = dernière ligne du type :

```
✓ [2026-08-27 18:42:10] deploy OK — <avant> → <après>, /readyz ready=true
```

## 3. Vérifier après

```bash
# Santé publique (les deux doivent répondre 200)
curl -sS https://app.labuse.immo/healthz
curl -sS https://app.labuse.immo/readyz

# Le service et ses logs frais
systemctl status labuse --no-pager
journalctl -u labuse -n 50 --no-pager

# Si le front a été rebuildé : recharger l'app dans le navigateur (Cmd+Shift+R)
# — index.html est en no-cache, les assets hashés suivent tout seuls.
```

Puis un tour d'écran rapide : login, une fiche parcelle, la carte.

## 4. Rollback (manuel — jamais automatique, pour ne rien masquer)

Le commit d'avant (`AVANT`) est affiché au début du run de `deploy.sh`.

```bash
# 1) Code : revenir au commit d'avant
sudo -u labuse git -C /opt/labuse/app reset --hard <AVANT>
sudo -u labuse /opt/labuse/venv/bin/pip install -e /opt/labuse/app
sudo systemctl restart labuse
curl -fsS http://127.0.0.1:8000/readyz          # "ready": true attendu

# 2) Base : UNIQUEMENT si la migration a abîmé la donnée — restaurer le dump
#    pris à l'étape 0 du déploiement (le plus récent de /var/backups/labuse) :
ls -lt /var/backups/labuse/labuse-labuse-*.dump | head -3
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse restore-db --file /var/backups/labuse/labuse-labuse-<DATE>.dump'
sudo systemctl restart labuse
```

> Le rollback ne supprime jamais les backups ; il restaure par-dessus. En cas de doute sur
> l'état du service après rollback : `docs/EXPLOITATION.md`, geste 10 (« l'app est tombée »).
