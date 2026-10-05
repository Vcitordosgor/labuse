# SDP-VERIF-1 — la SDP restante déduit-elle le bâti existant ?

**Mandat** (Vic, 06/10/2026) · branche `audit/sdp-verif-1` · worktree `~/Desktop/labuse-sdpverif` · **lecture seule** (aucun run, aucun recalcul, aucune écriture ; 0 transaction *idle-in-transaction* en fin ; seul ce rapport + le harnais sont commités).

Constat de départ sur `97410000AT1066` (22 Chemin Prevoisy, Saint-Benoît, zone Ub, 9 054 m², 11 bâtiments) : la fiche annonce **« 5 050 m² »** de SDP restante **et** **« 29 % »** d'emprise bâtie. Deux doutes : (a) le chiffre déduit-il la SDP du bâti existant ? (b) le libellé laisse-t-il croire à du terrain libre ?

Harnais rejouable : `docs/audit-2026-10/SDP-VERIF-1/sdpverif_dump.py` (appelle directement `parcel_faisabilite`, `compute_residuel`, `faisabilite_scenario`, `_potentiel_transformation_block`, lit la vue servie `parcel_residuel` — tout en lecture seule).

---

## 0. En un paragraphe

**Oui, le bâti existant est déduit.** Le chiffre servi partout au client (vignette listing/carte, tuile « SDP restante » de la fiche, encart Analyse LABUSE, Dossier, Copilote) est **le scénario « bâti conservé »** — `sdp_residuelle = max(0, SDP_max − SDP_bâti_existant)`, calculé à `src/labuse/faisabilite/residuel.py:206`. Pour AT1066 : 8 580 − 3 530 = **5 050 m²**. Le bâti pèse **3 530 m²** et il EST retranché. Le scénario « terrain libéré » (8 580 m², bâti rasé) n'apparaît **que** dans l'outil Faisabilité, explicitement étiqueté « bâti rasé / démolition à chiffrer ». **Le chiffre est juste.** Le seul vrai problème est le **libellé** : « SDP restante » / « droits à bâtir dormants » sur une parcelle visiblement bâtie peut se lire comme du terrain libre à bâtir, alors qu'il s'agit de la SDP qu'on peut **encore ajouter en gardant** le bâti.

---

## 1. Le calcul, étape par étape (les 9 lignes du moteur)

Le moteur (`faisabilite/engine.py`) construit l'enveloppe, puis `residuel.py` retranche le bâti. Chaîne réelle :

```
surface → zone d'implantation (après reculs) → emprise au sol max PLU
        → emprise constructible retenue = min(impl, PLU)
        → × occupation du gabarit (0,45) = emprise bâtie modélisée
        → × niveaux = SDP théorique (enveloppe)
        → − SDP du bâti existant  ← LA DÉDUCTION (residuel.py:206)
        → = SDP restante servie
```

### Témoin 1 — `97410000AT1066` (le cas de Vic · Saint-Benoît · **Ub** · non calibré → badge *Estimé*)

| # | Étape | Valeur | Source / formule |
|---|-------|--------|------------------|
| 1 | Surface parcelle | **9 054 m²** | cadastre |
| 2 | Zone d'implantation (après reculs) | 6 355 m² | moteur gabarit (reculs par côté) |
| 3 | Emprise au sol max PLU (80 %) | 7 243 m² | `emprise_sol_pct` Ub = 80 % → 9 054 × 0,80 |
| 4 | **Emprise constructible retenue** | **6 355 m²** | `min(impl 6 355 ; PLU 7 243)` → bornée par les reculs |
| 5 | Hauteur / niveaux | 9 m · **R+2 (3 niv.)** | PLU (hé) |
| 6 | Emprise bâtie modélisée (occupation 45 %) | 2 860 m² | 6 355 × 0,45 |
| 7 | **SDP théorique (enveloppe)** | **8 580 m²** | 2 860 × 3 niveaux |
| 8 | **SDP du bâti EXISTANT** | **3 530 m²** | emprise bâtie 1 858 m² × **2 niv. (égout LiDAR)** × 0,95 |
| 9 | **SDP restante servie** | **5 050 m²** | **8 580 − 3 530** (`residuel.py:206`) |

Déductions amont (reculs) : intégrées à l'étape 2/4. PPR rouge / emplacement réservé / pleine terre : **aucun sur cette parcelle** (`cause=None`, `exigu_raison=None`). Si présents, ils videraient l'assiette U/AU en amont (chemin `terrain_exigu`), pas à l'étape 8.

