# RADAR-FIX-2 — Radar en pause, mais la donnée s'engrange

**Branche** `fix/radar-fix-2` · worktree `~/Desktop/labuse-radarfix2` (ports 8900/6100).
**Rien mergé, rien déployé, aucun mail réel, aucune écriture en prod.** Correctif des écarts de
`docs/audit-2026-10/radar-etat-1/` (ECARTS.md, RELANCE.md) : *données ON, notifications OFF*.

En une phrase : le Radar **collecte** à nouveau tout seul le soir et nourrit **la prod** ; le cycle de
vie, les baisses de prix et les stats mensuelles **redémarrent** (de la donnée) ; la cloche et le digest
**restent coupés** derrière un interrupteur clair ; et tout se **voit** au Tableau de bord.

---

## Lot A — L'alarme de l'extension part toute seule + trace « auto »

**Le défaut (ECARTS §5).** Toutes les captures réelles tombaient *après minuit* : la trace d'un
lancement à la main, jamais de l'alarme du soir. Et rien, dans les données, ne distinguait une capture
« automatique » d'un clic → l'audit devait *déduire* « manuel » de l'heure.

**La cause.** L'extension posait une alarme UNIQUE à heure fixe (`when` = 21 h + jitter). Trois pièges se
cumulaient : (1) une alarme `when` unique est fragile — Mac endormi/Chrome fermé pile sur le créneau →
l'alarme brûle au réveil (après minuit, exactement la signature observée) ou se fait **écraser** par le
reschedule d'`onStartup` avant de partir ; (2) rien ne garantissait un passage *dans* la fenêtre du soir
une fois l'instant manqué ; (3) la capture ne portait aucune provenance.

**Le correctif — un BATTEMENT DE CŒUR** (`outils/radar-extension/background.js`). Une alarme
**périodique** (toutes les 5 min) réveille le worker ; à chaque battement on regarde si on est *dans la
fenêtre du soir* `[heure .. heure+jitter]` et si on n'a *pas déjà capturé ce soir* — si oui, on capture
**une** fois, source `auto`. Robuste au déchargement MV3 (le périodique survit), honnête sur la fenêtre
(Mac réveillé à 2 h = hors fenêtre → on ne capture PAS à 2 h), une seule capture/soir (garde
`autoRunDate` posée *avant* le run). Côté serveur, `pige_passes` gagne une colonne `source`
(auto | manuel | test) et le journal grave la signature « · déclenchée auto ».

**Fichiers.** `background.js` (heartbeat, `maybeRunTonight`, `source`), `popup.js` (recette « auto »),
`src/labuse/pige/tables.py` (colonne `source`), `src/labuse/pige/api.py` (`CaptureIn.source`,
`_upsert_passe`, ligne de journal).

**Preuves.**
- Chemin alarme → capture, hors navigateur : `node outils/radar-extension/_recette_alarme.mjs` → *« l'alarme
  a déclenché 2 capture(s) (nouvelles + relecture), toutes source auto, vers la prod ; autoRunDate posé »*.
- Bout-en-bout serveur (base `labuse_test`, page Saint-Denis réelle 35 annonces) : `POST /admin/radar/capture`
  `source:"auto"` → `pige_passes.source = 'auto'` et journal `pige.capture` : *« 35 annonce(s) nouvelle(s),
  0 remontée(s) · **déclenchée auto** »*.

**Recette humaine restante** (nécessite Chrome + Leboncoin, non automatisable ici) : charger l'extension,
cliquer **« Tester l'alarme (+2 min) »**, laisser Chrome ouvert → une capture `auto` part seule.

## Lot B — L'extension nourrit la PROD

**Le défaut (ECARTS §4).** L'extension pointait `http://localhost:8205` → elle remplissait la base du Mac,
jamais la prod.

**Le correctif** (`background.js`, `options.js`, `options.html`, `manifest.json`, `README.md`) :
- **Prod par défaut** : `labuseUrl = https://app.labuse.immo`, ajouté aux `host_permissions`. `localhost`
  reste autorisé mais ne sert qu'en **recette explicite** (on le tape dans les Options).
- Jeton de prod lu depuis les Options (inchangé : en-tête `X-Radar-Token`).
- **Rattrapage après bascule** : à la 1ʳᵉ capture après un changement d'hôte LABUSE (`lastCaptureHost`),
  les « nouvelles » remontent jusqu'au **plafond dur de 40 pages** (vs 15 en régime normal) pour
  rattraper depuis la dernière annonce connue en prod. **Règle d'arrêt inchangée** (`index_date` : on
  s'arrête dès qu'une page ne porte plus d'annonce plus récente que le seuil). La bascule est *consommée*
  (les soirs suivants ne rattrapent plus).
- **Échec lisible** : message clair dans le popup (`lastResult` = « Échec … Déposez à la main si ça
  dure. ») ; côté back, l'absence de capture fait apparaître la carte **« Déposer Radar »** dans À faire
  (mécanisme existant, seuil 26 h).

