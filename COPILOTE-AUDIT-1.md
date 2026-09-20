# COPILOTE-AUDIT-1 — D'où le Copilote tire chaque réponse

**Branche** `feat/copilote-audit-1` · **Étape 0** `git HEAD = 15cffe088ca3594894c803740a905eff567766cf` (main).
**Session** backend `:8085` (uvicorn, `PYTHONPATH=src` sur ce worktree, venv PDF-capable), Vite non lancé.
**Portée** lecture seule — aucun code applicatif modifié, aucun merge, aucun `labuse circuit`. Un seul commit : ce rapport + les preuves `captures/copilote-audit1/`.

---

## ⚠ Blocage live — points 3 et 5 non rejoués

La clé `ANTHROPIC_API_KEY` du poste renvoie **« solde de crédits Anthropic épuisé »** sur chaque appel
(`GET /ia/status → raison: "solde de crédits Anthropic épuisé — l'accès à l'API est suspendu"` ;
preuve : `captures/copilote-audit1/point3_fiche10.json`, 10/10 réponses = dégradation honnête). Le Copilote
se dégrade proprement (« le service d'analyse est indisponible… l'équipe est alertée »), il n'invente rien —
mais **aucune réponse live n'est produite**. Décision Vic : livrer l'audit **au niveau du code**, marquer les
deux livrables live **BLOQUÉS**, les rejouer quand la clé sera créditée. Le jeu des 10 questions
(`q10.json`) et des 16 adversariales (`q16.json`) est **prêt à rejouer** en un appel :
`python captures/copilote-audit1/ask.py captures/copilote-audit1/q16.json`.
La vérité-terrain de la fiche 97410000AN0347 est capturée (`fiche_parcelle_raw.json`) pour la comparaison.

---

## Les quatre chiffres en tête

| Chiffre | Valeur | Détail |
|---|---|---|
| **N — lectures par le registre** | **0** | Aucun outil ni branche d'intention ne résout un id de `src/labuse/registre/`. Le Copilote lit via des **facettes/moteurs** (`api.app`, `api.modules`, `faisabilite`) et du **SQL inline**, jamais le système d'ids du registre. |
| **M — lectures par SQL direct** | **5** | Sites de SQL inline : `parcelle_personne_morale` (`outils.py:306`), `entite_acronyme` (`outils.py:247-273`), `parcels⋈parcel_zone_plu` dans `destination_zone` (`outils.py:585-588`), criblage run-scoped `copilote/moteurs.py:120` (mission lourde, lancée par le front), infra `agent_runs/agent_events` (`copilote/executeur.py`). **3 au chat métier + 1 run-scoped + 1 infra.** |
| **K — faits en dur périmés** | **0 vus au client** | Aucun fait périmé n'atteint le client. Périmés mais **internes (commentaires)** : 2 (voir liste). Périmés **latents** (millésimes en dur corrects aujourd'hui) : 2. |
| **J — adversariales tenues / 16** | **BLOQUÉ (non rejoué)** | Crédits épuisés. Prédiction code : **16/16 structurellement protégées** (lecture prouvée, garde déterministe, ou refus par design) — **0 chemin d'invention trouvé**. À confirmer live. |

**Lecture d'ensemble.** Le Copilote v2 est **conçu pour ne pas inventer** : un oracle numérique par
conversation (`registre_faits`), une **garde formelle déterministe** qui retire tout chiffre-donnée hors
fourchette d'une réponse libre (`garde_generale_sans_chiffre`, `answering.py:744-770`), un gabarit
héros vérifié nombre par nombre, et une recherche web **gâtée sur citations réelles**. Le risque n'est pas
l'invention ; c'est le **silence sur des faits que la fiche montre mais qu'aucun outil n'expose**
(propriétaire, taxe, risques, pente — voir point 3).

---

## 1. La carte des lectures — 7 (en fait 9) intentions, 10 (pas 6) outils

Le routeur classe en **9 intentions** (`router.py:29` : QUESTION, EXPLIQUER, PREPARER, OUTIL, RECHERCHE,
VERIFICATION, VEILLE, PROJET, HORS_SUJET). Les **6 outils SQL** du doc M78 d'origine sont devenus **10**
(`OUTILS`, `outils.py:608-619`).

### 1a. Ce que chaque intention exécute (dispatch `answer()` → `_answer_with_route`, `answering.py:1274`)

