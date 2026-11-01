# MANDAT AUDIT-NU-3 — Lot H : Entrées hostiles et cas limites

**Registre.** Audit **LECTURE SEULE** joué le 2026-11-01. Branche `audit/nu-3-h`, worktree
`~/Desktop/labuse-nu3-h`, API **9290** (venv `uv` PDF-capable créé dans le worktree, deps `requirements.lock`),
front **servi par l'API** depuis `frontend/dist` reconstruit sur CETTE branche (`vite build`, `node_modules`
emprunté à `labuse-main` — deps identiques ; diff front vs `main` = 5 lignes, hors périmètre layout). Base Mac
`labuse` (**434 582 parcelles**, run servi `q_v20`, SRID 2975, PostGIS). **Aucune écriture base** (hors ce que
l'app écrit elle-même — ici rien : auth locale désactivée, zéro session créée), **aucun merge, aucun accès prod**.
Deux autres lots (G, J) tournaient en parallèle : Postgres **jamais coupé** (ressource partagée) — le scénario
« coupure de la base » est donc raisonné sur le code, pas joué (dit explicitement plus bas).

> Méthode. Chaque constat live est reproductible par une commande `curl` sur `127.0.0.1:9290` (transcrits ci-dessous)
> ou une requête `psql labuse`. Les captures mobiles sont dans `captures/` (binaire, **non versionné** — politique
> MENAGE-1 `**/captures/`, non forcé). Les vérifications de droits et de données extrêmes ont été menées en partie
> par sous-agents forkés (lecture seule), puis **re-vérifiées à la main** sur les points retenus.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~110** : batterie saisies hostiles sur 5 routes GET + 4 POST (SQLi, HTML, emoji, accents, retours-ligne, apostrophes, bornes de `limit`/`offset`, IDU malformés/espaces/minuscules, `source` injectée) ; 10 valeurs numériques hostiles sur l'estimation + 5 sur le bilan promoteur ; SSRF (localhost, métadonnées AWS, `file://`, IP décimale, redirection) ; 10 fiches en parallèle ; pagination au-delà ; 6 parcelles extrêmes (0,027 m², contenance NULL, disparue, vente 1 €, 59 mutations) × fiche + PDF + estimation ; app complète à **390 px** et **768 px** (+ fenêtre de bureau rétrécie) ; droits (admin, expiré, paiement requis, jeton, liens mail). |
| **Bloquant** | **0** |
| **Majeur** | **2** |
| **Mineur** | **4** |
| **Dette** | **2** |

**Verdict de synthèse.** La surface d'entrée est **largement durcie** — l'héritage des campagnes « C5 / GB-034-036 /
URGENCE-1 » tient : SQL paramétré partout (injection → liste vide, jamais une erreur), SSRF fermé au cordeau,
`UnicodeError→400`, `DataError→422`, `_check_idu` contre l'octet nul, popups carte en `textContent`. Le danger
résiduel n'est **pas** l'injection : c'est **l'absence d'un filet générique**. Il n'existe **aucun
`@app.exception_handler(Exception)`** — la promesse « jamais un 500 » est tenue cas par cas, et **une seule valeur
oubliée la casse** : `surface_hab=inf` lève un `OverflowError` Python AVANT SQL → **500 brut** servi au client
(prouvé live). Même gap pour une coupure de base en plein calcul. Côté droits, un trou net : un compte dont le
paiement échoue (`paiement_requis`) **garde l'accès payant complet** tant que Stripe n'a pas résilié. Côté mobile,
l'app **se barricade** sous 1 024 px (écran « disponible sur ordinateur ») — donc « rien de coupé » est tenu sur un
vrai téléphone ; la seule casse est l'en-tête d'une **fenêtre de bureau rétrécie** (non filtrée par la porte).

---

## Trouvailles

### NU-3-H-M01 — MAJEUR — `surface_hab=inf` (et valeurs scientifiques qui débordent) → **HTTP 500 brut**

- **Où** : `GET /radar/annonce/estimation/{idu}` (`src/labuse/pige/api.py:1746`, param `surface_hab: float | None = None`
  **sans bornes**) → `estimation_annonce` (`:1724`) → `_surface_pour_total` (`src/labuse/pige/api.py:1554-1555`).
- **Repro** :
  ```
  curl -G 'http://127.0.0.1:9290/radar/annonce/estimation/97411000IE0241' --data-urlencode 'surface_hab=inf'
  → 500 Internal Server Error
  curl -G '.../estimation/97411000IE0241' --data-urlencode 'surface_hab=1e309'   # 1e309 = inf en float → 500
  ```
  Trace serveur : `OverflowError: cannot convert float infinity to integer` à `pige/api.py:1555`.
- **Affiché vs juste** : le code garde `if isinstance(surface_hab,(int,float)) and surface_hab > 0: s = round(surface_hab)`.
  `inf > 0` est vrai, et `round(inf)` **lève**. Le garde teste le signe, jamais la finitude. Résultat : un **500 brut**
  (`"Internal Server Error"`, corps texte) là où le mandat exige « jamais un 500 ». Table mesurée sur `97411000IE0241` :

  | `surface_hab` | HTTP | observé |
  |---|---|---|
  | `85` (normal) | 200 | médiane 3990, `bati` |
  | `-500` | 200 | médiane 3990 — **négatif silencieusement ignoré** (cf. m04) |
  | `0` / `nan` | 200 | ignoré (tombe sur DVF) |
  | `1e30` / `1e308` | 200 | médiane 4036 — la valeur énorme **influe** sur le total |
  | **`inf` / `1e309`** | **500** | **OverflowError brut** |
  | `abc` / `45,5` (virgule FR) | 422 | propre (cast float refusé par FastAPI) |

- **Cause racine (systémique)** : il n'y a **aucun catch-all** — `grep '@app.exception_handler'` ne donne que
  `StarletteHTTPException` (`app.py:756`), `UnicodeError` (`:768`) et `_SA_DataError` (`:778`). Un `OverflowError`
  n'est **aucun des trois** (il naît en Python, pas dans SQL, donc pas un `DataError` 22xxx) → il remonte nu → 500.
  Le champ « surface habitable » est **optionnel et exposé à l'écran « Estimer un bien » (par adresse)** ; une valeur
  collée/énorme y est atteignable.
- **Capture** : transcrit curl ci-dessus + `grep OverflowError /tmp/nu3h_api.log`.
- **Amélioration** : (1) borner le param — `surface_hab: float | None = Query(None, gt=0, le=100000)` coupe AVANT le
  handler ; (2) à `pige/api.py:1554`, remplacer `surface_hab > 0` par `math.isfinite(surface_hab) and surface_hab > 0` ;
  (3) **la vraie ceinture** : ajouter un `@app.exception_handler(Exception)` qui journalise la trace serveur et rend
  un 500 JSON neutre (`{"detail":"erreur interne"}`) — cf. dette D01. Sans lui, chaque nouvel `int()/round()` non
  borné rouvre le même trou.

### NU-3-H-M02 — MAJEUR — Un compte « paiement requis » conserve l'accès payant complet

- **Où** : `session_utilisateur` (`src/labuse/comptes.py:456,466`) — liste de rejet ; `facturation.py:470` pose
  `comptes.statut='paiement_requis'` sur l'évènement Stripe `invoice.payment_failed` (`:462`).
- **Repro (dérivé, re-vérifié en code)** : carte refusée → Stripe émet `invoice.payment_failed` → le compte bascule
  `paiement_requis`. Or `session_utilisateur` **ne rejette que** `("supprime","suspendu")` (`:456`) puis
  `("suspendu","resilie","invite")` (`:466`) — **`paiement_requis` n'y figure pas**. Le cookie de session reste
  pleinement valide à chaque requête, et un nouveau `/login` réussit (statut ≠ `invite`/`suspendu` → création de
  session normale, `app.py:901`). `grep -rn paiement_requis src/labuse` confirme : **aucune porte runtime**, aucun 402,
  aucun bandeau serveur — la valeur n'est consommée nulle part côté accès.
- **Affiché vs juste** : le commentaire `facturation.py:469` promet « l'app passe "paiement requis" (bandeau, pas un
  500) ». En réalité l'état est **indiscernable de `actif`** pour le back : l'utilisateur garde **tout** l'accès payant
  (349 €/mois) pendant **toute** la fenêtre de relance Stripe (jours/semaines), jusqu'à l'escalade
  `customer.subscription.deleted` → `suspendre_compte` (`facturation.py:496`). C'est une grâce « douce » **non bornée
  et invisible**.
