# AUTONOMIE-1 — LABUSE tourne sans Vic

**Branche** `feat/autonomie-1` · worktree `~/Desktop/labuse-autonomie` · ports 9470/6670 · **Opus**
**Pas de merge.** Prod en **lecture seule, sauf la phase 0**. Date : 2026-11-02 (Réunion +04).

> **Bilan en une ligne.** Phase 0 **faite sur prod** (sauvegarde réparée + relancée + vérifiée + copiée
> hors-VPS, incidents de sauvegarde fermés **automatiquement avec preuve**). Phase 1 **livrée en code
> testé** (banc non-db **2848/0**, cohérence **6/0**, +40 tests neufs) : le **calcul de nuit** sur le
> serveur avec contrôles-avant-promotion, l'**injection par classes A/B** avec retour arrière, les
> **incidents vivants** (fusion + escalade > 3 j + auto-fermeture), la **restauration de contrôle**
> enregistrée, plusieurs **réparations**. Ce qui reste une **décision humaine** est listé en fin.

---

## PHASE 0 — prod, aujourd'hui, en premier (FAIT)

### La sauvegarde a échoué à 13 h 47 — cause trouvée, corrigée, relancée, vérifiée

**Cause (trouvée).** Le dump de 13:30 a tourné **17 min puis a été tué** à 13:47 :
`FATAL: terminating connection due to administrator command` pendant le `COPY public.tuyau_subdivise`.
Ce n'est **pas** la panne K-SAV-01 des jours précédents (30/10→01/11 : échecs instantanés 0,2 s sur le
`LOCK TABLE … pige_restauration_radarfix3`, **déjà résolue** par OPS-SAUVEGARDE-1 qui a supprimé la
table) : le dump de 13:47 a **dépassé la phase LOCK** (preuve que K-SAV-01 est fermée) et n'est tombé
qu'en fin de parcours. La fenêtre 13:30→13:47 **chevauche exactement** le DEPLOY-FINAL d'aujourd'hui
(déployé 13:12 Réunion + ~15 min d'incident de boot : purge d'un pile-up de verrous **qui a terminé des
backends orphelins** et reconstruit `spatial_layers_sub`). **Le déploiement en cours a tué la connexion
du pg_dump.** C'était un évènement ponctuel (le déploiement), pas une panne structurelle.

**Correction + relance.** Prod vérifiée **au calme** d'abord (0 backend non-idle, 0 process de deploy/
dump, `/readyz` prêt), script `backup_postgres.sh` confirmé **à jour** (filet-par-table `--exclude-table`
+ `has_table_privilege` bien déployé en `4e7c9d29f`). Relance **par le lanceur de jobs** (comme le cron) :
`labuse jobs run backup-postgres` → **`job_runs` id 8783, statut `ok`, 1135 s**, dump
`labuse-labuse-20261102-163345.dump` **6 558,86 Mo**.

**Vérification du dump + copie hors-VPS.**
- `pg_restore --list` : **1739 objets** (cohérent avec les dumps sains précédents).
- **sha256 VPS == Mac** (`a2e63dfab8a4e021583e4d0f7cb286d64d34782be72c7abe2956405c3c96bc8f`) après
  `pull_backups.sh labuse-vps` → `~/labuse-backups` (copie **bit-pour-bit**, 6,1 Go, rotation faite).

### Incidents fermés en base — « résolu automatiquement » avec preuve

Fermés **par le mécanisme normal** (pas à la main) :

| Incident | Ouvert | Résolu | Comment |
|---|---|---|---|
| `job-echec:backup-postgres` | 10-30 13:30 | **11-02 16:52** | auto-fermé par `jobs._journaliser_et_alerter` au **succès** du backup |
| `job-retard:backup-postgres` | 10-31 02:00 | **11-02 16:54** | auto-fermé par la vigie (`labuse ops verifier`) une fois le dernier succès frais |

