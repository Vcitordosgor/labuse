# Audit court — Données LiDAR HD · Historique des propriétaires

- **Branche** : `audit/donnees-lidar-proprio` (depuis `main` `8e5f3ee9`) · worktree `~/Desktop/labuse-lidar`
- **Nature** : lecture seule. Aucune donnée, aucun affichage, aucune ingestion modifiés.
- **DB** : `postgresql://openclaw@localhost:5432/labuse` (lecture). Pas de CARTE-VITESSE-2 en cours au lancement.
- **Captures** : API 8505 / front 5705 lancés puis **arrêtés** (ports vérifiés libres). 3 captures sous `docs/audit-2026-09/captures/`.
- **Date** : 2026-09-25.

> **Deux prémisses du mandat sont fausses, à corriger dans la tête du lecteur.**
> 1. « 30 % n'ont rien » en LiDAR → en réalité **92 %** des parcelles bâties sont couvertes ; le manque (8 %) est du micro-bâti, pas un trou de territoire.
> 2. « Nature du toit : 36 % classés » → il n'y a **que 31 parcelles** classées en base ; « 36 % » est le *taux de classement annoncé* de l'analyse à la demande, pas une couverture.

---

## 1. LiDAR HD

### 1.1 Ce qu'on a en base

| Table | Lignes | Millésime survol | Ingestion | Contenu |
|---|---|---|---|---|
| `batiment_hauteur_lidar` | **303 452** | mission unique **23LHDREUNION**, survol **2023-08-11 → 2023-10-11** | 2026-09-10 | `faitage_m`, `egout_m`, `hauteur_bdtopo_m`, `ecart_faitage_bdtopo_m`, `n_cellules`, `date_debut/fin_survol`, `code_mission`, `methode` (=`dalle`), `rnb_id`, `rnb_cause` |
| `toiture_lidar` | **31** | calculé à la demande (`computed_at` 2026-09-05 → 25) | on-demand + cache | `verdict` (double_pente 18 / monopente 12 / croupe_complexe 1), `pente_mediane_deg`, `pans_orientation_deg`, `part_pentue`, `confiance` |
| `lidar_dalle_grille` | **2 665** dalles | idem mission | — | grille 1 km, `url_mnh`+`fait_le` **tous renseignés** (toutes téléchargées), `n_parcelles`/`n_mesurees` |
| `parcel_solar` | 431 663 (île) | — | — | `azimut_bati_deg`, `azimut_confiance` (basse 35,5 % / haute 27,3 %) — **PAS** de nature du toit |

- `faitage_m`, `egout_m` : **100 % renseignés** (303 452). `ecart_faitage_bdtopo_m` : 273 552 (90,1 %) — les ~29 900 sans écart n'ont pas de bâti BD TOPO comparable (dont 4 270 `rnb_cause=aucun_bati_rnb_sur_parcelle`).
- **Calcul** (`hauteur_lidar.py:71-72`) : sur les cellules du MNH (MNS−MNT) dans l'emprise bâti — **faîtage = p99** (haut de distribution, robuste au bruit), **égout = p25** (bord de toit).
- Une seule mission, une seule date de survol : pas de multi-millésime à gérer.

### 1.2 Couverture

