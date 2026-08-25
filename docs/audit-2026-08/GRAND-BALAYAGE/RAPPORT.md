# GRAND BALAYAGE — Audit total de l'app par l'usage

> **AUDIT SEUL** — aucun fix, aucun code applicatif modifié. Seuls livrables : ce dossier `docs/audit-2026-08/GRAND-BALAYAGE/`.

## Contexte d'exécution (à lire avant de rejouer un repro)

- **Date** : 2026-08-25
- **Branche** : `audit/grand-balayage`
- **Front** : `http://localhost:5174/socle/` — ⚠️ **PORT 5174, pas 5173** (5173 était refusé ; Vite tourne sur 5174). Tous les repros ci-dessous se rejouent sur `:5174`.
- **Backend** : `http://localhost:8000`
- **Postgres** : lecture stricte
- **Navigateur** : Playwright MCP (Chromium), snapshots d'accessibilité par défaut ; captures d'écran uniquement sur anomalie → `captures/GB-xxx.png`
- **Compte principal** : session « VL » déjà ouverte — lecture + mission 45 (IDOR)
- **Compte de test** : écritures uniquement (lots 2-5) — ⚠️ identifiants à confirmer avant LOT 2
- **Artefacts Playwright** : `.playwright-mcp/` exclu via `.git/info/exclude` (n'entre dans aucun commit GB)

## Barème

| Gravité | Sens |
|---|---|
| 🔴 | Bloquant / faux chiffre servi / fuite inter-comptes / écran cassé |
| 🟠 | Dégradé fonctionnel / promesse non tenue visible / échec silencieux |
| 🟡 | Coquille UX / incohérence mineure / code mort sans impact usager |

Types : `bug` · `faux-chiffre` · `mort` · `orphelin` · `UX` · `perf` · `sécu`

---

## Inventaire de purge [GB-TEST]

> Objets créés sur le compte principal (session VL) pendant l'audit, à supprimer par Vic. **Je ne supprime rien moi-même.**

| # | Objet | Où | Créé au | Comment purger |
|---|---|---|---|---|
| P1 | Projet **id=185** « [GB-TEST] Marchand audit — a supprimer » (+ **~200** lignes `projet_parcelles` : shortlist figée cap 200 + rejeu M34) | table `projets` / `projet_parcelles` (compte_id NULL = bucket pilote) | M29, 2026-08-25 | `DELETE FROM projets WHERE id=185;` (cascade sur projet_parcelles) — ou « Archiver/Supprimer » sur la carte projet en UI |
| P2 | Colonne CRM **id=20** « [GB-TEST] renommee audit » (créée puis renommée) | table `crm_columns` (compte_id NULL) | M35, 2026-08-25 | `DELETE FROM crm_columns WHERE id=20;` — ou « Personnaliser » → supprimer la colonne en UI |
| P3 | Prospect CRM **id=91** (parcelle 97417000BC0067, colonne gb_test, note [GB-TEST]) | table `pipeline_entries` (compte_id NULL) | M35, 2026-08-25 | `DELETE FROM pipeline_entries WHERE id=91;` — ou « Archiver la carte » en UI |
| — | Tentative Courrier (M28) : **échec 500** → aucune demande persistée. msel (M9) : transitoire, vidé. 1ʳᵉ tentative projet (M29, périmètre défaut) : **dédup** → aucun objet créé. Prospects BZ1065/AO0180 : déjà dans le CRM de Vic (`already:true`) → **non modifiés**. | — | — | rien à purger |

---

## Registre des findings

<!-- Chaque anomalie : ID GB-xxx · gravité · type · où · repro · attendu vs observé · capture · hypothèse cause (jamais de fix). -->

### LOT 1 — Balayage systématique

**Périmètre exécuté** : 7 sections de nav parcourues une à une sur le compte principal (session VL, lecture seule) — IA (Copilote), Cartes, Outils, Projets, CRM, Veille (3 onglets), Sources, menu « Mon compte ». Console + réseau surveillés en continu. Les affordances d'**écriture** (Archiver/Personnaliser CRM, tout-lire cloche, création projet, déconnexion, feedback) sont volontairement **non déclenchées** ici (principal = lecture) — elles sont exercées sur le compte test aux lots 2-5.

#### GB-001 · 🟡 · faux-chiffre · Porte d'accueil « 16 outils »
- **Où** : porte d'accueil `LeftPanel.tsx` (AccueilPreuves), sous-titre de la porte « Ouvrir un outil » → « **16 outils** — trouver, instruire, agir, comprendre, suivre ».
- **Repro** : ouvrir `:5174/socle/` → panneau Cartes → lire la 3ᵉ porte. Puis nav « Outils » → l'en-tête du tiroir dit « **13 outils** fonciers, du repérage à l'action » et liste exactement 13 cartes.
- **Attendu vs observé** : les deux comptes devraient concorder. Observé : porte = 16, tiroir = 13 → **contradiction interne** dans la même UI.
- **Cause (hypothèse, vérifiée en source)** : la porte affiche `${MODULES.length}` (`LeftPanel.tsx`), or `MODULES` (`components/outils/registry.ts`) contient **16 entrées dont 3 `hidden: true`** — des alias résolvants sans carte : `calculette-fonciere` (M23 → « Étudier un bien »), `barometre` (M18 → « Communes »), `promesses` (M04 → « Permis »). Ces 3 alias ont été ajoutés par les fusions du 23/08/2026 (§2/§3 du registre), gonflant `MODULES.length` de 13→16. Le tiroir, lui, ne compte que les non-`hidden` (13). La porte ne filtre pas les `hidden`.
- **Impact** : cosmétique mais c'est un chiffre faux affiché sur l'accueil vitrine, en contradiction avec le tiroir — accroc à la doctrine « chaque donnée est datée à sa source / chiffres exacts ».

#### GB-002 · 🟡 · UX · Badge cloche « 1249 » (question mandat : vrai backlog ou compteur jamais purgé ?)
- **Verdict** : **vrai backlog, honnête et purgeable — PAS un compteur cassé.** `/events` renvoie `{unread: 1249, items:[…]}` ; les 1249 sont des events BODACC « procédure ouverte » **tous datés du 21/08/2026 au même timestamp** (`00:34:09.245315`), detail « (rattrapage) » = backfill de masse au recalcul, `lu:false`. Le panneau cloche offre « tout lire », « Marquer comme lu ✓ » par item, agrégation débordement (« N procédures BODACC à X — Voir les N → »), lien digest (`/events/digest.html` → 200) et disclaimer honnête « On ne vous prévient que sur ce qu'on sait réellement détecter. »
- **Seule réserve 🟡 UX** : badge à **4 chiffres non capé** (« 1249 » brut plutôt que « 99+ »), noyé par un backfill « (rattrapage) » d'un seul recalcul — la cloche perd sa valeur de tri tant qu'elle n'est pas purgée. Pas un défaut de comptage.

#### GB-003 · 🟡 (dev-only) · bug/UX · Onglet Veille › Secteurs : feed « Nouveautés » cassée en `npm run dev`
- **Où** : nav « Veille » → onglet « Secteurs » → section « Nouveautés » + bouton « Rafraîchir ». Panneau `SurveillancePanel`.
- **Repro** : Veille → Secteurs → 2 secteurs listés OK (« veille pour teralta », « Centre Saint-Paul ») mais « Nouveautés » reste **vide, sans message ni placeholder** ; console : `GET /alertes?only_new=false → 404` (×3 au chargement) ; « Rafraîchir » → `POST /alertes/refresh → 404`, no-op silencieux.
- **Cause (vérifiée)** : le backend répond bien — `:8000/alertes → 200` avec de vraies alertes (ex. « Permis déposé dans « Centre Saint-Paul » »). Le 404 vient du **proxy Vite dev** : `/alertes` (et `/alertes/refresh`, `/alertes/ack`) **absents de l'allowlist `apiPaths`** dans `frontend/vite.config.ts`. C'est la **classe de bug récurrente documentée ~8× dans ce même fichier** (« MANQUAIT au proxy dev → 404 rouge », M12/M36/M58/M70/M82…). **En prod (FastAPI même origine, aucun proxy) la feature fonctionne** — d'où la gravité dev-only.
- **Finding applicatif résiduel (indépendant du proxy)** : le front **avale le 404 en silence** — « Nouveautés » n'affiche ni erreur ni « aucune nouveauté », et « Rafraîchir » ne signale rien. Si `/alertes` 404 pour une autre raison (deploy skew, blip réseau), l'utilisateur voit un panneau vide muet. 🟡 robustesse.
- **Garde-fou audit** : allowlist proxy relevée → je ne reporterai pas de faux 404 dus au proxy dans les lots suivants (seul `/alertes` est confirmé manquant à ce stade).

#### GB-004 · 🟡 · UX · Escape ne ferme pas le dropdown Notifications
- **Où** : cloche Notifications (dropdown + backdrop `div.fixed.inset-0.z-10`).
- **Repro** : ouvrir la cloche → presser `Escape` → le panneau **reste ouvert**, le backdrop plein écran continue d'intercepter tous les clics (impossible de cliquer la nav tant qu'on n'a pas cliqué le backdrop). Seul un clic sur le backdrop ferme.
- **Attendu vs observé** : convention = Escape ferme un overlay. Observé : Escape inerte sur ce dropdown (fonctionne ailleurs, ex. panneaux outils). Gêne mineure.

### LOT 2 — Missions recherche / carte / fiches _(COMPLET — missions 1-15)_

> ⚠️ Écritures autorisées exceptionnellement sur le compte principal (décision Vic). Le LOT 2 n'a produit **aucune écriture** (recherche/carte/fiches en lecture ; l'« export » ne mute rien). Garde-fous en place pour les lots suivants (artefacts jetables étiquetés, pas d'édition destructive, pas d'email réel).

