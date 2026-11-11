# Gabarit réglementaire

Clé interne : `gabarit` (num M24) · composant : `frontend/src/components/outils/Gabarit.tsx` · endpoint(s) : `GET /outils/gabarit/{idu}` (écran) · `GET /gabarit/{idu}.pdf` (export PDF)

---

## 1. À quoi il sert, et pour qui

Il traduit, en dessin sur la carte et en quelques chiffres, **où** une construction peut être implantée sur une parcelle (zone restante après les reculs et les exclusions) et **jusqu'où** (hauteur, emprise maximales) — selon les règles du PLU, du PPR et des servitudes. Pour un conseiller/porteur de projet qui veut situer rapidement une enveloppe constructible « défendable » devant un règlement, sans la calculer à la main.

Règle affichée en tête du code (`Gabarit.tsx:14-20`) : l'outil ne sert **que** des règles sourcées — jamais de logements, d'étages, de surface de plancher, de coût, de valeur ou de « potentiel » (liste noire testée, cf. §7).

---

## 2. Le parcours

Un seul écran, dans le panneau de droite de l'outil.

1. **Saisie** — composant `EntreeParcelle` (`Gabarit.tsx:323`) : l'utilisateur tape une adresse/IDU **ou** clique une parcelle sur la carte. Une parcelle cliquée sur la carte (`selectedIdu`) est adoptée automatiquement (`Gabarit.tsx:248-252`).
2. **Appel** — `useQuery(['gabarit', idu])` appelle `getGabarit(idu)` → `GET /outils/gabarit/{idu}` (`Gabarit.tsx:260-265`).
3. **Résultat** — selon `res.status` :
   - **`ok`** (`Gabarit.tsx:393`) : la carte dessine le contour cadastral, les bandes de recul (ambre), les exclusions PPR (rouge), la **zone d'implantation** (vert) et l'emprise du bâti existant (gris). Le panneau affiche 4 tuiles (Zone d'implantation · Emprise maximale · Hauteur maximale · Surface parcelle), une ligne « Faîtage LiDAR sur la parcelle », la liste **Règles appliquées**, les puces **Non intégrées**, deux boutons (« Voir en 3D » / « Exporter en PDF ») et une phrase de contexte sur l'usage réel des permis.
   - **`incomplete`** (`Gabarit.tsx:369`) : seul le contour est tracé ; le panneau affiche la référence, la commune et le **motif** du calcul incomplet (ex. « limites non qualifiées »). Aucune métrique ni 3D.
   - **`inconstructible`** (`Gabarit.tsx:352`) : contour + verdict définitif + motif. Aucune enveloppe.
4. **3D** — bouton « Voir en 3D » : extrude la zone verte à la hauteur réglementaire, pose une pastille « Règle : X m » (`Gabarit.tsx:170-196`). Le volume est posé **à plat** (son sommet ne suit pas la pente), ce que l'écran dit via `terrainNote`.
5. **PDF** — bouton « Exporter en PDF » ouvre `GET /gabarit/{idu}.pdf` (même moteur, cf. §8).

---

## 3. Les données lues

Toutes les requêtes SQL sont dans `src/labuse/gabarit/builder.py` (le seul endroit où le réel entre) et `src/labuse/api/gabarit.py` (bâti existant).

| Donnée | Nom au catalogue | Table / config SQL réellement lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Géométrie + contenance parcelle | `Cadastre (API Carto PCI)` | `parcels` (`geom`, `geom_2975`, `contenance_m2`) — `builder.py:188-195` | PCI Parcellaire Express (DGFiP) « latest » | (non datée au catalogue) |
| Zone PLU (dominante + découpe) | `Urbanisme PLU/GPU (API Carto)` | `spatial_layers kind='plu_gpu_zone'` / `parcel_couche_intersection` via `zone_dominante` — `builder.py:215-243` | GPU/PLU par commune | par commune |
| **Règles chiffrées PLU** (emprise %, faîtage, égout, reculs voie/sép.) | (règlement PLU « validé » LABUSE — pas une source DB du catalogue) | **fichiers config** `config/plu_destinations/<insee>_<slug>.yaml` (`regles_zone`) + `config/plu_zonage.yaml` (`resolve_zone`), lus par `builder.py:248-293` | millésime par commune (`config/plu_millesimes.yaml`) | manuel |
| Classification des limites (voie/séparative) | `BD TOPO IGN` + `Cadastre (API Carto PCI)` | `spatial_layers kind='voirie'` + adjacence cadastre, via `classify_parcel_limits` (`limites.py`), millésime lu dans `data_sources` (`_bdtopo_millesime`, `builder.py:70-77`) | BD TOPO® V3 (IGN) | — |
| PPR zone rouge (exclusion) | `DEAL Réunion — PPR / aléas` | `spatial_layers kind='ppr'` + fonction `labuse_ppr_couleur` + `cascade_results` (verdict) — `builder.py:412-445` | PPR/PPRL approuvés 2011–2026 | — |
| SUP (servitudes d'utilité publique) | `Urbanisme PLU/GPU` / GPU-API Carto | `spatial_layers kind='sup'` (hors subtype `pm1`) — `builder.py:485-497` | (assiettes GPU) | — |
| Bâti existant (emprise) | `BD TOPO IGN` | `spatial_layers kind='batiment'` (`attrs->>'hauteur'`) — `gabarit.py:47-54` | BD TOPO® V3 (IGN) | — |
| **Hauteur bâti (faîtage mesuré)** | `LiDAR HD — MNH 50 cm (IGN)` | `batiment_hauteur_lidar.faitage_m` via `labuse_hauteur_lidar_m()` — `gabarit.py:42-45` | Survol 11/08–11/10/2023 | — |
| Ravine / trait de côte | `BD TOPO IGN` | `spatial_layers kind IN ('ravine','trait_de_cote')` — `builder.py:177-182` | BD TOPO® V3 | — |
| Verdict de constructibilité | (moteur `faisabilite.potentiel_batir`) | même robinet que la fiche — `builder.py:728-729` | dérivé | — |

**Point majeur :** les valeurs chiffrées du PLU (le cœur du calcul) ne viennent pas d'une table/API traçable mais de **fichiers YAML curés à la main par LABUSE** (`config/plu_destinations/*.yaml`, `config/plu_zonage.yaml`). Le code ne retient que les feuilles de statut `valide` ; une feuille `a_verifier`/`propose`/`absent` bloque ou passe en « non réglementé ».

---

## 4. Les calculs

Le moteur pur est `src/labuse/gabarit/engine.py` (`compute_gabarit`), alimenté par `builder.py`. Toutes les géométries passent en CRS métrique local 2975 pour les surfaces/buffers, puis reviennent en WGS84.

- **Zone d'implantation** (`engine.py:80-93`) : `parcelle − (union des buffers de recul) − (union des exclusions)`. Chaque recul = tampon (`line.buffer(setbackM)`) sur la limite classée. On ne garde que la part surfacique (`_as_polygonal`). Jamais `min(zone, plafond)` — la zone et le plafond d'emprise sont deux choses distinctes (`engine.py:8-9`).
- **Recul séparatif lié à la hauteur** (`builder.py:273-291`) : si la formule du règlement est « L ≥ h/2 » (ou h/3…), le recul retenu = `max(minimum sourcé, h_faîtage × fraction)` — jamais réduit au seul plancher. Si la hauteur de zone n'est pas validée, la formule passe en « non intégrée » (rien n'est inventé).
- **Plafond d'emprise** (`engine.py:107`) : `surface_parcelle × percent / 100`. Calculé **à part**. `None` (→ « Non réglementé ») si le règlement est muet et que ce silence est prouvé (`status='absent'`).
- **Surface parcelle** : contenance cadastrale si présente, sinon aire du dessin (`builder.py:193`). **Constante sensible :** `COALESCE(contenance_m2, ST_Area(geom_2975))`.
- **Ré-échelonnage de la zone** (`gabarit.py:143-148`) : l'aire `zoneImplantationM2` (calculée sur le dessin) est multipliée par `surfaceParcelleM2 / aire_dessin` pour tomber au m² près sur l'échelle « contenance » de l'outil Faisabilité (ex. AK0804 : 19 294 → 19 024 d'après le commentaire ; mesuré ici 19 286). La **forme** reste sur le dessin.
- **Déduction du bâti** (`builder.py:746-803`, `deduire_bati_de_zone`) : le bâti existant est découpé au contour puis **retranché** de la zone verte ; `zoneImplantationM2` devient la valeur après déduction, `batiDeduitM2` l'emprise retirée.
- **Hauteur** (`builder.py:323-380`) : le **faîtage** de la zone (`hf_m`) est servi si présent ; sinon l'**égout** (`he_m`, étiqueté « à l'égout », parfois « Estimé » si table graphique par secteur `builder.py:332-350`) ; sinon, prospect « L ≥ H » non chiffré → non intégré. Le faîtage alimente l'extrusion 3D.
- **Part exclue** (`engine.py:113-115`) : `aire_exclusion_dans_parcelle / aire_parcelle × 100`, arrondi entier ; > 50 % ⇒ bandeau « majoritairement inconstructible ».
- **Arrondis** : surfaces/hauteurs à 1 décimale (`_round`, `engine.py:33`) ; `batiDeduitM2` et aires de déduction à l'entier (`builder.py:795`) ; `pctPortionZone` à l'entier.

