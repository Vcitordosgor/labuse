# COMPTE-RENDU DESTINATIONS-1

**Branche** `feat/destinations-1` (depuis `main`). Calibration des DESTINATIONS des PLU des
24 communes de La Réunion, servie sur les 4 surfaces via un module unique. Commit par commune.

**Doctrine tenue** : une valeur servie est LUE dans le règlement (article + page_pdf + millésime),
ou n'est pas servie. Rien de déduit, rien de supposé. Une commune non calibrée affiche
« destination non calibrée sur cette commune » — jamais un silence.

---

## Écarts au mandat (à connaître d'emblée)

1. **23 sous-destinations, pas 21.** Le mandat annonçait 21 (état pré-2023). La version **en
   vigueur** de l'art. R151-28 (décret n° 2023-195 du 22/03/2023, applicable depuis le
   01/07/2023) en compte **23** : ajout de « lieux de culte » et « cuisine dédiée à la vente
   en ligne », destination 5 renommée « Autres activités des secteurs primaire, secondaire ou
   tertiaire ». La loi fait foi : le référentiel est calé sur les 23.
2. **2 SCoT au GPU, pas 5.** La prémisse « cinq SCoT (un par EPCI) » est fausse : CIVIS et CASUD
   partagent le **SCoT Grand Sud**. Seuls **2 SCoT** sont en vigueur et publiés (Grand Sud, TCO).
   Détail en X3.2.
3. **GPU dépublié pour Saint-André et Saint-Leu.** L'API GPU ne sert plus aucun document pour
   97409 et 97413 (révisions en cours ; constaté sur pièces le 03/09 — API + WFS vides). La note
   M40 du catalogue « présent au GPU » n'est plus vraie. Les **règlements officiels de mairie**
   (opposables) ont été récupérés et utilisés, avec traçabilité (URL, md5) dans leur meta.

---

## Architecture (X1 · X4 · X5)

- **Module unique** `src/labuse/plu/destinations.py` : référentiel R151-27/28, verdicts
  (autorisé / sous condition / interdit / non mentionné→silence / non lu / en cours de
  calibration / non calibrée), verrou CDAC (L752-1), SCoT/DAAC. Lu par les **4 surfaces** ;
  test d'unicité (`test_module_unique_aucune_autre_lecture`) : aucun autre code ne lit
  `config/plu_destinations/`.
- **Calibration** : un YAML par commune `config/plu_destinations/<insee>_<slug>.yaml` +
  `rnu.yaml` (Saint-Philippe). Même doctrine de citation que les `plu_<slug>.yaml` de
  constructibilité (article, page, millésime, date de lecture ; états `non_mentionne` ≠ `non_lu`).
- **X4** — Étude de zone › chalandise (verdict par zone PLU recouverte + CDAC + SCoT), Fiche
  parcelle › Urbanisme (ligne « Destinations » dépliable, 23 sous-destinations sourcées),
  Faisabilité › programme (destination du programme écartée si interdite, comptée), Copilote
  (outil `destination_zone`, même moteur, même phrase, bouton Étude de zone prérempli).
- **X5** — état par commune (calibrée / à relire / RNU / non calibrée ; « à relire »
  directionnel : nouvelle version PLU servie postérieure au document lu), chip sur la ligne
  PLU du Catalogue admin, page admin `GET /admin/destinations`.
- Tests : `tests/test_plu_destinations.py` **20 passés**. Front tsc 0 / build OK / vitest 137.
  Back copilote 145 passés.

---

## X2 — Calibration des 24 communes

**Total : 23 communes calibrées + Saint-Philippe (RNU), soit 24/24. 773 zones, 3 136 entrées
de sous-destinations explicites** (hors les 23 lignes × zones servies par le silence).

Relecture : à la clôture de chaque commune, **10 lignes tirées au hasard** (graine
`<insee>-relecture`) sont relues au texte par un agent indépendant. Une commune à **plus de
5 % d'écart (≥ 1/10) est relue en entier** (relecture intégrale). Tous les écarts relevés
étaient de **forme** (conditions non autoportantes « idem »/renvoi sans contenu, ou une cellule
de tableau mal lue) — **aucun écart de statut, de seuil, d'article, de page ou de citation
inventée** ; tous corrigés, l'intégrale confirmant 0 écart de fond.

