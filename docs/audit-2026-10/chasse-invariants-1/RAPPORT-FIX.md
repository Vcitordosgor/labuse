# RAPPORT-FIX — CHASSE-INVARIANTS-FIX-1

> Fermeture des 15 écarts de `ECARTS.md`, à la racine (une notion = un seul chemin). Branche
> `fix/chasse-invariants-1` depuis main (audit mergé), worktree `labuse-chasse-invariants`, API 8790,
> base servant **q_v18 / run_seq 15**. 15→15/10/2026. **Aucun run, rien sur le VPS** — seules deux
> reconstructions LOCALES étaient autorisées (E-02 `parcel_zone_plu`, E-07 centroïdes) + la recréation
> de la vue `v_pm_propension_vendre` (schéma, idempotente). Ne pas merger : **prêt à merger**.

## Verdict (5 lignes)
1. **8 lots, 8 commits** (`52e63248`→`3b80fe98`) + ce Lot 9 (garde + rapport). Les **15 écarts** sont
   fermés : 8 en **affichage** (effet immédiat) et 7 en **calcul** (effet au run final q_v19) ;
   E-08 est une table **orpheline** (rien à corriger, geste prod).
2. **Garde `chasse_invariants` : 26 OK / 11 ECART → 36 OK · 3 ECART · 0 SKIP.** Les 3 ECART restants
   (E-09, E-03, E-13) ne passeront au vert **qu'après le run q_v19** (raison détaillée §Garde).
3. Les 2 reconstructions locales sont **FAITES et prouvées** : `parcel_zone_plu` 427 419→430 320
   (+2 901 orphelines récupérées, témoin `97401000AH0371`→zone « Ud1 ») ; 9 792 centroïdes hors
   parcelle→**0** (témoin `97414000CK0122` : 236 m dehors→dedans).
4. **Bancs voisins tous verts** : `chasse_donnees` 0 ECART, `chasse_nav` 0 ECART, `banc_chasse_calculs`
   0 ECART. tsc 0, vitest lib 53, **21 tests `test_chasse_invariants_fix1.py`** verts.
5. **Pire écart (E-01, 19 569 %)** : l'export Comparatif imprime désormais « Saturé … », jamais le brut
   (capture `lot1-comparatif-APRES.html`).

---

## Les 15 écarts — un par un

Légende : **A** = affichage (effet immédiat au prochain service) · **C** = calcul (effet au run q_v19).

