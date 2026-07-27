# MANDAT O12-PARTIEL — Le lot découpé

Branche `feat/o12-partiel` (depuis `feat/o12-ile`, aucun merge). **EXPOSE reste `False`.**
Inversion d'approche : au lieu de « que reste-t-il après le bâti ? », « quel lot pourrait-on
découper ? » — un SOUS-POLYGONE compact, pas le résiduel entier.

---

## A — Méthode retenue : la « bande de façade » ⏸ POINT D'ARRÊT

### Principe (ce qu'un géomètre dessinerait)

1. **Univers** : les parcelles écartées aujourd'hui par le SEUL ratio > 50 % — tous les autres
   filtres parcelle restent : surface 1 000-6 000 m², bâti 8-45 %, pas d'ensemble bâti
   (activité), etc. Univers **disjoint** du pool résiduel (ratio ≤ 50 %) par construction.
2. **Support** : le lot est découpé DANS le résiduel R (parcelle − bâti bufferisé 3 m, plus
   grand polygone). Conséquence par construction : **aucun bâti dans le lot** et **recul de
   3 m du bâti conservé** — pas besoin de règle de démolition.
3. **Ancre** : le plus long segment **CONTIGU** de façade voirie de R (`ST_LineMerge` des
   intersections avec la voirie bufferisée 1,5 m) ; exigence ≥ 12 m. L'ancre fait au plus
   **25 m de large** (constante `ANCRE_LARGEUR_M`), essayée à 3 positions : début, milieu,
   fin de façade.
4. **Bande** : buffer de l'ancre à bouts droits (`endcap=flat`), profondeur **20 à 40 m**
   (pas de 5 m), clippé à R, plus grand polygone. Sur une façade droite cela donne un
   rectangle au cordeau perpendiculaire à la rue — la découpe d'un lot en façade, telle
   qu'un géomètre la trace.
5. **Sélection** : parmi les 3 × 5 découpes candidates, on retient celle de **meilleure
   compacité** qui satisfait TOUS les seuils.

### Aucun critère validé n'est assoupli (garde-fou n° 1)

