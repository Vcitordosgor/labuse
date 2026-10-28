# RADAR-SOURCES-1 — Ajouter Bien'ici et SeLoger au Radar

**Audit lecture seule** · branche `audit/radar-sources-1` · worktree `~/Desktop/labuse-radarsources` · 28/10/2026
**Aucun code écrit, aucune capture en masse, rien touché en prod.** Ce fichier est le seul livrable.

---

## En une phrase

> **Bien'ici : FAIRE (en premier).** Données propres en JSON, protection anti-robots la plus
> légère des trois, et surtout des **coordonnées précises** qui peuvent enfin rattacher une annonce
> à une parcelle — le nerf qui est aujourd'hui débranché côté Leboncoin.
>
> **SeLoger : FAIRE PLUS TARD (et sous réserve).** La mécanique de capture est la même que
> Leboncoin (donc peu de travail), mais le site est verrouillé par DataDome et il **répète surtout
> des annonces d'agence déjà vues** sur Leboncoin et Bien'ici — la valeur ajoutée est faible et le
> risque de blocage réel.
>
> **Ordre conseillé : Bien'ici d'abord, puis mesurer, puis décider pour SeLoger.**

---

## Ce qui existe déjà (rappel de la chaîne Leboncoin)

Avant de parler des nouveaux sites, voici la chaîne actuelle, car **une bonne partie est déjà
prévue pour plusieurs sources** :

1. **Extension navigateur** (`outils/radar-extension/`) : tourne dans le vrai navigateur de Vic,
   ciblée `*.leboncoin.fr`. Un **battement de cœur** (`background.js:508-557`) se déclenche 1 fois
   par soir dans une fenêtre (21 h → minuit). Elle lit le HTML des pages de résultats
   (`__NEXT_DATA__`) et poste le tout au serveur (`POST /admin/radar/capture`, en-tête
   `X-Radar-Token`). Trois passes : nouvelles / relecture / confirmation.
2. **Parseur serveur** (`src/labuse/pige/html_next.py`) : `analyser()` lit le JSON Leboncoin
   (`__NEXT_DATA__.props.pageProps.searchData.ads`), `aplatir()` traduit chaque annonce dans le
   schéma LABUSE (prix, surfaces, type, commune, quartier, position, dates, DPE…).
3. **Modèle de données** (`src/labuse/pige/tables.py`) : **`pige_biens`** (un bien physique,
   dédoublonné) ↔ **`pige_annonces`** (une occurrence par portail). La colonne
   **`pige_annonces.portail`** existe déjà et accepte n'importe quel slug.
4. **Cycle de vie** (`cycle.py`) : apparu → vu → en vente longue (>90 j) → à revérifier (>60 j) →
   retirée → **vendue** (croisement DVF) ou retirée sans vente.
5. **Rattachement parcelle** (`rattachement_html.py`) et **croisement DVF** (`cycle.py:68`) : déjà
   **indépendants du portail** — ils travaillent sur la position et les surfaces, pas sur l'URL.

**Deux bonnes nouvelles pour ce chantier :**

- Les slugs **`seloger`** et **`bienici`** sont **déjà déclarés** (`portails.py:16-19`), avec leur
  préfixe d'URL. `slug_pour_url()` reconnaît donc déjà une URL SeLoger/Bien'ici. Aucune migration
  de base n'est nécessaire pour la colonne « site ».
- Le **dédoublonnage entre portails existe déjà** : `_est_meme_bien()` (`html_ingest.py:114-151`)
  fusionne deux annonces en un seul `pige_biens`. Il est portail-agnostique. (Détail au Lot 3.)

**Le seul endroit vraiment spécifique à Leboncoin** est `aplatir()` (`html_next.py:103-153`) : il
lit les noms de champs de Leboncoin (`real_estate_type`, `square`, `land_plot_surface`, `rooms`,
`energy_rate`, `location.source`, `owner.type`…). **C'est là que chaque nouveau site demande du
travail : un traducteur par site.**

---

## Lot 1 — Chaque site

### Bien'ici (bienici.com)