- **Amélioration** : soit un bandeau réellement câblé depuis `statut_compte`, soit — plus sûr — une échéance de grâce
  (ex. 7 j) après laquelle `paiement_requis` est traité comme `suspendu` dans `session_utilisateur:466`.

### NU-3-H-m01 — MINEUR — IDU en minuscules (ou avec espace final) → 404 « inconnue » sur une parcelle existante

- **Où** : `_check_idu` (`src/labuse/api/app.py:8192-8200`) ; route fiche `app.py:7189`.
- **Repro** :
  ```
  curl '.../parcels/97411000ie0241?source=q_v20'   → 404 "Parcelle 97411000ie0241 inconnue…"
  curl '.../parcels/97411000IE0241?source=q_v20'   → 200   (la MÊME parcelle, en MAJUSCULES)
  curl '.../parcels/97411000IE0241%20?source=...'  → 404   (espace final)
  ```
- **Affiché vs juste** : `_check_idu` valide `[0-9A-Za-z]{1,20}` **sans normaliser la casse ni trim** ; les IDU en base
  sont en MAJUSCULES, donc une saisie/collage en minuscules passe le garde puis ne matche pas → « inconnue » **à tort**.
  L'autocomplétion fournit toujours des majuscules, mais un lien partagé/collé ou saisi à la main casse.
