# Saint-Leu — BLOCAGE : PLU propre `97413` absent du GPU (2026-06-21)

- **Commune / INSEE** : Saint-Leu / `97413`
- **Statut** : 🔴 **NON VALIDABLE** — bloquée pour cause de zonage inutilisable
- **État conservé** : `partiel_non_evalue` · **non-gold** · bandeau « Partielle — non évaluée » conservé
- **Date du constat** : 2026-06-21

> Cette note documente un **blocage**. Elle ne modifie ni la base, ni les verdicts,
> ni la configuration. Aucun run / cascade / re-fetch n'a été lancé pour la produire.

## Contexte

Saint-Leu était la cible du **pré-vol** suivant, après la validation au standard
« Saint-Paul » des **5 communes gold** : Saint-Paul (référence), L'Étang-Salé,
La Possession, Le Tampon, Saint-Pierre.

Stratégie prévue : `re_couches_re_cascade` (vague 2, risque moyen) — ré-ingestion
ciblée des couches puis ré-évaluation complète.

## État pré-run (état actuel, après rollback)

| Élément | Valeur |
|---|---|
| Parcelles | **22 959** |
| Évaluées | **0** |
| Bâti (couche) | **0** |
| Pente (couche) | **0** |
| Voirie (couche) | **5 000** |
| Couverture zonage PLU propre | **~0,1 %** |

## Tentative de run réel — arrêtée puis rollbackée

Un run réel a été tenté puis **interrompu en pleine cascade** à **6 000 / 22 959
parcelles** (le process de fond n'a pas survécu à une reprise du conteneur),
laissant la base dans un **état intermédiaire dangereux** (couches ré-ingérées +
parcelles upsertées + verdicts partiels).

La base a été **intégralement restaurée** depuis le backup pré-commune
`/var/backups/labuse/labuse-labuse-20260621-160213.dump` (procédure officielle
`labuse restore-db`). Vérifié après restore : 18 communes / 377 194 parcelles,
les 5 gold intactes, Saint-Leu revenue à **22 959 parcelles / 0 évaluée**.
Aucun rapport `saint_leu_RESULTS.md` n'a été généré (post-checks jamais atteints).

## Cause racine

**Aucune zone PLU propre à Saint-Leu (`97413`) n'est disponible dans le GPU**
(Géoportail de l'Urbanisme). Le document d'urbanisme communal de Saint-Leu est
absent du flux.

Les zones « PLU » récupérées par le fallback GPU sur l'emprise **n'appartiennent
pas à Saint-Leu** mais à des **communes voisines** :

- Les Avirons
- Saint-Louis
- Trois-Bassins
- L'Étang-Salé
- Cilaos

Elles tombent dans/autour de l'emprise par débordement géographique, mais ne
constituent **pas** le zonage réglementaire de Saint-Leu.

## Conséquence

- Couverture zonage **fiable** des parcelles de Saint-Leu : **~0,1 %**.
- Le contrôle critique **`couverture zonage ≥ 99 %`** **échoue** de façon
  catastrophique.
- Tout run de validation au standard gold **échouera donc nécessairement** sur ce
  contrôle, indépendamment du reste (parcelles, bâti, voirie, cascade).

Le zonage étant une entrée structurante de la cascade, des verdicts produits sur
une base zonage à ~0,1 % seraient **non fiables** et ne doivent pas être publiés.

## Décision

- Saint-Leu **reste `partiel_non_evalue`**.
- Saint-Leu **reste non-gold** ; le bandeau « Partielle — non évaluée » est **conservé**.
- **Aucun verdict modifié**, aucune donnée publiée.

## Condition de reprise

Reprise de Saint-Leu **conditionnée** à l'une des situations suivantes :

1. **Disponibilité d'un PLU/GPU `97413` fiable** dans le flux GPU (document
   d'urbanisme propre à Saint-Leu, couvrant ses parcelles) ; **ou**
2. **Source alternative officielle validée** fournissant le zonage réglementaire
   de Saint-Leu avec une couverture suffisante pour passer le contrôle
   `couverture zonage ≥ 99 %`.

## Consigne

> ⛔ **Ne pas relancer Saint-Leu** (run / cascade / re-fetch / passage gold) tant
> que la **condition de reprise** ci-dessus n'est pas remplie. Toute relance
> retomberait sur le même échec de zonage et reproduirait l'état intermédiaire
> dangereux.
