# MANDAT FABLE — Wave Détection Ortho : piscines, panneaux PV, pente terrain

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/wave-ortho-detection` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot.

**Prérequis (vérifier au démarrage)** : mandats **Habitat Solaire** (tables `parcel_solar`, `pv_registry`, `parkings_aper`) et **Data-Gap** (couche bâti + table `parcel_terrain`) mergés sur main. Si une dépendance manque : dégrader proprement (sauter le branchement concerné, le consigner au rapport), ne jamais bloquer le mandat.

---

## 1. Contexte business

Ce mandat débloque 4 usages d'un coup :
- **Piscinistes construction** : filtrer les parcelles SANS piscine (jardin + mutation récente + pente OK)
- **Entretien / rénovation / sécurité piscine** : cibler les parcelles AVEC piscine
- **Solaire** : `parcel_solar.pv_existant = 'detecte'` (exclusion prospection + candidats repowering fins) — implémente le stub `detect_rooftop_pv` prévu au mandat Habitat Solaire (Lot 4.4)
- **Parkings APER** : renseigner `parkings_aper.equipe` (ombrières présentes ou non)

Philosophie : **V0 déterministe + validation visuelle Vic avant tout ML.** Pas de deep learning tant que la V0 colorimétrique calibrée n'a pas montré ses limites sur échantillon validé. Le ML (Lot 8) n'est déclenché que sur décision de Vic après lecture des métriques.

## 2. Sources (toutes Licence Ouverte Etalab — usage commercial OK, attribution IGN)

- **BD ORTHO 20 cm** La Réunion — Géoplateforme IGN. Deux modes d'accès à évaluer au démarrage : téléchargement des dalles départementales (geoservices.ign.fr, JP2) ou flux WMS/WMTS `ORTHOIMAGERY.ORTHOPHOTOS` (data.geopf.fr, gratuit sans clé). Critère de choix : privilégier le téléchargement de dalles si volumétrie locale gérable (~50-80 Go temporaires), sinon streaming WMS par tuile. Documenter le millésime de l'ortho utilisée (l'âge de l'image = l'âge de la vérité terrain).
- **RGE ALTI 5 m** (MNT) La Réunion — même portail.
- Vérifier les URLs exactes courantes sur les deux portails avant d'implémenter ; les noter dans seed_sources.

## 3. Schéma cible

```sql
ortho_tiles(tile_id PK, geom, millesime, traite_at, nb_detections)
ortho_detections(id PK, type text,             -- 'piscine' | 'pv'
                 geom polygon, surface_m2 float,
                 confiance float,               -- 0-1, composite des critères
                 criteres jsonb,                -- détail scoring (debug/calibration)
                 idu text,                      -- parcelle rattachée
                 sur_bati bool,                 -- pour pv : sur emprise bâtie ?
                 validation text,               -- null | 'ok' | 'faux_positif' (Lot 3)
                 tile_id, detected_at)
parcel_equipements(idu PK→parcels,
                   piscine bool, piscine_surface_m2 float, piscine_confiance float,
                   pv_detecte bool, pv_surface_m2 float, pv_confiance float,
                   pv_probable_ces bool,        -- chauffe-eau solaire probable (voir Lot 4)
                   updated_at)
parcel_terrain(idu PK→parcels, pente_moy_deg float, pente_max_deg float,
               flag_terrassement_lourd bool)    -- seuil config, défaut 15°
