# VERITE-TERRAIN-3 — Relecture de cas, moitié 2 (cas 31 à 60 de TEST1-NON-60)

Audit lecture seule — 15/11/2026. 30 permis de logements réellement accordés, classés
« non constructible » par le moteur LABUSE de main. Sources : `cache/capacite/<idu>.json`,
`sitadel_permits`, `parcels`/`parcel_zone_plu`/`parcel_residuel`/`p_model_bati`,
`spatial_layers` (plu_gpu_zone, plu_gpu_prescription, ppr, georisque_alea, batiment),
`plu_reglement_extrait` (verbatim), `config/plu_destinations/*.yaml`, `config/calibrage/*`,
`plu_veille_etat`. Détail par cas : `TEST1-RELECTURE-2.csv`.

## Décompte final

| classement | n |
|---|---|
| erreur_labuse | 10 |
| decalage | 14 |
| exception_legale | 5 |
| indetermine | 1 |
| **total** | **30** |

## Erreurs confirmées (10) — trois familles

### E-A. Secteurs d'habitat de la zone A (Aba, Arh) servis « Construction neuve non autorisée » (5 cas)

Le règlement ADMET expressément les constructions nouvelles d'habitation dans ces secteurs,
et `config/plu_destinations/*.yaml` le modélise (`zones.<secteur>.sous_destinations.logement:
sous_condition`, seuil 120/150 m²) — mais le moteur capacité l'ignore : ces secteurs n'ont pas
de feuille `regles` d'enveloppe, `resolve_zone` ne les résout pas, et la famille A tombe dans
`faisabilite_zone_non_constructible` (`src/labuse/faisabilite/engine.py`, cause_moteur
`zone_transition`). Le verdict servi est factuellement faux au règlement.

Verbatims (plu_reglement_extrait) :
- **Salazie** (PLU 24/05/2022), ARTICLE A2 2.2-7, p.41-42 : « Dans le secteur Aba, les
  constructions nouvelles à usage d'habitation … sont admises dans la limite totale de
  150 m² de surface de plancher. »
- **Le Tampon** (règlement 2018), ARTICLE A2 2.2-6, p.92-93 : « Dans le secteur Aba, les
  constructions à usage d'habitation … admises dans la limite totale de 120 m² de surface
  de plancher. »
- **Les Trois-Bassins** (PLU 02/06/2022), ARTICLE A2.2 (8.), p.75 : « Dans le secteur Arh,
  les constructions nouvelles à usage d'habitation … admises dans la limite totale de
  120 m² de surface de plancher. »

Cas (tous les permis sont SOUS le seuil du secteur) :
| permis | idu | commune | surf_hab | seuil | dépôt |
|---|---|---|---|---|---|
| 97442122A0074 | 97421000AL0400 | Salazie | 146 m² | 150 | 2022 (accordé 03/2023) |
| 9744212500022 | 97421000AB0337 | Salazie | 117 m² | 150 | 2025 (post-PLU net) |
| 9744212600010 | 97421000AS0250/0256/0217 | Salazie | 113 m² | 150 | 02/2026 (post-PLU net) |
| 9744222600036 | 97422000AZ0506 | Le Tampon | 115 m² | 120 | 2026 |
| 9744232600011 | 97423000AK1813 | Trois-Bassins | 77 m² | 120 | 04/2026 |

Reproduction : `select texte_verbatim, page_pdf from plu_reglement_extrait where insee in
('97421','97422','97423') and zone='A' and article_ref like 'ARTICLE A%2%';` puis comparer au
`cache/capacite/<idu>.json` (`cause=zone_non_constructible:Aba|Arh`).

### E-B. Recul séparatif facultatif appliqué comme obligatoire → faux « terrain exigu » (4 cas)

Le moteur insète le contour de 3 m sur TOUTES les limites (« le contour inseté se vide ») ;
sur des parcelles étroites (3,4–6,5 m de large) l'assiette tombe à 0 m² et la décision
EXIGU-FIX conclut « exigu avec preuve ». Or les règlements cités rendent le retrait séparatif
FACULTATIF (implantation en limite permise), seul le recul sur voie étant obligatoire :
- St-Leu UB7/UD7 : « **Si** une construction est implantée **en retrait** des limites
  séparatives …, la marge d'isolement minimale doit être de 3,00 m. »
- St-Pierre Uf3 (PLU 25/06/2024) : « implantées : **Soit en limites séparatives** et au
  maximum sur 2 limites …, **Soit en retrait de 3 mètres**. »
- Salazie UC7 : « peuvent être implantées **sur deux limites séparatives latérales** pour
  les terrains dont la largeur sur voie est inférieure à 15 mètres. »

