# M26-B — Constat : charges supportables incohérentes fiche ↔ copilote (sujet BACK)

**Origine** : revue Point B (Vic). **Verdict** : pas de faute d'unité côté front ; payload
fidèle à son moteur ; mais **une seule méthode (`compute_bilan`) avec deux jeux
d'hypothèses**, dont l'un charge une configuration versionnée **périmée**. Un même
utilisateur peut lire 216 k€ sur la fiche et 449 k€ dans la note Copilote pour la même
parcelle. Aucune correction au M26-B (front seul) — **mandat back dédié, prioritaire**.

## 1 · Vérifications faites (parcelle #01 du run `93c22e53`, IDU 97415000CX1395)

| Grandeur | Payload copilote | Contre-épreuve directe | Verdict |
|---|---|---|---|
| `prix_probable_eur` | 204 288 € | `dvf_secteur_medianes` secteur `97415000CX`, terrain, 14 ventes : 336 €/m² × 608 m² | **exact à l'euro** |
| `surface_m2` / `sdp_m2` / SHAB | 608 / 467 / 368 | fiche `/modules/faisabilite/…` : identiques | cohérent |
| `charge_fonciere_eur` | **449 339 €** | fiche (même `compute_bilan`, même SHAB) : **216 579 €** | **divergent ×2,07** |

Reproduction exacte : `compute_bilan(368, 608, sector_price(…), hyp)` → **216 579** avec
`Hypotheses()`, **449 339** avec `Hypotheses.charger()`.

## 2 · Quel appel est le bon — instruction sur pièces

Présomption de la revue : « la config versionnée prime, la fiche est en tort ». **Sur
pièces, c'est l'inverse — la config versionnée est PÉRIMÉE** :

- **10/06/2026** (`e3191f2`, création du bilan promoteur) : le YAML
  `config/plu_saint_paul.yaml → hypotheses_faisabilite` grave
  `cout_construction_m2_bas/haut = 1800/2200`, commentés « au m² habitable ».
- **12/06/2026** (`2c25746`, **audit O2** « bilan prudent Réunion ») : les défauts du
  code passent à `2300/2800` **au m² de PLANCHER** + `coef_plancher_habitable = 1.15`,
  avec ce commentaire : « les 1 800-2 200 €/m² métropole sous-estimaient le coût et
  SUR-estimaient donc la charge foncière ». **Le YAML n'a jamais été réaligné.**
- Conséquence double pour `charger()` : valeurs d'avant-audit **et** contresens d'unité
  (des €/m² *habitable* de l'ancien schéma injectés dans des champs désormais lus en
  €/m² *plancher*, le coef 1.15 restant appliqué par ailleurs).

Donc : ni « la fiche a raison » ni « charger() a raison » — **la doctrine (config
versionnée éditable) est la bonne, mais son contenu doit être réaligné sur l'audit O2**,
puis TOUS les consommateurs basculés sur `charger()`. Les 3 YAML communaux portent la
même section à corriger (`plu_saint_paul/denis/pierre.yaml`).

## 3 · Inventaire des consommateurs de `compute_bilan`

| Consommateur | Appel | Hypothèses | `bilan_params` | Exposition |
|---|---|---|---|---|
| Fiche — GET `/faisabilite/{idu}` (bloc bilan) | `api/modules.py:810` | `Hypotheses()` (défauts audités) | non | écran |
| Calculette — POST `/faisabilite/{idu}/charge` | `api/modules.py:937` | `Hypotheses()` | oui (saisie utilisateur + défauts) | écran |
| Explication IA — `/faisabilite/{idu}/explain` | `api/modules.py:937` (même chemin) | `Hypotheses()` | oui (`bilan_params_defaut()`) | écran |
| Dossier banquier (PDF) | `api/briques_pdf.py:243` | `Hypotheses()` | oui (`bilan_params_defaut()` : 2500 €/m², 21 %) | **PDF export** |
| **Copilote** — moteur `marche_dvf` | `copilote/moteurs.py:385` | **`Hypotheses.charger()`** | non | écran + future note PDF (M26-C) |
| **Cœur faisabilité** — `parcel_faisabilite` | `faisabilite/db.py:368` | **`Hypotheses.charger()`** | oui (secteur, table `bilan_params`) | alimente fiche (capacité) et copilote (faisabilité) |
| Tests (`test_bilan`, `test_lot_d`, `test_pente_exposition`, …) | divers | `Hypotheses()` | fixtures | interne |

Non-consommateurs vérifiés : **score_e** (pipeline batch distinct « bilan-neuf-v2 »,
jamais `compute_bilan` — cf. commentaire `moteurs.py:350`) ; **Argumentaire de
négociation** et **Rapport de potentiel** : aucun appel direct trouvé (ils consomment
les briques ci-dessus — à re-vérifier en tête du mandat back).

Le tableau dit l'ampleur réelle : la ligne de fracture ne passe pas entre « fiche vs
copilote » mais entre **quatre surfaces aux défauts audités** (fiche, calculette,
explication, banquier) et **deux briques au YAML périmé** (copilote, cœur faisabilité) —
ces deux dernières partagent le même écran de fiche via la capacité, donc la fiche
elle-même mélange les deux régimes selon le bloc regardé.

## 4 · Estimation de l'écart sur les chiffres déjà servis

Mesuré sur les 20 restituées du run `93c22e53` (mêmes SHAB/prix, seuls les jeux
d'hypothèses varient) :

- ratio charge `charger()` / défauts audités : **médiane ×2,37** (min ×1,51, max ×41
  sur les charges positives) ;
- **11 parcelles sur 20 changent de verdict de viabilité** : charge > 0 avec le YAML
  périmé, charge ≤ 0 (opération non viable) avec les coûts audités — la surestimation
  n'est pas qu'un facteur d'échelle, elle inverse des conclusions ;
- sens systématique : le YAML périmé **surestime** la charge supportable (coûts de
  construction optimistes d'avant-audit).

Chiffres déjà servis par le canal périmé : les runs Copilote (démos M26-A/M26-B, aucune
diffusion client) et le bilan interne du cœur faisabilité partout où il transparaît. Les
exports Banquier et la calculette, eux, sont sur les défauts audités (+ `bilan_params`).

## 5 · À trancher au mandat back

1. Réaligner `hypotheses_faisabilite` des 3 YAML sur l'audit O2 (valeurs **et** unité
   €/m² plancher), puis basculer les 4 surfaces `Hypotheses()` sur `charger()` — une
   seule vérité, éditable, versionnée.
2. Clarifier la coexistence `charger()` × `bilan_params` (le secteur peut re-piloter le
   coût par la table — qui prime, et l'afficher).
3. Présentation des charges ≤ 0 : le front M26-B affiche désormais « Opération non
   viable — charge nulle ou négative (valeur), même à foncier gratuit » ; le back peut
   porter cette sémantique dans le payload (champ dédié) plutôt qu'un montant nu.

## 6 · Au passage — golden

`qa/golden_check.py` vise par défaut `LABUSE_API_BASE=127.0.0.1:8010` ; rien n'écoute
sur :8010 sur ce poste → 32 « api.\* absent » trompeurs (28/07). Pointé sur l'instance
réelle : **116/116 PASS**. À savoir pour les prochains mandats.
