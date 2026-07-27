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

## 3 · Plans (100 % déterministes, figés dans run_started) — v2, revue plafond 27/07

```
PLAN_INSTRUIRE  = criblage* · filtre_geometrique* · faisabilite* · risques* ·
                  marche_dvf · filtre_budget · mutation · assemblage*
PLAN_SHORTLIST  = criblage* · filtre_geometrique* · faisabilite* · risques* ·
                  mutation · assemblage_court*
PLAN_VERIFIER   = scoreur_unitaire* · assemblage_verdict*        (* = bloquant)
```

Cascade de coût (arbitrage Vic) : filtre bon marché AVANT la faisabilité (exhaustive,
parallèle) ; charge foncière sur TOUTES les retenues ; budget AVANT toute troncature ;
tri champion P APRÈS la faisabilité (classer les retenues, jamais choisir lesquelles
examiner) ; restitution top-20 à l'assemblage.

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
- **Plafond du criblage — RÉSOLU (arbitrage Vic « option c », 27/07)** : le plafond 24
  au criblage était un faux négatif structurel (vérité terrain : **3 852** parcelles de
  Saint-Paul satisfont le brief du run 1, le pipeline v1 en servait 0). Remplacé par la
  cascade de coût du §3 : filtre géométrique prouvablement conservateur (voir §9-bis),
  faisabilité exhaustive parallèle (4 sessions, pool borné, fermé en fin d'étape,
  annulation coupant les travaux en cours), garde-fou de dernier recours
  `copilote_max_candidats = 2000` avec requalification intégrale s'il mord.

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

## 9-bis · Revue plafond (« option c ») — filtre géométrique, mesures et preuves (27/07)

**Filtre géométrique** (`filtre_geometrique`, bloquant, avant faisabilité) : une parcelle
n'est écartée que si son MAJORANT de SDP — emprise insetée du recul (`ST_Buffer(−recul)`,
SQL) × niveaux(hé) × `coef_occupation` — reste sous la cible moins 1 m² (marge absorbant
l'ARRONDI du moteur, 8 cas limites à SDP = 420 pile sans elle). Toutes les valeurs sont
lues AUX MÊMES SOURCES que le moteur (`plu_rules.resolve_zone`, `Hypotheses.charger()`)
— jamais dupliquées : si le moteur change, le filtre suit. Zones sans plafond exploitable
(`à_vérifier`) ou dont l'attribution pourrait différer de celle du moteur (non-U/AU,
habitat interdit) : NON filtrées — la faisabilité tranche. Étiquette Sourcé (PLU calibré)
/ Estimé (repli générique 9 m ≈ 3 niveaux), provenance dans chaque motif d'écartement.

**Preuves 0 faux négatif** (vérité terrain complète, moteur exécuté sur TOUT le pool) :
Saint-Paul (calibré) : 13 155 parcelles, 3 852 retenues réelles, 0 FN · Bras-Panon
(générique) : 686, 177 retenues, 0 FN · Le Port (générique) : 1 333, 309 retenues, 0 FN.
Vérification complémentaire du filtre TEL QU'IMPLÉMENTÉ (résolution progressive des
renvois de zones incluse) : faisabilité exécutée sur les **8 905 parcelles qu'il écarte**
au brief du run 1 → **0 faux négatif** (aucune n'aurait été retenue par le moteur).

**Sémantique du filtre budget** : « dans le budget » = prix probable du foncier (médiane
terrain sectorielle × surface, `dvf_secteur_medianes`, Estimé) ≤ `budget_max_eur`.
Le sens « charge supportable ≥ budget » a été écarté : il exclurait les parcelles BON
MARCHÉ (prix probable 200 k€, charge 300 k€ → parfaitement dans un budget de 480 k€).
Sans prix probable : « non estimable — non filtrée », jamais écartée sur une absence.
**Pas d'hybride `score_e`** (condition Vic vérifiée) : `score_e` est un pipeline batch
DIFFÉRENT — la charge servie par le Copilote est calculée LIVE par les mêmes fonctions
que la fiche (`sector_price` + `compute_bilan`).

**DETTE PRODUIT PRIORITAIRE (consignée à la demande de Vic — mandat dédié à prévoir,
RIEN modifié ici).** Deux méthodes de charge foncière coexistent et sont SERVIES à des
endroits différents : un même utilisateur peut lire deux chiffres différents pour la
même parcelle dans la même session. Ce n'est pas faux au sens de la boussole (les deux
sont Estimé, tracés), mais l'incohérence coûte autant que l'erreur devant un comité.
| | `score_e` (batch, NUIT 21/07, `bilan-neuf-v2`) | bilan live (`sector_price`+`compute_bilan`) |
|---|---|---|
| Servi dans | fiche (chip marge), scoreur d'adresse, dossier banquier | faisabilité fiche/Flash, briques PDF, **Copilote M26-A** |
| Base de surface | SDP **résiduelle** (`parcel_residuel`) | SHAB **vendable** de la fourchette faisabilité |
| Prix de sortie | **NEUF** reconstruit (`dvf_prix_sortie_neuf`, secteur→commune, ~3 688 €/m² méd.) | médiane DVF existant (ancien+VEFA), rayon adaptatif 500→1500 m→commune |
| Coût construction | 2 550 €/m² (point, milieu de fourchette) | 2 300–2 800 €/m² (fourchette bas/haut) |
| Coefficients | CA×0,79 (marge 9 % + frais 12 %), plancher/habitable 1,15, VRD 0 | mêmes taux mais bilan complet (fourchette, mixité sociale, params sectoriels si calibrés) |
| Sortie | point unique (`charge_supportable`, `prix_probable`, `marge_estimee`) | fourchette bas/central/haut + fiabilité héritée du prix |
| Fraîcheur | snapshot (`computed_at` 21/07, `hypotheses_version` unique) | calcul à la demande sur l'état courant |

