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

---

# LOT 1 bis (22/11 ap-midi) — ingestion Mac, PREUVE ÉCHOUÉE → ARRÊT. Mon LOT 1 était faux.

**Décision Vic** : prescriptions seules, preuve avant envoi (diff = exactement +1 EBC BP, +1 EBC
+1 ER SJ, rien d'autre), sinon ARRÊT.

**Ce que j'ai fait** : ré-ingéré les prescriptions seules des 2 communes sur le **Mac** (purge
ciblée par ancien idurba — garde le débordement 97419 — puis `ingest_gpu_prescriptions`),
snapshots avant/après, comparaison robuste par type.

**La preuve a ÉCHOUÉ**, et le diagnostic révèle que **mon analyse du LOT 1 était erronée** :
- au LOT 1 je mesurais l'aire **globale, tous types confondus** (« recouvrement 100 % »
  trompeur, car le type 02 couvre tout) et ne regardais **que les ajouts**, pas les **retraits**.

**Vrais chiffres** (ancien document servi vs GPU en vigueur, **par type, ajouts ET retraits**) :

| Commune | Type | Δ réel | Parcelles intersectées |
|---|---|---|---|
| Bras-Panon | EBC (01) | +490 / −379 m² | **633** |
| Bras-Panon | type 02 | +243 m² | — |
| **Saint-Joseph** | **EBC (01)** | +58 m² / **−19,9 ha retirés** (1 grand EBC déclassé) | **~3 777** (brut, bords inclus) |
| Saint-Joseph | ER (05) | +470 m² | 2 (AH1041, AH1042) |

**L'écart est substantiel**, pas « 2 parcelles » : un **espace boisé classé de ~20 ha a été
déclassé à Saint-Joseph** par le nouveau PLU → la constructibilité de centaines/milliers de
parcelles y change (EBC retiré = assiette rendue). Ce n'est ni un ré-étiquetage ni un détail.

**Second problème** : le pipeline `ingest_gpu_prescriptions` (requête **par bbox**, puis filtre
partition) donne un résultat **différent du téléchargement direct par partition** (Saint-Joseph
surf-01 : ré-ingéré 65 features / 11 442 ha vs GPU-partition 64 / 11 435 ha — ~7 ha de
débordement d'une commune voisine). Donc même l'ingestion « officielle » ne reproduit pas
exactement le document GPU : à fiabiliser avant tout envoi.

**État** : **ARRÊT**. **La prod n'a jamais été touchée** (écritures uniquement sur le Mac). Le
**Mac a été restauré** à l'état d'avant depuis la prod (empreintes Mac = prod re-vérifiées,
Bras-Panon `8f78…`, Saint-Joseph `5ca7…`). **q_v25 NON lancé** (règle « un rouge → ARRÊT »).

**Ce qu'il faut maintenant décider (Vic)** : l'écart réel (déclassement d'un EBC de 20 ha à
Saint-Joseph, mouvements EBC à Bras-Panon) dépasse largement ce que j'avais estimé. Options :
1. **Mettre à jour les prescriptions** (geste de fond complet, intersections recalculées) en
   acceptant que la constructibilité de nombreuses parcelles de ces 2 communes change — **avant**
   q_v25 ; mais d'abord fiabiliser l'ingestion (partition, pas bbox) pour reproduire exactement
   le GPU. Puis relire l'impact (combien de parcelles gagnent/perdent de la constructibilité).
2. **Lancer q_v25 sans ces prescriptions** (en l'état servi actuel) et traiter ces 2 communes
   après — mais alors le classement servira un EBC de 20 ha qui n'existe plus à Saint-Joseph.

Je n'ingère/n'envoie/ne lance rien avant ta réponse. Je corrige aussi, par ce rapport, les
chiffres faux de mon LOT 1.

## Correction des chiffres d'impact (lecture seule, mesures abouties)

Les comptes « 3 777 » et « 633 » étaient des **effleurements de bord** : le contour d'un EBC
redessiné de 1-2 m crée des slivers tout le long de son périmètre, qui bordent des centaines de
parcelles **sans qu'aucune ne perde de surface constructible**. Le chiffre pertinent est
l'intersection **> 5 % de la surface de la parcelle** :

| Commune | Changement | Aire (brut) | **Parcelles matériellement touchées (>5 %)** |
|---|---|---|---|
| **Saint-Joseph** | EBC déclassé | **−19,9 ha** (mais surtout sur domaine non parcellaire — ravine/forêt) | **6** (9 avec >50 m²) |
| **Saint-Joseph** | ER ajouté | +470 m² | **2** (AH1041, AH1042) |
| **Bras-Panon** | EBC (contour redessiné) | +490 / −379 m² (net ~0) | **~0** (bords uniquement ; compte précis >5 % en time-out, mais aire nette négligeable) |
| **Bras-Panon** | type 02 | +243 m² | **0** |

**Conclusion honnête, chiffres stabilisés** : le document GPU a **réellement changé** (un EBC de
~20 ha a été redessiné/déclassé à Saint-Joseph, essentiellement sur du non-bâti), mais l'impact
**matériel** sur la constructibilité est **modeste et concentré à Saint-Joseph : ~6 parcelles
(EBC) + 2 (ER)** ; **Bras-Panon : négligeable**. Mon LOT 1 avait tort sur la méthode (aire
globale, ajouts seuls) ; la vérité se situe entre mes deux estimations : **pas « 2 parcelles »
par chance, pas « des milliers » par artefact, mais ~8 parcelles réellement concernées, à
Saint-Joseph**.

Cela n'enlève rien à l'ARRÊT : la preuve exigée (diff = exactement +1/+1/+1) n'est pas atteinte,
et l'ingestion `ingest_gpu_prescriptions` (bbox) ne reproduit pas exactement le GPU (partition) —
à fiabiliser avant tout envoi. **Rien lancé, prod intacte, Mac restauré, q_v25 non lancé.**
