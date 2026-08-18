# M112 — les invisibles rendus atteignables

Livré le 17/08/2026. Dernier des 4 correctifs arbitrés après l'audit M108 (§2, la matrice
demande × capacité). M109/M110/M111 réparaient ce qui **trompait** ; M112 traite le **manque** :
des outils qui existent mais qu'aucun chemin conversationnel ne rendait cliquables.

## Le constat (audit M108, §2)

28 outils au registre, 6 exemples d'accueil, 4 documents exportables — mais le Copilote n'ouvrait
qu'une poignée de portes. La matrice a listé **11 outils invisibles** (baromètre, comparateur de
communes, radar permis, promesses mortes, simulateur ZAN, rareté du foncier, renouvellement,
simulateur PLU, bascules du mois, carnet de secteur, scoreur d'adresse) : une demande claire
(« ouvre le baromètre ») tombait en HORS_SUJET ou en question sans porte. De même, aucune demande
ne menait à la **carte filtrée**, à la **Surveillance** (M104) ni à l'**édition d'un document**.

Doctrine posée par Vic pour ce mandat : *« du manque, pas du mensonge — tout ce qui trompait est
mort. Ici on rend atteignable ce qui existe. »* Interdits : réimplémenter un outil au lieu d'y
router ; une porte qui ouvre une **section générale** au lieu de l'objet paramétré ; un exemple
d'accueil qui ne marche pas ; merger.

## Phase 1 — les 11 outils invisibles → une porte nommée

`_CONCEPT_MAP` (answering.py) étendu de 11 entrées. Reconnaissance par **mots-clés foldés**
(accents/casse neutralisés), jamais une devinette. Chaque entrée est **anti-collision** : on évite
« permis » nu (capté par la véracité délai d'instruction), « renouvellement » nu, « marché » nu —
au profit de formulations qui désignent l'outil sans ambiguïté (« radar permis », « qui construit
quoi », « potentiel de renouvellement », « baromètre du foncier »). L'interception `_match_concept`
tourne pour **tout intent** et **avant** la clarification / le court-circuit HORS_SUJET (correction
d'ordre : sinon « où investir ? » et « les bascules du mois » retombaient en refus). Une porte =
`{porte: <module>}` → le front fait `setModule(module)`, l'outil s'ouvre. Jamais une réimplémentation.

## Phase 2 — trois guidages vers l'objet paramétré

1. **Carte filtrée.** Une demande visuelle (« montre les friches », « où sont les parcelles en
   procédure ») route vers le comptage facette (`compter_parcelles`, M110) ; sa réponse porte une
   `carte_filtre` = `{commune, filtres, libelle}`. `_criteres_vers_filtres` traduit les critères
   facette (surface_min, tier, événement, signaux, sans-adresse, copro, renouvellement, zonage…)
   vers les `Filters` camelCase du front. La **facette reste le point unique** : la carte affiche
   exactement ce que le Copilote a compté. Le front pose `setFilters` + `setCommune` + `setView`.
2. **Surveillance (M104).** La pose d'une veille (`preparer_veille`) sert désormais une
   `surveillance = {volet: 'secteurs'}` → bouton « Ouvrir la Surveillance → » vers le bon volet,
   là où la veille posée devient visible et réglable. Jamais « rendez-vous dans la section X » nu.
3. **Documents.** `_match_document` reconnaît les 4 exports (dossier, **dossier-banquier avant
   « dossier » nu**, argumentaire, pré-dossier). L'IDU est résolu (params ou contexte) ; sans IDU
   → clarification. La porte `document = {kind, idu, libelle}` → lien `<a>` vers le PDF (ou le .zip
   du pré-dossier). Le front connaît les patterns d'URL (`docUrl`).

## Phase 3 — les 6 exemples d'accueil aboutissent tous

SIDR (4183, M110) · Saint-Paul (51 129 + carte filtrée offerte) · veille permis (Surveillance) ·
maire (web) · **« qui gère le financement des bailleurs sociaux »** (web — PAS l'outil bailleur :
le concept-outil exige un mot foncier/parcelle, sinon c'est une question d'organisation) · écrire
au propriétaire (clarification IDU). Le piège #5 a motivé le resserrement du mot-clé bailleur
(« parcelles/foncier/patrimoine des bailleurs », plus jamais « bailleurs sociaux » nu).

## Front — rendu seul, aucune heuristique

`ReponseInline.tsx` rend trois boutons nouveaux à partir d'objets **produits par le serveur**
(`carte_filtre`, `surveillance`, `document`) : aucune décision de routage côté front, seulement
l'affichage d'une porte que le backend a décidée. `api.ts` type les trois champs. tsc 0, build OK.

## Vérification (Phase 4)

| Contrôle | Résultat |
|---|---|
| Portes (harnais `qa/m112/portes.py`, chemin `answer()` réel) | **22/22** — 11 outils + 2 cartes + surveillance + 2 documents + 6 accueil |
| Unités déterministes (`tests/test_copilote_guidage.py`) | **28/28** (concepts, piège bailleur, documents, traduction critères→filtres, carte) |
| Gate routeur (`qa/m78/routeur_eval.py`) | **97,1 %** clair (gate_95 ✓), ambigu 5/5, corrections 5/5 |
| Gate véracité (`qa/m78/veracite.py`) | **33/33** |
| Gate fil (`qa/m102/veracite_fil.py`) | **6/6** |
| Gate facette (`qa/m110/veracite_facette.py`) | **11/11** |
| Golden (`qa/golden_check.py`) | **116/119 PASS, 0 FAIL** (3 INDÉTERMINÉ = quota 429 env) |
| Suite | **1589 passed, 0 failed**, 43 skipped (env) |
| tsc · build | 0 · OK |
| Grep « rendez-vous dans » / « disponible dans la section » sans bouton | aucune (seule occurrence = un commentaire décrivant l'anti-motif) |

## Ce qui n'a PAS été touché

Aucun outil réimplémenté (on route vers les modules du registre). Aucune porte n'ouvre une section
nue : chaque porte est un module précis, une carte préfiltrée, un volet de Surveillance, ou un
document à IDU résolu. Anti-invention intact (le comptage servi passe le verrou M109). Non mergé —
la branche `feat/m112-guidage-copilote` attend Vic.
