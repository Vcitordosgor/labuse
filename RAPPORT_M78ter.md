# RAPPORT M78-ter — L'outil recherche_web : répondre au-delà de la base, sans mentir

Branche `feat/m78-copilote`. Le Copilote refusait « qui est le maire de Saint-Denis ? » comme une
projection de prix. On donne une source à ces questions légitimes : le web, cité et daté.

## La règle (inchangée) + la hiérarchie
Le modèle ne répond JAMAIS de mémoire. La recherche web est un OUTIL de plus (recherche web NATIVE de
l'API Anthropic — pas de scraping maison). Hiérarchie STRICTE, appliquée à l'aiguillage :
1. **Base LABUSE d'abord** — un outil interne prime TOUJOURS (« nouveau PLU ? » = Vérif procédure, jamais
   le web). Testé : le web n'est PAS appelé.
2. **Web ensuite** — public hors base (élus, organigrammes, actualité réglementaire, appels à projets,
   coordonnées de services), dans la barrière : foncier/immobilier/urbanisme/collectivités de La Réunion.
3. **Refus enfin** — inchangé (propriétaire PP, projections) et hors-sujet.

## L'outil
- `recherche_web(question)` (`outils.py`) : appel Anthropic `web_search_20250305`, extrait la réponse +
  les domaines cités ; journalise le coût (`ia_log` kind `copilote-web`). Rien trouvé → refus honnête.
- Le routeur élargit la barrière : collectivités et acteurs réunionnais (maire, élu, EPCI, Région,
  Département) ne sont PLUS hors-sujet → QUESTION. L'aiguillage (`_select_tool`) choisit `recherche_web`
  en DERNIER recours (aucun outil interne, pas une action-outil, dans la barrière).

## Le marquage (non négociable)
- Toute réponse web porte « **Source : web · [domaine] · consulté le [date]** » — JAMAIS un état
  Sourcé/Estimé (réservés aux données LABUSE). La réponse web n'est pas passée par `_formuler` (qui,
  lui, cite source+millésime LABUSE) : marquage construit à part.
- Sources divergentes/faibles → le prompt web le DIT (« Les sources divergent — à vérifier »).
- Rien trouvé → refus honnête + télémétrie.

## Télémétrie
`telemetrie.web` journalise les questions servies par le web À PART (genre `web_servi`, avec les
domaines). Un motif qui revient (organigrammes, contacts de services) = signal qu'un annuaire local
structuré mérite son mandat — la donnée décidera.

## Accueil (M78-bis §1)
+3 exemples au pool : « Qui est le maire de Saint-Denis ? », « Qui gère les dossiers de financement des
bailleurs sociaux à la Région ? », « Y a-t-il un appel à projets logement en cours à La Réunion ? »

## Tests (`qa/m78/veracite_web.py`) — 3/3 + coût journalisé
1. maire → **web=True**, « Source : web · annuaire-mairie.fr · consulté le … », aucun Sourcé/Estimé. ✅
2. nouveau PLU Saint-Leu → **OUTIL interne** (Vérif procédure), web NON appelé. ✅
3. recette rougail → **barrière** (HORS_SUJET), web NON appelé. ✅
4. coût journalisé (`ia_log` `copilote-web`). ✅

## Gardes
tsc 0 · vitest · build vert · pytest copilote 26 · golden diff 0 (scoring inchangé). NE PAS MERGER.
