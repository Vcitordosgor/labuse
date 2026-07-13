# M6 Phase 1 — §1.6 Audit UI exhaustif (+ §1.8 adresse BAN)

Audit LECTURE SEULE du 13/07/2026, branche `audit/grand-check`, app `http://127.0.0.1:8010/socle/` (LABUSE_DEV_MODE).
Harnais : Playwright (`frontend/qa/audit_m6_*.mjs`, 8 scripts), console + réseau écoutés à chaque clic, contre-vérification SQL (`psql labuse`, SELECT uniquement). Captures sous `reports/m6-audit/captures/`, données brutes sous `reports/m6-audit/*.json`.

**Doctrine de test** : tout ce qui LIT est cliqué ; les actions qui ÉCRIVENT en base (+ Pipeline, Suivre, Partage, + Veille, tout lire, dupliquer/désactiver une vue, Renommer/Archiver un projet, retirer du pipeline, drag kanban, soumission courrier) sont inventoriées mais **non cliquées** (audit lecture seule) — statut « NON TESTÉ (écriture) », handler vérifié dans le code.

---

## 1. Inventaire des boutons — tableau complet

Statuts : **OK** = effet attendu observé (réseau et/ou DOM/pixel) · **MORT** = aucun effet · **CASSÉ** = erreur console/HTTP · **REDONDANT** = doublon d'un autre contrôle · **NON TESTÉ (écriture)**.

### 1.1 Rail de navigation (`Rail.tsx`)

| Bouton | Action attendue | Observé | Statut |
|---|---|---|---|
| IA | vue IA (recherche NL) | vue IA rendue (24 éléments) | OK |
| Cartes | vue carte + panneau | rendue | OK |
| Outils | tiroir 19 modules | tiroir rendu, 19 cartes | OK |
| Vues | page Vues (`#pg=vues`) | rendue, hash mis à jour | OK |
| Projets | panneau projets | rendu | OK |
| CRM | kanban pipeline | rendu (6 parcelles) | OK |
| Sources | page fraîcheur des sources | rendue | OK |

### 1.2 Header (`header/Header.tsx`)

| Bouton | Action attendue | Observé (réseau) | Statut |
|---|---|---|---|
| Omnibox + Entrée (commune) | bascule le périmètre | `GET /stats?source=q_v3_datagap&commune=Saint-Denis` 200, hash `c=Saint-Denis` | OK |
| Omnibox + Entrée (IDU « AC 0253 ») | ouvre la fiche | `GET /parcels/search?q=AC0253` → fiche 97415000AC0253 (`/events/watch/…`, `/pipeline/parcel/…`) | OK |
| Omnibox IDU inexistant | message d'erreur | toast « Aucune commune ni parcelle trouvée pour “97499000ZZ9999” » (`etat-idu-inexistant.png`) | OK |
| Loupe « Lancer la recherche » | comme Entrée | bascule Sainte-Marie | OK (REDONDANT assumé avec Entrée) |
| Sélecteur commune | menu 24 communes + « voir la fiche commune → » | menu rendu (`btn-commune-menu.png`) | OK |
| ⓘ Contexte | volet SRU/ANRU/PLH/marché | `GET /communes/Sainte-Marie/contexte` 200, volet rendu (`btn-contexte.png`) | OK |
| Toggle « Verdict » | carte colorée par tier v2 | rendu + légende « VERDICT · SCORING V2 » | OK |
| Toggle « Mutabilité » | carte en dégradé SDP résiduelle | rendu + légende « MUTABILITÉ » (`btn-mode-mutabilite.png`) | OK (⚠ sémantique, cf. §5) |
| Cloche « 17 » Notifications | popover événements + veilles | `GET /events?limit=100`, `GET /events/searches` — popover rendu (`btn-notifications.png`) | OK (⚠ contenu, cf. §3) |
| Popover notif : item événement | ouvre la fiche de la parcelle | handler `select(e.idu)` (code) | NON TESTÉ (navigations en cascade) |
| Popover notif : « tout lire », ✓ marquer lu, « + Veille », suppression veille | écritures `event_log`/`saved_searches` | handlers vérifiés dans le code | NON TESTÉ (écriture) |
| Popover notif : « Digest → » | page HTML digest | `GET /events/digest.html` 200 (curl) | OK |
| « + Filtre » | popover filtres | rendu (91 éléments) — cf. §2 | OK |
| Chips filtres actifs « × » | retire le filtre | vérifié via recherche IA (chips « Chaude v2 × », « ≥ 1 000 m² × », « Vue mer × » posées puis état cohérent) | OK |
| Avatar « VL » | affichage seul | aucun handler | OK (inactif assumé) |

