# RAPPORT — Dossier communal, PHASE 0 : inventaire OAP (aucune ingestion, aucune écriture)

**Exécuté le 28/07/2026** (exécuteur Claude Code). **LECTURE SEULE intégrale** — aucune
ingestion, aucune écriture ; les jointures spatiales ont utilisé des tables TEMP de session.
Invariant tiers du run servi `q_v7_defisc` vérifié inchangé en clôture
(120 / 1031 / 3587 / 72980 / 353945).

> **Réserve d'entrée, factuelle** : le fichier `docs/mandats/MANDAT_DOSSIER_COMMUNAL.md`
> **n'existe pas** dans le dépôt (ni suivi, ni non suivi, ni sur une autre branche). Je ne l'ai
> pas lu et n'en ai pas inventé le contenu. Ce rapport exécute strictement l'inventaire décrit
> dans ta consigne : périmètres d'OAP dans la donnée PLU, consommateurs réels (méthode
> `constructible_neuf` — grep exhaustif), et le chiffre des parcelles servies en OAP par commune
> × tier. Si le mandat écrit dit autre chose, à réconcilier avant la phase 1.

## 0 · Les deux faits qui décident

1. **L'OAP existe dans la donnée** : `spatial_layers`, `kind='plu_gpu_prescription'`,
   `subtype='18'` (« Secteur comportant des orientations d'aménagement et de programmation
   (OAP) », code CNIG `typepsc=18`). **100 features, 7 communes, géométries toutes valides.**
   Ce n'est PAS la « table prescriptions » (elle n'existe pas sous ce nom) : c'est la couche
   GPU générique, où l'OAP est un sous-type parmi 20.
2. **L'OAP est lue mais NON discriminante** : dans le seul chemin servi qui la touche (cascade
   `PrescriptionPluLayer`), une parcelle en OAP produit un **`passed()` informatif à pénalité
   nulle**. Elle n'entre ni dans le tier, ni dans la capacité/emprise, ni dans le bilan. Même
   forme que le trou `constructible_neuf` : la donnée est là, elle ne pilote rien.

## 1 · Où vit l'OAP (donnée)

`plu_gpu_prescription` subtype `18`, par commune :

| Commune | features OAP | features nommées | ha OAP |
|---|---|---|---|
| Le Tampon | 13 | 1 | 1 048 |
| Saint-Paul | 15 | **15** | 603 |
| Le Port | 8 | **8** | 265 |
| Saint-Joseph | 19 | 1 | 83 |
| Sainte-Marie | 12 | 1 | 67 |
| Sainte-Suzanne | 21 | 1 | 51 |
| L'Étang-Salé | 12 | **11** | 44 |
| **Total** | **100** | — | **2 161** |

**Caveat qualité pour un dossier qui citerait l'OAP par nom** : seules Saint-Paul, Le Port et
L'Étang-Salé portent un `name`/`libelle` par OAP dans les attrs GPU (ex. « OAP 1.2 - Le front
de mer », « OAP Portes de l'Océan »). Les 4 autres communes n'ont qu'un libellé unique « OAP »
répété sur toutes leurs features — nommer l'OAP précise y exigera le règlement PDF, pas la seule
couche GPU. (Le subtype `05` « périmètre d'attente de projet L.151-41 » cite parfois l'OAP dans
des ER — « ER 31 … cf. OAP » — mais ce n'est pas l'OAP : ne pas confondre.)

## 2 · Consommateurs (méthode `constructible_neuf` : grep exhaustif, effet réel prouvé)

`plu_gpu_prescription` / `oap_typepsc` / OAP sont référencés à **trois** endroits servis ; **aucun
ne change un verdict, un tier, une capacité ou un bilan** :

