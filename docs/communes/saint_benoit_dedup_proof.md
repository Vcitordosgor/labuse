# Saint-Benoît — preuve de déduplication ciblée (doublon EXACT `spatial_layers`)

- **Commune / INSEE** : Saint-Benoît / 97410
- **Table** : `public.spatial_layers`
- **Paire candidate** : `id = 1133604` (à GARDER) vs `id = 1133675` (à SUPPRIMER)
- **Contexte** : run gold standard du 2026-06-23T07:56:01 sorti en `EXIT_ROLLBACK` (code 1),
  cause unique = contrôle critique « aucune duplication de couche » KO (1 groupe).
- **Action validée** : suppression ciblée de **la seule** ligne `1133675` (doublon strictement
  identique à `1133604`), **sans rollback, sans re-cascade, sans commit, sans gold, sans merge**.

---

## 1. Export des deux lignes (LECTURE SEULE, avant suppression)

| Champ | `id = 1133604` (gardée) | `id = 1133675` (supprimée) | Identique ? |
|---|---|---|---|
| `kind` | `plu_gpu_prescription` | `plu_gpu_prescription` | ✅ |
| `subtype` | `07` | `07` | ✅ |
| `name` | `element de paysage, de patrimoine, point de vue, a proteger, a mettre en valeur` | `element de paysage, de patrimoine, point de vue, a proteger, a mettre en valeur` | ✅ |
| `commune` | `Saint-Benoît` | `Saint-Benoît` | ✅ |
| `data_source_id` | `31` | `31` | ✅ |
| `ingestion_run_id` | `42` | `42` | ✅ |
| `created_at` | `2026-06-23 06:13:07.360569+00` | `2026-06-23 06:13:07.360569+00` | ✅ |
| `geom` (type) | `ST_Point` (SRID 4326) | `ST_Point` (SRID 4326) | ✅ |
| `geom` (WKT) | `POINT(55.72508134 -21.04825756)` | `POINT(55.72508134 -21.04825756)` | ✅ |
| `geom` `md5(ST_AsBinary)` | `9252581b5853eac63bef417d222692a8` | `9252581b5853eac63bef417d222692a8` | ✅ |
| `geom_2975` `md5(ST_AsBinary)` | `c329de2d87f994609f05e5137d150f21` | `c329de2d87f994609f05e5137d150f21` | ✅ |
| `attrs` `md5(::text)` | `e60744bc8f8f9aebe237fd8ee664987b` | `e60744bc8f8f9aebe237fd8ee664987b` | ✅ |

`attrs` (JSONB) — **identique** sur les deux lignes :

```json
{
  "txt": "EP 131",
  "idurba": "97410_PLU_20200206",
  "source": "API Carto GPU — prescription-pct",
  "libelle": "element de paysage, de patrimoine, point de vue, a proteger, a mettre en valeur",
  "typepsc": "07",
  "stypepsc": "00",
  "geom_kind": "pct",
  "millesime": "97410_PLU_20200206",
  "partition": "DU_97410",
  "url_source": "https://apicarto.ign.fr/api/gpu/prescription-pct"
}
```

## 2. Comparaison stricte (LECTURE SEULE)

```
ST_Equals(geom_1133604, geom_1133675)          = true
ST_OrderingEquals(geom_1133604, geom_1133675)  = true
md5(ST_AsBinary(geom))      égaux              = true
md5(ST_AsBinary(geom_2975)) égaux              = true
attrs = attrs               (JSONB)            = true
attrs::text = attrs::text                      = true
```

**kind / subtype / name / attrs / géométrie / hash / commune / data_source : tous identiques.**
Seule différence : la clé technique `id` (1133604 ≠ 1133675). → **Doublon EXACT confirmé.**

## 3. Confirmation que le doublon est UNIQUE et fermé

Expansion de **tous** les groupes dupliqués de la commune (clé pipeline =
`kind, md5(ST_AsBinary(geom_2975)), subtype, name, md5(attrs::text)`) :

```
kind                 | subtype | n |        ids
---------------------+---------+---+--------------------
plu_gpu_prescription |   07    | 2 | {1133604,1133675}
(1 groupe au total)
```

Le **seul** groupe en doublon contient **exactement** ces deux ids (`n = 2`).
→ Supprimer `1133675` ramène nécessairement `dup_groups` de **1 à 0**.

## 4. État métier AVANT suppression (référence d'invariance)

```
spatial_layers (commune)            = 75162
plu_gpu_prescription                = 2079
dvf_mutations                       = 654
verdicts (dernière éval / parcelle) : opportunite=589  a_creuser=4611  exclue=1035  faux_positif_probable=15436  (Σ=21671)
```

Aucune clé étrangère entrante ne référence `spatial_layers.id` (0 contrainte) → la
suppression d'une ligne **ne cascade nulle part**, elle retire uniquement cette ligne.

