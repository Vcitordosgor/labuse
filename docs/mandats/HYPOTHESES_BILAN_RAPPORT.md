# RAPPORT — Mandat hypothèses bilan : une seule vérité pour `compute_bilan`

**Exécuté le 28/07/2026** (branche `fix/hypotheses-bilan`, exécuteur Claude Code, arbitrages
Vic du 28/07 aux trois points d'arrêt). Mandat : `MANDAT_HYPOTHESES_BILAN.md` ; constat
d'origine : `M26B_CONSTAT_CHARGES.md`.

## 1 · Ce qui a été prouvé (mesure d'impact, points A-B)

- Le YAML versionné portait 1800–2200 €/m² « habitable » (avant-audit, `e3191f2` 10/06) ; les
  défauts codés portent l'audit O2 (2300–2800 €/m² de **plancher** + coef 1,15, `2c25746`
  12/06). Contre-épreuve à l'euro (CX1395) : 216 579 € vs 449 339 €.
- **Troisième jeu découvert** : override global `bilan_params.cout_construction_m2_sdp = 2100`,
  injecté le 14/06 (`d94ff9b`) — estimation ancrée sur la fourchette YAML **périmée**, 2 jours
  après l'audit, sans le citer, marquée « ★ à affiner en priorité » (RAPPORT_CALIBRATION_WEB.md)
  et jamais confirmée (gabarit `bilan_calibration_vic.csv` resté vide). PAS une décision produit.
- **Les tiers servis ne dépendent d'aucun champ de coût** (chaîne `sdp_residuelle` = capacité
  seule ; run épinglé au label `q_v7_defisc` ; `residuel_socle` = barème SDP). **score_e**
  (77 718 lignes, 21/07) portait déjà ses propres constantes au niveau audité (2550/1,15/0,79).

## 2 · Le chiffre commercial (mesuré, échantillons seedés `m26-hyp`)

Verdict « viable » = charge foncière médiane servie > 0. Aucune bascule inverse ; le sens est
systématique (le périmé/2100 SURestimait la charge).

**Chemin copilote** (YAML périmé → audité, ratio médian ×1,96, max ×41) :

| Échantillon | Calculables | Viables avant | Viables après | Basculent V→NV |
|---|---|---|---|---|
| Retenues run `instruire` 93c22e53 (Saint-Paul, 500/2947 seedé) | 500 | 368 | 176 | **192 (52 % des viables)** |
| Parc stratifié commune×tier (3 communes calibrées) | 559 | 220 | 100 | **120** |
| — dont Saint-Paul / Saint-Denis / Saint-Pierre | 198/182/179 | 154/31/35 | 89/**0**/11 | 65/31/24 |

**Chemin cœur** (`parcel_faisabilite`, override 2100 → fourchette auditée, ratio médian ×2,00) :
retenues 319 → 154 viables (165/500 basculent) ; parc 68/559 basculent.

