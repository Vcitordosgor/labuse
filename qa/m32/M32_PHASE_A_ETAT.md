# M32 — PHASE A : ÉTAT DE CALIBRATION + RÉCONCILIATION (Livrable A)

Régime [S] · branche `m32-train6-calibration` · base main post-M31 (`b3e4547`, vérifié).
**Lecture seule** — aucune calibration écrite, aucun run, aucune intégration moteur.
**POINT D'ARRÊT 1** : ce rapport réconcilie la prémisse du mandat avec l'état réel du dépôt.
Rien n'est fabriqué (doctrine : « non calculable proprement → l'écrire et s'arrêter »).

---

## 0 · La phrase

La prémisse du mandat — « 10 communes au schéma exhaustif, **14 restantes à extraire** » — ne
correspond pas à l'état du dépôt. En réalité : **des fichiers d'extraction sourcés existent pour
~21 communes** (à complétude variable), **le moteur n'en intègre que 4**, l'**annuaire PLU des 24
est déjà fait** (Phase B §1), le **bug zone_lib est déjà corrigé**, et **aucun document PLU source
n'est sur le disque** (le GPU est joignable mais re-télécharger+lire 14 règlements est le vrai
travail d'extraction, que ce point d'arrêt encadre). Le « 14 restantes » n'est donc ni vierge, ni
uniformément extractible — il faut réconcilier le périmètre avant d'écrire quoi que ce soit.

---

## 1 · Réconciliation du « 10 / 14 »

Le « **10** » = la **vague 1 GPU-pilote** (`docs/mandats/GPU_PILOTE_BILAN_9.md`, titre « BILAN DES 9
COMMUNES À JOUR ») : **9 communes dont l'archive GPU locale était présente et sha-vérifiée** (Les
Avirons, Bras-Panon, Entre-Deux, La Plaine-des-Palmistes, Saint-Paul, Saint-Pierre, Sainte-Rose, Les
Trois-Bassins, Cilaos) **+ L'Étang-Salé** (pilote, extraction phase 2 v2). Extractions dans
`config/calibrage/extraction_paquet{A,B,C}.yaml` + `extraction_l_etang_sale.yaml`.

Le « 10/14 » est donc une distinction **d'archive GPU vérifiée**, PAS de complétude d'extraction :
plusieurs des « 14 » ont AUSSI un `calibration_<commune>.yaml` sourcé (source mairie ou pull GPU
antérieur), à complétude variable.

### Trois niveaux distincts à ne pas confondre

| Niveau | Fichier | Communes | Ce que c'est |
|---|---|---|---|
| **Intégré au MOTEUR** | `config/calibrage/au_ouverture_planchers.yaml` | **4** (Saint-Paul, La Possession, Saint-Leu, Les Trois-Bassins) | ce que le moteur applique réellement (sous-plancher, ouverture) |
| **Extraction vague 1** | `extraction_paquet{A,B,C}.yaml` + L'Étang-Salé | **10** | GPU-pilote, archives sha-vérifiées |
| **Extraction sourcée (toutes)** | `calibration_*.yaml` | **21** | recherche par commune, `statut: Sourcé`, complétude variable |

---

## 2 · État réel par commune (24)

Légende complétude : **EXH** = zone × site OAP + planchers chiffrés · **PART** = ouverture +
planchers mais pas d'OAP par site (ou OAP bloquée) · **NÉG** = scan négatif (aucun plancher au
règlement — rien à calibrer) · **RNU/HORS** · **BLOQ** = source/opposabilité indisponible.

