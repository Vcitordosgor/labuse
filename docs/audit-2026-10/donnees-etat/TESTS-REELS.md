# TESTS-REELS.md — trois chaînes rejouées en local, bout en bout

*DONNEES-ETAT-1 Partie 3 · 20/10/2026 · **jamais la base servie**. Tout tourne sur une base jetable `labuse_detest` (créée ici, 78 tables `init-db` + schéma runtime + catalogue `seed-sources`), avec le venv du dépôt principal. Journaux dans `tests/` à côté de ce fichier.*

> **Pourquoi une base jetable et pas la base servie.** La base locale `labuse` (50 Go) **est** la base servie q_v19 ; le disque du Mac n'a que 14 Go libres → pas de clone possible. On a donc monté une base **vide** et rejoué les chaînes dessus. Conséquence honnête : les étages qui ont besoin de la **population de référence** (parcelles, adresses, sociétés) ou de **plusieurs heures de calcul** ne peuvent pas aboutir sur une base vide — c'est dit à chaque fois **où ça s'arrête**.

## Les étages communs à toute chaîne

`détection → À faire → Injecter/Déposer → Calculer → note de version → Basculer → l'écran qui change`

Les trois tests couvrent les **trois types d'entrée** (sonde, cron auto, dépôt manuel) jusqu'à l'ingestion. Les étages **Calculer → Basculer → écran** sont **communs** et **n'ont pas été exécutés** (voir la dernière section — pourquoi, et ce qui se passerait).

---

## Test 1 — type SONDE (détection → À faire → Injecter)

**Source testée** : toutes les sources surveillées (86 interrogées). **Chaîne** : `sonde-sources`.

| Étape | Geste | Résultat réel | Preuve |
|---|---|---|---|
| Amorçage | `seed-sources` + `ensure_source_veille` | 125 sources, **98 lignes de veille** (47 api · 27 témoin · 10 entête · 2 page · 12 rappel) | DB |
| **Détection** | `labuse jobs exec sonde-sources` (vraies requêtes HTTP amont) | **77 ok · 1 nouvelle_version · 4 injoignable · 4 illisible · 12 non sondées (rappel)** | `tests/T1-sonde-exec.log` + `source_veille` |
| → ce qui est détecté | — | **BDNB** : amont `2026-10-05` plus récent que la ligne de base → `nouvelle_version` écrit. Injoignables réels : endpoints OSM/Overpass, BAN PLUS. Illisibles : BODACC API, Géorisques SIS, SCOT, OCS GE | DB |
| **À faire** | lecture `etats_sources.lister_etats` | une source `nouvelle_version` donne `etat='nouvelle_version'` → phrase **« Nouvelle version disponible chez le producteur — à injecter »** (`etats_sources.py:92`) → ligne **Injecter** (`circuit_resume.py:358`) | code + DB |
| **Injecter** (la vanne) | — | bouton supervisé `POST /admin/sources/{id}/veille/injecter` (`dashboard.py:1680`) qui relance la commande d'ingestion. **Non cliqué** (lecture seule). | code |

