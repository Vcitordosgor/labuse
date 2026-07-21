# EXTRACT-DÉPOSANTS-ACTIFS — rapport (STOP final)

Branche `prospection/deposants-actifs`. **Read-only** (aucune table créée, zéro touche scoring/runs servis).
Mandat : CSV de prospection des **personnes morales qui déposent des PC/PA en ce moment** — les opérateurs
actifs, meilleurs prospects avant le chantier front. Précisions Vic (21/07/2026) intégrées : dirigeants RNE
autorisés au CSV ; `exports/` gitignoré, données nominatives jamais en git ; je ne merge pas.

## Livrable
- **CLI** : `labuse deposants-actifs [--mois 24] [--out exports/deposants_actifs.csv]`
  (`src/labuse/ingestion/deposants_actifs.py`).
- **CSV** (`;`, UTF-8) : `siren · denomination · n_permis · n_pc · n_pa · dernier_depot · communes ·
  nb_logements · n_parcelles_detenues · dirigeants · source`. Une ligne par SIREN, tri n_permis décroissant.
- **Résultat du run réel (fenêtre 24 mois)** : **871 déposants actifs** — 231 avec dirigeants RNE diffusibles,
  375 avec foncier détenu (DGFiP), 51 multi-permis (≥ 3). Fichier dans `exports/` (gitignoré, vérifié).

## Sources & honnêteté
- **SITADEL SDES** : SIREN/nom du pétitionnaire présents sur une **partie** des permis seulement
  (9 087 / 50 043 au total ; 1 160 PC/PA sur 24 mois). **On n'extrapole pas** : un permis sans SIREN
  n'invente pas de déposant. SIREN validé `^[0-9]{9}$` (pas de fausse identité).
- **RNE (`pm_dirigeants`)** : dirigeants **actifs ET diffusibles uniquement** — le flag de non-diffusion
  RNE prime (428 dirigeants actifs non diffusibles exclus). Rôle livré en **code RNE brut** (30, 73…),
  aucun libellé inventé. Personne physique jamais inférée d'ailleurs que du registre.
- **DGFiP (`parcelle_personne_morale`)** : simple compte de parcelles détenues (contexte).
- `nb_lgt` mixte (string/number/null dans le raw) → cast gardé par regex, NULL sinon.

## Confidentialité (précisions Vic)
- `exports/` ajouté au `.gitignore` — **le CSV nominatif ne peut pas entrer en git** (vérifié : `git status` vide).
- Tests sur **fixtures synthétiques** uniquement ; ce rapport ne contient **que des agrégats**.

## Micro-item glissé (config dev)
`idle_in_transaction_session_timeout = 10 min` sur le moteur SQLAlchemy (`src/labuse/db.py`, `connect_args`) —
suite à l'incident O12 (transactions zombies de clients tués tenant des verrous jusqu'à 2h47). Une transaction
IDLE si longtemps est toujours un bug ; les requêtes actives ne sont pas concernées. Vérifié : `SHOW` → `10min`.

## Tests
`tests/test_deposants_actifs.py` — **4/4 verts** : fenêtre 24 mois + PC/PA seulement + agrégats ; dirigeant
non diffusible **jamais** dans le CSV (et inactif exclu) ; SIREN invalide écarté ; CSV conforme (colonnes, `;`).

## Findings
1. **Couverture SIREN partielle** (~18 % des permis) : le CSV est un sous-ensemble fiable, pas l'exhaustivité
   des déposants — le dire en préambule d'usage commercial.
2. 640 déposants sur 871 n'ont pas de dirigeant diffusible en base RNE locale (couverture `pm_dirigeants`
   partielle + non-diffusion) — enrichissable si besoin par une passe RNE ciblée sur ces SIREN.
3. Codes rôle RNE bruts : une table de correspondance officielle (INPI) pourrait les libeller proprement — à
   n'ajouter que sourcée.

**STOP final** — branche pushée, je ne merge pas.
