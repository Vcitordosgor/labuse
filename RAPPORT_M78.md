# RAPPORT M78 — Copilote v2 : le client écrit, LABUSE instruit

Branche `feat/m78-copilote` (précondition OK : M-ENTREE mergé `5551103c`, main propre).
Maquettes de référence : `docs/DA-COPILOTE-ACCUEIL.html`, `docs/DA-COPILOTE-RESULTATS.html`.
Méthode : recopier les classes des maquettes et y verser les données — jamais de mémoire.

---

## DOCTRINE (gravée)

**Le modèle ne répond jamais une donnée de mémoire.** Toute affirmation factuelle provient d'un appel
d'outil exécuté contre la base. Le modèle traduit la question en appel d'outil, formule la réponse
depuis le résultat, cite l'outil. Le modèle n'écrit JAMAIS de SQL : il choisit un outil et des
paramètres typés, le serveur exécute une requête paramétrée. **Interdit** : un outil générique
`requete_libre(sql)` — c'est la porte de sortie de toute la doctrine.

**Les cinq issues d'une demande — une seule grammaire :**
1. **Couvert** → réponse chiffrée, source + millésime, états Sourcé/Estimé quand on restitue des
   données parcelle.
2. **Partiellement couvert** → ce qu'on a + ce qui manque, DIT (ex. délai Sitadel : médiane sur
   permis ACCORDÉS seulement = minimum optimiste, réserve rédigée mot pour mot du dossier banquier).
3. **Donnée structurellement inexistante** → refus SPÉCIFIQUE : pourquoi elle n'existe pas + où
   l'obtenir (propriétaire PP → demande SPF, porte Courrier ; « valeur dans 10 ans » → pas de
   projection, marché constaté proposé).
4. **Aucun outil ne correspond** → refus honnête, jamais une réponse plausible, pas de « bientôt ».
   Télémétrie (§1e). Cas connu : « cette parcelle est-elle divisible ? » (pas de score par parcelle,
   BACKLOG M-ENTREE) → répondre sur le fond (surface, zonage, règlement), AUCUN outil proposé.
5. **Hors sujet** → réponse fixe, zéro appel d'outil, zéro frais : « Je suis le copilote foncier de
   LABUSE — je réponds sur l'immobilier et le foncier de La Réunion. »

**Quand le Copilote dit « c'est fait », la chose EST faite** et visible dans la section de l'app.
Aucune confirmation sans écriture réelle préalable, par les API existantes uniquement.

**Coûts** : Sonnet par défaut partout (Opus interdit sans justification rapportée). Chaque appel
modèle journalisé (prompt, outils appelés, réponse, tokens) — c'est l'auditabilité vendue.

---

## PHASE 2 — Accueil + mission RECHERCHE _(en cours)_

- **Endpoint** `/api/copilote-v2` (POST /ask, GET /telemetrie) monté (`6f2c56cf`), testé TestClient.
- **Audit entonnoir (2d)** : Arrêter propre EXISTE (POST /cancel → run_cancelled persisté, exécuteur
  vérifie le statut à chaque étape = pas de zombie) ; async SSE + daemon + reprise. **Seul manque : modif
  de chip pendant l'instruction** (brief/plan figés) → à ajouter comme `annuler()` + relance (le cancel
  propre existe déjà). Je rebranche, je ne refais pas.
