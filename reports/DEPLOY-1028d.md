# DEPLOY-1028d — fin de fumée en prod de `4c38f525c` (annonce-1 + remise-1)

Lancé le 29/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps` (`https://app.labuse.immo`).
Périmètre : **fumée de fin** sur la mise en production de `4c38f525c` (merge `feat/annonce-1` +
`fix/remise-1`) — pré-vol et déploiement **déjà faits** et repris du compte-rendu précédent.
**Lecture seule assumée** : rien redéployé, rien modifié en prod, aucun rollback. Seule écriture
technique : une **session de test éphémère** (uid 31), créée puis **purgée** en fin de run (méthode
DEPLOY-1028b), autorisée explicitement par Vic pour fumer les écrans authentifiés.

Mêmes règles que `reports/DEPLOY-1028b.md`.

---

## Étape 0 — garde-fou horaire (fenêtre VACUUM FULL 01 h–03 h 30)

Heure **Réunion du VPS** relevée **avant tout geste** : **00 h 09 min 55** (`TZ=Indian/Reunion`, soit
20:09:55 UTC). **< 00 h 45 → feu vert.** La fumée s'est déroulée de **00 h 15 à 00 h 28** (Réunion),
terminée **largement avant 01 h 00** : le VACUUM FULL n'a jamais été approché ni gêné.

---

## Pré-vol & déploiement — repris du compte-rendu précédent (confirmés en lecture seule)

Le déploiement de `4c38f525c` était **fait et vert** (filet app `app.filet-20261029-000305`, `/readyz`
25/25, aucun 503). Confirmé sur place, sans rien toucher :

- `config/deploiement.json` prod :
  `sha = 4c38f525cd18386bc45e0c1aa3eccb4cf3e90c57`, `par = deploy_app.sh`,
  `deploye_le = 2026-10-28T20:03:46Z` (cohérent avec le filet `…000305` = 29/10 00:03:05 Réunion).
- Run **servi = `q_v20`** (manifeste intact).
- Le code prod est déployé **sans `.git`** (rsync) → `git rev-parse` distant = `no-git` (normal).

`4c38f525c` apporte en prod les deux chantiers que cette fumée vérifie :
**ANNONCE-1** (outil « Analyser une annonce », entrées adresse + lien Leboncoin) et **REMISE-1**
(affichage du régime de stationnement L151-35/36 suivant la règle de Vic).

### Session de test (jeton jamais affiché)
Compte `gb-test-ae` = **utilisateur id 31**. Session serveur **3 h** via `comptes.creer_session(db, 31, 3)` ;
le jeton est écrit dans un **curlrc `600`** (`/tmp/.gb1028d.curlrc`, user `labuse`) lu par `curl -K`
(cookie `labuse_session=u.<token>`), **jamais imprimé**. Vérifié : `/version` **401 sans cookie / 200 avec**,
`/moi` **200**. **Purgée en fin de run** (`DELETE … utilisateur_id=31` → 1 supprimée, **0 active restante**) ;
curlrc + scripts/JSON temporaires supprimés.

---

## Fumée — résultat de chaque point

### 1. Fiche BY0083 — s'ouvre, sans erreur ✓
`GET /parcels/97415000BY0083` → **HTTP 200, 0,17 s**. Payload à **77 clés** de 1ᵉʳ niveau, commune
**Saint-Paul**, surface 2 405 m², zone PLU **U4c**. **Aucune** clé `erreur`/`error`/`detail`.

### 2. Étude sur le témoin d'Étang-Salé — 23 places, L151-35, seuil 500 m ✓
Deux routes de l'écran « Étude de faisabilité » (REMISE-1 / ETUDE-V6) :

