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

### LOT 2 — Missions recherche / carte / fiches _(PARTIEL — missions 1-6 traitées ; 5,7-15 à reprendre)_

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

---

## TOP 10 « à corriger d'abord »

_(rempli au livrable final)_
