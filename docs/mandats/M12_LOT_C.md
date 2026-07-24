# M12 · LOT C — Carte & couches

Branche : `feat/m12-c-carte` (worktree isolé). **Ne pas merger** — revue Vic.
Fil conducteur : les panneaux prenaient trop de place sur la carte et se recouvraient.

Périmètre strict : carte / couches / légendes. **Zéro touche scoring, zéro touche data, zéro
touche backend.** (Golden 116/116 exigé et obtenu — voir plus bas.)

Fichiers touchés (tous front) :
`frontend/src/lib/layers.ts`, `frontend/src/lib/status.ts`, `frontend/src/store/useApp.ts`,
`frontend/src/components/map/MapView.tsx`, `frontend/src/components/map/Legend.tsx`,
`frontend/src/components/panel/LeftPanel.tsx`, `frontend/src/styles/index.css`.

---

## FAIT

### C1 — « Couches » = tiroir repliable, replié par défaut
`LayersSection` (LeftPanel) est désormais **replié par défaut** : seul l'en-tête « Couches »
+ un compteur « N active(s) » + un chevron sont visibles → la vue parcelle est libérée.
Ouvert, il **pousse** le contenu du dessous (flux flex-column : jamais de recouvrement ; la
liste des résultats garde sa hauteur, le bloc est plafonné `max-h-[38vh]` + scrollable).
**Auto-fermeture ~10 s** après une sélection de couche (minuteur relancé à chaque toggle,
nettoyé au démontage). L'état est partagé desktop + tiroir mobile.

### C2 — Pastille « i » par couche, textes centralisés
Une pastille ronde « i » à droite de chaque couche : **survol OU clic** → explication écrite
**pour un client** (via le composant `Tip` existant, tactile + clavier `tabIndex`). Le clic sur
la pastille ne bascule pas la couche. Textes **centralisés** dans
`LAYER_INFO: Record<string, string>` (`lib/layers.ts`, règle R3) — recopiés ci-dessous.

### C3 — Équipements : « i » distance + bug pastilles qui rétrécissent
- Le texte « i » de la couche Équipements mentionne que **la fiche parcelle donne la distance
  en mètres jusqu'à chaque équipement le plus proche**.
