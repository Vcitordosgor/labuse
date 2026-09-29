# CALCULS-FIX-1 — trois risques, avant le run

**Branche** `fix/calculs-1` (worktree `labuse-calculs`, base `origin/main` `f5cde690` = main après merge de CALCULS-1). Aucun run île, aucune bascule. Règle : aucune valeur affichée ne change sans être inscrite dans `CHANGEMENTS.csv` avec la raison.

Base : les 6 risques structurels de `docs/audit-2026-09/CALCULS-1/RAPPORT.md`. Traités ici : **n° 2, 3, 6**. Laissés pour après le déploiement : **n° 1, 4, 5** (rappelés en fin).

## Garde-fous

| Contrôle | État |
|---|---|
| `tsc --noEmit` | **0** |
| `vitest run` | **225 passed** |
| V6b (`test_v6b_coherence`) | **vert** |
| `pytest tests/` | état de départ (1 échec **pré-existant** hors périmètre, voir plus bas) — 0 régression |

Un commit par lot, poussé sur `origin/fix/calculs-1`. Pas de merge.

---

## Lot A — parcelle à cheval sur deux communes (risque n° 3)

**Cause supposée (audit).** `zone_dominante` groupe ses parts par token de zone sans la commune : une parcelle touchant deux communes verrait ses zones homonymes fusionnées → dominante potentiellement fausse.

**Mesure île — la prémisse est INFIRMÉE.** Le fix littéral proposé (grouper par `(commune, token)`) ne produit, sur l'échantillon île, **que des faux positifs « à cheval »** : des parcelles d'un **seul type de zone** réparties sur deux communes, qu'il basculerait « à cheval » à tort.

- 515 parcelles « victimes » de fusion (un token présent sur ≥ 2 communes) ; parmi elles, avec le fix littéral : **3 changements de dominante, 11 bascules `a_cheval`**.
- Or les cas observés sont des faux positifs : `97420000AB0002` = **100 % N** réparti Ste-Suzanne/voisine → deviendrait « à cheval » ; `97420000AS0404` = **95,8 % N** → idem. Par définition du drapeau (« la dominante ne résume plus la parcelle »), **100 % N EST résumé par N** → il ne doit PAS être « à cheval ».

**Correction retenue (arbitrage Vic « fix ciblé + garde »).** La dominante et `a_cheval` se décident sur le **TYPE de zone (token + famille)**, jamais sur la commune. La sonde `_N_ZONES` clée désormais sur `(token, famille)` — la MÊME clé que `_PARTS` — pour rester cohérente et déclencher le calcul des parts au **vrai** cas d'ambiguïté (un même token portant deux familles).

**Parcelles concernées : 0 aujourd'hui.** Aucune parcelle île n'a un token multi-famille (mesuré sur 30 000) → **0 valeur servie change**. C'est une **garde défensive** contre une future collision token↔famille, qui ferme l'incohérence `_N_ZONES` (token) vs `_PARTS` (token+famille). Les faux positifs du fix littéral sont ainsi évités.

Fichier : `faisabilite/zone_servie.py:_N_ZONES`. Test : `tests/regles/test_calculs_fix1_lot_a.py` (garde statique + parcelle réelle 100 % N non « à cheval »).

## Lot B — les pourcentages ne dépassent plus 100 (risque n° 2)

**Cause.** `zone.py:contraintes_plu` et `zone_demain` sommaient des aires d'intersection **sans `ST_Union`** : deux polygones GPU qui se recouvrent (bord partagé mal digitalisé, secteur superposé) comptent deux fois.

**Mesure.** Sur 8 000 parcelles-échantillon (parcelle prise comme zone d'étude, proxy de l'outil) : **2 parcelles** avec une part de zone > 100 %, **maximum constaté = 200 %** (une zone comptée double). Groupes en double compte : 3.

