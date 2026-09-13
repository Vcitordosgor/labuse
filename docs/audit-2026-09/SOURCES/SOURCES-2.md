# SOURCES-2 — les 92 au plein potentiel, d'après les producteurs

**Branche** `feat/sources-2` (worktree `~/Desktop/labuse-etat`), tirée de `main` après merge de
REPARATIONS-1. Référence : `RECHERCHE-PRODUCTEURS.md` (lu en entier avant toute écriture).
Étape 0 : 23/23 verrous verts (V3a candidat `q_v14` déclaré, manifeste sert `q_v11_m137`).
Aucun run, aucune bascule, aucun merge, aucun rescoring. Aucun scraping.

---

## LOT 0 — Le DPE, réparé pour de bon

### Ce que le mandat croyait, ce que le producteur montre

Le mandat partait de : « le filtre 974 rend 900 lignes métropolitaines pour 17 authentiques ;
la cause est le code postal ; réingérer en filtrant sur le code INSEE commune 974xx ». **Vérifié
chez le producteur le 13/09/2026 : le filtre INSEE ne répare rien.** Le schéma ADEME
(`dpe03existant`, 230 champs) n'a AUCUN champ « INSEE commune brut » — le seul INSEE est
`code_insee_ban`, produit du géocodage BAN de l'ADEME, et c'est LUI qui est contaminé :

| Filtre (dpe03existant) | Lignes |
|---|---|
| `code_insee_ban:974*` | 914 |
| `code_departement_ban:974` | 914 (identique) |
| `code_postal_brut:[97400 TO 97490]` | 16 |
| INSEE 974 **et** CP brut 974 | 14 |
| INSEE 974 **et** CP brut métropolitain | **900** |

Les 900 sont des logements **métropolitains** (échantillon vérifié : « 38-40 rue Saint Louis,
62200 BOULOGNE-SUR-MER » géocodé Saint-Paul ; Sète, Schiltigheim, Damgan…) que le géocodeur BAN
rabat sur l'île. Le CP brut, saisi par le diagnostiqueur d'après le bien, reste le seul juge —
la doctrine du module était la bonne.

### Le vrai gain : les jeux jamais ingérés — et le piège d'homonymie

Les jeux `dpe02neuf` (1,42 M lignes) et `dpe01tertiaire` (563 k) n'étaient **pas ingérés**.
Moisson CP brut 974 sur les trois jeux = **93 lignes** (16 existants + 75 neufs + 2 tertiaires).
Mais l'examen ligne par ligne a révélé le piège inverse — **le CP brut lui-même peut mentir par
homonymie de commune** :

- les **75 « neufs »** sont UN programme immobilier : `nom_commune_brut = "ST LEU"`, CP saisi
  97436 — mais géocodage BAN **Saint-Leu-la-Forêt (Val-d'Oise, 95563)** score 0,97, et les voies
  (« 42 rue du Rû », « 44-46 rue de Paris ») **n'existent pas** dans la table `adresses` du
  Saint-Leu réunionnais (0 résultat). C'est exactement le « risque d'homonymie majeur » que le
  rapport producteurs signalait (Saint-Denis, Saint-André, Saint-Leu, Saint-Louis) ;
- les **2 « orphelins »** historiques du jeu existant sont à **Montpellier** (« 123 TER avenue de
  Palavas », BAN 34172) et **Lille** (« 40 rue des Jardins Caulier », BAN 59350) — CP brut mal
  saisi. Ils étaient en base depuis M71, épinglés « aucun » ; ils tombent.

**Règle gravée** (`ingest_jeu`, testée) : une ligne au CP brut 974 dont le géocodage BAN est
réunionnais (cohérent) est gardée ; une ligne dont le BAN contredit (ou manque) n'est gardée que
si son adresse brute se **corrobore dans la table `adresses` locale** — sinon rejetée. Mieux vaut
une absence honnête qu'un logement de métropole épinglé sur une parcelle réunionnaise.

### Avant / après

| | avant | après |
|---|---|---|
| Jeux ADEME couverts | 1 (existants) | **3** (existants + neufs + tertiaire) |
| Lignes en base | 17 (dont 2 fausses — Montpellier, Lille — et 1 disparue amont) | **16, toutes corroborées** |
| Rattachées parcelle | 15/17 | **16/16** |
| Rattachées bâtiment (ID-RNB) | 0 (colonne absente) | **8/16** (`rnb_id`, clé BAN → `rnb_batiments.adresses`, sinon contenance géométrique) |
| Miroir producteur | non (lignes mortes conservées) | **oui** (DPE retiré/remplacé amont → supprimé) |
| Rejets mesurés | — | 77 métropolitaines (900 contaminées jamais entrées) |

Détail par jeu (run du 13/09/2026) : existant 14 gardés / 2 rejetés · neuf 0 / 75 · tertiaire 2 / 0.
Le tertiaire n'a ni `type_batiment` ni surface habitable au schéma (sa `surface_utile` reste dans
`raw`, jamais maquillée en habitable) ; `type_batiment='tertiaire'`.

### L'état INVISIBLE ne tombe PAS — et c'est le résultat honnête

Le mandat conditionnait : « faire tomber l'état INVISIBLE **si la fiche se remplit** ». Elle ne se
remplit pas : 16 DPE sur toute l'île ne couvrent aucun des 12 témoins (G2 re-mesuré après
ingestion : `1 source vide (dpe_ademe), 0 sans état INVISIBLE`). La cause n'est plus un filtre :
**les DPE réunionnais ne remontent presque pas à l'observatoire ADEME** (obligation DROM
01/07/2024, mais ni le jeu existants ni le jeu neufs n'en portent la trace en volume — aucun jeu
DOM dédié au catalogue, vérifié). C'est un **trou producteur**, écrit comme tel dans le registre.
Volume « après lot 0 » pour le lot 6 : **16**.

Sentinelle : `dataUpdatedAt` data-fair — mesuré le 13/09/2026, les trois jeux publient dans le
même train mensuel (09/09 tous les trois) → le jeu principal suffit comme signal de version
(commentaire gravé dans `sentinelle.py`).

Preuves : `labuse ingest-dpe` (sortie ci-dessus rejouable), `tests/test_dpe.py` 13/13 dont
`test_ingest_jeu_homonymie_et_miroir`, verrous 23/23 verts après lot.
