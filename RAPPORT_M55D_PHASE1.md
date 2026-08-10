# RAPPORT M55-D — PHASE 1 (mesure) : classification TRI / MODE / PRÉ-RÉGLAGE

Branche `feat/m55-d-filtres` (base `main` de5ad59c, **M55-C mergé — précondition vérifiée**).
**PHASE 1 = MESURE SEULE. Aucun code produit. STOP pour validation Vic avant la phase 2.**

Sources : `store/useApp.ts` (type `Filters`), `lib/filters.ts` (URL/chips), `lib/api.ts`
(`filterParams`/`tiersParam`/`getFiltre`), backend `src/labuse/api/app.py` (`/filtre` L1504,
`_q_v2_where` L797, modèle `FiltreCriteres` L1057). Vérif fonctionnelle : appels `/filtre` réels.

---

## Constat central (change la cible)

**Presque TOUT est du TRI.** Le backend `/filtre` accepte 42 paramètres — **tous consommés
(aucun mort)** — et **41 sont des `WHERE` sur des colonnes du run servi** (instantané, réversible,
zéro recalcul). Les seules exceptions :

- **`analyseLabuse`** (interrupteur « appliquer le classement ») — **n'existe PAS au backend**.
  C'est un toggle FRONT qui change la valeur du paramètre `tiers` envoyé :
  ON → tiers de l'analyse (hors exclusions dures) ; OFF → toute la trame (écartées incluses).
  Preuve : `lib/api.ts` `tiersParam()` L115-118. → **MODE** (mode de lecture), mais mécaniquement
  un simple changement de `WHERE tier`.
- **Curseur Mode B** (`modeB.travauxM2/loyerM2/rendementPct`) — envoyé SEULEMENT avec
  `mode_b_rentable=true` (`filterParams` L96-101), il **change la FORMULE** de rentabilité côté SQL
  (`app.py` L1041-1052). → **le seul vrai paramètre d'analyse/recalcul** piloté par l'UI.

**Il n'y a donc pas, aujourd'hui, de « moteur » que les filtres reconfigurent** : le run est figé
(`source` = run servi, non exposé comme filtre), les tiers sont déjà calculés, et chaque critère ne
fait que **narrower** le résultat. La cible « Mode d'analyse » du mandat doit être lue à cette aune
(voir §Plan / questions).

---

## Tableau de classification (exhaustif)

Légende catégorie : **TRI** = WHERE sur colonne du run servi · **MODE** = change l'analyse/lecture ·
**PRÉ-RÉGLAGE** = pose un lot de critères · **AUTRE**. Doublon = éditable dans les DEUX banques.
Tous **fonctionnent** (Δ compte mesuré sur Saint-Paul, run q_v8_calibre, base 51 129).

