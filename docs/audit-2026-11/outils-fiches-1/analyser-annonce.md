# Estimer un bien

Clé interne : `analyser-annonce` (num N1) · composant : `frontend/src/components/outils/AnalyserAnnonce.tsx` · endpoints : `POST /radar/annonce/analyser` (chemin lien), `GET /radar/annonce/estimation/{idu}` (chemin adresse), `GET /radar/annonce/classement/{idu}`, `GET /radar/annonce/rapport/{idu}`, PDF `/analyse-annonce/{idu}.pdf` (adresse) et `/analyse-annonce.pdf?url=…` (lien).

> Note de nommage : le mémoire du mandat parlait de `pige/estimer3.py` ; ce fichier **n'existe pas** dans ce worktree. Le cœur de l'estimation vit dans `src/labuse/pige/api.py` (`estimation_annonce`, l. 1902) et `src/labuse/marche_service.py` (`comparateur_bien`, l. 406 ; `comparateur_terrain`, l. 580). `src/labuse/estimation_prix.py` ne contient que des helpers de **mise en forme** (fourchettes, arrondis, €/m² FR), pas le calcul.

L'outil a **deux chemins** (l'écran d'entrée les tient tous les deux, `AnalyserAnnonce.tsx` l. 556-570) :
- **Chemin A — ADRESSE** : on choisit une parcelle (omnibox / clic carte) → rapport PARCELLE avec estimation du prix.
- **Chemin B — LIEN** : on colle un lien d'annonce Leboncoin → « ce que dit l'annonce » + écart au repère de la commune, **sans aucun rattachement parcelle**, fiabilité toujours « Limitée ».

---

## 1. À quoi il sert, et pour qui

