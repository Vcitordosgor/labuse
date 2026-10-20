# PURGES-20-10 — gestes de nettoyage en prod, avant déploiement

**Date :** 2026-10-20 · **Branche :** `ops/purges-20-10` (worktree `~/Desktop/labuse-purges`, **sans merge**)
**Prod :** VPS `labuse-vps` → base `labuse` (PostgreSQL 18.4, hôte `vps-5563949c`)
**Périmètre :** purges de données uniquement. **Aucun code modifié**, ni `deploy.sh`, ni `deploy_app.sh`.
**Sauvegardes :** `/var/backups/labuse/purges-20261020/` (sur le VPS), lues via `postgres`, écrites via `labuse`.
Chaque `DELETE`/`UPDATE` joué dans une transaction, `statement_timeout` posé, après go explicite de Vic, une cible à la fois.

## Note d'environnement (important)
Le mandat visait « la prod » via `. /etc/labuse/labuse.env`. Ce fichier **n'existe pas** sur le Mac
`air-de-victor.home`, dont le seul PostgreSQL joignable est le `localhost/labuse` **local** (à ne jamais toucher).
La prod est le **VPS `labuse-vps`** ; toutes les requêtes ci-dessous ont été jouées via
`ssh labuse-vps "sudo -u postgres psql -d labuse …"`. La base locale du Mac n'a pas été touchée.

Référence des SQL d'origine : `docs/audit-2026-10/chasse-orfevre-1/PURGES-PROD.md` (rédigé sur des ids de **dev**,
qui ne valaient rien en prod — chaque cible a été re-vérifiée en direct).

---

## Récapitulatif

| # | Purge | Visé (prod) | Supprimé / modifié | Sauvegarde |
|---|---|---:|---:|---|
| 1 | Mails de recette en file (`mail_queue`) | **0** | 0 (rien à faire) | — |
| 2 | `consultation_log` — trafic de banc `ip:12ca…` | 5 442 | **DELETE 5 442** | `purge2_consultation_log_ip12ca.csv` |
| 3 | Notes `[GB-TEST]` (`pipeline_entries`) | 38 | **DELETE 38** | `purge3_pipeline_entries_gbtest.csv` |
| 4 | Doublons du Radar (`pige_depots` par hash) | 94 | **DELETE 94** | `purge4_pige_depots_complet.csv` |
| 5 | Rattrapages ORF-14/15/16 (`UPDATE`) | 4327 / 136 / 2 | **UPDATE 4327 + 136 + 2** | `purge5_orf14/15/16…csv` |
| — | 481 dates INPI aberrantes | 481 | **0 en base — signalement producteur** | `inpi_481_dates_aberrantes.csv` |

---

