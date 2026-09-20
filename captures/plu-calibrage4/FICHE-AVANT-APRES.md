# PLU-CALIBRAGE-4 lot 3 — fiche parcelle AVANT/APRÈS la bascule (3 communes)

Preuve visuelle « le calcul ne bouge pas ». On dompe le bloc faisabilité SERVI À LA FICHE
(verdict + fourchette + chaque étape : valeur, formule, source) pour 3 parcelles de 3 communes,
depuis l'ANCIEN système (worktree au commit d83226e2, pré-bascule, `plu_rules` + `plu_<slug>.yaml`
présents) puis le NOUVEAU (HEAD, `zonage` seul), même base de données.

| parcelle | commune | zone | verdict AVANT | verdict APRÈS |
| --- | --- | --- | --- | --- |
| 97411000HV0175 | Saint-Denis | Ui | R+4 · au sol ~40-45 / sous-sol ~40-45 logts | **identique** |
| 97416000EI1048 | Saint-Pierre | Ud | R+4 · ~40 à 45 logts | **identique** |
| 97422000BW1034 | Le Tampon | Uav | R+4 · au sol ~44-45 / sous-sol ~44-45 logts | **identique** |

**Tous les NOMBRES sont identiques** — verdict, fourchette (emprise, niveaux, SDP, SHAB,
logements au sol / sous-sol, stationnement), et la valeur + la formule de CHAQUE étape.
`diff fiche_avant.json fiche_apres.json` ne renvoie que **3 libellés de SOURCE** (aucune valeur) :

- Saint-Pierre Ud, « Contrainte pleine terre » : `Art. Ud5.1, p.91` → `Art. 13` ;
- Le Tampon Uav, « Emprise % réglementé » (non réglementée) : `Art. Ua9, p.16 : « Non réglementée »` → `Art. 9` ;
- Le Tampon Uav, « Contrainte pleine terre » : `Art. Ua13.2, p.23 (…)` → `Art. 13`.

Même cause que la ligne « source pleine terre » du tableau d'équivalence : la pleine terre (et
l'emprise non réglementée) sont `propose`/`absent` dans les regles auditées → le moteur affiche
son libellé d'article générique (Art. 13 pleine terre, Art. 9 emprise) au lieu du texte libre de
l'ancien `plu_<slug>.yaml`. **La valeur retenue est identique** (emprise, m² pleine terre, tout le
reste). Aucun chiffre de la fiche ne bouge.

JSON complets : `fiche_avant.json`, `fiche_apres.json`.