| # | sévérité | fermeture | A/C | commit | preuve |
|---|---|---|---|---|---|
| E-01 | FAUX-CLIENT | rendu UNIQUE `fmt_taux_emprise`/`fmtTauxEmprise` : au-delà de 100 % → « Saturé : le bâti existant dépasse déjà le plafond d'emprise du PLU actuel ». Base inchangée (saturation réelle). Fuite réelle (export Comparatif) fermée. Filtre « Saturé » ajouté. | **A** | `52e63248` | capture lot1 (AY0015→Saturé, 0 brut) ; garde d12 verte |
| E-02 | FAUX-CLIENT | `parcel_zone_plu` reconstruite sur **signature des entrées** (plus « table vide »). Reconstruction LOCALE faite (+2 901). | **A** (après reconstruction) | `a7e4a727` | gardes d2 vertes (0 orpheline / 0 SDP-sans-zone), témoin AH0371→Ud1 |
| E-03 | FAUX-CLIENT | cascade : `INTERDICTION` **unionnés** avant le seuil 50 % (`ctx.union_coverage`, même formule que la fiche). | **C** | `fd5e3b68` | cascade live : AK0138 65 %→HARD_EXCLUDE, AM1179 92 %→HARD_EXCLUDE ; garde d4 **rouge jusqu'au run** |
| E-04 | FAUX-CLIENT | fenêtre DVF ancrée sur `max(date_mutation)` via helper unique `fenetre_dvf_sql` (fiche/Flash/Dossier/PDF/comparables). | **A** | `3044add4` | témoin AK0182 129→167 ventes ; garde d5 verte (helper ancré) |
| E-05 | FAUX-CLIENT | `_pm_dirigeant` : aîné PLAUSIBLE [18;110] sinon « âge inconnu » (jamais 0/4/13/114/117). | **A** | `f263d1ac` | test Lot 6 ; garde d6 « servi hors bornes : 0 » |
| E-06 | FAUX-CLIENT | vue `v_pm_propension_vendre` clampée [18;110] (filtre 70+ ET veille Succession). Vue recréée. | **A** (vue) / **C** (veille matérialisée) | `f263d1ac` | vue : 0 âge hors bornes (5→0) ; veille 1→0 au recompute |
| E-07 | INCOHERENT | centroïde `ST_PointOnSurface` (toujours DANS la parcelle), ingestion + 9 792 existantes (local). | **A** (point) / **C** (cascade le lit) | `a7e4a727` | garde d1 centroïde 9 792→0 |
| E-08 | INCOHERENT | table `parcel_residuel_bati` **ORPHELINE** (builder retiré 24/07, 0 lecteur servi). Le bâti SERVI (`parcel_bati_revele`/`bati.py`) est déjà clippé (0 infraction). **Aucun code à corriger** ; garde reciblée ; DROP recommandé en prod. | — | `a7e4a727` (garde Lot 9) | garde d1 bâti SERVI = 0 |
| E-09 | INCOHERENT | `surface_terrain_m2` NULL sur tout q_v18 : le code d'écriture (`residuel.py:243`) **existe déjà** ; le run q_v18 a été figé AVANT. | **C** | — (run q_v19) | garde d1 surface_run **rouge jusqu'au run** |
| E-10 | INCOHERENT | parcelle `cascade_exclue` en bande A/B/C/D → bande **« HC » (Hors classement)** + raison (`cause_libelle`), jamais A/B/C/D. Score conservé (ordre, pas score nul) → cohérence bande⇔score tenue. | **C** | `5481ab53` | combiner live : BE0108→HC « domaine public fluvial », AZ0498→HC « emprise routière » ; 2 témoins non-exclus restent A |
| E-11 | INCOHERENT | même racine qu'E-03 (non-union). Fiche et cascade s'accordent après union. | **C** | `fd5e3b68` | idem E-03 |
| E-12 | INCOHERENT | `surface_ha` prend le `filtre_vivant_sql` (même parc que `n_parcelles`). | **A** | `3b80fe98` | garde d8 verte : 24/24 communes surface = parc vivant |
| E-13 | INCOHERENT | `sous_densite` calculé sur la valeur ARRONDIE (celle servie), fin de la contradiction « 40 % + sous-densité ». | **C** | `52e63248` | test Lot 1 ; garde d12 sous-densité **rouge jusqu'au run** |
| E-14 | ROBUSTESSE | `tuile_hors_grille` : x/y hors [0,2^z) → **204** tuile vide (jamais 500), un correctif / deux routes. | **A** | `3b80fe98` | garde d11 verte : 6 tuiles hors grille servies proprement |
| E-15 | ROBUSTESSE | > 2 ha → « Opération d'aménagement : hors estimation promoteur » (seuil unique `amenagement.py`) : `score_e._row` (source) + fiche `score_e_block` (immédiat). | **A** (fiche) / **C** (score_e) | `9412d123` | test Lot 7 ; marge M€ supprimée dès le service |

## Les familles de racine (closes)
- **« Intermédiaire impossible non borné »** (E-01) → rendu unique, base honnête.
- **« Non-union des polygones de même kind »** (E-03/E-11) → `ctx.union_coverage`, partagé fiche↔cascade.
- **« Âge dirigeant sans clamp »** (E-05/E-06) → un garde-fou [18;110] à la source (aîné + vue).
- **« Table dérivée statique jamais revalidée »** (E-02 + cousin E-09) → signature d'entrées (E-02) ;
  E-09 n'était que le run figé (code présent).
- **« Deux définitions du parc »** (E-12) → `filtre_vivant_sql` sur la surface.

---

## La garde `chasse_invariants` (rejouée)

`PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_invariants` → **36 OK · 3 ECART · 0 SKIP**
(était 26 OK · 11 ECART · 2 SKIP). Cinq gardes ont été **recadrées** pour viser la vérité SERVIE, pas
une ancienne hypothèse périmée par la décision de design :

- **d1 ratios bornés / d12 taux impossible (E-01)** : la base GARDE le taux brut (saturation réelle) ;
  la garde prouve désormais que le rendu UNIQUE (`fmt_taux_emprise`) ne laisse jamais fuir un % > 100
  (pire cas 19 569 % → « Saturé … »).
