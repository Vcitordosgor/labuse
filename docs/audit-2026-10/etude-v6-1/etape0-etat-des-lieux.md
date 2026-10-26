# ÉTUDE V6 — Étape 0 : état des lieux de l'existant

Worktree `~/Desktop/labuse-etude-v6`, branche `feat/etude-v6`, ports 8860/6060.
Inventaire fait le 2026-10-21 (3 agents Explore + vérifications directes). But : savoir ce qu'on **adapte** (jamais réécrire).

---

## A. Moteur d'implantation — `src/labuse/implantation/`

Entrée unique : **`service.etudier_payload(session, entree) -> dict`** (service.py:192-323). Consommé par la route **`POST /modules/etude`** (+ `/modules/etude/pdf`).

| Fichier | Rôle |
|---|---|
| `service.py` | Orchestration ; parse modes `propose`/`saisi` ; assemble scénarios + GeoJSON + règles |
| `moteur.py` | Recherche déterministe (grille forme×niveaux×fraction = 225 candidats), évaluation, Pareto, `etudier_multi()` |
| `terrain.py` | Assiette (ST_Union + contiguïté 0,5 m), clip zone U/AU, reculs, **PPR live**, pente LiDAR ; `charger()` |
| `geometrie.py` | Repère 2975 ; pose barre/deux_barres/L, stationnement, espaces libres |
| `capacite.py` | Capacité **mesurée** sur la géométrie dessinée ; barème stationnement |
| `controles.py` | 11 contrôles réglementaires + **4 états** + verdict global |
| `regles.py` | Chargeur règles PLU calibrées (hauteur, emprise, reculs, pleine terre, mixité, stationnement, distance, prospect) |
| `conventions.py` | Hypothèses géométriques (profondeurs, modules, coursive…) + `avec_surcharges()` |
| `contexte.py` | Voisins, bâti BD TOPO, voies nommées, TN — pour la planche |
| `planche.py` | SVG plan masse + coupe (écran == PDF), numérotation `EF-AAAAMMJJ-XXXX` |
| `rendu.py` / `format.py` | Export PNG/JSON (tests) / format FR insécable |

**Modes** (service.py:220-229) : `programme=None` → *propose* ; `programme.mode="saisi"` + lignes type/nombre/surface → *je saisis* (`_programme_vers_demande`). Mesure jamais inversée (capacité ← géométrie).

**Contiguïté** (terrain.py:177-194) : `TOL = 0.5` m, fermeture morphologique `buffer(TOL/2).buffer(-TOL/2)`, morceaux >1 m² ; sinon `ValueError` « parcelles non contiguës ». Pas de parcours de graphe explicite (la fermeture PostGIS garantit la composante unique).

**Zone constructible** (terrain.py:198-250) : contenance via `faisabilite.zone_servie.zone_dominante()` (familles U/AU, `pct_constructible`, **sourcé PLU, pas recalculé**) ; clip géométrique `_zone_constructible` si écart >0,5 % ; reculs voie (défaut 4 m) / séparative (défaut 3 m) sur le **contour cadastral réel** ; **PPR rouge soustrait**, **PPR bleue signalée seulement**.

**Pareto** (moteur.py:321-347) : domine si `logements≥`, `shab≥`, `nb_bâtiments≤` + une inégalité stricte. Sortie ≤ 3 scénarios triés par objectif (`equilibre/plus_logements/plus_surface/plus_simple`).

**Contrôles — 4 états littéraux** (controles.py:25-28) : `"Réussi"`, `"Échoué"`, `"Non effectué"`, `"Non applicable"`. **Verdict global** (statut_etude:352-369) : `"simulation impossible"`, `"à compléter"`, `"exploitable en pré-faisabilité"`. 11 contrôles : CES, hauteur, prospect, reculs, perméabilité/pleine terre, stationnement, distance entre constructions, locaux vélos/déchets, PPR rouge, PPR bleue, ER/EBC/SUP.

**division-or : ABSENT de `implantation/`** → à localiser dans `labuse.faisabilite`/module division (requis Lot D).

---

## B. Frontend — `frontend/src/`