➡️ **La SDP du bâti existant est-elle soustraite ? OUI — à l'étape 9 (residuel.py:206).**

### Témoin 2 — `97411000BZ1065` (Saint-Denis · **Uh** · calibré · 2 bâtiments)

| # | Étape | Valeur |
|---|-------|--------|
| 1 | Surface | 1 625 m² |
| 4 | Emprise constructible | 487 m² |
| 5 | Niveaux | R+0 (1 niv.) |
| 7 | SDP théorique | 219 m² |
| 8 | **SDP bâti existant** | **183 m²** (193 m² × 1 niv. LiDAR × 0,95) |
| 9 | **SDP restante** | **36 m²** (219 − 183) · *taux emprise 40 % · consommé 84 %* |

➡️ **Bâti soustrait ? OUI (étape 9).** Parcelle presque saturée.

### Témoin 3 — `97416000ES0981` (Saint-Pierre · **Ug** · calibré · 1 bâtiment)

| # | Étape | Valeur |
|---|-------|--------|
| 1 | Surface | 874 m² |
| 4 | Emprise constructible | 437 m² |
| 5 | Niveaux | R+1 (2 niv.) |
| 7 | SDP théorique | 393 m² |
| 8 | **SDP bâti existant** | **209 m²** (220 m² × 1 niv. LiDAR × 0,95) |
| 9 | **SDP restante** | **184 m²** (393 − 209) · *taux emprise 50 % · consommé 53 %* |

➡️ **Bâti soustrait ? OUI (étape 9).**

### Témoin de contrôle — `97416000HX0198` (Saint-Pierre · **Ug** · calibré · **parcelle NUE**, 0 bâtiment)

| # | Étape | Valeur |
|---|-------|--------|
| 1 | Surface | 1 999 m² |
| 7 | SDP théorique | 900 m² |
| 8 | **SDP bâti existant** | **0 m²** (emprise bâtie 0) |
| 9 | **SDP restante** | **900 m²** (900 − 0) |

➡️ **Contrôle validé : sans bâti, SDP du bâti = 0, et les deux scénarios COÏNCIDENT** (terrain libéré = bâti gardé = 900 m²). La déduction est bien un retranchement du bâti réel, pas un rabais arbitraire.

---

## 2. Les deux scénarios : lequel alimente quoi

`faisabilite/scenarios.py` sert **deux** chiffres (code `FAISABILITE-3`) :

| Scénario | Formule | AT1066 | BZ1065 | ES0981 | HX0198 (nu) |
|----------|---------|-------:|-------:|-------:|------------:|
| **`terrain_libere`** (bâti rasé) | SDP enveloppe (bâti = 0), + « surface à démolir » affichée | **8 580 m²** (à démolir 3 530) | 219 (à démolir 183) | 393 (à démolir 209) | 900 |
| **`bati_garde`** (bâti conservé) | **SDP_max − SDP_existante** | **5 050 m²** | 36 | 184 | 900 |

**Ce qui alimente chaque surface client** (tous lisent la vue servie `parcel_residuel.sdp_residuelle_m2` = scénario **`bati_garde`**, bâti déduit) :

| Surface | Champ / source | Valeur AT1066 | Scénario |
|---------|----------------|--------------:|----------|
| Vignette listing (`GET /parcels`) + carte (`/map/parcels.geojson`) | `parcel_residuel.sdp_residuelle_m2` (app.py:3250/3315/3484) — sert aussi `etat_bien` « bati_encore » | 5 050 | **bâti gardé** |
| Tuile « SDP restante » de la fiche | `potentiel_transformation.sdp_residuelle_m2` (app.py:5879, Fiche.tsx:935/1291) | 5 050 | **bâti gardé** |
| Encart Analyse LABUSE / Copilote | tuile `resume_fiche.py:34` → robinet → `potentiel_transformation` | 5 050 | **bâti gardé** |
| Dossier PDF (`miroir.py:1037`, `verdicts.py:100`, `blocs/potentiel.py`) | idem `potentiel_transformation` | 5 050 | **bâti gardé** |
| **Outil Faisabilité (panneau)** | `faisabilite_scenario`, **les deux** présentés | 8 580 **et** 5 050 | les deux, étiquetés |

