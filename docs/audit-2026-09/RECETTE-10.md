# RECETTE-10 — le Financier au propre, et ce que vaut le score

Branche `fix/recette-10` depuis `fix/recette-9` · worktree `~/Desktop/labuse-recette6`.
**Règle de preuve** : un travail n'est fait que prouvé sur l'artefact final (PDF régénéré ou capture
depuis le vrai chemin). Aucun merge, aucune bascule, `:8020`/`q_v14` intacts.

Artefacts : `docs/audit-2026-09/captures-recette-10/`.

---

## T1 🔴 — La surélévation était fausse dans l'autre sens — FAIT

**Le défaut.** RECETTE-9 T9 a branché le LiDAR sur la surélévation mais a comparé l'égout **mesuré**
(3,0 m) à la règle de **faîtage** (10,0 m) : `10,0 − 3,0 = 7,0 m disponibles`. E1 comparait un faîtage
à une règle d'égout (marge sous-estimée) ; T9 a fait l'inverse (marge gonflée de plus du double). La
règle citée deux pages plus haut dans le même Dossier dit pourtant **10 m au faîtage · 7 m à l'égout**.

**Le bon calcul — les deux contraintes, la plus serrée mord** (parcelle `97411000EL0157`, Saint-Denis) :
- à l'égout : 7,0 (règle `he_m`) − 3,0 (égout mesuré) = **4,0 m**
- au faîtage : 10,0 (règle `hf_m`) − 6,9 (faîtage mesuré) = **3,1 m**
- **disponible réel : 3,1 m, limité par le faîtage.**

Recalcul à la main sur trois parcelles mesurées (table `batiment_hauteur_lidar`, règles `he/hf` de zone) :

| parcelle | égout mes. | faîtage mes. | he | hf | marge égout | marge faîtage | **retenue** | mord |
|---|---|---|---|---|---|---|---|---|
| 97411000EL0157 | 3,0 | 6,9 | 7 | 10 | 4,0 | 3,1 | **3,1** | faîtage |
| 97411000AB0006 | 4,4 | 8,3 | 7 | 10 | 2,6 | 1,7 | **1,7** | faîtage |
| 97411000AB0009 | 4,3 | 7,0 | 7 | 10 | 2,7 | 3,0 | **2,7** | égout |

(les trois cas, la contrainte mordante bascule selon la géométrie du toit — c'est exactement ce que le
LiDAR apporte : deux hauteurs distinctes, chacune appariée à SA règle.)

**Le correctif.**
- `faisabilite/potentiel.py::surelevation_mesuree(he_regle, hf_regle, egout_mesure, faitage_mesure)` :
  nouveau point de calcul unique. Chaque contrainte apparie règle et mesure **de la même base** ; la
  plus serrée décide ; renvoie `{marge_m, possible, contrainte, contraintes[]}`. `surelevation`
  expose désormais `he_regle_m`/`hf_regle_m` bruts (les deux règles, pas seulement le faîtage).
- `api/app.py::_potentiel_transformation_block` : quand le LiDAR a mesuré, appelle `surelevation_mesuree`
  au lieu de `hauteur_regle − égout`. Sert `hauteur_contrainte` (« égout »/« faîtage ») + `hauteur_contraintes`.
- `exports/blocs/potentiel.py` : la phrase dit **laquelle** des deux mord et montre les deux calculs.
- Fiche parcelle (`constructibilite.tsx`) : « possible (marge ~3,1 m, limité par le faîtage) ».
- `exports/collecte.py` : le collecteur registre `marge_surelevation_m` sert la marge mesurée LiDAR.

**Le test anti-inversion** (`tests/regles/test_surelevation.py`) : une règle d'égout ne se compare
jamais à un faîtage, ni l'inverse — chaque marge = règle − mesure appariées par base ; le résultat ne
peut valoir aucun croisement (ni `10−3=7`, ni `7−6,9=0,1`). Plus le cas EL0157 recalculé (3,1, faîtage).

**Autres cohabitations vérifiées** : `copilote/moteurs.py` (Densifier) dérive un NOMBRE DE NIVEAUX de
`he_m` (`int(he//étage)`), pas une marge — pas d'inversion. `exports/blocs/apporteur.py` n'imprime que
la hauteur du bâti, aucun calcul de surélévation. Le chemin BD TOPO (sans LiDAR) reste faîtage-contre-
faîtage (RECETTE-7, inchangé).

**Preuve — artefact final.** Dossier régénéré `captures-recette-10/T1-dossier-EL0157.pdf` (+ archive JSON).
Bloc 3 imprime : « Surélévation possible — **3,1 m disponibles, limité par le faîtage** (mesuré au
LiDAR HD). égout 3,0 m mesuré contre 7,0 m réglementaires (marge 4,0 m) · faîtage 6,9 m mesuré contre
10,0 m réglementaires (marge 3,1 m). » Chemin réel : `_q_v2_fiche` → `construire(..., 'dossier')`.
