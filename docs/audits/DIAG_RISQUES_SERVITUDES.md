# Diagnostic — « Pièges et risques » (entrée parcelle / servitudes) — 21/08/2026

Diagnostic seul, aucune correction. Branche `audit/risques-servitudes`. Ne merge pas.

## Verdict court
**Ce n'est PAS une régression de fusion** (aucun kind n'a sauté, l'enrichissement SUP→effet marche). MAIS
tu as raison sur le fond : **la ligne affichée sur `97415000CW1076` est un FAUX POSITIF** — un
« Zonage d'assainissement » **collectif**, qui n'est pas une servitude et, en collectif, pas une contrainte.

## 1. Les 7 kinds sont-ils toujours interrogés ? → OUI, aucun n'a sauté
`servitudes.py:_KINDS` = 7 kinds, tous passés à la requête (`sl.kind = ANY(:kinds)`, ligne 106) et tous
**peuplés** en base : `trait_de_cote` 24 168 · `bruit_route` 1 004 · `sol_pollue` 513 · **`sup` 417** ·
`zonage_assainissement` 258 · `cinquante_pas` 163 · `znieff` 162.
- À la fusion M137-T : `peb` (bruit aérien) RETIRÉ de `_KINDS` → passé en NON_COUVERT car **0 ligne** en
  base (un couvert-vide = faux RAS) — **correct**. `znieff` AJOUTÉ. **SUP n'a pas bougé.**
- **Preuve que SUP marche** : sur une parcelle en PPR (`97414000CE0141`), l'endpoint rend bien
  « Servitude d'Utilité Publique → **Risques naturels (PPR) — prescriptions constructives** » + 2 ZNIEFF.

## 2. L'enrichissement SUP→effet (_SUP, _SOL_POLLUE) est-il appliqué ? → OUI (petit trou)
`_detail()` applique `_SUP` (SUP) et `_SOL_POLLUE` (sols). Prouvé (pm1 → PPR). **Trou de complétude** :
3 sous-types présents en base ne sont PAS dans `_SUP` → rendus bruts « SUP xxx » :
**`ac3`**, **`el10`**, **`pm2`** (les autres — ac1/ac2/ac4/pm1/pm3 — sont enrichis). Mineur, à mapper.

## 3. Le zonage d'assainissement doit-il figurer dans cette liste ? → NON — c'est LE défaut
- Ce n'est **pas une servitude** : c'est une info de **raccordement** (collectif vs ANC). La fiche a déjà
  un bloc `anc` dédié (M86-B) qui dit l'état d'assainissement proprement.
- Pire, pour le sous-type **`collectif`** (raccordé au tout-à-l'égout = cas FAVORABLE, **pas** une
  contrainte), le lister comme « servitude/contrainte dormante » est un **FAUX POSITIF** qui gonfle le
  compte. Répartition : `collectif` 174 / `anc` 84. **67 208 parcelles** portent un zonage collectif
  compté à tort comme servitude.
- C'est exactement ce qu'on voit sur `97415000CW1076` : sa **seule** couche intersectante est un
  `zonage_assainissement` **collectif** → l'outil affiche « 1 servitude » alors qu'il y en a **0**.

## 4. Test avant/après sur une parcelle à SUP
- `97415000CW1076` (celle du signalement) : **aucune SUP** en base — seule intersecte un
  `zonage_assainissement collectif`. La « 1 ligne » est donc **exacte au niveau donnée**, mais **fausse au
  niveau sens** (faux positif). Le « avant montrait des SUP » portait sur une AUTRE parcelle.
- `97414000CE0141` (en PPR) : **n=3** — PPR enrichi + 2 ZNIEFF. La chaîne SUP→effet est intacte.
- Front `O5Servitudes` (blocB.tsx:61) rend **tous** les items du endpoint, sans filtre → pas de régression
  front.

## Conclusion & piste de correction (à décider — non faite ici)
Rien n'est cassé côté SUP. Le bug réel : **`zonage_assainissement` n'a pas sa place dans les servitudes**.
Correctif proposé : le **retirer de `_KINDS`** (l'assainissement vit déjà dans le bloc `anc` de la fiche) —
ou, a minima, ne le garder que pour le sous-type **`anc`** (la vraie contrainte) et jamais `collectif`.
Bonus : ajouter **ac3 / el10 / pm2** à `_SUP`. Sur `97415000CW1076`, après correctif : **0 servitude**
(honnête), et le compte cesse d'être gonflé sur 67 208 parcelles.
