# GABARIT-3D-3 — compte-rendu (finir le Gabarit 3D)

Branche `fix/gabarit-3d-3` (depuis `fix/gabarit-3d-2` = `edb8a5778`). Worktree `~/Desktop/labuse-3d`,
ports API 7290 / front 10090. Un commit par lot. Pas de merge.

---

## LOT 1 — Le losange « rupture à vérifier » — **FAIT**

Le losange (et son libellé, et sa ligne de légende) ne s'affiche **que si le terrain varie d'au moins
1,5 m** sur le segment du bâti (`[d0, d1+3 m]`). En dessous : **rien**. Constante `_RUPTURE_SEUIL_M = 1.5`
(`coupe_svg.py`) ; le drapeau `rupture` gouverne à la fois le losange, le libellé et la légende, donc les
trois disparaissent ensemble.

Test `tests/test_gabarit_scene.py::test_rupture_losange_seuil_1m5` : au-dessus (écart 3,3 m → présent),
en dessous (0,55 m → absent, ni losange, ni libellé, ni légende).

## LOT 2 — Un sol réellement mesuré, pour toute l'île — **FAIT** (couche corrigée, voir « LOT 2 — correction »)

> ⚠️ La première version de ce lot lisait la couche **`HIGHRES`**, qui à La Réunion est le **RGE ALTI 5 m**
> suréchantillonné : relief **en escalier** (marches ~5 m), cotes déplacées. Corrigé en lisant le **LiDAR HD
> natif 0,5 m**. Voir la section **« LOT 2 — correction »** plus bas ; le mécanisme (lecture à la demande,
> copie locale plafonnée, repli, pied véridique) est inchangé.

La coupe ET le maillage lisent le relief **fin de l'IGN**, demandé pour la fenêtre de la parcelle
**à l'ouverture** (`gabarit/sol.py` → `scene.charger_surface_sol`).

| Exigence | Réalisé |
|---|---|
| coupe + maillage en 0,5 m par parcelle | `charger_surface_sol` ; `build_scene` l'utilise pour l'échantillonneur (mesh + coupes) |
| copie locale resservie sans appel extérieur | `data/mnt_hr_cache/hr_<bbox>.tif` (gitignoré) ; cache AVANT tout appel |
| dossier plafonné à 1 Go, LRU | `_evict_lru` écarte les copies au dernier accès le plus ancien ; cap `LABUSE_GAB_SOL_CACHE_MAX` (défaut 2³⁰) |
| délai court + repli | timeout 4 s ; échec → copie si elle existe, sinon **fond 1 m** ; jamais d'écran cassé |
| la vue le dit en clair | `meta.sol_repli` + `meta.sol_message` → pied en ambre |
| pied = ce qui est servi | `maille de 0,5 m · acquisition JJ/MM/AAAA` lue dans la donnée (`lidar_dalle_grille`) |
| aucun secret/clé | WMS GetMap public (`geopf.fr`), aucune clé |

**Preuves** (`scripts/gabarit_3d3_sol_preuve.py`, endpoint `/outils/gabarit/sol/stats`) :
- **Bosse BZ1065 disparue** : coupe B, le MNT sous l'emprise passe de **405,6 m (1 m) à 402,1 m (0,5 m)** ;
  profil plat sous le bâti ; **0 losange « rupture »** (écart < 1,5 m). Cf. `BZ1065_1440x694.png`.
- **10 parcelles hors témoins** (bâties 2–8 bâtiments, nues, dénivelé 0,2 à 66 m) ouvertes **toutes en 0,5 m** :

  | froid médian | chaud médian | 2ᵉ ouverture — appels extérieurs |
  |---|---|---|
  | ~1,1 s | ~0,5 s | **0 / 10** (la copie sert) |

  (une parcelle de montagne, dénivelé 66 m, prend ~29 s — voir « ouvrir aux clients »).
