# MANDAT SCORING-4 — ré-entraîner le modèle avec les gains prouvés, sur les données neuves

**Nature** : ré-entraînement + run candidat. **Aucune promotion.**
**Modèle CC** : Fable.
**Branche** : `feat/scoring-4` depuis `main` (SOURCES-1 mergé). **Worktree** : `~/Desktop/labuse-scoring4`.
**À reprendre** : la branche `audit/scoring-donnees-1` (non poussée) porte le harnais et les variables mesurées — les rapatrier ici (cherry-pick ou copie des scripts), ne pas les réécrire.
**Livrables** : nouvel artefact gelé, run candidat `q_v14`, avis d'arène, note de version, `docs/audit-2026-09/SCORING-4.md`.
**Interdits** : aucun `promote`, aucune écriture sur `config/served_run.txt`, aucun merge. `q_v11_m137` reste le run servi jusqu'à décision de Vic.

## Étape 0 — trancher deux réserves AVANT de lancer quoi que ce soit
`pwd`, branche, arbre propre. Puis répondre par écrit, preuve `fichier:ligne` :
1. **Le pipeline sait-il réutiliser la cascade d'un run existant sous un nouveau run_id ?** On veut repartir de l'étage 0 de `q_v13_sources1` (ses 4 378 exclusions comprises) sans rejouer la cascade. Si non : dire ce que coûte le rejeu et attendre l'arbitrage de Vic.
2. **Les 22 sources de SOURCES-1 ont-elles ajouté des colonnes au dataset d'apprentissage ?** Si oui, le rebuild features est obligatoire et le temps double — le dire avant de commencer.
Si l'une des deux réponses bloque : s'arrêter et rendre compte, sans rien calculer.

## Recette du candidat (rien d'autre)

> **Le point central de ce mandat : `q_v14` doit porter EN MÊME TEMPS les deux améliorations qui n'ont jamais été combinées.**
> - **De `q_v12`** (gains de MODÈLE, jamais servis) : K2, K3, K4bis, isotonique par segment. Ils sont dans la recette, pas dans un run réutilisable — il faut les rejouer.
> - **De `q_v13_sources1`** (gains de DONNÉES, calculés mais non servis) : les 22 sources ingérées et sa cascade, dont les 4 378 exclusions neuves.
> Un candidat qui n'aurait que l'un des deux est un échec du mandat. Le contrôle est explicite : vérifier dans le manifeste que les features issues de q_v12 ET les données/cascade de q_v13_sources1 sont toutes présentes, et le dire dans le rapport.

Base **q_v12** (jamais servie) : K2 features mortes retirées, K3 résiduel lu à ~99 %, K4bis voisinage global, isotonique par segment.
Plus les **4 gains prouvés par SCORING-DONNÉES-1**, chacun as-of :
- bâti/nu reconstruit à la date de la ligne (`nu_asof`, `pct_bati_secteur_asof`) ;
- **PC déposé par un professionnel (SIREN) sur une parcelle détenue par un particulier** ;
- ancienneté du PLU ;
- ventes à acquéreur PM dans le secteur sur 36 mois (à surveiller : dégradait l'ECE PM — ne la garder que si l'ECE tient).
Sur les **données du jour** (22 sources, cascade de `q_v13_sources1`).
**Rien d'autre n'entre.** Pas de variable ajoutée en cours de route, pas de changement de cible : la cible reste **toute vente sous 12 mois**.

## Travail
1. **Rebuild du dataset** d'apprentissage avec ces variables (poste le plus long).
2. **Ré-entraînement** : re-binning WoE, coefficients, croisements, calibration isotonique par segment. Ce n'est PAS un re-score : nouvel artefact, nouveau sha256, nouveau manifeste de gel.
3. **Walk-forward 6 plis** comme l'artefact servi, plus le banc **K0** (train ≤2023 · cal 2024 · test 2025) pour comparer à q_v12 et au servi.
4. **Run candidat `q_v14`** par le pipeline, réutilisant la cascade de `q_v13_sources1` si l'étape 0 l'autorise. Scoring seul, **pas de résiduel** (il ne bouge pas).
5. **Arène** : candidat contre servi — churn top, ECE, boussole golden, avis.
6. **Libellés français des 4 variables neuves** dans le dictionnaire des contributions servi (le « top-5 lisible » de la fiche), par exemple « un professionnel a déposé un permis sur cette parcelle détenue par un particulier », « PLU ancien de N ans ». Sans ça, une bascule afficherait des noms de colonnes dans « Analyse LABUSE ».
7. **Note de version** en français : ce qui monte, ce qui descend, pourquoi, et le churn de tête annoncé franchement.

**Reprise** : un commit et un cache local par étape (dataset construit, artefact gelé, run scoré, arène). Si la session tombe, on repart de la dernière étape, jamais de zéro.

## Ce que le rapport doit contenir
- **LE tableau** (format SCORING-2), quatre colonnes : servi `q_v11_m137` · `q_v12` (modèle seul) · `q_v13_sources1` (données seules) · candidat `q_v14` (les deux). C'est ce qui permet de dire ce qui vient des données et ce qui vient du modèle.
- **Les paliers**, effectifs et précision par palier, île et Saint-Paul.
- **Les 50 premières Priorité** du candidat face au servi, chacune avec ses trois raisons en français.
- **Combien de parcelles changent de palier**, et lesquelles montent grâce au signal « permis d'un pro ».
- Ce qui a été **écarté** et pourquoi.
- **En passant, sans rien mesurer** : parmi les 22 sources de SOURCES-1, lesquelles feraient de bonnes variables pour un prochain ré-entraînement (une ligne par source : signal supposé, couverture, as-of possible ou non). Aucune n'entre dans q_v14.

## Garde-fous
- Test de fuite rejoué sur chaque variable neuve ; le lot s'arrête si un test casse.
- Si l'ECE se dégrade de plus de 0,01 sur un segment, la variable responsable sort.
- Si la précision de tête ne dépasse pas le servi, le dire et ne pas maquiller.
- Rien n'est promu : Vic bascule lui-même, après lecture, avec `golden promote`.