```

Tous les seuils (couleur, surfaces, pentes, confiance) en config, jamais en dur.

---

## Lot 1 — Pente terrain (MNT) : le quick win indépendant

À faire EN PREMIER : aucun rapport avec l'ortho, livrable en quelques heures, valeur immédiate.

0. ⚠ Si `parcel_terrain` existe déjà (data-gap LOT 9) : **RÉUTILISER** — ne calculer que ce qui manque (ex. la pente sur la partie NON bâtie, plus juste pour placer une piscine) et compléter la table. Jamais de table de pente concurrente.
1. Télécharger RGE ALTI 5 m 974, mosaïquer si dalles multiples (sauter si le raster de pente du data-gap a été conservé).
2. `gdaldem slope` → raster de pente en degrés.
3. Stats zonales par parcelle (rasterstats ou PostGIS raster) : `pente_moy_deg`, `pente_max_deg`. Idéalement sur la partie **non bâtie** de la parcelle (parcelle − emprise bâtie, c'est là que va la piscine) ; sur la parcelle entière en fallback si le découpage coûte trop.
4. `flag_terrassement_lourd = pente_moy_deg > 15` (config).

**Sanity check** : la pente médiane des parcelles bâties doit être nettement inférieure à la pente médiane de l'île entière (on construit dans le plat). Sinon, bug de projection ou d'unités.

## Lot 2 — Infrastructure tuiles + acquisition ortho ciblée

On ne traite PAS toute l'île : uniquement les zones utiles.

1. Grille de tuiles 512×512 m sur l'emprise terrestre. Marquer "à traiter" les tuiles intersectant : (a) au moins une emprise bâtie, ou (b) un polygone `parkings_aper`. Le reste est ignoré (océan, forêts, remparts).
2. Acquisition des images par tuile (résolution native 20 cm → 2560×2560 px/tuile), cache disque local, reprise sur interruption (checkpoint par tile_id).
3. Journal dans `ortho_tiles` + `ingestion_runs`.

## Lot 3 — Détection piscines V0 (colorimétrique) + outil de validation

**Méthode** (OpenCV, vectorisé, pas de GPU requis) :
1. Conversion HSV → masque teinte cyan/turquoise (plage config, point de départ H≈[80,130] en OpenCV 0-179, S et V élevés) → morphologie (ouverture/fermeture) → contours.
2. Filtres géométriques : surface 6-150 m² (config), compacité/solidité minimales (formes de bassin, pas de filaments), ratio d'aspect < 6.
3. Filtres contextuels : le centroïde doit tomber dans une parcelle ayant une emprise bâtie (ou à < 30 m d'une) ; exclusion des détections sur l'océan, ravines et plans d'eau (couches hydro BD TOPO si dispo, sinon masque littoral par buffer côte).
4. `confiance` composite (couleur pure, forme, taille typique 15-50 m², contexte) ; stocker le détail dans `criteres`.
5. Rattachement : parcelle contenant le centroïde ; si à cheval, la parcelle de plus grand recouvrement.

**Faux positifs connus à gérer** (documentés dans le code) : bâches et toits bleus (forme rectiligne + sur bâti → rejeter si recouvrement emprise bâtie > 60%), trampolines (petits, circulaires, sombres), terrains de sport (trop grands, teinte différente).
**Faux négatifs assumés** : piscines vertes/sales, couvertes, sous ombrage dense — c'est le recall qu'on mesurera, pas qu'on fantasmera.

**Outil de validation (obligatoire, c'est le cœur du process)** : page locale (ou notebook) affichant des vignettes ortho aléatoires avec détection surlignée + contexte 50 m, boutons OK / Faux positif → écrit `ortho_detections.validation`. Vic valide un échantillon de 200 détections. Calibrer les seuils jusqu'à **précision ≥ 90%** sur l'échantillon. Estimer le recall : tirer 100 parcelles aléatoires dans 3 quartiers résidentiels contrastés (Ermitage, Tampon, Sainte-Marie), inspection manuelle, comparer aux détections.

## Lot 4 — Détection PV V0 : candidats scorés, attentes calibrées

Plus difficile que les piscines — le mandat assume une V0 à précision moyenne, livrée comme **candidats scorés**, pas comme vérité :

1. Sur les emprises bâties uniquement (+ polygones parkings pour les ombrières) : masque teinte sombre bleutée/anthracite à réflectance faible, formes rectilignes (rectangularité élevée après approximation polygonale), surface ≥ 4 m².
2. **Piège local n°1 — les chauffe-eau solaires** : le 974 en est couvert (obligation RTAA DOM sur le neuf). Un CES ≈ 2-4 m² de capteur + ballon. Règle : détection 4-8 m² → `pv_probable_ces = TRUE` (à exclure des stats PV mais à garder : c'est un signal "pas de CES à vendre ici" pour le segment chauffe-eau solaire !) ; ≥ 8 m² → PV probable.
3. Confusions à gérer : ombres portées (exclure si mitoyenneté avec zone très sombre non rectiligne), vérandas/velux (petits, isolés), toits sombres uniformes (rejeter si le masque couvre > 80% de l'emprise).
4. Validation : même outil que Lot 3, échantillon 150. Cible réaliste : **précision ≥ 75%** en V0. En dessous → les résultats restent en base avec `confiance` mais ne remontent PAS dans `parcel_equipements` (attendre Lot 8).
5. Ombrières parkings : détection PV intersectant `parkings_aper.geom` → `equipe = TRUE`.

## Lot 5 — Matérialisation + branchements inter-modules

1. `parcel_equipements` : agrégation des détections avec `confiance ≥ seuil` (config, défaut 0.7 piscines / 0.8 PV) ou `validation = 'ok'`.
2. Branchements : `parcel_solar.pv_existant = 'detecte'` là où `pv_detecte` ; croisement avec `pv_registry` (mandat solaire) : les parcelles PV détecté × commune à installations 2006-2013 → renforcer `repowering` ; `parkings_aper.equipe` (Lot 4.5).
3. Signal `piscine_detectee` + intégration aux filtres existants.

## Lot 6 — Frontend

1. Fiche parcelle : badges "Piscine (~32 m²)", "PV détecté", "CES probable", "Pente moyenne 8°".
2. **Vue "Prospection piscinistes"** : filtres SANS piscine + jardin min (m²) + mutation < N mois + pente max + hors ABF + proprio-occupant min → carte + export CSV "à l'occupant" (aucun nom de personne physique).
3. **Vue "Parc piscines"** (segment entretien) : AVEC piscine, tri par surface bassin, croisement bâti ancien (proxy piscine âgée).
4. Mention de sourcing UI : "détection automatique sur orthophotographie IGN [millésime] — fiabilité statistique, non contractuelle".

## Lot 7 — Refresh

La BD ORTHO 974 est re-survolée tous les ~3-4 ans : pas de cron. Commande CLI re-runnable `--refresh` qui détecte un changement de millésime et rejoue le pipeline sur les tuiles concernées. Documenter le millésime courant dans le rapport.

## Lot 8 — OPTIONNEL, sur décision Vic uniquement : V1 ML

Ne PAS commencer sans feu vert explicite après lecture des métriques V0. Si déclenché : fine-tuning d'un modèle de segmentation léger (U-Net/YOLO-seg) sur les annotations produites par l'outil de validation (Lot 3/4 — elles deviennent le dataset d'entraînement, c'était le plan depuis le début). Cibles : précision ≥ 95% piscines, ≥ 90% PV.

---

## Critères d'acceptation

```sql
-- Volumétrie piscines plausible (île ~900K hab, climat tropical, Ouest très équipé)
SELECT count(*) FROM parcel_equipements WHERE piscine;          -- attendu : 15 000 – 45 000

