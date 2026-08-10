# RAPPORT M55-D — PHASE 2 (implémentation) : avancement

Branche `feat/m55-d-filtres`. Validations Vic reçues : **Q1** « Terrain nu/Bâti/Les deux » =
**pré-réglage dans Filtres** (pas un MODE) · **Q2** **étendre `#f=` à tous les champs** · **Q3**
filtres rapides header = **Verdict + Surface + SDP** · **Q4** (analyseLabuse dans l'URL) = oui (suit Q2).

Cible confirmée : **Mode d'analyse** = uniquement `analyseLabuse` (mode de lecture) + curseur Mode B
(seul recalcul) · **Filtres** = panneau unique dédupliqué + rapides header (Verdict/Surface/SDP) +
badge N · pré-réglages visibles · Mes vues capture tri+mode.

---

## Livré (stage 1) — persistance complète ✅ (commit 3983cf47)

`filtersToHash`/`filtersFromHash` couvrent **tous** les champs de `Filters` (avant : 11/~35).
Clés historiques conservées (rétro-compat lecture). Comme « Mes vues » et les veilles passent par
`filtersToHash`, elles capturent maintenant l'intégralité — **findings 1 & 3 de la phase 1 corrigés**
(fin du session-only). Test `filters.test.ts` : round-trip de tous les champs + `al` défaut true sur
vieux lien + clés historiques (3/3). tsc 0, vitest 29/29, build vert. **Q2 + Q4 satisfaits.**

---

## Reste à faire (stage 2 — restructuration UI) — plan turnkey

Surface CRITIQUE (les filtres pilotent carte + liste + compteurs + exports) et COUPLÉE (le panneau
`FiltreLabuse` vit dans `ResultsSection`, affiché si `verdict`). Découpage précis, à exécuter d'un
bloc et vérifier (compte inchangé + URL compat + mobile) :

1. **`ModeAnalyse` (nouveau, header, à gauche de « Filtres »)** — déplacer depuis `FiltreLabuse` :
   - l'interrupteur `analyseLabuse` (FiltreLabuse L302-308) ;
   - le `ModeBCurseur` (L102-124) dans un popover attaché + phrase d'aide 1 ligne + état
     « ça recalcule » (le seul vrai recalcul).
2. **Header « Filtres (N) »** — remplacer le popover `AddFilter` : garder SEULEMENT les rapides
   (Verdict/tiers, Surface, SDP) + bouton « Tous les filtres → » qui révèle le panneau
   (`setVerdict(true)` + scroll). Retirer du header les critères dupliqués (scoreMin, evenement,
   veille, horsCopro, flags) → ils vivent dans le panneau. **Badge N** = `countActiveFilters(filters)`
   (nouveau helper `lib/filters.ts` : compte tous les champs actifs SAUF `analyseLabuse`/mode).
3. **`FiltreLabuse` (le panneau unique B)** — retirer l'interrupteur + `ModeBCurseur` (montés en
   header) ; garder le compteur-lecture. Marquer les presets/`ProfilSelecteur` « pré-réglage » (déjà
   quasi le cas : posent des critères visibles, défaisables). « Réinitialiser » : séparer
   visuellement filtres (TRI) vs mode (bouton/section distincts ; `resetFilters` ne touche pas le mode
   OU le dit).
4. **`MesVues`** — libellé « capture les filtres ET le mode » (désormais vrai après stage 1).
5. **Dédup** : chaque champ (surface, sdp, flags, tiers, veille) n'a plus qu'UN contrôle (panneau ;
   le header n'expose que les 3 rapides).
6. **Mobile** : le panneau unique reste utilisable (vérif + capture).

### Vérifications de non-régression (obligatoires stage 2)
- Un critère = un seul endroit (preuve : surface introuvable à deux endroits).
- Poser mode + 3 filtres + un pré-réglage → badge juste, reset différencié, URL restituant tout.
- Une URL `#f=` d'AVANT la refonte s'ouvre correctement (déjà garanti par stage 1 + test).
- **Compte /filtre identique** pour un même `filters` avant/après (aucune sémantique changée —
  refonte UI pure).
- Captures : header, panneau, popover mode, pré-réglage appliqué (critères visibles), mobile.
- tsc 0, build vert, vitest vert.

**État : stage 1 (fondation) livré et testé. Stage 2 = restructuration UI, prête à exécuter selon
le plan ci-dessus — surface critique, à faire d'un bloc avec les vérifs de non-régression.**

## Périmètre
Front seul, `filters` unique (acquis M55-C), aucun changement moteur. CC ne merge jamais.
