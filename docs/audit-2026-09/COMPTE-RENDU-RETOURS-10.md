# COMPTE-RENDU RETOURS-10 — recette du 02/09, 23 h

**Branche `fix/retours-10`** (commit à suivre, non mergée — merge = Vic).
**Clôture** : `tsc` OK · `vite build` ✓ · **front 137 tests** verts · **back 2191 passed / 0 échec** (35 skips环境, aucun régressif).
Mesures T2/T3 faites sur **la base réelle** (`LABUSE_DATABASE_URL` du `.env` → `labuse@localhost`, `parcel_p_score_v2` = 3,0 M lignes, run servi `q_v11_m137` = 431 663 parcelles).

⚠ **Redémarrage serveur** requis (backend T1/T2 + deux index au boot via `ensure_schema`).

---

## T1 — Radar : plus d'instruction ✅

**Fait.** L'instruction humaine des candidates est retirée du front ; rien n'est supprimé en base (les endpoints `a-instruire`/`instruire` back subsistent, plus appelés).

- `Radar.tsx` : l'onglet **« À rattacher »**, l'écran **Instruire** (côte-à-côte annonce↔candidate, concorde/diverge, Suivante/Aucune) et les composants `InstructionCard`/`Instruction`/`Fait` **supprimés** ; imports `getRadarAInstruire`/`radarInstruire`/`RadarAInstruire`/`RadarPiste`/`RadarCritere`/`Declaratif` retirés.
- **Les 4 chiffres de tête deviennent 3** : *annonces en vie · à valider · re-vérifiées aujourd'hui / dues* (le « à rattacher » disparaît). Onglets : Déposer · À valider · Re-vérifier · Check.
- **Ce qui reste = rattachement AUTOMATIQUE à confiance forte**, en **un bouton « Rattacher » sur la ligne de l'annonce, dans la Re-vérification** (un clic humain). Back (`pige/api.py` `radar_reverif`) : la file expose désormais `rattachable_forte` + `piste_idu` — **lus des colonnes déjà stockées** (`rattachement_confiance` ≥ 0,85 ∧ 1re piste), zéro calcul neuf. Confiance faible → aucune tâche, l'annonce reste « non rattachée ».
- Le compteur **« rattachées N / M » reste** sur Circuit (`Flux.tsx`) et Pilotage (`AdminView.tsx`) — non touché.
- Test : `tests/test_radar_rattachement_s5.py::test_reverif_expose_le_rattachement_forte_en_un_clic` (forte → bouton + idu ; faible → rien ; colonnes brutes non fuitées).

## T2 — Dashboard : audit de performance sur la base réelle ✅

**Fait.** Cause exacte trouvée, mesurée, corrigée. Les endpoints Vic attend (Pilotage, Circuit) passent **sous 2 s**.

### T2.1 — Tableau des temps AVANT / APRÈS (base réelle, temps de réponse du handler = DB + assemblage)

| Page (endpoint) | AVANT | APRÈS | Requête la plus lente (avant) | Correctif |
|---|---:|---:|---|---|
| **Données · Circuit — flux/runs** | **31,7 s** | **16,9 s froid · 0,14 s chaud** | `count(*) … parcel_p_score_v2 a JOIN b … tier IS DISTINCT` (self-join 3 M, ~3 s) ×4 + `DISTINCT run_id` (seq scan 3 M, 1,9 s) + `tier,count(*) GROUP BY` (1,9 s) ×8 | mémoïsation des écarts (immuables) + distribution mémoïsée + `DISTINCT run_id`→registre ; **rendu progressif déjà en place** (RETOURS-9) |
| **Pilotage** | **6,1 s** | **1,45 s** | `count(*) FROM parcel_p_score_v2 WHERE run_id` (seq scan 3 M, 2,0 s) | `n_parcelles` lu du **registre** `p_score_v2_runs` |
| **Données · Circuit — flux** | **5,7 s** | **1,30 s** | idem (via `coherence_flux`→sonde→accueil) | idem + index communes/ventes |
| Sources client (liste) | 0,59 s | 0,58 s | `max(created_at) spatial_layers` (0,25 s) | < 2 s, laissé |
| IA · Catalogue · Produit · Comptes · Courrier · Signalements · Radar · Contacts · Couverture | < 0,1 s | < 0,1 s | — | RAS |

Les deux pages Pilotage & flux passaient par **`sante.sonde_metier`** qui **bust le cache** de `/accueil/chiffres` (« état réel ») et le recalculait à chaque affichage. Ce recalcul portait 3 comptes lourds → tous corrigés :