➡️ **Ils ne se contredisent PAS.** Partout où un seul chiffre est servi au client, c'est le **bâti gardé (déduit)**. Le 8 580 (bâti rasé) n'existe que dans l'outil Faisabilité, à côté du 5 050, avec le libellé explicite « 0 m² (démolition de ~3 530 à chiffrer) » (scenarios.py:317). **Aucune surface ne sert le chiffre qui ne déduit pas le bâti.**

*Note (hors saisie) : le scénario bâti gardé réaligne sa valeur sur la vue servie `parcel_residuel` quand l'utilisateur ne saisit aucune hypothèse (scenarios.py:259, « Golden 55 »), pour qu'outil et fiche disent le MÊME chiffre.*

---

## 3. Le cas de Vic, posé en détail

**D'où vient le « 29 % »** — c'est le **`taux_emprise_pct`** = emprise bâtie **÷ emprise CONSTRUCTIBLE** (pas ÷ la parcelle) :

```
emprise bâtie (BD TOPO + CoSIA, sur l'assiette U/AU) = 1 858 m²
÷ emprise constructible (étape 4)                    = 6 355 m²
= 29,2 %  → « 29 % »
```

⚠️ **Nuance de libellé importante** : les 29 % sont une part de **l'emprise constructible**, pas « 29 % de la parcelle ». Sur la parcelle elle-même, le bâti ne couvre que **1 858 / 9 054 = 20,5 %**. Le code l'étiquette correctement (« Taux d'occupation du gabarit — bâti existant ÷ emprise constructible », ComparePanel.tsx:70) ; le raccourci « de la parcelle » viendrait d'une lecture, pas du produit. Un troisième chiffre coexiste : **`pct_consomme` = 41 %** = SDP existante 3 530 ÷ SDP max 8 580 (fiche « SDP consommée / autorisée », constructibilite.tsx:51). Trois pourcentages, trois dénominateurs — tous justes, aucun n'est « % de la parcelle ».

**SDP attribuée aux 11 bâtiments — méthode :** `emprise bâtie × niveaux LiDAR × coef 0,95`

```
1 858 m² d'emprise bâtie × 2 niveaux (égout LiDAR mesuré 6,1 m → round(6,1/3) = 2)
      × 0,95 (emprise de toit → emprise de plancher, DONNEES-FIX-1 lot C)
= 3 530 m² de SDP existante
```

Les niveaux viennent de **l'égout LiDAR mesuré** (`hauteur_source="lidar"`, survol août 2023), pas d'un placeholder → `niveaux_reels=True`, pas d'estimation de hauteur.

**Passage aux 5 050 m² :** `8 580 (enveloppe) − 3 530 (existant) = 5 050 m²`.

**Cohérence avec le plafond d'emprise du PLU — le calcul demandé :**

```
Emprise constructible max (reculs)            = 6 355 m²
Emprise déjà bâtie                            = 1 858 m²  (29 % → « dormant » : 71 %)
Emprise constructible LIBRE                   = 4 497 m²

Pour réaliser 5 050 m² de SDP à R+2 (3 niveaux) :
  footprint neuf nécessaire = 5 050 / 3       = 1 683 m²   (< 4 497 libres ✔)
  occupation totale = (1 858 + 1 683) / 6 355 = 56 %       (< 80 % réglementaire Ub ✔)
```

➡️ **Cohérent.** On ne mobilise que 1 683 m² des 4 497 m² d'emprise constructible libres, pour une occupation totale de 56 % — sous le plafond réglementaire de 80 %. Le 5 050 m² tient dans l'enveloppe.

**Limite connue (honnête, non bloquante) :** l'enveloppe greenfield (8 580) suppose une occupation du gabarit de **45 %** (`coef_occupation`, pour accès/espacements), alors que le résiduel bâti-gardé tolère ici **56 %**. La soustraction se fait en SDP, pas en emprise : elle « récupère » le niveau manquant du bâti existant (2 niv. constatés vs 3 modélisés) et le réaffecte à du neuf. Le 5 050 est donc **un peu optimiste vis-à-vis de l'hypothèse d'occupation du greenfield lui-même**, mais **reste légal** (56 % < 80 %) et **conservateur en SDP** (5 050 < 8 580). Ce n'est pas un bug : c'est la nature de la soustraction en espace-SDP, et le code a d'ailleurs choisi `coef_sdp_existante = 0,95` (proche de 1) précisément pour **ne pas** surévaluer l'existant déduit et donc ne pas gonfler le résiduel.

---

## 4. Verdict

> **Le chiffre est juste.** Le bâti existant est bien déduit — 3 530 m² retranchés à l'étape 9 (`residuel.py:206`) ; les 5 050 m² servis partout au client sont le scénario **bâti conservé** (`parcel_residuel`), jamais l'enveloppe greenfield de 8 580 m². Le résiduel tient dans le plafond d'emprise du PLU (56 % < 80 %). Vérifié identiquement sur 3 témoins bâtis (déduction effective) et 1 témoin nu (les deux scénarios coïncident). Le doute de Vic — « est-ce que ça déduit le bâti ? » — se lève : **oui.**

### Le vrai problème : le libellé (il laisse croire à du terrain libre)

Le chiffre est bon mais son habillage peut tromper sur une parcelle visiblement bâtie. **Libellés à reformuler** (« SDP de plancher constructible restante, bâti conservé » plutôt que « droits à (construire/bâtir) restants/dormants »). **Aucun n'est modifié dans cette phase — liste pour décision de Vic :**

| Fichier:ligne | Libellé actuel | Surface |
|---------------|----------------|---------|
| `src/labuse/api/app.py:5886` | **« Potentiel modéré — droits à bâtir partiellement dormants »** | verdict §10 fiche (le libellé vu par Vic) |
| `src/labuse/api/app.py:5884` | « Fort potentiel — parcelle en forte sous-densité » | verdict §10 (pct < 40) |
| `src/labuse/exports/verdicts.py:100` | « SDP résiduelle **(droits à bâtir non consommés)** ≈ … » | Dossier PDF §10 |
| `src/labuse/cascade/layers/etage0_ext.py:174` | « SDP résiduelle non calculée — **droits à construire** inconnus » | bande Analyse LABUSE (motif) |
| `frontend/src/components/fiche/Fiche.tsx:935` et `:1291` et `:1914` | tuile **« SDP restante »** (+ infobulle « …que le PLU autorise ENCORE sur la parcelle ») | tuile bandeau + §10 |
| `frontend/src/components/fiche/Fiche.tsx:1912` | « … m² **de SDP résiduelle** » (verdict) | encadré verdict §10 |
| `src/labuse/copilote_v2/resume_fiche.py:34` | tuile **« SDP restante »** | bandeau Analyse LABUSE / Copilote |
| `src/labuse/exports/miroir.py:1037` | tuile **« SDP restante »** | bandeau du Dossier |
| `frontend/src/components/compare/ComparePanel.tsx:63` | « SDP résiduelle · {périmètre} » | panneau Comparer |

**Reformulation proposée** (inchangée ici) : remplacer « droits à bâtir/construire restants/dormants » par **« surface de plancher constructible restante (bâti conservé) »**, et compléter l'infobulle de la tuile « SDP restante » par « — en gardant les bâtiments existants ; pour le potentiel après démolition, voir l'outil Faisabilité ». Le mot clé qui manque partout est **« bâti conservé »** : il distingue sans ambiguïté le 5 050 (bâti gardé) du 8 580 (table rase).

### Correctif de précision secondaire (non bloquant)
Partout où le `taux_emprise_pct` (29 %) est présenté, s'assurer qu'il est dit **« de l'emprise constructible »** et jamais **« de la parcelle »** (sur la parcelle : 20,5 %). Le code actuel l'étiquette correctement (ComparePanel.tsx:70) ; à vérifier sur la carte/popup si une formulation « de la parcelle » y apparaît.

---

## Annexe — reproduire

```bash
cd ~/Desktop/labuse-sdpverif
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
export PYTHONPATH="$PWD/src"
~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/SDP-VERIF-1/sdpverif_dump.py \
    97410000AT1066 97411000BZ1065 97416000ES0981 97416000HX0198
```

Faits-clés vérifiés en base (lecture seule) : AT1066 enveloppe 8 580 m², bâti existant 1 858 m² × 2 niv. LiDAR × 0,95 = 3 530 m², résiduel servi **5 050 m²** = vue `parcel_residuel` = scénario bâti gardé ; taux emprise 29 % (= 1 858/6 355), consommé 41 % (= 3 530/8 580), bâti/parcelle 20,5 %. Les quatre témoins concordent ; 0 transaction *idle-in-transaction*.
