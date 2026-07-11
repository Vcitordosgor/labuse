# MANDAT FABLE — Wave ANC + Végétation : assainissement non collectif & canopée

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/wave-anc-vegetation` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot.

**Dépendance** : le Lot B (végétation) réutilise l'infrastructure tuiles du mandat Détection Ortho (`ortho_tiles`) — ne l'exécuter qu'APRÈS merge de `feat/wave-ortho-detection`. Le Lot A (ANC) est totalement indépendant et exécutable immédiatement.

---

## Contexte business

**Lot A — ANC** : une part majeure du parc réunionnais n'est pas raccordée au tout-à-l'égout, avec des taux de non-conformité élevés constatés par les SPANC. Mécanisme légal type APER : le diagnostic ANC est obligatoire à la vente et, en cas de non-conformité, **l'acquéreur doit mettre l'installation aux normes sous 1 an** (art. L.1331-11-1 du Code de la santé publique — Fable vérifie la référence exacte et la formulation avant de l'afficher). Donc : mutation DVF en zone ANC = travaux quasi obligatoires dans les 12 mois = le lead parfait pour les entreprises de travaux ANC (terrassiers, poseurs de fosses/micro-stations, bureaux d'études ANC).

**Lot B — Végétation** : la BD ORTHO existe en canal infrarouge (IRC) → NDVI → détection de canopée. Deux débouchés : segment **élagueurs/abatteurs** (végétation haute en limite de parcelle — obligation civile d'élagage, risque cyclonique) et **fiabilisation des leads solaires** (`flag_ombrage_vegetal` : un toit sous canopée = mauvais lead PV même bien exposé).

## Schéma cible

```sql
parcel_anc(idu PK→parcels,
           zone_anc text,          -- 'anc' | 'collectif' | NULL (inconnu)
           source text,            -- 'zonage_officiel' | 'proba_insee'
           proba_anc int,          -- 0-100 (renseigné même quand zonage officiel absent)
           updated_at)
parcel_vegetation(idu PK→parcels,
           ndvi_moyen float,
           canopee_pct float,              -- % de la parcelle sous canopée
           canopee_limite_pct float,       -- % de la bande limite (3 m) sous canopée
           canopee_bati_pct float,         -- % du buffer bâti (8 m) sous canopée
           methode_hauteur text,           -- 'mns' | 'lidar' | 'texture_fallback'
           confiance text,                 -- 'haute' (hauteur mesurée) | 'moyenne' (texture)
           updated_at)
```

Seuils en config : NDVI canopée (défaut 0.5), hauteur végétation haute (défaut 3 m), buffers, seuil ombrage.

---

## LOT A — Assainissement non collectif

### A1. Couche probabiliste (fiable, toute l'île)

1. **INSEE** : fichiers détail Logements du recensement (millésime le plus récent) — identifier dans le dictionnaire des variables celle du raccordement au réseau d'assainissement/égout, agréger le taux de non-raccordement à la maille la plus fine disponible (IRIS si la variable y est diffusée, sinon commune).
2. **Office de l'eau Réunion** (eaureunion.fr) : chercher données/publications sur les taux de raccordement par commune — utiliser comme calage/contrôle croisé de l'INSEE. Si seul un rapport PDF existe, extraire le tableau par commune manuellement dans un CSV de seed versionné (pas de scraping fragile).
3. `proba_anc` par parcelle bâtie = taux de non-raccordement de sa maille, modulé : +15 pts si la parcelle est à > 100 m de toute zone U dense (proxy réseau absent — utiliser le zonage PLU déjà en base : les zones N/A/AU non équipées sont massivement en ANC), plafonné 5-95.

### A2. Zonages officiels (précis, couverture variable — best effort discipliné)

1. Les zonages d'assainissement sont des annexes des documents d'urbanisme, parfois versées au **Géoportail de l'urbanisme**. Vérifier commune par commune (les 24) via l'API GPU ce qui est disponible en format SIG.
2. Fallback : sites des 5 intercommunalités compétentes (CINOR, TCO, CIVIS, CIREST, CASUD) — si zonage SIG téléchargeable, l'intégrer ; si PDF non géoréférencé, **noter et passer** (pas de digitalisation manuelle dans ce mandat).
3. Là où un zonage officiel existe : `zone_anc` renseigné, `source='zonage_officiel'`. Ailleurs : `source='proba_insee'` et seul `proba_anc` fait foi.
4. Tenir un tableau de couverture dans le rapport : commune × source disponible.

### A3. Signal et vue

1. Signal `anc_mutation` : parcelle bâtie × (`zone_anc='anc'` OU `proba_anc ≥ 70` — config) × mutation DVF < 12 mois.
2. **Vue "Prospection ANC"** (pattern des vues Habitat) : filtres commune, ancienneté mutation, source du zonage, pente (Lot MNT du mandat Ortho, si mergé — un terrain pentu complique la filière), export CSV "à l'occupant".
3. UI : mention informative sourcée sur l'obligation de mise en conformité post-vente — formulation factuelle validée par la référence légale, jamais de conseil juridique.

---

## LOT B — Végétation (après merge du mandat Ortho)

### B1. Acquisition IRC + NDVI

1. BD ORTHO **IRC** (infrarouge couleur) 974 — Géoplateforme IGN, même logique d'accès que l'ortho RVB du mandat précédent, même grille `ortho_tiles` (uniquement les tuiles déjà marquées "à traiter").
2. Pseudo-NDVI par pixel = (PIR − R) / (PIR + R). Masque canopée : NDVI ≥ seuil.

### B2. Hauteur de végétation — trois niveaux, prendre le meilleur disponible

1. **LiDAR HD IGN** : vérifier la disponibilité effective des dalles sur La Réunion (programme national en déploiement — statut 974 à constater, pas à supposer). Si dispo : MNH = MNS LiDAR − MNT → végétation haute = MNH > 3 m ∧ NDVI ≥ seuil. `methode_hauteur='lidar'`, `confiance='haute'`.
2. Sinon **MNS Corrélé IGN** (issu de la corrélation des prises de vue ortho) si disponible sur le 974 : même calcul, `methode_hauteur='mns'`, `confiance='haute'`.
3. Sinon **fallback texture** : canopée arborée ≈ NDVI élevé + forte variance locale (texture rugueuse) vs pelouse/canne (NDVI élevé, texture lisse). `methode_hauteur='texture_fallback'`, `confiance='moyenne'` — et l'UI l'affiche comme "végétation arborée probable". Ne pas sur-vendre.

### B3. Agrégations parcelle + branchements

1. `canopee_pct` (parcelle), `canopee_limite_pct` (bande intérieure de 3 m le long des limites parcellaires), `canopee_bati_pct` (buffer 8 m autour de l'emprise bâtie — V0 omnidirectionnelle ; le raffinement directionnel nord/est/ouest hémisphère sud est hors mandat, le noter en TODO).
2. **Branchement solaire** : `parcel_solar.flag_topo_ombrage` reste inchangé ; ajouter `flag_ombrage_vegetal = canopee_bati_pct > 30%` (config). Les vues de prospection PV du mandat Solaire ajoutent ce flag en filtre d'exclusion par défaut (décochable).
3. Signal `vegetation_haute_limite` : `canopee_limite_pct > 40%` (config) — le lead élagueur.

### B4. Vue "Prospection élagage"

Filtres : canopée en limite min, présence bâti voisin (< 10 m de la limite végétalisée — l'argument du conflit de voisinage/risque cyclonique), commune, confiance. Export "à l'occupant". Mention informative art. 673 Code civil (élagage en limite) formulée factuellement.

---

## Critères d'acceptation

```sql
-- A. Cohérence ANC : la médiane de proba_anc doit refléter les taux Office de l'eau (~ moitié du parc)
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY proba_anc) FROM parcel_anc;

