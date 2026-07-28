# RAPPORT — Phase A, BACK-TEST CONTRE LE RÉEL : la correction par médiane DVF communale est CONTREDITE

**Exécuté le 28/07/2026** (branche `mesure/calibration-phase-a-prix-neuf`, exécuteur Claude Code).
Contre-test bloquant exigé par Vic avant toute application (§1 de son arbitrage du 28/07).
**LECTURE SEULE intégrale.** État base ouverture ET clôture : **golden 116/116 PASS, tiers du
run servi `q_v7_defisc` au bit près (120 / 1031 / 3587 / 72980 / 353945).**

## ⚠ AVERTISSEMENT DE COUVERTURE (à ne pas adoucir — arbitrage Vic 28/07)

**Après application, la charge foncière supportable ne sera calculable que sur 6 communes —
Saint-Denis, Saint-Pierre, Saint-Paul, Saint-Leu, Le Tampon, La Possession — les seules où un
marché du collectif neuf est OBSERVABLE (≥ 10 ventes d'appartements). Sur les 18 autres, LABUSE
dira qu'il ne sait pas** (« non calculable » : marché du collectif non observable, ou collectif
majoritairement social/aidé — §17). C'est une régression APPARENTE de couverture et une
progression RÉELLE d'exactitude : mieux vaut s'abstenir que servir un chiffre faux. C'est aussi
ce qui rend le **second mode de bilan** (social + patrimonial locatif, §18) commercialement
NÉCESSAIRE et non plus seulement souhaitable.

## 0 · Verdict en une phrase

**Le contre-test contredit la correction naïve.** Substituer la médiane `dvf_prix_sortie_neuf`
communale au socle 4900 déclare **78 % des opérations collectives RÉELLEMENT construites non
viables**, dit que **99–100 % des acheteurs fonciers réels ont surpayé**, et échoue la preuve
la plus forte (opération complète) **à 100 %**. La correction n'est pas juste : elle est
excessive — **et l'erreur est en amont du prix, dans ce que la médiane MESURE.** Ne pas
appliquer. Le socle 4900 était faux (phase A l'a prouvé), mais la médiane communale l'est
davantage, dans l'autre sens.

## 1 · Les trois épreuves (données déjà ingérées, prix résolus selon la préséance validée
override bassin sourcé > DVF secteur > DVF commune > non calculable ; coûts YAML audités)

### E1 — Permis de construire collectifs réels (Sitadel ≥ 3 lgt, famille logements, 2021+)

Opérations viables par définition (elles ont été autorisées et construites). Charge supportable
calculée **sur le programme RÉEL du permis** (`surf_hab_creee` = surface habitable créée, donc
injectée telle quelle comme habitable vendable — pas de regonflement coef_plancher), prix de
sortie local, coûts corrigés.

- **Cohorte 1 137 · calculables 1 018 · charge ≤ 0 : 795 (78 %).**
- Déciles de charge (€, après trim des 9 artefacts terrain ci-dessous) :
  −1 792 016 · −785 226 · −434 775 · −290 710 · **−193 688 (médiane)** · −127 648 · −61 883 ·
  +24 587 · +255 488. **La moitié des opérations réelles sort à −190 k€ ou pire.**
- **13 communes sur 17 : quasi 100 % de charges ≤ 0** (Saint-Louis 81/81, Saint-Benoît 59/59,
  La Possession 43/43, L'Étang-Salé 37/37, Sainte-Marie 64/64, Sainte-Suzanne 45/45,
  Saint-Joseph 56/56, Petite-Île 23/23, La Plaine 25/25, Le Port 15/15…). Seules Saint-Denis
  (75/164), Saint-Paul (48/138), Saint-Leu (38/52), Trois-Bassins (5/12) respirent — les 4
  communes dont la médiane DVF dépasse le seuil de bascule.
- Variante E1b (capacité MODÈLE d'aujourd'hui, non le programme réel) : 748 / 861 ≤ 0 (87 %) —
  même verdict, biais déclaré (le bâti actuel ampute la capacité résiduelle).