**Correction.** Les morceaux d'intersection d'un même `(zone, commune, document)` sont **fusionnés (`ST_Union`) avant l'aire** — même doctrine que `risques_zone`/`assainissement_zone`/`espaces_zonages_zone` (déjà en `ST_Union`). `contraintes_plu` : union calculée une seule fois (CTE `agg`). `zone_demain` : zones AU fusionnées avant les hectares (`n` reste le compte de polygones).

**Vérification.** Après correction, `max part_pct = 100` sur le même échantillon. Test end-to-end sur la victime `97411000BP0891` : zone Uac **200 % → 100 %**, aucune part > 100.

**Parcelles concernées : ~2/8 000 (≈ 108 île en proxy)** ; l'outil réel (Étude de zone) est corrigé partout où des polygones PLU se recouvrent dans la zone dessinée. Fichier : `zone.py:contraintes_plu`, `zone.py:zone_demain`.

## Lot C — l'année de défiscalisation n'est plus figée (risque n° 6)

**Cause.** `ANNEE_ACTIVE = 2026` écrit en dur : au 1er janvier 2027, les plafonds de loyer et le coefficient de surface auraient été servis **périmés, sans signalement**.

**Correction.** `defisc.annee_active(today)` déduit l'année du barème à servir de la **date du jour** ET des `config/calibrage/defisc_<Y>.yaml` disponibles (le plus récent `Y ≤ année courante`). Si le barème de l'année n'existe pas encore : le dernier disponible est servi **avec son millésime affiché** (`millesime_bareme`, `bareme_perime`, `signalement_fraicheur` dans `sortie_locative`) **+ une entrée « barème défiscalisation »** sur `/sante/fraicheur` (page Données) — jamais un chiffre muet. Bascule automatique dès qu'un `defisc_2027.yaml` est déposé (0 code à toucher).

**Parcelles concernées : 0 valeur change en 2026** (barème 2026 toujours servi, mêmes valeurs). Le changement s'active en 2027. **Test simulant le 2 janvier 2027** : barème 2026 servi + `bareme_perime=True` + signalement nommant 2026 et 2027 (`tests/test_calculs_fix1_lot_c.py`, 4 verts). Fichiers : `faisabilite/defisc.py`, `fraicheur_caches.py`.

---

## Échec pytest de départ (pré-existant, hors périmètre)

`tests/test_faisabilite.py::test_plafond_densite_borne_les_zones_denses` échoue déjà sur `origin/main` (vérifié : Lot B stashé, fichier de test identique à la base). Il appelle `estimate_capacity(resolve_zone("U1pru"), …)` — sans aucun lien avec les fonctions corrigées ici ; la base de test ne porte pas la calibration PLU `U1pru` produisant la modulation « plafond de densité ». **0 régression introduite par ce mandat.**

## Risques laissés pour après le déploiement (rappel)

- **N° 1 — marge de surélévation, deux chemins clampent différemment** (estimé `max(0, …)` → 0 vs sourcé brut → négatif). Rendu incohérent mais **verdict identique** (`possible=False`) → non FAUX ; harmonisation cosmétique, sans urgence avant le run.
- **N° 4 — `compute_bilan` : coef négatif si `marge+frais > 100 %`** (saisie libre de la calculette) ; `coef_rendement = 0` → repli qui change l'unité. **Garde d'entrée** à ajouter côté calculette — touche l'outil interactif, pas le run.
- **N° 5 — `dvf_mediane.py` : bornes/seuils en littéraux** (double source de vérité vs `dvf_profils.yaml`). **Refactor de configuration**, sans effet sur une valeur servie aujourd'hui → à faire hors chemin critique du run.

## Livrables

```
docs/audit-2026-09/CALCULS-FIX-1.md   (ce fichier)
docs/audit-2026-09/CHANGEMENTS.csv    (par lot : avant / après / n_parcelles / raison)
src/labuse/faisabilite/zone_servie.py (Lot A)
src/labuse/zone.py                    (Lot B)
src/labuse/faisabilite/defisc.py, src/labuse/fraicheur_caches.py (Lot C)
tests/regles/test_calculs_fix1_lot_a.py, tests/test_calculs_fix1_lot_c.py
```
