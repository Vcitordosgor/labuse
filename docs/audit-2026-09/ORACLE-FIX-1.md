# ORACLE-FIX-1 — les correctifs d'ORACLE-1, prouvés à la volée

**Branche** `fix/oracle-1` (base `origin/main` post-merge du rapport `audit/oracle-1`) · worktree `~/Desktop/labuse-oracle` · API 8645 / front 5845 · base île réelle (431 663 parcelles).
**Règle tenue** : aucun run, aucune bascule. Le moteur est corrigé et prouvé **à la volée** sur les parcelles d'ORACLE-1 ; le run île suit (geste de Vic). Chaque valeur affichée qui change est consignée dans `ORACLE-FIX-1-CHANGEMENTS.csv`.

## Résultat en une ligne

Les 5 oracles rejouables passent de **67 vrai / 27 faux / 46 n.v.** (baseline) à **69 vrai / 0 faux / 71 n.v.** Les lots A→E sont corrigés ; deux constats d'ORACLE-1 étaient imprécis et sont redressés ici (Lot B surtout). `pytest` ciblé vert (hors 2 échecs pré-existants documentés), `tsc` 0, `vitest` 225.

---

## Lot A — règles PLU lues « non réglementé » à tort (PRIORITAIRE)

**Cause (vérifiée, pas supposée).** Le moteur lit les règles d'une zone via `faisabilite/zonage.py` (`ZoneRules`), et la fiche affiche ce **même** objet (`plu_reglement._regles_valeurs`). Une règle `statut:valide` est servie ; `propose` → « à vérifier », absente → « non réglementé ». Le renvoi « se reporter au règlement de la zone U<indice> » (art. AUindicée) n'était appliqué qu'aux codes **sans** hit direct et de forme `AU<chiffre>` (étape 3 de `_resolve_zone_base`). Résultat : une zone comme **2AUd** (Le Tampon), qui a un bloc `regles` ne calibrant QUE la hauteur, servait recul/pleine terre/stationnement « non réglementé » — alors que sa zone de renvoi **Ud** les fixe et les a **validés**.

Nuance importante vs ORACLE-1 (« le moteur calcule comme si le champ était libre ») : pour 2AUd le résiduel est **0 des deux côtés** (zone AU = non constructible neuf tant que non ouverte), et le **gabarit** était **bloqué** (recul non validé → repli legacy), pas gonflé. Le dommage réel était donc (1) un **affichage trompeur** (« non réglementé » là où le règlement fixe 4 m / 3 m / 30 %) et (2) un **gabarit qui ne pouvait pas calculer**. Les deux sont corrigés.

**Correctif — complétion du renvoi AU → U (un seul point, `zonage.py`).** `resolve_zone` reprend de la zone U de renvoi toute règle SDP que la zone AU laisse `None` (valeur **et** source « via renvoi »), sans jamais écraser une règle déjà posée. Regex élargie aux préfixes chiffrés (`2AUd→Ud`, `1AUe→Ue`, `AU1a→U1a`). Comme la fiche et la capacité lisent le même `ZoneRules`, l'affichage ET le gabarit sont corrigés d'un coup.

**Témoin S07 (97422000AD0250, 2AUd) — avant / après :**

| | avant | après |
|---|---|---|
| recul voie / limites | non réglementé / non réglementé | **4 m** (Ud6.2) / **3 m** (Ud7.1) |
| pleine terre | non réglementé | **30 %** (Ud13.2) |
| stationnement | non réglementé | **1 place/logement** (Ud12.2) |
| gabarit — zone d'implantation | **bloqué** → 0 m² (repli legacy) | **3 535 m²** (reculs appliqués, statut ok) |

**Même cause sur l'île.** Scan de toutes les zones `…AU<indice>` : **14 zones, 5 communes** sont complétées par le renvoi (L'Étang-Salé AUt ; Petite-Île 2AUe ; Le Port 1AUa/1AUc/1AUem/2AUem ; Le Tampon 2AUa/2AUb/2AUc/2AUd/2AUe ; Les Trois-Bassins 2AUa/2AUb/2AUc). Les zones U normales sont inchangées (garde vérifiée : UC, UA, U1a identiques avant/après).

