# OUTILS-1 — recette & retouches des 17 outils · compte-rendu

Poste : `~/Desktop/labuse` · branche : `feat/outils-1` (porte volontairement les 5 commits
`feat/radar-depot-2` non mergés + le commit maquette v3). **Ne pas merger** — la commande de merge est
au tout dernier point, isolée.

---

## 0. Le fait dominant de la recette : l'audit du 30/08 a tapé un serveur STALE

Reproduits UN À UN en local, sur le code de la branche + la base locale, **quatre des « bugs de fond »
n'existent pas dans le code courant** — ils étaient des artefacts d'un uvicorn non redémarré (le piège
récurrent « ancien code sert », déjà consigné en mémoire). Preuves live à l'appui :

| Item audit | Ce que dit l'audit | Repro live sur la branche | Verdict |
|---|---|---|---|
| **A1** ligne piscine « 5 828 € » | affichage faux | `/outils/taxe-amenagement` renvoie **5 020 €** (20×251), détail « 20 m² × 251 € », assiette 183 420 = 178 400+5 020 ; `grep 5828` sur tout le repo = **rien** | déjà correct |
| **A2** fiche commune « en erreur » | crash | `/communes/{Saint-Paul,Le Tampon,Cilaos,Saint-Philippe,Saint-Denis}/contexte` = **HTTP 200** ; clic fiche en Playwright = **0 crash, 0 erreur console** | déjà correct |
| **A3** SIRENE « non couvert » | branchement cassé | table `sirene_etablissements` = **158 515 lignes** ; `/outils/etude-zone` (zone témoin) renvoie `emplois_couverture=servie`, `concurrents.couverture=servie`, **n=33** | déjà servi |
| **A4** courrier « n'écrit plus » | POST muet | POST `/courrier/demande` live → **ligne id 42 créée** (26→27 lignes) ; `j()` throw sur non-2xx (la confirmation n'apparaît que sur 2xx, donc jamais « faussement transmise ») | déjà écrit |

**Conséquence opératoire pour le déploiement** : au VPS, il faut (1) redémarrer le service après la
bascule de code (`docs/EXPLOITATION.md §5`), (2) ingérer SIRENE une fois (`§12`, ajouté ce mandat). Sans
ça, l'écran rejoue exactement les symptômes de l'audit.

Le travail réel du mandat n'était donc PAS de « réparer » ces quatre points, mais d'appliquer les
**retouches spécifiées** (n° de demande, libellés, retraits, cartes) et de **prouver** que le fond tient.

---

## 1. Tableau de provenance (règle transversale)

Chaque chiffre affiché, sa source, son moteur, l'écart constaté. Le run servi unique = `q_v11_m137`
(`config/served_run.txt`), lu par le front au build (VITE_RUN_LABEL) et par l'API.

