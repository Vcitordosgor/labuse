# PALIERS-1 — trois paliers vrais, un seul vocabulaire, sur q_v14

**Nature** : refonte de la politique de paliers (étape 4) et de leur présentation (étape 5).
Le modèle ne change pas — `p_raw` de q_v14 est conservé tel quel. **Aucun promote, aucun
merge, aucune écriture `config/served_run.txt`, aucun rescoring.** `q_v11_m137` reste servi ;
Vic bascule lui-même, une fois, avec `golden promote q_v14`.

Branche `feat/paliers-1` (depuis `feat/scoring-4`), worktree `~/Desktop/labuse-paliers1`.
Un commit par lot. Modèle CC : Opus 4.8.

---

## Étape 0

`pwd` = `~/Desktop/labuse-paliers1`, branche `feat/paliers-1`, arbre propre, `git log` porte les
8 commits de scoring-4 (`8a8a8364` = mandat, `398655c3` … `25c27e9a`). Validé.

---

## Lot A0 — les quatre restes du rapport SCORING-4 (commit `811aa570`)

Corrigés **dans les générateurs** (source), artefacts régénérés, et le rapport SCORING-4.md
aligné.

1. **« 608 sorties de Priorité » était faux.** Priorité (brûlante) ne compte que **111**
   parcelles. Le générateur (`q_v14_arene.py churn`) étiquetait « Priorité » la **TÊTE servie**
   = brûlante + chaude = **1 478** (Priorité + À suivre). Corrigé : `TETE_TIERS`, et deux
   chiffres nommés — **608 sorties de la tête servie** (1 478 → 1 206) et **601 sorties du
   top-1158** (churn 51,9 %). Note de version relabellée.

2. **Matrice de migration (88, « zéro depuis Faible ») vs top-50 (n° 3 « Faible »).** Les deux
   ont raison — ils mesurent deux choses différentes.
   - La **matrice** décrit la migration de **tier** : 88 montées en Priorité = **61 depuis
     À suivre + 27 depuis Neutre (a_creuser), ZÉRO depuis une déclassée** (vérifié en base). La
     garde de tête tient : une déclassée ne monte pas en Priorité, même à p fort.
   - Le **top-50** est trié **par rang** (p le plus fort), pas « les 50 premières Priorité ».
     Il inclut **13 déclassées « Faible »** — ex. `97416000CS0269`, rang 3, p 0,60, restée
     `declasse_bati_sature` dans les deux runs, gardée hors Priorité par la garde bâti saturé.
   - **C'est exactement le cas que PALIERS-1 corrige** : le déclassement devient un motif, la
     parcelle garde son palier de probabilité. Générateur corrigé (colonne `palier_q_v14`,
     `montees_par_palier_servi`, titre honnête).

3. **Réserve foncière 8 789 → 5 997.** La réserve est un bucket **relatif** — top-décile de SDP
   résiduelle **ET** p sous la médiane du run. q_v14 la recompose : en classant plus haut ces
   parcelles à forte capacité, il en fait passer **3 083 des 3 116 qui quittent la réserve
   au-dessus de sa médiane p** (la condition « p sous la médiane » ne tient plus) ; **254** de
   plus sont écartées par la cascade élargie — d'où la baisse nette.

4. **Libellés** : `nu_constructible_asof` → « **terrain nu constructible** » ;
   `pct_bati_secteur_asof` → « **secteur peu bâti** » (source `qv14.LIBELLES_QV14` + re-mapping
   des rapports par clé de feature, sans rescoring).

---

## La nouvelle règle (décision Vic, 08/09/2026)

Le palier dit les **chances de vente sous 12 mois**, en probabilité absolue, **hors
copropriété** :

| Palier | Règle | Sens |
|---|---|---|
| **Priorité** | p ≥ 0,20 | une chance sur cinq |
| **À suivre** | 0,10 ≤ p < 0,20 | une chance sur dix |
| **Sans signal** | p < 0,10 | — |
| **Écartée** | cascade (étage 0), inchangée | hors gisement |

- **Copropriété** : hors palier, avec le motif « copropriété ».
- **Anti-churn simple** : au re-score, une parcelle ne descend que si p passe **sous 0,18**
  (Priorité) ou **sous 0,09** (À suivre). Pas d'autre hystérésis, pas de calibrage par rang,
  pas de plancher de capacité dans le palier.
