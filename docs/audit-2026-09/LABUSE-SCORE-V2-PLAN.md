# LABUSE SCORE v2 — le programme

## 0. Ce que l'audit a dit, en une phrase

Le modèle est **honnête mais myope** : quand il parle, il a raison (Priorité se vend à 16 %, ×10), mais il ne parle que sur les 10-17 % de parcelles où ses meilleures variables existent, et il ignore totalement le propriétaire alors que 81 % des parcelles sont en personne physique.

Le gain n'est pas dans un algorithme plus sophistiqué. Il est dans **trois choses simples** : rendre ses variables complètes, lui donner le propriétaire, et lui faire dire ce que le client achète.

## 1. La question du client

Un client ne veut pas « une probabilité ». Il veut : **quelles parcelles j'approche cette semaine, pourquoi, et qu'est-ce que j'y fais**. Trois axes — un seul est modélisé :

| Axe | Question | Aujourd'hui | Cible v2 |
|---|---|---|---|
| **Mutation** | Va-t-elle changer de main ? | hasard 12 mois, AUC 0,61 | AUC ≥ 0,70, couverture 100 %, propriétaire inclus |
| **Potentiel** | Qu'est-ce qu'on y crée ? | cascade + SDP résiduel (58,7 %) | résiduel 100 %, valeur créée en € |
| **Accès** | Peut-on joindre le propriétaire ? | rien | identifiable / courrier possible / déjà contacté |

**Priorité v2 = Mutation × Potentiel, filtrée par Accès.**

## 2. Chantier DONNÉES

### 2.1 Le censoring (plus gros gain à effort nul)
Les trois variables fortes sont à 9-17 % parce que l'absence est codée inconnue. L'absence **est** l'information : détention inconnue = « pas de vente depuis ≥ N ans » (signal fort) ; pas de permis = 0 ; nu_constructible calculable dès le résiduel complet. Attendu : AUC 0,61 → 0,66-0,68.

### 2.2 Mort à retirer
ndvi (dégrade), canopée, accès équipements, friche (0,15 %).

### 2.3 Le bloc PROPRIÉTAIRE — gain maximal (sous convention)
Fichiers fonciers Cerema : année de naissance, nombre d'indivisaires, type de droit (usufruit = succession), commune de résidence (non-résident), date du dernier acte (détention exacte pour TOUTES les parcelles), nature de personne morale. LOVAC : vacance. Attendu : AUC ≥ 0,72, Priorité étendue au-delà des parcelles à permis.

