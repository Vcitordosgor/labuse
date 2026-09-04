# INVENTAIRE T7 — vocabulaire d'opération (RETOURS-12)

Problème central : des VERDICTS NÉGATIFS issus d'un calcul d'opération (« ne finance pas ce
foncier », « opération non viable ») sont affichés au PREMIER niveau, sans que l'utilisateur
ait demandé une analyse d'opération et sans dire que c'est un scénario promoteur parmi
d'autres. Un notaire / agence / particulier n'a aucun indice que LABUSE calcule « vendre
neuf au prix DVF avec marge promoteur ».

## Premier niveau (verdict négatif à l'accueil) — À CORRIGER

| Fichier:Ligne | Écran | Texte |
|---|---|---|
| outils/EtudierBien.tsx:73 | banner accueil | « ce que le terrain vaut pour une opération » |
| outils/EtudierBien.tsx:160-167 | bloc verdict (charge ≤ 0) | « L'opération ne finance pas ce foncier… même terrain gratuit, elle ne dégage pas de valeur » |
| outils/EtudierBien.tsx:124,180 | bloc constat | « prix de sortie bâti », « CA visé 526 k€ sur 123 m² vendables » |
| outils/moteurs.tsx:254-267 | Assemblage M16 | « Charge foncière cumulée : −219 123 € », « l'ensemble ne finance pas ce foncier » |
| copilote/Resultats.tsx:42-57 (+ strings.ts:533-557) | restitution Copilote | « Opération non viable — charge nulle ou négative » |

## Second niveau (geste explicite) — vocabulaire promoteur assumé, à conserver

| Fichier:Ligne | Écran |
|---|---|
| fiche/constructibilite.tsx:67-300 | Calculette de charge foncière (« Vos hypothèses ») |
| api/briques_pdf.py:529-592 | PDF « Bilan promoteur & charge foncière » |

## Chaîne de calcul Faisabilité (pour O2)

`src/labuse/faisabilite/bilan.py` : `compute_bilan()` (429-694). Charge = bilan à rebours :
`cf = CA × coef_marge − coût_construction − VRD` (ligne 604-606). Bornée bas à 0 pour
l'affichage mais valeur brute négative montrée. `compute_calculette()` (739-842). Le prix
demandé est ensuite comparé/soustrait côté front.

## Règle T7 retenue

1. Premier niveau = descriptif/neutre (ce que porte la parcelle) ; aucun verdict négatif
   d'opération à l'accueil.
2. Le raisonnement d'opération (bilan, charge, marge) devient un second niveau explicite
   (« analyser une opération sur cette parcelle »).
3. Termes métier dits en français d'abord, technique entre parenthèses.
4. Le gros de la refonte Faisabilité est traité en O2 (bloc 2) ; T7 pose la règle
   transversale + neutralise les libellés de premier niveau (EtudierBien, moteurs M16,
   Resultats Copilote).
