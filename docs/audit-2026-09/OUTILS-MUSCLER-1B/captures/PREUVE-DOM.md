# OUTILS-MUSCLER-1B — preuve d'écran (DOM mesuré, app réelle, base labuse)

Les captures PNG n'ont pu être produites : l'outil de capture Playwright expire
systématiquement (timeout 5 s côté MCP, avant l'écriture du fichier) sur cet écran —
le rendu WebGL de la carte n'est pas en cause (masquer le canvas ne débloque pas).
Vic ayant l'app sous les yeux en recette, les six points sont prouvés ci-dessous par
mesure du DOM rendu (`getBoundingClientRect` + présence/absence de sélecteurs).

## Avant (code d'origine, `Successions.tsx` @ b2fca207)
- Menu Outils / titre panneau / fil d'Ariane : **« Successions »**.
- Cartes : bouton `[data-successions-assembler]` « Assembler → » présent.
- Rangée de gestes : `[data-successions-comparer]` « Comparer (N) → » + « Préparer les
  courriers » côte à côte, EN HAUT sous le bandeau.
- Rangée liste : libellé « Triées par résiduel SDP décroissant ».
- Périmètre : mention « choisi ici — pas hérité du filtre global ».
- Fil de retour vers l'outil : « ← Successions ».

## Après (mesuré sur http://localhost:5173, base labuse — 7 129 parcelles servies)
```
menuLabel            : "Successions à venir"        (pt 1)
title (h2 panneau)   : "Successions à venir"        (pt 1)
breadcrumb           : "← Outils › SUCCESSIONS À VENIR" (pt 1)
hasAssembler         : false                          (pt 2 — bouton retiré)
hasComparer          : false                          (pt 3 — bouton retiré)
triNoteVisible       : false                          (pt 4 — étiquette retirée)
filtreNoteVisible    : false                          (pt 5 — mention retirée)
courrierText         : "✉ Préparer les courriers (0) →"
courrierRight        : true   (bouton à droite de « Détail et méthode »)   (pt 6)
sameLine             : true   (même ligne que le résumé du tiroir, Δtop < 25px) (pt 6)
```

## Après — pont Courrier + fil de retour préservés (test fonctionnel)
```
sélection d'1 ligne  → compteur : "✉ Préparer les courriers (1) →"
clic                 → panneau : "Courrier propriétaire"   (pont vers Courrier OK)
fil de retour        : "← Successions à venir"              (fil + nouveau nom OK)
```

Tri serveur inchangé (aucune touche à `getSuccessions` / `/modules/successions`) ;
comportement du filtre commune inchangé (seule la mention est masquée).
