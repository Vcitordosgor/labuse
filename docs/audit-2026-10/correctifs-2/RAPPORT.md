# CORRECTIFS-2 — rapport

> **Note de nommage.** Le mandat parle de « CORRECTIFS-1 / worktree labuse-correctifs1 / ports
> 8960-6160 / rapport `correctifs-1/` ». Le worktree réellement fourni est **`labuse-correctifs2`**,
> la branche **`fix/correctifs-2`** (base `a951c0cba`, la prod du 29/10). Tout a été fait sur cette
> branche ; le rapport est donc classé sous `correctifs-2/`. Rien n'a été écrit en prod ; rien sous
> `pige/` ni l'extension Radar n'a été touché (session RADAR-FIX-3 en parallèle). Serveur local sur
> 8960, base servie Mac (`postgresql:///labuse`).

Deux lots indépendants, un commit.

---

## Lot 1 — `etat_bien` absent du cache de la fiche

### Constat reproduit
`etat_bien` (nature de la parcelle : `nu` / `bati_encore` / `bati_max` / `non_mesure`) est **calculé
en direct** par une même expression SQL, `_ETAT_BIEN_SQL` (`src/labuse/api/app.py:3856-3863`), à partir
de **`parcel_residuel.taux_emprise_pct`** (seuil < 5 % → nu) et `sdp_residuelle_m2` (SDP résiduelle > 0
→ encore constructible).

Cette expression est servie par **quatre** chemins… sauf la fiche :

| Chemin | Fichier | `etat_bien` servi ? |
|---|---|---|
| Liste / carte (panneau) | `app.py:4073` `_q_v2_list` (jointure `LEFT JOIN parcel_residuel rb`) | **oui** (live) |
| GeoJSON carte | `app.py:3723` `_q_v2_geojson` | **oui** (live) |
| Projets / parcours | `projets.py:1180` et `projets.py:1635` | **oui** (live) |
| **Fiche** `GET /parcels/{idu}` | `app.py:_q_v2_fiche` | **NON** |

### Pourquoi il était perdu entre le calcul et le cache servi
`_q_v2_fiche` (constructeur de la fiche premium servie et **mise en cache** par `_fiche_servie`)
**ne joignait pas `parcel_residuel`** dans sa requête d'en-tête (`head`) et **n'incluait pas**
`etat_bien` dans son dict de retour. Le champ n'était donc jamais ni calculé ni posé sur la fiche :
**0 / 434 582** parcelles le portaient dans le payload de fiche. C'est exactement le constat laissé
par ANNONCE-3 dans `pige/api.py:1242` (« ce champ, pourtant calculé en direct, n'est PAS peuplé sur
la base servie (0 parcelle le porte) »).

### Correctif (`src/labuse/api/app.py`, 1 fichier)
Dans `_q_v2_fiche`, la requête `head` :
- gagne `LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id` (même source que le résiduel) ;
- sélectionne `{_ETAT_BIEN_SQL} AS etat_bien` (la **même** expression que la liste — la fiche et la
  liste ne peuvent plus diverger) ;
et le dict de retour gagne `"etat_bien": head["etat_bien"]`.

`parcel_residuel` est à **1 ligne max par `parcel_id`** (vérifié en base : `max = 1`) → le `LEFT JOIN`
ne duplique pas la ligne d'en-tête, et une parcelle sans mesure retombe sur `'non_mesure'` (comme la
liste). Aucune autre logique changée.

### Preuve locale (CX0800 nue, BN2715 bâtie)
Source `parcel_residuel.taux_emprise_pct` :

| IDU | `taux_emprise_pct` | `sdp_residuelle_m2` | `etat_bien` attendu |
|---|---|---|---|
| `97413000CX0800` (Saint-Leu) | 0 | 1412 | `nu` |
| `97422000BN2715` (Le Tampon) | 17 | 375 | `bati_encore` |

Endpoint live après correctif (`GET /parcels/{idu}` sur :8960) :

```
/parcels/97413000CX0800 → etat_bien = 'nu'          (nue  ✓)
/parcels/97422000BN2715 → etat_bien = 'bati_encore' (bâtie ✓)
```

Et le cache partagé se re-peuple **avec** le champ :
`fiche_cache` → `has_etat_bien = t`, valeurs `nu` / `bati_encore`.

