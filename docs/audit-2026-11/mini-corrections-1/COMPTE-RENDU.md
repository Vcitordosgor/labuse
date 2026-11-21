# MINI-CORRECTIONS-1 — compte-rendu

Branche `fix/mini-corrections-1` · worktree `~/Desktop/labuse-chasse-ecrans` · API 7460 / front 10260.
Cinq petites corrections relevées par Vic à l'écran. Pas de merge dans `main`, aucune prod, DA existante,
aucun élargissement. Captures à côté de ce compte-rendu **et** dans `~/Desktop/mini-corrections-1/`
(les PNG sous `docs/audit-*/` sont gitignorés par convention du dépôt, `.gitignore:197` — présents sur
disque, non versionnés).

## Étape 0 — préalables

- `pwd` = `/Users/openclaw/Desktop/labuse-chasse-ecrans` · branche `fix/mini-corrections-1` · arbre propre.
- `.env` lu : base locale `postgresql+psycopg://openclaw@localhost:5432/labuse` (rôle OS, trust localhost).
- Base locale lisible (`\dt` OK, `parcels`/`adresses`/`dvf_mutations` peuplées).
- Environnement Python du poste reconstruit (il avait été vidé : aucun env n'avait plus `fastapi`) :
  `.venv` (uv, Python 3.12) depuis `requirements.lock` + `-e .[dev,ci]`. Aucune dépendance ajoutée au projet.

---

## Point 1 — Gabarit réglementaire : paragraphe en double sur l'écran de saisie

**Constat / cause.** Le paragraphe « Où et jusqu'où une construction peut s'implanter, selon les règles
réglementaires intégrées et sourcées dans LABUSE. » **a déjà été retiré** par le commit `1e9446865`
(RETOURS-25, ancêtre de `HEAD`). Le fichier porte la trace du retrait :
`frontend/src/components/outils/Gabarit.tsx:329` — `{/* RETOURS-25 (pt 7) — phrase d'intro … retirée. */}`.

**État actuel (vérifié à l'écran).** L'écran de saisie du Gabarit affiche :
le sous-titre **« Où et jusqu'où implanter, selon les règles sourcées. »** (le `desc` du registre, rendu
par `ModulePanel.tsx` — il **reste**), puis directement le champ d'entrée de parcelle. **Aucun** paragraphe
de redite entre les deux. → **Rien à corriger ; déjà conforme.**

Capture : `C1-gabarit-saisie.png` (sous-titre présent, pas de paragraphe en double).

---

## Point 2 — Pièges et risques : affichage de la parcelle sélectionnée

**Composant de référence** = `frontend/src/components/outils/EntreeParcelle.tsx` (la « boîte parcelle » :
adresse entière en gras + « IDU · zone · surface » dessous + croix ✕, l'adresse/zone/surface résolues via
`/parcels/apercu/{idu}`).

**Constat / cause.** « Pièges et risques » (clé `risques` → `Risques()` → `O5Servitudes`,
`blocB.tsx:74`) **utilise déjà `EntreeParcelle`**. L'affichage « AN 0006 · Ilr · 4,83 ha » **est** le rendu
de `EntreeParcelle` quand la parcelle **n'a pas d'adresse BAN** : le titre porte alors l'IDU court
(`AN 0006`) et la méta la zone + surface (`Ilr · 4,83 ha`). Ce cas est IDENTIQUE dans tous les outils qui
partagent `EntreeParcelle`.

**Preuve (même parcelle sans adresse, `97401000AB0014` — Les Avirons, zone Npnr, 5 ha) :**
- Pièges et risques : `AB 0014` / `Npnr · 5,00 ha` — `C2-pieges-parcelle-sans-adresse.png`
- Gabarit réglementaire : `AB 0014` / `Npnr · 5,00 ha` — `C2-gabarit-meme-parcelle-reference.png`

Les deux captures sont **à l'octet identiques** : Pièges affiche déjà la parcelle **comme les autres
outils**, même composant, mêmes informations, même ordre. Et pour une parcelle **avec** adresse (ex.
`97418000AE0389`), Pièges affiche bien « 37 Rue Emery Talvy, 97438 Sainte-Marie » puis « AE 0389 · UA ·
456 m² ». → **Rien à corriger ; déjà conforme.**

**Autre outil qui n'utilise PAS ce composant** (constaté, non corrigé — hors mandat visuel) : « Définir la
zone » (Étude de zone) — c'est précisément le point 3. Les outils **multi-parcelles** (Assemblage M16,
Programme M22, le lot « Un lot » du diligence) affichent des **puces** d'IDU courts par choix d'UI compact,
et « Remonter le temps » part d'un sélecteur carte — ce ne sont pas des entrées mono-parcelle comparables.

---

## Point 3 — Étape « Définir la zone » : affichage de la parcelle (CORRIGÉ)

**Composant de référence** = `EntreeParcelle` (idem point 2).

