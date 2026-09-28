# EXPORTS-FIX-1 — compte rendu

Mandat du 28/09/2026, deux parcelles (Dossier + Apporteur) : **P1** `97408000AO1424` (La Possession,
zone A, 25 046 m²) · **P2** `97415000EO0796` (Saint-Paul, U5b, 479 m²). Financier et Pré-dossier PC
hors mandat. Branche `fix/exports-fix-1` depuis `origin/main` (52f97272).

## Étape 0
1. Worktree créé depuis `origin/main` (`52f97272 Merge RETOURS-15 …`).
2. Base locale : `residuel_runs WHERE is_served` = **run 10** (`q_v15 assiette gabarit`). ✓ (pas de STOP)
3. API sur 8615 (`.venv` PDF-capable, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`, `PYTHONPATH=$PWD/src`,
   `LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`).
4. Avant : Dossier + Apporteur de P1 et P2 + `fiche-<idu>.json` → `avant/`.
5. Diff fiche ↔ Dossier → `etape0-diff.md`. **Gate < 20 lignes manquantes** : les seules lignes
   servies par la fiche et absentes du PDF sont `rang_tier` et `tier_opportunite` (le SCORE, écarté
   par conception) → **2 lignes**, aucun STOP. Sert le lot D (voir D1).

## Recette (globale)
- `apres/` : Dossier + Apporteur de P1 et P2 régénérés (+ `fiche-<idu>.json`, `.txt`).
- `captures/` : PNG avant/après (même page) des pages porteuses de chaque point + `B2-orthophoto-P1-piscine.jpg`.
- `recette_exports_fix1.py` : **RECETTE OK** — mots interdits (aucun ; aucune date `AAAA-MM-JJ`),
  champs Apporteur (noms uniques hors radio ; remplir un champ n'en change qu'un), cohérence
  garde ↔ sections (SDP, zone, risques, exposition — aucune tuile vide).

Mots interdits testés : `{'`, `part_pct`, `fiche identite`, `miroir de la fiche`,
`bandeau des six chiffres`, `mouvement_terrain`, `ocsge`, `scot_gpu`, `SCOT SCOT`, `1 bâtiments`,
toute date `AAAA-MM-JJ`. Tous absents des 4 documents.

Suite d'exports : `138→295 passed` selon le filtre, **un seul échec** :
`tests/test_oracle_dossier.py::test_oracle_couvre_chaque_ligne_du_dossier` — **pré-existant sur
`origin/main`** (vérifié en dé-stashant : `scot_parcelle`, `mesures_compensatoires_parcelle` sans
oracle) — hors mandat. `test_exports2_lot2` mis à jour pour les deux encadrés C6.

---

## Lot A — Rien de brut ne s'imprime · commit `6894dd67`
| # | fait | preuve |
|---|---|---|
| A1 | EBC : liste de dicts → « Espace boisé classé — 89,6 % de la parcelle » | P1 §4 · `P1-dossier-p3-*` |
| A2 | Garde : « Modèle 3.0 · miroir de la fiche » et « Le bandeau des six chiffres… » retirés | garde · `*-dossier-p1-*` |
| A3 | Sommaire : plus de clé technique « fiche identite … annexe » | garde · `*-dossier-p1-*` |
| A4 | « mouvement_terrain » → « mouvement de terrain » ; OCS GE US* → libellé FR ; sources « ocsge »/« scot_gpu » nommées | §2/§5 · `P1-dossier-p5-*` |
| A5 | SUP dédoublonnée par catégorie CNIG + libellé (« 1 servitude — PM1 — plan de prévention des risques ») | P1 §4 · `P1-dossier-p3-*` |
| A6 | Valeur ne répète plus le libellé (« SCOT SCOT », « TFPB : TFPB », « DPU : DPU ») | §4/§7 |
| A7 | Dates ISO → JJ/MM/AAAA partout | §4/§7 |
| A8 | Textes internes retirés/clairs (« propriétaire depuis au moins 2019 », « document Financier », « Bilan indicatif », « confirmée par les faits », « sur-détection », « PLU non calibré (estimation générique) », « N familles vérifiées sur 4 … non intégrée(s) ») | §1/§6/§7/§10 |
| A9 | §7 : chaque dispositif nommé (TVA outre-mer, ORT, QPV) | P1 §7 · `P1-dossier-p5-*` |

## Lot B — Un fait, une valeur · commit `225cbfdd`
| # | fait / STOP | preuve |
|---|---|---|
| B1 | SDP « restante » de la garde = redite au §10, même valeur, dite « SDP résiduelle (droits à bâtir non consommés) ≈ 179 m² » (un plancher — libellé « SDP » juste) | P2 garde+§10 · `P2-dossier-p1/p8-*` |
| B2 | Piscine FLAIR ∪ CoSIA **confirmée sur l'orthophoto** (capture) → ligne au §2 seulement ; hors §7 et hors compte (6→5 dispositifs) | `B2-orthophoto-P1-piscine.jpg`, `P1-dossier-p5-*` |
| B3 | Risques : « N couches de risque relevées par la cascade » (dit ce qu'il compte) | §5 |
| B4 | **STOP** — afficher faîtage (13 m) **et** égout (9 m) avec une marge sous CHAQUE règle et laquelle mord exige que le moteur gabarit porte la hauteur d'égout et la double marge (aujourd'hui : faîtage seul). Hors couche export (moteur, frontière fiche). Non corrigé. | — |
| B5 | §4 : `dispositifs_parcelle` (SUP) ne revendique plus « aucune prescription (ER/EBC/DPU/PEB) » quand un DPU est présent | P2 §4 · `P2-dossier-p4-*` |
| B6 | Marché : périmètre (secteur cadastral) + fenêtre par prix ; même seuil (5 ventes) pour tous les types (appartement à 2 ventes omis) ; médiane 100 m tous types retirée ; ligne 100 m une seule fois (§8) | §8/§9 |
| B7 | Permis « à proximité » : rayon **et** fenêtre (500 m · 24 mois, arbitrage Q7) | §9 |
| B8 | Stationnement : au-delà de 800 m → « hors rayon » (P1 à 812 m) | P1 §6 |
| B9 | Étiquettes : sol libre → *dérivé* ; viabilisation (score) → *estimé* ; TA (barème DELTA) → *sourcé* ; « emprise non réglementé » même étiquette §4 et §10 | §2/§4/§6/§7/§10 |

## Lot C — Vrai ou retiré · commit `dd5ce52d`
| # | fait / STOP | preuve |
|---|---|---|
| C1 | PLU : date d'approbation Sudocuh + dernière évolution ; date GPU dite « publiée au Géoportail ». **Recette : La Possession 12/06/2019, Saint-Paul 27/09/2012** ✓ | §4 · `*-dossier-p3/p4-*` |
| C2 | FRR : plus de « Parcelle DANS » sans test géométrique ; **FAQ FRR DGCL juillet 2025** vérifiée — à La Réunion (ZSAR des Hauts, décret 1978) seules les mesures NON FISCALES s'appliquent : l'art. 44 quindecies A CGI **ne s'y applique pas** (dit) | P1/P2 §7 |
| C3 | Ligne « Aucune divergence SAR indiquée » retirée (SAR hors base) | §4 |
| C4 | RTAA DOM : jamais « aucune exigence » — s'applique à tout logement neuf (dit) | §4 · `P2-dossier-p4-apres` |
| C5 | VEFA : **cause = clé `marche_secteur.neuf_vefa` jamais peuplée** (→ « insuffisant » systématique) alors que le registre sert la médiane (`neuf_vefa_commune` : Saint-Paul n=299/4 750 €/m², La Possession n=86). **Code corrigé** : lecture du registre | §8 |
| C6 | Deux encadrés : « Vérifié : rien » et « Non disponible ici » avec LA raison (jamais « zone non constructible OU données manquantes ») | §4/§5/§10 · `P2-dossier-p4-*` |
| C7 | Exposition calculée par le moteur (P1 plat, P2 Nord-Ouest) ; SDP zone A/N → « 0 m² — zone A » ; aucune tuile de garde vide | garde · `*-dossier-p1-*` |
| C8 | Verdict A/N cohérent avec les destinations (« non constructible pour un projet d'habitat courant ; seules les destinations agricoles/naturelles sous conditions ») ; ligne Terrain en A/N : « terrain à bâtir, ne vaut pas pour une parcelle agricole ou naturelle » | P1 §4/§8 |

## Lot D — Toute source citée imprime sa ligne · commit `c58d0271`
| # | fait / STOP | preuve |
|---|---|---|
| D1 | Diff étape 0 : aucune ligne non-score manquante (seuls `rang_tier`/`tier_opportunite`, le score, écartés) — rien à ajouter | `etape0-diff.md` |
| D2 | Sources citées sans ligne servie → hors §12 (RPG, ONF, INPN, Parc national, Cartofriches, BD CARTO, 50 pas, classement sonore, érosion, BODACC/INPI, Géorisques générique). **Réserve** : afficher RPG / BODACC / dirigeant INPI en LIGNES (plutôt que retirer) demande d'ingérer le RPG (table absente) et de câbler des extracteurs BODACC/INPI — non fait. | §12 |
| D3 | Alias « Potentiel foncier Région (ODS) » / « data.regionreunion.com — Potentiel foncier » → source canonique unique (et, non servie ici, sort via D2) | §12 |
| D4 | §9 : le plus proche de chaque famille avec nom + distance (École : LYCEE… (275 m)…), propre à la parcelle | §9 |

## Lot E — Apporteur · commit `97613640` (+ correctif date PLU, recette)
| # | fait | preuve |
|---|---|---|
| E1 | Noms de champ uniques (q1…q26) ; choix uniques = groupes RADIO. Recette pypdf : remplir un champ n'en change qu'un ✓ | `*-apporteur-p1/p2-*`, recette |
| E2 | Cases radio ≥ 4 mm sur la ligne du libellé ; zones en textarea, hauteur selon la question | `*-apporteur-*` |
| E3 | §6 : questions tirées des couches — corrigé le drapeau `obs_eau` (lisait « nature OU libellé », manquait « …inondation… » d'un PPR) : P1 a la question d'eau, P2 non | ctx obs_eau P1=True/P2=False |
| E4 | §3 version PERSONNE MORALE pour P2 (dirigeant, organe, signataires, procédure) — plus d'âge/indivision/succession/époux | `P2-apporteur-p1-*` |
| E5 | Note « Absents volontairement… » retirée | `*-apporteur-p1-*` |
| E6 | 5 points de vue NUMÉROTÉS, dits en clair (plus de « PCMI7-8 ») ; émetteur en tête | `*-apporteur-p2-*` |
| E7 | « 1 bâtiment » ; « Arrêt de bus » ; « A (agricole) » / « U5b (urbaine) » | `*-apporteur-p1-*` |
| E8 | Plus de saut de page forcé entre sections (fini la p.3 presque vide) | `*-apporteur-*` |

## Lot F — Forme · commit `d2a528f5`
| # | fait / réserve | preuve |
|---|---|---|
| F1 | « Généré via LABUSE » ne chevauche plus la dernière ligne : marge basse @page 19→24 mm, mention (div fixe) dans la bande réservée. *Note : dans ce WeasyPrint, seuls les div fixes et le compteur se rendent — les blocs de marge `string()`/`element()` sont inertes (pré-existant).* | `P1-dossier-p3-apres` |
| F2 | Garde : code de zone complet (« U5b ») | garde · `P2-dossier-p1-apres` |
| F3 | Plan calé sur la parcelle (plafond 19 = max ortho IGN via `zoom_max`, plus de « −1 ») : 479 m² n'est plus un point | `P2-dossier-p2-*` (§1) |
| F4 | IDU en police MONO (0 pointé) : « 97415000EO0796 » ne se lit plus « …E00796 » | garde · `*-dossier-p1-apres` |
| F5 | Gabarit : légende = éléments présents (plus de « PPR rouge » sans exclusion) ; bâti existant tracé. **Réserve** : le « côté rue » explicite n'est pas porté par le résultat gabarit du chemin fiche (lisible via bâti + retraits + contour) | P2 §10 · `P2-dossier-p8-*` |

---

## STOP / réserves (récapitulatif)
- **B4** — hauteurs faîtage/égout + double marge : moteur gabarit (frontière fiche), non corrigé.
- **D2** — RPG/BODACC/INPI en LIGNES : RPG non ingéré (table absente), BODACC/INPI non câblés ; les
  sources silencieuses sont retirées du §12 (option « sinon elle sort de la liste »).
- **F5** — « côté rue » explicite : non porté par le résultat gabarit servi à la fiche.
- **Test pré-existant** `test_oracle_dossier` : échoue déjà sur `origin/main`, hors mandat.

## Règles respectées
Aucune écriture en base, aucune réingestion, aucun run. Le front de la fiche (React) n'a pas été
touché. Un commit par lot, après sa recette. Les corrections hors couche export qui auraient changé
la valeur servie à la fiche ont été traitées côté export (présentation) ou signalées en STOP.

---

# EXPORTS-FIX-1-BIS — restes de la recette (seconde passe)

Régénération → `apres-bis/` ; captures avant(=`apres/`)/après(=`apres-bis/`) → `captures-bis/` +
`planche-bas-de-page.png` (27 bas de page des 4 PDF). Recette : `recette_exports_fix1.py` pointe
sur `apres-bis/` avec les mots interdits ajoutés (`cascade`, `engagée le`, `capacité nulle`) →
**RECETTE OK**. Test unitaire de la table OCS GE : `tests/test_ocsge_nomenclature.py` (4 tests).

| # | fait / STOP | preuve | commit |
|---|---|---|---|
| 1 **bloquant** | Nomenclature d'usage OCS GE reprise CODE PAR CODE (IGN) : US1.1 = « Agriculture », US5 = « Usage résidentiel » (l'ancienne table les inversait). Test unitaire + garde anti-inversion. | `P1-dossier-p2-*` · `test_ocsge_nomenclature` | `bd8bbee5` |
| 2 | P2 §10 : plus de ligne qui contredit la SDP résiduelle servie — « surface de plancher non calculable (capacité nulle) » retirée ; la capacité dit sa vraie raison. | `P2-dossier-p8-*` | `01ad227f` |
| 6 | Risques : garde ET §5 = nombre d'aléas IMPRIMÉS (2 sur P1, 1 sur P2) ; le mot « cascade » disparaît. | `P1-dossier-p4-*` | `01ad227f` |
| 11 | Étiquettes : viabilisation (score) → « probable » ; gabarit non chiffré → « Non disponible ici » sans étiquette ; surélévation → une seule cause (hauteur de règle). | `P1-dossier-p7-*` | `01ad227f` |
| 3 | Terrain nu « insuffisant » nomme SON périmètre (« à moins de 500 m ») ; plus de « secteur » ambigu. | `P2-dossier-p6-*` | `4da15c87` |
| 4 | RTAA DOM = règle applicable → ligne normale du §4 (« Rappel RTAA DOM »), hors de l'encadré. | `P2-dossier-p4-*` | `4da15c87` |
| 5 **STOP donnée** | « dernière évolution » = date d'APPROBATION Sudocuh, jamais une prescription : plus de « engagée le 16/12/2021 ». La base Sudocuh locale ne porte PAS le 27/03/2025 (recette) — seulement l'approbation 2012-09-27 et la prescription 2021-12-16 → la ligne d'évolution s'omet, correctement (aucune écriture en base ; le 27/03/2025 viendrait d'une ingestion Sudocuh plus fraîche). | `P2-dossier-p4-*` | `4da15c87` |
| 8 | §5 : ABF / ICPE / cavités, citées en source sans ligne, impriment leur « vérifié : rien » quand la cascade les a lues (result PASS). | `P1-dossier-p4-*` | `4da15c87` |
| 7 | « Généré via LABUSE » dans un bloc de marge @page (@bottom-center statique) : jamais dans le flux, aucun chevauchement (vérifié sur les 27 bas de page) ; en-têtes de groupe `break-after: avoid`. | `planche-bas-de-page.png` | `f9586be6` |
| 9 | Apporteur : sans émetteur, le §9 renvoie « à la personne qui vous a remis ce document » (plus « à l'émetteur (en tête) » inexistant). | `P1-apporteur-p4-*` | `f9586be6` |
| 10 | Apporteur : ronds sur la ligne du libellé (« ◯ Non ◯ Oui ◯ Ne sait pas », `display:inline-block`) ; brief compact de 4 pages, aucune page à une seule question. | `P1-apporteur-p2-*` | `f9586be6` |

## STOP / réserve BIS
- **Point 5** — le 27/03/2025 (dernière modification approuvée) n'est pas dans la base Sudocuh
  locale ; le code sert désormais une date d'approbation (jamais une prescription) et omet la ligne
  faute d'approbation d'évolution — conforme à la règle « sinon la ligne ne s'imprime pas ».
