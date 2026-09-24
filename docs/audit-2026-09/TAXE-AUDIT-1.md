# TAXE-AUDIT-1 — L'outil Taxe d'aménagement : bien branché, chiffres justes, calcul juste ?

**Branche** `audit/taxe-audit-1` (worktree `~/Desktop/labuse-taxeaudit`) · lecture seule · base main `ea6feb72`
**Point de départ** page de l'outil sur **CO0322** (`97415000CO0322`, Saint-Paul, zone A), sauvegardée par Vic le 24/09.
**Méthode** lecture du code + recompte via `taxe_amenagement.calculer()` (la fonction que la page appelle) + lecture directe de la table des taux en base (psql, lecture seule) + vérification des valeurs légales 2026 contre Légifrance / service-public / BOFiP. L'API et le navigateur n'ont **pas** été lancés (le recompte au niveau de la fonction et de la base est plus probant qu'une capture).

---

## Verdict d'ensemble

**L'outil est juste, bien branché, et ses constantes 2026 sont exactes** — y compris le point qui a déclenché ce mandat. Le calcul est correct au centime sur les 4 cas testés. Le raccordement fiche → outil → Dossier financier passe par **une seule fonction** (`calculer()`), affichée à trois endroits. Les manques réels sont sur la **couverture juridique** (exonérations de plein droit, secteurs majorés, surface taxable ≠ SDP, RAP), pas sur l'arithmétique.

> ⚠ **La prémisse du mandat est fausse — et c'est la conclusion la plus importante de cet audit.**
> Le mandat pose : « 886 en 2023, 914 en 2024, 930 en 2025 — un 2026 à 892 est impossible ». **C'est l'inverse : 892 €/m² est la vraie valeur 2026.** 2026 est **la première année de l'histoire de la taxe où la valeur forfaitaire BAISSE** (930 → 892, **−2,4 %**), parce que l'indice du coût de la construction (ICC INSEE) a reculé d'environ **−4 %** entre le T4 2024 et le T4 2025. L'indexation n'est pas garantie à la hausse ; en 2026 elle est négative. **Rien à corriger sur cette constante.**

---

## 1. Les valeurs nationales — d'où viennent-elles, sont-elles celles de 2026 ?

**Source unique** : `config/taxe_amenagement.yaml` (config datée, `releve_le: 2026-08-28`), servie telle quelle à l'UI par `GET /outils/taxe-amenagement/config` (`app.py:2670`) et lue par `calculer()` (`taxe_amenagement.py:123`). Aucun montant n'est écrit en dur dans le front (vérifié : `TaxeAmenagement.tsx` lit tout de `cfg.data`).

| Ligne | Constante (fichier:ligne) | Millésime porté | Valeur légale 2026 | Verdict |
|---|---|---|---|---|
| Valeur forfaitaire hors IdF | `config/taxe_amenagement.yaml:21` `hors_idf: 892` | 2026 | **892 €/m²** | ✅ **JUSTE** |
| Valeur forfaitaire IdF (mémoire, non appliquée au 974) | `:22` `idf: 1011` | 2026 | **1 011 €/m²** | ✅ juste |
| Piscine | `:38` `piscine_m2: 251` | 2026 | **251 €/m²** (était 262 en 2025) | ✅ juste |
| PV au sol | `:39` `panneau_pv_sol_m2: 10` | 2026 | **10 €/m²** | ✅ juste |
| Éolienne (mât > 12 m) | `:40` `eolienne_mat: 3000` | 2026 | **3 000 €/mât** | ✅ juste |
| Stationnement extérieur | `:41` `stationnement_ext_place: 2928` | 2026 | **2 928 €/place** (était 3 052 en 2025) | ✅ juste |
| — plafond sur délibération | `:42` `stationnement_ext_place_max_delib: 5857` | 2026 | **5 857 €/place** | ✅ juste |
| Exonération petites surfaces | `:26` `exoneration_surface_min_m2: 5` | stable (CGI 1635 quater D, 1°) | **< 5 m²** | ✅ juste |
| Abattement 50 % | `:32` `taux_pct: 50` | stable (CGI 1635 quater H) | **50 %** | ✅ juste |
| — plafond 100 premiers m² RP | `:33` `plafond_m2_residence_principale: 100` | stable | **100 m²** | ✅ juste |

**Sources vérifiées (24/09/2026)** :
- **CGI art. 1635 quater H**, [Légifrance LEGIARTI000049641227](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049641227/) — texte **en vigueur depuis le 01/07/2026** (modifié par décret n° 2026-562 du 29 juin 2026) : la valeur est **« fixée forfaitairement à 892 € pour les communes situées hors de la région d'Île-de-France et à 1 011 € »** IdF. Légifrance réécrit le montant du code chaque année à l'indexation → la citation verbatim de la fiche de règle (`regles/taxe_amenagement_eur.py:32`) est **exacte**.
- **service-public.gouv.fr [A15416](https://www.service-public.gouv.fr/particuliers/actualites/A15416)** (daté 07/01/2026) : 892 €/m² hors IdF, 1 011 IdF, piscine 251, stationnement 2 928 (jusqu'à 5 857 sur délibération), PV au sol 10, éolienne 3 000, seuil 5 m². Indexation sur l'ICC INSEE T3 2025 (indice 2056).
- **ATD31** (agence technique départementale) « valeurs 2026 » : confirme 892 (−4,06 % ICC entre T4 2024 et T4 2025), piscine 251, stationnement 2 928/5 857.

**Ce qui s'est passé (l'alerte du mandat)** : la série est 820 (2022) → 885/886 (2023) → 914 (2024) → 930 (2025) → **892 (2026)**. La baisse 2026 est réelle et documentée par toutes les sources officielles. Le YAML l'a correctement captée (commentaire `:7` « À METTRE À JOUR au millésime » + `releve_le: 2026-08-28`).

**Étiquette « Valeurs 2026 — service-public.gouv.fr »** : conforme. Le millésime (`meta.annee: 2026`), la source et l'URL viennent tous du YAML, servis à l'écran (`TaxeAmenagement.tsx:354-356`). Rien d'inventé.

**Nuance documentaire mineure** (déjà consignée dans `regles/taxe_amenagement_eur.py:41-45`, « ERRATA ») : les **commentaires** du YAML inversent H et I (ils attribuent les valeurs forfaitaires à l'art. 1635 quater I et l'abattement à H, alors que c'est l'inverse). **Les valeurs, elles, sont exactes** — c'est un lapsus de commentaire, gravité nulle sur le chiffre servi.

---

## 2. Les taux locaux — 24 communes + département

**Table** `taxe_amenagement_taux` (DDL `taxe_amenagement.py:45`), **source** `data_sources` = jeu ouvert **DGFiP / application DELTA** `delta_deliberation_tam_17_01_23` (data.economie.gouv.fr), ingéré par `ingestion/taxe_amenagement_delta.py`, **relevé le 08/09/2026** (TAXE-AMÉNAGEMENT-1). Résolution : `taux_communal_public(db, idu[:5])`.

**Les 24 communes, lues en base ce jour (lecture seule)** — chacune porte sa `delib_date` et sa source DELTA :

| INSEE | Commune | Taux | Date d'effet | | INSEE | Commune | Taux | Date d'effet |
|---|---|---|---|---|---|---|---|---|
| 97401 | Les Avirons | 5 % | 01/01/2022 | | 97413 | Saint-Leu | 5 % | 01/01/2022 |
| 97402 | Bras-Panon | 5 % | 01/01/2022 | | 97414 | Saint-Louis | 5 % | 01/01/2022 |
| 97403 | Entre-Deux | 5 % | 01/01/2022 | | **97415** | **Saint-Paul** | **5 %** | **01/01/2022** |
| 97404 | L'Étang-Salé | 5 % | 01/01/2022 | | 97416 | Saint-Pierre | 5 % | 01/01/2022 |
| 97405 | Petite-Île | 3,5 % | 01/01/2022 | | 97417 | Saint-Philippe | 5 % | 01/01/2022 |
| 97406 | La Plaine-des-Palmistes | 5 % | 01/01/2022 | | 97418 | Sainte-Marie | 5 % | 01/01/2022 |
| 97407 | Le Port | 3 % | 01/01/2025 | | 97419 | Sainte-Rose | 1 % | 01/01/2022 |
| 97408 | La Possession | 5 % | 01/01/2022 | | 97420 | Sainte-Suzanne | 5 % | 01/01/2022 |
| 97409 | Saint-André | 5 % | 01/01/2022 | | 97421 | Salazie | 3 % | 01/01/2022 |
| 97410 | Saint-Benoît | 5 % | 01/01/2022 | | 97422 | Le Tampon | 5 % | 01/01/2022 |
| 97411 | **Saint-Denis** | **3 %** | 01/01/2022 | | 97423 | Les Trois-Bassins | 3 % | 01/01/2024 |
| 97412 | Saint-Joseph | 3 % | 01/01/2022 | | 97424 | Cilaos | 5 % | 01/01/2022 |

**Verdict** : **24/24 communes présentes**, toutes DEFINITIF, chacune sourcée (délibération DGFiP/DELTA) et datée. **Saint-Paul = 5 % depuis le 01/01/2022** ✅ (conforme à l'affichage outil). **Saint-Denis = 3 %** ✅ (conforme à la fiche). Aucun taux saisi à la main, aucun taux inventé (doctrine respectée). Les taux sont **plausibles** (1 % à 5 %, dans les bornes légales `[1;5]` de la part communale de droit commun).

**Secteurs à taux majoré (jusqu'à 20 %)** — ⚠ **manque structurel.**
- Le jeu DELTA porte les secteurs majorés au **grain parcelle** (colonnes `prefixe/section/parcelle` remplies). L'ingestion les **écarte volontairement** : le filtre ne retient que la ligne communale **générale** (`parcelle is null`, `ingestion/taxe_amenagement_delta.py:40-41`). `calculer()` n'a **aucune** logique de majoration sectorielle (`grep « majoré » = 0`).
- Conséquence : si une commune de l'île a délibéré un **secteur à équiper** à taux majoré, l'outil applique quand même le taux général et **sous-estime** la taxe sur ces parcelles. L'outil est aujourd'hui **aveugle** aux secteurs majorés. Aucun taux > 5 % n'est en base ce jour — mais on ne peut pas conclure qu'il n'en existe pas : on a filtré la source **avant** de regarder.

**Taux départemental — la contradiction affichée.**
- **Config** : `part_departementale_defaut: 2.5`, `part_departementale_confirmee_974: true` (`config/taxe_amenagement.yaml:52-53`) — confirmé par DELTA (ligne `zone_application=Départementale`), TAXE-AMÉNAGEMENT-1.
- **Fiche §Fiscalité** (`constructibilite.tsx:82`) : affiche `src = confirmé` (car `taux_departemental_confirme` = `part_departementale_confirmee` = `true`). → **« 2,5 % · confirmé »**. ✅ **C'est l'affichage juste.**
- **Résultat de l'outil** (`TaxeAmenagement.tsx:330`) : n'ajoute « , à confirmer » **que si** `!confirmee` → comme `confirmee = true`, le résultat affiche **« 2,5 % »** sans réserve, cohérent avec la fiche.
- **Champ de saisie de l'outil** (`TaxeAmenagement.tsx:252`) : le `hint` est une **chaîne codée en dur** « Plafond légal 2,5 % — à confirmer auprès du département. », qui ignore `confirmee`.

→ **La fiche a raison** ; le taux départemental 974 **est** confirmé (2,5 %, source DELTA). La mention « à confirmer » que voit l'utilisateur dans l'outil vient uniquement du **hint du champ de saisie**, un **texte résiduel** non mis à jour après TAXE-AMÉNAGEMENT-1. Deux affichages parce que le hint est statique alors que le résultat, lui, lit `confirmee`. **Gravité faible** (texte, pas chiffre), mais c'est bien une incohérence à réparer.

---

## 3. Le calcul

Recompte via `taxe_amenagement.calculer()` (la fonction exacte appelée par l'endpoint `GET /outils/taxe-amenagement`, `app.py:2720`) :

| Cas | Détail | Assiette | Communale | Départementale | **Total** |
|---|---|---|---|---|---|
| **1. CO0322 — 400 m² RP, com 5 %, dép 2,5 %** | 300 m² × 892 + 100 m² × 892 × 50 % = 267 600 + 44 600 | **312 200** | 15 610 | 7 805 | **23 415 €** ✅ |
| 2. 400 m² logement aidé | 400 m² × 892 × 50 % (abattement sur toute la surface) | 178 400 | 8 920 | 4 460 | 13 380 € |
| 3. 120 m² RP + piscine 40 m² + 2 places | 62 440 + 40×251 (10 040) + 2×2 928 (5 856) | 78 336 | 3 916,80 | 1 958,40 | 5 875,20 € |
| 4. 4 m² (< 5 m²) | « exonérée (CGI 1635 quater D) » | 0 | 0 | 0 | **0 €** ✅ |
| 4b. 4 m² + piscine 20 m² | surface exonérée, **piscine taxée** 20×251 | 5 020 | 251 | 125,50 | 376,50 € |

**Cas 1 reproduit le montant du mandat au centime : 312 200 → 15 610 + 7 805 = 23 415 €.** ✅ Le calcul est **juste**.

**Vérifications demandées :**

- **Surface taxable ≠ SDP** — ⚠ **conflation non signalée.** L'endpoint prefill (`app.py:2680`) ne préremplit **pas** d'office la surface taxable (décision recette OUTILS-FIX-2). Il sert la **SDP résiduelle** (`parcel_residuel.sdp_residuelle_m2`, `app.py:2701`) comme **repère « SDP au gabarit »** avec un bouton **« reprendre »** qui la **copie dans le champ « Surface taxable »** (`TaxeAmenagement.tsx:195-200`). Or la **surface taxable** (CGI art. 1635 quater H : espaces clos et couverts > 1,80 m, **garages et annexes inclus**) ≥ la **SDP** (qui exclut garages/annexes). Reprendre la SDP comme surface taxable **sous-estime** la taxe, et l'outil **ne dit nulle part que SDP ≠ surface taxable**. Le champ est éditable et rien n'est copié sans clic — mais le geste « reprendre » invite à confondre deux assiettes distinctes. **Gravité moyenne.**

- **Exonérations de plein droit — largement absentes.** L'outil applique **seulement** l'exonération < 5 m². Il **ignore** :
  - **bâtiments agricoles en zone A** (art. 1635 quater D) — **c'est précisément le cas de CO0322, en zone A** : une construction agricole y serait exonérée, l'outil facturerait quand même ;
  - **PLAI / logements locatifs très sociaux** : exonérés **de plein droit**, alors que l'outil ne connaît qu'une case « logement aidé » qui applique un **abattement 50 %** (correct pour du **PLUS**, mais **PLAI ≠ 50 %, c'est 0** → sur-taxation) ;
  - **reconstruction à l'identique** après sinistre (art. 1635 quater D).
  L'unique case « logement aidé » mélange deux régimes distincts (abattement vs exonération). **Gravité moyenne à forte** (au moins l'agricole zone A et le PLAI).

- **Ordre / arrondi.** Ordre **correct** : abattement dans l'assiette (`taxe_amenagement.py:155`) **puis** taxe = assiette × taux (`:194-195`). **Arrondi** : chaque poste et l'assiette sont arrondis à 2 décimales ; les parts sont arrondies à 2 décimales (cas 3 : 3 916,80 / 1 958,40) — **pas** à l'euro. En droit, la surface taxable s'arrondit au m² inférieur et le montant à l'euro ; écart cosmétique, **gravité faible**.

- **Redevance d'archéologie préventive (RAP)** — ⚠ **absente de l'outil ; présente ailleurs mais sur un autre régime.**
  - `calculer()` ne calcule **aucune** RAP (`grep « archéolog/RAP » dans taxe_amenagement.py = 0`). L'outil n'en parle pas.
  - Le **Dossier financier** (`exports/financier_bilan.py:130,156`) porte bien une ligne `redevance_archeologie` — mais calculée **`0,68 €/m² × surface de plancher`**, c.-à-d. le régime **au m²** (grands aménagements / études d'impact, code du patrimoine art. L524-7), **pas** le régime **0,40 % de l'assiette de TA** qui accompagne un permis de construire courant. De plus **0,68 €/m² est la valeur 2025** (2026 = **0,69 €/m²**, arrêté du 23/12/2025) → constante périmée. **Gravité moyenne** : la RAP la plus probable pour un promoteur (0,40 % de l'assiette, due en même temps que la TA) n'est ni dans l'outil ni dans le Dossier.

- **Modalités** (exigibilité 90 jours après la DAACT, deux échéances si > 1 500 €) : **non affichées.** Info manquante, **gravité faible** (l'outil est une estimation avant dépôt, pas un échéancier).

- **« Gabarit non calculable en zone A — saisissez la surface »** : **cohérent avec le résiduel.** Le prefill lit `sdp_residuelle_m2` du **run résiduel servi** (`app.py:2701`, vue M135) ; en zone A (non constructible) ce champ est `null` → `sdp_gabarit_m2 = None` → le hint bascule sur « Gabarit non calculable en zone {zone} — saisissez la surface » (`TaxeAmenagement.tsx:189-191`). C'est **le même silence** que le résiduel affiche (« SDP restante — zone non constructible »). Aucune SDP inventée. ✅

---

## 4. Raccordement

- **Fiche §Fiscalité → outil** : le bouton **« Taxe d'aménagement — Changer les hypothèses »** (`Fiche.tsx:1642`, composant `PorteOutil`) fait `setParcelPrefill(idu)` + `setModule('taxe-amenagement')`. L'outil s'ouvre donc **sur CETTE parcelle** ; son prefill résout `taux_communal_public(idu[:5])` → **le taux de SA commune** (Saint-Paul 5 %). ✅ Ouverture sur la bonne parcelle **avec le bon taux communal**.
  - **Fil de retour** : ⚠ **implicite seulement.** `selectedIdu` est préservé, mais il n'y a **pas de fil d'Ariane « ← retour à la fiche »** explicite comme sur d'autres outils. Fonctionnellement on retrouve la parcelle ; ergonomiquement le retour n'est pas nommé. **Gravité faible.**
- **Un calcul, plusieurs affichages** — ✅ **vérifié.** Tout passe par `taxe_amenagement.calculer()` :
  - **Fiche** : `_taxe_amenagement_block` (`app.py:4430`) appelle `calculer(surface=0)` → **taux seulement, jamais de montant** (RECETTE-8 : pas de projet saisi, pas d'euro inventé).
  - **Outil** : `GET /outils/taxe-amenagement` → `calculer(surface = saisie)`.
  - **Dossier financier** : `exports/builder.py:214-231` appelle **le même** `calculer(surface = surface_plancher du projet)` → seul endroit qui chiffre un montant. Origine tracée « prefill ».
  - Exports **pré-dossier PC / Dossier banquier** : lisent `f["taxe_amenagement"]` (sortie du même bloc fiche) via `robinet_fiche.py:441` et `oracle_dossier.py:69` (chemin `taxe_amenagement.taux_communal_pct`) — donc **la même source**, pas de recalcul parallèle.
  - → **Aucune réimplémentation du barème ailleurs.** La seule divergence de « montant » est voulue : fiche = taux, Financier = montant sur SDP projet.

---

## 5. Verdict — juste / faux par ligne

| Élément | Verdict | Source de la constante |
|---|---|---|
| Valeur forfaitaire 892 €/m² hors IdF | ✅ **JUSTE** (2026, baisse réelle −2,4 %) | YAML `:21` ← CGI 1635 quater H / service-public A15416 |
| IdF 1 011, piscine 251, PV 10, éolienne 3 000, stationnement 2 928/5 857 | ✅ justes (2026) | YAML `:22,38-42` ← service-public A15416 |
| Exonération < 5 m², abattement 50 % / 100 m² RP / logement aidé | ✅ justes | YAML `:26,32-33` ← CGI 1635 quater D & H |
| 24 taux communaux + Saint-Paul 5 % / Saint-Denis 3 % | ✅ justes, sourcés, datés | `taxe_amenagement_taux` ← DGFiP/DELTA |
| Taux départemental 2,5 % « confirmé » (fiche) | ✅ juste | YAML `:52-53` ← DELTA |
| Taux départemental « à confirmer » (hint champ outil) | ⚠ **texte résiduel** (le hint ignore `confirmee`) | `TaxeAmenagement.tsx:252` (codé en dur) |
| Calcul (assiette, abattement, parts, exonération < 5) | ✅ **JUSTE** au centime (4 cas) | `taxe_amenagement.py:calculer` |

**Manques classés par gravité :**

- **Forte** — Exonérations de plein droit ignorées : **bâtiment agricole en zone A** (le cas de CO0322) et **PLAI** (traité en abattement 50 % au lieu d'exonération) → sur-taxation possible ; reconstruction à l'identique absente.
- **Moyenne** — **Secteurs à taux majoré** (jusqu'à 20 %) : la source les porte, l'ingestion les écarte (`parcelle is null`), le calcul les ignore → sous-taxation possible sur secteur à équiper.
- **Moyenne** — **Surface taxable ≠ SDP** : « reprendre » copie la SDP dans le champ « surface taxable » sans dire que la surface taxable inclut garages/annexes → sous-estimation, non signalée.
- **Moyenne** — **RAP** : absente de l'outil ; dans le Dossier financier au régime **0,68 €/m²** (= régime au m², **valeur 2025 périmée**, 2026 = 0,69) au lieu du **0,40 % de l'assiette** attendu pour un permis.
- **Faible** — Hint départemental « à confirmer » résiduel ; fil de retour fiche→outil implicite ; arrondi au centime (droit = à l'euro) ; modalités d'exigibilité non affichées.

**3 recommandations pour TAXE-FIX-1 :**

1. **Exonérations de plein droit (art. 1635 quater D).** Ajouter au moins les cas structurants : **bâtiment agricole en zone A** (l'outil connaît déjà `zone_plu` via le prefill → proposer la case en zone A) et **scinder « logement aidé »** en *abattement 50 % (PLUS)* vs *exonération (PLAI)*. Sinon l'outil sur-taxe des projets exonérés — le cas de CO0322.
2. **Secteurs à taux majoré.** Ingérer aussi les lignes DELTA au grain parcelle (`parcelle is not null`) dans une table de secteurs, et appliquer le taux majoré quand la parcelle tombe dans un secteur délibéré. À défaut, **afficher honnêtement** « secteurs majorés non pris en compte » plutôt que de laisser croire à une couverture complète.
3. **Surface taxable + RAP.** (a) Sous « reprendre », dire en une ligne que **la surface taxable inclut garages et annexes** (≥ SDP). (b) Ajouter une ligne **RAP 0,40 % de l'assiette** dans l'outil (souvent due avec la TA) et corriger/aligner la RAP du Dossier financier (régime + millésime 2026).

---

## 6. Hors mandat (non fait)

Aucune correction, aucun autre outil, aucun export modifié, aucun merge. Audit lecture seule ; API et navigateur non lancés (recompte au niveau `calculer()` + base). Rapport committé sur `audit/taxe-audit-1`.
