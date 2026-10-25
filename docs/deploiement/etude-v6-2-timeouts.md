# ÉTUDE V6-2 (Lot 3) — bornes & timeouts alignés sur 60 s / 75 s

La borne de l'Étude de faisabilité passe de **30 s à 60 s** (le sous-sol et la capacité maximale
peuvent demander davantage sur une assiette lourde). Tout ce qui attend DERRIÈRE est aligné sur
**~75 s** (15 s de marge) pour que le client reçoive TOUJOURS le message honnête « Étude trop lourde »
de l'app, jamais une coupure réseau (504/000) silencieuse.

## Ce qui est déjà dans le dépôt (aucune action de code)
- **App (borne du moteur)** : `src/labuse/api/modules.py` → `_ETUDE_TIMEOUT_S = 60`
  (+ `src/labuse/implantation/service.py` budget interne).
- **Front (garde-fou fetch)** : `frontend/src/lib/api.ts` → `ETUDE_FETCH_TIMEOUT_MS = 75_000` sur
  `postEtude` et le PDF.
- **nginx (prod)** : `deploy/nginx/labuse.conf` → `proxy_read_timeout 75s` / `proxy_send_timeout 75s`.
- **Caddy (prod, si utilisé)** : `deploy/Caddyfile.prod` → `reverse_proxy … { transport http { read_timeout 75s } }`.
- **systemd / uvicorn** : `deploy/systemd/labuse.service` → `--timeout-keep-alive 75`.

## Geste de PRODUCTION (Vic) — à faire sur le VPS, pas par le code
Le VPS n'est PAS modifié par ce dépôt. Déployer les fichiers ci-dessus puis **recharger** chaque brique :

1. **Proxy** — selon ce qui tourne en prod :
   - nginx : copier `deploy/nginx/labuse.conf` → `/etc/nginx/…`, puis
     `sudo nginx -t && sudo systemctl reload nginx`.
   - Caddy : copier `deploy/Caddyfile.prod` → `/etc/caddy/Caddyfile`, puis
     `sudo systemctl reload caddy` (ou `caddy reload`).
   (La prod n'utilise qu'UN des deux : recharger CELUI qui sert `app.labuse.immo`.)
2. **App / uvicorn** — copier `deploy/systemd/labuse.service` → `/etc/systemd/system/`, puis
   `sudo systemctl daemon-reload && sudo systemctl restart labuse`.
3. **Front** — rebuild + déploiement habituel du build (le garde-fou fetch est dans le bundle).

## Vérification
- Une étude lourde qui dépasse 60 s renvoie bien un **HTTP 503 `{erreur: etude_trop_lourde}`**
  (message « Étude trop lourde… »), PAS un 504 nginx/Caddy ni un onglet figé.
- Une étude normale (< 20 s en local) est inchangée.
