# PLU-CALIBRAGE-5 lot 2 — famille B (écarts / attributions) relue et tranchée

**335 règles B relues** (agent par commune, lecture de la citation stockée + du PDF authentique quand insuffisante). Décisions : **valider 103** · **corriger 41** · **absent 16** · formule 100 (→ lot 3) · propose 75 (reste).

**Appliqué : 155 feuilles** passées `valide` (valider 99 · corriger 40 · absent 16). Bilan règles : **propose 419 → 264**, valide 1563 → 1718.

## Méthode & garanties

- Un agent interne par commune relit CHAQUE règle : la `citation` stockée (texte verbatim du règlement, capturé en PLU-CALIBRAGE-3) d'abord, le PDF authentique (`data/plu_reglements/`) à la page citée ±3 quand elle ne suffit pas. Zéro invention : chaque `valider`/`corriger` cite la sous-chaîne EXACTE portant la valeur.

- **Garde anti-invention** (`qa/plu_calibrage5_appliquer.py`) : une décision n'est écrite que si le nombre décidé apparaît LITTÉRALEMENT dans la preuve. **5 refusées** (Saint-Paul retraits.voie « à l'alignement » → 0 m inféré, « 0 » non littéral) — laissées `propose`.

- **Contre-vérification** : les 144 preuves de valider/corriger ont été cherchées dans la citation stockée (117) ou le PDF complet (27, cas des renvois 1AU→U lus dans la section U) — **0 preuve introuvable, 0 fabrication**.

- « Chaque décision porte sa citation » : quand la valeur décidée n'était pas dans la citation stockée (renvoi, ou écart harmonisé), la PREUVE vérifiée devient la citation de la feuille. Les `absent` portent la preuve du SILENCE (« Il n'est pas fixé de règle », « non règlementé »).

- V6a re-vérifié : **1718 valide, 0 sans article+page+citation** (5 articles Saint-Paul complétés depuis la citation « Article 9 » et les feuilles sœurs de la commune — lacune d'extraction).


## Exemples (les écarts nommés du mandat)

- **Saint-Joseph U2a stationnement 1 → 2 places** (corrigé, « secteur U2a … 2 places »).

- **Saint-Pierre hauteurs de secteur** : Uazp/Uazpc faîtage 21 → 20 m, Uaza faîtage 21 → 14 m (corrigés).

- **Sainte-Suzanne 6 m** : le texte dit « H/2 avec minimum 5 m » (voie) — pas un nombre fixe → formule (lot 3), l'ancien 6 était faux.


## Décisions par commune

| commune | valider | corriger | absent | formule→L3 | propose |
| --- | --- | --- | --- | --- | --- |
| Les Avirons | 24 | 0 | 0 | 0 | 0 |
| Bras-Panon | 6 | 0 | 0 | 12 | 0 |
| Entre-Deux | 2 | 0 | 0 | 0 | 0 |
| L'Étang-Salé | 4 | 0 | 0 | 0 | 0 |
| Petite-Île | 0 | 0 | 0 | 2 | 0 |
| Le Port | 10 | 0 | 2 | 15 | 0 |
| La Possession | 0 | 2 | 5 | 21 | 2 |
| Saint-Benoît | 10 | 0 | 0 | 5 | 0 |
| Saint-Joseph | 4 | 3 | 0 | 11 | 50 |
| Saint-Louis | 0 | 2 | 0 | 8 | 0 |
| Saint-Paul | 4 | 23 | 3 | 1 | 1 |
| Saint-Pierre | 21 | 5 | 6 | 2 | 3 |
| Sainte-Marie | 0 | 6 | 0 | 8 | 19 |
| Sainte-Rose | 15 | 0 | 0 | 10 | 0 |
| Sainte-Suzanne | 0 | 0 | 0 | 4 | 0 |
| Les Trois-Bassins | 3 | 0 | 0 | 1 | 0 |
