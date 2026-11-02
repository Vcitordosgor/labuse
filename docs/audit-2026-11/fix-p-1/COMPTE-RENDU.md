# MANDAT FIX-P-1 — dernières dissonances avant déploiement

**Registre.** Branche `fix/p-1`, worktree `~/Desktop/labuse-fixp`, ports 9450/6650. Opus. Aucun merge,
aucun accès prod. Base Mac `labuse` (434 582 parcelles, run servi `q_v20`) en lecture pour la recette ;
venv PDF-capable `~/Desktop/labuse-main/.venv` + `PYTHONPATH` du worktree pour générer les documents.
Répond au lot P (`docs/audit-2026-11/nu-3/P/RAPPORT.md`) : la régression prioritaire + P-01→P-04 + J#4.

---

## Ce qui a été corrigé

### RÉGRESSION (prioritaire) — filtre « Risques / PPR » de la carte → 0 parcelle

**Constat (NU-3-P).** Le filtre « Risques (PPR/aléa) » retenait **0 parcelle** sur l'île entière là où
~**405 764** la portent — silencieusement, serveur ET client.

**Cause racine.** FIX-NU3-2 avait mappé `risques → ['ppr','georisque_alea']` (`app.py:58`, via
`CRITICAL_LAYERS`). Or ces deux tokens sont des `kind` de **`spatial_layers`** (la page *Couverture* :
sources ingérées), **absents** des tables que le filtre carte interroge :

| table | sert | token « risques » | `ppr` / `georisque_alea` |
|---|---|---|---|
| `parcel_flags` (filtre serveur `/filtre`) | 405 764 lignes | **présent** | absents |
| `dryrun_cascade_results` SOFT_FLAG (geojson → `p.flags` client) | 1 801 223 lignes | **présent** | absents |
| `spatial_layers.kind` (page Couverture) | sources | absent | présents |

Les deux vocabulaires avaient été confondus. L'expansion ne matchait donc **aucune** ligne.

**Correctif.**
- Serveur `src/labuse/api/app.py` — nouveau dict **`PARCEL_FLAG_GROUPES`** (vocabulaire `parcel_flags`,
  distinct de `CRITICAL_LAYERS`), `risques → ['risques']` (identité) ; `_q_v2_where._expand_flags`
  l'utilise au lieu de `CRITICAL_LAYERS`. `CRITICAL_LAYERS` (page Couverture) est **inchangé**.
- Client `frontend/src/lib/filters.ts` — `FLAG_GROUPES.risques = ['risques']` (miroir exact du serveur).

**Preuve.** Île : **405 764** parcelles (identique au compte de `parcel_flags`). Trois communes :
Saint-Paul **49 532 / 51 597**, Saint-Pierre **42 511 / 42 654**, Salazie **7 053 / 7 063**.

**Test de non-régression (demandé).** `tests/test_filtre_non_vacuite.py` (marqueur `reel`) :
- `test_filtre_flags_carte_jamais_vide_quand_la_donnee_existe` — pour chaque flag offert au client
  (sol_pollue, abf, icpe, risques, prescription_plu), SI `parcel_flags` porte des lignes de la couche
  (après expansion `PARCEL_FLAG_GROUPES`), ALORS le compteur d'île du filtre (`_q_v2_where` →
  `_q_v2_stats`, le chemin réel de `/filtre`) est **> 0**. Un 0 = la régression revenue.
- `test_filtre_risques_couvre_l_ile` — garde ciblée : « risques » couvre un ordre de grandeur cohérent
  (≥ moitié des parcelles à flag), jamais 0.
- **Vérifié qu'il ATTRAPE la régression** : en forçant l'ancien mapping `['ppr','georisque_alea']`, le
  compteur île retombe à **0** → le test échoue. Avec le correctif, 2 passed.

### P-01 — « SDP résiduelle » → « SDP restante » partout (régression M-T01)

Le mot unique de la doctrine SDP-UNIQUE-1/M-T01 est **« SDP restante »**. Résidus « résiduelle » alignés
(le **champ** `sdp_residuelle_m2` est inchangé — seul le libellé humain change) :

