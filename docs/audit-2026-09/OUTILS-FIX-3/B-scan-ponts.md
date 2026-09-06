# Lot B — Les deux ponts vers Scan patrimoine : cause & correction

Constat Vic : depuis **Permis**, le pont ouvre Scan sur le SIREN **392801130** et l'écran rend
« 0 parcelle · 0 actionnable · 0 m² SDP » + l'encart « Aucun dirigeant au registre INPI — succession
ou société en sommeil probable », alors que le permis porte bien un SIRET.

## B1 — Cause établie (fichier:ligne + SQL rejouable)

### 1. Le pont transmet-il la bonne valeur ?

- Pont : `frontend/src/components/outils/ModulePanel.tsx:431` (`PermitDrawer`) →
  `setM02Prefill(String(d['porteur_siren']))`, puis `setModule('patrimoine')`.
- Origine de `porteur_siren` : `src/labuse/api/modules.py:557` → `s.raw->>'petitioner_siren' AS porteur_siren`.
- Peuplement : `src/labuse/ingestion/permits_sdes.py:224-229` — SITADEL fournit `SIREN_DEM` (9) **et**
  `SIRET_DEM` (14) séparément ; `petitioner_siren` reçoit **SIREN_DEM** (9 chiffres).

**Verdict : le pont passe bien un SIREN à 9 chiffres.** `392801130` fait exactement 9 chiffres — ce
n'est PAS un SIRET tronqué. L'hypothèse « SIRET passé là où on attend un SIREN » ne s'applique donc
pas à ce cas précis. (Garde défensive ajoutée quand même — voir B2.)

### 2. Endpoint & requêtes de résolution

- Endpoint : `src/labuse/api/modules.py:232` — `GET /modules/patrimoine?siren=…`.
- Liste des parcelles + résolution (modules.py:253-264) :
  ```sql
  SELECT p.id, p.idu, p.commune, p.surface_m2, z.zone_fam, r.sdp_residuelle_m2,
         s2.tier AS tier_v2, s2.rang AS rang_v2,
         (d.status IN ('exclue','faux_positif_probable')) AS etage0
  FROM parcelle_personne_morale pm
  JOIN parcels p ON p.idu = pm.idu
  LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
  LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
  LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
  LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
  WHERE pm.siren = :s ORDER BY s2.rang ASC NULLS LAST;
  ```
- Raison sociale (modules.py:268) : `SELECT max(denomination) FROM parcelle_personne_morale WHERE siren=:s`.
- Signal INPI (modules.py avant fix) : `bool(siren) AND NOT EXISTS(SELECT 1 FROM pm_dirigeants WHERE siren=:s)`.

`parcelle_personne_morale.siren` est un `varchar` peuplé au **SIREN cadastral (9 chiffres)**.

### 3. Le zéro est-il réel ou un échec silencieux ? — vérifié sur la base réelle (`psql labuse`)

```sql
SELECT count(*)            FROM parcelle_personne_morale WHERE siren='392801130';  -- 0
SELECT max(denomination)   FROM parcelle_personne_morale WHERE siren='392801130';  -- NULL
SELECT count(*)            FROM pm_dirigeants            WHERE siren='392801130';  -- 0
SELECT count(*)            FROM parcelle_personne_morale WHERE siren LIKE '392801130%'; -- 0
```

**Le zéro est RÉEL, pas une requête en erreur** : l'entreprise 392801130 ne détient aucune parcelle
à La Réunion et n'a pas de raison sociale dans le fichier foncier — elle n'est **pas résolue** chez
nous comme propriétaire réunionnais (cas classique d'un pétitionnaire de permis basé hors de l'île).
La requête ne lève pas ; elle rend légitimement 0 ligne.

### 4. Logique de l'encart INPI (le vrai défaut)

- Front : `frontend/src/components/outils/ModulePanel.tsx:234-238` — affiché ssi `d['inpi_sans_dirigeant'] === true`.
- Back (avant fix) : `bool(siren) AND NOT EXISTS(pm_dirigeants)`.

**Défaut** : `pm_dirigeants` ne contient de ligne que pour les SIREN que l'ingestion INPI a résolus
**avec** dirigeant. Une absence de ligne ne distingue pas « INPI résolu, zéro dirigeant » (vrai
signal « foncier fantôme ») de « INPI jamais résolu pour ce SIREN » (angle mort). Couverture mesurée :

```sql
SELECT count(DISTINCT siren) FROM parcelle_personne_morale;                        -- 12 605 propriétaires PM
SELECT count(DISTINCT ppm.siren) FROM parcelle_personne_morale ppm
  WHERE EXISTS (SELECT 1 FROM pm_dirigeants d WHERE d.siren=ppm.siren);            -- 9 337 (26 % sans ligne)
```

Comme `bool(siren)` reste vrai même sur une entreprise **inconnue** de notre base, l'encart se
déclenchait sur 392801130 (0 parcelle, 0 dirigeant) — une interprétation tirée d'un pur angle mort.

## B2 — Correction

- **Écran vide dit ainsi** (`ModulePanel.tsx`, bloc `data-m02-aucune-parcelle`) : quand
  `n_parcelles === 0`, on affiche « Cette entreprise (SIREN …) ne détient aucune parcelle à La Réunion »
  au lieu des trois zéros + encart. Le SIREN est résolu (le pont/la recherche a rendu un résultat) ;
  l'entreprise ne possède simplement rien sur l'île.
- **Garde SIRET→SIREN à la source** (`ModulePanel.tsx:431`) : le pont tronque à `…replace(/\D/g,'').slice(0,9)`.
  Sans effet sur `porteur_siren` (déjà 9 chiffres) ; couvre le jour où la source n'exposerait qu'un SIRET.

## B3 — L'encart ne s'affiche que sur une entreprise résolue

Back (`modules.py`) : `inpi_sans_dirigeant = bool(rows) and bool(nom) and NOT EXISTS(pm_dirigeants)`.
Il ne se déclenche donc **que** pour une entreprise réellement détentrice de foncier réunionnais
(≥ 1 parcelle + raison sociale) — jamais sur une entreprise non résolue ni sur une requête vide.
Le vrai « foncier fantôme » (propriétaire résolu, aucun dirigeant) reste signalé.

Décision signalée : faute de journal de résolution INPI en base, on ne peut pas prouver, pour un
propriétaire résolu, que l'absence de ligne est « résolu & vide » plutôt que « non ingéré ». La garde
retenue (entreprise détentrice de foncier) est le meilleur proxy disponible sans nouvelle table ; le
signal reste donc borné aux entreprises que nous connaissons comme propriétaires.

Tests : `tests/test_patrimoine.py::test_patrimoine_entreprise_sans_foncier_pas_de_signal_inpi` (0
parcelle → False) et `::test_patrimoine_signal_inpi_sur_proprietaire_resolu` (propriétaire résolu →
True, puis False dès qu'un dirigeant est présent).
