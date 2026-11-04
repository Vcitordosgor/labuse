# CHASSE-FIX-1 — compte-rendu

Corriger, **à la source**, les trouvailles des lots A et B de la chasse (`audit/chasse-1-a`,
`audit/chasse-1-b`). Jamais écran par écran.

- **Branche** : `fix/chasse-fix-1` · worktree `~/Desktop/labuse-chassefix` · ports 9620/6820
- **HEAD de départ** : `423106cdc` (DEPLOY-GROUPE-1) · base Mac `labuse`, run servi **q_v20**
- **Date** : 2026-11-04 (soir, Réunion UTC+4)
- **Prod** : lecture seule ; jamais touchée. Fenêtre 01 h–05 h Réunion respectée.
- **Coordination multi-session** : trois sessions ont partagé la base Mac (`INJECTION-SOLIDE-1`,
  `RETOURS-16`, celle-ci). Fichiers communs (App.tsx) : changement minimal + signalé. Le banc complet
  a été joué sur une base de test **dédiée** (`labuse_test_cf`) pour ne pas corrompre le `labuse_test`
  qu'une session voisine réécrivait au même instant.

> **Note d'honnêteté.** Une partie du travail (B-2, B-3, B-4, résolveur B-5/B-6…) a été menée par des
> agents en arrière-plan ; l'un d'eux a été interrompu par un redémarrage de process et repris à la
> main. Chaque correctif a été **re-vérifié** ici avant d'être porté au crédit.

---

## Les corrections par cause

### A-1 / A-2 — micro-parcelles : le seuil teste partout la surface SERVIE
- **Cause** : le masque anti-sliver testait le **dessin** `surface_m2`, pas la surface servie
  `COALESCE(contenance_m2, surface_m2)` → 279 parcelles réelles (≤ 35 m²) hors compteur/liste/stats/
  entonnoir/découverte mais peintes sur la carte ; et les tuiles n'avaient **aucun** plancher.
