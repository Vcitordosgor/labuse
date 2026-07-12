# M5.1 — Lot 4.2 · Audit fraîcheur des sources (12/07/2026)

Audit lecture seule : millésime/date en base (`postgresql://openclaw@localhost/labuse`) vs dernière version publiée par le producteur, vérifiée **en ligne** le 12-13/07/2026. Aucune ingestion, aucun write en base. CSV compagnon : `fraicheur-sources.csv`.

## Tableau

| Source | En base | Producteur (dernière version) | URL de vérification | Écart | Verdict |
|---|---|---|---|---|---|
| DVF | max mutation 31/12/2025 (29 565) | Publication du 20/04/2026, couvre jusqu'au 31/12/2025 ; prochaine : oct. 2026 | [data.gouv DVF géoloc.](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/) | aucun | **À JOUR** |
| DVF histo | max 31/12/2020 (110 463) | millésimes 2021-2025 portés par `dvf_mutations` | [files.data.gouv geo-dvf](https://files.data.gouv.fr/geo-dvf/latest/csv/) | aucun (découpage volontaire) | **À JOUR** |
| Sitadel (SDES Dido) | max 30/05/2026 hors 1 outlier ; sync 10/07 | Diffusion mensuelle, dernière MAJ SDES 01/06/2026 (fin avril 2026) ; ancien jeu data.gouv **archivé** (migré Dido) | [SDES](https://www.statistiques.developpement-durable.gouv.fr/donnees-des-permis-de-construire-et-autres-autorisations-durbanisme) | aucun | **À JOUR** |
| BODACC | max annonce 02/07/2026 ; sync 05/07 | Données DILA traitées le 10/07/2026, MAJ quotidienne | [opendatasoft DILA](https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/) | ~8 j | **À RAFRAÎCHIR** (cron) |
| Fichiers fonciers Cerema | millésime non tracé (data_sources id 27) | **Dernier millésime : 2025** | [datafoncier.cerema.fr](https://datafoncier.cerema.fr/fichiers-fonciers) | 2025 dispo | **À RAFRAÎCHIR** |
| DGFiP PM | max millésime 2024 (461 570) | **Millésime 2025 publié** | [data.gouv PM](https://www.data.gouv.fr/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales) | 1 millésime | **À RAFRAÎCHIR** |
| DPE ADEME | max étab. 03/07/2026 ; sync 12/07 | MAJ 08/07/2026, hebdomadaire | [data.ademe.fr dpe03existant](https://data.ademe.fr/datasets/dpe03existant) | négligeable | **À JOUR** |
| RNIC | ingéré 10/07/2026 (2 220) | MAJ **quotidienne** depuis avril 2026 ; dernière 11/07/2026 | [data.gouv RNIC](https://www.data.gouv.fr/fr/datasets/registre-national-dimmatriculation-des-coproprietes/) | 1-2 j | **À JOUR** |
| Filosofi carreaux 200 m | millésime 2021 (14 773) | Dernier millésime carroyé publié = **Filosofi 2021** | [INSEE 8735162](https://www.insee.fr/fr/statistiques/8735162?sommaire=8735243) | aucun | **À JOUR** |
| Cadastre Etalab | parcels updated_at 29/06/2026 | Édition **2026-06-01** publiée le 29/06/2026 (la plus récente) | [cadastre.data.gouv.fr](https://cadastre.data.gouv.fr/data/etalab-cadastre/) | aucun | **À JOUR** (prochaine ~sept. 2026) |
| BD TOPO IGN | ingestions 28/06-01/07 (édition avril 2026 probable) | Calendrier 2026 : avril (261), **juillet (262)**, oct., janv. ; data.gouv MAJ 03/07/2026 | [data.gouv BD TOPO](https://www.data.gouv.fr/datasets/bd-topo-r) | édition juillet en diffusion | **À RAFRAÎCHIR (mineur)** |
| QPV | QPV 2024 ; sync 05/07 | Jeu MAJ 16/01/2026 ; QPV 2024 (métropole) + **QPV 2025 pour les outre-mer** (en vigueur 01/01/2025) | [data.gouv QPV](https://www.data.gouv.fr/fr/datasets/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/) | 974 = génération 2025 applicable | **À VÉRIFIER/RAFRAÎCHIR** |
| Cartofriches | sync 05/07/2026 | MAJ 15/06/2026, ~trimestrielle | [data.gouv Cartofriches](https://www.data.gouv.fr/fr/datasets/sites-references-dans-cartofriches/) | aucun | **À JOUR** |
| Géorisques (ICPE, cavités, MVT, SSP, aléas) | ingestions 30/06-10/07 | ICPE quotidien ; BDMvt/BDCavités (BRGM) en continu | [georisques.gouv.fr](https://www.georisques.gouv.fr/donnees/bases-de-donnees) | quelques jours | **À JOUR** (routine) |
| ABF / Mérimée | sync 05/07/2026 | **POP** enrichie quotidiennement ; ⚠ le jeu data.gouv « immeubles protégés MH » est figé au **29/09/2017** | [pop.culture.gouv.fr](https://pop.culture.gouv.fr/) | aucun si source = POP | **À JOUR** (éviter le jeu data.gouv 2017) |
| OCS GE | ingéré 28/06 (millésime 974 non tracé) | Millésimes 2017-2020 et 2021-2023 ; socle DROM achevé sept. 2025 ; 3e millésime 2024-2026 en cours | [ign.fr OCS GE](https://www.ign.fr/institut/occupation-du-sol-francais) | inconnu | **À VÉRIFIER** (tracer le millésime) |
| RGE ALTI | pas de last_sync | MAJ **arrêtées en 2024** ; remplacé par **MNT LiDAR HD** (DROM sauf Guyane d'ici 2026) | [cartes.gouv.fr MNT LiDAR HD](https://cartes.gouv.fr/aide/fr/partenaires/ign/observations-regulieres-territoire/relief/mnt-lidar-hd/) | produit gelé | **SOURCE MORTE/MIGRÉE** → MNT LiDAR HD |

## Anomalie Sitadel — date future (résolue)

`max(date) = 2026-08-17` provient d'**une seule ligne** sur 50 043 : `permit_id 9744122500519`, DP « locaux », `raw->>'etat' = 2`, `raw.src = "SDES Dido — Sitadel3 (974)"`. Le max réel hors outlier est **2026-05-30**, cohérent avec la diffusion mensuelle SDES. La date future arrive telle quelle de la source (erreur de saisie du producteur sur la date d'autorisation) — **pas un champ mal mappé**. Recommandation : garde-fou `date <= now()` au chargement ou flag qualité.

## Migrations de portails constatées

- Sitadel : le jeu data.gouv historique est archivé → source vivante = **SDES Dido** (déjà la source utilisée en base).
- IGN : geoservices.ign.fr redirige (301) vers **cartes.gouv.fr** ; fiches catalogue en JS non fetchables — vérifications faites via data.gouv et pages d'aide IGN.
- EDF SEI et ORE : migrés vers **Data Fair** (déjà connu, pour mémoire).
- Monuments historiques : le jeu data.gouv est mort (2017) ; la source vivante est **POP**.

## Synthèse (priorités)

1. **DGFiP PM millésime 2025** publié : à ajouter au panel 2021-2024 (`pm_proprietaires_millesimes`) — priorité n°1, un point annuel de churn en jeu.
2. **Fichiers fonciers Cerema millésime 2025** disponible : tracer le millésime actuellement en base puis planifier la montée de version (idéalement couplée au prep-recompute).
3. **QPV 974** : la génération applicable aux outre-mer est **QPV 2025** (pas 2024) — vérifier la génération de la couche en base avant tout usage fiscal/scoring.
4. **RGE ALTI gelé** par l'IGN : acter la bascule vers MNT LiDAR HD (le MNH LiDAR HD est déjà exploité côté végétation) et marquer la source 6 comme migrée dans `data_sources`.
5. **BODACC** (~8 j de retard, quotidien chez DILA) et **BD TOPO édition juillet 2026** : rafraîchissements de routine ; pour BD TOPO, coupler à la ré-ingestion voirie déjà au backlog. Tout le reste (DVF, Sitadel, DPE, RNIC, Filosofi, cadastre, Cartofriches, Géorisques, Mérimée/POP) est à jour.
