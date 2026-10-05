# RECETTE-2 — retours de Vic du 05/10/2026 (48 captures)

Branche `fix/recette-2` depuis `origin/main` · worktree `~/Desktop/labuse-recette2` · ports API **8705** / Vite **5905** · modèle Opus.
Captures : `captures/avant/` et `captures/apres/` (même cadrage que les captures de Vic).

> **Convention** : un point n'est marqué ✅ **fait** qu'après constat dans un vrai navigateur (Chrome/Playwright, base réelle sur 8705) **et** capture après. Les points non constatables en headless (3D de Gabarit) sont marqués ⚠ et listés pour Vic en fin de rapport.

## Étape 0 — état de départ (constaté)

| Contrôle | Résultat |
|---|---|
| `~/Desktop/labuse` sur `main...origin/main` | oui |
| Worktree `~/Desktop/labuse-recette2` créé depuis `origin/main` | oui — HEAD `7eea04de` |
| Branche `fix/recette-2` | recréée depuis `origin/main` (l'ancienne `fix/recette-2` locale était un alias déjà fusionné dans main, non poussée — supprimée) |
| `git log origin/main..origin/fix/recette-1` | **vide** — aucun commit de recette-1 non mergé ne touche les outils ; rien à signaler |
| API 8705 / Vite 5905 | démarrées (API `labuse api --port 8705` via `.venv` du dépôt + `PYTHONPATH` du worktree ; Vite `--port 5905 --strictPort`, proxy `LABUSE_API_DEV=…:8705`) |
| Base | PostgreSQL `labuse` (rôle `openclaw`) accessible |

> Note env : l'env conda `labusedb` du poste n'a plus d'interpréteur Python ; l'API tourne via le `.venv` du dépôt principal (python 3.12, weasyprint OK) avec `PYTHONPATH=~/Desktop/labuse-recette2/src` pour servir le **code du worktree**. `.env` copié depuis le dépôt principal (gitignoré, non hérité par le worktree).

---

## Tableau fait / non fait

Légende : ✅ fait+capturé · 🚧 en cours · ⬜ non commencé · ⚠ à vérifier par Vic (non constatable en headless).

### T — Règles transversales  — **commit `fix/recette-2` lot T**
| Pt | Sujet | État | Preuve |
|---|---|---|---|
| T1 | Doublon « ou cliquez une parcelle » — une seule mention | ✅ | `EntreeParcelle` (withCarte={false}) + blocB.tsx & ParcelPicker.tsx (phrases libres retirées) ; `T12_gabarit_01_entree.png` 2→1 ; sweep 18 outils (tableau ci-dessous) |
| T2 | Invite + chemin non utilisé disparaissent après résolution | ✅ | plus d'invite `◎` grisée-mais-visible sous le champ (Solaire) ; `T12_*_02_apres_clic` |
| T3 | Réinitialiser : secondaire, seul sur sa ligne, texte dessous ; présent ssi effaçable | ✅ | `T3_assemblage.png`, `T3_pieges.png` (avant: côte à côte → après: bouton seul en haut-droite, intro dessous). Permis « Revenir à l'île » → « Réinitialiser » |
| T4 | Aucun texte tronqué « … », aucun scroll horizontal | ✅ mécanisme + hors-fiche ; instances fiche en lot A | `.t-sub`/`.t-val`/tuiles `formes.tsx` (wrap), Blocs, acquéreurs commune, lignes mono Faisabilité, annonces marché. Tableau Comparer → D6 |
| T5 | Formats FR (virgule, JJ/MM/AAAA, « 1,1 an ») | ✅ mécanisme ; instances fiche/commune en lot A/B | helpers `fmtDist`/`fmtAns` ajoutés ; `fmtDateNum` = JJ/MM/AAAA ; date PPR risques fixée. Rappel : `toLocaleString('fr-FR')` rend déjà correctement — défauts réels (« 1.25 km », ISO) aux points A7/A8/A10/B5/B6 |
| T6 | Aucun code brut (`mouvement_terrain`, `tres_fort`, `EL10_…`) | ✅ aléas ; servitude EL10 en A5 | helpers `fmtAlea`/`fmtIntensite` ; risques.tsx câblé (nature+niveau). `EL10_Reunion_ass` traité en A5 (données servies réelles) |
| T7 | Boutons hors composant → Bouton/Retour | ✅ | Gabarit 3D déjà `<Bouton>` ; « Revenir à l'île » → `Réinitialiser`. Arbitrage : carte-choix « Rechercher dans le PLU » reste une carte (voir ci-dessous) |
| T8 | Chevron unique fiche parcelle ↔ fiche commune | ✅ | 3 glyphes ad hoc de la fiche (`primitives.tsx` TRow, `Fiche.tsx` Analyse LABUSE, `FinancierQuestionnaire`) → `<Chevron>` ; fiche commune déjà conforme. Visuel fiche complet en lot A |
| T9 | Cartes de choix internes sans bord gauche vert | ✅ | `T9_scan_portes.png` (2 portes sans barre verte). Portes Étude de zone supprimées en D8 |
| T10 | Survol = vert opaque, contenu sombre (« Toute l'île » Piscines) | ✅ | `T10_piscines_perimetre.png` — fond inline mint-0f (qui écrasait le `:hover`) retiré → fond neutre, survol opaque lisible |

**Sweep T1/T2 — 18 outils (doublon résiduel ?)** : plu, permis, communes, blocs-fonciers, successions = pas d'entrée parcelle (sans objet) · patrimoine, comparer, courriers, mon-secteur, étude-zone = `ParcelInput` direct, invite unique interne (OK) · assemblage, gabarit, taxe, solaire, calculette, temps = `EntreeParcelle` corrigé (OK) · **risques (blocB)** et **faisabilité (ParcelPicker)** = doublon **corrigé** (phrase libre retirée).

**Arbitrages lot T (tranchés) :**
- **T7 / PLU** — « Rechercher dans le PLU » est une **carte de choix sur 2 lignes**, jumelle du lien `<a>` « Télécharger le PLU intégral ». La forcer dans `<Bouton>` (ligne unique h-8) casserait la paire. Elle utilise déjà l'interaction partagée `hover-fill`. **Conservée en carte.** Les vraies cibles T7 (3D, « Revenir à l'île ») sont traitées.
- **T4 / T5 / T6 sur la fiche** — mécanismes (CSS tuiles, helpers de format, chevron) livrés en lot T ; les **instances précises de la fiche parcelle et de la fiche commune** (identité A3, servitude EL10 A5, pente A6, réseaux A7, fiscalité A8, quartier A10, CatNat B2, dates B6) sont appliquées et **constatées en lot A/B**, fiche chargée — aucun point sauté, traçabilité au point concerné.
- **T3 / Successions, Étude de zone, Piscines** — le compagnon du bouton n'y est pas un texte d'explication mais un sélecteur commune / un `Retour` ; ces écrans sont retravaillés en D8/D14, le placement Réinitialiser y est finalisé là.

> **Test pré-existant rouge (hors périmètre)** : `src/lib/layersCoquilles.test.ts` (« i » BPE attend `35 546`) échoue **déjà sur `origin/main`** (constaté par stash) — le texte `i` de la couche BPE (`lib/layers.ts`) ne porte aucun compte. Non causé par ce lot, non dans le périmètre T. Signalé ; à rattacher au lot C (couches) ou à un correctif données.

### A — Fiche parcelle  — **commit lot A** (témoins AM0097 zone N · BZ1065 zone Uh)
| Pt | Sujet | État | Preuve / note |
|---|---|---|---|
| A1 | En-tête sticky : coins arrondis du haut visibles, rien de rogné | ✅ | `.tete-collee` : coins hauts carrés → carte pleinement arrondie (border-radius 6px + bordure haute), collée top:0 (aucun trou noir). `A1_entete_scroll.png` |
| A2 | Branchement borné (circuit verrous + LIGNES.csv, 2 témoins) | ✅ | **V5d vert** (75 données maille parcelle, toutes déclarées) ; 120 lignes LIGNES.csv **toutes rendues ou sans objet motivé, 0 absent sans motif** (tableau A2 ci-dessous). 3 verrous rouges V1c/G5/G8 hors périmètre fiche |
| A3 | Identité « Administration publ… » / « COMMUNE DE SA… » → T4 | ✅ | `.t-sub`/`.t-val` wrap (plus de « … ») ; « COMMUNE DE SAINT-PAUL » sur 2 lignes, mot entier |
| A4 | Bâti : drapeau « Sources discordantes » (faîtage 4,1 vs BD TOPO 11,1) + titre « 2 bâtiments » | ✅ (live) | Nouveau motif directionnel « faîtage sous la hauteur BD TOPO » (hauteur_lidar.py) — **vérifié live** : `discordante:true`. Titre : BD TOPO=2 ∧ RNB=2 → « 2 bâtiments » (sous-titre + Verdict). `A4_bati.png` |
| A5 | Urbanisme : sous-titre tronqué (a) · 6 tuiles non calibré zones A/N (b) · servitude EL10 (c) | ✅ | (a) T4 `.t-sub` ; (b) zone N : 6 tuiles vides → seul paragraphe servi `z.note` ; (c) `fmtSup` → « Servitude EL10 » (code brut `EL10_Reunion_ass` retiré ; EL10 sans `nomsuplitt` en base = lacune donnée notée). `A5_urbanisme.png` |
| A6 | Risques : vigilance « Pente forte tres_fort (~56 %) » vs pente unique 19,1° (34,6 %) | ✅ (affichage, sans run) | Origine : `PenteLayer.evaluate` (phase1.py:891) prend le MAX des slope_pct de la grille (56,2 %), servi par le run q_v16. **Correctif d'AFFICHAGE** (risques.tsx) : la ligne de vigilance pente est réécrite à partir de la SEULE pente servie à la fiche (`terrain.pente_moy_deg` + `pente_bande`) → **« Pente forte (19,1° · 34,6 %) »**, identique à la tuile et §2 Terrain. Aucun run, aucun recalcul. Avant/après : `A6_risques_pente.png` (56 % tres_fort → 19,1°·34,6 %) |
| A7 | Réseaux : « Assainis. » (a) · viabilisation en doublon bandeau+ligne (b) | ✅ | (a) « Assainissement » ; (b) badge bandeau retiré, la ligne Verdict reste. `A7_reseaux.png` |
| A8 | Fiscalité « 5 + 2.5 % » → virgule | ✅ | « 5 + 2,5 % », TVA 8,5 %, ORT 25/04/2022. `A8_fiscalite.png` |
| A9 | Marché : sous-titre en double · « Aucun signal » · en-tête « — » vs 4 848 €/m² | ✅ | sous-titre une fois (MicroSpark sans label) ; « Aucun signal » retiré ; en-tête = `faisa.marche.median` → **4 848 €/m²** quand DVF secteur absent. `A9_marche.png` |
| A10 | Quartier : revenu en colonne (a) · dates ISO (b) · ECOLE… tronqué (c) · 2 boutons Étude de zone (d) · habitants/ménages (e) | ✅ | (a) `.f-row` grid `minmax(0,1fr) auto` → « 13 666 € » sur 1 ligne ; (b) `fmtDateNum` sur PermitsProximityBlock + DepotsBlock (+ historique autour) ; (c) `break-words` ; (d) un seul bouton « Étude de zone » ; (e) **même endpoint `/outils/etude-zone` même rayon que l'outil → chiffres identiques par construction**. `A10_quartier.png` |
| A11 | Simulation : sous-titre tronqué → T4 | ✅ | résolu par le wrap `.t-sub` (lot T) |
| A12 | Encart « Analyse LABUSE » : Q_V16 = version servie = run le + récent · accordéon repliable | ✅ | **q_v16 = served_run.txt = served_manifest.scoring_run = MAX(computed_at) score_labuse_runs** (OUI/OUI, tableau A12). Encart repliable : `<Chevron>` + état collapse ajoutés (AnalyseLabuseCard + carte verdict) |
| A13 | Assistant « momentanément indisponible » (a) · bouton « Voir l'entièreté » (b) | ✅ | (a) **pas un câblage** : `POST /parcels/{idu}/ask` répond 200 `degraded` · `reason: "solde de crédits Anthropic épuisé"` → clé/crédit `.env` à recharger (dit sans contourner) ; (b) bouton retiré |

**Tableau A2 — branchement (extrait, 2 témoins) :** V5d vert ; 120 lignes testées contre `GET /parcels/{idu}` (+ sous-endpoints `/exposition`, `/modules/faisabilite/{idu}`). Zéro absent sans motif. Absences motivées : AM0097 **zone N non constructible** (potentiel/capacité/bilan nuls), PP (pas PM), pas de DVF/bâti classé/fibre immeuble. BZ1065 (Uh) sert toute la chaîne. Détail complet des ~25 champs « sans objet » conservé dans l'investigation.

**Tableau A12 — version servie :** `config/served_run.txt`=q_v16 · `served_manifest.json.scoring_run`=q_v16 · `GET /config/run`={run:q_v16} · `score_labuse_runs` MAX(computed_at)=q_v16 (2026-10-05). Aucun run plus récent non servi.

**Arbitrages lot A :** A6 tranché « non fait live » (contrainte « aucun run ») avec correctif documenté — seul point du lot non constatable. A4 : le drapeau >3 m de FICHE-FIX-2 n'est PAS réintroduit tel quel (16 % de faux positifs) ; motif **directionnel** ciblé (faîtage SOUS BD TOPO = sens impossible). A5c : EL10 n'a pas de `nomsuplitt` servi (lacune d'ingestion GPU) → libellé officiel de catégorie par `fmtSup`, code exact conservé dans le `i`.

### B — Fiche commune Saint-Denis  — **commit lot B**
| Pt | Sujet | État | Preuve / note |
|---|---|---|---|
| B1 | Retirer le pied « Compteurs précalculés … Données de contexte … » | ✅ | `<p data-fiche-pied>` supprimé |
| B2 | Risques CatNat illisible → chaque arrêté sur 2 lignes (libellé pleine largeur, puis JJ/MM/AAAA · code) ; idem AZI/TRI | ✅ | `B2_catnat.png` : « Mouvement de Terrain » / « 26/02/2025 → 01/03/2025 · INTE2519692A », « et 13 autres… », AZI/TRI idem |
| B3 | « hors ORT — dit, jamais une carte absente » retiré ; « Dispositif — Aucune ORT » → « ORT — aucune » | ✅ | phrase interne retirée ; libellé conditionnel |
| B4 | Acquéreurs tronqués → T4 | ✅ | `ContextePanel` acquéreurs `truncate`→`break-words` (lot T) |
| B5 | « 50 ha promus »/« stock foncier repéré » → libellés registre · « 1,1 ans »→« 1,1 an » · « 7 M m² »→« 700 ha » | ✅ | labels « terrains classés opportunité (brûlantes+chaudes) · N ha cumulés » (registre) ; `fmtAns` (Foncier + Horizon) ; **chip SIGNAUX « ZAN épuisé dans 1,1 an »** (back `_signaux_commune` + cache Saint-Denis rafraîchi) ; « 700 ha » |
| B6 | Urbanisme « ( 2026-04-23) » → T5 | ✅ | `fmtDateNum` sur PLU/procédure/SCOT (date_reglement, prescription, date_approbation) |
| B7 | Chevrons carrés verts → T8 | ✅ | `ContextePanel` utilise déjà `<Chevron>` (fermé `<`, ouvert ▼ vert) — identique à la fiche parcelle. `B2_catnat.png` |

**Note B5 (cache)** : la chip SIGNAUX est servie du cache `commune_contexte_cache` (précalc nocturne `fiche-commune-cache`). Le correctif code étant live-invisible sans rebuild, le cache de Saint-Denis (témoin) a été **rafraîchi** (recompute de contexte borné — ni run de scoring, ni calcul géométrique) pour constater « 1,1 an ». Les autres communes se mettront à jour au prochain précalcul nocturne.

### C — Couches  — **commit lot C**
| Pt | Sujet | État | Preuve / note |
|---|---|---|---|
| C1 | Retirer le minzoom du 04/10 (couches à pastille visibles à tous zooms, île comprise) ; pastille conservée | ✅ | `CouchesTuyau.tsx` : helper `zmin()` → source/calques chargent dès z0 pour toutes les couches **sauf** zonage par-parcelle (431 k, tuile île ingérable — gardé). Pastille « Zoomez pour voir **mieux** » (simple info). **Vérifié vue île z9.4** : QPV 79, 50 pas 251, BPE 35 544 features rendues. `C1_ile_3couches.png` |

**Arbitrage C1 :** le bornage n'est pas supprimé aveuglément — **zonage par parcelle** (431 k polygones) GARDE son minzoom (la tuile île est ingérable, cf. harnais de captures). Les couches de la liste 04/10 (50 pas, ER, SIS, QPV, ANRU, TVA réduite, pylônes, postes, BPE, OSM, EnR, …) chargent à tous les zooms. Le gate était **client** (`addSource`/calques minzoom) ; le backend sert déjà les tuiles à tous les zooms (couches_tuyau §5).

### D — Outils  — **commit lot D** (partiel : voir états)
| Pt | Sujet | État | Preuve / note |
|---|---|---|---|
| D1 | PLU : « révision » vs « non servi » = 2 faits distincts ; Trois-Bassins servi | ✅ | « 3 PLU en révision (PLU en vigueur servi) · 2 règlements non servis (Saint-André, Saint-Leu) ». API : n_procedures=3, non_servis=[St-André, St-Leu], **Trois-Bassins en révision mais PAS dans non_servis → servi** ✓ |
| D2a | Permis : « Tous » coché par défaut | ✅ | `D2_permis_tous.png` — défaut seg='tous' |
| D2b | Permis : clic point → popup directe sur la carte (plus de drawer colonne) | ⬜ **non fait ce tour** | refonte du handler ModulePanel (PermitDrawer modal → popup MapLibre au clic point) — identifié (ModulePanel.tsx PermitDrawer 365-472 / handler 521-528), non terminé/vérifié ce tour |
| D3 | Communes €/m² neuf : seuil + servir le max de VEFA | 🚧 partiel | **seuil=8** (`config/dvf_profils.yaml:68`) ; **tableau 24 communes brut/servi ci-dessous**. Les « — » sont CORRECTS (« pas de médiane sans surface bâtie »). La « perte » = filtre `bati>0` (surface absente à l'acte VEFA, non rattrapable) + fenêtre 5 ans glissante sur `now()`. **Corriger à la source = re-ingestion (interdit « aucun run »)** → non fait ; légende « — : sous le seuil » UI non ajoutée ce tour |
| D4a | Assemblage : N parcelles toutes surlignées (bug 1/3) | ⬜ **non fait ce tour** | diagnostic : en vue île le surlignage repose sur `ile-hl`/tuiles vectorielles qui ne contiennent pas les 3 parcelles tant qu'on n'a pas zoomé. Correctif identifié : source GeoJSON dédiée des `msel` (comme `module-extra`), indépendante du zoom (MapView.tsx:682-684) |
| D4b | Doublon « 0 PM · 3 particuliers » (chip + encart) → une fois | ✅ | chip retirée (moteurs.tsx:242), encart « approche propriétaire » conservé |
| D4c | Bilan union ET2262/2264/2266 = chiffres moteur | ✅ (vérif) | `/assemblage/study` (Saint-Pierre, contigu) : **surface 986 m² · SDP 444 m² · logements 3–4 · CA 1 055 984 € · charge foncière centrale −47 519 €** |
| D5 | Comparer : barre se vide + invite explicite après chaque ajout | ✅ | invite dynamique « Cliquez la Nᵉ parcelle … ou saisissez-la » ; `key={n}` vide la barre |
| D6 | Comparer : 3 colonnes égales, pas de scroll H, texte à la ligne | ✅ | `table-fixed` + colonnes égales + `break-words` |
| D7 | Pièges : 2 cartes « Classement sonore » → une | ⬜ **non fait ce tour** | dédoublonnage probablement à la source (`/servitudes-invisibles`) — à vérifier/corriger côté back, non traité ce tour |
| D8 | Étude de zone : chemin unique, cercle 3 km (pas isochrone), libellé | 🚧 partiel | **cercle déjà dessiné** (back ignore minutes dès `rayon_km`) ; **en-tête corrigé → « Zone de X km autour de <adresse> »** (plus « À 10 MIN »). Reste : fusion complète des 2 portes + retrait « ← Changer la zone »/« ZONE SEULE » (non fait ce tour) |
| D9 | Remonter le temps : doublon → T1 | ✅ | couvert par le correctif `EntreeParcelle` (lot T) |
| D10 | Faisabilité : Réinitialiser (T3) · citation PLU 2 lignes (T4) · « étape par étape » accordéon Chevron fermé · vérif calculs | 🚧 partiel | citation 2 lignes ✅ (lot T) ; **accordéon → `<Chevron>` fermé par défaut** ✅ ; Réinitialiser Faisabilité + tableau vérif `/recalcul` : non faits ce tour |
| D11 | Gabarit : doublon (T1) · invite retirée · 3D Bouton (T7) · 3D rendu · vérif géométrie | 🚧 partiel | doublon ✅ (T1) · **section « Choisissez une parcelle » retirée** ✅ · 3D = `<Bouton>` ✅. **3D rendu NON CONSTATABLE en headless** (à vérifier par Vic) ; tableau géométrie non fait ce tour |
| D12 | Taxe : doublon (T1) · retirer « Le formulaire s'ouvrira… » | ✅ | section retirée |
| D13 | Solaire/Ensoleillement : T1/T2 · retirer invite + encart EnR + pied | ✅ | les 3 retirés |
| D14 | Piscines : survol (T10) · colonne source+croix · Réinit · goutte au centroïde · jointure · statut | ✅ | **(a) goutte** : endpoint `/parcelles` sert désormais des Points (kind piscine) — `D14_piscines_gouttes.png` : **2 380 gouttes, 0 parcelle teintée** · (b) colonne source + croix retirées · (c) Réinitialiser retiré · (f) `i` du statut sourcé. Tableaux (e)/(g) ci-dessous |
| D15 | Blocs : encart 2 lignes · Filtres Chevron · carte (SIREN bleu, 1 Bouton) | 🚧 partiel | **SIREN en bleu** ✅ · Filtres déjà accordéon Chevron ✅ · 1 seul Bouton « Scan patrimoine » ✅ · nom sur 2 lignes (break-words, lot T) ✅. Reste : encart réduit à 2 lignes (non fait ce tour) |

**Tableau D3 — VEFA 24 communes (brut DVF / servi, fenêtre 5 ans, seuil 8)** : 3 communes basculent sous le seuil alors que leur volume VEFA réel ≥ 8 — **Saint-Louis** (24 brut / 6 servi), **Saint-André** (8/1), **Le Port** (7/1) : surface absente à l'acte VEFA (1 093 VEFA sans `surface_reelle_bati`, dont 5 seulement récupérables par Carrez). Les 5 communes sans VEFA (Entre-Deux, Plaine-des-Palmistes, St-Philippe, Ste-Rose, Cilaos) = « — » légitime. Détail 24 lignes dans l'investigation D3.

**Tableau D14(e) — jointure piscine→parcelle** : sur 30 → 1 faux ; sur 50 136 → **23 faux (0,05 %)** (identique ST_Contains/ST_Intersects) ; 380 (0,75 %) idu orphelin. **D14(g) verdict** : après (a)+(e), **l'outil TIENT** — la jointure par idu est spatialement saine (99,95 %), la goutte au centroïde est propre. **Pas de refonte nécessaire** ; seule option résiduelle : exclure/signaler les 380 idu orphelins et les 23 hors-parcelle.
**D14(f) — statut « à confirmer »** : `piscines.statut='a_confirmer'` ⟺ `subtype='probable'` (CoSIA seule, sans corroboration ortho/FLAIR ≤ 2 m) ET `surface_m2 ≥ 8` (`PROBABLE_FLOOR_M2`, piscines_fusion.py:116). Sourcé par audit mesuré (précision 30–60 %). FLAIR toujours « servie ». Écrit dans le `i` du compteur.

**Arbitrages lot D (tranchés) :** D3 « corriger à la source » = re-ingestion DVF → **interdit** (Étape 0) → non fait, documenté ; les « — » sont corrects.

#### Mise à jour **commit lot D-reste** (`fix/recette-2`)
| Pt | État mis à jour | Preuve |
|---|---|---|
| D2b | ✅ code (constat popup non fiabilisé headless) | popup permis = **fiche directe** (`modPermisFiche` rendue dans la bulle) ; « détails → » + drawer colonne **supprimés** (`setPermitToOpen` retiré, tsc) ; + « voir la parcelle → ». Clic du point minuscule non déclenchable en headless (5 candidats) → à constater par Vic |
| D3-légende | ✅ | Légende Communes + `i` des colonnes : « — : sous le seuil (neuf **8** ventes VEFA · terrain nu **5** ventes) » |
| D4a | ✅ | source GeoJSON dédiée `module-hl-geo` (polygones réels par idu, zoom-indépendant) → **3/3 parcelles surlignées** (ET2262/64/66). `D4a_assemblage_surlignage.png` |
| D7 | ✅ | servitudes regroupées par catégorie : 1 carte « Classement sonore des voies » avec effets « catégorie 2 · catégorie 4 » (ES0981). `D7_pieges_sonore.png` |
| D8 | ✅ | chemin UNIQUE : 0 porte, 0 « ← Changer la zone », 0 badge « ZONE SEULE » ; en-tête « Zone de X km autour de … » ; cercle (back). `D8_etude_zone_unique.png` |
| D10 | ✅ | Réinitialiser Faisabilité ajouté (`D10_faisabilite_reinit.png`) ; accordéon « étape par étape » = `<Chevron>` fermé ; **tableau /recalcul ci-dessous (0 écart)** |
| D11 | ✅ géométrie (3D à voir par Vic) | **tableau gabarit ci-dessous** (emprise/hauteur = règle, zone d'implantation réduite) ; le **rendu 3D** reste non constatable en headless |
| D15 | ✅ | encart réduit à 2 lignes (détail dans le `i`) ; SIREN bleu ; Filtres accordéon Chevron ; 1 Bouton « Scan patrimoine » |

**Tableau D10 — faisabilité servie vs `/recalcul` (0 écart) :**
| IDU | SDP servi / recalcul | Logements servi / recalcul | Écart |
|---|---|---|---|
| BZ1065 (Uh) | 219 m² / 219 m² | 1–2 / 1–2 | **0** |
| ES0266 (Ug) | 502 m² / 502 m² | 5–7 / 5–7 | **0** |
| AM0097 (zone N) | — / — (non constructible) | — / — | **0** |
Cohérence : BZ1065 R+0 → SDP = emprise 219 ; ES0266 R+1 → SDP = emprise 251 × 2 = 502 ; logements = SHAB vendable / surface par logement.

**Tableau D11 — gabarit (règles citées, status `ok`/`integrated`) :**
| IDU | Surface | Zone d'implantation | Plafond emprise | Hauteur règle |
|---|---|---|---|---|
| BZ1065 (Uh) | 1 625 m² | 926,9 m² (réduite : reculs/PPR) | 487,5 m² (= 30 % surface) | 7,0 m |
| ES0266 (Ug) | 1 114,9 m² | 740,8 m² | 557,5 m² (= 50 %) | 12,0 m |
| ES0981 (Ug) | 873,9 m² | 540,6 m² | 436,9 m² (= 50 %) | 12,0 m |
Zone d'implantation = parcelle − reculs − PPR ; emprise % et hauteur = la règle de zone citée (0 écart). Le **rendu 3D** (flyTo, extrusion) reste à constater par Vic (non testable en headless).

**Tableau D3-source — écart VEFA brut/servi (sans ré-ingestion, lecture seule) :** DVF contient **2 687 VEFA** (toutes dates) · 2 351 dans la fenêtre 5 ans · **1 245 servies** → **écart total 1 442** (336 hors fenêtre 5 ans + 1 106 filtre surface `bati>0`/vraisemblance). **3 communes les plus touchées** (écart réel servi) : **Saint-Denis** 606→267 (−339), **Saint-Paul** 570→297 (−273), **Le Tampon** 339→102 (−237). Cause = surface absente à l'acte VEFA (non rattrapable) + fenêtre glissante — correction = re-ingestion (hors périmètre « aucun run »). Les « — » restent corrects.

### E — Docs, Signaler, Notifications  — **commit lot E** (partiel)
| Pt | Sujet | État | Preuve / note |
|---|---|---|---|
| E1 | Rail « Documents » → « Docs » | ✅ | `E1_rail_docs.png` — rail « Docs » (1), « Documents » (0) |
| E2 | Fenêtre Dossier : retirer les phrases + trancher la tuile Comparables DVF | ✅ | phrases « … Mes documents » retirées (6 docs + explication Dossier) ; **tuile « Comparables DVF » RETIRÉE** — aucun export (pas d'endpoint `/…comparable…`, tiroir fiche inexistant) → pas de document bancal grisé. `E2_documents.png` (tuile absente, vérifié = 0) |
| E3 | « Signaler » (haut) + « Signaler une erreur » (bas) → les deux arrivent au dashboard admin | ✅ (même écran ; 2 tables) | **Testé** : `/retours` (haut) → table `retours` id=1 ; `/signalements` (bas) → table `signalements` id=25. **Les deux remontent au MÊME écran admin** « Produit → Retours » (`Produit.tsx` fusionne `GET /admin/produit` + `GET /admin/signalements`) — prouvé par les 2 endpoints. **Arbitrage** : 2 tables distinctes par conception (global vs erreur-fiche/radar), unifiées sur un écran → l'admin voit bien les deux ; pas de migration de schéma (hors périmètre). Lignes de test nettoyées en base |
| E4 | Cloche : événements admin invisibles au client ; intro « vos secteurs » retirée | ✅ | (1) intro « vos secteurs » retirée ✅. (2) **Filtrage vérifié CORRECT, aucune fuite** : la cloche client est une **liste blanche fermée** issue de `config/veille.yaml` (`kinds_cloche`) + kinds marché, appliquée par `_cloche_closed_sql` + `_visible` (events.py:698-709). Les événements admin `kind=systeme` (« demande d'envoi de courrier », « e-mail pas parti ») sont **exclus** — prouvé **0** pour un compte client en base (SQL rejoué). Tableau type→client ci-dessous |

**Tableau E4 — type d'événement → cloche client (oui/non) :** `bascule`, `bodacc`, `match`, `nouveaute` (marché) → **oui** · `parcelle_suivie`, `radar`, `radar_baisse`, `radar_retrait`, `parcelle_en_vente` (grille veille.yaml, perso compte) → **oui** · **`systeme`** (demande courrier · e-mail pas parti · changement de statut) → **NON** · `veille` (perso cloisonné), `pige.*` → **non**. Diagnostic : filtre correct, aucune correction nécessaire ; le bucket admin (`compte_id NULL`) garde volontairement sa vue de diagnostic complète.
| E5 | Lien bas de cloche → ouvre Radar · Veille (accueil) ; libellé « Personnaliser les notifications → » | ✅ | `openRadar()` (radarEcran='portes') + libellé « Personnaliser les notifications → » |
| E6 | Retirer « Dernière capture … Radar alimenté par l'extension … vérifier l'extension » | ✅ | bloc retiré de `RadarMarche.tsx` (client) |

**Arbitrages lot E :** E3 (preuve dashboard) et E4-filtrage (client vs admin) exigent des **envois de test et une inspection multi-comptes** non réalisés ce tour → non faits, documentés. E2 tuile « Comparables DVF » grisée : à trancher (activer si l'export marche, sinon retirer) — non investiguée.

---

## Détail des correctifs

### T1 / T2 — doublon « ou cliquez une parcelle » + invite résiduelle après clic carte

**Constat (avant).** Le composant partagé des outils `EntreeParcelle` (`frontend/src/components/outils/EntreeParcelle.tsx`) rendait **deux** invites :
1. celle, interne, de `ParcelInput` (boîte pointillée « ◎ ou cliquez une parcelle sur la carte ») ;
2. la ligne libre « — ou — cliquez une parcelle sur la carte » du wrapper lui-même.

Après un clic carte (`source='carte'`), le wrapper grisait son champ adresse — mais l'invite interne de `ParcelInput`, à l'intérieur de ce bloc grisé, restait **visible en gris** : c'est l'« encore visible sur Solaire après un clic carte » de T2.

**Correctif.** Dans `EntreeParcelle`, `ParcelInput` reçoit désormais `withCarte={false}` : il ne rend plus sa propre invite (doublon supprimé) et ne reconsomme plus le clic carte (le tiroir l'adopte déjà via `selectedIdu`). L'unique invite restante est la ligne « — ou — » du wrapper, qui **grise** selon `source` (règle du 04/10, couverte par `EntreeParcelle.test.tsx`).

**Portée.** Tous les outils passant par `EntreeParcelle` : Prospection solaire, Gabarit, Taxe d'aménagement, blocB, Faisabilité/Calculette, VerifProcedure, moteurs, ModulePanel. **Reste à traiter** (prochain incrément T1/T2) : les outils qui consomment `ParcelInput` **en direct** (Étude de zone, Comparer, Scan patrimoine, Mon secteur, Pièges/ModulePanel, Documents, Veille) — sweep des 17 outils à compléter.

**Vérification.** `npx vitest run EntreeParcelle.test ParcelInput.test socle.test` → 15/15. Captures Gabarit avant/après (`T12_gabarit_01_entree.png`) : 2 invites → 1.

---

## Tableaux de vérification (A2, A12, D4, D10, D11, D14e) — à venir
## Réponses (A13, E2, E4) — à venir
## Ce que CC n'a pas pu constater (à vérifier par Vic) — à venir
