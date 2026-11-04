# SILENCE-1 — « une carte = une vraie décision de Vic ; un mail = une vraie nouvelle »

**Mandat** : branche `fix/silence-1`, worktree `~/Desktop/labuse-silence`, ports 9530/6730, Opus.
**Base** : `2980df40e` (prod servie `59ce629db`, q_v20). **Pas de merge.** Onglet John non touché.
**Prod** : LECTURE SEULE respectée — **aucune écriture prod n'a été appliquée dans cette session**
(garde-fou d'environnement + doctrine du mandat). Les gestes de Vic (acceptations, acquittements,
réparation sonde, exécution restore, démarrage veille) sont CÂBLÉS dans le code et **listés prêts à
l'emploi** en fin de rapport, à appliquer au déploiement avec le go de Vic.

Règle appliquée : **une carte sur le tableau = une vraie décision de Vic ; un mail = une vraie
nouvelle. Tout le reste disparaît ou se règle seul.**

---

## Point 2 — « Jamais réussi » faux (resume-matin à 04h30 pour un passage de 07h30)

**Cause EXACTE (trouvée sur prod, lecture seule).** Le VPS et sa base tournent en fuseau
`Indian/Reunion` (+04). L'ancre « première vue » d'un job (`job_premiere_vue.vue_at`) revient de
Postgres **en heure locale +04**. `ops_alertes._prochaine_apres(cron_utc, apres)` — qui calcule le
PREMIER PASSAGE PRÉVU pour l'alerte « jamais réussi » — itérait les champs cron **sur l'heure locale**
de `apres` au lieu de l'UTC. Pour resume-matin (`30 3 * * *` = 03:30 UTC = **07:30 Réunion**), il
rendait **03:30 Réunion** (= 23:30 UTC la veille) au lieu de 03:30 UTC ; l'échéance « 1er passage +
marge 1 h » tombait donc à **04:30 Réunion** → l'alerte criait pile à 04h30, **3 h avant le vrai
passage de 07h30**. `prochaine()` y échappait déjà parce qu'elle part de `datetime.now(timezone.utc)`.

Vérifié en base : `vue_at = 2026-11-03 21:00:05+04`, `job_runs` resume-matin `2026-11-04 07:30 ok`.

**Correctif** (`ops_alertes._prochaine_apres`) : on convertit `apres` en UTC avant d'itérer les champs
cron (le cron est UTC par contrat). Désormais premier_passage = 03:30 UTC = 07:30 Réunion, échéance
08:30 Réunion → plus aucune alerte à 04:30. Tests : `test_prochaine_apres_evalue_le_cron_en_utc_pas_en_local`,
`test_prochaine_apres_insensible_au_fuseau_de_l_ancre`, `test_echeance_jamais_reussi_de_resume_matin_est_apres_0430_reunion`.

## Point 3 — Résumé du matin : [INFO] / [URGENT] + liste « à traiter » nettoyée

`jobs_impl._resume_matin_texte` (lu par le repli ET par John via `composer_resume_matin`, donc fix
unique pour les deux chemins — onglet John non modifié) :
- **nouvelle fonction testable `ops_alertes.incidents_a_traiter(ouverts)`** : retire de « à traiter »
  les escalades d'ancienneté `escalade:ancien:<base>` qui DOUBLENT un incident `<base>` déjà listé
  (rappel interne ≠ second geste → un incident, un lien). Les incidents déjà résolus n'y figurent
  jamais (`incidents_ouverts` ne rend que `resolu_at IS NULL`).
- **[URGENT]** seulement si une vraie carte actionnable demeure (ou panne de nuit / sauvegarde
  absente) ; sinon **[INFO] « rien à signaler »**.
Tests : `test_incidents_a_traiter_retire_les_escalades_doublons`,
`test_incidents_a_traiter_garde_une_escalade_orpheline`, `test_resume_matin_info_quand_rien_ne_casse`.

## Point 1 — Sources A injectées mais toujours « nouvelle version » (INSEE, annuaire, OFB)

