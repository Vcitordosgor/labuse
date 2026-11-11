# PLU-VEILLE-1 — quand une commune publie un nouveau PLU, que fait LABUSE ?

**Mandat** : audit LECTURE SEULE — comment LABUSE détecte et traite une nouvelle version de PLU (ou une
modification) publiée au Géoportail de l'urbanisme (GPU) pour une commune de La Réunion. Aucune correction.
**Branche** `audit/plu-veille-1` · base `585d3dd8e` (worktree `~/Desktop/labuse-fraicheur-fix`).
**Prod** : lue en ssh (`labuse-vps`, `sudo -u postgres psql labuse`), lecture seule, requêtes légères.
**En ligne** : API Carto GPU (`apicarto.ign.fr/api/gpu`) interrogée pour le cas Saint-Denis.
**Date** : 10/11/2026 (heure serveur Indian/Reunion, UTC+4).

---

## 0. Résumé exécutif

Il n'y a **pas un** mécanisme mais **cinq étages**, dont trois sont **manuels** et un **aveugle au cas le
plus courant** :

1. **Détection** : une sonde quotidienne regarde `totalFeatures` (le **nombre de documents** GPU d'une
   commune). Elle voit un document **apparaître** (0 → 1), mais **pas une version qui en remplace une
   autre** (1 → 1) — qui est pourtant le cas d'une révision/modification sur une commune déjà dotée d'un
   PLU. Le vrai lieu où le nouveau millésime arrive est le catalogue `config/plu_millesimes.yaml`,
   **rafraîchi à la main** (campagnes d'extraction), pas par un job.
2. **Zonage** : classe **B (structurant)** → **jamais injecté automatiquement**. Mis à jour **sur clic**
   de Vic (ingestion GPU → `build-mvt` → `promote`).
3. **Règles chiffrées** : il existe un **drapeau de péremption** (`a_relire` → « à revérifier ») qui
   compare l'idurba du catalogue à celui gravé au calibrage — mais il est **réservé à l'admin** (Circuit),
   ne couvre que le calibrage *destinations*, et **ne fait PAS basculer les parcelles en « À vérifier »**
   côté client : pendant le délai de re-calibrage **les anciennes règles continuent d'être servies**.
4. **Procédures en cours** (révision/modification/enquête) : **suivies et affichées** côté client
   (registre curaté `config/veille_plu.yaml`, M41), mais alimentées **manuellement** (~trimestriel).
5. **Preuve Saint-Denis 05/08/2026** : le zonage servi EST la version du 05/08 (ingéré le 14/09), les
   règles *destinations* ont été relues le 03/09 — **mais** les **prescriptions** (ER/EBC/DPU) sont restées
   sur l'**ancienne** version (23/04, ingérées le 29/06), et le client n'a eu **aucun signal** pendant les
   ~5 semaines de latence manuelle. La détection de la bascule n'est pas venue de la sonde (aveugle) mais
   d'une campagne manuelle.

---

## 1. Détection — quel signal, quel job, en combien de temps

### 1.1 Le signal quotidien : `totalFeatures` (nombre de documents)
La sonde des sources (`sonde-sources`, `src/labuse/jobs.py:426`, cron `0 3 * * *` = **07:00 Réunion**,
quotidien) interroge l'API Carto GPU `document?partition=DU_<insee>` et lit le sélecteur **`totalFeatures`**
(`src/labuse/sentinelle.py` SEED) :
- `Urbanisme PLU/GPU (API Carto)` → `DU_97413` (Saint-Leu, témoin d'**apparition** du PLU révisé) ;
- `GPU — emplacements réservés` / `droit de préemption urbain` → `DU_97411` (Saint-Denis) ;
- `GPU — espaces boisés classés` → `DU_97415` ; `GPU — zonages d'assainissement` → `DU_97404` ;
- `PEB` → `DU_97416`.

**Le trou de fond** : `totalFeatures` est un **compteur de documents**. Une commune qui n'a **aucun**
PLU au GPU passe 0 → 1 (détecté). Une commune qui **remplace** son PLU par une révision/modification reste
**1 → 1** : le compteur ne bouge pas, l'**idurba change** (ex. `97411_PLU_20260423` → `97411_PLU_20260805`)
mais la sonde ne le voit pas. Vérifié en ligne le 10/11 : `apicarto.ign.fr/api/gpu/document?partition=DU_97411`
rend **`totalFeatures = 1`** (idurba `97411_PLU_20260805`) — la même valeur « 1 » qu'avec l'ancien document.
Le sélecteur choisi (compte) est donc **structurellement aveugle au remplacement de version**, qui est le
cas usuel d'une révision. (Les sondes qui lisent une **empreinte** de la réponse entière — ex.
`SUP — assiettes GPU`, selecteur `None` — captureraient l'idurba ; les sondes PLU, elles, lisent le compte.)

### 1.2 Le job mensuel `sync-gpu` est inerte sur le zonage
`sync-gpu` (`jobs.py:475`, cron `0 0 15 * *` = **04:00 le 15**, mensuel) est titré « Diff PLU des 24
communes ». Son implémentation (`src/labuse/jobs_impl.py` `sync_gpu`) ne fait QUE :
```python
r = veilles_mod.evaluer_toutes(ctx.db)   # veilles foncières (permis/DVF/zonage SUR parcelle suivie)
ctx.compte(..., note="diff PLU délégué au pipeline GPU existant ; événements générés")
```
Il ne **compare aucun idurba**, ne **ré-ingère aucun zonage**, ne touche ni `plu_millesimes.yaml` ni
`parcel_zone_plu`. La note « délégué au pipeline existant » décrit un pipeline **manuel** (§2).

### 1.3 Là où le millésime arrive réellement : le catalogue, à la main
Le point de vérité du millésime servi est **`config/plu_millesimes.yaml`** (`idurba` + `date_mairie` +
`statut` par commune). Son en-tête le dit : *« ré-extractions M32 (05/08) + confrontation idurba M40 »* —
c'est une **campagne manuelle d'extraction GPU** qui pose le nouvel idurba, pas un job. Cadence annoncée :
« révisions (périodique, pas de fréquence fixe) ».

**Délai** : pour une **apparition** de document → la sonde quotidienne lève une cloche sous 24 h. Pour un
**remplacement de version** (le cas courant) → **non borné** : il dépend de la prochaine campagne manuelle
d'extraction. Aucun job ne garantit la détection d'une révision sur une commune déjà dotée d'un PLU.

---

## 2. Mise à jour du zonage — automatique, sur clic, ou pas du tout ?

**Sur clic (manuel).** Le zonage PLU/GPU est **classe B — STRUCTURANT** : `src/labuse/autonomie.py:48`
`"Urbanisme PLU/GPU (API Carto)": ("B", "zonage opposable — tranche la constructibilité")`. La doctrine
AUTONOMIE-1 (`injection_nuit`, jobs_impl) **n'injecte jamais** une source classe B la nuit — elle attend le
clic de Vic. La chaîne réelle :
1. `labuse ingest …` (ou `ingest-plu`) ré-ingère les zones GPU → `spatial_layers` (`kind='plu_gpu_zone'`) ;
2. `build_parcel_zone_plu` (`src/labuse/api/tiles.py:78`) reconstruit la table dérivée servie
   `parcel_zone_plu` (zone dominante par parcelle). Un cache de signature `parcel_zone_plu_version`
   (`tiles.py:74`) fait rebâtir cette table **quand les entrées `spatial_layers` changent** — mais
   l'ingestion de ces entrées est, elle, **manuelle** ;
3. `build-mvt` puis `promote` pour servir le nouveau run.

Aucune de ces étapes n'est planifiée pour le PLU. **Preuve Saint-Denis** : la version 05/08 n'a été ingérée
que le **14/09** (§5) — un délai incompatible avec une mise à jour automatique.

---

## 3. Les règles chiffrées calibrées à la main — « à revalider » ? parcelles « À vérifier » ?

Il y a **deux** jeux de calibrage, sur des versions **différentes**, et un drapeau de péremption **partiel**.

### 3.1 Le calibrage SERVI (règles chiffrées) : `config/plu_destinations/`
Les valeurs chiffrées servies à l'analyse viennent de `plu.destinations.regles_commune(insee)`, qui lit
`config/plu_destinations/<insee>_<slug>.yaml` (`faisabilite/zonage.py:6` : « les VALEURS chiffrées viennent
des `regles` servies par le module `plu.destinations` »). Chaque fichier grave la version calibrée :
`meta.document_gpu` (idurba) + `meta.millesime` + `meta.lu_le`.

**Le drapeau de péremption existe** : `destinations.etat_commune` (`src/labuse/plu/destinations.py:186-241`)
compare l'`idurba` du catalogue (`plu_millesimes.yaml`) à l'`document_gpu` gravé au calibrage. Si le
catalogue est **plus récent** → état **`a_relire`** = **« à revérifier »** (`CALIBRAGE_ETAT_LABEL`,
destinations.py:745). Le sens est géré : un calibrage lu sur un document **plus frais** que le catalogue
n'est pas périmé (c'est le catalogue qui est en retard).

**Mais ce drapeau est réservé à l'ADMIN** : il est exposé par `calibrages_gpu()` → `api/app.py:8292`
(route admin) et `api/dashboard.py:1534` → front **`admin/Destinations.tsx`** (« à relire — nouvelle
version de PLU servie ») et `admin/circuit/Detail.tsx`. **Aucune** surface **client** (fiche/analyse) ne
porte cet état (grep `frontend/src/components/fiche` + `scenarios.py` : zéro référence à `idurba`/calibrage).

### 3.2 Les parcelles ne basculent PAS en « À vérifier »
`src/labuse/scenarios.py` (le moteur d'analyse) **ne contient aucune** référence à `idurba`,
`plu_millesimes`, calibrage ni « à revalider » (grep vide). Les statuts « À vérifier » / « Calcul à
compléter » de l'analyse tiennent à des causes **géométriques / legacy / donnée manquante**, **jamais** à
un changement de version de PLU. Conséquence : **pendant tout le délai** entre la publication GPU et le
re-calibrage manuel, **les anciennes règles chiffrées continuent d'être servies au client**, et aucune
parcelle ne passe « À vérifier ». Le drapeau `a_relire` prévient Vic ; il ne protège pas le client.

### 3.3 Le calibrage AUDIT : `config/calibrage/` (snapshots, non servis)
`config/calibrage/calibration_<commune>.yaml` + `zonage_<commune>.yaml` sont des **artefacts de session de
calibrage** (snapshot de zones + notes), pas la source servie (`zonage_saint_denis.yaml` en-tête : « Les
RÈGLES chiffrées par zone ne sont PAS en DB »). Ils ne sont lus qu'en marge (`filtre_bati.py:36` = liste
des communes à fiche ; `au_ouverture.py:70` lit le fichier **unique** `au_ouverture_planchers.yaml`) et par
les tests vérité-terrain. **Aucun drapeau** ne couvre leur péremption : ils peuvent diverger en silence
(cas Saint-Denis : encore `20260423` alors que le servi est `20260805`).

**Réponse à la question** : oui, les règles *destinations* sont marquées **« à revérifier »** — mais
**seulement à l'admin**, seulement pour ce jeu-là, et **sans** faire passer les parcelles en « À vérifier » :
**on continue de servir les anciennes règles** jusqu'au re-calibrage manuel.

---

## 4. Les procédures en cours (révision / modification / enquête) — suivies et affichées ?

**Oui, côté client — mais alimentées à la main.** Registre curaté `config/veille_plu.yaml` (M41), squelette
**Sudocuh** (data.gouv, Licence Ouverte), chair curatée, rafraîchi par passe **trimestrielle**
(`scripts/veille_plu_check.py`). Schéma strict par commune : `procedure`, `stade`, `date_acte`,
`debat_padd`, `confiance` (**SOURCE** | DEDUIT | ABSENT). Doctrine : **seules** les entrées `confiance=SOURCE`
sont servies en vigilance ; une **modification** n'a pas de PADD → pas de sursis L.153-11.

Logique : `src/labuse/veille_plu.py` — `procedure_active()`, `vigilance_sursis()` (base légale L.153-11 /
L.424-1, servie **uniquement** si `debat_padd` sourcé), `communes_en_procedure()`. Affichage **client** :
`frontend/src/components/outils/PluAnnuaire.tsx` (badge « révision »), `VerifProcedure.tsx` (IDU → stade +
conséquences), `ProcedureChangement.tsx` (ouverture de zone AU) + la fiche commune.

**Limite** : alimentation **manuelle trimestrielle** — aucun fetch automatique de Sudocuh ni des arrêtés
d'enquête ; `a_reverifier()` (seuils 30/90 j) signale les entrées vieillies, mais ne va pas les chercher.
Exemple vivant (plu_millesimes.yaml) : Saint-Leu (`97413`, révision S2 2026) et Saint-André (`97409`,
révision en cours) sont en `opposabilite_en_attente` — suivis, non servis comme opposables.

---

## 5. Preuve sur un cas réel — le PLU de Saint-Denis du 05/08/2026

| Étape | Constat (source) | Date |
|---|---|---|
| GPU en ligne | `document?partition=DU_97411` → **`totalFeatures = 1`**, idurba **`97411_PLU_20260805`** (remplace `97411_PLU_20260423` du 23/04, publié 18/06) | 10/11 (live) |
| Sonde `totalFeatures` | 1 (avant) → 1 (après) : **le remplacement n'est PAS détecté** par la sonde quotidienne | — |
| Catalogue | `config/plu_millesimes.yaml` : `97411` → idurba `97411_PLU_20260805`, `date_mairie 2026-08-05`, `statut a_jour` — posé par la **campagne manuelle M32 (05/08)** | 05/08 |
| Règles *destinations* | `config/plu_destinations/97411_saint_denis.yaml` : `document_gpu 97411_PLU_20260805`, `lu_le 2026-09-03` → `etat_commune('97411') = calibree` (« à jour »), 114 règles | **03/09** |
| Zonage servi (prod) | `spatial_layers` `plu_gpu_zone` idurba **`97411_PLU_20260805`**, 259 zones, `created_at` **2026-09-14** | **14/09** |
| **Prescriptions (prod)** | `spatial_layers` `plu_gpu_prescription` idurba **`97411_PLU_20260423`** (ANCIEN), `created_at` **2026-06-29** — **pas ré-ingérées** | 29/06 |
| Calibrage audit | `config/calibrage/calibration_saint_denis.yaml` + `zonage_saint_denis.yaml` : encore idurba **`97411_PLU_20260423`** (snapshots non servis, stale) | 26/07 |

**Lecture** : le zonage **et** les règles chiffrées *destinations* de Saint-Denis sont bien servis sur la
version du **05/08/2026** aujourd'hui — mais au prix d'une chaîne **100 % manuelle** (campagne M32 → relecture
destinations 03/09 → ré-ingestion zonage 14/09), soit **~5 semaines de latence** pendant lesquelles le client
a vu l'ancienne version **sans aucun signal** « à vérifier ». Et **les prescriptions (emplacements réservés,
EBC, DPU) restent sur l'ancien PLU du 23/04** : une mise à jour **partielle** (zones oui, prescriptions non)
qui sert des couches **incohérentes entre elles**. La détection n'est pas venue de la veille automatique
(aveugle au 1 → 1) mais d'un geste humain.

