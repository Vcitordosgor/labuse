# M-V · Volet 1 — Réingestion DPE : la premisse est inversée

**Verdict : il n'y a PAS de gisement caché de « dizaines de milliers » de DPE réunionnais.**
La mesure live retourne le contraire du constat du mandat : le stock 974 n'est pas *trop petit
faute d'ingestion complète*, il est **contaminé à ~98 % par des logements métropolitains** que
le géocodeur BAN de l'ADEME rabat sur des codes INSEE 974. L'action utile n'est donc pas de
*grossir* N mais de le **décontaminer**. Fait, testé — STOP review Vic.

## 1. Mesures préalables (API data-fair ADEME, live 09/08/2026)

Dataset consommé par le connecteur : `dpe03existant` (« DPE Logements existants depuis
juillet 2021 », 3CL réformée). National = **15 299 157**.

| Filtre | Compte 974 | Lecture |
|---|---|---|
| `code_insee_ban:974*` | **913** | ce que l'ingesteur voit aujourd'hui |
| `code_region_ban:04` | 913 | idem (même géocodage BAN) |
| `code_departement_ban:974` | 913 | idem |
| dont **CP brut métropolitain** (`code_postal_brut:[1000 TO 96000]`) | **897** | ⚠ logements de métropole |
| dont **CP brut réunionnais** (`code_postal_brut:[97400 TO 97490]`) | **15** | Réunion authentique |
| orphelins (CP brut 974xx **sans** BAN 974) | 2 | Réunion authentique (déjà géré) |
| `code_postal_brut:[97400 TO 97490]` (île entière, une requête) | **17** | = 15 + 2 : le gisement réel |

Autres jeux vérifiés pour écarter tout report caché :
- `dpe-france` (existants **avant** juillet 2021, 10,7 M national) : **~5 lignes** pour tout le
  974 (1–2 par commune). Le DPE n'était pas obligatoire en DROM avant le 01/07/2024.
- Logements **neufs** (post-2021) : 179 pour 974 — non pertinents pour le signal passoire (un
  neuf est classé A/B), doctrine « existants » inchangée, non ingérés.

### La preuve par l'échantillon
12 lignes tirées de `code_insee_ban:974*`, colonne BAN vs colonne BRUTE :

| BAN (géocodeur) | CP brut (diagnostiqueur) | commune brute | adresse brute |
|---|---|---|---|
| 97415 Saint-Paul | 62200 | Boulogne-sur-Mer | 38-40 rue Saint Louis |
| 97416 Saint-Pierre | 83460 | Le Luc | Hameaux Saint Pierre… |
| 97422 Le Tampon | 67300 | Schiltigheim | 50 A rue de Lauterbourg |
| 97413 Saint-Leu | 34200 | Sète | lotissement la Caraussane |
| 97409 Saint-André | 01220 | Divonne-les-Bains | rue Voltaire |
| … | … | … | *(12/12 métropolitains)* |

Le `_geopoint` ADEME est faux (100 % hors Réunion, déjà documenté) **et** le géocodage BAN
lui-même est faux : il fabrique un `identifiant_ban` d'allure réunionnaise (`97415_1330_00038`,
score 0,89) pour un bien de métropole. Les champs **bruts** (CP, commune, adresse saisis par le
diagnostiqueur d'après le bien) sont, eux, cohérents et fiables.

## 2. Le bug latent que ça révèle (pourquoi ce n'est pas cosmétique)

`ingestion/dpe.py::_rattacher` passe 1 = `identifiant_ban` → `adresses.id_ban` (table locale
réunionnaise). Le faux `identifiant_ban` d'un bien métropolitain **matche** une vraie adresse
réunionnaise → le logement de métropole est **épinglé sur une vraie parcelle réunionnaise**,
avec des coordonnées valides mais fausses, et **alimente `v_passoire_thermique`**. Le critère
de validation du mandat « aucun DPE sans coordonnées 2975 valides servi » était respecté à la
lettre (les coords existent) mais violé dans l'esprit (elles désignent le mauvais bien).

## 3. Correctif — on tranche sur le CP BRUT, jamais sur BAN

- `ingestion/dpe.py::is_reunion_authentic(rec)` : vrai si `code_postal_brut` ∈ 97400–97490.
  CP brut **métropolitain → rejeté** (même si BAN dit 974). CP brut **absent → laissé passer**
  (0 cas mesuré sur 913 ; la cascade de rattachement local reste seul juge).
- Branché dans `ingest_commune` **et** `ingest_orphelins` (ceinture-bretelles) ; compteur
  `hors_reunion` remonté au rapport CLI `ingest-dpe`.
- Idempotence inchangée (clé `numero_dpe`), `data_source_id`/fraîcheur inchangés (garde M-H).
- Docstrings connecteur + ingesteur corrigés (le « ~912 / ~10 par mois » était le leurre).

**Effet attendu au prochain `labuse ingest-dpe --force`** : `dpe` passe de ~910 à **~17**,
`hors_reunion` ≈ **~896**, la distribution A→G et le signal passoire ne comptent plus que des
biens réunionnais. `re-run = même compte` (upsert). `check_sources_declarees` inchangé.

⚠ **À faire côté données (hors code)** : purger les lignes métropolitaines déjà présentes en
base. Le `--force` réécrit les 17 authentiques mais **ne supprime pas** les ~890 déjà insérées.
Compte de contrôle avant purge :

```sql
-- lignes déjà en base à supprimer (bien métropolitain épinglé sur parcelle réunionnaise)
SELECT count(*) FROM dpe_records
WHERE (raw->>'code_postal_brut') ~ '^[0-9]+$'
  AND (raw->>'code_postal_brut')::int NOT BETWEEN 97400 AND 97490;
DELETE FROM dpe_records
WHERE (raw->>'code_postal_brut') ~ '^[0-9]+$'
  AND (raw->>'code_postal_brut')::int NOT BETWEEN 97400 AND 97490;
```

(À exécuter LOCAL puis VPS, comme les backfills M-H. Non exécuté par ce mandat — decision Vic.)

## 4. Tests

`tests/test_dpe.py` : `test_is_reunion_authentic` (métropole/réunion/absent) +
`test_contamination_metropole_ecartee` (un bien 62200 dont l'id_ban matcherait une adresse
locale est écarté avant tout épinglage → 0 ligne, 0 passoire). **12/12 verts.**

## 5. Ce qui n'a PAS été fait (et pourquoi)

- **Grossir N** : impossible, le gisement réunionnais réel est ~17. Réfutation propre de la
  premisse. La donnée « dizaines de milliers » n'existe pas dans ADEME pour le 974.
- **Ingérer les neufs** : sans valeur pour le signal passoire (A/B), doctrine existants tenue.
- **Purge des lignes déjà en base** : SQL fourni, laissé à Vic (donnée, pas code).
