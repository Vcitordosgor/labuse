# ÉTUDE V6-2 (Lot 3) — bornes & timeouts — marge portée à 90 s (CORRECTIFS-2 Lot 2)

La borne de l'Étude de faisabilité passe de **30 s à 60 s** (le sous-sol et la capacité maximale
peuvent demander davantage sur une assiette lourde). Tout ce qui attend DERRIÈRE est aligné sur
**90 s** pour que le client reçoive TOUJOURS le message honnête « Étude trop lourde » de l'app,
jamais une coupure réseau (504/000) silencieuse.

> **CORRECTIFS-2 (Lot 2)** — la marge passe de 75 s (15 s) à **90 s (30 s au-dessus de la borne de
> 60 s)**. La borne `_ETUDE_TIMEOUT_S` ne couvre QUE le **calcul** ; l'**export PDF** de l'étude
> (WeasyPrint, route `/modules/etude/pdf`) rend APRÈS ce calcul. Sur une assiette lourde de 4 parcelles
> à froid, le total (calcul borné à 60 s + rendu) dépassait les 75 s et récoltait un **504 transitoire**
> au premier essai. Le proxy réellement servi en prod est **Caddy** (vérifié : `nginx` est inactif, le
> fichier `deploy/nginx/` reste un vestige aligné par cohérence). Le `--timeout-keep-alive` d'uvicorn
> (75 s) reste inchangé : c'est le délai des connexions **inactives**, sans effet sur la durée d'une requête.

## Ce qui est dans le dépôt (aucune action de code)
- **App (borne du moteur)** : `src/labuse/api/modules.py` → `_ETUDE_TIMEOUT_S = 60`
  (+ `src/labuse/implantation/service.py` budget interne). **Inchangé.**
- **Front (garde-fou fetch)** : `frontend/src/lib/api.ts` → `ETUDE_FETCH_TIMEOUT_MS = 90_000` sur
  `postEtude` et le PDF.
- **nginx (vestige)** : `deploy/nginx/labuse.conf` → `proxy_read_timeout 90s` / `proxy_send_timeout 90s`.
- **Caddy (prod, servi)** : `deploy/Caddyfile.prod` → `reverse_proxy … { transport http { read_timeout 90s } }`.
- **systemd / uvicorn** : `deploy/systemd/labuse.service` → `--timeout-keep-alive 75` (inactif ≠ requête, inchangé).

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
