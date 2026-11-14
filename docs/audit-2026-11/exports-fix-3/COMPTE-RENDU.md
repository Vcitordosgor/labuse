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
jamais le préfixe du nom). La sous-zone n'ouvre la constructibilité que si la portion est un **vrai bout de terrain : ≥ 50 m²
(aire absolue) ET non vide après ÉROSION de 3 m** (`ST_Buffer(-3)`). En deçà (nulle, éclat, ou ruban) la
parcelle reste sa zone dominante non constructible — **aucune capacité sans surface réelle bâtissable en
U/AU**. Au-delà, la capacité est calculée sur la **seule** portion U/AU, **bornée** à l'aire réelle
mesurée (`emprise` et `surface_assiette` `= min(…, uau_m²)`).

> **Révision 2 (revue) — érosion de 3 m contre les RUBANS.** Un seuil d'aire SEUL rouvrait un trou : un
> ruban de superposition de 1 m de large sur 100 m de limite fait 100 m², passe le seuil, mais n'a rien
> de bâtissable. Mesure île : sur les 10 417 parcelles A/N à U/AU ≥ 50 m², **1 119 sont des rubans**
> (vides après érosion de 3 m), dont **158** dans le sous-ensemble ≥ 50 m² / < 1 %. La porte exige donc
> aussi que la portion survive à une érosion de 3 m (`_uau_portion_reelle(uau_m2, uau_erode_m2)` ;
> `_uau_reelle` renvoie désormais l'aire érodée). Rubans → 0 ; vrais bouts (ex. CH0052 : 3 489 m²,
> érodé 1 462 m²) → conservés. Exemples rubans écartés : 97410000AX0059 (693 m², érodé 0),
> 97409000AX0918 (495 m², érodé 0).
>
> **Géométrie (limite connue, assumée).** Pour ces parcelles (zone dominante A/N → gabarit bloquant), la
> capacité est déjà calculée par le chemin legacy sur la **géométrie de la portion U/AU insetée des
> reculs** (`_EMPRISE` : `U/AU ∩ ST_Buffer(parcelle, -recul)`), pas sur la parcelle entière. La borne
> numérique `min(emprise, uau_m²)` ne sert que de **filet** pour le cas (non observé sur A/N dominant) où
> le moteur gabarit servirait la parcelle et sur-bâtirait ; elle est conservée et DOCUMENTÉE comme telle.

> **Révision (revue) — seuil ABSOLU, pas « ≥ 1 % ».** Un plancher à 1 % pénalise les grandes parcelles :
> **130 parcelles** A/N de 18 à 45 ha portent une vraie frange U/AU ≥ 150 m² mais < 1 % (281 au total
> ≥ 50 m² et < 1 %). Un gate « ≥ 1 % » leur retirait à tort une capacité RÉELLE (ex. 97411000CH0052 :
> 44,7 ha, 3 489 m² = 0,78 % → après révision, constructible, capacité sur ~1 048 m² d'emprise, pas sur
> 44 ha). Seul compte donc « ≥ 50 m² de vraie U/AU ? ».
>
> **Pourquoi « calculer sur la seule portion » ne suffisait pas seul :** deux chemins faisaient
> silencieusement retomber la capacité sur le TERRAIN ENTIER — (1) le clip legacy utilisait la part
> arrondie à 0,1 pt (`_pct_constructible`) : une frange < 0,05 % s'arrondissait à 0 % → le garde
> `0 < pct < 100` échouait → assiette = toute la parcelle ; (2) le moteur gabarit pouvait bâtir sur toute
> la parcelle (BI0351 : 24 437 m²). D'où la combinaison **garde d'aire réelle + borne stricte** à la
> portion mesurée (la borne ne peut que réduire, jamais augmenter).

Garde-fou complémentaire : si la zone dominante A/N n'est pas calibrée au PLU (`resolve_zone → None`) et
que l'éclat U/AU est écarté, on sert un verdict ferme « zone non constructible »
(`engine.faisabilite_zone_non_constructible`), jamais `None` (qui dirait « hors PLU ») ni la capacité
fantôme.

**Mesure** — classification **île entière** (SQL, 110 624 parcelles A/N dominantes) ; capacité AVANT/
APRÈS = **échantillon borné de 120 parcelles par classe** dans le calcul en direct (seam
`LABUSE_UAU_PHANTOM_GATE`, avant = 0 / après = 1) :