**Laissés ouverts — à raison** (leur cause N'A PAS disparu, donc on ne les ferme pas) :
- `coherence-banc` (`job-echec` + `job-retard`) : **le banc ne repasse pas** (cf. Réparations) → cause
  encore présente ; corrigé en **code** (Phase 1), se fermera seul au prochain passage vert post-déploiement.
- `copie-externe-ancienne` : **décision humaine** — Vic doit brancher le disque externe (K-SAV-02).
- `restore-test-ancien` : réglé en Phase 1 (le job écrit désormais le marqueur) ; se ferme au 1ᵉʳ passage.
- `verite-sources` : **décision humaine** — 3 écarts parcelle↔source officielle à trancher.

---

## PHASE 1 — code (livré, testé)

Tout le cœur de politique vit dans un module neuf **`src/labuse/autonomie.py`** (fonctions PURES,
testées sans base ni réseau), câblé par des jobs et des vigies. « Sur-protéger est bénin, sous-protéger
est le bug » : un contrôle qui ne peut pas conclure est un **échec** (on ne promeut/injecte pas).

### Doctrine 1 — le calcul de nuit tourne sur le SERVEUR, la nuit

**Job `calcul-nuit`** (registre, famille 3 « Le moteur », 02:00 Réunion, budget 4 h) :
- **Fenêtre 01 h–05 h Réunion** (`autonomie.fenetre_nuit`) ; hors fenêtre → **abstention propre** (pas un
  échec). **Abandon propre** si la fenêtre est dépassée pendant le calcul (`fenetre_depassee`) — ne mord
  pas sur les heures ouvrées.
- **nice + ionice + plafond mémoire** (`RLIMIT_AS`, `_run_sous_process_nice`) : le calcul passe **sous**
  les requêtes servies ; un calcul qui déraille est tué par le noyau, pas la prod.
- **Déclencheur** (`autonomie.doit_calculer`) : recalcule dès qu'une **entrée a changé** (injection /
  source avancée, lu sur `data_sources.last_sync_at/source_horizon_at`) **sinon au plus 1×/semaine**.
- **Dépendances de calcul** : si `pandas/numpy/joblib` manquent au venv → **ÉCHEC BRUYANT** (« venv prod
  sans ML »), jamais un faux vert. Elles entrent au venv prod **de façon tracée** :
  `deploy/requirements-calcul.txt` (sous-ensemble scoring **sans torch**) + étape **`2bis`** de
  `deploy_app.sh` (install + import-smoke). *Le mandat change la doctrine DEPLOY-FINAL « aucun calcul sur
  prod » ; ces deps sont désormais autorisées, **minimales et tracées**.*
- **Contrôles AVANT promotion** (`autonomie.controler_run`) : manifeste présent, run complet, **comptes
  de parcelles égaux** au servi, **cohérence des témoins verte** (lue du dernier `coherence-banc`),
  **0 copropriété** et **0 parcelle entièrement rouge** en palier actionnable (doctrines E-010 /
  PPR-UNIQUE-1), **écart de paliers ≤ seuil** (3 %). **Tout vert → bascule** (`bascule_flux.basculer`) ;
  **sinon : PAS de promotion + mail à Vic**, le run candidat reste en base (non servi), rejouable.
- **Premier run = q_v21.** (Son exécution réelle reste un geste post-déploiement — cf. « Reste à faire ».)

### Doctrine 2 — les sources de référence à faible risque s'injectent seules

**Job `injection-nuit`** (famille 2, 01:00 Réunion, avant le calcul). Chaque source du registre porte une
**classe** (`autonomie.classe_source`, défaut **B = prudence**) :
- **A — référence à faible risque** : s'injecte **seule la nuit** avec contrôles (`controler_injection` :
  comptes non nuls, **géométries valides**, **couverture 974 ≥ seuil**, écart avec la version précédente
  ≤ 15 %) et **RETOUR ARRIÈRE automatique** si un contrôle échoue (`injecter_avec_rollback` : injecte →
  mesure → valide **ou** annule).