| Intention | Exécute & lit une donnée ? | Branche | Ce qui se passe |
|---|---|---|---|
| **QUESTION** | **OUI** | `answering.py:1360-1405` | `_select_tool` (LLM choisit un outil) → un des 10 `OUTILS` → `_formuler`. Voie de donnée principale. |
| **EXPLIQUER** | Exécute, **0 donnée LABUSE** | `answering.py:1289-1290` → `_general` | LLM « voie b » (connaissance générale). Aucune lecture base. Badgé `general=True`. |
| **PREPARER** | Fiche **si IDU** | `answering.py:1291-1292` → `_preparer` | Lit `_substance→fiche_parcelle` uniquement si un IDU est au contexte ; sinon prose sans donnée. |
| **VERIFICATION** | **OUI** (sur `confirme`) | `answering.py:1337-1339` → `missions_lourdes.verification` (`:51`) | Lit `fiche_parcelle` + `build_marche_commune`. Avis prix déterministe. |
| **RECHERCHE** | Partiel | `answering.py:1321-1333` → `_mission_recherche` | (a) « montre-moi » carte + commune → `compter_parcelles` au chat ; (b) sinon récap-péage, run lourd lancé par le **front** via `/api/copilote-v2/runs` (moteur M26-A). |
| **VEILLE** | NON (renvoi) | `answering.py:1340-1342` | `_refus_voie` → Surveillance. |
| **PROJET** | NON (renvoi) | `answering.py:1334-1336` | `_refus_voie` → Projets. |
| **OUTIL** | NON (renvoi) | `answering.py:1343-1352` | `_refus_voie` → Courriers / barre Outils. |
| **HORS_SUJET** | NON (constante) | `answering.py:1357-1358` | Refus en dur. |

> ⚠ **Commentaires périmés** : `router.py:26-28` et `answering.py:1318-1320` (M118) affirment que
> RECHERCHE/VERIFICATION sont des refus-voie. **Faux depuis SUITE-1 S9** (`answering.py:1188-1194`) qui les
> a rapatriés au chat. Le code fait autre chose que ce que ses commentaires disent.

### 1b. Les 10 outils (`outils.py`) — chemin de lecture

| Outil | Donnée lue | Chemin | Source finale | file:line |
|---|---|---|---|---|
| `compter_parcelles` | comptage par facette | moteur-nommé | `filtre()`/`FiltreCriteres` → `mvt_parcels`, `parcel_zone_plu` (**zone = dominante**) | `outils.py:161` |
| `parcelles_par_entreprise` | patrimoine d'une PM | moteur + SQL | `patrimoine()` ; nom→SIREN inline `parcelle_personne_morale` | `outils.py:322` ; SQL `:306-309` |
| `fiche_parcelle` | 1 parcelle | **payload** | `_q_v2_fiche()` **run-scoped — LE MÊME que la fiche** | `outils.py:336` |
| `stats_commune` | SRU + INSEE logement | moteur | `commune_contexte()` | `outils.py:357` |
| `delais_instruction` | délai médian | moteur | `velocite()` → Sitadel | `outils.py:377` |
| `marche` | terrain nu/neuf/loyer/tendance | moteur | `build_marche_commune()` → DVF/Sitadel/DHUP | `outils.py:402` |
| `compter_piscines` | piscines détectées | moteur | `prospection_piscines()` → `parcel_equipements` | `outils.py:540` |
| `compter_permis` | permis sur N mois | moteur | `permis()` → Sitadel | `outils.py:562` |
| `destination_zone` | verdict « puis-je ouvrir X » | moteur + SQL | `plu.destinations.verdict()` ; zone inline `parcels⋈parcel_zone_plu` | `outils.py:598` ; SQL `:585-588` |
| `recherche_web` | fait web (élus, actualité) | **LLM web externe** | Anthropic `web_search_20250305` ; source=`web` | `outils.py:493-496` |

Aide : `entite_acronyme` (seed CSV + SELECT) inline, `outils.py:247-273`. Outil `divisibilite` (M82) **retiré**
et inatteignable (`outils.py:521-525`).

### 1c. Décompte des lectures
- **registre-id : 0** · **SQL direct : 5** · **moteurs/facettes nommés : 8** (`filtre`, `patrimoine`,
  `commune_contexte`, `velocite`, `build_marche_commune`, `prospection_piscines`, `permis`,
  `plu.destinations.verdict`) · **payload/fiche : 1** (`_q_v2_fiche`, réutilisé ~4×) · **texte en dur : 4**
  (`HORS_SUJET`, `_CAPACITE_TXT`, `GENERAL_SYSTEM`, `PREPARE_SYSTEM`) · **web externe : 1**.

