# CHASSE-CALCULS-FIX-1 — captures

Captures réelles (navigateur Playwright, stack lancée localement : back 8781 + vite 5981, base q_v18).

| fichier | écart | ce qu'on voit |
|---|---|---|
| `A1-taxe-avant-1logement-66231.png` | **E-A1 + E-A2** | Outil TA, surface 1 400 m², résidence principale, **nb de logements vide** → **Total 66 231 €** + message « appliqué pour 1 logement … saisissez le nombre de logements » + encart **« Non pris en compte »** (exonérations facultatives, stationnement majoré). |
| `A1-taxe-apres-20logements-34342.png` | **E-A1 + E-A2** | Même cas, **nb de logements = 20** → **Total 34 342 €** (= recalcul manuel), le message a disparu ; l'encart « Non pris en compte » reste. |
| `C1-gabarit-3D-terrain-plat.png` | **E-C1** | Outil Gabarit (AK0804), **3D active** (hauteur sourcée 14 m) → note **« Volume 3D indicatif — terrain supposé plat (le relief n'entre pas dans le volume) »**. |
| `B3-fiche-legacy-AB0318-sans-pct-impossible.png` | **E-B3** (appui) | Fiche d'une parcelle servie par le moteur de secours (AB0318) : « SDP restante — » servie **proprement**, **aucun pourcentage impossible** (le `pct_potentiel` 164 % de l'audit n'est plus servi). |

## Note honnête sur la 4ᵉ capture (note « estimation simplifiée » en fiche)
La mention **« estimation simplifiée »** (E-B3) et la **note de surface datée** (E-B1) sont servies dans le payload `potentiel_transformation` (vérifié en direct : `GET /parcels/97411000AB0318` renvoie `estimation_simplifiee_note` + `pct_consomme: null`) et rendues par le code committé (`constructibilite.tsx` `TransformationBlock`). Leur **tiroir de fiche** n'a pas été surfacé par la navigation de cette session (le bloc `TransformationBlock` se monte dans la vue constructibilité, pas dans l'accordéon latéral atteint ici). La preuve fournie est donc : payload live + code + garde `_garde_eb3.py` exit 0. `B3-fiche-legacy-*.png` montre l'effet côté stats de fiche (plus de % impossible).
