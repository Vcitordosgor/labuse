# Où voir le LiDAR HD — une page

**Ce que c'est.** Le LiDAR HD de l'IGN (surface MNS − sol MNT) donne la hauteur **mesurée** d'un bâtiment,
et distingue le **faîtage** (haut du toit) de l'**égout** (bord de toit). Le BD TOPO, lui, ne porte qu'UNE
hauteur, incertaine, souvent au faîtage. Là où le LiDAR est passé, la hauteur passe d'**estimée** à
**sourcée (mesurée)**, et l'égout — que BD TOPO ne donne jamais — devient disponible.

Parcelle témoin : **97411000EL0157** (Saint-Denis) — **faîtage 6,9 m · égout 3,0 m** (mesurés).

| Où | Ce qu'on voit | Ce que ça dit de plus | Ce que ça change | Capture |
|---|---|---|---|---|
| **Fiche parcelle** → tiroir « Le bien » | « Hauteur du bâti **6,9 m au faîtage · 3,0 m à l'égout** — LiDAR HD (mesuré) » + pastille **sourcé** | Deux hauteurs distinctes, mesurées (au lieu d'une seule, estimée BD TOPO) | L'étiquette de nature : **sourcé** au lieu d'estimé | `captures-recette-10/T10-fiche-le-bien-lidar.png` |
| **Fiche parcelle** → Constructibilité | « Surélévation **possible (marge ~3,1 m, limité par le faîtage)** » | La marge est **mesurée**, et on sait **laquelle** des deux contraintes mord | Le **scénario de surélévation** (T1) : 3,1 m au lieu du 7,0 m gonflé | `captures-recette-10/T1-fiche-surelevation.png` |
| **Dossier** → §3 « Potentiel constructible » | « Surélévation possible — 3,1 m disponibles, **limité par le faîtage** (mesuré au LiDAR HD). égout 3,0 mesuré contre 7,0 réglementaires (4,0) · faîtage 6,9 contre 10,0 (3,1) » | Les **deux** calculs, chacun apparié à SA règle | Le chiffre imprimé au client : plus d'inversion égout↔faîtage | `captures-recette-10/T1-dossier-EL0157.pdf` (§3) |
| **Apporteur** | « environ **6,9 m** de haut » (hauteur du bâti servie par le même point LiDAR) | La hauteur de l'Apporteur est la même donnée mesurée | Cohérence : un seul point de hauteur pour tous les documents | (partage `hauteur_batie`, cf. Dossier) |
| **Extrusion 3D** (carte, bouton « 3D ») | Le bâti extrudé à sa hauteur | Là où le LiDAR est ingéré, l'extrusion peut passer au faîtage mesuré | Précision de la 3D (aujourd'hui BD TOPO ; bascule au LiDAR = mandat d'ingestion de masse T9) | — |

**Le point unique.** Les quatre consommateurs lisent la même mesure via `hauteur_lidar.hauteur_batie` /
`hauteur_lidar_servie` (table `batiment_hauteur_lidar`, une ligne par parcelle mesurée). **Garde** : la
pastille « sourcé » / « mesuré LiDAR HD » n'apparaît QUE là où cette ligne existe — jamais un faux
« mesuré » sur une commune non passée au LiDAR.

**Couverture.** Saint-Denis + le sous-ensemble prioritaire-bâti des 23 autres communes (ingestion bornée
T9). Le passage de TOUTE l'île au LiDAR (274 599 parcelles bâties) demande une ingestion de dalles MNS
dédiée (chiffrage en RECETTE-10 §T9), pas le WMS par parcelle.
