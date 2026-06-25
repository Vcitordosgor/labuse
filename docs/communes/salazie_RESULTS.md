# Salazie — import complet (complétude 24/24, **NON gold**)

> **Import complet de Salazie (97421)** réalisé pour la **complétude 24/24** de la couverture Réunion en base
> — **ce n'est PAS un passage gold**. Salazie est un **cirque** (cœur de parc national + forêt publique,
> relief extrême) : **0 opportunité attendue et confirmée**. Backup pré-commune **obligatoire créé et vérifié
> avant toute écriture**. **Aucune autre commune touchée, aucun passage gold, aucun commit, aucun merge.**

## Verdict : 🟢 **SUCCÈS technique** (exit 0, 22/22 post-checks verts) — Salazie **présente + enrichie au standard**, **délibérément NON marquée gold**

Import propre et conservateur : 7 035 parcelles importées et 100 % évaluées, toutes les couches critiques
présentes, **0 opportunité** (cohérent avec un cirque). La complétude passe à **23/24** (reste **Cilaos**).
Le rapport auto-généré conclut « peut être marquée gold » (message générique `EXIT_OK`) : **décision produit =
on ne marque PAS gold** ici — l'objectif est la *présence en base*, pas l'optimisation.

## Contexte

| Élément | Valeur |
|---|---|
| `main` (code) | **`a0ab887`** (inclut l'Étape A PPR PM1 < 10 % déjà mergée — **non re-généralisée** ici) |
| Backup pré-commune | `/var/backups/labuse/labuse-pre-salazie-20260625-114234.dump` (1 020 Mo) |
| SHA-256 | `682e06f40ca547b95930e93f01c9868b6ddd8fb40ba83e3cded4ead9405866fa` |
| Vérif. backup | sidecar `.sha256` · `sha256sum -c` **OK** · `pg_restore --list` **190 TOC** · **6/6 tables critiques** · **re-vérifié par le script lui-même avant écriture** (`backup OK + checksum vérifié`) |
| Commune / INSEE | **Salazie / 97421** (cirque, vague 6, risque élevé) |
| Stratégie yaml | `attendre` (différée) → **surclassée par décision de complétude** = `import_complet` |
| État détecté (runtime) | **ABSENT** (0 parcelle) → import complet |
| Runner | `import_commune_gold_standard.py --commune "Salazie" --insee 97421 --execute --confirm IMPORT_SALAZIE_COMPLET --backup …` |
| Exit | **0 (EXIT_OK)** · [B] cadastre 33 s · [D] couches 240 s · [F] cascade 1 209 s |

## État avant → après

| | Avant | Après |
|---|---|---|
| Parcelles Salazie | 0 | **7 035** (idu distincts 7 035 — **0 doublon**) |
| Sections | — | **32** |
| Évaluées | 0 | **7 035 / 7 035 (100 %)** |
| Bâti (couche) | 0 | **7 410** |
| **DB globale — parcelles** | 418 068 | **425 103** |
| **DB globale — communes** | 22 | **23** |
| **DB globale — gold** | 16 | **16 (inchangé)** |

## Couches ingérées (17 types — enrichissement maximal)

| Couche | n | | Couche | n |
|---|---|---|---|---|
| batiment | 7 410 | | plu_gpu_prescription | 879 |
| voirie | 2 736 | | osm_faux_positif | 74 |
| pente | 5 986 | | safer | 774 |
| plu_gpu_zone | 336 (couv. **100 %**) | | trait_de_cote | 1 007 |
| ppr | 2 | | water | 173 |
| sar | 57 | | ocs_ge | 59 |
| ravine | 629 | | potentiel_foncier | 57 |
| parc_national | 3 | | foret_publique | 13 |
| ens | 4 | | **abf** | **absent** (non critique) |

- Couverture zonage PLU : **100,0 %** · Duplication de couches : **0** · Index GIST : **3/3** · DVF : **109** (2023).

## Verdicts & opportunités (latest / parcelle)

| Verdict | n |
|---|---|
| **Opportunité** | **0** |
| À creuser | 836 |
| Écartée | 761 |
| Faux positif probable | 5 438 |
| **Σ** | **7 035** (= évaluées ✓) |

→ **Taux d'opportunité 0,0 %** — **attendu et correct** pour le cirque : cœur de parc national (`parc_national` 3),
forêt publique (`foret_publique` 13) et pente sur **5 986 / 7 035** parcelles → quasi-inconstructibilité.
**Confirme la prévision du pré-vol 24/24.** Salazie pèsera ≈ 0 lead commercial — sa valeur ici est la
**présence en base** (complétude), pas le volume d'opportunités.

## Contrôles d'intégrité

- ✅ **22 post-checks du script tous verts** (parcelles ≥ attendu, 0 doublon IDU, 0 géom invalide, 100 % geom_2975,
  100 % évaluées, bâti > 0, zonage ≥ 99 %, 0 duplication couche, index GIST, verdicts cohérents, taux QA ≤ 5 %,
  pipeline/feedback/alertes conservés).
- ✅ **Conservation** : les **22 communes d'origine ont des comptes de parcelles strictement identiques** avant/après ;
  seule **Salazie (+7 035)** ajoutée. Aucune autre commune ré-importée ni ré-évaluée.
- ✅ **Gold inchangé = 16** : `config/communes_gold_standard.yaml` **non modifié** (Salazie reste `etat: absent`).
- ✅ **Seuil scoring = 65 et tout le scoring inchangés** ; **aucune Étape B** (rouge/bleu) ; **Étape A non re-généralisée**
  (le code mergé tourne dans la cascade, mais 2 features PPR périmètre + 0 opportunité → **effet nul** ici).
- ✅ **Cilaos NON touchée** ; aucun dedup / rollback / cleanup ; `parcel_evaluations` d'autres communes intactes
  (Salazie n'en avait aucune avant — données fraîches, rien d'empilé).
- ✅ **Aucun commit, aucun merge, aucun passage gold.**

## Limites

- **0 opportunité = comportement correct**, pas un bug : cirque quasi-inconstructible. Ne pas interpréter comme un échec.
- **`abf` absent** : aucun périmètre ABF récupéré pour Salazie (non critique — l'absence n'est pas bloquante).
- **DVF 109 mutations (2023)** : marché foncier très mince — normal pour un cirque.
- **Mesure « opportunité » ≠ valeur foncière** : ici l'enjeu est la complétude de couverture, pas la génération de leads.

## Décision & suite

- **Salazie reste NON-gold** (présente + enrichie au standard). **Complétude : 23/24.**
- **Reste un seul absent : Cilaos (97424)** — dernier cirque — **sur décision séparée** (non lancé ici).
- **Backup post-commune** (horodaté + sha256) **recommandé** pour figer ce nouvel état 23/24 — **non réalisé dans cette
  mission** (hors périmètre), à valider séparément.

---

### Provenance (lecture seule, hors la mutation autorisée)

- **Mutation autorisée et unique** : `import_complet` Salazie (cadastre + couches scopées `commune='Salazie'` + cascade),
  backup pré-commune validé **avant** écriture.
- Mesures Phase 5 : `SELECT` sur `parcels`, `parcel_evaluations` (latest), `spatial_layers`, `dvf_mutations`.
- Aucun import d'une autre commune, aucune couche d'une autre commune modifiée, aucun passage gold, aucun changement de
  code/config/scoring, aucune Étape B, aucun commit, aucun merge, aucun contact externe.