| Critère (champ `Filters`) | Panneau(x) | Catégorie | Preuve (param → SQL) | Doublon | Fonctionne (Δ) |
|---|---|---|---|---|---|
| `tiers` (Verdict/Scoring + Déclassées) | Header + Panneau (presets) | **TRI** (nuance mode) | `tiers` → `WHERE s2.tier = ANY()` app.py L836 | **Oui** | oui |
| `analyseLabuse` (interrupteur) | Panneau | **MODE** | front `tiersParam` L115 (swap du set `tiers`) | non | oui (bascule le compte vers la trame entière) |
| `scoreMin` (POTENTIEL ≥/100) | Header | TRI | `score_min` → `d.q_score >=` L851 | non | oui (−50 935) |
| `surfaceMin` / `surfaceMax` | **Header + Panneau** | TRI | `surface_min/max` → `p.surface_m2` L854/857 | **Oui** | oui (−41 307) |
| `sdpMin` | **Header + Panneau** | TRI | `sdp_min` → `parcel_residuel.sdp_residuelle_m2 >=` L860 | **Oui** | oui (−46 324) |
| `sdpMax` | Panneau | TRI | `sdp_max` → `… <=` L909 | non | oui (−30 700) |
| `flags` (Contraintes/risques) | **Header + Panneau** | TRI | `flags` → `EXISTS parcel_flags` L870 | **Oui** | oui (−43 892) |
| `flagsExclus` | *(copilote seul)* | TRI | `flags_exclus` → `NOT EXISTS` L876 | non | oui |
| `evenement` (BODACC) | Header | TRI | `evenement` → `EXISTS cascade … rouge` L864 | non | oui |
| `veille` (succession) | **Header + Panneau** | TRI | `veille` → `EXISTS parcel_veille_succession` L849 | **Oui** | oui |
| `horsCopro` | Header | TRI | `hors_copro` → `NOT copro` L847 | non | oui (−536) |
| `communes` (secteur) | *(copilote cadreur)* | TRI | `communes` → `p.commune = ANY()` L833 | non | oui |
| `personneMorale` | *(via proprietaireType)* | TRI | `personne_morale` → `EXISTS parcelle_personne_morale` L889 | non | oui (−38 719) |
| `zonagePlu` (Famille U/AU/A/N) | Panneau | TRI | `zonage` → `parcel_zone_plu.zone_fam` L892 | non | oui (U −14 447 / A −42 031) |
| `zonePlu` (Zone exacte) | Panneau | TRI | `zone_plu` → `upper(zone_lib)=ANY()` L952 | non | oui (sensible au libellé — « UA » = 0 à SP) |
| `constructibilite` | Panneau | TRI | `constructibilite` → tiers + présence zone L913 | non | oui (−45 910) |
| `etatSol` (nu/bâti…) | Panneau | TRI *(cible = MODE ?)* | `etat_sol` → emprise % + tier L932 | non | oui (nu −47 147) |
| `capaciteMin` | Panneau | TRI | `capacite_min` → `sdp ≥ n×70` L946 | non | oui (−47 952) |
| `sousDensite` | Panneau | TRI | `sous_densite` → `parcel_residuel.sous_densite` L957 | non | oui (−40 098) |
| `multMin` (proba ×N) | Panneau | TRI | `mult_min` → `s2.mult_base >=` L959 | non | oui (−47 647) |
| `rangMax` (têtes rang P) | Panneau | TRI | `rang_max` → `s2.rang <=` L962 | non | oui (−51 108) |
| `renouvellement` | Panneau | TRI | `renouvellement` → `EXISTS parcel_renouvellement` L965 | non | oui (−43 054) |
| `divisionOr` (O12) | Panneau | TRI | `division_or` → `EXISTS division_or_candidates` L967 | non | oui |
| `proprietaireType` (pm/bailleur/pp) | Panneau | TRI | `proprietaire_type` → EXISTS/NOT EXISTS L969 | non | oui (pm −38 719) |
| `etatSociete` | Panneau | TRI | `etat_societe` → EXISTS bodacc/enrichment L982 | non | oui (radiée −51 063) |
| `copro` (avec/sans) | Panneau | TRI | `copro` → `s2.copro` L997 | non | oui (sans −536) |
| `npnru` | Panneau | TRI | `npnru` → `EXISTS anru_quartiers (commune)` L1003 | non | oui (SP=0 : légitime, hors 6 communes ANRU) |
| `adresseAbsente` | Panneau | TRI | `adresse_absente` → `NOT EXISTS adresse_parcelles` L1005 | non | oui (−29 683) |
| `budgetMax` (Mon budget) | Panneau | TRI | `budget_max` → `score_e.charge_supportable <=` L1008 | non | oui |
| `chargeMin` / `chargeMax` | Panneau | TRI | `charge_min/max` → `score_e.charge_supportable` L1014 | non | oui (chmin −44 809) |
| `prixMarcheMin` / `prixMarcheMax` | Panneau | TRI | `prix_marche_min/max` → `v_parcel_dvf_last.prix_m2_terrain` L1022 | non | oui (−48 428) |
| `marcheFiable` | Panneau | TRI | `marche_fiable` → `EXISTS dvf_secteur_medianes n≥3` L1030 | non | oui (−1 222) |
| `caMin` (bilan CA) | Panneau | TRI | `ca_min` → `sdp × prix_m2_neuf >=` L1035 | non | oui (−50 631) |
| **`modeBRentable` + curseur Mode B** | Panneau | **MODE** (recalcul) | `mode_b_rentable` + `modeb_*` → formule L1041-1052 | non | oui (−44 157 ; le curseur change le résultat) |
| **Pré-réglages** « Vous cherchez ? » (nu/bâti/les deux) | Panneau | **PRÉ-RÉGLAGE** | `setFilters` etatSol (TRI) + emphase Mode B (MODE) FiltreLabuse L233 | — | pose des critères visibles |
| **Pré-réglages** « Terrain nu constructible » / « Prêt à démarcher » | Panneau | **PRÉ-RÉGLAGE** | `setFilters({…})` bundle (tiers+flags+etatSol+sdpMin+proprio) L314 | — | oui |
| Sections « Constructibilité / Surface / SDP / Capacité / Zonage… » | Panneau | *(regroupements de TRI)* | conteneurs UI, pas de logique propre | — | — |
| **« Mes vues »** | Panneau | **AUTRE** (voir §) | `saveSearch(nom, filtersToHash(...))` L159 | — | oui, mais **partiel** |

*(Aucun critère CASSÉ ni MORT trouvé : les 42 params backend sont consommés, et le compte bouge
pour chacun. `npnru`/`zone_plu=UA` rendent 0 sur Saint-Paul pour des raisons de DONNÉES, pas de bug.)*

---

## Trois findings qui pèsent sur la cible