### 2.4 Ouvert, à ajouter au catalogue et au CRON
BDNB (année de construction, DPE — une maison de 1965 en G, c'est une vente à venir), trimestriel · DVF profondeur 2014 + types de mutation, semestriel · BODACC liquidations/dissolutions SCI, quotidien · Sitadel permis, refus, démolir, mensuel · INSEE décès × propriétaires (**avis juridique obligatoire avant usage**) · Radar (état « en vente » maintenant, variables à 1 mois, cible à 3-6) · retour terrain CRM.

### 2.5 Le voisinage et le marché
Une vente se propage. Variables as-of : ventes dans 150/400 m sur 12 et 24 mois et tendance · permis et opérations de promoteur dans le voisinage · prix de secteur et volume de transactions communal par année · propriétaire multi-parcelles ayant vendu récemment (« vendeur actif »). Second gain après le propriétaire.

### 2.6 Horizons
12 **et** 24 mois affichés (« 1/5 sous 1 an · 1/3 sous 2 ans »). « Long terme » devient une colonne, pas un palier.

### 2.7 Ce qu'on ne fera pas
Pas de variable < 5 % de couverture. Pas de source sans date. Pas de donnée client nominative dans le modèle commun.

## 3. Chantier MODÈLE

1. **Segments avant sophistication** : bâti individuel · terrain nu · personne morale · copropriété (base 29 %, isolée). Zone A non modélisée (AUC 0,51), écartée par la cascade.
2. **Challenger** : gradient boosting avec contraintes de monotonie, contre le champion, dans l'arène. Le champion reste servi tant que le challenger ne gagne pas sur une **année vierge**.
3. **Calibration propre** : entraîner ≤ 2023, calibrer 2024, tester 2025 — jamais calibrer et tester sur la même année (défaut actuel). Isotonique par segment.
4. **Explicabilité** : trois raisons en français par parcelle (SHAP → phrases).
5. **Objectifs** (année vierge) : métrique de tête = **précision en haut de liste** (précision@100 par commune, précision de Priorité), l'AUC est secondaire. Priorité ≥ 15 % de ventes réelles sur un effectif ≥ 3× l'actuel ; décile ≥ ×3 ; AUC ≥ 0,70 ; ECE ≤ 0,01 par segment ; churn ≤ 2 %.
6. **Hygiène de la cible** : une mutation multi-parcelles compte une fois par parcelle avec un indicateur « vente groupée » ; les ventes à des clients LABUSE sont marquées pour ne pas apprendre notre propre effet — et pour le mesurer.

## 4. Chantier PRODUIT

1. **Trois niveaux + deux états** : Priorité · À suivre · Sans signal — et En vente (Radar) · Écartée (cascade). Fini Long terme / Neutre / Faible.
2. **Score lisible** : « 1/5 sous 1 an · ×10 la moyenne » + « +820 m² SDP · ~610 k€ créés » + « propriétaire identifié · courrier possible ».
3. **Le pourquoi** : trois raisons en français, sourcées, datées.
4. **Analyse de commune** : « 21 priorités à Saint-Paul — 14 sur détention longue, 5 sur permis, 2 sur succession ; 3 nouvelles depuis août ».
5. **Ce qui a changé** : note de version par run + veille « ma parcelle a changé de niveau ».
6. **Honnêteté** : « 4 Priorités sur 5 ne se vendront pas cette année — mais c'est 10 fois plus que le hasard ».
7. **Complétude** : « score complet » ou « score partiel — propriétaire inconnu ».

## 5. Chantier EXPLOITATION

| Rythme | Quoi | Qui décide |
|---|---|---|
| quotidien | BODACC, Radar, sentinelle, garde de cohérence | CRON |
| mensuel (1er) | Sitadel → re-score candidat → arène → note de version → notification | CRON calcule, **Vic bascule** |
| trimestriel | BDNB, DVF profondeur, ré-entraînement challenger en arène | CRON calcule, Vic promeut |
| annuel | fichiers fonciers, LOVAC, recalibration | Vic |
| continu | retour terrain CRM, rattachement Radar | clients / Vic |

**Gardes** : ECE > 0,02, churn > 2 %, couverture d'une variable en chute > 10 points → run **refusé par défaut**, notifié, jamais basculé.

## 6. Séquence des mandats

1. **SCORING-2 — Fondations** : censoring, variables mortes, résiduel 100 %, segments, horizons, voisinage, calibration année vierge, challenger, raisons SHAP.
2. **PROPRIETAIRE-1** : bloc propriétaire + LOVAC + BDNB.
3. **PALIERS-1** : trois niveaux, score composite, pourquoi, analyse commune.
4. **CRON-SCORE-1** : re-score mensuel, arène, gardes, dérive.
5. **TERRAIN-1** puis **RADAR-ALGO-1**.

## 7. Quatre décisions pour Vic

1. **La convention fichiers fonciers inclut-elle la table propriétaires ?** Si non, la demander au Cerema — levier n° 1.
2. **La convention autorise-t-elle l'usage dérivé commercial ?** (variables agrégées, jamais nominatives) — à lire avant PROPRIETAIRE-1.
3. **INSEE décès × propriétaires** : avis juridique avant tout usage.
4. **Copropriété** : hors classement promoteur (recommandé) ou segment visible ?
