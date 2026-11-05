# CLASSEMENT-USAGE-1 — un classement juste pour tous les métiers

**Mandat** décision Vic (05/11/2026). Opus, branche `fix/classement-usage-1`, worktree
`~/Desktop/labuse-usage`, ports 9700/6900. Pas de merge, aucun accès prod. Base Mac `labuse`
(run servi **q_v20**, `runs.current()` vérifié). Lectures d'abord :
`docs/audit-2026-11/nu-4/D/RAPPORT.md` (branche `audit/nu4-d`) et `docs/SCORING_SPEC.md`.

> **En une ligne.** LABUSE sert TOUS les professionnels de l'immobilier. Le **palier reste la
> probabilité de vente**, la même pour tous — jamais « bonne affaire à construire ». Le **potentiel
> à bâtir** devient une information à part, lue par **UNE seule fonction** servie partout, qui ne
> sert **jamais de SDP sur une zone fermée**. Un **tri par usage** (« Va se vendre » / « À
> construire ») mémorisé par compte. Trois défauts du NU4-D corrigés à la source.

---

## 1. Ce qui change (et ce qui ne change pas)

**Ne change pas** — le calcul de la probabilité de vente (`p_raw`), les paliers servis, le run
**q_v21** : les corrections de *calcul* ne valent qu'à partir du prochain run. Le tri « Va se
vendre » est **identique au classement servi d'aujourd'hui** (recette §4).

**Change** — à la LECTURE (effet immédiat, run non recalculé, même doctrine que
`zone_servie.garde_sdp_residuelle`) :

1. **Une seule fonction de lecture du « potentiel à bâtir »** — `faisabilite/potentiel_batir.py`
   (`potentiel_batir` / `potentiel_batir_batch`). Elle sert quatre faits : **SDP restante** (bornée
   à 0 en zone fermée), **zone ouverte/fermée** (AU non ouverte, A, N, zone fermée au règlement),
   **constructibilité**, et **« rien à bâtir »** quand la SDP restante est nulle. Servie TELLE QUELLE
   à la fiche, aux listes, à la carte, au Copilote et au PDF.
2. **Tri par usage** dans les listes et la carte — « Va se vendre » (défaut, le classement actuel) /
   « À construire » (ne garde que le constructible, classé par probabilité de vente). **Mémorisé par
   compte**.
3. **Trois défauts corrigés à la source.**
4. **Libellés** — aucun texte ne laisse croire que le palier mesure un potentiel de construction
   (vérifié : `status.ts` est déjà au registre « probabilité de vente », 0 conflation trouvée).

---

## 2. Le gate « zone fermée » — verdict-driven, une seule règle

La fermeture est lue sur les **verdicts que le moteur produit déjà** (jamais le préfixe de zone nu —
garde-fou 21 077, cf. `constructibilite.py`). Une zone est **fermée / rien à servir** si l'un de :

- `parcel_residuel.cause` présente (le moteur a dit « pas de potentiel » : `zone_non_constructible`,
  `habitat_interdit`, `terrain_exigu`…) — la SDP stockée vaut alors déjà 0 ;
- `parcel_constructibilite.label` ∈ {`declasse_zone_fermee`, `declasse_non_constructible`} ;
- `parcel_au_statut.classe` ∈ {`declasse_au_fermee`, `declasse_au_statut_inconnu`, `générique`}.

S'appuyer sur le verdict par parcelle (et non la famille de zone dominante) **respecte l'assiette
clippée** des parcelles à cheval (décision FAISABILITE-clip) : une dominante A/N portant une portion
U/AU constructible garde sa SDP ; une A/N sans portion constructible porte déjà sa cause → fermée.

Mesuré sur le **top-100 du lot D** (q_v20) : **66 à construire**, **22 zone fermée**, **12 rien à
bâtir** — exactement les **66 affaires plausibles** et les 34 « fausses affaires » du NU4-D.

