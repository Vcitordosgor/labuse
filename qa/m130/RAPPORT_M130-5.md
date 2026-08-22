# M130-5 — PDF projet : vrai dénominateur, étage 0 dit, parts complètes

Branche `feat/m130-pdf-projet`. Ne pas merger. PDF : `M130-5-projet-{P1..P4}.pdf`.
`git branch` = `feat/m130-pdf-projet` · `git log -1` = M130-4 (56ea2b17) au départ ·
`lsof -ti:8000` = **83266 (serveur dev actif, code M130-4)** — la vérification
ci-dessous **régénère les PDF en direct** (import Python frais), indépendante de
ce serveur ; il faudra le redémarrer pour voir le nouveau rendu au navigateur.

---

## A — Le total affiché est celui de la population servie

Nouveau `_cadrage_total` = cardinal de la **même population que `_run_cadrage`**
(donc `_q_v2_list`) sans la limite : mêmes filtres (sliver < 2 m², base étage 0
sauf filtre `tiers` explicite, cadrage). `_vivier_figeable` **n'est plus** le
dénominateur du PDF (il reste utilisé par `projet_compteur` / `projet_apercu`).
**État 3** est désormais réservé au **`None`** (échec réel de requête) ; un `0`
légitime n'y tombe plus.

| Projet | total (`_cadrage_total`) | n | État |
|---|---|---|---|
| **P1** | **285 781** | 60 | État 1 |
| **P2** | **839** | 60 | État 1 |
| **P3** | **10 725** | 60 | **État 1** (était État 3 en M130-4) |

**P3 est maintenant État 1.** Le total affiché = **10 725**, pas 10 846 : la
population de la liste (`_q_v2_list`) **exclut les slivers < 2 m²**
(`MIN_DISPLAY_SURFACE_M2`) — les 10 846 du rapport M130-4 étaient le compteur
carte brut, une **autre** population. 10 725 est le cardinal exact de l'ensemble
dont la shortlist est extraite (vérifié : LEFT JOIN s2 = INNER JOIN s2 = 10 725,
`s2` couvre 100 % du run).

Phrase P3 rendue **mot pour mot** :
> Liste plafonnée : 60 parcelles figées sur ~ 10 725 retenues par le cadrage (à
> ce jour). Les figées ont été SÉLECTIONNÉES par probabilité de mutation (critère
> interne du moteur) — un rang non visible ; elles sont présentées ici par ordre
> géographique. Élargir la shortlist ne supprime pas ce rang : seule une liste
> complète ou un tri explicite (surface) est neutre. **Cette sélection est
> intégralement composée de parcelles classées à l'étage 0 du moteur (résidus
> cadastraux, emprises non exploitables, zones fermées à l'urbanisation). Elles
> n'ont pas vocation à être instruites en l'état.**

**P1 / P2 : totaux inchangés** (285 781 / 839) — aucun mouvement (pour un cadrage
sans filtre `tiers`, `_cadrage_total` et `_vivier_figeable` comptent la même
population : hors étage 0 + sliver ; ici le sliver n'écarte rien).

---

## B — L'étage 0 est dit

Lisible sans jointure coûteuse : `projet_parcelles` → `dryrun_parcel_evaluations`
(même run) → `d.status IN ('exclue','faux_positif_probable')` (= `_ETAGE0_SQL`).
Compté par shortlist (`etage0_count`). Deux formulations (totalité / partie),
ajoutées à la **ligne d'état de la liste**.

| Projet | parcelles étage 0 / n | phrase déclenchée |
|---|---|---|
| **P1** | **0** / 60 | aucune |
| **P2** | **0** / 60 | aucune |
| **P3** | **60** / 60 | **totalité** (mot pour mot ci-dessus) |

L'étage 0 est formulé comme un **état de la donnée** (résidus cadastraux, emprises
non exploitables, zones fermées à l'urbanisation), **jamais** un rang/score.

---

## C — Parts multi-zones : somme et complément

`97422000BV2471` : parts affichées Nco ~ 50 % · Ua ~ 48 % (= 98 %). Les 2 points
manquants = une **troisième zone Uav sous le seuil d'affichage de 5 %** (mesuré :
Nco 50, Ua 48, **Uav 2**) — ni trou de géométrie, ni arrondi. Correctif C.2
appliqué : reliquat non muet.

Ligne rendue :
> Parcelle multi-zones : Nco (naturelle) ~ 50 % · Ua (urbaine) ~ 48 % · **autres
> zones ~ 2 %** — la SDP n'est pas chiffrée ; une partie constructible peut
> exister et reste à instruire.

**Somme = 50 + 48 + 2 = 100 %.** Règle générale : `reste = 100 − Σ parts
affichées` ; `reste ≥ 2` → « · autres zones ~ X % » ; `±1` = arrondi, rien.

---

## Vérifications exigées (récapitulatif)

- **P3** : État **1**, total **10 725**, phrase étage 0 « totalité » (mot pour mot §A). ✅
- **P1 / P2** : totaux **inchangés** (285 781 / 839). ✅
- **P1 / P2 étage 0** : **0** chacun → aucune phrase déclenchée. ✅
- **`97422000BV2471`** : parts somment à **100 %** (Nco 50 · Ua 48 · autres 2). ✅
- **Aucun rang / score / verdict réintroduit par B** : ✅ — les mots
  « probabilité de mutation / rang / verdict / score / classement » n'apparaissent
  QUE dans (a) la ligne d'état (divulgation exigée du rang caché) et (b) la
  mention « Aucun verdict, score ni classement ». La phrase étage 0 elle-même n'en
  porte aucun.

ruff : 0 erreur nouvelle (les I001 restantes = imports pré-existants décalés).