| Question | Réponse |
|---|---|
| **Comment arrive la liste** | **JSON pur, via une API interne.** Le site est une application Angular : la page HTML initiale est une coquille quasi vide, les annonces sont chargées ensuite par un appel à `https://www.bienici.com/realEstateAds.json?filters=…` (le `filters` est un objet JSON encodé : `filterType=buy`, `propertyType`, zone géographique, pagination `page`/`from`, `size=24`). La réponse contient `total` (nombre) + `realEstateAds` (tableau). |
| **Anti-robots** | **Le plus léger des trois.** Décrit comme « le portail français le plus fiable à lire ». L'API répond à condition d'envoyer des en-têtes de vrai navigateur (`user-agent`, `accept-language`, `x-requested-with: XMLHttpRequest`). Pas de DataDome/Cloudflare bloquant signalé ; au pire un `429` si on va trop vite → se calmer. **Dans notre cas (extension = vraie session du navigateur de Vic) la question ne se pose quasiment pas** : les en-têtes et cookies sont ceux d'un humain réel. |
| **Lisible par annonce** | prix, prix/m², surface, pièces, chambres, type (maison/appart/terrain…), ville + code postal + quartier, **coordonnées GPS**, dates `publicationDate` et `modificationDate`, **galerie de photos** (plusieurs tailles), `reference`, classe DPE/GES, agence. Riche et propre. |
| **Volume approx. Réunion** | De l'ordre de **2 000 à 2 800 annonces de vente** (même écosystème « nourri par les agences » que SeLoger ≈ 2 980 et Logic-Immo ≈ 2 750). Chiffre exact non vérifié (budget de consultation manuelle réservé) ; plafond technique de l'API : **~2 500 lignes par requête** — sans objet ici, La Réunion tient sous le plafond. |
| **Ce qui casse le plus vite** | (1) le **nom/les paramètres du `filters`** si Bien'ici change son API ; (2) le **plafond 2 500** si un jour la zone dépasse (improbable à La Réunion) ; (3) un `429` si on enchaîne trop vite. Le schéma des champs est stable et documenté. |

**À retenir :** Bien'ici donne des **coordonnées** par annonce. Or le point faible connu du Radar
(voir mémoire [[annonce-audit-1]], [[radar-etat-1]]) est que **Leboncoin ne donne qu'un centroïde
de commune** → 0 annonce rattachée à une parcelle. Des coordonnées Bien'ici feraient passer ces
annonces en `source_position = "address"` → **le rattachement parcelle (donc le croisement DVF,
donc « vendue »/« retirée sans vente ») pourrait enfin fonctionner.** C'est l'argument fort.

### SeLoger (seloger.com)

| Question | Réponse |
|---|---|
| **Comment arrive la liste** | **JSON embarqué dans le HTML** (comme Leboncoin). Site Next.js : la page d'annonce porte `<script id="__NEXT_DATA__">` → `props.pageProps.listingData` ; la page de résultats porte un `window["initialData"]` (tableau `cards` + pagination). Donc **même geste de capture que Leboncoin** : lire le HTML rendu et en extraire le JSON. |
| **Anti-robots** | **DataDome, agressif.** SeLoger est « hautement protégé » : empreinte navigateur, analyse des mouvements de souris, CAPTCHA, `403 hard_block` sur un client trop « propre ». DataDome fait du scoring comportemental par ML — **même une session techniquement parfaite peut échouer si le rythme ne ressemble pas à un humain.** Pour nous, la vraie session de Vic aide beaucoup, mais **une navigation automatique nocturne page-après-page reste le profil que DataDome cherche à attraper.** |
| **Lisible par annonce** | Très riche : prix, prix/m², surface, pièces, chambres, type, ville + code postal + quartier + **coordonnées**, photos (plusieurs tailles) + vidéo + visite 3D, `listingId`/`reference`, DPE/GES, année, équipements, agence. |
| **Volume approx. Réunion** | **≈ 2 980 annonces de vente** (dont ~1 450 maisons, ~630 appartements). Fortement alimenté par les agences. |
| **Ce qui casse le plus vite** | **DataDome** (le risque n°1 : blocage ou CAPTCHA pendant la passe du soir), puis un changement de structure Next.js (`initialData` / `listingData`). Le CAPTCHA est le plus pénible : il **arrête net** la passe et demande une main humaine. |

