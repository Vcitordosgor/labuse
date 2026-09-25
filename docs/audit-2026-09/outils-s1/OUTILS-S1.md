# OUTILS-S1 — Audit + corrections des outils Ensoleillement · Piscines · Densifier · Blocs fonciers

Branche `fix/outils-s1` · worktree `~/Desktop/labuse-s1` · base main `ce77ae8d`.
Question par outil : **données branchées ? l'outil dit-il la vérité ?** puis corrections décidées par Vic.
Vérifs base : `postgresql://openclaw@localhost:5432/labuse` (lecture seule, aucun calcul île — l'autre session tourne en parallèle). App bootée sur 8455/5655 pour les captures puis arrêtée.

Résultat global : **tsc 0 · vite build 0 · vitest 188/188 · pytest 49/49** (renouv/blocs/solaire), aucune rupture nouvelle.

---

## Lot A — Ensoleillement · VERDICT : JUSTE (rien de faux). Corrections : Estimé/Sourcé posés sur chaque fait.

Fiche soleil BZ1065 (`97411000BZ1065`, Saint-Denis). Source unique : `parcel_solar` (+ `p_model_bati`, `parcel_terrain`, `toiture_lidar`, `parcel_equipements`). Endpoint `GET /modules/prospection-solaire/parcelle/{idu}` (`api/modules.py:922`). Aucun recalcul au front, données GELÉES au relevé.

| Fait affiché | Valeur | Source (table.champ) | Millésime | Recompte | OK/écart |
|---|---|---|---|---|---|
| Potentiel | 1 548 kWh/kWc/an | `parcel_solar.prod_spec_kwh_kwc` (1548,38) | PVGIS v5.3 · SARAH3 · relevé 2026-08-23 | arrondi de 1548,38 | **OK** |
| Toiture (emprise) | 197 m² | `p_model_bati.emprise_bati_m2` (BD TOPO) | BD TOPO | — | **OK** |
| Puissance installable | 39,4 kWc | `toit_m2 × kwc_par_m2` (197 × 0,2) | ratio config `prospection_solaire.yaml` | 197 × 0,2 = 39,4 | **OK** (Estimé, hypothèse écrite) |
| Production annuelle | 60 991 kWh/an | `kwc × productible` (39,4 × 1548) | dérivé | 39,4 × 1548 = 60 991 | **OK** |
| Orientation du bâti | 65° | `parcel_solar.azimut_bati_deg` (65,1), confiance **basse** | run solaire | ST_OrientedEnvelope, axe long | **OK, plausible** (cf. ci-dessous) |
| Nature du toit | simple pente | `toiture_lidar.verdict` (LiDAR HD, seuil confiance 0,70) | LiDAR HD IGN | — | **OK** |
| Pente du terrain | 13,8° | `parcel_terrain.pente_moy_deg` (RGE ALTI) | RGE ALTI | — | **OK** |
| Pente du toit (médiane) | 22,2° | `toiture_lidar.pente_mediane_deg` | LiDAR HD IGN | — | **OK** |
| Profil mensuel | pic déc. | `parcel_solar.prod_mensuel` (12 val.) | PVGIS run | max = déc. (144,44) | **OK, attendu** (cf. A.2) |

### A.1 — Orientation 65° du bâti vs azimut du versant 301° : deux mesures différentes, les deux légitimes
- **65°** = `azimut_bati_deg` — orientation de **l'axe long de l'enveloppe orientée du bâti** (`ST_OrientedEnvelope`, géométrie BD TOPO). Confiance **`basse`** servie (toit irrégulier).
- **301°** (fiche parcelle) = **azimut du versant du terrain** (aspect de la pente du sol, RGE ALTI). Rien à voir avec le bâti.
- Ce sont donc **deux objets distincts** (le toit ≠ la pente du sol), et l'écran le dit déjà : « Pente du terrain ci-dessus = pente moyenne du sol (RGE ALTI), pas la pente du toit ».
- **Plausibilité sur l'ortho** (`captures/ortho_BZ1065.jpg`) : le bâti central gris a son **arête longue orientée NE–SW**, cohérent avec un azimut d'enveloppe ~65° (ENE). La confiance `basse` est justifiée (toit en L). → **Le 65° est plausible.** La rosace de la fiche l'aligne correctement.

### A.1 — « Sans signal » de l'en-tête : LU du scoring servi (pas fabriqué)
- En-tête fiche soleil : `commune · classement`. Le classement = `_classement_court(tier_v2, etage0)` (`api/modules.py:774`) → lit **`parcel_p_score_v2.tier`** (run v2 servi) + `dryrun_parcel_evaluations` (cascade servie), mappé par `TIER_LABELS`.
- « Sans signal » = **le palier d'opportunité commercial le plus bas du scoring servi** (pas une donnée solaire). Confirmé à l'écran (`captures/apres_ensoleillement_fiche.png` : « Saint-Denis · Sans signal »). **Branché, honnête.**

### A.2 — Profil mensuel = maille de la parcelle (pas la moyenne île), pic austral attendu
Trois parcelles espacées (`parcel_solar`) :

| Parcelle | Commune | lat | pic (mois_optimal) | potentiel | min annuel |
|---|---|---|---|---|---|
| 97424000AR0004 | Cilaos (hauts, sud) | −21,170 | **octobre** | 1 431 | juin (103,7) |
| 97410000BD0450 | Saint-Benoît (est) | −21,049 | **octobre** | 1 543 | juin (100,98) |
| 97411000BZ1065 | Saint-Denis (nord) | −20,885 | **décembre** | 1 548 | juin (106,21) |

- **Trois profils DIFFÉRENTS** → la donnée est bien à la **maille PVGIS (~400 m)**, pas une moyenne île. La fiche le DIT (« maille PVGIS ~400 m — commun aux parcelles voisines, pas une mesure au toit »).
- **Le pic en décembre est attendu à La Réunion** (été austral, latitude ~−21°) : le minimum est **partout en juin** (hiver austral). Physiquement correct. Nuance climatique captée : hauts/est (Cilaos, Saint-Benoît) piquent en **octobre** (avant la saison des pluies), le nord-ouest sous le vent (Saint-Denis) en **décembre**. Cohérent, pas un bug.

### A.3 — Correction livrée
- **Ajout des étiquettes `Estimé`/`Sourcé` sur chaque KPI de la fiche soleil** (`ProspectionSolaire.tsx`, composant `KPI` + `ProvTag`), même vocabulaire que la fiche parcelle :
  - **Sourcé** (mesuré/relevé) : Toiture (emprise) · Pente du terrain · Pente du toit (médiane).
  - **Estimé** (modélisé) : Potentiel PVGIS · Puissance installable · Production annuelle · Orientation du bâti · Nature du toit.
- **Aucun chiffre corrigé** : l'audit n'a trouvé aucune valeur fausse.
- Capture : `captures/apres_ensoleillement_fiche.png`.

---

## Lot B — Piscines · AUDIT + PROPOSITION (pas de refonte ici — mandat PISCINES-2 après validation).

### B.1 — Les sources : DEUX couches, jamais fusionnées

| Source | Table | Nombre | Millésime | Précision | En base ? | Dans le strip ? |
|---|---|---|---|---|---|---|
| **FLAIR** (servie par l'outil) | `parcel_equipements` (cols piscine) | **8 299** (7 821 conf. ≥0,80 · 478 incertaines) | BD ORTHO / Ortho Express RVB 20 cm 2025 · détection FLAIR | ~90,7 % annoncé (966 verdicts Vic) | oui | non (couche `parcel_equipements` servie via l'outil, pas une couche tuyau) |
| **Ancienne couche « piscines »** (carte) | `tuyau_piscines` (kind `piscine_cosia`) | **50 443** (probable 34 062 · confirmée 11 877 · rare 4 504) | CoSIA (IA 20 cm) 2025 | variable (voir B.2) | oui | oui — libellé `Piscines (CoSIA)` (`layers.ts:60`), rendu `module-piscine` goutte d'eau |

- La couche qui « montrait beaucoup plus » = **CoSIA** (`tuyau_piscines`, 50 443), pas BD TOPO/DGFiP/OSM. C'est une **détection IA de couverture du sol** (classe « Piscine »), pas un cadastre.
- **Détection FLAIR brute** : `ortho_detections` (type `piscine`, 19 899 lignes candidates ; la matérialisation servie `parcel_equipements` retient 8 299 après filtres juge_flair/probe/sur_bâti).
- **Doublons entre sources (jointure spatiale 5 m)** : sur 16 354 piscines FLAIR (`ortho_detections` conf ≥0,80), **16 335 (99,9 %) ont une piscine CoSIA à ≤5 m**. Inversement, **32 879 des 50 443 CoSIA (65 %) n'ont AUCUNE FLAIR à ≤5 m** — le surplus CoSIA.
- **Ont-elles été fusionnées ? NON.** Deux tables distinctes, deux pipelines, aucune table d'union. FLAIR ⊂ empreinte CoSIA spatialement ; CoSIA est le filet large et bruité, FLAIR le sous-ensemble propre.

### B.2 — La vérité (échantillon visuel honnête, réduit)
Faute d'un tirage exhaustif de 30+30 (coûteux, et **l'outil ne sera refait qu'en PISCINES-2**), échantillon réduit vérifié à l'œil sur l'ortho IGN (`captures/pool_*.jpg`), croisé avec les statistiques de surface :

- **FLAIR haute confiance** : `pool_FLAIRH_1` (18,9 m²) ✅ vraie · `pool_FLAIRH_2` (35,6 m²) ✅ vraie · `pool_FLAIRH_3` ✅ — 3/3 vraies piscines.
- **CoSIA « confirmée »** (médiane 26,6 m²) : `pool_COSIAC_2` (28,4 m²) ✅ vraie piscine. Fiable.
- **CoSIA « probable »** (médiane **4,5 m²**, **52 % < 5 m²**) : `pool_COSIAP_1` (0,6 m²) ❌ bâche/artefact bleu · `pool_COSIAP_2` (3,3 m²) ⚠ objet rond ambigu (spa/pataugeoire). **Bruit majoritaire.**
- Statistique clef : CoSIA `probable` = **17 859 détections < 5 m²** (spas, reflets, bâches). CoSIA `confirmée`/`rare` = tailles de vraies piscines.
- **Précision réelle** : FLAIR haute = élevée (échantillon 3/3 + 90,7 % annoncé) ; CoSIA `confirmée` = fiable ; CoSIA `probable` = **fortement bruitée**. ⚠ Les 815 `ok` / 804 `faux_positif` de `ortho_detections.validation` sont le **jeu de revue des cas LIMITES** (train/validation), PAS un tirage aléatoire — ne pas les lire comme la précision servie.

### B.3 — L'écran (constats)
- **Tri par potentiel solaire** (1 435 kWh/kWc…) : le listing porte une colonne « Potentiel solaire » et un tri « Potentiel », **sans rapport pour un pisciniste**. Le tri par défaut est `commune` (`ProspectionSolaire.tsx:118`), mais dans une commune unique (Saint-Paul) l'ordre retombe sur le potentiel — d'où l'impression de tri par potentiel. Métier faux pour l'usage piscine.
- **« pas une piscine »** : ce n'est pas du texte, c'est un **bouton de signalement** (`Bouton niveau="lien"`, `data-piscines-pas`). Il POST `/modules/prospection-piscines/pas-une-piscine` → **INSERT dans `piscine_corrections`** (idu, motif, compte_id) → **relu par tous les endpoints piscines** (`NOT EXISTS (… piscine_corrections)`) : retire la parcelle du compteur, de la carte et du listing. Table actuellement **vide (0 ligne)**. Écriture réelle en base, audit `compte_id`. Mécanisme sain — mais l'affichage « bouton déguisé en texte » est trompeur.

### B.4 — PROPOSITION (à valider par Vic → mandat PISCINES-2)

**Source unique fusionnée** `piscines` : `FLAIR ∪ CoSIA`, **dédoublonnée par jointure spatiale 5 m**, chaque ligne portant :
- `source` (`flair` | `cosia` | `flair+cosia` quand les deux concordent — la concordance vaut confirmation),
- `confiance` (haute / moyenne / basse), avec un **plancher de surface** (écarter le bruit CoSIA < ~8 m², i.e. les 17 859 « probable » minuscules),
- `idu`, `commune`, `surface_m2`, géométrie.
Règle : garder FLAIR haute + CoSIA `confirmée`/`rare` + concordances ; reléguer CoSIA `probable` isolée en « à confirmer » (non servie par défaut).

**Écran cible (5 lignes)**
1. **À quoi ça sert** : lister les **piscines à équiper** pour un client pisciniste — chauffage solaire, couverture/volet, PAC, entretien — pas du potentiel PV.
2. **Liste par commune** avec **propriétaire PM (dénomination + SIREN) / PP (non nommé)**, surface, source, confiance.
3. **Filtres** métier : commune, confiance, surface min, propriétaire PM/PP, « avec / sans équipement solaire déjà détecté ».
4. **Une couche carte** unique (la source fusionnée), goutte d'eau, cliquable → fiche.
5. **Signalement propre** : « Pas une piscine » = **chip** explicite (pas un lien-texte), écrit en base (`piscine_corrections`), retrait immédiat de la liste + carte, réversible.

---

## Lot C — Densifier l'existant · AUDIT + explication + branchement (transparence du run).

### C.1 — À quoi ça sert (5 lignes, exemple chiffré)
L'outil cherche les parcelles **déjà bâties en zone U** où il reste une **SDP résiduelle importante** — donc un potentiel d'**extension, surélévation ou division** sur du foncier déjà construit (pas du terrain nu). **Exemple : Le Port `97407000AS0101`** — un « ensemble bâti » de 14 477 m² en zone U qui conserve **17 949 m² de SDP nette** non consommée (score 99,5, rang 6/île) : un collectif/copro qui peut porter beaucoup plus. Différence avec **l'Analyse LABUSE** (qui classe TOUTES les parcelles, bâties ou nues, par opportunité commerciale) : Densifier ne regarde QUE le **bâti occupé à droits résiduels réels**. Différence avec le **filtre Capacité** : celui-ci filtre sur la SDP sans exiger le bâti existant ni le score de rotation ; Densifier ajoute le critère « déjà bâti » + une **heuristique de score** (percentile).
**Franchise** : sur le fond, Densifier ≈ « filtre Capacité **+ bâti existant** + score percentile ». Si Vic veut simplifier, il est pliable dans les filtres (comme « Par critères ») ; ce qui le distingue vraiment est le **score densif.** et le repère « déjà bâti ».

### C.2 — Branchement

| Question | Réponse |
|---|---|
| D'où viennent les 67 260 parcelles ? | Table **`parcel_renouvellement`** (précalcul), bâtie par le CLI **`labuse renouv`** (`renouvellement.py`). |
| Quand se rafraîchit-il ? | **Jamais tout seul** — doctrine d'injection sur clic humain (Vic lance `labuse renouv`). `computed_at` = **2026-09-14**, `run_label` = **`q_v11_m137`**. |
| Lit-il le scoring servi ? | **OUI** — tier v2 (`parcel_p_score_v2`) + étage 0 (`dryrun_parcel_evaluations`) scopés sur `runs.current()` = **`q_v11_m137`** = le run de scoring servi (`config/served_run.txt`). Aligné. |
| Lit-il `parcel_residuel` servi (run 10 / q_v15) ? | **NON.** La SDP (`sdp_residuelle_m2`, `sdp_nette_m2`) vient de **`p_model_ext_dataset`** (snapshot `max(annee)`, run-agnostique) + cascade, **pas** de la vue `parcel_residuel` (run servi 10 = « q_v15 assiette gabarit »). |
| « Score densif. » (percentile) ? | `percent_rank()` pondéré : **capacité résiduelle nette 47 % + assiette (surface) 29 % + rotation du bâti 24 %** (`renouvellement.py:240`, config `renouvellement.yaml`). Continu 0–100. |
| Pourquoi Le Port AS0101 au top ? | `code_bati_origine = ensemble_bati`, 14 477 m² en U, **17 949 m² SDP nette** (0 % contrainte), rang 6. Un **ensemble bâti** (collectif/copro) à gros droits résiduels — légitime pour surélévation/extension. |
| Tableau plein écran (`SDP nette`, `Surface`) = mêmes fonctions que la fiche ? | **OUI, cohérents entre eux** : le tableau ET le bloc « Renouvellement » de la fiche lisent la **même** table `parcel_renouvellement`. ⚠ Mais tous deux divergent de la **Capacité** de la fiche (qui lit `parcel_residuel` run 10) quand la géométrie q_v15 a modifié le résiduel. |

**Nuance clef** : le run de **scoring** servi est encore `q_v11_m137` (`served_run.txt`) ; le run **10/q_v15** est le run de **géométrie résiduelle** servi, non promu au scoring. Densifier est donc **aligné au scoring servi**, mais sa **SDP est un snapshot `p_model_ext_dataset`**, pas le résiduel run 10 de la fiche-Capacité.

### C.3 — Correction livrée (transparence + « pas un instantané figé »)
Bug latent trouvé : l'endpoint filtre `WHERE r.run_label = runs.current()`. Si une bascule fait avancer le run de scoring servi **sans relancer** `labuse renouv`, la requête ne renvoie **plus rien → l'outil se vide EN SILENCE**, tout en affichant une « maj » rassurante.
- **Backend** (`app.py` `/renouvellement/liste`) : expose désormais `run_precalc`, `run_servi`, `perime` (= précalcul ≠ run servi) et un `maj` de repli. Vérifié LIVE : `{total: 67260, run_label: q_v11_m137, maj: 2026-09-14, run_precalc: q_v11_m137, run_servi: q_v11_m137, perime: false}`.
- **Front** (`Renouvellement.tsx`) : la note affiche maintenant **« Analyse LABUSE · run q_v11_m137 · maj 2026-09-14 · 67 260 parcelles »** (le run LU, plus seulement la date) ; si `perime`, **bandeau ambre** explicite (« Précalcul du … run … — le run servi est désormais … relancez `labuse renouv` ») au lieu d'un tableau vide muet.
- **Pas de reconstruction de la table** : `labuse renouv` est un calcul **île entière** (interdit ici, session parallèle) et relève de l'injection humaine (Vic). La correction rend la fraîcheur **visible et honnête** ; le vrai réalignement sur run 10 reste un `labuse renouv` lancé par Vic.
- Capture : `captures/apres_densifier_panel.png`.

### C.3 — « Utiliser la parcelle sélectionnée (CV0441) » disait « pas dans le segment »
- **`CV0441` n'est dans `parcel_renouvellement` pour AUCUNE commune** (Saint-Louis/Saint-Pierre/Saint-Paul/Saint-Denis existent en cadastre mais aucune n'est dans le segment). → **Le message « pas dans le segment » est JUSTE** : la parcelle n'est pas du bâti occupé à capacité résiduelle réelle. Message honnête, confirmé avec la géométrie courante.