1. **Persistance partielle (URL + Mes vues + veilles).** `filtersToHash` (`lib/filters.ts` L117) ne
   sérialise que **11 champs** : `tiers, scoreMin, surfaceMin/Max, sdpMin, evenement, veille,
   horsCopro, flags, flagsExclus, communes` (+ zone). Les **~24 autres** (constructibilite, etatSol,
   sdpMax, capaciteMin, zonagePlu, zonePlu, **analyseLabuse**, économie, mutation, propriété…) sont
   **SESSION-ONLY** : perdus au rechargement, **non partageables par URL**, et **non sauvegardés par
   « Mes vues » / veilles** (qui appellent `filtersToHash`). → contrainte mandat « URL #f= compatible »
   à tenir, MAIS la couverture actuelle est incomplète — **décision : étendre le hash à tous les
   champs (recommandé) ou garder le sous-ensemble ?**
2. **Les chips du header ne montrent que ce sous-ensemble** (`activeChips` L87 = mêmes 11 champs).
   Donc les filtres posés dans le panneau (constructibilite, etatSol, économie…) **n'apparaissent
   nulle part dans le header** et ne sont dans **aucun badge**. Le « + Filtres (N) » du mandat
   n'existe pas encore (bouton « + Filtre » nu). → la cible « badge N = TOUS les filtres actifs »
   exige d'abord de rendre ces champs visibles.
3. **« Mes vues » ne capture ni le mode ni les filtres du panneau.** Une vue sauvegardée = le
   sous-ensemble URL. Donc `analyseLabuse` (MODE) et l'essentiel du panneau **ne sont pas restitués**.
   → si la cible veut « une vue dit si elle capture tri+mode », il faut d'abord que la sauvegarde
   les capture (aujourd'hui non).

---

## Plan d'implémentation proposé (phase 2) — à valider

**Réalité mesurée** : le « MODE » se réduit à deux choses — `analyseLabuse` (mode de lecture) et le
**curseur Mode B** (hypothèses économiques, seul vrai recalcul). Le reste est du TRI. Le
« Terrain nu / Bâti / Les deux » de la cible est mécaniquement un **TRI** (`etatSol`, instantané) +
une emphase Mode B. → il faut trancher comment le présenter (question Q1).

**A. « Mode d'analyse »** (contrôle compact, gauche du « + Filtres ») = les vrais MODE :
- **interrupteur « Appliquer le classement LABUSE »** (`analyseLabuse`) — le mode de lecture ;
- **hypothèses Mode B** (curseur travaux/loyer/rendement) dans le popover — le seul recalcul, donc
  l'état de chargement « ça recalcule » y est légitime.
- *(Q1)* le segment « Terrain nu / Bâti / Les deux » : soit ici comme **pré-réglage de mode**
  (pose `etatSol`, honnêtement étiqueté « raccourci »), soit dans « Filtres » comme pré-réglage.

**B. « Filtres »** — un panneau unique, chaque champ **une seule fois** :
- fusionner les doublons (surface, sdp, flags, tiers, veille) — un seul contrôle chacun ;
- header = 3-4 filtres rapides (verdict/tiers, surface, un flag) + « Tous les filtres » ouvrant LE
  panneau ; **badge N = tous les filtres TRI actifs** (nécessite finding 2) ;
- « Réinitialiser » sépare visiblement **filtres** (TRI) et **mode** (analyseLabuse + Mode B).

**C. Pré-réglages** (« Vous cherchez ? », presets) → raccourcis marqués « pré-réglage » qui POSENT
des critères **visibles** (chips), défaisables un par un.

**D. « Mes vues »** → étendre la sauvegarde pour capturer **tri + mode** et le DIRE ; sinon une vue
ment par omission (finding 3).

**Contraintes** : `filters` reste unique (acquis M55-C) ; URL `#f=` — *(Q2)* étendre à tous les
champs (recommandé, sinon les vues/partages restent partiels) en gardant les clés existantes
rétro-compatibles ; aucun critère ne disparaît ; mobile vérifié.

### Questions à trancher (STOP)
- **Q1** — « Terrain nu / Bâti / Les deux » = MODE (comme le mandat le suggère) ou TRI/pré-réglage
  (ce qu'il est mécaniquement) ? De ça dépend le contenu du contrôle « Mode d'analyse ».
- **Q2** — étend-on `#f=` (et donc Mes vues/veilles) à TOUS les champs (fin de la persistance
  partielle) ? Recommandé, mais c'est un changement de format (rétro-compatible en lecture).
- **Q3** — quels 3-4 filtres « rapides » dans le header (proposition : tiers/verdict + surface + 1 flag) ?
- **Q4** — `analyseLabuse` (aujourd'hui non partagé) doit-il entrer dans l'URL/les vues ? (cohérent avec Q2.)

**STOP — j'attends ta validation du plan (et des réponses Q1-Q4) avant toute écriture en phase 2.**

---

## Périmètre
Phase 1 : lecture seule (front + moteur), zéro code. Phase 2 : front uniquement, après validation.
CC ne merge jamais.
