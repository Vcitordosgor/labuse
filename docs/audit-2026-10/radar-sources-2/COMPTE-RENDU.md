# RADAR-SOURCES-2 — Bien'ici au Radar (capture par l'extension, traducteur serveur)

**Branche** `feat/radar-sources-2` · worktree `~/Desktop/labuse-bienici` · ports 8980/6180 · 29/10/2026
**Aucun merge, aucun accès prod, aucune écriture en base servie.** Pas touché à `pige/api.py`, `exports/`,
ni à la fiche (deux autres sessions tournent). Suit l'audit [RADAR-SOURCES-1](../radar-sources-1/RAPPORT.md)
(verdict « Bien'ici d'abord »).

---

## En une phrase

> **Bien'ici est capturé comme Leboncoin, par l'extension, dans le navigateur de Vic** : l'extension fait
> un `fetch()` même-origine de `realEstateAds.json` et poste le JSON au serveur, qui le traduit dans le
> schéma LABUSE. **Le nerf débranché se rebranche : là où Leboncoin ne donne qu'un centroïde de commune
> (0 parcelle candidate), Bien'ici donne une position floutée à 50 m → 74 % des biens rattachables
> décrochent au moins une parcelle candidate** (47/66 atteignent une parcelle à ≥2 critères). Le
> rattachement AUTOMATIQUE reste rare (1/66) car le rayon de recherche partagé (150 m, calibré pour
> Leboncoin) est 3× le floutage Bien'ici et ramène ~12 candidates en zone dense → **l'écran d'instruction
> admin devient utilisable, l'auto-rattachement ≥2-critères-unique reste l'exception** (doctrine V2).

---

## Ce qui a été construit

