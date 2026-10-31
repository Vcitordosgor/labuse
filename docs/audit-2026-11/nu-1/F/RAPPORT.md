# AUDIT-NU-1 — Lot F : Transversal

**Branche** `audit/nu-1-f` · worktree `~/Desktop/labuse-nu-f` · API `:9100` · front `:6300` · run servi **q_v20** · base locale (= le Mac, pas la prod) · **LECTURE SEULE** (aucune écriture, aucun merge, aucun accès prod ; toutes les requêtes SQL passées avec `default_transaction_read_only=on`).

Date : 2026-10-31. Modèle : Opus. Auteur : audit transversal.

Périmètre tenu : **Projets** (les deux chemins, kanban, parité filtres carte), **CRM**, **Veille** et **Radar** côté interface, **Copilote** écran, **Notifications / cloche**, **Compte / onboarding**, **dashboard admin** (Données, Comptes, IA, Pilotage, Sources), **accessibilité**, **cohérence DA**, **performance** (froid/chaud), **sécurité** (droits admin, routes sans auth, injection, jetons), **textes** (orthographe, accents, cohérence des libellés). Méthode : navigateur réel (Playwright) + API + recalcul SQL indépendant + lecture du code (fichier:ligne) + confrontation aux textes métier.

---

## Cinq chiffres

| | |
|---|---|
| Scénarios joués (écrans × parcelles × froid/chaud, navigateur + API) | **~60** |
| **Bloquants** | **3** |
| **Majeurs** | **21** |
| **Mineurs** | **21** |
| **Dettes** | **9** |

Console navigateur : **0 erreur / 0 avertissement** sur tout le parcours Lot F (Carte → Radar → fiche bien → Projets → wizard → CRM). Les blessures ne sont pas des plantages : elles sont dans l'**assemblage** (un même chiffre qui vit à deux endroits et diverge), dans le **discours** (un écran qui jure « rien d'autre » alors qu'il fait autre chose), dans la **latence à froid** (Pilotage 88 s, Sources 15 s) et dans une **SSRF** authentifiée.

Requêtes > 2 s relevées (froid) : `GET /admin/pilotage` **88,4 s** · `GET /sources` **14,8 s** (→ 6,5 → 0,8 s à chaud) · `GET /radar/biens` 1,7 s · `GET /pipeline` 1,2 s. Tout le reste < 1 s.

---

## Les 5 trouvailles les plus graves (détail plus bas)

1. **NU-F-001** (bloquant) — Radar : le **même** « prix acté médian maisons » d'une commune vaut **4 030 €/m²** dans « Ce bien » et **3 750 €/m²** dans le tableau du marché, **sur le même écran** ; l'écart de négociation affiché (−51,9 %) est calculé sur le chiffre que l'écran ne montre jamais.
2. **NU-F-002** (bloquant) — Copilote : le code interne du **tier de scoring** (`sans_signal`, `a_creuser`, `reserve_fonciere`, `declasse_*`) fuit tel quel dans la réponse au client via l'outil fiche (clé de lecture erronée).
3. **NU-F-003** (bloquant) — Projets : « Partir d'une sélection filtrée » jure « **les mêmes filtres que la carte — rien d'autre** », mais le wizard **exclut l'étage 0** et n'offre que **4 des ~11 familles** de filtres de la carte → il compte 12 à 35 % de parcelles en moins pour le même cadrage.
4. **NU-F-004** (majeur) — Sécurité : **SSRF** authentifiée via « Analyser une annonce » (`?url=`) — aucune liste blanche d'hôte, redirections suivies ; oracle de ports internes pour tout client à 349 €.
5. **NU-F-005** (majeur) — Performance : `GET /admin/pilotage` (onglet Pilotage) bloque **88 s à froid** sur un appel réseau Stripe **synchrone** dans le thread de requête.

**Ce que je changerais en premier** : NU-F-001 et NU-F-002 — un chiffre faux et un code interne qui fuit, tous deux lus par un client qui décide d'un achat. Puis NU-F-004 (une ligne de validation d'hôte ferme les trois routes SSRF d'un coup).

---

# Trouvailles

Convention : gravité · **où** · reproduction · **affiché vs juste** (avec recalcul) · cause `fichier:ligne` · **proposition** (2 phrases).

## BLOQUANTS

### NU-F-001 · BLOQUANT · Radar — deux médianes « acté maisons » contradictoires sur le même écran
- **Où** : écran Radar, colonne droite. Bloc « Ce bien » vs tableau « Le marché · Par type de bien », même commune. Capture : `captures/NU-F-radar-double-mediane.png`.
- **Repro** : Radar → ouvrir le marché → cliquer une maison de L'Étang-Salé (ex. « Lambert », 219 000 €, `bien_id=428`). Le panneau marché bascule sur « L'Étang-Salé ».
- **Affiché vs juste** : « Ce bien · Écart · L'Étang-Salé · maisons · **vs acté −51,9 %** » ← médiane acté **4 030 €/m² (n=59)** servie par `GET /radar/biens/428/vs-marche`. Le tableau du même écran affiche « Maison · ACTÉ €/M² (DVF) = **3 750** (n=351, 2021–2025) » via `GET /radar/marche-tableau`. **Recalcul DVF** (mes requêtes) : la population « 12 mois glissants, bâti ≥ 20 m² » donne ~4 030 (n≈59) ; la population « toutes années, bornes 100–12 000 » donne 3 750 (n=351). Les deux reproduisent. Le client lit un rabais de −51,9 % contre une référence **jamais montrée** ; la référence montrée (3 750) donnerait −48,3 %.
- **Cause** : deux moteurs pour un seul libellé. « Ce bien » = `marche.bien_vs_marche` → `_median_bati_commune` (fenêtre 12 mois glissants) `src/labuse/pige/marche.py:336-346` ; le tableau = `_dvf_bati_type` (toutes années) `src/labuse/signaux.py:220-230`. RECETTE-4 a recâblé « Ce bien » sans recâbler le tableau.
- **Proposition** : les deux panneaux d'un même écran doivent lire **une** médiane acté par (commune, type) ; alignez `bien_vs_marche.acte` sur `_dvf_bati_type` (ou l'inverse) et étiquetez la fenêtre (« DVF 2021–2025 » vs « DVF 12 mois ») pour que le chiffre voyage avec son périmètre.

