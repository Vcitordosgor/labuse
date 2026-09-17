# COUCHES-RECETTE-1 — retours de recette sur les 56 couches

Branche **`feat/couches-tuyau`**, worktree `~/Desktop/labuse-couches-tuyau`.
Hash de départ (étape 0) : **`6f637e66`** (= `origin/feat/couches-tuyau`, worktree propre).
Commits de ce mandat (non mergés, additifs) :

| Commit | Lot |
|---|---|
| `346c87c5` | Lot A/B — déclarations + tuyau (couleurs A3, familles, `i`, limites communes/bassin/endiguement/téléphérique) |
| `ec6b8bf3` | Lot A — front (Repères en tête + défaut, DA sans pastille, `i` par couche, légende accordéon, voile ortho) |

**Garde-fous respectés** : aucun merge ; `:8020` intouché ; aucune couche ni endpoint ancien
retiré (tout additif) ; `served_run.txt` / `served_manifest.json` / `run_precedent.txt` jamais
commités ; `statement_timeout` posé sur chaque session, aucune requête > 60 s ; aucune
simplification / dégradation de géométrie. `tsc -b` vert, `labuse circuit verrous` joué.

## Verrous (`labuse circuit verrous`)

**V7a VERT** — 56 couches × zooms 10/13/16, 168 tuiles décodées EN ENTIER, objets / parties /
contour / position **identiques à la brute** (mes changements de géométrie — `mixte`,
dé-subdivision de `bassin_versant`, reconstruction de `mvt_communes` — préservent la parité).

2 verrous CASSÉS, **tous deux pré-existants / environnementaux, hors de mon périmètre** :
- **G7** — la sonde nocturne n'a pas tourné depuis 3 j (dernier passage 13/09) ; **0 fuite
  ouverte**. Staleness temporelle, pas une régression.
- **V1c** — verrou pré-existant documenté (cf. historique RECETTE-8/CIRCUIT-6 « V1c/V3a
  pré-existants »). Aucun de mes fichiers (YAML couleurs/familles/`i`, `couches_tuyau.py`,
  `declarations.py`) ne touche son domaine.

---

## Lot A — règles transversales

