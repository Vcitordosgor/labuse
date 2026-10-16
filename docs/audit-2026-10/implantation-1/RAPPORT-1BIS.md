# IMPLANTATION-1BIS — Rapport

Rendre l'implantation crédible (corrections du moteur sur L'Étang-Salé), puis éprouver **le même
moteur, sans réglage par terrain**, sur deux autres témoins collectifs — et une **deuxième passe** de
corrections (prospect, allées, noyaux, accès). Même branche `feat/implantation-1`.

Livrables : `plan-v2.png` + `scenario-v2.json` (L'Étang-Salé), `plan-saint-andre.png` +
`scenario-saint-andre.json`, `plan-saint-denis.png` + `scenario-saint-denis.json`.

> Pré-faisabilité automatisée. Ni étude d'architecte, ni preuve de conformité, ni permis. Le mot
> « conforme » n'apparaît pas. Toute hypothèse géométrique est étiquetée « Estimé · convention ».

---

## Première passe — les cinq constats du plan, corrigés

| # | Constat (v1) | Correction |
|---|---|---|
| 1 | Deux allées, places d'un seul côté : ~822 m² / 18 places | **Allée unique**, places des **deux côtés** si la largeur ≥ 15 m (sinon un côté, le rapport dit pourquoi). |
| 2 | Allée sous les bâtiments, coursive débordante | Non-chevauchement testé sur **tous les couples** du plan de sol : aire ∩ = 0, sinon scénario **rejeté**. |
| 3 | Allée aboutissant hors voie | Toute allée **reliée à l'accès** (sur voie) et **desservant des places** ; sinon supprimée. |
| 4 | Deux barres « exploitable » à tort | > 1 bâtiment → distance **Non effectué** → **à compléter** ; 1 bâtiment → **Non applicable**. Objectif : préférer un seul bâtiment. |
| 5 | Surfaces par soustraction | Surfaces **mesurées séparément** (bâti, places, allées, accès, pleine terre, reste) ; **Σ = assiette**. |

Compléments : ratios (emprise, perméabilité) sur la **contenance cadastrale** (dessin = formes
seulement), écart affiché ; **pente non prise en compte**, dénivelé LiDAR reporté.

## Deuxième passe — corrections ciblées

1. **Saint-Denis — prospect L > H (Ui.7 : « 4m ≤ L ≥ h/2 »), non chiffrable.** Nouveau contrôle
   **« Prospect (hauteur relative) » = Non effectué**, et **règle générale appliquée** : une règle
   de hauteur non chiffrable **ne laisse jamais l'étude exploitable** → Saint-Denis passe
   **« à compléter »**. Hauteur bornée par la seule règle absolue (18 m). Test ajouté.
2. **L'Étang-Salé** : places **imposées par le barème** et **places dessinées** affichées (ci-dessous
   et dans `scenario-v2.json`), comme pour les deux autres terrains.
3. **Saint-Denis — allée.** (a) **Aucune allée ni place en PPR rouge** (free = assiette − bâti −
   PPR rouge ; vérifié par test). (b) **Allée coupée au droit de la dernière place** (plus aucun
   tronçon mort) ; le test « pas de cul-de-sac » renforcé **casse** désormais sur l'ancien
   prolongement (allée − (places ∪ accès) bufferisée ≈ 0).
