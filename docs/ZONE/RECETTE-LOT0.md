# ZONE-RECETTE · LOT 0 — MESURE (rendu avant de coder)

Trois mesures sur la base **dev** (`labuse`, parcelles/données réelles). Elles décident du reste.

## M1 — Concurrents : pourquoi 0

- **Chaîne** : bloc « CONCURRENTS DANS LA ZONE » servi par `POST /outils/etude-zone` →
  `zone.concurrents_zone()` → table **`sirene_etablissements`** filtrée par NAF dans la zone.
- **Compte réel en base** :

  | Requête | Lignes |
  |---|---|
  | `sirene_etablissements` (total) | **0** |
  | NAF `1071C` (total / actif / Saint-Paul) | 0 / 0 / 0 |

- **Les 4 boulangeries** (Le Pain Frotté, L'Île aux Pains ×2, The Bread Workshop) : **0 en base** —
  non parce qu'elles n'existent pas, mais parce que **la table est vide**.
- **Verdict : (a) source NON INGÉRÉE.** Le CLI `ingest-sirene-etab` existe (mandat Étude de zone)
  mais n'a **jamais été exécuté** sur la base dev. Ce n'est ni un mapping d'activité muet (le NAF
  `1071C` est bien la clé normalisée attendue), ni une géométrie fausse, ni un filtre trop strict :
  il n'y a **rien à filtrer**. Le « 0 » affiché est un **faux zéro** → c'est précisément ce que le
  LOT A doit corriger (dire « non couvert », pas « aucun établissement »).

## M2 — Zone : la géométrie réellement mesurée

Le mystère « 5 min voiture = 715 hab **<** 10 min à pied = 11 131 hab » (impossible) ne vient PAS de
l'isochrone. Mesures directes depuis un point côtier de Saint-Paul (55.2707, −21.0096) :

| Périmètre calculé | Surface | Habitants |
|---|---|---|
| Isochrone **5 min voiture** | **1,71 km²** | 4 298 |
| Isochrone **10 min à pied** | **0,675 km²** | 1 808 |
| **Polygone** Saint-Paul côtier (repère, 20,7 km²) | 20,72 km² | 20 558 |

- **Les isochrones brutes sont COHÉRENTES** (voiture ⊃ pied, 1,71 > 0,675 km²). Le profil de routage
  est correct : `voiture`→`car`, `pied`→`pedestrian`.
- **11 131 hab est une échelle de POLYGONE** (plusieurs km²), pas d'une marche de 10 min. Un polygone
  ~2× plus petit que mon repère (20,7 km² → 20 558 hab) donne ~11 000 hab.
- **Le polygone dessiné EST utilisé** : `EtudeZone.tsx` l.60 envoie `body.geom` dès que
  `drawnZone.length ≥ 3` ; le backend calcule alors **sur le polygone** (mode/minutes ignorés pour la
  géométrie — il n'est ni intersecté ni remplacé). MAIS deux défauts le rendent incohérent à l'usage :
  1. **L'en-tête MENT** (l.159 : « La zone à {minutes} min {mode} ») même quand la mesure porte sur
     un polygone → **LOT D**.
  2. **La capture du tracé est instable** (double-clic déplace un sommet au lieu de fermer → le
     polygone n'est pas/mal committé dans `useApp.zone`) → selon l'état, le tool retombe sur
     l'isochrone du point → **LOT E**.
  → La paire « 715 / 11 131 » = **deux géométries différentes** (isochrone d'un point vs polygone),
  toutes deux étiquetées par mode/minutes. Correctifs = LOT C (entrées exclusives) + D (libellé) +
  E (validation du tracé) + F (cycle de vie).

## M3 — Filosofi / SIRENE / MOBPRO : état d'ingestion

| Source | Lignes en base | État |
|---|---|---|
| Filosofi carreaux 200 m | **14 773** | **Sourcé** |
| BPE (équipements) | 35 546 | **Sourcé** |
| MOBPRO (emplois commune) | **0** | **NON COUVERT** |
| SIRENE établissements | **0** | **NON COUVERT** |

Pour chaque chiffre affiché par l'outil :

| Chiffre | Statut |
|---|---|
| Habitants · ménages · % < 25 ans | **Sourcé** (Filosofi 2021) |
| Revenu médian / an | **Estimé** (Filosofi lissé — doctrine) |
| Actifs y travaillent | **NON COUVERT** (MOBPRO vide) → aujourd'hui « — » muet, à corriger (LOT A) |
| Équipements & commerces proches | **Sourcé** (BPE 2025) ; temps via isochrone IGN |
| Concurrents (par activité) | **NON COUVERT** (SIRENE vide) → aujourd'hui faux « 0 » (LOT A) |
| Marché de la zone (ventes DVF, médian €/m², permis) | **Sourcé** là où la table porte des données ; annonces Radar selon l'état de `pige_biens` |

## Ce que LOT 0 impose au reste

- **LOT A est indispensable** : SIRENE et MOBPRO non ingérés → l'outil doit dire **« non couvert »**
  (pas « 0 », pas « — »). Distinguer *source servie + 0* / *source non ingérée* / *requête en erreur*.
- L'ingestion réelle de SIRENE/MOBPRO est un acte d'exploitation (hors code) : ce mandat rend l'outil
  **honnête** en leur absence ; il ne les ingère pas.
