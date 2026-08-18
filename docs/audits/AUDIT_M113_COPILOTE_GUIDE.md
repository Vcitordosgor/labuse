# M113 — le Copilote guidé : contexte d'abord, scénarios dédiés

Livré le 17/08/2026. Fait suite à l'arbitrage Phase 0 de Vic (réaffectation modèles **A + B1**).
L'utilisateur choisit d'abord CE qu'il veut faire (chips de contexte), puis écrit : l'IA connaît le
scénario avant de lire le message. Le texte libre reste possible (routeur M78 inchangé).

## Phase 0 — la latence, mesurée (voir `AUDIT_M113_LATENCE.md`)

Constat : les 4 étages du Copilote étaient sur **sonnet**. Le maire (web) ≈ 15–16 s = route(sonnet)
+ select(sonnet) + web-search, deux appels sonnet avant même la recherche. `LABUSE_ASSISTANT_MODEL`
n'affecte PAS le Copilote (scopé `explain_parcel`). Expériences : routeur sur **haiku** = 100 % au
gate (mieux que 97,1 % sonnet), ⅓ du coût. **Arbitrage Vic : A + B1** — les chips court-circuitent le
routage, ET `classify → haiku` (B1). Select/formule/web restent sonnet.

## B1 — le routeur sur haiku (arbitré)