**Mission 1 — 50 parcelles d'entreprises en procédure BODACC** → ✅ liste exploitable atteinte. « Procédure collective » (signal `procedure`) seule = **660** parcelles en procédure ; overlap « société ET procédure » = **634** (exact). Liste cliquable → fiches.

**Mission 2 — patrimoine d'une entreprise (SHLMR puis SCI)** → ✅ Scan patrimoine fonctionnel. SHLMR = **2618 parcelles** (803 actionnables, SDP résiduelle 1 249 991 m², valorisation 1 486,4 M€) ; petite SCI (SCI LES VIOLETTES) = 13 parcelles. Résumé + badges tier + parcelles cliquables.

**Mission 3 — brûlantes >1000 m² zone U Saint-Paul → export** → ✅ combinaison de filtres OK ; analyse honnête : Saint-Paul >1000 m² = « **0 priorité** (brûlante), 100 à suivre, 1235 long terme, 4038 neutre, 1362 faible, 9453 écartées » sur 16 188 — donc **0 brûlante** dans ce périmètre (résultat honnête, pas un bug). ⚠️ **Export : aucun bouton export/CSV trouvé dans le listing carte** (à confirmer LOT 3 — cohérent avec le fait que le CSV vit dans des outils dédiés : patrimoine, faisabilité, densifier).

**Mission 4 — terrains nus proches du littoral** → l'app n'offre **aucun critère de proximité littorale** (filtres = communes / surface / zonage / état-sol / 7 signaux). « Terrain nu » existe (état-sol), « proche du littoral » **non**. Absence honnête (aucune fausse promesse : le filtre ne prétend pas le proposer) — **pas un mur muet, pas un finding**.

**Mission 6 — 4 chemins de recherche** → ✅ IDU court « BZ1065 » **et** IDU complet « 97411000BZ1065 » ouvrent la fiche (via `/parcels/search` qui résout la réf courte) ; adresse « rue de la Republique » → autocomplétion numérotée + commune + code postal. Chemins commune/lieu-dit non testés isolément (l'autocomplétion est adresse-centrée).

#### GB-005 · 🟡 · UX/perf · CTA « Voir les N parcelles » — mise à jour tardive à l'ajout d'un 2ᵉ signal
- **Repro** : Filtres → cocher « Procédure collective » (CTA → 660) → cocher « Détenu par une société » → le CTA reste affiché à **660** (compte du 1er signal) pendant >2,5 s (2 snapshots a11y, 2 ordres différents) avant de se réconcilier à l'union correcte **33 556** (valeur observée au clic). Comptes eux-mêmes **exacts** (660/33 530/33 556 collent à l'arithmétique d'ensemble backend). Eventuellement correct → 🟡. Confiance moyenne (timing snapshot vs DOM).
- **SAIN associé** : sémantique **OU divulguée** (`FiltreLabuse.tsx:533` : « une parcelle correspond si au moins un des signaux cochés est présent »).

#### GB-006 · 🟡 · UX/recherche · Scan patrimoine ne résout pas les acronymes
- **Repro** : Scan patrimoine → « SHLMR » → « n'a pas de foncier connu… ou n'y figure pas » (faux-négatif). Le même détenteur ressort à **2618 parcelles** sous sa raison sociale « SOCIETE ANONYME D'HABITATIONS A LOYER MODERE DE LA REUNION ».
- **Cause (hypothèse)** : recherche sur la raison sociale littérale (fichiers fonciers DGFiP) ; l'acronyme « SHLMR » n'y figure pas. Honnêtement formulé mais trompeur pour un gros bailleur que tout le monde nomme par son sigle.

#### GB-007 · 🟡 · faux-chiffre · Écart de compte autocomplétion vs scan (Scan patrimoine)
- **Repro** : l'autocomplétion annonce « SHLMR 2632 parc. » mais le scan chargé dit « 2618 parcelles » (Δ14) ; « SCI LES VIOLETTES 14 parc. » → scan « 13 parcelles » (Δ1). **Écart systématique** (autocomplétion > scan).
- **Cause (hypothèse)** : deux dénominateurs (autocomplétion compte des lignes de propriété brutes ; le scan dé-doublonne / exclut slivers ou géométries absentes).

#### GB-008 · 🟡 · UX · Filtre « Communes » affiche des codes postaux bruts, sans nom
- **Repro** : Cartes → Filtres → section « 1 · Communes » = 24 boutons libellés uniquement par un **code postal** (97400, 97410, 97460…), **sans `title`/`aria-label`/nom de commune** (vérifié DOM). Un utilisateur doit connaître les codes postaux (97460 = Saint-Paul). Les *markers* carte, eux, sont nommés.
- **Cause (vérifiée)** : l'app **connaît** le nom — cliquer 97460 pose `#…&cs=Saint-Paul` dans le hash — mais le bouton **affiche le code postal** au lieu du nom. Pur choix d'affichage. (Les codes postaux ne sont d'ailleurs pas 1:1 avec les communes.)

#### GB-009 · 🟡 · UX · Omnibox : « Aucune adresse trouvée » pendant la saisie d'un IDU valide
- **Repro** : taper « BZ1065 » ou « 97411000BZ1065 » → le dropdown d'autocomplétion **adresse** affiche « Aucune adresse trouvée — vérifiez l'orthographe, ou tapez un IDU / une commune » alors que l'IDU est valide et **s'ouvre** en fiche dès qu'on presse Entrée. Message potentiellement décourageant (l'utilisateur peut croire que ça a échoué avant de valider).

**Mission 5 — empiler 4 filtres + reset** → ✅ 4 filtres (Saint-Paul + smin=1000 + zf=U + procedure) = « **4 actifs** », CTA « Voir les 16 parcelles ». Reset (`Réinitialiser`) → **430 813 / aucun actif / hash vidé / surface vidée** (retour à zéro complet). Le compteur « 4 actifs » **résout le doute « 1 actif » de GB (mission 3)** : c'était le zonage non appliqué (déplier ≠ sélectionner), **pas un bug**. Reset filter-scoped par design (tooltip « retour à l'état vierge »).

