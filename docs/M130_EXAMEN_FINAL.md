# M130 — L'EXAMEN FINAL : quel modèle sur le vivier réel ?

> **En une ligne.** Sur le vivier servi aujourd'hui (285 781 parcelles, 2/3 bâti),
> **aucun des deux modèles ne gagne la métrique de promotion.** C_bati fait
> **+0,5 % de RR@1158 hors copro** vs l'actuel (5,30 vs 5,27) — un écart dans le
> bruit, intervalles de confiance entièrement superposés. **Le seul écart réel et
> reproductible : le segment BÂTI, où C_bati fait +9,6 %** (5,38 vs 4,91). Verdict :
> **ne pas promouvoir** sur cette base ; ce que ça implique est au §5.

Protocole IDENTIQUE à M127/M127-bis/M36 (walk-forward, train ≤2023 — binning sur
TRAIN seul —, calibration isotonique 2024, test 2025 ; RR@1158 hors copro ; ex æquo
départagés, RR médian sur 20 tirages). **La seule chose qui change — et c'est le sujet
du mandat — la POPULATION D'ÉVALUATION est le nouveau vivier**, pas l'ancien. k=1158
inchangé ; la population passe de « toute la trame 2025 hors copro » à « hors copro ∩
vivier servi q_v10_m129 (non écarté par la cascade) ». Mesure seule : rien de servi n'a
bougé. Sorties brutes : `reports/m130/{global,segments,tete_de_liste}.csv`.

---

## 1. Les deux concurrents

| Modèle | Définition | Base |
|---|---|---|
| **actuel** | 22 features nettoyées, résiduel v1 — la reproduction **sous-protocole** du modèle servi `m36-l2f-2026` | l'échelle « A_ref » de M127 (6,67 ≈ réf gelée 6,73) |
| **C_bati** | actuel + cause M125 (résiduel v2) + 9 features bâti (emprise, nb/hauteur/étages bâtiments, usage, surélévation, % potentiel) | le challenger M127-bis, gardé au chaud (+11 % bâti alors mesuré) |

> **Pourquoi une reproduction et pas l'artefact servi lui-même ?** L'artefact figé
> `m36-l2f-2026` est calibré sur 2025 : le tester sur le fold 2025 serait une fuite.
> La reproduction fold-2025 de sa configuration (échelle A_ref) est la seule mesure
> honnête sur ce fold — c'est exactement la base qu'a utilisée M127. L'offset de
> reproduction (voir §4) s'annule dans la comparaison actuel↔C_bati : les deux sont
> refités à l'identique.

---

## 2. Le tableau — 2 modèles × (RR global, RR nu, RR bâti, ECE)

**Population = nouveau vivier** (fold 2025 hors copro ∩ vivier servi), n = 282 633,
taux de base 1,72 %. RR@1158 médian, IC95 bootstrap 1000.

| Modèle | RR global (IC95) | RR **nu** | RR **bâti** | ECE |
|---|---|---|---|---|
| **actuel** | **5,27** [4,32 – 6,22] | 4,86 | 4,91 | 0,0012 |
| **C_bati** | **5,30** [4,36 – 6,23] | 4,96 | **5,38** | 0,0012 |
| Δ C_bati vs actuel | **+0,5 %** (bruit) | +2,0 % | **+9,6 %** | = |

- **Global : +0,5 %** — les ICs se recouvrent presque parfaitement ([4,32–6,22] vs
  [4,36–6,23]). C'est un pile-ou-face, pas un gain.