### NU-F-002 · BLOQUANT · Copilote — le code interne du tier de scoring fuit au client
- **Où** : Copilote, chemin outil `fiche_parcelle`. `src/labuse/copilote_v2/outils.py:359`, re-surfacé dans la substance « sans outil » et les faits PREPARER `src/labuse/copilote_v2/answering.py:1835`.
- **Repro** : demander au Copilote de résumer une parcelle (ex. `97417000AO0113`, tier `sans_signal`). La réponse peut rendre littéralement « verdict LABUSE : sans_signal ».
- **Affiché vs juste** : le dict `score_v2` servi par l'API (`app.py:4489-4501`) expose `tier`, `rang`, **`label`**, `motif` — **jamais** `verdict` ni `libelle`. Or `outils.py:359` lit `sv2.get("verdict") or sv2.get("libelle") or sv2.get("tier")` → les deux premiers sont `None` → il retombe **toujours** sur `tier` = le code de classement brut (`a_creuser`, `reserve_fonciere`, `ecartee`, `sans_signal`, `declasse_*`). Le garde anti-invention ne vérifie que les nombres (`answering.py:299-311`), jamais les chaînes → le modèle le répète tel quel. **Juste** = le mot client traduit `label` (ici « Sans signal »).
- **Cause** : noms de clés erronés à `outils.py:359` (outil écrit contre une forme de `score_v2` qui n'existe pas). Viole la règle Vic « jamais de code brut » + « le scoring ne s'affiche que là où le client l'a demandé ».
- **Proposition** : lire `sv2.get("label")` et supprimer le repli `verdict`/`libelle`/`tier`. Une ligne ferme les deux chemins (formuler + substance/PREPARER).

### NU-F-003 · BLOQUANT · Projets — « les mêmes filtres que la carte — rien d'autre » est faux
- **Où** : Projets → « Nouveau projet » → « Partir d'une sélection filtrée ». Promesse à l'écran `frontend/src/components/projets/ParcoursProjet.tsx:153` (« Les mêmes filtres que le panneau Filtre de la carte, appliqués à la base — **rien d'autre** »). Capture : `captures/NU-F-projets-liste.png`.
- **Repro / recalcul** (API `:9100`, run q_v20) :
  - `POST /projets/apercu` sur un cadrage rend `{"n":3355,"total":4195}` — **l'aperçu avoue lui-même** un écart de 20 % entre « triables » (n) et « total ».
  - Côté carte, `GET /filtre` d'un cadrage {Saint-Denis, nu, pm_privée} rend `total=433` (bandes A30·B73·C124·D166·**0=22·NC=2**) ; le wizard du même cadrage rend ~381 (l'étage 0 et le plancher de surface retirés). Écart systématique 12–35 % selon le cadrage.
- **Affiché vs juste** : (a) le compteur exclut l'étage 0 — `_cadrage_total` ajoute `AND NOT {_ETAGE0_SQL}` `src/labuse/api/projets.py:293-294` et `:348-349`, plus le plancher `MIN_DISPLAY_SURFACE_M2` ; la carte, elle, **compte** ces parcelles (bandes 0/NC). (b) Le cadrage n'offre que **Surface, Zonage, État du sol, Signaux** (`FiltreFacettes.tsx`), alors que la carte (`FiltreLabuse.tsx`) ajoute Copropriété, Hauteur LiDAR, Emprise/Saturé, ZFANG, FRR et toute la section Propriétaire (Particulier/Société, SIREN, Forme juridique, APE, dirigeants) — pourtant toutes mappées côté backend (`projets.py:_CADRAGE_MAP`). Le promoteur qui a ciblé « SCI, dirigeant ≥ 70 ans, sans copro » sur la carte **ne peut pas** reproduire ce cadrage ; son projet est plus large que sa recherche.
- **Cause** : `FiltreFacettes` est un sous-ensemble codé en dur (le commentaire prétend « les facettes de la carte réutilisées telles quelles » — faux) ; l'exclusion étage 0 est voulue pour le tri mais contredite par la phrase « rien d'autre ».
- **Proposition** : soit afficher le vrai total carte (et expliciter « 433 correspondent · 381 triables »), soit faire rendre à `FiltreFacettes` les mêmes sections que `FiltreLabuse` ; dans tous les cas, retirer « rien d'autre » tant que ce n'est pas vrai.

## MAJEURS

### NU-F-004 · MAJEUR · Sécurité — SSRF authentifiée via « Analyser une annonce »
- **Où** : `POST /radar/annonce/analyser` et `GET /analyse-annonce.pdf?url=` (`src/labuse/pige/api.py:1384`, `src/labuse/api/documents.py:279-288`) ; primitive `_fetch_page_oneshot` `pige/api.py:1090` (`requests.get(url, timeout=8, allow_redirects=True)`).
- **Repro** (tout client connecté — routes derrière le garde global, pas admin) : la validation est `_URL_RE.match(url)` (`^\s*https?://`, `pige/api.py:1079`) + un test de sous-chaîne `"leboncoin." not in url`. Aucune ne restreint l'hôte. `http://169.254.169.254/latest/meta-data/?leboncoin.` passe ; `http://leboncoin.attacker.com/` passe ; un `302` depuis `http://attacker/leboncoin.` vers `http://127.0.0.1:…` est suivi. (Je n'ai **pas** tiré de requête vers un hôte interne ; preuve par le code.)
- **Affiché vs juste** : les codes d'erreur distincts (`url_bloquee` sur 401/403/429, `url_illisible` sinon, « le portail n'a pas répondu » sur échec connexion) forment un **oracle fiable** de ports/hôtes internes. Juste = liste blanche d'hôtes exacts + rejet des IP privées + `allow_redirects=False`.
- **Cause** : `pige/api.py:1079-1090` — validation de schéma seulement, jamais d'hôte ; redirections suivies.
- **Proposition** : dans `_fetch_page_oneshot`, `urlparse(...).hostname` ∈ {`www.leboncoin.fr`, `www.bienici.com`}, résoudre et bloquer RFC-1918/loopback/link-local, couper les redirections. Un seul point ferme les trois routes (dont NU-F-006).