- **303 452 / 329 315 parcelles bâties** (`p_model_bati`) = **92,1 %**. 25 863 sans LiDAR (7,9 %). 0 ligne LiDAR hors parcelle bâtie (contenance parfaite).
- **Uniforme** sur les 24 communes : de 86,1 % à 92,2 % — aucune commune pleine, mais **aucun trou géographique concentré**. La perte est systémique, pas régionale.
- **Cause des trous** : les parcelles sans LiDAR ont une **emprise bâtie médiane de 13 m²** (moyenne 55) contre **213 m²** (moyenne 327) pour les couvertes. Ce sont des **micro-bâtis** (abris, édicules, polygones de bruit) sous le seuil de mesure ou en bord de dalle. **Pas** des dalles manquantes (toutes téléchargées), **pas** un filtre volontaire large, **pas** l'absence de BD TOPO.
- Dans les dalles téléchargées : 303 432 / 304 161 parcelles mesurées (**99,76 %**) — le pipeline mesure quasiment tout ce qu'il voit.
- **Le reste est-il récupérable ?** La mission 23LHDREUNION couvre déjà **toute l'île** (2 665 dalles ≈ surface de la Réunion ; 1 036 dalles sans bâti = mer/relief). Les 25 863 manquantes sont surtout du micro-bâti sans valeur promoteur ; les dalles sont **déjà en base**, donc re-mesurer coûterait quasi rien mais rapporterait peu.

### 1.3 Est-ce juste ?

- **Distribution de l'écart faîtage vs BD TOPO** : médiane **0,90 m**, p90 **3,80 m**, moyenne 1,40 m. `> 3 m` = **43 406 (15,9 %)** des comparables (seuil du badge « Sources discordantes »). `> 5 m` = 11 191. **Seulement 2 valeurs aberrantes** (> 100 m : bug d'unité/coord sur 2 parcelles). `faitage ≥ egout` **toujours** (0 inversion) ; `egout` marginalement négatif au pire (−15,7, résiduel).
- **Constat central** : sur les 43 404 écarts > 3 m, **100 % ont le faîtage LiDAR PLUS HAUT que BD TOPO ; 0 l'inverse.** Et l'**égout LiDAR ≈ hauteur BD TOPO** (écart moyen +0,55 m, médian 1,20 m). → La « discordance » n'est pas une erreur : **BD TOPO stocke une hauteur proche de l'égout, le LiDAR mesure le faîtage.** Sur un toit en pente ou un R+n, les deux ont raison — sur deux grandeurs différentes.
- **15 cas tirés au hasard parmi les > 3 m** (tous `faitage > bdtopo`, `egout ≈ bdtopo`) :

| IDU | faîtage | égout | BD TOPO | écart | lecture |
|---|---|---|---|---|---|
| 97416000CW1762 | 7,8 | 4,7 | 4,5 | 3,3 | égout=BD TOPO → LiDAR juste sur le faîtage |
| 97408000AP1022 | 18,9 | 13,2 | 13,7 | 5,2 | immeuble ; BD TOPO ≈ égout |
| 97408000BN0094 | 11,5 | 9,1 | 8,2 | 3,3 | idem |
| 97410000AT0689 | 7,3 | 3,4 | 3,9 | 3,4 | égout≈BD TOPO |
| 97412000BO0354 | 10,2 | 8,6 | 5,3 | 4,9 | égout>BD TOPO : BD TOPO sous-estime |
| 97417000AY0252 | 5,1 | 2,6 | 2,0 | 3,1 | pavillon en pente |
| 97415000EO0368 | 6,7 | 4,3 | 3,2 | 3,5 | — |
| 97412000BW0326 | 5,7 | 2,4 | 2,2 | 3,5 | — |
| 97411000IE0153 | 6,3 | 3,2 | 1,9 | 4,4 | BD TOPO très basse |
| 97414000HH0026 | 6,3 | 2,5 | 2,1 | 4,2 | — |
| 97403000AP2044 | 5,6 | 3,5 | 2,4 | 3,2 | — |
| 97414000DN0333 | 10,9 | 6,5 | 7,7 | 3,2 | égout≈BD TOPO |
| **97408000AN1789** | **13,6** | **3,2** | 4,5 | **9,1** | **span faîtage-égout énorme → à surveiller (végétation/objet possible sur le p99)** |
| 97418000AT0387 | 5,4 | 2,4 | 0,2 | 5,2 | BD TOPO quasi nulle (bâti mal renseigné amont) |
| 97412000CX0763 | 7,1 | 3,7 | 3,9 | 3,2 | égout=BD TOPO |

