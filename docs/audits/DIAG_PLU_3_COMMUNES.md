# DIAGNOSTIC — Les 3 communes sans PLU calibré (Saint-André, Saint-Leu, Saint-Philippe)

**Mandat : MESURE, aucune correction.**
Question : pour ces communes, le moteur lit-il une valeur INVENTÉE quelque part (repli sur
une moyenne, sur une commune voisine, sur une valeur par défaut) — auquel cas c'est un faux
positif sur des milliers de parcelles qui fausse le score — ou bien un **NULL honnête traité
comme « inconnu »** ? Et l'écran le dit-il ?

Run servi : `q_v10_m129`. Toutes les lignes de code citées sont vérifiées `fichier:ligne`.

---

## VERDICT EN UNE LIGNE

**Aucune valeur inventée nulle part.** Le NULL est coalescé honnêtement en `'inconnu'` dans le
score (bin catégoriel **entraîné**, poids propre) et en `unknown` / non-évaluable dans la
cascade (« trou de donnée, pas un verdict »). L'écran le dit, commune par commune. Et le bin
`'inconnu'` **abaisse** légèrement le score (WoE −0,199) — donc il n'y a même pas de biais
haussier : pas de faux positif, ni au sens donnée ni au sens score.

**Nuance importante à corriger dans l'énoncé** : « 3 communes sans PLU calibré » mélange deux
choses. **Saint-André et Saint-Leu ONT leur zonage PLU actuel, opposable et SERVI** (le PLU en
vigueur est présent au GPU ; c'est la *révision future* qui n'est pas approuvée, donc non
servie). **Seule Saint-Philippe (RNU) n'a aucun zonage.** La feature `zone_plu` est donc
pleinement sourcée pour 2 des 3 communes ; le `'inconnu'` ne concerne réellement que
~**4 366 parcelles** (Saint-Philippe 4 162 + résiduelles Saint-Leu 204), et honnêtement.

---

## 1. Que lit le moteur pour ces parcelles — et le fichier:ligne du repli

### a) Feature de score `zone_plu`
```
src/labuse/scoring/p_model/ext_sql.py:254   coalesce(st.zone_plu, 'inconnu') AS zone_plu
src/labuse/scoring/p_model/sql.py:450       coalesce(st.zone_plu, 'inconnu') AS zone_plu
```
NULL → **la chaîne littérale `'inconnu'`**. Pas un zonage par défaut, pas le zonage d'une
commune voisine, pas une moyenne. Le repli est un marqueur explicite « pas de donnée ».

### b) Dérivé `nu_constructible`
```
src/labuse/scoring/p_model/ext_sql.py:257   ... AND coalesce(st.zone_plu, '') IN ('U','AU')) AS nu_constructible
src/labuse/scoring/p_model/sql.py:454       (idem)
```
NULL → `''` → **jamais constructible** (le doute ne rend pas constructible).

### c) Cascade
```
src/labuse/cascade/layers/phase1.py:233-244   pas d'intersection de zone → unknown(...)
src/labuse/cascade/layers/phase1.py:226-231   couche zonage absente du contexte → unknown(...)
```
Repli = `unknown` (NON ÉVALUABLE), jamais un zonage fabriqué. Détail en §4.

**Conclusion #1 : les deux points de repli (score + cascade) sont des NULL honnêtes.
Aucune valeur inventée.**

---

## 2. Combien de parcelles, par commune (dataset servi `q_v10_m129`)

| INSEE | Commune | Total (vivier scoré) | Zonées (U/AU/A/N) | `inconnu` |
|-------|---------|---------------------:|------------------:|----------:|
| 97409 | Saint-André   | 22 600 | 22 600 (100 %) | **0** |
| 97413 | Saint-Leu     | 22 959 | 22 755 (99,6 %) | **204** (résiduelles) |
| 97417 | Saint-Philippe| 4 162  | ~0 (9 chevauchements de bord) | **4 162** |

- **Saint-André n'est PAS concernée** par le moindre trou : 100 % de ses parcelles portent le
  zonage du PLU 2019 en vigueur (142 zones ingérées au GPU).
