# IMPLANTATION-1BIS — Rapport

Rendre l'implantation crédible (corrections du moteur sur L'Étang-Salé), puis éprouver **le même
moteur, sans réglage par terrain**, sur deux autres témoins collectifs. Même branche
`feat/implantation-1`, à la suite d'IMPLANTATION-1.

Livrables : `plan-v2.png` + `scenario-v2.json` (L'Étang-Salé), `plan-saint-andre.png` +
`scenario-saint-andre.json`, `plan-saint-denis.png` + `scenario-saint-denis.json`.

---

## LOT A — Les cinq constats, corrigés

| # | Constat sur `plan.png` (v1) | Correction (v2) |
|---|---|---|
| 1 | Deux allées parallèles, places d'un seul côté : ~822 m² pour 18 places | **Allée unique**, places des **deux côtés** quand la largeur le permet (sinon un côté, et le `stationnement_note` dit pourquoi). **18,6 m²/place** (contre 45,7). |
| 2 | Une allée sous les bâtiments ; une coursive déborde sur l'autre allée | Non-chevauchement testé sur **tous les couples** (module, noyau, coursive, place, allée, accès, espace libre) : aire ∩ = 0, sinon le scénario est **rejeté**. |
| 3 | Allée débouchant sur une limite non classée voie (inutile) | Toute allée doit être **reliée à l'accès** (lui-même sur une limite classée voie) ET **desservir des places** ; sinon supprimée. Aucun cul-de-sac. |
| 4 | Deux barres, « distance entre constructions » non contrôlée, statut « exploitable » quand même | Plusieurs bâtiments → contrôle **Non effectué** → statut **« à compléter »**. Un seul bâtiment → **Non applicable**. L'objectif **préfère un scénario à un seul bâtiment** (exploitable). |
| 5 | Surfaces de stationnement obtenues par soustraction | Surfaces **mesurées séparément** (bâti, places, allées, accès, pleine terre, reste non affecté) ; **leur somme = l'assiette** (vérifié par test). |

Compléments : ratios (emprise, perméabilité) calculés sur la **contenance cadastrale**
(le dessin ne sert qu'aux formes) ; écart contenance/dessin affiché. **Pente non prise en compte**
dans le volume ; le dénivelé LiDAR (RGE ALTI 5 m) est reporté.

### STOP du LOT A — tenu
0 chevauchement · toutes les allées reliées à l'accès · surfaces mesurées dont la **somme =
assiette** · **aucun « Réussi » sans règle citée** (vérifié sur les trois terrains).

### Avant / après — L'Étang-Salé (AW 99 + 451 + 624 + 625, UA)

| | IMPLANTATION-1 (v1) | IMPLANTATION-1BIS (v2) |
|---|---:|---:|
| Forme / statut | deux barres · « exploitable » (à tort) | **une barre · exploitable** (un seul bâtiment) |
| Logements | 16 (T2 12 · T3 4) | **28** (T2 16 · T3 8 · T4 4) |
| SDP | 1 328 m² | **2 020 m²** |
| Places (aériennes) | 18 | **34** (= 34 imposées) |
| **m² par place** | **≈ 45,7** | **18,6** |
| Emprise bâtie | 332 m² | **505 m²** |
| Pleine terre | 590 m² | 608 m² |
| Stationnement | 2 allées, un côté | **1 allée, deux côtés** |
| Surfaces | par soustraction | **mesurées, Σ = assiette (1 744 m²)** |

L'allée unique à double accès (places des deux côtés) divise par ~2,5 la surface par place et
libère du sol pour un bâtiment plus grand : **+12 logements**, et le statut « exploitable » est
désormais **honnête** (un seul volume, distance inter-bâtiments sans objet).

---

## LOT B — Deux autres témoins (même moteur, mêmes conventions)

Seul calibrage autorisé : le **barème de stationnement** de la zone s'il manque. Cas ici :
Saint-André **UC 12.2** était `propose` → ajouté en feuille `par_typologie` validée (citation
verbatim, par surface de plancher : < 50 m² → 1 place, ≥ 50 m² → 1,5, arrondi inférieur).
Saint-Denis **Ui** avait déjà un barème validé (1 place/logement).

### Saint-André — AX 255 + 256, zone UC

| | Archi (référence) | LABUSE |
|---|---:|---:|
| Logements | 48 collectifs | **27** (T2 15 · T3 9 · T4 3) |
| Surface | 2 568 m² intérieurs | SDP 1 902 m² · SHAB 1 260 m² |
| Niveaux | R+2 | **R+2** |
| Places | 48 (1/logt) | **40** (barème ≥ 50 m² → 1,5) |
| Statut | — | **à compléter** |

Contenance 4 163 m² (dessin 4 144, écart 18). Stationnement : **allée unique, deux côtés**,
40 places = 40 imposées (**Réussi**), 19,9 m²/place. Emprise 634 m². Perméabilité (40 %) **Réussi**
(2 715 ≥ 1 665 m²). Pas de CES en UC → emprise **Non effectué**. Dénivelé 2,7 m (3,2 %), non pris
en compte.

**Pourquoi l'écart (48 → 27), qui ne se corrige pas en réglant le moteur :**
- **PPR « B3 » (inondation + mouvements de terrain) couvre 3 745 m² des 4 145 m²** de l'assiette :
  toute construction la touche → l'étude passe honnêtement **« à compléter »** (prescriptions à
  lire). L'archi a composé avec ; le moteur la signale, il ne l'interprète pas.
- **Barème.** Nos modules ≥ 50 m² imposent 1,5 place ; l'archi compte 1/logement (clause « < 50 m² »
  ou « logement aidé » du même article). Nos logements plus grands coûtent plus de stationnement
  aérien → moins de logements à surface égale.