- **Amélioration** : `idu = (idu or "").strip().upper()` en tête de `_check_idu` (la regex reste la ceinture).

### NU-3-H-m02 — MINEUR — `source=q_v*` inexistante (ou toute valeur hors `q_v`) silencieusement remplacée par le run par défaut

- **Où** : `parcel_fiche` (`src/labuse/api/app.py:7198`) — `run = source if (source and source.startswith("q_v")) else runs.current()`.
- **Repro** (md5 du corps identique dans tous les cas) :
  ```
  source=q_v20            → 200  md5=2f0c8cca…   (référence)
  source=q_v99999         → 200  md5=2f0c8cca…   (run inexistant)
  source=q_v20'--         → 200  md5=2f0c8cca…   (injection → inoffensive, paramétrée)
  source=../../etc/passwd → 200  md5=2f0c8cca…   (ne commence pas par q_v → défaut)
  source=totally_bogus    → 200  md5=2f0c8cca…
  ```
- **Affiché vs juste** : **positif sécurité** (aucune injection, aucun traversal : le run file une requête paramétrée,
  un run inconnu retombe sur le défaut). **Mais** un run `q_v*` inexistant est servi **comme s'il était valide**, sans
  le moindre signal — un partenaire API croyant épingler le run X reçoit le run courant, octet pour octet. Comparer :
  `GET /sources/{id}` sait répondre `404 "Source inconnue"` (`app.py:1512`) ; la fiche, non.
- **Amélioration** : si `source` est fourni et ne résout pas un run connu, répondre `404 "run inconnu"` (ou `?strict=1`),
  plutôt que de servir le défaut en silence.

### NU-3-H-m03 — MINEUR — Fenêtre de bureau rétrécie (< ~420 px) : l'en-tête se chevauche / déborde hors écran

- **Où** : la porte mobile `frontend/src/lib/appareil.ts` (`estAppareilMobile`) bloque sur **l'écran PHYSIQUE**
  (`window.screen.width < 1024`) **une seule fois au chargement**, pas sur la largeur de fenêtre — donc une fenêtre de
  bureau simplement rétrécie **n'est PAS filtrée** (commentaire assumé dans le fichier). La barre du haut (logo +
  recherche + badge « Fiche commune » + cloche + compte) n'est pas responsive sous ~420 px.
- **Repro** : écran physique ≥ 1024 px, fenêtre amenée à 390 px (ou DevTools responsive avec `screen.width` ≥ 1024).
  Mesuré via Playwright : à 390 px, `document.scrollWidth == 390` (**pas** de défilement horizontal de page, bon point)
  **mais 22 éléments** ont leur bord droit **au-delà** du viewport (jusqu'à `right=458-488 px`) : ils sont **rognés**
  (overflow masqué) donc **inaccessibles** — la boîte de recherche recouvre le badge « Fiche comm… », les contrôles de
  droite (cloche, compte) sortent de l'écran. À **768 px** : quasi propre (4 débordements mineurs, `maxRight≈797`, soit
  ~29 px, hors marqueurs carte).
- **Capture** : `captures/mobile-390-app-fullapp.png` (en-tête rogné), `captures/narrow-768-fiche.png` (propre).
- **Nuance honnête** : sur un **vrai** téléphone/tablette (< 1024 px physique) l'app sert l'écran unique
  « disponible sur ordinateur » — donc **rien n'est coupé** là où le mandat le craignait. Le défaut ne touche que le
  cas « bureau en demi-écran ».
- **Amélioration** : rendre la barre du haut responsive (wrap / menu condensé) sous ~640 px, puisque ce cas échappe à
  la porte `appareil.ts`.

### NU-3-H-m04 — MINEUR — Surface habitable **négative** silencieusement acceptée (estimation rendue comme si le champ était vide)

