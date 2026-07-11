# MANDAT FABLE — Moteur de Segments Habitat : 11 métiers, 1 architecture

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/moteur-segments-habitat` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot.

---

## 1. Contexte & principe d'architecture

11 métiers Habitat (pergolistes, paysagistes, clôtures, artisans rénovation, cuisinistes, salles de bain, couvreurs, menuiseries, termites, extensions, alarmes) partagent les mêmes données déjà en base — seuls les filtres changent. Interdiction de coder 11 vues en dur : ce mandat construit **UN moteur de segments** (query builder sur les attributs parcelle) + **une bibliothèque de presets métiers** stockée en données. Ajouter le 31e métier demain = insérer une ligne de preset, zéro dev.

**Coordination inter-mandats (IMPORTANT)** : les mandats Habitat Solaire, Détection Ortho et ANC/Végétation prévoient chacun des "vues de prospection". Règle de convergence : si ce moteur existe au moment où ces mandats s'exécutent, leurs vues s'implémentent comme **presets de ce moteur** (pas de systèmes parallèles). Si leurs vues ont déjà été construites en dur avant ce mandat, les migrer en presets fait partie du Lot 4. Un seul système de vues à la fin, quel que soit l'ordre d'exécution.

**Résilience aux mandats non mergés** : le moteur détecte à l'exécution quelles colonnes existent (`parcel_solar`, `parcel_equipements`, `parcel_terrain`, `parcel_anc`, `parcel_vegetation`…). Filtre dont la colonne manque → affiché grisé "disponible prochainement" ; preset dépendant → badge "partiel" avec la liste des filtres inactifs. Ce mandat est donc exécutable dans n'importe quel ordre de la pile.

## 2. Schéma

```sql
segment_presets(id PK, slug unique, nom, categorie text,      -- 'exterieur'|'renovation'|'energie'|'securite'|'foncier_bati'
                description text, argumentaire text,           -- la ligne de pitch commercial du segment
                filtres jsonb,                                 -- définition déclarative (voir Lot 1)
                colonnes_export jsonb, tri_defaut text,
                actif bool, ordre int, created_by text, updated_at)
parcel_residuel(idu PK→parcels,
                emprise_max_m2 float,                          -- selon règles PLU calibrées
                emprise_residuelle_m2 float,
                surelevation_possible bool,                    -- hauteur PLU vs hauteur BD TOPO
                confiance text,                                -- 'haute'|'moyenne' selon complétude règles
                updated_at)
