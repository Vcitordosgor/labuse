# OPS-NUIT-2 — faire taire les fausses alertes

Lancé le **2026-11-03** depuis le worktree `~/Desktop/labuse-opsnuit2` (ports 9490/6690), branche
**`fix/ops-nuit-2`** assise sur **`fix/ops-nuit-1`** (`e249f4835`, l'état servi en prod). Prod en
**lecture seule** (psql `sudo -u postgres`, aucune écriture), **pas de merge**, pas de déploiement.

> **Bilan en une ligne.** Cinq fausses alarmes réduites au silence **sans affaiblir la vraie
> surveillance** : la vigie de sauvegarde ne juge plus qu'un dump **terminé** (fin du « 1,2 Mo » mesuré
> en pleine écriture) ; « jamais réussi » attend le **premier passage prévu + marge** du job (fini le cri
> au déploiement) et **n'escalade plus dans l'instant** ; `/readyz` **tolère une coupure < 2 min** d'un
> redéploiement (cause confirmée du 14h15 Paris) ; le contrôle de cohérence du calcul de nuit **lit le
> banc de 03h45** et reste **« en attente »** (pas « échec ») tant qu'un passage frais manque ; le Radar
> a enfin **un seul compteur par nuit, par portail**. Plus le piège V6b : le golden se lit en session
> **authentifiée** (même lecteur que le banc). Recette : banc **vert**, cohérence **verte**, front
> **tsc 0 / vitest**, **hook vert**.

---

## 0. Pourquoi la branche part de `fix/ops-nuit-1` et non de `main`

`fix/ops-nuit-1` (prod servie, `38c74a643`→`e249f4835`) **n'est pas encore mergée dans `main`**. Tous
les points d'OPS-NUIT-2 **continuent** ce travail (la vigie « 1,2 Mo », le « jamais réussi » de
`resume-matin`, les pièges de DEPLOY-AUTONOMIE-2). La branche a donc été réassise sur `fix/ops-nuit-1`
pour que la base corresponde **exactement** au code servi — sinon chaque correctif aurait divergé.

## 1. Vigie de sauvegarde — ne juger QU'UN dump terminé

**Constat.** `ops_alertes._dumps()` prend le `.dump` le plus récent par `mtime`. `pg_dump` écrit
**directement** dans `labuse-<db>-<ts>.dump` (pas de fichier temporaire) : pendant les ~18 min
d'écriture, ce fichier **partiel** EST le plus récent et **grossit** → la vigie mesurait « 1,2 Mo » en
plein milieu et criait « sauvegarde rétrécie » (et faussait la fraîcheur).

