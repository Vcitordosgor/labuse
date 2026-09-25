# RADAR-AUDIT-1 — le chemin d'un dépôt de page, du fichier à la base

**Branche** `audit/radar-1` · worktree `~/Desktop/labuse-radar` · ports 8205/5405 · **lecture seule, rien corrigé.**
**Objet** : retracer tout le parcours d'un dépôt du soir — le fichier `docs/RADAR/Maison_a__vendre…page_2_-_leboncoin.html` que Vic enregistre chaque soir (Cmd+S « page web complète ») — depuis le point d'entrée jusqu'à ce qui est stocké, en passant par le parseur, la déduplication, les agents ; puis les trous ; puis ce qu'il faudrait pour automatiser la capture.

> ⚠️ **Le fichier `Maison…page_2_-_leboncoin.html` n'était pas présent dans le worktree au moment de l'audit** (`docs/RADAR/` était vide). L'audit trace donc le code qui **traiterait** ce fichier, vérifié ligne à ligne dans `src/labuse/pige/` et confirmé par les fixtures des tests (`tests/test_pige_html.py`, `tests/test_pige_depot2.py`). Le nom du fichier (« page 2 ») est lui-même un signal — voir §6.

---

## Résumé exécutif

Le dépôt HTML suit un chemin **100 % local, sans réseau ni IA** (doctrine §2) : `html_next` lit le bloc `__NEXT_DATA__` de la page, `html_ingest` insère/met à jour **par `list_id`**, `coherence` écarte les annonces qui se contredisent, `rattachement_html` tente de coller chaque bien à une parcelle par convergence de ≥2 critères. Ce noyau est **solide, honnête et idempotent** : re-déposer la même page ne duplique rien.

**Trois angles morts, tous documentés au §6 :**
1. **La déduplication ne connaît que `list_id`.** Deux portails (ou une re-publication avec un nouvel identifiant) pour le même bien physique → **deux biens**. Le dédoublonnage « jumeau » (prix±2 % ∧ surface±5 %) existe mais **uniquement sur l'ancien chemin capture-vision**, jamais sur le chemin HTML.
2. **Le cycle de vie est en sommeil.** Les jobs `radar-cycle` (en-vente-longue / à-revérifier / **expirées**), `radar-cycle-dvf` (vendue) et `radar-cycle-mensuel` (retirée-sans-vente = la cible Courrier) **ne sont pas planifiés** — CLI seulement. Une annonce retirée n'est donc **jamais détectée automatiquement**, et tout l'entonnoir aval (vendue, courrier) dort.
3. **Aucune conscience de la pagination.** Le parseur lit *la page qu'on lui donne*. « Page 2 » se dépose exactement comme « page 1 », mais rien ne sait qu'il existe une page 2, 3… ni ne signale « il manque des pages ». Ce que Vic n'enregistre pas n'entre jamais, en silence.

---

## 1. Le point d'entrée du dépôt, et ce qu'il accepte

