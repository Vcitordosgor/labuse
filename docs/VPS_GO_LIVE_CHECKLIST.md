# LA BUSE — Checklist GO-LIVE VPS OVH

> Checklist opérationnelle, à cocher dans l'ordre. Détails techniques : `docs/DEPLOYMENT_OVH_VPS.md`.
> Règle d'or : **un dump frais existe avant toute action irréversible**, et le **rollback est testé**.

---

## ✅ AVANT la migration (préparation, hors production)

- [ ] Branche `claude/brave-davinci-NaRd4` **mergée dans `main`** + tag de release posé (cf. annexe du doc déploiement).
- [ ] `pytest -q` vert et `ruff check src/labuse tests` propre sur `main`.
- [ ] VPS-2 OVH commandé (Ubuntu 24.04, 4 vCores / 8 Go / 75 Go), accès SSH OK.
- [ ] Pare-feu UFW posé (SSH + 80 + 443 uniquement ; **PostgreSQL fermé au monde**).
- [ ] Utilisateur système `labuse` créé ; arborescence `/opt/labuse`, `/etc/labuse`, `/var/backups/labuse`.
- [ ] PostgreSQL 16 + PostGIS 3.4 installés ; `deploy/postgresql/postgresql.vps2.conf` posé en `conf.d` ; `SHOW shared_buffers` = 2GB, `random_page_cost` = 1.1.
- [ ] **Dump frais produit sur la source** (`labuse backup-db`) et `scp` vers `/var/backups/labuse` du VPS.
- [ ] `/etc/labuse/labuse.env` rempli : `LABUSE_ENV=production`, `LABUSE_DATABASE_URL` (mot de passe fort), `LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY` (`openssl rand -hex 32`), `LABUSE_PUBLIC_URL=https://app.labuse.immo`. **Aucun secret dans git.**
- [ ] TTL DNS de `labuse.immo` **abaissé** (ex. 300 s) la veille, pour basculer vite.

## ✅ PENDANT la migration

- [ ] App installée (`git clone main` + venv + `pip install -e .`) ; `labuse --help` répond.
- [ ] Schéma appliqué : `labuse init-db` (idempotent) puis **dump restauré** (`pg_restore`).
- [ ] `labuse doctor --json` → tous les checks critiques au vert.
- [ ] Service systemd actif : `systemctl enable --now labuse` ; `journalctl -u labuse` sans erreur ; `curl 127.0.0.1:8000/healthz` = `{"status":"ok"}`.
- [ ] Nginx posé + `nginx -t` OK ; site activé ; `default` retiré.

## ✅ DNS `labuse.immo`

- [ ] Enregistrements **A (+ AAAA)** créés/mis à jour → IP du VPS pour :
  - [ ] `app.labuse.immo` (l'application)
  - [ ] `labuse.immo` (apex)
  - [ ] `www.labuse.immo`
- [ ] Propagation vérifiée : `dig +short app.labuse.immo` renvoie l'IP du VPS.

## ✅ HTTPS

- [ ] `certbot --nginx -d app.labuse.immo -d labuse.immo -d www.labuse.immo --redirect` → certificat émis.
- [ ] `https://app.labuse.immo/healthz` répond en **200** (cadenas valide).
- [ ] `http://…` redirige bien vers `https://app.labuse.immo`.
- [ ] `certbot renew --dry-run` OK (renouvellement auto).
- [ ] (Après 24-48 h stables) HSTS décommenté dans `deploy/nginx/labuse.conf` + reload.

## ✅ Sauvegardes

- [ ] `deploy/scripts/backup_postgres.sh` testé manuellement → dump daté dans `/var/backups/labuse`, rotation OK, **rien dans `/opt/labuse/app`**.
- [ ] Cron de sauvegarde quotidienne (3h) installé pour l'utilisateur `labuse`.
- [ ] Cron de maintenance hebdo (`db_maintenance.sh`, dimanche 4h) installé.
- [ ] (Recommandé) Offload vers OVH Object Storage configuré (rclone/s3cmd) — rétention longue hors VPS.

## ✅ Test client (recette fonctionnelle)

- [ ] `deploy/scripts/smoke_test.sh` (en local sur le VPS) → tous les tests critiques PASSENT.
- [ ] Depuis un poste externe : connexion sur `https://app.labuse.immo`, **login pilote** OK.
- [ ] Carte se charge (Leaflet **vendorisé** → aucun écran noir même réseau filtré), KPIs remplis.
- [ ] Ouverture d'une fiche réelle (ex. `97415000BK0023`) : verdict, bilan, marché (Obsimmo/loyers/INSEE), export HTML, impression PDF navigateur.
- [ ] `/readyz` public = 200.

## ✅ ROLLBACK (préparé ET répété AVANT le go-live)

- [ ] Tag/commit de la version **précédente** identifié.
- [ ] Dump **d'avant migration** présent dans `/var/backups/labuse`.
- [ ] Procédure répétée à blanc une fois : `git checkout <tag-1>` → `pip install -e .` → (si besoin) `pg_restore --clean` du dump d'avant → `systemctl restart labuse` → `smoke_test.sh`.
- [ ] Critère de déclenchement défini (ex. smoke test rouge, /readyz 503 persistant) + qui décide.

---

### Post go-live (J+1)

- [ ] `journalctl -u labuse --since "1 hour ago"` sans erreur récurrente.
- [ ] Première sauvegarde cron exécutée (vérifier `/var/log/labuse-backup.log`).
- [ ] TTL DNS remonté à une valeur normale (ex. 3600 s).
- [ ] (Optionnel) `labuse bilan-calibrate config/bilan_calibration_vic.csv` une fois les vrais chiffres bilan reçus.