| INSEE | Commune | Extraction ? | Moteur ? | Complétude | Note source |
|---|---|---|---|---|---|
| 97401 | Les Avirons | oui (vague 1) | non | PART | GPU 2024-12-06 ✓ · densité 30/30/20 |
| 97402 | Bras-Panon | oui (vague 1) | non | PART | GPU 2026-04-28 · densité 30→50 TCSP, dépend. phasage inter-zones |
| 97403 | Entre-Deux | oui (vague 1) | non | **EXH** | tableau OAP par site (~19 sites) + densité 20 |
| 97404 | L'Étang-Salé | oui (pilote) | non | **EXH** | 50/30/15 + VRD opérateur (seul cas VRD trouvé) |
| 97405 | Petite-Île | oui | non | PART | ouverture a_verifier, phasage probable |
| 97406 | La Plaine-des-Palmistes | oui (vague 1) | non | PART | 10 LLS/opération ; OAP graphique non OCR-able |
| 97407 | Le Port | oui | non | PART | densité 50 (OAP) ; 2AU fermée réserve |
| 97408 | La Possession | oui | **oui** (partiel) | **EXH** | densité 50 + social 40-60% OAP ; moteur = densité seule |
| 97409 | Saint-André | a_verifier | non | **BLOQ** | GPU 2019 dépublié, révision non approuvée — opposabilité inconnue |
| 97410 | Saint-Benoît | oui (mairie) | non | PART/NÉG | format 2 colonnes bloque ; 19 fiches AU (cf. §4) ; 7 brûlantes sur AUb |
| 97411 | Saint-Denis | oui | non | **NÉG** | v2026 : OAP disparue, aucun plancher au règlement (scan négatif) |
| 97412 | Saint-Joseph | oui | non | **NÉG** | v2025 remplace 2019 ; phasage disparu, aucun plancher |
| 97413 | Saint-Leu | oui (mairie) | **oui** | **EXH** | PLU 2007 opposable ; min 10 log + 30/30/15 |
| 97414 | Saint-Louis | oui | non | PART | écart de version (v20250926 extrait vs v20251218 en vigueur) — à confirmer |
| 97415 | Saint-Paul | oui (vague 1) | **oui** (ouverture seule) | PART | planchers DÉLÉGUÉS au PLH TCO (non chiffrés) |
| 97416 | Saint-Pierre | oui (vague 1) | non | **EXH** | 50/60/80 (OAP) + social 20-40% par site — la plus riche |
| 97417 | Saint-Philippe | — | — | **RNU** | 0 document GPU, RNU confirmé — hors calibration AU |
| 97418 | Sainte-Marie | oui | non | **EXH** | 50/25/25 + OAP par site ; **1er cas date-butoir 2AU = 2031** |
| 97419 | Sainte-Rose | oui (vague 1) | non | PART | densité 20 (10 rural) ; phasage 1AU complexe (exclut 1AUc/1AUe) |
| 97420 | Sainte-Suzanne | oui | non | PART | densité au règlement (valeurs à re-confirmer) |
| 97421 | Salazie | oui | non | PART | densité probable au règlement (valeurs à re-confirmer) |
| 97422 | Le Tampon | oui | non | **EXH** | 10/20 par secteur + OAP 50 + 2AU phasage ; golden brûlante 2AUd connue |
| 97423 | Les Trois-Bassins | oui (vague 1) | **oui** | **EXH** | 35/30/20 + social 25/40% + 2AU→1AU (cas-type phasage) |
| 97424 | Cilaos | oui (vague 1) | non | **NÉG** | montagne, aucun plancher ; OAP graphique bloquée |

**Compte (24)** : EXH 8 · PART 10 · NÉG 3 · RNU 1 (Saint-Philippe) · BLOQ 1 (Saint-André) ·
Saint-Benoît 1 (cas spécial PART/NÉG, 19 fiches graphiques). **Moteur = 4 seulement.**

---

## 3 · Découvertes (le « rapport des découvertes » demandé)

1. **Planchers de densité PROPRES par commune (confirmé vague 1)** — ni universels, ni propres à
   L'Étang-Salé : L'Étang-Salé 50/30/15, Les Trois-Bassins 35/30/20 (règlement), Saint-Pierre
   50/60/80 (OAP), La Plaine 10 LLS/opération, Sainte-Marie 50/25/25, Saint-Leu 30/30/15. Une
   parcelle sous le seuil = inconstructible seule (fait absent des YAML de zone).
2. **Dépendance de phasage INTER-ZONES — 3 communes** (Bras-Panon, Sainte-Rose, Les Trois-Bassins) :
   l'ouverture d'une AU est subordonnée à l'urbanisation d'une AUTRE zone. **Aucun YAML actuel ne
   modélise de dépendance inter-zones** — schéma à étendre (dette).
3. **Premier cas DATE-BUTOIR** (Sainte-Marie) : 2AU ouvre à une date (2031), pas à une condition
   d'opération. Le schéma `au_ouverture` ne porte pas encore la date-butoir.
4. **Scans NÉGATIFS = rien à calibrer** (Saint-Denis, Saint-Joseph, Cilaos) : le règlement ne pose
   AUCUN plancher. Ce n'est PAS un trou à combler — c'est `sans_objet`, à servir tel quel (« pas de
   seuil-taille au règlement »), jamais un plancher deviné.
5. **Prévalence OAP** : densité/social réels viennent souvent de l'OAP par site, pas du règlement
   (Saint-Pierre, La Possession, Bras-Panon). L'extraction exhaustive = lire l'OAP site par site.
6. **Charges VRD opérateur** : trouvées seulement à L'Étang-Salé (chapitre réseaux) — à chercher
   systématiquement pour les autres, absentes des extractions actuelles.
7. **Écarts de VERSION** : Saint-Louis (v extraite ≠ v en vigueur), Saint-Denis (v2026 vs 2024
   servie), Saint-Joseph (v2025 vs 2019) — un ré-extrait doit être ancré sur la version OPPOSABLE.

---

## 4 · Cas concrets listés au mandat

