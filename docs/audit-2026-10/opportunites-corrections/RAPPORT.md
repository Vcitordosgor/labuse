# Corrections A · B · C — opportunités (suite du diagnostic lot 2)

Branche `fix/opportunites` (worktree `labuse-opp`, base main `d3b1e11b`). Un commit par correction.
Mesures faites sur la **base servie** (`labuse`, lecture seule ; `postgresql:///labuse`), run résiduel
`run_seq 16` / cascade `q_v19_sources`.

---

## A — Saint-Leu UD : hauteur relue au règlement → **conforme, aucune correction (STOP)**

**Instruction :** relire la règle de hauteur au règlement officiel (page citée), corriger si elle est
fausse ; si le règlement donne bien la valeur actuelle, expliquer d'où viennent les permis plus hauts.

**Relecture.** Saint-Leu UD, article **UD 10, page 54** du règlement (PLU 2007, `saintleu.re`,
md5 `d74416f9…`). Valeur servie par LABUSE (`config/plu_destinations/97413_saint_leu.yaml`) :

> « La hauteur maximale … est limitée à : **4,00 m à l'égout** du toit — **6,00 m au faîtage** — **R+combles** » (CES 40 %).

L'extraction de calibrage (`captures/plu-calibrage3/extractions/97413_saint_leu.json`, issue du même PDF)
porte **mot pour mot** la même valeur (`he_m=4`, `hf_m=6`, « R+combles », p.54). **La valeur n'est pas
fausse** — elle est fidèle au règlement. → **Aucune correction, STOP.**

**D'où viennent alors les permis « plus hauts ».** Ils ne sont pas plus hauts. Mesure sur les 297 permis
Saint-Leu UD du gisement :

- **287/297 sont des maisons individuelles** (1 logement ; ratio logements médian **1,0**) — pas des
  collectifs. Le dépassement est en **surface de plancher** (ratio SDP médian **1,55**), pas en hauteur.
- Le moteur, en live, compte les niveaux **sur l'égout** : `4 m ÷ 3 m/niveau = 1 niveau (R+0)` → SDP max
  ~80–110 m² ; une maison réelle en bâtit ~129 m². L'écart ×1,55 vient de ce que LABUSE **ne compte pas
  le niveau de combles** que le règlement accorde explicitement (« R+combles »), pas d'une hauteur fausse.

**Conséquence.** 0 parcelle change de statut au titre de A. Le vrai levier — compter le niveau de
**combles** quand le règlement l'accorde — est une modification de **modélisation des niveaux**, qui
toucherait **toutes les zones « R+combles » de l'île** (pas seulement Saint-Leu UD) : décision distincte,
hors du périmètre « corriger la valeur de hauteur ». **Signalé à Vic, non implémenté.**

---

## B — terrain_exigu : seuil déjà au **minimum justifié** → pas d'abaissement sûr

**Instruction :** abaisser le seuil au minimum justifié par les permis réels, **pas plus** — et aucune
parcelle ne doit devenir constructible à tort.

**Ce que recouvrent les 46 permis « terrain_exigu ».** En rejouant le moteur sur leurs parcelles :

| sous-cause (exigu_raison) | n | nature |
|---|--:|---|
| `reculs` (contour inseté vidé) | 20 | les reculs vident l'assiette |
| `hors_rouge_trop_petit` (PPR, < 200 m²) | 16 | partie hors zone rouge trop petite |
| `ppr_rouge` / `emplacement_reserve` / `contraintes` | 8 | **réellement bloquant** (PPR rouge, ER) |
| `portion_reduite` (à cheval) | 2 | portion U/AU réduite |

