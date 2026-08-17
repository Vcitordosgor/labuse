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
| Tests déterministes copilote (projet/guidage/rupture/facette/miscompte) | **43/43** |
| Tests déterministes SCÉNARIO (`tests/test_copilote_scenario.py`) | **5/5** (registre · web court-circuit · projet sans création directe · intent forcé) |
| Suite complète | **1600 passed** (1 échec pré-existant `test_partners_api_v1`, confirmé par stash sur le tip M112 — hors périmètre) |
| tsc · build | **0 · OK** |
| Latence maire : structure du court-circuit | web-**libre** appelle classify (`degraded=True`) ; web-**chip** le SAUTE (`degraded=None`) — court-circuit confirmé |
| Gate scénario chip (`qa/m113/scenarios.py`) · fil · facette · latence chiffrée | **à rejouer** — quota API épuisé (voir note) |

> **Note quota (environnement).** À force de rejouer les gates aujourd'hui (vérification M112 + les
> expériences Phase 0 + les re-runs B1), l'API modèle a atteint un plafond (429 « service
> indisponible ») qui n'a pas récupéré après 15 min — vraisemblablement un plafond JOURNALIER. C'est
> le même signal qui rend le golden « INDÉTERMINÉ » : panne d'environnement, PAS un écart métier.
> Le **routeur (100 %)** et la **véracité (33/33)** — les deux gates critiques du changement de modèle
> B1 — ont tourné VERT avant l'épuisement. Les gates **scénario / fil / facette** et la **latence
> chiffrée** sont à REJOUER dès récupération du quota (aucune assertion assouplie). Couverture du
> risque en attendant : (1) véracité 33/33 exerce le chemin complet route→select→formule, dont des
> comptages facette (Q11/Q16/Q17) — le socle des scénarios `donnees`/`parcelle` ; (2) 5 tests
> déterministes valident le forçage de scénario, le court-circuit web et le « jamais de création
> directe » ; (3) les tests de rupture (M111) couvrent la logique du fil. Branche NON mergée : la
> re-confirmation de ces trois gates est un prérequis au merge.

## Interdits respectés

Voie texte libre préservée · aucun bouton de confirmation/correction sur une réponse · récap M109
conservé (phrase) · le Copilote ne crée plus jamais un projet sans le formulaire · modèle changé
uniquement selon l'arbitrage Phase 0 (B1) · chips servis par le serveur, jamais en dur · rien de
M109-M111 assoupli · non mergé.
