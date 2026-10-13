# ÉTAPE 0 — environnement de la chasse (CHASSE-NAV-1)

Date : 13/10/2026. Modèle : Opus. **Lecture seule stricte** (aucune écriture base/VPS, aucune action irréversible).

## Preuves d'amorçage

| Point | Valeur |
|---|---|
| `pwd` | `/Users/openclaw/Desktop/labuse-chasse-nav` (worktree dédié) |
| Branche | `audit/chasse-nav-1` (depuis `main` `5c4b156c`) |
| Arbre | propre avant travaux (seul `docs/audit-2026-10/chasse-nav-1/` ajouté) |
| API | `labuse api --port 8770` → `http://127.0.0.1:8770` · `GET /healthz` = `{"status":"ok"}` · boot `env=local · auth=désactivée (local) · schéma=ok` |
| Front | `vite --port 5970 --host 127.0.0.1` → `http://127.0.0.1:5970/socle/` · proxy `LABUSE_API_DEV=http://127.0.0.1:8770` · `/config/run` 200 via proxy |
| Base | Postgres local `labuse` (rôle OS `openclaw`, trust) — run servi **q_v18** (433 229 parcelles `score_labuse`) |
| App | rendue entièrement (rail 9 vues + header + panneau + carte) — capture `captures/etape0-app-chargee.png` |

Commandes de lancement (variables en ligne, aucun `.env` écrit dans le worktree) :

```
# API
LABUSE_DATABASE_URL='postgresql+psycopg://openclaw@localhost:5432/labuse' LABUSE_ENV=local LABUSE_CONFIG_DIR=config \
  PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -c "from labuse.cli import app; app()" api --port 8770
# Front
LABUSE_API_DEV='http://127.0.0.1:8770' node_modules/.bin/vite --port 5970 --host 127.0.0.1
```

## Mode d'authentification retenu : **local « rideau ouvert » (auth désactivée)**

En `env=local` sans `LABUSE_AUTH_PASSWORD`, `auth.enabled()` renvoie `False` (`src/labuse/api/auth.py:62`) :
- **écrans admin atteignables** — `exiger_admin()` est un no-op en rideau ouvert (`auth.py:211-212`). Le « compte admin local » du mandat est donc satisfait : le dashboard admin est joignable sans mot de passe.
- vues scoped (`/projets`, `/documents`, `/alertes`, `/events`, `/moi`) répondent **200** en mode « pilote/legacy » : `current_compte()` = `None` → données globales/non cloisonnées (`src/labuse/api/tenant.py`).
- **limite connue, pas un écart de navigation** : les routes qui EXIGENT un compte identifié (`compte_ou_401`) renvoient 401 sans session — observé sur `GET /moi/prefs-carte` (2 erreurs console au chargement). Le front traite cet appel en *best-effort* (`onboarding.py:1254` « un enregistrement qui rate ne casse jamais la carte »), donc la carte s'ouvre normalement. En prod avec un compte connecté l'appel renvoie 200. → consigné comme **artefact du mode auth-off**, à re-vérifier avec une vraie session dans CHASSE-NAV-FIX-1 si besoin, mais hors périmètre « bon bouton / bon contexte ».

## Garde-fous actions irréversibles

- **Mail** : `env=local` sans `LABUSE_MAIL_REEL` → `envoi_reel_autorise()` = `False` (`config.py:365`) : tout envoi est journalisé en `.eml`, **0 réseau**. Aucun bouton d'envoi (mail/courrier/invitation) ne sera déclenché ; les destinations/contextes sont relevés par lecture de code.
- **Paiement / suppression / invitation** : relevés sans déclenchement.
- RADAR dépôt de captures : `/srv` read-only → erreur de boot **bénigne** (répertoire de pige inaccessible), non testé (feature admin/extension hors périmètre nav).

## Témoins pressentis (affinés au Lot B)

- Parcelle bizone : `97411000BZ1065` (présente q_v18).
- Projet avec parcelles : `237` (p.ex.), `235 LABUSE TEST`, `236 LABUSTRE TEST 2`.
- Veille : 3 `watch_zones`, 9061 `alertes`.
- Parcelle disparue / surface incertaine / commune : à fixer au Lot B.

## Arrêt (avant de rendre la main)

API + navigateur arrêtés, `lsof` 8770/5970 vérifié vide — fait en fin de mandat.