- **BZ1065** (cas ancré du mandat, capture 01) : faîtage **10,3** m · égout 3,6 m · BD TOPO **4,2** m · écart 6,1 m — bâtiment R+2/R+3, **le LiDAR a raison** ; BD TOPO (4,2 ≈ égout) est le point bas. Confirmé par FICHE-AUDIT-2.
- **Nature du toit** : **31 parcelles** classées, point. Le « 36 % » vient du **texte de méthode** servi (`toit.methode`) : « confiance ≥ 0,70… 0 faux au seuil, **36 % des toits classés** ; non déterminée sinon ». C'est le **taux de classement de l'analyse à la demande** (visite fiche / outil solaire), cachée dans `toiture_lidar` — **pas** un pré-calcul île entière. D'où « quasi rien » de disponible hors des parcelles déjà visitées.

### 1.4 Où c'est affiché (tous les lecteurs)

Point de lecture unique : **`hauteur_lidar_servie()`** (`hauteur_lidar.py:164`, lit `batiment_hauteur_lidar`). Consommateurs :

| Lecteur | Fichier | Lit | Valeur = fiche ? |
|---|---|---|---|
| Fiche Bâti « Le bien » | `bati.py:le_bien_block` → `leBien.tsx` | faîtage+égout+écart+survol+badge discordance+nature toit | référence — **capture 01** |
| Potentiel « Marge en hauteur » / surélévation | `app.py:5320` scenario → `surelevation_mesuree` → `constructibilite.tsx` | faîtage/égout mesurés vs règle | **oui** (10,3 / 4,2 identiques) — **capture 03** |
| Gabarit 3D (extrusion) | `gabarit.py:43`, `app.py:6040` | `faitage_m` | oui |
| Solaire pente/nature | `solaire_toiture.py` → `ProspectionSolaire.tsx` | `toiture_lidar` verdict+pente | oui (cache) |
| Scoring | `score_labuse.py:289` (JOIN) | hauteur | oui |
| Exports PDF | `bati.py:le_bien_block` | tous les champs | oui |

→ **Cohérent** : tous passent par le point unique. Vérifié en direct : fiche Bâti 10,3 m = Potentiel 10,3 m.

### 1.5 Ce qu'on ne fait pas encore

- **La hauteur LiDAR n'entre PAS dans la capacité / SDP** (FICHE-AUDIT-2 confirmé, capture 03) : pour BZ1065, la capacité affiche **R+0, SDP 292 m², 2-3 logements** — calculée sans tenir compte du bâti existant mesuré à 10,3 m (R+2/R+3). Le LiDAR ne sert qu'à « marge en hauteur » (surélévation), pas à déduire l'existant.

| Usage possible | En base ? | Valeur promoteur | Coût |
|---|---|---|---|
| **Niveaux existants** = faîtage / ~3 m → R+n | oui (`faitage_m`) | fort | faible (dérivation) |
| **SDP existante** ≈ emprise × niveaux → **résiduel réel** | oui (`faitage_m` + `emprise_bati_m2`) | **très fort** (corrige la surestimation de capacité sur parcelles bâties) | moyen (brancher dans le moteur résiduel) |
| Surélévation possible (marge = règle − faîtage) | déjà branché | moyen | fait |
| Volume bâti (emprise × hauteur) | oui | moyen | faible |
| Ombrage (MNS voisins) | dalle en base, non exploité | faible-moyen | élevé |
| Végétation haute (MNH hors emprise bâti) | dalle en base, non exploité | faible | élevé |

---

## 2. Historique des propriétaires

### 2.1 Ce qu'on a en base

| Table | Millésimes réels | Lignes | Rôle |
|---|---|---|---|
| `pm_proprietaires_millesimes` | **2019, 2020, 2021, 2022, 2023, 2024** (pas 2025) | 72 709 → 81 161 / an | historique PM versionné (DGFiP, situation 1ᵉʳ janvier) |
| `parcelle_personne_morale` | **2025** seul | 82 701 | snapshot servi (courant) |
| `dvf_mutations_parcelle` | 2021 → 2025 | 102 551 | ventes récentes |
| `dvf_mutations_histo` | 2014 → 2020 | 110 477 | ventes archives |

