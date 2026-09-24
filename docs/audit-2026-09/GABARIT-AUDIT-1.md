# GABARIT-AUDIT-1 — L'outil Gabarit réglementaire : juste, raccordé, complet ?

Audit court, **lecture seule**, après la chaîne GABARIT-1→6 + couverture (mergée dans `main` `c6073ff3`).
Branche `audit/gabarit-audit-1`, worktree `~/Desktop/labuse-gabaudit`. Aucune modification de code
applicatif ; aucun merge. Sonde jetable rejouable : `docs/audit-2026-09/gabarit-audit-1/verif_gabarit.py`
(exécute le **même** moteur que l'endpoint `GET /outils/gabarit/{idu}` — `build_gabarit_input` +
`compute_gabarit` — plus, en regard, `parcel_faisabilite` et la contenance cadastrale).

## Étape 0
`pwd` = `/Users/openclaw/Desktop/labuse-gabaudit` · branche `audit/gabarit-audit-1` · arbre propre. OK.

## Chaîne de la donnée (rappel, pour lire les écarts)

| Valeur outil | Champ API | Source réelle |
|---|---|---|
| Surface parcelle | `surfaceParcelleM2` | `ST_Area(geom_2975)` — **mais réécrite** à la portion de la zone constructible dominante si la parcelle est à cheval (`builder.py:222-223`) |
| Zone d'implantation | `zoneImplantationM2` | moteur géométrique : morceau − reculs par côté (bufferisés) − exclusions PPR rouge (`engine.py:80-93`) |
| Plafond d'emprise | `plafondEmpriseM2` / `…Status` | `surface × CES%` ; `absent` = silence prouvé du règlement (`builder.py:268-285`) |
| Hauteur réglementaire | `hauteurReglementaireM` | **faîtage** `hf_m` de la zone (`builder.py:249`), sinon égout `he_m` cité comme tel |
| Reculs (voie / sép.) | `appliedRules[limite-*]` | `resolve_zone` (config `plu_destinations/*.yaml`) × classification des limites v2 (`limites.py`) |

Le **règlement validé** est lu dans `config/plu_destinations/{insee}_*.yaml` (feuilles `statut: valide`,
chaque valeur citée à son article), pas dans `plu_reglement_extrait` (verbatim brut) — c'est la même
source que la fiche pour les reculs/hauteur/CES.

---

## 1. Les trois contradictions relevées par Vic

### 1.a — BW0102 (Saint-Paul, U6c) : « 7 465 m² » (outil) vs « 1,03 ha » (fiche)

`97415000BW0102` : contenance cadastrale **10 320,9 m²** (`parcels.surface_m2` = `ST_Area(geom_2975)`,
identiques). La parcelle est **à cheval sur trois zones** (vérifié en base) :

| Zone | m² | % |
|---|---|---|
| **U6c** (constructible) | **7 465,4** | 72,3 % |
| A (agricole) | 2 494,3 | 24,2 % |
| N (naturelle) | 361,2 | 3,5 % |

Le builder, quand une parcelle est à cheval **avec une seule zone constructible**, recalcule tout sur
**le morceau constructible** : `surface = cons[0]["area"]` et `geom = cons[0]["gj"]` (`builder.py:220-223`).
D'où **7 465 m²** = la portion U6c. La fiche, elle, affiche la **contenance cadastrale DGFiP** entière
(`Fiche.tsx:787`, « Contenance cadastrale de la parcelle »).

| Info | Valeur outil | Valeur fiche | Source outil | Source fiche | Qui a raison | Cause de l'écart |
|---|---|---|---|---|---|---|
| Surface | 7 465 m² | 1,03 ha (10 321 m²) | portion U6c du découpage multi-zones | contenance cadastrale entière | **Les deux, pour leur usage** | l'outil clippe à la zone servie ; le libellé « Surface parcelle » masque que c'est la portion U |

**Verdict 1.a** : aucun chiffre n'est faux. L'outil calcule légitimement sur la portion constructible
(sinon le gabarit serait faux). **Le défaut est de présentation** : appeler « Surface parcelle » une
surface qui n'est pas la parcelle. L'info existe dans la charge utile (`multizone.servie_sur = "U6c
(72,3 %)"`) mais le titre de la ligne ne le dit pas. **Écran à corriger : l'outil** (libeller
« Surface en zone U6c (72 % de la parcelle) »).

### 1.b — Hauteur : outil 9 m / 7 m vs fiche 6 m / 3 m

