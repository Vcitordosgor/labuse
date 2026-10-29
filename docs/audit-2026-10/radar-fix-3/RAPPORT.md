# RADAR-FIX-3 — Les fausses suppressions de la passe « confirmation »

Branche `fix/radar-fix-3` · worktree `~/Desktop/labuse-radarfix3` · ports 8950/6150.
**Pas de merge, pas de déploiement : ce sont des gestes de Vic.** Mesure prod en lecture seule.

---

## 1. Constat

La passe de confirmation automatique du **28/10 à 23 h 03** (`pige_passes` id **274**) a marqué
**60 biens sur 60** en `retiree`. Vic en a rouvert 5 : **4 sont toujours en ligne**. Ce sont de
fausses suppressions.

Vérifié en prod (lecture seule) :

```
 id  |    passe     |      captured_at       | source | n_pages | n_supprimees |     créée      →      maj
 274 | confirmation | 2026-10-28 00:00:00+04 | auto   |   60    |     60       | 23:03:56  →  23:17:15
```

Ce n'est pas isolé : la passe id **4 du 26/09** avait déjà fait **107/107**. Deux passes à 100 % de
retraits = la signature d'un blocage pris pour des suppressions de masse, jamais de vraies suppressions.

---

## 2. Cause racine

La décision « supprimée » est prise **dans l'extension** (`outils/radar-extension/background.js`,
fonction `passeConfirmation`), puis le serveur (`/admin/radar/confirmation`) **faisait confiance** à ce
verdict et écrivait `retiree`. Deux défauts se cumulaient dans l'extension :

1. **Regex sur le HTML COMPLET.** Le verdict « supprimée » venait de
   `/page introuvable|cette annonce n'est plus|n'existe plus|404|annonce supprimée|expirée/.test(outerHTML)`.
   Testé sur **tout le `outerHTML`** (scripts, JSON `__NEXT_DATA__`, CSS, bannières), pas sur le texte
   visible. Le jeton nu **« 404 »** se retrouve partout (un prix « 404 000 », un hash d'asset, une route
   Next.js) ; « expirée »/« supprimée » traînent dans les gabarits JS d'autres états. → faux positifs.

