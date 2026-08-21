# Retrait « Suivi de secteur » (O7 / carnet) — 21/08/2026

Retiré du produit (DORMANT). Branche `feat/retrait-suivi-secteur`. Ne merge pas.

## Mesure « ce qu'on perd » (rendue AVANT le retrait, comme demandé)

La vue-instantané du carnet agrégeait, par section cadastrale (`left(idu,10)`) : opportunités (stock
brûlante+chaude), prix DVF secteur, permis 24 mois, signaux, ZAN commune. Où chaque bloc existe-t-il APRÈS
le retrait ?

| Bloc du carnet | Ailleurs ? | Où |
|---|---|---|
| **Prix DVF secteur** (`dvf_secteur_medianes`, 2 359) | **OUI** | **Fiche parcelle** — `dvfSecteur` (`Fiche.tsx:1358`), « Prix secteur €/m² », section « Marché — prix de sortie bâti (secteur) ». Ouvrir n'importe quelle parcelle de la section. |
| **ZAN** (conso commune) | **OUI** | **Communes** (fiche commune, section « Rareté & ZAN ») + fiche parcelle. ZAN est de toute façon commune-level. |
| **Permis 24 mois** | **OUI (autre grain)** | **Radar permis** (par commune / zone dessinée, zoomable sur la section) + fiche parcelle (permis à proximité, `/parcelle-permis`). Pas un compte PAR SECTION, mais trouvables. |
| **Signaux de veille** (`parcel_signals`) | **OUI** | La **Veille** surface les mêmes signaux (c'est son métier). |
| **Opportunités AGRÉGÉES par section** (compte brûlante+chaude sur `left(idu,10)`) | **NON — nulle part** | Aucun autre point n'agrège les opportunités par section (grep = 0 hors `carnet.py`). Sur la **carte**, les parcelles de la section sont colorées par tier → **visible à l'œil, jamais compté**. |

### Réponse à « où le client trouve l'état de cette section ? »
- Prix → fiche d'une parcelle de la section. ZAN → Communes. Permis → radar permis (zoom secteur) ou fiche.
  Signaux → Veille.
- **SEUL manque réel** : le **compte d'opportunités agrégé par section**, en un chiffre. Il n'a **pas d'autre
  foyer** (on le devine sur la carte, on ne le lit pas). Ce n'est pas « toute la vue est perdue » — c'est
  **ce chiffre-là** qui l'est.

### Piste si tu veux le garder (à décider, non fait ici)
Poser ce compte là où on regarde déjà une section : **la section « secteur » de la fiche parcelle** (« N
opportunités dans cette section »), ou un **survol carte** par section. Petit ajout, foyer naturel — mais
c'est une décision produit, hors de ce retrait.

## Le retrait (même patron)
- **Écran** : entrée `registry` (groupe « temps »), `COMPONENTS` + import dans `ModulePanel` retirés.
  Vérifié : « Suivi de secteur » absent du menu, pas de bouton `data-outil=o7-carnet`.
- **Concept-route Copilote** (`answering.py`) : SUPPRIMÉE (sinon lien mort — piège Foncier fantôme). Les
  demandes « suivi de secteur » retombent sur le traitement normal (le vrai suivi = la Veille).
- **Portes depuis la fiche** : AUCUNE (grep = 0) — rien à couper.
- **Reste au dépôt (DORMANT)** : composant `O7Carnet` (exporté), endpoints `/carnet-secteur`, tests.
- Tests alignés : `test_suivi_de_secteur_retire_plus_de_concept` (concept = None), gate `qa/m112/portes`.

## Vérif
Capture (menu sans « Suivi de secteur ») · Copilote guidage 26/26 · golden 119/119 · garde-run
431 663=431 663 · tsc 0 · build.