---

## 2. Ce qu'il dit en dur — confronté à la réalité du jour

**Le code est bâti pour ne PAS coder les faits en dur.** Les comptages (parcelles, permis, délais, prix)
sont servis live par les moteurs ; la garde 2.6 retire tout chiffre-donnée hors fourchette des réponses
libres. Faits littéraux réellement rendus au client, chacun confronté :

| Fait en dur (cité) | file:line | Catégorie | Réalité du jour | Verdict |
|---|---|---|---|---|
| `CADASTRE_MILLESIME = "Etalab 2026-06"` | `outils.py:25` | date (servie `millesime` de `compter_parcelles`) | `app.py:1248,1285` idem | **CURRENT** mais *latent-faux* (en dur, pas lu de `data_sources.source_millesime`) |
| `"détection ortho/IA (BD ORTHO 20 cm 2025)"` | `outils.py:547` | date+déf (servie `source` de `compter_piscines`) | `ortho_tiles.py:32 MILLESIME="2025"` idem | **CURRENT** mais *latent-faux* (en dur vs `millesime_servi(db)`) |
| `"…24 communes de La Réunion (ex. …)"` | `outils.py:102` | comptage communes (refus client) | `filtres/echantillons/communes.json` = 24 | **CURRENT** |
| `IDU (14 caractères)` | `router.py:106,166` ; `answering.py:74…` | format | IDU Réunion = 14 car. | **CURRENT** |
| `compter_permis défaut 24 mois` | `outils.py:562,568` ; `answering.py:81` | fenêtre (config) | cohérent partout | **CURRENT** |
| DVF `n_ventes < 5 → échantillon insuffisant` | `missions_lourdes.py:80,102` | seuil (client) | `cascade/layers/phase2.py:44 min_ventes_fiable=5` | **CURRENT** |
| Défs SDP/SHAB/charge foncière ; glossaire créole ; art. `L752-1`/`R151-28` | `answering.py:722-725,711-712` ; `outils.py:577,583` | définitions | stables | **CURRENT** |
| `# les 11 outils invisibles du registre` | `answering.py:1447` | comptage outils (**commentaire**) | la table `_CONCEPT_MAP` n'en tient plus 11 (dormants retirés) | **PÉRIMÉ (commentaire, non-client)** |
| `# haiku 100 % au gate (45 cas, > 97,1 % sonnet)` | `router.py:8-9` | mesure (**commentaire**) | benchmark Phase-0 sur modèles anciens, jamais rejoué (auj. haiku-4-5 / sonnet-4-6) | **PÉRIMÉ-ish (commentaire, historique)** |
| **Comptage sources / couches** | — | — | **AUCUN n'est codé en dur dans copilote_v2** (hors périmètre du Copilote) | **N/A** |

**K = 0 faux vu au client.** Tout littéral visible est CURRENT. Les seuls périmés sont **2 commentaires
internes** ; s'y ajoutent **2 millésimes en dur latents-faux** (corrects aujourd'hui, mais divergeront
silencieusement au prochain ingest — le motif `millesime_servi(db)` existe à 20 lignes de là).

---

## 3. Un seul moteur — parité Copilote / fiche (⚠ live BLOQUÉ, analyse code)

**Verrou structurel** : l'outil `fiche_parcelle` appelle **`_q_v2_fiche(db, idu, run_label=runs.current())`**
(`outils.py:336`) — **exactement la fonction que sert l'endpoint fiche** (`app.py:5164`). Là où le Copilote
répond un fait de parcelle *via cet outil*, la divergence avec la fiche est **impossible par construction**
(même moteur, même run servi). **Mais** l'outil ne restitue au formulateur que **5 champs** :
`commune, surface_m2, zone (=reg[0].zone), verdict (score_v2), etage0` (`outils.py:341-344`) — il **jette**
propriétaire, taxe, risques (pourtant *lus* par `_q_v2_fiche`), pente. Et **aucun autre outil** ne lit le
propriétaire / la TA / les risques / la pente *par IDU*. Conséquence sur les 10 questions
(vérité-terrain fiche capturée) :

