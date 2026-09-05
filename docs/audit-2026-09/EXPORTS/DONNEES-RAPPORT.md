# EXPORTS-AUDIT — rapport de vérité sur les données des exports

**Mandat** : EXPORTS-AUDIT v2 · branche `audit/exports-donnees` · lecture seule, aucune correction.
**Date** : 05/09/2026 · base réelle `labuse` (431 663 parcelles) · run scoring servi `q_v11_m137` · run résiduel `m135-run2-ile`.
**Annexe de reproductibilité** : `DONNEES-ANNEXE.md` (chaque valeur citée y a sa requête ou sa commande).

> Note liminaire : le document source `EXPORTS-AUDIT.md` cité par le mandat n'est **pas dans le dépôt**
> (aucun fichier sous `docs/audit-2026-09/EXPORTS/` avant ce rapport). Les constats du 03-04/09 sont
> repris du texte du mandat et **re-vérifiés sur PDF régénérés le 05/09** — quand une valeur a bougé
> entre-temps, les deux sont citées.

---

## Préalable — procédure de génération locale (établie et éprouvée)

Script reproductible **hors dépôt** : `~/Desktop/exports/generer.sh <IDU>` (wrapper) + `~/Desktop/exports/generer.py` (worker).
Produit, pour un IDU, dans `~/Desktop/exports/<IDU>/` : `fiche.json` (référence écran), `fiche.pdf`, `dossier.pdf`, `banquier.pdf`, `argumentaire.pdf`, `predossier-pc.zip`, `flash.pdf`.

| Ingrédient | Valeur | Pourquoi |
|---|---|---|
| Python | `/Users/openclaw/miniforge3/envs/labusedb/bin/python` | le `.venv` du dépôt est cassé |
| `DYLD_FALLBACK_LIBRARY_PATH` | `/opt/homebrew/lib` | WeasyPrint exige libgobject/pango absents de l'env conda |
| `PYTHONPATH` | `/Users/openclaw/Desktop/labuse-merge/src` | le package editable installé pointe sur `~/Desktop/labuse` (clone principal), pas sur le worktree |
| Base | `.env` du worktree → `postgresql+psycopg://openclaw@localhost:5432/labuse` | base réelle |
| Transport | `fastapi.testclient.TestClient(app)` | passe par les **vraies routes HTTP** (auth locale passante, quotas réels) |

Routes appelées : `GET /parcels/{idu}` (fiche.json), `GET /parcels/{idu}/export.pdf` (fiche), `GET /dossier/{idu}.pdf`, `GET /dossier-banquier/{idu}.pdf`, `GET /argumentaire/{idu}.pdf` (défauts calculette 2 500 €/m² · 21 % · VRD 90), `GET /pre-dossier/{idu}.zip`. Flash : `generate_flash_report(idu, force=True)` (`src/labuse/flash/report.py:119`) — même générateur que la livraison payée, la route publique exigeant Stripe.

**Limite constatée** : la synthèse IA du Banquier échoue en repli propre (« crédit API Anthropic épuisé », `kind=synthese-banquier`) — le PDF sort quand même. Les 28 artefacts (4 témoins × 7) ont été générés le 05/09.

## Parcelles témoins

| # | IDU | Justification |
|---|---|---|
| T1 | `97415000BO0852` | Saint-Paul, 742 m², U1a, bâtie 73 %, PPR/bruit/ICPE/ABF/mixité — imposée par le mandat. |
| T2 | `97401000AD0554` | Les Avirons, 634 m², Ud3, **nue** (`parcel_residuel.taux_emprise_pct = 0`), adressée — nue en U hors Saint-Paul. |
| T3 | `97416000DY0106` | Saint-Pierre, 5 064 m², **zone N** (`parcel_zone_plu`), bâtie 22 % — test des verdicts en zone non constructible (la base lui annonce pourtant une SDP résiduelle de 4 188 m²). |
| T4 | `97411000AV0110` | Saint-Denis, 665 m², **à cheval Uh 57,4 % / N 42,6 %** (intersection `spatial_layers` kind=`plu_gpu_zone`) — test de la résolution de zone. |

Référence « écran » = le JSON de `GET /parcels/{idu}` (`app.py:4250` → `_q_v2_fiche`, `app.py:3283`), dumpé dans `~/Desktop/exports/<IDU>/fiche.json`.

---

## Tableau de synthèse