- **Où** : `_surface_pour_total` (`src/labuse/pige/api.py:1554`).
- **Repro** : `surface_hab=-500` → 200, médiane 3990 (identique à champ vide). Le garde `surface_hab > 0` fait tomber
  le négatif sur la branche DVF/ratio **sans le signaler**.
- **Affiché vs juste** : pas de crash, pas de valeur aberrante — mais une saisie manifestement fautive est **avalée en
  silence** plutôt que refusée ; l'utilisateur croit avoir renseigné sa surface alors qu'elle est ignorée.
- **Amélioration** : refuser (`422`) une surface ≤ 0 via `Query(gt=0, …)` (mutualisé avec M01), ou retourner une note
  « surface ignorée (valeur invalide) ».

### NU-3-H-D01 — DETTE — Aucun `@app.exception_handler(Exception)` : toute exception Python non prévue fuit en 500 brut

- **Où** : `src/labuse/api/app.py:756-792` (trois handlers seulement).
- **Constat** : la garantie « jamais un 500 » est **per-case**. Déjà déclenchée live par M01 (`OverflowError`). **Même
  classe, non jouée pour ne pas perturber G/J** : une **coupure de la base en plein calcul** (Étude, PDF) lève une
  `OperationalError` (connexion tombée) qui **n'est pas** un `DataError` → 500 brut. `pool_pre_ping=True`
  (`config.py:53`) ne protège qu'au **checkout** du pool (blip ENTRE requêtes), pas une coupure **pendant** une requête
  en cours. `/readyz` sait rendre un 503 propre si la base est injoignable (`app.py:1068`), mais les endpoints métier,
  non.
- **Amélioration** : un `@app.exception_handler(Exception)` qui journalise la trace côté serveur et rend un 500 JSON
  neutre — la ceinture générique qui ferme M01 **et** la famille « exception imprévue → 500 brut ».

### NU-3-H-D02 — DETTE — Garde admin en ligne (`exiger_admin(request)`) plutôt qu'en dépendance de routeur

- **Où** : `exiger_admin` (`src/labuse/api/auth.py:214`), appelé comme **première instruction** de chaque handler admin
  (ops/dashboard/courrier/protection/promo/partners/pige).
- **Constat** : l'énumération des **~95 décorateurs de routes admin** ne révèle **aucune route non gardée** (les 7
  « suspects » du scan AWK sont des faux positifs : `exiger_admin` suit une signature/imports plus longs). Donc
  **couverture complète aujourd'hui** — mais la protection tient à une ligne manuscrite par handler : **une seule
  oubliée = une route admin ouverte**, sans que les tests l'attrapent structurellement.
- **Amélioration** : porter la garde en `dependencies=[Depends(exiger_admin)]` sur les routeurs admin (fail-safe par
  construction).

---

## Ce qui a tenu (confirmations — l'audit valide aussi le durci)

| Vecteur | Résultat | Preuve |
|---|---|---|
| **Injection SQL** (autocomplete, `/parcels/search`, proprios) | **Fermé** — requête paramétrée → liste vide, 200, jamais d'erreur | `q=' OR 1=1--`, `q=';DROP TABLE parcels;--` → `{"features":[]}` |
| **SSRF** (`POST /radar/annonce/analyser`) | **Fermé** — schéma + liste blanche d'hôtes + blocage IP privée + pas de redirection | localhost / `169.254.169.254` / `file://` / IP décimale `2130706433` → `url_invalide`/`url_bloquee` ; `pige/api.py:1011-1048` |
| **XSS / HTML injecté** | **Non rendu** — `q=<img onerror=…>` → liste vide ; popups carte en `textContent` (`CouchesTuyau.tsx:365`, `popupXss.test`) ; le seul `dangerouslySetInnerHTML` « libre » est l'aperçu de gabarit **admin** (`Licences.tsx:207`) ; `BilanEcran.tsx:472` = chaînes **statiques** | batterie curl + lecture code |
| **Emoji / accents / retours-ligne bruts** | `400` propre (emoji non-encodé) ou liste vide ; accents OK | `UnicodeError→400` (`app.py:768`) |
| **Bornes `limit`/`offset`**, entier > bigint, `mult_min=1e999` | `422` propre ou liste vide — jamais 500 | `DataError→422` (`app.py:778`) + `Query(ge/le)` |
| **IDU** octet nul / HTML / emoji / 400 car. | `404` propre | `_check_idu` (`app.py:8192`) |
| **10 fiches en parallèle** | 10 × 200 | `for i in 1..10 … &` |
| **Pagination au-delà** (`offset=1e19`) | 200 vide / `422`, jamais 500 | `/communes`, `/parcels` |
| **Parcelles extrêmes** : 0,027 m² (`97401000AR1644`), contenance NULL (`97415000HO0313`), **disparue** (`97416000CR1226`), **vente 1 €** (`97411000DL0757`), **59 mutations** (`97415000BI0290`) | fiche + `export.pdf` + estimation **toutes 200** ; **vente 1 € ne pollue PAS** l'estimation (288 €/m², comparateur secteur) ; disparue → **fiche + PDF de courtoisie** | curl ; **ex-bloquant NU-A-003 (fiche disparue 500) = CORRIGÉ** |
| **Compte expiré / suspendu / essai échu** | session refusée à chaque requête (bascule à la requête, pas de cron) | `comptes.py:456-462` |
| **Jeton falsifié / expiré, logout rejoué** | 401/302 propre ; session révoquée serveur | `auth.py:180-211`, `app.py:1038` |
| **Liens mail** (reset, invitation, codes 2FA) | **usage unique** (token consommé en base en une passe atomique) | `comptes.py:585-600 / 329-346 / 536-546` |
| **Client → routes admin** | `403` ; `exiger_admin` sur ~95 routes, **0 oubli trouvé** | `auth.py:214` |
| **Mobile < 1024 px physique** | écran unique « disponible sur ordinateur » — **rien de cassé servi** | `appareil.ts`, `captures/mobile-390-landing.png` |

