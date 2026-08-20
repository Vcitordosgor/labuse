# M132 — L'EXAMEN À HAUTE PUISSANCE

> **Verdict mécanique : C_bati NON PROMU** — et les deux méthodes d'agrégation
> concordent. Le gain bâti est **réel et directionnel** (agrégé +0,34, le fold 2024 seul
> significatif à +0,81), la puissance ×3 a bien resserré l'IC (de ±0,67 à un fold à ±0,41
> agrégé) **et le point est resté positif** — mais la borne basse s'arrête à **−0,08**,
> juste sous 0. À la barre des 95 % gravée dans la métrique v2, ça ne passe pas. **Fin
> propre du chantier : C_bati reste au chaud, le servi reste la référence.**

Rien n'a changé : ni la métrique v2, ni les modèles, ni le run servi. On a ajouté des
données à la **mesure** (folds 2023 + 2024 + 2025), pas au modèle. Le **vivier est un
instantané unique de la cascade** (exclusions physiques/légales, ~invariantes) : tenu FIXE
(q_v10_m129, 285 781) sur les trois folds ; seuls l'année de label et la fenêtre
d'entraînement (walk-forward) varient — ce qui isole la puissance ajoutée de toute dérive
d'univers. Sorties : `reports/m132/{par_fold,agrege,ece,verdict}.csv`.

---

## 1. Le tableau — par fold, puis agrégé

Top 0,4 % de chaque segment sur son propre classement ; écart pairé (bootstrap 2000,
mêmes lignes rééchantillonnées pour les deux modèles). nu : k=171 sur 42 838 · bâti :
k=959 sur 239 795 (par fold).

### Segment NU

| Fold | base | actuel | C_bati | Δ pairé [IC95] | statut |
|---|---|---|---|---|---|
| 2023 | 2,26 % | 5,70 | 4,40 | −1,07 [−2,70 , +0,25] | dans le bruit |
| 2024 | 2,22 % | 4,74 | 4,47 | +0,00 [−0,79 , +0,51] | dans le bruit |
| 2025 | 2,87 % | 4,79 | 4,90 | +0,20 [−0,98 , +1,24] | dans le bruit |
| **agrégé** | | **4,70** | **4,78** | **pooling −0,32 [−0,96 , +0,24]** · méta −0,08 [−0,54 , +0,38] | **dans le bruit** |

### Segment BÂTI

| Fold | base | actuel | C_bati | Δ pairé [IC95] | statut |
|---|---|---|---|---|---|
| 2023 | 1,90 % | 6,75 | 6,75 | −0,06 [−0,77 , +0,59] | dans le bruit |
| 2024 | 1,52 % | 6,17 | 6,96 | **+0,81 [+0,07 , +1,58]** | **supérieur** |
| 2025 | 1,52 % | 5,02 | 5,44 | +0,41 [−0,27 , +1,03] | dans le bruit |
| **agrégé** | | **6,04** | **6,36** | **pooling +0,34 [−0,08 , +0,74]** · méta +0,35 [−0,05 , +0,75] | **dans le bruit** |

**Calibration (ECE, vivier, 3 folds poolés) :** actuel 0,0028 · C_bati 0,0027 → non dégradée.

**La méthode d'agrégation, dite.** *Pooling des paires* (primaire) : micro-moyenne des RR
sur les trois folds — chaque mutation compte une fois dans le pool, c'est directement le
gain de puissance visé, et la structure pairée est préservée au niveau de l'observation.
*Méta-analyse* (contrôle) : Δ par fold + variance, pool inverse-variance (effet fixe). **Les
deux concordent** (bâti : pooling +0,34 vs méta +0,35 ; borne basse −0,08 vs −0,05) — le
choix ne change pas le verdict, donc pooling fait foi.

---

## 2. Le verdict mécanique de la double barre (sur l'agrégé)

