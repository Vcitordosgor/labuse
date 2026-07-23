# Runbook — rotation des clés LABUSE

> **Pour Vic. Procédure pas-à-pas par secret.** Carte des secrets : [`docs/audits/SECRETS_CARTOGRAPHIE.md`](audits/SECRETS_CARTOGRAPHIE.md).
> Règle d'or : **poser la nouvelle valeur et vérifier qu'elle marche AVANT de révoquer l'ancienne.** Inverser l'ordre = coupure.
> Ordonné du **moins risqué au plus risqué**. 🕐 = à faire aux heures creuses (coupe le service).

**Rappel emplacements** : Mac `~/Desktop/labuse/.env` + `~/labuse-backups/M7_SECRETS.txt` ; VPS `/etc/labuse/labuse.env` (app), `/etc/caddy/labuse.env` (rideau), `/home/labuse/.pgpass` (backups). Après édition d'un env VPS : `ssh labuse-vps 'sudo systemctl restart labuse'` (app) ou `sudo systemctl reload caddy` (rideau).

---

## 1. `ANTHROPIC_API_KEY` — le plus sûr (aucune coupure)
Repli stub si absente/invalide → **zéro interruption de service**.
1. **Générer** : console.anthropic.com → *Settings → API Keys → Create Key*.
2. **Poser** : `.env` (Mac) et `/etc/labuse/labuse.env` (VPS) → `ANTHROPIC_API_KEY=…`. Mettre à jour `M7_SECRETS.txt` si tu l'y notes.
3. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
4. **Vérifier** : une recherche NL réelle dans l'app renvoie une réponse riche (pas le badge « mode mots-clés »). Ou `labuse` CLI d'IA.
5. **Révoquer** : supprimer l'ancienne clé dans la console Anthropic. Risque si inversé : nul (repli stub).

## 2. `INPI_*`, `MERCIFACTEUR_*`, `SMTP_PASSWORD` — hors service live (ingestion/courrier/mail)
Ne touchent pas le trafic servi.
1. **Générer** : portail INPI / dashboard Merci Facteur / fournisseur SMTP.
2. **Poser** : `.env` (Mac) + `/etc/labuse/labuse.env` (VPS) si utilisé côté VPS.
3. **Redémarrer** : rien pour le service web ; la prochaine ingestion/lettre utilisera la nouvelle valeur.
4. **Vérifier** : lancer l'ingestion concernée (`labuse ingest-dirigeants` pour INPI) / un envoi test Merci Facteur en sandbox.
5. **Révoquer** : l'ancienne, une fois l'ingestion OK.

