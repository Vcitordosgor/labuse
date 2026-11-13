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
- *Règle* : n'émettre le marqueur que si la plus forte pente dans `[d0, d1+3]` dépasse un **vrai seuil**
  (p. ex. Δz ≥ ~1,5 m sur le segment, ou pente ≥ ~30 %), **ou** quand l'artefact « élément couvert » du
  point 1 est détecté au bord du bâti. En dessous : rien (terrain dessiné tel quel, sans alarme).

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

### B2 — Les cotes d'altitude ne sont plus traversées par le contour blanc — **FAIT**

Les cotes (point haut / point bas) tombaient souvent SUR la limite → le contour blanc les traversait. On
les décale vers l'INTÉRIEUR par un décalage **adaptatif** (8 directions × distances croissantes, on retient
la position qui dégage la boîte au moindre déplacement, en préférant l'intérieur). Contrôle ajouté au
harnais : `window.__gab3dCotesAudit()` projette le contour en pixels et teste l'intersection
segment ↔ boîte du libellé.

**Cotes traversées par le contour (hi ou bas), ouverture / Recentrer :**

| taille | BZ1065 avant → après | CM1658 avant → après |
|---|---|---|
| 1280×720  | oui → **non** | oui → **non** |
| 1440×694  | oui → **non** | oui → **non** |
| 1440×900  | oui → **non** | oui → **non** |
| 1920×1080 | non → **non** | oui → **non** |
| 2560×1300 | non → **non** | oui → **non** |

→ **Aucune cote traversée après correctif** (10/10 : 2 témoins × 5 tailles, ouverture ET Recentrer).

---

### Captures (1440×694)
- `BZ1065_1440x694_before.png` / `BZ1065_1440x694_after.png`
- `CM1658_1440x694_before.png` / `CM1658_1440x694_after.png`