- **Ce qui sort de l'échelle et devient un MOTIF** (fiche, filtrable) : bâti saturé, zone
  fermée, AU fermée, non constructible, bâti révélé. La parcelle **garde son palier de
  probabilité** — une maison saturée à une chance sur cinq est « Priorité » pour un agent, le
  motif dit au promoteur qu'il n'y a pas de projet.
- **Ce qui devient un FILTRE** : réserve foncière (SDP résiduelle dans le décile supérieur),
  indépendant du palier, là où « Long terme » existait.
- **Ce qui disparaît du vocabulaire client** : Long terme, Neutre, Faible, Score V. Le Score V
  reste calculable en base, plus affiché nulle part.

---

## Lot A — mesurer avant d'implémenter (commit `84ca2491`)

Au banc **K0 (test 2025**, ventes réelles à 12 mois, clients LABUSE exclus), q_v14 scoré par son
artefact **gelé** (aucun fit, aucun rescoring). Effectif + précision réelle de Priorité et À
suivre, **avec et sans les anciens déclassements** (`paliers1_lotA.py`).

| Zone | Palier | Variante | Effectif | Précision réelle |
|---|---|---|---|---|
| **île** | **Priorité** | **sans déclassements (règle neuve)** | **119** | **34,4 %** |
| île | Priorité | avec déclassements (règle ancienne) | 50 | 42,0 % |
| île | À suivre | sans déclassements | 416 | 12,7 % |
| île | À suivre | avec déclassements | 239 | 14,2 % |
| Saint-Paul | Priorité | sans déclassements | 11 | 27,3 % |
| Saint-Paul | Priorité | avec déclassements | 6 | 33,3 % |
| Saint-Paul | À suivre | sans déclassements | 62 | 11,3 % |
| Saint-Paul | À suivre | avec déclassements | 38 | 10,5 % |

**Garde-fou chiffré du mandat** : précision de Priorité **sans déclassements** (île) =
**34,4 % ≥ 20 % → VERT.** Feu vert pour le Lot B. Garder les déclassées dans Priorité **double
presque la tête** (50 → 119) **sans faire tomber la précision sous le plancher** (42 % → 34 %) :
la thèse du mandat — « une maison saturée à une chance sur cinq est Priorité pour un agent » —
tient sur données réelles.

*À suivre* : 12,7 % réel, bien dans la bande 10-20 % annoncée (bien calibré, ECE q_v14 ≈ 0,002).

**Churn annuel simulé 2024→2025** (majorant du churn mensuel — le p bouge plus sur un an que
sur un mois) : ~**79 %** hors anti-churn ; l'anti-churn simple (0,18 / 0,09) ne le réduit que de
**~2 points** (Priorité 79,5 % → 77,8 %). Les variations as-of d'une année dépassent de loin la
bande d'hystérésis de 2 points. **Fait rapporté à Vic** : l'anti-churn « simple » voulu par le
mandat borne le churn mensuel (mouvements fins) mais n'empêche pas la rotation de fond du
modèle as-of ; c'est la conséquence assumée de « pas d'autre hystérésis ».

---

## Lot B — la politique (commit `71aeaa29`)

`statuts.assign_paliers` — **fonction PURE de `p_raw`** (hors copropriété), **seuils EN CONFIG**
(`config/scoring_client.yaml → paliers`, jamais en dur). Domaine = 4 valeurs, aucune autre.
Anti-churn simple (entrée stricte, descente tamponnée un cran à la fois). Écartée (cascade
étage 0) prime.

- **Déclassements → MOTIFS** (`statuts.motifs_parcelle` : bâti saturé / zone fermée / AU fermée
  / non constructible / bâti révélé + copropriété), dérivés des mêmes caches que le pipeline —
  plus jamais un tier. La parcelle garde son palier.
- **Réserve foncière → DRAPEAU** (`statuts.reserve_fonciere`, SDP résiduelle décile supérieur),
  indépendant du palier.
- **Recalcul des paliers de q_v14 SEULEMENT** (`paliers1_lotB.py`, idempotent, `p_raw` INTACT) :

| Palier | Effectif q_v14 (toutes parcelles) | dont hors copropriété |
|---|---|---|
| Priorité | 114 | 83 |
| À suivre | 631 | 371 |
| Sans signal | 280 658 | 277 824 |
| Écartée | 150 260 | 149 961 |

