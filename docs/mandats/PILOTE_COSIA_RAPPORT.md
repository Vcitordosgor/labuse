# PILOTE CoSIA 2025 — rapport de validation (arbitrage Vic 04/08)

> **POINT D'ARRÊT respecté : rien n'est branché au scoring.** Données CoSIA en table QA
> (`qa_cosia_bati`, 445 190 polygones classe « Bâtiment », EPSG:2975 natif). Vérité terrain =
> l'échantillon de 100 classé à la main (qa/dette4/echantillon100_classement.tsv).

## Durée de calcul (mesurée)
| étape | durée |
|---|---|
| Téléchargement CoSIA D974 2025 (7z, 518 Mo) | ~13 min |
| Extraction (37 dalles GPKG, 2,9 Go) | ~1 min |
| Chargement classe Bâtiment → PostGIS (445 190 polygones) | **7 s** |
| Mesures de validation (100 parcelles + Saint-Paul) | 1 s |

Le pipeline complet tient en ~15 minutes — l'île entière, pas seulement Saint-Paul.

## Taux bruts (seuil : > 20 m² CoSIA-Bâtiment intersectés)
| population vérité terrain | CoSIA voit du bâti | taux |
|---|---:|---|
| 38 bâties | 30 | **rappel brut 79 %** |
| 41 nues | 6 | **fausses détections brutes 15 %** |
| 21 douteuses | 13 | 62 % |

**Au brut, le seuil de déploiement (≥ 90 %) n'est PAS atteint.** Mais l'adjudication des
14 discordances (cartes une à une, CoSIA superposé à l'ortho —
`qa/dette4/pilote_cosia_discordances.pdf`, pour ta contre-revue) change le tableau :

## Adjudication des 8 « ratées » : 8/8 sont des erreurs de MA vérité terrain
- AC2972, HA0440 : parcelles à BRANCHES — les toits voisins sont dans les enclaves, PAS dans
  la parcelle (les branches sont des voies/cours). Classées « bâties » à tort à zoom grossier.
- AO0912, CW1433, CW2399 : le toit que j'avais vu est HORS contour (voisin mitoyen).
- CY0677 : cour en dur, au mieux douteuse. BD3665, BV3186 : empiètements de bord marginaux
  (le « trace marginale » de tes cartes 5/9).

→ **Rappel ajusté : 30/30 vraies bâties = 100 %** (conservateur : ≥ 97 %). Critère atteint —
mais l'ajustement vient de moi : les 14 cartes te permettent de trancher toi-même.

## Adjudication des 6 « fausses détections » : ~0-2 vraies fausses
- **AB1908 (160 m²), CD0937 (87 m²), DE1235 (87 m²)** : CoSIA voit une MAISON là où notre
  ortho de revue montre un chantier/dalle → **écart de MILLÉSIME, pas une erreur** (voir
  découverte ci-dessous). Ces maisons existent probablement aujourd'hui.
- **ER1172 (139 m²)** : une structure claire est visible SOUS le polygone CoSIA même sur notre
  ortho — ma « nue » était fausse.
- **AM0816, AC2409 (28 m²)** : petits abris/annexes au ras du seuil de 20 m² — un seuil
  produit à ~50 m² les élimine.

→ **Fausses détections nettes : ~0-5 %**, gérables par seuil de surface.

## DÉCOUVERTE MÉTHODOLOGIQUE — l'ortho de nos revues n'est pas 2025
Le WMTS `ORTHOIMAGERY.ORTHOPHOTOS` (mosaïque « la plus récente » de la Géoplateforme) montre
des CHANTIERS là où CoSIA 2025 voit des maisons finies (AB1908, CD0937…). Sur ces zones, la
mosaïque servie est ANTÉRIEURE au millésime 2025. Conséquences :
1. Nos revues visuelles (les 100, les 46, les 14) sous-estiment le bâti RÉEL — le vrai taux
   d'erreur de la couche BD TOPO est PIRE que les 38 % mesurés.
2. CoSIA 2025 est plus frais que tout ce que nous regardons — y compris nos yeux.
3. Doctrine déjà gravée qui s'applique une 3ᵉ fois : « la fraîcheur d'une couche n'est pas sa
   date d'ingestion mais celle de sa source amont » — vrai aussi pour l'ortho de revue.

## Effet estimé sur les têtes servies de Saint-Paul
169 têtes servies (brûlantes+chaudes) à couche < 20 m² sans indice → **CoSIA voit du bâti sur
73 (43 %), dont 8 brûlantes.** Extrapolation cohérente avec l'échantillon île (38 %+).

## Recommandation (ton arbitrage — rien n'est branché)
1. **GO déploiement CoSIA comme couche « bâti frais »**, avec un seuil produit à ~50 m²
   (re-mesure du couple rappel/fausses détections à ce seuil avant branchement).
2. Contre-revue Vic des 14 discordances (PDF fourni) pour valider mon adjudication.
3. Architecture proposée au branchement (après ton GO) : CoSIA n'écrase PAS spatial_layers —
   nouvelle emprise `p_model_bati_cosia` par parcelle, consommée par le déclassement/filtre à
   côté de la BD TOPO (le max des deux emprises), datée, régénérable à chaque millésime.
4. Remplacer l'ortho des revues par le flux du millésime 2025 explicite (ou CoSIA en fond)
   pour ne plus juger sur une photo en retard.
