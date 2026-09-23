# LES VERROUS — ce qui ne repose plus sur la vigilance de personne

*CIRCUIT-5, 06/09/2026. Une commande les joue tous : `labuse circuit verrous`. Elle est jouée
par les tests (`pytest -m verrous`), par la sonde chaque nuit (résultat au Journal de la page
Circuit), et par `deploy.sh` qui **refuse de déployer** si un verrou casse. Un déploiement qui
passe la porte est la preuve que tout tient.*

*CIRCUIT-5b, 06/09/2026 — les restes tranchés. Lot 1 : les quatre « à rattacher » entrent au
catalogue (68 + annuaire DILA, RNIC/Anah, RPLS/SDES, conso ENAF/Cerema = **72 servies**),
chacune avec sa ligne `data_sources`, son slug au registre et ses lecteurs déclarés. Lot 2 : les
huit réservoirs muets tranchés — sept rattachés (un lecteur vivant trouvé par grep : permis
d'époque, dirigeants INPI, toiture LiDAR, ombrage végétal, viabilisation APER, ANC Office de
l'eau, enrichissement DINUM du Score V) et **MOBPRO retirée** (lecteur mort) → **71 servies**.
V1d ne signale plus aucun réservoir muet.*

Trois verdicts : **vert** (la phrase est vraie), **cassé** (la commande sort en erreur, le
déploiement refuse, la ligne rouge apparaît au Résumé), **à décider** (rien de cassé — une
question t'attend, sans urgence, jamais bloquante).

## Note d'exploitation — le faisceau de CA de la sonde (CIRCUIT-P4, lot 0)

*23/09/2026.* Sur le Mac de dev (Python de Homebrew), le contexte TLS par défaut d'`urllib`
n'est **branché sur aucune autorité de certification** : les 84 sondes de la sentinelle
tombaient toutes en `CERTIFICATE_VERIFY_FAILED` et la page Données **mentait en local** —
« producteur injoignable » partout, alors que les producteurs répondent. Ce n'est pas un état
des sources, c'est l'environnement TLS.

Le geste : `sentinelle._http` fournit désormais un **faisceau de CA explicite** (un seul point
de sortie réseau). L'ordre de préférence :

1. `SSL_CERT_FILE` s'il est posé dans l'environnement (ou `.env`) — on l'honore tel quel ;
2. sinon le bundle **`certifi`** (toujours packagé dans le venv) ;
3. sinon (certifi absent) le trousseau système, avec un `WARNING` au log — jamais muet.

En prod Linux le contexte par défaut marche déjà ; le faisceau ne fait que le rendre
**déterministe**. Aucune donnée n'est téléchargée ni injectée : la sentinelle prévient, Vic
décide (doctrine SENTINELLE-1).

Preuve locale (réseau seul, sans base — pour ne pas toucher le run résiduel en cours) :
échantillon de 8 URLs `https` du `SEED` appelées via `sentinelle._http` → **8/8 `HTTP 200`,
0 `CERTIFICATE_VERIFY_FAILED`** (avant le geste : 8/8 en échec SSL).

## Lot 1 — les tables

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V1a** | Aucun moteur ne lit une table hors de la carte table → réservoir. | La carte est déclarée dans le code (`registre/tables.py`) ; les requêtes des moteurs et les passe-plats sont passés au crible à chaque passage. | Détail du repère « 71 » (la carte, réservoir par réservoir). |
| **V1b** | Pendant un passage de la sonde, aucune table hors carte n'est touchée. | Le journal des requêtes de la session capture TOUT ce que la sonde lit vraiment. | Journal (passage de nuit). |
| **V1c** | Toute table du schéma est dans la carte, ou orpheline LISTÉE avec son action. | Les orphelines sont CALCULÉES (le schéma moins la carte) — une table nouvelle inconnue sort orpheline toute seule ; sans action proposée, le verrou casse. | Résumé « tables orphelines à purger » · TABLES-ORPHELINES.md · `labuse tables purger` (déplace vers `poubelle`, jamais un DROP — ton geste). |
| **V1d** | Aucun réservoir muet ne dort dans la vitrine. | Chaque réservoir servi doit être lu par une donnée du registre ; sinon la question « source à retirer, ou lecteur manquant ? » est posée. | Résumé « réservoirs sans lecteur » (à décider). |

## Lot 2 — les sources : le même compte partout (71 servies après CIRCUIT-5b)

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V2a** | Le nombre de sources servies est LE MÊME partout : vitrine SQL, prédicat Python, page — et chacune a sa place dans la carte. | Une égalité de comptes (jamais un nombre écrit en dur) mesurée à chaque passage. | Le repère « N / total » du Résumé. |
| **V2b** | Toute ligne du catalogue hors vitrine dit pourquoi : alias (sa cible en vitrine), retirée (date + raison), hub, ou chantier nommé. | Les statuts sont de PREMIÈRE CLASSE en base (plus un préfixe de note) ; un doublon caché casse le verrou. Le seed refuse une source sans id, producteur, mode, cadence et sonde. | Détail du repère « 71 », « lignes en base non servies » (chaque ligne dit sa raison). |

## Lot 3 — les versions : une seule servie, partout

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V3a** | Chaque réservoir n'a qu'une version servie ; les tuiles servent le run du manifeste. | Les seules générations admises d'une table sont `x`, `x__attente`, `x__precedente` (l'échange CIRCUIT-3) ; les pointeurs sont comparés. | Détail Pompe (pointeurs, horloges). |
| **V3b** | Après une bascule, zéro eau ancienne — rien d'ouvert hors « gelé, étiqueté ». | L'eau est MESURÉE à l'instant du passage ; s'il en reste, le verrou nomme la donnée et le robinet. | Résumé « robinets servent de l'eau ancienne ». |
| **V3c** | La sonde écrit des ids, plus des libellés. | Chaque écart et chaque eau ancienne portent `chiffre_id` et `robinet_id` du registre — attribuables, comptables, cliquables. | Détail Robinet (fuites / eau). |

## Lot 4 — les communes : la bonne ligne pour la bonne commune

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V4a** | Le SRU de Saint-Benoît n'apparaît jamais sur Sainte-Marie : un code hors des 24 communes ne peut plus ENTRER en base. | Une clé étrangère Postgres sur chaque table à maille commune, vers le référentiel seedé du code. C'est la base qui refuse, pas une revue. | Résumé (lignes héritées « à décider » s'il en reste). |
| **V4b** | Saint-Benoît sert les valeurs de Saint-Benoît — celles attendues chez le producteur, pas seulement différentes. | L'identité du bloc servi (insee, commune) + les attendus lus chez INSEE et GASPAR, rejoués à chaque passage. | Fiche commune (les cartes) ; écarts au Journal. |
| **V4c** | Sur une parcelle en limite de commune, la zone PLU au centroïde vient du document de SA commune. | Trois parcelles témoins AU CONTACT d'une limite, vérifiées contre la partition GPU `DU_<insee>`. | Fiche parcelle des témoins. |
| **V4d** | Chacune des 15 cartes de la fiche commune a, pour chacune des 24 communes, son attendu producteur ou sa ligne à valider. | Un fichier par carte (`filtres/echantillons/communes/`), structurellement complet sinon le verrou casse ; ce qui reste à lire chez le producteur est proposé dans ECHANTILLONS-A-VALIDER.md. | ECHANTILLONS-A-VALIDER.md § communes. |
| **V4e** | Aucune ligne servie à maille adresse / parcelle / bâtiment ne porte un code postal hors 974/977 ni une commune hors des 24 (SOURCES-3 lot 4). | Le garde-fou commun `ingestion/garde_974.py` croise trois critères indépendants — CP réunionnais (974xx/977xx CEDEX), commune ∈ 24 (normalisée : accents, casse, tirets, ST/STE), coordonnées dans l'emprise de l'île — et rejette dès que les critères présents ne confirment pas TOUS La Réunion (le cas Saint-Leu-la-Forêt : CP+commune réunionnais mais coordonnées Val-d'Oise → rejet). Le verrou scanne les tables servies à colonne code postal ; le rejet d'ingestion est journalisé avec ses trois valeurs. | Journal (`geste=garde_974`) ; test `test_garde_974.py`. |

## Lot 5 — les concepts et les moteurs

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V5a** | Un concept = un id : deux données au même libellé ou à la même définition n'existent pas. | Normalisation (casse, accents, espaces) sur tout le registre ; les DEUX seuls groupes assumés sont déclarés dans le code et motivés dans CONCEPTS-CANONIQUES.md. | CONCEPTS-CANONIQUES.md. |
| **V5b** | Une donnée = une fonction : un producteur nommé partout, plus aucun `sql_propre` ni `front`. | Les gardes CIRCUIT-2, réunies dans les verrous, plus l'intégrité du registre. | Détail Robinet (moteur). |
| **V5c** | Zéro couple (donnée, robinet) silencieux. | Chaque couple est sondé la nuit, mono-robinet (le golden et les règles CIRCUIT-4 font foi), ou porte SA raison nommée — jamais un « non couvert » muet. Les témoins tournent : 54 fixes + 50 tirés chaque nuit parmi les parcelles consultées la veille. | Journal (passage de nuit, compte des témoins). |
| **V5d** | Tout par déclaration : chaque donnée à la maille parcelle servie sur la fiche est déclarée avec une section nommée — aucun câble muet. | Le verrou croise les données maille parcelle servies par un robinet `fiche` avec les déclarations `declarations/fiche` ; une donnée servie sans section déclarée casse (FICHE-RANGEMENT-2 lot 2). | Déclarations fiche ; `verrou_fiche_sections`. |
| **V5e** | Tout par déclaration (commune) : chaque donnée à la maille commune servie sur la fiche commune est déclarée avec sa carte — aucun câble muet. | Le pendant commune du V5d : le verrou croise les données maille commune servies par un robinet `fiche_commune_*` avec les déclarations `declarations/commune` ; une donnée servie sans carte déclarée casse (COMMUNE-RANGEMENT-2 lot 5). | Déclarations commune ; `verrou_fiche_commune_cartes`. |
| **V5f** | Tout chiffre affiché par un OUTIL porte un id du registre. | Le verrou lit les clés d'outils VISIBLES de `registry.ts` (cartes du menu, hors alias hidden), vérifie que chacune a son robinet au registre et que ce robinet ne sert que des chiffres déclarés dans `DONNEES` — un outil qui lirait la base hors registre (SQL direct, champ payload non déclaré) casse (OUTILS-FIX-5 lot 7). | `registry.ts` ; `verrou_outils_registre`. |
| **V6a** | Aucune règle chiffrée VALIDÉE sans sa source : article + page + citation, toujours — une valeur validée sans preuve n'existe pas. | Le verrou parcourt les calibrations PLU (`destinations.iter_regles_calibrees`) et n'exige la source complète que des feuilles au statut `valide` ; les `propose` de l'agent attendent la revue (PLU-CALIBRAGE-1 lot 4). | Calibration PLU ; `verrou_regles_citations`. |
| **V7a** | Chaque tuile servie reproduit la brute : même nombre d'objets, aucune partie perdue (GeometryCollections comprises), contour < 1 px, position exacte — aux zooms 10/13/16. | Le verrou décode la tuile RÉELLEMENT servie par le tuyau vectoriel (56 couches × z10/13/16) et la compare à la géométrie brute : nombre d'objets, aires, position. Une couche qui perd un morceau à la subdivision, ou décale une géométrie, casse ici (COUCHES-TUYAU-1). | Décodage des tuiles servies ; `verrou_tuiles`. |
| **V8a** | Toute veille et tout envoi a un job du registre : chaque fonction d'évaluation (suivis, secteurs, recherches, veilles, sentinelle) et d'envoi (digest, Radar) est portée par un job du crontab généré, qui l'appelle — retirer les crons legacy n'éteint plus rien. | Le verrou parcourt les fonctions critiques de veille/envoi ; chacune doit avoir son job au registre `labuse.jobs.JOBS` (donc au crontab généré) et l'implémentation du job doit l'appeler vraiment (suit un niveau de délégation). Casse si une fonction n'a pas de job (VEILLE-FIX-1 lot 1). | Registre des jobs ; `verrou_veille_a_un_job`. |

## Ce que tu peux dire sans réserve

- « Le PLU affiché sur Saint-Paul est celui de Saint-Paul » — V4a (la base refuse), V4c (témoins en limite).
- « Si Sitadel 2026 est en base, tout l'app lit Sitadel 2026 » — V3a (une génération), V3b (zéro eau), V1b (aucune lecture hors carte).
- « Les outils n'écoutent que les sources du catalogue » — V2a (le même compte partout), V2b (le reste dit pourquoi), V1a (les moteurs ne lisent que la carte).
- « Une même donnée donne le même résultat partout » — V5a (un id), V5b (une fonction), V5c (comparé ou raisonné), la sonde chaque nuit.
- « Tout le monde écoute le même moteur » — V5b, V1a, et la porte de `deploy.sh` : rien ne part si un verrou casse.

## Tes gestes, quand tu veux

- `labuse circuit verrous` — rejouer tout, une ligne par verrou (phrase, verdict, preuve).
- `labuse tables purger` puis `--apply` — pousser les orphelines vers `poubelle` (réversible).
- Trancher les « réservoirs sans lecteur » (V1d) et purger les orphelines (TABLES-ORPHELINES.md) — les « à rattacher » sont tranchés (CIRCUIT-5b lot 1).
- Merger, déployer — la porte fait le reste.
