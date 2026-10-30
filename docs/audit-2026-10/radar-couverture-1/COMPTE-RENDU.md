# RADAR-COUVERTURE-1 — compte-rendu

**Branche** `feat/radar-couverture-1` · worktree `~/Desktop/labuse-couverture` · ports 9000/6200.
**Périmètre** : extension Chrome `outils/radar-extension/` UNIQUEMENT. Aucun accès prod, aucune lecture
serveur des portails, aucun changement serveur (les compteurs `nb_nouvelles` / `n_pages` existaient déjà).
Merge et rechargement de l'extension = gestes de Vic.

Constat de Vic (passe 336, nuit du 29→30/10) : la passe auto est partie à **02 h 39 Réunion** au lieu de
21 h, n'a lu **qu'une page** (27 nouvelles sur 35, page saturée) contre ~40 en manuel, et **Bien'ici n'y
était pas**. Les trois points ci-dessous traitent exactement ces trois symptômes.

---

## 1. Heure Réunion — la fenêtre du soir se juge en `Indian/Reunion`

**Cause.** `fenetreSoir()` posait le début avec `new Date().setHours(opts.hour||21)` — **en heure locale de
l'OS**. Le Mac de Vic est à l'heure de **Paris** ; `setHours(21)` = 21 h Paris = ~00 h Réunion (hiver,
Paris UTC+1, Réunion UTC+4 fixe, +3 h d'écart). Avec le jitter 0–3 h, la fenêtre « 21 h→minuit » couvrait
en réalité **00 h→03 h Réunion** → la minute-cible tirée est tombée à **02 h 39 Réunion**. Même défaut sur
la garde « une capture par soir » (`localDateStr` = date OS).

**Correctif** (`background.js`). L'epoch (`Date.now`) est absolu, indépendant du fuseau de l'OS ; seule la
conversion en horloge **murale** dépend du fuseau. On dérive donc les composantes murales Réunion via
`Intl.DateTimeFormat(timeZone:"Indian/Reunion")` (qui ignore le fuseau de l'OS), et on reconvertit une
horloge murale Réunion en epoch via le décalage mesuré :
- `reunionParts(now)` → `{year,month,day,hour,minute,second,dateStr}` murales Réunion ;
- `reunionOffsetMs(now)` → décalage (+4 h, mesuré) ; `reunionWallToEpoch(now,h,m)` → epoch d'une heure murale ;
- `fenetreSoir()` ancre `[opts.hour:00 … +jitterMaxMin]` sur l'horloge **Réunion** ;
- `maybeRunTonight()` : `today` = **date Réunion** (garde « un soir » en Réunion) ;
- horodatage du popup (`lastResult`) affiché en **heure Réunion** (`toLocaleTimeString(timeZone:"Indian/Reunion")`),
  suffixé « Réunion ».

**Preuve** — `recette_fenetre.mjs` (horloge du process forcée à `Europe/Paris`) : le début de fenêtre vaut
**21 h Réunion = 18 h Paris** (pas 21 h Paris) ; 23 h Réunion est **dans** la fenêtre ; **02 h 39 Réunion est
hors fenêtre** (ni le soir même, ni la veille) → plus de capture après minuit.

## 2. Pagination jusqu'à épuisement — règle d'arrêt par NOUVEAUTÉ

**Cause du « une seule page ».** `passeNouvelles` s'arrêtait sur un **seuil de date** :
`index_date_max_de_la_page ≤ (dernière_capture − 1 h)`. L'`index_date` de Leboncoin est au **jour** ; dès
qu'une capture récente (p. ex. le test Bien'ici requalifié du 29/10) relevait le seuil à « aujourd'hui »,
la page 1 (datée du jour, à 00 h) passait **sous le seuil** → arrêt immédiat. D'où « 27 nouvelles sur une
seule page » alors qu'il y avait d'autres pages à lire.

**Correctif** (`background.js`). On remplace le seuil de date par une **règle de nouveauté**, pilotée par le
serveur : `/admin/radar/capture` renvoie déjà `nb_nouvelles` par page. On tourne les pages **tant que la
dernière rapporte ≥ 1 annonce nouvelle**, on **s'arrête à la 1ʳᵉ page sans nouveauté**. Inchangé : le délai
« rythme humain » entre pages (4–8 s jittés), et le plafond dur (40 pages en rattrapage, 15 en régime
normal) comme garde. `n_pages` côté serveur = **+1 par page POSTÉE** → il reflète le nombre **réel** de
pages lues. **Même règle pour les deux portails** : `passeNouvellesBienici` applique exactement la même
logique (`biCapturePage` renvoie `nb_nouvelles` ; page vide au-delà du dernier résultat = fin propre, non
postée donc non comptée).

**Preuve** — `recette_pagination.mjs` : LBC `5·3·1·0` → **4 pages** (arrêt sur la page à 0) ; page 1 à 0 →
**1 page** ; nouveauté partout → **plafond 15** ; BI `5·3·0` → **3 pages** ; BI page vide → **2 pages postées**.

## 3. Bien'ici dans la passe automatique — deux défauts cumulés, les deux corrigés

Diagnostic des trois hypothèses du mandat :
- **Passe non déclenchée ?** NON — la passe auto a bien tourné (27 nouvelles Leboncoin capturées, source auto).
- **Capture refusée ?** NON au sens anti-robots, mais **OUI au sens technique** (voir défaut A).
- **Recherche non configurée ?** POSSIBLE (voir défaut B) — non vérifiable sans l'espace de stockage Chrome
  de Vic, donc corrigé par principe.

**Défaut A — BUG d'injection (racine).** `biCapturePage` appelait `biFetchResults(...)` **directement dans
le service worker**. Or `biFetchResults` est une fonction **injectée** : elle lit `location.origin` et fait
un fetch **même-origine** `realEstateAds.json` avec la session de Vic. Dans le worker, `location.origin` =
**l'extension** (`chrome-extension://…`), pas `bienici.com` → la requête n'atteint jamais le portail →
réponse non-200 → `BlockError` → **la capture Bien'ici échoue chaque nuit**. (Incohérence interne : `biFetchAd`,
lui, était correctement injecté via `injectArgs` à la confirmation.) C'est ce qui explique « Bien'ici n'y
était pas » : les 95 annonces Bien'ici en prod venaient d'une capture **de test** requalifiée (DEPLOY-1029b),
pas de la passe auto. **Correctif** : `biCapturePage` passe par `injectArgs(tabId, biFetchResults, […])` —
le fetch tourne dans l'onglet `bienici.com` (même-origine, session chaude), comme le promet le commentaire
et comme `biFetchAd` le fait déjà. Doctrine §2 respectée (aucune lecture serveur).

