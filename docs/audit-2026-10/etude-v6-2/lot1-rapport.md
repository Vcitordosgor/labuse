# ÉTUDE V6-2 — Lot 1 : le bug des surfaces (T1 = 9 m²)

## Le défaut constaté
« Hypothèses modifiables » pouvait afficher **T1 = 9 m²** au lieu de 30, et cette valeur se
**propageait** : l'étape 3 et le récapitulatif lisaient l'état VIVANT de l'éditeur (`surfOf`/`varOf`),
pas les défauts. Reproduction : éditer la surface T1 → 9 dans le résultat, puis « Modifier le
programme » et changer la quantité → l'étape 3 affichait **60 T1 = 540 m²** (60 × 9), la saisie
de l'éditeur ayant FUITÉ et PERSISTÉ au retour en étape 3 (le composant ne se remonte pas sur les
mêmes parcelles).

## La cause
1. **Étape 3 / récap lisaient l'éditeur.** `surfaceProg/surfaceVar/surfaceInt` étaient calculés avec
   `surfOf(t)`/`varOf(t)` — donc la surface ÉDITÉE, pas la surface par défaut. Avant tout calcul,
   l'étape 3 doit toujours montrer les défauts.
2. **Pas de remise à zéro au retour.** « Modifier le programme » ne réinitialisait pas l'état `hyp`
   de l'éditeur → une surface bricolée (9) survivait au retour en étape 3.
3. **Le résultat ne lisait pas sa propre source.** « Votre demande » était calculé côté client, pas
   depuis le payload analysé (la vraie source du PDF).

## Le correctif (`frontend/src/components/outils/EtudeV6.tsx` + `api.ts` + `service.py`)
- **Défauts garantis** : `SURF` reste l'unique source — T1 30/6, T2 56/9, T3 70/12, T4 80/14.
  L'étape 3 et le récap calculent désormais avec `SURF[t].area`/`SURF[t].varangue` (plus jamais
  l'éditeur) → avant calcul, toujours les défauts.
- **Remise à zéro** : `modifierProgramme()` = `resetHyp()` (vide l'éditeur) + `analyse.reset()`.
  Les deux boutons « Modifier le programme » (collectif + lotissement) l'appellent → aucune fuite.
- **Source unique dans le résultat** : « Votre demande » lit le PAYLOAD analysé —
  `resultat.programme_saisi.demande` × `resultat.hypotheses.surfaces` / `.varangues`
  (défauts `SURF` en secours). C'est la même source que le PDF (`corpsBody()` unique).
- **Le back renvoie les varangues** : `service.py` échoe `hypotheses.varangues` dans le payload
  collectif (les surfaces y étaient déjà), pour que le résultat et le PDF lisent la même varangue.
- **Types** : `varangues?: Record<string, number>` ajouté à `EtudeIn.hypotheses` et
  `EtudePayload.hypotheses` (`api.ts`).

## Preuve
- **Flux neuf 10 T1** : étape 3 ET « Votre demande » = **300,0 m² · dont 60,0 varangues ·
  240,0 intérieur · 10×T1** (capture `captures/lot1-apres-10T1-300.png`).
- **Pas de fuite** : éditer T1 → 9 (sans recalculer), « Modifier le programme », remettre 60 T1 →
  l'étape 3 affiche **1 800,0 m²** (60 × 30), plus 540 (capture
  `captures/lot1-apres-modifier-60T1-1800.png`).
- **Le back renvoie bien** `varangues {T1:6}` dans le payload (vérifié par `curl`).
- Édition sous le minimum (T1 → 9 m²) : le moteur borne au module minimum (20 m²) et le résultat
  affiche la surface RÉALISÉE (200 pour 10 T1), identique au PDF — honnête, pas un faux 90.

## Test unitaire
`EtudeV6.test.tsx` (Lot 1) — deux gardes :
1. « Votre demande » lit les surfaces du payload : **10 T1 = 300 / 60 varangues / 240 intérieur**.
2. **La surface éditée ne FUIT PAS** : T1 bricolé à 9 puis « Modifier le programme » → l'étape 3
   repasse aux défauts (**300**, jamais **90**).

## Vérifié
- **tsc 0 · vitest 290/290** (EtudeV6 12/12).
- **pytest implantation** : 158 passed, 2 failed = `test_route_*` **pré-existants et environnementaux**
  (DB de test vide → « parcelles introuvables » à `terrain.charger`, avant tout payload ; sans rapport
  avec le Lot 1).
- **chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP** (API servie sur 8830).
