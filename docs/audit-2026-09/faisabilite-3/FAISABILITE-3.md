# FAISABILITE-3 — L'outil Faisabilité refait sur la maquette validée

Branche `feat/faisabilite-3` (worktree `~/Desktop/labuse-faisa3`, ports 8535/5735). Mandat de Vic
du 27/09/2026 : reproduire la **lisibilité** de la calculette Kelfoncier avec des **chiffres vrais**
(terrain non rasé par défaut trompeur, reculs jamais déduits, AU non ouverte comptée → tout cela
corrigé). 5 lots, un commit par lot. **Règle absolue tenue : aucun calcul dans le front** — chaque
chiffre affiché vient d'un appel au moteur ; le front ne fait que rendre et renvoyer le scénario et
les hypothèses.

Commits : Lot A `876a03c7` · Lot B `634c2574` · Lot C `ce34977e` · Lot D `ae1a5d69` · Lot E (ce
livrable + captures).

---

## La fonction unique et sa signature

```python
# src/labuse/faisabilite/scenarios.py
def faisabilite_scenario(session, parcel_id,
                         scenario: str | None = None,       # 'terrain_libere' (défaut) | 'bati_garde'
                         hyp_overrides: dict | None = None,  # « et si… » (3 clés blanches, cf. HYP_EDITABLES)
                         test: dict | None = None            # {n_logements, surface_par_logement} — optionnel
                         ) -> dict | None                    # None si la parcelle est hors PLU
```

**UN SEUL moteur, deux scénarios**, sans dupliquer aucun calcul :