- **d1 bâti ≤ dessin (E-08)** : vise `parcel_bati_revele` (SERVI, clippé = 0), plus l'orpheline figée.
- **d5 fenêtre DVF (E-04)** : vérifie que le helper SERVI `fenetre_dvf_sql` ancre sur `max(date_mutation)`
  (et non CURRENT_DATE) — la parité lecteur↔helper est prouvée par les tests Lot 5.
- **d6 âge dirigeant (E-05/E-06)** : compte les âges SERVIS hors bornes (aîné 0, vue 0) ; les **481**
  dates INPI aberrantes de SOURCE sont signalées à part (jamais modifiées en base), et la veille
  matérialisée (1) est signalée « à recompute ».

### Vertes MAINTENANT (affichage + reconstructions locales)
E-01, E-02, E-04, E-05, E-06 (vue), E-07, E-08, E-12, E-14 — + tous les invariants déjà verts.

### Ne passeront au vert qu'APRÈS le run final q_v19 (3 ECART, raison)
| garde | écart | pourquoi |
|---|---|---|
| d1 `surface du run présente` | **E-09** | `surface_terrain_m2` NULL sur q_v18 (run figé avant peuplement) ; le code d'écriture existe → peuplé au q_v19. |
| d4 `PPR rouge union vs cascade` | **E-03/E-11** | lit `cascade_results` du run SERVI (q_v18) ; l'union ne s'applique qu'au recalcul cascade du q_v19. |
| d12 `sous-densité cohérente` | **E-13** | `sous_densite`/`taux_emprise_pct` ne seront ré-écrits cohérents qu'au q_v19. |

(E-10 « HC », E-06 veille `parcel_veille_succession`, E-15 `score_e`, E-07 effet cascade : corrigés en
code, matérialisés au q_v19 / au recompute veille — non bloquants, non comptés en ECART car la garde
vise le point servi juste.)

## Bancs voisins (exigés verts)
- `scripts.coherence.chasse_donnees` → **0 ECART** (2 OK · 23 SKIP, base locale non warmée).
- `scripts.coherence.chasse_nav` → **0 ECART** (7 OK · 3 SKIP).
- `docs/audit-2026-10/chasse-calculs-1/banc_chasse_calculs.py` → **0 ECART**.

---

## Plan de run final (ce que q_v19 doit embarquer) + gestes prod

**q_v19 (recalcul) embarque le code de ces lots :**
1. **E-03/E-11** — cascade PPR rouge en UNION (`phase1.py`, `context.union_coverage`) → recalcul cascade.
2. **E-10** — fusion bande « HC » pour les `cascade_exclue` (`score_labuse_combine.combiner`) → recalcul scoring.
3. **E-13** — `sous_densite` sur la valeur arrondie (`residuel.py`) → recalcul résiduel.
4. **E-09** — peuplement `surface_terrain_m2` (code présent `residuel.py:243`) → recalcul résiduel.
5. **E-15** — `score_e._row` garde-fou 2 ha → rebuild `score_e`.
6. **E-07** — l'effet du centroïde corrigé sur la cascade (zone/distances au point) → recalcul cascade.

**Gestes PROD (hors run, au déploiement) :**
- **E-02** — rejouer la reconstruction `parcel_zone_plu` (DROP+CREATE, ~16 min) ; purge/réchauffe des
  **tuiles** (`mvt_tile_cache`) car le zonage de 2 901 parcelles change.
- **E-07** — rejouer la mise à jour des **centroïdes** hors-géométrie (`UPDATE … ST_PointOnSurface`),
  puis re-ingestions qui lisent le point (adresses/amenités) si besoin.
- **E-06** — recréer la vue `v_pm_propension_vendre` (au boot) + **recompute de la veille**
  `parcel_veille_succession` (purge l'unique SCI à âge aberrant).
- **E-08** — **DROP** de la table orpheline `parcel_residuel_bati` ; repointer `ban_adresses` sur le
  bâti servi (`parcel_bati_revele`) — dette propre, hors run.
- **E-05/E-06 (source)** — signaler à l'amont INPI/RNE les **481 dates de naissance aberrantes**
  (futures 2026-11, enfants 2018-2024, centenaires 1909/1911) — cf. `captures/.../lot6-dates-inpi-aberrantes.txt`.

**Après q_v19 + gestes**, la garde `chasse_invariants` doit passer **37/… tout vert** et rejoindre le
banc de nuit.