---

## Lot 2 — Réutiliser l'extension

### Ce qui se branche TEL QUEL (commun aux deux sites)

- **Le modèle de données** : `pige_biens` / `pige_annonces`, la colonne `portail`, les slugs
  `seloger`/`bienici` déjà déclarés. **Rien à migrer.**
- **Le cycle de vie** (`cycle.py`), le **rattachement parcelle** (`rattachement_html.py`) et le
  **croisement DVF** : portail-agnostiques, ils marcheront sur une annonce Bien'ici/SeLoger dès
  qu'elle est dans `pige_biens` **sans un ligne à changer** (et marcheront *mieux* avec les
  coordonnées Bien'ici).
- **Le dédoublonnage inter-portails** `_est_meme_bien()` : déjà écrit, déjà portail-agnostique.
- **Le point d'entrée serveur** (`POST /admin/radar/capture` / `deposer-html`) et la garde
  `X-Radar-Token`.

### Ce qu'il faut AJOUTER

| Site | Capture (extension) | Parseur (serveur) |
|---|---|---|
| **SeLoger** | **Faible** : même geste que Leboncoin (lire le HTML rendu). Ajouter `*://*.seloger.com/*` aux permissions et une table d'URLs par commune. | **Un parseur dédié** : lire `window.initialData` (résultats) / `__NEXT_DATA__.listingData` (annonce) et une **fonction `aplatir` propre à SeLoger** (noms de champs différents). |
| **Bien'ici** | **Moyen (chemin différent)** : les annonces ne sont PAS dans le HTML (SPA Angular). L'extension ne doit pas « lire la page » mais **appeler `realEstateAds.json` depuis la session** (un `fetch()` même-origine dans le script de contenu — ça passe l'anti-robots car c'est la vraie session). C'est un **nouveau mode de capture** « API », pas « HTML ». | **Trivial** : la réponse est déjà du JSON propre → juste une `aplatir` Bien'ici (mapping de champs). Pas de parsing HTML. |

**En clair :**
- **Dispatch** : `html_next.analyser()` devra **reconnaître le site** (via l'URL ou la forme du
  JSON) et router vers le bon traducteur. Aujourd'hui il est câblé sur les chemins Leboncoin.
- **Le vrai coût est le traducteur par site** (la fonction `aplatir`), pas la plomberie.
- Bien'ici déplace une partie du travail de l'extension (nouveau mode « appel API ») mais **allège
  le serveur** (JSON déjà propre). SeLoger fait l'inverse : extension quasi inchangée, mais parseur
  HTML/JSON à écrire et site plus fragile.

### Le même rythme du soir peut-il enchaîner les 3 sites ?

**Oui, mais pas naïvement.**

- Le battement de cœur actuel fait **une capture par jour** dans une fenêtre du soir. Enchaîner 3
  sites, c'est **~3× plus de navigation** (budgets actuels : 15 nouvelles + 20 relecture + 60
  confirmations ≈ par site), donc ~3× plus de surface d'exposition à l'anti-robots.
- **Bien'ici en mode API** coûte très peu de requêtes (24 annonces/appel, JSON) → se glisse dans le
  même battement sans problème.
- **SeLoger en navigation** est le plus coûteux et le plus risqué (DataDome déteste les séquences
  régulières). Si on l'ajoute, il faut : **étaler** (ne pas lancer les 3 en rafale — garder le
  jitter, un site à la fois avec pauses humaines), **plafonner** le nombre de pages, et surtout
  **prévoir l'arrêt propre sur CAPTCHA** (journaliser « bloqué » plutôt que boucler).
- Recommandation de rythme : **Leboncoin + Bien'ici(API) dans le même battement** ; **SeLoger, si
  retenu, un autre soir** (alterner) pour ne pas tripler le temps de navigation une même nuit.

---

## Lot 3 — Doublons

### La règle de rapprochement existe déjà