catnat_arretes(id PK, insee, commune, type_peril text, date_arrete date, date_debut, date_fin, raw jsonb)
```

---

## Lot 1 — Le moteur (backend)

1. **Registry de filtres déclaratif** : chaque filtre = {clé, libellé, type (range/bool/enum/select), table.colonne source, unité, disponibilité détectée}. Filtres à câbler (selon existence) : ancienneté mutation DVF (mois), prix mutation, type de bien, période de construction (DPE), surface emprise bâtie, surface jardin (parcelle − emprise), pente moy/max, piscine, PV détecté, CES probable, score solaire, facture élec estimée, flag ABF, flag amiante, proba proprio-occupant, ombrage végétal, canopée limite, zone/proba ANC, zonage PLU, commune(s), QPV, emprise résiduelle, surélévation possible, catnat récent.
2. **Évaluateur** : preset.filtres (jsonb) → SQL paramétré sur `parcels` + jointures LEFT sur les tables d'attributs. Pagination, tri, count. Aucune injection possible : les clés de filtres passent par le registry, jamais de SQL libre côté client.
3. **API** : `GET /segments` (presets + disponibilité), `POST /segments/query` (preset modifié à la volée), `POST /segments/export`.
4. Un preset modifié à la volée ne s'enregistre pas ; la sauvegarde en nouveau preset est réservée admin (Vic).

## Lot 2 — Droits résiduels sur bâti (le calcul nouveau du mandat)

Recycle le moteur de constructibilité (règles PLU calibrées "premium fin" des 23 communes + RNU Saint-Philippe) sur les **parcelles déjà bâties** :

1. `emprise_max_m2` = surface parcelle × coefficient d'emprise du zonage PLU calibré (utiliser les règles déjà en base ; si une commune/zone n'a pas de règle d'emprise exploitable → NULL, `confiance` en conséquence).
2. `emprise_residuelle_m2 = emprise_max_m2 − emprise_bâtie_BD_TOPO` (plancher 0).
3. `surelevation_possible` : hauteur max du zonage (si calibrée) − hauteur bâtiment BD TOPO (attribut hauteur) ≥ 2.8 m.
4. **Libellé UI impératif** : "potentiel indicatif estimé — les règles complètes du PLU (retraits, prospects, servitudes) peuvent le réduire". C'est un signal de prospection, pas une étude de faisabilité — cohérent avec le produit Flash qui, lui, vendra l'analyse fine.

## Lot 3 — Signal CATNAT (le boost post-cyclone des couvreurs)

1. **Source** : base GASPAR (Géorisques — la wave Géorisques existante couvre les zonages ; vérifier si les arrêtés CATNAT y sont, sinon ingérer le fichier national GASPAR "arrêtés de catastrophe naturelle", filtré 974) → `catnat_arretes`.
2. Signal `catnat_recent` : commune sous arrêté CATNAT (vent cyclonique, inondation) de moins de 6 mois (config).
3. Effet : les presets marqués `boost_catnat` (couvreurs, étanchéité, menuiseries) affichent un bandeau "communes récemment en état de catastrophe naturelle : X, Y" et proposent le filtre pré-coché. Refresh : intégré au job mensuel existant.

## Lot 4 — Les presets seedés (seed versionné, éditable ensuite en admin)

| slug | Catégorie | Filtres par défaut | Tri | Boost |
|---|---|---|---|---|
| pergolas-terrasses | Extérieur | jardin ≥ 150 m², mutation < 24 mois, pente ≤ 10°, hors ABF (décochable) | mutation récente | — |
| paysagistes | Extérieur | jardin ≥ 300 m², mutation < 12 mois | jardin desc | — |
| clotures-portails | Extérieur | mutation < 12 mois, jardin ≥ 100 m² | mutation récente | — |
| artisans-renovation | Rénovation | mutation < 18 mois, construction < 1990 | mutation récente | — |
| cuisinistes | Rénovation | mutation < 12 mois | prix mutation desc | — |
| salles-de-bain | Rénovation | mutation < 18 mois, construction < 1995 | mutation récente | — |
| couvreurs-etancheite | Rénovation | construction < 1985 | âge bâti desc | catnat |
| menuiseries-cyclonique | Rénovation | construction < 1990 | âge bâti desc | catnat |
| termites-charpente | Rénovation | construction < 1980 | âge bâti desc | — |
| extensions-surelevations | Foncier bâti | résiduel ≥ 30 m² OU surélévation possible, proprio-occupant ≥ 60 | résiduel desc | — |
| alarmes-telesurveillance | Sécurité | mutation < 6 mois | mutation récente | — |

Note termites : l'île étant intégralement classée zone termites (à confirmer d'une phrase dans le rapport), le zonage n'est pas un filtre — le preset repose sur l'âge du bâti, et l'argumentaire le dit.

+ presets des autres mandats s'ils ne sont pas encore construits (ou migration s'ils le sont) : `pv-residentiel`, `chauffe-eau-solaire`, `clim-pac`, `piscinistes-construction`, `parc-piscines-entretien`, `anc-travaux`, `elagage` — reprendre leurs filtres définis dans les mandats respectifs. Chaque preset porte son `argumentaire` (la ligne de pitch : "Mutation < 6 mois = pic d'équipement alarme à l'emménagement", etc.) — soigner ces textes, ils serviront au commerce.

## Lot 5 — Frontend : la page "Segments"

1. Galerie de presets groupés par catégorie, badge de disponibilité (complet/partiel), compteur live de parcelles matchées par preset (cache 24h).
2. Clic → query builder pré-rempli : panneaux de filtres (grisés si indisponibles), carte + table paginée, colonnes du preset.
3. **Export CSV "à l'occupant"** standardisé : adresse, commune, caractéristiques du preset, jamais de nom de personne physique. En-têtes en français lisible (c'est l'artisan qui ouvre ce fichier dans Excel).
4. Admin (Vic uniquement) : CRUD presets, duplication, activation/désactivation, édition de l'argumentaire.

---

## Critères d'acceptation

```sql
-- Presets seedés et évaluables
SELECT count(*) FROM segment_presets WHERE actif;              -- ≥ 11 (+ ceux migrés/anticipés)

-- Chaque preset actif retourne un résultat non aberrant (échantillon)
-- via POST /segments/query : count > 0 ET count < 50% du parc bâti pour chaque preset

-- Résiduel : volumétrie et confiance
SELECT confiance, count(*) FROM parcel_residuel WHERE emprise_residuelle_m2 >= 30 GROUP BY 1;

-- CATNAT ingéré
SELECT max(date_arrete) FROM catnat_arretes;                   -- cohérent avec les derniers événements 974
```

+ Playwright : la page Segments charge, 3 presets testés (dont un "partiel" si applicable) filtrent et exportent non-vide, l'admin sauvegarde un preset dupliqué.
+ Test de résilience : moteur fonctionnel sur une base SANS `parcel_solar`/`parcel_equipements` (simuler l'absence) — les presets dépendants s'affichent "partiels" sans erreur.

## Contraintes

- RGPD : exports "à l'occupant", aucune donnée nominative personne physique, pas de filtre nominatif.
- Sécurité : aucune requête SQL construite depuis du texte client — registry de filtres uniquement.
- Paramètres et seuils des presets en seed éditable, pas en dur dans le code.
- Réseau : GASPAR/Géorisques uniquement (Lot 3). Tout le reste = base existante.
- Ordre conseillé : 1 → 4 (presets sur filtres déjà dispo) → 5 → 2 → 3. Livrer de la valeur visible avant les calculs lourds.

## Rapport de fin attendu

Liste des filtres câblés avec leur disponibilité constatée, compteurs par preset (le "combien de leads par métier" — c'est l'argument de vente de Vic), volumétrie résiduel/surélévation par confiance, confirmation du classement termites de l'île, statut CATNAT (source trouvée dans l'existant ou ingérée), et liste des presets marqués "partiels" avec le mandat qui les complétera.