## 1. Mails de recette en file — RIEN À FAIRE
`mail_queue` en prod = **11 lignes, toutes `recu`** ; **0** en `a_rejouer`/`en_attente`. Les deux prédicats de
`PURGES-PROD` (fenêtre 16/10 ; dû vers compte inexistant) renvoient **0**. Les « 12 mails » étaient des ids de dev.
(La colonne `sujet` du SQL d'origine n'existe même pas en prod — c'est `template_nom`.) Aucune suppression, aucune sauvegarde.

## 2. `consultation_log` de l'audit → trafic de banc de charge
La fenêtre « angle C du 18/10 » = **0 ligne** en prod (l'audit écrivait sur dev). Découverte à côté : le hash d'IP
**`ip:12ca17b49af2289436f3`** = **5 442** consultations (juillet–août) — un banc de charge (602 sur parcelles forgées
`QA0000…QA0299`/`XX9999` + 4 414 sur de vraies parcelles vues ~90-100× chacune). Décision Vic : **option « toute l'IP »**.
Garde-fous vérifiés avant go : `consultation_log` n'a aucune colonne compte/user (trafic anonyme), le hash n'apparaît pas
dans `comptes`, et **aucune ligne après le 27/08** (0 après fin août). Sauvegarde des 5 442 lignes, puis :
```sql
DELETE FROM consultation_log WHERE sujet = 'ip:12ca17b49af2289436f3';   -- DELETE 5442
```
**Après :** `consultation_log` 6 380 → **938** ; `ip:12ca…` → **0**.

## 3. Notes `[GB-TEST]` (`pipeline_entries`)
**38** lignes en prod. Répartition : **36 sur `LABUSE (admin)`** (compte interne, sans Stripe) + **2 orphelines** (`compte_id` NULL).
**0 sur Stéphanie JAMMES** (compte 36, vrai client) ; **0 sur un compte Stripe**. Notes manifestement synthétiques
(« prospect audit — a supprimer », « AAAA… », « an-pipeline-769894 »). Sauvegarde des 38 lignes, puis :
```sql
DELETE FROM pipeline_entries WHERE notes LIKE '%[GB-TEST]%';   -- DELETE 38
```
**Après :** `[GB-TEST]` → **0** ; les **4** lignes de pipeline de Stéphanie intactes.

## 4. Doublons du Radar (`pige_depots`)
`pige_depots` = journal de dépôts (les annonces vivent dans `pige_biens`/`pige_annonces`). **94** lignes en double
(même `hash`, re-lectures `nb_nouvelles=0`), archive adressée par contenu (`…/<hash>.html`, un seul fichier par hash).
Vérifié avant go : `nouvelles_sur_supprimees = 0` (aucune annonce nouvelle perdue) ; **aucune FK** ni colonne `depot_id`
ne référence `pige_depots.id` (rien à repointer). Le volet `event_log 'pige:%'` = **0 ligne** (no-op). Sauvegarde de la table
complète (133), puis :
```sql
DELETE FROM pige_depots a USING pige_depots b
WHERE a.hash = b.hash AND a.hash <> '' AND a.id > b.id;   -- DELETE 94
```
**Après :** `pige_depots` 133 → **39** (= 39 hashs distincts, 0 doublon).
**Index uniques laissés au boot** (self-healing ORF-09) : non créés ici, conformément à la décision Vic.

## 5. Rattrapages ORF-14/15/16 (`UPDATE`, exécutés un par un)
Sauvegarde de l'état *avant* pour les trois cibles, puis :

- **ORF-14 — `piscines.commune`** (backfill depuis la parcelle) :
  ```sql
  UPDATE piscines pi SET commune = p.commune
  FROM parcels p WHERE pi.idu = p.idu AND (pi.commune IS NULL OR pi.commune='')
    AND p.commune IS NOT NULL AND p.commune <> '';   -- UPDATE 4327
  ```
  (filtre `p.commune<>''` resserré p/r au SQL d'origine, pour ne jamais réécrire une commune vide par une vide)
  **Après :** 32 communes vides restantes = exactement les 32 piscines **sans parcelle** correspondante (non corrigeables).

- **ORF-15 — `m10_permit_delais.valide`** (autorisation antérieure au dépôt) :
  ```sql
  UPDATE m10_permit_delais SET valide = false WHERE valide AND date_autorisation < date_depot;   -- UPDATE 136
  ```
  **Après :** 0 incohérent restant.

- **ORF-16 — `score_labuse_runs.n_parcelles`** (recompte, avec garde `EXISTS`) :
  ```sql
  UPDATE score_labuse_runs r
  SET n_parcelles = (SELECT count(*) FROM score_labuse s WHERE s.run_label = r.run_label)
  WHERE EXISTS (SELECT 1 FROM score_labuse s WHERE s.run_label = r.run_label);   -- UPDATE 2
  ```
  **Avant/après :** `q_v16` 1663 → **431663** ; `q_v18` (servi) 1229 → **433229** ; écart **0** sur les deux.

---

## 481 dates de naissance INPI aberrantes — SIGNALEMENT, pas de base touchée
**Décision documentée** (`chasse-invariants-1/RAPPORT-FIX.md`, E-05/E-06) : **signaler au producteur RNE/INPI**, les valeurs
restent **servies « âge inconnu »** (exclues de l'outil Successions et du filtre 70+), **jamais modifiées en base**.
Compte reproduit en prod (lecture seule) : **481** dirigeants `INDIVIDU` à âge `<18` (479, dont une naissance future « 2026-11 »)
ou `>110` (2 : naissances 1911-11 et 1909-03). **Aucun `UPDATE`/`DELETE` joué.**
Livrables : texte prêt à envoyer `INPI-SIGNALEMENT-RNE.md` (dans le dépôt) + liste des 481 cas
`inpi-481-dates-aberrantes.csv` (`siren, representant_id, role_entreprise, date_naissance, age_calcule, motif`
— sans nom/prénom), **conservée hors dépôt dans `~/Documents/LABUSE-INPI/inpi-481-dates-aberrantes.csv`**
(copie identique aussi sur le VPS : `/var/backups/labuse/purges-20261020/inpi_481_dates_aberrantes.csv`,
sha256 `6696b4e8…`).

---

## Fichiers de sauvegarde sur le VPS (`/var/backups/labuse/purges-20261020/`)
| Fichier | Lignes | sha256 |
|---|---:|---|
| `purge2_consultation_log_ip12ca.csv` | 5 442 | `00d46496f7cb8adb314a0764e5403b41b7fbc00573d787938c38e04eb4c70b28` |
| `purge3_pipeline_entries_gbtest.csv` | 38 | `5caca6f39206e9f560e9bb2deb3060aad773496ccde25644d0c5bb5f63b97a01` |
| `purge4_pige_depots_complet.csv` | 133 | `1d94c997282108e5060c7d37820f677c8460d45bf1537c50badb81ca3267a899` |
| `purge5_orf14_piscines_commune_vide.csv` | 4 359 | `e06a73fab5b08909e023583c983876c0e414fbf4fdb065c91f0bfdd023ee10b4` |
| `purge5_orf15_m10_permit_incoherents.csv` | 136 | `cf34d2faf4c4668b09da200db8825874b8c29413bc9fe347851100b4f3d136f5` |
| `purge5_orf16_score_labuse_runs.csv` | 2 | `5a5ea2a5c06e9eba0fe7c9178598e7edcde417c69a7cbd3f667c4e43e9d152c7` |
| `inpi_481_dates_aberrantes.csv` | 481 | `6696b4e8c84bccb481bcf2d2ea934de0ba8cc3989ab3071a978bc7b0040c81e9` |

## Restitution par CSV (si besoin)
Chaque sauvegarde est un `COPY … WITH CSV HEADER` restaurable par `COPY <table> FROM … WITH CSV HEADER`
(après recréation des lignes supprimées). Les `UPDATE` d'ORF-14/15/16 sont réversibles depuis les CSV d'état *avant*.

## Ce qui n'a PAS été fait (volontairement)
- Aucun code, aucun `deploy.sh`/`deploy_app.sh` touché.
- Index uniques ORF-09 (`uq_pige_depots_hash`, `uq_event_log_pige_jour`) **non créés** → laissés au boot (self-healing).
- Section 4 de `PURGES-PROD.md` (ORF-12 résidus de recette, dédoublonnage `event_log`) **hors mandat** / sans objet en prod.
- Les 481 dates INPI **non modifiées** en base (signalement producteur).
- **Branche non mergée.**
