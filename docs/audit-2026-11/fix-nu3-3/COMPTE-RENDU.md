# FIX-NU3-3 — exploitation : surveillance des jobs, sauvegardes, chaîne des données, charge, 2FA

**Branche** `fix/nu3-3` · **worktree** `~/Desktop/labuse-fix3` · **ports** API 9420 / front 6620
**Opus** · **Pas de merge, aucun accès prod** (dépôt seul ; les gestes prod → DEPLOY-FINAL).
Trois sessions en parallèle (FIX-NU3-1/2/3) : je n'ai touché **ni aux outils, ni aux PDF client, ni au
front client, ni à l'extension** — seulement la **chaîne de provenance des données** (millésime /
§Sources), le **cockpit d'exploitation** (admin), et le **socle** (jobs, sauvegardes, charge, auth).

Sources : `docs/audit-2026-11/nu-3/I/RAPPORT.md`, `K/RAPPORT.md`, `L/RAPPORT.md`, `reports/OPS-SAUVEGARDE-1.md`.

---

## Verdict

| Recette du mandat | Résultat |
|---|---|
| Un job **volontairement gelé** (tué en plein run) ET un job **jamais lancé** apparaissent en retard | ✅ `test_fix_nu3_3.py::test_jobs_en_retard_bloque_et_jamais` (motifs `bloque` / `jamais`) |
| Une source **avancée sur une copie locale** se voit **en fiche ET en PDF** | ✅ millésime composé unique (fiche §Les données **et** PDF §12), `test_composer_surface_une_avance_amont` + `test_pdf_sources_montre_le_millesime` |
| **25 utilisateurs** simulés : fiche et carte **sous 1 s** | ✅ **sonde fiche p95 0,79 s · carte p95 0,40 s** (API 9420, 25 users / 90 s — cf. §Charge) |
| **Hook vert** | ✅ secrets · tsc 0 · vitest **301** · pytest unit **2810** · cohérence **6/0 écart** (1 échec pré-existant hors périmètre, prouvé sur `main`) |

---

## 1. Surveillance des jobs (I-ADM-01→07, L-JOB-01→07)

**Trois états de panne, désormais tous visibles et cohérents entre écrans :**

- **Jamais réussi** (I-ADM-01 / L-JOB-01) — `ops_alertes._jobs_en_retard` ne SAUTE plus les jobs sans
  succès. Un job planifié non gelé qui n'a jamais réussi, alors que le serveur tourne depuis plus d'une
  cadence (référence = plus ancien passage journalisé, `jobs_journal.premiere_activite`), apparaît en
  retard, **motif `jamais`** → incident `job-retard:<nom>` **+ escalade** `escalade:job-jamais:<nom>`
  (mail Vic). Une base vierge (aucun passage) ne crie pas.
- **Bloqué** (I-ADM-03) — un job tué en plein run (`en_cours` figé au-delà de `timeout_s + 5 min`,
  `jobs.bloque_depuis`) est dit **BLOQUÉ (rouge)** de façon **identique partout** : vigie
  (`job-bloque:<nom>`), L'usine (`_pastille_poste`), tuiles (`_pastille_job`), résumé (`_resume_usine` :
  bloqué = en échec, plus « à l'arrêt »), page Horloge (`Cron.tsx`), `/healthz/crons` (`statut:"bloque"`).
  Fini le « travaille en ce moment » / vert à vie.
- **A tourné puis s'est tu** (le cas historique) — inchangé (dernier succès > 1,5× cadence).

