# GRANDE REVUE AVANT MISE EN LIGNE — RAPPORT

> Mandat GRANDE REVUE (27/08/2026). Branche `audit/grande-revue` (depuis `19f92b86`, qui inclut la
> bascule du run servi `q_v10_m129` → **`q_v11_m137`**, re-run des 24 communes de ce midi : 431 663
> parcelles, canari/score-v2/build-mvt/purge vérifiés). Doctrine intacte : Sourcé/Estimé/Absent,
> moteur unique, jamais de faux positif — **aucun chiffre servi ne change dans ce mandat** (seule
> exception encadrée : le re-run conditionnel R10).
>
> Gravités : 🔴 bloquant / faille · 🟠 durcissement recommandé · 🟡 dette / constat documenté.
> Findings RV-001→. Base de vérification empirique : `labuse` (prod locale) en lecture + `labuse_test`
> pour les comptes de test `[REVUE-TEST]` (purgés en fin).

---
## R1 — FRAÎCHEUR DES 58 SOURCES

Méthode : inventaire `data_sources` (58 affichées) × vérification en ligne des millésimes chez les
producteurs (data.gouv, SDES, ADEME, cadastre.data.gouv, IGN, Sudocuh, DILA, INPI, BRGM) × croisement
avec les commandes d'ingestion CLI et les crons installés. Le run servi `q_v11_m137` (re-run de ce
midi) a consommé l'état actuel de la base.

### Sources cadencées / à flux vivant (vérifiées en ligne)

| Source | Ingéré | Disponible amont (vérifié) | Retard | Commande | Cascade |
|--------|--------|---------------------------|--------|----------|---------|
| **géo-DVF Etalab** | 2021–2025 (horizon déc. 2025) | `latest/csv` = 2021→2025, horizon oct. 2025 · prochain oct. 2026 | **Non** | `refresh-dvf` (cron dvf) | oui (prix) |
| **Cadastre PCI (DGFiP)** | « latest » | juin 2026 publié 01/07 · `latest` suit | **Non** | API Carto (live) | oui (parcelles) |
| **SITADEL (SDES)** | 2026-06 | fiche MàJ 25/08 ; période exacte non affichée en ligne | Inconnu | `ingest-permits` (cron sitadel) | non (événements) |
| **DPE ADEME** | horizon 03/07/2026, hebdo | flux continu vivant (data.ademe.fr) | **Non** | `ingest-dpe` (cron dpe) | non |
| **BAN** | horizon 11/07/2026 | flux quotidien vivant | **Non** | `ingest-ban` (cron ban) | non |
| **BODACC (DILA)** | horizon 02/07/2026 | flux quotidien vivant | **Non** | `ingest-bodacc` (cron bodacc) | non (features) |
| **INPI RNE** | 06/07/2026 | flux quotidien vivant | **Non** | `ingest-inpi-rne` | non (features PM) |
| **Géorisques (BRGM)** | 13/08/2026 | flux vivant par base (API) | **Non** | `ingest-georisques` | oui (spatial_layers PPR/ICPE) |
| **Sudocuh (DGALN)** | état 31/12/2024 | dernier état annuel = 31/12/2024 | **Non** | manuel | non |
| **IGN BD TOPO V3 (bâti)** | mi-2025 | **éd. avril (261) + juillet (262) 2026 publiées** | **OUI** | ⚠ pas de commande CLI simple | **oui (bâti→résiduel)** |

### Les 48 autres sources

Millésimées statiques au dernier état publié (INSEE RP2022/2023, Filosofi 2021, IRIS 2024, ZNIEFF
29/08/2025, QPV 2024, ZFANG décret 05/2026, FRR 07/2024, Cartofriches, 50 pas, classement sonore
2023, INPN 2021/2025, LiDAR HD 25/06/2025, etc.) ou flux/proxy live (API Carto GPU/PLU, SUP, SIRENE,
Recherche d'entreprises, OSM/Overpass, GTFS PAN màj 08/2026). **Aucun retard ingérable détecté** :
soit au dernier millésime publié, soit flux vivant déjà ingéré (juillet–août 2026), soit source
manuelle/licence en attente (Fichiers fonciers Cerema, VRD/SPANC) → constat seulement.

### Décision R1 (arbitrages)

- **Aucune ingestion lancée.** Les sources cascade au sens strict (DVF, cadastre, zonage PLU/GPU,
  Géorisques) sont **à jour** ; les flux vivants (DPE/BAN/BODACC/INPI) sont frais (ingérés mi-août par
  les crons) et **non cascade** — les relancer créerait un delta de données non re-scoré, contraire à
  « aucun chiffre servi ne change ». → constat.
- **RV-001 🟡 — BD TOPO en retard (édition juillet 2026 vs bâti ingéré mi-2025).** C'est la seule
  source **cascade** ayant bougé (le bâti alimente `parcel_residuel` → SDP → score de cascade, cf.
  `residuel.py:35` `kind='batiment'`). **Mais** il n'existe **pas de commande d'ingestion BD TOPO
  simple/libre** au CLI (le bâti vit dans `spatial_layers` via un pipeline WFS non trivial ; la seule
  commande bâti est `ingest-cosia`, autre source). Ré-ingérer le bâti de toute l'île + recalculer le
  résiduel + re-scorer, juste avant mise en ligne, est un **chantier DONNÉE dédié** hors périmètre
  d'une revue. → **Constat documenté, pas d'ingestion.**
- **Conséquence pour R10 : aucune source cascade n'a été ré-ingérée → R10 ne se déclenche pas** (le
  bâti actuel est cohérent avec le résiduel recalculé ce midi). Détaillé en R10.
