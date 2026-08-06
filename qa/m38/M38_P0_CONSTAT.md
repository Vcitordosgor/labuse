# M38 — Phase 0 : SOURCE des dépôts (vérifiée sur pièces) + écart mesuré — DÉCISION Vic

**Branche `m38-permis-deposes` · base main 14ae2116 · LECTURE SEULE** (téléchargements
d'échantillons réels autorisés par le mandat Phase 0.1 ; aucune écriture DB, aucun tier touché).

> ⚠ **DÉCOUVERTE qui reformule la prémisse — je m'arrête pour ton arbitrage** (règle « ne
> présume pas, rapporte et attends »). La donnée existe et est exploitable au parcellaire, mais
> PAS celle que la prémisse supposait. Détail ci-dessous.

## 1 · Source vérifiée SUR PIÈCES (pas sur la doc)

Téléchargement live de l'API Dido (SDES/Sitadel3), dataset **`6513f0189d7d312c80ec5b5b`**
« Liste des permis de construire et autres autorisations d'urbanisme » — la source DÉJÀ
ingérée (`permits_sdes.py`). Métadonnées live : **licence LO (fr-lo)**, **MAJ 2026-07-28**
(mensuelle), 4 datafiles (logements / locaux / PA / PD). Header CSV réel inspecté colonne par
colonne.

**Le champ de dépôt EXISTE et est exact** : **`DR_DEPOT`** = date réelle de dépôt (ex.
`2025-09-22`, `2014-05-06`) — pas seulement l'année (`AN_DEPOT`). Mesuré sur le datafile
logements (40 751 lignes 974) :

| Grandeur | Valeur |
|---|---|
| `DR_DEPOT` rempli | **99,9 %** (40 694/40 751) |
| Réf. cadastrale (parcelle) | **99,3 %** (SEC/NUM_CADASTRE, jusqu'à 3 paires) |
| `DR_DEPOT` présent sur les 4 datafiles | oui (logements, locaux, PA, PD) |

→ **Le dépôt est disponible à granularité PARCELLE + date exacte.** La condition de STOP du
mandat (« aucune source à granularité ≥ commune ») n'est PAS atteinte : c'est mieux, on a le
parcellaire.

## 2 · LA nuance qui reformule le mandat (constater avant présumer)

Le dataset Dido est **AUTORISATIONS uniquement** — vérifié sur pièces : sur 40 751 lignes,
**0 sans `DATE_REELLE_AUTORISATION`** ; `ETAT_DAU` ∈ {2 autorisé, 4, 5 commencé, 6 terminé},
**aucun état « refusé » ni « en instance »**. Métadonnées : les 4 datafiles sont tous des
« autorisations », **aucun datafile « déposés » / « en instance »**.

**Conséquence** : la donnée « permis déposés » disponible en open data = **la date de dépôt des
permis qui ont FINI par être autorisés**. Les permis **refusés / abandonnés / encore en
instance ne sont PAS publiés** — ils n'entrent jamais dans le dataset.

Donc la prémisse du mandat se scinde en deux biais, dont UN SEUL est corrigeable :
- ✅ **« un permis autorisé arrive des mois après le dépôt »** → CORRIGEABLE : on connaît la
  date de dépôt exacte (`DR_DEPOT`), on peut redater l'activité sur le dépôt.
- ❌ **« les refus/abandons sont invisibles »** → NON corrigeable depuis l'open data : Sitadel
  ne publie jamais les permis non-aboutis. On ne fabrique pas une donnée qui n'existe pas.

## 3 · Écart autorisés vs déposés — MESURÉ (datafile logements)

- **Délai dépôt → autorisation : médiane 276 jours (~9 mois)** · p10 122 j · p90 430 j
  (n = 33 765 délais valides). C'est exactement le retard décrit par le mandat.
- Volumes par année de dépôt vs autorisation (2026 partiel) :

| Année | déposés (DR_DEPOT) | autorisés (DATE_REELLE_AUT) |
|---|---:|---:|
| 2023 | 2 479 | 2 687 |
| 2024 | 2 083 | 2 070 |
| 2025 | 2 207 | 2 158 |
| 2026 | 346 (partiel) | 1 002 |

⚠ Lecture honnête du « 2026 : 346 déposés / 1 002 autorisés » : le dataset étant
autorisés-seuls, un permis déposé en 2026 n'y apparaît QUE lorsqu'il est autorisé. Les 346 sont
les dépôts 2026 déjà autorisés (les plus rapides, p10 ~4 mois) ; les dépôts 2026 encore en
instance sont **absents**. Donc `DR_DEPOT` donne une **datation historique plus juste** (et une
visibilité anticipée pour les permis à instruction rapide), mais **pas** la vision temps-réel
des dépôts en cours.

## 4 · Ce qui est actuellement ingéré (à ne pas re-supposer)

`sitadel_permits` (50 043 lignes : PC 45 742 · DP 2 391 · PD 1 108 · PA 802 ; 39 294
géolocalisées, 50 043 avec idu_codes). La colonne `date` = **`DATE_REELLE_AUTORISATION`**
(`permits_sdes._date_autorisation`). **`DR_DEPOT` N'EST PAS capté** (ni colonne, ni raw) — la
donnée est pourtant déjà téléchargée à chaque refresh (même dataset). L'ajouter = étendre le
SELECT + stocker, sans nouvelle source.

## 5 · Ce que M38 PEUT livrer (périmètre réel) vs la prémisse

| Objectif mandat | Faisable ? |
|---|---|
| Ingérer les permis déposés | ✅ via `DR_DEPOT` (date de dépôt des permis autorisés), parcelle |
| Exposer en fiche « dépôts récents sur le secteur » | ✅ (compte par période, datation dépôt) |
| Mesurer le délai dépôt→autorisation | ✅ (276 j médian) |
| Redater la « dynamique constructive » sur le dépôt | ✅ (Phase 3, à blanc) |
| Voir les refus / abandons / dépôts en instance | ❌ inexistant en open data |
| Vision temps-réel des dépôts non encore autorisés | ❌ (dataset autorisés-seuls) |

## DÉCISION demandée (avant Phase 1)

Le livrable réel = **« redater sur le dépôt + exposer l'activité de dépôt »**, PAS « ajouter les
permis refusés/en instance » (impossible). C'est un rétrécissement matériel de la prémisse.

1. **Je continue sur ce périmètre réel** (ingérer `DR_DEPOT`, exposer les dépôts par période au
   secteur/parcelle avec étiquette de granularité, mesurer le décalage de la dynamique
   constructive à blanc) — ma recommandation, la donnée est solide et parcellaire ?
2. Ou tu juges que sans les refus/en-instance l'intérêt est trop faible et tu **réorientes**
   (autre source à explorer — portails régionaux, DEAL — ou abandon) ?
3. Précision utile : veux-tu que le bloc fiche compte **tous les dépôts** (toutes années) ou
   seulement une **fenêtre récente** (ex. 24-36 mois), et au niveau **parcelle** (réf. cadastrale
   exacte) ou **secteur** (préfixe IDU 10) ?