---

## Données extrêmes — couverture

| Cas | Témoin | Mesure | Écran/PDF |
|---|---|---|---|
| Surface ~0 | `97401000AR1644` | `ST_Area` = **0,027 m²** | fiche 200, PDF 200 |
| Contenance NULL | `97415000HO0313`, `97408000AR8001` | `contenance_m2 IS NULL` | fiche 200, PDF 200 |
| Parcelle disparue | `97416000CR1226` | `cadastre_disparue_le` non nul | fiche+PDF de courtoisie (ex-NU-A-003) |
| Vente ≤ 1 € | `97411000DL0757` (1 €), `97415000CH1825` (0,15 €) | `dvf_mutations_parcelle.valeur_fonciere` | estimation non polluée (288 €/m²) |
| Vendue ≥ 3×/an | `97415000BI0290` (59), `97422000EN0343` (57), `97404000AW0636` (53) | `count(DISTINCT id_mutation)`, Δdate ≤ 365 j | fiche 200, PDF 200 |
| Géométrie NULL | **AUCUN** | `geom IS NULL` → 0 ligne | — |
| IDU dupliqué | **AUCUN** | `GROUP BY idu HAVING count>1` → 0 ligne | `idu` unique en base |
| À cheval ≥ 3 zones | *non isolé* | intersection `spatial_layers.plu_gpu_zone` (requête bornée 25 s, 0 témoin sur 97415) | — |
| 200 bâtiments | *non témoigné* | nécessite jointure spatiale lourde (hors budget lecture-seule) | — |
| Propriétaire ≥ 1000 parcelles | *non témoigné* | la base Mac n'expose pas la table de propriété DGFiP (RGPD) ; `owner_enrichment` est de l'enrichissement, pas un lien compte→parcelles | — |

Les trois derniers cas n'ont pu être **témoignés dans cette base** (soit 0 occurrence, soit table de propriété absente) ;
dit ici explicitement plutôt que supposé couvert.

---

## Note d'intendance (axe concurrence & réseau)

- **10 requêtes identiques en parallèle** : jouées (10 × 200). **API lente simulée** : non simulée (pas de proxy de
  latence monté) ; le durcissement async existant (ÉTUDE-ASYNC-1, processus spawn tuable à la borne) est hors-périmètre
  de régression ici.
- **Deux comptes sur la même parcelle/le même projet** : non joué en live (auth locale désactivée → un seul contexte ;
  monter deux comptes payants eût exigé des écritures/Stripe hors cadre lecture-seule). À reprendre sur un banc
  multi-comptes dédié.
- **Coupure de base pendant une étude** : **non jouée** (Postgres partagé avec les lots G/J) → raisonnée en dette D01.

---

## Les deux correctifs à jouer en premier

1. **Un `@app.exception_handler(Exception)`** (D01) + borner `surface_hab` (M01) : ferme d'un coup le 500 brut prouvé et
   toute sa famille (coupure DB, futurs `round()`/`int()` non bornés).
2. **Traiter `paiement_requis` comme un état restreint** (M02) : au minimum un bandeau câblé, idéalement une échéance de
   grâce après laquelle `session_utilisateur` le coupe — sinon accès payant gratuit pendant toute la relance Stripe.
