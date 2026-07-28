# MANDAT CALIBRATION ESTIMÉES — les 10 valeurs provisoires du chantier calibration web

**SPEC SEULEMENT — non exécuté** (rédigé le 28/07/2026 à la demande de Vic, suite du mandat
hypothèses bilan). Le contrôle `labuse bilan-params-perimes` — posé par ce mandat — a signalé
au premier run **10 valeurs « estimées » jamais confirmées depuis 37-43 jours** : le même âge
et le même chantier (calibration web des 14-15/06, `d94ff9b`/`f25e8cc`) que le
`cout_construction = 2100` dont l'instruction a montré qu'il était ancré sur une fourchette
périmée. Ce mandat instruit les 9 restantes + le socle prix neuf, une par une.

**Exécuteur** : à désigner. **Vic merge en `--no-ff`.** Pièces : `RAPPORT_CALIBRATION_WEB.md`
(dérivations d'origine + MISE À JOUR 28/07), `HYPOTHESES_BILAN_RAPPORT.md` (méthode de mesure
réutilisable, échantillons seedés `m26-hyp`).

## 0 · Le problème, en une phrase

Neuf paramètres « estimés » du bilan promoteur et un socle de prix appliqué île entière sont en
production depuis six semaines sans confirmation terrain ; une erreur « aux proportions du
2100 » (±17,6 %) sur le prix de sortie suffit à elle seule à inverser des verdicts de
viabilité — dans l'autre sens que le bug corrigé.

## 1 · Inventaire des 10 signalées (état base du 28/07/2026)

Sensibilité = effet d'un écart ±17,6 % (la proportion du 2100 vs l'audit) sur la charge de la
parcelle témoin CX1395 (chemin cœur : CA×0,76 = 1 370 k€, construction 1 079 k€, VRD 55 k€,
charge 237 k€). **Ordre de grandeur analytique à confirmer par la mesure de phase A.**

| Param (secteur) | Valeur | Date | Gouverne | Sensibilité ±17,6 % |
|---|---|---|---|---|
| `prix_m2_neuf` (Le Guillaume) | 3900 | 15/06 | CA du cœur sur ce bassin (`q1=med=q3` override) | **±102 % de la charge** (levier prix) — locale au bassin |
| `honoraires_pct` (*) | 12 | 15/06 | coef du CA (cœur ; défaut hyp ailleurs) | ±16 % |
| `marge_cible_pct` (*) | 9 | 20/06 | coef du CA (cœur) — recalée LOT 3 « fourchette 8-10 terrain » | ±12 % |
| `majoration_vrd_pente_pct` (*) | 30 | 15/06 | VRD si pente ≥ 15 % | ±7 % où déclenchée |
| `majoration_vrd_assainissement_pct` (*) | 25 | 15/06 | VRD si assainissement autonome | ~±6 % où déclenchée |
| `cout_vrd_base` (*) | 90 | 15/06 | VRD = 90 €/m² × terrain (cœur) | ±4 % — MAIS voir §2.2 |
| `frais_financiers_pct` (*) | 3 | 15/06 | coef du CA (cœur) | ±4 % |
| `prix_m2_lls` (*) | 2900 | 15/06 | CA pondéré en secteur de mixité (clause déclenchée + pct_lls 30) | fort mais localisé (zones SMS) |
| `ratio_vendable` (*) | 0.80 | 15/06 | **AUCUN moteur ne le lit** (§3) | indéfinie |
| `bonus_vue_mer_pct` (*) | 15 | 15/06 | **AUCUN moteur ne le lit** (§3) | indéfinie |

Hors liste mais MÊME famille (§2.1) : `prix_m2_neuf` global `*` = **4900**, provenance
« sourcée » — sourcée pour Saint-Paul, appliquée à toute l'île.

## 2 · Les deux prioritaires (Vic, 28/07)

### 2.1 Prix de sortie neuf — le levier n°1, et un problème de périmètre, pas de dérivation