2. **`redirectedAway`.** « supprimée » aussi dès que l'URL finale ne contenait plus le `list_id` —
   c.-à-d. dès qu'une page de **consentement / connexion / vérification DataDome / accueil** s'intercalait
   (ce qui arrive pour **toute** une soirée d'un coup). D'où le **60/60** : non pas 60 annonces parties,
   mais 60 liens redirigés/bloqués lus comme « parties ».

Le garde `looksBlocked` (DataDome/captcha) existait mais ne couvrait que les pages criant « datadome /
captcha / vérification » ; un interstitiel muet ou une simple redirection passait à travers et tombait
dans `redirectedAway` → `supprimee`.

**En clair : une page qu'on n'a pas pu lire était comptée comme une annonce partie.**

---

## 3. Neutralisation immédiate — **par le SERVEUR (déploiement ciblé)**

> **Réponse à la question de Vic : c'est le serveur, pas l'extension.**

Pourquoi le serveur :

- L'**écriture** `retiree` se fait côté serveur ; c'est le seul point de passage obligé. Le neutraliser
  là protège la prod **quelle que soit la version de l'extension** chargée dans Chrome.
- L'extension vit dans le navigateur de Vic ; un correctif d'extension n'a d'effet qu'**après
  rechargement manuel** (et on ne sait pas quelle version tourne). Trop lent et trop incertain pour
  l'urgence.
- Un déploiement serveur ciblé (restart API) suffit, sans toucher aux données.

**Ce que fait le correctif serveur** (`src/labuse/pige/api.py`) :

- La voie historique **`POST /admin/radar/confirmation`** (un appel = un lien) **ne retire plus jamais
  rien.** `presente` continue de confirmer les annonces actives ; tout verdict de suppression y est
  désormais compté « non vérifiée » (pas d'écriture de statut). → l'extension actuellement déployée, non
  corrigée, **ne peut plus retirer aucun bien** dès que le serveur est déployé.
- Le retrait n'est possible que par la nouvelle voie **`/admin/radar/confirmation-batch`**, sous preuve
  positive **et** garde-fou (ci-dessous). Le retrait **humain** reste `POST /admin/radar/retiree`.

Donc : **déployer l'API neutralise l'incident tout de suite** ; l'extension corrigée (§4) se recharge
ensuite, à froid, pour rétablir un retrait automatique sûr.

---

## 4. Correctif de fond — on ne retire que sur **preuve positive**

Règle gravée : **un bien n'est retiré que sur preuve positive** —
soit une page « *cette annonce n'est plus disponible / supprimée / désactivée* » **reconnue**,
soit une **vraie page 404** reconnue. Une page **bloquée, vide, illisible ou redirigée** ne retire
**jamais** rien ; elle est comptée **à part** (« non vérifiée »).

### Côté extension (`background.js`)
- `inspectPage` expose maintenant le **texte visible** (`bodyText`) et le `title` ; la reconnaissance se
  fait **sur le texte visible**, plus jamais sur le HTML/JS complet.
- Nouvelle fonction **pure** `classifierConfirmation(info, finalUrl, listId)` :
  - page illisible / `looksBlocked` → **`inconnue`** (non vérifiée) ;
  - **phrases entières** d'expiration reconnues → `supprimee` + preuve **`expiree`** ;
  - page d'erreur 404 reconnue → `supprimee` + preuve **`http_404`** ;
  - on est resté **sur l'annonce** (`list_id` dans l'URL) **et** son contenu s'affiche → `presente` ;
  - sinon (redirigée, vide, non reconnue) → **`inconnue`**.
  La preuve d'expiration **prime** sur la présence d'un prix (une page expirée affiche des annonces
  « recommandées » avec prix — c'est la phrase qui tranche, pas le prix).
- `passeConfirmation` collecte les verdicts et **poste toute la passe en un envoi** (`…/confirmation-batch`) ;
  sur un mur DataDome, elle **s'arrête** (ne martèle pas) — les liens non vus restent « non vérifiés ».

### Côté serveur (`api.py`, défense en profondeur)
- `_classer_confirmation` **re-vérifie la preuve** : `supprimee` n'est honoré en retrait **que** si
  `preuve ∈ {expiree, http_404}`. Sans preuve → « non vérifiée », zéro écriture de statut.
- Nouveau compteur **`pige_passes.n_non_verifiees`** (séparé de `n_supprimees`) : on distingue « on n'a
  pas pu voir » de « l'annonce est partie ». Une ligne de journal par passe le dit.

### Garde-fou des 30 %
Si une passe veut retirer **plus de 30 %** des biens qu'elle a vérifiés (plancher : au moins 5 liens),
elle **n'écrit AUCUN retrait** et se signale en **anomalie** (journal `pige.statut_change` dédié). Les
retraits refusés ne sont pas perdus : les biens restent actifs et seront re-vérifiés à la passe suivante,
une fois le blocage passé. Appliqué sur la **passe entière** (`/confirmation-batch`) — c'est pour ça que
le batch est l'unité. Le 28/10 (60/60 = 100 %) et le 26/09 (107/107) auraient été **bloqués**.

### Tests — un par cas
- **Serveur** `tests/test_pige_confirmation.py` (12 tests, base `labuse_test`) : preuve `expiree` retire ·
  preuve `http_404` retire · `supprimee` **sans** preuve ne retire pas (+ compté non vérifié) · `inconnue`
  non vérifiée · preuve non reconnue non vérifiée · `presente` confirme l'actif · garde-fou **bloque à 40 %**
  (aucun retrait, anomalie) · garde-fou **laisse passer à 30 %** (3 retraits) · voie simple ne retire
  **jamais** · voie simple `presente` confirme · `list_id` inconnu.
- **Extension** `outils/radar-extension/recette_confirmation.mjs` (7 cas) : présente · expirée (preuve) ·
  vraie 404 (preuve) · bloquée DataDome · vide/illisible · redirigée accueil · **bruit « 404 » dans le JS
  → présente** (prouve qu'on ne lit plus le HTML complet). Invariant dur : un `supprimee` **sans** preuve
  positive fait échouer la recette.

---

## 5. Mesure en prod (lecture seule)

Fenêtre `retiree_le ∈ [28/10 23:03, 28/10 23:18]` → **60 biens**, tous actuellement `retiree`,
**0 avec `vendue_le`** (aucun croisé « vendu » par DVF). Aucun n'a de champ `vendue_*` renseigné.

**Les 60 `bien_id` :**

```
114, 115, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148,
149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169,
170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 184, 185, 186, 187, 189, 207, 208
```

→ **Combien ont déjà un `vendue_le` renseigné par le croisement DVF : 0 / 60.**
La restauration des champs `vendue_*` à NULL est donc, en l'état, sans effet destructeur (aucune vente
réelle à préserver) — on les remet néanmoins à NULL par la transaction, comme demandé.

---

## 6. Restauration en prod — **prête, uniquement avec le go de Vic**

Script : `docs/audit-2026-10/radar-fix-3/restauration.sql`. **Une seule transaction**, **exactement ces
60 `bien_id`** : `statut → active`, `retiree_le` et `vendue_*` → `NULL`. On les remet **tous** en actif ;
une fois les passes corrigées, elles retireront la seule qui a vraiment expiré.

Garde-fous intégrés (annulent tout si écart) : exactement 60 lignes, toutes « retiree », **aucune** vente
DVF (si l'une a été vendue entre-temps, la transaction s'annule et ne l'écrase pas). Filet de
réversibilité : table d'audit `pige_restauration_radarfix3` capturant l'état AVANT.

**Sauvegarde vérifiée avant** : une sauvegarde pleine prise **après** l'incident existe —
`/var/backups/labuse/labuse-labuse-20261029-030308.dump` (6,1 Go, **1748 objets**, contient
`TABLE DATA pige_biens`), vérifiée par `pg_restore --list`. Vic peut en prendre une fraîche juste avant.

**Répétition à blanc faite (28→29/10, ROLLBACK forcé, rien écrit en prod)** :
```
BEGIN → SELECT 60 → DO (garde-fous OK) → UPDATE 60 →
 actifs | reste_retiree_le | reste_vendue
   60   |        0         |      0
ROLLBACK
```
Prod re-vérifiée ensuite : les 60 toujours `retiree`, table d'audit absente (rollback propre). **Aucune
écriture prod n'a eu lieu dans tout ce mandat.**

Lancement réel (geste de Vic, après go) :
```
ssh labuse-vps 'sudo -u postgres psql -d labuse -v ON_ERROR_STOP=1 -1 -f -' < restauration.sql
```

---

## 7. Fichiers

| Fichier | Rôle |
|---|---|
| `src/labuse/pige/api.py` | Preuve positive, voie simple neutralisée, `/confirmation-batch`, garde-fou 30 %, comptage non-vérifiées |
| `src/labuse/pige/tables.py` | Colonne `pige_passes.n_non_verifiees` (DDL idempotente) |
| `src/labuse/api/auth.py` | `/admin/radar/confirmation-batch` ajouté à l'allowlist du jeton Radar |
| `outils/radar-extension/background.js` | `bodyText`/`title`, `classifierConfirmation`, passe en batch, arrêt sur blocage |
| `outils/radar-extension/recette_confirmation.mjs` | Recette classification (7 cas) |
| `tests/test_pige_confirmation.py` | 12 tests serveur (un par cas) |
| `docs/audit-2026-10/radar-fix-3/restauration.sql` | Transaction de restauration (go Vic) |

## 8. Vérifications

- `tests/test_pige_confirmation.py` : **12 verts** · `test_pige_api` + `test_pige_cycle` + `test_radar_auto1`
  + `test_auth` : verts (base `labuse_test`, socket openclaw).
- Python unitaires (gate pre-push, `not db`) : **2604 passed**, 2 *erreurs pré-existantes* dans
  `test_donnees_etat_fix1` (rôle `labuse` TCP absent sur ce Mac — prouvé identiques sans mes changements).
- Recettes extension : `recette_confirmation` **7/7**, `recette_alarme` et `recette_bascule` toujours verts.
- Scan de secrets : rien trouvé. Hook pre-commit (gros fichiers) : OK.
- **Front non touché** (diff 100 % backend + extension) → tsc/vitest inchangés ; non rejoués
  (`frontend/node_modules` absent dans ce worktree, limite connue des worktrees).
- 4 tests `pige` DB (`test_pige_client/depot2/digests/socle`) rouges = **pré-existants** (données
  résiduelles de `labuse_test`), prouvés identiques avec mes changements remisés (`git stash`).

## 9. Gestes de Vic (dans l'ordre)

1. **Déployer l'API** (restart) → neutralise l'incident immédiatement (la passe ne retire plus rien).
2. Sur go : lancer `restauration.sql` (sauvegarde fraîche recommandée avant) → les 60 repassent actifs.
3. Recharger l'extension corrigée dans Chrome → le retrait automatique reprend, sous preuve + garde-fou.
4. (Merge de la branche à sa convenance.)
