# A0-5 — Voies privées (E2) : détection sourcée + remesure de couverture

Lecture via le builder complet (`scripts/gabarit_a0_5_mesure.py`) sur la **même cohorte de 170
parcelles** que GABARIT-3/4 (relue depuis `captures/gabarit-3/couverture-synthese.csv`, reproductible),
EPSG:2975. Seuil GABARIT-4 déjà atteint (≥ 75 %) ; GABARIT-5 vise le **lot voie privée (E2)** et
**0 faux**.

## Résultat — avant / après GABARIT-5

| | GABARIT-4 | **GABARIT-5** |
|---|---|---|
| Servies | 135 / 170 (79 %) | **143 / 170 (84 %)** |
| FAUX servis (arêtes « road ») | 0 | **0** |
| Régressions (servie → bloquée) | — | **0** |

**+8 parcelles servies, 0 faux, 0 régression.**

## Le lot E2 (12 ex-« enclave / voie privée » de GABARIT-4)

Le crible grossier de GABARIT-3/4 (`_has_chemin_neighbor`, compacité < 3) confondait E1 (enclave sans
accès cadastré) et E2 (accès par une **parcelle de voie privée**). GABARIT-5 le remplace par les
**trois critères obligatoires** (aucun seul ne suffit) — sans bâti, allongée (L/l ≥ 5) **et** étroite
(largeur ≤ 6 m : un chemin, pas un lot allongé), raccordée au réseau BD TOPO à une extrémité **sans**
être elle-même une voie BD TOPO. Résultat sur les 12 :

| Sort | n | parcelles |
|---|---|---|
| **Bloc E2** (voie privée détectée, citation absente → motif honnête) | 4 | CY0812, DE1754, AS0592, AM1059 |
| **Servie E1** (voisin élancé non qualifiant → vraie enclave, séparatives seules) | 8 | CX0805, EN3783, AT0577, HB0374, BH2024, CZ0540, EM0661, DH0088 |
| Servie par citation « voies privées » | 0 | — (aucune zone calibrée ne la vise, cf. tableau communes) |

Le gain +8 vient de ces 8 ex-E2 reclassées **E1** (leur voisin élancé n'est pas une voie privée
raccordée : L/l < 5, ou largeur > 6 m, ou non raccordé au réseau). Les 4 vraies E2 restent bloquées
avec le **bon motif** (« desservie par une voie privée : le règlement ne précise pas le recul »).

## Le width-cap a évité une régression

Sans plafond de largeur, la détection prenait des **lots allongés** (ex. CH0196 — parcelle de la
recette E1 de GABARIT-3 — bordée de deux parcelles de 631 / 789 m², ~10 m de large) pour des voies
privées et la bloquait à tort. Le plafond largeur ≤ 6 m sépare nettement les chemins (3–4 m) des lots
(≥ 10 m) : **CH0196 reste servie** (aucune régression), les vrais chemins d'accès restent détectés.

## Causes de blocage restantes (27)

| Cause | n |
|---|---|
| PLU : zone non calibrée | 10 |
| limite non qualifiée (emprise non couverte) | 9 |
| E2 : voie privée (citation absente) | 4 |
| recul non validé | 3 |
| PLU : hauteur non validée | 1 |

## Verdict

**84 % ≥ 75 %, 0 faux, 0 régression.** Le mécanisme « voie privée par citation » est implanté et
prouvé (tests unitaires) mais **inert sur la calibration actuelle** — aucune zone ne vise les voies
privées avec un recul chiffré (cf. `RAPPORT-GABARIT-5.md`, tableau communes) : parallèle exact du
mécanisme « emprises publiques » de GABARIT-3. Il servira automatiquement dès qu'une calibration
gravera un recul de voie privée validé.