- **Chaîne 2019 → 2025 complète** : `historique.py` (_TIMELINE_SQL) fait l'UNION `pm_proprietaires_millesimes` (2019-24) + `parcelle_personne_morale` (2025). Aucun millésime manquant.
- **Jointure** : `idu` (14 c.), `SIREN` (9 chiffres), et **pseudo-SIREN « U… »** quand la DGFiP n'a pas résolu le SIREN.
- **Personnes physiques** : rien de nominatif (doctrine RGPD — ces fichiers ne portent que des PM). Mais **DVF permet de dire « la parcelle a changé de mains », datée**, sans nom : ventes de 2014 à 2025. Ex. CH1970 (personne physique, aucune PM) : seule trace = DVF, vente 2025-12-31, 123 000 € (⚠ date 31/12 = souvent « millésime seul connu »).

### 2.2 Est-ce juste ? — 5 parcelles témoins (chaîne 2019→2025 lue en base)

| Témoin | 2019 | 2020 | 2021-2025 | DVF | Lecture |
|---|---|---|---|---|---|
| **CBO Territoria SA** `97415000BI0007` | 452038805 | 452038805 | 452038805 | 0 | propre, stable |
| **SIDR SEM** `97411000BH0119` | 310863592 | 310863592 | 310863592 | 0 | propre, stable |
| **SCI Laurent Grandpre** `97411000CD1214` | SIREN **NULL** | pseudo **U23719996** | réel **483339628** | 0 | **2 faux « changements »** (capture 02) |
| **ONF** `97415000AB0001` | pseudo **U15960284** | pseudo U15960284 | réel **662043116** | 0 | **1 faux « changement »** (2020→2021) |
| **CH1970** `97414000CH1970` | — (aucune PM) | — | — | vente 2025-12-31 | personne physique : histoire = DVF seule |

- **Faux-positifs de changement** : `historique()` (`proprietaire_historique.py:67-70`) diffère sur le **SIREN brut** : `(a or "") != (b or "")`. Il **ne filtre pas** les pseudo-SIREN « U… » ni la complétude SIREN croissante des premiers millésimes. Résultat, la **fiche §Identité affiche des changements de propriétaire qui n'ont jamais eu lieu** :
  - SCI Laurent Grandpre : « 2019 → 2020 : SCI LAURENT GRANDPRE → SCI LAURENT GRANDPRE » (**dénomination identique** !) et « 2020 → 2021 : U23719996 → 483339628 » — même entité tout du long (capture 02).
  - ONF : « 2020 → 2021 : U15960284 → 662043116 » — même Office.
- **Incohérence entre écrans sur la même donnée** : la **frise « Remonter le temps »** (`moteurs.py:445-456`), elle, détecte « U… » → « Propriétaire PM non identifiable » et **n'affirme aucun changement**. La frise est prudente, la fiche §Identité ne l'est pas (le correctif E3 de REMONTER-TEMPS-2 n'a été appliqué qu'à la frise).
- Trous restants : (1) SIREN NULL / pseudo « U… » anciens ; (2) changement de dénomination sans changement de SIREN (cosmétique, ex. « SCI LAURENT GRANDPRE » ↔ « LAURENT GRANDPRE ») ; (3) **fusion-absorption** = vrai changement de SIREN, non distingué d'une vente.

### 2.3 Où c'est affiché