Le 4900 n'est PAS une dérivation métropole (source : neuf Saint-Paul 2024 ~4 920 €/m²,
corroboré ~5 200) — sur ce point l'inquiétude est levée. **Le vrai défaut est le périmètre** :
ce chiffre saint-paulois est le socle global `*`, donc le CA du cœur à Saint-Denis,
Saint-Pierre et partout ailleurs est calculé au prix du neuf de Saint-Paul. La ventilation par
bassin n'existe QUE pour 5 bassins de Saint-Paul (dont l'estimée Le Guillaume 3900, échantillon
« FRAGILE » dès l'origine). Levier mesuré sur le témoin : **±17,6 % de prix = ±102 % de
charge, et −17,6 % fait basculer la parcelle en non viable** — une erreur de prix a
mécaniquement plus d'effet que l'erreur de coût qu'on vient de corriger.
À instruire : médianes `dvf_prix_sortie_neuf` par commune (la table existe, score_e s'en sert)
vs le 4900 servi — l'écart Saint-Denis/Saint-Pierre est mesurable sur pièces, sans terrain.

### 2.2 VRD 90 €/m² — faible levier au niveau saisi, ordre de grandeur non confirmé

±17,6 % ne pèse que ±4 % de charge : ce n'est pas la précision qui inquiète, c'est l'ORDRE DE
GRANDEUR (« à confirmer par devis local » dès l'origine, jamais confirmé). Un VRD réel à
2-3× (viabilisation en pente, réseaux éloignés — cas fréquents à La Réunion) pèserait 8-12 %
de charge en terrain plat et bien plus combiné aux majorations pente/ANC (elles-mêmes
estimées : 30 % et 25 % s'appliquent multiplicativement au 90). Les trois valeurs VRD forment
un BLOC à confirmer ensemble, par devis réels.

## 3 · Les deux paramètres morts — décision à prendre

`ratio_vendable` (0,80) et `bonus_vue_mer_pct` (15) ne sont lus par **aucun moteur**
(vérifié : seuls `bilan_params`/`bilan_calibration` les portent ; `compute_bilan` lit
`coef_rendement` des hypothèses YAML — 0,80 aussi — pas `ratio_vendable`). Ils sont affichés
au panneau de calibration comme s'ils calibraient quelque chose. Trancher : **brancher**
(`ratio_vendable` doublonne `coef_rendement` → plutôt le retirer et documenter que le YAML
gouverne ; `bonus_vue_mer_pct` = fonctionnalité jamais câblée → brancher ou retirer) — dans
les deux cas, plus de paramètre affiché qui ne gouverne rien.

## 4 · Méthode (phases, points d'arrêt)

- **A — Mesure de sensibilité systématique** (lecture seule) : pour chaque paramètre vivant,
  ±17,6 % et ±50 % sur les échantillons seedés `m26-hyp` (mêmes 1149 parcelles, méthode du
  mandat hypothèses bilan) → ampleur RÉELLE par commune/tier, bascules de verdict. Pour le
  prix neuf : écart mesuré `dvf_prix_sortie_neuf` par commune vs 4900. **Point d'arrêt Vic.**
- **B — Collecte des vrais chiffres** : gabarit `config/bilan_calibration_vic.csv` (TOUJOURS
  vide au 28/07 — action Vic) : coût construction (fera passer la charge d'Estimé à Sourcé),
  VRD + majorations (devis), honoraires/frais/marge (retour promoteur), prix LLS (bailleur),
  prix neuf par commune (observatoire/annonces, pattern des 5 bassins existants).
- **C — Injection** `labuse bilan-calibrate` (jamais à la main) + décision sur les 2 morts +
  golden avant/après + tiers au bit près + mesure de confirmation sur échantillons seedés.
  Les verrous du mandat hypothèses bilan (placeholder, `bilan-params-perimes`, test-verrous)
  encadrent déjà tout ça.

## 5 · Interdits

Modifier une valeur sans chiffre réel confirmé (source datée) · injecter à la main hors
`bilan-calibrate` · passer une étiquette à Sourcé sans source externe vérifiable · recalculer
score_e sans GO · toucher au socle `prix_m2_neuf` global sans avoir mesuré l'écart par commune
(phase A) · laisser un paramètre affiché sans consommateur (§3 tranché au mandat).
