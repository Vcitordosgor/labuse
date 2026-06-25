# Saint-Leu — run **PROVISOIRE** via AGORAH 2007 (**NON-gold**)

> ⚠️ **DISCLAIMER (obligatoire)** : *« Analyse provisoire basée sur le PLU opposable 2007 disponible via AGORAH.
> Le zonage est en révision et devra être recalculé dès publication d'un PLU révisé exploitable. »*

> **Run PROVISOIRE** de Saint-Leu (97413) : la commune (22 959 parcelles, **3ᵉ marché DVF du département**) était
> présente mais **non analysée** (PLU absent du GPU). Elle est débloquée via le **repli AGORAH PLU 2007**
> (`97413_20070226`, couverture **99,60 %**). **Saint-Leu RESTE NON-gold** : le PLU 2007 est en révision (avis
> Région défavorable, approbation 2ᵉ sem. 2026 non stabilisée) → résultats **provisoires**, à recalculer.

## Verdict : 🟡 **SUCCÈS technique provisoire** (exit 0, 22/22 post-checks verts) — débloquée pour analyse, **NON marquée gold**

## Contexte & backup

| Élément | Valeur |
|---|---|
| `main` (code) | **`d0f010b`** (repli AGORAH 97413 autorisé — provisoire) |
| Backup pré-commune | `/var/backups/labuse/labuse-pre-saint-leu-agorah-20260625-185202.dump` (1.1 Go) |
| SHA-256 | `35173977b05560432451424f7163235e4d9ec6a0ff1d594be34f6910330e9d2c` (sidecar OK, `sha256sum -c` OK, 190 TOC, 6/6 tables critiques) |
| Commune / INSEE | **Saint-Leu / 97413** (vague 2, loi Littoral) |
| Runner | `import_commune_gold_standard.py … --execute --confirm IMPORT_SAINT_LEU_COMPLET --backup …` |
| Exit | **0 (EXIT_OK)** · B 32 s · D 249 s (aucune couche en erreur) · F cascade 2 037 s |

## Source de zonage (PROVISOIRE)

- **GPU `DU_97413` : ABSENT** au moment du run (`document` 0, `zone-urba` 0 ; `municipality is_rnu=false`, `is_coastline=true`).
- **Repli AGORAH déclenché** (`should_use_agorah_fallback("97413", 0) = True`) → **368 zones AGORAH insérées**,
  `idurba 97413_20070226`, datappro **2007-02-26**, source `AGORAH_BASE_PERMANENTE_PLU_REUNION`.
- **Couverture parcellaire AGORAH propre `97413` = 99,60 %** (663 zones plu_gpu_zone au total = 368 AGORAH propres
  + 295 bleed voisins GPU 97401/97414/97423/97404/97424 — sans incidence, couverture propre = couverture totale).
- **PLU en révision, non stabilisé** : projet arrêté 11/12/2025, avis Région défavorable 27/02/2026 (SAR), enquête
  publique reportée, approbation visée 2ᵉ sem. 2026 ; géométrie révisée non publiée en SIG. **→ résultats provisoires.**

## Couches : avant → après

| Couche | Avant | Après |
|---|---:|---:|
| **bâti** | 0 | **35 339** |
| **pente** | 0 | **6 582** |
| **voirie** | 5 000 (plafonné) | **11 761** (déplafonnée) |
| PPR | 0 | **4** |
| SAR | 0 | **128** |
| prescriptions | 0 | **274** |
| ravines | 0 | **477** |
| OSM faux positifs | 0 | **174** |
| plu_gpu_zone | 295 (bleed only) | **663** (dont **368 AGORAH propres**) |
| **géométrie invalide** | 1 | **0** (réparée `ST_MakeValid`) |
| **DVF** | 2 470 | **1 307** ✅ (homogénéisé geo-dvf Etalab 2021-2025 — **amélioration de qualité, pas une perte** ; cf. § DVF) |

## DVF — homogénéisation (pas une régression)

Le compteur DVF de Saint-Leu passe de **2 470 → 1 307** : ce n'est **pas une perte de données**, mais une
**migration de l'ancien flux ODS Région vers le flux canonique geo-dvf Etalab (data.gouv) 2021-2025**,
**résidentiel uniquement** (Maison 714 + Appartement 593), **dédoublonné par vraie mutation** (`id_mutation`,
fin du surcompte multi-lots). L'ancien 2 470 était du **surcompte parcelle-level périmé** (ODS 2014-2021,
`mutation_id = parcelle`, non-résidentiel inclus). Le nouveau 1 307 (2021:298 · 2022:387 · 2023:245 ·
2024:191 · 2025:186) est **homogène avec les 24 communes** (toutes geo-dvf 2021-2025 ; ex. Saint-Louis
1 161 / 29 241 parc.). → **amélioration de qualité, €/m² correct, aucune correction nécessaire.**