---

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| Zone d'implantation (m²) | `zoneImplantationM2` : parcelle − reculs − exclusions − bâti, ré-échelonnée contenance (`engine.py` + `gabarit.py:143`) | Sourcé (géométrie cadastre + reculs PLU config) |
| « après reculs · bâti déduit X m² » | `batiDeduitM2` (`builder.py:802`) | Sourcé (BD TOPO bâti) |
| Emprise maximale (m²) | `plafondEmpriseM2` = contenance × CES% (`engine.py:107`) | Sourcé (CES = config PLU) |
| « X % de la parcelle » | `empriseRule.value` lu de la règle PLU (`Gabarit.tsx:395-396`) | Sourcé (config PLU) |
| « Non réglementé » | `plafondEmpriseStatus='absent'` (silence prouvé du règlement) | Sourcé (absence prouvée en config) |
| Hauteur maximale (m) | `hauteurReglementaireM` = faîtage PLU (`builder.py:325`) | Sourcé (config PLU) |
| « X m à l'égout » | `hauteurEgoutM` (`builder.py:327`) | Sourcé (config PLU) |
| « Estimé — table graphique par secteur » | `hauteurEstimee=true`, égout de repli (`builder.py:332-350`) | **Estimé** (valeur de repli étiquetée) |
| « Non chiffrée · prospect L ≥ H » | `hauteurStatus='not_integrated'` (`builder.py:367-378`) | Sourcé (règle lue, non chiffrable) |
| Surface parcelle (m²) | `surfaceParcelleM2` = contenance cadastre (`builder.py:193`) | Sourcé (cadastre) |
| « dont X m² en zone … (Y %) » | `surfaceNote`/`pctPortionZone` sur parcelle à cheval (`builder.py:699-706`) | Sourcé (découpe PLU) |
| Faîtage LiDAR sur la parcelle (m) | max des `hauteur_m` du bâti, = **la valeur LiDAR unique de la parcelle** (`Gabarit.tsx:431`, `gabarit.py:44`) | Sourcé (LiDAR HD 2023) — mais **non rattachée à un bâtiment précis** |
| Règles appliquées (recul voie/sép., emprise, hauteur) | `appliedRules` (`engine.py:128-158`) | Sourcé (config PLU + BD TOPO) |
| Badge de zone (ex. « Uh ») / « mesuré » | `source.zone` ou source BD TOPO (`Gabarit.tsx:400-401`) | Sourcé |
| Non intégrées (Stationnement, Espaces libres, prospect…) | `nonIntegratedRules` (`engine.py:160-162`) | Sourcé (règle connue, non modélisée) |
| « permis délivrés … moitié de ce maximum (médiane sur 6 601 permis) » | Texte **codé en dur** (`Gabarit.tsx:493-494`), ratio médian 0,46/0,40 Sit@del post-PLU | **Estimé** (statistique figée, non recalculée à la parcelle) |