| Pièce | Chemin | Note |
|---|---|---|
| Programme/étude | `components/outils/M22Programme.tsx` (842 l.) | `M22({embedded, initialIdus, onBilan, onClose})` ; **2 états** (config → scénarios), pas 3 étapes |
| Overlay | `components/outils/EtudeEcran.tsx` | monte M22 `embedded`, Échap ferme |
| Store | `store/useApp.ts:990-995` | `etudeIdus: string[]|null`, `ouvrirEtude(idus)`, `fermerEtude()` ; `CLOSE_OVERLAYS` remet à null |
| Plan masse | `components/outils/PlanMasseSvg.tsx` | injecte `planche_svg` serveur ou fallback GeoJSON |
| Client API | `lib/api.ts:2195` | `postEtude(EtudeIn) -> EtudePayload` sur `/modules/etude` ; `ETUDE_PDF_URL=/modules/etude/pdf` |
| Tests | `Faisabilite.test.tsx`, `Etude.test.tsx`, `EtudeDocs.test.tsx` | verdict, PLU sourcé, hypothèses, scénarios, overlay |
| Design system | `components/ui/` + `tailwind.config.js` | `Bouton` (3 niveaux × 4 tons), `Badge`, `Case`, `Seg`, `Section`, tokens noir/vert (`mint`, `bg-*`, `txt-*`) — **aucun jeton nouveau** |

Types actuels : programme **T2/T3/T4** ; `type_projet='collectif'` ; `stationnement='aerien'` ; `terrain='libere'` (options UI uniques). `EtudeProgramme = {ref, logements, par_type, sdp_m2, shab_m2?}`.

---

## C. Couches base disponibles pour l'étude (+ millésime)

| Couche | Table(s) | Date | Millésime constaté |
|---|---|---|---|
| PLU zonage | `parcel_zone_plu`, `plu_reglement_extrait` | `millesime`/rebuild | articles → 2026-08-05 ; rebuild 2026-10-17 |
| **PPR rouge/bleu** | `spatial_layers kind='ppr'` (164 zones) | `created_at` | 2026-09-13 — **live, voir §D** |
| Aléas | `spatial_layers kind='georisque_alea'` (1093) | `created_at` | 2026-09-14 |
| SUP | `spatial_layers kind='sup'` (417) | `created_at` | 2026-09-14 |
| ER | `plu_gpu_prescription` subtype='05' | `created_at` | 2026-06-29 |
| EBC | `plu_gpu_prescription` subtype='01' | `created_at` | 2026-06-29 |
| OAP | — | — | **pas de couche dédiée** (dans docs PLU) |
| Voirie BD TOPO | `spatial_layers kind='voirie'`, `adresses` | `created_at`/`refreshed_at` | voirie 2026-07-01 ; adresses 2026-10-11 |
| LiDAR/pente/MNT | `batiment_hauteur_lidar`, `rgealti_mnt_5m`, `spatial_layers kind='pente'` | survol/`mesure_le` | survol 2023-08→10 ; mesuré 2026-09-10 ; MNT 5 m sans millésime |
| Ravines/hydro | `spatial_layers kind in ('ravine','water')` | `created_at` | 2026-06-29 |
| Réseaux | `spatial_layers kind in ('ligne_mt','ligne_ht','zonage_assainissement')` | `created_at` | MT/HT 2026-09-14 ; assainissement 2026-07-11 |
| Cadastre | `parcels` + `ingestion_runs` | `updated_at` | 2026-10-15 (PCI « latest » 2026-10-11) |

Registre central des sources : table **`data_sources`** (champs `source_millesime`, `last_sync_at`, `fraicheur_statut`). À réutiliser pour l'exigence « source + millésime » de chaque contrôle.

---

## D. Finding corrigé — PPR Saint-Denis (⚠ piège overlay)

L'agent DB a conclu « DL0247/DL0248 sans PPR » car la table **précalculée `parcel_couche_intersection` ne contient AUCUN `kind='ppr'`** (seulement dpu/sup/…). **Vérification directe (géométrie live) :**

| Parcelle | INTERDICTION (rouge) | PRESCRIPTION (bleu) |
|---|---|---|
| DL0247 | 254,7 m² = **33,5 %** (R1) | 114,1 m² = 15,0 % (rB3) |
| DL0248 | 293,8 m² = **37,5 %** (R1) | 120,0 m² = 15,3 % (rB3+B2) |