- **Bâti : +9,6 %** (5,376 / 4,905) — le seul écart franc, **cohérent avec M127-bis**
  (+11 % à l'époque). Les features bâti aident là où elles doivent.
- **Nu : +2,0 %** — quasi plat, attendu (aucune feature nu nouvelle).
- **Calibration IDENTIQUE** (ECE 0,0012) — les deux sont parfaitement calibrés ;
  C_bati n'achète pas son gain bâti au prix du calibrage.

Segments : nu n=42 838 (k=176, base 2,87 %) · bâti n=239 795 (k=982, base 1,52 %).
Le bâti est **85 % de la population du vivier** et a le taux de base le plus BAS
(1,52 % vs 2,87 % nu) — c'est le terrain le plus dur, et celui que C_bati améliore.

---

## 3. La composition de la tête de liste

Top-k du nouveau vivier hors copro, classé par score décroissant.

| Modèle | Tête | nu | bâti | % bâti | mutations observées |
|---|---|---|---|---|---|
| **actuel** | top 100 | 34 | 66 | 66 % | 19 |
| **actuel** | top 1000 | 212 | 788 | 79 % | 96 |
| **C_bati** | top 100 | 23 | **77** | **77 %** | **21** |
| **C_bati** | top 1000 | 159 | **841** | **84 %** | **98** |

- C_bati **déplace la tête vers le bâti** (+11 pts en top 100, +5 pts en top 1000) —
  logique, puisque le vivier est 2/3 bâti et que C_bati sait mieux y classer.
- Il attrape **marginalement plus de mutations réelles dans la tête** (+2 en top 100,
  +2 en top 1000). Réel, mais petit — et fragile à ce niveau d'effectifs (≈20 positifs
  en top 100).

---

## 4. La référence honnête — ce que le changement d'univers fait à lui seul

RR@1158 hors copro de **l'actuel**, mesuré sur les deux univers, même fit :

| Univers | n | taux base | RR@1158 actuel (IC95) |
|---|---|---|---|
| **ANCIEN vivier** (toute la trame 2025 hc) | 428 239 | 1,515 % | **6,47** [5,34 – 7,67] |
| **NOUVEAU vivier** (hc ∩ vivier servi) | 282 633 | 1,720 % | **5,27** [4,32 – 6,22] |

> **L'effet d'univers seul : 6,47 → 5,27, soit −18,5 %.** C'est de LOIN le plus gros
> mouvement du mandat, et il n'a rien à voir avec le modèle. Restreindre au vivier
> retire les parcelles les plus faciles à écarter (l'étage 0) et concentre la
> population sur un terrain plus dense, plus bâti, au taux de base plus haut : le
> top-1158 y enrichit mécaniquement moins. **Le même modèle, sur l'univers qu'on sert
> vraiment, « vaut » 5,3 et non 6,5.** Ce n'est pas une régression du modèle — c'est la
> vérité de l'univers servi, dite enfin sur la bonne population.

**Sur l'ancien vivier, C_bati (6,39) est même LÉGÈREMENT SOUS l'actuel (6,47)** : les
features bâti ajoutent du bruit sur la population complète (pleine de nu faciles). Ce
n'est que sur le vivier bâti-lourd que C_bati passe devant — de justesse au global,
franchement sur le segment bâti.

**Sur le repère gelé 6,73 :** notre reproduction fold-2025 de l'actuel donne 6,47 (RR
médian 20 seeds, dataset v2bis, labels 2025 vivants). L'écart au 6,73 est l'offset
documenté depuis M36 (6,73 gelé → 6,15 label vivant → 6,67 repro M127) : dérive du
label 2025 + médiane-de-tirages vs tirage unique. Il est le même pour les deux modèles
et s'annule dans la comparaison.

---

## 5. Recommandation — NE PAS PROMOUVOIR (et ce que ça implique)

**Aucun modèle ne bat la référence sur la métrique de promotion (RR@1158 hors copro).**
Sur le vivier réel, C_bati fait +0,5 % au global — dans le bruit, ICs superposés. Par la
règle « battre la référence », **C_bati ne franchit pas la barre.** Verdict : **statu quo,
on ne touche pas au run servi.**

Mais il faut dire la nuance honnêtement, parce qu'elle est réelle :