---

## 6. Les trous, classés par gravité

### GRAVE
1. **Sonde aveugle au remplacement de version.** Le sélecteur `totalFeatures` (compte de documents) ne
   change pas quand une révision remplace un PLU existant (1 → 1) — le cas le plus courant. La veille
   automatique **ne détecte pas** la révision/modification d'une commune déjà dotée d'un PLU ; seule une
   **apparition** (0 → 1) est vue. Détection réelle = campagne manuelle (`plu_millesimes.yaml`).
   *(sentinelle.py SEED PLU ; live DU_97411 = 1.)*
2. **Mise à jour partielle du zonage.** Les **prescriptions** (ER/EBC/DPU) ne sont pas ré-ingérées avec les
   **zones** : Saint-Denis sert `plu_gpu_zone` 05/08 **et** `plu_gpu_prescription` 23/04 — des couches du
   même PLU dans deux versions. Rien ne garantit la cohérence zones ↔ prescriptions après une bascule.
3. **Aucun signal client pendant la latence.** `scenarios.py` n'a aucun lien version-de-PLU → les parcelles
   **ne passent jamais « À vérifier »** quand le PLU change ; on sert l'ancien zonage/les anciennes règles
   pendant des semaines **sans prévenir le client**. Le seul drapeau (`a_relire`) est **admin-only**.