## 3. `LABUSE_STRIPE_SECRET_KEY` — rotation en douceur (Stripe gère un chevauchement)
1. **Générer** : dashboard.stripe.com → *Developers → API keys → Roll key* (Stripe garde l'ancienne active pendant une fenêtre de grâce).
2. **Poser** : `.env` + `/etc/labuse/labuse.env` → `LABUSE_STRIPE_SECRET_KEY=sk_live_…`.
3. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
4. **Vérifier** : un parcours Checkout test (ou `/onboarding/retour` sur un paiement réel) aboutit ; pas d'erreur d'auth Stripe dans les logs.
5. **Révoquer** : expirer l'ancienne dans Stripe **après** vérif. Risque si inversé : Checkout KO le temps du redéploiement.

## 4. `LABUSE_STRIPE_WEBHOOK_SECRET` — nécessite le dashboard Stripe
1. **Générer** : dashboard Stripe → *Developers → Webhooks → l'endpoint `/stripe/webhook` → Signing secret → Roll*.
2. **Poser** : `.env` + `/etc/labuse/labuse.env` → `LABUSE_STRIPE_WEBHOOK_SECRET=whsec_…`.
3. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
4. **Vérifier** : dashboard Stripe → *Send test webhook* → l'app répond **200** (pas 400 « signature invalide »).
5. **Révoquer** : l'ancien signing secret. Risque si inversé : les webhooks tombent en 400 → activations de compte manquées (le filet `reconcile_abonnement` rattrape, mais à éviter).

## 5. 🕐 `CADDY_BASIC_AUTH_PASSWORD` / `CADDY_BASIC_HASH` — change le rideau (coupe l'accès web)
1. **Générer** : nouveau mot de passe fort **et son hash bcrypt** : `ssh labuse-vps 'caddy hash-password --plaintext "NOUVEAU_MDP"'`.
2. **Poser** : `/etc/caddy/labuse.env` → `CADDY_BASIC_HASH=<hash>` (VPS) ; noter le mot de passe clair dans `M7_SECRETS.txt` (`CADDY_BASIC_AUTH_PASSWORD`).
3. **Recharger** : `ssh labuse-vps 'sudo systemctl reload caddy'` (reload, pas restart — pas de coupure TLS).
4. **Vérifier** : `curl -u labuse:NOUVEAU_MDP https://app.labuse.immo/healthz` → 200 ; sans creds → 401.
5. **Révoquer** : l'ancien hash est déjà remplacé (un seul à la fois). ⚠ Mets à jour **`LABUSE_QA_BASIC`** partout où tu lances le smoke/golden. Risque si mal fait : plus personne (ni toi) ne passe le rideau → SSH + reload pour corriger.

## 6. 🕐 `LABUSE_AUTH_PASSWORD` — mot de passe pilote (fail-closed sans lui)
Absent → routes métier en **503** (fail-closed). Change le login pilote.
1. **Générer** : mot de passe fort (ou `sha256:<hex>` si tu préfères ne pas le stocker en clair — `auth.password_ok` accepte les deux).
2. **Poser** : `/etc/labuse/labuse.env` → `LABUSE_AUTH_PASSWORD=…` ; `M7_SECRETS.txt`.
3. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
4. **Vérifier** : login pilote via l'app avec le nouveau mdp → session OK (`/parcels?limit=1` ≠ 401). Mettre à jour `LABUSE_QA_PASSWORD` pour le smoke/golden.
5. **Révoquer** : un seul mdp actif à la fois. Risque si vide/typo : 503 total → SSH pour corriger.

## 7. 🕐 `LABUSE_SECRET_KEY` — invalide TOUTES les sessions
Rotation = tous les utilisateurs connectés sont **déconnectés** (les cookies signés deviennent invalides). Fail-closed hors `local` : si absente au boot, l'app **refuse de démarrer**.
1. **Générer** : `openssl rand -hex 32`.
2. **Poser** : `/etc/labuse/labuse.env` → `LABUSE_SECRET_KEY=<64 hex>` ; `M7_SECRETS.txt`. **Ne jamais la laisser vide hors local.**
3. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
4. **Vérifier** : `curl .../healthz` 200 (l'app a démarré = clé présente), puis re-login → session neuve OK.
5. **Révoquer** : rien à révoquer (clé unique) — l'effet « révocation » est immédiat (anciennes sessions mortes). Risque si vide : l'app **ne démarre pas** (fail-closed) → poser la clé + restart.

## 8. 🕐🕐 Mot de passe Postgres (`PG_LABUSE_PASSWORD` / DSN / `.pgpass`) — le plus risqué, COORDONNÉ
Vit à **trois** endroits qui doivent bouger ensemble.
1. **Générer** : mot de passe fort.
2. **Changer dans Postgres** : `ssh labuse-vps 'sudo -u postgres psql -c "ALTER ROLE labuse WITH PASSWORD '"'"'NOUVEAU'"'"'"'`.
3. **Poser aux 3 endroits** :
   - VPS `/etc/labuse/labuse.env` → `LABUSE_DATABASE_URL=postgresql+psycopg://labuse:NOUVEAU@localhost:5432/labuse`
   - VPS `/home/labuse/.pgpass` → ligne `localhost:5432:labuse:labuse:NOUVEAU` (perms 600)
   - Mac `.env` (DSN via tunnel) + `M7_SECRETS.txt` (`PG_LABUSE_PASSWORD`)
4. **Redémarrer** : `ssh labuse-vps 'sudo systemctl restart labuse'`.
5. **Vérifier** : `curl .../readyz` → `ready:true` (l'app parle à la DB) ; un backup manuel `sudo -u labuse pg_dump` fonctionne (`.pgpass` OK). ⚠ **Ordre impératif** : changer le mot de passe Postgres AVANT ou en même temps que les 3 fichiers — si tu changes les fichiers d'abord, l'app perd la DB ; si tu changes Postgres d'abord sans les fichiers, idem. Fais-le d'un bloc, aux heures creuses.
6. **Révoquer** : le mot de passe est remplacé atomiquement par `ALTER ROLE` (pas de chevauchement Postgres) → d'où l'importance de tout poser dans la même fenêtre.

## 9. Clé SSH Mac→VPS (`~/.ssh/labuse_vps_ed25519`) — poser la nouvelle AVANT de retirer l'ancienne
Casse deploy + pull backups si mal fait.
1. **Générer** : `ssh-keygen -t ed25519 -f ~/.ssh/labuse_vps_ed25519_new`.
2. **Ajouter la nouvelle pubkey au VPS** : `ssh-copy-id -i ~/.ssh/labuse_vps_ed25519_new.pub labuse-vps` (l'ancienne marche encore).
3. **Basculer** : pointer `~/.ssh/config` Host `labuse-vps` sur la nouvelle clé.
4. **Vérifier** : `ssh labuse-vps 'echo ok'` passe avec la nouvelle clé ; un `deploy_app.sh` à blanc / un `pull_backups.sh` marchent.
5. **Révoquer** : retirer l'ancienne pubkey de `~labuse/.ssh/authorized_keys` (et `~ubuntu/…`) sur le VPS. Risque si inversé : plus d'accès SSH → console OVH pour rentrer.

---

## B4 — Ordre recommandé + checklist coffre-fort

### Ordre de rotation conseillé (du plus sûr au plus risqué)
1. Anthropic → 2. INPI/MerciFacteur/SMTP → 3. Stripe secret → 4. Stripe webhook → 5. 🕐 Caddy basic_auth → 6. 🕐 mot de passe pilote → 7. 🕐 `LABUSE_SECRET_KEY` → 8. 🕐🕐 Postgres → 9. clé SSH.

**Urgents ?** Aujourd'hui, **aucune fuite avérée** (cf. cartographie F2/F3/F4 : rien dans git/shell/code). Donc pas de rotation d'urgence. **Priorise ce qui a pu transiter dans un canal moins maîtrisé** (chat, capture d'écran, e-mail) : si un secret précis a été partagé ainsi, rote celui-là en premier. Sinon, une rotation d'hygiène planifiée (secret_key + Postgres aux heures creuses) suffit.

### À mettre dans Bitwarden (un item par secret, libellé suggéré)
- `LABUSE — Postgres (labuse role)` → PG_LABUSE_PASSWORD *(note : 3 emplacements — env VPS, .pgpass VPS, .env Mac)*
- `LABUSE — SECRET_KEY (signature sessions/paiement)` → 64-hex *(rotation = déconnexion globale)*
- `LABUSE — mot de passe pilote (LABUSE_AUTH_PASSWORD)`
- `LABUSE — Caddy rideau (basic_auth labuse)` → mot de passe clair + note « hash bcrypt dans /etc/caddy/labuse.env »
- `LABUSE — Stripe secret key (sk_live)`
- `LABUSE — Stripe webhook secret (whsec)`
- `LABUSE — Anthropic API key`
- `LABUSE — INPI (API + SFTP)` → 4 champs
- `LABUSE — Merci Facteur (API key + secret)`
- `LABUSE — SSH Mac→VPS (labuse_vps_ed25519)` → attacher le fichier de clé privée, note « pubkey sur authorized_keys VPS »
- `LABUSE — SMTP` (si/quand branché)

Une fois tout dans Bitwarden : `M7_SECRETS.txt` reste le miroir local d'urgence (chmod 600) mais Bitwarden devient la source de vérité. Ne jamais committer, ne jamais coller dans un chat/log.

*Fin M5-B3/B4.*