---

## 6. Les limites

- **Le PLU chiffré n'est pas « sourcé » au sens d'une donnée traçable** : c'est de la config YAML curée à la main. Toute erreur de saisie dans un YAML se propage silencieusement. Une zone non calibrée → « Calcul incomplet » (`builder.py:251-255`).
- **Faîtage LiDAR trompeur** : `labuse_hauteur_lidar_m(faitage_m)` renvoie **un seul chiffre par parcelle**, appliqué à **tous** les bâtiments (vérifié §9 : BZ1065 → 3 bâtiments tous à 10,3 m ; DH0076 → 107 bâtiments tous à 6,8 m). C'est le plus haut faîtage mesuré sur/au contact de la parcelle, qui peut venir d'un bâtiment voisin. L'outil l'assume (ne l'extrude plus en 3D, `Gabarit.tsx:164-169`) mais la ligne « Faîtage LiDAR » reste affichée comme valeur de parcelle.
- **Pas de SDP / logements / étages / coût** : hors mandat, jamais calculés.
- **3D à plat** : le volume ne suit pas la pente du terrain (`terrainNote`).
- **Découpage multi-CES non servi** : ≥ 2 zones constructibles distinctes → « Calcul incomplet » (`builder.py:227-230`).
- **Reculs ravine/littoral non chiffrés** : traités comme emprise publique, signalés « non intégrés » (`builder.py:611-616`).
- **Constat « enveloppe dépassée par le bâti »** : l'outil **ne compare jamais** le bâti existant à l'enveloppe réglementaire (commentaire `Gabarit.tsx:176-190`). Le bâti débordait surtout à cause d'un décalage base/gabarit (liseré de base masqué, `Gabarit.tsx:31-37`). La hauteur réglementaire et le faîtage LiDAR sont affichés **côte à côte sans jugement** « dépasse ». Sur AK0804/BZ1065 (cf. mémoire), le bâti réel dépasse la règle — l'outil ne le dit pas.

---

## 7. Les tests

- `tests/gabarit/test_engine.py` (≈ 25 cas) garantit le moteur pur : distinction zone ≠ plafond (`test_02`), zéros explicites valides, exclusion partielle/totale, **entrée non mutée** (`test_06`), géométrie invalide → incomplet, regroupement des reculs par ruleId (`test_19`), source absente/différente du catalogue refusée, CES absent servi « non réglementé », hauteur prospect non intégrée, et la **liste noire** `test_20_aucun_champ_estimatif` (aucun « logement/étage/sdp/coût/valeur/potentiel » dans la sortie).
- `tests/gabarit/test_builder.py` garantit le raccordement réel : parcelle inconnue, zone `propose`/non calibrée bloque, multizone (1 constructible servie / 2 bloque / tout A-N bloque), limites non qualifiées bloque, enclaves E1/E2, emprise publique par citation, PPR toujours présent, hauteur égout sans faîtage, faîtage prioritaire, SUP intersectante déduite.
- `tests/gabarit/test_limites.py` (classification voie/séparative), `test_plan_svg.py`, `test_enveloppe_predossier.py`.
- **Aucun test front** : pas de `Gabarit.test.tsx` trouvé — le rendu du panneau, les tuiles, la ligne faîtage LiDAR, les couches carte et la 3D ne sont couverts par **aucun test**.
- **Non vérifié par les tests** : la cohérence écran↔PDF de la SUP (cf. §8) ; le fait que le faîtage LiDAR puisse venir d'un voisin ; la phrase « 6 601 permis » (valeur figée en dur).

---

## 8. Les documents liés (PDF, exports)

Le PDF `GET /gabarit/{idu}.pdf` (`documents.py:160-186`) appelle `builder.construire_gabarit` (`exports/builder.py:483-543`) qui **lit le même moteur** (`build_gabarit_input` + `compute_gabarit`) puis **la même chaîne** (`appliquer_verdict_constructibilite`, `rescale_zone_contenance`, `appliquer_note_a_cheval`, `deduire_bati_de_zone`, `_bati_existant`). Les chiffres cœur (zone, plafond, hauteur, surface, bâti déduit) sont donc **identiques** à l'écran.

**Une divergence de source documentée :** pour les **SUP**, le PDF lit la liste des servitudes **de la fiche** (`_dispositifs_block`, `exports/builder.py:527-535`) et non la déduction géométrique du moteur, « parce que le moteur écrivait "Aucune SUP" là où la fiche sert "1 servitude PM1" ». L'écran, lui, affiche la SUP **déduite par le moteur** (`builder.py:502-506`). Écran et PDF peuvent donc présenter la couverture SUP différemment.

Si le calcul est incomplet/inconstructible, le PDF rend un **document de refus** propre (jamais une enveloppe), cohérent avec l'écran.

---

## 9. Trois cas rejoués

Sorties réelles de `curl http://127.0.0.1:7300/outils/gabarit/{idu}` (le serveur était en cours de démarrage au premier essai ; relancé après ~10 s).

**97411000BZ1065 — Saint-Denis, zone Uh** · `status=ok`
- surfaceParcelle 1 567 m² · zone d'implantation 734 m² (bâti déduit 160 m²) · emprise max 470,1 m² (30 % · integrated) · hauteur 7 m faîtage, 4,5 m égout.
- PLU lu : emprise 30 %, faîtage 7, égout 4,5, recul voie 3, recul sép. 4 (source « PLU — Saint-Denis »).
- Classification : 2 voies, 3 side, 2 rear, 1 arête résiduelle rattachée. PPR = SOFT_FLAG zone **bleue** (pas d'exclusion, `rouge=false`).
- Bâti : **3 bâtiments, tous `hauteur_m=10,3` (LiDAR)** → la ligne « Faîtage LiDAR 10 m » est une valeur unique de parcelle. Enveloppe 7 m < 10,3 m : **l'outil n'affiche aucune alerte de dépassement**.

**97409000AK0804 — Saint-André, zone UB** · `status=ok`
- surfaceParcelle 27 862 m² · zone d'implantation 19 286 m² (bâti déduit 0) · emprise **Non réglementée** (`absent`) · hauteur 14 m faîtage, 12 m égout.
- PLU : emprise `null`, faîtage 14, égout 12, recul voie 6, recul sép. 3 (source « PLU — Saint-André »).
- PPR = SOFT_FLAG **zone rouge sur 12 %** (`partExcluePct=12`, `rouge=true`) — « vigilance forte, pas d'exclusion automatique ». Non intégrées : Stationnement, Espaces libres. (La parcelle du briefing : faîtage 14/égout 12 confirmés, mais commune = **Saint-André**, pas Saint-André ≠ relevé « déjà vu ».)
- Bâti : 1 bâtiment, `hauteur_m=4,4` (LiDAR).

**97415000DH0076 — Saint-Paul, zone U2b** · `status=ok` (témoin « secteur sud » du briefing ; la DB le place à **Saint-Paul**, pas Saint-Pierre/Joseph — je le signale sans l'écarter : la parcelle existe et calcule.)
- surfaceParcelle 19 513 m² · zone d'implantation 12 645 m² (bâti déduit 4 725 m²) · emprise **Non réglementée** · hauteur 19 m faîtage, 15 m égout.
- PLU : faîtage 19, égout 15, recul voie 4, recul sép. 3 (source « PLU — Saint-Paul »). Classification : 1 arête **emprise publique** → double règle « Recul voie (emprise publique) » + « Recul voie ». PPR rouge sur 2 %. Non intégrées : Stationnement, Espaces libres, **Recul ravine/littoral**.
- Bâti : **107 bâtiments, tous `hauteur_m=6,8`** → illustre nettement que le faîtage LiDAR est une valeur unique appliquée à tout le bâti.

---

## 10. Tes doutes

1. **(Grave) Le faîtage LiDAR est une valeur unique de parcelle appliquée à tous les bâtiments.** La requête `SELECT labuse_hauteur_lidar_m(faitage_m) … WHERE idu=:i` (`gabarit.py:42-45`) renvoie **un seul chiffre**, recopié sur chaque bâtiment (DH0076 : 107 bâtiments à 6,8 m). Un conseiller pourrait croire que « 10 m » caractérise le bâtiment dessiné ; il peut venir d'un voisin. L'outil l'assume côté 3D mais la ligne « Faîtage LiDAR » reste affichée.
2. **(Grave) Le cœur chiffré du calcul vient de YAML curés à la main, pas d'une source traçable.** Emprise %, hauteurs, reculs sortent de `config/plu_destinations/*.yaml` / `config/plu_zonage.yaml`. Une erreur de saisie se propage sans filet ; le « sourcé » affiché est en réalité « transcrit par LABUSE ».
3. **(Moyen) Écran et PDF divergent sur les SUP.** Le PDF lit les servitudes de la fiche (`_dispositifs_block`), l'écran la déduction géométrique du moteur. La même parcelle peut afficher « Aucune SUP » à l'écran et une servitude dans le PDF (ou l'inverse) — aucun test ne verrouille cette cohérence.
4. **(Moyen) L'enveloppe peut être dépassée par le bâti sans aucune mention.** L'outil affiche hauteur réglementaire et faîtage LiDAR côte à côte sans jamais comparer (BZ1065 7 m vs 10,3 m). Le constat connu (BZ1065, AP1319) n'est pas restitué à l'utilisateur : il doit faire la soustraction lui-même.
5. **(Faible) La phrase « médiane sur 6 601 permis » est figée en dur** (`Gabarit.tsx:493-494`), ni recalculée ni rattachée à la parcelle, et non testée — elle vieillira sans que personne ne le voie.

---

## Synthèse INDEX

- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/gabarit.md`.
- Outil `gabarit` (M24) : `GET /outils/gabarit/{idu}` + PDF `GET /gabarit/{idu}.pdf`. Front `Gabarit.tsx`, moteur pur `gabarit/engine.py`, raccordement réel `gabarit/builder.py`, bâti `api/gabarit.py`.
- Calcul = parcelle cadastrale − reculs (buffers) − exclusions − bâti, plafond d'emprise à part (CES × contenance), hauteur = faîtage PLU, 3D extrudée à plat.
- Données lues : cadastre (`parcels`), zone PLU (`spatial_layers plu_gpu_zone`), PPR rouge (`spatial_layers ppr` + `labuse_ppr_couleur`), SUP, classification voie/séparative (BD TOPO + adjacence cadastre), bâti BD TOPO, faîtage LiDAR HD 2023.
- **Part sourcée vs estimée (estimation) : ~90 % sourcé.** Géométries et verdicts sont tracés en base ; **mais** les valeurs chiffrées du PLU (emprise, hauteurs, reculs) viennent de **fichiers YAML curés à la main** (`config/plu_destinations/*`, `config/plu_zonage.yaml`), pas d'une API/table. Seules 2 valeurs sont clairement « estimées » : hauteur de repli « table graphique » (étiquetée) et la phrase « 6 601 permis » figée en dur.
- 3 témoins rejoués (sorties réelles) : BZ1065 Saint-Denis Uh (zone 734 m², haut. 7/4,5, PPR bleu), AK0804 Saint-André UB (zone 19 286 m², haut. 14/12, PPR rouge 12 %, emprise non réglementée), DH0076 Saint-Paul U2b (zone 12 645 m², haut. 19/15, 107 bâtiments). Les 3 reclassent à Saint-André/Saint-Paul, pas les communes supposées du briefing — signalé.
- **Doute le plus grave :** le « Faîtage LiDAR sur la parcelle » est une valeur LiDAR **unique**, recopiée identiquement sur **tous** les bâtiments de la parcelle (ex. 107 bâtiments à 6,8 m) et pouvant provenir d'un voisin — présentée comme une mesure du bâti sans l'être.
- Tests : moteur et builder bien couverts (liste noire anti-estimatif incluse) ; **aucun test front**, et ni la divergence SUP écran/PDF ni le caractère unique du faîtage LiDAR ne sont testés.
