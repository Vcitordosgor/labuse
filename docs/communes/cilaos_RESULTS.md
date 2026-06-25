# Cilaos — import complet (complétude **24/24 atteinte**, NON gold)

> **Import complet de Cilaos (97424)** — **dernière commune** vers la **complétude 24/24** de la couverture
> Réunion en base. **Ce n'est PAS un passage gold.** Cilaos est un **cirque** (relief fort, cœur de parc
> national, forêt publique, PPR) : importée et **100 % évaluée**, **4 opportunités (0,1 %)** — quasi-nul,
> attendu. Backup pré-commune **obligatoire créé et vérifié avant écriture**. **Aucune autre commune touchée
> (Salazie inchangée), aucun passage gold, aucun commit, aucun merge.**

## Verdict

- **Complétude 24/24 : 🟢 GO** — run techniquement **propre** (exit 0, 22/22 post-checks verts), Cilaos
  présente + enrichie au standard. **La base couvre désormais les 24 communes de La Réunion.**
- **Gold : 🔴 NO-GO** (attendu) — **4 opportunités (0,1 %)**, profil cirque quasi-inconstructible.
  **Cilaos reste NON-gold** (import de complétude), comme Salazie.

## Contexte

| Élément | Valeur |
|---|---|
| `main` (code) | **`7c9f97e`** (inclut l'Étape A PPR PM1 < 10 % déjà mergée — **non re-généralisée** ici) |
| Backup pré-commune | `/var/backups/labuse/labuse-pre-cilaos-20260625-130353.dump` (1.1 Go, 1 119 162 540 octets) |
| SHA-256 | `83bdd2f95ba3be27b6077088891ce29663ce0a00750931c0c63714b78de1148b` |
| Vérif. backup | sidecar `.sha256` · `sha256sum -c` **OK** · `pg_restore --list` **190 TOC** · **6/6 tables critiques** · **re-vérifié par le script avant écriture** |
| Commune / INSEE | **Cilaos / 97424** (cirque, vague 6, risque élevé) |
| Stratégie yaml | `attendre` (différée) → **surclassée par décision de complétude** = `import_complet` |
| État détecté (runtime) | **ABSENT** (0 parcelle) → import complet |
| Runner | `import_commune_gold_standard.py --commune "Cilaos" --insee 97424 --execute --confirm IMPORT_CILAOS_COMPLET --backup …` |
| Exit | **0 (EXIT_OK)** · [B] cadastre 22 s · [D] couches 187 s · [F] cascade 629 s |

## État avant → après

| | Avant | Après |
|---|---|---|
| Parcelles Cilaos | 0 | **6 560** (idu distincts 6 560 — **0 doublon**) |
| Sections | — | **13** |
| Évaluées | 0 | **6 560 / 6 560 (100 %)** |
| Bâti (couche) | 0 | **5 584** |
| **DB globale — parcelles** | 425 103 | **431 663** |
| **DB globale — communes** | 23 | **24 ✅ (complétude totale)** |
| **DB globale — gold** | 16 | **16 (inchangé)** |

## Couches ingérées (17 types — enrichissement maximal)

| Couche | n | | Couche | n |
|---|---|---|---|---|
| batiment | 5 584 | | plu_gpu_prescription | 255 |
| voirie | 2 327 | | osm_faux_positif | 95 |
| pente | 4 080 | | safer | 70 |
| plu_gpu_zone | 232 (couv. **100 %**) | | trait_de_cote | 1 007 |
| ppr | 2 | | water | 150 |
| sar | 31 | | ocs_ge | 86 |
| ravine | 402 | | potentiel_foncier | 31 |
| parc_national | 3 | | foret_publique | 9 |
| ens | 2 | | **abf** | **absent** (non critique) |

- **PLU** : 232 zones, dont **`97424_plu_20240213` = 149 zones (IDURBA dominant, PLU propre de Cilaos)** + 83
  zones limitrophes (emprise : Entre-Deux 32, Saint-Louis 26, Saint-Paul 16, La Possession 4, Saint-Benoît 2,
  Les Avirons / Salazie / Les Trois-Bassins 1 chacune). **Couverture totale 100 %**, **couverture propre 97424
  = 100 %** (chaque parcelle couverte par le PLU de Cilaos). Duplication de couches : **0** · Index GIST : **3/3** · DVF : **128** (2023).

## Verdicts & opportunités (latest / parcelle)

| Verdict | n |
|---|---|
| **Opportunité** | **4** |
| À creuser | 2 074 |
| Écartée | 1 434 |
| Faux positif probable | 3 048 |
| **Σ** | **6 560** (= évaluées ✓) |

→ **Taux d'opportunité 0,1 % (4 opp)** — quasi-nul, **attendu** pour le cirque (cœur de parc national
`parc_national` 3 + forêt publique `foret_publique` 9 + pente sur 4 080 / 6 560). Légèrement au-dessus du 0
de Salazie mais **toujours quasi-inconstructible**. Valeur de l'import = **présence en base** (complétude),
pas le volume d'opportunités.

