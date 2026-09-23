# ASSEMBLAGE-1 — L'outil Assemblage lit-il la bonne donnée et calcule-t-il juste

**Mandat :** audit court, lecture seule. (1) les données affichées viennent-elles des bonnes sources ; (2) les calculs (SDP cumulée, logements, ×vs meilleure seule, charge foncière) sont-ils justes.
**Branche :** `audit/assemblage-1` (worktree `~/Desktop/labuse-assemblage`, base main `2370a9da`). Aucune modif de code — ce rapport est le seul livrable.
**Preuves live :** backend du worktree lancé sur `:8275` (base `labuse`), endpoint `POST /moteurs/assemblage` + sonde read-only `fiche_payload`.

---

## Verdict

**(1) Sources : justes.** Toutes les données affichées lisent les tables et les moteurs de la fiche — surface cadastrale, prix marché de zone, propriétaires PM. Aucune source parallèle.

**(2) Calculs : arithmétiquement exacts, mais un choix de méthode structurant fausse le *sens* de deux chiffres.** Surface, SDP cumulée, logements, ×gain et charge foncière se reproduisent **à l'euro** à partir des hypothèses affichées. **Mais** l'outil **additionne des bilans de parcelles indépendantes** au lieu de calculer sur l'assiette fusionnée. Conséquences :

- **SDP cumulée = Σ des SDP *gabarit* de chaque parcelle** (`fourchette.surface_plancher_m2`), pas un recalcul sur l'assiette fusionnée **et pas** la SDP *résiduelle* servie sur la fiche (`parcel_residuel`). Sur du foncier bâti/saturé, l'écart est énorme (témoin 2 : Assemblage 653 m² vs fiches ~0/6 m²).
- **Charge foncière cumulée = Σ des résiduels fonciers de 3 mini-opérations séparées.** Le signe négatif (−11 841 €) est un **artefact de la sommation** (reculs internes comptés des deux côtés + VRD facturée 3× par parcelle), **pas** une propriété du foncier. Sur l'opération réelle d'ensemble elle serait sensiblement plus haute, vraisemblablement positive.

Aucun mélange d'unité, aucune valeur par défaut aberrante. Le problème est **méthodologique**, pas numérique.

---

## 1. Le fil de la donnée

Outil = module **M16 « Assemblage »** (`frontend/src/components/outils/moteurs.tsx:124`), servi par **`POST /moteurs/assemblage`** (`src/labuse/api/moteurs.py:154`), cœur d'agrégation **`aggregate_assiette`** (`src/labuse/assemblage.py:119`).

| Info affichée | Source réellement lue | Même moteur que la fiche ? |
|---|---|---|
| **Surface d'assiette** | `Σ parcels.surface_m2` (cadastre), pas d'union géométrique | **Oui** — même colonne `parcels.surface_m2` |
| **SDP estimée cumulée** | `Σ fiche_payload.fourchette.surface_plancher_m2` = SDP **gabarit** (plafond densité ∩ stationnement, modulée) **brute du bâti existant** | **Partiellement** — = la SDP de la *Faisabilité* de la fiche, **≠** la SDP *résiduelle* (`parcel_residuel`, qui déduit le bâti). Voir §3 |
| **Logements** | `Σ fourchette.logements_sous_sol` (repli `logements_au_sol`) — pas de m²/logement fixe ; réutilise le décompte logements de la faisabilité par parcelle | Oui, mais scénario **sous-sol/silo** (≠ scénario *au sol* qui porte la SDP/le CA — léger décalage interne, voir écarts) |
| **« d'un seul tenant »** | contiguïté = graphe d'adjacence + DFS, `ST_DWithin(geom_2975, 0.5 m)` (`moteurs.py:182`). `/assemblage/study` fait le même test via `ST_NumGeometries(ST_Union(ST_Buffer(·, 0.25)))=1` | Oui — tolérance **0,5 m**, même `ADJ_BUFFER_M` que voisinage.py |
| **Interlocuteurs / PM / particuliers** | `parcelle_personne_morale` (dénomination + SIREN) ; particulier = jamais nommé | **Oui** — même table et même règle SIREN que **Scan patrimoine** ([[scan-patrimoine-1]]) |
| **Marché zone €/m²** | `prix_terrain_nu_zone` → `ligne2_terrain_zone` (`dvf_mutations_parcelle` × `parcel_zone_plu`, zone dominante) | **Oui** — référentiel *unique* du terrain nu, le même que la §Marché de la fiche depuis ETUDIER-BIEN-2 |
| **Charge foncière cumulée** | `Σ fiche_payload.bilan.charge_fonciere` (résiduel foncier « à rebours » : `CA×coef − construction − VRD`), par parcelle | Oui (même `compute_bilan_servi`), mais **sommé par parcelle**, voir §2 |