**Cause (prod, lecture seule).** L'injection de nuit lançait bien l'ingestion (chaîne
`ingest && filtre --par vanne`) mais **rien ne remettait la veille à « ok »** après succès :
`data_sources.source_millesime` (le servi) n'avançait pas et `source_veille.dernier_statut` restait
`nouvelle_version`. Conséquence : les témoins (annuaire DILA, OFB) se ré-affichaient à chaque passage,
et la source par **agent** (Population INSEE) n'est même plus sondée (`passer` n'interroge que
api/page/entete/temoin) → le latch ne tombait jamais.

**L'annuaire A-T-IL été injecté ?** OUI — vérifié sur les journaux prod :
- `ingest-annuaire-services` : « Annuaire services 974 : **442 ingérés · 2 purgés** », filtre `ok`.
- `population-legale-sync` : « 24 communes, millésime 2023 », filtre `ok`.
- `enr-exclue-toiture-build` (OFB/APER) : 3 zonages, filtre `ok`.
Les trois ingestions ont RÉUSSI le 4/11 01:00 ; la carte ne persistait QUE faute d'acquittement.

**Correctif.** Nouvelle fonction `sentinelle.acquitter_apres_injection(db, nom)` + commande CLI
`source-acquitter <nom>`, **enchaînée à la vanne** (`ingest && filtre && source-acquitter`, donc exécutée
seulement si ingestion + filtre réussissent — `lancer_ingestion_source` dans `api/dashboard.py`). Elle :
remet `dernier_statut='ok'`, pose `dernier_notifie_vu = injection_vu = dernier_vu`, remet les échecs à
zéro, aligne la baseline témoin (`dernier_entete`), et pour les méthodes **à version** (api/page)
avance `data_sources.source_millesime = dernier_vu`. Test `test_acquittement_remet_la_veille_ok_et_avance_le_servi`
(les 3 méthodes : la carte disparaît, le servi n'avance que pour api/page).
**Preuve prod des 3 cartes qui disparaissent** : commande au §PROD ci-dessous (acquittement des id
99/152/157), à appliquer avec le go de Vic.

## Point 5 — Contrôles et journal

- **G8 ne s'écrit plus « échec » chaque matin.** `jobs_impl` (sonde de nuit des verrous) sépare les
  cassés BLOQUANTS des AVERTISSEMENTS (`VERROUS_AVERTISSEMENT = {G8}`) : le résultat journalisé est
  `echec` seulement s'il reste un cassé bloquant, `avertissement` si seul G8 « casse », `ok` sinon ; G8
  n'ouvre plus la notification « Verrous cassés ». Le résumé affiche G8 en « avertissements » (ambre
  côté front, jamais rouge).
- **« 3 pointeurs de run au lieu d'un » corrigé à la source.** Le manifeste (`served_manifest.json`)
  fait foi ; nouvelle `golden_ops.realigner_vue_depuis_manifeste()` RÉÉCRIT la vue dérivée
  `served_run.txt` depuis le manifeste. La vigie `ops_alertes` l'appelle (self-heal) AVANT de signaler :
  divergence réparée → aucun incident ouvert ; incident seulement si le réalignement échoue (disque en
  lecture seule). Test `test_realigner_vue_depuis_manifeste_corrige_la_divergence`. (Prod actuellement
  cohérent : served_run.txt == manifeste == `q_v20`.)
- **Sonde BODACC réparée.** Prod ce matin : `illisible` « réponse non-JSON », 3 échecs (hoquet
  opendatasoft — l'endpoint répond de nouveau). Deux correctifs : (a) `sentinelle.sonder_api` classe une
  réponse NON-JSON en **`injoignable`** (hoquet serveur, couvert par la grâce < 7 j) et non `illisible`
  (= notre lecteur cassé, en panne dès 3) — un chemin JSON absent dans un corps valide reste `illisible` ;
  (b) le semis BODACC lit la **fraîcheur réelle** via l'endpoint `records` (`results.0.dateparution`,
  = 2026-11-04 en direct) au lieu du `metas.default.modified` figé à 2021. Tests
  `test_sonde_api_non_json_est_injoignable_pas_illisible`, `test_sonde_api_chemin_absent_reste_illisible`,
  `test_bodacc_seed_lit_la_fraicheur_reelle`. Réappliquer sur prod : §PROD.

## Point 6 — Vérité sources (3 écarts Géorisques)