- **Artefact borné** : les 9 charges extrêmes (jusqu'à −96 M€) sont des parcelles à terrain
  géant (692 580 / 421 284 / 413 426 m²…, ZAC-parent ou géocodage) où le VRD (90 €/m² × terrain)
  explose. Retirées ; sans effet sur les 78 %.

### E2 — Parcelles achetées par une personne morale (SCI/SA/SAS/SARL/SNC « non remarquables »), vente DVF mono-parcelle 2021+ hors appartement, prix payé vs charge modèle

- **Cohorte 1 267 · calculables 993 · prix payé > charge : 981 (99 %).**
- Là où la charge est positive (163 cas), déciles du ratio **prix payé / charge : 1 · 2 · 2 · 4 ·
  5 (médiane) · 6 · 8 · 11 · 22** — l'acheteur paie 5× notre charge à la médiane.
- Déciles de l'écart charge − prix (€) : −1 215 537 … −490 759 (médiane) … : on est en dessous
  du prix payé partout sauf la queue haute.
- *Réserve d'interprétation* : une PM achète aussi du bâti/du patrimonial, `prix_paye` porte sur
  la parcelle entière (foncier + existant) — E2 seule est un signal faible. Elle ne vaut que
  corroborée par E3.

### E3 — L'opération complète : parcelle achetée PUIS PC collectif ≥ 3 lgt ≤ 4 ans après (la preuve la plus forte)

- **Cohorte 42 · calculables 36 · prix payé > charge : 36 (100 %) · charge ≤ 0 : 31 (86 %).**
- Déciles ratio prix payé / charge (charge > 0) : 2 · 2 · 10 · 10 · 10 (médiane) · … · 12.
- Cas concrets : Sainte-Suzanne payé 60 k€ / charge −100 k€ ; Saint-Louis 60 k€ / −162 k€ ;
  Saint-Leu 88 k€ / −101 k€ ; Le Tampon 120 k€ / −127 k€. **Des opérations bel et bien montées
  (achat réel + permis collectif réel), que le modèle corrigé déclare à perte foncière.**

## 2 · Où est l'erreur — prouvé par les maillons, pas supposé

**Le point de bascule est mécanique.** charge/m² habitable = prix_neuf × 0,76 − 1,15 × 2 550 −
VRD. Hors VRD, charge > 0 exige **prix_neuf > 1,15 × 2 550 / 0,76 = 3 859 €/m² habitable** — rien
que pour couvrir la construction et la marge, AVANT le moindre euro de foncier. **66 % des
opérations réelles d'E1 se sont vendues sous ce seuil.** Vérif à la main (Saint-Benoît, PC 4 lgt,
434 m²) : vente 2 385 €/m² × 0,76 = 1 813 < coût 2 932 €/m² → perte sur la construction seule.

**Pourquoi la médiane DVF est en dessous du seuil — la médiane mesure la mauvaise population,
sur des échantillons minuscules :**

| INSEE | Commune | n | n_appt | p25 | **p50** | p75 | p90 | max |
|---|---|---|---|---|---|---|---|---|
| 97410 | Saint-Benoît | 22 | **0** | 1 388 | **2 385** | 2 883 | 5 668 | 6 204 |
| 97407 | Le Port | 16 | 1 | 1 740 | **2 268** | 3 510 | 4 121 | 4 513 |
| 97418 | Sainte-Marie | 17 | 1 | 2 178 | **2 863** | 3 319 | 6 283 | 8 837 |
| 97414 | Saint-Louis | 37 | 3 | 2 469 | **3 073** | 3 892 | 5 700 | 10 672 |
| 97405 | Petite-Île | 9 | **0** | 1 206 | **1 980** | 3 165 | 3 610 | 3 866 |

- Les communes bon marché ont **5 à 37 ventes, presque toutes des MAISONS** (Saint-Benoît :
  22 ventes, 0 appartement ; Petite-Île, La Plaine : 0 appartement). La médiane mesure le prix
  d'une **maison neuve individuelle** (autoconstruction, rural, parfois social/aidé), pas le prix
  de sortie d'un **collectif de marché** — qui est précisément ce que la charge promoteur modélise.
- Le proxy « vente ≤ 3 ans après achèvement d'un PC » ratisse tout : logement aidé revendu,
  VEFA à prix plafonné, maison rurale. La **médiane** de ce mélange est un mauvais estimateur du
  prix promoteur.
- **Le marché de marché existe — au-dessus de la médiane.** Sur les 17 communes couvertes, seules
  **4 ont p50 ≥ 3 859**, mais **11 ont p75 ≥ 3 859 et 15 ont p90 ≥ 3 859.** Le haut de la
  distribution franchit le seuil quasi partout : le prix collectif existe, la médiane le noie.

**Conclusion de localisation** : l'erreur n'est pas « le socle 4900 » (phase A l'a bien réfuté),
c'est **l'instrument de remplacement**. `dvf_prix_sortie_neuf` au niveau médiane/commune ne mesure
pas « prix de sortie du collectif neuf de marché ». La corriger vers cette médiane empile un
second biais, plus grand et de sens opposé, sur des échantillons trop maigres. Candidat
secondaire à ne pas écarter : le coût 2 550 €/m² SDP × coef_plancher 1,15 (= 2 932 €/m² habitable)
pourrait être haut pour ces opérations modestes — mais il vient d'être audité (O2) et la preuve
la plus directe pointe l'instrument prix (population maison-dominée, n minuscule, p75/p90 qui
franchit le seuil). Les deux leviers sont à départager en phase suivante ; aucun ne justifie
d'appliquer la médiane en l'état.