- **Saint-Leu** : 99,6 % zonées (PLU 2007, 368 zones ingérées) ; seules **204 résiduelles** en
  `inconnu` (parcelles hors emprise de toute zone).
- **Saint-Philippe (RNU)** : la totalité des 4 162 parcelles en `inconnu` — c'est attendu, il
  n'y a **aucun** PLU communal (0 zonage au bourg).

Total réel en `'inconnu'` sur les 3 communes : **~4 366 parcelles**, pas « des milliers » sur
Saint-André/Saint-Leu.

---

## 3. La feature `zone_plu` (3ᵉ prédicteur) — bin « inconnu » légitime ou valeur inventée ?

### Déclaration de la feature
```
src/labuse/scoring/p_model/features.py:93-98
  FeatureSpec("zone_plu", "Z", "cat", 0,
    "GPU zonage agrégé U / AU (AUc,AUs) / A / N, centroïde dans la zone ;
     'inconnu' explicite hors couverture", ...)
```
`'inconnu'` est documenté comme une **catégorie explicite « hors couverture »**.

### Preuve dans l'artefact entraîné (`reports/m36-foncier/artifacts-m36-scoring2026.joblib`)
Table WoE de `zone_plu` (`encoder.binned['zone_plu']`) :

| catégorie | WoE | event_rate | counts (train) |
|-----------|-----:|-----------:|---------------:|
| A         | −0,788 | 0,78 % | 590 616 |
| AU        | +0,755 | 3,55 % | 84 560 |
| N         | −0,771 | 0,79 % | 288 688 |
| U         | +0,149 | 1,97 % | 2 454 416 |
| **inconnu** | **−0,199** | **1,40 %** | **35 024** |
| *missing* | *0,0* | *nan* | *0* |

`'inconnu'` est un **bin catégoriel PLEINEMENT ENTRAÎNÉ** :
- **35 024 lignes d'entraînement** portent cette catégorie ;
- **poids WoE propre** (−0,199), dérivé de son **propre taux d'événement mesuré** (1,40 %) ;
- il n'est **PAS** mappé sur le poids de U (+0,149) ni d'aucune vraie zone ;
- il n'est **PAS** le `missing_woe` (=0,0, `missing_count=0`) — donc pas un « fourre-tout NaN ».

**Conclusion #3 : bin légitime, pas une valeur inventée.** Mieux : son WoE est **négatif** — une
parcelle sans zonage tire le score très légèrement vers le BAS (taux d'événement historique
1,40 % < U 1,97 %). Le modèle n'invente pas un zonage constructible ; il a *appris* que
« pas de zonage » ≈ légèrement moins mutable. **Aucun biais haussier, aucun faux positif.**

---

## 4. La cascade — exclues, incluses, ou traitées par défaut ?

```
src/labuse/cascade/layers/phase1.py:233-244  (couche "zonage_plu_gpu")
  # M71 BLOC C : AUCUNE zone PLU sur la parcelle = trou de donnée
  # (Saint-Philippe : 0 couche au GPU, commune RNU — 4 153 parcelles ; Saint-Leu :
  #  91 résiduelles ; 0 ailleurs, mesuré). Un trou de donnée n'est PAS un verdict :
  # NON ÉVALUABLE (unknown, impacte la complétude comme ABF) — plus jamais un
  # PASS silencieux « Hors zonage PLU connu ».
  return [unknown(self.name,
      "Zonage PLU non publié au GPU pour cette parcelle — constructibilité non "
      "évaluable sur ce critère (trou de donnée, pas un verdict).", source=SRC_GPU)]
```