`_est_meme_bien()` (`html_ingest.py:114-151`) décide si une nouvelle annonce **est le même bien
physique** qu'un bien déjà connu, et les fusionne (`_absorber`, le plus ancien survit). Elle est
**déjà prévue pour l'inter-portails** et utilise, à commune identique :

1. **le type** (maison/appartement/terrain) — obligatoire des deux côtés ;
2. **la surface pertinente** (terrain pour un terrain, habitable sinon) ;
3. **le prix** ;
4. **le quartier** (`district`) et la nature de la position (`city` vs `address`).

Logique retenue (déjà durcie contre le sur-dédoublonnage) :
- **surface ET prix EXACTS → même bien**, où qu'il soit (signal le plus fort) ;
- sinon, **tolérance ±2 % surface / ±3 % prix** accordée **seulement si le quartier correspond** ;
- règle B : **même quartier + surface exacte** (le prix a pu bouger).

**Les photos ne sont PAS utilisées** par la règle actuelle.

### Combien de doublons sur un échantillon de 20 ?

**Je n'ai pas capturé ces 20 annonces** (lecture seule + interdiction de capture en masse). Je donne
donc une **estimation raisonnée**, à confirmer par une vraie mesure lors de la mise en œuvre :

- Les annonces SeLoger et Bien'ici sont **très majoritairement des annonces d'agence**, et les
  agences **diffusent le même bien sur tous les portails** (passerelles type Ubiflow) — Leboncoin
  compris. **Donc, parmi 20 annonces Bien'ici/SeLoger prises au hasard, une large majorité du
  volet « agence » est aussi présente sur Leboncoin.**
- **MAIS** « présent sur Leboncoin » ≠ « déjà dans le Radar » : le Radar ne couvre Leboncoin que
  partiellement (La Réunion, fenêtre du soir, et la pige était gelée depuis 06/10 — cf.
  [[radar-etat-1]]). **Le taux de doublon réellement observé dépend donc surtout du taux de
  remplissage actuel du Radar, pas seulement du recouvrement théorique entre sites.**
- Fourchette d'attente honnête : **recouvrement théorique élevé (ordre de 50–70 % pour le volet
  agence), mais taux de doublon *mesuré dans le Radar* probablement plus bas** tant que la pige
  Leboncoin n'est pas pleinement relancée. C'est **exactement la mesure à faire au démarrage** (Lot
  à rejouer sur 20 vraies annonces).

### Taux d'erreur de la règle et angle mort inter-portails

- **Faux positifs mesurés** sur la base actuelle : **3** (deux F2 ~53 m² à ~150 k€ dans des
  quartiers différents), d'où le durcissement « quartier obligatoire » hors valeurs exactes. Bon
  signe : la règle est déjà conservatrice.
- **Angle mort pour l'inter-portails** : la tolérance ±2 %/±3 % s'appuie sur **l'égalité textuelle
  du libellé de quartier** (`district`). **Or Leboncoin et SeLoger/Bien'ici n'écrivent pas les
  quartiers pareil** (« Saint-Gilles les Bains » vs « Saint-Paul » vs code postal). Résultat probable :
  - **le vrai levier inter-portails sera la paire « surface exacte + prix exact »** (qui ne dépend
    pas du quartier) — et elle marchera bien, les portails recopient les mêmes chiffres ;
  - **les cas « prix arrondi différemment » risquent de NE PAS fusionner** faute de quartier
    identique → **sous-dédoublonnage** (le même bien compté deux fois). C'est l'erreur dominante
    attendue, et elle est *préférable* au sur-dédoublonnage (on ne fabrique pas de faux « vendu »).
- **Recommandation d'amélioration (hors périmètre de cet audit, à décider plus tard)** : ajouter un
  rapprochement par **`reference` d'agence** (présente chez SeLoger/Bien'ici) et/ou par
  **empreinte de photo**, qui trancheraient les cas où quartier et prix divergent. **Ne rien coder
  ici** — simple piste.

---

## Recommandation par site et ordre