**Verdict** : la **détection marche pour de vrai** (elle a trouvé une version amont réellement plus récente et l'a écrite ; elle a classé honnêtement les injoignables/illisibles). **Où ça s'arrête** : l'Injecter n'a pas été déclenché (geste de Vic, lecture seule). *Nuance notée* : BDNB est surveillée mais hors vitrine dans ce seed — à confirmer que sa « nouvelle version » remonte bien dans les réservoirs de l'À-faire en prod (hors mandat).

---

## Test 2 — type AUTO / CRON (ingestion de nuit)

**Source testée** : BODACC (procédures collectives). **Chaîne** : job `ingest-bodacc` (cron quotidien 06:40 en prod).

| Étape | Geste | Résultat réel | Preuve |
|---|---|---|---|
| **Ingestion** | `labuse jobs exec ingest-bodacc` | **exit 0, sans erreur** ; `data_sources` BODACC `last_sync_at` mis à **20/10 16:08** | `tests/T2-bodacc.log` + DB |
| Lignes produites | — | **0 ligne** `bodacc_procedures` / `bodacc_sondages` | DB |

**Verdict** : le job **tourne et se termine proprement** (connexion amont ok, pas d'erreur). **Où ça s'arrête** : BODACC est **piloté par les SIREN déjà connus** de la base ; sur une base vide, **rien à interroger → 0 ligne**. C'est la preuve d'une dépendance structurelle : l'ingestion quotidienne **a besoin de la population de référence** (sociétés/parcelles). En prod, où la population existe, ce même job produit (mesuré : ~342 s/passage, `last_sync` quotidien — cf. ETAT.md). **Il n'y a pas de garde « ±20 % »** : le job aurait écrit ce qu'il trouve, quel que soit le volume (voir ECARTS).

---

## Test 3 — type MANUEL (dépôt d'un fichier)

**Source testée** : MOBPRO (emplois au lieu de travail, INSEE). **Chaîne** : dépôt d'un fichier + `labuse ingest-mobpro --file`.

| Étape | Geste | Résultat réel | Preuve |
|---|---|---|---|
| **Dépôt** | fichier CSV `DCLT;IPONDI` déposé (`/tmp/mobpro_detest.csv`, 5 lignes dont une métropole 75056) | — | `tests/T3-mobpro.log` |
| **Ingestion** | `labuse ingest-mobpro --file …` | **exit 0 — « MOBPRO 974 : 3 communes »** | log |
| Lignes produites | — | 97411 = **5** (3+2 agrégés), 97415 = 5, 97401 = 1 ; **75056 (métropole) REJETÉ** par le filtre 974 ; `last_sync_at` mis à jour | DB `mobpro_commune` |

**Verdict** : le dépôt manuel **marche de bout en bout** — fichier → CLI → lignes en base → millésime/date mis à jour, **et le filtrage 974 fonctionne** (l'homonyme métropolitain est écarté). **Où ça casse côté dashboard** : **il n'existe aucun bouton d'upload** ; la tuile « Déposer » du dashboard **mène à la source** mais le dépôt réel est **toujours** un geste CLI avec un fichier (voir ECARTS).

---

## Les étages communs NON exécutés : Calculer → note de version → Basculer → l'écran qui change

**Non joués, volontairement**, et voici pourquoi — c'est là que « ça casse » pour un audit en lecture seule sur base jetable :

1. **Calculer** (cascade + résiduel + scoring) a besoin de **tout le parc** (~433 k parcelles + couches + PLU) et prend **plusieurs heures** (`compute-residuel --ile` puis `score-labuse`). Impossible sur une base vide, et proscrit sur la base servie.
2. **Basculer** (`bascule_flux.basculer`) écrit le manifeste et **purge les caches** du run servi — un geste qui **touche la base servie**, exclu du mandat.
3. **L'écran qui change** (tuiles, fiche, carte) se reconstruit par `rebuild` **après** la bascule.

Ce que ces étages **feraient** (vérifié dans le code, cf. COMMENT-CA-MARCHE §5-6) : un run candidat `q_vXX`, une note de version, puis une bascule atomique du manifeste + rebuild des tuiles/intersections/fiches communes. Ces chemins **tournent en vrai** sur le Mac à chaque run (dernier : q_v19, 18-19/10, cf. ETAT.md) — ils ne sont simplement pas rejouables ici sans la base de référence.

## Deux frottements rencontrés en montant les tests (dignes d'être notés)

- **`init-db` ne suffit pas** à faire tourner un job : il crée 78 tables mais **pas `event_log`** (créée par `api.events.ensure_tables` au démarrage de l'app). Le premier `sonde-sources` a **planté** sur `relation "event_log" does not exist` avant d'écrire. → bootstrap incomplet pour qui monte une base de test (ECARTS, cosmétique).
- **Sur le Mac, `labuse jobs run <job>` refuse toujours** : le wrapper pose son verrou dans `/run/lock`, **absent de macOS** → `mkdir` échoue → « déjà en cours (verrou tenu) ». Contourné avec `LABUSE_LOCK_DIR=/tmp/…` ou en appelant `labuse jobs exec` (sans verrou). Sans effet en prod (Linux a `/run/lock`). (ECARTS, cosmétique/dev.)