### 1. Traducteur serveur (`src/labuse/pige/html_next.py`)
- **Dispatch** : `analyser()` reconnaît AVANT tout un dépôt JSON (clé `realEstateAds`) et route vers
  `aplatir_json_ads` ; sinon, chemin Next.js Leboncoin **inchangé** (une page Leboncoin commence par `<`,
  un payload Bien'ici par `{` → détection sûre, zéro régression Leboncoin).
- **`aplatir_json_ads(ad)`** alimente le **même schéma plat** que le traducteur Leboncoin. Une donnée
  absente reste absente (jamais devinée). Mapping mesuré sur la fixture réelle :
  - prix, prix/m², surfaces (hab + terrain), pièces, chambres, type, commune, zipcode, quartier, **lat/lng**,
    dates (`publicationDate`/`modificationDate`), année, DPE/GES, agence/particulier, piscine, baisse de prix.
  - **commune résolue par l'INSEE du quartier** (`district.code_insee` → `communes.nom_officiel`) : le champ
    `city` est souvent une LOCALITÉ (« Saint-Gilles les Bains ») hors des 24 communes → sans ça, 100 %
    hors-périmètre. Avec ça : **100/100 dans le périmètre**.
  - DPE `NS`/`VI` (non soumis / vierge) → `None` (seule une lettre A–G passe) ; pas de `global_condition`,
    taxe, chauffage, SIREN, nb d'étages chez Bien'ici → restent `None`.
  - `hasPool` → piscine (booléen dédié, jamais lu dans le titre) ; `priceHasDecreased` → badge baisse daté.
- **list_id** : les id Bien'ici sont des CHAÎNES (« immo-facile-61412190 ») ; la colonne `list_id` est un
  `bigint`. On en dérive un entier **stable** (hachage 56 bits, idempotence) avec le **bit 62 forcé** →
  l'espace Bien'ici (> 4,6·10¹⁸) **ne croise jamais** les list_id Leboncoin (< ~10¹⁰) : aucune fausse
  collision « même annonce ». La chaîne réelle vit dans l'URL sortante (index unique) et dans `brut`.
- **Doctrine §2** : le nom du portail ne vit **qu'en commentaire** et dans le module d'affichage
  `portails.py` (helper `lien_annonce_jsonads` qui bâtit l'URL sortante sur le préfixe officiel). Le code
  du traducteur est **neutre** (`json_ads`) → il **passe la garde `test_pige_socle`** (cf. § réserves).

### 2. Extension (`outils/radar-extension/`)
- `manifest.json` : `*://*.bienici.com/*` ajouté aux sites couverts.
- `background.js` : **mode API** (pas de lecture de page — Bien'ici est une SPA). L'extension ouvre un
  onglet bienici.com (session chaude), puis `fetch()` **même-origine** de `realEstateAds.json` page par
  page (zone « La Réunion » = `-77601`, `filterType=buy`, **à CONFIRMER par Vic**) et poste chaque corps
  JSON à `/admin/radar/capture` — **même route, même tuyau que Leboncoin**. Les **trois passes** :
  - *nouvelles* / *relecture* : appels API paginés, rythme humain (jitter), plafonds durs, arrêt net sur
    blocage/429 ;
  - *confirmation* : re-`fetch()` de l'annonce seule (`realEstateAd.json?id=`) — **404 = preuve positive de
    disparition**, `onTheMarket:false` = expirée, sinon présente. Mêmes règles qu'après RADAR-FIX-3
    (**aucun retrait sans preuve positive, garde-fou 30 %** côté serveur, inchangé).
  - Leboncoin et Bien'ici tournent dans le **même battement** ; la confirmation route chaque lien à son
    portail (par hôte) — un lien d'un autre portail n'est jamais classé à tort.
- `options.html/js` : champ « URL de recherche Bien'ici » (vide = portail désactivé).

---

## Recette (capture réelle, lecture seule sur la base servie `labuse`)

**Fixture** `qa/radar-bienici/ECH-BIENICI-1.json` — **capture réelle** d'une page de résultats « ventes,
toute La Réunion » via le navigateur (exactement le `fetch()` qu'exécutera l'extension), **100 annonces**
(`total` annoncé par Bien'ici : **4 293** ventes). Champs lourds/PII que le parseur ne lit pas retirés
(photos, visites, téléphones, données compte), description tronquée — **tous les champs mappés intacts**.

### Lecture et champs
| | valeur |
|---|---|
| Annonces lues | **100/100** |
| Dans le périmètre (24 communes) | **100/100** (0 hors-périmètre — grâce à la résolution INSEE) |
| prix / prix_m2 / pièces / type / commune / zipcode / quartier / **lat+lng** / owner | **100/100** |
| surface terrain | 50/100 (seulement les maisons avec terrain) · chambres 97 · année 71 · DPE 0 (tout `NS`/`VI`) |
| types | 66 maisons, 34 appartements · baisse de prix 11 · piscine 25 · pro 100 |

### Rattachement — le résultat le plus important du mandat
Cascade `rattachement_html.rattacher` appelée (SELECT seulement) contre les **434 582 parcelles** :

| état | n (sur 100) |
|---|---|
| rattachée (auto, ≥2 critères **uniques**) | **1** |
| piste (candidates trouvées, à instruire) | **48** |
| non rattachée | 51 (dont **34 appartements** non rattachables par nature) |

**Assiette rattachable = 66** (maisons/terrains/immeubles). Sur elle :
- **49/66 (74 %) décrochent au moins une parcelle candidate** — contre **~0 avec Leboncoin** (centroïde de
  commune ⇒ rien dans le rayon). **C'est le déblocage attendu de l'audit.**
- **47/66 atteignent une parcelle à ≥2 critères convergents**, mais **46 sont AMBIGUËS** (plusieurs
  parcelles à ≥2 critères dans le rayon) → PISTE ; **1 seule est unique** → rattachée automatiquement.
- Cause de l'ambiguïté, mesurée : le floutage Bien'ici est un **disque de 50 m** (90 % des annonces ;
  quelques-unes à 125 m, de rares à 500 m), mais le rayon de recherche `RAYON_M` est **150 m** (calibré
  pour la position imprécise de Leboncoin) → en zone dense il ramène **~12 candidates** (le plafond
  `MAX_PISTES`), dont plusieurs plausibles. La doctrine RATTACHEMENT-V2 (≥2 critères **sur une seule**
  parcelle) refuse alors de trancher seule — **c'est voulu** (jamais un pin faussement sûr).

**Lecture honnête** : les coordonnées Bien'ici **font converger la chaîne vers des candidates** (74 %) et
rendent **l'écran d'instruction admin enfin utile** (pistes classées par nb de critères + distance, là où
Leboncoin n'offrait rien). L'auto-rattachement reste rare par conception. **Piste d'amélioration (hors
périmètre, à décider)** : un rayon de recherche **resserré pour les sources à position-adresse** (≈ le
floutage, 50–60 m au lieu de 150) ferait tomber les candidates et sortirait beaucoup des 46 ambiguës en
rattachement unique — mais `RAYON_M` est **partagé avec Leboncoin** ; ne rien changer ici sans un mandat
dédié (mesure Leboncoin à refaire).

### Dédoublonnage inter-portails
`html_ingest.bien_meme_physique` (`_est_meme_bien`, portail-agnostique) appelé (SELECT seulement) contre
les **416 biens déjà en base (tous Leboncoin, 428 annonces)** :
- **4/100 annonces Bien'ici fusionnent** avec un bien Leboncoin existant (surface + prix EXACTS, le signal
  le plus fort — robuste au quartier écrit différemment entre portails, cf. angle mort de l'audit).
- Taux modeste **attendu** : la pige Leboncoin n'a que 416 biens en base (fenêtre partielle, gel 06/10) →
  le recouvrement théorique agence (50–70 %) ne peut se matérialiser que sur ce que le Radar contient
  déjà. Le levier « surface+prix exacts » fonctionne ; le sous-dédoublonnage sur quartier divergent reste
  l'erreur dominante *préférable* (jamais un faux « vendu »). Prouvé aussi en test unitaire (fusion d'une
  annonce Bien'ici avec un bien Leboncoin jumeau posé à la main → 1 bien, 2 occurrences portail).

### Tests
- **`tests/test_pige_bienici.py` — 18/18 verts** : 16 de parsing pur (schéma, types, commune via INSEE,
  coordonnées, list_id stable+disjoint, DPE `NS`/`VI`→None, absence restée absente, URL classée `bienici`,
  échec bruyant 0 annonce, dispatch qui ne confond pas Leboncoin) + 2 base jetable (idempotence 100 ads /
  2ᵉ dépôt 0 nouvelle ; **fusion inter-portails**).
- **Extension, hors navigateur** : `recette_bienici.mjs` **11/11** (routage par portail, id depuis l'URL,
  confirmation sur **preuve positive uniquement**) ; régression Leboncoin `recette_confirmation.mjs`
  **7/7** inchangée.
- **Hook git pré-commit (garde >2 Mio, MENAGE-1) : vert** — la fixture fait 286 Kio.

---

## Réserves honnêtes (pré-existantes, PAS introduites par ce mandat)
- `tests/test_pige_socle.py::test_aucune_requete_portail_dans_le_depot` est **ROUGE sur le HEAD de la
  branche AVANT ce mandat** (prouvé : édits Bien'ici remisés → toujours rouge) : 3 lignes d'**affichage**
  (`exports/builder.py:847`, `api/documents.py:272/275`, « Annonce Leboncoin… ») ajoutées par ANNONCE-2/3
  et jamais allowlistées. Ces fichiers sont **hors périmètre** (exports/, fiche). **Mon traducteur
  Bien'ici passe la garde proprement** (nommage neutre). À allowlister par la session ANNONCE.
- `tests/test_pige_depot2.py::test_d5_copros_embasees_mais_non_servies` **ROUGE sur HEAD** aussi
  (indépendant de Bien'ici — prouvé édits remisés).

---

## Gestes de Vic (pas faits ici — ni merge ni pose)
1. **Confirmer la recherche Bien'ici** « ventes, toute La Réunion » (zone `-77601`, `filterType=buy`) et la
   coller dans les Options de l'extension (URL de recherche Bien'ici).
2. **Poser/mettre à jour l'extension** dans son navigateur (le `manifest` couvre désormais bienici.com).
3. **Merger** `feat/radar-sources-2` quand décidé.

## Pour rejouer la recette
```
# tests unitaires (base jetable)
PYTHONPATH=src LABUSE_TEST_DATABASE_URL=postgresql+psycopg://openclaw@/labuse_test \
  ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_pige_bienici.py -q
# recette rattachement + fusions (LECTURE SEULE sur la base servie)
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@/labuse PYTHONPATH=src \
  ~/Desktop/labuse/.venv/bin/python qa/radar-bienici/recette_bienici.py
# recettes extension (hors navigateur)
node outils/radar-extension/recette_bienici.mjs && node outils/radar-extension/recette_confirmation.mjs
```

## Fichiers
- Traducteur : `src/labuse/pige/html_next.py` (dispatch + `aplatir_json_ads`/`extraire_json_ads`) ·
  URL sortante : `src/labuse/pige/portails.py` (`lien_annonce_jsonads`).
- Extension : `outils/radar-extension/{manifest.json,background.js,options.html,options.js,recette_bienici.mjs}`.
- Fixture : `qa/radar-bienici/ECH-BIENICI-1.json` · Recette : `qa/radar-bienici/recette_bienici.py`.
- Tests : `tests/test_pige_bienici.py`.