### Le cas 97422000AX1253 (2AUe), nommé au mandat
Le run servi lui stocke **25 426 m²** de SDP résiduelle **sans cause** (`parcel_residuel_runs` run_seq
17), parce que le résiduel ignorait la fermeture que la constructibilité signale
(`declasse_zone_fermee`). Le gate la rattrape : **SDP restante servie = 0**, « Rien à bâtir — Zone
fermée à l'urbanisation (2AUe) ». Borné à la lecture, sur fiche **et** PDF (au-sol **et** table rase).

---

## 3. Les trois défauts, corrigés à la source

| # | Défaut NU4-D | Correction | Effet |
|---|---|---|---|
| 1 | SDP servie sur zone fermée (AX1253 = 25 426 m² en 2AUe) | gate `potentiel_batir` borne la SDP à 0 (lecture) ; `bloc_potentiel` (PDF) et `_potentiel_transformation_block` (fiche) défèrent au gate | immédiat, tous lecteurs |
| 2 | `rang` inclut l'étage 0 → une écartée loge au rang 5 | `pipeline.py` : l'étage 0 est lu **avant** le rang et **exclu** du classement (`hors = ¬copro ∧ ¬ecartee_etage0`) | **prochain run** (q_v20 intact) |
| 3 | « À suivre » non constructible servie **sans avertissement** (13 pièges silencieux) | `verdict_servi` joint constructibilité + statut AU + cause résiduelle → champ `avertissement` + `declasse` (le palier de probabilité ne bouge pas) | immédiat ; **13/13** pièges NU4-D portent désormais un motif |

Le défaut 2 est une correction de *calcul* : elle ne vaut qu'au prochain run (q_v20 servi inchangé —
« Va se vendre » reste identique). Le tri « À construire » écarte de toute façon les écartées en
lecture (périmètre par défaut hors étage 0).

---

## 4. Tri par usage (listes + carte), mémorisé par compte

- Prédicat unique `potentiel_batir.where_a_construire` (EXISTS autonomes) injecté dans
  `FiltreCriteres.a_construire` → coule dans le **compteur**, la **page** ET la **liste d'IDU de la
  carte** à l'identique (jamais deux définitions).
- « À construire » = zone ouverte **ET** SDP restante > 0, classé par **rang** (= probabilité de
  vente). « Va se vendre » = le classement actuel.
- Mémoire par compte : colonne `prefs_carte.tri_usage` + endpoint `/moi/prefs-carte` (lecture/
  écriture séparée, un POST `tri_usage` ne remet pas fond/couches à NULL). Front : `useApp.triUsage`
  hydraté au boot, segmenté « Va se vendre / À construire » dans la liste.

Île entière (q_v20) : « Va se vendre » = **432 350** · « À construire » = **194 344** parcelles.

---

## 5. Surfaces servies (une fonction, partout)

| Surface | Point d'entrée | Statut |
|---|---|---|
| Fiche React | `fiche.potentiel_a_batir` → `PotentielABatirBlock` (en tête de Constructibilité) ; `_potentiel_transformation_block` déférant au gate | ✅ |
| Listes + carte | `FiltreCriteres.a_construire` (`/filtre`, `/parcels`) + segmenté `useApp.triUsage` | ✅ |
| Copilote | `robinet_fiche` extracteur `potentiel_a_batir` + `resume_fiche._CHAMPS` | ✅ |
| PDF / Flash | `flash/data.py` `out["potentiel_a_batir"]` + ligne « Potentiel à bâtir » dans `rapport.html.j2` ; `bloc_potentiel` borné | ✅ |