| Donnée | État | Vérité établie | Moteur cible | Effort | Bloquant pour |
|---|---|---|---|---|---|
| A1 Prix €/m² | 🔴 | 8 moteurs backend + isochrone ; « prix commune » = médiane autour du **centroïde géométrique** (n 11) ; 2 moteurs « neuf » concurrents (4 730 vs 4 742) | `marche_service` seul point d'appel, un profil nommé par usage, libellés vrais | L | toute maquette marché |
| A2 Comparables | 🔴 | 3 filtres (z-score MAD / trim 5 % / **aucun**) ; la fiche imprime les extrêmes sans filtre ; vente d'immeuble agrégée « appartement 750 m² » servie partout | un filtre unique paramétré + dédup/étiquetage multi-lots à l'ingestion | M | fiche, Dossier, Flash |
| A3 Potentiel | 🔴 | 4 verdicts = 4 moteurs ; « 127 m² » vient d'une **table orpheline** (bâtisseur retiré du code le 24/07, données figées 10-11/07) ; égout 12 m et faîtage 16 m cohabitent | le moteur commun `estimate_capacity` seul ; supprimer la lecture `parcel_residuel_bati` | M | tous les exports |
| A4 Permis | 🟠 | 5 définitions (500 m·24 m / 400 m·5 ans / 100 m·36 m / 300 m·5 ans / viab. 100 m) ; le « 17 = 17 » du 03-04/09 était une **coïncidence** (05/09 : 18 vs 17) ; le profil `PERMITS_FLASH_500M` **ment** (exécute 300 m·5 ans) | profils nommés réellement appliqués + libellé unique | M | Dossier, fiche |
| A5 Mixité | 🟠 | 2 questions mélangées : servitude PLU présente (cascade) vs clause déclenchée par le programme (bilan) — les deux vraies, aucun document ne l'explique | un bloc unique à 2 lignes (servitude / déclenchement) | S | Banquier |
| A6 Accès voirie | 🟠 | 2 moteurs : cascade `acces` (intersection stricte avec l'axe BD TOPO → quasi toujours « pas d'accès ») vs viabilisation (ST_DWithin 10/75 m → « voie au contact ») ; les deux servis dans le même JSON | le test à distance (viabilisation) ; requalifier ou supprimer la couche cascade | S | fiche |
| A7 ICPE | 🟠 | le régime « Non ICPE » vient **tel quel de Géorisques** ; l'ingestion garde les non-classées dans `kind='icpe'` et la cascade alerte sur la seule proximité sans lire le régime | filtrer le régime à l'ingestion ou dans la couche | S | fiche, Dossier |
| A8 Propriétaire | 🟠 | 3 blocs, 3 sources (fichier PM DGFiP / sondage BODACC par SIREN / ligne cascade « non renseigné » sur une autre table) ; contiguïté même propriétaire **déjà calculable** (`assemblage.py`) | une carte propriétaire unique alimentée par les 3 sources | M | Apporteur |
| A9 Zéros | 🟠 | `dvf_secteur_medianes` et compteurs pige rendent 0/`—` sans indicateur de couverture ; le Flash omet les sections vides (bon) mais pas les tableaux | garde de couverture systématique (« non couvert » ≠ 0) | M | tous |
| A10 Invraisemblances | 🟡 | `pct_qpv=100` pour les 24 communes (donnée d'ingestion RPLS fausse, **masquée** de la fiche servie depuis RETOURS-11F2) ; « fiable » vs « marge non estimable » = 2 drapeaux indépendants ; délai 9 mois = cohorte PC aboutis, cut 12 mois | re-jointure RPLS×QPV géométrique ; lier les 2 drapeaux ; libellé cohorte | S | Banquier |
| Zone PLU (transverse) | 🔴 | **2 résolutions de zone** : dominante par surface (`parcel_zone_plu`) vs zone du **centroïde** (faisabilité `_CTX`) — T3 servie « constructible 27-31 logements » en zone N, T4 « non constructible N » en dominante Uh | une seule résolution (dominante par surface + drapeau « à cheval ») | M | tout verdict |
| D1 Moteurs de rendu | 🟠 | 2 moteurs (WeasyPrint ×3 chaînes, FPDF ×4) ; fiche PDF sans métadonnées producteur | briques_pdf comme socle unique | L | maintenance |
| D2 Arithmétique gabarit | 🟡 | l'essentiel des calculs est en Python-remplissage (liste au chapitre D2) ; rien dans Jinja hors arrondis | tout lire des moteurs | S | recette |
| D3 Sources en dur | 🟠 | MOBPRO cité en dur (`rapport.html.j2:553`, `pdf_zone.py:161`) alors qu'écarté le 28/08 | pieds de section dérivés des données lues | S | crédibilité |
| D4 Archivage Flash | 🟠 | seul le PDF est archivé ; le dict `data` du template n'est pas figé → document payé non reproductible | archiver `data` en JSON à côté du PDF | S | conformité |
| D5 Proxy Vite | 🟡 | `/argumentaire` + ~9 routes absentes de `apiPaths` (`frontend/vite.config.ts:19`) | compléter la liste | S | dev |
| D6 Test PDF | 🟡 | 2 tests génèrent un PDF (Flash, fiche) mais **aucun** n'extrait de valeurs ni ne compare à `fiche.json` | test doré : générer → extraire → comparer | M | recette |

Les lignes LOT B et LOT C sont dans leurs chapitres (verdicts SERVABLE / APRÈS TRAVAIL / PAS SERVABLE par ligne).

---

# LOT A — les moteurs qui se contredisent

## A1 · Prix — huit moteurs backend + un isochrone

### Chemins de code

| # | Fonction | Fichier:ligne | Paramètres | Qui la lit |
|---|---|---|---|---|
| 1 | `marche_commune.ligne1_prix_ancien` → `sector_price` sur la **parcelle la plus proche du centroïde géométrique de la commune** (`_repr_parcel`) | `faisabilite/marche_commune.py:71-85` et `:53-61` | rayon adaptatif 500→1500 m **autour du centroïde**, 5 ans, appartement→mixte, trim 5 % | bloc « Marché » du Dossier/Flash/fiche PDF (`marche_bloc.py:27`) |
| 2 | `dvf_secteur_medianes` (table d'ingestion, médianes par type × secteur cadastral) | `flash/data.py:515-520` (lecture) | secteur cadastral (préfixe IDU), millésimes géo-DVF 2021-2025 | en-tête fiche (3 804), lignes « Secteur — appartement/maison/autre/terrain » |
| 3 | `sector_price` (parcelle) | `faisabilite/bilan.py:204-285` ; constantes `:107-110` (`MIN_N_SECTEUR=8`, rayons `(500,1000,1500)`, 5 ans, trim 5 %, bornes 1 000-12 000) | rayon adaptatif autour de **la parcelle** | Banquier/Argumentaire via `briques_pdf.collect:249` et `marche_service.py:44-48` |
| 4 | `ligne4_tendance` (commune, 12 mois vs fenêtre précédente) | `faisabilite/marche_commune.py:174-200` | commune entière, seuil n≥30 | ligne « Tendance » Dossier/Flash/Banquier/Argumentaire |
| 5 | `etude_zone` (isochrone) | `api/app.py:4313-4435` | isochrone 10 min voiture | outil Étude de zone (4 561 du relevé 03-04/09) |
| 6 | `resolve_prix_sortie_servi` → `resolve_prix_neuf_marche` | `faisabilite/bilan.py:325-349` ; `ingestion/dvf_prix_neuf.py:173-201` | ventes ≤ 3 ans après achèvement PC, hors bailleurs sociaux, N_MIN=10, préséance secteur>commune>île | LE prix de sortie du bilan (Banquier, Argumentaire, calculette, fiche) |
| 7 | `neuf_vefa_commune` (profil `DVF_NEUF_VEFA`) | `marche_service.py:52-58` ; `ingestion/dvf_marche.py` | VEFA **déclaré par l'acte**, grain commune, fenêtre 5 ans | ligne « Neuf VEFA » de la fiche (`app.py:3432-3446`) |
| 8 | `ligne2_terrain_zone` / `prix_terrain_nu_zone` | `faisabilite/marche_commune.py:88-110` | terrain nu × zone PLU calibrée (U/AU) | bloc Marché, outil Marché, calculette |
| — | `flash._marche` (médiane locale 500 m/3 ans) | `flash/data.py:418-506` | `RAYON_MARche_M=500`, 3 ans, tous types, z-score MAD>3,5 | Dossier/Flash (« 22 ventes ») — **la médiane calculée n'est pas imprimée** (voir plus bas) |

### Valeurs sur les 4 témoins (écran d'abord ; mesures du 05/09, annexe §A1)

| Moteur | T1 St-Paul | T2 Avirons | T3 St-Pierre | T4 St-Denis |
|---|---|---|---|---|
| écran/fiche en-tête (`dvf_secteur_medianes` appart) | **3 804** (36 v.) | — | — | — |
| 1 · ligne1 « commune » (centroïde) | 3 766, **n 11** | 3 150 (n 56) | 2 739 (n 8) | 2 556 (n 35) |
| 3 · `sector_price` parcelle | 3 818 (n 25) | 2 308 (n 27, fragile) | 3 103 (n 43) | 3 118 (n 29) |
| 4 · tendance 12 m (commune) | 4 490 (n 218/583) | — | — | — |
| 6 · prix de sortie servi | **4 730** (commune, n 54) | 4 375 (repli île ±12 %) | 4 258 (n 76) | 4 275 (n 77) |
| 7 · Neuf VEFA (acte) | **4 742** (n 308) | insuffisant (n 0) | 4 916 (n 162) | 4 998 (n 272) |
| flash `_marche` 500 m/3 ans | 4 207 (22 v., **non imprimée**) | 2 337 (13 v.) | 3 462 (56 v.) | 3 174 (6 v.) |

### Réponses aux questions du mandat

- **« n 11 » présenté comme le marché de la commune** : libellé **faux**, requête correcte pour ce qu'elle fait. `ligne1_prix_ancien` prend la parcelle la plus proche du **centroïde géométrique** de la commune (`marche_commune.py:57-61` : `ORDER BY centroid <-> ST_Centroid(ST_Collect(centroid))`) et lance `sector_price` en rayon adaptatif depuis là. Pour Saint-Paul (commune immense, centroïde dans les hauts, parcelle représentative `97415000CO0049`), il reste 11 ventes retenues — pendant que la même page compte 136 ventes/trimestre commune entière. La ligne sort pourtant `fiabilite: "fiable"`.
- **« n 218/583 »** : `ligne4_tendance` (`marche_commune.py:174-200`) — 218 ventes fenêtre 12 mois récente, 583 fenêtre précédente. Défini nulle part dans les documents ; format posé à `marche_bloc.py:30-32`.
- **4 730 ≠ 3 818 × 1,24** : hypothèse **réfutée**. Aucun coefficient 1,24 dans le code (grep exhaustif, annexe §A1.q3). 4 730 = `resolve_prix_neuf_marche` niveau **commune**, n 54 (ventes ≤ 3 ans après achèvement PC, hors bailleurs sociaux, `dvf_prix_neuf.py:173-201`). Pourquoi pas le « VEFA à 5 003 » (03-04/09 ; 4 742 n 308 au 05/09) : c'est **l'autre** moteur neuf (`neuf_vefa_commune`, VEFA déclaré par l'acte, fenêtre 5 ans) — deux définitions du « neuf » cohabitent et personne ne les distingue dans les documents.
- **`sector_price` et les exports** : il **est** appelé par les exports (Banquier `briques_pdf.py:249`, Argumentaire via `_collect`, fiche PDF `app.py:4519-4520`, bloc Marché via ligne1) — pas seulement écran/Radar.
- **La médiane des « 22 ventes rayon 500 m »** : calculée (`_marche` → `med_m2_bati` = 4 207 chez T1) puis **jamais imprimée** — le Dossier annonce l'effectif et décrit la médiane en légende (`dossier.txt:184-187`) sans le chiffre. Elle est perdue au gabarit.
- **« DVF 2026 » vs « jusqu'à déc. 2025 »** : la vraie borne des ventes en base est **max(date_mutation) = 10/08/2026**. « DVF 2026 » = `_dvf_millesime` (max de l'année, `marche_commune.py:63-66`) ; « 2021-2025 » = le libellé catalogue `data_sources.source_millesime` (« géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 »), affiché tel quel par la fiche. Deux libellés dérivés différemment, aucun ne dit la borne réelle.

**Laquelle est juste** : chaque moteur répond à une question différente ; le faux est dans les **libellés** (ligne1 n'est pas « la commune » ; deux « neuf » sans distinction ; millésimes contradictoires). Arbitrage produit nécessaire sur : quel prix afficher en tête de fiche, et lequel des deux « neuf » sert le bilan (Q1-Q3 en fin de rapport).
**Moteur cible** : `marche_service` déjà positionné comme point d'appel unique (`marche_service.py:34-58`) — y faire passer **tous** les lecteurs (ligne1 comprise), un profil nommé par usage, libellés générés depuis le profil. Supprimer : l'appel direct `sector_price` du bloc commune (ligne1), le double moteur neuf en tête de fiche sans étiquette.
**Effort** : L.

## A2 · Comparables — trois filtres, et une vente d'immeuble déguisée

| Chemin | Fichier:ligne | Filtre aberrance | Nb affiché | Qui l'imprime |
|---|---|---|---|---|
| `flash._marche` | `flash/data.py:452-506` | z-score MAD > 3,5 (`:476`), bornes 1 000-12 000 | 5 (`gardees[:5]`, `:492`, en dur) | Dossier/Flash « Comparables récents » |
| `marche_service.comparables` | `marche_service.py:148-179` | **aucun** | 12 (`LIMIT 12` SQL, en dur) | fiche PDF (`app.py:4485`) |
| `sector_price._trim_aberrants` | `faisabilite/bilan.py:136-152` | bornes + trim 5 % si n≥20 | tous les retenus (25 chez T1) | bande de points Argumentaire (`argumentaire.py:106-134`), tableau Banquier |

- Les trois tris sont du **code dupliqué** (5, 12 en dur ; profils différents), pas un paramètre.
- **Le « 750 m² »** : mutation `2025-1268771`, **une seule ligne** en base `dvf_mutations`, `type_local='Appartement'`, 750 m², 4,5 M€ — l'ingestion géo-DVF a agrégé la mutation multi-lots (somme des surfaces) en une ligne typée du premier lot. Résultat : une vente d'immeuble entier passe pour « un appartement de 750 m² à 6 000 €/m² » et survit aux trois filtres — elle est imprimée le 05/09 dans la fiche (12 ventes, avec 814 et 10 135 €/m²) **et** dans le tableau Dossier/Flash pourtant sous-titré « ventes au prix/m² aberrant écartées » (6 000 €/m² n'est pas aberrant au sens MAD).
- Dédup : par `mutation_id` (une mutation = une ligne servie), donc pas de double compte — mais pas de garde de vraisemblance surface/type.

**Verdict** : la fiche (chemin sans filtre) est fautive au regard de sa propre promesse implicite ; le vice de fond est à l'**ingestion** (agrégation multi-lots sans étiquette « vente d'immeuble »). **Moteur cible** : un seul filtre paramétré dans `marche_service`, + type `immeuble` posé à l'ingestion quand une mutation somme plusieurs lots. **Effort** : M.

## A3 · Potentiel constructible — quatre verdicts, quatre moteurs, dont un mort

### Les quatre chemins

| Verdict imprimé | Moteur | Fichier:ligne | Détail |
|---|---|---|---|
| « Emprise résiduelle 127 m² » (Dossier/Flash) | table `parcel_residuel_bati` | lecture `flash/data.py:238-250` | `emprise_max_m2 (667,8 = 742 × 90 % emprise U1a) − emprise bâtie BD TOPO (540,4)` — **PAS un calcul de gabarit** (hypothèse 668−540 du mandat : confirmée sur le fond, mais la soustraction est matérialisée en table) |
| « SDP résiduelle 0 m² » (écran) | `parcel_residuel` (run `m135-run2-ile`) | table servie par la fiche | SDP max − SDP existante ; T1 : `sdp_residuelle_m2=0`, et `taux_emprise_pct=123` (!) |
| « Aucun droit à bâtir résiduel au sol… surélévation (marge ~6,6 m) » (fiche PDF) | `renouvellement.py` lisant `parcel_residuel_bati` | `renouvellement.py:214-227` | marge 6,6 = `hauteur_max_m 16 (FAÎTAGE) − hauteur_bati 9,4` |
| « 635 m² vendables · 7-9 logements » (partout) | moteur commun `estimate_capacity` | `faisabilite/engine.py:172-474` | scénario table rase, hauteur **ÉGOUT 12 m** ÷ 3 = R+3 |

### Le point décisif : `parcel_residuel_bati` est une table **orpheline**

Son bâtisseur (`labuse/segments/residuel_bati.py`, « Lot 2 — droits résiduels sur parcelles bâties ») a été **retiré du code actif le 24/07/2026** (commit `7fd96725`, spin-off « Vues », archivé sous `archive/vues-m12-5e50113`). Les données datent des **10-11/07/2026** (`min/max(updated_at)`), 292 056 lignes dont seulement **43 420 avec `emprise_max_m2`** (15 %). `flash/data.py:238-250` et `renouvellement.py:214-227` continuent de la servir au client. Le « 127 m² » ne sera plus jamais rafraîchi.

### Réponses aux autres questions

- **Égout vs faîtage** : les deux cohabitent. Le moteur commun prend l'égout en priorité (`engine.py:285-297` ; repli faîtage si égout absent, avec avertissement). La table orpheline stocke `hauteur_max_m=16` (faîtage) et la fiche PDF en dérive « marge ~6,6 m » de surélévation. Même parcelle : niveaux au 12, surélévation au 16.
- **« 7 à 9 » vs « ~8 à 10 »** : le détail imprimé au Banquier/Argumentaire (« 635 ÷ 80 à 65 m²/logt → ~8 à 10 », `banquier.txt:137`) et le titre (« 7 à 9 ») viennent du même moteur mais le titre applique en plus le **plafond stationnement + modulation** (`engine.py:448-474` : `min(floor, densite_cap, log_max_park)`), le détail non. Le moteur servi rend `logements_au_sol=(7,9)` (annexe §A3) ; la ligne « ~8 à 10 » est une étape intermédiaire imprimée comme si c'était la fourchette.
- **Recul 3 m vs 5 m** : les deux sont dans le chiffre ET dans le texte, mais pour des objets différents : recul **limites séparatives** 3 m (défaut `engine.py:226`, appliqué au buffer `:240-242`) ; recul **voirie** 5 m (défaut `:221`, avertissement « à_vérifier » `banquier.txt:154`). Les libellés ne disent pas qu'il s'agit de deux reculs distincts.
- **« ~3,65 M€ réhab » et « ~570 k€ terrain nu »** : bloc `mode_b` (`faisabilite/bilan.py` `compute_mode_b`, servi via `flash/data.py:593` et briques « assainissement & réhab ») ; terrain nu = `768 €/m² × 742 m²` — le 768 étant la médiane terrain du **secteur cadastral** (`dvf_secteur_medianes`), imprimée avec la formule dans les 5 documents.

**Verdict** : le moteur commun (`estimate_capacity` + `compute_bilan_servi`) est le seul vivant et cohérent ; « 127 m² » (table morte) et la surélévation au faîtage doivent disparaître ou être recalculés par le moteur commun. **Effort** : M (supprimer 2 lectures + re-libeller). 

### Transverse — LA résolution de zone diverge entre moteurs (découvert sur T3/T4)

| Moteur | Règle | Fichier:ligne | T3 (dominante N) | T4 (dominante Uh 57 %) |
|---|---|---|---|---|
| `parcel_zone_plu` (écran, tuiles, filtres) | zone **dominante par surface** d'intersection | `api/tiles.py:35-80` | N | Uh |
| Faisabilité `_CTX` (capacité, bilan, exports) | zone **contenant le centroïde** (plus petite d'abord) | `faisabilite/db.py:29-36` | **Ud** → constructible, 27-31 logements, SDP 6 837 m² | **N** → non constructible (`cause=zone_non_constructible:N`) |

Sur toute parcelle à cheval, l'écran et le bilan peuvent se contredire **en miroir** : T3 est classée N à l'écran et servie « 27-31 logements » par la faisabilité ; T4 est classée Uh à l'écran et servie « rien à construire ». S'y ajoute `parcel_residuel` qui annonce à T3 une SDP résiduelle de 4 188 m² en zone N. C'est la racine commune d'une partie des « quatre verdicts ». 🔴

## A4 · Permis à proximité — cinq définitions

| Définition | Moteur | Fichier:ligne | T1 au 05/09 |
|---|---|---|---|
| 500 m · 24 mois | `flash._dynamique` (`RAYON_PERMIS_M=500`, `FENETRE_PERMIS_MOIS=24`, `flash/data.py:48-50,525-559`) | Dossier/Flash « Autorisations » | **18** |
| ≤ 400 m · 5 ans | cascade `phase2.py:95-116` (radius/months des params de couche) | fiche « Dynamique constructive : 17 PC » | **17** |
| < 100 m · 36 mois | `site_voisinage.voisinage_proche` (profil `VOISINAGE_100M`, `marche_service.py:22,28`) | fiche « 0 permis (<100 m, 36 mois) » | 0 |
| 300 m · 5 ans | `nearby_permits` **défauts** (`ingestion/permits.py:234-235`) | Banquier « Permis voisins (SITADEL, ≤ 5 ans) » | 6 lignes ≤ 168 m |
| < 100 m (signal viabilisation) | `viabilisation_build.py:77-82` (voie/permis 10-100 m) | fiche/Dossier « 6 permis autorisés < 100 m · 2 depuis 2022 » | 6 |

- **Le « 17 » identique sous deux définitions était une coïncidence** : régénérés le 05/09, les deux moteurs divergent (18 vs 17). Preuve par l'évolution des données.
- **Le profil ment** : `PERMITS_FLASH_500M` est documenté « 500 m / 24 mois » (`marche_service.py:25`) mais `permits()` appelle `nearby_permits(db, pid)` **sans passer rayon ni fenêtre** (`marche_service.py:186-187`) → exécute les défauts **300 m / 5 ans**. Le Banquier imprime « ≤ 5 ans » sans dire le rayon.

**Verdict** : aucun chiffre n'est faux isolément ; le système l'est (cinq questions non étiquetées + un profil non appliqué). **Moteur cible** : `marche_service.permits` avec paramètres réellement transmis, libellé généré du profil. **Effort** : M.

## A5 · Mixité sociale — deux questions, deux réponses, zéro explication

- Cascade phase1 (`cascade/layers/phase1.py:460-463`) : la parcelle intersecte une prescription PLU `mixite_sociale` → fiche/Flash : « quota de logements aidés imposé (impacte le bilan, pas la constructibilité) ». C'est la **servitude**.
- Bilan (`faisabilite/bilan.py:390-411` `_clause_mixite`) : seuils du règlement (SDP ≥ seuil OU logements ≥ seuil OU terrain > seuil) sur le **programme estimé** → Banquier : « non déclenchée, pas de quota LLS » (T1 : programme 794 m² SDP sous le seuil de 1 800 m² imprimé par le règlement PLU servi, `fiche.json/reglement_plu` : « ≥ 1 800 m² → 30 % LLS »).
- Le bilan **lit** bien sa propre clause (`bilan.py:536-547`) ; il ne lit pas la couche cascade, et réciproquement. Les deux ont raison ; aucun document ne dit qu'il s'agit de « secteur soumis » vs « programme sous le seuil ».

**Verdict** : incohérence de présentation, pas de calcul. **Cible** : un bloc unique deux lignes (« Secteur de mixité : OUI — Seuil de déclenchement : 1 800 m², programme estimé 794 m² → non déclenchée »). **Effort** : S.

## A6 · Accès voirie — un test géométriquement inapte

Servis **dans le même JSON** de T1 (`fiche.json`) : `lines[11]` (couche `acces`) « Pas d'accès direct évident à la voirie. » ET `viabilisation.contributions[1]` « voie au contact + bâti riverain ».

| Moteur | Test | Fichier:ligne |
|---|---|---|
| Cascade `AccesLayer` | intersection stricte parcelle × géométrie voirie | `cascade/layers/phase1.py:790-802` |
| Viabilisation | `ST_DWithin` 10 m et 75 m (`voie10`/`voie75`) | `faisabilite/viabilisation_build.py:77-82` |

L'axe BD TOPO est une **polyligne au milieu de la chaussée** : elle n'intersecte quasi jamais le polygone parcellaire — le test cascade répond « pas d'accès » pour une parcelle dont la façade donne sur la Chaussée Royale. C'est lui qui se trompe (géométrie, pas projection : tout est en 2975). RETOURS-11F a unifié l'affichage front, le backend sert toujours les deux.

**Cible** : le test à distance ; supprimer ou re-spécifier la couche `acces` (buffer de largeur de voie). **Effort** : S.

## A7 · ICPE — le régime est vrai, l'alerte ne le lit pas

- La ligne « ENGEN (ex CALTEX) - St Paul — **Non ICPE** — 158 m » vient **telle quelle de Géorisques** : `spatial_layers.subtype='Non ICPE'` (7 enregistrements ENGEN en base, mélange « Autres régimes »/« Non ICPE » — requête en annexe §A7). L'ingestion (`ingestion/georisques_layers.py:112-128`) stocke le régime dans `subtype`/`attrs.regime`.
- La couche cascade `IcpeLayer` (`cascade/layers/etage1.py:217-229`) alerte sur la **seule proximité** d'un enregistrement `kind='icpe'` sans lire le régime → « Installation classée à proximité » pour une installation que la même page déclare non classée.
- Le tableau du Dossier (`flash/data.py:377-391`) affiche les 5 plus proches AVEC le régime — d'où la contradiction visible.

**Verdict** : la ligne de risque est fautive (sur-inclusion). Une station-service en activité relèverait normalement d'un régime — « Non ICPE » signifie ici que Géorisques la recense sans classement (cessation/antériorité) ; à trancher côté produit si on la montre du tout. **Cible** : filtrer `regime NOT IN ('Non ICPE')` dans la couche (ou à l'ingestion), et l'écrire dans le libellé. **Effort** : S.

## A8 · Propriétaire — trois blocs, trois sources

| État imprimé (fiche T1) | Source | Fichier:ligne |
|---|---|---|
| « PM “non remarquable”, groupe 0, acquérable » + dénomination MCA3/SIREN à l'écran | `parcelle_personne_morale` (fichier PM DGFiP) + SIRENE | `app.py:3406-3417`, `_pm_identite app.py:4106-4133` |
| « BODACC — aucune procédure — sondé le 19/08/2026 » | `bodacc_sondages` par **SIREN** | `ingestion/bodacc.py:40-68`, rendu `cascade/layers/etage2.py:60-90` |
| « Propriétaire (personne morale) non renseigné pour cette parcelle » | couche cascade lisant **une autre assiette** (`parcel_source_results`/absence de payload propriétaire au run) | ligne `lines[]` de la fiche |

- Le sondage BODACC ne « sonde » jamais un propriétaire absent : il interroge un SIREN **connu** de `parcelle_personne_morale` (mécaniquement impossible autrement, `bodacc.py:63-68`). La coexistence « sondé » + « non renseigné » prouve que la ligne « non renseigné » lit une **autre source** que le fichier PM — deux assiettes pour la même question.
- **Contiguïté même propriétaire** : déjà calculable aujourd'hui — `assemblage.py:30-43` (`_same_owner`), `:46-85` (`parcel_assemblage`, ST_DWithin 0,5 m), `:88-116` (`find_assemblages`), exposé `POST /outils/moteurs/assemblage` (`app.py:4652-4668`). Réutilisable tel quel pour le document Apporteur.

**Cible** : une carte propriétaire unique (fichier PM + SIRENE + BODACC), la ligne cascade supprimée ou branchée sur la même assiette. **Effort** : M.

## A9 · Zéros de couverture

Endroits où un 0/`—` sort sans distinguer « mesuré à zéro » de « non couvert » :

| Donnée | Rendu | Fichier:ligne | Indicateur de couverture disponible ? |
|---|---|---|---|
| Médianes secteur par type (« autre : 20 ventes, médiane — ») | tableau fiche/Dossier | lecture `flash/data.py:515-520` | non (la table `dvf_secteur_medianes` rend NULL sous seuil sans motif) |
| « Neuf/VEFA : 3 — » (Banquier) | décomposition `_comparables` | `faisabilite/bilan.py:180-201`, rendu `briques_pdf.comparables` | oui partiellement (seuils existent côté `neuf_vefa_commune` mais pas sur cette ligne) |
| Annonces actives : 0 (Radar) | compteur brut | `pige/releves.py:29-30` | **oui, non lu** : la couverture pige est partielle et connue (LOT B11) |
| Compteurs permis (0 permis < 100 m) | `voisinage_proche` | `marche_service.py:22,28` | couverture géoloc SITADEL = 83 % (`nearby_permits.dynamique.couverture_pct` — l'indicateur **existe** et n'est pas imprimé) |
| Sections Flash | omission si `rien=True` | `flash/data.py:389-390` et gabarit | doctrine correcte (omission ≠ zéro) — à généraliser |

**Règle cible** : chaque compteur imprimé porte sa couverture ou un état « non couvert » ; le cas SITADEL montre que l'info existe déjà et est jetée au rendu. **Effort** : M.

## A10 · Valeurs invraisemblables

- **« Parc social 7 265 · 100 % en QPV »** : `rpls_commune.pct_qpv = 100.0` pour **les 4 communes témoins** (et les 24, cf. RETOURS-11F2) — donnée d'ingestion fausse. Depuis RETOURS-11F2 le champ est **masqué de la fiche servie** (`app.py:3488` le retire du dict) ; la fiche du 05/09 imprime « Parc social commune : 7 265 logements (RPLS 01/01/2025) » **sans** le % QPV. Si un document du 03-04/09 l'affichait encore, il lisait un autre chemin — plus reproduit au 05/09. La vraie jointure RPLS×périmètres QPV n'existe pas en code.
- **« Fiabilité : fiable » + « marge NON ESTIMABLE »** : deux drapeaux indépendants — `fiabilite` dérive du **prix de sortie neuf** (`_fiabilite_prix_neuf`, `bilan.py:412+` : local observé → « fiable ») ; « marge non estimable » sort d'une autre branche (données de marché de la **marge**). Ils peuvent légitimement diverger mais la page ne l'explique pas.
- **« Délai 9 mois · 4 796 dossiers »** : cohorte = permis **PC** de la commune, **aboutis** (`valide`), déposés il y a plus de 12 mois (cohorte mûre), médiane `percentile_cont(0.5)` — `flash/data.py:697-706`, table `m10_permit_delais`. Les refus et dossiers en cours sont exclus (le PDF le dit : « minimum optimiste »).

---

# LOT D — plomberie des exports

## D1 · Moteurs de rendu : deux, pas un

| Export | Moteur | Chaîne |
|---|---|---|
| Flash / Dossier | WeasyPrint + Jinja | `flash/report.py:141` (templates `flash/templates/`) ; Dossier = même template, en-tête différent (`api/dossier.py:64-110`) |
| Banquier / Argumentaire | WeasyPrint via `briques_pdf.render_pdf` | `api/briques_pdf.py:740-750` |
| fiche PDF | **FPDF** direct | `api/pdf_premium.py:343` (`render_fiche_pdf`), rempli par `app.py:4448-4497` |
| Pré-dossier PC | FPDF **et** WeasyPrint mélangés | `api/pre_dossier.py:84,165-172,226` |
| Étude de zone / Projet | FPDF | `api/pdf_zone.py:14`, `api/pdf_projet.py:13` |

Le « un seul builder » de CONNEXIONS-2 (lot A) n'est **pas** l'état réel : deux moteurs, trois chaînes WeasyPrint distinctes. La fiche imprimée est produite par la chaîne FPDF `parcel_export_pdf → render_fiche_pdf` et ne pose **aucune métadonnée** PDF (auteur/titre/date absents du code FPDF).

## D2 · Arithmétique en gabarit ou en code de remplissage

Dans les templates Jinja : **rien que des arrondis d'affichage** (`rapport.html.j2:70,77,112,116`). En revanche, dans le code Python de remplissage (par opposition à une lecture moteur) :

| Calcul | Fichier:ligne | Devrait lire |
|---|---|---|
| `plancher = round(vendable / rendement)` ; `rendement_pct = round(rend*100)` | `flash/data.py:228-230` | `surface_plancher_m2` du moteur (déjà servi) |
| moyenne coût construction `(cc_bas+cc_haut)/2` | `api/argumentaire.py:61,148` | hypothèses résolues du bilan |
| €/m² bâti par vente `valeur/surface` | `flash/data.py:457` | acceptable (grandeur par ligne), mais dupliqué dans 3 chemins |
| pourcentage recouvrement zone `100*ST_Area(...)` | `flash/data.py:167-168` | zone servie (`parcel_zone_plu` n'a pas le %) |
| écart plafond densité `(deriv−vend)/max(deriv,1)` | `api/briques_pdf.py:501-503` | le moteur |
| marge foncière `round(charge − prix_probable)` | `api/pdf_premium.py:368` | le bilan servi |
| volatilité `(q3−q1)/med`, tendance `100*(mr−ma)/ma` | `faisabilite/bilan.py:64-95` | (moteur — acceptable, c'est le moteur lui-même) |

Le « 127 m² » de A3 n'est **pas** dans cette liste (table matérialisée) — mais la table étant orpheline, l'effet est pire : le chiffre ne suit ni l'ingestion ni la bascule, définitivement.

## D3 · Pieds de section : listes en dur

- **MOBPRO cité en dur** dans `flash/templates/rapport.html.j2:553` et `api/pdf_zone.py:161` alors qu'écarté le 28/08 — cas de départ du mandat **confirmé**.
- Liste vigilances Argumentaire en dur (`api/argumentaire.py:290`).
- À l'inverse, la section 10 « Sources & millésimes » du Flash itère la liste dynamique (`rapport.html.j2:567-570`, alimentée par `data.sources`). Deux régimes cohabitent dans le même document.

## D4 · Archivage Flash

Archivé : le PDF seul (`flash/report.py:142-147`, nom portant `order_ref`/`idu`/`TEMPLATE_VERSION`). Le dict `data` complet (`collect_report_data`, `flash/data.py:846-894`) est jeté après rendu. Pour la reproductibilité d'un document payé : figer `data` en JSON à côté du PDF (mêmes clés que le template), les millésimes y sont déjà (`data.sources`).

## D5 · Proxy Vite

`frontend/vite.config.ts:19-40` (`apiPaths`). Absents alors que des routes backend existent : `/argumentaire` (confirmé à la ligne 19-40 — le préfixe n'y est pas), `/lettre-zonage`, `/pipeline-rarete`, `/ortho`, `/protection`, `/readyz`, `/shortlist`, `/audit`, `/feedback`, `/admin/programmes` (couvert partiellement par `/admin` ? — `/admin` n'est PAS dans apiPaths non plus au bloc lu ; inventaire complet de l'agent en annexe §D5). Le commentaire du fichier documente lui-même la famille de bugs (« /pre-dossier MANQUAIT », « /bilan MANQUAIT »).

## D6 · Tests PDF

Existants : `tests/test_flash_report.py:66-85` (génère un Flash réel WeasyPrint, vérifie `%PDF-` + idempotence), `tests/test_pdf_premium.py:27-30` (fiche FPDF, vérifie l'en-tête). **Aucun** test n'extrait de valeurs du PDF ni ne les compare au JSON servi. Le test doré de la recette : générer via la procédure du préalable → `pdftotext -layout` → extraire les grandeurs nommées → comparer à `fiche.json` (le présent audit est le prototype manuel de ce test ; scripts en annexe).

---

# LOT B — ce qui existe en base et n'est pas servi

Mesures du 05/09 sur la base réelle (chaque requête en annexe §B).

| B# | Donnée | Tables (existence vérifiée) | Couverture réelle | Fraîcheur | Moteur existant | Verdict |
|---|---|---|---|---|---|---|
| B1 | DPE ADEME | `dpe_records` ✓ | **17 lignes**, 14 parcelles = **0,003 %** | max 21/07/2026 ; millésime `data_sources` vide | `ingestion/dpe.py:219`, vue `v_passoire_thermique` (`models.py:1530`) | **PAS SERVABLE** (quasi vide ; amont ~910 DPE au 974) |
| B2 | BDNB | aucune table `bdnb*` | **0 %** — absente | amont `2026-02-a` = métropole seule | flux prêt `ingestion/bdnb.py:1-28` | **PAS SERVABLE** (amont sans 974) |
| B3 | CoSIA 2025 | `p_model_bati_cosia` ✓, `qa_cosia_bati` ✓, `parcel_bati_revele` ✓, `parcel_vegetation` ✓ | emprise bâtie 321 314 = **74,4 %** ; canopée/NDVI **98,7 %** | CoSIA 2025, calc. 04/08 ; végétation 13/08 | `faisabilite/bati_revele.py:33`, `residuel.py:45` | **emprise + canopée : SERVABLE TEL QUEL** ; imperméabilisation totale : PAS SERVABLE (non calculée) |
| B4 | Historique propriété 2019→2025 | `pm_proprietaires_millesimes` ✓ (2019-2024) + `parcelle_personne_morale` (2025) | 91 397 parcelles PM = **21,2 %** (PM seulement, RGPD) | import 12/07/2026 | `proprietaire_historique.py:44` — **le diff est déjà codé** | **SERVABLE TEL QUEL** (périmètre PM affiché) |
| B5 | Parcelles contiguës | `parcels` (PostGIS) | île entière | live | `assemblage.py:46/88/119` | **SERVABLE TEL QUEL** (seuils YAML étiquetés PLACEHOLDER — à assumer) |
| B6 | Taxe d'aménagement | config YAML datée | n/a | config datée | `taxe_amenagement.py:29` | **APRÈS TRAVAIL** — surface taxable = saisie, taux communal absent partout (`app.py:2570-2571`, `taxe_amenagement.py:100-104`) |
| B7 | Contacts institutionnels | `commune_contacts` ✓ | **0 ligne, 0/24 communes** | — | CRUD `commune_contacts.py:54-78` | **PAS SERVABLE** (table vide — remplissage humain) |
| B8 | Programmes promoteurs | `programmes` ✓ | **9 lignes, 1 promoteur, 4 communes**, 0 géométrie/IDU | relevé 31/08 | `api/veille_promoteurs.py:161,195` | **PAS SERVABLE** (anecdotique, non rattachable à une parcelle) |
| B9 | Blocs fiche absents du Dossier | `plu_reglement_extrait` (3 258 extraits, 21/24 communes) | voir détail | — | 3 modules réutilisables / 3 inline `app.py` | **APRÈS TRAVAIL** |
| B10 | Destinations PLU | config YAML | 4/4 témoins calibrés (**exécuté**) | référentiel 01/07/2023 | `plu/destinations.py:290` `verdict()` — pur, sans DB | **SERVABLE TEL QUEL** (CDAC exposé, vérifié à l'exécution) |
| B11 | Radar | `pige_biens`, `pige_annonces` | 104 actives, **7 rattachées** (6,7 %), 12/24 communes, 61 % à St-Denis | pige née le **29/08** | `pige/*` | **PAS SERVABLE comme statistique** ; liste factuelle seulement |
| B12 | Étude de zone | `zone_isochrone_cache` | — | — | `app.py:4348` (chalandise) + `app.py:4265` (contexte) | **SERVABLE TEL QUEL** — `minutes`/`mode` sont des **paramètres** (`app.py:4341-4344,4358-4359`), deux visages = deux endpoints |
| B13 | Millésimes manquants | `data_sources`, `source_veille` | 31 sources sans millésime ; date ailleurs pour **26/31** | — | sondes `ingestion/fraicheur.py:40-120` | **APRÈS TRAVAIL** — composer millésime → `dernier_vu` sentinelle → sonde → `last_sync_at` ; 5 orphelines sans aucune date (EDF SEI, Géoplateforme, PEIGEO, ODRÉ, ZNIEFF) |

Détails saillants :

- **B1** — le DPE est rattaché **à la parcelle** (`dpe_records.parcelle_idu`, index `ix_dpe_parcelle`, rattachement BAN locale), mais l'ingestion est à la demande par commune (`cli.py:1219`) et n'a jamais tourné en masse ; l'amont lui-même est minuscule (DPE obligatoire en DROM depuis le 01/07/2024 seulement, ~910 DPE au 974 — `seed_sources.py:285`). Aucun témoin couvert.
- **B3** — la **pleine terre n'est PAS un forfait 10 %** : `plu_rules.py:42` la lit par zone dans les YAML calibrés (30/40/20/10 % selon zone, sourcés article/page), appliquée `engine.py:271-279`, non appliquée avec avertissement si absente (`engine.py:281-282`). Le « 10 % » de T1 (U1a) est la valeur calibrée de sa zone. En revanche l'**imperméabilisation CoSIA multi-classes n'est pas en base** (seul le bâti est vectorisé).
- **B4** — `proprietaire_historique.historique()` (timeline + changements, doctrine constat) est déjà branché dans la fiche (`app.py:3420-3421`) et **absent du Dossier** (0 occurrence dans `flash/data.py`).
- **B9** — réutilisables tels quels : articles PLU (`plu_reglement.reglement_block`), gestionnaires réseaux (`viabilisation.resolve_gestionnaires`), historique propriétaire ; à extraire d'`app.py` : transports/proximités (`app.py:3668-3717`), identité PM (`app.py:4068-4133`), fraîcheur zonage (`app.py:3992`) et constantes fiscales DOM (`app.py:3649-3665`).
- **B10** — exécution réelle sur les témoins : Saint-Paul U1a logement `sous_condition` (≥ 1 800 m² SDP → 30 % LLS) ; Les Avirons Ud3 `sous_condition` (> 1 000 m² → 40 %) ; Saint-Pierre N `non_mentionne` → interdit (art. N1 p.212 cité) ; Saint-Denis Uh `sous_condition` (collectif ≥ 30 logements). Verrou CDAC dans le payload (`CDAC_SEUIL_M2=1000`, `destinations.py:96,276`, source L752-1 c. commerce).

---

# LOT C — ce qui n'existe pas encore

**Préalable catalogue** : la sentinelle surveille **49 sources actives** (`source_veille`) sur **77 lignes `data_sources`** ; `SENTINELLE-INVENTAIRE.md` ne mentionne **aucun** sujet de ce lot (grep AS1/captage/PEB/DPU/préemption : 0). Deux « découvertes » existent en réalité **déjà en base** (ER/EBC) — avec des trous précis. Toutes les sondes ci-dessous ont été exécutées le 05/09 (commandes en annexe §C).

| Donnée | Déjà au catalogue ? | Source | Couverture 974 **testée** | Licence | Effort | Valeur export |
|---|---|---|---|---|---|---|
| Emplacements réservés | **OUI — en base** (`spatial_layers` kind=`plu_gpu_prescription` typepsc 05, **2 250 objets**, routés par la cascade `phase1.py:372-446`) | GPU `/prescription-surf` | ✅ live (ER Saint-Denis retrouvé) ; **trou : Saint-André, Saint-Leu, Saint-Philippe = 0 document au GPU ; Petite-Île = PLU (335 zones) sans prescriptions** | Licence Ouverte | S (combler les 4 communes = hors GPU, L) | ⭐⭐⭐ éliminatoire |
| Espaces boisés classés | **OUI — en base** (typepsc 01, **1 782 objets**) | idem | ✅ idem, mêmes 4 communes en trou | LO | S / L idem | ⭐⭐⭐ |
| DPU | NON | GPU `info-surf` **typeinf 04** (LABUSE n'ingère que typeinf 19, source id 67) | ✅ live : St-Paul 158, St-Denis 41, Le Tampon 2, Ste-Marie 1, **0 dans les 20 autres partitions** (⚠ le paramètre `typeinf` de l'API ne filtre pas — piège vérifié) | LO | **S** (même connecteur que l'assainissement) | ⭐⭐ (« non téléversé » ailleurs, jamais « pas de DPU ») |
| Captages AS1 | NON | **introuvable en open data 974** : GPU = 24 doc SUP listés, aucun AS1 (ni A5/I4/EL9) ; data.gouv = 0 ; DEAL Lizmap (2 projets, ~95 couches) = pas de captage | ❌ vérifié absent ; trace partielle typeinf 99 St-Denis | — | **L** (demande ARS / Office de l'eau) | ⭐⭐⭐ mais inaccessible aujourd'hui |
| PEB Roland-Garros / Pierrefonds | NON | WMS-V Géoplateforme `dgac_peb_plan_wmsv` | ✅ **GetFeatureInfo positif aux 2 aéroports** (zone D Lden 50 R.-Garros, zone C Lden 52 Pierrefonds ; arrêtés 2017) | données publiques Géoplateforme | **S** (2 emprises GeoJSON) | ⭐⭐⭐ éliminatoire (L.112-10 : zones A/B/C) |
| SUP T5 dégagement aéro | NON (base `sup` = pm1/2/3, el10, ac1-4) | GPU : doc `120064019_SUP_974_T5` **en production depuis le 09/07/2026** | ⚠ listé, mais **API Carto ne sert encore aucune assiette T5** (0 sur la piste même ; PM1 y répond) ; archive : 404/403 aux 2 URL tentées | LO | M (re-sonder / archive GPU) | ⭐⭐ |
| SUP T7 | NON | servitude **nationale sans géométrie** (hors T5) | sans objet | — | S | ⭐ mention fixe |
| Aléa sismique | NON | Géorisques `/zonage_sismique` + D.563-8-1 C. env. | ✅ **zone 2 FAIBLE uniforme** (14 communes sondées + décret) | LO | **S = une constante** | ⭐ ligne fixe |
| Aléa volcanique | NON | **aucun zonage opposable** (DDRM : « aucun PPRn ne prend en compte le risque d'éruption » ; PPR Ste-Rose/St-Philippe = inondation+MVT) | ✅ vérifié | — | — | ⭐ mention Est, **clore** |
| CatNat | OUI (Géorisques « ok ») **mais table cassée** | GASPAR `/gaspar/catnat` | ✅ **BUG : `catnat_arretes` = exactement 10 arrêtés/commune (troncature page_size défaut) vs réel 21 (St-Denis), 24 (St-Paul), 17 (St-Benoît)** ; commande `ingest-catnat` retirée du CLI (`cli.py:2630`) et cron retiré (`api/ops.py:28-29`) ; `/etc/cron.d/` inexistant sur cette machine | LO | **S** (ré-ingérer `page_size=100` + job) | ⭐⭐ |
| Argiles RGA | NON | Géorisques `/rga` | ❌ **corps vide au 974** (témoin Toulouse OK) — jamais cartographié (sols volcaniques) | — | — | **non pertinent, clos** |
| Zonage A/B/C | NON (grep code = 0) | CSV data.gouv, arrêté 23/06/2026 | ✅ **24/24 : Les Avirons, L'Étang-Salé, Saint-Leu, Saint-Paul = zone A ; les 20 autres = B1** | lov2 | **S** (24 lignes statiques) | ⭐⭐⭐ (PTZ, dispositifs DOM, plafonds → levier bailleur du bloc SRU) |
| Loyers de marché | NON | Carte des loyers DHUP 2025 (CSV, seule Mayotte exclue) | ✅ **24/24 communes** apparts+maisons (St-Denis 15,09 €/m², n=14 748 ; St-Paul 18,86 ; ⚠ petites communes en maille) | LO | **S** (CSV annuel) | ⭐⭐⭐ rendement locatif |
| Coût de démolition | NON | **aucun référentiel public fiable** : ADEME/DEMOCLES = pratiques sans €/m², CEREMA = rien, Batiprix/UNTEC = payants ; le « 20 453 €/logement ANRU » qui circule n'a pas pu être retrouvé dans un document officiel — ne pas l'utiliser ; fourchettes commerciales métropole 80-250 €/m² non officielles | ❌ rien 974 | — | — | **→ champ de saisie** (cf. arbitrage Q11) |
| Coût de construction | NON | **EPTB 2024** (DEAL/SDES, 23/01/2026 : maison ≈ 1 516 €/m² hors terrain) + **dataset CDC** `lareunion.opendatasoft.com` (Licence Ouverte, maj 15/06/2026, API sondée : prix de revient médian collectif social **2 304 → 2 842 €/m² SU**, 2021→2025) | ✅ | lov2 / LO | **S** | ⭐⭐⭐ **le 2 300-2 800 actuel (`faisabilite/engine.py:41`) devient sourçable** |
| ECLN | NON | SDES : « réalisée en France métropolitaine » | ❌ | — | — | **clos** |

Points saillants C1 :

- **Le trou éliminatoire réel n'est pas le flux, c'est le téléversement** : `municipality` répond `is_rnu=false` pour les 24 communes, mais Saint-André, Saint-Leu et Saint-Philippe n'ont **aucun document** au GPU et Petite-Île n'a pas ses prescriptions. Sur ces 4 communes, une parcelle grevée d'un ER sortira « constructible » quoi qu'on fasse côté GPU — il faut le PLU papier (mairie/PEIGEO, non testé) ou un **drapeau « prescriptions non vérifiables »** dans le PDF (arbitrage Q12).
- **typeinf 99** contient au passage des aléas PPR, ZNIEFF, zones SAFER et des périmètres de sursis à statuer TCSP (11 à Saint-Denis) — matière éliminatoire supplémentaire dans le même flux que le DPU.

## C4 · Abandons explicites (ne plus y revenir)

| Élément | Motif définitif |
|---|---|
| Photos du terrain, état intérieur du bâti | aucune source publique n'existera (vie privée, droit de propriété) — constat humain (visite, annonce Radar), pas une donnée |
| Servitudes privées | actes notariés non publics ; fichier immobilier SPF consultable à l'acte, payant, non massifiable légalement → mention d'avertissement standard dans le PDF |
| Tracés fins de réseaux | exclusion volontaire déjà actée (DT-DICT = procédure par projet ; tracés sensibles) — le proxy actuel (MT EDF, zonage assainissement) est le bon niveau |
| Prix demandé du vendeur · plan de financement/LTV | données du deal, pas du territoire — saisie utilisateur par construction |

---

# Arbitrages à demander à Vic

Une question par ligne, avec les options. Tout le reste du rapport est factuel ; ces dix points ne peuvent pas être tranchés par le code.

| # | Question | Options |
|---|---|---|
| Q1 | Quel prix afficher en tête de fiche et dans la synthèse marché ? | a) `sector_price` parcelle (3 818) b) médiane secteur cadastral (3 804) c) les deux, étiquetées — mais jamais « ligne1 centroïde » comme aujourd'hui |
| Q2 | La ligne « prix ancien médian de la commune » (centroïde, n 11) : corriger le scope ou le libellé ? | a) vraie médiane commune entière b) garder le rayon adaptatif mais libeller « autour du centre de la commune » c) supprimer la ligne |
| Q3 | Quel « neuf » sert le bilan : `resolve_prix_neuf_marche` (4 730, ≤3 ans post-achèvement, hors bailleurs) ou `neuf_vefa_commune` (4 742, VEFA à l'acte) ? | a) garder le premier (décision 28/07) et retirer l'autre de la fiche b) fusionner c) afficher les deux avec définitions |
| Q4 | `parcel_residuel_bati` (table orpheline, « 127 m² ») : supprimer la lecture ou ressusciter le bâtisseur ? | a) supprimer des exports (recommandé : moteur commun seul) b) rapatrier le bâtisseur archivé et le brancher au run |
| Q5 | Résolution de zone : dominante par surface ou centroïde ? Que sert-on sur une parcelle à cheval ? | a) dominante partout + drapeau « à cheval » avec les deux règlements b) centroïde partout c) le plus restrictif des deux |
| Q6 | Une parcelle en zone N avec `parcel_residuel.sdp_residuelle_m2 > 0` (T3 : 4 188 m²) : que doit dire l'export ? | a) 0 en zone N/A par règle b) servir le chiffre avec la cause c) ne rien servir |
| Q7 | Permis à proximité : une seule définition client (rayon·fenêtre) ? | a) 500 m · 24 mois partout b) 400 m · 5 ans partout c) garder plusieurs MAIS chaque chiffre porte sa définition (état minimal exigible) |
| Q8 | La vente d'immeuble agrégée (« appartement 750 m² ») : filtre d'affichage ou correction d'ingestion ? | a) étiqueter `immeuble` à l'ingestion quand la mutation somme des lots b) seuil de vraisemblance à l'affichage (appartement > 200 m² → écarté) c) les deux |
| Q9 | ICPE « Non ICPE » : les recensements non classés doivent-ils alerter ? | a) exclus de la couche d'alerte, gardés au tableau avec régime b) exclus partout c) statu quo avec libellé « recensé Géorisques, non classé » |
| Q10 | Le document payé (Flash) doit-il archiver ses données d'entrée (dict `data` en JSON) pour être reproductible ? | a) oui, à côté du PDF (recommandé) b) non |
| Q11 | Coût de démolition : le LOT C confirme qu'aucun référentiel public fiable n'existe pour le 974 — le poste devient-il un champ de saisie du bilan ? | a) oui, saisie avec défaut « non chiffré » b) fourchette interne assumée « à dire d'expert, non officielle » |
| Q12 | Saint-André, Saint-Leu, Saint-Philippe (aucun document GPU) et Petite-Île (prescriptions non téléversées) : que disent les exports sur ER/EBC/prescriptions ? | a) drapeau « prescriptions non vérifiables sur cette commune » (recommandé) b) silence actuel (risque : faux « constructible ») c) ingestion manuelle des PLU papier (effort L) |
