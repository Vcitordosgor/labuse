# AUDIT M86-B — Brancher l'assainissement (ANC / tout-à-l'égout) · Phase 1 diagnostic

> **Restitution.** La donnée EXISTE, elle n'est PAS servie à la fiche écran. Réglementaire (`zone_anc`) :
> **57 712 / 431 663 parcelles (13,4 %)**, 4 communes seulement (St-Denis, St-Paul, Le Port,
> L'Étang-Salé) — collectif 47 803, anc 9 909. Estimé (`proba_anc`, 5-95 %, seuil servi 70) : 278 685
> parcelles ; **152 978 parcelles n'ont AUCUNE ligne**. **Un `zone_anc` NULL = pas de zonage disponible,
> JAMAIS « collectif par défaut ».** La chaîne casse en **aval du calcul** : `parcel_anc` est bien peuplé,
> mais **aucune route API servie ne l'expose à la fiche écran** ; seul le PDF lit `zone_anc`, et **cassé**
> (`bool()` → indistinct collectif/anc). Accord réglementaire↔estimation : **76,3 %** — MAIS l'estimation
> **rate 69 % des ANC réels** (30,6 % de rappel), elle sous-détecte la contrainte. Mesuré le 2026-08-14.
> **STOP** : Vic arbitre (servir l'estimation malgré le rappel faible ? seuil ? emplacement).

---

## 1. Couverture réglementaire (`zone_anc`)
- **57 712 / 431 663 parcelles (13,4 %)** ont `zone_anc` renseigné, toutes `source='zonage_officiel'`
  (couches d'assainissement GPU, couverture SIG **4/24 communes**). Valeurs : **collectif 47 803**,
  **anc 9 909**.
- Par commune : Saint-Denis 24 119 · Saint-Paul 21 737 · Le Port 6 960 · L'Étang-Salé 4 896. **Les 20
  autres communes : 0 zonage réglementaire.**
- **Le sens du NULL (le cœur du sujet)** : `zone_anc` NULL = **zonage réglementaire NON disponible**
  (SIG absent pour cette commune), PAS « collectif ». Les 47 803 « collectif » sont un **collectif
  EXPLICITE** issu du zonage officiel — jamais un défaut. Donc **373 951 parcelles** sont « réglementaire
  inconnu », à ne surtout pas afficher comme raccordées.

## 2. Couverture estimée (`proba_anc`)
- **278 685 parcelles** ont `proba_anc` (entier 5-95, médiane 65). Stocké dans **`parcel_anc.proba_anc`**
  (table dérivée STATIQUE, **non run-scopée** — `idu` PK, `source`, `zone_anc`, `proba_anc`, `updated_at`).
- Ne couvre que les **parcelles bâties** (`parcel_residuel_bati.emprise_batie_m2 > seuil`). **152 978
  parcelles** (non bâties / hors maille) n'ont **aucune** ligne `parcel_anc` → ni Sourcé ni Estimé =
  **Absent**.

## 3. Où casse la chaîne
Trajet : `anc.py compute_proba` (ingestion) → `parcel_anc` (table) → **∅ point de calcul servi** →
`flash/data.py:483` (PDF pré-dossier, lit `zone_anc`) → front `ViabilisationBlock` (coût raccordement, PAS le zonage).
- Le **calcul écrit** bien `zone_anc`/`proba_anc` dans `parcel_anc`. ✔
- **Le maillon manquant = la ROUTE API → le FRONT.** AUCUN endpoint servi (`api/app.py /parcels/{idu}`,
  `api/modules.py`, `faisabilite/`) ne lit `parcel_anc` pour la fiche écran. Le seul lecteur est le
  **PDF** (`flash/data.py`), et il est **CASSÉ** : `out["anc"] = {"zone_anc": bool(r["zone_anc"])}` →
  `bool('collectif')` = `bool('anc')` = `True` → il ne distingue PAS collectif d'ANC (donc inutilisable).
- Le front `ViabilisationBlock` affiche `cout_raccordement.assainissement` (une estimation de COÛT), pas
  le statut réglementaire collectif/ANC. → **Cas 2 (+3) du mandat** : le champ n'est ni exposé par l'API
  servie, ni affiché au front. Le calcul est là ; il n'est jamais remonté.

## 4. Recouvrement réglementaire ↔ estimation (accord)
Sur les 57 712 parcelles ayant les DEUX, au seuil servi **70** :

| zone_anc réel | total | estimé ANC (proba≥70) | estimé collectif (proba<70) |
|---|---|---|---|
| **anc** | 9 909 | **3 031 (30,6 %)** ✔ | 6 878 (69,4 %) ✘ manqués |
| **collectif** | 47 803 | 6 779 (14,2 %) ✘ | 41 024 (85,8 %) ✔ |

**Accord global : 76,3 %.** MAIS asymétrie grave : l'estimation **ne rappelle que 30,6 % des ANC réels**
(elle en manque 69 %). Servir « proba<70 → probablement collectif » **rassurerait à tort la majorité des
vrais ANC** — exactement le cas où la contrainte compte (épandage + étude de sol). **Conséquence pour le
service** : l'estimation est un signal FAIBLE, jamais un substitut du réglementaire, et son sens « bas =
collectif » est trompeur. À afficher, au mieux, comme « estimation statistique de secteur », pas comme un
verdict parcellaire.

## 5. Fiabilité de l'estimation (méthode exacte)
`anc.compute_proba` : **taux de non-raccordement de la maille IRIS** (`anc_maille_taux`, agrégé de
**INSEE RP2022 EGOUL**) via `ST_Contains(iris_insee)` ; repli **maille commune** ; **+ bonus rural**
(commune avec PLU ∧ parcelle > `dist` de toute zone U) ; borné **[5, 95]**. Seuil de bascule servi = **70**
(`config/anc_vegetation.yaml:43`). **Maille IRIS/commune, jamais parcellaire** → d'où le rappel faible sur
une réalité qui, elle, est décidée à la parcelle. Méthode connue et documentée (donc *serviable* au sens
doctrinal), mais **grossière** — à marquer Estimé sans ambiguïté.

---

## Phase 3 — questions ouvertes (tranchées ici)

**1. Contours IRIS est-il lu ailleurs que par la chaîne ANC ?** → **NON.** `iris_insee` n'est lu que par
`anc.compute_proba`. Filosofi/Attractivité utilise les **carreaux 200 m** (`filosofi_carreaux_200m`), PAS
l'IRIS. Conséquence : **IRIS (et EGOUL, qui alimente `anc_maille_taux`) NE SONT PAS morts en soi — ils le
sont tant que `proba_anc` n'est pas servi.** Si la Phase 2 sert l'Estimé, **IRIS + INSEE RP2022 (EGOUL)
SORTENT de la liste MORTE de M86.** (Office de l'eau, lui, reste à part — cf. ci-dessous.)

**2. Le YAML du radar PLU a-t-il été construit à partir de Sudocuh ?** → **OUI.** `config/veille_plu.yaml`
l'écrit : « Squelette = **Sudocuh** (data.gouv.fr) ; Chair = ce registre curaté à la main ». Chaque entrée
cite « Sudocuh 31/12/2024 » en source. → **Sudocuh est une source RÉELLE mais INDIRECTE** (curée
manuellement dans le YAML servi par le radar). **Statut « curée manuellement », PAS de retrait.** Corrige
le verdict MORTE de M86 : Sudocuh alimente bien un point servi, par curation.

**Office de l'eau (nuance) :** `calage_office_eau` LIT `anc_maille_taux` et écrit `parcel_signals`
(contrôle croisé QA) ; il ne CONSTRUIT pas `anc_maille_taux` (bâti par EGOUL) et ne nourrit pas
`proba_anc`. Son unique sortie servie (`/signals`) a été retirée. → **reste MORTE** même après branchement
(contrôle QA, pas une donnée servie). Seul de la chaîne ANC.

## Bilan pour l'arbitrage (Phase 2 conditionnée)
- **Sourcé** (zone_anc) : prêt, 4 communes, à exposer + afficher (collectif/ANC + commune + date amont).
- **Estimé** (proba_anc) : disponible mais **rappel ANC 30 %** — Vic tranche s'il faut le servir, et
  comment le cadrer (« estimation de secteur », jamais « probablement collectif »). Seuil 70 modifiable.
- **Absent** : 152 978 parcelles sans ligne → à écrire « inconnu », jamais « collectif ».
- **Effet de bord M86** : brancher l'Estimé **ressuscite IRIS + EGOUL** (sortent de MORTE) ; **Sudocuh
  n'était pas morte** (source indirecte curée) ; **Office de l'eau reste morte** (QA).
- **Un seul endroit** : le champ servi sera calculé par un **helper partagé** (fiche écran + PDF + export),
  jamais recalculé trois fois. Emplacement retenu : **tiroir Constructibilité** (contrainte, pas confort).