- **2ᵉ ouverture = 0 appel extérieur** : prouvé par le compteur `appels_wms` (wms↓chaud = 0 sur les 10).
- **Repli prouvé en coupant le service** (`LABUSE_GAB_SOL_WMS` injoignable) : parcelle **déjà en copie →
  servie en 0,5 m (`source=copie`)** ; parcelle non cachée → **fond 1 m, `repli=true`**, message en clair.
- Unitaires `tests/gabarit/test_sol.py` : LRU, copie sans appel, repli (sans réseau).

## LOT 3 — Le verdict lu au bon endroit — **FAIT**

`gabarit/builder.py` lisait la table figée `cascade_results` (rail legacy mort) pour le verdict PPR. Il lit
désormais le **run servi** via `served_cascade_lines` (`dryrun_cascade_results` du run épinglé, dédupliqué
+ arbitré), ligne `layer_name='risques'`, comme le reste de l'app. La part ROUGE exclue reste calculée EN
DIRECT (`labuse_ppr_couleur`). Garde `tests/gabarit/test_builder.py::test_gabarit_builder_ne_lit_pas_
cascade_results` : plus aucune requête `FROM cascade_results` dans le Gabarit (vérifié sur tout `gabarit/`).

## LOT 4 — La légende du plan-clé — **FAIT**

À 1440×694 et 1280×720 la légende passait **sous le panneau de la coupe** (plan-clé pleine hauteur +
légende > section haute ; `overflow-y-auto` la coupait). Fix : le **plan-clé rétrécit** (conteneur `flex-1`,
`object-contain`) pour laisser la légende et les titres (`shrink-0`) **toujours visibles** — plan-clé
conservé, rien retiré. Contrôle au harnais `scripts/gabarit_3d3_legende.mjs` : la boîte
`[data-gab3d-legende]` tient **dans la vue** ET **au-dessus de `[data-gab3d-coupe-panneau]`**, 4 entrées.

| taille | avant | après |
|---|---|---|
| 1280×720 | KO (legBottom 432 > coupeTop 392) | **OK** |
| 1440×694 | KO (432 > 366) | **OK** |
| 1440×900, 1920×1080, 2560×1300 | OK | **OK** |

---

## LOT 2 — correction : le relief était faux, maintenant il est juste — **FAIT**

**Constat (tes captures).** Terrain en escalier (paliers plats ~5 m + marches), cotes sur sol dégagé
déplacées d'environ 1 m, pied affirmant « maille de 0,5 m ». La couche lue, `HIGHRES`, n'est pas du 0,5 m
à La Réunion.

**Les faits** (`scripts/gabarit_3d3_faits_sol.py` — même fenêtre de 50 m sur BZ1065, deux couches lues à
0,5 m demandé) :

| Couche WMS | valeurs distinctes (100×100 px) | plus long palier plat |
|---|---|---|
| `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES` (RGE ALTI) | **123** | **4,5 m** (≈ la maille 5 m) |
| `IGNF_LIDAR-HD_MNT_ELEVATION…RGR92UTM40S` (LiDAR HD) | **1 368** (× 11) | fin (0,5 m natif) |

→ `HIGHRES` est **grossier** (RGE ALTI 5 m servi en 0,5 m = marches) ; le **LiDAR HD** est bien natif 0,5 m.
C'est la couche LiDAR HD que nous lisions auparavant (à 1 m), et dont la maille native EST 0,5 m.

**La correction.** `gabarit/sol.py` lit désormais `IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S`
(préfixe de cache `lidarhd05_`). **On garde tout le reste du LOT 2** : lecture à la demande pour toute l'île,
copie locale plafonnée (LRU 1 Go), repli sur le fond 1 m si le service ne répond pas, pied véridique.

