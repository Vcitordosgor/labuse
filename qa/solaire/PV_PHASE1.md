# SOLAIRE M2 — Phase 1 : la méthode + l'essai empirique (STOP)

## 1. Comment les piscines sont détectées (rappel, motif à transposer)

`src/labuse/ingestion/ortho_piscines.py` (Lot 3, **au dépôt** — pas parti au spin-off), V0 déterministe
OpenCV/CPU sur les tuiles BD ORTHO 20 cm 2025 (cache Lot 2) :
- **HSV → masque cyan/turquoise** (plages `config/detection_ortho.yaml[piscines]`) + morphologie ;
- contours + filtres géométriques (surface 6-150 m², solidité, ratio d'aspect < 6) ;
- filtres contextuels SQL (centroïde en parcelle bâtie / < 30 m, exclusion eau/ravines) ;
- confiance composite. **Précision mesurée ~90,7 %** (juge FLAIR × probe, 966 verdicts Vic).
La piscine marche parce que le **cyan brillant est une signature RARE et distinctive** sur une toiture.

## 2. Le PV par la même voie — l'essai

Un détecteur PV EXISTE déjà : `src/labuse/ingestion/ortho_pv.py` (Lot 4, au dépôt). Masque bâti∪parkings,
**teinte sombre bleutée/anthracite (V ≤ 110), rectangularité ≥ 0,75, ≥ 4 m²**, gestion CES/ombres/velux.
Il a produit **23 529 candidats** dans `ortho_detections type='pv'` — mais **JAMAIS validés**
(`validation` NULL partout) : le portillon de matérialisation (précision ≥ 75 % sur 150, mandat d'origine)
n'a jamais été franchi, d'où `parcel_equipements.pv_detecte = 0`. Le mandat d'origine lui-même annonçait
« plus difficile que les piscines, précision moyenne assumée, cible ≥ 75 % ».

**Essai** (`qa/solaire/pv_probe.py`) : le cache ortho ayant été purgé, on RE-ACQUIERT les tuiles (WMS BD
ORTHO, gratuit sans clé), on découpe l'emprise des parcelles échantillon, on assemble des planches, on
étiquette à l'œil (vérité terrain) et on croise avec les détections stockées.
Échantillon **59 parcelles** : 30 « détectées PV » (étalées en confiance) + 29 grands toits ≥ 800 m²
(cibles installateur). Planches : `qa/solaire/pv_crops/planche_0..4.png`.

### Matrice (51 étiquetées, 8 ambiguës « ? » écartées)

| | PV réel (œil) | Pas de PV |
|---|---|---|
| **Détecté PV** | TP = **0** | FP = **28** |
| **Non détecté** | FN = **0** | TN = **23** |

**PRÉCISION = 0 %** · RECALL = n/a (aucun PV confirmé dans l'échantillon, même parmi 30 grands toits).

Les 28 « détections » étiquetées sont des **faux positifs identifiables** : piscines bleues (#1, #8, #25,
#27), toitures peintes bleutées / tôle claire (#9, #19, #13, #39), **serres/tunnels agricoles** (#17, #34,
#54), **terrain de sport** (#18), toitures grises banales. Exactement les confusions que le détecteur
disait « gérer » — il ne les gère pas. Un vrai grand PV commercial (#32) n'était **pas** détecté (FN visuel).

Réserve honnête : à 20 cm, un **petit PV résidentiel** peut m'échapper (d'où les 8 « ? » exclus) — mais les
28 FP, eux, montrent des objets CLAIREMENT non-PV. La précision est donc réellement très basse, bien en
deçà des 85 % (et même des 75 % d'origine). NB : la détection de confiance MAX isolée (idu 97407000AZ0163,
conf 0,88) était un vrai PV — le haut de la distribution contient des vrais positifs, mais la masse des
23 529 candidats est dominée par le bruit.

## 3. Verdict : STOP

**On ne sert pas ce filtre.** Le motif colorimétrique ne se transpose pas des piscines au PV : le cyan
d'une piscine est distinctif ; un panneau sombre se confond avec toits sombres, ombres — et surtout avec
les objets brillants que le détecteur sur-déclenche (piscines, toits bleutés, serres, terrains de sport).

**Alternatives (à arbitrer sur ces chiffres) :**
1. **Modèle IA léger** (segmentation sémantique « panneau PV ») — la seule voie crédible, MAIS il faut
   d'abord un **jeu étiqueté** (quelques centaines de toits PV/non-PV labellisés) : c'est un mandat de
   DONNÉE à ouvrir, pas un dérivé gratuit de l'existant.
2. **Renoncer** au filtre « toits sans PV » en V0 — l'honnêteté commerciale l'emporte sur un filtre qui se
   trompe massivement.

Pas de Phase 2 (pas de `pv_detecte` servi, pas de filtre « sans PV ») tant que (1) n'a pas livré.