- **Forme.** Le moteur ne pose qu'une barre rectangulaire plaquée sur le grand axe ; l'architecte
  épouse le contour et préfère un bâtiment plus étendu.

### Saint-Denis — DL 247 + 248, zone Ui (PPR rouge et bleue)

| | Archi (référence) | LABUSE |
|---|---:|---:|
| Logements | 22–27 (RPA ; cartouche incohérent) | **12** (T2 6 · T3 6) |
| Places | 8 (RPA, 1 pour 3) | **12** (Ui : 1/logement, validé) |
| Emprise | 377 m² | 174 m² |
| Hauteur | max 18 m | **R+5 ≈ 18 m** |
| Statut | — | **exploitable** |

Contenance 1 580 m² (dessin 1 544, écart 36). **PPR rouge (interdiction, 548 m²) retirée de la zone
d'implantation** → zone réduite à 650 m². **PPR bleue (prescription, 234 m²) signalée** : le bâti
proposé **ne la touche pas** → l'étude reste **exploitable**. Barème Ui 1/logt → 12 places = 12
imposées (**Réussi**). Allée unique, **un seul côté** (largeur libre < 15 m). Pas de règle de pleine
terre en Ui → perméabilité **Non effectué**. **Prospect L > H non chiffrable** → hauteur bornée par
la **seule règle absolue (18 m)**, dit ici. Dénivelé 3,3 m (6 %), non pris en compte.

**Pourquoi l'écart (22–27 → 12), structurel :**
- **RPA.** L'archi est une résidence pour personnes âgées : logements plus petits et **dérogation de
  stationnement (1 pour 3 → 8 places)**. Le moteur applique la **règle générale Ui validée
  (1/logement)** ; il ne modélise pas la dérogation RPA.
- **PPR rouge** déduite : la zone constructible tombe à 650 m² ; notre barre y est prudente
  (emprise 174 vs 377 pour l'archi, qui occupe davantage le hors-rouge).
- Les deux s'accordent sur l'essentiel : **bâti hors zone rouge**.

---

## Récapitulatif des trois terrains

| Terrain | Zone | Forme | Logts | Places | m²/place | Statut | Contrôles (R·NE·NA) |
|---|---|---|---:|---:|---:|---|---|
| L'Étang-Salé | UA | barre R+3 | **28** | 34 | 18,6 | exploitable | 5 · 1 · 4 |
| Saint-André | UC | barre R+2 | **27** | 40 | 19,9 | à compléter | 4 · 5 · 1 |
| Saint-Denis | Ui | barre R+5 | **12** | 12 | 30,8 | exploitable | 4 · 5 · 1 |

Même moteur, mêmes conventions, aucun réglage par terrain : la zone, les règles (avec le verrou
« validée + citation »), les PPR et la voirie viennent toutes des données. **61 tests verts** sur les
trois terrains (chevauchement tous couples, allées reliées, somme des surfaces = assiette,
contenance, barème, déterminisme).

## Reproduire

```
PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
<python> -c "from labuse.implantation import moteur, rendu; \
from labuse.implantation.moteur import IDUS_SAINT_ANDRE as A; \
s=moteur.etudier(idus=A); rendu.rendre_plan_png(s,'plan.png'); rendu.ecrire_scenario_json(s,'s.json')"
```

Tests : `pytest tests/test_implantation1.py` (marqués `reel`, 61 tests, paramétrés sur les trois
terrains ; nécessite `LABUSE_APP_DATABASE_URL`).
