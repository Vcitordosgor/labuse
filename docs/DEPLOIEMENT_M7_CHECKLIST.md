# Checklist de déploiement — voie M7 (merge → deploy → smoke)

> Procédure **testée** (déploiement du 2026-07-23). Le code part du Mac en rsync ; le VPS n'a aucun credential git. Tout aux **heures creuses** (Réunion endormie ; le backup tourne à 03:00 UTC). Rien ne touche la donnée servie → **golden 116/116 exigé à la fin**.

## 0. Pré-vol (lecture seule)
```bash
git fetch origin -q && git log --oneline origin/main -5      # les merges attendus sont là ?
# fenêtre + secret + trafic réel :
ssh labuse-vps 'echo "UTC $(date -u +%H:%M) / Réunion $(TZ=Indian/Reunion date +%H:%M)"'   # loin de 03:00 UTC
ssh labuse-vps 'sudo grep -c "^LABUSE_SECRET_KEY=." /etc/labuse/labuse.env'                 # = 1 (sinon l'app refuse de démarrer)
# sessions actives (idéalement 0) :
ssh labuse-vps 'sudo -u labuse bash -c "set -a;. /etc/labuse/labuse.env;set +a; psql \"\$(printf %s \$LABUSE_DATABASE_URL|sed s/+psycopg//)\" -tAc \"select count(*) from sessions_auth where expire_at>now()\""'
```
**Gate** : secret présent, hors fenêtre backup, peu/pas de sessions → on continue.

## 1. Déployer le code
```bash
git worktree add --detach /tmp/labuse-deploy-wt origin/main       # arbre PROPRE de main
bash /tmp/labuse-deploy-wt/deploy/scripts/deploy_app.sh labuse-vps # rsync + venv + IMPORT-SMOKE + dist
```
- L'import-smoke (`import labuse.api.app, labuse.comptes, labuse.api.tenant, labuse.api.events`) **fait échouer le déploiement AVANT tout restart** si une dépendance cœur manque. Ne pas ignorer un échec ici.
- `deploy_app.sh` ne fait PAS le restart ni le Caddyfile (étapes 2-3).

## 2. Caddyfile (seulement s'il a changé)
```bash
# le seul delta doit être ton changement — vérifie :
ssh labuse-vps 'sudo diff /etc/caddy/Caddyfile /opt/labuse/app/deploy/Caddyfile.prod'
# backup + install + VALIDATION NATIVE (--envfile : PAS de sourcing bash, sinon le hash bcrypt
# CADDY_BASIC_HASH est corrompu par l'expansion des `$` → faux « illegal base64 ») :
ssh labuse-vps 'sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date -u +%Y%m%d%H%M) \
  && sudo cp /opt/labuse/app/deploy/Caddyfile.prod /etc/caddy/Caddyfile \
  && sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile --envfile /etc/caddy/labuse.env'
# → « Valid configuration » AVANT de recharger. Si erreur : restaurer le .bak, NE PAS reload.
ssh labuse-vps 'sudo systemctl reload caddy && systemctl is-active caddy'
```
Vérifs externes (depuis le Mac, sans identifiants) :
```bash
curl -s -o/dev/null -w '%{http_code}\n' https://app.labuse.immo/healthz          # 401 = rideau intact
curl -s -o/dev/null -w '%{http_code}\n' https://app.labuse.immo/stripe/webhook    # ≠ 401 = webhook exempté (405 GET)
```

## 3. Redémarrer l'app
```bash
ssh labuse-vps 'sudo systemctl restart labuse'
# attendre healthz 200 (~5-8 s), puis :
ssh labuse-vps 'sudo journalctl -u labuse --since "1 min ago" --no-pager | grep "schéma"'   # les 2 workers = schéma=ok
ssh labuse-vps 'sudo journalctl -u labuse --since "2 min ago" --no-pager | grep -c "schéma=échec"'  # = 0 (verrou A5)
```
- La migration (`ensure_scoping`) tourne dans le lifespan, sérialisée par l'advisory-lock A5 → **les 2 workers finissent `schéma=ok`**, plus de course `CREATE TYPE`.

## 4. Smoke — le gate éliminatoire
```bash
# secrets QA depuis ~/labuse-backups/M7_SECRETS.txt (jamais en git) — cf. DEPLOY_RUNBOOK.md
# ⚠ l'IP QA du Mac doit être dans LABUSE_QA_ALLOWLIST (elle tourne) — procédure : DEPLOY_RUNBOOK.md
ssh -N -L 15432:127.0.0.1:5432 labuse-vps &        # tunnel DB (face base du golden)
LABUSE_QA_TARGET=https://app.labuse.immo LABUSE_QA_BASIC=… LABUSE_QA_PASSWORD=… \
LABUSE_DATABASE_URL=postgresql://labuse:…@127.0.0.1:15432/labuse \
  python qa/golden_check.py            # attendu : 116/116 PASS
LABUSE_QA_BASIC=… LABUSE_QA_PASSWORD=… qa/smoke_prod.sh https://app.labuse.immo   # attendu : VERT
```
**Gate final** : golden **116/116**, smoke **VERT**. Sinon → diagnostiquer avant de laisser en l'état.

## 5. Nettoyage
```bash
git worktree remove --force /tmp/labuse-deploy-wt && git worktree prune
```

---

## Rollback
- **Code** : `git worktree add /tmp/wt-rollback <commit-précédent>` puis re-`deploy_app.sh` + `systemctl restart labuse`.
- **Caddyfile** : `sudo cp /etc/caddy/Caddyfile.bak.<stamp> /etc/caddy/Caddyfile && sudo systemctl reload caddy`.
- **DB** : `ensure_scoping` est idempotent et additif — aucun rollback de schéma nécessaire pour un simple redéploiement de code.

## Pièges connus
- `caddy validate` : **toujours `--envfile`**, jamais sourcer l'env en bash (corrompt le hash bcrypt).
- `psql` sur le VPS : `LABUSE_DATABASE_URL` est un DSN SQLAlchemy → `sed 's/+psycopg//'` avant psql.
- `LABUSE_SECRET_KEY` absente hors `local` → l'app **refuse de démarrer** (fail-closed) : c'est voulu, pose la clé.
- Ne jamais utiliser le serveur `:8010` local (build stale) pour un golden — booter sa propre instance.
