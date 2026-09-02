# MANDAT SCORING-1 — l'algorithme mis à nu (audit, lecture seule)

**Branche : `audit/scoring-1`**. **Aucune modification de code servi** : ce mandat lit, mesure, écrit un rapport. Scripts de mesure dans `scripts/audit/scoring/`, rapport dans `docs/audit-2026-09/SCORING-RAPPORT.md`. Aucun sous-agent ne touche à git.

**Pourquoi** : Vic veut savoir ce que vaut le modèle, comment il est fait, quelles données s'y entrelacent, où sont les gisements — avant de décider quoi améliorer.

**Étape 0** : pwd, branche, arbre propre.

## Règle d'écriture du rapport

Chaque section commence par **trois phrases en français simple** (ce qu'on a trouvé, ce que ça veut dire, ce qu'on peut en faire), puis le détail. Un chiffre sans sa base (« 6,7× » sans « ×1,74 % = 11,7 % ») ne compte pas. Aucune conclusion sans la mesure qui la porte.

## A — Le modèle, expliqué

1. **Ce qu'il prédit exactement** : la cible (vente sous 1 an ? quel type de mutation — vente, succession, donation ?), l'unité (parcelle ? bien ?), la fenêtre.
2. **Comment il est fait** : type de modèle (hasard en temps discret — une phrase), périodes d'apprentissage et de validation, walk-forward. Où il vit dans le code, quel run est servi (q_v11_m137), quel modèle de probabilité (m36-l2f-2026), quel run de résiduel (m135) — et **comment ces trois s'articulent** (schéma texte).
3. **La chaîne complète** : feature store → cascade → scoring → policy (paliers) → présentation, avec pour chaque étape ce qui entre, ce qui sort, ce qui peut écarter une parcelle.

## B — Les données entrelacées : la carte des variables

Cœur chirurgical du mandat.

1. **Toutes les variables**, une ligne chacune : nom · définition en français · source amont (laquelle des 64) · millésime · **couverture réelle mesurée** (% de parcelles renseignées) · type (statique / évolutive / calculée).
2. **Importance mesurée** : contribution de chaque variable au classement (permutation ou équivalent, sur validation). Les 10 qui comptent, celles qui ne comptent **pas** (candidates au retrait), celles qui comptent mais sont mal couvertes (le gisement).
3. **Dépendances** : lesquelles disent la même chose (corrélées), lesquelles dérivent l'une de l'autre — schéma « qui dérive de quoi ».
4. **Fuites** : une variable connaît-elle la vente qu'elle prétend prédire (permis déposé par l'acheteur, DVF de la même mutation) ? Test explicite, résultat écrit.
5. **Ce qui manque** : variables connues comme prédictives en France et absentes — âge du propriétaire, décès/succession, indivision, propriétaire non résident, vacance du logement, durée de détention, divorce. Pour chacune : déjà en base sans être utilisée ? dans une source sous convention (fichiers fonciers, LOVAC) ? nulle part ?

## C — La calibration réelle : est-ce que « 1/5 » vaut 1/5 ?

1. Sur l'année de validation hors échantillon (2025), **par décile** : probabilité prédite moyenne vs taux de vente observé. Tableau + écart.
2. **Par commune** (24) : lift du décile supérieur, taux observé, nombre de ventes — mention honnête si l'effectif est trop faible.
3. **Par type** : terrain nu / bâti · zone U / AU / A-N. Bon partout, ou bon en U et aveugle en A ?
4. **Par palier affiché** : sur les parcelles marquées Priorité / À suivre / Long terme / Neutre / Faible début 2025, combien se sont vendues. Le libellé tient-il sa promesse ?
5. **Stabilité** : q_v10 → q_v11, combien de parcelles changent de palier et pourquoi.

## D — Les paliers : logique et alternatives

1. **Comment sont fixés les seuils** aujourd'hui : quantile, probabilité absolue, règle ? Où dans le code.
2. **Ce que chaque palier contient** : effectifs île et par commune, probabilité médiane, part terrain/bâti.
3. **Simuler l'alternative** — trois niveaux + deux états : Priorité (≥ 1/5) · À suivre (1/10 à 1/5) · Sans signal · + « En vente » (annonce Radar rattachée) · Écartée (cascade). Effectifs résultants, et ce que ça change à Saint-Paul (aujourd'hui 21 / 264 / 1 251 / 21 774 / 10 600 / 17 095). Mesurer, ne rien changer.
4. **Le relatif** : pour chaque palier, le lift (« ×N la moyenne ») — pour décider si on l'affiche à côté de la fraction.