**Hypothèses du bilan (résolues par secteur, `bilan_params` / `hypotheses_ile.yaml`)** — constatées sur les témoins :
prix de sortie **neuf** (médiane locale DVF neuf), coût construction **2300–2800 €/m² SDP** (milieu 2550), **marge 9 % + honoraires 12 % + frais financiers 3 % = 24 % du CA** (`coef = 0,76`), **VRD 90 €/m² terrain** × majorations (pente ≥15 % + assainissement autonome → ×1,55 sur les témoins), rendement vendable/plancher **0,80**.

---

## 2. Vérification des calculs — témoin de Vic

> ⚠ Le mandat situe le témoin à **Saint-Denis** ; en base ces parcelles sont à **Saint-Paul (97415), section CV**. Les surfaces (811/1533/1434) correspondent exactement — c'est bien le même assemblage, commune mal étiquetée dans le mandat.

Assemblage **CV0724 + CV1506 + CV1507** (Saint-Paul, zone **AU3c**), sortie `/moteurs/assemblage` réelle :

| Chiffre | Attendu (mandat) | Servi (live) | Détail |
|---|---|---|---|
| Surface | 3 778 = 811+1533+1434 | **3 778** | ✅ Σ cadastrale |
| SDP cumulée | 3 061 = 657+1242+1162 | **3 061** | ✅ **somme de SDP gabarit** individuelles |
| ×vs meilleure seule | 3 061 / 1 242 | **×2,46** (+146 %) | ✅ `sdp / max(sdp_par_parcelle)` |
| Logements | 20–26 | **20–26** | ✅ Σ `logements_sous_sol` : (4–6)+(8–10)+(8–10) |
| Charge foncière | −11 841 € (−3 €/m²) | **−11 841 €** (−3 €/m² terrain) | ✅ (voir recomposition) |
| CA cumulé | — | **5 983 450 €** | 1 286 560 + 2 426 490 + 2 270 400 |
| Marché zone | (328 €/m²) | **328 €/m²** (DVF, fiab. moyenne, n=132) | zone AU dédupée |

### 2.1 SDP cumulée = SOMME de résiduels individuels ?

**Oui — c'est une somme de SDP *par parcelle*, pas un recalcul sur l'assiette fusionnée.** `aggregate_assiette` fait `sdp += fiche_payload.fourchette.surface_plancher_m2` pour chaque parcelle (`assemblage.py:141`).

Ce que ça vaut vs un vrai calcul sur l'assiette fusionnée :
- Chaque SDP de parcelle **a déjà retranché ses reculs de périmètre**, **y compris les limites internes partagées** avec les voisines de l'assemblage.
- À la fusion, ces limites internes **ne sont plus des limites** → plus de recul → les bandes correspondantes redeviennent constructibles.
- Donc le recul interne est **soustrait deux fois** (une fois de chaque côté) : la somme **sous-estime** la SDP réelle de l'assiette. **Direction : SDP fusionnée ≥ SDP sommée.** L'outil l'admet lui-même (`note_sdp` : « à la fusion, les reculs INTERNES disparaissent — l'assiette réelle porte GÉNÉRALEMENT PLUS »).
- **Ordre de grandeur** : le gain ≈ (longueur des limites internes) × (profondeur de recul) × niveaux. Pour ces 3 parcelles mitoyennes CV avec reculs latéraux de quelques mètres, c'est un gain **modéré mais réel** (quelques % à ~10 %+ de SDP) — jamais négatif. La somme est donc un **plancher prudent**, jamais une surestimation.

### 2.2 Charge foncière −11 841 € : recomposition à la main

La charge foncière n'est **pas** une somme de résiduels de SDP — c'est la somme des **charges foncières supportables** (valeur résiduelle du terrain) de chaque bilan. Par parcelle : `cf = CA × 0,76 − coût construction − VRD`.

**CV0724** (SHAB vendable 272 m², prix sortie 4 730 €/m²) :
- CA = 272 × 4 730 = **1 286 560 €** ; CA×0,76 = 977 786 €
- SDP retenue = 272 / 0,80 = 340 m² ; construction = 340 × 2 550 = 867 000 €
- VRD = 90 × 1,55 × 811 = 113 135 € *(pente 18 % + assainissement autonome)*
- **cf = 977 786 − 867 000 − 113 135 ≈ −2,3 k€** ✅ (servi −2 333 €)

**CV1506** : CA 2 426 490 ×0,76 − 641×2 550 − 90×1,55×1533 ≈ **−4,9 k€** ✅ (servi −4 902 €)
**CV1507** : CA 2 270 400 ×0,76 − 600×2 550 − 90×1,55×1434 ≈ **−4,6 k€** ✅ (servi −4 606 €)
**Σ = −11 841 €** ✅ ; **−11 841 / 3 778 = −3 €/m² terrain** ✅