| # | Commune | INSEE | Millésime | Zones | Entrées | Tirage | Relecture intégrale (si > 5 %) |
|---|---------|-------|-----------|------:|--------:|--------|--------------------------------|
| 1 | Saint-Denis | 97411 | 2026-08-05 | 35 | 146 | 10/10 (0 %) | — |
| 2 | Saint-Paul | 97415 | 2025-12-17 | 67 | 185 | 10/10 | — |
| 3 | Saint-Pierre | 97416 | 2024-06-25 | 45 | 503 | 10/10 | — |
| 4 | Le Port | 97407 | 2024-12-09 | 27 | 179 | 10/10 | — |
| 5 | Sainte-Marie | 97418 | 2025-11-26 | 32 | 171 | 6/10 (40 %) | 139/171 → 32 écarts (1 classe) corrigés → 0 |
| 6 | Le Tampon | 97422 | 2023-08-11 | 30 | 125 | 9/10 (10 %) | 94/115 → 21 écarts corrigés + alignement Uc/Ud → 0 |
| — | Saint-Philippe | 97417 | RNU | — | 23 (statique) | s.o. | s.o. (calibration L111-3/L111-4) |
| 7 | Saint-André | 97409 | 2019-02-28 | 25 | 94 | 9/10 | 104/104 → 0 |
| 8 | Saint-Louis | 97414 | 2025-12-18 | 51 | 69 | 9/10 | 69/69 → 0 |
| 9 | Saint-Joseph | 97412 | 2025-12-10 | 60 | 132 | 7/10 (30 %) | 132/132 → 0 |
| 10 | Saint-Benoît | 97410 | 2020-02-06 | 75 | 71 | 10/10 | — |
| 11 | La Possession | 97408 | 2025-12-17 | 30 | 141 | 9/10 | 141/141 → 0 (28 citations = pointeurs, verbatim sur l'entrée de tête) |
| 12 | Saint-Leu | 97413 | 2007-02-26 | 37 | 100 | 10/10 | — |
| 13 | Les Avirons | 97401 | 2024-12-06 | 27 | 146 | 10/10 | — |
| 14 | Bras-Panon | 97402 | 2026-04-28 | 29 | 115 | 10/10 | — |
| 15 | Entre-Deux | 97403 | 2024-09-24 | 16 | 94 | 9/10 (image) | tableau U re-vérifié sur l'image, 2 cellules Ue corrigées → 0 |
| 16 | L'Étang-Salé | 97404 | 2025-09-17 | 24 | 102 | 10/10 | — |
| 17 | Petite-Île | 97405 | 2023-06-09 | 34 | 357 | 9/10 | 345/345 → 0 (écart tirage = faux positif ; secteur Np ajouté) |
| 18 | La Plaine-des-Palmistes | 97406 | 2023-05-27 | 22 | 43 | 11/11 | — |
| 19 | Sainte-Rose | 97419 | 2019-05-04 | 23 | 90 | 10/10 | — |
| 20 | Sainte-Suzanne | 97420 | 2025-09-29 | 24 | 105 | 10/10 | — |
| 21 | Salazie | 97421 | 2022-05-24 | 15 | 49 | 10/10 | — |
| 22 | Les Trois-Bassins | 97423 | 2022-06-02 | 30 | 94 | 10/10 | — |
| 23 | Cilaos | 97424 | 2024-02-13 | 15 | 25 | 10/10 | — |

**Communes restantes : aucune.** Les 24 sont calibrées (23 sur règlement lu + Saint-Philippe RNU).

### Points de méthode et cas particuliers

- **Source des règlements** : le GPU (`data.geopf.fr/annexes/gpu/documents/`) pour 21 communes ;
  mairie pour Saint-André et Saint-Leu (GPU dépublié) ; RNU (Légifrance) pour Saint-Philippe.
  Chaque règlement lu porte son **md5** dans sa meta.
- **Trois formats de règlement rencontrés**, tous traités : (a) ancien format R123
  « occupations interdites / soumises à conditions » (mapping conservateur des termes vers les
  sous-destinations, jamais au-delà de ce que le texte porte) ; (b) format moderne à **listes à
  cocher** ou **tableaux** des 23 sous-destinations (relayés tels quels) ; (c) STECAL par familles
  (Saint-Benoît : Ns/Nta/Ntb + caducité ELAN citée) et par bassins (Saint-Paul : 7 livrets).
- **Entre-Deux** : le tableau de destinations (p. 17) sort **vide à l'extraction texte** (symboles
  graphiques). Lu **directement sur le PDF rendu en image** (300 DPI), colonnes Ua/Ub/Ue,
  légende p. 11.
- **Silence lu, jamais supposé** : chaque zone porte sa règle de silence (`autorise`/`interdit`)
  citée sur la structure du règlement (liste fermée d'interdictions = autorisé ; « seules sont
  admises… » = interdit ; A/N « toute construction sauf article 2 » = interdit).
- **`non_lu` honnêtes** : secteurs servis au zonage mais introuvables au règlement (ex.
  Saint-Louis 1AUste/2AUste, Saint-Joseph 4 codes « st », Cilaos Ub1/NtoPOS, Trois-Bassins
  Nto1-6, La Possession AUEm) — marqués `non_lu` avec note, jamais comblés.
- **Discordances de millésime documentées** : Trois-Bassins (idurba GPU 2022 vs approbation
  2017), Cilaos (idurba 2024 vs pièce 2008 maj 2018) — consignées en meta, non tranchées.

---

## X3 — CDAC et SCoT/DAAC