1. **Le seul effet reproductible est vrai** : C_bati lève le segment bâti de +9,6 %
   (cohérent avec les +11 % de M127-bis), à calibration identique, sans coût sur le nu.
2. **Le vivier est désormais 2/3 bâti** — c'est la thèse M129 tout entière
   (renouvellement urbain). Le segment que C_bati améliore est précisément celui qui
   domine maintenant l'univers servi.
3. **Pourtant le global ne bouge pas** : le top-1158 reste ancré par les nu (taux de
   base 2× plus haut, plus faciles) et par les cas évidents. Un gain segmenté sur le
   bâti se dilue dans une métrique globale à k fixe.

**Ce que ça implique.** La question n'est pas « C_bati est-il meilleur ? » (au global,
non ; sur le bâti, oui). Elle est : **la bonne métrique de promotion est-elle encore
RR@1158 global, maintenant que l'univers servi est bâti-lourd ?** Si la valeur produit
est le renouvellement bâti, alors +9,6 % sur le segment qui pèse 85 % du vivier compte
plus que ne le dit un headline plat — mais **certifier ça exige une métrique
bâti-appropriée** (RR bâti dédiée, ou RR pondérée par segment), et **changer la métrique
en cours d'examen est interdit ce tour-ci.** C_bati est le bon candidat à porter dans
cette décision de métrique — ce n'est pas une promotion sur la règle d'aujourd'hui.

**Décision recommandée à Vic :** garder l'actuel servi ; garder C_bati au chaud
(inchangé depuis M127-bis, re-confirmé ici sur le vrai vivier) ; si tu veux mieux servir
le vivier bâti, **le prochain mandat n'est pas un ré-entraînement mais un choix de
métrique** (faut-il juger le modèle sur le bâti maintenant que le produit est bâti ?).
La promotion — et le choix de la métrique — restent ta décision.

---

## Annexe — Phase 1 : la queue M129-D (vérification de l'existant)

Captures de l'état SERVI (après refonte) dans `qa/m130/captures/` — carte+compteur,
panneau Filtre (les 3 facettes « Le bien »), fiche parcelle, parcours projet, kanban,
et le rejeu. **Aucun défaut trouvé.**

- **Rejeu sur un projet réel** (Démo — 40 logements · Saint-Paul, id 24) : rejeu →
  **`ajoutees_refonte = 5` sur 9 entrées**. Le kanban DIT exactement
  « **+10 nouvelles (dont 5 entrées par refonte cascade — nouveau vivier, pas un
  mouvement de marché) · 5 sorties du cadrage · 5 tris conservés** ». Les décisions
  (retenue/écartée/à analyser) survivent. Le mécanisme P4 est vivant et doctrinalement
  propre (capture `07-kanban-rejeu-refonte.png`).
- **Compteur réconcilié (vérifié, pas un défaut)** : analyse OFF (défaut, « tout le
  foncier factuel ») = **431 663** ; analyse ON (« LABUSE retient hors exclusions
  dures ») = **285 781** — exactement le vivier servi. L'arithmétique boucle :
  431 663 = 285 781 (vivier) + 145 882 (écartées étage 0). Doctrine M30 « tout montrer ».
- **Les 3 facettes « Le bien »** présentes et lisibles : « On peut encore construire » /
  « Construite au maximum » / « Propriétaire public » (capture `02b`).
- **Fiche, motifs FR, nom du score** : sections françaises (Urbanisme, Constructibilité,
  Risques, Marché…), « Probabilité de vente sous 1 an ». Pas de trace de la division
  (sortie du produit en M129-C).

**Limite dite.** Les captures livrées sont l'état « après ». Un « avant » pixel-exact
exigerait de revenir au code pré-M129 **et** de re-servir q_v9_m81 (donc dé-servir l'état
courant) — détour lourd que je n'ai pas fait sans arbitrage. Le delta avant→après est
tracé par les audits M119-M129 ; je peux produire les captures « avant » par revert si
tu le demandes.
