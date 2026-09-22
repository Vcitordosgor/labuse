# RAPPORT M68 — PHASE 0 (diagnostic) : défilement bloqué de la fiche

Branche `feat/m68-scroll-fiche` (depuis `main` = `0e4ce2a0`, M61 mergé). Parcelle **97411000AK0043**
(Saint-Denis). Mesures au runtime (Playwright, dev :5173), pas de supposition. **STOP** après diagnostic.

## 1. Conteneur de défilement + hauteurs mesurées

Structure de la fiche (`Fiche.tsx`) :
```
<aside class="fiche-v6 … flex h-full flex-col">           (1373)  — h = hauteur viewport
  {événement} {module}                                    (shrink-0)
  <div style="padding:14px 14px 0; flex-shrink:0">        (1405)  — WRAPPER FIXE (ne rétrécit jamais)
     .head (en-tête)  +  CTA  +  [data-verdict-card]      (1490-1640)  ← LE BLOC ANALYSE EST ICI
  </div>
  <div class="… min-h-0 flex-1 overflow-y-auto …">        (1709)  — CONTENEUR DE SCROLL (flex-1)
     IA · tiroirs · actions · exports · [data-disclaimer-legal]
  </div>
</aside>
```

Le **conteneur de défilement** = `div.min-h-0.flex-1.overflow-y-auto.overflow-x-clip` (Fiche.tsx:1709).
Son `overflow-y` est bien `auto` et **n'est jamais perdu**. Hauteurs calculées (largeur 1440) :

| Viewport | bloc Analyse | wrapper fixe (1405) | conteneur scroll (client) | scrollHeight | mention légale |
|---|---|---|---|---|---|
| 900 | absent | 278 px | **566 px** | 973 | atteignable (scroll) |
| 900 | **déplié** | **567 px** | **277 px** | 973 | atteignable (scroll forcé) |
| 900 | **replié** | 285 px | **559 px** | 973 | **visible sans scroll** |
| 768 | déplié | 567 px | **145 px** | 973 | sliver |
| 700 | déplié | 567 px | **77 px** | 973 | sliver |
| 640 | déplié | 567 px | **20 px** | 973 | inutilisable |

## 2. Cause (mesurée)

**Ce n'est PAS** un overflow perdu, ni une hauteur fixe sur le conteneur de scroll, ni un position/sticky.
C'est une **partition de mise en page** : le **bloc Analyse (CTA + `data-verdict-card`) est rendu DANS le
wrapper `flex-shrink:0` du haut (Fiche.tsx:1405), EN DEHORS du conteneur de défilement** (mesuré :
`verdictCard.dansScroll = false`).

Déplié, le bloc Analyse gonfle ce wrapper fixe (278 → **567 px**). Comme le wrapper a `flex-shrink:0`,
il ne rend jamais l'espace ; le conteneur de scroll (`flex-1`) est **affamé** : 566 → 277 px à 900,
puis **145 / 77 / 20 px** à 768 / 700 / 640. Le contenu (973 px) est comprimé dans un hublot minuscule,
positionné SOUS la grande carte. Comme la carte (le gros du visible) n'est pas dans une zone scrollable,
la molette n'y fait rien → **ressenti « bloqué »**. Sous ~623 px de haut, le wrapper (567) dépasserait
l'`aside` (qui n'a aucun scroll propre) → le bas serait carrément **clippé, inatteignable**.

## 3. Le défaut existait-il avant M61 ?

**OUI — il PRÉCÈDE M61.** Au commit `c1155fa2` (avant M61), le `data-verdict-card` (l.1477) était déjà
dans le même wrapper `flex-shrink:0` (l.1394), hors du conteneur de scroll (l.1684). M61 **n'a pas
introduit** le blocage. Au contraire, la transformation en tiroir de M61 le **mitige** : replié, le
wrapper redescend à 285 px et le scroll est rétabli. Avant M61 la carte était toujours dépliée → le
blocage survenait dès que le verdict était affiché (depuis M55-O, quand la carte a absorbé P + motifs +
renouvellement + éligibilité).

## 4. Le défaut se produit-il quand le bloc est replié ?

**NON.** Replié, le wrapper fixe = 285 px, le conteneur de scroll = 559 px (@900), et la **mention légale
est directement visible** sans défiler. Le blocage est **DÉPLIÉ-seulement**.

## Constat inattendu sur PHASE 1(b) — repli déjà correct

