# LA BUSE — Sécurité & déploiement pilote

> Donner accès à LA BUSE à UN promoteur, en pilote encadré, sans exposer l'app entière
> et sans lancement local fragile. **Ce n'est pas un SaaS** : un compte unique, une
> commune, un client — assumé (cf. §9).

## 1. Architecture pilote

```
client ──HTTPS──▶ reverse proxy (Caddy/nginx/Traefik — TLS)
                      │ :8000
                  app LA BUSE (Docker, non-root, auth session)
                      │ réseau compose interne (5432 non publié)
                  PostGIS 16 (volume pgdata + ./backups)
```

- **Tout est protégé par session** sauf `/healthz` (process), `/readyz` (détails réduits
  sans session), `/login`, `/logout`. `/docs`–`/openapi.json` : locaux uniquement.
- Auth = **un mot de passe pilote** (variable d'env), session cookie signé HMAC
  (httpOnly, SameSite=Lax, **Secure hors local** → HTTPS obligatoire en pilote),
  expiration 12 h, échec neutre + délai anti force-brute + journalisation.
- **Fail-closed** : `LABUSE_ENV=pilot` sans mot de passe → routes métier en **503**,
  jamais « ouvert par accident ».

## 2. Variables d'environnement

| Variable | Obligatoire pilote | Rôle |
|---|---|---|
| `LABUSE_ENV` | oui (`pilot`) | mode : `local` (dev, auth off par défaut) / `pilot` / `production` |
| `LABUSE_AUTH_PASSWORD` | **oui** | mot de passe d'accès — en clair ou `sha256:<hexdigest>` |
| `LABUSE_SECRET_KEY` | **oui** | signature des sessions (`openssl rand -hex 32`) ; absente = sessions perdues à chaque redémarrage |
| `LABUSE_SESSION_HOURS` | non (12) | durée de session |
| `LABUSE_PUBLIC_URL` | non | origine CORS autorisée (vide = même origine uniquement) |
| `POSTGRES_PASSWORD` | **oui** (compose) | mot de passe DB |
| `LABUSE_DATABASE_URL` | géré par compose | URL PostGIS |

Créer le mot de passe (option hash, pour ne pas le mettre en clair dans l'env) :
```bash
echo -n 'le-mot-de-passe' | sha256sum     # → LABUSE_AUTH_PASSWORD=sha256:<hexdigest>
openssl rand -hex 32                      # → LABUSE_SECRET_KEY
```

**Aucun secret n'est committé** : `.env` est gitignoré, le compose pilote **refuse de
démarrer** si `POSTGRES_PASSWORD` / `LABUSE_AUTH_PASSWORD` / `LABUSE_SECRET_KEY` manquent.

## 3. Lancement Docker

```bash
cp .env.example .env                      # puis renseigner les 3 secrets ci-dessus
docker compose -f docker-compose.pilot.yml up -d --build
docker compose -f docker-compose.pilot.yml exec app labuse prepare-pilot   # ≈5 min la 1ʳᵉ fois
docker compose -f docker-compose.pilot.yml exec app labuse doctor          # ✅ PRÊT attendu
```

Puis mettre le reverse proxy HTTPS devant `:8000` (les cookies sont `Secure` : sans
HTTPS, le navigateur ne les renverra pas). `docker-compose.yml` (racine) reste l'aide
**dev** : base seule, identifiants de dev — ne pas l'utiliser pour un pilote.

## 4. Préparation / vérification de la base

| Besoin | Commande |
|---|---|
| Tout préparer (idempotent, saute ce qui est déjà prêt) | `labuse prepare-pilot` |
| Diagnostic complet + réparation légère du schéma | `labuse doctor` (`--json` pour le monitoring) |
| Contrôle 13 points de la démo | `labuse demo-healthcheck` |
| Pré-chauffe + conformité des 8 fiches de démo | `labuse warm-demo` |
| Reconstruction des données (couches + évaluation) | `labuse rebuild-demo --commune 97415` |

## 5. Sauvegarde / restauration

```bash
labuse backup-db                          # → backups/labuse-<db>-AAAAMMJJ-HHMMSS.dump (pg_dump -Fc)
labuse restore-db --file backups/….dump   # confirmation explicite : ÉCRASE la base
labuse doctor                             # toujours vérifier après une restauration
```
- Le dump contient **tout** : parcelles, couches, évaluations, **pipeline de prospection**
  (saisies manuelles — la seule donnée non reconstructible !), cache enrichment, état démo.
- Sous compose : `docker compose -f docker-compose.pilot.yml exec app labuse backup-db`
  (le dossier `backups/` est monté côté hôte). Sortir les dumps de la machine régulièrement.
- Fichier invalide → erreur claire, rien n'est touché. Restauration possible vers une autre
  base : `--target-url postgresql+psycopg://…` (répétition générale sans risque).
- Filet de secours : `rebuild-demo` reconstruit tout depuis les sources publiques **sauf**
  le pipeline → **sauvegarder avant toute opération risquée**.

## 6. Healthcheck & monitoring

| Sonde | Sens | Sans session |
|---|---|---|
| `GET /healthz` | process vivant (zéro DB) | public |
| `GET /readyz` | schéma + données critiques (200/503) | public, **réduit** à `{ready, checked_at}` |
| `GET /demo-status` | état démo complet | protégé (session) |
| `labuse doctor --json` | tout, côté serveur | exit 0/1/2 |

Brancher l'alerte du proxy/orchestrateur sur `/healthz` (redémarrage) et `/readyz`
(état dégradé). Le healthcheck **Docker** intégré sonde `/healthz`. Logs : démarrage
(env/auth/schéma), connexions réussies/refusées (IP), erreurs — via stdout du conteneur.

## 7. Checklist avant d'ouvrir l'accès au client

- [ ] `.env` complet (3 secrets), **jamais** committé ; mot de passe pilote transmis par
      canal séparé ;
- [ ] HTTPS opérationnel devant l'app (cookies Secure) ;
- [ ] `labuse prepare-pilot` → ✅ PILOTE PRÊT ; `doctor --json` → `ready_for_demo: true` ;
- [ ] test depuis un navigateur EXTERNE : `/` redirige vers `/login`, mauvais mot de passe
      refusé, bon mot de passe → carte ; `/stats` sans session → 401 ;
- [ ] `labuse backup-db` exécuté et dump copié HORS de la machine ;
- [ ] rappel des limites au client (pré-analyse ; constructibilité/propriété/rentabilité
      jamais garanties — le produit le dit, le contrat doit le dire aussi).

## 8. Limites de sécurité ASSUMÉES (pilote, pas SaaS)

- **Un seul mot de passe partagé** : pas d'identités individuelles, pas d'audit par
  utilisateur, révocation = changer le mot de passe (déconnecte tout le monde).
- Pas de rate-limit réseau global (seulement un délai sur l'échec de connexion) ;
  à compléter au proxy si exposition large.
- Pas de CSRF token : l'API accepte les requêtes du navigateur connecté (SameSite=Lax
  couvre l'essentiel ; risque résiduel faible pour un pilote mono-utilisateur).
- Sessions non révocables individuellement (signées, sans état serveur) ; expiration 12 h.
- La base n'est pas chiffrée au repos (pas de donnée nominative dedans — prospection
  manuelle exclue des données externes).

## 9. Ce qui n'est PAS encore SaaS (avant exposition publique large)

comptes individuels + rôles · multi-tenant (un client = ses données) · rate-limiting et
WAF · CSRF systématique · gestion de secrets centralisée (vault) · sauvegardes
planifiées + testées automatiquement · supervision/alerting branchés · journaux d'audit
horodatés inviolables · revue de sécurité externe.

---
*LA BUSE vérifie, priorise, explique et organise la prospection — elle ne garantit ni
constructibilité, ni propriété, ni rentabilité. L'accès pilote est restreint et journalisé.*
