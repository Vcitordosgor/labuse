# MARCHE-UNIQUE-1 — un seul module de marché DVF

**Branche** `fix/marche-unique-1` · worktree `~/Desktop/labuse-marche` · ports 9140/6340 · base locale `labuse`
(434 582 parcelles, DVF arrêté 2025-12-31). **Aucun merge, aucun accès prod, lecture seule prod.** Pas de
touche au résiduel (SDP) ni aux risques (PPR) — sessions sœurs.

## Le problème (registre NU-1)

Chaque surface recalculait sa médiane de marché avec son propre filtre de nature, sa propre fenêtre et son
propre dénominateur. Résultat mesuré AVANT, sur la base réelle :

| Surface | Saint-Denis maison | Saint-Paul appartement |
|---|---|---|
| Radar — tableau (`_dvf_bati_type`, tout-historique, baromètre [100;12000]) | 3 085 | 4 704 |
| Radar — « Ce bien » / Estimer / PDF (`marche_commune_bloc`, fenêtre 12 mois) | 3 235 | 5 427 |

Deux « acté médian maisons » sur le MÊME écran (NU-F-001, +4,8 % à +15,4 %), le neuf (VEFA) qui remontait la
médiane « ancien » (NU-A-012 / NU-D-011 / NU-E-025 / NU-E-030), un prix d'appartement servi sur une maison
(NU-A-002 / NU-D-010), un dénominateur terrain gonflé (NU-E-031), des caches jamais datés (NU-E-032), la
parcelle comparée à elle-même (NU-E-023), et les loyers OLL « non disponibles » partout (NU-A-013).

## La réponse : un point de calcul UNIQUE

Nouveau module **`src/labuse/marche_dvf_commune.py`** — `mediane_commune(db, commune, type_bien)` et
`mediane_neuf_commune(db, insee)`. Doctrine (un critère, un endroit) :

- **Nature** — l'ANCIEN bâti = `nature_mutation = 'Vente'` STRICT. Natures réelles mesurées en base :
  `Vente`, `Vente en l'état futur d'achèvement` (VEFA = neuf), `Vente terrain à bâtir`, `Adjudication`,
  `Echange`, `Expropriation` (**viager absent de DVF Réunion**). On exclut VEFA, VTB, adjudication, échange,
  expropriation de l'ancien. Le TERRAIN nu = `Vente` + `Vente terrain à bâtir` (M101 B2).
- **Multi-parcelles / dépendances** — le bâti lit `dvf_mutations` (grain MUTATION, dépendances agrégées) ;
  le terrain lit `dvf_mutations_parcelle` et DÉDOUBLONNE (`max()` par (mutation, parcelle) puis `sum()`).
- **Fenêtre** — millésime géo-DVF ENTIER, ancré sur `max(date_mutation)` (jamais `now()`).
- **Neuf** — médiane VEFA dédiée, un seul libellé « neuf (VEFA) » (NU-B-003).

Les surfaces **fiche, Estimer, Radar (tableau + « Ce bien »), Communes (fiche commune), Étude et PDF** lisent
désormais cette médiane via `_dvf_bati_type` et `marche_commune_bloc`, tous deux rebranchés sur le point unique.

## Recette — « la même médiane partout »

`mediane_commune` == tableau Radar (`_dvf_bati_type`) == bloc commune (`marche_commune_bloc`, lu par « Ce bien »,
Estimer et les PDF), prouvé sur la base réelle pour 3 communes × 2 types :

| Commune | Type | canon | tableau | « Ce bien »/Estimer/PDF |
|---|---|---|---|---|
| Saint-Denis | maison | 3 263 | 3 263 | 3 263 |
| Saint-Denis | appartement | 2 380 | 2 380 | 2 380 |
| Saint-Pierre | maison | 3 145 | 3 145 | 3 145 |
| Saint-Pierre | appartement | 2 950 | 2 950 | 2 950 |
| Saint-Paul | maison | 3 944 | 3 944 | 3 944 |
| Saint-Paul | appartement | 4 694 | 4 694 | 4 694 |