Résultat cascade pour une parcelle sans zonage :
- **NON exclue** (pas de `hard_exclude`) ;
- **NON incluse comme constructible** (pas de `positive` / pas de PASS silencieux) ;
- **traitée comme `unknown` = non évaluable sur ce critère**, ce qui **impacte la complétude**
  (au même titre qu'une donnée ABF manquante).

Le commentaire cite nommément Saint-Philippe (« 4 153 parcelles ») et Saint-Leu (« 91
résiduelles ») : le cas est reconnu et documenté à la source. Ancien comportement (PASS
silencieux « hors zonage connu ») explicitement retiré en M71.

**Conclusion #4 : trou de donnée honnête, ni exclusion ni inclusion abusive.**

---

## 5. À l'écran — la fiche dit-elle « pas de PLU » ou affiche-t-elle un zonage comme sourcé ?

Trois surfaces, toutes honnêtes et différenciées par commune.

### a) Étiquette de fraîcheur PLU — `_plu_fraicheur` (`src/labuse/api/app.py:2969-3017`)
Statut lu dans `config/plu_millesimes.yaml` :

- **Saint-André (97409)** — statut `opposabilite_en_attente` :
  > « PLU approuvé le 2019-02-28 (opposable, présent au GPU) — il fait foi à ce jour.
  >   Une révision est en cours, non approuvée — non opposable, non servie. »

  → Le zonage affiché EST le vrai PLU 2019 servi (142 zones). La révision est signalée
  comme document *futur non servi*. **Honnête et exact.**

- **Saint-Leu (97413)** — statut `opposabilite_en_attente` :
  > « PLU approuvé le 2007-02-26 (opposable, présent au GPU) — il fait foi …
  >   Révision en cours (approbation visée S2 2026), non approuvée → non servie. »

  → Idem : vrai PLU 2007 servi (368 zones), révision future signalée. **Honnête.**

- **Saint-Philippe (97417)** — statut `rnu` (`app.py:3011-3015`) :
  > document_servi = « **Aucun PLU — RNU (règlement national d'urbanisme).** »
  > fait_foi = « Le RNU s'applique ; **aucun zonage communal servi.** »
  > action = « Constructibilité au cas par cas (RNU) — vérifier en mairie. »

  → **Dit explicitement qu'il n'y a pas de PLU.** Aucun zonage présenté comme sourcé.

### b) Bandeau RNU commune — `rnu.rnu_block` (`app.py:2662`, `src/labuse/rnu.py:28-31`)
Source de vérité `config/rnu_communes.yaml` (seule Saint-Philippe / 97417 y figure) :
> « **Commune au règlement national d'urbanisme — pas de PLU local.** »
Mécanisme GÉNÉRAL (toute commune sans document local), jamais un cas codé en dur.

### c) Note de capacité — `app.py:1415-1417`
> Saint-Philippe : « **RNU — pas de PLU opposable : capacité non calculable**, … »
et `app.py:1479` : `raison_sans_zonage = "zonage non publié au GPU"`.

**Conclusion #5 : l'écran DIT la situation, et correctement par commune.** Saint-André et
Saint-Leu affichent leur zonage réel (sourcé, car il l'est) + le drapeau « révision en cours,
non servie » ; Saint-Philippe affiche « Aucun PLU — RNU » partout, sans jamais fabriquer un
zonage.

---

## SYNTHÈSE

| # | Question | Réponse | Preuve |
|---|----------|---------|--------|
| 1 | Ce que lit le moteur / repli | NULL → `'inconnu'` (score) et `unknown` (cascade) — honnête | `ext_sql.py:254`, `sql.py:450`, `phase1.py:233-244` |
| 2 | Parcelles concernées | St-André 0 · St-Leu 204 · St-Philippe 4 162 (~4 366 total) | dataset `q_v10_m129` |
| 3 | Feature `zone_plu` | Bin `inconnu` **entraîné** (WoE −0,199 propre, 35 024 obs), pas inventé, **abaisse** le score | `features.py:93-98` + artefact WoE |
| 4 | Cascade | `unknown` / non-évaluable (« trou de donnée, pas un verdict ») — ni exclue ni incluse | `phase1.py:233-244` |
| 5 | Écran | Le dit par commune : St-André/St-Leu = zonage réel + « révision non servie » ; St-Philippe = « Aucun PLU — RNU » | `app.py:2969-3017`, `rnu.py:28-31`, `app.py:1415` |

**Rien à corriger côté donnée ou score : c'est le cas « NULL honnête traité comme inconnu »,
pas le cas « valeur inventée ».** Le seul point à noter est de langage : Saint-André et
Saint-Leu ne sont PAS « sans zonage » — elles ont leur PLU actuel servi et opposable ; ce qui
n'est pas calibré/servi, c'est leur *révision en cours*. Seule Saint-Philippe est réellement
sans zonage (RNU), et tout le produit le dit.

---

## ADDENDUM — La PAU de Saint-Philippe : substitut honnête, pas cécité

Question de suivi : Saint-Philippe (RNU, 4 162 parcelles sans zonage) est-elle *réellement*
aveugle, ou la PAU estimée (`parcel_pau`) lui donne-t-elle déjà un substitut ?
**Réponse : elle a un substitut ESTIMÉ, honnête et branché — pas aveugle.**

### 1. Couverture
`parcel_pau` ne couvre QU'UNE commune : Saint-Philippe (97417). **2 373 des 4 162** parcelles
(57 %) sont dans l'enveloppe PAU estimée. Enveloppe : 35 noyaux, 3 482 bâtiments clusterisés,
268 ha (`commune_pau`).

### 2. Méthode — **Estimé**, pas Sourcé
`src/labuse/rnu.py:131-186` (`build_pau`, méthode « médiane » validée Vic 26/07/2026) :
noyaux = `ST_ClusterDBSCAN` des centroïdes de bâtiments BD TOPO (eps 50 m, min 10) ; enveloppe
= `ST_Union(ST_Buffer(bâtiment, 40 m))` ; parcelle dans la PAU ssi
`ST_PointOnSurface ∈ enveloppe` (critère « centre »). Paramètres en **config**
(`rnu_communes.yaml › pau`), jamais en dur. C'est une **ESTIMATION LABUSE** — assumée telle,
jamais présentée comme la délimitation officielle.

### 3. Servie à l'écran — oui, avec avertissement
`rnu.rnu_block` (`src/labuse/rnu.py:82-108`, appelé fiche `app.py:2662`) sert `dans_pau`
True/False + `AVERTISSEMENT_PAU` (`rnu.py:36`) :
> « Enveloppe urbanisée estimée par LABUSE — la délimitation des parties actuellement
>   urbanisées relève de l'appréciation du service instructeur. »
Donc l'écran dit *à la fois* « dans/hors PAU » **et** que c'est une estimation.

### 4. Entre-t-elle dans le score / la cascade ?
- **Modèle de proba (WoE, `zone_plu` 3ᵉ prédicteur) : NON.** `parcel_pau` n'est pas une
  feature (`features.py` ne la lit pas) ; la proba reste calculée sur `zone_plu='inconnu'`
  (cf. §3 principal). La PAU **n'influence pas la probabilité de mutation.**
- **Gate de tier p_v2 (`plancher_c`, `scoring/p_v2/statuts.py:55-70`) : OUI, comme substitut
  d'U/AU.** Au RNU, U/AU n'existe pas et la branche SDP non plus (pas de règlement, pas de
  droits calculables) ; l'équivalent validé est « parcelle DANS la PAU ∧ surface ≥ **même**
  seuil (600 m²) ». Injectée par `pipeline.py:277-286`. **947** parcelles St-Philippe passent
  ce plancher (PAU ∧ surface ≥ 600) — sans PAU elles seraient toutes recalées faute de zonage.
- **Cascade Q (`phase1.py`) : NON** — la couche zonage reste `unknown` (§4 principal) ; la PAU
  ne fabrique pas de verdict de zonage.
- **division_or** (`ingestion/division_or.py:297,501,736-737`) : la PAU sert de repli quand
  `zone IS NULL` (lot RNU gardé seulement si dans la PAU) — même logique, hors score/cascade.

### Verdict addendum
Saint-Philippe **n'est pas aveugle** : la PAU lui fournit un substitut d'urbanité **estimé,
étiqueté comme tel, au même seuil que tout le monde**, qui débloque le *tiering* de 947
parcelles (les 2 373 dans la PAU, filtrées à surface ≥ 600). Ce substitut agit **uniquement**
sur l'éligibilité-capacité (gate de tier), **jamais** sur la probabilité de mutation ni sur un
verdict de zonage — qui, eux, restent en `inconnu`/`unknown` honnêtes. Aucun faux positif : la
seule chose « inventée » est une **enveloppe explicitement estimée**, affichée avec son
avertissement, et bornée au même plancher de surface que les communes à PLU.
