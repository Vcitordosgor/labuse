# Audit court — Suivi de secteur (O7 / carnet-secteur) — 21/08/2026

Constat seul, aucune correction. Branche `audit/suivi-secteur`.

## 1. Branché ? Scopé ? Vide ?
- **Branché, oui.** Endpoints `src/labuse/api/carnet.py` : `GET /carnet-secteur` (liste) + `/{secteur}` (page).
  Tables lues :
  - `parcel_p_score_v2` (`carnet.py:71` liste, `:97` page) — **run-scopé `q_v10_m129`** (`s.run_id = :run`) ✓
  - `parcels` (`:71`, `:90`), `sitadel_permits` (`:123`, permis 24 mois), `commune_conso_enaf` (`:131`, ZAN)
  - `dvf_secteur_medianes` (`:104`), `dvf_prix_sortie_neuf` (`:109`), `parcel_signals` (`:116`) — chacun gardé par `_has`.
- **Sert de la donnée (pas vide côté données)** : 478 secteurs ont des opportunités ; les tables gardées
  SONT peuplées en prod (`dvf_secteur_medianes` 2 359, `parcel_signals` 69 357 ; `dvf_prix_sortie_neuf`
  12 seulement — prix neuf épars, même trou qu'au comparateur). Donc un secteur ouvert affiche stock + prix
  + permis + signaux + ZAN, sourcés.
- **MAIS aucun ÉTAT** : l'outil n'écrit RIEN (100 % SELECT). Pas de secteur « enregistré » (cf. §3).

## 2. Que fait-il ? (client vs calcul, le nom)
- **En une phrase client** : « Mon secteur (une section cadastrale) suivi comme un portefeuille — stock,
  prix, permis, signaux, tout sourcé. »
- **Ce que le calcul dit vraiment** : un AGRÉGAT EN LECTURE par micro-secteur (`left(idu,10)` = INSEE + 000
  + section) — zéro donnée nouvelle, tout est déjà en base. C'est un **tableau de bord de consultation**.
- **Le nom ne correspond PAS tout à fait.** « **Suivi** de secteur » promet un suivi (abonnement, alertes,
  digest). Or le code le dit lui-même (champ `note`, `carnet.py:37`) : « l'abonnement (digest hebdo, compte)
  n'est pas encore actif ; le carnet se consulte à la demande. » Il n'y a **aucun suivi** — juste une
  consultation ponctuelle. Nom fidèle = « **Fiche de secteur** » / « **Secteur en un coup d'œil** ».

## 3. Combien de secteurs / d'utilisateurs ?
- **Secteurs enregistrés par l'outil : 0.** Le carnet ne persiste rien. Les tables d'ancrage citées dans sa
  doc (`watch_zones` 3 lignes, `watched_parcels` 7 lignes) appartiennent à la **Veille**, PAS au carnet — il
  ne les écrit ni ne les lit.
- **Usage mesurable : aucun** (pas d'instrumentation par endpoint ; `usage_compteurs` = rate-gel, sans route).
- **Verdict pratique** : outil **sans état et sans usage traçable** — il produit une vue à la demande, mais
  personne n'y « a un secteur ». En pratique : un rapport consultable, pas un portefeuille suivi.

## 4. Recouvrements
- **Veille (ex-Surveillance) — RECOUVREMENT FORT.** La Veille SUIT activement des parcelles/zones
  (`events.py` `watch_toggle`→`watched_parcels`, `watch_zones`) + des veilles de critères (`copilote_v2.py`
  `veilles_lister/_executer_veille`) et les CONFRONTE aux bascules (`events.py:510 _veilles_match`) → alertes
  (la cloche). **Le « suivi » que le NOM du carnet promet, c'est exactement ce que fait la Veille** — et la
  doc du carnet (`carnet.py:13`) dit que son futur abonnement s'ancrerait sur `watch_zones`/`watched_parcels`,
  soit les tables de la Veille. Le carnet n'ajoute que la VUE-instantané d'un secteur ; son bloc « signaux de
  veille » lit `parcel_signals`, les mêmes signaux que la Veille surface.
- **Rejeu des projets M120 — recouvrement PARTIEL.** Un projet = un jeu de filtres `FiltreCriteres` figé +
  shortlist + rejeu daté (ajoutées/sorties). Un projet scopé sur une commune/zone couvre un « secteur suivi
  dans le temps », en plus riche (n'importe quel critère + diff de rejeu). Le carnet, lui, est figé sur UNE
  section géographique. **Un projet peut subsumer un suivi de secteur.**
- **Alertes de bascule (/events, réparées) — recouvrement PARTIEL/complémentaire.** Les bascules sont les
  CHANGEMENTS d'état par parcelle → alertes ; le carnet montre le STOCK courant (instantané). L'ex-« Quoi de
  neuf » montrait déjà les bascules par secteur. Le carnet = photo ; les bascules = deltas — deux vues du
  « qu'est-ce qui bouge sur ce secteur ».

## 5. LIMIT caché ? Vestiges de matrice ?
- **LIMIT caché : OUI.** La liste plafonne à **30** (`carnet.py:59` `limit=Query(30…)`) ; le front appelle
  `/carnet-secteur` sans param → 30 par défaut, et **ne le dit pas** (`blocB.tsx:251`, aucun « 30 sur N »,
  pas de « voir plus »). Il existe **478** secteurs à opportunités → **30 affichés sur 478, en silence**.
  (Le 6ᵉ outil de la semaine avec un plafond muet.)
- **Vestiges de matrice : AUCUN.** Ni `q_score`, ni `a_score`, ni `matrice_statut` dans `carnet.py` ni dans
  `O7Carnet`. Propre.

## Synthèse
Outil **propre** (pas de matrice) et **branché** (données réelles, run-scopé), mais : (a) son NOM promet un
suivi qu'il ne fait pas (consult-only ; le suivi = la Veille) ; (b) **0 état / 0 usage traçable** ; (c) un
**plafond muet à 30/478** ; (d) **recouvre la Veille** (le suivi), partiellement les **projets M120** (le
portefeuille dans le temps) et les **bascules** (ce qui bouge). Sa seule valeur PROPRE et vivante = la
**vue-instantané agrégée d'une section** (stock+prix+permis+signaux+ZAN en un écran). À toi de décider.
