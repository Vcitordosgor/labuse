# COMMUNE-FIX-2 — la fiche commune propre et juste

**Branche** `fix/commune-fix-2` · worktree `~/Desktop/labuse-commune2` · ports API 9930 / front 7130.
Aucun merge, aucun accès prod. DA existante conservée. Captures avant/après dans `captures/`.

Deux fichiers touchés (front only, zéro backend, zéro DDL) :

| Fichier | Rôle |
|---|---|
| `frontend/src/components/contexte/ContextePanel.tsx` | la fiche commune (volet 420 px) |
| `frontend/src/components/header/Header.tsx` | le menu déroulant « Fiche commune » du header |

+ `tests/test_commune_fix_2.py` (non-régression `reel`) et ce dossier d'audit.

---

## 1. Aucun défilement horizontal, quelle que soit la largeur du texte

**Cause trouvée (mesurée live, pas au grep).** Le bloc Identité débordait de **21 px** à droite :
la valeur de `RowT` était `shrink-0 text-right` — un libellé long (la ligne « Par quartier … » :
`vacance méd. 8,2 % (étendue 0–53,7 % selon l'IRIS, petits IRIS inclus)`) ne pouvait pas rétrécir et
poussait la largeur → barre horizontale (`scrollWidth 440 > clientWidth 419`).

**Correctif (3 gestes, robustes « quelle que soit la largeur ») :**
- `RowT` : la valeur passe de `shrink-0` à `min-w-0 break-words` → elle revient à la ligne au lieu de pousser.
- La ligne longue « Par quartier » est **destructurée** : libellé + chiffre-clé (vacance médiane) sur la
  1ʳᵉ ligne, la précision (« étendue … ») en **pleine largeur** dessous — plus de colonne de droite écrasée.
- Garde-fou dur : le conteneur défilant reçoit `overflow-x-hidden` → **aucune barre horizontale possible**,
  quel que soit le texte, et comme tout revient à la ligne, rien n'est tronqué.

**Vérifié live** sur Saint-Denis et Saint-Philippe (RNU), **toutes sections dépliées** : `0` élément
débordant, `scrollWidth == clientWidth`. Avant : `captures/avant-04-identite-loaded.png` (« Par » chevauche
« vacance »). Après : `captures/apres-02-bandeau.png`.

## 2. Trois gros chiffres ajoutés au bandeau

Le bandeau passe de 6 à **9 chiffres** (grille 3×3, dernière rangée = les trois ajoutés), **même gabarit**
que les six (chiffre mono bold 14 px · libellé caps · source) :

| Chiffre | Valeur | Source |
|---|---|---|
| **Surface** | surface cadastrale de la commune (ha) | Cadastre (`foncier.surface_ha`) |
| **Intercommunalité** | sigle (CINOR, TCO, CIVIS, CIREST, CASUD) | INSEE (`d.epci`) |
| **SRU (LLS / obj.)** | part de logements sociaux / objectif légal | DHUP (`sru.taux_lls / objectif_pct`) |

Tout vient **déjà du payload** (`d.foncier.surface_ha`, `d.epci`, `d.sru`) : aucun chiffre en dur, aucun
appel réseau en plus. Capture : `captures/apres-02-bandeau.png`.

## 3. Section « Contacts » retirée

Le composant `ContactsMairie` (contacts nommés + bouton « + Ajouter un contact », listing/ajout admin) est
**supprimé** de la fiche, ainsi que ses imports devenus inutiles (`useMutation`, `useQueryClient`,
`getMoi`, `getCommuneContacts`, `postCommuneContact`, `deleteCommuneContact`, `ContactEdit`…). Les
**coordonnées officielles de la mairie** (adresse, téléphone, e-mail, site, fiche Annuaire) **restent** dans
le bloc Identité — ce sont des coordonnées, pas la section de contacts retirée.

## 4. Une seule police, une seule échelle de tailles (alignée sur le reste de l'app)

Décision retenue (confirmée avec le demandeur) : **garder le système de rôles de l'app** (titre
Space Grotesk, chiffres-clés JetBrains Mono, corps Inter) et **unifier l'échelle**. La fiche utilisait
**≈ 13 tailles ad-hoc** (9 / 9,5 / 10 / 10,5 / 11 / 11,5 / 12 / 12,5 / 13 / 14 / `text-sm` / `text-base` /
`text-lg`). Elles sont ramenées à **une échelle de 6** : **18 / 14 / 12 / 11 / 10 / 9**.

