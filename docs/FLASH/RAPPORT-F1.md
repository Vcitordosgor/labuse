# RAPPORT — F1 (enquête, avant tout code)

Mandat « Rapport Flash : la section zone ». Écrit avant d'écrire une ligne, comme exigé.

## 1. Comment le rapport Flash est structuré

- **Chaîne** : `src/labuse/flash/` — `data.py` (collecte), `report.py` (assemblage + rendu),
  `carte.py` (carte de situation), `templates/rapport.html.j2` + `rapport.css` (mise en page).
- **Données** : `collect_report_data(db, idu, adresse=…)` (data.py) assemble un dict `data` par
  sous-builders (`_identite`, `_constructibilite`, `_risques`, `_patrimoine`, `_marche_via_service`,
  `_dynamique`, `_terrain`, `_contexte_commune`, `_aper`…). Chaque absence → section `None` que le
  template omet proprement. `parcelle` porte déjà **`lon`/`lat`** (centroïde 4326) et le `geojson`.
- **Structure du document** : une page de **garde** (couverture + carte de situation OSM + table méta)
  puis **10 sections numérotées** dans `rapport.html.j2` :
  `01 Identité · 02 Constructibilité · 03 Risques · 04 Patrimoine · 05 Marché (commune & comparables) ·
  06 Dynamique locale · 07 Contexte commune · 08 Terrain & réseaux · 09 Sources & millésimes ·
  10 Ce que ce document ne peut pas dire`.
- **Sommaire / pagination** : il n'y a **pas** de page de sommaire (TOC) séparée — le « sommaire » EST
  la suite numérotée des `<h2><span class="num">NN</span>…`. La pagination est gérée par WeasyPrint ;
  `<section class="saut">` force un saut de page. Une section s'insère donc en **ajoutant un numéro** et
  en décalant la queue.
- **Sources centralisées** : la section 09 est bâtie depuis `_SECTION_SOURCES` (liste `(section, label,
  nom_source, millésime_statique)`) filtrée par les sections **rendues** (`rendues` dans
  `collect_report_data`). `_SECTION_LABELS` nomme chaque section dans le tableau des sources.

## 2. Ce que produit `pdf_zone` et comment la zone est calculée

- **Calcul (source unique)** : `src/labuse/zone.py::etude_de_zone(db, lon, lat, minutes, mode, *, geom,
  naf)` — isochrone IGN (cache + dégradé honnête), `population_zone` (UNIQUE point Filosofi),
  `emplois_communes` (MOBPRO commune), `equipements_proches` (BPE, avec temps), `generateurs_flux`,
  `marche_zone` (DVF/Radar/permis), et `concurrents_zone` **si** un NAF est fourni. L'endpoint
  `POST /outils/etude-zone` (api/app.py) appelle CE MÊME `etude_de_zone` — c'est le point de calcul unique.
- **Rendu de l'outil** : `src/labuse/api/pdf_zone.py::render_zone_pdf(data)` produit le PDF **autonome**
  de l'outil (écran 3), en **fpdf2**.

## 3. Même bibliothèque de rendu ? — NON

- **Flash = WeasyPrint** (HTML/CSS via Jinja2 : `rapport.html.j2` + `rapport.css`, `HTML(...).write_pdf`).
- **`pdf_zone` = fpdf2** (dessin impératif).
- **Conséquence (choix le moins coûteux)** : on **ne réutilise pas** la mise en page fpdf2 de `pdf_zone`
  (moteur différent, et le mandat interdit de réécrire un moteur de rendu). La section zone du Flash sera
  du **HTML/CSS** dans le template Jinja, **fidèle à l'écran 3**. `pdf_zone` reste intact (il sert l'outil).

## 4. Point de vigilance — le calcul reste à UN SEUL endroit

Respecté : la section Flash **consomme** `zone.etude_de_zone` (via un nouveau builder `_zone` dans
data.py) et **ne recopie aucune logique**. La seule chose nouvelle est la **présentation HTML** ; les
chiffres viennent du module. Aucune divergence de revenu possible : le rapport Flash n'affiche **aucun**
revenu Filosofi ailleurs (vérifié — `filosofi_carreaux_200m` n'est cité que dans la liste des tables).

## Plan F2→F4 (dérivé)

- **F2** : `_zone(db, parcelle)` appelle `etude_de_zone(lon, lat, 10, "voiture", naf=None)` et renvoie
  TOUJOURS un dict rendable (dégradé honnête si indisponible/inhabitée). Nouvelle section
  **« 09 — Autour de cette parcelle »** (écran 3 : population · activité/concurrence · carte de la zone ·
  marché immobilier · astérisque ESTIMÉ + sources), Sources→10, Limites→11. Carte de la zone via
  `build_situation_map(isochrone, extra=parcelle)` (réutilise le builder existant, optionnel/résilient).
  Ajout de la section 'zone' à `_SECTION_LABELS` et `_SECTION_SOURCES` (INSEE Filosofi/MOBPRO, SIRENE,
  BPE, IGN isochrones).
- **F3** : le parcours /flash ne transmet **pas** de NAF → section **sans volet concurrence** + finding
  **FZ-001** (ajouter le choix d'activité au parcours). Entrée par adresse déjà gérée (en-tête dit
  l'adresse et la parcelle déduite).
- **F4** : vrais PDF (centre-ville, hauts, adresse, dégradé) livrés dans `docs/FLASH/`, regardés
  (pagination, débordements, tables coupées).

## Findings

- **FZ-001** (à poser en F3) : le parcours `/flash` ne propose pas l'activité (NAF). La section zone est
  donc générée **sans volet concurrence**. Pour l'activer : ajouter un champ « activité » au parcours
  Flash (réutiliser `GET /outils/etude-zone/naf`) et le transmettre jusqu'à `generate_flash_report`.
