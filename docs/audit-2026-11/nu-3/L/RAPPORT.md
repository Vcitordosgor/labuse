# AUDIT NU-3 — Lot L : extension Chrome (Radar) & chaîne des données

- **Branche** : `audit/nu-3-l` · worktree `~/Desktop/labuse-nu3-l` · ports 9330/6530
- **Mandat** : LECTURE SEULE — aucune modification de l'extension, aucun correctif, aucun merge, aucun accès prod. Deux autres lots (M, N) en parallèle.
- **Base** : requêtes read-only sur la base LOCALE `labuse` (`postgresql://openclaw@localhost:5432/labuse`).
- **Méthode** : code autoritatif (l'application n'a PAS été bootée ; pas d'écran réel Playwright, pas de simulation d'ingestion réelle — tracé par lecture de code + lecture de base). **Limite assumée** : les valeurs « écran » / « PDF » sont dérivées du chemin de rendu (React / gabarit PDF), pas d'un rendu live.
- **Format des constats** : identique à `docs/audit-2026-11/nu-1/` — gravité · reproduction · affiché contre juste · fichier:ligne · proposition.
- **Numérotation** : `L-EXT-*` (extension), `L-CHN-*` (chaîne des données / nouveau millésime), `L-MIL-*` (millésimes affichés, 10 parcelles), `L-JOB-*` (jobs planifiés).

---

## Récapitulatif des gravités