**Front — `frontend/src/components/admin/Radar.tsx`** (composant `DepotHtml`, réservé à l'écran admin) :
- un sélecteur de fichier `<input type="file" accept=".html,.htm,text/html">` (`Radar.tsx:53`) ;
- au choix du fichier, `const html = await f.text()` (`Radar.tsx:38`) lit le fichier **côté navigateur** et poste `radarDeposerHtml(html, f.name)`. C'est le **texte** du fichier qui part, pas le fichier ; le nom (`f.name`) est joint pour la traçabilité.
- Le rendu affiche « *N annonces lues — X nouvelles, Y mises à jour, Z à qualifier* » (`Radar.tsx:63-69`) ou un message d'échec (`:57-62`).

**Endpoint — `POST /admin/radar/deposer-html`** (`src/labuse/pige/api.py:64`) :
- corps `DeposerHtmlIn { html: str, nom_fichier: str | None }` (`api.py:31`) ;
- **réservé admin** (`exiger_admin`, `api.py:69`) — comme toute la page Radar ;
- délègue à `html_ingest.ingester(db, body.html, body.nom_fichier)` (`api.py:74`).

**Ce qu'il accepte / rejette proprement** (jamais de 500 muet) :
| Cas | Retour |
|---|---|
| Page reconnue | `{ok: true, nb_annonces, nb_nouvelles, nb_maj, nb_a_qualifier, etats, provenance, mode, …}` |
| `__NEXT_DATA__` absent / structure changée / 0 annonce | `{ok: false, erreur: "next_data", motif}` (`api.py:75`, `NextDataError`) |
| Répertoire d'archivage non inscriptible | `{ok: false, erreur: "stockage", motif}` (`api.py:78`, `DepotStockageError` — nomme le chemin) |

**À noter :** il existe **deux autres points d'entrée** qui ne sont *pas* le dépôt du soir :
- `POST /admin/radar/deposer` (`api.py:50`) — l'**ancien** chemin par capture d'écran (image base64) → agent **vision IA** (`extraction.py`). Coûte un appel LLM ; crée un **brouillon** à valider à la main. Le chemin HTML l'a **remplacé** (`html_next.py:4`).
- `POST /admin/radar/depot-agence/analyser` (`api.py:740`) — le parcours « Publier une annonce » d'une agence : une **seule** annonce, collée en HTML **ou** via URL (`_fetch_page_oneshot`, une requête one-shot serveur, `api.py:674`). Derrière un drapeau fermé par défaut (question Hoguet en attente). Hors périmètre du dépôt du soir.

---

## 2. Le parseur — ce qu'il extrait, ce qu'il rate

Point d'entrée unique : **`html_next.analyser(html)`** (`src/labuse/pige/html_next.py:359`). Il lit le `<script id="__NEXT_DATA__">` par regex + `json.loads` (`html_next.py:48,69`) et **reconnaît trois structures**, dans cet ordre :

| Ordre | Structure Next.js | Mode | Provenance |
|---|---|---|---|
| 1 | `props.pageProps.searchData.ads` (page de résultats riche) | `resultats` | `json_riche` |
| 2 | `props.pageProps.ad` (page d'une annonce seule) | `annonce` | `json_riche` |
| 3 | Vignettes DOM `<article>…/ad/ventes_immobilieres/{id}` | `resultats` | `dom_degrade` |
| — | rien de reconnu | — | `NextDataError` **bruyante** nommant les trois chemins (`html_next.py:394`) |

**La page du soir de Vic est le cas 1** (résultats leboncoin riches). L'ordre compte : une page d'annonce porte aussi des vignettes « similaires » dans son DOM — la page d'annonce est testée **avant** les vignettes pour ne pas ingérer les similaires (`html_next.py:363`).

### Champs extraits par annonce (`aplatir`, `html_next.py:103`)
- **identité** : `list_id` (clé d'idempotence), `url`, `subject` (titre) ;
- **prix** : `price` (gère `price` en liste), `price_per_square_meter` ;
- **type** : `real_estate_type` mappé `1→maison, 2→appartement, 3→terrain` (`_RET`, `html_next.py:34`) ;
- **surfaces / pièces** : `square` (habitable), `land_plot_surface` (terrain), `rooms`, `bedrooms`, `nb_floors_house`/`is_single_storey` (étages) ;
- **bâti** : `building_year`, `global_condition`, `energy_rate`/`ges` (→ lettre A–G via `_classe`), `property_tax`, `heating_mode` ;
- **localisation** : `location.city`, `zipcode`, `district`, `lat`, `lng`, **`location.source`** (= `address` point rue, ou `city` = quartier flouté — `html_next.py:145`) ;
- **vendeur** : `owner.type` (`pro`/`private→particulier`), `owner.siren` ;
- **dates portail** : `first_publication_date` (**fait foi** pour la nouveauté), `index_date` (republication seulement), `expiration_date`, `status` ;
- **piscine** : booléen déduit du **mot « piscine » dans le titre** (le portail n'a pas d'attribut dédié — `html_next.py:122`) ;
- **`brut`** : sous-ensemble d'attributs conservé tel quel pour la traçabilité.

Une annonce **sans aucun attribut connu** (`_ATTRS`, `html_next.py:38`) lève `NextDataError` (« structure changée ») — garde-fou contre un changement silencieux de format leboncoin. **Une liste `ads` vide lève aussi** (`html_next.py:97`) : « un zéro silencieux trahirait un changement de structure, pas une vraie absence ».

### Page d'annonce seule (mode `annonce`, `html_next.py:339`)
En plus des champs ci-dessus, `extraire_faits_declares` (`html_next.py:313`) lit le **corps texte du vendeur** pour en tirer des **faits déclarés** : zone(s) PLU (regex `_ZONE_RE`), COS/CES, emprise au sol %, drapeaux (à rénover / à démolir / succession / lotissement + nom / viabilisé). **Le texte lui-même n'est jamais stocké** — seulement ces faits, étiquetés « déclaré dans l'annonce » (déclaratif vendeur, pas du calibré LABUSE).

### Variante B dégradée (vignettes DOM, `html_next.py:206`)
Quand leboncoin sert (par test A/B) une page sans `searchData`, les annonces ne vivent que dans le DOM. On en tire honnêtement peu : `list_id`, `url`, titre, prix, commune/CP/quartier (regex), badge « Pro », badge « Baisse de prix », piscine (mot du titre). **Ni position, ni dates de publication** → provenance `dom_degrade`, **jamais rattaché** (§4).

### Ce que le parseur **rate** (par conception ou limite)
- **Adresse exacte** : leboncoin ne la donne pas en résultats — seulement `lat`/`lng` (souvent `source=city` = **point de quartier flouté**) + `district`. Aucune rue.
- **`real_estate_type` hors 1/2/3** : tout autre code (dont **immeuble**, parking, autre) → `type = None` (conservé dans `brut`, **jamais deviné**). Un « immeuble » leboncoin ressort donc sans type → non rattachable (§4) et non soumis aux contrôles de type de la cohérence (§ ci-dessous).
- **Photos, description, nom du vendeur, téléphone** : jamais extraits sur le chemin collecté (seul le dépôt **agence** confie photos/description — `tables.py:251-252`).
- **Piscine / DPE réels** : la piscine n'est qu'un mot du titre (mesuré 0/38 dans le corpus) ; le DPE dépend d'`energy_rate` souvent « non soumis ».
- **La pagination** : `analyser` ne lit que le tableau `ads` de *cette* page ; le total de résultats et le numéro de page ne sont ni lus, ni exploités (§6).

---

## 3. La déduplication — sur quoi, et si l'on dépose deux fois

**Clé unique = `list_id`.** Index `uq_pige_annonces_list_id` (`tables.py:201`) + `uq_pige_annonces_url` sur `url_sortante` (`tables.py:122`).

Pour chaque annonce, `_ingester_annonce` (`html_ingest.py:148`) :
1. résout la commune (§5, hors 24 → `hors_perimetre`, **rien en base**) ;
2. cherche un `bien_id` existant **par `list_id`** (`html_ingest.py:158`) ;
3. **absent → « nouvelle »** : insère `pige_biens` + `pige_annonces` + `pige_faits`, joue cohérence + rattachement, journalise `pige.nouvelle` (ou `pige.a_qualifier`) ;
4. **présent → « maj »** : republication = **confirmation « toujours en vente »** — repousse `date_derniere_confirmation`, ramène `a_reverifier`/`en_vente_longue` à `active` (jamais `retiree`/`vendue`), historise une baisse de prix éventuelle (`_maj_prix`, `html_ingest.py:55`).

### Si Vic dépose deux fois la même page
- **Fichier identique** : archivé **content-addressed par hash SHA-256** (`_archiver`, `html_ingest.py:43`) → non re-dupliqué sur disque. Une **nouvelle ligne `pige_depots`** est écrite à chaque dépôt (traçabilité), mais chaque annonce retombe sur son `list_id` → **0 nouvelle, N mises à jour**, aucune donnée corrompue.
- **Événements** : `journaliser(... dedup=...)` (`tables.py:302`) porte des clés de dédup (`pige:nouvelle:{bien_id}`, `pige:baisse:{bien_id}:{prix}`, `pige:depot:{hash[:16]}`) → pas de doublon dans l'`event_log`.
- **Doublon sponsorisé dans la même page** : leboncoin répète parfois une annonce (sponsorisée + organique) — **même `list_id`** → la 2ᵉ occurrence est une « maj » (dédoublonnée). ✅

### Le trou de la dédup (voir aussi §6)
- **Aucun dédoublonnage « bien physique ».** Le twin-matching `_bien_jumeau` (commune ∧ prix±2 % ∧ surface±5 %, `intake.py:41`) n'est branché que sur l'**ancien chemin capture-vision** (`intake.deposer:122`). `html_ingest` **ne l'appelle jamais**. Conséquence : la même maison sur leboncoin **et** SeLoger (deux `list_id`), ou re-publiée avec un nouvel identifiant, = **deux biens distincts**. C'est un choix (idempotence par `list_id`), mais il fait que le compteur de biens et les stats **surcomptent** les biens multi-portails.

---

## 4. Les agents qui tournent après — et ce que ça coûte

### À l'ingestion (synchrone, dans la transaction du dépôt)
- **`coherence.evaluer`** (`coherence.py:43`) — une annonce dont les champs se contredisent part en **`a_qualifier`** (hors stats **et** hors veilles) :
  - *structurel* : un « terrain » qui porte pièces / année / surface habitable / chauffage ; un bâti dont `surface_hab == surface_terrain` ;
  - *référentiel* : prix/m² d'un « terrain » > 4× (ou < ¼×) la médiane du terrain nu de la commune (`marche_commune`, jamais un chiffre inventé). **Coût** : quelques requêtes SQL, aucun réseau.
- **`rattachement_html.rattacher`** (`rattachement_html.py:145`) — colle le bien à une parcelle par **convergence de ≥2 critères indépendants** :
  - univers **positionnel** dans un rayon de **150 m** autour du point (flouté) : `C1` surface cadastrale ≈ terrain annoncé (±10 %), `C2` emprise bâtie BD TOPO plausible (borne basse = élimine la parcelle vide) ;
  - **corroborants** (ne créent jamais de candidate) : `C3` DVF à l'envers, `C5` DPE ADEME, `C6` piscine ortho ;
  - **RATTACHÉE** ssi **une seule** parcelle porte ≥2 critères (confiance 0,75→0,95) ; sinon **PISTE** ; sinon **NON RATTACHÉE**. **Jamais d'`idu` automatique** ambigu. Un bien **dégradé** (variante B, sans position) ou **`a_qualifier`** n'est **jamais** rattaché (`html_ingest.py:135`).
  - **Géolocalisation** : il n'y a **pas d'appel de géocodage** — la position vient directement du JSON leboncoin (`location.lat/lng`). (L'ancien chemin vision géocode via BAN *seulement* si une adresse figure dans `source_brute`, ce qui n'arrive pas aujourd'hui — `intake.py:257`.) **Coût** : plusieurs requêtes PostGIS `ST_DWithin` par bien rattachable, aucune IA, aucun réseau.

### Après l'ingestion (jobs)
- **`radar-cloche`** — planifié **quotidien 07:05** (`jobs.py:379` → `jobs_impl.radar_cloche` → `digests.evaluer_radar_cloche`, `digests.py:292`) : pose à la **cloche** de chaque client les annonces du jour qui matchent une de ses veilles (`veille.matche`, `veille.py:75`). **Aucun mail ici.**
- **Digest du matin** — planifié **07:15** (`jobs.py:405` → `api.events.envoyer_digests`) : e-maile en **un** message par compte tout ce qui a bougé (parcelles suivies + Radar + nouveautés), via **Brevo / `mail_queue`**, idempotent par jour, jamais vide. **Coût** : un e-mail transactionnel Brevo par compte concerné par jour. *(Le sender dédié `digests.envoyer`/template `radar_alerte`, `digests.py:317`, est aujourd'hui **CLI seulement** — `radar-digests`, `cli.py:3738` — le canal servi étant cloche + digest du matin.)*

### Les critères de veille
Créés par le client via `POST /radar/veille` (`api.py:567`), stockés dans `veilles.criteria` (jsonb) : commune(s), type, prix min/max, surfaces min, particulier only. `veille.matche` (`veille.py:75`) est un **constat strict** : un critère absent n'exclut pas ; un critère présent doit être satisfait. Les biens **`a_qualifier`** et les **copros** (`est_copro`) sont exclus de la liste évaluée (`digests.py:61-84`).

### Le coût, en une phrase
**Le dépôt HTML lui-même ne coûte rien** (aucun LLM, aucun réseau — doctrine §2). Les seuls coûts du domaine Radar sont : (a) l'e-mail Brevo du digest ; (b) la vignette ortho IGN WMS servie à l'écran d'instruction admin (`/admin/radar/ortho/{idu}`, cache 24 h, `api.py:480`) ; (c) l'ancien chemin **vision** (un appel LLM par capture, `extraction.py:98`) et le **fetch one-shot** du dépôt agence par URL — deux chemins hors dépôt du soir.

---

## 5. Ce qui est stocké (tables, colonnes) — et ce qui est jeté

Schéma **isolé `pige_*`** (`src/labuse/pige/tables.py`), zéro écriture hors `pige_*`.

| Table | Rôle | Colonnes clés |
|---|---|---|
| `pige_biens` | le **bien physique** (dédoublonné par `list_id`) | `commune`, `type_bien`, `est_copro`, `idu`, `rattachement_niveau/confiance/etat/pistes/criteres/humain`, `statut`, `a_qualifier`+`_motifs`, `lat/lng`, `source_position`, `zipcode`, `district`, dates cycle (`date_publication`, `date_premiere_saisie`, `date_derniere_confirmation`, `retiree_le`, `vendue_*`) |
| `pige_annonces` | l'**occurrence portail** (2 portails → 2 lignes, même bien) | `portail`, `url_sortante` (unique), **`list_id`** (unique), `first_publication_date`, `index_date`, `expiration_date`, `statut_portail`, `date_saisie` |
| `pige_faits` | les **faits validés** | prix, type, pièces, surfaces, DPE/GES, `particulier_pro`, `annee_construction`, `etat_bien`, `taxe_fonciere`, `prix_m2`, `chauffage`, `owner_siren`, **`etiquettes`** (Sourcé/Estimé/Absent par champ), **`provenance`** (`json_riche`/`dom_degrade`), **`declaratif`** (zone PLU…), **`source_brute`** (payload aplati intégral), `valide_at` |
| `pige_prix_historique` | une ligne par **changement de prix** | `ancien_prix`, `nouveau_prix`, `date_constat` |
| `pige_depots` | **un dépôt = une ligne** | `nom_fichier`, `hash`, `chemin_archive`, `nb_annonces/nouvelles/maj/a_qualifier`, `date_depot` |
| `pige_captures` | métadonnées des captures (chemin vision) | `chemin_prive`, `hash` |
| `pige_clics` | chaque clic sortant client | `compte_id`, `bien_id`, `portail` |
| `pige_interets_agence`, `radar_releves` | dépôt agence ; relevé quotidien des compteurs cumulés | — |

**Particularité du chemin HTML** : `_ecrire_faits` insère avec **`valide_at = now()`** (`html_ingest.py:99`) → les faits sont **servis immédiatement**, sans étape « Valider » manuelle (contrairement au chemin vision qui crée un brouillon `valide_at NULL`). La colonne IA « à vérifier » reste `NULL` pour le HTML (donnée structurée, aucun champ incertain — `html_ingest.py:67`).

**Ce qui est jeté / jamais stocké :**
- le **texte libre de l'annonce** (corps vendeur) — seuls des *faits* en sont extraits (`html_next.py:280`) ;
- **photos, description, titre** sur le chemin collecté (seul le dépôt agence les confie) ;
- les annonces **hors des 24 communes** → `hors_perimetre`, rien n'entre (`html_ingest.py:152`) ;
- les **copropriétés** (`est_copro`) sont embasées mais **jamais servies** (absentes carte / digests / veilles) ;
- le HTML brut **est** archivé sur disque (privé, jamais servi par le web) — mais son texte n'entre jamais en colonne.
- **Rien conserve la « provenance de page »** : le bien ne sait pas de quelle page (1, 2…) ni de quelle recherche il vient. `pige_depots` garde le fichier, pas le lien annonce↔dépôt.

---

## 6. Les trous

### a) Annonces sans adresse / sans position
Un bien sans `lat/lng` (ou en variante B dégradée) est **stocké** (commune seule) mais **jamais rattaché** — servi avec la pastille « Non rattaché à une parcelle » (`digests.py:136`). Quand `source_position = city`, la position est un **point de quartier flouté** ; le rattachement tente quand même dans un rayon de 150 m, ce qui peut ne rien trouver ou (rarement) désigner la mauvaise parcelle — d'où l'exigence de **≥2 critères** comme garde-fou. Pas de perte silencieuse, mais pas de rattachement non plus.

### b) Doublons sponsorisés
- **Dans une même page** : même `list_id` → dédoublonné (« maj »). ✅
- **Entre portails ou re-publication** : `list_id` différent → **doublon de bien** (pas de twin-dedup sur le chemin HTML, §3). Le compteur « biens » et les stats **surcomptent**.

### c) Annonces retirées jamais détectées — **le trou le plus profond**
Trois mécanismes de retrait existent dans `cycle.py`, mais leur **planification a été retirée** :
- `marquer_expirees` (`cycle.py:123`) : passe `retiree` sur `expiration_date` portail dépassée — vit dans `run_quotidien` ;
- `matcher_dvf` (`cycle.py:64`) : passe `vendue` (rattachement Sourcé + mutation DVF [3;18] mois) — `run_dvf` ;
- `qualifier_retiree_sans_vente` (`cycle.py:103`) : la **cible Courrier** — `run_mensuel`.

Or **seul `radar-cloche` est planifié** (`jobs.py:379`). Le commentaire du registre est explicite : *« Radar : PAS de job […] radar-cycle, radar-releves : retirés »* (`jobs.py:429`). Les commandes `radar-cycle-quotidien` / `-dvf` / `-mensuel` (`cli.py:3708,3718,3728`) et la fonction `jobs_impl.radar_cycle` (`jobs_impl.py:159`) existent mais **ne tournent que si Vic les lance à la main**. Conséquences :
- une annonce **expirée côté portail** n'est marquée `retiree` que si `run_quotidien` est lancé → sinon elle reste `active` indéfiniment ;
- **une annonce qui disparaît des dépôts** (retirée sans `expiration_date`) n'est **jamais** détectée : il n'existe **aucune réconciliation** « vue la dernière fois, absente aujourd'hui ». Le retrait ne se constate que par l'`expiration_date` ou par le clic humain « retirée » (`api.py:190`) ;
- toute la chaîne **vendue → retirée-sans-vente → Courrier** est **dormante**.

### d) Pages 2+ jamais déposées
Le parseur lit **la page qu'on lui donne**, sans conscience de pagination. « Page 2 » se dépose exactement comme « page 1 ». Mais :
- **rien ne sait** qu'une recherche a N pages, ni combien d'annonces sont attendues (le total/numéro de page du `searchData` n'est pas lu) ;
- **rien ne signale** « il manque des pages » ;
- si Vic n'enregistre que la page 1, les annonces des pages suivantes **n'entrent jamais**, **en silence** — c'est exactement le risque que le nom du fichier (`…page_2…`) met en lumière : chaque page est un dépôt indépendant, et la complétude repose entièrement sur la discipline humaine.

### e) Trous mineurs
- **`immeuble`** (et tout `real_estate_type` hors 1/2/3) → `type = None` → non rattachable et non contrôlé en cohérence.
- **Re-publication avec nouveau `list_id`** = nouveau bien (perte du lien avec l'ancien).
- **`a_qualifier`** exclut des stats/veilles mais le bien reste stocké (pas un trou, un choix — signalé pour mémoire).

---

## 7. Ce qu'il faudrait pour **automatiser la capture sans rien casser**

**Contrainte cardinale (doctrine §2, `portails.py:8`)** : aucun code ne doit requêter/scraper un portail côté serveur — c'est la ligne rouge légale (Hoguet / CGU portail, question chez l'avocat de Vic). Toute automatisation doit donc **produire le même `.html` que l'endpoint accepte déjà**, sans changer le contrat d'entrée. Les pistes ci-dessous respectent cette ligne et sont classées par **risque croissant** :

1. **Réveiller les jobs de cycle (risque nul, gain immédiat).** Ré-inscrire au registre `radar-cycle` (quotidien), `radar-cycle-dvf` (après l'ingestion DVF) et `radar-cycle-mensuel`, avec le wrapper `run-job.sh` + flock comme les autres. Les fonctions **existent, sont idempotentes** (`cycle.py`) et **ne fetchent rien**. À elle seule, cette mesure ferme le trou « expirées » (§6c via `expiration_date`) et rallume l'entonnoir vendue/Courrier.

2. **Détecter le délistage par réconciliation (risque faible).** Ajouter au bien une notion de « vu au dépôt n° » ; sur chaque dépôt, un bien de la commune couverte **absent de la page depuis K dépôts consécutifs** → **signal** « peut-être retirée » (jamais un `retiree` automatique — une page filtrée n'est pas une preuve d'absence). Purement local, sur des données déjà en base.

3. **Signaler les pages manquantes (risque faible, si le JSON le porte).** Si `searchData` expose le **total de résultats / la pagination**, comparer « X annonces attendues vs Y déposées » et afficher « page 2 manquante » sur l'écran admin. Aucune collecte — juste une lecture de plus du même `__NEXT_DATA__`.

4. **Automatiser la capture côté humain, pas côté serveur (risque moyen, la vraie automatisation).** Un outil qui tourne **sur la machine de Vic, dans sa propre session** (bookmarklet, ou Playwright piloté localement par lui) et qui parcourt les pages 1…N d'une recherche enregistrée, enregistre chaque page en `.html` et les **dépose via l'endpoint existant**. Cela reste de la **collecte humaine** (sa machine, sa session, son geste) — le serveur ne touche jamais le portail. Variante minimale sans navigateur : accepter un **dossier de `.html`** et boucler les dépôts (l'endpoint est déjà idempotent, donc rejouable sans risque).

5. **Dédup « bien physique » en douceur (risque moyen).** Rebrancher `_bien_jumeau` sur le chemin HTML **en proposition** (`fusion_proposee`), jamais en fusion automatique, pour cesser de surcompter le même bien sur deux portails (§3, §6b). À traiter comme une suggestion d'instruction admin, pas un merge silencieux.

**Garde-fous à préserver quoi qu'il arrive** : l'archivage content-addressed + l'idempotence par `list_id` (ne rien casser du rejouable) ; l'échec **bruyant** du parseur (jamais un « 0 annonce » silencieux) ; et surtout — **le jour où quelque chose fetche un portail côté serveur, on a franchi la ligne.** Automatiser *la capture* doit rester un outil humain/local qui alimente le même tuyau ; le tuyau, lui, ne change pas.

---

*Fin — RADAR-AUDIT-1. Lecture seule, aucun fichier de code modifié.*