## 3 · Ce que ça change pour la suite (aucune application avant re-mesure)

1. **Ne rien appliquer.** Ni socle 4900, ni médiane communale. Le produit ne doit pas déclarer
   ~94 % de l'île inconstructible sur un instrument prix biaisé.
2. **Le back-test devient le test d'acceptation de tout instrument prix.** Avant toute
   application, re-dériver un prix de sortie candidat (pistes : restreindre aux APPARTEMENTS
   comme proxy du collectif ; retenir un percentile haut p75/p90 plutôt que la médiane ; relever
   `N_MIN` pour fiabiliser ; distinguer le libre du social) puis **re-passer E1/E3 : le bon
   instrument est celui sous lequel les opérations réellement construites ressortent
   majoritairement viables.** Tant qu'E1 reste massivement négatif, l'instrument est faux.
3. **Départager prix vs coût** : mesurer, sur E1, la sensibilité conjointe (prix p75 ×
   construction bas de fourchette 2 300) — si le réel se recolle, le partage d'erreur est
   quantifié.
4. **Préséance validée conservée** (override bassin sourcé > DVF secteur > DVF commune) : elle
   reste juste comme ORDRE de repli ; c'est la VALEUR de repli (médiane) qui est en cause.

## 4 · Tiers — inchangés, prouvé et mesuré

