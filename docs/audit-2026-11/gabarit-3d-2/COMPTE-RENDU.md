# GABARIT-3D-2 — compte-rendu

Branche `fix/gabarit-3d-2` (base `origin/main`). Worktree `~/Desktop/labuse-3d`, ports API 7290 / front 10090.

---

## LOT A — Le sol près du bâti (lecture seule, aucun code applicatif modifié)

Témoin : **BZ1065** (`97411000BZ1065`, Saint-Denis), coupe B « orientée par la voie ». La coupe B monte
de ~402 m à **405,6 m au bord du bâti** (d ≈ 68→84 m, sommet à d = 80,5 m) puis retombe à ~402 m, ce qui
correspond exactement au signalement (402,3 → 405,7 → 402,3). Mesures reproductibles :
`scripts/gabarit_3d2_sol_bati.py` (A1/A2) et `scripts/gabarit_3d2_rupture_prevalence.py` (A4).

### A1 — La bosse est-elle dans la donnée IGN, ou créée par notre interpolation ?

**Elle est DANS la donnée IGN (MNT LiDAR HD 1 m), pas créée par nous.**

| Mesure (MNT 1 m local, `data/mnt1m/fond_1m.tif`) | valeur |
|---|---|
| MNT au sommet de la bosse (profil app, d = 80,5 m) | **405,62 m** |
| MNT 1 m lu directement au même point (x,y) | **405,64 m** (= profil app) |
| MNT max SOUS l'emprise bâtie | **405,68 m** |
| sol voisin (médiane du MNT, anneau 0–3 m hors emprise) | **401,6 m** |
| écart bosse / sol voisin | **+4,0 m** (≈ 1,5 niveau) |

Le profil servi par l'app (405,62 m) = la valeur brute du MNT 1 m au même point (405,64 m). L'app **ne
crée pas** la bosse : elle échantillonne le MNT tel quel (maillage triangulé, `TerrainMesh.profil`). La
bosse est un pixel « sol » à 405,6 m dans le MNT IGN, +4 m au-dessus du sol alentour.

### A2 — Au sommet de la bosse : MNT vs MNS

**MNT(1 m) ≈ MNS ≈ 405,6 m, alors que le vrai sol (MNT HR 0,5 m) est à 402,0 m → élément COUVERT classé « sol ».**

Au sommet (x = 336 627,8 ; y = 7 689 770,5), relevés WMS LiDAR HD 0,5 m (`geopf.fr`) :

| couche | valeur |
|---|---|
| MNT 1 m (notre fond local) | **405,62 m** |
| MNS 0,5 m (surface) | **405,61 m** |
| MNT HR 0,5 m (sol, produit plus fin) | **402,04 m** |
| sol voisin (A1) | 401,6 m |

→ **MNT(1 m) = MNS** (écart 0,01 m) : notre MNT 1 m a capté la SURFACE, pas le sol. Le MNT HR 0,5 m (sol
propre) dit que le vrai terrain est à **402,0 m** (= le voisinage). L'écart **MNS − sol = +3,6 m ≈ 1 niveau**.
C'est la signature exacte d'un **élément couvert (varangue / auvent / abri)** classé « sol » dans le MNT
LiDAR HD 1 m — l'hypothèse A2 est **confirmée**. (BZ1065 a 4 bâtiments, le sommet tombe sous une emprise.)

### A3 — Calcul du profil sous le bâti ; prend-il ce point haut comme appui ?

**Le profil sous le bâti n'est PAS interpolé par LABUSE : c'est le MNT 1 m brut, échantillonné le long de
l'axe. Et oui, il prend le point haut (405,6 m) comme un point de terrain réel.**

- `scene._construire_coupe` → `_Sampler.profil` → `TerrainMesh.profil` échantillonne le MNT au
  FRANCHISSEMENT des faces du maillage ; la portion dans `[d0, d1]` (emprise) est tracée en pointillé
  (`coupe_svg.py:203`), étiquetée « profil sous le bâti **(interpolé)** ». Le « (interpolé) » renvoie à
  **l'interpolation de l'IGN** (le MNT « terre nue » comble sous le bâti), **pas** à un calcul LABUSE.
- Aucun aplatissement, aucune exclusion des pixels du bâti : le MNT est dessiné tel quel comme « sol ».
- Le seul contrôle (`_batiment_coupe`, `scene.py:369`) vérifie que le MNT **existe** (pas une lacune) aux
  deux façades (±1,5 m, 5 points) → sinon la portion est interrompue. Il ne traite pas le point haut
  spécialement : **la bosse à 405,6 m est prise comme un appui/sommet de terrain légitime.**