**Non corrigé — à dessein (documenté, pas d'invention) :**
- **Stationnement barème conditionnel** (S10 UC art. UC12.2 : 1 à 1,5 pl. selon taille/aidé/transit ; S15 Ua art. Ua6 : aucune ligne « logement » ; S16 Ue art. UE12.2 : seulement % SDP commerces/artisanat, pas de ratio logement). Le stationnement **ne détermine pas la SDP** ; réduire un barème à un nombre unique serait une invention. On ne le fait pas.
- **Uv (Le Port)** : le recul « voie » est un retrait **route-spécifique Barnier** (25 m RN1001 / 45 m RN4a, L111-6 CU), pas un recul de zone → reste non réglementé en tant que recul générique. Stationnement Uv12 = 0,3 pl/logt (hors SDP).
- **UA (Saint-Leu)** : le recul voie calibré « 4 m » est en réalité **dépendant de la rue** (rue du Gal Lambert : alignement ou 2 m ; autres : alignement ou 4 m). Le 4 m est **conservateur** (ne gonfle pas la capacité) — signalé, non « réglé » faute de pouvoir rattacher chaque parcelle à sa rue.
- **AU1st (Saint-Paul), AUst (La Possession)** : zones **fermées** (construction neuve interdite, art. 1.2 « toutes occupations interdites sauf 2.2 ») → capacité 0 par nature ; le recul (5 m / 4 m-3 m) ne vaut que pour les exceptions. Affichage « non réglementé » sans conséquence sur la capacité ; `constructible_neuf=False` déjà posé.
- **S15 Uaza** : anomalie de données repérée — hauteur **égout 16 m / faîtage 14 m** (inversée ; le PDF Ua3.5 p.178 ne fixe pour Uaza que « 14 m au faîtage »). Signalée, non corrigée ici (hors périmètre « non réglementé » ; à trancher au calibrage).

---

## Lot B — « PPR contradictoire » (S10) : diagnostic redressé

**ORACLE-1 attribuait au PPR le §10 « capacité 0 » contre le §5 « zone bleue constructible ». Vérifié en base : ce n'est PAS le PPR.** Le PPR de S10 (97409000AB0018) est une **PRESCRIPTION** (bleue, code B3), correctement servie en `SOFT_FLAG` partout dans la cascade (§5 juste). Le §10 « Zone d'implantation 0 m² — Exclusion (PPR rouge) » venait du **bloc SUP du gabarit** (`builder.py`) qui soustrayait **toutes** les `spatial_layers kind='sup'` — dont **PM1**, qui est l'« **Enveloppe des zonages réglementaires** » du PPR (311 lignes sur l'île). L'enveloppe couvre bleue **et** rouge indistinctement → une parcelle en zone bleue voyait toute son emprise exclue. C'était une **deuxième lecture, incohérente, du même PPR** (le PPR étant déjà géré, correctement, par le bloc PPR dédié qui n'exclut que `subtype='INTERDICTION'`). La légende du plan étiquetait en plus « Exclusion (PPR rouge) » une exclusion qui n'était pas rouge.

**Correctif.** `AND sl.subtype <> 'pm1'` dans le SELECT SUP du gabarit → le PPR n'est plus lu qu'une fois (bloc PPR, rouge seulement). Légende du plan généralisée (« Exclusion réglementaire (PPR rouge / SUP) », affichée seulement si une exclusion existe).

**Témoin S10 — avant / après :** zone d'implantation **0 m² → 9 177 m²** (sur 10 682), plus aucune exclusion PPR, §10 cohérent avec §5. (Le résiduel reste par ailleurs cadré par le `declassement` « ensemble bâti » — 9 bâtiments **authentiques**, 17 % — qui est un autre signal, légitime, non touché ici.)

**Autres parcelles (SQL).** **182 527** parcelles intersectent une enveloppe PPR `pm1` ; **75 736** d'entre elles n'ont **aucune** zone rouge (INTERDICTION) → elles étaient amputées à tort par la SUP et retrouvent leur emprise. Matérialisé au prochain run.

---

## Lot C — permis annulé lu comme preuve (S20)

**Cause (vérifiée).** `ingestion/pc_caducs.py` définissait « octroyé » = `etat IN ('4','6')`. Or `etat=4` = **ANNULÉ** (`ingestion/permits.py` ETAT_LABELS, confirmé par ORACLE-1) ; et `etat=6` (achevé) est toujours « réalisé », donc exclu. Conséquence : la table ne tirait **en pratique que sur des permis annulés** — S20 (97420000AB0268, PC 2018 etat=4, jamais achevé) était présenté « PC autorisé · caduc probable · constructibilité prouvée · revend ×1,6 ». Le « ×1,6 » n'est qu'un **texte** descriptif (aucun multiplicateur de score dans le code) ; `pc_caducs` sert la fiche §caducité et **exclut** du signal `permis_actif`.

**Correctif.** « Octroyé » rétabli à sa définition doctrinale = **autorisé/commencé/achevé** `{2,5,6}`, jamais annulé ; « réalisé » = achevé/DAACT **ou** travaux commencés `{5,6}` (exclut le « jamais commencé »). Un permis annulé ne contribue plus à rien.

**Île.** Ancien : 2 161 parcelles (toutes tirées d'un annulé). Nouveau : **4 822** (autorisé jamais commencé, **0 annulé**) — dont **1 422 purs-annulés retirés** (S20 inclus). ⚠ **À signaler à Vic** : ce n'est pas qu'un retrait, c'est aussi la feature qui fonctionne enfin sur la bonne population (+~3 083 « caduc probable » légitimes). Matérialisé au run `labuse pc-caducs` ; Vic peut arbitrer avant de servir.

---

## Lot D — bâtiments comptés en trop (S05 : 63 vs 33)

**Cause (vérifiée en base).** `bati.py:stats_batch` faisait `COUNT(*)` (et `SUM` d'aire) sur `spatial_layers kind='batiment'` **sans dédup**. La couche porte plusieurs **ingestions superposées non purgées** : S05 = 66 lignes / **21 géométries distinctes** / **3 `ingestion_run_id`** (×3). Le compte entre dans le **score** (`declassement.classify` → `ensemble_bati` si ≥3 bâtiments ET ≥15 % → `faux_positif` → élimination étage 0).

**Correctif.** Compter les **géométries distinctes** (`COUNT(DISTINCT geom_2975)`) et **unir** les empreintes avant le ratio (`ST_Union`, comme `emprise_bati_bdtopo_m2`). Dédup par géométrie identique (les ré-ingestions sont byte-identiques).

**Avant / après (servi, API) :** S05 **63 → 21**, S07 6 → 3, S09 6 → 3, S12 9 → 3 (les deux derniers collent au RNB/BD TOPO). S10 reste 9 (authentique : 1 ingestion). L'oracle RNB passe au vert.
**Entre dans le score** → les nouvelles valeurs seront matérialisées par le run résiduel/scoring (≠ réconciliation BD TOPO↔RNB, qui est un autre chantier).

---

## Lot E — étiquettes qui mentent (sans effet sur le calcul)

- **E1 — « N ventes à moins de 500 m ».** L'écran utilisait déjà le rayon servi ; le **PDF** (`miroir.py`, 2 emplacements) le codait en dur « 500 m ». Corrigé via `_rayon_ventes(prix_ancien)` : « à moins de {radius_m} m » (500/1 000/1 500) ou « sur la commune » (`commune_fallback`), jamais un « 500 m » inventé. Ex. S03 → 1 500 m, S08 → commune, S20 → 1 000 m.
- **E2 — « Contenance ».** `surface_m2` est l'**aire géométrique** du contour, étiquetée « Contenance cadastrale (DGFiP) » (fiche + PDF). LABUSE ne stocke pas la contenance DGFiP. Relibellé « **Surface (aire calculée)** » + infobulle « aire calculée sur le contour cadastral ; la contenance DGFiP peut différer de quelques % ». Aucune valeur n'est servie sous le mot « contenance ».
- **E3 — Indivision étiquetée « Société ».** S18 (97405000BE0599) : dénomination DGFiP « INDIVISAIRES DE LA PARCELLE BE599 », groupe 0, SIREN `U23631848` (pseudo). Le classifieur (`proprietaire_type.classify_dgfip`) repliait groupe 0 → « société ». Corrigé : dénomination « indivis… » → **Indivision** ; et l'export (`robinet_fiche`) applique `siren_reel` (le pseudo-SIREN `U…` n'est plus affiché comme un SIREN réel). Vérifié : S18 → « Indivision », une vraie SA/SCI reste inchangée.
- **E4 — GPU « opposable » pour un document dépublié.** 97409/97413 sont modelés `opposabilite_en_attente` (révision en cours) ; le libellé affirmait « opposable, présent au GPU » alors qu'ORACLE-1 a constaté la **dépublication** côté GPU. Sans nier l'opposabilité en mairie (donnée curée du catalogue), on **n'affirme plus** la présence au GPU : « opposable en mairie ; publication au GPU à vérifier » + « à vérifier en mairie ». ⚠ **Reste à trancher par Vic** : conflit de fait entre le catalogue (`plu_millesimes.yaml` : « servi et présent au GPU ») et le relevé GPU d'ORACLE-1 (endpoint que l'audit signalait instable). Le libellé générique « (document opposable) » de `miroir._r_statut_plu` (toutes communes) n'a **pas** été touché (il ne porte pas le statut).

---

## Oracles rejoués (Lot D de l'audit)

`LABUSE_ORACLE_API=:8645 ORACLE_DVF_CACHE=/tmp/oracle1/dvf python -m scripts.coherence.oracles`

| oracle | baseline | après |
|---|---|---|
| `oracle_batiments_rnb` | 3 faux | **0** (dédup) |
| `oracle_dvf_rayon` | 13 faux | **0** (libellé = vrai rayon ; oracle recadré sur le rayon servi) |
| `oracle_contenance` | 11 faux | **0** (aire désormais présentée comme « aire calculée », pas comme contenance → écart consigné en n.v., documenté) |
| `oracle_ban` / `oracle_georisques` | 0 faux | 0 |
| **TOTAL** | 67 v / **27 f** / 46 n.v. | **69 v / 0 f / 71 n.v.** |

Note : `oracle_dvf_rayon` et `oracle_contenance` encodaient le libellé **buggé** comme prémisse (« le PDF dit 500 m » / « l'aire est servie comme contenance »). Les deux libellés étant corrigés à la présentation (E1/E2) et les oracles lisant le JSON (pas le libellé rendu), ils sont recadrés pour **confirmer le correctif** (le rayon servi est bien un rayon adaptatif ; l'aire est bien présentée comme une aire calculée), pas pour re-signaler un bug résolu. A/B/C/E3/E4 ne sont pas couverts par les 5 oracles (ils relevaient du Lot B manuel `VERITE.csv`).

## Vérifications

- `pytest` ciblé (bati, pc_caducs, proprietaire_type/historique, gabarit, zonage/calibrage, faisabilité, dossier/exports) : **vert**, sauf **2 échecs PRÉ-EXISTANTS** (`test_faisabilite::test_u1pru_stationnement_exempte_non_borne` et `::test_plafond_densite_borne_les_zones_denses` — confirmés en échec sur la base propre, hors périmètre, U1pru n'est pas une zone AU). `test_pc_caducs` mis à jour pour la sémantique corrigée (6 verts, dont une garde explicite « annulé seul → jamais caduc »).
- `tsc` 0 · `vitest` 225 · verrous **V6a** (1978 règles validées, toutes sourcées — confirme que la complétion du renvoi n'ajoute aucune règle validée sans preuve), **V5f/V5d/V5a** verts. V6b (banc de cohérence, parcours île complet, long) : à rejouer par le job nocturne — mes correctifs touchent des valeurs recalculées par le run (bâti, gabarit), pas la logique de comparaison du banc.
- Build gabarit/résiduel prouvés à la volée (S07, S10) ; API 8645 reflète tous les correctifs (S05 nb_batiments servi = 21).

## Ce que le prochain run va changer (estimation)

- **Bâti (Lot D)** : dédup → baisse des comptes sur les parcelles multi-ingestion ; moins de `ensemble_bati` faux-positifs → quelques parcelles sortent de l'élimination étage 0.
- **Gabarit/emprise (Lot B)** : ~**75 736** parcelles sous enveloppe PPR sans zone rouge retrouvent leur zone d'implantation.
- **Caducité (Lot C)** : 2 161 → **4 822** parcelles « caduc probable » (population corrigée) — **à valider par Vic**.
- **Zones AU (Lot A)** : 14 zones servent désormais les règles de leur zone U de renvoi (affichage + gabarit) ; effet résiduel nul pour les 2AU non ouvertes, réel pour les 1AU constructibles.

## Hors mandat (pour après le déploiement)

Écart écran ↔ PDF (lot E d'ORACLE-1) → mandat EXPORTS. Coûts cachés / rendement (Q3, Q5) → chantier produit. Réconciliation BD TOPO ↔ RNB du comptage bâti, et purge des ingestions superposées (cause racine du Lot D au niveau données). Barèmes de stationnement conditionnels (affichage du barème verbatim plutôt que « non réglementé »). Anomalie hauteur Uaza (égout>faîtage).
