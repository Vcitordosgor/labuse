# MISE-EN-LIGNE-6 — prescriptions Bras-Panon / Saint-Joseph (LOT 1)

**22/11, lecture seule.** Prescriptions du GPU téléchargées **hors base** (API Carto
`prescription-surf/lin/pct` par partition `DU_97402`/`DU_97412`, document en vigueur), comparées
aux servies par **différence symétrique d'aire** (robuste à l'ordre et à la précision) et par
histogramme `typepsc`. **Verdict : DIFFÉRENTES (infime) → ARRÊT. Rien n'a été ingéré.**

## Ce que montre la comparaison

**Géométrie globale : ~99,99 % identique.** Surf : recouvrement **100 %** (Bras-Panon 7 762,9 ha
servi = 7 762,9 ha GPU ; Saint-Joseph idem à l'arrondi). Lin/pct : déplacement < 0,3 %. *(Un
premier chiffrage par `md5(wkb)` donnait de faux écarts — artefact d'ordre des sous-géométries ;
corrigé par la mesure d'aire.)*

**Mais des objets réels ont été ajoutés** (composantes > 50 m², hors slivers) :

| Commune | Type | Ajout réel | Parcelles touchées |
|---|---|---|---|
| Bras-Panon (97402) | EBC (01) | 1 objet, **490 m²** | **0** |
| Saint-Joseph (97412) | EBC (01) | 1 objet, 60 m² | **0** |
| Saint-Joseph (97412) | **ER (05)** | 1 objet, **470 m²** | **2** : `97412000AH1042` (7 440 m²), `97412000AH1041` (797 m²) |

Rien n'a été retiré ; les types inchangés (ER/mixité/patrimoine/pct) sont identiques des deux
côtés. **Impact réel sur le classement : 2 parcelles** (Saint-Joseph), sous un **nouvel
emplacement réservé** de 470 m². Bras-Panon : 0 parcelle touchée (le nouvel EBC tombe hors
parcellaire — voirie/espace public).

## Règles du classement qui lisent ces prescriptions

`cascade/layers/phase1.py` + `regles/dispositifs_droit_sols.py` + `faisabilite/db.py:
parcel_faisabilite` : **EBC (type 01)** — part ≥ 80 % → RÉDHIBITOIRE, sinon part soustraite de
l'assiette ; **ER (type 05)** — part ≥ seuil → RÉDHIBITOIRE, sinon vigilance + **surface ER
déduite de l'emprise constructible** (union ER∪EBC). Donc les 2 parcelles `97412000AH1041/1042`
verraient leur emprise constructible réduite par le nouvel ER — un vrai effet, mais borné à ces
deux parcelles.

## Verdict et geste proposé (rien d'ingéré sans ta réponse)

**Ce n'est pas un simple ré-étiquetage.** Un ré-étiquetage (script d'hier) poserait le nouvel
idurba sur des géométries qui n'ont **pas** les nouveaux EBC/ER → le servi mentirait (étiquette
`20260428`/`20251210` sans l'ER de Saint-Joseph). Il faut **ré-ingérer** les prescriptions.

**Geste proposé** (≈ 30 min, hors fenêtre de calcul) :
1. **Mac** — ré-ingérer zones + prescriptions des 2 communes depuis le GPU (pipeline existant
   `ingest_gpu_zones` + `ingest_gpu_prescriptions`, par commune) : met `plu_gpu_prescription` au
   nouvel idurba **avec** les nouveaux objets, et recalcule `parcel_zone_plu` /
   `parcel_couche_intersection` localement (~quelques min).
2. **Envoi ciblé en prod** — les lignes `plu_gpu_prescription` (et zones si besoin) des 2
   communes seulement, par un geste de fond ciblé (≈ comme hier, mais géométries ré-ingérées, pas
   une étiquette) + sauvegarde des lignes touchées avant (quelques Mo).
3. **Intersections** — recalcul des intersections parcelle × prescription pour ces 2 communes
   (les 2 parcelles de Saint-Joseph prennent l'ER). `plu-veille-nuit` doit alors sortir **24/24**.
4. Puis q_v25 lirait des prescriptions à jour.

**Alternative** : lancer q_v25 maintenant en l'état — conséquence exacte et bornée : **2
parcelles de Saint-Joseph** (AH1041, AH1042) seraient classées avec une emprise légèrement
surestimée (ER de 470 m² ignoré) ; **Bras-Panon : aucun impact**. À re-corriger après.

**Je m'arrête ici** (LOT 2 conditionné à un LOT 1 vert = « identiques », ce qui n'est pas le
cas). Dis-moi : ré-ingérer les prescriptions des 2 communes avant q_v25, ou lancer q_v25 en
acceptant l'écart de 2 parcelles et corriger après ?