- **Audit facettes (2c)** : 42 facettes `FiltreCriteres`. **3 demandes-types NON couvertes** (arbitrage Vic
  → BACKLOG, « le DIRE » en attendant) : (1) **risque en recherche = ANOMALIE PRODUIT** (la donnée existe —
  cascade risques, PPR M-I 14 000 parcelles — pas filtrable) ; (2) facette spatiale (« proche de la mer ») ;
  (3) « déjà en vente » = donnée absente (pas de source d'annonces — à dire ainsi, jamais « bientôt »).
  Les chips ne promettront jamais ces trois ; le Copilote les DIT + télémétrie.

## PHASE 1 — Routeur et boîte à outils
_(en cours — 1a LIVRÉ ci-dessous ; restent : 1b outils+SQL · 1c table demande→outil · 1d test
véracité 32 questions · 1e télémétrie · 1f plafonds/coûts)_

### 1a — Routeur d'intention (LIVRÉ, gate bloquant franchi)

**Module** : `src/labuse/copilote_v2/router.py`. Un appel **Sonnet** (`core.MODEL_REASONING`, doctrine
« Sonnet partout ») classe le message en 7 intentions + extrait des paramètres typés. Sortie **JSON
strict validée par schéma** (`ROUTE_SCHEMA`, jsonschema) — motif éprouvé de `/ia/search` : parse
robuste (élague les ```json), clés hors liste blanche ÉLAGUÉES (jamais avalées ni inventées),
**une re-demande** si JSON invalide puis erreur honnête. Le routeur ne répond JAMAIS une donnée.
- **Contexte de session** : `HISTORIQUE_TOURS = 6` derniers tours passés au modèle (dimensionné :
  6 couvre les enchaînements « et à Saint-Benoît ? » sans gonfler le coût — mesuré ~1500 tok in/appel).
- **Correction / héritage** : `prior_params` fusionnés côté serveur — un paramètre déjà connu (IDU du
  tour 1) survit au re-routage du tour 2 s'il n'est pas contredit. Filet déterministe en plus du modèle.

**Test** (`qa/m78/routeur_eval.py`, 45 messages étiquetés, modèle RÉEL) — matrice de confusion :

```
attendu\obtenu  QUEST  OUTIL  RECHE  VERIF  VEILL  PROJE  HORS_
QUESTION          8
OUTIL                   6
RECHERCHE                      6
VERIFICATION                          4
VEILLE                                       4
PROJET                                              3
HORS_SUJET                                                 4
```
- **Précision intentions claires : 100 % (35/35)** — gate ≥ 95 % franchi. Diagonale parfaite.
- **Ambigus 5/5** : une clarification posée (jamais un menu) sur « Saint-Paul. », « Cette parcelle. »,
  « Je veux investir. », « Combien ça coûte ? », « Le terrain là-bas ».
- **Corrections de tour 2 : 5/5** — bon re-routage ET paramètre conservé (IDU/surface/programme/commune).
- Répartition : 7 intentions (33 clairs dont 6 OUTIL, **2 sans outil = division**, décision M-ENTREE)
  + 5 ambigus + 5 corrections = 45.
- **Deux ajustements de prompt** consignés (pas de sur-ajustement — règles de principe) : (i) « des
  parcelles [caractéristique] à [commune] » = ENSEMBLE à lister → RECHERCHE (pas QUESTION) ; (ii)
  « ajoute une parcelle à ce projet » = gestion de PROJET (flux Phase 3b réel), pas OUTIL générique.
- **Coût mesuré** : ~0,006 €/appel de routage (Sonnet, ~1500 tok in / ~90 tok out) ; journalisé dans
  `ia_log` (kind `copilote-route`). Une passe complète des 45 messages ≈ 0,27 €.

### 1b — Boîte à outils QUESTION : point de calcul EXISTANT par outil (doctrine « un seul endroit »)

Chaque outil **appelle** la fonction/endpoint qui produit déjà la donnée pour la fiche/les moteurs.
Il n'en RECRÉE aucun : pas de SQL de scoring/marché réécrit, `requete_libre(sql)` interdit. La preuve
de non-recréation = l'outil importe et invoque ce point, et le test 1b confronte sa sortie à ce même
point (égalité fiche↔Copilote) ; les comptages/stats sont en plus confrontés à l'oracle hand-SQL (1d).

| Outil QUESTION | Point de calcul EXISTANT réutilisé | Fichier:ligne | Preuve de non-recréation |
|---|---|---|---|
| `marche(commune)` | `build_marche_commune(db, commune)` (9 lignes DVF/Sitadel/DHUP, terrain nu M79) | `faisabilite/marche_commune.py:318` | import direct ; test d'ÉGALITÉ Copilote==build_marche_commune (mêmes chiffres que la fiche) |
| `fiche_parcelle(idu)` | `_q_v2_fiche(db, idu, run_label)` (verdict via `verdict_servi`, ICD, risques arbitrés, zonage) | `api/app.py:2191` | import lazy ; verdict/risques lus, jamais recalculés — test d'égalité au verdict servi |
| `delais_instruction(commune)` | `velocite(nature, db)` + réserve rédigée | `api/modules.py:457` (réserve `:523-528`) | la réserve Sitadel est CITÉE mot pour mot (champ `censure`), pas reformulée |
| `parcelles_par_entreprise(q)` | `patrimoine_search(q)` / `patrimoine(siren)` (DGFiP PM) | `api/modules.py:190-235` | import direct ; comptage confronté à l'oracle 1d (SIDR=4241) |
| `stats_commune(commune)` | `commune_contexte(commune, db)` (SRU, QPV, INSEE logement, PLH) | `api/app.py:1361` | import lazy ; chaque bloc garde son `source_nom`+`millesime` d'origine |
| `compter_parcelles(...)` | `_q_v2_where(...)` (fragment WHERE des 20 facettes M55) + COUNT sur le run servi | `api/app.py:827` | réutilise le fragment WHERE canonique (mêmes facettes que la recherche), jamais un WHERE maison |

Note doctrine : le **verdict client** (fiche) et le **marché/M79** ne sont PAS dans le hand-SQL de 1d
(ce sont des sorties de FONCTIONS, pas des colonnes brutes ; les re-dériver forkerait le point unique).
Ils sont prouvés par **égalité au point de calcul canonique** — ce qui EST la garantie « le Copilote dit
la même chose que la fiche ».

### 1c — Aiguillage OUTIL : table demande-type → outil (registre RÉEL de la page Outils)

Construite depuis `frontend/src/components/outils/registry.ts`. « Un outil existe » → réponse sur le
fond PUIS porte `.porte-outil` ; si l'outil accepte un IDU et qu'une parcelle est citée, la porte
pré-remplit via **`parcelPrefill`** (motif M-ENTREE) ou le prefill dédié existant.

| Demande-type du client | Outil (clé registre) | Pré-remplissage IDU |
|---|---|---|
| assembler des parcelles | Assemblage (`assemblage`) | `parcelPrefill` (M-ENTREE) |
| faisabilité / capacité d'un terrain | Faisabilité (`programme`) | `parcelPrefill` (M-ENTREE) |
| charge foncière / ce que je peux payer | Calculette foncière (`calculette-fonciere`) | `calcPrefill` (M60) |
| écrire au propriétaire | Courrier SPF (`courriers`) | via IDU (M60) |
| patrimoine d'une société | Scan patrimoine (`patrimoine`) | `m02Prefill` (SIREN) |
| comparer des parcelles | Comparateur (`comparer`) | sélection |
| règlement d'une zone | Annuaire PLU (`plu-annuaire`) | `pluPrefill` (insee+zone) |
| lettre de vérification de zonage | Lettre de zonage (`lettre-zonage`) | via IDU |
| procédure PLU en cours | Vérif procédure (`verif-procedure`) | via IDU |
| due diligence / contrôle avant achat | Contrôle avant achat (`duediligence`) | via IDU |
| servitudes invisibles | Servitudes (`o5-servitudes`) | via IDU |
| évolution dans le temps | Remonter le temps (`temps`) | via IDU |
| **diviser une parcelle** | **AUCUN** (découverte commune, décision M-ENTREE) | — → issue 4 (refus honnête, télémétrie) |

### 1b/1c code + 1d test de véracité (LIVRÉ, gate bloquant VERT)

- **6 outils** (`copilote_v2/outils.py`) : chacun appelle son point de calcul par IMPORT PARESSEUX
  (motif `ia.py`, zéro cycle). Correction/preuve trouvées en construisant : `patrimoine` compte les
  parcelles RÉELLES (jointure `parcels`) = 4183 pour la SIDR (l'oracle naïf comptait 4241 enregistrements
  PM, dont 58 idus absents de `parcels` → l'outil a raison) ; la zone d'une parcelle est une sortie de
  fonction (facette GPU ≠ `zone_fam`) → sortie du hand-SQL, comme le verdict. Résolution nom→SIREN
  accent-insensible par tokens (le client tape « Société », la base stocke « SOCIETE »).
- **Couche de réponse** (`answering.py`) : routeur → sélection d'outil (le modèle choisit un NOM + args
  typés, jamais du SQL) → exécution serveur → formulation. **Verrou anti-invention** : tout nombre de la
  prose doit exister dans le résultat d'outil (+ source/millésime cités), sinon prose rejetée → gabarit
  sourcé. **Refus = TEMPLATES déterministes** (le ton d'un refus ne s'improvise pas).
- **1d — VÉRACITÉ 32/32 VERT** (`qa/m78/veracite.py`, modèle réel). 18 exactes (chiffre == oracle
  hand-SQL), 6 partielles (réserve DITE), 6 refus (2 PP→SPF, 2 projections, 2 hors-sujet), 2 outil
  (porte calculette / division sans porte). 5 ratés corrigés en cours (routeur « Combien »→QUESTION,
  mapping « opportunités », `delais_instruction` porte aussi le nb de permis, 2 attentes de test fausses).

### 1e télémétrie · 1f plafonds/coûts

- **1e** (`telemetrie.py`) : table `copilote_telemetrie` (DDL inline). Journalise refus « pas d'outil »
  (anonymisé), critères non traduisibles, 👍/👎 (avec mission_id, §2f). `resume()` trie par fréquence
  = la feuille de route MESURÉE. La télémétrie ne casse jamais une réponse (try/except + rollback).
- **1f** : plafonds EN CONFIG (`config.py`) — `copilote_v2_missions_jour=40`, `copilote_v2_tokens_mission
  =40 000`, `copilote_v2_instructions_lourdes_max=1` (le reste en file). Sonnet partout (Opus interdit).
  Chaque appel journalisé `ia_log` (kind `copilote-route|select|formule`). Coût mesuré : routage
  ~0,006 € ; une QUESTION complète (routage+sélection+formulation) ~0,015-0,02 €.

### Démo 10 messages (STOP Phase 1) — 5 réponses · 5 refus

`qa/m78/demo.py`. Réponses : comptage (5 301 parcelles ≥ 5000 m² Saint-Paul, sourcé) · patrimoine SIDR
(4 183 parcelles + SDP) · délais Saint-Benoît (9 mois + réserve Sitadel intégrale) · SRU Saint-Benoît
(34,49 % conforme) · porte Calculette pré-remplie. Refus : propriétaire PP → SPF (courrier proposé) ·
projection → marché constaté proposé · divisibilité → fond (194 m² zone A Saint-Louis) + AUCUN outil ·
2× hors-sujet (réponse fixe). Ton sobre, honnête, l'alternative offerte quand elle existe.
