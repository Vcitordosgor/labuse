# COUCHES-RECETTE-2 — deuxième recette des couches

Branche **`feat/couches-tuyau`**, worktree `~/Desktop/labuse-couches-tuyau`.
Hash de départ (étape 0) : **`b3719d04`**. Commits de ce mandat (additifs, non mergés) :

| Commit | Contenu |
|---|---|
| `ef5e828c` | backend/YAML — piscines en points (A), Payanké projet (D), DPU/friches/BPE/arrêt (D), pastel→franc (C3) |
| `42e2327a` | front — filtres géométrie (A), panneau/légende (B), voile/clair/clic (C), rendu par niveau/popup/icônes (D) |

**Garde-fous** : aucun merge ; `:8020` intouché (toutes les tables dérivées — tuyau_piscines,
tuyau_telepherique — sont bâties à part, spatial_layers jamais modifiée) ; `served_run.txt` /
`served_manifest.json` / `run_precedent.txt` non commités ; `statement_timeout` sur chaque session,
aucune requête servie > 60 s ; aucune simplification de géométrie. `tsc -b` vert. **circuit verrous :
V7a VERT + V1c VERT** (tuyau_piscines/tuyau_telepherique enregistrées), G7 seul (sonde nocturne).

Stack de preuve : API `:8055` (mon code) + front vite `:5255` (proxy) + Chrome/Playwright. Captures
dans `captures/recette2/`. Script `frontend/qa/recette2_couches.mjs`.

---

## Lot A — ronds sur chaque sommet des polygones (CORRIGÉ génériquement)

**Cause** : un calque `circle` de MapLibre dessine un cercle à CHAQUE sommet de n'importe quelle
géométrie (anneaux de polygone, nœuds de ligne). Les couches à géométrie polygone/mixte servies avec
une dimension `point` (SIS/CASIAS `point_et_polygone`, TCSP `mixte`) posaient donc un rond par sommet ;
les piscines (données CoSIA = POLYGONES servis par une couche déclarée `point`) donnaient « 5 points
par piscine ».

**Correction (générique, dans `calques()`)** : chaque calque est FILTRÉ par type de géométrie —
`circle` → `Point` seul, `line` → `LineString` seul, `fill`/`outline` → `Polygon` seul. Règle
respectée : un polygone = remplissage + contour ; seuls les vrais points portent un cercle ; le seul
point sur une surface est le marqueur au **centroïde** (A2 de RECETTE-1). En plus, `tuyau_piscines`
sert désormais `ST_PointOnSurface` (un point par piscine).

Preuve : `A_piscines_1dot.png` (UN rond par piscine, 3 couleurs), `A_tcsp_stations.png` (zone
turquoise nette + rayon, AUCUN rond au sommet ; seules les stations sont des points),
`A_casias_sis.png`. Vérifié sur toutes les couches surfaciques via les filtres génériques.

## Lot B — panneau et légende

- **B1** un seul en-tête « Couches » (`B_panneau_da.png`). **B2** les couches du tuyau utilisent LE
  MÊME composant que l'ancienne liste (`LayerRowUI` partagé) → DA indiscernable (même case 13 px, même
  « i », même espacement). **B3** le « i » est un `Tip` au survol IMMÉDIAT, curseur normal (pas de « ? »).
- **B4** légende (`B_legende_5.png`) : plus de pastille à côté du titre ; les pastilles sont DANS
  l'accordéon, une par niveau (une seule si la couche n'a qu'un niveau) ; titres/libellés sur plusieurs
  lignes, jamais tronqués.
- **B5** couche à zoom minimum (`B_zoom_hint.png`) : en vue île, « Zoomez pour voir … » en légende ET
  bandeau sur la carte — jamais un silence.

## Lot C — lisibilité

- **C1** voile de mise en avant : `couche-veil` (calque background) sous les couches et au-dessus du
  fond, sur tous les basemaps ; s'active dès qu'une couche non-Repères est visible, disparaît sinon
  (`C_voile_inactif.png` / `C_voile_actif.png`). **C2** Clair et IGN : contours de parcelles noirs,
  limites de communes gris foncé (Sombre/Ortho inchangés — `C_clair_2couches.png`). **C3** 50 pas et
  TVA primo → teintes franches. **C4** clic commune : la commune en valeur, le reste atténué
  (`C_clic_commune_ile.png`).

## Lot D — corrections par couche

Voir aussi les rapports détaillés ci-dessous (SUP, CASIAS/SIS, Friches, Payanké).

| Couche | Fait | Preuve |
|---|---|---|
| DPU | 2 couleurs — la donnée distingue simple (197) / renforcé (5) | `D_dpu.png` |
| SUP | comptage par famille île/commune (aucune perte) + familles distinguables par couleur | `D_sup_ile.png`, `D_sup_commune.png` |
| CASIAS/SIS | Lot A ; polygone rempli quand l'emprise existe, point sinon | `A_casias_sis.png` |
| Piscines | un rond par piscine, couleur par niveau | `A_piscines_1dot.png` |
| TCSP | zone/rayon sans ronds ; seules les stations sont des points | `A_tcsp_stations.png` |
| Transport | clic arrêt → nom + lignes + réseau (popup) | — |
| Téléphérique | Payanké (projet) digitalisé en pointillé, source citée | `D_telepherique_payanke.png` |
| BPE | libellés A→G en clair + points plus gros | `D_bpe_labels.png` |
| OSM | popup opaque au-dessus du point ; icônes dès le zoom commune | — |
| Friches | statut en 3 couleurs (avec projet / potentielle / sans projet) | `D_friches.png` |