- **B — structurant** (PLU, PPR, DVF, cadastre, LiDAR, BD TOPO, DGFiP…) : **jamais injectée seule**, elle
  **attend le clic de Vic**, demandé par **mail** quand la sentinelle voit une nouvelle version.

**Le câblage source→ingesteur par source de classe A reste à compléter** (mapping vérifié requis) : le job
LISTE aujourd'hui les classes et n'injecte que ce qu'il sait **mesurer** — on n'injecte **jamais à
l'aveugle**. La politique (contrôles + rollback) est livrée et testée ; le branchement par source est la
suite mécanique.

**Tableau des classes** (129 sources du registre prod — **A = 35, B = 94**) : cf. annexe en fin de doc.
La majorité en B est **voulue** : « dans le doute, un humain décide ».

### Doctrine 3 — un incident se ferme seul quand sa cause disparaît (incidents vivants)

- **Auto-fermeture** : déjà portée par `ops_alertes.verifier_declencheurs` (disque, readyz, sauvegarde,
  radar, jobs…) — **démontrée en vrai aujourd'hui** (incidents de sauvegarde). Étendue : le calcul de
  nuit et les sources B en attente se referment de même.
- **Fusion « retard / échec »** (`autonomie.fusionner_retard_echec`) : `job-echec:<nom>` et
  `job-retard:<nom>`/`job-bloque:<nom>` = **une seule carte par job** au Tableau de bord.
- **Escalade > 3 jours** (`autonomie.incidents_anciens`, câblée dans `verifier_declencheurs`) : tout
  incident ouvert depuis plus de 3 j **remonte dans le mail quotidien** (`escalade:ancien:*`, 1 rappel/
  jour), et se referme avec son incident sous-jacent.
- **Tableau de bord = décisions humaines** : les cartes masquent les doublons d'escalade d'ancienneté et
  fusionnent les jobs ; chaque carte garde **un bouton par action**.

### Restauration de contrôle mensuelle (enregistrée, visible)

