# PLU-VERIF-1 — chaque règle PLU, relue à la page citée

**Branche** `audit/plu-verif-1` · worktree `~/Desktop/labuse-pluverif` · base `origin/main`.
Audit + corrections limitées au **statut** et à la **référence** des règles (jamais une
valeur inventée). Aucun run île. Les recalibrations restent hors mandat (PLU-CALIBRAGE suivant).

## Ce qui a été relu

Les règles chiffrées calibrées vivent dans `config/plu_destinations/974??_*.yaml`, bloc
`regles` de chaque zone (une feuille = une valeur + `article` + `page_pdf` + `citation` +
`statut`). Point de lecture unique : `plu.destinations.iter_regles_calibrees()`.

**Périmètre = les 2 031 règles chiffrées** (hauteur faîtage/égout/niveaux, emprise au sol,
reculs voie/limites, pleine terre, stationnement, mixité) de **23 communes**. COHERENCE-1 en
avait relu 30 (30/30) ; ce mandat les relit **toutes**.

> Hors périmètre (à mesurer dans un mandat dédié) : les **3 136 feuilles `sous_destinations`**
> (statut interdit/autorisé par destination) et les **509 clauses de `silence`** de zone. Ce
> sont des verdicts de statut, pas des valeurs chiffrées — vérification de nature différente.

### Étape 0 — inventaire (socle)
- **2 031 règles**, **23 communes** — 1 980 `valide`, 51 `propose`, 0 autre statut.
- Chaque commune calibrée a **son PDF de règlement servi en local** ; les 23 millésimes
  calibrés correspondent **exactement** au PDF servi (`etat_commune` = `calibree` partout).
- **Référence complète** (article + page) : seules **3 feuilles** sans `article`
  (Saint-Paul U2e/U3e/AU5e stationnement, toutes `propose` — non servies ; page présente).
- **0 page ILLISIBLE** : les 23 PDF portent une couche texte (aucun scan à OCRiser),
  y compris Saint-Leu 2007.

## Résultat global (2 031 règles)

| Verdict | N | % |
|---|---:|---:|
| **JUSTE** (valeur + réf. exactes, sans exception ignorée) | 1 804 | 88,8 % |
| **JUSTE + exception à afficher** (valeur exacte, la fiche tait une dérogation réelle) | 147 | 7,2 % |
| **MAUVAISE RÉFÉRENCE** (valeur exacte, page fausse) | 76 | 3,7 % |
| **FAUSSE** (valeur erronée pour la zone) | **2** | 0,10 % |
| **INDÉCIDABLE** | 2 | 0,10 % |

Méthode : le **Lot A** (script `labuse plu verif`) a tranché automatiquement 1 631 règles en
**TROUVÉ** (article + valeur + citation retrouvés sur la page citée ±1, sans exception hors
citation). Les **400** restantes (AMBIGU/ABSENT) ont été **relues une à une sur le PDF** au
**Lot B** (22 sous-lecteurs, un par commune) : 173 JUSTE, 147 JUSTE+exception, 76 mauvaises
références, 2 fausses, 2 indécidables.

## 🔴 Les 2 FAUSSES (corrigées → `propose`, valeur NON réécrite)

1. **Saint-Joseph (97412) · zone U5cvd · retrait aux limites séparatives.**
   LABUSE servait **5 m**. L'article U5 7.2 (et la citation stockée elle-même !) disent
   *« au moins égale à la moitié de la hauteur (H)… avec un **minimum de 3 mètres** »*. La
   valeur 5 m contredit sa propre citation. → passée `propose`, note « lue au PDF : 3 m (H/2, min 3 m) ».

2. **Saint-Paul (97415) · zone U1pru · retrait aux limites séparatives.**
   LABUSE servait **3 m minimum** (règle générale des zones U1). Mais U1pru est **carve-out** :
   *« Chaque construction pourra s'implanter sur une limite séparative sans limitation de
   longueur. En cas de retrait, celui-ci ne pourra excéder 5 mètres »* — un **maximum de 5 m**,
   pas un minimum de 3 m. → passée `propose`, note « lue au PDF : recul ≤ 5 m (max), pas 3 m min ».

