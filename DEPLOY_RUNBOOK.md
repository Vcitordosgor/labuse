# LA BUSE — Runbook de mise en service pilote (VPS)

> Déployer LA BUSE sur un petit serveur, avec HTTPS, auth, sauvegardes — **sans improvisation**.
> Chaque étape : commande → résultat attendu → quoi faire si ça échoue.

## 0. Architecture

```
                    DNS A : labuse.mondomaine.re → IP du VPS
internet ──443/80──▶ Caddy (HTTPS auto Let's Encrypt, HTTP→HTTPS)
                      │ réseau compose interne
                      ▼
                 app LA BUSE  (loopback hôte uniquement ; auth session applicative)
                      │
                      ▼
                 PostGIS 16   (AUCUN port publié)

Volumes : pgdata (base) · caddy_data (certificats) · ./backups (dumps, montés côté hôte)
Ports publiés : 80, 443 (Caddy) — c'est tout.
Secrets : .env serveur uniquement (gitignoré) — POSTGRES_PASSWORD, LABUSE_AUTH_PASSWORD,
LABUSE_SECRET_KEY, LABUSE_DOMAIN.
Optionnel — assistant IA (3.A) : ANTHROPIC_API_KEY (clé API Anthropic ; sans elle, le bouton
« Expliquer cette parcelle » affiche un message clair et reste inactif). Modèle surchargeable
via LABUSE_ASSISTANT_MODEL (défaut : claude-sonnet-4-6).
```

Dimensionnement pilote constaté : base Saint-Paul complète ≈ 1,5 Go en base, dump **≈ 240 Mo** ;
2 vCPU / 4 Go RAM / 20 Go disque suffisent largement.

## 1. Préparer le serveur (Ubuntu 22.04/24.04)

```bash
ssh root@IP
adduser labuse && usermod -aG sudo labuse            # utilisateur d'exploitation
ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable
```
**Attendu :** `ufw status` → 22, 80, 443 seulement.
**Si échec :** ne pas continuer sans pare-feu actif.

## 2. Installer Docker

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker labuse && su - labuse
docker version && docker compose version
```
**Attendu :** versions affichées sans sudo.
**Si échec :** suivre docs.docker.com/engine/install/ubuntu — ne pas bricoler.

## 3. Copier le projet

```bash
sudo mkdir -p /opt/labuse && sudo chown labuse: /opt/labuse
git clone <dépôt> /opt/labuse && cd /opt/labuse
```
**Attendu :** `git log --oneline -1` montre le commit attendu.

## 4. Créer le .env (secrets)

```bash
cp .env.pilot.example .env
openssl rand -hex 16    # → POSTGRES_PASSWORD
openssl rand -hex 32    # → LABUSE_SECRET_KEY
echo -n 'le-mot-de-passe-client' | sha256sum   # → LABUSE_AUTH_PASSWORD=sha256:<hex>
nano .env               # renseigner aussi LABUSE_DOMAIN
chmod 600 .env
cp deploy/Caddyfile.example deploy/Caddyfile
```
**Attendu :** `.env` complet, lisible par vous seul ; le DNS du domaine pointe déjà vers le VPS.
**Si échec (compose refuse de démarrer plus tard) :** une variable `:?` manque dans `.env`.

## 5. Lancer

```bash
docker compose -f docker-compose.pilot.yml -f docker-compose.caddy.yml up -d --build
docker compose -f docker-compose.pilot.yml ps
```
**Attendu :** `db` healthy, `app` running, `caddy` running ; au premier accès, Caddy
obtient le certificat (quelques secondes).
**Si échec :** `docker compose logs caddy` — cause n°1 : DNS pas encore propagé ou port 80
bloqué (Let's Encrypt doit joindre le serveur).

## 6. Vérifier /healthz

```bash
curl -s https://$LABUSE_DOMAIN/healthz
```
**Attendu :** `{"status":"ok"}` en HTTPS valide ; `curl -sI http://…` → redirection 308 vers https.
**Si échec :** `docker compose logs app` (le process) puis `logs caddy` (le TLS).

