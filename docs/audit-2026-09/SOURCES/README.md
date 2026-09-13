# SOURCES-AUDIT-1 — chaque source, à son plein potentiel ou pas

*Audit en lecture seule des 116 sources du catalogue LABUSE + 15 candidates. Branche
`audit/sources-1`. Rien n'est ingéré, rien n'est mergé, rien n'est corrigé en passant.*

## Le dossier

| Fichier | Contenu |
|---|---|
| **`SOURCES-AUDIT.md`** | Les 116 par famille, **verdict en tête de ligne**, lisible d'un bout à l'autre. |
| **`SOURCES-AUDIT.csv`** | Une ligne par source, **toutes les colonnes** (identité, couverture, complétude, visibilité, potentiel, verdict). |
| **`fiches/<id>.md`** | Une fiche par source (116). |
| **`LOT0-INVENTAIRE.md`** | S1 compteur page vs base · S2 les 4 retraits (**tous en attente**) · S3 doublons · S4 familles. |
| **`LOT2-3-4.md`** | Les 10 déclarées · les 5 manuelles · les partielles qui se disent entières. |
| **`CANDIDATES.md`** | Les 15 candidates : GO / ATTENTION / NON, avec la raison. |
| **`CLICKTEST.md`** | Test client **au vrai navigateur** (:8032/:5200) : 30 sources, chemin cliqué, nb de clics, `i`, et les **INVISIBLES fonctionnelles**. |
| **`REPARATIONS.md`** | Le tableau des verdicts, les principes non tenus, le **plan d'ordre**, le flou restant. |
| **`captures/`** | Captures navigateur réelles (accueil, COUCHES, Outils, page Sources, fiche, outils). |
| **`DEMANDE-REGION-EPCI.md`** | Rattachement du lot 2 au courrier prêt (`docs/CIRCUIT/DEMANDE-REGION-EPCI.md`). |
| **`scripts/audit_sources/`** | Les scripts qui génèrent tout ça (**rejouables**). |

## Rejouer

```bash
cd docs/audit-2026-09/SOURCES/scripts
python -m audit_sources.generate      # régénère CSV + fiches + SOURCES-AUDIT.md
```

Les scripts n'importent PAS le paquet `labuse` (deps lourdes) : ils exécutent en isolation les
deux fichiers de constantes (`circuit_etats.py`, `registre/tables.py`) et lisent la base. La
**visibilité** de chaque source est dérivée du graphe du registre
(`réservoir → chiffre → robinet`), pas saisie à la main. Les champs qualitatifs (potentiel,
champs non pris, verdict nuancé) viennent de `curation.py`, adossés au code, marqués
« non vérifié » quand le producteur n'a pas pu être consulté (aucun scraping).

## Les verdicts, en un coup d'œil (sur 116)

62 PLEINE · 24 PARTIELLE (14 couverture + 10 champs) · 4 SERVIE HORS REGISTRE ·
10 À DEMANDER · 5 MANUELLE · 5 RETIRÉE · 3 ALIAS · 3 HUB · **0 à retirer**.

> ⚠ « 0 invisible » (verdict CSV, dérivé du registre) est un **artefact de méthode** : le graphe
> réservoir→robinet ne peut PAS produire d'invisible. Le **test navigateur** (`CLICKTEST.md`)
> sépare *transparence* (les 95 sur la page /sources en 2 clics, avec source+licence+fraîcheur)
> de l'**usage fonctionnel**, et trouve **≥ 5 INVISIBLES fonctionnelles** — donnée n'atteignant
> aucune surface parcelle/carte/outil : DVF Région (119), LOVAC (141), Fichiers fonciers (27),
> DV3F (142), et **DPE (37) en pratique** (17 records = fiche vide malgré « à jour »).

## Les trois faits saillants

1. **Les 4 retraits « décidés » sont tous en attente** : BD ORTHO IRC, Office de l'eau,
   Parkings APER et DINUM sont **lus en direct** et servent une valeur (Solaire, Réseaux,
   Propriétaire). La règle « si un moteur les lit, le retrait attend » s'applique aux quatre.
   Aucune écriture en base. (LOT0 §S2)
2. **La couche « OCS GE » ment sur son étiquette** : l'UI dit « OCS GE (IGN) », la base sert
   **BD CARTO V5** (proxy grossier). La vraie donnée d'artificialisation est une candidate GO.
   (CANDIDATES #2)
3. **Le partiel qui se dit entier** : le **DPE** est « connecté » avec **17 records** (ingestion
   quasi-vide) ; le **LiDAR** couvre 70 % en hauteur (303 452 parcelles) mais ~0 % en verdict de
   toiture (27), et sa hauteur est créditée à BD TOPO au lieu de LiDAR. Le modèle a besoin d'un
   état de couverture, pas d'un statut binaire. (LOT2-3-4 §Lot 4)

*Note (2ᵉ passe) : les comptes de couverture sont mesurés sur la base servie
`postgresql://openclaw@localhost:5432/labuse` (431 663 parcelles). La 1ʳᵉ passe avait
sous-compté le LiDAR (mauvaise table `toiture_lidar` héritée de `RESERVOIR_TABLES`) et qualifié
à tort la base de « non représentative ». Corrigé.*
