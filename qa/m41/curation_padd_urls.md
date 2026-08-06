# M41 — Curation conjointe : trouver le débat PADD des 3 cibles réelles

**But** : armer la vigilance sursis. Elle reste ÉTEINTE tant que le `debat_padd` de la cible n'est
pas une date **constatée et sourcée** (arbitrage Vic : pas de conditionnel flou en fiche). Saint-
Philippe (élaboration dormante 2002) est HORS de cette curation — pas de sursis sur une procédure
dormante.

## Ce qu'on cherche
La date du **débat sur les orientations générales du PADD** (Code urb. L.153-11) — c'est le seuil
légal du sursis à statuer. Elle figure dans une **délibération du conseil municipal** (« débat sans
vote sur les orientations du PADD »), au **recueil des actes administratifs** de la commune ou dans
les pièces de la procédure sur le **Géoportail de l'urbanisme (GPU)**.

## Où chercher (points d'entrée — Vic complète / confirme)

| Cible | INSEE | Révision prescrite | Points d'entrée à visiter |
|---|---|---|---|
| **Saint-André** | 97409 | 2022-06-22 | Site commune (rubrique PLU/urbanisme) + recueil des actes ; GPU `https://www.geoportail-urbanisme.gouv.fr` (commune 97409) ; **contact mairie déjà en main (Vic)**. |
| **Saint-Leu** | 97413 | 2022-05-17 | Site commune Saint-Leu (PLU en révision) + recueil des actes ; GPU commune 97413. |
| **Les Trois-Bassins** | 97423 | 2022-06-02 | Site commune Les Trois-Bassins + recueil des actes ; GPU commune 97423. |

> Je ne fabrique pas d'URL profonde de délibération que je n'ai pas vérifiée (doctrine). Ci-dessus =
> les points d'entrée officiels ; la référence exacte de la délib se fixe à la visite.

## Format d'entrée attendu (à reporter dans `config/veille_plu.yaml`)
Pour chaque cible dont le débat PADD est trouvé et daté :

```yaml
  "97409":
    stade: "debat_padd"              # avance depuis "prescrite"
    debat_padd: "2024-03-12"         # date ISO du débat PADD (la pièce)
    source: "Délibération conseil municipal n°… du 12/03/2024 (débat PADD)"
    source_url: "https://…"          # URL de la délib / recueil des actes
    date_constat: "2026-08-XX"       # jour de la vérification
    confiance: "SOURCE"              # SOURCE une fois la pièce en main
```

Après édition : `PYTHONPATH=src python scripts/veille_plu_check.py` (lint) puis
`… --diff config/veille_plu.<snapshot>.yaml` pour voir ce qui a bougé. La vigilance sursis
s'allumera automatiquement (radar = point de calcul unique) pour les parcelles de la commune.

## Rappel — ce qu'on NE met pas
- Pas de `debat_padd` « supposé » ou déduit d'un calendrier : SOURCE ou rien.
- Pas de vigilance sursis servie tant que `confiance != SOURCE` sur le PADD.
- Jamais d'affirmation sur l'issue de la révision (zonage futur) — radar = stade + droit actuel.
