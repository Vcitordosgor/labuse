# CIRCUIT-6 lot 0 — l'inventaire des contournements, et leur raccordement

*La règle mère : tout ce qui s'affiche à un client — un chiffre, un libellé, une liste de
sources, un drapeau d'état, un nom de couche — vient du registre ou casse la CI. Ce document
inventorie ce qui vivait À CÔTÉ du registre (une ligne par contournement), et dit pour chacun
le raccord : fait au lot 0, ou confié au lot qui le porte.*

*Note d'héritage : le verrou « provenance des chiffres » (RECETTE-7 Z5) et la liste dérivée de
libellés (RECETTE-8) vivent sur des branches recette NON mergées — ils n'existent pas sur main.
CIRCUIT-6 construit donc le rattachement sur main, sans dépendre d'eux.*

## L'inventaire

| # | Endroit | Ce qu'il affiche | D'où ça vient réellement | Raccord |
|---|---|---|---|---|
| 1 | Fiche parcelle — « Les données » (`app.py:_data_sources_fiche`, 2800) | ~28 sources (nom, producteur, millésime, fiabilité) | `data_sources` ⋈ `dryrun_cascade_results` (participation cascade — la MÊME batterie partout, donc liste quasi identique pour toutes les parcelles) + millésime composé 4 niveaux en Python | **Lot 7** (fuite n°1) : le manifeste devient « sources qui ont réellement une valeur pour CETTE parcelle » via le moteur de remplissage (lot 2) |
| 2 | Fiche — libellés de fiabilité (`_FIAB`, app.py:2823) | « surveillée / estimée / déclarative / à confirmer » | dict Python local en dur | **FAIT lot 0** : `vocabulaires.FIABILITE_LIBELLES`, garde `test_fiabilite_importee_du_vocabulaire` |
| 3 | Page /sources — drapeau « à jour » (`etats_sources.py:etat_source`) | « À jour. » par source | version sentinelle SEULE — jamais le remplissage (le DPE disait « à jour » avec 17 lignes) | **Lot 4** (G4) : l'état combine version ET remplissage |
| 4 | Page /sources — compteur (accueil.py:85) | « 95 sources » | `count(*) WHERE_AFFICHEES` (calculé ✓) mais les 21 hors vitrine sont TUES | **Lot 1** (G1) : 95 et 116 côte à côte, écart détaillé par statut |
| 5 | Carte — noms de couches (`frontend/src/lib/layers.ts`) | libellés + mention de source (« Occupation du sol (BD CARTO V5 — grain grossier) ») | codés en dur au front, jamais lus du registre | **Partiel lot 0** : parité kinds↔carte des réservoirs (`test_kinds_de_routes_dans_la_carte`, avec la carte d'alias sis/casias/ebc/er/plu_gpu/rpg/enp/tcsp_axe) + pin du libellé ocs_ge (« BD CARTO », jamais « OCS GE (IGN) »). **Reste** : libellés du panneau Cartes non dérivés du registre (écrit tel quel, mandat futur) |
| 6 | Couche « OCS GE » | — | **déjà réparé sur main** : layers.ts:47 dit « Occupation du sol (BD CARTO V5 — grain grossier) » ; la page /sources dit « PROXY » | **FAIT (constat) + garde lot 0** `test_ocs_ge_libelle_dit_bd_carto` (anti-régression) |
| 7 | Outil Taxe d'aménagement | montant calculé depuis les taux communaux | chiffres `taxe_amenagement_eur`/`_estimee` avaient `reservoirs=()` → la source 98 n'alimentait RIEN au graphe | **FAIT lot 0** : arête `taxe_amenagement` posée sur les deux chiffres (donnees.py), garde `test_aretes_taxe_catnat_rtaa_presentes` |
| 8 | Fiche commune / Pièges — CatNat | 426 arrêtés | `catnat_n` avait `reservoirs=()` → catnat_gaspar muet | **FAIT lot 0** : arête `catnat_gaspar` posée |
| 9 | Faisabilité — rappel RTAA DOM (modules.py:1763) | exigences de conception DOM | `config/rtaa_dom.yaml` servi sans AUCUN chiffre au registre (source 43 n'alimentait rien) | **FAIT lot 0** : chiffre `rtaa_exigences` (passe_plat, réservoir rtaa_dom) + rattaché au robinet `outil_faisabilite` |
| 10 | Scan patrimoine — SIRENE | recherche société | lit `parcelle_personne_morale` (DGFiP) ; le connecteur « SIRENE » (connectors/__init__.py:68) pointe le MÊME endpoint que la source 45 (DINUM) | **Lot 1** (G1) : doublon de canal 21/45 à faire sonner puis arbitrer |
| 11 | Exports PDF — libellés de scénarios (exports/blocs/potentiel.py) | « Au sol… / En hauteur… / Reconstruction… » | littéraux en dur dans le module de rendu | **FAIT lot 0** : `vocabulaires.SCENARIOS_POTENTIEL` + garde `test_scenarios_importes_du_vocabulaire` |
| 12 | Libellés de paliers (tiers) | « Priorité / À suivre / … » | `scoring/tiers_client.py` + miroir front testé | **déjà raccordé** (constat, rien à faire) |
| 13 | Sentinelle — raisons de non-surveillance | (admin) pourquoi une source n'a pas de sonde | `sentinelle.RAISONS_NON_SURVEILLEES` (43 entrées) — dict séparé, exhaustivité non garantie | **Lot 4** (G4) : verrou « sonde OU raison, jamais rien » |
| 14 | Hauteur bâti servie | « Hauteur du bâti (BD TOPO) » | `potentiel.py:_hauteur_bati_m` lit BD TOPO ; la table LiDAR `batiment_hauteur_lidar` (303 452 lignes en base) n'est lue par PERSONNE sur main et absente de la carte des réservoirs | **Lot 7** (fuite n°2) : brancher la hauteur LiDAR et la créditer à `lidar_hd_mnh` |
| 15 | DPE | « à jour » sur /sources, fiche vide | `dpe_records` = 17 (amont ADEME pollué : ~913 lignes 974*, ~897 à CP métropolitain) | **Lot 7** (fuite n°4, seule ingestion autorisée) + **Lot 2** (G2 : INVISIBLE affiché) |

## Ce que le lot 0 a posé (code)

- `src/labuse/vocabulaires.py` — FIABILITE_LIBELLES + SCENARIOS_POTENTIEL (un littéral, un endroit).
- `app.py` et `exports/blocs/potentiel.py` importent le vocabulaire (plus de littéral local).
- `registre/donnees.py` — 3 arêtes posées (taxe ×2, catnat) + 1 chiffre créé (`rtaa_exigences`) ;
  `registre/robinets.py` — `outil_faisabilite` sert `rtaa_exigences`. Registre cohérent : 240
  chiffres, 157 robinets, 0 réservoir inconnu.
- `tests/verrous/test_lot0_contournements.py` — 7 gardes (dont 1 preuve « la garde mord » sur un
  kind inventé).

## Ce qui reste ouvert (confié aux lots)

G1 : compteur 116 + doublons (lot 1) · G2 : INVISIBLE mesuré (lot 2) · G4 : à-jour combiné +
raisons exhaustives (lot 4) · G7 : manifeste par parcelle, hauteur LiDAR, DPE (lot 7) ·
libellés du panneau Cartes dérivés du registre : NON FAIT, écrit tel quel (mandat futur).
