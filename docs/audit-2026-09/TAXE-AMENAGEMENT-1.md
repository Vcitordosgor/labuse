# TAXE-AMÉNAGEMENT-1 — les 24 taux communaux

Branche `feat/taxe-amenagement-1`, worktree `~/Desktop/labuse-ta1`. Aucun merge, aucune bascule.
**Doctrine tenue : aucun taux inventé, estimé, moyenné ou emprunté à une commune voisine.**

---

## Lot A — la source automatique existe (et prime) ✅ FAIT

### La recherche
Point de départ : le fichier **REI** (DGFiP) ingéré par SOURCES-1 porte la taxe **foncière**, pas
la taxe d'**aménagement** — c'est écrit noir sur blanc dans `src/labuse/ingestion/rei.py:10`
(« ⚠ La taxe d'aménagement n'est PAS dans le REI »), vérifié live le 07/09/2026. Rien ne dormait
non plus en base (seule `taxe_amenagement_taux`, vide, 0/24).

**Mais une autre source publique existe, sur la même plateforme que le REI** : le jeu ouvert
**`delta_deliberation_tam_17_01_23`** — *« Taxe d'aménagement — éléments de taxation votés par les
collectivités à partir de 2022 »* — produit par la **DGFiP via son application DELTA**, publié sur
`data.economie.gouv.fr`. Depuis la réforme (transfert à la DGFiP, ord. 2022-883), les communes
transmettent leurs délibérations dans DELTA ; le jeu est **rafraîchi deux fois par an** (fin janvier
et seconde quinzaine d'octobre).

### Ce que porte la source (vérifié sur l'API le 08/09/2026)
- **Clé de jointure commune** : `departement` + `commune` → **INSEE** (974 + 2 chiffres, ex. 974+11
  = 97411 Saint-Denis). Correspond exactement au référentiel LABUSE.
- **Couverture 974 : 24/24 communes**, toutes `DEFINITIF`, toutes en vigueur (`date_fin` nulle).
- **Millésime** : taux en vigueur, avec une **date d'effet** par délibération (`date_effet`). La
  plupart datent du 01/01/2022 ; Trois-Bassins a rebasculé au 01/01/2024, Le Port au 01/01/2025.
- **Grain PARCELLE** : quand une commune sectorise (taux majoré sur des parcelles nommées), le jeu
  a une ligne par parcelle. Le **taux communal général** est la ligne `zone_application=Communale`
  **sans** section/parcelle → c'est celui qu'on retient.
- **Bonus** : une ligne `zone_application=Départementale` donne la **part départementale = 2,5 %**,
  ce qui **CONFIRME** le taux que le YAML ne servait jusqu'ici qu'en « plafond légal à confirmer ».

Le mandat tranche : *si une source existe, elle prime sur la saisie manuelle.* Elle a donc été
**ingérée comme les autres**, avec sa fiche au registre CIRCUIT et son millésime.

### Le tableau des 24 communes (tel qu'ingéré, source DGFiP/DELTA)

| INSEE | Commune | Taux communal | Date d'effet |
|------|---------|:---:|:---:|
| 97401 | Les Avirons | 5 % | 01/01/2022 |
| 97402 | Bras-Panon | 5 % | 01/01/2022 |
| 97403 | Entre-Deux | 5 % | 01/01/2022 |
| 97404 | L'Étang-Salé | 5 % | 01/01/2022 |
| 97405 | Petite-Île | 3,5 % | 01/01/2022 |
| 97406 | La Plaine-des-Palmistes | 5 % | 01/01/2022 |
| 97407 | Le Port | 3 % | 01/01/2025 |
| 97408 | La Possession | 5 % | 01/01/2022 |
| 97409 | Saint-André | 5 % | 01/01/2022 |
| 97410 | Saint-Benoît | 5 % | 01/01/2022 |
| 97411 | Saint-Denis | 3 % | 01/01/2022 |
| 97412 | Saint-Joseph | 3 % | 01/01/2022 |
| 97413 | Saint-Leu | 5 % | 01/01/2022 |
| 97414 | Saint-Louis | 5 % | 01/01/2022 |
| 97415 | Saint-Paul | 5 % | 01/01/2022 |
| 97416 | Saint-Pierre | 5 % | 01/01/2022 |
| 97417 | Saint-Philippe | 5 % | 01/01/2022 |
| 97418 | Sainte-Marie | 5 % | 01/01/2022 |
| 97419 | Sainte-Rose | 1 % | 01/01/2022 |
| 97420 | Sainte-Suzanne | 5 % | 01/01/2022 |
| 97421 | Salazie | 3 % | 01/01/2022 |
| 97422 | Le Tampon | 5 % | 01/01/2022 |
| 97423 | Les Trois-Bassins | 3 % | 01/01/2024 |
| 97424 | Cilaos | 5 % | 01/01/2022 |

*Part départementale (toutes communes) : 2,5 % — confirmée par la même source.*

### Ce qui a été livré (Lot A)
- `src/labuse/ingestion/taxe_amenagement_delta.py` : chargeur qui interroge l'API ODS
  (`data.economie.gouv.fr`), retient le taux communal général en vigueur, reconstruit l'INSEE,
  garde la délibération la plus récente, écarte tout taux hors bornes `[0 ; 20]` (et le liste),
  signale les communes absentes (jamais comblées), remonte la part départementale. **Purge + upsert
  idempotent.**
- CLI `labuse ingest-taxe-amenagement` (rejoue le filtre `taxe_amenagement` après ingestion).
- Vanne « Relancer l'ingestion » (`config/sources_ingestion.yaml`) : le bouton apparaît maintenant
  que la commande existe.
- Registre CIRCUIT (`seed_sources.py`) : la fiche passe de `à faire`/`0/24` à **`connecté`/`vérifié`**,
  provider « DGFiP (application DELTA) », millésime « DGFiP DELTA — 24/24 communes en vigueur »,
  attribution Licence Ouverte 2.0.
- Sonde `taxe_amenagement` (`filtres/sources.py`) : la couverture affiche désormais **24/24** (verte).
- Cadence de veille (`seed_sources.py`) et raison sentinelle (`sentinelle.py`) alignées sur la
  réalité : source auto réingérée à la demande, DELTA publié 2×/an (~200 j).

### Effet sur les surfaces (déjà branché, mécanisme CIRCUIT-3 lot 6.2)
La calculette `taxe_amenagement.py` lisait déjà `taux_communal_public()`. Dès l'ingestion, elle
**cesse d'exiger un taux saisi** et affiche le taux public daté. Vérifié : Saint-Denis renvoie
`3,0 % — source DGFiP DELTA, date d'effet 2022-01-01`. Les six surfaces (outil dédié, fiche, Dossier,
Flash, Financier, pré-dossier PC) qui disaient « taux communal non renseigné » ont maintenant le taux.
*(La mise en avant systématique du millésime « taux 2026, délibération du … » et l'alerte « > 1 an »
relèvent du Lot C — voir plus bas.)*

### Tests
`tests/test_taxe_amenagement_delta.py` (5, verts) : remplissage par INSEE, délibération la plus
récente conservée, taux hors bornes écarté, commune absente signalée, source datée. Les 17 tests
taxe/calculette existants restent verts ; 72 tests seed/circuit/sentinelle/sources verts.

---

## Lot B — saisie manuelle : SANS OBJET
Le mandat conditionne le Lot B à l'absence de source automatique (« à défaut »). **Une source
existe et couvre 24/24 → le Lot B n'a pas lieu d'être.** Aucun fichier de saisie manuelle n'est
créé (il ferait doublon avec une source officielle qui se met à jour toute seule). *À décider par
Vic : confirmer qu'on ne monte pas de canal de saisie manuelle en parallèle.*

---

## Lot C — la fraîcheur : À FAIRE (lot suivant)
- Millésime affiché **partout où le taux apparaît** (« taux communal 5 %, délibération en vigueur
  au 01/01/2022, source DGFiP/DELTA »).
- Alerte quand un taux date de plus d'un an (modèle des autres sources périmées).
- La ligne de sonde `X/24` existe déjà (24/24 vert) — reste à la remonter au tableau de bord.

---

## Ce qu'il reste côté Vic
1. **Décision Lot B** : confirmer qu'aucune saisie manuelle parallèle n'est montée (source auto suffit).
2. **Part départementale** : DELTA confirme 2,5 %. Faut-il basculer le YAML de « à confirmer » à
   « confirmée par DELTA » ? (touche le total servi au banquier — laissé au Lot C / à ton aval).
3. **Feu vert pour le Lot C** (millésime affiché + alerte fraîcheur).
4. Merge / bascule : réservés à Vic (rien poussé, rien mergé).