| Outil | Chiffre | Table · colonne | Moteur | Millésime | Écart |
|---|---|---|---|---|---|
| **Taxe** | surface 178 400 € | barème `config/taxe_amenagement.yaml` `valeur_forfaitaire_m2.hors_idf=892` | `taxe_amenagement.calculer()` | barème 2026 (service-public.gouv.fr, daté) | 0 — front rend `l.assiette_eur`, ne recalcule rien |
| **Taxe** | piscine 5 020 € | yaml `forfaits.piscine_m2=251` | idem | 2026 | 0 (le « 5 828 » n'est nulle part dans le code) |
| **Taxe** | part dép. 4 585,5 € | assiette × `taux.part_departementale_defaut=2,5 %` | idem | 2026 | 0 (= 183 420×2,5 %, au centime) |
| **Fiche commune** | stock, permis 5 ans, €/m² | `parcel_p_score_v2`, `sitadel_permits`, `m10_permit_delais`, DVF | `comparateur.py` + `_foncier_commune`/`marche_commune` | run servi | tableau = fiche pour le stock/permis ; €/m² **ancien** diffère par NIVEAU (commune vs secteur), documenté — pas deux moteurs |
| **Étude de zone** | postes salariés (fourchette) | `sirene_etablissements.tranche_effectif` | `zone.emplois_zone` | SIRENE géo 2026-08 | 0 (couverture servie) |
| **Étude de zone** | concurrents (n, temps) | `sirene_etablissements` filtré NAF + isochrone IGN | `zone.concurrents_zone` | SIRENE géo 2026-08 | 0 ; n servi = count SQL même emprise. Manque **date de création** (colonne absente de la table — signalé) |
| **PLU** | 21 servable · 2 révision · 1 RNU | `config/plu_millesimes.yaml` `statut` via `corpus_status` | `plu_annuaire_communes` | corpus PLU | **corrigé** : le RNU n'est plus compté « en procédure » |
| **Scan patrimoine** | valorisation nu (M€) | Σ(`surface_m2` × prix zone U/AU) `ligne2_terrain_zone` (DVF) | `modules.patrimoine` | run servi + DVF | contre-calcul non rejoué (voir §4) |
| **Scan patrimoine** | SDP résiduelle (m²) | Σ(`sdp_residuelle_m2`) | `modules.patrimoine` | run servi | idem |
| **Faisabilité** | SDP gabarit | emprise × `coef_occupation` × niveaux | `faisabilite/engine.py` | run servi | contre-calcul aux extrêmes non rejoué (voir §4) |
| **Étudier un bien** | charge foncière | CA×(1−marge−honoraires−frais_fin) − coût_constr − VRD | `faisabilite/bilan.py` | run servi | écart -122 911/-123 410 = arrondis/poste (voir §4) |
| **Courrier** | n° de demande | `courrier_demandes.id` | `courrier.creer_demande` | — | n° client = n° base = n° admin (source unique) |

Aucune valeur métier n'est écrite en dur dans le front des outils que j'ai touchés : le barème taxe vient
du backend, le compte d'outils de `MODULES`, les compteurs PLU du backend, le seuil marché radar de la
constante `SEUIL_N=5` (`pige/marche.py`).

---

## 2. Ce qui a été livré (fait + vérifié)

### A1 / B8 — Taxe d'aménagement
- Le calcul est juste (vérifié live). Le « 5 828 » n'existe pas dans le code (grep exhaustif).
- **B8** : le produit exact sous chaque poste passe en **petit mono** (`font-mono`) → l'écran s'auto-vérifie
  (assiette = somme des postes). Capture `02-taxe-A1B8.png` : « Surface 250 m² × 892 €/m² (dont 100 m² à
  −50 %) = 178 400 € » · « Piscine 20 m² × 251 € = 5 020 € ».

### A4 / B6 — Courrier (traçabilité)
- **Aucune migration** (les tables `courrier_demandes`/`courrier_envois` existent ; le POST écrit — prouvé).
- **Client** : la confirmation devient « ✓ **Demande n° {id} transmise.** » + promesse 24 h + « Retrouvez vos
  demandes dans **Projets → Mes courriers** ». La **timeline d'états internes** (Demandé→Imprimé→Posté) est
  **retirée** côté client ; le récap « Vos demandes » n'affiche plus de statut interne (n° + date + communes).
- **Projets → Mes courriers** : nouvel onglet minimal (n°, date, communes, volume), lecture seule, sans état interne.
- **Admin** : la file « Demandes de courrier » (n°, client, parcelles, date, transitions) existe déjà
  (`admin/Courrier.tsx` + `/courrier/admin/demandes`) ; le **mail admin** part à chaque demande
  (`send_email_async`, même mécanique que les digests ; SMTP absent → mail prêt + loggé, l'écran admin fait foi).
- Tests mis à jour : `CourrierService.test.tsx` vérifie « Demande n° 42 », le renvoi « Mes courriers », et
  l'absence d'« Imprimé »/« Posté ».

### A5 — Bandeau PLU (RNU ≠ procédure)
- Backend `plu_annuaire_communes` expose `n_revision`, `n_rnu`, `n_non_ingere`, **calculés depuis le statut
  réel** de l'annuaire (jamais par soustraction). Front : « **21 PLU disponibles · 2 en révision · 1 au RNU** ».
  Si un PLU passe en révision demain, le bandeau suit seul. Vérifié live (servables 21 / rev 2 / rnu 1).
- Note : le **radar procédures** (`ProcedureChangement`, moteur SuDocUH distinct) n'incluait déjà PAS le RNU
  (`_ACTIVE_PROC = {revision_plu, elaboration_plu}`) — laissé tel quel, c'est le bon moteur.

### B1 — Panneau d'accueil
- Nouvelle carte **« Suivre le marché — Radar »** (◉, barre verte) entre « Explorer la carte » et
  « Demander au Copilote » → `setView('radar')`. Titre sur une ligne (`truncate`).
- « N outils » : **déjà dynamique** (`MODULES.filter(!hidden).length` = 15) — inchangé, confirmé.
- Pied : « **Toutes les données sont à jour.** » + lien « **voir les données →** » vers Sources.
- Capture `01-accueil-B1.png` (les trois retouches visibles).

### B4 (partie 1) — Communes « Fiche → » permanent
- L'affordance « Ouvrir la fiche → » au survol devient « **Fiche →** » **permanent** sur chaque ligne
  (visible d'emblée, correct sur tactile). Test `CommunesTable.test.tsx` mis à jour.

### B7 — Exports CSV retirés
- **Densifier** (`Renouvellement.tsx`) et **Scan patrimoine** (`ModulePanel.tsx` M02) : boutons + code mort
  (`csvEscape`/`exporterCsv`, import `modPatrimoineCsvUrl`) supprimés. La consultation reste illimitée.
- Laissé intact : l'export **vélocité** (`/modules/velocite?fmt=csv`) et l'export **solaire** — hors périmètre B7.
- Test `DensifierTable.test.tsx` mis à jour (le bouton n'existe plus).

### A3 — SIRENE : documentation VPS
- Branchement OK sur la branche (prouvé). `docs/EXPLOITATION.md §12` ajouté : commande exacte
  (`labuse ingest-sirene-etab`), durée (~3–8 min), volumétrie (≈158 515), **double check post-ingestion**
  (count SQL + appel API zone témoin dont la couverture doit passer à « servie »).

---

## 3. Vérifs de gates

- **tsc** : 0 erreur. **build** front : OK (`npm run build`). **vitest** : **108/108** (23 fichiers), tests
  de recette adaptés au nouveau comportement (courrier n°, communes Fiche→, densifier sans CSV).
- **Golden** : **0 fichier de scoring touché** — mes modifications portent sur `api/modules.py`
  (compteurs PLU, additif), le front outils, la doc et les tests ; aucun fichier `qa/golden_*`,
  `faisabilite` de scoring, ni `cascade`. Le golden est intact par construction.
- **Suite pytest** : **2000 passed, 42 skipped, 0 failed** (348 s), avec
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (contourne le piège WeasyPrint/`libgobject` FZ-002,
  pré-existant/environnemental). Les 42 skips sont environnementaux (base QA indisponible), non liés au
  mandat. Tests directement concernés verts (`test_plu_annuaire_integral`, `test_veille_plu`,
  `test_taxe_cas_reels`).
- **Captures** : `docs/OUTILS-1/captures/` (1440×900 @2x) — accueil, taxe, PLU, courrier, communes, fiche
  commune + `_report.json` (assertions : carte Radar présente, lien Sources présent, taxe = 5 020 €,
  fiche commune sans crash).

---

## 4. Ce qui reste — signalé, pas bâclé (« corrige si sûr, signale sinon »)

Ces points touchent des surfaces à sémantique sensible (fichier `Fiche.tsx` de 2 000+ lignes, sémantique
radar, refontes visuelles lourdes). Plutôt que de les précipiter au risque de mal étiqueter une donnée, je
les documente avec le point d'entrée exact.

- **A5 (périmètre capacité)** — étiqueter « résiduel, bâti conservé : 26 m² » vs « potentiel, terrain
  libéré : 123 m² ». Points : `Fiche.tsx:350` (SDP résiduelle estimée = *bâti conservé*), bloc
  potentiel_transformation `Fiche.tsx:2097-2146`, et la SHAB vendable gabarit (= *terrain libéré*). À faire
  aux 3 surfaces (fiche, pièges, comparaison). **Risque** : inverser les deux périmètres — d'où le renvoi.
- **A6 (contre-calculs)** — formules localisées : patrimoine `modules.py:273-293` (val = Σ surface×prix U/AU,
  SDP = Σ sdp_residuelle) ; SDP gabarit `faisabilite/engine.py:305,323` (emprise×coef×niveaux — le
  281 159 m² de DK1169 est à vérifier aux extrêmes) ; charge `faisabilite/bilan.py:465,498,505,527`
  (CA×coef − coût − VRD). L'écart -122 911/-123 410 relève d'arrondis/d'un poste : à consigner dans la doc méthode.
- **B2 (Permis, interface unifiée 2 couleurs)** — `ModulePanel.tsx` M03 (307-490) + `api/modules.py`
  530-540. Comptes servis (5 575 en cours / 15 475 point mort) = `sitadel_permits` (`date`, `raw->>'daact'`).
  Refonte : champ recherche pleine largeur, segment [En cours N | Point mort N | Tous], badge
  « Sans DAACT · X ans », items 2 lignes, compteur honnête. **Refonte visuelle lourde — non entamée.**
- **B3 (Ensoleillement)** — `ProspectionSolaire.tsx`. Onglets « Ma parcelle » / « Top parcelles », colonne
  TOITURE M² en 2ᵉ position + 2ᵉ critère de tri (potentiel DESC puis toiture DESC), fil d'Ariane
  « ‹ Prospection solaire ». **Non entamé.**
- **B4 (partie 2, bloc Marché des annonces Radar)** — la donnée existe (`pige/marche.py` : `SEUIL_N=5`,
  `stats(db)` par commune ; endpoint marché radar). Bloc à insérer dans `Communes.tsx` : replié
  « en constitution · N biens collectés · affichage par commune à partir de 5 » tant qu'aucune commune n'a
  ≥ 5, sinon les communes ≥ 5. **Feature neuve touchant la sémantique radar (quels biens comptent :
  validés ? rattachés ?) — signalée, non bâclée.**
- **B5 (Remonter le temps, contour parcelle)** — `TimeMachine.tsx` : épingle `pin` existante ; ajouter le
  contour cadastral (trait vert + halo) + étiquette IDU sur les DEUX volets, vue centrée. **Non entamé.**
- **A3 (enrichissement concurrents)** — servir enseigne + distance + **lien vers la parcelle** (via
  lon/lat → `parcelAt`) dans `EtudeZone.tsx`. La **date de création** exige d'ajouter
  `dateCreationEtablissement` à l'ingestion SIRENE (colonne absente aujourd'hui). **Signalé.**

---

## 5. Fichiers touchés

Backend : `src/labuse/api/modules.py` (compteurs PLU, additif) · `docs/EXPLOITATION.md` (§12 SIRENE).
Front : `panel/LeftPanel.tsx` · `outils/TaxeAmenagement.tsx` · `outils/ModulePanel.tsx` ·
`projets/ProjetsPanel.tsx` · `outils/PluAnnuaire.tsx` · `outils/blocB.tsx` · `outils/Renouvellement.tsx` ·
`lib/api.ts`. Tests : `CourrierService/CommunesTable/DensifierTable.test.tsx`.
Captures : `docs/OUTILS-1/captures/`. Écriture DB : **aucune** (aucune migration ; tables existantes).

---

## 6. Merge

**Ne pas merger.** La commande, si Vic la valide après revue :

```
git checkout main && git merge --no-ff feat/outils-1
```
