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
