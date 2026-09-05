# RETOURS-14 — COMPTE-RENDU

Branche `fix/retours-12`, deux commits (lot carte S5-S9, lot outils S1-S4 + S10 + S11).
Captures avant/après : `docs/audit-2026-09/RETOURS-14/captures/` (suffixes `-avant` / `-apres`).

## Une ligne par travail

- **S1 — deux tableaux** : FAIT. Deux portes distinctes dans l'outil Communes : « Évolution du
  marché — ventes actées et permis » (DVF trimestriel + Sitadel, sous-titre qui nomme les sources)
  et « Marché des annonces (Radar) — 101 biens collectés à ce jour » (compteur vivant dans le
  titre, médiane jamais servie sous n = 5). Le tableau Radar quitte le moteur M18 (il n'y est plus
  en doublon). Captures `S1-*`.
- **S2 — liens secondaires jaunes** : FAIT. `.hover-jaune` : jaune `--pj-jaune` EN PERMANENCE
  (mesuré au repos : `rgb(245,197,24)` après, `rgb(74,222,128)` avant), survol = fond jaune opaque
  texte encre. Appliqué aux 24 occurrences (Scan patrimoine, Fiche →, liens d'en-tête). Captures
  `S2-lien-repos`/`S2-lien-survol`.
- **S3 — annuaire PLU uniforme** : FAIT. Les 24 cartes partagent la même coquille
  (bordure/fond/texte identiques, plus de carte « éteinte ») ; la commune au RNU est cliquable et
  son écran offre le lien Légifrance vers les articles du RNU (mesuré : 1 lien après, 0 avant).
  Captures `S3-annuaire`, `S3-rnu-ecran`.
- **S4 — taxe d'aménagement retapée** : FAIT. L'outil s'ouvre sur UNE entrée : « Désignez la
  parcelle du projet » (barre unique ParcelInput + « …ou cliquez une parcelle sur la carte », la
  sélection carte est adoptée en direct) ; le formulaire n'apparaît qu'une parcelle désignée ; la
  surface taxable est préremplie et VISIBLE (BZ1065 → 26 m², mesuré dans le champ) ; le
  placeholder « ex. 120 » trompeur est supprimé. **Réponse sur R26** : R26 avait bien été commité
  (4cfe8e48) et servi — mais le préremplissage ne s'engageait que depuis une parcelle DÉJÀ
  sélectionnée (fiche ouverte) ; l'outil ouvert seul n'offrait ni barre ni explication du clic
  carte, et le placeholder « ex. 120 » restait affiché : pour Vic, l'outil semblait inchangé.
  C'est l'entrée de l'outil qui était en cause, pas le calcul. Captures `S4-entree`,
  `S4-parcelle-designee`.
- **S5 — permis orphelins rattachés par la géométrie** : FAIT. Nouveau module
  `ingestion/cadastre_historique.py` : cadastre d'ÉPOQUE embasé (Etalab millésimes 2017-07→2025-09
  + PCI vecteur DGFiP EDIGEO 2017-02-13, 5 233 parcelles disparues retrouvées), rattachement par
  `ST_PointOnSurface` de la parcelle d'origine, provenance DITE (`parcelle d'origine (cadastre X)`),
  parcelles actuelles mémorisées, drapeau `origine_redecoupee` si la parcelle a été redivisée.
  **Compteurs : 7 325 permis récupérés par la géométrie · 580 points d'adresse DÉMIS (geom →
  geom_approx, la liste dit « localisation approximative (adresse) ») · 2 894 restants sans
  localisation (motifs : parcelle disparue avant le premier cadastre disponible 2017-02, référence
  parcellaire illisible/erronée dans Sitadel).** Plus JAMAIS un point sur une parcelle incertaine.
  L'hôtel (PC 97441816A0077, parcelle d'origine BC0328 divisée le 31/12/2016) est posé sur son
  chantier (capture ortho) et remonte dans la fiche de la parcelle actuelle BC0331 (« Autour de
  cette parcelle » → permis à 0 m, tiroir = provenance « parcelle d'origine »). Captures `S5-*`.
- **S6 — toute couche au premier clic** : FAIT, avec un correctif différent de l'hypothèse du
  mandat. La cause mesurée n'était PAS une course addSource/addLayer : l'endpoint simplifiait les
  993 polygones d'aléa À LA VOLÉE à chaque requête (**14 s mesurées avant** — le temps que la
  réponse arrive, Vic avait décoché/recoché et le 2e clic touchait le cache react-query, d'où
  « le 2e clic marche »). Correctif : géométrie simplifiée MATÉRIALISÉE (`geom_simple`, entretenue
  au même point que `geom_2975`, jamais les 800 k bâtiments), endpoint en
  `COALESCE(geom_simple, à-la-volée)` → **0,8 s serveur, ~4 s rendu navigateur (14 Mo), au PREMIER
  clic, sur les 4 fonds** (captures avant = couche muette / après = aléa rendu, sombre/clair/
  plan/ortho).
- **S7 — arrêts fusionnés dans Transport public** : FAIT. Une seule entrée « Transport public
  (lignes et arrêts) » (l'entrée « Arrêts » séparée n'existe plus — mesuré 1 avant / 0 après), les
  arrêts montent avec la couche au zoom quartier et restent cliquables (popup Gare Routière
  vérifiée), légende et « i » réécrits (le renvoi des pôles d'échange vers « Axes structurants »
  est conservé — test FIX-COUCHES P5). Captures `S7-*`.
- **S8 — « Stationnement allégé »** : FAIT. Couche renommée « Stationnement allégé — TCSP
  (art. L151-36) » ; la ZONE des 800 m est DESSINÉE (rayon en tireté + parcelles couvertes
  teintées — 24 466 parcelles matérialisées côté ingestion, servies en `tcsp_zone`) ; « i » en
  français métier (« moins de parking à construire = plus de surface vendable ») ; captures sur
  les 4 fonds `S8-tcsp-{sombre,clair,plan,ortho}`.
- **S9 — une couche lignes électriques** : FAIT. « Lignes électriques (HTA / HTB) » : HTA (EDF,
  trait fin) et HTB (BD TOPO, trait épais) sous UNE entrée (l'entrée « moyenne tension » séparée
  n'existe plus — mesuré 1 avant / 0 après), légende à deux styles avec les deux sources et les
  deux millésimes. Capture `S9-lignes-electriques`.
- **S10 — un seul accordéon Attention** : FAIT. L'outil procédure PLU porte UN accordéon
  « Attention (2) » (périmètre/simulation + recalcul à blanc) ; le second accordéon du moteur M15
  est supprimé ; le fait « procédure en cours » reste hors accordéon. Captures `S10-*`.
- **S11 — toiture au seuil de confiance** : FAIT. La confiance = « masse expliquée » de
  l'histogramme d'orientation (pics ± 1 secteur), calculée en production comme au prototype.
  **Seuil gravé : 0,70 — 0 faux sur les 20 bâtiments contrôlés à l'œil, CONFIRMÉ sur 50** (les
  deux faux restants de l'extension — une croupe et un bâtiment en L lus « double pente » —
  tombent à 0,672 et 0,698, sous le seuil ; les faux du jeu initial étaient à 0,402/0,420/0,589).
  **Précision au seuil : 18/18 servis corrects (100 %) · couverture : 18/50 = 36 %.** Sous le
  seuil : « non déterminée (LiDAR) » — le verdict brut reste en cache (mesure), jamais servi ; la
  pente médiane (mesure directe) reste servie. La nature du toit entre DANS la grille des faits de
  la fiche soleil (« Nature du toit », à côté d'« Orientation du bâti », visible sans clic) ; le
  « i » dit la méthode et le seuil. Vérifié en vif : 0,694 → « non déterminée (LiDAR) », 0,828 →
  « simple pente ». Captures `S11-fiche-toit-servi` (BD0800) / `S11-fiche-toit-non-determine`
  (AZ0290 — servie « simple pente » avant, « non déterminée » après).

## Recette

- Suite pytest : **2 304 passed, 1 failed** — l'échec (`test_front_reliquats::test_r5_etudier_deux_marges`)
  est PRÉ-EXISTANT (chaîne absente dès la base `b222d00f`, constaté aux mandats précédents, hors
  périmètre). Nouveaux tests `test_retours14_carte.py` (4 : rattachement à cheval, démote
  d'adresse, geom_simple, tcsp_zone servi) et `test_retours14_outils.py` (3 : seuil S11).
- vitest : 170 passed (le « i » Transport garde le renvoi vers Axes — test P5 réparé après ma
  première rédaction). `tsc` : 0 erreur. Build : OK.
- Golden : le décalage 48 FAIL pré-existant (libellé score_v2 `bc142e4f`, réf non régénérée —
  constaté dès RETOURS-13) est inchangé ; aucun fichier scoring touché par ce mandat.
- Sentinelle : le « Cadastre d'époque » entre au catalogue des sources (78) avec sa raison de
  non-surveillance (archives immuables) — test compteur 68 → 69.

## Notes d'exploitation

- `python -m labuse.ingestion.cadastre_historique` : ré-exécutable (idempotent) ; les millésimes
  Etalab/PCI sont des ARCHIVES immuables, aucune cadence de rafraîchissement nécessaire.
- `via_permits_geo` (viabilisation) a été reconstruite après le rattachement S5 : les permis
  récupérés alimentent le signal M-VIA et le bloc « Permis à proximité » des fiches.
- Le cache `toiture_lidar` a été purgé (colonne `confiance` ajoutée) : chaque fiche soleil
  recalcule à la première demande (~1 s WMS), puis cache.