**Mission 7 — 23 couches** → ✅ **21 couches** listées (groupées : LE FOND / LES ZONAGES / RISQUES ET PROTECTIONS / ACCÈS ET RÉSEAUX / DISPOSITIFS ET PÉRIMÈTRES). Toggles **rendent proprement** : BPE (`/map/layers.geojson?kind=amenite_bpe&limit=40000` — plafond 40000 du fix couches actif), ZFANG (`kind=zfang`), Aléa inondation, Parc national → tous 200, **0 erreur console nouvelle**. Datation « i » + « Fraîcheur des données » par couche active (0 au repos = seules 3 actives). _Échantillon 4/21 couches à z10 (île) ; rendu visuel z12-18 par couche non couvert — assumé._ Observation : 21 vs 23 (mémoire audit-couches) = possible drift registre.

**Mission 8 — Remonter le temps** → ✅ parcelle → frise « L'ANNÉE À REVOIR (AVANT) » = **1950 / 2000 / 2006 / 2011 / 2016 / 2021 + Auj.** ; split-swipe « 1950-1965 vs Aujourd'hui 🔒 après fixe » ; switch 2011 → « 2011-2015 vs Aujourd'hui ». Contour épinglé par design. **SAIN.**

**Mission 9 — msel → Assemblage → retour** → ✅ bilan **honnête** : « **NON contiguë** » (flag correct), 1 interlocuteur PM, assiette 4 873 m², SDP cumulée 3 269 m², logements 31–39, « ×2,09 +109 % vs meilleure seule », **charge cumulée −309 885 € négative** (bloc rouge), disclaimer « reculs internes disparaissent », pont « ✉ Préparer les courriers (3) ». _(msel injectée via `window.__labuse.setMsel` — clic-carte multi impraticable via le driver — assumé.)_

**Mission 11 — verdict fiche == carte** → ✅ **5/5** (declasse_bati_sature ×2, chaude, ecartee ×2) identiques entre `/filtre` (carte) et `/parcels/{idu}` (fiche), même source q_v10_m129. _Cross-check backend sur 5 au lieu de 20 fiches UI (verdict servi par le même endpoint) ; 2 fiches rendues en UI vérifiées._

**Mission 12 — fiches contrastées** → ⚠️ **LÉGER** : fiches rendent avec blocs adaptés au type (vérifié sur chaude BL0032 / écartée AD1237 / résidentiel Le Tampon). Les 3 types spécifiques (copro-RNIC / nue-agricole / équipement-public) **non isolés chacun** — assumé, à compléter.

**Mission 13 — boutons fiche** → ✅ tous présents : Copier l'IDU, Demander à LABUSE (analyse), Poser une question (Copilote), Synthèse IA, **Courrier**, **+ CRM**, **+ Projet**, **PDF**, **Dossier**, **Pré-dossier PC**, « Données et méthode 27 sources ». Exports **fonctionnels** : `/parcels/{idu}/explain` 200, `export.pdf` 200 (`application/pdf`, 174 Ko), `dossier/{idu}.pdf` 200, `pre-dossier/{idu}.zip` 200. Écritures (+CRM/+Projet/Courrier) → M28/34/35 avec [GB-TEST].

**Mission 14 — HARD_EXCLUDE (pourquoi lisible ?)** → ✅ le verdict fiche dit lisiblement « **écartée : exclusion légale ou physique — motif détaillé dans l'analyse** » ; l'analyse agrégée (mission 3) liste « zonage inconstructible, PPR rouge, impossibilités physiques » + « voir pourquoi ». _Vérifié sur un hard-exclude « zone fermée » ; parcelle Parc-national spécifique non isolée via backend — assumé._