Mapping : `9,5→10`, `10,5→10`, `11,5→11`, `12,5→12`, `13→12` (titres de carte) et `13→14` (chiffre-clé SRU),
`text-sm→12`, `text-base→text-lg (18)` ; les chiffres « héros » des cartes (foncier, terrain nu) sont
unifiés à **18**. Inventaire final : `9 / 10 / 11 / 12 / 14 px + text-lg (18)` — exactement l'échelle.
Captures : `captures/apres-03-foncier-prix.png`.

## 5. Menu déroulant « Fiche commune » refait

`Header.tsx` — `CommuneSelect` :
- **Largeur ajustée au contenu** : `w-max` (fini le `w-[320px]` fixe).
- **Apparition animée comme les autres menus** : classe `.floating` (→ `@keyframes apparition`, la même que
  le menu compte).
- **Deux colonnes** (`grid grid-cols-2`), **triées alphabétiquement** (article ignoré via `trierCommunes`),
  chacune **avec son code** (code postal `CP_PAR_COMMUNE`, repli INSEE).

Avant : `captures/avant-01-dropdown.png` (une colonne, 320 px fixe). Après :
`captures/apres-01-dropdown.png` + zoom `captures/apres-01b-dropdown-zoom.png`.

---

## 6. Vérification des 24 fiches contre leurs sources — 0 chiffre faux

**Méthode.** Les 24 payloads servis par `/communes/{insee}/contexte` (exactement ce que l'écran lit,
`_rafraichir_partages` live compris) comparés **fait par fait** aux **tables sources**, par recalcul SQL
indépendant (`verif_sources.py`, lecture seule) :

| Famille (source) | Faits vérifiés / commune | Table source | Résultat |
|---|---|---|---|
| **INSEE** | habitants, millésime, logements, ménages, vacance % | `population_legale`, `commune_insee_logement` | **120/120 ✓** |
| **SRU** (DHUP) | taux LLS, objectif, statut, nb LLS | `commune_contexte_sru` | **96/96 ✓** |
| **DVF** | prix ancien médian €/m², mutations 12 mois | `dvf_mutations` (mêmes filtres) | **48/48 ✓** |
| **Sitadel** | permis 12 mois (nb) | `sitadel_permits` | **24/24 ✓** |
| **GPU** | zonage U/AU/A/N Σ ≈ 100 % | `spatial_layers` (cohérence) | **24/24 ✓** |
| **Bandeau ajouté** | surface cadastrale ≤ somme parcels ; sigle EPCI | `parcels`, `config/epci_974.yaml` | **48/48 ✓** |

**TOTAL : 360 faits sur 24 communes · 0 écart.** Contrôles de réalité : les 24 médianes DVF et les 24
`permis_12m` sont non-nuls ; les 5 EPCI de La Réunion sont correctement assignés (TCO, CINOR, CIREST,
CIVIS, CASUD) ; Saint-Philippe = RNU. Tableau complet : `verif_table.csv` (312 lignes INSEE/SRU/DVF/
Sitadel/GPU). Script rejouable : `verif_sources.py`.

**Non-régression.** `tests/test_commune_fix_2.py` (marqué `reel` → tourne au banc de nuit, pas dans le
pre-push) verrouille ces invariants fiche = source pour les 24 communes. **6 tests, 6 passed** (3,7 s).

---

## 7. Portes vertes

| Vérif | Résultat |
|---|---|
| Scan secrets | ✓ rien trouvé |
| Front `tsc -b` | ✓ |
| Front `vitest` | ✓ 309 passed (65 fichiers) |
| Front `vite build` | ✓ |
| Python unitaires (famille hook, sans base) | ✓ 3193 passed, 49 skipped |
| Banc cohérence (12 témoins, base locale) | ✓ 6 passed — **aucun écart (1 €/1 m²)** |
| `test_commune_fix_2.py` (reel, 24 communes) | ✓ 6 passed |

Tout est vert. Commit sur `fix/commune-fix-2`, pas de merge.
