# GPU-PILOTE — Revue visuelle assemblage (5 cas) : 3 tiennent, 2 révèlent un défaut

> Cartes : `qa/au_ouverture/cartes_assemblage.{html,pdf}` (49 tuiles IGN ortho, cible verte + voisins
> retenus ≥3 m orange + surfaces + seuil). Verdict : NE PAS servir la mention en l'état — la mesure
> compte des voisins NON assemblables en pratique.

## Contiguïté ponctuelle : réglée (Q1)
Passage de `ST_DWithin 0,5 m` (tout contact, coins compris) à **frontière commune ≥ 3 m** (linéaire).
Vérifié sur les cartes : les voisins retenus ont des frontières de 4 à 41 m — de vraies limites.

## Les 3 brûlantes : TIENNENT ✅
- CAS 1 `AB1907` (243 m², seuil 1666) : 4 voisins **non bâtis**, frontières 11,8-18,6 m → assemblage 2 061 m². Vrai lotissement de lots nus contigus.
- CAS 2 `AB1906` (358 m²) : 5 voisins, frontières 6,9-20,1 m → 7 738 m². OK.
- CAS 3 `AB1911` (184 m²) : 4 voisins non bâtis, frontières 9-20,5 m → 1 868 m². Propre.

## Les 2 cas d'épreuve : ÉCHOUENT ❌ — la mesure sur-compte
- **CAS 4 `AB1806` — voisin manifestement BÂTI** : les voisins qui « permettent d'atteindre le seuil »
  sont soit **lourdement bâtis** (`AB1804` 696 m² / **856 m² de bâti**, `AB1807` 1007 m² / **547 m²
  bâti**), soit un **géant à frontière marginale** (`AB0740` 25 353 m², frontière **3,9 m** — juste
  au-dessus du seuil). **Un voisin entièrement bâti n'est PAS assemblable.** La mention dirait
  faussement « des voisines permettraient d'atteindre le seuil ».
- **CAS 5 `AB1808` — voisin le plus petit** : le plus petit voisin retenu fait **8 m²** (un délaissé),
  compté car frontière 7 m. Bruit — inoffensif ici (l'assemblage tient par d'autres), mais il ne
  devrait pas figurer dans « N voisines ».

## Correctif AVANT le re-run (mesure)
Le comptage `voisins_assemblables` doit ne retenir que les voisins **RÉELLEMENT** assemblables :
1. **Exclure les voisins lourdement bâtis** (emprise bâtie > ~50 % de leur surface) — non assemblables.
2. **Ignorer les délaissés** (surface < ~50 m², ou une surface min à caler).
3. Éventuellement relever la frontière min ou plafonner l'apport d'un unique voisin géant à frontière
   juste-au-seuil (le 3,9 m d'un 25 000 m²).
Puis re-mesurer les 399/708 assemblables — le nombre baissera, mais il sera VRAI.

## Verdict
3/5 tiennent, 2/5 échouent → **pas de go immédiat**. Le correctif ci-dessus est déterministe et
sourçable (bâti = `spatial_layers kind=batiment`). Après correctif + re-mesure, nouvelle revue courte.