**Élément couvert sous l'emprise bâtie** (le seul vrai défaut du LiDAR HD : il voit le toit d'une varangue,
pas le sol dessous). **Sous l'emprise bâtie uniquement**, là où le relief forme une **bosse locale qui
dépasse d'au moins 1,5 m les deux sols voisins et retombe au-delà** (`_COUVERT_SEUIL_M = 1.5`, `coupe_svg.py`),
le profil n'est **pas dessiné comme mesuré** : trait distinct pointillé, libellé **« sol non mesuré sous un
élément couvert »**, **aucune cote accrochée dessus**. Une vraie pente (un côté qui remonte) ne le déclenche
pas (pas de faux positif). Rien d'inventé ailleurs.

**Contrôles ajoutés.**
- **Anti-escalier** — `test_anti_escalier_detecte_les_paliers` : la métrique `palier_max_m` vaut **≥ 2 m sur un
  escalier** (profil type RGE ALTI 5 m → le contrôle « < 2 m » **échoue sur les anciennes captures**) et
  **< 2 m sur un relief naturel fin**.
- **Justesse** (`scripts/gabarit_3d3_justesse.py`) — nouveau relief 0,5 m **vs ancien fond 1 m**, sur sol
  dégagé (intérieur cadastre, hors emprise bâtie) : écart **médian 0,013 m**, p90 ≤ 0,065 m, **≪ 0,30 m**.
  Mesuré sur les **voisinages témoins** — le fond 1 m (`fond_1m.tif`, RGE ALTI) est un fichier **partiel,
  hors-git, limité à ces voisinages**. Sur **12 parcelles de l'île**, le **plus long palier** du LiDAR HD va
  de 1,0 à **3,0 m** (pentes et plateformes naturelles) : **aucune marche ~5 m**, l'escalier a disparu.
- **Pied véridique** : `MNT LiDAR HD IGN · maille de 0,5 m · acquisition JJ/MM/AAAA` (date lue par parcelle :
  BZ1065 14/09/2023, DX0049 18/08/2023, CT0442 16/09/2023).

**Deux finitions (tes captures).**
- **4a — CT0442** : « pente max N % sur 5 m » et les cotes d'altitude ne se chevauchent plus (les cotes
  évitent la **boîte 2D** du libellé de pente, `_cotes` ; 0 chevauchement mesuré). Test
  `test_cote_evite_la_pente_max_5m`, recadrage `CT0442_coupe.png`.