**Le zéro de Saint-Denis est une information de MARCHÉ, pas un défaut du modèle** (consigne
Vic) : aux coûts réels, les prix de sortie DVF de l'existant dionysien ne supportent plus
d'opération neuve sur l'échantillon — le cœur, assis sur le prix neuf calibré (4 900 €/m²), y
conserve 114/182 viables. **Nuance d'échantillon** : le volet « retenues » ne couvre que
Saint-Paul (aucun run `instruire` n'existait pour Saint-Denis/Saint-Pierre) ; le parc stratifié
couvre les trois communes.

## 3 · Ce qui a été appliqué (séquence Vic, ordre strict)

1. **Golden avant** : 116/116 PASS + tiers relevés (120/1031/3587/72980/353945).
2. **YAML ×3 réalignés** : 2300/2800 plancher + `coef_plancher_habitable: 1.15` explicite +
   traçabilité datée (décision, audit, commit fautif, constat).
3. **Override 2100 supprimé** (base) + retiré du socle de seed (`bilan_calibration.py` — sinon
   le boot le ré-injectait) + **migration de boot ciblée** dans `ensure_bilan_params`
   (models.py : DELETE du 2100 système uniquement — provenance « estimee », valeur exacte —
   pour que toute base déjà déployée soit purgée ; un override saisi par Vic survivrait).
   Défaut registre `cout_construction_m2_sdp` → **0 = repli fourchette YAML** dans
   `compute_bilan`.
4. **Dérivations depuis la source unique** : défauts calculette 2550/21 (plus de 2500 gravé —
   y compris le `Field(2500)` du body API attrapé par le verrou) ; score_e dérive
   2550/1,15/0,79 de `charger()` (numériquement identique à `bilan-neuf-v2` — aucun recalcul
   du snapshot requis, le prochain batch trace la version dérivée).
   **Bascule §2** : fiche, calculette, explication, banquier passent sur `Hypotheses.charger()` —
   valeur-neutre post-réalignement (seul `pct_lls` 0→30, sans effet hors mixité calibrée).
5. **Test-verrous** (`tests/test_hypotheses_source_unique.py`, 5 tests) : YAML ≡ audit ;
   aucun `Hypotheses()` direct hors engine/tests ; aucune constante de coût > 100 hors source
   (AST — a immédiatement attrapé le `Field(2500)`) ; calculette et score_e dérivés.
6. **Golden après : 116/116 PASS** + **tiers au bit près : identiques**. Honnêteté de la
   preuve : la référence golden ne couvre AUCUN champ bilan/charge — son PASS garantit le
   périmètre « ne doit pas bouger » (cascade, tiers, zonages, ancres), pas les charges.
7. **Mesure de confirmation : CONFORME AU EURO** — le live post-application reproduit la
   prédiction sur 1026 parcelles copilote (0 écart, ×1,96) et 1026 cœur (0 écart, ×2,00).
   La fiche servie (HTTP) porte 216 579 € et « 2300–2800 €/m² de surface de plancher ».

## 4 · Préséance gravée (documentée dans `bilan_params.py`)

1. **Source unique** = fourchette `hypotheses_faisabilite` du YAML PLU (auditée O2) ; le défaut
   registre 0 signifie « repli fourchette YAML » ; 2. un override **sectoriel justifié et
   sourcé** (table) peut re-piloter le coût ; 3. **jamais de défaut codé silencieux** (verrou).
L'invariant calculette = dossier banquier (`test_bilan_calculette_vs_dossier`) tient.

## 5 · Verrou anti-« provisoire devenu permanent » (ajout Vic n°1)

- `resolve()` : une valeur de provenance « estimee » **reste `is_placeholder=true`** (visible
  aux bandeaux) tant qu'elle n'est pas confirmée ; seed et base existante alignés.
- Contrôle : **`labuse bilan-params-perimes --jours N`** (code retour 1 si signalement) — au
  premier run : **10 estimées non confirmées de 37-43 jours** (VRD 90, marge 9 %, honoraires
  12 %, frais financiers 3 %, LLS 2 900, ratio 0,80, bonus vue mer 15 %, majorations
  pente/ANC, prix neuf Le Guillaume). Le scénario 2100 n'était pas isolé.

## 6 · L'étiquette ne change pas (ajout Vic n°2)

La charge foncière reste **Estimé** partout : steps `prov="estimee"/"derive"` inchangés,
libellé moteur « hypothèse coût (prudente, Réunion) », note YAML explicite. 2300–2800 est un
chiffre d'**audit**, pas un chiffre sourcé : le passage à Sourcé exige un coût de promoteur
réunionnais réel. **Action qui revient à Vic** : remplir `config/bilan_calibration_vic.csv`
(question n°1 : « ton coût de construction au m² SDP, collectif R+3/R+4, hors foncier ? »),
puis `labuse bilan-calibrate`.

## 7 · Documenté, non corrigé (mandats séparés) + divers

- **`_doc()` sans commune** (`plu_rules.py:85`) : `Hypotheses.charger()` lit TOUJOURS
  `plu_saint_paul.yaml` — les sections `hypotheses_faisabilite` de Saint-Denis/Saint-Pierre
  sont documentaires (leurs YAML le disent). Corriger ferait varier les hypothèses par commune
  → nouvel impact à mesurer → **mandat séparé** (décision Vic 28/07). Les 3 YAML sont réalignés
  à l'identique pour que la correction future soit un no-op sur les coûts.
- Écart préexistant hors mandat : `test_potentiel.py::test_o12_reste_masque` échoue AVANT
  comme APRÈS ces changements (séquelle de la clôture O12 « EXPOSE=True » du 28/07) — signalé,
  non touché.
- Chiffres déjà servis par les canaux corrigés : runs copilote de démo M26-A/B (aucune
  diffusion client, cf. constat §4) et bloc bilan du cœur sur la fiche.

## 8 · Artefacts

Mesures : `/tmp/mesure_hypotheses_bilan.py` + `/tmp/mesure_coeur_2100.py` +
`/tmp/confirme_ratios.py` (lecture seule, seed `m26-hyp`), résultats JSON dans `/tmp`.
Baselines : golden avant/après 116/116 ; `/tmp/tiers_avant.txt` = `/tmp/tiers_apres.txt`.