| # | Titre court | Gravité |
|---|---|---|
| L-EXT-01 | Capture Leboncoin poste le DOM complet d'une session connectée (données perso du Mac non expurgées, archivées sur disque) | **majeur** |
| L-EXT-02 | Changement de schéma JSON Bien'ici = « fin d'inventaire » silencieuse, run affiché « OK » | **majeur** |
| L-EXT-03 | Aucune défense contre une horloge Mac fausse (fenêtre du soir + `captured_at` faussés) | **majeur** |
| L-EXT-04 | Un incident Bien'ici fait passer toute la soirée en « Échec » alors que Leboncoin a réussi | mineur |
| L-EXT-05 | La fenêtre du soir ne peut pas franchir minuit Réunion (configs hors défaut) + angle mort 5 min | mineur/dette |
| L-EXT-06 | Jeton admin prod stocké et affiché en clair | mineur |
| L-EXT-07 | Changement de sélecteur « page suivante » Leboncoin = arrêt silencieux page 1 | mineur |
| L-EXT-08 | `outerHTML` posté sans borne de taille (jusqu'à 40 pages/soir) | dette |
| L-EXT-09 | `communeUrls` (24 communes) : code mort jamais appelé, encodage jamais validé | dette |
| L-CHN-01 | Le client ne voit JAMAIS le nouveau millésime en fiche : `source_millesime` est une chaîne figée | **majeur** |
| L-CHN-02 | Le PDF client (§12 Sources) n'affiche AUCUNE date de source pour les 10 sources | **majeur** |
| L-CHN-03 | Aucun run marqué « périmé » quand une source amont avance (couches gelées assumées) | majeur |
| L-CHN-04 | Clé de fraîcheur des caches aveugle à `source_horizon_at` (sous-invalidation possible) | majeur |
| L-CHN-05 | `source_checks` vide : la date « amont vérifié » n'est jamais prouvée au client | mineur |
| L-CHN-06 | Désync libellé PPR run↔base = faux positif « plus récente » en admin Flux | mineur |
| L-CHN-07 | Sitadel : horizon servi n'avance qu'au prochain `persist_millesime` | dette |
| L-MIL-01 | Date d'approbation PPR affichée = la plus récente d'AILLEURS, jamais celle de la commune | **majeur** |
| L-MIL-02 | Notes techniques internes du millésime fuient à l'écran (cascade brute vs « Les données » nettoyée) | **majeur** |
| L-MIL-03 | `source_horizon_at` Sitadel périmé de 2 mois vs dernier permis ingéré | mineur |
| L-MIL-04 | Date d'édition LiDAR « 13/03/2025 » = littéral en dur absent de la base | mineur |
| L-MIL-05 | Cadastre & RNIC : date d'ingestion/sync LABUSE tient lieu de millésime producteur | mineur/dette |
| L-JOB-01 | Un job jamais réussi est invisible de la vigie « en retard » | majeur |
| L-JOB-02 | La moitié des jobs est hors du monitoring public `/healthz/crons` | majeur |
| L-JOB-03 | `/admin/cron` ignore le gel et affiche une « prochaine exécution » mensongère | mineur |
| L-JOB-04 | Conversion de fuseau `_h_reunion` à modulo 24 : day-wrap latent | dette |
| L-JOB-05 | `docs/EXPLOITATION-CRON.md` périmé (décrit le legacy retiré, horaires faux) | dette |
| L-JOB-06 | `poser_crontab_solidite.sh` injecte un job retiré du registre (`recap-matin`) | mineur |
| L-JOB-07 | Commentaire `planifie=False` cite `agents-sources` qui est en réalité planifié | mineur |

**Total** : 0 bloquant · 9 majeurs · 10 mineurs · 6 dettes.

Fil rouge, cohérent avec les autres lots NU : **l'arithmétique est juste ; le danger est à la périphérie du millésime et de l'assemblage** — un libellé qui ne bouge pas quand l'amont bouge, une date globale servie comme locale, un échec silencieux indistinguable d'un succès.

---

# 1. L'extension Radar

Code lu en intégralité : `background.js` (843 l.), `popup.js`, `options.js`, `content.js` (référence non injectée), `manifest.json`, `popup.html`, `options.html`, les 6 recettes `recette_*.mjs`. Vérifications croisées côté serveur : `src/labuse/pige/api.py:174-220` (endpoint `/admin/radar/capture`) et `src/labuse/pige/html_ingest.py:45-52,459-528` (ingestion + archivage disque).

## 1.1 Réponses directes au mandat

### a) Si Leboncoin / Bien'ici change une classe, renvoie un captcha, une page vide, un JSON tronqué

**Leboncoin** (lecture de page riche, `inspectPage`/`readPage`) :
- **Captcha / vérification** : détecté par mots-clés dans le texte visible + titre + URL (`datadome`, `captcha`, `verification`, `challenge`, `access denied`) → `BlockError` → arrêt net, badge ✗, notification « Radar bloqué, dépose à la main » (`background.js:273-276, 375, 727-728`). **Sain.**
- **Changement de classe / structure** : `readPage` exige soit `__NEXT_DATA__.props.pageProps.searchData`, soit des cartes DOM (`[data-test-id=aditem_container]`…) ; sinon `BlockError "Ni searchData ni cartes d'annonces"` (`background.js:377-383`). Un changement de structure est donc traité comme un blocage → arrêt propre, **aucune fausse donnée**. **Sain** (voir toutefois L-EXT-07 pour la pagination).
- **Page vide / 0 annonce** : `searchData` présent mais 0 annonce → non bloqué → POST, le serveur renvoie `nb_nouvelles=0` → la passe s'arrête (`background.js:410`). **Sain.**
- **JSON `__NEXT_DATA__` tronqué** : `JSON.parse` sous try/catch → `nextData=null` → si pas de cartes DOM non plus → `BlockError`. **Sain.**

**Bien'ici** (appel API JSON `realEstateAds.json`, `biCapturePage`) :
- **429 (trop vite)** : `BlockError "Bien'ici 429"` → arrêt (`background.js:569`). **Sain.**
- **Captcha / page HTML au lieu de JSON** : `JSON.parse` échoue → `BlockError "JSON illisible"` (`:572`). **Sain.**
- **Réponse vide / statut ≠ 200** : `BlockError "réponse vide (HTTP …)"` (`:570`). **Sain.**
- **JSON tronqué** : `JSON.parse` échoue → `BlockError`. **Sain.**
- **⚠ Changement de clé/schéma avec HTTP 200 et JSON valide** : `ads = JSON.parse(body).realEstateAds || []` (`:572`). Un renommage de clé (ou `realEstateAds:null`) → `ads=[]` → `{empty:true}` → la passe s'arrête **sans erreur, sans notification**, et le run affiche « OK ». **Défaut — voir L-EXT-02.**

### b) Consommation CPU / mémoire sur une passe

- **Boucles bornées** : `passeNouvelles` ≤ 40 pages (`CAP_TOTAL_PAGES`/`CAP_NOUVELLES`), `passeRelecture` ≤ 20, confirmation ≤ 60 (`background.js:9-12, 403, 425, 489`). Aucune boucle non bornée.
- **Un seul onglet de travail à la fois** : bloc Leboncoin ouvre 1 onglet en arrière-plan, réutilisé pour la confirmation, puis fermé (`:691-704`) ; Bien'ici ouvre son propre onglet, fermé en `finally` (`:647-654`).
- **Mémoire** : pour Leboncoin, chaque page lit `document.documentElement.outerHTML` (le DOM complet d'une SPA rendue — potentiellement plusieurs Mo) et le POSTe (`:265, 407`). Transitoire par page, GC entre pages. **Pas de borne de taille** (L-EXT-08). Bien'ici est léger (JSON).
- **CPU** : le coût réel est **Chrome qui rend 40 pages Leboncoin lourdes** dans un onglet d'arrière-plan + `innerText` (force un layout à chaque page). Le service worker lui-même est négligeable (polling `waitTabComplete` toutes les 500 ms, battement d'alarme toutes les 5 min).
- **Durée** : délais « rythme humain » 4–8 s entre pages, 8–15 s entre confirmations (`:15-18`). Une soirée pleine (≈ nouvelles + 20 relecture + 60 confirmations) ≈ **20–40 min** avec un onglet SPA lourd ouvert. Raisonnable, mais long.

### c) Ce qu'elle envoie au serveur (données perso du Mac ?)

Envois (tous avec en-tête `X-Radar-Token`) :
- `/admin/radar/capture` : `{passe, url, page, html, captured_at, source}` (`background.js:336-345`).
- `/admin/radar/etat` : GET, rien.
- `/admin/radar/confirmation-batch` : `{items:[{list_id, verdict, preuve, url, http_status}]}` (`:358-366`).

**Pas d'exfiltration de cookies** : aucun accès à `document.cookie`/`localStorage` (grep vide). Le `fetch` Bien'ici est même-origine (porte la session implicitement), mais le serveur ne reçoit que le JSON.

**⚠ Mais** le champ `html` de la capture Leboncoin = `document.documentElement.outerHTML` d'une page rendue **dans la session connectée de Vic** (doctrine §2 : « vraie session »). Le DOM d'un Leboncoin connecté et son `__NEXT_DATA__` embarquent fréquemment le contexte du compte (nom, menu compte, identifiant utilisateur, compteurs de messagerie, parfois jetons). Tout est posté **et archivé verbatim sur le disque serveur** (`html_ingest.py:49-51` écrit `{hash}.html`). La promesse « aucune donnée personnelle de l'utilisateur du Mac » **n'est pas appliquée** — voir **L-EXT-01**.

### d) Comportement à minuit Réunion + horloge Mac fausse

- **Fuseau** : la fenêtre du soir et l'horodatage sont ancrés sur l'horloge **murale Réunion** (`Indian/Reunion`, UTC+4 fixe) via `Intl`, indépendamment du fuseau de l'OS (`background.js:122-155`). Correct et testé (`recette_fenetre.mjs` : machine à Paris → fenêtre bien à 21 h Réunion = 18 h Paris). **Sain** pour le cas « horloge juste, fuseau Paris ».
- **Minuit** : défaut `hour=21`, `jitterMaxMin=180` → fenêtre `[21:00 .. 24:00]` Réunion, bornée pile à minuit. Le « soir » se compte par **date Réunion** ; garde `autoRunDate` = une seule capture par jour Réunion (`:771-791`). Un réveil après minuit → `now > fin` → abstention (pas de capture à 02 h — c'était la cible du correctif RADAR-COUVERTURE-1). **Sain** au défaut (voir L-EXT-05 pour les angles morts).
- **⚠ Horloge Mac FAUSSE** : toute la logique dérive de `new Date()` (l'epoch de l'OS), corrigé **seulement pour le fuseau**. Le commentaire « QUELLE QUE SOIT l'horloge de la machine » (`:115-121`) n'est vrai que pour le **décalage de fuseau**, pas pour une horloge **absolument fausse**. Une horloge décalée de N heures / de date décale toute la fenêtre « soir » et horodate chaque capture avec un `captured_at` faux. **Aucune détection** — voir **L-EXT-03**.

## 1.2 Constats

### L-EXT-01 — majeur — La capture Leboncoin poste (et le serveur archive) le DOM complet d'une page de session connectée, sans expurger les données personnelles du Mac
- **Reproduction** : passe « nouvelles » ou « relecture » Leboncoin → `inspectPage` capture `document.documentElement.outerHTML` (`background.js:265`) → `apiCapture` POSTe ce `html` (`:341`) → serveur `html_ingest.ingester` → `_archiver` écrit `{hash}.html` sur disque (`html_ingest.py:49-51`, appelé `:475`).
- **Affiché c. juste** : doctrine (en-tête `background.js:20-25`) = « POSTE le JSON tel quel… comme le HTML Leboncoin », laissant entendre qu'on envoie de la donnée d'annonces. Réalité = le **DOM entier d'une page authentifiée** (en-tête compte, `__NEXT_DATA__` d'hydratation incluant potentiellement l'utilisateur/jetons) est transmis **et persisté verbatim** côté serveur.
- **fichier:ligne** : `outils/radar-extension/background.js:265, 336-345` ; `src/labuse/pige/html_ingest.py:45-52, 475`.
- **Proposition** : n'extraire et n'envoyer que `__NEXT_DATA__.props.pageProps.searchData` (ou les cartes d'annonces) côté extension avant POST ; ne jamais transmettre `outerHTML`. Réduit d'un coup la surface vie privée ET la taille du payload (cf. L-EXT-08).

### L-EXT-02 — majeur — Un changement de schéma JSON Bien'ici (HTTP 200) est silencieusement traité comme « fin d'inventaire » ; le run s'affiche « OK » en n'ayant rien capturé
- **Reproduction** : Bien'ici renvoie 200 avec un JSON valide dont la clé `realEstateAds` est renommée/absente/`null` → `ads = JSON.parse(body).realEstateAds || []` → `ads=[]` → `biCapturePage` renvoie `{nouvelles:0, empty:true}` → `passeNouvellesBienici` incrémente `used` puis `break` sans lever → `runEvening` écrit `lastResult: "OK … BI nouv 1 …"`.
- **Affiché c. juste** : popup/État = « OK … BI nouv 1 », journal serveur = passe posée ; réalité = **0 annonce Bien'ici capturée**. Leboncoin traite la même situation (ni searchData ni cartes) comme un **blocage** (`background.js:381`) ; Bien'ici non.
- **fichier:ligne** : `outils/radar-extension/background.js:571-573, 583-592` (vs la garde LBC `:377-383`).
- **Proposition** : avant de traiter `empty` comme fin d'inventaire, vérifier la **forme attendue** du JSON (présence du tableau `realEstateAds` et, en page 1, d'un compteur total non nul) ; sinon lever `BlockError` comme pour un captcha.

### L-EXT-03 — majeur — Aucune défense contre une horloge système fausse : la fenêtre du soir et `captured_at` en dépendent entièrement
- **Reproduction** : régler l'horloge du Mac à +N heures (ou mauvaise date). `reunionParts`/`reunionWallToEpoch` dérivent de `new Date()` ; `Intl` ne corrige que le fuseau, pas un epoch faux (`background.js:122-155`). Conséquences : la capture « du soir » part au mauvais moment réel (ex. midi Réunion), et chaque capture porte un `captured_at = nowIso()` faux (`:341, 675`).
- **Affiché c. juste** : le commentaire `:115-121` affirme la robustesse « quelle que soit l'horloge de la machine » — vrai seulement pour le fuseau. Côté serveur, un `captured_at` faux fausse les fenêtres temporelles : `radar_capture` compte les prix modifiés via `ts >= captured_at` (`src/labuse/pige/api.py:193-194`) et dédup/journalise sur `captured_at` (`:199, 216`) → futur = 0 prix modifié, passé = sur-comptage ; `anciennete_j` / « depuis hier » (F-014/F-015 NU-1) en pâtissent aussi.
- **fichier:ligne** : `outils/radar-extension/background.js:122-155, 675, 341` ; `src/labuse/pige/api.py:193-194, 199, 216`. Recette `recette_fenetre.mjs` ne teste que le fuseau (machine Paris), jamais une horloge décalée.
- **Proposition** : à chaque run, comparer `Date.now()` à une source de temps de confiance — l'en-tête `Date` de la réponse `apiEtat` (déjà appelée `:682`) — et si l'écart dépasse quelques minutes, refuser la capture + notifier « horloge du Mac à vérifier ». À défaut, laisser le serveur horodater avec sa propre horloge et ignorer `captured_at` client.

### L-EXT-04 — mineur — Un incident Bien'ici fait passer TOUTE la soirée en « Échec » alors que Leboncoin a déjà réussi et posté
- **Reproduction** : le bloc Leboncoin se termine et POSTe (`background.js:690-705`), puis le bloc Bien'ici lève un `BlockError` (429, vide, JSON illisible — `:569-572`). Le throw remonte au `catch` de `runEvening` (`:721`) qui écrit `lastResult: "Échec (…) — …"` (`:726`), **écrasant** les `parts` LBC déjà accumulés.
- **Affiché c. juste** : popup = « Échec » global ; réalité = LBC nouvelles/relecture/confirmation réussies et enregistrées serveur.
- **fichier:ligne** : `outils/radar-extension/background.js:688-731`.
- **Proposition** : encapsuler chaque bloc portail dans son propre try/catch, consigner un statut par portail, et rapporter le succès partiel (« LBC OK · BI échec »).

### L-EXT-05 — mineur/dette — La fenêtre du soir ne peut pas franchir minuit Réunion (configs hors défaut) + angle mort de 5 min au ras de minuit
- **Reproduction** : Options autorisent `hour` 0–23 et `jitterMaxMin` 0–600 (`options.js:25-26`). Avec une fenêtre qui franchit minuit (ex. `hour=23`, `jitter≥60`), `fenetreSoir` ancre `debut = reunionWallToEpoch(now, hour, 0)` sur la date Réunion **courante** (`:764-768`) ; après 00:00 la date roule à J+1, `debut` est recalculé à 23:00 **J+1** (futur) → `maybeRunTonight` renvoie « pas encore l'heure » (`:786`) → la portion post-minuit n'est **jamais** rattrapée. Angle mort annexe : si la minute-cible tirée tombe dans les ~5 dernières min avant minuit et qu'aucun battement n'y atterrit, la capture du jour est silencieusement sautée (au changement de date la cible est redessinée pour J+1, `:779-782`).
- **Affiché c. juste** : les Options acceptent des combinaisons heure/jitter qui ne se déclenchent jamais après minuit, sans avertissement. Au défaut (21:00+180=24:00 pile) c'est sain.
- **fichier:ligne** : `outils/radar-extension/background.js:764-768, 779-787` ; bornes `options.js:25-26`.
- **Proposition** : borner explicitement la fenêtre à `[debut, min(fin, minuit)]` et le documenter, ou calculer `debut` relativement à la soirée même après le passage de minuit.

### L-EXT-06 — mineur — Le jeton admin prod est stocké et affiché en clair
- **Reproduction** : le champ `token` des Options est `type="text"` (`options.html`, label « Jeton (X-Radar-Token) ») ; il est persisté en clair dans `chrome.storage.local` (`options.js:28`, relu `background.js:65-93`).
- **Affiché c. juste** : le README présente le jeton comme « jeton de prod » ; il ouvre `/admin/radar/capture|etat|confirmation`. Toute autre extension ayant la permission `storage`, un accès au profil, ou un regard par-dessus l'épaule le lit.
- **fichier:ligne** : `outils/radar-extension/options.html` (input token) ; `options.js:21, 28` ; usage header `background.js:339, 350, 361`.
- **Proposition** : `type="password"`, documenter la portée du jeton, et confirmer qu'il est bien un jeton Radar dédié (révocable) et non le jeton admin global.

### L-EXT-07 — mineur — Un changement de sélecteur « page suivante » Leboncoin arrête silencieusement la passe à la page 1
- **Reproduction** : `inspectPage` détecte la pagination via des sélecteurs fixes (`a[title="Page suivante"], [aria-label*="suivante"], a[rel=next], link[rel=next]`, `:303-306`). Si Leboncoin change ces sélecteurs, `hasNext=false` → `passeNouvelles` fait `break` dès la page 1 (`:411`) alors que la page a livré des annonces nouvelles. Le run affiche « OK · nouv 1 ».
- **Affiché c. juste** : « OK, nouv 1 » alors que l'inventaire réel comptait de nombreuses pages ; perte de couverture non signalée (distincte du blocage, qui lui est bien détecté).
- **fichier:ligne** : `outils/radar-extension/background.js:303-306, 314-322, 411, 436`.
- **Proposition** : si une page 1 pleine (searchData avec N annonces) ne débouche sur aucune page suivante, émettre un avertissement doux (« pagination non trouvée — sélecteur à revoir ») plutôt qu'un arrêt silencieux.

### L-EXT-08 — dette — `outerHTML` posté sans borne de taille, jusqu'à 40 pages par soirée
- **Reproduction** : chaque page Leboncoin POSTe le `outerHTML` intégral (`:407`), sans plafond d'octets, jusqu'à 40 fois (`CAP_TOTAL_PAGES`).
- **Affiché c. juste** : non visible ; pic mémoire transitoire côté worker + téléversements volumineux + archivage disque serveur non borné.
- **fichier:ligne** : `outils/radar-extension/background.js:407, 265`.
- **Proposition** : résolu par L-EXT-01 (n'envoyer que `__NEXT_DATA__`) ; sinon plafonner la taille et tronquer proprement avec signalement.

### L-EXT-09 — dette — `communeUrls` (générateur 24 communes) est du code mort, jamais appelé, à l'encodage non validé
- **Reproduction** : `communeUrls` (`:193-222`) et la constante `COMMUNES` (`:39-46`) ne sont référencées que par la fonction elle-même (grep : 0 appelant dans le flux de soirée, qui utilise `opts.searchUrl` directement). Le commentaire admet que l'encodage du paramètre `locations` Leboncoin est « PAS connu … À VALIDER en Lot 0.2 » (`:186-192`).
- **Affiché c. juste** : code présent suggérant une couverture commune-par-commune qui n'existe pas (la passe est île-entière).
- **fichier:ligne** : `outils/radar-extension/background.js:39-46, 193-222`.
- **Proposition** : supprimer (ou câbler après validation de l'encodage réel).

## 1.3 Points vérifiés sains (extension)
- Blocage → arrêt net + notification + pas de martèlement ; 429 géré ; `waitTabComplete` borné à 25 s.
- Retrait d'annonce **uniquement sur preuve positive** (phrase d'expiration / 404 / off-market) — bloqué/vide/redirigé = « inconnue » = 0 retrait (`classifierConfirmation` `:465-482`, `classifierConfirmationBienici` `:612-618`). Robuste contre les faux retraits (régression 60/60 du 28/10 corrigée).
- Confirmation : la navigation du navigateur est **restreinte aux hôtes leboncoin/bienici** (routage `confLbc`/`confBi` par `isLeboncoin`/`isBienici`, `:686-687`) → un serveur/jeton compromis ne peut pas rediriger le navigateur vers un hôte arbitraire.
- Garde anti double-déclenchement (`running`), une capture par jour Réunion (`autoRunDate` posée AVANT le run), battement périodique robuste au déchargement MV3.
- Manifest MV3 minimal (pas de content-script persistant ; permissions : alarms/storage/notifications/scripting/tabs ; hôtes larges `*://*/*` en **optional**).

---

# 2. La chaîne des données — arrivée d'un nouveau millésime

Pour chaque source : la sentinelle le voit-elle ? la page Données le dit-elle ? les caches sont-ils invalidés ? le run est-il marqué périmé ? un client voit-il la bonne date en fiche et PDF ? (chemin tracé par lecture de code ; l'app n'est pas bootée — limite assumée.)

## 2.1 Architecture vérifiée
1. **Sentinelle** (`src/labuse/sentinelle.py`) : veille généralisée, 4 méthodes (`api`/`page`/`entete`/`temoin`). Écrit `source_veille.dernier_vu/dernier_statut`, **jamais `data_sources`** (doctrine `sentinelle.py:4-6` : « Vic décide »). Les 10 sources ciblées ont toutes une sonde active (vérifié en base).
2. **Écriture du millésime servi** : `data_sources.source_millesime` n'est écrit que par les ingesteurs (`persist_millesime`, `ingestion/fraicheur.py:335`) et le semis statique `ingestion/seed_sources.py`. La sentinelle n'y touche pas.
3. **Affichage client** : `millesime_source.composer` (point unique) — fiche §Sources et pieds PDF (`registre/valeur.py:159`). `composer` **ignore** `dernier_vu` et `last_sync_at` (`millesime_source.py:84-101`).
4. **Caches** : `fraicheur_caches.empreinte_attendue = run|cascade|residuel|millesimes_hash|code` ; `millesimes_hash` (`fraicheur_caches.py:73-83`) hache **uniquement `source_millesime`**, pas `source_horizon_at`.
5. **Run** : tables de run intouchables par la fraîcheur (`ingestion/fraicheur.py:6-9`) ; désync badge/rang ↔ source fraîche **assumée et documentée**.

## 2.2 Tableau par source

| source | sentinelle ? | page Données = date réelle ? | cache busté au nouveau millésime ? | run marqué périmé ? | client voit la bonne date (fiche + PDF) ? |
|---|---|---|---|---|---|
| **DVF** | OUI `page` (`sentinelle.py:492`) | OUI (date live `max(date_mutation)` via `etat_sources`, `fraicheur.py:234`) | Partiel (médianes bustées sur `max(date_mutation)` mais `millesimes_hash` NON) | NON (run gelé) | Fiche : millésime figé « 2021–2025 » ; **PDF §12 : absente** |
| **Cadastre PCI** | OUI `api` (`sentinelle.py:408`) | NON (hors dict SOURCES ; string « latest ») | NON | NON | Fiche : string figée ; **PDF §12 : absente** |
| **PLU/GPU** | OUI `temoin` + garde idurba (`bascule_gardes.py:508`) | NON (horizon NULL ; `derniere_donnee` = ingestion) | NON | NON (auto=False) | Fiche : champ séparé `plu_fraicheur` (YAML manuel `app.py:6108`) ; **PDF §12 : absente** |
| **PPR (DEAL)** | OUI `temoin` GASPAR (`sentinelle.py:588`) | NON | NON | NON | Fiche : « approuvés 2011–2026 » figé + désync run↔base ; **PDF §12 : absente** |
| **BD TOPO** | OUI `api` (`sentinelle.py:410`) | NON | NON | NON | Fiche : « édition courante » sans date (`composer:98`) ; **PDF §12 : absente** |
| **LiDAR HD** | OUI `temoin` WFS (`sentinelle.py:427`) | NON | NON | NON | Fiche : « Survol 2023 · MNx 13/03/2025 » figé ; **PDF §12 : absente** |
| **Sitadel** | OUI `api` Dido (`sentinelle.py:569`) | OUI (date live `max(date)`, statut dérivé) | NON | NON | Fiche : « 2026-08 » n'avance qu'au persist ; **PDF §12 : absente** |
| **SIRENE** | OUI `api` (`sentinelle.py:515`) | NON | NON | NON | Fiche : « état courant (non versionné) » figé ; **PDF §12 : absente** |
| **RNIC** | OUI `api` (`sentinelle.py:391`) | NON | NON | NON | Fiche : « extraction annuelle » sans date ; **PDF §12 : absente** |
| **OLL** | OUI `api` ODS metas.modified | NON | NON | NON | Fiche : « OLL 2024 » figé ; **PDF §12 : absente** |

**Constante** : détection amont (sentinelle) **solide, 10/10**. Point faible **en aval** : de la détection vers la date affichée.

## 2.3 Constats

### L-CHN-01 — majeur — Le client ne voit JAMAIS le nouveau millésime en fiche : `source_millesime` est une chaîne descriptive figée, et `dernier_vu` (sentinelle) n'atteint pas le client
- **Reproduction** : la sentinelle détecte un nouveau millésime (des sources sont actuellement en `dernier_statut='nouvelle_version'` en base : BDNB, Géorisques MVT, Annuaire) → `data_sources.source_millesime` inchangé → `composer` affiche l'ancienne chaîne.
- **Affiché c. juste** : fiche montre « OLL 2024 » / « 2011–2026 » / « extraction annuelle » alors que l'amont a avancé.
- **fichier:ligne** : `src/labuse/millesime_source.py:84-101` (`composer` reçoit `dernier_vu`/`last_sync_at` mais ne les lit jamais ; « la sentinelle reste un signal INTERNE »).
- **Proposition** : quand `source_millesime` est non daté ET `dernier_vu` porte une date amont plus récente, surfacer « édition courante, amont vu le JJ/MM », ou offrir un geste semi-auto recopiant `dernier_vu` validé par Vic vers `source_millesime`.

### L-CHN-02 — majeur — Le PDF client (§12 « Sources, limites et mentions ») n'affiche AUCUNE date/millésime de source, pour les 10 sources
- **Reproduction** : générer le Dossier/PDF → bloc Sources = nom + fournisseur seuls.
- **Affiché c. juste** : le client exporte un document sans savoir de quand datent cadastre/DVF/PLU/PPR. Asymétrie avec la fiche (qui montre une chaîne) et avec les pieds de section PDF (`registre/valeur.py:_millesimes` compose bien un millésime).
- **fichier:ligne** : `src/labuse/exports/blocs/sources.py:51-53` (« le NOM … jamais le millésime »).
- **Proposition** : décision produit — afficher le millésime composé dans §12 (comme les pieds de section), ou documenter explicitement l'omission. En l'état, asymétrie fiche↔PDF non tracée.

### L-CHN-03 — majeur — Aucun run servi n'est marqué « périmé » quand une source amont avance ; pour les couches cascade gelées (PLU, PPR) c'est « détection seule »
- **Reproduction** : nouveau PLU approuvé → `check_couches_cascade` (`fraicheur.py:453`) et `check_coherence_idurba` (`bascule_gardes.py:508`) **signalent sans bloquer** (`bascule_gardes.py:161`). `check_fraicheur` (`:158`) lit `source_horizon_at` ; PLU/PPR = NULL → « horizon inconnu », jamais un retard.
- **Affiché c. juste** : le run q_v20 continue d'être servi avec l'ancien zonage/aléa, sans drapeau « périmé » côté run.
- **fichier:ligne** : `src/labuse/ingestion/fraicheur.py:6-9, 158-160, 453-473` ; `src/labuse/bascule_gardes.py:158-216, 508`.
- **Proposition** : acceptable par doctrine (désync assumée), MAIS la fraîcheur par commune doit rester visible au client et la fiche doit signaler « zonage servi = idurba X (date), révision détectée » quand `check_coherence_idurba` voit un GPU plus récent.

### L-CHN-04 — majeur — La clé de fraîcheur des caches (`millesimes_hash`) ne hache que `source_millesime` (figé), pas `source_horizon_at` : sous-invalidation possible
- **Reproduction** : nouvelle livraison DVF → `refresh_dvf`→`persist_millesime` réécrit `source_millesime` avec la **même** chaîne « 2021–2025 » (`fraicheur.py:360`, `s.get("millesime")` constant), `source_horizon_at` avance. `empreinte_attendue` inchangée → `commune_contexte_cache`/tuiles non invalidés.
- **Affiché c. juste** : atténué (lecteurs servis lisent la médiane live ; `caches_marche_perimes` détecte via `max(date_mutation)`) mais la clé générique est aveugle à l'horizon.
- **fichier:ligne** : `src/labuse/fraicheur_caches.py:73-91` ; `src/labuse/ingestion/fraicheur.py:360`.
- **Proposition** : ajouter `source_horizon_at` (ou max des horizons) à `millesimes_hash` — « sur-invalider est bénin, sous-invalider est le bug » (leur propre doctrine, `fraicheur_caches.py:76`).

### L-CHN-05 — mineur — `source_checks` est vide : la date « amont vérifié à la dernière version » n'est jamais prouvée au client
- **Reproduction** : la page Données lit `source_checks.verified_at` (`app.py:1310`) → dict vide (0 ligne en base) → mention jamais affichée.
- **Affiché c. juste** : honnête (le front n'invente pas), mais la promesse « suivie à la dernière version » n'a aucune preuve datée côté client.
- **fichier:ligne** : `src/labuse/api/app.py:1310`.
- **Proposition** : brancher l'écriture de `source_checks` à chaque passe sentinelle `ok`, ou documenter l'omission.

### L-CHN-06 — mineur — Désync libellé PPR run↔base = faux positif « plus récente » en admin Flux
- **Reproduction** : `p_score_v2_runs(q_v20).params.source_millesimes` contient « PPR… (DEAL **Lizmap**) » ; `data_sources` contient « …approuvé le 2026-04-16 (état DEAL) ». `flux.py:177` → `plus_recente=True` → l'admin Flux marque PPR « plus récente que le run » pour un simple **renommage** de libellé.
- **Affiché c. juste** : faux positif admin.
- **fichier:ligne** : `src/labuse/flux.py:150-237` (comparaison sur chaîne libre).
- **Proposition** : comparer sur une clé stable (horizon/idurba) plutôt que la chaîne libre.

### L-CHN-07 — dette — Sitadel : la date servie (`source_millesime`=« 2026-08 », `source_horizon_at`=2026-06-30) n'avance qu'au prochain `persist_millesime`, pas à la détection sentinelle
- `last_sync_at`=2026-10-11 mais horizon reste juin. Non bloquant (cadence bornable, statut live dérivé). À surveiller : l'écart horizon↔ingestion (voir aussi L-MIL-03).
- **fichier:ligne** : `src/labuse/ingestion/fraicheur.py:335-367`.

---

# 3. Les millésimes affichés — 10 parcelles réelles (écran vs PDF vs base)

**Limite** : l'app n'est pas bootée ; « écran » et « PDF » sont tracés jusqu'au composant React / au gabarit PDF, pas rendus live. Vérité base = `psql` lecture seule sur `labuse` local.

## 3.1 Les 3 chemins qui citent une date de source
1. **Liste « Les données » de la fiche** — `_data_sources_fiche` (`src/labuse/api/app.py:3590-3687`) lit `data_sources.source_millesime/source_horizon_at/last_sync_at`, compose via `millesime_source.composer` (`millesime_source.py:84`, qui **nettoie** les notes internes), pose `millesime` (`app.py:3653, 4942`).
2. **Ligne de cascade par contrainte** — `app.py:4694` pose `"millesime_amont": r["source_millesime"]` **BRUT** (jamais passé par `composer`/`nettoyer_notes_internes`), rendu inline `frontend/src/components/fiche/primitives.tsx:284-285`.
3. **PDF** — bloc « Sources » = nom + fournisseur seuls, jamais le millésime (`exports/blocs/sources.py:53`). Les dates du PDF sont **par donnée** : aléas (`miroir.py:456`), SUP (`miroir.py:391`), permis (`miroir.py:325-336`), PLU (`etude_faisabilite.py:915`), via `libelle_date_source` (`servitudes.py:292`, `app.py:5261`).

Point clé : la date de source du **catalogue** (`data_sources`) est un texte libre, **global (jamais scopé commune/parcelle)**, non recalculé depuis les tables sous-jacentes.

## 3.2 Les 10 parcelles (base locale)

| IDU | Commune | Ingestion cadastre (`parcels.created_at`) |
|---|---|---|
| 97424000AC0462 | Cilaos | 2026-06-29 |
| 97403000AP0786 | Entre-Deux | 2026-06-29 |
| 97407000AO0623 | Le Port | 2026-06-29 |
| 97422000BW1407 | Le Tampon | 2026-06-28 |
| 97411000AR0040 | Saint-Denis | 2026-06-29 |
| 97411000HV0135 | Saint-Denis (Ste-Clotilde) | 2026-06-29 |
| 97412000CY0369 | Saint-Joseph | 2026-06-29 |
| 97413000DF0259 | Saint-Leu | 2026-06-28 |
| 97415000HO0003 | Saint-Paul | 2026-06-28 |
| 97416000ES0741 | Saint-Pierre | 2026-06-28 |

## 3.3 Matrice source × (écran / PDF / vérité base)

La date de source du catalogue est **identique pour les 10 parcelles** (ligne `data_sources` unique). Une ligne par source suffit ; la colonne vérité indique où ça diverge.

| Source | Écran (fiche « Les données ») + fichier:ligne | PDF + fichier:ligne | Vérité base (table.colonne) | Match ? |
|---|---|---|---|---|
| **DVF** | « 2021–2025 + archives 2014–2020 », horizon 2025-12-31 — `app.py:3653` | **nom seul, pas de date** `blocs/sources.py:53` ; vente par parcelle `miroir.py:285` | `dvf_mutations.date_mutation` 2021-01-01→**2025-12-31** ; histo 2014→2020 | **OUI** (horizon=max réel) ; divergence écran↔PDF |
| **Cadastre PCI** | « latest ingérée », last_sync 2026-10-11 — `app.py:3680` | nom seul | `parcels.created_at` = **2026-06-28/29** | **PARTIEL** — last_sync ≠ ingestion réelle |
| **PPR / aléas** | « PPR le plus récent approuvé le **2026-04-16** » — ligne unique, **non scopée commune** ; aussi cascade brute `primitives.tsx:284` | nom seul ; aléas datés **par parcelle** `miroir.py:456` | `spatial_layers kind='ppr_etat'` : **seule SAINT-ANDRÉ**=2026-04-16 ; Le Tampon=2017-10-20, Saint-Joseph=2017-03-16, Saint-Leu=2015-11-23… | **TROMPEUR** — date d'ailleurs sur toutes les fiches |
| **BD TOPO** | « édition courante » `millesime_source.py:98`, last_sync 2026-09-26 | nom seul | `spatial_layers` bâti : pas de colonne édition (seul `created_at`) | **PARTIEL (honnête)** — placeholder, aucune fausse date |
| **LiDAR HD** | « Survol **11/08–11/10/2023** · MNx édités **13/03/2025** » `app.py:3653` | nom si hauteur sourcée `blocs/sources.py:61` (sans date) | `batiment_hauteur_lidar` survol **2023-08-11→2023-10-11** ✓ ; « 13/03/2025 » **stocké nulle part** | **PARTIEL** — survol exact ; édition littérale en dur |
| **SITADEL** | millésime « 2026-08 », horizon **2026-06-30** `app.py:1401/3653` | permis datés par parcelle `miroir.py:325` | `sitadel_permits.date` max = **2026-08-31** | « 2026-08 » OUI ; **horizon périmé 2 mois** |
| **SIRENE** | « 2026-09 », last_sync 2026-10-18 | nom seul | `sirene_etablissements.date_dernier_traitement` max = **2026-09-30** | **OUI** |
| **RNIC** | « extraction annuelle » (aucune année), last_sync **2026-10-11** | nom seul ; copro comptée sans date `miroir.py:293` | `rnic_coproprietes.ingested_at` uniforme = **2026-10-11** | **PARTIEL** — `ingested_at` LABUSE sert de fraîcheur |
| **OLL** | « OLL **2024** » | nom seul | `oll_loyers.annee` = **2024** | **OUI** |
| **PLU/GPU** | « révisions — détail en fiche » | PLU daté par fiche `etude_faisabilite.py:915` | `parcel_zone_plu_version` par commune | **GÉNÉRIQUE** — défère au détail (non falsifiable ici) |

Présence réelle par parcelle (ce que la fiche listerait) : DVF récent sur BW1407 (2023-10-31), HV0135 (**2025-08-29**), CY0369 (2023-06-06), ES0741 (2021-07-09) ; copro RNIC sur BW1407, HV0135, ES0741 ; permis Sitadel 2026 sur AP0786 (×2), AR0040, CY0369 ; survol LiDAR 2023 sur 8/10.

## 3.4 Constats

### L-MIL-01 — majeur — La date d'approbation PPR affichée est globale (la plus récente d'AILLEURS), jamais celle de la commune de la parcelle
- **Gravité** : majeur (fait réglementaire — un PPR est communal ; mal le dater fausse la perception de l'opposabilité).
- **Reproduction** : fiche de toute parcelle hors Saint-André (ex. 97422000BW1407 Le Tampon, 97413000DF0259 Saint-Leu) → « Les données » / ligne cascade PPR → « PPR le plus récent approuvé le **2026-04-16** ».
- **Affiché c. juste** : affiché « approuvé le 2026-04-16 » pour **toutes** les communes ; juste = Le Tampon 2017-10-20, Saint-Leu 2015-11-23, Saint-Joseph 2017-03-16… `spatial_layers kind='ppr_etat'` : **seule SAINT-ANDRÉ** porte 2026-04-16.
- **fichier:ligne** : `data_sources.source_millesime` (ligne unique) ; servi `src/labuse/api/app.py:3653` (liste) et `app.py:4694`→`primitives.tsx:284` (cascade). Vérité par commune dans `spatial_layers` (`ppr_etat`).
- **Proposition** : composer la date PPR **par commune de la parcelle** (comme la ligne aléas par parcelle, `miroir.py:456`) ; à défaut retirer la date du libellé global (« PPR approuvé — date par commune en fiche »).

### L-MIL-02 — majeur — Les notes techniques internes du millésime fuient à l'écran dans les lignes de cascade (brut), alors que « Les données » de la même fiche les nettoie
- **Gravité** : majeur (jargon interne servi au client ; divergence intra-écran du même champ).
- **Reproduction** : fiche d'une parcelle avec bâti / DPU / pente → onglet contraintes → ligne de cascade → millésime inline BRUT.
- **Affiché c. juste** : la cascade affiche « BD TOPO® V3 — **édition non enregistrée** », « GPU typeinf 04 — **partiel, non-publiées listées** », « BD CARTO® V5 (**proxy**) », « **proxy RPG.LATEST** », « PCI — **« latest » ingérée** » ; alors que « Les données » sur la même fiche affiche la version nettoyée.
- **fichier:ligne** : `src/labuse/api/app.py:4694` (pose `source_millesime` SANS `nettoyer_notes_internes`) ; rendu `frontend/src/components/fiche/primitives.tsx:284-285`. Le nettoyeur existe (`millesime_source.py:56`) et est appliqué `app.py:3653` (liste) mais pas `:4694` (cascade).
- **Proposition** : passer `source_millesime` par `nettoyer_notes_internes`/`composer` au point `app.py:4694`, comme la liste « Les données ».

### L-MIL-03 — mineur — `source_horizon_at` de SITADEL est périmé de 2 mois vs le dernier permis ingéré
- **Reproduction** : parcelles 97403000AP0786, 97411000AR0040, 97412000CY0369 (permis 2026) ; tout consommateur de `source_horizon_at` SITADEL.
- **Affiché c. juste** : `source_horizon_at=2026-06-30` ; réel `sitadel_permits.date`/`p_model_permits.date_autorisation` max = **2026-08-31**. Le millésime texte dit pourtant « 2026-08 » → deux champs de la même ligne se contredisent.
- **fichier:ligne** : `data_sources` (SITADEL) ; lu `src/labuse/api/app.py:1401-1403, 3653`.
- **Proposition** : recaler `source_horizon_at` sur `max(date)` réel à l'ingestion SITADEL. (Corrobore L-CHN-07.)

### L-MIL-04 — mineur — Une date d'édition LiDAR (« MNx édités 13/03/2025 ») est un littéral en dur absent de la base
- **Reproduction** : fiche avec hauteur LiDAR → « Survol 11/08–11/10/2023 · MNx édités **13/03/2025** ».
- **Affiché c. juste** : survol exact (`batiment_hauteur_lidar.date_debut/fin_survol`) ; « 13/03/2025 » n'existe dans **aucune** colonne (la seule autre date, `mesure_le`=2026-09-10, est le calcul LABUSE, correctement non affiché).
- **fichier:ligne** : `data_sources.source_millesime` (LiDAR HD) texte libre.
- **Proposition** : retirer la date d'édition non traçable (garder la fenêtre survol vérifiable) ou l'ingérer en colonne.

### L-MIL-05 — mineur/dette — Pour Cadastre et RNIC, une date d'ingestion/sync LABUSE tient lieu de millésime producteur
- **Reproduction** : Cadastre « latest ingérée » + last_sync **2026-10-11** alors que les 10 parcelles sont ingérées **2026-06-28/29** ; RNIC « extraction annuelle » (aucune année) + last_sync **2026-10-11** = `rnic_coproprietes.ingested_at` uniforme.
- **Affiché c. juste** : pas de fausse date, mais une date LABUSE présentée comme « millésime de source ».
- **fichier:ligne** : `data_sources` (Cadastre PCI ; RNIC Anah), composer `app.py:3680/3653`.
- **Proposition** : étiqueter « ingéré le JJ/MM/AAAA » (déjà le rôle de `libelle_date_source`, `millesime_source.py:113`) plutôt qu'une date de sync nue ; pour RNIC, exposer l'année d'extraction si fournie.

## 3.5 Verts (cohérents écran/base)
DVF (plage + horizon 2025-12-31 = max réel), SIRENE (2026-09 = max), OLL (2024 = seule année), LiDAR fenêtre de survol (11/08–11/10/2023 exacte). Le PDF n'affiche volontairement aucun millésime dans sa liste de sources (`blocs/sources.py:53`) — divergence écran↔PDF **par conception** (voir L-CHN-02).

---

# 4. Les jobs planifiés

**Trois mécanismes cron coexistent** ; la vérité est le **registre `src/labuse/jobs.py`** (c'est lui que `labuse jobs crontab --tz reunion` convertit en +4 h et que `deploy.sh:59-72` pose dans le fichier UNIQUE `/etc/cron.d/labuse`, VPS en fuseau `Indian/Reunion`). Le legacy `/etc/cron.d/labuse-*` (13 fichiers) est retiré par `deploy.sh:74-80`. `poser_crontab_solidite.sh` est un patch obsolète.

## 4.1 Tableau des 30 jobs (registre)

cron_utc = brut registre ; Réunion = +4 h (posé/exécuté).

| Job | cron_utc | Réunion | Source |
|---|---|---|---|
| sonde-sources | `0 3 * * *` | 07:00 quotidien | jobs.py:380 |
| agents-sources | `0 19 * * 0` | 23:00 dim (hebdo, gating 1/2 en code) | jobs.py:386 |
| filtres-sources | `5 3 * * *` | 07:05 quotidien | jobs.py:397 |
| coherence-robinets | `25 3 * * *` | 07:25 quotidien | jobs.py:402 |
| ingest-bodacc | `40 2 * * *` | 06:40 quotidien | jobs.py:407 |
| ingest-sitadel | `30 0 10 * *` | 04:30 le 10 mensuel | jobs.py:413 |
| ingest-dpe | `0 0 12 * *` | 04:00 le 12 mensuel | jobs.py:419 |
| ingest-sirene | `0 0 7 * *` | 04:00 le 7 mensuel | jobs.py:424 |
| sync-gpu | `0 0 15 * *` | 04:00 le 15 mensuel | jobs.py:429 |
| ingest-dvf | `0 1 * * 2` | 05:00 mardi hebdo | jobs.py:438 |
| backup-postgres | `30 9 * * *` | **13:30** quotidien | jobs.py:445 |
| pg-maintenance | `0 0 * * 0` | 04:00 dim hebdo | jobs.py:459 |
| purge-runs | `30 0 * * 0` | 04:30 dim **[GELÉ]** | jobs.py:464 |
| healthcheck | `*/15 * * * *` | toutes 15 min | jobs.py:475 |
| sante-endpoints | `7,37 * * * *` | toutes 30 min | jobs.py:480 |
| copilote-purge | `30 23 * * *` | 03:30 quotidien | jobs.py:485 |
| abuse-scan | `0 6 * * *` | 10:00 quotidien | jobs.py:493 |
| purge-sessions | `0 4 * * *` | 08:00 quotidien | jobs.py:498 |
| radar-cloche | `5 3 * * *` | 07:05 quotidien **[GELÉ si notifs off]** | jobs.py:506 |
| radar-cycle | `0 0 * * *` | 04:00 quotidien | jobs.py:516 |
| radar-cycle-dvf | `30 0 * * *` | 04:30 quotidien | jobs.py:523 |
| radar-cycle-mensuel | `30 1 1 * *` | 05:30 le 1er mensuel | jobs.py:529 |
| evaluer-suivis | `2 3 * * *` | 07:02 quotidien | jobs.py:540 |
| detect-events | `4 3 * * *` | 07:04 quotidien | jobs.py:549 |
| digest | `15 3 * * *` | 07:15 quotidien **[GELÉ si notifs off]** | jobs.py:555 |
| mail-queue-consommer | `*/5 * * * *` | toutes 5 min | jobs.py:570 |
| fiche-commune-cache | `0 23 * * *` | 03:00 quotidien | jobs.py:582 |
| coherence-banc | `45 23 * * *` | 03:45 quotidien | jobs.py:592 |
| verite-sources | `0 2 15 * *` | 06:00 le 15 mensuel | jobs.py:610 |
| signal-instantane | `0 2 1 * *` | 06:00 le 1er mensuel | jobs.py:622 |

Les 30 labels `heure_reunion` internes sont cohérents (0 écart par calcul). Gels : `purge-runs` (statique `jobs.py:473`) ; `radar-cloche`/`digest` (dynamique `_gel_notifs` `jobs.py:370-375`).

## 4.2 Échec « 2 fois d'affilée » + visibilité admin
Mécanique commune (`jobs.py:exec_one`→`_journaliser_et_alerter` `:155-184, 262`) : 1er échec = état `echec|timeout` + ligne `job_runs` + ouverture incident `job-echec:<nom>` (1 mail Brevo + cloche, `ops_alertes.py:138-143`). 2e échec (j+1) = `rappel` (≤1/jour, jour Réunion, `ops_alertes.py:148-163`) — **pas d'escalade, pas de retry auto** (sauf `mail-queue-consommer`, file interne 5 min/1 h/24 h). Retour vert = mail « résolu ». Seul `healthcheck` applique un seuil « 2 échecs » AVANT d'alerter (`jobs_impl.py:424, 430, 483-484`). Visibilité : `/admin/cron` (badge ÉCHEC + erreur), `/admin/usine` (pastille rouge echec/timeout, ambre périmé), cloche + vigie « jobs en retard ».

## 4.3 Constats

### L-JOB-01 — majeur — Un job qui n'a JAMAIS réussi est invisible de la vigie « en retard »
- **Reproduction** : `ops_alertes._jobs_en_retard` saute tout job dont `dernier_succes is None` (`ops_alertes.py:327-329`) ; Usine `_job_perime` renvoie `False` si `statut not in ("ok","dry-run")` (`cockpit_resume.py:43-44`). Si la ligne cron n'est jamais tirée, ou si le tout premier passage échoue en boucle, aucun « retard » n'est signalé.
- **Affiché c. juste** : Usine peint « à l'arrêt » (gris) / `/admin/cron` « JAMAIS » — indistinguable d'un job neuf pas encore dû, alors qu'il peut être cassé depuis l'installation.
- **fichier:ligne** : `src/labuse/ops_alertes.py:327-329` ; `src/labuse/cockpit_resume.py:43-44, 72-73`.
- **Proposition** : vigie « job planifié jamais vu depuis N× cadence après installation » (date de pose connue via `deploiement.json`) ; distinguer « jamais lancé » de « arrêté ».

### L-JOB-02 — majeur — La moitié des jobs est hors du monitoring public `/healthz/crons`
- **Reproduction** : `_crons_du_registre` ne retient que `TOUCHE_EAU` + `backup-postgres` (`ops.py:44-62`). Donc `mail-queue-consommer`, `digest`, `healthcheck`, `sante-endpoints`, `purge-sessions`, `copilote-purge`, `radar-cycle[-dvf/-mensuel]`, `radar-cloche`, `coherence-banc`, `fiche-commune-cache`, `pg-maintenance`, `signal-instantane`, `evaluer-suivis`, `detect-events` ne figurent pas dans `GET /healthz/crons`.
- **Affiché c. juste** : le moniteur VPS (et `docs/EXPLOITATION-CRON.md:41`) affiche `ok:true` même si `mail-queue-consommer` (envoi des mots de passe/confirmations) ou `digest` est mort.
- **fichier:ligne** : `src/labuse/api/ops.py:45-47, 70-120`.
- **Proposition** : exposer l'état de TOUS les jobs planifiés (via `_jobs_en_retard` déjà exhaustif), ou au moins les critiques (mail-queue, digest).

### L-JOB-03 — mineur — `/admin/cron` ignore le gel et affiche une « prochaine exécution » mensongère
- **Reproduction** : `jobs.liste()` renvoie `gel`/`planifie`/`prochaine_reunion` (`jobs.py:331-347`), mais le type front `CronJob` n'a ni `gel` ni `planifie` (`api.ts:2948-2953`) et `Cron.tsx` n'en affiche aucun. `prochaine()` est calculée inconditionnellement, même pour un job gelé.
- **Affiché c. juste** : un job gelé (`purge-runs`, ou `digest`/`radar-cloche` si notifs off) affiche « ▶ prochaine : <date future> » (`Cron.tsx:36`) alors que cron ne le lancera jamais ; aucune mention « gelé ». `/admin/usine` le gère correctement — incohérence propre à `/admin/cron`.
- **fichier:ligne** : `frontend/src/components/admin/Cron.tsx:9-15, 36` ; `frontend/src/lib/api.ts:2948-2953` ; `src/labuse/jobs.py:331`.
- **Proposition** : ajouter `gel`/`planifie` au type et à l'affichage (badge GELÉ, masquer « prochaine »), ou rediriger vers `/admin/usine`.

### L-JOB-04 — dette — Conversion de fuseau `_h_reunion` à modulo 24 : day-wrap latent
- **Reproduction** : `_h_reunion` (`cli.py:4955-4960`) ajoute 4 h modulo 24 sur le seul champ heure, sans ajuster jour-du-mois/semaine. 0 bug actif (aucun job spécifique-au-jour ne franchit minuit), mais un futur `0 21 15 * *` deviendrait `0 1 15 * *` = 01:00 Réunion **le 15** au lieu du **16**.
- **fichier:ligne** : `src/labuse/cli.py:4951-4960`.
- **Proposition** : refuser (ou décaler le jour) à la génération si `(int(h)+4)>=24` sur un cron à `dom`/`dow` non-`*`.

### L-JOB-05 — dette — `docs/EXPLOITATION-CRON.md` périmé (décrit le legacy retiré, horaires faux)
- **Reproduction** : le doc décrit 13 fichiers `/etc/cron.d/labuse-*` comme installés (`EXPLOITATION-CRON.md:7-31`), or `deploy.sh:74-80` les retire. Horaires divergents : backup « 09:30 Réunion » (doc) vs **13:30** (registre `jobs.py:446`) ; bodacc « 06:30 » vs 06:40 ; sitadel/dpe/dvf en quotidien/hebdo (doc) vs mensuel/hebdo-mardi (registre) ; jobs du registre absents du doc.
- **fichier:ligne** : `docs/EXPLOITATION-CRON.md:7-36` ; `docs/EXPLOITATION.md:81, 169` ; horaire réel `src/labuse/jobs.py:445-446`.
- **Proposition** : régénérer la doc depuis le registre (`labuse jobs crontab`).

### L-JOB-06 — mineur — `poser_crontab_solidite.sh` injecte un job retiré du registre (`recap-matin`)
- **Reproduction** : le script ajoute `labuse jobs run recap-matin` et refuse si le job n'existe pas (`poser_crontab_solidite.sh:30-54`) ; or `recap-matin` a été retiré (`jobs.py:602-607`) → `exit 1`. De plus le script contredit le mécanisme actuel (fichier unique régénéré par `deploy.sh`).
- **fichier:ligne** : `deploy/scripts/poser_crontab_solidite.sh:30-54` ; `src/labuse/jobs.py:602-607`.
- **Proposition** : supprimer le script.

### L-JOB-07 — mineur — Le commentaire `planifie=False` cite `agents-sources`, qui est en réalité planifié
- **Reproduction** : `jobs.py:79-81` donne `agents-sources` comme exemple de `planifie=False` ; or il ne le passe pas (`jobs.py:386-396`, défaut `True`). Il est émis au crontab `0 19 * * 0` UTC = 23:00 dim Réunion **toutes les semaines** ; le filtre 1/2 vit dans le code (`semaine_agents`, `jobs.py:301-304`), pas dans cron. Cadence annoncée « 15 j » ≠ fréquence cron (hebdo).
- **fichier:ligne** : `src/labuse/jobs.py:79-81, 386-396, 301-304`.
- **Proposition** : corriger le commentaire (aucun job n'utilise `planifie=False`) ou documenter la cadence réelle (hebdo + gating applicatif).

## 4.4 Points vérifiés sains (jobs)
- Pas de double-conversion de fuseau (registre UTC → `--tz reunion` +4 h → VPS `Indian/Reunion`).
- Verrou anti-chevauchement partagé cron↔bouton admin (flock `-E 200`, `run-job.sh`) ; tour sauté ≠ échec.
- Timeout par job (SIGALRM) + purge du pool après timeout (`jobs.py:139-152, 205-241`).
- Dédup des alertes au **jour Réunion** explicite en SQL (`ops_alertes.py:148-151`).
- Règle dry-run SMTP (jobs d'envoi calculent sans envoyer, visible en badge).
- Parseur cron gère listes/plages/pas sans lever (`jobs.py:267-298`, `tests/test_cron_parser.py`).

---

# Annexe — fichiers clés
- Extension : `outils/radar-extension/background.js`, `popup.js`, `options.js`, `options.html`, `manifest.json`, `recette_*.mjs`.
- Serveur capture : `src/labuse/pige/api.py:174-220`, `src/labuse/pige/html_ingest.py:45-52, 459-528`.
- Chaîne/millésime : `src/labuse/sentinelle.py`, `millesime_source.py:56-113`, `fraicheur_caches.py:73-91`, `ingestion/fraicheur.py:6-9,158-160,335-367,453-473`, `bascule_gardes.py:158-216,476-538`, `flux.py:150-237`, `api/app.py:1282-1401,3590-3687,4694,6108-6167`, `registre/valeur.py:135-163`, `exports/blocs/sources.py:27-76`, `exports/miroir.py:285-456`, `ingestion/seed_sources.py`, `config/served_manifest.json`, `config/plu_millesimes.yaml`.
- Jobs : `src/labuse/jobs.py`, `jobs_impl.py:424-484`, `ops_alertes.py:138-339`, `cockpit_resume.py:33-78,607-632`, `api/ops.py:44-120`, `cli.py:4949-4992`, `frontend/src/components/admin/Cron.tsx`, `deploy.sh:55-80`.