- **`terrain_libere`** (défaut) : l'enveloppe du terrain, bâti existant compté à 0 =
  `parcel_faisabilite(session, parcel_id, hyp_overrides)` tel quel
  (SDP = min(zone d'implantation, emprise max) × niveaux × occupation, moteur GEOMETRIE-1 pour
  l'assiette). La **surface à démolir** (emprise bâtie BD TOPO × niveaux LiDAR = `sdp_existante`) est
  renvoyée pour affichage.
- **`bati_garde`** : le chemin du **résiduel servi** `compute_residuel(..., assiette_clippee=True)`
  (bâti conservé, SDP existante déduite, hauteur LiDAR — DONNEES-FIX-1). **Golden 55 (invariant) :**
  `sdp_possible_m2 == compute_residuel(assiette_clippee=True).sdp_residuelle_m2` (même code path que
  la vue `parcel_residuel` servie). Les logements sont mis à l'échelle du plancher résiduel restant
  (`sdp_residuelle / sdp_enveloppe`) — **toujours ≤ terrain libéré**.

Cas particuliers, jamais devinés au front :

| Cas | Détection (moteur) | Sortie |
|---|---|---|
| Parcelle **nue** | `taux_emprise_pct < 2 %` (déf. « terrain nu » du résiduel) | `bati_present=False` → un seul scénario |
| À **cheval** | `ctx.a_cheval` + `zone_parts` (GEOMETRIE-1) | `portion_constructible_m2` + verdict « sur les N m² en U6c » |
| **AU non ouverte** | `cause == "zone_transition"` et code ∋ « AU » | `sdp=0`, motif « zone AU non ouverte à l'urbanisation » |
| **Habitat interdit** | `cause == "habitat_interdit"` | `logement_autorise=False` + citation ; test → « non autorisé » |
| Terrain exigu / rédhibitoire / hauteur indispo / règle non validée | `cause` structurée | `sdp=0` + motif dédié |

L'API expose ce moteur en **un seul appel** :
`POST /modules/faisabilite/{idu}/scenario` `{scenario, overrides, test}` → `{idu, scenario: <panneau>}`
(`src/labuse/api/modules.py`, `ScenarioIn` / `faisabilite_scenario_route`). Le front l'appelle via
`postFaisabiliteScenario` (`frontend/src/lib/api.ts`). Panneau : `FaisabiliteTab`
(`frontend/src/components/fiche/constructibilite.tsx`) — **une implémentation** partagée par l'outil
(M22) et l'onglet Faisabilité de la fiche parcelle.

---

## Les valeurs LABUSE et leur fichier

Les hypothèses viennent de **`config/`**, jamais du composant (test-garde inclus). Base
île-générique `config/hypotheses_ile.yaml`, override par commune dans `config/plu_zonage.yaml`
(section `hypotheses_faisabilite`) ; défauts du dataclass `Hypotheses` (`faisabilite/engine.py`).

**Seules 3 vraies hypothèses de modélisation sont éditables** (RETOURS-15 C3 ; `HYP_EDITABLES`,
`faisabilite/engine.py`) :

| Clé | Libellé | Défaut | Bornes | Fichier |
|---|---|---|---|---|
| `coef_occupation` | Occupation du gabarit | 45 % | 10–100 % | `hypotheses_ile.yaml` / dataclass |
| `coef_rendement` | Rendement SDP → habitable | 80 % | 50–100 % | idem |
| `logement_m2` | Surface moyenne / logement | 65–80 m² | 20–200 m² | idem |

Les valeurs **fixées par le PLU** (hauteur d'un niveau, densité, surface d'une place) ne sont jamais
des hypothèses éditables (servies par le moteur, non modifiables).

**Garde « défaut ≠ PLU »** (test `test_garde_occupation_defaut_pas_100pct`) : l'occupation par défaut
est `0 < coef_occupation ≤ 1.0` et **jamais 1.0** — aucune valeur par défaut ne remplit 100 % de
l'emprise max (contrairement à Kelfoncier qui contredit le CES).

---

## Le tableau des 8 étapes et leur source

Les 8 étapes du panneau (repliées par défaut, maquette rule 6) sont ASSEMBLÉES depuis la fourchette
du moteur — les mêmes valeurs que le verdict (même appel). Étape 5/6 dépendent du scénario.

| # | Étape | Valeur | Source (badge) |
|---|---|---|---|
| 1 | Zone d'implantation après reculs | `zone_implantation_m2` (assiette après reculs, avant CES) | Sourcé — moteur gabarit / géométrie réelle |
| 2 | Emprise au sol max | `surface × CES %` si réglementé, sinon « non réglementée → bornée par les reculs » | Sourcé (Art. 9) / Pas de règle PLU |
| 3 | Niveaux (hauteur) | `R+n` + hauteur (m) | Sourcé (Art. 10, hé/hf) |
| 4 | Plancher max (× occupation) | `surface_plancher_m2` (enveloppe pleine) | Estimé (occupation) |
| 5 | Bâti existant | terrain libéré : « 0 m² (démolition de ~M m² à chiffrer) » · bâti gardé : « ~S m² conservés » | Sourcé (égout LiDAR / BD TOPO) ou Pas de règle (terrain nu) |
| 6 | Plancher possible | terrain libéré : enveloppe · bâti gardé : `sdp_residuelle_m2` | Dérivé |
| 7 | Logements | fourchette (plancher habitable ÷ surface moyenne/logt) | Dérivé |
| 8 | Stationnement | `~N place(s)` si régime borné, sinon « non borné » | Sourcé (Art. 12) / non réglementé |

Deux champs de fourchette **ajoutés** au moteur (`faisabilite/engine.py`, affichage seul, 0 calcul
modifié) : `zone_implantation_m2` (étape 1) et `emprise_sol_max_m2` (étape 2).

**Ce qui n'est pas modélisé se DIT** (Lot D) : mixité `propose`/absente → ligne PLU « non
modélisée » ; hauteur au prospect → « calculée par parcelle » (jamais une valeur de zone trompeuse) ;
CES absent → « non réglementé → bornée par les reculs » (jamais 0). Pied : « Pré-faisabilité sur
règlement public, pas un certificat d'urbanisme ».

---

## Où chaque lot vit

| Lot | Fichiers |
|---|---|
| A — moteur 2 scénarios | `faisabilite/scenarios.py` (neuf), `faisabilite/engine.py` (+2 champs), `api/modules.py` (route), `lib/api.ts` |
| B — panneau maquette | `frontend/src/components/fiche/constructibilite.tsx` (`FaisabiliteTab` réécrit) |
| C — même partout | fiche `Fiche.tsx:1685` (déjà le composant partagé) ; export pré-dossier `api/pre_dossier.py` (`_regles_et_pieces`) ; copilote `copilote_v2/resume_fiche.py` (cite le moteur, 0 calcul) |
| D — non modélisé | `faisabilite/scenarios.py` (`_plu_section`) + tests |

**Exports** : le pré-dossier PC lit le même appel (`faisabilite_scenario`, scénario terrain libéré
par défaut) et l'écrit **en toutes lettres** (« Scénario retenu : terrain libéré… SDP jusqu'à ~N m²…
surface à démolir ~M m² à chiffrer »). Habitat interdit → « Logement non autorisé dans cette zone ».
Dossier expert / Flash lisent la capacité de la fiche (enveloppe = terrain libéré).

---

## Captures (6 témoins + états)

Base **dev** (`labuse` locale, 431 663 parcelles) : elle ne reproduit pas les chiffres de
production des témoins du mandat (ex. BZ1065 y ressort `terrain_exigu` — l'assiette gabarit se vide,
faute des données LiDAR/gabarit du run servi). Les captures sont donc prises sur des témoins **réels
de cette base** exerçant chaque comportement ; les payloads bruts du moteur sont dans
`captures/*.json` de session (voir aussi le tableau ci-dessous).

Dossier `captures/` :

| Fichier | Témoin | Ce qu'il montre |
|---|---|---|
| `1-terrain-libere-BE1505.png` | Le Tampon Ua (bâti 907 m²) | Verdict « Jusqu'à 1 117 m² · 11–14 logts », 2 cartes, « Ce qui limite », badges, PLU (articles+pages), 3 hypothèses, 8 étapes dépliées |
| `2-bati-garde-BE1505.png` | idem | **Scénario basculé** → « Encore 255 m² · 2–4 logts, bâti conservé » ; étape 5 « 862 m² conservés » |
| `3-test-ne-tient-pas-BE1505.png` | idem, bâti gardé | **Test « Ne tient pas »** (3 × 90 = 270 > 255 → il manque 15 m²) |
| `4-hypothese-recalcul-BE1505.png` | idem, terrain libéré | **Hypothèse modifiée** (occupation 45 → 70 %) → recalcul par le moteur (1 117 → 1 738 m²) |
| `5-nue-un-seul-scenario-BC0343.png` | Saint-Paul U4c (nue) | `bati_present=False` → **un seul scénario** (carte « bâti gardé » absente) |
| `6-habitat-interdit-AE0192.png` | Les Avirons AUt | **Habitat interdit** → message + citation ; test « non autorisé » ; PLU quand même servi |
| `7-a-cheval-BW0102.png` | Saint-Paul U6c | **À cheval** → « sur les 7 462 m² en U6c », portion constructible |
| `8-terrain-exigu-PLU-BZ1065.png` | Saint-Denis Uh | Terrain exigu (dev) MAIS **« Ce que le PLU permet » identique à la maquette** : 7 m faîtage · 4,5 m égout [Uh.10 p.73], emprise 30 % [Uh.9], reculs 3 m·4 m [Uh.6-7], mixité 15 % dès 30 logts [Uh.2] |

Le témoin BZ1065 confirme que la **section PLU rend exactement la maquette** ; seul le verdict diffère
en base dev (donnée gabarit absente), pas le comportement du panneau.

---

## Tests

- **Python** `tests/test_faisabilite3_scenarios.py` (**13 P**) : les deux champs de fourchette
  ajoutés ; terrain libéré (enveloppe + démolition) ; bâti gardé == résiduel servi (golden 55) ;
  bâti gardé ≤ terrain libéré ; nue → un seul scénario ; habitat interdit → message + test « non
  autorisé » ; AU non ouverte → 0 ; à cheval → portion ; test champs vides → « à compléter » ;
  tient / ne tient pas ; mixité non modélisée ; hauteur prospect non chiffrée ; garde « défaut ≠ PLU ».
- **Front** `frontend/src/components/outils/Faisabilite.test.tsx` (**9 P**) : verdict + « ce qui
  limite » + badges ; section PLU (article/page cliquable + mixité non modélisée) ; 3 hypothèses +
  reset ; 8 étapes repliées/dépliables ; bascule de scénario ; test « ne tient pas » ; aucun bouton
  IA ; ouverture outil + lien capacité.
- **Vérif globale** : `tsc` 0 · `vitest` **201 P** · `build` OK · `pytest` suites mandat
  (faisabilité/gabarit/résiduel/exports/copilote/pré-dossier) **409 P / 9 skip** (témoins absents de
  la base de test). **1 échec PRÉ-EXISTANT** hors mandat : `test_copilote2_outil::test_portes_concept_toutes_vivantes`
  (`_CONCEPT_MAP → « renouvellement »`, outil Densifier retiré ailleurs — présent sur `main`).

## Hors mandat (non touché)

Le scoring (le classement continue de lire `bati_garde`) · le calibrage PLU · les autres outils ·
le merge.