| # | Question (97410000AN0347) | Vérité fiche | Outil qui l'expose | Même moteur ? | Verdict prédit (code) |
|---|---|---|---|---|---|
| 1 | Commune ? | Saint-Benoît | `fiche_parcelle.commune` | **OUI** (`_q_v2_fiche`) | parité garantie |
| 2 | Surface ? | 4 501 m² | `fiche_parcelle.surface_m2` | **OUI** | parité garantie |
| 3 | Zone PLU ? | **N** (zone unique, dominante) | `fiche_parcelle.zone=reg[0]` | **OUI** | parité garantie · ⚠ `reg[0]` = 1re zone, pas forcément la dominante si multi-zones |
| 4 | Propriétaire ? | Commune de Saint-Benoît (public, SIREN 219740107) | **AUCUN** | — | **gap** : pas d'outil owner-par-IDU → refus ou risque invention |
| 5 | Taux TA communal ? | **5 %** (depuis 01/01/2022) | **AUCUN** | — | **gap** : la TA est dans la fiche mais aucun outil ne l'expose |
| 6 | Risques naturels ? | PPR rouge 100 % (rédhibitoire) + bleue inondation ~17 % | **AUCUN** (lus par `_q_v2_fiche`, jetés par l'outil) | — | **gap** |
| 7 | Pente ? | 3,4° moy / 11,2° max | **AUCUN** | — | **gap** |
| 8 | Score / potentiel ? | **Écartée** (percentile 13,76) | `fiche_parcelle.verdict` | **OUI** | parité garantie |
| 9 | Commune (redite) ? | Saint-Benoît | `fiche_parcelle.commune` | **OUI** | parité garantie |
| 10 | Capacité constructible ? | nulle (zone N + PPR rouge) | **AUCUN** (déclaré non-applicable) | — | par design : renvoi Faisabilité, **pas** de calcul |

**Zone : dominante, pas confetti.** `compter_parcelles` lit `parcel_zone_plu` = **zone dominante** par
parcelle (`app.py:1210`). `fiche_parcelle` prend `reglement_plu.zones[0]`. Ici zone unique **N** → pas de
confetti. Caveat : `[0]` n'est pas explicitement trié par couverture — à surveiller sur une parcelle
multi-zones.

**Capacité : zonage.py ou vestige ?** **Ni l'un ni l'autre.** Aucun `import zonage`, aucun moteur de
constructibilité dans `copilote_v2`. Constructibilité/densité/capacité sont **déclarées non-applicables**
(`answering.py:138-139`), surfacées en `criteres_non_appliques`, et une demande de programme est renvoyée
au **prefill de l'outil Faisabilité** (`answering.py:1297-1301`). La division route vers `_division` qui ne
lit que zone/surface de la fiche et **refuse de calculer** en ouvrant l'Annuaire PLU (`answering.py:1646-1675`).

> **Synthèse point 3.** 4 questions sur 10 (commune, surface, zone, score) sont garanties **iso-moteur** avec
> la fiche. 5 (propriétaire, TA, risques, pente + capacité) n'ont **aucun outil** → le Copilote ne peut pas
> refléter la fiche : soit il refuse, soit il tombe en voie B où la garde 2.6 doit l'empêcher d'inventer un
> chiffre. **Ce n'est pas une divergence de moteur, c'est un trou d'outillage.** Confirmation chiffre-à-chiffre
> à rejouer live (crédits).

---

## 4. v1 et v2 — le nommage est un leurre

Le paquet `src/labuse/copilote/` **n'est pas mort** : c'est le **moteur de missions lourdes de v2**. Son
routeur `api/copilote.py` est monté sous le préfixe **`/api/copilote-v2`** (`copilote.py:42`), pas
`/api/copilote`. Les URLs `/api/copilote/*` (vrai v1) **n'existent plus** (0 référence dans `src/` et
`frontend/src/`).

