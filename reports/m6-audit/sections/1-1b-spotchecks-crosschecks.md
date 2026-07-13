# M6 §1.1b — Spot-checks externes, outliers DVF, cohérence inter-couches

Audit LECTURE SEULE du 13/07/2026 (branche `audit/grand-check`). Base `postgresql://openclaw@localhost:5432/labuse`.
Complète `reports/m51-unification/FRAICHEUR.md` (fraîcheur) et `AUDIT-COUCHES.md` (couches/témoins) — rien n'est refait, tout est approfondi.
Aucune écriture en base (tables temporaires de session uniquement), aucun code produit modifié.

---

## BLOC A — Spot-checks contre les sources officielles

Méthode : valeurs tirées de la base (SELECT), re-requêtées **en ligne le 13/07/2026** sur l'API/portail officiel du producteur, comparaison champ à champ.

### A-PVGIS (parcel_solar / solar_grid)

La chaîne solaire stocke deux niveaux : `solar_grid` = points de grille 400 m interrogés directement sur PVcalc **v5_3** (params exacts retrouvés dans `config/habitat_solaire.yaml` + `src/labuse/ingestion/solaire_pvgis.py` : `peakpower=1, loss=14, angle=15, aspect=180 (plein nord), usehorizon=1`), puis `parcel_solar.prod_spec_kwh_kwc` = **interpolation IDW (4 voisins)** de la grille. Le spot-check porte donc sur les deux niveaux. (Limite côtière SARAH3 : connue et documentée, non ré-investiguée.)

**Niveau grille (comparaison exacte attendue) — 3 points re-requêtés sur `https://re.jrc.ec.europa.eu/api/v5_3/PVcalc` :**

| solar_grid id | lon / lat | Base E_y (kWh/kWc/an) | API E_y | Écart | Base H(i)_y | API H(i)_y | Écart | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 55.21576 / −21.04532 | 1396,83 | 1396,83 | **0,00** | 1831,11 | 1831,11 | 0,00 | **RACCORD EXACT** |
| 3477 | 55.39776 / −21.30005 | 1603,52 | 1603,52 | **0,00** | 2095,44 | 2095,44 | 0,00 | **RACCORD EXACT** |
| 6833 | 55.50036 / −21.06613 | 759,92 | 759,92 | **0,00** | 989,48 | 989,48 | 0,00 | **RACCORD EXACT** |

Base de rayonnement confirmée par l'API : `PVGIS-SARAH3`. Le point 6833 (759,92, fond de vallée côté Est) confirme que l'horizon topographique (`usehorizon=1`) est bien dans la donnée.

**Niveau parcelle (valeur = IDW, tolérance attendue ≈ ±2 % à 400 m de pas) — 3 parcelles, API interrogée au centroïde :**