Lecture seule intégrale : aucune écriture, seul le chemin de lecture `parcel_faisabilite` +
`compute_bilan` sollicité (jamais l'écrivain `p_v2/pipeline.py`). Golden 116/116 et tiers au bit
près, ouverture ET clôture (`/tmp/tiers_backtest_cloture.txt`, `/tmp/golden_backtest_cloture.txt`).
Clause d'honnêteté maintenue : le golden ne couvre aucun champ de charge — il ne protège pas ce
périmètre à l'application ; condition d'arrêt inchangée (un tier bouge = arrêt).

## Artefacts

`/tmp/backtest_reel_phaseA.py` (LECTURE SEULE, 3 épreuves), résultats à l'euro
`/tmp/backtest_e1.json` (1 137), `/tmp/backtest_e2.json` (1 267), `/tmp/backtest_e3.json` (42).
Relevés d'état ouverture/clôture golden + tiers dans `/tmp`.

---

# SUITE — segmentation marché vs social/aidé + sensibilité coût×taille (28/07/2026)

Mesure exigée par Vic avant toute re-dérivation du prix : la cohorte E1 n'est pas qualifiée
(une opération de marché ne se monte pas à perte ; 66 % vendaient sous le seuil de bascule → une
part n'est pas du marché). Segmentation par le **pétitionnaire du permis** (SIREN Sitadel).
**LECTURE SEULE** : la charge n'est PAS recalculée, on filtre la population des charges déjà
mesurées (`/tmp/backtest_e1.json`, `e3.json`) ; la sensibilité coût est recomposée
analytiquement (`charge(coût) = c_prog + SDP × (2550 − coût)`, le coût entre linéairement).
Bailleurs sociaux / SEM réunionnais identifiés par 7 SIREN confirmés (SHLMR 310895172,
SIDR 310863592, SODEGIS 380177170, SEDRE 310863378, SEMADER 380572453, SEM Réunion 332824242,
SODIAC 378918510 ; faux positifs de nom écartés — TEYSSEDRE, etc.). Couverture pétitionnaire :
610/1036 permis E1 (**59 %** ; 41 % « inconnu », sans SIREN — volume faible, 18 % des logements,
opérations petites, peu compatibles avec du gros social qui, lui, dépose toujours au SIREN).

## 9 · Le social ne domine PAS l'île — l'hypothèse de catégorie est réfutée

Répartition du collectif 2021+ (≥ 3 lgt) :

| Segment | permis | logements |
|---|---|---|
| Social / SEM (bailleurs confirmés) | 96 (9 %) | 2 890 (**20 %**) |
| Marché ou défisc (privé identifié) | 514 (50 %) | 8 659 (61 %) |
| Inconnu (sans pétitionnaire) | 426 (41 %) | 2 614 (18 %) |

**Parmi les identifiés : social = 16 % des permis, 25 % des logements.** Le social est un quart
du collectif réunionnais, **pas l'essentiel**. (Borne haute : même en reversant dans l'« aidé »
le SNC IP1R — 536 lgt, véhicule institutionnel probablement intermédiaire/LLI — et les SCCV/SCI
défisc du segment « marché », l'aidé resterait minoritaire à l'échelle de l'île.)

## 10 · Retirer le social ne recolle PAS le modèle — le marché échoue encore

Même charge, population filtrée :

| Segment | E1 : charge ≤ 0 | E3 : payé > charge | E3 : charge ≤ 0 |
|---|---|---|---|
| **Marché ou défisc** | **365 / 527 = 69 %** | **22 / 22 = 100 %** | 20 / 22 = 91 % |
| Social / SEM | 96 / 127 = 76 % | 3 / 3 = 100 % | 2 / 3 = 67 % |
| Inconnu | 334 / 364 = 92 % | 11 / 11 = 100 % | 9 / 11 = 82 % |

Passer de 78 % (global) à **69 % (marché seul)** ne sauve rien. **Par l'arbre de décision de Vic
(point 3) : même le marché échoue → le levier coût est en cause. Testé ci-dessous.**

## 11 · Sensibilité coût × TAILLE d'opération (marché, 525 op. après trim artefacts)

% de charge ≤ 0 selon le coût de construction (€/m² SDP) et la taille :

| Taille (lgt) | n | @2550 (audité) | @2300 | @2000 | @1800 |
|---|---|---|---|---|---|
| 3-4 | 171 | 86 % | 71 % | 48 % | 33 % |
| 5-9 | 127 | 66 % | 52 % | 41 % | 25 % |
| **10-19** | 84 | **42 %** | 28 % | 20 % | 11 % |
| 20+ | 143 | 65 % | 51 % | 41 % | 21 % |
| **TOTAL** | 525 | **69 %** | 54 % | 40 % | 25 % |

**Coût de construction €/m² SDP qui annulerait la charge, au prix DVF-local réel** (médiane) :
3-4 lgt → **2 018** · 5-9 → 2 219 · **10-19 → 2 573** · 20+ → 2 123 · TOTAL → 2 195.

**Lecture** :
- **Le levier coût est réel MAIS c'est la TAILLE qui structure tout.** Un coût unique de 2 550
  appliqué à toutes les opérations est faux : le coût implicite d'équilibre va de 2 018 (petit)
  à 2 573 (moyen). Le collectif de 4 logements à Saint-Benoît et l'immeuble de 15 ne se
  construisent pas au même €/m² — la mesure le confirme, Vic avait raison.
- **Le segment 10-19 logements — le collectif de marché « normal » — est le plus proche du
  vrai** : 42 % ≤ 0 à coût audité, et son coût implicite d'équilibre (2 573) **coïncide avec le
  2 550 audité**. Là, le modèle est presque juste ; une simple économie d'échelle le recollerait.
- **Les petites opérations (3-4 lgt, 86 % ≤ 0) NE se corrigent PAS par un coût plus bas** (elles
  coûtent PLUS cher au m², pas moins) : leur échec vient d'ailleurs — soit elles se vendent bien
  au-dessus de la médiane DVF (instrument prix), soit elles sont construites pour louer/garder
  (pas de prix de sortie de marché applicable). **Les deux leviers se cumulent, aucun seul ne
  suffit.**

## 12 · Le fait produit — VRAI, mais COMMUNE PAR COMMUNE (révision du point 4 de Vic)

Le social ne domine pas l'île, mais sa part varie du tout au tout selon la commune (% social
parmi le collectif identifié) :

| Social DOMINE (charge de marché inapplicable) | % | Marché DOMINE (le modèle doit tenir) | % |
|---|---|---|---|
| Le Port | 96 | Sainte-Marie | 4 |
| Entre-Deux | 97 | Saint-Pierre | 13 |
| Saint-Philippe | 84 | Saint-Denis | 14 |
| Petite-Île | 76 | Saint-Louis | 17 |
| Cilaos | 72 | Les Avirons | 17 |
| Bras-Panon | 60 | Saint-Leu | 21 |
| Saint-Joseph | 56 | La Possession | 23 |
| La Plaine-des-Palmistes | 53 | Saint-Benoît | 26 |

(Le Tampon, Saint-André, Salazie, Sainte-Rose, Les Trois-Bassins : aucun social identifié →
collectif de marché ou petit privé.)

**Deux régimes, deux diagnostics :**
1. **Communes à social dominant** (Le Port, Entre-Deux, Saint-Philippe, Petite-Île, Cilaos,
   Saint-Joseph, La Plaine, Bras-Panon) — ce sont les communes les moins chères, où le neuf DVF
   était le plus bas. **Le fait produit de Vic (point 4) TIENT, à leur échelle** : « Charge
   foncière de marché non atteignable sur cette commune — le collectif y est majoritairement
   social ou aidé. » Ce n'est pas une régression, c'est l'information exacte, et elle intéresse
   les bailleurs sociaux (dans la cible).
2. **Communes à marché dominant** (Sainte-Marie 4 % social, Saint-Denis, Saint-Pierre,
   Saint-Louis, Saint-Leu…) — le collectif y EST de marché, et pourtant le back-test le déclare
   non viable (Sainte-Marie : 64/64 ≤ 0). **Ici PAS d'erreur de catégorie : c'est l'instrument.**
   Prix DVF-médian sous-évalué (population maison-dominée) + coût unique sans économie d'échelle.

## 13 · Conclusion et prochaine mesure (rien n'est appliqué)

- **Social minoritaire à l'échelle de l'île (20-25 %)** ; l'échec E1 n'est PAS un simple artefact
  de catégorie. Mais **le fait produit tient commune par commune** là où le social domine (8
  communes listées) → formulation « charge de marché non atteignable » à servir CIBLÉE, jamais
  île entière.
- **Le modèle est presque juste sur le collectif de marché de taille normale (10-19 lgt) en
  commune de marché** ; il échoue sur (a) les petites opérations et (b) les communes bon marché,
  par cumul instrument-prix + coût-unique-sans-taille.
- **Prochaine mesure (avant toute application, acceptation = « les opérations de marché de taille
  normale ressortent majoritairement viables »)** : re-dériver le prix (appartements only,
  percentile haut p75-p90, `N_MIN` relevé) ET introduire un coût variable par taille d'opération,
  puis re-passer E1/E3 sur le sous-ensemble marché en régime « commune de marché ». Départager la
  part respective des deux leviers sur ce sous-ensemble propre.
- **Second mode de bilan (opération sociale)** : hors de ce mandat, mais la mesure le motive —
  25 % des logements et la majorité de 8 communes en relèvent.

Rien n'est appliqué. Aucun re-run de scoring. Invariant tiers inchangé (120 / 1031 / 3587 /
72980 / 353945). Artefacts : `/tmp/segment_marche_social.py`, `/tmp/cout_taille_sensibilite.py`
(LECTURE SEULE, recomposition analytique — aucune écriture).

