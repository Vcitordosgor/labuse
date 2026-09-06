# A0 — Successions : état de la donnée (lecture seule, 06/09/2026)

## 1. Origine
Table `parcel_veille_succession` (`src/labuse/models.py:333`), **reconstruite intégralement** (DELETE+INSERT) à chaque run Score V :
`src/labuse/scoring/score_v.py` — `compute_all()` l.412, insertion l.587-592, critère `veille_succession_eligible()` l.371-377.
Règle (constantes `src/labuse/scoring/score_v_constants.py:170-193`) : propriétaire **personne morale à SIREN confirmé** (jamais un
match par nom) **et** (dirigeant le plus âgé ≥ 70 ans **ou** SCI créée ≥ 20 ans sans mise à jour RNE depuis ≥ 5 ans).
Amont : RNE INPI (âges dirigeants via `v_pm_propension_vendre`, `score_v.py:104-109`), Recherche d'entreprises DINUM en repli
(l.112-131), fichiers PM DGFiP (`parcelle_personne_morale`, l.78-85). Aucun acte, aucun décès : le signal ne vient ni de MAJIC ni de DVF.

## 2. Fraîcheur
`SELECT MAX(computed_at) FROM parcel_veille_succession;` → **2026-08-09 02:10** (28 jours). Amont RNE INPI synchronisé le
**2026-07-06** (62 jours) ; SIRENE sondé quotidiennement (sentinelle « ok » au 03/09). Pas de cadence propre : la table ne bouge
qu'à un run `score-v-compute`. Une version RNE plus récente que celle chargée existe donc très probablement (flux INPI continu).

## 3. Complétude
`SELECT count(*) FROM parcel_veille_succession;` → **7 129 parcelles**. Par commune (`JOIN parcels p ON p.idu = parcelle_id
GROUP BY p.commune`) : **24/24 communes servies**, de Entre-Deux (17) à Saint-Denis (1 045). Jointures sans perte mesurée :
0 IDU non résolu vers `parcels`, 0 SIREN orphelin vers `parcelle_personne_morale` (LEFT JOIN comptés, rejouables).

## 4. Fiabilité
Le signal n'est **pas** une succession ouverte ni un décès constaté : c'est un **radar patrimonial à 3-7 ans** (« succession
probable » — docstring `models.py:333` et `score_v_constants.py:170-173`). Motifs : dirigeant ≥ 70 ans 7 122/7 129 (99,9 %),
SCI dormante 7. `dirigeant_age` rempli à 99,9 % (70 → 117 ans, médiane 76). **Aucune date de signal par parcelle** :
`computed_at` = date du run, l'âge RNE est un état sans historique (proxy `date_mise_a_jour_rne`, documenté `score_v.py:20-22`).
Gardes testées `tests/test_score_v13.py:62-76` : particulier/public/bailleur jamais taggés, match par dénomination jamais.
Par construction, tout propriétaire du signal est une PM nommée — la doctrine « particulier jamais nommé » est sans objet ici.

## 5. Verdict
Servable telle quelle, **à condition de ne jamais écrire « en succession »** : l'écran doit dire « succession probable
(radar 3-7 ans) » et dater le signal du calcul (09/08/2026). Manque : une date « en succession depuis » par parcelle —
impossible avec l'amont actuel. Rafraîchissement possible et utile (RNE de juillet) : `labuse score-v-compute`
(CLI `src/labuse/cli.py:2626-2639`, idempotent) — **non exécuté**, décision Vic (doctrine sentinelle : injection sur clic humain).