- **v1 monté & appelable ?** Oui — `app.py:7388,7397` `include_router`. Endpoints (préfixe `/api/copilote-v2`) :
  `POST /runs`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events` (SSE), `POST /runs/{id}/answer`,
  `POST /runs/{id}/cancel`. Appelés par le front (`lib/copilote.ts:118-140`, `useCopiloteRun.ts`,
  `CopiloteView.tsx`). Tous les 9 fichiers `copilote/` sont **atteignables et sous tests**.
- **Portage des missions lourdes : FAIT par délégation, pas par réécriture.** RECHERCHE = vrai run cascade
  **commune par commune / parcelle par parcelle** via le moteur M26-A (`copilote/moteurs.py`), streamé en SSE.
  VERIFICATION = exécutée au chat par `missions_lourdes.verification` (déterministe DVF, sans run). La
  recherche/vérif **web** existe aussi (`recherche_web`). La décision « ne garder que v2 » est satisfaite en
  **réutilisant** le moteur v1 sous le préfixe v2.
- **v2 sait faire** : QUESTION (10 outils), EXPLIQUER (voie B gardée), PREPARER (script), VERIFICATION (avis
  prix), RECHERCHE (run lourd). **v2 ne fait pas au chat** : poser une veille (→ Surveillance), créer un
  projet (→ Projets), agir un outil métier (→ fiche/CRM/Outils), **calculer** une capacité/divisibilité.

**Vestiges v1** (voir liste dédiée) : `PLAN_SHORTLIST`/`PLAN_VERIFIER` + missions `shortlist`/
`verifier_adresse` + `assemblage_court`/`scoreur_unitaire`/`assemblage_verdict`/`interpreter_refs` :
atteignables **seulement** par appel API forgé ou tests — **morts depuis l'UI** (le front ne lance que
`mission='instruire'`, `CopiloteView.tsx:92`).

---

## 5. L'anti-invention, rejoué (⚠ live BLOQUÉ — mécanisme + prédiction)

**Machinerie anti-invention (code) :**
1. **Oracle numérique par conversation** — `registre_faits` : tout nombre servi par un outil est gravé
   (`copilote_faits` : `outil/cle/valeur/source/millesime`, `registre_faits.py:22-33`). Un nombre repris à un
   tour ultérieur **doit exister dans ce registre** ou il est rejeté (`registre_faits.py:1-13`).
2. **Garde formelle 2.6 (déterministe)** — `garde_generale_sans_chiffre` (`answering.py:762-770`) : dans une
   réponse libre (voie B), toute phrase portant un **chiffre-donnée à unité** (`€, €/m², m², parcelles,
   logements, %`) qui n'est **pas** une fourchette (« entre X et Y », « environ », « ~ »…) est **retirée** et
   remplacée par le renvoi aux outils. Pas de 2e appel LLM. Testée `tests/test_circuit1_lot2.py`.
3. **Gabarit héros vérifié** — `heros.py` vérifie chaque nombre contre le JSON source ; 2 échecs → gabarit
   déterministe sans modèle.
4. **Web gâté sur citations** — `recherche_web` ne rend un résultat **que** si des citations à URL réelles
   existent (`outils.py:499-515`) ; sinon `ok=False` (« rien trouvé »).

**Prédiction code sur les 16 adversariales** (`q16.json`, prêtes à rejouer) — **0 chemin d'invention** :

| Type | # | Chemin attendu | Protection |
|---|---|---|---|
| Comptages méta (sources / outils / couches / précision) | 1-4 | aucun outil ne les compte | refus / renvoi (pas de lecture → garde 2.6 en voie B) |
| Mafate | 5 | pas une des 24 communes | `resoudre_commune` → refus/clarif |
| Projection 10 ans | 6 | refus par design | intercept projection |
| Zone humide par IDU | 7 | aucun outil | gap → refus / voie B gardée |
| TA à Saint-Benoît | 8 | aucun outil TA-par-commune | gap → refus / voie B gardée |
| Piscines / permis / prix / délais / réserves / destination | 9-11,13-15 | `compter_piscines`/`compter_permis`/`marche`/`delais_instruction`/`compter_parcelles`/`destination_zone` | **lecture prouvée** (+ réserve échantillon) |
| SCI inconnue | 12 | `parcelles_par_entreprise` SIREN absent | vide honnête (pas d'invention) |
| TVA VEFA ANRU (voie B) | 16 | `_general` | **garde 2.6** retire tout chiffre précis hors fourchette |

**J = à confirmer live.** Prédiction : **16/16 tenues** (10 refus/renvoi/vide honnête protégés + 6 lectures
prouvées). Le seul risque résiduel identifié : une phrase hallucinée *à côté* d'une vraie citation web
(la garde vérifie la présence de citation, pas le mapping phrase↔citation) — atténué par le format
≤ 2 phrases / ~180 car.

---

## 6. Le web

- **Déclenchement** : (a) chip **« web »** → court-circuit direct `_reply_web` sans routeur
  (`answering.py:511-512`) ; (b) le sélecteur choisit `recherche_web` comme **« DERNIER RECOURS (M78-ter) »**
  (`answering.py:98-101`) — seulement si aucun outil interne ne couvre, dans la barrière « foncier/urbanisme/
  collectivités de **La Réunion** ». `SELECT_SYSTEM` martèle « la BASE LABUSE prime TOUJOURS ».
- **Réel, pas de mémoire** : appel natif Anthropic `web_search_20250305` (`outils.py:493-496`), SDK direct,
  timeout 45 s, `max_uses=3`. Résultat rendu **uniquement si citations à URL présentes**.
- **Étiquetage client (non négociable)** : `"Source : web · {domaine} · consulté le {date}"` + flag `web=True`
  (`answering.py:467-471`), **jamais** les badges données « Sourcé/Estimé ». Pas de citation → refus honnête,
  pas de fabrication.

---

## 7. Le journal et le coût

- **Deux journaux distincts.** (1) **Télémétrie serveur** `copilote_telemetrie` (`telemetrie.py`) —
  genres `refus/critere_non_traduisible/web_servi/feedback`, demande **anonymisée** (≤500 car., « aucun
  identifiant client stocké »), servie **admin** en agrégat (`GET /telemetrie`). (2) **Journal d'événements
  client** des missions lourdes : `CopiloteView.tsx:49-72` rend chaque event `#{seq} {kind} {JSON.stringify(payload)}`.