## Verdicts cascade (latest) — PROVISOIRES

| Verdict | n |
|---|---:|
| **Opportunité** | **976** |
| À creuser | 7 455 |
| Écartée | 998 |
| Faux positif probable | 13 530 |
| **Σ** | **22 959** (= évaluées ✓) |

- **Taux d'opportunité : 4,3 %** (dans le gate QA ≤ 5 %, élevé mais non explosif — cf. La Possession 4,6 %, Sainte-Marie 4,5 %).
- **Score** : max **88** · médiane globale **45,0** · médiane des opportunités **68,0** (> seuil 65) · micro-opportunités (251–500 m²) **262**.
- **Comparaison** (sans conclure gold) : Saint-Leu **4,3 %** vs Saint-André **0,2 %** / Saint-Denis **0,2 %** — Saint-Leu
  est bien plus « ouverte » : grande commune côtière, marché actif, **zonage 2007 (plus permissif que le futur PLU
  probablement)**. Ces 976 opportunités sont **PROVISOIRES** : la révision reclassera le zonage → recalcul obligatoire.

## Contrôles d'intégrité

- ✅ **22 post-checks du script verts** (parcelles, 0 doublon, 0 géom invalide, 100 % geom_2975, 100 % évaluées,
  bâti > 0, pente > 0, voirie, couverture zonage **99,6 %**, 0 duplication, ppr/sar/ravine/prescriptions, index GIST,
  verdicts cohérents, taux QA ≤ 5 %, conservation pipeline/feedback/alertes).
- ✅ **Conservation** : DB 431 663 / 24 inchangée ; **23 autres communes strictement conservées** ; seul INSEE **97413** modifié.
- ✅ **Gold inchangé = 17** : `config/communes_gold_standard.yaml` **non modifié** — **Saint-Leu reste `partiel_non_evalue` / non-gold / non fiable**.
- ✅ Aucun rollback · aucun passage gold · scoring/seuil 65/PPR inchangés · Étape A non généralisée · `parcel_evaluations`
  stale non nettoyées · aucun commit · aucun merge.

## Risques

1. **Volatilité du zonage 2007** : la révision (avis Région défavorable, +12,4 ha U visés) reclassera les zones →
   les **976 opportunités sont provisoires** et devront être **recalculées** dès le PLU révisé exploitable.
2. **DVF homogénéisé (2 470 → 1 307)** : migration de l'ancien flux ODS Région → flux canonique geo-dvf Etalab
   2021-2025 (résidentiel, dédoublonné par vraie mutation). **Ni un risque ni une perte** — amélioration de qualité
   et alignement avec les 24 communes (cf. § DVF). Vérifié read-only.
3. **Affichage client obligatoirement assorti du disclaimer** (zonage 2007 en révision).

## Recommandation

- **Garder Saint-Leu NON-gold** (déjà le cas — config non touchée). Ne PAS la passer gold tant que le PLU révisé
  n'est pas approuvé + publié en géométrie exploitable.
- **Produit** : montrer Saint-Leu comme **« analysée (provisoire — PLU 2007 en révision) »** avec le disclaimer ; ses
  976 opportunités sont des **leads à instruire, provisoires**.
- **Veille** : dès publication du PLU révisé (GPU `DU_97413` ou AGORAH refresh `idurba ≥ 2026`) → re-`re_couches_re_cascade`
  Saint-Leu (re-fetch zonage + re-cascade), puis re-décider gold.
- **DVF** : homogénéisé (geo-dvf Etalab 2021-2025) — **rien à corriger** (amélioration de qualité, alignement 24 communes ; cf. § DVF).

---

### Provenance
- Mutation autorisée unique : `re_couches_re_cascade` Saint-Leu (upsert cadastre id-préservant + couches scopées + repli AGORAH 2007 + cascade), backup validé avant écriture.
- Mesures Phase 5 : `SELECT` lecture seule sur `parcels`, `parcel_evaluations` (latest), `spatial_layers`, `dvf_mutations`.
- Aucune autre commune touchée, aucun rollback, aucun passage gold, aucun commit, aucun merge.
