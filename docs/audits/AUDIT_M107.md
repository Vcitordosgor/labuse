# AUDIT M107 — le Copilote converse vraiment

Mesuré et livré le 17/08/2026. Branche `feat/m107-copilote-conversation`.

## 1. Phase 1 — les chemins qui posent une question (l'état AVANT)

| # | chemin | question posée | moyen de répondre AVANT M107 |
|---|---|---|---|
| 1 | **clarification depuis l'accueil** (carte PRÉCISION, `clarification_recap` — le cas de Vic) | « Quel programme… ? » | options cliquables seulement ; la promesse « …ou écrivez librement votre réponse dans la barre » était **FAUSSE en pratique** : la barre gardait la demande précédente, sans focus, au-dessus de la carte |
| 2 | **récap-péage** (« C'est bien ça ? ») avant mission lourde | oui | Oui ✓ · Corriger ✓ (renvoi barre) — mais PAS d'écriture directe d'une correction |
| 3 | **affinage** (« Envie d'affiner ? ») | oui | boutons + champ libre inline ✓ (déjà conforme) |
| 4 | **erreur récupérable** (« Réessayez dans un instant ») | invitation | AUCUN moyen sur place (ni bouton, ni champ) |
| 5 | **Copilote embarqué** (fiche, shortlist) | clarification possible | AUCUN champ de réponse ; pas de Corriger ; fil non chaîné (chaque question repartait à froid) |
| 6 | **fil de l'accueil** (dernier tour = clarification) | oui | champ M102-B2 ✓ — c'est LE SEUL endroit où B2 avait branché le champ : la branche FIL (intents légers). Le chemin 1 passe par `setRecap()` qui rend RecapConfirmation À LA PLACE du fil — le champ n'y existait pas |

Côté serveur, la barre « marchait » techniquement (conversation_id → prior_params,
gate 45) — mais **la ré-interprétation du récap RECHERCHE était nue** :
`recap_recherche(db, message)` re-parsait « 15 logements » seul et **re-demandait
la commune donnée au tour d'avant** (mesuré en rejeu). Deux défauts distincts :
la promesse d'interface fausse ET le contexte perdu au récap.

## 2. Livré (Phases 2-3)

- **Chemin 1** : champ de réponse DANS la carte Précision, sous la question,
  autofocus + bouton Répondre ; la promesse fausse est REMPLACÉE par le champ
  qui la tient.
- **Chemin 2** : récap « C'est bien ça ? » = Oui · Corriger · ET un champ
  « …ou corrigez directement en écrivant ici » (le geste de Vic).
- **Chemin 4** : l'échec porte un bouton **Réessayer** sur place.
- **Chemin 5** : le Copilote embarqué chaîne sa conversation (conversation_id),
  montre le champ de réponse sur clarification (autofocus), reçoit Corriger,
  et sa barre se vide après envoi.
- **Chemin 6** : le champ du fil devient PERMANENT (« Répondre, corriger ou
  préciser… »), autofocus quand une question vient d'être posée.
- **La barre principale se vide après envoi** (accueil, lancement de mission,
  embarqué) — elle ne garde plus la question précédente comme si elle attendait.
- **Serveur — le brief effectif** : pour RECHERCHE, le récap est interprété sur
  les tours CLIENT du fil (bornés à 4) + le message courant, et ce
  `brief_effectif` est SERVI — le front relance récap et run avec lui, jamais
  avec la réponse nue. Rejeu mesuré : T1 « …100000m2 à saint paul » →
  clarification programme ; T2 « 15 logements » → « J'ai compris : Saint-Paul,
  15 logements, ≥ 100000 m², hors PPR rouge. » (même conversation).
- **TTL (Phase 3)** : 120 → **10 minutes d'inactivité** (config
  `copilote_v2_contexte_ttl_minutes`, la valeur VOYAGE dans /ask — jamais
  recopiée au front). L'expiration est ANNONCÉE (bandeau « Nouvelle
  conversation — le fil précédent a expiré ») ; le fil reste visible estompé
  et repart de zéro AU MESSAGE SUIVANT — jamais vidé en silence. « Repartir de
  zéro » reste disponible. **Réserve dite (P3.4)** : 10 min est court pour qui
  réfléchit (pas de mesure d'usage réel disponible en local) — le paramètre est
  en config, ajustable en un endroit.

## 3. Vérification (Phase 4)

- **Cas exact de Vic rejoué À L'ÉCRAN** : demande → carte PRÉCISION avec champ
  (autofocus, barre vidée « ») → « 15 logements » dans la carte → récap complet
  avec Oui (1) · Corriger (1) · correction directe (1).
- Fil de 3 tours avec champ permanent ✓ ; expiration annoncée à l'écran (TTL
  servi — capture faite à TTL 1 min via env, config normale restaurée) ; reset ✓.
- Chemin 5 embarqué : vérifié par typage/build (une clarification déclenchable
  à la demande depuis la fiche n'a pas de cas reproductible court — le champ est
  câblé sur `rep.clarification`, même mécanique que le fil).
- **Anti-invention INTACTE, aucun assouplissement** : véracité 32/32 · véracité
  fil 3/3 · routeur 45 msgs précision claire 100 % (gate_95 vrai).
- Golden 0 FAIL · 1560 passed · tsc 0 · build OK.
- Captures : carte Précision + champ · récap Oui/Corriger · fil 3 tours ·
  annonce d'expiration.