Pour un prospecteur/agent qui veut jauger le prix d'un bien : soit à partir d'une **adresse** (LABUSE croise le bien avec les ventes DVF du secteur et la valeur du terrain nu), soit à partir d'un **lien d'annonce Leboncoin** déjà relevé par le Radar (ce que dit l'annonce, confronté à la médiane de la commune). Ce n'est **pas** une estimation notariale : c'est un repère de marché honnête sur des comparables, assorti d'une fiabilité mesurée.

## 2. Le parcours

### Chemin A — adresse (rapport PARCELLE)
Écran unique (`AnalyserAnnonce.tsx` l. 556) : la boîte `EntreeParcelle` sert de recherche puis de badge de la parcelle choisie. Dès qu'une parcelle est choisie (`onPick`, l. 564), le `RapportParcelle` (l. 96) s'affiche dessous :
- **6 tuiles** : Surface, Zone PLU, SDP restante, Dernière vente, Risques, Exposition (l. 143-150).
- **« Estimation du prix »** (l. 185) : « Prix estimé au m² » en gros + fourchette « de Q1 à Q3 », badge **Fiabilité** (Élevée/Moyenne/Limitée), nombre de ventes · rayon/périmètre · période, phrase sur la nature (terrain nu / copropriété / bâti), et « ±N % » mesuré sur 2025.
- **Surface habitable saisissable** (bâti hors copropriété, l. 230) : facultative, affine « l'ordre de grandeur », préremplie depuis la dernière vente DVF.
- **« Ordre de grandeur du bien/terrain »** (l. 252) : surface × €/m² = valeur + fourchette. Pour le bâti, **« Lecture foncière · valeur du terrain »** (l. 269).
- **Accordéon « Les ventes comparables »** (l. 282), fermé par défaut : les 8 ventes qui pèsent le plus, prix bruts.
- Bouton **Exporter en PDF** (l. 319).

### Chemin B — lien (rapport COMMUNE)
L'écran lien n'est pas affiché en direct : il s'ouvre via un **pont Radar « Ce bien »** (`annonceLienPrefill`, l. 484-498) qui lance l'analyse au montage. Le `RapportAnnonce` (l. 338) montre :
- **« Ce que dit l'annonce »** (l. 378) : prix demandé, type, surface, pièces, terrain — **uniquement les champs présents** ; un champ attendu absent = « non précisé dans l'annonce » (l. 346).
- **« Prix face au marché »** (l. 388) : lecture bâti (écart % au repère du type dans la commune) + lecture foncière (terrain × terrain nu, valeur + % du prix). Badge **Fiabilité « Limitée »** gravé en dur (l. 412).
- **« La commune »** (l. 423) : ventes de maisons 12 mois, médianes, évolution, PLU, aléas, permis 12 mois + lien « Fiche commune ».
- Bouton Exporter en PDF (l. 441).

Si le bien n'est pas dans le Radar, une **phrase d'erreur** FR s'affiche (l. 461-472) ; aucun code HTTP.

## 3. Les données lues

| Source (catalogue) | Table(s) SQL réellement lues | Millésime servi | Cadence |
|---|---|---|---|
| **DVF / valeurs foncières** | `dvf_mutations` (comparateurs bâti & terrain, `marche_service.py` l. 439) ; `dvf_mutations_parcelle` (géo-DVF 2021+, l'exclusion de la parcelle sujet + dernière mutation) ; `dvf_mutations_histo` (ventes 2014-2020, `api.py` l. 1597) | `géo-DVF Etalab — millésime 2026-S1` ; en base : `dvf_mutations` 2021-01-01 → 2026-06-30 (31 171 lignes) ; `dvf_mutations_histo` 2014-01-03 → 2020-12-31 (110 477 lignes) | semestriel |
| **DVF Réunion (Région)** | alimente l'historique `dvf_mutations_histo` (jeu figé 2014→mi-2021) | `jeu figé 2014→mi-2021 (54 449 mutations)` | — (alias / contrôle producteur) |
| **Radar (pige d'annonces)** | `pige_annonces` / `pige_biens` / `pige_faits` (chemin lien, `api.py` l. 1264-1272) — 528 annonces en base | `Collecte manuelle — biens en vente (faits + lien)` | quotidien (statut `manuel`) |
| calibration de précision (interne) | `estimer_precision_calibration` (fiabilité + fourchette mesurées, `_fiabilite_mesuree` l. 1682) | table locale, `maj` 2026-11-11 (19 lignes : par INSEE + lignes île `*`) | recalculée par le banc `pige.banc_estimer` |
| PLU / zonage (constructibilité, chemin A) | `spatial_layers` (`plu_gpu_zone`, `ppr`) ; `faisabilite.zonage.resolve_zone` ; `potentiel_batir` | run PLU servi | selon run |
| run résiduel / scoring (SDP, classement) | `parcel_residuel`, `score_labuse`, `mvt_meta` (`api.py` l. 2194-2205 ; `_classement_bande` l. 1451) | run servi courant | selon run |
| commune (chemin B) | `communes_referentiel` / `parcels` (nom canonique) ; `faisabilite.marche_commune.marche_commune_bloc` ; `commune_contexte` (PLU/aléas) | contexte commune servi | selon run |

**Important** : rien ne vient de Leboncoin en direct. Le serveur **n'appelle jamais** le lien fourni (fermeture SSRF, `api.py` l. 1410-1428) ; la seule donnée d'annonce provient du Radar (relevé par l'extension).

## 4. Les calculs

### 4a. Nature du bien (quel comparateur ?)
`_estimation_annonce_core` (`api.py` l. 1931) décide dans l'ordre (l. 1948-1991) :
1. **Copropriété** si `score_v2.copro` (flag du run servi) → comparateur **appartements** (l. 1968).
2. **Terrain nu** si la dernière vente DVF est un terrain, **ou** (sans vente) si l'emprise bâtie < 5 % (`_nature_parcelle`, l. 1462) → repère €/m² de **terrain nu** (l. 1991).
3. **Bâti** sinon → comparateur bâti ; type forcé (maison/appartement) par la dernière vente DVF, sinon type dominant déduit du secteur (l. 2014-2025).

### 4b. €/m² servi — médiane pondérée PUIS reprise de `reference_locale`
`comparateur_bien` (`marche_service.py` l. 406) :
- Récupère les ventes DVF (gré à gré seul, `nature_mutation='Vente'`, `surface_reelle_bati ≥ 20`, parcelle sujet exclue) dans un **rayon adaptatif** `_CMP_RAYONS = (500, 1000, 1500) m` (l. 322) jusqu'au **seuil d'effectif 8** (`seuil_effectif_local("comparables_annonce", 8)`, l. 424), repli commune entière.
- **Médiane pondérée par ressemblance** (l. 486-523) : chaque comparable reçoit un poids = produit de gaussiennes/laplaciennes sur distance, écart de surface, écart de terrain (maisons), et une **demi-vie** d'ancienneté. Constantes `_POIDS_SEGMENT` (l. 333) : maison `h_dist=900, h_surf=120, halflife=4, h_terr=1500` ; appartement `h_dist=500, h_surf=160, halflife=2`. Codées en dur, « réglées sur 2024, annoncées sur 2025 » (commentaire l. 324-332).
- Les prix sont **ramenés à l'ancre récente** par une dérive locale `_drift_commune` (médianes 2019-2024 figées, bornée [−4 % ; +12 %]/an, l. 338-339 ; facteur par comparable borné [0,7 ; 1,6], l. 501).
- **PUIS** (l. 545-558) : pour un type maison/appartement, la médiane/q1/q3/n/rayon/période sont **écrasés** par `faisabilite.bilan.reference_locale` (le même moteur de secteur que la carte Marché de la fiche) → un seul €/m² pour le même bien. La médiane pondérée ci-dessus ne pilote alors que **l'ordre des 8 comparables affichés**, pas le chiffre de tête (sauf secteur mixte type `None`).

### 4c. Terrain nu
`comparateur_terrain` (`marche_service.py` l. 580) : même rayon adaptatif, agrège par mutation, borne €/m² [50 ; 20 000], trim 5 % des extrêmes. `_terrain_repere` sert la médiane + q1/q3 + n + périmètre.

### 4d. Fiabilité et fourchette — **MESURÉES**, pas figées
`_fiabilite_mesuree` (`api.py` l. 1675) lit `estimer_precision_calibration` par (type, INSEE), repli ligne île `*` :
- fourchette servie `precision_pct` = **écart Q3 mesuré** (`ecart_q3`), arrondi ;
- niveau = « Élevée » si `ecart_median < 15 %` **et** `n ≥ 15` ; « Moyenne » si `< 25 %` et `n ≥ 8` ; sinon « Limitée » (l. 1688-1693).
- Sans calibration : repli bande historique `_fiabilite_bien`/`_fiabilite_segment` (`_FIAB_SEG` l. 1532, `_ECART_SEGMENT={"terrain":19}` l. 1545). Le repli commune force « Limitée » (l. 1569).

### 4e. Ordre de grandeur (valeur indicative)
`_valeur_indicative` : surface × €/m², arrondi au millier (`_arrondi_mille`, l. 1548). La **surface** du bâti = surface bâtie de la dernière vente DVF, sinon emprise au sol × ratio médian habitable/emprise de la commune × niveaux LiDAR (`_surface_pour_total`, l. 1780) — **jamais l'emprise brute**. La fourchette basse/haute vient de `±precision_pct` autour de la valeur. **Lecture foncière** : surface terrain × €/m² terrain nu, et % du bâti.

### 4f. Chemin B (lien)
`rapport_lien` (`api.py` l. 1326) : lecture bâti = `(prix_m2_annonce − médiane_commune) / médiane_commune × 100` (l. 1351) ; lecture foncière = `terrain × €/m² terrain nu`, arrondi au millier, % du prix (l. 1358-1367). Conclusion textuelle selon seuils 75 % / 40 % (l. 1361-1366).

## 5. Chaque chiffre affiché

### Chemin A — rapport parcelle
| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| Surface (tuile) | `fiche.surface_m2` | sourcé (cadastre) |
| Zone PLU (tuile) | `fiche.reglement_plu.zones[0].zone` | sourcé (PLU GPU) |
| SDP restante (tuile) | `potentiel_transformation.sdp_residuelle_m2` | estimé (moteur résiduel) |
| Dernière vente (tuile) | `dvf_parcelle.derniere_mutation` (date + valeur DVF) | sourcé (DVF) |
| Risques (tuile) | `n_aleas` = familles d'aléas distinctes (`distinct_hazards`) | sourcé (Géorisques/PPR) |
| Exposition (tuile) | `getParcelExposition.orientation` | sourcé (calcul géométrique) |
| **Prix estimé au m²** | `median` de `comparateur_bien`/terrain, **repris de `reference_locale`** pour maison/appart | **estimé** (médiane de ventes DVF) |
| « de Q1 à Q3 €/m² » | `q1`/`q3` | estimé |
| Fiabilité (badge) | `fiabilite_mot` (back) ← calibration mesurée | estimé (mesuré sur ventes 2025) |
| N ventes · rayon · période | `n`, `radius_m`/`perimetre`, `periode` | sourcé (comptages DVF) |
| ±N % précision | `precision_pct` = `ecart_q3` de `estimer_precision_calibration` | estimé (mesure banc) |
| Ordre de grandeur (valeur €) | surface × €/m², arrondi millier | estimé |
| Lecture foncière (valeur €) | terrain × €/m² terrain nu | estimé |
| 8 ventes comparables | ventes DVF (prix bruts) triées par poids | sourcé (lignes DVF réelles) |

### Chemin B — rapport annonce
| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| Prix / Type / Surface / Pièces / Terrain | `pige_faits` (Radar) | sourcé (annonce relevée) |
| Lecture bâti : écart % | `(prix_m2 − médiane_commune)/médiane_commune` | estimé (calcul) sur médiane sourcée |
| Référentiel €/m² · N ventes | `marche_commune_bloc` (DVF commune) | sourcé (DVF) |
| Lecture foncière : valeur / % | terrain × terrain nu commune | estimé |
| Fiabilité « Limitée » | gravé en dur (pas de rattachement parcelle) | — |
| Bloc commune (ventes, médianes, évolution, permis, PLU, aléas) | `marche_commune_bloc` + `commune_contexte` | sourcé |

## 6. Les limites

- **Ce n'est pas un total à bâtir** : l'estimation est un **repère de marché du secteur**. Sur une parcelle inconstructible (N/A/AU fermée/PPR rédhibitoire), un `avertissement_constructibilite` est ajouté (`api.py` l. 1924), mais le €/m² reste celui du secteur.
- **Maisons : précision plancher ~27 %** (commentaire l. 331, confirmé témoin 97411 : ±54 %). Le code lui-même le dit : « aucune méthode ne descend sous 20 % » pour les maisons.
- **Le chiffre de tête maison/appartement n'est PAS la médiane pondérée** : il est écrasé par `reference_locale` (l. 545-558). La pondération ne sert plus qu'à ordonner les 8 comparables. C'est intentionnel (cohérence avec la fiche) mais contre-intuitif vu le libellé « Prix estimé … pondéré ».
- **Terrain : `valeur_indicative` = contenance ENTIÈRE × €/m²** (témoin 97409 : 27 862 m² × 278 = 7,7 M€). Sur un très grand terrain, ce « ordre de grandeur » n'a pas de sens marchand (un acquéreur n'achète pas 2,8 ha au €/m² d'un lot à bâtir).
- **Chemin B** : fiabilité TOUJOURS « Limitée » (aucune adresse précise, pas de parcelle). Dépend entièrement de ce que le **Radar** a relevé ; un bien absent du Radar renvoie une erreur (aucun fetch Leboncoin). Le lat/lng est un centroïde de quartier/commune, pas la parcelle.
- **Historique DVF** : la dernière vente couvre 2014→ via `dvf_mutations_histo` **si la table existe** ; sinon seul le géo-DVF 2021+ est servi (`_histo_dispo`, l. 1606). Ici elle existe.

## 7. Les tests

- `tests/test_annonce_lien.py` : garantit l'extraction du `list_id` sur formes d'URL courantes (l. 22), le `None` pour une page non-annonce (l. 37), que l'endpoint **ne fetch jamais** (`url_bloquee` servi, l. 50), le rapport depuis Radar sans fetch (l. 76 : prix/surface/pièces/`titre=None`/`releve_le` réels), et l'identifiant inconnu → `None` (l. 115).
- `tests/test_annonce_pdf.py` : structure du PDF parcelle (l. 113), parcelle nue/comparables terrain (l. 151), copropriété (l. 162), `fiabilite_mot` servi tel quel (l. 173), jamais un champ vide (l. 182), estimation absente sourcée (l. 195), deux lectures chiffrées sur le lien (l. 222), PDF lien déterministe (l. 244), arrondi de l'ordre de grandeur (l. 259), une ligne par aléa sans doublon (l. 282), message d'échec lien identique à l'outil (l. 339).
- `tests/test_estimer2.py` : dernière vente couvre 2014 (l. 58), rayon adaptatif terrain (l. 122), hypothèse surface LiDAR en clair (l. 151), **fiabilité servie vient de la calibration mesurée** (l. 198), fourchette mesurée remplace le ±30 % fixe (l. 216), médiane pondérée = vrai quantile pondéré (l. 231), médiane identique fiche/Estimer (l. 247).
- `tests/test_estimer_precision1.py` : surface saisie prime (l. 16), bandes de fiabilité appart/maison (l. 34-53), quantile pondéré (l. 61-72).
- `tests/test_marche_unique_estimer.py` : Estimer et fiche servent la **même médiane** (l. 33), médiane indépendante de la surface du sujet (l. 58).
- `frontend/src/components/documents/AnalyseAnnonceDoc.test.tsx` : rendu du document.

**Non vérifié par les tests** : la **justesse marchande** du €/m² (aucun test ne confronte l'estimation à un prix de transaction réel hors échantillon — c'est le rôle du banc `estimer_precision_calibration`, pas d'un test unitaire) ; le comportement quand `reference_locale` écrase la médiane pondérée vs ce qu'affiche le libellé « pondéré » ; le bon sens de la `valeur_indicative` d'un très grand terrain.

## 8. Les documents liés (PDF, exports)

Les deux PDF partagent le **même point de calcul** que l'écran (aucun recalcul divergent) :
- **PDF parcelle** `/analyse-annonce/{idu}.pdf` (`documents.py` l. 332) → appelle `estimation_annonce` (le même que `GET /radar/annonce/estimation/{idu}`). Le paramètre `surface_hab` voyage de l'écran au PDF (`docAnalyseAnnonceUrl`, `api.ts` l. 1471) → écran == PDF == Doc.
- **PDF lien** `/analyse-annonce.pdf?url=…` (`documents.py` l. 373) → appelle `radar_annonce_analyser` (le même que l'écran), puis `builder.construire_analyse_annonce_lien` sur le rapport **tel quel**. Même phrase d'échec (422) que l'outil.

Vérification réelle : PDF parcelle 97411000BZ1065 renvoie `http=200 application/pdf size=146627`. Source identique confirmée par `test_annonce_pdf` (points unique écran==PDF).

## 9. Trois cas rejoués

`GET /radar/annonce/estimation/{idu}` (serveur :7300), le 2026-11-11. Chiffres bruts copiés des réponses.

**97411000BZ1065 (Saint-Denis) — BÂTIE, maison.** `median=3821 €/m²`, `q1=2970`, `q3=4722`, `n=30`, `radius_m=500`, `periode=[2022,2026]`, `fiabilite=limitee`, `fiabilite_mot=Limitée`, `precision_pct=54`, `fourchette_source=mesure_commune`, `ecart_median_mesure=32`, `calibration_n=17`, `n_aleas=2`, `type_label_pluriel=maisons`. `valeur_indicative`: 95 m² × 3 821 = **363 000 €** (167 000–559 000), surface estimée d'après l'emprise 193 m² × 1 niveau LiDAR × ratio 0,51. `lecture_fonciere`: 1 567 m² × 578 €/m² = **906 000 €** (250 % du bâti). `constructibilite`: zone Uh, constructible. 8 comparables (le 1er : 07/2025, maison 165 m², 238 095 €, 1 443 €/m², 226 m). — Croisement : `estimer_precision_calibration(maison,97411)` donne `ecart_q3=54.2`, `ecart_median=31.8` → cohérent avec les 54 / 32 servis.

**97409000AK0804 (Saint-André) — NUE, terrain.** `median=278 €/m²`, `q1=254`, `q3=396`, `n=26`, `radius_m=500`, `perimetre=500 m autour de la parcelle`, `periode=2021–2025`, `fiabilite=limitee`, `precision_pct=72`, `fourchette_source=mesure_ile` (pas de ligne 97409 → repli île `*` terrain `ecart_q3=71.8`), `calibration_n=120`, `n_aleas=2`. `valeur_indicative`: **27 862 m² × 278 = 7 746 000 €** (2 169 000–13 322 000). 8 comparables terrain (le 1er : 05/2022, 212 m², 57 120 €, 269 €/m², 0 m). — Illustre la limite §6 : l'ordre de grandeur sur 2,8 ha n'est pas un prix marchand réaliste.

**97415000DH0076 (Saint-Pierre) — COPROPRIÉTÉ, appartement.** `median=6275 €/m²`, `q1=5508`, `q3=7168`, `n=79`, `radius_m=500`, `periode=[2022,2026]`, `fiabilite=fiable`, `fiabilite_mot=Élevée`, `precision_pct=23`, `fourchette_source=mesure_commune`, `ecart_median_mesure=12`, `calibration_n=16`, `n_aleas=2`. Pas de `valeur_indicative` (copro : aucun lot unique à valoriser). `lecture_fonciere`: 19 513 m² × 1 098 = 21 425 000 €. 8 comparables appart (1er : 06/2026, 49 m², 275 000 €, 5 612 €/m², 127 m). — Croisement : `estimer_precision_calibration(appartement,97415)` `ecart_median=12.5 (<15)`, `n=16 (≥15)` → bien « Élevée », cohérent.

**Chemin B rejoué** (lien réel d'une annonce du Radar, `POST /radar/annonce/analyser`, `.../ventes_immobilieres/4661496863448217817.htm`) : `ok=true`, annonce maison Le Tampon, prix 194 000 €, 87,78 m², terrain 95 m², 3 pièces, 2 210 €/m², relevée 2026-10-29. `lectures.bati`: écart **−8 %** vs référentiel 2 397 €/m² (n=1 738). `lectures.fonciere`: 95 m² × 263 = 25 000 € (13 % du prix → « valeur tient surtout au bâti »). Bloc commune Le Tampon : 233 ventes maison 12 mois, médiane 2 397 €/m², terrain 263 €/m², évolution +5,4 %, PLU « à jour », aléas inondation/mouvement, 62 permis. Un lien inconnu du Radar renvoie `{"ok":false,"erreur":"url_bloquee"}` ; une URL hors Leboncoin `url_invalide` — aucun fetch sortant, conforme au code (l. 1416-1428).

## 10. Tes doutes

1. **(grave) Le libellé « Prix estimé au m² » et la mécanique divergent.** Pour maison/appartement, la médiane pondérée par ressemblance (le gros du code `comparateur_bien`) est **écrasée** par `reference_locale` (l. 545-558) ; le chiffre de tête est en réalité la **médiane de secteur** de la carte Marché, pas l'estimation pondérée que l'écran décrit. L'utilisateur croit lire une estimation fine du bien ; il lit un repère de secteur. La pondération ne change que l'ordre des 8 comparables.
2. **(grave) `valeur_indicative` d'un terrain = contenance ENTIÈRE × €/m² de lot.** Le témoin 97409 affiche 7,7 M€ pour 2,8 ha. Le €/m² vient de ventes de lots à bâtir (quelques centaines de m²) ; multiplier par une contenance de 2,8 ha produit un « ordre de grandeur » faux et potentiellement trompeur, sans seuil de garde.
3. **(moyen) La fiabilité maison sort presque toujours « Limitée ».** Calibration mesurée : maison île `ecart_median=26,8 %` et par commune souvent >25 % → la condition « Élevée » (<15 % & n≥15) n'est quasi jamais atteinte. C'est honnête, mais l'outil « estime » surtout des maisons avec un ±50 % affiché : l'utilité pratique du chiffre est faible et ce n'est pas mis en avant.
4. **(moyen) Dépendance totale au Radar pour le chemin B, sans fraîcheur visible côté calcul.** Le lien n'est exploitable que si le bien a été relevé (statut source `manuel`, « collecte manuelle »). Un bien récent/absent renvoie une erreur ; le `releve_le` (ex. 2026-10-29) peut être ancien sans que l'écart au marché le pondère. La source Radar est marquée `manuel` dans `data_sources`, pas automatisée.
5. **(mineur) La `reference_locale` et la `precision_pct` peuvent décrire des échantillons différents.** Le €/m² vient de `reference_locale` (rayon/période propres) tandis que la fourchette ±% vient de `estimer_precision_calibration` (mesure banc par INSEE, parfois repli île). Les deux sont servis côte à côte comme s'ils portaient sur le même échantillon ; ce n'est pas garanti.

---

## Synthèse INDEX (≈12 lignes)

- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/analyser-annonce.md`.
- Outil « Estimer un bien » (clé `analyser-annonce`, N1), 2 chemins : **adresse** → rapport parcelle + estimation (`GET /radar/annonce/estimation/{idu}`) ; **lien Leboncoin** → ce que dit l'annonce + écart au repère commune (`POST /radar/annonce/analyser`, fiabilité toujours « Limitée »).
- Le mémoire parlait de `pige/estimer3.py` : **inexistant ici**. Le calcul vit dans `pige/api.py:estimation_annonce` (l. 1902) + `marche_service.py:comparateur_bien/terrain`.
- Données principales : **DVF** (`dvf_mutations` 2021-2026 + `dvf_mutations_histo` 2014-2020, millésime 2026-S1 semestriel), **Radar** `pige_*` (quotidien manuel, 528 annonces), calibration locale `estimer_precision_calibration`, PLU/scoring pour tuiles.
- Méthode réelle : médiane **pondérée par ressemblance** PUIS, pour maison/appart, **écrasée par `reference_locale`** (médiane de secteur = celle de la fiche) ; fiabilité et fourchette **mesurées** par le banc (INSEE, repli île).
- Part sourcé vs estimé : tuiles et comparables bruts = **sourcés** (DVF/cadastre/Géorisques) ; tout le bloc prix (€/m², fourchette, valeur indicative, fiabilité, écart %) = **estimé**. Grossièrement ~50/50 à l'écran, mais le cœur « prix » est estimé.
- 3 témoins rejoués (sorties réelles) : BZ1065 bâtie maison 3 821 €/m² ±54 % Limitée ; AK0804 nue terrain 278 €/m² ±72 % (valeur indicative 7,7 M€ sur 2,8 ha) ; DH0076 copro appart 6 275 €/m² ±23 % Élevée. Chemin B rejoué sur une vraie annonce Radar (Le Tampon, −8 % vs marché).
- PDF (parcelle et lien) = **même point de calcul que l'écran**, vérifié (PDF 200/146 627 o).
- **Le doute le plus grave** : le libellé « Prix estimé au m² » (présenté comme une estimation pondérée du bien) sert en réalité la **médiane de secteur** (`reference_locale` écrase la pondération pour maison/appart) ; secondairement, l'« ordre de grandeur » terrain multiplie la **contenance entière** par un €/m² de lot à bâtir, produisant des valeurs non marchandes sur les grandes parcelles.