| surface | fichier:ligne | avant → après |
|---|---|---|
| Flash (tableau) | `flash/templates/rapport.html.j2:172` | « SDP **résiduelle** du run servi » → « restante » |
| Flash (verdict) | `faisabilite/potentiel.py:174` | « ~N m² de SDP **résiduelle** » → « restante » |
| Scan PM (patrimoine) | `frontend/.../ModulePanel.tsx:359` | « SDP résiduelle » → « SDP restante » |
| LLS (fiche) | `ModulePanel.tsx:1179` | idem |
| Chip moteur (SDP min) | `outils/moteurs.tsx:817` | idem |
| Aide Successions (×2) | `outils/Successions.tsx:45,47` | idem |
| Catalogue libellés | `lib/strings.ts:590,610` | idem |
| Légende couche | `lib/layers.ts:13` | idem |
| Contexte densifiables | `contexte/ContextePanel.tsx:639` | idem |

Dossier, Comparatif, fiche écran, Copilote disaient déjà « restante » (M-T01 tenu, confirmé). Les
occurrences « résiduelle » restantes dans le code sont des **commentaires / docstrings / noms de colonne
/ descriptions du registre** (jamais servies au client) et des concepts DISTINCTS (TVA résiduelle, marge
résiduelle, arête résiduelle, inondation résiduelle…) — laissées telles quelles.

### P-02 / J#4 — la tuile « RISQUES » compte les aléas distincts partout

**Constat.** La tuile « Risques » affichait trois nombres pour la même parcelle : Dossier/fiche-écran =
`n_vigilances` (toutes les lignes §5), Estimer = `n_hazards` (aléas distincts). « 5 vigilances » au
Dossier vs « 2 aléas » à l'Estimer.

**Correctif.** La **tuile « Risques »** affiche désormais, partout, le **nombre d'aléas distincts** par la
fonction unique **`distinct_hazards`** (= `aleas.n_hazards`), mot « aléa » :
- Dossier (page de garde) `src/labuse/exports/miroir.py:1121` — tuile passée de `n_vigilances` à
  `n_hazards` (lu sur la fiche, « N aléa(s) »).
- Fiche écran `frontend/src/components/fiche/Fiche.tsx:1000` — tuile passée de `vigils.length` à
  `aleas.n_hazards`.
- Estimer : déjà `distinct_hazards` (inchangé).

Les **« vigilances »** (notion plus large : servitudes, sols, SUP…) **gardent leur libellé propre** et ne
s'affichent **jamais** sous « Risques » : §5 du Dossier (ligne « Vigilances », `n_vigilances` conservé) et
section §5 écran « Risques et environnement » (badge « N vigilances »). Conforme au mandat.

**J#4.** Dossier == fiche == Estimer sur les 10 parcelles (voir recette).

### P-03 — une seule emprise bâtie (celle de la fiche)

**Constat.** Dossier/Apporteur imprimaient l'emprise BD TOPO **unionnée et clippée** à la parcelle
(`le_bien.emprise_batie_m2`, producteur unique `bati.emprise_bati_bdtopo_m2`) ; l'Estimer en imprimait
une autre, **non clippée** (`p_model_bati.emprise_bati_m2`) — 136 m² vs 105 m².

**Correctif.** `src/labuse/pige/api.py` — nouvel helper `_emprise_bati_fiche_m2(fiche)` lit la SEULE
emprise de la fiche ; appliqué à `estimation_annonce` (champ `emprise_bati_m2` + surface du total),
`_parcelle_mesures` (ligne « Bâti existant, emprise ») et `_contrainte_limitante`. L'ancien
`_emprise_bati_m2` (lecture `p_model_bati`) est retiré. **Preuve** (SQL + rendu) : Estimer == fiche ==
Dossier sur les 10 parcelles (105/232/143/1682…).

**Gabarit — pas de second moteur à corriger.** Le « 442 m² » attribué au Gabarit par l'audit est la
ligne **« Plafond d'emprise »** (CES × surface = plafond réglementaire), un fait DISTINCT, correctement
étiqueté. L'extracteur du lot P (regex large `emprise\s*(\d+)\s*m²`) l'avait capté comme « emprise
bâtie » — **artefact d'extraction**, pas un second moteur. Le Gabarit n'affiche aucune emprise bâtie
« totale » concurrente (son bâti sert la vue 3D / la déduction `zone − bâti_in_zone`, une géométrie
dérivée). Aucun changement de code nécessaire ; documenté ici.

### P-04 — « prix médian » = marche_dvf_commune ; l'estimé d'Estimer = « Prix estimé au m² »