### NU-F-005 · MAJEUR · Performance — onglet Pilotage : 88 s à froid (Stripe synchrone)
- **Où** : `GET /admin/pilotage` → `stripe_lecture.apercu()` `src/labuse/api/dashboard.py:398`, `src/labuse/stripe_lecture.py:129-145`.
- **Repro / mesure** : `curl` à froid = **88,4 s** (HTTP 200, 15,6 Ko) ; re-mesure immédiate < 1 s (cache 5 min). La page admin Pilotage attend donc 88 s au premier chargement de la journée.
- **Affiché vs juste** : `apercu()` fait `client.subscriptions.list(expand=[customer,latest_invoice]).auto_paging_iter()` + `invoices.list()` — appels réseau **synchrones** vers Stripe dans le thread de requête (`stripe_lecture.py:58-86`). Juste = lecture asynchrone/hors requête, ou cache servi immédiatement + rafraîchissement en tâche de fond.
- **Cause** : appel bloquant non borné dans le handler (même famille que l'incident étude/GIL ETUDE-ASYNC-1) ; le `timeout` HTTP Stripe n'est pas plafonné court.
- **Proposition** : servir le dernier cache tout de suite et rafraîchir Stripe dans un worker (ou borne `StripeClient(..., timeout=5)` + réponse « lecture Stripe en cours »). Ne jamais tenir le thread de requête 88 s.

### NU-F-006 · MAJEUR · Performance — onglet Sources : 14,8 s à froid
- **Où** : `GET /sources` (page Sources / catalogue).
- **Repro / mesure** : froid **14,8 s** → 6,5 s → 0,8 s (chaud). I/O disque sur la base de 44 Go (buffers froids) + agrégation du catalogue non pré-calculée.
- **Proposition** : pré-calculer/mettre en cache l'état du catalogue (il change rarement) et servir une réponse < 1 s ; sinon afficher les trois points verts et charger en différé. (cf. VITESSE-3, plancher disque.)

### NU-F-007 · MAJEUR · Sécurité — SSRF « dépôt agence » sans aucun contrôle d'hôte (latent)
- **Où** : `POST /admin/radar/depot-agence/analyser` `src/labuse/pige/api.py:1156` ; validation `:1163` = `_URL_RE.match(src)` seul (même pas le test `leboncoin.`).
- **Repro** : garde `_depot_admin_ou_ouvert` = admin **ou** tout client si `radar_depot_agence_actif` (défaut `False`, `config.py:95`). Admin-seul aujourd'hui ; dès que le drapeau s'ouvre aux clients (prévu), SSRF sans aucune restriction.
- **Proposition** : même durcissement `_fetch_page_oneshot` (NU-F-004) ; ne pas ouvrir le drapeau avant.

### NU-F-008 · MAJEUR · CRM — fonctionnalité « Étiquette de contact » morte, le compteur Pilotage ment
- **Où** : backend vivant (`app.py:9328-9337` constantes, `:9481-9495` PATCH écrit `contact_etiquette` + INSERT `contact_etiquette_log`, `:9369` meta sert 8 libellés) ; **aucune UI** ne pose l'étiquette (Kanban/fiche ne patchent que `status`/`prospection`).
- **Affiché vs juste** : `contact_etiquette_log` = 2 lignes (recalcul SQL), `compte_id` NULL partout → le compteur Pilotage « étiquettes/semaine » (`dashboard.py:444-451`) est **structurellement ~0**. Le `DeplacerMenu` a remplacé le sélecteur d'étiquette sans retirer le chemin backend.
- **Cause** : feature SCORING-3 L5 superseded ; meta/PATCH/log/types TS laissés vivants.
- **Proposition** : ressusciter un sélecteur sur la carte, ou retirer meta/PATCH/log + types TS. Un journal écrit sans producteur est un piège et fait mentir le Pilotage.

### NU-F-009 · MAJEUR · CRM — compteur de colonne à double source : colonne « vide » indéboulonnable
- **Où** : garde de suppression `src/labuse/api/crm_columns.py:170-173` (`_cards_in` compte **tout**, y compris archivé) vs compteur affiché `src/labuse/registre/moteurs/plateforme.py:131-142` (`archived_at IS NULL`). Dialogue `frontend/src/components/crm/Kanban.tsx:190,196-213`.
- **Repro** (données réelles pilote) : la colonne `chaud` a 0 actif + 1 archivé. Personnaliser → ✕ : le front dit « Cette colonne est vide — suppression immédiate » et envoie `move_to:null` ; le backend `_cards_in('chaud')=1` → 422 → toast générique « Action sur la colonne échouée — réessayez ». Colonne **jamais supprimable**, sans raison affichée.
- **Cause** : `_cards_in` n'a jamais reçu le filtre `archived_at IS NULL` posé ailleurs (PROJETS-CRM-FIX-1).
- **Proposition** : ajouter `AND archived_at IS NULL` à `_cards_in` (crm_columns.py:172) pour aligner la garde sur la sémantique affichée.

### NU-F-010 · MAJEUR · CRM — le dialogue de suppression lit un compteur filtré par la recherche
- **Où** : `frontend/src/components/crm/Kanban.tsx:474-475` (`byCol`/`cardCount` filtrés par l'omnibox), `:190,196` (le dialogue lit `withCounts[idx].cards`).
- **Repro** : taper une recherche qui masque toutes les cartes d'une colonne peuplée → ✕ → dialogue « 0 carte · suppression immédiate » + `move_to:null` → backend rejette (422) → toast « réessayez ». La cible de déplacement pré-sélectionnée reflète aussi le sous-ensemble filtré.
- **Cause** : le front recalcule les compteurs client-side (recherche incluse) au lieu d'appeler `GET /pipeline/columns` (qui sert le vrai `cards`, mais n'est jamais appelé → moteur registre mort, cf. dette).
- **Proposition** : alimenter le dialogue avec le compteur **non filtré** (appel `GET /pipeline/columns` ou `byCol` sans prédicat de recherche pour le dialogue).

### NU-F-011 · MAJEUR · Projets — le kanban contredit le discours du wizard
- **Où** : `frontend/src/components/projets/ProjetKanban.tsx:330-335,349-354` : « **LABUSE a analysé** N parcelles … classées par **probabilité de mutation** » — alors que `ParcoursProjet.tsx:189-191` jure que ce chemin « ne parle plus d'analyse LABUSE ni de probabilité de mutation ».
- **Affiché vs juste** : l'utilisateur crée via « sélection filtrée » (pas d'analyse, promis) puis ouvre le projet et lit « LABUSE a analysé… ». Le même fait (« ce qu'est ce parcours ») vit en deux endroits qui se contredisent. L'analyse par tier `priorite`/`a_suivre` est bien calculée (`projets.py:1003-1034`).
- **Proposition** : retirer le bandeau d'analyse + le langage probabiliste du kanban de ce chemin (ou l'aligner). Un seul discours par parcours.