## Contrôles d'intégrité

- ✅ **22 post-checks du script tous verts** (parcelles ≥ attendu, 0 doublon IDU, 0 géom invalide, 100 % geom_2975,
  100 % évaluées, bâti > 0, zonage ≥ 99 %, 0 duplication couche, index GIST, verdicts cohérents, taux QA ≤ 5 %,
  conservation pipeline/feedback/alertes).
- ✅ **Conservation** : les **23 communes antérieures ont des comptes strictement identiques** ; **Salazie inchangée
  (7 035)**. Seule **Cilaos (+6 560)** ajoutée. Aucune autre commune ré-importée ni ré-évaluée.
- ✅ **Gold inchangé = 16** : `config/communes_gold_standard.yaml` **non modifié** (Cilaos reste `etat: absent`).
- ✅ **Seuil scoring = 65 et tout le scoring inchangés** ; **aucune Étape B** (rouge/bleu) ; **Étape A non re-généralisée**
  (code mergé dans la cascade, mais 2 features PPR périmètre → effet nul ici).
- ✅ **Aucun dedup / rollback / cleanup** ; `parcel_evaluations` d'autres communes intactes (Cilaos sans stale, import unique).
- ✅ **Aucun commit, aucun merge, aucun passage gold.**

## Limites

- **4 opportunités (0,1 %) = comportement correct**, pas un bug : cirque quasi-inconstructible.
- **`abf` absent** : aucun périmètre ABF récupéré (non critique).
- **DVF 128 mutations (2023)** : marché foncier très mince — normal pour un cirque.
- **PLU 232 zones dont 83 limitrophes** (emprise GPU) : sans incidence, couverture propre 97424 = 100 %.

## Décision & suite

- **Cilaos reste NON-gold** (présente + enrichie). **Complétude : 24/24 — objectif de couverture Réunion totale ATTEINT.**
- **Plus aucune commune absente.** La priorité produit « 24 communes présentes en DB et enrichies au maximum »
  est désormais **satisfaite**.
- **Prochaine étape possible (NON exécutée ici)** : **backup stable post-Cilaos / 24 communes** pour figer cet
  état complet — à valider séparément.

---

### Provenance (lecture seule, hors la mutation autorisée)

- **Mutation autorisée et unique** : `import_complet` Cilaos (cadastre + couches scopées `commune='Cilaos'` + cascade),
  backup pré-commune validé **avant** écriture.
- Mesures Phase 5 : `SELECT` sur `parcels`, `parcel_evaluations` (latest), `spatial_layers`, `dvf_mutations`.
- Aucun import d'une autre commune, Salazie non modifiée, aucun passage gold, aucun changement de
  code/config/scoring, aucune Étape B, aucun commit, aucun merge, aucun contact externe.
