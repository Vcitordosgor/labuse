# EXPORTS-FIX-3 — COMPTE-RENDU

**Un seul verdict de constructibilité, lu par tous les documents.**

- Worktree `~/Desktop/labuse-exports`, branche `fix/exports-3` (base `907e03987`), ports 7410 / 10210.
- Point de départ : `~/Desktop/exports-audit-3/DIAGNOSTIC.md` + `ECARTS.md`.
- Pas de merge · DA existante · un commit par lot · prod et run servi NON touchés · aucun run île.
- Preuves régénérées : `~/Desktop/exports-audit-4/` (+ tableau avant/après `AVANT-APRES.md`).

Commits : `LOT 1` `e1c467efb` · `LOT 2` `8d5cc862d` · `LOT 2 (suite)` `ce2093704` · `LOT 3` `c2e9f369c`.

---

## LOT 1 — Le moteur ne fabrique plus de constructible — **FAIT**

**Cause mesurée.** `_sous_zone_constructible` (`faisabilite/db.py`) accrochait N'IMPORTE quelle portion
U/AU touchant une parcelle dont la zone dominante est A/N, et rendait TOUTE la parcelle constructible,
sans la clipper. 97408000BI0351 (100 % N) touche un éclat « UB » de **0,09 m²** → `f.constructible=True`
→ 24 437 m² de plancher. Les exemples de l'audit confirment le motif : BT0053 (A, 14,5 ha) 16 m² d'U/AU,
HN0194 (A, 18 ha) 2 m², DN0096 (N, 22 ha) 14 m².

**Correctif à la racine (db.py).** Garde d'aire réelle au point d'appel DB-aware `parcel_faisabilite` :
on mesure la surface U/AU RÉELLE (intersection géométrique, famille lue par `labuse_zone_famille(subtype)`
— la source unique du code : tient sur `1AU`/`2AU` et les libellés littéraux de Bras-Panon / Saint-Pierre,
jamais le préfixe du nom). La sous-zone n'ouvre la constructibilité que si la portion est une **vraie
surface : ≥ 50 m² ET ≥ 1 %** (classe « au-delà » du mandat). En deçà (nulle / infime) la parcelle reste
sa zone dominante non constructible — **aucune capacité sans surface réelle en U/AU** ; une parcelle
réellement à cheval garde la capacité de sa **seule** partie constructible (assiette déjà clippée).

Garde-fou complémentaire : si la zone dominante A/N n'est pas calibrée au PLU (`resolve_zone → None`) et
que l'éclat U/AU est écarté, on sert un verdict ferme « zone non constructible »
(`engine.faisabilite_zone_non_constructible`), jamais `None` (qui dirait « hors PLU ») ni la capacité
fantôme.

**Mesure île (calcul en direct), 3 classes selon la surface réelle en U/AU** — seam
`LABUSE_UAU_PHANTOM_GATE` (avant = 0 / après = 1) :

| classe | parcelles A/N (SQL, île) | capacité AVANT | capacité APRÈS |
|---|---|---|---|
| **nulle** (U/AU = 0) | 89 623 | 0 (aucune sous-zone à accrocher) | 0 |
| **infime** (< 50 m² OU < 1 %) | 10 865 | 91 / 120 constructibles (échantillon) | **0 / 120** |
| **au-delà** (≥ 50 m² ET ≥ 1 %) | 10 136 | 108 / 120 | 108 / 120 (inchangé) |

→ **zéro capacité dans la classe « nulle »** (et désormais « infime »), capacité des parcelles
réellement à cheval **préservée**.

**Tests** (`tests/test_exports_fix_3.py`) : purs (`_uau_portion_reelle`, seuils) + réels (marker `reel`,
base locale `labuse`) — BI0351 + les 3 exemples → non constructibles, SDP nulle ; `97416000ID0331`
(dominante N, ~60 % de vraie U/AU) garde sa capacité sur la portion. Témoin EXIGU-FIX `97403000AL0258`
repointé (il est désormais correctement lu « zone naturelle non constructible », son doute venait du
fantôme) ; témoin « à vérifier » déplacé sur `97415000BN1169` (ambiguïté géométrique réelle).

---

## LOT 2 — Un seul verdict, partout — **FAIT**