### X3.1 CDAC (statique, citée)
Règle nationale portée par le module (pas par les YAML communaux) : au-delà de **1 000 m² de
surface de vente**, autorisation d'exploitation commerciale obligatoire (**art. L752-1 du code
de commerce**). Servie automatiquement sur les sous-destinations de commerce dès qu'un régime
autorisé peut dépasser ce plafond (« soumis à CDAC au-delà de 1 000 m² de surface de vente »).

### X3.2 SCoT / DAAC — ce qui existe, commune par commune
**Aucune géométrie ZACOM/DAAC publiée** à La Réunion au 03/09/2026 : ni GPU, ni data.gouv, ni
AGORAH/PEIGEO (recensement dans `data/reglements-plu/_daac_recensement.md`). La voie PDF du
mandat a été suivie. Réalité des SCoT :

- **Grand Sud** (CIVIS + CASUD) : **seul DAAC en vigueur** (SCoT approuvé 18/02/2020, DOO modifié
  02/09/2024). Liste officielle des **7 ZPLC périphériques** (pages PDF 77-78 du DOO) + fiches
  communales lues en image.
- **TCO** : SCoT 21/12/2016 modifié 03/10/2022, **pas de DAAC** ; le commerce est localisé par
  principes (DOO §4, « espaces urbains de référence »), **non nommé par commune** → `non_localisé`.
- **CINOR** : SCoT hors GPU ; DAACL **en projet** (non opposable) → `non_localisé`.
- **CIREST** : SCoT 2004 abrogé, nouveau en élaboration → `non_localisé`.

Verdict servi par commune (« secteur préférentiel du SCoT : oui / non / non localisé ») :

| Verdict | Communes |
|---------|----------|
| **oui** (secteur ZPLC nommé) | Saint-Pierre (4 secteurs), Saint-Louis (1 : ZAE Bel Air), Saint-Joseph (1 : ZAE des Grègues), Le Tampon (1 : rue du Général de Gaulle prolongée) |
| **non** (Grand Sud, commune sans ZPLC) | Cilaos, L'Étang-Salé, Les Avirons, Petite-Île, Entre-Deux, Saint-Philippe |
| **non localisé** (TCO / CINOR / CIREST, pas de DAAC ou secteurs non nommés) | Le Port, La Possession, Saint-Paul, Saint-Leu, Trois-Bassins (TCO) · Saint-Denis, Sainte-Marie, Sainte-Suzanne (CINOR) · Saint-André, Saint-Benoît, Bras-Panon, Sainte-Rose, Salazie, La Plaine-des-Palmistes (CIREST) |

Source : `config/plu_destinations/scot_daac.yaml` (24 communes, chaque secteur cité avec sa page).

---

## X4.1 — Trois captures de chalandise (verdict servi)

Générées via le module (`verdicts_zones_etude`), phrase servie **telle quelle** sur l'Étude de
zone. Les trois états du mandat :

- **Autorisé** — Restauration, zone Ucv (Saint-Pierre) :
  « Restauration : autorisé — zone Ucv — art. Ucv1 (tableau) — p. 60 (PDF) — PLU millésime
  2024-06-25 » · secteur préférentiel SCoT : **oui**.
- **Sous condition** — Artisanat et commerce de détail, zone Um (Saint-Denis) :
  « Artisanat et commerce de détail : surface de plancher limitée à 300 m² — zone Um —
  art. Um 2 — p. 65 (PDF) — PLU millésime 2026-08-05 » · SCoT : non localisé.
- **Interdit** — Hôtels, zone Ua (Le Port) :
  « Hôtels : interdit — zone Ua — art. Ua 1 — p. 21 (PDF) — PLU millésime 2024-12-09 »
  · SCoT : non localisé.

(Le 4e état, « en cours de calibration », s'affiche pour une zone `non_lu` ou une commune non
calibrée — plus aucune commune dans ce cas.) Détail : `data/reglements-plu/_captures_chalandise.json`.

---

## Temps passé

La **lecture** des 24 règlements a été **parallélisée** (agents de lecture indépendants, 2-4
par commune selon la taille) ; le temps-agent par commune s'échelonne de **~2 min** (petites
communes : Salazie, Cilaos) à **~11 min** (gros règlements : Saint-Paul 413 p., Petite-Île
169 p., Saint-Joseph 185 p.). Chaque commune a ensuite un tirage de relecture (~1,5-4 min) et,
si > 5 %, une relecture intégrale (~3-8 min). Le mandat s'est déroulé sur **deux sessions**
(coupures de quota), sans perte : PDF, textes paginés et fragments conservés sur disque, reprise
par l'état consigné dans `data/reglements-plu/_avancement.md`.

---

## Artefacts

- Calibrations : `config/plu_destinations/*.yaml` (24 communes + `rnu.yaml`, `scot_daac.yaml`, `README.md`).
- Module + tests : `src/labuse/plu/destinations.py`, `tests/test_plu_destinations.py`.
- Outillage : `scripts/audit/destinations/valide_calibration.py`, `assemble_commune.py`.
- Sources lues (hors git, `.gitignore`) : `data/reglements-plu/` (PDF, textes paginés, fragments,
  relectures, recensement DAAC, captures chalandise).
