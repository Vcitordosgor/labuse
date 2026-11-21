# ÉTUDE — bornes & timeouts — borne 120 s, marge 150 s (ETUDE-PLAFOND-1)

La borne de l'Étude de faisabilité passe de **60 s à 120 s** (ETUDE-PLAFOND-1, décision Vic). Motif :
on LAISSE le calcul finir plutôt que de rendre « partielle ». La **prod (VPS) est ~1,7× plus lente**
que le Mac (3,25 s vs 1,91 s sur la même boucle) ; à N=150 GARDÉ (le résultat ne baisse pas),
Saint-André (30,4 s froid sur le Mac) y prend **50–75 s**, au bord ou au-dessus de l'ancien plafond
de 60 s. Le filet interne de la grille passe de 57 à **100 s** (toujours SOUS la borne → « partielle »
reste signalée AVANT la mise à mort). Tout ce qui attend DERRIÈRE est aligné sur **150 s** (30 s
au-dessus de la borne) pour que le client reçoive TOUJOURS le message honnête « Étude trop lourde »
de l'app, jamais une coupure réseau (504/000) silencieuse.

> Historique : borne 30 s → 60 s (ÉTUDE V6-2 Lot 3), marge aval 75 s → 90 s (CORRECTIFS-2 Lot 2),
> puis borne 60 s → **120 s** et marge aval 90 s → **150 s** (ETUDE-PLAFOND-1).
>
> La borne `etude_timeout_s` couvre le **calcul** (et, pour la route PDF, le rendu qui suit) : le
> processus enfant est TUÉ (SIGTERM → SIGKILL) à cette borne. Le `--timeout-keep-alive` d'uvicorn
> (75 s) borne les connexions **INACTIVES**, sans effet sur la durée d'une requête EN VOL → inchangé.
> Le proxy réellement servi en prod est **Caddy** (`nginx` est un vestige, gardé aligné par cohérence).

## Pourquoi aucune limite plus basse ne coupe avant 120 s (vérifié)
- **Filet grille** `etude_grille_garde_fou_s = 100 s` : SOUS la borne → rend « partielle » (honnête),
  ne coupe pas la requête.
- **`statement_timeout` (60 s)** `config.py:api_statement_timeout_ms` : posé en `SET LOCAL` **uniquement
  par `get_db`** (requêtes de l'API). Le calcul d'étude tourne dans un PROCESSUS ENFANT avec
  `session_scope()` (moteur partagé, `db.py` ne pose AUCUN `statement_timeout`) → la grille n'est PAS
  bornée par 60 s. (De toute façon c'est un plafond PAR requête SQL ; la durée d'étude est du CPU Python
  shapely, pas une seule requête.)
- **File d'attente** `etude_file_attente_s = 20 s` : délai d'attente d'une PLACE avant de spawner (503
  « file pleine »), pas un plafond de durée de calcul.
- **Fetch front** `AbortSignal.timeout(150_000)` : STRICTEMENT au-dessus de la borne (le navigateur
  reçoit le 503 avant d'abandonner).
- **Proxy dev (vite)** `{ target, changeOrigin }` sans `timeout` → défaut Node (~5 min) : ne coupe pas
  en local. En prod, Caddy/nginx à 150 s.

## Ce qui est dans le dépôt (code + conf)
- **App (borne du moteur)** : `src/labuse/config.py` → `etude_timeout_s = 120.0`
  (env `LABUSE_ETUDE_TIMEOUT_S`) + `etude_grille_garde_fou_s = 100.0` (filet).
- **Front (garde-fou fetch)** : `frontend/src/lib/api.ts` → `ETUDE_FETCH_TIMEOUT_MS = 150_000` sur
  `postEtude` ET le PDF.
- **nginx (vestige)** : `deploy/nginx/labuse.conf` → `proxy_read_timeout 150s` / `proxy_send_timeout 150s`.
- **Caddy (prod, servi)** : `deploy/Caddyfile.prod` → `reverse_proxy … { transport http { read_timeout 150s } }`.
- **systemd / uvicorn** : `deploy/systemd/labuse.service` → `--timeout-keep-alive 75` (inactif ≠ requête, inchangé).

## Geste de PRODUCTION (Vic) — à faire sur le VPS, pas par le code
Le VPS n'est PAS modifié par ce dépôt. Déployer les fichiers ci-dessus puis **recharger** chaque brique :

1. **Proxy** — selon ce qui tourne en prod :
   - nginx : copier `deploy/nginx/labuse.conf` → `/etc/nginx/…`, puis
     `sudo nginx -t && sudo systemctl reload nginx`.
   - Caddy : copier `deploy/Caddyfile.prod` → `/etc/caddy/Caddyfile`, puis
     `sudo systemctl reload caddy` (ou `caddy reload`).
   (La prod n'utilise qu'UN des deux : recharger CELUI qui sert `app.labuse.immo`.)
2. **App / uvicorn** — pas de geste si la borne est prise par défaut (`config.py`) ; sinon poser
   `LABUSE_ETUDE_TIMEOUT_S=120` dans `/etc/caddy/labuse.env` (ou l'env du service) puis
   `sudo systemctl restart labuse`.
3. **Front** — rebuild + déploiement habituel du build (le garde-fou fetch est dans le bundle).

## Vérification
- Une étude lourde qui dépasse 120 s renvoie bien un **HTTP 503 `{erreur: etude_trop_lourde}`**
  (message « Étude trop lourde… »), PAS un 504 nginx/Caddy ni un onglet figé.
- Une étude normale (< 20 s en local) est inchangée ; une étude N=150 lourde (Saint-André) ABOUTIT
  (le résultat ne baisse pas) au lieu d'être coupée.