**Point unique + ordre des motifs.** `faisabilite.potentiel_batir` est la source unique du verdict +
motif, lue par la fiche, le Dossier, le Gabarit, l'Étude et le Copilote. Ordre imposé appliqué dans
`_assemble` et `exports/verdicts.verdict_potentiel` : **zone non constructible → zone rouge du PPR → le
reste** ; « terrain trop étroit » ne passe jamais devant une raison de zone. BI0351 (run servi
cause=terrain_exigu) disait « terrain trop exigu » ; il dit désormais « **zone non constructible —
naturelle** » à la fiche, au Dossier §3, au Gabarit et à l'Étude.

**Quand le verdict est « non constructible » :**
- **Pré-dossier PC** (`api/pre_dossier.pre_dossier_zip`) : **refusé** (HTTP 422, motif), **aucun ZIP,
  aucun CERFA**. BI0351 régénéré = 422 `non_constructible` (corrige a/f).
- **Comparatif** (`exports/blocs/comparatif` + `app._compare_row`) : ligne « Constructibilité → Non
  constructible — <motif> », et **aucun** plancher, hauteur, bilan ni charge foncière dans sa colonne.
- **Dossier / Gabarit / Faisabilité / Analyse** : le motif est celui de la fiche ; **rien** sous « ce
  qu'il reste à bâtir » (en-tête de groupe masqué sur une parcelle non constructible — `LOT 2 (suite)`,
  `miroir.py`, corrige « d »).

**Garde automatique** : `test_garde_aucun_document_ne_sert_de_capacite_sur_non_constructible` (reel)
parcourt les producteurs sur BI0351 (potentiel_batir, faisabilite_scenario, Comparatif, Pré-dossier) et
échoue si l'un sert capacité, bilan ou CERFA. Vert.

> Note (deux horloges). Le run servi `parcel_residuel` porte toujours cause=terrain_exigu pour BI0351 —
> il n'est pas recalculé (hors mandat). Le verdict SERVI au client est néanmoins « zone non
> constructible » : le motif est recomposé à la lecture (ordre des motifs), sans toucher au run.

---

## LOT 3 — Les fautes de contenu

| | Faute | État | Correctif |
|---|---|---|---|
| a | Analyse « Parcelle bâtie, appartement » sur bâti non mesuré | ✅ | sous-titre « Bâti détecté, à vérifier » ; non mesuré + non constructible → « Pas d'estimation : zone non constructible (N) » (`pige/api`, `pige/estimer3`) |
| b | Zone rouge « 69 % » = part d'un aléa faible | ✅ | la part « Zone rouge » est celle du PPR (31 %, fiche) ; l'aléa faible reste « Faible » (`pige/api._risques_rows`) |
| c | Formule DK0208 irréproductible (470 624 ≠ 237 000) | ✅ | « 113 m² (224 m² au sol × 0,516 × 0,974) × 2 101 €/m² » = 237 000 € (`pige/api`) |
| d | HT0538 « 614 m² » & « capacité nulle » | 🟡 | la SDP résiduelle (614 m²) et le nombre de logements (0) sont deux sorties distinctes ; l'en-tête trompeur « reste à bâtir » est traité (LOT 2 suite), mais la réconciliation explicite des deux chiffres sur HT0538 reste un libellé confort |
| e | Risque présent sur la fiche absent d'un autre document | ⬜ | non traité : l'Analyse n'ouvre pas le canal TRI (inondation extrême) / endiguement (`servitudes.py:427`) |
| f | DPU « rien à signaler » périmètre non vérifié | ✅ | présence testée **par commune** (`phase1.DpuLayer`, `couvre_commune`) |
| f | Taxe d'aménagement — assiette | ✅ | « surface taxable (… distincte de la surface de plancher) » (`api/pre_dossier`) |
| f | PLU « opposable » | ✅ | « opposable à la date des données LABUSE » + caveat mairie toujours porté (`api/app`) |
| g | Comparatif « dépasse le plafond d'emprise » | ✅ | « occupe déjà toute l'emprise constructible (gabarit après reculs) » — le taux est l'occupation du gabarit, pas le CES (`faisabilite/residuel` + miroir TS `frontend/src/lib/format.ts`) |
| g | Bilans sans hypothèses | 🟡 | charge foncière supprimée sur non constructible ; donner hypothèses + dénominateur sur les parcelles constructibles reste confort |

---

## LOT 4 — Preuve — **FAIT**