**Preuve.** `node outils/radar-extension/_recette_bascule.mjs` → *bascule : 40 pages « nouvelles » +
hôte consommé ; régime normal : 15 pages ; échec : message lisible*.

**Recette humaine restante** (volontairement NON jouée — « rien en prod ») : sur la machine qui capture,
coller le jeton de prod, lancer une capture, puis **lire** le journal prod (`ssh labuse-vps`) pour la
constater. Aucune écriture prod n'a été faite dans ce mandat.

## Lot C — Dégel partiel des crons

**Le défaut (ECARTS §1).** Les cinq tâches de nuit étaient gelées « Phase 8 Stéphanie ».

**Le correctif** (`src/labuse/jobs.py`, `src/labuse/config.py`) :
- `radar-cycle`, `radar-cycle-dvf`, `radar-cycle-mensuel` **sortent du gel** (de la donnée : retraits,
  ventes DVF, qualification mensuelle).
- `radar-cloche` + `digest` **restent gelés** derrière **UN interrupteur** nommé et documenté :
  `LABUSE_RADAR_NOTIFS` (défaut `off`). `on` les rallume — à basculer au Mac mini une fois des veilles
  clients créées. Helper `_gel_notifs()` ; le gel reste au registre (crontab COMMENTÉ, healthz « gele »).

**Preuves.**
- Crontab généré : `radar-cycle/-dvf/-mensuel` **actifs**, `radar-cloche`/`digest` **commentés**
  `# GELÉ (notifications OFF (LABUSE_RADAR_NOTIFS=off))`. Avec `LABUSE_RADAR_NOTIFS=on` → décommentés.
- Passage local des 3 jobs dégelés (base servie du Mac) : les trois `statut=ok` ;
  `mail_queue` **5 → 5** (0 mail), `event_log kind='radar'` **0** (0 cloche), `kind LIKE '%digest%'`
  **0** (0 digest). → *0 cloche, 0 digest, 0 mail_queue.*

## Lot D — Le voir au Tableau de bord

**Le correctif** (`src/labuse/cockpit_resume.py` `_carte_radar`, `src/labuse/api/dashboard.py`,
`frontend/.../TableauDeBord.tsx`, `types.ts`, `style.ts`). Une carte **« Radar »** sous les 4 tuiles :
**Données ON / Notifications OFF**, **dernière capture auto** (date + nb d'annonces, lue sur
`pige_passes` source=auto), **dernier `radar-cycle`**. **Ambre** si pas de capture depuis **48 h**.

**Preuve.** Captures `captures/lotD-carte-radar.png` (AVANT sans carte / APRÈS vert / APRÈS ambre),
`captures/lotD-radar-vert.png`, `captures/lotD-radar-ambre.png` (harnais `radar-card-harness`, vraie
`<TableauDeBord/>`).

---

## Interdits respectés

Aucun élargissement : pas de dédup, pas de rattachement, pas de refonte de l'écran Radar. Rien mergé,
rien déployé, aucun mail réel, aucune écriture en prod (les preuves prod sont des recettes humaines
documentées, pas exécutées ici).

## Vérifications

- Backend ciblé (base `labuse_test`) : **67 passed, 3 skipped** (test_radar_auto1 / radar_fix1 / pige_api /
  cockpit_lot_a / cockpit_lot_b / cron1_registre / donnees_etat_fix1 / veille_fix1). Tests mis à jour :
  `test_radar_auto1` (+ garde dégel/interrupteur), `test_cockpit_lot_a` (clé `radar`), `test_cockpit_lot_b`
  (gelés = {radar-cloche, digest}).
- Front : **tsc 0** ; vitest **264 passed** (snapshot `Donnees` régénéré pour le CSS de la carte). Les 8
  suites `components/outils/*` en échec local sont un **artefact d'environnement** (import worker
  `maplibre-gl` « Denied » car `node_modules` est un lien vers `labuse-main`), sans rapport avec ce lot.
- Extension : `node --check` OK (background/options/popup) ; `_recette_alarme.mjs` + `_recette_bascule.mjs` verts.

## Artefacts de recette (hors app)

`outils/radar-extension/_recette_alarme.mjs`, `_recette_bascule.mjs` (mocks `chrome.*`, zéro navigateur) ;
`frontend/radar-card-harness.{html,tsx}` (rend la vraie carte, zéro base). Tous marqués « recette ».

## Gestes restants (humains, à la décision)

1. Décider le rallumage des notifications → `LABUSE_RADAR_NOTIFS=on` sur la machine, créer ≥ 1 veille
   Radar client (sinon `radar-cloche` ne matche rien), redéployer le crontab.
2. Sur la machine qui capture (Mac mini conseillé) : jeton de prod dans les Options, recette
   « Tester l'alarme (+2 min) », puis lire le journal prod pour constater la 1ʳᵉ vraie capture.
3. Merge + déploiement (hors de ce mandat).