Vérifié en base : Priorité `p_raw ∈ [0,215 ; 1,0]`, À suivre `[0,103 ; 0,188]`, Sans signal
`< 0,10` — cohérence palier ↔ p_raw parfaite, `p_raw` inchangé.

- **Pipeline** câblé v2 pour la **recette q_v14 uniquement** ; le servi (m36) et q_v12 gardent le
  tier par rang → **golden servi intact** (vérifié).
- **Registre CIRCUIT** (`regles/tier_opportunite.py`) mis à jour : la règle derrière le calcul.
- **Sonde nocturne 4.7** étendue aux quatre valeurs (`sonde_circuit.py`) : domaine ⊆ 4 valeurs
  + cohérence palier ↔ p_raw selon les seuils config ; **0 écart sur q_v14**.

Gardes : `tests/test_paliers1.py` (11 tests — entrée stricte, anti-churn, motifs, réserve,
« une déclassée garde son palier »).

---

## Lot C — un seul vocabulaire, partout (commit `5545051d`)

Le domaine de `tier_opportunite` est désormais **Priorité / À suivre / Sans signal / Écartée**.
Plus de brûlante / chaude / réserve / à creuser / déclassé, ni de « Long terme / Neutre /
Faible / Score V » — **un seul mapping canonique**, back et front, sans table de traduction
par écran.

- **Serveur** : `scoring/tiers_client.py` — `PALIERS_CLIENT` (4 valeurs) + `CORRESPONDANCE_LEGACY`
  (anciens codes → canonique, **runs jamais réécrits**) ; `court`/`long`/`code_palier`/
  `montre_multiple`. Tous les points de service (`verdict_servi`, `api/scoreur`, `api/projets`,
  `api/assistant`, `api/resume`, `api/export`, `api/modules`, `flash/data`, `veille_plu`) lisent
  cette valeur. Fallbacks legacy « Neutre »/« Faible » purgés.
- **Front** : `lib/status.ts` — `PALIER_META` (4) + `CORRESPONDANCE_LEGACY` + `codePalier` ;
  `TIER_V2_META`/`verdictMeta`/`effectiveTier` résolvent tout code vers le palier canonique.
  `lib/strings.ts` `defTiers` = 4 paliers.
- **×N** (rapport à la moyenne de la commune) : affiché **à côté de Priorité et À suivre
  seulement** (`montre_multiple` / `codePalier` côté fiche).
- **Anciens runs** : la correspondance en lecture les projette sur les 4 valeurs (brûlante →
  Priorité, chaude → À suivre, à creuser / réserve / déclassé → Sans signal, étage 0 → Écartée) ;
  jamais réécrits.

**Forward-compatibilité de la bascule (additive, zéro régression sur le servi).** La *plomberie*
qui filtre / colore / compte par code de tier (carte `MapView`, tri de liste, filtre par défaut,
raccourci « secteur opportunités », tri SQL, et les agrégats backend de tête/servable) reconnaît
désormais **les deux vocabulaires** : anciens codes (run servi) **et** codes v2 (q_v14). On
n'ajoute que les nouveaux codes aux listes existantes — un run ne porte qu'un vocabulaire, l'autre
ne matche rien. Ainsi la carte, les filtres et les compteurs fonctionnent **avant comme après**
`golden promote q_v14`, sans toucher au pipeline de tuiles ni au scoring.

### Le mapping avant / après (déterministe, run servi `q_v11_m137`)

Sur le run servi (anciens codes), la correspondance en lecture change le libellé ainsi — c'est
le « avant / après » de chaque écran qui classe, sur **la même parcelle** :

| Code stocké (run servi) | Avant | Après |
|---|---|---|
| `brulante` | Priorité | **Priorité** |
| `chaude` | À suivre | **À suivre** |
| `reserve_fonciere` | **Long terme** | **Sans signal** (+ drapeau réserve) |
| `a_creuser` | **Neutre** | **Sans signal** |
| `declasse_*` | **Faible** | **Sans signal** (+ motif en fiche) |
| `ecartee` | Écartée | **Écartée** |

