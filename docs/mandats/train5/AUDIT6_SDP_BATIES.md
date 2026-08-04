# AUDIT 6 — SDP DES BÂTIES RÉVÉLÉES : ampleur du recalcul résiduel (chemin B)

Constat gravé à la bascule : une `declasse_bati_revele` affiche la SDP du terrain nu
théorique (la chaîne résiduel ignore le bâti révélé par CoSIA).
## Ampleur mesurée
- **9 044** parcelles en règle : **5 132 affichent une SDP > 0**, total **3 484 421 m²**
  de SDP « terrain nu théorique » servie à tort (emprise CoSIA moyenne 149 m²).
- Correction attendue par parcelle : SDP_existante ≈ emprise_max × niveaux (hypothèse
  défaut) — ordre de grandeur : −150 à −400 m² de SDP par parcelle bâtie, soit une SDP
  résiduelle qui tombe souvent sous les seuils (plancher C, réserve foncière).
- Au-delà des révélées : TOUTE parcelle où max(BD TOPO, CoSIA) > emprise BD TOPO
  (~159 000 parcelles servies, mesuré au train 1) a une SDP potentiellement surévaluée —
  mais l'enjeu produit est concentré sur les 5 132 (elles AFFICHENT le chiffre avec la
  mention « terrain nu théorique » depuis la bascule).
## Chemin du recalcul (si arbitré)
Re-passer `compute_residuel` avec l'emprise max (la chaîne calibrée v8 : migration
parcel_residuel + rebuild p_model_static + re-score) — c'est une BASCULE complète
(heures, 6 gardes), qui touche TOUTES les SDP servies, le plancher C et la réserve
foncière. À séquencer comme la v8 (mesure à blanc d'abord). Pas urgent tant que la
mention « terrain nu théorique » est servie — honnêteté affichée.