### Écrans & documents qui lisent `etat_bien` — et ce qu'ils montraient faute de la valeur **de fiche**
Résultat honnête : **aucune case vide visible à l'écran** — le trou de la fiche était masqué, soit par
un recalcul live ailleurs, soit par un contournement.

1. **Liste de résultats** — `frontend/.../panel/ResultsSection.tsx:92-96` (badge « Nu / Bâtie ») et
   `segmentOf` (`:274-277`, segment Terrain nu / Bâti à densifier). Lit `ParcelProps.etat_bien`, **servi
   par `_q_v2_list` / `_q_v2_geojson`** → affichage **correct**, jamais affecté par le trou de la fiche.
2. **Tableau Projets** — `frontend/.../projets/ProjetKanban.tsx:29-33,112` (`etatLabel`). Lit
   `ParcoursItem.etat_bien`, **servi par `projets.py`** → affichage **correct**, jamais affecté.
3. **La fiche parcelle** (`GET /parcels/{idu}`) — ne servait **aucun** `etat_bien`. Aucun composant
   « fiche » du front ne l'affiche aujourd'hui, donc **pas de régression d'écran** ; mais la fiche était
   **incohérente avec la liste** (même parcelle : la liste dit « Nu », la fiche était muette).
4. **Documents (PDF)** — aucun builder sous `src/labuse/exports/` ne lit `etat_bien`. L'outil
   « Analyser une annonce » (ANNONCE-3) avait besoin de la nature → l'a **contournée** dans
   `pige/api.py:_nature_parcelle` (`:1238-1273`) en **recalculant** depuis `parcel_residuel`. Le PDF/écran
   d'annonce affichait donc la bonne nature **malgré** le trou, au prix d'une logique dupliquée.

> **Conséquence du correctif.** La fiche sert désormais `etat_bien` (cohérence fiche ↔ liste rétablie),
> et le contournement `_nature_parcelle` d'ANNONCE-3 devient **redondant**. Il **n'a pas été modifié**
> (interdit de toucher `pige/`) : une session habilitée pourra plus tard le simplifier pour lire le
> champ de fiche au lieu de recalculer.

### Déploiement : recalcul / invalidation du cache ?
**Non, aucun geste manuel n'est nécessaire** — le déploiement standard invalide déjà les deux étages
du cache de fiche :

- **L2 (cache partagé en base `fiche_cache`)** : sa clé `cle_fraicheur` inclut `code_sha()` via
  `empreinte_attendue` (`fraicheur_caches.py:78-83`), et `code_sha()` lit `config/deploiement.json.sha`
  réécrit à CHAQUE déploiement (`deploy_app.sh:115-128`). **En plus**, `deploy_app.sh:170-172` fait
  explicitement `DELETE FROM fiche_cache` (« nouveau code → code_sha change → … on VIDE »).
- **L1 (cache mémoire par worker)** : vidé par le **restart** du service que tout déploiement effectue
  (`deploy_app.sh:173`).

La fiche se **recalcule paresseusement au premier accès** post-déploiement (pas de recompute de masse ;
la table est bornée). **C'est précisément ce qui expliquait le `None` en local** : mes éditions ne sont
pas commitées → `git HEAD` (donc `code_sha`) inchangé → la ligne `fiche_cache` pré-existante collait
encore → payload périmé servi. Après `DELETE` ciblé + restart, l'endpoint a servi `etat_bien` (preuve
ci-dessus). Au déploiement, le bump de `sha` + le `DELETE FROM fiche_cache` du script jouent le même
rôle, à l'échelle de toute la base.

*Seul cas à surveiller (rappel à Vic, pas une action) :* un hot-swap de code **hors** `deploy_app.sh`
(sans réécrire `config/deploiement.json` et sans `DELETE`) laisserait des fiches périmées jusqu'à
éviction. Le déploiement normal couvre tout.

---

## Lot 2 — timeout du proxy sur l'Étude 4 parcelles

### Proxy réellement servi en prod (lecture seule)
Vérifié **en lecture seule** sur le VPS (`ssh labuse-vps`, aucune écriture) :

```
systemctl is-active caddy → active
systemctl is-active nginx → inactive
caddy version            → v2.11.4
/etc/caddy/Caddyfile      → reverse_proxy 127.0.0.1:8000 { transport http { read_timeout 75s } }
```