-- A. Gradient : les Hauts et zones rurales > centres urbains denses
SELECT commune, avg(proba_anc) FROM parcel_anc pa JOIN parcels USING (idu)
GROUP BY 1 ORDER BY 2 DESC;   -- Salazie/Cilaos/hauts en tête, Le Port/Saint-Denis centre en queue

-- A. Signal exploitable
SELECT count(*) FROM signals WHERE type='anc_mutation';   -- attendu : centaines à ~2K/an glissant

-- B. Sanity physique NDVI : l'Est au vent (pluvieux) plus vert que l'Ouest sous le vent
SELECT cote, avg(ndvi_moyen) FROM parcel_vegetation pv JOIN ... ;   -- Est > Ouest obligatoire

-- B. Couverture
SELECT methode_hauteur, count(*) FROM parcel_vegetation GROUP BY 1;

-- B. Volumétrie élagage plausible
SELECT count(*) FROM parcel_vegetation WHERE canopee_limite_pct > 40;
```

+ Playwright : vues ANC et Élagage chargent, filtrent, exportent non-vide. + Vérification visuelle Vic : 20 vignettes "végétation haute détectée" (réutiliser l'outil de validation du mandat Ortho).

## Contraintes

- RGPD : niveau parcelle, exports "à l'occupant", aucune donnée nominative personne physique.
- Positionnement : l'élagage se vend comme service au propriétaire de la végétation ou à son voisin exposé — aucune fonctionnalité de signalement/délation de voisinage. Le module ANC qualifie des travaux, il ne "détecte pas des fosses non conformes" (donnée qu'on n'a pas et qu'on ne prétend pas avoir).
- Mentions légales (CSP L.1331-11-1, Code civil 673) : références vérifiées par Fable avant affichage, formulation factuelle courte.
- Attribution IGN (IRC/LiDAR/MNS) et INSEE dans l'UI.
- Paramètres en config. Réseau : INSEE, GPU, sites intercos, Géoplateforme IGN, Office de l'eau. Rien d'autre.
- Ordre : Lot A intégralement, puis Lot B (post-merge Ortho). Si le mandat Ortho n'est pas mergé au moment de l'exécution : livrer le Lot A seul et s'arrêter proprement.

## Rapport de fin attendu

Lot A : maille INSEE obtenue, tableau de couverture zonages par commune (officiel vs proba), volumétrie du signal anc_mutation. Lot B : méthode hauteur retenue (lidar/mns/texture) avec justification, résultat du sanity Est/Ouest, volumétries canopée, nb de leads PV re-flagués `ombrage_vegetal`, nb de parcelles candidates élagage.