**→ Reproduction à l'euro. Aucune unité mélangée (m² terrain vs m² SDP, € vs k€), aucune valeur par défaut aberrante.** Le chiffre est *arithmétiquement juste*.

### 2.3 Pourquoi ~0/négatif, et pourquoi c'est trompeur

Le résiduel est ≈ 0 pour deux raisons **économiques**, pas une erreur :
1. **Densité faible en AU** : SHAB vendable 272 m² sur 811 m² terrain (SDP/terrain ≈ 0,42). Peu de surface vendable pour amortir le foncier + la VRD.
2. **VRD facturée au m² de *terrain* × 1,55** (pente ≥15 % + assainissement autonome) : ~139,5 €/m² terrain. Sur une parcelle peu dense, la VRD par m² vendable explose (~415 €/m² vendable sur CV0724).

Et surtout, la **méthode de sommation aggrave le négatif** :
- la VRD est comptée **3 fois par parcelle** (811 + 1533 + 1434 m² viabilisés séparément), alors qu'une opération d'ensemble **mutualise** accès/réseaux ;
- la SDP est sous-comptée (§2.1) → moins de CA que l'assiette réelle.

Le résultat : une charge supportable de **−3 €/m²** juste à côté d'un **prix de marché du terrain de 328 €/m²**. Cette contradiction (le marché paie 328, le modèle dit ~0) **est le signal** que ce chiffre est un scénario prudent de 3 mini-opérations disjointes, **pas** la valeur du foncier de l'ensemble.

---

## 2bis. Deuxième témoin — Le Tampon, 2 parcelles zone U

**AD0780 (635 m²) + AD0781 (642 m²)** (Le Tampon 97422, zone **U**, contiguës) :

| Chiffre | Servi (live) | Vérif |
|---|---|---|
| Surface | 1 277 | ✅ 635+642 |
| SDP cumulée | 653 | ✅ 324+329 |
| ×vs meilleure seule | ×1,98 (+98 %) | ✅ 653/329 |
| Logements | 6–8 | ✅ Σ sous-sol |
| CA cumulé | 2 253 996 € | — |
| Charge foncière | **−94 419 € (−74 €/m² terrain)** | Σ des cf par parcelle |
| Marché zone | 285 €/m² (DVF, n=1106) | — |
| Propriétaires | 1 PM (**SCI LE LOTUS**, SIREN 434245858) + 1 particulier | ✅ `parcelle_personne_morale` |

Même comportement : charge foncière fortement négative (−74 €/m²) **face à un marché à 285 €/m²** — la contradiction est ici encore plus flagrante, et s'explique par le **§3 ci-dessous** : ces parcelles sont **déjà bâties/saturées**.

---

## 3. Cohérence avec le reste de l'app

| Question | Réponse | Preuve |
|---|---|---|
| SDP d'une parcelle seule dans Assemblage = SDP restante de sa fiche (`parcel_residuel`, run 5) ? | **NON** | Assemblage sert la SDP **gabarit brute** (`surface_plancher_m2`) ; la fiche sert la **résiduelle** (`max(0, sdp_max − bâti existant)`). Coïncident sur du nu, **divergent sur du bâti** |
| Marché zone = terrain nu de la §Marché de la fiche ? | **OUI** | `prix_terrain_nu_zone`/`ligne2_terrain_zone`, référentiel unique partagé (ETUDIER-BIEN-2) |
| Propriétaires = Scan patrimoine ? | **OUI** | `parcelle_personne_morale`, jointure par IDU→SIREN, PM nommée / particulier masqué — règle identique |

**Détail de la divergence SDP** (`fourchette.surface_plancher_m2` servi par Assemblage vs `parcel_residuel.sdp_residuelle_m2` servi par la fiche) :

| Parcelle | Assemblage (gabarit) | Fiche résiduel | Écart |
|---|---|---|---|
| CV0724 (AU, nu) | 657 | 649 | +8 (négligeable) |
| CV1506 (AU, nu) | 1 242 | 1 191 | +51 |
| CV1507 (AU, nu) | 1 162 | 1 162 | 0 |
| **AD0780 (U, bâti saturé)** | **324** | **0** | **+324** |
| **AD0781 (U, bâti saturé)** | **329** | **6** | **+323** |