Les deux valeurs de chaque écran sont **de vraies règles PLU validées, mais ce ne sont pas les mêmes
grandeurs**. Règlement (config validée, cité à l'article) :

| Parcelle / zone | Faîtage `hf_m` | Égout `he_m` | Outil affiche | Fiche (en-tête Urbanisme) affiche |
|---|---|---|---|---|
| BW0102 · U6c | **9 m** (Art. 10.2, p.282) | 6 m (Art. 10.2) | **9 m** (faîtage) | **6 m max** |
| BZ1065 · Uh | **7 m** (Art. Uh.10, p.73) | 4,5 m (Art. Uh.10) | **7 m** (faîtage) | **3 m max** |

- **L'outil** sert le **faîtage** `hf_m` (`builder.py:249`) — la hauteur maximale réglementaire réelle.
  9 m et 7 m sont **exacts** et sourcés à l'article.
- **La fiche (en-tête « Règles d'urbanisme »)** n'affiche **pas** une règle : elle affiche
  `fourchette.hauteur_m = niveaux × étage_m` (`engine.py:649`), un **gabarit LABUSE estimé**.
  `niveaux` est compté **sur l'égout** : `niveaux = int(he_m // étage_m)` (`engine.py:472-473`,
  commentaire l.488 « niveaux comptés sur hé (égout), pas hf »). Avec étage_m = 3 m :
  - U6c : ⌊6 ÷ 3⌋ = 2 niveaux → **6 m** (« R+1 ») ;
  - Uh : ⌊4,5 ÷ 3⌋ = 1 niveau → **3 m** (« R+0 »).

Donc le « 3 m max » de BZ1065 **n'est ni le faîtage (7) ni l'égout (4,5)** : c'est 1 niveau × 3 m.

| Info | Valeur outil | Valeur fiche en-tête | Source outil | Source fiche | Qui a raison | Cause |
|---|---|---|---|---|---|---|
| Hauteur | 9 / 7 m | 6 / 3 m « max » | faîtage PLU `hf_m` (sourcé) | `niveaux × 3 m` estimé depuis l'égout | **L'outil** pour « hauteur réglementaire » | deux grandeurs différentes sous des libellés voisins ; la fiche présente une **estimation** comme un « max » réglementaire |

**Verdict 1.b** : l'outil est juste (faîtage = plafond réglementaire). **La fiche se trompe de libellé** :
« 6 m max » / « 3 m max » dans un en-tête « Règles d'urbanisme » se lit comme une règle, alors que c'est
le gabarit estimé (niveaux × étage). **Écran à corriger : la fiche** (en-tête). Corollaire important au
§2 : le **tiroir §10 de la même fiche** affiche, lui, « Hauteur réglementaire : 9 m » (le vrai faîtage) —
donc *une même fiche montre 6 m en en-tête et 9 m dans son tiroir §10*.

### 1.c — Emprise : BW0102 « non réglementé » vs BZ1065 « 488 m² »

- **BW0102 / U6c** : le YAML U6c **n'a aucune feuille `emprise_sol`** → `MaxFootprint(status="absent")`
  (`builder.py:274-282`), servi « non réglementé ». C'est le **silence prouvé** de GABARIT-4 (la zone U6c
  règle hauteur, reculs, stationnement, pleine terre — mais **pas** le CES). Donnée sourcée, pas un trou.
