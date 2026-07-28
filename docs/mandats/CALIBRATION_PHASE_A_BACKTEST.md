# RAPPORT — Phase A, BACK-TEST CONTRE LE RÉEL : la correction par médiane DVF communale est CONTREDITE

**Exécuté le 28/07/2026** (branche `mesure/calibration-phase-a-prix-neuf`, exécuteur Claude Code).
Contre-test bloquant exigé par Vic avant toute application (§1 de son arbitrage du 28/07).
**LECTURE SEULE intégrale.** État base ouverture ET clôture : **golden 116/116 PASS, tiers du
run servi `q_v7_defisc` au bit près (120 / 1031 / 3587 / 72980 / 353945).**

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
