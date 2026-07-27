# M26-A — RAPPORT DE FIN DE MANDAT · COPILOTE LABUSE, SOCLE AGENTIQUE

**Branche** : `feat/m26a-copilote-socle` (base `origin/main` 18ea733, poussée, non mergée —
Vic merge en `--no-ff`). **Périmètre tenu** : back-end uniquement, aucune UI.
**Règle absolue respectée** : le LLM ne calcule jamais rien — il n'apparaît QUE dans
l'interpréteur (`copilote/interpreteur.py`), tout chiffre servi vient d'un moteur
déterministe existant, journalisé et étiqueté.

## 1 · Schéma des tables (`copilote/tables.py`, pattern maison CREATE IF NOT EXISTS)

| table | rôle | points clés |
|---|---|---|
| `agent_runs` | un dossier d'instruction | `id uuid`, `compte_id` (FK comptes, pattern SEC-IDOR, bucket pilote = NULL) + `utilisateur_id` nullable (décision GO Q2), `mission`, `status` (CACHE — recalculable par `reduce_run`), `brief_raw` verbatim, `brief_json` (null tant que non validé), `engine_versions` jsonb |
| `agent_events` | **event log append-only, source de vérité unique** | `UNIQUE (run_id, seq)`, seq strictement croissant par run ; trigger SQL refusant tout UPDATE (le DELETE ligne à ligne n'est pas bloqué par trigger : la suppression d'un run entier — FK CASCADE — doit rester possible ; le code n'expose aucune suppression d'événement) |
| `agent_run_parcels` | détail retenues/écartées | les payloads d'événements ne portent que IDs + compteurs + agrégats |

`engine_versions` grave à la création du run : **le run servi épinglé** (`Q_A_RUN_LABEL`,
§7-J — exigence GO Q3), `rules_version()` (sha des 3 YAML de règles), la version du
prompt interpréteur (`m26a-v1`), le sha git court.

## 2 · Taxonomie des événements (fermée)

`run_started` (mission, brief_raw, **plan figé**) · `brief_parsed` · `clarification_requested` ·
`clarification_answered` · `step_started` · `step_completed` (moteur, résultat compact,
étiquette sourcé/estimé, durée_ms, compteur avant→après si filtrant) · `step_failed`
(code_erreur, résumé ≤ 200 car, jamais de stacktrace) · `run_paused` / `run_resumed` ·
`run_completed` (n_retenues, n_écartées, durée) · `run_failed` (code, message honnête).

**`run_cancelled` — VALIDÉ par Vic (revue M26-A, 27/07/2026), taxonomie DÉFINITIVE à
11 types.** Le mandat prévoyait le statut `cancelled` et `POST /cancel` sans événement
correspondant — sans `run_cancelled`, le statut ne serait plus dérivable de l'event log.
Nécessité structurelle actée ; toute extension ultérieure reste une décision Vic.

`reduce_run(events) → status` : fonction pure, états terminaux absorbants, testée sur
13 séquences (pause/reprise, clarification, échec, annulation, terminal absorbant).
Le filtre boussole (`copilote/boussole.py`) passe sur CHAQUE payload avant écriture :
clés nominatives bloquées sauf preuve personne morale/publique (types alignés sur
`proprietaire_type`) ; `prenom`/`contact`/`dirigeant` bloqués même en contexte PM.

## 3 · Plans (100 % déterministes, figés dans run_started)

```
PLAN_INSTRUIRE  = criblage* · faisabilite* · risques* · marche_dvf · mutation · assemblage*
PLAN_SHORTLIST  = criblage* · faisabilite* · risques* · mutation · assemblage_court*
PLAN_VERIFIER   = scoreur_unitaire* · assemblage_verdict*        (* = bloquant)
```

## 4 · Décisions prises (avec le GO de Vic)

1. **Mutation = champion P, lecture seule** (GO Q1). L'étape `mutation` lit
   tier/rang/percentile du run servi épinglé, étiquette Sourcé. Le Radar Mutation V1
   (NON SERVI, RR 0,51) n'est jamais appelé — un test le verrouille
   (`test_mutation_v1_jamais_dans_un_wrapper`).
2. **Propriété du run = compte_id + utilisateur_id nullable** (GO Q2). Le quota est
   compté sur le MÊME scope : compte connecté → sujet `c:<compte_id>` ; bucket pilote →
   sujet session/IP de `protection.sujet_de`. Kind `agent`, limite
   `LABUSE_COPILOTE_QUOTA_JOUR` (défaut provisoire 10), 429 même style que M23, compté
   AVANT `run_started`. Testé quota ACTIF (hors dev mode) : 429 honnête, aucun run créé,
   aucun moteur appelé.
