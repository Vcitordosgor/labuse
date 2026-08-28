# RECETTE — F4 (Rapport Flash : la section zone)

Quatre **vrais PDF** générés par la chaîne réelle (WeasyPrint) contre la base **dev** (parcelles
réelles) et **regardés** page à page. Livrés dans ce dossier — preuve du mandat.

| PDF | Cas | Ce qui a été vérifié |
|---|---|---|
| `flash-zone-centre-ville.pdf` | Saint-André centre (`97409000AC0701`) | Zone tracée 10 min voiture · **14 276 hab**, revenu **18 846 €\*** (ESTIMÉ), équipements avec temps (« 2 min en voiture »), **carte de la zone avec l'isochrone tracée**, marché (125 ventes / 3 970 €/m² / 99 permis). |
| `flash-zone-hauts.pdf` | Salazie, les hauts (`97421000AB0148`) | Zone peu peuplée mais habitée (**838 hab**), isochrone dessinée sur le cirque, marché peu liquide (5 ventes / 938 €/m² / 11 permis) — dit tel quel. |
| `flash-zone-adresse.pdf` | Entrée commerçant par adresse | En-tête = « 12 rue de la Gare, 97440 Saint-André » + références parcellaires ; la section zone se génère normalement. |
| `flash-zone-degrade.pdf` | Isochrone IGN forcée en échec | Rapport **complet** (7 pages) ; section « Autour de cette parcelle » dit honnêtement « L'étude de la zone atteignable n'a pas pu être établie … aucune valeur approchée n'est affichée ». **Jamais** de page blanche ni de rapport en échec. |

## Ce que j'ai regardé

- **Fidélité écran 3** : population · équipements & commerces (avec temps) · carte de la zone
  (isochrone + parcelle) · marché immobilier de la zone. Conforme à `docs/ZONE/maquette-zone-v1.html`.
- **Honnêtetés présentes** : `€*` + note « Revenu estimé — carreaux INSEE Filosofi 2021, valeurs
  lissées » ; « isochrone IGN, temps *hors trafic* » ; sources & millésimes centralisés (section 10 :
  INSEE Filosofi 2021, MOBPRO, SIRENE, BPE 2025, Isochrones IGN) ; **aucune** prévision de chiffre
  d'affaires ni note d'attractivité.
- **Pagination** : la section démarre sur une page propre (`saut`) ; les tableaux (population, marché)
  ne sont **jamais coupés** entre deux pages. Sur le cas le plus dense (centre-ville), la seule note en
  astérisque déborde seule en fin — bénin ; **choix assumé** de garder `saut` (tableaux entiers) plutôt
  que risquer un tableau coupé. Renumérotation vérifiée : Sources = 10, Limites = 11.
- **Carte de la zone** : rendue par le **même** builder `build_situation_map` (isochrone en polygone
  principal, parcelle en repère) — aucune logique de carte dupliquée ; optionnelle et résiliente.

## Calcul à un seul endroit (vigilance F1)

La section consomme `zone.etude_de_zone` via `flash/data.py::_zone` — **aucune recopie** de la logique de
calcul. `pdf_zone.py` (rendu fpdf2 de l'outil) reste intact. `TEMPLATE_VERSION` 1.3 → **1.4**.

## Findings

- **FZ-001** : le parcours `/flash` ne transmet pas l'activité (NAF). La section est donc générée
  **sans volet concurrence** — dit dans le PDF (« Analyse de la concurrence non incluse : le parcours
  Flash ne précise pas encore l'activité étudiée »). Pour l'activer : champ « activité » au parcours
  (réutiliser `GET /outils/etude-zone/naf`), transmis jusqu'à `generate_flash_report`. **Pas de défaut
  bricolé.**
- **FZ-002** (env, pré-existant) : WeasyPrint nécessite les libs système pango/glib. Sur ce poste
  (macOS ARM), le rendu marche avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (pango via brew).
  C'est la cause du `OSError libgobject` de `test_flash_report`/`test_dossier` dans la suite — antérieur
  au mandat, indépendant de la zone.