---

## Lot D — Blocs fonciers · AUDIT + corrections UI.

### D.1 — Vérité (recompte de 3 blocs)

| Bloc (Saint-Paul) | Parcelles | Surface | Résiduel stocké | Σ membres | Cohérence | Zones | run |
|---|---|---|---|---|---|---|---|
| **CBO TERRITORIA** | 118 | 278 ha (2 782 076 m²) | **323 345 m²** | 323 345 | **exact** | A AU2c AU2h Acu N… U2c U2e U2h | 2 |
| CBO TERRITORIA | 108 | 15,6 ha | 158 533 m² | 158 533 | exact | N U4a U4b U4c | 2 |
| CBO TERRITORIA | 29 | 42,5 ha | 83 609 m² | 83 609 | exact | A Acu N Ncu | 2 |

- **CBO Territoria = mandat confirmé EXACT** (118 parcelles · 278 ha · résiduel 323 345 m² · zones A AU2c AU2h Acu).
- **Bloc mixte A + AU : la zone A compte-t-elle 0 ?** OUI. `sdp_couverture = 118/118` : toutes les parcelles ont une valeur résiduelle, mais les parcelles **A/N (non constructibles) valent 0** ; le résiduel agrégé (323 345 m²) provient **uniquement des parcelles AU/U**. `résiduel = Σ parcel_residuel`, zone A à zéro. ✅
- **Run lu** : `residuel_run_seq = 2` (bâti 2026-09-07), **PAS le run servi 10 (q_v15)** — même famille de staleness que Densifier : le résiduel des blocs est Σ `parcel_residuel` **au run 2**, à réaligner par un `labuse blocs-build` (injection Vic). *(Noté, non corrigé — calcul île interdit ici.)*
- **Contiguïté** : `ST_DWithin(geom_2975, 0,5 m)` + union-find (`blocs.py`), même SIREN. Buffer 0,5 m (source unique `ADJ_BUFFER_M`, partagée avec l'Assemblage).
- **Voies** : une parcelle de voirie appartient à la commune (SIREN ≠) → elle **coupe** la contiguïté entre les parcelles qu'elle sépare (sauf contact ≤ 0,5 m). Les blocs traversés par une vraie route **sont donc scindés** — comportement attendu.

### D.2 — Propriétaires publics : DÉJÀ décochés par défaut (mandat basé sur un état périmé)
- `Blocs.tsx:134` : `inclurePublics = useState(false)` ; backend filtre `AND is_public = false` par défaut ; bandeau « **N propriétaires publics écartés** ».
- LIVE : **6 361 blocs privés servis · 4 864 publics écartés** (`captures/apres_blocs_panel.png`). Commune de Saint-Paul / EPF **n'apparaissent PAS** par défaut.
- **La case est déjà décochée par défaut** → **rien à corriger sur ce point.** La prémisse du mandat (« publics inclus par défaut, Saint-Paul n°2 ») était **périmée**. Signalé honnêtement.

### D.3 — Corrections UI livrées (décisions Vic) — `captures/apres_blocs_panel.png`
1. **Raccourci « Préparer les courriers » retiré** (pied bas-droite) — pont Courrier abandonné dans cet outil.
2. **« Détail et méthode » retiré** du coin bas-gauche. Son contenu (le regroupement · ce qu'il ne dit pas · les chiffres : surface/communes/zonages Sourcés, SDP résiduelle Estimée = Σ résiduels de la fiche) est **remonté dans le « i » de l'en-tête**.
3. **Cases à cocher par bloc retirées** (+ « Tout sélectionner ») : la sélection multiple ne servait **QU'au** Courrier (supprimé) → hors DA des autres outils, retirée entièrement (état `sel`, pont `idusCourrier`, import `Case` de la multi-sélection).
4. **Cartes de bloc lisibles** (composants charte) : **nom · résiduel Estimé · parcelles · surface · commune · zones · un seul bouton « Scan patrimoine → »**. (Le pont « Assembler → » reste dans le détail déplié — geste de drill-down, distinct de l'ancienne multi-sélection.)

---

## Vérification

| Contrôle | Résultat |
|---|---|
| `tsc --noEmit` | **0 erreur** |
| `vite build` | **exit 0** |
| `vitest run` | **188/188** |
| `pytest` (renouv/blocs/solaire) | **49/49** |
| Boot API 8455 + endpoints | 200 (renouvellement/liste nouveaux champs, blocs, solaire) — puis **API/vite arrêtés, ports libérés** |

## Captures (`docs/audit-2026-09/outils-s1/captures/`)
- `ortho_BZ1065.jpg` — plausibilité azimut 65° (arête NE–SW).
- `pool_FLAIRH_{1,2,3}.jpg` · `pool_COSIAC_2.jpg` (vraies) · `pool_COSIAP_{1,2}.jpg` (bruit CoSIA).
- `apres_ensoleillement_fiche.png` — étiquettes Estimé/Sourcé (Lot A) + « Sans signal ».
- `apres_densifier_panel.png` — note « run q_v11_m137 · maj 2026-09-14 » (Lot C).
- `apres_blocs_panel.png` — cartes nettoyées, pas de cases ni de pied, publics écartés (Lot D).

## Hors mandat (non touché)
Refonte outil Piscines (→ PISCINES-2 après validation B.4) · le scoring · les autres outils · reconstruction île de `parcel_renouvellement`/`parcel_blocs` (injection Vic) · merge.
