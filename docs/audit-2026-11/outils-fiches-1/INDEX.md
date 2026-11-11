# OUTILS-FICHES-1 — index des fiches outils

Audit **lecture seule** (branche `audit/outils-fiches-1`, worktree `~/Desktop/labuse-fiches`, 11/11/2026). Une fiche par
outil du menu « Outils », prise dans le registre `frontend/src/components/outils/registry.ts`. Chaque fiche décrit ce
que le code **fait réellement** (pas ce qu'il devrait faire), avec fichier:ligne, les sources du catalogue `data_sources`,
et trois cas rejoués sur sorties réelles.

## Méthode et conventions
- **Backend** interrogé en local sur `http://127.0.0.1:7300` (FastAPI, mode dev, base Postgres `openclaw@labuse`
  partagée). Un **seul worker** : plusieurs fiches notent que le serveur s'est bloqué/est tombé sous une requête lourde
  (listes permis, valorisation patrimoine, FTS PLU). Les sorties ont été obtenues par relances ; aucune écriture.
- **Parcelles témoins** du mandat : `97411000BZ1065`, `97409000AK0804`, `97415000DH0076`. Fait établi par les 16 fiches
  et à retenir : `97415000DH0076` résout en **Saint-Paul** (INSEE 97415), **pas** Saint-Pierre/Joseph ; `97409000AK0804`
  appartient à la **COMMUNE DE SAINT ANDRÉ** (personne morale publique). Deux des trois témoins ne sont **pas** des
  personnes morales (BZ1065, DH0076) → les outils « propriétaire PM » (Patrimoine, Blocs, Successions) les rejouent sur
  témoins adaptés, signalés dans chaque fiche.
- **Catalogue des sources** : table `data_sources` (129 lignes, 107 servies). Les millésimes cités ci-dessous sont ceux
  **servis** au 11/11/2026.

## Tableau des outils

| Outil (clé / num) | Données principales lues | Sourcé / estimé | Doute le plus grave |
|---|---|---|---|
| **PLU** (`plu` / O13) | `plu_reglement_extrait` (verbatim, 21/24 communes) ; configs `plu_millesimes.yaml`, `veille_plu.yaml` ; API GPU live. Source cat. « Urbanisme PLU/GPU (API Carto) ». | ~85 % sourcé (verbatim, page PDF, statut) / ~15 % estimé (titre « en clair », drapeau doute, pagination — heuristiques en dur). | Saint-Benoît marqué « servable » mais **8 extraits** seulement (vs 100-400 ailleurs) : ingestion incomplète, rien ne le signale ; aucun test de complétude ni de la recherche FTS. |
| **Permis** (`permis` / M03 ; +`promesses`) | `sitadel_permits` (SITADEL, millésime **2026-08**, mensuel, →31/08/2026) + dérivées `m10_permit_delais`, `via_permits_geo`. | ~90 % sourcé (comptages/distances) / estimé = fenêtres temporelles (Récent 24 m, Dormant >36 m) et case « Autres ». | La liste Dormant (`/modules/promesses`) a **fait tomber le backend** pendant l'audit (cohérent avec notes « COUNT ~4-28 s »). |
| **Communes** (`communes` / O6 ; +`barometre`) | DVF (`dvf_mutations`, 2026-S1), SITADEL (2026-08), Cerema ENAF (`commune_conso_enaf`, 2021-2024), DHUP SRU/loyers, OCS GE, DGFiP PM (`parcelle_personne_morale`, 2025), `parcel_p_score_v2`. | ~80-85 % sourcé / ~15-20 % estimé (score composite min-max **non calibré**, budget/horizon ZAN loi TRACE −50 %). | Le « score où investir » et l'horizon ZAN (~1 an) sont des estimations non calibrées présentées comme des verdicts saillants. |
| **Scan patrimoine** (`patrimoine` / M02 ; +`veille-promoteurs`) | `parcelle_personne_morale` (DGFiP PM 2025), `sitadel_permits`, `pm_dirigeants` (INPI), `bodacc_depots`, `etablissement_parcelle` (SIRENE), `dvf_mutations_parcelle`. | ~90 % sourcé / estimé = valorisation (surface × médiane DVF zone) + regroupement en opérations (250 m / 24 m). | **3 comptes différents de « parcelles détenues » pour le même SIREN** (1833 vs 1871) affichés côte à côte, aucun test ne les réconcilie. |
| **Assemblage** (`assemblage` / M16) | `parcels` (cadastre PCI/Etalab), `spatial_layers` (zonage/grèves GPU), `parcelle_personne_morale`, `dvf_mutations_parcelle` (2026-S1). | ~40 % sourcé (géom, zonage, PM, marché) / ~60 % estimé (toutes les SDP, charge foncière, prix de sortie — moteur de faisabilité). | Si bâti existant > capacité de l'union, « Bâti conservé » affiche 0 m² / −100 % en masquant `sdp_existante_totale` → lecture « rien à faire » à tort. Aucun test numérique des SDP. |
| **Comparer** (`comparer` / A8) | `GET /compare` recopie des champs **déjà calculés** par la fiche + faisabilité (CoSIA 2025, BD TOPO, DGFiP PM, `plu_destinations`, PPR, BAN PLUS, DVF). | 7/11 lignes sourcées / 4 estimées (SDP résiduelle, SDP max, part gabarit, charge foncière). | `terrain_zone_eur_m2` **recalculé sans le seuil `SEUIL_N=8`** que la fiche applique (`app.py:9266-9270`) alors que le commentaire prétend lire la fiche « telle quelle » (atténué : non affiché aujourd'hui). |
| **Pièges et risques** (`risques` / M10) | `spatial_layers` (∩ parcelle, `geom_2975`) ⋈ `data_sources` ; `parcel_au_statut` ; `labuse.veille_plu`. 16 familles (PPR, Géorisques, 50 pas, DPU, EBC, bruit/PEB, ravines, ZNIEFF…). | ~85 % sourcé (chaque ligne = couche datée) / estimé = drapeau « rédhibitoire », puces « Vérifié rien à signaler », bloc « Non couvert ». | **Faux « RAS » par zone blanche** : couches partielles (DPU, assainissement 4/24, zones humides) affichées « Vérifié » là où aucune donnée n'existe (présence testée à l'échelle île, pas parcelle). |
| **Étude de zone** (`etude-zone` / M27) | Filosofi 2021 (carreaux 200 m), SIRENE géo (2026-09), DVF (`dvf_mutations`/`marche_dvf`, 2026-S1), SITADEL (2026-08), BPE 2025, Arcep 2026_T1, IRIS RP2022. | ~80 % sourcé (agrégats) / estimé = emplois (somme des bornes de tranches SIRENE, `TRANCHE_BORNES` en dur). | Se dit « chalandise » mais le périmètre est un **cercle à vol d'oiseau** (pas une isochrone) ; la lentille concurrents/NAF a été **retirée de l'UI** ; le médian €/m² vient du **secteur fiche**, pas du cercle. |
| **Estimer un bien** (`analyser-annonce` / N1) | DVF (`dvf_mutations` 2021→ + `dvf_mutations_histo` 2014-2020, 2026-S1), Radar `pige_*` (manuel/quotidien), `estimer_precision_calibration`. Calcul : `pige/api.py:1902`, `marche_service.py`. | tuiles + 8 comparables = sourcés / tout le bloc prix (€/m², fourchette, valeur, fiabilité, écart) = estimé. ~50/50 écran, cœur « prix » estimé. | « Prix estimé au m² » sert en réalité la **médiane de secteur** (`reference_locale` écrase la pondération par ressemblance) ; l'« ordre de grandeur » terrain multiplie la contenance **entière** par un €/m² de lot à bâtir → valeurs non marchandes sur grandes parcelles. |
| **Remonter le temps** (`temps` / M08) | A : `dvf_mutations_parcelle` + `dvf_mutations_histo`, `sitadel_permits`, `pm_proprietaires_millesimes`, `dfi_filiation`. B : tuiles WMTS IGN via `ortho_proxy.py` (SCAN 50 1950 → Ortho Express 2025). | ~100 % sourcé (aucun barème ni valeur calculée). | Le **chemin A (frise des faits datés) n'est rendu nulle part** dans l'app servie (`App.tsx:506` ne monte que le comparateur) alors que le menu l'annonce et que l'endpoint/composant existent et sont testés. |
| **Gabarit** (`gabarit` / M24) | `parcels`, `spatial_layers` (zone PLU, PPR via `labuse_ppr_couleur`, SUP), classif voie/séparative (BD TOPO + adjacence, `limites.py`), bâti BD TOPO, faîtage LiDAR HD 2023. | ~90 % sourcé (géom/verdicts) MAIS les **valeurs PLU chiffrées** (emprise %, hauteurs, reculs, CES) viennent de **YAML curés à la main** (`config/plu_destinations/*.yaml`, `plu_zonage.yaml`), pas d'une table traçable. | Le « faîtage LiDAR » est **une** valeur unique recopiée sur **tous** les bâtiments de la parcelle (et peut venir d'un voisin), présentée comme mesure du bâti ; et l'outil ne compare jamais ce faîtage à l'enveloppe → dépassement du bâti jamais signalé. |
| **Taxe d'aménagement** (`taxe-amenagement` / K3) | `taxe_amenagement_taux` + `taxe_amenagement_secteur` (source « Taxe d'aménagement — taux communaux (délibérations) », DGFiP DELTA, 24/24) ; barème `config/taxe_amenagement.yaml` (892 €/m², part dép. 2,5 %…). | taux + barème sourcés (légal daté) / tous les **montants €** estimés (calculés). RAP 0,40 % et péremption 365 j en dur. | Taux tous figés au **01/01/2022** en base ; péremption basée sur la date de relevé (`maj_at`), pas sur la délibération → un taux revoté non réingéré serait servi « en vigueur » sans alerte. |
| **Prospection solaire** (`prospection-solaire` / M26) | A piscines : `piscines` (BD ORTHO 20 cm **2025** + CoSIA). B ensoleillement : `parcel_solar` (PVGIS v5.3/SARAH3), `parcel_terrain` (RGE ALTI), `toiture_lidar` (LiDAR HD MNH 2023). **Tout gelé.** | ~50/50 : potentiel PVGIS/emprise/pentes/détection sourcés / puissance (`toit × 0,2 kWc/m²`), production, orientation, nature toit estimés. | « Puissance installable »/« Production annuelle » = `emprise × 0,2` sans part exploitable ni masques, lisible comme un dimensionnement de projet (DH0076 : 1,38 GWh/an). |
| **Blocs fonciers** (`blocs-fonciers` / M29) | `parcel_blocs` + `parcel_bloc_membres` (batch `blocs-build`), `parcelle_personne_morale` (DGFiP PM **2025**), `parcels`, `parcel_zone_plu`, vue `parcel_residuel`. Contiguïté `ADJ_BUFFER_M=0,5 m`. | ~85 % sourcé / seul estimé = SDP résiduelle (somme `parcel_residuel`, badge « Estimé »). | **4 865 blocs publics** (souvent les plus gros gisements) **masqués par défaut** derrière une case : l'utilisateur voit « 6 357 blocs » sans réaliser l'ampleur cachée. |
| **Successions à venir** (`successions` / M28) | snapshot `parcel_veille_succession` (batch `score-v-compute`, 06/10/2026) ; `pm_dirigeants`/`v_pm_propension_vendre` (INPI, 05/07/2026) pour l'âge ; DGFiP PM ; `bodacc_depots` ; SDP via `p_model_ext_dataset`. | identité + âge dirigeant sourcés / verdict « succession probable », seuils (âge ≥70, SCI dormante 20/5 ans), SDP estimés. ~60/40. | Snapshot servi contient **103 parcelles à dirigeant_age ≥100 ans (jusqu'à 114)** — faux positifs **nominatifs** ; le garde-fou [18;110] est postérieur au dernier build mais l'endpoint lit la table figée. Risque éthique + exactitude. DFI **non utilisée** (contrairement au brief). |
| **Courrier propriétaire** (`courriers` / M09) | `parcels`, `parcelle_personne_morale`, `owner_enrichment` (SIRENE), `parcel_adresse` (BAN), `parcel_zone_plu`, `dvf_mutations_parcelle` (2026-S1), `dryrun_cascade_results`, `courrier_opposition`. Provider `stub` (aucun envoi auto). | ~90 % sourcé (contenu courrier) / config = prix 2,50 € / coût 2,69 € / délai « 3 à 5 » / plafond 100 / seuil DVF 8. | Prix client (2,50 €) figé en config et **inférieur au coût** prestataire (2,69 €) ; le calcul « coût × marge 1,5 » documenté n'est **plus appliqué** → changer le coût admin ne change rien au prix (vente à perte non signalée). |