### 1.3 Panneau gauche — couches (`panel/LeftPanel.tsx`)

Les 9 toggles de couches (Zonage PLU, Parcelles, PPR, Vue mer, Parc national, Limites parcelles, Limites communes, ANRU, Équipements) ont été audités en M5.1 lot 4 (`reports/m51-unification/AUDIT-COUCHES.md`, 9/9 OK) ; re-vérification ciblée ici :

| Bouton | Observé | Statut |
|---|---|---|
| Toggle ANRU (commune SANS périmètre : Entre-Deux) | `GET /map/layers.geojson?kind=anru&commune=Entre-Deux` 200 — **0 feature, aucun message utilisateur** (`etat-anru-muet.png`) | OK mécaniquement, **ANOMALIE d'état vide (A3 confirmée)** |
| « masquer » / « Afficher l'analyse LABUSE → » | couleurs verdict off/on (diff DOM) | OK |
| « ‹ » replier / « › » déplier | panneau replié/déplié, tuiles rechargées | OK |

### 1.4 Panneau gauche — résultats (`panel/ResultsSection.tsx`)

| Bouton | Action attendue | Observé | Statut |
|---|---|---|---|
| Chip « Tout 13 400 » | périmètre v2 hors étage 0 | retour à « 13 400 visibles ici » | OK |
| Chip « Brûlantes v2 27 » | tiers=brulante | liste 27 brûlantes (`btn-chip-brulantes.png`) | OK |
| Chip « Chaudes 222 » | tiers=chaude | liste filtrée | OK |
| Chip « Réserve foncière 444 » | tiers=reserve_fonciere | liste filtrée | OK |
| Chip « À creuser 12 707 » | tiers=a_creuser | liste filtrée | OK |
| Chip « Écartées 37 729 » | opt-in étage 0 dur | liste + carte rouge opaque (`btn-chip-ecartees.png`) | OK |
| Tri « rang P » / « ×N » / « surface » / « commune » | réordonne la liste | ordre de liste changé pour les 4 | OK ×4 |
| « pourquoi ? ▾ » (entonnoir) | popover motifs | `GET /stats/entonnoir?commune=Saint-Paul` 200 — tiers v2 exacts, **mais `motifs: []`** (cf. §7) | OK (⚠ état vide) |
| Checkbox « masquer les copropriétés » | hors_copro | compteurs recalculés 13 400 → 13 312 (SQL-exact) | OK |
| Lien « ⬇ CSV » | export liste filtrée | href `/parcels/export.csv?source=q_v3_datagap&commune=…&limit=5000&sort=rang` (200) — **sans adresse BAN**, cf. §6 | OK |
| « Tout voir → » | étend la liste | 200 → **13 400 cartes rendues dans le DOM** | OK (⚠ perf : 13 400 nœuds, aucun virtualiseur) |
| Carte de résultat (clic) | ouvre la fiche | fiche 97415000DK1044 rendue (`btn-carte-resultat-fiche.png`) | OK |
| État vide : « Élargir à toute l'île » / « Réinitialiser les filtres » | sortie du vide | rendus (vu sur liste vide Sainte-Marie) | OK |

### 1.5 Toolbar carte (`map/MapToolbar.tsx`) + carte (`map/MapView.tsx`)

| Bouton | Observé | Statut |
|---|---|---|
| Zoom « + » / « − » | tuiles rechargées / diff pixel | OK ×2 |
| « Fond de plan » (popover) | 3 basemaps + « REMONTER LE TEMPS » | OK |
| Basemap Ortho IGN | WMTS `ORTHOIMAGERY.ORTHOPHOTOS` 200, rendu changé | OK |
| Ortho « 1950-1965 » / « 2000-2005 » / « Actuelle » | ortho historique rendue (`btn-ortho-1950.png`) | OK |
| Basemap Plan IGN | (testé indirectement via cycle) | OK |
| « 3D » on/off | tuiles terrarium 200, relief rendu (`btn-3d.png`) | OK |
| Outil Distance | tracé + mesure (diff pixel, `btn-mesure-distance.png`) | OK |
| Outil Surface | polygone + m² (`btn-mesure-surface.png`) | OK |
| Outil Altitude | `GET /altimetrie/...elevation.json` 200 (`btn-altitude.png`) | OK |
| Outil Zone | polygone → résultats filtrés + badge « Zone active × » (`btn-zone-filtre.png`) | OK |
| « Zone active × » | filtre zone retiré | OK |
| Clic carte sur parcelle | ouvre la fiche | OK |