---

# SUITE 2 — trois catégories qualifiées + instrument prix trouvé (28/07/2026)

Arbitrage Vic : il n'y a pas deux catégories d'opérations mais **trois**, et le bilan promoteur
ne s'applique qu'à la troisième. Mesures ci-dessous (LECTURE SEULE, aucune écriture, aucun re-run
de scoring).

| Catégorie | Équilibre réel | compute_bilan s'applique ? |
|---|---|---|
| Social / aidé (~25 % des logements) | subventions, LLS/LLTS | ❌ |
| Patrimonial 3-4 lgt, build-to-hold | rendement locatif + défisc (`q_v7_defisc`) | ❌ |
| **Promotion de marché, vendue (≥ 10 lgt)** | prix de sortie − coûts − marge | ✅ |

## 14 · Catégorie 2 qualifiée sur PIÈCES (pas supposée) — test build-to-hold

Pour chaque opération E1, revente DVF observée APRÈS le PC (cohorte **2021-2022**, la moins
censurée : 3-5 ans écoulés). « Tenue » = jamais revendue = build-to-hold.

| Taille (lgt) | n | vendue post-PC | **tenue (build-to-hold)** |
|---|---|---|---|
| 3-4 | 293 | 28 % | **72 %** |
| 5-9 | 103 | 35 % | 65 % |
| 10-19 | 80 | 51 % | 49 % |
| 20+ | 118 | 47 % | 53 % |

**72 % des opérations de 3-4 logements ne sont jamais revendues** : un particulier qui bâtit 3-4
logements les garde pour louer — ni vente, ni prix de sortie, ni marge de promoteur. Le taux de
vente double vers les grandes (28 % → 51 %). La catégorie 2 est réelle et volumineuse.
*Caveats* : censure à droite résiduelle (un PC 2022 s'achève ~2024, DVF parcelle s'arrête au
31/12/2025) et VEFA off-plan mal captée au 974 → le taux « tenu » est une borne HAUTE ; le
gradient petit→grand, lui, est robuste. Le 20+ (47 %, sous les 10-19) est contaminé par le
social/SEM qui se garde en gestion locative sociale.

## 15 · Test d'acceptation resserré — et PASSÉ

Sous-ensemble = **promotion de marché véritable** : ≥ 10 lgt + commune de marché (social < 50 %)
+ commune couverte par le nouvel instrument, non-social ; variante STRICTE = + revente post-PC
observée. Charge RECALCULÉE (`compute_bilan`, programme réel) en changeant **seulement le prix**.