### NU-F-012 · MAJEUR · Projets — compteur de la liste périmé jusqu'à la première ouverture
- **Où** : `src/labuse/api/projets.py:622-658` (`proposee = max(0, cadrage_total_cache − décidées)`). Cache recalculé seulement à create/rejeu/patch/ouverture (`:400-409,1166-1169`).
- **Repro mesuré** : projet avec `cadrage_total` caché = 412, relecture fraîche = 381 ; la liste affiche 399 (412−13), l'ouverture recalcule et affiche 368 (381−13) — écart 31, jusqu'à la 1re ouverture qui « répare » le cache. Le run a changé (q_v19→q_v20) sans invalider le cache.
- **Cause** : le cache `cadrage_total` survit à la bascule de run.
- **Proposition** : inclure le run servi dans la validité du cache (recalcul si `cadrage_total_at` < promotion du run), ou invalider tous les caches projets à la bascule.

### NU-F-013 · MAJEUR · Projets — table figée (≤ 200) vs compteur vif : « à trier » a deux sens
- **Où** : `_figer_shortlist` écrit ≤ 200 lignes `proposee` dans `projet_parcelles` (`projets.py:672-744`) ; l'affichage « à trier » vient du vif `_cadrage_total − décidées` (`:1170,1266`) ; l'export CSV/PDF sert la table **figée**.
- **Repro mesuré** : un projet a 187 lignes `proposee` physiques mais l'écran dit « 368 à trier » ; la pagination kanban feuillette un vivier vif (381) via `_cadrage_page_idus` → au-delà de la page 1, les parcelles affichées ne sont pas les figées. L'export ne voit que 187. Deux populations sous un mot.
- **Proposition** : clarifier figé (export, daté) vs vif (tri live), ou aligner la source ; dire le plafond 200 quand le vivier le dépasse (déjà fait dans `FiltreFacettes:91`, absent du kanban).

### NU-F-014 · MAJEUR · Radar — « En vente depuis N j » calculé dans deux fuseaux (off-by-one)
- **Où** : carte liste `RadarEcran.tsx:30-42,100,107` (JS `Date.now()`, fuseau OS = CEST) vs bloc « Ce bien » `marche.py:316-318` (`now() AT TIME ZONE 'Indian/Reunion'`).
- **Affiché vs juste** : bien 293 backend `anciennete_j=41` ; le front parse `"2026-09-20"` comme minuit UTC et soustrait un `Date.now()` parisien → 40 **ou** 41 selon l'heure. Les deux nombres du même bien diffèrent de 1 près de la frontière de jour (le décalage Paris↔Réunion garantit une fenêtre de désaccord).
- **Cause** : arithmétique de jours dupliquée en deux fuseaux ; champ de repli différent (`date_saisie` front vs `date_premiere_saisie` back).
- **Proposition** : servir `anciennete_j` (Réunion) sur le payload liste aussi et ne laisser au front que l'affichage ; supprimer `joursDepuis` côté front.