- `_rupture_d` (`coupe_svg.py:385`) cherche ensuite la **plus forte pente** dans `[d0, d1+3]` → ici le
  flanc de la bosse (405,6 → 402,2) → le losange « **Rupture du terrain à vérifier** » se pose dessus.

### A4 — Sur 30 parcelles bâties tirées au sort, combien ont une « rupture à vérifier » qui touche une emprise bâtie ?

Reproduction fidèle de l'app (build_scene, axes A/B réels, même `_rupture_d`), MNT alimenté par le MÊME
produit IGN (LiDAR HD MNT 1 m, WMS) fenêtre par parcelle — le fond local ne couvre que 4 témoins.

| mesure | résultat |
|---|---|
| parcelles avec scène exploitable | **30** |
| dont coupe traversant ≥ 1 bâtiment | **28 / 30** |
| **« Rupture du terrain à vérifier » TOUCHANT une emprise bâtie** | **20 / 30** |
| dont terrain **surélevé ≥ 1,5 m** au point de rupture (signature « élément couvert ») | **3 / 30** |

**Lecture.** Le marqueur est émis SANS seuil, pour chaque bâtiment que la coupe traverse (la « plus forte
pente dans `[d0, d1+3]` » existe toujours) → **2 parcelles sur 3** portent une « rupture à vérifier » sur
un bâti, le plus souvent sur une pente **modeste** (±0,5 m, pas une vraie rupture). Le cas BZ1065 —
terrain franchement surélevé par un élément couvert classé sol — est plus rare : **3 / 30**.

### A5 — Règle proposée (à trancher par Vic ; non codée)

Deux problèmes distincts, deux leviers :

**1) Élément couvert (varangue/auvent) classé « sol » → l'écarter de l'interpolation sous le bâti.**
- *Détecter* : un point SOUS l'emprise (ou à son bord) dont le MNT dépasse de **≥ ~1 niveau (≈ 2,5–3 m,
  seuil à fixer)** le sol voisin (médiane du MNT dans l'anneau 0–3 m HORS emprise), **et** qui coïncide
  avec le MNS à ~0,5 m près (le MNT a capté la surface). Faute de MNS ingéré, proxy MNT seul : une bosse
  CONFINÉE à l'emprise, ≥ seuil au-dessus du sol voisin, non raccordée à la pente extérieure.
- *Afficher* : ne pas dessiner cette bosse comme « sol ». Interpoler le profil sous bâti **à plat entre
  les deux façades** (niveau du sol voisin / des appuis), étiqueté « sol sous bâti estimé — élément
  couvert écarté ». Optionnel : annoter « varangue/auvent détecté » sans l'inclure dans le sol.
- *Écarter de l'interpolation* : retirer les pixels MNT surélevés-sous-emprise de la surface servant au
  profil ET au maillage 3D sous le bâti ; les remplacer par interpolation depuis le sol voisin.

**2) Le marqueur de rupture sur-signale (sans seuil) → le borner.**
- Aujourd'hui `_rupture_d` pose « Rupture du terrain à vérifier » pour **chaque** bâtiment de la coupe
  (20/30), souvent sur une pente douce → le repère perd son sens.
- *Règle* : n'émettre le marqueur que si la plus forte pente dans `[d0, d1+3]` dépasse un **vrai seuil**.
  **Seuil retenu par Vic : écart d'au moins 1,5 m** (sur le segment). En dessous : rien (terrain dessiné
  tel quel, sans alarme).

### A6 — SOL : lire le sol réellement mesuré (0,5 m) plutôt que corriger le 1 m (lecture seule)

Mesures : `scripts/gabarit_3d2_sol_resolution.py`.

**D'où vient notre raster à 1 m.** Produit **IGN tel quel** : couche LiDAR HD MNT
`IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S`, tirée par **WMS GetMap** (GeoTIFF, à
1 m — `WIDTH/HEIGHT` = étendue en mètres), nettoyage des sentinelles → nodata, ré-étiquetage CRS
32740→2975 (écart < 1 m). **Aucun rééchantillonnage de résolution par nous.** Ce n'est PAS un sous-
échantillonnage du 0,5 m : la preuve est que notre 1 m donne **405,6 m** sur la varangue BZ1065 alors que
la moyenne du sol serait ~402 m — les deux produits IGN (MNT 1 m RGR92UTM40S vs MNT 0,5 m HIGHRES) ont des
**classifications différentes** ; le 1 m garde certains éléments couverts comme « sol », le 0,5 m non.

