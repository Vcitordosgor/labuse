# ECARTS-2 — CHASSE-INVARIANTS-2

> Une ligne par **violation confirmée** (revérifiée à la main sur 3 exemples avant d'entrer ici).
> Audit LECTURE SEULE — aucun correctif appliqué. Base servie q_v18 / run_seq 15, 434 582 parcelles.
> Gravité : **FAUX-CLIENT** (un chiffre/texte faux atteint le client) · **INCOHERENT** (deux surfaces se
> contredisent, ou une dérivée non revalidée) · **ROBUSTESSE** (plantage/NaN/anomalie source isolée).

**4 violations confirmées, toutes trouvées par F1 (schéma). 3 partagent une MÊME racine** (hauteurs
LiDAR servies sans borne). Les familles F2 (registre), F3 (métamorphique), F4 (PLU), F5 (API), F6 (zones
muettes) sont **au vert** — 0 violation confirmée (détail et chasses vides prouvées dans RAPPORT-2.md).

| # | gravité | règle | exemples (3) | attendu | obtenu | cause | fichier:ligne |
|---|---------|-------|--------------|---------|--------|-------|---------------|
| E2-01 | **FAUX-CLIENT** | `F1.batiment_hauteur_lidar.egout_m.non_negatif` | `97413000DC1454` egout=-15,7 · `97411000AB0300` -15,0 · `97418000BC0364` -10,6 (tous `methode='dalle'`) | hauteur d'égout ≥ 0 | **1 218** lignes `egout_m < 0` | LiDAR `MNS−MNT` négatif quand le modèle de sol passe au-dessus de l'emprise bâtie (remblai/débord/glitch vertical), `methode='dalle'` ; servie telle quelle | `src/labuse/api/app.py:6424` (`"hauteur_egout_lidar_m"`, aucun clamp) |
| E2-02 | **FAUX-CLIENT** | `F1.batiment_hauteur_lidar.faitage_m.non_negatif` | `97413000DC1454` faîtage=-11,6 · `97413000DD1550` -4,8 · `97421000AR0022` -1,8 (parcelles vivantes) | hauteur de faîtage ≥ 0 | **44** lignes `faitage_m < 0` (parcelles vivantes) | même artefact LiDAR « dalle » ; `faitage_m` = hauteur du bâti existant | `src/labuse/api/app.py:6423` **et** `src/labuse/api/gabarit.py:43-63` (`hauteur_m = round(faitage_m,1)`, non clampé — hauteur de bâti NÉGATIVE rendue au client dans l'outil Gabarit) |
| E2-03 | **FAUX-CLIENT** | `F1.batiment_hauteur_lidar.faitage_m.hauteur_max300` | `97418000AZ0417` faîtage=53 401,6 · `97418000AZ0128` 53 401,6 (les 2 seules ; `n_cellules=7240`, `code_mission='23LHDREUNION'`, `methode='dalle'`) | faîtage ≤ 300 m (plafond physique très large ; plus haut bâti de l'île ~60 m) | **2** lignes à **53 401,6 m** (53 km) | cellule LiDAR mal géoréférencée (altitude ~53 km) face à un MNT près du niveau de la mer ; `hauteur_bdtopo_m`=6,1 m pour les mêmes bâtis = preuve de l'artefact ; servie telle quelle (fiche + Gabarit, sans borne) | `src/labuse/api/app.py:6423`, `src/labuse/api/gabarit.py:63` |
| E2-04 | ROBUSTESSE | `F1.dpe_records.annee_construction.annee_bornee` | `2568E0569173B` (maison, parcelle `97418000AW0434`) `annee_construction=1761` — unique | année ∈ [1800, 2026] | **1** ligne à **1761** | **anomalie SOURCE ADEME** (saisie DPE) — une maison « 1761 » à La Réunion est invraisemblable ; servie sur la fiche DPE telle que fournie. Pas un bug de l'app : saisie amont (comme N-01..N-05 vague 1) | donnée amont `dpe_records` (ADEME) |

## Racine unique E2-01/02/03 — « hauteur LiDAR servie sans borne »
Les trois premiers écarts sont le **même défaut** : les hauteurs LiDAR (`faitage_m`/`egout_m`, table
`batiment_hauteur_lidar`) sont servies **sans borne basse ni haute** alors que `methode='dalle'` produit
des valeurs négatives (terrain au-dessus du bâti) et, dans 2 cas, une cellule aberrante à 53 km. Elles
alimentent la fiche parcelle (`hauteur_faitage_lidar_m`, `hauteur_egout_lidar_m`) **ET** l'outil Gabarit
(hauteur du bâti existant, `round(faitage_m,1)`). Un garde-fou unique au service —
`GREATEST(0, LEAST(faitage_m, 300))`, ou un repli sur `hauteur_bdtopo_m` quand `methode='dalle'` rend un
négatif — ferme les trois d'un coup. **Geste pour Vic (hors périmètre de cet audit lecture seule).**

## Non retenus (faux-mordants écartés AVANT de tourner — traçabilité)
Pour mémoire, chaque famille a écarté des règles candidates sans sens (détail dans FN.md) :
aucune parcelle A/N à SDP>0 n'est un bug (assiette clippée, adjugé Vic 24/09) ; `SDP = emprise×niveaux`
n'est qu'une **borne supérieure** (CES/pleine terre rabotent) ; taux d'imposition communaux non bornés à
100 ; `taux_emprise_pct`/`pct_potentiel` de base dépassent 100 légitimement (clampés au rendu, vague-1
E-01) ; pages PLU citées vérifiées contre `meta.pages_total` (extrait `plu_reglement_extrait` épars) ;
centroïdes « hors commune » ≤ 75 m = artefacts de la geojson simplifiée, pas des misattributions.