### 5.1 La SDP d'une zone fermée : une seule valeur, fiche **et** carte
Le NU4-D servait une SDP résiduelle sur des zones fermées (ex. AX1253, 25 426 m²) sans cause — à la
fiche **comme à la tuile MVT**. Pour que la carte et la fiche servent la MÊME valeur (∅), la 3ᵉ porte
« zone fermée au verdict » (`potentiel_batir.sql_zone_fermee_verdict`) est reproduite aux TROIS
lecteurs que le banc confronte : la **fiche** (`_potentiel_transformation_block` défère à
`potentiel_batir`, SDP servie ∅), la **tuile** (`tiles.py build_mvt_table`, porte conditionnelle +
`labuse build-mvt`), et le **jumeau SQL** du banc (`checks_parcelle`). Mesuré après rebuild MVT :
fiche ∅ = jumeau ∅ = tuile absente pour les 5 zones fermées de l'échantillon, 152 = 152 = 152 pour
une parcelle constructible. Le `fiche_cache` (L2 en base) est purgé avant recette (sinon il sert
l'ancien chiffre). Même geste que ECARTS-ZERO-1 (« corrigé source `tiles.py`, rebuild MVT »).

---

## 6. Recette

| Contrôle (mandat) | Résultat |
|---|---|
| 100 premières du lot D, tri « À construire » — 0 sans rien à bâtir ni zone fermée en tête | ✅ **66 têtes**, toutes constructibles (34 écartées : 22 zone fermée + 12 rien à bâtir) |
| tri « Va se vendre » — classement **identique** à aujourd'hui (q_v20) | ✅ 200/200 têtes identiques au servi |
| cas **97422000AX1253** corrigé | ✅ SDP servie **25 426 → 0** (fiche, carte, PDF) ; « Rien à bâtir — Zone fermée (2AUe) » |
| captures avant/après | ✅ `preuves/AVANT_APRES.txt` + `preuves/captures/` (fiche SDP ∅, toggle Va se vendre/À construire) |
| les 13 pièges silencieux du NU4-D portent un avertissement | ✅ **13/13** |
| **banc complet 0 rouge** · suite de cohérence verte | ✅ **3368 comparaisons · 0 écart** (10 reds SDP miens + 6 `SDP-tuile` hérités résolus par gate tuile + rebuild MVT ; 18 reds commune = `commune_contexte_cache` périmé sur la base Mac, `rafraichir_contexte_cache` → 0) — cf. §5.1 |
| hook vert (unit + tsc + vitest) | ✅ **unit 2950/0**, front **tsc 0**, **vitest 270/0** (8 suites non chargées = artefact symlink maplibre worker, pré-existant) |

Rejouable : `preuves/recette.py` (les 5 contrôles, **TOUT VERT**), `preuves/avant_apres.py` →
`preuves/AVANT_APRES.txt`, `preuves/extract_nu4d.sql` (extraction NU4-D). **Pièges de recette** : purger
`fiche_cache` (L2 en base) et **rebuild MVT** (`labuse build-mvt`) avant le banc, sinon il confronte
d'anciennes valeurs. La suite `base de test` reste à **1350/0 utiles** ; 2 échecs (`test_m137` tuiles,
`test_circuit_p2` perf) **pré-existants** (échouent identiquement sur l'arbre vierge `git stash`,
dépendances d'ordre/charge), non liés à ce mandat.

---

## 7. Fichiers touchés

**Back** — `faisabilite/potentiel_batir.py` (NEUF, la fonction unique + fragments SQL),
`verdict_servi.py` (avertissement), `scoring/p_v2/pipeline.py` (rang hors étage 0),
`faisabilite/potentiel.py` (gate PDF), `api/app.py` (`potentiel_a_batir` fiche, tri `a_construire`,
SDP transfo ∅ en zone fermée), `api/tiles.py` (tuile MVT : porte zone fermée), `comptes.py` +
`api/onboarding.py` (`prefs_carte.tri_usage`), `exports/robinet_fiche.py`, `copilote_v2/resume_fiche.py`,
`flash/data.py`, `flash/templates/rapport.html.j2`.

**Banc** — `scripts/coherence/checks_parcelle.py` (jumeau SQL SDP : porte zone fermée, aligné au producteur).

**Front** — `lib/types.ts` (`PotentielABatir`), `components/fiche/constructibilite.tsx`
(`PotentielABatirBlock`), `components/panel/ResultsSection.tsx` (segmenté tri par usage),
`store/useApp.ts` (`triUsage` + filtre), `lib/api.ts` (`a_construire` + `tri_usage`).

**Tests** — `tests/test_potentiel_batir.py` (NEUF).

## 8. Limites / dette
- Défaut 2 (rang hors étage 0) : effectif **au prochain run** ; q_v20 servi inchangé (voulu).
- Build frontend via `node_modules` symlinké depuis `~/Desktop/labuse` (worktree sans install).
- Dette : merge PR.