---

## Rapport — SUP (île vs commune)

**Comptage des objets servis par famille** (morceaux `ST_AsMVTGeom` retenus / assiettes distinctes),
même méthode aux deux zooms :

- Vue **île** (z10, tuile 669/572, ¼ de l'île) : ac1 (3 assiettes), ac4 (1), el10 (1), pm1 (14),
  pm2 (4), pm3 (4) — **6 familles**.
- Vue **commune** (z13, Saint-Denis, tuile 5357/4582) : ac4 (1), el10 (1), pm1 (2) — **3 familles**.

**Aucune perte** : la différence est GÉOGRAPHIQUE, pas une perte au zoom — la tuile z10 couvre ¼ de
l'île (donc plus de familles), la tuile z13 ne couvre que le centre de Saint-Denis (qui n'a
localement que ac4/el10/pm1). À Saint-Denis, pm1 (PPR naturels) domine réellement (270 morceaux, 2
assiettes) → la couche paraît « rouge » là-bas, ce qui est la donnée, pas un rendu uniforme. Les
familles restent **distinguables par couleur** aux deux zooms (`D_sup_commune.png` : rouge pm1 +
bleu el10 + violet ac4). Le voile C1 aide à les détacher du fond.

## Rapport — CASIAS et SIS (deux types d'objets)

`sol_pollue` porte DEUX géométries selon l'objet :
- **emprise du site** (MULTIPOLYGON) — le périmètre réel du site (43 objets : casias 19, sis 9,
  instruction 15) ;
- **point d'adresse** (POINT) — quand seule l'adresse est connue, pas l'emprise (482 points : casias
  437, instruction 45). **SIS = uniquement des emprises** (polygones) ; **CASIAS = surtout des points**
  d'adresse (437) + quelques emprises (19).

Rendu (Lot A) : l'emprise polygonale est **remplie + contour** (marqueur au centroïde pour l'échelle
île) ; le point d'adresse est **un seul rond**. Plus aucun rond parasite sur les sommets d'emprise.

## Rapport — Friches (Cartofriches inclut-il les friches bâties ?)

**Oui.** La couche `friche` provient de Cartofriches ET du recensement AGORAH des **friches urbaines
BÂTIES** (source `https://www.agorah.com/…/recensement-des-friches-urbaines-baties-a-la-reunion/`).
Les attributs le confirment : `site_type = "friche d'habitat"`, `bati_nombre ≥ 1`, `bati_etat =
"dégradation très importante"`, `site_occupation = "totalement inoccupé"`. Le **statut** est servi en
sous-type et rendu en 3 couleurs distinctes : avec projet (52, vert) / potentielle (2, ambre) / sans
projet (318, rouge = le gisement disponible) — `D_friches.png`.

## Rapport — Payanké (2e téléphérique)

**Sources consultées** : CINOR (site officiel `cinor.re/la-ligne-bellepierre-la-montagne/` et
`telepherique-urbain.cinor.org`), presse (La1ère, Imazpress, LINFO, Zinfos974), Wikipédia
(« Téléphérique urbain de la Cinor »), OpenStreetMap (Nominatim + Overpass).

**Trouvé** : le projet **Payanké** (CINOR, marché attribué au groupement MND) relie **Bellepierre**
(station basse, bas de Bellepierre à l'intersection de la rue Bertin, près du CHU Félix Guyon) à **La
Montagne** (station haute, Belvédère au début de la route de la Vigie) — **1,3 km, 305 m de dénivelé,
franchit une grande ravine**, mise en service annoncée ~2029. OSM porte la station haute nommée
« Station Belvédère - La Vigie » (55,4330 / -20,8848).

**Tracé du câble** : NON publié en GIS (ni CINOR, ni OSM, ni Géoportail). Les deux **stations**, elles,
sont publiées. J'ai donc digitalisé un **SEGMENT INDICATIF** entre les deux stations annoncées
(55,4448/-20,8918 ↔ 55,4330/-20,8848), servi via `build_tuyau_telepherique` en `subtype=ligne_projet`,
rendu **en pointillé ambre** « Ligne en projet (Payanké — tracé indicatif) », source CINOR citée au
clic. La précision du câble n'est PAS revendiquée (rien inventé au-delà des stations publiées) —
`D_telepherique_payanke.png`.

Sources : [CINOR — ligne Bellepierre>La Montagne](https://www.cinor.re/la-ligne-bellepierre-la-montagne/) ·
[La1ère — Payanké](https://la1ere.franceinfo.fr/reunion/a-quoi-ressemblera-payanke-le-futur-telepherique-entre-bellepierre-et-la-montagne-1737461.html) ·
[Wikipédia — Téléphérique urbain de la Cinor](https://fr.wikipedia.org/wiki/T%C3%A9l%C3%A9ph%C3%A9rique_urbain_de_la_Cinor).

« Ne merge pas. »
