# Radar Mutation — Plan perf « chargement froid » de la liste `/mutation`

> Analyse sérieuse, **lecture seule**, sans migration. Rédigé le **2026-06-27** (Phase 2E).
> Mesures réelles sur la base de prod (Saint-Paul, 51 129 parcelles, `cascade_results` 8,99 M).
> Prototypes **non commités** (benchmark/EXPLAIN uniquement). Aucune écriture DB.

## TL;DR — recommandation

| # | Option | Froid | Top-8 | Risque | Statut |
|---|---|---|---|---|---|
| 1 | **Cache mémoire TTL** | 4,7 s (1er) puis **~0–9 ms** | identique | très faible | ✅ **fait (2D)** |
| 2 | Réécriture SQL **une passe** | **~1,2 s** (×3,9) | change (ex-æquo) | moyen | prototypé, **propose 2F** |
| 3 | **Départage déterministe** | — | change (ex-æquo) | moyen | à coupler avec #2 |
| 4 | **Index** `cascade_results` | **~0,5–1 s** (est.) | identique | DDL (GO séparé) | recommandé hors-nuit |
| 5 | **Matérialisation** scores | instant, multi-niveaux | nouveau pipeline | élevé (table+refresh) | vision long terme |

> **Recommandation** : garder le **cache (#1)** comme socle (déjà en place, gain ×1000 sur le cas
> courant). Pour le **froid**, le meilleur couple **court terme** est **#2 + #3** (une passe +
> départage) : **~1,2 s et reproductible**, **sans DDL** — mais il **change le top-8 actuel**
> (départage des ex-æquo à 100), donc **décision produit explicite requise**. Le meilleur couple
> **structurel** est **#4 (index)** : froid ~0,5–1 s **sans changer le classement**, mais c'est une
> **migration** (GO DB séparé). À éviter pour l'instant : **#5** (gros chantier).

---

## Diagnostic (rappel mesuré, Phase 2D + 2E)

`top_for_commune(Saint-Paul, limit=8, pool=200)` ≈ **4,7 s**, dont **~90 % dans la présélection
SQL**. `EXPLAIN ANALYZE` : **4 × `Parallel Seq Scan` sur `cascade_results`** (un par couche
`zon/pot/dvf/rsq`, en `DISTINCT ON`) + tris `external merge` sur disque. Cause : `cascade_results`
n'a qu'un index `(parcel_id)`, **pas d'index `layer_name`** ⇒ chaque couche = balayage complet des
8,99 M lignes. Le moteur de score lui-même est **instantané** (le coût est la SÉLECTION).

---

## Option 1 — Cache mémoire TTL **(implémenté, Phase 2D)**

- **Quoi** : mémorise le résultat exact de `top_for_commune` (clé `commune/niveau/min_score/limit`,
  TTL 300 s, lock, plafond 256). En mémoire process, **rien en DB**.
- **Gain mesuré** : 1er appel 4,7 s (inchangé) → suivants **~0–9 ms** (×~1000). Top-8 **identique**.
- **Coût/risque** : nul côté DB ; péremption ≤ 5 min (acceptable, données stables hors re-cascade) ;
  ne réduit PAS le tout premier appel (à froid) — c'est le seul angle mort, traité par les options
  suivantes.

## Option 2 — Réécriture SQL en **une seule passe** (prototypé, non commité)

- **Quoi** : remplacer les 4 CTE `DISTINCT ON` par **une passe** sur `cascade_results` (filtrée
  commune + 4 couches), puis **pivot** par `FILTER (WHERE layer_name=…)`.
- **Gain mesuré** : **~1,2 s** (min sur 3) contre 4,7 s ⇒ **×3,9** à froid. Aucune écriture, aucun
  index.
- **Risque** : **change le top-8 actuel**. La cause n'est pas une erreur de formule (prescore
  identique sur les candidats communs) mais le **`LIMIT` parmi de nombreux ex-æquo à 100** : sans
  départage, l'ordre des égalités est arbitraire. → à coupler avec l'option 3.

## Option 3 — Départage déterministe (`ORDER BY prescore DESC, p.id`)

- **Quoi** : ajouter une clé de tri stable pour rendre la sélection **reproductible**.
- **Effet** : top-8 **stable** d'un appel à l'autre et d'une version à l'autre. Mesuré avec #2 :
  TOP-8 = `AB0690, AT0737, AY0395, CW0284, CZ1202, DK1002, DM0031, DM0890` (5/8 communs avec
  l'actuel ; les 3 différents sont **aussi des prioritaire à 100** — pur effet de départage).
- **Risque** : change le top-8 **livré aujourd'hui** (même s'il est plus sain). ⇒ **décision
  produit** : assumer un top reproductible. **Recommandé**, couplé à #2.

## Option 4 — Index `cascade_results(parcel_id, layer_name, evaluated_at DESC)` **(DDL — GO séparé)**

- **Quoi** : index couvrant pour transformer les 4 `Seq Scan` en parcours d'index ciblés.
- **Gain estimé** : froid **~0,5–1 s** (le coût retombe sur la CTE `le` ~0,5 s + bâti ~0,55 s),
  **sans changer la formule NI le top-8**. C'est le **meilleur levier structurel**.
- **Coût/risque** : c'est une **migration** (interdite cette nuit) — disque supplémentaire (ordre
  de grandeur ~100–300 Mo) + léger surcoût d'écriture sur l'ingestion `cascade_results`. Risque
  fonctionnel faible (index additif), mais **nécessite un GO DB explicite**.

## Option 5 — Matérialisation des scores (table dédiée) **(vision, GO séparé)**

- **Quoi** : précalculer `score_mutation/niveau/confiance` par parcelle dans une table, rafraîchie
  après chaque cascade.
- **Gain** : listes **instantanées** même à froid, **vrai filtrage multi-niveaux** (y compris
  « à surveiller », aujourd'hui absent du top car le pool ne remonte que le haut du panier).
- **Coût/risque** : **élevé** — nouvelle table + pipeline de refresh + gestion de la péremption +
  invalidation. Change l'architecture. **Hors mission sans risque DB.**

---

## Coût / gain / risque — synthèse

| Option | Effort | Gain froid | Change top-8 | Touche la DB |
|---|---|---|---|---|
| 1 Cache (fait) | — | 0 (mais ×1000 répété) | non | non |
| 2 Une passe | faible (SQL) | ×3,9 | oui (ex-æquo) | non |
| 3 Départage | trivial | — | oui (ex-æquo) | non |
| 4 Index | faible (DDL) | ×5–9 (est.) | **non** | **oui (migration)** |
| 5 Matérialisation | élevé | ×∞ (précalculé) | non | **oui (table)** |

## Recommandation finale

1. **Maintenant (sans risque)** : le cache (#1) reste le socle. Si l'on veut attaquer le froid sans
   DDL, implémenter **#2 + #3** en Phase 2F — **après décision produit** d'assumer un top
   reproductible (le top-8 change parmi les ex-æquo à 100, tous légitimement « prioritaire »).
2. **Quand un GO DB est possible** : l'**index #4** est le meilleur compromis (froid ~0,5–1 s,
   classement inchangé). À privilégier sur #5 tant que le multi-niveaux n'est pas un besoin ferme.
3. **Plus tard** : #5 (matérialisation) seulement si l'on veut des listes instantanées multi-niveaux
   à l'échelle des 24 communes.