Le moteur `terrain.py::_ppr_par_couleur()` (l.76-81) lit **`spatial_layers kind='ppr'` en direct** → il **verra** le PPR (rouge soustrait, bleue signalée). ✅ **Conséquence étude v6 :** ne jamais s'appuyer sur `parcel_couche_intersection` pour le PPR ; vérifier que la **fiche** (exigée « mêmes sources ») n'affiche pas « PPR absent » par ce biais. Illustration parfaite de la règle « donnée absente = non vérifié, jamais absent ».

---

## E. Écarts existant ↔ mandat V6 (à combler, 1 lot = 1 commit)

| # | Existant | Mandat V6 | Lot |
|---|---|---|---|
| 1 | Programme T2/T3/T4 | **T1–T4** (4 lignes +/−) | A (étape 3) |
| 2 | `type_projet=collectif` seul | **4 types** (étudiante/senior/social/lotissement), aucune présélection | A (étape 2) + C + D |
| 3 | 4 états contrôle | **5 états** (+ `À confirmer`) ; verdicts globaux `Exploitable sous hypothèses / À compléter / Impossible pour cause établie` | B + C |
| 4 | division-or hors `implantation/` | brancher sur l'assiette à la demande (pas batch île) | D |
| 5 | M22 = 2 états (config/scénarios) | **parcours 3 étapes** (Parcelles → Type → Programme) + récap droite, **sans carte** dans le formulaire | A |
| 6 | Capacité affichée direct | « non vérifié » tant que moteur pas tourné ; 4 grandeurs séparées (sol restant / emprise / SDP / m² programme) | A + B |
| 7 | Stationnement barème zone | règle **lue du PLU par type de projet** (unité, article, millésime, exceptions) ; plafonds L151-35 « sous condition » | C |

---

## F. Captures du parcours actuel (app servie q_v19, 8860/6060)

Captures dans `captures/` (via `window.__labuse.ouvrirEtude([AW0099,AW0451,AW0624,AW0625])`) :
- `00-parcours-actuel-etat1-config.png` — **état 1 (config)** : header Fermer/Réinitialiser, terrain « 1 à 8 parcelles contiguës » + 4 chips + carte « 4 parcelles · Contiguës, assiette fusionnée », TYPE DE PROJET, OBJECTIF, PROGRAMME, STATIONNEMENT.
- `01-parcours-actuel-etat2-scenarios.png` — **état 2 (scénarios)** : carte scénario « A · barre · Exploitable », 4 grandeurs, plan masse SVG + table SURFACES.

**Observations (confirment les écarts §E, matière pour A/B) :**
1. Boutons **« Maisons groupées · bientôt », « Lotissement · bientôt », « En ouvrage · bientôt »** présents → **interdits par le mandat** (« rien de bientôt, aucun bouton inactif sans raison »). À remplacer par les 4 vrais types + stationnement motivé.
2. Type de projet : seul **Collectif** actif. Programme en **T2/T3/T4** (pas T1–T4).
3. **Un seul scénario** (A barre, Pareto effondré) vs mandat **3 variantes** (Votre programme / Optimisation / Alternative).
4. Les 4 grandeurs affichées = logements / places / SDP / niveaux — **≠** les 4 mandatées (sol restant / emprise mobilisable / SDP autorisée / m² programme envisageables).
5. Déjà bon à réutiliser : disclaimer « Pré-faisabilité indicative… ni preuve de conformité » ; **plan masse SVG** avec légende **PPR rouge (retirée) / PPR bleue (signalée)** + table SURFACES mesurées (Terrain 1 746 · Emprise 504 m²·29 % · SDP 1 800 · Stat+allée 626 · Pleine terre 614 · Places 34/34 · Logts 28).

**Datapoint live (propose, objectif équilibre) — Étang-Salé UA :** LABUSE 28 logts (T2×16·T3×8·T4×4), 34 places, SDP 1 800 m², emprise 504 m² (29 %), R+3, « exploitable ». Limite = hauteur. **vs archi 29 logts / SP 2 368 m² (y/c coursives+varangues) / 31 places / R+3.** (1er point du futur tableau d'écarts.)

## G. Checklist Étape 0
- [x] Inventaire moteur / frontend / couches+millésime.
- [x] IDU vérifiés + données archi transcrites (`etudes-archi-donnees.md`).
- [x] Finding PPR Saint-Denis corrigé (§D).
- [x] Captures du parcours actuel (état 1 + état 2).
- [x] App arrêtée, ports 8860/6060 libres.