## 7. Vérifier /readyz

```bash
curl -s https://$LABUSE_DOMAIN/readyz
```
**Attendu (1ʳᵉ installation) :** `{"ready":false,…}` HTTP 503 — NORMAL : le schéma est posé
(auto au boot) mais les **données** ne sont pas encore construites. Sans session, le détail
est volontairement réduit.
**Si `ready:true` :** base déjà construite (réinstallation) — passer à l'étape 9.

## 8. Construire les données pilote

```bash
docker compose -f docker-compose.pilot.yml exec app labuse prepare-pilot
```
**Attendu :** `✅ PILOTE PRÊT` (≈ 5-10 min la première fois : cadastre + couches + évaluation
+ pré-chauffe ; ≈ 6 s si déjà prêt). Puis `curl /readyz` → 200.
**Si échec :** la sortie nomme l'étape en cause ; `labuse doctor` pour le détail ;
cause n°1 : réseau sortant bloqué (les sources publiques doivent être joignables).

## 9. Première sauvegarde

```bash
docker compose -f docker-compose.pilot.yml exec app labuse backup-db
ls -lh backups/
```
**Attendu :** `labuse-labuse-<date>.dump` ≈ 240 Mo.
**Si échec :** voir le message pg_dump affiché (droits, espace disque).

## 10. Tester la connexion (depuis un poste EXTERNE)

Navigateur → `https://<domaine>/` :
**Attendu :** redirection vers `/login` ; mauvais mot de passe → « Identifiants invalides » ;
bon mot de passe → carte. En navigation privée : `https://<domaine>/stats` → 401.
**Si échec cookie :** vérifier que vous êtes bien en HTTPS (cookie `Secure`).

## 11. Tester la démo

Connecté → bouton **« 🎬 Démo guidée »** : panneau **✅ Démo prête**, 8 parcelles listées,
clic sur BK0023 → fiche instantanée (cache chaud).
**Si « ⚠ Démo non prête » :** le panneau affiche LA commande à lancer — l'exécuter via
`docker compose … exec app <commande>`.

## 12. Tester l'export

Fiche BK0023 → **Export HTML** : document avec « Résumé opportunité », bilan, comparables,
prospection, disclaimers.
**Si échec :** `docker compose logs app` (erreur affichée côté serveur, jamais de stack au client).

## 13. Sauvegarde EXTERNE + cron quotidien

```bash
crontab -e
# 0 3 * * * cd /opt/labuse && ./scripts/backup_daily.sh
scp backups/labuse-*.dump poste-sur:/sauvegardes/labuse/   # copie HORS du serveur
```
**Attendu :** `backups/backup.log` trace chaque nuit ; au moins un dump existe HORS du VPS.
**Si échec cron :** lancer `./scripts/backup_daily.sh` à la main et lire `backups/backup.log`.
Configurer `LABUSE_BACKUP_EXTERN` (montage/rclone) pour automatiser la copie externe.

---

## Exploitation courante

| Besoin | Commande |
|---|---|
| État complet | `docker compose -f docker-compose.pilot.yml exec app labuse doctor` (`--json` pour sonde) |
| Logs app | `docker compose -f docker-compose.pilot.yml logs -f app` |
| Redémarrer | `docker compose -f docker-compose.pilot.yml -f docker-compose.caddy.yml restart` |
| Mettre à jour | `git pull && docker compose … up -d --build` puis `exec app labuse doctor` |
| Restaurer | voir `RESTORE_DRILL.md` (procédure TESTÉE : ~46 s) |
| Changer le mot de passe pilote | éditer `.env` puis `docker compose … up -d app` (déconnecte tout le monde) |

Avant chaque rendez-vous client : `CLIENT_DEMO_CHECKLIST.md`.