1. **`parcelles`** `count(*) parcel_p_score_v2 WHERE run_id` (Parallel Seq Scan 3 M, 2,0 s) → lecture de `p_score_v2_runs.n_parcelles` (clé primaire, **la « date » = `computed_at` du registre**). `accueil.py`.
2. **`ventes_train`** `count(*) p_model_ext_dataset WHERE label_l2=1 AND annee…` (seq scan 4,3 M, 0,95 s) → **index `ix_pmed_label_annee (label_l2, annee)`**.
3. **`communes_calibrees`** `parcels ⋈ parcel_zone_plu GROUP BY commune` (seq scan parcels, 0,66 s) → **index couvrant `ix_parcels_idu_commune (idu) INCLUDE (commune)`** → index-only scan (0,15 s).

**flux/runs (Circuit)** : les écarts `(candidat, servi)` sont **immuables** (runs append-only) → mémoïsés (`bascule_flux._ECART_CACHE`, vidé à la bascule) ; la distribution des tiers par run mémoïsée (`golden_ops._DISTRIB_CACHE`) ; `DISTINCT run_id` lu du registre. Résultat : **0,14 s chaud** (ce que voit l'utilisateur après le 1ᵉ affichage), et l'endpoint est **déjà chargé progressivement** (non bloquant, RETOURS-9 Q1). Le froid reste 16,9 s (4 self-joins de 3 M inhérents) — arbitrage assumé : admin-only, déféré, chaud-instant ; le froid-instant durable demanderait de **persister** l'écart au calcul du run (noté, hors périmètre front).

### T2.3 — Test de garde
`tests/test_admin_perf_retours10.py` : exécute chaque endpoint admin et **échoue au-dessus de 2 s** (mesure chaude = UX réelle). Se **skip** quand `parcel_p_score_v2 < 1 M` (base de test/CI vide) → la garde vit sur la base réelle de Vic. Outil de mesure reproductible : `scripts/perf_admin_retours10.py`.

## T3 — Listes : 200 par 200, partout ✅

**Fait.** Règle unique, un seul composant, plus jamais « Tout voir ».

### T3.1 — Inventaire des listes > 200 lignes et conversions

| Liste | Fichier | Avant | Après |
|---|---|---|---|
| **Parcelles — chemin normal (commune)** | `ResultsSection.tsx` | slice + **« Tout voir »** (chargeait 33 910 → figeait) | `usePagination` 200 + **« Voir 200 de plus »** |
| **Parcelles — chemin Analyse LABUSE (île)** | `ResultsSection.tsx` | « Charger plus » (200/page) | aligné **« Voir 200 de plus »** |
| **Projets** (À trier / Retenues / Écartées) | `ProjetsPanel.tsx` | 4 puis **« voir les N autres »** (tout) | 4 puis **+200 / clic** + compteur |
| **Radar (biens)** | `RadarView.tsx` | tout rendu | fenêtre 200 + **« Voir de plus »** (carte garde tous les pins) |
| **PLU / Densifier (M15)** | `moteurs.tsx` | « Voir N de plus » **+ « Tout charger »** | **« Tout charger » retiré**, 200 |
| **Faisabilité (M22)** | `M22Programme.tsx` | idem | idem |
| **Renouvellement (M19)** | `Renouvellement.tsx` | idem | idem |
| Permis (M04), Marché (M03), Patrimoine (M02) | `ModulePanel.tsx` | « Voir plus » / plafond serveur borné | déjà incrémentaux / bornés serveur — laissés (ne figent pas) |
| Résultats Copilote | `Resultats.tsx` | top-20 servi (choix produit) | inchangé |

**Composant unique** `ListPagination.tsx` : `PAGE_SIZE` **400 → 200** ; le bouton **« Tout charger (total) »** (`onAll`) — celui qui tirait 33 910 lignes et figeait l'app — **supprimé** partout. Position de défilement conservée (on **append**, le conteneur garde son scroll). Arbitrage : les outils paginés côté serveur gardent le `cap` du back pour le libellé exact « Voir N de plus » ; M02/M03/M04 restent bornés serveur (jamais de dump).

### T3.3 — Test
`ListPagination.test.ts` : une liste de **33 910** ne montre que **200** au 1ᵉ rendu, **+200 par clic** ; **aucun** bouton « tout charger » (assertion négative).

## T4 — Fiche parcelle : en-tête variante A ✅

**Fait.** Les trois pavés pleins deviennent **pastilles contour** (Cadastre vert · Pages jaunes ambre · Google Maps blanc), **pleines au survol ET au clic** (`:active`), la ligne de chiffres juste dessous. Rien d'autre ne bouge. Les 3 URL sont construites par des **fonctions pures testées** (`fiche/liensExternes.ts`).

### T4.2 — Vérification des liens sur 5 parcelles réelles (lien par lien)

| Parcelle | Cadastre Géoportail | Google Maps | Pages jaunes |
|---|---|---|---|
| **97401000AC0428** · Les Avirons · 8 313 m² *(adresse BAN)* | `c=55.360677,-21.206489&z=19` + couche `CADASTRALPARCELS.PARCELLAIRE_EXPRESS` → **centré parcelle** ✓ | `query=-21.206489,55.360677` (lat,lon) → **emplacement** ✓ | `ou=22 bis Ruelle des Cypres 97425 Les Avirons` → **adresse exacte** ✓ |
| **97401000AC0515** · Les Avirons · 967 m² *(adresse BAN)* | `c=55.362444,-21.209956` centré ✓ | `query=-21.209956,55.362444` ✓ | `ou=17 Impasse des Capucines 97425 Les Avirons` ✓ |
| **97401000AB0001** · Les Avirons · 169 715 m² *(sans adresse)* | `c=55.378495,-21.172318` centré ✓ | `query=-21.172318,55.378495` ✓ | `ou=Les Avirons` → **« Pages jaunes — commune »** ✓ |
| **97401000AB0002** · Les Avirons · 108 456 m² *(sans adresse)* | `c=55.377727,-21.174849` centré ✓ | `query=-21.174849,55.377727` ✓ | `ou=Les Avirons` → **commune** ✓ |
| **97417000BN0004** · Saint-Philippe · 28,2 M m² *(grande rurale)* | `c=55.746590,-21.311872` centré sur le centroïde (pas la commune) ✓ | `query=-21.311872,55.746590` ✓ | `ou=Saint-Philippe` → **commune** ✓ |

**Constat** : Géoportail n'accepte pas l'IDU dans le permalien → on centre sur le **centroïde** au zoom 19, couche cadastre allumée (parcelle identifiable). Maps porte les coordonnées (jamais une recherche texte). L'ordre lon/lat n'est jamais confondu (test dédié). Sans adresse, Pages jaunes tombe sur la commune **et le dit**.

### T4.3 — Test
`fiche/liensExternes.test.ts` : construit les 3 URL, vérifie `c=lon,lat`, `query=lat,lon`, l'adresse exacte vs commune seule, l'anti-confusion lat/lon, et « aucun lien » si ni adresse ni commune.

## T5 — Copilote : accueil épuré ✅

**Fait** (`AccueilCopilote.tsx`). Les deux phrases (« rien à choisir » / « nouveau fil ») **retirées**. Les trois exemples deviennent des **chips discrètes** sous le champ (contour ligne au repos, **plein mauve au survol** via `.hover-fill-ia`), la question part au clic. « Ce qu'il sait faire » passe sur **une ligne de quatre**, icônes mauves **légères** (tuile 30 px, fond mauve ~10 %). « Reprendre » : **« voir tout · N »** remonté dans l'**en-tête de section** (plus de bouton séparé), 4 fils au repos, rétention en pied.

## T6 — Bouton « Signaler » : plein quand ouvert ✅

**Fait** (`Header.tsx`). Ouvert → **plein vert, encre sombre** (`bg-mint text-mint-ink`, règle DA RETOURS-9). Re-balayage : la **cloche** était déjà correcte (pleine à l'ouverture) ; la **recherche** n'a pas d'état actif persistant (loupe sans toggle) — aucun défaut.

## T7 — Sources client : tuile « Dernière analyse » retirée ✅

**Fait** (`SourcesPage.tsx`). La tuile « arrêtée au JJ/MM · dernière analyse » quitte la page (les quatre restantes se répartissent la ligne, `text-[26px]` uniforme). La date de l'analyse vit déjà sur les fiches et dans Projets. L'endpoint `/sources/couverture` reste (champs `parcelles`/`communes` toujours servis).

---

## Fichiers
**Front** : `ListPagination.tsx`(+test), `panel/ResultsSection.tsx`, `outils/{moteurs,M22Programme,Renouvellement,RadarView}.tsx`, `projets/ProjetsPanel.tsx`, `admin/Radar.tsx`, `fiche/Fiche.tsx` + `fiche/liensExternes.ts`(+test), `copilote/AccueilCopilote.tsx`, `header/Header.tsx`, `sources/SourcesPage.tsx`, `lib/api.ts`.
**Back** : `api/accueil.py`, `golden_ops.py`, `bascule_flux.py`, `models.py` (2 index idempotents au boot), `pige/api.py` + `tests/test_radar_rattachement_s5.py`, `tests/test_admin_perf_retours10.py`, `scripts/perf_admin_retours10.py`.