| Règle | État | Ce qui a été fait |
|---|---|---|
| **A1** ne colorer que la donnée | ✅ *(par construction dans le tuyau)* | Le tuyau ne peint QUE les features de chaque couche ; il ne remplit jamais le reste de l'île ni ne recolore les limites communes. Le bug historique « ZFANG passe les limites communes en bleu / marron ailleurs » était un comportement **legacy** (hors tuyau) ; `limites_communes` est désormais une couche « Repères » indépendante (vert #5CE6A1). *(À confirmer visuellement — cf. Différé/preuve.)* |
| **A2** couleurs vives, points visibles en vue île | ⚠️ partiel | Cimetières : gris #E0E7EC (invisible sur fond sombre) → violet-ardoise vif. **Point d'île (centroïde) NON encore rendu** : `centroide` n'est pas câblé dans le tuyau (servir un centroïde casserait le verrou sans le rendre conscient) → **différé** (barrages/cimetières restent des polygones, visibles au zoom, pas en points d'île). |
| **A3** pas de camaïeu | ✅ | ZNIEFF, Parc national, PPR, classement sonore, aléa mvt, TRI, piscines, TCSP — voir Lot B. Toutes les autres couches à grades vérifiées (aléa inondation, PEB, artificialisation, zonage parcelle : déjà distinctes). |
| **A4** couleurs distinctes entre couches d'une famille | ✅ *(TCSP)* | TCSP éclaté en 4 teintes. Les 4 couches Transport restent colorées **par réseau** (data-driven, c'est la donnée) ; distinction inter-couches assurée par la géométrie (axes lignes bleu-gris, HTB/HTA tiretés distincts, téléphérique rose tireté, TCSP 4 teintes). |
| **A5** « Repères » en tête, cochées par défaut | ✅ | Nouvelle famille `reperes` (Limites communes + Limites parcelles), **en tête** du panneau, **cochées par défaut** ; **toutes les autres couches décochées par défaut** (comme les anciennes). |
| **A6** voile gris en vue ortho | ✅ | Calque `background` `ortho-veil` (gris #20242A) entre l'orthophoto et les couches, opacité 0,3 **uniquement en ortho** (0 sur Sombre/Clair/Plan), piloté par `applyClairMode`. |
| **A7** chargement | ⚠️ partiel | Mesures **serveur** ci-dessous (toutes < 0,4 s pour les couches modifiées, y compris `bassin_versant` dé-subdivisé). Profilage navigateur (waterfall, debounce, cache tuiles) : **différé**. Aucune requête > 60 s. |
| **A8** un « i » par couche | ✅ | Le texte `i` (déclaration YAML `comment.i`) est transmis par `/map/tuyau/couches` et affiché en info-bulle par couche dans le panneau (tous les `i` présents, 0 couche sans `i`). |
| **A9** DA identique aux anciennes | ✅ | Panneau : case à cocher + nom, **plus de carré coloré (Pastille) devant le nom**. La couleur se lit dans la légende. |
| **A10** légende renommée + accordéon | ✅ | Panneau « **Légende** » ; **un accordéon par couche active** (titré du nom) ; la **dernière couche allumée est dépliée**, les autres repliées, clic pour changer ; décalée vers le haut (`bottom-10`) pour ne pas chevaucher « Cadastre © DGFiP ». |
| **A11** rangement par catégorie | ✅ | Voir tableau catégories ci-dessous. Repères en tête ; BPE+OSM → « Équipements » ; bâti 3D retiré du panneau (bouton 3D) ; « Fond de plan » disparaît. |
| **A12** rien de muet | ⚙️ | Chaque couche porte déjà sa phrase d'`absence` (déclaration). La liste « pas de donnée publiée pour : … » par couche partiellement couverte (aléa mvt communes sans donnée, VEFA < 10 ventes) : la légende par niveaux la dit déjà (VEFA « moins de 10 ventes » ; aléa mvt = **à compléter** côté légende dynamique — cf. Différé). |

### A11 — tableau des catégories (pour validation Vic)

Ordre du panneau (fixé dans `ORDRE_FAMILLES`) :

| Ordre | Catégorie | Couches |
|---|---|---|
| 1 | **Repères** *(cochées par défaut)* | Limites communes, Limites parcelles |
| 2 | Urbanisme | Limites officielles du PLU (GPU), Zonage PLU par parcelle (calibré), 50 pas géométriques, Artificialisation (OCS GE), DPU, SUP, ER, EBC |
| 3 | Risques | PPR, Ravines (DPF), Endiguement, PEB, Classement sonore, Cartes de bruit, Aléa inondation, Aléa mvt, SIS, CASIAS, ICPE, Cavités, Trait de côte, TRI, Murs de soutènement, Barrages/ponts/dalles |
| 4 | Environnement | Zones humides, ENP, ZNIEFF, Parc national, Forêts publiques, Bassins versants |
| 5 | Foncier | Piscines, Friches, SAR, Foncier agricole (RPG/SAFER), Zones d'activité |
| 6 | Réseaux | Lignes HTB, Lignes HTA |
| 7 | Transport | Axes structurants, Transport public — lignes, Transport public — arrêts, Téléphérique, Pôles d'échange, TCSP |
| 8 | Dispositifs | ZFANG, FRR, TVA primo, QPV, ANRU |
| 9 | Patrimoine | Périmètres ABF, Cimetières |
| 10 | Équipements | Équipements OSM, Équipements INSEE (BPE) |
| 11 | Marché | Prix du logement neuf (VEFA) |
| — | *(Fond de plan — disparu)* | Bâti 3D → **bouton 3D**, hors panneau |

### A7 — mesures de chargement (serveur, tuiles impactées)

Génération de la tuile (session `statement_timeout` 58 s), vraie tuile de l'île :

| Couche | z10 | z13 | Note |
|---|---|---|---|
| `bassin_versant` (dé-subdivisé, contour_seul) | **0,37 s** (618 Ko) | 0,06 s | Aucune simplification ; largement < 60 s |
| `limites_communes` (mvt_communes réparé) | **0,01 s** (2,7 Ko) | 0,00 s | 24 communes, 49–122 pts (vs 667 k avant) |
| `endiguement` (mixte) | **0,01 s** (14 Ko) | 0,00 s | Digues-lignes + zones |

Profilage navigateur complet (waterfall, cache, debounce, couches re-demandées) : **différé**.

---

## Lot B — corrections couche par couche

| Couche | Correction | État |
|---|---|---|
| ZFANG | A1 (colorer que la donnée) | ✅ le tuyau ne peint que les zones ZFANG ; limites communes indépendantes. *(vérif visuelle différée)* |
| FRR | A1 idem | ✅ idem |
| Parc national | A3 cœur/adhésion franchement différents | ✅ cœur **vert forêt** #1E7A45 / adhésion **ambre** #D9973B |
| **Bassins versants** | *rien ne s'affichait* | ✅ **cause trouvée** : `contour_seul` (pas de fond) + subdivisé (le front supprime le contour des morceaux) = ni fond ni bord. `registre()` ne subdivise plus une couche `contour_seul`. |
| ZNIEFF | A3 type I/II | ✅ olive #8F9E4B / sarcelle #3FA6A0 |
| SAR | légende par vocation | ⚠️ **différé** — `sar` n'a pas de sous-type vocation servi en base (une seule teinte) ; à instruire côté donnée. |
| Piscines | A3 + doublons | ⚠️ couleurs A3 posées (bleu/turquoise/ocre). **Constats données** : (1) `spatial_layers.piscine_cosia` porte `subtype="Piscine"` pour les 46 599 — **l'attribut `niveau` (confirmée/probable/rare) n'y est pas** (il vit dans l'outil solaire / `parcel_equipements`) → sur cette couche carte le rendu 3-niveaux retombe sur une teinte ; (2) **62 paires de points < 2 m** à Saint-Denis = doublons BD ORTHO/CoSIA confirmés. Dédoublonnage + `niveau` = **tâches donnée** (non faites, additif). NB : couche `panneau_general: false` (outil Prospection solaire). |
| **Limites communes** | *cassée (dessine un réseau)* | ✅ **réparée** : `build_mvt_communes` charge le GeoJSON officiel `communes974.geojson` (contours IGN) au lieu de dissoudre les parcelles (arêtes internes non dissoutes → 667 k pts/commune). Après : 24 communes, 49–122 pts. Rendu de l'ancienne couche repris (#5CE6A1, 1,6 px). |
| Limites parcelles | cochée par défaut (A5) | ✅ famille `reperes`, cochée par défaut |
| Équipements BPE | légende par catégorie | ⚙️ déjà colorée par domaine A–G (data-driven) ; légende par domaine présente. Sortie vers « Équipements » (A11). |
| Équipements OSM | rond + icône + clic → nom | ⚠️ rond coloré par type + clic → popup **OK** ; **icône par type différée** (le tuyau rend des cercles, pas des symboles ; l'ancienne couche posait une icône — refonte symboles à instruire). Sortie vers « Équipements ». |
| **Bâti 3D** | retirer du panneau, brancher au bouton 3D, vérifier calage | ✅ retiré du panneau ET non monté (couche `extrusion` exclue) ; le bouton 3D (`toggleTerrain`) porte déjà l'extrusion du bâti. **Mesure de calage (superposition ortho zoom rue) : différée.** |
| Cimetières, Barrages | A2 points visibles en vue île | ⚠️ couleurs vives posées (cimetières violet vif) ; **points d'île (centroïde) différés** (câblage centroïde tuyau, cf. A2). |
| TRI | A3 3 couleurs | ✅ extrême jaune / moyen orange / fréquent rouge (emboîtement gardé) |
| Aléa mvt | A3 4 grades + A12 communes sans donnée | ✅ jaune→orange→rouge→violet ; **liste des communes sans donnée en légende : différée** (légende dynamique). |
| PPR | A3 Information/Prescription/Interdiction | ✅ jaune / orange / rouge |
| Classement sonore | A3 cat. 1→5 ordonnées | ✅ cat.5 jaune → cat.1 violet |
| **Systèmes d'endiguement** | *rien de visible* | ✅ **cause** : 69/117 objets sont des **lignes** (digues) mais déclaré `geometrie: polygone` → jamais dessinés. `geometrie: mixte` + trait épais #22C4A0. |
| TCSP | A3 4 éléments | ✅ zone turquoise / rayon bleu / tronçon vert / station ambre ; `geometrie: mixte` (avant : zone seule rendue). |
| Transport public | fusionner lignes+arrêts en 1 couche, 2 sous-calques | ⚠️ **différé (structurel)** — reste 2 couches distinctes pour l'instant ; fusion en un toggle à 2 sous-calques = lot front dédié. Couleur par réseau + clic déjà présents. |
| **Téléphérique** | renommer + dessiner la ligne + 2ᵉ projet | ✅ renommé « Téléphérique » ; **ligne Papang rendue** (`geometrie: mixte` — la donnée `ligne` existait, 2 objets, mais le front ignorait le niveau ligne d'une couche `point`). **Payanké** (2ᵉ, projet) : nom **confirmé** (CINOR, Bellepierre ↔ La Montagne, ~2029), mais **aucun tracé GIS officiel publié → non dessiné** (rien inventé). |
| Zonage PLU par parcelle (calibré) | étiquettes de zone + calibrage + lenteur | ⚠️ **différé** — étiquettes de zone (Ncu, U1b… en texte sur la parcelle dès le zoom commune) non implémentées (calque symbole `text-field` à ajouter) ; profilage/lenteur (431 k parcelles) non traité. La donnée `zone_fam`/`zone_lib` est déjà servie et colorée. |
| Zonage PLU | renommer + 2 teintes + légende 2 entrées | ✅ renommée « **Limites officielles du PLU (GPU)** » ; 2 teintes (U vert / reste brun) ; légende à 2 entrées. |
| **SUP** | légende par famille + clic code + dédoublonner PM1 | ✅ légende **par famille** (AC1-4, PM1-3, EL10, couleurs distinctes) + **code au clic**. **Dédoublonnage PM1 (~4×, 311 lignes) : signalé, non fait** (tâche donnée, additif). |
| Toutes | A8 « i », A9 DA, A10 légende | ✅ (voir Lot A) |

---

## Lot C — cohérence carte ↔ fiche parcelle (inventaire seul, aucune correction)

Établi par lecture du code (endpoint fiche `app.py:_q_v2_fiche`, cascade `served_cascade.py`,
blocs `_aleas_block`/`_dispositifs_block`/`_sols_block`/`_proximites_block`/`_reglement_plu_block`,
front `fiche/*.tsx`). **51/56 PRÉSENTES**. Les ABSENTES sont un futur mandat (non corrigé ici).

| kind | section de la fiche | verdict |
|---|---|---|
| ppr, dpf, endiguement, alea_inondation, alea_mvt, tri_zone, bruit_route, bruit_carte, cinquante_pas, icpe, cavite, trait_de_cote, abf, foret_publique, cimetiere, construction_lineaire, construction_surfacique, znieff, enp, zone_humide, parc_national | Risques et protections (aléas / cascade / voisinage) | PRÉSENTE |
| sis, casias | Risques et protections → Sols | PRÉSENTE |
| sup | Risques et protections → Vigilances SUP | PRÉSENTE |
| peb, dpu, er, ebc | Réseaux et accès → Dispositifs | PRÉSENTE |
| axe_structurant, transport_ligne, transport_arret, telepherique, pole_echange, ligne_ht, tcsp | Réseaux et accès → Proximités / Transport | PRÉSENTE |
| piscine_cosia | Réseaux et accès → Terrain (détection ortho) | PRÉSENTE |
| zfang, frr, tva_primo, qpv | Titres et impôts → Territoire fiscal | PRÉSENTE |
| anru | En-tête de fiche | PRÉSENTE |
| plu_gpu_zone | Urbanisme → Zonage PLU | PRÉSENTE |
| sar | Urbanisme → SAR | PRÉSENTE |
| safer | Foncier agricole | PRÉSENTE |
| friche | Urbanisme (cascade) | PRÉSENTE |
| artificialisation | Le bien → Couverture du sol | PRÉSENTE |
| batiment | Le bien → Emprise / hauteur / nombre | PRÉSENTE |
| vefa_neuf | Marché (fiche commune) | PRÉSENTE |
| amenite, amenite_bpe | Autour → À proximité | PRÉSENTE |
| **ligne_mt** (HTA) | — | **ABSENTE** *(la carte la montre, la fiche non — `ligne_ht` y est, pas `ligne_mt`)* |
| **bassin_versant** | — | **ABSENTE** *(contexte hydrologique, couche de fond)* |
| **zone_activite** | — | **ABSENTE** |
| **limites_parcelles, limites_communes, zonage_parcelle** | — | **ABSENTE** *(repères / fond, sans objet en fiche individuelle)* |

---

## Session 2 — points différés TRAITÉS (stack dédié + captures réelles)

Stack lancé : **API `:8055`** (mon code, `PYTHONPATH` du worktree) + **front vite `:5255`** (proxy → 8055)
+ **navigateur Chrome (Playwright)**. `:8020` intouché. Captures dans `captures/recette1/`.

| Point | Fait | Preuve (capture) |
|---|---|---|
| **A2 centroïdes** cimetières/barrages | ✅ symbole (pastille couleur) au centroïde du polygone → visible dès l'île ; géométrie servie inchangée (V7a intact) | `couche_cimetiere_commune.png` (points violets) |
| **Fusion Transport public** | ✅ lignes + arrêts en UNE entrée (un toggle, 2 sous-calques) via `groupe` ; légende par réseau | `legende_accordeon_5.png` |
| **Étiquettes zonage parcelle + lenteur** | ✅ calque symbole `zone_lib` dès z12 ; CAUSE lenteur = 431 k parcelles servies dès l'île → `zoom_min 11` (LOD, géométrie inchangée) | `zonage_parcelle_etiquettes_stdenis.png`, `zonage_parcelle_{stdenis,stpaul,saintemarie}.png` |
| **A7 waterfall + message** | ✅ message « Votre carte se charge pour vous donner l'information la plus précise possible » ; gating par `zoom_min` (semis de points/parcelles ne chargent plus la tuile île) | `a7_message_chargement.png` |
| **Dédoublonnage SUP PM1** | ✅ `build_tuyau_subdivise` dédoublonne par (kind, subtype, idass) — 417 → **123 assiettes** ; table dérivée seule (`:8020` intouché) | `couche_sup_commune.png` |
| **Dédoublonnage piscines + niveau** | ✅ `tuyau_piscines` : 1 piscine = 1 point (ST_ClusterDBSCAN, **0 doublon résiduel**), niveau en attribut (confirmee 11 877 / probable 34 062 / rare 4 504) | `couche_piscines_niveaux.png` (3 couleurs) |
| **Vocations SAR** | ✅ légende par vocation (7 vocations, couleurs distinctes) + popup | `couche_sar_commune.png` |
| **Icônes OSM + nom au clic** | ✅ **icône par type** (🏛️ mairie, 🏫 école, 🏥 santé, 🛒 commerce, 🚓 police, 🧺 marché, 🧸 crèche, 🎓 collège/lycée = EQUIP_META de l'ancienne couche) : calque symbole avec image emoji **générée au canvas** (robuste ≠ text-field du style, sans glyphes) posée sur le rond coloré ; clic → nom | `couche_osm_icone_zoom.png`, `couche_osm_icones.png`, `couche_osm_icones_clic.png` |
| **A12 légende « pas de donnée »** | ✅ mesuré : seule **Saint-Denis** a 0 donnée aléa mvt ; note en légende | `couche_alea_mvt_ile.png` |
| **Calage bâti 3D** | ✅ mesuré : extrusion BD TOPO alignée sur l'ortho au zoom rue (St-Denis), **aucun décalage systématique visible (< 2 m)**, pas d'erreur de projection | `bati_3d_calage_ortho.png` |

**Verrous après session 2** : **V7a VERT** (56 couches, tuiles = brute) ; **V1c VERT** (réparé : les
3 tables dérivées du tuyau — tuyau_subdivise / mvt_communes / tuyau_piscines — enregistrées dans
`TABLES_FABRIQUEES` ; V1c était CASSÉ depuis COUCHES-TUYAU-1). Reste **G7 seul** (sonde nocturne non
passée depuis > 48 h — 0 fuite ouverte, purement environnemental).

## Poids réseau réel des tuiles (mesuré au navigateur)

Mesuré via Playwright (contexte à cache ISOLÉ par mesure, position vérifiée) : somme des corps de
réponse des tuiles `.pbf` de la couche, en **vue commune (zoom 12,4)**, pour aléa mouvement de terrain
et zonage par parcelle à Saint-Denis / Saint-Paul / Saint-Pierre.

| Couche | Saint-Denis | Saint-Paul | Saint-Pierre |
|---|---|---|---|
| **Aléa mouvement de terrain** | 0,24 Mo (2 tuiles) | ~0 Mo* | 0,94 Mo (4 tuiles) |
| **Zonage PLU par parcelle** | 2,51 Mo (4 tuiles) | 3,34 Mo (6 tuiles) | 4,31 Mo (4 tuiles) |

Tuile individuelle la plus lourde : **1,61 Mo** (zonage, Saint-Pierre). **Aucune vue ne dépasse 20 Mo**
— la plus lourde est le zonage par parcelle à Saint-Pierre à **4,31 Mo**. (Le gating `zoom_min 11` du
zonage empêche la tuile île géante ; en vue commune le poids reste modéré.)

*Saint-Paul aléa mvt ≈ 0 : la vue centrée sur le centre-ville (littoral) au zoom 12,4 ne couvre pas les
zones d'aléa, qui sont dans les Hauts (la commune est très étendue) — pas un problème de poids.

## Captures (navigateur réel, Chrome via Playwright, `:5255` → API `:8055`)

`node frontend/qa/recette1_couches.mjs` (+ tranches). Dossier `captures/recette1/` :
- **Preuves mandat** : `panneau_reperes_full.png` (Repères en tête, cochés) · `legende_accordeon_5.png`
  (accordéon, 5 couches, une dépliée) · `ortho_voile_propre.png` (ortho + voile gris + couches) ·
  `a7_message_chargement.png` (message A7).
- **Par couche modifiée** (île + commune) : `couche_<kind>_{ile,commune}.png` pour limites_communes,
  endiguement, telepherique (ligne rose rendue), tcsp (4 teintes), sar (vocations), ppr, bruit_route,
  alea_mvt, znieff, parc_national, tri_zone, cimetiere (centroïdes), sup, plus `couche_piscines_niveaux.png`.
- **Zonage par parcelle** sur 3 communes : `zonage_parcelle_{stdenis,stpaul,saintemarie}.png` + zoom rue.
- **Limite du harnais** : `alea_mvt`/`zonage` en vue commune très dense font parfois sauter le transport
  CDP de Playwright (message > 512 Mo, artefact connu COUCHES-TUYAU-1) → ces vues sont capturées à l'île
  ou à un zoom intermédiaire ; la donnée est servie (vérifiée aussi par tuile SQL) et V7a la valide.

## Reste (hors périmètre de ce mandat)

- Lot C ABSENTES (ligne_mt, bassin_versant, zone_activite en fiche) — mandat séparé annoncé.
- G7 : relancer la sonde nocturne (environnement).

« Ne merge pas. »