## E — Le Radar dans l'algorithme (préparer l'injection)

Vic veut, quand la collecte aura un mois, injecter les données Radar. Préparer sans brancher :

1. **Inventaire** de ce que le Radar produit par parcelle rattachée : annonce active (depuis quand), prix demandé, écart au référentiel, baisse de prix, retrait, vendue (paire DVF). Quantités réelles à ce jour.
2. **Trois natures à ne pas confondre** :
   - **un fait** (« en vente ») → un **état** affiché au-dessus des paliers, pas une variable ;
   - **une variable** (« a été en vente 24 mois sans se vendre », « baisse de prix ») → entre dans le hasard, avec sa couverture ;
   - **une cible** (paires annonce → vente DVF) → apprend le délai et l'écart demandé/acté, modèle à part.
3. **Seuils** : à partir de combien d'annonces rattachées et de paires chaque usage devient honnête (jamais un effet appris sur < 30 observations). Estimer la date au rythme actuel (7 rattachées / 108 — le goulot est là, le dire).
4. **Le schéma** : quelle table, quelles colonnes, quel job — prêt à mandater au seuil atteint.

## F — Le retour terrain (préparer la capture)

Le modèle prédit « va se vendre » ; le client veut « peut être convaincu ». À cadrer, sans construire :

1. **Ce qui existe déjà** : colonnes CRM (statuts de pipeline), statuts Courrier (répondu / sans réponse), signalements. Qu'est-ce qui est déjà exploitable comme étiquette ?
2. **Le vocabulaire minimal** proposé : contacté · pas de réponse · refus ferme · pas maintenant · ouvert à discuter · en négociation · vendu à nous · vendu à un autre. Un clic par changement, jamais un formulaire. Où le poser sans alourdir.
3. **Confidentialité** : ces étiquettes appartiennent au compte qui les pose. Elles ne peuvent nourrir un modèle commun qu'agrégées et anonymisées — le dire, et dire ce que ça implique.
4. **Seuil d'utilité** : combien d'étiquettes avant qu'un modèle « volonté de vendre » ait un sens.

## H — Recalcul mensuel : cadrer le CRON avant de le poser

Position de départ : **oui pour le calcul automatique, non pour la mise en service automatique** — le run candidat se calcule seul, Vic bascule à la main après lecture de l'écart. À instruire :

1. **Deux choses différentes** : *re-scorer* (même modèle, données du mois — sûr, mensuel) et *ré-entraîner* (le modèle réapprend — rare, toujours suivi d'une calibration C avant bascule). Ce que le pipeline fait des deux aujourd'hui.
2. **Ce qui bouge d'un mois à l'autre** : mesurer sur q_v10 → q_v11 quelles variables ont changé, combien de parcelles ont changé de palier, causes. Si 95 % des mouvements viennent de deux sources, la cadence se cale sur elles.
3. **Coût et durée** : le run (~3 h) peut-il tourner de nuit sans gêner la prod ? Un run incrémental est-il possible ?
4. **La cadence proposée** : le 1er du mois, après ingest-sitadel → run candidat → garde de cohérence → **note de version générée** (« run d'octobre : DVF 2026-S1, 312 annonces, N montent, M descendent, causes ») → notification → Vic bascule ou refuse. Dire ce qui existe déjà et ce qui manque.
5. **Ce que voit le client** : la date d'analyse change ; faut-il lui dire ce qui a bougé sur SES parcelles suivies ? Proposer.
6. **Garde-fous** : un run dont la calibration dévie ou dont > X % des parcelles changent de palier est **refusé par défaut** et signalé. Proposer X.

## G — Verdict et plan

1. **En cinq lignes** : le modèle est-il bon, où, et où il ne l'est pas.
2. **Les trois investissements qui rapportent le plus**, classés par gain / effort, avec ce qu'il faut pour chacun et ce qu'on mesure avant/après.
3. **Ce qu'il ne faut pas faire** (sur-ajuster, ajouter des variables à 5 % de couverture, changer les seuils sans re-calibrer).
4. Les mandats suivants proposés, un titre et trois lignes chacun — Vic tranche.

---

## Compte-rendu attendu

Rapport `SCORING-RAPPORT.md` commité, scripts rejouables, résumé chat en dix lignes. Attendus nommés : B.1 la table des variables avec couverture mesurée · B.4 le test de fuite · C.1 la calibration par décile · C.4 le taux de vente réel par palier affiché · E.3 la date estimée du seuil Radar · H.2 ce qui bouge d'un mois à l'autre · H.4 la cadence proposée · G.2 les trois investissements.
