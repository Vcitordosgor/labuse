# RECETTE — COUCHES-1
**Branche :** `fix/couches-1` · **Base de recette :** `labuse` (locale) · **API :** worktree sur :8020 · **Front :** :5175

> ⚠ **Captures.** Le rendu carte est WebGL avec relief 3D en repeinte continue : l'outil de
> capture (MCP Playwright, plafond 5 s) ne peut pas le photographier après le premier chargement à
> froid. Chaque travail visuel est donc prouvé par **render-proof** (`queryRenderedFeatures` /
> lecture DOM : couche peinte, couleurs, textes de légende, comptes) — preuve plus forte qu'un
> pixel. L'app reste lancée sur :5175 pour les captures avant/après au cadrage de Vic.

---

## 1. Tableau de recette des 25 travaux

| # | Lot | Travail | État | Preuve |
|---|-----|---------|------|--------|
| 1 | 1 | PEB : mesurer avant de toucher (E1) | **Clos, sans correction** | 122/333/798/3068 parcelles en zones A/B/C/D, toutes corridor Gillot (Sainte-Marie 3795 / St-Denis 159) — pas de décalage. `cascade_rules.yaml:371` |
| 2 | 1 | SIS : état honnête (E2) | **Fait** | 4 périmètres 0,6–1,4 ha, invisibles en aplat île → remontés en POINTS (`ov-sis-pt`). 4 points peints à z9 (avant 0) |
| 3 | 1 | Parc national cœur/adhésion (E3) | **Fait** | 2 aplats (cœur #6B3E17 / adhésion #C08A54, match subtype), 4 cœur + 8 adhésion peints ; légende 2 entrées |
| 4 | 2 | Légendes manquantes (A1) | **Fait** | PPR, ravines/DPF, parc national, zonage-vitrine : groupes vérifiés au DOM |
| 5 | 2 | Compteur « N COUCHES » (A2) | **Fait** | Comptait le fond → 3 couches pour ppr+znieff+dpf (BASE_FOND exclu) |
| 6 | 2 | Panneau légende sans troncature (A3) | **Fait** | `max-h` 35vh → min(70vh,34rem) + overscroll-contain |
| 7 | 2 | Accordéon chevron vertical (A4) | **Fait** | `rotate-90` (latéral) → `rotate-180` (vertical ⌄/⌃), vérifié au DOM |
| 8 | 2 | ZNIEFF I/II (A5) + `i` OSM (A6) | **Fait** | 2 entrées (opacité 0,20 vs 0,06), 144/38 peints ; note OSM ajoutée |
| 9 | 2 | Millésime/dérivé — règle unique (A7) | **Fait** | Retirés des libellés QPV/NPNRU/TVA → vivent dans le `i` (couches-info) |
| 10 | 3 | Taxonomie §3 — 7 catégories | **Fait** | 8 en-têtes (Le fond + 7), 35 couches couvertes, vérifié au DOM |
| 11 | 3 | Source hors du titre (B3) | **Fait** | « Lignes électriques » (HTA/HTB→i), « Limites officielles du PLU » (GPU brut→i) |
| 12 | 3 | Limites PLU : mesure + sous-option + fiche (B4) | **Fait** | 9,0 % à cheval (mesuré) ; sous-option indentée ; fiche « à cheval sur 3 zones — Npnr 59 %… » |
| 13 | 4 | Équipements OSM/BPE cohabitation (C1) | **Fait** | Langage unique (cercles, source=contour), `i` complémentarité, mesure 4883/15214 |
| 14 | 4 | Points de transport (C2) | **Fait** | Ordre pôle<station<arrêt ; station en ANNEAU (nesting) |
| 15 | 4 | TVA sous-option de QPV (C3) | **Fait** | `LAYER_SUBOPTIONS`, rendue indentée sous QPV |
| 16 | 4 | Ordre d'empilement nature (C4) | **Fait** | parc 58 < znieff 60 < enp 61 < zone_humide 62 |
| 17 | 5 | Aucun aplat vert (D1) | **Fait** ⚠pixels | EBC forêt profond, ENP indigo #6A4CC2, FRR sarcelle |
| 18 | 5 | Camaïeux cassés (D2) | **Fait** ⚠pixels | Mvt 4 crans, sonore 2 paliers séparés, HTA ardoise-bleu vs HTB argent, TCSP=1 teinte/3 formes |
| 19 | 5 | Opacités (D3/D4) | **Fait** ⚠pixels | PPR 0,14→0,24 +contour, DPU/CBS↑ ; SUP 0,24→0,16, ZFANG/FRR↓, mvt aplat↓ |
| 20 | 5 | Vocabulaire de gravité aligné (D5) | **Fait** | faible/moyen/élevé/très élevé sur les deux aléas |
| 21 | 5 | Emojis → glyphes DA (D6) | **Fait** | OSM en pastille colorée (anneau blanc), plus d'image emoji (vérifié) |
| 22 | 6 | Chargement (F) | **Fait** | geom_simple matérialisée pour les kinds SOURCES-1 (54 583 lignes) ; lourdes off par défaut (déjà) |
| 23 | 7 | Inventaire champs + exposition (G1) | **Fait** | Popups riches (SUP/ER/CASIAS/ZNIEFF/PPR…) — attrs joint côté API ; tableau §3 |
| 24 | 7 | Fraîcheur = millésime amont (G2) | **Fait** | `i` QPV = « millésime génération 2024 » (pas ingestion) ; tableau §3 |
| 25 | 7 | Tableau de couverture (G3) | **Fait** | Registre déclare mode/cadence/statut par source ; tableau §4 |

---

## 2. Réponses aux points « À VÉRIFIER » de l'audit (preuve factuelle)

- **E1 — PEB décalé ou décoratif ?** RÉFUTÉ. Le PEB intersecte du foncier réel : A=122, B=333, C=798,
  D=3068 parcelles, TOUTES en Sainte-Marie (3795) / Saint-Denis (159) / Sainte-Suzanne (1) = corridor
  Roland-Garros/Gillot. La part sur mer (B 40 %, C 61 %, D 72 %) est le cône d'approche légitime.
  Géométrie correcte → **constat fermé, aucune correction**. Câblé au cascade (`cascade_rules.yaml:371`,
  hard a/b + flag c/d).
- **E2 — SIS table vide ou polygones sous le seuil ?** Polygones sous le seuil : 4 périmètres réels de
  6 500–13 700 m² (Le Port, Saint-Benoît, Saint-Louis, Sainte-Marie), invisibles en aplat à l'échelle
  île. **Remontés en points** (fix livré).
- **B4 — taux de parcelles à cheval, artefact de découpe ?** Mesuré sur le run servi : **9,00 %** par
  zone réglementaire (subtype), 9,93 % par zone exacte, 12,6 % par famille. Seuil anti-liseré 10 % ;
  l'écart avec le brut (14 %) = contacts de bord, PAS un artefact (B4 point b vérifié). ~1 parcelle sur
  10 → couche demeurée en sous-option + fiche conditionnelle.
- **A2 — le compteur compte-t-il autre chose ?** Oui : il comptait `Object.values(layers)` fond compris
  (limites+communes+parcelles toujours vrais → « 4 » figé). Corrigé : compte les couches de données.
- **E3/E1 mesures** : voir §1.
- **F — geom_simple généralisée ?** NON (constat confirmé) : la liste de matérialisation précédait
  SOURCES-1 → 11 kinds simplifiaient à la volée. Gain mesuré RPG (38 460 polygones) : 536 ms → 34 ms.
- **F — couches lourdes off par défaut ?** DÉJÀ le cas (`useApp.ts:704`).
- **G2 — fraîcheur = ingestion ou amont ?** Le `i` (couches-info, registre) affiche le millésime AMONT
  (QPV « génération 2024 »). L'ancien « ingéré le » vivait dans le libellé de légende (retiré, A7).

---

## 3. Inventaire des champs (G1) — source vs exposé au clic

Avant COUCHES-1, **3 couches seulement** (VEFA, arrêts, équipements) exposaient un clic ; 30+ étaient
muettes. Après : popups riches pour les couches ci-dessous (attrs joint par `/map/layers.geojson` aux
seuls kinds à popup riche — jamais les semis de points).

| Couche | Champs disponibles à la source (attrs) | Exposés au clic (après) |
|--------|----------------------------------------|--------------------------|
| SUP | nomsuplitt, typeass, nomass, idass, urlreg | Type, catégorie d'assiette, assiette, **acte/règlement (lien)** |
| Emplacements réservés | txt (prescription), libelle, typepsc, url_source | **Destination/bénéficiaire (txt)**, libellé, document (lien) |
| Espaces boisés classés | txt, libelle, url_source | Prescription, libellé, **règlement (lien)** |
| DPU | libelle, txt, typeinf | Type, précision |
| CASIAS | statut, adresse, identifiant_casias, superficie, date_maj | **Nom (site), état du dossier, adresse, superficie, identifiant** |
| SIS | statut, id_sis, adresse, superficie, fiche_risque | Statut, adresse, identifiant SIS, fiche (lien) |
| ZNIEFF | id_mnhn, type, gestionnaire, url_fiche | **Nom, numéro national (id_mnhn), type, gestionnaire, fiche INPN (lien)** |
| PPR | risque, document, approbation, statut, code_degre | **Risque, document (PPR), date d'approbation, statut** |
| Aléas (inond/mvt) | degre, risque, document, niveau, classe | Degré, risque, document |
| ENP | type, surface_ha, nom | Nom, type, surface |
| Zones humides | nature, typename, localite | Nom, nature, inventaire |
| Ravines/DPF | toponyme, typologie, classe | Toponyme, type, classe |
| Équipements OSM | name, subtype (catégorie) | Nom, catégorie (+ distance parcelle) — inchangé |
| Transport (arrêts) | name, lignes_noms, reseau | Nom, lignes, réseau — inchangé |
| VEFA | prix_m2, n_ventes, tranche… | Panneau commune dédié — inchangé |

*Champs vides à la source omis (jamais « — » vide) ; « Détail non renseigné à la source » si tout est
vide. Écart source↔exposé restant : `urlreg`/`nomsuplitt` SUP souvent vides côté producteur (GPU).*

---

## 4. Tableau de couverture (G3) — source · millésime · cadence · sentinelle

Fraîcheur = **millésime amont**. Cadence et sentinelle lues du registre (`seed_sources.py`) + `source_veille`.

| Couche | Source | Millésime amont | Cadence | Sentinelle |
|--------|--------|-----------------|---------|-----------|
| Zonage PLU / limites off. | Urbanisme PLU/GPU (API Carto) | GPU/PLU par commune (révisions) | en direct | — (live) |
| PPR / Aléas | DEAL Réunion — PPR / aléas | PPR/PPRL 2011–2026 | 365 j | ✅ |
| PEB | DGAC via annexes GPU | Roland-Garros B/C/D | 365 j | ❌ *(cadence seule)* |
| ER / EBC | GPU prescriptions (API Carto) | typepsc 05/01 par commune | en direct | — (live) |
| DPU | GPU info-surf | typeinf 04 (partiel) | 190 j | ❌ *(cadence seule)* |
| SUP | SUP assiettes GPU (API Carto) | *(à renseigner amont)* | 35 j | ✅ |
| Parc national | INPN | 2021 | 365 j | ✅ |
| ZNIEFF | INPN/MNHN | maj 29/08/2025 | 365 j | ✅ |
| 50 pas | DEAL | cadastre 1877 (géoréf.) | 365 j | ❌ *(cadence seule)* |
| Ravines/DPF | DEAL Carmen | arrêté 2006 | 365 j | ❌ *(cadence seule)* |
| Zones humides | DEAL Carmen | inv. 2003/2009/2011/2019 | 365 j | ❌ *(cadence seule)* |
| ENP | INPN + DEAL Carmen | passe 05/07/2026 | 365 j | ❌ *(cadence seule)* |
| RPG | IGN/ASP (proxy) | RPG.LATEST (non pinné) | en direct | ✅ |
| SIS / CASIAS | Géorisques (BRGM) | 4 SIS / 453 CASIAS, vu 07/09/2026 | 365 j | ✅ |
| Classement sonore | Cerema | arrêtés déc. 2023 | 365 j | ✅ |
| Cartes de bruit (CBS) | DEAL | CBS 2022 | 365 j | ❌ *(cadence seule)* |
| QPV | ANCT | génération 2024 | 365 j | ✅ |
| TVA primo | dérivé QPV +500 m | (dérivé) | (suit QPV) | (suit QPV) |
| NPNRU/ANRU | DEAL/ANCT | QP génération 2024 | 365 j | ✅ |
| ZFANG | Légifrance | décret 2026-421 (29/05/2026) | 365 j | ❌ *(cadence seule)* |
| FRR | Légifrance | FRR 01/07/2024 | 365 j | ❌ *(cadence seule)* |
| VEFA neuf | geo-DVF (DGFiP) | fenêtre 36 mois | 365 j | (DVF veillée) |
| Équipements BPE | INSEE | BPE 2025 | 365 j | ✅ |
| Équipements OSM | OpenStreetMap | continu | 365 j | ❌ *(cadence seule)* |
| Transport / TCSP / axes | GTFS PAN · OSM · BD TOPO | LO / continu | 365 j | ✅ GTFS / ❌ OSM |
| Lignes HTA/HTB | EDF open data · BD TOPO | ~02/2020 republié 2025 | 365 j | ✅ HTA |

**Couches sans surveillance active (sentinelle ❌)** : PEB, DPU, 50 pas, ravines/DPF, zones humides,
ENP, CBS, ZFANG, FRR, OSM. Elles ne sont **pas muettes** — le registre leur déclare une cadence
attendue (rappel manuel au dépassement) ; mais elles ne sont pas sondées automatiquement. Recommandé
d'étendre la sentinelle à celles dont l'amont est sondable (hors périmètre COUCHES-1 → SENTINELLE).
**PLU/GPU et RPG** sont en mode « en direct » (API Carto / RPG.LATEST) : toujours frais, cadence sans objet.

---

## 5. Gates

- **tsc** 0 · **vitest** 191/191 (44 fichiers) · **pytest** plu/reglement 114 · geom/layer/map 67 (skips = env).
- Chaque lot committé séparément (7 commits, non mergés — CC ne merge jamais).
- Décisions de teintes (Lot 5, D1-D4) : conformes à la doctrine de contraste M105-B, **à valider aux
  pixels par Vic** (le rendu WebGL n'est pas capturable par l'outil).