### NU-F-015 · MAJEUR · Radar — compteur d'alerte : la valeur, son libellé et l'état vide sur trois fenêtres différentes
- **Où** : `frontend/src/components/radar/VeilleEcrans.tsx:291-295` ; backend `pige/veille.py:110-126` + `digests.py`.
- **Affiché vs juste** : `a.nouveaux` = biens vus pour la 1re fois **depuis hier 00:00 Réunion** (`veille.py:116-118`). Or le libellé non-nul dit « N annonces **depuis votre dernier passage** » (il n'existe **aucun** suivi de dernière visite) et l'état vide dit « **Rien cette semaine** » (7 jours) pour un compte d'1 jour. Deux sémantiques temporelles fausses autour d'un nombre d'un jour.
- **Proposition** : aligner le texte sur la vraie fenêtre (« depuis hier » / « Rien depuis hier »), ou implémenter un vrai suivi de dernière visite. Ne pas vendre « cette semaine » / « dernier passage » sur un compte « depuis hier ».

### NU-F-016 · MAJEUR · Radar — « fenêtres 30 j / 90 j comptées à partir de la dernière collecte » : faux
- **Où** : `frontend/src/components/radar/RadarMarche.tsx:60,71-77` affiche « Dernière collecte : {date} — les fenêtres 30 j/90 j se comptent à partir de cette date » ; backend `marche._AGG` `marche.py:33-47` et `tableau` `:240-251`.
- **Affiché vs juste** : `nouvelles_30j`/`vendues_90j` = `date_premiere_saisie >= (now() AT TIME ZONE 'Indian/Reunion')::date − N` → comptées **depuis aujourd'hui**, pas depuis la capture. DB : dernière capture 2026-10-27, aujourd'hui 2026-10-31, **écart 4 j** → la fenêtre « 30 j » finit aujourd'hui, pas le 27/10. Si l'extension cale, la base annoncée dérive.
- **Proposition** : ancrer la SQL sur `derniere_capture_at`, **ou** corriger la phrase en « comptées jusqu'à aujourd'hui ». Ne pas annoncer une base que la requête n'utilise pas.

### NU-F-017 · MAJEUR · Notifications — brief du matin : « Rien de nouveau » affiché alors qu'il y a des événements
- **Où** : `src/labuse/api/events.py:1249-1250` : `n_evenements = somme(groupes) + permis_hier` mais `vide = (len(veilles)==0 and permis_hier==0)` — **ignore `groupes`**.
- **Affiché vs juste** : un client avec un événement `parcelle_suivie` (vente DVF) dans les 24 h mais sans ligne `veille` ni `permis_hier` obtient `n_evenements>0` **et** `vide=True` → texte « Rien de nouveau sur vos secteurs depuis hier » qui contredit le compte. `parcelle_suivie` est l'événement perso dominant → ça se déclenche en pratique.
- **Proposition** : `vide = (n_evenements == 0)`.

### NU-F-018 · MAJEUR · Notifications — liens des mails morts (base_url localhost/vide)
- **Où** : `GET /readyz` → `mail_liens:{base_url:"http://127.0.0.1:8000", ok:false, avert:"… aucun client ne pourra cliquer"}` ; `events.py:1437`, `emails.py:187`, `digests.py:55,482`.
- **Affiché vs juste** : quand `base_url` est vide/localhost, l'en-tête `List-Unsubscribe` (RFC-8058) devient relatif (désabo un-clic cassé) et `digest_html_email` ne rend **aucun** lien profond. Dépend entièrement du réglage `public_base_url` en prod. (Config prod, mais le périmètre « mail » est touché.)
- **Proposition** : fail-closed — refuser d'enfiler/envoyer un digest tant que `base_url_probleme()` est posé ; exiger un base_url public absolu avant tout lien.

### NU-F-019 · MAJEUR · DA — zone Projets codée à la main, hex de marque en dur (verrou charte)
- **Où** : `frontend/src/components/projets/ProjetsPanel.tsx`, `ParcoursProjet.tsx` : tout en `style={{…}}` inline + hex littéraux `#060A08 #0C1410 #ECF5EF … ` et surtout **`#4ADE80`** (le mint de marque, `ProjetsPanel:91/97`, `ParcoursProjet:22`). `config/brand_colors.json` interdit tout hex de marque en dur (verrou `tests/test_brand_colors.py`). Inputs hauts de 44–52 px (`ParcoursProjet:172-184`), pas la charte 32 px ; boutons `<button style>` au lieu de `Bouton`.
- **Proposition** : remplacer le mint par le token/classe `mint`, les gris par `bg/surface/txt`, les boutons par `Bouton` (32 px/r6), un input charte partagé.

### NU-F-020 · MAJEUR · DA — Radar/Veille : `<select>` natifs et pastilles maison au lieu de `Select`/`Badge`/`Chip`
- **Où** : `radar/RadarEcran.tsx:138,148,164,168-177` (input/select natifs), `:94-101` pastilles « Nouveau / Baisse / En vente » en `<span rounded-full bg-mint/12>` (opacité `/12` hors charte), `:103` hex `#E7B008` en dur ; `radar/VeilleEcrans.tsx:338,370,383,85-90,365-368` (mêmes). `Select`/`Badge`/`Chip` (ui) existent précisément pour ça.
- **Proposition** : `Select` pour les menus, `Badge` pour les pastilles de statut, `Chip` (avec `aria-pressed`) pour les fréquences, tokens `amber`/`mint` au lieu des hex/opacités.

### NU-F-021 · MAJEUR · Textes — espace insécable manquante avant €/%/m² sur des écrans clients
- **Où** : les helpers canoniques `lib/format.ts` utilisent l'insécable, mais plusieurs écrans **redéfinissent et masquent** `fmtEur`/`fmt`/`pct` avec une espace normale : `radar/RadarEcran.tsx:25,97`, `radar/RadarMarcheColonne.tsx:15-16,146`, `radar/VeilleEcrans.tsx:210-211`, `projets/ProjetKanban.tsx:201-202,366`. **Vu à l'écran** : le marché Radar affiche « **3 038€/m²** » (aucune espace du tout avant €).
- **Affiché vs juste** : `245 000 €` / `74 %` / `1 245 m²` avec U+00A0. 
- **Proposition** : supprimer les `fmtEur`/`fmt`/`pct` locaux et importer ceux de `lib/format` ; composer `€/m²` sur `fmtEur` pour hériter de l'insécable.

### NU-F-022 · MAJEUR · A11y — rangées de projet / « voir plus » non atteignables au clavier ; champs sans label
- **Où** : `projets/ProjetsPanel.tsx:69` `<div onClick=ouvrir>` et `:302` `<div onClick>` « VOIR 200 DE PLUS » — pas de `role`/`tabIndex`/`onKeyDown` (le clavier ne peut pas ouvrir un projet ; contraste : Veille `LigneParcelle` le fait bien). Champs placeholder-seul : `copilote/AccueilCopilote.tsx:193` (textarea principale), `projets/ParcoursProjet.tsx:171,173,221,250` (**vu à l'écran** : input « Ex. Nouveau projet » sans label), `header/Header.tsx:558-560,747`, `sources/SourcesPage.tsx:154`.
- **Proposition** : `<button>` ou `role="button" tabIndex=0 onKeyDown` (Enter/Espace) sur les div cliquables ; `aria-label` sur chaque champ placeholder-seul (WCAG 1.3.1/3.3.2).

### NU-F-050 · MAJEUR · Admin (L'usine) — un automate quotidien gelé peint « au vert »
- **Où** : onglet « L'usine » + tuiles « Est-ce que tout tourne ? ». `src/labuse/cockpit_resume.py:33-44` (`_pastille_job`), `:517-530` (`_pastille_poste`).
- **Repro / recalcul** : `GET /admin/usine` → pastille `purge-sessions` = **vert**. DB `job_runs` : dernier `ok` de `purge-sessions` = **2026-10-20 (il y a 11 j)**, cadence *quotidien*. La règle `ops_alertes._jobs_en_retard` (`:311`, > 1,5× cadence) classe ce job en **retard** — et le Tableau de bord le passe d'ailleurs en rouge (cohérence inter-onglets cassée, cf. NU-F-051).
- **Affiché vs juste** : affiché « au vert » ; juste = ambre/rouge. La pastille ne regarde que le `statut` du dernier run, jamais la fraîcheur vs `cadence`/`prochaine_reunion` (pourtant servies par `jobs.liste()` `:342-344`). Un automate quotidien mort depuis 11 j passe pour sain — l'écran « est-ce que ça tourne ? » ment.
- **Proposition** : après `statut == ok`, comparer `dernier.fin` à la cadence (réutiliser la règle 1,5× de `_jobs_en_retard`) et rendre ambre/rouge si périmé. Un seul prédicat de fraîcheur, partagé.

### NU-F-051 · MAJEUR · Admin (Tableau de bord) — des incidents périmés affichés comme alarmes rouges vivantes
- **Où** : cartes « aujourd'hui ». `src/labuse/api/dashboard.py:2924-2929`, `cockpit_resume.py:152-181` (`_cartes_incidents`).
- **Repro** : `GET /admin/circuit` → cartes rouges « L'app n'est pas prête à répondre » (readyz) et « La sauvegarde ne tourne plus ». Or en direct : `GET /readyz` → **200 `ready:true`** ; `GET /admin/sante-endpoints` → tout vert. Les `ops_incidents` concernés datent du **2026-10-29 01:15** et ne se ferment qu'au prochain `verifier_tout` (dont le job porteur est gris → jamais rejoué localement).
- **Affiché vs juste** : affiché « app pas prête » (rouge, présent) ; juste = app prête (readyz 200). L'âge « ouvert depuis » est caché dans « Voir le détail » → un incident vieux de 2 j se lit comme « maintenant », et l'admin voit deux onglets se contredire. *Caveat : la péremption vient en partie du fait que la passe de monitoring n'a pas rejoué en local ; le défaut de conception (carte sans signal de fraîcheur, contradiction inter-onglets) tiendrait aussi en prod si la passe prend du retard.*
- **Proposition** : exiger une passe `verifier_tout` fraîche avant de faire confiance à `incidents_ouverts`, ou horodater chaque carte et dégrader visuellement les incidents plus vieux que la dernière passe.

## MINEURS

### NU-F-023 · MINEUR · Compte — `/moi` expose `role` / `statut_compte` inutilisés
- `src/labuse/api/onboarding.py:849-856` : la réponse inclut `role`/`statut_compte` (valeurs **du caller**, pas d'un autre compte — pas d'IDOR) jamais lues par le front. Surface client élargie pour rien. **Proposition** : retirer, ou servir un booléen `paiement_requis`.

### NU-F-024 · MINEUR · Compte — TTL d'enrôlement 2FA trop court (300 s)
- `src/labuse/api/auth.py:34` `DEFI_2FA_TTL_S=300`. Scanner le QR + saisir le code au-delà de 5 min → bounce silencieux vers `/login`. Récupérable (même secret re-servi) donc mineur. **Proposition** : 900 s à l'enrôlement.

### NU-F-025 · MINEUR · Notifications — `/events/count` ≠ `/events` sur les types mis en sourdine
- `events.py:781-782` : `events_count` appelle `notifications_non_lues` **sans** `cloche_filter_sql`, alors que `list_events` passe `cf` (filtre prefs). Un client qui coupe la cloche d'un type voit ces lignes exclues de la liste mais **comptées** par le badge → pastille indélébile. **Proposition** : passer le même `cf` à `notifications_non_lues`.

### NU-F-026 · MINEUR · Copilote — le payload `resume_fiche` expose des IDs de champ internes
- `GET /api/copilote-v2/ask` renvoie `"id":"surface_parcelle_m2"`, `"id":"pente_deg"` dans `resume_fiche.tuiles/sections` (non rendus, mais visibles dans le corps JSON). **Proposition** : ne pas sérialiser les ids de registre vers le client.

### NU-F-027 · MINEUR · Copilote — tolérance anti-invention ±1 et chiffres source/millésime
- `answering.py:308` `abs(n-a)<=1` laisse passer un entier off-by-one (« 10 mois » pour 9) ; `:291-292` verse `source`/`millesime` dans les nombres autorisés (« q_v20 »/« 2025 » rendent 20/2025 dicibles). **Proposition** : tolérance 0 sur les entiers ; ne pas autoriser les chiffres de métadonnées.

### NU-F-028 · MINEUR · CRM — le message d'erreur d'étiquette fuit les clés internes
- `app.py:9487-9488` : `f"(attendu : {', '.join(CONTACT_ETIQUETTES)})"` joint les **clés** snake_case (`contacte, pas_de_reponse, …`) au lieu des libellés. **Proposition** : joindre `.values()`.

### NU-F-029 · MINEUR · CRM — `priority` éditable mais jamais affiché sur la carte
- `Kanban.tsx:266-269` l'édite, `app.py:9217` le sert ; le rendu de carte ne l'affiche jamais → ne peut pas trier. **Proposition** : afficher une pastille, ou retirer le contrôle.

### NU-F-030 · MINEUR · CRM — champs servis mais non rendus (`proprietaire_label`, `has_manual_contact`)
- `app.py:9234-9235` les servent par carte, rien ne les rend. Payload mort. **Proposition** : retirer du payload.

### NU-F-031 · MINEUR · Sécurité — `/version` divulgue `env`
- `GET /version` renvoie `{"env":"local", par:…}` à tout utilisateur authentifié. Info mineure. **Proposition** : retirer `env`/`par` du payload client ou le gater admin.

### NU-F-032 · MINEUR · Radar — date de relevé affichée ici, masquée là, par politique
- `RadarMarcheColonne.tsx:199-206` retire la date de relevé (« décision Vic 18/09 ») ; `RadarMarche.tsx:71-77` l'affiche. Même payload `derniere_capture_at`, traitement incohérent. **Proposition** : une seule politique.

### NU-F-033 · MINEUR · Radar — sous-titre Veille mélange une fenêtre 7 j et 1 j
- `VeilleEcrans.tsx:54` : `nEvenements = suivis(nouveau, 7 j) + alertes(nouveaux, depuis hier)` sous un seul « depuis votre dernier passage ». **Proposition** : une fenêtre unique, ou séparer suivis (semaine) et alertes (hier).

### NU-F-034 · MINEUR · Textes — « Archivées » sur « projet » (masculin)
- `projets/ProjetsPanel.tsx:233` chip « Archivées » (**vu à l'écran** à côté de « Actifs »). Un projet est masculin → « Archivés ». **Proposition** : corriger.

### NU-F-035 · MINEUR · Textes — formateurs monétaires admin hors `lib/format`
- `admin/Licences.tsx:29`, `admin/Radar.tsx:21`, `admin/Ia.tsx:13,17` : `${v.toFixed(2).replace('.',',')} €` (espace normale, pas de groupement des milliers). Admin-only. **Proposition** : router par `lib/format`.

### NU-F-036 · MINEUR · Textes — verbe de retrait incohérent
- « Retirer du CRM » (`DeplacerMenu:26`) vs « Ne plus suivre » (`VeilleEcrans:192`) vs « Écarter » (tri). Surfaces différentes mais à cartographier délibérément. **Proposition** : un verbe par concept.

### NU-F-037 · MINEUR · DA — contrôle segmenté dupliqué + opacité hors charte
- `Segment` copié-collé dans `RadarEcran.tsx:201-215` et `VeilleEcrans.tsx:400-414`, actif en `bg-mint/12`. **Proposition** : un composant partagé, actif via token charte.

### NU-F-038 · MINEUR · DA — boutons icône sous-32 px dans Veille
- `VeilleEcrans.tsx:194` (retirer) et `:269` (menu ⋯) en `h-7 w-7` (28 px). Charte = 32×32 (`Bouton icone`). **Proposition** : `Bouton icone` / `h-8 w-8`.

### NU-F-039 · MINEUR · A11y — statut de notification par couleur seule
- `Header.tsx:335,481` : lu/non-lu par pastille ambre vs grise, sans texte/aria (WCAG 1.4.1). **Proposition** : `aria-label` (« non lue » / « N non lues »).

### NU-F-040 · MINEUR · A11y — alt d'image générique
- `Header.tsx:545` `<img alt="logo">`. **Proposition** : `alt=""` si décoratif (comme `Rail.tsx:187`), sinon décrire.

### NU-F-041 · MINEUR · A11y / DA — bouton « Envoyer » du Copilote codé à la main
- `copilote/AccueilCopilote.tsx:194` `bg-cp-ia px-5 py-2.5` (~38 px, pas `Bouton`). **Proposition** : `Bouton ton="ia"`.

### NU-F-052 · MINEUR · Admin (Textes) — carte agrammaticale « Les un cache sont en retard »
- **Où** : carte cache du Tableau de bord. `cockpit_resume.py:88-98` (`_CACHE_NOM`), `:105-110` (`_carte_cache`).
- **Affiché vs juste** : `GET /admin/circuit` rend littéralement « **Les un cache sont en retard sur les dernières sources** ». La clé `_CACHE_NOM` est `derives_regle` mais `/sante/fraicheur` émet ce cache sous `"tables dérivées (version de règle)"` → le `startswith` (`:105`) échoue → repli « un cache ». Juste : « Les dérivés des règles sont en retard ».
- **Proposition** : ajouter une entrée `_CACHE_NOM` sur le nom réellement émis, ou faire matcher le libellé fraîcheur plutôt que la clé interne.

### NU-F-053 · MINEUR · Admin (Textes) — tuile « en échec » alors que la pastille est grise (jamais passé)
- **Où** : tuiles « Est-ce que tout tourne ? ». `cockpit_resume.py:387-396`.
- **Affiché vs juste** : « Courrier aux clients » pastille **grise** + ligne « dernier passage **en échec** » ; « Contrôle de nuit » gris + « à revoir ». DB : `coherence-banc` et `mail-queue-consommer` ont `dernier.statut = None` (**jamais passé**), pas un échec. Le constructeur de tuile fait `== "vert" sinon "en échec"`, écrasant le cas gris dans « échec ».
- **Proposition** : trois états dans la ligne (vert / gris-jamais / rouge-échec) au lieu de vert-vs-reste → le gris lit « jamais passé ».

## DETTES

### NU-F-042 · DETTE · Compte — `brand.charger` avale toutes les exceptions
- `src/labuse/marque.py:61-82` : `except Exception: return None` → un vrai échec DB/logo est indistinct de « non configuré » ; un client ayant uploadé un logo peut recevoir un PDF sans marque sans le savoir. **Proposition** : logguer en warning dans l'except, distinguer « logo stocké mais illisible ».

### NU-F-043 · DETTE · CRM — `/pipeline` sans borne de pagination
- `app.py:9372-9385` charge toutes les entrées actives du tenant (N+1 déjà résolu par `_prefetch_maps`). Grossit linéairement. **Proposition** : borner/paginer côté serveur.

### NU-F-044 · DETTE · CRM — moteur registre `cartes_par_colonne` mort pour l'UI
- `plateforme.py:131` + `crm_columns.py:176-187` (`GET /pipeline/columns`) jamais appelé par le front → deux sources de « cartes par colonne » qui divergent (cf. NU-F-009/010). **Proposition** : câbler l'UI dessus ou retirer l'endpoint.

### NU-F-045 · DETTE · Copilote/Notifications — fuseau Réunion recodé à la main
- `events.py:300` `REUNION_TZ = timezone(timedelta(hours=4))` (réutilisé `:1262,1351,1373`) contourne `tz.REUNION_TZ` (« jamais le fuseau du process »). Valeur juste aujourd'hui, mais deux sources de vérité. **Proposition** : importer `tz.REUNION_TZ` partout.

### NU-F-046 · DETTE · Copilote — exceptions avalées / fuseaux de repli
- `digests.py:280-281` `except: pass` (insert événement d'échec radar) ; `answering.py:1123-1124` `except: return None` sans rollback → incident serveur trompeur plus tard ; `mailfile.py:297` `.astimezone()` nu (CEST admin) ; `Header.tsx:298` repli `new Date(e.date)` sans offset (mauvais jour hors UTC). **Proposition** : rollback + log ; dates Réunion explicites.

### NU-F-047 · DETTE · Copilote — cloche annonce re-postée d'un jour à l'autre
- `events.py:1538` dédup `annonce:{type}:{titre}` same-day seulement → même titre re-posté le lendemain. **Proposition** : dédup sur une fenêtre glissante.

### NU-F-048 · DETTE · Sécurité — CORS `*` en local seulement
- `app.py:420-424` `allow_origins=["*"]` uniquement si `env=="local"`, sans `allow_credentials`. Juste aujourd'hui. **Proposition** : commentaire/assert que `allow_credentials` ne doit jamais passer `True` avec `*`.

### NU-F-049 · DETTE · Compte — troncature silencieuse des champs marque (240 car.)
- `onboarding.py:1232-1246` coupe à 240 car. sans retour ; l'UI ne donne pas la limite. **Proposition** : afficher la limite / un compteur.

### NU-F-054 · DETTE · Admin — commentaires de compteurs périmés + préfixe d'incident `job-retard:` sans bouton
- Les nombres en dur dans les commentaires de `dashboard.py:2832,2844` (« 95 », « 91/55/266/22 ») sont périmés (servis en direct : 99/60/289/24) — commentaires seulement, pas un bug runtime. Par ailleurs `ops_alertes` écrit des clés `job-retard:<nom>` (`:427`) mais `cockpit_resume._titre_incident_generique` ne traite spécialement que `job-echec:` (`:143`) → les incidents `job-retard:` n'ont pas de bouton « Relancer » (retombent sur « Accepter »). **Proposition** : rafraîchir les commentaires ; traiter le préfixe `job-retard:` comme `job-echec:`.

---

## Ce qui est CORRECT (vérifié, pas supposé)

- **Console** 0 erreur / 0 avertissement sur tout le parcours (npm réel, pas symlink).
- **Isolation multi-tenant (IDOR)** : chaque table scoppée filtre `compte_id IS NOT DISTINCT FROM :cid` ou passe par `_projet_or_404` (projets, pipeline, watch_zones, alertes, event_log, watched_parcels, courrier, documents, copilote). Aucun IDOR trouvé.
- **Garde d'auth global fail-closed** (`app.py:496`), session validée en base à chaque requête (`comptes.py:448`), gardes de déploiement qui refusent de booter si la prod part avec auth off / secret absent / `DEV_MODE` (`auth.py:117-149`). Les **104 routes `/admin/*`** appellent `exiger_admin` (403 pour un client). Un client à 349 € ne peut pas atteindre l'admin en prod.
- **Pas d'injection SQL** : tous les f-strings/`.format` SQL interpolent des **constantes internes** ; l'entrée utilisateur est toujours liée (`:param`, `ANY(:x)`). Sonde `?q=' OR 1=1--` → `{"features":[]}`, 200, pas de dump.
- **Secrets** jamais sérialisés : mots de passe en **argon2id**, jetons en SHA-256, `/admin/stripe` rend un booléen, `/.env` → 404. CSP/HSTS/XFO/nosniff présents ; cookies `HttpOnly`/`SameSite=Lax`/`Secure` hors local ; webhook Stripe signé ; X-Forwarded-For non usurpable.
- **CRM** : surface carte = `contenance_m2` (cohérent fiche) ; particuliers jamais nommés ; aucune carte perdue (archive réversible, suppression de colonne exige `move_to`, refuse la dernière) ; échéances calculées côté serveur en jour Réunion ; pas de scroll horizontal (pagination par flèches) ; mutations optimistes avec rollback + toast.
- **Compte/onboarding** : aucune fuite de secret/PII ; validation serveur du CGV/mot de passe ; jetons `pay_token` signés HMAC ; anti-énumération au reset ; effacement RGPD propre ; upload logo validé par signature (SVG actif rejeté).
- **Copilote** : garde générale (rollback, log serveur, message honnête, aucun id technique) ; sondes de fuite scoring/prompt → refus propre (sauf NU-F-002) ; 429 affiché verbatim.
- **Radar/Veille** : garde date `≤ 2005` → pas de « 1970 » (aucune ligne epoch en base) ; dates serveur en Réunion (`db.py:91` force la session TZ) ; médianes masquées sous n=5 ; `vs-marche` sur id inconnu → 200 `{introuvable}`, pas 500 ; surfaces arrondies par `fmtM2` (pas de fausse précision).
- **Projets** : parité **interne** wizard ↔ projet ouvert OK ; « Partir de zéro » crée bien un dossier vide (vivier 0) ; le budget n'affecte pas la sélection (informatif) ; un seul « Retour » ; dédup douce/fusion cohérentes.

---

## Hors lot (croisé, non instruit)

- Fiche parcelle, exports PDF, scoring interne, estimation prix : Lot A / ESTIMATION-BANC (SDP contradictoire, « maison au prix d'appartement », sur-vente de précision). NU-F-002 recoupe la règle « le scoring ne s'affiche que là où le client l'a demandé ».
- Cloche « 99+ » en local : le bucket pilote (`compte_id NULL`) voit 1045 non-lus (`events.py:712-740`) — attendu en local, mais **à confirmer** qu'aucun vrai client ne tombe dans le bucket NULL en prod (sinon badge 99+ pour tous).
- `par_type` appartement « statistiques seules » et paliers d'écart (normal≥30/indicatif 5-29/insuffisant<5) : cohérents, non réinstruits.