**Job `restore-test` RÉTABLI** (famille 4, mensuel le 5). Il **écrit toujours** `.restore-test.json`
(lu par la vigie + le Tableau de bord → l'incident « jamais enregistré » **se ferme seul**). Contrôle de
**lisibilité** (`pg_restore --list`) côté serveur en permanence ; **restauration RÉELLE dans une BASE À
PART du VPS** (`labuse_restore_ctrl`, `deploy/scripts/restore_test_base.sh`, createdb→restore→count→drop)
quand `LABUSE_RESTORE_TEST_REEL=1` **et** que le disque le permet (**garde 4×** la taille du dump).

### Réparations

| Sujet | État | Détail |
|---|---|---|
| **coherence-banc rouge depuis le 28/10** | **CORRIGÉ (code)** | Cause : `deploy_app.sh` exclut `docs/`, or le banc lit à l'exécution `docs/…/ECHANTILLON.csv` (produit gelé) → `FileNotFoundError`. Fix : rsync ciblé des 3 échantillons (coherence + 2 chasse) sans lever l'exclusion. Se ferme au 1ᵉʳ passage vert post-déploiement. **Dette tracée** : relocaliser ces échantillons hors `docs/`. |
| **« verrous » (6 contrôles) en échec chaque nuit depuis le 28/10** | **DIAGNOSTIC** | **Même date, même cause probable** : les 25 gardes CHASSE-DONNÉES + verrous tournent *dans* `coherence-banc`, qui **lève avant** de les atteindre (ECHANTILLON manquant) → verrous jamais évalués. Le fix coherence-banc ci-dessus les rétablit. À **confirmer** au 1ᵉʳ passage vert. |
| **3 pointeurs de run au lieu d'un** | **OBSERVABILITÉ (code)** | `runs.pointeurs()` expose env / manifeste / `served_run.txt` + `coherents` ; vigie `pointeurs-run-divergents` (living incident) si le backend (manifeste) et le bundle front (`served_run.txt`) divergent. `current()` **inchangé** (le manifeste fait déjà foi — on ne touche pas au chemin servi). |
| **Livreurs Sitadel / DPE / SIRENE à l'arrêt** | **VÉRIFIÉS planifiés** | Les 3 sont au registre, `planifie=True`, **non gelés** (famille 2, cron mensuel posé). Pas à l'arrêt côté planif ; un éventuel échec d'exécution est désormais visible (jobs vivants). |
| **6 sondes en panne** | **DIAGNOSTIC + fix path** | Données réelles prod : **3 `injoignable`** (Overpass : OSM transport, TCSP, Parkings APER — 11-13 échecs consécutifs = endpoint public saturé) ; **3 `illisible`** (Géorisques SIS / OCS GE / SCOT GPU — 14 échecs = URL/format amont changé). Ce sont des **sondes informatives** (ne bloquent rien). Fix : mirror Overpass + re-validation **en ligne** des 3 endpoints (nécessite un accès live — **décision/geste humain**, listé). |
| **87 écarts entre écrans** | **TRIAGE** | Registre autoritatif `docs/audit-2026-*/…/ECARTS.csv`. Tri par gravité → **À CORRIGER** : `bloquant` + `a_corriger` ; **À ACCEPTER AVEC RAISON** : `cosmetique`. Ex. CHASSE-1 (45) : 5 bloquant + 23 à corriger = **28 à corriger**, **17 à accepter**. Méthodo + listes : cf. annexe. L'énumération ligne-à-ligne des 87 est une **suite tracée** (le cadre + les compteurs sont posés ici). |

### Radar — le serveur détecte une nuit sans passe

Couvert côté serveur par la vigie **`radar-muet`** (`ops_alertes._vigie_radar_muet`) : aucune passe
`pige_passes` depuis **30 h → incident** (donc « le serveur le dit dans le mail »), **48 h → escalade**
Vic. Le Mac reste la machine de capture (réveil programmé + verrou `running` corrigé = FIX-NU3-4 / geste
Mac de Vic). **Server-side : rien à ajouter** — la détection d'une nuit muette est déjà là.

---

## RECETTE

| Attendu du mandat | Résultat |
|---|---|
| Un run simulé qui **échoue un contrôle** n'est **pas promu** et déclenche le **mail** | ✅ `test_autonomie_1.py::test_run_simule_echoue_controle_non_promu_et_mail` (+ 7 contrôles unitaires) |
| Une **injection classe A** avec un contrôle qui échoue **revient en arrière** | ✅ `::test_injection_classe_a_echoue_revient_en_arriere` (rollback appelé, commit jamais) |
| Un **incident dont la cause disparaît se ferme seul** | ✅ **démontré en prod** (sauvegarde) + mécanisme `verifier_declencheurs` |
| **Banc complet 0 rouge** | ✅ **2848 passed / 0 failed** (non-db/reel/local/network ; +40 tests AUTONOMIE-1) |
| **Suite de cohérence verte** | ✅ `scripts/ci/coherence_run.sh` → **6 passed, 0 écart** (1 €/1 m², base locale, run servi 17) |
| **Hook vert** | ✅ non-db **2848/0** + cohérence **6/0** ; **front non touché** (aucun `.ts/.tsx`) → tsc 0 / vitest 301 **inchangés** du baseline |

> Les suites **`db`/`reel`** (API live, second Postgres) et le **pre-push** complet se jouent sur une
> machine portant la base applicative branchée (comme les mandats précédents) : non rejouables tels quels
> dans ce worktree (base présente mais l'API n'est pas bootée ici). Le gate unitaire + la cohérence réelle
> sont verts.

---

## CE QUI RESTE, PAR NATURE, UNE DÉCISION HUMAINE

1. **Promouvoir une source de classe B** (PLU, PPR, DVF, cadastre, LiDAR, BD TOPO, DGFiP, …) — le clic de
   Vic, par conception (jamais automatique).
2. **Trancher les écarts `verite-sources`** (parcelle ↔ source officielle) — jugement.
3. **Brancher le disque externe** (copie hors-VPS longue durée, K-SAV-02).
4. **Re-valider en ligne les 3 endpoints de sondes `illisible`** (SIS / OCS GE / SCOT) — lecture du
   nouveau format amont.
5. **Accepter/corriger chaque écart écran** de la liste « à corriger » vs « à accepter » (le tri est posé ;
   l'arbitrage final reste humain).
6. **Lancer/valider le premier run q_v21** et confirmer la bascule (le calcul + les contrôles sont
   automatiques ; la **première** mise en service se fait sous l'œil de Vic).

## RESTE À FAIRE (tracé, hors « décision humaine »)

- **Déployer** ce code (hors mandat « pas de merge ») : alors coherence-banc + verrous repassent, les
  deps de calcul entrent au venv, et les jobs de nuit s'arment.
- **Câbler source→ingesteur** pour chaque source de classe A (la politique contrôles+rollback est prête).
- **Énumérer ligne-à-ligne** les 87 écarts dans les deux listes (cadre + compteurs posés).
- **Relocaliser** les échantillons gelés du banc hors `docs/` (robustesse déploiement).
- **UI Tableau de bord** : rendu « décisions humaines seules » + un bouton par action (la fusion/escalade
  back est faite ; le polish front reste).

---

## Fichiers

**Neufs** : `src/labuse/autonomie.py`, `deploy/requirements-calcul.txt`,
`deploy/scripts/restore_test_base.sh`, `tests/test_autonomie_1.py`, `tests/test_autonomie_registre.py`,
ce compte-rendu.
**Modifiés** : `src/labuse/config.py` (réglages autonomie), `src/labuse/jobs.py` (3 jobs + familles),
`src/labuse/jobs_impl.py` (`calcul_nuit`, `injection_nuit`, `restore_test` enrichi + helpers),
`src/labuse/ops_alertes.py` (escalade > 3 j + vigie pointeurs), `src/labuse/cockpit_resume.py` (fusion),
`src/labuse/runs.py` (`pointeurs()`), `deploy/scripts/deploy_app.sh` (échantillons banc + deps calcul),
`docs/audit-2026-10/DASHBOARD-FIX-1/HORLOGES.csv` (régénéré), `tests/test_cockpit_lot_b.py` (33 jobs).

---

## ANNEXE — Tableau des classes de sources (A = auto nuit · B = clic de Vic)

**A — référence à faible risque (35)** : injectée seule la nuit, contrôles + rollback.
50 pas géométriques (limite haute) · ABF/Monuments historiques · Annuaire administration (DILA) ·
BD NYME lieux-dits · BODACC · BPE INSEE · Base Adresse Nationale · Cartofriches · CatNat (GASPAR) ·
GéoLittoral érosion · Classement sonore ITT · Contours IRIS · Contraintes EnR (habitations) · Espaces
protégés Ramsar/sites classés · Filosofi INSEE · Forêts publiques (ONF) · GéoMCE · INPI RNE ·
INPN/patrinat espaces protégés · INSEE RP Logement 2023 · INSEE RP2022 IRIS · Inventaires ZAE ·
MOBPRO · Parc National (INPN) · Population légale (INSEE geo.api) · QPV 2024 · Recherche d'entreprises ·
SIRENE · SIRENE géolocalisés · SUP assiettes GPU · Trafic RN · Transport GTFS (PAN) · ZNIEFF · ZPPA ·
Zones exclues EnR sauf toiture (OFB/APER).

**B — structurant / prudence (94)** : attend le clic de Vic (mail). Inclut les socles explicites —
Urbanisme PLU/GPU, DEAL PPR/aléas, DVF, Cadastre (PCI + Etalab), RGE ALTI / LiDAR HD, BD TOPO, OCS GE,
RNB, IGN BD CARTO, DGFiP personnes morales, Fichiers fonciers, SITADEL, DPE — **plus toute source non
classée explicitement** (défaut = B). La règle par défaut est **la prudence** : une source inconnue ne
s'injecte pas seule.

*(Table complète reproductible : `labuse` + `autonomie.sources_par_classe(data_sources)`.)*
