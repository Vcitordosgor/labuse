# Saint-André — BLOCAGE : PLU propre `97409` absent du GPU (2026-06-21)

- **Commune / INSEE** : Saint-André / `97409`
- **Statut** : 🔴 **NON VALIDABLE** — bloquée pour cause de zonage inutilisable
- **État conservé** : `partiel_non_evalue` · **non-gold** · bandeau « Partielle — non évaluée » conservé
- **Date du constat** : 2026-06-21

> Cette note documente un **blocage**. Elle ne modifie ni la base, ni les verdicts,
> ni la configuration. **Aucun run / cascade / re-fetch n'a été lancé** — le blocage
> a été détecté **au pré-vol** (analyse lecture seule), avant toute exécution.

## Contexte

Saint-André était la cible du **pré-vol** suivant, après la validation au standard
« Saint-Paul » des **7 communes gold** : Saint-Paul (référence), L'Étang-Salé,
La Possession, Saint-Pierre, Le Tampon, Saint-Louis, Saint-Denis.

Stratégie prévue : `re_couches_re_cascade` (vague 3, risque moyen) — ré-ingestion
ciblée des couches puis ré-évaluation complète.

## État actuel (mesuré au pré-vol, lecture seule)

| Élément | Valeur |
|---|---|
| Parcelles | **22 600** |
| Sections | **33** |
| Évaluées | **0** |
| Bâti (couche) | **0** |
| Voirie (couche) | **5 000** (plafonnée) |
| Pente (couche) | **3 819** |
| Couverture zonage PLU propre | **0,018 %** (4 / 22 600) |

Cadastre propre par ailleurs (0 doublon IDU, 0 `geom_2975` nul, 2 géométries
invalides mineures) — mais **non exploitable** sans zonage.

## Détection au pré-vol — pas de run réel

Contrairement à un échec en cours de run, le blocage a été **identifié en amont**
par l'analyse de couverture zonage du pré-vol. **Aucun run réel n'a été lancé**,
donc **aucun rollback** n'a été nécessaire et **aucun rapport
`saint_andre_RESULTS.md`** n'a été généré. La base est strictement inchangée.

> ⚠️ À noter : le **dry-run** du script générique sort en `exit 0` car ses
> pré-checks ne vérifient que la *présence* d'une couche `plu_gpu_zone` (277 > 0),
> **pas la couverture réelle**. Seul le post-check `couverture zonage ≥ 99 %`
> (après cascade) attraperait le problème — d'où l'intérêt d'avoir tranché au
> pré-vol pour **ne pas gâcher un run** qui finirait en rollback.

## Cause racine

**Aucune zone PLU propre à Saint-André (`97409`) n'est disponible dans le GPU**
(Géoportail de l'Urbanisme). Le document d'urbanisme communal de Saint-André est
absent du flux : **aucune partition `DU_97409`**, aucun `idurba` `97409`.

Les **277 zones** récupérées par le fallback GPU sur l'emprise **n'appartiennent
pas à Saint-André** mais à des **communes voisines** :

| Commune voisine | Partition | Zones |
|---|---|---|
| Sainte-Suzanne | `DU_97420` | 179 |
| Bras-Panon | `DU_97402` | 84 |
| Salazie | `DU_97421` | 12 |
| Sainte-Marie | `DU_97418` | 2 |

Elles tombent dans/autour de l'emprise par débordement géographique, mais ne
constituent **pas** le zonage réglementaire de Saint-André.

## Conséquence

- Couverture zonage **propre** (`97409`) des parcelles de Saint-André : **0 %**.
- Couverture par **toute** zone (y compris débordement voisin) : **0,018 %**
  (4 parcelles sur 22 600, à la frontière).
- Le contrôle critique **`couverture zonage ≥ 99 %`** est **impossible à passer**.
- Tout run de validation au standard gold **échouera donc nécessairement** sur ce
  contrôle, indépendamment du reste (parcelles, bâti, voirie, cascade).

C'est **exactement le cas Saint-Leu** (`97413` absent du GPU) : run réel impossible.

## Décision

- Saint-André **reste `partiel_non_evalue`**.
- Saint-André **reste non-gold** ; le bandeau « Partielle — non évaluée » est **conservé**.
- **Config inchangée**, **aucun verdict modifié**, aucune donnée publiée.

## Condition de reprise

Reprise de Saint-André **conditionnée** à l'une des situations suivantes :

1. **Disponibilité d'un PLU/GPU `97409` fiable** dans le flux GPU (document
   d'urbanisme propre à Saint-André, couvrant ses parcelles) ; **ou**
2. **Source alternative officielle validée** fournissant le zonage réglementaire
   de Saint-André avec une couverture suffisante pour passer le contrôle
   `couverture zonage ≥ 99 %`.

## Consigne

> ⛔ **Ne pas relancer Saint-André** (run / cascade / re-fetch / passage gold) tant
> que la **condition de reprise** ci-dessus n'est pas remplie. Toute relance
> retomberait sur le même échec de zonage garanti.
