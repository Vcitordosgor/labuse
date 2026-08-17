# AUDIT M102 — Phase 0 : le multi-tours du Copilote (mesure, STOP)

Mesuré le 2026-08-17 (code + appels réels à `/api/copilote-v2/ask`). **Aucun code de
conversation écrit — Vic arbitre l'ampleur au vu du coût.** Les corrections immédiates
(Phase 1) et l'accueil (Phase 3) sont livrées indépendamment.

## 1. Ce qui existe déjà (et où c'est branché)

Le récap-confirmation M78 (`RecapConfirmation.tsx`, `copilote_v2/recap.py`) est un
**péage réservé aux missions lourdes** : il ne se déclenche que pour les intentions
`RECHERCHE` et `VERIFICATION` (answering.py:229-231, 273, 292 — règle M78-bis §5 : « la
confirmation est un péage, justifiée quand une mauvaise interprétation coûte cher »).
C'est POURQUOI il ne se déclenche ni sur « créer un projet » (intention `PROJET` → chemin
« clarification » : une question texte, sans champ de réponse dédié) ni sur « vérif
procédure PLU » (intention `OUTIL` → réponse immédiate avec porte). Mesuré en direct :
les deux cas de Vic rendent respectivement `clarification: true` et
`porte: "verif-procedure"` — jamais un récap.

## 2. L'état de session : une mémoire ÉCRITE, jamais RELUE

La persistance **existe** (`copilote_v2/historique.py` : tables `copilote_conversations`
/ `copilote_messages` par compte, rétention 90 j en config, endpoints `/missions` +
restauration). MAIS :
- le front n'envoie **jamais** `history` (CopiloteView.tsx:118 ne passe que
  `conversation_id` + `confirme` — le champ `history` du type API existe et reste vide) ;
- le serveur ne **recharge pas** l'historique depuis `conversation_id` avant
  d'interpréter (ask() → answer() reçoit `body.history` = None).

Résultat : chaque `/ask` est interprété **sans mémoire**. La conversation est stockée
pour la reprise d'écran, pas pour l'interprétation. Le squelette du multi-tours est là
(classify() accepte déjà `history` [{role, content}] ET `prior_params` —
router.py:187-193) ; il n'est simplement pas alimenté.

## 3. Le routeur à froid : mesuré

« 15 logements à Saint-Paul » envoyé seul (comme le ferait un client répondant à « quel
est votre objectif ? ») part en `RECHERCHE` avec un brief complet — le routeur ne peut
pas savoir qu'il répondait à une question `PROJET`. Mesure annexe : un `history` au
mauvais format ({role, texte} au lieu de {role, content}) fait tomber le routeur en mode
dégradé (« service d'analyse indisponible ») — le garde existe mais le format n'est pas
plié.

## 4. L'anti-invention sur plusieurs tours : c'est LE point dur

Le verrou actuel (answering.py:146 + verifs.py) compare les nombres de la réponse au
résultat de l'outil **du tour courant** (oracle par tour — c'est ce que la gate véracité
32/32 prouve). Un chiffre donné au tour 2 et repris au tour 5 n'a **pas d'oracle au tour
5** : soit le formuler ne peut pas le reprendre (comportement actuel — le verrou le
bloquerait), soit il faut un **registre de faits du fil** (chiffre → outil → source →
millésime, porté par la conversation et vérifié à chaque tour). Sans ce registre, le
multi-tours qui « se souvient des chiffres » casse la traçabilité — on ne le livre pas
sans lui (doctrine : on ne sacrifie pas la garantie pour du confort).

## 5. Le coût honnête d'un multi-tours complet

| chantier | contenu | taille |
|---|---|---|
| Interprétation contextuelle (serveur) | recharger les N derniers messages depuis `conversation_id`, plier au format router, passer `history` + `prior_params` (plomberie existante des deux côtés) | ~1 jour |
| Champ de réponse dans le fil (front) | quand `clarification: true`, un champ de réponse attaché à la question, envoyé avec le fil | ~1 jour |
| Récap partout (extension de la règle M78) | à chaque interprétation, une phrase « j'ai compris X » + bouton Corriger (le composant existe, l'étendre hors missions lourdes) | ~1 jour |
| **Registre de faits du fil (anti-invention)** | table/structure {conversation_id, fait, valeur, outil, source, millésime}, alimentée par chaque ToolResult, vérifiée par le verrou à chaque tour ; SANS lui, pas de reprise de chiffres | **le gros morceau : conception + implémentation + GATE de véracité multi-tours à écrire (l'actuelle ne couvre que le tour isolé)** |
| Fin de fil | bouton « repartir de zéro » (front) + TTL (rétention 90 j existante, à borner par fil actif) | ~½ jour |

Estimation d'ensemble : **l'équivalent de 2 à 3 mandats** — un mandat serveur
(fil + interprétation contextuelle + registre de faits), un mandat front (fil
conversationnel, champ de réponse, récap généralisé), et la **gate de véracité
multi-tours** (sans elle, aucune garantie mesurée — la 32/32 actuelle ne prouve que le
coup isolé).

**STOP — Vic arbitre l'ampleur.** Les Phases 1 et 3 sont livrées ci-dessous quoi qu'il
arrive.

---

## Annexe — la chaîne exacte du « 500 nu » et du jargon (constat 2, reproduit)

`/ask` laisse fuir les `HTTPException` des outils aval : mesuré,
`{"detail": "Parcelle X absente du run q_v9_m81"}` (HTTP 404 brut — app.py:2326) sur une
question de fiche avec un IDU hors run. Le front (CopiloteView.tsx:129-131) affiche ce
message d'erreur BRUT comme réponse du Copilote — c'est à la fois le « 500 nu » ET le
`q_v9_m81` servi à l'écran que Vic a vus. Corrigé en Phase 1 : garde générale dans
`/ask` (message honnête, trace serveur) + messages d'erreur aval sans identifiant de
run + le catch front ne montre plus jamais un message technique.