3. **Criblage = lecture seule** (GO Q3) : run servi épinglé + `parcel_zone_plu` +
   `cascade_results` (PPR rouge, ABF). Aucun score recalculé ; chaque filtre journalise
   avant→après ; plafond `copilote_max_candidats` (24) JAMAIS silencieux
   (`plafonne_a` dans le payload).
4. **Entonnoir faisabilité** : moteur 11 étapes existant (`parcel_faisabilite`), étiquette
   Estimé. SDP estimée < cible → écartée motif tracé ; non calculable → écartée
   « non vérifiable » (boussole). La conversion logements→SDP est du CODE :
   `SDP_PAR_LOGEMENT_M2 = 70`.
5. **marche_dvf annote, n'élimine pas** : charge foncière = Estimé ; un Estimé n'écarte
   jamais une parcelle (le rapprochement budget est porté à la note, pas tranché).
6. **Zéro retenue = run `done`, n_retenues=0** — aucun assouplissement silencieux.
7. **Exécution in-process** (thread démon, pas de worker séparé en M26-A). Budgets :
   timeout global 120 s, plafond 12 appels moteurs (retries inclus), vérifiés avant
   chaque étape. Retry ×1 uniquement sur transitoire (timeout/connexion).

## 5 · API + SSE

`POST /api/copilote/runs` · `GET /runs` · `GET /runs/{id}` (état DÉRIVÉ de l'event log) ·
`GET /runs/{id}/events` (SSE) · `POST /runs/{id}/answer` · `POST /runs/{id}/cancel`.
Cloison : toutes les routes filtrent `compte_id IS NOT DISTINCT FROM :cid` (accès croisé
→ 404, testé).

**SSE (documentation demandée au GO)** : `StreamingResponse` + **polling de
`agent_events` toutes les 0,4 s** (constante `_POLL_S`), pas de LISTEN/NOTIFY en M26-A.
Rejeu d'abord (`after_seq` → reprise exacte, ni doublon ni trou, testé), puis streaming ;
le flux se ferme sur événement `fin` quand le run devient terminal ou `awaiting_user`,
et au plus tard après 180 s (`_SSE_MAX_S`). **Déconnexion client** : Starlette ferme le
générateur ; le run continue en arrière-plan ; un rafraîchissement retombe sur le même
fil via `after_seq`. Si le polling devient un point de charge → M26-B (décision GO).

## 6 · Tests

- **81 nouveaux tests copilote** (objectif ~40) : réduction (13 séquences), boussole,
  émission append-only (trigger testé), interpréteur (jeu figé de 16 phrases + 4 cas
  verifier_adresse : commune absente, k€, deux communes, hors-sujet, injection —
  sortie hors schéma REJETÉE, anti-invention de références), plans snapshot, exécuteur
  (retry unique, bloquant/non-bloquant, budgets, annulation, zéro retenue), API
  (SSE reconnexion, **quota actif hors dev mode**, cloison).
- L'interpréteur est testé avec un LLM injecté à sorties figées (comportement attendu du
  prompt `m26a-v1`) : c'est toute la chaîne de validation code qui est couverte — aucun
  appel réseau en test.
- Non-régression : voir §7.

## 7 · Vérifications d'intégrité (sur la base de ce poste — décision GO Q4)

- Tiers du run servi `q_v7_defisc` : **120 / 1031 / 3587 / 72980 / 353945** — vérifiés
  avant ET après mandat (les écritures du Copilote ne touchent que ses 3 tables).
- Champion P intouché : artefact + FREEZE non modifiés (lecture seule par SQL).
- Golden : `qa/golden_check.py` contre la base applicative de ce poste + API locale —
  résultat en §9.
- Aucun moteur existant modifié. Fichiers hors `copilote/` touchés : `api/app.py`
  (+4 lignes : router + ensure), `config.py` (+4 constantes), `tests/conftest.py`
  (+3 lignes : ensure tables copilote).

## 8 · Limites connues