| permis | idu | zone | parcelle | inset −3 m | permis accordé |
|---|---|---|---|---|---|
| 97441313A0107 | 97413000CY1217 | UD St-Leu | 210 m² (larg. 6,5 m) | 1 m² | 91 m² (2013, bâti aujourd'hui 121 m²) |
| 97441323A0068 | 97413000CN0467+CN0304 | UB St-Leu | 95+61 m² | 0 m² | 59 m² (2023) |
| 97441624A0218 | 97416000HO0272 | Uf St-Pierre | 192 m² (larg. 5,8 m) | 0 m² | 114 m² (07/2024 ; dépôt 01/2024 sous l'ancien PLU — la règle actuelle citée prouve néanmoins la sur-application) |
| 97442124A0010 | 97421000AV1300 | UC Salazie | 106 m² (portion UC 72 m²) | 0 m² | 42 m² (07/2024) |

Reproduction : `select idu, round(st_area(geom_2975))::int,
round(st_area(st_buffer(geom_2975,-3)))::int from parcels where idu in
('97413000CY1217','97413000CN0467','97413000CN0304','97416000HO0272','97421000AV1300');`

### E-C. Couche zonage lacunaire → faux « hors_plu » (1 cas)

**97441315A0075 / 97413000DE2186 (Saint-Leu)** — verdict `hors_plu` (aucune zone) alors que
la parcelle (397 m², rue Félicien Hibon, 4 bâtiments BD TOPO totalisant 103 m²) est en tissu
urbain à 23 m d'un polygone UC, 62 m d'un N, 83 m d'un UCA (partition DU_97413, idurba
97413_20070226) : trou dans la couche de zonage 2007 — un PLU couvre tout le territoire
communal, « hors PLU » est matériellement faux. Reproduction : `select z.attrs->>'libelle',
round(st_distance(p.geom_2975,z.geom_2975)) from parcels p, spatial_layers z where
p.idu='97413000DE2186' and z.kind='plu_gpu_zone' and z.attrs->>'partition' like '%97413%'
and st_dwithin(p.geom_2975,z.geom_2975,300) order by 2 limit 3;`

## Décalages (14)

- **Le Tampon 2AUc ×6** (97442224A0251, 97442224A0401, 9744222500054, 9744222500057,
  9744222600045, 9744222600064) : zones 2AU fermées au règlement 2018/GPU 2023-08-11
  (ouverture « subordonnée », AUindicée 2.2 (3) p.86 ; réserve SAR p.7) — le verdict LABUSE est
  conforme au document détenu, mais 6 permis 2024-2026 (dont du neuf de 115-135 m², grappe
  impasse des Pêches) signalent une ouverture/modification du PLU non répercutée au GPU
  (`plu_veille_etat` 97422 : a_jour sur le doc 2023). Donnée amont en retard, pas une règle fausse.
- **Instruit sous l'ancien PLU** : 97441623A0473 (Us St-Pierre, dépôt 2023, PLU 25/06/2024),
  97442025A0053 (A Ste-Suzanne, accordé 14 j après le PLU 29/09/2025), 97442322A0076
  (1AUa Trois-Bassins, dépôt 2022/PLU 02/06/2022 + ER 70 LLS couvrant 100 %).
- **Rattachement parcellaire incomplet** : 97442224A0131 (7 logements / 681 m² de SDP rattachés
  à 2 confettis de 68+38 m² — l'assiette réelle est ailleurs).
- **Multi-parcelles à cheval** : 97442122A0025 (N + Aba Salazie, dépôt autour de l'approbation
  du PLU ; NB la règle Aba est par ailleurs l'erreur E-A).
- **Document opposable incertain (St-Leu, PLU 2007, GPU vide)** : 97441323A0224 (neuf en N
  en 2024 contre un texte qui n'admet que 20 m² d'extension — évolution non ingérée probable),
  97441320A0012 (APF / ZAC Roche Café : mise en compatibilité non ingérée).
- **PPR littoral** : 97441022A0230 (97410000AO0473, 100 % en PPRL zone R INTERDICTION,
  submersion fort 86 % ; bâti existant 317 m² — chronologie PPR/permis non tranchable).

## Exceptions légales (5)

- **Logement d'exploitant / extension en zone A** : 97441022A0170 (CL0481, bâti 272 m², 80 m² ;
  A-3 2° p.34 St-Benoît), 97441024A0073 (CK0099, ferme 6 ha, 2 lgt), 97441313A0266 (AC0017,
  ferme 7,7 ha, 46 m² ; A 2 al.1 p.100 St-Leu : une habitation/exploitation ≤150 m² SHON).
- **Emplacement réservé logement social réalisé par son bénéficiaire** : 9744122500200
  (AO0432-34, 26 lgt) et 9744122600079 (CY0017, 28 lgt) — Saint-Joseph, parcelles couvertes à
  100 % par l'ER « logement social/mixité sociale » (prescription GPU 05), permis portés par le
  MÊME pétitionnaire SIREN 380572453 : LABUSE écarte par conception les parcelles grevées d'ER
  (cascade_rules, décision 3.a) ; côté bénéficiaire de la servitude, le programme se construit.
  (À noter : 97412 est `desync` dans plu_veille_etat — ancien 20240320 → nouveau 20251210.)

## Indéterminé (1)

- 97441625A0474 (97416000HI1129, Us St-Pierre 98 %, aucun bâti recensé) : permis NEUF 141 m²
  déposé 2025 (post-PLU 2024) alors que le verbatim Us1 p.130 n'admet que « les extensions
  limitées à 25 % de la surface de plancher des constructions existantes ». Le verdict LABUSE est
  conforme au règlement ; le permis le contredit sans explication locale — non tranchable.