- **SQL exposé au client ?** **Non.** Les payloads sont des **résultats métier** (`resultat`, `etiquette`,
  `duree_ms`, `compteur`, `mention_sdp`, `calibrage`), pas des requêtes. Le SQL reste serveur (`events.py`).
  Le fil propre (`FilInstruction.tsx`) n'affiche que libellé moteur fixe + compteur avant→après. Le bouton
  « Voir le journal » (`BlocLivrable.tsx:23`) **n'est pas gaté admin** — transparence assumée des moteurs
  déterministes.
- **Quota** : lu du **budget euro par compte**, appliqué **AVANT tout appel modèle**. `POST /ask`
  (`copilote_v2.py:75-84`) → `etat_plafond_ia(compte, sujet, jour)` → 429 si dépassement. Garde **unifiée**
  avec `/ia` (compteur `usage_compteurs` kind `copilote`). Compte connecté → budget € via
  `depassement_budget_eur` (SUM `ia_log.cout_eur` du jour vs `comptes.copilote_budget_eur`) ; bucket pilote →
  comptage d'appels `nl_quota_jour` (défaut 80). **Facturation et blocage partagent un seul registre**
  (`ia_log`).
- **Modèles** : **tous** via `ai_models.py` (`model_for(kind)`), aucun littéral en dur dans
  `answering.py/outils.py/router.py`. Router = **haiku** (`copilote-route`), sélection+formulation+général+
  prepare+web+héros+mission = **sonnet** (`copilote-select/-formule/-general/-prepare/-web/-heros`,
  `copilote_mission`). Coût logué par `core._log_cost` → `ia_log` (`cout_eur = (tin·pin+tout·pout)/1e6`).
- **Coût moyen d'une question** : **non mesuré** (crédits épuisés → 0 appel réel). À relever sur les 10 du
  point 3 au rejeu (requête : `SELECT kind, count(*), sum(cout_eur) FROM ia_log WHERE ... GROUP BY kind`).

---

## 8. La mémoire par compte

- **Ce qui est retenu** : `copilote_conversations` (compte_id, titre, statut, run_id), `copilote_messages`
  (role, texte, intent, `payload` = contexte d'interprétation, jamais servi), `copilote_faits` (l'oracle
  numérique). TTL de contexte borné (`copilote_v2_contexte_ttl_minutes`, défaut 10) ; purge après rétention
  (défaut 90 j).
- **Cloisonnement compte** : **oui**, sur toutes les lectures. `historique.fil` (`:84-91`),
  `historique.charger` (`:114-124`), `historique.lister` (`:104-110`), `registre_faits.du_fil` (`:88-93`)
  filtrent `compte_id IS NOT DISTINCT FROM :c`. Un `conversation_id` étranger → `None` → **404**
  (`copilote_v2.py:200-203`). **Aucune fuite inter-compte** pour les comptes connectés.