| IDU | Commune | Base (IDW) | API au centroïde | Écart | Verdict |
|---|---|---|---|---|---|
| 97415000BN1074 | Saint-Paul | 1341,57 | 1341,58 | −0,00 % | **RACCORD** |
| 97410000BD0634 | Saint-Benoît | 1481,90 | 1495,95 | −0,94 % | **RACCORD** (erreur d'interpolation, dans la tolérance) |
| 97413000CH0350 | Saint-Leu | 1450,70 | 1448,67 | +0,14 % | **RACCORD** |

**Verdict PVGIS : 6/6 raccord.** Tolérance documentée : 0 % au grain grille (donnée brute conservée fidèlement), < ±1 % observé au grain parcelle (IDW). Aucun écart anormal.

### A-DVF (dvf_mutations_parcelle / dvf_mutations)

Source de vérification : distribution officielle géo-DVF Etalab, fichier `https://files.data.gouv.fr/geo-dvf/latest/csv/2025/communes/974/97411.csv` téléchargé le 13/07/2026 (app.dvf.etalab.gouv.fr consomme la même distribution). 3 mutations 2025 tirées au hasard :

| id_mutation | Champ | Base (`dvf_mutations_parcelle`) | Source officielle | Écart |
|---|---|---|---|---|
| 2025-1268435 | date / valeur / parcelle / terrain | 13/05/2025 · 165 000 € · 97411000IS0679 · 330 m² sols | idem | **0** |
| 2025-1270912 | 2 lignes (Appartement 64 m² + Dépendance) · 102 000 € · 26/09/2025 · BD0745 | idem (2 lignes, lots 27 et 120) | **0** (les nos de lot ne sont pas conservés en base — perte documentée, pas un écart) |
| 2025-1271718 | 14 lignes · 1 160 000 € · 07/11/2025 · 11 parcelles EP (dont EP0237 ×4) | idem 14 lignes | **0** |

**Verdict : `dvf_mutations_parcelle` est fidèle ligne à ligne à la source (3/3, 17 lignes comparées).**
⚠ En revanche la table agrégée `dvf_mutations` (celle du Baromètre) introduit des artefacts **de fabrication interne** sur ces mêmes mutations — démontré au BLOC B : pour 2025-1271718 elle stocke `surface_reelle_bati = 456 m²` alors que la maison vendue fait 228 m² (ligne dupliquée par nature de culture sols/terres, sommée deux fois), et 2025-1268435 (terrain nu) est absente **par construction** (la table ne retient que les mutations résidentielles mono-type avec surface, cf. `_geo_dvf_aggregate`, `src/labuse/ingestion/layers_ingest.py`).

### A-Sitadel (sitadel_permits)

Source de vérification : API SDES **Dido** (source vivante, le jeu data.gouv historique est archivé — cf. FRAICHEUR.md), datafile « logements » `8b35affb-55fc-4c1f-915b-7750f974446a`, filtre serveur `DEP_CODE=eq:974&NUM_DAU=eq:…`. 3 permis :

| permit_id | Champ | Base | Source Dido | Écart |
|---|---|---|---|---|
| 9744222500061 | type/date/état/commune/nb lgt/surf hab | PC · 22/09/2025 · état 2 · Le Tampon · 1 lgt · 27 m² | PC · 2025-09-22 · ETAT_DAU 2 · COMM 97422 · 1 · 27 | **0** |
| 97441325A0013 | idem | PC · 01/10/2025 · état 2 · Saint-Leu · 1 lgt · 39 m² | PC · 2025-10-01 · 2 · 97413 · 1 · 39 | **0** |
| 97441425A0205 | idem | PC · 18/12/2025 · état 5 · Saint-Louis · 1 lgt · 102 m² | PC · 2025-12-18 · 5 · 97414 · 1 · 102 | **0** |

**Verdict : 3/3 raccord exact** (type, date réelle d'autorisation, état, commune, nb logements, surface habitable). L'unique anomalie connue du flux (1 permis daté 17/08/2026, futur) vient du producteur et reste consignée dans FRAICHEUR.md ; re-comptée ici : toujours **1 seule ligne** sur 50 043 (règle C10).

### A-BODACC (bodacc_procedures)

Annonce `A202601243229` vérifiée sur l'API officielle DILA (`bodacc-datadila.opendatasoft.com`, dataset `annonces-commerciales` — le site bodacc.fr renvoie vers la même fiche `url_complete`) :

| Champ | Base | Source | Écart |
|---|---|---|---|
| siren | 790442891 | 790 442 891 (SCCV LIANE DE FEU, Le Tampon) | 0 |
| type_procedure | Autre jugement et ordonnance | jugement.nature idem | 0 |
| famille_jugement | Extrait de jugement | jugement.famille idem | 0 |
| date_annonce | 02/07/2026 | dateparution 2026-07-02 | 0 |
| tribunal / n° annonce / publication | Greffe TJ Saint-Pierre · 3229 · A | idem | 0 |

**Verdict : raccord exact 1/1** (jugement du 23/06/2026, clôture pour insuffisance d'actif — le contenu détaillé du jugement n'est pas stocké en base, seul le méta l'est : fidèle).

### A-DPE ADEME (dpe_records)

3 DPE re-requêtés sur `https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines?qs=numero_dpe:"…"` :

| numero_dpe | Base (étiquettes · type · surface · année · date · adresse · insee) | Source ADEME | Écart |
|---|---|---|---|
| 2697E1150241Z | A/A · maison · 152,2 m² · 2018 · 27/04/2026 · 5 Rue des Oliviers Saint-Louis · 97414 | idem champ à champ | **0** |
| 2674E1806904J | D/D · appartement · 46,6 m² · 2012 · 03/07/2026 · 17 Rue de la Gare Saint-Denis · 97411 | idem | **0** |
| 2673E0456907J | E/C · appartement · 28,5 m² · 1980 · 17/02/2026 · 1035 Av. des Mascareignes Saint-André · 97409 | idem | **0** |

**Verdict : 3/3 raccord exact** (y compris `adresse_ban` et `code_insee_ban`).

### A-BAN (adresses)

3 adresses re-requêtées sur `https://api-adresse.data.gouv.fr/search/` (citycode forcé) :

| id_ban base | BAN id retourné | Label BAN | Distance coords base↔BAN | Verdict |
|---|---|---|---|---|
| 97414_1180_00023 | 97414_1180_00023 | 23 Rue du Professeur Henri Lapierre 97450 Saint-Louis | **0,0 m** | **RACCORD EXACT** |
| 97415_0639_00154_ter | 97415_0639_00154_ter | 154ter Chemin Fond de Puits 97422 Saint-Paul | **0,0 m** | **RACCORD EXACT** |
| 97413_0500_00175 | 97413_0500_00175 | 175 rue du général lambert 97436 Saint-Leu | **0,0 m** | **RACCORD EXACT** |

### Synthèse BLOC A

**19/19 spot-checks raccord avec les sources officielles** (PVGIS 6, DVF 3, Sitadel 3, BODACC 1, DPE 3, BAN 3). La fidélité **d'ingestion** est excellente sur toutes les sources testées. Les problèmes trouvés ne sont pas des écarts à la source : ce sont des artefacts **d'agrégation interne** (BLOC B) et de **croisement** (BLOC C).

---

## BLOC B — Outliers DVF qui polluent le Baromètre foncier

### Ce que fait le Baromètre aujourd'hui

`src/labuse/api/moteurs.py` → `_barometre_data()` (M18, servi en JSON + PDF « canal marketing ») lit **`dvf_mutations`** (29 565 lignes, 1 ligne = 1 mutation, fenêtre 2021-2025) et calcule par trimestre et par commune :
- `mutations` = `count(*)` — **aucun filtre** ;
- `median_eur_m2` = médiane de `valeur_fonciere / surface_reelle_bati` filtrée `surface > 0 AND valeur > 0 AND ratio BETWEEN 100 AND 12000`.

Il n'exclut **ni la VEFA, ni les échanges/adjudications/expropriations, ni les prix symboliques (> 0 suffit), ni les surfaces mal agrégées**. En amont, `dvf_mutations` est fabriquée par `_geo_dvf_aggregate()` (`layers_ingest.py`) qui ne retient que les mutations résidentielles mono-type géolocalisées avec surface — c'est déjà un bon garde-fou — mais **somme la surface bâtie sans dédoublonner les lignes**.

### B1 — Ventes à prix symbolique

Grain mutation, `dvf_mutations_parcelle` (43 698 mutations) : **211 mutations ≤ 1 €**, 224 ≤ 10 €, **422 ≤ 1 000 €**, 61 sans prix.
Exemples : `2025-1266622` (0,15 € !, Saint-Paul CH1825, 11/02/2025), `2022-1636046` (1 €, 97406000AV1300), `2021-1674043` (1 €, Saint-Paul DP0808). Typiquement donations déguisées en « Vente », apports, régularisations.
Dans la table du Baromètre (`dvf_mutations`) il en reste **16 à ≤ 1 € et 31 à ≤ 1 000 €** : le filtre `ratio ≥ 100` les écarte de la **médiane**, mais elles restent comptées dans le volume `mutations` affiché. Les médianes de secteur (`dvf_secteur_medianes`, `dvf_marche.py`) appliquent déjà, elles, un seuil `valeur > 1000` — le Baromètre est **moins protégé que le module marché**.

### B2 — Mutations multi-parcelles : le prix total est DUPLIQUÉ par ligne, pas ventilé

Démonstration par requête (`dvf_mutations_parcelle`) : le prix `valeur_fonciere` d'une mutation multi-parcelles est recopié **à l'identique sur chaque ligne** (c'est le fonctionnement du fichier DGFiP, pas un bug d'ingestion) :

| id_mutation | lignes | parcelles distinctes | prix distincts | valeur |
|---|---|---|---|---|
| 2025-1269487 | 104 | 95 | **1** | 1 € |
| 2021-1678410 | 82 | 78 | **1** | 1 € |
| 2022-1640625 | 74 | 70 | **1** | 1 € |

Volumes : **6 184 mutations sur 43 698 (14,2 %) touchent ≥ 2 parcelles** (5 221 en 2-3, 871 en 4-10, 92 en > 10). Toute lecture « par parcelle » du prix (ex. vue `v_parcel_dvf_last`) porte donc le prix de l'ENSEMBLE — le caveat est documenté dans `dvf_marche.py` et exposé par le flag `multi_parcelles` : conforme. Le Baromètre travaille au grain mutation, donc pas de double compte du **prix** ; le problème est la **surface** (B4).

### B3 — VEFA

`dvf_mutations_parcelle` : 2 686 mutations VEFA (6 641 lignes). Dans la table du Baromètre : **1 407 mutations sur 29 565 (4,8 %)** de nature « Vente en l'état futur d'achèvement » (+ 160 adjudications, 66 échanges, 3 expropriations, 31 « vente terrain à bâtir »). La VEFA est du **neuf** : la mélanger à l'ancien dans une même médiane €/m² biaise la série vers le haut (et le flux VEFA est concentré sur quelques trimestres/communes de livraison). La conservation de la VEFA en base est un choix produit assumé (comparable « neuf », docstring `ingest_dvf`) — c'est son **absence de distinction dans le Baromètre** qui pollue.

### B4 — Surfaces bâties double-comptées dans `dvf_mutations` (bug de fabrication)

geo-DVF répète la ligne d'un même local pour **chaque subdivision fiscale (nature_culture) et chaque disposition** ; `_geo_dvf_aggregate()` somme `surface_reelle_bati` de toutes les lignes résidentielles sans dédoublonner. Vérifié : les 29 565 valeurs stockées = somme **brute** ; en dédoublonnant (distinct par parcelle × type × surface) **1 440 mutations (4,9 %) ont une surface gonflée, facteur moyen ×2,6**, extrêmes spectaculaires :

| mutation | commune | valeur | surface stockée | surface dédoublonnée | €/m² stocké | €/m² corrigé |
|---|---|---|---|---|---|---|
| 2024-1188637 | Saint-Paul | 10 814 215 € | **67 740 m²** | 323 m²* | **160** | 33 481* |
| 2023-1319031 | Sainte-Marie | 5 683 343 € | 8 002 m² | 352 m²* | 710 | 16 146* |
| 2023-1317431 | Saint-Denis | 15 000 € | 4 503 m² | 203 m² | 3 | 74 |

\* borne basse : pour les programmes VEFA multi-lots (2024-1188637 = **1 008 lignes « Appartement » sur UNE parcelle**, chaque lot répété sur 4 natures de culture), ni la somme brute ni le dédoublonnage ne reconstituent la vraie surface — les numéros de lot ne sont pas conservés en base. La vraie surface est irrécupérable sans ré-ingestion avec `lot*_numero`.
Gravité : un €/m² de 160 ou 710 **passe le filtre 100-12000 du Baromètre** et tire la médiane vers le bas.

### B5 — Impact chiffré sur le Baromètre

Périmètre = les mutations que le Baromètre utilise réellement pour sa médiane (surface > 0, valeur > 0, ratio 100-12000) : **29 220**. Part polluée (VEFA ∪ natures non-Vente ∪ surface double-comptée ∪ prix ≤ 1 000 €) : **2 982 mutations, soit 10,2 %** — détail : VEFA 1 394, autres natures (adjudication/échange/expropriation) 241, surface double-comptée 1 384, prix symbolique 0 (ceux-ci sont bien absorbés par le filtre ratio ≥ 100, mais restent comptés dans le volume `mutations` affiché).

Médiane €/m² bâti « telle que servie » vs « propre » (hors VEFA/natures non-Vente/prix ≤ 1 000 €, et surface non double-comptée), fenêtre 2021-2025 :

| Périmètre | n baromètre | médiane actuelle | n propre | médiane propre | Δ |
|---|---|---|---|---|---|
| Saint-Denis | 8 120 | 2 481 €/m² | 7 539 | 2 455 €/m² | **−26 € (−1,0 %)** |
| Saint-Paul | 3 552 | 4 351 €/m² | 3 114 | 4 291 €/m² | **−60 € (−1,4 %)** |
| Saint-Pierre | 3 254 | 3 022 €/m² | 2 938 | 3 010 €/m² | −12 € (−0,4 %) |
| Île entière | 29 220 | 2 591 €/m² | 26 238 | 2 581 €/m² | −10 € (−0,4 %) |

Lecture : la **médiane** est robuste (impact ≤ 1,4 % sur les communes témoins — deux pollutions se compensent partiellement : la VEFA, chère, tire vers le haut ; les surfaces double-comptées, qui minorent le €/m², tirent vers le bas). En revanche **10,2 % des observations de la série sont fausses ou hors-objet une à une** : tout usage non médian (volumes affichés, moyennes, top communes où la VEFA se concentre, comparaison trimestrielle d'une petite commune où 50 livraisons VEFA tombent le même trimestre) est exposé. Le compteur `mutations` du Baromètre et le `count >= 100` du top communes incluent ces 10,2 %.

À noter aussi : **386 mutations résidentielles** de `dvf_mutations_parcelle` sont absentes du Baromètre **par construction** (mutations mixtes maison+appartement écartées, non-géolocalisées) — choix documenté, pas une perte silencieuse.

### Recommandations BLOC B (pour M6 Phase 2, aucune appliquée ici)

1. Baromètre : exclure `nature_mutation <> 'Vente'` (la VEFA peut devenir une série séparée « neuf »), seuil `valeur > 1000`, et aligner le comptage `mutations` sur le périmètre de la médiane.
2. `_geo_dvf_aggregate` : dédoublonner les lignes résidentielles par (parcelle, lot/disposition) — nécessite de conserver `numero_disposition`/`lot1_numero` à l'ingestion ; a minima, dédoublonner par (id_parcelle, type_local, surface).
3. Flag `vefa` déjà présent dans `raw` : l'exploiter (aucune migration nécessaire pour la reco 1).

---

## BLOC C — Cohérence inter-couches (règles automatiques, toute la base)

Règles exécutées le 13/07/2026 sur l'île entière (431 663 parcelles, 24 communes). Chaque règle : SQL (résumé), violations, gravité, cause probable. Les 5 témoins M5.1 ne sont pas re-testés.

### C1 — Piscine détectée sans bâti sur la parcelle

```sql
WITH pisc AS (SELECT DISTINCT idu FROM ortho_detections
              WHERE type='piscine' AND (validation IS NULL OR validation<>'faux_positif') AND idu IS NOT NULL)
SELECT count(*) FROM pisc JOIN parcels p USING (idu)
WHERE NOT EXISTS (SELECT 1 FROM spatial_layers b
                  WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975));
```
**707 violations / 17 729 parcelles à piscine (4,0 %).** Exemples : 97402000AD0868, 97402000AE0397, 97402000AE0621 (Bras-Panon).
Gravité : **moyenne** — une piscine sans bâti peut être réelle (piscine sur parcelle voisine de la maison, détachée) mais c'est aussi le profil type du faux positif (bassins agricoles, bâches). Cause probable : mélange (i) rattachement de la détection à la parcelle du bassin et non à celle de la maison (découpages fins), (ii) faux positifs restants du jeu non validé (`validation IS NULL` = 18 280 sur 19 899), (iii) trous BD TOPO sur bâti récent. À croiser avec le preset piscines (proxy emprise 40-400 déjà en place).

### C2 — DPE rattaché à une parcelle sans bâti

Même EXISTS bâtiment que C1 sur `dpe_records.parcelle_idu` : **41 violations / 903 DPE rattachés (4,5 %).** Exemples : 2595E2711429O → 97413000AV1795 (Saint-Leu), **2697E1150241Z → 97414000DK0140** (maison 2018 — également testée au BLOC A : la donnée ADEME est exacte, c'est le rattachement parcellaire ou le millésime BD TOPO qui pèche), 2135E0632315E → 97415000BO0843.
Gravité : **faible** — cause probable : géocodage BAN à la parcelle voisine (rattachements `ban_locale` avec score 0,7-0,8) et constructions récentes absentes de BD TOPO.

### C3 — Vue mer « oui » incompatible avec le relief

Critère retenu (documenté) : la table `parcel_vue_mer` porte `obstruction_pct` (calcul de masque) et `distance_cote_m`. Incompatibilités testées : (a) `vue='oui' AND obstruction_pct >= 50` — contradiction interne ; (b) `vue='oui' AND distance_cote_m > 2000` — au-delà de la portée maximale observée pour « partielle » (2 000 m), sans MNT d'altitude parcellaire en base (RGE ALTI stocké en **pente**, pas en altitude), la distance sert de proxy ; (c) `vue='non' AND obstruction_pct=0 AND distance_cote_m < 100` — front de mer sans obstruction classé sans vue.
**Violations : (a) 0 · (b) 3 · (c) 0** sur 150 642 parcelles évaluées. Les 3 cas (b) : 97414000ET1418 (Saint-Louis, 4 851 m, obstruction 3 %), 97411000CM0143 (Saint-Denis, 4 758 m), 97418000AS1334 (Sainte-Marie, 2 324 m) — plausibles en hauteur (obstruction quasi nulle mesurée), à vérifier visuellement.
Gravité : **négligeable** — la couche vue mer est interne-cohérente. Verdict : **OK**.

### C4 — Permis récent sur parcelle au statut incohérent ⚠

Critère : PC/PA **autorisé** depuis le 01/07/2024 (le flux Sitadel ne contient que des autorisations, cf. `_statut()` `permits.py`) dont `idu_codes` pointe une parcelle encore présentée comme opportunité (`mvt_parcels.status='chaude'` ou `tier_v2='brulante'`).
```sql
WITH ids AS (SELECT permit_id, date, jsonb_array_elements_text(idu_codes) idu
             FROM sitadel_permits WHERE date >= '2024-07-01' AND type IN ('PC','PA'))
SELECT count(DISTINCT m.idu) FROM ids JOIN mvt_parcels m ON m.idu = ids.idu
WHERE m.status='chaude' OR m.tier_v2='brulante';
```
**320 parcelles (312 permis) / 1 277 chaudes-ou-brûlantes (25 %)** — dont **77 des 119 brûlantes (65 %)** : 39 permis état 2 (autorisé), 4 état 4, 30 état 5, 6 état 6. Le champ `mvt_parcels.evenement` est vide pour les 119 brûlantes : le permis n'est **pas** la cause de leur mise en avant. Exemples brûlantes : 97401000AI1188 (Les Avirons, PC 97440124A0050 du 28/04/2025), 97402000AD1052 (Bras-Panon, PC du 02/12/2024), 97403000AR1423 (Entre-Deux, PC du 13/11/2025).
Gravité : **HAUTE (produit)** — une « brûlante » vendue comme dormante qui porte un PC autorisé (voire achevé) depuis moins de 2 ans décrédibilise la shortlist en démo client. Cause probable : le scoring v2 n'utilise pas (ou pas en malus) le signal « permis autorisé SUR la parcelle » ; à intégrer au calibrage M6 (malus ou flag « déjà en projet »).

### C5 — Bâti BD TOPO vs classement de la parcelle

(a) **Parcelle chaude/brûlante avec emprise bâtie > 30 % de la surface : 0 violation.** Le caractère « nu » du périmètre produit est cohérent. **OK**.
(b) **Emprise bâtie > surface de la parcelle (×1,05) : 17 728 parcelles** (`p_model_bati.emprise_bati_m2 > parcels.surface_m2*1.05`). Exemples : 97404000AD1396 (emprise 2 m² / surface 1 m²), 97413000DG0115 (89/30), 97422000EM0459 (13/4).
Gravité : **moyenne-haute** — cause démontrée par C7 ci-dessous : les bâtiments dupliqués inter-communes sont sommés deux/trois fois par `build_bati()` (`scoring/p_model/sql.py`, `sum(ST_Intersection(...))` sans dédoublonnage). S'y ajoutent des micro-parcelles (surface < emprise réelle d'un bâtiment débordant).

### C6 — Adresses BAN orphelines & rattachements DPE (règles ajoutées)

- `adresses.idu` pointant une parcelle inexistante : **0** (sur l'ensemble de la table). **OK**.
- `dpe_records.parcelle_idu` dont le préfixe INSEE ≠ `code_insee` du DPE : **6** (ex. 2106E0576902U : DPE à Saint-Pierre 97416, parcelle 97422000BW0933 au Tampon — géocodage `point_ban` en limite communale). Gravité : faible.

### C7 — Doublons géométriques de la couche bâtiment (règle ajoutée — écho de l'anomalie A1 PLU) ⚠⚠

```sql
WITH d AS (SELECT md5(ST_AsBinary(geom)::text) h, count(*) n, count(DISTINCT commune) ncom
           FROM spatial_layers WHERE kind='batiment' GROUP BY 1 HAVING count(*)>1)
SELECT count(*), sum(n)-count(*), count(*) FILTER (WHERE ncom>1) FROM d;
```
**247 825 géométries dupliquées → 303 576 lignes excédentaires sur 817 506 (37 % de la couche), 100 % inter-communes** (192 693 en double, 54 533 en triple, jusqu'à ×5). Exemple : un bâtiment « Résidentiel » présent à l'identique sous Entre-Deux (id 1214949), Saint-Pierre (414208) et Le Tampon (517421).
C'est la **même cause racine que l'anomalie A1** (PLU dupliqué, consignée M5.1) : l'ingestion par commune récupère les objets d'un halo autour de la commune, sans dédoublonnage global. L'ampleur (37 %, contre 7 % pour le PLU) indique un halo/bbox large, pas seulement les limites.
**Impact mesuré sur `p_model_bati`** (échantillon aléatoire de 4 000 parcelles bâties, recalcul avec/sans dédoublonnage) : **39,7 % des parcelles bâties ont une emprise gonflée, facteur moyen ×2,28** (×1,51 sur tout l'échantillon). Toute variable dérivée (caractère nu/bâti du p-score, densité bâtie de secteur, résiduel, C5b) est contaminée.
Gravité : **HAUTE (données)** — réparation = dédoublonnage à l'ingestion (ou `DISTINCT ON (md5(geom))` dans `build_bati`) + re-run p_model ; à coupler au fix A1 et à la ré-ingestion BD TOPO juillet déjà au backlog.

### C8 — Permis Sitadel dont l'IDU cadastral n'existe pas (règle ajoutée)

`idu_codes` reconstruits (SEC_CADASTREn/NUM_CADASTREn) absents de `parcels` : **9 295 IDU distincts, 12 241 permis touchés sur 50 043 (24 %)**. Exemples : 97441116A0361 → 97411000DS0641, 97441117A0083 → 97411000AB0730, 97440326A0025 → 97403000AP2040.
Gravité : **moyenne** — attendu en partie (historique 2013+ : parcelles divisées/remembrées depuis, édition cadastre 2026-06), mais 24 % plafonne le géocodage parcellaire des permis (cf. mémoire Sainte-Suzanne 64,6 %) et donc la règle C4. Cause : décalage millésimes cadastre/permis + reconstruction d'IDU sans contrôle d'existence.

### C9 — Raccord interne DVF (règle ajoutée)

- Mutations de `dvf_mutations` sans détail dans `dvf_mutations_parcelle` : **0**. **OK**.
- Mutations résidentielles (avec surface) absentes du Baromètre : 386 — **par construction** (mixtes/non-géolocalisées, documenté). **OK**.

### C10 — Garde-fous temporels (règle ajoutée)

Permis à date future : **1** (le 9744122500519 du 17/08/2026, outlier producteur déjà consigné FRAICHEUR.md — inchangé). DVF : max 31/12/2025, aucun futur. **OK**.

### Synthèse BLOC C

| Règle | Violations | Gravité |
|---|---|---|
| C1 piscine sans bâti | 707 / 17 729 (4,0 %) | moyenne |
| C2 DPE sur parcelle sans bâti | 41 / 903 (4,5 %) | faible |
| C3 vue mer incompatible | 3 / 150 642 | négligeable |
| **C4 permis récent sur chaude/brûlante** | **320 / 1 277 (25 %) — dont 77/119 brûlantes** | **haute (produit)** |
| C5a bâti fort sur chaude/brûlante | 0 | — |
| C5b emprise > surface parcelle | 17 728 | moyenne-haute (symptôme C7) |
| C6 adresses orphelines / DPE insee | 0 / 6 | nulle / faible |
| **C7 bâtiments dupliqués inter-communes** | **303 576 lignes (37 % de la couche) ; 39,7 % des parcelles bâties gonflées ×2,28** | **haute (données)** |
| C8 IDU permis inexistants | 12 241 permis (24 %) | moyenne |
| C9 raccord DVF interne | 0 | — |
| C10 dates futures | 1 (connu) | faible |

---

## Verdict global §1.1b

1. **Fidélité aux sources : excellente.** 19/19 spot-checks exacts (PVGIS jusqu'à la 2e décimale, DVF ligne à ligne, Sitadel/BODACC/DPE/BAN champ à champ). Les portails vivants utilisés sont les bons (Dido, DILA-ODS, data-fair ADEME).
2. **Le risque n'est pas à l'ingestion mais à l'agrégation/croisement.** Trois chantiers chiffrés pour M6 :
   - **Bâtiments dupliqués (C7)** — 37 % de la couche, emprises gonflées ×2,28 pour 40 % des parcelles bâties ; même racine que A1, à corriger ensemble ;
   - **Baromètre DVF (BLOC B)** — 10,2 % des mutations de sa médiane sont VEFA/natures non-Vente/surfaces double-comptées ; effet médiane mesuré modeste (−0,4 à −1,4 % sur les communes témoins) mais volumes et extrêmes contaminés, et 1 440 surfaces stockées fausses dans `dvf_mutations` (facteur moyen ×2,6) ;
   - **Permis récents sur brûlantes (C4)** — 65 % des brûlantes portent un PC/PA autorisé < 2 ans : signal à intégrer au scoring avant toute démo.
