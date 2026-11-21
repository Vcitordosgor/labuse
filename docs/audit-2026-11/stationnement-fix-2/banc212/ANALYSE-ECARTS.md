# Banc 212 — recalcul depuis l'image : écarts moteur (7 catégories)

267 couples recomputés depuis l'image de la page officielle (agent lecteur d'image, ne lit pas le code),
4 programmes chacun. 145/267 couples concordants 4/4. 37 lignes d'écart = bugs moteur réels :

## Cat. 1 — Arrondi inférieur non appliqué (le moteur arrondit au supérieur)
- La Plaine-des-Palmistes 97406 (R1-R4) : « 1,5 place/logt arrondi à l'entier INFÉRIEUR pour l'ensemble
  de l'opération » → maison 1,5→1 ; moteur rend 2. VÉRIFIÉ IMAGE p.103.
- Saint-Paul 97415 (R2,R3,R5,R6,R7) : zones 1,5/logt, arrondi inférieur → maison 1,5→1 ; moteur rend 2.

## Cat. 2 — Logement aidé plafonné à 1/logt (R.111-25 / L151-35), moteur applique la règle générale
- Étang-Salé 97404, Saint-André 97409, Cilaos 97424 (R1-R3), Saint-Paul 97415-R4 (Usdu) :
  aidé = 20 (1/logt) ; moteur = 30 (1,5/logt) voire 44.

## Cat. 3 — Visiteur spécifique du logement aidé (1/10) manquant
- Entre-Deux 97403 : aidé = 20 + 2 (1 visiteur/10 logts) = 22 ; moteur = 20.
- Saint-Paul 97415 (R1,R2,R3,R5,R6,R7) : aidé = 20 + 2 = 22 ; moteur = 24/34 (applique le visiteur général 1/5).

## Cat. 4 — Terme au m² du logement aidé (Le Port)
- Le Port 97407 (R1-R5) : aidé = 0,2/logt + 8 places/1000 m² = 16 ; moteur = 4 (terme +8/1000 manquant).

## Cat. 5 — Places PUBLIQUES (opération > 10/5 logements : +0,5/logt sur le domaine public)
- Saint-Louis 97414 (R1-R4) : aidé a 10 publiques ; moteur = 0.
- Sainte-Suzanne 97420 : collectif/mixte ont 10 publiques ; moteur = 0.

## Cat. 6 — Seuil de surface PAR LOGEMENT (Saint-Denis)
- Saint-Denis 97411 : mixte = 25 (10×110 m²≥100→1,5 + 10×30 m²<100→1) ; moteur = 20 (palier ≥100→1,5 manquant).

## Cat. 7 — Couverture
- Saint-Pierre 97416-R4 (Uf6) : page rendue incorrecte → à relire (zones Uf) ; non un bug moteur a priori.
