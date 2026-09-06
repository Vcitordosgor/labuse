# LES VERROUS — ce qui ne repose plus sur la vigilance de personne

*CIRCUIT-5, 06/09/2026. Une commande les joue tous : `labuse circuit verrous`. Elle est jouée
par les tests (`pytest -m verrous`), par la sonde chaque nuit (résultat au Journal de la page
Circuit), et par `deploy.sh` qui **refuse de déployer** si un verrou casse. Un déploiement qui
passe la porte est la preuve que tout tient.*

Trois verdicts : **vert** (la phrase est vraie), **cassé** (la commande sort en erreur, le
déploiement refuse, la ligne rouge apparaît au Résumé), **à décider** (rien de cassé — une
question t'attend, sans urgence, jamais bloquante).

## Lot 1 — les tables

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V1a** | Aucun moteur ne lit une table hors de la carte table → réservoir. | La carte est déclarée dans le code (`registre/tables.py`) ; les requêtes des moteurs et les passe-plats sont passés au crible à chaque passage. | Détail du repère « 68 » (la carte, réservoir par réservoir). |
| **V1b** | Pendant un passage de la sonde, aucune table hors carte n'est touchée. | Le journal des requêtes de la session capture TOUT ce que la sonde lit vraiment. | Journal (passage de nuit). |
| **V1c** | Toute table du schéma est dans la carte, ou orpheline LISTÉE avec son action. | Les orphelines sont CALCULÉES (le schéma moins la carte) — une table nouvelle inconnue sort orpheline toute seule ; sans action proposée, le verrou casse. | Résumé « tables orphelines à purger » · TABLES-ORPHELINES.md · `labuse tables purger` (déplace vers `poubelle`, jamais un DROP — ton geste). |
| **V1d** | Aucun réservoir muet ne dort dans la vitrine. | Chaque réservoir servi doit être lu par une donnée du registre ; sinon la question « source à retirer, ou lecteur manquant ? » est posée. | Résumé « réservoirs sans lecteur » (à décider). |

## Lot 2 — les sources : 68, pas un de plus

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V2a** | Le nombre de sources servies est LE MÊME partout : vitrine SQL, prédicat Python, page — et chacune a sa place dans la carte. | Une égalité de comptes (jamais un 68 écrit en dur) mesurée à chaque passage. | Le repère « N / 68 » du Résumé. |
| **V2b** | Toute ligne du catalogue hors vitrine dit pourquoi : alias (sa cible en vitrine), retirée (date + raison), hub, ou chantier nommé. | Les statuts sont de PREMIÈRE CLASSE en base (plus un préfixe de note) ; un doublon caché casse le verrou. Le seed refuse une source sans id, producteur, mode, cadence et sonde. | Détail du repère « 68 », « lignes en base non servies » (chaque ligne dit sa raison). |

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

## Lot 5 — les concepts et les moteurs

| | La phrase | Ce qui le garantit | Où ça se lit |
|---|---|---|---|
| **V5a** | Un concept = un id : deux données au même libellé ou à la même définition n'existent pas. | Normalisation (casse, accents, espaces) sur tout le registre ; les DEUX seuls groupes assumés sont déclarés dans le code et motivés dans CONCEPTS-CANONIQUES.md. | CONCEPTS-CANONIQUES.md. |
| **V5b** | Une donnée = une fonction : un producteur nommé partout, plus aucun `sql_propre` ni `front`. | Les gardes CIRCUIT-2, réunies dans les verrous, plus l'intégrité du registre. | Détail Robinet (moteur). |
| **V5c** | Zéro couple (donnée, robinet) silencieux. | Chaque couple est sondé la nuit, mono-robinet (le golden et les règles CIRCUIT-4 font foi), ou porte SA raison nommée — jamais un « non couvert » muet. Les témoins tournent : 54 fixes + 50 tirés chaque nuit parmi les parcelles consultées la veille. | Journal (passage de nuit, compte des témoins). |

## Ce que tu peux dire sans réserve

- « Le PLU affiché sur Saint-Paul est celui de Saint-Paul » — V4a (la base refuse), V4c (témoins en limite).
- « Si Sitadel 2026 est en base, tout l'app lit Sitadel 2026 » — V3a (une génération), V3b (zéro eau), V1b (aucune lecture hors carte).
- « Les outils n'écoutent que les 68 sources » — V2a (68 = 68 partout), V2b (le reste dit pourquoi), V1a (les moteurs ne lisent que la carte).
- « Une même donnée donne le même résultat partout » — V5a (un id), V5b (une fonction), V5c (comparé ou raisonné), la sonde chaque nuit.
- « Tout le monde écoute le même moteur » — V5b, V1a, et la porte de `deploy.sh` : rien ne part si un verrou casse.

## Tes gestes, quand tu veux

- `labuse circuit verrous` — rejouer tout, une ligne par verrou (phrase, verdict, preuve).
- `labuse tables purger` puis `--apply` — pousser les orphelines vers `poubelle` (réversible).
- Trancher les « réservoirs sans lecteur » et les « à rattacher » (TABLES-ORPHELINES.md).
- Merger, déployer — la porte fait le reste.