| Critère | Pool validé | Lot découpé |
|---|---|---|
| Surface du lot | 500-… (résiduel) | **600-900 m²** (cible du mandat) |
| Compacité (Polsby-Popper) | ≥ 0,25 (seuil) / 0,28 observé | **≥ 0,28** (le plancher OBSERVÉ du pool validé) |
| Largeur constructible | cercle inscrit ≥ 9 m | idem, sur le lot |
| Façade voirie | ≥ 12 m | **≥ 12 m CONTIGUË, revérifiée sur le lot** (pas héritée de l'ancre) |
| Bâti dans le lot | aucun / règle D | **aucun, par construction** (lot ⊂ résiduel) |
| Zonage | U/AU sur le lot, PAU si RNU | idem, sur le lot découpé |
| Littoral / domaine public | 50 pas, trait de côte, forêt domaniale, cœur du Parc | idem, sur le lot découpé |
| Emprise du lot restant | ≤ plafond PLU calibré sinon 60 % | idem (bâti conservé ÷ surface − lot) |
| Activité (ensemble bâti) | exclu | exclu (identique) |

### Les 5 exemples dessinés — `docs/mandats/O12_PARTIEL_EXEMPLES.pdf`

Détecteur de PRODUCTION exécuté sur 2 communes pilotes (Entre-Deux + Bras-Panon) :
**9 lots à découper** (6 + 3) là où le pool résiduel n'en a que 3 (2 + 1). Les 5 cartes
(top compacité) montrent : fond IGN, parcelle (vert), bâti (gris), **lot découpé stocké tel
que calculé** (orange), **voirie** (bleu), libellé « Lot À DÉCOUPER (hypothétique — le lot
proposé exige un découpage géomètre) », et les métriques (surface, compacité via clarté,
façade, emprise restante, zonage).

| idu | commune | lot m² | compacité | façade m | rayon m | emprise restante | zone |
|---|---|---:|---:|---:|---:|---:|---|
| 97403000AP2225 | Entre-Deux | 686 | 0,810 | 25,6 | 12,3 | 0,399 | U (Ub) |
| 97402000AK0807 | Bras-Panon | 642 | 0,802 | 29,1 | 11,5 | 0,541 | U (Ub) |
| 97402000AH0621 | Bras-Panon | 623 | 0,785 | 25,6 | 12,5 | 0,237 | U (Ua) |
| 97403000AR1521 | Entre-Deux | 638 | 0,785 | 25,6 | 12,5 | 0,209 | U (Ub) |
| 97402000AI0265 | Bras-Panon | 625 | 0,785 | 25,8 | 12,5 | 0,120 | U (Ub) |

(4 autres au-delà des 5 cartes : compacités 0,41-0,66 — toujours au-dessus du plancher 0,28.)

### Détails d'implémentation

- `src/labuse/ingestion/division_or.py` : `_DETECT_PARTIEL` + `_INSERT_PARTIEL` +
  `build_divisions_partiel` (mêmes placeholders et constantes que le détecteur résiduel :
  `pau_pred`, critère activité, plafond d'emprise par PLU calibré). Constantes dédiées
  documentées : `LOT_DECOUPE_MIN/MAX_M2`, `COMPACITE_MIN_DECOUPE`, `ANCRE_LARGEUR_M`.
- **Famille distincte** (mandat C) : `type_division='decoupe'`, jamais fusionnée — le tri du
  dossier garde les lots résiduels devant. La **géométrie du lot est STOCKÉE**
  (`lot_geom geometry(Polygon, 2975)`) : la carte de revue trace la découpe DU RUN, jamais
  une recalculée ; un géomètre peut l'exporter telle quelle.
- La carte de revue trace désormais la **voirie** (toutes familles) et le libellé
  hypothétique explicite pour `decoupe`.
- Tests : `test_lot_decoupe_o12_partiel` verrouille l'univers (ratio > 50 % seul), la bande
  (LineMerge + endcap=flat + LineSubstring), les seuils (600-900, ≥ 0,28, ≥ 9 m, façade lot
  ≥ 12), les gardes (zonage, littoral, emprise) et la famille distincte. **9/9 PASS.**

### Limites assumées (à voir en revue)

- L'ancre est posée sur la façade du RÉSIDUEL : sur parcelle d'angle, la bande peut suivre
  la mauvaise rue — la revue le verra (3 positions d'ancre limitent le cas).
- `endcap=flat` sur façade COURBE donne un lot en éventail — la compacité ≥ 0,28 le borne.
- Pas de variante « démolition » pour les découpes (v1) : le lot évite tout bâti. Extension
  possible après revue si le vivier le justifie.
- Coût : ~2-5 min/commune pilote (3×5 découpes × cercle inscrit). Île entière estimée
  30-90 min en 5 parallèles — lancée seulement après le GO.

**⏸ STOP — validation demandée avant le run île (B).** → **GO reçu**, avec correctif préalable.

---

## A-bis — Correctif préalable au GO : façade RESTANTE du lot bâti (anti-enclavement)

La bande pouvait enclaver la maison. Ajouté : le lot RESTANT (côté propriétaire) doit garder
**≥ 12 m de façade voirie CONTIGUË** — même seuil que le lot détaché — **mesurée directement
sur sa géométrie** (parcelle − découpe, `ST_LineMerge` contre TOUTES les voiries), jamais par
soustraction de longueurs (l'artefact du finding O12). Le cas **parcelle traversante** passe
naturellement : si le reste donne sur la deuxième rue, sa façade est comptée. Sinon, rejet.

**Impact pilotes (avant l'île) : 9 → 6** — retirés `97403000AP2225`, `97402000AK0807`,
`97402000AH0621` (la bande mangeait la façade de la maison ; les deux premiers étaient les
tops compacité des 5 exemples initiaux — le correctif était nécessaire). Parmi les 6 gardés,
**0 cas traversant** (toutes les façades restantes sont sur la même rue que le lot — mesuré,
distance façade-lot ↔ façade-reste = 0 m partout).

## B — Run île : **139 lots à découper, 22 communes sur 24**

`scripts/o12_run_partiel.py` (DELETE des `decoupe` + rebuild — le pool résiduel n'est jamais
touché). Effectifs (0 : Le Port, Les Avirons) :

Saint-Paul 16 · Le Tampon 15 · Saint-Joseph 13 · Saint-Denis 12 · Sainte-Marie 11 ·
Saint-Pierre 10 · Saint-Benoît 8 · Saint-Leu 8 · Saint-André 7 · Saint-Louis 7 · Cilaos 5 ·
Entre-Deux 5 · La Possession 5 · Salazie 5 · Petite-Île 4 · L'Étang-Salé 2 · et 1 chacune :
Bras-Panon, La Plaine-des-Palmistes, Les Trois-Bassins, Saint-Philippe, Sainte-Rose,
Sainte-Suzanne.

Distributions (n = 139) :
- **surface du lot** : min 600 · P25 621 · médiane 632 · P75 683 · max 896 m² ;
- **compacité** : min 0,290 · P25 0,577 · **médiane 0,718** · max 0,815 (des rectangles — la
  méthode produit ce qu'elle promet ; à comparer à la médiane 0,505 du pool résiduel) ;
- **façade du lot** : min 15,7 · médiane 27,6 · max 52,3 m ;
- **emprise restante** : min 0,098 · médiane 0,203 · max 0,585 (toutes sous plafond).

**Toutes les 139 parcelles gagnent un lot partiel qui n'existait pas** (univers = écartées par
le ratio, disjoint du pool résiduel par construction) : le vivier passe de 15 à **154**
candidats (× 10), sans toucher aucun seuil validé.

## C — Deux familles distinctes (acté)

`type_division='decoupe'`, jamais fusionné ; tri du dossier : lots résiduels d'abord ;
libellé carte : **« Lot À DÉCOUPER (hypothétique — le lot proposé exige un découpage
géomètre) »**. En table : 139 `decoupe` + 14 `libre` + 1 `demolition`.

## D — Dossier de revue (session neuve)

- **`docs/mandats/O12_PARTIEL_REVUE.pdf`** — 20 cartes échantillonnées en tourniquet sur les
  22 communes du pool (le rang-1 de 20 communes, tri clarté) : lot découpé (tracé STOCKÉ du
  run), bâti, **voirie**, métriques + emprise restante + zonage.
- **`docs/mandats/O12_PARTIEL_EXEMPLES.pdf`** — les 5 exemples (régénérés post-correctif
  anti-enclavement : 2 des 5 initiaux avaient été éliminés par la garde, preuve qu'elle mord).
- **`docs/mandats/O12_PARTIEL_REVUE.zip`** — les 2 PDF + `pool_decoupe.csv` (les 139, toutes
  métriques) + log du run. **Prêt pour la revue en session neuve.**

## Preuves & finding

- Golden **116/116 PASS** après chaque étape ; tests `test_division_or.py` **9/9**.
- EXPOSE reste `False` — rien d'exposé avant la revue des 20 cartes.
- Finding d'ingénierie : les `ALTER … IF NOT EXISTS` du DDL par commune se mettent en FILE
  (verrou exclusif) derrière chaque INSERT long en parallèle — workers bloqués ~40 min sur un
  no-op. Corrigé : `_ensure_ddl` saute le DDL quand le schéma est déjà au dernier état.