**Constat / cause.** `EtudeZone.tsx` (étape 1 « Définir la zone ») utilisait **`ParcelInput` brut** : après
un choix, le champ ne gardait que le **libellé de la suggestion** (« BZ 1065 — Saint-Denis » = IDU court —
commune), sans la boîte parcelle (adresse / zone / surface / ✕).

**Correction.** `frontend/src/components/outils/EtudeZone.tsx` — l'étape 1 utilise désormais
`EntreeParcelle` (qui encapsule lui-même `ParcelInput` pour la saisie). L'état `source`/`picked` est piloté
comme dans Gabarit/Pièges, le clic carte est adopté via l'effet `selectedIdu`, et la ✕ réinitialise la zone.

**Avant / après (même référence `AB0014`) :**
- Avant : champ nu « AB 14 — Cilaos » — `C3-etude-zone-AVANT.png`
- Après : boîte parcelle `AB 0014` / `N · 32,65 ha` + ✕ + aide — `C3-etude-zone-APRES.png`

→ Étude de zone affiche maintenant la parcelle **comme les autres outils**.

---

## Point 4 — Recherche d'adresse : un choix dans la liste doit toujours aboutir (CORRIGÉ)

**D'où vient « aucune adresse ».** En choisissant une proposition d'adresse, la barre appelle
`Header.onPickAddress` : si la suggestion porte un `idu`, elle ouvre la parcelle (`select(idu)`) ; sinon elle
résout le **point** géocodé via `GET /parcels/at?lon&lat`. Or ce résolveur ne faisait qu'un `ST_Contains`
(parcelle qui **contient** le point) et renvoyait **`{idu: null}`** si aucune ne le contenait — point BAN
posé sur la voirie/le trottoir, ou hors cadastre. Le front affichait alors « … localisée, mais aucune
parcelle en base à ce point. » (`Header.tsx`). C'est le « aucune adresse » de Vic.

> Reproduction locale : l'adresse exacte du mandat aboutit déjà en local (ses suggestions portent un `idu`
> rattaché). Le cul-de-sac se reproduit au **niveau du résolveur** : `GET /parcels/at` sur un point hors de
> toute parcelle (ex. point au large `54.5,-21.5`) renvoyait `{"idu":null}` → c'est exactement le chemin qui
> produit « aucune adresse » quand une suggestion géocodée n'a pas d'`idu`.

**Correction.**
- Back `src/labuse/api/app.py` (`parcel_at`) : à défaut d'une parcelle **contenante**, renvoie la parcelle
  la **plus proche** (KNN GiST `<->`) avec sa **distance en mètres** (`distance_m`, geography). Ne rend
  `idu=None` que si la base est vide. `{idu, distance_m}` (0 si contenante).
- Front `frontend/src/lib/api.ts` (`parcelAt`) : type `{idu, distance_m}`.
- Front `frontend/src/components/header/Header.tsx` (`onPickAddress`) : si pas d'`idu` de suggestion, atterrit
  sur la parcelle du point (contenante **ou** la plus proche) et **annonce la distance** ; le message
  « aucune parcelle » n'est plus atteint que base vide (cas impossible en prod).

**Tests (base réelle).**
- `tests/test_mini_corrections_1.py::test_parcel_at_ne_rend_jamais_aucune_parcelle` : point au large →
  parcelle la plus proche + `distance_m > 0` ; point dans une parcelle → `distance_m == 0`.
- `tests/test_mini_corrections_1.py::test_toute_proposition_aboutit_a_une_parcelle` : l'adresse du mandat,
  ses variantes **bis/ter/quater**, et **20 adresses à graine fixe** (setseed `0.4242`, une par commune,
  plusieurs communes) → **24/24 aboutissent à une parcelle servable**, 0 « aucune adresse ».

Résultat (exécution locale) : `24/24 aboutissent · « aucune adresse » = 0`. Capture d'un choix qui aboutit :
`C4-adresse-aboutit-fiche.png` (47 Rue Emery Talvy → fiche `97418000AE0389`).

> Note : une suggestion peut porter un `idu` de parcelle **disparue du cadastre** (ex. `97411000DR0043`,
> `cadastre_disparue_le = 2026-09-01`). La fiche (`/parcels/{idu}`) la sert tout de même avec son historique
> (HTTP 200) — ce n'est **pas** un « aucune adresse ». Aucun changement nécessaire de ce côté.

---

## Point 5 — Mention de fraîcheur des ventes (CORRIGÉ, code + tests seulement)