Après la bascule `golden promote q_v14`, les codes stockés sont directement
`priorite / a_suivre / sans_signal / ecartee` → mêmes libellés, résolus nativement.
**Le ×N** (rapport à la moyenne de la commune) ne s'affiche plus qu'à côté de **Priorité et
À suivre**.

### Écrans touchés

Tous lisent la valeur via le mapping canonique unique — aucun n'a son propre libellé :

| Écran | Point de lecture |
|---|---|
| Fiche | `verdictMeta`/`PALIER_META` (front) ; ×N gaté (Priorité/À suivre) |
| Carte | `MapView` (coloration + filtre par palier, deux vocabulaires reconnus) |
| Étudier un bien | verdict servi (API) → libellé canonique |
| Projets (Kanban) | `api/projets` `_TIER_LABEL` + filtre palier |
| Radar | `score_v2` → `verdictMeta` |
| Veille / Communes / Marché | `veille_plu` (tiers sursis) ; `marche.tsx` |
| Densifier / Prospection solaire | classement via `verdictMeta` |
| PDF / exports | `api/export`, `flash/data` → `TIER_LABELS` |
| Copilote / Assistant | `api/assistant` `_STATUT_PHRASE`, `api/resume` |

Captures pixel avant/après par écran : prises par Vic sur l'app en marche (le pont MCP/WebGL ne
capture pas au-delà de 5 s). La transformation de libellé est déterministe (table ci-dessus) ;
`tsc`/`vitest`/`pytest` verts tiennent lieu de preuve de non-régression.

**Fichiers** (Lot C, commit `5545051d`) :
- **Mapping canonique** : serveur `scoring/tiers_client.py` ; front `lib/status.ts`,
  `lib/strings.ts`.
- **Libellés servis** : `verdict_servi.py`, `api/{projets,assistant,resume}.py`, `veille_plu.py`
  (fallbacks « Neutre »/« Faible » purgés) ; front `components/fiche/Fiche.tsx` (×N gaté),
  `components/panel/LeftPanel.tsx`, `components/outils/ScoringV2.tsx`.
- **Forward-compat additive** (deux vocabulaires) — front : `components/map/MapView.tsx`,
  `components/fiche/marche.tsx`, `components/panel/{FiltreLabuse,ResultsSection}.tsx`, `lib/api.ts` ;
  serveur (~30 sites de filtre/compte/tri, jamais le scoring) : `api/{app,carnet,events,export,
  ia,modules,moteurs,nl_aggregate,partners,rarete,score_v2,voisinage}.py`, `demo.py`,
  `shortlist.py`, `golden_ops.py`, `filtres/sources.py`, `copilote/moteurs.py`,
  `faisabilite/piscine_signal.py`, `scoring/{lignee_tete,p_v2/monitoring}.py`,
  `registre/moteurs/{commune,plateforme}.py`.
- **Tests** : `test_{m137_vocabulaire,front_reliquats,verdict_servi,scoreur,resume,assistant,
  ux_v1,paliers1}` mis au nouveau domaine.

Vérifié : front `tsc` 0 / `vitest` 191 ; suite backend **2857 passed / 12 failed** (= baseline
pré-existant : weasyprint, base-réelle, stripe/courrier, `ia_log` FK, cerfa, `test_r5_etudier` —
**0 régression nette**).

---

## Effectifs finaux par palier (run q_v14, hors copropriété)

| Zone | Priorité | À suivre |
|---|---|---|
| **île** | 83 | 371 |
| **Saint-Paul (97415)** | 5 | 49 |

(Toutes parcelles, copropriété comprise mais hors palier : Priorité 114, À suivre 631.)

Réserve foncière (drapeau, SDP résiduelle décile supérieur) : indépendante du palier, dérivée à
la lecture (`statuts.reserve_fonciere`) là où le listing « Long terme » existait.

---

## Recette

Une capture **avant / après** par écran qui classe, sur la **même parcelle**, jointe au rapport
(section « Écrans touchés »). La transformation de libellé est déterministe (mapping unique) ;
les captures pixel sont prises par Vic sur l'app en marche (le pont MCP/WebGL ne capture pas
au-delà de 5 s). Preuve DOM et table de correspondance ci-dessus.

## Rapport

Aucune promotion. **Vic bascule lui-même, une fois, avec `golden promote q_v14`** — le run
candidat porte déjà, ensemble, le nouveau modèle (q_v14) et les nouveaux paliers.