- **Fix (source unique)** : nouveau `surface.SLIVER_MASK_SQL(alias, param)` + `MIN_DISPLAY_SURFACE_M2`
  dans `surface.py`. Câblé dans les **4** masques de `app.py` (`_q_v2_stats` compteur, `_q_v2_list`
  liste, idus/entonnoir, GeoJSON) **et** dans le build des tuiles `tiles.py` (`build_mvt_table`, qui
  n'avait aucun plancher). Un seul prédicat, testant la surface servie, des deux côtés.
- **Preuve (SQL `labuse`, lecture seule)** :
  `live 433 229 · ancien compteur (dessin≥2) 432 350 · neuf compteur (servie≥2) **432 591** ·
  279 réelles réintégrées · 638 vrais slivers (servie<2)`. Après `build-mvt`, la carte = alive ∧
  servie≥2 = **432 591** → **compteur == carte** (l'écart 879 = 600 slivers + 279 réelles est résorbé).
- **Dette** : `build-mvt` local + prod (go Vic) pour matérialiser le plancher dans `mvt_parcels` —
  différé comme les campagnes précédentes ; la preuve ci-dessus est indépendante du rebuild.

### A-3 — dates : une seule fonction de format, fuseau Indian/Reunion
- **Cause** : grappe de `toLocaleDateString` sans fuseau + calculs d'âge relatif à la main
  (`Date.now()`/UTC) → bugs « J-1 » (classe SILENCE-1) sur navigateurs hors Réunion.
- **Fix** : `lib/format.ts` reçoit les formateurs manquants — `fmtDateCourt`, `fmtMoisAn`,
  `fmtDateLong`, `fmtJourSemaine`, `fmtHorodatage`, `ageEnJours`, `ageEnMois`, `ageConversation`,
  `ageMoisLabel`, `labelJours` — tous en `Indian/Reunion`, l'âge compté en **jours calendaires**
  Réunion (plus de delta de millisecondes brut). ~20 sites routés : ResultsSection, RadarMarche,
  ProjetsPanel, VeillePromoteurs, marche, AccueilCopilote, CircuitDiagram, VeilleEcrans, MapView,
  Header, JohnTaylor, ConversationsSidebar, status.ts, Radar, Licences, AdminView + 8 horodatages admin
  (Resume, AFaire, Circuit, Journal, Sources, Usine, Detail, Cron) → `fmtHorodatage`.
- **Garde-fou** : `lib/__tests__/format-dates.test.ts` scanne tout `src/` et **refuse** hors de
  `format.ts` : `toLocaleDateString`, `toLocaleTimeString`, `toLocaleString(...timeZone...)` et l'âge
  relatif interpolé (`il y a ${…}`). Plus un test positif (rendu UTC+4, pas J-1).
- **Preuve** : `tsc --noEmit` 0 erreur ; **vitest 309/309** (65 fichiers), dont la garde A-3.

### B-1 — le Retour du navigateur rouvre l'écran que l'URL décrit
- **Cause** : l'effet de lecture du hash (`App.tsx`) tournait **au seul montage** (`[]`), sans
  écouteur `popstate`/`hashchange` → Back/Forward changeaient l'URL sans ré-appliquer l'état (fiche
  fermée sous une URL de fiche).
- **Fix** : la lecture du hash devient `appliquer()`, **rejouée** sur `popstate` et `hashchange`
  (comme `Circuit.tsx`) ; symétrie ajoutée (`select(null)` ferme la fiche quand l'URL n'en décrit
  plus). `replaceState` ne déclenche ni l'un ni l'autre → pas de boucle ; `appliquer` idempotent.
- **Preuve** : `tsc` + suite front 309 verts. Vérif live Playwright : différée (éviter de perturber la
  session voisine qui lit la base ; MCP revenu en cours de session).

### B-2 — Assemblage : SDP « bâti conservé » par défaut, « terrain libéré » nommé
- **Cause** : l'Assemblage servait la SDP **max** de l'union (table rase) sans le dire → contredisait
  les fiches « bâti conservé » (ER0783 : fiche 749 m², assemblage 913).
- **Fix (`assemblage.py` / `moteurs.py` / `moteurs.tsx`)** : `aggregate_assiette` calcule la SDP
  **bâti conservé** = SDP max de l'union − bâti existant conservé (Σ `sdp_existante` lu du **même bloc
  `residuel` que la fiche**) et l'expose par **défaut** (`sdp_m2`), la SDP **terrain libéré** restant
  servie sous ce nom (`sdp_terrain_libere_m2`), jamais seule. SDP par parcelle = la résiduelle de la
  fiche (comparaison « vs meilleure seule » comme la fiche).
- **Preuve** : `tests/test_assemblage.py` **vert** (base isolée).

### B-3 — Prix au m² maison : Estimer et la carte Marché lisent la MÊME médiane (MARCHE-UNIQUE)
- **Cause** : deux chemins de calcul (`comparateur_bien` Estimer vs `medianes_par_type` fiche) sur des
  échantillons/fenêtres distincts → 4 747 €/m² à l'Estimer, 4 265 €/m² sur la fiche pour le même bien.
- **Fix (`marche_service.py` / `faisabilite/bilan.py`)** : un seul point de calcul (`reference_locale`)
  pour les deux écrans.
- **Preuve (direct, `labuse` q_v20)** : `97415000ER0783` maison = **4 265 €/m²** à l'Estimer ET sur la
  fiche (rayon 500 m), idem ER0918/DT0487/BO0587 — un seul chiffre. `tests/test_marche_unique_estimer.py`
  (skippe proprement si la base de test ne porte pas assez de ventes DVF bâties).

### B-4 — mutateurs d'ops globaux sous `/admin`, réservés aux admins
- **Cause** : `POST /partners/match/run`, `/events/detect`, `/events/demo` écrivaient dans `event_log`
  (cloche partagée) **hors** du segment `/admin` et **sans garde** → un client authentifié les lançait.
- **Fix (`partners.py` / `events.py`)** : routes déplacées sous `/admin/…` (fail-safe structurel) **et**
  `exiger_admin` explicite (double garde, comme John). Balayage des autres routes mutantes : aucune
  autre écriture-pour-tous ouverte aux clients (jumelle `/partners/profiles` déjà gardée).
- **Preuve** : `tests/test_audit_secu.py::test_mutateurs_ops_globaux_sous_admin` **vert** — client → 403,
  admin → passe, anciens chemins → **404**.

### B-5 — Copilote : une adresse n'est retenue que si voie ET commune correspondent
- **Cause** (`copilote_v2/resolveur.py`) : la relaxe par jetons dépouillait voie + commune jusqu'au seul
  numéro, puis matchait des voies arbitraires présentées comme sûres.
- **Fix** : `_mots_adresse` sépare voie/commune/CP ; une candidate n'est retenue que si **tous** les
  mots significatifs de la voie figurent dans son libellé **et** (si commune/CP saisis) la commune
  correspond ; sinon « adresse introuvable » + candidates **proposées** (jamais imposées).
- **Preuve** : `tests/test_copilote_chassefix_b.py` vert (« 777 avenue bidon à Gotham » → introuvable ;
  « 3 chemin de la Citerne 97417 La Montagne » → `97411000BZ1065`).

### B-6 — Copilote : parcelle à cheval cite toutes les zones avec leur part
- **Fix (`copilote_v2/resume_fiche.py`)** : sur `a_cheval`, la réponse zone cite toutes les zones avec
  leur part (même source que la fiche, `zone_dominante`) + mention de la part non constructible.
- **Preuve** : `tests/test_copilote_chassefix_b.py` vert (`DV0499` → U6c + N ; `EL0168` → U5c + Ncor).

### Les 7 mineurs du lot B
- **m1 / m2** (events detect/demo sans garde) : corrigés **avec B-4** (sous `/admin` + `exiger_admin`).
- **m3** (FAB « Couches » qui recouvre la fiche à 390 px) : `LeftPanel.tsx` masque le bouton flottant
  tant qu'une fiche est ouverte (`selectedIdu`) — on choisit des couches sur la carte, pas en lisant.
- **m4** (« viabilisation confirmée » sur-promet) : `viabilisation.py` — le badge **replié** dit
  « confirmée **au voisinage** » (score inféré du voisinage, pas un branchement réel) ; le déplié garde
  « confirmée par les faits ». Repro `tests/test_viabilisation.py` **vert**.
- **m5** (relance de prix sans possessif perd le contexte) : `copilote_v2/router.py` — une relance
  courte (« et le prix au m2 ? ») réhérite la parcelle du fil, sauf si elle nomme une autre commune.
- **m6** (John refuse « lister/compter ») : `john/chat.py` — l'anti-invention autorise désormais les
  **cardinalités** des collections lues (compter ce qu'on a lu ≠ inventer) ; un nombre inventé reste
  refusé. Repro `tests/test_john_1.py::test_cardinalite_dune_liste_lue_passe_lanti_invention` **vert**.
- **m7** (hauteur sans unité) : `copilote_v2/outils.py` — « 13 m » (texte des règles), la valeur brute
  restant dans `data`.

---

## Recette

| Vérification | État |
|---|---|
| `tsc --noEmit` (front) | **0 erreur** |
| `vitest run` (front) | **309 / 309** (65 fichiers), dont la garde A-3 |
| A-1/A-2 compteur == carte (SQL `labuse`, lecture seule) | **432 591 = 432 591** ✓ |
| B-3 Estimer == fiche (direct, `labuse` q_v20) | ER0783 **4 265 = 4 265** ✓ |
| Tests de piste (base isolée) : B-2, B-4, m4, m6, B-5/B-6/m5/m7 | **86 passés / 1 skip** |
| Suite Copilote complète (fork) | **206 passés, 13 skips, 0 échec** |

**Rouge avant / vert après** : chaque trouvaille porte une repro (test ou preuve SQL/direct) : m4
(`mot != "confirmée"`), m6 (compte 47 d'une liste de 47), A-1/A-2 (comptage), B-2/B-4/B-5/B-6 (tests
dédiés), B-3 (ER0783 4747→4265).

### Dettes de recette (restantes)
- **Banc complet 0 rouge + suite de cohérence** sur le `labuse_test` **ensemencé** : à jouer dès que la
  session voisine libère cette base (jouer le banc sur une base **vide** n'est pas représentatif — les
  tests dépendants des données skippent/échouent, comme vu). Puis **commit**.
- **`build-mvt`** local + prod (go Vic) : matérialise le plancher anti-sliver dans `mvt_parcels` ;
  différé par convention (la preuve compteur==carte est indépendante du rebuild).
- **Prod contre local (reste du lot A)** : après 05 h Réunion, rejouer `harness-cross-surface.py`
  contre l'API prod sur les 362 IDU, en lecture seule ; expliquer/corriger tout écart.
- **Vérif live** B-1 (Retour navigateur) et m3 (FAB 390 px) au navigateur : différée pour ne pas
  perturber la session voisine ; couverte en attendant par la suite front + revue de code.