### MOYEN
4. **Drapeau de péremption partiel et admin-only.** `etat_commune`/`a_relire` ne couvre que le calibrage
   *destinations* (`config/plu_destinations`) — ni les prescriptions, ni `config/calibrage/*`, ni le client.
5. **Chaîne entièrement manuelle, délai non borné.** Classe B → ingestion/calibrage/`build-mvt`/`promote`
   au clic ; `sync-gpu` est **inerte sur le zonage** malgré son titre. Rien ne borne le délai
   publication → service.
6. **Procédures alimentées à la main (trimestriel).** Pas de fetch automatique Sudocuh/arrêtés ; un
   changement de stade ou une enquête publique peut rester invisible jusqu'à la prochaine curation.

### MINEUR
7. **`config/calibrage/*` diverge en silence.** Snapshots d'audit (Saint-Denis encore `20260423`) sans
   drapeau — faible impact (non servis) mais trompeur pour qui les relit.
8. **`statut: a_jour` du catalogue est ambigu.** Il signifie « idurba GPU == idurba catalogue », **pas**
   « tout a suivi » : à Saint-Denis il est « a_jour » alors que les prescriptions et les snapshots de
   calibrage sont restés en arrière.

---

*Fin du rapport. Lecture seule — aucune donnée ni configuration prod/locale modifiée.*
