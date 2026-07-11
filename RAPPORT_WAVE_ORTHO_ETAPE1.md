# Wave Détection Ortho — rapport d'étape 1 (Lots 1-3) · STOP validation Vic

**Branche** : `feat/wave-ortho-detection` (5 commits). **État** : l'outil de validation des
200 vignettes est PRÊT — le mandat s'arrête ici en attendant ta session (les Lots 4 PV,
5 matérialisation, 6 front et 7 refresh reprennent après tes métriques).

## 🎯 Ta session de validation (~20-30 min)

```
labuse api            # (une instance tourne déjà sur le port 8003)
→ http://127.0.0.1:8003/ortho/validation
```
Raccourcis clavier : **O** = piscine · **F** = faux positif · **espace** = passer.
La page tire des vignettes ALÉATOIRES (détection surlignée rouge + 50 m de contexte),
affiche la progression /200 et la **précision live**. Objectif mandat : ≥ 90 % —
sinon on resserre les seuils (`config/detection_ortho.yaml`) et on rejoue, ou on
remonte le seuil de confiance de matérialisation (courbe par tranche ci-dessous à
recalculer après tes 200 verdicts) :
```sql
SELECT width_bucket(confiance, 0.5, 1.0, 5) AS tranche,
       count(*) FILTER (WHERE validation='ok')::float
       / NULLIF(count(*) FILTER (WHERE validation IS NOT NULL), 0) AS precision
FROM ortho_detections WHERE type='piscine' GROUP BY 1 ORDER BY 1;
```

## Ce qui est fait

**Lot 1 — pente** : `parcel_terrain` RÉUTILISÉE (aucune table concurrente), raster de
pente 5 m conservé réutilisé (zéro re-téléchargement). Nouvelle colonne
`pente_non_batie_deg` (parcelle − bâtiments, là où va la piscine) : 173 051/423 452
calculées, le job checkpointé continue en fond (~10-15/s, fin dans quelques heures,
sans impact sur la suite). Sanity : médiane bâties 6,5° < île 7,4° ✓ (écart modéré :
le cadastre exclut déjà remparts et cirques — pas de bug d'unités).

**Lot 2 — tuiles** : BD ORTHO **millésime 974 = 2025** (20 cm, fiche IGN — vérité
terrain toute fraîche). Mode retenu : WMS Géoplateforme EPSG:2975 natif (2560² px),
vs dalles JP2 (~50-80 Go) → **5 041 tuiles utiles** (bâti ∪ parkings, océan/remparts
ignorés) = 5,6 Go de cache, 0 échec, reprise par tuile. ⚠ le cache est CONSERVÉ
jusqu'à la fin du mandat (les vignettes de validation en dépendent) — purge au Lot 7.

**Lot 3 — piscines V0 + calibration par planches** : pipeline HSV → morphologie →
filtres géométriques → rejets contextuels SQL → confiance composite (détail dans
`criteres`). Partie la plus utile de l'étape : **4 planches de 24 vignettes inspectées
visuellement** ont fait passer la précision estimée de ~30 % à ~60-65 % au seuil 0,7
(~75-80 % à 0,9) en identifiant les faux positifs RÉUNIONNAIS :

| Faux positif | Volume rejeté | Parade (config/SQL) |
|---|---|---|
| Toits de tôle bleue | 33 011 | recouvrement bâti > 25 % (au lieu des 60 % du mandat) |
| Voitures/camions bleus | ~9 000 | voirie BD TOPO < 4 m + parkings OSM + surface ≥ 10 m² |
| Bâches sombres | ~12 000 | V moyen ≥ 135 |
| Bleu roi (bâches neuves) | inclus | H ≤ 112 (plage mandat 80-130 resserrée à 85-112) |
| Terrains multisport bleus | 207 | couche OSM pitch |
| Lagon fragmenté | ~150 000 bruts | filtre « < 30 m d'une parcelle » dès l'INSERT |

**Résultat île entière (run homogène, bornes calibrées)** : 55 554 candidats bruts →
**19 899 détections** (18 901 ≥ 0,7 · 11 196 ≥ 0,9) sur **18 361 parcelles** —
DANS la fourchette d'acceptation (15 000-45 000). Surface médiane 19 m² (typique).

**Gradient géographique** (critère mandat ✓) : taux d'équipement des parcelles bâties —
tête : La Possession 11,0 %, L'Étang-Salé 10,5 %, Saint-Paul 9,4 %, Saint-Denis 7,8 %,
Saint-Leu 6,9 % · queue : Plaine-des-Palmistes 1,1 %, Cilaos 1,2 %, Salazie 1,7 %,
Sainte-Rose 3,5 %. Couverture traitement : 5 041/5 041 tuiles = **1.0** ✓.

**Recall (estimation qualitative, 3 quartiers × 24 parcelles bâties inspectées)** :
Ermitage ~6/7 piscines visibles détectées ; Tampon 1-2/2 ; Sainte-Marie : 1 piscine à
eau SOMBRE non détectée — le faux négatif type ASSUMÉ par le mandat (eau verte/sombre,
couverte, sous canopée). Recall estimé **~70-85 % sur piscines bleues visibles** ;
la mesure formelle (100 parcelles/quartier) pourra suivre ta session si tu la juges utile.

## Positionnement (rappel contrainte mandat)

Qualification commerciale uniquement — aucun code, requête ou texte orienté détection
fiscale. Attribution IGN + mention « détection automatique sur orthophotographie IGN
2025 — fiabilité statistique, non contractuelle » prévue au front (Lot 6).

## Après ta session (reprise du mandat)

1. Si précision ≥ 90 % (éventuellement en remontant le seuil) → Lot 5 partiel
   (matérialisation `parcel_equipements.piscine`), Lot 6 (vues piscinistes = PRESET du
   moteur de segments + parc piscines), signal `piscine_detectee`.
2. Lot 4 PV (mêmes tuiles, cible ≥ 75 %, chauffe-eau 4-8 m² = signal CES) + ombrières
   parkings → `parkings_aper.equipe` ; **croisement Lot 5.2 « PV détecté × communes
   2006-2013 » = la SEULE voie repowering** (registre anonymisé, cf. mandat solaire).
3. Lot 7 refresh (--refresh par millésime) + purge du cache (5,6 Go).
4. GO/NO-GO Lot 8 ML sur tes métriques — tes 200 verdicts sont déjà le début du
   dataset d'entraînement.