**Les 20 « reculs » ne sont pas abaissables.** Leur assiette insetée mesurée vaut **≈ 0 m²** (« contour
vidé »), sur de petites parcelles (38–354 m²) : les reculs (3 m voirie + 3 m séparatif) consomment tout.
Les permis réels y sont des constructions **mitoyennes / à l'alignement** (mur mitoyen, recul nul sur
limite partagée) que LABUSE **ne peut pas déduire** du cadastre. Abaisser le seuil `SEUIL_EXIGU_M2` (5 m²)
ne les reclasse pas (l'assiette est ~0) et tout seuil plus bas fabriquerait des « constructibles » à
~0 m² — **faux positifs interdits**.

**Les 16 « hors_rouge » : abaisser le seuil de 200 m² fabrique des micro-bâtis.** Les fragments hors zone
rouge des permis vont de 70 à 198 m². Mais en simulant l'abaissement, la SDP obtenue sur ces fragments
est **absurde** (micro-bâtis) : SDP de **10, 11, 12, 17, 19, 26…** m² ; seuls les fragments ~195–198 m²
donnent une SDP réelle (71–120 m²). Un fragment de 70–140 m² après reculs ne porte qu'un micro-bâti —
donc « constructible à tort ». Le **minimum justifié où un bâti réel résulte** est ~195 m² ≈ le seuil
**actuel (200 m²)**.

**Conséquence.** Le seuil `terrain_exigu` est **déjà au minimum justifié** : l'abaisser violerait « aucune
constructible à tort » (mitoyen à 0 m², micro-bâtis). **0 parcelle reclassée sûrement → aucune
modification.** Les 46 permis sont des exclusions **conservatrices mais correctes** (mitoyen non
modélisable, PPR, ER). (Reproductible : `scripts/diagnostic_opportunites_lot2.py` + moteur de faisabilité
sur les 46.)

---

## C — rédhibitoire en zone U : le RPG (indicatif) ne bloque plus en U/AU

**Instruction :** ne garder l'exclusion « rédhibitoire » que pour les causes **réellement bloquantes**.

**Cause identifiée.** Sur les 83 parcelles « rédhibitoire » en zone U du gisement, **seules 3** ont une
exclusion de la **cascade** (DPF, PPR rouge). Les **80 autres** viennent du **moteur de faisabilité**
(`estimate_capacity`), qui posait `facteur = 0` (→ cause `redhibitoire`) dès que la parcelle est
**déclarée agricole au RPG** (`agricole_sar`, couche SAFER). Or le code lui-même le disait :
« usage agricole … **indicatif, n'emporte pas d'interdiction automatique** ». Le RPG (registre
parcellaire graphique) est une déclaration d'usage, **pas** une interdiction d'urbanisme : en zone U/AU,
c'est le **zonage PLU** qui gouverne. Des permis logements ont bien été accordés sur ces parcelles.

**Correction** (`src/labuse/faisabilite/engine.py`, modulation réunionnaise). En zone **U/AU**, le RPG
devient une **note informative** (plus de `facteur = 0`). En zone **A/N**, comportement **inchangé** (le
RPG reste l'exclusion de fait — périmètre de C = zone U). Causes **réellement bloquantes conservées** :
aléa **PPR fort**, **bande littorale**.

**Parcelles qui changent de statut.** Sur les **4 768** parcelles servies « rédhibitoire » touchant le
RPG, après correction :

- **4 756 passent constructibles** (12 restent NC pour une autre cause) ;
- réparties en **4 191 zone U + 565 zone AU** (zone résolue par le moteur) ;
- **0 en zone A/N** → **aucune parcelle agricole devenue constructible à tort** (contrôle sur les 4 768).

**Garde-fou zone A/N validé.** Un premier correctif non borné faisait basculer des parcelles de zone A ;
le correctif final est **borné à la famille U/AU** (lu sur `rules.code`, la zone que le moteur utilise).
Contrôle avant/après : **0** nouvelle constructible de famille moteur A/N.

**20 parcelles tirées au hasard, vérifiées à la main** (toutes constructibles, zone U/AU, SDP réelle,
aucune en A/N) :

| idu | commune | zone | surface | SDP max |
|---|---|---|--:|--:|
| 97401000AN0645 | Les Avirons | Uc | 899 | 485 |
| 97403000AR1203 | Entre-Deux | Ub | 356 | 217 |
| 97405000AR1155 | Petite-Île | UD | 202 | 15 |
| 97405000BE0918 | Petite-Île | UZ | 397 | 643 |
| 97409000AI0898 | Saint-André | UB | 306 | 234 |
| 97409000BK0325 | Saint-André | UB | 469 | 335 |
| 97410000AH1314 | Saint-Benoît | Ub | 84 | 91 |
| 97410000BL0340 | Saint-Benoît | Ub | 560 | 185 |
| 97412000AO0791 | Saint-Joseph | U5vi | 1205 | 434 |
| 97412000BX0523 | Saint-Joseph | U3ar | 659 | 344 |
| 97412000CY0150 | Saint-Joseph | U5ru | 4490 | 871 |
| 97414000CV0700 | Saint-Louis | UD | 551 | 248 |
| 97415000CP1937 | Saint-Paul | U3c | 379 | 188 |
| 97416000CZ0005 | Saint-Pierre | Uf | 11840 | 4039 |
| 97416000EX1097 | Saint-Pierre | Uf | 645 | 141 |
| 97418000AT1020 | Sainte-Marie | UD | 1500 | 563 |
| 97419000AX0402 | Sainte-Rose | UC | 493 | 221 |
| 97420000BE0003 | Sainte-Suzanne | UC | 1340 | 722 |
| 97422000BD0583 | Le Tampon | Uc | 1410 | 1276 |
| 97422000CT0226 | Le Tampon | Ud | 415 | 129 |

→ **20/20 OK**, aucune devenue constructible à tort.

---

## Séquence du run à lancer cette nuit (sans la lancer)

**La cascade `q_v19_sources` doit-elle être refaite ? → NON.** Justification : la seule correction de code
(C) est dans le **moteur de faisabilité** (`estimate_capacity`, modulation réunionnaise), **en aval de la
cascade**. La cascade (`phase1`/`phase2`) produit les verdicts de couches (PPR, DPF, A/N, ER, littoral,
50 pas…) ; **aucun ne dépend du RPG** — la couche cascade `safer` est un **flag informatif** (sauf zone A
cannière, HARD_EXCLUDE, inchangé). Vérifié : sur les 83 parcelles, seules 3 avaient une exclusion
cascade ; les 80 venaient du moteur. La cascade `q_v19_sources` reste donc **valide et réutilisable** —
on la relit, on ne la recalcule pas (A et B n'ont aucun changement de code).

**Séquence (base servie `labuse`, run NEUF, jamais le servi) :**

1. **Résiduel** — rejoue le moteur de faisabilité (prend le correctif C) sur toute l'île, dans un run neuf :
   ```
   labuse compute-residuel --ile --new-run q_v20
   ```
   (réutilise la cascade `q_v19_sources` existante ; ~4 756 parcelles passent constructibles).
2. **Score LABUSE + Signal** — re-score en **lisant la cascade existante** `q_v19_sources` + le nouveau résiduel :
   ```
   labuse score-labuse --run q_v20 --cascade-label q_v19_sources --signal-run <id p_score_v2 servi>
   ```
3. **Score É (marge)** — recalcule la marge sur le nouveau résiduel : `labuse score-e …` (mêmes options que le run servi).
4. **Bascule** (gestes servis, après banc vert) : `labuse residuel-serve <seq q_v20>` + promotion golden +
   manifeste **`cascade_run = q_v19_sources` (inchangé)** + `served_run.txt → q_v20`.
5. **Contrôle** : banc de cohérence + `labuse parite` ; vérifier que les 4 756 passent constructibles et
   **0 en zone A/N**.

Les étapes 2–4 reprennent exactement les flags du run servi q_v19 (cf. `docs/EXPLOITATION.md`), **sans
l'étape cascade** : c'est le seul écart, et il est justifié ci-dessus.

> ⚠ Ampleur : C ajoute ~4 756 parcelles constructibles (foncier urbain cultivé, longtemps zéroté à tort
> par le RPG). C'est volumineux mais **mesuré et sûr** (0 à tort). À confirmer par Vic avant la bascule.