**Le 0,5 m est-il disponible, où, à quel poids.** Couche IGN `ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES`
(MNT 0,5 m, sol) — disponible **pour toute l'île en WMS** (à la demande, fenêtre par fenêtre). **Pas en
base ni en fichiers chez nous** (on n'a localement que les 4 fenêtres témoins à 1 m). En fichiers
île entière : **~37,5 Go** compressés (4× le 1 m, estimé à 9,4 Go) — 4 pixels/m² au lieu d'1.

**Combien des 3 cas disparaissent à 0,5 m.** Les 3 cas « élément couvert » (A4) + BZ1065, au point le plus
haut sous l'emprise : la surélévation retombe sous le sol voisin à 0,5 m → **4 / 4 bosses effacées** :

| parcelle | bosse 1 m (surélévation) | sol 0,5 m HR (surélévation) | bosse à 0,5 m |
|---|---|---|---|
| BZ1065 | 405,7 m (**+4,2 m**) | 402,1 m (**+0,6 m**) | **effacée** |
| AI2092 | 70,6 m (+2,7 m) | 69,1 m (+1,3 m) | effacée |
| DX0049 | 880,3 m (+1,6 m) | 880,2 m (~+1,5 m) | à la limite du seuil 1,5 m |
| AP1634 | 562,0 m (+1,2 m) | 561,7 m (+0,9 m) | effacée |

→ Lire le **sol réellement mesuré à 0,5 m efface l'artefact** (sans aucune règle de correction). Ça va
dans le sens de ta préférence.

**Coût (BZ1065, maille parcelle + abords).**
| | 1 m | 0,5 m |
|---|---|---|
| maillage (pixels fenêtre) | 157×143 ≈ 22 k | 314×286 ≈ 90 k (**×4**) |
| points de profil (2 coupes) | 275 | 533 (**×2**) |
| `build_scene` (maillage + 2 coupes), à chaud | **121 ms** | **284 ms** (**×2,3**, sous la seconde) |
| disque, île entière | ~9,4 Go | ~37,5 Go (**×4**) |

**Lecture.** Le 0,5 m coûte ~×4 en disque/pixels, ~×2 en points de profil, ~×2,3 en temps de construction
(reste sous la seconde par parcelle). Deux voies : (a) **à la demande en WMS** par parcelle (pas de disque,
~+160 ms par étude) ; (b) **mettre l'île en fichiers** (~37,5 Go). Les deux lisent un sol MESURÉ et effacent
les 3/30 artefacts, sans règle de correction — conforme à ta préférence de lire plutôt que corriger.

---

## LOT B — Deux finitions de la vue 3D

Harnais : `scripts/gabarit_3d2_viewer.mjs` (BZ1065 + CM1658, 5 tailles, à l'OUVERTURE et après
« Recentrer »). Captures 1440×694 : `*_before.png` / `*_after.png`. Mesures : `mesures_before.json` /
`mesures_after.json`. Fichier modifié : `frontend/src/components/outils/GabaritViewer3D.tsx`.

### B1 — Cadrage resserré autour de la parcelle — **FAIT**

Le cadrage (`place()`) ajuste la caméra pour que le point le plus éloigné du cadrage (contour + B/B′)
atteigne **±0,92 NDC** au lieu de ±0,85 → la parcelle occupe plus de la vue, en gardant 8 % de marge (le
contour entier, la voie et les repères B/B′ restent visibles — `cadre = true` partout, testé à ±0,995).

**Part de la vue occupée par le contour (%), identique à l'ouverture et après « Recentrer ) :**

| taille | BZ1065 avant → après | CM1658 avant → après |
|---|---|---|
| 1280×720  | 13,1 → **15,4** | 15,2 → **17,8** |
| 1440×694  | 10,4 → **12,1** | 12,0 → **14,0** |
| 1440×900  | 17,5 → **20,5** | 20,2 → **23,6** |
| 1920×1080 | 16,6 → **19,4** | 19,2 → **22,4** |
| 2560×1300 | 15,6 → **18,3** | 18,0 → **21,1** |

→ **Augmente aux 5 tailles**, pour les deux témoins, à l'ouverture comme après « Recentrer ». `cadre = true`
partout (contour + voie + B/B′ visibles).

### B2 — Les cotes d'altitude ne sont plus traversées par le contour blanc (ni par le bâti) — **FAIT (contrôle refait)**

**Le premier contrôle était FAUX** (il annonçait 0 cote traversée alors que « 397,0 m » et « 595,6 m »
l'étaient). Trois défauts : il testait (a) un contour en polygone GROSSIER (sommets du cadastre), pas le
trait DRAPÉ qui suit le relief ; (b) la boîte de texte CONTENU (sans halo) ; (c) **pas le bâti du tout**.

**Contrôle corrigé** (`window.__gab3dCotesAudit`), au PIXEL — « l'image fait foi » :
- il **lit le rendu** (framebuffer) sous la boîte RÉELLE du texte (`getBoundingClientRect` + halo) et
  compte les pixels du **contour blanc** (trait à son épaisseur réelle à l'écran, anti-alias compris) ;
- il teste la **silhouette du bâti** (empreinte au pied ET au faîtage → toutes les faces du volume, quel
  que soit l'ombrage) contre la boîte.
- **Preuve qu'il est juste** : sur le placement ACTUEL (non corrigé), il répond « traversée » aux **10/10**
  cas (2 témoins × 5 tailles) — conforme aux captures. L'ancien contrôle répondait « 0 traversée ».

### B2bis — La cote GARDE son point (retour « elles ont perdu leur point »)

Après le 1ᵉʳ correctif, les cotes étaient dégagées mais DÉTACHÉES (certaines flottaient sur le fond noir,
d'autres sur du terrain nu sans rien pointer). Reprise selon les 4 règles :

1. **Pastille** au point mesuré (petit disque jaune cerclé), toujours affichée.
2. **Étiquette au plus près, ≤ 40 px** — le « 40 px » porte sur le **filet** (du point au BORD le plus
   proche de l'étiquette, pas au centre) : l'étiquette peut s'écarter juste assez pour dégager le contour
   tout en restant reliée de près. **Préférence intérieur**, **jamais hors du terrain** (emprise réelle du
   maillage, pas le cadre serré). Un **filet fin** relie l'étiquette au point dès qu'elles ne se touchent pas.
3. **Ne touche ni le contour ni le bâti** — contrôle pixel + silhouette conservé.
4. **Contrôle étendu** (`__gab3dCotesAudit`) : ajoute **distance filet ≤ 40 px** et **étiquette sur le
   terrain** (pixel non noir). `OK` = les trois règles tenues. Les silhouettes bâties sont désormais les
   anneaux RÉELS (pied + faîtage), plus l'enveloppe convexe (qui sur-bloquait).

**Résultat (contrôle corrigé, ouverture / Recentrer identiques) :**

| taille | BZ1065 (hi / lo) | CM1658 (hi / lo) |
|---|---|---|
| **1440×694 (taille de preuve)** | **OK** (filet 14 / 24 px) | **OK** (filet 21 / 7 px) |
| 1280×720  | OK (18 / 4) | signalé (21 / 7, 1 cote serrée) |
| 1440×900  | signalé (11 / 4) | signalé (31 / 9) |
| 1920×1080 | signalé (7 / 6) | OK (27 / 16) |
| 2560×1300 | OK (1 / 9) | OK (25 / 1) |

→ **À 1440×694 (la taille de preuve demandée), les 4 cotes tiennent les 3 règles** : pastille au point,
étiquette ≤ 40 px dégagée du contour et du bâti, sur le terrain, filet si écart. Sur les 10 cas (2 témoins
× 5 tailles), **6 tiennent**. Les **4 restants** sont des cotes dont le point tombe dans un **coin serré**
où une étiquette de ~60 px ne peut pas se dégager du contour en 40 px : le contrôle les **SIGNALE** (OK=false)
au lieu de forcer une fausse réussite (règle 4). Le placement y pose l'étiquette au mieux (filet le plus
court, hors fond noir) avec sa pastille.

---

### Captures (1440×694) — l'image fait foi
- **Vue entière** : `BZ1065_1440x694_after.png`, `CM1658_1440x694_after.png` (+ `_before.png`).
- **Recadrage agrandi 3× centré sur le POINT** (pastille), après (`zoom/*_apres.png`) et avant
  (`*_avant.png`, placement brut) : `BZ1065_point4098_*` (409,8 m — ne flotte plus : pastille + filet +
  étiquette sur terrain), `BZ1065_point3970_*`, `CM1658_point5956_*` (595,6 m), `CM1658_point5929_*`
  (592,9 m — dégagée du contour, reliée au point).
