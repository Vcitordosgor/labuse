# Saint-Paul — pilote re-cascade Étape A (quick-win PPR PM1 < 10 %)

> **Pilote de mesure** de l'effet réel de l'Étape A PPR v2 (mergée sur `main` à `7490f75`) : une parcelle
> seulement **marginalement** touchée par un périmètre PM1/PPR (< 10 % de sa surface) ne reçoit plus de
> SOFT_FLAG **fort** bloquant, mais une note informative **faible**. Mesuré sur **Saint-Paul (97415)**,
> commune gold la plus bénéficiaire (≈ 139 parcelles < 10 % ; Saint-André est couvert à ~98,6 % → quasi
> insensible). **Saint-Paul reste gold (aucun passage gold), aucune Étape B (rouge/bleu).**

## Verdict : 🟢 **GO — l'Étape A fonctionne comme conçu**

**+81 opportunités réelles** créées par le quick-win sur Saint-Paul, **0 opportunité perdue à cause de
l'Étape A**, **rouge/bleu non utilisé**, **seuil 65 inchangé**, **aucune autre commune ni couche modifiée**.

## Contexte

| Élément | Valeur |
|---|---|
| `main` (code) | **`7490f75`** (Étape A mergée) |
| Backup pré-pilote | `/var/backups/labuse/labuse-pre-saint-paul-ppr-stepa-20260624-212243.dump` (1 068 Mo) |
| SHA-256 | `e4ec5eab26445b925d89017d32642308b9f66f1fd806f7400b83cf537c1bcd48` (sidecar `…dump.sha256`, `sha256sum -c` OK, `pg_restore --list` 190 TOC, tables critiques OK) |
| Commune pilote | **Saint-Paul / 97415** (gold), 51 129 parcelles |
| Runner | `run_all.evaluate_commune` (cascade + scoring + déclassement, **sans ré-import couches**) ; exit **0**, 51 129 évaluées en 7 153 s |

## Chiffres avant / après (verdicts latest, Saint-Paul)

| Verdict | Avant | Après | Δ net |
|---|---|---|---|
| **Opportunité** | 1 848 | **1 905** | **+57** |
| À creuser | 15 852 | 15 397 | −455 |
| Écartée | 1 532 | 1 537 | +5 |
| Faux positif probable | 31 897 | 32 290 | +393 |

## Effet Étape A ISOLÉ (analyse de transition par parcelle)

| Transition | n |
|---|---|
| Gagne « opportunité » (avant ≠ opp → après = opp) | **82** |
| … **dont via flag marginal (Étape A)** | **81** |
| Perd « opportunité » (avant = opp → après ≠ opp) | 25 |
| … dont via flag marginal | **0** |

→ **Effet propre de l'Étape A = +81 opportunités** (parcelles déflaguées < 10 % atteignant le seuil).
Les **−25 pertes ne sont PAS dues à l'Étape A** (0 via marginal) : ce sont des reclassements liés à la
**dérive de code** (la re-cascade applique le code actuel complet, plus récent que l'éval Saint-Paul d'origine).
Le **net** Saint-Paul (+57) = +81 (Étape A) − ~24 (dérive).

## Delta flags PPR (cascade_results rafraîchis)

| | Avant | Après |
|---|---|---|
| PPR **fort** | 17 577 | 15 081 |
| PPR **faible / marginal** (note « < 10 % ») | 0 | **4 742** |

→ **4 742 parcelles déflaguées** (périmètre PM1 marginal). Sur ces 4 742, seules **81** franchissent le seuil
65 (fort→faible = **+10** au score, suffisant uniquement si score ≥ 55) ; les autres restent « à creuser » /
faux positif (score insuffisant ou autre contrainte) — comportement attendu, **conservateur**.

## Delta opportunités : réel vs estimation

| | Valeur |
|---|---|
| Estimation pré-vol (PPR-seul + score ≥ 55 + < 10 %) | ~67 |
| **Réel (Étape A, via marginal)** | **+81** |

Légèrement **au-dessus** de l'estimation conservatrice — l'Étape A délivre bien sur une commune bord-rognée.

## Contrôles d'intégrité

- ✅ **Seuil scoring = 65** inchangé (`opportunity_threshold`).
- ✅ **Rouge/bleu non implémenté/non utilisé** : `risques` HARD_EXCLUDE (rouge) sur Saint-Paul = **0**.
- ✅ **Seule Saint-Paul re-évaluée** : 51 129 nouvelles `parcel_evaluations`, **aucune autre commune**.
- ✅ **Couches intactes** : `spatial_layers` non modifiées (re-cascade ne touche pas les couches).
- ✅ **Anciennes `parcel_evaluations` conservées** (empilées, non nettoyées) — l'« avant » = avant-dernière éval.
- ✅ **DB globale** : 418 068 parcelles / 22 communes / **gold 16** inchangés.

## Limites

- **La re-cascade n'isole pas parfaitement l'Étape A** : elle ré-applique le **code actuel complet** vs des
  évals Saint-Paul **plus anciennes** → le **net** (+57) inclut une **dérive** (−25 pertes hors-Étape-A,
  fpp +393). L'effet Étape A **propre** (+81, via marginal) est en revanche **net et non ambigu**.
- **Décalage du total de flags `risques`** (17 577 → 19 823 incl. faible) : la re-cascade recalcule toutes les
  intersections sur l'état courant ; l'éval d'origine était plus ancienne. À noter, sans incidence sur la
  mesure Étape A.
- **Couverture par feature** (pas sommée si plusieurs PPR se chevauchent) — cas rare, cf. spec.
- **Mesure d'opportunité ≠ valeur foncière** : +81 « opportunité » = candidats à instruire, pas des leads validés.

## Verdict & recommandation

- **Verdict Étape A : 🟢 GO.** Le quick-win < 10 % fonctionne (+81 opportunités réelles, 0 perte imputable,
  rouge/bleu et seuil 65 intacts). Conservateur et sûr.
- **Recommandation (une seule) : généraliser l'Étape A** aux autres communes **bord-rognées** (Saint-Pierre,
  Le Tampon, La Possession, Saint-Louis, Saint-Benoît, Saint-Joseph), **re-cascade pilotée commune par commune
  avec backup**, en **examinant d'abord la dérive** (les −25 pertes Saint-Paul) pour décider si un refresh
  global des évals gold est souhaité. **Saint-André / Saint-Denis → Étape B** (rouge/bleu), où le quick-win
  est quasi inopérant (couverture ~97 %).
- **Ne PAS** baisser le seuil 65, **ne PAS** neutraliser le PPR, **ne PAS** traiter le bleu comme libre
  (Étape B séparée).

---

### Provenance (lecture seule, hors mutation pilote)

- Mutation **autorisée et unique** : re-cascade Saint-Paul (`evaluate_commune`), backup préalable validé.
- Mesures : SELECT sur `parcel_evaluations` (latest + avant-dernière) et `cascade_results` (dernière passe).
- Aucun import, aucune couche modifiée, aucune autre commune touchée, aucun passage gold, aucun changement de
  code/config/scoring, aucun rouge/bleu, aucun contact DEAL.
