# Campagne PPR rouge/bleu — synthèse & décision (read-only)

> **Statut : note de synthèse. Aucune action technique engagée.** Toute la campagne a été menée en
> **lecture seule** (SELECT DB + WMS Géorisques, fichiers temporaires hors dépôt). Aucun import, aucune
> re-cascade, aucune mutation DB, aucun changement de scoring, aucun passage gold. Ce document **fige les
> conclusions** ; les décisions produit/techniques sont à prendre séparément.

## 1. Résumé exécutif

- **Le sur-flag PPR est systémique** sur les 16 communes gold : la règle actuelle **« toute intersection du
  périmètre PM1 → SOFT_FLAG fort »** (couche `risques`) **sous-compte fortement les opportunités**, car un
  flag *fort* à la fois pénalise (−15) **et** bloque le statut `opportunite` (`has_fort_flag`).
- **~90 % des parcelles U/AU flaggées « PPR fort » sont en réalité Bleu (prescriptions) ou Hors-zone** — pas
  Rouge (interdiction). Le flag est donc *majoritairement faux*.
- Le **zonage réglementaire rouge/bleu est disponible au WMS Géorisques pour 14/16 communes gold**.
- **Saint-Denis = lacune** : périmètre PM1 publié mais **zonage R/B absent** du WMS → gain indéterminé.
- **Sainte-Marie = hors-scope** : PPR négligeable (9 parcelles PPR-fort, 0 population flip).
- **Quick-win « seuil de couverture PM1 » et PPR rouge/bleu sont complémentaires** (bords rognés vs cœur bleu),
  pas concurrents.

## 2. Résultats clés (chiffres)

| Indicateur | Valeur |
|---|---|
| **Gain R/B fiable — optimiste** (bleu→pass, score ≥ 50, 14 communes publiées) | **≈ +2 356 opportunités** |
| **Gain R/B fiable — conservateur** (bleu→moyen, score ≥ 60) | **≈ +230** |
| **Quick-win seuil couverture PM1** (indépendant du R/B) | **≈ +473 (< 10 %) à +782 (< 30 %) flips** |
| **Saint-André** (chef de file) | **+1 018 optimiste / +78 conservateur** (54 → ~1 072, **×20**) |
| **Saint-Denis** | **+218 INDÉTERMINÉ** (périmètre seul → exclu du gain fiable) |
| Abattement déclassement (parcelles flip) | **0 %** (vérifié : parcelles propres) |
| Inconnus WMS | **0** (méthode 100 % fiable sur ~2 800 points interrogés) |

**Top communes à impact (R/B publié) :** Saint-André (+1 018) · Saint-Paul (+541) · Saint-Pierre (+260) ·
Le Tampon (+158) · La Possession (+131). *Les 3 premières = 77 % du gain fiable.*

**Pourquoi c'est important :** le taux d'opportunité gold actuel va de **0,22 %** (Saint-André, Saint-Denis —
**forte couverture PPR**) à **3,6 %** (Saint-Paul, Saint-Pierre — **faible couverture PPR**). Le blanket PPR
explique une grande part de l'écart : **les communes gold les plus « plombées » sont celles le plus couvertes
par le PPR**, alors que leurs parcelles sont majoritairement en zone **bleue** (constructible sous conditions).

## 3. Tableau complétude R/B (16 communes gold)