- **BZ1065 / Uh** : CES **30 %** (Art. Uh.9, « limitée à 30 % de la superficie de l'unité foncière »)
  → 30 % × 1 625 = **487,5 ≈ 488 m²**. Exact.

| Info | BW0102 | BZ1065 | Qui a raison |
|---|---|---|---|
| Plafond d'emprise | « non réglementé » (silence U6c) | 488 m² (30 % Art. Uh.9) | **Les deux corrects** |

**Verdict 1.c** : les deux sont justes. « Non réglementé » = silence réellement prouvé du règlement U6c,
pas une lacune de données.

---

## 2. Vérification sur 10 parcelles

Les 2 de Vic + 8 tirées. Toutes les valeurs « outil » proviennent du moteur de l'endpoint
(`verif_gabarit.py`). `fiche_h` = en-tête Urbanisme (`fourchette.hauteur_m`). `resid_assiette` =
emprise constructible du moteur résiduel (`parcel_faisabilite`, base de `parcel_residuel`).

| # | Parcelle | Zone | Cas | Cadastre | Outil surf. | Zone impl. | Plafond empr. | Haut. outil | Haut. fiche | Assiette résiduel |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 97415000BW0102 | U6c | à cheval A/N (Vic) | 10 321 | 7 465 | 5 867 | non régl. | **9** | 6 | 6 193 |
| 2 | 97411000BZ1065 | Uh | U mono (Vic) | 1 625 | 1 625 | 927 | 488 (30 %) | **7** | 3 | 487 (CES) |
| 3 | 97411000AV0055 | Uh | U simple | 2 126 | 2 126 | 1 396 | 638 (30 %) | 7 | 3 | 638 (CES) |
| 4 | 97411000AV0056 | Uh | U simple | 1 304 | 1 304 | 821 | 391 (30 %) | 7 | 3 | 391 (CES) |
| 5 | 97415000AD0242 | U1g | à cheval A/N (servie) | 1 386 | 1 386 | 341 | non régl. | 9 | 6 | 341 |
| 6 | 97415000AC0071 | (A) | à cheval, A dominante | 2 666 | — | — | — | — | — | terrain_exigu |
| 7 | 97411000AH0022 | Ua | PPR rouge | 1 332 | 1 332 | 638 | 932 (70 %) | 18 | 15 | 928 (CES) |
| 8 | 97411000AW0732 | Ua | PPR rouge | 1 005 | 1 005 | 711 | 703 (70 %) | 18 | 15 | 703 (CES) |
| 9 | 97411000HB0374 | Ui | enclave (séparatives seules) | 306 | 306 | 40 | 183 | 18 | 15 | 40 |
| 10 | 97411000AK0069 | Ud | hauteur non chiffrée | 239 | 239 | 60 | 191 (80 %) | **non chiffrée (prospect L≥H)** | — | terrain_exigu |

**Constats transversaux, chacun vérifié contre la règle citée et la géométrie en base :**

- **Reculs par côté (classification v2)** — corrects et cités : Uh voie 3 / sép. 4 (Art. Uh.6/Uh.7) ;
  U6c voie 4 / sép. 3 (Art. 6/7.2) ; Ua voie 4 / sép. 2 (Art. Ua.6/Ua.7). Sur l'enclave HB0374 :
  **séparatives seules (4 m), aucun recul de voie** — choix assumé de GABARIT-5 (une vraie enclave « E1 »
  est servie sur ses limites séparatives, pas bloquée).
- **Hauteur = faîtage partout** (9 / 7 / 18) ; la fiche affiche systématiquement 2 à 3 m de moins
  (niveaux × 3 depuis l'égout : 6 / 3 / 15). **Écart systémique, pas parcelle par parcelle.**
- **Emprise** : U6c/U1g « non réglementé » (silence) ; Uh 30 % ; Ua 70 % ; Ud 80 % — tous exacts.
- **PPR rouge** (AH0022, AW0732, et BW0102) : `cascade_results` porte bien `HARD_EXCLUDE` (« PPR zone
  rouge inconstructible ») ; l'outil dessine l'exclusion et la **soustrait** de la zone d'implantation
  (règle « PPR — analyse » en `integrated`). Sur les parcelles sans rouge, « PPR — analyse » est listée
  en *non intégrée* (honnête).
- **Ud (AK0069)** : hauteur en **plage 12–27 m avec prospect L ≥ H, sans hauteur absolue de base**
  (Art. Ud.10) → l'outil dit correctement **« Non chiffrée (prospect L ≥ H) »** (statut `not_integrated`),
  et la range dans les règles non intégrées. CES 80 % servi. Comportement juste.
- **AC0071 (« à cheval » attendu U1g+A)** : bloqué « zone A hors calibrage PLU » — la **dominante par
  surface** est A, et `zone_dominante` ne l'a **pas** marquée `a_cheval`. Donc une parcelle réellement à
  cheval, mais majoritairement A, est traitée comme une parcelle A pleine et bloquée. Cas limite à noter
  (différent du découpage propre de BW0102/AD0242).

### Cohérence avec le résiduel (`parcel_residuel`, run 8) — **DEUX MOTEURS DIFFÉRENTS**

La « zone d'implantation » de l'outil et l'« assiette clippée » du résiduel **ne sont pas la même
géométrie**. Construction :

| | Gabarit — zone d'implantation | Résiduel — assiette clippée (`db.py` `_EMPRISE`) |
|---|---|---|
| Retrait | **par côté**, bufferisé (voie ≠ séparative) | **inset uniforme** `ST_Buffer(geom, −recul)` |
| Clip zone | morceau de la **zone constructible dominante** | intersection avec l'**union U/AU** |
| PPR rouge | **soustrait** (exclusion géométrique) | non soustrait de l'emprise de base (grève traitée à part) |
| CES | **non plafonné** (géométrie pure) | emprise finale = `min(assiette, CES)` |

Écart quantifié, sur les zones **sans CES** (où l'assiette résiduel = géométrie brute, donc comparable) :

- **BW0102** : zone impl. **5 867 m²** vs assiette résiduel **6 193 m²** → **−326 m² (−5,3 %)**
  (les reculs par côté + la soustraction PPR mordent plus que l'inset uniforme) ;
- **AD0242** : 341 vs 341 → **≈ 0** (petite parcelle, inset ≈ reculs).

Sur les zones **à CES** (Uh, Ua), l'assiette résiduel affichée (`emprise_constructible_m2`) est déjà
**plafonnée au CES** (BZ1065 = 487 = le CES, pas la géométrie 927 m²) : ce n'est pas la même grandeur que
la zone d'implantation géométrique de l'outil — comparaison non pertinente à l'euro. **À signaler** :
sur AH0022 (**PPR rouge**), l'outil exclut le rouge (zone impl. 638 m²) alors que l'emprise résiduel
(928 m²) ne le retire pas — divergence de traitement du risque entre les deux moteurs.

**Réponse §2 : non, ce ne sont pas les mêmes géométries** — deux moteurs (inset uniforme ∩ U/AU vs
reculs par côté − PPR, plafonné CES ou non). Ils ne servent pas la même chose (le résiduel vise la
capacité/SDP ; le gabarit vise l'enveloppe d'implantation), mais **l'utilisateur qui compare les deux
écrans verra des m² différents sans explication**.

### Cohérence avec le tiroir §10 de la fiche (GABARIT-5)

Le tiroir §10 (`GabaritLine.tsx`) appelle **le même endpoint** `/outils/gabarit/{idu}` et affiche donc
**exactement les valeurs de l'outil** : surface (7 465), zone d'implantation, plafond, et « Hauteur
réglementaire : 9 m » (avec la source « §4 Urbanisme »). **Il est cohérent avec l'outil, mais il
contredit l'en-tête « Règles d'urbanisme » de sa propre fiche** (6 m max). La contradiction n'est donc
pas outil ↔ fiche, mais **en-tête Urbanisme de la fiche ↔ tout le reste** (outil + tiroir §10).

---

## 3. Ce que l'outil ne montre pas et pourrait montrer (faits sourcés — jamais logements/SDP/valeur)

Le builder ne lit **que** : zone, reculs (classification limites), hauteur/emprise (YAML validé),
PPR rouge (`cascade_results` risques). Il **ne lit ni** `batiment`, **ni** `plu_gpu_prescription`
(ER/EBC), **ni** `sup` (vérifié : aucune de ces couches n'apparaît dans `builder.py`).

| Donnée | En base | Dans l'outil | Utile | Coût |
|---|---|---|---|---|
| **Bâti existant** (emprise BD TOPO) | oui — `batiment` (817 k), `batiment_cosia` | **non** | **fort** — BZ1065 porte 2 bâtiments invisibles ; l'outil dit où l'on *peut* construire, pas ce qui est *déjà là* | faible (1 requête + tracé) |
| **Hauteur bâti mesurée** (LiDAR) | oui — `batiment_hauteur_lidar`, `toiture_lidar` | **non** (déjà utilisée par la surélévation de la fiche, pas par l'outil) | fort — permet de croiser faîtage réglé vs faîtage mesuré | faible-moyen |
| **ER / EBC / prescriptions** | oui — `plu_gpu_prescription` (10 490 ; codes 07/05/01/02/15/17…) | **non déduites** | fort — un ER ou un EBC ampute réellement l'enveloppe | moyen (croiser + soustraire, comme le PPR) |
| **SUP** (servitudes d'utilité publique) | oui — `sup` (417) | **non** | moyen | moyen |
| **Liste explicite des règles non intégrées** | oui — la charge utile porte déjà `nonIntegratedRules` (Stationnement, Espaces libres, prospect…) | **non** (le front n'affiche qu'un *compte*) | moyen — l'honnêteté est déjà là, il manque l'affichage | **faible** (rendre une liste déjà présente) |

**Les 21 % de parcelles non servies.** Sur l'échantillon de recette GABARIT-5 (170 parcelles),
**143 servies (84 %)**, donc ~16 % bloquées (le « 21 % » du mandat est la mesure plus ancienne /
île-entière ; l'ordre de grandeur tient). Ce que voit le client : `status="incomplete"`, le message
**« Calcul incomplet — donnée réglementaire manquante »** + le motif précis dans `validationErrors`
(ex. « zone Uc hors calibrage PLU », « recul sur voie non réglementé », « desservie par une voie
privée : le règlement ne précise pas le recul »). C'est **honnête** (motif nommé, pas d'invention). Les
**5 causes restantes** et leur poids (27 bloquées de l'échantillon, `A0-5-MESURE.md`) :

| Cause | n | poids |
|---|---|---|
| PLU : zone non calibrée | 10 | 37 % |
| limite non qualifiée (emprise publique non couverte) | 9 | 33 % |
| voie privée (citation du recul absente) | 4 | 15 % |
| recul non validé | 3 | 11 % |
| PLU : hauteur validée sans valeur exploitable | 1 | 4 % |

---

## 4. Verdict

- **Viable** — oui. Sur les 10 parcelles, tout ce que l'outil chiffre est **exact et sourcé à l'article**
  (faîtage, CES, reculs par côté, silence prouvé, prospect non chiffré, exclusion PPR rouge). Il ne
  ment pas et ne bloque qu'avec un motif nommé.
- **Raccordé** — partiellement. Il partage la config PLU validée avec la fiche, et le **tiroir §10** est
  un miroir fidèle. Mais l'**en-tête « Règles d'urbanisme » de la fiche** sert une autre grandeur
  (niveaux × étage depuis l'égout) sous un libellé de règle, et le **résiduel** dessine une assiette
  d'un **second moteur** (inset uniforme ∩ U/AU, plafonné CES) — d'où des m² et une hauteur différents
  entre écrans, sans explication pour l'utilisateur.
- **Complet** — non, mais volontairement borné. Manquent le **bâti existant** (en base, non tracé),
  les **ER/EBC/SUP** (en base, non déduits) et l'**affichage** de la liste des règles non intégrées
  (déjà dans la charge utile). Le CDC (jamais logements/SDP/valeur) reste respecté.

### Liste des écarts (non corrigés)

1. **Hauteur — le point n°1.** L'en-tête Urbanisme de la fiche affiche « 6 m / 3 m max » = gabarit estimé
   (niveaux × 3 m depuis l'égout), présenté comme une règle. L'outil et le tiroir §10 affichent le
   faîtage réglementaire (9 / 7 m). **Écran à corriger : la fiche (en-tête).** L'outil a raison.
2. **Surface.** L'outil libelle « Surface parcelle » ce qui est la portion de la zone constructible
   dominante (7 465 m² = 72 % de BW0102). **Écran à corriger : l'outil (libellé).** Aucun chiffre faux.
3. **Deux moteurs pour l'assiette.** Zone d'implantation (gabarit) ≠ assiette clippée (résiduel) :
   BW0102 −326 m² (−5,3 %) ; traitement PPR rouge divergent (exclu par l'outil, pas par l'emprise
   résiduel). Différence de méthode, non expliquée à l'utilisateur.
4. **À cheval à dominante A/N.** AC0071 (U1g minoritaire + A dominante) est bloquée « zone A » sans être
   marquée `a_cheval` — la portion constructible est perdue. Cas limite à trancher.
5. **Bâti / ER / EBC / SUP** absents de l'outil alors qu'ils sont en base et amputent l'enveloppe réelle.
6. **Règles non intégrées** : la liste existe dans la charge utile, seul le compte est affiché.

### 3 recommandations pour GABARIT-6 (ou suite)

1. **Réparer la hauteur d'en-tête de la fiche** (écart n°1) : soit y afficher le **faîtage réglementaire**
   (aligné sur l'outil et le tiroir §10), soit relibeller sans ambiguïté « gabarit estimé R+1 (~6 m) » et
   sortir la valeur de la colonne « Règles d'urbanisme ». Idéalement, montrer **faîtage ET égout** cités.
2. **Relibeller la surface de l'outil** quand la parcelle est à cheval : « Surface en zone U6c (72 % de
   la parcelle — 10 321 m² au cadastre) », en réutilisant `multizone.servie_sur` déjà présent.
3. **Afficher la liste des règles non intégrées** (déjà dans `nonIntegratedRules`) et **tracer le bâti
   existant** (couche `batiment`, coût faible) — deux gains d'honnêteté immédiats sans nouveau calcul.

## 5. Hors mandat (non traité)
Corriger le code · la classification des limites · les exports · les autres outils · merger.
