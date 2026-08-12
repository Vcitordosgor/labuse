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

**STOP — en attente d'arbitrage avant PHASE 1.**
