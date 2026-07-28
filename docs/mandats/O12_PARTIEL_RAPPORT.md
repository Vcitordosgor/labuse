# MANDAT O12-PARTIEL — Le lot découpé

Branche `feat/o12-partiel` (depuis `feat/o12-ile`). **EXPOSE = `True`** (Vic, 28/07/2026).
Inversion d'approche : au lieu de « que reste-t-il après le bâti ? », « quel lot pourrait-on
découper ? » — un SOUS-POLYGONE compact, pas le résiduel entier.

---

## CLÔTURE (28/07/2026) — EXPOSE=True · pool 35

Le segment est validé après **2 revues visuelles exhaustives** (les 44 puis les 36/35 cartes),
**une contre-preuve de mécanisme** (le bug `liee_geometrie` qui s'auto-annulait) et **un verdict
de calibrage PLU** (emprise réelle). **Aucun faux positif connu n'y survit** — c'est ce qui
permet de le servir. Câblage client = M22-D (section divisibilité du Rapport de potentiel).

### Le chemin complet du filtrage
**5 916 → 294 → 15 → 139 → 45 → 36 → 35.** Sept étapes : (1) `5 916` résiduels bruts →
(2) `294` après correctifs A (ratio ≤ 50 %, zone U/AU, clarté plafonnée) → (3) `15` après les
gardes de forme et de viabilité (littoral, emprise, solidité…) sur la famille résiduelle →
(4) `139` lots à DÉCOUPER (inversion « bande de façade ») → (5) `45` après les correctifs de
revue (connexité + érosion, bâti d'activité, voirie qualifiée, fraîcheur) → (6) `36` après
solidité + arbitrage des douteux → (7) `35` après re-confrontation au plafond PLU réel (BO0089
tombe). Pool final servi : **27 découpes + 8 résiduels**.

### Trois limites/dépendances GRAVÉES (conditions du service)
1. **Rappel non mesuré — limite connue, pas un oubli.** Le pool a été généré sous le défaut
   d'emprise permissif à **60 %** en amont ; des candidats situés en zone à plafond SUPÉRIEUR
   (ex. Saint-Denis Ud à **80 %**) ont pu être rejetés à la génération et **ne sont pas
   récupérés**. Le pool est donc **conservateur par construction** — c'est le bon côté de
   l'erreur, mais il est écrit : ré-ouvrir le rappel exigerait un re-run complet du détecteur
   avec les 21 PLU calibrés (perf 5-6 h/grosse commune).
2. **`BH1036` (Sainte-Suzanne UB, 56 % au repli 60 %) — sur liste de surveillance.** Passe tant
   que la zone n'a pas d'emprise chiffrée ; **marqué en base (`note_revue`) et dans
   `reports/o12-ile/pool_complet.csv`** pour qu'un futur passage le retrouve sans chercher.
3. **`scripts/o12_emprise_recheck.py` = contrôle RÉCURRENT, pas un script d'un jour.** À
   relancer **après chaque évolution des PLU** : un plafond nouvellement chiffré (ou abaissé)
   peut faire tomber un candidat. C'est une **dépendance du segment**, au même titre que le
   garde-fou de fraîcheur bâti (PC Sitadel ≥ 2023). Le flag `EXPOSE=True` porte ce rappel en
   commentaire ; à recontrôler avant toute régénération du dossier.

### Suite
Vic **merge** `feat/o12-partiel` (Fable ne merge jamais), puis **M22-D** branche la section
divisibilité du Rapport de potentiel (`_divisibilite()` lira `EXPOSE`) en commit dédié.
Golden **116/116**, tiers au bit près. Tests `test_division_or.py` **12/12**.

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

---

# MANDAT O12-PARTIEL-2 — correctifs post-revue (NO-GO en l'état) ⏸ POINTS D'ARRÊT A & B

Revue visuelle des 20 cartes : méthode validée sur le fond, 6 correctifs exigés.
Tout est chiffré ci-dessous sur les **139 stockés** (géométries `lot_geom` en base — aucun
re-run nécessaire pour l'entonnoir) ; la SQL de PRODUCTION reproduit l'entonnoir au candidat
près (validée sur Petite-Île 2/2 et Saint-Benoît 6/6, transaction annulée).

## Entonnoir (mandaté, séquentiel sur les 139)

| Étape | Retirés | Restants |
|---|---:|---:|
| C2 — connexité stricte du reste (composantes > 1 m²) | **49** | 90 |
| C3 — lot nu strict (bâti ∩ lot ≤ 1 m², voisins compris) | 0 | 90 |
| C4 — zonages d'activité (liste config) | **3** | 87 |
| C5 — RNU : façade sur voirie qualifiée | 0¹ | **87** |

¹ le candidat RNU fautif (`97417000AO0329`, façade sur « Chemin ») tombe déjà en C2.

**Options en arbitrage (non appliquées)** : + C2-érosion → **66** ; + C5 étendu hors RNU → **48**.

## C1 — Gain estimé : retiré des fiches, piste gelée

**D'où venait le chiffre** : `gain_estime_eur` = `score_e.marge_estimee`, jointe par idu dans
`_INSERT` — c'est la **marge promoteur du Score É V2** pour une opération de PROMOTION sur la
**parcelle entière** (prix de sortie NEUF × SHAB constructible − coûts), pas le produit d'une
division. Elle est négative pour l'écrasante majorité des parcelles de l'île (fait connu du
Score É : marges serrées, médiane négative — cf. O0). Sur une fiche « Division en or », −2,1 M€
est donc un chiffre **sémantiquement faux**, pas seulement choquant : le bon ordre de grandeur
serait la valeur du TERRAIN À BÂTIR du lot (600-900 m² viabilisables), notion non calculée
aujourd'hui. **Fait** : ligne retirée des fiches (remplacée par la compacité), champ conservé
en table masquée, formule NON touchée (interdit du mandat). Refonte ou abandon : décision Vic.

## C2 — Connexité du lot restant

Implémenté : le reste (parcelle − lot) doit être **d'un seul tenant** — composantes comptées
avec une **tolérance de 1 m²** (les slivers cadastraux observés font < 1 m² ; documentée).
**−49 sur 139** — liste complète : AT0140, AW0372, CH0239, CH3356, CP0890, DP0101 (Saint-Paul) ·
AH0386, AB0189² (Saint-Benoît) · EN3624, EO0702 (Saint-Louis) · IE0466, HX0397 (Saint-Pierre) ·
CX0846 (Saint-Denis) · AE0970, AE0697, AV0453, AV0695, BI0296 (Le Tampon) · BM1224, BM1352,
BX1357, CE2730 (Saint-Joseph) · CO0123, CQ0450, CS0256, DC0859 (Saint-Leu) · AI0612, BE0102
(Saint-André) · AI0780, AI2095, AM0716 (Cilaos) · AO1130, AP3000, AP3016, AP4237, BO0227,
BW0054 (Sainte-Marie) · AE0876, AV0200 (L'Étang-Salé) · AO0843, AS0857, AS1883 (Entre-Deux) ·
AM0243, AN0518, AN1648 (La Possession) · AI0524 (Sainte-Rose) · AN0302, BC0185 (Salazie) ·
AE0235 (La Plaine-des-Palmistes) · AO0329 (Saint-Philippe). ² voir ci-dessous.

**Les 3 cas nommés par la revue — constat honnête** : leur reste est CONNEXE au sens strict
(il tient par un couloir) — la connexité stricte ne les attrape pas.
- `97410000AB0189` et `97408000AC1115` : attrapés par la **variante érosion** (reste rétréci
  de 2 m, composantes > 25 m² — un couloir < 4 m de large ne « connecte » plus) : **−21 de
  plus** sur le pool post-mandat (87 → 66). → **Arbitrage : appliquer l'érosion ?** (reco : oui)
- `97418000AI0768` : ni strict ni érosion (reste d'un seul côté) — mais sa façade repose sur
  une **route empierrée** : il tombe si C5 est étendu hors RNU (ci-dessous).

## C3 — Lot ∩ bâti : 0 partout, critère appliqué quand même

`aire_bati_dans_lot_m2` calculée contre **tous** les bâtiments (voisins compris) et rendue en
table + CSV : **0,0 m² pour les 139** — conforme à la construction (lot ⊂ résiduel, bâti
bufferisé 3 m retiré). Les recouvrements VUS en revue (CX0214, AH1514, AZ0485, AC0262, AS1883)
sont des **artefacts** : bâtiments visibles sur l'ortho mais ABSENTS de BD TOPO (constructions
récentes/légères — distance au bâti vectoriel le plus proche : 7,9 m pour CX0214) ou parallaxe
ortho/cadastre. Le critère `≤ 1 m²` (bruit de numérisation, documenté) est appliqué en défense
en profondeur. **Risque résiduel consigné** : le millésime BD TOPO peut rater du bâti réel —
seule la revue visuelle (ou un contrôle ortho type module détection) le voit.

### C3.3 — Distance lot ↔ bâti conservé ⏸ POINT D'ARRÊT B (chiffré, non appliqué)

Par construction le lot est à **≥ 3 m du bâti de SA parcelle** (buffer). Mesuré contre TOUS
les bâtiments (voisins compris) : **2 candidats à < 1 m** (min 0,4 m) et **19 à < 3 m** — tous
dus à des bâtiments VOISINS en limite. Options : (a) rien — la garde structurelle couvre le
bâti conservé, objet littéral du sous-point ; (b) ≥ 1 m contre tous bâtiments → **−2** ;
(c) ≥ 3 m contre tous → **−19**. **Reco : (b)** — un lot collé au mur du voisin est aussi
ininstruisible que collé au sien. Attendre le GO.

## C4 — Zonages d'activité : exclusion par config, liste sourcée

`config/o12_zones_activite.yaml` — trois niveaux de preuve, AUCUNE devinette :
**explicite** (description GPU : 10 communes), **calibré** (`habitat: interdit` du PLU
Saint-Paul : U1e, U1ec, U2e, U3e, AU5e), **inféré** (famille « e » sans description — convention
confirmée par les 10 communes explicites ; réfutable, cf. Bras-Panon `1AUe` gardé hors liste
car sa description dit « urbanisation prioritaire SAR »). Cilaos, Salazie, Saint-Joseph,
Saint-Philippe : rien au GPU. **Retire 3** du pool : `97405000AW1275` (UEa — le cas de la
revue), `97405000AW1526` (UEa), `97410000BD0537` (Ue Saint-Benoît).

**Libellés AMBIGUS — arbitrage demandé (non exclus)** :
- *touristiques/loisirs* : UT/AUT (Petite-Île), UT (Saint-André), UT/UTp (Sainte-Marie),
  Ut/AUt1/AUt2 (Saint-Pierre) ;
- *équipements/aéroport/militaire/parcs* : Ue « principaux équipements », Uea (aérodrome),
  Uemi (militaire), Uep (parcs) à Saint-Pierre ; UR (aéroport Roland-Garros, Sainte-Marie) ;
- *AU à ouverture différée* : AUx (Saint-Denis, « stricte »), 2AU*/3AU* divers ;
- *divers* : Uva (coulée verte, Saint-Denis), Uat (ZAC Triangle, Saint-Denis), UZ/1AUz
  (ZAC Cambrai, Petite-Île), 2AUec/AUst (équipements-commerces, Bras-Panon — EXCLUS car
  « activités économiques » explicite ; signalés par transparence).
- **Hors mandat mais à signaler** : le pool RÉSIDUEL validé contient `97411000BP0363`
  (Saint-Denis) en zone **Ua « zone d'activités du Chaudron »** — validé en revue des 16,
  non touché ici. Arbitrage : l'exclusion doit-elle s'appliquer aussi à la famille résiduelle ?

## C5 — Qualification des voiries

**Source** : `spatial_layers kind='voirie'` = **BD TOPO IGN**, nature portée par `subtype`
(les `attrs` sont vides — pas d'attribut « accès réglementé » ingéré). Qualifiés « ouverts à
la circulation publique » : *Route à 1 chaussée, Route à 2 chaussées, Rond-point*. Non
qualifiés : *Chemin (58 337), Sentier (20 094), Route empierrée (22 426), Escalier, Type
autoroutier, Bretelle* (l'empierrée est carrossable mais rien ne prouve l'ouverture publique —
prudence). **Implémenté (mandat)** : candidat RNU → façade contiguë ≥ 12 m sur voirie
QUALIFIÉE. Concerné : 1 candidat RNU (`97417000AO0329`, façade sur « Chemin » — le cas vu en
revue, la « route » au nord-ouest n'est pas son linéaire de façade) ; il tombe déjà par C2.
**Constat île entière (arbitrage)** : **40/139** lots ont leur façade sur du linéaire non
qualifié (18 encore présents dans le pool post-mandat) — étendre la qualification à TOUTES les
communes ? (reco : oui — un lot « à bâtir » desservi par un sentier n'est pas plausible ;
cela attrape aussi `AI0768`). Ce serait un DURCISSEMENT du critère façade, pas un
assouplissement.

## C6 — Sensibilité au plancher 600 m² (documentation, aucun seuil touché)

Sur les 139 : **81 lots < 650 m²** (58 %), **113 < 700 m²** (81 %), pic de **31 lots entre
620 et 630 m²**. Explication STRUCTURELLE : parmi les découpes valides, l'algorithme retient
la MEILLEURE COMPACITÉ — le carré ~25 × 25 m = 625 m² est l'optimum géométrique de la bande
(ancre 25 m) ; le pic à 625 est un artefact de sélection, PAS un signe de pénurie : 84/139
parcelles gardent un reste ≥ 1 000 m² après découpe. Si le plancher montait à 650/700,
l'algorithme choisirait des bandes plus profondes (25 × 26+) sur les mêmes parcelles — la
perte attendue est faible, mais un chiffre EXACT exigerait un re-run à plancher modifié
(non fait : aucun seuil touché).

## État des points d'arrêt

- **⏸ A (GO re-run île)** : entonnoir mandaté 139 → **87**. Questions ouvertes qui changent
  le pool final : C2-érosion (→ 66), C5 étendu (→ 48), et les deux listes d'arbitrage C4.
- **⏸ B (sous-point C3.3)** : chiffré ci-dessus — reco option (b), −2.
- Après GO : re-run île complet → `pool_decoupe.csv` (avec `aire_bati_dans_lot_m2`) →
  20 cartes (sans marge Score É, compacité affichée) + 5 exemples + zip session neuve.

---

# GO Vic (27/07/2026) — arbitrages appliqués et re-run île

Tous les arbitrages pris : **érosion 2 m** (couloir < 4 m ≠ accès utilisable — largeur
minimale d'un passage carrossable ; références SANS application : érosion 1 m rejetterait
53/139 en isolation, 3 m en rejetterait 38 — le 2 m est entre les deux et porte une
justification physique, pas un réglage fin) · **C5 étendu à toutes les communes** ·
**C4 ambigus tous exclus** (config mise à jour, touristiques marqués pour réouverture v2) ·
**filtre-LIBELLÉ** sur les deux familles · **distance bâti ≥ 1 m** (garde-fou de COHÉRENCE
GÉOMÉTRIQUE — un lot à 0,4 m d'un mur signale une erreur de donnée — PAS une règle
d'urbanisme : le 3 m est refusé car il simulerait un contrôle de prospect que le dossier
refuse explicitement de prononcer).

## Entonnoir FINAL (séquentiel sur les 139 ; re-run île = même résultat au candidat près)

| Étape | Retirés | Restants |
|---|---:|---:|
| C2 — connexité stricte du reste (composantes > 1 m²) | 49 | 90 |
| C2-érosion — reste rétréci de 2 m toujours d'un seul tenant | 22 | 68 |
| C3 — lot nu strict (bâti ∩ lot ≤ 1 m²) | 0 | 68 |
| C3.3 — lot à ≥ 1 m de tout bâti | 0¹ | 68 |
| C4 — codes exclus (activité + arbitrés + 2AU*/3AU*) | 6 | 62 |
| C4-libellé — mots-clés d'activité dans le descriptif | 0² | 62 |
| C5 étendu — façade sur voirie qualifiée partout | 17 | **45** |

¹ les 2 cas < 1 m tombent déjà en amont. ² redondant avec les codes sur ce pool — mais c'est
lui qui attrape **BP0363** (« Ua : zone d'activités du Chaudron ») côté résiduel : le filtre
par code ne suffit pas, le libellé complète (finding traité).

**Ventilation C5 par catégorie** (les 40 façades non qualifiées, pour réouverture éventuelle
d'une sous-catégorie sans re-run) : **route empierrée 23 (+1 mixte chemin)** · chemin 8
(+2 mixtes) · sentier 7 (+1 mixte). La sous-catégorie « empierrée » est la plus grosse — si
elle recouvre de vraies voies publiques des Hauts, sa réouverture rendrait ~24 candidats.

**Filtre-libellé, prises code par code** (pools avant re-run) : Petite-Île AUE (1), UEa (1) ·
Saint-Benoît Ue (1) · **Saint-Denis Ua (1, pool RÉSIDUEL — BP0363)**. Aucun autre code
générique ne cachait de zone d'activité dans les pools actuels ; le filtre reste actif pour
les runs futurs. Descriptions MIXTES protégées (habitat/« commerces de proximité » : Ud
Bras-Panon, UA Saint-André — vérifiées non touchées).

## Pools finaux (re-run île complet, 24 communes)

- **Lot résiduel : 14** (13 libres + 1 démolition, 7 communes) — seule perte vs pool validé :
  `97411000BP0363` (retrait ordonné). Distributions inchangées (lots 509-883 m², compacité
  0,280-0,717).
- **Lot à découper : 45**, 14 communes : Saint-Paul 7 · Le Tampon 7 · Saint-Pierre 6 ·
  Saint-Joseph 5 · Saint-Benoît 4 · Saint-Denis 4 · Cilaos 2 · Saint-André 2 · Saint-Leu 2 ·
  Sainte-Marie 2 · Entre-Deux, La Possession, Les Trois-Bassins, Saint-Louis 1.
  Lots 606-781 m² (médiane 632) · compacité 0,312-0,793 (médiane 0,706) · façade médiane
  27,6 m · emprise restante max 0,556 · `aire_bati_dans_lot_m2` = 0 partout (colonne au CSV).
- **Total : 59 candidats.** Le vivier est passé sous les ~139 comme attendu — 40 % des cartes
  de la revue précédente étaient suspectes, les 139 n'étaient pas servables ; 59 propres
  valent mieux. (Seuil d'alerte « < 30 » du mandat : non atteint.)

---

# REVUE 2 (27/07/2026) — 14/20 propres · analyses demandées ⏸ ARBITRAGE PLANCHER

## 1 — Plancher de compacité : distribution et coût des trois seuils

Déciles de la compacité des 45 lots : D0 0,312 · D1 0,492 · D2 0,533 · D3 0,621 · D4 0,667 ·
**D5 0,706** · D6 0,739 · D7 0,785 · D8 0,785 · D9 0,785 · D10 0,793.

| Plancher | Survivants | Pool total (avec 14 résiduels) | Cartes visées tuées |
|---:|---:|---:|---|
| 0,55 | 36 | 50 | AC0118 (0,312) · AE0284 (0,485) |
| **0,60** | **33** | **47** | + AT0650 (0,552) |
| 0,65 | **29 — SOUS 30** | 43 | + CX0720 (0,647) |

**Constat honnête : aucun plancher ne tue les 5 cartes visées.** `AV0203` (0,665) survit même
à 0,65 — un lot en U autour d'une PETITE maison peut rester compact au sens Polsby-Popper.
Le plancher réduit la classe, il ne l'éradique pas ; l'éradication demanderait un critère de
convexité (ex. aire/aire de l'enveloppe convexe), non chiffré ici. À 0,60 (préférence
annoncée) : 33 découpes + 14 résiduels = 47, au-dessus du seuil d'alerte. `CX0720` (0,647)
survivrait à 0,60 — mais il est aussi l'un des cas « > 50 % » ci-dessous.

## 2 — Les « > 50 % » : pas une fuite, une règle propre à l'autre famille — en-tête corrigé

La borne « lot ≤ 50 % de la parcelle » (correctif A2) appartient à la famille **lot
RÉSIDUEL** : elle rejette les parcelles dont le terrain libre entier dépasse la moitié
(démembrement). L'univers du **lot à découper** est PRÉCISÉMENT le complément (résiduel
> 50 %) et sa borne est ABSOLUE (600-900 m²) + viabilité du reste — jamais un ratio. Sur
petite parcelle, le lot dépasse mécaniquement 50 % : **6 cas sur 45** (CR0093 50,7 % ·
CX0720 50,9 % · AT0650 55,2 % · CV0219 55,3 % · BO0089 55,8 % · AV0573 64,3 %). Aucun filtre
ne fuit — mais l'en-tête du dossier affirmait la règle globalement : **corrigé** (l'intro
détaille désormais les règles PAR famille et dit explicitement que la borne 50 % ne
s'applique pas aux découpes).

**Glissement de population documenté** : après l'érosion et C5, les parcelles retenues sont
plus petites — min 1 060 · P25 1 536 · médiane 1 975 m² (16/45 sous 1 600 m²) ; le lot y pèse
mécaniquement plus lourd. Point d'attention connexe : la famille découpe n'a PAS d'équivalent
du « le lot bâti garde ≥ 400 m² » du résiduel — **1 cas** de reste < 400 m² (`AV0573`,
378 m² + maison, et 64,3 % de ratio). Si un garde « reste ≥ 400 m² » était souhaité : −1.

## 3 — CX0214 : risque de fraîcheur, non classé — note source & recoupements

- **Source bâti** : BD TOPO IGN V3, flux WFS Géoplateforme (`BDTOPO_V3:batiment`), ingérée
  les **28-29/06/2026** (817 506 bâtiments). Le flux sert l'édition IGN courante à cette
  date ; le délai intrinsèque de BD TOPO sur les constructions neuves (mise à jour
  photogrammétrique) est de plusieurs mois à années — le millésime TERRAIN réel est donc
  antérieur à 2026, sans précision disponible en base.
- **Recoupement possible en base, coût faible (une jointure SQL)** : `sitadel_permits`
  (50 043 permis 2013-2026, liens parcellaires `idu_codes`). Appliqué aux 45 : **2 candidats
  portent un PC récent sur la parcelle** — `97416000CZ2174` (PC du **05/11/2025**, bâti
  probablement en chantier, invisible de BD TOPO — le cas dangereux type) et `97416000CO0911`
  (PC 02/2023). **CX0214 lui-même : recoupement NÉGATIF** — aucun permis sur la parcelle
  (plus proche : 50 m, 2017) ; les structures visibles sont soit non déclarées, soit un
  artefact de parallaxe. Le recoupement Sitadel ne blanchit donc PAS ce cas.
- **Recoupement lourd disponible** : le module détection ortho (config/detection_ortho.yaml,
  tuiles RVB) pourrait comparer l'emprise bâtie VUE à la couche vecteur — coût : run tuiles
  sur les lots (~heures) + calibration. Non lancé.
- **Limite consignée du segment** : « lot nu » est affirmé au vu de BD TOPO ; toute
  construction postérieure au millésime IGN (déclarée ou non) est invisible du détecteur —
  seule la revue visuelle sur ortho récente, ou un recoupement permis/ortho, la voit.
  Aucun classement de CX0214.

**Aucun re-run, aucun filtre appliqué — en attente de l'arbitrage plancher** (et, s'il est
souhaité, du garde « reste ≥ 400 m² » et du flag permis-récent).

---

# REVUE 2 — arbitrage SOLIDITÉ : chiffres et branche déclenchée ⏸ (pas de re-run)

## Solidité (aire ÷ enveloppe convexe) des 45

Déciles : D0 0,687 · D1 0,789 · D2 0,826 · D3 0,884 · D4 0,912 · D5 0,948 · D6 0,973 ·
D7 0,995 · D8-D10 1,000.

| Les 5 en U | solidité | compacité | | Les 14 validées | solidité |
|---|---:|---:|---|---|---:|
| AC0118 | 0,687 | 0,312 | | CS0625 (la plus basse) | **0,898** |
| AE0284 | 0,785 | 0,485 | | BW0123 | 0,938 |
| AT0650 | 0,860 | 0,552 | | AH1514, AV0207 | 0,946-0,948 |
| CX0720 | 0,884 | 0,647 | | les 10 autres | 0,961-1,000 |
| AV0203 | **0,912** | 0,665 | | | |

| Seuil | Survivants/45 | U au-dessus | Validées perdues |
|---:|---:|---|---|
| 0,80 | 40 | AT0650, CX0720, AV0203 | aucune |
| 0,85 | 35 | AT0650, CX0720, AV0203 | aucune |
| 0,90 | 28 | AV0203 | CS0625 |

## Branche déclenchée : la 2 — avec un constat que la règle n'avait pas prévu

- **Branche 1 (séparation propre) : NON** — AV0203 (0,912) est AU-DESSUS de la validée la plus
  basse (CS0625, 0,898) : aucun seuil ne sépare proprement.
- **Branche 2 (imparfaite mais bonne, ≤ 1 validée perdue) : OUI** — atteignable à 0,90
  (4 U tués, 1 validée perdue). Action appliquée telle qu'écrite : **solidité au seuil qui
  préserve les validées (0,85) + plancher de compacité 0,55**.
- **Constat honnête** : sur ce pool, solidité et compacité attrapent LES MÊMES deux extrêmes
  (AC0118, AE0284) — la prémisse « la solidité voit ce que Polsby-Popper ne voit pas » ne se
  vérifie pas ; à 0,85 la compacité 0,55 ne retire plus rien (gardée en ceinture). Les trois
  U « modérés » (AT0650 0,860 · CX0720 0,884 · AV0203 0,912) ne sont séparables par AUCUN
  réglage sans perdre une validée. **Ils sont portés à la liste d'exclusions de revue**
  (`config/o12_exclusions_revue.yaml` — le mécanisme traçable créé pour CX0214 : ces trois cas
  ont été VUS et JUGÉS en revue, c'est exactement son usage ; réversible en retirant l'entrée).
  La classe « U modéré NON VU en revue » reste une **limite consignée du segment** — un critère
  géométrique ne la sépare pas des bandes franches validées.

## Gardes appliqués (GO revue 2) — entonnoir prévisionnel sur les 45 stockés

| Étape | Retirés | Restants |
|---|---:|---:|
| Solidité ≥ 0,85 | 10 | 35 |
| Compacité ≥ 0,55 (ceinture) | 0 | 35 |
| Reste ≥ 400 m² (aligné famille résiduelle) | 1 (AV0573, 378 m²) | 34 |
| Fraîcheur : PC ≥ 01/01/2023 sur parcelle | 2 (CZ2174 PC 11/2025 · CO0911 PC 02/2023) | 32 |
| Exclusions de revue (CX0214 + 3 U) | 4 | **28** |

**Pool prévisionnel : 28 découpes — SOUS 30, signalé** (+ 14 résiduels = 42). Nuance : la
solidité s'applique désormais DANS la grille de découpe (3 ancres × 5 profondeurs) — le re-run
peut REPÊCHER des parcelles dont le lot stocké était en U mais qu'une autre ancre découpe en
bande franche : 28 est un plancher, le chiffre exact viendra du re-run.

**Fenêtre fraîcheur justifiée** : BD TOPO ingérée 28-29/06/2026 ; sa mise à jour bâti repose
sur une ortho millésimée (cycle DOM ~3 ans, dernier millésime exploitable ~2023) + 12-18 mois
de chantier après PC → tout PC déposé depuis le 01/01/2023 peut être bâti mais invisible de la
couche. Gravé : **« lot nu » = nu au vu de BD TOPO (millésime), recoupé Sitadel (PC) — rien de
plus n'est affirmé.** (En passant : les 14 résiduels ont été recoupés — aucun PC ≥ 2023.)

**Réserve ortho (information, pas d'action)** : la brique existe — `ortho_piscines.py` =
FLAIR-INC (segmentation multi-classes Etalab, la classe *bâtiment* en fait partie) + probe
DINOv2, 100 % local sur les tuiles RVB déjà outillées (`ortho_detections`). Un contrôle
« bâti visible dans le lot » réutiliserait l'infrastructure telle quelle ; seuls le profil de
décision et la calibration seraient à refaire (l'équivalent du travail piscines).

---

# REVUE 2 — GO solidité : re-run exhaustif, mécanisme de tracé, pool final 44

## Ce que le re-run a produit (`scripts/o12_rerun_v3.py` — snapshot → résiduel → découpe)

**Familles : découpe = 30 · libre = 13 · démolition = 1 → 44 candidats.** Solidité des découpes :
min **0,858** (au ras du seuil 0,85, par construction), médiane 0,978, max 1,000 ; compacité
0,571-0,793 ; lots 606-703 m² (médiane 629). **Entonnoir final** : 45 découpes revues → 30
(les 15 retraits = solidité < 0,85, reste < 400, PC frais, exclusions de revue) + **2 repêchées**
via une ancre alternative que la contrainte solidité-dans-la-grille a fait gagner. Comme prévu,
28 était un plancher : le re-run remonte à 30.

Toutes les exclusions ont TENU (vérifié : 0 ligne pour les 4 exclusions de revue + les 2 PC
frais). Les 3 U liés-géométrie sont sortis parce que leur tracé re-calculé est identique au
snapshot ; CX0214 est sorti par IDU (permanent).

## Le mécanisme « à revoir » a mordu — 1 cas

Statut de tracé vs revue précédente : **inchangé = 29 · modifié = 1 · résiduel = 14**.
Le cas modifié est **`97422000AV0573`** (Le Tampon) : c'est exactement la parcelle dont le reste
faisait 378 m² (< 400). La contrainte « reste ≥ 400 m² » a écarté son ancien lot ; une autre
ancre en produit un nouveau (reste ≥ 400), de tracé différent (différence symétrique 5,6 %).
Il revient donc au dossier avec le bandeau **« ✎ Tracé MODIFIÉ depuis la revue précédente — à
revoir »** au lieu d'être gardé silencieusement ou perdu. C'est précisément le comportement
demandé : *la validation portait sur un tracé, pas sur un IDU.*

## Les deux natures d'exclusion (config/o12_exclusions_revue.yaml)

| Nature | IDU | Comportement au re-run |
|---|---|---|
| `permanente` | CX0214 | exclu par IDU, quelle que soit la géométrie (bâti douteux non blanchi) |
| `liee_geometrie` | AT0650, CX0720, AV0203 | exclu **seulement si** le lot re-calculé ≈ le tracé revu (snapshot `division_or_revue_snapshot`, différence symétrique < 2 %) ; un tracé modifié reviendrait au dossier |

Snapshot pris **avant** toute destruction (l'orchestrateur photographie les 45 découpes, puis
TRUNCATE résiduel, puis rebuild découpe) ; `snapshot_review_lots` est non destructif quand il
n'y a rien à photographier, pour survivre au TRUNCATE intermédiaire.

## Règle de gouvernance gravée (revue 2)

**Ce segment ne s'expose qu'après revue de 100 % du pool, tant qu'aucun critère géométrique
n'attrape la classe des « U modérés ».** La revue 2 l'a établi : solidité et compacité ne
séparent pas AV0203 (0,912) d'une bande franche validée (CS0625, 0,898) — un défaut visible
seulement à l'œil rend l'échantillon insuffisant. Si le pool grossit un jour au point de rendre
la revue exhaustive impraticable, c'est le **critère manquant** qu'il faudra trouver — pas
l'échantillon qu'il faudra reprendre. Le dossier est donc désormais EXHAUSTIF (`--all` : une
carte par candidat, découpes par commune puis résiduels, solidité + compacité + statut de tracé
affichés).

---

# REVUE 3 — corrections + DEUX bugs de mécanisme trouvés et corrigés

Pool final : **28 découpes + 10 résiduels = 38** (34 servables + 4 douteux en attente d'arbitrage).
Golden 116/116, tiers au bit près, tests 12/12, EXPOSE reste False.

## 1 — AV0203 a percé : IDU FANTÔME (bug de saisie) → verrou

Cause exacte : le vrai U de Saint-Denis est `97411000AV0203` (INSEE 97411) ; la config portait
`97416000AV0203` (préfixe 97416 = Saint-Pierre), **un IDU qui n'existe dans AUCUNE parcelle** →
l'exclusion n'a jamais rien matché. Origine : dans l'analyse solidité je résolvais les IDU par
suffixe (`endswith`), donc l'analyse utilisait le bon 97411 ; en recopiant à la main dans le
YAML j'ai figé le préfixe brut erroné. Les 2 autres U (AT0650, CX0720) avaient le bon IDU.

**Verrou** (`test_exclusions_revue_idu_coherents`, sans DB, déterministe) : chaque exclusion
porte une `commune` OBLIGATOIRE, et les 5 premiers chiffres de l'IDU doivent ÉGALER son INSEE
(`check_exclusions_revue`). Un IDU-fantôme est détecté au test ET écarté au chargement
(`_exclusions_revue` fail-safe : une config incohérente n'exclut rien, plutôt que d'exclure la
mauvaise parcelle).

## 2 — AT0650 a REPARU : le mécanisme `liee_geometrie` s'auto-annulait (2e bug)

Découvert en comparant le pool re-calculé au CSV v3 : `97409000AT0650` (exclu en v3) était
revenu. Cause : `liee_geometrie` comparait le tracé re-calculé au **snapshot**, or le snapshot
est reconstruit depuis le pool à chaque run — une fois AT0650 exclu, il quitte le pool, donc le
snapshot suivant, donc la comparaison perd sa référence et la parcelle **reparaît**. Le
mécanisme se défaisait après un tour.

**Correctif** : le détecteur étant DÉTERMINISTE (le tracé d'une parcelle est identique à chaque
run tant que le code ne bouge pas), toutes les exclusions passent en **`permanente` (par IDU)** —
robuste, garantit la non-réapparition (ta demande explicite). La nuance « re-revoir si
l'algorithme produit un autre tracé » reste couverte par la RÈGLE de revue exhaustive à chaque
changement d'algorithme. Le snapshot ne sert plus qu'à l'annotation « tracé modifié » (info).
`liee_geometrie` est abandonnée (documenté dans le yaml et le code).

## 3 — Résiduels : tri à la main des 4 FP (pas de plancher systématique)

Les planchers découpe (0,85/0,55) appliqués aux résiduels tuent **10/14 dont des validés**
(BV0182 démolition 0,773 ; CR0068 0,847) — même 0,80/0,50 en tue 7. Les 4 FP que tu as repérés
sont les **4 plus basses solidités** (≤ 0,672), nettement sous le premier validé (0,773). Un
résiduel est du terrain libre existant (sa forme est un FAIT, pas une proposition de l'algo) :
**pas de plancher systématique**, exclusion à la main des 4 FP (permanente). Distribution des 14
au rapport ci-dessous (§ REVUE 3 data).

**Mon avis sur les 4 douteux** (tu tranches) : `CM0143` (0,713/0,391 — métriques DANS le cluster
FP, compacité 0,391) → **je pencherais EXCLURE** · `AO0805` (0,853/0,535, façade 12,3 m au ras,
emprise restante 59 %) → **EXCLURE (prudence)** : reste petit et mal desservi · `BH1036`
(0,828/0,485, façade 40 m) → **GARDER** (grande façade, pas un U ; emprise 56 % à noter) ·
`AV2092` (0,893/0,505, zone UB « quartiers résidentiels » vérifiée, non spécialisée) → **GARDER**.

## 4 — DM0665 (Saint-Pierre, Ud) : zone vérifiée = OK

Libellé GPU : **« Zone urbaine mixte de centralité »** — non spécialisée (ni activité, ni
touristique). Géométrie excellente (solidité 0,948 / compacité 0,697, façade 55 m). Reste
validée. Si l'ortho montre un équipement réel, c'est un fait d'usage que le zonage (mixte) ne
capte pas — mais rien ne justifie l'exclusion côté zonage.

## Findings d'ingénierie (consignés)

- **Erreur de méthode (la mienne)** : mes changements de revue 3 ne font que RETIRER 6 parcelles.
  Le geste correct était `DELETE FROM division_or_candidates WHERE idu IN (…)`, PAS un TRUNCATE +
  re-run complet. J'ai lancé le re-run, buté sur la perf (ci-dessous), puis **reconstruit** le
  pool découpe depuis l'état v3 revu (CSV attributs + snapshot géométries) moins les exclusions —
  déterministe, identique à un run propre. Leçon : un changement « removal-only » = DELETE.
- **Perf du détecteur découpe** : sur les 2 plus gros viviers (Saint-Paul, Le Tampon), une passe
  dépasse **5-6 h**. Cause : `ST_MaximumInscribedCircle` (coût invisible au planner) évaluée
  ~2× × (3 ancres × 5 profondeurs) par parcelle candidate, plus `ST_ConvexHull`/`ST_Area`
  recalculés. **TODO** (à tester séparément, non fait ici pour ne pas risquer la sortie
  déterministe juste avant livraison) : dans la CTE `carve`, matérialiser `aire/périmètre/
  convexe/rayon` une fois par candidat (LATERAL) au lieu de les recalculer en SELECT + WHERE →
  ~½ des appels `ST_MaximumInscribedCircle`. Le run résiduel est plus lent encore (deux variantes)
  mais tolérable.

## REVUE 3 data — distribution solidité/compacité des 14 résiduels

| idu | commune | zone | sol | comp | avis |
|---|---|---|---:|---:|---|
| AX0324 | L'Étang-Salé | UA | 0,573 | 0,280 | FP exclu |
| CR0776 | Saint-Paul | U3c | 0,615 | 0,367 | FP exclu |
| AP3270 | Sainte-Marie | UD | 0,662 | 0,416 | FP exclu |
| HX1065 | Saint-Pierre | Ug | 0,672 | 0,401 | FP exclu |
| CM0143 | Saint-Paul | U6a | 0,713 | 0,391 | douteux → exclure (reco) |
| BV0182 | Saint-Paul | U6c | 0,773 | 0,472 | validé (démolition) |
| BH1036 | Sainte-Suzanne | UB | 0,828 | 0,485 | douteux → garder (reco) |
| CR0068 | Saint-Leu | UC | 0,847 | 0,582 | validé |
| AO0805 | Sainte-Marie | UD | 0,853 | 0,535 | douteux → exclure (reco) |
| AM0946 | Saint-Joseph | U5 | 0,854 | 0,563 | validé |
| CX0585 | Saint-Leu | UD | 0,868 | 0,589 | validé |
| AV2092 | Sainte-Marie | UB | 0,893 | 0,505 | douteux → garder (reco) |
| CQ0412 | Saint-Leu | UD | 0,941 | 0,717 | validé |
| DM0665 | Saint-Pierre | Ud | 0,948 | 0,697 | validé (zone vérifiée) |

Survivants aux planchers découpe : **sol≥0,85/comp≥0,55 → 4/14** ; **sol≥0,80/comp≥0,50 → 7/14**
(tuent des validés) — d'où le tri à la main.

---

# REVUE 3 — clôture : arbitrage, traçabilité prouvée, pool intégralement revu

## Pool arbitré : 36 (28 découpes + 8 résiduels)

4 douteux tranchés (arbitrage Vic, = mes recos) : **CM0143 exclu** (métriques dans le cluster FP,
lot qui contourne le bâti à un carrefour) · **AO0805 exclu** (façade 12,3 m au ras + emprise
restante 59 %, reste quasi saturé) · **BH1036 gardé** (40 m de façade — la compacité basse vient
de l'allongement le long de la voirie, pas d'un contournement) · **AV2092 gardé** (zone UB
résidentielle vérifiée). Les 2 exclusions ont été appliquées par **`DELETE`** (removal-only, la
leçon), pas un re-run.

## DOCTRINE gravée — pas de plancher de forme systématique sur les résiduels

**Un lot résiduel est du terrain libre EXISTANT : sa forme est un FAIT du terrain, pas une
proposition de l'algorithme.** Un plancher géométrique systématique (solidité/compacité) y est
donc illégitime — et les chiffres le confirment : les planchers découpe (0,85/0,55) tueraient
BV0182 (0,773, démolition validée) et CR0068 (0,847), tous deux constructibles. On écarte les
faux positifs résiduels **à la main, en revue**, jamais par un seuil aveugle. (Les lots à
DÉCOUPER, eux, SONT des propositions de l'algorithme → les planchers s'y appliquent pleinement.)
Cette règle vaut pour toute évolution future du segment.

## Traçabilité de la reconstruction (les 3 conditions, rendues visibles)

1. **Preuve de coïncidence (déterminisme)** : le run frais des petites/moyennes communes a
   produit 18 découpes ; le CSV v3 en a 17 pour ces mêmes communes. **Seule différence :
   `97409000AT0650`** — le U que le bug `liee_geometrie` laissait passer (désormais permanent).
   Sur TOUTES les autres parcelles, le détecteur frais reproduit le CSV v3 au caractère près :
   le détecteur est déterministe, donc reconstruire depuis l'état v3 = re-tourner un run propre.
2. **Provenance par famille (lisible, colonne `provenance` du CSV)** : les **28 découpes** sont
   RECONSTRUITES (attributs = CSV v3 `[O12-PARTIEL-2 E]`, revu par Vic ; géométrie `lot_geom` =
   snapshot des tracés revus) ; les **8 résiduels** sont FRAÎCHEMENT calculés (run résiduel du
   run ciblé — le résiduel est rapide et sa géométrie déterministe). Aucune découpe des 4 gros
   viviers n'a été re-calculée à la grille (perf 5-6 h) : leurs tracés viennent de l'état revu.
3. **Conformité aux filtres de forme des 28 découpes** (reconstruites comprises), mesurée sur la
   table finale : solidité **min 0,880** (≥ 0,85) · compacité **min 0,608** (≥ 0,55) · reste
   **min 483 m²** (≥ 400) · bâti dans lot **0,0 m² partout** · **0** découpe avec PC Sitadel
   ≥ 2023. Toutes conformes.

## Statut de tracé des 36 (la question qui décide) : AUCUN modifié

| Statut vs revue précédente (44 cartes) | Nombre |
|---|---:|
| inchangé (découpe — lot_geom identique au tracé revu, différence symétrique nulle) | 28 |
| résiduel (tracé déterministe — résiduel recalculé, identique par construction) | 8 |
| **modifié** | **0** |

Les 28 découpes sont byte-identiques aux tracés revus (reconstruites DEPUIS le snapshot du pool
v3 qui a généré le dossier des 44 cartes) ; les 8 résiduels sont des recalculs déterministes du
même résiduel. **Aucun tracé n'a bougé → les 36 sont tous dans les 44 déjà revus → PAS de 4e
dossier de revue nécessaire.** (Le PDF `O12_PARTIEL_REVUE.pdf` est régénéré à 36 cartes comme
artefact à jour, pas comme nouvelle demande de revue.)

## Reste avant EXPOSE=True (points de sortie)

1. Ton **feu vert** au vu de ce rapport (pool 36, tracés inchangés, filtres conformes).
2. Ton **merge** de `feat/o12-partiel` (Fable ne merge jamais).
3. Branchement de la **section divisibilité du Rapport de potentiel (M22-D)** — commit dédié.

EXPOSE reste **False** jusqu'à (1)+(2). Golden **116/116**, tiers au bit près
(120 · 1031 · 3587 · 72980 · 353945). Tests `test_division_or.py` **12/12**.

---

# REVUE 3 — dernière marche : re-confrontation au plafond PLU RÉEL (post-merge nuit)

Le pool avait été calculé quand 2 communes seulement étaient calibrées (le reste au repli 60 %).
Les PLU de la nuit (`feat/plu-nuit-a` + `-b`, mergés sur main) gravent 21 communes ; les emprises
réelles sont souvent < 60 %. `feat/o12-partiel` a été mis à jour depuis origin/main (sens
main→feature — PAS le merge livrable, réservé à Vic). Verdict par `scripts/o12_emprise_recheck.py`
(lecture seule, mêmes règles que le détecteur : `emprise_sol_pct` calibrée si chiffrée, sinon 60 %).

## Résultat : 36 → 35, **1 faux positif tombe**

**`97418000BO0089`** (Sainte-Marie, découpe, zone **UD**) : emprise du lot restant **55,6 %** >
plafond réel **50 %** (UD calibré). Le défaut 60 % le laissait passer ; le vrai plafond l'écarte.
**Il sort du pool** (removal-only → `DELETE`, pas de compensation). Un re-run propre du détecteur
avec les 21 YAML le droppe de lui-même (le filtre emprise lit désormais le vrai plafond) → table =
sortie du détecteur, reproductible.

**Les 35 autres passent leur vrai plafond.** Notamment `AV2092` (douteux GARDÉ en revue 3,
Sainte-Marie **UB**) : emprise 56 % ≤ plafond réel **70 %** — la calibration CONFIRME de le garder.

## Les 20 candidats encore au repli 60 % (à part)

- **Commune non calibrée** (restent au défaut, comme annoncé) : Saint-André (`AR2367`), Saint-Leu
  (`CM0268, CQ0412, CR0068, CR0093, CX0585`).
- **Zone calibrée mais emprise « non fixée » au PLU** (Art. 9 sans chiffre → repli 60 % légitime) :
  Entre-Deux Ub, Le Tampon Uc, Saint-Paul U3c/U4b/U6c, Saint-Pierre Us, Sainte-Suzanne UB.

Un seul y est proche du plafond : **`BH1036`** (Sainte-Suzanne UB, 56 %) — passe au repli 60 %, à
re-confronter si cette zone reçoit une emprise chiffrée. Tous les autres sont ≤ 40 %.

## Honnêteté — effet à double tranchant (non compensé, assumé)

La calibration RETIRE un faux positif en zone à plafond bas (UD 50 %), mais elle pourrait aussi
ADMETTRE des candidats en zone à plafond HAUT (ex. Saint-Denis Ud 80 %) que le défaut 60 %
rejetait à la génération. Ce gain de rappel n'est PAS mesuré (il exigerait un re-run complet —
perf 5-6 h/grosse commune) et n'est PAS compensé : doctrine précision d'abord. On l'a su avant un
client, pas après — c'était l'objet de la marche.

## Pool FINAL : 35 (27 découpes + 8 résiduels)

Golden **116/116 PASS**, tiers au bit près — la mise à jour depuis main (PLU + copilote) n'a pas
touché le service. Tests **12/12**. Les 35 sont tous dans les 44 déjà revus, 0 tracé modifié,
désormais tous conformes à leur vrai plafond d'emprise. **EXPOSE reste False** jusqu'au feu vert
+ merge de Vic.

## Livrables (revue en session neuve)

- `docs/mandats/O12_PARTIEL_REVUE.pdf` — **44 cartes (pool complet)**, solidité + compacité +
  bandeau de statut de tracé sur chacune.
- `docs/mandats/O12_PARTIEL_EXEMPLES.pdf` — 5 exemples découpe.
- `reports/o12-ile/pool_decoupe.csv` — enrichi : solidité, compacité, emprise restante,
  aire_bati_dans_lot, zone, **revue_statut** (nouveau/inchangé/modifié).
- `reports/o12-ile/exclusions_revue.csv` + `config/o12_exclusions_revue.yaml` — les exclusions
  de revue avec **nature** (permanente / liée-géométrie), motif, date.
- `docs/mandats/O12_PARTIEL_REVUE.zip` — tout le nécessaire pour la revue en session neuve.

Golden **116/116 PASS**, tiers servis au bit près (120 · 1031 · 3587 · 72980 · 353945).
Tests `test_division_or.py` **11/11**. **EXPOSE reste False.**

---

## (archive) Livrables de l'itération précédente

`docs/mandats/O12_PARTIEL_REVUE.pdf` (20 cartes, tourniquet sur les 14 communes, SANS
colonne Gain, compacité affichée) · `O12_PARTIEL_EXEMPLES.pdf` (5 exemples régénérés) ·
`O12_PARTIEL_REVUE.zip` (les 2 PDF + `pool_decoupe.csv` enrichi + logs des 2 runs).
Golden **116/116 PASS**, tiers servis au bit près (120 · 1031 · 3587 · 72980 · 353945).
Tests **10/10**. **EXPOSE reste False** — la revue visuelle des 20 cartes tranche.
