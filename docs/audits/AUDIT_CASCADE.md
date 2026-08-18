# AUDIT — LA CASCADE, RÈGLE PAR RÈGLE

*Audit pur, aucune correction. Mesures sur le run servi `q_v9_m81` (`config/served_run.txt`),
univers 431 663 parcelles (24 communes). Chaque constat porte son `fichier:ligne`.*

---

## VERDICT (réponse ferme à la question de Vic)

**Filtre caché : NON.** Aucune parcelle ne sort du jeu sans motif écrit. Les 340 752 parcelles
de l'étage 0 portent **toutes** au moins un verdict `HARD_EXCLUDE` avec un `detail` humain
(`cascade/base.py:36` : `detail` est un argument **obligatoire** de `hard_exclude()`). Mesuré :
340 752 parcelles écartées = 340 752 parcelles avec ≥ 1 ligne `HARD_EXCLUDE` motivée. Aucun écart.

**UN point mérite d'être nommé** — non pas un filtre caché actif, mais un **filtre caché *latent*** :
la liste et la carte joignent `dryrun_parcel_evaluations` en **INNER JOIN** (`app.py:1949`, `app.py:2125`).
Une parcelle SANS ligne d'évaluation pour le run servi y disparaîtrait **sans motif**. Aujourd'hui
l'impact est **ZÉRO** (mesuré : 431 663 parcelles = 431 663 évaluations — le run évalue tout l'univers,
0 orpheline). Mais c'est une porte silencieuse par construction : si un run futur n'évalue pas une
parcelle, elle s'évapore. Le compteur (entonnoir) est en LEFT JOIN (`app.py:1599`) et ne l'aurait pas
perdue → divergence latente carte/compteur (déjà relevée M122).