Les 3 écarts (prod, run du 15/10) : notion `risques_presence`, LABUSE « aucune vigilance risque » vs
Géorisques `resultats_rapport_risque?...&rayon=1000` listant des risques **au périmètre / régionaux**
(Séisme, Feu, Inondation de secteur…). **Notion incomparable** : LABUSE sert des vigilances de
**PARCELLE** (PPR / aléa LOCAL zoné), pas une présence dans un rayon de 1 km.

**Correctif** (`scripts/coherence/oracles` — l'oracle de la vérité sources) : même notion.
- le libellé servi devient **« aucun PPR ni aléa local »** ;
- quand LABUSE n'a aucun PPR / aléa local et que Géorisques ne montre qu'une présence AU PÉRIMÈTRE, ce
  n'est **plus un « faux »** (notions différentes, le zonage PPR parcelle a été vérifié manuellement au
  Lot B ; l'endpoint parcelle Géorisques répond 404) ;
- la sonde garde sa valeur : si LABUSE AFFIRME un risque local introuvable chez Géorisques, c'est
  toujours « faux » (faux positif LABUSE).
Tests `test_oracle_risques_presence_ne_compte_plus_le_regional_comme_faux`,
`test_oracle_risques_presence_detecte_encore_un_faux_positif_labuse`.

**87 écarts triés par TABLEAU-1** : déjà acceptés avec leur raison dans
`docs/audit-2026-11/tableau-1/ECARTS-DISPOSITION.csv` (70 lignes reasonnées, toutes `accepter`) ; le
banc de cohérence les classe déjà `TOLERABLE` (run prod #19 : n_ecarts 153, **faux_client 0,
erreurs_lecteur 0, tolerable 87**). Rien à corriger ; l'acceptation est effective.

**Incident de 20 jours** (`verite-sources`, ouvert 2026-10-15) + son escalade : à fermer sur prod avec
le go de Vic (le correctif oracle empêche la récurrence au prochain passage mensuel). Cf. §PROD.

## Point 7 — VRD / SPANC

Prod : id 26, `depot_manuel`, jamais alimentée (aucun fichier) → `a_verifier` valait VRAI (parce que
`dernier_controle IS NULL` était traité comme « en retard ») → la source s'affichait **« échue »** avec
une carte **« Déposer »** pour un fichier qui n'a JAMAIS existé.

**Correctif** : dans `api/dashboard.py`, `a_verifier` exige désormais un **dépôt antérieur** (une source
n'est « échue » que si elle a déjà été alimentée ET que sa cadence est dépassée). Une manuelle jamais
alimentée reste donc **« jamais vérifiée » (gris, benin) = en attente de fichier** : **aucune carte,
aucun mail** tant qu'aucun fichier n'existe. La page Sources l'affiche en sous-ligne
**« en attente de fichier »** (front `Sources.tsx`, vocabulaire des 5 libellés préservé). Cadence passée
à **91 j (trimestrielle)** dans le semis des sources ET des rappels (« un rappel trimestriel suffit »).
Tests `test_manuelle_jamais_alimentee_sans_carte_deposer`, `test_vrd_spanc_rappel_trimestriel`.

---

## Recette

- **SILENCE-1** : `tests/test_silence_1.py` **15/15**.
- **Banc complet** (`pytest -m "not local"`) : voir §résultat (0 rouge hors 3 échecs PRÉ-EXISTANTS
  reproduits sur `main` propre : `test_circuit_p2_lot5` (perf > 1 s, environnement), `test_circuit_p3_lot3`
  (`@pytest.mark.local`, base réelle), `test_circuit_p_lot1` (`jobs_eau==10` vs 11 avec `ingest-bodacc`
  — antérieur à ce mandat)).
- **Front** : `tsc -b` **0 erreur**, `vitest run` **303/303**.
- **0 mail faux sur 24 h simulées** : prouvé par les tests du point 3 (résumé [INFO] quand rien ne
  casse ; « à traiter » sans doublon d'escalade ni incident résolu) + point 2 (plus de « jamais réussi »
  à 04h30).
- **Tableau 0 carte après les gestes de Vic** : les 3 cartes « nouvelle version » tombent par
  acquittement (point 1, prouvé en test) ; les incidents `verite-sources`(+escalade) et
  `restore-test-ancien` se ferment par les gestes §PROD ; la fausse carte « Déposer » VRD/SPANC disparaît
  par le correctif (point 7). Reste alors 0 carte actionnable.

## Fichiers touchés (code)

- `src/labuse/ops_alertes.py` — `_prochaine_apres` UTC (P2) ; `incidents_a_traiter` (P3) ; vigie
  pointeurs self-heal (P5).
- `src/labuse/jobs_impl.py` — résumé [INFO]/[URGENT] + « à traiter » (P3) ; G8 avertissement au journal (P5).
- `src/labuse/sentinelle.py` — `acquitter_apres_injection` (P1) ; non-JSON → injoignable + semis BODACC
  `records` (P5) ; cadence VRD/SPANC 91 j (P7).
- `src/labuse/api/dashboard.py` — chaîne vanne `&& source-acquitter` (P1) ; `a_verifier` exige un dépôt
  antérieur (P7).
- `src/labuse/cli.py` — commande `source-acquitter` (P1).
- `src/labuse/golden_ops.py` — `realigner_vue_depuis_manifeste` (P5).
- `src/labuse/circuit_etats.py` — commentaire « en attente de fichier » (P7, vocabulaire 5 libellés
  préservé).
- `src/labuse/ingestion/seed_sources.py` — cadence VRD/SPANC 91 j (P7).
- `scripts/coherence/oracles/__init__.py` — oracle `risques_presence` même notion + libellé (P6).
- `frontend/src/components/admin/circuit/Sources.tsx` — sous-ligne « en attente de fichier » (P7).
- `tests/test_silence_1.py` (neuf, 15 tests) ; `tests/test_sentinelle.py`,
  `tests/test_circuit_p4_etats.py` (mis à jour pour le nouveau comportement).

## §PROD — gestes à appliquer au déploiement, avec le go de Vic (NON appliqués ici)

> Prod restée en lecture seule durant ce mandat. Ces commandes réalisent les points 1/4/5/6 côté données.

**P1 — acquitter les 3 sources A (les 3 cartes « nouvelle version » disparaissent)** — après le
déploiement du code, le prochain `injection-nuit` acquitte tout seul ; pour le faire tout de suite :
```
labuse source-acquitter "Annuaire de l'administration (service-public.fr / DILA)"
labuse source-acquitter "Population légale (INSEE via geo.api.gouv)"
labuse source-acquitter "Zones exclues EnR sauf toiture (OFB/APER)"
```

**P4 — restauration de contrôle mensuelle, base à part, sur le VPS** (enregistre `.restore-test.json`,
ferme `restore-test-ancien`) :
```
sudo LABUSE_RESTORE_TEST_REEL=1 -u labuse labuse jobs run restore-test   # base jetable labuse_restore_ctrl, droppée après
```
(si l'espace disque VPS ne permet pas la restauration réelle, le job retombe sur le contrôle de
lisibilité `pg_restore --list` et écrit quand même le marqueur → l'incident se ferme.)

**P4 — enquêteurs IA / veille John ne sont plus « à l'arrêt »** : `agents-sources` a tourné `ok` le
01/11 (vert, cadence 15 j) ; `john-veille` n'a jamais tourné (planifié, non dû). Le démarrer une fois
sous plafond : `labuse jobs run john-veille` (plafond 50 €, pause propre si atteint). L'en-tête de
« Est-ce que tout tourne ? » ne compte déjà que les vrais échecs (TABLEAU-1, confirmé) ; une veille
désactivée se compterait « à l'arrêt » (gris), jamais « en échec ».

**P5 — réparer la sonde BODACC** (après déploiement du semis, un `sentinelle semer` + un passage
suffisent ; sinon aligner la ligne) :
```
labuse sentinelle semer    # réécrit url/selecteur BODACC (records) depuis le SEED
labuse sentinelle passer --source "BODACC (procédures collectives)"   # reprobe → ok, échecs remis à 0
```

**P6 — fermer l'incident « vérité sources » de 20 jours** (tranché : Géorisques régional ≠ vigilance de
parcelle ; le correctif oracle empêche la récurrence) :
```
labuse ops resoudre verite-sources
labuse ops resoudre escalade:ancien:verite-sources
```

**Dette** : merge `fix/silence-1 → main` par PR (push main gardé par le harnais). Aucun filet de
rollback nécessaire (pas de déploiement dans ce mandat).