**Mission 15 — erreurs propres** → ✅ backend **404 honnête** (« Parcelle X inconnue de l'analyse en cours. ») ; **injection SQL** `'; DROP TABLE parcels;--` → 404 « Parcelle inconnue » (paramétré, pas de 500, pas de fuite — **pré-couvre M42**) ; UI **jamais d'écran cassé** ; omnibox « Aucune adresse trouvée ». _(Note : `select()` direct d'un IDU inexistant = no-op silencieux, cas-limite non atteignable normalement.)_

#### GB-010 · 🟡 (confiance faible) · état · msel persiste à la fermeture/réouverture de l'Assemblage
- **Repro** : outil Assemblage → composer une assiette (3 parcelles) → fermer l'outil (retour carte) → rouvrir Assemblage → **les 3 chips sont toujours là**.
- **Ambiguïté** : préservation de brouillon plausible (msel = état propre de l'assemblage) OU fuite d'état. Le risque réel (résidu de surbrillance carte hors assemblage, héritage par un autre outil) est à confirmer en **mission 37** (session longue multi-outils — « le patron du bug Courrier »). Non confirmé comme bug à ce stade.

#### Note méthodo (pour la reprise)
- `window.__labuse` expose les **actions** de l'app (`select`, `setMsel`, `setModule`…) — utilisé pour sélectionner une parcelle / peupler msel de façon fiable.
- **Deep-link outil** : `page.goto()` sur un simple changement de hash **ne re-rend pas** l'outil (quirk driver) — il faut un **reload réel** (vérifié : `#m=assemblage` ouvre bien l'outil au reload) ou cliquer la carte d'outil. Les deep-links `#m=…` sont donc **SAINS**, l'échec apparent était un artefact de test.
- `querySelectorAll('*')` capture le `<style>` Tailwind (~99 Ko) — à éviter dans les `evaluate`.

---

### LOT 3 — Les 13 outils, un scénario métier chacun _(COMPLET — 11 missions faites + 19/26 couverts ailleurs)_

> **Mission 19** (Assemblage contiguës→courriers) = **couvert par M9** (bilan honnête + pont « Préparer les courriers » vérifiés ; le Courrier lui-même est HS = GB-011). **Mission 26** (export CSV) = **couvert** : bouton « ↓ Exporter (CSV) » confirmé présent (Prospection solaire) + patrimoine vérifié M2.

**Mission 21 — Pièges & risques (servitudes, pont Courrier)** → ✅ **SAIN**. 2 voies (Une parcelle / Un lot), intro honnête (« jamais un faux « RAS » … due diligence notariale indispensable »). BZ1065 : « **2 servitude(s)/contrainte(s)** » — ANC « Sourcé GPU — zonages d'assainissement · 2026-08-21 · dispositif individuel à prévoir », SUP « Sourcé SUP — assiettes GPU (API Carto) · 2026-07-10 » (**chacune datée+sourcée**), et « Risques PPR prescriptions constructives — **NON COUVERT PAR LA BASE — À VÉRIFIER AILLEURS** » (honnêteté no-faux-RAS). Pont Courrier = onglet « Un lot » (mémoire), pas sur la vue parcelle unique.

**Mission 23 — Solaire ensoleillement (maille PVGIS)** → ✅/⚠️ PVGIS **sourcé/daté** : potentiel « kWh/kWc/an — productible spécifique PVGIS », footer « PVGIS v5.3 · SARAH3 · RGE ALTI · gelées 11/07/2026 » ; table PARCELLE/CLASSEMENT/POTENTIEL/PENTE/ORIENT./TOITURE + « ↓ Exporter (CSV) ». _Le caveat spécifique « maille ~400 m » (granularité grille, pas par-toit) **non vu dans la liste** — peut-être en détail parcelle ; à confirmer (non poussé)._ Sourcing **SAIN**.

**Mission 17 — Faisabilité « 3 immeubles R+3 de 8 logements »** → ✅ voie critères OK : BÂTIMENTS=3, R+N=3, UNITÉS/BÂT=8 → « **3 090 parcelles · 24 unités → SDP gabarit ≥ ~1 440 m²** » (calcul cohérent : 3×8=24 logements). Le tool cite exactement l'exemple du mandat et dit « périmètre choisi ici — pas hérité du filtre global ». _Voie prefill Copilote (annoncée) → reportée en M33 (quota principal)._ **SAIN.**

**Mission 22 — Permis, « accordés jamais réalisés »** → ✅ **libellé EXEMPLAIRE** : « Accordés, achèvement non déclaré · PC accordés sans DAACT au fichier Sitadel — **majorant à vérifier (le commencement n'est pas tracé), pas « jamais réalisé »** · 15 451 ». Le tool refuse explicitement le terme trompeur. Radar : « 5 613 permis · 5 037 sur la carte · 576 sans localisation · géocodage 90 % · jusqu'au 2026-06-30 » (honnête sur la couverture). _Filtre Le Port/24 mois non appliqué spécifiquement — le point de fond est vérifié._ **SAIN.**

**Mission 18 — Densifier St-Denis (top 20, écartées, 3 fiches)** → ✅ tableau modal riche (**67 258 parcelles** occupées en zone constructible, maj 2026-08-24 ; colonnes **Parcelle · Classement · Score densif. · SDP résiduelle · Surface · Bâti · Zone · Rang commune** — tier/score/SDP étiquetés, cf. mémoire). Toggle **écartées « masquées / les inclure »** fonctionnel (390→400 rendues). Clic sur une ligne → **ferme le modal + ouvre la fiche** de la parcelle (ex. 97404000AZ0004). _Scoping St-Denis spécifique non isolé (table île triée « Rang commune », pas de select commune dans le modal) — assumé._ **SAIN.**

**Mission 20 — PLU (bascule AUc→U, agrégats en paginant)** → ✅ 2 voies (Annuaire PLU / Procédure & changement). Voie procédure : « ⚠ **3 communes en procédure PLU** », périmètre select 24 communes (« choisi ici — pas hérité du filtre global »), bascules **AUc→U / AUs→U / AU→U**. Simulation Saint-Paul (hors procédure) → honnête : « 🕓 Aucune procédure PLU en cours — simulation hypothétique · **Recalcul à blanc — rien n'est persisté** · SDP estimée par analogie aux parcelles U ». _Stabilité des agrégats en paginant non poussée (nécessite une des 3 communes en procédure ; fix plu-perf Lot A déjà validé)._ Structure & honnêteté **SAINES**.

**Mission 24 — Solaire piscines (carte des 8 299)** → ✅ **chiffres exacts**. « Piscines détectées — toute l'île **8 299** · détection ortho/IA · à confirmer sur site » ; méthodo honnête « FLAIR sur BD ORTHO 20 cm 2025 (IGN) — précision ~90,7 % ; seuil de confiance (juge FLAIR ≥ 0,30 × probe ≥ 0,50) » ; par commune **Saint-Paul 1 616**, Saint-Denis 1 317, Saint-Pierre 927… (8299 & 1616 = mémoire, exacts). Filtre surface (≥20/40/60 m²). Footer « PVGIS v5.3 SARAH3 · RGE ALTI · gelées 11/07/2026 ». _« Cliquer 5 gouttes » (interaction carte) non exhaustif._ **SAIN.**

**Mission 27 — Comparaison, stepper + double-Échap** → ✅/⚠️ **PARTIEL** : stepper 3 étapes propre (« Cliquez les parcelles sur la carte » / chips « +1 libre » ×3 / « Comparer (0/3) » / « Revenez à la carte — ✕ ou Échap — votre sélection reste dans ce panneau »). Échap **ferme l'outil proprement** (retour carte, hash vidé). _Comparaison 2 parcelles + double-Échap tableau **non exercés** — le peuplement se fait par clic-carte/fiche (impraticable via le driver ; aucune action compare exposée sur `window.__labuse`)._ Structure & fermeture SAINES.

**Mission 28 — Courrier 3 étapes + notif admin** → ⚠️ **CASSÉE — confirmé après redémarrage** → voir **GB-011** (requalifié : **vrai bug de migration**, pas un serveur stale). Wizard 3 étapes propre (Destinataires → Rédaction → Envoi, 4 gabarits, « adressage générique SPF/CERFA — aucune identité PP »), mais l'action finale « Demander l'envoi à LABUSE » **échoue (500)** : demande non créée, notif admin non déclenchée. _(Aucun objet [GB-TEST] persisté — rien à purger ; re-testé post-restart : 2 lignes legacy inchangées, 0 notif admin.)_

#### GB-011 · 🔴 · bug (migration + cascade de heal au boot) · Courrier 500 + heal de schéma avorté
- **Repro (usage)** : Outils → Courrier → étape 1 ajouter une parcelle (ex. 97411000BZ1065) → Rédiger → Vérifier l'envoi → **« Demander l'envoi à LABUSE »** → l'UI affiche « **La demande n'a pas pu être transmise — réessayez.** » (retry re-échoue indéfiniment). Console : `POST /courrier/demande` et `GET /courrier/demandes` → **500**.
- **Confirmé backend** : `curl :8000/courrier/demandes` → 500 (pas un 404 proxy — `/courrier` est bien proxifié). Le SELECT du handler `courrier.demandes_de` (`SELECT id, ts, n, communes, modele, statut, updated_at … WHERE corps IS NOT NULL`) échoue en base : **`ERROR: column "n" does not exist`**.
- **Cause RACINE (prouvée statiquement + empiriquement) — bug de migration réel, PAS un serveur stale** :
  - `courrier.ensure_tables` (`courrier.py:64`) exécute le DDL ainsi : `for stmt in DDL.strip().split(";"): c.execute(text(stmt))`, le tout dans **une seule transaction** `with engine.begin()`.
  - Or le `DDL` contient un **commentaire SQL avec des `;` internes** (« M82 l'avait déclarée morte (aucun consommateur) **;** elle a désormais cloche + … sans casser **;** anciennes lignes = corps NULL »). Le `split(";")` **coupe ce commentaire** → produit des morceaux de SQL **invalides** : `[3] "elle a désormais cloche +"`, `[4] "anciennes lignes = corps NULL, filtrées à la lecture)." + le CREATE TABLE`. → **erreur de syntaxe** à l'exécution.
  - Comme tout est dans **une seule transaction**, la 1ʳᵉ erreur (morceau [3]) **avorte tout** ; le `CREATE TABLE courrier_demandes` + les 8 `ALTER ADD COLUMN` (morceaux [4]-[13]) **ne s'exécutent jamais**. À chaque boot.
- **État exact du schéma (post-restart, `psql`)** : `courrier_demandes` = `id, ts, sujet, idu, motif, texte, statut` (ANCIEN schéma, créé par un autre chemin ; 2 lignes legacy du **2026-07-16**, statut `a_traiter`). Colonnes attendues **`compte_id, parcelles, n, communes, modele, corps, updated_at` ABSENTES**. Le SELECT du handler → `ERROR: column "n" does not exist`.
- **Redémarrage NE corrige PAS** (testé) : après restart, schéma inchangé, `GET /courrier/demandes` → 500, `POST /courrier/demande` (payload [GB-TEST]) → 500, `courrier_demandes` toujours à **2 lignes** (aucune demande créée), **0 notif admin** (`event_log` source='Courrier' = 0). Le fix requiert de corriger le découpage des statements dans `ensure_tables` (ne pas splitter sur les `;` de commentaire).
- **CASCADE (le cœur du 🔴) — périmètre exact vérifié en base** : la boucle de heal `for _ens in (_modules_ens, _ia_ens, _events_ens, _partners_ens, _projets_ens, _protection_ens, _courrier_ens, _crm_columns_ens, _veilles_ens): _ens(_engine())` (`app.py:109-111`) n'a **pas de try/except par itération** (le try/except est global). `_courrier_ens` est **7ᵉ** → sa levée **abandonne tout le heal restant** : `_crm_columns_ens`(8), `_veilles_ens`(9), puis hors-boucle `_comptes_ens`, `_scoping_ens` (cloison IDOR), `_copilote_ens`.
  - **RUN (avant courrier, OK)** : modules, ia, events, partners, projets, protection.
  - **SAUTÉS chaque boot** : crm_columns, veilles, comptes, scoping(IDOR), copilote.
  - **État RÉEL en base (psql, lecture)** des 5 sautés :

  | Ensure sauté | Migration attendue | État base | Impact |
  |---|---|---|---|
  | crm_columns | table `crm_columns` + `uq_crm_columns_compte_key` | ✅ présent (boot antérieur) | aucun défaut actuel |
  | **veilles** | `UPDATE veilles SET actif=false` sur types non évaluables | ❌ **NON appliqué** | **id=2 `bodacc` `actif=true` — voir GB-011-a** |
  | comptes | tables `comptes`/`utilisateurs`, drop `comptes_plan_check` | ✅ présent (check retiré) | aucun |
  | scoping IDOR | `compte_id` sur SCOPED_TABLES + FK + `uq_pipeline_compte_parcel` | ✅ présent (`pipeline_entries.compte_id` + FK + contrainte) | **pas de trou IDOR actuel** |
  | copilote | `agent_runs` + `fk_agent_runs_compte` | ✅ présent | aucun |

  → **4/5 déjà appliqués par des boots antérieurs** (d'où pas de trou IDOR aujourd'hui), **mais 1/5 (veilles) est un défaut réel actuel**, et **toute FUTURE migration** dans ces 5 modules (y compris de nouvelles règles de **cloison IDOR** — zone sensible) serait **silencieusement non appliquée** tant que courrier est cassé. Le heal est donc **globalement à l'arrêt**.
- **CoSIA (hors cascade — vérifié)** : la normalisation du statut CoSIA vit dans `ingestion/` (pas dans la boucle boot). État base : `data_sources` id=83 « CoSIA » `status='connecte'` (minuscule) → fix S2 **appliqué**, **PAS majuscule**, **non concerné par la cascade**. (Réserve mineure indépendante : `reliability_level` NULL pour CoSIA.)
- **Masquage (fait partie du finding)** : `/readyz` répond `schema.ok:true` / `missing:[]` alors que le heal a échoué (il ne surveille ni `courrier_demandes` ni l'état de `app.state.schema_heal`). Un opérateur qui se fie à `/readyz` **ne verra jamais** que le heal est cassé et que toute migration future est gelée. La sonde de santé **ment par omission**.
- **Gravité : escaladée 🟠 → 🔴.** Justification (consigne Vic « 🔴 si la cascade est confirmée ») : cascade **confirmée** (heal restant abandonné à chaque boot), **défaut réel déjà présent** (GB-011-a veilles), **gel de toute migration future** sur 5 modules dont la **cloison IDOR** (impact sécurité potentiel au prochain changement de schéma), **sonde `/readyz` faussement verte** qui masque le tout, et **outil vitrine (Courrier) entièrement HS non contournable au runtime**. → **TOP 1 du TOP 10.**
- **Note opérationnelle** : ~~« redémarrer le backend en prod applique les migrations »~~ **INVALIDÉ** — ici la migration est intrinsèquement cassée et un redémarrage ne l'applique pas. (La règle « tout déploiement prod DOIT redémarrer le backend » reste vraie en général, mais elle ne sauve PAS ce cas.)
- **SAIN associé** : le front **gère le 500 proprement** (message honnête « La demande n'a pas pu être transmise — réessayez », pas de crash).

#### GB-011-a · (rattaché à GB-011, pas un GB indépendant) · veille fantôme `bodacc` id=2 restée active
- **Symptôme (base)** : `SELECT type, count(*) FILTER (WHERE actif) FROM veilles GROUP BY type` → `permis: 7`, **`bodacc: 1`**. La veille `id=2 type=bodacc` est **`actif=true`** alors que `bodacc` n'est **pas** un type évaluable (`EVALUABLES` = `{permis}`) → veille « active » mais **jamais évaluée** (exactement le défaut V1 de l'audit veille, que le fix FIX-VEILLE devait éteindre).
- **Cause = la cascade GB-011** : la désactivation (`UPDATE veilles SET actif=false WHERE actif AND NOT (type = ANY(EVALUABLES))`) vit dans `copilote_v2/veilles.ensure_tables` — **9ᵉ de la boucle de heal, sautée** parce que `_courrier_ens` (7ᵉ) lève avant. Le fix ne s'applique donc jamais. → **conforme à la règle anti-doublon : rattaché à GB-011, pas de numéro propre.**
- **Résolution attendue** : une fois GB-011 corrigé (découpage DDL courrier), `_veilles_ens` re-tournera au boot et repassera id=2 à `actif=false` (migration idempotente non destructive).

---

**Mission 16 — Étudier BZ1065, cohérence calculette** → ✅ constat sourcé exact (CLASSEMENT Neutre, SHAB vendable 123 m², prix de sortie 4 275 €/m², résiduel net bâti 26 m²). Onglet « Vos hypothèses » = 3 réglages (Coût construction, Marge & frais, VRD). **Cohérence vérifiée** : coût 2550→1500 €/m² fait passer la charge foncière de **−122 911 € (−76 €/m²)** à **+39 k€ (+24 €/m²)** (« ne finance pas » → « ce que l'opération peut payer ») ; marge 21→40 % la refait chuter à **−61 380 € (−38 €/m²)**. Le verdict bouge dans le bon sens (coût↓→charge↑, marge↑→charge↓). Le « Prix demandé du terrain » = comparateur (« 300 000 € dépasse de 519 k€ ce que la charge supporte »). **SAIN.**

**Mission 25 — Communes (St-Joseph/St-Paul/Le Port), chiffres datés & sourcés** → ✅ **exemplaire**. Fiche Saint-Joseph : chaque ligne porte **valeur + source + millésime + fiabilité** — « Prix ancien médian 2 197 €/m² (q1 1763–q3 2599, n9) · Sourcé · DVF 2025 · fragile » ; « terrain nu U 262 / AU 90 €/m² · DVF terrain 2025 · moyenne » ; « Prix de sortie neuf : **non calculable** — charge de marché non atteignable, collectif majoritairement social/aidé · insuffisant » (honnête) ; « Tendance 12 m ↑8.2 % · DVF 2025 · bonne » ; « 49 mut./trim (−9 % an) ». Désambiguïsation « médiane locale vs médiane commune entière » présente (cf. I2). 14 marqueurs source / 8 dates sur la fiche. **SAIN.**

### LOT 4 — Missions transverses métier _(missions 29-38)_

- **M29 — Marchand de biens (chaîne)** → ✅ filtres→shortlist→projet vérifié : projet **id=185** créé, shortlist figée **10 parcelles** (vivier 3363, cap 200). **Dédup douce** honnête (nom OU cadrage → renvoie l'existant, toast « (il existait déjà) »). Kanban→M34, CRM→M35, Courrier→**GB-011-b** (le pont fonctionne, l'envoi final 500).
- **M30 — Liquidation→patrimoine→assemblage** → composition d'outils déjà vérifiés (procédure M1=660, Scan patrimoine M2, Assemblage M9) ; intégration cohérente. _Non rejoué de bout en bout (redondant)._
- **M31 — « 30 logements sociaux < 800 m d'un collège »** → l'app n'a **aucun filtre de proximité à un équipement** ; le Copilote (langage naturel) est offline. Absence **honnête**, pas de fausse promesse — pas un finding (cf. M4 littoral).
- **M32 — Watch / digest** → `GET /events/watch/{idu}` 200, `watch_zones`=3 en base, `digest.html` 200 → mécanisme + digest **SAINS**. _Dessin d'un secteur sur carte non exercé (impraticable driver)._
- **M33 — Copilote 10 questions** → **IMPOSSIBLE ici** : `POST /api/copilote-v2/ask` → 200 mais payload « **service d'analyse indisponible — réessayez** » = **modèle LLM hors-ligne** dans cet env local (PAS GB-011 : `agent_runs` existe). Dégradation **honnête** (200, message propre, pas de crash/invention) → **pas un finding**. Idem voie prefill Copilote de M17.
- **M34 — Projets (décider, rejeu, exports)** → ✅ sur projet 185 : PATCH parcelle → `retenue` (200, réversible), `POST /rejouer` 200, `export.pdf` 200 (application/pdf), `export.csv` 200 (text/csv). **SAIN.**
- **M35 — CRM (colonne, prospect, renommage)** → ✅ colonne [GB-TEST] créée (id=20) + **renommée** (colonnes de Vic **intactes**) ; prospect **idempotent** pour existants (`already:true`, non modifiés), nouveau prospect id=91 + PATCH note/colonne. _Note mineure : `POST /pipeline` **ignore `column_key`/`note` à la création** (défaut reperee/vide) — il faut PATCHer après._
- **M36 — Sources vs couches « i »** → cohérent : 60 sources `connecte` (≈ page 59 via WHERE_AFFICHEES), datation « i »/Fraîcheur des couches vérifiée (M7), page Sources 59 (LOT 1). _Cross-check 5 sources non exhaustif ; échantillon BPE/ZFANG concordant._
- **M37 — Session longue, fuites d'état** → session **très longue continue** sur tous les outils : **aucune nouvelle fuite d'état inter-outils** observée au-delà de **GB-010** (msel persiste à la fermeture Assemblage). Bridges (courrierPrefillIdus/parcelPrefill) consomment à l'usage ; pas de crash ni de croissance mémoire visible. Le « patron du bug Courrier » **non reproduit** ailleurs.
- **M38 — Mobile 390px** → ✅ **responsive** : accueil + fiche sans **débordement horizontal** (scrollWidth=390, 0 élément trop large), bouton Couches mobile dédié. **SAIN.**

_Décision d'exécution (notée) : plusieurs écritures LOT 4 faites via l'API backend (POST/PATCH) plutôt que la seule UI, pour tenir le budget contexte — le flux UI équivalent est vérifié par ailleurs (wizard projet 6 étapes, kanban, CRM). Aucune écriture hors [GB-TEST]._

### LOT 5 — Robustesse et méchanceté _(missions 39-46)_

- **M39 — Double-clic (doublons ?)** → ✅ **pas de doublons** : les créations sont **dédup/idempotentes** (Projets = dédup douce nom OU cadrage ; CRM add = `already:true` ; Assemblage = cap). Un double-clic renvoie l'existant, ne duplique pas.
- **M40 — F5 en plein flux** → ✅ le hash restaure vue/module/commune/filtres/verdict (deep-link vérifié M2) ; les **saisies transitoires** d'outil (calculette, brouillon courrier, sélection comparaison) sont **réinitialisées** (non persistées) mais l'outil **rouvre proprement, sans état cassé** (reload testé des dizaines de fois via `location.reload()` sur tous les outils). Comportement acceptable.
- **M41 — Bouton retour navigateur** → ✅ navigation par **historique de hash** (`#m=…`, `#cs=…`) : le retour ramène à la vue précédente sans crash. _(Mécanisme vérifié ; pas de parcours exhaustif.)_
- **M42 — Champs méchants** → ✅ **robuste, aucun 500** : `/filtre` smin négatif/énorme/non-numérique → 200 (lenient) ; `/parcels/search` émoji / 5000 chars → 200 ; autocomplete émoji → **422 propre** ; **SQL injection** `'; DROP TABLE…` → 404 (M15). Pas de crash, pas de fuite.
- **M43 — Sélection énorme (500 msel)** → ✅ `POST /moteurs/assemblage` avec **500 IDUs** → 200 en 0,66 s, **capé à 30** (`cap:30, tronquee:true`) : plafond **gracieux**, pas de timeout/crash. Le refus est propre (troncature signalée).
- **M44 — Session expirée** → **non testable ici** : « Session pilote » (compte_id NULL, pas de flux d'auth/expiration dans cet env), « Se déconnecter » → `/logout` existe. À rejouer avec un vrai flux compte. _Pas un finding._
- **M45 — IDOR systématique** → ✅ **cloison SOLIDE** : `_scope`/`_projet_or_404` gatent les **12 endpoints `/{pid}`** (35 réfs compte_id dans projets.py), `compte_id`+FK présents en base, sondes `PATCH /projets/9999999` & `DELETE /pipeline/9999999` → **404** (ids étrangers rejetés, pas de 500/fuite). ⚠️ **À REJOUER À DEUX COMPTES avant le 2e client** (bucket pilote unique NULL ici ; le test 2-comptes de `fix-crm-cloison` avait déjà prouvé la cloison /explain+/export).
- **M46 — Couper le backend 10 s** → **non exercé délibérément** (tuer le backend de Vic sort du périmètre sûr ; risque qu'il ne revienne pas). La **dégradation front sur échec d'endpoint est déjà vérifiée par des pannes réelles** : GB-011 Courrier → « réessayez » (propre), Copilote offline → « service d'analyse indisponible » (propre), `/alertes` → **silencieux** (GB-003). Verdict : gestion d'erreur **majoritairement propre**, un cas silencieux (GB-003).

### LOT 6 — Code mort et orphelins _(missions 47-50, statique)_

_(Analyse statique déléguée — `vulture` + `ts-prune` + grep ; aucun fichier modifié. Synthèse console = mission 50, plus haut.)_

#### GB-012 · 🟡 · mort/orphelin · Cruft résiduel (bénin, sans impact usager)
- **47 Python** : `vulture --min-confidence 80` → **9 findings réels** (aucun faux positif route/fixture) : variables assignées jamais lues (`events.py:271 is_market`, `division_or.py:625 decoupe`, `ortho_tiles.py:148 keep_tables`, `pv_detection.py:13 ortho_tile`, `marque.py:34 mime_declare`), branche `else` inatteignable (`registre_faits.py:44`), imports inutilisés (`app.py:40 V_BRULANTE_THRESHOLD`, `verdict_servi.py:35 tier_court/tier_long`). Trivial à nettoyer.
- **47 endpoints front-orphelins** : ~29 paths openapi jamais référencés dans `frontend/src`. La plupart **légitimement server-side** (admin `/protection/admin*`, API externe `/api/v1/*`, anti-bot `/protection/defi`, `/courrier/admin/*`). Vrais candidats produit : **`/modules/division*`** (division morte, cohérent M129-C), `/map/permits.geojson`, `/events/demo`, `/coverage`.
- **48 Front** : `ts-prune` (knip indispo sans config) → **~20 wrappers `lib/api.ts` orphelins** (exportés, 0 importeur : `getEntonnoir`, `copiloteV2Veilles*`, `getShortlist`, `deriveProjet`, `proposerProjet`, `chercherPlus`…) + exports lib inutilisés (`filters.ts activeChips/removeToken`, `status.ts ageSignal/DECLASSE_ORDER…`, `registry.ts VIOLET_DIM/GROUPS`). Les **composants outils dormants** (ScoringV2/M17/M19/O7/O9/O10/M05-07) sont **auto-documentés « retiré/DORMANT, conservé au dépôt »** → intentionnels, PAS des oublis.
- **Impact** : **nul côté usager** — code non atteint. Cohérent avec les dispositifs « en extinction » déjà documentés (table `veilles`, `criteres`/`frequence`, `capacite_estimee`). 🟡 hygiène.

#### SAIN (LOT 6)
- **49(b) — 0 flag `LABUSE_*` défini jamais lu** : les 33 flags sont tous lus (via pydantic `Settings` ou `os.getenv`) — **config propre**, pas de flag mort.
- **49(a) — 0 `FIXME`/`HACK`/`XXX`** ; les 45 `TODO` sont tous des jalons « # TODO étage 1/2 » (feuille de route scoring **assumée**, signaux non branchés au score), pas de dette cachée.

---

## Ce qui est SAIN et vérifié

**LOT 1** :
- **Console propre** sur toutes les vues sauf le cas `/alertes` (GB-003, dev-proxy). Aucune erreur JS, aucun warning React, aucun autre 404/500 réseau sur toute la session (vérifié via `browser_network_requests` filtré).
- **Polling `/events` = 60 s** exactement (gap mesuré 60,2 s sur page fraîche) — sain, pas de boucle emballée (une « rafale » de 170 appels observée au départ = 35 min cumulées, pas un runaway).
- **7 sections de nav rendent toutes** sans casse : IA, Cartes, Outils, Projets, CRM, Veille, Sources.
- **États vides corrects** : colonnes CRM « Contacté » (0) et « En discussion » (0) → « Aucune parcelle / glissez-en une ici ».
- **Compteurs Projets cohérents** : Projet Beta Saint-Paul « 13/33909 retenues » + « 33896 à trier » (33909−13=33896 ✓), cache VIF daté « au 25/08 » — le fix `fix-projets-compteur` (M140) tient sur le principal.
- **CRM privacy** : PP « Propriétaire particulier — non communiqué » vs PM nommée « (registre public DGFiP) » — doctrine respectée.
- **Sources = accueil = 59** (page « 59 sources · 58 à jour » ↔ accueil « 59 sources ») — le fix `page==accueil==59` tient.
- **Copilote** : bouton « Envoyer » désactivé à vide ; brief du matin honnête (« Rien de neuf depuis hier »).
- **Veille Parcelles/Critères** propres (6/50 suivies « aucun changement » ; traducteur NL « Traduire » désactivé à vide).
- **Cloche** : agrégation débordement + « tout lire » + digest 200 (voir GB-002).

**LOT 2** (missions 1-6) :
- **Comptes filtre exacts** : `procedure`=660, `pm_privee`=33 530, union=33 556 (arithmétique d'ensemble vérifiée backend) ; **sémantique OU divulguée** (`FiltreLabuse.tsx:533`).
- **Zonage = sélecteur 2 niveaux SAIN** : cliquer une famille (U) **déplie** ses 131 sous-zones + une option « U seul · toute la famille » (`zf=U`) ; les compteurs zonage **se re-scopent** à la commune sélectionnée (U 306 630 île → 36 682 Saint-Paul).
- **Deep-link hash** rehydraté : `#f`, `smin`, `zf`, `cs`, `v` restaurés à la navigation.
- **Analyse LABUSE honnête** : rapporte « 0 priorité », écartées détaillées (« zonage inconstructible, PPR rouge… » + « voir pourquoi »).
- **Scan patrimoine** fonctionnel (gros + petit détenteur, résumé SDP/valorisation, badges tier, cap autocomplétion « 12 premiers résultats » honnête).
- **Recherche** : IDU court + complet → fiche ; adresse → autocomplétion (numéro + commune + CP).
- **Réinitialiser les filtres** : retour à la base **430 813** + hash vidé (reset propre observé).
- **Capacité absente honnêtement** : pas de critère « proximité littorale » — aucune fausse promesse (mission 4).

**LOT 2** (missions 5,7-15) :
- **Reset filtres complet** (M5) : 4 filtres → « 4 actifs » → Réinitialiser → 430 813 / hash vidé / à zéro. Compteur « N actifs » correct.
- **21 couches** (M7) togglent proprement, 200 partout, 0 erreur console ; BPE plafond 40000 actif ; datation « i »/« Fraîcheur » par couche active.
- **Remonter le temps** (M8) : 6 millésimes 1950→2021 + Auj., split-swipe « après fixe », switch millésime fonctionnel.
- **Assemblage** (M9) : bilan honnête (flag « NON contiguë », charge négative bloc rouge, disclaimer reculs internes, pont Courrier) ; **deep-link outil SAIN** (reload réel).
- **3 fonds** (M10) : Ortho IGN (geopf ORTHOIMAGERY, « © IGN BD ORTHO ») + Plan IGN (PLANIGNV2) → tuiles 200 ; cartouche « Carte à jour au 24/08/2026 ».
- **Verdict fiche == carte** (M11) : 5/5 exacts (même source q_v10_m129).
- **Boutons fiche** (M13) complets ; exports 200 (`explain`, `export.pdf` application/pdf, `dossier.pdf`, `pre-dossier.zip`).
- **Exclusion lisible** (M14) : « écartée : exclusion légale ou physique — motif détaillé ».
- **Erreurs propres** (M15) : 404 honnête, **SQL-injection-safe**, jamais d'écran cassé — pré-couvre M42.

**LOT 3** (outils) : Étudier calculette **cohérente** (coût/marge font basculer la charge), Faisabilité (24 unités, SDP gabarit), **Permis libellé exemplaire** (« pas jamais réalisé »), **piscines 8299 / Saint-Paul 1616 exacts** (méthodo FLAIR honnête), Communes **chaque chiffre daté+sourcé+gradé** (« non calculable » honnête), Densifier (colonnes étiquetées, toggle écartées, fiche depuis ligne), PLU bascule **honnête** (« recalcul à blanc, rien persisté »), Pièges **servitudes datées+sourcées** + « NON COUVERT PAR LA BASE » (no faux RAS), Comparaison stepper + Échap propres.

**LOT 4** (transverses) : Projet créé + **shortlist figée** (dédup à toast honnête), **décider/rejeu/exports PDF+CSV** OK, **CRM colonne créer/renommer + prospect** (Vic intact), **watch + digest** OK, **mobile 390px responsive** (0 débordement), Copilote **dégrade honnêtement** hors-ligne. Absences honnêtes (littoral M4, proximité équipement M31).

**LOT 5** (robustesse) : **aucun 500** sur inputs méchants (négatif/énorme/émoji/5000 chars/SQL), 500 msel → **cap gracieux à 30**, **cloison IDOR SOLIDE** (_scope/_projet_or_404 sur 12 endpoints, sondes 404, compte_id+FK en base), pas de doublons (dédup idempotent), F5 rouvre propre.

**Console (mission 50)** : 0 warning React, 0 exception JS non capturée sur toute la session ; seules erreurs = GB-003 (dev-proxy) + GB-011.

**Verdict global : socle SAIN et honnête** (doctrine « chaque donnée datée+sourcée » tenue partout, dégradations honnêtes, cloison IDOR en place, front robuste). **Un seul défaut grave : GB-011** (Courrier + cascade de heal), le reste = coquilles 🟡.

---

## Synthèse console (mission 50)

Sur **toute la session** (11 lots-passes, tous les outils, navigateur unique) : les **seules erreurs console d'origine applicative** sont **GB-003** (`/alertes`, `/alertes/refresh` — trou proxy dev + échec avalé) et **GB-011** (`/courrier/demandes`, `/courrier/demande` — le 🔴). Les 404 `/watch_zones` et `/parcels/99999000XX9999` étaient mes **sondes délibérées**. **Zéro warning React, zéro exception JS non capturée** sur toutes les pages et tous les outils → runtime front sain.

---

## TOP 10 « à corriger d'abord »

| # | ID | Grav. | Résumé | Action (jamais implémentée par l'audit) |
|---|---|---|---|---|
| 1 | **GB-011** | 🔴 | **Courrier 500 + cascade de heal au boot** : `courrier.ensure_tables` splitte le DDL sur `;` en coupant un commentaire → `CREATE/ALTER courrier_demandes` jamais appliqué → Courrier HS **et** abandon de tout le heal restant (crm_columns/veilles/comptes/scoping IDOR/copilote). `/readyz` ment. Redémarrage ne corrige pas. | Corriger le découpage des statements dans `ensure_tables` (ne pas splitter sur les `;` de commentaire ; ou statements en liste). |
| 2 | **GB-011-a** | 🔴(cascade) | **Veille fantôme** : `veilles.id=2 bodacc actif=true` (type non évaluable) car sa désactivation est dans un ensure sauté par la cascade. | Se résout avec GB-011 (le heal re-tournera). |
| 3 | **GB-008** | 🟡 | **Filtre Communes = codes postaux bruts** (97460…) sans nom, alors que le nom est dans le hash. Friction sur un filtre cœur. | Afficher le nom de commune sur les chips (le mapping existe déjà). |
| 4 | **GB-001** | 🟡 | **Accueil « 16 outils » vs 13 réels** (`MODULES.length` compte 3 alias `hidden`) — faux-chiffre sur la vitrine, contredit par le tiroir « 13 outils ». | Porte : `MODULES.filter(m=>!m.hidden).length`. |
| 5 | **GB-006** | 🟡 | **Scan patrimoine : acronyme « SHLMR » → 0 résultat** (faux-négatif) alors qu'il détient 2618 parcelles sous sa raison sociale. | Indexer/résoudre les sigles connus. |
| 6 | **GB-003** | 🟡 (dev) | **Veille › Secteurs `/alertes` 404 en `npm run dev`** (trou allowlist proxy Vite ; prod OK) **+ 404 avalé en silence** (Nouveautés vide, Rafraîchir no-op). | Ajouter `/alertes` à `apiPaths` (vite.config.ts) + surfacer l'échec côté front. |
| 7 | **GB-007** | 🟡 | **Écart de compte Scan patrimoine** : autocomplétion « N parc. » > scan « N parcelles » (systématique, ex. 2632 vs 2618). | Aligner les deux dénominateurs. |
| 8 | **GB-005** | 🟡 | **CTA « Voir les N parcelles » tarde** à intégrer un 2ᵉ signal (affiche le compte du 1er >2,5 s) avant de se réconcilier. | Rafraîchir le compte à chaque toggle de signal. |
| 9 | **GB-009** | 🟡 | **Omnibox** : « Aucune adresse trouvée » pendant la saisie d'un **IDU valide** (qui s'ouvre pourtant à l'Entrée) → décourageant. | Message autocomplétion tenant compte du format IDU. |
| 10 | **GB-010** | 🟡 | **msel persiste** à la fermeture/réouverture de l'Assemblage (résidu d'état, à surveiller pour fuite carte/inter-outils). | Vider msel à la sortie de l'outil (ou l'assumer comme brouillon). |

**Hors TOP 10 (mineurs)** : GB-002 (badge cloche 1249 non capé, backlog réel), GB-004 (Escape ne ferme pas le dropdown notif) ; observations : dédup projet à toast honnête (M29), `POST /pipeline` ignore colonne/note à la création (M35), caveat maille PVGIS ~400 m non affiché en liste (M23).

_(Le LOT 6 « code mort/orphelins » — statique — est traité séparément ci-dessous ; findings de type `mort`/`orphelin`, gravité 🟡 max, hors TOP 10.)_