| Site | Verdict | Pourquoi |
|---|---|---|
| **Bien'ici** | ✅ **FAIRE — en premier** | JSON propre (parseur trivial), anti-robots le plus léger, **coordonnées qui débloquent le rattachement parcelle/DVF**, slug déjà déclaré. Coût : un mode « appel API » dans l'extension + une `aplatir` Bien'ici. |
| **SeLoger** | 🟡 **FAIRE PLUS TARD — sous réserve** | Capture quasi identique à Leboncoin (peu de travail côté extension), **mais DataDome** (risque de blocage/CAPTCHA en nocturne) et **fort recouvrement agence** avec Leboncoin + Bien'ici (valeur marginale faible). À tenter **après** Bien'ici, en mesurant d'abord le vrai taux de doublon et si la session réelle passe DataDome. |

**Ordre conseillé**

1. **Bien'ici** (mode API + traducteur) — meilleur rapport valeur/effort, et seul à apporter du
   neuf (le rattachement).
2. **Mesurer** : taux de doublon réel Bien'ici↔Leboncoin sur 20 vraies annonces, et vérifier que
   les coordonnées Bien'ici rattachent bien à la parcelle.
3. **SeLoger** seulement si (a) on veut vraiment plus de volume d'agence **et** (b) la navigation
   nocturne passe DataDome de façon stable. Sinon, **ne pas faire** : il n'ajoute presque que des
   doublons.

> **Rien n'a été élargi, aucun code écrit.** Les pistes « reference d'agence » et « empreinte
> photo » sont notées pour mémoire, à décider dans un mandat ultérieur.

---

## Annexe — références

### Fichiers de la chaîne existante
- Extension : `outils/radar-extension/manifest.json`, `background.js` (battement `:508-557`, passes `:313-417`)
- Capture serveur : `src/labuse/pige/api.py` (`POST /admin/radar/capture`)
- Parseur : `src/labuse/pige/html_next.py` (`analyser` `:359`, `aplatir` `:103-153` — **spécifique Leboncoin**)
- Ingestion + **dédoublonnage** : `src/labuse/pige/html_ingest.py` (`_est_meme_bien` `:114-151`, `bien_meme_physique` `:154`, `_absorber` `:172`)
- Modèle : `src/labuse/pige/tables.py` (`pige_biens`, `pige_annonces.portail`, `pige_faits`)
- **Slugs portails (déjà prêts)** : `src/labuse/pige/portails.py` (`seloger`, `bienici` `:16-19`)
- Cycle / DVF : `src/labuse/pige/cycle.py` (`matcher_dvf` `:68`)
- Rattachement : `src/labuse/pige/rattachement_html.py` (`rattacher` `:153`)

### Sources externes (consultées à distance, aucune capture en masse)
- Bien'ici — API `realEstateAds.json`, structure et plafond : [lobstr.io](https://www.lobstr.io/fr/blog/comment-scraper-bien-ici-avec-python-et-requests-en-2023-1), [scraping-bot.io](https://scraping-bot.io/scraper/bien-ici)
- SeLoger — Next.js `__NEXT_DATA__` / `initialData` + DataDome : [scrapfly.io](https://scrapfly.io/blog/posts/how-to-scrape-seloger-com-listing-real-estate-ads)
- DataDome (difficulté, scoring comportemental) : [scrapfly.io/bypass/datadome](https://scrapfly.io/bypass/datadome), [datadome.co](https://datadome.co/guides/scraping/scraper-crawler-bots-how-to-protect-your-website-against-intensive-scraping/)
- Volumes Réunion (974) : [SeLoger](https://www.seloger.com/recherche/achat/immobilier/la-reunion/la-reunion-974/ad06re1) (~2 980), [Logic-Immo](https://www.logic-immo.com/recherche-immo/vente/immobilier/la-reunion/la-reunion-974/ad06re1) (~2 750)
- Doublons inter-portails (agences diffusent partout) : [lesoutilsimmo.fr](https://www.lesoutilsimmo.fr/guides/portails-annonces-immobilieres-guide-2026), [en-contact.com](https://en-contact.com/bienici-seloger-leboncoin-dockinn-ia-et-portails-immobiliers)