La PHASE 1(b) affirme que, replié, « le sous-bloc VERDICT LABUSE reste visible (verdict, ratio, jauge,
Pourquoi ce score) ». **Ce n'est PAS reproductible sur le code mergé (main + M61), parcelle AK0043 :**
replié, le bloc mesure **49 px** et ne contient QUE l'en-tête — mesuré `hasBadge:false`, `hasPourquoi:false`,
`hasReglette:false`, texte = « Analyse LABUSE · Écartée · › » (capture `phase0-replie.png`). Le repli montre
donc **déjà** « Analyse LABUSE + le verdict en une ligne + le chevron », exactement le comportement attendu.
→ L'observation de la PHASE 1(b) reflète vraisemblablement un build **antérieur à M61**. **À arbitrer** :
soit (b) est sans objet, soit préciser un cas non couvert.

## Correctif recommandé (PHASE 1a, à valider en arbitrage)

**Déplacer le bloc Analyse (CTA + `data-verdict-card`) DANS le conteneur de défilement** (Fiche.tsx:1709),
en tête de celui-ci — au lieu du wrapper `flex-shrink:0`. Le bloc Analyse défile alors avec le reste ;
le conteneur de scroll retrouve toute la hauteur `flex-1` quel que soit l'état (absent / déplié / replié /
synthèse ouverte / n'importe quel tiroir). Seul l'en-tête `.head` (identité + 4 chiffres) reste éventuellement
fixe, ou tout devient scrollable. Alternative moins sûre (déconseillée) : retirer `flex-shrink:0` du wrapper
— mais alors la carte se comprimerait au lieu de scroller. Recette (a) = descendre jusqu'à la mention légale
dans les 4 états, sur AK0043 + les 4 parcelles M55-O.

## Captures
`reports/m68/captures/` : `phase0-deplie.png`, `phase0-replie.png` (en-tête seul, 49 px),
`phase0-fiche-deplie-768.png` (la carte remplit le visible, scroll comprimé dessous).

---

# PHASE 1 (après arbitrage Vic)

Arbitrage : (a) correctif recommandé retenu ; (b) sans objet (ne pas toucher au repli) ; ajouter à la
recette la mesure de la hauteur utile du scroll aux 4 viewports (déplié) ; garder (c) retrait du résidu
`.band` de `docs/DA-FICHE-v6.html`.

## (a) Défilement rétabli
`Fiche.tsx` : **seul l'en-tête `.head` (identité + 4 chiffres) reste fixe** ; tout le reste — bloc Analyse
(CTA + `data-verdict-card`), bannière RNU, signaux, tiroirs, actions, exports, mention légale — vit
désormais **dans le conteneur `overflow-y-auto flex-1`**. Réalisé par 3 édits de frontières (bilan des
`<div>` équilibré, tsc/build verts) : fermeture du wrapper fixe juste après l'en-tête, ouverture du
conteneur de défilement à sa suite (bloc Analyse enveloppé d'un `<div>` non-flex pour préserver son
espacement interne), fusion de l'ancien conteneur. `verdictCard.dansScroll = true` (mesuré).

**Recette — hauteur utile du conteneur de scroll (bloc Analyse DÉPLIÉ), AK0043 :**

| Viewport | AVANT (PHASE 0) | APRÈS (PHASE 1) | mention légale atteignable |
|---|---|---|---|
| 900 | 277 px | **616 px** | oui |
| 768 | 145 px | **484 px** | oui |
| 700 | 77 px | **416 px** | oui |
| 640 | **20 px** | **356 px** | oui |

Aucune hauteur ne tombe sous un seuil empêchant d'atteindre la mention légale (min = 356 px @640).

**Recette — mention légale atteignable dans les 4 états × 5 parcelles** (AK0043 + les 4 M55-O
97408000AP1647, 97409000AR1260, 97411000HM0273, 97407000AI1821), viewport 768 :
absent / déplié / replié / synthèse ouverte → **visible = true partout**, **console 0 erreur** (mesuré).

## (b) Repli — non touché
Conformément à l'arbitrage, aucun changement au repli. Vérifié inchangé : replié = « Analyse LABUSE ·
Écartée · › » sur une ligne (`phase1-bloc-replie.png`).

## (c) Résidu `.band` retiré
`docs/DA-FICHE-v6.html` : mockup `.band` « Marché peu actif à Sainte-Marie » supprimé, règles CSS `.band`
retirées, tokens `--amber-band/--amber-txt/--amber-ico` retirés (0 autre usage ; `--amber`/`--amber-bg`
conservés). La maquette suit l'app (composant retiré en M65 P1).

## Garde-fous PHASE 1
tsc 0 · vitest 32/32 · build vert · console 0 erreur (5 parcelles) · recette scroll ci-dessus.

## Captures PHASE 1
`reports/m68/captures/` : `phase1-bas-fiche-atteint-768.png` (en-tête fixe + scroll jusqu'à la mention
légale, exports visibles), `phase1-bloc-replie.png` (bloc replié une ligne, inchangé).

**Commits** : PHASE 0 = `633847a7` (diagnostic). PHASE 1 = ce commit. **NON mergé.**
