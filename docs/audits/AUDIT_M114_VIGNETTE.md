# M114 · Phase 0 — la vignette du secteur : faisabilité mesurée

Mesuré le 18/08/2026, base réelle. **STOP** : ces mesures + la recommandation attendent l'arbitrage
de Vic (vignette réelle ou repli) avant de construire la refonte.

## Ce que la vignette doit montrer

La maquette (`DA-PROJETS-v1.html` §6) porte une miniature de l'emprise à gauche de chaque ligne
(64 px « à trier » / 52 px « à jour »). **Ce n'est PAS une image satellite** : c'est un SCHÉMA —
des rectangles en contour (parcelles du secteur) + un aplat mint (parcelles retenues). Le signal
utile est la **répartition spatiale** du projet, pas un fond de carte.

## Faisabilité — la donnée est déjà là, et gratuite

`projet_parcelles` (statut par parcelle : proposee/retenue/ecartee/a_analyser) ⋈ `parcels.centroid`
donne directement les points + leur statut. Normalisés client-side dans la bbox du projet → un SVG
de la même nature que la maquette.

| mesure | valeur |
|---|---|
| requête par projet (chaud) | **1–7 ms** |
| **UNE requête batchée pour toute la liste** (9 projets, 355 parcelles) | **27 ms** |
| stockage | **aucun** (dérivé live) |
| cache / invalidation | **aucun** — lecture live de `projet_parcelles` : une parcelle retenue/écartée se voit au prochain fetch, sans rafraîchissement |
| génération | SVG client depuis les points (tokens DA), négligeable |

La liste charge déjà les `counts` (proposee/retenue…) par projet — la vignette se greffe sur la même
lecture, un seul aller-retour.

## Le projet sans emprise (état vide)

**5 projets** sur la base n'ont AUCUNE parcelle (cadrage à compléter, zéro retenue). Leur vignette
n'a rien à tracer. → état vide DISTINCT d'un chargement : carré atténué + **initiale de la commune**
en mono (repli du §2 du mandat), jamais un spinner.

## Recommandation

**Vignette réelle** (schéma SVG des centroïdes : contour pour proposée/écartée, aplat mint pour
retenue) quand le projet a des parcelles ; **initiale de la commune** quand il n'en a pas. Le
« repli » du mandat n'est donc pas une alternative globale mais l'**état vide** naturel. Coût
mesuré négligeable (~27 ms pour toute la liste, zéro stockage, zéro cache) : rien ne justifie de
renoncer à la vignette réelle. Client-side (React SVG) pour coller aux tokens DA et éviter tout
stockage/rendu serveur.