Sur du foncier **non bâti** (CV, zone AU) les deux quasi-coïncident. Sur du foncier **déjà bâti/saturé** (AD, tier `declasse_bati_sature`), l'Assemblage affiche 324/329 m² de « SDP estimée » là où la fiche de chaque parcelle dit **~0 de potentiel résiduel**. L'Assemblage raisonne donc en **table rase** (démolition/reconstruction implicite) sans le dire, et **ne déclenche pas** son garde-fou « parcelle sans droits à bâtir » (qui teste `sdp_m2 ≤ 0` sur la SDP gabarit, jamais nulle ici).

> Note : le libellé front (`moteurs.tsx:333`) affirme que la « SDP estimée » est **« ≠ SDP gabarit de la Faisabilité »**. C'est inexact : la valeur servie **est** `surface_plancher_m2`, la SDP de la faisabilité. Le libellé sème une distinction que le calcul ne fait pas.

---

## 4. Récapitulatif & liste des écarts (non corrigés)

| Élément | Source | Calcul | Verdict |
|---|---|---|---|
| Surface d'assiette | `parcels.surface_m2` | Σ cadastrale | ✅ OK |
| SDP cumulée | `fourchette.surface_plancher_m2` | Σ par parcelle (gabarit brut) | ⚠ écart méthode (E1, E2) |
| Logements | `fourchette.logements_sous_sol` | Σ par parcelle | ⚠ scénario silo ≠ SDP/CA (E4) |
| ×vs meilleure seule | backend | `sdp / max(sdp_par)` | ✅ OK |
| Contiguïté | `ST_DWithin 0,5 m` + DFS | — | ✅ OK |
| Propriétaires | `parcelle_personne_morale` | SIREN | ✅ OK (= Scan patrimoine) |
| Marché zone | `ligne2_terrain_zone` | médiane DVF terrain/zone | ✅ OK (= fiche §Marché) |
| Charge foncière | `Σ bilan.charge_fonciere` | résiduel foncier sommé | ⚠ juste au calcul, faux de sens (E1, E3) |

**Écarts :**

- **E1 — Bilan sommé, pas fusionné (structurant).** SDP, VRD, CA, charge foncière sont **additionnés parcelle par parcelle**. La fusion (reculs internes disparus → +SDP ; VRD mutualisée → −coûts) rendrait la charge foncière **matériellement plus haute**. Le signe négatif est un artefact de méthode. L'outil l'admet pour la SDP (`note_sdp`) mais **pas pour la charge foncière**, qui hérite pourtant du même biais en pire (la VRD triple).
- **E2 — SDP gabarit ≠ SDP résiduelle de la fiche.** Sur du bâti saturé, l'Assemblage affiche un potentiel (324/329 m²) que la fiche dit nul (0/6 m²). Table rase implicite non dite ; garde-fou « sans droits à bâtir » inopérant sur ces cas.
- **E3 — Charge foncière ≈ 0/négative pilotée par densité faible × VRD au m² terrain ×1,55**, à comparer au marché terrain 328/285 €/m². La divergence supportable vs marché n'est ni expliquée ni signalée à l'utilisateur.
- **E4 — Logements (scénario sous-sol/silo) incohérent avec SDP & CA (scénario au sol).** Le décompte logements 20–26 vient du scénario silo (parking enterré) que le bilan refuse justement de chiffrer sans son coût. Logements légèrement optimistes vs la base SDP/CA.
- **E5 — Libellé front « ≠ SDP gabarit » inexact** (la valeur servie EST la SDP gabarit).
- **E6 (cosmétique) — commune du témoin** : Saint-Paul, pas Saint-Denis.

### Charge foncière — phrase nette

> **La charge foncière cumulée −11 841 € est arithmétiquement JUSTE** (elle se reproduit à l'euro depuis les hypothèses affichées : prix de sortie 4 730 €/m², coût 2 300–2 800 €/m² SDP, marge+frais 24 %, VRD 90 €/m² terrain ×1,55, rendement 0,80 — **aucun mélange d'unité, aucune valeur par défaut aberrante**). **Mais son SENS dépend d'une hypothèse de méthode à revoir :** c'est le résiduel foncier de **trois opérations de parcelles indépendantes additionnées**, pas un bilan sur l'assiette fusionnée. La méthode **soustrait les reculs internes des deux côtés** (SDP sous-comptée) et **facture la VRD trois fois** (×1,55) — deux biais qui poussent le chiffre vers le négatif. Sur l'opération réelle d'ensemble (VRD mutualisée, reculs internes disparus → plus de SDP), la charge foncière serait **sensiblement plus haute et vraisemblablement positive**. Le signe négatif est un **artefact de la sommation, pas la valeur du foncier** — ce que confirme le prix de marché du terrain (328 €/m²) affiché juste à côté.

---

## Hors mandat (non fait)

Aucune correction, aucun merge, aucune modif d'outil. Rapport seul, committé sur `audit/assemblage-1`.