**Écart résiduel : 0 € partout** (avant : jusqu'à +15,4 %). Test de non-régression qui échoue au moindre écart :
`tests/test_marche_unique_1.py` (seed 3 communes × 2 types + VEFA/adjudication/échange à exclure ; vérifie la
convergence des 3 surfaces à l'euro près ET que la VEFA/adjudication ne contaminent pas l'ancien).

## Avant / après chiffré

- **NU-F-001 (divergence Radar)** : jusqu'à **+15,4 % → 0 %** (médiane identique sur toutes les surfaces).
- **Estimation MAISON sur le banc** (ventes maison DVF 2025 mono-parcelle, n≈2 047 estimables, estimateur
  `comparateur_bien`, no-leak renforcé par l'exclusion de la parcelle sujet) :
  **|écart| médian 28,0 % (BANC-RAYON-1) → 24,7 %** (type déduit, même méthode) ; **23,8 %** en forçant le type
  maison (effet NU-D-010). Gain porté par l'exclusion VEFA (NU-E-030) et l'auto-exclusion (NU-E-023).
- **NU-E-031 (dénominateur terrain)** : **1 092 / 16 205 mutations terrain (6,7 %)** avaient un dénominateur
  gonflé par les lignes `nature_culture` répétées (facteur jusqu'à **×435**) → corrigé (max par parcelle puis somme).
- **NU-A-013 (loyers OLL)** : **0 → 429 709 parcelles (98,9 %)** rattachées à une zone OLL (preuve 5 parcelles,
  5 communes : 97403→9,2 · 97409→9,2 · 97411→12,2 · 97415→11,5 · 97416→11,0 €/m², `fiche.disponible=True`).
- **NU-E-032 (caches datés)** : `caches_marche_perimes()` signale les deux caches prod comme « antérieurs à
  NU-E-032 » (colonne `millesime_dvf` absente) ; après rebuild ils portent et vérifient leur millésime.

## Détail des correctifs

| Fichier | Correctif | Findings |
|---|---|---|
| `marche_dvf_commune.py` (neuf) | point de calcul unique commune×type + neuf + `caches_marche_perimes` | F-001, A-002, D-010, B-003, E-032 |
| `pige/signaux.py` `_dvf_bati_type` | délègue à `mediane_commune` (maison/appartement) | F-001 |
| `faisabilite/marche_commune.py` `marche_commune_bloc` | médianes servies = `mediane_commune` ; 12 mois réservé à l'évolution | F-001, A-002, D-010 |
| `faisabilite/bilan.py` `_ventes_bati_dedup`/`sector_price`/`reference_locale` | nature `= 'Vente'` + VEFA hors médiane servie « ancien » (split neuf/ancien préservé) | A-012, E-025, E-030, E-035 |
| `marche_service.py` `comparables`/`comparateur_bien` | nature `= 'Vente'` + exclusion parcelle sujet | A-012, E-023, E-025 |
| `marche_service.py` `comparateur_terrain` | dénominateur dédoublonné (max par parcelle) + nature terrain + exclusion sujet | E-031, E-023, E-025 |
| `dvf_mediane.py` `mediane_bati` | nature `= 'Vente'` + fenêtre ancrée sur `max(date_mutation)` | A-012, E-033 |
| `ingestion/dvf_marche.py`, `ingestion/dvf_prix_neuf.py` | colonne `millesime_dvf` + stamp au build + migration douce | E-032 |
| `ingestion/oll_loyers.py` `oll_parcelle` | join sur `right(subtype,4)` (+ repli commune `0000`) | A-013 |
| `scoring/p_v2/potentiel.py` | `prix_secteur_eur_m2` → `prix_commune_eur_m2` (le grain est `left(idu,5)` = commune) | E-014 |
| `frontend/.../ContextePanel.tsx` | libellé « neuf » → « neuf (VEFA) » (un seul libellé neuf) | B-003 |
| `registre/lectures.py` | déclaration fine des arêtes du nouveau module (graphe exact) | — |

## Garde-fous & choix assumés

- **Non touché** : le résiduel/SDP et les PPR/risques (sessions sœurs) ; la SDP n'est que *lue* (nature,
  potentiel) sans modification de son calcul.
- Le baromètre 24 communes (`prix_ancien_communes`, mixte [100;12000], tout-historique) reste **volontairement
  distinct** (« on observe tout le marché » — commentaire `moteurs.py`) ; il est déjà en `= 'Vente'` (sans VEFA).
  La cohérence par type est servie sur la fiche commune, le Radar, Estimer et les PDF.
- `sector_price` garde son split neuf/ancien (`_comparables`) pour le PDF banquier ; seule la médiane SERVIE
  comme « Prix ancien médian » devient ancien-seul.

## Tests

- Hook (famille unitaire, `-m "not db and not local and not reel and not network"`) : **2 769 passés, 0 échec**.
- Famille base de test (`labuse_test`) : marché + recette + scoring potentiel **verts** ; les contrôles de
  cohérence dépendants de données réelles *skippent* sur base vide (vérifiés sur la base réelle, cf. supra).
- `tests/test_marche_unique_1.py` (recette, échoue au moindre écart) et `tests/test_reparations1_lot2.py`
  (graphe des arêtes exact) : verts.

Rejeu : `LABUSE_TEST_DATABASE_URL=postgresql+psycopg:///labuse_test PYTHONPATH=src <venv>/python -m pytest`.
Mesures base réelle : `LABUSE_DATABASE_URL=postgresql+psycopg:///labuse`.