`router.py` : `classify` passe sur `MODEL_FACTUAL`. Une régression prudente est apparue (haiku
demandait une précision sur « Combien de logements à Saint-Paul ? » au lieu de servir 51 317) —
corrigée par une RÈGLE DURE du prompt (« une question "Combien de … à [commune] ?" est CLAIRE,
clarification null, jamais demander de préciser la métrique »). Après correctif : routeur **100 %**,
véracité **33/33** (rien d'assoupli).

## Phase 1 — les finitions dues

1. **« Nouveau fil »** (dette M107-B) : vrai bouton secondaire (classes DA-ACCUEIL-BRIEF, bordure
   cp-line, cible px-4 py-2, survol), à portée du champ. Remplace le lien souligné faible.
2. **Carte PRÉCISION** : placeholder « Votre réponse… » (le « …ou » datait des deux voies d'avant
   M107), un seul cadre au thème mint (fini le mauve-dans-vert), bordure neutre au repos, accent mint
   au focus.

## Phase 2 — les chips de contexte

Registre serveur `SCENARIOS` (answering.py), servi par `GET /api/copilote-v2/scenarios` (jamais en
dur au front). 6 chips : Interroger mes données (QUESTION) · Trouver une parcelle (RECHERCHE) · Créer
un projet (parcours guidé) · Rechercher sur le web (QUESTION→web) · Mettre sous surveillance (VEILLE)
· Ouvrir un outil (OUTIL). Le chip choisi arrive dans `/ask` (`scenario`) et FORCE le scénario :
- **web** : classify court-circuité — la question verbatim au web (gain de latence majeur) ;
- **projet** : ouvre le parcours guidé (jamais de création directe) ;
- **autres** : classify RÉDUIT à l'extraction de paramètres (haiku), intent FORCÉ, clarification
  d'intention retirée (la clarification de PARAMÈTRE reste, produite en aval).

L'anti-invention, le récap M109 et les gardes sont IDENTIQUES à la voie texte libre — le
court-circuit du routage ne court-circuite jamais le verrou. Front : chips « Que souhaitez-vous
faire ? », le placeholder du champ s'adapte au scénario (servi par le serveur), un lien « écrire
librement » libère le mode. Aucun chip = routeur M112 inchangé.

## Phase 3 — le parcours projet guidé

`ParcoursProjet.tsx` : parcours en étapes (nom → commune → programme → critères → récap → créer). La
**commune vient du référentiel** (`/communes`), jamais du texte libre. **Le Copilote ne crée PLUS
jamais directement** : l'intent PROJET (chip OU texte libre) ouvre le formulaire, prérempli de ce qui
est compris (« 15 logements à Saint-Paul » → commune + logements). L'ancien `_executer_projet`
(création serveur « c'est fait ») est RETIRÉ de l'endpoint. Le projet créé porte « Voir le projet → »
(mécanique M107-B). Même composant accessible directement depuis la section Projets (« + Nouveau
projet »), sans Copilote.

## Phase 4 — les réponses par scénario

- **Web** : `WEB_SYSTEM` resserré — le fait seul, UNE à DEUX phrases, aucune introduction (le gabarit
  du maire était trop long). Source + date de consultation conservées.
- **Données** : le chiffre + la phrase récap M109 (critères appliqués ET non appliqués, en
  information) + la porte carte/outil. Inchangé, court.
- **Parcelle** : le récap-péage RECHERCHE conservé (c'est une action, le péage protège l'exécution).
- **Aucun bouton de confirmation ni de correction sur une RÉPONSE** : le « Corriger » de la réponse
  inline (ReponseInline) est retiré — une réponse qui ne convient pas se corrige en relançant. Le
  récap M109 RESTE, mais comme une phrase d'information, jamais un bouton.

## Phase 5 — vérification

| Contrôle | Résultat |
|---|---|
| Gate routeur (B1 haiku, `qa/m78/routeur_eval.py`) | **100 %** (gate_95 ✓), ambigu 5/5, corrections 5/5, coût ÷3 |
| Gate véracité (`qa/m78/veracite.py`) | **33/33** (après correctif prompt B1) |
| **Gate scénario chip** (`qa/m113/scenarios.py`, oracle SQL) | **6/6** — données(51 129)+récap · web court(134 car.)+source · parcelle=péage · surveillance=VEILLE+porte · outil=porte · projet=form prérempli |
| **Gate fil** (`qa/m102/veracite_fil.py`) sous B1 | **6/6** |
| **Gate facette** (`qa/m110/veracite_facette.py`) sous B1 | **11/11** |
| Tests déterministes copilote (projet/guidage/rupture/facette/miscompte) | **43/43** |
| Tests déterministes SCÉNARIO (`tests/test_copilote_scenario.py`) | **5/5** |
| Suite complète | **1600 passed** (1 échec pré-existant `test_partners_api_v1`, confirmé par stash sur le tip M112 — hors périmètre) |
| tsc · build | **0 · OK** |

### Latence du maire, PAR LEVIER (`qa/m113/chrono_leviers.py`, 2 passes)

| levier | temps mesuré | gain vs BASE |
|---|---|---|
| BASE (libre, routeur **sonnet** — ni A ni B1) | 11,8 / 11,2 s | — |
| **B1** seul (libre, routeur **haiku**) | 9,7 / 10,2 s | **≈ −1,9 s** (étage routage) |
| **A+B1** (chip **web**) | 8,6 / 8,4 s | **≈ −3,3 s** (route + select ôtés) |

Lecture : **A** (le chip web) court-circuite classify → route + select disparaissent (≈ −3,3 s
aujourd'hui ; le jour de la mesure Phase 0, select seul valait 5–9 s → le gain y aurait été bien
plus grand). **B1** accélère l'étage routage (≈ −1,9 s) sur la voie LIBRE et les chips non-web ;
pour le maire (web), B1 n'ajoute rien AU chip (classify déjà sauté) — le gain du maire est porté par
A. Le plancher restant (~8,5 s) est la **recherche web elle-même** (variable, jusqu'à 3 requêtes),
hors de portée des leviers. La base du jour (11,8 s) est plus basse que celle de Phase 0 (15–16 s) :
l'API était moins chargée — les GAINS RELATIFS tiennent, les absolus varient avec la charge amont.

> Gates rejouées après recharge des crédits API (le blocage de la veille était un **solde de crédits
> épuisé** — `invalid_request_error` « credit balance too low » — et non un quota qui se réinitialise).
> Aucune assertion assouplie. Branche NON mergée.

## Interdits respectés

Voie texte libre préservée · aucun bouton de confirmation/correction sur une réponse · récap M109
conservé (phrase) · le Copilote ne crée plus jamais un projet sans le formulaire · modèle changé
uniquement selon l'arbitrage Phase 0 (B1) · chips servis par le serveur, jamais en dur · rien de
M109-M111 assoupli · non mergé.