- **RÈGLE PRODUIT (Vic, revue M26-A — s'applique à toute présentation du résultat)** :
  quand un plafond a mordu, le résultat ne peut JAMAIS être présenté comme exhaustif.
  Un « 0 retenue » après troncature doit dire « aucune retenue parmi les N examinées
  sur M candidates » — jamais « aucune opportunité ». État au 27/07 : la troncature est
  journalisée dans `step_completed` du criblage (`plafonne_a`, `n_pool`, compteurs
  avant→après) mais le récap `run_completed` (`n_retenues`/`n_ecartees`) ne la requalifie
  pas encore — correction à faire selon l'arbitrage plafond (voir ci-dessous), AVANT
  toute UI M26-B.
- **Plafond du criblage (arbitrage Vic en cours, bloquant pour le merge)** :
  `copilote_max_candidats = 24`, appliqué en fin de criblage après les filtres du brief,
  tri déterministe tier (brûlante→à creuser) puis rang du champion P puis IDU. Mesuré
  (Saint-Paul, run 1) : pool servi 13 155 (= 4 tiers non écartés sur 51 129 parcelles),
  les 24 examinées = les 24 meilleures brûlantes → le « 0 retenue » du run 1 signifie
  « 0 parmi les 24 meilleures brûlantes », pas « rien à Saint-Paul ». Débit mesuré de la
  faisabilité : 13,1 ms/parcelle (échantillon 300, pseudo-aléatoire md5) → pool complet
  ≈ 172 s, hors budget 120 s d'un facteur ~1,4 (pas une impossibilité d'échelle).

- L'exécution est in-process : un redémarrage du serveur laisse un run `running` orphelin
  (pas de reprise automatique en M26-A ; l'event log permet de le constater honnêtement —
  une reprise/watchdog est un candidat M26-D).
- `run_paused`/`run_resumed` sont dans la taxonomie et la réduction (testés) mais aucun
  endpoint ne les émet en M26-A.
- Le SSE par polling (0,4 s) est dimensionné pilote, pas charge — bascule LISTEN/NOTIFY
  possible en M26-B sans toucher au contrat.
- L'interpréteur réel dépend d'`ANTHROPIC_API_KEY` : sans clé → `run_failed`
  `ia_indisponible` honnête (jamais de brief deviné). Testé.
- `verifier_adresse` sur adresse libre passe par le géocodage BAN du scoreur existant
  (appel réseau) — l'IDU reste 100 % local.

## 9 · Point d'arrêt B — démo (exécutée le 27/07/2026, base de ce poste)

`scripts/demo_copilote_m26a.sh` (curl uniquement, pas d'UI). Serveur local sur la base
applicative, interpréteur réel (Sonnet, clé du poste). **Prérequis découvert** :
`anthropic` est dans l'extra `[ai]` — l'interpréteur exige `pip install -e ".[ai]"`.

**Run 1** — brief exact du mandat : « collectif 6 logements Saint-Paul, 480 k€, hors PPR
rouge » (run `68978431…`) :
- `brief_parsed` : communes ["Saint-Paul"], logements 6 → **sdp_cible 420 m² (conversion
  CODE)**, budget 480 000 €, exclure_ppr_rouge true — rien d'inventé par le modèle ;
- criblage Sourcé : pool 13 155 → plafond 24 (brûlantes, journalisé `plafonne_a`) ;
- faisabilité Estimé : 24 → 0 (motifs tracés « SDP estimée insuffisante (X m² < 420) ») ;
- **run `done` en 5,9 s, n_retenues=0, n_ecartees=24** — zéro retenue servi tel quel,
  24 lignes `agent_run_parcels` avec motifs. Reconnexion SSE `after_seq=3` : reprise
  exacte au seq 4, aucun doublon.

**Run 2** — même brief + « terrain d'au moins 2000 m² » (run `634b4d8f…`) :
- criblage : 13 155 → surface_min 703 → plafond 24 (15 chaudes, 9 réserve) ;
- faisabilité : 24 → 22 ; charge foncière calculable pour les 22 (DVF) ; champion P
  Sourcé (tiers par candidat) ; **run `done` en 5,6 s, 22 retenues / 2 écartées en base**.

**Vérifications finales** : golden **116/116 PASS** (API locale portant le code Copilote,
base applicative) · tiers `q_v7_defisc` **120/1031/3587/72980/353945** inchangés au bit
près après démo · non-régression pytest : les 17 échecs + 66 erreurs constatés sur la
branche sont **identiques à `origin/main`** sur ce poste (diff vide — préexistants :
test_front_reliquats, test_protection, setup test_api…) ; la branche ajoute exactement
ses 81 tests verts (1167 passés vs 1086 baseline).
