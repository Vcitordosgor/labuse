# RETOURS-16 — COMPTE-RENDU

Branche `fix/retours-12`, trois commits (carte V1 · permis V2-V4 · recherche V5) + ce compte-rendu.
Captures avant/après : `docs/audit-2026-09/RETOURS-16/captures/` (suffixes `-avant` / `-apres`).
Script de recette : `qa/retours16_shots.mjs` (copie locale dans `frontend/` pour l'exécution).

## Une ligne par travail

- **V1 — la mer partout, sans marches** : FAIT. Mesuré d'abord (reconstruction GetTile z13 côte
  nord) : les rectangles en escalier = la mer PHOTO de l'Ortho Express qui s'arrête par dalles,
  d'un bleu différent de la mosaïque monde qui affleure dessous — deux sources, deux bleus, et le
  blanc no-data mal rogné laissait les liserés. Correctif : **toutes** les sources ortho (Express,
  mosaïque monde, 6 millésimes) passent par le proxy généralisé `api/ortho_proxy.py` (whitelist
  fermée — aucune tuile brute) ; la photo ne garde la mer que sur une **bande côtière** (700 m
  pleine — la grande jetée du Port reste entière —, fondu jusqu'à 1,6 km) ; au-delà, l'**aplat
  unique** `#0A3B59` (bleu mesuré sur la mosaïque monde au large du 974), posé par le **canvas**
  MapLibre sur l'emprise entière — jamais par tuile. Le blanc no-data fond sur 48 px (plus de
  liseré) ; `raster-fade-duration: 0` sur les couches ortho (le crossfade de 300 ms laissait voir
  le canvas aux jointures). La transition suit la **côte**, plus jamais les bords de dalles.
  Recette : 4 cadrages × 2 fonds (île entière · côte nord au large · Saint-Gilles · z16, ortho ET
  Plan IGN), aucune marche visible. Note : le Plan IGN (non-ortho) dessine sa propre mer monde
  entière — il reste en direct.
- **V2 — chip « Autorisé » retiré, puce localisation entière** : FAIT. L'état Sitadel « 2 »
  (Autorisé) devient muet dans la LISTE côté serveur (information constante : Sitadel 974 ne
  publie que des autorisés — elle vit dans la phrase d'explication en tête d'outil) ; la fiche
  permis garde l'état complet, et les états qui varient (« Chantier ouvert », « En cours »,
  « Travaux achevés ») restent servis. La puce de localisation (« approx. (adresse) » / « non
  localisé ») passe **en premier** dans les badges et ne se tronque plus (`whitespace-nowrap` +
  place libérée). Chips constants inventoriés (V2.3) : **le chip type « PC » du mode Dormant**
  (l'endpoint `/promesses` filtre `WHERE type='PC'` en dur → toujours « PC ») — masqué aussi ;
  l'état « Autorisé » (ce mandat). Aucun autre chip constant par construction trouvé (balayage
  Radar/Communes/CRM/fiche).
- **V3 — « Dormant »** : FAIT. Segment, pied de liste, infobulles, registre d'outils (« les permis
  dormants »), fiche commune (ContextePanel « Permis dormants »), source de la fiche commune,
  libellé Copilote (« Permis dormants » ; « permis au point mort » reste un synonyme de routage —
  vocabulaire utilisateur). La définition (« autorisé ancien sans achèvement déclaré (DAACT) »)
  reste dans la phrase d'explication. Aucun export ne portait le terme (vérifié : flash, courrier,
  promo — 0 occurrence).
- **V4 — les compteurs disent ce qu'ils comptent** : FAIT, mesuré d'abord (§ ci-dessous). Le chip
  « Tous » comptait la SOMME de deux fenêtres (21 046 ce jour — le « 21 038 » de Vic) quand le bas
  comptait la base : il compte désormais la **base entière** via `count_only` (COUNT léger, ni
  lignes ni les 47k geoms) ; chaque chip porte son périmètre en infobulle ; le pied nomme tout
  (« 5 580 sur ce filtre (24 derniers mois) · 5 362 localisés · 5 362 sur la carte · données
  jusqu'au 2026-07-31 » ; en Tous « 50 544 en base (toute la profondeur Sitadel) · 47 070
  localisés »). Le « sur la carte » a bien suivi la levée du LIMIT (U2) : 47 070, plus jamais
  8 200. Inventaire des compteurs de l'app : § ci-dessous.