Nouvel instrument prix : **APPARTEMENTS seuls** (proxy du collectif), ventes ≤ 3 ans
post-achèvement, **N_MIN ≥ 10**, percentile au niveau commune. Coût **audité 2 550** conservé
(implicite d'équilibre des 10-19 = 2 573, déjà juste — §11).

| Sous-ensemble | ancien prix (médiane mixte) | **appt p50** | **appt p75** | appt p90 |
|---|---|---|---|---|
| Large (≥10, marché, non-social ; n=178) | 59 % viables | 80 % | **93 %** | 99 % |
| **Strict (+ vendu ; n=85)** | — | 84 % | **95 %** | 99 % |

**Le modèle est validé là où il s'applique.** Sur la promotion de marché vendue, l'instrument
appartement fait ressortir **84 % (p50) à 95 % (p75)** d'opérations viables — contre l'effondrement
de la médiane mixte. **L'erreur était bien l'instrument prix** (la médiane noyait le collectif
sous les maisons), pas le modèle. Le coût audité tient.

## 16 · L'instrument trouvé (et sa discipline)

- **Appartements uniquement** : c'est le levier qui recolle (dès le p50 : 80-84 %). Le percentile
  n'est que du réglage fin.
- **p75 recommandé comme ancre** (93-95 %), p50 comme plancher. **p90 (99 %) SUR-corrige** — il
  réintroduit l'optimisme du 4900, à écarter.
- **N_MIN ≥ 10, résolution commune** : 6 communes couvertes (Saint-Denis 112 appt, Saint-Pierre 76,
  Saint-Paul 54, Saint-Leu 41, Le Tampon 36, La Possession 12). Le p50 appartement y dépasse déjà
  le seuil 3 859 partout sauf La Possession (n=12, fragile).
- **Ailleurs = « non calculable », et c'est CORRECT.** Sainte-Marie (que le back-test donnait
  64/64 ≤ 0 à la médiane mixte) a < 10 ventes d'appartements : l'instrument appartement **s'abstient**
  au lieu d'asserter un chiffre faux. Non calculable > faux. Sa faillite précédente était
  l'artefact maison, pas une non-viabilité réelle.
- **Préséance conservée** : override bassin sourcé > appt secteur (si ≥ N_MIN) > appt commune >
  non calculable. Le repli île est définitivement écarté.

## 17 · Le fait produit — trois formulations, commune par commune

1. **Communes à social dominant** (Le Port 96 %, Entre-Deux 97 %, Saint-Philippe 84 %,
   Petite-Île 76 %, Cilaos 72 %, Bras-Panon 60 %, Saint-Joseph 56 %, La Plaine 53 %) →
   « **Charge foncière de marché non atteignable — le collectif y est majoritairement social ou
   aidé.** » Information exacte, cible bailleurs sociaux.
2. **Communes de marché couvertes** (Saint-Denis, Saint-Pierre, Saint-Paul, Saint-Leu, Le Tampon,
   La Possession) → le modèle tient avec l'instrument appartement (§15). C'est là qu'il sert.
3. **Communes de marché non couvertes** (Sainte-Marie, Saint-Louis, Les Avirons, Saint-Benoît,
   L'Étang-Salé : < 10 ventes d'appartements) → « **marché du collectif non observable (n
   insuffisant) — charge non calculable** », jamais un chiffre inventé.
4. **Petites opérations patrimoniales (3-4 lgt, build-to-hold)** → « **hors périmètre du bilan
   promoteur : opération de rendement locatif, pas de prix de sortie de marché.** »

## 18 · Second mode de bilan — mandat produit à part entière (consigné)

Motivé par DEUX populations, pas une : **social/aidé** (25 % des logements, majorité de 8 communes)
**et patrimonial locatif** (72 % des petites opérations). Un bilan « opération sociale / locative »
(équilibre par subventions + rendement locatif + défisc, pas par prix de sortie − marge) touche
directement la cible bailleurs sociaux. **Hors de ce mandat** — à ouvrir comme mandat distinct.

## 19 · Conclusion

- **Modèle validé** sur son périmètre (promotion de marché vendue ≥ 10 lgt) : 84-95 % viables avec
  l'instrument appartement, coût audité confirmé.
- **Instrument trouvé** : appartements seuls, p75 (plancher p50), N_MIN ≥ 10, commune ; p90 écarté.
- **Deux catégories hors périmètre** (social, patrimonial locatif) qualifiées sur pièces —
  ce ne sont pas des échecs du modèle.
- **Rien n'est appliqué.** L'application (résolution appartement par commune + préséance + coût par
  taille pour les < 10 lgt servis + étiquettes « non calculable » commune par commune) reste au
  point d'arrêt Vic, avec le back-test comme test d'acceptation permanent. Invariant tiers inchangé
  (120 / 1031 / 3587 / 72980 / 353945). Artefacts : `/tmp/rederive_acceptation.py`,
  `/tmp/segment_marche_social.py`, `/tmp/cout_taille_sensibilite.py` (tous LECTURE SEULE).

---

# SUITE 3 — composition du quartile bas : p50 ou p75 tranché par la POPULATION (28/07/2026)