| Critère | Pooling | Méta | 
|---|---|---|
| **(a)** inférieur hors bruit sur AUCUN segment | ✓ (nu −0,32 et bâti +0,34 straddlent 0) | ✓ |
| **(b)** supérieur hors bruit sur AU MOINS UN segment | **✗** (bâti +0,34 [**−0,08**, +0,74] — la borne basse franchit 0) | **✗** (bâti [−0,05, +0,75]) |
| **(c)** ECE ne se dégrade pas | ✓ (0,0027 ≤ 0,0028) | ✓ |
| **PROMU ?** | **NON** | **NON** |

**(a) ∧ (b) ∧ (c) = faux, par les deux méthodes → C_bati NON PROMU.** Le critère bloquant
est (b), et il l'est **de justesse** : l'agrégé bâti est solidement positif (+0,34), mais son
IC95 s'arrête à −0,08 — il manque 0,08 de RR pour franchir 0. C'est un quasi-succès, pas un
démenti.

---

## 3. Ce que ça signifie — fin propre du chantier

**Le gain bâti n'était pas un artefact, mais il ne franchit pas la barre.** C'est la lecture
honnête, plus fine que « le +8 % n'était pas réel » :

- Le signal est **directionnel et stable** : bâti agrégé +0,34, jamais négatif hors bruit,
  et le fold 2024 le voit seul significatif (+0,81 [+0,07, +1,58]). Sur nu, rien (agrégé
  −0,32, dans le bruit — 2023 même défavorable mais sans signification).
- La **puissance ×3 a fait exactement ce qu'on attendait** : l'IC bâti est passé de
  [−0,27, +1,03] (un fold) à [−0,08, +0,74] (agrégé), ~40 % plus étroit, **et le point a
  tenu**. Ce n'est pas un signal qui s'évapore quand on le regarde de plus près — c'est un
  signal qui converge vers ~+0,34 mais reste **sous le seuil de certification à 95 %**.
- **Par la règle que tu as gravée (IC95, double barre), NON PROMU.** La métrique v2 n'a pas
  été fléchie pour l'occasion : le seuil est 95 %, l'agrégé bâti y échoue de 0,08.

**Conséquence, mécaniquement :**
- **C_bati reste au chaud** — inchangé depuis M127-bis, re-confirmé sur le vrai vivier (M130,
  M131) et maintenant à haute puissance (M132). Son artefact est archivé
  (`reports/m127bis/artifact-m127bis-C_bati-fold2025.joblib`).
- **Le run servi reste la référence.** Aucune bascule, aucun re-tiérage, aucun plan M-suivant
  à déclencher : la condition « PROMU » n'est pas remplie.
- **Le chantier de ré-entraînement se clôt proprement** : M124→M132 ont établi, mesuré, et
  tranché mécaniquement que le meilleur modèle servable aujourd'hui reste l'actuel. Le seul
  levier restant pour le bâti serait **plus d'événements encore** (folds antérieurs à 2023,
  si la profondeur DVF + les labels le permettent) — mais c'est un mandat de DONNÉE, pas de
  modèle, et il n'est pas ouvert ici.

**Il n'y a pas de plan d'exécution à écrire** (réservé au cas PROMU). Le verdict est NON
PROMU, robuste aux deux méthodes d'agrégation. **La décision — clore, ou financer un mandat
de données pour re-tenter le bâti à puissance encore supérieure — reste la tienne, sur ce
rapport.**

---

## Annexe — reproductibilité

- Protocole : `scripts/m132/examen_hp.py` (réutilise `scripts/m127/examen.py` fit_fold,
  `scripts/m127bis/examen_bis.py` specs bâti). Folds 2023/2024 refités ; 2025 réutilise le
  cache M131. Prédictions cachées `reports/m132/preds_<fold>.npz` (gitignorées, régénérables).
- Bootstrap pairé 2000 tirages, seed 974. Métrique v2 inchangée (dalle §6).
- Rien de servi touché ; golden/tests non impactés (mesure hors ligne).