| Écran | Table(s) / millésime | Cohérence |
|---|---|---|
| Fiche §Identité (historique) | `pm_millesimes` 2019-24 + `pm_morale` 2025 | ⚠ traitement pseudo-SIREN non filtré (2.2) |
| Remonter le temps (frise) | même union + DVF + Sitadel + DFI | pseudo-SIREN **filtré** (prudent) |
| Scan patrimoine | `parcelle_personne_morale` 2025 seul | courant, cohérent |
| Acquisitions récentes (Communes + Étude Zone) | `pm_millesimes` diff millésimes consécutifs | cohérent |
| Blocs fonciers / Successions | `parcelle_personne_morale` 2025 | courant, cohérent |

→ **Pas de divergence de millésime** entre écrans (courant = 2025, historique = 2019-2025 affichés explicitement). La seule divergence est le **traitement du pseudo-SIREN** (frise vs fiche).

### 2.4 Ce qu'on ne montre pas encore

| Usage possible | En base ? | Valeur promoteur | Coût |
|---|---|---|---|
| **Ancienneté de détention** = 2025 − 1ᵉʳ millésime au même SIREN | oui | **fort** (détention longue = vendeur potentiel) | faible |
| Vue timeline **unifiée PM + ventes DVF** datée dans la fiche | oui (2 blocs déjà, séparés) | fort | moyen |
| « La parcelle a changé de mains » pour personnes physiques via DVF (daté, sans nom) | oui (DVF) | moyen | faible |
| Motif du changement (vente / succession / fusion-absorption) | partiel | moyen | élevé |

---

## 3. Verdict

**LiDAR HD — complet, juste, bien montré, mal exploité.** La couverture est **92 %** (pas 70 %), uniforme, et le manque est du micro-bâti sans enjeu ; la mission unique 23LHDREUNION couvre déjà l'île. Les hauteurs sont justes : la seule « discordance » (16 % à > 3 m) est un artefact de définition — le LiDAR mesure le faîtage (p99), BD TOPO ≈ l'égout (100 % des écarts vont dans ce sens, 2 vraies aberrations sur 273 552). Tous les écrans lisent la même valeur via un point unique. Le vrai manque est en aval : la hauteur ne sert pas encore à déduire l'existant (niveaux, SDP), donc la capacité surestime le résiduel sur les parcelles bâties. La nature du toit n'existe qu'à 31 parcelles.

- **R1 (fort)** : injecter le faîtage LiDAR dans la capacité (niveaux existants → SDP existante → résiduel réel). Corrige la surestimation sur parcelles bâties.
- **R2 (moyen)** : recadrer le badge « Sources discordantes » — ce n'est pas une erreur mais faîtage vs égout ; ne flagger que les vrais suspects (span faîtage-égout anormal / `n_cellules` faible, ex. AN1789).
- **R3 (moyen)** : pré-calculer la nature du toit en batch île entière ; sinon le solaire reste vide pour 99,99 % des parcelles.

**Historique propriétaires — complet et cohérent, mais un constat faux à corriger.** Les millésimes PM 2019→2025 sont tous présents, DVF couvre 2014→2025, les écrans lisent la bonne table au bon millésime, et la doctrine RGPD tient (PM seules, DVF datée sans nom pour les physiques). **Le défaut central** : la fiche §Identité affiche des « changements de propriétaire » qui n'existent pas (pseudo-SIREN « U… » → SIREN réel, ou SIREN manquant en début d'historique), là où la frise, elle, les neutralise déjà. Sur 5 témoins, 2 (SCI, ONF) exhibent ce faux-positif.

- **R1 (fort)** : filtrer pseudo-SIREN « U… » et complétude SIREN croissante dans `historique()` — aligner la fiche §Identité sur la frise, supprimer les faux changements.
- **R2 (fort)** : afficher l'**ancienneté de détention** (années au même SIREN depuis le 1ᵉʳ millésime) — signal de prospection direct, quasi gratuit.
- **R3 (moyen)** : timeline unifiée PM + ventes DVF datée dans la fiche.

---

## 4. Hors mandat (non fait)

Aucun téléchargement de dalle, aucune correction de donnée, aucune touche à l'affichage, aucun merge. API/front arrêtés après captures.