Dernière mesure avant application (arbitrage Vic) : p75 ne se justifie que si le bas de la
distribution des appartements neufs est du produit aidé/plafonné. Sinon p75 est optimiste et p50
s'impose. **La justification doit porter sur la population, jamais sur le score du test.**
DVF public ne porte pas l'identité vendeur → signal = **pétitionnaire du PC d'origine** sur la
parcelle (couverture 255/331 = 77 % des ventes d'appartements des 6 communes). LECTURE SEULE.

## 20 · Le quartile bas est du produit aidé — mais SEULEMENT à Saint-Denis

Composition des ventes d'appartements neufs (6 communes), quartile bas (≤ p25 communal) vs reste :

| Zone | n | prix moyen | social | privé | inconnu | % social des identifiés |
|---|---|---|---|---|---|---|
| **Q1 (quartile bas)** | 84 | 2 616 | 24 | 34 | 26 | **41 %** |
| Q2-Q4 (reste) | 247 | 4 670 | 11 | 186 | 50 | 6 % |

Le quartile bas est **7× plus social** que le reste (41 % vs 6 %) → la traîne basse EST enrichie
en aidé. **Mais la contamination est CONCENTRÉE** : les 24 ventes sociales du quartile bas sont
**toutes à Saint-Denis** (24 des 28 ventes de son quartile bas = 86 % social). Dans les 5 autres
communes couvertes, le quartile bas contient **ZÉRO vente sociale identifiée** (Saint-Pierre,
Saint-Leu, Saint-Paul, Le Tampon, La Possession).

**Conséquence directe (population, pas score)** : un p75 uniforme serait une correction légitime
à Saint-Denis mais une hypothèse OPTIMISTE dans 5 communes sur 6. La correction propre n'est pas
un percentile arbitraire, c'est **exclure les ventes de bailleurs sociaux puis prendre la
médiane du marché** :

| INSEE | Commune | n | dont social | p50 plein | **p50 marché (excl. social)** | p75 plein |
|---|---|---|---|---|---|---|
| 97411 | Saint-Denis | 112 | 35 | 4 005 | **4 275** | 4 572 |
| 97416 | Saint-Pierre | 76 | 0 | 4 258 | 4 258 | 4 652 |
| 97422 | Le Tampon | 36 | 0 | 4 318 | 4 318 | 4 491 |
| 97415 | Saint-Paul | 54 | 0 | 4 730 | 4 730 | 5 276 |
| 97413 | Saint-Leu | 41 | 0 | 4 953 | 4 953 | 5 574 |
| 97408 | La Possession | 12 | 0 | 2 638 | 2 638 | 2 879 |

La médiane de marché = la médiane pleine dans 5 communes (rien à exclure) ; elle ne remonte
qu'à Saint-Denis (4 005 → 4 275), là où l'aidé traîne le bas.

## 21 · Recommandation d'instrument (population-justifiée) + confirmation

**Instrument retenu : médiane des ventes d'appartements neufs APRÈS exclusion des ventes de
bailleurs sociaux (« médiane de marché »), N_MIN ≥ 10, résolution commune.** Justification —
une phrase, sur la population : *« Le quartile bas n'est du produit aidé qu'à Saint-Denis (86 %
de son quartile bas est construit par un bailleur social) ; l'en exclure y porte la médiane de
marché à 4 275 €/m². Dans les cinq autres communes couvertes, aucune vente aidée n'est
identifiable : la médiane pleine EST la médiane de marché. »*

**p75 est ÉCARTÉ comme règle générale** : il n'est justifié par la population qu'à Saint-Denis,
et la médiane-de-marché y produit le même effet pour la bonne raison. Confirmation (le score
vient APRÈS la justification, il ne la fonde pas) :

| Sous-ensemble | p50 plein | **p50 marché (excl. social)** |
|---|---|---|
| Strict vendu (n=85) | 84 % | **93 %** |
| Large (n=178) | 80 % | **92 %** |

La médiane-de-marché atteint l'effet du p75 (92-93 %) sans son optimisme. **Caveats honnêtes** :
(a) les ventes « inconnu » du quartile bas (26) pourraient masquer de l'aidé non exclu — mais les
bailleurs déposent au SIREN, l'inconnu est surtout du petit privé ; impact non matériel (le test
passe). (b) **La Possession est fragile** : n=12 (au ras de N_MIN) et médiane 2 638 SOUS le seuil
de bascule 3 859 — la traiter avec prudence à l'application (relever N_MIN, ou la basculer en
« non calculable » si le marché n'y est pas assez épais).

## 22 · Gravé dans le mandat (arbitrages Vic 28/07)