1. **Cascade — `src/labuse/cascade/layers/phase1.py:439`** (`PrescriptionPluLayer`). Mapping
   `config/cascade_rules.yaml:100` → `oap_typepsc: ["18"]` (donc la branche OAP s'exécute bien,
   ce n'est pas un code orphelin). Effet : `passed(self.name, "Orientation d'aménagement (OAP) :
   {lib} — secteur de projet encadré (principes d'aménagement à respecter).")`. Le commentaire du
   code est explicite (l. 432-434) : *« Contraintes de PROGRAMME / quasi communales (mixité,
   eaux pluviales, OAP) : RÉELLES mais NON discriminantes → PASS informatif, recensé, tracé,
   AUCUNE pénalité, pas de bruit dans la vigilance. »* → **zéro impact sur le tier.**
2. **Faisabilité — `src/labuse/faisabilite/db.py:211`**. Lit les prescriptions, mais seulement
   `emplacement_reserve_typepsc` (déduction d'emprise), `mixite_sociale_typepsc` et
   `eaux_pluviales_typepsc` pour le contexte éco. **L'OAP (18) n'y figure pas** → aucun effet sur
   l'emprise constructible, la SDP résiduelle ou la charge foncière.
3. **Flash — `src/labuse/flash/data.py:136`**. Liste les libellés de prescriptions dans le
   one-pager Flash (affichage only). Aucune logique.

Surface côté fiche servie : le `passed()` OAP apparaît dans la **trace cascade complète**
(ligne verte informative) mais **PAS dans le résumé de vigilance** — `api/resume.py:92` ne
remonte `prescription_plu` que pour les HARD_EXCLUDE / SOFT_FLAG fort. Le filtre IA
(`api/ia.py`) et la sémantique NL (`api/nl_semantics.py`) connaissent `prescription_plu` comme
famille, jamais l'OAP en propre. **Aucun consommateur dans `scoring/`.**

**Verdict d'inventaire** : l'OAP est ingérée, géométriquement propre, et servie comme simple
annotation verte. C'est un signal DORMANT — présent, jamais exploité.

## 3 · Le chiffre qui décide — parcelles servies en périmètre OAP (run `q_v7_defisc`)

Jointure spatiale `geom_2975` (métrique). Trois définitions, elles convergent :

| Périmètre | brûlante | chaude | réserve fonc. | à creuser | **non-écartées** | écartées |
|---|---|---|---|---|---|---|
| Intersecte une OAP (aire > 0) | 7 | 54 | 160 | 2 662 | **2 883** | 8 519 |
| Centroïde DANS une OAP | 7 | 52 | 141 | 2 441 | **2 641** | — |
| ≥ 50 % de la parcelle couverte | 7 | 52 | 140 | 2 436 | **2 635** | — |

- **Total parcelles servies intersectant une OAP : 11 402** — dont **8 519 déjà écartées** (le
  gros du volume : l'OAP se superpose à beaucoup d'inconstructible). La population actionnable
  est les **~2 6–2 9k non-écartées**.
- **Tiers de tête en OAP : 7 brûlantes + 52 chaudes + ~140 réserve foncière ≈ 199 parcelles**,
  plus ~2 440 à creuser. **Les 7 brûlantes sont TOUTES à Saint-Paul.**
- Concentration géographique (non-écartées, ≥ 50 % couvert) : **Le Tampon 1 557 + Saint-Paul 635
  = 83 % de la masse** ; puis Le Port 194, L'Étang-Salé 103, Sainte-Marie 64, Sainte-Suzanne 51,
  Saint-Joseph 31.

## 4 · Recommandation de périmètre pour la phase 1 (scope seulement)

**Traiter l'OAP comme un signal de CONTEXTE de projet, pas comme un critère de scoring.** Une
OAP est un « secteur de projet encadré » — souvent là où la commune VEUT de la densité/du
renouvellement (front de mer, centralité, ZAC). En faire une pénalité serait un contresens ; la
cascade a raison de la classer non discriminante. Le gain d'un dossier communal est de la
**restituer comme information servie** (la parcelle est dans l'OAP « X », principes à respecter,
potentiel encadré), pas de bouger un tier.

**Périmètre recommandé, resserré par la mesure :**

1. **Cœur de phase 1 : les 199 non-écartées de tiers de tête en OAP** (7 brûlantes Saint-Paul +
   52 chaudes + 140 réserve foncière) — c'est là que l'enrichissement OAP a une valeur commerciale
   immédiate et vérifiable une par une.
2. **Deux communes portent 83 % de la masse** (Le Tampon, Saint-Paul) : commencer par elles ; ce
   sont aussi les deux plus grandes surfaces d'OAP (1 048 + 603 ha). Saint-Paul cumule l'avantage
   d'avoir ses **15 OAP nommées** dans la donnée → dossier citable sans PDF.
3. **Exclure de la phase 1 les 8 519 écartées** (l'OAP n'y ajoute rien : déjà hors périmètre) et
   **les 4 communes sans OAP nommée** (Le Tampon, Saint-Joseph, Sainte-Marie, Sainte-Suzanne) du
   volet « citer l'OAP par nom » tant que le règlement PDF n'est pas dépouillé — sinon on afficherait
   « OAP » générique, sans le principe d'aménagement, ce qui n'informe pas.
4. **Décision qui revient à Vic avant la phase 1** : l'appartenance OAP doit-elle **nuancer le
   cadrage d'opportunité** (potentiel encadré = souvent un PLUS, la commune y porte un projet) ou
   rester **purement descriptive** dans le dossier ? Les deux sont défendables ; la seconde est un
   no-op sur le score (aucun tier ne bouge), la première demande sa propre mesure d'impact. Aucune
   ne justifie de rendre l'OAP discriminante dans la cascade.

**Hors périmètre phase 1 explicitement** : aucune modification de la cascade, du scoring, du
bilan ou de l'emprise — l'inventaire ne fournit aucun motif de rendre l'OAP pénalisante.

## Artefacts

Requêtes LECTURE SEULE (tables TEMP de session, rien de persisté). Comptages reproductibles :
run `q_v7_defisc`, `spatial_layers kind='plu_gpu_prescription' subtype='18'`, jointure
`geom_2975`. Invariant tiers relevé inchangé en clôture.