- **Nuance (pas une faille)** : le bucket **anonyme/pilote** (`compte_id = NULL`) est **un espace partagé**
  (`NULL IS NOT DISTINCT FROM NULL`) — deux sessions anonymes peuvent se lire par id. Conforme au design
  « bucket pilote » ; à surveiller si des données sensibles y transitent. Comptes réels : isolation saine.

---

## Les quatre listes

### A. Faits en dur périmés
1. `answering.py:1447` — commentaire « **les 11 outils invisibles** » : la table `_CONCEPT_MAP` n'en tient
   plus 11 (dormants retirés). **Interne, non-client.**
2. `router.py:8-9` — « **45 cas, > 97,1 % sonnet** » : benchmark Phase-0 sur modèles anciens, jamais rejoué.
   **Interne, non-client.**
3. `router.py:26-28` & `answering.py:1318-1320` — commentaires **M118** affirmant RECHERCHE/VERIFICATION =
   refus-voie : **contredits par le code** (rapatriés au chat, SUITE-1 S9). **Interne.**
4. *(latent-faux)* `outils.py:25` `CADASTRE_MILLESIME="Etalab 2026-06"` et `outils.py:547`
   `"BD ORTHO … 2025"` : **corrects aujourd'hui**, mais en dur (pas lus de `data_sources.source_millesime`) →
   divergeront silencieusement au prochain ingest. **Vus au client.**

### B. Chiffres divergents Copilote / fiche
*(Live bloqué — analyse structurelle.)* Aucune divergence de **moteur** possible sur les champs qu'un outil
expose : `fiche_parcelle` lit le **même `_q_v2_fiche`** que la fiche (commune, surface, zone, score = iso).
**Trou d'outillage** (le Copilote ne peut PAS refléter la fiche, faute d'outil) sur : **propriétaire, taxe
d'aménagement, risques naturels, pente** — tous présents dans la fiche, aucun exposé par un outil. Caveat
`fiche_parcelle.zone = reg[0]` (1re zone) vs dominante `parcel_zone_plu` sur parcelle multi-zones.

### C. Lectures hors registre
**Toutes (N registre = 0).** SQL direct : `parcelle_personne_morale`, `entite_acronyme`,
`parcels⋈parcel_zone_plu` (destination_zone), criblage `copilote/moteurs.py`, infra `agent_runs/events`.
Moteurs/facettes : `filtre`, `patrimoine`, `commune_contexte`, `velocite`, `build_marche_commune`,
`prospection_piscines`, `permis`, `plu.destinations.verdict`. Payload : `_q_v2_fiche`.

### D. Vestiges v1
1. `copilote/plans.py:38-45` — `PLAN_SHORTLIST`, `PLAN_VERIFIER` + missions `shortlist`/`verifier_adresse` :
   morts depuis l'UI (front ne lance que `instruire`, `CopiloteView.tsx:92`) ; atteignables seulement via
   API forgé/tests. Entraîne `assemblage_court`, `scoreur_unitaire`, `assemblage_verdict`, `interpreter_refs`
   (`moteurs.py`, `interpreteur.py`) — même statut.
2. `copilote_v2/missions_lourdes.py:44-47` — pierre tombale `preparer_veille`/`_executer_veille` (retirés
   M118, producteur `_action` veille inatteignable).
3. **Liens-morts de routage** (`answering.py:1414-1492`) : `porte` que le Copilote peut émettre —
   `plu-annuaire`, `lettre-zonage`, `verif-procedure`, `duediligence`, `o5-servitudes`, `simulplu` — **ne sont
   plus des clés de `registry.ts`** (fondues dans les hubs `plu`/`risques`, M137-P/T). Résolution dépend du
   mapping `porte→hub` du front ; sinon lien-mort (le piège « Foncier fantôme » à demi corrigé). *Intégrité de
   routage, pas un faux affiché.*

---

## Ce qu'on ne fait pas / preuve
- **Aucune correction** appliquée. Le rapport sert à décider du rebranchement.
- **Preuve** : `captures/copilote-audit1/` — `fiche_parcelle_raw.json` (vérité-terrain fiche),
  `point3_fiche10.json` (10 dégradations honnêtes = preuve du blocage crédits), `q10.json` + `q16.json`
  (jeux prêts à rejouer), `ask.py` (harnais). Captures écran des réponses live : **à produire au rejeu**.
- `tsc -b` = **vert** (exit 0 ; aucun TypeScript modifié). Lecture seule confirmée.
