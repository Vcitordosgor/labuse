# Saint-André — résultats import gold standard (2026-06-23T18:59:59)

- **Commune / INSEE** : Saint-André / 97409
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)
- **Particularité** : zonage PLU **absent du Géoportail de l'Urbanisme** (0 zone propre `DU_97409` au GPU, API Carto + WFS) → **repli AGORAH** automatique (cf. § Repli AGORAH).

## Gates pré-commune (avant run réel)

- **Purge disque contrôlée** (disque saturé avant le backup) : **6 dumps obsolètes** (`pre-*`) supprimés pour libérer l'espace. **Aucune baseline documentée dans `docs/BACKUPS.md` supprimée** ; backup courant `labuse-post-nogo-trois-bassins-sainte-rose-20260623-164812.dump` **conservé**, sidecars des baselines conservés.
- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-saint-andre-agorah-20260623-175552.dump` (≈ 1,03 Go)
  - **SHA-256** : `e8bc66b5d9782471caa427ab6052e1c4e9dfcef0c919c86d2fb9fe0ac1c75383`
  - intégrité revérifiée (`sha256sum -c`) ✓
- **Dry-run** : OK (plan validé, aucune écriture en base).
- **Phrase de confirmation** : `IMPORT_SAINT_ANDRE_COMPLET`.
- **Run réel** `re_couches_re_cascade` → **code de sortie 0**.

## Repli AGORAH (source du zonage PLU)

Le Géoportail de l'Urbanisme ne sert **aucune** zone propre `DU_97409` (vérifié API Carto + WFS). Le repli AGORAH s'est déclenché **automatiquement** (commune allowlistée **et** 0 zone propre au GPU) :

- **Fallback déclenché** : oui (`should_use_agorah_fallback("97409", 0) → True`)
- **Zones AGORAH insérées** : **142**
- **`attrs.source`** : `AGORAH_BASE_PERMANENTE_PLU_REUNION` (Base permanente des PLU de La Réunion — Open Data Réunion / OpenDataSoft)
- **idurba** : `97409_20190228`
- **datappro** : `2019-02-28`
- **Partition** : `DU_97409`
- **Typezones** : **U=41 / AU=40 / A=40 / N=21** (Σ = 142)
- **Couverture zonage PLU propre `DU_97409`** : **100 %** (142 zones propres, toutes issues d'AGORAH)

> En base, `plu_gpu_zone` = **419** au total = 142 zones propres `DU_97409` (AGORAH) + 277 zones limitrophes (autres partitions) ramenées par la requête bbox du GPU ; **seules les 142 propres** portent le zonage de Saint-André.

## État avant → après

- Parcelles : 22600 → **22600**
- Sections : **33**
- Bâti (couche) : 0 → **50910**
- Évaluées : **22600 / 22600** (100 %)

## Couches

- batiment : 50910
- voirie : 13264 (non tronquée — bien au-delà du plafond de 5000)
- pente : 3819
- plu_gpu_zone : 419 (dont 142 propres `DU_97409` via AGORAH)
- ppr : 4
- sar : 121
- ravine : 353
- plu_gpu_prescription : 308
- osm_faux_positif : 188
- dvf (mutations) : 934
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **54**
- À creuser : **6851**
- Écartée : **548**
- Faux positif probable : **15147**
- Taux d'opportunité : **0.2 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 12
- **Comparaison** : profil **comparable au gold Saint-Denis (≈ 0,2 %)** — ce n'est **pas** un pattern quasi-nul façon La Plaine-des-Palmistes / Les Trois-Bassins / Sainte-Rose (où les opportunités s'effondrent sous l'effet zonage A/N + bâti R1). Les 54 opportunités sont réelles et exploitables.

## Temps d'exécution

- parcelles : 24s
- couches : 193s
- cascade : 3419s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (22600) — 22600 (min 22600)
- ✓ OK   sections présentes — 33
- ✓ OK  [critique] 0 doublon IDU — 22600/22600
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 22600/22600
- ✓ OK  [critique] bâti présent (> 0) — 50910
- ✓ OK  [critique] zonage PLU présent — 419
- ✓ OK  [critique] pente présente — 3819
- ✓ OK  [critique] voirie présente — 13264
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 121 features
- ✓ OK   ravine : complet — 353 features
- ✓ OK   plu_gpu_prescription : complet — 308 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 22600/22600
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.2 % (54 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion

**SUCCÈS — GO pour l'étape gold séparée.**

Le présent commit est **docs-only** : il **ne marque pas** Saint-André gold. `config/communes_gold_standard.yaml` et les tests restent **inchangés** ; Saint-André demeure `partiel_non_evalue`. Le passage gold 15→16 fera l'objet d'une **étape validée distincte**.
