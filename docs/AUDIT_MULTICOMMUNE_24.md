# Audit recheck complet multi-commune — 24 communes

> Audit **lecture seule** (aucun code/DB modifié ; `/enrichment` intercepté → 0 endpoint d'écriture
> déclenché). Réalisé le 2026-06-28 sur `main = 060dbeb` (sélecteur multi-commune Phase #1).
> DB métier vérifiée inchangée avant/après (`431663 / 9103 / enrichment 27`).

## Verdict : ⚠️ ATTENTION — feature OK sur 23/24, **1 bug bloquant (P1)** à corriger

Le sélecteur multi-commune fonctionne **proprement sur 23 des 24 communes** : sélection, badge,
stats cohérentes, carte recalée, **anti-stale parfait** (aucune donnée d'une autre commune), Radar
sidebar + calque cohérents, fiche ouvrable, **0 erreur console**, bascules < 5 s. **MAIS** la
bascule vers **Saint-Philippe** (seule commune **non évaluée** : 4162 parcelles, 0 évaluation)
**lève une exception et bloque ensuite tout le sélecteur** (deadlock). Fix trivial identifié.

---

## 1. Méthode

- Playwright headless, navigation réelle via le menu déroulant pour **les 24 communes**.
- Par commune : bascule (chrono), badge, stats (KPI vs DB), **anti-stale** (1ᵉʳ idu doit être
  préfixé par l'INSEE de la commune), `FEATURES`, Radar sidebar (count + 1ᵉʳ idu), calque Radar,
  fiche ouvrable, erreurs console (hors tuiles externes + hors `/enrichment` aborté).
- Tests ciblés : Salazie en isolation, mécanisme du deadlock, **mobile 390 px**.
- `/enrichment` (GET qui écrit, bug connu #4) **aborté** dans le navigateur de test.

## 2. Résultats — 24 communes

**22/24 ✅ au vert strict** (anti-stale + fiche + 0 console). Saint-Philippe ❌ (bug ci-dessous),
Salazie ❌ **uniquement victime du deadlock** (OK confirmée en isolation : 7032 parcelles).

| Commune | Badge | Attendu | Feat | Anti-stale | Radar | Calque | Fiche | Console | Bascule |
|---|---|---|---|---|---|---|---|---|---|
| Saint-Paul | GOLD | 51129 | 51005 | ✅ | 8 | 153 | ✅ | 0 | — |
| Le Tampon | GOLD | 42756 | 42711 | ✅ | 8 | 160 | ✅ | 0 | 4,2 s |
| Saint-Pierre | GOLD | 42425 | 42304 | ✅ | 8 | 160 | ✅ | 0 | 4,1 s |
| Saint-Denis | GOLD | 38138 | 38025 | ✅ | 8 | 132 | ✅ | 0 | 4,9 s |
| Saint-Louis | GOLD | 29241 | 29187 | ✅ | 8 | 150 | ✅ | 0 | 3,1 s |
| Saint-Joseph | GOLD | 28959 | 28931 | ✅ | 8 | 160 | ✅ | 0 | 3,6 s |
| Saint-Leu | **NON ÉVALUÉE** | 22959 | 22899 | ✅ | 8 | 160 | ✅ | 0 | 2,7 s |
| Saint-André | GOLD | 22600 | 22571 | ✅ | 8 | 150 | ✅ | 0 | 2,6 s |
| Saint-Benoît | GOLD | 21671 | 21651 | ✅ | 8 | 160 | ✅ | 0 | 3,5 s |
| Sainte-Marie | GOLD | 16746 | 16713 | ✅ | 8 | 160 | ✅ | 0 | 1,8 s |
| La Possession | GOLD | 13338 | 13314 | ✅ | 8 | 140 | ✅ | 0 | 2,6 s |
| Petite-Île | GOLD | 13137 | 13117 | ✅ | 8 | 132 | ✅ | 0 | 1,4 s |
| Sainte-Suzanne | GOLD | 12527 | 12502 | ✅ | 8 | 111 | ✅ | 0 | 1,4 s |
| Le Port | GOLD | 10195 | 10112 | ✅ | 8 | 160 | ✅ | 0 | 1,3 s |
| L'Étang-Salé | GOLD | 9070 | 9054 | ✅ | 8 | 76 | ✅ | 0 | 3,1 s |
| Les Avirons | GOLD | 8611 | 8595 | ✅ | 8 | 100 | ✅ | 0 | 1,2 s |
| Salazie | PARTIELLE | 7035 | 7032¹ | ✅¹ | — | — | ✅¹ | 0¹ | 1,0 s¹ |
| Cilaos | PARTIELLE | 6560 | 6553 | ✅ | 8 | 102 | ✅ | 0 | 0,9 s |
| Sainte-Rose | PARTIELLE | 6287 | 6283 | ✅ | 8 | 131 | ✅ | 0 | 1,1 s |
| La Plaine-des-Palmistes | PARTIELLE | 6450 | 6448 | ✅ | 8 | 87 | ✅ | 0 | 0,9 s |
| Entre-Deux | GOLD | 6312 | 6307 | ✅ | 7 | 59 | ✅ | 0 | 1,0 s |
| Bras-Panon | GOLD | 6041 | 6033 | ✅ | 8 | 154 | ✅ | 0 | 0,9 s |
| Les Trois-Bassins | PARTIELLE | 5314 | 5306 | ✅ | 8 | 36 | ✅ | 0 | 0,9 s |
| **Saint-Philippe** | **NON ÉVALUÉE** | 4162 | 4160 | ✅ | **0** | **0** | ✅ | **1** ❌ | 0,6 s |

¹ Salazie : mesuré **en isolation** (le run séquentiel l'a vue bloquée par le deadlock de Saint-Philippe).

**Anti-stale : 24/24 ✅** — chaque commune n'affiche QUE ses parcelles (idu préfixé par son INSEE).
Aucun résidu d'une commune précédente, jamais.

## 3. 🔴 Bug bloquant trouvé — BUG-MC1 (P1, régression Phase #1)

**Titre** : bascule vers une commune **entièrement non évaluée** → exception Leaflet + **deadlock du sélecteur**.

- **Repro** : sélectionner **Saint-Philippe** (4162 parcelles, **0 évaluée**) → puis tenter une autre commune.
- **Attendu** : carte vide propre, puis bascule suivante normale.
- **Observé** : `PAGEERR: Bounds are not valid.` lors de la bascule, puis **toute bascule suivante est
  bloquée** (vérifié : après Saint-Philippe, clic sur Cilaos → reste sur Saint-Philippe, `COMMUNE_BUSY=true`).
- **Cause** : les parcelles de Saint-Philippe sont **non évaluées** (status null) → le filtre de statut
  les masque toutes → la couche carte est **vide** → `layer.getBounds()` est **invalide** →
  `map.fitBounds(...)` **lève une exception**. Comme `switchCommune()` pose `COMMUNE_BUSY = true`
  **sans `try/finally`**, l'exception laisse le verrou **bloqué** → les bascules suivantes
  court-circuitent (`if (COMMUNE_BUSY) return`).
- **Fichier** : `src/labuse/api/web/app.js` — `switchCommune()` (garde `fitBounds`) + le `main()` de boot
  a le même motif `fitBounds` latent (ligne ~2856, inoffensif au boot car défaut = Saint-Paul évaluée).
- **Sévérité** : **P1** — deadlock UX dur (1/24 communes le déclenche, mais bloque ensuite **tout** le sélecteur).
- **Fix (trivial, 2 points, sans risque)** :
  1. Garder le `fitBounds` : `const bb = layer && layer.getBounds(); if (map && bb && bb.isValid()) map.fitBounds(bb, {maxZoom:15});`
  2. Envelopper le corps de `switchCommune()` dans un `try { … } finally { COMMUNE_BUSY = false; }` (le verrou se libère TOUJOURS).
  3. (Cohérence) Appliquer la même garde `.isValid()` au `fitBounds` du boot `main()`.

## 4. Findings secondaires (hors périmètre frontend / hors mission)

- **Saint-Leu — badge trompeur** : classée `partiel_non_evalue` / badge **« Non évaluée »** par
  `/communes/status`, **mais la DB contient 22 959 évaluations + 976 opportunités**. Le frontend
  affiche fidèlement le `label` backend — c'est la **classification/wording backend** qui est
  incohérente (« non évaluée » alors que la commune EST évaluée). À corriger côté `/communes/status`
  (lié aux bugs exclus #14/#15, hors mission).
- **Carte des communes non évaluées** : Saint-Philippe affiche une **carte vide** (« vos filtres
  masquent toutes les parcelles ») car il n'existe **pas de filtre « non évaluée »** pour montrer les
  parcelles sans statut. Lié au design des filtres + à l'état data, pas au multi-commune.
- **Mobile (390 px)** : le sélecteur vit dans l'en-tête/sidebar, **accessible via l'onglet « Liste »**
  (la vue par défaut mobile est « Carte »). Fonctionne : menu **24 options**, largeur 356 px (non
  rogné), bascule OK, **0 overflow, 0 pageerror**. UX mineure : pas de sélecteur sur la vue Carte mobile.

## 5. Performance de bascule

Toutes les bascules **< 5 s** (click → carte interactive `DATA_READY`). Max : **Saint-Denis 4,9 s**,
Le Tampon 4,2 s, Saint-Pierre 4,1 s (les plus grosses). Petites communes ~0,9–1,5 s. **0 bascule > 8 s.**
Le Radar sidebar + calque se peuplent en **asynchrone** ensuite (calcul à froid ~4,7 s, déjà documenté
dans le plan perf). Acceptable.

## 6. Cohérence des données

- **Stats** : le KPI « parcelles » (depuis `/stats`) = `parcelles_en_base` **exactement** (ex.
  Saint-Philippe 4162 = 4162). Le compte `FEATURES` (geojson) est **~0,2–0,3 % en dessous** partout
  (parcelles sans géométrie valide, non rendues) — **cohérent**, pas un bug.
- **Badges** : 17 GOLD + 5 PARTIELLE + 2 NON ÉVALUÉE — conformes à `/communes/status` (sous réserve
  du finding Saint-Leu §4).

## 7. DB inchangée

Avant/après : `parcels=431 663`, `opportunités=9 103`, `parcel_enrichment=27` (intact). Aucune
écriture (le seul GET qui écrit, `/enrichment`, a été aborté en QA).

## 8. Recommandation

1. **Corriger BUG-MC1** (P1) — fix trivial 2 lignes (`fitBounds .isValid()` + `try/finally` sur
   `COMMUNE_BUSY`). À faire **avant de considérer le multi-commune « livré »** : c'est un deadlock dur.
2. Ensuite, enchaîner la **correction des bugs safe** (2, 4, 6, 7, 8, 10, 11, 13) comme prévu.
3. Plus tard / backend (hors frontend) : corriger la **classification Saint-Leu** dans
   `/communes/status` ; envisager un **filtre « non évaluée »** ou un message dédié pour les communes
   non évaluées ; éventuel sélecteur de commune sur la **vue Carte mobile**.

> **Verdict : ATTENTION.** Le multi-commune est à **23/24** ; 1 bug bloquant (deadlock Saint-Philippe)
> reste à corriger, fix trivial identifié. Anti-stale parfait, perf OK, mobile OK, DB intacte.
