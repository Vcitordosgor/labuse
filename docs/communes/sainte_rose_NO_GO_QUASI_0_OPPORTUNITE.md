# Sainte-Rose (97419) — NO-GO gold : quasi-0 opportunité

**Décision (2026-06-23)** : Sainte-Rose est **différée** (NON-GOLD) après un run `import_complet` rendu
**techniquement propre** (exit 0 après dédup ciblée d'un doublon SAFER) mais dont le **résultat métier est
trop faible** (8 opportunités sur 6 287 parcelles, 0,1 %). Décision analogue à **La Plaine-des-Palmistes**
et **Les Trois-Bassins** : le run a fait son travail, mais le profil d'opportunité de la commune est
intrinsèquement quasi nul → **pas de passage gold** sans arbitrage produit/scoring.

## 1. Le run est techniquement propre (exit 0 après dédup)

Le run initial est sorti **exit 1 (ROLLBACK)** à cause d'**un seul** doublon EXACT de couche `safer`
(RPG agricole) — **corrigé proprement** par dédup ciblée :

| Étape | Détail |
|---|---|
| Doublon | couche `safer`, `subtype=rpg`, `name="Parcelle agricole RPG (CSA)"`, ids `{1357411, 1357421}` |
| Preuve | `ST_Equals` = true · `ST_OrderingEquals` = true · md5(WKB) & md5(geom_2975) égaux · attrs égaux |
| Suppression | **explicite par id** `DELETE … WHERE id = 1357421` (transaction gardée, rollback auto si ≠ 1) ; gardé `1357411` |
| Résultat | duplication **1 → 0** · `safer` **1 400 → 1 399** · **aucune re-cascade** (dédup verdict-neutre) |
| Exit final | **0 / 22 contrôles sur 22 verts** |

Après dédup : 6 287 parcelles · 6 287/6 287 évaluées · PLU propre `DU_97419` 100 % · voirie 6 941
(non tronquée) · bâti 6 229 · DVF 126 · PPR 2 · OSM 35 · 0 doublon de couche.

Backup pré-commune (point de retour, non utilisé) :
`/var/backups/labuse/labuse-pre-sainte-rose-20260623-160441.dump`
(SHA-256 `b42194cdf5032dd724a0904d5a2e4f7f87af3f99f79153cdff5be38b2cef7bda`).

## 2. Verdicts inchangés après la suppression

La suppression du doublon `safer` est **verdict-neutre** (le polygone supprimé est un doublon exact ; sa
suppression ne change aucune relation spatiale, l'identique subsistant via `1357411`) :

| Verdict | Avant dédup | Après dédup | % |
|---|---|---|---|
| faux positif probable | 3 697 | 3 697 | 58,8 % |
| à creuser | 1 818 | 1 818 | 28,9 % |
| écartée | 764 | 764 | 12,2 % |
| **opportunité** | **8** | **8** | **0,1 %** |

## 3. Mais le résultat métier est trop faible

**8 opportunités sur 6 287 parcelles (0,1 %).** La garde QA technique passe (0,1 % ≤ plafond 5 %, qui ne
borne que le haut), mais le résultat est **commercialement quasi nul**.

## 4. Pattern proche de La Plaine-des-Palmistes et Les Trois-Bassins

Même profil « quasi-0 opportunité ». Cause probable propre à Sainte-Rose : **commune volcanique** (Piton
de la Fournaise, coulées de lave), **aléas naturels forts** → **58,8 % de faux positifs probables** +
**12,2 % d'écartées** (le plus haut taux d'écartées des communes traitées, cohérent avec les contraintes
réglementaires/risques). Il ne reste quasiment aucune parcelle libre constructible. Le 0-opp est
**intrinsèque**, **pas un artefact** (toutes couches présentes, PLU propre 100 %, osm OK, doublon corrigé).

## 5. Décision

- **Gold différé** : Sainte-Rose **reste `absent`/non-gold** en config (aucun passage gold).
- **Data conservée en DB** : run + dédup conservés (6 287 parcelles + couches, doublon `safer` retiré),
  **aucun rollback recommandé** (backup pré-commune disponible si retour souhaité un jour).
- **Aucune mutation supplémentaire** : pas de re-cascade, pas de dédup générique, pas de nettoyage d'évaluations.
- **À reprendre plus tard** : arbitrage **produit / scoring** — valeur commerciale d'une commune à quasi-0
  opportunité ? Ajustement du scoring sur les communes à forts aléas / fort bâti ? Décision découplée du
  run technique (validé).

## 6. Communes au même statut « différé »

| Commune | INSEE | Motif |
|---|---|---|
| La Plaine-des-Palmistes | 97406 | 0 opportunité (scoring/métier) |
| Entre-Deux | 97403 | évaluée sans bâti (La Plaine-bis) |
| Les Trois-Bassins | 97423 | quasi-0 opportunité (1/5 314) |
| **Sainte-Rose** | **97419** | **quasi-0 opportunité (8/6 287, 0,1 %) ; volcan/aléas** |

> Bloquées PLU/GPU (catégorie distincte, à débloquer séparément) : Saint-Leu, Saint-André, Saint-Philippe.