-- Gradient géographique : taux d'équipement piscine Ouest/Sud > Est
SELECT commune, count(*) FILTER (WHERE pe.piscine)::float / count(*) AS taux
FROM parcels p LEFT JOIN parcel_equipements pe USING (idu)
WHERE p.a_bati GROUP BY 1 ORDER BY 2 DESC;
-- Saint-Gilles/Saint-Paul/Saint-Leu en tête, Salazie/Sainte-Rose en queue, sinon investiguer

-- Précision validée
SELECT type, count(*) FILTER (WHERE validation='ok')::float /
       count(*) FILTER (WHERE validation IS NOT NULL) AS precision
FROM ortho_detections GROUP BY 1;                                -- piscine ≥ 0.90 ; pv ≥ 0.75

-- Pente : sanity
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pente_moy_deg) FROM parcel_terrain;

-- Couverture traitement
SELECT count(*) FILTER (WHERE traite_at IS NOT NULL)::float / count(*) FROM ortho_tiles;  -- = 1.0
```

+ Playwright : les 2 vues frontend chargent, filtrent, exportent non-vide.

## Contraintes

- **Positionnement** : ce pipeline sert la qualification commerciale. Aucune fonctionnalité, requête pré-câblée ou texte orienté "détection de piscines non déclarées" / fraude fiscale — ni dans le code, ni dans l'UI, ni dans les exports. Non négociable.
- RGPD : niveau parcelle/bâtiment uniquement, exports "à l'occupant" sans données nominatives personnes physiques.
- Attribution IGN dans l'UI (Licence Ouverte).
- Perf : pipeline exécutable sur la machine locale (CPU, OpenCV vectorisé), checkpoint/reprise, pas de dépendance GPU en V0.
- Disque : nettoyage du cache tuiles en fin de run (garder `ortho_tiles` + détections, pas les images).
- Ordre conseillé : **1 (MNT) → 2 → 3 → 5 partiel piscines → 6 → 4 → 5 complet → 7**. Le Lot 3 (validation Vic) est bloquant pour tout ce qui suit côté piscines : prévoir la session de validation tôt.

## Rapport de fin attendu

Millésime ortho, nb tuiles traitées, volumétries par type, précision/recall mesurés avec la matrice des seuils retenus, taux d'équipement par commune (top/flop 5), statut PV (intégré ou resté en candidats), nb parkings passés à `equipe=TRUE`, et recommandation argumentée GO/NO-GO sur le Lot 8 ML.