## Incohérences entre outils

Grandeurs calculées de plusieurs façons, et sources lues sous plusieurs formes/millésimes. Chaque point renvoie aux fiches.

1. **Prix DVF au m² d'un secteur — calculé d'au moins trois façons incompatibles.** La même donnée (« DVF / valeurs
   foncières », géo-DVF Etalab 2026-S1) sert un « €/m² de secteur » :
   - **Fiche / Étude de zone / Commune** appliquent un seuil d'effectif `SEUIL_N=8` ventes (défini `dvf_mediane.py:31`, appliqué p.ex. `zone.py:681`, `fiche_commune.py:43`) : sous le seuil, la médiane est masquée (« — ») ;
   - **Comparer** pose `terrain_zone_eur_m2` dans `_compare_row` en prenant le secteur `max(n_ventes)` de `dvf_parcelle.secteur` **sans ce seuil** (`app.py:9266-9270`) — peut sortir un prix sur 1-2 ventes que la fiche masquerait, alors que le commentaire du code (`app.py:9323-9326`) affirme le lire « tel quel » depuis la fiche ;
   - **Estimer un bien** écrase la médiane pondérée par ressemblance avec la médiane de secteur `reference_locale` ;
   - **Étude de zone** affiche, pour son médian €/m², la valeur du **secteur de la fiche** (`marche_dvf(idu)`) et non du cercle qu'elle analyse, alors que ses autres chiffres marché viennent du cercle.
   → cf. `comparer.md`, `analyser-annonce.md`, `etude-zone.md`, `courriers.md`.