→ **Caddy** est le proxy servi (nginx est inactif ; `deploy/nginx/labuse.conf` est un **vestige**,
cf. `docs/DEPLOYMENT_OVH_VPS.md`). Confirmé aussi par `deploy/systemd/labuse.service` et `vps_setup.sh`.

### Rectification de la prémisse
La prémisse du mandat (« le proxy coupe **avant** la borne applicative de 60 s ») **ne tient pas** au
niveau du `read_timeout` : le Caddy **déployé** est **déjà à 75 s** (15 s au-dessus de la borne
`_ETUDE_TIMEOUT_S = 60`, `src/labuse/api/modules.py:2009`) — identique au dépôt (commit `a6e89ad48`,
ETUDE-V6-2 Lot 3, présent dans `main`). Un calcul d'étude de **~51 s** (< 60 < 75) **ne peut pas**
récolter un 504 par ce `read_timeout`.

### Cause réelle du 504 transitoire à froid, et correctif
La borne `_ETUDE_TIMEOUT_S = 60` ne borne que le **calcul** (abandon du thread à 60 s → HTTP 503
honnête, `modules.py:2017-2032`). Mais l'**export PDF** de l'étude (`/modules/etude/pdf`, même
garde-fou fetch) rend le document **APRÈS** ce calcul (WeasyPrint). Sur une assiette lourde de 4 parcelles
**à froid** (buffers disque froids, cf. VITESSE-3), le **total** (calcul borné à 60 s + rendu) peut
dépasser les 75 s du proxy → **504 transitoire au premier essai**, qui disparaît à chaud.

Correctif : **marge portée de 75 s à 90 s** (30 s au-dessus de la borne de 60 s) **dans la configuration
du dépôt uniquement** — rien sur le VPS, la pose se fera au prochain déploiement :

- `deploy/Caddyfile.prod` → `read_timeout 90s` (le proxy servi).
- `frontend/src/lib/api.ts` → `ETUDE_FETCH_TIMEOUT_MS = 90_000` (sinon le navigateur abandonnait à 75 s
  **avant** le proxy — le même constant couvre l'étude JSON et le PDF).
- `deploy/nginx/labuse.conf` → `proxy_read_timeout`/`proxy_send_timeout 90s` (vestige, aligné par cohérence).
- `docs/deploiement/etude-v6-2-timeouts.md` → chaîne décrite à 90 s + raison (rendu PDF après la borne).

Inchangés (volontairement) : `_ETUDE_TIMEOUT_S = 60` (la borne applicative n'est pas l'objet du lot) ;
`--timeout-keep-alive 75` d'uvicorn (délai des connexions **inactives**, sans effet sur la durée d'une
requête).

`caddy validate` n'a **pas** pu être joué en local (Caddy non installé sur le Mac) ; la syntaxe de
`deploy/Caddyfile.prod` est inchangée hormis la valeur numérique `75s→90s`. À valider à la pose :
`caddy validate --config /etc/caddy/Caddyfile` puis `systemctl reload caddy`.

---

## Vérifications
- **Lot 1** : import `labuse.api.app` OK ; endpoint live `/parcels/{idu}` sur les 2 IDU témoins
  (nu / bati_encore) ; `fiche_cache` re-peuplé avec le champ ; `parcel_residuel` prouvé unique par
  `parcel_id` (pas de duplication de ligne).
- **Lot 2** : proxy prod identifié en lecture seule (Caddy actif, nginx inactif, read_timeout déployé
  = 75 s) ; `deploy/Caddyfile.prod` est bien la source posée en prod (`DEPLOYMENT_OVH_VPS.md §10`).
- **Hook** : le pre-commit (`scripts/git-hooks/pre-commit`) est un garde-fou « gros fichiers > 2 Mio » ;
  les 5 fichiers modifiés sont tous de petites éditions texte → **vert**.
- `frontend` : `node_modules` non provisionné dans ce worktree (gotcha connu `npm ci`/symlink) ; la
  modification front est une constante numérique **invariante en type** (`number`).

## Gestes de Vic
Merge `fix/correctifs-2` → déploiement standard (`deploy_app.sh` : bump `deploiement.json` + `DELETE
FROM fiche_cache` + restart). Côté proxy, reposer `/etc/caddy/Caddyfile` depuis `deploy/Caddyfile.prod`
puis `caddy validate && systemctl reload caddy`.