- **V5 — autocomplétion sur toutes les barres** : FAIT — un endpoint, un composant.
  `GET /api/recherche/suggest?q=&types=` (api/recherche.py) : six grammaires typées, aiguillées
  par la **forme** de la saisie, 8 propositions max, index posés au heal du boot. Le composant de
  barre partagé (`AddressAutocomplete`) appelle le suggest à 2 caractères (anti-rebond 200 ms,
  annulation), rend les propositions **groupées par type** (libellé discret à gauche, l'essentiel
  en clair), navigation clavier ↑↓ Entrée Échap, survol vert opaque contenu inversé
  (`bg-mint text-mint-ink`). **Entrée ne devine plus la 1re suggestion** (l'auto-pick d'avant est
  retiré — V5.5) : la frappe reste ce que l'utilisateur a tapé, seule une ligne sélectionnée se
  substitue. Zéro proposition n'est pas muet : « Aucune correspondance pour “xxx” — formats
  acceptés : … » (formats de la barre). Captures : les six grammaires en action + zéro-résultat.

## V1 — coût du proxy, mesuré

Viewport 1440×900 ≈ 35 tuiles. Couche monde (la seule demandée sous z12), séquentiel :

| zoom | à froid (1ʳᵉ visite) | dont tuiles « mer » (404 sans requête IGN) | à chaud (cache disque) |
|---|---|---|---|
| z8 | 1 066 ms | 34/35 à ~0 ms | 2 ms |
| z9 | 1 367 ms | 31/35 | 3 ms |
| z10 | 1 564 ms | 29/35 | 3 ms |

Le coût à froid = les requêtes WMTS IGN des tuiles côtières (~400-550 ms chacune, parallélisées
par le navigateur en pratique) ; les tuiles entièrement au large répondent **404 sans toucher
l'IGN** (test géométrique ~0 ms) — le dézoom est donc PLUS léger qu'avant pour la majorité des
tuiles. **Cache disque posé** (`ortho_proxy_cache_dir`, défaut `.local/ortho-proxy-cache`,
purgeable) : la deuxième visite lit le disque, 2-3 ms le viewport entier. Traitement pixel
(fondu côte + no-data) : ~10-40 ms par tuile côtière, payé une fois.

## V4 — ce que compte chaque chiffre (mesuré le 05/09/2026, base locale)

| Chiffre à l'écran (avant) | Ce qu'il comptait réellement |
|---|---|
| « Récent 5 580 » | permis autorisés dans les **24 derniers mois de données** (ancrés sur la fin du flux Sitadel 2026-07-31), toutes natures, île entière (ou commune filtrée) |
| « Au point mort 15 466 » | PC autorisés depuis **plus de 36 mois**, sans DAACT, parcelle non bâtie, rattachés au run servi |
| « Tous 21 046 » (le « 21 038 » de Vic) | la **somme des deux fenêtres ci-dessus** — PAS le total. Deux jours plus tôt : 21 038 |
| « 50 544 permis » (bas, en Tous) | total base = fenêtre 240 mois ancrée sur 2026-07-31 (la base entière contient 50 545 lignes ; 1 permis antérieur à 2006 sort de la fenêtre) |
| « 8 200 sur la carte » (constat Vic) | l'ANCIEN plafond LIMIT 8000 + points dormants — levé en U2 ; aujourd'hui 47 070 localisés servis |

Après : le chip « Tous » = 50 544 (total en base, `count_only`) ; le pied nomme le périmètre du
filtre actif, les localisés et la date des données (capture `V4-permis-compteurs-*`).

### Inventaire des compteurs de l'app (règle « aucun nombre sans son périmètre »)

Balayage des écrans (hors Permis, traité) — **3 compteurs manquent leur périmètre** :

1. `RadarView.tsx` (~l. 541) — « N biens · M sur la carte » : N = biens **après filtres actifs**
   (commune/type/prix/rattachement), mais rien ne le dit ; « sur la carte » ne dit pas que ce
   sont les seuls **rattachés à une parcelle**.
2. `VeillePromoteurs.tsx` (l. 241) — « N opérations · M logements » sans dire si c'est l'île
   entière ou les filtres actifs (commune/catégorie/depuis).
3. (mineur) `RadarView` : même écran, le compteur de rattachés est ambigu (« sur la carte » vs
   « non localisé » de la liste).