**La cascade ne court-circuite pas.** En phase 1, **toutes** les couches s'évaluent sur **toutes** les
parcelles (`cascade/engine.py:36-40`) — l'ordre config est « le moins cher d'abord », mais aucune couche
n'arrête l'évaluation. L'exclusion est décidée à l'**agrégation** (`scoring/opportunity.py:42` : présence
d'un seul `HARD_EXCLUDE` → score 0). Le « cumulé à son passage » ci-dessous est donc un calcul *a
posteriori* dans l'ordre config, pas un court-circuit réel.

---

## 1. LES RÈGLES D'EXCLUSION — liste exhaustive, ordre réel

**14 couches** peuvent produire un `HARD_EXCLUDE`. Les ~20 autres couches (`safer`, `ravine`, `abf`,
`ens`, `ocs_ge`, `acces`, étage 1 complet, phase 2, étage 2) n'excluent **jamais** — vérifié couche par
couche (elles ne renvoient que `soft_flag`/`positive`/`passed`/`unknown`).

Ordre = ordre des `layers:` dans `config/cascade_rules.yaml`, filtré par phase/enabled/registry
(`engine.py:21-25`). Colonnes : **seuil** (`fichier:ligne`) · **panier** (exclue/faux_positif, cf. §4) ·
**motif servi** (le `detail` est écrit dans `dryrun_cascade_results.detail`, lu par la fiche et les 4
documents via `served_cascade.py`) · **seule** (parcelles dont c'est la SEULE couche HE) · **total** ·
**nouvelles** (ajoutées au cumul dans l'ordre) · **cumulé**.

| # | Couche | Seuil (fichier:ligne) | Panier | Motif servi | Seule | Total | Nouv. | Cumulé |
|---|---|---|---|---|--:|--:|--:|--:|
| 1 | **eau** | centroïde OU ≥ 50 % surface — `phase1.py:73-80` (seuil `cascade_rules.yaml:24`) | exclue | oui | 6 | 316 | 316 | 316 |
| 2 | **parc_national** (cœur) | subtype `coeur` — `phase1.py:102-108` (`yaml:33`) | exclue | oui | 30 | 6 137 | 6 119 | 6 435 |
| 3 | **foret_publique** (domaniale) | subtype `domaniale` + `mode_default: hard_exclude` — `phase1.py:133-136` (`yaml:43-44`) | exclue | oui | 377 | 6 890 | 3 519 | 9 954 |
| 4 | **zonage_plu_gpu** | A/N ≥ `an_hard_exclude_pct`=90 % — `phase1.py:277-283` (`yaml:79`) · zone éco (habitat interdit) ≥ 90 % — `phase1.py:303-313` · `exclude_zones` exact — `phase1.py:247-251` (`yaml:73`, vide) | faux_positif (A/N) **+** exclue (éco) | oui | 51 806 | 103 722 | 95 125 | 105 079 |
| 5 | **prescription_plu** | ER ≥ `er_hard_exclude_pct`=50 % — `phase1.py:430-437` (`yaml:122`) · libellé VETO ≥ 50 % — `phase1.py:418-421` | faux_positif | oui | 857 | 5 140 | 4 518 | 109 597 |
| 6 | **risques** (PPR rouge) | part rouge ≥ `ppr_red_exclude_pct`=50 % — `phase1.py:525-529` (`yaml:148`) | exclue | oui | 5 589 | 44 764 | 13 178 | 122 775 |
| 7 | **trait_de_cote** | subtype `bande_courte` — `phase1.py:626-629` (`yaml:180`) | faux_positif | oui | 0 | 3 | 0 | 122 775 |
| 8 | **pente** | > `seuil_faux_positif_pct`=60 % — `phase1.py:658-662` (`yaml:195`) | faux_positif | oui | 884 | 14 831 | 2 312 | 125 087 |
| 9 | **osm_faux_positif** | `cemetery`/`school` (`phase1.py:761-763`, `yaml:240`) · couverture ≥ `faux_positif_coverage`=0,50 (`phase1.py:771-776`, `yaml:247`) | faux_positif | oui | 294 | 1 526 | 1 234 | 126 321 |
| 10 | **bati** | franc `declasse=='faux_positif'` — `phase1.py:863-864` ; seuils dans `bati.py:34-41` (ratio ≥ 0,50 ; ≥ 0,30 ; ≥ 0,15 + ≥ 3 bâti) | faux_positif | oui | 164 124 | 195 209 | 176 795 | 303 116 |
| 11 | **surface** | < `faux_positif_max_m2`=100 m² — `phase1.py:813-817` (`yaml:283`) | faux_positif | oui | 13 971 | 38 588 | 22 742 | 325 858 |
| 12 | **foncier_public** | propriétaire DGFiP groupe 1-4/9 — `etage0_ext.py:65-76` (dict `etage0_ext.py:25`) | exclue | oui | 9 002 | 36 379 | 11 138 | 336 996 |
| 13 | **emprise_lineaire** | largeur < 8 m ET allongement > 8× — `etage0_ext.py:93-98` (consts `etage0_ext.py:40-41`) | faux_positif | oui | 1 925 | 13 801 | 2 349 | 339 345 |
| 14 | **emprise_routiere** | ≥ 30 m d'axes, densité ≥ 0,5, bâti < 10 %, sans signal privé — `etage0_ext.py:126-135` (consts `etage0_ext.py:47-50`) | faux_positif | oui | 1 407 | 4 851 | 1 407 | 340 752 |

**Cumul final = 340 752 = étage 0** (exclue 78 221 + faux_positif_probable 262 531). Reste après cascade :
90 911 figeables (a_creuser 82 626 + opportunite 8 285). *(La somme des « total » ≫ 340 752 : 90 480
parcelles sont écartées par ≥ 2 couches, 250 272 par une seule.)*

**Lecture** : `bati` est le filtre dominant — **164 124 parcelles ne sont écartées QUE par lui** ; le
retirer libérerait le tiers de l'étage 0. Viennent ensuite `zonage_plu_gpu` (51 806 seul) et `surface`
(13 971 seul). `trait_de_cote` (3) et `eau` (316) sont marginaux.

---

## 2. LES SEUILS — config ou en dur ?

La doctrine interdit le « en dur ». **La majorité des seuils sont en config** (`cascade_rules.yaml` /
`opportunity_weights.yaml`), lus par les couches via `params`. **Trois foyers restent EN DUR** dans le
code Python — findings du présent audit :

| Seuil | Valeur | Où | Config ? |
|---|---|---|---|
| Recouvrement eau | 0,5 | `yaml:24` | ✅ config |
| Zonage A/N hard-exclude | 90 % | `yaml:79` | ✅ config *(marqué PLACEHOLDER « à calibrer Vic »)* |
| Zonage mixte plancher | 5 % | `yaml:81` | ✅ config *(PLACEHOLDER)* |
| Prescription ER hard-exclude | 50 % | `yaml:122` | ✅ config *(PLACEHOLDER)* |
| PPR rouge marginal / exclusion | 2 % / 50 % | `yaml:147-148` | ✅ config |
| Pente flag / faux-positif | 30 % / 60 % | `yaml:191,195` | ✅ config *(PLACEHOLDER)* |
| OSM couverture flag / franc | 0,30 / 0,50 | `yaml:242,247` | ✅ config |
| Surface micro-parcelle | 100 m² | `yaml:283` | ✅ config *(PLACEHOLDER)* |
| Ravine buffer | 10 m | `yaml:166` | ✅ config *(PLACEHOLDER)* |
| **Bâti — franc/à-creuser** | ratio 0,50 / 0,30 / 0,15 ; 3 bâti ; 5000 m² | **`bati.py:34-41`** | ❌ **EN DUR** (constantes module) |
| **Emprise linéaire** | largeur 8 m, allongement 8× | **`etage0_ext.py:40-41`** | ❌ **EN DUR** |
| **Emprise routière** | 30 m, 6 m, densité 0,5, bâti 10 % | **`etage0_ext.py:47-50`** | ❌ **EN DUR** |
| **Groupes publics DGFiP** | {1,2,3,4,9} | **`etage0_ext.py:25`** | ❌ **EN DUR** (dict) |
| **Barème socle SDP** | -25…+30 par palier | **`etage0_ext.py:31`** | ❌ **EN DUR** (n'exclut pas — barème) |

**Nuance honnête sur l'« en dur » de l'étage 0 étendu** : `etage0_ext.py` porte en tête (`:1-14`) la
raison — ces règles sont la **reproduction exacte** des verdicts découverts actifs à Saint-Paul (run q_v2,
jamais committé ; audit C4), gravées « diff zéro » (`scripts/extend_cascade_ile.py`). Le `bati.py` est
volontairement **point de vérité unique** partagé avec la fiche « Occupation » (`yaml:258` : « PAS de seuil
dupliqué ici »). Ce ne sont donc pas des seuils oubliés — mais ils restent **hors config**, non
basculables sans toucher au code : c'est l'écart à la doctrine, nommé.

**PLACEHOLDER** : six seuils config décisifs (zonage 90/5, ER 50, pente 60, surface 100) sont marqués
« à calibrer par Vic » — en config donc modifiables, mais **non encore validés** par une mesure.

---

## 3. LES EXCLUSIONS SANS MOTIF — le filtre caché

Recherché : un chemin où une parcelle sort **sans motif écrit** (jointure qui perd, NULL traité comme
exclu, valeur par défaut). **Zéro trouvé et actif. Preuves :**

1. **Tout `HARD_EXCLUDE` porte un motif.** `hard_exclude(layer, detail, …)` — `detail` obligatoire
   (`base.py:36`). Les 14 couches passent toutes un `detail` humain (colonne « motif servi » du §1).
   Mesuré : 340 752 écartées = 340 752 avec ≥ 1 ligne `HARD_EXCLUDE` motivée.

2. **NULL n'est pas traité comme exclu.** L'étage 0 servi = `status IN ('exclue','faux_positif_probable')`
   (`_ETAGE0_SQL`, `app.py:725`) — un `status` NULL n'y tombe **pas**. `residuel_socle` hors couverture
   (parcel_residuel 23/24) → `UNKNOWN`, **jamais** une exclusion (`etage0_ext.py:158-161`, commentaire
   explicite « à résoudre par extension du calcul, pas un signal d'absence »). De même `bati` sans couche
   bâtiments → `UNKNOWN` (`phase1.py:857-859`), `zonage` sans zone → `UNKNOWN` (`phase1.py:239-244`).
   Le doute ne classe pas.

3. **Le seul risque est latent, mesuré à 0 aujourd'hui.** Carte (`app.py:1949`) et liste (`app.py:2125`)
   font un **INNER JOIN** sur `dryrun_parcel_evaluations` : une parcelle sans ligne d'éval pour le run
   disparaît **sans motif**. Aujourd'hui 0 orpheline (431 663 = 431 663). Le compteur, lui, est en LEFT
   JOIN (`app.py:1599`) — il ne la perdrait pas. Filtre caché latent, à surveiller au prochain run.

4. **La liste masque l'étage 0 PAR DÉFAUT** (`app.py:2085` : `AND NOT _ETAGE0_SQL`) — mais ce n'est pas
   une exclusion *sans* motif : ces parcelles ont leur `detail`, et le masquage est un **défaut d'affichage
   documenté** (territoire M122), réaffichable via `tiers=ecartee` (`app.py:901-902`). Motif présent,
   simplement non montré par défaut.

---

## 4. LES DEUX ÉTAGES FLOUS

### 4a. `exclue` vs `faux_positif_probable` — la frontière exacte

**Un seul point de décision** : `scoring/opportunity.py:44`
```python
exclude_kind = "exclue" if any(v.exclude_kind == "exclue" for v in hard) else "faux_positif"
```
→ `scoring/status.py:16-17` : `EXCLUE` si `exclude_kind == "exclue"`, sinon `FAUX_POSITIF_PROBABLE`.

**Règle : « exclue » l'emporte.** Dès qu'UNE couche `HARD_EXCLUDE` pose `kind="exclue"`, la parcelle est
`exclue` — même si dix autres couches ont posé `faux_positif`. Sinon (toutes en `faux_positif`) →
`faux_positif_probable`.

Qui pose quel `kind` (mesuré : chaque couche × statut final de la parcelle) :

| Couche | pose `kind=` | →exclue | →faux_positif | (le reste va où ?) |
|---|---|--:|--:|---|
| eau | **exclue** | 316 | 0 | — |
| parc_national (cœur) | **exclue** | 6 137 | 0 | — |
| foret_publique (domaniale) | **exclue** | 6 890 | 0 | — |
| risques (PPR rouge) | **exclue** | 44 764 | 0 | — |
| foncier_public | **exclue** | 36 379 | 0 | — |
| zonage (zone éco) | **exclue** | 39 885 | 63 837 | branche A/N = faux_positif ; éco = exclue |
| bati | faux_positif | 13 725 | **181 484** | 13 725 co-écartées par une couche « exclue » |
| surface | faux_positif | 9 959 | 28 629 | idem co-écartées |
| pente | faux_positif | 10 667 | 4 164 | idem |
| prescription_plu | faux_positif | 2 613 | 2 527 | idem |
| emprise_lineaire | faux_positif | 4 175 | 9 626 | idem |
| emprise_routiere | faux_positif | 2 473 | 2 378 | idem |
| osm_faux_positif | faux_positif | 1 056 | 470 | idem |
| trait_de_cote | faux_positif | 3 | 0 | les 3 co-écartées « exclue » (littoral ∩ eau/PPR) |

**Les 181 484 bâties : CONFIRMÉ.** `bati` pose `kind="faux_positif"` (`phase1.py:864`) → ses parcelles
tombent en **`faux_positif_probable`**, sauf 13 725 qui touchent aussi une couche « exclue » (eau, PPR
rouge, foncier public…). Sur 195 209 bâties écartées, **181 484 sont dans `faux_positif_probable`** —
exactement le chiffre du mandat. C'est un **choix délibéré**, pas un accident : `bati.classify` renvoie
`declasse='faux_positif'` (`bati.py:54-66`), et une parcelle déjà bâtie EST, littéralement, un « faux
positif » du gisement foncier (elle est apparue candidate, elle ne l'est pas). Le débat « mauvais panier »
est **sémantique, pas technique** : faut-il traiter « déjà bâti » comme définitif (`exclue`) plutôt que
« probablement pas une cible » (`faux_positif_probable`) ? Le code fait le second choix, en un point
unique et traçable (`bati.py:37,54`). *(Aucune correction — c'est un arbitrage produit, ton geste.)*

Récapitulatif paniers (mesuré, run servi) :
- **`exclue`** = 78 221 — nourri par eau/parc-cœur/forêt-domaniale/PPR-rouge/foncier-public + zonage-éco
  (avec chevauchements ; total union authentique = 78 221).
- **`faux_positif_probable`** = 262 531 — dominé par bâti (181 484), surface (28 629), zonage A/N.

### 4b. L'« étage 2 » (BODACC, âge dirigeant) — exclusion ou score ?

**Ni l'un ni l'autre côté exclusion : étage 2 n'écarte JAMAIS.** Vérifié couche par couche :
- **age_dirigeant** (`etage2.py:29-57`) : renvoie `positive` (points, courbe d'âge `yaml:448`),
  `passed` ou `unknown`. Jamais `hard_exclude`.
- **bodacc** (`etage2.py:60-90`) : renvoie `soft_flag` sévérité **INFO** (× 0 point — flag affiché, 0
  point) et, si procédure ROUGE, pose `evenement='rouge'`. Jamais `hard_exclude`.

**Sa place exacte** : phase 2, **uniquement sur les promues** (survivantes de phase 1, `engine.py:43-50`)
— PLUS une **exception nommée** (`engine.py:61-70`, arbitrage Vic M103 P5) : `bodacc` s'évalue aussi pour
les **non-promues dont le propriétaire est sous pression** (préchargé de `v_foncier_sous_pression`). Effet
de cette exception : poser `evenement='rouge'` sur des parcelles **déjà écartées**, pour qu'elles
remontent à la facette « Événement » (`app.py:922-924`) — une procédure collective ne disparaît pas parce
que la parcelle est bâtie. **Cela ne dé-exclut ni ne ré-exclut personne** : le statut reste celui de la
cascade ; seul un drapeau d'événement est ajouté. L'étage 2 agit donc sur le **score** (points d'âge) et
sur un **signal d'événement** (bascule « chaude »), **jamais** sur l'exclusion.

---

## 5. LE PIPELINE RÉEL — schéma & réponse ferme

```
   PHOTO : 431 663 parcelles (24 communes, cadastre)
     │
     ▼  PHASE 1 — géométrique, TOUTES les couches sur TOUTES les parcelles (pas de court-circuit)
     │   14 couches HARD_EXCLUDE-capables (eau→emprise_routiere)
     │   agrégation opportunity.py:42 : ≥1 HARD_EXCLUDE → score 0
     │   kind : "exclue" gagne sur "faux_positif" (opportunity.py:44)
     │
     ├─────────────── ÉTAGE 0 = 340 752 écartées (toutes motivées)
     │                    ├─ exclue ............. 78 221  (eau, parc-cœur, forêt, PPR rouge, foncier public, zonage éco)
     │                    └─ faux_positif_probable 262 531 (bâti 181 484, surface, zonage A/N, pente, emprises…)
     │
     ▼  PROMUES = 90 911 survivantes (aucun HARD_EXCLUDE)
     │
     ▼  PHASE 2 + étages 1/2 — score & signaux (dvf, sitadel, friche, âge dirigeant, BODACC…)
     │   AUCUNE de ces couches n'écarte — bonus/malus/flags/événement seulement
     │
     ▼  RESTE FIGEABLE = 90 911
         ├─ a_creuser .... 82 626
         └─ opportunite ... 8 285
```

**Réponse à Vic — filtre caché : NON.**
- Toute exclusion est motivée (340 752 = 340 752). Preuve : `base.py:36` + mesure.
- Aucun NULL/défaut ne vaut exclusion (`etage0_ext.py:158`, `phase1.py:857,239`).
- L'unique porte silencieuse est **latente** (INNER JOIN carte/liste, `app.py:1949/2125`), **0 parcelle
  aujourd'hui** — à surveiller au prochain run, non un filtre actif.
- Les 181 484 bâties sont bien en `faux_positif_probable`, par **choix délibéré** de `bati.py` (kind
  faux_positif), en un point unique — question sémantique ouverte, pas un défaut caché.
- L'étage 2 (BODACC/âge) **ne participe pas à l'exclusion** : score & événement seulement.

*Trois findings pour ton arbitrage (aucune correction faite) : (1) seuils EN DUR `bati.py:34-41` +
`etage0_ext.py:25,31,40-41,47-50` ; (2) six seuils config PLACEHOLDER non calibrés ; (3) INNER JOIN
latent carte/liste. Branche `audit/cascade-regles`, non mergée.*