**Défaut B — recherche non configurée par défaut.** `bieniciSearchUrl` valait `""` par défaut → bloc
Bien'ici **sauté en silence** si Vic ne l'avait pas collée. **Correctif** : défaut **non vide**
`https://www.bienici.com/recherche/achat/la-reunion-974` (ventes, toute La Réunion) dans `getOpts` ET
`options.js`, pour que la passe auto couvre **Leboncoin puis Bien'ici** out-of-the-box. Cette URL ne sert
qu'à ouvrir l'onglet de session ; les filtres réels du fetch restent `BIENICI_FILTERS` (zone `-77601`,
`filterType:buy`). Vider le champ dans les Options désactive Bien'ici (choix laissé à Vic).

L'ordre Leboncoin **puis** Bien'ici était déjà celui de `runEvening`.

---

## Garde-fous (inchangés, respectés)
- Retrait sur **preuve positive** uniquement + **garde-fou 30 %** (RADAR-FIX-3) : non touchés.
- **Aucune lecture serveur des portails** : Bien'ici reste capturé par fetch même-origine injecté dans la
  session de Vic.
- Aucune capture en masse jouée ici : les recettes sont des harnais hors-navigateur (mocks `chrome.*`) ; la
  recette terrain de Vic est limitée à **3 pages**.

## Recette terrain (geste de Vic, limité à 3 pages)
1. Charger l'extension corrigée (Options : laisser les URLs par défaut, renseigner le jeton Radar prod).
2. Popup → « Capturer maintenant » (ou l'alarme de test +2 min) en limitant la recherche à ~3 pages.
3. Vérifier : pages lues = pages apportant du neuf, arrêt sur la 1ʳᵉ page sans nouveauté, **Bien'ici inclus**,
   horodatage du popup en **heure Réunion**.

## Vérifs automatiques (toutes vertes)
`node outils/radar-extension/<fichier>.mjs` :
- **`recette_fenetre.mjs`** (neuf) — fenêtre en heure Réunion sous horloge Paris.
- **`recette_pagination.mjs`** (neuf) — arrêt par nouveauté, même règle LBC/BI, `n_pages` réel.
- `recette_alarme.mjs`, `recette_bascule.mjs`, `recette_bienici.mjs`, `recette_confirmation.mjs` — non
  régressées (Bien'ici explicitement désactivé dans les deux recettes mono-portail LBC).

Hook pre-commit (garde > 2 Mio) vert. Fichiers touchés : `background.js`, `options.js`, `options.html`,
`recette_alarme.mjs`, `recette_bascule.mjs`, + 2 recettes neuves.