### 1.6 Fiche parcelle (`fiche/Fiche.tsx`) — testée sur riche (97415000AC0253) et pauvre (97415000AH0586)

| Bouton | Observé | Statut |
|---|---|---|
| Onglets Synthèse / Règles / Risques / Marché / Proprio / Solaire / Bilan | 7/7 rendus sur les 2 fiches (captures `fiche-riche-*.png`, `fiche-pauvre-*.png`) | OK ×7 |
| « ✕ » fermer | fiche fermée | OK |
| Barres score Qualité / Accessibilité / Signaux vendeur (dépliables) | lignes signées + sources dépliées (`fiche-riche-scores-deplies.png`) | OK |
| Référence source (ex. `spatial_layers#…`) → SourceDrawer | drawer « SOURCE » ouvert, « Toutes les sources → » présent | OK |
| Recherche dans la fiche (loupe) | champ + compteur de résultats | OK |
| Calculette charge foncière (3 inputs) | recalcul « selon vos hypothèses » ; ⚠ affiche « Charge foncière supportable −69 k€ » (négatif) sur la fiche pauvre | OK (⚠ copy, cf. §7) |
| « → tout son patrimoine (M02) » (Proprio) | préremplit Scan patrimoine | handler vérifié (code) — module M02 testé OK | OK |
| Bloc RTAA « 10 exigences → » | dépliage exigences + liens Légifrance | OK |
| Bouton « IA » (Analyse IA) | popover Synthèse / « Pourquoi ce score ? » | popover ouvert (onglets présents, aucun appel réseau à l'ouverture) ; la génération (clic onglet = POST) non déclenchée — écriture/coût ; repli stub crédits épuisés connu | OK |
| Recherche interne (données) | « 3 résultats » pour « PLU » sur la fiche riche | compteur exact | OK |
| SourceDrawer — contenu | « SOURCE · Fichiers fonciers (Cerema) » : EXTRAIT + fournisseur/catégorie/accès/fiabilité + « Toutes les sources → » ; état honnête « Propriétaire inconnu (Fichiers fonciers sous convention non branchés) » | | OK |
| Calculette — verdict achat | coût 2 200 €/m², prix demandé 150 k€ → « ✓ Supportable — le terrain peut valoir 150 k€ ; marge de 252 k€ (+168 %) » | recalcul complet | OK |
| « PDF » | href `/parcels/{idu}/export.pdf` | OK (href, non téléchargé — mandat exports) |
| « Dossier » | href `/dossier/{idu}.pdf` | OK (href) |
| « 1950 » | ouvre module « Remonter le temps » | module testé OK (§1.7) | OK |
| « Cadastre » / « G » | liens externes Géoportail / Google Maps | hrefs présents | OK |
| « + Pipeline » / « 👁 Suivre » / « ↗ Pack apporteur » | écritures (pipeline, watch, lien public) | handlers vérifiés | NON TESTÉ (écriture) |

### 1.7 Menu Outils — 19 modules (`outils/registry.ts`)

Chaque module ouvert, réseau + console écoutés, capture `outil-*.png` : **Scoring v2 (P) · Faisabilité programme · Parkings APER · Toitures tertiaires · Division parcellaire · Foncier fantôme · Scan patrimoine · Mode bailleur · Matching promoteurs · Assemblage · Baromètre foncier · Radar permis · Promesses mortes · Vélocité admin · Simulateur PLU · Simulateur ZAN · Remonter le temps · Due diligence · Courrier propriétaire → 19/19 OK** (aucune 4xx/5xx, aucune erreur console). Les formulaires générateurs (courrier, due diligence par lot) n'ont pas été soumis (écriture).

### 1.8 Autres écrans

| Écran / bouton | Observé | Statut |
|---|---|---|
| Vues — « Recalculer les compteurs » | compteurs rafraîchis | OK |
| Vues — ouvrir « Foncier — Brûlantes & chaudes » | vue chargée « 27 brûlantes · 222 chaudes » (v2) | OK |
| Vues — « argumentaire » | panneau argumentaire rendu | OK |
| Vues — « dupliquer » / « désactiver » / recherche NL de vue | écriture / POST IA | NON TESTÉ (écriture) |
| Projets — « Ouvrir » (rejouer) | filtres rejoués sur données actuelles | OK |
| Projets — « + Décrire un projet » / « Renommer » / « Archiver » | écritures | NON TESTÉ (écriture) |
| CRM — clic IDU « Ouvrir la fiche sur la carte » | fiche ouverte | OK |
| CRM — « ✕ » retirer, drag entre colonnes | écritures pipeline | NON TESTÉ (écriture) |
| IA — saisie + « Chercher » | `POST /ia/search` 200 → traduit en filtres serveur `tiers=chaude&surface_min=1000&vue_mer=true`, chips posées, 16 chaudes (SQL-cohérent) | OK |
| IA — 6 chips de suggestion | remplissent la requête | OK (déclenchent la même chaîne) |
| IA — « Démarrer le montage » | copilote projet (écriture projet) | NON TESTÉ (écriture) |
| Sources — « Imprimer » | `window.print()` intercepté = appelé | OK |
| Sources — « Source officielle ↗ » | lien externe (adresse.data.gouv.fr, …) | OK (href) |

### 1.9 Compte final

- **Testés cliqués : ≈110 actions uniques** (8 scripts ; les reprises de harnais — popovers à overlay — dédupliquées) → **tout ce qui a pu être jugé est OK : 0 bouton MORT, 0 bouton CASSÉ côté produit**.
- **NON TESTÉS (écriture, doctrine lecture seule) : 17 contrôles** — tous les handlers tracés dans le code (agents de lecture), aucun bouton orphelin.
- **REDONDANTS assumés (pas des anomalies)** : loupe omnibox = Entrée ; « masquer les copropriétés » existe en 2 endroits (panneau + popover Filtre, même setter `horsCopro`) ; chips tiers du panneau = section « VERDICT · SCORING V2 » du popover (même `filters.tiers`).
- **Bruit console (hors produit)** : fetch des glyphes `basemaps.cartocdn.com` bloqué CORS dans l'environnement d'audit (labels de carte) ; sans effet fonctionnel constaté.
- **Constat harnais devenu constat produit** : **Échap ne ferme aucun popover** (notifications, + Filtre, entonnoir, fond de plan) — seule la fermeture clic-hors-zone existe (`div.fixed.inset-0`). Mineur mais systémique.

---

## 2. Filtres — utiles, pertinents, fonctionnels ? (contre-vérification SQL)

Périmètre : Saint-Paul, run servi `q_v3_datagap`, run v2 `m36-l2f-2026-2026-07-12`, périmètre par défaut = hors étage 0. **Chaque compteur affiché a été rejoué en SQL : 12/12 exacts.**

| Filtre (popover « + Filtre » / chips) | UI affiche | SQL attendu | Verdict |
|---|---:|---:|---|
| Tout (défaut) | 13 400 | 13 400 | ✔ exact |
| Brûlantes v2 | 27 | 27 | ✔ |
| Chaudes | 222 | 222 | ✔ |
| Réserve foncière | 444 | 444 | ✔ |
| À creuser | 12 707 | 12 707 | ✔ |
| Écartées (étage 0 dur) | 37 729 | 37 729 | ✔ |
| Vue mer dégagée | 3 034 | 3 034 | ✔ |
| Veille succession | 221 | 221 | ✔ |
| Surface ≥ 1 000 (cumulé veille — artefact harnais assumé) | 56 | 56 | ✔ |
| Avec événement (BODACC) | 1 | 1 | ✔ |
| Masquer les copropriétés | 13 312 | 13 312 | ✔ |
| Signal proprio « Procédure collective » | 15 | 15 | ✔ |
| Flag « ⚑ Risques (PPR/aléa) » | 12 960 | 12 960 | ✔ |
| SCORE Q ≥ 70 | 641 | 641 | ✔ |
| Réinitialiser tous les filtres | 13 400 | 13 400 | ✔ |

Jugement d'utilité :
- **Utiles et pertinents** : tiers v2, vue mer, veille succession, surfaces, événement BODACC, hors copro, signaux propriétaire (libellés métier clairs), flags de vigilance.
- **« SCORE Q ≥ » : pertinence à instruire** — filtre le `q_score` MATRICE dans un popover pilotée v2 (« VERDICT · SCORING V2 »). C'est le dernier filtre à vocabulaire matriciel côté client ; soit le renommer « Qualité (Q) » avec tooltip, soit le déplacer en « avancé ».
- **« SDP ≥ m² »** : utile (promoteur) mais sigle non expliqué à cet endroit (il l'est dans la légende Mutabilité).
- **« ⚑ Prescription PLU », « ⚑ ABF », « ⚑ ICPE », « ⚑ Pollution »** : même mécanisme SQL que « ⚑ Risques » testé exact (couche `flags`), considérés fonctionnels.
- La sérialisation URL des filtres (`filtersToHash`, `tv=` depuis M5.1) permet les liens partageables ; **attention** : ce même hash sert les veilles (cf. §3).

---

## 3. Notifications — que déclenchent-elles vraiment ?

**Moteur : `src/labuse/api/events.py` — CONFIRMÉ resté MATRICE** (comme consigné au TABLEAU-LEXICAL M5.1).

- Déclencheur : `detect_events(run_from, run_to)` (l. 56) compare `dryrun_parcel_evaluations.matrice_statut` entre deux runs. 4 détecteurs : `bascule` (changement de statut matrice), `bodacc` (événement rouge nouveau), `permis` (SITADEL ≤ 300 m d'une parcelle suivie/pipeline), `veille` (bascule montante ∧ filtres d'une recherche sauvegardée). Persistance `event_log`, idempotent.
- **Véracité — les notifications racontent l'ANCIEN monde** :
  - Titres réels en base (18 événements, tous du 10/07) : `▲ AD0396 : a_surveiller → chaude`, `▼ BK0301 : chaude → a_surveiller` — **« a_surveiller » n'existe plus dans l'UI** (v2 dit « Réserve foncière ») ;
  - le payload `/events` expose `statut: "a_surveiller"` ;
  - le détail veille (l. 181) énonce « Bascule vers {matrice_statut} qui matche votre veille » ;
  - **les 18 événements sont `demo=true`** (seed `q_v2_demo` du 10/07) — le badge « 17 » de la cloche vend 17 alertes non lues qui sont TOUTES des données de démonstration (marquées « DÉMO » dans le popover, mais le badge, lui, ne distingue pas).
- **Double désynchronisation veilles** : le parseur serveur `_parse_hash_filters` (l. 129-137) ne connaît que `st=` (statuts matrice), `vm`, `ev`, `q`, `smin/smax`, `sdp`, `fl`. Or depuis M5.1 le front sérialise `tv=` (tiers v2), `veille`, `copro`, `v_signal`… → **une veille sauvegardée aujourd'hui verra son filtre de tier silencieusement IGNORÉ** par le moteur (notifications faux-positives), et ses bascules seront comparées en statuts matrice. C'est exactement le « veilles `st=` à re-sauvegarder » de M5.1, aggravé : même re-sauvegardée, une veille `tv=` n'est pas comprise. 0 veille en base aujourd'hui (`saved_searches` vide) — fenêtre idéale pour corriger avant tout abonné réel.
- **Valeur pour l'abonné (aujourd'hui)** : faible — flux figé au 10/07, 100 % démo, vocabulaire d'un monde retiré de l'UI. Le canal (cloche + digest HTML `/events/digest.html`, fonctionnel) et la mécanique (idempotence, kinds, montantes) sont sains.
- **Proposition de mise en valeur (Phase 2)** :
  1. **Basculer le moteur sur les tiers v2** : diff de `parcel_p_score_v2.tier` entre runs v2 (« ▲ AD0396 : Réserve foncière → Brûlante v2 · rang 117→23 ») + parse `tv=` dans `_parse_hash_filters` ; le rang et ×N rendent la bascule vendeuse.
  2. **Badge honnête** : exclure `demo=true` du compteur non-lu (ou badge « DÉMO » sur la cloche elle-même) tant qu'aucun run réel n'a tourné.
  3. **Digest hebdo actionnable** : grouper par veille et par commune, joindre l'adresse BAN et le lien fiche — c'est la brique « suivi de cible » (M14) qui justifie l'abonnement.

**Indice /stats (élucidé)** : `GET /stats` SANS `source` sert la forme legacy v1 (`parcel_evaluations` : `opportunite: 6021, a_creuser, exclue, completeness_avg…`, app.py l. 791-817) — un monde ni matrice-dryrun ni v2. Le front, lui, envoie TOUJOURS `source=q_v3_datagap` (`lib/api.ts` l. 14 et 45) et reçoit la ventilation tiers v2 (`{tiers:{brulante:117,…}, opportunites:1077}`) ; vérifié en réseau live sur chaque écran. Aucun consommateur du legacy trouvé (front, scripts, cron). **Reco** : faire de `q_v3_datagap` le défaut serveur de `/stats` (et renvoyer la forme legacy uniquement sous `?legacy=1`), pour qu'un curl nu ne raconte plus 6 021 « opportunités » d'un monde mort (vs 1 077 réelles).

---

## 4. Audit sémantique — ce qui reste faux ou jargonneux

(Complément du TABLEAU-LEXICAL M5.1 — les 32 occurrences déjà traitées ne sont pas re-listées ; rien de traité n'a régressé : vérifié à l'écran sur chips, tri, cartes, fiche, légende, exports.)

| Endroit | Constat | Gravité / proposition |
|---|---|---|
| Notifications (`/events`, titres + `statut`) | « a_surveiller », « Bascule chaude » = matrice | **LE reste lexical majeur** (cf. §3) |
| Header : toggle « **Mutabilité** » | collision avec « probabilité de **mutation** » (scoring v2, vente) : ici « mutabilité » = SDP résiduelle constructible | Renommer « Potentiel (SDP) » ou « Constructible » ; la légende dit déjà « SDP résiduelle » |
| Popover filtres : « SCORE Q ≥ » | sigle matrice pilote dans une UI v2 | tooltip `SCORE_TIP.q` existe ailleurs — l'appliquer ici, ou reléguer |
| « SDP » (filtre, légende, cartes outils) | jargon promoteur, jamais développé (« surface de plancher ») | 1 tooltip à la première occurrence de chaque écran |
| « ×N » / « rang P » (tris, cartes) | jargon v2 ; tooltips présents sur les tris, pas sur le « ×13.1 » des cartes de résultats | title sur la valeur ×N des cartes |
| « ◠ » (vue mer, cartes de résultats) | glyphe cryptique, tooltip présent mais invisible au premier regard | légende locale ou libellé au survol suffisant — à trancher |
| « 92 » (anneau complétude sur chaque carte) | nombre nu ; tooltip au survol seulement | acceptable, consigner |
| Vues : badge « COMPLET » | signifie « toutes les données du preset sont disponibles », peut se lire « liste complète » | « données 100 % » ou tooltip |
| Fiche : bloc « MODULE · M01/M22 » | code interne exposé au client | afficher le nom du module, code en secondaire |
| Fiche pauvre : « signaux vendeur 0/100 » + « Signaux partiels » | 0/100 pour « aucun signal » lisible comme un score calculé très bas | la bande V a un état « aucun » — l'utiliser (« aucun signal public ») |
| Calculette : « Charge foncière supportable » suivi de « **−69 k€** » | un montant négatif sous un titre positif ; la mention « NÉGATIVE en bas de fourchette » arrive après | inverser : verdict d'abord (« opération non viable à ces hypothèses ») |
| « Pack apporteur », « Digest » | jargon métier assumé, tooltips corrects | RAS (consigné) |
| Écran Vues, IA, entonnoir | vocabulaire v2 partout (« brûlantes v2 », « réserve foncière », « rang ») | conforme M5.1 ✔ |

---

## 5. Vignette légende (bas droite) — CONSERVÉE, synchro v2 vérifiée

DOM live (`legende-dom.json`) vs code (`lib/status.ts` `TIER_V2_META`, source de vérité unique ; `verdictMeta` ; chips `ResultsSection.tsx` l. 103-108 ; carte `MapView.tsx` l. 54-60) :

| Tier | Légende (DOM) | `TIER_V2_META` | Chips | Carte (fill) |
|---|---|---|---|---|
| Brûlante v2 | rgb(232,105,90) = #E8695A | #E8695A | #E8695A | #E8695A (op. 0,95 + liseré braise) |
| Chaude v2 | #E8B44C | #E8B44C | #E8B44C | #E8B44C (0,9) |
| Réserve foncière | #6FA8DC | #6FA8DC | #6FA8DC | #6FA8DC (0,55) |
| À creuser | #8FA69A | #8FA69A | #8FA69A | #8FA69A (0,45) |
| Écartée | #4A5A52 | #4A5A52 | #4A5A52 | **#E8695A à 4 %** (étage 0 quasi invisible) |

- Titre « VERDICT · SCORING V2 », ordre `LEGEND_V2_ORDER` — **libellés et couleurs identiques pixel/DOM pour les 4 tiers actifs : SYNCHRONISÉE** (capture `legende-verdict.png`).
- Mode Mutabilité : la vignette bascule sur le dégradé « 0 m² — SDP résiduelle — 5 000+ » identique à `MUTABILITE_COLOR` ✔ (`legende-mutabilite.png`).
- Branche legacy (matrice) : uniquement si `/v2/modele` est indisponible — non observée (run v2 présent), conforme.
- **Nuance consignée (pas une demande de suppression)** : pour « Écartée », la légende/chips montrent #4A5A52 (gris-vert `TIER_V2_META`) alors que la carte peint l'étage 0 en #E8695A à 4 % d'opacité et que le badge de fiche d'une écartée suit `verdictMeta` → `STATUT_META.ecartee` **#E8695A rouge**. Trois rendus pour un même mot ; défendable (règle « l'étage 0 prime »), mais si un client compare la pastille de légende au badge de fiche, elles diffèrent. À trancher en Phase 2a (aligner la pastille légende sur #E8695A ou le badge sur #4A5A52).

---

## 6. §1.8 Adresse postale (BAN) — où est-elle visible ?

Base : `adresses` + `adresse_parcelles`, **100 % des 257 145 parcelles couvertes** ont au moins une adresse (jointure vérifiée : `97403000AR1104 → 2 Impasse des Caramboles, 97414 Entre-Deux`). La donnée existe, elle n'est presque jamais montrée :

| Vue | Adresse visible ? | Détail |
|---|---|---|
| **Fiche parcelle** (`GET /parcels/{idu}`, `Fiche.tsx` en-tête) | **NON — ANOMALIE majeure** | payload sans aucun champ adresse (`_q_v2_fiche` app.py l. 1196-1356 ; `_build_fiche` l. 1827-1831 : le « numero » est cadastral) ; l'en-tête affiche IDU · m² · commune. **Un commentaire de `MapView.tsx` l. 19-20 promet « la fiche porte l'adresse » — contrat non tenu** |
| Cartes de résultats (`ResultsSection.tsx`) | **NON — anomalie** | « DK 1044 · 426 m² · Saint-Paul », jamais la rue |
| Omnibox | **NON — anomalie** | recherche par commune/IDU uniquement ; impossible de chercher « 12 rue … » |
| Popup carte | **NON — anomalie** | clic parcelle → fiche (sans adresse) ; popups réservés aux équipements |
| CRM kanban | **NON — anomalie** | IDU + statut seulement |
| CSV du panneau résultats (`/parcels/export.csv`) | **NON — anomalie** (vérifié : en-têtes `idu,commune,surface…` sans adresse) | à distinguer des exports segments ↓ |
| Exports Vues/segments (CSV) | **OUI** | `BAN_EXPORT_KEYS` émis d'office en tête (`segments/engine.py` l. 25-28) |
| Publipostage | **OUI** | adresse BAN obligatoire (refus 409 sinon) |
| Pré-dossier PC (`/dossier/{idu}.pdf`) | **OUI** | CERFA cadre terrain rempli depuis `adresse_parcelles` |
| PDF fiche premium (`pdf_premium.py`) | **NON — anomalie** | la fiche PDF identifie la parcelle sans adresse (noté ; mandat exports en parallèle) |

**Verdict §1.8 : 7 vues identifient une parcelle sans son adresse** (fiche, cartes de résultats, omnibox, popup carte, CRM, CSV panneau, PDF fiche) → liste pour correction Phase 2a. Le plus rentable : ajouter la jointure BAN dans `/parcels/{idu}` + en-tête de fiche, puis cartes de résultats et omnibox (géocodage BAN inverse déjà disponible).

---

## 7. États vides et erreurs — ce que voit le client

| Cas | Ce que voit le client | Verdict | Capture |
|---|---|---|---|
| Parcelle écartée (étage 0) | bandeau « **LABUSE l'a écartée — voici pourquoi** » + motifs sourcés (« ✕ bati — déjà bâtie : 4 bâtiment(s)… ») | ✔ exemplaire | `fiche-pauvre-synthese.png` |
| Onglet fiche sans signal | « Aucun signal sur cet onglet. » | ✔ | `fiche-pauvre-proprio.png` |
| Propriétaire personne physique | « Propriétaire : personne physique ou non recensé… (workflow SPF/CERFA, jamais automatisée) » | ✔ honnête | idem |
| Solaire sans donnée réelle | estimations toutes étiquetées « estimation statistique — jamais une donnée réelle » | ✔ | `fiche-pauvre-solaire.png` |
| DPE absent / pas de mutation DVF | ligne source « Aucune mutation… » / signal absent sans faux zéro ; marché : « X ventes ≤ 1000 m » sinon section repliée | ✔ |  |
| Liste vide (commune/filtres) | « Aucune parcelle ne correspond… » + boutons « Élargir à toute l'île » / « Réinitialiser les filtres » | ✔ | `btn-notifications.png` (arrière-plan) |
| IDU/commune introuvable (omnibox) | toast « Aucune commune ni parcelle trouvée pour “…” » | ✔ | `etat-idu-inexistant.png` |
| **Couche ANRU sur commune sans périmètre** | **rien** : toggle actif, 0 feature (`layers.geojson?kind=anru&commune=Entre-Deux` → 0), aucun message | ✗ **A3 confirmée** — proposer un toast « Aucun périmètre ANRU dans cette commune (8 quartiers : Le Port, St-Denis…) » | `etat-anru-muet.png` |
| **Entonnoir « LE RESTE, PAR MOTIF »** | titre de section affiché avec `motifs: []` — la promesse « pourquoi le reste est écarté (SQL-exact) » n'affiche AUCUN motif sur ce run | ✗ faux-vide — masquer la section ou afficher « ventilation par motif non matérialisée sur ce run » | `btn-entonnoir.png` |
| Veilles (0 sauvegardée) | juste le titre « VEILLES » + champ « + Veille », sans phrase d'explication | ~ passable — une ligne de valeur (« Sauvegardez une recherche pour être alerté aux prochains runs ») aiderait | `btn-notifications.png` |
| Cloche pleine de démo | badge « 17 » non lu, tous étiquetés DÉMO à l'intérieur seulement | ✗ badge trompeur (cf. §3) | `btn-notifications.png` |
| Calculette non calculable / négative | « Charge foncière non calculable » (✔) mais aussi « supportable **−69 k€** » (✗ copy) | ~ | `fiche-calculette-verdict.png` |
| Erreur API (liste) | « Erreur de chargement des parcelles. » + réessayer (code `ResultsSection.tsx` l. 378) | ✔ prévu — non simulé (interdit de perturber l'API partagée) | — |

**Pires états vides** : (1) cloche = 17 notifications 100 % démo en vocabulaire matrice ; (2) ANRU muette ; (3) entonnoir sans motifs ; (4) fiche sans adresse (un vide qui ne dit pas son nom).

---

## 8. Fichiers produits

- Scripts (lecture seule, rejouables) : `frontend/qa/audit_m6_dom.mjs`, `audit_m6_boutons.mjs`, `audit_m6_boutons2/3/4.mjs`, `audit_m6_filtres.mjs`, `audit_m6_fiche.mjs`, `audit_m6_fiche2.mjs`, `audit_m6_fiche3.mjs`, `audit_m6_outils.mjs`.
- Données : `reports/m6-audit/dom-inventory.json` (820 éléments), `boutons-cartes*.json`, `filtres-resultats.json`, `fiche-etats.json`, `fiche-extras.json`, `outils-resultats.json`, `legende-dom.json`, `notifications-contenu.txt`, `entonnoir-texte.txt`, `ia-resultat.txt`.
- Captures : `reports/m6-audit/captures/` (≈ 60 PNG : `dom-*.png`, `btn-*.png`, `filtre-*.png`, `fiche-*.png`, `outil-*.png`, `etat-*.png`, `legende-*.png`).