- **Test d'acceptation PERMANENT** de tout instrument prix ou coût : sous-ensemble **promotion de
  marché véritable** (vendue post-PC + ≥ 10 lgt + commune de marché couverte), critère
  **« majoritairement viables »**. Tout futur changement de prix ou de coût le repasse AVANT
  application. Harnais : `/tmp/rederive_acceptation.py`, `/tmp/confirme_marche_only.py`.
- **Un correctif à la fois** : le PRIX d'abord (ce mandat). Le **coût variable par taille
  d'opération = MANDAT SUIVANT**, avec sa propre mesure d'impact — chiffre déjà en main : coût
  d'équilibre implicite **2 018 €/m² (petites 3-4 lgt) → 2 573 (moyennes 10-19)** (§11). NE PAS
  le mélanger à l'application prix.
- **Second mode de bilan** (opération sociale + patrimonial locatif) = mandat produit distinct,
  désormais NÉCESSAIRE (18 communes non couvertes en bilan de marché ; cible bailleurs sociaux).
- **Préséance finale** : override bassin sourcé > appt secteur (≥ N_MIN) > appt commune
  (médiane de marché) > **non calculable**. Repli île définitivement écarté.

**Rien n'est appliqué.** Aucun re-run de scoring. Golden 116/116 et tiers au bit près à chaque
tour (120 / 1031 / 3587 / 72980 / 353945). La mesure du quartile bas close le diagnostic ;
l'application est au point d'arrêt Vic.

---

# APPLICATION (28/07/2026) — instrument appartement de marché + suppression du socle 4900

GO Vic. Séquence stricte (mêmes gates que les hypothèses du bilan). Branche
`feat/calibration-prix-appartement-marche`. **Fable ne merge pas — Vic merge en `--no-ff`.**

**Décisions Vic appliquées** : (1) **La Possession → « non calculable »** (n=12, médiane 2 638 <
seuil 3 859 ; règle gravée : N_MIN franchi de justesse + médiane sous le seuil = instrument non
fiable, PAS une commune non viable — servira aux communes qui franchiront N_MIN plus tard).
**Couverture finale : 5 communes** (Saint-Denis, Saint-Pierre, Saint-Paul, Saint-Leu, Le Tampon).

**Ce qui a été fait, dans l'ordre :**
1. Golden 116/116 + tiers relevés avant. Golden ne couvre aucun champ charge/marge (vérifié).
2. `dvf_prix_sortie_neuf` reconstruit : appartements de marché (hors bailleurs sociaux, SIREN
   pétitionnaire du PC), N_MIN ≥ 10, secteur→commune, règle de fragilité. 5 communes + 6 secteurs.
3. **Socle global 4900 supprimé** (`bilan_calibration.py`) + **purge de boot ciblée**
   (`models.py` `ensure_bilan_params`, valeur exacte / provenance / secteur global — piège du 2100
   évité) + purge appliquée en base (1 ligne). Overrides de bassin sourcés conservés (préséance).
4. Cœur (`faisabilite/db.py`) : prix résolu par **préséance** override bassin sourcé > dvf secteur
   > dvf commune > **non calculable**. Hors 5 communes : parcelle **servie avec la mention**
   (jamais écartée, M26-A), formulation par cas (social dominant / marché non observable). score_e
   recomposé (estimables 51 926 → 29 353).
5. Golden **116/116** + tiers **au bit près** (120/1031/3587/72980/353945) après. Aucun tier bougé.
6. Acceptation par le **chemin de production** (`resolve_prix_neuf_marche`) : promotion de marché
   ≥ 10 lgt → **89-91 % viables** (bande validée ~90 % ; léger écart vs 92-93 % = résolution
   SECTEUR plus locale + La Possession écartée, deux effets corrects). Fiche vérifiée en direct :
   Saint-Denis/Saint-Paul → charge réelle ; Sainte-Marie/Le Port → non calculable servi.

**Tests** : 2 verrous d'ancien socle mis à jour (nouvelle vérité), 3 verrous ajoutés (socle hors
seed, formulations imposées au mot près, purge boot idempotente). 75 tests verts sur le périmètre.

**RÉSERVE consignée — consommateurs hors fiche (correction SUIVANTE, un correctif à la fois)** :
seule la fiche utilisait le socle 4900. Le **Copilote, le Banquier, l'Argumentaire, les modules**
calculent leur charge sur `sector_price` (DVF de l'EXISTANT, ~2 265) — jamais le socle — et sont
déjà **non-filtrants** (parcelle servie, fait charge omis si absent : comportement M26-A vérifié).
MAIS ils ne consomment PAS encore le nouvel instrument : ils afficheront donc une charge (base
DVF-existant) là où la fiche dit « non calculable ». Divergence **pré-existante** (la fiche était
à 4900, eux à 2 265) désormais plus visible → à router sur `resolve_prix_neuf_marche` dans une
correction dédiée, avec sa propre passe de vérification. Signalé, non bundlé.
