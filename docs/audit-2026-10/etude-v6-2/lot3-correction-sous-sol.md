# ÉTUDE V6-2 — Correction Lot 3 : sous-sol Étang-Salé (48 → 44) et pourquoi pas 29

L'alerte : Étang-Salé en sous-sol donnait **48 logts** contre **29** chez l'architecte. Vérification et
corrections des 4 points, sur la MÊME assiette (AW 99/451/624/625, UA, contenance 1 746 m²).

## 1. Pleine terre / perméabilité au-dessus du sous-sol — CORRIGÉ (impact : 48 → 44)
La surface au-dessus d'un sous-sol est **sur dalle → jamais de la pleine terre**. `capacite.calculer`
retranche désormais de la pleine terre la part de l'emprise enterrée qui **déborde le bâti**
(`sur_dalle_m2`). Le contrôle **Perméabilité 30 % (UA 2.6)** s'applique sur la pleine terre RÉELLE →
l'emprise du sous-sol est de fait **limitée** pour tenir les 30 %. Étang-Salé sous-sol : 44 places =
1 100 m² enterrés, dont **364,8 m² sur dalle retirés** de la pleine terre → pleine terre 620 m² ≥ 524 m²
(30 %). Au-delà de 44, les 30 % tombent → c'est ce qui plafonne le sous-sol (48 était faux).

## 2. Rampe réaliste — CORRIGÉ
La rampe faisait ~20 m² (4 × 6 m arbitraire). Désormais : **largeur ≥ 3,5 m**, **pente ≤ 18 %**,
**longueur = hauteur du sous-sol / pente** (3 m / 18 % ≈ 16,7 m) → emprise au sol réaliste
(conventions `rampe_largeur_m`, `rampe_pente_max_pct`, `hauteur_sous_sol_m`). Clippée à l'espace libre
disponible le long de la voie (24 m² ici).

## 3. Hauteur sur la pente (TN 32,98 → 38,21) — VÉRIFIÉ, signalé
Nouveau contrôle **« Hauteur sur terrain en pente »** : la hauteur à l'égout se mesure depuis le terrain
naturel ; sur la pente (dénivelé LiDAR 6,2 m, pente moyenne 8 %), le dénivelé **sous le bâtiment ≈ 1,9–2,2 m**.
Un volume à **toiture plate R+3 dépasserait le plafond égout (12 m) de ~2 m côté aval** → **bâtiment EN
GRADINS requis**, partie aval possiblement **R+2 (comme l'architecte)**. LABUSE suppose des gradins (R+3
conservé, cohérent avec la calibration PLU) et le **signale « À confirmer »** — il n'invente pas une
réduction. (Un dénivelé sous bâti < 3 m reste absorbable par un décrochement ; au-delà, une partie passe
vraiment en R+2.)

## 4. Règles UA citées par l'architecte — NON VÉRIFIÉES (honnête)
« 20 % d'espaces verts hors stationnement » et « marge plantée de 2 m sur 75 % du linéaire hors
mitoyenneté » ne sont **pas** dans le PLU calibré LABUSE (pas de champ au schéma `ReglesZone`). Donc,
conformément au mandat, elles sont **signalées « non vérifiées »** (payload `regles_non_verifiees`,
récit « Règles non vérifiées »), **jamais appliquées en douce**. Elles **réduiraient** la capacité
servie si elles l'étaient (surtout les 20 % EV, qui s'ajoutent aux 30 % de pleine terre).

## Tableau — Étang-Salé AW 99/451/624/625, UA, 23 T2 + 6 T3

| Source | Logements | Niveaux | Places | Stationnement | Remarques |
|---|---|---|---|---|---|
| **LABUSE aérien** | **32** | R+3 (gradins à confirmer) | 32 au sol | aérien (585 m²) | maximum réglementaire ; parking plafonne (−16) |
| **LABUSE sous-sol** | **44** | R+3 (gradins à confirmer) | 44 au −1 | sous-sol 1 100 m² + rampe 24 m² | 364 m² sur dalle retirés de la pleine terre ; 30 % respectés |
| **Architecte** | **29** | R+3 + **partie R+2** | 31 | sous-sol | +20 % EV + marge plantée 2 m + volume compact |

## L'écart résiduel (44 vs 29) est EXPLIQUÉ, pas caché
LABUSE sert le **maximum réglementaire sous les règles calibrées** (pleine terre 30 %, CES, hauteur,
stationnement). L'architecte applique en plus : **20 % d'espaces verts + marge plantée** (hors PLU
calibré → non vérifiées par LABUSE, mais réductrices), une **partie en R+2** sur la pente (LABUSE garde
R+3 en gradins, signalé), et un **volume plus compact** (choix de conception). Ces trois éléments,
cumulés, expliquent l'écart ; chacun est désormais SIGNALÉ à l'écran.

## Vérifié
tsc 0 · vitest 15/15 (EtudeV6) · pytest capacité/sous-sol · chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.
Capture `captures/lot3-correction-sous-sol-44.png`.
