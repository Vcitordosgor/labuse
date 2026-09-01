# RAPPORT SENTINELLE-1 — l'agent de veille des sources, généralisé

**Branche** : `feat/sentinelle-1` (depuis `main` après merge de `fix/connexions-3`). **Merge = Vic.**
**Étape 0** : `pwd` = `~/Desktop/labuse`, branche `feat/sentinelle-1`, arbre propre au départ. ✅

La sentinelle **surveille et prévient. Elle ne télécharge rien, n'ingère rien, ne remplace aucune
donnée, n'écrit JAMAIS dans `data_sources`.** Détection 100 % mécanique (dates, motifs, en-têtes ; zéro
LLM). Aucune source de type annonce n'est surveillée. Doctrine du mandat respectée de bout en bout.

---

## W1 — La table de veille des sources

**Fait.** Modèle `SourceVeille` (`models.py`) + migration boot `ensure_source_veille` (idempotente,
`CREATE TABLE IF NOT EXISTS`, câblée dans `_ensure_schema_steps`). Colonnes exactes du mandat : `source_id`
(FK `data_sources`, `ON DELETE CASCADE`, unique), `url_version`, `methode`, `selecteur`, `cadence_heures`
(défaut 24), `dernier_passage_at`, `dernier_vu`, `dernier_statut`, `dernier_message`, `actif`.
**Ajout assumé** : `dernier_entete` — la méthode `entete` a besoin de mémoriser le dernier ETag/Last-Modified
pour détecter un changement (sinon impossible de comparer « au dernier téléchargement »).

**Constat.** Une source sans ligne = non surveillée, état normal (LEFT JOIN partout, jamais une erreur).
**Reste.** —

## W2 — Trois méthodes de détection, pas plus

**Fait.** Module `sentinelle.py`, une seule couche réseau injectable (`_http`, one-shot, timeout 12 s,
User-Agent `LABUSE-sentinelle/1.0`, **aucun retry**). Trois méthodes :
- **`api`** — GET JSON, extraction au chemin pointé `selecteur` (`a.b.0.c`).
- **`page`** — GET HTML, `selecteur` = regex ; on garde le **plus récent** (`max`), jamais le premier venu.
- **`entete`** — HEAD (repli GET) ; compare `ETag`/`Last-Modified` au dernier vu ; ne nomme aucune version.

Comparaison au millésime **réellement servi** (`data_sources.source_millesime`, W3.3) : une lecture `ok`
devient `nouvelle_version` seulement si l'amont est **postérieur** au servi (jamais si égal).

**Reprise de `sentinelle-dvf-cadastre` — donne-t-elle le même résultat qu'avant ?**
Oui, à l'échelle du **résultat** (une alerte DVF/cadastre est levée), avec une **mécanique améliorée** :
l'ancien job était une simple heuristique de **date** (`prochain_millesime_at` échue) ; DVF et cadastre
sont désormais **deux lignes de `source_veille`** sondées réellement (DVF en `page`, cadastre en `entete`).
Test de non-régression `test_non_regression_dvf_alerte_comme_l_ancien_job` : sur la même donnée, l'ancienne
heuristique **et** le nouveau passage lèvent tous deux l'alerte. **Bonus** : l'ancien code comparait un
`date` à un `datetime` → `TypeError` **latent** dès qu'une source portait `prochain_millesime_at` (le job
aurait planté en prod) ; corrigé dans la fonction conservée. L'ancien `sentinelle-dvf-cadastre` **n'est plus
au registre des jobs** (fonction gardée uniquement pour ce test).

**Reste.** —

## W3 — Le job quotidien