| Commune | INSEE | R/B publié ? | gain R/B fiable | quick-win utile ? | verdict |
|---|---|---|---|---|---|
| Saint-André | 97409 | ✅ oui | **+1 018** | non (couv. 98 %) | R/B requis |
| Saint-Paul | 97415 | ✅ oui | **+541** | **oui** | R/B + quick-win |
| Saint-Pierre | 97416 | ✅ oui | **+260** | **oui** | R/B + quick-win |
| Le Tampon | 97422 | ✅ oui | **+158** | **oui** | R/B + quick-win |
| La Possession | 97408 | ✅ oui | **+131** | **oui** | R/B + quick-win |
| Le Port | 97407 | ✅ oui | +77 | non | R/B (peu de rouge) |
| Saint-Louis | 97414 | ✅ oui | +42 | oui | mixte |
| Saint-Joseph | 97412 | ✅ oui | +36 | oui | blanket + justifié (56 % rouge) |
| Les Avirons | 97401 | ✅ oui | +25 | partiel | R/B |
| Saint-Benoît | 97410 | ✅ oui | +24 | oui | **blanket justifié (67 % rouge)** |
| L'Étang-Salé | 97404 | ✅ oui | +14 | oui | mixte |
| Petite-Île | 97405 | ✅ oui | +14 | oui | mixte |
| Sainte-Suzanne | 97420 | ✅ oui | +13 | oui | mixte |
| Bras-Panon | 97402 | ✅ oui | +3 | oui | marginal |
| **Saint-Denis** | 97411 | ❌ **périmètre seul** | *(+218 indéterminé)* | non (couv. 97 %) | **lacune WMS** |
| **Sainte-Marie** | 97418 | — | 0 | — | **PPR négligeable (hors-scope)** |

**14 communes au WMS complet · 1 lacune (Saint-Denis) · 1 hors-scope (Sainte-Marie).**

## 4. Quick-win « seuil de couverture PM1 »

La règle actuelle flague *fort* dès que le périmètre PM1 **effleure** la parcelle (intersection > 0, parfois
**~0 % de surface**). Exiger une **couverture minimale** déflague les parcelles en **bord de périmètre** —
**sans aucune nouvelle donnée** :

- **seuil < 10 %** : **≈ +473 flips** ;
- **seuil < 30 %** : **≈ +782 flips**.

Ce levier corrige surtout les **parcelles en bord de périmètre** des grandes communes côtières :
**Saint-Paul, Saint-Pierre, Le Tampon, La Possession** (couverture moyenne 31–58 %, beaucoup de bords rognés).
Il est **insuffisant pour Saint-André** (parcelles réellement couvertes à ~98,6 % par le périmètre **mais en
zone bleue** → seul le R/B y débloque). Limite : le quick-win est **crue** (déflague par couverture, **ignore
rouge/bleu**) → à n'appliquer qu'à **seuil conservateur** (5–10 %), où un bord est rarement la zone rouge critique.

## 5. PPR rouge/bleu (lecture des codes)

Source : **Géorisques WMS** `PPRN_ZONE_INOND` / `PPRN_ZONE_MVT` / `PPRN_ZONE_SUBMAR`, attribut
`code_zone_reglement` (standard CNIG/COVADIS), interrogé en `CRS:84` / `INFO_FORMAT=application/vnd.ogc.gml`.

- **Rouge `R1` / `R2`** = **Interdiction** → **exclusion** (inconstructible).
- **Bleu `B` / `B2` / `B2u` / `B3`** = **Prescriptions** → **constructible SOUS CONDITIONS** (cotes,
  études, etc.).
- **Hors-zone** = aucune zone réglementaire au point → **pas de contrainte PPR réglementaire directe**.

**Politique produit recommandée :** **rouge → exclusion** · **bleu → flag MOYEN** · **hors-zone /
hors-périmètre → pas de flag**. **Ne PAS traiter le bleu comme totalement libre** : les prescriptions sont de
vraies contraintes (coût, faisabilité). Le scénario « optimiste » (+2 356, bleu→pass) est une **borne haute** ;
le réaliste se situe entre conservateur (~230) et optimiste selon la politique « bleu ».

## 6. Limites

- **Toute la campagne en READ-ONLY** : SELECT DB + WMS, fichiers hors dépôt. Aucune mutation, aucune
  re-cascade, aucun changement de scoring.