- **Régime de stationnement** — `POST /modules/etude/stationnement`
  (`type_projet = etudiante`) → **200, 0,70 s**. Affiche :
  - règle générale du PLU : **UA 2.7.3**, millésime 2025-09-17, « 1 pl. T1–T2 · 1,5 pl. T3–T4 · 2 pl. T5+ » ;
  - **plafond national `reference = "L151-35"`**, catégorie « résidence universitaire (L151-34) »,
    `ratio_plafond = 1,0` ;
  - **seuil 500 m** matérialisé : `condition_tcsp_sous_500m = false`, `distance_tcsp_m = 7 819`
    (TCSP à ~7,8 km → au-delà de 500 m, pas de réduction à 0,5).
- **Étude complète** — `POST /modules/etude` sur l'**assemblage des 4 parcelles témoins**
  (`97404000AW0099 / AW0451 / AW0624 / AW0625`) + **programme saisi** 11 T1 + 5 T2 + 2 T3 + 5 T4
  (= 23 logements), `type_projet = etudiante` → **200**. La variante **`votre_programme` = 23 logements /
  23 places** — exactement le plafond L151-35 (1 place/logt → 23 × 1 = **23 places**). (Le scénario A de
  capacité libre affiche 27/27 ; capacité maximale 32 logements — ce sont les autres cases, pas le
  programme du client.) **Les 3 attentes sont tenues.**

> **Observation non bloquante (à surveiller, hors mandat).** Le **premier** appel de l'étude d'assemblage
> a renvoyé **HTTP 504 à 17,1 s** côté client : c'est un **timeout de la passerelle** (proxy), pas une
> erreur applicative. Le moteur d'implantation sur 4 parcelles prend **~51 s** ; au **rejeu** la requête a
> abouti **200 en 51 s**, à l'identique **via le proxy public ET en direct sur le backend** (`127.0.0.1:8000`).
> Dans `journalctl -u labuse`, les **trois** POST `/modules/etude` sont loggés **200** (l'app termine ;
> c'est le proxy qui lâche avant). Autrement dit : le timeout de la passerelle est **plus court** que la
> durée d'une étude d'assemblage lourde → un 504 transitoire possible au 1ᵉʳ essai à froid. Non corrigé
> (lecture seule).

### 3. Comparatif sur 3 parcelles neuves — chronométré ✓
3 parcelles jamais ouvertes : `97411000IB0138 / IB0139 / IB0140`.

| Étape | Temps | HTTP |
|---|---|---|
| Fiche IB0138 (à froid, **temps de celle-ci**) | **4,39 s** | 200 |
| Fiche IB0139 (à froid) | **1,58 s** | 200 |
| Fiche IB0140 (à froid) | **1,86 s** | 200 |
| `GET /compare` (3 parcelles) — **froid** | **1,02 s** | 200 |
| `GET /compare` (3 parcelles) — **chaud** | **0,71 s** | 200 |

`/compare` renvoie un objet `{count, parcels}` (3 parcelles), **aucune erreur**. Le froid du comparatif
est rapide (1,02 s) parce qu'il **réutilise le cache des 3 fiches** déjà ouvertes individuellement —
comportement voulu depuis DEPLOY-1028b (Lots 3+7).

### 4. Analyser une annonce — une par adresse, une par lien Leboncoin ✓
- **Entrée ADRESSE** → rapport parcelle **complet + estimation**. L'écran résout l'adresse en `idu`
  (omnibox / clic carte) puis rend le **rapport parcelle** : `GET /parcels/{idu}` (fiche complète, 200,
  0,11 s) + **estimation** `GET /radar/annonce/classement/{idu}` → **« C · À étudier »** (200) + le
  comparateur DVF de la fiche (`prix_ancien` : n, q1, q3, médiane, période — présent) + exposition (200).
  Le rapport est **complet**. *Nuance honnête* : `/parcels/search` résout par **référence `idu`**
  (`97415000BY0083` → 1 résultat), pas par **texte de rue** (« Évariste », « 143 Rue » → 0) — c'est une
  recherche de référence, le géocodage d'adresse se fait par la carte ; ce n'est pas une régression de
  l'outil, le rapport servi est correct.
- **Entrée LIEN Leboncoin** → `POST /radar/annonce/analyser` (URL d'annonce) : **API HTTP 200**, corps
  `{"ok": false, "erreur": "url_bloquee"}`. **Message portail propre, aucun code HTTP à l'écran.** Le
  détail technique part **au LOG** (`WARNING … radar/annonce/analyser — portail bloque … HTTP 403`) —
  exactement le design ANNONCE-1-FIX (pt 2). → cas **« message portail/DataDome propre » (accepté)** ;
  motif relevé = `url_bloquee` (le portail a refusé la lecture automatique, HTTP 403).

### 5. `docs_coherence.py` — zéro écart ✓
`scripts.docs_coherence 97415000BY0083` exécuté **en prod contre `https://app.labuse.immo`** (cookie de la
session injecté au runtime, **jamais affiché** ; Bilan rendu en-process) → **0 écart sur 18 données
partagées** (exit 0). Les 8 documents s'accordent (surface 2 458, emprise 900, zone libérée 1 736, pente
9,7°, hauteur 9/6, recul 4, 2 pl/logt, pleine terre 40 %, prix bâti 4 125, terrain 250, VEFA 4 745, SDP max
1 327, SDP résiduelle 453, propriétaire succession, date 27/10/2026) — identique à DEPLOY-1028b.

### 6. 10 minutes de journaux propres — aucune erreur ni 5xx ✓
`journalctl -u labuse`, fenêtre **00:15:04 → 00:27:52** Réunion (**12 min 48 s**, **2 154 lignes**,
couvrant toute la fumée) :

- **0 erreur · 0 exception · 0 traceback · 0 critical · 0 rollback · 0 `TimeoutError`.**
- **0 code 5xx** dans les logs d'accès. Distribution HTTP = **32 × 200 + 1 × 401** (le 401 = mon test
  « sans cookie » **délibéré**).
