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

---

## TOP 10 « à corriger d'abord »

_(rempli au livrable final)_