---

## 5. Suppression ciblée (transaction, rollback automatique si ≠ 1 ligne)

Suppression **explicite par id** (jamais un prédicat générique), dans une transaction
avec garde-fous ; toute anomalie (`ROW_COUNT ≠ 1`, gardée absente, cible survivante)
déclenche `RAISE EXCEPTION` → la transaction entière est annulée.

```sql
BEGIN;
DO $$
DECLARE keep_before int; del_before int; n int; keep_after int; del_after int;
BEGIN
  SELECT count(*) INTO keep_before FROM spatial_layers WHERE id = 1133604;
  SELECT count(*) INTO del_before  FROM spatial_layers WHERE id = 1133675;
  IF keep_before <> 1 THEN RAISE EXCEPTION 'ABORT: keeper 1133604 absent before (%)', keep_before; END IF;
  IF del_before  <> 1 THEN RAISE EXCEPTION 'ABORT: target 1133675 absent before (%)', del_before; END IF;

  DELETE FROM spatial_layers WHERE id = 1133675;        -- suppression EXPLICITE par id
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 1 THEN RAISE EXCEPTION 'ABORT: deleted % (≠1) -> rollback', n; END IF;

  SELECT count(*) INTO keep_after FROM spatial_layers WHERE id = 1133604;
  SELECT count(*) INTO del_after  FROM spatial_layers WHERE id = 1133675;
  IF keep_after <> 1 THEN RAISE EXCEPTION 'ABORT: keeper 1133604 missing after (%)', keep_after; END IF;
  IF del_after  <> 0 THEN RAISE EXCEPTION 'ABORT: target 1133675 survives after (%)', del_after; END IF;
END $$;
COMMIT;
```

Résultat d'exécution :

```
BEGIN
NOTICE:  GUARDS PASSED: deleted=1 (id=1133675) | keeper 1133604 present=1 | target 1133675 present=0
DO
COMMIT
psql_exit_code=0
```

- **Ligne supprimée** : `id = 1133675` (1 ligne, exactement).
- **Ligne conservée** : `id = 1133604` (intacte).

## 6. Vérification APRÈS (LECTURE SEULE, indépendante)

```
id 1133604 présent = true
id 1133675 présent = false
dup_groups (DUP_GROUPS_SQL pipeline) = 0          (avant : 1)
plu_gpu_prescription                 = 2078       (avant : 2079)
spatial_layers (commune)             = 75161      (avant : 75162  →  −1, la seule ligne retirée)
dvf_mutations                        = 654        (INCHANGÉ)
verdicts : opportunite=589  a_creuser=4611  exclue=1035  faux_positif_probable=15436  (Σ=21671)  INCHANGÉS
gardée 1133604 : POINT(55.72508134 -21.04825756) · attrs.txt = "EP 131"  (intacte)
```

| Métrique | Avant | Après | Δ |
|---|---|---|---|
| `dup_groups` | 1 | **0** | ✅ corrigé |
| `plu_gpu_prescription` | 2079 | 2078 | −1 (le doublon) |
| `spatial_layers` (commune) | 75162 | 75161 | −1 (uniquement) |
| `dvf_mutations` | 654 | 654 | 0 |
| opportunité / à creuser / écartée / faux positif | 589 / 4611 / 1035 / 15436 | 589 / 4611 / 1035 / 15436 | 0 (strict) |

## 7. Post-checks pipeline & rapport

Re-passage des post-checks via le **code du pipeline lui-même**
(`read_postcheck_metrics` → `postcheck_results` → `final_decision`, LECTURE SEULE,
**aucune re-cascade**) :

- `aucune duplication de couche` → **✓ OK (0 groupes)** (seul contrôle qui était KO)
- tous les autres contrôles critiques restent **✓ OK** ;
  verdicts cohérents (Σ = 21671), bâti 34683, voirie 14922, zonage 100 %, index GIST 3/3.
- **Code de sortie final = 0 (SUCCÈS)**.

Rapport `docs/communes/saint_benoit_RESULTS.md` régénéré en **exit 0** (horodatage du run
d'origine préservé). Seuls les champs liés au doublon changent vs la version exit 1
(verdict, prescription 2079→2078, duplication 1→0, contrôle dédup ✗→✓, conclusion) ;
verdicts et autres critiques **strictement inchangés**.

> Note : le doublon retiré est un **point strictement identique** (même géométrie exacte
> que `1133604`). Sa suppression est **neutre pour la cascade** : aucune relation spatiale
> ne change (le point subsiste via `1133604`), d'où des verdicts inchangés sans re-cascade.

**Interdits respectés** : aucun rollback, aucune re-cascade, aucun passage gold, aucun
commit, aucun merge, aucun nettoyage d'évaluations stale, aucun amend/reset-author/force-push.

