# Saint-Philippe — BLOCAGE : PLU propre `97417` absent du GPU (2026-06-22)

- **Commune / INSEE** : Saint-Philippe / `97417`
- **Statut** : 🔴 **NON VALIDABLE** — bloquée pour cause de zonage inutilisable
- **État conservé** : `partiel_non_evalue` · **non-gold / non-fiable** · bandeau « Partielle — non évaluée » conservé
- **Date du constat** : 2026-06-22

> Cette note documente un **blocage**. Elle ne modifie ni la base, ni les verdicts,
> ni la configuration. **Aucun run / cascade / re-fetch n'a été lancé** — le blocage
> a été détecté **au pré-vol** (analyse lecture seule), avant toute exécution.

## Contexte

Saint-Philippe (commune du Sud, secteur volcan — Piton de la Fournaise) était la cible
du **pré-vol** suivant, après la validation au standard « Saint-Paul » des **8 communes
gold** : Saint-Paul (référence), L'Étang-Salé, La Possession, Saint-Pierre, Le Tampon,
Saint-Louis, Saint-Denis, Saint-Joseph.

Stratégie prévue : `re_couches_re_cascade` (vague 6, risque moyen). Le registre
(`config/communes_gold_standard.yaml`) flaggait déjà « **couverture GPU faible en base** » —
le pré-vol confirme qu'elle est en réalité **nulle**.

## État actuel (mesuré au pré-vol, lecture seule)

| Élément | Valeur |
|---|---|
| Parcelles | **4 162** |
| Sections | **29** |
| Doublons IDU | **0** |
| Géométries invalides | **0** |
| `geom_2975` nuls | **0** |
| Évaluées | **0 / 4 162** |
| Couverture zonage PLU propre | **0,00 %** (0 / 4 162) |

Cadastre **propre** par ailleurs (0 doublon, 0 géométrie invalide, 0 `geom_2975` nul) —
mais **non exploitable** sans zonage.

## Détection au pré-vol — pas de run réel

Le blocage a été **identifié en amont** par l'analyse de couverture zonage du pré-vol.
**Aucun run réel n'a été lancé**, donc **aucun rollback** n'a été nécessaire et **aucun
rapport `saint_philippe_RESULTS.md`** n'a été généré. La base est strictement inchangée.

> ⚠️ Rappel : le **dry-run**/pré-checks ne vérifient que la *présence* d'une couche
> `plu_gpu_zone` (19 > 0), **pas la couverture réelle**. Seul le post-check
> `couverture zonage ≥ 99 %` (après cascade) attraperait le problème — d'où l'intérêt
> d'avoir tranché au pré-vol pour **ne pas gâcher un run** qui finirait en rollback.

## Cause racine

**Aucune zone PLU propre à Saint-Philippe (`97417`) n'est disponible dans le GPU**
(Géoportail de l'Urbanisme). Le document d'urbanisme communal de Saint-Philippe est
absent du flux : **aucune partition `DU_97417`**, aucun `idurba` `97417`.

Les **19 zones** récupérées par le fallback GPU sur l'emprise **n'appartiennent pas à
Saint-Philippe** mais à des **communes voisines** :

| Commune voisine | Partition | Zones |
|---|---|---|
| Saint-Joseph | `DU_97412` | 18 |
| Sainte-Rose | `DU_97419` | 1 |

Et elles sont si marginales sur l'emprise qu'elles **ne couvrent aucune parcelle** de
Saint-Philippe.

## Conséquence

- Couverture zonage **propre** (`97417`) des parcelles de Saint-Philippe : **0 %**.
- Couverture par **toute** zone (y compris débordement voisin) : **0,00 %** (0 / 4 162).
- Le contrôle critique **`couverture zonage ≥ 99 %`** est **impossible à passer**.
- Tout run de validation au standard gold **échouera donc nécessairement** sur ce contrôle,
  indépendamment du reste (parcelles, bâti, voirie, cascade).

C'est le **3ᵉ cas Saint-Leu-bis** (après Saint-Leu `97413` et Saint-André `97409`) :
**run réel impossible** tant qu'une **source officielle fiable `97417`** n'est pas disponible.

## Décision

- Saint-Philippe **reste `partiel_non_evalue`**.
- Saint-Philippe **reste non-gold / non-fiable** ; le bandeau « Partielle — non évaluée » est **conservé**.
- **Config inchangée**, **aucun verdict modifié**, aucune donnée publiée.

## Condition de reprise

Reprise de Saint-Philippe **conditionnée** à l'une des situations suivantes :

1. **Disponibilité d'un PLU/GPU `97417` fiable** dans le flux GPU (document d'urbanisme
   propre à Saint-Philippe, couvrant ses parcelles) ; **ou**
2. **Source alternative officielle validée** fournissant le zonage réglementaire de
   Saint-Philippe avec une couverture suffisante pour passer le contrôle
   `couverture zonage ≥ 99 %`.

## Consigne

> ⛔ **Ne pas relancer Saint-Philippe** (run / cascade / re-fetch / passage gold) tant que
> la **condition de reprise** ci-dessus n'est pas remplie. Toute relance retomberait sur le
> même échec de zonage garanti (couverture 0 %).
