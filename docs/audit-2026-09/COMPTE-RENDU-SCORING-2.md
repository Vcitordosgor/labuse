# COMPTE-RENDU SCORING-2 — fondations du score v2 (arène, rien de servi ne change)

**Branche `feat/scoring-2`, un commit par lot K. Le run servi reste `q_v11_m137` ;
aucun code servi, aucun seuil, aucune table servie touchés. Tout vit dans
`scripts/audit/scoring/` (extension du harnais SCORING-1, validé 1,7·10⁻⁷ de la
prod) et `reports/score-v2-arene/`. La bascule éventuelle appartient à Vic.**

Protocole unique (K0) : **entraîner ≤ 2023 · calibrer 2024 · tester 2025** (année
vierge). Hygiène de la cible : ventes groupées flaguées par parcelle (2 934/6 693
en 2025) ; ventes à un client LABUSE exclues et comptées — **0 en 2025** (le CRM
démarre 2026-07, les 3 courriers sont tous `simule`).

## LE tableau unique (banc K0 — test 2025 sauf K1 bis : test 2024)

| Métrique | base | K1 | K1bis 12m* | K1bis 24m* | K2 | K3 | K4 | **K4bis (global)** | K4bis seg. | K5 GBM |
|---|---|---|---|---|---|---|---|---|---|---|
| préc@100/commune (méd. 24) | 0,060 | 0,055 | 0,065 | 0,085 | 0,070 | 0,060 | 0,050 | **0,075** | 0,045 | 0,070 |
| précision Priorité | **0,137** | 0,074 | 0,103 | 0,091 | 0,072 | 0,077 | 0,078 | 0,066 | 0,023 | **0,197** |
| effectif Priorité | 73 | 68 | 68 | 66 | 69 | **91** | 77 | **91** | 86 | 76 |
| précision À suivre | 0,101 | 0,096 | 0,068 | 0,148 | 0,090 | 0,086 | 0,112 | 0,107 | 0,097 | 0,081 |
| effectif À suivre | 643 | 607 | 591 | 593 | 621 | 604 | 689 | 608 | 651 | 676 |
| lift décile sup | 2,06 | 2,05 | 1,86 | 1,78 | 2,10 | 2,09 | 2,00 | **2,11** | 1,98 | 1,93 |
| AUC global | 0,613 | 0,612 | 0,585 | 0,592 | **0,626** | 0,622 | 0,611 | 0,610 | 0,608 | 0,607 |
| AUC bâti indiv. | 0,575 | 0,577 | 0,595 | 0,579 | 0,589 | 0,587 | 0,589 | 0,584 | 0,590 | **0,595** |
| AUC terrain nu | 0,654 | 0,649 | 0,653 | 0,645 | 0,656 | **0,657** | 0,618 | **0,657** | 0,623 | 0,619 |
| AUC pers. morale | 0,659 | 0,664 | 0,533 | 0,586 | **0,686** | 0,686 | 0,645 | 0,681 | 0,631 | 0,624 |
| AUC copro | 0,614 | 0,610 | 0,648 | 0,620 | 0,605 | 0,605 | 0,609 | 0,610 | 0,596 | **0,666** |
| ECE global | 0,0013 | 0,0012 | 0,0030 | 0,0025 | 0,0014 | 0,0015 | 0,0024 | 0,0012 | 0,0044 | 0,0044 |
| ECE bâti / nu / PM / copro | 16/43/63/239 (·10⁻⁴) | 19/44/65/261 | — | — | 19/45/75/206 | 20/50/79/214 | **15/58/39/181** | 21/45/86/195 | 19/63/91/191 | 22/61/86/**151** |
| churn top-1158 vs servi | 0,180 | 0,289 | 0,244 | 0,554 | 0,340 | 0,364 | 0,850 | 0,453 | 0,891 | 0,857 |

\* K1 bis : train ≤2022, cal 2023, **test 2024** — seule année à fenêtre 24 mois
complète (DVF s'arrête au 31/12/2025). Verdict : **24 mois classe légèrement
mieux** (AUC +0,007, insensible au taux de base ; la précision de tête profite
mécaniquement du taux ~2×). Colonne d'étude, rien d'affiché.

**Précaution de lecture (mesurée, pas supposée)** : le témoin « re-fit des
features servies inchangées » (`k1_variantes.csv`) donne Priorité **8,7 %** là où
l'artefact donne 13,7 % — à features STRICTEMENT égales. Sur ~70 parcelles,
la précision Priorité porte ±8 points de bruit d'échantillonnage ; préc@100,
lift et AUC sont les lignes stables du tableau.

### Ce que chaque lot a réellement montré

- **K1 (censoring)** : l'attendu « AUC +0,04-0,07 » **ne se matérialise pas** —
  la prémisse était fausse : le modèle servi codait DÉJÀ l'absence en bin
  explicite (« inconnu »/« jamais », WoE propre), et l'historique du dataset
  étendu remonte à 2014 (pas 2021). Trois variantes mesurées + témoin ; retenue :
  catégorielle censurée fine (`{<1,1-2,2-3,3-5,5-8,8+,censure}`), AUC neutre.
  `permis_bin` servi satisfaisait déjà K1.2 tel quel.
- **K2 (mortes)** : **le vrai gain du mandat** — AUC 0,613 → **0,626**, signes de
  coefficients 100 % stables en bootstrap (93 % avant), 29 → 20 features.
- **K3 (résiduel)** : les « 41,3 % vides » n'étaient pas des trous du moteur —
  `parcel_residuel` couvre 100 % du parc (doctrine M125 : 0 = réponse, cause
  explicite) ; c'est `p_model_static` qui perdait tout ce qui portait une cause
  (+ 436 parcelles calculées égarées au build). Couverture 58,7 % → ~99 %
  (seul `hors_plu`, 4 397, réellement inconnaissable). **Aucun recalcul 1 h 47
  nécessaire** — ce poste ne sert qu'aux rafraîchissements PLU/bâti.
- **K4 (segments)** : verdict à rebours du plan — **calibration ↑** (ECE PM ÷2,
  copro isolée) mais **discrimination ↓** (nu 0,657→0,618 : la mise en commun
  des 3 M de lignes bat les fits séparés). Un piège mesuré et corrigé au passage :
  zone A hors apprentissage rendait la catégorie « A » inconnue du dictionnaire
  WoE (WoE 0 = neutre → la zone A remontait artificiellement).
- **K4 bis (voisinage)** : en architecture globale, **meilleure tête du tableau**
  (préc@100 0,075, lift 2,11, Priorité 91) pour une AUC stable ; la segmentée
  décroche. « PM vendeur actif » est dominé par les gros institutionnels
  (~60 k parcelles/an flaguées) — à affiner par nature de PM avant d'en attendre
  quelque chose.

## K3 — ventilation des 41,3 % (n = 177 899 + 436 égarées)

| Famille de cause | n | SDP écrite | Complétable ? |
|---|---|---|---|
| zone_non_constructible | 100 953 | 0 | ✅ lue (la réponse du moteur) |
| terrain_exigu | 50 192 | 0 | ✅ lue |
| zone_non_resolue | 12 566 | 0 | ✅ lue (A/N hors YAML : sans droits neufs) |
| habitat_interdit | 5 645 | 0 | ✅ lue |
| redhibitoire | 4 145 | 0 | ✅ lue |
| **hors_plu** | 4 397 | NULL | ❌ réellement inconnaissable — cause explicite |
| calculée mais NULL au feature store | 436 | — | ✅ à récupérer au prochain build |

## K4 bis — test de fuite dédié

Features reconstruites avec la source amont **tronquée à asof** == features
livrées (ventes ET permis), date max des événements entrants 31/12/2024 < asof
01/01/2025 → **`fuite_detectee = false`** (`k4bis_test_fuite.csv`). Le lot
s'arrête net (assert) si ce test casse.

## K5 — verdict de l'arène

Challenger : HistGradientBoosting (équivalent LightGBM natif du venv ML —
`monotonic_cst`, catégorielles natives), un modèle par segment, monotonie métier,
isotonique 2024, même banc. **Règle de promotion (écrite, jamais appliquée)** :
précision de tête (préc@100 ET Priorité) **ET** AUC **ET** ECE ≤ 0,01 par
segment, sur l'année vierge.

**Verdict : NON PROMU** — il gagne la précision Priorité (19,7 %, meilleur du
tableau) et la calibration copro, mais perd préc@100 (0,070 vs 0,075), AUC
(0,607 vs 0,610), lift (1,93 vs 2,11), et l'ECE copro dépasse 0,01.
`promotion_satisfaite = false`, `promotion_appliquee = false`. Le champion reste.

## K7 — note de version du meilleur candidat

> **Candidat du 03/09/2026** (champion K4 bis global) : censoring explicite
> (détention/permis 100 % couverts), 4 mortes + 5 retired retirées, résiduel lu
> à 100 %, voisinage as-of (fuite zéro) — préc@100/commune 0,060 → 0,075, lift
> décile 2,06 → 2,11, Priorité sur 91 parcelles (effectif ×1,2), AUC 0,610,
> ECE 0,0012, churn top-1158 vs servi 45,3 %. Challenger GBM non promu.
> Rien de servi ne change : `q_v11_m137` reste le run servi.

(`k7_manifeste.json` : protocole, hygiène, segments, 31 features + couvertures
2026, croisements, table K0 complète, millésimes du catalogue, règle et verdict.)

## Recommandation (trois lignes)

1. **Ne pas promouvoir** : aucun candidat n'atteint les objectifs du plan (AUC
   ≥ 0,70, Priorité ≥ 15 % sur un effectif 3×) — le plafond sans le bloc
   propriétaire est confirmé par la mesure.
2. **Retenir pour le prochain re-freeze** (décision Vic) : K2 + lecture résiduel
   K3 (gains sûrs, stables), voisinage K4 bis pour la tête de liste ; segments =
   isotonique par segment seulement, pas les fits séparés.
3. **Attendre PROPRIETAIRE-1** pour le vrai saut (levier n° 1 du rapport), en
   gardant l'arène et ce banc K0 comme juge de paix.

---
*Harnais : `scripts/audit/scoring/{protocole,candidats,voisinage,challenger,raisons,run_candidat}.py`
(rejouable ; caches locaux `reports/score-v2-arene/cache/`, hors dépôt).
Variantes mesurées : `k1_variantes.csv`, `k4_variantes.csv`. Tests purs :
`tests/test_scoring2_arene.py`. Aucun redémarrage serveur nécessaire — rien de
servi n'a changé.*