4. **Noyaux.** Conventions nommées (`implantation_conventions.yaml`, « Estimé ») : `largeur_noyau_m`
   3,5 · **`max_logements_par_noyau` 6** · **`longueur_max_coursive_par_noyau_m` 30**. Le moteur pose
   **autant de noyaux que nécessaire** (Saint-André : 9 logts/niveau → **2 noyaux** ; L'Étang-Salé 2).
   **Ratio SHAB / SDP affiché par bâtiment.**
5. **Saint-André — accès dans l'angle.** Distance accès–angle **reportée** (7,4 m) avec la mention
   **« visibilité à confirmer »** (non bloquant).

### STOP tenu
0 chevauchement (tous couples) · allées reliées à l'accès, aucune en cul-de-sac, aucune en PPR
rouge · surfaces mesurées **Σ = assiette** · **aucun « Réussi » sans règle citée** (3 terrains).
**76 tests verts** (paramétrés sur les trois terrains).

---

## L'Étang-Salé (AW 99 + 451 + 624 + 625, UA) — avant / après

| | IMPLANTATION-1 (v1) | IMPLANTATION-1BIS (v2) |
|---|---:|---:|
| Forme / statut | deux barres · « exploitable » (à tort) | **une barre · exploitable** (honnête) |
| Logements | 16 | **28** (T2 16 · T3 8 · T4 4) |
| SDP | 1 328 m² | **2 202 m²** · SHAB 1 312 m² (**SHAB/SDP 0,60**) |
| **Places imposées / dessinées** | 18 / 18 | **34 / 34** (barème UA 2.7.3) |
| **m² par place** | ≈ 45,7 | **17,9** |
| Emprise | 332 m² | 505 m² |
| Noyaux par niveau | 1 | **2** (coursive ≤ 30 m / noyau) |
| Stationnement | 2 allées, un côté | **1 allée, deux côtés** |
| Surfaces | par soustraction | **mesurées, Σ = assiette** |

Mixité (UA 1.3) applicable (SDP > 1 000 m²) : **6 logements aidés** imposés. Accès au sud sur
l'avenue, à **3,1 m** d'un angle (visibilité à confirmer). Dénivelé LiDAR 6,2 m (pente moy. 8 %),
non pris en compte.

## Saint-André (AX 255 + 256, UC)

| | Archi | LABUSE |
|---|---:|---:|
| Logements | 48 collectifs | **24** (T2 12 · T3 9 · T4 3) |
| Surface | 2 568 m² | SDP 1 870 · SHAB 1 140 m² (**SHAB/SDP 0,61**) |
| Niveaux | R+2 | **R+2** |
| Places (imposées / dessinées) | 48 (1/logt) | **36 / 36** (barème UC 12.2 : ≥ 50 m² → 1,5) |
| Statut | — | **à compléter** |

Allée unique, **deux côtés**, 20,3 m²/place. **2 noyaux/niveau** (coursive longue). Emprise bâtie,
perméabilité 40 % **Réussi** (pas de CES en UC → emprise **Non effectué**). **Accès à 7,4 m d'un
angle → visibilité à confirmer.** Dénivelé 2,7 m.

**Écarts (48 → 24), structurels :**
- **PPR « B3 » (inondation + mouvements) couvre 3 745 des 4 145 m²** : toute construction la touche →
  **« à compléter »** honnête. L'archi a composé avec ; le moteur signale, il n'interprète pas.
- **Barème** ≥ 50 m² → 1,5 place (vs 1/logt pour l'archi, clause « < 50 m² » / « aidé »).
- **Noyaux** réalistes (2) et **forme** rectangulaire unique : moins dense qu'un plan d'architecte.

## Saint-Denis (DL 247 + 248, Ui — PPR rouge et bleue, prospect L > H)

| | Archi | LABUSE |
|---|---:|---:|
| Logements | 22–27 (RPA) | **12** (T2 6 · T3 6) |
| Places (imposées / dessinées) | 8 (RPA 1/3) | **12 / 12** (Ui : 1/logt, validé) |
| Emprise | 377 m² | 174 m² · SDP 1 046 · SHAB 552 m² (**SHAB/SDP 0,53**) |
| Hauteur | 18 m | **R+5 ≈ 18 m** |
| Statut | — | **à compléter** |

**PPR rouge (interdiction, 548 m²) retirée** de la zone **et du stationnement** (aucune place/allée
en rouge) → zone 650 m². **PPR bleue (234 m²) signalée**, non touchée par le bâti. **Prospect L > H
(Ui.7) non chiffrable → contrôle Non effectué → à compléter** (hauteur bornée par la seule règle
absolue 18 m). Allée unique coupée au droit des places. **1 noyau/niveau** (petit bâtiment : SHAB/SDP
0,53, circulation proportionnellement lourde — fait assumé et affiché). Accès à 3,5 m d'un angle.
Dénivelé 3,3 m.

**Écarts (22–27 → 12), structurels :**
- **RPA** : logements plus petits + **dérogation de stationnement 1/3** (8 places). Le moteur applique
  la règle **générale Ui validée (1/logt)** ; il ne modélise pas la dérogation RPA.
- **PPR rouge** déduite : zone constructible réduite ; barre prudente (emprise 174 vs 377).
- Accord sur l'essentiel : **bâti hors zone rouge**.

---

## Récapitulatif

| Terrain | Zone | Forme | Logts | Places (imp/dess) | m²/place | Noyaux/niv | SHAB/SDP | Statut |
|---|---|---|---:|---:|---:|---:|---:|---|
| L'Étang-Salé | UA | barre R+3 | **28** | 34 / 34 | 17,9 | 2 | 0,60 | exploitable |
| Saint-André | UC | barre R+2 | **24** | 36 / 36 | 20,3 | 2 | 0,61 | à compléter |
| Saint-Denis | Ui | barre R+5 | **12** | 12 / 12 | 20,4 | 1 | 0,53 | à compléter |

Même moteur, mêmes conventions, aucun réglage par terrain : zone, règles (verrou « validée +
citation »), PPR, voirie et prospect viennent des données. Les écarts avec l'architecte **s'expliquent
(PPR, RPA, barème, forme, prospect)** — ils ne se corrigent pas en réglant le moteur.

## Reproduire

```
PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
<python> -c "from labuse.implantation import moteur, rendu; \
from labuse.implantation.moteur import IDUS_SAINT_DENIS as D; \
s=moteur.etudier(idus=D); rendu.rendre_plan_png(s,'plan.png'); rendu.ecrire_scenario_json(s,'s.json')"
```

Tests : `pytest tests/test_implantation1.py` (`reel`, 76 tests, paramétrés sur les trois terrains).