- **Bug corrigé** : la rampe `icon-size` (`12→0,32 / 17→0,60`) s'aplatissait et **plafonnait à
  z17**. Au zoom rapproché (z18-20, l'échelle de travail sur une parcelle) les pastilles
  restaient figées à 0,60 pendant que tout le reste grossissait → rétrécissement *relatif*.
  Nouvelle rampe **croissante et continue jusqu'à z20** :
  `12→0,30 · 15→0,55 · 17→0,85 · 20→1,3`. Les pastilles grossissent quand on approche.

### C4 — Réordonnancement des couches (plus utilisé → moins utilisé)
Ordre appliqué au tableau `LAYERS` (une justification par ligne) :

| # | couche | justification (1 ligne) |
|---|--------|--------------------------|
| 1 | Parcelles | la couche de travail (verdict coloré), vue à chaque session |
| 2 | Limites parcelles | contour cadastral, référence constante posée sur le fond |
| 3 | Colorisation par type de zonage (C5) | lecture d'ensemble de la constructibilité, geste rapide |
| 4 | Zonage PLU (par parcelle) | zone précise à la parcelle (étiquette + clic), le détail |
| 5 | Zonage PLU (zones officielles) | polygones GPU bruts, moins fréquent (déjà couvert par 3/4) |
| 6 | PPR multirisque | écran risques, filtre d'exclusion précoce fréquent |
| 7 | Équipements | contexte de proximité, courant en due diligence |
| 8 | Limites communes | repère communal (défaut ON, rarement basculé) |
| 9 | Parc national | situationnel (relief / mi-pentes) |
| 10 | ANRU (NPNRU) | périmètres de renouvellement, de niche |
| 11 | 50 pas géométriques | bande littorale, la plus rare (communes côtières uniquement) |

### C5 — « Colorisation par type de zonage » (à côté de « par parcelle »)
Nouvelle couche `zonage_colorise` (store `LayerToggles`, défaut OFF) **à côté** de
« Zonage PLU (par parcelle) », pas à sa place. Elle **colorie d'un coup TOUTES les parcelles**
par type de zone, **sans clic**. Implémentation : les deux couches (`zonage_parcelle` OU
`zonage_colorise`) allument le même remplissage par famille (`zonageColor` → `zonageFill`),
la différence est que « par parcelle » ajoute l'étiquette au zoom + le popup au clic, tandis
que « colorisation » est la lecture d'ensemble nue.

**Palette (grief « U1a / U1c trop proches »)** : le grief est un grief d'écart de teinte. Les
4 familles sont écartées autour du cercle chromatique (≥90° entre voisines), distinctes du
verdict :
- U — urbaine : `#E5417F` (magenta franc)
- AU — à urbaniser : `#4C7DF0` (bleu roi)
- A — agricole : `#E8B23A` (or / ambre chaud)
- N — naturelle : `#3FB56A` (vert franc)
- autre : `#8A94A6` (gris neutre)

Légende associée fournie (voir C6).

> **Portée volontairement famille (U/AU/A/N), pas par zone précise (U1a…)** — cf.
> « laissé volontairement » ci-dessous. La donnée `zone_lib` compte **468 valeurs distinctes,
> dont 133 sont du bruit purement numérique** : une colorisation data-driven par zone précise,
> stable et lisible, exigerait un travail backend/tuiles hors périmètre. Le mandat autorise
> explicitement le repli famille comme livrable — c'est ce qui est livré, sans rien casser à
> moitié.

### C6 — Légendes qui cohabitent (fin du recouvrement)
Solution retenue : **un seul panneau** (`Legend.tsx`), sections **empilées** avec séparateurs,
**borné en hauteur** (`max-h-[60vh]`) et **scrollable** — jamais de superposition. La légende
« Équipements » (qui recouvrait le verdict) **quitte son bloc flottant** de MapView et rejoint ce
panneau. La META Équipements est remontée dans `lib/status.ts` (`EQUIP_META`) pour partager une
source unique entre le rendu carte et la légende.

### C7 — Légende « Verdict » repliée par défaut (jamais supprimée)
Le bloc Verdict est **replié par défaut** (bouton chevron), **dépliable au clic**. Jamais
supprimé (décision réservée à Vic ; le défaut réversible = replier). Intégré à la solution C6.

### C8 — Infobulle de zonage harmonisée
Le popup MapLibre par défaut est un carré **blanc à angles droits** encadrant notre bloc sombre
arrondi (double épaisseur). Règle CSS `.labuse-popup` ajoutée (`styles/index.css`) : conteneur
**transparent + arrondi**, pointe alignée sur le fond sombre `#0F1A14`, bouton de fermeture
masqué → **un seul bloc net, arrondi, sans liseré blanc**.

---

## LAISSÉ VOLONTAIREMENT (non fait, raison)

- **C5 par zone précise (U1a, U1c…)** : non fait — `zone_lib` = 468 valeurs distinctes dont
  133 de bruit numérique ; une palette data-driven par zone stable/lisible impose un
  nettoyage backend + rebuild de tuiles hors périmètre du lot. Repli **famille U/AU/A/N**
  livré (autorisé par le mandat). **Suivi** : normaliser `zone_lib` côté ingestion + porter
  un code de zone propre dans les tuiles MVT, puis étendre l'expression `match` MapLibre.

---

## C2 — TEXTES RECOPIÉS (source : `LAYER_INFO`, `lib/layers.ts`)

- **zonage** — « La carte officielle des zones du PLU (urbaine, à urbaniser, agricole,
  naturelle) telle que publiée par la commune — les grands aplats de couleur, sans découpage à
  la parcelle. »
- **zonage_parcelle** — « Chaque parcelle prend la couleur de sa zone du PLU. En zoomant, ou en
  cliquant une parcelle, le code exact de la zone (par ex. U1a, 1AUc) s'affiche. »
- **zonage_colorise** — « Colorie d'un coup TOUTES les parcelles selon leur type de zone
  (urbaine, à urbaniser, agricole, naturelle) — sans avoir à cliquer parcelle par parcelle. Une
  lecture d'ensemble du potentiel de constructibilité. »
- **parcelles** — « Les parcelles cadastrales, colorées selon l'avis de LABUSE (les plus
  prometteuses ressortent). C'est la couche de travail principale. »
- **ppr** — « Les zones exposées à un risque naturel connu (inondation, mouvement de terrain,
  littoral…) inscrites dans un Plan de Prévention des Risques — utile pour écarter tôt un
  terrain contraint. »
- **parc** — « Le périmètre du Parc national de La Réunion : à l'intérieur, l'urbanisation est
  très restreinte voire interdite. »
- **limites** — « Le simple tracé du contour de toutes les parcelles, sans couleur — pour lire
  le découpage cadastral sur le fond de carte. »
- **communes** — « Les frontières officielles entre les communes (le trait vert) — pour se
  repérer et savoir de quelle mairie dépend un terrain. »
- **anru** — « Les quartiers inscrits dans un programme de renouvellement urbain (ANRU) :
  secteurs prioritaires où des opérations d'aménagement sont soutenues par l'État. »
- **cinquante_pas** — « La bande littorale des « 50 pas géométriques » (81,20 m depuis le
  rivage), un régime foncier propre à l'outre-mer où la constructibilité est très encadrée. »
- **equipements** — « Les équipements du quotidien à proximité (mairie, écoles, santé,
  commerces, transport, sport). Sur la fiche d'une parcelle, LABUSE indique la distance en
  mètres jusqu'à chaque équipement le plus proche. »

---

## Vérifications

- **Build front** : `cd frontend && npm run build` → `tsc -b` + `vite build` OK, **0 erreur
  TypeScript**.
- **Golden** (backend intouché) : `116/116 PASS, 0 FAIL` (API locale port 8021, v2/modèle servi
  `m36-l2f-2026`). *Note d'exécution : un premier passage a affiché 84/116 par course avec un
  serveur en cours d'arrêt (32 sentinelles score_v2 « absent ») ; relancé sur serveur sain →
  116/116.*