**D'où vient « 31/12/2025 ».** La mention de fraîcheur DVF vient de `data_sources.source_horizon_at`, écrit
par `persist_millesime` (`src/labuse/ingestion/fraicheur.py`) à partir de la requête `date_sql` de la couche
DVF. Celle-ci lisait **`SELECT max(date_mutation) FROM dvf_mutations_parcelle`** — la **table de détail par
parcelle**, alimentée par la grande passe Mac, qui **retardait** (max `2025-12-31`) alors que les **ventes
servies** (`dvf_mutations`, rechargées par `refresh_dvf` et servies par `_dvf_couverture` « ventes jusqu'à »)
vont jusqu'au **`2026-06-30`**. D'où « ventes jusqu'au 31/12/2025 ».

Mesuré en base :

| source | max(date_mutation) |
|---|---|
| `dvf_mutations` (ventes servies) | **2026-06-30** |
| `dvf_mutations_parcelle` (détail) | 2025-12-31 |
| `data_sources` horizon DVF (avant) | 2025-12-31 |

**Correction.**
1. **La mention est lue sur les ventes réellement servies.** `fraicheur.py` — `date_sql` DVF =
   `SELECT max(date_mutation)::date FROM dvf_mutations`. Vérifié en **dry-run** (transaction annulée, aucune
   écriture persistée) : `persist_millesime(only='dvf')` porterait l'horizon à **2026-06-30**.
2. **Rafraîchissement même sans nouvelle livraison.** `fraicheur.py` — `refresh_dvf` rejoue
   `persist_millesime(only='dvf')` **même en no-op** : la mention ne reste plus figée en attendant un
   rechargement.
3. **La tâche hebdomadaire enchaîne la reconstruction de la table dérivée.** `src/labuse/jobs_impl.py`
   (`ingest_dvf`, job hebdo « ingest-dvf » mardi) enchaîne désormais, dans la MÊME tâche : `refresh-dvf`
   **puis `dvf-marche`** (reconstruction de `dvf_secteur_medianes` = prix des terrains nus, recalcul
   idempotent TRUNCATE+INSERT, **dédup du couple (id_mutation, id_parcelle)** via le CTE `DISTINCT`). Plus de
   dépendance au job BODACC du lendemain : la mention **et** le prix des terrains nus suivent.

**Tests.**
- `test_dvf_horizon_lu_sur_les_ventes_servies` : `date_sql` lit `dvf_mutations`, pas `dvf_mutations_parcelle`.
- `test_tache_hebdo_dvf_enchaine_la_reconstruction_du_derive` : `ingest_dvf` appelle `refresh-dvf` **puis**
  `dvf-marche`.
- `test_refresh_dvf_rafraichit_lhorizon_meme_en_no_op` : `persist_millesime(only='dvf')` rejoué en no-op.

**AUCUNE reconstruction n'a été lancée** (ni en local ni sur le serveur) — code et tests seulement. La
vérification du point 1 (horizon → 2026-06-30) a été faite en transaction **annulée** (rollback), base
inchangée.

### Commande exacte à lancer à la mise en ligne

Une fois le code déployé, rejouer **une fois** la chaîne DVF (idempotente) pour que l'horizon et le prix des
terrains nus reflètent les ventes déjà en base, sans attendre le cron du mardi :

```bash
labuse refresh-dvf && labuse dvf-marche
```

- `labuse refresh-dvf` : recharge toute nouvelle livraison DVF **et** rejoue `persist_millesime(only='dvf')`
  (même en no-op) → `data_sources.source_horizon_at` DVF = `max(date_mutation)` de `dvf_mutations` (→ la
  mention passe à « ventes jusqu'à juin 2026 »).
- `labuse dvf-marche` : reconstruit `dvf_secteur_medianes` (prix des terrains nus), dédup
  (id_mutation, id_parcelle), idempotent.

Ensuite, la tâche hebdomadaire `ingest-dvf` (mardi) enchaîne d'elle-même ces deux étapes.

> Caveat honnête : le prix des terrains nus se calcule sur `dvf_mutations_parcelle` (détail par parcelle,
> chargé par la grande passe Mac). `dvf-marche` reconstruit la table dérivée à partir de ce détail ; pour que
> les prix reflètent les mutations les plus récentes, ce détail doit être à jour côté serveur (passe Mac). La
> **mention de fraîcheur**, elle, est désormais indépendante de ce détail (lue sur `dvf_mutations`).

---

## Vérifications

- Front : `tsc -b` OK · `vitest run` 342/342 OK.
- Python (famille du hook, sans base) : `pytest -m "not db and not local and not reel and not network"` —
  voir ci-dessous (vert).
- Tests du mandat : `tests/test_mini_corrections_1.py` — 3 unitaires + 2 `reel` (base réelle) verts.
- Hook pre-push : **vert, sans `--no-verify`**. Branche poussée.
- API (7460) et navigateur arrêtés avant de rendre la main.

## Fichiers touchés

| Fichier | Point |
|---|---|
| `frontend/src/components/outils/EtudeZone.tsx` | 3 |
| `src/labuse/api/app.py` (`parcel_at`) | 4 |
| `frontend/src/lib/api.ts` (`parcelAt`) | 4 |
| `frontend/src/components/header/Header.tsx` (`onPickAddress`) | 4 |
| `src/labuse/ingestion/fraicheur.py` (`SOURCES['dvf']`, `refresh_dvf`) | 5 |
| `src/labuse/jobs_impl.py` (`ingest_dvf`) | 5 |
| `tests/test_mini_corrections_1.py` | 4, 5 |

Points 1 et 2 : aucun changement de code (déjà conformes) — documentés avec captures.