- `/readyz` : **200** (aucun 503).
- WARNING présents mais **tous bénins/attendus** : 1 × `radar/annonce/analyser — portail bloque … HTTP 403`
  (= le code HTTP du portail Leboncoin part au LOG, l'écran reste propre : design voulu) ; ~42 ×
  `weasyprint` (sélecteurs CSS `::note-*` non supportés, fontTools vs HarfBuzz) émis par la génération du
  **PDF d'étude** de `docs_coherence` — cosmétique, pré-existant.
- Les 12 occurrences de la chaîne « 504 » repérées à la relecture sont **toutes** des **ID de glyphe
  `5042`** (sous-ensemble de police du PDF) : **faux positifs**, pas un seul vrai 504/timeout dans l'app.

---

## Synthèse

**Tous les points de fumée sont VERTS.** La mise en prod de `4c38f525c` (annonce-1 + remise-1) est
confirmée saine et servie : fiche BY0083 OK, Étude Étang-Salé **23 places / L151-35 / seuil 500 m**,
Comparatif rapide et correct, « Analyser une annonce » fonctionnel sur ses **deux entrées** (adresse =
rapport complet + estimation ; lien Leboncoin = message portail propre, détail au log), `docs_coherence`
**0 écart**, journaux **sans erreur ni 5xx**. Run servi `q_v20` intact.

**Une seule observation, non bloquante :** le proxy renvoie un **504 transitoire** sur une **étude
d'assemblage très longue (~51 s)** alors que l'application aboutit bien en **200** — le timeout de la
passerelle est plus court que la durée d'une étude lourde. À arbitrer hors mandat (aligner le timeout
proxy sur la borne applicative de 60 s, cf. `deploy/nginx/labuse.conf` / le commentaire `_ETUDE_TIMEOUT_S`
dans `src/labuse/api/modules.py`). **Aucun geste prod, aucun rollback** — fumée en lecture seule, session
de test purgée.
