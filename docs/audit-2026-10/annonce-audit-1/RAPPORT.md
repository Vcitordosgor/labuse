# ANNONCE-AUDIT-1 — « Analyser une annonce » : ce qu'on a déjà

**Branche** `audit/annonce-audit-1` · worktree `~/Desktop/labuse-annonceaudit` · ports 8910/6110
**Nature** audit LECTURE SEULE. Aucun correctif, aucun merge, rien de servi touché.
**Date** 2026-10-28 · **Modèle** Opus

---

## Objet et méthode

On étudie un futur outil **« Analyser une annonce »** (type *repere-immo.fr*, mais angle **foncier** LABUSE : coller une URL d'annonce → prix vs DVF → parcelle → PLU / résiduel / Score). La récupération serveur des annonces est **écartée** (déjà testée, bloquée) ; la capture passe par l'**extension Radar**. Cet audit **mesure ce qu'on a déjà**, il ne construit rien.

**Méthode.** Lecture du code de l'extension (`outils/radar-extension/`) et de la chaîne serveur `src/labuse/pige/` ; mesures empiriques sur la base pige réellement alimentée.

**⚠ Quelle « base de prod ».** D'après l'audit [[radar-etat-1]] du même jour, **la prod VPS ne reçoit plus de capture Radar depuis le 06/10** (l'extension pointait `localhost:8205` → elle nourrissait la base Mac, pas la prod ; le correctif RADAR-FIX-2 qui bascule vers `https://app.labuse.immo` n'est **ni mergé ni déployé**). La **seule base pige réellement peuplée est donc la base Mac** (`postgresql:///labuse`). Toutes les mesures ci-dessous portent sur cette base (**428 annonces, 416 biens, 100 % Leboncoin**). Un comptage **live sur la prod VPS** demanderait un accès prod explicite (tentative refusée ici par la garde « Production Read » — voir Décision 3). Vu l'état documenté, la prod est au mieux gelée au 06/10 ; la base Mac est le reflet fidèle de ce que produit la chaîne.

---

## Lot A — Extension Radar : quels champs, quelle fiabilité

### Ce qui existe

**L'extension n'extrait quasiment rien elle-même.** Le service worker (`background.js`) ouvre un onglet sur une **page de RÉSULTATS de recherche** Leboncoin, lit le DOM vivant via `inspectPage()` et **POST le `outerHTML` entier** à `/admin/radar/capture`. Côté client elle ne calcule que : présence d'une page suivante, dates d'annonces (`index_date`), détection de blocage DataDome/captcha (`background.js:178-229`). **Toute l'extraction de champs est serveur**, à partir du HTML capturé — plus précisément du bloc JSON `__NEXT_DATA__` embarqué dans la page (`src/labuse/pige/html_next.py`).

**Champs extraits (serveur), et leur source :**

| Champ | Source | Fiabilité mesurée (n=416 biens) |
|---|---|---|
| prix | `ads[].price` (+ repli regex `Prix: … €`) | **100 %** (416/416) |
| type de bien | `attributes.real_estate_type` {1 maison, 2 appart, 3 terrain} | **98,6 %** (410) |
| surface habitable | `attributes.square` (+ regex titre) | **92,8 %** (386) |
| nombre de pièces | `attributes.rooms` (+ regex titre) | **83,7 %** (348) |
| prix/m² | `attributes.price_per_square_meter` | 82,2 % (342) |
| surface terrain | `attributes.land_plot_surface` | 51,9 % (216) |
| année construction | `attributes.building_year` | 37,0 % (154) |
| **DPE / GES** | `attributes.energy_rate` / `ges` | **2,9 %** (12) ⚠ |
| commune / CP / quartier | `location.city` / `zipcode` / `district` | bon (type 98 %) |
| lat / lng | `location.lat` / `lng` | 82,7 % (344) — **mais voir Lot C** |
| vendeur pro/particulier | `owner.type` (+ badge DOM) | présent |
| chambres, étage, chauffage, état, taxe f. | `attributes.*` | rare à jamais |

**Provenance des captures** (n=416) : `json_riche` 315, `dom_degrade` 72 (page A/B sans `__NEXT_DATA__` → sous-ensemble titre+vignette seulement), 29 sans provenance. Doctrine « échec bruyant » : un type de bien au code inconnu ou une annonce sans aucun attribut connu lève une erreur plutôt que d'inventer (`html_next.py:109-110`).

**Le code sait DÉJÀ lire une page d'annonce unique.** Le dispatcher gère trois formes (`html_next.py:359-397`) : résultats riches (`searchData.ads[]`), **page de détail (`pageProps.ad`)**, résultats dégradés (DOM). La page de détail passe par le **même** `aplatir()` et, en bonus, parse `ad.body` → **faits déclarés** (zone PLU, COS/CES, emprise, drapeaux rénover/démolir/succession/lotissement/viabilisé) stockés dans `pige_faits.declaratif` (`html_next.py:313-354`, `html_ingest.py:353`). Un **fetch one-shot** d'une URL existe même déjà (`api.py:962-976` : UA Chrome, `Accept-Language: fr-FR`, timeout 8 s, **sans retry** sur 401/403/429/DataDome).

### Ce qui manque

- **Les champs qui font un outil « annonce » riche ne sont PAS dans la capture liste.** Sur une page de résultats, Leboncoin ne livre ni **DPE** (2,9 %), ni **photos**, ni **texte/description**. Mesure : `photos` et `description` sont **à 0** sur les 416 biens (ces colonnes ne se remplissent qu'au dépôt agence / page détail). Or un outil *repere-immo*-like s'appuie justement sur description + photos + DPE.
- **Pas de parcours « une URL → une analyse ».** La chaîne est bâtie pour une **passe de liste** (nouvelles / relecture / confirmation, plafonds 15/20/40 pages, rythme humain). Le chemin « détail » existe en lecture mais n'est pas exposé en entrée d'outil, et le `_fetch_page_oneshot` n'a pas de garde anti-blocage (le même DataDome qui a fait écarter la récup serveur s'applique).
- **SeLoger / Bien'ici — constat (0 ligne de code).** Le principe actuel = « lire le JSON d'hydratation de la page ». Il est **transposable seulement si** ces portails embarquent un état JSON analogue. Constat de structure (à confirmer sur une vraie page — Décision 2) : **SeLoger** sert historiquement les données d'annonce via un état JSON embarqué / `initialState` dans la page ; **Bien'ici** hydrate plutôt via une **API JSON client** (XHR) que via un bloc statique, donc une capture `outerHTML` pourrait ne pas suffire sans rejouer l'appel API. Les deux sont, comme Leboncoin, protégés anti-bot. **Aucune n'est câblée aujourd'hui** : `portails.py` et la chaîne ne connaissent que Leboncoin (428/428 des captures). Les ajouter = un parseur par portail + validation anti-blocage, pas une bascule de config.

---

## Lot B — Prix demandé vs DVF

### Ce qui existe

Deux comparaisons coexistent (`src/labuse/pige/signaux.py`, `marche.py`) :

1. **Par commune (ce qui tourne réellement).** Médiane des prix **affichés** du Radar vs médiane **DVF acté** du même type, à l'échelle **commune entière** (`marche.py:199-215`, `signaux._dvf_bati`). Seuils : `SEUIL_N = 5` ventes DVF et 5 annonces, sinon verdict `insuffisant` ; type priorisé (Maison/Appartement) avec repli mixte sous 30 ventes ; écart % = `100·(demandé−acté)/acté` ; badge « sous le marché » à ≤ −15 %. Rognage 5 % des extrêmes, bornes 100–12 000 €/m².
2. **Par annonce, rayon adaptatif (le « bon » comparateur).** `signaux._ref_local` **délègue** au moteur de secteur unique `faisabilite.bilan.reference_locale` : rayons **500 → 1000 → 1500 m**, **minimum 8 ventes** par rayon (`MIN_N_SECTEUR = 8`), fenêtre 5 ans de préférence, repli **commune** si aucun rayon ne tient (`bilan.py:120-121, 249-260, 338`).

Le code **sait** que la comparaison commune est mauvaise : commentaire `signaux.py:48-53` — « la référence commune-entière est **TROP LARGE** → surestime de **+70 à +231 %** », d'où la voie par parcelle.

### Ce qui manque — et le nœud

**La voie par annonce (rayon adaptatif) est VERROUILLÉE sur le rattachement.** `_ref_local` renvoie `None` si **pas d'idu**, type non bâti, ou n insuffisant à 1500 m (`signaux.py:56-62`). Or **0 bien sur 416 n'a d'idu** (Lot C). **Conséquence directe : aujourd'hui, 100 % des comparaisons retombent sur la médiane commune** — c'est-à-dire exactement la référence que le code lui-même qualifie de +70 à +231 % trop large. **La qualité du « prix vs DVF » de l'outil annonce dépend entièrement du Lot C.**

**Écart avec la cible** (rayon adaptatif 300 m → 3 km, 8 ventes mini, repli commune < 3 ventes) :

| Critère | Cible | Existant | Écart |
|---|---|---|---|
| Rayon mini | 300 m | 500 m | +200 m |
| Rayon maxi | 3 000 m | 1 500 m | **−1 500 m** (pas de palier 2/2,5/3 km) |
| Ventes mini | 8 | 8 | **conforme** |
| Repli commune | sous 3 ventes | dès < 8 à 1500 m (→ `None`) | repli plus **précoce** |
| Critères de ressemblance | — | **type + surface bâti ≥ 20 m² seulement** ; pièces, année, état **ignorés** | partiel |

En clair : l'ossature (rayon → min 8 → repli commune) **existe et est proche de la cible**, mais plafonne à 1,5 km, filtre peu (type + surface), et surtout **ne s'active jamais faute d'idu**.

---

## Lot C — Rattachement annonce → parcelle (le nerf)

### Ce qui existe

Pipeline **sophistiqué et déjà écrit**, en deux versions (`rattachement.py` V0, `rattachement_html.py` V2 — c'est V2 qui vaut) :

- **V2, convergence double-critère anti-faux-positif** (`rattachement_html.py:153-231`) : autour du point de l'annonce, rayon **150 m** (`geom_2975`), on croise jusqu'à 5 critères indépendants — surface terrain ±10 %, emprise bâtie BD TOPO, DVF ±15 %, DPE ±10 %, piscine ortho. **Rattachée** = **exactement 1 parcelle** avec **≥ 2 critères** (confiance 0,75 → 0,95). Plusieurs convergences → `piste`. Terrain nu : exception « 1 seule parcelle à ±1 % » → `probable` (0,70).
- Résultat stocké sur `pige_biens` : `idu`, `rattachement_etat` (rattachee/piste/non_rattachee), `rattachement_niveau`, `rattachement_confiance`, `rattachement_pistes` (jsonb), `rattachement_humain` (geste admin « C'est cette parcelle »).

### Ce qui manque — mesuré

**Sur les 416 biens de la base pige, le résultat est sans appel :**

| | biens | avec idu |
|---|---|---|
| **non_rattachee** | **369** | 0 |
| **piste** (candidats, jamais auto-utilisés) | **47** | 0 |
| **rattachee** | **0** | **0** |

**Aucun bien n'est rattaché à une parcelle. Aucun idu. Aucun rattachement humain. Aucune adresse exacte.** Le pont vers PLU / résiduel / Score n'est **jamais franchi automatiquement**.

**Cause racine, mesurée.** La convergence V2 a besoin d'un **point d'ancrage à 150 m près**. Or Leboncoin ne livre presque jamais l'adresse : répartition `source_position` —

| source_position | état | biens |
|---|---|---|
| **city** (centroïde quartier/commune, bruité à plusieurs km) | non_rattachee | 278 |
| city | piste | 42 |
| **address** (niveau rue) | non_rattachee | 19 |
| address | piste | 5 |
| (aucune coordonnée — vignettes dégradées) | non_rattachee | 72 |

Soit **24 biens seulement (5,8 %) géocodés au niveau rue** ; **320 au centroïde `city`** et 72 sans coordonnée. Avec un point « city » à plusieurs km, le rayon 150 m ne tombe sur rien d'exploitable → `non_rattachee`, ou au mieux une liste de `pistes` morphologiques (exemples réels : « terrain 184 m² ≈ 190 annoncés (3 %), emprise 170 m² » à 111 m, 2 pistes concurrentes → jamais tranché). `html_ingest` a d'ailleurs **désactivé le rattachement automatique** à l'ingestion (`html_ingest.py:322-331` → `non_rattachee`), reportant tout sur le geste admin manuel.

**Ce qui manque donc :** non pas l'algorithme (il est bon), mais **l'entrée d'une adresse exploitable**. Sans adresse rue, le rattachement reste humain, un par un.

---

## Conclusion — branchable ou vrai chantier ?

**Les deux, selon l'ambition.**

- **Ce qui est branchable tout de suite (socle réel) :** le serveur sait **déjà** parser une page d'annonce unique (y compris les faits déclarés PLU/drapeaux), un fetch one-shot existe, et le comparateur DVF par rayon (500→1500 m, min 8, repli commune) est écrit et proche de la cible. Un MVP « coller une URL → fiche prix + commune + type + écart DVF **commune** » est à portée **sans nouveau moteur**.

- **Ce qui est un vrai chantier :** les **deux maillons qui font la valeur foncière** sont en réalité **débranchés**. (1) Le rattachement parcelle produit **0 succès** sur données réelles, parce que Leboncoin ne donne pas l'adresse — et **tout l'angle LABUSE (PLU/résiduel/Score) passe par là**. (2) Le « bon » prix vs DVF (par parcelle) est **verrouillé sur ce même rattachement** et retombe à 100 % sur la médiane commune que le code juge +70 à +231 % trop large. Tant que l'adresse n'entre pas, l'outil reste un « afficheur d'annonce + repère commune », pas l'outil foncier visé. S'ajoutent : DPE/photos/description absents de la capture liste, blocage anti-bot sur le fetch direct, et aucun portail hors Leboncoin.

**En une phrase : l'ossature est là et bonne ; le nerf (annonce → parcelle) ne tient pas sur les données Leboncoin actuelles. Sans résoudre l'entrée d'adresse, « Analyser une annonce » en version foncière est un chantier, pas un branchement.**

### 3 décisions à soumettre à Vic

1. **Niveau d'ambition du MVP.** (a) *Léger* : URL → prix + type + écart DVF **commune** + faits déclarés, sans parcelle (branchable vite, mais c'est du *repere-immo* générique, pas l'angle foncier) ; (b) *Foncier* : on vise la parcelle → PLU/résiduel/Score, ce qui oblige à résoudre l'adresse (ci-dessous). Lequel vise-t-on d'abord ?

2. **Comment obtenir l'adresse rue** (sans quoi le rattachement reste à 0 et le DVF reste commune) : (a) **saisie/confirmation humaine** de l'adresse ou de la parcelle à l'analyse (le geste « C'est cette parcelle » existe déjà) ; (b) lire la **page détail** (plus riche que la liste : parfois rue + faits déclarés) via l'extension ; (c) exploiter les **pistes morphologiques** comme présélection à valider. L'audit recommande (a)+(c) : seul chemin fiable aujourd'hui. Accepte-t-on une **étape humaine** dans le parcours ?

3. **Périmètre portails & comptage prod.** (a) On reste **Leboncoin seul** pour le MVP, ou on provisionne SeLoger/Bien'ici (un parseur par portail + validation anti-blocage, Bien'ici probablement via API et non `outerHTML`) ? (b) Autorise-t-on un **comptage lecture seule sur la prod VPS** pour confirmer l'état réel de `pige_biens` en prod (l'audit n'a pu mesurer que la base Mac ; la prod est gelée depuis le 06/10 d'après [[radar-etat-1]]) ?

---

### Annexe — preuves

- **Base** : `postgresql:///labuse` (Mac), 428 annonces / 416 biens, 100 % Leboncoin.
- **Fiabilité champs** : `pige_faits` — prix 416, type 410, surface_hab 386, pièces 348, prix_m2 342, surface_terrain 216, année 154, **DPE 12**, photos 0, description 0.
- **Rattachement** : `pige_biens` — non_rattachee 369, piste 47, **rattachee 0, idu 0, rattachement_humain 0, adresse_exacte 0**. `source_position` : city 320, address 24, aucune 72.
- **Code** : extension `outils/radar-extension/background.js` ; extraction `src/labuse/pige/html_next.py`, `html_ingest.py`, `intake.py`, `api.py` ; DVF `signaux.py`, `marche.py`, `faisabilite/bilan.py` ; rattachement `rattachement.py`, `rattachement_html.py`, `tables.py`.