| classe (surface réelle U/AU) | parcelles A/N (île) | capacité AVANT (éch. 120) | capacité APRÈS |
|---|---|---|---|
| **nulle** (U/AU = 0) | 89 623 | **0** (aucune sous-zone à accrocher) | **0** |
| **éclat** (< 50 m²) | 10 584 | 92 / 120 (fantôme) | **0 / 120** |
| **≥ 50 m²** dont **ruban** (vide à -3 m) | 10 417 — dont **1 119 rubans** | — | rubans → **0** |
| **≥ 50 m²** dont **vrai bout** (survit à -3 m) | 9 298 | 106 / 120 | 106 / 120 (préservée, sur la portion) |

→ **classe « nulle » : zéro capacité avant comme après** ; éclats (< 50 m²) ET rubans (≥ 50 m² mais
vides à -3 m, 1 119 sur l'île) passent à zéro ; la capacité des **vrais** bouts U/AU (9 298) est
**préservée et bornée à la portion réelle**.

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
| d / j | HT0538 « 614 m² » & « capacité nulle » sur la même page | ✅ | la « Surface vendable » dit ce qu'elle mesure : « non chiffrée ici — surface de logements revendables, distincte de la surface de plancher (la SDP ci-dessus, un droit à bâtir) » (`exports/miroir` ; corrige aussi l'en-tête « reste à bâtir » masqué en LOT 2 suite) |
| e | Risque présent sur la fiche absent d'un autre document | ✅ | l'Analyse (`pige/api._risques_rows`) et la notice PCMI4 (`api/pre_dossier._pcmi4`) citent la zone inondable TRI (scénario extrême) et le système d'endiguement, lus de la cascade `fiche.lines` |
| f | DPU « rien à signaler » périmètre non vérifié | ✅ | présence testée **par commune** (`phase1.DpuLayer`, `couvre_commune`) |
| f | Taxe d'aménagement — assiette | ✅ | « surface taxable (… distincte de la surface de plancher) » (`api/pre_dossier`) |
| f | PLU « opposable » | ✅ | « opposable à la date des données LABUSE » + caveat mairie toujours porté (`api/app`) |
| g | Comparatif « dépasse le plafond d'emprise » | ✅ | « occupe déjà toute l'emprise constructible (gabarit après reculs) » — le taux est l'occupation du gabarit, pas le CES (`faisabilite/residuel` + miroir TS `frontend/src/lib/format.ts`) |
| g / m (#7) | Comparatif : bilans sans hypothèses ni dénominateur | ✅ | charge foncière « €/m² **de terrain** » + note sous le tableau donnant les hypothèses du bilan ; sans elles, pas de charge affichée (`exports/blocs/comparatif` + `app._compare_row`) |
| #4 (b/d) | Comparatif : zone rouge PPR + EBC dans la colonne contraintes | ✅ | contraintes majeures (PPR rouge, EBC) remontées en tête de la colonne (`app._compare_row`) |
| #5 (B1) | Bâti : une seule valeur = fiche | ✅ | non mesuré (trace aérienne) → « bâti détecté, à vérifier » dans l'Analyse ET le Comparatif ; nu → « aucun » ; mesuré → part (`app._compare_row` + `comparatif._bati_existant` + `pige/api`) |
| #6 (l) | HT0538 : prix terrain même étiquette que la fiche | ✅ | l'Analyse nomme son vrai périmètre « secteur élargi (voisinage) », distinct du « secteur cadastral » (section) de la fiche (`exports/blocs/annonce`) |

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

## Garde durable de promotion (LOT 1 #4)

`bascule_gardes.check_uau_erode_ruban` — « aucune parcelle A ou N avec capacité si sa portion U/AU
érodée de 3 m est vide ». Lecture seule du run matérialisé ; **bloquante** (ajoutée à la séquence de
`scripts/bascule_v8_calibre.py`, après `verify_completude`). Un run calculé par le moteur corrigé passe
à 0 faute. **Preuve** : sur le run servi actuel (q_v20, calculé avant correctif) la garde détecte
**256 parcelles** A/N avec capacité sur une portion U/AU érodée vide (ex. 97416000CV1495…) → `ok=False`,
promotion refusée. Tests : `_fautes_ruban` (pur — échoue sur un jeu d'essai {éclat, ruban, vrai bout})
et `check_uau_erode_ruban` (réel, détecte sur le run local).

## Documents régénérés (LOT 1 revue)

Cette revue ne change AUCUN des 8 documents des 3 parcelles de l'audit : BI0351 (éclat 0,09 m²) était
déjà écarté par le seuil d'aire et le reste par l'érosion ; DK0208/HT0538 inchangées. Les témoins de la
revue (rubans 97410000AX0059/AX0918 → non constructibles ; vrai bout 97411000CH0052 → capacité sur
~1 048 m²) sont vérifiés par le calcul en direct et les tests, hors des 3 parcelles.

## RELECTURE (2ᵉ passe) — le Dossier était manqué partout

Une relecture indépendante a montré que plusieurs faits corrigés dans les producteurs ne l'étaient pas
dans le **Dossier** (rendu par `exports/miroir`, qui lit ses propres extracteurs). Corrigés ET cités
dans `~/Desktop/exports-audit-4/AVANT-APRES.md` (§ RELECTURE, chaque ligne = phrase lue dans le PDF
régénéré) :

- **Dossier (3 parcelles)** : DPU « non ingéré pour cette commune — NON VÉRIFIÉ » (plus « rien à
  signaler » ; `robinet_fiche._c_dpu` teste la présence par commune + `miroir._r_dpu`) ; PLU « version
  servie par LABUSE … évolution publiée depuis au GPU non confrontée » (`miroir` statut PLU) ; taxe
  « surface taxable » (`miroir._r_taxe` + `blocs/commune`) ; bâti « Bâti détecté, à vérifier — 323 m²
  CoSIA » (plus « Parcelle non bâtie » ; `miroir`) ; PPR hors rouge « soumise aux règles de sa zone — en
  A/N reste non constructible » (plus « constructible » ; `servitudes._ppr_ligne`) ; **zone inondable
  TRI** ajoutée (registre `donnees.py` + `robinets.py` + `robinet_fiche._c_tri` + `risques.yaml` +
  `oracle_dossier`) ; 614 m² « surface de plancher estimée, hors stationnement et pleine terre ».
- **Taxe d'archéologie (ZIP)** : « assiette = surface TAXABLE » (`pre_dossier`). **PCMI4** : un aléa
  Géorisques hors zonage PPR dit « HORS zonage PPR — aucune prescription PPR opposable » (plus
  « prescriptions du règlement PPR »).
- **Étude de faisabilité** : le payload de régénération était erroné (`idu` au lieu de `idus`) → les 3
  disaient « au moins une parcelle requise ». Corrigé : BI0351 refus motivé (zone N), HT0538 étude
  (10 logements R+4), DK0208 refus motivé (441 m² bâtie saturée).
- **Comparatif** : hypothèses PAR bilan (une par colonne, étiquetée IDU) ; saturation nommée « surface
  de plancher autorisée consommée » (plus « occupe toute l'emprise », qui contredisait le Gabarit).
- **Analyse** : « Zone rouge · 31 % » une seule fois (plus répétée par aléa) ; prix terrain « secteur
  élargi (voisinage) » ; fibre « raccordable à proximité (≤ 100 m, pas sur la parcelle) » ; table « 8
  ventes » bornée aux 8 plus proches.

**Piège levé (durable).** La fiche est servie depuis un cache (`fiche_cache` L1 par worker + L2 en base)
dont la clé ne portait QUE la fraîcheur des données — un correctif de libellé STOCKÉ dans la fiche (ex.
le PPR « hors zone rouge », produit par `servitudes._ppr_ligne` et rangé dans `aleas.liste[].libelle`)
restait servi périmé. Ajout d'un jeton `_FICHE_CODE_REV` à la clé du cache. Ce jeton **se déduit seul de
la révision git déployée** (`git:<sha>` ; prod = checkout git sur le VPS) : tout nouveau commit invalide
le cache de fiche sans geste manuel. **Limite connue** : un déploiement sans `.git` (wheel) retombe sur
une constante de repli (`_FICHE_CODE_REV_FALLBACK`), à bumper à la main.

**3 derniers points (relecture 3) — faits ET cités :**
- Comparatif, parcelle non constructible : « (pas d'exclusion automatique) » n'est PLUS montré, MAIS la
  « zone rouge sur 31 % — vigilance forte » RESTE. Correction d'un bug de la passe précédente, signalé
  par le relecteur : le filtre retirait la contrainte ENTIÈRE (la zone rouge 31 % disparaissait de la
  colonne) ; il ne retire désormais que la clause rassurante (`comparatif._contraintes_txt` découpe sur
  « ; » et garde « zone rouge 31 % — vigilance forte »). Vérifié p.3 du PDF livré (0 « exclusion
  automatique », « zone rouge sur 31 % » présent). Le message partagé de la cascade n'est pas modifié.
- Dossier zone N : « Logement » sous conditions → « Logement : extension d'un logement existant
  seulement, sous conditions — voir le règlement de la zone » (`blocs/zonage._destinations`, famille A/N).
- Jeton de cache auto-déduit de git (ci-dessus).

**Non corrigé (hors mandat, à lister seulement)** : pages presque vides, carte du Comparatif, libellés
« revenu médian » / « surface réelle », exports `md`/`html` legacy, estimation « maison » sur 4 bâtiments.

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
- `i` Pré-dossier — checklist PCMI8 reflétant l'état réel de la pièce (`pre_dossier.py` liste statique).
- `p` Étude de zone « niveau de vie moyen » partout (`zone.py:171`, `etude_zone.py:242`, `rapport.html.j2`).
- `p` Pré-dossier « surface réelle » = contenance cadastrale, pas l'aire du dessin (`pre_dossier.py:662`).
- `d` Dossier — « Logement sous conditions » qualifié « extension d'habitation existante (art. N2.2) ».
- `C2` route legacy `/parcels/{idu}/export?format=md|html` (paliers / jargon) — non exposée par l'UI.
- `p` (confort) Analyse — borne du tableau « 8 ventes » (rendu non borné).

**Ce qui ne disparaîtra qu'avec un nouveau classement (bascule d'un run résiduel neuf) :** le champ
`parcel_residuel.cause = terrain_exigu` de BI0351 (et des ~10 865 parcelles « infime ») reste stocké dans
le run servi. Le verdict affiché au client est déjà corrigé À LA LECTURE (ordre des motifs, garde d'aire
réelle en direct). Mais les lecteurs SQL purs du run (tri/compteurs de listes, carte) continueront de voir
`terrain_exigu` jusqu'à un recalcul + bascule d'un run neuf — hors mandat (aucun run île lancé).
EXIGU-FIX-1 corrige déjà le libellé ; la bascule, elle, relève de la session de déploiement.

---

## Relecture finale (tour 6) — corrections de cohérence inter-documents

Même règle que les tours précédents : une seule formule par fait, lue par tous les documents.

1. **Analyse BI0351** — le commentaire de zone rouge n'est écrit qu'UNE fois. `pige/api._risques_rows`
   porte un drapeau `_premier_ppr` : la première ligne du PPR porte le commentaire d'implication, les
   lignes d'aléas suivantes (dont l'aléa faible) renvoient « Même zone … du PPR (voir ci-dessus) ; cet
   aléa y est pris en compte. » — plus de répétition sur la ligne de l'aléa faible.
2. **PLU de La Possession** — le 17/12/2025 est la date d'**approbation**, pas de publication.
   `exports/miroir._r_statut_plu` : « version servie par LABUSE, dernière approbation le 17/12/2025
   (une évolution publiée depuis au GPU n'est pas confrontée ici) ».
3. **VEFA neuf (Saint-Pierre)** — une seule période. `cascade/layers/fiche_couches4.py:78` : « (N ventes
   VEFA / 5 ans) », comme le Dossier (« commune, 5 ans ») ; l'étiquette « 36 mois » du Comparatif est
   supprimée (mêmes 158 ventes, une période).
4. **DPU (Saint-Pierre)** — une seule formule, celle du Dossier. `_attach_contraintes_signalees`
   interroge la présence du périmètre DPU **par commune** : une commune sans couche ingérée donne
   « Droit de préemption urbain (DPU) — non ingéré pour cette commune (non vérifié) », jamais un DPU
   « signalé » sur le terrain. L'Étude dit désormais ce que dit le Dossier.
5. **Étude HT0538 — garde-fou d'honnêteté (aucune correction de moteur)** :
   - **a.** quand le plancher de l'Étude dépasse la capacité servie par la fiche, le document l'écrit en
     clair et n'est jamais dit « exploitable » → « À vérifier ». `_attach_garde_fiche` attache la SDP de
     la fiche (`potentiel_batir.sdp_restante_m2`) ; `etude_faisabilite._gardes_honnete` rétrograde le
     statut affiché et imprime la raison.
   - **b.** barème de stationnement indisponible → « Stationnement non vérifié » (jamais « 0 place selon
     la règle du PLU »), et la conclusion n'est pas « exploitable ».
   - **c.** les risques de la fiche figurent dans l'Étude : zone inondable TRI et système d'endiguement
     (ils passent par la cascade, pas par `aleas_parcelle`) sont ré-attachés à §2.
   - **d.** plan page 6 : la section vient de l'IDU (`planche.py` `_g_zone_limites`), plus de « AW »
     codé en dur → « HT 538 » au contour comme au cartouche.
   - Les enrichissements (a–d) sont ré-attachés **à chaque export**, hors du cache de révision, pour
     qu'une révision stockée avant un correctif ne serve pas un libellé périmé.

---

## Point 6 — diagnostic en lecture seule : pourquoi l'Étude dit 888 m² et la fiche 614 m² (HT0538) ?

**Aucune correction de moteur dans cette branche.** Constat chiffré, mesuré sur le run servi et le
moteur d'étude le 14/11/2026 (parcelle `97416000HT0538`, Saint-Pierre, zone Ud, 510 m²).

| | Fiche / Dossier / Comparatif / pré-dossier | Étude de faisabilité |
|---|---|---|
| Source | `parcel_residuel.sdp_residuelle_m2` (run de nuit, Gabarit) | `implantation.service.etudier_payload` (recherche d'implantation) |
| **SDP** | **614 m²** | **887,5 m² (10 logements, R+4)** |
| Hauteur | `hauteur_source = « sans »` → **hauteur non modélisée**, repli prudent (≈ R+1/R+2) | lit la règle réelle du PLU : **15 m à l'égout / 20 m au faîtage → R+4 (5 niveaux)** |
| Emprise | CES 60 % à plat sur l'assiette : 0,60 × 510 × 2 ≈ 612 ≈ 614 | emprise après **reculs 3 m** (≈ 177 m²/niveau) × 5 niveaux ≈ 888 |
| Stationnement | non modélisé (sans effet sur la SDP) | **barème indisponible** → 0 place dessinée (aucune contrainte appliquée) |
| Pleine terre | non défalquée (CES à plat) | non défalquée du chiffre final |
| Nature du chiffre | `capacite_estimee = False`, `sous_densite = True` — **estimation de criblage, volontairement prudente** | **enveloppe maximale** recherchée, non validée |

**Lecture des règles, moteur par moteur :**
- **Hauteur — c'est l'écart décisif.** Le moteur de nuit n'a pas pu modéliser la hauteur pour cette
  parcelle (`hauteur_source = « sans »`) et retient un repli prudent (de l'ordre de 2 niveaux). Le moteur
  d'étude lit la hauteur réglementaire réelle (15 m à l'égout) et empile 5 niveaux (R+4). À emprise
  comparable, 5 niveaux contre ≈ 2 expliquent l'essentiel du 888 contre 614.
- **Emprise.** Le moteur de nuit applique le CES (60 %) à plat sur l'assiette ; le moteur d'étude part de
  l'emprise réellement disponible après reculs (3 m sur voie et limites), plus petite au sol mais empilée
  plus haut.
- **Stationnement.** Le barème de la zone n'est pas servi (`« document manquant — à confirmer »`). Le
  moteur de nuit ne le modélise pas ; le moteur d'étude dessine 0 place, ce qui ne retranche aucune
  capacité — d'où un chiffre non bridé par le stationnement.
- **Pleine terre (20 %).** Ni l'un ni l'autre ne la défalque explicitement du chiffre final.

**Lequel a raison ?** Aucun des deux n'est une capacité ferme « exploitable » :
- 614 m² est une **estimation de criblage prudente** (hauteur non modélisée → repli, CES à plat) : c'est
  le verdict servi partout ailleurs, délibérément conservateur.
- 888 m² est une **enveloppe maximale** qui lit la vraie hauteur mais **ignore un barème de stationnement
  indisponible** et ne défalque pas la pleine terre : elle **surévalue**.

La correction juste de cette branche n'est donc pas de trancher un chiffre (ce serait toucher au moteur),
mais d'**empêcher l'Étude de se dire « exploitable »** quand elle dépasse le verdict servi et repose sur
un barème manquant (garde-fou du point 5). La réconciliation des deux moteurs (modéliser la hauteur du
run de nuit, ou défalquer stationnement/pleine terre dans l'étude) relève d'un futur mandat moteur.