**Garde-fou — arbitrage final (Vic, 27/07) : 5 000, validé sur mesure.** La charge live
était DÉJÀ parallélisée (même `_en_parallele` que la faisabilité) — mesure dédiée :
mono 13,4 ms/p vs 4 sessions 7,1 ms/p, speedup ×1,9 seulement (contention PostGIS sur
les requêtes DVF à rayon). La mesure décisive est l'EXHAUSTIF de bout en bout, garde-fou
levé : **56,8 s** (et 55,3 / 56,2 s aux runs de confirmation) — largement sous les 120 s.
Le garde-fou passe donc à **5 000** (budget inchangé), et reste un plafond en PARCELLES,
jamais en temps (reproductibilité du même brief d'un jour à l'autre — gravé en
commentaire de la constante). S'il mord : requalification intégrale.

**Indicateur « au-dessus de la charge supportable »** (Vic, revue budget — un indicateur,
JAMAIS un filtre) : pour chaque retenue où prix probable ET charge sont connus,
`au_dessus_charge_supportable = prix probable > charge foncière supportable` — « dans le
budget de l'acheteur mais l'opération ne supporte pas son prix ». La parcelle reste
retenue, l'utilisateur arbitre (logique Argumentaire de négociation). Étiquette Estimé.
Porté par parcelle (payload marche_dvf + restituées) et compté au récap.

**Run de preuve FINAL** (brief exact du mandat, config par défaut, 27/07) — **56,2 s** :
entonnoir `pool 13 155 → filtre_geometrique 4 250 → examinées 4 250 (garde-fou 5 000
non mordu) → retenues 2 947 → dans_budget 2 753 (+194 non estimables non filtrées,
905 écartées budget) → restituées 20` · `exhaustif: true` · 1 836 retenues marquées
au-dessus de la charge supportable · faisabilité 3 852/4 250 en 14,6 s (4 sessions) ·
charge live 3 852/3 852 en 33,0 s · le « 0 retenue » du pipeline v1 est devenu
**2 947 retenues exhaustives** sur le même brief.

## 10 · Information produit (demande Vic, revue calibrage) — règles chiffrées PLU

**Communes en repli générique (22)** : Les Avirons, Bras-Panon, Cilaos, Entre-Deux,
L'Étang-Salé, Petite-Île, La Plaine-des-Palmistes, Le Port, La Possession, Saint-André,
Saint-Benoît, Saint-Joseph, Saint-Leu, Saint-Louis, Saint-Philippe, Saint-Pierre,
Sainte-Marie, Sainte-Rose, Sainte-Suzanne, Salazie, Le Tampon, Les Trois-Bassins.
(Calibrées : Saint-Paul, Saint-Denis. Vérifié moteur en main : `calibree=True` pour 2
communes exactement.)

**Contenu d'un `config/plu_<commune>.yaml` calibré** (dimensionnement de la re-gravure) :
Saint-Paul = 277 lignes, Saint-Denis = 312. Racine : `source` (document, URL, offset PDF),
`mode`, `regles_transverses`, `hypotheses_faisabilite`, `zones` (Saint-Paul : 35),
`zones_au_renvoi`, `zones_au_st`, `zones_non_constructibles`. Par zone : `he_m`, `hf_m`,
`emprise_sol_pct`, `recul_voirie_m`, `recul_limites_sep_m`, `stat_logement`,
`pleine_terre_pct`, chacun avec sa source (`*_src` : article + page) et ses notes ;
valeurs `a_verifier` admises (jamais comblées). Extraction manuelle depuis le règlement
PDF, sourcée article/page — c'est le travail par commune.

**Consommateurs des règles chiffrées** (donc en repli générique sur 22 communes) :
- Faisabilité 11 étapes (fiche, Flash) et tout ce qui l'appelle : `briques_pdf.collect`
  → **dossier banquier O1**, **rapport de potentiel M22-D**, **pré-dossier PC (Lot 5)**,
  `api/modules.py` (3 appels), **Copilote M26-A** ;
- `api/moteurs.py` (SimulPLU), `api/traducteur.py` (traducteur PLU),
  `api/lettre_zonage.py`, `plu_reglement.py` (deep-links règlement — repli GPU propre) ;
- **chaîne du résiduel** : `faisabilite/residuel.py` → `parcel_residuel`
  (`sdp_residuelle_m2`) consommé par la couche cascade `residuel_socle` (étage 0 étendu
  du scoring SERVI), la shortlist, le renouvellement et `score_e` (marge €).

**À dire sans euphémisme (exigence Vic)** : la portée du repli générique à 22 communes
NE SE LIMITE PAS à la faisabilité affichée. Via la chaîne du résiduel, des règles
génériques (hé 9 m ≈ 3 niveaux, reculs par défaut) entrent dans `residuel_socle`, donc
dans le SCORING SERVI (tiers Q×A), dans la shortlist, dans le renouvellement et dans
`score_e` — sur 22 communes sur 24, les « droits à construire » qui irriguent ces scores
sont une estimation générique, pas une lecture du règlement. C'est étiqueté Estimé là où
c'est affiché, mais l'ampleur systémique relève d'un arbitrage produit (re-gravure des
YAML PLU commune par commune : ~300 lignes sourcées article/page chacune, cf. supra).
