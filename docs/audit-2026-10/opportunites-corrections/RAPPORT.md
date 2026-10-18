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
