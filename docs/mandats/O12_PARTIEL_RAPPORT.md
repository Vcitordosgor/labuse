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

**⏸ STOP — validation demandée avant le run île (B).** Si la méthode ne convient pas
(découpes jugées non plausibles), on s'arrête là, conformément au garde-fou n° 2.

---

## B — Run île *(après GO)*

## C — Deux familles distinctes *(acté dans le code, cf. A)*

## D — Dossier de revue *(après B)*