Les deux sont des reculs latéraux ; passées en `propose`, elles ne sont **plus servies comme
sourcées** (la capacité repasse en estimée pour ces deux zones). La recalibration de la valeur
juste relève du PLU-CALIBRAGE suivant.

## MAUVAISES RÉFÉRENCES (76 — page corrigée, valeur inchangée)

Cause quasi unique : **les zones AU renvoient aux zones U** (« se reporter au règlement de la
zone U indiquée en indice »). La valeur reprise de la zone U est exacte, mais `page_pdf`
pointait la **page d'intro AU** (le renvoi) au lieu de la **page de l'article U réel**. Corrigé
sur la page portant réellement la règle.

| Commune | N | page fausse → juste (exemple) |
|---|---:|---|
| Les Trois-Bassins (97423) | 21 | zones 1AU* → pages des articles Ua/Ub/Uc |
| Sainte-Rose (97419) | 18 | 1AU* tous « p.55 » (intro AU) → articles UA/UC/UE |
| Le Port (97407) | 11 | 1AU* « p.145 » (intro) → articles U indicés |
| Saint-Louis (97414) | 11 | page du début d'article → page de la règle (ex. UA 10.2 p.17→20) |
| Saint-Leu (97413) | 6 | stationnement p.10 → **p.13** (Art. 11 dispositions générales) |
| Sainte-Marie (97418) | 6 | hauteurs « activités » p.32 → **p.35** (tableau U8.2) |
| Entre-Deux (97403) | 2 | AUb hauteur p.29 → **p.21** (art. U7.2) |
| Saint-Paul (97415) | 1 | U2h stationnement p.76 → **p.81** (tableau 12.2) |

## JUSTE + exception (147 — exception enregistrée en note)

Valeur **exacte**, mais la fiche ne dit pas une dérogation/sous-secteur présent au même
article. Motifs les plus fréquents :
- **sous-secteurs à hauteur/emprise réduite** non distingués (ex. Saint-Denis Ud 80 % mais
  Udop/Udp 70 % ; Le Tampon Ua 21/25 m mais Uav 16/20 m) ;
