# MANDAT CALIBRATION ESTIMÉES — les 10 valeurs provisoires du chantier calibration web

**SPEC — exécution différée** (rédigé le 28/07/2026, arbitré par Vic le jour même : phase A =
priorité n°1 du mandat, §3 déjà exécuté hors phase A ; **ne pas lancer avant la clôture de la
phase 4 PLU** — un correctif à la fois, ses mesures porteraient sinon sur des charges
mouvantes. Vic donne le signal). Le contrôle `labuse bilan-params-perimes` — posé par ce mandat — a signalé
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
| `ratio_vendable` (*) | ~~0.80~~ | 15/06 | mort — **RETIRÉ le 28/07** (§3) | — |
| `bonus_vue_mer_pct` (*) | ~~15~~ | 15/06 | mort — **RETIRÉ le 28/07** (§3) | — |

Hors liste mais MÊME famille (§2.1) : `prix_m2_neuf` global `*` = **4900**, provenance
« sourcée » — sourcée pour Saint-Paul, appliquée à toute l'île.

## 2 · Les deux prioritaires (Vic, 28/07)

### 2.1 Prix de sortie neuf — PRIORITÉ N°1 (arbitrage Vic 28/07/2026)

**Le symétrique exact du bug corrigé** (nommé ainsi par Vic) : 4900 €/m² est un chiffre
saint-paulois — l'une des communes les plus chères de l'île — servi comme socle global aux
23 communes. La charge foncière étant ce qui reste après retrait des coûts du CA, un prix de
sortie trop haut SURESTIME la charge : vraisemblablement une seconde couche d'optimisme, avec
un levier deux fois supérieur à celui du coût (**±17,6 % de prix = ±102 % de charge sur le
témoin, −17,6 % le fait basculer en non viable** ; le coût corrigé pesait ×2). Même structure
que le repli PLU générique et que le 2100 : **une valeur d'un cas particulier appliquée par
défaut à tous les autres, dans le sens généreux — troisième occurrence du motif en deux
jours.**

**La phase A n'est PAS « confirmer 4900 » : c'est remplacer un socle global par une résolution
par commune**, avec `dvf_prix_sortie_neuf` qui existe déjà et que score_e consomme (repli
secteur → commune, niveau tracé). Les 5 overrides sectoriels existants deviennent la règle,
pas l'exception. Le 4900 ne survit — au plus — que comme valeur de Saint-Paul.

**Mesure BLOQUANTE avant toute application** : l'écart de charge foncière par commune entre le
socle 4900 et le prix réel local, avec le nombre de bascules viable → non viable (échantillons
seedés `m26-hyp`). **Si l'ampleur est comparable à celle du coût de construction, c'est un
mandat de même priorité, pas une suite** (règle Vic). Sens attendu : partout où le neuf local
vaut moins que le 4900 saint-paulois — vraisemblablement la majorité des 23 communes — la
charge servie est SURestimée et des « viables » basculeront non viables, comme pour le coût ;
seules les poches plus chères que Saint-Paul iraient dans l'autre sens.

### 2.2 VRD 90 €/m² — bloc de trois, VALIDÉ par Vic (28/07) : traiter en un lot

±17,6 % ne pèse que ±4 % de charge : ce n'est pas la précision qui inquiète, c'est l'ORDRE DE
GRANDEUR (« à confirmer par devis local » dès l'origine, jamais confirmé). Un VRD réel à
2-3× (viabilisation en pente, réseaux éloignés — cas fréquents à La Réunion) pèserait 8-12 %
de charge en terrain plat et bien plus combiné aux majorations pente/ANC (elles-mêmes
estimées : 30 % et 25 % s'appliquent multiplicativement au 90). Les trois valeurs VRD forment
un BLOC à confirmer ensemble, par devis réels.

## 3 · Les deux paramètres morts — TRANCHÉ ET FAIT (Vic 28/07/2026, hors phase A)

`ratio_vendable` (0,80) et `bonus_vue_mer_pct` (15) n'étaient lus par **aucun moteur**
(`compute_bilan` lit `coef_rendement` des hypothèses YAML — 0,80 aussi — pas
`ratio_vendable` ; `bonus_vue_mer_pct` n'était même pas au registre : ligne orpheline en
base). **Retirés le 28/07** (registre/panneau, seed, gabarit CSV, base + purge de boot
idempotente, refus à l'injection testé) : « afficher des curseurs qui ne calibrent rien est
trompeur pour l'utilisateur et dangereux pour nous — quelqu'un finira par les ajuster en
croyant agir sur le modèle » (Vic). Les re-brancher = décision explicite avec sa mesure
d'impact. Mention portée à `RAPPORT_CALIBRATION_WEB.md`.

## 4 · Méthode (phases, points d'arrêt)

- **A — PRIORITÉ N°1 : prix de sortie neuf, du socle global à la résolution par commune**
  (lecture seule d'abord). Mesure BLOQUANTE : écart de charge par commune entre socle 4900 et
  prix réel local (`dvf_prix_sortie_neuf`, repli secteur → commune comme score_e) + bascules
  de verdict, sur les échantillons seedés `m26-hyp` étendus aux communes non calibrées ; en
  annexe, sensibilité ±17,6 %/±50 % des autres paramètres vivants. **Point d'arrêt Vic —
  si l'ampleur est comparable au coût de construction, requalification en mandat de même
  priorité.** L'application (résolution par commune, les 5 overrides deviennent la règle) ne
  part qu'après ce point d'arrêt.
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