**Couverture exhaustive** (I-ADM-02 / L-JOB-02) — `/healthz/crons` expose **TOUS** les jobs planifiés
(plus seulement les 11 « eau » + backup) : `mail-queue-consommer`, `digest`, `healthcheck`,
`purge-sessions`, `radar-cycle*`, `coherence-banc`… y sont, avec un seuil **en heures** pour les
sous-journaliers (mail-queue dead 2 h = vu, plus « au bout d'un jour »).

**Cohérence de l'en-tête** (I-ADM-05) — un poste qui **travaille** (`en_cours` sain) n'est plus compté
« à l'arrêt » : il rejoint la flotte saine → l'en-tête ne contredit plus la grille.

**Page Horloge** (L-JOB-03 / I-ADM-04) — `Cron.tsx` lit les verdicts serveur (`gel`/`bloque`/`perime`) :
badge **GELÉ / BLOQUÉ / EN RETARD / JAMAIS / OK** ; un job **gelé** n'affiche plus une « prochaine
exécution » menteuse (dit « gelé »).

**Journal** (I-ADM-07) — un résultat **inconnu** ne vire plus au **vert** par défaut (ambre « à regarder »).

**Nettoyages** — `_h_reunion` **échoue bruyamment** si un cron à jour spécifique franchissait minuit en
+4 h (day-wrap latent, L-JOB-04) ; `EXPLOITATION-CRON.md` **réécrit** (il décrivait le legacy retiré :
backup « 09:30 » au lieu de 13:30, `ingest-ban` fantôme…) → pointeur vers le registre + `labuse jobs
crontab` (L-JOB-05) ; `poser_crontab_solidite.sh` **supprimé** (injectait `recap-matin`, retiré du
registre, L-JOB-06) ; commentaire `planifie=False`/`agents-sources` corrigé (L-JOB-07).

**Noté, non traité** (dette / mineur, hors recette) : I-ADM-06 (garde-fou d'âge absolu par source
critique côté `fraicheur.py` — demande une décision de cadence par source, risque de faux-positif sur
LiDAR/DVF pluriannuels : laissé à Vic) ; I-ADM-09 (totaux sur les listes tronquées du dashboard) ;
la re-sonde `traction.coherence` (dashboard.py:531, l'affichage de l'âge — le volet Journal→vert est fait).

## 2. Sauvegardes (K-SAV + OPS-SAUVEGARDE-1 §7 + décisions Vic)

- **Fraîcheur, pas seulement présence** (cause du silence du 30/10) — la vigie `sauvegarde` juge l'ÂGE
  du dernier dump : **> 30 h → incident** `sauvegarde-perimee`. Le vieux dump du 29/10 ne pourrait plus
  rester « OK » trois jours.
- **Escalade** (décision Vic) — une panne durable **> 24 h** après le 1ᵉʳ seuil (> 54 h) ouvre
  `escalade:sauvegarde` : **mail explicite à Vic, sujet « ESCALADE — … », une fois par jour tant que ça
  dure** (même porte unique `ops_alertes`). Idem **automate jamais réussi** et **Radar muet 2 nuits**.
- **Filet par table** (K-SAV-01/05, décision Vic) — `backup_postgres.sh` détecte via `psql`
  (`has_table_privilege`) toute table `public` **illisible** par le rôle de dump et l'**exclut
  nominativement** (`--exclude-table=public.<t>`) : une table illisible (type `pige_restauration_radarfix3`,
  owner postgres) ne fait **plus tomber tout le dump** (le `LOCK TABLE` unique ne bute plus). Les
  exclusions sont **rapportées** (stderr + marqueur `.dump-tables-exclues.json`) — les réintégrer = un
  `GRANT SELECT` (geste prod). Toute **table nouvelle lisible** (ex. `signal_instantanes`, owner labuse)
  entre d'elle-même (K-SAV-05).
- **Restauration de contrôle mensuelle** (K-SAV-03) — jadis seulement une carte passive ; une
  restauration **jamais enregistrée ou > 35 j** ouvre désormais l'incident `restore-test-ancien`.
- **Radar muet** (K-RAD-01, server-side only — l'extension n'est PAS touchée) — nouvelle vigie :
  aucune passe `pige_passes` depuis **30 h → incident** `radar-muet` ; **48 h (2 nuits) → escalade** Vic.
- K-SAV-02 (copie hors-VPS) : scripts + cartes existent déjà ; **brancher le disque** = geste Vic
  (DEPLOY-FINAL), hors dépôt.

## 3. Chaîne des données & millésimes (L-CHN-01/02/04, L-MIL-01/02/04)

- **La source avancée se voit — fiche ET PDF** (L-CHN-01/02) : le PDF §12 « Sources » affiche désormais
  le **millésime composé** (fin de la doctrine « noms seuls ») ; `millesime_source.composer` **surface
  une avance amont réelle** (« … — à jour au 2026 ») quand `source_horizon_at` dépasse l'année la plus
  récente du libellé figé — sans inventer de date sur un libellé sans année (anti L-MIL-05).
- **Clé de fraîcheur complète** (L-CHN-04) : `millesimes_hash` hache aussi `source_horizon_at` (une
  nouvelle livraison DVF qui réécrit le même libellé mais avance l'horizon invalide bien les caches).
- **PPR par commune** (L-MIL-01) : la date d'approbation PPR servie (fiche §Les données **et** ligne de
  cascade) est celle de la **commune de la parcelle** (`ppr.date_approbation_commune`, lue dans
  `spatial_layers.ppr_etat`), plus la plus récente d'AILLEURS (Saint-André 2026-04-16 sur toute l'île).