Tous les documents des trois parcelles régénérés dans `~/Desktop/exports-audit-4/` (même rangement que
`exports-audit-3`), + `AVANT-APRES.md` (tableau avant/après, faute par faute, sur toutes les lignes du
tableau de `DIAGNOSTIC.md`). Faits saillants vérifiés sur les PDF régénérés :

- BI0351 Pré-dossier : **HTTP 422** (était 200, ZIP 1,4 Mo).
- BI0351 Comparatif : « Non constructible — Zone non constructible — naturelle », capacité/charge = « — ».
- BI0351 Dossier §3 : « Terrain non constructible — zone naturelle (zone N) » ; plus de « reste à bâtir ».
- BI0351 Analyse : « Bâti détecté, à vérifier » ; « Pas d'estimation : zone non constructible (N) » ;
  « Zone rouge · 31 % ».
- BI0351 Gabarit / Étude : documents de refus « zone non constructible — naturelle ».
- DK0208 Analyse : « 113 m² (224 m² au sol × 0,516 × 0,974) × 2 101 €/m² = 237 000 € ».
- DK0208 Comparatif : « occupe déjà toute l'emprise constructible (gabarit après reculs) ».

---

## Qualité (hook)

- **Python unitaire** (`not db and not local and not reel and not network`) : **3326 passed, 0 failed**.
- **Front** : `tsc -b` 0 erreur · **vitest 340 passed**.
- **Cohérence** (`scripts/ci/coherence_run.sh`, base locale) : **7 passed** — 1 €/1 m² identique sur les
  12 témoins.
- Deux tests d'un mandat antérieur mis à jour pour refléter le nouveau libellé (plus précis) :
  `test_exports2_lot2` (§3 « zone naturelle (zone N) »), `test_exigu_fix_1` (témoin « à vérifier »
  repointé). Aucun test désactivé.

---

## HORS MANDAT (non touché) — et ce qui ne disparaîtra qu'avec un nouveau classement

**Explicitement hors mandat (non touchés) :** le groupe « confort » du DIAGNOSTIC, le Bilan, l'Apporteur,
le Courrier (non audités), tout recalcul de run.

**Items de contenu non traités (confort / hors cœur des 4 lots), avec leur emplacement pour la suite :**
- `e` Analyse — ouvrir le canal TRI (inondation extrême) + endiguement (`pige/api._risques_rows` ne lit
  que ppr + georisque_alea ; `servitudes.py:427,451`).
- `l` Analyse — aligner le sens de « secteur cadastral » (rayon 500 m) avec la section littérale de la
  fiche (`marche_service.py:580` vs `app.py:5088`).
- `i` Pré-dossier — checklist PCMI8 reflétant l'état réel de la pièce (`pre_dossier.py` liste statique).
- `m`/`g` Comparatif — hypothèses + dénominateur de la charge foncière sur parcelles constructibles.
- `p` Étude de zone « niveau de vie moyen » partout (`zone.py:171`, `etude_zone.py:242`, `rapport.html.j2`).
- `p` Pré-dossier « surface réelle » = contenance cadastrale, pas l'aire du dessin (`pre_dossier.py:662`).
- `d` Dossier — « Logement sous conditions » qualifié « extension d'habitation existante (art. N2.2) ».
- `C2` route legacy `/parcels/{idu}/export?format=md|html` (paliers / jargon) — non exposée par l'UI.
- `b/d` Comparatif — faire remonter zone rouge PPR + EBC dans la colonne « Contraintes relevées » (la
  non-constructibilité y figure déjà via la ligne « Constructibilité »).
- `B1` Dossier/Comparatif/Analyse — une seule emprise bâtie servie (réconcilier le_bien 0 / p_model_bati
  323 / Comparatif 1 %).

**Ce qui ne disparaîtra qu'avec un nouveau classement (bascule d'un run résiduel neuf) :** le champ
`parcel_residuel.cause = terrain_exigu` de BI0351 (et des ~10 865 parcelles « infime ») reste stocké dans
le run servi. Le verdict affiché au client est déjà corrigé À LA LECTURE (ordre des motifs, garde d'aire
réelle en direct). Mais les lecteurs SQL purs du run (tri/compteurs de listes, carte) continueront de voir
`terrain_exigu` jusqu'à un recalcul + bascule d'un run neuf — hors mandat (aucun run île lancé).
EXIGU-FIX-1 corrige déjà le libellé ; la bascule, elle, relève de la session de déploiement.