- **WMS GetFeatureInfo au centroïde** (pas d'overlap polygone exact) : une parcelle à cheval rouge/bleu est
  classée par son centre. Robuste pour le **sens** (sur-flag confirmé), approximatif pour le **compte exact**.
- **Flips = estimation arithmétique** (score + Δ ≥ 65), **pas de re-cascade**. Abattement déclassement vérifié = 0.
- **Saint-Denis incomplet au WMS** (périmètre publié, zonage R/B absent) → +218 indéterminé, exclu du fiable.
- **Petites communes** classées sur petits échantillons (~9 points) → confiance moyenne/faible ; certaines
  sont **rouge-lourdes** (Saint-Benoît 67 %, Saint-Joseph 56 %), donc le R/B y aide moins.
- **COVADIS/DEAL** (vecteur exact) serait utile **plus tard** (overlap exact + combler Saint-Denis), **mais
  n'est PAS indispensable pour démarrer** : le WMS sert déjà le R/B pour 14/16 communes.
- **Décision produit à prendre séparément** (politique bleu/rouge/hors-zone, seuils, ordre des chantiers).

## 7. Recommandation finale

- ✅ **GO pour réfléchir à un futur chantier PPR rouge/bleu** : fiabilité confirmée (14/16 publiés), gain
  massif (≈ +2 356 optimiste, dominé par Saint-André), données accessibles **sans solliciter DEAL** dans un
  premier temps.
- ✅ **GO potentiel pour un quick-win « seuil de couverture PM1 » conservateur** (5–10 %) : ~+473 flips,
  gratuit, complémentaire, traite les bords rognés **et** Saint-Denis (où le R/B manque).
- ❌ **NO-GO à toute neutralisation PPR aveugle** (supprimer le flag sans distinguer rouge/bleu surfacerait des
  parcelles en zone **rouge** interdite).
- ❌ **NO-GO à traiter le bleu comme « aucun risque »** (Prescriptions = vraies contraintes ; bleu → flag *moyen*).
- ➡️ **Prochaine étape = décision PRODUIT séparée** (politique PPR : quick-win et/ou R/B, seuils, traitement
  bleu/rouge/hors-zone, sort de Saint-Denis). **Aucun build, aucun changement de scoring tant que cette
  décision n'est pas prise.**

## 8. Prochaine mission proposée (NON exécutée)

```text
Décision produit PPR — arbitrage (atelier de décision, pas une exécution).

Objectif : choisir la stratégie PPR de LABUSE à partir des conclusions de la campagne
(note docs/communes/PPR_ROUGE_BLEU_CAMPAIGN.md). Décider, sans coder :
1) Quick-win "seuil de couverture PM1" : OUI/NON, et à quel seuil (5/10/30 %) ?
2) Ingestion R/B depuis le WMS Géorisques (code_zone_reglement) sur les 14 communes publiées :
   OUI/NON, et dans quel ordre (priorité Saint-André/Paul/Pierre) ?
3) Demande COVADIS/DEAL (vecteur exact + Saint-Denis) : maintenant, plus tard, ou jamais ?
4) Politique de traitement : rouge = exclusion ? bleu = flag moyen ? hors-zone = pas de flag ?
   Saint-Denis : garder le flag actuel tant que pas de vecteur ?
5) Garde-fous : pas de neutralisation aveugle, pas de bleu = libre, seuil scoring inchangé.

Livrable : une décision écrite (choix 1-4 + garde-fous) qui servira de cahier des charges
au futur chantier technique — lequel fera l'objet d'une mission validée distincte.
Aucune exécution technique dans cet atelier.
```

---

### Provenance (lecture seule)

- DB (SELECT) : `parcels`, `parcel_evaluations`, `cascade_results`, `spatial_layers` (couverture PM1).
- WMS Géorisques : `PPRN_ZONE_*` (zonage réglementaire) + `PPRN_PERIMETRE_*` (périmètre) —
  `https://www.georisques.gouv.fr/services`, `CRS:84`, `INFO_FORMAT=application/vnd.ogc.gml`,
  attribut `code_zone_reglement`.
- Données de travail conservées **hors dépôt** dans `/tmp/labuse_sourcing/ppr/`. Aucune écriture sous le repo
  pendant la campagne ; aucune mutation DB ; aucun passage gold ; aucun contact DEAL.