- **4b — plan-clé** : à 1440×694 le plan-clé reste **lisible (texte à l'écran 12,7 px ≥ 11)** ET la légende
  tient entière (plan-clé à **210×108**, légende sur **2 colonnes**) ; les lettres d'axe **A/A′/B/B′** sont
  décalées en dehors du segment et **ne se superposent plus** (cas DX0049). Tests
  `test_plan_cle_lettres_axe_sans_chevauchement` + harnais `gabarit_3d3_legende.mjs` (5 tailles, DX0049 et
  BZ1065 : OK partout).

**Preuves refaites** : `BZ1065_*`, `CT0442_*`, `DX0049_*` à 1440×694 et 1920×1080 + recadrages de coupe
`*_coupe.png` ; `justesse.json`, `legende_after_*.json`.

---

## LOT 5 — Temps d'ouverture borné — **FAIT**

**Constat** : ~29 s sur un dénivelé de 66 m. C'est le MAILLAGE 3D (three.js) qui coûte — ~linéaire en
sommets — pas la coupe ni le réseau.

**Règle appliquée** :
- La **coupe reste toujours en 0,5 m** (sampler step 1) : c'est elle qui porte les cotes.
- Le **maillage 3D s'allège selon la taille du cadre** : 0,5 m → **1 m** → **2 m** (plafond), le plus fin
  qui tient sous ~6 500 sommets (`_step_faces`, `scene.py`). Seules les FACES servies à la visionneuse
  s'allègent ; la coupe et son échantillonneur ne bougent pas.
- Les **cotes d'altitude de la vue 3D viennent du sol 0,5 m**, calculées côté serveur sur les mêmes
  positions que les sommets natifs (`_cote_3d_sol_degage`), **pas du maillage allégé** → identiques quel que
  soit l'allègement. Sur sol dégagé (hors emprise bâtie).
- Le **pied dit ce qui est affiché** : « MNT LiDAR HD IGN · **coupe à 0,5 m · relief 3D allégé à 1 m** (ou
  2 m) · acquisition … » ; si non allégé : « maille de 0,5 m » comme avant.

**Preuve — maillage & cotes** (`scripts/gabarit_3d3_lot5_preuve.py`, `lot5_maillage.json`, 10 parcelles
constructibles) : sommets **médians 28 350 → 3 672** (BZ1065 42 180 → 2 900, BL0111 67 704 → 4 368) ;
**écart de cote 3D avant/après = 0,00 m** sur les 10 (les cotes viennent du sol 0,5 m).

**Preuve — ouverture navigateur** (`scripts/gabarit_3d3_ouverture.mjs`, `lot5_ouverture.txt`, WebKit, clic →
1ʳᵉ image, hors réseau, process préchauffé) :

| parcelle | sommets | maille 3D | ouverture |
|---|---|---|---|
| BZ1065 (la lente) | 2 900 | 2 m | **1,96 s** |
| CZ0589 | 2 346 | 2 m | 1,28 s |
| AP1022 | 2 112 | 2 m | 1,28 s |
| DX0049 | 1 960 | 2 m | 1,18 s |
| AW2362 | 5 520 | 1 m | 1,94 s |
| CW1762 | 5 056 | 1 m | 1,61 s |
| HE0412 | 3 922 | 1 m | 1,38 s |
| EX0029 | 3 672 | 1 m | 1,20 s |
| CT0442 | 2 806 | 1 m | 1,02 s |

→ **les 9 parcelles constructibles ouvrent sous 2 s** (toutes < 3 s). BZ1065, qui tenait ~5 s en 0,5 m,
ouvre en **1,96 s** à 2 m, **cotes identiques** (409,8 / 396,6 m avant comme après).

**Limite honnête** : l'allègement est plafonné à 2 m. Une parcelle immense (cadre > ~250 m, ex. une emprise
foncière publique non bâtie) peut dépasser 3 s même à 2 m — ce sont des cas non constructibles (sans bouton
3D). Les parcelles **constructibles** mesurées restent toutes sous 3 s.

**Contrôles** : `test_step_faces_allege_selon_taille` (0,5 → 1 → 2 m, plafonné),
`test_faces_allegees_moins_de_sommets_coupe_inchangee`.

---

## Finitions avant merge — **FAIT**

