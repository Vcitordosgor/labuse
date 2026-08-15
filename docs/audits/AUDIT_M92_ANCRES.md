# AUDIT M92 — ancres golden transitoires : dater ce qui périme

**Mandat M92 · Phase 1 (inventaire) · branche `audit/m92-ancres-transitoires` · NON mergé**

Le golden est la bascule : il ne vaut que si un échec signale TOUJOURS une régression.
Une ancre qui dépend d'un état périssable (procédure BODACC, permis récent, âge d'un
dirigeant, rang d'un run) rougit quand le monde change, sans qu'aucun code n'ait
régressé — le garde crie au loup. Ce document classe les 119 ancres **stable** vs
**transitoire** et, pour les transitoires, estime l'horizon de péremption.

## Méthode

119 ancres = **86 ancres J3** (gèlent le COUPLE base : `cascade_status`,
`matrice_statut`, `tier_v2` + `motif`/`validation`) + **33 entrées « full »** (comparent
base+API champ par champ : surface, commune, zonage, scores, `score_v2`, `dvf`,
`permis_sitadel`, `veille_succession`, …).

Golden **119/119 PASS aujourd'hui** : rien n'a encore péri. L'audit est PRÉVENTIF.

## Ce qui est STABLE (la majorité saine — ne change que si le code change)

- **~80 ancres J3** à motif géométrique / réglementaire : `surface` (6), `risques` PPR
  (5), `pente` (5), `zonage_plu_gpu` (5), `emprise_routiere` (5), `emprise_lineaire` (4),
  `osm_faux_positif` (5), `prescription_plu` (5), `eau` (4), `foncier_public` (5),
  `declasse_bati_revele/sature/non_constructible/zone_fermee/au_statut_inconnu` (12),
  `reserve_fonciere` (2). Ces motifs sont des faits cadastraux/réglementaires : l'ancre
  fait son travail.
- **Champs stables des 33 full** : `surface_m2`, `commune`, `zonage_detail`, `q_score`,
  `a_score`, `a_completude`, `completeness_score` (règles de calcul déterministes).

## Ce qui est TRANSITOIRE

### A. Prévisible (horizon estimable)

| Ancre(s) | Champ | Dépend de | Horizon de péremption |
|---|---|---|---|
| `97407000BI0350` (75), `97410000AS1425` (73), `97410000AS1450` (73) | `veille_succession.dirigeant_age` | âge recalculé `age(date_naissance)` à chaque build (`v_pm_propension_vendre`) | **≤ 1 an** — au prochain REJEU postérieur à l'anniversaire du dirigeant (annuel, déterministe) |
| `97414000CV0907` (canari BODACC actuel, M81) | `tier_v2` forcé « chaude » par évènement rouge | procédure collective SIREN 540092202 (liquidation judiciaire, 2025-06-12) | **~2027-2028** — à la CLÔTURE de la procédure (déjà documenté dans le golden) |

*Note* : `97415000AC0253` est l'EX-canari (procédure clôturée au rejeu q_v9) — déjà
documenté comme transitoire assumé dans le golden, tier `chaude` gelé au run q_v8.

### B. Imprévisible (périt sur un évènement réel de la parcelle, sans horizon estimable)

| Champ | Entrées full concernées | Dépend de | Horizon |
|---|---|---|---|
| `dvf.derniere` / `dvf.n_mutations` | **6** : `97407000BI0350`, `97411000AL0360`, `97413000CS0160`, `97415000CY0104`, `97422000AX1253`, `97422000BY0489` | ingestion d'une NOUVELLE vente sur la parcelle (requête non fenêtrée) | **imprévisible** (dépend d'une mutation réelle) |
| `permis_sitadel.dernier` / `n` | **18** (dont `97403000AR1423`, `97408000AP1647`, `97418000AT2379`, `97420000AO0654`, …) | ingestion d'un NOUVEAU permis sur la parcelle (non fenêtré) | **imprévisible** (dépend d'un dépôt réel) |

### C. Run-gated (transitoire mais PARTIELLEMENT déjà signalé)

| Champ | Entrées | Dépend de | État actuel |
|---|---|---|---|
| `score_v2.rang` | **32** full | classement population entière du run servi | change au REJEU. Le golden AVERTIT (`WARN: run v2 servi a changé → écarts tier/rang attendus`) mais **compte quand même le diff en FAIL** — l'avertissement explique, il ne neutralise pas |
| `tier_v2` | 86 ancres J3 | scoring du run servi | idem : run-gated, WARN partiel |

## Constats

1. **Le seul périssable VRAIMENT prévisible et non couvert est `dirigeant_age`** (3
   entrées) : il incrémente à chaque rejeu franchissant un anniversaire. Aucun WARN ne
   le couvre aujourd'hui → un rejeu de routine le ferait rougir comme une régression.
2. **Le canari BODACC** (`97414000CV0907`) est déjà documenté transitoire avec horizon
   (~2027-2028) — sain, mais la date vit dans un commentaire de motif, pas dans un champ
   exploitable par le garde à l'échec.
3. **dvf/permis** (6 + 18) sont transitoires mais imprévisibles ; ils sont souvent
   INCIDENTS au but de l'ancre (le point est le tier/verdict/surface, pas la date du
   dernier permis). Candidats à la **ré-ancre sur le stable** (retirer le champ daté de
   la comparaison, garder la couverture réelle) plutôt qu'à un simple marquage.
4. **rang/tier** sont run-gated : le WARN existe mais **produit encore un FAIL** sur
   rejeu — c'est exactement le « troisième état » que M90 a posé ailleurs (indéterminé ≠
   échec) et qui manque ici : un rejeu attendu devrait donner « à rafraîchir », pas FAIL.

## STOP — arbitrage Vic

Peu d'ancres sont réellement transitoires-prévisibles (3 `dirigeant_age` + 1 canari
BODACC déjà daté). Le gros du bruit potentiel vient des champs INCIDENTS (dvf/permis
datés) et du couple run-gated (rang/tier). Quatre traitements possibles, à arbitrer :

1. **Marquer** les transitoires prévisibles avec leur date/horizon dans le golden (champ
   dédié `perime_le` / `transitoire`), pour que l'échec dise « ancre transitoire, péremption
   prévue le … » avant qu'on cherche une régression.
2. **Ré-ancrer sur le stable** les champs incidents (dvf/permis datés) : les retirer de la
   comparaison des full concernées quand ils ne sont pas le but de l'ancre — la couverture
   réelle (tier/verdict/surface) reste, le bruit disparaît à la racine. *(Pas une
   suppression d'ancre : une ré-ancre.)*
3. **Troisième état « à rafraîchir »** pour les transitoires périmées (rang/tier au rejeu,
   dirigeant_age) : distinguer à l'échec la péremption prévisible de la régression, comme
   M90 (indéterminé ≠ FAIL).
4. **Assumer** ce qui reste transitoire par nature (le canari BODACC teste un vrai
   évènement) : garder date + procédure de rafraîchissement documentée.

Aucune ancre ne sera supprimée (interdit). Le nombre d'ancres stables ne baisse pas ;
il peut monter si des champs incidents sont ré-ancrés sur du stable.