**Correctif.** `ops_alertes._backup_en_cours()` (lit l'état job `backup-postgres` = `en_cours`) +
`_dumps_termines()` qui **écarte le dump en cours d'écriture** ; la vigie et le résumé du matin ne jugent
que des dumps **finis**. Si le seul dump présent est celui en cours (première sauvegarde), **aucun** cri
« absente » / « rétrécie » : on attend qu'il soit terminé. Les dumps ratés sont supprimés par le script,
et les `SUSPECT-`/`GARDE-`/`hebdo-` sont hors du glob → le seul fichier non terminé possible est le run
en cours. *(La garde anti-rétrécissement du script, OPS-NUIT-1, reste la pièce préventive côté écriture.)*

**Preuve.** `test_ops_nuit_2.py::test_dumps_termines_ecarte_le_dump_en_cours` (le partiel est écarté
pendant l'écriture, jugé une fois fini) + `::test_vigie_ne_crie_pas_retrecie_pendant_ecriture`
(`verifier_declencheurs` n'ouvre PAS `sauvegarde-retrecie`, le dump jugé est le bon).

## 2. « Jamais réussi » — après le premier passage prévu + marge, sans escalade immédiate

**Constat.** Un job jamais réussi était jugé sur l'**âge du SYSTÈME** (`premiere_activite` = plus ancien
run tous jobs confondus). Un job **neuf** (ex. `resume-matin`, ajouté à 14h par OPS-NUIT-1) était donc
crié « jamais réussi » **dès le déploiement** — des heures avant son premier passage prévu (07h30) — et
**escaladait dans la foulée** (mail à Vic).

**Correctif.** Nouvelle ancre **par job** : `job_premiere_vue(nom, vue_at)` (table posée sans DDL sur le
chemin chaud, via `to_regclass`). La vigie **enregistre** la 1ʳᵉ vue des jobs planifiés (un job neuf
s'ancre à *maintenant*, un job à historique à son **premier run**), puis juge « jamais réussi »
uniquement si le **premier passage cron après cette ancre + marge** (plancher 1 h) est dépassé. Un job
tout juste ajouté attend sereinement son heure ; un cron posé mais jamais tiré finit par franchir ce
premier passage et se signale. **Plus d'escalade immédiate** : l'incident seul ; l'escalade éventuelle
vient de la vigie « incident ancien > 3 j ». Toute `escalade:job-jamais:*` résiduelle (ex. celle ouverte
à tort sur `resume-matin`) est **refermée**.

**Preuve.** `::test_jamais_reussi_attend_le_premier_passage` (job vu à l'instant → pas crié ; ancre
reculée de 2 j → crié) + `::test_jamais_reussi_n_escalade_plus_immediatement` (incident ouvert,
**aucune** `escalade:job-jamais:*`). `test_fix_nu3_3` mis à jour aux nouvelles sémantiques.

## 3. `/readyz` « pas prêt » à 14h15 Paris le 03/11 — cause + tolérance

**Cause (journaux prod, lecture seule).** `ops_incidents` : `readyz` ouvert **`2026-11-03 17:15:04 +04`
= 14:15:04 Paris**, refermé **`17:17:08 +04`** (~2 min), `rappels = 0`. C'est **le redémarrage du
déploiement** OPS-NUIT-1 de l'après-midi (le rapport OPS-NUIT-1 le note : « incident /readyz transitoire
du restart refermé »). `/readyz` répond « pas prêt » le temps que le port rouvre, puis repasse à 200.

**Correctif.** La vigie `/readyz` est **débouncée** (`ops_alertes.vigie_readyz`, seuil
`readyz_tolerance_s` = 120 s, état persisté hors base) : l'incident ne s'ouvre QUE si « pas prêt »
**persiste au-delà de 2 min**. Point d'appel **unique** : le healthcheck ne double plus la décision
(il garde sa sonde pour le compte-rendu du passage). Une coupure plus longue qu'un redéploiement
alerte toujours.

**Preuve.** `::test_readyz_debounce_tolere_coupure_courte` (1er « pas prêt » sous tolérance → aucun
incident ; vieilli > 120 s → incident ouvert ; service revenu → incident refermé + état effacé).

## 4. Radar — un seul chiffre par nuit, par portail

**Constat (données prod du 02/11).** Trois nombres pour la même nuit :
- **152** = carte « dernière capture » : `SUM(pige_passes.n_nouvelles)` des passes auto du soir
  (passe `nouvelles` 33 + passe `relecture` 119) ;
- **119** = résumé du matin : la **dernière** ligne `pige_passes` (`ORDER BY id`) seule (ici la relecture) ;
- **« Leboncoin 2, Bien'ici 3 »** = compte-rendu de l'extension : des **PAGES** lues, pas des annonces.

`pige_passes.n_nouvelles` est l'**auto-déclaration** de l'extension (comptée page par page, sommée entre
passes), **sans portail** (la table n'en porte pas).

**Définition retenue (une notion, un compteur, par portail).** La **vérité par portail** est
`pige_annonces` : une ligne par annonce (`url_sortante`/`list_id` UNIQUES), avec son `portail` et son
`created_at` = première fois vue. « **Annonces nouvelles de la nuit** », par portail = les lignes
`pige_annonces` créées ce **jour calendaire Réunion**. Mesuré sur prod pour le 02/11 :
**Bien'ici 387 · Leboncoin 72 · total 459**. Les « pages lues » restent une notion **distincte** et
nommée comme telle.

**Correctif.** Module unique `pige/comptage_nuit.py::comptage_nuit()` (lit `pige_annonces`, par portail),
câblé **partout** : carte Radar du Tableau de bord (`dashboard.py` + `cockpit_resume._carte_radar`),
**résumé du matin** (`jobs_impl`), **admin Radar** (`/admin/radar/check`) et le front (`Radar.tsx`,
type `api.ts`). Le compte-rendu de l'extension (`background.js`) est **relibellé** : « N page(s) de
nouveautés / N page(s) revues / N annonce(s) vérifiée(s) » — plus jamais confondu avec « nouvelles ».

⚠ **Recharger l'extension Chrome** après merge (le `background.js` change).

**Preuve.** `::test_comptage_nuit_par_portail` (3 Bien'ici + 1 Leboncoin le jour visé, veille exclue ;
le total **ignore** `pige_passes.n_nouvelles=999`) + SQL canonique **rejoué sur prod** (387/72/459).

## 5. Les deux pièges de DEPLOY-AUTONOMIE-2

**V6b — le golden lu en session authentifiée.** `circuit_verrous.verrou_coherence_banc` (mâchoire 4)
rejouait le golden via `TestClient(app)` **non authentifié** → sur la prod servie, `/parcels` = **401** →
`raise_for_status` → golden « cassé » (taxe « disparue », hauteur ≠ fiche) alors que le client voit la
bonne donnée. Désormais il lit par **`scripts.coherence.lib.client_en_process`** (hôte interne +
`make_token`) : **exactement** le lecteur du banc de 03h45 → 0 dérive déterministe. *(Dette
DEPLOY-AUTONOMIE-2 fermée.)*

**Calcul de nuit — lire le banc de 03h45, pas une mesure fraîche.** Le contrôle de cohérence lit déjà
`coherence_runs` (il ne relance pas de mesure) ; le piège réel était l'**ordre** : `calcul-nuit`
démarre à 02h, le banc écrit à 03h45 → la dernière ligne pouvait être celle d'**hier** (ou absente), et
`controler_run` traitait « mesure manquante » comme un **échec** → faux « contrôles en échec » au mail.
Correctif : la lecture est **épinglée au banc** (`mode = 'ile'`) et **jugée fraîche** (≤
`calcul_nuit_coherence_max_age_h` = 12 h) ; sinon la cohérence est **« en attente »** (nouveau 3ᵉ état
du `Verdict`), le run n'est pas promu (prudence) mais **aucun incident URGENT** — le verdict part au
résumé en INFO, et `promouvoir_si_ok` n'alerte plus pour un simple « en attente ».

**Preuve.** `::test_coherence_banc_pas_frais_en_attente_pas_echec` (pas frais → `en_attente`, `echecs`
vide ; frais vert → OK ; frais rouge → vrai échec) + `::test_mesures_run_lit_le_banc_et_juge_la_fraicheur`
(banc d'1 h = frais, banc de 2 j = pas frais).

## 6. Recette

- **Unitaires SEULES (le gate du hook pre-push, sans base)** : `-m "not db and not local and not reel
  and not network"` → **2862 passed / 0 failed / 49 skipped**.
- **Unitaires + base (CI complet)** : `-m "not local and not reel and not network"` → sur base de test
  nettoyée (§6quater) **4194 passed / 0 failed / 0 error / 88 skipped** (6 rouges intermédiaires, tous
  fermés — voir §6bis).
- **OPS-NUIT-2 ciblés** : `tests/test_ops_nuit_2.py` **8/8** (nouveau) ; `tests/test_fix_nu3_3.py` vert
  (sémantique « jamais réussi » mise à jour).
- **Front** : `tsc -b` **0 erreur** ; `vitest` **301 passed / 63 fichiers** (install natif ; via un
  node_modules symlinké d'un autre worktree, 8 fichiers carte échouent sur le worker maplibre hors-racine
  — artefact connu du symlink, 266 passés, cf. FIX-NU3-1).
- **Cohérence** : `scripts/ci/coherence_run.sh` → **6 passed**, « aucun écart (1 €/1 m²) sur les témoins »
  (confirme que le golden V6b lu en session authentifiée est vert).
- **Prod (lecture seule)** : incident `readyz` 14h15 Paris confirmé en base (`ops_incidents` :
  `17:15:04 +04` → `17:17:08 +04`, rappels 0) ; SQL Radar canonique rejoué (Bien'ici 387 / Leboncoin 72
  / total 459 pour le 02/11).

### 6 bis. Les 6 rouges intermédiaires (tous fermés)

Introduits par les correctifs, fermés avant le vert final :
1–2. `test_jobs_en_retard` / `test_jamais_reussi_n_escalade` — **pollution de la base de test PARTAGÉE** :
     `job_premiere_vue` (table neuve, persistante) committée par un test healthcheck antérieur → ancre
     figée. Tests rendus déterministes (ardoise `DELETE FROM job_premiere_vue`, rollback de fin). Aussi :
     `AmbiguousParameter` sur l'upsert `marquer_vues` → `CAST(:n AS varchar)`.
3.   `test_orf02_repli_local` — le repli attend `readyz` ; avec le débounce, une 1ʳᵉ observation ne
     signale plus → test pré-ancre un « pas prêt » soutenu (base verrouillée pg_dump = panne durable).
4.   `test_aucune_requete_portail_dans_le_depot` — `comptage_nuit.py` citait « leboncoin/bienici » en
     CODE → remplacé par `pige/portails.py::nom()` (seul endroit d'affichage autorisé).
5–6. `test_graphe_exact` / `test_g6` — le read `pige_passes`/`pige_annonces` a **migré** de
     `api/dashboard.py` vers `comptage_nuit.py` → graphe fin désynchronisé. `registre/lectures.py` mis à
     jour (2 lectures déclarées pour `comptage_nuit.py`, 1 périmée retirée de `api/dashboard.py`) →
     `lecteurs_non_declares`/`lectures_perimees`/`analyse_g6` **tous vides**.

### 6 ter. Pas de migration

La table `job_premiere_vue` se crée toute seule (`to_regclass` + `CREATE TABLE IF NOT EXISTS`, hors du
chemin chaud), comme `ops_incidents` — aucune migration, aucune variable d'env obligatoire (deux réglages
optionnels : `LABUSE_READYZ_TOLERANCE_S`=120, `LABUSE_CALCUL_NUIT_COHERENCE_MAX_AGE_H`=12).

### 6 quater. Les 4 « errors » de setup = pollution de la base de test (pas mon code)

Le run CI complet remontait **4 erreurs de SETUP** (pas des échecs d'assertion), toutes
`UniqueViolation: utilisateurs_email_key` — un test qui COMMITTE des comptes à email FIXE, sur la base
`labuse_test` PARTAGÉE et persistante. Après ~5 passes complètes dans la journée, `utilisateurs` avait
**6 580 lignes accumulées** (emails surtout aléatoires = fuite d'un test non rollback-é) ; une fixture à
email fixe butait sur une ligne déjà posée. **Indépendant de ce mandat** : mon diff ne touche AUCUNE
table `utilisateurs`/compte, et la 1ʳᵉ passe de la journée n'avait aucune de ces erreurs. Dette
pré-existante (un test qui commite sans rollback). Preuve : après `TRUNCATE utilisateurs CASCADE`
(artefacts de test uniquement — FK : `sessions_auth`/`totp_2fa`/`totp_secours`), le run CI complet est
**0 error / 0 failed**. Le hook pre-push, lui, ne joue QUE les unitaires (sans base) → jamais concerné.

## 7. Dette / non fait (volontaire)

1. **Extension Chrome à recharger** après merge (`background.js` relibellé).
2. **Merge `fix/ops-nuit-1` → `main`** reste à faire par PR (indépendant de ce mandat) ; cette branche
   s'y ajoute ensuite.
3. **Repli local de `readyz`** pendant une indisponibilité TOTALE de la base : non conservé (le point
   d'appel unique passe par la base) — couvert par la sonde `/health` (2 échecs → `echec` bruyant) et
   par l'incident « base injoignable » lui-même.
4. **Fenêtre « nuit » Radar** = jour calendaire Réunion de la dernière capture auto (documenté dans
   `comptage_nuit.py`) ; si l'on veut coller à la *soirée* plutôt qu'au *jour*, c'est un réglage à part.

## Fichiers touchés

`src/labuse/ops_alertes.py`, `jobs_journal.py`, `jobs_impl.py`, `autonomie.py`, `config.py`,
`circuit_verrous.py`, `cockpit_resume.py`, `api/dashboard.py`, `pige/api.py`, `registre/lectures.py`,
**`pige/comptage_nuit.py` (neuf)**, `outils/radar-extension/background.js`,
`frontend/src/components/admin/Radar.tsx`, `frontend/src/lib/api.ts`, `tests/test_fix_nu3_3.py`,
`tests/test_fix_orfevre1_point2.py`, **`tests/test_ops_nuit_2.py` (neuf)**.