Les autres compteurs contrôlés disent leur périmètre (Communes/acquisitions « N / M chargés
depuis AAAA », Dormants « les N plus anciens chargés », Solaire « N listées (limite 500) sur M
détectées », Surveillance « Parcelles suivies · N », Mon secteur « Ventes : N · 1990-2026 »,
projets « N à explorer »…). Les 3 manques sont **signalés, non corrigés** (hors périmètre V4 —
l'écran Radar a son propre cycle de mandats) ; à reprendre au prochain passage Radar.

## V5 — réponse et index, mesurés

Endpoint mesuré en local (le `ms` serveur voyage dans chaque réponse) :

| saisie | grammaires servies | temps serveur |
|---|---|---|
| `BZ 65` | cadastre (multi-communes : Saint-Denis, Saint-Joseph, Saint-Paul…) | 25 ms |
| `97411000BZ10` | cadastre (préfixe IDU) | 37 ms |
| `428173` | SIREN (préfixe) | 23 ms |
| `sci mirab` | propriétaire | 48 ms |
| `saint-pa` | adresse + commune + propriétaire | 38 ms |
| `50 rue helene` | adresse | 29 ms |

Index posés (heal du boot, `recherche.ensure_index`) : `ix_parcels_section_numero`
(section, numero varchar_pattern_ops — la référence courte passait par un seq-scan de **799 ms**
sur 431k parcelles) et `ix_adresses_suggest_trgm` (GIN trigram sur l'adresse **pliée** en
expression littérale — le LIKE plié coûtait **~290 ms par frappe texte**, c'était le poste
dominant ; `sql_plie_lit`/`plie()` dans constants.py, même pliage des deux côtés, doctrine
M99-B). Tout est sous 50 ms — l'objectif < 150 ms est tenu avec marge.

### Inventaire barre × autocomplétion (V5.4)

| Barre (écran) | Composant | Grammaires proposées | Autocomplétion maison ? |
|---|---|---|---|
| Omnibox (header) | partagé | les six | non (résolution Entrée conservée) |
| ParcelInput (~12 outils : Étudier, Faisabilité, Pièges, Solaire, Remonter le temps, Courrier, Diligence, Étude de zone, Densifier, Mon secteur, Taxe…) | partagé (via AddressAutocomplete) | adresse · cadastre | non (désambiguïsation par candidates à l'Entrée = résolution T1, conservée) |
| Permis (ModulePanel) | partagé | adresse · cadastre · **commune** (pose le filtre) | non |
| Radar (RadarView) | partagé | adresse · cadastre | non |
| Veille promoteurs | partagé | adresse · cadastre | non |
| Scan patrimoine | partagé | propriétaire · SIREN · cadastre · adresse | **liste maison `sug` SUPPRIMÉE** ; `resoudre()` à l'Entrée conservé (résolution, pas suggestion) |
| Radar admin (DepotAgence) | partagé | adresse · cadastre | non |
| Vérif procédure PLU | ParcelInput (depuis R24) | adresse · cadastre | non |
| ZAN (moteurs M17) | — | — | outil **retiré du menu** (composant conservé au dépôt, plus servi) — non rebranché |
| PLU annuaire · CRM · Sources · loupe intra-fiche · admin Flux | champs de **filtrage local plein-texte** (le contenu se filtre à la frappe — pas une recherche de ressource) | hors périmètre, comme au T1 | — |

## Recette

- Suite pytest : **2 336 passed, 1 failed, 37 skipped**. L'unique échec
  (`test_r5_etudier_deux_marges_chacune_dit_son_referentiel`) est PRÉ-EXISTANT (chaîne absente
  dès la base, constaté aux mandats RETOURS-14/15, hors périmètre). Un premier passage avait
  montré 3 échecs supplémentaires (ortho_detection, p_model_dataset, pre_dossier) : **flakiness
  d'ordre** — verts en isolation ET au second passage complet, aucun fichier concerné touché par
  ce mandat. Le verrou `test_omnibox_parcelinput_chemin_unique` (M137) a été MIS À JOUR avec V5 :
  l'aiguillage IDU de la barre vit désormais côté serveur (api/recherche.py) — l'intention « un
  seul foyer par côté » est conservée et vérifiée. Nouveaux : `test_retours16_carte.py` (5) ·
  `test_retours16_permis.py` (6) · `test_retours16_recherche.py` (8).
- vitest : **171 passed** (36 fichiers, omnibox compris). `tsc` : 0 erreur. Build : OK.
- Compteurs de recette mesurés à l'écran (Playwright) : segment « Récent 5 580 · Dormant 15 466 ·
  Tous 50 544 » ; pied « 5 580 sur ce filtre (24 derniers mois) · 5 362 localisés · 5 362 sur la
  carte · données jusqu'au 2026-07-31 » ; « Dormant » ×3 / « point mort » ×0.

## Notes d'exploitation

- Le cache disque du proxy ortho (`LABUSE_ORTHO_PROXY_CACHE_DIR`, défaut `.local/ortho-proxy-cache`)
  est purgeable sans risque : les tuiles se re-fabriquent à la demande.
- Les index du suggest se posent seuls au premier boot (heal « recherche ») — rien à faire au VPS.
- L'ancien chemin `/map/tiles/ortho-express/…` reste servi (alias → couche express) pour les
  fronts en cache navigateur.