2. **Même source DVF lue via ≥5 tables/chemins différents.** `dvf_mutations_parcelle` (Assemblage, Patrimoine, Courrier,
   Solaire, Temps, Estimer), `dvf_mutations` agrégée (Communes, Étude de zone, Estimer), `marche_dvf(idu)` secteur (Étude
   de zone, Comparer via fiche), `reference_locale` (Estimer). Deux **jeux** DVF coexistent par ailleurs : géo-DVF Etalab
   (`dvf_mutations*`, 2021→, millésime 2026-S1) et le jeu historique `dvf_mutations_histo` (2014→2020/2021) — horizons et
   périmètres différents, mobilisés ensemble par Estimer et Temps.

3. **« SDP résiduelle / droits à bâtir restants » — trois origines pour la même grandeur.**
   - vue précalculée **`parcel_residuel`** : Blocs, Taxe (prefill `sdp_gabarit`), Patrimoine, Estimer ;
   - **moteur de faisabilité live** (recalcul) : Assemblage, Comparer, Gabarit ;
   - jeu **`p_model_ext_dataset`** : Successions, Patrimoine.
   Rien ne garantit que les trois donnent la même valeur pour une parcelle donnée (ex. Taxe sert `sdp_gabarit=35 m²` lu
   d'une vue, pendant que Gabarit recalcule la capacité à chaud). → cf. `taxe-amenagement.md`, `gabarit.md`, `assemblage.md`, `blocs-fonciers.md`, `successions.md`.

4. **Règles PLU chiffrées — deux représentations de la même règle.** L'emprise %, les hauteurs et les reculs sont servis
   par des **YAML curés à la main** (`config/plu_destinations/*.yaml`, `config/plu_zonage.yaml`) pour Gabarit, Taxe et
   Comparer, tandis que l'outil **PLU (Annuaire)** sert le **verbatim** du règlement (`plu_reglement_extrait`). Les deux
   peuvent diverger (valeur curée ≠ texte opposable) et aucun contrôle ne les rapproche. → cf. `gabarit.md`, `plu.md`, `taxe-amenagement.md`.

5. **Patrimoine : trois comptes de « parcelles détenues » pour un même SIREN** (1833 via JOIN `parcels` vs 1871 en count
   brut), affichés dans le même écran sans réconciliation. → cf. `patrimoine.md`.

6. **DFI (documents de filiation) — utilisée par un outil, pas par les autres qui pourraient.** Temps lit `dfi_filiation`
   (découpes/filiation) ; Successions et Patrimoine, dont c'est le domaine (transmission), ne l'utilisent **pas** (âge
   dirigeant via RNE seulement, PM uniquement). → cf. `temps.md`, `successions.md`, `patrimoine.md`.

7. **Contiguïté — constante partagée, cohérente (contre-exemple positif).** `ADJ_BUFFER_M = 0,5 m` est importée
   d'Assemblage par Blocs ; la classification PPR passe par la **même** fonction SQL `labuse_ppr_couleur` dans Risques et
   Gabarit. Ces deux grandeurs-là ne divergent pas — à préserver.

## Réserves d'audit
- Backend mono-worker instable sous charge : quelques sorties « live » manquent (ex. variante PLU `search&zone=N`), signalées dans les fiches concernées.
- Les parts « sourcé / estimé » sont des **estimations d'auditeur** (ordre de grandeur), pas des mesures.
- Les numéros de ligne cités l'ont été à la date de l'audit (HEAD `97a477e19`) ; un rebase les décalera.