1. **Élément couvert (BZ1065).** Sous l'emprise bâtie, la varangue n'est **plus tracée** : un trait pointillé
   **droit** relie les deux sols voisins (de la dernière cote au sol avant à la première après), **un seul**
   libellé « sol non mesuré sous un élément couvert », **pas de losange** de rupture sur cette portion (elle
   est déjà expliquée), **aucune cote** dessus (le « haut » qui tombait sur la dalle est écarté). Le **maillage
   3D** non plus ne montre la bosse : elle est aplanie au sol voisin (`_sol_sans_bosses_couvertes`, sommets
   sous l'emprise BZ1065 ramenés de 405,7 m à ≤ 402,3 m). La coupe et les cotes gardent le sol réel.
2. **Plan-clé.** Il **remplit** la place disponible (créneau `flex-1` + SVG demandé à son format → plus de vide,
   texte ≥ 11 px) : **74 %** de la hauteur du panneau à 1440×694, **83 %** à 1920×1080. La légende reste sur
   **une colonne** quand la hauteur le permet, **deux** seulement si le panneau est court (libellés courts →
   jamais coupés en deux lignes). Chaque lettre **A/A′/B/B′** est posée **au bout de son axe** (décalée le long
   de l'axe, pas rejetée au loin).
3. **Date d'acquisition.** Elle vient de la **grille des dalles LiDAR HD** (champ `date_fin`), affichée avec sa
   source dans le pied (« … · acquisition JJ/MM/AAAA · dalle LiDAR HD »). Si la fenêtre couvre **plusieurs**
   acquisitions, le pied montre la **plage** (« acquisitions du … au … »). L'ancien « 12/08/2023 » venait du
   fond 1 m (RGE ALTI), produit différent.
4. **Titre sans adresse (CT0442).** Titre « **Parcelle CT 0442** » (section + numéro), sous-titre = identifiant —
   plus de doublon identifiant/identifiant.
5. **Cote à chaque entrée de limite.** L'aperçu de la coupe réaffiche **une cote à chaque limite** traversée
   (rôle `limite` réintégré), en plus de la voie et du haut/bas — comme avant.

**Contrôles ajoutés** (`scripts/gabarit_3d3_finitions.mjs`, `finitions.json`) : (1) **aucun libellé de la coupe
ne chevauche un autre** (échouait sur l'ancienne BZ1065 : « Rupture » + « sol non mesuré » superposés, et cotes
jointives) ; (2) **le plan-clé occupe ≥ 2/3 de la hauteur** disponible ; (3) les **lettres d'axe** ne se
chevauchent pas. Les 3 parcelles × 2 tailles : **tous OK**. Tests Python : `test_sol_non_mesure_sous_element_couvert`
(bosse non tracée, trait droit, un libellé, pas de losange, pas de cote), `test_cote_evite_la_pente_max_5m`,
`test_plan_cle_lettres_axe_sans_chevauchement`.

---

## Captures (entières)
- **BZ1065** : `BZ1065_1440x694.png`, `BZ1065_1920x1080.png` (sol 0,5 m, bosse partie, légende entière,
  pied « maille de 0,5 m · acquisition 14/09/2023 »).
- **Deux des dix parcelles** : `DX0049_*` (bâtie en pente, acq. 18/08/2023), `CT0442_*` (nue en pente,
  acq. 16/09/2023), à 1440×694 et 1920×1080.
- LOT 4 avant/après : `BZ1065_1440x694_before.png` / `_after.png`, `BZ1065_1920x1080_before.png` / `_after.png`.

## Ce qui resterait pour ouvrir cette vue aux CLIENTS

La vue reste **pilote ADMIN** (`_exiger_admin`). Avant de l'ouvrir aux clients :

1. **Performance (traitée au LOT 5).** Le maillage 3D est désormais **allégé selon la taille** (0,5 → 1 → 2 m)
   → les parcelles constructibles ouvrent **sous 2 s** (cf. LOT 5). Reste un plafond à 2 m : une emprise
   immense (non constructible, sans bouton 3D) peut dépasser 3 s — un niveau de détail serveur ou un
   pré-calcul lèverait ce dernier cas si on voulait l'ouvrir.
2. **Cache mutualisé.** Le cache (`data/mnt_hr_cache/`, 1 Go) est **local au process** ; en prod multi-worker
   il faut un cache partagé (volume commun) ou **pré-ingérer l'île en 0,5 m** (~37,5 Go, estimé) pour un
   premier accès toujours chaud. Le plafond 1 Go est à relever pour un usage insulaire.
3. **Dépendance WMS IGN.** Le repli couvre les pannes, mais la latence du **premier** accès (froid) et les
   quotas IGN restent un risque client → pré-chauffe / ingestion ou CDN interne.
4. **Dé-gating + UX.** Retirer l'`_exiger_admin` (ou auth client), nettoyer le pied « Détails techniques —
   scène … » (orienté dev), états d'erreur/chargement soignés, responsive, et une entrée produit claire.
5. **Fond photo & autres calques** déjà en place (pilote) à valider côté client.

Hook vert, branche poussée, non mergée.