- **majorations conditionnelles** (projet ≥ 2000 m² → +2/+2 m ; RPA/commerce en RDC ; PPRI) ;
- **reculs le long des RN/RD** (retrait porté à 20–75 m de l'axe) non signalés ;
- **stationnement** : LLTS = 0 place, mutualisation −50 % dans 300 m (Petite-Île) ;
- **exclusions génériques** (ouvrages techniques, extensions de bâti non conforme, équipements
  d'intérêt collectif) — dérogations standard, notées mais peu structurantes.

Ces 147 exceptions sont **stockées** en champ `note` de chaque feuille (préfixe
`PLU-VERIF-1 (exception à afficher)`). **Un point reste à câbler** (hors « corrections de
statut ») : leur **affichage sous le « i » de la fiche** — le chemin de propagation
feuille→`ZoneRules`→fiche n'existe pas encore (les notes de feuille ne remontent pas dans
`faisabilite/zonage.py::_zone_rules_from_regles`). La donnée est prête ; le fil d'affichage
est un petit suivi front+back identifié.

## INDÉCIDABLE (2)
- **Saint-Paul Usdu · emprise** — l'article 9 fixe l'emprise **en m²** (≤150 m² habitation…),
  jamais un CES en % : l'abstention de LABUSE (valeur vide) est **cohérente**, rien à trancher.
- **Sainte-Marie UTp · pleine terre** — `a_verifier`, aucune valeur portée ; l'art. U12.2
  « activités » ne nomme jamais UTp ni « pleine terre ».

## Par commune

| INSEE | Commune | N | TROUVÉ (auto) | JUSTE | +exc | mauv.réf | FAUSSE | indéc |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 97401 | Les Avirons | 120 | 103 | 1 | 16 | 0 | 0 | 0 |
| 97402 | Bras-Panon | 93 | 87 | 0 | 6 | 0 | 0 | 0 |
| 97403 | Entre-Deux | 31 | 29 | 0 | 0 | 2 | 0 | 0 |
| 97404 | L'Étang-Salé | 79 | 53 | 26 | 0 | 0 | 0 | 0 |
| 97405 | Petite-Île | 94 | 70 | 4 | 20 | 0 | 0 | 0 |
| 97406 | La Plaine-des-Palmistes | 59 | 41 | 0 | 18 | 0 | 0 | 0 |
| 97407 | Le Port | 81 | 59 | 8 | 3 | 11 | 0 | 0 |
| 97408 | La Possession | 120 | 110 | 0 | 10 | 0 | 0 | 0 |
| 97409 | Saint-André | 42 | 42 | 0 | 0 | 0 | 0 | 0 |
| 97410 | Saint-Benoît | 30 | 25 | 5 | 0 | 0 | 0 | 0 |
| 97411 | Saint-Denis | 90 | 64 | 19 | 7 | 0 | 0 | 0 |
| 97412 | Saint-Joseph | 162 | 139 | 8 | 14 | 0 | **1** | 0 |
| 97413 | Saint-Leu | 73 | 65 | 1 | 1 | 6 | 0 | 0 |
| 97414 | Saint-Louis | 120 | 73 | 33 | 3 | 11 | 0 | 0 |
| 97415 | Saint-Paul | 183 | 145 | 32 | 3 | 1 | **1** | 1 |
| 97416 | Saint-Pierre | 163 | 131 | 1 | 31 | 0 | 0 | 0 |
| 97418 | Sainte-Marie | 114 | 95 | 12 | 0 | 6 | 0 | 1 |
| 97419 | Sainte-Rose | 58 | 40 | 0 | 0 | 18 | 0 | 0 |
| 97420 | Sainte-Suzanne | 68 | 49 | 19 | 0 | 0 | 0 | 0 |
| 97421 | Salazie | 47 | 42 | 4 | 1 | 0 | 0 | 0 |
| 97422 | Le Tampon | 89 | 80 | 0 | 9 | 0 | 0 | 0 |
| 97423 | Les Trois-Bassins | 61 | 38 | 0 | 2 | 21 | 0 | 0 |
| 97424 | Cilaos | 54 | 51 | 0 | 3 | 0 | 0 | 0 |
| | **TOTAL** | **2 031** | **1 631** | **173** | **147** | **76** | **2** | **2** |

## Lot D — permanence

- Le vérificateur devient **`labuse plu verif`** (`src/labuse/plu/verif.py`, commande dans
  `plu/cli.py`) — `--csv <path>` écrit le détail, `--faux` liste les non-TROUVÉ. Rejouable à
  chaque règle validée / nouveau millésime (la sentinelle de fraîcheur PLU du Circuit déclenche).
  PDF cherchés via `$LABUSE_PLU_PDF_DIR` puis `data/plu_reglements/`.
- **Résultat pour l'onglet Cohérence** : `verif.resume()` rend `{total, verdicts, communes}` —
  à brancher sur `/admin/coherence` (fil documenté, non encore posé pour rester dans le périmètre).

## Livrables
- `REGLES.csv` — une ligne par règle (verdict Lot A + statut + raison de calibration).
- `lotB/*.json` (22) + `lotB_agrege.json` — verdicts finaux relus au PDF, avec preuve citée.
- `corrections_lotC.json` — les 225 corrections appliquées.
- `scripts/plu_verif/{inventaire,verif,page_text,appliquer_lotC}.py`, `PROTOCOLE_LOTB.md`.

## Reproductibilité
Après corrections, `labuse plu verif` : **TROUVÉ 1 671 · AMBIGU 336 · ABSENT 24 · ILLISIBLE 0**
(vs 1 631 / 315 / 85 avant : les 76 pages corrigées font basculer 61 ABSENT — la citation
retombe sur la bonne page — dont 40 en TROUVÉ, le reste en AMBIGU car la page corrigée porte
une exception réelle). Les 24 ABSENT résiduels sont des pages-tableau / renvois annexe /
valeurs `propose` vides, **toutes confirmées justes au Lot B** — limite du texte-matcher, pas
des écarts.