- **Pas de notes internes à l'écran** (L-MIL-02) : la ligne de cascade (`app.py:4694`) passe par le
  même `nettoyer_notes_internes` que « Les données » (fini « édition non enregistrée », « proxy »,
  « typeinf »).
- **LiDAR** (L-MIL-04) : date d'édition « 13/03/2025 » (en dur, traçable nulle part) **retirée** du
  semis ; fenêtre de survol vérifiable conservée.
- **Noté, non traité** (mineur/dette, hors recette) : L-CHN-03 (drapeau « run périmé » rendu en fiche —
  la détection existe déjà côté `bascule_gardes`, le rendu client est territoire des sessions sœurs),
  L-CHN-05/06/07, L-MIL-03 (recalage horizon Sitadel à l'ingestion).

## 4. Charge (K-CHG-01/02/03, décision Vic : PDF deux à la fois + plafond d'études)

Module `perf_limits` : deux files d'attente **processus-locales**.
- **PDF en file** (`pdf_slot`, défaut **2**) autour du point de rendu weasyprint unique
  (`exports/rendu.render_pdf`).
- **Plafond d'études** (`etude_slot`, défaut **3**) autour du spawn du processus d'étude
  (`api/modules._dans_processus`) ; file pleine après attente bornée → **503 honnête** (« trop de
  monde, réessayez ») au lieu de laisser 26 processus saturer la RAM.

**Mesure live (API 9420, base locale, 25 users / 90 s, caches chauds)** :

| Sonde (perçu) | p50 | **p95** | max | rappel K (sans file, 25 u) |
|---|---|---|---|---|
| **fiche** | 0,028 s | **0,791 s** | 14,2 s* | p95 **10,7 s** |
| **carte** | 0,021 s | **0,395 s** | 8,8 s* | p95 **10,1 s** |

\* quelques rares samples pris dans un pic de contention au démarrage ; le **p95 < 1 s** est la garantie
du mandat. Travaux lourds pendant la sonde : 27 études OK + **18 × 503 « file pleine »** (dégradation
gracieuse voulue), 33 PDF, 56 estimations. **Fiche & carte tiennent sous 1 s à 25 users** — ce qui
cassait à 25 dans le lot K. Bornes basses sur le Mac 8 c/8 Go, relevables en prod par env.

## 5. Sécurité — second facteur pilote (I-ADM-08, décision Vic)

Le mot de passe pilote partagé n'ouvre **plus** l'admin à lui seul :
- mot de passe OK → **défi 2FA** (comme les admins nominatifs) ; `/login/2fa` exige un **code TOTP**
  vérifié contre le secret pilote (`LABUSE_PILOTE_TOTP_SECRET`) ;
- **aucun secret configuré → login pilote REFUSÉ** (fail-closed) : « second facteur obligatoire, **ou
  suppression du compte partagé** » (I-ADM-08).
Tests : `test_auth.py` (2FA pilote OK, mauvais code refusé, fail-closed sans secret).

---

## Tableau des identifiants (configuration introduite)

Tous surchargeables par variable d'environnement (préfixe `LABUSE_`, majuscules). Les valeurs ci-dessous
sont les **défauts du dépôt** ; les réglages prod vont dans DEPLOY-FINAL.

| Clé (env) | Défaut | Rôle |
|---|---|---|
| `LABUSE_PILOTE_TOTP_SECRET` | *(absent)* | **Secret TOTP base32 du compte pilote partagé.** Absent → login pilote refusé (fail-closed). Générer : `python -c "from labuse.totp import generer_secret; print(generer_secret())"`, poser en env, enrôler le secret dans une app d'authentification (Google Authenticator…). |
| `LABUSE_PDF_RENDU_MAX` | `2` | Rendus PDF weasyprint simultanés (file d'attente). |
| `LABUSE_ETUDE_PROCESSUS_MAX` | `3` | Processus d'étude simultanés (plafond). |
| `LABUSE_ETUDE_FILE_ATTENTE_S` | `20` | Attente max d'une place d'étude avant 503 « file pleine ». |
| `LABUSE_SAUVEGARDE_SEUIL_H` | `30` | Âge du dump au-delà duquel la sauvegarde est « périmée ». |
| `LABUSE_SAUVEGARDE_ESCALADE_H` | `24` | Panne de sauvegarde au-delà de ce délai (après le 1ᵉʳ seuil) → escalade mail Vic. |
| `LABUSE_RADAR_MUET_SEUIL_H` | `30` | Silence Radar (aucune passe) au-delà → incident. |
| `LABUSE_RADAR_MUET_ESCALADE_H` | `48` | Radar muet 2 nuits → escalade mail Vic. |
| `LABUSE_RESTORE_TEST_SEUIL_J` | `35` | Restauration de contrôle plus ancienne (ou jamais) → incident. |
| `LABUSE_PSQL_BIN` | `psql` | Binaire psql pour le filet par table de `backup_postgres.sh`. |

**Clés d'incident (vigie `ops_alertes`) — à qui / sujet :** tous → mail `admin_email`/`contact_email`
(Vic) + cloche admin, 1 rappel/jour. Escalades = sujet préfixé « ESCALADE — ».

| Clé incident | Déclencheur | Escalade |
|---|---|---|
| `job-retard:<nom>` | dernier succès > 1,5× cadence, OU jamais réussi | `escalade:job-jamais:<nom>` si jamais réussi |
| `job-bloque:<nom>` | `en_cours` figé > timeout + 5 min | — |
| `sauvegarde-perimee` | dump > 30 h | `escalade:sauvegarde` si panne > 24 h de plus |
| `radar-muet` | aucune passe > 30 h | `escalade:radar` à 48 h (2 nuits) |
| `restore-test-ancien` | restauration de contrôle jamais faite / > 35 j / KO | — |

---

## Banc & hook

- **Front** : `tsc -b` 0 · `vitest` **301 passed / 63 fichiers**.
- **Python unit** (`-m "not db and not local and not reel and not network"`) : **2810 passed**, 48
  skipped, **1 échec PRÉ-EXISTANT** `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens`
  (échoue **aussi sur `main`** → hors périmètre FIX-NU3-3). *(Deux autres échecs n'apparaissaient que
  lorsque l'API de recette tournait sur la même base locale et la mutait pendant les tests de comptage ;
  API arrêtée → verts.)*
- **Cohérence** (`scripts/ci/coherence_run.sh`) : **6 passed, 0 écart** (1 €/1 m²).
- **Recette dédiée** : `tests/test_fix_nu3_3.py` **8 passed** (bloqué/jamais, fraîcheur+escalade
  sauvegarde, composer avance, PDF millésime, files de charge, filet par table).
- Suites touchées re-jouées vertes : `test_auth` (13), `test_ops_healthz` (3), `test_cockpit_lot_b`,
  `test_cloisonnement_1`, `test_cron1_lot3`, millésime/sources/fiche/ppr (463), étude/implantation (101).

## Fichiers (25 modifiés, 1 supprimé, 2 créés)

Socle jobs/vigie : `jobs.py`, `jobs_journal.py`, `cockpit_resume.py`, `ops_alertes.py`, `api/ops.py`,
`config.py`, `cli.py`. Chaîne données : `millesime_source.py`, `exports/blocs/sources.py`,
`fraicheur_caches.py`, `ppr.py`, `api/app.py`, `ingestion/seed_sources.py`. Charge : **`perf_limits.py`
(créé)**, `exports/rendu.py`, `api/modules.py`. Auth : `api/auth.py`, `api/app.py`. Admin front :
`admin/Cron.tsx`, `admin/circuit/Journal.tsx`, `lib/api.ts`. Sauvegarde : `deploy/scripts/backup_postgres.sh`.
Doc : `docs/EXPLOITATION-CRON.md` (réécrit). Supprimé : `deploy/scripts/poser_crontab_solidite.sh`.
Tests : **`tests/test_fix_nu3_3.py` (créé)** + 4 tests réalignés (auth, cockpit, healthz, cloisonnement).