**Constat.** Même intitulé « prix médian maison » pour deux valeurs : Dossier/Flash = médiane
`marche_dvf` (module unique), Estimer = médiane pondérée des comparables de précision (jusqu'à +9 %).

**État réel.** Les libellés « Prix médian maison / Terrain nu, médiane » (PDF `exports/blocs/annonce.py`
et écran `AnalyserAnnonce.tsx:419-420`) servent **déjà** `median_maison_eur_m2` de `marche_commune_bloc`
→ `mediane_commune` (module unique `marche_dvf_commune`). Égalité garantie par la suite de cohérence
(`test_mediane_commune_batie_identique_sur_les_trois_lectures`). Le « 3 664 » capté par l'audit était le
**gros chiffre de l'« Estimation du prix »** (pondéré + fourchette), pris par la regex large
`\d €/m² de … à …` — autre **artefact d'extraction**.

**Correctif (clarté, conforme au mandat).** Le prix pondéré d'Estimer porte désormais un **libellé
explicite « Prix estimé au m² »**, jamais une médiane : écran `AnalyserAnnonce.tsx:197` + PDF
`exports/blocs/annonce.py:234` (classe `.estkicker` ajoutée dans `exports/builder.py`). Aucune ambiguïté
possible entre l'estimation pondérée et la médiane de marché.

---

## Recette

Script `docs/audit-2026-11/fix-p-1/recette_matrices.py` — génère EN PROCESS les 3 documents porteurs des
5 faits (Dossier, Estimer, Flash) par leurs builders réels (route = `fiche` passée), sur les **10
parcelles témoins du lot P**, et confronte :

| fait | résultat |
|---|---|
| P-01 sdp_libelle | « SDP restante » partout ; « résiduelle » **nulle part** (Dossier/Estimer/Flash) |
| P-02 tuile Risques | « N aléa(s) » (jamais « vigilance ») ; Dossier == fiche `n_hazards` |
| J#4 aléas | Dossier == fiche == Estimer (`n_aleas`) sur 10/10 |
| P-03 emprise | Estimer == fiche `le_bien.emprise_batie_m2` sur 10/10 (105/232/143/1682…) |
| P-04 prix | Estimer étiquette « Prix estimé au m² » ; « Prix médian » = marche_dvf |

**→ 0 écart sur les 5 faits.**

Filtre Risques/PPR : compte cohérent sur 3 communes (Saint-Paul 49 532 / 51 597, Saint-Pierre
42 511 / 42 654, Salazie 7 053 / 7 063) ; île 405 764.

**Suites.**
- Front : **tsc 0**, **vitest 301/301** (63 fichiers). (⚠ node_modules réel installé dans le worktree —
  un symlink vers un autre checkout fait tomber 8 fichiers carte sur un refus de chemin worker Vite et
  ne collecte que 266 : artefact connu, non lié au code.)
- Suite de cohérence `tests/coherence_ecrans/` (`scripts/ci/coherence_run.sh`, base réelle run 17) :
  **6 passed, 0 écart** (1 €/1 m²).
- Banc complet (`pytest`, base app branchée) : **4 374 passed, 88 skipped, 4 failed**. Les **4 échecs
  sont PRÉ-EXISTANTS** — reproduits à l'identique sur la base propre (`git stash` du correctif) donc
  **0 nouveau rouge** :
  - `test_zone_donnees::test_lot2_emplois_zone_fourchette_et_sans_tranche` — libellé SIRENE « postes
    salariés **estimés (tranches)** » vs test attendant « **déclarés** » (`labuse/zone.py`, non touché).
  - `test_circuit_provenance::…[BO0852 / AD0554 / DY0106]` — un « 249 m » (ligne LTM, régime
    Autorisation) de l'Apporteur hors registre (proximités, non touchées).
- Hook pre-push (`scripts/git-hooks/pre-push`) : secret-scan ✓ · front tsc 0 / vitest 301 ✓ · famille
  unitaire Python ✓ · cohérence 6/0 ✓.

---

## Fichiers touchés (16 + 1 test + recette)

Serveur : `api/app.py` (filtre), `exports/miroir.py` (tuile Risques), `exports/blocs/annonce.py` +
`exports/builder.py` (libellé estimé + CSS), `faisabilite/potentiel.py` (verdict Flash), `pige/api.py`
(emprise unique), `flash/templates/rapport.html.j2`. Client : `lib/filters.ts`, `fiche/Fiche.tsx`,
`outils/{ModulePanel,moteurs,Successions,AnalyserAnnonce}.tsx`, `contexte/ContextePanel.tsx`,
`lib/{strings,layers}.ts`. Test : `tests/test_filtre_non_vacuite.py`. Recette :
`docs/audit-2026-11/fix-p-1/recette_matrices.py`.