- **zone_lib (bug d'ingestion 8 communes / 95 396 parcelles)** : **DÉJÀ CORRIGÉ.** Vérifié en base :
  seuls NULL restants = Saint-Philippe (4 153, RNU → correct) + **91 parcelles Saint-Leu qui n'ont
  AUCUN zonage GPU** (hors zonage réel, 0 intersection `plu_gpu_zone`, pas un trou). Total hors RNU =
  91, non-bug. **Aucune correction nécessaire.**
- **Saint-Philippe = RNU** : confirmé (0 document GPU, `is_rnu` apicarto). Hors calibration AU —
  traité en RNU (débordements 97412/97419). À garder à part comme le mandat le demande.
- **Saint-Paul « fermée » / Saint-Leu** : tous deux DÉJÀ dans le moteur (`au_ouverture_planchers.yaml`).
  Saint-Paul = ouverture conditionnelle, planchers délégués PLH (non chiffrés) ; Saint-Leu = complet
  (min 10 log + 30/30/15, source mairie PLU 2007 opposable).
- **19 fiches annexes Saint-Benoît** : identifiées (`plu_saint_benoit.yaml:104` — fiches AU N°01-19,
  régime d'urbanisation par zone AU). **NON intégrables au schéma v1** : hauteur définie par secteur
  GRAPHIQUE + PDF 2 colonnes → extraction fiable impossible (arbitrage Vic 28/07 déjà rendu). 7
  brûlantes sur AUb (dont AUb19). **C'est une dette schéma v2** (« hauteur par calque graphique »),
  pas une extraction à forcer en v1.
- **Annuaire PLU (Phase B §1)** : **DÉJÀ FAIT** — `reports/m51-unification/PLU-A-RECALIBRER.md`
  (13/07) : 24 communes, idurba, GPU en ligne, date d'approbation, statut, vigilances (Saint-André,
  Saint-Leu, Saint-Louis, Le Port PARTIALLY_ANNULLED). Liste « à recalibrer » = VIDE (base alignée GPU).

---

## 5 · Ce qui est DOABLE maintenant vs BLOQUÉ

**Doable sans nouvelle source (extractions déjà sourcées)** :
- **Intégrer au moteur** les extractions EXH/PART déjà sourcées non encore câblées (Entre-Deux,
  Saint-Pierre, Sainte-Marie, Le Tampon, L'Étang-Salé, Les Avirons, Sainte-Rose, Bras-Panon, La
  Plaine, Le Port, Petite-Île, Saint-Louis…). ⚠ Mais l'intégration CHANGE la faisabilité servie
  (nouvelles zones passent en sous-plancher) → c'est un effet de **rebuild** (Phase C, sur GO), pas
  Phase A. À faire une fois le périmètre arbitré.
- Servir les scans négatifs tels quels (`sans_objet`) — déjà le comportement par défaut.

**Bloqué (ne PAS forcer)** :
- **Saint-André** : opposabilité inconnue (PLU 2019 dépublié, révision non approuvée) → `a_verifier`,
  pas de calibration tant que la version opposable n'est pas tranchée.
- **Extraction FRAÎCHE des communes partielles** (VRD, OAP par site manquantes, écarts de version) :
  le GPU est joignable (HTTP 200) mais **aucun document source n'est sur le disque** — chaque
  ré-extraction = télécharger le règlement+OAP, le lire article/page. C'est le vrai travail
  d'extraction, par commune, qui excède un point d'arrêt et doit être cadré (quelles communes, quelle
  version opposable).
- **19 fiches Saint-Benoît** : schéma v2 (graphique), hors v1.

---

## 6 · Recommandation + POINT D'ARRÊT 1

La prémisse « extraire 14 communes vierges » est **partiellement caduque** : l'annuaire est fait, le
zone_lib est corrigé, 21 extractions existent, le moteur n'en intègre que 4. Le vrai travail restant
n'est PAS « extraire 14 » mais un mélange de :
1. **Intégration au moteur** des extractions déjà sourcées (geste de rebuild — Phase C, sur GO) ;
2. **Ré-extraction ciblée** des communes partielles/à écart de version (télécharger la version
   OPPOSABLE, lire OAP+VRD) — à cadrer commune par commune ;
3. **Sans objet** : scans négatifs (3), RNU (1), Saint-Benoît v2 (1), Saint-André bloqué (1).

**Demande d'arbitrage Vic (Point d'arrêt 1)** :
- (a) Confirmer que le « 14 » = intégrer-les-sourcées + ré-extraire-les-partielles, PAS repartir de
  zéro. Si oui, lesquelles ré-extraire en priorité (liste), et sur quelle version opposable ?
- (b) Le rebuild d'intégration (Phase C) embarque-t-il TOUTES les EXH sourcées d'un coup, ou par
  vague ?
- (c) Saint-André : attendre l'opposabilité (statu quo) ou traiter le PLU 2019 comme opposable ?
- (d) Saint-Benoît 19 fiches : confirmer report en schéma v2 (pas de forçage v1).

**Rien n'est écrit ni intégré tant que (a)–(d) ne sont pas tranchés.** Aucune règle fabriquée.