**Fait.** Job `sentinelle-sources` (`jobs.py`, **quotidien** 07:00 Réunion / 03:00 UTC ; cron.d mis à jour,
l'ancienne ligne mensuelle retirée). `sentinelle.passer` : parcourt les lignes `actif=true` **à cadence
échue**, sonde **séquentiellement** avec un **délai** entre appels (2 s ; 0 en test), écrit le résultat
**dans `source_veille`**. **Aucune écriture dans `data_sources`** (vérifié par test : le millésime servi ne
bouge pas). `injoignable`/`illisible` = la **sentinelle** a échoué, jamais la donnée — les deux états
restent distincts (test dédié). `envoie_mail=False` : la notif passe par la **cloche admin**, pas un mail
quotidien (bruit évité).

**Reste.** —

## W4 — Ce que Vic voit

**Fait.**
1. **Notification admin** à la 1re détection, **dédupliquée par (source, millésime)** via `creer_notification
   (kind="systeme", compte_id=NULL, permanent=True)` → **jamais un rappel quotidien** (test : 2e passage même
   millésime → 0 notif). Formulation : « *DVF : 2026-S1 est publié — vous servez 2025-S2* ». `entete` (sans
   millésime lisible) dit « *le fichier amont a changé* ».
2. **Tuile Sources** : chip « *N nouvelle version disponible* » dans l'en-tête + `synthese.nouvelle_version`
   / `surveillees` au backend. Le lien est la liste elle-même.
3. **Page Sources (admin)** : le panneau « Agent de veille des sources » **sort de son état grisé**
   (`admin/Sources.tsx`). Par source surveillée : **millésime servi · millésime amont** (ambre si nouvelle
   version) **· dernier passage · statut**. Actions **« Vérifier maintenant »** (`POST
   /admin/sources/{id}/veille/verifier`, sonde en direct) et **suspendre/réactiver** la veille (`POST
   …/veille/active`).
4. **Rien côté client** : tout est sous `exiger_admin`, kind `systeme` (compte NULL) invisible aux abonnés.

**Reste.** Pas d'édition du `selecteur`/`url` depuis l'UI (hors périmètre du mandat) : un sélecteur à
corriger se fait en base/SEED. Le design rend l'erreur **sûre** (statut `illisible` visible, jamais un crash).

## W5 — Peupler la table

**Fait.** Peuplement **conservateur** (W5.3 : une URL non vérifiée est pire qu'une absence). SEED de
`sentinelle.py`, rattaché aux sources par **nom exact**, ensemencé au boot, **idempotent** (rafraîchit
url/methode/selecteur, **préserve `actif`** — une source suspendue par Vic le reste ; test dédié).

**Surveillées : 6 sur 64 entrées du catalogue.** Ventilation par méthode :

| Méthode | N | Sources |
|---|---|---|
| `page` | 1 | DVF / valeurs foncières (index géo-DVF, regex `20\d{2}`) |
| `entete` | 3 | Cadastre Etalab (bulk), BPE INSEE (zip), QPV 2024 ANCT (zip) |
| `api` | 2 | DPE ADEME (`dataUpdatedAt`, data-fair), BODACC (`dataset.metas.default.modified`, ODS v2.1) |

Toutes ces URL **existent déjà** dans `data_sources` (jamais inventées). Le choix privilégie `entete`
(aucun sélecteur à deviner) et ne retient en `api`/`page` que des champs/motifs à contrat stable.

**Non surveillées — les 58 autres, par raison (W5.2)** :
- **Pas d'URL stable / import manuel** : Filosofi INSEE, Office de l'eau Réunion, Potentiel foncier Région
  (PEIGEO/AGORAH), MOBPRO, VRD/SPANC, Fichiers fonciers Cerema (convention) → aucune page/API de version.
- **Endpoints requête sans notion de version** (search/records/WFS `GetFeature`) : BAN, Recherche
  d'entreprises, SIRENE, Overpass/OSM, API Carto (parcelle/zone-urba/assiette-sup), Géorisques (ssp/cavités/
  mvt/ICPE), couches Géoplateforme WFS (BD TOPO, RGE ALTI, IRIS, forêts, RPG) → surveillables **en principe**
  (GetCapabilities / `dataUpdatedAt`) mais **pas sans vérifier un sélecteur par source** = effort
  disproportionné et risque de pollution `illisible` sans validation réseau réelle.
- **Portails proxyfiés / injoignables catalogués** : PEIGEO hub, DEAL WMS/WFS (servis via proxys).
- **Doublons/dormants** du catalogue (technical_notes `DOUBLON`/`RETIRÉ`/`DORMANT`).

Ces sources restent **non surveillées, sans ligne** — état normal. Extension = ajouter des entrées au SEED
une fois chaque URL+sélecteur **vérifiés au premier passage réel** (le bouton « Vérifier maintenant » le
permet source par source, sans redéploiement de code une fois la ligne créée).

**Reste.** Élargir le SEED après validation live des candidats API/GetCapabilities (Tier 2).

---

## Clôture — vérifications

- **tsc** : ✅ 0 erreur. **build front** : ✅.
- **Tests front** : ✅ **118 passed** (26 fichiers ; +3 `Sources.veille.test.tsx`).
- **Tests backend** : ✅ **2092 passed**, 34 skipped, dont **13 neufs** (`test_sentinelle.py`) + `test_dashboard`
  mis à jour (clés `synthese`). **2 échecs pré-existants** hors périmètre, fichiers non touchés :
  `test_pige_socle` (pige/api.py importe un client HTTP) et `test_zone_donnees` (jointure SIRENE) — connus
  (cf. mémoire CONNEXIONS-3). L'ERROR `test_cascade` en run complet est un `OperationalError` transitoire
  (contention base) : le test **passe isolé**.
- ⚠ **Effectif au redémarrage serveur** (nouvelle table + seed au boot, nouveaux endpoints, nouveau job).

**Fichiers.** Back : `models.py`, `sentinelle.py` (neuf), `jobs.py`, `jobs_impl.py`, `api/dashboard.py`,
`deploy/cron.d-labuse`. Front : `lib/api.ts`, `admin/Sources.tsx`. Tests : `test_sentinelle.py` (neuf),
`Sources.veille.test.tsx` (neuf), `test_dashboard.py`.

Merge isolé en dernier :
```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/sentinelle-1
```
